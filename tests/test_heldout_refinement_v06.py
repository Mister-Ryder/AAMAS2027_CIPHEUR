"""R2 adapter tests use fabricated graphs/metadata only, never real TEST labels."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur import heldout_mechanism_v06 as original
from cipheur import heldout_refinement_v06 as r2
from cipheur.graph_features import FeatureRuleProgram
from cipheur.synthesis_study_v06 import ARMS, canonical, digest, write
from tests.test_heldout_mechanism_v06 import program, tiny_pair


ROOT = Path(r2.__file__).parent.parent


def selection_fixture(missing=()):
    raw, blocks = program(), [0, 1, 2, 3]
    joint, quality = [], []
    for b in blocks:
        source = f"block_{b}_witness:0"
        joint.append({"id": "joint|" + source, "source_candidate_id": source, "block": b,
            "arm": "witness", "slot": 0, "program": raw, "program_sha256": canonical(raw),
            "eligible": True, "role": "proposed_witness_joint", "joint_gate_required": True})
        for a in ARMS:
            absent = (b, a) in missing
            source = None if absent else f"block_{b}_{a}:0"
            quality.append({"id": "quality|" + (source or f"block_{b}_{a}:missing"),
                "source_candidate_id": source, "block": b, "arm": a, "slot": None if absent else 0,
                "program": None if absent else raw, "program_sha256": None if absent else canonical(raw),
                "eligible": False, "role": "nonguarded_quality_comparator",
                "joint_gate_required": False, "missing_baseline": absent})
    return {"version": "v06_R2_joint_and_quality_roles_TRAIN_selection_002", "selection_split": "train",
        "test_accessed": False, "all120_original_slots_assessed": True, "no_fallback": True,
        "R1_barrier_remains_failed": True, "ready_for_TEST": True, "proposed_witness_joint_count": 4,
        "quality_comparator_requested_count": 12, "selection_plan_sha256": r2.SELECTION_PLAN_SHA256,
        "matched_transport_complete_blocks": blocks, "programs": joint + quality,
        "quality_comparator_missing_cells": [{"block": b, "arm": a} for b, a in missing]}


def release_fixture(selection, bindings):
    return {"version": "v06_R2_root_TEST_release_002", "issued_by": "root", "allow_TEST": True,
        "before_any_TEST_labels_or_performance": True, "all15_R2_requests_frozen_before_assessment": True,
        "all120_original_slots_assessed": True, "independent_R2_TRAIN_audit_zero_errors": True,
        "authoring_completion_verified": True, "proposed_witness_joint_count": 4,
        "R1_barrier_remains_failed": True,
        "matched_transport_complete_blocks": selection["matched_transport_complete_blocks"],
        "original_runtime_sha256": r2.ORIGINAL_RUNTIME_SHA256,
        "R2_heldout_source_sha256": r2.source_hashes(), **bindings}


def synthetic_registration_files(base, missing=()):
    """Construct a full 72-state fixture; static configs are the only real reads."""
    plan, certs, study, assessed, controls = (base / n for n in ("plan", "certs", "study", "assessed", "controls"))
    records, labels = [], []
    for i in range(36):
        rs, ls = tiny_pair(numeric=True)
        for rec, lab in zip(rs, ls):
            rec["id"] = lab["id"] = f"unit_fixture_{i}:{rec['side']}"
            rec["cluster"] = lab["cluster"] = rec["pair"] = f"unit_fixture_{i}"
        records.extend(rs); labels.extend(ls)
    write(plan / "data.json", {"records": records})
    write(plan / "protocol.json", {"fabricated_inputs_only": True})
    write(plan / "freeze_receipt.json", {"data_sha256": digest(plan / "data.json"),
        "protocol_sha256": digest(plan / "protocol.json"), "before_any_oracle_query": True,
        "source_sha256": {"fabricated_oracle_source": "unit_only"}})
    # Neither static configuration contains candidate/evaluation outcomes.
    kernel_path = base / "kernel.json"
    kernel_path.write_bytes((ROOT / "configs/repair_train_v06_001.json").read_bytes())
    kernel = json.loads(kernel_path.read_bytes())
    (base / "relabel.json").write_bytes((ROOT / "configs/relabel_refinement_v06_002.json").read_bytes())
    write(base / "packet_audit.json", {"checks": 1, "errors": []})
    write(base / "train_audit.json", {"checks": 1, "errors": []})
    write(base / "authoring_audit.json", {"checks": 1, "errors": 0})
    study.mkdir()
    (study / "selection_plan.json").write_bytes((ROOT / "configs/refinement_selection_v06_002.json").read_bytes())
    write(study / "training_evidence.json", {"fabricated_train_metadata": True})
    author = {"version": "matched_refinement_round_v06_002", "blocks": 5, "slots_per_block_arm": 8,
        "arms": list(ARMS), "registered_before_round2_authoring": True, "test_accessed": False,
        "all_unchanged_assessment_sources": r2.ORIGINAL_RUNTIME_SHA256,
        "training_evidence_sha256": digest(study / "training_evidence.json"),
        "selection_plan_sha256": digest(study / "selection_plan.json"),
        "kernel_config_sha256": digest(kernel_path), "kernel_config": kernel,
        "interface_limits": original.DEFAULT_INTERFACE_LIMITS,
        "source_sha256": {k: r2.ORIGINAL_RUNTIME_SHA256[n] for k, n in (
            ("assessment", "synthesis_study_v06.py"), ("kernel", "repair_v06.py"),
            ("typed_library", "graph_features.py"), ("compiled_runtime", "compiled.py"))}}
    write(study / "protocol.json", author)
    write(study / "freeze_receipt.json", {"before_round2_authoring": True,
        "protocol_sha256": digest(study / "protocol.json")})
    write(study / "transport_runtime_binding.json", {"before_any_R2_authoring_or_candidate_assessment": True,
        "R2_assessment_sha256": r2.R2_SELECTOR_SHA256, "selection_plan_sha256": r2.SELECTION_PLAN_SHA256,
        "independent_packet_audit_sha256": digest(base / "packet_audit.json")})
    write(study / "authoring_completion.json", {"version": "R2_matched_cli_authoring_completion_v06",
        "protocol_sha256": digest(study / "protocol.json"), "all15_R2_requests_frozen_before_assessment": True,
        "same_requested_model_and_settings_all_cells": True,
        "transport_runtime_binding_sha256": digest(study / "transport_runtime_binding.json"),
        "response_sha256": {f"block_{b}_{a}.json": "0" * 64 for b in range(5) for a in ARMS}})
    assessed.mkdir()
    (assessed / "candidate_results.jsonl").write_text("unit fixture byte binding only\n", encoding="utf-8")
    selected = selection_fixture(missing)
    write(assessed / "execution.json", {"all15_R2_requests_frozen_before_assessment": True,
        "protocol_sha256": digest(study / "protocol.json"), "TEST_accessed": False,
        "matched_transport_complete_blocks": selected["matched_transport_complete_blocks"]})
    selected.update(protocol_sha256=digest(study / "protocol.json"),
        execution_sha256=digest(assessed / "execution.json"),
        candidate_results_sha256=digest(assessed / "candidate_results.jsonl"))
    write(base / "selection.json", selected)
    write(assessed / "complete.json", {"complete": True, "all120_assessed": True,
        "ready_for_TEST": True, "proposed_witness_joint_count": 4,
        "selection_sha256": digest(base / "selection.json"), "TEST_queries": 0})
    raw = program()
    write(base / "control_bank.json", {"banks": {"enumerated_structural": [raw] * 8, "fixed_base9": [raw] * 8},
        "degree_fixed_reference": FeatureRuleProgram("degree", [], "weight/max(1,degree)").to_dict()})
    write(base / "control_freeze.json", {"control_banks_sha256": digest(base / "control_bank.json")})
    write(controls / "protocol.json", {"control_bank_sha256": digest(base / "control_bank.json"),
        "kernel_config": kernel, "interface_limits": original.DEFAULT_INTERFACE_LIMITS})
    write(controls / "freeze_receipt.json", {"protocol_sha256": digest(controls / "protocol.json")})
    write(base / "controls_selection.json", {"selection_split": "train", "test_accessed": False,
        "all64_original_slots_assessed": True, "no_fallback": True,
        "registration_sha256": digest(controls / "protocol.json"),
        "selections": [{"block": 0, "bank": group, "quality_only_baseline": {"id": group + "_unit",
            "slot": 0, "program": raw, "program_sha256": canonical(raw), "eligible": False}}
            for group in ("enumerated_structural", "fixed_base9")]})
    paths = {"R2_protocol_sha256": study / "protocol.json", "selection_plan_sha256": study / "selection_plan.json",
        "authoring_completion_sha256": study / "authoring_completion.json",
        "transport_runtime_binding_sha256": study / "transport_runtime_binding.json",
        "R2_TRAIN_execution_sha256": assessed / "execution.json", "R2_TRAIN_complete_sha256": assessed / "complete.json",
        "R2_candidate_results_sha256": assessed / "candidate_results.jsonl", "R2_TRAIN_audit_sha256": base / "train_audit.json",
        "R2_authoring_audit_sha256": base / "authoring_audit.json", "packet_audit_sha256": base / "packet_audit.json",
        "training_evidence_sha256": study / "training_evidence.json", "R2_freeze_sha256": study / "freeze_receipt.json",
        "original_evidence_freeze_sha256": plan / "freeze_receipt.json", "original_data_sha256": plan / "data.json",
        "original_query_protocol_sha256": plan / "protocol.json", "controls_protocol_sha256": controls / "protocol.json",
        "controls_freeze_sha256": controls / "freeze_receipt.json", "control_bank_sha256": base / "control_bank.json",
        "control_bank_freeze_sha256": base / "control_freeze.json", "kernel_config_sha256": kernel_path,
        "relabel_config_sha256": base / "relabel.json"}
    bindings = {n: digest(p) for n, p in paths.items()}
    bindings.update(selection_sha256=digest(base / "selection.json"),
        controls_selection_sha256=digest(base / "controls_selection.json"))
    write(base / "release.json", release_fixture(selected, bindings))
    certs.mkdir()
    (certs / "results.jsonl").write_text("".join(json.dumps(l) + "\n" for l in labels), encoding="utf-8")
    for n in ("data.json", "protocol.json"):
        (certs / n).write_bytes((plan / n).read_bytes())
    write(certs / "execution.json", {"split": "test", "programme_freeze_sha256": digest(base / "release.json"),
        "source_sha256": {"fabricated_oracle_source": "unit_only"}})
    write(certs / "complete.json", {"execution_complete": True, "split": "test", "states": 72,
        "results_sha256": digest(certs / "results.jsonl"), "programme_freeze_sha256": digest(base / "release.json")})
    return dict(plan=plan, selection=base / "selection.json", selection_sha256=digest(base / "selection.json"),
        controls_selection=base / "controls_selection.json",
        controls_selection_sha256=digest(base / "controls_selection.json"), certificates=certs,
        test_certificate_sha256=digest(certs / "results.jsonl"), r2_study=study, train_assessment=assessed,
        train_audit=base / "train_audit.json", authoring_audit=base / "authoring_audit.json",
        packet_audit=base / "packet_audit.json", root_release=base / "release.json",
        root_release_sha256=digest(base / "release.json"), controls_registration=controls,
        control_bank=base / "control_bank.json", control_freeze=base / "control_freeze.json",
        relabel_config=base / "relabel.json", kernel_config=kernel_path, out=base / "registration", workers=8)


class R2SelectionTests(unittest.TestCase):
    def test_four_joint_w_and_twelve_quality_with_gate_failure_are_distinct(self):
        entries = r2.validate_selected(selection_fixture())
        self.assertEqual(len(entries), 16)
        joint = [e for e in entries if e["joint_gate_required"]]
        quality = [e for e in entries if not e["joint_gate_required"]]
        self.assertEqual(len(joint), 4)
        self.assertTrue(all(e["arm"] == "witness" and e["eligible"] for e in joint))
        self.assertEqual(len(quality), 12)
        self.assertTrue(all(not e["eligible"] and e["joint_gate_not_required"] for e in quality))
        # Same AST still has sixteen distinct authoring/selection identities.
        self.assertEqual(len({e["program_sha256"] for e in entries}), 1)
        self.assertEqual(len({e["id"] for e in entries}), 16)

    def test_missing_quality_positions_remain_null(self):
        entries = r2.validate_selected(selection_fixture(((0, "objective"), (2, "witness"))))
        nulls = [e for e in entries if e["missing_baseline"]]
        self.assertEqual(len(nulls), 2)
        self.assertTrue(all(e["program"] is None and e["priority"] is None for e in nulls))
        bad = selection_fixture(((0, "objective"),))
        bad["programs"][6]["program"] = program()
        with self.assertRaises(ValueError):
            r2.validate_selected(bad)

    def test_genuine_joint_barrier_cannot_be_replaced_by_quality_w(self):
        for field, value in (("ready_for_TEST", False), ("all120_original_slots_assessed", False),
                             ("proposed_witness_joint_count", 3), ("R1_barrier_remains_failed", False)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                r2.validate_selected({**selection_fixture(), field: value})
        selected = selection_fixture(); selected["programs"][0]["eligible"] = False
        with self.assertRaisesRegex(ValueError, "Genuine"):
            r2.validate_selected(selected)
        selected = selection_fixture(); selected["programs"][0]["joint_gate_required"] = False
        with self.assertRaisesRegex(ValueError, "gate-required"):
            r2.validate_selected(selected)

    def test_root_release_requires_all15_audit_four_w_and_byte_bindings(self):
        selected = selection_fixture(); bindings = {"selection_sha256": "a" * 64}
        release = release_fixture(selected, bindings)
        r2.validate_release(release, bindings, selected)
        for key, value in (("allow_TEST", False), ("all15_R2_requests_frozen_before_assessment", False),
                           ("independent_R2_TRAIN_audit_zero_errors", False), ("proposed_witness_joint_count", 3)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Root R2 release"):
                r2.validate_release({**release, key: value}, bindings, selected)
        with self.assertRaisesRegex(ValueError, "binding"):
            r2.validate_release(release, {"selection_sha256": "b" * 64}, selected)
        with self.assertRaisesRegex(ValueError, "frozen runtime"):
            r2.validate_release({**release, "original_runtime_sha256": {}}, bindings, selected)


class R2TinyMechanismTests(unittest.TestCase):
    def test_missing_entry_never_scores_or_searches_and_has_no_fake_zero(self):
        records, labels = tiny_pair()
        entry = next(e for e in r2.validate_selected(selection_fixture(((0, "objective"),))) if e["missing_baseline"])
        with patch.object(original, "evaluate_entry", side_effect=AssertionError("Missing cannot execute")):
            result = r2.evaluate_entry((entry, records, labels, {"source_sha256": r2.source_hashes()}, "original"))
        self.assertIsNone(result["interface"])
        self.assertIsNone(result["kernel_summary"])
        self.assertIsNone(result["actual_wall_seconds"])
        self.assertEqual(len(result["kernel_rows"]), 2)
        self.assertTrue(all(r["result"] is None for r in result["kernel_rows"]))
        self.assertEqual(result["extra_oracle_calls"], 0)

    def test_unused_addition_still_fails_and_all_five_pairs_remap_exactly(self):
        records, labels = tiny_pair(numeric=True)
        saved = deepcopy((records, labels))
        self.assertTrue(original.heldout_interface_assessment(program("weight"), records, labels)["quotient"]["contradictory"])
        maps = []
        for i in range(5):
            rs, ls, mapping = original.relabel_inventory(records, labels, i, "V06_RELABEL_ROBUSTNESS_20261004_001")
            mp = mapping["fixture"]; maps.append(tuple(sorted(mp.items())))
            self.assertEqual(len(mp), len(set(mp.values())))
            self.assertEqual(rs[0]["graph"]["contacts"], rs[1]["graph"]["contacts"])
            self.assertEqual(rs[0]["fixed"], [mp["6"]]); self.assertEqual(rs[1]["excluded"], [mp["7"]])
            self.assertEqual(ls[0]["rows"][0]["a"], mp["0"])
            self.assertEqual(ls[0]["rows"][0]["difference"]["lower_exact"], "1")
            self.assertEqual(ls[1]["rows"][0]["difference"]["upper_exact"], "-1")
            assessed = original.heldout_interface_assessment(program(), rs, ls)
            self.assertEqual(assessed["strict_passed"], 2)
            self.assertTrue(original.paired_checks(assessed)[0]["pair_passed"])
            self.assertTrue(all(r["split"] == "test" for r in rs))
        self.assertEqual(len(set(maps)), 5)
        self.assertEqual((records, labels), saved)

    def test_r2_wrapper_keeps_full_tiny_states_original_shared_kernel_and_roles(self):
        records, labels = tiny_pair()
        entry = r2.validate_selected(selection_fixture())[0]
        protocol = {"source_sha256": r2.source_hashes(), "original_helper_sha256": original.source_hashes(),
            "interface_limits": original.DEFAULT_INTERFACE_LIMITS,
            "kernel_config": {"seconds": .5, "clock": "wall", "repair_config": original.REPAIR_CONFIG}}
        result = r2.evaluate_entry((entry, records, labels, protocol, "original"))
        self.assertEqual(result["identity"]["role"], "proposed_witness_joint")
        self.assertEqual(result["interface"]["strict_passed"], 2)
        self.assertEqual(result["kernel_coverage"]["verified_incumbents"], 2)
        self.assertTrue(all(Fraction(r["result"]["value_exact"]) == 4 for r in result["kernel_rows"]))
        self.assertEqual(result["extra_oracle_calls"], 0)
        self.assertFalse(result["selection_performed"])


class R2PreparationTests(unittest.TestCase):
    def test_full_fabricated_prepare_27_positions_nulls_and_freeze_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            kwargs = synthetic_registration_files(Path(temp), ((0, "objective"),))
            with patch.object(r2.platform, "system", return_value="Linux"), \
                 patch.object(original, "evaluate_entry", side_effect=AssertionError("Prepare cannot evaluate")):
                result = r2.prepare(**kwargs)
                self.assertEqual(result["requested_identities"], 27)
                self.assertEqual(result["present_identities"], 26)
                self.assertEqual(result["requested_state_assignments"], 11664)
                self.assertEqual(result["TEST_programme_evaluations"], 0)
                proto = json.loads((kwargs["out"] / "protocol.json").read_bytes())
                self.assertEqual(proto["assignments"], 162)
                self.assertEqual(proto["scorable_state_assignments"], 26 * 72 * 6)
                self.assertEqual(proto["proposed_method_count"], 4)
                self.assertEqual(proto["main_comparators_requested"], 19)
                self.assertEqual(sum(e["missing_baseline"] for e in proto["entries"] if "missing_baseline" in e), 1)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    r2.prepare(**kwargs)
                (kwargs["out"] / "test_inputs.json").write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "changed"):
                    r2.run(kwargs["out"], Path(temp) / "must_not_run", kwargs["root_release_sha256"])
                self.assertFalse((Path(temp) / "must_not_run").exists())

    def test_release_denied_before_reading_any_test_certificate(self):
        with tempfile.TemporaryDirectory() as temp:
            kwargs = synthetic_registration_files(Path(temp))
            release = json.loads(kwargs["root_release"].read_bytes()); release["allow_TEST"] = False
            write(kwargs["root_release"], release); kwargs["root_release_sha256"] = digest(kwargs["root_release"])
            # Destroy the synthetic label file: an early release rejection must
            # occur before any access, rather than a missing-label exception.
            (kwargs["certificates"] / "results.jsonl").unlink()
            with patch.object(r2.platform, "system", return_value="Linux"):
                with self.assertRaisesRegex(ValueError, "Root R2 release"):
                    r2.prepare(**kwargs)
            self.assertFalse(kwargs["out"].exists())

    def test_certificates_bind_release_not_selection_and_failed_audits_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            kwargs = synthetic_registration_files(Path(temp))
            cert_path = kwargs["certificates"] / "execution.json"
            cert = json.loads(cert_path.read_bytes()); cert["programme_freeze_sha256"] = kwargs["selection_sha256"]
            write(cert_path, cert)
            with patch.object(r2.platform, "system", return_value="Linux"):
                with self.assertRaisesRegex(ValueError, "root-release"):
                    r2.prepare(**kwargs)
        with self.assertRaisesRegex(ValueError, "zero errors"):
            r2._audit_passed({"checks": 10, "errors": ["bad source"]}, "fabricated")

    def test_linux_guard_and_original_adapter_config_unchanged(self):
        with patch.object(r2.platform, "system", return_value="Windows"):
            with self.assertRaisesRegex(ValueError, "Linux-only"):
                r2.run("missing", "missing", "0" * 64)
        self.assertEqual(digest(original.__file__), r2.ORIGINAL_HELDOUT_SHA256)
        self.assertEqual(digest(ROOT / "configs/relabel_v06_001.json"), r2.ORIGINAL_RELABEL_SHA256)
        r2._check_runtime()


if __name__ == "__main__":
    unittest.main()
