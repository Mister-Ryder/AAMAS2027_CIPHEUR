"""Tiny semantic fixtures, never fresh benchmark/test instances."""
from fractions import Fraction
from hashlib import sha256
import itertools
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cipheur.advanced_study_v04 import (
    SOLVERS, _constructive, _local, _milp_result, _published, _verify,
    additional_programmes, context_task, normalise_contexts, run,
    solver_entries, summaries, validate_config,
)
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph


def fixture(weights=None):
    weights = weights or {"a": 8, "b": 5, "c": 6, "d": 2}
    return Graph("synthetic_runner_fixture", tuple(Contact(v, w, v, v, 0, 1)
                 for v, w in weights.items()), frozenset((("a", "b"), ("a", "c"))))


def optimum(graph, fixed=(), excluded=()):
    nodes = sorted(graph.available(fixed, excluded))
    return max(sum((Fraction(graph.nodes[v].weight) for v in tuple(fixed) + subset), Fraction(0))
        for size in range(len(nodes) + 1) for subset in itertools.combinations(nodes, size)
        if graph.feasible(tuple(fixed) + subset))


def configuration():
    return {"executables": {name: "/missing/synthetic-fixture-binary-" + name for name in SOLVERS},
            "program_cpu_seconds": 5, "local_search_seconds": 2, "milp_seconds": 10}


