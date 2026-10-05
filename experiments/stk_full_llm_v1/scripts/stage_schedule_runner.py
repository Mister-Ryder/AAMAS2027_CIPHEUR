"""Frozen complete-schedule stages: VALIDATION, TEST, and final TRAIN. No selection."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
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
from train_candidate_runner import execution_health, safe_id, TRADITIONAL

SCRIPT=Path(__file__).resolve()
CONFIGS={"A":("g0340","gW0340_gE0340_s0150"),"M":("g0680","gW0680_gE0680_s0150"),
         "J":("g1200","gW1200_gE1200_s0150"),"stress":("g1800","gW1800_gE1800_s0150"),
         "W":("gW1200_gE0340_s0150",),"E":("gW0340_gE1200_s0150",),
         "MW":("gW0680_gE1200_s0150",),"ME":("gW1200_gE0680_s0150",)}
STAGES={"val":{"split":"val","replicates":("r006",),"configs":("A","W","E","J")},
        "test":{"split":"test","replicates":("r008","r009"),"configs":("A","M","J","stress","W","E","MW","ME")},
        "final_train":{"split":"train","replicates":("r000","r001"),"configs":("A","W","E","J")}}

def sources(stage):
    return ["CP-%s-%s" % (geometry,replicate) for replicate in STAGES[stage]["replicates"] for geometry in ("AU","AP")]

def selected_ids(args, protocol):
    identifiers=list(args.program_id or [])
    if args.program_ids_json:
        obj=json.loads(args.program_ids_json.read_text(encoding="utf-8"))
        identifiers+=obj if isinstance(obj,list) else obj["program_ids"]
    if not identifiers and args.stage=="test":
        identifiers=list(protocol["final_program_ids"])
    if len(set(identifiers))!=len(identifiers):raise ValueError("Duplicate requested programme IDs")
    return identifiers

def graph_entries(args):
    """Only registered graph paths and metadata are examined; never optimizer outputs."""
    stage=STAGES[args.stage]; root=args.data_root.resolve()
    raw=None
    if args.graph_manifest:
        raw=json.loads(args.graph_manifest.read_text(encoding="utf-8"))["graphs"]
    result=[]
    for source in sources(args.stage):
        for alias in stage["configs"]:
            if raw is not None:
                matches=[v for v in raw if v["source"]==source and v.get("config_alias",v.get("config"))==alias]
                if len(matches)!=1:raise ValueError("Graph-manifest alias/source must be unique: "+source+"/"+alias)
                item=matches[0]
                if item.get("split",stage["split"])!=stage["split"]:raise ValueError("Graph manifest split disagrees")
                npz=(root/item["npz_path"]).resolve(); metadata=(root/item["metadata_path"]).resolve()
            else:
                graph_root=args.graph_root.resolve() if args.graph_root else root/"graphs"
                # Uniform filenames take deterministic priority over equal cached factorial copies.
                candidates=[graph_root/source/(tag+".npz") for tag in CONFIGS[alias]]
                existing=[v for v in candidates if v.is_file()]
                if not existing:raise FileNotFoundError("No registered input for "+source+"/"+alias)
                npz=existing[0]; metadata=npz.with_suffix(".json")
            try:npz_ref=npz.relative_to(root).as_posix();metadata_ref=metadata.relative_to(root).as_posix()
            except ValueError:raise ValueError("All graph inputs must remain under --data-root")
            meta=json.loads(metadata.read_text(encoding="utf-8"))
            split={"validation":"val","val":"val","train":"train","test":"test"}.get(meta.get("split"))
            if meta.get("source_id")!=source or split!=stage["split"]:raise ValueError("Source/split metadata mismatch")
            canonical=meta.get("config_id",npz.stem)
            if canonical not in CONFIGS[alias]:raise ValueError("Configuration metadata does not match registered alias: "+alias)
            result.append({"source":source,"config_alias":alias,"config":canonical,"split":stage["split"],
                           "npz_ref":npz_ref,"metadata_ref":metadata_ref,"npz_sha256":sha(npz),"metadata_sha256":sha(metadata)})
    return result

def register(args):
    if args.manifest.exists():raise ValueError("Do not overwrite stage registration")
    if len(args.cpus)!=8 or len(set(args.cpus))!=8:raise ValueError("Register eight distinct single-CPU workers")
    if len(set(args.budgets))!=len(args.budgets) or len(set(args.seeds))!=len(args.seeds):raise ValueError("Repeated budget or seed")
    protocol=json.loads(args.protocol.read_text(encoding="utf-8"))
    allowed_budgets=protocol.get("budgets_seconds",protocol.get("execution_cpu_seconds",[]))
    allowed_seeds=protocol.get("seeds",protocol.get("formal_seeds",[]))
    if not set(args.budgets)<=set(allowed_budgets) or not set(args.seeds)<=set(allowed_seeds):raise ValueError("Unregistered budget/seed")
    if args.stage=="test":
        if protocol.get("frozen") is not True:raise ValueError("TEST requires frozen protocol before registration")
        if set(sources("test"))!=set(protocol["test_sources"]):raise ValueError("TEST source freeze mismatch")
    ids=selected_ids(args,protocol)
    if not ids and args.program_bank and not args.all_programs:raise ValueError("Specify exact stage programme IDs or --all-programs")
    if args.stage=="test" and args.all_programs:raise ValueError("TEST forbids unrestricted candidate banks")
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    programmes=[]; bank_ref=None; bank_sha=None
    if args.program_bank:
        bank_sha=sha(args.program_bank)
        bank=json.loads(args.program_bank.read_text(encoding="utf-8"))
        if bank.get("TEST_used_for_selection") is True:raise ValueError("Programme bank declares TEST exposure")
        if args.stage=="test":
            if bank_sha!=protocol["frozen_program_bank_sha256"]:raise ValueError("TEST bank does not match frozen SHA")
            if not set(ids)<=set(protocol["final_program_ids"]):raise ValueError("TEST contains an unselected programme")
        seen=set()
        for item in bank["programs"]:
            if not args.all_programs and item["id"] not in ids:continue
            if item["id"] in seen:raise ValueError("Repeated programme ID in bank")
            seen.add(item["id"])
            programmes.append({"method":"program","program_id":item["id"],"arm":item.get("arm","unspecified"),
                               "batch":item.get("batch"),"round":item.get("round")})
        if set(ids)-seen:raise ValueError("Requested stage programme ID missing from bank")
        bank_ref="programme_bank.json"; shutil.copyfile(args.program_bank,args.manifest.parent/bank_ref)
    elif ids:raise ValueError("Programme IDs require a bank")
    if len(set(args.method))!=len(args.method):raise ValueError("Repeated classical baseline")
    evaluations=programmes+[{"method":v,"program_id":None,"arm":v} for v in args.method]
    if not evaluations:raise ValueError("No stage methods registered")
    native_needed=any(v["method"].startswith("chils") for v in evaluations)
    if native_needed and not args.native_executable:raise ValueError("Register native executable for CHILS methods")
    graphs=graph_entries(args); jobs=[]
    for evaluation in evaluations:
        for graph in graphs:
            for budget in args.budgets:
                for seed in args.seeds:
                    identity=json.dumps([args.stage,evaluation["method"],evaluation["program_id"],graph["source"],graph["config_alias"],budget,seed],separators=(",", ":"))
                    jobs.append({"job_id":safe_id(identity),**evaluation,**graph,"seconds":budget,"seed":seed})
    random.Random(args.shuffle_seed).shuffle(jobs)
    for index,job in enumerate(jobs):job.update(registered_order=index,worker_index=index%8,cpu=args.cpus[index%8])
    shutil.copyfile(args.protocol,args.manifest.parent/"protocol.json")
    runtime=("stage_schedule_runner.py","train_candidate_runner.py","cloud_profile.py","full_schedule_benchmark.py",
             "full_schedule_execution.py","published_weighted_baselines.py")
    source_hashes={v.relative_to(args.cipheur_root).as_posix():sha(v) for v in sorted((args.cipheur_root/"cipheur").rglob("*.py"))}
    if not source_hashes:raise ValueError("Missing dependency code snapshot")
    registration={"version":"complete_schedule_stage_v1","stage":args.stage,"split":STAGES[args.stage]["split"],"created_utc":now(),
         "source_ids":sources(args.stage),"configs":list(STAGES[args.stage]["configs"]),"graphs":graphs,"graph_count":len(graphs),
         "jobs":jobs,"job_count":len(jobs),"programmes":programmes,"bank_ref":bank_ref,"bank_sha256":bank_sha,
         "budgets_seconds":args.budgets,"seeds":args.seeds,"shuffle_seed":args.shuffle_seed,"workers":8,"cpus":args.cpus,
         "script_hashes":{v:sha(SCRIPT.with_name(v)) for v in runtime},"cipheur_hashes":source_hashes,
         "protocol_ref":"protocol.json","protocol_sha256":sha(args.manifest.parent/"protocol.json"),
         "native_executable_sha256":sha(args.native_executable) if native_needed else None,
         "thread_environment":{"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","PYTHONHASHSEED":"0"},
         "path_resolution":"graph refs relative to --data-root; programme bank/protocol relative to this manifest; deps under --cipheur-root",
         "input_registration_scope":"specified input file hashes and source/config/split metadata only; no optimizer result inspection",
         "selection_scope":"provided programme IDs, no selection or adaptation by this dispatcher",
         "negative_and_failed_records":"retained; no automatic retries or pruning; seeded baseline returned after programme failure is explicitly marked",
         "config_alias_scope":"logical A/M/J/stress/W/E/MW/ME retained in job record; benchmark receives actual metadata config_id",
         "original_paths_provenance_only":{"data_root":str(args.data_root.resolve()),"cipheur_root":str(args.cipheur_root.resolve())}}
    dump(args.manifest,registration)
    print(json.dumps({"manifest":str(args.manifest),"sha256":sha(args.manifest),"stage":args.stage,"jobs":len(jobs),"graphs":len(graphs),"programmes":len(programmes)}),flush=True)
    return registration

def verify(args,reg):
    if reg.get("version")!="complete_schedule_stage_v1" or reg["stage"]!=args.stage:raise ValueError("Stage registration mismatch")
    if reg["source_ids"]!=sources(args.stage) or reg["configs"]!=list(STAGES[args.stage]["configs"]):raise ValueError("Stage input domain changed")
    for filename,expected in reg["script_hashes"].items():
        if sha(SCRIPT.with_name(filename))!=expected:raise ValueError("Frozen runtime changed: "+filename)
    for filename,expected in reg["cipheur_hashes"].items():
        if sha(args.cipheur_root/filename)!=expected:raise ValueError("Frozen dependency changed: "+filename)
    for graph in reg["graphs"]:
        for ref,h in (("npz_ref","npz_sha256"),("metadata_ref","metadata_sha256")):
            if sha(args.data_root/graph[ref])!=graph[h]:raise ValueError("Frozen input changed")
    if reg["bank_ref"] and sha(args.manifest.parent/reg["bank_ref"])!=reg["bank_sha256"]:raise ValueError("Frozen programme bank changed")
    if sha(args.manifest.parent/reg["protocol_ref"])!=reg["protocol_sha256"]:raise ValueError("Frozen stage protocol changed")
    if reg["native_executable_sha256"] and (not args.native_executable or sha(args.native_executable)!=reg["native_executable_sha256"]):raise ValueError("Frozen native changed")
    if args.stage=="test":
        protocol=json.loads((args.manifest.parent/reg["protocol_ref"]).read_text(encoding="utf-8"))
        if protocol.get("frozen") is not True or reg["bank_sha256"]!=protocol["frozen_program_bank_sha256"]:raise ValueError("TEST freeze not satisfied")
        if not {v["program_id"] for v in reg["programmes"]}<=set(protocol["final_program_ids"]):raise ValueError("TEST unselected programme")

def command(args,reg,job,output):
    argv=[sys.executable,str(SCRIPT.with_name("full_schedule_benchmark.py")),"--cipheur-root",str(args.cipheur_root),
          "--graph",str(args.data_root/job["npz_ref"]),"--metadata",str(args.data_root/job["metadata_ref"]),
          "--source",job["source"],"--config",job["config"],"--split",job["split"],"--method",job["method"],
          "--seconds",str(job["seconds"]),"--seed",str(job["seed"]),"--protocol",str(args.manifest.parent/reg["protocol_ref"]),"--output",str(output)]
    if job["method"]=="program":argv += ["--program-bank",str(args.manifest.parent/reg["bank_ref"]),"--program-id",job["program_id"]]
    if job["method"].startswith("chils"):argv += ["--native-executable",str(args.native_executable),"--native-output-root",str(output.parent/(output.stem+"_native"))]
    return argv

def worker(index,args,reg,events):
    cpu=reg["cpus"][index]
    try:
        os.sched_setaffinity(0,{cpu});env=dict(os.environ,**reg["thread_environment"])
        for job in reg["jobs"]:
            if job["worker_index"]!=index:continue
            output=args.output_root/"results"/(job["job_id"]+".json");output.parent.mkdir(parents=True,exist_ok=True)
            rec=run_recorded(command(args,reg,job,output),output,env,timeout=args.wall_guard)
            rec.update({k:job.get(k) for k in ("job_id","registered_order","source","config","config_alias","split","method","program_id","arm","seconds","seed")})
            rec.update(worker_index=index,cpu=cpu,worker_pid=os.getpid())
            if output.exists():
                try:
                    result=json.loads(output.read_text(encoding="utf-8"));rec["execution_health"]=execution_health(result)
                    rec["record_cpu_affinity"]=result.get("cpu_affinity")
                    if rec["record_cpu_affinity"]!=[cpu]:rec["affinity_mismatch"]=True
                except Exception as exc:rec["result_parse_error"]=repr(exc)
            with (args.output_root/("worker_cpu_%d.jsonl"%cpu)).open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
            events.put({"type":"record","record":rec})
    except Exception as exc:events.put({"type":"worker_failure","worker_index":index,"cpu":cpu,"error":repr(exc),"traceback":traceback.format_exc()})
    finally:events.put({"type":"worker_done","worker_index":index})

def execute(args,reg):
    verify(args,reg)
    args.output_root=args.output_root.resolve();args.output_root.mkdir(parents=True,exist_ok=True)
    out=args.output_root
    if (out/"execution_receipt.json").exists():raise ValueError("Never overwrite a stage execution or silently retry failures")
    allowed=sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else []
    if not set(reg["cpus"])<=set(allowed):raise ValueError("Registered single-CPU affinity unavailable")
    dump(out/"execution_receipt.json",{"started_utc":now(),"manifest_sha256":sha(args.manifest),"hostname":socket.gethostname(),"python":sys.version,
         "platform":platform.platform(),"pid":os.getpid(),"stage":args.stage,"cpus":reg["cpus"],"allowed_cpus_before_pinning":allowed,
         "load_average_at_start":os.getloadavg(),"job_count":len(reg["jobs"]),"wall_guard_seconds":args.wall_guard})
    ctx=mp.get_context("spawn");events=ctx.Queue();processes=[]
    for index in range(8):
        process=ctx.Process(target=worker,args=(index,args,reg,events));process.start();processes.append(process)
    done=set();rows=[];failures=[];started=time.perf_counter()
    while len(done)<8:
        try:event=events.get(timeout=1.)
        except Exception:
            for index,process in enumerate(processes):
                if index not in done and process.exitcode is not None:
                    done.add(index);failures.append({"worker_index":index,"status":"exited_without_terminal_event","exitcode":process.exitcode})
            continue
        if event["type"]=="worker_done":done.add(event["worker_index"])
        elif event["type"]=="worker_failure":
            failures.append(event)
            with (out/"worker_failures.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(event)+"\n")
        else:
            rec=event["record"];rows.append(rec)
            with (out/"jobs.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
            print(json.dumps({k:rec.get(k) for k in ("registered_order","status","program_id","method","source","config_alias","seconds","seed","cpu")}),flush=True)
    for process in processes:process.join()
    completed={v["job_id"] for v in rows};missing=[v["job_id"] for v in reg["jobs"] if v["job_id"] not in completed]
    groups=defaultdict(list)
    for row in rows:groups[(row["method"],row.get("program_id"),row["arm"],row["seconds"],row["seed"])].append(row)
    summary=[]
    for key,group in groups.items():
        valid=[v for v in group if v["status"]=="complete" and "execution_health" in v]
        summary.append({"method":key[0],"program_id":key[1],"arm":key[2],"seconds":key[3],"seed":key[4],"records":len(group),
                       "status_counts":dict(Counter(v["status"] for v in group)),"feasible_denominator":len(valid),
                       "mean_value_ticks_on_feasible_records":sum(v["execution_health"]["value_ticks"] for v in valid)/len(valid) if valid else None,
                       "head_committed_count":sum(bool(v.get("execution_health",{}).get("head_ever_committed")) for v in group),
                       "programme_error_count":sum(v.get("execution_health",{}).get("programme_error_count",0) for v in group),
                       "interpretation":"descriptive only; this script makes no programme-selection decision"})
    dump(out/"execution_summary.json",{"stage":args.stage,"manifest_sha256":sha(args.manifest),"finished_utc":now(),"registered_jobs":len(reg["jobs"]),
         "recorded_jobs":len(rows),"missing_job_ids":missing,"worker_failures":failures,"worker_exit_codes":[v.exitcode for v in processes],
         "status_counts":dict(Counter(v["status"] for v in rows)),"by_method_budget_seed":summary,
         "execution_wall_seconds":time.perf_counter()-started,"load_average_at_end":os.getloadavg()})
    if missing or failures:raise SystemExit(2)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",choices=STAGES,required=True);p.add_argument("--register",action="store_true");p.add_argument("--execute",action="store_true")
    p.add_argument("--manifest",type=Path,required=True);p.add_argument("--data-root",type=Path,required=True);p.add_argument("--cipheur-root",type=Path,required=True)
    p.add_argument("--graph-root",type=Path);p.add_argument("--graph-manifest",type=Path);p.add_argument("--output-root",type=Path)
    p.add_argument("--program-bank",type=Path);p.add_argument("--program-id",action="append");p.add_argument("--program-ids-json",type=Path);p.add_argument("--all-programs",action="store_true")
    p.add_argument("--method",choices=TRADITIONAL,action="append",default=[]);p.add_argument("--native-executable",type=Path);p.add_argument("--protocol",type=Path)
    p.add_argument("--budgets",type=float,nargs="+",default=[2.,10.]);p.add_argument("--seeds",type=int,nargs="+",default=[2,3,5]);p.add_argument("--cpus",type=int,nargs=8,default=list(range(24,32)))
    p.add_argument("--shuffle-seed",type=int,default=20261005);p.add_argument("--wall-guard",type=float,default=120.)
    args=p.parse_args();args.manifest=args.manifest.resolve()
    if not args.register and not args.execute:p.error("Choose --register and/or --execute")
    if args.register and not args.protocol:p.error("Stage registration requires --protocol")
    if args.execute and not args.output_root:p.error("Execution requires --output-root")
    reg=register(args) if args.register else json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.execute:execute(args,reg)

if __name__=="__main__":main()
