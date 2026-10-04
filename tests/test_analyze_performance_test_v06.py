"""Small arithmetic/coverage fixtures only; no optimizer, AST, or live TEST input."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import analyze_performance_test_v06 as analysis


def row(context="p1-left", method="W0", reward="20", *, cohort="joint_W", seed=1,
        target=0.1, track="cold_Degree", population="fresh_toy", family="toy",
        wall=2.0, block=0):
    return {"id": context, "population": population, "family": family, "n": 4,
            "regime": "gap", "profile": "standard", "pair_id": context.split('-')[0] if population.startswith('fresh_') else None,
            "side": context.split('-')[-1], "source_cluster": context.split('-')[0],
            "target": target, "track": track, "method": method, "seed": seed,
            "analysis_cohort": cohort, "program_kind": "toy_frozen_kind", "program_role": "toy_frozen_role",
            "authoring_block": block, "authoring_arm": "witness", "program_sha256": "a" * 64,
            "published_winner_origin": None, "success": reward is not None, "returned": True,
            "status": "completed" if reward is not None else "unsupported", "error": None if reward is not None else {"type": "InputLimit"},
            "reward_exact": reward, "total_exact": "1000", "standalone_wall_seconds": wall,
            "standalone_cpu_seconds": 3.0, "native_wall_seconds": 1.5 if track == "warm_CHILS" else None,
            "native_cpu_seconds": 2.0 if track == "warm_CHILS" else None,
            "policy_wall_seconds": 0.5 if track == "warm_CHILS" else wall,
            "policy_cpu_seconds": 1.0 if track == "warm_CHILS" else 3.0,
            "shared_graph_load_wall_seconds": 0.25, "shared_graph_load_cpu_seconds": 0.125,
            "work": 9, "search_nodes": 4}


def audit_metadata():
    # This is a fabricated report for entry-guard tests, never an actual run audit.
    checks = dict(analysis.REQUIRED_AUDIT_CHECKS)
    checks.update(terminal_complete_original_batch=1,
                  complete_batch_exact_deployment_protocol_and_successful_exit=1,
                  terminal_status_count_reconstruction=1)
    return {"version": analysis.AUDIT_VERSION, "errors": 0, "error_details": [],
            "checks_by_kind": checks, "checks": sum(checks.values()),
            "audit_source_sha256": analysis.AUDITOR_SOURCE_SHA256,
            "independent_helper_sha256": dict(analysis.AUDIT_HELPER_SHA256)}


class PerformanceAnalysisTests(unittest.TestCase):
    def test_role_mean_retains_duplicate_asts_and_does_not_pick_best(self):
        rows = [row(method=f"W{i}", reward=str(v), block=i) for i, v in enumerate((10, 10, 10, 30))]
        analysis.validate_rows(rows, strict=False)
        result = analysis.context_estimates(rows)[0]
        self.assertEqual(result["complete_mean_reward_exact"], "15")
        self.assertEqual(result["requested_members"], 4)
        self.assertEqual(result["authoring_blocks"], [0, 1, 2, 3])
        self.assertEqual(len(result["member_identities"]), 4)

    def test_failed_native_seed_preserves_null_and_complete_group_requirement(self):
        rows = [row(method="CHILS", reward=v, track="native", seed=i)
                for i, v in enumerate(("10", None, "30"), 1)]
        analysis.validate_rows(rows, strict=False)
        result = analysis.context_estimates(rows)[0]
        self.assertIsNone(result["complete_mean_reward_exact"])
        self.assertEqual(result["available_mean_reward_exact"], "20")
        self.assertEqual((result["requested_members"], result["successful_members"]), (3, 2))
        self.assertEqual(result["status_counts"], {"completed": 2, "unsupported": 1})

    def test_fixed_reference_is_CHILS_seed1_not_seed_mean_or_best(self):
        rows = [row(method="CHILS", reward=str(v), track="native", seed=i)
                for i, v in enumerate((10, 20, 30), 1)]
        rows.append(row(reward="20"))
        records, _ = analysis.contrasts(analysis.context_estimates(rows), analysis.fixed_reference_estimates(rows), analysis.ClusterBootstrap(50))
        value = next(r for r in records if r["first"] == "joint_W" and r["contrast"] == "versus_fixed_full_CHILS_seed1")
        self.assertEqual(value["percent_gain_exact"], "100")

    def test_cluster_bootstrap_preserves_both_constraint_sides(self):
        units = [{"cluster": "pair:a", "value": "0"}, {"cluster": "pair:a", "value": "100"},
                 {"cluster": "pair:b", "value": "50"}, {"cluster": "pair:b", "value": "50"}]
        result = analysis.ClusterBootstrap().interval(units, "value", is_exact=True)
        self.assertEqual(result["mean_exact"], "50")
        self.assertEqual(result["ci95"], [50.0, 50.0])
        self.assertEqual(result["assigned_clusters"], 2)
        self.assertEqual(result["requested_bootstrap_replicates"], 2000)

    def test_bootstrap_keeps_all_assigned_missing_clusters(self):
        units = [{"cluster": "a", "value": None}, {"cluster": "b", "value": "7"}]
        result = analysis.ClusterBootstrap().interval(units, "value", is_exact=True)
        self.assertEqual(result["assigned_clusters"], 2)
        self.assertEqual(result["defined_clusters"], 1)
        self.assertEqual(result["mean_exact"], "7")
        self.assertLess(result["defined_bootstrap_replicates"], 2000)
        self.assertGreater(result["defined_bootstrap_replicates"], 0)

    def test_zero_missing_and_negative_percent_gains_are_explicit(self):
        self.assertIsNone(analysis.paired_percent("10", "0"))
        self.assertIsNone(analysis.paired_percent(None, "10"))
        self.assertEqual(analysis.paired_percent("5", "10"), "-50")

    def test_accelerated_and_standard_bootstrap_use_identical_cluster_draws(self):
        units = [{"cluster": "a", "value": None}, {"cluster": "a", "value": "3"},
                 {"cluster": "b", "value": "8"}, {"cluster": "b", "value": "10"}]
        accelerated = analysis.ClusterBootstrap().interval(units, 'value', is_exact=True)
        with patch.object(analysis, 'np', None):
            standard = analysis.ClusterBootstrap().interval(units, 'value', is_exact=True)
        self.assertEqual(accelerated, standard)
        self.assertEqual(standard['ci95'], [3.0, 9.0])

    def test_role_average_and_within_block_contrasts_are_distinct(self):
        rows = []
        for t in analysis.TARGETS:
            for block, w, r in ((0, 20, 10), (1, 2, 4)):
                rows += [row(method=f'W{block}', reward=str(w), cohort='quality_W', block=block, target=t),
                         row(method=f'R{block}', reward=str(r), cohort='quality_R', block=block, target=t)]
        result = analysis.analyze_rows(rows, strict=False, replicates=20)
        role = next(r for r in result['contrast_contexts'] if r['contrast'] == 'quality_W_minus_quality_R' and r['target'] == 0.1)
        self.assertEqual(role['percent_gain_exact'], '400/7')
        blocks = [r for r in result['identity_contrast_contexts'] if r['contrast'] == 'within_frozen_block:quality_W_minus_quality_R' and r['target'] == 0.1]
        self.assertEqual({r['authoring_block']: r['percent_gain_exact'] for r in blocks}, {0: '100', 1: '-50'})

    def test_standalone_warm_cost_not_amortized_across_policies(self):
        rows = [row(method=f"W{i}", track="warm_CHILS", wall=2.0, block=i) for i in range(4)]
        estimate = analysis.context_estimates(rows)[0]
        self.assertEqual(estimate["standalone_wall_seconds"], 2.0)
        self.assertEqual(estimate["native_wall_seconds"], 1.5)
        self.assertEqual(estimate["policy_wall_seconds"], 0.5)
        self.assertEqual(estimate["standalone_plus_graph_load_wall_seconds"], 2.25)
        self.assertEqual(estimate["standalone_cpu_seconds"], 3.0)

    def test_all_targets_remain_in_curves_even_when_every_reward_null(self):
        rows = [row(target=t, reward=None, wall=float(t) + 0.5) for t in analysis.TARGETS]
        result = analysis.analyze_rows(rows, strict=False, replicates=20)
        for curve in result["role_budget_curves"]:
            self.assertEqual([p["target"] for p in curve["points"]], [0.1, 1.0, 5.0])
            self.assertTrue(all(p["metrics"]["complete_mean_reward_exact"]["mean"] is None for p in curve["points"]))
        self.assertTrue(result["identity_budget_curves"])

    def test_family_and_exploratory_populations_do_not_pool_raw_rewards(self):
        rows = [row(context="source1", population=p, family=p, target=t)
                for p in ("WDP", "C3_interval_exploratory", "C3_legacy_exploratory") for t in analysis.TARGETS]
        # These are distinct source identities; a source can recur between separated C3 models.
        for r in rows:
            r["id"] = r["population"] + ":" + r["id"]
        result = analysis.analyze_rows(rows, strict=False, replicates=20)
        self.assertEqual({r["population"] for r in result["role_summaries"]}, {"WDP", "C3_interval_exploratory", "C3_legacy_exploratory"})
        self.assertTrue(all(r["family"] is not None for r in result["role_summaries"]))
        self.assertTrue(all("absolute_reward_difference_exact" not in r["metrics"] for r in result["contrast_summaries"] if r["family"] is None))

    def test_varying_status_counts_do_not_split_a_budget_curve(self):
        rows = [row(target=t, reward="9" if t != 1 else None) for t in analysis.TARGETS]
        result = analysis.analyze_rows(rows, strict=False, replicates=20)
        for curve in result["role_budget_curves"]:
            self.assertEqual(len(curve["points"]), 3)
            middle = curve["points"][1]
            self.assertEqual(middle["coverage"]["successful_members"], 0)
            self.assertEqual(middle["status_counts"], {"unsupported": 1})

    def test_audit_and_compact_bytes_gate_precede_analysis(self):
        with tempfile.TemporaryDirectory() as d:
            rows = Path(d) / 'audited_rows.jsonl'
            rows.write_text(json.dumps(row()) + '\n', encoding='utf-8')
            audit = Path(d) / 'audit.json'
            audit.write_text(json.dumps({'errors': 1, 'audited_rows_sha256': analysis.digest(rows)}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'audit has not passed'):
                analysis.load_audited_rows(audit, rows, analysis.digest(audit))
            audit.write_text(json.dumps({**audit_metadata(), 'audited_rows_sha256': '0' * 64}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'not bound'):
                analysis.load_audited_rows(audit, rows, analysis.digest(audit))

    def test_reviewed_audit_metadata_and_interrupted_disposition(self):
        report = audit_metadata()
        analysis.verify_audit_provenance(report, 'a' * 64, 'a' * 64)
        counts = report['checks_by_kind']
        for k in ('terminal_complete_original_batch',
                  'complete_batch_exact_deployment_protocol_and_successful_exit',
                  'terminal_status_count_reconstruction'):
            del counts[k]
        counts['incomplete_batch_guard_or_error_explicit'] = 1
        report['checks'] = sum(counts.values())
        # A final guarded frame remains analyzable with null measurements.
        analysis.verify_audit_provenance(report, 'a' * 64, 'a' * 64)

    def test_root_authorized_report_bytes_are_required(self):
        report = audit_metadata()
        for expected in (None, '', 'ABC', 'a' * 63, 'A' * 64):
            with self.assertRaisesRegex(ValueError, 'root-authorized'):
                analysis.verify_audit_provenance(report, 'a' * 64, expected)
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            analysis.verify_audit_provenance(report, 'b' * 64, 'a' * 64)

    def test_stale_missing_and_false_audit_provenance_rejected(self):
        mutations = [('version', None), ('version', 'old_audit'),
                     ('audit_source_sha256', '0' * 64), ('independent_helper_sha256', {}),
                     ('errors', False), ('error_details', [{'kind': 'hidden_error'}]),
                     ('error_details', None), ('checks', 0), ('checks', True),
                     ('checks_by_kind', {}), ('checks_by_kind', {'fake': 1})]
        for field, value in mutations:
            report = audit_metadata();report[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                analysis.verify_audit_provenance(report, 'a' * 64, 'a' * 64)

    def test_inconsistent_checks_and_absent_final_disposition_rejected(self):
        mutations = [lambda r: r.update(checks=r['checks'] + 1),
                     lambda r: r['checks_by_kind'].update(complete_preregistered_frame=True),
                     lambda r: r['checks_by_kind'].update(original_lossless_graph_bytes=1),
                     lambda r: r['checks_by_kind'].pop('terminal_complete_original_batch'),
                     lambda r: r['checks_by_kind'].update(incomplete_batch_guard_or_error_explicit=1),
                     lambda r: r['checks_by_kind'].pop('terminal_status_count_reconstruction')]
        for mutate in mutations:
            report = audit_metadata();mutate(report)
            if report['checks'] != sum(report['checks_by_kind'].values()) and report['checks'] != audit_metadata()['checks'] + 1:
                report['checks'] = sum(report['checks_by_kind'].values())
            with self.assertRaises(ValueError):
                analysis.verify_audit_provenance(report, 'a' * 64, 'a' * 64)

    def test_local_helper_change_cannot_use_claimed_old_source_hash(self):
        original_digest = analysis.digest
        helper = next(iter(analysis.AUDIT_HELPER_SHA256))
        def changed(path):
            return '0' * 64 if Path(path) == analysis.ROOT / helper else original_digest(path)
        with patch.object(analysis, 'digest', changed), self.assertRaisesRegex(ValueError, 'closure has changed'):
            analysis.verify_audit_provenance(audit_metadata(), 'a' * 64, 'a' * 64)

    def test_duplicates_infinities_and_error_diagnostic_rewards_rejected(self):
        a = row()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            analysis.validate_rows([a, deepcopy(a)], strict=False)
        a = row(wall=float('inf'))
        with self.assertRaisesRegex(ValueError, 'finite'):
            analysis.validate_rows([a], strict=False)
        a = row()
        a["success"] = False
        with self.assertRaisesRegex(ValueError, 'remain null'):
            analysis.validate_rows([a], strict=False)

    def test_incomplete_requested_matrix_rejected_by_production_gate(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete predeclared'):
            analysis.validate_rows([row()], strict=True)


if __name__ == '__main__':
    unittest.main()
