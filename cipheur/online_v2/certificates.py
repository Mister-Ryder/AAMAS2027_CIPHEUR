"""Small-patch conditional certificates and an exact evidence archive.

Only the supplied ``active`` induced graph is optimized.  An external fixed
schedule must already be compatible with it; excluded vertices cannot be added.
Thus these are conditional patch bounds, never whole-instance oracle values.
All objective arithmetic is integer ticks.  ``deadline`` is an absolute
``time.process_time()`` CPU timestamp.  Interrupted bounds remain sound.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from copy import deepcopy
from fractions import Fraction
import math
from numbers import Integral
import time
from typing import Mapping


MAX_PATCH_NODES = 64
ARCHIVE_SCOPE = "consistency_of_one_pointwise_rule_over_retained_contexts"


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    return int(value)


def _expired(deadline):
    return deadline is not None and time.process_time() >= deadline


def _greedy_lower(root, residual, adjacency, weights, deadline, work, ratio):
    selected = [root]
    remaining = set(residual)
    while remaining and not _expired(deadline):
        best, best_degree = None, None
        for node in sorted(remaining):
            degree = 0
            for other in adjacency[node]:
                work["greedy_adjacency_probes"] += 1
                degree += other in remaining
            if best is None:
                best, best_degree = node, degree
            elif ratio:
                lhs = weights[node] * (best_degree + 1)
                rhs = weights[best] * (degree + 1)
                if lhs > rhs or (lhs == rhs and
                        (weights[node], -degree, -node) >
                        (weights[best], -best_degree, -best)):
                    best, best_degree = node, degree
            elif (weights[node], -degree, -node) > (
                    weights[best], -best_degree, -best):
                best, best_degree = node, degree
            if _expired(deadline):
                return selected
        selected.append(best)
        remaining.difference_update(adjacency[best])
        remaining.discard(best)
    return selected


def _clique_partition(residual, adjacency, weights, deadline, work):
    # Every completed class is a clique.  Unprocessed vertices become singleton
    # classes on interruption, so no upper-bound assumption depends on timeout.
    order = sorted(residual, key=lambda v: (
        -len(adjacency[v] & residual), -weights[v], v))
    cliques = []
    for position, node in enumerate(order):
        if _expired(deadline):
            cliques.extend([[v] for v in order[position:]])
            break
        assigned = False
        for clique in cliques:
            compatible = True
            for other in clique:
                work["clique_adjacency_probes"] += 1
                if other not in adjacency[node]:
                    compatible = False
                    break
                if _expired(deadline):
                    cliques.append([node])
                    cliques.extend([[v] for v in order[position + 1:]])
                    return cliques
            if compatible:
                clique.append(node)
                assigned = True
                break
        if not assigned:
            cliques.append([node])
    return cliques


def local_certificates(adjacency: dict[int, set[int]], weights: dict[int, int],
                       active: set[int], roots: list[int], *, deadline=None):
    """Return sound LB/UB rows and pairwise conditional preference intervals.

    For mandatory root ``v``, the target is
    ``weight[v] + MWIS(active - closed_neighborhood(v))``.  Two feasible greedy
    completions supply lower bounds; a weighted clique partition supplies the
    upper bound.  No exact/full solver is called.  ``lower_solution`` is a real
    feasible patch completion which the caller may independently commit.

    Edges outside ``active`` are ignored.  The active graph must be undirected,
    loop-free, at most 64 vertices, with nonnegative integer-tick weights.
    Time already spent validating this bounded patch is charged in CPU usage.
    """
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    if deadline is not None and not math.isfinite(deadline):
        raise ValueError("deadline must be a finite absolute CPU timestamp")
    if len(active) > MAX_PATCH_NODES:
        raise ValueError(f"active patch exceeds {MAX_PATCH_NODES} vertices")
    nodes = sorted(_integer(v, "active vertex") for v in active)
    root_ids = [_integer(v, "root") for v in roots]
    if len(set(root_ids)) != len(root_ids):
        raise ValueError("roots must be distinct")
    if not set(root_ids) <= set(nodes):
        raise ValueError("each root must belong to active")
    local_weights, local_adj = {}, {}
    work = {"input_adjacency_probes": 0, "greedy_adjacency_probes": 0,
            "clique_adjacency_probes": 0, "pair_comparisons": 0}
    for v in nodes:
        if v not in adjacency or v not in weights:
            raise ValueError(f"missing adjacency or weight for active vertex {v}")
        local_weights[v] = _integer(weights[v], "weight")
        if local_weights[v] < 0:
            raise ValueError("contact weights must be nonnegative integer ticks")
        if v in adjacency[v]:
            raise ValueError("active graph contains a self-loop")
        local_adj[v] = set()
        for u in nodes:
            if u != v:
                work["input_adjacency_probes"] += 1
                if u in adjacency[v]:
                    local_adj[v].add(u)
    for v in nodes:
        for u in local_adj[v]:
            if v not in local_adj[u]:
                raise ValueError("active graph must be undirected")

    rows = []
    for root in root_ids:
        root_start = time.process_time()
        residual = set(nodes) - local_adj[root] - {root}
        best = [root]
        for use_ratio in (True, False):
            if _expired(deadline):
                break
            trial = _greedy_lower(root, residual, local_adj, local_weights,
                                  deadline, work, use_ratio)
            trial_value = sum(local_weights[v] for v in trial)
            best_value = sum(local_weights[v] for v in best)
            if trial_value > best_value or (trial_value == best_value and
                                           sorted(trial) < sorted(best)):
                best = trial
        cover = _clique_partition(residual, local_adj, local_weights,
                                  deadline, work)
        maxima = [max(local_weights[v] for v in clique) for clique in cover]
        lower = sum(local_weights[v] for v in best)
        upper = local_weights[root] + sum(maxima)
        if lower > upper:
            raise AssertionError("inconsistent independently sound bounds")
        rows.append({"root": root, "lower_ticks": lower,
                     "upper_ticks": upper, "lower_solution": sorted(best),
                     "upper_cliques": [sorted(k) for k in cover],
                     "upper_clique_maxima_ticks": maxima,
                     "mandatory_root_weight_ticks": local_weights[root],
                     "residual_count": len(residual),
                     "exact": lower == upper,
                     "deadline_reached": _expired(deadline),
                     "cpu_seconds": time.process_time() - root_start})
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            work["pair_comparisons"] += 1
            low = a["lower_ticks"] - b["upper_ticks"]
            high = a["upper_ticks"] - b["lower_ticks"]
            preferred = a["root"] if low > 0 else b["root"] if high < 0 else None
            preference = ("a" if low > 0 else "b" if high < 0 else
                          "tie" if low == high == 0 else "unknown")
            pairs.append({"a": a["root"], "b": b["root"],
                          "delta_lower_ticks": low, "delta_upper_ticks": high,
                          "preference": preference, "preferred_root": preferred,
                          "competing": b["root"] in local_adj[a["root"]],
                          "a_certificate": deepcopy(a),
                          "b_certificate": deepcopy(b)})
    return {"version": "conditional_patch_intticks_clique_v1",
            "scope": "conditional_active_patch",
            "global_optimality_claim": False,
            "full_oracle_calls": 0, "active_nodes": nodes, "roots": rows,
            "pairs": pairs, "operation_counts": work,
            "deadline_clock": "time.process_time",
            "deadline_reached": _expired(deadline),
            "cpu_seconds": time.process_time() - cpu_start,
            "wall_seconds": time.perf_counter() - wall_start}


def _exact_vector(vector):
    if not isinstance(vector, tuple):
        raise TypeError("feature vector must be an exact tuple")
    key = []
    for value in vector:
        if isinstance(value, bool):
            raise TypeError("boolean is not a numeric graph feature")
        if isinstance(value, Integral):
            pair = (int(value), 1)
        elif isinstance(value, Fraction):
            pair = (value.numerator, value.denominator)
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("nonfinite feature value")
            pair = value.as_integer_ratio()
        else:
            raise TypeError("features must be integers, Fractions or finite floats")
        key.append(pair)
    return tuple(key)


def _components(outgoing, incoming):
    # Iterative Kosaraju avoids recursion limits in an explicitly bounded archive.
    seen, order = set(), []
    for root in outgoing:
        if root in seen:
            continue
        stack = [(root, False)]
        while stack:
            node, done = stack.pop()
            if done:
                order.append(node)
                continue
            if node in seen:
                continue
            seen.add(node)
            stack.append((node, True))
            stack.extend((child, False) for child in sorted(outgoing[node], reverse=True)
                         if child not in seen)
    seen, result = set(), []
    for root in reversed(order):
        if root in seen:
            continue
        stack, component = [root], []
        seen.add(root)
        while stack:
            node = stack.pop()
            component.append(node)
            for child in incoming[node]:
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        result.append(sorted(component))
    return result


def _one_cycle(component, outgoing):
    start, allowed = min(component), set(component)
    if start in outgoing[start]:
        return [start, start]
    first = min(outgoing[start] & allowed)
    queue, predecessor = deque([first]), {first: None}
    while queue:
        node = queue.popleft()
        if node == start:
            path = []
            while node is not None:
                path.append(node)
                node = predecessor[node]
            return [start] + list(reversed(path))
        for child in sorted(outgoing[node] & allowed):
            if child not in predecessor:
                predecessor[child] = node
                queue.append(child)
    raise AssertionError("strongly connected component has no return path")


class EvidenceArchive:
    """Exact relational quotient of retained, explicitly bounded contexts.

    A cycle rules out one pointwise score consistent with every retained strict
    relation.  It does not rule out a policy with changing parameters/history.
    Features use exact numeric equality: a float is its exact binary rational,
    not a decimal rendering, epsilon match, bucket, contact ID or config label.
    The caller is responsible for supplying sound conditional certificate rows.
    Graph-difference witnesses, if supplied in a row, are preserved; graph
    differences cannot be inferred from feature vectors alone.
    """

    def __init__(self, *, max_contexts=128, max_strict_rows=4096):
        self.max_contexts = _integer(max_contexts, "max_contexts")
        self.max_strict_rows = _integer(max_strict_rows, "max_strict_rows")
        if self.max_contexts < 1 or self.max_strict_rows < 1:
            raise ValueError("archive limits must be positive")
        self._contexts = OrderedDict()
        self._revision = 0
        self._feature_dimension = None

    def add(self, context_id, feature_vectors: Mapping[int, tuple],
            certificate_rows):
        """Add/replace a context; return exact cycles and their decision witnesses.

        Rows have ``a``, ``b``, ``delta_lower_ticks``, ``delta_upper_ticks`` as
        returned by ``local_certificates()[\"pairs\"]``.  Only strict intervals
        produce graph arcs.  Unknown/tie rows never become preference labels.
        """
        if not isinstance(context_id, str) or not context_id:
            raise ValueError("context_id must be a nonempty string")
        vectors = {_integer(root, "feature root"): _exact_vector(vector)
                   for root, vector in feature_vectors.items()}
        dimensions = {len(vector) for vector in vectors.values()}
        if len(dimensions) > 1:
            raise ValueError("one representation needs a fixed feature dimension")
        dimension = next(iter(dimensions), self._feature_dimension)
        if (self._feature_dimension is not None and dimension is not None and
                dimension != self._feature_dimension):
            raise ValueError("representation changed: rebuild the archive with all "
                             "retained contexts under the new representation")
        strict, unknown, ties, provided = [], 0, 0, 0
        for raw in certificate_rows:
            row = deepcopy(raw)
            a, b = _integer(row["a"], "pair a"), _integer(row["b"], "pair b")
            if a == b or a not in vectors or b not in vectors:
                raise ValueError("pair needs two distinct roots with feature vectors")
            low = _integer(row["delta_lower_ticks"], "delta lower")
            high = _integer(row["delta_upper_ticks"], "delta upper")
            if low > high:
                raise ValueError("reversed certificate interval")
            preferred = a if low > 0 else b if high < 0 else None
            label = ("a" if low > 0 else "b" if high < 0 else
                     "tie" if low == high == 0 else "unknown")
            if "preferred_root" in row and row["preferred_root"] != preferred:
                raise ValueError("preferred_root disagrees with certified interval")
            if "preference" in row and row["preference"] != label:
                raise ValueError("preference disagrees with certified interval")
            provided += 1
            if preferred is not None:
                strict.append({"preferred_root": preferred,
                               "other_root": b if preferred == a else a,
                               "certificate": row})
            elif label == "tie":
                ties += 1
            else:
                unknown += 1
        if len(strict) > self.max_strict_rows:
            raise ValueError("one context exceeds strict-row archive limit")
        replaced = context_id in self._contexts
        self._contexts.pop(context_id, None)
        self._contexts[context_id] = {"vectors": vectors, "strict": strict,
                                     "provided": provided, "unknown": unknown,
                                     "ties": ties}
        self._feature_dimension = dimension
        evicted = []
        while (len(self._contexts) > self.max_contexts or
               sum(len(c["strict"]) for c in self._contexts.values()) >
               self.max_strict_rows):
            evicted.append(self._contexts.popitem(last=False)[0])
        self._revision += 1
        result = self.summary()
        result.update({"added_context": context_id, "replaced_context": replaced,
                       "evicted_contexts": evicted})
        return result

    def summary(self):
        node_ids, occurrence, edges = {}, {}, {}
        for context_id, context in self._contexts.items():
            for root, vector in sorted(context["vectors"].items()):
                node = node_ids.setdefault(vector, len(node_ids))
                occurrence.setdefault(node, []).append({"context_id": context_id,
                                                         "root": root})
            for relation in context["strict"]:
                a, b = relation["preferred_root"], relation["other_root"]
                edge = (node_ids[context["vectors"][a]],
                        node_ids[context["vectors"][b]])
                edges.setdefault(edge, []).append({"context_id": context_id,
                    "preferred_root": a, "other_root": b,
                    "certificate": deepcopy(relation["certificate"])})
        outgoing = {node: set() for node in node_ids.values()}
        incoming = {node: set() for node in node_ids.values()}
        for a, b in edges:
            outgoing[a].add(b)
            incoming[b].add(a)
        vectors = {node: vector for vector, node in node_ids.items()}
        cycles = []
        for component in _components(outgoing, incoming):
            if len(component) == 1 and component[0] not in outgoing[component[0]]:
                continue
            path = _one_cycle(component, outgoing)
            cycle_edges = [{"preferred_quotient_node": a,
                            "other_quotient_node": b,
                            "occurrences": deepcopy(edges[(a, b)])}
                           for a, b in zip(path, path[1:])]
            cycles.append({"type": "exact_representation_cycle",
                           "scope": ARCHIVE_SCOPE,
                           "scc_nodes": component, "cycle_path": path,
                           "nodes": [{"quotient_node": node,
                                      "exact_vector_ratios": [list(v) for v in vectors[node]],
                                      "occurrences": deepcopy(occurrence[node])}
                                     for node in sorted(set(path))],
                           "edges": cycle_edges})
        cycles.sort(key=lambda cycle: cycle["scc_nodes"])
        return {"version": "exact_numeric_archive_quotient_v1",
                "archive_revision": self._revision,
                "only_archive_consistency": True, "scope": ARCHIVE_SCOPE,
                "arbitrary_dynamic_policy_impossibility_claim": False,
                "approximate_matches": 0,
                "feature_dimension": self._feature_dimension,
                "retained_context_ids": list(self._contexts),
                "context_count": len(self._contexts),
                "quotient_node_count": len(node_ids),
                "strict_row_count": sum(len(c["strict"]) for c in self._contexts.values()),
                "quotient_edge_count": len(edges),
                "unknown_row_count": sum(c["unknown"] for c in self._contexts.values()),
                "tie_row_count": sum(c["ties"] for c in self._contexts.values()),
                "self_loop_count": sum(a == b for a, b in edges),
                "cyclic_scc_count": len(cycles),
                "has_cycle": bool(cycles), "cycles": cycles,
                "structural_witness": deepcopy(cycles[0]) if cycles else None}
