"""Independent archive audit of the unchanged-AST heap timing extension."""
from collections import Counter, defaultdict
from hashlib import sha256
from fractions import Fraction
import io
import json
from pathlib import Path
import statistics
import zipfile

import verify_v03_evidence as audit
from verify_advanced_results_v04 import contexts,bootstrap

ROOT=Path(__file__).resolve().parents[1]


def confirmation():
    result={}
    path=ROOT/"experiments/runs/v04/advanced_fresh_v04_001.tar.gz"
    for member,handle,_ in audit.stream(path):
        if member!="results.jsonl":continue
        for line in handle:
            r=json.loads(line)
            result[r["id"]]={arm:next(m for m in r["methods"] if m["method"]==method) for arm,method in (("primary","guided_v04"),("degree","baseline"))}
    return result


def trace(g,row,fixed,excluded,where):
    active=g.available(fixed,excluded);actions=[];dirty_sum=preserved=frontier_scan=0
    initial=len(active)
    for step in row["trace"]:
        node=step["selected"]
        audit.require(node in active and step["remaining_count"]==len(active),"heap_trace_original_active_state",where,"invalid selected/count")
        if node not in active:break
        actions.append(node);removed={node}|(g.adj[node]&active)
        frontier=set()
        for deleted in removed:
            neighbors=g.adj[deleted]&active;frontier.update(neighbors);frontier_scan+=len(neighbors)
        frontier-=removed;active-=removed;dirty_sum+=len(frontier);preserved+=len(active)-len(frontier)
    audit.require(not active and sorted(set(fixed)|set(actions))==row["selected"],"heap_trace_complete_original_selection",where,"residual/selection differs")
    keys=("initialization_work","update_work","query_work")+(("priority_work",) if row["backend"]=="heap" else ())
    audit.require(row["feature_work"]==sum(row[k] for k in keys) and row["feature_work"]==sum(row["feature_primitives"].values()),"heap_charged_work_reconciliation",where,"work components/primitive counts differ")
    if row["backend"]=="full_scan":
        audit.require(row["score_evaluations"]==sum(s["remaining_count"] for s in row["trace"]),"heap_full_scan_score_count",where,"full scan score count differs")
    else:
        s=row["score_heap"];p=row["feature_primitives"]
        audit.require(s["mode"]=="local_priority" and s["eligible_local"] is True and s["static_scores"] is False and s["timeout_fallback"] is False,"heap_prespecified_local_mode",where,"selected programme locality/mode differs")
        audit.require(s["initial_score_evaluations"]==initial and s["refresh_score_evaluations"]==dirty_sum and s["invalidated_scores"]==dirty_sum and s["preserved_score_states"]==preserved and s["score_evaluations"]==row["score_evaluations"]==initial+dirty_sum,"heap_exact_local_frontier_invalidation",where,"local refresh does not cover exact surviving frontier")
        audit.require(p.get("score_frontier_scan",0)==frontier_scan and p.get("score_cache_delete",0)==initial,"heap_frontier_and_deletion_charges",where,"frontier/deletion charge differs")
        audit.require(p.get("score_heap_compare",0)==s["heap_comparisons"] and p.get("score_heap_push",0)==s["heap_pushes"] and p.get("score_heap_pop",0)==s["heap_pops"] and p.get("score_cache_write",0)==s["score_evaluations"],"heap_actual_priority_operation_receipts",where,"heap/cache operation receipts differ")


