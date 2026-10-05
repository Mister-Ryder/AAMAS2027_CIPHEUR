"""Portable one-run complete graph benchmark, with explicit split/provenance."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time

SCRIPT=Path(__file__).resolve()
early=argparse.ArgumentParser(add_help=False)
early.add_argument("--cipheur-root",type=Path,default=SCRIPT.parents[3])
known,_=early.parse_known_args();sys.path.insert(0,str(known.cipheur_root.resolve()))
from full_schedule_execution import load_graph,run_full_schedule,NAMESPACE
from cipheur.repair_v06 import _Meter
from cipheur.graph_features import FeatureRuleProgram,graph_operation_library

def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def main():
    parser=argparse.ArgumentParser(parents=[early],description=__doc__)
    parser.add_argument("--graph",type=Path)
    parser.add_argument("--metadata",type=Path)
    parser.add_argument("--graph-manifest",type=Path,help="graphs:[{source,config,split,npz_path,metadata_path}]")
    parser.add_argument("--source",required=True)
    parser.add_argument("--config",required=True)
    parser.add_argument("--split",choices=("train","val","test"),required=True)
    parser.add_argument("--method",choices=("degree","weight","grasp","local2swap","cp_sat","program","chils","chils_ils"),required=True)
    parser.add_argument("--native-executable",type=Path)
    parser.add_argument("--native-output-root",type=Path)
    parser.add_argument("--program-bank",type=Path)
    parser.add_argument("--program-id")
    parser.add_argument("--protocol",type=Path,help="Required frozen protocol for TEST; time fractions and caps are read here")
    parser.add_argument("--seconds",type=float,required=True)
    parser.add_argument("--seed",type=int,default=2)
    parser.add_argument("--patch-cap",type=int,default=128)
    parser.add_argument("--swap-rounds",type=int,default=2)
    parser.add_argument("--max-repairs",type=int,default=10000,help="Engineeringfixture may cap iterations; formal uses protocol fixed value")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.seconds<=0 or args.patch_cap<32 or args.swap_rounds<0 or args.max_repairs<0:raise ValueError("Invalid execution budgets")
    protocol=read(args.protocol) if args.protocol else {}
    if args.split=="test":
        if not args.protocol or protocol.get("frozen") is not True:raise ValueError("TEST requires a frozen protocol")
        if args.source not in protocol["test_sources"]:raise ValueError("TEST source not frozen")
    if protocol:
        budgets=protocol.get("budgets_seconds",protocol.get("execution_cpu_seconds",[]))
        seeds=protocol.get("seeds",protocol.get("formal_seeds",[]))
        if args.seconds not in budgets or args.seed not in seeds:raise ValueError("Budget/seed not preregistered")
        args.patch_cap=protocol.get("patch_cap",protocol.get("repair_activity_cap",args.patch_cap))
        args.swap_rounds=protocol.get("swap_rounds",args.swap_rounds)
        args.max_repairs=protocol.get("max_repairs",args.max_repairs)
    meter=_Meter(args.seconds,"cpu",None,0)
    graph_path,meta_path=args.graph,args.metadata
    if args.graph_manifest:
        entries=read(args.graph_manifest)["graphs"]
        matches=[v for v in entries if (v["source"],v["config"],v["split"])==(args.source,args.config,args.split)]
        if len(matches)!=1:raise ValueError("Graph manifest source/config/split is not unique")
        item=matches[0];base=args.graph_manifest.parent
        graph_path=(base/item["npz_path"]).resolve();meta_path=(base/item["metadata_path"]).resolve()
    if not graph_path or not meta_path:raise ValueError("Provide graph+metadata, or one exact graph manifest entry")
    bank_item=None;program=None
    if args.method=="program":
        if not args.program_bank or not args.program_id:raise ValueError("Program requires bank and exact id")
        bank=read(args.program_bank);matches=[p for p in bank["programs"] if p["id"]==args.program_id]
        if len(matches)!=1:raise ValueError("Programme id must resolve exactly once")
        bank_item=matches[0];program=FeatureRuleProgram.from_dict(bank_item["program"])
        if "rule_only" in bank_item.get("arm","") and program.features:raise ValueError("Rule-only arm cannot add features")
        if args.split=="test":
            if digest(args.program_bank)!=protocol["frozen_program_bank_sha256"]:raise ValueError("TEST programme bank changed after freeze")
            if args.program_id not in protocol["final_program_ids"]:raise ValueError("Unselected programme cannot access TEST")
    graph,loading=load_graph(graph_path,meta_path,meter)
    meta=graph.provenance["metadata"]
    if meta.get("source_id")!=args.source or args.config not in (meta.get("config_id",graph_path.stem),meta.get("factorial_id")):
        raise ValueError("Graph metadata identity mismatch")
    normalized_split={"validation":"val","val":"val","train":"train","test":"test"}.get(meta.get("split"))
    if normalized_split!=args.split:raise ValueError("Requested split differs from data metadata")
    native_runner=None
    if args.method in ("chils","chils_ils"):
        if not args.native_executable:raise ValueError("Published native baseline requires explicit executable")
        from published_weighted_baselines import run_chils
        def native_runner(current,initial,remaining,random_seed):
            return run_chils(current,initial,remaining,random_seed,args.native_executable,
                population=4 if args.method=="chils" else 1,
                output_root=args.native_output_root or args.output.parent/(args.output.stem+"_native"))
    result=run_full_schedule(graph,args.method,args.seconds,args.seed,program,meter,
        patch_cap=args.patch_cap,swap_rounds=args.swap_rounds,max_repairs=args.max_repairs,
        destroy_cycle=tuple(protocol.get("destroy_cycle",protocol.get("destroy_counts",[16,32]))),
        construction_fraction=protocol.get("construction_fraction",.2),swap_fraction=protocol.get("swap_fraction",.1),native_runner=native_runner)
    result.update(source=args.source,config=args.config,split=args.split,loading=loading,
        graph_config_id=meta.get("config_id",graph_path.stem),
        program_id=args.program_id,program_arm=bank_item.get("arm") if bank_item else None,
        program=bank_item["program"] if bank_item else None,offline_program_provenance=bank_item.get("provenance") if bank_item else None,
        input_graph_sha256=digest(graph_path),metadata_sha256=digest(meta_path),
        program_bank_sha256=digest(args.program_bank) if args.program_bank else None,
        protocol_sha256=digest(args.protocol) if args.protocol else None,
        graph_manifest_sha256=digest(args.graph_manifest) if args.graph_manifest else None,
        script_sha256=digest(SCRIPT),execution_module_sha256=digest(SCRIPT.with_name("full_schedule_execution.py")),
        numeric_namespace=NAMESPACE,hostname=socket.gethostname(),platform=platform.platform(),python=sys.version,
        pid=os.getpid(),cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,
        dependency_scope="numpy,existingcipheur; CP-SAT requires ortools singleworker",
        method_label_note="degree/weight/GRASP are heads in identical shared anytime backbone; local2swap andCP-SAT are standalone fullgraph comparators",
        start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(time.time()-result["wall_seconds"])))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    before_cpu=time.process_time();before_wall=time.perf_counter()
    json.dumps(result,ensure_ascii=False)
    result["serialization_measurement"]={"cpu_seconds":time.process_time()-before_cpu,"wall_seconds":time.perf_counter()-before_wall,
        "scope":"one complete JSON encoding pass; finalartifact write overhead is reported separately from optimization budget"}
    result["cpu_seconds_including_record_encoding"]=time.process_time()-meter.cpu_start+float(result["native_child_cpu_seconds"] or 0.)
    result["wall_seconds_including_record_encoding"]=time.perf_counter()-meter.wall_start
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("source","config","split","method","program_id","value_exact","feasible","cpu_seconds","wall_seconds","head_ever_committed")},ensure_ascii=False))

if __name__=="__main__":main()
