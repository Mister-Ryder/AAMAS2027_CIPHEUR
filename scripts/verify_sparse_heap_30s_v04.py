"""Independent 30-CPU-second SNAP heap extension audit; no study reruns."""
from collections import Counter,defaultdict
from hashlib import sha256
from fractions import Fraction
import io
import json
import math
from pathlib import Path
import zipfile

import verify_v03_evidence as audit
from verify_advanced_results_v04 import contexts
from verify_heap_results_v04 import trace

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"experiments/runs/v04/heap_sparse_v04_30s_001.tar.gz"
SOURCE=ROOT/"experiments/source_snapshots/v04/heap_v04_30s_001_source.zip"


def read(path):
    metadata,hashes={},{};snapshot=None;rows={};hasher=sha256()
    for member,handle,_ in audit.stream(path):
        if member in {"config.json","data.json","frozen_programs.json","executed_programs.json","execution.json","complete.json"}:
            b=handle.read();metadata[member]=json.loads(b);hashes[member]=sha256(b).hexdigest()
        elif member=="source_snapshot.zip":snapshot=handle.read()
        elif member=="results.jsonl":
            for line in handle:
                hasher.update(line);r=json.loads(line)
                audit.require(r["id"] not in rows,"sparse30_unique_context",str(path),r["id"]);rows[r["id"]]=r
    return metadata,hashes,snapshot,rows,hasher.hexdigest()


