"""Assemble all registered TRAIN candidates and one predetermined old control."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--llm-bank",type=Path,required=True)
    p.add_argument("--grammar-bank",type=Path,required=True)
    p.add_argument("--old-bank",type=Path,required=True)
    p.add_argument("--old-id",default="joint|block_0_witness:2")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists(): raise ValueError("Do not overwrite a combined candidate bank")
    read=lambda path:json.loads(path.read_text(encoding="utf-8"))
    llm,grammar,old=read(args.llm_bank),read(args.grammar_bank),read(args.old_bank)
    if any(str(v.get("selection_split","")).lower()!="train" or v.get("TEST_used_for_selection") is True for v in (llm,grammar,old)):
        raise ValueError("All source banks must be TRAIN-only")
    if len(llm["programs"])!=48 or len(grammar["programs"])!=32:
        raise ValueError("First-round preregistration is exactly 48 LLM and 32 grammar candidates")
    matches=[v for v in old["programs"] if v["id"]==args.old_id]
    if len(matches)!=1:raise ValueError("Old programme control must resolve uniquely")
    frozen=copy.deepcopy(matches[0]);frozen["old_original_arm"]=frozen.get("arm");frozen["arm"]="old_frozen"
    programmes=llm["programs"]+grammar["programs"]+[frozen]
    if len({v["id"] for v in programmes})!=81:raise ValueError("Duplicate ID across the registered banks")
    result={"version":"stk_full_llm_v1_first_round_combined81", "selection_split":"TRAIN", "TEST_used_for_selection":False,
            "candidate_count":81,"composition":{"real_LLM":48,"nonLLM_grammar":32,"old_frozen":1},
            "selection":"all registered first-round candidates; no ranking, quality inspection or filtering by this assembler",
            "old_control_selection":"fixed preregistered first old-bank ID; exact original programme unchanged",
            "source_banks_sha256":{k:hashlib.sha256(path.read_bytes()).hexdigest() for k,path in
                                   (("llm",args.llm_bank),("grammar",args.grammar_bank),("old",args.old_bank))},
            "programs":programmes}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(args.output),"sha256":hashlib.sha256(args.output.read_bytes()).hexdigest(),"candidate_count":81}))

if __name__=="__main__":main()
