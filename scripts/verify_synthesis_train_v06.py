"""Independent frozen R1 TRAIN audit, without production study reexecution.

Reconstructs demanded/full interfaces, exact feature quotients, strict scalar
fit, every saved feasible initializer/patch/commit, clique proofs, macro
quality/work and fixed selectors. Independent typed-expression/graph helpers
are reused; original scorer, oracle, repair and assessment modules are never
imported or called. Saved costs are audited receipts, never remeasured.
"""
from __future__ import annotations

import argparse
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
from scripts.verify_matched_llm_v05 import (
    BASE, FeatureView, boundary, canonical, normalized_program, quotient, rank, rule_code,
)
from scripts.verify_public_alias_v05 import view, graph_digest, exact_vector, exact_alpha

RUN = ROOT / "experiments/discovery/v06_synthesis_server_001"
ARCHIVE = ROOT / "experiments/runs/v06/synthesis_train_server_v06_001.tar.gz"
CAPSULE = ROOT / "experiments/source_snapshots/v06/synthesis_train_server_v06_001_source.zip"
ARCHIVE_SHA = "c6b3b754aa0af36c769a4865e5f935085136f025d88665f079835dfc445f89d9"
CAPSULE_SHA = "7b4a757eab641e808ab7d0cc0542f9442d6e7a4413f3f45230b48847294490b1"
ARMS = ("witness", "relations", "objective")


def digest(path):
    h = sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def feasible(nodes, adj, chosen, fixed=(), excluded=()):
    chosen = list(chosen)
    s = set(chosen)
    return (len(chosen) == len(s) and s <= nodes.keys() and set(fixed) <= s
            and not s & set(excluded) and all(not adj[v] & s for v in s))


def exact_value(nodes, chosen):
    return sum((Fraction(nodes[v]["weight"]) for v in chosen), Fraction())


def score_lazy(program, state, node):
    """Independent reference evaluator honoring Python branch short-circuiting."""
    expressions = {f["name"]: f["expression"] for f in program["features"]}
    base = state.base(node)

    class Locals(dict):
        def __missing__(self, key):
            if key in base:
                value = base[key]
            else:
                value = state.operation(expressions[key], node)
            self[key] = value
            return value

    code = rule_code(program["rule"], BASE + tuple(expressions))
    value = float(eval(code, {"__builtins__": {}}, Locals(min=min, max=max, abs=abs)))
    if not math.isfinite(value) or abs(value) > 1e15:
        raise ValueError("Nonfinite/out-of-range independent local priority")
    return value


def interface(program, records, labels):
    names = {f["name"] for f in program["features"]}
    demanded = set(rule_code(program["rule"], BASE + tuple(names)).co_names) & names
    vectors, full_vectors, requirements, checks = {}, {}, [], []
    for record in sorted(records, key=lambda r: r["id"]):
        state = FeatureView(record["graph"], record["fixed"], record["excluded"])
        strict = [q for q in labels[record["id"]]["rows"] if q["difference"]["status"] == "strict"]
        cache = {}
        for v in sorted({q[k] for q in strict for k in ("a", "b")}):
            values = state.features(program, v)
            cache[v] = (values, rank(program, values))
            oid = record["id"] + "|" + v
            full_vectors[oid] = values
            vectors[oid] = {k: val for k, val in values.items() if k in BASE or k in demanded}
        for index, q in enumerate(strict):
            p = q["difference"]["preferred"]
            n = q["b"] if p == q["a"] else q["a"]
            requirements.append({"preferred": record["id"] + "|" + p,
                "other": record["id"] + "|" + n, "state": record["id"], "query_index": index})
            ps, ns = cache[p][1], cache[n][1]
            actual_alias = q["base_alias_by_side"][0 if not record["paired"] or record["side"] == "left" else 1]
            checks.append({"state": record["id"], "a": q["a"], "b": q["b"], "preferred": p,
                "score_preferred": ps, "score_other": ns, "passed": ps > ns + 1e-8,
                "score_tie": ps == ns, "query_kind": q["kind"], "actual_base_alias": actual_alias})
    q = quotient(vectors, requirements)
    full_q = quotient(full_vectors, requirements)
    return {"demanded_features": sorted(demanded), "strict_total": len(checks),
        "strict_passed": sum(r["passed"] for r in checks),
        "alias_strict_total": sum(r["actual_base_alias"] for r in checks),
        "alias_strict_passed": sum(r["actual_base_alias"] and r["passed"] for r in checks),
        "strict_checks": checks, "quotient": q, "declared_quotient": full_q,
        "full_observed_consistency": not q["contradictory"] and all(r["passed"] for r in checks)}, vectors, full_vectors, requirements


