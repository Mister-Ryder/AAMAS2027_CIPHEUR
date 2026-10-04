"""Compiled, incrementally maintained features for the frozen greedy kernel.

This module imports only the graph model and the reference feature runtime.
No certificate oracle, synthesis provider, or saved evidence is accessible.
Aggregate accumulators store exact sums of the floating-point terms consumed
by the reference ``math.fsum``. Rounding occurs once at the query boundary,
avoiding subtraction drift while preserving integer-to-float semantics.
"""
from __future__ import annotations

from fractions import Fraction
import heapq
import math
from time import perf_counter

from .graph_features import (
    FeatureRuleProgram, _BASE_EXPRESSIONS, _Expression, _FeatureState, _charge,
)
from .model import Graph


def _shape(expression: _Expression):
    return expression.op, tuple(_shape(arg) for arg in expression.args)


_ROOT_SHAPE = ("root", ())
_AVAILABLE_SHAPE = ("available", ())
_NEIGHBOR_SHAPE = ("neighbors", (_ROOT_SHAPE,))
_EDGE_SHAPE = ("induced_edges", (_NEIGHBOR_SHAPE,))
_LOWERED = {
    ("count", (_NEIGHBOR_SHAPE,)): "degree",
    ("sum_weights", (_NEIGHBOR_SHAPE,)): "conflict_weight",
    ("max_weight", (_NEIGHBOR_SHAPE,)): "max_conflict_weight",
    ("count", (_AVAILABLE_SHAPE,)): "remaining_count",
    ("sum_weights", (_AVAILABLE_SHAPE,)): "available_weight",
    ("count", (_EDGE_SHAPE,)): "neighbor_edge_count",
    ("edge_min_weight_sum", (_EDGE_SHAPE,)): "neighbor_edge_min",
    ("edge_weight_product_sum", (_EDGE_SHAPE,)): "neighbor_edge_product",
    _shape(_BASE_EXPRESSIONS["compatible_weight"]): "compatible_weight",
}

class _LazyScoreLocals(dict):
    """Validated numeric inputs materialize only when Python reads a name."""
    def __init__(self, getter):
        super().__init__({'min':min,'max':max,'abs':abs});self.getter=getter
    def __missing__(self,key):
        value=self.getter(key);self[key]=value;return value


def _float_term(value) -> Fraction:
    """Exactly represent the conversion that math.fsum applies to one term."""
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError("Feature terms must be finite")
    return Fraction(converted)


class _CompiledSnapshot(_FeatureState):
    def __init__(self, owner: "CompiledEvaluator"):
        super().__init__(owner.graph, owner.active, owner.meter)
        self.owner = owner

    def evaluate(self, expression: _Expression, root: str):
        owner = self.owner
        expression = owner.expressions.get(expression, expression)
        key = (expression, root if expression.depends_on_root else None)
        _charge(self.meter, "cache_lookup")
        if key in self.cache:
            return self.cache[key]
        lowered = owner.lowered.get(expression)
        if lowered is not None:
            _charge(self.meter, "maintained_query")
            if lowered == "degree":
                value = len(owner.neighbors[root])
            elif lowered == "conflict_weight":
                value = float(owner.neighbor_sums[root])
            elif lowered == "compatible_weight":
                value = float(owner.total_weight - owner.neighbor_sums[root]
                              - owner.weight_terms[root])
                _charge(self.meter, "exact_arithmetic", 2)
            elif lowered == "max_conflict_weight":
                heap = owner.neighbor_maxima[root]
                while heap and heap[0][1] not in owner.neighbors[root]:
                    heapq.heappop(heap)
                    _charge(self.meter, "heap_remove")
                value = -heap[0][0] if heap else 0.0
            elif lowered == "remaining_count":
                value = len(owner.active)
            elif lowered == "available_weight":
                value = float(owner.total_weight)
            elif lowered == "neighbor_edge_count":
                value = owner.edge_counts[root]
            elif lowered == "neighbor_edge_min":
                value = float(owner.edge_min_sums[root])
            else:
                value = float(owner.edge_product_sums[root])
            if not math.isfinite(value):
                raise ValueError("Feature values must be finite")
            if isinstance(value, float):
                _charge(self.meter, "exact_to_float")
            self.cache[key] = value
            return value
        if _shape(expression) == _NEIGHBOR_SHAPE:
            # Generic set operations still receive exactly the reference set.
            _charge(self.meter, "operation")
            _charge(self.meter, "set_materialize", len(owner.neighbors[root]))
            value = frozenset(owner.neighbors[root])
            self.cache[key] = value
            return value
        # The inherited implementation recursively calls this method, so its
        # children can still share DAG entries or use maintained quantities.
        _charge(self.meter, "fallback_dispatch")
        return super().evaluate(expression, root)