def one(dataset,reference,saved):
    path=ROOT/f"experiments/runs/v04/heap_{dataset}_v04_001.tar.gz"
    meta,hashes={},{};snapshot=None
    for member,handle,_ in audit.stream(path):
        if member in {"config.json","data.json","frozen_programs.json","executed_programs.json","execution.json","complete.json"}:
            raw=handle.read();meta[member]=json.loads(raw);hashes[member]=sha256(raw).hexdigest()
        elif member=="source_snapshot.zip":snapshot=handle.read()
    config,exe,done=meta["config.json"],meta["execution.json"],meta["complete.json"]
    expected=contexts(meta.pop("data.json"));programmes=meta["executed_programs.json"];freeze=meta["frozen_programs.json"]
    audit.require(len(expected)==(456 if dataset=="fresh" else 8)==done["contexts"]==exe["contexts"] and done["complete"] is True,"heap_assigned_population_complete",dataset,"assigned population mismatch")
    population="test" if dataset=="fresh" else "public"
    audit.require(config["repetitions"]==exe["repetitions"]==3 and config["program_cpu_seconds"]==5 and config["score_slice"] is True and config["selection_permitted"] is False and exe["selection_permitted"] is False and exe["original_confirmatory_runner_modified"] is False,"heap_frozen_extension_protocol",dataset,"protocol/selection differs")
    audit.require(hashes["data.json"]==config["input_sha256"][population]==exe["input_sha256"] and hashes["config.json"]==exe["config_sha256"] and hashes["frozen_programs.json"]==config["train_freeze_sha256"]==exe["train_freeze_sha256"]==audit.file_digest(ROOT/".research/train_v04_frozen.json"),"heap_pinned_input_config_freeze_bytes",dataset,"byte hashes differ")
    audit.require(freeze["test_accessed"] is False and freeze["selection_split"]=="train" and programmes=={a:freeze["programs"][p] for a,p in config["program_arms"].items()},"heap_same_train_frozen_asts",dataset,"executed programme differs from TRAIN")
    audit.require(sha256(snapshot).hexdigest()==exe["source_snapshot_sha256"],"heap_source_package_byte_hash",dataset,"source package differs")
    with zipfile.ZipFile(io.BytesIO(snapshot)) as z:
        audit.require(len(z.namelist())==len(set(z.namelist())),"heap_unique_source_zip_members",dataset,"duplicate source member")
        for name,h in exe["source_sha256"].items():
            audit.require(sha256(z.read("cipheur/"+name)).hexdigest()==h==audit.file_digest(ROOT/"cipheur"/name),"heap_exact_source_manifest_and_reviewed_local_bytes",name,"source differs from reviewed implementation")
        audit.require(sha256(z.read("config.json")).hexdigest()==hashes["config.json"] and sha256(z.read("frozen_programs.json")).hexdigest()==hashes["frozen_programs.json"],"heap_source_zip_prefrozen_receipts",dataset,"source/config/freeze archive mismatch")
    target=ROOT/"experiments/source_snapshots/v04/heap_execution_v04_source.zip"
    if target.exists():audit.require(target.read_bytes()==snapshot,"heap_preserved_source_package_same",dataset,"existing preserved package differs")
    else:target.write_bytes(snapshot)
    seen=set();counts=Counter();coverage=Counter();assessed=parity_failures=0;hasher=sha256();flat=defaultdict(list);failure_status=Counter();confirmation_parity=Counter();max_cpu=defaultdict(float);orders=Counter()
    index={key:i for i,key in enumerate(sorted(expected))};names=list(config["program_arms"])
    for member,handle,_ in audit.stream(path):
        if member!="results.jsonl":continue
        for line in handle:
            hasher.update(line);r=json.loads(line);where=dataset+"/"+r["id"];p=expected[r["id"]];g=audit.view(p["graph"]);f,x=p["fixed"],p["excluded"]
            audit.require(r["id"] not in seen and all(r[k]==p[k] for k in ("pair_id","side","split","family","cluster","fixed","excluded")) and r["graph_sha256"]==g.digest and r["n"]==len(g.contacts) and r["m"]==len(g.edges),"heap_original_input_identity",where,"duplicate or changed graph/context")
            seen.add(r["id"]);rows={};expected_order=[]
            for rep in range(3):
                for arm in names if (index[r["id"]]+rep)%2==0 else list(reversed(names)):
                    pi=names.index(arm);backends=["full_scan","heap"] if (index[r["id"]]+rep+pi)%2==0 else ["heap","full_scan"]
                    for pos,backend in enumerate(backends):expected_order.append((arm,rep,backend,pos))
            audit.require(len(r["runs"])==12 and len(r["paired"])==6 and r["selection_permitted"] is False,"heap_per_context_assigned_calls",where,"missing/extra calls")
            for i,row in enumerate(r["runs"]):
                key=(row["arm"],row["repetition"],row["backend"]);order=(row["arm"],row["repetition"],row["backend"],row["pair_position"])
                audit.require(key not in rows and order==expected_order[i] and row["sequence"]==i,"heap_interleaved_order_balance_receipt",where,"sequence/seed/backend differs")
                rows[key]=row;arm,rep,backend=key;w=where+"/"+str(key)
                counts[arm+"/"+backend+"/"+("completed" if row["completed"] else "failed")]+=1
                coverage[arm+"/"+backend+"/assigned"]+=1;coverage[arm+"/"+backend+"/completed"]+=int(row["completed"])
                if row["pair_position"]==0:orders[arm+"/"+backend+"/first"]+=1
                max_cpu[arm+"/"+backend+"/"+("complete" if row["completed"] else "failed")]=max(max_cpu[arm+"/"+backend+"/"+("complete" if row["completed"] else "failed")],row["cpu_seconds"])
                audit.require(row["fallback_used"] is False and row["score_slice"] is True and row["declared_cpu_seconds"]==5 and row["program_name"]==programmes[arm]["name"] and row["program_sha256"]==config["program_sha256"][arm]==exe["program_sha256"][arm],"heap_program_and_budget_identity",w,"programme/budget/fallback differs")
                if row["completed"]:
                    audit.check_selection(g,row["selected"],row["value"],f,x,w)
                    audit.require(row["feasible"] is True and Fraction(row["value_exact"])==g.value(row["selected"]),"heap_completed_exact_original_reward",w,"exact reward differs")
                    trace(g,row,f,x,w)
                    if dataset=="fresh":
                        old=reference[r["id"]][arm]
                        audit.require(old["completed"] and all(row[k]==old[k] for k in ("selected","value_exact","trace")),"heap_same_policy_as_original_confirmation",w,"execution changes original confirmation policy")
                        confirmation_parity[arm]+=1
                else:
                    audit.require(all(row.get(k) is None for k in ("selected","value","value_exact","trace","feasible","feature_work","score_evaluations")),"heap_failure_no_partial_or_quality",w,"partial schedule/reward retained")
                    failure_status[row["status"]]+=1
            pairs={}
            for pair in r["paired"]:
                key=(pair["arm"],pair["repetition"]);arm,rep=key
                audit.require(key not in pairs,"heap_unique_pair_receipt",where,"duplicate pair")
                pairs[key]=pair;full=rows[(arm,rep,"full_scan")];heap=rows[(arm,rep,"heap")];both=full["completed"] and heap["completed"]
                equal=all(full[k]==heap[k] for k in ("trace","selected","value","value_exact")) if both else None
                audit.require(pair["both_completed"]==both and pair["exact_trace_selection_value_parity"]==equal and pair["failed_backends"]==[b for b in ("full_scan","heap") if not rows[(arm,rep,b)]["completed"]],"heap_saved_pair_completion_and_parity",where,"saved parity/completion differs")
                if both:
                    assessed+=1;parity_failures+=not equal
                    audit.require(equal and full["compilation"]==heap["compilation"],"heap_completed_trace_and_compiler_equivalence",where,"exact trace/compiler parity fails")
                    audit.require(audit.near(pair["full_over_heap_cpu"],full["cpu_seconds"]/heap["cpu_seconds"]) and audit.near(pair["full_over_heap_work"],full["feature_work"]/heap["feature_work"]) and pair["score_evaluations_saved"]==full["score_evaluations"]-heap["score_evaluations"],"heap_saved_ratio_and_query_savings",where,"saved conditional cost differs")
                else:audit.require(all(pair[k] is None for k in ("full_over_heap_cpu","full_over_heap_work","score_evaluations_saved")),"heap_unassessable_ratio_null",where,"ratio credited without both complete")
            group="standard" if r["family"].startswith("standard_") else "dense_long" if r["family"].startswith("dense_long_") else r["family"]
            if dataset=="sparse":group=r["cluster"]
            for arm in names:
                valid=[pair for (a,_),pair in pairs.items() if a==arm and pair["both_completed"]]
                flat[group+"/"+arm].append({"stratum":group,"cluster":r["cluster"],"cpu_ratio":statistics.median(p["full_over_heap_cpu"] for p in valid) if valid else None,"work_ratio":statistics.median(p["full_over_heap_work"] for p in valid) if valid else None,"score_saved":statistics.median(p["score_evaluations_saved"] for p in valid) if valid else None,"assessable":len(valid)})
    audit.require(seen==set(expected) and sum(counts.values())==done["runs"]==12*len(expected) and dict(counts)==done["method_counts"] and hasher.hexdigest()==done["results_sha256"] and parity_failures==done["parity_failures"]==0,"heap_complete_counts_failure_hash",dataset,"counts/failures/result bytes differ")
    # The saved Boolean is vacuously true with zero assessable pairs; keep the denominator.
    audit.require(done["all_completed_pairs_match"]==(parity_failures==0),"heap_complete_parity_boolean_scope",dataset,"saved Boolean differs")
    audit.require(all(orders[a+"/heap/first"]==orders[a+"/full_scan/first"] for a in names),"heap_first_backend_balanced",dataset,"backend order imbalance")
    groups={}
    for name,entries in flat.items():
        groups[name]={"assigned_contexts":len(entries),"assessable_pairs":sum(e["assessable"] for e in entries),"cpu_ratio":bootstrap(entries,"cpu_ratio"),"work_ratio":bootstrap(entries,"work_ratio"),"score_evaluations_saved":bootstrap(entries,"score_saved")}
        actual=groups[name];s=saved["groups"][name]
        audit.require(actual["assigned_contexts"]==s["assigned_contexts"] and actual["assessable_pairs"]==s["assessable_pairs"],"heap_analysis_assigned_pair_counts",name,"analysis counts differ")
        for k,target in (("cpu_ratio","cpu_ratio_conditional"),("work_ratio","work_ratio_conditional"),("score_evaluations_saved","score_evaluations_saved_conditional")):
            a,b=actual[k],s[target]
            audit.require((a is None and b is None) or (a and b and all(abs(a[v]-b[v])<1e-12 for v in ("estimate","lower","upper")) and a["source_clusters"]==b["source_clusters"]),"heap_independent_context_median_cluster_ci",name,k)
    audit.require(dict(coverage)==saved["coverage"],"heap_analysis_full_failure_coverage",dataset,"saved coverage differs")
    return {"archive_sha256":audit.file_digest(path),"input_sha256":hashes["data.json"],"contexts":len(expected),"assigned_runs":sum(counts.values()),"method_counts":dict(counts),"assessable_pairs":assessed,"exact_trace_mismatches":parity_failures,"original_confirmatory_trace_checks":dict(confirmation_parity),"declared_cpu_target":5,"max_observed_cpu_seconds":dict(max_cpu),"failure_statuses":dict(failure_status),"balanced_first_backend_counts":dict(orders),"source_snapshot_sha256":exe["source_snapshot_sha256"],"groups":groups,"scope":"Ratios conditional on both complete; context medians precede source-cluster bootstrap; sparse zero-assessable parity is unknown, not confirmed."}


if __name__=="__main__":
    saved=json.loads((ROOT/"experiments/analysis/v04/heap_summary.json").read_bytes());reference=confirmation()
    reports={dataset:one(dataset,reference,saved[dataset]) for dataset in ("fresh","sparse")}
    report={"datasets":reports,"checks":dict(audit.CHECKS),"issues":list(audit.ISSUES.values()),"scope":"Read-only streaming archive verification; no timing/policy/solver rerun or selection. Exact frontiers and original-graph witnesses independently checked. Source matches reviewed backend; no online oracle/model/native call in extension."}
    path=ROOT/"experiments/analysis/v04/heap_extension_audit.json";path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(path),"checks":sum(audit.CHECKS.values()),"issues":report["issues"],"datasets":{n:{k:r[k] for k in ("contexts","assigned_runs","method_counts","assessable_pairs","exact_trace_mismatches","original_confirmatory_trace_checks")} for n,r in reports.items()}}))
    raise SystemExit(int(any(i["severity"]=="error" for i in report["issues"])))
