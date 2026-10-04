"""Matched V06 banks: immutable authoring, TRAIN assessment, frozen selection.

Certified full-residual inequalities are scored on their original snapshots.
Independent-set repair quality is a separate measurement under one shared
kernel. Nothing in this module queries a conditional-value oracle or an LLM.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import statistics
import time

from .compiled import CompiledEvaluator
from .graph_features import FeatureRuleProgram
from .model import Graph
from .programs import FEATURES
from .refinement import diagnose_occurrences
from .repair_v06 import RepairConfig, repair_schedule

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("witness", "relations", "objective")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+"\n").encode())


def validate_response(payload,block,arm,slots=8):
    schema=(isinstance(payload,dict) and set(payload)=={"version","block","arm","candidates"}
        and payload["version"]=="matched_cold_bank_v06" and type(payload["block"]) is int and payload["block"]==block
        and payload["arm"]==arm and isinstance(payload["candidates"],list))
    candidates=payload["candidates"] if schema else []
    bad=not schema or len(candidates)>slots
    seen=set();rows=[]
    for slot in range(slots):
        row={"id":f"block_{block}_{arm}:{slot}","block":block,"arm":arm,"slot":slot,"program":None}
        if bad:row["status"]="invalid_response_schema"
        elif slot>=len(candidates):row["status"]="missing_slot"
        else:
            try:
                p=FeatureRuleProgram.from_dict(candidates[slot]).to_dict()
                key=canonical({k:p[k] for k in ("features","rule")})
                if key in seen:row["status"]="duplicate_deployment_AST_within_batch"
                else:
                    seen.add(key);row.update(status="static_valid",program=p,
                        program_sha256=canonical(p),deployment_AST_sha256=key)
            except (TypeError,ValueError,KeyError,RecursionError) as error:
                row.update(status="invalid_candidate",error_type=type(error).__name__,error=str(error))
        rows.append(row)
    return rows


def load_bank(study):
    study=Path(study)
    protocol=json.loads((study/"protocol.json").read_text(encoding="utf-8"))
    freeze=json.loads((study/"freeze_receipt.json").read_text(encoding="utf-8"))
    completion=json.loads((study/"authoring_completion.json").read_text(encoding="utf-8"))
    amendment=json.loads((study/"transport_amendment.json").read_text(encoding="utf-8"))
    if (protocol["version"]!="matched_synthesis_v06_001" or protocol["arms"]!=list(ARMS)
        or freeze["protocol_sha256"]!=digest(study/"protocol.json") or not freeze["before_authoring"]
        or completion["version"]!="matched_cli_authoring_completion_v06"
        or not completion["all_authoring_completed_before_assessment"]
        or not completion["same_requested_model_and_settings_all_cells"]
        or completion["transport_amendment_sha256"]!=digest(study/"transport_amendment.json")
        or amendment["original_protocol_sha256"]!=digest(study/"protocol.json")
        or not amendment["decided_before_any_v06_candidate_assessment"]):
        raise ValueError("Incomplete or changed registered authoring freeze")
    for name,expected in protocol["packet_sha256"].items():
        if digest(study/name)!=expected:raise ValueError("Packet changed: "+name)
    expected_names={f"block_{b}_{a}.json" for b in range(protocol["blocks"]) for a in ARMS}
    if set(completion["response_sha256"])!=expected_names:
        raise ValueError("Every registered session must be frozen before assessment")
    if digest(study/"training_evidence.json")!=protocol["training_evidence_sha256"]:
        raise ValueError("Frozen TRAIN evidence changed")
    bank=[]
    for block in range(protocol["blocks"]):
        for arm in ARMS:
            name=f"block_{block}_{arm}.json";path=study/"responses"/name
            if digest(path)!=completion["response_sha256"][name]:raise ValueError("Raw response changed")
            try:payload=json.loads(path.read_text(encoding="utf-8"))
            except (ValueError,UnicodeError):payload=None
            bank.extend(validate_response(payload,block,arm,protocol["slots_per_block_arm"]))
    return protocol,bank


class InterfaceLimit(ValueError):pass


class InterfaceMeter(dict):
    def __init__(self,max_work=100000000,cpu_seconds=60):
        self.max_work=max_work;self.deadline=time.process_time()+cpu_seconds
        super().__init__(feature_work=0,feature_primitives={})
    def __setitem__(self,key,value):
        super().__setitem__(key,value)
        if key=="feature_work":
            self.check()
    def check(self):
        if self.get("feature_work",0)>self.max_work:raise InterfaceLimit("offline_interface_work_cap")
        if time.process_time()>=self.deadline:raise InterfaceLimit("offline_interface_cpu_cap")


def interface_assessment(raw,records,label_rows,limits=None):
    """Full exact quotient on retained strict endpoints, plus actual rule fit."""
    start=time.process_time();meter=InterfaceMeter(**(limits or {}))
    program=FeatureRuleProgram.from_dict(raw);meter.check()
    demanded=set(program.code.co_names)&{f["name"] for f in program.features}
    labels={r["id"]:r for r in label_rows}
    occurrences,declared_occurrences,requirements={}, {}, []
    checks=[]
    for record in sorted(records,key=lambda r:r["id"]):
        meter.check()
        if record["split"]!="train":raise ValueError("TRAIN interface input includes TEST")
        graph=Graph.from_dict(record["graph"])
        if graph.digest()!=record["graph_digest"]:raise ValueError("Graph binding changed")
        active=graph.available(record["fixed"],record["excluded"])
        strict=[q for q in labels[record["id"]]["rows"] if q["difference"]["status"]=="strict"]
        evaluator=CompiledEvaluator(graph,program,active,meter,score_slice=False)
        cache={}
        for node in sorted({q[k] for q in strict for k in ("a","b")}):
            values=evaluator.feature_values(node)
            cache[node]=(values,program._rank(values,meter))
            oid=record["id"]+"|"+node
            occurrences[oid]={k:v for k,v in values.items() if k in FEATURES or k in demanded}
            declared_occurrences[oid]=values
        for index,q in enumerate(strict):
            p=q["difference"]["preferred"];n=q["b"] if p==q["a"] else q["a"]
            requirements.append({"preferred":record["id"]+"|"+p,"other":record["id"]+"|"+n,
                                 "state":record["id"],"query_index":index})
            ps,ns=cache[p][1],cache[n][1]
            checks.append({"state":record["id"],"a":q["a"],"b":q["b"],"preferred":p,
                           "score_preferred":ps,"score_other":ns,"passed":ps>ns+1e-8,
                           "score_tie":ps==ns,"query_kind":q["kind"],
                           "actual_base_alias":q["base_alias_by_side"][0 if not record["paired"] or record["side"]=="left" else 1]})
            meter.check()
    diagnosis=diagnose_occurrences(occurrences,requirements)
    meter.check()
    declared_diagnosis=diagnose_occurrences(declared_occurrences,requirements)
    meter.check()
    return {"demanded_features":sorted(demanded),"strict_total":len(checks),
        "strict_passed":sum(q["passed"] for q in checks),
        "alias_strict_total":sum(q["actual_base_alias"] for q in checks),
        "alias_strict_passed":sum(q["passed"] and q["actual_base_alias"] for q in checks),
        "quotient":diagnosis,"declared_quotient":declared_diagnosis,
        "strict_checks":checks,"interface_feature_work":meter["feature_work"],
        "interface_cpu_seconds":time.process_time()-start,
        "full_observed_consistency":not diagnosis["contradictory"] and all(q["passed"] for q in checks)}


def macro_quality(rows,records):
    by_family=defaultdict(list);by_work=defaultdict(list)
    rmap={r["id"]:r for r in records}
    for row in rows:
        record=rmap[row["id"]];result=row["result"]
        total=sum((Fraction(c["weight"]) for c in record["graph"]["contacts"]),Fraction())
        ratio=Fraction(result["value_exact"])/total if total else Fraction(1)
        by_family[record["family"]].append(ratio)
        by_work[record["family"]].append(result["meter"]["feature_work"]+result["meter"]["repair_work"])
    family_quality={f:sum(values,Fraction())/len(values) for f,values in by_family.items()}
    family_work={f:Fraction(sum(values),len(values)) for f,values in by_work.items()}
    return {"macro_quality_exact":str(sum(family_quality.values(),Fraction())/len(family_quality)),
            "macro_work_exact":str(sum(family_work.values(),Fraction())/len(family_work)),
            "family_reward_over_total_weight":{f:str(v) for f,v in family_quality.items()},
            "family_work":{f:str(v) for f,v in family_work.items()}}


def assess_candidate(task):
    entry,evidence,protocol=task
    if entry["status"]!="static_valid":return {**entry,"eligible":False,"kernel_rows":[],"assessment_status":entry["status"]}
    records=evidence["records"]
    start=time.process_time()
    result={**entry,"eligible":False,"kernel_rows":[]}
    try:
        result["interface"]=interface_assessment(entry["program"],records,evidence["labels"],protocol["interface_limits"])
        cfg=protocol["kernel_config"]
        for record in sorted(records,key=lambda r:r["id"]):
            row=repair_schedule(Graph.from_dict(record["graph"]),entry["program"],
                fixed=record["fixed"],excluded=record["excluded"],priority="program",
                seconds=cfg["seconds"],clock=cfg["clock"],config=RepairConfig(**cfg["repair_config"]))
            result["kernel_rows"].append({"id":record["id"],"family":record["family"],"result":row})
        result["kernel_summary"]=macro_quality(result["kernel_rows"],records)
        valid=all(r["result"]["completed"] and r["result"]["feasible"] for r in result["kernel_rows"])
        result["eligible"]=valid and not result["interface"]["quotient"]["contradictory"]
        result["assessment_status"]="assessed" if valid else "kernel_execution_error"
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError) as error:
        result.update(assessment_status="interface_or_execution_error",error_type=type(error).__name__,error=str(error))
    result["assessment_cpu_seconds"]=time.process_time()-start
    return result


def selection_key(row):
    if not row["eligible"]:raise ValueError("An ineligible raw slot cannot win")
    return (-row["interface"]["strict_passed"],-Fraction(row["kernel_summary"]["macro_quality_exact"]),
            Fraction(row["kernel_summary"]["macro_work_exact"]),row["slot"])


def select_cells(rows,blocks=4):
    winners=[];empty=[];prefix=[]
    for block in range(blocks):
        for arm in ARMS:
            cell=sorted((r for r in rows if r["block"]==block and r["arm"]==arm),key=lambda r:r["slot"])
            eligible=[r for r in cell if r["eligible"]]
            if eligible:winners.append(min(eligible,key=selection_key))
            else:empty.append({"block":block,"arm":arm})
            for count in range(1,len(cell)+1):
                available=[r for r in cell[:count] if r["eligible"]]
                win=min(available,key=selection_key) if available else None
                prefix.append({"block":block,"arm":arm,"raw_slots":count,
                    "winner_id":win["id"] if win else None,
                    "strict_passed":win["interface"]["strict_passed"] if win else None,
                    "first_eligible_original_slot":min(r["slot"] for r in available) if available else None})
    return winners,empty,prefix


def train(study,out,workers=8):
    study,out=Path(study),Path(out)
    if out.exists():raise ValueError("Never overwrite TRAIN candidate observations")
    protocol,bank=load_bank(study)
    for key,name in (("kernel","repair_v06.py"),("typed_library","graph_features.py"),("compiled_runtime","compiled.py")):
        if protocol["source_sha256"][key]!=digest(Path(__file__).parent/name):
            raise ValueError("Registered shared source changed: "+name)
    evidence=json.loads((study/"training_evidence.json").read_text(encoding="utf-8"))
    if len(bank)!=96 or len(evidence["records"])!=120:raise ValueError("Changed registered TRAIN frame")
    if any(r["split"]!="train" for r in evidence["records"]):raise ValueError("Forbidden TEST input")
    out.mkdir(parents=True)
    for name in ("protocol.json","freeze_receipt.json","authoring_completion.json","training_evidence.json","transport_amendment.json"):
        (out/name).write_bytes((study/name).read_bytes())
    write(out/"bank.json",bank)
    source={name:digest(Path(__file__).parent/name) for name in ("synthesis_study_v06.py","repair_v06.py","compiled.py","graph_features.py","model.py","programs.py","refinement.py","representation.py")}
    write(out/"execution.json",{"workers":workers,"source_sha256":source,"bank_sha256":digest(out/"bank.json"),
        "all_authoring_completed_before_assessment":True,"selection_split":"train","test_accessed":False})
    rows=[]
    with (out/"candidate_results.jsonl").open("w",encoding="utf-8",newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            fs={pool.submit(assess_candidate,(entry,evidence,protocol)):entry for entry in bank}
            for future in as_completed(fs):
                try:row=future.result()
                except Exception as error:
                    row={**fs[future],"eligible":False,"kernel_rows":[],
                         "assessment_status":"assessment_worker_error","error_type":type(error).__name__,"error":str(error)}
                rows.append(row)
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n");stream.flush()
                print(json.dumps({"assessed":row["id"],"status":row["assessment_status"],"eligible":row["eligible"],
                                  "strict_fit":row.get("interface",{}).get("strict_passed")}),flush=True)
    winners,empty,prefix=select_cells(rows)
    write(out/"selection.json",{"version":"v06_TRAIN_selected_programs_001","selection_split":"train","test_accessed":False,
        "all_96_original_slots_assessed":len(rows)==96,"empty_cells":empty,
        "all_cells_have_genuine_winner":len(winners)==12 and not empty,
        "programs":[{k:r[k] for k in ("id","block","arm","slot","program","program_sha256")} for r in winners],
        "selector_receipt":[{"id":r["id"],"strict_passed":r["interface"]["strict_passed"],
            "macro_quality_exact":r["kernel_summary"]["macro_quality_exact"],"macro_work_exact":r["kernel_summary"]["macro_work_exact"]} for r in winners],
        "prefix":prefix,"protocol_sha256":digest(study/"protocol.json"),"execution_sha256":digest(out/"execution.json"),
        "candidate_results_sha256":digest(out/"candidate_results.jsonl")})
    write(out/"complete.json",{"complete":True,"candidate_count":len(rows),"eligible":sum(r["eligible"] for r in rows),
        "status":dict(Counter(r["assessment_status"] for r in rows)),"empty_cells":empty,
        "selection_sha256":digest(out/"selection.json"),"test_queries":0})
    print(json.dumps({"complete":str(out),"eligible":sum(r["eligible"] for r in rows),"winners":len(winners),"empty_cells":empty}),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--study",required=True);p.add_argument("--out",required=True)
    p.add_argument("--workers",type=int,default=8);args=p.parse_args();train(args.study,args.out,args.workers)
