"""One bounded TRAIN engineering profile; never selects a programme or reads TEST."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCRIPT = Path(__file__).resolve()
TAG_E = "gW0340_gE1200_s0150"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def now():
    return datetime.now(timezone.utc).isoformat()

def compact_result(result):
    keep = ("source", "config", "split", "method", "program_id", "program_arm", "value_ticks", "value_exact",
            "feasible", "cpu_seconds", "wall_seconds", "cpu_seconds_including_record_encoding",
            "head_ever_committed", "stats", "native_child_cpu_seconds", "native_measurement_available")
    return {k: result[k] for k in keep if k in result}

def run_recorded(argv, output, env, timeout=90):
    """The controller measures process wall time, not optimization CPU time."""
    output = Path(output)
    started = time.perf_counter()
    record = {"started_utc": now(), "argv": argv, "output": str(output)}
    try:
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout,
                              check=False, text=True, encoding="utf-8", errors="replace")
        output.with_suffix(".stdout.txt").write_text(proc.stdout, encoding="utf-8")
        output.with_suffix(".stderr.txt").write_text(proc.stderr, encoding="utf-8")
        record.update(returncode=proc.returncode, process_wall_seconds=time.perf_counter()-started)
        if proc.returncode != 0 or not output.is_file():
            record.update(status="failed", stderr_tail=proc.stderr[-6000:])
        else:
            result = json.loads(output.read_text(encoding="utf-8"))
            record.update(status="complete" if result.get("feasible") is True else "infeasible", result=compact_result(result),
                          result_sha256=sha(output))
    except Exception as exc:
        record.update(status="failed", error=repr(exc), process_wall_seconds=time.perf_counter()-started)
    if record["status"] != "complete":
        dump(output.with_suffix(".failure.json"), record)
    return record

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--cipheur-root", type=Path, required=True)
    p.add_argument("--native-executable", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--program-bank", type=Path)
    p.add_argument("--protocol", type=Path)
    p.add_argument("--cpu", type=int, default=24)
    p.add_argument("--seconds", type=float, default=2.)
    p.add_argument("--include-degree", action="store_true")
    args = p.parse_args()
    if args.seconds not in (2., 10.):
        raise ValueError("Engineering profile supports only proposed 2/10 second budgets")
    out = args.output_root.resolve(); out.mkdir(parents=True, exist_ok=True)
    if (out/"registration.json").exists():
        raise ValueError("Choose a fresh output root; profile runs are not overwritten")
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {args.cpu})
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               NUMEXPR_NUM_THREADS="1", PYTHONHASHSEED="0")
    graph = args.data_root/"extensions"/"heterogeneous_ground_v1"/"graphs"/"CP-AU-r000"/(TAG_E+".npz")
    metadata = graph.with_suffix(".json")
    bank = args.program_bank or args.cipheur_root/"examples"/"frozen_joint_bank_v06.json"
    old_id = "joint|block_0_witness:2"
    cases = (["degree"] if args.include_degree else []) + ["oldfrozen", "cp_sat", "chils_ils", "chils"]
    jobs = []
    for method in cases:
        output = out/(method+".json")
        argv = [sys.executable, str(SCRIPT.with_name("full_schedule_benchmark.py")), "--cipheur-root", str(args.cipheur_root),
                "--graph", str(graph), "--metadata", str(metadata), "--source", "CP-AU-r000", "--config", "E",
                "--split", "train", "--method", "program" if method == "oldfrozen" else method,
                "--seconds", str(args.seconds), "--seed", "2", "--output", str(output)]
        if method == "oldfrozen":
            argv += ["--program-bank", str(bank), "--program-id", old_id]
        if method.startswith("chils"):
            argv += ["--native-executable", str(args.native_executable), "--native-output-root", str(out/(method+"_native"))]
        if args.protocol:
            argv += ["--protocol", str(args.protocol)]
        jobs.append({"profile_method": method, "argv": argv, "output": str(output)})
    files = [SCRIPT, SCRIPT.with_name("full_schedule_benchmark.py"), SCRIPT.with_name("full_schedule_execution.py"),
             SCRIPT.with_name("published_weighted_baselines.py"), graph, metadata, bank, args.native_executable]
    registration = {"version": "TRAIN_engineering_profile_v1", "created_utc": now(), "split": "train",
                    "purpose": "bounded execution engineering only; no programme selection", "seconds": args.seconds,
                    "seed": 2, "cpu": args.cpu, "thread_environment": {k: env[k] for k in
                    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "PYTHONHASHSEED")},
                    "files_sha256": {str(v): sha(v) for v in files}, "jobs": jobs}
    dump(out/"registration.json", registration)
    results = []
    for job in jobs:
        record = run_recorded(job["argv"], job["output"], env)
        record["profile_method"] = job["profile_method"]
        results.append(record)
        with (out/"profile.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False)+"\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)
    dump(out/"profile_summary.json", {"registration_sha256": sha(out/"registration.json"), "results": results,
                                      "failed_or_infeasible": sum(v["status"] != "complete" for v in results)})

if __name__ == "__main__":
    main()
