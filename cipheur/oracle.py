"""Sound budgeted MWIS envelopes and full-residual conditional certificates."""
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
    lower_exact: str = ""
    upper_exact: str = ""
    upper_method: str = "weighted_clique_cover"
    clique_cover: tuple[tuple[str, ...], ...] = ()
    feasibility_checked: bool = True


class Budget:
    def __init__(self, max_calls=100, max_nodes=100000):
        if any(type(v) is not int or v < 0 for v in (max_calls, max_nodes)):
            raise ValueError("Oracle budgets must be nonnegative integers")
        self.max_calls, self.max_nodes = max_calls, max_nodes
        self.calls = self.nodes = 0
        self.seconds = 0.0

    def reserve(self):
        if self.calls >= self.max_calls or self.nodes >= self.max_nodes:
            raise RuntimeError("Oracle budget exhausted")
        self.calls += 1

    def to_dict(self):
        return {"calls": self.calls, "expanded_nodes": self.nodes,
                "elapsed_seconds": self.seconds, "max_calls": self.max_calls, "max_nodes": self.max_nodes}


def exact_value(graph, ids):
    return sum((Fraction(graph.nodes[v].weight) for v in ids), Fraction(0))


def outward(value, direction):
    rounded = float(value)
    if direction < 0 and Fraction(rounded) > value:
        return math.nextafter(rounded, -math.inf)
    if direction > 0 and Fraction(rounded) < value:
        return math.nextafter(rounded, math.inf)
    return rounded


def greedy_clique_cover(graph: Graph, candidates) -> tuple[tuple[str, ...], ...]:
    """Deterministic disjoint clique partition; no maximum-clique claim."""
    remaining = set(candidates)
    if not remaining <= graph.nodes.keys():
        raise ValueError("Clique cover contains unknown candidates")
    order = sorted(remaining, key=lambda v: (-len(graph.adj[v] & remaining), -graph.nodes[v].weight, v))
    cliques = []
    for seed in order:
        if seed not in remaining:
            continue
        clique = [seed]
        remaining.remove(seed)
        for node in order:
            if node in remaining and all(node in graph.adj[v] for v in clique):
                clique.append(node)
                remaining.remove(node)
        cliques.append(tuple(sorted(clique)))
    return tuple(cliques)


def clique_cover_upper(graph: Graph, candidates, cliques=None) -> Fraction:
    """Verify coverage, disjointness and every clique edge before summing maxima."""
    candidates = set(candidates)
    if not candidates <= graph.nodes.keys():
        raise ValueError("Unknown clique-cover candidate")
    cliques = greedy_clique_cover(graph, candidates) if cliques is None else cliques
    seen, upper = set(), Fraction(0)
    for raw in cliques:
        clique = tuple(raw)
        if not clique or len(set(clique)) != len(clique) or seen & set(clique):
            raise ValueError("Clique partition must be nonempty and disjoint")
        if not set(clique) <= candidates:
            raise ValueError("Clique partition contains extraneous contacts")
        if any(b not in graph.adj[a] for i, a in enumerate(clique) for b in clique[i + 1:]):
            raise ValueError("Partition member is not a clique")
        seen.update(clique)
        upper += max(Fraction(graph.nodes[v].weight) for v in clique)
    if seen != candidates:
        raise ValueError("Clique partition does not cover all candidates")
    return upper


def _envelope(graph, remaining, method):
    if method == "weighted_clique_cover":
        return clique_cover_upper(graph, remaining)
    if method == "weight_sum":
        return exact_value(graph, remaining)
    raise ValueError("Unknown MWIS envelope method")


def _greedy_completion(graph, fixed, candidates):
    selected = list(fixed)
    for v in sorted(candidates, key=lambda k: (-graph.nodes[k].weight, k)):
        if not graph.adj[v].intersection(selected):
            selected.append(v)
    if not graph.feasible(selected):
        raise AssertionError("Lower-bound schedule is infeasible")
    return tuple(sorted(selected))


def _bound(graph, lower, upper, selected, expanded, method, cover=()):
    if not graph.feasible(selected) or exact_value(graph, selected) != lower or lower > upper:
        raise AssertionError("Invalid certified interval or feasibility witness")
    return Bound(outward(lower, -1), outward(upper, 1), tuple(sorted(selected)), expanded,
                 upper == lower, str(lower), str(upper), method, tuple(cover), True)


