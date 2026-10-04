"""Frozen orchestration for cloud-only V06 TRAIN Degree repair feedback."""
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
STEM = "repair_degree_feedback_v06_001"
RECEIPTS = ROOT / "experiments/discovery/repair_feedback_server_v06_001"
CAPSULE = ROOT / "experiments/source_snapshots/v06/repair_degree_feedback_v06_001_source.zip"
DATA = "experiments/discovery/v06_evidence_001/data.json"
CONFIG = "configs/repair_train_v06_001.json"
CODE = ("cipheur/__init__.py", "cipheur/model.py", "cipheur/programs.py",
        "cipheur/graph_features.py", "cipheur/compiled.py", "cipheur/repair_v06.py",
        "scripts/run_repair_feedback_v06.py")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n").encode("utf-8"))


def package():
    if CAPSULE.exists() or RECEIPTS.exists():
        raise ValueError("Preserve original registered feedback capsule")
    assert digest(ROOT / "scripts/run_repair_feedback_v06.py") == "b1df66408db5f7ccfcea72f67b12b62e27baaf894567f38e86af2f4306c4aa82"
    assert digest(ROOT / "cipheur/repair_v06.py") == "c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3"
    assert digest(ROOT / DATA) == "968f96b7712ca3ecc8a7b43f567c6b6403742f26f0e76e9d5f2c680973827784"
    plan = {"version": "repair_feedback_server_v06_001", "before_any_feedback": True,
            "data": DATA, "split": "train", "assigned": 120, "workers": 8,
            "output": "output/" + STEM, "clock": "wall", "seconds": 0.5,
            "whole_run_wall_guard_seconds": 3600, "guard_is_failure_safeguard_only": True,
            "source_sha256": {n: digest(ROOT / n) for n in CODE},
            "data_sha256": digest(ROOT / DATA), "root_config_sha256": digest(ROOT / CONFIG),
            "root_config": json.loads((ROOT / CONFIG).read_text(encoding="utf-8")),
            "test_execution_permitted": False, "query_retries": 0,
            "timing_scope": "Kernel starts before AST/init; task includes reconstruction; batch wall separately includes interpreter/import/verification/pool startup and receipts"}
    write(RECEIPTS / "execution_plan.json", plan)
    names = (*CODE, "scripts/run_repair_feedback_server_v06.py", DATA, CONFIG,
             "experiments/discovery/repair_feedback_server_v06_001/execution_plan.json")
    inventory = {n: digest(ROOT / n) for n in names}
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(inventory):
            entry = zipfile.ZipInfo(name, (2026, 10, 3, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (ROOT / name).read_bytes())
    receipt = {"before_any_feedback": True, "source_zip": CAPSULE.relative_to(ROOT).as_posix(),
               "source_zip_sha256": digest(CAPSULE), "files_sha256": inventory,
               "execution_plan_sha256": digest(RECEIPTS / "execution_plan.json")}
    write(RECEIPTS / "capsule_receipt.json", receipt)
    print(json.dumps(receipt), flush=True)


def optional(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def run():
    capsule = json.loads((RECEIPTS / "capsule_receipt.json").read_text())
    plan = json.loads((RECEIPTS / "execution_plan.json").read_text())
    assert capsule["before_any_feedback"] and plan["before_any_feedback"]
    assert plan["split"] == "train" and plan["test_execution_permitted"] is False
    assert plan["workers"] == 8 and plan["assigned"] == 120
    assert digest(CAPSULE) == capsule["source_zip_sha256"]
    for name, expected in capsule["files_sha256"].items():
        assert digest(ROOT / name) == expected, name
    output = ROOT / plan["output"]
    if output.exists() or (RECEIPTS / "execution_host_receipt.json").exists():
        raise ValueError("Do not overwrite or rerun prepared feedback")
    host = {"before_any_feedback": True, "timestamp_unix": time.time(),
            "pid": os.getpid(), "python": sys.version, "executable": sys.executable,
            "platform": platform.platform(), "workers": 8,
            "visible_cpu_count": os.cpu_count(), "cgroup_cpu_max": optional("/sys/fs/cgroup/cpu.max"),
            "cgroup_memory_max": optional("/sys/fs/cgroup/memory.max"),
            "active_process_inventory": subprocess.check_output(
                ["ps", "-eo", "pid,comm,pcpu,pmem", "--sort=-pcpu"], text=True).splitlines()[:25],
            "source_zip_sha256": capsule["source_zip_sha256"],
            "execution_plan_sha256": capsule["execution_plan_sha256"],
            "test_execution_permitted": False}
    write(RECEIPTS / "execution_host_receipt.json", host)
    base = [sys.executable, "scripts/run_repair_feedback_v06.py", "--data", plan["data"],
            "--out", plan["output"], "--workers", "8", "--split", "train"]
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    started = time.perf_counter()
    log = ROOT / (STEM + ".worker.log")
    guarded = False
    with log.open("xb") as stream:
        prepared = subprocess.run([*base, "--prepare-only"], cwd=ROOT, env=env,
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=60)
        if prepared.returncode:
            raise ValueError("Outcome-free prepare failed; no TRAIN execution occurred")
        frozen = json.loads((output / "freeze_receipt.json").read_text())
        assert frozen["source_sha256"] == plan["source_sha256"]
        protocol = json.loads((output / "protocol.json").read_text())
        assert protocol["contexts"] == 120 and protocol["split"] == "train"
        child = subprocess.Popen([*base, "--run"], cwd=ROOT, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        write(RECEIPTS / "query_launch_receipt.json", {
            "child_pid": child.pid, "timestamp_unix": time.time(), "split": "train",
            "host_receipt_sha256": digest(RECEIPTS / "execution_host_receipt.json"),
            "feedback_protocol_sha256": digest(output / "protocol.json"),
            "feedback_freeze_receipt_sha256": digest(output / "freeze_receipt.json"),
            "whole_run_wall_guard_seconds": plan["whole_run_wall_guard_seconds"]})
        try:
            code = child.wait(timeout=plan["whole_run_wall_guard_seconds"])
        except subprocess.TimeoutExpired:
            guarded = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait()
    fullwall = time.perf_counter() - started
    completion = output / "completion.json"
    if completion.exists():
        c = json.loads(completion.read_text())
        assert c["assigned"] == c["returned"] == 120 and c["test_executions"] == 0
        assert digest(output / "results.jsonl") == c["results_sha256"]
    for name in ("execution_plan.json", "capsule_receipt.json", "execution_host_receipt.json", "query_launch_receipt.json"):
        (output / name).write_bytes((RECEIPTS / name).read_bytes())
    (output / "root_config.json").write_bytes((ROOT / CONFIG).read_bytes())
    (output / "worker.log").write_bytes(log.read_bytes())
    write(output / "server_execution_receipt.json", {
        "append_only": True, "source_zip_sha256": capsule["source_zip_sha256"],
        "host_receipt_sha256": digest(RECEIPTS / "execution_host_receipt.json"),
        "original_completion_sha256": digest(completion) if completion.exists() else None,
        "full_prepare_and_run_wall_seconds": fullwall,
        "shared_startup_is_not_charged_per_kernel_assignment": True,
        "exit_code": code, "whole_run_guard_triggered": guarded,
        "test_executions": 0, "retries": 0, "all_partial_outcomes_retained": True})
    archive = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(output, arcname=STEM)
    write(RECEIPTS / "completion_archive_receipt.json", {
        "archive_sha256": digest(archive), "archive_bytes": archive.stat().st_size,
        "execution_complete": completion.exists() and code == 0 and not guarded})
    print(json.dumps({"archive_sha256": digest(archive), "complete": completion.exists(),
                      "exit_code": code, "guard_triggered": guarded}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("package", "run"))
    args = parser.parse_args()
    package() if args.mode == "package" else run()
