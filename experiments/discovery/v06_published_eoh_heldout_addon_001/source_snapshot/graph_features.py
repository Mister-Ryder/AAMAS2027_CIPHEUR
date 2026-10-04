"""Typed graph features and a frozen feature--ranking program.

Only deterministic graph traversals are evaluated here.  In particular, this
module has no dependency on the offline certificate oracle or any LLM provider.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import keyword
import math
import re
from time import perf_counter
from typing import Any

from .model import Graph
from .programs import FEATURES


MAX_FEATURES = 6
MAX_EXPRESSION_NODES = 48
MAX_EXPRESSION_DEPTH = 8
_FUNCTIONS = ("min", "max", "abs")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# A union argument type means either collection type, never an untyped value.
GRAPH_OPERATION_TYPES = {
    "root": ((), "Node"),
    "available": ((), "NodeSet"),
    "neighbors": (("Node",), "NodeSet"),
    "singleton": (("Node",), "NodeSet"),
    "union": (("NodeSet", "NodeSet"), "NodeSet"),
    "intersection": (("NodeSet", "NodeSet"), "NodeSet"),
    "difference": (("NodeSet", "NodeSet"), "NodeSet"),
    "induced_edges": (("NodeSet",), "EdgeSet"),
    "count": (("NodeSet|EdgeSet",), "Number"),
    "sum_weights": (("NodeSet",), "Number"),
    "max_weight": (("NodeSet",), "Number"),
    "clique_cover_weight": (("NodeSet",), "Number"),
    "greedy_independent_weight": (("NodeSet",), "Number"),
    "edge_min_weight_sum": (("EdgeSet",), "Number"),
    "edge_weight_product_sum": (("EdgeSet",), "Number"),
    "weight": (("Node",), "Number"),
    "duration": (("Node",), "Number"),
    "const": ((), "Number"),
    "add": (("Number", "Number"), "Number"),
    "sub": (("Number", "Number"), "Number"),
    "mul": (("Number", "Number"), "Number"),
    "div": (("Number", "Number"), "Number"),
    "min": (("Number", "Number"), "Number"),
    "max": (("Number", "Number"), "Number"),
    "abs": (("Number",), "Number"),
}


def graph_operation_library() -> dict:
    """Return a JSON-serializable library description for synthesis prompts."""
    return {
        op: {"arguments": list(arguments), "result": result}
        for op, (arguments, result) in GRAPH_OPERATION_TYPES.items()
    }


def _op(op: str, *args: dict) -> dict:
    return {"op": op, "args": list(args)}


NEIGHBOR_EDGE_MIN = _op(
    "edge_min_weight_sum", _op("induced_edges", _op("neighbors", _op("root")))
)
NEIGHBOR_EDGE_COUNT = _op(
    "count", _op("induced_edges", _op("neighbors", _op("root")))
)


@dataclass(frozen=True)
class _Expression:
    op: str
    args: tuple["_Expression", ...]
    value: float | None
    result_type: str
    depends_on_root: bool

    def to_dict(self) -> dict:
        if self.op == "const":
            return {"op": "const", "value": self.value}
        return {"op": self.op, "args": [argument.to_dict() for argument in self.args]}


def _compile_expression(source: dict) -> _Expression:
    count = 0

    def visit(item: Any, depth: int) -> _Expression:
        nonlocal count
        count += 1
        if count > MAX_EXPRESSION_NODES or depth > MAX_EXPRESSION_DEPTH:
            raise ValueError("Feature expression exceeds its size or depth limit")
        if not isinstance(item, dict) or not isinstance(item.get("op"), str):
            raise ValueError("Each feature expression must be an operation object")
        op = item["op"]
        if op not in GRAPH_OPERATION_TYPES:
            raise ValueError(f"Unknown graph operation: {op}")
        if op == "const":
            if set(item) != {"op", "value"}:
                raise ValueError("const requires exactly op and value")
            value = item["value"]
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e9:
                raise ValueError("Constants must be finite bounded numbers")
            return _Expression(op, (), float(value), "Number", False)
        if set(item) - {"op", "args"}:
            raise ValueError("Unexpected keys in feature expression")
        sources = item.get("args", [])
        if not isinstance(sources, list):
            raise ValueError("Operation args must be a list")
        expected, result_type = GRAPH_OPERATION_TYPES[op]
        if len(sources) != len(expected):
            raise ValueError(f"{op} requires {len(expected)} arguments")
        args = tuple(visit(argument, depth + 1) for argument in sources)
        for argument, wanted in zip(args, expected):
            if argument.result_type not in wanted.split("|"):
                raise ValueError(f"{op} expects {wanted}, received {argument.result_type}")
        return _Expression(op, args, None, result_type,
                           op == "root" or any(argument.depends_on_root for argument in args))

    tree = visit(source, 1)
    if tree.result_type != "Number":
        raise ValueError("A feature expression must return Number")
    return tree


def _internal_expression(source: dict) -> _Expression:
    """Compile numeric base-feature expressions with the same public type checker."""
    return _compile_expression(source)


_ROOT = _op("root")
_AVAILABLE = _op("available")
_NEIGHBORS = _op("neighbors", _ROOT)
_BASE_EXPRESSIONS = {
    "weight": _internal_expression(_op("weight", _ROOT)),
    "duration": _internal_expression(_op("duration", _ROOT)),
    "degree": _internal_expression(_op("count", _NEIGHBORS)),
    "conflict_weight": _internal_expression(_op("sum_weights", _NEIGHBORS)),
    "max_conflict_weight": _internal_expression(_op("max_weight", _NEIGHBORS)),
    "compatible_weight": _internal_expression(_op("sum_weights", _op(
        "difference", _op("difference", _AVAILABLE, _NEIGHBORS), _op("singleton", _ROOT)))),
    "remaining_count": _internal_expression(_op("count", _AVAILABLE)),
}


def _charge(meter: dict | None, primitive: str, amount: int = 1) -> None:
    if meter is not None:
        meter["feature_work"] = meter.get("feature_work", 0) + amount
        breakdown = meter.setdefault("feature_primitives", {})
        breakdown[primitive] = breakdown.get(primitive, 0) + amount


class _FeatureState:
    """Memoization is owned by one immutable active-set snapshot, not a graph."""

    def __init__(self, graph: Graph, active: set[str], meter: dict | None):
        self.graph = graph
        self.active = frozenset(active)
        if not self.active <= graph.nodes.keys():
            raise ValueError("Active set contains unknown nodes")
        self.meter = meter
        self.cache: dict[tuple[_Expression, str | None], Any] = {}

    def evaluate(self, expression: _Expression, root: str):
        key = (expression, root if expression.depends_on_root else None)
        if key in self.cache:
            return self.cache[key]
        args = [self.evaluate(argument, root) for argument in expression.args]
        op, graph = expression.op, self.graph
        _charge(self.meter, "operation")
        if op == "root":
            value = root
        elif op == "available":
            value = self.active
        elif op == "neighbors":
            _charge(self.meter, "neighbor_membership", len(graph.adj[args[0]]))
            value = frozenset(node for node in graph.adj[args[0]] if node in self.active)
        elif op == "singleton":
            _charge(self.meter, "active_membership")
            value = frozenset((args[0],)) if args[0] in self.active else frozenset()
        elif op in ("union", "intersection", "difference"):
            # Collection-scan units are a stable, declared proxy for set work.
            _charge(self.meter, "set_scan", len(args[0]) + len(args[1]))
            if op == "union":
                value = args[0] | args[1]
            elif op == "intersection":
                value = args[0] & args[1]
            else:
                value = args[0] - args[1]
        elif op == "induced_edges":
            nodes = sorted(args[0])
            _charge(self.meter, "edge_membership", len(nodes) * (len(nodes) - 1) // 2)
            value = frozenset((a, b) for i, a in enumerate(nodes)
                              for b in nodes[i + 1:] if b in graph.adj[a])
        elif op == "count":
            _charge(self.meter, "cardinality")
            value = len(args[0])
        elif op in ("sum_weights", "max_weight"):
            ordered = sorted(args[0])
            _charge(self.meter, "weight_read", len(ordered))
            _charge(self.meter, "aggregation", len(ordered))
            weights = [graph.nodes[node].weight for node in ordered]
            value = math.fsum(weights) if op == "sum_weights" else max(weights, default=0.0)
        elif op in ("clique_cover_weight", "greedy_independent_weight"):
            # Fixed polynomial graph primitives. They do not call a synthesis
            # provider or conditional oracle, and do not solve neighborhood MWIS.
            remaining = set(args[0])
            _charge(self.meter, "set_copy", len(remaining))
            terms = []
            if op == "greedy_independent_weight":
                order = sorted(remaining, key=lambda v: (-graph.nodes[v].weight, v))
                _charge(self.meter, "weight_read", len(order))
                for v in order:
                    _charge(self.meter, "active_membership")
                    if v not in remaining:
                        continue
                    terms.append(graph.nodes[v].weight)
                    _charge(self.meter, "adjacency_scan", len(graph.adj[v]))
                    remaining.difference_update(graph.adj[v] | {v})
            else:
                order = sorted(remaining, key=lambda v: (-graph.nodes[v].weight, v))
                _charge(self.meter, "weight_read", len(order))
                for v in order:
                    _charge(self.meter, "active_membership")
                    if v not in remaining:
                        continue
                    clique = [v]
                    remaining.remove(v)
                    for u in order:
                        _charge(self.meter, "active_membership")
                        if u not in remaining:
                            continue
                        compatible = True
                        for q in clique:
                            _charge(self.meter, "adjacency_membership")
                            if u not in graph.adj[q]:
                                compatible = False
                                break
                        if compatible:
                            clique.append(u)
                            remaining.remove(u)
                    terms.append(max(graph.nodes[q].weight for q in clique))
                    _charge(self.meter, "weight_read", len(clique))
            _charge(self.meter, "aggregation", len(terms))
            value = math.fsum(terms)
        elif op in ("edge_min_weight_sum", "edge_weight_product_sum"):
            edges = sorted(args[0])
            _charge(self.meter, "weight_read", 2 * len(edges))
            _charge(self.meter, "arithmetic", len(edges))
            _charge(self.meter, "aggregation", len(edges))
            terms = [min(graph.nodes[a].weight, graph.nodes[b].weight)
                     if op == "edge_min_weight_sum"
                     else graph.nodes[a].weight * graph.nodes[b].weight for a, b in edges]
            value = math.fsum(terms)
        elif op == "weight":
            _charge(self.meter, "weight_read")
            value = graph.nodes[args[0]].weight
        elif op == "duration":
            _charge(self.meter, "contact_field_read", 2)
            _charge(self.meter, "arithmetic")
            contact = graph.nodes[args[0]]
            value = contact.end - contact.start
        elif op == "const":
            value = expression.value
        else:
            _charge(self.meter, "arithmetic")
            if op == "add":
                value = args[0] + args[1]
            elif op == "sub":
                value = args[0] - args[1]
            elif op == "mul":
                value = args[0] * args[1]
            elif op == "div":
                if args[1] == 0:
                    raise ValueError("Feature division by zero")
                value = args[0] / args[1]
            elif op == "min":
                value = min(args)
            elif op == "max":
                value = max(args)
            else:  # abs, validated at construction
                value = abs(args[0])
        if expression.result_type == "Number" and not math.isfinite(value):
            raise ValueError("Feature values must be finite")
        self.cache[key] = value
        return value

    def feature_values(self, program: "FeatureRuleProgram", node: str) -> dict[str, float]:
        if node not in self.active:
            raise ValueError("Scored node must belong to the current active set")
        started = perf_counter()
        try:
            values = {name: self.evaluate(expression, node)
                      for name, expression in _BASE_EXPRESSIONS.items()}
            _charge(self.meter, "constraint_read", 4)
            values["station_gap"] = self.graph.constraints.get(
                "station_gap", self.graph.constraints.get("ground_trans_time", 0))
            values["satellite_gap"] = self.graph.constraints.get(
                "satellite_gap", self.graph.constraints.get("satellite_change_time", 0))
            values.update({name: self.evaluate(expression, node)
                           for name, expression in program._expressions})
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in values.values()):
                raise ValueError("Feature values must be finite numbers")
            return values
        except OverflowError as error:
            raise ValueError("Feature arithmetic overflow") from error
        finally:
            if self.meter is not None:
                self.meter["feature_seconds"] = self.meter.get("feature_seconds", 0.0) + (
                    perf_counter() - started)


def _compile_rule(rule: str, feature_names: tuple[str, ...]):
    if not isinstance(rule, str) or not rule.strip() or len(rule) > 2000:
        raise ValueError("Ranking rule must be a bounded expression string")
    try:
        tree = ast.parse(rule, mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise ValueError("Invalid ranking-rule syntax") from error
    nodes = list(ast.walk(tree))
    if len(nodes) > 256:
        raise ValueError("Ranking rule AST too large")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.IfExp, ast.Compare,
               ast.BoolOp, ast.Name, ast.Load, ast.Constant, ast.Call,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
               ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
               ast.And, ast.Or, ast.Not)
    for node in nodes:
        if not isinstance(node, allowed):
            raise ValueError(f"Disallowed ranking-rule syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in feature_names + _FUNCTIONS:
            raise ValueError(f"Unknown ranking-rule feature: {node.id}")
        if isinstance(node, ast.Call):
            if (not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS
                    or node.keywords or not 1 <= len(node.args) <= 8
                    or (node.func.id == "abs" and len(node.args) != 1)):
                raise ValueError("Only bounded min/max/abs calls are allowed")
        if isinstance(node, ast.Constant) and (
                type(node.value) not in (int, float) or not math.isfinite(node.value)
                or abs(node.value) > 1e9):
            raise ValueError("Only finite bounded numeric rule literals are allowed")
    return compile(tree, "<feature-ranking-rule>", "eval")


class FeatureRuleProgram:
    """A serializable typed representation and its safe numeric ranking rule."""

    def __init__(self, name: str, features: list[dict], rule: str, rationale: str = ""):
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError("Program name must be a nonempty bounded string")
        if not isinstance(rationale, str) or len(rationale) > 20000:
            raise ValueError("Program rationale must be a bounded string")
        if not isinstance(features, list) or len(features) > MAX_FEATURES:
            raise ValueError(f"At most {MAX_FEATURES} additional features are allowed")
        self.name, self.rule, self.rationale = name, rule, rationale
        expressions = []
        reserved = set(FEATURES + _FUNCTIONS)
        for feature in features:
            if not isinstance(feature, dict) or set(feature) != {"name", "expression"}:
                raise ValueError("Each feature requires exactly name and expression")
            feature_name = feature["name"]
            if (not isinstance(feature_name, str) or len(feature_name) > 80
                    or not _IDENTIFIER.fullmatch(feature_name) or keyword.iskeyword(feature_name)
                    or feature_name.startswith("__") or feature_name in reserved):
                raise ValueError("Feature names must be unique unreserved identifiers")
            reserved.add(feature_name)
            expressions.append((feature_name, _compile_expression(feature["expression"])))
        self._expressions = tuple(expressions)
        self.feature_names = FEATURES + tuple(name for name, _ in self._expressions)
        self.code = _compile_rule(rule, self.feature_names)

    @property
    def features(self) -> list[dict]:
        return [{"name": name, "expression": expression.to_dict()}
                for name, expression in self._expressions]

    @classmethod
    def from_dict(cls, source: dict) -> "FeatureRuleProgram":
        if not isinstance(source, dict) or set(source) != {"name", "features", "rule", "rationale"}:
            raise ValueError("Feature-rule program requires name, features, rule, and rationale")
        return cls(source["name"], source["features"], source["rule"], source["rationale"])

    def to_dict(self) -> dict:
        return {"name": self.name, "features": self.features,
                "rule": self.rule, "rationale": self.rationale}

    def evaluate_features(self, graph: Graph, node: str, active: set[str],
                          meter: dict | None = None) -> dict[str, float]:
        return _FeatureState(graph, active, meter).feature_values(self, node)

    def _rank(self, values: dict[str, float], meter: dict | None = None) -> float:
        started = perf_counter()
        try:
            result = float(eval(self.code, {"__builtins__": {}},
                                {**values, "min": min, "max": max, "abs": abs}))
        except (ZeroDivisionError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Invalid program score: {error}") from error
        finally:
            if meter is not None:
                meter["scoring_seconds"] = meter.get("scoring_seconds", 0.0) + (
                    perf_counter() - started)
        if not math.isfinite(result) or abs(result) > 1e15:
            raise ValueError("Program score must be finite and bounded")
        return result

    def score(self, graph: Graph, node: str, active: set[str], meter: dict | None = None) -> float:
        return self._rank(self.evaluate_features(graph, node, active, meter), meter)


def schedule_feature_program(graph: Graph, program: FeatureRuleProgram,
                             fixed=(), excluded=()) -> dict:
    """Execute a frozen program inside the unchanged feasible greedy kernel."""
    fixed, excluded = tuple(fixed), tuple(excluded)
    chosen = list(fixed)
    active = graph.available(fixed, excluded)
    trace = []
    meter = {"feature_work": 0, "feature_seconds": 0.0, "scoring_seconds": 0.0,
             "feature_primitives": {}}
    while active:
        state = _FeatureState(graph, active, meter)
        scores = {node: program._rank(state.feature_values(program, node), meter)
                  for node in sorted(active)}
        node = min(active, key=lambda item: (-scores[item], item))
        trace.append({"selected": node, "score": scores[node], "remaining_count": len(active)})
        chosen.append(node)
        active -= {node} | graph.adj[node]
    if not graph.feasible(chosen):
        raise AssertionError("Kernel feasibility invariant violated")
    return {"selected": sorted(chosen), "value": graph.value(chosen), "feasible": True,
            "trace": trace, **meter}


FEATURE_RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "features": {"type": "array", "maxItems": MAX_FEATURES, "items": {
            "type": "object", "properties": {
                "name": {"type": "string"}, "expression": {"type": "object"}},
            "required": ["name", "expression"], "additionalProperties": False}},
        "rule": {"type": "string"}, "rationale": {"type": "string"}},
    "required": ["name", "features", "rule", "rationale"],
    "additionalProperties": False,
}