def main():
    m,h,snapshot,results,result_hash=read(ARCHIVE)
    old,oldh,old_snapshot,previous,_=read(ROOT/"experiments/runs/v04/heap_sparse_v04_001.tar.gz")
    config,exe,done=m["config.json"],m["execution.json"],m["complete.json"]
    expected=contexts(m["data.json"]);programmes=m["executed_programs.json"];freeze=m["frozen_programs.json"]
    audit.require(config["program_cpu_seconds"]==30 and config["repetitions"]==3 and config["selection_permitted"] is False and exe["selection_permitted"] is False and exe["original_confirmatory_runner_modified"] is False and done["selection_permitted"] is False,"sparse30_separate_fixed_budget_scope","config","budget/selection differs")
    scientific=lambda c:{k:v for k,v in c.items() if k not in ("version","scope","program_cpu_seconds")}
    audit.require(scientific(config)==scientific(old["config.json"]) and old["config.json"]["program_cpu_seconds"]==5,"sparse30_only_declared_budget_change","config","science/AST/input/order settings changed")
    for field,member in (("input_sha256","data.json"),("config_sha256","config.json"),("train_freeze_sha256","frozen_programs.json")):
        audit.require(h[member]==exe[field],"sparse30_execution_byte_identity",member,"hash differs")
    audit.require(h["data.json"]==oldh["data.json"]==config["input_sha256"]["public"] and h["frozen_programs.json"]==oldh["frozen_programs.json"]==config["train_freeze_sha256"]==audit.file_digest(ROOT/".research/train_v04_frozen.json"),"sparse30_original_input_freeze_unchanged","inputs","bytes differ")
    audit.require(programmes==old["executed_programs.json"]=={a:freeze["programs"][p] for a,p in config["program_arms"].items()} and freeze["test_accessed"] is False and freeze["selection_split"]=="train","sparse30_train_asts_unchanged","programmes","frozen selection differs")
    audit.require(audit.file_digest(SOURCE)=="d516c9819b847d6f7ae0e196234f436d8515e10f303cf634b3a0c07f9e413668" and sha256(snapshot).hexdigest()==exe["source_snapshot_sha256"],"sparse30_prefrozen_source_package_hash","source","source hash differs")
    runner_change={}
    with zipfile.ZipFile(SOURCE) as outer,zipfile.ZipFile(io.BytesIO(snapshot)) as runtime,zipfile.ZipFile(io.BytesIO(old_snapshot)) as old_runtime:
        audit.require(sha256(outer.read("configs/heap_extension_v04_30s.json")).hexdigest()==h["config.json"]==sha256(runtime.read("config.json")).hexdigest(),"sparse30_exact_prefrozen_config","config","source config differs")
        for name,digest in exe["source_sha256"].items():
            source_bytes=outer.read("cipheur/"+name)
            audit.require(digest==sha256(source_bytes).hexdigest()==sha256(runtime.read("cipheur/"+name)).hexdigest()==audit.file_digest(ROOT/"cipheur"/name),"sparse30_exact_frozen_executed_reviewed_source",name,"frozen/executed/current source differs")
            if name!="heap_study_v04.py":
                audit.require(digest==old["execution.json"]["source_sha256"][name],"sparse30_unchanged_reviewed_backend_source",name,"backend core differs")
            else:
                original=old_runtime.read("cipheur/"+name)
                before=b'    if (config.get("repetitions") != 3 or config.get("program_cpu_seconds") != 5\n'
                after=b'    protocol = (config.get("version"), config.get("program_cpu_seconds"))\n    if (protocol not in {("fixed_ast_heap_execution_extension_v04", 5),\n                         ("fixed_ast_heap_execution_extension_v04_30s", 30)}\n            or config.get("repetitions") != 3\n'
                audit.require(original.count(before)==1 and source_bytes==original.replace(before,after),"sparse30_only_runner_protocol_guard_extension",name,"runner changed beyond explicit version/CPU guard")
                runner_change={"old_sha256":sha256(original).hexdigest(),"new_sha256":digest,"only_change":"Config admission guard recognizes explicit (version,CPU target) pairs for5/30-second extensions; execution/scoring/timing/failure logic byte-identical."}
    counts=Counter();orders=Counter();cross=Counter();failure=Counter();maxcpu=defaultdict(float);cases={};assessable=0
    names=list(config["program_arms"]);index={k:i for i,k in enumerate(sorted(expected))}
    for cid,r in results.items():
        p=expected[cid];g=audit.view(p["graph"]);f,x=p["fixed"],p["excluded"];where=cid
        audit.require(all(r[k]==p[k] for k in ("pair_id","side","split","family","cluster","fixed","excluded")) and r["graph_sha256"]==g.digest and r["n"]==len(g.contacts) and r["m"]==len(g.edges) and r["selection_permitted"] is False,"sparse30_original_graph_boundary_identity",where,"input/graph/F/X differs")
        expected_order=[]
        for rep in range(3):
            for arm in names if (index[cid]+rep)%2==0 else list(reversed(names)):
                backends=["full_scan","heap"] if (index[cid]+rep+names.index(arm))%2==0 else ["heap","full_scan"]
                expected_order.extend((arm,rep,b,pos) for pos,b in enumerate(backends))
        audit.require(len(r["runs"])==12 and len(r["paired"])==6,"sparse30_complete_per_context_assignment",where,"missing rows")
        rows={};oldrows={(s["arm"],s["repetition"],s["backend"]):s for s in previous[cid]["runs"]};localcounts=Counter()
        for i,row in enumerate(r["runs"]):
            key=(row["arm"],row["repetition"],row["backend"]);arm,rep,backend=key;w=where+"/"+str(key)
            audit.require(key not in rows and (*key,row["pair_position"])==expected_order[i] and row["sequence"]==i,"sparse30_interleaved_order_balance",w,"order differs");rows[key]=row
            status="completed" if row["completed"] else "failed";counts[arm+"/"+backend+"/"+status]+=1;localcounts[arm+"/"+backend+"/"+status]+=1
            if row["pair_position"]==0:orders[arm+"/"+backend+"/first"]+=1
            audit.require(row["fallback_used"] is False and row["score_slice"] is True and row["declared_cpu_seconds"]==30 and row["program_sha256"]==config["program_sha256"][arm]==exe["program_sha256"][arm] and row["program_name"]==programmes[arm]["name"],"sparse30_same_ast_no_timeout_fallback",w,"AST/budget differs")
            audit.require(all(isinstance(row[k],(int,float)) and math.isfinite(row[k]) and row[k]>=0 for k in ("seconds","cpu_seconds")),"sparse30_all_assigned_cost_retained",w,"missing/nonfinite cost")
            maxcpu[arm+"/"+backend+"/"+status]=max(maxcpu[arm+"/"+backend+"/"+status],row["cpu_seconds"])
            if row["completed"]:
                audit.check_selection(g,row["selected"],row["value"],f,x,w)
                audit.require(row["feasible"] is True and g.value(row["selected"])==Fraction(row["value_exact"]),"sparse30_exact_original_reward",w,"witness differs");trace(g,row,f,x,w)
                previous_successes=[v for k,v in oldrows.items() if k[0]==arm and k[2]==backend and v["completed"]]
                for prior in previous_successes:audit.require(all(prior[k]==row[k] for k in ("trace","selected","value","value_exact")),"sparse30_all_cross_budget_success_trace_equivalence",w,"same AST differs from successful5-second row")
                cross[arm+"/"+backend+"/all_successful_cross_pairs"]+=len(previous_successes)
            else:
                audit.require(all(row.get(k) is None for k in ("selected","value","value_exact","trace","feasible","feature_work","score_evaluations")),"sparse30_failure_null_no_partial_quality",w,"partial result returned");failure[row["status"]]+=1
            if oldrows[key]["completed"] and row["completed"]:cross[arm+"/"+backend+"/same_repetition_both_complete"]+=1
        pairs=set()
        for p in r["paired"]:
            key=p["arm"],p["repetition"];audit.require(key not in pairs,"sparse30_unique_pair",where,"duplicate pair");pairs.add(key)
            full,heap=rows[(*key,"full_scan")],rows[(*key,"heap")];both=full["completed"] and heap["completed"];assessable+=both
            audit.require(p["both_completed"]==both and p["exact_trace_selection_value_parity"] is None and p["failed_backends"]==[b for b in ("full_scan","heap") if not rows[(*key,b)]["completed"]] and all(p[k] is None for k in ("full_over_heap_cpu","full_over_heap_work","score_evaluations_saved")),"sparse30_unassessable_pairs_no_parity_or_speedup",where,"unassessable ratio credited")
        cases[cid]={"family":r["family"],"source_cluster":r["cluster"],"n":r["n"],"m":r["m"],"counts":dict(localcounts)}
    audit.require(set(results)==set(expected) and done["complete"] is True and done["contexts"]==8 and done["runs"]==96==sum(counts.values()) and dict(counts)==done["method_counts"] and result_hash==done["results_sha256"] and done["parity_failures"]==assessable==0 and done["all_completed_pairs_match"] is True,"sparse30_complete_counts_hash_vacuous_parity","complete","population/accounting differs")
    audit.require(all(orders[a+"/heap/first"]==orders[a+"/full_scan/first"] for a in names),"sparse30_balanced_first_backend","order","imbalance")
    report={"archive_sha256":audit.file_digest(ARCHIVE),"frozen_source_zip_sha256":audit.file_digest(SOURCE),"member_sha256":h,"contexts":8,"runs":96,"method_counts":dict(counts),"assessable_fullscan_heap_pairs":assessable,"cross_budget_same_ast_success_checks":dict(cross),"max_observed_cpu_seconds":dict(maxcpu),"failure_statuses":dict(failure),"cases":cases,"checks":dict(audit.CHECKS),"issues":list(audit.ISSUES.values()),"scope":["Separate30-process-CPU-second post-diagnostic execution extension; same8 source/weight inputs and same TRAIN-frozen ASTs.","Comparison with5-second successes is repeated execution of the same inputs, not additional independent quality instances.","Fullscan completes0/24 per AST, so exact paired sparse parity and speedup remain unassessable; vacuous all_completed_pairs_match=true is not confirmation.","Workers differ:8 here versus2 in5-second sparse timing; no causal wall-cost comparison across budgets is inferred.","All costs and null failures retained; no partial/fallback schedules, original confirmatory quality credit, or program selection changes."]}
    report["runner_source_change"]=runner_change
    target=ROOT/"experiments/analysis/v04/sparse_heap_30s_audit.json";target.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"checks":sum(audit.CHECKS.values()),"issues":report["issues"],"counts":dict(counts),"assessable_pairs":assessable,"cross_budget_checks":dict(cross),"max_cpu":dict(maxcpu)}))
    return int(any(i["severity"]=="error" for i in report["issues"]))


if __name__=="__main__":raise SystemExit(main())
