"""Deterministic union of saved strict requirements; no new scientific run.

Uses the frozen original complete-quotient function, verifies common feature
semantics, and retains each original source/query/boundary/certificate link.
No graph, objective solver, policy execution, or model is called.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import time

SCRIPT=Path(__file__).resolve()
spec=importlib.util.spec_from_file_location("frozen_p0_evidence",SCRIPT.with_name("p0_evidence.py"))
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
NAMESPACE="fraction_seconds_binary_fsum_base9_v1"
STAGES=("p0","patch_interface_probe")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-root",type=Path)
    parser.add_argument("--cipheur-root",type=Path)
    parser.add_argument("--input-root",type=Path,default=core.ROOT/"analysis")
    parser.add_argument("--output-root",type=Path,default=core.ROOT/"analysis"/"joint_quotient")
    parser.add_argument("--allow-partial",action="store_true",help="Mark incomplete stage/source inventory explicitly; default requires all4sources in bothstages")
    args=parser.parse_args()
    inputs=args.input_root.resolve();output=args.output_root.resolve()
    requirements,inventory=[],[]
    for stage in STAGES:
        qpath=inputs/stage/"complete_demanded_quotient.json"
        recorded=json.loads(qpath.read_text(encoding="utf-8"))
        if recorded.get("numeric_namespace")!=NAMESPACE or tuple(recorded["full_feature_names"])!=tuple(core.FEATURES):
            raise ValueError("Incompatible feature semantics cannot be merged:"+stage)
        for source in core.SOURCES:
            path=inputs/stage/source/"strict_requirements.json"
            summary=inputs/stage/source/"summary.json"
            if not path.exists() or not summary.exists():
                if not args.allow_partial:raise ValueError("Incomplete formal inventory:"+str(path))
                inventory.append({"stage":stage,"source":source,"status":"missing"});continue
            stat=json.loads(summary.read_text(encoding="utf-8"))
            count=stat["queries"] if stage=="p0" else stat["executed_queries"]
            planned=50 if stage=="p0" else 30
            if count!=planned and not args.allow_partial:raise ValueError("Incomplete formal query count:"+str(summary))
            saved=json.loads(path.read_text(encoding="utf-8"))
            for row in saved:
                if len(row["preferred_phi"])!=9 or len(row["other_phi"])!=9:raise ValueError("Not fullbase9")
                if row["source"]!=source:raise ValueError("Source identity mismatch")
                if row["delta_interval"]["preference"] not in ("a","b"):raise ValueError("Nonstrict requirement in strict label file")
                row["evidence_stage"]=stage
                row["original_requirement_file"]=str(path.relative_to(inputs))
                row["original_requirement_file_sha256"]=core.digest(path)
                row["certificate_file"]=str(Path(stage)/row["certificate_file"])
                requirements.append(row)
            inventory.append({"stage":stage,"source":source,"queries":count,"planned":planned,
                "status":"completed" if count==planned else "partial","strict_requirements":len(saved),
                "file_sha256":core.digest(path)})
    quotient=core.quotient(requirements)
    core.dump(output/"complete_demanded_quotient_union.json",quotient)
    complete=all(row["status"]=="completed" for row in inventory)
    receipt={"inventory":inventory,"all_four_sources_both_stages_complete":complete,
        "strict_requirements":len(requirements),"quotient_classes":len(quotient["vertices"]),
        "self_loops":quotient["self_loop_count"],"cycle_observed":quotient["directed_cycle_observed"],
        "G2":quotient["conclusion"],"numeric_namespace":NAMESPACE,"features":list(core.FEATURES),
        "semantic_compatibility":"both stages use actual compiled fullbase9 and conditional forced-inclusion preference under recordedF/P/X; interface search roles do not change label meaning",
        "source_groups":["r000","r001"],"test_sources_read":0,
        "scientific_execution_calls":0,"solver_calls":0,"model_calls":0,
        "script_sha256":core.digest(SCRIPT),"frozen_quotient_source_sha256":core.digest(SCRIPT.with_name("p0_evidence.py")),
        "generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    core.dump(output/"union_receipt.json",receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ("inventory","features")},ensure_ascii=False),flush=True)


if __name__=="__main__":main()
