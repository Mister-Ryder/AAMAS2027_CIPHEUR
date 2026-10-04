"""Auditor preparation tests use constructed values, never EoH outcomes."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest

from scripts import verify_published_eoh_authoring_v06 as author
from scripts import verify_published_eoh_train_v06 as train


def row(identity, q, work, covered=True):
    return {"id": identity, "program": {"fabricated": identity}, "feedback": {
        "quality_covered": covered, "macro_quality_exact": q, "macro_work_exact": work}}


class IndependentEoHPreparationTests(unittest.TestCase):
    def test_official_scaled_double_even_rounding(self):
        for q, expected in (("123455/1000000", -0.12346), ("123445/1000000", -0.12344),
                            ("1/3", -0.33333), ("1", -1.0), ("0", 0.0)):
            self.assertEqual(author.objective(q), expected)

    def test_equal_objective_keeps_first_even_if_work_worse(self):
        a, b = row("seed", "1/2", "9999"), row("new", "1/2", "1")
        self.assertEqual([p["id"] for p in author.population([a, b])], ["seed"])
        self.assertEqual([p["id"] for p in author.population([b, a])], ["new"])

    def test_distinct_exact_quality_may_round_to_same_objective(self):
        a, b = row("seed", "1/2", "100"), row("subrounded_gain", "500001/1000000", "1")
        self.assertEqual([p["id"] for p in author.population([a, b])], ["seed"])

    def test_only_two_best_quality_objectives_no_work_tiebreak(self):
        rows = [row("middle", "3/5", "1"), row("worst", "1/5", "1"),
                row("best", "4/5", "9999"), row("failed", None, None, False)]
        self.assertEqual([p["id"] for p in author.population(rows)], ["best", "middle"])

    def test_parent_draw_is_reproducible_with_replacement(self):
        pop = author.population([row("seed", "1/2", "1")])
        self.assertEqual([p["id"] for p in author.draw(pop, 2, 0, 3, "fixture")], ["seed", "seed"])
        pop = author.population([row("a", "3/5", "1"), row("b", "1/2", "1")])
        self.assertEqual(author.draw(pop, 20, 1, 4, "fixture"), author.draw(pop, 20, 1, 4, "fixture"))

    def test_recursive_label_rejection_is_about_fields(self):
        self.assertTrue(author.label_free({"task": "ordinary graph structural reasoning", "quality": ["1/2"]}))
        self.assertFalse(author.label_free({"packet": [{"equality_joins": []}]}))

    def test_final_gate_refuses_before_reading_evolving_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "calls").mkdir()
            (base / "calls" / "do_not_open").write_text("unfrozen")
            with self.assertRaisesRegex(ValueError, "not frozen"):
                author.final_gate(base)

    def test_final_gate_requires_four_real_seed_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            s = {"version": "v06_published_EoH_DSL_TRAIN_quality_selection_001", "all32_positions_frozen": True,
                "TEST_accessed": False, "requested_positions": 32, "protocol_sha256": author.PROTO_SHA,
                "root_authoring_release_sha256": author.RELEASE_SHA, "programs": [None] * 4,
                "original_positions": [{"run": r, "slot": k, "id": f"run_{r}_slot_{k}"}
                    for r in range(4) for k in range(8)]}
            (base / "selection.json").write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError, "four original seed"):
                author.final_gate(base)

    def test_request_packet_recipe_has_no_information_gate(self):
        seed = {"program": {"rationale": "fixture"}}
        sf = {"quality_covered": True, "macro_quality_exact": "1/2", "macro_work_exact": "9"}
        pop = author.population([{"id": "run_0:warm_seed", "program": seed["program"], "feedback": sf}])
        p = {"training_states_sha256": "a" * 64}
        req = author.expected_request(0, 2, pop, seed, sf, {"task": "fixture"}, p, {"rng_salt": "fixture"})
        self.assertEqual(req["parents"], ["run_0:warm_seed", "run_0:warm_seed"])
        self.assertTrue(author.label_free(req["packet"]))

    def test_auditors_do_not_import_production_algorithms(self):
        for module in (author, train):
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            modules = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
            self.assertFalse(any(m and (m == "cipheur" or m.startswith("cipheur.")) for m in modules))


if __name__ == "__main__":
    unittest.main()
