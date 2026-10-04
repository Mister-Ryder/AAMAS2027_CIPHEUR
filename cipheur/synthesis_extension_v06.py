"""Assess every raw slot, retaining a pre-assessment transport supplement.

Uses the unchanged registered V06 scorer and selector. The first four whole
transport-complete blocks define a conditional matched-authoring estimand;
the original provider failure remains in unconditional intention-to-author
counts. No candidate outcome decides inclusion of an authoring block.
"""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from .synthesis_study_v06 import (ARMS, ROOT, assess_candidate, canonical,
    digest, load_bank, select_cells, selection_key, validate_response, write)


def load_extended_bank(parent,supplement):
    parent,supplement=Path(parent),Path(supplement)
    protocol,bank=load_bank(parent)
    extra=json.loads((supplement/"protocol.json").read_text(encoding="utf-8"))
    freeze=json.loads((supplement/"freeze_receipt.json").read_text(encoding="utf-8"))
    completion=json.loads((supplement/"authoring_completion.json").read_text(encoding="utf-8"))
    if (extra["parent_protocol_sha256"]!=digest(parent/"protocol.json")
        or freeze["protocol_sha256"]!=digest(supplement/"protocol.json")
        or completion["supplement_protocol_sha256"]!=digest(supplement/"protocol.json")
        or completion["parent_completion_sha256"]!=digest(parent/"authoring_completion.json")
        or not completion["all_authoring_completed_before_assessment"]
        or not completion["same_requested_model_and_settings_all_cells"]
        or not extra["decided_before_any_candidate_assessment"]
        or extra["supplement_blocks"]!=[4] or extra["total_original_slots"]!=120):
        raise ValueError("Changed or incomplete fixed supplemental transport registration")
    for name,expected in extra["packet_sha256"].items():
        if digest(supplement/name)!=expected:raise ValueError("Supplemental packet changed")
    expected={f"block_4_{arm}.json" for arm in ARMS}
    if set(completion["response_sha256"])!=expected:raise ValueError("Supplemental completion incomplete")
    for arm in ARMS:
        name=f"block_4_{arm}.json";path=supplement/"responses"/name
        if digest(path)!=completion["response_sha256"][name]:raise ValueError("Raw supplemental output changed")
        try:payload=json.loads(path.read_text(encoding="utf-8"))
        except (ValueError,UnicodeError):payload=None
        bank.extend(validate_response(payload,4,arm,8))
    transport=[]
    for block in range(5):
        study=parent if block<4 else supplement
        for arm in ARMS:
            stem=f"block_{block}_{arm}"
            receipt=json.loads((study/"receipts"/(stem+".receipt.json")).read_text(encoding="utf-8"))
            response=study/"responses"/(stem+".json")
            if digest(response)!=receipt["response_sha256"]:raise ValueError("Receipt response binding changed")
            if receipt["requested_configuration"]!=extra["parent_requested_configuration"]:
                raise ValueError("Requested authoring configuration changed across cells")
            whole=(receipt["exit_code"]==0 and not receipt["timed_out"] and response.stat().st_size>0)
            transport.append({"block":block,"arm":arm,"complete_transport":whole,
                              "receipt_sha256":digest(study/"receipts"/(stem+".receipt.json"))})
    matched=[b for b in range(5) if all(r["complete_transport"] for r in transport if r["block"]==b)][:4]
    return protocol,bank,transport,matched


