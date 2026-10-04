"""Separate frozen EoH TEST addon; original R2 registration stays immutable.

Register only static sources/plans before TEST. Prepare/run require a root addon
release binding the final four TRAIN outputs and independent audits; reuse the
original prepared R2 certificate/mapping inventory without oracle calls.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
import json
from pathlib import Path
import platform
import shutil
import time

from . import heldout_mechanism_v06 as original
from . import heldout_refinement_v06 as r2
from .graph_features import FeatureRuleProgram
from .synthesis_study_v06 import canonical, digest, write


R2_ADAPTER_SHA256 = "1e8bd6a2577eabe8e33a73edc1303358f09cdbfc1c5c53604eaf91db3380ef1a"
EOH_AUTHOR_RELEASE_SHA256 = "6f3a7059c92bebbf2905cdf51a9eda681a73d8990f3f254fc567c3b461ad9c35"
SOURCE_NAMES = r2.SOURCE_NAMES + ("heldout_published_eoh_v06.py",)
IDENTITIES = [f"published_EoH_DSL_quality:run_{i}" for i in range(4)]
VARIANTS = ["original"] + [f"relabel_{i}" for i in range(5)]
SALT = "V06_RELABEL_ROBUSTNESS_20261004_001"
ROLE_SCOPE = {
    "role": "Four nonguarded TRAIN-only published EoH-DSL quality pipeline positions",
    "origins": "Seed-origin, genuine authored origin, missing and duplicate AST identities retained",
    "selection": "No TEST selection, no certificate gate for the published quality comparator",
    "contrast": "W-joint versus EoH combines evidence, generation, selection and compute differences",
    "prototype": "Bounded seeded DSL adaptation, not unrestricted native EoH reproduction",
    "dependence": "Paired endpoints, five relabels and duplicate policies are not independent samples",
    "classical": "Identical shared classical initialization/repair is not a new LLM contribution",
}


def read(path):
    return json.loads(Path(path).read_bytes())


def bound(path, expected):
    return original._bound_read(path, expected)


def source_hashes():
    return {n: digest(Path(__file__).parent / n) for n in SOURCE_NAMES}


LOADED_SOURCE_HASHES = source_hashes()


def check_runtime(expected=None):
    r2._check_runtime()
    current = source_hashes()
    if (current != LOADED_SOURCE_HASHES or current["heldout_refinement_v06.py"] != R2_ADAPTER_SHA256
        or (expected is not None and current != expected)):
        raise ValueError("Frozen EoH addon/runtime changed")


def linux_only():
    if platform.system() != "Linux":
        raise ValueError("Published EoH heldout preparation/execution is Linux-only")


def validate_selection(selection, protocol_sha256, seed_sha256):
    if (selection.get("version") != "v06_published_EoH_DSL_TRAIN_quality_selection_001"
        or selection.get("all32_positions_frozen") is not True
        or selection.get("requested_positions") != 32 or selection.get("TEST_accessed") is not False
        or selection.get("no_retry_or_fallback_authored_output") is not True
        or selection.get("protocol_sha256") != protocol_sha256
        or selection.get("root_authoring_release_sha256") != EOH_AUTHOR_RELEASE_SHA256):
        raise ValueError("Complete frozen TRAIN-only EoH pipeline selection required")
    positions = selection.get("original_positions", [])
    expected = [(r, s, f"run_{r}_slot_{s}") for r in range(4) for s in range(8)]
    if len(positions) != 32 or [(p["run"], p["slot"], p["id"]) for p in positions] != expected:
        raise ValueError("All32 original EoH author positions must remain ordered and retained")
    programs = selection.get("programs", [])
    if len(programs) != 4 or [p["id"] for p in programs] != IDENTITIES:
        raise ValueError("Exactly four ordered EoH pipeline positions required")
    entries = []
    for run, p in enumerate(programs):
        if (p.get("run") != run or p.get("role") != "nonguarded_published_quality_baseline"
            or p.get("joint_gate_required") is not False
            or p.get("TRAIN_label_selected_seed_history") is not True
            or p.get("gate_fit_not_used_for_selection") is not True):
            raise ValueError("EoH origin/quality-only role changed")
        missing = p.get("winner_origin") == "missing"
        if missing:
            if any(p.get(k) is not None for k in ("program", "program_sha256", "source_id")):
                raise ValueError("Missing EoH output must remain null without a fallback")
        else:
            raw = FeatureRuleProgram.from_dict(p["program"]).to_dict()
            if raw != p["program"] or canonical(raw) != p["program_sha256"]:
                raise ValueError("Frozen EoH program changed during parsing")
            origin = p.get("winner_origin")
            if origin == "shared_R1_warm_seed":
                if p["source_id"] != f"run_{run}:warm_seed" or p["program_sha256"] != seed_sha256:
                    raise ValueError("Shared seed origin/program binding changed")
            elif origin == "genuine_EoH_author_slot":
                if p["source_id"] not in {f"run_{run}_slot_{s}" for s in range(8)}:
                    raise ValueError("Authored EoH origin must be an original slot in the same run")
            else:
                raise ValueError("Unknown EoH winner origin")
        entries.append({**p, "priority": None if missing else "program", "missing_baseline": missing,
                        "main_comparison": True, "joint_gate_not_required": True})
    return entries


def audit_passed(audit, phase, selection_sha256, protocol_sha256):
    checks = audit.get("checks")
    if isinstance(checks, dict):
        checks = sum(checks.values()) if all(type(v) is int for v in checks.values()) else None
    if (type(checks) is not int or checks < 1 or audit.get("errors") not in (0, [])
        or audit.get("audit_phase") != phase or audit.get("selection_sha256") != selection_sha256
        or audit.get("protocol_sha256") != protocol_sha256
        or audit.get("root_authoring_release_sha256") != EOH_AUTHOR_RELEASE_SHA256
        or audit.get("all32_positions_frozen") is not True or audit.get("TEST_accessed") is not False):
        raise ValueError("Independent complete zero-error EoH audit required: " + phase)


def validate_release(release, bindings):
    if (release.get("version") != "v06_published_EoH_root_TEST_addon_release_001"
        or release.get("issued_by") != "root" or release.get("allow_TEST") is not True
        or release.get("before_any_addon_TEST_label_read_or_programme_evaluation") is not True
        or release.get("EoH_bank_and_audits_frozen_before_original_TEST_queries") is not True
        or release.get("all32_author_positions_and4_seed_fitness_frozen") is not True
        or release.get("independent_EoH_author_and_TRAIN_audits_zero_errors") is not True
        or release.get("requested_published_identities") != 4
        or release.get("original_R2_27_identities_roles_hashes_unchanged") is not True):
        raise ValueError("Root addon release after complete independent TRAIN/author audits required")
    for key, expected in bindings.items():
        if release.get(key) != expected:
            raise ValueError("Root addon release binding changed: " + key)


def register(config, eoh_study, evidence_plan, r2_relabel_config, out):
    """Read static registrations only, never EoH calls/fitness or TEST records."""
    out, study, plan = Path(out), Path(eoh_study), Path(evidence_plan)
    if out.exists():
        raise ValueError("Never overwrite the outcome-free addon registration")
    check_runtime()
    cfg, ep, ef, relabel = (read(p) for p in (config, study / "protocol.json", plan / "freeze_receipt.json", r2_relabel_config))
    if (cfg.get("version") != "v06_published_EoH_pre_TEST_heldout_addon_001"
        or cfg.get("registered_before_any_EoH_TEST_labels_or_programme_evaluation") is not True
        or cfg.get("requested_identities") != 4 or cfg.get("identity_order") != IDENTITIES
        or cfg.get("variants") != VARIANTS or cfg.get("permutations_per_source") != 5
        or cfg.get("requested_state_assignments") != 1728 or cfg.get("salt") != SALT
        or type(cfg.get("workers")) is not int or not 1 <= cfg["workers"] <= 8
        or relabel.get("salt") != SALT or relabel.get("permutations_per_source") != 5
        or relabel.get("requested_identities") != 27
        or ep.get("version") != "v06_published_EoH_DSL_001" or ep.get("split") != "train"
        or ep.get("requested_positions") != 32 or ep.get("TEST_accessed") is not False
        or ep.get("feedback_certificate_access") is not False):
        raise ValueError("Static pre-TEST addon/EoH/R2 registration changed")
    if digest(study / "root_authoring_release.json") != EOH_AUTHOR_RELEASE_SHA256:
        raise ValueError("Original EoH authoring release binding changed")
    frozen_directory(study, digest(study / "freeze_receipt.json"))
    if (digest(plan / "data.json") != ef["data_sha256"] or digest(plan / "protocol.json") != ef["protocol_sha256"]
        or read(plan / "protocol.json")["counts"]["test"] != 72):
        raise ValueError("Original frozen 72-state query frame changed")
    files = {"config.json": config, "EoH_protocol.json": study / "protocol.json",
        "EoH_freeze.json": study / "freeze_receipt.json", "EoH_author_release.json": study / "root_authoring_release.json",
        "evidence_freeze.json": plan / "freeze_receipt.json", "evidence_protocol.json": plan / "protocol.json",
        "R2_relabel_config.json": r2_relabel_config}
    protocol = {"version": "v06_published_EoH_heldout_addon_registration_001", "before_any_EoH_TEST_access": True,
        "requested_identities": 4, "requested_state_assignments": 1728, "identity_order": IDENTITIES,
        "variants": VARIANTS, "workers": cfg["workers"], "salt": SALT, "source_sha256": source_hashes(),
        "R2_source_sha256": r2.source_hashes(), "original_helper_sha256": original.source_hashes(),
        "original_data_sha256": ef["data_sha256"], "original_query_protocol_sha256": ef["protocol_sha256"],
        "EoH_protocol_sha256": digest(study / "protocol.json"), "EoH_seed_program_sha256": ep["shared_R1_warm_seed_sha256"],
        "EoH_kernel_config_sha256": ep["kernel_config_sha256"],
        "EoH_author_release_sha256": EOH_AUTHOR_RELEASE_SHA256, "role_scope": ROLE_SCOPE,
        "all_prior_R2_roles_and_27_identities_unchanged": True, "extra_oracle_calls": 0,
        "static_input_sha256": {name: digest(path) for name, path in files.items()}}
    out.mkdir(parents=True)
    for name, path in files.items():
        shutil.copyfile(path, out / name)
    for name in SOURCE_NAMES:
        dest = out / "source_snapshot" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).parent / name, dest)
    write(out / "protocol.json", protocol)
    write(out / "freeze_receipt.json", {"before_any_EoH_TEST_labels_or_programme_evaluation": True,
        "artifact_sha256": {p.relative_to(out).as_posix(): digest(p) for p in sorted(out.rglob("*")) if p.is_file()},
        "source_sha256": source_hashes()})
    return {"registration": str(out), "requested_state_assignments": 1728, "TEST_accessed": False}


def frozen_directory(directory, expected_freeze_sha256):
    directory = Path(directory)
    freeze = bound(directory / "freeze_receipt.json", expected_freeze_sha256)
    for name, sha in freeze["artifact_sha256"].items():
        if digest(directory / name.replace("\\", "/")) != sha:
            raise ValueError("Registered input/source bytes changed: " + name)
    return freeze


def prepare(registration, registration_sha256, r2_registration, r2_freeze_sha256, selection, selection_sha256,
            authoring_audit, train_audit, root_release, root_release_sha256, out):
    linux_only()
    out, registration, parent = map(Path, (out, registration, r2_registration))
    if out.exists():
        raise ValueError("Never overwrite an EoH heldout preparation")
    frozen = frozen_directory(registration, registration_sha256)
    check_runtime(frozen["source_sha256"])
    proto = read(registration / "protocol.json")
    selected = bound(selection, selection_sha256)
    entries = validate_selection(selected, proto["EoH_protocol_sha256"], proto["EoH_seed_program_sha256"])
    for path, phase in ((authoring_audit, "authoring"), (train_audit, "train")):
        audit_passed(read(path), phase, selection_sha256, proto["EoH_protocol_sha256"])
    # This release check deliberately precedes every prepared TEST label/input read.
    bindings = {"addon_registration_sha256": registration_sha256, "EoH_selection_sha256": selection_sha256,
        "R2_registration_freeze_sha256": r2_freeze_sha256,
        "EoH_authoring_audit_sha256": digest(authoring_audit), "EoH_TRAIN_audit_sha256": digest(train_audit),
        "EoH_protocol_sha256": proto["EoH_protocol_sha256"], "EoH_author_release_sha256": EOH_AUTHOR_RELEASE_SHA256,
        "original_data_sha256": proto["original_data_sha256"], "original_query_protocol_sha256": proto["original_query_protocol_sha256"],
        "addon_source_sha256": source_hashes()}
    release = bound(root_release, root_release_sha256)
    validate_release(release, bindings)
    parent_freeze = frozen_directory(parent, r2_freeze_sha256)
    pp = read(parent / "protocol.json")
    parent_selected = read(parent / "selection.json")
    r2.validate_selected(parent_selected)
    main_release = bound(parent / "root_release.json", pp["root_release_sha256"])
    r2.validate_release(main_release, pp["release_bindings"], parent_selected)
    main_eoh_bindings = {"published_EoH_addon_registration_sha256": registration_sha256,
        "published_EoH_selection_sha256": selection_sha256,
        "published_EoH_authoring_audit_sha256": digest(authoring_audit),
        "published_EoH_TRAIN_audit_sha256": digest(train_audit), "published_EoH_addon_source_sha256": source_hashes()}
    if (main_release.get("published_EoH_all32_and4_seed_fitness_frozen_before_TEST") is not True
        or any(main_release.get(k) != v for k, v in main_eoh_bindings.items())):
        raise ValueError("Main root release must bind completed EoH bank/audits/static addon before original TEST queries")
    if (parent_freeze.get("before_any_R2_TEST_programme_evaluation") is not True
        or pp.get("requested_identities") != 27 or len(pp.get("entries", [])) != 27
        or pp.get("source_sha256") != proto["R2_source_sha256"]
        or pp.get("original_helper_sha256") != proto["original_helper_sha256"]
        or pp.get("original_data_sha256") != proto["original_data_sha256"]
        or pp.get("original_query_protocol_sha256") != proto["original_query_protocol_sha256"]
        or pp.get("variants") != VARIANTS or pp.get("all_original_states") != 72
        or digest(parent / "kernel_config.json") != proto["EoH_kernel_config_sha256"]
        or pp.get("kernel_config") != read(parent / "kernel_config.json")
        or pp.get("interface_limits") != original.DEFAULT_INTERFACE_LIMITS
        or release.get("R2_root_release_sha256") != pp["root_release_sha256"]
        or release.get("R2_selection_sha256") != pp["selection_sha256"]):
        raise ValueError("Original root-released R2 identities/input/runtime binding changed")
    records = read(parent / "test_inputs.json")["records"]
    labels = read(parent / "test_certificates.json")["labels"]
    original.validate_test_labels(records, labels)
    if len(records) != 72 or read(parent / "relabel_config.json")["salt"] != SALT:
        raise ValueError("All72 original states and original relabel salt required")
    planned = read(parent / "relabel_inventory.json")
    if [p["index"] for p in planned] != list(range(5)) or [p["variant"] for p in planned] != VARIANTS[1:]:
        raise ValueError("Allfive original relabel mappings required")
    for p in planned:
        rs, _, mapping = original.relabel_inventory(records, labels, p["index"], SALT)
        if mapping != p["mappings"] or {r["id"]: r["graph_digest"] for r in rs} != p["graph_digests"]:
            raise ValueError("Original R2 paired relabel mapping changed")
    out.mkdir(parents=True)
    copies = {"root_release.json": root_release, "EoH_selection.json": selection,
        "EoH_authoring_audit.json": authoring_audit, "EoH_TRAIN_audit.json": train_audit,
        "addon_registration.json": registration / "protocol.json", "addon_registration_freeze.json": registration / "freeze_receipt.json",
        "R2_freeze.json": parent / "freeze_receipt.json", "R2_protocol.json": parent / "protocol.json",
        "R2_root_release.json": parent / "root_release.json", "R2_selection.json": parent / "selection.json",
        "test_inputs.json": parent / "test_inputs.json", "test_certificates.json": parent / "test_certificates.json",
        "relabel_inventory.json": parent / "relabel_inventory.json", "relabel_config.json": parent / "relabel_config.json"}
    for name, path in copies.items():
        shutil.copyfile(path, out / name)
    for name in SOURCE_NAMES:
        dest = out / "source_snapshot" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).parent / name, dest)
    present = sum(not e["missing_baseline"] for e in entries)
    protocol = {**proto, "version": "v06_published_EoH_heldout_addon_execution_001", "split": "test",
        "entries": entries, "release_bindings": bindings, "root_release_sha256": root_release_sha256,
        "R2_registration_freeze_sha256": r2_freeze_sha256, "R2_root_release_sha256": pp["root_release_sha256"],
        "R2_selection_sha256": pp["selection_sha256"], "EoH_selection_sha256": selection_sha256,
        "kernel_config": pp["kernel_config"], "interface_limits": pp["interface_limits"],
        "R2_test_certificate_sha256": pp["test_certificate_sha256"], "present_identities": present,
        "scorable_state_assignments": present * 432, "assignments": 24, "selection_performed": False}
    write(out / "protocol.json", protocol)
    write(out / "freeze_receipt.json", {"before_any_EoH_TEST_programme_evaluation": True,
        "root_release_sha256": root_release_sha256, "source_sha256": source_hashes(),
        "artifact_sha256": {p.relative_to(out).as_posix(): digest(p) for p in sorted(out.rglob("*")) if p.is_file()}})
    return {"prepared": str(out), "requested_state_assignments": 1728, "present_identities": present, "TEST_programme_evaluations": 0}


def evaluate_entry(task):
    entry, records, labels, protocol, variant = task
    check_runtime(protocol["source_sha256"])
    result = r2.evaluate_entry((entry, records, labels, {**protocol, "source_sha256": protocol["R2_source_sha256"]}, variant))
    result.update(role_scope=ROLE_SCOPE)
    return result


def run(registration, registration_sha256, out, root_release_sha256):
    linux_only()
    registration, out = Path(registration), Path(out)
    if out.exists():
        raise ValueError("Never overwrite EoH TEST observations")
    freeze = frozen_directory(registration, registration_sha256)
    check_runtime(freeze["source_sha256"])
    if (freeze.get("before_any_EoH_TEST_programme_evaluation") is not True
        or freeze.get("root_release_sha256") != root_release_sha256):
        raise ValueError("Frozen root-released EoH execution registration required")
    proto = read(registration / "protocol.json")
    validate_release(bound(registration / "root_release.json", root_release_sha256), proto["release_bindings"])
    entries = validate_selection(read(registration / "EoH_selection.json"), proto["EoH_protocol_sha256"], proto["EoH_seed_program_sha256"])
    if entries != proto["entries"] or proto["variants"] != VARIANTS or proto["requested_state_assignments"] != 1728:
        raise ValueError("Four assigned EoH identities and full variant frame changed")
    records, labels = read(registration / "test_inputs.json")["records"], read(registration / "test_certificates.json")["labels"]
    original.validate_test_labels(records, labels)
    if len(records) != 72:
        raise ValueError("Retain the full72 original states")
    variants = [("original", records, labels)]
    for p in read(registration / "relabel_inventory.json"):
        rs, ls, mapping = original.relabel_inventory(records, labels, p["index"], SALT)
        if mapping != p["mappings"] or {r["id"]: r["graph_digest"] for r in rs} != p["graph_digests"]:
            raise ValueError("Registered relabel mapping changed")
        variants.append((p["variant"], rs, ls))
    tasks = [(e, rs, ls, proto, v) for v, rs, ls in variants for e in entries]
    if [v[0] for v in variants] != VARIANTS or len(tasks) != 24 or sum(len(t[1]) for t in tasks) != 1728:
        raise ValueError("All24 identity/variant assignments and1728 state positions required")
    out.mkdir(parents=True)
    write(out / "execution.json", {"registration_sha256": registration_sha256, "root_release_sha256": root_release_sha256,
        "EoH_selection_sha256": proto["EoH_selection_sha256"], "R2_selection_sha256": proto["R2_selection_sha256"],
        "R2_test_certificate_sha256": proto["R2_test_certificate_sha256"], "source_sha256": source_hashes(),
        "split": "test", "workers": proto["workers"], "assignments": 24, "requested_state_assignments": 1728,
        "selection_performed": False, "extra_oracle_calls": 0, "role_scope": ROLE_SCOPE})
    rows, started = [], time.perf_counter()
    with (out / "results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=proto["workers"]) as pool:
            futures = {pool.submit(evaluate_entry, t): (t[0], t[-1]) for t in tasks}
            for f in as_completed(futures):
                e, v = futures[f]
                try:
                    row = f.result()
                except Exception as error:
                    row = {"id": e["id"], "identity": e, "variant": v, "split": "test", "kernel_rows": [],
                        "assignment_status": "worker_error", "worker_error_type": type(error).__name__, "worker_error": str(error),
                        "selection_performed": False, "extra_oracle_calls": 0, "role_scope": ROLE_SCOPE}
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); stream.flush()
                write(out / "progress.json", {"returned_assignments": len(rows), "assigned": 24, "last_id": e["id"], "last_variant": v})
    summary = []
    for e in entries:
        observed = {r["variant"]: r for r in rows if r["id"] == e["id"]}
        passed = [(observed[v].get("interface") or {}).get("strict_passed") for v in VARIANTS[1:]]
        totals = [(observed[v].get("interface") or {}).get("strict_total") for v in VARIANTS[1:]]
        qualities = [(observed[v].get("kernel_summary") or {}).get("macro_quality_exact") for v in VARIANTS]
        works = [(observed[v].get("kernel_summary") or {}).get("macro_work_exact") for v in VARIANTS]
        q5 = [Fraction(q) for q in qualities[1:]] if all(q is not None for q in qualities[1:]) else None
        summary.append({"id": e["id"], "identity": e, "missing_baseline": e["missing_baseline"],
            "original_strict_passed": (observed["original"].get("interface") or {}).get("strict_passed"),
            "original_strict_total": (observed["original"].get("interface") or {}).get("strict_total"),
            "all5_relabel_strict_passed": passed, "all5_relabel_strict_total": totals,
            "mean_relabel_strict_passed": sum(passed) / 5 if all(p is not None for p in passed) else None,
            "worst_relabel_strict_passed": min(passed) if all(p is not None for p in passed) else None,
            "all6_variant_macro_quality_exact": qualities, "all6_variant_macro_work_exact": works,
            "mean_relabel_macro_quality_exact": str(sum(q5, Fraction()) / 5) if q5 is not None else None,
            "worst_relabel_macro_quality_exact": str(min(q5)) if q5 is not None else None})
    write(out / "robustness_summary.json", summary)
    measured = [r for r in rows if r["assignment_status"] != "missing_quality_comparator"]
    write(out / "complete.json", {"execution_complete": len(rows) == 24, "split": "test", "returned_assignments": len(rows),
        "assigned": 24, "requested_state_assignments": 1728, "scorable_state_assignments": proto["scorable_state_assignments"],
        "missing_assignments": sum(r["assignment_status"] == "missing_quality_comparator" for r in rows),
        "worker_errors": sum("worker_error" in r for r in rows), "interface_errors": sum("interface_error" in r for r in measured),
        "kernel_errors": sum(r.get("kernel_coverage", {}).get("errors", 72) for r in measured),
        "results_sha256": digest(out / "results.jsonl"), "root_release_sha256": root_release_sha256,
        "actual_execution_wall_seconds": time.perf_counter() - started, "selection_performed": False,
        "extra_oracle_calls": 0, "no_fallback": True, "all_pairs_unknowns_quota_shortfalls_missing_positions_retained": True})
    return {"complete": str(out), "returned_assignments": len(rows), "requested_state_assignments": 1728}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("register")
    for name in ("config", "eoh-study", "evidence-plan", "r2-relabel-config", "out"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("prepare")
    for name in ("registration", "registration-sha256", "r2-registration", "r2-freeze-sha256", "selection", "selection-sha256",
                 "authoring-audit", "train-audit", "root-release", "root-release-sha256", "out"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("run")
    for name in ("registration", "registration-sha256", "out", "root-release-sha256"):
        p.add_argument("--" + name, required=True)
    args = vars(parser.parse_args()); mode = args.pop("mode")
    print(json.dumps(globals()[mode](**args), ensure_ascii=False))


if __name__ == "__main__":
    main()