def solve(graph: Graph, candidates=None, fixed=(), excluded=(), max_nodes=10000,
          upper_method="weighted_clique_cover") -> Bound:
    """Budgeted B&B with a verified weighted clique envelope at every frontier."""
    if type(max_nodes) is not int or max_nodes < 0:
        raise ValueError("Node budget must be a nonnegative integer")
    fixed, excluded = tuple(sorted(fixed)), tuple(excluded)
    available = graph.available(fixed, excluded)
    if candidates is not None:
        candidates = set(candidates)
        if not candidates <= graph.nodes.keys():
            raise ValueError("Unknown candidate")
    active = available if candidates is None else available & candidates
    weights = {v: Fraction(graph.nodes[v].weight) for v in graph.nodes}
    base = exact_value(graph, fixed)
    chosen = _greedy_completion(graph, fixed, active)
    best, expanded = exact_value(graph, chosen), 0
    envelope_cache = {}
    def envelope(remaining):
        if remaining not in envelope_cache:
            envelope_cache[remaining] = _envelope(graph, remaining, upper_method)
        return envelope_cache[remaining]
    frontier = [(frozenset(active), fixed, base)]
    while frontier and expanded < max_nodes:
        remaining, selected, value = frontier.pop()
        expanded += 1
        if value > best:
            best, chosen = value, selected
        if value + envelope(remaining) <= best:
            continue
        v = min(remaining, key=lambda k: (-len(graph.adj[k] & remaining), -graph.nodes[k].weight, k))
        rest = remaining - {v}
        frontier.append((rest, selected, value))
        frontier.append((rest - graph.adj[v], selected + (v,), value + weights[v]))
    upper = max([best] + [value + envelope(remaining) for remaining, _, value in frontier])
    cover = greedy_clique_cover(graph, active) if upper_method == "weighted_clique_cover" else ()
    return _bound(graph, best, upper, chosen, expanded, upper_method, cover)


def local_bound(graph, region, action, fixed=(), excluded=(), max_nodes=10000,
                upper_method="weighted_clique_cover"):
    """Complete the interior witness globally; relax interior/outside edges for U."""
    fixed, excluded = tuple(fixed), tuple(excluded)
    if action not in graph.available(fixed, excluded):
        raise ValueError("Forced action is not feasible at the boundary")
    region = set(region)
    if not region <= graph.nodes.keys():
        raise ValueError("Unknown region contact")
    boundary = fixed + (action,)
    available = graph.available(boundary, excluded)
    interior, outside = available & region, available - region
    result = solve(graph, interior, boundary, excluded, max_nodes, upper_method)
    completion = _greedy_completion(graph, result.selected, outside)
    lower = exact_value(graph, completion)
    cover = greedy_clique_cover(graph, outside) if upper_method == "weighted_clique_cover" else ()
    upper = Fraction(result.upper_exact) + _envelope(graph, outside, upper_method)
    return _bound(graph, lower, upper, completion, result.expanded, upper_method, cover)


def _intersect_bounds(previous, current):
    """Different regions solve the same full conditional space; intersect safely."""
    if previous is None:
        return current
    lower_source = current if Fraction(current["lower_exact"]) > Fraction(previous["lower_exact"]) else previous
    upper_source = current if Fraction(current["upper_exact"]) < Fraction(previous["upper_exact"]) else previous
    lower, upper = Fraction(lower_source["lower_exact"]), Fraction(upper_source["upper_exact"])
    if lower > upper:
        raise AssertionError("Repeated sound intervals cannot have empty intersection")
    merged = dict(lower_source)
    merged.update(lower=outward(lower, -1), upper=outward(upper, 1), lower_exact=str(lower),
                  upper_exact=str(upper), exact=lower == upper,
                  expanded=previous["expanded"] + current["expanded"],
                  upper_method=upper_source["upper_method"], clique_cover=upper_source["clique_cover"])
    return merged


