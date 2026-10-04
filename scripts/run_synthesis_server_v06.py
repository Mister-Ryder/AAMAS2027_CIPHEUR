"""Package and execute frozen V06 LLM/control TRAIN assessments on the server.

All15 authoring requests must be finished and independently audited. Each raw
slot is assessed once; no author, candidate repair, TEST query or TEST selection
is invoked. The two eight-worker phases run sequentially.
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
STEM = "synthesis_train_server_v06_001"
STAGE = ROOT / "experiments/discovery" / STEM
CAPSULE = ROOT / "experiments/source_snapshots/v06" / (STEM + "_source.zip")
PARENT = "experiments/discovery/v06_authoring_001"
SUPPLEMENT = "experiments/discovery/v06_authoring_supplement_001"
CONTROLS = "experiments/discovery/v06_controls_001"
CONTROL_REG = "experiments/discovery/v06_control_assessment_001"
AUDIT = "experiments/analysis/v06/authoring_reviewed_audit_v06_001.json"
FIRST_AUDIT = "experiments/analysis/v06/authoring_audit_v06_001.json"
SOURCES = ["scripts/run_synthesis_server_v06.py", "scripts/verify_authoring_v06.py",
    "scripts/review_authoring_v06.py", "scripts/verify_matched_llm_v05.py",
    "scripts/verify_public_alias_v05.py"] + ["cipheur/" + name for name in
    ("__init__.py", "model.py", "programs.py", "graph_features.py", "compiled.py",
     "repair_v06.py", "synthesis_study_v06.py", "synthesis_extension_v06.py",
     "control_assessment_v06.py", "refinement.py", "representation.py")]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())


def package():
    if STAGE.exists() or CAPSULE.exists():
        raise ValueError("Never replace the original assessment capsule")
    # Frozen response content may be read only after both completion receipts.
    for directory in (PARENT, SUPPLEMENT):
        completion = json.loads((ROOT / directory / "authoring_completion.json").read_bytes())
        if not completion["all_authoring_completed_before_assessment"]:
            raise ValueError("Authoring not fully frozen")
    audit = json.loads((ROOT / AUDIT).read_bytes())
    if audit.get("errors") not in (0, []) or audit.get("error_count") != 0 or audit.get("raw_slot_count") != 120:
        raise ValueError("Independent authoring audit must have zero errors")
    from cipheur.synthesis_extension_v06 import load_extended_bank
    _, bank, _, matched = load_extended_bank(ROOT / PARENT, ROOT / SUPPLEMENT)
    if len(bank) != 120:
        raise ValueError("Retain all120 original positions")
    if matched != audit["matched_transport_complete_blocks"]:
        raise ValueError("Transport cohort differs from independently reviewed receipt")
    for key, path in (("parent_completion_sha256", ROOT / PARENT / "authoring_completion.json"),
                      ("supplement_completion_sha256", ROOT / SUPPLEMENT / "authoring_completion.json"),
                      ("parent_protocol_sha256", ROOT / PARENT / "protocol.json"),
                      ("supplement_protocol_sha256", ROOT / SUPPLEMENT / "protocol.json"),
                      ("initial_audit_sha256", ROOT / FIRST_AUDIT),
                      ("audit_script_sha256", ROOT / "scripts/verify_authoring_v06.py"),
                      ("review_script_sha256", ROOT / "scripts/review_authoring_v06.py")):
        if digest(path) != audit["metadata"][key]:
            raise ValueError("Independent review attests changed bytes: " + key)
    for name, expected in audit["source_and_receipt_bindings"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Reviewed source/receipt changed: " + name)
    files = list(SOURCES) + [AUDIT, FIRST_AUDIT]
    for directory in (PARENT, SUPPLEMENT, CONTROLS, CONTROL_REG):
        files.extend(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob("*") if p.is_file())
    missing = [name for name in files if not (ROOT / name).is_file()]
    if missing:
        raise ValueError("Missing runtime sources: " + repr(missing))
    file_hashes = {name: digest(ROOT / name) for name in sorted(set(files))}
    STAGE.mkdir(parents=True); CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in file_hashes:
            archive.write(ROOT / name, name)
    write(STAGE / "registration.json", {"version": STEM,
        "before_any_candidate_assessment": True, "all15_raw_sessions_frozen": True,
        "all120_raw_slots_retained": True, "matched_transport_complete_blocks": matched,
        "assessment_split": "train", "workers": 8, "sequential_LLM_and_control_phases": True,
        "whole_phase_wall_guard_seconds": 7200, "file_sha256": file_hashes,
        "source_zip_sha256": digest(CAPSULE), "authoring_audit_sha256": digest(ROOT / AUDIT),
        "parent_completion_sha256": digest(ROOT / PARENT / "authoring_completion.json"),
        "supplement_completion_sha256": digest(ROOT / SUPPLEMENT / "authoring_completion.json"),
        "TEST_accessed": False, "model_calls": 0, "oracle_calls": 0, "query_retries": 0})
    print(json.dumps({"source_zip": str(CAPSULE), "source_zip_sha256": digest(CAPSULE),
        "registration_sha256": digest(STAGE / "registration.json"), "files": len(file_hashes)}), flush=True)


def server_run():
    if platform.system() != "Linux":
        raise ValueError("Research assessment is server-only")
    registration = json.loads((STAGE / "registration.json").read_bytes())
    if digest(CAPSULE) != registration["source_zip_sha256"]:
        raise ValueError("Frozen capsule changed")
    for name, expected in registration["file_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen assessment input changed: " + name)
    host = STAGE / "host_receipt.json"
    if host.exists():
        raise ValueError("Preserve original server execution")
    started = time.perf_counter()
    write(host, {"platform": platform.platform(), "python": sys.version,
        "pid": os.getpid(), "timestamp_unix": time.time(), "workers": 8,
        "cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        "registration_sha256": digest(STAGE / "registration.json")})
    output = ROOT / "output" / STEM
    output.mkdir(parents=True, exist_ok=False)
    phases = [
        ("LLM", ["-m", "cipheur.synthesis_extension_v06", "--parent", PARENT,
            "--supplement", SUPPLEMENT, "--out", str(output / "llm"), "--workers", "8"]),
        ("controls", ["-m", "cipheur.control_assessment_v06", "train", "--parent", PARENT,
            "--supplement", SUPPLEMENT, "--controls", CONTROLS, "--registration", CONTROL_REG,
            "--out", str(output / "controls"), "--workers", "8"])]
    receipts = []
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    for phase, command in phases:
        before = time.perf_counter(); guard = False
        with (output / (phase + ".log")).open("xb") as stream:
            child = subprocess.Popen([sys.executable, *command], cwd=ROOT, env=env,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            write(output / (phase + "_launch.json"), {"phase": phase, "pid": child.pid,
                "workers": 8, "timestamp_unix": time.time(), "no_TEST_access": True})
            try:
                code = child.wait(timeout=registration["whole_phase_wall_guard_seconds"])
            except subprocess.TimeoutExpired:
                guard = True; os.killpg(child.pid, signal.SIGTERM)
                try:
                    code = child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); code = child.wait()
        receipts.append({"phase": phase, "exit_code": code, "whole_phase_guard_triggered": guard,
            "wall_seconds": time.perf_counter() - before, "no_retry": True,
            "partial_original_outcomes_retained": True})
        write(output / "phase_receipts.json", receipts)
        if code or guard:
            break
    for name in ("registration.json", "host_receipt.json"):
        (output / name).write_bytes((STAGE / name).read_bytes())
    complete = len(receipts) == 2 and all(not r["exit_code"] and not r["whole_phase_guard_triggered"] for r in receipts)
    write(output / "server_execution_receipt.json", {"execution_complete": complete,
        "full_batch_wall_seconds": time.perf_counter() - started,
        "registration_sha256": digest(STAGE / "registration.json"),
        "source_zip_sha256": digest(CAPSULE), "phases": receipts,
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
    args = parser.parse_args()
    {"package": package, "server-run": server_run}[args.mode]()
