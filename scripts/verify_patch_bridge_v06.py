"""Independent postfreeze TRAIN patch-bridge verification, never execution.

Only independent audit helpers are imported. Production scorers, search,
oracle and study modules are not imported or executed. Exact verification
uses a separate bounded memo recurrence, not a new experimental query.
Every assigned programme/state position is retained in the audit output.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_matched_llm_v05 import FeatureView, boundary, normalized_program, rule_code, BASE
from scripts.verify_public_alias_v05 import view, graph_digest, components, exact_alpha

REGISTRATION = ROOT / "experiments/discovery/v06_patch_bridge_001"
PROGRAMS = ROOT / "experiments/discovery/v06_patch_bridge_programs_frozen_001/program_inventory.json"
RELEASE = ROOT / "experiments/discovery/v06_test_release_002/TRAIN_patch_bridge_root_release_001.json"
CAPSULE = ROOT / "experiments/source_snapshots/v06/v06_TRAIN_patch_bridge_execution_001.zip"
CAPSULE_RECEIPT = ROOT / "experiments/discovery/v06_test_release_002/TRAIN_patch_bridge_capsule_receipt_001.json"
DEGREE = ROOT / "experiments/runs/v06/repair_degree_feedback_v06_001.tar.gz"
PINS = {
    "freeze": "52fba1417af9be535e2a22ff030f99c33ff715349974a7150a79cc0bab3aa347",
    "programs": "f19b64047748a673a2fcd3335abbf9dc922b404ed6d45a18a3d26a90725d9602",
    "release": "975846ae34e90d2d8efb7bdbacb6c189693ddf14544b1c5baac0c506275d8311",
    "capsule": "824f6f7ae3d4f9e88f79149794aa74842f03970278f132e8d71f7d4e70d37e77",
    "degree": "e67be3ca5c91d6d5d413c4226de6ae047f0b63673d3b951d1cfd95de62f717fc",
}
HELPERS = {
    "scripts/verify_matched_llm_v05.py": "52b331fea2214642ac50ffe3996c95a6fb9893320e50df84e1371f8fedae087b",
    "scripts/verify_public_alias_v05.py": "6b349b659bad3acfd3a9e1abbf9046a984f8f66df05068841c1ba8c076aa959a",
}
LOCAL = "restricted_patch_forced_include_with_saved_outside_incumbent_fixed"
FULL = "original_full_residual_requirement_at_original_permanent_boundary"
OUTPUT_NAMES = ("inventory.json", "config.json", "protocol.json", "freeze_receipt.json",
    "original_training_evidence.json", "program_inventory.json", "root_release.json",
    "execution.json", "labels.jsonl", "scores.jsonl", "coverage.json", "prefixes.json",
    "summary.json", "complete.json")
RESULT_PREFIX = "v06_TRAIN_patch_bridge_results_server_001"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def members(path, names, prefix=None):
    """Read without extraction; reject duplicate named files or missing members."""
    found = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            normalized = member.name.replace("\\", "/")
            name = Path(normalized).name
            if prefix is not None and normalized != prefix + "/" + name:
                continue
            if member.isfile() and name in names:
                if name in found:
                    raise ValueError("Ambiguous archive member: " + name)
                found[name] = archive.extractfile(member).read()
    if set(found) != set(names):
        raise ValueError("Missing archive members: " + str(sorted(set(names) - set(found))))
    return found


def decode(raw):
    return {name: ([json.loads(line) for line in data.splitlines() if line]
        if name.endswith(".jsonl") else json.loads(data)) for name, data in raw.items()}


class Checks:
    def __init__(self):
        self.counts, self.errors = Counter(), []

    def require(self, condition, kind, where=""):
        self.counts[kind] += 1
        if not condition:
            self.errors.append({"check": kind, "where": where})


def feasible(nodes, adj, selected, fixed=(), excluded=()):
    selected = list(selected)
    s = set(selected)
    return (len(selected) == len(s) and s <= nodes.keys() and set(fixed) <= s
        and not s & set(excluded) and all(not adj[v] & s for v in s))


def value(nodes, selected):
    return sum((Fraction(nodes[v]["weight"]) for v in selected), Fraction())


def alpha(nodes, adj, region, cache, graph_sha, ceiling=1000000):
    key = graph_sha, tuple(sorted(region))
    if key not in cache:
        cache[key] = exact_alpha(nodes, adj, region, max_states=ceiling)
    return cache[key][0]


def clique_upper(nodes, adj, region, cover):
    flat = [v for group in cover for v in group]
    if (len(flat) != len(set(flat)) or set(flat) != set(region) or
        any(not group or any(b not in adj[a] for a, b in itertools.combinations(group, 2)) for group in cover)):
        raise ValueError("Not a disjoint clique partition of the whole restricted patch")
    return sum((max(Fraction(nodes[v]["weight"]) for v in group) for group in cover), Fraction())


def fallback_cover(nodes, adj, region):
    """Rebuild the specified capped-certificate clique witness, not its search."""
    remaining, cover = set(region), []
    for v in sorted(region, key=lambda v: (-len(adj[v] & set(region)), v)):
        if v not in remaining:
            continue
        clique = [v]
        remaining.remove(v)
        for u in sorted(remaining):
            if all(u in adj[x] for x in clique):
                clique.append(u)
                remaining.remove(u)
        cover.append(clique)
    return clique_upper(nodes, adj, region, cover)


def reference_rows(evidence, state, checks):
    original = next(r for r in evidence["records"] if r["id"] == state["id"])
    labels = next(r for r in evidence["labels"] if r["id"] == state["id"])
    checks.require(original["split"] == labels["split"] == "train"
        and graph_digest(original["graph"]) == labels["graph_digest"] == state["graph_sha256"]
        and set(original["fixed"]) == set(state["permanent_fixed"])
        and set(original["excluded"]) == set(state["excluded"]), "original_reference_graph_boundary", state["id"])
    result = []
    for i, row in enumerate(labels["rows"]):
        d = row["difference"]
        if d["status"] == "strict" and {row["a"], row["b"]} <= set(state.get("patch", [])):
            result.append({"a": row["a"], "b": row["b"], "preferred": d["preferred"],
                "original_row_index": i, "lower_exact": d["lower_exact"],
                "upper_exact": d["upper_exact"], "scope": FULL})
    return result


def query_union(state, refs, config):
    nodes, _, adj = view(state["graph"])
    def key(pair):
        a, b = pair
        text = config["salt"] + "|" + state["id"] + "|" + a + "|" + b
        return b not in adj[a], sha256(text.encode()).digest(), pair
    pairs = sorted(itertools.combinations(sorted(state.get("patch", [])), 2), key=key)
    core = pairs[:config["pairs_per_patch"]]
    merged = {p: {"a": p[0], "b": p[1], "sample_rank": i,
        "competing": p[1] in adj[p[0]], "in_core_sha": True,
        "in_full_strict_bridge": False, "full_reference_rows": []} for i, p in enumerate(core)}
    for r in refs:
        p = tuple(sorted((r["a"], r["b"])))
        if p not in merged:
            merged[p] = {"a": p[0], "b": p[1], "sample_rank": None,
                "competing": p[1] in adj[p[0]], "in_core_sha": False,
                "in_full_strict_bridge": False, "full_reference_rows": []}
        merged[p]["in_full_strict_bridge"] = True
        merged[p]["full_reference_rows"].append(r["original_row_index"])
    extras = sorted(set(merged) - set(core), key=lambda p: sha256(
        (config["salt"] + "|full|" + state["id"] + "|" + p[0] + "|" + p[1]).encode()).digest())
    union = [{**merged[p], "query_rank": i} for i, p in enumerate(core + extras)]
    adjacent = sum(b in adj[a] for a, b in pairs)
    quota = {"eligible_pairs": len(pairs), "eligible_adjacent_pairs": adjacent,
        "planned_pairs": len(core), "planned_adjacent_pairs": sum(b in adj[a] for a, b in core),
        "pair_shortfall": max(0, config["pairs_per_patch"] - len(core)),
        "adjacent_quota_shortfall": max(0, config["pairs_per_patch"] - adjacent),
        "core_planned_pairs": len(core), "full_strict_surviving_requirements": len(refs),
        "full_strict_surviving_unique_pairs": sum(r["in_full_strict_bridge"] for r in union),
        "union_planned_pairs": len(union), "added_original_full_pairs": len(extras)}
    return union, quota


def check_saved_patch(state, context, row, checks, cache):
    """Reconstruct shared Degree initialization and the first materialized patch."""
    where = state["id"]
    nodes, _, adj = view(context["graph"])
    fixed, excluded = set(context["fixed"]), set(context["excluded"])
    legal = set(boundary(nodes, adj, fixed, excluded))
    checks.require(context["split"] == row["split"] == state["split"] == "train"
        and context["id"] == row["id"] == where and row["method"] == "shared_kernel_degree"
        and canonical(context) == state["context_sha256"] and canonical(row) == state["feedback_row_sha256"]
        and context["graph"] == state["graph"]
        and graph_digest(context["graph"]) == state["graph_sha256"] == row["graph_sha256"]
        and sorted(fixed) == state["permanent_fixed"] and sorted(excluded) == state["excluded"],
        "original_degree_state_and_row_byte_semantics", where)
    result = row["result"]
    if result is None:
        checks.require(state["patch_status"] == "no_result" and not state["queries"], "explicit_no_result_patch", where)
        return None
    checks.require(result["priority"] == "degree" and result["config"]["policy_scope"] == "branch",
        "original_shared_degree_branch_scope", where)
    incumbent, active = set(fixed), set(legal)
    for step in result["initializer_trace"]:
        chosen = min(active, key=lambda v: (-Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & active)), v))
        checks.require(step["selected"] == chosen and step["available"] == len(active)
            and Fraction(step["score_exact"]) == Fraction(nodes[chosen]["weight"]) / max(1, len(adj[chosen] & active)),
            "original_degree_each_initializer_argmax", where)
        incumbent.add(chosen)
        active -= {chosen} | adj[chosen]
    checks.require(not active and result["initialization_complete"]
        and sorted(incumbent) == result["initial_selected"] and feasible(nodes, adj, incumbent, fixed, excluded),
        "original_degree_complete_feasible_initializer", where)
    first = next(((i, p) for i, p in enumerate(result["patch_trace"]) if p.get("patch")), None)
    if first is None:
        checks.require(state["patch_status"] == "no_constructed_nonempty_patch" and not state["queries"], "explicit_empty_patch", where)
        return None
    i, patch = first
    checks.require(not any(p.get("committed") for p in result["patch_trace"][:i]), "no_gain_based_later_patch_choice", where)
    d, region = set(patch["destroy"]), set(patch["patch"])
    outside = incumbent - d
    full = set(boundary(nodes, adj, sorted(outside), sorted(excluded)))
    cfg = result["config"]
    global_scores = {v: Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & legal)) for v in legal}
    retained = set(d)
    if len(retained) < cfg["max_patch_vertices"]:
        retained.add(patch["target"])
    extra = sorted(full - retained, key=lambda v: (-global_scores[v], v))
    expected = retained | set(extra[:cfg["max_patch_vertices"] - len(retained)])
    checks.require(d and d <= incumbent and not d & fixed and d <= region <= full
        and region == expected and len(region) <= cfg["max_patch_vertices"]
        and len(d) <= cfg["max_destroy"] and patch["target"] in legal - incumbent
        and adj[patch["target"]] & incumbent <= d and patch["full_region_size"] == len(full)
        and patch["stage"] in ("local_search", "returned"), "exact_original_D_preserving_restriction", where)
    expected_fields = {"patch_status": "constructed", "patch_index": i, "patch_id": where + "|patch:" + str(i),
        "incumbent_before": sorted(incumbent), "outside_fixed": sorted(outside), "destroy": sorted(d),
        "patch": sorted(region), "full_free_region": sorted(full), "restricted": region != full,
        "original_trace_sha256": canonical(result["patch_trace"]), "selected_trace_sha256": canonical(patch),
        "original_trace_stage": patch["stage"], "original_priority_order_present": bool(patch.get("priority_order")),
        "snapshot_sha256": canonical({"graph_sha256": state["graph_sha256"], "outside_fixed": sorted(outside),
            "excluded": sorted(excluded), "destroy": sorted(d), "patch": sorted(region)})}
    for k, v in expected_fields.items():
        checks.require(state.get(k) == v, "saved_snapshot_identity", where + ":" + k)
    root_u = clique_upper(nodes, adj, region, patch["root_clique_cover"])
    optimum = alpha(nodes, adj, region, cache, state["graph_sha256"])
    lower, upper = Fraction(patch["lower_exact"]), Fraction(patch["upper_exact"])
    checks.require(root_u == Fraction(patch["root_upper_exact"]) and root_u >= optimum
        and set(patch["local_selected"]) <= region and feasible(nodes, adj, patch["local_selected"])
        and lower == value(nodes, patch["local_selected"]) >= value(nodes, d)
        and lower <= optimum <= upper <= root_u, "original_clique_witness_exact_patch_enclosure", where)
    checks.require(not patch["restricted_exact"] or lower == upper == optimum, "original_exact_claim_independent_optimum", where)
    return {"id": where, "patch": sorted(region), "exact_patch_optimum": str(optimum),
        "saved_root_upper_exact": str(root_u), "saved_lower_exact": str(lower), "saved_upper_exact": str(upper),
        "saved_restricted_exact": patch["restricted_exact"], "snapshot_sha256": state["snapshot_sha256"]}


def check_local_label(state, query, saved, config, checks, cache):
    where = state["id"] + "|" + query["a"] + ":" + query["b"]
    start_errors = len(checks.errors)
    nodes, _, adj = view(state["graph"])
    region, a, b = set(state["patch"]), query["a"], query["b"]
    pa = components(adj, region - {a} - adj[a])
    pb = components(adj, region - {b} - adj[b])
    checks.require(all(saved.get(k) == v for k, v in query.items()) and saved["scope"] == LOCAL
        and saved["outside_incumbent_weight_cancels"] is True
        and saved["cancelled_components"] == [list(p) for p in sorted(pa & pb)], "local_query_identity_and_exact_cancellation", where)
    lower, upper, recurrence_states = Fraction(nodes[a]["weight"]) - Fraction(nodes[b]["weight"]), Fraction(nodes[a]["weight"]) - Fraction(nodes[b]["weight"]), 0
    seen = set()
    for side, parts in (("a", pa - pb), ("b", pb - pa)):
        rows = saved["unmatched"][side]
        checks.require([r["vertices"] for r in rows] == [list(p) for p in sorted(parts)], "all_unmatched_components_exactly_once", where + "|" + side)
        for item in rows:
            part, bound = tuple(item["vertices"]), item["bound"]
            truth = alpha(nodes, adj, part, cache, state["graph_sha256"])
            lb, ub = Fraction(bound["lower_exact"]), Fraction(bound["upper_exact"])
            checks.require(set(bound["selected"]) <= set(part) and feasible(nodes, adj, bound["selected"])
                and lb == value(nodes, bound["selected"]) <= truth <= ub and bound["exact"] == (lb == ub),
                "independent_component_LB_optimum_UB", where)
            if bound["reason"] == "exact_memo_recurrence":
                checks.require(lb == ub == truth, "exhaustive_component_exact_claim", where)
            elif bound["reason"] == "recurrence_limit_sound_clique_enclosure":
                checks.require(ub == fallback_cover(nodes, adj, part), "capped_component_clique_upper_rebuilt", where)
            else:
                checks.require(False, "known_component_bound_reason", where)
            checks.require(type(bound["recurrence_states"]) is int and 0 <= bound["recurrence_states"] <= bound["state_limit"]
                <= config["recurrence_states_per_query"], "component_saved_search_count_scope", where)
            if part not in seen:
                recurrence_states += bound["recurrence_states"]
                seen.add(part)
            if side == "a":
                lower += lb; upper += ub
            else:
                lower -= ub; upper -= lb
    forced_a = Fraction(nodes[a]["weight"]) + alpha(nodes, adj, region - {a} - adj[a], cache, state["graph_sha256"])
    forced_b = Fraction(nodes[b]["weight"]) + alpha(nodes, adj, region - {b} - adj[b], cache, state["graph_sha256"])
    truth = forced_a - forced_b
    epsilon = Fraction(config["certificate_epsilon_exact"])
    preferred = a if lower > epsilon else b if upper < -epsilon else None
    status = "strict" if preferred else "exact_tie" if lower == upper == 0 else "unknown"
    checks.require(Fraction(saved["lower_exact"]) == lower <= truth <= upper == Fraction(saved["upper_exact"])
        and saved["exact"] == (lower == upper) and saved["preferred"] == preferred and saved["status"] == status,
        "sound_interval_sign_tie_unknown_unchanged", where)
    checks.require(saved["query_state_limit"] == config["recurrence_states_per_query"]
        and Fraction(saved["epsilon_exact"]) == epsilon and saved["recurrence_states"] == recurrence_states
        <= config["recurrence_states_per_query"], "query_shared_budget_receipt_not_remeasured", where)
    return {"state_id": state["id"], **query, "saved_status": status, "saved_preferred": preferred,
        "saved_lower_exact": str(lower), "saved_upper_exact": str(upper), "independent_difference_exact": str(truth),
        "independent_forced_a_exact": str(forced_a), "independent_forced_b_exact": str(forced_b),
        "scope": LOCAL, "error_count": len(checks.errors) - start_errors}


def score_independent(entry, state):
    nodes, _, adj = view(state["graph"])
    region = set(state["patch"])
    if entry["priority"] == "degree":
        return {v: Fraction(nodes[v]["weight"]) / max(1, len(adj[v] & region)) for v in sorted(region)}
    program = normalized_program(entry["program"])
    expressions = {f["name"]: f["expression"] for f in program["features"]}
    code = rule_code(program["rule"], BASE + tuple(expressions))
    snapshot = FeatureView(state["graph"], active=region)
    scores = {}
    for v in sorted(region):
        base = snapshot.base(v)
        class Lazy(dict):
            def __missing__(self, key):
                answer = base[key] if key in base else snapshot.operation(expressions[key], v)
                self[key] = answer
                return answer
        result = float(eval(code, {"__builtins__": {}}, Lazy(min=min, max=max, abs=abs)))
        if not math.isfinite(result) or abs(result) > 1e15:
            raise ValueError("Independent scorer nonfinite/out-of-range")
        scores[v] = Fraction(result)
    return scores


def expected_fit(targets, scores, margin):
    rows = []
    for r in targets:
        p = r["preferred"]
        if p is None:
            continue
        other = r["b"] if p == r["a"] else r["a"]
        diff = scores[p] - scores[other]
        rows.append({"a": r["a"], "b": r["b"], "preferred": p,
            "score_difference_exact": str(diff), "passed": diff > margin, "score_tie": diff == 0,
            "target_scope": r["scope"], "in_core_sha": r.get("in_core_sha", False),
            "in_full_strict_bridge": r.get("in_full_strict_bridge", False)})
    return {"strict_targets": len(rows), "passed": sum(r["passed"] for r in rows),
        "core_SHA_strict_targets": sum(r["in_core_sha"] for r in rows),
        "core_SHA_passed": sum(r["in_core_sha"] and r["passed"] for r in rows),
        "full_strict_pair_local_targets": sum(r["in_full_strict_bridge"] for r in rows),
        "full_strict_pair_local_passed": sum(r["in_full_strict_bridge"] and r["passed"] for r in rows), "rows": rows}


def check_score_receipts(entry, state, saved, config, checks, where, executed):
    """An executed failure is measured, not an alternative missing encoding."""
    if not executed:
        checks.require(all(saved.get(k) is None for k in ("feature_meter", "cpu_seconds", "wall_seconds")),
            "nonexecuted_missing_positions_have_no_fabricated_receipts", where)
        return
    meter = saved.get("feature_meter")
    valid_meter = (isinstance(meter, dict) and type(meter.get("feature_work")) is int
        and meter["feature_work"] >= 0 and isinstance(meter.get("feature_primitives"), dict)
        and all(type(v) is int and v >= 0 for v in meter["feature_primitives"].values()))
    checks.require(valid_meter, "mandatory_executed_feature_meter_and_nonnegative_breakdown", where)
    for k in ("cpu_seconds", "wall_seconds"):
        measured = saved.get(k)
        checks.require(type(measured) in (int, float) and math.isfinite(measured) and measured >= 0,
            "mandatory_executed_timing_receipt_not_remeasured", where + "|" + k)
    if not valid_meter:
        return
    if saved["status"] == "scored":
        checks.require(meter["feature_work"] <= config["max_score_feature_work"], "complete_score_within_work_cap", where)
        if entry["priority"] == "degree":
            _, _, adj = view(state["graph"])
            checks.require(meter["feature_work"] == sum(len(adj[v]) + 2 for v in state["patch"])
                and not meter["feature_primitives"], "degree_direct_exact_work_receipt", where)
        else:
            phases = [meter.get(k) for k in ("initialization_work", "query_work", "update_work")]
            valid_phases = all(type(v) is int and v >= 0 for v in phases)
            checks.require(valid_phases, "complete_programme_phase_work_receipts", where)
            if valid_phases:
                checks.require(sum(meter["feature_primitives"].values()) == meter["feature_work"]
                    == sum(phases) and meter["update_work"] == 0,
                    "programme_proxy_work_receipt_sum_no_deletion", where)
    if saved["status"] == "score_work_cap":
        checks.require(meter["feature_work"] > config["max_score_feature_work"], "cap_failure_preserved_charged_crossing", where)
        if entry["priority"] == "degree":
            _, _, adj = view(state["graph"])
            work, prefix, crossing = 0, [], False
            for v in sorted(state["patch"]):
                work += len(adj[v]) + 2
                if work > config["max_score_feature_work"]:
                    crossing = True
                    break
                prefix.append(v)
            partial = saved.get("partial_scores_not_predictions", {})
            checks.require(crossing and meter["feature_work"] == work and not meter["feature_primitives"]
                and isinstance(partial, dict) and list(partial) == prefix,
                "degree_cap_exact_first_crossing_and_completed_prefix", where)
    # An evaluator-initialization/score failure can legitimately have a partial
    # programme meter; do not invent or require absent complete-phase fields.
    for k in ("feature_seconds", "initialization_seconds", "update_seconds", "scoring_seconds"):
        if k in meter:
            measured = meter[k]
            checks.require(type(measured) in (int, float) and math.isfinite(measured) and measured >= 0,
                "saved_meter_timing_finite_nonnegative", where + "|" + k)


def check_score(entry, state, saved, refs, labels, config, checks):
    where = state["id"] + "|" + entry["id"]
    start_errors = len(checks.errors)
    checks.require(saved["state_id"] == state["id"] and saved["program_id"] == entry["id"]
        and saved["role"] == entry["role"] and saved["patch_status"] == state["patch_status"]
        and saved["selection_performed"] is False, "one_frozen_score_position_identity", where)
    expected_missing = "no_patch" if state["patch_status"] != "constructed" else "missing_program" if entry["priority"] == "program" and entry.get("program") is None else None
    check_score_receipts(entry, state, saved, config, checks, where, expected_missing is None)
    scores, independent_error = None, None
    if expected_missing is not None:
        checks.require(saved["status"] == expected_missing, "explicit_absent_patch_or_program_no_fallback", where)
    else:
        try:
            scores = score_independent(entry, state)
        except (ValueError, ZeroDivisionError, OverflowError, ArithmeticError) as error:
            independent_error = type(error).__name__
    if saved["status"] == "scored":
        checks.require(expected_missing is None and independent_error is None and scores is not None,
            "scored_position_finite_valid_program", where)
        if scores is None:
            return {"state_id": state["id"], "program_id": entry["id"], "status": saved["status"], "error_count": len(checks.errors) - start_errors}
        nodes, _, adj = view(state["graph"])
        checks.require(saved["scores"] == {v: str(scores[v]) for v in sorted(scores)}, "every_actual_patch_score_exact_binary_float", where)
        order = sorted(scores, key=lambda v: (-scores[v], v))
        active, greedy = set(state["patch"]), []
        for v in order:
            if v in active:
                greedy.append(v); active -= {v} | adj[v]
        checks.require(saved["priority_order"] == order and saved["greedy_proposal"] == greedy
            and feasible(nodes, adj, greedy) and feasible(nodes, adj, set(greedy) | set(state["outside_fixed"]))
            and Fraction(saved["greedy_patch_weight_exact"]) == value(nodes, greedy)
            and saved["snapshot_sha256"] == state["snapshot_sha256"], "fixed_priority_tiebreak_greedy_feasible_not_search_claim", where)
        margin = Fraction(config["score_margin_exact"])
        for key, targets in (("local_fit", labels), ("full_target_fit", refs)):
            checks.require(saved[key] == expected_fit(targets, scores, margin), "all_strict_fit_counts_flags_exact_margin", where + "|" + key)
        checks.require(Fraction(saved["score_margin_exact"]) == margin and "not the kernel" in saved["greedy_scope"]
            and "no branch search" in saved["branch_scope"], "diagnostic_scope_no_online_effect_claim", where)
    else:
        checks.require(saved["scores"] is None and saved["local_fit"] is None and saved["full_target_fit"] is None,
            "missing_or_failed_scores_never_zero_accuracy_or_fallback", where)
        if expected_missing is None:
            checks.require(saved["status"] in ("score_work_cap", "score_error") and isinstance(saved.get("error"), str)
                and isinstance(saved.get("error_type"), str), "all_failed_positions_explicit_reason", where)
            if saved["status"] == "score_error":
                checks.require(independent_error is not None, "independent_score_error_reproduced", where)
            partial = saved.get("partial_scores_not_predictions", {})
            checks.require(set(partial) <= set(state["patch"])
                and (scores is None or all(Fraction(x) == scores[v] for v, x in partial.items())), "partial_scores_not_full_predictions", where)
    return {"state_id": state["id"], "program_id": entry["id"], "role": entry["role"], "status": saved["status"],
        "snapshot_sha256": state.get("snapshot_sha256"), "saved_row_sha256": canonical(saved),
        "independent_scores": {v: str(x) for v, x in scores.items()} if saved["status"] == "scored" and scores is not None else None,
        "actual_scores": saved["scores"], "actual_priority_order": saved.get("priority_order"),
        "actual_greedy_proposal": saved.get("greedy_proposal"),
        "actual_greedy_patch_weight_exact": saved.get("greedy_patch_weight_exact"),
        "actual_local_fit": saved["local_fit"], "actual_full_target_fit": saved["full_target_fit"],
        "actual_feature_meter": saved.get("feature_meter"), "actual_cpu_seconds": saved.get("cpu_seconds"),
        "actual_wall_seconds": saved.get("wall_seconds"), "partial_scores_not_predictions": saved.get("partial_scores_not_predictions"),
        "actual_error_type": saved.get("error_type"), "actual_error": saved.get("error"),
        "error_count": len(checks.errors) - start_errors, "independent_score_error": independent_error}


def registration_checks(checks):
    for key, path in (("freeze", REGISTRATION / "freeze_receipt.json"), ("programs", PROGRAMS),
        ("release", RELEASE), ("capsule", CAPSULE), ("degree", DEGREE)):
        checks.require(digest(path) == PINS[key], "frozen_input_byte_pin", key)
    for name, expected in HELPERS.items():
        checks.require(digest(ROOT / name) == expected, "independent_helper_byte_pin", name)
    freeze, protocol, config = (read(REGISTRATION / n) for n in ("freeze_receipt.json", "protocol.json", "config.json"))
    receipt, release, programs = read(CAPSULE_RECEIPT), read(RELEASE), read(PROGRAMS)
    checks.require(receipt["source_zip_sha256"] == PINS["capsule"] and receipt["root_release_sha256"] == PINS["release"], "capsule_and_explicit_root_release_binding")
    with zipfile.ZipFile(CAPSULE) as archive:
        checks.require(len(set(archive.namelist())) == len(archive.namelist())
            and set(archive.namelist()) == set(receipt["files_sha256"]), "exact_source_capsule_closure")
        for name, expected in receipt["files_sha256"].items():
            checks.require(sha256(archive.read(name)).hexdigest() == expected == digest(ROOT / name), "every_capsule_member_current_and_frozen_byte_identity", name)
    for name, expected in freeze["files"].items():
        checks.require(digest(REGISTRATION / name) == expected, "registration_frozen_bytes", name)
    checks.require(freeze["split"] == protocol["split"] == config["split"] == programs["selection_split"] == release["selection_split"] == "train"
        and release["bridge_execution_authorized"] is True and release["program_release_complete"] is True
        and release["no_bridge_authoring_or_selection_feedback"] is True
        and programs["test_used_for_selection"] is False and programs["ready_for_execution"] is True
        and release["bridge_freeze_sha256"] == PINS["freeze"] and release["program_inventory_sha256"] == PINS["programs"]
        and protocol["runtime_source_sha256"] == freeze["runtime_source_sha256"] == release["runtime_source_sha256"], "TRAIN_only_postfreeze_no_feedback_or_TEST")
    checks.require(programs["before_any_bridge_certificate_or_program_score"] is True
        and freeze["before_any_bridge_certificate_or_program_score"] is True
        and protocol["before_any_bridge_certificate_or_program_score"] is True, "preexecution_registration_before_bridge_outcomes")
    entries = programs["entries"]
    counts = Counter(e["role"] for e in entries)
    checks.require(len(entries) == len({e["id"] for e in entries}) == 23
        and counts == Counter({**config["required_roles"], "eoh_quality": 4}), "all23_roles_identities_null_duplicates_retained")
    for e in entries:
        checks.require((e["priority"] == "degree") == (e["role"] == "degree")
            and (e["role"] != "witness_joint" or e.get("program") is not None), "genuine_W_no_degree_or_missing_substitution", e["id"])
        if e.get("program") is not None:
            normalized_program(e["program"])
    return config, protocol, entries


def audit(archive, archive_sha256, output):
    output = Path(output)
    if output.exists():
        raise ValueError("Independent audit receipts are immutable; choose a new output")
    checks, cache = Checks(), {}
    checks.require(digest(archive) == archive_sha256, "canonical_server_archive_sha256")
    config, protocol, entries = registration_checks(checks)
    raw = members(archive, OUTPUT_NAMES, prefix=RESULT_PREFIX)
    registration_raw = members(archive, ("config.json", "protocol.json"), prefix="registration")
    for name, value in registration_raw.items():
        checks.require(value == raw[name] == (REGISTRATION / name).read_bytes(),
            "server_duplicated_registration_namespace_exact_bytes", name)
    data = decode(raw)
    for name in ("inventory.json", "config.json", "protocol.json", "freeze_receipt.json", "original_training_evidence.json"):
        checks.require(raw[name] == (REGISTRATION / name).read_bytes(), "server_exact_registration_bytes", name)
    checks.require(raw["program_inventory.json"] == PROGRAMS.read_bytes() and raw["root_release.json"] == RELEASE.read_bytes(), "server_exact_program_and_root_release_bytes")
    execution, complete = data["execution.json"], data["complete.json"]
    expected_asts = {e["id"]: canonical({k: e["program"][k] for k in ("features", "rule")}) if e.get("program") is not None else None for e in entries}
    checks.require(execution["deployment_ast_sha256"] == expected_asts and execution["duplicate_ast_identities_retained"] is True
        and execution["runtime_source_sha256"] == complete["runtime_source_sha256"] == protocol["runtime_source_sha256"]
        and execution["root_release_sha256"] == complete["root_release_sha256"] == PINS["release"], "all23_executable_AST_and_source_identity")
    for r in (execution, complete):
        checks.require(r["split"] == "train" and r["selection_performed"] is False
            and r["online_model_calls"] == r["new_full_residual_oracle_calls"] == 0, "execution_no_authoring_selection_or_full_query")
    checks.require(complete["execution_complete"] is True and complete["assigned_states"] == 120
        and complete["assigned_program_state_identities"] == 2760
        and complete["labels_sha256"] == sha256(raw["labels.jsonl"]).hexdigest()
        and complete["scores_sha256"] == sha256(raw["scores.jsonl"]).hexdigest()
        and complete["no_authoring_or_selection_feedback"] is True, "complete_all2760_and_raw_stream_bindings")
    original_raw = members(DEGREE, ("training_contexts.json", "results.jsonl", "protocol.json", "freeze_receipt.json"))
    original = decode(original_raw)
    for name, info in protocol["archive_members"].items():
        checks.require(sha256(original_raw[name]).hexdigest() == info["sha256"], "original_Degree_archive_member_hash", name)
    contexts = {r["id"]: r for r in original["training_contexts.json"]["contexts"]}
    feedback = {r["id"]: r for r in original["results.jsonl"]}
    inventory, label_rows, score_rows = data["inventory.json"]["records"], data["labels.jsonl"], data["scores.jsonl"]
    ids = [s["id"] for s in inventory]
    checks.require(len(ids) == len(set(ids)) == len(contexts) == len(feedback) == 120
        and set(ids) == set(contexts) == set(feedback) and ids == sorted(ids)
        and [r["id"] for r in label_rows] == ids, "all120_original_states_exact_frozen_order")
    expected_positions = [(s["id"], e["id"]) for s in inventory for e in entries]
    checks.require([(r["state_id"], r["program_id"]) for r in score_rows] == expected_positions
        and len(set(expected_positions)) == 2760, "all2760_assigned_rows_no_missing_duplicate_or_reordering")
    patch_audits, label_audits, position_audits, references = [], [], [], {}
    evidence = data["original_training_evidence.json"]
    for state, saved in zip(inventory, label_rows):
        patch_audits.append(check_saved_patch(state, contexts[state["id"]], feedback[state["id"]], checks, cache))
        refs = references[state["id"]] = reference_rows(evidence, state, checks)
        queries, quota = query_union(state, refs, config)
        checks.require(state["queries"] == queries and state["quota"] == quota == saved["quota"], "independent_query_union_SHA_strict_strata_shortfalls", state["id"])
        checks.require(saved["id"] == state["id"] and saved["split"] == "train"
            and saved["family"] == state["family"] and saved["patch_status"] == state["patch_status"]
            and saved["snapshot_sha256"] == state.get("snapshot_sha256")
            and saved["oracle_used_by_program"] is False and saved["available_original_full_requirements"] == refs,
            "local_label_state_scope_and_old_full_references", state["id"])
        checks.require(len(saved["rows"]) == len(queries), "all_planned_local_queries_retained", state["id"])
        for query, label in zip(queries, saved["rows"]):
            label_audits.append(check_local_label(state, query, label, config, checks, cache))
        nodes, _, adj = view(state["graph"])
        legal = set(boundary(nodes, adj, state["permanent_fixed"], state["excluded"]))
        for ref in refs:
            a, b = ref["a"], ref["b"]
            diff = Fraction(nodes[a]["weight"]) + alpha(nodes, adj, legal - {a} - adj[a], cache, state["graph_sha256"])
            diff -= Fraction(nodes[b]["weight"]) + alpha(nodes, adj, legal - {b} - adj[b], cache, state["graph_sha256"])
            checks.require(Fraction(ref["lower_exact"]) <= diff <= Fraction(ref["upper_exact"])
                and ref["preferred"] == (a if diff > 0 else b if diff < 0 else None), "old_full_requirement_sound_independent_scope", state["id"])
        expected_overlap = []
        for ref in refs:
            overlap = next(r for r in saved["rows"] if {r["a"], r["b"]} == {ref["a"], ref["b"]})
            expected_overlap.append({"a": ref["a"], "b": ref["b"], "full_preferred": ref["preferred"],
                "local_preferred": overlap["preferred"], "local_status": overlap["status"],
                "direction_agrees": overlap["preferred"] == ref["preferred"] if overlap["status"] == "strict" else None,
                "full_scope": FULL, "local_scope": LOCAL})
        checks.require(saved["full_vs_local_overlap"] == expected_overlap, "full_local_disagreement_or_unknown_never_hidden", state["id"])
    checks.require(len(label_audits) == protocol["planned_queries"] == 159
        and sum(q["in_core_sha"] for q in label_audits) == protocol["core_SHA_queries"] == 155
        and sum(q["in_full_strict_bridge"] for q in label_audits) == protocol["original_full_strict_pair_queries"] == 7
        and sum(s["quota"]["pair_shortfall"] for s in inventory) == protocol["query_shortfalls"] == 325,
        "all159_queries_both_strata_and_missing_quota_counts")
    cumulative, prefixes = {e["id"]: Counter() for e in entries}, []
    for index, state in enumerate(inventory):
        labels = label_rows[index]["rows"]
        for j, entry in enumerate(entries):
            saved = score_rows[index * len(entries) + j]
            position_audits.append(check_score(entry, state, saved, references[state["id"]], labels, config, checks))
            c = cumulative[entry["id"]]
            c.update(assigned_states=1, sampled_queries=len(labels), local_strict_labels=sum(r["status"] == "strict" for r in labels),
                core_SHA_queries=sum(r["in_core_sha"] for r in labels),
                core_SHA_strict_labels=sum(r["in_core_sha"] and r["status"] == "strict" for r in labels),
                full_strict_pair_queries=sum(r["in_full_strict_bridge"] for r in labels), score_complete_states=int(saved["status"] == "scored"))
            if saved["local_fit"] is not None:
                lf, ff = saved["local_fit"], saved["full_target_fit"]
                c.update(observed_local_strict_predictions=lf["strict_targets"], local_strict_passed=lf["passed"],
                    observed_core_SHA_strict_predictions=lf["core_SHA_strict_targets"], core_SHA_strict_passed=lf["core_SHA_passed"],
                    observed_full_pair_local_strict_predictions=lf["full_strict_pair_local_targets"],
                    full_pair_local_strict_passed=lf["full_strict_pair_local_passed"],
                    observed_full_target_predictions=ff["strict_targets"], full_target_passed=ff["passed"])
            prefixes.append({"program_id": entry["id"], "state_prefix": index + 1, "last_state_id": state["id"], **dict(c)})
    checks.require(data["prefixes.json"] == prefixes, "all2760_cumulative_prefix_counters")
    summary = [{"id": e["id"], "role": e["role"], "deployment_ast_sha256": expected_asts[e["id"]],
        "missing_program": e["priority"] == "program" and e.get("program") is None,
        "status_counts": dict(Counter(r["status"] for r in score_rows if r["program_id"] == e["id"])),
        **dict(cumulative[e["id"]]), "missing_predictions_are_not_zero_accuracy": True} for e in entries]
    checks.require(data["summary.json"] == summary, "all23_role_summary_arithmetic_and_null_denominators")
    cov = data["coverage.json"]
    coverage = {"states": 120, "patch_status_counts": dict(Counter(s["patch_status"] for s in inventory)),
        "families": dict(Counter(s["family"] for s in inventory)),
        "original_priority_order_present_states": sum(s.get("original_priority_order_present", False) for s in inventory),
        "planned_queries": len(label_audits), "planned_adjacent_queries": sum(q["competing"] for q in label_audits),
        "core_SHA_queries": sum(q["in_core_sha"] for q in label_audits),
        "core_SHA_local_label_status_counts": dict(Counter(q["saved_status"] for q in label_audits if q["in_core_sha"])),
        "original_full_strict_pair_queries": sum(q["in_full_strict_bridge"] for q in label_audits),
        "original_full_strict_pair_local_status_counts": dict(Counter(q["saved_status"] for q in label_audits if q["in_full_strict_bridge"])),
        "pair_quota_shortfalls": sum(s["quota"]["pair_shortfall"] for s in inventory),
        "local_label_status_counts": dict(Counter(q["saved_status"] for q in label_audits)),
        "original_full_requirements_available": sum(len(x) for x in references.values()),
        "full_local_overlap": sum(len(r["full_vs_local_overlap"]) for r in label_rows),
        "strict_full_local_agreement": sum(q["direction_agrees"] is True for r in label_rows for q in r["full_vs_local_overlap"]),
        "strict_full_local_disagreement": sum(q["direction_agrees"] is False for r in label_rows for q in r["full_vs_local_overlap"])}
    for k, v in coverage.items():
        checks.require(cov.get(k) == v, "coverage_aggregate_independent_arithmetic", k)
    for family in sorted({s["family"] for s in inventory}):
        family_states = [s for s in inventory if s["family"] == family]
        family_labels = [r for r in label_rows if r["family"] == family]
        expected = {"states": len(family_states), "constructed_patches": sum(s["patch_status"] == "constructed" for s in family_states),
            "core_SHA_queries": sum(q["in_core_sha"] for s in family_states for q in s["queries"]),
            "union_queries": sum(len(s["queries"]) for s in family_states),
            "local_status": dict(Counter(q["status"] for r in family_labels for q in r["rows"]))}
        checks.require(cov["per_family"].get(family) == expected, "every_family_coverage_not_pooled_incidence", family)
    report = {"version": "v06_TRAIN_patch_bridge_independent_verification_001", "audit_phase": "train_patch_bridge",
        "checks": sum(checks.counts.values()), "check_categories": dict(checks.counts),
        "errors": len(checks.errors), "error_records": checks.errors, "TEST_accessed": False,
        "experimental_reexecution": False, "production_runtime_imported": False,
        "metadata": {"archive": str(Path(archive)), "archive_sha256": digest(archive),
            "source_capsule_sha256": PINS["capsule"], "program_inventory_sha256": PINS["programs"],
            "source_capsule_receipt_sha256": digest(CAPSULE_RECEIPT),
            "protocol_sha256": digest(REGISTRATION / "protocol.json"),
            "root_release_sha256": PINS["release"], "registration_freeze_sha256": PINS["freeze"],
            "original_Degree_archive_sha256": PINS["degree"], "audit_script_sha256": digest(__file__),
            "independent_helper_sha256": HELPERS, "output_member_sha256": {n: sha256(x).hexdigest() for n, x in raw.items()}},
        "assigned_states": len(inventory), "assigned_score_positions": len(position_audits), "query_union_count": len(label_audits),
        "coverage": coverage, "independent_summary": summary, "patch_audit_rows": patch_audits,
        "label_audit_rows": label_audits, "position_audit_rows": position_audits,
        "limits": ["Restricted forced-inclusion values do not certify pivot efficiency or deployment improvement.",
            "Old full strict label stratum is certification-conditioned; core quota shortfalls and nonadjacent pairs remain.",
            "Exact verification recurrence has a one-million-state ceiling; failure never becomes an asserted certificate.",
            "Feature work is an executed operation proxy: primitive sums, cap, no-update identity and exact Degree work are checked; programme primitive counts and CPU/wall costs are not remeasured.",
            "Duplicate AST identities and programme null/error positions remain; missing predictions are not zero accuracy."]}
    if any(n == "cipheur" or n.startswith("cipheur.") for n in sys.modules):
        raise AssertionError("Production runtime imported during independent verification")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = audit(args.archive, args.archive_sha256, args.out)
    print(json.dumps({"checks": report["checks"], "errors": report["errors"],
        "assigned_score_positions": report["assigned_score_positions"], "query_union_count": report["query_union_count"],
        "audit_sha256": digest(args.out)}, ensure_ascii=False))
    raise SystemExit(0 if report["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
