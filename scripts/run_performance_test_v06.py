"""Frozen two-initializer TEST orchestration; execution requires root release.

Plan and input preparation never call a solver or read candidate responses.
Binding accepts only twelve genuinely TRAIN-selected programs plus separately
frozen quality-only controls. Both kernel tracks and all published requests are
registered before TEST, with immutable source/input/selection barriers.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
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
CODE=("cipheur/__init__.py","cipheur/model.py","cipheur/programs.py",
      "cipheur/graph_features.py","cipheur/compiled.py","cipheur/repair_v06.py",
      "cipheur/advanced_baselines.py","cipheur/advanced_baselines_v06.py",
      "scripts/fetch_uai_mmap_v06.py","scripts/run_classic_public_train_v06.py",
      "scripts/run_performance_test_v06.py")
STARTUP={n:sha256((ROOT/n).read_bytes()).hexdigest() for n in CODE}
from cipheur.model import Graph
from cipheur.repair_v06 import RepairConfig,repair_schedule
from cipheur.graph_features import FeatureRuleProgram
from cipheur.advanced_baselines_v06 import run_solver
from scripts.run_classic_public_train_v06 import INPUTS,METHODS,REPAIR,raw_graph

PERFORMANCE="experiments/runs/v06/performance_inputs_v06_001.tar.gz"
PERFORMANCE_SHA="1f853ec90153ecd65418119352c13d9e17242e6dddd407ed8eaa45f7bf3aa20b"
C3="experiments/runs/v06/c3_interval_inputs_v06_001.tar.gz"
C3_SHA="af7c0295a8db99e3eacb8d5d6e1a0183a87808312ca04bb280f01e10b69323a9"


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".tmp")
    temp.write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode())
    os.replace(temp,path)


def sources():
    current={n:digest(ROOT/n) for n in CODE}
    if current!=STARTUP:raise ValueError("Source changed after startup/import")
    return current


def prepared_input_bindings(include_uai64=False):
    assert digest(ROOT/PERFORMANCE)==PERFORMANCE_SHA
    public=[]
    for family,binding in INPUTS.items():
        assert digest(ROOT/binding["inventory"])==binding["inventory_sha256"]
        assert digest(ROOT/binding["archive"])==binding["archive_sha256"]
        for r in json.loads((ROOT/binding["inventory"]).read_bytes())["records"]:
            if r.get("split")!="test" or r.get("parse_status")!="valid":continue
            common_supported=family!="UAI" or r["direct_native_signed32_compatible"]
            additional64=(family=="UAI" and include_uai64 and not common_supported and
                          r["family"]=="Grids" and r["negative_weights"]==0 and
                          int(r["scaled_total_weight"])<=2**63-1)
            if not common_supported and not additional64:continue
            public.append({**r,"input_family":family,"id":family+":"+r["source_cluster"],
                "population":"WDP" if family=="WDP" else "UAI_Segmentation" if common_supported else "UAI_Grids_CHILS64",
                "source_weight_scale":binding["weight_scale"] if common_supported else int(r["exact_denominator_scale"]),
                "orientation":binding["orientation"],
                "encoding_scope":"exact_CHILS64_only" if family=="WDP" or additional64 else "common_signed32"})
    assert Counter(c["input_family"] for c in public)=={"WDP":25,"UAI":13 if include_uai64 else 3}
    assert {c["source_cluster"] for c in public if c["population"]=="UAI_Segmentation"}=={
        "Segmentation_14","Segmentation_18","Segmentation_19"}
    if include_uai64:assert sum(c["population"]=="UAI_Grids_CHILS64" for c in public)==10
    return sorted(public,key=lambda c:c["id"])


def plan_only(study,include_c3,include_uai64=False):
    study=Path(study)
    if study.exists():raise ValueError("Preserve first performance registration")
    public=prepared_input_bindings(include_uai64)
    if include_c3!="none":assert digest(ROOT/C3)==C3_SHA
    config={"version":"performance_test_v06_001","before_any_TEST_solver_outcomes":True,
        "workers":8,"wall_targets":[0.1,1,5],"native_requests":[m for m in METHODS if m["method"]!="Degree"],
        "repair_config":REPAIR,"common_seed":1,"native_hard_wall_guard_seconds":30,
        "whole_batch_wall_guard_seconds":14400,"strong_initializer_fraction":0.5,
        "cold_track":"Common Degree initialization plus bounded repair with full nominal T",
        "warm_track":"Common CHILS(seed1,nominal T/2) feasible incumbent, Degree-feasible extension, then bounded repair with nominal T/2; unchanged kernel",
        "warm_failure":"Failed/unsupported native initializer makes all associated warm rows explicitly unavailable with null value; no hidden Degree or other fallback",
        "warm_monotonicity":"Every returned warm incumbent must be exact source-feasible and have reward >= the supplied CHILS initial incumbent; no separate cold Degree candidate or best-of-two seed",
        "warm_reuse":"One deterministic native initializer is executed per graph/target and shared across all15 policy rows. Each standalone warm-pipeline cost is charged the same measured initialization cost plus its own repair cost; actual shared execution wall/CPU is separate.",
        "policy_slots":15,"genuine_proposed_slots":12,"quality_only_control_slots":2,
        "assignments_per_source_target":42,"core_contexts":244+(10 if include_uai64 else 0),
        "core_assignments":(244+(10 if include_uai64 else 0))*126,
        "include_additional_UAI_Grids_CHILS64":include_uai64,
        "optional_c3_track":include_c3,"optional_c3_contexts":0 if include_c3=="none" else 48 if include_c3=="both" else 24,
        "fresh_synthetic_archive":PERFORMANCE,"fresh_synthetic_archive_sha256":PERFORMANCE_SHA,
        "public_input_bindings":INPUTS,"public_TEST_sources":public,
        "optional_c3_archive":C3 if include_c3!="none" else None,
        "optional_c3_archive_sha256":C3_SHA if include_c3!="none" else None,
        "executables":json.loads((ROOT/"configs/advanced_public_v04_remote.json").read_bytes())["executables"],
        "selection_barrier":"Exactly12 genuine TRAIN winners, three arms ×four complete matched blocks, separately SHA-bound two quality-only control banks; no TEST-selected substitution",
        "root_release_barrier":"A root-owned authorization JSON must explicitly bind the frozen protocol, source capsule, program selection and control selection before server launch",
        "timing":"Nominal native internal wall targets and cooperative Python repair wall targets. Full native preparation/startup/checking, repair CPU/wall, shared graph loading and actual overshoot retained. Equal targets are not matched end-to-end hard deadlines or language-independent fairness.",
        "failure":"Every assigned method/seed/track retained; unsupported encoding and solver/runner failures null rather than manufactured zero reward. Returned anytime caps retain feasible incumbents. Programme-error retained incumbents are diagnostic, with completed=false.",
        "quality":"Exact original feasible objective. Analyze WDP/UAI/synthetic/C3 populations separately. Any later quality denominator must be explicitly sourced, not called exact optimum without proof.",
        "unit_semantics":"WDP integral original objective with exact clique complement; UAI scale100000 exact rational objective; synthetic quarters; original C3 integer duration objective and separately labeled legacy versus interval models",
        "no_online_LLM_or_conditional_oracle":True,"source_sha256":sources(),
        "selection_config_scope":"Performance caps differ from original .5s/200k/4096/32 authoring selector; original TRAIN assessment and candidate ASTs remain unchanged"}
    study.mkdir(parents=True)
    write(study/"protocol.json",config)
    write(study/"freeze_receipt.json",{"before_any_TEST_solver_outcomes":True,
        "registered_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "protocol_sha256":digest(study/"protocol.json"),"source_sha256":config["source_sha256"]})
    capsule=study/"source.zip"
    with zipfile.ZipFile(capsule,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for name in CODE:z.writestr(name,(ROOT/name).read_bytes())
        for family,binding in INPUTS.items():z.writestr(binding["inventory"],(ROOT/binding["inventory"]).read_bytes())
        z.writestr(study.relative_to(ROOT).as_posix()+"/protocol.json",(study/"protocol.json").read_bytes())
        z.writestr(study.relative_to(ROOT).as_posix()+"/freeze_receipt.json",(study/"freeze_receipt.json").read_bytes())
    write(study/"capsule_receipt.json",{"before_any_TEST_solver_outcomes":True,"source_zip_sha256":digest(capsule),
        "source_sha256":config["source_sha256"],"protocol_sha256":digest(study/"protocol.json")})
    return config


def verify_study(study):
    study=Path(study)
    protocol=json.loads((study/"protocol.json").read_bytes())
    freeze=json.loads((study/"freeze_receipt.json").read_bytes())
    capsule=json.loads((study/"capsule_receipt.json").read_bytes())
    assert digest(study/"protocol.json")==freeze["protocol_sha256"]==capsule["protocol_sha256"]
    assert digest(study/"source.zip")==capsule["source_zip_sha256"]
    assert sources()==protocol["source_sha256"]==freeze["source_sha256"]==capsule["source_sha256"]
    assert protocol["repair_config"]==REPAIR==asdict(RepairConfig(**REPAIR))
    assert protocol["wall_targets"]==[0.1,1,5] and protocol["strong_initializer_fraction"]==0.5
    assert prepared_input_bindings(protocol["include_additional_UAI_Grids_CHILS64"])==protocol["public_TEST_sources"]
    if protocol["optional_c3_track"]!="none":assert digest(ROOT/C3)==protocol["optional_c3_archive_sha256"]
    return protocol,capsule


def bind_selections(study,selection,selection_sha,controls,controls_sha):
    study=Path(study);protocol,capsule=verify_study(study)
    if (study/"deployment.json").exists():raise ValueError("Do not replace frozen performance ASTs")
    assert digest(selection)==selection_sha and digest(controls)==controls_sha
    selected=json.loads(Path(selection).read_bytes());control=json.loads(Path(controls).read_bytes())
    assert selected["selection_split"]=="train" and selected["test_accessed"] is False
    assert selected["all_cells_have_genuine_winner"] is True and len(selected["programs"])==12
    assert control["selection_split"]=="train" and control["test_accessed"] is False and control["all64_original_slots_assessed"]
    programs=[];cells=set()
    for r in selected["programs"]:
        assert r["arm"] in ("witness","relations","objective") and type(r["block"]) is int
        assert canonical(r["program"])==r["program_sha256"]
        assert FeatureRuleProgram.from_dict(r["program"]).to_dict()==r["program"]
        cells.add((r["block"],r["arm"]))
        programs.append({**r,"method_id":r["id"],"kind":"genuine_TRAIN_winner","available":True})
    blocks=sorted({r["block"] for r in selected["programs"]})
    assert len(blocks)==4 and cells=={(b,a) for b in blocks for a in ("witness","relations","objective")}
    if "matched_transport_complete_blocks" in selected:assert blocks==selected["matched_transport_complete_blocks"]
    for bank in ("enumerated_structural","fixed_base9"):
        rows=[r for r in control["selections"] if r["block"]==0 and r["bank"]==bank and r["used_for_performance"]]
        assert len(rows)==1
        winner=rows[0]["quality_only_baseline"]
        if winner is None:
            programs.append({"method_id":"quality_only_"+bank,"kind":"quality_only_control",
                             "bank":bank,"available":False,"program":None,"program_sha256":None})
        else:
            assert canonical(winner["program"])==winner["program_sha256"]
            assert FeatureRuleProgram.from_dict(winner["program"]).to_dict()==winner["program"]
            programs.append({**winner,"method_id":"quality_only_"+bank,"kind":"quality_only_control",
                             "bank":bank,"available":True,"joint_eligible":winner["eligible"]})
    programs.append({"method_id":"Degree","kind":"shared_classical_priority","available":True,"program":None})
    assert len(programs)==15 and len({r["method_id"] for r in programs})==15
    deployment={"selection_sha256":selection_sha,"controls_selection_sha256":controls_sha,
        "protocol_sha256":digest(study/"protocol.json"),"source_zip_sha256":capsule["source_zip_sha256"],
        "programs":programs,"genuine_winners":12,"matched_blocks":blocks,
        "no_TEST_tuning":True,"before_any_TEST_solver_outcomes":True}
    (study/"TRAIN_selection.json").write_bytes(Path(selection).read_bytes())
    (study/"controls_TRAIN_selection.json").write_bytes(Path(controls).read_bytes())
    write(study/"deployment.json",deployment)
    return deployment


def prepare_inputs(study,out):
    study,out=Path(study),Path(out);protocol,_=verify_study(study)
    if platform.system()!="Linux":raise ValueError("Large performance graph preparation is server-only")
    out.mkdir(parents=True,exist_ok=False)
    contexts=[]
    def add(meta,graph_dict):
        graph=Graph.from_dict(graph_dict)
        identity=graph.digest()
        if meta.get("graph_sha256") is not None:assert identity==meta["graph_sha256"]
        name="graphs/"+sha256(meta["id"].encode()).hexdigest()[:16]+".json"
        write(out/name,graph_dict)
        contexts.append({**meta,"graph_sha256":identity,"graph_file":name,"graph_file_sha256":digest(out/name),
                         "n":len(graph.nodes),"m":len(graph.edges)})
    with tarfile.open(ROOT/PERFORMANCE) as t:
        data=json.load(t.extractfile("performance_inputs_v06_001/data.json"))
    assert len(data["contexts"])==216
    for c in data["contexts"]:
        assert c["split"]=="test"
        add({k:v for k,v in {**c,"population":"fresh_"+c["family"],"source_weight_scale":1}.items() if k!="graph"},c["graph"])
    for family,binding in INPUTS.items():
        with tarfile.open(ROOT/binding["archive"]) as t:
            for c in protocol["public_TEST_sources"]:
                if c["input_family"]!=family:continue
                raw=t.extractfile(binding["member_root"]+"/"+c["path"]).read()
                assert sha256(raw).hexdigest()==c["raw_sha256"]
                add(c,raw_graph(raw,c).to_dict())
    if protocol["optional_c3_track"]!="none":
        with tarfile.open(ROOT/C3) as t:
            data=json.load(t.extractfile("c3_interval_inputs_v06_001/data.json"))
        for c in data["contexts"]:
            scope=protocol["optional_c3_track"]
            if scope!="both" and not c["population"].startswith("C3_"+scope+"_"):continue
            add({k:v for k,v in c.items() if k!="graph"},c["graph"])
    assert len(contexts)==protocol["core_contexts"]+protocol["optional_c3_contexts"]
    assert len({c["id"] for c in contexts})==len(contexts)
    contexts.sort(key=lambda c:c["id"])
    write(out/"context_inventory.json",{"contexts":contexts,"optimization_calls":0})
    write(out/"input_freeze.json",{"before_any_TEST_solver_outcomes":True,
        "context_inventory_sha256":digest(out/"context_inventory.json"),"source_protocol_sha256":digest(study/"protocol.json"),
        "contexts":len(contexts),"assignments":len(contexts)*3*42,
        "graph_files_sha256":{c["graph_file"]:c["graph_file_sha256"] for c in contexts}})
    return len(contexts)


def row_template(c,target,track,method,seed=1):
    return {"id":c["id"],"population":c["population"],"split":c["split"],"n":c["n"],"m":c["m"],
        "pair_id":c.get("pair_id"),"side":c.get("side"),"graph_sha256":c["graph_sha256"],
        "source_weight_scale":c["source_weight_scale"],"nominal_wall_target_seconds":target,
        "track":track,"method":method,"seed":seed}


def key(row):return row["id"],row["nominal_wall_target_seconds"],row["track"],row["method"],row["seed"]


def expected_rows(c,protocol,deployment):
    for target in protocol["wall_targets"]:
        for m in protocol["native_requests"]:yield row_template(c,target,"native",m["method"],m["seed"])
        yield row_template(c,target,"common_initializer","CHILS_half",1)
        for track in ("cold_Degree","warm_CHILS"):
            for p in deployment["programs"]:yield row_template(c,target,track,p["method_id"],1)


def run_context(c,protocol,deployment,out):
    out=Path(out);wall0,cpu0=time.perf_counter(),time.process_time()
    assert digest(out/c["graph_file"])==c["graph_file_sha256"]
    graph=Graph.from_dict(json.loads((out/c["graph_file"]).read_bytes()))
    assert graph.digest()==c["graph_sha256"]
    loading={"id":c["id"],"graph_sha256":c["graph_sha256"],
        "shared_graph_load_wall_seconds":time.perf_counter()-wall0,"shared_graph_load_cpu_seconds":time.process_time()-cpu0}
    token=sha256(c["id"].encode()).hexdigest()[:16]
    write(out/"context_loading"/(token+".json"),loading)
    log=out/"context_results"/(token+".jsonl");log.parent.mkdir(parents=True,exist_ok=True)
    def emit(stream,row,result,error=None,extra=None):
        success=error is None and result is not None and result.get("completed") is True and result.get("feasible") is True
        original=(str(Fraction(result["value_exact"])/c["source_weight_scale"])
                  if result and result.get("value_exact") is not None else None)
        row.update(result=result,runner_error=error,assignment_returned=True,
                   successful_assignment=success,value_exact_original_objective=original,
                   quality_reward_exact_original_objective=original if success else None,
                   diagnostic_retained_reward_exact_original_objective=original if not success else None)
        if extra:row.update(extra)
        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n");stream.flush()
    with log.open("x",encoding="utf-8",newline="\n") as stream:
        for target in protocol["wall_targets"]:
            for m in protocol["native_requests"]:
                row=row_template(c,target,"native",m["method"],m["seed"])
                try:
                    native_wall,native_cpu=time.perf_counter(),time.process_time()
                    name="CHILS" if m["method"]=="CHILS_ILS" else m["method"]
                    result=run_solver(graph,protocol["executables"][name]["path"],m["method"],seconds=target,
                                      seed=m["seed"],hard_wall_seconds=30)
                    result.update(wrapper_self_cpu_seconds=time.process_time()-native_cpu,
                                  wrapper_wall_seconds=time.perf_counter()-native_wall)
                    emit(stream,row,result)
                except Exception as e:emit(stream,row,None,{"type":type(e).__name__,"message":str(e)})
            row=row_template(c,target,"common_initializer","CHILS_half",1)
            initial=None;initial_error=None
            try:
                native_wall,native_cpu=time.perf_counter(),time.process_time()
                initial=run_solver(graph,protocol["executables"]["CHILS"]["path"],"CHILS",seconds=target*0.5,
                                   seed=1,hard_wall_seconds=30)
                initial.update(wrapper_self_cpu_seconds=time.process_time()-native_cpu,
                               wrapper_wall_seconds=time.perf_counter()-native_wall)
            except Exception as e:initial_error={"type":type(e).__name__,"message":str(e)}
            emit(stream,row,initial,initial_error,{"native_phase_nominal_seconds":target*0.5,
                "shared_initializer_receipt_sha256":canonical(initial) if initial else None})
            for track in ("cold_Degree","warm_CHILS"):
                for p in deployment["programs"]:
                    row=row_template(c,target,track,p["method_id"],1)
                    extra={"program_sha256":p.get("program_sha256"),"program_kind":p["kind"],
                           "policy_nominal_seconds":target if track=="cold_Degree" else target*0.5}
                    if not p["available"]:
                        emit(stream,row,None,{"type":"MissingFrozenQualityOnlyControl","message":"No completed feasible TRAIN control winner; no replacement"},extra);continue
                    if track=="warm_CHILS" and (initial_error or initial is None or not initial["completed"] or not initial["feasible"]):
                        extra.update(native_initial_result=initial,advanced_track_available=False,
                                     shared_initializer_receipt_sha256=canonical(initial) if initial else None)
                        emit(stream,row,None,{"type":"NativeInitializerUnavailable","message":"Preserve native initialization failure; no hidden fallback"},extra);continue
                    started,cpu=time.perf_counter(),time.process_time()
                    result=None;error=None
                    try:
                        result=repair_schedule(graph,program=p["program"],priority="degree" if p["method_id"]=="Degree" else "program",
                            seconds=extra["policy_nominal_seconds"],clock="wall",config=RepairConfig(**protocol["repair_config"]),
                            initial=initial["selected"] if track=="warm_CHILS" else None,random_seed=1)
                        if track=="warm_CHILS":assert Fraction(result["value_exact"])>=Fraction(initial["value_exact"])
                    except Exception as e:error={"type":type(e).__name__,"message":str(e)}
                    extra.update(policy_wrapper_wall_seconds=time.perf_counter()-started,
                                 policy_wrapper_cpu_seconds=time.process_time()-cpu)
                    if track=="warm_CHILS":
                        extra.update(native_initial_value_exact=initial["value_exact"],
                            native_initial_selected=initial["selected"],
                            shared_initializer_receipt_sha256=canonical(initial),
                            standalone_pipeline_wall_seconds=initial["seconds"]+extra["policy_wrapper_wall_seconds"],
                            standalone_pipeline_cpu_seconds=initial.get("child_cpu_seconds",0)+initial["wrapper_self_cpu_seconds"]+extra["policy_wrapper_cpu_seconds"],
                            native_initialization_cost_shared_in_actual_execution=True,advanced_track_available=True)
                    emit(stream,row,result,error,extra)
    write(out/"context_execution"/(token+".json"),{"id":c["id"],"actual_shared_context_wall_seconds":time.perf_counter()-wall0,
        "actual_shared_context_self_cpu_seconds":time.process_time()-cpu0,"requests":126,
        "cost_scope":"Actual execution reuses one CHILS-half initializer per target; standalone pipeline charges are reported separately"})
    return c["id"]


def worker_run(study,out):
    study,out=Path(study),Path(out);protocol,_=verify_study(study)
    deployment=json.loads((study/"deployment.json").read_bytes())
    root_release=json.loads((out/"root_release.json").read_bytes())
    assert root_release["approved_TEST_launch"] is True
    assert root_release["deployment_sha256"]==digest(study/"deployment.json")
    assert digest(study/"TRAIN_selection.json")==deployment["selection_sha256"]
    assert digest(study/"controls_TRAIN_selection.json")==deployment["controls_selection_sha256"]
    freeze=json.loads((out/"input_freeze.json").read_bytes())
    assert digest(out/"context_inventory.json")==freeze["context_inventory_sha256"]
    assert freeze["source_protocol_sha256"]==digest(study/"protocol.json")
    contexts=json.loads((out/"context_inventory.json").read_bytes())["contexts"]
    path=out/"results.jsonl"
    if path.exists():raise ValueError("No overwrite, rerun or performance resume")
    statuses=Counter();returned=0;started=time.perf_counter()
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=8) as pool:
            fs={pool.submit(run_context,c,protocol,deployment,str(out)):c for c in contexts}
            for f in as_completed(fs):
                c=fs[f];error=None
                try:assert f.result()==c["id"]
                except Exception as e:error={"type":type(e).__name__,"message":str(e)}
                journal=out/"context_results"/(sha256(c["id"].encode()).hexdigest()[:16]+".jsonl")
                rows=[]
                if journal.exists():
                    for line in journal.read_text().splitlines():
                        try:rows.append(json.loads(line))
                        except json.JSONDecodeError:break
                observed={key(r) for r in rows};assert len(observed)==len(rows)
                expected=list(expected_rows(c,protocol,deployment))
                for r in expected:
                    if key(r) not in observed:
                        r.update(result=None,runner_error=error or {"type":"MissingWorkerReceipt","message":"Assigned row missing, retained without retry"},
                                 assignment_returned=True,value_exact_original_objective=None);rows.append(r)
                assert len(rows)==126 and {key(r) for r in rows}=={key(r) for r in expected}
                for r in rows:
                    stream.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+"\n");returned+=1
                    statuses[(r["track"]+":"+(r["result"]["status"] if r.get("result") else r["runner_error"]["type"]))]+=1
                stream.flush();write(out/"progress.json",{"assigned":len(contexts)*126,"returned":returned,
                    "status_counts":dict(statuses),"wall_seconds":time.perf_counter()-started})
    assert returned==len(contexts)*126
    write(out/"completion.json",{"assigned":returned,"returned":returned,"contexts":len(contexts),
        "status_counts":dict(statuses),"wall_seconds":time.perf_counter()-started,"results_sha256":digest(path),
        "deployment_sha256":digest(study/"deployment.json"),"protocol_sha256":digest(study/"protocol.json"),
        "online_model_calls":0,"conditional_oracle_calls":0,"all_rows_retained":True})


def server_run(study,out,authorization):
    if platform.system()!="Linux":raise ValueError("TEST performance is server-only")
    study,out=Path(study),Path(out);protocol,capsule=verify_study(study)
    release=json.loads(Path(authorization).read_bytes());deployment=json.loads((study/"deployment.json").read_bytes())
    assert release["approved_TEST_launch"] is True
    assert release["source_zip_sha256"]==capsule["source_zip_sha256"]
    assert release["protocol_sha256"]==digest(study/"protocol.json")
    assert release["deployment_sha256"]==digest(study/"deployment.json")
    assert release["selection_sha256"]==deployment["selection_sha256"]
    assert release["controls_selection_sha256"]==deployment["controls_selection_sha256"]
    freeze=json.loads((out/"input_freeze.json").read_bytes())
    assert release["input_freeze_sha256"]==digest(out/"input_freeze.json")
    assert digest(out/"context_inventory.json")==freeze["context_inventory_sha256"]
    for name,expected in freeze["graph_files_sha256"].items():assert digest(out/name)==expected
    for e in protocol["executables"].values():assert digest(e["path"])==e["sha256"]
    if (out/"host_receipt.json").exists():raise ValueError("Preserve original TEST launch")
    (out/"root_release.json").write_bytes(Path(authorization).read_bytes())
    write(out/"host_receipt.json",{"before_any_TEST_solver_outcomes":True,"timestamp_unix":time.time(),
        "python":sys.version,"platform":platform.platform(),"workers":8,
        "cgroup_cpu_max":Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "cgroup_memory_max":Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        "root_release_sha256":digest(out/"root_release.json"),"source_zip_sha256":capsule["source_zip_sha256"]})
    started=time.perf_counter();guard=False
    with (out/"worker.log").open("xb") as log:
        child=subprocess.Popen([sys.executable,"scripts/run_performance_test_v06.py","worker-run","--study",str(study),"--out",str(out)],
            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env={**os.environ,"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1"})
        write(out/"launch_receipt.json",{"child_pid":child.pid,"timestamp_unix":time.time(),"assigned":freeze["assignments"],
            "whole_batch_wall_guard_seconds":14400,"root_release_sha256":digest(out/"root_release.json")})
        try:code=child.wait(timeout=14400)
        except subprocess.TimeoutExpired:
            guard=True;os.killpg(child.pid,signal.SIGTERM)
            try:code=child.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
    for name in ("protocol.json","freeze_receipt.json","capsule_receipt.json","deployment.json","TRAIN_selection.json","controls_TRAIN_selection.json"):
        (out/name).write_bytes((study/name).read_bytes())
    # Preserve the complete predeclared matrix even after a whole-batch guard.
    # Never fabricate timings or a feasible objective for unreturned requests.
    if guard or code!=0:
        contexts=json.loads((out/"context_inventory.json").read_bytes())["contexts"]
        observed=set()
        for journal in (out/"context_results").glob("*.jsonl"):
            for line in journal.read_text().splitlines():
                try:observed.add(key(json.loads(line)))
                except json.JSONDecodeError:break
        with (out/"unreturned_assignments.jsonl").open("x",encoding="utf-8",newline="\n") as stream:
            for context in contexts:
                for row in expected_rows(context,protocol,deployment):
                    if key(row) not in observed:
                        row.update(result=None,value_exact_original_objective=None,assignment_returned=False,
                            runner_error={"type":"WholeBatchGuard" if guard else "BatchWorkerExit",
                                          "message":"Predeclared assignment had no complete journal receipt; not retried"})
                        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
    write(out/"server_execution_receipt.json",{"source_zip_sha256":capsule["source_zip_sha256"],
        "actual_batch_wall_seconds":time.perf_counter()-started,"exit_code":code,
        "whole_batch_guard_triggered":guard,"all_partial_journals_retained":True,"retries":0})
    archive=ROOT/"experiments/runs/v06"/(out.name+".tar.gz");archive.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,"x:gz") as t:t.add(out,arcname=out.name)
    print(json.dumps({"archive":str(archive),"archive_sha256":digest(archive),"exit_code":code,"guard":guard}),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("plan-only","bind-selections","prepare-inputs","server-run","worker-run"))
    p.add_argument("--study",required=True);p.add_argument("--out")
    p.add_argument("--include-c3",choices=("none","interval","legacy","both"),default="both")
    p.add_argument("--include-uai64",action="store_true")
    p.add_argument("--selection");p.add_argument("--selection-sha256");p.add_argument("--controls");p.add_argument("--controls-sha256")
    p.add_argument("--authorization")
    a=p.parse_args()
    if a.mode=="plan-only":r=plan_only(a.study,a.include_c3,a.include_uai64)
    elif a.mode=="bind-selections":r=bind_selections(a.study,a.selection,a.selection_sha256,a.controls,a.controls_sha256)
    elif a.mode=="prepare-inputs":r=prepare_inputs(a.study,a.out)
    elif a.mode=="server-run":r=server_run(a.study,a.out,a.authorization)
    else:r=worker_run(a.study,a.out)
    print(json.dumps(r,ensure_ascii=False,allow_nan=False),flush=True)
