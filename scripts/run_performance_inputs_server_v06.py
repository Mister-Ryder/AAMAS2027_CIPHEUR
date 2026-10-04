"""Freeze and generate all fresh V06 TEST inputs on cloud; no optimization."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STEM = "performance_inputs_v06_001"
REC = ROOT / "experiments/discovery/performance_inputs_server_v06_001"
CAP = ROOT / "experiments/source_snapshots/v06/performance_inputs_v06_001_source.zip"
NAMES = ("scripts/prepare_performance_v06.py", "cipheur/model.py", "cipheur/__init__.py",
         "scripts/run_performance_inputs_server_v06.py")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def package():
    if CAP.exists() or REC.exists():
        raise ValueError("Preserve first input-generation freeze")
    assert digest(ROOT / NAMES[0]) == "893115422a9e7dbae61105cec7ffa27d257e8a482cab380af9909c11a4364ee8"
    inventory = {n: digest(ROOT / n) for n in NAMES}
    execution = {"before_any_input_generation": True, "source_sha256": inventory,
                 "workers": 4, "pairs": 108, "endpoints": 216,
                 "optimization_calls_permitted": 0, "candidate_evaluations_permitted": 0,
                 "selection_binding": None, "wall_safety_seconds": 3600,
                 "all_prespecified_cells_retained": True}
    write(REC / "execution_plan.json", execution)
    inventory["experiments/discovery/performance_inputs_server_v06_001/execution_plan.json"] = digest(REC / "execution_plan.json")
    CAP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAP, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(inventory):
            entry = zipfile.ZipInfo(name, (2026, 10, 3, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (ROOT / name).read_bytes())
    write(REC / "source_receipt.json", {"before_any_input_generation": True,
          "source_zip_sha256": digest(CAP), "source_zip": CAP.relative_to(ROOT).as_posix(),
          "files_sha256": inventory})
    print(json.dumps({"source_zip_sha256": digest(CAP), "workers": 4}), flush=True)


def run():
    source = json.loads((REC / "source_receipt.json").read_text())
    execution = json.loads((REC / "execution_plan.json").read_text())
    assert source["before_any_input_generation"] and execution["optimization_calls_permitted"] == 0
    assert digest(CAP) == source["source_zip_sha256"]
    for name, expected in source["files_sha256"].items():
        assert digest(ROOT / name) == expected, name
    output = ROOT / "output" / STEM
    if output.exists() or (REC / "host_receipt.json").exists():
        raise ValueError("Preserve earlier input generation; no redraw")
    host = {"before_any_input_generation": True, "python": sys.version,
            "platform": platform.platform(), "executable": sys.executable,
            "workers": 4, "timestamp_unix": time.time(), "pid": os.getpid(),
            "cgroup_cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
            "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
            "source_zip_sha256": source["source_zip_sha256"],
            "optimization_calls": 0, "test_outcomes_accessed": False}
    write(REC / "host_receipt.json", host)
    base = [sys.executable, NAMES[0], "--out", "output/" + STEM]
    started = time.perf_counter()
    with (ROOT / "generation.log").open("xb") as log:
        subprocess.run([*base, "--plan-only"], cwd=ROOT, stdout=log,
                       stderr=subprocess.STDOUT, timeout=60, check=True)
        write(REC / "pre_generation_receipt.json", {
              "original_protocol_sha256": digest(output / "protocol.json"),
              "original_freeze_receipt_sha256": digest(output / "freeze_receipt.json"),
              "source_zip_sha256": source["source_zip_sha256"],
              "before_any_graph_generation": True, "workers": 4})
        subprocess.run([*base, "--generate", "--workers", "4"], cwd=ROOT, stdout=log,
                       stderr=subprocess.STDOUT, timeout=execution["wall_safety_seconds"], check=True)
    complete = json.loads((output / "input_completion.json").read_text())
    assert complete["pairs"] == 108 and complete["endpoints"] == 216
    assert complete["optimization_calls"] == complete["candidate_evaluations"] == 0
    assert complete["data_sha256"] == digest(output / "data.json")
    for name in ("execution_plan.json", "source_receipt.json", "host_receipt.json", "pre_generation_receipt.json"):
        (output / name).write_bytes((REC / name).read_bytes())
    write(output / "server_generation_receipt.json", {
          "append_only": True, "full_generation_and_startup_wall_seconds": time.perf_counter() - started,
          "original_input_completion_sha256": digest(output / "input_completion.json"),
          "source_zip_sha256": source["source_zip_sha256"],
          "optimization_calls": 0, "test_outcomes_accessed": False, "redraws": 0})
    archive = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(output, arcname=STEM)
    write(REC / "archive_receipt.json", {"archive_sha256": digest(archive),
          "archive_bytes": archive.stat().st_size, "data_sha256": complete["data_sha256"],
          "input_generation_complete": True, "optimization_calls": 0})
    print(json.dumps({"archive_sha256": digest(archive), "endpoints": 216}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("package", "run"))
    args = parser.parse_args()
    package() if args.mode == "package" else run()
