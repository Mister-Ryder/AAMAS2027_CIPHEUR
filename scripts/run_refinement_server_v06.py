"""Immutable server-only R2 TRAIN assessment; no new evidence or TEST access.

The entire fifteen-request authoring batch and its independent transport audit
must be frozen before packaging. Original R1 sources and barriers are retained.
The new R2 selector has explicit genuine-proposed and nonguarded-comparator roles.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STEM = "refinement_train_server_v06_002"
STAGE = ROOT / "experiments/discovery" / STEM
CAPSULE = ROOT / "experiments/source_snapshots/v06" / (STEM + "_source.zip")
STUDY = "experiments/discovery/v06_refinement_draft_003"
AUDIT = "experiments/analysis/v06/refinement_authoring_audit_v06_002.json"
AUDITOR = "scripts/verify_refinement_authoring_v06.py"
SOURCES = ["scripts/run_refinement_server_v06.py", AUDITOR,
    "scripts/author_refinement_cli_v06.py", "scripts/author_matched_cli_v06.py",
    "scripts/verify_refinement_packets_v06.py", "scripts/verify_authoring_v06.py",
    "scripts/verify_matched_llm_v05.py",
    "scripts/verify_public_alias_v05.py", "configs/refinement_selection_v06_002.json",
    "experiments/analysis/v06/refinement_packet_audit_v06_002.json"] + ["cipheur/" + name for name in
    ("__init__.py", "model.py", "programs.py", "graph_features.py", "compiled.py",
     "repair_v06.py", "synthesis_study_v06.py", "refinement_study_v06.py",
     "refinement.py", "representation.py")]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())


def validate_authoring_audit(audit):
    """Require a review of exactly these completed authoring inputs."""
    if audit.get("error_count") != 0 or audit.get("raw_slot_count") != 120:
        raise ValueError("Independent R2 authoring audit must cover all120 slots without errors")
    if audit.get("errors") not in (0, []):
        raise ValueError("Independent R2 authoring audit has unresolved findings")
    bindings = audit["source_and_receipt_bindings"]
    required = {AUDITOR, STUDY + "/protocol.json", STUDY + "/authoring_completion.json",
        STUDY + "/transport_runtime_binding.json"}
    required.update(STUDY + f"/receipts/block_{b}_{a}.receipt.json"
        for b in range(5) for a in ("witness", "relations", "objective"))
    required.update(STUDY + f"/responses/block_{b}_{a}.json"
        for b in range(5) for a in ("witness", "relations", "objective"))
    if not required <= bindings.keys():
        raise ValueError("Audit must bind its source, all15 responses and completion/transport receipts")
    for name, expected in bindings.items():
        if digest(ROOT / name) != expected:
            raise ValueError("Independently reviewed bytes changed: " + name)


def package():
    if STAGE.exists() or CAPSULE.exists():
        raise ValueError("Never replace the original R2 assessment capsule")
    completion = json.loads((ROOT / STUDY / "authoring_completion.json").read_bytes())
    if not completion["all15_R2_requests_frozen_before_assessment"]:
        raise ValueError("All15 requests must finish before candidate inspection")
    audit = json.loads((ROOT / AUDIT).read_bytes())
    validate_authoring_audit(audit)
    from cipheur.refinement_study_v06 import load_bank
    proto, bank, _, matched = load_bank(ROOT / STUDY)
    if len(bank) != 120 or matched != audit["matched_transport_complete_blocks"]:
        raise ValueError("Bank/cohort differs from the independent authoring audit")
    files = list(SOURCES) + [AUDIT]
    files.extend(p.relative_to(ROOT).as_posix() for p in (ROOT / STUDY).rglob("*") if p.is_file())
    missing = [name for name in files if not (ROOT / name).is_file()]
    if missing:
        raise ValueError("Missing R2 assessment input: " + repr(missing))
    file_hashes = {name: digest(ROOT / name) for name in sorted(set(files))}
    STAGE.mkdir(parents=True); CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in file_hashes:
            archive.write(ROOT / name, name)
    write(STAGE / "registration.json", {"version": STEM,
        "before_any_R2_candidate_assessment": True, "all15_R2_raw_sessions_frozen": True,
        "all120_R2_raw_slots_retained": True, "matched_transport_complete_blocks": matched,
        "assessment_split": "train", "workers": 8, "whole_phase_wall_guard_seconds": 7200,
        "file_sha256": file_hashes, "source_zip_sha256": digest(CAPSULE),
        "authoring_audit_sha256": digest(ROOT / AUDIT),
        "completion_sha256": digest(ROOT / STUDY / "authoring_completion.json"),
        "R2_protocol_sha256": digest(ROOT / STUDY / "protocol.json"),
        "R2_selection_plan_sha256": proto["selection_plan_sha256"],
        "R1_twelve_genuine_barrier_remains_failed": True, "R1_sources_unchanged": True,
        "TEST_accessed": False, "model_calls": 0, "oracle_calls": 0, "query_retries": 0})
    print(json.dumps({"source_zip": str(CAPSULE), "source_zip_sha256": digest(CAPSULE),
        "registration_sha256": digest(STAGE / "registration.json"), "files": len(file_hashes)}), flush=True)


def server_run():
    if platform.system() != "Linux":
        raise ValueError("Research assessment is server-only")
    registration = json.loads((STAGE / "registration.json").read_bytes())
    if digest(CAPSULE) != registration["source_zip_sha256"]:
        raise ValueError("Frozen R2 capsule changed")
    for name, expected in registration["file_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen R2 assessment input changed: " + name)
    host = STAGE / "host_receipt.json"
    if host.exists():
        raise ValueError("Preserve the original server execution")
    started = time.perf_counter()
    write(host, {"platform": platform.platform(), "python": sys.version,
        "pid": os.getpid(), "timestamp_unix": time.time(), "workers": 8,
        "cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        "registration_sha256": digest(STAGE / "registration.json")})
    output = ROOT / "output" / STEM
    output.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    before = time.perf_counter(); guard = False
    command = [sys.executable, "-m", "cipheur.refinement_study_v06", "--study", STUDY,
        "--out", str(output / "llm"), "--workers", "8"]
    with (output / "LLM.log").open("xb") as stream:
        child = subprocess.Popen(command, cwd=ROOT, env=env,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        write(output / "LLM_launch.json", {"phase": "R2_LLM_TRAIN", "pid": child.pid,
            "workers": 8, "timestamp_unix": time.time(), "no_TEST_access": True})
        try:
            code = child.wait(timeout=registration["whole_phase_wall_guard_seconds"])
        except subprocess.TimeoutExpired:
            guard = True; os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL); code = child.wait()
    receipt = {"phase": "R2_LLM_TRAIN", "exit_code": code,
        "whole_phase_guard_triggered": guard, "wall_seconds": time.perf_counter() - before,
        "no_retry": True, "partial_original_outcomes_retained": True}
    write(output / "phase_receipts.json", [receipt])
    for name in ("registration.json", "host_receipt.json"):
        (output / name).write_bytes((STAGE / name).read_bytes())
    complete = not code and not guard
    write(output / "server_execution_receipt.json", {"execution_complete": complete,
        "full_batch_wall_seconds": time.perf_counter() - started,
        "registration_sha256": digest(STAGE / "registration.json"),
        "source_zip_sha256": digest(CAPSULE), "phases": [receipt],
        "TEST_queries": 0, "online_model_calls": 0, "oracle_calls": 0, "no_retries": True})
    destination = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "x:gz") as archive:
        archive.add(output, arcname=STEM)
    write(STAGE / "archive_receipt.json", {"archive_sha256": digest(destination),
        "archive_bytes": destination.stat().st_size, "execution_complete": complete})
    print(json.dumps(json.loads((STAGE / "archive_receipt.json").read_bytes())), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("package", "server-run"))
    args = parser.parse_args(); {"package": package, "server-run": server_run}[args.mode]()
