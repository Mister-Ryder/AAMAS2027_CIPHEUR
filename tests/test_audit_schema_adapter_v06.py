"""Frozen-consumer schema compatibility without modifying independent evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.normalize_audit_receipt_v06 import digest, normalize


class AuditSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.original = Path(self.temp.name) / "independent.json"
        self.output = Path(self.temp.name) / "adapted.json"
        self.report = {"version": "toy_independent", "checks": {"arithmetic": 4, "source": 2},
                       "total_checks": 6, "errors": [], "error_count": 0,
                       "selection_sha256": "retained", "ready_for_TEST": True,
                       "proposed_witness_joint_count": 4, "scope": ["original"]}

    def write_original(self):
        self.original.write_text(json.dumps(self.report), encoding="utf-8")
        return digest(self.original)

    def test_original_bytes_and_every_noncount_finding_survive(self):
        expected = self.write_original()
        raw = self.original.read_bytes()
        result = normalize(self.original, expected, self.output)
        adapted = json.loads(self.output.read_bytes())
        self.assertEqual(self.original.read_bytes(), raw)
        self.assertEqual((adapted["checks"], adapted["errors"]), (6, 0))
        self.assertEqual(adapted["original_check_categories"], self.report["checks"])
        self.assertEqual(adapted["original_error_records"], self.report["errors"])
        for key in self.report:
            if key not in ("checks", "errors"):
                self.assertEqual(adapted[key], self.report[key])
        self.assertEqual(result["new_checks_performed"], 0)
        self.assertEqual(adapted["schema_adapter"]["original_report_sha256"], expected)

    def test_failed_audit_is_not_turned_into_a_pass(self):
        self.report.update(errors=[{"kind": "incorrect_bound"}], error_count=1)
        with self.assertRaises(ValueError):
            normalize(self.original, self.write_original(), self.output)
        self.assertFalse(self.output.exists())

    def test_inconsistent_or_boolean_count_is_rejected(self):
        for counts, total in (({"a": 2}, 3), ({"a": True}, 1), ({"a": -1}, -1),
                              ({"a": 1}, True)):
            self.report.update(checks=counts, total_checks=total)
            with self.assertRaises(ValueError):
                normalize(self.original, self.write_original(), self.output)
            self.assertFalse(self.output.exists())

    def test_wrong_binding_and_overwrite_are_rejected(self):
        expected = self.write_original()
        with self.assertRaises(ValueError):
            normalize(self.original, "0" * 64, self.output)
        normalize(self.original, expected, self.output)
        raw = self.output.read_bytes()
        with self.assertRaises(ValueError):
            normalize(self.original, expected, self.output)
        self.assertEqual(self.output.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
