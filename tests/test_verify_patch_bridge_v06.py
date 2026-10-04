"""Constructed verifier tests only; no frozen programme, TRAIN or TEST query."""
import copy
from fractions import Fraction
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from scripts import verify_patch_bridge_v06 as verify


def graph(weights, edges):
    return {"name": "constructed", "contacts": [{"id": v, "satellite": "s" + v,
        "station": "g" + v, "start": 0, "end": 1, "weight": w} for v, w in weights.items()],
        "edges": [list(e) for e in edges], "constraints": {}}


def state(source, patch):
    return {"id": "toy", "split": "train", "graph": source, "graph_sha256": verify.graph_digest(source),
        "patch": sorted(patch), "patch_status": "constructed", "outside_fixed": [],
        "snapshot_sha256": "toy_snapshot"}


def program(rule="weight", features=None):
    return {"name": "toy", "features": features or [], "rule": rule, "rationale": "constructed"}


def query(a="a", b="b"):
    return {"a": a, "b": b, "in_core_sha": True, "in_full_strict_bridge": False,
        "sample_rank": 0, "query_rank": 0, "competing": True, "full_reference_rows": []}


def config():
    return {"pairs_per_patch": 4, "salt": "TOY_ONLY", "recurrence_states_per_query": 10,
        "certificate_epsilon_exact": "1/100000000", "score_margin_exact": "1/1000000000",
        "max_score_feature_work": 200000}


def degree_scored_fixture():
    source = graph({"a": 2, "b": 1}, [("a", "b")]); s = state(source, ["a", "b"])
    entry = {"id": "degree", "role": "degree", "priority": "degree", "program": None}
    row = {"state_id": "toy", "program_id": "degree", "role": "degree", "patch_status": "constructed",
        "selection_performed": False, "status": "scored", "snapshot_sha256": "toy_snapshot",
        "scores": {"a": "2", "b": "1"}, "priority_order": ["a", "b"], "greedy_proposal": ["a"],
        "greedy_patch_weight_exact": "2", "local_fit": verify.expected_fit([], {}, Fraction(0)),
        "full_target_fit": verify.expected_fit([], {}, Fraction(0)), "score_margin_exact": "1/1000000000",
        "greedy_scope": "diagnostic priority-only proposal; not the kernel's retained best incumbent",
        "branch_scope": "fixed priority ordering only; no branch search or pivot-efficiency evaluation",
        "feature_meter": {"feature_work": 6, "feature_primitives": {}}, "cpu_seconds": 0.001, "wall_seconds": 0.002}
    return s, entry, row


class ExactScopeTests(unittest.TestCase):
    def test_clique_upper_rejects_missing_duplicate_and_nonclique(self):
        source = graph({"a": 8, "b": 7, "x": 10}, [("a", "b")])
        nodes, _, adj = verify.view(source)
        self.assertEqual(verify.clique_upper(nodes, adj, nodes, [["a", "b"], ["x"]]), 18)
        for cover in ([["a", "b"]], [["a", "b"], ["b", "x"]], [["a", "b", "x"]]):
            with self.assertRaises(ValueError):
                verify.clique_upper(nodes, adj, nodes, cover)

    def test_cancelled_components_and_scoped_forced_value(self):
        source = graph({"a": 4, "b": 3, "x": 7, "y": 6}, [("a", "b"), ("x", "y")])
        s = state(source, source_node_ids(source))
        q = query()
        saved = {**q, "lower_exact": "1", "upper_exact": "1", "preferred": "a", "status": "strict",
            "exact": True, "cancelled_components": [["x", "y"]], "unmatched": {"a": [], "b": []},
            "recurrence_states": 0, "epsilon_exact": "1/100000000", "query_state_limit": 10,
            "scope": verify.LOCAL, "outside_incumbent_weight_cancels": True}
        checks = verify.Checks()
        out = verify.check_local_label(s, q, saved, config(), checks, {})
        self.assertFalse(checks.errors)
        self.assertEqual(out["independent_difference_exact"], "1")
        bad = copy.deepcopy(saved); bad["cancelled_components"] = []
        checks = verify.Checks()
        verify.check_local_label(s, q, bad, config(), checks, {})
        self.assertTrue(checks.errors)

    def test_unknown_is_not_upgraded_after_stronger_verification(self):
        source = graph({"a": 2, "b": 2, "x": 6, "y": 9, "z": 6},
            [("a", "b"), ("b", "x"), ("b", "y"), ("b", "z"), ("x", "y"), ("y", "z")])
        s = state(source, source_node_ids(source)); q = query()
        # After forcing a, x-y-z remains; exact optimum12, greedy9, clique upper15.
        saved = {**q, "lower_exact": "9", "upper_exact": "15", "preferred": None, "status": "unknown",
            "exact": False, "cancelled_components": [], "unmatched": {"a": [{"vertices": ["x", "y", "z"],
                "bound": {"lower_exact": "9", "upper_exact": "15", "selected": ["y"], "exact": False,
                    "recurrence_states": 0, "state_limit": 0, "reason": "recurrence_limit_sound_clique_enclosure"}}], "b": []},
            "recurrence_states": 0, "epsilon_exact": "20", "query_state_limit": 10,
            "scope": verify.LOCAL, "outside_incumbent_weight_cancels": True}
        cfg = config(); cfg["certificate_epsilon_exact"] = "20"
        checks = verify.Checks(); out = verify.check_local_label(s, q, saved, cfg, checks, {})
        self.assertFalse(checks.errors)
        self.assertEqual(out["saved_status"], "unknown")
        self.assertEqual(out["independent_difference_exact"], "12")
        bad = copy.deepcopy(saved); bad["status"] = "strict"; bad["preferred"] = "a"
        checks = verify.Checks(); verify.check_local_label(s, q, bad, cfg, checks, {})
        self.assertTrue(checks.errors)

    def test_full_and_restricted_optima_can_reverse(self):
        source = graph({"a": 8, "b": 7, "x": 10, "y": 3}, [("a", "b"), ("a", "x"), ("b", "y")])
        nodes, _, adj = verify.view(source)
        def difference(region):
            return Fraction(8) + verify.alpha(nodes, adj, set(region) - {"a"} - adj["a"], {}, "g") - Fraction(7) - verify.alpha(nodes, adj, set(region) - {"b"} - adj["b"], {}, "g")
        self.assertEqual(difference(set(nodes)), -6)
        self.assertEqual(difference({"a", "b", "y"}), 4)


