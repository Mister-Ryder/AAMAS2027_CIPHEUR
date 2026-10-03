import math
import random
import unittest

from cipheur.compiled import CompiledEvaluator, schedule_compiled
from cipheur.graph_features import FeatureRuleProgram, schedule_feature_program
from cipheur.model import Contact, Graph


def op(name, *args):
    return {"op": name, "args": list(args)}


ROOT = op("root")
NEIGHBORS = op("neighbors", ROOT)
NEIGHBOR_EDGES = op("induced_edges", NEIGHBORS)
AVAILABLE = op("available")


def program():
    return FeatureRuleProgram("compiled_test", [
        {"name": "tri_count", "expression": op("count", NEIGHBOR_EDGES)},
        {"name": "tri_min", "expression": op("edge_min_weight_sum", NEIGHBOR_EDGES)},
        {"name": "tri_product", "expression": op("edge_weight_product_sum", NEIGHBOR_EDGES)},
        {"name": "global_edges", "expression": op("count", op("induced_edges", AVAILABLE))},
        {"name": "global_weight", "expression": op("sum_weights", AVAILABLE)},
        {"name": "fallback", "expression": op("sum_weights", op("intersection", AVAILABLE, NEIGHBORS))},
    ], "weight - 0.3*conflict_weight + tri_min/max(1,degree) + 0.00001*tri_product")


def graph(weights, edges, name="test"):
    contacts = tuple(Contact(str(i), weight, f"s{i}", f"g{i}", i, i + 1)
                     for i, weight in enumerate(weights))
    return Graph(name, contacts, frozenset((str(a), str(b)) for a, b in edges),
                 {"station_gap": 0.25, "satellite_gap": 0.5})


