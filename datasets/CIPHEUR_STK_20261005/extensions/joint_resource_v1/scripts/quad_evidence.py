"""Frozen four-configuration TRAIN diagnostic for joint resource changes.

No new physics, graph edits, task weights, solver algorithm, or LLM calls.
All anchors are inherited from the pre-label P0 manifests; boundaries are
constructed from the new joint-constraint feasible Degree incumbent.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import importlib.util
import itertools
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time

SCRIPT=Path(__file__).resolve()
locations=argparse.ArgumentParser(add_help=False)
locations.add_argument("--data-root",type=Path)
locations.add_argument("--cipheur-root",type=Path)
locations.add_argument("--extension-root",type=Path)
locations.add_argument("--output-root",type=Path)
locations.add_argument("--p0-output-root",type=Path)
locations.add_argument("--old-probe-output-root",type=Path)
known,_=locations.parse_known_args()
BASE=(known.data_root or SCRIPT.parents[3]).resolve()
EXT=(known.extension_root or SCRIPT.parents[1]).resolve()
OUTPUT=(known.output_root or EXT/"analysis"/"quad_evidence").resolve()
P0=(known.p0_output_root or BASE/"analysis"/"p0").resolve()
OLDPROBE=(known.old_probe_output_root or BASE/"analysis"/"patch_interface_probe").resolve()

def import_script(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

core=import_script("quad_frozen_p0",BASE/"scripts"/"p0_evidence.py")
probe=import_script("quad_frozen_probe",BASE/"scripts"/"p0_patch_interface_probe.py")
from cipheur.repair_v06 import RepairConfig, repair_schedule

CONFIGS={"A":(340,150),"G":(1200,150),"S":(340,600),"J":(1200,600)}
PAIRS=(("A","J"),("A","G"),("A","S"),("G","J"),("S","J"),("G","S"))
CAPS=((8,16),(16,64),(32,128))
QUERY_SECONDS=2.
EPSILON_TICKS=1
HEADS=("degree","existing_frozen","certified_reference")


def tag(config):
    g,s=CONFIGS[config]
    return f"g{g:04d}_s{s:04d}"


def register():
    bank=core.PROJECT/"examples"/"frozen_joint_bank_v06.json"
    frozen=json.loads(bank.read_text(encoding="utf-8"))["programs"][0]
    value={"stage":"single authorized joint-resource TRAIN extension",
        "physical_data":"same four original STK libraries, two source groups; no additional physical axis or TEST",
        "configurations_seconds":CONFIGS,"primary_pair":"A->J",
        "factorial_pairs":{"ground":"A->G","satellite":"A->S","satellite_at_strong_ground":"G->J","ground_at_strong_satellite":"S->J","secondary_cross_diagonal":"G->S"},
        "anchors":"original pre-label P0 manifests first10(a,b), never read their labels or method winners",
        "seed_destroy":"I_J intersection({a,b} union N_J(a) union N_J(b)); I_J is actual common dynamic exact weight/degree initialization atJ",
        "destroy_expansion":"gJ complete graph unweighted BFS froma; append I_J nodes bydistance thencontactID to8/16/32; seed over fixed goal or insufficient reachable incumbent retains unavailable slot",
        "patch_caps":CAPS,"patch_rule":"actual J-free region outside F=I_J minusD; retainD+a+b then original full-residual J Degree extras to16/64/128",
        "boundary":"same completecontacts,F,P,X=V minus(F unionP), and competing feasiblea/b inall4configs; A is weakest",
        "inventory":{"sources":list(core.SOURCES),"anchors_per_source":10,"quadqueries_per_source":30,"total_quadqueries":120},
        "certificate":"8 forced spaces perquadquery, shared2second wall budget, same 1tick epsilon; valid lower witnesses and min(root,frontier) clique upper enclosure",
        "certificate_scope":"restricted outside-fixed patch, frozen microsecond numeric instance, not72h global optimum",
        "strict_patterns":"all16patterns of4strict signs inA,G,S,J order; partial/tie/unavailable separately retained",
        "joint_only_reversal":"four sides all strict, A=G=S direction andJ opposite; denominator four-side-strict quadqueries, also report all planned slots",
        "interaction":"I=Delta_J-Delta_G-Delta_S+Delta_A; sound[LJ-UG-US+LA,UJ-LG-LS+UA], eachDelta=Va-Vb under sameF/P/X",
        "derived_pair_relations":"all6 pairs derived from saved4side labels, no extra solver calls; unknown cannot count as preservation",
        "numeric_namespace":"fraction_seconds_binary_fsum_base9_v1; actual ground/satellite gap fields read from NPZ ticks, including600",
        "execution":{"B&B":"unchanged actual frozen repair solve, lazy heads, same2000nodes perhead, allcosts recorded",
            "commit":"separate diagnostic pairwisecommit+common dynamicDegree completion, raw and common positivegain guard results",
            "heads":HEADS,"reference":"strict side certificate only; otherwise explicitDegree fallback; offline development probe"},
        "frozen_id":frozen["id"],"frozen_program":frozen["program"],
        "frozen_bank_sha256":core.digest(bank),
        "dependencies_sha256":{"p0_evidence.py":core.digest(BASE/"scripts"/"p0_evidence.py"),
            "p0_patch_interface_probe.py":core.digest(BASE/"scripts"/"p0_patch_interface_probe.py"),
            "repair_v06.py":core.digest(core.PROJECT/"cipheur"/"repair_v06.py")},
        "script_sha256":core.digest(SCRIPT),"model_calls":0,"new_physical_simulation_calls":0,
        "P1":"joint new+old fullbase9 quotient and gates required; no automaticLLM progression",
        "registered_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    path=OUTPUT/"registration.json"
    if path.exists():
        old=json.loads(path.read_text(encoding="utf-8"))
        candidate=json.loads(json.dumps(value))
        for k,v in candidate.items():
            if k!="registered_utc" and old[k]!=v:raise ValueError("Quad registration changed:"+k)
        return old
    core.dump(path,value)
    return json.loads(path.read_text(encoding="utf-8"))


def build_graph(z,source,config):
    g,s=CONFIGS[config]
    actualg=int(z["ground_gap_ticks"].item())
    actuals=int(z["satellite_gap_ticks"].item())
    if (actualg,actuals)!=(g*core.SCALE,s*core.SCALE):raise ValueError("Actual NPZ config does not match declaredtag")
    graph,ids=core.build_graph(z,source,g)
    graph.name=source+"-"+tag(config)
    graph.constraints.update(station_gap=Fraction(actualg,core.SCALE),satellite_gap=Fraction(actuals,core.SCALE))
    return graph,ids


def prepare(source,graphs,ids,out):
    start=time.perf_counter()
    j=graphs["J"];index={v:i for i,v in enumerate(ids)};full=set(ids)
    init=repair_schedule(j,priority="degree",seconds=None,config=RepairConfig(max_patches=0))
    incumbent=set(init["selected"])
    core.dump(out/"external_incumbent_J.json",{k:init[k] for k in ("value_exact","cpu_seconds","wall_seconds","meter","config")}|{
        "selected_indices":sorted(index[v] for v in incumbent),"configuration":"J","purpose":"common feasible outside boundary only"})
    old_path=P0/source/"query_manifest.json"
    old=json.loads(old_path.read_text(encoding="utf-8"))
    degree={v:j.nodes[v].weight/max(1,len(j.adj[v])) for v in ids}
    queries=[]
    for anchor in old["queries"][:10]:
        for goal,cap in CAPS:
            identity=f"{source}:q{anchor['slot']:03d}:d{goal:02d}"
            header={"id":identity,"source":source,"anchor_slot":anchor["slot"],"destroy_target":goal,"patch_cap":cap}
            if anchor.get("status")=="unavailable":
                queries.append(header|{"status":"unavailable","reason":"original_anchor_unavailable"});continue
            a,b=ids[anchor["a"]],ids[anchor["b"]]
            if a!=anchor["a_contact_id"] or b!=anchor["b_contact_id"]:
                raise AssertionError("Original anchor indices map to different completecontacts")
            destroy=incumbent&({a,b}|j.adj[a]|j.adj[b])
            seed=sorted(index[v] for v in destroy)
            if len(destroy)>goal:
                queries.append(header|{"status":"unavailable","reason":"seed_destroy_above_fixed_goal","seed_destroy_indices":seed});continue
            additions=[]
            for distance,v in probe.breadth_first_order(j,a,incumbent):
                if len(destroy)>=goal:break
                if v not in destroy:
                    destroy.add(v);additions.append({"node_index":index[v],"graph_distance":distance})
            if len(destroy)<goal:
                queries.append(header|{"status":"unavailable","reason":"insufficient_reachable_incumbent","seed_destroy_indices":seed});continue
            fixed=incumbent-destroy
            blocked=set(fixed)
            for v in fixed:blocked.update(j.adj[v])
            free=full-blocked;retained=destroy|{a,b}
            if not retained<=free:raise AssertionError("Seed must free both actions")
            extra=sorted(free-retained,key=lambda v:(-degree[v],v))
            patch=retained|set(extra[:cap-len(retained)])
            for config,graph in graphs.items():
                if b not in graph.adj[a] or any(graph.adj[v]&fixed for v in patch):
                    raise AssertionError("Fourconfig actions/boundaries not jointlyfeasible competing:"+config)
            fi=sorted(index[v] for v in fixed);pi=sorted(index[v] for v in patch)
            xi=sorted(set(range(len(ids)))-set(fi)-set(pi))
            queries.append(header|{"a":anchor["a"],"b":anchor["b"],"a_contact_id":a,"b_contact_id":b,
                "seed_destroy_indices":seed,"destroy_indices":sorted(index[v] for v in destroy),
                "expansion_additions":additions,"fixed_indices":fi,"patch_indices":pi,
                "full_free_region_size":len(free),"restricted":len(free)!=len(patch),
                "excluded_encoding":"universe_indices minusfixed_indices minuspatch_indices","excluded_count":len(xi),
                "excluded_indices_sha256":core.hash_indices(xi),"fixed_indices_sha256":core.hash_indices(fi),
                "patch_indices_sha256":core.hash_indices(pi),"all4actions_feasible_competing":True})
    value={"source":source,"queries":queries,"prepared_before_labels":True,
        "original_prelabel_manifest_sha256":core.digest(old_path),
        "graph_npz_sha256":{c:core.digest(EXT/"graphs"/source/(tag(c)+".npz")) for c in CONFIGS},
        "preparation_wall_seconds":time.perf_counter()-start}
    core.dump(out/"query_manifest.json",value)
    return value


def pair_relation(left,right):
    if left in ("a","b") and right in ("a","b"):return "reversal" if left!=right else "preservation"
    if left==right=="tie":return "tie"
    if left=="tie" and right in ("a","b"):return "tie_to_strict"
    if right=="tie" and left in ("a","b"):return "strict_to_tie"
    return "unknown"


def certificate(arrays,query):
    start=time.perf_counter();bounds={};spaces=[(c,k) for c in CONFIGS for k in ("a","b")]
    for i,(config,action) in enumerate(spaces):
        nodes,masks,weights,loc=core.patch_arrays(arrays[config],query)
        left=max(0,QUERY_SECONDS-(time.perf_counter()-start))
        bounds[config+"_"+action]=probe.forced_bound(nodes,masks,weights,loc[query[action]],left/(len(spaces)-i))
    signs={c:core.sign_interval(bounds[c+"_a"],bounds[c+"_b"]) for c in CONFIGS}
    labels={c:signs[c]["preference"] for c in CONFIGS}
    relations={a+"->"+b:pair_relation(labels[a],labels[b]) for a,b in PAIRS}
    strict4=all(v in ("a","b") for v in labels.values())
    pattern="".join("+" if labels[c]=="a" else "-" for c in CONFIGS) if strict4 else None
    ilo=signs["J"]["lower_ticks"]-signs["G"]["upper_ticks"]-signs["S"]["upper_ticks"]+signs["A"]["lower_ticks"]
    ihi=signs["J"]["upper_ticks"]-signs["G"]["lower_ticks"]-signs["S"]["lower_ticks"]+signs["A"]["upper_ticks"]
    isign="positive" if ilo>EPSILON_TICKS else "negative" if ihi< -EPSILON_TICKS else "tie" if ilo==ihi==0 else "unknown"
    return {"query_id":query["id"],"scope":"same restrictedP/F/X underfourresource configurations",
        "bounds":bounds,"signs":signs,"pair_relations":relations,
        "all_four_strict":strict4,"strict_pattern_AG_SJ_order":pattern,
        "pattern_config_order":["A","G","S","J"],
        "joint_only_reversal":strict4 and labels["A"]==labels["G"]==labels["S"] and labels["J"]!=labels["A"],
        "interaction":{"lower_ticks":ilo,"upper_ticks":ihi,"sign":isign,"epsilon_ticks":EPSILON_TICKS,
            "formula":"DeltaJ-DeltaG-DeltaS+DeltaA; [LJ-UG-US+LA,UJ-LG-LS+UA]"},
        "common_fixed_reward_ticks":sum(int(arrays["A"]["weight_ticks"][i]) for i in query["fixed_indices"]),
        "bound_value_scope":"variable patch contribution; same fixed reward cancels fromeveryDelta",
        "wall_seconds":time.perf_counter()-start,"declared_wall_seconds":QUERY_SECONDS,
        "budget_soft_overshoot_note":"final legitimate bound/witness validation is included inactualtime"}


def process_source(source,registration,limit_anchors=None):
    out=OUTPUT/source;out.mkdir(parents=True,exist_ok=True)
    arrays={c:core.load(EXT/"graphs"/source/(tag(c)+".npz")) for c in CONFIGS}
    graphs={};ids=None
    for c in CONFIGS:
        graph,these=build_graph(arrays[c],source,c);graphs[c]=graph
        if ids is None:ids=these
        if these!=ids or graph.contacts!=graphs["A"].contacts:raise AssertionError("Different quadcontacts")
    if not(graphs["A"].edges<=graphs["G"].edges and graphs["A"].edges<=graphs["S"].edges and
            graphs["J"].edges==graphs["G"].edges|graphs["S"].edges):raise AssertionError("Invalid resourcecrossing")
    path=out/"query_manifest.json"
    manifest=json.loads(path.read_text(encoding="utf-8")) if path.exists() else prepare(source,graphs,ids,out)
    program=core.FeatureRuleProgram.from_dict(registration["frozen_program"])
    certificates,requirements,bb,commits=[],[],[],[]
    for query in manifest["queries"]:
        if limit_anchors is not None and query["anchor_slot"]>=limit_anchors:continue
        identity=f"q{query['anchor_slot']:03d}_d{query['destroy_target']:02d}"
        if query.get("status")=="unavailable":
            certificates.append({"query_id":query["id"],"status":"unavailable","reason":query["reason"]});continue
        cp=out/"certificates"/(identity+".json")
        cert=json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else certificate(arrays,query)
        core.dump(cp,cert);certificates.append(cert)
        patch={ids[i] for i in query["patch_indices"]}
        for config,graph in graphs.items():
            pref=cert["signs"][config]["preference"]
            if pref in ("a","b"):
                good,bad=(query["a"],query["b"]) if pref=="a" else (query["b"],query["a"])
                requirements.append({"query_id":query["id"],"source":source,"side":config,
                    "boundary_hash":core.sha256((query["fixed_indices_sha256"]+query["excluded_indices_sha256"]+query["patch_indices_sha256"]).encode()).hexdigest(),
                    "certificate_file":str(cp.relative_to(OUTPUT)),"certificate_sha256":core.digest(cp),
                    "delta_interval":cert["signs"][config],"preferred_contact_id":ids[good],"other_contact_id":ids[bad],
                    "preferred_phi":list(core.phi(graph,ids[good],patch)),"other_phi":list(core.phi(graph,ids[bad],patch))})
            tp=out/"bb_traces"/(identity+"_"+config+".json")
            rows=json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else core.run_g3(graph,ids,query,cert,config,program)
            core.dump(tp,rows);bb.extend(rows)
            tp=out/"commit_traces"/(identity+"_"+config+".json")
            rows=json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else probe.commit_probe(graph,ids,query,cert,config,program)
            core.dump(tp,rows);commits.extend(rows)
    core.dump(out/"strict_requirements.json",requirements)
    available=[c for c in certificates if c.get("status")!="unavailable"]
    summary={"source":source,"planned_quadqueries":30,"executed_quadqueries":len(certificates),
        "unavailable":len(certificates)-len(available),"strict_side_requirements":len(requirements),
        "four_side_strict":sum(c["all_four_strict"] for c in available),
        "joint_only_reversal":sum(c["joint_only_reversal"] for c in available),
        "relations":{a+"->"+b:dict(Counter(c["pair_relations"][a+"->"+b] for c in available)) for a,b in PAIRS},
        "interaction":dict(Counter(c["interaction"]["sign"] for c in available)),
        "bb_rows":len(bb),"bb_exact_rows":sum(r["restricted_exact"] for r in bb),"commit_rows":len(commits),
        "certificate_wall_seconds":sum(c["wall_seconds"] for c in available),"model_calls":0}
    core.dump(out/"summary.json",summary);print(json.dumps(summary,ensure_ascii=False),flush=True)


def aggregate():
    summaries,requirements,certificates,bb,commits=[],[],[],[],[]
    for source in core.SOURCES:
        out=OUTPUT/source
        if not(out/"summary.json").exists():continue
        summaries.append(json.loads((out/"summary.json").read_text(encoding="utf-8")))
        requirements.extend(json.loads((out/"strict_requirements.json").read_text(encoding="utf-8")))
        certificates.extend(json.loads(p.read_text(encoding="utf-8")) for p in sorted((out/"certificates").glob("*.json")))
        for sub,destination in (("bb_traces",bb),("commit_traces",commits)):
            for p in sorted((out/sub).glob("*.json")):destination.extend(json.loads(p.read_text(encoding="utf-8")))
    q=core.quotient(requirements);core.dump(OUTPUT/"complete_demanded_quotient.json",q)
    patterns=Counter(c["strict_pattern_AG_SJ_order"] for c in certificates if c["all_four_strict"])
    pattern_table=[{"pattern":"".join(p),"count":patterns["".join(p)],"joint_only_reversal":"".join(p) in ("+++-","---+")} for p in itertools.product("+-",repeat=4)]
    core.dump(OUTPUT/"all16_strict_pattern_table.json",{"config_order":["A","G","S","J"],"patterns":pattern_table,
        "four_side_strict_denominator":sum(patterns.values()),"completed_quadquery_slots":sum(s["executed_quadqueries"] for s in summaries),
        "partial_or_tie_quadqueries":sum(not c["all_four_strict"] for c in certificates),
        "unavailable_quadqueries":sum(s["unavailable"] for s in summaries)})
    combined=[];inventory=[]
    for stage,folder in (("old_p0",P0),("old_patch_probe",OLDPROBE)):
        for source in core.SOURCES:
            p=folder/source/"strict_requirements.json"
            if not p.exists():raise ValueError("Old formalrequirement source missing:"+str(p))
            for r in json.loads(p.read_text(encoding="utf-8")):
                r["evidence_stage"]=stage;r["original_requirement_file_sha256"]=core.digest(p);combined.append(r)
            inventory.append({"stage":stage,"source":source,"file_sha256":core.digest(p)})
    for r in requirements:r["evidence_stage"]="joint_resource_quad";combined.append(r)
    union=core.quotient(combined);core.dump(OUTPUT/"new_old_quotient_union.json",union)
    bg,cg=defaultdict(list),defaultdict(list)
    for r in bb:bg[(r["query_id"],r["side"])].append(r)
    for r in commits:cg[(r["query_id"],r["side"])].append(r)
    execution={"B&B":{"states":len(bg),"rows":len(bb),"exact_rows":sum(r["restricted_exact"] for r in bb),
        "different_values_states":sum(len({r["lower_exact"] for r in rows})>1 for rows in bg.values())},
        "commit":{"states":len(cg),"rows":len(commits),
            "different_pair_choices_states":sum(len({r["selected_action"] for r in rows})>1 for rows in cg.values()),
            "different_raw_values_states":sum(len({r["local_value_exact"] for r in rows})>1 for rows in cg.values()),
            "different_guarded_values_states":sum(len({r["full_schedule_guarded_value_exact"] for r in rows})>1 for rows in cg.values())},"per_head":{}}
    for head in HEADS:
        br=[r for r in bb if r["head"]==head];cr=[r for r in commits if r["head"]==head]
        execution["per_head"][head]={"B&B":{"rows":len(br),"search_nodes":sum(r["search_nodes"] for r in br),
            "wall_seconds":sum(r["total_wall_seconds"] for r in br),"operation_proxy":sum(r["total_operation_proxy"] for r in br)},
            "commit":{"rows":len(cr),"wall_seconds":sum(r["wall_seconds"] for r in cr),"operation_proxy":sum(r["operation_proxy"] for r in cr),
                "negative_raw_gain_states":sum(Fraction(r["unguarded_gain_exact"])<0 for r in cr),
                "strict_choices":sum(r["choice_matches_strict_certificate"] is not None for r in cr),
                "strict_consistent":sum(r["choice_matches_strict_certificate"] is True for r in cr)}}
    core.dump(OUTPUT/"execution_summary.json",execution)
    result={"completed_sources":len(summaries),"planned_sources":4,"summaries":summaries,
        "quadqueries":sum(s["executed_quadqueries"] for s in summaries),"planned_quadqueries":120,
        "new_strict_requirements":len(requirements),"new_G2":q["conclusion"],
        "joint_only_reversals":sum(c["joint_only_reversal"] for c in certificates),
        "four_strict_denominator":sum(c["all_four_strict"] for c in certificates),
        "relations":{a+"->"+b:dict(Counter(c["pair_relations"][a+"->"+b] for c in certificates)) for a,b in PAIRS},
        "interaction":dict(Counter(c["interaction"]["sign"] for c in certificates)),
        "combined_old_new_strict_requirements":len(combined),"combined_quotient_classes":len(union["vertices"]),
        "combined_cycle":union["directed_cycle_observed"],"combined_G2":union["conclusion"],
        "old_requirement_inventory":inventory,"source_groups":["r000","r001"],"TEST_read":0,
        "execution_summary":execution,"automatic_P1_progression":False,"model_calls":0}
    core.dump(OUTPUT/"acceptance.json",result);print(json.dumps({k:v for k,v in result.items() if k not in ("summaries","old_requirement_inventory")},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(parents=[locations])
    parser.add_argument("--source",choices=core.SOURCES)
    parser.add_argument("--register-only",action="store_true")
    parser.add_argument("--aggregate-only",action="store_true")
    parser.add_argument("--no-aggregate",action="store_true",help="Parallelworker: onlysource outputs; root runs one aggregate-only afterallworkerscomplete")
    parser.add_argument("--limit-anchors",type=int,help="engineeringpilot prefix only; formal remains10anchors/source")
    args=parser.parse_args()
    if args.limit_anchors is not None and not 1<=args.limit_anchors<=10:raise ValueError("limit-anchors1..10")
    registration=register()
    core.dump(OUTPUT/("execution_"+str(os.getpid())+".json"),{"hostname":socket.gethostname(),"platform":platform.platform(),
        "python":sys.version,"pid":os.getpid(),"argv":sys.argv,"script_sha256":core.digest(SCRIPT),
        "registration_sha256":core.digest(OUTPUT/"registration.json"),"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
    if args.register_only:return
    if not args.aggregate_only:
        for source in ((args.source,) if args.source else core.SOURCES):process_source(source,registration,args.limit_anchors)
    if not args.no_aggregate:aggregate()


if __name__=="__main__":main()
