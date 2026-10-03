"""Outcome-independent exact-input alias census on development residual states.

No test/transfer outcomes, proposal banks, or deployment programs are read. The
base interface is evaluated by the CURRENT FeatureRuleProgram implementation,
including typed math.fsum aggregation. Oracle labels are acquired only after a
deterministic, outcome-independent query plan has been fixed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import tarfile
from time import perf_counter

from .graph_features import FeatureRuleProgram, _FeatureState
from .model import Graph, aligned_intervention
from .oracle import Budget, certify_pair
from .programs import FEATURES
from .refinement import diagnose_occurrences
from .representation import vector_key


BASE_PROGRAM = FeatureRuleProgram("alias_census_weight_degree", [], "weight / max(1, degree)")
_VISIBLE_PARAMETERS = {"station_gap", "ground_trans_time", "satellite_gap", "satellite_change_time"}
_NEIGHBORS = {"op": "neighbors", "args": [{"op": "root", "args": []}]}
_EDGES = {"op": "induced_edges", "args": [_NEIGHBORS]}
STRUCTURE_PROGRAM = FeatureRuleProgram("alias_census_typed_distinctions", [
    {"name": "neighbor_edge_count", "expression": {"op": "count", "args": [_EDGES]}},
    {"name": "neighbor_edge_min", "expression": {"op": "edge_min_weight_sum", "args": [_EDGES]}},
    {"name": "neighbor_edge_product", "expression": {"op": "edge_weight_product_sum", "args": [_EDGES]}},
    {"name": "neighbor_clique_cover", "expression": {"op": "clique_cover_weight", "args": [_NEIGHBORS]}},
    {"name": "neighbor_greedy", "expression": {"op": "greedy_independent_weight", "args": [_NEIGHBORS]}},
], "weight")
_STRUCTURE_NAMES = tuple(f["name"] for f in STRUCTURE_PROGRAM.features)


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _graph(value):
    return value if isinstance(value, Graph) else Graph.from_dict(value)


def _diagnostic(record):
    source = record.get("source", {})
    return ("diagnostic" in record.get("family", "").lower()
            or "probe" in source.get("origin", "").lower()
            or source.get("population_claim") == "mechanism_diagnostic_only")


def development_pairs(data):
    """Reject outcome/test containers, exclude probes, and retain both splits."""
    if not isinstance(data, dict) or set(data) - {"train", "validation", "protocol"}:
        raise ValueError("Alias census accepts only train/validation development data")
    if not all(isinstance(data.get(split), list) for split in ("train", "validation")):
        raise ValueError("Both development splits must be explicit lists")
    pairs, excluded, identities = [], [], set()
    for split in ("train", "validation"):
        for record in data[split]:
            if record.get("source", {}).get("split", split) != split:
                raise ValueError("Record split disagrees with its development container")
            if _diagnostic(record):
                excluded.append({"split": split, "id": record["id"], "family": record.get("family")})
                continue
            key = (split, record["id"])
            if key in identities:
                raise ValueError("Duplicate development pair identity")
            identities.add(key)
            pairs.append({**record, "census_split": split})
    return sorted(pairs, key=lambda p: (p["census_split"], p["id"])), excluded


def load_development_archive(path):
    """Read exactly the completed development archive's data member, no results."""
    path = Path(path)
    with tarfile.open(path) as archive:
        members = [m for m in archive.getmembers()
                   if m.name == "development_scale_001/data.json" and m.isfile()]
        if len(members) != 1:
            raise ValueError("Expected the unique development_scale_001/data.json member")
        payload = archive.extractfile(members[0]).read()
    data = json.loads(payload)
    development_pairs(data)  # Validate before returning, without consulting results.
    return data, {"archive": str(path), "archive_sha256": sha256(path.read_bytes()).hexdigest(),
                  "data_member": members[0].name, "data_sha256": sha256(payload).hexdigest()}


def base_vectors(graph, active):
    """Exactly the nine values supplied by the current typed base interface."""
    state = _FeatureState(graph, set(active), None)
    values = {v: state.feature_values(BASE_PROGRAM, v) for v in sorted(active)}
    if any(set(row) != set(FEATURES) for row in values.values()):
        raise AssertionError("Current base interface changed; census must be reviewed")
    return values


