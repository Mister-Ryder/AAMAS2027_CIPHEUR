"""Checks for frozen-program follow-up identity and audit invariants."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur.experiment_data import make_suite, _record
from cipheur.experiments import serialize_pair, save
from cipheur.followup import fresh_records, prior_identities, run, _protect_c3
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph


class FollowupTests(unittest.TestCase):
    def test_later_indices_are_disjoint_from_every_prior_split(self):
        old_config = {"counts": {"diagnostic": 2, "random_temporal": 2, "c3": 0}}
        old_suite = make_suite(old_config)
        old_data = {split: [serialize_pair(record) for record in old_suite[split]]
                    for split in ("train", "validation", "test")}
        with patch("cipheur.oracle.solve", side_effect=AssertionError("Generation called an oracle")):
            suite = make_suite({"counts": {"diagnostic": 5, "random_temporal": 4, "c3": 0}})
            fresh, audit = fresh_records(suite, old_data, old_config)
        self.assertEqual(audit["families"], {"diagnostic": 3, "random_temporal": 2})
        self.assertEqual(audit["prefix_pairs_excluded"], {"diagnostic": 2, "random_temporal": 2})
        protected = prior_identities(old_data)
        for record in fresh:
            self.assertEqual(record["source"]["split"], "test")
            self.assertGreaterEqual(int(record["id"].rsplit("_", 1)[1]), 2)
            for side in ("left", "right"):
                self.assertNotIn(record[side].digest(), protected["graphs"])
            self.assertNotIn(record["source"]["seed"], protected["seeds"])

    def test_reused_prior_instance_is_rejected_even_if_not_a_prior_test(self):
        old = make_suite({"counts": {"diagnostic": 1, "random_temporal": 0, "c3": 0}})
        prior = {"train": [serialize_pair(old["test"][0])], "validation": [], "test": []}
        with self.assertRaisesRegex(ValueError, "record ID"):
            fresh_records(old, prior, {"counts": {"diagnostic": 0, "random_temporal": 0, "c3": 0}})

    def test_c3_identity_exclusion_preserves_induced_graph_and_reports_counts(self):
        contacts = (Contact("1", 3, "s1", "g", 0, 3), Contact("2", 2, "s2", "g", 2, 4),
                    Contact("3", 1, "s3", "h", 0, 1))
        source = {"split": "test", "original_ids": [1, 2, 3], "arc_metadata": {str(i): {} for i in (1, 2, 3)}}
        left = Graph("c3_before", contacts, frozenset({("1", "2")}),
                     {"model": "v51_legacy", "ground_trans_time": 340})
        right = Graph("c3_after", contacts, frozenset({("1", "2")}),
                      {"model": "v51_legacy", "ground_trans_time": 700})
        record = _record("c3_test_0008", "c3", left, right, source, fixed=("3",))
        fresh, receipt = _protect_c3(record, {1})
        self.assertEqual(receipt["prior_opportunities_removed_count"], 1)
        self.assertEqual(fresh["source"]["original_ids"], [2, 3])
        self.assertEqual(set(fresh["left"].nodes), {"2", "3"})
        self.assertFalse(fresh["left"].edges)
        self.assertEqual(fresh["fixed"], ("3",))
        self.assertIsNone(fresh["a"])
        self.assertIsNone(fresh["b"])
        empty, receipt = _protect_c3(record, {1, 2, 3})
        self.assertIsNone(empty)
        self.assertEqual(receipt["retention_reason"], "no_unseen_opportunities_after_identity_exclusion")

    def test_small_complete_followup_keeps_frozen_bytes_and_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            pilot, output = Path(directory) / "old", Path(directory) / "fresh"
            pilot.mkdir()
            config = {"counts": {"diagnostic": 1, "random_temporal": 1, "c3": 0},
                      "oracle": {"max_calls": 100, "max_nodes": 100000, "nodes_per_call": 10000},
                      "reference_max_nodes": 100000}
            old = make_suite(config)
            save(pilot / "config.json", config)
            save(pilot / "data.json", {split: [serialize_pair(record) for record in old[split]]
                                      for split in ("train", "validation", "test")})
            frozen = {"weight": FeatureRuleProgram("weight", [], "weight").to_dict(),
                      "weight_degree": FeatureRuleProgram("degree", [], "weight / (1 + degree)").to_dict()}
            save(pilot / "frozen_programs.json", frozen)
            before = (pilot / "frozen_programs.json").read_bytes()
            summary = run(pilot, output, counts={"diagnostic": 3, "random_temporal": 2, "c3": 0})
            self.assertEqual(before, (output / "frozen_programs.json").read_bytes())
            self.assertEqual(before, (pilot / "frozen_programs.json").read_bytes())
            self.assertEqual(summary["cross_run_audit"]["retained_pairs"], 3)
            self.assertEqual(summary["reference_contexts"], 6)
            self.assertTrue(summary["all_schedules_feasible"])
            self.assertEqual(summary["selection_names"], {"weight": "weight", "weight_degree": "degree"})
            receipt = json.loads((output / "freeze_receipt.json").read_text(encoding="utf-8"))
            self.assertTrue(receipt["frozen_file_byte_identical_to_prior"])
            self.assertFalse(receipt["new_training_or_validation_selection"])
            self.assertTrue((output / "source_snapshot" / "cipheur" / "followup.py").is_file())
            result_receipt = json.loads((output / "result_receipt.json").read_text(encoding="utf-8"))
            self.assertIn("test_metrics.csv", result_receipt)
            self.assertIn("source_snapshot/cipheur/followup.py", result_receipt)
            with self.assertRaises(FileExistsError):
                run(pilot, output)


if __name__ == "__main__":
    unittest.main()
