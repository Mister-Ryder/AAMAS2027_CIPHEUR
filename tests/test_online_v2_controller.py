"""Small state/structural-mutation fixtures; not model proposals or benchmarks."""
from copy import deepcopy
import random
import unittest

from cipheur.online_v2.controller import OnlineController
from cipheur.online_v2.typed import validate_recipe


def recipe(name="synthetic_fixture"):
    return {"name": name,
            "features": [{"name": "twohop_edges", "expression":
                {"op": "count", "args": [{"op": "incident_edges", "args": [
                    {"op": "neighbors_of_set", "args": [{"op": "neighbors", "args": [
                        {"op": "root", "args": []}]}]}]}]}}],
            "rule": "weight / (1 + degree) + c0 * twohop_edges",
            "patch_policy": {"anchor": "uniform", "destroy_count": 4,
                             "patch_cap": 32, "expand_hops": 1,
                             "reconstruction": "greedy"},
            "evaluation_plan": {"feature_scope": "patch",
                                "max_feature_cpu_fraction": .15, "lazy": True},
            "adaptation_template": {"mutation_scales": [.2, .2, .2, .2],
                                    "stagnation_trials": 8, "action": "mutate"},
            "coefficients": [1., 1., 1., 1.],
            "rationale": "Synthetic unit-test fixture; no LLM provenance."}


class OnlineControllerTests(unittest.TestCase):
    def test_raw_negative_quality_updates_credit(self):
        controller = OnlineController([recipe()], "graph-A")
        genome = controller.select(random.Random(2), {"trial": 0})
        result = controller.observe(genome.id, -25, 100, .01)
        self.assertEqual(result["reward"], -.25)
        self.assertLess(result["fitness_rate"], 0)
        self.assertEqual(controller.statistics[genome.id]["negative"], 1)
        self.assertEqual(controller.statistics[genome.id]["gain_ticks"], -25)

    def test_reset_drops_all_current_instance_learning(self):
        controller = OnlineController([recipe()], "graph-A")
        old = controller.select()
        controller.observe(old.id, 20, 100, .01, .9)
        controller.mutate(old, random.Random(4))
        controller.notify_cycle("actual-test-cycle", {"has_cycle": True, "instance_id": "graph-A"})
        controller.reset("graph-B")
        self.assertEqual(controller.update_count, 0)
        self.assertEqual(controller.selected_count, 0)
        self.assertEqual(controller.mutation_count, 0)
        self.assertEqual(controller.cycle_notifications, 0)
        self.assertEqual(len(controller.population), 1)
        self.assertEqual(controller.population[0].recipe, recipe())
        self.assertTrue(all(s["observations"] == 0 for s in controller.statistics.values()))
        with self.assertRaises(KeyError):
            controller.observe(old.id, 1, 100, .01)

    def test_mutation_changes_representation_or_rule_not_only_coefficients(self):
        controller = OnlineController([recipe()], "graph-A")
        rng = random.Random(7)
        parent = controller.population[0]
        changed_representation = False
        for _ in range(12):
            child = controller.mutate(parent, rng)
            validate_recipe(child.recipe)
            self.assertTrue(child.features != parent.features or child.rule != parent.rule)
            self.assertNotEqual(child.program_hash, parent.program_hash)
            changed_representation |= child.features != parent.features
            self.assertLessEqual(len(controller.population), 4)
        self.assertTrue(changed_representation)

    def test_select_evolves_after_actual_observations(self):
        controller = OnlineController([recipe()], "graph-A")
        rng = random.Random(2)
        for _ in range(8):
            genome = controller.select(rng)
            controller.observe(genome.id, 0, 100, .01)
        selected = controller.select(rng)
        self.assertEqual(controller.mutation_count, 1)
        self.assertGreater(selected.generation, 0)
        self.assertTrue(any(e["event"] == "adaptation" for e in controller.events))

    def test_archive_fit_does_not_replace_quality_cost(self):
        controller = OnlineController([recipe("a"), recipe("b")], "graph-A")
        first, second = controller.population
        controller.observe(first.id, 10, 100, .01, 1.)
        controller.observe(second.id, 20, 100, .01, 0.)
        self.assertEqual(controller.select(random.Random(2)).id, second.id)
        self.assertFalse(controller.events[-1]["current_archive_fit_tiebreak"])

    def test_archive_fit_breaks_equal_quality_cost_tie(self):
        controller = OnlineController([recipe("a"), recipe("b")], "graph-A")
        first, second = controller.population
        controller.observe(first.id, 10, 100, .01, .1)
        controller.observe(second.id, 10, 100, .01, .9)
        self.assertEqual(controller.select(random.Random(2)).id, second.id)
        self.assertTrue(controller.events[-1]["current_archive_fit_tiebreak"])

    def test_only_actual_cycle_can_request_witness_mutation(self):
        controller = OnlineController([recipe()], "graph-A")
        with self.assertRaises(ValueError):
            controller.notify_cycle("fit-failure", {"has_cycle": False})
        with self.assertRaises(ValueError):
            controller.notify_cycle("foreign-cycle", {"has_cycle": True, "instance_id": "graph-B"})
        genome = controller.select()
        controller.observe(genome.id, 0, 100, .01)
        controller.notify_cycle("test-cycle", {"has_cycle": True, "instance_id": "graph-A"})
        child = controller.select(random.Random(3))
        self.assertEqual(child.mutation_kind, "current_cycle_feature_import")
        self.assertEqual(controller.witness_mutations, 1)
        self.assertTrue(any(e["event"] == "witness_mutation" and not e["ranking_repaired"]
                            for e in controller.events))

    def test_fixed_mode_does_not_adapt(self):
        controller = OnlineController([recipe("a"), recipe("b")], "graph-A", mode="fixed")
        original = controller.population
        for index in range(16):
            selected = controller.select()
            self.assertEqual(selected.id, original[index % len(original)].id)
            controller.observe(selected.id, 0, 100, .01)
        self.assertEqual(controller.mutation_count, 0)
        with self.assertRaises(RuntimeError):
            controller.mutate(original[0])


if __name__ == "__main__":
    unittest.main()
