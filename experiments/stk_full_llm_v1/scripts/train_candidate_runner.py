"""Registered, portable eight-worker TRAIN-only complete-schedule evaluation."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import random
import shutil
import socket
import sys
import time
import traceback

from cloud_profile import dump, now, run_recorded, sha

SCRIPT = Path(__file__).resolve()
TRAIN_SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
TAGS = {"A":"gW0340_gE0340_s0150", "W":"gW1200_gE0340_s0150",
        "E":"gW0340_gE1200_s0150", "J":"gW1200_gE1200_s0150"}
TRADITIONAL = ("degree", "weight", "grasp", "local2swap", "cp_sat", "chils_ils", "chils")

def safe_id(value):
    # Identity is kept verbatim in JSON; only artifact names use a stable digest.
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]

def register(args):
    manifest = args.manifest.resolve()
    if manifest.exists():
        raise ValueError("Registration already exists; use --execute with the immutable manifest")
    if args.seconds != 2. or args.seed != 2:
        raise ValueError("Candidate TRAIN protocol is fixed at two CPU seconds and seed 2")
    if len(args.cpus) != 8 or len(set(args.cpus)) != 8:
        raise ValueError("Formal TRAIN registration requires eight distinct single-CPU workers")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8")) if args.protocol else {}
    if protocol and (protocol.get("candidate_training_cpu_seconds", 2.) != 2. or
                     protocol.get("candidate_training_seed", 2) != 2):
        raise ValueError("Protocol candidate training budget disagrees")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    graphs = []
    for source in TRAIN_SOURCES:
        for config, tag in TAGS.items():
            relative = Path("extensions")/"heterogeneous_ground_v1"/"graphs"/source/(tag+".npz")
            graph = args.data_root/relative
            metadata = graph.with_suffix(".json")
            meta = json.loads(metadata.read_text(encoding="utf-8"))
            if meta.get("source_id") != source or meta.get("split") != "train":
                raise ValueError("Only registered TRAIN source metadata may be read")
            if config not in (meta.get("factorial_id"), meta.get("config_id")):
                raise ValueError("TRAIN graph does not have the registered factorial identity")
            graphs.append({"source":source, "config":config, "split":"train",
                           "npz_ref":relative.as_posix(), "metadata_ref":relative.with_suffix(".json").as_posix(),
                           "npz_sha256":sha(graph), "metadata_sha256":sha(metadata)})
    bank_descriptors = []; programme_descriptors = []; seen = set()
    requested = set(args.program_id or [])
    for index, original in enumerate(args.program_bank):
        original = original.resolve()
        bank = json.loads(original.read_text(encoding="utf-8"))
        selection_split = str(bank.get("selection_split", "")).lower()
        if selection_split != "train":
            raise ValueError("Candidate bank must declare TRAIN selection_split")
        if bank.get("TEST_used_for_selection") is True:
            raise ValueError("Candidate bank declares TEST exposure")
        snapshot = manifest.parent/"banks"/("bank_%03d.json" % index)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if snapshot.exists():
            raise ValueError("Bank snapshot already exists in fresh registration directory")
        shutil.copyfile(original, snapshot)
        ref = snapshot.relative_to(manifest.parent).as_posix()
        bank_descriptors.append({"ref":ref, "sha256":sha(snapshot), "original_path_provenance_only":str(original)})
        for item in bank["programs"]:
            identifier = item["id"]
            if requested and identifier not in requested:
                continue
            if identifier in seen:
                raise ValueError("Duplicate programme ID across banks: "+identifier)
            if not isinstance(identifier, str) or not isinstance(item.get("program"), dict):
                raise ValueError("Malformed programme bank item")
            seen.add(identifier)
            programme_descriptors.append({"program_id":identifier, "arm":item.get("arm", "unspecified"),
                                          "bank_ref":ref, "bank_sha256":sha(snapshot)})
    if requested-seen:
        raise ValueError("Unknown requested programme IDs: "+repr(sorted(requested-seen)))
    methods = list(args.method)
    if any(v not in TRADITIONAL for v in methods) or len(set(methods)) != len(methods):
        raise ValueError("Invalid or repeated baseline methods")
    if not programme_descriptors and not methods:
        raise ValueError("No candidate or baseline registered")
    evaluations = [{"method":"program", **p} for p in programme_descriptors]
    evaluations += [{"method":method, "program_id":None, "arm":method} for method in methods]
    jobs = []
    for evaluation in evaluations:
        for graph in graphs:
            identity = json.dumps([evaluation["method"],evaluation.get("program_id"),graph["source"],graph["config"],
                                   args.seconds,args.seed],ensure_ascii=False,separators=(",", ":"))
            jobs.append({"job_id":safe_id(identity), **evaluation, **graph,
                         "seconds":args.seconds, "seed":args.seed})
    random.Random(args.shuffle_seed).shuffle(jobs)
    for index, job in enumerate(jobs):
        job["registered_order"] = index
        job["worker_index"] = index % len(args.cpus)
        job["cpu"] = args.cpus[job["worker_index"]]
    file_set = [SCRIPT, SCRIPT.with_name("cloud_profile.py"), SCRIPT.with_name("full_schedule_benchmark.py"),
                SCRIPT.with_name("full_schedule_execution.py"), SCRIPT.with_name("published_weighted_baselines.py")]
    code_hashes = {v.name:sha(v) for v in file_set}
    # Source snapshot identity is explicit; no source file is copied or modified here.
    cipheur_hashes = {str(v.relative_to(args.cipheur_root)).replace("\\", "/"):sha(v)
                      for v in sorted((args.cipheur_root/"cipheur").rglob("*.py"))}
    if not cipheur_hashes:
        raise ValueError("Missing cipheur dependency source snapshot")
    protocol_ref = None
    if args.protocol:
        target = manifest.parent/"protocol.json"
        if target.exists():
            raise ValueError("Protocol snapshot already exists")
        shutil.copyfile(args.protocol, target)
        protocol_ref = target.name
    registration = {"version":"TRAIN_full_schedule_candidates_v1", "created_utc":now(), "split":"train",
                    "physical_source_groups":2, "source_ids":list(TRAIN_SOURCES), "configs":list(TAGS),
                    "candidate_cpu_seconds":args.seconds, "candidate_seed":args.seed,
                    "shuffle_seed":args.shuffle_seed, "jobs":jobs, "job_count":len(jobs),
                    "cpus":args.cpus, "workers":len(args.cpus), "worker_assignment":"fixed round-robin after preregistered shuffle",
                    "programmes":programme_descriptors, "banks":bank_descriptors,
                    "graph_count":len(graphs), "graphs":graphs, "script_hashes":code_hashes, "cipheur_hashes":cipheur_hashes,
                    "protocol_ref":protocol_ref, "protocol_sha256":sha(manifest.parent/protocol_ref) if protocol_ref else None,
                    "native_executable_sha256":sha(args.native_executable) if args.native_executable else None,
                    "thread_environment":{"OMP_NUM_THREADS":"1", "OPENBLAS_NUM_THREADS":"1", "MKL_NUM_THREADS":"1",
                                          "NUMEXPR_NUM_THREADS":"1", "PYTHONHASHSEED":"0"},
                    "negative_and_failed_records":"retain all, no automatic rerun, no programme pruning",
                    "result_scope":"complete 72h full graph schedule; no conditional oracle or online LLM",
                    "path_resolution":"graph refs relative to --data-root; banks/protocol relative to this manifest; source dependencies under --cipheur-root",
                    "cpu_budget_scope":"graph loading, common seed, feature evaluation, all optimization and final feasibility validation; process startup separate",
                    "paths_provenance_only":{"original_data_root":str(args.data_root.resolve()), "original_cipheur_root":str(args.cipheur_root.resolve())}}
    dump(manifest, registration)
    print(json.dumps({"registration":str(manifest), "sha256":sha(manifest), "jobs":len(jobs),
                      "programmes":len(programme_descriptors), "graphs":len(graphs)},ensure_ascii=False),flush=True)
    return registration

def verify_inputs(args, registration):
    if registration.get("version") != "TRAIN_full_schedule_candidates_v1" or registration.get("split") != "train":
        raise ValueError("This runner accepts only the fixed TRAIN registration")
    if registration["source_ids"] != list(TRAIN_SOURCES) or registration["configs"] != list(TAGS):
        raise ValueError("Registered source/config domain changed")
    for filename, expected in registration["script_hashes"].items():
        if sha(SCRIPT.parent/filename) != expected:
            raise ValueError("Frozen execution script changed: "+filename)
    for filename, expected in registration["cipheur_hashes"].items():
        if sha(args.cipheur_root/filename) != expected:
            raise ValueError("Frozen cipheur dependency changed: "+filename)
    for graph in registration["graphs"]:
        for ref, h in (("npz_ref", "npz_sha256"), ("metadata_ref", "metadata_sha256")):
            if sha(args.data_root/graph[ref]) != graph[h]:
                raise ValueError("Frozen TRAIN input changed: "+graph[ref])
    for bank in registration["banks"]:
        if sha(args.manifest.parent/bank["ref"]) != bank["sha256"]:
            raise ValueError("Frozen candidate bank changed")
    if registration["protocol_ref"] and sha(args.manifest.parent/registration["protocol_ref"]) != registration["protocol_sha256"]:
        raise ValueError("Frozen candidate execution protocol changed")
    expected_native = registration["native_executable_sha256"]
    if expected_native and (not args.native_executable or sha(args.native_executable) != expected_native):
        raise ValueError("Frozen native executable changed")

def job_command(args, registration, job, output):
    argv = [sys.executable, str(SCRIPT.with_name("full_schedule_benchmark.py")),
            "--cipheur-root",str(args.cipheur_root), "--graph",str(args.data_root/job["npz_ref"]),
            "--metadata",str(args.data_root/job["metadata_ref"]), "--source",job["source"],
            "--config",job["config"], "--split","train", "--method",job["method"],
            "--seconds",str(job["seconds"]), "--seed",str(job["seed"]), "--output",str(output)]
    if job["method"] == "program":
        argv += ["--program-bank",str(args.manifest.parent/job["bank_ref"]), "--program-id",job["program_id"]]
    if job["method"].startswith("chils"):
        if not args.native_executable:
            raise ValueError("CHILS requires --native-executable")
        argv += ["--native-executable",str(args.native_executable), "--native-output-root",str(output.parent/(output.stem+"_native"))]
    if registration["protocol_ref"]:
        argv += ["--protocol",str(args.manifest.parent/registration["protocol_ref"])]
    return argv

def execution_health(result):
    phases = result.get("phases", {})
    return {"construction_status":phases.get("construction", {}).get("status"),
            "construction_error":phases.get("construction", {}).get("error"),
            "cp_sat_status":phases.get("cp_sat", {}).get("status"),
            "native_status":phases.get("native_published", {}).get("status"),
            "programme_error_count":sum(v.get("status") == "programme_error" for v in result.get("repairs", [])) +
                                    int(phases.get("construction", {}).get("status") == "programme_error"),
            "native_cpu_measurement_available":result.get("native_cpu_measurement_available"),
            "seed_value_ticks":result.get("seed_value_ticks"), "value_ticks":result.get("value_ticks"),
            "head_ever_committed":result.get("head_ever_committed"), "total_cpu_seconds":result.get("cpu_seconds"),
            "loading_cpu_seconds":result.get("loading", {}).get("input_cpu_seconds")}

def worker_main(index, args, registration, events):
    cpu = registration["cpus"][index]
    log = args.output_root/("worker_cpu_%d.jsonl" % cpu)
    try:
        if hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(0, {cpu})
        else:
            raise RuntimeError("Formal workers require OS single-CPU affinity")
        env = dict(os.environ, **registration["thread_environment"])
        for job in registration["jobs"]:
            if job["worker_index"] != index:
                continue
            output = args.output_root/"results"/(job["job_id"]+".json")
            output.parent.mkdir(parents=True, exist_ok=True)
            record = run_recorded(job_command(args, registration, job, output), output, env, timeout=args.wall_guard)
            record.update(job_id=job["job_id"], registered_order=job["registered_order"], source=job["source"],
                          config=job["config"], method=job["method"], program_id=job.get("program_id"), arm=job["arm"],
                          worker_index=index, cpu=cpu, worker_pid=os.getpid())
            if output.is_file():
                try:
                    result = json.loads(output.read_text(encoding="utf-8"))
                    record["execution_health"] = execution_health(result)
                    record["record_cpu_affinity"] = result.get("cpu_affinity")
                    if record["record_cpu_affinity"] != [cpu]:
                        record["affinity_mismatch"] = True
                except Exception as exc:
                    record["result_parse_error"] = repr(exc)
            with log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False)+"\n")
            events.put({"type":"record", "record":record})
    except Exception as exc:
        events.put({"type":"worker_failure", "worker_index":index, "cpu":cpu, "error":repr(exc), "traceback":traceback.format_exc()})
    finally:
        events.put({"type":"worker_done", "worker_index":index, "cpu":cpu})

def execute(args, registration):
    verify_inputs(args, registration)
    out = args.output_root.resolve(); args.output_root = out
    out.mkdir(parents=True, exist_ok=True)
    if (out/"execution_receipt.json").exists() or (out/"jobs.jsonl").exists():
        raise ValueError("Execution output exists; failures are retained without silent reruns")
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    if allowed is None or not set(registration["cpus"]) <= set(allowed):
        raise ValueError("Registered CPU affinity is unavailable on this host")
    dump(out/"execution_receipt.json", {"started_utc":now(), "manifest_sha256":sha(args.manifest), "hostname":socket.gethostname(),
         "platform":platform.platform(), "python":sys.version, "pid":os.getpid(), "cpus":registration["cpus"],
         "allowed_cpus_before_worker_pinning":allowed, "load_average_at_start":os.getloadavg() if hasattr(os,"getloadavg") else None,
         "job_count":len(registration["jobs"]), "wall_guard_per_job_seconds":args.wall_guard,
         "single_thread_policy":"each worker and child pinned to one CPU; BLAS/OMP one; CP-SAT num_search_workers=1"})
    ctx = mp.get_context("spawn")
    events = ctx.Queue(); workers = []
    for index in range(registration["workers"]):
        process = ctx.Process(target=worker_main, args=(index,args,registration,events))
        process.start(); workers.append(process)
    finished = set(); records = []; failures = []; started = time.perf_counter()
    while len(finished) < len(workers):
        try:
            event = events.get(timeout=1.)
        except Exception:
            for index, process in enumerate(workers):
                if index not in finished and process.exitcode is not None:
                    finished.add(index)
                    failures.append({"worker_index":index,"status":"worker_exited_without_terminal_event","exitcode":process.exitcode})
            continue
        if event["type"] == "worker_done":
            finished.add(event["worker_index"])
        elif event["type"] == "worker_failure":
            failures.append(event)
            with (out/"worker_failures.jsonl").open("a",encoding="utf-8") as f:
                f.write(json.dumps(event,ensure_ascii=False)+"\n")
        else:
            record = event["record"]; records.append(record)
            with (out/"jobs.jsonl").open("a",encoding="utf-8") as f:
                f.write(json.dumps(record,ensure_ascii=False)+"\n")
            print(json.dumps({k:record.get(k) for k in ("registered_order","status","method","program_id","source","config","cpu")},ensure_ascii=False),flush=True)
    for process in workers:
        process.join()
    completed_ids = {v["job_id"] for v in records}
    missing = [v["job_id"] for v in registration["jobs"] if v["job_id"] not in completed_ids]
    summaries = defaultdict(list)
    for record in records:
        summaries[(record["method"],record.get("program_id"),record["arm"])].append(record)
    by_method = []
    for key, rows in summaries.items():
        healthy = [v for v in rows if v["status"] == "complete"]
        qualities = [v["execution_health"]["value_ticks"] for v in healthy if v.get("execution_health",{}).get("value_ticks") is not None]
        by_method.append({"method":key[0],"program_id":key[1],"arm":key[2],"record_count":len(rows),
                          "status_counts":dict(Counter(v["status"] for v in rows)),
                          "feasible_record_count":len(healthy), "mean_value_ticks_on_feasible_records":sum(qualities)/len(qualities) if qualities else None,
                          "quality_denominator":len(qualities), "head_committed_count":sum(bool(v.get("execution_health",{}).get("head_ever_committed")) for v in rows),
                          "programme_error_count":sum(v.get("execution_health",{}).get("programme_error_count",0) for v in rows),
                          "inference":"descriptive TRAIN evaluation only; no candidate selected by this runner"})
    dump(out/"execution_summary.json", {"manifest_sha256":sha(args.manifest),"finished_utc":now(),
         "registered_jobs":len(registration["jobs"]),"recorded_jobs":len(records),"missing_job_ids":missing,
         "worker_failures":failures,"worker_exit_codes":[v.exitcode for v in workers],
         "status_counts":dict(Counter(v["status"] for v in records)),"by_method":by_method,
         "execution_wall_seconds":time.perf_counter()-started,"load_average_at_end":os.getloadavg() if hasattr(os,"getloadavg") else None})
    if missing or failures:
        raise SystemExit(2)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--register",action="store_true")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--cipheur-root",type=Path,required=True)
    p.add_argument("--output-root",type=Path)
    p.add_argument("--program-bank",type=Path,action="append",default=[])
    p.add_argument("--program-id",action="append")
    p.add_argument("--method",choices=TRADITIONAL,action="append",default=[])
    p.add_argument("--protocol",type=Path)
    p.add_argument("--native-executable",type=Path)
    p.add_argument("--seconds",type=float,default=2.)
    p.add_argument("--seed",type=int,default=2)
    p.add_argument("--shuffle-seed",type=int,default=20261005)
    p.add_argument("--cpus",type=int,nargs=8,default=list(range(24,32)))
    p.add_argument("--wall-guard",type=float,default=90.)
    args = p.parse_args()
    args.manifest = args.manifest.resolve()
    if not args.register and not args.execute:
        p.error("Choose --register and/or --execute")
    if args.wall_guard < 10:
        raise ValueError("Wall guard must allow bounded input/output overhead")
    if args.execute and not args.output_root:
        p.error("--execute requires --output-root")
    registration = register(args) if args.register else json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.execute:
        execute(args, registration)

if __name__ == "__main__":
    main()
