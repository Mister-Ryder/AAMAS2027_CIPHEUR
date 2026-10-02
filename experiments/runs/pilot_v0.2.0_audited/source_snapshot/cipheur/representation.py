"""Exact feature-alias diagnosis for finite strict ranking specifications.

A directed cycle is a proof that no deterministic pointwise scalar function of
these vectors can satisfy every observed inequality. Absence of cycles only
establishes satisfiability on this finite quotient, not DSL expressibility.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import math
from .model import Graph


def vector_key(values):
    result = []
    for name, value in sorted(values.items()):
        if not math.isfinite(value):
            raise ValueError("Feature vectors must be finite")
        # Preserve integer precision as well as exact binary floating values.
        # Numeric 1 and 1.0 are equal, but 2**53 and 2**53+1 are distinguishable.
        number = Fraction(value)
        result.append((name, number.numerator, number.denominator))
    return tuple(result)


def ranking_report(program, specifications, margin=1e-8):
    checks = []
    for index, spec in enumerate(specifications):
        for side in ("left", "right"):
            graph = Graph.from_dict(spec[side])
            active = graph.available(spec["fixed"], spec["excluded"])
            a, b = spec["a"], spec["b"]
            scores = {v: program.score(graph, v, active) for v in (a, b)}
            preferred = spec[side + "_preferred"]
            other = b if preferred == a else a
            checks.append({"specification": spec.get("id", str(index)), "side": side,
                           "relation": spec["relation"], "preferred": preferred,
                           "scores": scores, "passed": scores[preferred] > scores[other] + margin})
    return {"passed": sum(row["passed"] for row in checks), "total": len(checks),
            "fraction": sum(row["passed"] for row in checks) / len(checks) if checks else None,
            "all_passed": all(row["passed"] for row in checks), "checks": checks}


def diagnose_representation(program, specifications, max_witnesses=12):
    adjacency, edge_evidence, vectors = defaultdict(set), defaultdict(list), {}
    for index, spec in enumerate(specifications):
        for side in ("left", "right"):
            graph = Graph.from_dict(spec[side])
            active = graph.available(spec["fixed"], spec["excluded"])
            preferred = spec[side + "_preferred"]
            other = spec["b"] if preferred == spec["a"] else spec["a"]
            values = {v: program.evaluate_features(graph, v, active) for v in (preferred, other)}
            u, v = vector_key(values[preferred]), vector_key(values[other])
            adjacency[u].add(v)
            adjacency[v]  # Ensure destinations are also quotient vertices.
            vectors[u], vectors[v] = values[preferred], values[other]
            edge_evidence[u, v].append({"specification": spec.get("id", str(index)),
                "side": side, "preferred": preferred, "other": other,
                "neighbor_sets": {n: sorted(graph.adj[n] & active) for n in (preferred, other)},
                "neighbor_induced_edges": {n: [list(e) for e in sorted(graph.edges)
                    if set(e) <= (graph.adj[n] & active)] for n in (preferred, other)},
                "intervention": spec["intervention"], "fixed": spec["fixed"],
                "excluded": spec["excluded"]})
    # Iterative DFS avoids recursion limits for large accumulated evidence sets.
    if type(max_witnesses) is not int or max_witnesses < 0:
        raise ValueError("max_witnesses must be a nonnegative integer")
    color, parent, cycles, has_cycle = {}, {}, [], False
    for start in sorted(adjacency):
        if color.get(start, 0):
            continue
        color[start] = 1
        stack = [(start, iter(sorted(adjacency[start])))]
        while stack:
            u, children = stack[-1]
            try:
                v = next(children)
            except StopIteration:
                color[u] = 2
                stack.pop()
                continue
            if color.get(v, 0) == 0:
                parent[v] = u
                color[v] = 1
                stack.append((v, iter(sorted(adjacency[v]))))
            elif color[v] == 1:
                has_cycle = True
                cycle = [u]
                while cycle[-1] != v:
                    cycle.append(parent[cycle[-1]])
                cycle.reverse()
                cycle.append(v)
                if len(cycles) < max_witnesses:
                    cycles.append(cycle)
    witnesses = [{"kind": "self_loop" if len(c) == 2 else "directed_cycle",
                  "vectors": [vectors[v] for v in c[:-1]],
                  "requirements": [edge_evidence[a, b][0] for a, b in zip(c, c[1:])]}
                 for c in cycles]
    return {"comparison": "exact_integer_and_binary_float_numeric_equality", "quotient_nodes": len(adjacency),
            "quotient_edges": len(edge_evidence),
            "self_loop_requirements": sum(len(rows) for (u, v), rows in edge_evidence.items() if u == v),
            "contradictory": has_cycle, "structural_witnesses": witnesses,
            "scope": "deterministic_pointwise_scalar_rankings_on_observed_exact_feature_vectors",
            "acyclic_does_not_prove_dsl_expressibility": True}
