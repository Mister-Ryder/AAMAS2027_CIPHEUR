"""Exact score-local priority execution of an unchanged typed ranking program.

This alternate backend is separate from the frozen compiled runner. Demanded
global inputs conservatively rescore the whole residual graph. For local rules,
cached scores survive only when the scored vertex's neighborhood is unchanged.
No conditional oracle, synthesis service, or native solver is used here.
"""
from __future__ import annotations

import heapq

from .compiled import CompiledEvaluator
from .graph_features import FeatureRuleProgram, _charge


# This is a reviewed whitelist, not inference from depends_on_root. The current
# DSL's only Node producer is root. A future arbitrary-node/multihop primitive
# must be reviewed before extending it.
_LOCAL_OPERATIONS = frozenset({
    "root", "neighbors", "singleton", "union", "intersection", "difference",
    "induced_edges", "count", "sum_weights", "max_weight", "clique_cover_weight",
    "greedy_independent_weight", "edge_min_weight_sum", "edge_weight_product_sum",
    "weight", "duration", "const", "add", "sub", "mul", "div", "min", "max", "abs",
})
_STATIC_INPUTS = frozenset({"weight", "duration", "station_gap", "satellite_gap"})
_NEIGHBOR_INPUTS = frozenset({"degree", "conflict_weight", "max_conflict_weight"})


def score_locality(program: FeatureRuleProgram) -> dict:
    """Conservative syntactic locality of every possibly demanded rule input.

    co_names includes inputs in untaken branches. Unused declared features are
    irrelevant to score-sliced semantics and are not used for this classification.
    """
    if not isinstance(program, FeatureRuleProgram):
        raise TypeError("A typed FeatureRuleProgram is required")
    demanded = set(program.code.co_names) & set(program.feature_names)
    features = dict(program._expressions)
    reasons, dynamic = [], False

    def operations(expr):
        result = {expr.op}
        for child in expr.args:
            result.update(operations(child))
        return result

    for name in sorted(demanded):
        if name in _STATIC_INPUTS:
            continue
        if name in _NEIGHBOR_INPUTS:
            dynamic = True
        elif name in features:
            ops = operations(features[name])
            if "available" in ops:
                reasons.append(name + ":available_leaf")
            elif not ops <= _LOCAL_OPERATIONS:
                reasons.append(name + ":unreviewed_operation")
            dynamic |= "neighbors" in ops
        else:
            reasons.append(name + ":global_or_unreviewed_input")
    return {
        "eligible_local": not reasons,
        "static_scores": not reasons and not dynamic,
        "scorer_inputs": sorted(demanded),
        "global_reasons": reasons,
        "scope": "immutable_graph_and_constraints_current_single_root_DSL",
        "conditional_branch_optimization": False,
    }


def _priority_charge(meter, primitive, amount=1):
    _charge(meter, primitive, amount)
    meter["priority_work"] = meter.get("priority_work", 0) + amount


class _Entry(tuple):
    """The exact (-score, node, version) key, with heap comparisons charged."""
    def __new__(cls, score, node, version, meter, stats):
        result = super().__new__(cls, (-score, node, version))
        result.meter, result.stats = meter, stats
        return result

    def __lt__(self, other):
        _priority_charge(self.meter, "score_heap_compare")
        self.stats["heap_comparisons"] += 1
        return tuple.__lt__(self, other)


def schedule_heap(graph, program: FeatureRuleProgram, fixed=(), excluded=(), meter=None) -> dict:
    """Execute the same lexicographic greedy policy with safe score caching.

    Raises the caller's budget exception unchanged. No partial schedule or other
    backend is returned after a failure. Global rescoring is a declared execution
    mode selected before running, not a timeout fallback.
    """
    locality = score_locality(program)
    fixed, excluded = tuple(fixed), tuple(excluded)
    chosen = list(fixed)
    evaluator = CompiledEvaluator(graph, program, graph.available(fixed, excluded),
                                  meter=meter, score_slice=True)
    meter = evaluator.meter
    meter.setdefault("priority_work", 0)
    stats = {key: 0 for key in (
        "score_evaluations", "initial_score_evaluations", "refresh_score_evaluations",
        "preserved_score_states", "invalidated_scores", "heap_pushes", "heap_pops",
        "heap_comparisons", "stale_entries_discarded", "full_rescore_states",
        "max_heap_entries",
    )}
    versions, heap, trace = {}, [], []

    def refresh(nodes, initial=False):
        for node in sorted(nodes):
            _priority_charge(meter, "score_cache_write")
            version = versions.get(node, -1) + 1
            versions[node] = version
            score = evaluator.score(node)
            stats["score_evaluations"] += 1
            stats["initial_score_evaluations" if initial else "refresh_score_evaluations"] += 1
            _priority_charge(meter, "score_heap_push")
            heapq.heappush(heap, _Entry(score, node, version, meter, stats))
            stats["heap_pushes"] += 1
            stats["max_heap_entries"] = max(stats["max_heap_entries"], len(heap))

    if locality["eligible_local"]:
        refresh(evaluator.active, initial=True)
    while evaluator.active:
        if not locality["eligible_local"]:
            _priority_charge(meter, "score_heap_clear", len(heap))
            heap.clear()
            stats["full_rescore_states"] += 1
            refresh(evaluator.active, initial=not trace)
        while heap:
            _priority_charge(meter, "score_heap_pop")
            entry = heapq.heappop(heap)
            stats["heap_pops"] += 1
            negative_score, node, version = entry
            _priority_charge(meter, "score_heap_validate", 2)
            if node in evaluator.active and versions.get(node) == version:
                break
            stats["stale_entries_discarded"] += 1
        else:
            raise AssertionError("A nonempty active set must have current heap scores")
        trace.append({"selected": node, "score": -negative_score,
                      "remaining_count": len(evaluator.active)})
        chosen.append(node)
        # Discover the frontier BEFORE CompiledEvaluator mutates neighbor sets.
        # It includes neighbors of blocked neighbors, not only selected's neighbors.
        removed = {node} | evaluator.neighbors[node]
        dirty = set()
        if locality["eligible_local"] and not locality["static_scores"]:
            for deleted in sorted(removed):
                adjacent = evaluator.neighbors[deleted]
                _priority_charge(meter, "score_frontier_scan", len(adjacent))
                dirty.update(adjacent)
            dirty.difference_update(removed)
        evaluator.remove({node} | graph.adj[node])
        for deleted in sorted(removed):
            _priority_charge(meter, "score_cache_delete")
            versions.pop(deleted, None)
        if locality["eligible_local"]:
            stats["invalidated_scores"] += len(dirty)
            stats["preserved_score_states"] += len(evaluator.active) - len(dirty)
            refresh(dirty)
    if not graph.feasible(chosen):
        raise AssertionError("Kernel feasibility invariant violated")
    return {
        "selected": sorted(chosen), "value": graph.value(chosen), "feasible": True,
        "trace": trace, **meter, "compilation": dict(evaluator.metadata),
        "score_heap": {
            "backend": "score_local_priority_heap_v04",
            "mode": "static_priority" if locality["static_scores"] else
                    "local_priority" if locality["eligible_local"] else "full_rescore",
            **locality, **stats,
            "work_scope": "compiler_plus_score_cache_frontier_and_actual_heap_operations_comparisons",
            "equivalence_scope": "schedule_compiled_score_slice_true_on_valid_inputs",
            "timeout_fallback": False,
            "stale_heap_memory_bound_claimed": False,
        },
        "locality_scope": locality["scope"],
    }