def _rollout_boundaries(graph, fixed, excluded, max_steps):
    chosen, result = list(fixed), []
    for step in range(max_steps + 1):
        active = graph.available(chosen, excluded)
        vectors = base_vectors(graph, active)
        scores = {v: BASE_PROGRAM._rank(vector) for v, vector in vectors.items()}
        action = min(active, key=lambda v: (-scores[v], v)) if active else None
        result.append({"step": step, "fixed": sorted(chosen), "excluded": sorted(excluded),
                       "actual_next_action": action})
        if action is None or step == max_steps:
            break
        chosen.append(action)
    return result


def _structure_values(state, node):
    values = state.feature_values(STRUCTURE_PROGRAM, node)
    return {name: values[name] for name in _STRUCTURE_NAMES}


def census_pairs(pairs, *, max_steps=2):
    """Enumerate all common-conflict pairs at initial and actual rollout states.

    Both side rollouts contribute boundaries. Duplicate fixed/excluded sets are
    merged before counting, and every remaining boundary is replayed on BOTH
    graphs. Candidate membership never depends on conditional-oracle outcomes.
    """
    if type(max_steps) is not int or not 0 <= max_steps <= 2:
        raise ValueError("Census permits initial plus at most two rollout steps")
    boundaries, candidates, totals, groups = [], [], Counter(), {}
    started = perf_counter()
    for pair_index, pair in enumerate(pairs):
        if _diagnostic(pair):
            raise ValueError("Diagnostic probes must be excluded before census")
        split = pair.get("census_split", pair.get("source", {}).get("split"))
        if split not in ("train", "validation"):
            raise ValueError("Census pair is not in a development split")
        left, right = _graph(pair["left"]), _graph(pair["right"])
        fixed, excluded = tuple(pair.get("fixed", ())), tuple(pair.get("excluded", ()))
        intervention = aligned_intervention(left, right, fixed, excluded)
        changes = sorted(intervention["parameter_changes"])
        omitted = sorted(set(changes) - _VISIBLE_PARAMETERS)
        label = f"{split}|{pair.get('family', 'unspecified')}|{changes[0]}|{len(left.nodes)}"
        group = groups.setdefault(label, Counter())
        group["pairs"] += 1
        group["graph_contexts"] += 2
        totals["pairs"] += 1
        totals["graph_contexts"] += 2
        states = {}
        for side, graph in (("left", left), ("right", right)):
            for state in _rollout_boundaries(graph, fixed, excluded, max_steps):
                key = (tuple(state["fixed"]), tuple(state["excluded"]))
                entry = states.setdefault(key, [])
                entry.append({"side": side, **state})
                group["proposed_boundaries"] += 1
                totals["proposed_boundaries"] += 1
        for (boundary, exclusions), origins in sorted(states.items()):
            identity = {"split": split, "pair_id": pair["id"], "fixed": boundary, "excluded": exclusions}
            bid = _hash(identity)
            row = {"id": bid, "pair_index": pair_index, "pair_id": pair["id"], "split": split,
                   "family": pair.get("family"), "size": len(left.nodes), "changed_parameters": changes,
                   "unexposed_changed_parameters": omitted, "fixed": list(boundary),
                   "excluded": list(exclusions), "rollout_origins": origins, "group": label}
            group["unique_boundaries"] += 1
            totals["unique_boundaries"] += 1
            try:
                aligned_intervention(left, right, boundary, exclusions)
                active = {"left": left.available(boundary, exclusions),
                          "right": right.available(boundary, exclusions)}
            except ValueError as error:
                row.update(valid_replay=False, reason="invalid_common_boundary", error=str(error))
                boundaries.append(row)
                group["invalid_boundary_replays"] += 1
                totals["invalid_boundary_replays"] += 1
                continue
            vectors = {side: base_vectors(graph, active[side])
                       for side, graph in (("left", left), ("right", right))}
            keys = {side: {v: vector_key(value) for v, value in values.items()}
                    for side, values in vectors.items()}
            feature_states = {side: _FeatureState(graph, active[side], None)
                              for side, graph in (("left", left), ("right", right))}
            structure_cache = {"left": {}, "right": {}}
            def structure(side, node):
                cache = structure_cache[side]
                if node not in cache:
                    cache[node] = _structure_values(feature_states[side], node)
                return cache[node]
            common = active["left"] & active["right"]
            # Equal active induced problems imply equal conditional values on
            # both sides. Cross-only matches here cannot yield a reversal cycle.
            residual_equal = (active["left"] == active["right"] and all(
                left.adj[v] & active["left"] == right.adj[v] & active["right"]
                for v in active["left"]))
            counts = Counter()
            for a in sorted(common):
                for b in sorted(common & left.adj[a] & right.adj[a]):
                    if b <= a:
                        continue
                    counts["common_conflicting_pairs"] += 1
                    equal_sides = [side for side in ("left", "right") if keys[side][a] == keys[side][b]]
                    distinguishing = {}
                    for side in equal_sides:
                        av, bv = structure(side, a), structure(side, b)
                        names = [name for name in _STRUCTURE_NAMES if Fraction(av[name]) != Fraction(bv[name])]
                        if names:
                            distinguishing[side] = {"features": names, "a": av, "b": bv}
                        counts[f"within_side_exact_alias_pairs_{side}"] += 1
                    direct = keys["left"][a] == keys["right"][a] and keys["left"][b] == keys["right"][b]
                    swapped = keys["left"][a] == keys["right"][b] and keys["left"][b] == keys["right"][a]
                    partial = any(keys["left"][u] == keys["right"][v] for u in (a, b) for v in (a, b))
                    counts["within_side_exact_alias_pairs"] += bool(equal_sides)
                    counts["within_side_structurally_distinguished_alias_pairs"] += bool(distinguishing)
                    counts["cross_direct_vector_match_pairs"] += direct
                    counts["cross_swapped_vector_match_pairs"] += swapped
                    counts["cross_any_equality_join_pairs"] += partial
                    if not equal_sides and not partial:
                        continue
                    kinds = []
                    if equal_sides:
                        kinds.append("within_side_exact_alias")
                    if distinguishing:
                        kinds.append("within_side_typed_structure_distinction")
                    if direct:
                        kinds.append("cross_direct_vector_match")
                    if swapped:
                        kinds.append("cross_swapped_vector_match")
                    if partial:
                        kinds.append("cross_side_equality_join")
                    cid = _hash({**identity, "a": a, "b": b})
                    query_eligible = bool(equal_sides) or not residual_equal
                    priority = (0 if distinguishing else 1 if equal_sides else 2 if swapped else 3 if direct else 4)
                    candidates.append({"id": cid, "boundary_id": bid, "pair_index": pair_index,
                        "pair_id": pair["id"], "split": split, "family": pair.get("family"),
                        "size": len(left.nodes), "a": a, "b": b, "fixed": list(boundary),
                        "excluded": list(exclusions), "group": label, "kinds": kinds,
                        "within_equal_sides": equal_sides, "typed_distinctions": distinguishing,
                        "vectors": {side: {v: vectors[side][v] for v in (a, b)} for side in vectors},
                        "unexposed_changed_parameters": omitted, "residual_problems_identical": residual_equal,
                        "query_eligible": query_eligible, "query_priority": priority,
                        "no_query_reason": None if query_eligible else "cross_only_identical_conditional_problems"})
                    counts["candidate_pairs"] += 1
                    counts["query_eligible_candidates"] += query_eligible
                    counts["cross_only_identical_problem_candidates"] += not query_eligible
            row.update(valid_replay=True, active_left=len(active["left"]), active_right=len(active["right"]),
                       common_actions=len(common), residual_problems_identical=residual_equal,
                       counts=dict(counts), no_candidates=not counts["candidate_pairs"])
            boundaries.append(row)
            for counter in (totals, group):
                counter.update(counts)
                counter["valid_boundary_replays"] += 1
                counter["boundaries_without_candidates"] += not counts["candidate_pairs"]
    return {"totals": dict(totals), "groups": {key: dict(value) for key, value in sorted(groups.items())},
            "boundaries": boundaries, "base_feature_names": list(FEATURES),
            "base_program": BASE_PROGRAM.to_dict(), "typed_distinction_library": STRUCTURE_PROGRAM.to_dict(),
            "max_rollout_steps": max_steps, "elapsed_seconds": perf_counter() - started,
            "candidate_prefilter_uses_oracle": False,
            "unexposed_configuration_warning": "satellite_trans_time is not an explicit current base field"}, candidates


