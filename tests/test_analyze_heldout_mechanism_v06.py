"""Constructed metadata/statistics checks; no heldout programme evaluation."""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts import analyze_heldout_mechanism_v06 as analysis


def query(preferred="a", passed=False, score_a=1, score_b=2):
    return {"a": "a", "b": "b", "preferred": preferred, "certificate_status": "strict",
        "lower_exact": "3" if preferred == "a" else "-9", "upper_exact": "7" if preferred == "a" else "-4",
        "passed": passed, "score_a": score_a, "score_b": score_b}


class GateAndMissingnessTests(unittest.TestCase):
    def test_final_audit_rejects_stale_incomplete_failed_and_boolean_checks(self):
        report = {"version": "v06_independent_R2_heldout_result_audit_001", "kind": "R2", "checks": 12,
            "errors": 0, "error_records": [], "archive_sha256": "archive", "audit_script_sha256": "source",
            "independent_helper_sha256": analysis.independent_helper_hashes(),
            "verified_identity_variant_count": 162, "requested_state_assignments": 11664,
            "production_scheduler_or_oracle_calls": 0, "programme_selection": False}
        analysis.validate_audit(report, "R2", "archive", "source")
        for field, value in (("checks", True), ("errors", 1), ("archive_sha256", "stale"),
            ("audit_script_sha256", "stale"), ("verified_identity_variant_count", 161),
            ("error_records", ["unresolved"])):
            with self.assertRaises(ValueError):
                analysis.validate_audit({**report, field: value}, "R2", "archive", "source")

    def test_audit_helper_closure_rejects_missing_stale_extra_or_changed_current_helper(self):
        report = {"version": "v06_independent_R2_heldout_result_audit_001", "kind": "R2", "checks": 1,
            "errors": 0, "error_records": [], "archive_sha256": "archive", "audit_script_sha256": "source",
            "independent_helper_sha256": analysis.independent_helper_hashes(),
            "verified_identity_variant_count": 162, "requested_state_assignments": 11664,
            "production_scheduler_or_oracle_calls": 0, "programme_selection": False}
        analysis.validate_audit(report, "R2", "archive", "source")
        for altered in (None, {}, {**report["independent_helper_sha256"], "unbound_helper.py": "extra"}):
            with self.assertRaises(ValueError):
                analysis.validate_audit({**report, "independent_helper_sha256": altered}, "R2", "archive", "source")
        changed = {**report["independent_helper_sha256"], analysis.INDEPENDENT_HELPERS[0]: "changed"}
        with self.assertRaises(ValueError):
            analysis.validate_audit({**report, "independent_helper_sha256": changed}, "R2", "archive", "source")
        # The reported current-source digest also becomes stale if a helper's
        # actual bytes change while the main auditor file remains unchanged.
        with patch.object(analysis, "independent_helper_hashes", return_value=changed):
            with self.assertRaises(ValueError):
                analysis.validate_audit(report, "R2", "archive", "source")

    def test_both_config_bytes_pinned_even_if_registration_booleans_unchanged(self):
        self.assertEqual(analysis.validate_analysis_configs(analysis.CONFIGS), analysis.CONFIG_SHA256)
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for index, original in enumerate(analysis.CONFIGS):
                path = Path(folder) / str(index)
                path.write_bytes(original.read_bytes()); paths.append(path)
            self.assertEqual(analysis.validate_analysis_configs(paths), analysis.CONFIG_SHA256)
            for index in range(2):
                original = paths[index].read_bytes()
                paths[index].write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "configuration byte hash changed"):
                    analysis.validate_analysis_configs(paths)
                # Config validation precedes even audit/archive file reads.
                with patch.object(analysis, "CONFIGS", tuple(paths)), patch.object(analysis.tarfile, "open") as opener:
                    with self.assertRaisesRegex(ValueError, "configuration byte hash changed"):
                        analysis.load_batch("not-an-archive", "not-an-audit", "R2")
                    opener.assert_not_called()
                paths[index].write_bytes(original)

    def test_incomplete_batch_refused_before_invalid_result_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root / "batch.tar.gz"; audit = root / "audit.json"
            terminal = {"execution_complete": False, "assigned": 162, "returned_assignments": 161,
                "requested_state_assignments": 11664, "selection_performed": False, "extra_oracle_calls": 0, "no_fallback": True}
            with tarfile.open(path, "w:gz") as tar:
                for name, raw in (("v06_R2_heldout_results_server_002/complete.json", json.dumps(terminal).encode()),
                    ("v06_R2_heldout_results_server_002/results.jsonl", b"DO NOT READ INVALID EVOLVING RESULTS")):
                    member = tarfile.TarInfo(name); member.size = len(raw); tar.addfile(member, io.BytesIO(raw))
            report = {"version": "v06_independent_R2_heldout_result_audit_001", "kind": "R2", "checks": 1,
                "errors": 0, "error_records": [], "archive_sha256": analysis.digest(path),
                "independent_helper_sha256": analysis.independent_helper_hashes(),
                "audit_script_sha256": analysis.digest(analysis.AUDITOR), "verified_identity_variant_count": 162,
                "requested_state_assignments": 11664, "production_scheduler_or_oracle_calls": 0, "programme_selection": False}
            audit.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                analysis.load_batch(path, audit, "R2")

    def test_conditional_statistic_never_turns_missing_into_zero(self):
        rows = [{"family": "f", "cluster": "s1", "value": 1}, {"family": "f", "cluster": "s2", "value": None}]
        summary = analysis.summarize(rows, "value", with_bootstrap=False)
        self.assertEqual(summary["conditional_mean"], 1)
        self.assertIsNone(summary["full_members_mean"])
        self.assertEqual(summary["missing_members"], 1)
        self.assertIsNone(analysis.summarize([], "value")["conditional_mean"])

    def test_cluster_bootstrap_keeps_two_constraint_sides_together(self):
        rows = [{"family": "f", "cluster": "pair1", "value": 0}, {"family": "f", "cluster": "pair1", "value": 1},
            {"family": "f", "cluster": "pair2", "value": 0}, {"family": "f", "cluster": "pair2", "value": 1}]
        summary = analysis.bootstrap_mean(rows, "value", replicates=32)
        self.assertEqual(summary["lower_95"], 0.5); self.assertEqual(summary["upper_95"], 0.5)
        self.assertEqual(summary["cluster_count"], 2)


