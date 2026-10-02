import copy
import json
import unittest
from unittest.mock import patch

from cipheur.graph_features import (
    FeatureRuleProgram, GRAPH_OPERATION_TYPES, NEIGHBOR_EDGE_COUNT,
    NEIGHBOR_EDGE_MIN, graph_operation_library, schedule_feature_program,
)
from cipheur.model import Contact, Graph, reversal_fixture
from cipheur.programs import Program, features, schedule


def op(name, *args):
    return {"op": name, "args": list(args)}


def fixture():
    contacts = tuple(Contact(node, weight, "s" + node, "g" + node, 0, 1)
                     for node, weight in (("r", 8), ("a", 5), ("b", 7), ("c", 2), ("d", 11)))
    return Graph("neighbor_path", contacts,
                 frozenset((("r", "a"), ("r", "b"), ("r", "c"),
                            ("a", "b"), ("b", "c"))), {"station_gap": 3})


def program(definitions=(), rule="weight"):
    return FeatureRuleProgram.from_dict({"name": "test", "features": list(definitions),
                                         "rule": rule, "rationale": "test fixture"})


class TypedFeatureTests(unittest.TestCase):
    def test_neighbor_edge_values_and_base_compatibility(self):
        graph = fixture()
        candidate = program([
            {"name": "n_edge_min", "expression": NEIGHBOR_EDGE_MIN},
            {"name": "n_edge_count", "expression": NEIGHBOR_EDGE_COUNT},
            {"name": "n_edge_products", "expression": op("edge_weight_product_sum", op(
                "induced_edges", op("neighbors", op("root"))))},
        ], "weight + n_edge_min - n_edge_count")
        values = candidate.evaluate_features(graph, "r", set(graph.nodes))
        self.assertEqual(values["n_edge_min"], 7)
        self.assertEqual(values["n_edge_count"], 2)
        self.assertEqual(values["n_edge_products"], 49)
        for name, value in features(graph, "r").items():
            self.assertEqual(values[name], value)
        self.assertEqual(candidate.score(graph, "r", set(graph.nodes)), 13)
        restored = FeatureRuleProgram.from_dict(json.loads(json.dumps(candidate.to_dict())))
        self.assertEqual(restored.to_dict(), candidate.to_dict())

    def test_active_set_change_never_reuses_previous_state(self):
        graph = fixture()
        candidate = program([{"name": "n_edge_min", "expression": NEIGHBOR_EDGE_MIN}], "n_edge_min")
        active = set(graph.nodes)
        meter = {}
        self.assertEqual(candidate.score(graph, "r", active, meter), 7)
        before = meter["feature_work"]
        active.remove("b")
        self.assertEqual(candidate.score(graph, "r", active, meter), 0)
        self.assertGreater(meter["feature_work"], before)
        with self.assertRaises(ValueError):
            candidate.score(graph, "b", active)
        with self.assertRaises(ValueError):
            candidate.score(graph, "r", active | {"unknown"})

    def test_shared_subtree_has_deterministic_work_and_real_timings(self):
        graph = fixture()
        single = program([{"name": "edges_one", "expression": NEIGHBOR_EDGE_MIN}])
        duplicate = program([{"name": "edges_one", "expression": NEIGHBOR_EDGE_MIN},
                             {"name": "edges_two", "expression": copy.deepcopy(NEIGHBOR_EDGE_MIN)}])
        other = program([{"name": "edges_one", "expression": NEIGHBOR_EDGE_MIN},
                         {"name": "edges_count", "expression": NEIGHBOR_EDGE_COUNT}])
        meters = [{}, {}, {}]
        for candidate, meter in zip((single, duplicate, other), meters):
            candidate.score(graph, "r", set(graph.nodes), meter)
            self.assertGreater(meter["feature_seconds"], 0)
            self.assertGreater(meter["scoring_seconds"], 0)
            self.assertEqual(meter["feature_work"], sum(meter["feature_primitives"].values()))
            # The three unordered pairs inside the neighbor set are traversed once.
            self.assertEqual(meter["feature_primitives"]["edge_membership"], 3)
        self.assertEqual(meters[0]["feature_work"], meters[1]["feature_work"])
        self.assertEqual(meters[2]["feature_work"] - meters[0]["feature_work"], 2)
        repeat = {}
        single.score(graph, "r", set(graph.nodes), repeat)
        self.assertEqual(repeat["feature_work"], meters[0]["feature_work"])

    def test_set_and_arithmetic_operations_respect_types(self):
        graph = fixture()
        root, available = op("root"), op("available")
        neighbors = op("neighbors", root)
        combined = op("union", op("singleton", root), neighbors)
        definitions = [
            {"name": "outside", "expression": op("sum_weights", op("difference", available, combined))},
            {"name": "overlap", "expression": op("count", op("intersection", neighbors, combined))},
            {"name": "arithmetic", "expression": op("abs", op("div", op("sub",
                {"op": "const", "value": 2}, op("max_weight", neighbors)),
                {"op": "const", "value": 2}))},
        ]
        values = program(definitions).evaluate_features(graph, "r", set(graph.nodes))
        self.assertEqual(values["outside"], 11)
        self.assertEqual(values["overlap"], 3)
        self.assertEqual(values["arithmetic"], 2.5)
        self.assertEqual(set(graph_operation_library()), set(GRAPH_OPERATION_TYPES))

    def test_type_errors_unknown_ops_and_unbounded_expressions_are_rejected(self):
        wrong = (
            op("neighbors", op("available")),
            op("count", op("root")),
            op("sum_weights", op("induced_edges", op("available"))),
            op("induced_edges", op("available")),
            op("oracle", op("root")),
            {"op": "const", "value": True},
            {"op": "const", "value": float("inf")},
            {"op": "weight", "args": [op("root")], "python": "__import__('os')"},
            {"op": "count", "args": "available"},
        )
        for expression in wrong:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                program([{"name": "bad", "expression": expression}])
        deep = {"op": "const", "value": 1}
        for _ in range(8):
            deep = op("abs", deep)
        with self.assertRaises(ValueError):
            program([{"name": "deep", "expression": deep}])
        wide = {"op": "const", "value": 1}
        for _ in range(5):
            wide = op("add", wide, copy.deepcopy(wide))
        with self.assertRaises(ValueError):
            program([{"name": "wide", "expression": wide}])

    def test_names_schema_and_rule_injections_are_rejected(self):
        for name in ("weight", "min", "bad-name", "class", "__builtins__"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                program([{"name": name, "expression": NEIGHBOR_EDGE_MIN}])
        with self.assertRaises(ValueError):
            program([{"name": "duplicate", "expression": NEIGHBOR_EDGE_MIN}] * 2)
        with self.assertRaises(ValueError):
            program([{"name": "n" + str(i), "expression": NEIGHBOR_EDGE_MIN} for i in range(7)])
        for rule in ("__import__('os')", "weight.__class__", "[weight][0]", "weight ** 2",
                     "sum(x for x in [])", "unknown", "abs(weight, degree)", "max(weight=1)"):
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                program(rule=rule)
        with self.assertRaises(ValueError):
            FeatureRuleProgram.from_dict({"name": "incomplete", "features": [], "rule": "weight"})

    def test_invalid_runtime_values_are_rejected(self):
        graph = fixture()
        zero = op("div", {"op": "const", "value": 1}, {"op": "const", "value": 0})
        with self.assertRaises(ValueError):
            program([{"name": "zero", "expression": zero}]).score(graph, "r", set(graph.nodes))
        with self.assertRaises(ValueError):
            program(rule="weight / 0").score(graph, "r", set(graph.nodes))
        with self.assertRaises(ValueError):
            program(rule="1000000000 * 1000000000").score(graph, "r", set(graph.nodes))


class FrozenFeatureKernelTests(unittest.TestCase):
    def test_equivalent_base_rule_and_boundary_invariants(self):
        for graph in reversal_fixture():
            for rule in ("weight", "-weight", "weight / (1 + degree)",
                         "weight - conflict_weight", "weight if degree < 2 else -duration"):
                result = schedule_feature_program(graph, program(rule=rule), fixed=("d",), excluded=("c",))
                original = schedule(graph, Program("original", rule), fixed=("d",), excluded=("c",))
                self.assertEqual(result["selected"], original["selected"])
                self.assertEqual(result["trace"], original["trace"])
                self.assertTrue(graph.feasible(result["selected"]))
                self.assertIn("d", result["selected"])
                self.assertNotIn("c", result["selected"])
                self.assertGreater(result["feature_work"], 0)
                self.assertEqual(result["feature_work"], sum(result["feature_primitives"].values()))

    def test_no_oracle_or_llm_call_during_frozen_execution(self):
        graph = fixture()
        candidate = program([{"name": "n_edge_min", "expression": NEIGHBOR_EDGE_MIN}],
                            "weight - conflict_weight + n_edge_min")
        with patch("cipheur.oracle.solve", side_effect=AssertionError("Online oracle call")), \
             patch("cipheur.oracle.certify_pair", side_effect=AssertionError("Online certificate call")), \
             patch("cipheur.providers.generate_candidate", side_effect=AssertionError("Online LLM call")):
            result = schedule_feature_program(graph, candidate)
        self.assertTrue(result["feasible"])
        self.assertTrue(graph.feasible(result["selected"]))

    def test_empty_and_invalid_boundaries(self):
        graph = fixture()
        empty = schedule_feature_program(graph, program(), excluded=tuple(graph.nodes))
        self.assertEqual(empty["selected"], [])
        self.assertEqual(empty["feature_work"], 0)
        self.assertEqual(empty["feature_seconds"], 0)
        for fixed, excluded in ((("r", "a"), ()), (("r", "r"), ()),
                                (("r",), ("r",)), ((), ("unknown",))):
            with self.assertRaises(ValueError):
                schedule_feature_program(graph, program(), fixed=fixed, excluded=excluded)
        result = schedule_feature_program(graph, program(), fixed=(node for node in ("r",)),
                                          excluded=(node for node in ("d",)))
        self.assertEqual(result["selected"], ["r"])
        self.assertEqual(result["feature_work"], 0)


if __name__ == "__main__":
    unittest.main()
