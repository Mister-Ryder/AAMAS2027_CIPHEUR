"""Tiny independent checks; no actual TRAIN feature values or masters executed."""
import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from cipheur.model import Contact, Graph
from cipheur.refinement import minimum_cost_vector_refinement
from scripts import run_catalogue_refinement_v06 as study


class CatalogueCostTests(unittest.TestCase):
    def test_static_union_ignores_names_eligibility_quality_and_numeric_spelling(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rows.jsonl"
            rows = []
            for block, arm, slot in itertools.product(range(5), ("witness", "relations", "objective"), range(8)):
                rows.append({"id": f"block_{block}_{arm}:{slot}", "status": "static_valid",
                             "eligible": bool(slot % 2), "kernel_summary": {"macro_quality_exact": str(slot)},
                             "program": {"name": "p", "features": [{"name": "alias" + str(slot),
                                  "expression": {"op": "const", "value": 1 if slot % 2 else 1.0}}],
                                         "rule": "weight", "rationale": ""}})
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with patch.object(study, "_FeatureState", side_effect=AssertionError("must not evaluate")):
                catalogue, inventory = study.collect_catalogue(path)
            self.assertEqual(len(catalogue), 1)
            self.assertEqual(len(catalogue[0]["original_metadata_sources"]), 120)
            self.assertEqual(inventory["all_original_positions"], 120)
            self.assertEqual(catalogue[0]["expression"], {"op": "const", "value": 1.0})

    def test_independent_cut_DP_matches_exhaustive_weighted_cardinality_search(self):
        rng = random.Random(604)
        names = ["f" + str(i) for i in range(8)]
        for _ in range(30):
            costs = {name: rng.randrange(1, 10) for name in names}
            cuts = [set(rng.sample(names, rng.randrange(1, 6))) for _ in range(rng.randrange(1, 7))]
            k = rng.randrange(0, 5)
            feasible = [chosen for n in range(k + 1) for chosen in itertools.combinations(names, n)
                        if all(set(chosen) & cut for cut in cuts)]
            best = min(feasible, key=lambda chosen: (sum(costs[x] for x in chosen), len(chosen), chosen)) if feasible else None
            proof = study.independent_cut_master(cuts, costs, k, 100000)
            self.assertTrue(proof["complete"])
            self.assertEqual(proof["feasible"], best is not None)
            if best is not None:
                self.assertEqual(proof["selected_names"], list(best))
                self.assertEqual(proof["cost_exact"], str(sum(costs[x] for x in best)))
        truncated = study.independent_cut_master([{"f0"}], {"f0": 1}, 1, 0)
        self.assertFalse(truncated["complete"])
        self.assertIsNone(truncated["cost_exact"])

    def test_independent_quotient_preserves_integer_and_binary_float_equality(self):
        occurrences = {"a": {"base": 1}, "b": {"base": 1.0}}
        req = [{"preferred": "a", "other": "b"}]
        values = {"f": {"a": 2**53, "b": 2**53 + 1}}
        checker = study.IndependentQuotient(occurrences, req, values)
        self.assertFalse(checker.check([])["acyclic"])
        self.assertTrue(checker.check(["f"])["acyclic"])
        values["f"]["b"] = float(2**53 + 1)
        self.assertFalse(study.IndependentQuotient(occurrences, req, values).check(["f"])["acyclic"])

    def fixture(self):
        occurrences = {x: {"base": 0} for x in "abcd"}
        requirements = [{"preferred": "a", "other": "b"}, {"preferred": "c", "other": "d"}]
        values = {"f1": dict(zip("abcd", [1, 0, 0, 0])),
                  "f2": dict(zip("abcd", [0, 0, 1, 0])),
                  "f3": dict(zip("abcd", [1, 0, 1, 0]))}
        costs = {"f1": 2, "f2": 1, "f3": 5}
        protocol = {"max_selected": 2, "independent_master_max_states_total_per_catalogue": 10000,
                    "independent_exhaustive_max_subsets": 10000}
        return occurrences, requirements, values, costs, protocol

    def test_full_multiple_cycles_and_additive_optimum_have_independent_proofs(self):
        occurrences, requirements, values, costs, protocol = self.fixture()
        result = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_selected=2)
        self.assertGreaterEqual(len(result["rounds"]), 2)
        self.assertEqual(result["cost_exact"], "3")
        audit = study.audit_refinement(result, occurrences, requirements, values, costs, protocol, True)
        self.assertTrue(audit["independently_verified_additive_minimum"])
        self.assertTrue(audit["exhaustive"]["complete"])
        self.assertEqual(audit["exhaustive"]["subsets_enumerated"], 7)
        corrupt = json.loads(json.dumps(result))
        corrupt["witnesses"][0]["equality_joins"][0]["positive"] = "c"
        with self.assertRaisesRegex(ValueError, "does not close"):
            study.audit_refinement(corrupt, occurrences, requirements, values, costs, protocol, True)

    def test_budget_unknown_is_not_relabelled_even_when_enumeration_finds_repair(self):
        occurrences, requirements, values, costs, protocol = self.fixture()
        result = minimum_cost_vector_refinement(occurrences, requirements, values, costs,
                                                max_selected=2, max_master_subsets=0)
        self.assertEqual(result["reason"], "master_budget_exhausted")
        audit = study.audit_refinement(result, occurrences, requirements, values, costs, protocol, True)
        self.assertTrue(audit["exhaustive"]["feasible"])
        self.assertFalse(audit["independently_verified_additive_minimum"])

    def test_tiny_feature_cost_is_positive_and_all_unique_occurrences_are_retained(self):
        graph = Graph("tiny", (Contact("a", 1, "s", "a", 0, 1), Contact("b", 2, "s", "b", 0, 1)),
                      frozenset({("a", "b")}))
        frame = {"graphs": {"s": graph}, "active": {"s": {"a", "b"}}, "endpoints": {"s": ["a", "b"]}}
        entry = {"name": "constant", "expression": {"op": "const", "value": 0}}
        with patch.object(study, "WORKER_FRAME", frame), patch.object(study, "WORKER_SETUP", {}):
            row = study.evaluate_feature((entry, {"max_work": 100000, "cpu_seconds": 60}))
        self.assertTrue(row["completed"])
        self.assertEqual(row["values"], {"s|a": 0.0, "s|b": 0.0})
        self.assertGreater(row["positive_additive_cost"], 0)
        self.assertEqual(row["positive_additive_cost"], max(1, row["meter"]["feature_work"]))
        with patch.object(study, "WORKER_FRAME", frame), patch.object(study, "WORKER_SETUP", {}):
            failed = study.evaluate_feature((entry, {"max_work": 0, "cpu_seconds": 60}))
        self.assertFalse(failed["completed"])
        self.assertIsNone(failed["positive_additive_cost"])
        self.assertEqual(failed["status"], "feature_evaluation_failed")


if __name__ == "__main__":
    unittest.main()