def query_plan(candidates, max_queries=200):
    if type(max_queries) is not int or max_queries < 0:
        raise ValueError("Query limit must be nonnegative")
    eligible = [row for row in candidates if row["query_eligible"]]
    selected = sorted(eligible, key=lambda row: (row["query_priority"], row["id"]))[:max_queries]
    return selected, {"method": "typed-within-alias, other-within-alias, cross-swapped, cross-direct, partial-cross-join; SHA256 ID order",
                      "max_queries": max_queries, "eligible_count": len(eligible), "selected_count": len(selected),
                      "unsampled_eligible_count": len(eligible) - len(selected),
                      "selected_ids": [row["id"] for row in selected], "oracle_outcomes_used": False}


def _strict_preference(bounds, side, a, b, epsilon):
    av, bv = bounds.get(side + "_a"), bounds.get(side + "_b")
    if av is None or bv is None:
        return None
    margin = Fraction(epsilon)
    if Fraction(av["lower_exact"]) > Fraction(bv["upper_exact"]) + margin:
        return a
    if Fraction(bv["lower_exact"]) > Fraction(av["upper_exact"]) + margin:
        return b
    return None


def _certify_task(task):
    pair, candidate, options = task
    left, right = _graph(pair["left"]), _graph(pair["right"])
    budget = Budget(max_calls=options["max_calls"], max_nodes=options["query_nodes"])
    witness, details = certify_pair(left, right, candidate["a"], candidate["b"], budget,
        candidate["fixed"], candidate["excluded"], options["epsilon"],
        nodes_per_call=options["nodes_per_call"], max_region=options["max_region"],
        include_preservation=True, raise_on_exhaustion=False)
    preferences = {side: _strict_preference(details.get("bounds", {}), side,
                                           candidate["a"], candidate["b"], options["epsilon"])
                   for side in ("left", "right")}
    relation = ("unknown" if None in preferences.values() else
                "preservation" if preferences["left"] == preferences["right"] else "reversal")
    if witness is not None and witness["relation"] != relation:
        raise AssertionError("Oracle witness and exact side inequalities disagree")
    return {"candidate": candidate, "pair_relation": relation, "side_preferences": preferences,
            "oracle_reason": details["reason"], "details": details, "certificate": witness,
            "budget": budget.to_dict(), "unknown_is_not_preservation": True}


