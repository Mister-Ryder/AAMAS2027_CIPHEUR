"""Root-owned metadata binding for the already frozen R2/EoH TEST protocols.

Default checking issues no release. Explicit issuance requires final independent
audits and the reviewed lossless schema receipts. No TEST labels, solver,
candidate assessment, model authoring or programme selection is executed here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

R2 = "experiments/discovery/v06_refinement_draft_003"
TRAIN = "experiments/discovery/v06_refinement_server_002/llm"
EOH = "experiments/discovery/v06_published_eoh_001"
ANALYSIS = "experiments/analysis/v06"
PLAN = "experiments/discovery/v06_evidence_001"
CONTROL = "experiments/discovery/v06_control_assessment_001"
PERFORMANCE = "experiments/discovery/performance_r2_eoh_test_v06_003_registered_001"
AUDIT_STEMS = ("refinement_train_audit_v06_002", "refinement_authoring_audit_v06_002",
               "refinement_packet_audit_v06_002")


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def bound_paths():
    return {
        "selection_sha256": f"{TRAIN}/selection.json",
        "controls_selection_sha256": "experiments/discovery/v06_synthesis_server_001/controls/selection.json",
        "R2_protocol_sha256": f"{R2}/protocol.json",
        "selection_plan_sha256": f"{R2}/selection_plan.json",
        "authoring_completion_sha256": f"{R2}/authoring_completion.json",
        "transport_runtime_binding_sha256": f"{R2}/transport_runtime_binding.json",
        "R2_TRAIN_execution_sha256": f"{TRAIN}/execution.json",
        "R2_TRAIN_complete_sha256": f"{TRAIN}/complete.json",
        "R2_candidate_results_sha256": f"{TRAIN}/candidate_results.jsonl",
        "R2_TRAIN_audit_sha256": f"{ANALYSIS}/{AUDIT_STEMS[0]}_scalar_receipt_001.json",
        "R2_authoring_audit_sha256": f"{ANALYSIS}/{AUDIT_STEMS[1]}_scalar_receipt_001.json",
        "packet_audit_sha256": f"{ANALYSIS}/{AUDIT_STEMS[2]}_scalar_receipt_001.json",
        "training_evidence_sha256": f"{R2}/training_evidence.json",
        "R2_freeze_sha256": f"{R2}/freeze_receipt.json",
        "original_evidence_freeze_sha256": f"{PLAN}/freeze_receipt.json",
        "original_data_sha256": f"{PLAN}/data.json",
        "original_query_protocol_sha256": f"{PLAN}/protocol.json",
        "controls_protocol_sha256": f"{CONTROL}/protocol.json",
        "controls_freeze_sha256": f"{CONTROL}/freeze_receipt.json",
        "control_bank_sha256": "experiments/discovery/v06_controls_001/control_banks.json",
        "control_bank_freeze_sha256": "experiments/discovery/v06_controls_001/freeze_receipt.json",
        "kernel_config_sha256": "configs/repair_train_v06_001.json",
        "relabel_config_sha256": "configs/relabel_refinement_v06_002.json",
        "published_EoH_addon_registration_sha256": "experiments/discovery/v06_published_eoh_heldout_addon_001/freeze_receipt.json",
        "published_EoH_selection_sha256": f"{EOH}/selection.json",
        "published_EoH_authoring_audit_sha256": f"{EOH}/audit/authoring_audit.json",
        "published_EoH_TRAIN_audit_sha256": f"{EOH}/audit/train_audit.json",
        "audit_schema_review_sha256": f"{ANALYSIS}/audit_schema_adapter_review_v06_001.json",
        "independent_audit_schema_adapter_sha256": "scripts/normalize_audit_receipt_v06.py",
        "TEST_certificate_execution_wrapper_sha256": "scripts/run_evidence_test_server_v06.py",
    }


def verify_schema_receipts():
    originals = {}
    for stem in AUDIT_STEMS:
        p = ROOT / ANALYSIS / (stem + ".json")
        original = read(p)
        adapted = read(ROOT / ANALYSIS / (stem + "_scalar_receipt_001.json"))
        if (adapted["original_check_categories"] != original["checks"]
                or adapted["original_error_records"] != original["errors"]
                or original["errors"] != []
                or adapted["checks"] != original["total_checks"]
                or adapted["errors"] != 0
                or adapted["schema_adapter"]["original_report_sha256"] != digest(p)
                or adapted["schema_adapter"]["adapter_source_sha256"] != digest(ROOT / "scripts/normalize_audit_receipt_v06.py")):
            raise ValueError("Lossless independent-report schema binding failed: " + stem)
        for key in original:
            if key not in ("checks", "errors") and adapted.get(key) != original[key]:
                raise ValueError("Original independent finding changed: " + stem + ":" + key)
        originals[stem + ".json"] = digest(p)
    review = read(ROOT / ANALYSIS / "audit_schema_adapter_review_v06_001.json")
    if (review.get("errors") not in (0, []) or review.get("schema_only_approved") is not True
            or review.get("adapter_source_sha256") != digest(ROOT / "scripts/normalize_audit_receipt_v06.py")):
        raise ValueError("Independent schema-only review has not approved these exact bytes")
    return originals


def main_receipt():
    from cipheur import heldout_refinement_v06 as r2
    from cipheur import heldout_published_eoh_v06 as addon
    r2._check_runtime()
    addon.check_runtime()
    paths = bound_paths()
    bindings = {key: digest(ROOT / path) for key, path in paths.items()}
    originals = verify_schema_receipts()
    selected = read(ROOT / TRAIN / "selection.json")
    r2.validate_selected(selected)
    completion = read(ROOT / R2 / "authoring_completion.json")
    assessed = read(ROOT / TRAIN / "complete.json")
    if (completion.get("all15_R2_requests_frozen_before_assessment") is not True
            or len(completion.get("response_sha256", {})) != 15
            or completion.get("failed_transport_cells") != []
            or completion.get("no_TEST_access") is not True
            or assessed.get("all120_assessed") is not True or assessed.get("complete") is not True
            or assessed.get("TEST_queries") != 0 or assessed.get("selection_sha256") != bindings["selection_sha256"]):
        raise ValueError("Complete original R2 author/assessment freeze is required")
    for key in ("R2_TRAIN_audit_sha256", "R2_authoring_audit_sha256", "packet_audit_sha256"):
        r2._audit_passed(read(ROOT / paths[key]), key)
    protocol = read(ROOT / EOH / "protocol.json")
    published = read(ROOT / EOH / "selection.json")
    addon.validate_selection(published, digest(ROOT / EOH / "protocol.json"), protocol["shared_R1_warm_seed_sha256"])
    for key, phase in (("published_EoH_authoring_audit_sha256", "authoring"),
                       ("published_EoH_TRAIN_audit_sha256", "train")):
        addon.audit_passed(read(ROOT / paths[key]), phase, bindings["published_EoH_selection_sha256"],
                           digest(ROOT / EOH / "protocol.json"))
    programs = [p for p in selected["programs"] if p["role"] == "proposed_witness_joint"]
    if len(programs) != 4:
        raise ValueError("Four genuine frozen W joint programmes are mandatory")
    receipt = {
        "version": "v06_R2_root_TEST_release_002", "issued_by": "root",
        "issued_utc": datetime.now(timezone.utc).isoformat(),
        "allow_TEST": True, "before_any_TEST_labels_or_performance": True,
        "all15_R2_requests_frozen_before_assessment": True, "all120_original_slots_assessed": True,
        "independent_R2_TRAIN_audit_zero_errors": True, "authoring_completion_verified": True,
        "proposed_witness_joint_count": 4, "R1_barrier_remains_failed": True,
        "matched_transport_complete_blocks": selected["matched_transport_complete_blocks"],
        "original_runtime_sha256": r2.ORIGINAL_RUNTIME_SHA256,
        "R2_heldout_source_sha256": r2.source_hashes(),
        "published_EoH_all32_and4_seed_fitness_frozen_before_TEST": True,
        "published_EoH_addon_source_sha256": addon.source_hashes(),
        "selection_split": "train", "test_accessed": False, "programs": programs,
        "original_independent_audit_sha256": originals,
        "metadata_helper_sha256": digest(__file__),
        "scope": "Authorizes only the predeclared frozen TEST protocols; no new authoring, selection or efficacy claim.",
        **bindings}
    r2.validate_release(receipt, bindings, selected)
    return receipt


def issue(path):
    path = Path(path)
    if path.exists():
        raise ValueError("Root releases are immutable and cannot be replaced")
    receipt = main_receipt()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return {"root_release": str(path), "sha256": digest(path), "before_any_TEST_labels_or_performance": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-main", metavar="NEW_ROOT_RECEIPT")
    args = parser.parse_args()
    if args.issue_main:
        print(json.dumps(issue(args.issue_main)))
    else:
        paths = bound_paths()
        missing = {key: path for key, path in paths.items() if not (ROOT / path).is_file()}
        print(json.dumps({"release_issued": False, "missing_final_bindings": missing,
                          "TEST_labels_read": False, "TEST_execution": False}, ensure_ascii=False))
