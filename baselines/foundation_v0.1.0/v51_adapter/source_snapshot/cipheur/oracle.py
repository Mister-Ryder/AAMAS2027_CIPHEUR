from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import math
import time
from .model import Graph, aligned_intervention


@dataclass
class Bound:
    lower: float
    upper: float
    selected: tuple[str, ...]
    expanded: int
    exact: bool


class Budget:
    def __init__(self, max_calls=100, max_nodes=100000):
        self.max_calls, self.max_nodes = max_calls, max_nodes
        self.calls = self.nodes = 0
        self.seconds = 0.0

    def reserve(self):
        if self.calls >= self.max_calls or self.nodes >= self.max_nodes:
            raise RuntimeError("Oracle budget exhausted")
        self.calls += 1

    def to_dict(self):
        return {"calls": self.calls, "expanded_nodes": self.nodes,
                "elapsed_seconds": self.seconds, "max_calls": self.max_calls,
                "max_nodes": self.max_nodes}


def exact_value(graph, ids):
    # Fraction(float) represents the exact input binary value, without repeated
    # arithmetic rounding. This is the objective defined by the saved graph.
    return sum((Fraction(graph.nodes[v].weight) for v in ids), Fraction(0))


def outward(value, direction):
    rounded = float(value)
    if direction < 0 and Fraction(rounded) > value:
        return math.nextafter(rounded, -math.inf)
    if direction > 0 and Fraction(rounded) < value:
        return math.nextafter(rounded, math.inf)
    return rounded


def solve(graph: Graph, candidates=None, fixed=(), excluded=(), max_nodes=10000) -> Bound:
    """Budgeted branch and bound with valid upper bounds for every frontier node."""
    fixed = tuple(sorted(fixed))
    available = graph.available(fixed, excluded)
    active = available if candidates is None else available & set(candidates)
    weights = {v: Fraction(graph.nodes[v].weight) for v in graph.nodes}
    base = exact_value(graph, fixed)
    frontier = [(frozenset(active), fixed, base)]
    best, chosen, expanded = base, fixed, 0
    def upper(state):
        remaining, _, value = state
        return value + sum((weights[v] for v in remaining), Fraction(0))
    while frontier and expanded < max_nodes:
        remaining, selected, value = frontier.pop()
        expanded += 1
        if value > best:
            best, chosen = value, selected
        if not remaining or value + sum((weights[v] for v in remaining), Fraction(0)) <= best:
            continue
        v = max(sorted(remaining), key=lambda k: (len(graph.adj[k] & remaining), graph.nodes[k].weight))
        rest = remaining - {v}
        frontier.append((rest, selected, value))
        frontier.append((rest - graph.adj[v], selected + (v,), value + weights[v]))
    ub = max([best] + [upper(s) for s in frontier])
    return Bound(outward(best, -1), outward(ub, 1), tuple(sorted(chosen)), expanded, ub == best)


def local_bound(graph, region, action, fixed=(), excluded=(), max_nodes=10000):
    """L completes locally selected nodes globally; U relaxes all cross-boundary edges."""
    boundary = tuple(fixed) + (action,)
    available = graph.available(boundary, excluded)
    interior = available & set(region)
    outside = available - set(region)
    result = solve(graph, interior, boundary, excluded, max_nodes)
    completion = list(result.selected)
    for v in sorted(outside, key=lambda k: (-graph.nodes[k].weight, k)):
        if graph.feasible(completion + [v]):
            completion.append(v)
    lower = exact_value(graph, completion)
    upper = Fraction(result.upper) + exact_value(graph, outside)
    return Bound(outward(lower, -1), outward(upper, 1), tuple(sorted(completion)), result.expanded,
                 upper == lower)


def certify_pair(left, right, a, b, budget, fixed=(), excluded=(), epsilon=1e-8,
                 initial_region=None, nodes_per_call=10000, max_region=64):
    """Progressive four-bound certificate. No full-graph claim from an isolated subgraph."""
    intervention = aligned_intervention(left, right, fixed, excluded)
    if not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("Certificate epsilon must be finite and nonnegative")
    for graph in (left, right):
        if a == b or a not in graph.available(fixed, excluded) or b not in graph.available(fixed, excluded):
            return None, {"reason": "decisions_not_both_feasible"}
        if b not in graph.adj[a]:
            return None, {"reason": "decisions_not_competing_on_both_sides"}
    region = set(initial_region or (a, b)) | {a, b}
    if not region <= left.nodes.keys():
        raise ValueError("Unknown region node")
    history = []
    while len(region) <= max_region:
        bounds = {}
        for label, graph, action in (("left_a", left, a), ("left_b", left, b),
                                     ("right_a", right, a), ("right_b", right, b)):
            budget.reserve()
            start = time.perf_counter()
            result = local_bound(graph, region, action, fixed, excluded,
                                 min(nodes_per_call, budget.max_nodes - budget.nodes))
            budget.nodes += result.expanded
            budget.seconds += time.perf_counter() - start
            bounds[label] = asdict(result)
        history.append({"region": sorted(region), "bounds": bounds})
        la, lb, ra, rb = (bounds[k] for k in ("left_a", "left_b", "right_a", "right_b"))
        def strictly_better(x, y):
            return Fraction(x["lower"]) > Fraction(y["upper"]) + Fraction(epsilon)
        l_pref = a if strictly_better(la, lb) else b if strictly_better(lb, la) else None
        r_pref = a if strictly_better(ra, rb) else b if strictly_better(rb, ra) else None
        if l_pref and r_pref and l_pref != r_pref:
            witness = {"a": a, "b": b, "left_preferred": l_pref, "right_preferred": r_pref,
                       "left": left.to_dict(), "right": right.to_dict(),
                       "fixed": list(fixed), "excluded": list(excluded),
                       "intervention": intervention, "bounds": bounds, "region": sorted(region),
                       "epsilon": epsilon, "certificate_scope": "full_residual_graph_with_fixed_boundary",
                       "history": history}
            return witness, {"reason": "certified", "expansions": len(history)}
        if l_pref and r_pref and l_pref == r_pref:
            return None, {"reason": "certified_same_preference", "history": history}
        expanded = set(region)
        for v in region:
            expanded.update(left.adj[v] | right.adj[v])
        if expanded == region or len(expanded) > max_region:
            return None, {"reason": "unresolved_bounds", "history": history}
        region = expanded
    return None, {"reason": "region_budget"}
