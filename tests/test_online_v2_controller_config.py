"""Synthetic config/state tests; no model, benchmark or historical fitting."""
from copy import deepcopy
import random
import unittest

from cipheur.online_v2.controller import DEFAULT_CONFIG, OnlineController, validate_controller_config
from cipheur.online_v2.typed import PatchEvaluator, validate_recipe


def recipe(name="left", expression=None):
    expression = expression or {"op": "count", "args": [{"op": "neighbors", "args": [{"op": "root"}]}]}
    return {"name": name, "features": [{"name": "f", "expression": expression}],
            "rule": "weight + c0 * f",
            "patch_policy": {"anchor": "uniform", "destroy_count": 4, "patch_cap": 32,
                             "expand_hops": 1, "reconstruction": "greedy"},
            "evaluation_plan": {"feature_scope": "patch", "max_feature_cpu_fraction": .15, "lazy": True},
            "adaptation_template": {"mutation_scales": [.2, .2, .2, .2],
                                    "stagnation_trials": 8, "action": "mutate"},
            "coefficients": [1., 0., -2., .25],
            "rationale": "Synthetic test recipe, not an LLM output."}


def score(program, node=0):
    evaluator = PatchEvaluator({0: {1, 2}, 1: {0}, 2: {0}}, {0: 10, 1: 20, 2: 30},
                               program, program["coefficients"], {0, 1, 2}, {0, 1, 2})
    return evaluator.score(node)


