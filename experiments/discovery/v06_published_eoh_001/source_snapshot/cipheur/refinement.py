"""Exact finite-catalogue, cycle-join separating representation repair.

Each master cut hits a concrete closed alternating walk. Every master solution
is separated against the ENTIRE refined quotient, including parallel evidence
and self-loops. A repaired exact master is therefore a minimum for the fixed
catalogue, observations and additive costs, not for the rule DSL or unseen data.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import math
from time import perf_counter

from .graph_features import FeatureRuleProgram, MAX_FEATURES, _FeatureState
from .model import Graph
from .representation import vector_key


def diagnose_occurrences(occurrences, requirements, feature_values=None, selected=()):
    """Build full exact quotient and one witnessed cycle with concrete joins.

    ``occurrences`` maps occurrence IDs to base numeric vectors. Requirements
    contain ``preferred`` and ``other`` occurrence IDs, with optional metadata.
    ``feature_values`` maps feature names to {occurrence ID: numeric value}.
    """
    feature_values = {} if feature_values is None else feature_values
    keys, vectors = {}, {}
    for oid, base in occurrences.items():
        values = dict(base)
        for name in selected:
            if name in values:
                raise ValueError("Proposed feature collides with the base interface")
            values[name] = feature_values[name][oid]
        keys[oid] = vector_key(values)
        vectors[oid] = values
    adjacency, evidence = defaultdict(set), defaultdict(list)
    for index, req in enumerate(requirements):
        p, n = req["preferred"], req["other"]
        if p not in keys or n not in keys:
            raise ValueError("Requirement has an unknown concrete endpoint")
        u, v = keys[p], keys[n]
        adjacency[u].add(v)
        adjacency[v]
        evidence[u, v].append(index)
    color, parent, cycle = {}, {}, None
    for start in sorted(adjacency):
        if color.get(start, 0):
            continue
        color[start] = 1
        stack = [(start, iter(sorted(adjacency[start])))]
        while stack and cycle is None:
            u, children = stack[-1]
            try:
                v = next(children)
            except StopIteration:
                color[u] = 2
                stack.pop()
                continue
            if not color.get(v, 0):
                parent[v] = u
                color[v] = 1
                stack.append((v, iter(sorted(adjacency[v]))))
            elif color[v] == 1:
                cycle = [u]
                while cycle[-1] != v:
                    cycle.append(parent[cycle[-1]])
                cycle.reverse()
                cycle.append(v)
        if cycle is not None:
            break
    witnesses = []
    if cycle is not None:
        indices = [evidence[u, v][0] for u, v in zip(cycle, cycle[1:])]
        arcs = [{**requirements[i], "requirement_index": i} for i in indices]
        joins = []
        for i, arc in enumerate(arcs):
            negative, positive = arc["other"], arcs[(i + 1) % len(arcs)]["preferred"]
            if keys[negative] != keys[positive]:
                raise AssertionError("Cycle join endpoints must be exactly equal")
            joins.append({"negative": negative, "positive": positive,
                          "negative_vector": vectors[negative], "positive_vector": vectors[positive]})
        witnesses.append({"kind": "self_loop" if len(arcs) == 1 else "directed_cycle",
                          "requirements": arcs, "equality_joins": joins})
    return {"contradictory": cycle is not None, "quotient_nodes": len(adjacency),
            "quotient_edges": len(evidence),
            "self_loop_requirements": sum(len(rows) for (u, v), rows in evidence.items() if u == v),
            "structural_witnesses": witnesses,
            "comparison": "exact_integer_and_binary_float_numeric_equality",
            "acyclic_does_not_prove_dsl_expressibility": True}


def minimum_cost_vector_refinement(occurrences, requirements, feature_values, costs, *,
                                   max_rounds=None, max_master_subsets=None, max_selected=None):
    """Exact branch-and-bound master plus full-quotient separation.

    Finite budgets return a partial repair with ``optimal=False``. No greedy or
    one-pass cover is mislabeled as a global finite-catalogue minimum.
    """
    started = perf_counter()
    for value in (max_rounds, max_master_subsets, max_selected):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Refinement budgets must be nonnegative integers or None")
    names = tuple(sorted(feature_values))
    if set(names) != set(costs):
        raise ValueError("Every catalogue feature needs exactly one cost")
    exact_costs = {}
    for name in names:
        value = costs[name]
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Standalone feature costs must be finite and positive")
        exact_costs[name] = Fraction(value)
        if set(feature_values[name]) != set(occurrences):
            raise ValueError("Catalogue feature must be evaluated at every occurrence")
        for value in feature_values[name].values():
            vector_key({name: value})
    cuts, witnesses, rounds = [], [], []
    selected, evaluated = (), 0
    diagnosis_cache = {}
    def diagnose(subset):
        if subset not in diagnosis_cache:
            diagnosis_cache[subset] = diagnose_occurrences(occurrences, requirements, feature_values, subset)
        return diagnosis_cache[subset]
    reason, repaired, optimal = "", False, False
    # Exact search is deliberately bounded on request, not silently greedy.
    while True:
        current = diagnose(selected)
        if not current["contradictory"]:
            reason, repaired, optimal = "repaired", True, True
            break
        if max_rounds is not None and len(rounds) >= max_rounds:
            reason = "separation_budget_exhausted"
            break
        witness = current["structural_witnesses"][0]
        cover = tuple(name for name in names if any(
            Fraction(feature_values[name][join["negative"]]) != Fraction(feature_values[name][join["positive"]])
            for join in witness["equality_joins"]))
        witness = {**witness, "id": len(witnesses), "separating_features": list(cover),
                   "separated_after_selected": list(selected)}
        witnesses.append(witness)
        if not cover:
            reason = "catalogue_cannot_separate_witness"
            break
        cut = frozenset(cover)
        if cut in cuts:
            raise AssertionError("A covered concrete walk cannot survive a refined quotient")
        cuts.append(cut)
        best, best_key, master_complete = None, None, True
        visited, pending = set(), [frozenset()]
        while pending:
            subset_set = pending.pop()
            if subset_set in visited:
                continue
            if max_master_subsets is not None and evaluated >= max_master_subsets:
                master_complete = False
                break
            visited.add(subset_set)
            evaluated += 1
            subset = tuple(sorted(subset_set))
            if max_selected is not None and len(subset) > max_selected:
                continue
            cost = sum((exact_costs[name] for name in subset), Fraction(0))
            if best_key is not None and cost > best_key[0]:
                continue
            uncovered = [constraint for constraint in cuts if not subset_set & constraint]
            if not uncovered:
                key = (cost, len(subset), subset)
                if best_key is None or key < best_key:
                    best, best_key = subset, key
                continue
            if max_selected is not None and len(subset) >= max_selected:
                continue
            # Every feasible repair must choose a member of this uncovered cut.
            # Positive costs make supersets of an already covered set dominated.
            cut = min(uncovered, key=lambda c: (len(c), tuple(sorted(c))))
            for name in sorted(cut, key=lambda n: (exact_costs[n], n), reverse=True):
                pending.append(subset_set | {name})
        if not master_complete:
            # The best fully separated candidate encountered may be feasible,
            # but truncated search cannot establish cost minimality.
            if best is not None:
                selected = best
                repaired = not diagnose(selected)["contradictory"]
            reason = "master_budget_exhausted"
            break
        if best is None:
            reason = "catalogue_infeasible_under_cardinality_limit"
            break
        selected = best
        separated = diagnose(selected)  # Required full recheck after EVERY solve.
        rounds.append({"round": len(rounds), "selected_names": list(selected),
                       "cost_exact": str(best_key[0]), "master_globally_optimal": True,
                       "full_quotient_rechecked": True, "quotient": separated,
                       "cuts": [sorted(c) for c in cuts], "master_subsets_evaluated": evaluated})
    final = diagnose(selected)
    total = sum((exact_costs[name] for name in selected), Fraction(0))
    return {"selected_names": list(selected), "cost": float(total), "cost_exact": str(total),
            "repaired": repaired, "optimal": optimal and repaired, "reason": reason,
            "rounds": rounds, "witnesses": witnesses, "diagnosis": final,
            "master_subsets_evaluated": evaluated, "quotient_evaluations": len(diagnosis_cache),
            "elapsed_seconds": perf_counter() - started,
            "objective_scope": "fixed_evidence_finite_catalogue_additive_standalone_feature_cost",
            "max_selected": max_selected, "rule_expressibility_proved": False}


def minimum_cost_refinement(program, specifications, catalogue, costs=None, *,
                            max_rounds=None, max_master_subsets=None):
    """Type-check proposals, evaluate exact joins, then repair an observed interface."""
    names = [entry.get("name") for entry in catalogue]
    if len(names) != len(set(names)):
        raise ValueError("Catalogue names must be unique")
    if set(names) & set(program.feature_names):
        raise ValueError("Catalogue collides with the existing representation")
    proposal_programs = {entry["name"]: FeatureRuleProgram("proposal", [entry], "weight") for entry in catalogue}
    occurrences, requirements, values = {}, [], {name: {} for name in names}
    endpoints, measured_costs, evaluations = {}, {name: 0 for name in names}, {}
    for index, spec in enumerate(specifications):
        for side in ("left", "right"):
            graph = spec[side] if isinstance(spec[side], Graph) else Graph.from_dict(spec[side])
            active = graph.available(spec["fixed"], spec["excluded"])
            preferred = spec[side + "_preferred"]
            other = spec["b"] if preferred == spec["a"] else spec["a"]
            ids = []
            for node in (preferred, other):
                oid = f"{index}:{side}:{node}"
                ids.append(oid)
                cache_key = (graph.digest(), frozenset(active), node)
                if cache_key not in evaluations:
                    base = program.evaluate_features(graph, node, active)
                    proposal_values, work = {}, {}
                    for name, candidate in proposal_programs.items():
                        meter = {}
                        expression = candidate._expressions[0][1]
                        proposal_values[name] = _FeatureState(graph, active, meter).evaluate(expression, node)
                        work[name] = meter["feature_work"]
                    evaluations[cache_key] = base, proposal_values, work
                base, proposed, work = evaluations[cache_key]
                occurrences[oid] = base
                endpoints[oid] = {"occurrence": oid, "specification": spec.get("id", str(index)),
                                  "side": side, "contact": node, "graph_fingerprint": graph.digest(),
                                  "fixed": sorted(spec["fixed"]), "excluded": sorted(spec["excluded"])}
                for name in names:
                    values[name][oid] = proposed[name]
                    measured_costs[name] += work[name]
            requirements.append({"preferred": ids[0], "other": ids[1],
                                 "metadata": {"specification": spec.get("id", str(index)), "side": side}})
    effective_costs = {name: max(1, measured_costs[name]) for name in names} if costs is None else costs
    result = minimum_cost_vector_refinement(occurrences, requirements, values, effective_costs,
        max_rounds=max_rounds, max_master_subsets=max_master_subsets,
        max_selected=MAX_FEATURES - len(program.features))
    result.update(selected_features=[entry for entry in catalogue if entry["name"] in result["selected_names"]],
                  feature_costs=dict(effective_costs), measured_standalone_work=measured_costs,
                  endpoints=endpoints, feature_evaluation_cache_entries=len(evaluations),
                  rule_repair_required=bool(result["selected_names"]))
    for witness in result["witnesses"]:
        for join in witness["equality_joins"]:
            join["negative_endpoint"] = endpoints[join["negative"]]
            join["positive_endpoint"] = endpoints[join["positive"]]
    return result