class LossAndPairTests(unittest.TestCase):
    def test_signed_gap_bound_and_tiny_margin_failure_are_separate(self):
        self.assertEqual(analysis.query_losses(query())["hypothetical_pairwise_rank_choice_minimum_loss_exact"], "3")
        b = analysis.query_losses(query(preferred="b", score_a=2, score_b=1))
        self.assertEqual(b["certified_gap_min_exact"], "4")
        self.assertEqual(b["hypothetical_pairwise_rank_choice_minimum_loss_exact"], "4")
        tiny = analysis.query_losses(query(score_a="1000000001/1000000000", score_b=1))
        self.assertEqual(tiny["certified_gap_weighted_specification_violation_exact"], "3")
        self.assertEqual(tiny["hypothetical_pairwise_rank_choice_minimum_loss_exact"], "0")
        self.assertTrue(tiny["tiny_positive_margin_failure"])

    def test_tie_choice_is_id_order_and_unmeasured_loss_remains_null(self):
        tie = analysis.query_losses(query(preferred="b", score_a=1, score_b=1))
        self.assertTrue(tie["score_tie"]); self.assertEqual(tie["hypothetical_pairwise_rank_choice"], "a")
        self.assertEqual(tie["hypothetical_pairwise_rank_choice_minimum_loss_exact"], "4")
        missing = analysis.query_losses(query(passed=None, score_a=None, score_b=None))
        self.assertEqual(missing["certified_gap_min_exact"], "3")
        self.assertIsNone(missing["certified_gap_weighted_specification_violation_exact"])
        self.assertIsNone(missing["hypothetical_pairwise_rank_choice_minimum_loss_exact"])

    def test_mixed_family_unscaled_gap_is_diagnostic_and_per_family_loss_is_primary(self):
        rows = []
        for family in ("unit_public", "satellite"):
            row = {**query(), "family": family, "cluster": "source_" + family, "actual_base_alias": True}
            row.update(analysis.query_losses(row)); rows.append(row)
        with patch.object(analysis, "bootstrap_mean", return_value=None):
            mixed = analysis.query_summary(rows, [])
            single = analysis.query_summary(rows[:1], [])
        self.assertTrue(mixed["loss_aggregation_scope"]["mixed_family_diagnostic_only"])
        self.assertFalse(mixed["loss_aggregation_scope"]["primary_paper_loss_eligible"])
        self.assertEqual(mixed["hypothetical_pairwise_rank_choice_minimum_loss"]["conditional_mean"], 3)
        self.assertFalse(single["loss_aggregation_scope"]["mixed_family_diagnostic_only"])
        self.assertTrue(single["loss_aggregation_scope"]["primary_paper_loss_eligible"])

    def test_reversal_joint_correctness_requires_both_observed_sides(self):
        base = {"program_id": "p", "variant": "original", "pair": "pair", "query_index": 0,
            "cluster": "pair", "family": "f", "a": "a", "b": "b", "certificate_status": "strict"}
        rows = [{**base, "side": "left", "preferred": "a", "passed": True},
            {**base, "side": "right", "preferred": "b", "passed": False}]
        pair = analysis.paired_rows(rows)[0]
        self.assertEqual(pair["category"], "strict_reversal"); self.assertFalse(pair["pair_passed"])
        rows[1]["passed"] = None
        self.assertIsNone(analysis.paired_rows(rows)[0]["pair_passed"])
        with self.assertRaises(ValueError): analysis.paired_rows(rows + [rows[0]])
        bad = deepcopy(rows); bad[1]["b"] = "c"
        with self.assertRaises(ValueError): analysis.paired_rows(bad)

    def test_five_rename_cost_worst_and_missing_mean_are_explicit(self):
        values = dict(zip(analysis.VARIANTS, [7, 1, 2, 3, 4, 5]))
        self.assertEqual(analysis.robustness(values, "cost")["all5_worst"], 5)
        self.assertEqual(analysis.robustness(values, "fit")["all5_worst"], 1)
        values["relabel_4"] = None
        result = analysis.robustness(values, "fit")
        self.assertEqual(result["measured_relabels"], 4)
        self.assertIsNone(result["all5_mean"]); self.assertEqual(result["mean_of_observed_relabels"], 2.5)