def certify_candidates(pairs, selected, *, workers=1, query_nodes=2000,
                       nodes_per_call=500, max_region=1024, max_calls=64, epsilon=1e-8,
                       on_result=None):
    """Each selected pair gets its own total node/call budget, with no fallback."""
    for name, value in (("workers", workers), ("query_nodes", query_nodes),
                        ("nodes_per_call", nodes_per_call), ("max_calls", max_calls)):
        if type(value) is not int or value < (1 if name == "workers" else 0):
            raise ValueError("Invalid census oracle option: " + name)
    options = dict(query_nodes=query_nodes, nodes_per_call=nodes_per_call,
                   max_region=max_region, max_calls=max_calls, epsilon=epsilon)
    tasks = [(pairs[row["pair_index"]], row, options) for row in selected]
    def consume(iterator):
        results = []
        for row in iterator:
            results.append(row)
            if on_result is not None:
                on_result(row, len(results))
        return results
    if workers == 1:
        return consume(map(_certify_task, tasks))
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return consume(executor.map(_certify_task, tasks, chunksize=1))


def summarize_certificates(pairs, results):
    """Use each sound side arc, but never label one-sided evidence preservation.

    A second quotient adds unexposed numeric configuration fields as an audit.
    A disappearing cross-configuration cycle is not called structural necessity.
    """
    occurrences, audited, requirements = {}, {}, []
    totals, groups = Counter(), {}
    audit_fields = sorted({name for row in results for name in row["candidate"]["unexposed_changed_parameters"]})
    for row in results:
        candidate = row["candidate"]
        pair = pairs[candidate["pair_index"]]
        group = groups.setdefault(candidate["group"], Counter())
        for count in (totals, group):
            count["queries"] += 1
            count[row["pair_relation"]] += 1
            count["expanded_nodes"] += row["budget"]["expanded_nodes"]
            count["conditional_calls"] += row["budget"]["calls"]
            count["unknown_side_requirements"] += sum(v is None for v in row["side_preferences"].values())
        for side in ("left", "right"):
            graph = _graph(pair[side])
            for node, vector in candidate["vectors"][side].items():
                oid = f"{candidate['boundary_id']}:{side}:{node}"
                if oid in occurrences and occurrences[oid] != vector:
                    raise AssertionError("A concrete occurrence has inconsistent base values")
                occurrences[oid] = vector
                expanded = dict(vector)
                for field in audit_fields:
                    value = graph.constraints.get(field, 0)
                    if type(value) not in (int, float) or not math.isfinite(value):
                        raise ValueError("Configuration audit requires numeric fields")
                    expanded[f"audit_{field}_present"] = int(field in graph.constraints)
                    expanded[f"audit_{field}"] = value
                audited[oid] = expanded
            preferred = row["side_preferences"][side]
            if preferred is not None:
                other = candidate["b"] if preferred == candidate["a"] else candidate["a"]
                requirements.append({"preferred": f"{candidate['boundary_id']}:{side}:{preferred}",
                    "other": f"{candidate['boundary_id']}:{side}:{other}",
                    "candidate_id": candidate["id"], "side": side, "pair_relation": row["pair_relation"]})
    base = diagnose_occurrences(occurrences, requirements)
    configuration = diagnose_occurrences(audited, requirements)
    return {"totals": dict(totals), "groups": {key: dict(value) for key, value in sorted(groups.items())},
            "certified_side_requirements": len(requirements), "occurrences": len(occurrences),
            "base_quotient": base, "configuration_audited_quotient": configuration,
            "configuration_audit_fields": audit_fields,
            "configuration_omission_can_explain_all_observed_cycles": base["contradictory"] and not configuration["contradictory"],
            "pair_unknowns_remain_unknown": True, "requirements": requirements,
            "scope": "queried development occurrences only; DAG does not prove information sufficiency or DSL expressibility"}


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_rows(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--archive", type=Path)
    inputs.add_argument("--data", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--max-queries", type=int, default=200)
    parser.add_argument("--query-nodes", type=int, default=2000)
    parser.add_argument("--nodes-per-call", type=int, default=500)
    parser.add_argument("--max-region", type=int, default=1024)
    parser.add_argument("--max-calls", type=int, default=64)
    parser.add_argument("--epsilon", type=float, default=1e-8)
    parser.add_argument("--census-only", action="store_true")
    args = parser.parse_args(argv)
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Use a fresh output directory; existing census artifacts are not overwritten")
    if args.archive:
        data, source = load_development_archive(args.archive)
    else:
        payload = args.data.read_bytes()
        data, source = json.loads(payload), {"data": str(args.data), "data_sha256": sha256(payload).hexdigest()}
    pairs, excluded = development_pairs(data)
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = {"source": source, "options": {key: str(value) if isinstance(value, Path) else value
                                              for key, value in vars(args).items()},
        "source_sha256": {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ("alias_census.py", "graph_features.py", "oracle.py", "model.py", "representation.py", "refinement.py")},
        "allowed_splits": ["train", "validation"], "excluded_diagnostic_records": excluded,
        "test_or_transfer_outcomes_read": False, "candidate_banks_or_frozen_programs_changed": False}
    _write_json(args.out / "execution.json", receipt)
    census, candidates = census_pairs(pairs, max_steps=args.max_steps)
    census["excluded_diagnostic_pairs"] = len(excluded)
    _write_json(args.out / "census.json", census)
    _write_rows(args.out / "candidates.jsonl", candidates)
    selected, plan = query_plan(candidates, args.max_queries)
    _write_json(args.out / "query_plan.json", plan)
    _write_json(args.out / "complete.json", {"complete": False, "stage": "query_plan_saved",
                                            "queries_planned": len(selected)})
    print(json.dumps({"census_totals": census["totals"], "query_plan": {key: value for key, value in plan.items() if key != "selected_ids"}}), flush=True)
    if not args.census_only:
        with (args.out / "oracle_results.jsonl").open("w", encoding="utf-8") as stream:
            def save_result(row, count):
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                if count % 10 == 0 or count == len(selected):
                    print(json.dumps({"queries_completed": count, "queries_planned": len(selected)}), flush=True)
            results = certify_candidates(pairs, selected, workers=args.workers, query_nodes=args.query_nodes,
                nodes_per_call=args.nodes_per_call, max_region=args.max_region, max_calls=args.max_calls,
                epsilon=args.epsilon, on_result=save_result)
        summary = summarize_certificates(pairs, results)
        _write_json(args.out / "summary.json", summary)
        print(json.dumps({"certificate_totals": summary["totals"], "base_contradictory": summary["base_quotient"]["contradictory"],
                          "configuration_audited_contradictory": summary["configuration_audited_quotient"]["contradictory"]}), flush=True)
    _write_json(args.out / "complete.json", {"complete": True, "stage": "census_only" if args.census_only else "census_and_certificates",
        "queries_completed": 0 if args.census_only else len(selected),
        "query_plan_sha256": sha256((args.out / "query_plan.json").read_bytes()).hexdigest()})


if __name__ == "__main__":
    main()
