"""Outcome-free EoH addon tests: fabricated metadata and tiny graphs only."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur import heldout_published_eoh_v06 as addon
from cipheur import heldout_mechanism_v06 as original
from cipheur import heldout_refinement_v06 as r2
from cipheur.synthesis_study_v06 import canonical, digest, write
from tests.test_heldout_mechanism_v06 import program, tiny_pair
from tests.test_heldout_refinement_v06 import synthetic_registration_files


def selection_fixture(missing=(), authored=()):
    raw = program()
    programs = []
    for run in range(4):
        absent, is_authored = run in missing, run in authored
        programs.append({"id": addon.IDENTITIES[run], "run": run,
            "role": "nonguarded_published_quality_baseline", "joint_gate_required": False,
            "program": None if absent else raw, "program_sha256": None if absent else canonical(raw),
            "source_id": None if absent else f"run_{run}_slot_3" if is_authored else f"run_{run}:warm_seed",
            "winner_origin": "missing" if absent else "genuine_EoH_author_slot" if is_authored else "shared_R1_warm_seed",
            "TRAIN_label_selected_seed_history": True, "gate_fit_not_used_for_selection": True})
    return {"version": "v06_published_EoH_DSL_TRAIN_quality_selection_001", "programs": programs,
        "original_positions": [{"run": r, "slot": s, "id": f"run_{r}_slot_{s}", "status": "fabricated"}
            for r in range(4) for s in range(8)], "requested_positions": 32, "all32_positions_frozen": True,
        "root_authoring_release_sha256": addon.EOH_AUTHOR_RELEASE_SHA256, "protocol_sha256": "a" * 64,
        "no_retry_or_fallback_authored_output": True, "TEST_accessed": False}


def release_fixture(bindings):
    return {"version": "v06_published_EoH_root_TEST_addon_release_001", "issued_by": "root", "allow_TEST": True,
        "before_any_addon_TEST_label_read_or_programme_evaluation": True,
        "EoH_bank_and_audits_frozen_before_original_TEST_queries": True,
        "all32_author_positions_and4_seed_fitness_frozen": True,
        "independent_EoH_author_and_TRAIN_audits_zero_errors": True,
        "requested_published_identities": 4, "original_R2_27_identities_roles_hashes_unchanged": True, **bindings}


def preparation_fixture(base):
    old = synthetic_registration_files(base)
    with patch.object(r2.platform, "system", return_value="Linux"):
        r2.prepare(**old)
    parent = old["out"]
    pp = addon.read(parent / "protocol.json")
    registration = base / "addon_static"
    proto = {"version": "v06_published_EoH_heldout_addon_registration_001", "source_sha256": addon.source_hashes(),
        "R2_source_sha256": r2.source_hashes(), "original_helper_sha256": original.source_hashes(),
        "EoH_protocol_sha256": "a" * 64, "EoH_seed_program_sha256": canonical(program()),
        "EoH_kernel_config_sha256": digest(parent / "kernel_config.json"),
        "original_data_sha256": pp["original_data_sha256"], "original_query_protocol_sha256": pp["original_query_protocol_sha256"],
        "variants": addon.VARIANTS, "salt": addon.SALT, "workers": 1, "requested_state_assignments": 1728}
    write(registration / "protocol.json", proto)
    write(registration / "freeze_receipt.json", {"source_sha256": addon.source_hashes(),
        "artifact_sha256": {"protocol.json": digest(registration / "protocol.json")}})
    selected = base / "eoh_selection.json"
    write(selected, selection_fixture(missing=(3,)))
    audits = {}
    for phase in ("authoring", "train"):
        audits[phase] = base / ("eoh_" + phase + "_audit.json")
        write(audits[phase], {"checks": {"independent_fixture": 2}, "errors": 0, "audit_phase": phase,
            "selection_sha256": digest(selected), "protocol_sha256": "a" * 64,
            "root_authoring_release_sha256": addon.EOH_AUTHOR_RELEASE_SHA256,
            "all32_positions_frozen": True, "TEST_accessed": False})
    # Complete fabricated main receipt; genuine evidence is never modified by these tests.
    main = addon.read(parent / "root_release.json")
    main.update(published_EoH_all32_and4_seed_fitness_frozen_before_TEST=True,
        published_EoH_addon_registration_sha256=digest(registration / "freeze_receipt.json"),
        published_EoH_selection_sha256=digest(selected), published_EoH_authoring_audit_sha256=digest(audits["authoring"]),
        published_EoH_TRAIN_audit_sha256=digest(audits["train"]), published_EoH_addon_source_sha256=addon.source_hashes())
    write(parent / "root_release.json", main)
    pp["root_release_sha256"] = digest(parent / "root_release.json")
    write(parent / "protocol.json", pp)
    pf = addon.read(parent / "freeze_receipt.json")
    pf["root_release_sha256"] = pp["root_release_sha256"]
    pf["artifact_sha256"] = {n: digest(parent / n) for n in pf["artifact_sha256"]}
    write(parent / "freeze_receipt.json", pf)
    bindings = {"addon_registration_sha256": digest(registration / "freeze_receipt.json"),
        "R2_registration_freeze_sha256": digest(parent / "freeze_receipt.json"), "EoH_selection_sha256": digest(selected),
        "EoH_authoring_audit_sha256": digest(audits["authoring"]), "EoH_TRAIN_audit_sha256": digest(audits["train"]),
        "EoH_protocol_sha256": "a" * 64, "EoH_author_release_sha256": addon.EOH_AUTHOR_RELEASE_SHA256,
        "original_data_sha256": pp["original_data_sha256"], "original_query_protocol_sha256": pp["original_query_protocol_sha256"],
        "addon_source_sha256": addon.source_hashes(), "R2_root_release_sha256": pp["root_release_sha256"],
        "R2_selection_sha256": pp["selection_sha256"]}
    release = base / "eoh_release.json"
    write(release, release_fixture(bindings))
    return dict(registration=registration, registration_sha256=bindings["addon_registration_sha256"],
        r2_registration=parent, r2_freeze_sha256=bindings["R2_registration_freeze_sha256"], selection=selected,
        selection_sha256=digest(selected), authoring_audit=audits["authoring"], train_audit=audits["train"],
        root_release=release, root_release_sha256=digest(release), out=base / "eoh_prepared")


class EoHAddonTests(unittest.TestCase):
    def validate(self, selected):
        return addon.validate_selection(selected, "a" * 64, canonical(program()))

    def test_four_duplicates_keep_seed_origin_and_identity(self):
        entries = self.validate(selection_fixture())
        self.assertEqual(len(entries), 4)
        self.assertEqual(len({e["program_sha256"] for e in entries}), 1)
        self.assertEqual([e["id"] for e in entries], addon.IDENTITIES)
        self.assertTrue(all(e["winner_origin"] == "shared_R1_warm_seed" for e in entries))

    def test_authored_origin_and_null_stay_distinct(self):
        entries = self.validate(selection_fixture(missing=(3,), authored=(1,)))
        self.assertEqual(entries[1]["source_id"], "run_1_slot_3")
        self.assertTrue(entries[3]["missing_baseline"])
        self.assertIsNone(entries[3]["priority"])

    def test_changed_seed_or_crossrun_origin_rejected(self):
        for field, value in (("program_sha256", "0" * 64), ("source_id", "run_3:warm_seed")):
            s = selection_fixture(); s["programs"][0][field] = value
            with self.assertRaises(ValueError):
                self.validate(s)

    def test_missing_output_cannot_have_fallback(self):
        s = selection_fixture(missing=(0,)); s["programs"][0]["program"] = program()
        with self.assertRaises(ValueError):
            self.validate(s)

    def test_positions_gate_and_test_access_bound(self):
        for edit in (lambda s: s["original_positions"].pop(), lambda s: s.update(TEST_accessed=True),
                     lambda s: s["programs"][0].update(joint_gate_required=True)):
            s = selection_fixture(); edit(s)
            with self.assertRaises(ValueError):
                self.validate(s)

    def test_audit_requires_complete_pass_and_selection_binding(self):
        a = {"checks": 3, "errors": [], "audit_phase": "train", "selection_sha256": "b" * 64,
            "protocol_sha256": "a" * 64, "root_authoring_release_sha256": addon.EOH_AUTHOR_RELEASE_SHA256,
            "all32_positions_frozen": True, "TEST_accessed": False}
        addon.audit_passed(a, "train", "b" * 64, "a" * 64)
        for field, value in (("errors", 1), ("all32_positions_frozen", False), ("selection_sha256", "c" * 64)):
            bad = deepcopy(a); bad[field] = value
            with self.assertRaises(ValueError):
                addon.audit_passed(bad, "train", "b" * 64, "a" * 64)

    def test_root_must_bind_all_prior_test_order_and_sources(self):
        bindings = {"addon_source_sha256": addon.source_hashes(), "EoH_selection_sha256": "b" * 64}
        release = release_fixture(bindings)
        addon.validate_release(release, bindings)
        for field, value in (("EoH_bank_and_audits_frozen_before_original_TEST_queries", False),
                             ("EoH_selection_sha256", "c" * 64), ("requested_published_identities", 3)):
            bad = deepcopy(release); bad[field] = value
            with self.assertRaises(ValueError):
                addon.validate_release(bad, bindings)

    def test_prepare_preserves_parent_and_full_mapping_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = preparation_fixture(Path(tmp))
            parent_bytes = {p: p.read_bytes() for p in args["r2_registration"].rglob("*") if p.is_file()}
            with patch.object(addon.platform, "system", return_value="Linux"):
                info = addon.prepare(**args)
            self.assertEqual(info["requested_state_assignments"], 1728)
            self.assertEqual(info["present_identities"], 3)
            self.assertEqual(parent_bytes, {p: p.read_bytes() for p in parent_bytes})
            for name in ("test_inputs.json", "test_certificates.json", "relabel_inventory.json"):
                self.assertEqual((args["out"] / name).read_bytes(), (args["r2_registration"] / name).read_bytes())
            with patch.object(addon.platform, "system", return_value="Linux"), self.assertRaises(ValueError):
                addon.prepare(**args)

    def test_bad_root_rejected_before_any_prepared_test_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = preparation_fixture(Path(tmp))
            bad = addon.read(args["root_release"]); bad["allow_TEST"] = False
            write(args["root_release"], bad); args["root_release_sha256"] = digest(args["root_release"])
            actual_read, accessed = addon.read, []
            def guard(path):
                if Path(path).name in ("test_inputs.json", "test_certificates.json"):
                    accessed.append(str(path)); raise AssertionError("TEST access before release")
                return actual_read(path)
            with patch.object(addon.platform, "system", return_value="Linux"), patch.object(addon, "read", side_effect=guard):
                with self.assertRaises(ValueError):
                    addon.prepare(**args)
            self.assertEqual(accessed, [])

    def test_null_assignment_has_no_interface_or_schedule_calls(self):
        records, labels = tiny_pair(numeric=True)
        entry = self.validate(selection_fixture(missing=(0,)))[0]
        protocol = {"source_sha256": addon.source_hashes(), "R2_source_sha256": r2.source_hashes(),
            "original_helper_sha256": original.source_hashes()}
        with patch.object(original, "repair_schedule", side_effect=AssertionError("null inference")), \
             patch.object(original, "heldout_interface_assessment", side_effect=AssertionError("null diagnostic")):
            result = addon.evaluate_entry((entry, records, labels, protocol, "original"))
        self.assertEqual(len(result["kernel_rows"]), 2)
        self.assertIsNone(result["interface"])
        self.assertIsNone(result["kernel_summary"])
        self.assertIsNone(result["actual_cpu_seconds"])

    def test_tiny_present_output_uses_original_shared_runtime(self):
        records, labels = tiny_pair(numeric=True)
        entry = self.validate(selection_fixture(authored=(0,)))[0]
        protocol = {"source_sha256": addon.source_hashes(), "R2_source_sha256": r2.source_hashes(),
            "original_helper_sha256": original.source_hashes(), "interface_limits": original.DEFAULT_INTERFACE_LIMITS,
            "kernel_config": {"seconds": 0.5, "clock": "wall", "repair_config": original.REPAIR_CONFIG}}
        result = addon.evaluate_entry((entry, records, labels, protocol, "original"))
        self.assertEqual(result["assignment_status"], "program_evaluated")
        self.assertEqual(result["extra_oracle_calls"], 0)
        self.assertEqual(result["kernel_coverage"]["verified_incumbents"], 2)
        self.assertEqual(result["kernel_coverage"]["errors"], 0)

    def test_main_receipt_missing_eoh_proof_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = preparation_fixture(Path(tmp))
            parent = args["r2_registration"]
            main = addon.read(parent / "root_release.json")
            main.pop("published_EoH_all32_and4_seed_fitness_frozen_before_TEST")
            write(parent / "root_release.json", main)
            pp = addon.read(parent / "protocol.json")
            pp["root_release_sha256"] = digest(parent / "root_release.json")
            write(parent / "protocol.json", pp)
            pf = addon.read(parent / "freeze_receipt.json")
            pf["artifact_sha256"] = {n: digest(parent / n) for n in pf["artifact_sha256"]}
            write(parent / "freeze_receipt.json", pf)
            args["r2_freeze_sha256"] = digest(parent / "freeze_receipt.json")
            release = addon.read(args["root_release"])
            release["R2_registration_freeze_sha256"] = args["r2_freeze_sha256"]
            release["R2_root_release_sha256"] = pp["root_release_sha256"]
            write(args["root_release"], release)
            args["root_release_sha256"] = digest(args["root_release"])
            with patch.object(addon.platform, "system", return_value="Linux"), self.assertRaisesRegex(ValueError, "Main root release"):
                addon.prepare(**args)


if __name__ == "__main__":
    unittest.main()
