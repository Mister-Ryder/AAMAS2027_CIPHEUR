"""Server-only original72 TEST certificate execution under a prior root release.

The frozen original oracle/query implementation is unchanged. This wrapper
adds source/receipt binding, a whole-job failure guard and lossless archival;
it neither resamples queries nor changes a tie, interval, budget or outcome.
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

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def run(plan, out, release, release_sha256):
    if platform.system() != "Linux":
        raise ValueError("Real research execution is server/Linux only")
    plan, out, release = map(Path, (plan, out, release))
    if out.exists() or digest(release) != release_sha256:
        raise ValueError("Immutable new output and exact prior root-release bytes required")
    root = json.loads(release.read_bytes())
    if (root.get("version") != "v06_R2_root_TEST_release_002"
            or root.get("allow_TEST") is not True
            or root.get("before_any_TEST_labels_or_performance") is not True
            or root.get("published_EoH_all32_and4_seed_fitness_frozen_before_TEST") is not True
            or root.get("test_accessed") is not False or root.get("selection_split") != "train"
            or len(root.get("programs", [])) != 4
            or root.get("TEST_certificate_execution_wrapper_sha256") != digest(__file__)):
        raise ValueError("Complete prior root R2/EoH release is mandatory")
    for name, field in (("data.json", "original_data_sha256"),
                        ("protocol.json", "original_query_protocol_sha256"),
                        ("freeze_receipt.json", "original_evidence_freeze_sha256")):
        if digest(plan / name) != root[field]:
            raise ValueError("Original query plan changed: " + name)
    freeze = json.loads((plan / "freeze_receipt.json").read_bytes())
    for name, expected in freeze["source_sha256"].items():
        if digest(ROOT / "cipheur" / name) != expected:
            raise ValueError("Original certificate implementation changed: " + name)
    archive = ROOT / "experiments/runs/v06" / (out.name + ".tar.gz")
    wrapper = out.parent / (out.name + "_wrapper")
    if archive.exists() or wrapper.exists():
        raise ValueError("Retain all original launch records; no retry or overwrite")
    wrapper.mkdir(parents=True)
    (wrapper / "root_release.json").write_bytes(release.read_bytes())
    source = {**freeze["source_sha256"], "wrapper": digest(__file__)}
    write(wrapper / "execution_plan.json", {
        "version": "v06_R2_EoH_original72_TEST_certificates_server_001",
        "split": "test", "before_any_TEST_certificate_query": True,
        "root_release_sha256": release_sha256, "programme_freeze_sha256": release_sha256,
        "source_sha256": source, "original_states": 72, "workers": 8,
        "whole_job_wall_guard_seconds": 3600, "query_retries": 0,
        "query_and_budget_changes": False})
    write(wrapper / "host_receipt.json", {
        "before_any_TEST_certificate_query": True, "timestamp_unix": time.time(),
        "python": sys.version, "platform": platform.platform(), "workers": 8,
        "root_release_sha256": release_sha256,
        "cgroup_cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip()})
    command = [sys.executable, "-B", "-m", "cipheur.evidence_study_v06", "run",
               "--plan", str(plan), "--out", str(out), "--split", "test", "--frozen", str(release)]
    started = time.perf_counter()
    guard = False
    with (wrapper / "worker.log").open("xb") as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, env={**os.environ,
                                 "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        write(wrapper / "launch_receipt.json", {"timestamp_unix": time.time(), "child_pid": child.pid,
                                                "command": command, "root_release_sha256": release_sha256})
        try:
            code = child.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            guard = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait()
    write(wrapper / "server_execution_receipt.json", {
        "exit_code": code, "whole_job_guard_triggered": guard,
        "actual_wrapper_wall_seconds": time.perf_counter() - started,
        "root_release_sha256": release_sha256, "query_retries": 0,
        "all_partial_outputs_retained": True,
        "original_complete_sha256": digest(out / "complete.json") if (out / "complete.json").exists() else None,
        "original_results_sha256": digest(out / "results.jsonl") if (out / "results.jsonl").exists() else None})
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        if out.exists():
            tar.add(out, arcname=out.name)
        tar.add(wrapper, arcname=wrapper.name)
    return {"archive": str(archive), "archive_sha256": digest(archive),
            "exit_code": code, "guard_triggered": guard}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "out", "release", "release-sha256"):
        parser.add_argument("--" + name, required=True)
    args = vars(parser.parse_args())
    print(json.dumps(run(**args)))
