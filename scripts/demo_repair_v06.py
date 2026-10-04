"""Run a genuinely frozen V06 priority within the shared feasible repair kernel.

This toy example requires no LLM, oracle, SSH or original satellite data.
Its output is a feasibility demonstration, not a research benchmark result.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cipheur.model import Graph
from cipheur.repair_v06 import RepairConfig,repair_schedule


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph",default="examples/deployment_graph.json")
    parser.add_argument("--bank",default="examples/frozen_joint_bank_v06.json")
    parser.add_argument("--program-id",default="joint|block_0_witness:2")
    parser.add_argument("--seconds",type=float,default=.5)
    parser.add_argument("--out",default="output/demo_v06/result.json")
    args=parser.parse_args()
    graph=Graph.from_dict(json.loads((ROOT/args.graph).read_bytes()))
    bank=json.loads((ROOT/args.bank).read_bytes())
    entries=[r for r in bank["programs"] if r["id"]==args.program_id]
    if len(entries)!=1 or entries[0]["role"]!="proposed_witness_joint":
        raise ValueError("Choose one of the four frozen genuine joint programs")
    entry=entries[0]
    program_sha=sha256(json.dumps(entry["program"],sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    if program_sha!=entry["program_sha256"]:
        raise ValueError("Frozen program bytes changed")
    result=repair_schedule(graph,entry["program"],priority="program",seconds=args.seconds,
        clock="wall",config=RepairConfig())
    if not result["completed"] or not result["feasible"] or not graph.feasible(result["selected"]):
        raise ValueError("Toy demonstration did not return a completed feasible incumbent")
    output={"example_only":True,"program_id":entry["id"],"program_sha256":program_sha,
        "TRAIN_selection_sha256":bank["TRAIN_selection_sha256"],"online_model_calls":0,
        "conditional_oracle_calls":0,"result":result}
    target=(ROOT/args.out).resolve()
    if target.exists():
        raise ValueError("Use a new output path; preserve prior demonstration")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes((json.dumps(output,indent=2,allow_nan=False)+"\n").encode())
    print(json.dumps({"program_id":entry["id"],"feasible":result["feasible"],
        "reward_exact":result["value_exact"],"selected":result["selected"],"output":str(target)}))
