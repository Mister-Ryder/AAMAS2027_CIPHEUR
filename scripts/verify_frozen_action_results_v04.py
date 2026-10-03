"""Independent audit of retrospective frozen-pool held-out action evidence.

Streams saved archives, replays state planning and scalar choices, verifies
component lower witnesses and small exact intervals, and excludes counterfactual
states from per-program summaries. Never calls a deployed oracle or native solver.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import ast
import itertools
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import time
import zipfile

import verify_v03_evidence as audit
import verify_v04_training as train

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"experiments/runs/v04/frozen_action_v04_001.tar.gz"
SOURCE=ROOT/"experiments/source_snapshots/v04/frozen_action_v04_001_source.zip"
TRAIN_SOURCE=ROOT/"experiments/source_snapshots/v04/relevance_v04_source.zip"


def rule(source,names):
    parsed=ast.parse(source,mode="eval")
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.IfExp,ast.Compare,ast.Name,
             ast.Load,ast.Constant,ast.Call,ast.Add,ast.Sub,ast.Mult,ast.Div,
             ast.Pow,ast.USub,ast.UAdd,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    for node in ast.walk(parsed):
        if not isinstance(node,allowed):raise ValueError("Unaudited scalar syntax "+type(node).__name__)
        if isinstance(node,ast.Name) and node.id not in names|{"min","max","abs"}:raise ValueError("Unknown scalar input "+node.id)
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in {"min","max","abs"} or node.keywords):raise ValueError("Unaudited scalar call")
    return compile(parsed,"<independent-frozen-rule>","eval")


class ChoiceReplay:
    """Independent graph AST semantics; adjacency restricts induced-edge scans."""
    def __init__(self,g,active,programs):
        self.g,self.active,self.programs=g,set(active),programs
        self.total=g.value(active);self.root_cache={};self.set_cache={};self.queries=0
        base={"weight","duration","degree","conflict_weight","max_conflict_weight",
              "compatible_weight","remaining_count","station_gap","satellite_gap"}
        self.code={cid:rule(p["rule"],base|{f["name"] for f in p["features"]}) for cid,p in programs.items()}

    def expression(self,e,root):
        key=(train.canonical(e),root)
        if key in self.root_cache:return self.root_cache[key]
        op=e["op"];a=[self.expression(x,root) for x in e.get("args",[])]
        if op=="root":v=root
        elif op=="available":v=self.active
        elif op=="neighbors":v=self.g.adj[a[0]]&self.active
        elif op=="singleton":v={a[0]}&self.active
        elif op=="union":v=a[0]|a[1]
        elif op=="difference":v=a[0]-a[1]
        elif op=="induced_edges":v={(u,w) for u in a[0] for w in self.g.adj[u]&a[0] if u<w}
        elif op=="count":v=len(a[0])
        elif op=="max_weight":v=max((self.g.contacts[w]["weight"] for w in a[0]),default=0.0)
        elif op in ("edge_min_weight_sum","edge_weight_product_sum"):
            v=math.fsum(min(self.g.contacts[u]["weight"],self.g.contacts[w]["weight"]) if op=="edge_min_weight_sum" else self.g.contacts[u]["weight"]*self.g.contacts[w]["weight"] for u,w in sorted(a[0]))
        elif op in ("clique_cover_weight","greedy_independent_weight"):
            setkey=(op,frozenset(a[0]))
            if setkey not in self.set_cache:
                order=sorted(a[0],key=lambda w:(-self.g.weights[w],w));remaining=set(a[0]);terms=[]
                for w in order:
                    if w not in remaining:continue
                    if op=="greedy_independent_weight":
                        terms.append(self.g.contacts[w]["weight"]);remaining.difference_update(self.g.adj[w]|{w})
                    else:
                        group=[w];remaining.remove(w)
                        for u in order:
                            if u in remaining and all(u in self.g.adj[q] for q in group):group.append(u);remaining.remove(u)
                        terms.append(max(self.g.contacts[q]["weight"] for q in group))
                self.set_cache[setkey]=math.fsum(terms)
            v=self.set_cache[setkey]
        else:raise ValueError("Unaudited feature operation "+op)
        self.root_cache[key]=v;return v

    def values(self,cid,v):
        g=self.g;c=g.contacts[v];n=g.adj[v]&self.active;ns=g.value(n);constraints=g.raw["constraints"]
        values={"weight":c["weight"],"duration":c["end"]-c["start"],"degree":len(n),
            "conflict_weight":float(ns),"max_conflict_weight":float(max((g.weights[u] for u in n),default=0)),
            "compatible_weight":float(self.total-ns-g.weights[v]),"remaining_count":len(self.active),
            "station_gap":constraints.get("station_gap",constraints.get("ground_trans_time",0)),
            "satellite_gap":constraints.get("satellite_gap",constraints.get("satellite_change_time",0))}
        values.update({f["name"]:self.expression(f["expression"],v) for f in self.programs[cid]["features"]})
        return values

    def score(self,cid,v):
        self.queries+=1
        value=float(eval(self.code[cid],{"__builtins__":{}},{**self.values(cid,v),"min":min,"max":max,"abs":abs}))
        if not math.isfinite(value):raise ValueError("Nonfinite independent score")
        return value

    def chosen(self,cid):return min(sorted(self.active),key=lambda v:(-self.score(cid,v),v))


def main():
    started=time.perf_counter()
    meta,hashes=audit.json_members(ARCHIVE,{"config.json","execution.json","complete.json","data.json","frozen_programs.json","program_pool.json"})
    config,exe,done=meta["config.json"],meta["execution.json"],meta["complete.json"]
    frozen,pool=meta["frozen_programs.json"],meta["program_pool.json"]
    programmes={e["id"]:e["program"] for e in pool}
    for key,member in (("data_sha256","data.json"),("frozen_sha256","frozen_programs.json"),("config_sha256","config.json")):
        audit.require(hashes[member]==exe[key]==config.get(key,exe[key]),"action_input_config_freeze_bytes",member,"hash differs")
    audit.require(hashes["data.json"]==audit.file_digest(ROOT/".research/fresh_data_v04_002/data.json") and hashes["frozen_programs.json"]==audit.file_digest(ROOT/".research/train_v04_frozen.json"),"action_original_input_freeze_identity","inputs","original fixed bytes differ")
    audit.require(config["selection_permitted"] is False and exe["selection_permitted"] is False and done["selection_permitted"] is False and frozen["test_accessed"] is False and frozen["selection_split"]=="train" and exe["model_calls"]==0,"action_no_selection_no_models","scope","selection/freeze/model declaration differs")
    audit.require(list(programmes)==config["program_ids"] and len(programmes)==len(pool)==6 and all(p==frozen["programs"][cid] for cid,p in programmes.items()),"action_six_immutable_programmes","pool","duplicate/changed frozen AST")
    with zipfile.ZipFile(SOURCE) as z,zipfile.ZipFile(TRAIN_SOURCE) as t:
        inventory={PurePosixPath(n).name:sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith("cipheur/") and n.endswith(".py")}
        audit.require(inventory==exe["source_sha256"],"action_complete_executed_source_manifest","source","source ZIP differs")
        audit.require(sha256(z.read("configs/frozen_action_audit_v04.json")).hexdigest()==hashes["config.json"],"action_prefrozen_config_bytes","config","config absent from original source ZIP")
        core=("relevance_synthesis_v04.py","oracle.py","model.py","graph_features.py","compiled.py")
        audit.require(all(inventory[n]==sha256(t.read("cipheur/"+n)).hexdigest() for n in core),"action_unchanged_original_train_engine","source","TRAIN mechanism/score core changed")
        original_config=json.loads(t.read("configs/relevance_v04_train.json"))
        audit.require(config["cancellation"]==original_config["cancellation"] and config["max_matched_full_comparisons"]==0 and config["max_states_per_context"]==config["max_rollout_steps"]==2 and config["program_cpu_seconds"]==5,"action_fixed_query_and_state_budgets","config","budget/state caps differ")
    contexts={};split_counts=Counter()
    for split in config["splits"]:
        for pair in meta["data.json"][split]:
            for side in ("left","right"):
                key=(pair["id"],side);audit.require(key not in contexts,"action_input_unique_context",str(key),"duplicate")
                contexts[key]=(split,pair);split_counts[split]+=1
    audit.require(split_counts=={"validation":132,"test":456} and len(contexts)==config["contexts"]==exe["contexts"]==588,"action_prespecified_full_population","inputs",str(split_counts))
    # Only selections/traces are retained for overlap checks with the primary study.
    prior={}
    for member,handle,_ in audit.stream(ROOT/"experiments/runs/v04/advanced_fresh_v04_001.tar.gz"):
        if member!="results.jsonl":continue
        for line in handle:
            r=json.loads(line)
            prior[(r["pair_id"],r["side"]) ]={m["method"]:{k:m.get(k) for k in ("completed","selected","trace","value")} for m in r["methods"] if m["method"] in programmes}
    seen=set();members=set();hasher=sha256();counts=Counter();groups=defaultdict(list);family_counts=Counter();regret_rows=[];preferences=Counter();aggregate=defaultdict(Counter);parity=Counter();query_count=0
    for member,handle,full in audit.stream(ARCHIVE):
        audit.require(full not in members,"action_unique_archive_member",str(ARCHIVE),full);members.add(full)
        if member=="source_snapshot.zip":
            audit.require(sha256(handle.read()).hexdigest()==exe["source_snapshot_sha256"],"action_runtime_source_zip_hash","source","nested snapshot hash differs")
        if member!="results.jsonl":continue
        for line in handle:
            hasher.update(line);c=json.loads(line);key=(c["pair_id"],c["side"]);where=str(key)
            audit.require(key in contexts and key not in seen,"action_complete_unique_context",where,"duplicate/unknown");seen.add(key)
            if key not in contexts:continue
            split,pair=contexts[key];g=audit.view(pair[c["side"]]);family_counts[split+"/"+c["family"]]+=1
            audit.require(c["execution_complete"] is True and c["selection_permitted"] is False and c["family"]==pair["family"] and c["size"]==len(g.contacts) and audit.view(c["graph"]).digest==g.digest,"action_original_graph_success_scope",where,"graph/scope mismatch")
            rows={r["candidate_id"]:r for r in c["rows"]}
            audit.require(len(rows)==len(c["rows"])==6 and set(rows)==set(programmes),"action_all_six_rollouts",where,"missing/extra/duplicate")
            fixed,excluded=pair.get("fixed",[]),pair.get("excluded",[]);planned={}
            for cid,r in rows.items():
                counts["schedule_assignments"]+=1;counts["schedules_completed" if r["completed"] else "schedule_failures"]+=1
                audit.require(all(isinstance(r[k],(int,float)) and math.isfinite(r[k]) and r[k]>=0 for k in ("cpu_seconds","wall_seconds")),"action_all_assigned_schedule_cost",where+cid,"missing cost")
                if not r["completed"]:
                    audit.require(all(r[k] is None for k in ("value","selected","trace","feature_work")),"action_rollout_failure_null",where+cid,"partial/fallback schedule")
                    continue
                audit.check_selection(g,r["selected"],r["value"],fixed,excluded,where+cid)
                chosen=list(fixed)
                for i,step in enumerate(r["trace"]):
                    active=g.available(chosen,excluded)
                    audit.require(step["selected"] in active and step["remaining_count"]==len(active),"action_rollout_feasible_trace",where+cid,"bad boundary")
                    chosen.append(step["selected"])
                audit.require(not g.available(chosen,excluded) and set(chosen)==set(r["selected"]),"action_rollout_complete_trace",where+cid,"selection differs")
                for step in range(min(config["max_rollout_steps"],len(r["trace"]))+1):
                    boundary=tuple(sorted(list(fixed)+[t["selected"] for t in r["trace"][:step]]))
                    st=planned.setdefault(boundary,{"fixed":list(boundary),"sources":[],"id":train.canonical([g.digest,boundary,tuple(excluded)])})
                    st["sources"].append({"candidate_id":cid,"step":step})
                if split=="test":
                    old=prior[key][cid];both=old["completed"] and r["completed"]
                    if both:audit.require(all(old[k]==r[k] for k in ("selected","trace","value")),"action_original_quality_rollout_parity",where+cid,"same AST changed trace/reward")
                    parity[cid+"/both_completed" if both else cid+"/unassessable"]+=1
            initial=tuple(sorted(fixed));plan=sorted(planned.items(),key=lambda x:(x[0]!=initial,-len(x[1]["sources"]),x[1]["id"]))[:2]
            expected_states=[s for _,s in plan if g.available(s["fixed"],excluded)]
            audit.require(c["state_pool_count"]==len(planned) and c["states_planned"]==len(plan) and c["states_unsampled"]==len(planned)-len(plan) and len(c["states"])==len(expected_states),"action_coverage_state_plan_counts",where,"plan differs")
            aggregate[split+"/"+c["family"]]["contexts"]+=1
            own=defaultdict(list)
            for state,want in zip(c["states"],expected_states):
                sw=where+"/"+state["id"]
                audit.require(all(state[k]==want[k] for k in ("id","fixed","sources")) and state["excluded"]==excluded,"action_coverage_state_plan_exact",sw,"boundary/source/priority differs")
                audit.require(state["counterfactual_choices_not_used_for_selection"] is True and state["matched_full_residual"]==[],"action_no_counterfactual_selection_or_redundant_matched_search",sw,"scope differs")
                counts["audited_states"]+=1;aggregate[split+"/"+c["family"]]["states"]+=1
                active=g.available(state["fixed"],excluded);sources={s["candidate_id"] for s in state["sources"]};choices=state["choices"]
                audit.require(set(choices)|set(state["choice_failures"])==set(programmes) and not set(choices)&set(state["choice_failures"]),"action_choice_failure_partition",sw,"candidate coverage differs")
                replay=ChoiceReplay(g,active,programmes)
                for cid,v in choices.items():
                    audit.require(v in active and replay.chosen(cid)==v,"action_independent_exact_argmax",sw+cid,"actual choice differs")
                    # Validate adjacency optimized semantics against the pre-existing
                    # independent TRAIN graph decoder at each saved chosen root.
                    values=replay.values(cid,v)
                    for f in programmes[cid]["features"]:audit.require(values[f["name"]]==train.expression(g,active,v,f["expression"]),"action_feature_decoder_crosscheck",sw+cid+f["name"],"feature decoder differs")
                    if cid in sources:
                        source=next(s for s in state["sources"] if s["candidate_id"]==cid)
                        audit.require(rows[cid]["trace"][source["step"]]["selected"]==v,"action_reached_choice_matches_rollout",sw+cid,"own action differs from own trace")
                query_count+=replay.queries
                actions=state["actions"]
                audit.require(actions==sorted(set(choices.values())) and {(d["a"],d["b"]) for d in state["differences"]}==set(itertools.combinations(actions,2)) and len(state["differences"])==len(actions)*(len(actions)-1)//2,"action_complete_finite_pool",sw,"pool/difference duplicates or omissions")
                endpoints={};cache={}
                for d in state["differences"]:
                    endpoints[d["a"],d["b"]]=train.delta(g,state,d,sw,Fraction(config["epsilon"]))
                    counts["difference_status_"+d["status"]]+=1;aggregate[split+"/"+c["family"]]["difference_status_"+d["status"]]+=1
                    if d["preferred"] is not None:
                        other=d["b"] if d["preferred"]==d["a"] else d["a"]
                        for cid,v in choices.items():
                            if cid in sources and v==other:preferences[split+"/"+cid+"/certified_inferior_action"]+=1
                            if cid in sources and v==d["preferred"]:preferences[split+"/"+cid+"/certified_preferred_action"]+=1
                    for side in ("a","b"):
                        for part in d["unmatched"][side]:
                            k=tuple(part["vertices"])
                            audit.require(k not in cache or cache[k]==part["bound"],"action_cached_component_bound_consistent",sw,"cached interval differs")
                            cache[k]=part["bound"]
                budget=state["oracle_budget"];limits=config["cancellation"]
                calls=sum(v["reason"]!="call_budget_trivial_interval" for v in cache.values());expanded=sum(v["expanded"] for v in cache.values())
                audit.require(calls==budget["calls"]<=limits["max_calls"] and expanded==budget["expanded_nodes"]<=limits["max_nodes"] and budget["cache_components"]==len(cache) and budget["max_calls"]==limits["max_calls"] and budget["max_nodes"]==limits["max_nodes"],"action_component_query_budget_receipt",sw,"calls/cache/nodes differ")
                for vertices,b in cache.items():
                    audit.require(b["expanded"]<=limits["nodes_per_component"] and (len(vertices)<=limits["max_search_component"] or b["expanded"]==0),"action_component_individual_search_cap",sw,"component nodes exceed cap")
                    if b["reason"]=="call_budget_trivial_interval":audit.require(b["lower_exact"]=="0" and Fraction(b["upper_exact"])==g.value(vertices) and b["selected"]==[],"action_call_cap_trivial_sound_interval",sw,"unsound exhausted-call interval")
                counts["component_calls"]+=calls;counts["expanded_nodes"]+=expanded
                audit.require(set(state["regret"])==set(choices),"action_regret_complete_candidate_pool",sw,"missing regret")
                normalization=max(1,statistics.fmean(t["weight"] for t in g.raw["contacts"]))
                for cid,saved in state["regret"].items():
                    chosen=choices[cid];lo=hi=Fraction(0);unknown=0
                    for d in state["differences"]:
                        if chosen not in (d["a"],d["b"]):continue
                        l,u=endpoints[d["a"],d["b"]]
                        if chosen==d["a"]:l,u=-u,-l
                        lo,hi=max(lo,l),max(hi,u);unknown+=d["status"]=="unknown"
                    reached=cid in sources
                    audit.require(saved["chosen"]==chosen and (Fraction(saved["lower_exact"]),Fraction(saved["upper_exact"]))==(lo,hi) and saved["unknown_comparisons"]==unknown and saved["actual_reached_in_recorded_rollout"]==reached and Fraction(saved["lower"])<=lo and Fraction(saved["upper"])>=hi,"action_exact_pool_regret_reached_arithmetic",sw+cid,"regret/scope differs")
                    counts["own_reached_regret_rows" if reached else "counterfactual_regret_rows_excluded"]+=1
                    if reached:
                        r={"split":split,"family":c["family"],"pair_id":c["pair_id"],"side":c["side"],"state_id":state["id"],"program_id":cid,"lower":float(lo),"upper":float(hi),"normalized_lower":float(lo)/normalization,"normalized_upper":float(hi)/normalization,"unknown":unknown,"positive_certified_regret":lo>Fraction(config["epsilon"]),"certified_zero_pool_regret":hi==0}
                        regret_rows.append(r);own[cid].append(r)
            for cid,r in rows.items():
                reached=own[cid]
                population="standard" if c["family"].startswith("standard_") else "dense_long" if c["family"].startswith("dense_long_") else c["family"]
                groups[split+"/"+population+"/"+cid].append({"completed":r["completed"],"reached":len(reached),"lower":statistics.fmean(t["normalized_lower"] for t in reached) if reached else None,"upper":statistics.fmean(t["normalized_upper"] for t in reached) if reached else None,"positive":sum(t["positive_certified_regret"] for t in reached),"zero":sum(t["certified_zero_pool_regret"] for t in reached),"unknown":sum(t["unknown"] for t in reached)})
    audit.require(seen==set(contexts) and len(seen)==done["contexts"] and done["audit_failures"]==0 and done["execution_complete"] is True and hasher.hexdigest()==done["results_sha256"],"action_complete_harness_results_hash","complete","missing/context failure/hash differs")
    summaries={}
    for key,rows in sorted(groups.items()):
        finite=[r for r in rows if r["lower"] is not None]
        summaries[key]={"assigned_contexts":len(rows),"completed_rollouts":sum(r["completed"] for r in rows),"contexts_with_own_reached_audited_state":len(finite),"own_reached_states":sum(r["reached"] for r in rows),"context_mean_weight_normalized_regret_lower":statistics.fmean(r["lower"] for r in finite) if finite else None,"context_mean_weight_normalized_regret_upper":statistics.fmean(r["upper"] for r in finite) if finite else None,"certified_positive_own_states":sum(r["positive"] for r in rows),"certified_zero_pool_regret_own_states":sum(r["zero"] for r in rows),"unknown_own_comparisons":sum(r["unknown"] for r in rows)}
    report={"scope":"Retrospective unchanged frozen-six-program finite-pool action audit; no selection/proposal/native/deployed-oracle calls","archive_sha256":audit.file_digest(ARCHIVE),"source_zip_sha256":audit.file_digest(SOURCE),"member_sha256":hashes,"input_splits":dict(split_counts),"families":dict(family_counts),"counts":dict(counts),"independently_replayed_scalar_queries":query_count,"small_component_checks":dict(train.COUNTS),"distinct_bruteforced_small_components":len(train.SMALL),"original_test_rollout_parity":dict(parity),"summaries":summaries,"own_reached_strict_preference_incidences":dict(preferences),"checks":dict(audit.CHECKS),"issues":list(audit.ISSUES.values()),"seconds":time.perf_counter()-started,"limitations":["Large component upper endpoints are computational receipts tied to unchanged, hash-verified executed TRAIN oracle code; archived B&B frontier proofs are absent.","Regret endpoints are deterministic bounds, not confidence intervals; summarized only over each policy's actual sampled reached states.","Actual state plans differ across programs; means are conditional on selected reached boundaries, not estimates of all-state or all-action regret.","Strict-preference incidences can repeat within shared contexts/states; they are not independent certificates or causal attribution of global quality.","Offline evidence does not change deployed rankings or TRAIN selections. Trace parity against the original test study is conditional on both completed.","Declarations establish archived no-selection provenance, not proof of every external human information access."]}
    output=ROOT/"experiments/analysis/v04/frozen_action_audit.json";output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    (ROOT/"experiments/analysis/v04/frozen_action_reached_states.json").write_text(json.dumps({"scope":report["scope"],"rows":regret_rows},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"checks":sum(audit.CHECKS.values()),"issues":report["issues"],"counts":report["counts"],"small":report["small_component_checks"],"seconds":report["seconds"]}))
    return int(any(i["severity"]=="error" for i in report["issues"]))


if __name__=="__main__":raise SystemExit(main())
