"""TRAIN-only synthesis using actual choices and cancelled completion differences.

All deployed candidates remain ordinary FeatureRuleProgram ASTs executed by
schedule_compiled. Exact component cancellation is an OFFLINE evidence tool,
never a feature supplied by a deployment oracle. Unresolved bounds stay unknown.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import statistics
import sys
import tarfile
import time

from .compiled import CompiledEvaluator, schedule_compiled
from .graph_features import FeatureRuleProgram, _FeatureState, NEIGHBOR_EDGE_COUNT, NEIGHBOR_EDGE_MIN
from .model import Contact, Graph, temporal_graph
from .oracle import solve, exact_value, outward, local_bound
from .refinement import diagnose_occurrences, minimum_cost_vector_refinement


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def components(graph, active):
    """Exact connected partition, with a deterministic vertex-set identity."""
    remaining, parts = set(active), []
    if not remaining <= graph.nodes.keys():
        raise ValueError("Unknown component vertex")
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        part, pending = {seed}, [seed]
        while pending:
            neighbors = graph.adj[pending.pop()] & remaining
            remaining.difference_update(neighbors)
            part.update(neighbors)
            pending.extend(sorted(neighbors))
        parts.append(tuple(sorted(part)))
    return tuple(sorted(parts))


class CancelledCompletionOracle:
    """Cache exact-subproblem intervals, cancel identical conditioned components.

    For R_d = R minus ({d} union N_R(d)), V(d)=w(F)+w(d)+sum_C MWIS(C).
    Identical components in R_a/R_b have the same UNKNOWN optimum and cancel.
    Bounds on only unmatched components therefore enclose the GLOBAL difference.
    """
    def __init__(self, graph, fixed=(), excluded=(), *, nodes_per_component=64,
                 max_search_component=128, max_nodes=10000, max_calls=256):
        for value in (nodes_per_component, max_search_component, max_nodes, max_calls):
            if type(value) is not int or value < 0:
                raise ValueError("Cancellation limits must be nonnegative integers")
        self.graph, self.fixed, self.excluded = graph, tuple(fixed), tuple(excluded)
        self.active = graph.available(self.fixed, self.excluded)
        self.nodes_per_component, self.max_search_component = nodes_per_component, max_search_component
        self.max_nodes, self.max_calls = max_nodes, max_calls
        self.cache, self.partitions = {}, {}
        self.calls = self.expanded_nodes = 0
        self.elapsed_seconds = 0.0
        self.total_difference_seconds = 0.0

    def partition(self, action):
        if action not in self.active:
            raise ValueError("Compared action must be feasible at this boundary")
        if action not in self.partitions:
            residual = self.active - self.graph.adj[action] - {action}
            self.partitions[action] = components(self.graph, residual)
        return self.partitions[action]

    def bound(self, part):
        part = tuple(part)
        if part not in self.cache:
            if self.calls >= self.max_calls:
                # This interval is a sound trivial fallback, NOT a completed
                # solver call or a fabricated strict label.
                upper = exact_value(self.graph, part)
                self.cache[part] = {"lower_exact": "0", "upper_exact": str(upper), "selected": [],
                    "exact": upper == 0, "expanded": 0, "reason": "call_budget_trivial_interval"}
                return self.cache[part]
            contacts = tuple(self.graph.nodes[v] for v in part)
            vertices = set(part)
            edges = frozenset(e for e in self.graph.edges if e[0] in vertices and e[1] in vertices)
            induced = Graph("cancelled_component", contacts, edges, self.graph.constraints)
            node_limit = min(self.nodes_per_component, self.max_nodes - self.expanded_nodes)
            if len(part) > self.max_search_component:
                node_limit = 0
            started = time.perf_counter()
            result = solve(induced, max_nodes=node_limit)
            self.elapsed_seconds += time.perf_counter() - started
            self.calls += 1
            self.expanded_nodes += result.expanded
            if not induced.feasible(result.selected):
                raise AssertionError("Component lower witness is infeasible")
            self.cache[part] = {"lower_exact": result.lower_exact, "upper_exact": result.upper_exact,
                "selected": list(result.selected), "exact": result.exact, "expanded": result.expanded,
                "reason": "searched" if node_limit else "zero_node_sound_envelope"}
        return self.cache[part]

    def difference(self, a, b, epsilon=1e-8):
        started = time.perf_counter()
        if a not in self.active or b not in self.active:
            raise ValueError("Compared actions must be feasible at this boundary")
        if not math.isfinite(epsilon) or epsilon < 0:
            raise ValueError("Difference epsilon must be finite and nonnegative")
        if a == b:
            return {"a": a, "b": b, "lower_exact": "0", "upper_exact": "0",
                    "lower": 0.0, "upper": 0.0, "preferred": None, "status": "exact_tie",
                    "cancelled_components": [], "unmatched": {"a": [], "b": []}, "exact": True}
        pa, pb = set(self.partition(a)), set(self.partition(b))
        common, only_a, only_b = sorted(pa & pb), sorted(pa - pb), sorted(pb - pa)
        wa, wb = Fraction(self.graph.nodes[a].weight), Fraction(self.graph.nodes[b].weight)
        rows = {side: [{"vertices": list(part), "bound": self.bound(part)} for part in parts]
                for side, parts in (("a", only_a), ("b", only_b))}
        lower = wa - wb + sum((Fraction(row["bound"]["lower_exact"]) for row in rows["a"]), Fraction(0))
        lower -= sum((Fraction(row["bound"]["upper_exact"]) for row in rows["b"]), Fraction(0))
        upper = wa - wb + sum((Fraction(row["bound"]["upper_exact"]) for row in rows["a"]), Fraction(0))
        upper -= sum((Fraction(row["bound"]["lower_exact"]) for row in rows["b"]), Fraction(0))
        if lower > upper:
            raise AssertionError("Cancelled interval is empty")
        preferred = a if lower > Fraction(epsilon) else b if upper < -Fraction(epsilon) else None
        self.total_difference_seconds += time.perf_counter() - started
        return {"a": a, "b": b, "lower_exact": str(lower), "upper_exact": str(upper),
                "lower": outward(lower, -1), "upper": outward(upper, 1), "preferred": preferred,
                "status": "strict" if preferred else "exact_tie" if lower == upper == 0 else "unknown",
                "exact": lower == upper, "forced_weight_difference_exact": str(wa - wb),
                "cancelled_components": [list(part) for part in common], "unmatched": rows,
                "scope": "full_residual_conditional_value_difference; identical components cancel exactly"}

    def pool_regret(self, chosen, actions, epsilon=1e-8):
        actions = sorted(set(actions) | {chosen})
        if not set(actions) <= self.active:
            raise ValueError("Regret action pool must be feasible at this boundary")
        rows = [self.difference(other, chosen, epsilon) for other in actions if other != chosen]
        lower = max([Fraction(0)] + [Fraction(row["lower_exact"]) for row in rows])
        upper = max([Fraction(0)] + [Fraction(row["upper_exact"]) for row in rows])
        return {"chosen": chosen, "actions": actions, "lower_exact": str(lower), "upper_exact": str(upper),
                "lower": outward(lower, -1), "upper": outward(upper, 1), "comparisons": rows,
                "unknown_comparisons": sum(row["status"] == "unknown" for row in rows),
                "scope": "regret relative to finite actual-action pool; upper is not an upper bound on all-action regret"}

    def receipt(self):
        return {"calls": self.calls, "expanded_nodes": self.expanded_nodes,
                "elapsed_seconds": self.total_difference_seconds, "solve_elapsed_seconds": self.elapsed_seconds,
                "cache_components": len(self.cache), "max_nodes": self.max_nodes, "max_calls": self.max_calls}


def guided_candidates():
    """Twelve predetermined typed proposals authored in this assistant turn."""
    neighbor = {"op": "neighbors", "args": [{"op": "root", "args": []}]}
    ng = {"name": "ng", "expression": {"op": "greedy_independent_weight", "args": [neighbor]}}
    nc = {"name": "nc", "expression": {"op": "clique_cover_weight", "args": [neighbor]}}
    ec = {"name": "ec", "expression": NEIGHBOR_EDGE_COUNT}
    em = {"name": "em", "expression": NEIGHBOR_EDGE_MIN}
    retained = {"op": "difference", "args": [{"op": "difference", "args": [
        {"op": "available", "args": []}, neighbor]},
        {"op": "singleton", "args": [{"op": "root", "args": []}]}]}
    rc = {"name": "residual_cover", "expression": {"op": "clique_cover_weight", "args": [retained]}}
    rg = {"name": "residual_greedy", "expression": {"op": "greedy_independent_weight", "args": [retained]}}
    backup = "weight*(1+2*ec/max(1,degree*(degree-1)))/(1+conflict_weight/max(0.000001,weight))"
    templates = [
        ("feasible_ratio_g12", [ng], "weight/max(0.000001,weight,ng)"),
        ("upper_ratio", [nc], "weight/max(0.000001,weight,nc)"),
        ("midpoint_ratio", [ng, nc], "weight/max(0.000001,weight,(ng+nc)/2)"),
        ("ambiguity_discount", [ng, nc], "weight/max(0.000001,weight,ng)-max(0,nc-ng)/max(0.000001,weight+nc)"),
        ("feasible_loss", [ng], "weight-ng"),
        ("upper_loss", [nc], "weight-nc"),
        ("interval_normalized_ratio", [ng, nc], "weight/max(0.000001,weight,(ng+nc)/2)/(1+max(0,nc-ng)/max(0.000001,nc))"),
        ("feasible_pair_hybrid", [ng, em], "weight/max(0.000001,weight,(ng+max(max_conflict_weight,conflict_weight-em))/2)"),
        ("feasible_density_hybrid", [ng, ec], "weight/max(0.000001,weight,ng)+2*ec/max(1,degree*(degree-1))*weight/max(0.000001,weight+conflict_weight)"),
        ("density_gap_ratio", [ng, nc, ec], "weight/max(0.000001,weight,ng+max(0,nc-ng)/(1+2*ec/max(1,degree*(degree-1))))"),
        ("retained_guard_64", [rc, rg, ec], "weight+(residual_cover+residual_greedy)/2 if remaining_count<=64 else " + backup),
        ("retained_guard_128", [rc, rg, ec], "weight+(residual_cover+residual_greedy)/2 if remaining_count<=128 else " + backup),
    ]
    return [FeatureRuleProgram("v04_" + name, features, rule,
            "Predetermined assistant-authored TRAIN-only proposal; neighborhood packing/cover summaries are heuristic features, not a global ranking guarantee.").to_dict()
            for name, features, rule in templates]


def build_bank(discovery):
    from .discovery_study import enumeration
    from .scale_study import methods
    entries = []
    arms = {"guided_v04": guided_candidates(), "enumerated_v03": enumeration(),
            "baseline": [p.to_dict() for p in methods()]}
    for arm in ("free", "rule"):
        value = json.loads((Path(discovery) / (arm + "_batch.json")).read_text(encoding="utf-8"))
        arms[arm + "_v03"] = value["candidates"]
    old = json.loads((Path(discovery) / "guided_batch.json").read_text(encoding="utf-8"))["candidates"]
    arms["prior_guided_controls"] = [p for p in old if p["name"] in
        ("g03_density_adjusted_weight_pressure", "g05_diminishing_pair_discount", "g12_neighborhood_greedy_value_ratio", "g18_retained_bracket_midpoint")]
    for arm, bank in arms.items():
        for index, source in enumerate(bank):
            program = FeatureRuleProgram.from_dict(source)
            entries.append({"id": arm + ":" + str(index), "arm": arm, "index": index,
                            "program": program.to_dict(), "program_sha256": _hash(program.to_dict())})
    return entries


def load_train(path, *, min_contacts=64, max_contacts=128, per_stratum=2):
    """Read only training graphs; validation values/old result records are unused."""
    path = Path(path)
    if path.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(path) as archive:
            member = archive.getmember("development_scale_001/data.json")
            payload = archive.extractfile(member).read()
    else:
        payload = path.read_bytes()
    data = json.loads(payload)
    if "train" not in data or any(k in data for k in ("test", "transfer", "results", "outcomes")):
        raise ValueError("TRAIN engine rejects test/transfer/outcome containers")
    selected, counts = [], Counter()
    for pair in sorted(data["train"], key=lambda p: p["id"]):
        if pair.get("source", {}).get("split", "train") != "train":
            raise ValueError("Non-training record inside training container")
        if pair.get("family") == "diagnostic" or "probe" in pair.get("source", {}).get("origin", ""):
            continue
        n = len(pair["left"]["contacts"])
        if not min_contacts <= n <= max_contacts:
            continue
        parameter = pair.get("source", {}).get("parameter", "station_gap")
        stratum = (pair["family"], n, parameter)
        if per_stratum is not None and counts[stratum] >= per_stratum:
            continue
        counts[stratum] += 1
        selected.append(pair)
    return selected, {"source": str(path), "data_sha256": sha256(payload).hexdigest(),
                      "allowed_selection_split": "train", "selected_pair_ids": [p["id"] for p in selected],
                      "training_graph_digests": sorted({_graph_digest(pair[side]) for pair in data["train"] for side in ("left", "right")}),
                      "validation_and_test_outcomes_used": False}


def _graph_digest(value):
    return Graph.from_dict(value).digest()


class _CPUCap(TimeoutError):
    pass


class _Meter(dict):
    def __init__(self, seconds):
        super().__init__()
        self.deadline = time.process_time() + seconds
        self.writes = 0

    def __setitem__(self, key, value):
        self.writes += 1
        if self.writes % 128 == 0 and time.process_time() > self.deadline:
            raise _CPUCap("Cooperative CPU inference budget exceeded")
        super().__setitem__(key, value)


def _argmax(graph, program, fixed, excluded, seconds):
    active = graph.available(fixed, excluded)
    if not active:
        return None
    evaluator = CompiledEvaluator(graph, program, active, _Meter(seconds), score_slice=True)
    return min(active, key=lambda v: (-evaluator.score(v), v))


def train_context(task):
    """Complete schedules, coverage-planned real boundaries, shared action pool."""
    pair, side, bank, config = task
    graph, fixed, excluded = Graph.from_dict(pair[side]), tuple(pair.get("fixed", ())), tuple(pair.get("excluded", ()))
    rows, states = [], {}
    for entry in bank:
        program = FeatureRuleProgram.from_dict(entry["program"])
        started, cpu = time.perf_counter(), time.process_time()
        try:
            result = schedule_compiled(graph, program, fixed, excluded,
                meter=_Meter(config["program_cpu_seconds"]), score_slice=True)
            row = {"candidate_id": entry["id"], "completed": True, "value": result["value"],
                   "feature_work": result["feature_work"], "selected": result["selected"], "trace": result["trace"]}
            chosen = list(fixed)
            for step in range(config["max_rollout_steps"] + 1):
                state_key = tuple(sorted(chosen))
                state = states.setdefault(state_key, {"fixed": list(state_key), "sources": [], "id": _hash([graph.digest(), state_key, excluded])})
                state["sources"].append({"candidate_id": entry["id"], "step": step})
                if step >= config["max_rollout_steps"] or step >= len(result["trace"]):
                    break
                chosen.append(result["trace"][step]["selected"])
        except _CPUCap:
            row = {"candidate_id": entry["id"], "completed": False, "value": None,
                   "feature_work": None, "selected": None, "trace": None, "status": "CPU_budget_exceeded"}
        row.update(cpu_seconds=time.process_time() - cpu, wall_seconds=time.perf_counter() - started)
        rows.append(row)
    initial = tuple(sorted(fixed))
    planned = sorted(states.items(), key=lambda item: (item[0] != initial, -len(item[1]["sources"]), item[1]["id"]))[:config["max_states_per_context"]]
    audits = []
    for _, state in planned:
        active = graph.available(state["fixed"], excluded)
        if not active:
            continue
        choices, failures = {}, []
        for entry in bank:
            try:
                choices[entry["id"]] = _argmax(graph, FeatureRuleProgram.from_dict(entry["program"]),
                    state["fixed"], excluded, config["program_cpu_seconds"])
            except _CPUCap:
                failures.append(entry["id"])
        actions = sorted(set(v for v in choices.values() if v is not None))
        oracle = CancelledCompletionOracle(graph, state["fixed"], excluded,
            **config["cancellation"])
        # Cache each unordered delta once. The action-order plan is fixed before
        # querying; budget differences are explicit, not hidden outcome filters.
        deltas = [oracle.difference(a, b, config["epsilon"]) for i, a in enumerate(actions) for b in actions[i + 1:]]
        regret = {}
        own_sources = {source["candidate_id"] for source in state["sources"]}
        for cid, chosen in choices.items():
            lower, upper, unknown = Fraction(0), Fraction(0), 0
            for delta in deltas:
                if chosen not in (delta["a"], delta["b"]):
                    continue
                lo, hi = Fraction(delta["lower_exact"]), Fraction(delta["upper_exact"])
                if chosen == delta["a"]:
                    lo, hi = -hi, -lo
                lower, upper = max(lower, lo), max(upper, hi)
                unknown += delta["status"] == "unknown"
            regret[cid] = {"chosen": chosen, "actual_reached_in_recorded_rollout": cid in own_sources,
                "lower_exact": str(lower), "upper_exact": str(upper), "lower": outward(lower, -1),
                "upper": outward(upper, 1), "unknown_comparisons": unknown}
        # Matched zero-search full-residual baseline, same actions/boundary; it
        # measures cancellation itself separately from extra branch exploration.
        matched = []
        for delta in deltas[:config["max_matched_full_comparisons"]]:
            a, b = delta["a"], delta["b"]
            la = local_bound(graph, {a, b}, a, state["fixed"], excluded, max_nodes=0)
            lb = local_bound(graph, {a, b}, b, state["fixed"], excluded, max_nodes=0)
            zero = CancelledCompletionOracle(graph, state["fixed"], excluded, nodes_per_component=0,
                max_search_component=config["cancellation"]["max_search_component"], max_nodes=0, max_calls=config["cancellation"]["max_calls"])
            cd = zero.difference(a, b, config["epsilon"])
            matched.append({"a": a, "b": b, "full_lower_exact": str(Fraction(la.lower_exact) - Fraction(lb.upper_exact)),
                "full_upper_exact": str(Fraction(la.upper_exact) - Fraction(lb.lower_exact)),
                "cancelled_zero_node": cd})
        audits.append({**state, "excluded": list(excluded), "actions": actions, "choices": choices,
            "choice_failures": failures, "regret": regret, "differences": deltas,
            "oracle_budget": oracle.receipt(), "matched_full_residual": matched,
            "counterfactual_choices_not_used_for_selection": True})
    return {"pair_id": pair["id"], "side": side, "family": pair["family"], "size": len(graph.nodes),
        "graph": graph.to_dict(), "rows": rows, "states": audits, "state_pool_count": len(states),
        "states_planned": len(planned), "states_unsampled": len(states) - len(planned),
        "scope": "TRAIN only; finite actual-action pool regret; score_slice=True uniformly"}


def fresh_temporal_pair(split, size, index, regime, profile="standard", namespace=40000000):
    """Fresh namespace, disjoint from v03; no oracle or outcome-based filtering."""
    splits = ("train", "validation", "test")
    if split not in splits or profile not in ("standard", "dense_long"):
        raise ValueError("Invalid fresh split/profile")
    if type(index) is not int or not 0 <= index < 1000:
        raise ValueError("Fresh indices must be in [0,1000)")
    seed = namespace + splits.index(split) * 1000000 + size * 1000 + index
    if profile == "dense_long":
        seed += 100000000
    rng = random.Random(seed)
    satellites, grounds = {"balanced": (8, 6), "ground_scarce": (12, 3), "satellite_scarce": (3, 12)}[regime]
    horizon = size * (1.8 if profile == "standard" else .18)
    shift = splits.index(split) * 10000000 + index * 10000
    contacts = []
    for _ in range(size):
        start = rng.randrange(int(horizon * 4)) / 4
        duration = rng.randrange(2, 49 if profile == "standard" else 193) / 4
        contacts.append(Contact(f"v{rng.getrandbits(64):016x}", rng.randrange(1, 81) / 4,
            f"S{rng.randrange(satellites)}", f"G{rng.randrange(grounds)}", shift + start, shift + start + duration))
    gaps = ((0., 2.), (.25, 3.5), (.5, 6.))[splits.index(split)]
    name = f"v04_{profile}_{split}_{regime}_{size}_{index:04d}"
    left = temporal_graph(name + "_left", contacts, gaps[0], 0)
    right = temporal_graph(name + "_right", contacts, gaps[1], 0)
    return {"id": name, "family": profile + "_" + regime, "left": left.to_dict(), "right": right.to_dict(),
        "fixed": [], "excluded": [], "source": {"split": split, "seed": seed, "namespace": namespace,
        "size": size, "profile": profile, "regime": regime, "outcome_filtering": False,
        "origin": "v04_fresh_generator"}}


def fresh_temporal_data(config, splits=("validation", "test")):
    result = {split: [] for split in splits}
    seed_ids = {}
    for split in splits:
        for profile in config["profiles"]:
            for regime in config["regimes"]:
                for size in config["sizes"]:
                    for index in range(config["per_cell"][split]):
                        pair = fresh_temporal_pair(split, size, index, regime, profile, config["seed_namespace"])
                        key = (profile, size, pair["source"]["seed"])
                        # Same seed across regimes is deliberate pairing; across
                        # splits is forbidden and must never be counted independent.
                        if key in seed_ids and seed_ids[key] != split:
                            raise ValueError("Fresh split seed overlap")
                        seed_ids[key] = split
                        result[split].append(pair)
    return result


def _information_audit(contexts, bank, specs, training_digests, config):
    base = FeatureRuleProgram("base_information_interface", [], "weight")
    occurrences, endpoints, requirements = {}, {}, []
    def append(graph, fixed, excluded, preferred, other, metadata):
        active = graph.available(fixed, excluded)
        state = _FeatureState(graph, active, None)
        prefix = _hash([graph.digest(), sorted(fixed), sorted(excluded)])
        ids = []
        for node in (preferred, other):
            oid = prefix + ":" + node
            occurrences[oid] = state.feature_values(base, node)
            endpoints[oid] = (graph, set(active), node)
            ids.append(oid)
        requirements.append({"preferred": ids[0], "other": ids[1], "metadata": metadata})
    for context in contexts:
        graph = Graph.from_dict(context["graph"])
        for state in context["states"]:
            for delta in state["differences"]:
                preferred = delta["preferred"]
                if preferred is None:
                    continue
                other = delta["b"] if preferred == delta["a"] else delta["a"]
                append(graph, state["fixed"], state["excluded"], preferred, other,
                    {"kind": "cancelled_actual_action", "pair_id": context["pair_id"], "side": context["side"]})
    known = set(training_digests)
    for spec in specs:
        for side in ("left", "right"):
            graph = Graph.from_dict(spec[side])
            if graph.digest() not in known:
                raise ValueError("Seed evidence is not from supplied training graphs")
            preferred = spec[side + "_preferred"]
            other = spec["b"] if preferred == spec["a"] else spec["a"]
            bounds = spec["bounds"]
            positive = bounds[side + ("_a" if preferred == spec["a"] else "_b")]
            negative = bounds[side + ("_b" if preferred == spec["a"] else "_a")]
            if Fraction(positive["lower_exact"]) <= Fraction(negative["upper_exact"]) + Fraction(spec["epsilon"]):
                raise ValueError("Saved seed relation lacks its strict bound inequality")
            append(graph, spec["fixed"], spec["excluded"], preferred, other,
                   {"kind": "prior_training_certificate", "id": spec.get("id"), "side": side})
    catalogue, seen = [], set()
    for source in guided_candidates():
        for feature in source["features"]:
            signature = _hash(feature["expression"])
            if signature not in seen:
                seen.add(signature)
                catalogue.append({"name": "catalogue_" + str(len(catalogue)), "expression": feature["expression"]})
    tables, costs = {}, {}
    for feature in catalogue:
        proposal = FeatureRuleProgram("repair_catalogue", [feature], "weight")
        table, cost = {}, 0
        for oid, (graph, active, node) in endpoints.items():
            meter = {}
            table[oid] = _FeatureState(graph, active, meter).evaluate(proposal._expressions[0][1], node)
            cost += meter["feature_work"]
        tables[feature["name"]], costs[feature["name"]] = table, max(1, cost)
    repair = minimum_cost_vector_refinement(occurrences, requirements, tables, costs,
        max_selected=6, max_rounds=32, max_master_subsets=100000)
    diagnoses = {}
    for entry in bank:
        program = FeatureRuleProgram.from_dict(entry["program"])
        expanded = {oid: program.evaluate_features(graph, node, active)
                    for oid, (graph, active, node) in endpoints.items()}
        diagnoses[entry["id"]] = diagnose_occurrences(expanded, requirements)
    audited = {oid: {**vector, "audit_satellite_trans_time_present": int("satellite_trans_time" in endpoints[oid][0].constraints),
                         "audit_satellite_trans_time": endpoints[oid][0].constraints.get("satellite_trans_time", 0)}
               for oid, vector in occurrences.items()}
    return {"base_quotient": diagnose_occurrences(occurrences, requirements),
        "configuration_audited_quotient": diagnose_occurrences(audited, requirements),
        "master": repair, "catalogue": catalogue, "candidate_quotients": diagnoses,
        "requirements": requirements, "occurrences": len(occurrences),
        "minimum_interface_is_ablation_not_principal_pool_restriction": True,
        "physical_configuration_field_is_audit_not_deployment_input": "satellite_trans_time"}


def select_candidates(contexts, bank, information, config):
    collected = defaultdict(list)
    for context in contexts:
        best = max((row["value"] for row in context["rows"] if row["completed"]), default=0)
        cost_reference = next(row for row in context["rows"] if row["candidate_id"] == "baseline:1")
        for row in context["rows"]:
            regrets = [state["regret"][row["candidate_id"]] for state in context["states"]
                if row["candidate_id"] in state["regret"] and state["regret"][row["candidate_id"]]["actual_reached_in_recorded_rollout"]]
            normalization = max(1.0, statistics.fmean(c["weight"] for c in context["graph"]["contacts"]))
            collected[row["candidate_id"]].append({"family": context["family"],
                "quality": row["value"] / best if row["completed"] and best else 0,
                "completed": row["completed"], "relative_work": row["feature_work"] / max(1, cost_reference["feature_work"] or 1) if row["completed"] else config["timeout_relative_work"],
                "regret_lower": statistics.fmean(r["lower"] / normalization for r in regrets) if regrets else None,
                "regret_upper": statistics.fmean(r["upper"] / normalization for r in regrets) if regrets else None,
                "unknown_comparisons": sum(r["unknown_comparisons"] for r in regrets),
                "reached_audited_states": len(regrets), "cpu_seconds": row["cpu_seconds"]})
    assessments = []
    def macro(rows, field):
        families = defaultdict(list)
        for row in rows:
            if row[field] is not None:
                families[row["family"]].append(row[field])
        return statistics.fmean(statistics.fmean(values) for values in families.values()) if families else None
    for entry in bank:
        rows = collected[entry["id"]]
        quality, cost = macro(rows, "quality"), macro(rows, "relative_work")
        assessments.append({**entry, "macro_train_quality": quality, "macro_relative_work": cost,
            "primary_utility": quality - config["cost_penalty"] * (cost - 1),
            "macro_actual_regret_lower": macro(rows, "regret_lower"), "macro_actual_regret_upper": macro(rows, "regret_upper"),
            "completed": sum(row["completed"] for row in rows), "contexts": len(rows),
            "unknown_comparisons": sum(row["unknown_comparisons"] for row in rows),
            "reached_audited_states": sum(row["reached_audited_states"] for row in rows),
            "contradictory": information["candidate_quotients"][entry["id"]]["contradictory"]})
    programs, selection = {}, {}
    for arm in sorted(set(entry["arm"] for entry in bank)):
        pool = [row for row in assessments if row["arm"] == arm]
        # Rule/baseline arms remain comparators, not silently forced through the
        # joint information gate. No unknown regret threshold excludes a program.
        if arm in ("guided_v04", "free_v03", "enumerated_v03") and config["joint_information_gate"]:
            pool = [row for row in pool if not row["contradictory"]]
        if not pool:
            selection[arm] = {"eligible": 0, "reason": "no_catalogue_program_passes_information_gate"}
            continue
        primary = max(pool, key=lambda row: (row["primary_utility"], -row["index"]))
        band = [row for row in pool if row["primary_utility"] >= primary["primary_utility"] - config["primary_tie_band"]]
        chosen = min(band, key=lambda row: (row["macro_actual_regret_upper"] if row["macro_actual_regret_upper"] is not None else float("inf"),
            row["macro_actual_regret_lower"] if row["macro_actual_regret_lower"] is not None else float("inf"),
            row["unknown_comparisons"], -row["primary_utility"], row["index"]))
        programs[arm], selection[arm] = chosen["program"], {"eligible": len(pool), "within_primary_band": len(band),
            "selected_id": chosen["id"], "primary_only_id": primary["id"], "unknown_is_not_a_hard_gate": True}
        if arm == "guided_v04":
            programs["guided_primary_only_ablation"] = primary["program"]
    return assessments, programs, selection


def run_train(data_path, discovery, config_path, output, workers=4):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    pairs, source = load_train(data_path, **config["training_subset"])
    for regime in config["dense_training"]["regimes"]:
        for size in config["dense_training"]["sizes"]:
            for index in range(config["dense_training"]["per_cell"]):
                pairs.append(fresh_temporal_pair("train", size, index, regime, "dense_long", config["fresh_seed_namespace"]))
    if 2 * len(pairs) > config["max_contexts"]:
        raise ValueError("Prespecified development context cap exceeded")
    bank = build_bank(discovery)
    _write(root / "candidate_bank.json", bank)
    _write(root / "data.json", {"train": pairs})
    _write(root / "config.json", config)
    _write(root / "generation_receipt.json", {"generator": "one continuing Codex assistant agent authoring session with root feedback before any v04 TRAIN outcome", "authoring_sessions": 1,
        "new_guided_proposals": 12, "external_API_calls": 0, "token_usage": None,
        "served_model_identifier": "gpt-6.1-sol", "model_metadata_source": "trusted root turn metadata, verified in docs/AI_ASSISTANCE_V03.md", "candidate_outcome_selection_split": "train",
        "generation_context": "Prior qualitative failure motivates a new method. Old test outcomes are not read or used in numerical candidate selection. Design is not claimed blinded to that prior failure.",
        "scope": "12 fixed proposals versus existing 24-candidate controls; not matched generation compute or multi-batch variance"})
    _write(root / "execution.json", {"source": source, "workers": workers, "score_slice": True,
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")},
        "config_sha256": sha256(Path(config_path).read_bytes()).hexdigest(), "test_outcomes_read": False})
    contexts = []
    tasks = [(pair, side, bank, config) for pair in pairs for side in ("left", "right")]
    with ProcessPoolExecutor(max_workers=workers) as pool, (root / "training_contexts.jsonl").open("w", encoding="utf-8") as stream:
        for future in as_completed([pool.submit(train_context, task) for task in tasks]):
            context = future.result()
            contexts.append(context)
            stream.write(json.dumps(context, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            print(json.dumps({"completed_contexts": len(contexts), "total": len(tasks)}), flush=True)
    contexts.sort(key=lambda row: (row["pair_id"], row["side"]))
    specs = json.loads((Path(discovery) / "seed_specifications.json").read_text(encoding="utf-8")) if config["use_prior_training_certificates"] else []
    information = _information_audit(contexts, bank, specs, source["training_graph_digests"], config)
    _write(root / "information_repair.json", information)
    assessments, programs, selection = select_candidates(contexts, bank, information, config)
    _write(root / "assessments.json", assessments)
    _write(root / "frozen_programs.json", {"programs": programs, "selection": selection, "test_accessed": False,
        "selection_split": "train", "no_validation_or_test_outcome_selection": True,
        "primary_objective": "equal-family mean reward / best observed completed bank schedule minus relative-work penalty",
        "secondary_objective": "within declared utility tie band, minimize finite-pool actual-reached regret upper; unknown is not an exclusion gate",
        "candidate_bank_sha256": sha256((root / "candidate_bank.json").read_bytes()).hexdigest(),
        "config_sha256": sha256((root / "config.json").read_bytes()).hexdigest(), "score_slice": True,
        "minimum_information_interface_is_ablation": True})
    _write(root / "complete.json", {"complete": True, "training_contexts": len(contexts), "candidates": len(bank),
        "selected": {arm: program["name"] for arm, program in programs.items()}})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("train", "fresh-data"), default="train")
    parser.add_argument("--data")
    parser.add_argument("--discovery")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    if args.mode == "train":
        if not args.data or not args.discovery:
            parser.error("TRAIN mode requires --data and --discovery")
        run_train(args.data, args.discovery, args.config, args.out, args.workers)
    else:
        root = Path(args.out)
        root.mkdir(parents=True, exist_ok=False)
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        data = fresh_temporal_data(config)
        _write(root / "data.json", data)
        _write(root / "protocol.json", {"config": config, "no_oracle_or_outcome_filtering": True,
            "c3_pending_separate_disjoint_original_id_manifest": True,
            "counts": {split: len(records) for split, records in data.items()}})


if __name__ == "__main__":
    main()
