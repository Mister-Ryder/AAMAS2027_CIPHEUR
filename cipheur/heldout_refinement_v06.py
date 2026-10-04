"""R2-only frozen TEST adapter; no authoring, selection, or online oracle.

The original twelve-joint-winner adapter remains immutable. This separate
adapter requires a root release for four genuine W joint winners and retains
all twelve nonguarded quality-comparator positions, including explicit nulls.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import platform
import shutil
import time

from . import heldout_mechanism_v06 as original
from .graph_features import FeatureRuleProgram
from .synthesis_study_v06 import ARMS, canonical, digest, write


ORIGINAL_RUNTIME_SHA256 = {
    "compiled.py": "f0f85d0104fbdcdca54fd5adf743e42946812132612cfe590d02315fb8631788",
    "graph_features.py": "b6f807e9a1a13e8443532247e24fc802815053d375f69ed2c2718a222282a03d",
    "model.py": "d5968cffb1676a2f4bd73d5ba2715618142059b0c81ec8263f76a79100a8a1d8",
    "programs.py": "cca9739aff75dba79d3ad4b5742f1db10e88ffb398f21dbda09fc23bd20b0f59",
    "refinement.py": "90a7e6c6981a73d13b715dc0b2b773cd2052724c2e044af617b7795eb074bd99",
    "repair_v06.py": "c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3",
    "representation.py": "5f844dd5ab6d5f79e92a0a7ea6ba0af6073d2e7d3f39a69a091b3fcf875d9dc0",
    "synthesis_study_v06.py": "f640af65645426cdf172d1cbc7326bae221acf43ece81225ef8bf06cf2c8b0bb",
}
ORIGINAL_HELDOUT_SHA256 = "2df16b56c4910567c4112c4063e22cfe7eca603c0b22a6f3a8dffb1074c93b2f"
ORIGINAL_RELABEL_SHA256 = "b59803e0a96242d6572d35140151f0bf22e56b415022da94beb1ee8ec8615c1c"
R2_SELECTOR_SHA256 = "8a200a923cb50c0f691a2fe378300d89ce74c4565ade71437a1d07a282b087e6"
SELECTION_PLAN_SHA256 = "2fda6a9ef59f8483deb838c0edca2b515118c2d7409f44ee3bc655217d7c71d9"
SOURCE_NAMES = original.SOURCE_NAMES + ("heldout_refinement_v06.py", "refinement_study_v06.py")
ROLE_SCOPE = {
    "proposed_witness_joint": "Four genuine W joint winners; complete framework and joint selection",
    "nonguarded_quality_comparator": "Common objective selector; joint gate may fail; never a certified winner",
    "contrast": "W-joint versus R/O-quality includes selector differences, not isolated witness causality",
    "study": "R1-selected common warm seed; R2 is conditional incremental repair, not cold replication",
    "originality": "Shared Degree initialization and bounded classical MWIS repair are not LLM-specific gains",
    "uncertainty": "Original source cluster; paired endpoints, relabelings, and duplicate AST identities are dependent",
    "R1": "Original failed twelve-winner release remains failed and immutable",
}


def source_hashes():
    return {n: digest(Path(__file__).parent / n) for n in SOURCE_NAMES}


LOADED_SOURCE_HASHES = source_hashes()


def _linux_only():
    if platform.system() != "Linux":
        raise ValueError("R2 held-out research preparation/execution is Linux-only")


def _check_runtime(expected=None):
    current = source_hashes()
    if current != LOADED_SOURCE_HASHES or (expected is not None and current != expected):
        raise ValueError("Frozen R2 adapter/runtime changed after load")
    for name, sha in {**ORIGINAL_RUNTIME_SHA256, "heldout_mechanism_v06.py": ORIGINAL_HELDOUT_SHA256,
                      "refinement_study_v06.py": R2_SELECTOR_SHA256}.items():
        if current[name] != sha:
            raise ValueError("Original frozen runtime/selector changed: " + name)


def _read(path):
    return json.loads(Path(path).read_bytes())


def _bound_read(path, expected):
    return original._bound_read(path, expected)


def validate_selected(selection):
    """Validate the pre-generation R2 roles without loading raw candidates."""
    blocks, programs = selection.get("matched_transport_complete_blocks", []), selection.get("programs", [])
    if (selection.get("version") != "v06_R2_joint_and_quality_roles_TRAIN_selection_002"
        or selection.get("selection_split") != "train" or selection.get("test_accessed") is not False
        or selection.get("all120_original_slots_assessed") is not True or selection.get("no_fallback") is not True
        or selection.get("R1_barrier_remains_failed") is not True or selection.get("ready_for_TEST") is not True
        or selection.get("proposed_witness_joint_count") != 4
        or selection.get("quality_comparator_requested_count") != 12
        or selection.get("selection_plan_sha256") != SELECTION_PLAN_SHA256
        or len(blocks) != 4 or len(set(blocks)) != 4 or blocks != sorted(blocks)
        or any(type(b) is not int or not 0 <= b <= 4 for b in blocks) or len(programs) != 16):
        raise ValueError("R2 requires four genuine W joint winners and twelve explicit quality positions")
    joint = [p for p in programs if p.get("role") == "proposed_witness_joint"]
    quality = [p for p in programs if p.get("role") == "nonguarded_quality_comparator"]
    if (len(joint) != 4 or {(p["block"], p["arm"]) for p in joint} != {(b, "witness") for b in blocks}
        or len(quality) != 12 or {(p["block"], p["arm"]) for p in quality} != {(b, a) for b in blocks for a in ARMS}
        or len({p["id"] for p in programs}) != 16):
        raise ValueError("R2 joint/quality cells or assigned identities changed")
    missing, entries = [], []
    for p in joint + quality:
        is_joint = p["role"] == "proposed_witness_joint"
        if p.get("joint_gate_required") is not is_joint or type(p.get("eligible")) is not bool:
            raise ValueError("R2 gate-required role or recorded eligibility changed")
        if not is_joint and p.get("missing_baseline") is True:
            if (p["slot"] is not None or p["program"] is not None or p["program_sha256"] is not None
                or p.get("source_candidate_id") is not None or p["eligible"] is not False
                or p["id"] != f"quality|block_{p['block']}_{p['arm']}:missing"):
                raise ValueError("Missing R2 quality position must remain null without fallback")
            missing.append({"block": p["block"], "arm": p["arm"]})
            entries.append({**p, "priority": None, "main_comparison": True, "missing_baseline": True})
            continue
        source_id = f"block_{p['block']}_{p['arm']}:{p['slot']}"
        if (type(p["slot"]) is not int or not 0 <= p["slot"] < 8
            or p["id"] != ("joint|" if is_joint else "quality|") + source_id
            or p.get("source_candidate_id") != source_id
            or p.get("missing_baseline", False) is not False
            or (is_joint and p["eligible"] is not True)
            or canonical(p["program"]) != p["program_sha256"]):
            raise ValueError("Genuine R2 winner/program/slot binding changed")
        raw = FeatureRuleProgram.from_dict(p["program"]).to_dict()
        if raw != p["program"]:
            raise ValueError("R2 serialized program changed during validation")
        entries.append({**p, "program": raw, "priority": "program", "main_comparison": True,
                        "missing_baseline": False, "joint_gate_not_required": not is_joint})
    order = lambda c: (c["block"], c["arm"])
    if sorted(selection.get("quality_comparator_missing_cells", []), key=order) != sorted(missing, key=order):
        raise ValueError("R2 quality missing-cell inventory changed")
    return entries


def _audit_passed(audit, name):
    if type(audit.get("checks")) is not int or audit["checks"] < 1 or audit.get("errors") not in (0, []):
        raise ValueError("Independent audit did not pass with zero errors: " + name)


def validate_release(release, bindings, selection):
    if (release.get("version") != "v06_R2_root_TEST_release_002" or release.get("issued_by") != "root"
        or release.get("allow_TEST") is not True
        or release.get("before_any_TEST_labels_or_performance") is not True
        or release.get("all15_R2_requests_frozen_before_assessment") is not True
        or release.get("all120_original_slots_assessed") is not True
        or release.get("independent_R2_TRAIN_audit_zero_errors") is not True
        or release.get("authoring_completion_verified") is not True
        or release.get("proposed_witness_joint_count") != 4
        or release.get("R1_barrier_remains_failed") is not True
        or release.get("matched_transport_complete_blocks") != selection["matched_transport_complete_blocks"]):
        raise ValueError("Root R2 release after all15 authoring/TRAIN audit/four genuine W is required")
    for name, expected in bindings.items():
        if release.get(name) != expected:
            raise ValueError("Root R2 release binding changed: " + name)
    if release.get("original_runtime_sha256") != ORIGINAL_RUNTIME_SHA256:
        raise ValueError("Root R2 release must bind every original frozen runtime SHA256")
    if release.get("R2_heldout_source_sha256") != source_hashes():
        raise ValueError("Root R2 release must bind the new adapter and its complete helper sources")


def evaluate_entry(task):
    entry, records, labels, protocol, variant = task
    _check_runtime(protocol["source_sha256"])
    if entry.get("missing_baseline"):
        # Every assignment remains visible; no prediction, work or reward was measured.
        return {"id": entry["id"], "identity": entry, "variant": variant, "split": "test",
            "assignment_status": "missing_quality_comparator", "interface": None, "paired_checks": None,
            "kernel_rows": [{"id": r["id"], "family": r["family"], "cluster": r["cluster"],
                             "split": "test", "missing_baseline": True, "result": None} for r in records],
            "kernel_summary": None, "kernel_coverage": {"assigned_states": len(records),
                "returned_states": len(records), "missing_states": len(records), "normal_completed": 0,
                "verified_incumbents": 0, "errors": 0, "normal_budget_stops": 0},
            "actual_cpu_seconds": None, "actual_wall_seconds": None,
            "selection_performed": False, "extra_oracle_calls": 0, "role_scope": ROLE_SCOPE}
    helper_protocol = {**protocol, "source_sha256": protocol["original_helper_sha256"]}
    result = original.evaluate_entry((entry, records, labels, helper_protocol, variant))
    result.update(assignment_status="program_evaluated", role_scope=ROLE_SCOPE)
    return result


def prepare(plan, selection, selection_sha256, controls_selection, controls_selection_sha256,
            certificates, test_certificate_sha256, r2_study, train_assessment, train_audit,
            authoring_audit, packet_audit, root_release, root_release_sha256,
            controls_registration, control_bank, control_freeze, relabel_config,
            kernel_config, out, workers=8):
    _linux_only()
    out, plan, study, assessed, certificates = map(Path, (out, plan, r2_study, train_assessment, certificates))
    if out.exists():
        raise ValueError("Never overwrite R2 held-out registration")
    _check_runtime()
    # Release validation deliberately precedes reading any withheld certificates.
    release = _bound_read(root_release, root_release_sha256)
    selected = _bound_read(selection, selection_sha256)
    entries = validate_selected(selected)
    validate_release(release, {"selection_sha256": selection_sha256,
                              "controls_selection_sha256": controls_selection_sha256}, selected)
    controls = _bound_read(controls_selection, controls_selection_sha256)
    paths = {"R2_protocol_sha256": study / "protocol.json", "selection_plan_sha256": study / "selection_plan.json",
        "authoring_completion_sha256": study / "authoring_completion.json",
        "transport_runtime_binding_sha256": study / "transport_runtime_binding.json",
        "R2_TRAIN_execution_sha256": assessed / "execution.json", "R2_TRAIN_complete_sha256": assessed / "complete.json",
        "R2_candidate_results_sha256": assessed / "candidate_results.jsonl", "R2_TRAIN_audit_sha256": Path(train_audit),
        "R2_authoring_audit_sha256": Path(authoring_audit), "packet_audit_sha256": Path(packet_audit),
        "training_evidence_sha256": study / "training_evidence.json", "R2_freeze_sha256": study / "freeze_receipt.json",
        "original_evidence_freeze_sha256": plan / "freeze_receipt.json",
        "original_data_sha256": plan / "data.json", "original_query_protocol_sha256": plan / "protocol.json",
        "controls_protocol_sha256": Path(controls_registration) / "protocol.json",
        "controls_freeze_sha256": Path(controls_registration) / "freeze_receipt.json",
        "control_bank_sha256": Path(control_bank), "control_bank_freeze_sha256": Path(control_freeze),
        "kernel_config_sha256": Path(kernel_config), "relabel_config_sha256": Path(relabel_config)}
    bindings = {name: digest(path) for name, path in paths.items()}
    bindings.update(selection_sha256=selection_sha256, controls_selection_sha256=controls_selection_sha256)
    validate_release(release, bindings, selected)
    for path, name in ((train_audit, "R2 TRAIN"), (authoring_audit, "all15 R2 authoring"), (packet_audit, "packets")):
        _audit_passed(_read(path), name)
    author, completion, runtime, freeze = (_read(study / n) for n in (
        "protocol.json", "authoring_completion.json", "transport_runtime_binding.json", "freeze_receipt.json"))
    execution, complete = (_read(assessed / n) for n in ("execution.json", "complete.json"))
    selection_plan = _read(study / "selection_plan.json")
    if (author.get("version") != "matched_refinement_round_v06_002" or author.get("blocks") != 5
        or author.get("slots_per_block_arm") != 8 or author.get("arms") != list(ARMS)
        or author.get("registered_before_round2_authoring") is not True or author.get("test_accessed") is not False
        or selected["protocol_sha256"] != bindings["R2_protocol_sha256"]
        or selected["selection_plan_sha256"] != bindings["selection_plan_sha256"]
        or selected["execution_sha256"] != bindings["R2_TRAIN_execution_sha256"]
        or selected["candidate_results_sha256"] != bindings["R2_candidate_results_sha256"]
        or author.get("all_unchanged_assessment_sources") != ORIGINAL_RUNTIME_SHA256
        or author.get("training_evidence_sha256") != bindings["training_evidence_sha256"]
        or author.get("selection_plan_sha256") != SELECTION_PLAN_SHA256
        or selection_plan.get("registered_before_any_R2_authoring_or_candidate_assessment") is not True
        or selection_plan.get("deployment", {}).get("proposed_method_count") != 4
        or freeze.get("before_round2_authoring") is not True or freeze.get("protocol_sha256") != bindings["R2_protocol_sha256"]
        or completion.get("version") != "R2_matched_cli_authoring_completion_v06"
        or completion.get("protocol_sha256") != bindings["R2_protocol_sha256"]
        or completion.get("all15_R2_requests_frozen_before_assessment") is not True
        or completion.get("same_requested_model_and_settings_all_cells") is not True
        or completion.get("transport_runtime_binding_sha256") != bindings["transport_runtime_binding_sha256"]
        or set(completion.get("response_sha256", {})) != {f"block_{b}_{a}.json" for b in range(5) for a in ARMS}
        or runtime.get("before_any_R2_authoring_or_candidate_assessment") is not True
        or runtime.get("R2_assessment_sha256") != R2_SELECTOR_SHA256
        or runtime.get("selection_plan_sha256") != SELECTION_PLAN_SHA256
        or runtime.get("independent_packet_audit_sha256") != bindings["packet_audit_sha256"]
        or execution.get("all15_R2_requests_frozen_before_assessment") is not True
        or execution.get("protocol_sha256") != bindings["R2_protocol_sha256"] or execution.get("TEST_accessed") is not False
        or execution.get("matched_transport_complete_blocks") != selected["matched_transport_complete_blocks"]
        or complete.get("complete") is not True or complete.get("all120_assessed") is not True
        or complete.get("ready_for_TEST") is not True or complete.get("proposed_witness_joint_count") != 4
        or complete.get("selection_sha256") != selection_sha256 or complete.get("TEST_queries") != 0):
        raise ValueError("R2 frozen authoring/assessment/deployment metadata changed")
    for key, name in (("assessment", "synthesis_study_v06.py"), ("kernel", "repair_v06.py"),
                      ("typed_library", "graph_features.py"), ("compiled_runtime", "compiled.py")):
        if author["source_sha256"][key] != ORIGINAL_RUNTIME_SHA256[name]:
            raise ValueError("R2 original source binding changed: " + name)
    control_protocol = _read(Path(controls_registration) / "protocol.json")
    control_receipt, bank, bank_freeze = _read(paths["controls_freeze_sha256"]), _read(control_bank), _read(control_freeze)
    if (controls["registration_sha256"] != bindings["controls_protocol_sha256"]
        or control_receipt["protocol_sha256"] != bindings["controls_protocol_sha256"]
        or control_protocol["control_bank_sha256"] != bindings["control_bank_sha256"]
        or bank_freeze["control_banks_sha256"] != bindings["control_bank_sha256"]):
        raise ValueError("Original fixed-control freeze changed")
    entries += original.control_entries(controls, bank)
    if len(entries) != 27 or len({e["id"] for e in entries}) != 27:
        raise ValueError("All 27 R2 requested identities must remain explicit")
    relabel, kernel = _read(relabel_config), _read(kernel_config)
    if (relabel.get("version") != "v06_R2_pre_TEST_relabel_robustness_002"
        or relabel.get("registered_before_any_R2_TEST_labels_or_programme_evaluation") is not True
        or relabel.get("permutations_per_source") != 5 or relabel.get("requested_identities") != 27
        or relabel.get("original_relabel_config_sha256") != ORIGINAL_RELABEL_SHA256
        or relabel.get("salt") != "V06_RELABEL_ROBUSTNESS_20261004_001"
        or kernel["seconds"] != .5 or kernel["clock"] != "wall" or kernel["repair_config"] != original.REPAIR_CONFIG
        or workers != 8 or type(workers) is not int or kernel.get("workers") != 8
        or kernel != author["kernel_config"] or kernel != control_protocol["kernel_config"]
        or digest(kernel_config) != author["kernel_config_sha256"]
        or author["interface_limits"] != original.DEFAULT_INTERFACE_LIMITS
        or control_protocol["interface_limits"] != original.DEFAULT_INTERFACE_LIMITS):
        raise ValueError("Original five paired bijections/.5-second/200k-work semantics changed")
    data_freeze = _read(plan / "freeze_receipt.json")
    if (data_freeze.get("before_any_oracle_query") is not True
        or data_freeze["data_sha256"] != bindings["original_data_sha256"]
        or data_freeze["protocol_sha256"] != bindings["original_query_protocol_sha256"]):
        raise ValueError("Original frozen evidence/query definitions changed")
    records = [r for r in _read(plan / "data.json")["records"] if r["split"] == "test"]
    if len(records) != 72:
        raise ValueError("Retain all original 72 withheld states and every planned query")
    label_path = certificates / "results.jsonl"
    if digest(label_path) != test_certificate_sha256:
        raise ValueError("R2 TEST certificate SHA256 changed")
    cert_complete, cert_execution = (_read(certificates / n) for n in ("complete.json", "execution.json"))
    if (cert_complete.get("execution_complete") is not True or cert_complete.get("split") != "test"
        or cert_execution.get("split") != "test" or cert_complete.get("states") != 72
        or cert_complete["results_sha256"] != test_certificate_sha256
        or cert_complete["programme_freeze_sha256"] != root_release_sha256
        or cert_execution["programme_freeze_sha256"] != root_release_sha256
        or digest(certificates / "data.json") != bindings["original_data_sha256"]
        or digest(certificates / "protocol.json") != bindings["original_query_protocol_sha256"]
        or cert_execution["source_sha256"] != data_freeze["source_sha256"]):
        raise ValueError("R2 TEST certificates lack root-release/original-input binding")
    labels = [json.loads(line) for line in label_path.read_text(encoding="utf-8").splitlines() if line]
    original.validate_test_labels(records, labels)
    out.mkdir(parents=True)
    copies = {"root_release.json": root_release, "selection.json": selection, "controls_selection.json": controls_selection,
        "R2_protocol.json": paths["R2_protocol_sha256"], "selection_plan.json": paths["selection_plan_sha256"],
        "R2_freeze.json": paths["R2_freeze_sha256"], "authoring_completion.json": paths["authoring_completion_sha256"],
        "transport_runtime_binding.json": paths["transport_runtime_binding_sha256"],
        "R2_TRAIN_execution.json": paths["R2_TRAIN_execution_sha256"], "R2_TRAIN_complete.json": paths["R2_TRAIN_complete_sha256"],
        "R2_TRAIN_audit.json": train_audit, "R2_authoring_audit.json": authoring_audit, "packet_audit.json": packet_audit,
        "original_evidence_freeze.json": paths["original_evidence_freeze_sha256"],
        "original_query_protocol.json": paths["original_query_protocol_sha256"],
        "controls_protocol.json": paths["controls_protocol_sha256"], "controls_freeze.json": paths["controls_freeze_sha256"],
        "control_bank.json": control_bank, "control_bank_freeze.json": control_freeze,
        "kernel_config.json": kernel_config, "relabel_config.json": relabel_config}
    for name, path in copies.items():
        shutil.copyfile(path, out / name)
    write(out / "test_inputs.json", {"records": records})
    write(out / "test_certificates.json", {"labels": labels})
    inventory = []
    for i in range(5):
        rs, _, mappings = original.relabel_inventory(records, labels, i, relabel["salt"])
        inventory.append({"variant": f"relabel_{i}", "index": i, "mappings": mappings,
                          "graph_digests": {r["id"]: r["graph_digest"] for r in rs}})
    write(out / "relabel_inventory.json", inventory)
    sources = source_hashes()
    for name in sources:
        target = out / "source_snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).parent / name, target)
    present = sum(not e.get("missing_baseline", False) for e in entries)
    protocol = {"version": "v06_R2_heldout_mechanism_relabel_002", "split": "test", "role_scope": ROLE_SCOPE,
        "root_release_sha256": root_release_sha256, **bindings, "test_certificate_sha256": test_certificate_sha256,
        "release_bindings": bindings,
        "source_sha256": sources, "original_helper_sha256": original.source_hashes(), "entries": entries,
        "kernel_config": kernel, "interface_limits": original.DEFAULT_INTERFACE_LIMITS,
        "variants": ["original"] + [f"relabel_{i}" for i in range(5)], "workers": workers,
        "all_original_states": 72, "relabel_state_count": 360, "requested_identities": 27,
        "present_identities": present, "missing_quality_identities": 27 - present,
        "main_comparators_requested": 19, "proposed_method_count": 4, "quality_comparators_requested": 12,
        "assignments": 162, "requested_state_assignments": 11664, "scorable_state_assignments": present * 432,
        "matched_transport_complete_blocks": selected["matched_transport_complete_blocks"],
        "all_pairs_and_planned_queries_retained": True, "no_fallback": True,
        "selection_performed": False, "extra_oracle_calls": 0, "identical_AST_execution_reused": False,
        "normal_caps_retain_incumbents": True, "base_demanded_quotient_actual_scalar_fit_separate": True}
    write(out / "protocol.json", protocol)
    write(out / "freeze_receipt.json", {"before_any_R2_TEST_programme_evaluation": True,
        "root_release_sha256": root_release_sha256,
        "artifact_sha256": {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()},
        "source_sha256": sources})
    return {"prepared": str(out), "requested_identities": 27, "present_identities": present,
        "variants": 6, "requested_state_assignments": 11664, "TEST_programme_evaluations": 0}


def run(registration, out, root_release_sha256):
    _linux_only()
    registration, out = Path(registration), Path(out)
    if out.exists():
        raise ValueError("Never overwrite R2 held-out observations")
    freeze = _read(registration / "freeze_receipt.json")
    if (freeze.get("before_any_R2_TEST_programme_evaluation") is not True
        or freeze.get("root_release_sha256") != root_release_sha256):
        raise ValueError("R2 root-release-bound pre-evaluation freeze is required")
    for name, sha in freeze["artifact_sha256"].items():
        if digest(registration / name) != sha:
            raise ValueError("Registered R2 held-out input/source changed: " + name)
    _check_runtime(freeze["source_sha256"])
    protocol = _read(registration / "protocol.json")
    selected = _read(registration / "selection.json")
    validate_selected(selected)
    _bound_read(registration / "root_release.json", root_release_sha256)
    release = _read(registration / "root_release.json")
    validate_release(release, protocol["release_bindings"], selected)
    if (protocol.get("root_release_sha256") != root_release_sha256 or protocol.get("requested_identities") != 27
        or len(protocol["entries"]) != 27 or len({e["id"] for e in protocol["entries"]}) != 27
        or protocol["original_helper_sha256"] != original.source_hashes()):
        raise ValueError("R2 assignment/helper/release binding changed")
    records, labels = _read(registration / "test_inputs.json")["records"], _read(registration / "test_certificates.json")["labels"]
    if len(records) != 72:
        raise ValueError("R2 requires the full original 72-state TEST frame")
    original.validate_test_labels(records, labels)
    variants = [("original", records, labels)]
    relabel = _read(registration / "relabel_config.json")
    for planned in _read(registration / "relabel_inventory.json"):
        rs, ls, mappings = original.relabel_inventory(records, labels, planned["index"], relabel["salt"])
        if mappings != planned["mappings"] or {r["id"]: r["graph_digest"] for r in rs} != planned["graph_digests"]:
            raise ValueError("R2 registered paired relabel isomorphism changed")
        variants.append((planned["variant"], rs, ls))
    if [v[0] for v in variants] != protocol["variants"]:
        raise ValueError("Every original/five-relabel variant must remain assigned")
    tasks = [(e, rs, ls, protocol, variant) for variant, rs, ls in variants for e in protocol["entries"]]
    if len(tasks) != 162 or sum(len(t[1]) for t in tasks) != 11664:
        raise ValueError("All 27 requested identities by 72 states by six variants are required")
    out.mkdir(parents=True)
    write(out / "execution.json", {"registration_sha256": digest(registration / "protocol.json"),
        "root_release_sha256": root_release_sha256, "selection_sha256": protocol["selection_sha256"],
        "controls_selection_sha256": protocol["controls_selection_sha256"],
        "test_certificate_sha256": protocol["test_certificate_sha256"], "source_sha256": protocol["source_sha256"],
        "split": "test", "workers": protocol["workers"], "assignments": 162,
        "requested_state_assignments": 11664, "scorable_state_assignments": protocol["scorable_state_assignments"],
        "role_scope": ROLE_SCOPE, "selection_performed": False, "extra_oracle_calls": 0})
    rows = []
    started = time.perf_counter()
    with (out / "results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
            futures = {pool.submit(evaluate_entry, task): (task[0], task[-1]) for task in tasks}
            for future in as_completed(futures):
                entry, variant = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    row = {"id": entry["id"], "identity": entry, "variant": variant, "split": "test",
                        "kernel_rows": [], "assignment_status": "worker_error",
                        "worker_error_type": type(error).__name__, "worker_error": str(error),
                        "selection_performed": False, "extra_oracle_calls": 0, "role_scope": ROLE_SCOPE}
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); stream.flush()
                write(out / "progress.json", {"returned_assignments": len(rows), "assigned": len(tasks),
                    "last_id": entry["id"], "last_variant": variant})
    summary = []
    for entry in protocol["entries"]:
        observed = {r["variant"]: r for r in rows if r["id"] == entry["id"]}
        scores = [(observed[f"relabel_{i}"].get("interface") or {}).get("strict_passed") for i in range(5)]
        totals = [(observed[f"relabel_{i}"].get("interface") or {}).get("strict_total") for i in range(5)]
        complete_fit = all(s is not None for s in scores)
        summary.append({"id": entry["id"], "identity": entry, "missing_baseline": entry.get("missing_baseline", False),
            "original_strict_passed": (observed["original"].get("interface") or {}).get("strict_passed"),
            "original_strict_total": (observed["original"].get("interface") or {}).get("strict_total"),
            "all5_relabel_strict_passed": scores, "all5_relabel_strict_total": totals,
            "mean_relabel_strict_passed": sum(scores) / 5 if complete_fit else None,
            "worst_relabel_strict_passed": min(scores) if complete_fit else None,
            "all5_fit_measurements_available": complete_fit, "role_scope": ROLE_SCOPE})
    write(out / "robustness_summary.json", summary)
    measured = [r for r in rows if r["assignment_status"] != "missing_quality_comparator"]
    write(out / "complete.json", {"execution_complete": len(rows) == len(tasks), "split": "test",
        "returned_assignments": len(rows), "assigned": 162, "requested_state_assignments": 11664,
        "missing_assignments": sum(r["assignment_status"] == "missing_quality_comparator" for r in rows),
        "worker_errors": sum("worker_error" in r for r in rows),
        "interface_errors": sum("interface_error" in r for r in measured),
        "kernel_errors": sum(r.get("kernel_coverage", {}).get("errors", 72) for r in measured),
        "results_sha256": digest(out / "results.jsonl"), "root_release_sha256": root_release_sha256,
        "actual_execution_wall_seconds": time.perf_counter() - started,
        "selection_performed": False, "extra_oracle_calls": 0, "no_fallback": True,
        "all_pairs_quota_shortfalls_unknowns_missing_positions_retained": True})
    return {"complete": str(out), "returned_assignments": len(rows), "assigned": 162}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    for name in ("plan", "selection", "selection-sha256", "controls-selection", "controls-selection-sha256",
                 "certificates", "test-certificate-sha256", "r2-study", "train-assessment", "train-audit",
                 "authoring-audit", "packet-audit", "root-release", "root-release-sha256", "controls-registration",
                 "control-bank", "control-freeze", "relabel-config", "kernel-config", "out"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--workers", type=int, default=8)
    p = sub.add_parser("run")
    for name in ("registration", "out", "root-release-sha256"):
        p.add_argument("--" + name, required=True)
    args = vars(parser.parse_args()); mode = args.pop("mode")
    print(json.dumps(prepare(**args) if mode == "prepare" else run(**args), ensure_ascii=False))


if __name__ == "__main__":
    main()