class KernelReceiptTests(unittest.TestCase):
    def test_error_incumbent_is_diagnostic_only_while_normal_cap_counts(self):
        batch = {"kind": "R2", "records": [{"id": "state", "family": "f", "cluster": "source"}]}
        result = {"completed": False, "error": "programme error", "feasible": True, "incumbent_available": True,
            "budget_exhausted": False, "status": "program_error", "value_exact": "7", "initial_value_exact": "7",
            "meter": {"feature_work": 3, "repair_work": 4, "search_nodes": 0}, "cpu_seconds": 0.1, "wall_seconds": 0.2}
        assignment = {"id": "p", "variant": "original", "identity": {"missing_baseline": False},
            "kernel_rows": [{"id": "state", "result": result}]}
        row = analysis.compact_kernel(batch, assignment)[0]
        self.assertEqual(row["diagnostic_reward_exact"], "7")
        self.assertIsNone(row["normal_performance_reward_exact"]); self.assertIsNone(row["normal_total_work"])
        result.update(completed=True, error=None, budget_exhausted=True, status="time_budget")
        row = analysis.compact_kernel(batch, assignment)[0]
        self.assertTrue(row["normal_completed"]); self.assertTrue(row["normal_budget_stop"])
        self.assertEqual(row["normal_total_work"], 7)

    def test_complete_constructed_frame_retains_all31_and13392_positions(self):
        entries = []
        for block in range(4):
            entries.append({"id": f"joint{block}", "role": "proposed_witness_joint", "arm": "witness", "block": block})
            for arm in ("witness", "relations", "objective"):
                entries.append({"id": f"quality{block}{arm}", "role": "nonguarded_quality_comparator", "arm": arm, "block": block})
        entries += [{"id": f"control{i}", "role": "TRAIN_quality_only_control"} for i in range(2)]
        entries += [{"id": "fixed_degree", "role": "classical_Degree"}]
        entries += [{"id": f"fixed{i}", "role": "complete_relabel_control_bank"} for i in range(8)]
        published = [{"id": f"eoh{i}", "role": "nonguarded_published_quality_baseline", "winner_origin": "shared_R1_warm_seed"} for i in range(4)]
        for e in entries + published:
            e.update(program={"features": [], "rule": "weight"}, missing_baseline=False)
        records = [{"id": str(i), "family": "toy", "cluster": "single_toy_source", "paired": False} for i in range(72)]
        labels = [{"id": r["id"], "rows": []} for r in records]
        mappings = [{"variant": v, "mappings": {"single_toy_source": {}}} for v in analysis.VARIANTS[1:]]
        result = {"completed": True, "error": None, "feasible": True, "incumbent_available": True,
            "budget_exhausted": False, "status": "no_improvement", "value_exact": "7", "initial_value_exact": "7",
            "meter": {"feature_work": 3, "repair_work": 4, "search_nodes": 0}, "cpu_seconds": 0.1, "wall_seconds": 0.2}
        def batch(kind, es):
            rows = [{"id": e["id"], "identity": e, "variant": v, "assignment_status": "program_evaluated",
                "interface": {"query_checks": []}, "kernel_rows": [{"id": r["id"], "result": result} for r in records]}
                for e in es for v in analysis.VARIANTS]
            return {"kind": kind, "entries": es, "records": records, "labels": labels, "mappings": mappings, "rows": rows}
        actual_bootstrap = analysis.bootstrap_mean
        # Only constructed fixtures use two draws to test the plumbing;
        # production analysis remains fixed at2,000 registered replicates.
        with patch.object(analysis, "bootstrap_mean", side_effect=lambda rows, key: actual_bootstrap(rows, key, replicates=2)):
            out = analysis.analyze_batches([batch("R2", entries), batch("EoH", published)])
        self.assertEqual(out["frame"]["kernel_positions"], 13392)
        self.assertEqual(len(out["identities"]), 31)
        self.assertEqual(out["EoH_pipeline_origin_counts"], {"shared_R1_warm_seed": 4})
        self.assertEqual(len(out["dependent_duplicate_AST_groups"][0]["ids"]), 31)
        self.assertTrue(all(r["normal_paired_degree_percentage_gain"] == "0" for r in out["kernel_rows"]))


if __name__ == "__main__":
    unittest.main()
