"""Independent pre-generation replay of the R1-derived R2 packet frontier.

Only saved JSON and hashes are read. No production author, assessor, kernel,
feature evaluator or conditional oracle is imported or invoked.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "experiments/discovery/v06_synthesis_server_001/llm"
AUDIT = ROOT / "experiments/analysis/v06/synthesis_train_audit_v06_001.json"
AUDIT_SHA = "d0dfeb7d780dda90e70cd16f77c8348ff9e8293a34eafa716bef6e4cd0b5226e"
PLAN = ROOT / "configs/refinement_selection_v06_002.json"
PLAN_SHA = "2fda6a9ef59f8483deb838c0edca2b515118c2d7409f44ee3bc655217d7c71d9"
SALT = "v06_r2_counterexample_metadata_sha_002"
ARMS = ("witness", "relations", "objective")


def digest(path):
    h = sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def ordering(obj):
    return sha256(SALT.encode() + b"|" + encoded(obj)).digest()


def projection(result):
    return {"initial_value_exact": result["initial_value_exact"],
            "value_exact": result["value_exact"], "selected": result["selected"],
            "improvements": result["improvements"],
            "patches_attempted": result["patches_attempted"],
            "search_nodes": result["meter"]["search_nodes"],
            "feature_work": result["meter"]["feature_work"],
            "repair_work": result["meter"]["repair_work"],
            "cpu_seconds": result["cpu_seconds"],
            "wall_seconds": result["wall_seconds"]}


def audit(study, output):
    checks, errors = Counter(), []

    def require(ok, check, location=""):
        checks[check] += 1
        if not ok:
            errors.append({"check": check, "location": location})

    require(digest(AUDIT) == AUDIT_SHA, "immutable_R1_independent_audit")
    require(digest(PLAN) == PLAN_SHA, "approved_before_generation_role_plan")
    prior, plan = load(AUDIT), load(PLAN)
    require(prior["error_count"] == 0 and prior["total_checks"] == 3203865
            and not prior["summary"]["ready_for_TEST"], "R1_failed_barrier_not_reopened")
    frame, seedsel, prep = (load(study / n) for n in
                           ("training_evidence.json", "seed_selection.json", "preparation_receipt.json"))
    proto = load(study / "draft_protocol.json")
    require(digest(study / "training_evidence.json") == prior["metadata"]["training_evidence_sha256"],
            "unchanged_full120_TRAIN_frame")
    require(digest(R1 / "candidate_results.jsonl") == prior["metadata"]["llm_results_sha256"],
            "unchanged_all120_original_R1_result_positions")
    for name, expected in prep["immutable_prepared_files_sha256"].items():
        require(digest(study / name) == expected, "prepared_byte_hash", name)
    require(digest(ROOT / "scripts/prepare_refinement_round_v06.py") == prep["source_sha256"],
            "unchanged_packet_builder_source")
    require(proto["blocks"] == 5 and proto["requested_slots"] == 120
            and proto["slots_per_block_arm"] == 8 and proto["arms"] == list(ARMS)
            and proto["no_adaptive_supplement"] and proto["no_retry_or_replacement"]
            and proto["selection_split"] == "train" and not proto["test_accessed"]
            and not proto["registered_before_round2_authoring"], "five_fixed_blocks_draft_before_authoring")
    require(not (study / "authoring_completion.json").exists()
            and not (study / "responses").exists() and not (study / "receipts").exists(),
            "no_R2_authored_or_assessed_outcomes_seen")
    for name, expected in proto["all_unchanged_assessment_sources"].items():
        require(digest(ROOT / "cipheur" / name) == expected,
                "unchanged_original_assessment_source", name)

    summaries = prior["candidate_summaries"]["llm"]
    candidates = [r for r in summaries if r["assessment_status"] == "assessed"
                  and not r["eligible"] and r["quotient"]["contradictory"]]
    best = min(candidates, key=lambda r: (-r["strict_passed"],
               -Fraction(r["kernel_summary"]["macro_quality_exact"]),
               Fraction(r["kernel_summary"]["macro_work_exact"]), r["id"]))
    require(best["id"] == seedsel["seed_source_id"] == "block_2_relations:3"
            and seedsel["seed_program"] == best["program"]
            and seedsel["seed_kernel_summary"] == best["kernel_summary"]
            and seedsel["seed_strict_passed"] == best["strict_passed"] == 584,
            "independent_exact_common_best_ineligible_seed_selection")
    raw = None
    with (R1 / "candidate_results.jsonl").open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["id"] == best["id"]:
                raw = row
                break
    require(raw is not None and seedsel["cycle_witnesses"] == raw["interface"]["quotient"]["structural_witnesses"]
            and seedsel["deployment_AST_sha256"] == raw["deployment_AST_sha256"],
            "common_seed_and_cycle_original_row_identity")
    require(seedsel["seed_program"]["features"] == best["program"]["features"]
            and seedsel["seed_program"]["rule"] == best["program"]["rule"],
            "common_seed_six_feature_code_unchanged")
    rmap = {r["id"]: r for r in frame["records"]}
    labelmap = {r["id"]: r for r in frame["labels"]}
    feedback = {r["id"]: r["result"] for r in frame["kernel_feedback"]}
    seedrows = {r["id"]: r["result"] for r in raw["kernel_rows"]}
    require(len(rmap) == 120 and all(r["split"] == "train" for r in rmap.values()), "TRAIN_only_state_inventory")
    strict = {}
    for sid in sorted(rmap):
        rows = [r for r in labelmap[sid]["rows"] if r["difference"]["status"] == "strict"]
        for i, q in enumerate(rows):
            p, a, b = q["difference"]["preferred"], q["a"], q["b"]
            n = b if p == a else a
            lo, hi = Fraction(q["difference"]["lower_exact"]), Fraction(q["difference"]["upper_exact"])
            if p == b:
                lo, hi = -hi, -lo
            strict[sid, p, n] = {"state": sid, "preferred": p, "other": n,
                "query_index": i, "kind": q["kind"], "lower_exact": str(lo), "upper_exact": str(hi)}
    require(len(strict) == 594, "all594_original_certified_relations_unchanged")

    mandatory = []
    for cycle in raw["interface"]["quotient"]["structural_witnesses"]:
        for req in cycle["requirements"]:
            sid = req["state"]
            key = (sid, req["preferred"][len(sid)+1:], req["other"][len(sid)+1:])
            require(key in strict and strict[key]["query_index"] == req["query_index"],
                    "mandatory_cycle_arc_certified_original_label", str(key))
            if key not in mandatory:
                mandatory.append(key)
    require(seedsel["mandatory_cycle_requirements"] == [list(k) for k in mandatory]
            and len(mandatory) == 2, "two_exact_mandatory_cycle_arcs")
    companions = defaultdict(set)
    for r in rmap.values():
        if r["paired"]:
            companions[r.get("pair", r["cluster"])].add(r["id"])

    def closure(keys):
        states = {k[0] for k in keys}
        for sid in list(states):
            r = rmap[sid]
            if r["paired"]:
                states.update(companions[r.get("pair", r["cluster"])])
        return states

    def keymeta(k):
        return {"state": k[0], "preferred": k[1], "other": k[2], "kind": strict[k]["kind"]}

    selected = list(mandatory)
    failed = {(c["state"], c["preferred"], c["b"] if c["preferred"] == c["a"] else c["a"])
              for c in raw["interface"]["strict_checks"] if not c["passed"]}
    decisions = []
    for k in sorted(failed - set(selected), key=lambda k: (ordering(keymeta(k)), k)):
        include = len(selected) < 32 and len(closure(selected + [k])) <= 16
        decisions.append({"key": list(k), "included": include,
                          "metadata_sha256": ordering(keymeta(k)).hex()})
        if include:
            selected.append(k)
    selected.sort(key=lambda k: (ordering(keymeta(k)), k))
    states = sorted(closure(selected), key=lambda sid: (ordering({"state": sid}), sid))
    mapping = {sid: "case_%03d" % i for i, sid in enumerate(states)}
    expected_labels = [{**strict[k], "label_id": "r%03d" % i} for i, k in enumerate(selected)]
    require(seedsel["selected_requirements"] == expected_labels
            and seedsel["feedback_cap_decisions"] == decisions
            and seedsel["all_common_states"] == states
            and seedsel["masked_state_bindings"] == mapping
            and len(selected) == 11 and len(states) == 6,
            "independent_SHA_frontier_eleven_labels_six_states")
    require(proto["packet_cases"] == 6 and proto["packet_strict_relations"] == 11
            and proto["packet_cycle_witnesses"] == 1 and proto["packet_concrete_equality_joins"] == 2,
            "draft_protocol_actual_packet_counts")

    common_names = ("shared_seed_program", "shared_seed_macro_feedback", "base_features",
        "typed_operations", "limits", "rule_language", "operation_notes", "deployment_kernel",
        "common_observation_scope", "authoring_constraints", "examples", "output_schema", "task", "version")
    expected_arm_packets = {}
    packets = {}
    for b in range(5):
        for arm in ARMS:
            name = "block_%d_%s" % (b, arm)
            packet = load(study / "packets" / (name + ".json"))
            packets[name] = packet
            text = encoded(packet).decode()
            require(packet["block"] == b and packet["arm"] == arm
                    and len((study / "packets" / (name + ".json")).read_bytes()) <= 180000,
                    "exact_arm_block_assignment_packet_cap", name)
            if arm not in expected_arm_packets:
                expected_arm_packets[arm] = {k: v for k, v in packet.items() if k != "block"}
            require({k: v for k, v in packet.items() if k != "block"} == expected_arm_packets[arm],
                    "same_arm_all_five_blocks_identical_except_index", name)
            require(not any(sid in text for sid in rmap)
                    and not any(r["cluster"] in text for r in rmap.values()),
                    "source_metadata_masked", name)
            require(packet["shared_seed_program"] == {"name": "shared_seed_v06r2",
                    "features": best["program"]["features"], "rule": best["program"]["rule"], "rationale": ""}
                    and packet["shared_seed_macro_feedback"] == {k: best["kernel_summary"][k] for k in
                    ("macro_quality_exact", "macro_work_exact")}, "seed_code_objective_work_identical", name)
            require(packet["limits"] == {"additional_features": 6, "expression_nodes_per_feature": 48,
                    "expression_depth_per_feature": 8, "rule_characters": 2000,
                    "rule_AST_nodes": 256, "program_slots": 8}, "unchanged_grammar_limits", name)
            require([c["case"] for c in packet["examples"]] == list(mapping.values()), "same_six_cases_order", name)
            for c in packet["examples"]:
                sid = next(s for s, m in mapping.items() if m == c["case"])
                r, g = rmap[sid], rmap[sid]["graph"]
                nodes = sorted(g["contacts"], key=lambda n: n["id"])
                expect_nodes = [{"id": n["id"], "weight": n["weight"], "duration": n["end"]-n["start"]} for n in nodes]
                require(c["graph"]["nodes"] == expect_nodes
                        and sorted(map(tuple, c["graph"]["edges"])) == sorted(map(tuple, g["edges"]))
                        and c["fixed"] == r["fixed"] and c["excluded"] == r["excluded"],
                        "exact_original_graph_weights_durations_edges_boundary", name + "/" + sid)
                require(c["degree_repair_feedback"] == projection(feedback[sid])
                        and c["shared_seed_repair_feedback"] == projection(seedrows[sid]),
                        "saved_degree_seed_feedback_not_newmeasurement", name + "/" + sid)
            if arm == "objective":
                # A numeric timing receipt can incidentally contain the digits
                # 594. Such digits are not disclosure of the relation count.
                forbidden = ("certified_relations", "explicit_equality_joins", "scalar_fit", "strict_passed",
                             "quotient", "acyclic", "ineligible", "equality_joins")
                require(not any(w in text.lower() for w in forbidden), "objective_no_gate_fit_label_disclosure", name)
            else:
                relations = [{"label_id": "r%03d" % i, "case": mapping[k[0]],
                    "preferred": k[1], "other": k[2], "lower_exact": strict[k]["lower_exact"],
                    "upper_exact": strict[k]["upper_exact"],
                    "scope": "preferred-minus-other full-residual conditional completion difference at the explicit shown F/X boundary; not a restricted-patch pivot guarantee"}
                    for i, k in enumerate(selected)]
                require(packet["certified_relations"] == relations, "eleven_sound_original_signed_bounds", name)
                if arm == "relations":
                    require("explicit_equality_joins" not in packet and "representation_instruction" not in packet,
                            "relations_no_explicit_witness_feedback", name)
                else:
                    explicit = packet["explicit_equality_joins"]
                    require(len(explicit) == 1 and explicit[0]["kind"] == "directed_cycle"
                            and explicit[0]["interface"]["demanded_additional_features"] == best["demanded_features"],
                            "genuine_two_arc_cycle_full_demanded_mask", name)
                    for old, new in zip(raw["interface"]["quotient"]["structural_witnesses"][0]["equality_joins"],
                                        explicit[0]["equality_joins"]):
                        sid = "v06_public32|MANN_a9_unit"
                        n, p = old["negative"][len(sid)+1:], old["positive"][len(sid)+1:]
                        verified = prior["actual_two_arc_information_obstruction"]["actions"]
                        require(new["negative"] == mapping[sid] + "|" + n
                                and new["positive"] == mapping[sid] + "|" + p
                                and new["negative_vector"] == verified[n]["full_declared_vector"]
                                and new["positive_vector"] == verified[p]["full_declared_vector"]
                                and new["negative_vector"] == new["positive_vector"],
                                "independently_proved_full_vector_join_source_identity", name)
    first = packets["block_0_witness"]
    for name, p in packets.items():
        require(all(p[k] == first[k] for k in common_names), "all_three_arms_identical_common_payload", name)
    w, r = packets["block_0_witness"], packets["block_0_relations"]
    for k in ("certified_relations", "shared_seed_scalar_fit_feedback", "authoring_objective", "label_scope"):
        require(w[k] == r[k], "W_R_identical_labels_fit_gate_instructions", k)
    wrdiff = set(w) ^ set(r)
    require(wrdiff == {"explicit_equality_joins", "representation_instruction"},
            "only_explicit_witness_fields_added_to_W")
    report = {"version": "independent_R2_pre_generation_packet_audit_v06_002",
        "total_checks": sum(checks.values()), "checks": dict(checks), "errors": errors, "error_count": len(errors),
        "metadata": {"study": str(study.relative_to(ROOT)).replace("\\", "/"),
            "R1_audit_sha256": AUDIT_SHA, "approved_selection_roles_sha256": PLAN_SHA,
            "draft_protocol_sha256": digest(study / "draft_protocol.json"),
            "preparation_receipt_sha256": digest(study / "preparation_receipt.json"),
            "seed_selection_sha256": digest(study / "seed_selection.json"),
            "training_evidence_sha256": digest(study / "training_evidence.json"),
            "audit_script_sha256": digest(__file__)},
        "summary": {"seed": best["id"], "cases": len(states), "shown_strict_labels": len(selected),
            "cycle_arcs": len(mandatory), "concrete_joins": 2, "packets": len(packets), "fixed_raw_positions": 120,
            "W_R_common_labels_and_gate": True, "objective_labels_gate_fit_absent": True,
            "original_R1_ready_for_TEST": False, "TEST_queries": 0, "authoring_or_assessment_called": False},
        "scope": ["Frozen R1-selected warm seed and counterexample frontier are adaptive TRAIN feedback, not new independent observations.",
            "Old independently verified full vectors and certificate bounds are byte-bound; no production oracle or candidate evaluation is run.",
            "This audit verifies the prepared draft. Later finalization/transport hashes require their own freeze before authoring."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": report["total_checks"], "errors": errors, "summary": report["summary"],
                      "audit_sha256": digest(output)}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    audit(ROOT / a.study, ROOT / a.out)
