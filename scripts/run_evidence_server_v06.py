"""Package/replay the frozen V06 TRAIN evidence plan without TEST queries.

This wrapper changes no oracle, input, query, label, or original receipt. Its
whole-run wall guard only detects a genuine stalled job and retains partial
outputs rather than rerunning or fabricating unfinished labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
STEM = "v06_evidence_train_001"
PLAN = ROOT / "experiments/discovery/v06_evidence_001"
RECEIPTS = ROOT / "experiments/discovery/v06_evidence_server_001"
CAPSULE = ROOT / "experiments/source_snapshots/v06/v06_evidence_train_001_source.zip"
BUDGET_SHA = "16834240d6136cf54cf208e3f03b24f7d0505f72b9cc898df8bf1ac31f4b19d2"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n").encode("utf-8"))


def package():
    if CAPSULE.exists() or RECEIPTS.exists():
        raise ValueError("Do not overwrite a registered server evidence capsule")
    frozen = json.loads((PLAN / "freeze_receipt.json").read_text(encoding="utf-8"))
    assert frozen["before_any_oracle_query"]
    assert digest(PLAN / "data.json") == frozen["data_sha256"]
    assert digest(PLAN / "protocol.json") == frozen["protocol_sha256"]
    assert digest(PLAN / "BUDGET_SCOPE.json") == BUDGET_SHA
    for name, expected in frozen["source_sha256"].items():
        assert digest(ROOT / "cipheur" / name) == expected, name
    data = json.loads((PLAN / "data.json").read_text(encoding="utf-8"))
    train = [r for r in data["records"] if r["split"] == "train"]
    assert len(train) == 120
    execution = {
        "version": "v06_evidence_server_train_replay_001",
        "registered_before_any_query": True,
        "split": "train", "test_queries_permitted": False,
        "workers": 8, "whole_run_wall_guard_seconds": 3600,
        "guard_scope": "failure guard only; no query relabeling, subsampling or retry",
        "command": ["-m", "cipheur.evidence_study_v06", "run", "--plan",
                    "experiments/discovery/v06_evidence_001", "--out",
                    "output/" + STEM, "--split", "train"],
        "train_states": len(train),
        "train_queries": sum(len(r["queries"]) for r in train),
        "train_query_kind": dict(Counter(q["kind"] for r in train for q in r["queries"])),
        "prior_plan_freeze_sha256": digest(PLAN / "freeze_receipt.json"),
        "budget_scope_sha256": BUDGET_SHA,
        "original_source_sha256": frozen["source_sha256"],
        "budget_receipt_append_only": True,
        "outcome_unknowns_ties_shortfalls_retained": True,
        "source_constructor_and_queries_unchanged": True,
        "public_states_prior_corpus_scope": "source-disjoint TRAIN/TEST raw sources within previously exposed corpus",
    }
    write(RECEIPTS / "execution_plan.json", execution)
    members = [ROOT / "cipheur" / n for n in frozen["source_sha256"]]
    members += [ROOT / "cipheur/__init__.py", Path(__file__).resolve()]
    members += [PLAN / n for n in ("data.json", "protocol.json", "freeze_receipt.json", "BUDGET_SCOPE.json")]
    members += [RECEIPTS / "execution_plan.json"]
    inventory = {p.relative_to(ROOT).as_posix(): digest(p) for p in members}
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(inventory):
            entry = zipfile.ZipInfo(name, (2026, 10, 3, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (ROOT / name).read_bytes())
    receipt = {"registered_before_any_query": True, "source_zip_sha256": digest(CAPSULE),
               "source_zip": CAPSULE.relative_to(ROOT).as_posix(), "files_sha256": inventory,
               "execution_plan_sha256": digest(RECEIPTS / "execution_plan.json"),
               "budget_scope_sha256": BUDGET_SHA, "query_split": "train"}
    write(RECEIPTS / "capsule_receipt.json", receipt)
    print(json.dumps({"source_zip_sha256": receipt["source_zip_sha256"],
                      "execution_plan_sha256": receipt["execution_plan_sha256"],
                      "train_states": len(train), "train_queries": execution["train_queries"]}), flush=True)


def read_optional(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def run():
    capsule = json.loads((RECEIPTS / "capsule_receipt.json").read_text())
    execution = json.loads((RECEIPTS / "execution_plan.json").read_text())
    assert capsule["registered_before_any_query"] and capsule["query_split"] == "train"
    assert digest(CAPSULE) == capsule["source_zip_sha256"]
    for name, expected in capsule["files_sha256"].items():
        assert digest(ROOT / name) == expected, name
    assert digest(PLAN / "BUDGET_SCOPE.json") == BUDGET_SHA
    budget = json.loads((PLAN / "BUDGET_SCOPE.json").read_text())
    assert budget["before_any_oracle_query"]
    assert execution["split"] == "train" and execution["test_queries_permitted"] is False
    assert execution["workers"] == 8
    output = ROOT / "output" / STEM
    if output.exists() or (RECEIPTS / "execution_host_receipt.json").exists():
        raise ValueError("Preserve prior server attempts; no rerun or overwrite")
    host = {"before_any_oracle_query": True, "timestamp_unix": time.time(),
            "pid": os.getpid(), "platform": platform.platform(),
            "python": sys.version, "executable": sys.executable,
            "visible_cpu_count": os.cpu_count(),
            "affinity_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
            "cgroup_cpu_max": read_optional("/sys/fs/cgroup/cpu.max"),
            "cgroup_memory_max": read_optional("/sys/fs/cgroup/memory.max"),
            "memory_info": read_optional("/proc/meminfo"),
            "active_process_inventory": subprocess.check_output(
                ["ps", "-eo", "pid,comm,pcpu,pmem", "--sort=-pcpu"], text=True).splitlines()[:25],
            "workers": 8, "source_zip_sha256": capsule["source_zip_sha256"],
            "execution_plan_sha256": capsule["execution_plan_sha256"],
            "budget_scope_sha256": BUDGET_SHA,
            "test_queries_permitted": False}
    write(RECEIPTS / "execution_host_receipt.json", host)
    log = ROOT / "output" / (STEM + ".worker.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    guarded = False
    with log.open("xb") as stream:
        child = subprocess.Popen([sys.executable, *execution["command"]], cwd=ROOT,
                                 stdout=stream, stderr=subprocess.STDOUT,
                                 start_new_session=True,
                                 env={**os.environ, "OMP_NUM_THREADS": "1",
                                      "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        write(RECEIPTS / "query_launch_receipt.json", {
            "child_pid": child.pid, "parent_pid": os.getpid(),
            "timestamp_unix": time.time(), "split": "train", "workers": 8,
            "execution_host_receipt_sha256": digest(RECEIPTS / "execution_host_receipt.json"),
            "whole_run_wall_guard_seconds": execution["whole_run_wall_guard_seconds"]})
        try:
            code = child.wait(timeout=execution["whole_run_wall_guard_seconds"])
        except subprocess.TimeoutExpired:
            guarded = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait()
    output.mkdir(parents=True, exist_ok=True)
    for name in ("BUDGET_SCOPE.json",):
        (output / name).write_bytes((PLAN / name).read_bytes())
    for name in ("execution_plan.json", "capsule_receipt.json", "execution_host_receipt.json", "query_launch_receipt.json"):
        (output / name).write_bytes((RECEIPTS / name).read_bytes())
    original_execution = output / "execution.json"
    complete = output / "complete.json"
    receipt = {"append_only": True, "split": "train", "test_queries_run": 0,
               "budget_scope_sha256": BUDGET_SHA,
               "source_zip_sha256": capsule["source_zip_sha256"],
               "execution_host_receipt_sha256": digest(RECEIPTS / "execution_host_receipt.json"),
               "original_execution_sha256": digest(original_execution) if original_execution.exists() else None,
               "original_complete_sha256": digest(complete) if complete.exists() else None,
               "exit_code": code, "whole_run_guard_triggered": guarded,
               "total_wall_seconds": time.perf_counter() - started,
               "partial_outcomes_retained": True, "query_retries": 0}
    if complete.exists():
        c = json.loads(complete.read_text())
        assert c["split"] == "train" and c["states"] == 120 and c["execution_complete"]
        assert c["results_sha256"] == digest(output / "results.jsonl")
    write(output / "execution_budget_receipt.json", receipt)
    (output / "worker.log").write_bytes(log.read_bytes())
    archive = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(output, arcname=STEM)
    write(RECEIPTS / "completion_archive_receipt.json", {
        "archive_sha256": digest(archive), "archive_bytes": archive.stat().st_size,
        "execution_budget_receipt_sha256": digest(output / "execution_budget_receipt.json"),
        "execution_complete": complete.exists() and code == 0 and not guarded})
    print(json.dumps({"archive_sha256": digest(archive), "exit_code": code,
                      "guard_triggered": guarded, "complete_receipt": complete.exists()}), flush=True)
    if code != 0 or guarded:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("package", "run"))
    args = parser.parse_args()
    package() if args.mode == "package" else run()