def train(parent,supplement,out,workers=8):
    parent,supplement,out=Path(parent),Path(supplement),Path(out)
    if out.exists():raise ValueError("Preserve every original assessment observation")
    protocol,bank,transport,matched=load_extended_bank(parent,supplement)
    if len(bank)!=120:raise ValueError("All120 raw positions must be kept")
    for key,name in (("kernel","repair_v06.py"),("typed_library","graph_features.py"),("compiled_runtime","compiled.py")):
        if digest(Path(__file__).parent/name)!=protocol["source_sha256"][key]:raise ValueError("Frozen shared runtime changed")
    if digest(Path(__file__).parent/"synthesis_study_v06.py")!=protocol["source_sha256"]["assessment"]:
        raise ValueError("Original V06 assessment semantics changed")
    evidence=json.loads((parent/"training_evidence.json").read_text(encoding="utf-8"))
    if len(evidence["records"])!=120 or any(r["split"]!="train" for r in evidence["records"]):raise ValueError("Changed TRAIN frame")
    out.mkdir(parents=True)
    for prefix,study in (("parent",parent),("supplement",supplement)):
        for name in ("protocol.json","freeze_receipt.json","authoring_completion.json"):
            (out/(prefix+"_"+name)).write_bytes((study/name).read_bytes())
    write(out/"bank.json",bank)
    source={name:digest(Path(__file__).parent/name) for name in ("synthesis_extension_v06.py","synthesis_study_v06.py","repair_v06.py","compiled.py","graph_features.py","model.py","programs.py","refinement.py","representation.py")}
    write(out/"execution.json",{"workers":workers,"source_sha256":source,"bank_sha256":digest(out/"bank.json"),
        "all15_authoring_sessions_frozen_before_assessment":True,"selection_split":"train","test_accessed":False,
        "transport_cells":transport,"matched_transport_complete_blocks":matched,
        "matched_scope":"Conditional on whole matched-block transport success; not missing-at-random or unconditional system effectiveness"})
    rows=[]
    with (out/"candidate_results.jsonl").open("w",encoding="utf-8",newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            fs={pool.submit(assess_candidate,(entry,evidence,protocol)):entry for entry in bank}
            for future in as_completed(fs):
                try:row=future.result()
                except Exception as error:
                    row={**fs[future],"eligible":False,"kernel_rows":[],"assessment_status":"assessment_worker_error",
                         "error_type":type(error).__name__,"error":str(error)}
                rows.append(row);stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n");stream.flush()
                print(json.dumps({"assessed":row["id"],"status":row["assessment_status"],"eligible":row["eligible"],
                    "strict_fit":row.get("interface",{}).get("strict_passed")}),flush=True)
    all_winners,all_empty,prefix=select_cells(rows,5)
    winners=[r for r in all_winners if r["block"] in matched]
    empty=[r for r in all_empty if r["block"] in matched]
    all_genuine=len(matched)==4 and len(winners)==12 and not empty
    write(out/"selection.json",{"version":"v06_transport_supplement_TRAIN_selection_001",
        "selection_split":"train","test_accessed":False,"all120_original_slots_assessed":len(rows)==120,
        "matched_transport_complete_blocks":matched,"all_cells_have_genuine_winner":all_genuine,
        "empty_matched_cells":empty,"all_unconditional_empty_cells":all_empty,
        "programs":[{k:r[k] for k in ("id","block","arm","slot","program","program_sha256")} for r in winners],
        "nonmatched_winners_not_deployed":[r["id"] for r in all_winners if r["block"] not in matched],
        "selector_receipt":[{"id":r["id"],"strict_passed":r["interface"]["strict_passed"],
            "macro_quality_exact":r["kernel_summary"]["macro_quality_exact"],"macro_work_exact":r["kernel_summary"]["macro_work_exact"]} for r in winners],
        "all_raw_prefixes":prefix,"parent_protocol_sha256":digest(parent/"protocol.json"),
        "supplement_protocol_sha256":digest(supplement/"protocol.json"),"execution_sha256":digest(out/"execution.json"),
        "candidate_results_sha256":digest(out/"candidate_results.jsonl"),"no_fallback":True})
    write(out/"complete.json",{"complete":True,"candidate_count":len(rows),"eligible":sum(r["eligible"] for r in rows),
        "assessment_status":dict(Counter(r["assessment_status"] for r in rows)),
        "all_cells_have_genuine_winner":all_genuine,"matched_blocks":matched,
        "selection_sha256":digest(out/"selection.json"),"TEST_queries":0})
    print(json.dumps({"all120_assessed":True,"matched_blocks":matched,"genuine_winners":len(winners),"ready_for_TEST":all_genuine}),flush=True)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--parent",required=True);p.add_argument("--supplement",required=True)
    p.add_argument("--out",required=True);p.add_argument("--workers",type=int,default=8)
    args=p.parse_args();train(args.parent,args.supplement,args.out,args.workers)
