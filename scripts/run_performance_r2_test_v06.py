"""R2 two-initializer TEST orchestration; execution requires root release.

Plan and input preparation never call a solver or read candidate responses.
Binding distinguishes four genuine witness-joint winners from twelve requested
nonguarded quality-only comparator positions and two fixed-bank controls.
Missing quality positions remain null. R1's twelve-genuine barrier is preserved
in the original runner. Both tracks require independently audited TRAIN bindings.
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
      "cipheur/refinement_study_v06.py","configs/refinement_selection_v06_002.json",
      "configs/analysis_refinement_v06_002.json",
      "scripts/run_performance_r2_test_v06.py")
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
SELECTION_CONFIG="configs/refinement_selection_v06_002.json"
PRESERVED_R1_RUNNER="scripts/run_performance_test_v06.py"
PRESERVED_R1_SHA="af66f797aa00d18c3ba9d3ab88866acb988d5980127ed548bb15d7e07a2f31b3"


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
    assert digest(ROOT/PRESERVED_R1_RUNNER)==PRESERVED_R1_SHA
    assert digest(ROOT/"cipheur/repair_v06.py")=="c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3"
    public=prepared_input_bindings(include_uai64)
    if include_c3!="none":assert digest(ROOT/C3)==C3_SHA
    config={"version":"performance_r2_test_v06_002","before_any_TEST_solver_outcomes":True,
        "workers":8,"wall_targets":[0.1,1,5],"native_requests":[m for m in METHODS if m["method"]!="Degree"],
        "repair_config":REPAIR,"common_seed":1,"native_hard_wall_guard_seconds":30,
        "whole_batch_wall_guard_seconds":14400,"strong_initializer_fraction":0.5,
        "cold_track":"Common Degree initialization plus bounded repair with full nominal T",
        "warm_track":"Common CHILS(seed1,nominal T/2) feasible incumbent, Degree-feasible extension, then bounded repair with nominal T/2; unchanged kernel",
        "warm_failure":"Failed/unsupported native initializer makes all associated warm rows explicitly unavailable with null value; no hidden Degree or other fallback",
        "warm_monotonicity":"Every returned warm incumbent must be exact source-feasible and have reward >= the supplied CHILS initial incumbent; no separate cold Degree candidate or best-of-two seed",
        "warm_reuse":"One deterministic native initializer is executed per graph/target and shared across all19 policy rows. Each standalone warm-pipeline cost is charged the same measured initialization cost plus its own repair cost; actual shared execution wall/CPU is separate.",
        "policy_slots":19,"genuine_proposed_slots":4,"nonguarded_quality_comparator_slots":12,"quality_only_control_slots":2,
        "assignments_per_source_target":50,"core_contexts":244+(10 if include_uai64 else 0),
        "core_assignments":(244+(10 if include_uai64 else 0))*150,
        "include_additional_UAI_Grids_CHILS64":include_uai64,
        "optional_c3_track":include_c3,"optional_c3_contexts":0 if include_c3=="none" else 48 if include_c3=="both" else 24,
        "total_contexts":244+(10 if include_uai64 else 0)+(0 if include_c3=="none" else 48 if include_c3=="both" else 24),
        "total_assignments":(244+(10 if include_uai64 else 0)+(0 if include_c3=="none" else 48 if include_c3=="both" else 24))*150,
        "fresh_synthetic_archive":PERFORMANCE,"fresh_synthetic_archive_sha256":PERFORMANCE_SHA,
        "public_input_bindings":INPUTS,"public_TEST_sources":public,
        "optional_c3_archive":C3 if include_c3!="none" else None,
        "optional_c3_archive_sha256":C3_SHA if include_c3!="none" else None,
        "executables":json.loads((ROOT/"configs/advanced_public_v04_remote.json").read_bytes())["executables"],
        "selection_config_sha256":digest(ROOT/SELECTION_CONFIG),
        "selection_barrier":"Independently audited R2 ready_for_TEST; exactly4 eligible W joint winners in4preselected transport blocks plus exactly12 requested nonguarded quality-comparator W/R/O positions with missing retained; separate original block0 controls. No pooling, replacement or TEST selection.",
        "R1_preserved_runner_sha256":PRESERVED_R1_SHA,
        "R1_status":"Original twelve-genuine barrier is unchanged; this separate R2 deployment does not repair, substitute or relabel missing R1 cells.",
        "independent_TRAIN_audit_barrier":"Hash-bound zero-error audit with selection_sha256, ready_for_TEST=true and proposed_witness_joint_count=4, retained unchanged before identities bind",
        "root_release_barrier":"A root-owned authorization JSON must explicitly bind the frozen protocol, source capsule, program selection and control selection before server launch",
        "timing":"Nominal native internal wall targets and cooperative Python repair wall targets. Full native preparation/startup/checking, repair CPU/wall, shared graph loading and actual overshoot retained. Equal targets are not matched end-to-end hard deadlines or language-independent fairness.",
        "failure":"Every assigned method/seed/track retained; unsupported encoding and solver/runner failures null rather than manufactured zero reward. Returned anytime caps retain feasible incumbents. Programme-error retained incumbents are diagnostic, with completed=false.",
        "quality":"Exact original feasible objective per source. Input-derived reward/total-weight is a loose upper-bound fraction, never an optimality percentage. Separately report comparison with predeclared full-target CHILS seed1; zero or missing reference makes the ratio null, retaining request and failure coverage. No best-TEST denominator or baseline selection.",
        "analysis_groups":"Fresh synthetic resource/profile families, WDP five source families, UAI Segmentation and separate CHILS64 Grids, C3 interval and legacy tracks remain separate. C3 sources were previously exposed and are exploratory. Arms/blocks/duplicate AST identities remain nested within shared graph sources; proposed joint and nonguarded quality roles are never pooled. Report coverage before quality, no zero fill for unsupported inputs.",
        "unit_semantics":"WDP integral original objective with exact clique complement; UAI per-source exact integer LCM reversed for original rational reward; synthetic quarters; original C3 integer duration objective and separately labeled legacy versus interval models",
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
    assert protocol["version"]=="performance_r2_test_v06_002"
    assert protocol["policy_slots"]==19 and protocol["assignments_per_source_target"]==50
    assert protocol["selection_config_sha256"]==digest(ROOT/SELECTION_CONFIG)
    assert prepared_input_bindings(protocol["include_additional_UAI_Grids_CHILS64"])==protocol["public_TEST_sources"]
    if protocol["optional_c3_track"]!="none":assert digest(ROOT/C3)==protocol["optional_c3_archive_sha256"]
    return protocol,capsule


def deployment_from_selection(selected,control,audit,selection_sha,selection_config_sha):
    """Pure binding contract, callable with mocks without opening candidate files."""
    assert selected["version"]=="v06_R2_joint_and_quality_roles_TRAIN_selection_002"
    assert selected["selection_split"]=="train" and selected["test_accessed"] is False
    assert selected["all120_original_slots_assessed"] and selected["ready_for_TEST"] is True
    assert selected["proposed_witness_joint_count"]==4 and selected["quality_comparator_requested_count"]==12
    assert selected["selection_plan_sha256"]==selection_config_sha
    assert selected["no_fallback"] and selected["R1_barrier_remains_failed"]
    assert audit["errors"]==0 and audit["selection_sha256"]==selection_sha
    assert audit["ready_for_TEST"] is True and audit["proposed_witness_joint_count"]==4
    assert control["selection_split"]=="train" and control["test_accessed"] is False and control["all64_original_slots_assessed"]
    blocks=selected["matched_transport_complete_blocks"]
    assert len(blocks)==4 and len(set(blocks))==4 and blocks==sorted(blocks) and all(type(b) is int and 0<=b<5 for b in blocks)
    programs=[];joint_cells=set();quality_cells=set();missing=[]
    for r in selected["programs"]:
        assert type(r["block"]) is int and r["block"] in blocks and r["arm"] in ("witness","relations","objective")
        assert type(r["eligible"]) is bool
        if r["role"]=="proposed_witness_joint":
            assert r["arm"]=="witness" and r["joint_gate_required"] is True and r["eligible"] is True
            assert not r.get("missing_baseline",False) and r["program"] is not None
            assert r["id"].startswith("joint|") and r["source_candidate_id"] is not None
            assert (r["block"],r["arm"]) not in joint_cells;joint_cells.add((r["block"],r["arm"]))
            kind="genuine_R2_witness_joint";available=True
        else:
            assert r["role"]=="nonguarded_quality_comparator" and r["joint_gate_required"] is False
            assert r["id"].startswith("quality|")
            assert (r["block"],r["arm"]) not in quality_cells;quality_cells.add((r["block"],r["arm"]))
            kind="nonguarded_R2_quality_comparator";available=not r["missing_baseline"]
            if not available:
                assert r["program"] is r["program_sha256"] is r["slot"] is r["source_candidate_id"] is None
                assert r["eligible"] is False and r["id"]==f"quality|block_{r['block']}_{r['arm']}:missing"
                missing.append({"block":r["block"],"arm":r["arm"]})
        if available:
            assert type(r["slot"]) is int and 0<=r["slot"]<8 and isinstance(r["source_candidate_id"],str)
            assert r["id"]==("joint|" if kind=="genuine_R2_witness_joint" else "quality|")+r["source_candidate_id"]
            assert canonical(r["program"])==r["program_sha256"]
            assert FeatureRuleProgram.from_dict(r["program"]).to_dict()==r["program"]
        programs.append({**r,"method_id":r["id"],"kind":kind,"available":available,"joint_eligible":r["eligible"]})
    assert len(programs)==16 and joint_cells=={(b,"witness") for b in blocks}
    assert quality_cells=={(b,a) for b in blocks for a in ("witness","relations","objective")}
    assert sorted(missing,key=lambda r:(r["block"],r["arm"]))==sorted(selected["quality_comparator_missing_cells"],key=lambda r:(r["block"],r["arm"]))
    for bank in ("enumerated_structural","fixed_base9"):
        rows=[r for r in control["selections"] if r["block"]==0 and r["bank"]==bank and r["used_for_performance"]]
        assert len(rows)==1
        winner=rows[0]["quality_only_baseline"]
        if winner is None:
            programs.append({"method_id":"quality_only_"+bank,"kind":"quality_only_fixed_control",
                "role":"original_fixed_bank_quality_control","bank":bank,"available":False,"program":None,"program_sha256":None})
        else:
            assert canonical(winner["program"])==winner["program_sha256"]
            assert FeatureRuleProgram.from_dict(winner["program"]).to_dict()==winner["program"]
            programs.append({**winner,"method_id":"quality_only_"+bank,"kind":"quality_only_fixed_control",
                "role":"original_fixed_bank_quality_control","bank":bank,"available":True,"joint_eligible":winner["eligible"]})
    programs.append({"method_id":"Degree","kind":"shared_classical_priority","role":"shared_classical_priority","available":True,"program":None})
    assert len(programs)==19 and len({r["method_id"] for r in programs})==19
    return programs,blocks


def bind_selections(study,selection,selection_sha,controls,controls_sha,audit,audit_sha):
    study=Path(study);protocol,capsule=verify_study(study)
    if (study/"deployment.json").exists():raise ValueError("Do not replace frozen performance ASTs")
    assert digest(selection)==selection_sha and digest(controls)==controls_sha and digest(audit)==audit_sha
    selected=json.loads(Path(selection).read_bytes());control=json.loads(Path(controls).read_bytes())
    audit_payload=json.loads(Path(audit).read_bytes())
    programs,blocks=deployment_from_selection(selected,control,audit_payload,selection_sha,protocol["selection_config_sha256"])
    deployment={"selection_sha256":selection_sha,"controls_selection_sha256":controls_sha,
        "independent_TRAIN_audit_sha256":audit_sha,
        "protocol_sha256":digest(study/"protocol.json"),"source_zip_sha256":capsule["source_zip_sha256"],
        "programs":programs,"genuine_witness_joint_winners":4,"requested_nonguarded_quality_comparators":12,"matched_blocks":blocks,
        "roles_never_pooled":True,"R1_barrier_preserved":True,
        "no_TEST_tuning":True,"before_any_TEST_solver_outcomes":True}
    (study/"TRAIN_selection.json").write_bytes(Path(selection).read_bytes())
    (study/"controls_TRAIN_selection.json").write_bytes(Path(controls).read_bytes())
    (study/"independent_TRAIN_audit.json").write_bytes(Path(audit).read_bytes())
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
        source_total=sum((Fraction(v.weight) for v in graph.contacts),Fraction())/meta["source_weight_scale"]
        assert source_total>0
        contexts.append({**meta,"graph_sha256":identity,"graph_file":name,"graph_file_sha256":digest(out/name),
                         "total_source_weight_exact":str(source_total),
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
        "contexts":len(contexts),"assignments":len(contexts)*3*50,
        "graph_files_sha256":{c["graph_file"]:c["graph_file_sha256"] for c in contexts}})
    return len(contexts)


def row_template(c,target,track,method,seed=1):
    return {"id":c["id"],"population":c["population"],"split":c["split"],"n":c["n"],"m":c["m"],
        "pair_id":c.get("pair_id"),"side":c.get("side"),"graph_sha256":c["graph_sha256"],
        "source_weight_scale":c["source_weight_scale"],"nominal_wall_target_seconds":target,
        "total_source_weight_exact":c.get("total_source_weight_exact"),
        "track":track,"method":method,"seed":seed}


def key(row):return row["id"],row["nominal_wall_target_seconds"],row["track"],row["method"],row["seed"]


def expected_rows(c,protocol,deployment):
    for target in protocol["wall_targets"]:
        for m in protocol["native_requests"]:yield row_template(c,target,"native",m["method"],m["seed"])
        yield row_template(c,target,"common_initializer","CHILS_half",1)
        for track in ("cold_Degree","warm_CHILS"):
            for p in deployment["programs"]:yield policy_row(c,target,track,p)


def policy_row(c,target,track,p):
    return {**row_template(c,target,track,p["method_id"],1),"program_kind":p["kind"],
        "program_role":p["role"],"program_sha256":p.get("program_sha256"),"joint_eligible":p.get("joint_eligible"),
        "authoring_block":p.get("block"),"authoring_arm":p.get("arm"),"source_candidate_id":p.get("source_candidate_id")}


def run_context(c,protocol,deployment,out):
    out=Path(out);wall0,cpu0=time.perf_counter(),time.process_time()
    assert c["split"]=="test" or c["population"] in ("C3_interval_exploratory","C3_legacy_exploratory")
    assert len(deployment["programs"])==19
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
        total=c.get("total_source_weight_exact")
        row["input_total_weight_fraction_exact"]=(str(Fraction(original)/Fraction(total)) if success and total is not None else None)
        if row["input_total_weight_fraction_exact"] is not None:assert 0<=Fraction(row["input_total_weight_fraction_exact"])<=1
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
                    row=policy_row(c,target,track,p)
                    extra={"policy_nominal_seconds":target if track=="cold_Degree" else target*0.5}
                    if not p["available"]:
                        assert p["kind"] in ("nonguarded_R2_quality_comparator","quality_only_fixed_control")
                        emit(stream,row,None,{"type":"MissingFrozenQualityOnlyPosition","message":"No completed feasible TRAIN quality winner; predeclared role retained, no replacement"},extra);continue
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
                            standalone_pipeline_wall_seconds=initial["wrapper_wall_seconds"]+extra["policy_wrapper_wall_seconds"],
                            standalone_pipeline_cpu_seconds=initial.get("child_cpu_seconds",0)+initial["wrapper_self_cpu_seconds"]+extra["policy_wrapper_cpu_seconds"],
                            native_initialization_cost_shared_in_actual_execution=True,advanced_track_available=True)
                    emit(stream,row,result,error,extra)
    write(out/"context_execution"/(token+".json"),{"id":c["id"],"actual_shared_context_wall_seconds":time.perf_counter()-wall0,
        "actual_shared_context_self_cpu_seconds":time.process_time()-cpu0,"requests":150,
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
    assert digest(study/"independent_TRAIN_audit.json")==deployment["independent_TRAIN_audit_sha256"]==root_release["independent_TRAIN_audit_sha256"]
    assert root_release["source_zip_sha256"]==deployment["source_zip_sha256"] and root_release["protocol_sha256"]==deployment["protocol_sha256"]
    assert all(root_release["all_source_hashes"].get(n)==h for n,h in protocol["source_sha256"].items())
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
                                 assignment_returned=True,successful_assignment=False,value_exact_original_objective=None,
                                 quality_reward_exact_original_objective=None);rows.append(r)
                assert len(rows)==150 and {key(r) for r in rows}=={key(r) for r in expected}
                for r in rows:
                    stream.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+"\n");returned+=1
                    statuses[(r["track"]+":"+(r["result"]["status"] if r.get("result") else r["runner_error"]["type"]))]+=1
                stream.flush();write(out/"progress.json",{"assigned":len(contexts)*150,"returned":returned,
                    "status_counts":dict(statuses),"wall_seconds":time.perf_counter()-started})
    assert returned==len(contexts)*150
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
    assert all(release["all_source_hashes"].get(n)==h for n,h in protocol["source_sha256"].items())
    assert release["deployment_sha256"]==digest(study/"deployment.json")
    assert release["selection_sha256"]==deployment["selection_sha256"]
    assert release["controls_selection_sha256"]==deployment["controls_selection_sha256"]
    assert release["independent_TRAIN_audit_sha256"]==deployment["independent_TRAIN_audit_sha256"]==digest(study/"independent_TRAIN_audit.json")
    assert deployment["genuine_witness_joint_winners"]==4 and deployment["requested_nonguarded_quality_comparators"]==12
    assert deployment["roles_never_pooled"] and deployment["R1_barrier_preserved"]
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
        child=subprocess.Popen([sys.executable,"scripts/run_performance_r2_test_v06.py","worker-run","--study",str(study),"--out",str(out)],
            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env={**os.environ,"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1"})
        write(out/"launch_receipt.json",{"child_pid":child.pid,"timestamp_unix":time.time(),"assigned":freeze["assignments"],
            "whole_batch_wall_guard_seconds":14400,"root_release_sha256":digest(out/"root_release.json")})
        try:code=child.wait(timeout=14400)
        except subprocess.TimeoutExpired:
            guard=True;os.killpg(child.pid,signal.SIGTERM)
            try:code=child.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
    for name in ("protocol.json","freeze_receipt.json","capsule_receipt.json","deployment.json","TRAIN_selection.json","controls_TRAIN_selection.json","independent_TRAIN_audit.json"):
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
                            successful_assignment=False,quality_reward_exact_original_objective=None,
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
    p.add_argument("--selection-audit");p.add_argument("--selection-audit-sha256")
    p.add_argument("--authorization")
    a=p.parse_args()
    if a.mode=="plan-only":r=plan_only(a.study,a.include_c3,a.include_uai64)
    elif a.mode=="bind-selections":r=bind_selections(a.study,a.selection,a.selection_sha256,a.controls,a.controls_sha256,a.selection_audit,a.selection_audit_sha256)
    elif a.mode=="prepare-inputs":r=prepare_inputs(a.study,a.out)
    elif a.mode=="server-run":r=server_run(a.study,a.out,a.authorization)
    else:r=worker_run(a.study,a.out)
    print(json.dumps(r,ensure_ascii=False,allow_nan=False),flush=True)