class CompiledTests(unittest.TestCase):
    def assert_state_matches(self, evaluator):
        for node in sorted(evaluator.active):
            reference = evaluator.program.evaluate_features(
                evaluator.graph, node, evaluator.active)
            self.assertEqual(evaluator.feature_values(node), reference)
            self.assertEqual(evaluator.score(node), evaluator.program.score(
                evaluator.graph, node, evaluator.active))

    def test_overlapping_batch_deletions_preserve_all_aggregates(self):
        # Two triangles share an edge, so subtracting each deleted triangle
        # edge twice would corrupt both the count and min/product sums.
        g = graph([0.1, 0.2, 0.3, 0.4, 0.7],
                  [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (3, 4)])
        evaluator = CompiledEvaluator(g, program(), g.nodes)
        self.assert_state_matches(evaluator)
        evaluator.remove(["0", "1", "0"])
        self.assert_state_matches(evaluator)
        evaluator.remove(["0", "3"])
        self.assert_state_matches(evaluator)
        evaluator.remove(evaluator.active.copy())
        self.assertEqual(evaluator.active, set())
        self.assertEqual(evaluator.total_weight, 0)

    def test_random_deletion_states_have_identical_numeric_interface(self):
        rng = random.Random(8417)
        p = program()
        for index in range(35):
            n = rng.randrange(3, 18)
            weights = [rng.choice([0, 0.1, 0.2, 1.0, rng.random() * 20,
                                   rng.random() * 1e8]) for _ in range(n)]
            edges = [(i, j) for i in range(n) for j in range(i + 1, n)
                     if rng.random() < 0.45]
            g = graph(weights, edges, str(index))
            evaluator = CompiledEvaluator(g, p, g.nodes)
            order = list(g.nodes)
            rng.shuffle(order)
            self.assert_state_matches(evaluator)
            for start in range(0, n, 3):
                evaluator.remove(order[start:start + 3])
                self.assert_state_matches(evaluator)

    def test_random_frozen_schedules_match_reference_traces(self):
        rng = random.Random(7813)
        p = program()
        for index in range(50):
            n = rng.randrange(1, 28)
            weights = [rng.random() * 15 + 0.01 for _ in range(n)]
            edges = [(i, j) for i in range(n) for j in range(i + 1, n)
                     if rng.random() < rng.choice([0.1, 0.4, 0.7])]
            g = graph(weights, edges, str(index))
            reference, compiled = schedule_feature_program(g, p), schedule_compiled(g, p)
            for key in ("selected", "trace", "value", "feasible"):
                self.assertEqual(compiled[key], reference[key])
            self.assertEqual(compiled["feature_work"], compiled["initialization_work"]
                             + compiled["update_work"] + compiled["query_work"])
            self.assertGreater(compiled["query_work"], 0)

    def test_large_integer_and_near_tie_semantics_match(self):
        g = graph([2**53, 2**53 + 1, 2**53 + 3, 1, 3, 7],
                  [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4), (3, 5), (4, 5)])
        original = program()
        p = FeatureRuleProgram("large_features", original.features, "weight / 1e6")
        evaluator = CompiledEvaluator(g, p, g.nodes)
        self.assert_state_matches(evaluator)
        evaluator.remove(["0", "4"])
        self.assert_state_matches(evaluator)
        for rule in ("weight", "weight - conflict_weight", "compatible_weight", "degree"):
            current = FeatureRuleProgram("large", [], f"({rule}) / 1e6")
            self.assertEqual(schedule_compiled(g, current)["trace"],
                             schedule_feature_program(g, current)["trace"])

    def test_fixed_excluded_boundary_and_empty_state(self):
        g = graph([4, 6, 3, 5, 1], [(0, 1), (1, 2), (2, 3)])
        p = program()
        for fixed, excluded in ((["0"], ["4"]), ([], list(g.nodes))):
            reference = schedule_feature_program(g, p, fixed, excluded)
            compiled = schedule_compiled(g, p, fixed, excluded)
            self.assertEqual(compiled["trace"], reference["trace"])
            self.assertEqual(compiled["selected"], reference["selected"])
            self.assertTrue(compiled["feasible"])
        with self.assertRaises(ValueError):
            schedule_compiled(g, p, ["0", "1"])

    def test_generic_root_independent_expression_is_shared_per_snapshot(self):
        g = graph([1, 2, 3, 4], [(0, 1), (1, 2), (2, 3)])
        shared = op("count", op("induced_edges", AVAILABLE))
        p = FeatureRuleProgram("shared", [
            {"name": "one", "expression": shared},
            {"name": "two", "expression": shared},
        ], "weight + one - two")
        evaluator = CompiledEvaluator(g, p, g.nodes)
        first = evaluator.feature_values("0")
        membership_after_first = evaluator.meter["feature_primitives"].get("edge_membership", 0)
        second = evaluator.feature_values("1")
        self.assertEqual(first["one"], second["two"])
        self.assertEqual(evaluator.meter["feature_primitives"].get("edge_membership", 0),
                         membership_after_first)
        self.assertGreater(evaluator.metadata["shared_nodes_saved"], 0)
        evaluator.remove(["0"])
        self.assert_state_matches(evaluator)
        self.assertGreater(evaluator.meter["feature_primitives"].get("edge_membership", 0),
                           membership_after_first)

    def test_product_overflow_is_not_evaluated_for_unused_edges(self):
        # The graph has an edge but no triangle, so every induced-neighborhood
        # product sum is empty. Precomputing products for all graph edges would
        # spuriously reject a valid reference program.
        g = graph([1e200, 1e200], [(0, 1)])
        p = FeatureRuleProgram("empty_products", [
            {"name": "products", "expression": op("edge_weight_product_sum", NEIGHBOR_EDGES)},
        ], "weight * 0")
        evaluator = CompiledEvaluator(g, p, g.nodes)
        self.assert_state_matches(evaluator)
        self.assertEqual(evaluator.feature_values("0")["products"], 0.0)

    def test_near_cancellation_in_updates_does_not_leave_residual_noise(self):
        g = graph([1e20, 0.1, 0.2, 0.3, 0.4],
                  [(i, j) for i in range(5) for j in range(i + 1, 5)])
        evaluator = CompiledEvaluator(g, program(), g.nodes)
        evaluator.remove(["0", "1", "2"])
        self.assert_state_matches(evaluator)
        self.assertEqual(evaluator.feature_values("3")["conflict_weight"], 0.4)
        self.assertTrue(math.isfinite(evaluator.feature_values("3")["tri_product"]))


if __name__ == "__main__":
    unittest.main()