class AdvancedComparisonTests(unittest.TestCase):
    def test_additional_control_source_hash_and_identical_definition_required(self):
        programme = FeatureRuleProgram("prior_fixed", [], "weight").to_dict()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "legacy_freeze.json"
            payload = json.dumps({"programs": {"guided": programme}}).encode()
            source.write_bytes(payload)
            entry = {"id": "legacy_fixed", "program": programme,
                     "source_receipt": {"path": "legacy_freeze.json", "sha256": sha256(payload).hexdigest()}}
            config = {"additional_programmes": [entry]}
            controls, receipts, bytes_ = additional_programmes(config, temporary, {"guided": programme})
            self.assertEqual(controls["legacy_fixed"], programme)
            self.assertFalse(receipts["legacy_fixed"]["member_of_original_TRAIN_freeze"])
            self.assertTrue(receipts["legacy_fixed"]["identical_programme_in_source_checked"])
            self.assertEqual(bytes_["legacy_fixed"], payload)
            changed = FeatureRuleProgram("prior_fixed", [], "-weight").to_dict()
            with self.assertRaises(ValueError):
                additional_programmes({"additional_programmes": [{**entry, "program": changed}]}, temporary, {})
            with self.assertRaises(ValueError):
                additional_programmes({"additional_programmes": [{**entry, "source_receipt": {"path": "legacy_freeze.json", "sha256": "0" * 64}}]}, temporary, {})
            with self.assertRaises(ValueError):
                additional_programmes(config, temporary, {"legacy_fixed": programme})

    def test_same_ast_full_interface_trace_and_optional_chils_ils(self):
        graph = fixture()
        context = {"id": "fixture:graph", "pair_id": "fixture", "side": "graph", "split": "public",
                   "family": "synthetic_fixture", "cluster": "fixture", "graph": graph.to_dict(), "fixed": [], "excluded": []}
        programme = FeatureRuleProgram("conditional_cover", [{"name": "nc", "expression": {
            "op": "clique_cover_weight", "args": [{"op": "neighbors", "args": [{"op": "root", "args": []}]}]}}],
            "weight if remaining_count>2 else weight+nc").to_dict()
        config = {**configuration(), "full_interface_programme_ids": ["guided_v04"], "chils_ils_short": True}
        short = {"name": "short_5s", "official_seconds": 5, "hard_wall_seconds": 30}
        def official(g, exe, name, fixed, excluded, seconds, seed, hard_wall_seconds):
            return {"method": name, "seed": seed, "completed": False, "status": "synthetic_native_failure",
                    "returncode": -11, "stdout": "preserved", "selected": None, "value": None}
        with patch("cipheur.advanced_study_v04.run_solver", side_effect=official):
            result = context_task((context, config, {"guided_v04": programme}, short))
        self.assertEqual(len([r for r in result["methods"] if r["kind"] == "published"]), 15)
        self.assertEqual(result["method_summary"]["CHILS_ILS"]["seeds"], [1, 2, 3])
        self.assertEqual(result["method_summary"]["CHILS_ILS"]["primary_reward_mean_zero_accounted"], 0)
        full = next(r for r in result["methods"] if r["method"] == "guided_v04_full_interface")
        self.assertFalse(full["score_slice"])
        self.assertEqual(full["same_AST_as"], "guided_v04")
        self.assertTrue(result["full_interface_parity"]["guided_v04"]["trace_identical"])
        self.assertTrue(result["full_interface_parity"]["guided_v04"]["selection_identical"])
        long = {**short, "official_seconds": 30}
        self.assertEqual([n for n, _ in solver_entries(config, long)], list(SOLVERS))

    def test_saved_schemas_keep_boundaries_and_filter_only_declared_ids(self):
        graph = fixture()
        public = {"public": [{"id": "unit_fixture", "family": "DIMACS",
            "cluster": "original_source", "graph": graph.to_dict(), "fixed": ["d"], "excluded": ["c"]}]}
        contexts, total = normalise_contexts(public)
        self.assertEqual(total, 1)
        self.assertEqual(contexts[0]["id"], "unit_fixture:graph")
        self.assertEqual(contexts[0]["fixed"], ["d"])
        self.assertEqual(contexts[0]["excluded"], ["c"])
        pair = {"id": "pair", "family": "temporal", "left": graph.to_dict(), "right": graph.to_dict(),
                "fixed": ["d"], "excluded": ["c"], "source": {"seed": 123}}
        contexts, total = normalise_contexts({"test": [pair], "validation": []}, context_ids=["pair:right"])
        self.assertEqual(total, 2)
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0]["side"], "right")
        self.assertEqual(contexts[0]["cluster"], "123")
        for requested in (["pair:missing"], ["pair:right", "pair:right"]):
            with self.assertRaises(ValueError):
                normalise_contexts({"test": [pair]}, context_ids=requested)
        with self.assertRaises(ValueError):
            normalise_contexts({"test": [pair]}, splits=["train"])

    def test_original_fixed_excluded_verification_and_no_returned_fallback(self):
        graph = fixture()
        for selected in (["a"], ["a", "a", "d"], ["a", "c", "d"], ["b", "c", "d"]):
            with self.assertRaises(ValueError):
                _verify(graph, selected, ["d"], ["c"])
        program = FeatureRuleProgram("weight", [], "weight").to_dict()
        with patch("cipheur.advanced_study_v04.schedule_compiled", return_value={"selected": ["a", "a"]}):
            row = _constructive(graph, [], [], "frozen", program, "frozen_programme", 5)
        self.assertFalse(row["completed"])
        self.assertIsNone(row["selected"])
        self.assertFalse(row["fallback_used"])
        self.assertEqual(row["returned_result"]["selected"], ["a", "a"])
        row = _local(graph, [], [], [], 2)
        self.assertFalse(row["completed"])
        self.assertIsNone(row["selected"])
        self.assertEqual(row["status"], "no_completed_classical_initialization")

    def test_real_metis_encoding_failure_remains_explicit(self):
        graph = fixture({"a": .1, "b": .2, "c": .3, "d": .4})
        row = _published(graph, [], [], "M2WIS", "/missing/binary", 5, 1, 30)
        self.assertFalse(row["completed"])
        self.assertEqual(row["status"], "input_encoding_failure")
        self.assertIsNone(row["value"])
        self.assertIn("integer scaling", row["error"]["message"])

    def test_failed_native_output_preserved_and_mean_three_not_best_three(self):
        graph = fixture()
        raw = {"method": "M2WIS", "completed": False, "status": "Solver exit status -11",
               "returncode": -11, "stdout": "kernel0/fullyreduced", "stderr": "",
               "command": ["official_binary", "input.graph"], "raw_solution": None, "seconds": .02}
        with patch("cipheur.advanced_study_v04.run_solver", return_value=raw):
            row = _published(graph, [], [], "M2WIS", "/official/binary", 5, 3, 30)
        self.assertEqual(row["returncode"], -11)
        self.assertEqual(row["stdout"], "kernel0/fullyreduced")
        self.assertEqual(row["adapter_result"], raw)
        rows = [{"method": "M2WIS", "kind": "published", "seed": seed, "completed": True,
                 "value": value, "value_exact": str(value)} for seed, value in ((1, 10), (2, 13))] + [row]
        report = summaries(rows, "15")["M2WIS"]
        self.assertAlmostEqual(report["primary_reward_mean_zero_accounted"], 23 / 3)
        self.assertEqual(report["completed_only_reward_mean"], 11.5)
        self.assertEqual(report["completed_runs"], 2)
        self.assertEqual(report["requested_runs"], 3)
        self.assertEqual(report["seeds"], [1, 2, 3])

    def test_absent_highs_incumbent_not_replaced_with_fixed_boundary(self):
        graph = fixture()
        result = SimpleNamespace(status=1, message="time limit", x=None,
                                 mip_dual_bound=-13., mip_gap=float("inf"), mip_node_count=0)
        row = _milp_result(graph, ["d"], [], result, 10)
        self.assertFalse(row["completed"])
        self.assertEqual(row["status"], "no_solver_incumbent")
        self.assertIsNone(row["selected"])
        self.assertIsNone(row["value"])
        self.assertFalse(row["fallback_used"])
        self.assertEqual(row["numerical_upper"], 15)
        self.assertIsNone(row["mip_gap"])
        self.assertFalse(row["exact_optimum_claimed"])

    def test_context_formal_upper_encloses_exhaustive_optimum_and_dual_is_separate(self):
        graph = fixture()
        context = {"id": "fixture:graph", "pair_id": "fixture", "side": "graph",
            "split": "public", "family": "synthetic_semantic_fixture", "cluster": "fixture",
            "graph": graph.to_dict(), "fixed": [], "excluded": []}
        programme = FeatureRuleProgram("weight", [], "weight").to_dict()
        def official(g, exe, name, fixed, excluded, seconds, seed, hard_wall_seconds):
            if seed == 3:
                return {"method": name, "completed": False, "selected": None,
                        "value": None, "status": "native_timeout", "seconds": .01}
            return {"method": name, "completed": True, "selected": ["a", "d"] if seed == 1 else ["b", "c", "d"],
                    "value": -999, "feasible": True, "seconds": .01}
        numerical = {"method": "HiGHS_MILP", "kind": "numerical_reference", "completed": True,
            "selected": ["b", "c", "d"], "value": 13, "value_exact": "13", "feasible": True,
            "solver_status": 0, "numerical_upper": 13, "exact_optimum_claimed": False}
        with patch("cipheur.advanced_study_v04.run_solver", side_effect=official), patch("cipheur.advanced_study_v04._milp", return_value=numerical):
            result = context_task((context, configuration(), {"frozen": programme},
                                  {"name": "short_5s", "official_seconds": 5, "hard_wall_seconds": 30}))
        exact = optimum(graph)
        self.assertLessEqual(Fraction(result["reference"]["best_verified_lower_exact"]), exact)
        self.assertGreaterEqual(Fraction(result["reference"]["formal_upper_exact"]), exact)
        self.assertFalse(result["reference"]["independent_exact_proof"])
        self.assertFalse(result["reference"]["numerical_dual_is_formal_certificate"])
        self.assertEqual(result["reference"]["numerical_upper"], 13)
        self.assertEqual(len([r for r in result["methods"] if r["kind"] == "published"]), 12)
        for row in result["methods"]:
            if row["completed"]:
                self.assertLessEqual(Fraction(row["value_exact"]), exact)
        self.assertAlmostEqual(result["method_summary"]["CHILS"]["primary_reward_mean_zero_accounted"], 23 / 3)

    def test_fixed_protocol_and_executable_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            normalized, receipts = validate_config(configuration(), temporary)
            self.assertEqual(normalized["seeds"], [1, 2, 3])
            self.assertTrue(normalized["score_slice"])
            self.assertFalse(receipts["M2WIS"]["exists"])
            for field, value in (("official_seconds", 30), ("program_cpu_seconds", 6),
                                 ("score_slice", False), ("seeds", [1])):
                with self.assertRaises(ValueError):
                    validate_config({**configuration(), field: value}, temporary)
            with self.assertRaises(ValueError):
                validate_config({**configuration(), "long_budget": {"seconds": 30, "context_ids": []}}, temporary)

    def test_multiprocess_fixture_keeps_failed_runs_in_completion_receipt(self):
        graph = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data.json"; frozen = root / "frozen.json"; config = root / "config.json"
            data.write_text(json.dumps({"public": [{"id": "tiny_semantic_fixture", "family": "fixture",
                "graph": graph.to_dict()}]}), encoding="utf-8")
            programme = FeatureRuleProgram("weight", [], "weight").to_dict()
            frozen.write_text(json.dumps({"test_accessed": False, "selection_split": "train",
                                          "programs": {"synthetic_frozen": programme}}), encoding="utf-8")
            frozen_before = frozen.read_bytes()
            control_source = root / "prior_control_source.json"
            control_bytes = json.dumps({"candidates": [programme]}).encode()
            control_source.write_bytes(control_bytes)
            declared = {**configuration(), "chils_ils_short": True,
                "full_interface_programme_ids": ["synthetic_frozen"],
                "additional_programmes": [{"id": "prespecified_prior_control", "program": programme,
                    "source_receipt": {"path": "prior_control_source.json", "sha256": sha256(control_bytes).hexdigest()}}]}
            config.write_text(json.dumps(declared), encoding="utf-8")
            output = root / "run"
            run(data, frozen, config, output, workers=1)
            receipt = json.loads((output / "complete.json").read_text(encoding="utf-8"))
            row = json.loads((output / "results.jsonl").read_text(encoding="utf-8"))
            self.assertTrue(receipt["execution_complete"])
            self.assertFalse(receipt["all_requested_methods_completed"])
            self.assertEqual(receipt["phases"][0]["processed_contexts"], 1)
            self.assertEqual(len([r for r in row["methods"] if r["kind"] == "published" and not r["completed"]]), 15)
            control = next(r for r in row["methods"] if r["method"] == "prespecified_prior_control")
            self.assertEqual(control["kind"], "additional_prespecified_programme")
            self.assertTrue(row["full_interface_parity"]["synthetic_frozen"]["trace_identical"])
            self.assertEqual((output / "frozen_programs.json").read_bytes(), frozen_before)
            self.assertEqual(frozen.read_bytes(), frozen_before)
            self.assertEqual((output / "additional_source_0.json").read_bytes(), control_bytes)
            self.assertTrue((output / "context_plan.json").is_file())
            self.assertFalse(row["selection_permitted"])
            self.assertTrue(row["reference"]["coverage_edges_and_disjointness_checked"])
            with self.assertRaises(FileExistsError):
                run(data, frozen, config, output, workers=1)


if __name__ == "__main__":
    unittest.main()
