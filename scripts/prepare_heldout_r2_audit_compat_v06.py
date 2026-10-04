"""Lossless metadata-only preparation compatibility for immutable R2 runtime.

The original pre-generation transport binds the original independent packet
report, while the main TEST release binds its reviewed scalar-count receipt.
Both byte identities must be verified. This separate preparation entry point
changes only that comparison, plus the source-snapshot location needed because
the function lives in scripts/. All selection, certificate and execution checks
are preserved; the original run function and every runtime source stay intact.
"""
from __future__ import annotations
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cipheur import heldout_refinement_v06 as frozen
from cipheur.heldout_refinement_v06 import (
    _linux_only, _check_runtime, _bound_read, validate_selected, validate_release,
    _read, digest, _audit_passed, ARMS, ORIGINAL_RUNTIME_SHA256, SELECTION_PLAN_SHA256,
    R2_SELECTOR_SHA256, ORIGINAL_RELABEL_SHA256, original, ROLE_SCOPE, source_hashes, write)

EXPECTED_ORIGINAL_PACKET_AUDIT_SHA256='7cabb43f86f1346dfd7b0156c096fc05bfd70c6f24850ee663394137f803837c'
EXPECTED_PREPARER_SHA256='1e8bd6a2577eabe8e33a73edc1303358f09cdbfc1c5c53604eaf91db3380ef1a'
EXPECTED_MAIN_ROOT_SHA256='8e69f14051ce731332b11aaefa2f60c2ace38780e4f20dfb9429974555ca83d1'

def verify_compatibility(compatibility_release, original_packet_audit, arguments):
    """No certificates, input graphs, policy scores, candidates or outcomes read."""
    release=_read(compatibility_release)
    if (release.get('version')!='v06_R2_packet_audit_identity_preparation_compatibility_001'
        or release.get('issued_by')!='root'
        or release.get('before_any_R2_TEST_programme_evaluation') is not True
        or release.get('scientific_runtime_and_selection_unchanged') is not True
        or release.get('metadata_comparison_changes')!=1):
        raise ValueError('Require separate root-owned metadata-only compatibility release')
    if digest(frozen.__file__)!=EXPECTED_PREPARER_SHA256 or release.get('original_preparer_sha256')!=EXPECTED_PREPARER_SHA256:
        raise ValueError('Original preparation/runtime bytes changed')
    if digest(__file__)!=release.get('compatibility_preparer_sha256'):
        raise ValueError('Compatibility preparation bytes changed')
    if (arguments['root_release_sha256']!=EXPECTED_MAIN_ROOT_SHA256
        or digest(arguments['root_release'])!=EXPECTED_MAIN_ROOT_SHA256
        or release.get('main_root_release_sha256')!=EXPECTED_MAIN_ROOT_SHA256):
        raise ValueError('Original main root release changed')
    main=_read(arguments['root_release'])
    original_hash=digest(original_packet_audit)
    if (original_hash!=EXPECTED_ORIGINAL_PACKET_AUDIT_SHA256
        or release.get('original_packet_audit_sha256')!=original_hash
        or main.get('original_independent_audit_sha256',{}).get('refinement_packet_audit_v06_002.json')!=original_hash):
        raise ValueError('Original independent packet audit was not frozen by main release')
    audit=_read(original_packet_audit); scalar=_read(arguments['packet_audit'])
    if (digest(arguments['packet_audit'])!=main['packet_audit_sha256']
        or release.get('scalar_packet_receipt_sha256')!=main['packet_audit_sha256']
        or scalar.get('schema_adapter',{}).get('original_report_sha256')!=original_hash
        or scalar.get('schema_adapter',{}).get('adapter_source_sha256')!=main['independent_audit_schema_adapter_sha256']
        or audit.get('errors')!=[] or audit.get('error_count')!=0
        or not isinstance(audit.get('checks'),dict)
        or not audit['checks'] or any(type(n) is not int or n<0 for n in audit['checks'].values())
        or sum(audit['checks'].values())!=audit.get('total_checks')
        or scalar.get('checks')!=audit.get('total_checks') or scalar.get('errors')!=0
        or scalar.get('original_check_categories')!=audit['checks']
        or scalar.get('original_error_records')!=audit['errors']):
        raise ValueError('Lossless zero-error packet-audit provenance failed')
    for key,value in audit.items():
        if key not in ('checks','errors') and scalar.get(key)!=value:
            raise ValueError('Original packet-audit finding changed: '+key)
    runtime=_read(Path(arguments['r2_study'])/'transport_runtime_binding.json')
    if runtime.get('independent_packet_audit_sha256')!=original_hash:
        raise ValueError('Pre-generation transport no longer binds original packet report')
    return release

def _prepare_compat(plan, selection, selection_sha256, controls_selection, controls_selection_sha256,
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
        or runtime.get("independent_packet_audit_sha256") != EXPECTED_ORIGINAL_PACKET_AUDIT_SHA256
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
        shutil.copyfile(Path(frozen.__file__).parent / name, target)
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

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','selection','selection-sha256','controls-selection','controls-selection-sha256',
        'certificates','test-certificate-sha256','r2-study','train-assessment','train-audit','authoring-audit',
        'packet-audit','root-release','root-release-sha256','controls-registration','control-bank','control-freeze',
        'relabel-config','kernel-config','out','compatibility-release','original-packet-audit'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--workers',type=int,default=8)
    args=vars(parser.parse_args())
    compat=args.pop('compatibility_release'); packet=args.pop('original_packet_audit')
    verify_compatibility(compat,packet,args)
    print(json.dumps(_prepare_compat(**args),ensure_ascii=False))

if __name__=='__main__':main()
