"""Fabricated graphs/transactions only: no native author, R2 response or TEST."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur import published_eoh_v06 as eoh
from cipheur.synthesis_study_v06 import canonical, digest, write
from scripts import author_published_eoh_cli_v06 as driver
from tests.test_heldout_mechanism_v06 import program, tiny_pair


def records_fixture():
    rs, _ = tiny_pair()
    keys = {"id", "split", "family", "cluster", "graph", "graph_digest", "fixed", "excluded"}
    return [{**{k: r[k] for k in keys}, "split": "train"} for r in rs]


def feedback(identity="run_0:warm_seed", q="1/2", work="999", slot=None, covered=True):
    return {"id": identity, "run": 0, "slot": slot, "operator": "seed" if slot is None else eoh.OPS[slot],
        "program_sha256": canonical(program()), "quality_covered": covered,
        "status": "quality_covered" if covered else "invalid_or_failed_original_attempt",
        "macro_quality_exact": q if covered else None, "macro_work_exact": work if covered else None,
        "family_quality": {"tiny": q} if covered else None, "family_work": {"tiny": work} if covered else None,
        "assigned_states": 120, "completed_feasible_states": 120 if covered else 0,
        "error_count": 0, "unexecuted_states": 0 if covered else 120}


def store_feedback(study, value):
    path = study / "fitness" / f"run_{value['run']}" / ("seed.json" if value["slot"] is None else f"slot_{value['slot']}.json")
    write(path, value); proto = eoh.read(study / "protocol.json")
    write(path.with_suffix(".receipt.json"), {"feedback_sha256": digest(path), "source_sha256": proto["source_sha256"],
        "protocol_sha256": digest(study / "protocol.json"), "training_states_sha256": proto["training_states_sha256"],
        "root_release_sha256": digest(study / "root_authoring_release.json"), "split": "train",
        "certificate_access": False, "TEST_accessed": False})


def fixture(base):
    root = Path(eoh.__file__).resolve().parents[1]
    for name, source in (("cfg.json", "configs/published_eoh_v06_001.json"),
                         ("kernel.json", "configs/repair_train_v06_001.json")):
        (base / name).write_bytes((root / source).read_bytes())
    records = []
    for i in range(60):
        pair = records_fixture()
        for r in pair:
            r["id"] = f"unit_{i}:" + r["id"]
        records.extend(pair)
    write(base / "inputs.json", {"records": records})
    write(base / "seed.json", {"program": program(), "program_sha256": canonical(program()),
        "source_candidate_id": "fabricated_R1_candidate", "TRAIN_label_selected_history": True,
        "R1_seed_selection_sha256": "a" * 64})
    write(base / "context.json", {"task": "Fabricated MWIS unit test only", "typed_grammar": eoh.grammar_contract(),
        "TRAIN_examples": records[:2]})
    write(base / "transport.json", {"requested_configuration": {"model": "fabricated_unit_model", "model_provider": "unit",
        "model_reasoning_effort": "unit", "model_reasoning_summary": None, "profile": None},
        "cli_executable_sha256": "0" * 64})
    study = base / "study"
    eoh.prepare(base / "cfg.json", base / "seed.json", base / "context.json", base / "inputs.json",
                base / "kernel.json", base / "transport.json", study)
    proto = eoh.read(study / "protocol.json")
    write(study / "root_authoring_release.json", {"version": "v06_published_EoH_root_authoring_release_001",
        "issued_by": "root", "allow_authoring": True, "protocol_sha256": digest(study / "protocol.json"),
        "freeze_receipt_sha256": digest(study / "freeze_receipt.json"),
        "shared_R1_warm_seed_sha256": canonical(program()), "R1_seed_selection_sha256": proto["R1_seed_selection_sha256"],
        "requested_positions": 32, "TEST_allowed": False})
    return study, digest(study / "root_authoring_release.json")


class PublishedEoHTests(unittest.TestCase):
    def test_equal_rounded_quality_collapses_population_without_work_tiebreak(self):
        pop = [{"id": "warm_seed", "program": program(), "feedback": feedback(work="999")},
               {"id": "new_better_work", "program": program("weight"),
                "feedback": feedback("new", q="500000001/1000000000", work="1")}]
        selected = eoh.population_management(pop)
        self.assertEqual([p["id"] for p in selected], ["warm_seed"])
        parents = eoh.parent_draw(selected, 2, 0, 2, "test")
        self.assertEqual([p["id"] for p in parents], ["warm_seed", "warm_seed"])
        self.assertEqual(eoh.parent_draw(selected, 2, 0, 2, "test"), parents)

    def test_original_operator_sequence_and_grammar_are_fixed(self):
        cfg = eoh.read(Path(eoh.__file__).resolve().parents[1] / "configs/published_eoh_v06_001.json")
        eoh.validate_config(cfg)
        bad = deepcopy(cfg); bad["operator_sequence"][-1] = "m1"
        with self.assertRaises(ValueError):
            eoh.validate_config(bad)
        eoh.reject_labels(eoh.grammar_contract())  # Legal set-difference primitive is not a certificate.
        self.assertEqual(cfg["grammar"]["max_added_features"], 6)

    def test_tiny_actual_kernel_is_certificate_free_and_reward_checked(self):
        records = records_fixture()
        kernel = eoh.read(Path(eoh.__file__).resolve().parents[1] / "configs/repair_train_v06_001.json")
        with patch("cipheur.synthesis_study_v06.assess_candidate", side_effect=AssertionError("No label assessor")):
            rows, summary = eoh.quality_assessment(program(), records, kernel, workers=1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(Fraction(summary["macro_quality_exact"]), Fraction(1, 2))
        self.assertTrue(all(Fraction(r["result"]["value_exact"]) == 4 for r in rows))
        records[0]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "TEST"):
            eoh.quality_assessment(program(), records, kernel, workers=1)
        with self.assertRaisesRegex(ValueError, "certified"):
            eoh.reject_labels({"family_work": {"certificate": "bad"}})

    def test_fabricated_prepare_and_release_are_required_before_native_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            study, release_sha = fixture(Path(temp))
            self.assertEqual(eoh.load_study(study, release_sha)["requested_positions"], 32)
            release = eoh.read(study / "root_authoring_release.json"); release["allow_authoring"] = False
            write(study / "root_authoring_release.json", release)
            with patch.object(driver.subprocess, "Popen", side_effect=AssertionError("Must not call native CLI")):
                with self.assertRaisesRegex(ValueError, "root-reviewed"):
                    driver.execute(study, "absent_request.json", digest(study / "root_authoring_release.json"))
            (study / "train_inputs.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "freeze changed"):
                eoh.load_study(study, release_sha)

    def test_request_requires_prior_real_quality_transaction_and_no_gate_feedback(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); study, release_sha = fixture(base)
            req = eoh.make_request(study, 0, None, base / "seed_request.json", release_sha)
            self.assertEqual(req["operator"], "seed")
            with self.assertRaises(FileNotFoundError):
                eoh.make_request(study, 0, 0, base / "first.json", release_sha)
            store_feedback(study, feedback())
            first = eoh.make_request(study, 0, 0, base / "first.json", release_sha)
            self.assertEqual(first["operator"], "i1"); eoh.reject_labels(first["packet"])
            with self.assertRaises(FileNotFoundError):
                eoh.make_request(study, 0, 1, base / "second.json", release_sha)
            bad = feedback(); bad["strict_fit"] = 1
            store_feedback(study, bad)
            with self.assertRaisesRegex(ValueError, "fitness changed|certified"):
                eoh.make_request(study, 0, 0, base / "must_reject.json", release_sha)

    def test_ingest_validates_server_byte_binding_and_rejects_injected_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); study, release_sha = fixture(base)
            req_path = base / "seed_request.json"; req = eoh.make_request(study, 0, None, req_path, release_sha)
            result = base / "fake_server"; write(result / "assessment.json", {"fabricated_receipt_only": True})
            write(result / "feedback.json", feedback())
            proto = eoh.read(study / "protocol.json")
            execution = {"request_sha256": digest(req_path), "root_release_sha256": release_sha,
                "protocol_sha256": digest(study / "protocol.json"), "training_states_sha256": proto["training_states_sha256"],
                "source_sha256": proto["source_sha256"], "feedback_sha256": digest(result / "feedback.json"),
                "assessment_sha256": digest(result / "assessment.json"), "split": "train", "TEST_accessed": False,
                "certificate_access": False}
            write(result / "execution.json", execution)
            with self.assertRaisesRegex(ValueError, "binding"):
                eoh.ingest(study, req_path, result, "f" * 64, release_sha)
            imported = eoh.ingest(study, req_path, result, execution["feedback_sha256"], release_sha)
            self.assertTrue(imported["no_conditional_feedback"])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                eoh.ingest(study, req_path, result, execution["feedback_sha256"], release_sha)

    def test_invalid_original_attempt_has_absent_measurements_and_no_search(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); study, release_sha = fixture(base)
            store_feedback(study, feedback())
            req_path = base / "request.json"; req = eoh.make_request(study, 0, 0, req_path, release_sha)
            calls = study / "calls" / req["id"]; calls.mkdir(parents=True)
            for name, raw in (("response.json", b"malformed original output"), ("events.jsonl", b""),
                              ("stderr.txt", b""), ("input.txt", b"unit prompt")):
                (calls / name).write_bytes(raw)
            (calls / "request.json").write_bytes(req_path.read_bytes())
            transport = eoh.read(study / "transport_binding.json")
            write(calls / "receipt.json", {"id": req["id"], "run": 0, "slot": 0, "operator": "i1",
                "request_sha256": digest(req_path), "response_sha256": digest(calls / "response.json"),
                "raw_event_sha256": digest(calls / "events.jsonl"), "raw_stderr_sha256": digest(calls / "stderr.txt"),
                "wrapper_sha256": digest(calls / "input.txt"), "no_retry": True, "exit_code": 0, "timed_out": False,
                "root_release_sha256": release_sha, "requested_configuration": transport["requested_configuration"],
                "cli_executable_sha256": transport["cli_executable_sha256"], "no_candidate_assessment": True,
                "TEST_accessed": False})
            with patch.object(eoh.platform, "system", return_value="Linux"), \
                 patch.object(eoh, "quality_assessment", side_effect=AssertionError("Invalid cannot search")):
                observed = eoh.evaluate(study, req_path, base / "evaluation", release_sha, calls)
            self.assertFalse(observed["quality_covered"])
            self.assertIsNone(observed["macro_quality_exact"])
            self.assertIsNone(observed["macro_work_exact"])
            self.assertEqual(observed["unexecuted_states"], 120)
            self.assertEqual(observed["error_count"], 0)

    def test_final_seed_incumbents_are_explicit_and_failed_runs_stay_null(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); study, release_sha = fixture(base)
            for run in range(4):
                seed_fb = {**feedback(covered=run != 3), "run": run, "id": f"run_{run}:warm_seed"}
                store_feedback(study, seed_fb)
                if run == 3:
                    continue
                for slot in range(8):
                    stem = f"run_{run}_slot_{slot}"
                    store_feedback(study, {**feedback(stem, slot=slot), "run": run})
                    write(study / "calls" / stem / "response.json", program())
                    write(study / "calls" / stem / "receipt.json", {"response_sha256": digest(study / "calls" / stem / "response.json"),
                        "exit_code": 0, "fabricated_unit_receipt": True})
            selected_path = base / "selection.json"
            eoh.finish(study, selected_path, release_sha)
            selected = eoh.read(selected_path)
            self.assertEqual(len(selected["original_positions"]), 32)
            self.assertEqual(len(selected["programs"]), 4)
            self.assertTrue(all(p["winner_origin"] == "shared_R1_warm_seed" for p in selected["programs"][:3]))
            self.assertIsNone(selected["programs"][3]["program"])
            self.assertEqual(selected["programs"][3]["winner_origin"], "missing")
            self.assertEqual(selected["native_CLI_spawned_attempts"], 24)
            self.assertFalse(selected["TEST_accessed"])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                eoh.finish(study, selected_path, release_sha)

    def test_full_train_contract_rejects_test_or_certificate_fields(self):
        records = []
        for i in range(60):
            for r in records_fixture():
                r["id"] = f"{i}:" + r["id"]; records.append(r)
        eoh.validate_records(records)
        bad = deepcopy(records); bad[0]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "TRAIN-only"):
            eoh.validate_records(bad)
        bad = deepcopy(records); bad[0]["queries"] = []
        with self.assertRaisesRegex(ValueError, "certified"):
            eoh.validate_records(bad)


if __name__ == "__main__":
    unittest.main()