def audit(output):
    began = time.perf_counter()
    checks, errors, totals = Counter(), [], Counter()
    row_summaries = {"llm": [], "controls": []}
    timings, status_counts, exact_patch_cache, priority_cache = {}, {}, {}, {}

    def require(ok, kind, where):
        checks[kind] += 1
        if not ok:
            errors.append({"kind": kind, "where": where})

    require(digest(ARCHIVE) == ARCHIVE_SHA, "immutable_original_result_archive", "archive")
    require(digest(CAPSULE) == CAPSULE_SHA, "immutable_original_source_capsule", "capsule")
    extraction = load(RUN / "EXTRACTION_RECEIPT.json")
    registration = load(RUN / "registration.json")
    require(extraction["archive_sha256"] == ARCHIVE_SHA and extraction["original_bytes_preserved"], "extraction_binding", "extraction")
    with tarfile.open(ARCHIVE, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        require(len(members) == len(extraction["files_sha256"]), "complete_result_archive_member_inventory", "archive")
        for m in members:
            rel = Path(m.name).relative_to("synthesis_train_server_v06_001").as_posix()
            h = sha256()
            f = tar.extractfile(m)
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
            require(h.hexdigest() == extraction["files_sha256"][rel] == digest(RUN / rel), "unchanged_extracted_result_bytes", rel)
    with zipfile.ZipFile(CAPSULE) as z:
        require(set(z.namelist()) == set(registration["file_sha256"]), "complete_source_capsule_inventory", "capsule")
        for name, expected in registration["file_sha256"].items():
            require(sha256(z.read(name)).hexdigest() == expected == digest(ROOT / name), "source_capsule_current_input_identity", name)
    require(registration["source_zip_sha256"] == CAPSULE_SHA
            and registration["assessment_split"] == "train" and registration["TEST_accessed"] is False
            and registration["all15_raw_sessions_frozen"] and registration["all120_raw_slots_retained"],
            "registered_train_only_15freeze_120slots", "registration")
    author_audit = load(ROOT / "experiments/analysis/v06/authoring_reviewed_audit_v06_001.json")
    require(not author_audit["errors"] and author_audit["error_count"] == 0
            and author_audit["raw_slot_count"] == 120, "independent_authoring_reviewed_receipt", "authoring")
    require(registration["authoring_audit_sha256"] == digest(ROOT / "experiments/analysis/v06/authoring_reviewed_audit_v06_001.json"), "authoring_audit_byte_binding", "authoring")
    raw_bank = author_audit["raw_slot_static_inventory"]
    saved_bank = load(RUN / "llm/bank.json")
    require(saved_bank == raw_bank, "all120_static_bank_positions_identity", "bank")
    raw_map = {r["id"]: r for r in raw_bank}
    control_proto = load(ROOT / "experiments/discovery/v06_control_assessment_001/protocol.json")
    controls = {r["id"]: r for r in control_proto["entries"]}
    require(len(controls) == 64 and len({r["deployment_AST_sha256"] for r in controls.values()}) == 16
            and control_proto["independent_authoring_draws"] is False, "fixed16_ASTs_64_repeated_slots", "controls")
    parent = load(RUN / "llm/parent_protocol.json")
    cfg = parent["kernel_config"]
    frame_path = ROOT / "experiments/discovery/v06_authoring_001/training_evidence.json"
    frame = load(frame_path)
    records = frame["records"]
    rmap = {r["id"]: r for r in records}
    labels = {r["id"]: r for r in frame["labels"]}
    require(digest(frame_path) == parent["training_evidence_sha256"], "frozen_training_frame_identity", "frame")
    require(len(records) == len(rmap) == 120 and len(labels) == 120
            and all(r["split"] == "train" for r in records), "120_TRAIN_only_states", "frame")
    require(sum(q["difference"]["status"] == "strict" for r in labels.values() for q in r["rows"]) == 594,
            "all594_certified_strict_relations", "labels")
    evidence_audit = load(ROOT / "experiments/analysis/v06/evidence_train_audit_v06_001.json")
    require(not evidence_audit["errors"] and digest(ROOT / "experiments/analysis/v06/evidence_train_audit_v06_001.json")
            == parent["independent_train_evidence_audit_sha256"], "previous_independent_full_label_proof_binding", "labels")
    state_views = {}
    for r in records:
        require(graph_digest(r["graph"]) == r["graph_digest"], "frozen_train_graph_digest", r["id"])
        n, _, adj = view(r["graph"])
        legal = boundary(n, adj, r["fixed"], r["excluded"])
        state_views[r["id"]] = (n, adj, legal)

    def verify_witnesses(saved, vectors, requirements, where):
        for w in saved["structural_witnesses"]:
            arcs, joins = w["requirements"], w["equality_joins"]
            require(bool(arcs) and len(arcs) == len(joins), "complete_saved_cycle_joins", where)
            for i, (arc, join) in enumerate(zip(arcs, joins)):
                idx = arc["requirement_index"]
                require({k: arc[k] for k in requirements[idx]} == requirements[idx], "cycle_arc_is_original_certified_requirement", where)
                n, p = arc["other"], arcs[(i + 1) % len(arcs)]["preferred"]
                require(join["negative"] == n and join["positive"] == p
                        and join["negative_vector"] == vectors[n] and join["positive_vector"] == vectors[p]
                        and exact_vector(vectors[n]) == exact_vector(vectors[p]), "exact_saved_cycle_equality_join", where)

    def verify_kernel(record, result, program, where):
        nodes, adj, legal = state_views[record["id"]]
        fixed, excluded = set(record["fixed"]), set(record["excluded"])
        require(result["config"] == cfg["repair_config"] and result["declared_seconds"] == cfg["seconds"]
                and result["deadline_clock"] == cfg["clock"] and result["priority"] == "program",
                "identical_shared_kernel_configuration_budget", where)
        require(result["completed"] and result["feasible"] and result["incumbent_available"]
                and result["error"] is None and result["fallback_used"] is False
                and result["online_model_calls"] == result["conditional_oracle_calls"] == 0
                and result["exact_optimum_claimed"] is False, "feasible_completed_no_fallback_model_oracle_globalopt", where)
        require(feasible(nodes, adj, result["selected"], fixed, excluded), "final_selected_original_graph_feasibility", where)
        require(Fraction(result["value_exact"]) == exact_value(nodes, result["selected"])
                and result["value"] == math.fsum(nodes[v]["weight"] for v in sorted(result["selected"])), "exact_final_reward", where)
        incumbent, active = set(fixed), set(legal) - fixed
        for v in fixed:
            active -= adj[v]
        for q in result["initializer_trace"]:
            chosen = min(active, key=lambda v: (-Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & active)), v))
            score = Fraction(nodes[chosen]["weight"]) / max(1, len(adj[chosen] & active))
            require(q["selected"] == chosen and q["available"] == len(active)
                    and Fraction(q["score_exact"]) == score, "every_exact_common_initializer_argmax", where)
            incumbent.add(chosen)
            active -= {chosen} | adj[chosen]
        require(not active and result["initialization_complete"] and sorted(incumbent) == result["initial_selected"]
                and exact_value(nodes, incumbent) == Fraction(result["initial_value_exact"]), "complete_shared_initializer_identity", where)
        require(Fraction(result["starting_value_exact"]) == exact_value(nodes, fixed), "original_boundary_starting_reward", where)
        global_scores = {v: Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & legal)) for v in legal}
        commits, patch_nodes = 0, 0
        for p in result["patch_trace"]:
            totals["saved_patch_traces"] += 1
            destroy = set(p["destroy"])
            outside = incumbent - destroy
            full = set(nodes) - outside - excluded
            for v in outside:
                full -= adj[v]
            require(destroy <= incumbent and not destroy & fixed and len(destroy) <= cfg["repair_config"]["max_destroy"]
                    and p["target"] in legal - incumbent
                    and adj[p["target"]] & incumbent <= destroy, "legal_movable_destroy_and_target_blockers", where)
            require(Fraction(p["incumbent_patch_exact"]) == exact_value(nodes, destroy), "exact_destroy_weight", where)
            patch = set(p["patch"])
            retained = set(destroy)
            if len(retained) < cfg["repair_config"]["max_patch_vertices"]:
                retained.add(p["target"])
            extra = sorted(full - retained, key=lambda v: (-global_scores[v], v))
            expected_patch = retained | set(extra[:cfg["repair_config"]["max_patch_vertices"] - len(retained)])
            require(destroy <= patch <= full and patch == expected_patch
                    and len(patch) <= cfg["repair_config"]["max_patch_vertices"]
                    and p["full_region_size"] == len(full) and p["restricted"] == (patch != full),
                    "exact_shared_D_preserving_patch_restriction", where)
            replacement = p["local_selected"]
            require(set(replacement) <= patch and feasible(nodes, adj, replacement)
                    and Fraction(p["lower_exact"]) == exact_value(nodes, replacement)
                    and Fraction(p["lower_exact"]) >= exact_value(nodes, destroy), "feasible_local_lower_witness_and_D_seed", where)
            cover = p["root_clique_cover"]
            flattened = [v for group in cover for v in group]
            require(len(flattened) == len(set(flattened)) and set(flattened) == patch
                    and all(g and all(b in adj[a] for i, a in enumerate(g) for b in g[i + 1:]) for g in cover),
                    "root_clique_partition_sound_full_patch_cover", where)
            root_u = sum((max(Fraction(nodes[v]["weight"]) for v in group) for group in cover), Fraction())
            require(root_u == Fraction(p["root_upper_exact"]) and root_u >= Fraction(p["lower_exact"]), "exact_root_clique_upper_envelope", where)
            if p["restricted_exact"]:
                require(Fraction(p["upper_exact"]) == Fraction(p["lower_exact"]), "restricted_exact_interval_identity", where)
                if Fraction(p["lower_exact"]) != root_u:
                    key = (record["graph_digest"], tuple(sorted(patch)))
                    if key not in exact_patch_cache:
                        exact_patch_cache[key] = exact_alpha(nodes, adj, patch, max_states=1000000)
                    optimum, expanded = exact_patch_cache[key]
                    require(Fraction(p["lower_exact"]) == optimum and p["upper_method"] == "exhaustive_restricted_search",
                            "independent_small_patch_exact_optimum", where)
                else:
                    require(p["upper_method"] == "exact_verified_clique_partition", "tight_clique_exact_proof_scope", where)
            else:
                require(Fraction(p["upper_exact"]) == root_u, "interrupted_search_keeps_root_upper", where)
            if p["priority_order"]:
                key = (canonical({k: program[k] for k in ("features", "rule")}), record["graph_digest"], tuple(sorted(patch)))
                if key not in priority_cache:
                    v = FeatureView(record["graph"], active=patch)
                    scores = {node: score_lazy(program, v, node) for node in sorted(patch)}
                    priority_cache[key] = sorted(patch, key=lambda node: (-scores[node], node))
                require(p["priority_order"] == priority_cache[key], "saved_local_programme_full_priority_order", where)
                degree_order = sorted(patch, key=lambda v: (-Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & patch)), v))
                require(p["common_degree_order"] == degree_order, "saved_local_shared_degree_order", where)
                for g in p["greedy_passes"]:
                    order = priority_cache[key] if g["order"] == "priority" else degree_order
                    available, chosen = set(patch), set()
                    for node in order:
                        if node in available:
                            chosen.add(node)
                            available -= {node} | adj[node]
                    require(g["complete"] and Fraction(g["value_exact"]) == exact_value(nodes, chosen), "saved_two_local_greedy_lower_passes", where)
            gain = exact_value(nodes, replacement) - exact_value(nodes, destroy)
            require(Fraction(p["gain_exact"]) == gain and p["committed"] == (gain > 0), "exact_strict_positive_gain_commit_rule", where)
            if p["committed"]:
                new = outside | set(replacement)
                require(feasible(nodes, adj, new, fixed, excluded) and exact_value(nodes, new) > exact_value(nodes, incumbent), "global_feasible_monotone_commit", where)
                incumbent = new
                commits += 1
            require(0 <= p["search_nodes"] <= cfg["repair_config"]["node_budget_per_patch"], "patch_search_node_cap", where)
            patch_nodes += p["search_nodes"]
        require(sorted(incumbent) == result["selected"] and commits == result["improvements"]
                and len(result["patch_trace"]) == result["patches_attempted"], "every_saved_patch_replay_final_identity", where)
        meter = result["meter"]
        require(meter["search_nodes"] == patch_nodes <= cfg["repair_config"]["max_search_nodes"], "global_search_node_receipt", where)
        for name in ("feature", "repair"):
            require(type(meter[name + "_work"]) is int and meter[name + "_work"] >= 0
                    and all(type(v) is int and v >= 0 for v in meter[name + "_primitives"].values())
                    and sum(meter[name + "_primitives"].values()) == meter[name + "_work"], "charged_operation_proxy_breakdown_identity", where)
        require(all(math.isfinite(result[k]) and result[k] >= 0 for k in ("wall_seconds", "cpu_seconds"))
                and not result["global_budget_exhausted"], "executed_timing_receipt_not_remeasured", where)
        totals["verified_kernel_assignments"] += 1

    interface_cache = {}
    seed_record = None
    for group, bank in (("llm", raw_map), ("controls", controls)):
        seen, statuses = set(), Counter()
        with (RUN / group / "candidate_results.jsonl").open(encoding="utf-8") as f:
            for index, line in enumerate(f):
                row = json.loads(line)
                identity = row["id"]
                require(identity in bank and identity not in seen, "one_real_assessment_per_original_position", identity)
                seen.add(identity)
                original = bank[identity]
                require(all(row[k] == v for k, v in original.items() if k not in ("error", "error_type")), "unchanged_raw_static_candidate_identity", identity)
                statuses[row["assessment_status"]] += 1
                if row["status"] != "static_valid":
                    require(not row["eligible"] and not row["kernel_rows"]
                            and row["assessment_status"] == row["status"], "failed_slot_no_hidden_candidate_or_fallback", identity)
                    row_summaries[group].append({k: row[k] for k in ("id", "block", "arm", "slot", "eligible", "assessment_status")})
                    continue
                program = normalized_program(row["program"])
                ast_hash = canonical({k: program[k] for k in ("features", "rule")})
                require(ast_hash == row["deployment_AST_sha256"] and canonical(program) == row["program_sha256"], "canonical_program_AST_binding", identity)
                if ast_hash not in interface_cache:
                    interface_cache[ast_hash] = interface(program, records, labels)
                reference, vectors, full_vectors, requirements = interface_cache[ast_hash]
                saved = row["interface"]
                for k in ("demanded_features", "strict_total", "strict_passed", "alias_strict_total", "alias_strict_passed", "full_observed_consistency"):
                    require(saved[k] == reference[k], "exact_demand_mask_scalar_fit_summary", identity + ":" + k)
                require(saved["strict_checks"] == reference["strict_checks"], "all594_independent_numeric_scalar_preferences", identity)
                for name, vv in (("quotient", vectors), ("declared_quotient", full_vectors)):
                    require(all(saved[name][k] == reference[name][k] for k in reference[name]), "independent_full_exact_feature_quotient", identity + ":" + name)
                    verify_witnesses(saved[name], vv, requirements, identity + ":" + name)
                require(len(row["kernel_rows"]) == 120 and {q["id"] for q in row["kernel_rows"]} == set(rmap), "all120_real_TRAIN_kernel_assignments", identity)
                family_q, family_work = defaultdict(list), defaultdict(list)
                valid = True
                for q in row["kernel_rows"]:
                    r = rmap[q["id"]]
                    require(q["family"] == r["family"], "family_source_assignment_identity", identity)
                    verify_kernel(r, q["result"], program, identity + "|" + q["id"])
                    valid = valid and q["result"]["completed"] and q["result"]["feasible"]
                    total_weight = sum((Fraction(c["weight"]) for c in r["graph"]["contacts"]), Fraction())
                    family_q[r["family"]].append(Fraction(q["result"]["value_exact"]) / total_weight)
                    family_work[r["family"]].append(q["result"]["meter"]["feature_work"] + q["result"]["meter"]["repair_work"])
                fq = {k: sum(v, Fraction()) / len(v) for k, v in family_q.items()}
                fw = {k: Fraction(sum(v), len(v)) for k, v in family_work.items()}
                summary = {"macro_quality_exact": str(sum(fq.values(), Fraction()) / len(fq)),
                    "macro_work_exact": str(sum(fw.values(), Fraction()) / len(fw)),
                    "family_reward_over_total_weight": {k: str(v) for k, v in fq.items()},
                    "family_work": {k: str(v) for k, v in fw.items()}}
                require(row["kernel_summary"] == summary, "exact_eight_family_quality_work_and_denominator", identity)
                eligible = valid and not reference["quotient"]["contradictory"]
                require(row["eligible"] == eligible and row["assessment_status"] == ("assessed" if valid else "kernel_execution_error"), "eligibility_from_unchanged_gate_and_execution", identity)
                small = {k: row[k] for k in ("id", "block", "arm", "slot", "program", "program_sha256", "eligible", "assessment_status")}
                small.update(strict_passed=reference["strict_passed"], alias_strict_passed=reference["alias_strict_passed"],
                    quotient=reference["quotient"], demanded_features=reference["demanded_features"], kernel_summary=summary)
                row_summaries[group].append(small)
                if identity == "block_2_relations:3":
                    seed_record = (program, reference, vectors, full_vectors, requirements, saved)
                if (index + 1) % 8 == 0:
                    print(json.dumps({"audit_group": group, "positions_verified": index + 1,
                        "kernel_rows_verified": totals["verified_kernel_assignments"], "errors_so_far": len(errors)}), flush=True)
        require(seen == set(bank), "all_original_positions_coverage", group)
        status_counts[group] = dict(statuses)

    def skey(r):
        return (-r["strict_passed"], -Fraction(r["kernel_summary"]["macro_quality_exact"]),
                Fraction(r["kernel_summary"]["macro_work_exact"]), r["slot"])

    matched = [1, 2, 3, 4]
    selected = load(RUN / "llm/selection.json")
    expected_winners, empty, prefix, unconditional_empty = [], [], [], []
    for block in range(5):
        for arm in ARMS:
            rows = sorted((r for r in row_summaries["llm"] if r["block"] == block and r["arm"] == arm), key=lambda r: r["slot"])
            eligible = [r for r in rows if r["eligible"]]
            winner = min(eligible, key=skey) if eligible else None
            if not winner:
                unconditional_empty.append({"block": block, "arm": arm})
            if block in matched:
                if winner:
                    expected_winners.append({k: winner[k] for k in ("id", "block", "arm", "slot", "program", "program_sha256")})
                else:
                    empty.append({"block": block, "arm": arm})
            for n in range(1, 9):
                ee = [r for r in rows[:n] if r["eligible"]]
                best = min(ee, key=skey) if ee else None
                prefix.append({"block": block, "arm": arm, "raw_slots": n,
                    "winner_id": best["id"] if best else None,
                    "strict_passed": best["strict_passed"] if best else None,
                    "first_eligible_original_slot": min(r["slot"] for r in ee) if ee else None})
    require(selected["programs"] == expected_winners and selected["empty_matched_cells"] == empty
            and selected["all_unconditional_empty_cells"] == unconditional_empty
            and selected["all_raw_prefixes"] == prefix, "exact_lexicographic_real_winners_emptycells_allprefixes", "selection")
    require(len(expected_winners) == 9 and not selected["all_cells_have_genuine_winner"]
            and selected["no_fallback"] and selected["test_accessed"] is False
            and selected["matched_transport_complete_blocks"] == matched, "nine_winner_genuine12_barrier_stops_TEST", "selection")
    require(empty == [{"block": 1, "arm": "relations"}, {"block": 2, "arm": "objective"}, {"block": 4, "arm": "witness"}],
            "three_different_arm_empty_matched_cells_retained", "selection")
    control_selected = load(RUN / "controls/selection.json")
    for s in control_selected["selections"]:
        rows = [r for r in row_summaries["controls"] if r["block"] == s["block"] and r["arm"] == s["bank"]]
        joint = [r for r in rows if r["eligible"]]
        qbest = min(rows, key=lambda r: (-Fraction(r["kernel_summary"]["macro_quality_exact"]), Fraction(r["kernel_summary"]["macro_work_exact"]), r["slot"]))
        fields = ("id", "block", "arm", "slot", "program", "program_sha256", "eligible")
        require(not joint and s["joint_eligible_winner"] is None and s["joint_eligible_slots"] == 0
                and s["quality_completed_slots"] == 8 and s["quality_only_baseline"] == {k: qbest[k] for k in fields}
                and s["used_for_performance"] == (s["block"] == 0), "separate_fixed_control_joint_gate_qualityonly_repeat0_selection", str(s["block"]) + s["bank"])

    # Independent full-residual exact optima for the actual two-arc obstruction.
    program, ref, vectors, full_vectors, requirements, saved = seed_record
    state = rmap["v06_public32|MANN_a9_unit"]
    nodes, adj, active = state_views[state["id"]]
    actions, values = ("34", "5", "7", "35"), {}
    proof_states = 0
    for node in actions:
        optimum, states = exact_alpha(nodes, adj, active - {node} - adj[node], max_states=1000000)
        value = exact_value(nodes, state["fixed"]) + Fraction(nodes[node]["weight"]) + optimum
        oid = state["id"] + "|" + node
        values[node] = {"conditional_completion_exact": str(value), "residual_optimum_exact": str(optimum),
            "verifier_states": states, "demanded_vector": vectors[oid], "full_declared_vector": full_vectors[oid]}
        proof_states += states
    require({k: v["conditional_completion_exact"] for k, v in values.items()} == {"34": "15", "5": "14", "7": "15", "35": "14"},
            "independent_four_action_full_residual_conditional_optima", "MANN_a9")
    for namespace, vv in (("demanded", vectors), ("full_declared", full_vectors)):
        oid = lambda n: state["id"] + "|" + n
        require(exact_vector(vv[oid("5")]) == exact_vector(vv[oid("7")])
                and exact_vector(vv[oid("35")]) == exact_vector(vv[oid("34")])
                and exact_vector(vv[oid("34")]) != exact_vector(vv[oid("5")])
                and exact_vector(vv[oid("7")]) != exact_vector(vv[oid("35")]), "genuine_two_arc_cycle_beyond_direct_alias", namespace)
    require(ref["strict_passed"] == 584 and ref["alias_strict_passed"] == 86 and ref["quotient"]["contradictory"], "best_ineligible_seed_finite_fit_information_obstruction", "seed")
    for a, b, preferred in (("34", "5", "34"), ("35", "7", "7")):
        q = next(q for q in labels[state["id"]]["rows"] if q["a"] == a and q["b"] == b)
        difference = Fraction(values[a]["conditional_completion_exact"]) - Fraction(values[b]["conditional_completion_exact"])
        require(Fraction(q["difference"]["lower_exact"]) == difference == Fraction(q["difference"]["upper_exact"])
                and q["difference"]["preferred"] == preferred and q["difference"]["status"] == "strict", "sound_exact_original_cycle_arc_bounds", a + "|" + b)

    for group in ("llm", "controls"):
        complete = load(RUN / group / "complete.json")
        require(complete["eligible"] == sum(r["eligible"] for r in row_summaries[group])
                and complete["assessment_status"] == status_counts[group]
                and complete["selection_sha256"] == digest(RUN / group / "selection.json")
                and complete["TEST_queries"] == 0, "complete_receipt_counts_selection_binding_noTEST", group)
    phases = load(RUN / "phase_receipts.json")
    execution = load(RUN / "server_execution_receipt.json")
    host = load(RUN / "host_receipt.json")
    require(len(phases) == 2 and phases[0]["phase"] == "LLM" and phases[1]["phase"] == "controls"
            and all(p["exit_code"] == 0 and not p["whole_phase_guard_triggered"] and p["no_retry"] for p in phases)
            and execution["execution_complete"] and execution["TEST_queries"] == 0
            and execution["online_model_calls"] == execution["oracle_calls"] == 0, "two_complete_sequential_server_phases_no_reexecution_orTEST", "execution")
    completion_time = datetime.fromisoformat(load(RUN / "llm/supplement_authoring_completion.json")["completed_utc"]).timestamp()
    require(host["timestamp_unix"] > completion_time and host["workers"] == 8
            and host["registration_sha256"] == digest(RUN / "registration.json"), "execution_after_all15_authoring_freezes", "host")
    totals["independent_exact_patch_queries"] = len(exact_patch_cache)
    totals["independent_exact_patch_verifier_states"] = sum(v[1] for v in exact_patch_cache.values())
    totals["independent_local_priority_orders"] = len(priority_cache)
    totals["conditional_counterexample_verifier_states"] = proof_states
    summary = {
        "all_llm_slots": len(row_summaries["llm"]), "all_control_slots": len(row_summaries["controls"]),
        "llm_eligible_unconditional": sum(r["eligible"] for r in row_summaries["llm"]),
        "llm_eligible_conditional_matched": sum(r["eligible"] for r in row_summaries["llm"] if r["block"] in matched),
        "control_eligible": sum(r["eligible"] for r in row_summaries["controls"]),
        "actual_matched_winners": len(expected_winners), "empty_matched_cells": empty,
        "ready_for_TEST": False, "quality_exact_values": sorted({r["kernel_summary"]["macro_quality_exact"] for r in row_summaries["llm"] + row_summaries["controls"] if "kernel_summary" in r})}
    report = {"version": "independent_frozen_R1_TRAIN_audit_v06_001", "total_checks": sum(checks.values()),
        "checks": dict(checks), "errors": errors, "error_count": len(errors), "totals": dict(totals),
        "metadata": {"archive_sha256": ARCHIVE_SHA, "source_zip_sha256": CAPSULE_SHA,
            "registration_sha256": digest(RUN / "registration.json"), "extraction_receipt_sha256": digest(RUN / "EXTRACTION_RECEIPT.json"),
            "training_evidence_sha256": digest(frame_path), "authoring_audit_sha256": registration["authoring_audit_sha256"],
            "llm_results_sha256": digest(RUN / "llm/candidate_results.jsonl"), "control_results_sha256": digest(RUN / "controls/candidate_results.jsonl"),
            "llm_selection_sha256": digest(RUN / "llm/selection.json"), "control_selection_sha256": digest(RUN / "controls/selection.json"),
            "audit_script_sha256": digest(__file__), "independent_helpers_sha256": {n: digest(ROOT / n) for n in
                ("scripts/verify_matched_llm_v05.py", "scripts/verify_public_alias_v05.py")}},
        "summary": summary, "status_counts": status_counts, "candidate_summaries": row_summaries,
        "actual_two_arc_information_obstruction": {"candidate_id": "block_2_relations:3", "state": state["id"],
            "graph_digest": state["graph_digest"], "strict_fit": "584/594", "actual_alias_fit": "86/90",
            "arcs": [["34", "5"], ["7", "35"]], "equality_joins": [["5", "7"], ["35", "34"]],
            "actions": values, "scope": "Observed exact feature input insufficiency for every deterministic pointwise scalar; not physical incidence or successful LLM repair"},
        "verification_wall_seconds": time.perf_counter() - began,
        "scope": ["Frozen original TRAIN results are inspected; original assessors/scorers/repair/oracle modules are never imported or executed.",
            "Independent feature interpretation and exact recurrences are verification computations, not new candidate optimization or scientific outcomes.",
            "All saved costs/timings are bound executed receipts; no new speed/work measurement is substituted.",
            "The demanded/full quotient, actual scalar fit and schedule quality are separate audited outcomes.",
            "R1 failed its12 genuine-program TEST barrier; nine winners cannot be deployed as a complete matched study, and no hidden fallback or weakened gate is permitted.",
            "Enumerated/fixed-bank repetitions are not independent LLM authoring draws; quality-only controls remain distinct from joint-eligible proposals.",
            "New targeted TRAIN repair must be separately registered and cannot retroactively replace R1 failure.",
            "No TEST conditional query or candidate/selection evaluation is performed by this audit."]}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": report["total_checks"], "errors": len(errors), "summary": summary,
        "audit_sha256": digest(output), "verification_seconds": report["verification_wall_seconds"]}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    audit(ROOT / a.out)
