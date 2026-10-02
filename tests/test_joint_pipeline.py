"""Autonomous joint-loop checks on tiny synthetic development data only."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cipheur.experiment_data import diagnostic_pair
from cipheur.experiments import serialize_pair
from cipheur.graph_features import FeatureRuleProgram, schedule_feature_program
from cipheur.joint_pipeline import run
from cipheur.oracle import Budget, certify_pair
from cipheur.providers import ProviderError


REPAIR = json.loads((Path(__file__).resolve().parents[1] /
                     "examples" / "joint_neighbor_repair.json").read_text(encoding="utf-8"))
REPLAY_METADATA = {"backend": "replay", "live_llm": False}


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def make_prepared(directory):
    prepared = directory / "prepared"
    prepared.mkdir()
    train = diagnostic_pair("train", 0, "reversal")
    validation = diagnostic_pair("validation", 0, "reversal")
    spec, _ = certify_pair(train["left"], train["right"], train["a"], train["b"], Budget(),
                           train["fixed"], train["excluded"], include_preservation=True)
    spec.update(id=train["id"], family="diagnostic")
    save(prepared / "config.json", {"selection": {"min_spec_fraction": 0.75, "cost_penalty": 0.002},
                                    "reference_max_nodes": 10000})
    save(prepared / "train_specifications.json", [spec])
    save(prepared / "training_request.json", {"system": "Joint synthesis from training evidence.",
                                               "user": {"training_marker": "TRAIN_ONLY"}})
    save(prepared / "data.json", {"train": [serialize_pair(train)],
                                   "validation": [serialize_pair(validation)],
                                   "test": {"forbidden": "TEST_SECRET_NEVER_INSPECT"}})
    (prepared / "test_metrics.json").write_text("INVALID_TEST_METRICS_NEVER_READ", encoding="utf-8")
    return prepared, validation


class JointPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.prepared, self.validation = make_prepared(self.directory)

    def tearDown(self):
        self.temporary.cleanup()

    def config(self, rounds=1):
        return {"rounds": rounds, "provider": {"type": "replay", "path": "mocked.json"}}

    def test_real_replay_end_to_end_exports_frozen_acyclic_program_and_receipt(self):
        candidate = self.directory / "repair.json"
        save(candidate, REPAIR)
        result = run(self.prepared, {"rounds": 1, "provider": {
            "type": "replay", "path": str(candidate), "authoring_source": "current_assistant"}},
            self.directory / "joint")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["representation_repaired"])
        self.assertEqual(result["automated_llm_calls"], 0)
        self.assertEqual(result["replay_calls"], 1)
        self.assertFalse(result["test_data_accessed"])
        root = self.directory / "joint"
        self.assertTrue(json.loads((root / "initial_assessment.json").read_text())["contradictory"])
        self.assertTrue(json.loads((root / "selected_assessment.json").read_text())["rankings"]["all_passed"])
        frozen = FeatureRuleProgram.from_dict(json.loads((root / "selected_program.json").read_text()))
        with patch("cipheur.oracle.solve", side_effect=AssertionError("Deployment oracle call")), \
             patch("cipheur.providers.generate_candidate", side_effect=AssertionError("Deployment LLM call")):
            scheduled = schedule_feature_program(self.validation["left"], frozen,
                                                self.validation["fixed"], self.validation["excluded"])
        self.assertTrue(scheduled["feasible"])
        receipt = json.loads((root / "freeze_receipt.json").read_text())
        self.assertEqual(receipt["used_splits"], ["train", "validation"])
        self.assertIn("round_000/provider_receipt.json", receipt["artifact_sha256"])
        self.assertIn("joint_pipeline.py", receipt["source_sha256"])
        self.assertNotIn("TEST_SECRET", (root / "development_data.json").read_text())
        self.assertNotIn("TEST_SECRET", (root / "round_000" / "request.json").read_text())

    def test_invalid_candidate_is_saved_and_next_round_receives_repair_feedback(self):
        bad = {**REPAIR, "rule": "__import__('os')"}
        with patch("cipheur.joint_pipeline.generate_feature_candidate", side_effect=[
                (bad, REPLAY_METADATA), (REPAIR, REPLAY_METADATA)]) as generated:
            result = run(self.prepared, self.config(2), self.directory / "joint")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["candidate_rejections"], 1)
        previous = json.loads(generated.call_args_list[1].args[1]["user"])["previous_attempts"]
        self.assertFalse(previous[0]["accepted"])
        self.assertEqual(previous[0]["reason"], "candidate_evaluation_failure")
        self.assertTrue((self.directory / "joint" / "round_000" / "candidate_response.json").exists())

    def test_provider_failure_is_recorded_and_does_not_abort_configured_repair_round(self):
        with patch("cipheur.joint_pipeline.generate_feature_candidate", side_effect=[
                ProviderError("Mock transport failed."), (REPAIR, REPLAY_METADATA)]) as generated:
            result = run(self.prepared, self.config(2), self.directory / "joint")
        self.assertEqual(result["provider_failures"], 1)
        self.assertEqual(result["status"], "completed")
        previous = json.loads(generated.call_args_list[1].args[1]["user"])["previous_attempts"]
        self.assertEqual(previous[0]["reason"], "provider_or_typed_validation_failure")

    def test_unchanged_contradictory_representation_cannot_replace_initial(self):
        contradictory = {"name": "rule_only", "features": [], "rule": "weight - conflict_weight",
                         "rationale": "Cannot distinguish the aliased actions."}
        with patch("cipheur.joint_pipeline.generate_feature_candidate", return_value=(contradictory, REPLAY_METADATA)):
            result = run(self.prepared, self.config(), self.directory / "joint")
        self.assertEqual(result["status"], "no_eligible_candidate")
        self.assertFalse(result["selected_is_eligible"])
        self.assertFalse(result["representation_repaired"])
        self.assertEqual(result["selected"], "initial_weight")
        event = json.loads((self.directory / "joint" / "events.json").read_text())[0]
        self.assertEqual(event["reason"], "representation_contradiction")

    def test_acyclic_but_incorrect_rankings_are_rejected_at_specification_threshold(self):
        bad_rule = {**REPAIR, "name": "wrong_direction", "rule": "-neighbor_min"}
        with patch("cipheur.joint_pipeline.generate_feature_candidate", return_value=(bad_rule, REPLAY_METADATA)):
            result = run(self.prepared, self.config(), self.directory / "joint")
        self.assertEqual(result["status"], "no_eligible_candidate")
        event = json.loads((self.directory / "joint" / "events.json").read_text())[0]
        self.assertFalse(event["contradictory"])
        self.assertEqual(event["reason"], "specification_threshold_not_met")

    def test_cost_penalty_rejects_more_work_without_quality_improvement(self):
        expensive = copy.deepcopy(REPAIR)
        expensive["name"] = "extra_unused_feature"
        expensive["features"].append({"name": "unused_constant", "expression": {"op": "const", "value": 1}})
        with patch("cipheur.joint_pipeline.generate_feature_candidate", side_effect=[
                (REPAIR, REPLAY_METADATA), (expensive, REPLAY_METADATA)]):
            result = run(self.prepared, self.config(2), self.directory / "joint")
        self.assertEqual(result["selected"], REPAIR["name"])
        assessments = json.loads((self.directory / "joint" / "candidate_assessments.json").read_text())
        self.assertEqual(assessments[1]["quality"], assessments[2]["quality"])
        self.assertGreater(assessments[2]["feature_work"], assessments[1]["feature_work"])
        self.assertLess(assessments[2]["utility"], assessments[1]["utility"])

    def test_validation_reference_solves_are_cached_between_candidates(self):
        from cipheur.experiments import solve
        with patch("cipheur.experiments.solve", wraps=solve) as reference, \
             patch("cipheur.joint_pipeline.generate_feature_candidate", side_effect=[
                 (REPAIR, REPLAY_METADATA), (REPAIR, REPLAY_METADATA)]):
            run(self.prepared, self.config(2), self.directory / "joint")
        self.assertEqual(reference.call_count, 2)

    def test_http_attempt_budget_prevents_calls_and_counts_only_successful_http_receipts(self):
        config = {"rounds": 1, "provider": {"type": "openai_responses", "model": "mock-model"},
                  "provider_budget": {"max_http_attempts": 0}}
        with patch("cipheur.joint_pipeline.generate_feature_candidate") as generated:
            result = run(self.prepared, config, self.directory / "no_http")
        generated.assert_not_called()
        self.assertEqual(result["stop_reason"], "http_attempt_budget_exhausted")
        self.assertEqual(result["automated_llm_calls"], 0)
        config["provider_budget"]["max_http_attempts"] = 1
        config["rounds"] = 2
        with patch("cipheur.joint_pipeline.generate_feature_candidate", return_value=(
                REPAIR, {"backend": "openai_responses", "live_llm": True})) as generated:
            result = run(self.prepared, config, self.directory / "one_mock_http")
        self.assertEqual(generated.call_count, 1)
        self.assertEqual(result["http_generation_attempts"], 1)
        self.assertEqual(result["automated_llm_calls"], 1)

    def test_provider_sequence_can_switch_after_failure_and_command_is_counted_separately(self):
        config = {"rounds": 3, "providers": [{"type": "replay", "path": "bad.json"},
                                               {"type": "command", "argv": ["mock-command"]}]}
        with patch("cipheur.joint_pipeline.generate_feature_candidate", side_effect=[
                ProviderError("Mock replay failure"), (REPAIR, {"backend": "external_command", "live_llm": True})]):
            result = run(self.prepared, config, self.directory / "sequence")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["automated_llm_calls"], 0)
        self.assertEqual(result["external_llm_commands"], 1)
        self.assertEqual(result["stop_reason"], "configured_provider_sequence_complete")

    def test_wall_time_budget_and_fresh_directory_rule(self):
        config = {**self.config(), "provider_budget": {"max_seconds": 1e-12}}
        with patch("cipheur.joint_pipeline.generate_feature_candidate") as generated:
            result = run(self.prepared, config, self.directory / "timed")
        generated.assert_not_called()
        self.assertEqual(result["stop_reason"], "wall_time_budget_exhausted")
        with self.assertRaises(ValueError):
            run(self.prepared, config, self.directory / "timed")

    def test_cli_with_config_relative_replay_path_runs(self):
        save(self.directory / "repair.json", REPAIR)
        config = self.directory / "config.json"
        save(config, {"rounds": 1, "provider": {"type": "replay", "path": "repair.json"}})
        result = subprocess.run([sys.executable, "-m", "cipheur.joint_pipeline", "--prepared-run", str(self.prepared),
                                 "--config", str(config), "--output", str(self.directory / "cli")],
                                capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
