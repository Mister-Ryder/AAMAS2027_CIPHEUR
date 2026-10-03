"""Actual-rollout anchored evidence acquisition and decision relevance audits.

Ranking proxies select queries only. Labels come exclusively from sound oracle
intervals after replaying the SAME fixed/excluded contact sets on both sides.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
import random
from time import perf_counter

from .model import Graph, aligned_intervention
from .oracle import certify_pair, solve, local_bound, outward
from .programs import features


def _graph(value):
    return value if isinstance(value, Graph) else Graph.from_dict(value)


def rank_actions(graph, program, active):
    """Use the same score-descending, contact-ID tie break as the feasible kernel."""
    active = set(active)
    if hasattr(program, "evaluate_features"):
        scores = {v: program.score(graph, v, active) for v in sorted(active)}
    else:
        scores = {v: program.score(features(graph, v, active)) for v in sorted(active)}
    order = sorted(active, key=lambda v: (-scores[v], v))
    return {"order": order, "scores": scores, "positions": {v: i + 1 for i, v in enumerate(order)}}


def residual_fingerprint(graph, fixed, excluded):
    payload = {"graph": graph.digest(), "fixed": sorted(fixed), "excluded": sorted(excluded),
               "active": sorted(graph.available(fixed, excluded))}
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def rollout_states(graph, program, fixed=(), excluded=(), max_steps=None):
    """Return actual successive kernel boundaries, never constructed partial sets."""
    if max_steps is not None and (type(max_steps) is not int or max_steps < 0):
        raise ValueError("Rollout step limit must be nonnegative or None")
    fixed, excluded = tuple(fixed), tuple(excluded)
    chosen, states = list(fixed), []
    active = graph.available(chosen, excluded)
    while active and (max_steps is None or len(states) < max_steps):
        ranking = rank_actions(graph, program, active)
        action = ranking["order"][0]
        states.append({"step": len(states), "fixed": sorted(chosen), "excluded": sorted(excluded),
                       "actual_next_action": action, "ranking": ranking,
                       "residual_fingerprint": residual_fingerprint(graph, chosen, excluded)})
        chosen.append(action)
        active = graph.available(chosen, excluded)
    if not graph.feasible(chosen):
        raise AssertionError("Rollout commitment witness is infeasible")
    return states


def acquire_rollout_evidence(pairs, program, budget, *, fixed=None, excluded=None,
                             strategy="anchored", anchor_sides=("left", "right"),
                             max_steps=None, max_attempts=100, max_witnesses=None,
                             nodes_per_call=10000, max_region=64, epsilon=1e-8,
                             upper_method="weighted_clique_cover", seed=0):
    """Certify actual argmax versus a common adjacent feasible challenger.

    Pairs may be (Graph, Graph) tuples or experiment records with left/right and
    fixed/excluded. None means use record boundaries; supplied sets override them.
    ``uniform`` samples an eligible challenger and permutes queries as a control.
    Edge-preserving interventions remain eligible. Every saved attempt includes
    alignment failures and consumed budget; no heuristic proxy is ever a label.
    """
    if strategy not in ("anchored", "uniform"):
        raise ValueError("Unknown anchored acquisition strategy")
    if any(side not in ("left", "right") for side in anchor_sides):
        raise ValueError("Anchor side must be left or right")
    for value in (max_attempts, max_witnesses):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Acquisition limits must be nonnegative integers")
    if max_attempts == 0 or max_witnesses == 0:
        return [], []
    rng, queries = random.Random(seed), []
    for index, pair in enumerate(pairs):
        record = pair if isinstance(pair, dict) else {}
        left = _graph(record["left"] if record else pair[0])
        right = _graph(record["right"] if record else pair[1])
        initial_fixed = tuple(record.get("fixed", ())) if fixed is None else tuple(fixed)
        initial_excluded = tuple(record.get("excluded", ())) if excluded is None else tuple(excluded)
        identity = record.get("id", str(index))
        pair_request = {"pair": index, "id": identity, "family": record.get("family"),
                        "rollout_program": program.to_dict(), "strategy": strategy,
                        "initial_fixed": sorted(initial_fixed), "initial_excluded": sorted(initial_excluded),
                        "graph_fingerprints": {"left": left.digest(), "right": right.digest()}}
        try:
            aligned_intervention(left, right, initial_fixed, initial_excluded)
        except ValueError as error:
            queries.append((None, {**pair_request, "failure_reason": "invalid_alignment", "error": str(error)}))
            continue
        for anchor_side in anchor_sides:
            graph = left if anchor_side == "left" else right
            for state in rollout_states(graph, program, initial_fixed, initial_excluded, max_steps):
                boundary, exclusions = tuple(state["fixed"]), tuple(state["excluded"])
                request = {**pair_request, "anchor_side": anchor_side, "step": state["step"],
                           "fixed": list(boundary), "excluded": list(exclusions),
                           "actual_next_action": state["actual_next_action"],
                           "anchor_rollout_residual_fingerprint": state["residual_fingerprint"]}
                try:
                    intervention = aligned_intervention(left, right, boundary, exclusions)
                    active = {"left": left.available(boundary, exclusions),
                              "right": right.available(boundary, exclusions)}
                except ValueError as error:
                    queries.append((None, {**request, "failure_reason": "invalid_boundary_replay", "error": str(error)}))
                    continue
                rankings = {side: rank_actions(g, program, active[side])
                            for side, g in (("left", left), ("right", right))}
                a = state["actual_next_action"]
                common = active["left"] & active["right"]
                eligible = sorted(common & left.adj[a] & right.adj[a]) if a in common else []
                request.update(intervention=intervention,
                    residual_fingerprints={side: residual_fingerprint(g, boundary, exclusions)
                                           for side, g in (("left", left), ("right", right))},
                    actual_next_actions={side: rank["order"][0] if rank["order"] else None
                                         for side, rank in rankings.items()},
                    eligible_challengers=eligible)
                if not eligible:
                    queries.append((None, {**request, "failure_reason": "no_common_adjacent_challenger"}))
                    continue
                b = (rng.choice(eligible) if strategy == "uniform" else
                     min(eligible, key=lambda v: (rankings[anchor_side]["positions"][v], v)))
                request.update(a=a, b=b,
                    rank_positions={side: {v: rankings[side]["positions"][v] for v in (a, b)} for side in rankings},
                    action_scores={side: {v: rankings[side]["scores"][v] for v in (a, b)} for side in rankings},
                    anchor_is_actual_argmax=rankings[anchor_side]["order"][0] == a)
                if not request["anchor_is_actual_argmax"]:
                    raise AssertionError("Saved anchor is not the actual rollout action")
                queries.append(((left, right, boundary, exclusions), request))
    if strategy == "uniform":
        rng.shuffle(queries)
    specifications, attempts = [], []
    for context, request in queries[:max_attempts]:
        before, started = budget.to_dict(), perf_counter()
        if context is None:
            attempts.append({"request": request, "reason": request["failure_reason"],
                             "details": {"reason": request["failure_reason"]},
                             "before": before, "after": budget.to_dict(), "elapsed_seconds": perf_counter() - started})
            continue
        left, right, boundary, exclusions = context
        witness, detail = certify_pair(left, right, request["a"], request["b"], budget,
            boundary, exclusions, epsilon, nodes_per_call=nodes_per_call, max_region=max_region,
            include_preservation=True, upper_method=upper_method, raise_on_exhaustion=False)
        attempts.append({"request": request, "reason": detail["reason"], "details": detail,
                         "before": before, "after": budget.to_dict(), "elapsed_seconds": perf_counter() - started})
        if witness is not None:
            witness.update(id=f"{request['id']}:{request['anchor_side']}:{request['step']}:{len(specifications)}",
                           family=request["family"], acquisition=request)
            witness["current_program_failed"] = any(
                request["action_scores"][side][witness[side + "_preferred"]] <=
                request["action_scores"][side][witness["b"] if witness[side + "_preferred"] == witness["a"] else witness["a"]] + epsilon
                for side in ("left", "right"))
            specifications.append(witness)
            if max_witnesses is not None and len(specifications) >= max_witnesses:
                break
        if detail["reason"] == "budget_exhausted":
            break
    return specifications, attempts


def evidence_relevance(program, specifications, *, regret_nodes=None):
    """Report semantic boundary reachability, escape, choice consistency and regret.

    Optional regret intervals use separately budgeted offline reference solves;
    they are not added to evidence or consulted by deployment.
    """
    rows, rollout_cache = [], {}
    for index, spec in enumerate(specifications):
        metadata = spec.get("acquisition", {})
        initial_fixed = tuple(metadata.get("initial_fixed", ()))
        initial_excluded = tuple(metadata.get("initial_excluded", ()))
        for side in ("left", "right"):
            graph = _graph(spec[side])
            cache_key = (graph.digest(), frozenset(initial_fixed), frozenset(initial_excluded))
            if cache_key not in rollout_cache:
                rollout_cache[cache_key] = rollout_states(graph, program, initial_fixed, initial_excluded)
            reached = any(set(state["fixed"]) == set(spec["fixed"]) and
                          set(state["excluded"]) == set(spec["excluded"])
                          for state in rollout_cache[cache_key])
            active = graph.available(spec["fixed"], spec["excluded"])
            ranking = rank_actions(graph, program, active)
            chosen = ranking["order"][0] if ranking["order"] else None
            escape = chosen not in (spec["a"], spec["b"])
            row = {"specification": spec.get("id", str(index)), "side": side,
                   "boundary_reachable": reached, "next_action": chosen, "next_action_escape": escape,
                   "chosen_action_consistent": chosen == spec[side + "_preferred"] if not escape else None,
                   "rank_positions": {v: ranking["positions"][v] for v in (spec["a"], spec["b"])}}
            if regret_nodes is not None and reached and chosen is not None:
                reference = solve(graph, fixed=spec["fixed"], excluded=spec["excluded"], max_nodes=regret_nodes)
                conditional = local_bound(graph, graph.nodes, chosen, spec["fixed"], spec["excluded"], regret_nodes)
                lower = max(Fraction(0), Fraction(reference.lower_exact) - Fraction(conditional.upper_exact))
                upper = max(Fraction(0), Fraction(reference.upper_exact) - Fraction(conditional.lower_exact))
                row["conditional_regret"] = {"lower_exact": str(lower), "upper_exact": str(upper),
                                              "lower": outward(lower, -1), "upper": outward(upper, 1),
                                              "reference_exact": reference.exact,
                                              "chosen_completion_exact": conditional.exact,
                                              "expanded_nodes": reference.expanded + conditional.expanded}
            rows.append(row)
    choices = [row for row in rows if row["chosen_action_consistent"] is not None]
    return {"rows": rows, "total_side_requirements": len(rows),
            "boundary_reachable": sum(row["boundary_reachable"] for row in rows),
            "next_action_escape": sum(row["next_action_escape"] for row in rows),
            "pair_choices": len(choices), "consistent_pair_choices": sum(row["chosen_action_consistent"] for row in choices),
            "reachability_fraction": sum(row["boundary_reachable"] for row in rows) / len(rows) if rows else None,
            "escape_fraction": sum(row["next_action_escape"] for row in rows) / len(rows) if rows else None,
            "pair_choice_consistency": sum(row["chosen_action_consistent"] for row in choices) / len(choices) if choices else None}