def certify_pair(left, right, a, b, budget, fixed=(), excluded=(), epsilon=1e-8,
                 initial_region=None, nodes_per_call=10000, max_region=64,
                 include_preservation=False, upper_method="weighted_clique_cover",
                 raise_on_exhaustion=True):
    """Progressive four-space certificates with optional structured exhaustion.

    Legacy exhaustion exceptions carry the same ``details`` as the nonthrowing
    acquisition path, preserving all partially computed intervals.
    """
    fixed, excluded = tuple(fixed), tuple(excluded)
    intervention = aligned_intervention(left, right, fixed, excluded)
    if not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("Certificate epsilon must be finite and nonnegative")
    if type(nodes_per_call) is not int or nodes_per_call < 0 or type(max_region) is not int or max_region < 0:
        raise ValueError("Certificate limits must be nonnegative integers")
    for graph in (left, right):
        active = graph.available(fixed, excluded)
        if a == b or a not in active or b not in active:
            return None, {"reason": "decisions_not_both_feasible"}
        if b not in graph.adj[a]:
            return None, {"reason": "decisions_not_competing_on_both_sides"}
    region = set((a, b) if initial_region is None else initial_region) | {a, b}
    if not region <= left.nodes.keys():
        raise ValueError("Unknown region node")
    history, accumulated = [], {}
    before, started = budget.to_dict(), time.perf_counter()
    def detail(reason, **extra):
        return {"reason": reason, "history": history, "bounds": accumulated,
                "expansions": len(history), "before": before, "after": budget.to_dict(),
                "elapsed_seconds": time.perf_counter() - started, **extra}
    while len(region) <= max_region:
        raw = {}
        row = {"region": sorted(region), "raw_bounds": raw, "bounds": {}, "complete": False}
        history.append(row)
        for label, graph, action in (("left_a", left, a), ("left_b", left, b),
                                     ("right_a", right, a), ("right_b", right, b)):
            try:
                budget.reserve()
            except RuntimeError as error:
                row["uncomputed"] = [k for k in ("left_a", "left_b", "right_a", "right_b") if k not in raw]
                row["bounds"] = dict(accumulated)
                details = detail("budget_exhausted", unknown_reason="exhausted_computation")
                if raise_on_exhaustion:
                    error.details = details
                    raise
                return None, details
            start = time.perf_counter()
            result = local_bound(graph, region, action, fixed, excluded,
                                 min(nodes_per_call, budget.max_nodes - budget.nodes), upper_method)
            budget.nodes += result.expanded
            budget.seconds += time.perf_counter() - start
            raw[label] = asdict(result)
            accumulated[label] = _intersect_bounds(accumulated.get(label), raw[label])
        row["bounds"], row["complete"] = dict(accumulated), True
        la, lb, ra, rb = (accumulated[k] for k in ("left_a", "left_b", "right_a", "right_b"))
        def strictly_better(x, y):
            return Fraction(x["lower_exact"]) > Fraction(y["upper_exact"]) + Fraction(epsilon)
        l_pref = a if strictly_better(la, lb) else b if strictly_better(lb, la) else None
        r_pref = a if strictly_better(ra, rb) else b if strictly_better(rb, ra) else None
        if l_pref and r_pref and (l_pref != r_pref or include_preservation):
            witness = {"a": a, "b": b, "left_preferred": l_pref, "right_preferred": r_pref,
                       "left": left.to_dict(), "right": right.to_dict(),
                       "fixed": list(fixed), "excluded": list(excluded),
                       "intervention": intervention, "bounds": dict(accumulated), "region": sorted(region),
                       "epsilon": epsilon, "certificate_scope": "full_residual_graph_with_fixed_boundary",
                       "relation": "reversal" if l_pref != r_pref else "preservation", "history": history}
            return witness, detail("certified")
        if l_pref and r_pref:
            return None, detail("certified_same_preference")
        ties = [side for side, x, y in (("left", la, lb), ("right", ra, rb))
                if x["exact"] and y["exact"] and x["lower_exact"] == y["lower_exact"]]
        if ties:
            return None, detail("unresolved_bounds", unknown_reason="equal_conditional_optima", tied_sides=ties)
        expanded = set(region)
        for v in region:
            expanded.update(left.adj[v] | right.adj[v])
        if expanded == region or len(expanded) > max_region:
            return None, detail("unresolved_bounds", unknown_reason="region_limit" if len(expanded) > max_region
                               else "unresolved_intervals")
        region = expanded
    return None, detail("region_budget", unknown_reason="region_limit")
