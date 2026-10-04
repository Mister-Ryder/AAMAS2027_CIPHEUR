from __future__ import annotations
import ast
from dataclasses import dataclass
import math
from .model import Graph

FEATURES = ("weight", "duration", "degree", "conflict_weight", "max_conflict_weight",
            "compatible_weight", "station_gap", "satellite_gap", "remaining_count")


def features(graph: Graph, v: str, remaining=None):
    active = set(graph.nodes) if remaining is None else set(remaining)
    adjacent = graph.adj[v] & active
    c = graph.nodes[v]
    return {"weight": c.weight, "duration": c.end - c.start, "degree": len(adjacent),
            "conflict_weight": sum(graph.nodes[u].weight for u in adjacent),
            "max_conflict_weight": max([graph.nodes[u].weight for u in adjacent] + [0]),
            "compatible_weight": sum(graph.nodes[u].weight for u in active - adjacent - {v}),
            "station_gap": graph.constraints.get("station_gap", graph.constraints.get("ground_trans_time", 0)),
            "satellite_gap": graph.constraints.get("satellite_gap", graph.constraints.get("satellite_change_time", 0)),
            "remaining_count": len(active)}


@dataclass
class Program:
    name: str
    expression: str
    rationale: str = ""

    def __post_init__(self):
        if not isinstance(self.expression, str) or len(self.expression) > 2000:
            raise ValueError("Program too large")
        self.tree = ast.parse(self.expression, mode="eval")
        nodes = list(ast.walk(self.tree))
        if len(nodes) > 256:
            raise ValueError("Program AST too large")
        allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.IfExp, ast.Compare,
                   ast.BoolOp, ast.Name, ast.Load, ast.Constant, ast.Call,
                   ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
                   ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
                   ast.And, ast.Or, ast.Not)
        for node in nodes:
            if not isinstance(node, allowed):
                raise ValueError(f"Disallowed syntax: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id not in FEATURES + ("min", "max", "abs"):
                raise ValueError("Unknown feature or function")
            if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or
                   node.func.id not in ("min", "max", "abs") or node.keywords or not 1 <= len(node.args) <= 8):
                raise ValueError("Only bounded min/max/abs calls allowed")
            if isinstance(node, ast.Constant) and (type(node.value) not in (int, float) or
                   not math.isfinite(node.value) or abs(node.value) > 1e9):
                raise ValueError("Only finite bounded numeric literals allowed")
        self.code = compile(self.tree, "<priority-program>", "eval")

    def score(self, feature_values):
        try:
            value = float(eval(self.code, {"__builtins__": {}},
                               {**feature_values, "min": min, "max": max, "abs": abs}))
        except (ZeroDivisionError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Invalid program score: {error}") from error
        if not math.isfinite(value) or abs(value) > 1e15:
            raise ValueError("Program score must be finite and bounded")
        return value

    def to_dict(self):
        return {"name": self.name, "expression": self.expression, "rationale": self.rationale}


def schedule(graph, program, fixed=(), excluded=()):
    chosen = list(fixed)
    active = graph.available(fixed, excluded)
    trace = []
    while active:
        scores = {v: program.score(features(graph, v, active)) for v in sorted(active)}
        v = min(active, key=lambda k: (-scores[k], k))
        trace.append({"selected": v, "score": scores[v], "remaining_count": len(active)})
        chosen.append(v)
        active -= {v} | graph.adj[v]
    if not graph.feasible(chosen):
        raise AssertionError("Kernel feasibility invariant violated")
    return {"selected": sorted(chosen), "value": graph.value(chosen), "feasible": True, "trace": trace}


def requirement_report(program, witnesses, margin=1e-8):
    checks = []
    for i, witness in enumerate(witnesses):
        pair_ok = True
        for side in ("left", "right"):
            graph = Graph.from_dict(witness[side])
            available = graph.available(witness["fixed"], witness["excluded"])
            a, b = witness["a"], witness["b"]
            scores = {v: program.score(features(graph, v, available)) for v in (a, b)}
            preferred = witness[side + "_preferred"]
            other = b if preferred == a else a
            ok = scores[preferred] > scores[other] + margin
            pair_ok &= ok
            checks.append({"witness": i, "side": side, "preferred": preferred,
                           "scores": scores, "passed": ok})
        checks[-1]["pair_passed"] = pair_ok
    return {"checks": checks, "passed": sum(c["passed"] for c in checks),
            "total": len(checks), "all_passed": all(c["passed"] for c in checks)}


PROGRAM_SCHEMA = {"type": "object", "properties": {
    k: {"type": "string"} for k in ("name", "expression", "rationale")},
    "required": ["name", "expression", "rationale"], "additionalProperties": False}