class CompiledEvaluator:
    """One graph/residual state with a shared typed DAG and deletion updates.

    ``feature_values`` and ``score`` query the current state. ``remove`` takes
    an iterable of IDs, applies deletions sequentially, and invalidates all
    residual-dependent cached expressions. The supplied meter, when present,
    receives initialization, update, and query work as well as elapsed times.
    """

    def __init__(self, graph: Graph, program: FeatureRuleProgram, active,
                 meter: dict | None = None, score_slice: bool = False):
        if not isinstance(program, FeatureRuleProgram):
            raise TypeError("A typed FeatureRuleProgram is required")
        self.graph, self.program = graph, program
        self.score_slice = score_slice
        self.required_names = set(program.code.co_names) & set(program.feature_names)
        self.active = set(active)
        if not self.active <= graph.nodes.keys():
            raise ValueError("Active set contains unknown nodes")
        self.meter = meter if meter is not None else {}
        for key in ("feature_work", "initialization_work", "update_work", "query_work",
                    "feature_seconds", "initialization_seconds", "update_seconds",
                    "scoring_seconds"):
            self.meter.setdefault(key, 0)
        self.meter.setdefault("feature_primitives", {})
        self._snapshot = None
        self._term_cache = {}
        started, before = perf_counter(), self.meter["feature_work"]
        self.expressions = {}
        original_count = 0

        def intern(expression):
            nonlocal original_count
            original_count += 1
            _charge(self.meter, "compile_node")
            args = tuple(intern(arg) for arg in expression.args)
            canonical = _Expression(expression.op, args, expression.value,
                                    expression.result_type, expression.depends_on_root)
            found = self.expressions.get(canonical)
            if found is None:
                self.expressions[canonical] = canonical
                found = canonical
            return found

        for name, expression in _BASE_EXPRESSIONS.items():
            if not score_slice or name in self.required_names:intern(expression)
        for name, expression in program._expressions:
            if not score_slice or name in self.required_names:intern(expression)
        self.lowered = {expression: _LOWERED[_shape(expression)]
                        for expression in self.expressions
                        if _shape(expression) in _LOWERED}
        requested = set(self.lowered.values())
        self._uses_sums = bool(requested & {'conflict_weight','compatible_weight','available_weight'}) or not score_slice
        self._uses_max = 'max_conflict_weight' in requested or not score_slice
        self._edge_kinds = requested & {
            "neighbor_edge_count", "neighbor_edge_min", "neighbor_edge_product"}
        self.metadata = {
            "backend": "shared_dag_incremental_v03",
            "score_slice": score_slice,
            "branch_sensitive_inputs": score_slice,
            "scorer_inputs": sorted(self.required_names),
            "tree_nodes": original_count,
            "dag_nodes": len(self.expressions),
            "shared_nodes_saved": original_count - len(self.expressions),
            "root_independent_nodes": sum(not expr.depends_on_root
                                          for expr in self.expressions),
            "lowered_aggregates": sorted(requested),
            "generic_snapshot_fallback": True,
            "numeric_semantics": "exact_sum_of_reference_float_terms_then_one_round",
            "work_scope": "compilation_initialization_queries_deletion_updates",
            "bit_complexity_measured": False,
        }
        try:
            self.weight_terms = {}
            self.neighbors = {}
            self.neighbor_sums = {}
            self.neighbor_maxima = {}
            self.total_weight = Fraction(0)
            self.edge_counts = {}
            self.edge_min_sums = {}
            self.edge_product_sums = {}
            if self._uses_sums:
                for v in sorted(self.active):
                    term = _float_term(graph.nodes[v].weight)
                    self.weight_terms[v] = term
                    self.total_weight += term
                    _charge(self.meter, "weight_read")
                    _charge(self.meter, "float_to_exact")
                    _charge(self.meter, "exact_arithmetic")
            for v in sorted(self.active):
                _charge(self.meter, "neighbor_membership", len(graph.adj[v]))
                neighbors = graph.adj[v] & self.active
                self.neighbors[v] = neighbors
                if self._uses_sums:
                    self.neighbor_sums[v] = sum((self.weight_terms[u] for u in neighbors), Fraction(0))
                    _charge(self.meter, "exact_arithmetic", len(neighbors))
                if self._uses_max:
                    self.neighbor_maxima[v] = [(-graph.nodes[u].weight, u) for u in neighbors]
                    heapq.heapify(self.neighbor_maxima[v])
                    _charge(self.meter, "weight_read", len(neighbors))
                    _charge(self.meter, "heap_initialize", len(neighbors))
                if self._edge_kinds:
                    self.edge_counts[v] = 0
                    self.edge_min_sums[v] = Fraction(0)
                    self.edge_product_sums[v] = Fraction(0)
                    ordered = sorted(neighbors)
                    for i, a in enumerate(ordered):
                        for b in ordered[i + 1:]:
                            _charge(self.meter, "edge_membership")
                            if b in graph.adj[a]:
                                self.edge_counts[v] += 1
                                _charge(self.meter, "integer_arithmetic")
                                if "neighbor_edge_min" in self._edge_kinds:
                                    self.edge_min_sums[v] += self._edge_term(a, b, "min")
                                    _charge(self.meter, "exact_arithmetic")
                                if "neighbor_edge_product" in self._edge_kinds:
                                    self.edge_product_sums[v] += self._edge_term(a, b, "product")
                                    _charge(self.meter, "exact_arithmetic")
        except (OverflowError, ArithmeticError) as error:
            raise ValueError("Feature arithmetic overflow") from error
        finally:
            self.meter["initialization_work"] += self.meter["feature_work"] - before
            elapsed = perf_counter() - started
            self.meter["initialization_seconds"] += elapsed
            self.meter["feature_seconds"] += elapsed
        self.metadata["initial_active_nodes"] = len(self.active)

    def _edge_term(self, a: str, b: str, kind: str) -> Fraction:
        key = (*sorted((a, b)), kind)
        _charge(self.meter, "edge_term_cache_lookup")
        if key not in self._term_cache:
            wa, wb = self.graph.nodes[a].weight, self.graph.nodes[b].weight
            value = min(wa, wb) if kind == "min" else wa * wb
            self._term_cache[key] = _float_term(value)
            _charge(self.meter, "weight_read", 2)
            _charge(self.meter, "arithmetic")
            _charge(self.meter, "float_to_exact")
        return self._term_cache[key]

    def feature_values(self, node: str) -> dict:
        if node not in self.active:
            raise ValueError("Scored node must belong to the current active set")
        before = self.meter["feature_work"]
        started = perf_counter()
        try:
            if self._snapshot is None:
                _charge(self.meter, "snapshot_materialize", len(self.active))
                self._snapshot = _CompiledSnapshot(self)
            if not self.score_slice:return self._snapshot.feature_values(self.program, node)
            values={name:self._snapshot.evaluate(expr,node) for name,expr in _BASE_EXPRESSIONS.items() if name in self.required_names}
            for name,expr in self.program._expressions:
                if name in self.required_names:values[name]=self._snapshot.evaluate(expr,node)
            if 'station_gap' in self.required_names:
                values['station_gap']=self.graph.constraints.get('station_gap',self.graph.constraints.get('ground_trans_time',0));_charge(self.meter,'constraint_read',2)
            if 'satellite_gap' in self.required_names:
                values['satellite_gap']=self.graph.constraints.get('satellite_gap',self.graph.constraints.get('satellite_change_time',0));_charge(self.meter,'constraint_read',2)
            return values
        finally:
            self.meter["query_work"] += self.meter["feature_work"] - before
            if self.score_slice:self.meter['feature_seconds'] += perf_counter()-started

    def score(self, node: str) -> float:
        if self.score_slice:
            if node not in self.active:raise ValueError('Scored node must be active')
            if self._snapshot is None:
                before=self.meter['feature_work']
                _charge(self.meter,'snapshot_materialize',len(self.active));self._snapshot=_CompiledSnapshot(self)
                self.meter['query_work']+=self.meter['feature_work']-before
            expressions={**_BASE_EXPRESSIONS,**dict(self.program._expressions)}
            feature_elapsed=[0.0]
            def getter(name):
                before=self.meter['feature_work'];started=perf_counter()
                try:
                    _charge(self.meter,'scorer_input_lookup')
                    if name in expressions:return self._snapshot.evaluate(expressions[name],node)
                    if name=='station_gap':
                        _charge(self.meter,'constraint_read',2)
                        return self.graph.constraints.get('station_gap',self.graph.constraints.get('ground_trans_time',0))
                    if name=='satellite_gap':
                        _charge(self.meter,'constraint_read',2)
                        return self.graph.constraints.get('satellite_gap',self.graph.constraints.get('satellite_change_time',0))
                    raise ValueError('Unexpected scorer input '+name)
                finally:
                    self.meter['query_work']+=self.meter['feature_work']-before
                    elapsed=perf_counter()-started
                    self.meter['feature_seconds']+=elapsed;feature_elapsed[0]+=elapsed
            started=perf_counter()
            try:result=float(eval(self.program.code,{'__builtins__':{}},_LazyScoreLocals(getter)))
            except (ZeroDivisionError,TypeError,ValueError,OverflowError) as error:
                raise ValueError(f'Invalid program score: {error}') from error
            finally:self.meter['scoring_seconds']+=max(0.0,perf_counter()-started-feature_elapsed[0])
            if not math.isfinite(result) or abs(result)>1e15:raise ValueError('Program score must be finite and bounded')
            return result
        return self.program._rank(self.feature_values(node), self.meter)

    def remove(self, nodes) -> None:
        """Delete once per vertex; overlapping batch deletions never double count."""
        removing = set(nodes)
        if not removing <= self.graph.nodes.keys():
            raise ValueError("Deletion contains unknown nodes")
        started, before = perf_counter(), self.meter["feature_work"]
        try:
            for x in sorted(removing):
                _charge(self.meter, "active_membership")
                if x not in self.active:
                    continue
                neighbors_x = self.neighbors[x]
                for v in sorted(neighbors_x):
                    _charge(self.meter, "neighbor_update")
                    if self._edge_kinds:
                        # Membership scans of the smaller set implement the
                        # actual intersection work charged here.
                        small, large = sorted((self.neighbors[v], neighbors_x), key=len)
                        _charge(self.meter, "intersection_scan", len(small))
                        common = [y for y in small if y in large]
                        for y in common:
                            self.edge_counts[v] -= 1
                            _charge(self.meter, "integer_arithmetic")
                            if "neighbor_edge_min" in self._edge_kinds:
                                self.edge_min_sums[v] -= self._edge_term(x, y, "min")
                                _charge(self.meter, "exact_arithmetic")
                            if "neighbor_edge_product" in self._edge_kinds:
                                self.edge_product_sums[v] -= self._edge_term(x, y, "product")
                                _charge(self.meter, "exact_arithmetic")
                    self.neighbors[v].remove(x)
                    if self._uses_sums:self.neighbor_sums[v] -= self.weight_terms[x]
                    _charge(self.meter, "set_delete")
                    if self._uses_sums:_charge(self.meter, "exact_arithmetic")
                self.active.remove(x)
                if self._uses_sums:self.total_weight -= self.weight_terms[x]
                _charge(self.meter, "set_delete")
                if self._uses_sums:_charge(self.meter, "exact_arithmetic")
                self._snapshot = None
        finally:
            self.meter["update_work"] += self.meter["feature_work"] - before
            elapsed = perf_counter() - started
            self.meter["update_seconds"] += elapsed
            self.meter["feature_seconds"] += elapsed


def schedule_compiled(graph: Graph, program: FeatureRuleProgram,
                      fixed=(), excluded=(), meter=None, score_slice=False) -> dict:
    """Apply the unchanged deterministic kernel using compiled graph features."""
    fixed, excluded = tuple(fixed), tuple(excluded)
    chosen = list(fixed)
    evaluator = CompiledEvaluator(graph, program, graph.available(fixed, excluded),meter,score_slice)
    trace = []
    while evaluator.active:
        scores = {node: evaluator.score(node) for node in sorted(evaluator.active)}
        node = min(evaluator.active, key=lambda item: (-scores[item], item))
        trace.append({"selected": node, "score": scores[node],
                      "remaining_count": len(evaluator.active)})
        chosen.append(node)
        evaluator.remove({node} | graph.adj[node])
    if not graph.feasible(chosen):
        raise AssertionError("Kernel feasibility invariant violated")
    return {"selected": sorted(chosen), "value": graph.value(chosen), "feasible": True,
            "trace": trace, **evaluator.meter, "compilation": evaluator.metadata}