class PositionTests(unittest.TestCase):
    def test_lazy_rule_does_not_evaluate_unused_invalid_feature(self):
        source = graph({"a": 2, "b": 1}, [("a", "b")]); s = state(source, ["a", "b"])
        expression = {"op": "div", "args": [{"op": "const", "value": 1}, {"op": "const", "value": 0}]}
        entry = {"priority": "program", "program": program("weight if degree > 0 else boom", [{"name": "boom", "expression": expression}])}
        self.assertEqual(verify.score_independent(entry, s), {"a": Fraction(2), "b": Fraction(1)})

    def test_exact_fit_margin_preserves_ties_and_full_local_scope(self):
        scores = {"a": Fraction(8), "b": Fraction(7)}
        local = [{"a": "a", "b": "b", "preferred": "a", "scope": verify.LOCAL, "in_core_sha": True}]
        full = [{"a": "a", "b": "b", "preferred": "b", "scope": verify.FULL}]
        self.assertEqual(verify.expected_fit(local, scores, Fraction(0))["passed"], 1)
        self.assertEqual(verify.expected_fit(full, scores, Fraction(0))["passed"], 0)
        self.assertEqual(verify.expected_fit(local, scores, Fraction(1))["passed"], 0)
        self.assertTrue(verify.expected_fit(local, {"a": Fraction(7), "b": Fraction(7)}, Fraction(0))["rows"][0]["score_tie"])

    def test_missing_position_stays_null_not_zero_accuracy(self):
        s = state(graph({"a": 2}, []), ["a"])
        entry = {"id": "missing", "role": "fixed_base", "priority": "program", "program": None}
        row = {"state_id": "toy", "program_id": "missing", "role": "fixed_base", "patch_status": "constructed",
            "selection_performed": False, "status": "missing_program", "scores": None, "local_fit": None, "full_target_fit": None}
        checks = verify.Checks(); out = verify.check_score(entry, s, row, [], [], config(), checks)
        self.assertFalse(checks.errors); self.assertIsNone(out["actual_local_fit"])
        bad = {**row, "local_fit": {"passed": 0}}
        checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], config(), checks)
        self.assertTrue(checks.errors)

    def test_degree_direct_cost_rejects_corruption(self):
        s, entry, row = degree_scored_fixture()
        checks = verify.Checks(); verify.check_score(entry, s, row, [], [], config(), checks)
        self.assertFalse(checks.errors)
        bad = copy.deepcopy(row); bad["feature_meter"]["feature_work"] = 5
        checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], config(), checks)
        self.assertTrue(checks.errors)

    def test_executed_scored_position_requires_meter_and_both_times(self):
        s, entry, row = degree_scored_fixture()
        for key in ("feature_meter", "cpu_seconds", "wall_seconds"):
            for missing in (True, False):
                with self.subTest(key=key, omitted=missing):
                    bad = copy.deepcopy(row)
                    if missing: del bad[key]
                    else: bad[key] = None
                    checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], config(), checks)
                    self.assertTrue(checks.errors)

    def test_executed_cap_requires_meter_times_and_actual_first_crossing(self):
        s, entry, _ = degree_scored_fixture()
        cfg = config(); cfg["max_score_feature_work"] = 0
        row = {"state_id": "toy", "program_id": "degree", "role": "degree", "patch_status": "constructed",
            "selection_performed": False, "status": "score_work_cap", "scores": None,
            "local_fit": None, "full_target_fit": None, "error_type": "_FeatureLimit", "error": "toy cap",
            "partial_scores_not_predictions": {}, "feature_meter": {"feature_work": 3, "feature_primitives": {}},
            "cpu_seconds": 0.001, "wall_seconds": 0.002}
        checks = verify.Checks(); verify.check_score(entry, s, row, [], [], cfg, checks)
        self.assertFalse(checks.errors)
        for key in ("feature_meter", "cpu_seconds", "wall_seconds"):
            with self.subTest(omitted=key):
                bad = copy.deepcopy(row); del bad[key]
                checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], cfg, checks)
                self.assertTrue(checks.errors)
        # The reviewer's original row has no receipts at all; this cannot
        # discard a valid score from the observed denominator.
        bad = {k: v for k, v in row.items() if k not in ("feature_meter", "cpu_seconds", "wall_seconds")}
        checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], config(), checks)
        self.assertTrue(checks.errors)
        # Merely fabricating a charged crossing is impossible for Degree
        # when the whole exact direct loop would charge only6 units.
        bad = copy.deepcopy(row); bad["feature_meter"]["feature_work"] = 200001
        checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], config(), checks)
        self.assertTrue(checks.errors)

    def test_executed_error_allows_partial_meter_but_requires_receipts(self):
        s = state(graph({"a": 2}, []), ["a"])
        expression = {"op": "div", "args": [{"op": "const", "value": 1}, {"op": "const", "value": 0}]}
        entry = {"id": "error", "role": "fixed_base", "priority": "program",
            "program": program("boom", [{"name": "boom", "expression": expression}])}
        row = {"state_id": "toy", "program_id": "error", "role": "fixed_base", "patch_status": "constructed",
            "selection_performed": False, "status": "score_error", "scores": None, "local_fit": None,
            "full_target_fit": None, "partial_scores_not_predictions": {}, "error_type": "ValueError", "error": "toy division failure",
            "feature_meter": {"feature_work": 3, "feature_primitives": {"compile_node": 3}},
            "cpu_seconds": 0.001, "wall_seconds": 0.002}
        checks = verify.Checks(); verify.check_score(entry, s, row, [], [], config(), checks)
        self.assertFalse(checks.errors)
        for key in ("feature_meter", "cpu_seconds", "wall_seconds"):
            with self.subTest(omitted=key):
                bad = copy.deepcopy(row); del bad[key]
                checks = verify.Checks(); verify.check_score(entry, s, bad, [], [], config(), checks)
                self.assertTrue(checks.errors)

    def test_nonexecuted_missing_identity_cannot_fabricate_cost(self):
        s = state(graph({"a": 2}, []), ["a"])
        entry = {"id": "missing", "role": "fixed_base", "priority": "program", "program": None}
        row = {"state_id": "toy", "program_id": "missing", "role": "fixed_base", "patch_status": "constructed",
            "selection_performed": False, "status": "missing_program", "scores": None, "local_fit": None, "full_target_fit": None}
        for key, fabricated in (("cpu_seconds", 0), ("wall_seconds", 0), ("feature_meter", {"feature_work": 0, "feature_primitives": {}})):
            checks = verify.Checks(); verify.check_score(entry, s, {**row, key: fabricated}, [], [], config(), checks)
            self.assertTrue(checks.errors)

    def test_core_query_union_retains_added_label_and_shortfall(self):
        s = state(graph({"a": 1, "b": 1, "c": 1, "d": 1}, [("a", "b")]), ["a", "b", "c", "d"])
        core, quota = verify.query_union(s, [], config())
        extra = next(p for p in [("a", "b"), ("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"), ("c", "d")] if not any({r["a"], r["b"]} == set(p) for r in core))
        union, quota = verify.query_union(s, [{"a": extra[0], "b": extra[1], "original_row_index": 6}], config())
        self.assertEqual(len(union), 5); self.assertEqual(quota["added_original_full_pairs"], 1)
        self.assertFalse(union[-1]["in_core_sha"]); self.assertTrue(union[-1]["in_full_strict_bridge"])
        one = state(graph({"a": 1}, []), ["a"])
        union, quota = verify.query_union(one, [], config())
        self.assertEqual(union, []); self.assertEqual(quota["pair_shortfall"], 4)

    def test_archive_reader_rejects_duplicate_output_and_never_extracts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "toy.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                for prefix in ("a", "b"):
                    raw = b"{}"; member = tarfile.TarInfo(prefix + "/complete.json"); member.size = len(raw)
                    archive.addfile(member, io.BytesIO(raw))
            with self.assertRaises(ValueError): verify.members(path, ("complete.json",))
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_no_production_module_import(self):
        # Other tests legitimately import production modules. Only this
        # verifier's own fresh import is relevant to its isolation contract.
        code = ("import sys; from scripts import verify_patch_bridge_v06; "
            "assert not any(n == 'cipheur' or n.startswith('cipheur.') for n in sys.modules)")
        result = subprocess.run([sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


def source_node_ids(source):
    return [n["id"] for n in source["contacts"]]


if __name__ == "__main__":
    unittest.main()