class ControllerConfigTests(unittest.TestCase):
    def test_validation_is_explicit(self):
        self.assertEqual(validate_controller_config(), DEFAULT_CONFIG)
        for invalid in ({"unknown": 2}, {"evolve_every": True}, {"evolve_every": 16},
                        {"paired_race": 1}, {"credit_metric": "abs_signed_gain_per_cpu"}):
            with self.assertRaises(ValueError):
                validate_controller_config(invalid)
        config = validate_controller_config({"credit_metric": "absolute_signed_gain_per_cpu", "paired_race": True})
        self.assertEqual(config["credit_metric"], "absolute_signed_gain_per_cpu")

    def test_absolute_credit_has_no_removed_weight_bias_and_retains_negative(self):
        a = OnlineController([recipe()], config={"credit_metric": "absolute_signed_gain_per_cpu"})
        b = OnlineController([recipe()], config={"credit_metric": "absolute_signed_gain_per_cpu"})
        first = a.observe(a.population[0].id, 6, 1, .25)
        second = b.observe(b.population[0].id, 6, 12, .25)
        self.assertEqual(first["fitness_rate"], second["fitness_rate"])
        self.assertEqual(first["fitness_rate"], 24.)
        negative = a.observe(a.population[0].id, -60, 12, .25)
        self.assertEqual(negative["reward"], -60.)
        self.assertLess(negative["fitness_rate"], 0)
        self.assertEqual(a.statistics[a.population[0].id]["negative"], 1)

    def test_explicit_legacy_defaults_preserve_rng_and_mutation_behavior(self):
        bank = [recipe("a"), recipe("b")]
        original = OnlineController(bank, "graph")
        explicit = OnlineController(bank, "graph", config=DEFAULT_CONFIG)
        for index in range(24):
            left, right = original.select(), explicit.select()
            self.assertEqual(left.to_dict(), right.to_dict())
            original.observe(left.id, index % 3 - 1, 10, .02)
            explicit.observe(right.id, index % 3 - 1, 10, .02)
            self.assertEqual(original.statistics, explicit.statistics)
        self.assertEqual(original.mutation_count, explicit.mutation_count)

    def test_bounded_relative_uses_seed_center_not_random_walk(self):
        control = OnlineController([recipe()], mode="coefficients_only", config={"parameter_mode": "bounded_relative"})
        parent = control.population[0]
        rng = random.Random(9)
        centers = parent.coefficient_centers
        for _ in range(20):
            child = control.mutate(parent, rng)
            self.assertEqual(child.coefficient_centers, centers)
            self.assertEqual(child.coefficients[1], 0.)
            for value, center in zip(child.coefficients, centers):
                lower, upper = sorted((.5 * center, 1.5 * center))
                self.assertLessEqual(lower, value)
                self.assertLessEqual(value, upper)
            parent = child

    def test_atomic_template_combines_two_intact_semantic_blocks(self):
        left = recipe("left")
        right = recipe("right", {"op": "count", "args": [{"op": "singleton", "args": [{"op": "root"}]}]})
        left["coefficients"][0], right["coefficients"][0] = 2., 3.
        right["rule"] = "weight / (1 + degree) + c0 * f"
        left["adaptation_template"]["mutation_scales"] = [0., 0., 0., 0.]
        control = OnlineController([left, right], config={"parameter_mode": "bounded_relative", "structural_mode": "atomic_template"})
        parent = control.population[0]
        child = control.mutate(parent, random.Random(3))
        validate_recipe(child.recipe)
        self.assertEqual(child.mutation_kind, "atomic_template")
        self.assertEqual(len(child.features), 2)
        self.assertNotEqual(child.program_hash, parent.program_hash)
        self.assertNotIn(child.rule, (left["rule"], right["rule"]))
        self.assertAlmostEqual(score(child.recipe), .5 * score(left) + .5 * score(right))
        self.assertEqual(child.coefficient_centers, (.5, .5, 0., 0.))
        self.assertIn(parent.id, {g.id for g in control.population})
        self.assertTrue(any(e["event"] == "semantic_structure_mutation" and e["whole_score_blocks_preserved"]
                            for e in control.events))

    def test_same_operator_rewrite_changes_real_feature_tree(self):
        left = recipe("left")
        right = recipe("right", {"op": "count", "args": [{"op": "singleton", "args": [{"op": "root"}]}]})
        left["adaptation_template"]["mutation_scales"] = [0., 0., 0., 0.]
        control = OnlineController([left, right], config={"structural_mode": "same_operator_rewrite"})
        parent = control.population[0]
        child = control.mutate(parent, random.Random(3))
        self.assertEqual(child.mutation_kind, "same_operator_rewrite")
        self.assertEqual(child.rule, parent.rule)
        self.assertNotEqual(child.features, parent.features)
        self.assertEqual(child.features[0]["expression"], right["features"][0]["expression"])
        self.assertNotEqual(score(child.recipe), score(parent.recipe))
        self.assertNotEqual(child.representation_hash, parent.representation_hash)

    def test_structure_unavailable_is_not_falsely_reported_as_repair(self):
        control = OnlineController([recipe()], config={"structural_mode": "atomic_template", "parameter_mode": "bounded_relative"})
        parent = control.population[0]
        child = control.mutate(parent, random.Random(3))
        self.assertEqual(child.features, parent.features)
        self.assertEqual(child.rule, parent.rule)
        self.assertEqual(child.mutation_kind, "parameter_policy_only_structure_unavailable")
        self.assertTrue(any(e["event"] == "structural_mutation_unavailable" for e in control.events))

    def test_evolution_period_counts_credit_updates_and_reset_retains_config(self):
        control = OnlineController([recipe()], mode="coefficients_only",
                                   config={"evolve_every": 32, "paired_race": True})
        for _ in range(8):
            genome = control.select()
            control.observe(genome.id, 0, 12, .01)
        control.select()
        self.assertEqual(control.mutation_count, 0)
        for _ in range(24):
            genome = control.select()
            control.observe(genome.id, 0, 12, .01)
        control.select()
        self.assertEqual(control.mutation_count, 1)
        control.reset("new")
        self.assertEqual(control.update_count, 0)
        self.assertEqual(control.snapshot()["config"]["evolve_every"], 32)
        self.assertTrue(control.snapshot()["config"]["paired_race"])


if __name__ == "__main__":
    unittest.main()
