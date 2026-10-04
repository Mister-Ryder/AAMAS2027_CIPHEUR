"""Independent audit of immutable R2 TRAIN traces and joint/quality roles.

No production scorer, oracle, kernel, loader or assessor is imported/executed.
The existing independently reviewed R1 trace verifier is reused only for
complete non-cap traces; interrupted/error traces retain their honest scope.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import verify_synthesis_train_v06 as independent
from scripts.verify_matched_llm_v05 import BASE, FeatureView, boundary, canonical, normalized_program
from scripts.verify_public_alias_v05 import view, graph_digest, exact_vector, exact_alpha

STEM = "refinement_train_server_v06_002"
RUN = ROOT / "experiments/discovery/v06_refinement_server_002"
STUDY = ROOT / "experiments/discovery/v06_refinement_draft_003"
ARCHIVE = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
CAPSULE = ROOT / "experiments/source_snapshots/v06" / (STEM + "_source.zip")
CAPSULE_SHA = "67239f759c17cf347e663b6495e6dc47a550ffd56fcd86d7e069c20afe3140fc"
AUTHOR_AUDIT = ROOT / "experiments/analysis/v06/refinement_authoring_audit_v06_002.json"
AUTHOR_SHA = "2c3327ae92e0deccabb054636bcabfd9e31ed317679837fc26b31243128b7f7c"
R1_VERIFIER_SHA = "941264da65d8aac3ccb9242de75ebff4c7f8cc29eb602e071be11d4e25dc8322"
ARMS = ("witness", "relations", "objective")
load, digest = independent.load, independent.digest
feasible, value = independent.feasible, independent.exact_value


def complete_trace_verifier(namespace):
    """Extract only a reviewed independent function, never its R1 audit run.

    Reuse preserves the exact audited mathematics without changing any frozen
    R1 source. Its closure variables are supplied by this separate R2 audit.
    """
    path = ROOT / "scripts/verify_synthesis_train_v06.py"
    if digest(path) != R1_VERIFIER_SHA:
        raise ValueError("Reviewed independent R1 mathematics changed")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "audit")
    function = next(n for n in outer.body if isinstance(n, ast.FunctionDef) and n.name == "verify_kernel")
    scope = {**vars(independent), **namespace}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), scope)
    return scope["verify_kernel"]


def audit(output, expected_archive_sha):
    began = time.perf_counter()
    checks, errors, totals = Counter(), [], Counter()

    def require(ok, kind, where=""):
        checks[kind] += 1
        if not ok:
            errors.append({"kind": kind, "where": where})

    require(len(expected_archive_sha) == 64 and digest(ARCHIVE) == expected_archive_sha,
            "independently_pinned_original_R2_result_archive")
    require(digest(CAPSULE) == CAPSULE_SHA, "independently_pinned_R2_source_capsule")
    extraction = load(RUN / "EXTRACTION_RECEIPT.json")
    registration = load(RUN / "registration.json")
    require(extraction["archive_sha256"] == expected_archive_sha and extraction["byte_preserving_extraction"],
            "original_extraction_receipt_binding")
    with tarfile.open(ARCHIVE, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        require(len(members) == len(extraction["raw_members_sha256"]), "entire_original_archive_member_inventory")
        for member in members:
            rel = Path(member.name).relative_to(STEM).as_posix()
            h = sha256()
            stream = tar.extractfile(member)
            for chunk in iter(lambda: stream.read(1048576), b""):
                h.update(chunk)
            require(h.hexdigest() == extraction["raw_members_sha256"][rel] == digest(RUN / rel),
                    "all_original_extracted_result_bytes", rel)
    with zipfile.ZipFile(CAPSULE) as z:
        require(set(z.namelist()) == set(registration["file_sha256"]), "all_original_source_capsule_members")
        for name, expected in registration["file_sha256"].items():
            require(sha256(z.read(name)).hexdigest() == expected == digest(ROOT / name),
                    "capsule_source_input_byte_identity", name)
    require(registration["source_zip_sha256"] == CAPSULE_SHA and registration["before_any_R2_candidate_assessment"]
        and registration["all15_R2_raw_sessions_frozen"] and registration["all120_R2_raw_slots_retained"]
        and registration["assessment_split"] == "train" and not registration["TEST_accessed"]
        and registration["R1_twelve_genuine_barrier_remains_failed"] and registration["R1_sources_unchanged"],
        "registered_R2_all15_frozen_TRAIN_only_R1_failure_retained")
    author = load(AUTHOR_AUDIT)
    require(digest(AUTHOR_AUDIT) == AUTHOR_SHA == registration["authoring_audit_sha256"]
        and author["error_count"] == 0 and not author["errors"] and author["raw_slot_count"] == 120,
        "independent_zero_error_all120_authoring_receipt")
    bank = author["raw_slot_static_inventory"]
    require(load(RUN / "llm/bank.json") == bank, "all120_independent_raw_static_positions_identity")
    rawmap = {r["id"]: r for r in bank}
    proto = load(STUDY / "protocol.json")
    frame = load(STUDY / "training_evidence.json")
    cfg = proto["kernel_config"]
    records = frame["records"]
    rmap, labels = {r["id"]: r for r in records}, {r["id"]: r for r in frame["labels"]}
    require(len(records) == len(rmap) == len(labels) == 120 and all(r["split"] == "train" for r in records)
        and digest(STUDY / "training_evidence.json") == proto["training_evidence_sha256"], "unchanged_full120_TRAIN_states")
    require(sum(q["difference"]["status"] == "strict" for r in labels.values() for q in r["rows"]) == 594,
            "unchanged594_sound_strict_TRAIN_requirements")
    evidence_audit_path = ROOT / "experiments/analysis/v06/evidence_train_audit_v06_001.json"
    evidence_audit = load(evidence_audit_path)
    r1proto = load(ROOT / "experiments/discovery/v06_synthesis_server_001/llm/parent_protocol.json")
    require(not evidence_audit["errors"] and digest(evidence_audit_path) == r1proto["independent_train_evidence_audit_sha256"],
            "previous_independent_exact_label_proof_binding")
    require(proto["source_sha256"]["assessment"] == "f640af65645426cdf172d1cbc7326bae221acf43ece81225ef8bf06cf2c8b0bb"
        and cfg == r1proto["kernel_config"] and proto["selector"] == r1proto["selector"],
        "original_f640_kernel_gate_selector_unchanged")
    state_views = {}
    for r in records:
        require(graph_digest(r["graph"]) == r["graph_digest"], "original_TRAIN_graph_digest", r["id"])
        nodes, _, adj = view(r["graph"])
        state_views[r["id"]] = nodes, adj, boundary(nodes, adj, r["fixed"], r["excluded"])
    exact_patch_cache, priority_cache, interface_cache = {}, {}, {}
    fullverify = complete_trace_verifier({"require": require, "cfg": cfg, "state_views": state_views,
        "totals": totals, "exact_patch_cache": exact_patch_cache, "priority_cache": priority_cache})

    def partialverify(record, result, program, where):
        """Verify returned bounds/witnesses without inventing an exhaustion proof."""
        nodes, adj, legal = state_views[record["id"]]
        fixed, excluded = set(record["fixed"]), set(record["excluded"])
        require(result["config"] == cfg["repair_config"] and result["declared_seconds"] == cfg["seconds"]
            and result["deadline_clock"] == cfg["clock"] and result["priority"] == "program",
            "partial_identical_shared_kernel_configuration", where)
        require(result["feasible"] and result["incumbent_available"] and not result["fallback_used"]
            and result["online_model_calls"] == result["conditional_oracle_calls"] == 0
            and not result["exact_optimum_claimed"] and feasible(nodes, adj, result["selected"], fixed, excluded)
            and Fraction(result["value_exact"]) == value(nodes, result["selected"]),
            "partial_retained_incumbent_exact_reward_feasibility_no_fallback", where)
        require(result["completed"] == (result["error"] is None), "ordinary_budget_vs_explicit_programme_error", where)
        if not result["completed"]:
            require(result["status"] == "programme_or_repair_error", "explicit_failed_programme_retains_diagnostic_only", where)
        incumbent, active = set(fixed), set(legal) - fixed
        for v in fixed:
            active -= adj[v]
        for step in result["initializer_trace"]:
            chosen = min(active, key=lambda v: (-Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & active)), v))
            require(step["selected"] == chosen and step["available"] == len(active)
                and Fraction(step["score_exact"]) == Fraction(nodes[chosen]["weight"]) / max(1, len(adj[chosen] & active)),
                "partial_every_initializer_prefix_argmax", where)
            incumbent.add(chosen); active -= {chosen} | adj[chosen]
        require(sorted(incumbent) == result["initial_selected"]
            and value(nodes, incumbent) == Fraction(result["initial_value_exact"])
            and (not result["initialization_complete"] or not active), "partial_common_initializer_prefix_identity", where)
        require(Fraction(result["starting_value_exact"]) == value(nodes, fixed), "partial_explicit_starting_boundary", where)
        scores = {v: Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & legal)) for v in legal}
        commits, expanded = 0, 0
        for p in result["patch_trace"]:
            totals["saved_patch_traces"] += 1
            d = set(p["destroy"]); outside = incumbent - d
            full = set(nodes) - outside - excluded
            for v in outside:
                full -= adj[v]
            require(d <= incumbent and not d & fixed and len(d) <= cfg["repair_config"]["max_destroy"]
                and p["target"] in legal - incumbent and adj[p["target"]] & incumbent <= d
                and Fraction(p["incumbent_patch_exact"]) == value(nodes, d), "partial_legal_destroy_target_boundary", where)
            replacement = set(p["local_selected"])
            require(feasible(nodes, adj, replacement) and Fraction(p["lower_exact"]) == value(nodes, replacement)
                and value(nodes, replacement) >= value(nodes, d), "partial_feasible_lower_and_destroy_seed", where)
            if p["patch"] is None:
                require(p["stage"] == "region_construction" and replacement == d and not p["committed"]
                    and p["upper_exact"] is None and not p["restricted_exact"], "interrupted_region_no_fabricated_bound", where)
            else:
                patch = set(p["patch"])
                keep = set(d)
                if len(keep) < cfg["repair_config"]["max_patch_vertices"]:
                    keep.add(p["target"])
                extra = sorted(full - keep, key=lambda v: (-scores[v], v))
                expected = keep | set(extra[:cfg["repair_config"]["max_patch_vertices"]-len(keep)])
                require(patch == expected and d <= patch <= full and replacement <= patch
                    and p["full_region_size"] == len(full) and p["restricted"] == (patch != full),
                    "partial_exact_D_preserving_shared_restriction", where)
                if p["root_upper_exact"] is None:
                    require(p["upper_exact"] is None and not p["restricted_exact"] and not p["root_clique_cover"],
                            "uncomputed_root_upper_remains_unknown", where)
                else:
                    cover = p["root_clique_cover"]; flat = [v for group in cover for v in group]
                    require(len(flat) == len(set(flat)) and set(flat) == patch
                        and all(g and all(b in adj[a] for i,a in enumerate(g) for b in g[i+1:]) for g in cover),
                        "partial_root_clique_cover_exact_feasibility", where)
                    upper = sum((max(Fraction(nodes[v]["weight"]) for v in g) for g in cover), Fraction())
                    require(upper == Fraction(p["root_upper_exact"]) and upper >= value(nodes, replacement),
                            "partial_root_upper_sound_envelope", where)
                    if p["restricted_exact"]:
                        key = (record["graph_digest"], tuple(sorted(patch)))
                        if key not in exact_patch_cache:
                            exact_patch_cache[key] = exact_alpha(nodes, adj, patch, max_states=1000000)
                        require(exact_patch_cache[key][0] == value(nodes, replacement) == Fraction(p["upper_exact"]),
                                "partial_reported_exact_patch_independent_proof", where)
                    else:
                        require(Fraction(p["upper_exact"]) == upper, "interrupted_BnB_keeps_sound_root_upper", where)
                if p["priority_order"]:
                    key = (canonical({k: program[k] for k in ("features", "rule")}), record["graph_digest"], tuple(sorted(patch)))
                    if key not in priority_cache:
                        state = FeatureView(record["graph"], active=patch)
                        ps = {v: independent.score_lazy(program, state, v) for v in sorted(patch)}
                        priority_cache[key] = sorted(patch, key=lambda v: (-ps[v], v))
                    require(p["priority_order"] == priority_cache[key], "partial_saved_complete_local_priority_order", where)
                    degree = sorted(patch, key=lambda v: (-Fraction(nodes[v]["weight"]) / max(1,len(adj[v]&patch)),v))
                    require(p["common_degree_order"] == degree, "partial_common_degree_priority_order", where)
                    for g in p["greedy_passes"]:
                        order = priority_cache[key] if g["order"] == "priority" else degree
                        remaining, taken, attainable = set(patch), set(), {Fraction()}
                        for v in order:
                            if v in remaining:
                                taken.add(v); remaining -= {v} | adj[v]
                            attainable.add(value(nodes, taken))
                        require(Fraction(g["value_exact"]) in attainable
                            and (not g["complete"] or Fraction(g["value_exact"]) == value(nodes,taken)),
                            "partial_greedy_lower_feasible_prefix_not_full_pass_claim", where)
            gain = value(nodes, replacement) - value(nodes, d)
            require(Fraction(p["gain_exact"]) == gain and p["committed"] == (gain > 0),
                    "partial_strict_positive_commit_rule", where)
            if p["committed"]:
                new = outside | replacement
                require(feasible(nodes,adj,new,fixed,excluded) and value(nodes,new) > value(nodes,incumbent),
                        "partial_monotone_global_feasible_commit", where)
                incumbent = new; commits += 1
            require(0 <= p["search_nodes"] <= cfg["repair_config"]["node_budget_per_patch"], "partial_patch_node_cap", where)
            expanded += p["search_nodes"]
        require(sorted(incumbent) == result["selected"] and commits == result["improvements"]
            and len(result["patch_trace"]) == result["patches_attempted"], "partial_trace_final_incumbent_identity", where)
        meter = result["meter"]
        # A node charge may stop before local expanded increments; never hide it.
        require(expanded <= meter["search_nodes"] <= cfg["repair_config"]["max_search_nodes"]
            and meter["search_nodes"]-expanded <= int(result["global_budget_exhausted"]),
            "partial_charged_node_interrupt_difference_explicit", where)
        for kind in ("feature", "repair"):
            work, primitives = meter[kind+"_work"], meter[kind+"_primitives"]
            require(type(work) is int and work >= 0 and all(type(v)is int and v>=0 for v in primitives.values())
                and sum(primitives.values()) <= work
                and (result["global_budget_exhausted"] or sum(primitives.values()) == work),
                "partial_work_receipt_interrupt_before_breakdown_not_hidden", where)
        require(all(math.isfinite(result[k]) and result[k] >= 0 for k in ("wall_seconds","cpu_seconds")),
                "partial_original_actual_timing_not_remeasured", where)
        if result["global_budget_exhausted"]:
            require(result["status"] in ("time_budget","work_budget","total_node_budget"), "partial_original_global_budget_reason", where)
        totals["verified_kernel_assignments"] += 1
        totals["partial_or_errored_kernel_assignments"] += 1

    def verify_witnesses(saved, vectors, requirements, where):
        for witness in saved["structural_witnesses"]:
            arcs, joins = witness["requirements"], witness["equality_joins"]
            require(bool(arcs) and len(arcs) == len(joins), "complete_actual_cycle_join_witness", where)
            for i,(arc,join) in enumerate(zip(arcs,joins)):
                index = arc["requirement_index"]
                require({k:arc[k] for k in requirements[index]} == requirements[index], "actual_cycle_original_certified_arc", where)
                n,p = arc["other"], arcs[(i+1)%len(arcs)]["preferred"]
                require(join["negative"] == n and join["positive"] == p
                    and join["negative_vector"] == vectors[n] and join["positive_vector"] == vectors[p]
                    and exact_vector(vectors[n]) == exact_vector(vectors[p]), "actual_complete_exact_vector_join", where)

    rows, seen, statuses = [], set(), Counter()
    with (RUN / "llm/candidate_results.jsonl").open(encoding="utf-8") as f:
        for index,line in enumerate(f):
            row = json.loads(line); identity = row["id"]
            require(identity in rawmap and identity not in seen, "one_original_assessment_per_raw_slot", identity)
            seen.add(identity); statuses[row["assessment_status"]] += 1
            require(all(row[k] == v for k,v in rawmap[identity].items() if k not in ("error","error_type")),
                    "original_raw_program_static_identity_unchanged", identity)
            small = {k:row[k] for k in ("id","block","arm","slot","eligible","assessment_status")}
            small["quality_covered"] = False
            if row["status"] != "static_valid":
                require(not row["eligible"] and not row["kernel_rows"] and row["assessment_status"] == row["status"],
                        "invalid_raw_position_no_hidden_fallback", identity)
                rows.append(small); continue
            program = normalized_program(row["program"])
            ahash = canonical({k:program[k] for k in ("features","rule")})
            require(ahash == row["deployment_AST_sha256"] and canonical(program) == row["program_sha256"],
                    "canonical_independent_static_deployment_identity", identity)
            small.update(program=program, program_sha256=row["program_sha256"])
            if "interface" not in row:
                require(not row["eligible"] and row["assessment_status"] == "interface_or_execution_error"
                    and not row["kernel_rows"] and row.get("error_type") is not None,
                    "explicit_interface_failure_not_genuine_candidate", identity)
                totals["interface_failures_not_numerically_replayed"] += 1
                rows.append(small); continue
            if ahash not in interface_cache:
                interface_cache[ahash] = independent.interface(program, records, labels)
            ref,vectors,fullvectors,requirements = interface_cache[ahash]
            saved = row["interface"]
            for k in ("demanded_features","strict_total","strict_passed","alias_strict_total","alias_strict_passed","full_observed_consistency"):
                require(saved[k] == ref[k], "independent_demanded_interface_actual_fit", identity+"/"+k)
            require(saved["strict_checks"] == ref["strict_checks"], "all594_independent_scalar_rank_predictions", identity)
            for name,vv in (("quotient",vectors),("declared_quotient",fullvectors)):
                require(all(saved[name][k] == ref[name][k] for k in ref[name]), "independent_full_feature_quotient_gate", identity+"/"+name)
                verify_witnesses(saved[name],vv,requirements,identity+"/"+name)
            require(len(row["kernel_rows"]) == 120 and {q["id"] for q in row["kernel_rows"]} == set(rmap),
                    "all120_actual_TRAIN_assignments_per_candidate", identity)
            fq,fw = defaultdict(list),defaultdict(list); valid=True
            for q in row["kernel_rows"]:
                r,result = rmap[q["id"]],q["result"]
                require(q["family"] == r["family"], "kernel_family_source_identity", identity)
                complete = (result["completed"] and not result["global_budget_exhausted"]
                    and all(p["patch"] is not None and p["root_upper_exact"] is not None
                            and all(g["complete"] for g in p["greedy_passes"]) for p in result["patch_trace"]))
                (fullverify if complete else partialverify)(r,result,program,identity+"|"+r["id"])
                valid = valid and result["completed"] and result["feasible"]
                denom = sum((Fraction(n["weight"]) for n in r["graph"]["contacts"]),Fraction())
                fq[r["family"]].append(Fraction(result["value_exact"])/denom if denom else Fraction(1))
                fw[r["family"]].append(result["meter"]["feature_work"]+result["meter"]["repair_work"])
                totals["global_budget_stops"] += int(result["global_budget_exhausted"])
                totals["kernel_programme_errors"] += int(not result["completed"])
            familyq = {k:sum(v,Fraction())/len(v) for k,v in fq.items()}
            familyw = {k:Fraction(sum(v),len(v)) for k,v in fw.items()}
            summary = {"macro_quality_exact":str(sum(familyq.values(),Fraction())/len(familyq)),
                "macro_work_exact":str(sum(familyw.values(),Fraction())/len(familyw)),
                "family_reward_over_total_weight":{k:str(v) for k,v in familyq.items()},
                "family_work":{k:str(v) for k,v in familyw.items()}}
            require(summary == row["kernel_summary"], "exact_eight_family_quality_work_denominators", identity)
            require(row["eligible"] == (valid and not ref["quotient"]["contradictory"])
                and row["assessment_status"] == ("assessed" if valid else "kernel_execution_error"),
                "unchanged_joint_gate_actual_execution_eligibility", identity)
            small.update(quality_covered=valid and row["assessment_status"] == "assessed",
                strict_passed=ref["strict_passed"], alias_strict_passed=ref["alias_strict_passed"],
                demanded_features=ref["demanded_features"], quotient=ref["quotient"], kernel_summary=summary)
            rows.append(small)
            if (index+1)%8 == 0:
                print(json.dumps({"R2_positions_verified":index+1,"kernel_assignments_verified":totals["verified_kernel_assignments"],
                                  "errors_so_far":len(errors)}),flush=True)
    require(seen == set(rawmap) and len(rows) == 120, "all120_original_positions_retained")
    matched = author["matched_transport_complete_blocks"]
    require(matched == registration["matched_transport_complete_blocks"] == [0,1,2,3], "independent_predeclared_transport_cohort")

    def jointkey(r):
        return (-r["strict_passed"],-Fraction(r["kernel_summary"]["macro_quality_exact"]),
                Fraction(r["kernel_summary"]["macro_work_exact"]),r["slot"])

    def qkey(r):
        return (-Fraction(r["kernel_summary"]["macro_quality_exact"]),Fraction(r["kernel_summary"]["macro_work_exact"]),r["slot"])

    fields=("id","block","arm","slot","program","program_sha256","eligible")
    joint,empty,prefixes,quality=[],[],[],[]
    for b in range(5):
        for arm in ARMS:
            cell=sorted((r for r in rows if r["block"]==b and r["arm"]==arm),key=lambda r:r["slot"])
            elig=[r for r in cell if r["eligible"]]
            if elig:
                joint.append(min(elig,key=jointkey))
            else:
                empty.append({"block":b,"arm":arm})
            for n in range(1,9):
                ee=[r for r in cell[:n] if r["eligible"]]
                best=min(ee,key=jointkey) if ee else None
                prefixes.append({"block":b,"arm":arm,"raw_slots":n,"winner_id":best["id"] if best else None,
                    "strict_passed":best["strict_passed"] if best else None,
                    "first_eligible_original_slot":min(r["slot"] for r in ee) if ee else None})
            qq=[r for r in cell if r["quality_covered"]]
            quality.append({"block":b,"arm":arm,"winner":min(qq,key=qkey) if qq else None})
    proposed=[r for r in joint if r["block"] in matched and r["arm"]=="witness"]
    qm=[r for r in quality if r["block"] in matched]
    expected=[{**{k:r[k] for k in fields},"id":"joint|"+r["id"],"source_candidate_id":r["id"],
        "role":"proposed_witness_joint","joint_gate_required":True} for r in proposed]
    for c in qm:
        r=c["winner"]
        expected.append({**({k:r[k] for k in fields} if r else {"block":c["block"],"arm":c["arm"],"slot":None,
            "program":None,"program_sha256":None,"eligible":False}),
            "id":"quality|"+(r["id"] if r else f"block_{c['block']}_{c['arm']}:missing"),
            "source_candidate_id":r["id"] if r else None,"role":"nonguarded_quality_comparator",
            "joint_gate_required":False,"missing_baseline":r is None})
    selected=load(RUN/"llm/selection.json")
    ready=len(matched)==4 and len(proposed)==4
    expected_fields={"matched_transport_complete_blocks":matched,"all_uniform_joint_winners":[{k:r[k] for k in fields} for r in joint],
        "all_uniform_empty_joint_cells":empty,"all_raw_joint_prefixes":prefixes,
        "all_uniform_quality_winners":[{"block":c["block"],"arm":c["arm"],"winner":{k:c["winner"][k] for k in fields} if c["winner"] else None} for c in quality],
        "proposed_witness_joint_count":len(proposed),"ready_for_TEST":ready,"programs":expected,
        "quality_comparator_requested_count":len(qm),"quality_comparator_missing_cells":[{"block":c["block"],"arm":c["arm"]} for c in qm if c["winner"] is None],
        "no_fallback":True,"R1_barrier_remains_failed":True}
    for key,expect in expected_fields.items():
        require(selected[key]==expect,"independent_uniform_joint_quality_role_selection",key)
    require(selected["all120_original_slots_assessed"] and not selected["test_accessed"]
        and selected["selection_split"]=="train" and selected["protocol_sha256"]==digest(STUDY/"protocol.json")
        and selected["candidate_results_sha256"]==digest(RUN/"llm/candidate_results.jsonl")
        and selected["selection_plan_sha256"]==proto["selection_plan_sha256"],"selection_exact_original_input_receipts_noTEST")
    completion=load(RUN/"llm/complete.json")
    require(completion["all120_assessed"] and completion["eligible"]==sum(r["eligible"] for r in rows)
        and completion["status"]==dict(statuses) and completion["ready_for_TEST"]==ready
        and completion["proposed_witness_joint_count"]==len(proposed)
        and completion["selection_sha256"]==digest(RUN/"llm/selection.json") and completion["TEST_queries"]==0,
        "original_complete_receipt_exact_counts_four_W_barrier")
    execution=load(RUN/"server_execution_receipt.json")
    phase=load(RUN/"phase_receipts.json")
    host=load(RUN/"host_receipt.json")
    require(execution["execution_complete"] and execution["TEST_queries"]==execution["online_model_calls"]==execution["oracle_calls"]==0
        and execution["no_retries"] and len(phase)==1 and phase[0]["exit_code"]==0
        and not phase[0]["whole_phase_guard_triggered"] and phase[0]["no_retry"],"one_frozen_server_TRAIN_phase_no_retry_TEST_model_or_oracle")
    require(host["timestamp_unix"]>datetime.fromisoformat(load(STUDY/"authoring_completion.json")["completed_utc"]).timestamp()
        and host["workers"]==8 and host["registration_sha256"]==digest(RUN/"registration.json"),
        "server_execution_after_all15_author_freeze")
    totals["distinct_independent_exact_patch_queries"]=len(exact_patch_cache)
    totals["independent_exact_patch_verifier_states"]=sum(v[1] for v in exact_patch_cache.values())
    report={"version":"independent_R2_frozen_TRAIN_audit_v06_002","total_checks":sum(checks.values()),"checks":dict(checks),
        "errors":errors,"error_count":len(errors),"totals":dict(totals),"raw_slot_count":len(rows),
        "selection_sha256":digest(RUN/"llm/selection.json"),"ready_for_TEST":ready,"proposed_witness_joint_count":len(proposed),
        "matched_transport_complete_blocks":matched,"status_counts":dict(statuses),"candidate_summaries":rows,
        "metadata":{"archive_sha256":expected_archive_sha,"source_zip_sha256":CAPSULE_SHA,
            "registration_sha256":digest(RUN/"registration.json"),"extraction_receipt_sha256":digest(RUN/"EXTRACTION_RECEIPT.json"),
            "authoring_audit_sha256":AUTHOR_SHA,"protocol_sha256":digest(STUDY/"protocol.json"),
            "candidate_results_sha256":digest(RUN/"llm/candidate_results.jsonl"),"audit_script_sha256":digest(__file__),
            "independent_helpers_sha256":{name:digest(ROOT/name) for name in ("scripts/verify_synthesis_train_v06.py",
                "scripts/verify_matched_llm_v05.py","scripts/verify_public_alias_v05.py")}},
        "verification_wall_seconds":time.perf_counter()-began,
        "scope":["No original production assessor/kernel/scorer/oracle/loader is imported or executed.",
            "All raw positions, missing/invalid/error/capped outcomes and actual scalar/quotient/quality/work observations remain distinct.",
            "Complete non-cap traces reuse only the frozen independent R1 mathematical verifier; partial traces retain unknown bounds and feasible prefixes.",
            "Costs/times are saved charged proxies and actual receipts, never substituted with verifier timings.",
            "R1's failed12-winner barrier remains immutable; R2 independently requires four genuine witness joint winners.",
            "Uniform quality-only comparators do not inherit certificate consistency or count as proposed-method winners.",
            "No candidate tuning, replacement, production TRAIN reexecution or TEST query/evaluation is performed."]}
    output=Path(output)
    if output.exists():
        raise ValueError("Preserve every independent R2 audit; append a reviewed report if needed")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"checks":report["total_checks"],"errors":len(errors),"ready_for_TEST":ready,
        "proposed_witness_joint_count":len(proposed),"audit_sha256":digest(output)}),flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True)
    p.add_argument("--archive-sha",required=True)
    a=p.parse_args()
    audit(ROOT/a.out,a.archive_sha)
