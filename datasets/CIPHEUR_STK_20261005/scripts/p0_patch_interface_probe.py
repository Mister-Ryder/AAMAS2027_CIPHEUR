"""One bounded, registered G3-failure diagnostic; no TEST and no synthesis.

Expands real destroyed incumbent neighbourhoods, then compares the unchanged
actual repair search and a separately named pairwise-commit choice interface.
The original frozen P0 script and its evidence are never modified.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import time

_args=argparse.ArgumentParser(add_help=False)
_args.add_argument("--data-root",type=Path)
_args.add_argument("--cipheur-root",type=Path)
_args.add_argument("--output-root",type=Path)
_args.add_argument("--p0-output-root",type=Path)
_known,_=_args.parse_known_args()
SCRIPT=Path(__file__).resolve()
spec=importlib.util.spec_from_file_location("frozen_p0_evidence",SCRIPT.with_name("p0_evidence.py"))
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
ROOT=core.ROOT
OUTPUT=(_known.output_root or ROOT/"analysis"/"p0_interface_probe").resolve()
P0=(_known.p0_output_root or ROOT/"analysis"/"p0").resolve()
from cipheur.repair_v06 import _initialize, _Meter, _priorities

TARGETS=((8,16),(16,64),(32,128))
ANCHORS=10
HEADS=("degree","existing_frozen","certified_reference")


def register():
    row=json.loads((core.PROJECT/"examples"/"frozen_joint_bank_v06.json").read_text(encoding="utf-8"))["programs"][0]
    value={"stage":"P0 G3 failure branch, one bounded interface diagnostic",
        "scope":"TRAIN r000/r001 only; no TEST, no batch model calls",
        "sources":list(core.SOURCES),"anchors_per_source":ANCHORS,
        "anchor_rule":"original preregistered P0 manifest first10 query slots, preserving original a,b; unavailable slot stays unavailable",
        "destroy_targets_and_patch_caps":[{"destroy_target":d,"patch_cap":p} for d,p in TARGETS],
        "destroy_expansion_rule":"seed original query destroy; breadth-first distances in g1200 complete graph from original target a, unweighted; append external-incumbent contacts by minimum distance then contact-ID order until8/16/32; never inspect preference or scores for expansion",
        "patch_rule":"F=original common g1200 feasible incumbent minus expandedD; actual free region V minus (F union N1200(F)); retain expandedD+a+b, then original full-residual Degree-priority extras up to declared cap",
        "pair_and_boundary":"same complete contacts, weights, resources,a,b,F,P,X=V minus(F unionP) in g340/g1200; actions remain individually feasible and competing",
        "gap_pair_seconds":[340,1200],"satellite_gap_seconds":150,
        "certificate_budget_seconds_four_spaces":core.QUERY_SECONDS,
        "upper_bound_intersection":"U=min(valid original root clique-partition envelope, valid remaining-frontier envelope); clique regrouping is sound but need not monotonically tighten root envelope",
        "epsilon_ticks":core.EPSILON_TICKS,
        "B&B_probe":"unchanged actual repair_v06 _solve/_Meter/_priorities, same2000-node allowance and lazy head factory; exact patch value ordering invariant when solved",
        "commit_probe":"NEW DIAGNOSTIC INTERFACE: evaluate a/b at exactly currentP, irrevocably commit higher-scored action (contact-ID tie), then unchanged dynamic exact Degree initializer completes P minus committed-action neighbours; all heads share completion",
        "commit_acceptance":"save unguarded forced-choice feasible value; separately save common positive-gain guard against originalD. No claim this is original V06 or a new final solver",
        "reference_head":"B&B probe uses frozen P0 pair-score-swap rule; commit probe selects certified strict preferred action. Unknown/tie has Degree fallback, expressly flagged; offline probe not deployable comparator",
        "frozen_id":row["id"],"frozen_program":row["program"],
        "frozen_p0_script_sha256":core.digest(SCRIPT.with_name("p0_evidence.py")),
        "script_sha256":core.digest(SCRIPT),
        "repair_source_sha256":core.digest(core.PROJECT/"cipheur"/"repair_v06.py"),
        "numeric_namespace":"fraction_seconds_binary_fsum_base9_v1",
        "P1":"no automatic progression; complete quotient and joint P0 acceptance still required",
        "registered_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    path=OUTPUT/"registration.json"
    if path.exists():
        old=json.loads(path.read_text(encoding="utf-8"))
        for k,v in value.items():
            if k!="registered_utc" and old[k]!=v:raise ValueError("Probe registration changed:"+k)
        return old
    core.dump(path,value)
    return value


def breadth_first_order(graph, target, incumbent):
    visited,frontier={target},{target}
    candidates=[]
    depth=0
    while frontier:
        candidates.extend((depth,v) for v in sorted(frontier&incumbent))
        nxt=set()
        for v in frontier:nxt.update(graph.adj[v])
        nxt-=visited
        visited.update(nxt)
        frontier=nxt
        depth+=1
        if len(candidates)>=max(d for d,_ in TARGETS):break
    return sorted(candidates,key=lambda x:(x[0],x[1]))


def prepare(source,left,right,ids,out,p0manifest,incumbent):
    index={v:i for i,v in enumerate(ids)}
    full=set(ids)
    degree={v:right.nodes[v].weight/max(1,len(right.adj[v])) for v in ids}
    queries=[]
    for old in p0manifest["queries"][:ANCHORS]:
        for goal,cap in TARGETS:
            identity=f"{source}:q{old['slot']:03d}:d{goal:02d}"
            if old.get("status")=="unavailable":
                queries.append({"id":identity,"source":source,"anchor_slot":old["slot"],"destroy_target":goal,
                    "status":"unavailable","reason":"original_preregistered_anchor_unavailable"});continue
            a,b=ids[old["a"]],ids[old["b"]]
            destroy={ids[i] for i in old["destroy_indices"]}
            additions=[]
            for distance,v in breadth_first_order(right,a,incumbent):
                if len(destroy)>=goal:break
                if v not in destroy:
                    destroy.add(v);additions.append({"node_index":index[v],"graph_distance":distance})
            if len(destroy)<goal:
                queries.append({"id":identity,"source":source,"anchor_slot":old["slot"],"destroy_target":goal,
                    "status":"unavailable","reason":"reachable_incumbent_inventory_below_destroy_target"});continue
            fixed=incumbent-destroy
            blocked=set(fixed)
            for v in fixed:blocked.update(right.adj[v])
            free=full-blocked
            retained=destroy|{a,b}
            extra=sorted(free-retained,key=lambda v:(-degree[v],v))
            patch=retained|set(extra[:cap-len(retained)])
            if not retained<=free:raise AssertionError("Expanded neighbourhood lost anchor/seed")
            if b not in left.adj[a] or b not in right.adj[a]:raise AssertionError("Actions no longer compete")
            if any(left.adj[v]&fixed or right.adj[v]&fixed for v in patch):raise AssertionError("Actions not jointly boundary-available")
            fi=sorted(index[v] for v in fixed);pi=sorted(index[v] for v in patch)
            xi=sorted(set(range(len(ids)))-set(fi)-set(pi))
            queries.append({"id":identity,"source":source,"anchor_slot":old["slot"],
                "destroy_target":goal,"patch_cap":cap,"a":old["a"],"b":old["b"],
                "a_contact_id":a,"b_contact_id":b,"destroy_indices":sorted(index[v] for v in destroy),
                "fixed_indices":fi,"patch_indices":pi,"full_free_region_size":len(free),
                "restricted":len(free)!=len(patch),"expansion_additions":additions,
                "excluded_encoding":"universe_indices minus fixed_indices minus patch_indices",
                "excluded_count":len(xi),"excluded_indices_sha256":core.hash_indices(xi),
                "fixed_indices_sha256":core.hash_indices(fi),"patch_indices_sha256":core.hash_indices(pi),
                "same_fixed_excluded":True,"both_actions_feasible_competing_both_configurations":True})
    record={"source":source,"prepared_before_labels":True,"queries":queries,
        "original_p0_query_manifest_sha256":core.digest(P0/source/"query_manifest.json"),
        "original_common_external_incumbent_sha256":core.digest(P0/source/"external_incumbent.json"),
        "graph_npz_sha256":{f"g{gap:04d}":core.digest(ROOT/"graphs"/source/f"g{gap:04d}.npz") for gap in (340,1200)}}
    core.dump(out/"query_manifest.json",record)
    return record


def commit_probe(graph,ids,query,cert,side,program):
    patch={ids[i] for i in query["patch_indices"]}
    fixed={ids[i] for i in query["fixed_indices"]}
    destroy={ids[i] for i in query["destroy_indices"]}
    a,b=ids[query["a"]],ids[query["b"]]
    pref=cert["signs"][side]["preference"]
    baseline=sum((graph.nodes[v].weight for v in destroy),Fraction())
    fixed_value=sum((graph.nodes[v].weight for v in fixed),Fraction())
    rows=[]
    for head in HEADS:
        meter=_Meter(None,"cpu",None,0)
        meter.tick("diagnostic_pair_commit_input",len(patch)+2)
        called=time.perf_counter()
        if head=="existing_frozen":
            evaluator=core.CompiledEvaluator(graph,program,patch,meter,score_slice=True)
            scores={v:evaluator.score(v) for v in (a,b)}
        else:
            scores={v:graph.nodes[v].weight/max(1,len(graph.adj[v]&patch)) for v in (a,b)}
            meter.tick("degree_priority",len(graph.adj[a])+len(graph.adj[b])+4)
        preferred=min((a,b),key=lambda v:(-scores[v],v))
        reference_certified=head=="certified_reference" and pref in ("a","b")
        if reference_certified:
            meter.tick("offline_reference_lookup")
            preferred=a if pref=="a" else b
        scoring_seconds=time.perf_counter()-called
        completion_start=time.perf_counter()
        local={preferred};trace=[]
        weights={v:graph.nodes[v].weight for v in patch}
        meter.tick("exact_weight_conversion",len(patch))
        _initialize(graph,local,patch,weights,meter,trace)
        completion_seconds=time.perf_counter()-completion_start
        updated=fixed|local
        value=sum((graph.nodes[v].weight for v in local),Fraction())
        meter.sealed=True
        meter.tick("final_validation",len(updated)+sum(len(graph.adj[v]) for v in updated))
        if not graph.feasible(updated) or preferred not in local or not fixed<=updated:
            raise AssertionError("Irrevocable diagnostic commit lost feasibility/boundary")
        accepted=value>baseline
        retained=fixed|local if accepted else fixed|destroy
        rows.append({"interface":"new_pairwise_commit_then_common_dynamic_Degree_completion",
            "query_id":query["id"],"source":query["source"],"side":side,"head":head,
            "a_contact_id":a,"b_contact_id":b,"selected_action":preferred,
            "pair_scores":{v:str(scores[v]) for v in scores},"certified_preference":pref,
            "choice_matches_strict_certificate":preferred==(a if pref=="a" else b) if pref in ("a","b") else None,
            "reference_uses_strict_certificate":reference_certified,
            "reference_fallback_reason":None if reference_certified or head!="certified_reference" else pref,
            "scoring_seconds":scoring_seconds,"completion_seconds":completion_seconds,
            "cpu_seconds":time.process_time()-meter.cpu_start,"wall_seconds":time.perf_counter()-meter.wall_start,
            "meter":dict(meter),"operation_proxy":meter.get("feature_work",0)+meter.get("repair_work",0),
            "local_selected":sorted(local),"local_value_exact":str(value),
            "initial_destroy_value_exact":str(baseline),"unguarded_gain_exact":str(value-baseline),
            "full_schedule_unguarded_value_exact":str(fixed_value+value),
            "positive_gain_guard_accepted":accepted,
            "full_schedule_guarded_value_exact":str(fixed_value+max(value,baseline)),
            "guarded_selected_set_sha256":core.sha256(json.dumps(sorted(retained)).encode()).hexdigest(),
            "completion_trace":trace,"local_completion_domain":"recordedP minus selected-action conflicts",
            "scope":"diagnostic restricted choicepoint, no claim of original V06/global final solver performance"})
    return rows


def forced_bound(nodes,masks,weights,action_local,seconds):
    """Same integer conditional B&B, intersect two valid nonnested covers.

    A new clique partition of a residual need not refine the root partition.
    Both enclosures are valid; intersect them instead of asserting monotonicity.
    The frozen original P0 implementation is preserved without edits.
    """
    start=time.perf_counter();deadline=start+max(0,seconds)
    full=(1<<len(nodes))-1
    active=full&~((1<<action_local)|masks[action_local])
    forced=weights[action_local]
    def members(mask):
        while mask:
            bit=mask&-mask;yield bit.bit_length()-1;mask^=bit
    cache={}
    def envelope(mask,keep=False):
        if mask in cache and not keep:return cache[mask],[]
        order=sorted(members(mask),key=lambda j:(-(masks[j]&mask).bit_count(),-weights[j],nodes[j]))
        rest,total,cover=mask,0,[]
        for i in order:
            if not rest&(1<<i):continue
            clique=[i];rest&=~(1<<i);common=masks[i]
            for j in order:
                if rest&(1<<j) and common&(1<<j):
                    clique.append(j);rest&=~(1<<j);common&=masks[j]
            total+=max(weights[j] for j in clique)
            if keep:cover.append([nodes[j] for j in clique])
        cache[mask]=total
        return total,cover
    order=sorted(members(active),key=lambda i:(-Fraction(weights[i],max(1,(masks[i]&active).bit_count())),nodes[i]))
    chosen,mask,best=1<<action_local,active,forced
    for i in order:
        if mask&(1<<i):
            chosen|=1<<i;best+=weights[i];mask&=~((1<<i)|masks[i])
    root_extra,cover=envelope(active,True);root_upper=forced+root_extra
    frontier=[(active,1<<action_local,forced)]
    expanded,best_mask,cuts=0,chosen,0
    while frontier and expanded<50000 and time.perf_counter()<deadline:
        mask,selected,value=frontier.pop();expanded+=1
        if value>best:best,best_mask=value,selected
        if not mask:continue
        if value+envelope(mask)[0]<=best:cuts+=1;continue
        i=min(members(mask),key=lambda j:(-(masks[j]&mask).bit_count(),-weights[j],nodes[j]))
        rest=mask&~(1<<i)
        frontier.append((rest,selected,value))
        frontier.append((rest&~masks[i],selected|(1<<i),value+weights[i]))
    frontier_upper=max([best]+[value+envelope(mask)[0] for mask,_,value in frontier])
    upper=min(root_upper,frontier_upper)
    selected=[nodes[i] for i in members(best_mask)]
    if sum(weights[i] for i in members(best_mask))!=best or any(masks[i]&best_mask for i in members(best_mask)):
        raise AssertionError("Conditional lower witness invalid")
    if best>upper:raise AssertionError("Valid upper enclosures cannot lie below feasible lower witness")
    return {"lower_ticks":best,"upper_ticks":upper,"exact":best==upper,"selected_indices":selected,
        "expanded_nodes":expanded,"bound_cuts":cuts,"root_upper_ticks":root_upper,
        "frontier_upper_ticks":frontier_upper,"upper_intersection_used":frontier_upper>root_upper,
        "root_clique_partition_indices":cover,
        "frontier":[{"remaining_indices":[nodes[i] for i in members(mask)],"selected_indices":[nodes[i] for i in members(sel)],
            "value_ticks":val,"upper_ticks":val+envelope(mask)[0]} for mask,sel,val in frontier],
        "termination":"exact" if best==upper else "node_budget" if expanded>=50000 else "time_budget",
        "allocated_wall_seconds":seconds,"wall_seconds":time.perf_counter()-start}


def certificate(z0,z1,query):
    start=time.perf_counter();bounds={}
    for k,(z,action) in enumerate(((z0,query["a"]),(z0,query["b"]),(z1,query["a"]),(z1,query["b"]))):
        nodes,masks,weights,loc=core.patch_arrays(z,query)
        left=max(0,core.QUERY_SECONDS-(time.perf_counter()-start))
        bounds[("left_a","left_b","right_a","right_b")[k]]=forced_bound(nodes,masks,weights,loc[action],left/(4-k))
    signs={side:core.sign_interval(bounds[side+"_a"],bounds[side+"_b"]) for side in ("left","right")}
    a,b=(signs[s]["preference"] for s in ("left","right"))
    relation=("reversal" if a!=b else "preservation") if a in ("a","b") and b in ("a","b") else (
        "tie" if a==b=="tie" else "tie_to_strict" if a=="tie" and b in ("a","b") else
        "strict_to_tie" if b=="tie" and a in ("a","b") else "unknown")
    return {"query_id":query["id"],"scope":"restricted expanded outside-fixed patch, frozen microsecond instance",
        "common_fixed_reward_ticks":sum(int(z0["weight_ticks"][i]) for i in query["fixed_indices"]),
        "bound_value_scope":"variable patch contribution; fixed reward constant cancels from delta",
        "bounds":bounds,"signs":signs,"relation":relation,"wall_seconds":time.perf_counter()-start,
        "budget_includes_patch_arrays":True,"budget_soft_overshoot_note":"final sound-bound/witness validation recorded in elapsed time"}


def source_run(source,registration,limit_anchors=None):
    out=OUTPUT/source
    out.mkdir(parents=True,exist_ok=True)
    z0=core.load(ROOT/"graphs"/source/"g0340.npz");z1=core.load(ROOT/"graphs"/source/"g1200.npz")
    left,ids=core.build_graph(z0,source,340);right,ids1=core.build_graph(z1,source,1200)
    if ids!=ids1 or left.contacts!=right.contacts or not left.edges<=right.edges:raise AssertionError("Invalid aligned intervention")
    old=json.loads((P0/source/"query_manifest.json").read_text(encoding="utf-8"))
    incumbent_record=json.loads((P0/source/"external_incumbent.json").read_text(encoding="utf-8"))
    incumbent={ids[i] for i in incumbent_record["selected_indices"]}
    if not right.feasible(incumbent) or not left.feasible(incumbent):raise AssertionError("Common incumbent not feasible")
    mp=out/"query_manifest.json"
    manifest=json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else prepare(source,left,right,ids,out,old,incumbent)
    program=core.FeatureRuleProgram.from_dict(registration["frozen_program"])
    certificates,requirements,bb,commit=[],[],[],[]
    for query in manifest["queries"]:
        if limit_anchors is not None and query["anchor_slot"]>=limit_anchors:continue
        slot=f"q{query['anchor_slot']:03d}_d{query['destroy_target']:02d}"
        if query.get("status")=="unavailable":
            certificates.append({"query_id":query["id"],"relation":"unavailable","reason":query["reason"]});continue
        path=out/"certificates"/(slot+".json")
        cert=json.loads(path.read_text(encoding="utf-8")) if path.exists() else certificate(z0,z1,query)
        core.dump(path,cert);certificates.append(cert)
        patch={ids[i] for i in query["patch_indices"]}
        for side,graph in (("left",left),("right",right)):
            pref=cert["signs"][side]["preference"]
            if pref in ("a","b"):
                good,bad=(query["a"],query["b"]) if pref=="a" else (query["b"],query["a"])
                requirements.append({"query_id":query["id"],"source":source,"side":side,
                    "boundary_hash":core.sha256((query["fixed_indices_sha256"]+query["excluded_indices_sha256"]+query["patch_indices_sha256"]).encode()).hexdigest(),
                    "certificate_file":str(path.relative_to(OUTPUT)),"certificate_sha256":core.digest(path),
                    "delta_interval":cert["signs"][side],"preferred_contact_id":ids[good],"other_contact_id":ids[bad],
                    "preferred_phi":list(core.phi(graph,ids[good],patch)),"other_phi":list(core.phi(graph,ids[bad],patch))})
            p=out/"bb_traces"/(slot+"_"+side+".json")
            rows=json.loads(p.read_text(encoding="utf-8")) if p.exists() else core.run_g3(graph,ids,query,cert,side,program)
            core.dump(p,rows);bb.extend(rows)
            p=out/"commit_traces"/(slot+"_"+side+".json")
            rows=json.loads(p.read_text(encoding="utf-8")) if p.exists() else commit_probe(graph,ids,query,cert,side,program)
            core.dump(p,rows);commit.extend(rows)
    core.dump(out/"strict_requirements.json",requirements)
    summary={"source":source,"planned_queries":len(manifest["queries"]),"executed_queries":len(certificates),
        "relations":dict(Counter(c["relation"] for c in certificates)),"strict_side_requirements":len(requirements),
        "actual_patch_sizes":[{"destroy_target":goal,"patch_cap":cap,
            "min":min((len(q["patch_indices"]) for q in manifest["queries"] if q["destroy_target"]==goal and "patch_indices" in q),default=None),
            "max":max((len(q["patch_indices"]) for q in manifest["queries"] if q["destroy_target"]==goal and "patch_indices" in q),default=None)} for goal,cap in TARGETS],
        "bb_rows":len(bb),"bb_restricted_exact":sum(r["restricted_exact"] for r in bb),"commit_rows":len(commit),
        "certificate_total_wall_seconds":sum(c.get("wall_seconds",0) for c in certificates),"model_calls":0}
    core.dump(out/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


def aggregate():
    summaries,requirements,bb,commit=[],[],[],[]
    for source in core.SOURCES:
        out=OUTPUT/source
        if not (out/"summary.json").exists():continue
        summaries.append(json.loads((out/"summary.json").read_text(encoding="utf-8")))
        requirements.extend(json.loads((out/"strict_requirements.json").read_text(encoding="utf-8")))
        for sub,destination in (("bb_traces",bb),("commit_traces",commit)):
            for p in sorted((out/sub).glob("*.json")):destination.extend(json.loads(p.read_text(encoding="utf-8")))
    quotient=core.quotient(requirements)
    core.dump(OUTPUT/"complete_demanded_quotient.json",quotient)
    bg,cg=defaultdict(list),defaultdict(list)
    for r in bb:bg[(r["query_id"],r["side"])].append(r)
    for r in commit:cg[(r["query_id"],r["side"])].append(r)
    result={"stage":"bounded G3 failure-branch interface probe","completed_sources":len(summaries),"source_summaries":summaries,
        "G2":quotient["conclusion"],"strict_requirements":len(requirements),
        "B&B":{"states":len(bg),"rows":len(bb),"all_restricted_exact":bool(bb) and all(r["restricted_exact"] for r in bb),
            "different_final_patch_value_states":sum(len({r["lower_exact"] for r in rows})>1 for rows in bg.values()),
            "different_search_nodes_states":sum(len({r["search_nodes"] for r in rows})>1 for rows in bg.values())},
        "commit":{"states":len(cg),"rows":len(commit),
            "different_pair_action_states":sum(len({r["selected_action"] for r in rows})>1 for rows in cg.values()),
            "different_unguarded_value_states":sum(len({r["local_value_exact"] for r in rows})>1 for rows in cg.values()),
            "different_positive_guard_value_states":sum(len({r["full_schedule_guarded_value_exact"] for r in rows})>1 for rows in cg.values())},
        "per_head":{},"automatic_P1_progression":False,"batch_LLM_calls":0,
        "limitations":["One label-independent neighbourhood/interface probe, not an expansion of physics or TEST screening",
            "Reference uses offline certificates only and is not a deployable method",
            "ForcedQ preference is not a guaranteed efficient B&B pivot or guaranteed better Degree completion",
            "The pairwise commit diagnostic is a newly defined restricted interface, not original V06 full-graph results",
            "Same2k B&B-node allowance does not equal same total computation; feature and search cost both recorded"]}
    for head in HEADS:
        br=[r for r in bb if r["head"]==head];cr=[r for r in commit if r["head"]==head]
        result["per_head"][head]={"B&B":{"rows":len(br),"nodes":sum(r["search_nodes"] for r in br),
            "wall_seconds":sum(r["total_wall_seconds"] for r in br),"operation_proxy":sum(r["total_operation_proxy"] for r in br)},
            "commit":{"rows":len(cr),"wall_seconds":sum(r["wall_seconds"] for r in cr),
                "operation_proxy":sum(r["operation_proxy"] for r in cr),
                "strict_choices":sum(r["choice_matches_strict_certificate"] is not None for r in cr),
                "strict_consistent":sum(r["choice_matches_strict_certificate"] is True for r in cr)}}
    core.dump(OUTPUT/"acceptance.json",result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("source_summaries","per_head","limitations")},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(parents=[_args])
    parser.add_argument("--source",choices=core.SOURCES)
    parser.add_argument("--register-only",action="store_true")
    parser.add_argument("--aggregate-only",action="store_true")
    parser.add_argument("--limit-anchors",type=int,help="Engineering pilot prefix only; formal per-source plan is always30queries")
    args=parser.parse_args()
    if args.limit_anchors is not None and not 1<=args.limit_anchors<=10:raise ValueError("limit-anchors must be1..10")
    registration=register()
    core.dump(OUTPUT/("execution_"+str(os.getpid())+".json"),{"hostname":socket.gethostname(),"platform":platform.platform(),
        "python":core.sys.version,"pid":os.getpid(),"argv":core.sys.argv,"script_sha256":core.digest(SCRIPT),
        "registered_sha256":core.digest(OUTPUT/"registration.json"),"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
    if args.register_only:return
    if not args.aggregate_only:
        for source in ((args.source,) if args.source else core.SOURCES):source_run(source,registration,args.limit_anchors)
    aggregate()


if __name__=="__main__":main()
