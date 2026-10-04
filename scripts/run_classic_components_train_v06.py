"""Server-only classical-component TRAIN calibration; no candidate code.

All source choices, seeds, phase targets and repair caps are frozen before
outcomes. The experiment is excluded from author packets and the original
120-state selector. Unsupported/error requests remain null, without fallback.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict
from fractions import Fraction
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
STEM="classic_components_train_v06_001"
STAGE=ROOT/"experiments/discovery"/STEM
CONFIG=ROOT/"configs"/(STEM+".json")
CAPSULE=ROOT/"experiments/source_snapshots/v06"/(STEM+"_source.zip")
OUT=ROOT/"output"/STEM
CODE=("cipheur/__init__.py","cipheur/model.py","cipheur/programs.py",
      "cipheur/graph_features.py","cipheur/compiled.py","cipheur/repair_v06.py",
      "cipheur/advanced_baselines.py","cipheur/advanced_baselines_v06.py",
      "scripts/fetch_uai_mmap_v06.py","scripts/run_classic_public_train_v06.py",
      "scripts/run_classic_components_train_v06.py")
STARTUP={n:sha256((ROOT/n).read_bytes()).hexdigest() for n in CODE}
from cipheur.model import Graph
from cipheur.repair_v06 import RepairConfig,repair_schedule
from cipheur.advanced_baselines_v06 import run_solver
from scripts.run_classic_public_train_v06 import INPUTS,REPAIR,raw_graph


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".tmp")
    temp.write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode())
    os.replace(temp,path)


def sources():
    current={n:digest(ROOT/n) for n in CODE}
    if current!=STARTUP:raise ValueError("Source changed after startup/import")
    return current


def input_inventory():
    records=[];uai_inventory=[]
    for family,binding in INPUTS.items():
        assert digest(ROOT/binding["inventory"])==binding["inventory_sha256"]
        assert digest(ROOT/binding["archive"])==binding["archive_sha256"]
        rows=json.loads((ROOT/binding["inventory"]).read_bytes())["records"]
        if family=="UAI":uai_inventory=rows
        for r in rows:
            if r.get("split")!="train" or r.get("parse_status")!="valid":continue
            if family=="UAI" and not (r["negative_weights"]==0 and int(r["scaled_total_weight"])<=2**63-1):continue
            records.append({**r,"input_family":family,"id":family+":"+r["source_cluster"],
                "source_weight_scale":1 if family=="WDP" else int(r["exact_denominator_scale"]),
                "orientation":binding["orientation"]})
    assert len(records)==32 and Counter(r["input_family"] for r in records)=={"WDP":25,"UAI":7}
    assert {r["source_cluster"] for r in records if r["input_family"]=="UAI"}=={
        "Segmentation_12","Segmentation_13","Segmentation_16","Grids_25","Grids_28","Grids_29","ProteinFolding_11"}
    return sorted(records,key=lambda r:r["id"]),uai_inventory


def package():
    if STAGE.exists() or CONFIG.exists() or CAPSULE.exists():raise ValueError("Preserve first component registration")
    assert digest(ROOT/"cipheur/repair_v06.py")=="c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3"
    assert digest(ROOT/"cipheur/advanced_baselines_v06.py")=="713364f084ef9c3538be275b2437e681e6a9d0457dbc028d621ba0bc71ee4477"
    selected,uai=input_inventory()
    config={"version":STEM,"before_any_component_outcomes":True,"split":"train","workers":8,
        "targets":[0.1,1,5],"native_seeds":[1,2,3],"cold_degree_seed":1,
        "native_initial_fraction":0.5,"repair_fraction":0.5,"repair_config":REPAIR,
        "native_hard_wall_guard_seconds":30,"whole_batch_guard_seconds":3600,
        "sources":selected,"input_bindings":INPUTS,"source_sha256":sources(),
        "original_UAI_inventory_retained":uai,"assigned_sources":32,"assigned_requests":960,
        "requests_per_context":30,"CHILS_executable":json.loads((ROOT/"configs/advanced_public_v04_remote.json").read_bytes())["executables"]["CHILS"],
        "methods":"For every source and nominal target: CHILSfull at seeds1/2/3; CHILShalf at seeds1/2/3; same-seed CHILShalf incumbent to Degreewarm with half target; one Degreecold at full target",
        "encoding":"Raw Fraction weight strings times exact per-source integer LCM; WDP integer objective and exact clique complement. No float parsing, rounding, GCD or vertex reduction",
        "warm_semantics":"Validate supplied CHILS incumbent, Degree-feasibly extend it, bounded repair; not a separate cold Degree candidate or best-of-two initializer. Every returned warm incumbent exact reward must be >= native seed",
        "reuse_and_cost":"Native half-phase receipt is shared with its same-seed warm pipeline. Report its measured wrapper selfCPU+childCPU+wall charged once to standalone pipeline plus repair actualCPU/wall. Report actual shared batch/context costs and graph loading separately.",
        "timing_scope":"Native internal nominal wall and cooperative repair wall; actual wrapper preparation/startup/checking/overshoot retained. Targets are not matched end-to-end hard deadlines, and C++ versus Python implementation cost remains explicit.",
        "failures":"All assignments retained. Unsupported native input or native initialization error gives null comparison/advanced-track output, never hidden fallback. Normal repair caps retain anytime feasible incumbent; programme/runner errors explicit diagnostics, not primary successful quality.",
        "scope":"Classical components only, no LLM candidate/program reads, no authoring packet access, no TEST; previously seen28TRAIN sources plus all4 previously unoptimized exact64-compatible UAI TRAIN sources",
        "use_restriction":"Do not send outcomes to R2 authors or selector. Original120-state evidence/commonfeedback/selector and original1008calibration stay immutable.",
        "model_calls":0,"oracle_calls":0,"TEST_execution_permitted":False}
    write(CONFIG,config)
    write(STAGE/"registration.json",{"registered_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "before_any_component_outcomes":True,"config_sha256":digest(CONFIG),"source_sha256":config["source_sha256"]})
    names=[*CODE,CONFIG.relative_to(ROOT).as_posix(),(STAGE/"registration.json").relative_to(ROOT).as_posix(),
           INPUTS["WDP"]["inventory"],INPUTS["UAI"]["inventory"]]
    files={n:digest(ROOT/n) for n in names}
    CAPSULE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(CAPSULE,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for n in sorted(files):z.writestr(n,(ROOT/n).read_bytes())
    receipt={"before_any_component_outcomes":True,"source_zip_sha256":digest(CAPSULE),
             "config_sha256":digest(CONFIG),"files_sha256":files,"assigned_requests":960}
    write(STAGE/"capsule_receipt.json",receipt)
    print(json.dumps(receipt),flush=True)


def verify_package():
    receipt=json.loads((STAGE/"capsule_receipt.json").read_bytes())
    assert digest(CAPSULE)==receipt["source_zip_sha256"]
    for n,e in receipt["files_sha256"].items():assert digest(ROOT/n)==e,n
    config=json.loads(CONFIG.read_bytes())
    assert config["source_sha256"]==sources() and config["repair_config"]==REPAIR==asdict(RepairConfig(**REPAIR))
    assert config["before_any_component_outcomes"] and not config["TEST_execution_permitted"]
    assert input_inventory()[0]==config["sources"]
    assert config["targets"]==[0.1,1,5] and config["native_seeds"]==[1,2,3]
    assert digest(config["CHILS_executable"]["path"])==config["CHILS_executable"]["sha256"]
    return config,receipt


def prepare(config,receipt):
    OUT.mkdir(parents=True,exist_ok=False)
    contexts=[]
    for family,binding in INPUTS.items():
        with tarfile.open(ROOT/binding["archive"]) as t:
            for r in config["sources"]:
                if r["input_family"]!=family:continue
                assert r["split"]=="train"
                raw=t.extractfile(binding["member_root"]+"/"+r["path"]).read()
                assert sha256(raw).hexdigest()==r["raw_sha256"]
                graph=raw_graph(raw,r)
                name="graphs/"+sha256(r["id"].encode()).hexdigest()[:16]+".json"
                write(OUT/name,graph.to_dict())
                contexts.append({**r,"graph_file":name,"graph_file_sha256":digest(OUT/name),
                    "graph_sha256":graph.digest(),"m_conflict":len(graph.edges)})
    contexts.sort(key=lambda r:r["id"])
    protocol={**config,"contexts":contexts,"prepared_before_any_solver":True,
        "source_zip_sha256":receipt["source_zip_sha256"],"config_sha256":digest(CONFIG)}
    write(OUT/"protocol.json",protocol)
    write(OUT/"freeze_receipt.json",{"before_any_component_outcomes":True,
        "protocol_sha256":digest(OUT/"protocol.json"),"source_zip_sha256":receipt["source_zip_sha256"],
        "graph_files_sha256":{r["graph_file"]:r["graph_file_sha256"] for r in contexts}})
    return protocol


def template(c,target,track,seed):
    return {"id":c["id"],"input_family":c["input_family"],"family":c["family"],"source_cluster":c["source_cluster"],
        "split":"train","source_path":c["path"],"source_sha256":c["raw_sha256"],"graph_sha256":c["graph_sha256"],
        "n":c["n"],"m":c["m_conflict"],"source_weight_scale":c["source_weight_scale"],
        "nominal_wall_target_seconds":target,"track":track,"seed":seed}


def expected(c):
    for target in (0.1,1,5):
        for track in ("CHILSfull","CHILShalf","Degreewarm"):
            for seed in (1,2,3):yield template(c,target,track,seed)
        yield template(c,target,"Degreecold",1)


def key(r):return r["id"],r["nominal_wall_target_seconds"],r["track"],r["seed"]


def execute_context(c,config):
    started,cpu=time.perf_counter(),time.process_time()
    assert c["split"]=="train" and digest(OUT/c["graph_file"])==c["graph_file_sha256"]
    graph=Graph.from_dict(json.loads((OUT/c["graph_file"]).read_bytes()))
    assert graph.digest()==c["graph_sha256"]
    token=sha256(c["id"].encode()).hexdigest()[:16]
    write(OUT/"context_loading"/(token+".json"),{"id":c["id"],"shared_graph_load_wall_seconds":time.perf_counter()-started,
        "shared_graph_load_cpu_seconds":time.process_time()-cpu,"shared_by_requests":30})
    path=OUT/"context_results"/(token+".jsonl");path.parent.mkdir(parents=True,exist_ok=True)
    def emit(stream,row,result,error=None,extra=None):
        valid=error is None and result is not None and result.get("completed") is True and result.get("feasible") is True
        original=(str(Fraction(result["value_exact"])/c["source_weight_scale"])
                  if result and result.get("value_exact") is not None else None)
        row.update(result=result,runner_error=error,assignment_returned=True,successful_assignment=valid,
            quality_reward_exact_original_objective=original if valid else None,
            diagnostic_retained_reward_exact_original_objective=original if not valid else None)
        if extra:row.update(extra)
        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n");stream.flush()
    def native(seconds,seed):
        before,self_cpu=time.perf_counter(),time.process_time()
        result=run_solver(graph,config["CHILS_executable"]["path"],"CHILS",seconds=seconds,seed=seed,hard_wall_seconds=30)
        result.update(wrapper_wall_seconds=time.perf_counter()-before,wrapper_self_cpu_seconds=time.process_time()-self_cpu)
        return result
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        for target in config["targets"]:
            for seed in config["native_seeds"]:
                result=None;error=None
                try:result=native(target,seed)
                except Exception as e:error={"type":type(e).__name__,"message":str(e)}
                emit(stream,template(c,target,"CHILSfull",seed),result,error)
            for seed in config["native_seeds"]:
                initial=None;error=None
                try:initial=native(target*0.5,seed)
                except Exception as e:error={"type":type(e).__name__,"message":str(e)}
                emit(stream,template(c,target,"CHILShalf",seed),initial,error,{"native_phase_nominal_seconds":target*0.5})
                row=template(c,target,"Degreewarm",seed)
                if error or initial is None or not initial["completed"] or not initial["feasible"]:
                    emit(stream,row,None,{"type":"NativeInitializerUnavailable","message":"No fallback or replacement"},
                        {"native_initial_response":initial});continue
                before,self_cpu=time.perf_counter(),time.process_time();result=None;error=None
                try:
                    result=repair_schedule(graph,priority="degree",initial=initial["selected"],seconds=target*0.5,
                        clock="wall",config=RepairConfig(**config["repair_config"]),random_seed=1)
                    assert Fraction(result["value_exact"])>=Fraction(initial["value_exact"])
                except Exception as e:error={"type":type(e).__name__,"message":str(e)}
                policy_wall=time.perf_counter()-before;policy_cpu=time.process_time()-self_cpu
                emit(stream,row,result,error,{"native_phase_nominal_seconds":target*0.5,"repair_phase_nominal_seconds":target*0.5,
                    "native_initial_value_exact":initial["value_exact"],"native_initial_selected":initial["selected"],
                    "native_initial_wrapper_wall_seconds":initial["wrapper_wall_seconds"],
                    "native_initial_wrapper_self_cpu_seconds":initial["wrapper_self_cpu_seconds"],
                    "native_initial_child_cpu_seconds":initial.get("child_cpu_seconds"),
                    "repair_wrapper_wall_seconds":policy_wall,"repair_wrapper_cpu_seconds":policy_cpu,
                    "standalone_pipeline_wall_seconds":initial["wrapper_wall_seconds"]+policy_wall,
                    "standalone_pipeline_cpu_seconds":initial["wrapper_self_cpu_seconds"]+initial.get("child_cpu_seconds",0)+policy_cpu,
                    "initial_cost_shared_with_half_baseline_actual_execution":True})
            before,self_cpu=time.perf_counter(),time.process_time();result=None;error=None
            try:result=repair_schedule(graph,priority="degree",seconds=target,clock="wall",config=RepairConfig(**config["repair_config"]),random_seed=1)
            except Exception as e:error={"type":type(e).__name__,"message":str(e)}
            emit(stream,template(c,target,"Degreecold",1),result,error,
                {"repair_wrapper_wall_seconds":time.perf_counter()-before,"repair_wrapper_cpu_seconds":time.process_time()-self_cpu})
    write(OUT/"context_execution"/(token+".json"),{"id":c["id"],"actual_shared_context_wall_seconds":time.perf_counter()-started,
        "actual_shared_context_self_cpu_seconds":time.process_time()-cpu,"assigned":30})
    return c["id"]


def worker_run():
    config,_=verify_package()
    protocol=json.loads((OUT/"protocol.json").read_bytes());freeze=json.loads((OUT/"freeze_receipt.json").read_bytes())
    assert digest(OUT/"protocol.json")==freeze["protocol_sha256"]
    assert protocol["source_sha256"]==sources() and len(protocol["contexts"])==32
    if (OUT/"results.jsonl").exists():raise ValueError("Do not rerun/resume/overwrite outcomes")
    counts=Counter();statuses=Counter();started=time.perf_counter()
    with (OUT/"results.jsonl").open("x",encoding="utf-8",newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=8) as pool:
            fs={pool.submit(execute_context,c,config):c for c in protocol["contexts"]}
            for f in as_completed(fs):
                c=fs[f];error=None
                try:assert f.result()==c["id"]
                except Exception as e:error={"type":type(e).__name__,"message":str(e)}
                path=OUT/"context_results"/(sha256(c["id"].encode()).hexdigest()[:16]+".jsonl")
                rows=[]
                if path.exists():
                    for line in path.read_text().splitlines():
                        try:rows.append(json.loads(line))
                        except json.JSONDecodeError:break
                observed={key(r) for r in rows};assert len(observed)==len(rows)
                for r in expected(c):
                    if key(r) not in observed:
                        r.update(result=None,runner_error=error or {"type":"MissingWorkerReceipt","message":"Assigned request retained; no retry"},
                            assignment_returned=True,successful_assignment=False,quality_reward_exact_original_objective=None);rows.append(r)
                assert len(rows)==30 and {key(r) for r in rows}=={key(r) for r in expected(c)}
                for r in rows:
                    stream.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+"\n")
                    counts["returned"]+=1;counts["successful"]+=r["successful_assignment"]
                    statuses[r["track"]+":"+(r["result"]["status"] if r.get("result") else r["runner_error"]["type"])]+=1
                stream.flush();counts["sources_returned"]+=1
                write(OUT/"progress.json",{"assigned":960,**dict(counts),"status_counts":dict(statuses),"wall_seconds":time.perf_counter()-started})
    assert counts["returned"]==960
    write(OUT/"completion.json",{"assigned":960,**dict(counts),"status_counts":dict(statuses),
        "wall_seconds":time.perf_counter()-started,"results_sha256":digest(OUT/"results.jsonl"),
        "protocol_sha256":digest(OUT/"protocol.json"),"source_zip_sha256":protocol["source_zip_sha256"],
        "TEST_solver_calls":0,"LLM_candidate_reads":0,"oracle_calls":0,"model_calls":0})


def server_run():
    if platform.system()!="Linux":raise ValueError("Research run is server-only")
    config,receipt=verify_package()
    if (STAGE/"host_receipt.json").exists():raise ValueError("Preserve first execution")
    started=time.perf_counter()
    host={"before_any_component_outcomes":True,"timestamp_unix":time.time(),"pid":os.getpid(),
        "python":sys.version,"platform":platform.platform(),"workers":8,
        "cpu_max":Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "memory_max":Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        "source_zip_sha256":receipt["source_zip_sha256"],"config_sha256":digest(CONFIG)}
    write(STAGE/"host_receipt.json",host)
    protocol=prepare(config,receipt);prepare_wall=time.perf_counter()-started
    guard=False
    with (OUT/"worker.log").open("xb") as stream:
        child=subprocess.Popen([sys.executable,"scripts/run_classic_components_train_v06.py","worker-run"],cwd=ROOT,
            stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
            env={**os.environ,"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1"})
        write(STAGE/"launch_receipt.json",{"child_pid":child.pid,"timestamp_unix":time.time(),"assigned":960,
            "protocol_sha256":digest(OUT/"protocol.json"),"freeze_receipt_sha256":digest(OUT/"freeze_receipt.json"),
            "prepared_before_launch":True,"whole_batch_guard_seconds":3600})
        try:code=child.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            guard=True;os.killpg(child.pid,signal.SIGTERM)
            try:code=child.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
    if code or guard:
        observed=set()
        for journal in (OUT/"context_results").glob("*.jsonl"):
            for line in journal.read_text().splitlines():
                try:observed.add(key(json.loads(line)))
                except json.JSONDecodeError:break
        with (OUT/"unreturned_assignments.jsonl").open("x",encoding="utf-8",newline="\n") as stream:
            for c in protocol["contexts"]:
                for r in expected(c):
                    if key(r) not in observed:
                        r.update(result=None,runner_error={"type":"WholeBatchGuard" if guard else "WorkerBatchExit"},
                            assignment_returned=False,successful_assignment=False,quality_reward_exact_original_objective=None)
                        stream.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+"\n")
    for name in ("registration.json","capsule_receipt.json","host_receipt.json","launch_receipt.json"):
        (OUT/name).write_bytes((STAGE/name).read_bytes())
    (OUT/"registered_config.json").write_bytes(CONFIG.read_bytes())
    write(OUT/"server_execution_receipt.json",{"source_zip_sha256":receipt["source_zip_sha256"],
        "full_verify_prepare_run_wall_seconds":time.perf_counter()-started,"shared_prepare_wall_seconds":prepare_wall,
        "whole_batch_guard_triggered":guard,"exit_code":code,"retries":0,"all_partial_results_retained":True,
        "TEST_solver_calls":0,"LLM_candidate_reads":0,"oracle_calls":0,"model_calls":0})
    archive=ROOT/"experiments/runs/v06"/(STEM+".tar.gz");archive.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,"x:gz") as t:t.add(OUT,arcname=STEM)
    write(STAGE/"archive_receipt.json",{"archive_sha256":digest(archive),"archive_bytes":archive.stat().st_size,
        "execution_complete":(OUT/"completion.json").exists() and code==0 and not guard})
    print(json.dumps(json.loads((STAGE/"archive_receipt.json").read_bytes())),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=("package","server-run","worker-run"))
    a=p.parse_args();{"package":package,"server-run":server_run,"worker-run":worker_run}[a.mode]()
