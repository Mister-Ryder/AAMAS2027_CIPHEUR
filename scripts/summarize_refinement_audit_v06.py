"""Descriptive scientific review from the zero-error independent R2 audit.

No program or graph is executed. Raw saved interface metadata is used only to
report declared-vs-demanded gate counts already checked by that audit.
"""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/"experiments/analysis/v06/refinement_train_audit_v06_002.json"
AUTHOR=ROOT/"experiments/analysis/v06/refinement_authoring_audit_v06_002.json"
SELECT=ROOT/"experiments/discovery/v06_refinement_server_002/llm/selection.json"
RESULTS=ROOT/"experiments/discovery/v06_refinement_server_002/llm/candidate_results.jsonl"
ARMS=("witness","relations","objective")


def digest(p):
    return sha256(p.read_bytes()).hexdigest()


def main():
    a=json.loads(AUDIT.read_bytes()); author=json.loads(AUTHOR.read_bytes()); sel=json.loads(SELECT.read_bytes())
    assert digest(AUDIT)=="a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34"
    assert a["error_count"]==0 and not a["errors"] and digest(SELECT)==a["selection_sha256"]
    assert digest(RESULTS)==a["metadata"]["candidate_results_sha256"]
    rows=a["candidate_summaries"]; rmap={r["id"]:r for r in rows}
    static={r["id"]:r["status"] for r in author["raw_slot_static_inventory"]}
    declared={}
    for line in RESULTS.open(encoding="utf-8"):
        r=json.loads(line)
        declared[r["id"]]={"declared_quotient":r["interface"]["declared_quotient"],
            "full_observed_consistency":r["interface"]["full_observed_consistency"]}

    def mean_exact(values):
        return str(sum(map(Fraction,values),Fraction())/len(values)) if values else None

    def metrics(rs):
        return {"raw_slots":len(rs),"static_valid":sum(static[r["id"]]=="static_valid" for r in rs),
            "finite_interface_verified":sum("strict_passed" in r for r in rs),
            "completed_feasible_all120":sum(r["quality_covered"] for r in rs),
            "joint_eligible":sum(r["eligible"] for r in rs),
            "joint_eligibility_yield_exact":str(Fraction(sum(r["eligible"] for r in rs),len(rs))),
            "demanded_quotient_conflicts":sum(r["quotient"]["contradictory"] for r in rs),
            "demanded_direct_selfloop_candidates":sum(r["quotient"]["self_loop_requirements"]>0 for r in rs),
            "demanded_cycle_without_selfloop_candidates":sum(r["quotient"]["contradictory"] and r["quotient"]["self_loop_requirements"]==0 for r in rs),
            "declared_quotient_conflicts":sum(declared[r["id"]]["declared_quotient"]["contradictory"] for r in rs),
            "full_actual_scalar_consistency":sum(declared[r["id"]]["full_observed_consistency"] for r in rs),
            "mean_strict_passed_exact":mean_exact([r["strict_passed"] for r in rs]),"strict_total":594,
            "mean_actual_alias_passed_exact":mean_exact([r["alias_strict_passed"] for r in rs]),"actual_alias_total":90,
            "min_max_strict_passed":[min(r["strict_passed"] for r in rs),max(r["strict_passed"] for r in rs)],
            "candidate_macro_Q_exact_values":sorted({r["kernel_summary"]["macro_quality_exact"] for r in rs}),
            "mean_candidate_macro_work_exact":mean_exact([r["kernel_summary"]["macro_work_exact"] for r in rs])}

    populations={}
    for name,blocks in (("all_five_fixed_blocks",list(range(5))), ("matched_four_transport_blocks",a["matched_transport_complete_blocks"])):
        armdata={arm:metrics([r for r in rows if r["arm"]==arm and r["block"] in blocks]) for arm in ARMS}
        blockdata=[{"block":b,"arms":{arm:metrics([r for r in rows if r["arm"]==arm and r["block"]==b]) for arm in ARMS}} for b in blocks]
        contrasts={"W_minus_R_joint_yield_pp_exact":str(100*(Fraction(armdata["witness"]["joint_eligibility_yield_exact"])-Fraction(armdata["relations"]["joint_eligibility_yield_exact"]))),
            "W_minus_R_mean_strict_labels_exact":str(Fraction(armdata["witness"]["mean_strict_passed_exact"])-Fraction(armdata["relations"]["mean_strict_passed_exact"])),
            "W_minus_R_mean_alias_labels_exact":str(Fraction(armdata["witness"]["mean_actual_alias_passed_exact"])-Fraction(armdata["relations"]["mean_actual_alias_passed_exact"]))}
        populations[name]={"blocks":blocks,"arms":armdata,"block_details":blockdata,"descriptive_contrasts":contrasts}

    def selected(r,role):
        s=rmap[r["id"]]
        return {"id":r["id"],"block":r["block"],"arm":r["arm"],"slot":r["slot"],"role":role,
            "joint_eligible":s["eligible"],"strict_passed":s["strict_passed"],"strict_total":594,
            "actual_alias_passed":s["alias_strict_passed"],"actual_alias_total":90,
            "macro_Q_exact":s["kernel_summary"]["macro_quality_exact"],"macro_work_exact":s["kernel_summary"]["macro_work_exact"],
            "demanded_quotient_conflict":s["quotient"]["contradictory"],
            "full_actual_scalar_consistency":declared[s["id"]]["full_observed_consistency"]}

    joint=[selected(r,"uniform_joint_selection") for r in sel["all_uniform_joint_winners"]]
    quality=[selected(c["winner"],"nonguarded_quality_only_selection") if c["winner"] else {"block":c["block"],"arm":c["arm"],"id":None} for c in sel["all_uniform_quality_winners"]]
    chosen={}
    for role,data in (("uniform_joint",joint),("uniform_quality_only",quality)):
        chosen[role]={}
        for arm in ARMS:
            rs=[r for r in data if r["block"] in a["matched_transport_complete_blocks"] and r["arm"]==arm and r["id"] is not None]
            chosen[role][arm]={"present_programs":len(rs),"requested_programs":4,
                "mean_strict_passed_exact":mean_exact([r["strict_passed"] for r in rs]),
                "mean_alias_passed_exact":mean_exact([r["actual_alias_passed"] for r in rs]),
                "mean_macro_Q_exact":mean_exact([r["macro_Q_exact"] for r in rs]),
                "mean_macro_work_exact":mean_exact([r["macro_work_exact"] for r in rs]),
                "actually_joint_eligible_count":sum(r["joint_eligible"] for r in rs)}
    report={"version":"independent_R2_descriptive_scientific_review_v06_002","audit_sha256":digest(AUDIT),
        "selection_sha256":digest(SELECT),"source_archive_sha256":a["metadata"]["archive_sha256"],
        "authoring_audit_sha256":digest(AUTHOR),"summary_script_sha256":digest(Path(__file__)),
        "populations":populations,"all_uniform_joint_selected":joint,"all_uniform_quality_only_selected":quality,
        "matched_selected_arm_means":chosen,"ready_for_TEST":a["ready_for_TEST"],"proposed_witness_joint_count":a["proposed_witness_joint_count"],
        "limits":["No new scientific outcome or program execution: only byte-bound zero-error audit and original saved metadata.",
            "All5-block descriptive yield is distinct from the preregistered matched4-block cohort.",
            "Joint and quality-only selection roles are different; passing the information gate does not imply full scalar consistency.",
            "All120candidates have identical TRAIN scheduleQ; no TRAIN scheduling-quality advantage is supported.",
            "W's higher gate yield must not be described as superior scalarfit: its mean raw and joint-selected strictfit is lower thanR.",
            "The common seed/frontier are R1-selected adaptive TRAIN feedback; four transport-conditional blocks and unequal authoring costs limit causal scope.",
            "Programme deployment is only a frozen readiness result; performance and heldout-label transfer remain unmeasured here."]}
    out=ROOT/"experiments/analysis/v06/refinement_train_scientific_review_v06_002.json"
    if out.exists():raise ValueError("Preserve scientific review")
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"review_sha256":digest(out),"populations":{k:v["descriptive_contrasts"] for k,v in populations.items()},"selected_means":chosen}))


if __name__=="__main__":main()
