"""Read-only analysis of saved heterogeneous P0 evidence, never a solver.

Reads authoritative formal JSON and graph metadata/arrays. It does not import
the frozen algorithms, alter labels, generate new preferences, or scan TEST.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction
from hashlib import sha256
import itertools
import json
from pathlib import Path
import statistics
import time
import numpy as np

SOURCES=("CP-AU-r000","CP-AP-r000","CP-AU-r001","CP-AP-r001")
CONFIGS={"A":(340,340),"W":(1200,340),"E":(340,1200),"J":(1200,1200)}
PAIRS=(("A","J"),("A","W"),("A","E"),("W","J"),("E","J"),("W","E"))
HEADS=("degree","existing_frozen","certified_reference")
FEATURES=("weight","duration","degree","conflict_weight","max_conflict_weight",
          "compatible_weight","station_gap","satellite_gap","remaining_count")
NAMESPACE="heterogeneous_station_local_base9_v1"
SCALE=1000000
EPS=1

def read(path):return json.loads(path.read_text(encoding="utf-8"))
def digest(path):return sha256(path.read_bytes()).hexdigest()
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def table(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=keys);writer.writeheader();writer.writerows(rows)
def tag(config):
    west,east=CONFIGS[config];return f"gW{west:04d}_gE{east:04d}_s0150"
def sign(lo,hi):return "a" if lo>EPS else "b" if hi< -EPS else "tie" if lo==hi==0 else "unknown"
def relation(left,right):
    if left in ("a","b") and right in ("a","b"):return "reversal" if left!=right else "preservation"
    if left==right=="tie":return "tie"
    if left=="tie" and right in ("a","b"):return "tie_to_strict"
    if right=="tie" and left in ("a","b"):return "strict_to_tie"
    return "unknown"
def distribution(values):
    values=list(values)
    if not values:return {"n":0}
    ordered=sorted(values);n=len(values)
    quantile=lambda p:float(ordered[round((n-1)*p)])
    return {"n":n,"min":float(ordered[0]),"p10":quantile(.1),"median":float(statistics.median(ordered)),
            "p90":quantile(.9),"max":float(ordered[-1]),"mean":float(sum(values)/n)}
def csr_neighbors(z,node):return {int(v) for v in z["indices"][z["indptr"][node]:z["indptr"][node+1]]}
def patch_adjacency(z,patch):return {node:csr_neighbors(z,node)&patch for node in patch}
def phi(z,node,patch,adj):
    terms={v:Fraction(float(Fraction(int(z["weight_ticks"][v]),SCALE))) for v in patch}
    neighboring=sum((terms[v] for v in adj[node]),Fraction())
    values=(Fraction(int(z["weight_ticks"][node]),SCALE),
            Fraction(int(z["end_ticks"][node])-int(z["start_ticks"][node]),SCALE),
            len(adj[node]),float(neighboring),
            max((Fraction(int(z["weight_ticks"][v]),SCALE) for v in adj[node]),default=0),
            float(sum(terms.values(),Fraction())-neighboring-terms[node]),
            Fraction(int(z["ground_gap_by_node_ticks"][node]),SCALE),
            Fraction(int(z["satellite_gap_ticks"].item()),SCALE),len(patch))
    return tuple(str(Fraction(value)) for value in values)

def audit_bound(z,query,bound,forced,adj):
    patch=set(query["patch_indices"]);chosen=set(bound["selected_indices"])
    assert len(chosen)==len(bound["selected_indices"]) and chosen<=patch and forced in chosen
    assert all(not(adj[node]&chosen) for node in chosen)
    assert sum(int(z["weight_ticks"][v]) for v in chosen)==bound["lower_ticks"]
    residual=patch-{forced}-adj[forced]
    cliques=bound["root_clique_partition_indices"]
    flat=[v for clique in cliques for v in clique]
    assert len(flat)==len(set(flat)) and set(flat)==residual
    assert all(clique and all(b in adj[a] for i,a in enumerate(clique) for b in clique[i+1:]) for clique in cliques)
    upper=int(z["weight_ticks"][forced])+sum(max(int(z["weight_ticks"][v]) for v in clique) for clique in cliques)
    assert upper==bound["root_upper_ticks"]
    assert bound["lower_ticks"]<=bound["upper_ticks"]==min(bound["root_upper_ticks"],bound["frontier_upper_ticks"])
    assert bound["exact"]==(bound["lower_ticks"]==bound["upper_ticks"])

def quotient_profile(value):
    vertices=value["vertices"];edges=value["edges"];trace=value["cycle_trace"]
    if value["directed_cycle_observed"]:
        assert trace
        for i,edge in enumerate(trace):
            assert edge["to"]==trace[(i+1)%len(trace)]["from"]
            req=edge["requirement"]
            assert req["preferred_phi"]==vertices[edge["from"]]["full9"]
            assert req["other_phi"]==vertices[edge["to"]]["full9"]
            interval=req["delta_interval"]
            assert interval["preference"] in ("a","b")
            assert sign(interval["lower_ticks"],interval["upper_ticks"])==interval["preference"]
    return {"numeric_namespace":value["numeric_namespace"],"strict_requirements":value["strict_requirements"],
        "classes":len(vertices),"occurrences":sum(len(v["occurrences"]) for v in vertices.values()),
        "multi_occurrence_classes":sum(len(v["occurrences"])>1 for v in vertices.values()),
        "self_loops":value["self_loop_count"],"directed_cycle":value["directed_cycle_observed"],
        "conclusion":value["conclusion"],"cycle_length":len(trace),"cycle_trace":trace,
        "warning":"shared complete features are connections; only a strict directed cycle is a certified obstruction"}

def analyse(args):
    root=args.input_root.resolve();ext=args.extension_root.resolve();out=args.output_root.resolve()
    acceptance=read(root/"acceptance.json");registration=read(root/"registration.json")
    if not args.allow_partial:assert acceptance["completed_sources"]==4 and acceptance["quadqueries"]==120
    assert registration["numeric_namespace"]==NAMESPACE
    inventory=[];records=[];bb=[];commits=[];requirements=[];group_index={};audit_counts=Counter()
    for source in SOURCES:
        folder=root/source
        if not(folder/"summary.json").exists():continue
        manifest=read(folder/"query_manifest.json")
        queries={q["id"]:q for q in manifest["queries"]}
        arrays={};metas={}
        for config in CONFIGS:
            path=ext/"graphs"/source/(tag(config)+".npz")
            with np.load(path,allow_pickle=False) as stored:arrays[config]={k:stored[k].copy() for k in stored.files}
            metas[config]=read(path.with_suffix(".json"))
            assert digest(path)==manifest["graph_npz_sha256"][config]
        groups=metas["A"]["antenna_group"]
        reqs=read(folder/"strict_requirements.json");requirements.extend(reqs)
        expected_phi={}
        for path in sorted((folder/"certificates").glob("*.json")):
            cert=read(path);query=queries[cert["query_id"]]
            record={"source":source,"query_id":query["id"],"patch_cap":query["patch_cap"],
                "patch_nodes":len(query["patch_indices"]),"destroy_target":query["destroy_target"],
                "certificate_path":str(path.relative_to(root)),"certificate_sha256":digest(path),
                "a_contact_id":query["a_contact_id"],"b_contact_id":query["b_contact_id"],
                "boundary":{"fixed_hash":query["fixed_indices_sha256"],"excluded_hash":query["excluded_indices_sha256"],"patch_hash":query["patch_indices_sha256"]}}
            a_group=groups[str(arrays["A"]["antenna_id"][query["a"]])]
            b_group=groups[str(arrays["A"]["antenna_id"][query["b"]])]
            record["action_group"]=a_group+"-"+b_group
            record["same_group"]=a_group==b_group;group_index[query["id"]]=record["action_group"]
            record["labels"]={c:cert["signs"][c]["preference"] for c in CONFIGS}
            record.update(all_four_strict=cert["all_four_strict"],joint_only_reversal=cert["joint_only_reversal"],
                pattern=cert["strict_pattern_AWEJ_order"],interaction=cert["interaction"],pair_relations=cert["pair_relations"],
                wall_seconds=cert["wall_seconds"],phis={},pair_aliases={})
            patch=set(query["patch_indices"])
            for config in CONFIGS:
                z=arrays[config];adj=patch_adjacency(z,patch)
                record["phis"][config]={action:list(phi(z,query[action],patch,adj)) for action in ("a","b")}
                for action in ("a","b"):
                    expected_phi[(query["id"],config,str(z["contact_id"][query[action]]))]=record["phis"][config][action]
                    bound=cert["bounds"][config+"_"+action]
                    if args.audit:audit_bound(z,query,bound,query[action],adj)
                    audit_counts["forced_spaces"]+=1;audit_counts["exact_spaces"]+=bound["exact"]
                left,right=cert["bounds"][config+"_a"],cert["bounds"][config+"_b"]
                interval=cert["signs"][config]
                assert (left["lower_ticks"]-right["upper_ticks"],left["upper_ticks"]-right["lower_ticks"])==(interval["lower_ticks"],interval["upper_ticks"])
                assert sign(interval["lower_ticks"],interval["upper_ticks"])==interval["preference"]
            intervals=cert["signs"]
            lo=intervals["J"]["lower_ticks"]-intervals["W"]["upper_ticks"]-intervals["E"]["upper_ticks"]+intervals["A"]["lower_ticks"]
            hi=intervals["J"]["upper_ticks"]-intervals["W"]["lower_ticks"]-intervals["E"]["lower_ticks"]+intervals["A"]["upper_ticks"]
            assert (lo,hi)==(cert["interaction"]["lower_ticks"],cert["interaction"]["upper_ticks"])
            for a,b in PAIRS:
                name=a+"->"+b
                assert relation(record["labels"][a],record["labels"][b])==record["pair_relations"][name]
                record["pair_aliases"][name]={action:record["phis"][a][action]==record["phis"][b][action] for action in ("a","b")}
            records.append(record)
        for req in reqs:
            assert req["numeric_namespace"]==NAMESPACE
            for role in ("preferred","other"):
                assert req[role+"_phi"]==expected_phi[(req["query_id"],req["side"],req[role+"_contact_id"])]
            audit_counts["strict_phi_matches"]+=1
        for sub,destination in (("bb_traces",bb),("commit_traces",commits)):
            for path in sorted((folder/sub).glob("*.json")):
                for row in read(path):
                    row["source"]=source;row["patch_cap"]=queries[row["query_id"]]["patch_cap"]
                    row["action_group"]=group_index[row["query_id"]];destination.append(row)
        inventory.append({"source":source,"queries":len(records)-sum(x["queries"] for x in inventory),
            "manifest_sha256":digest(folder/"query_manifest.json"),"requirements_sha256":digest(folder/"strict_requirements.json")})
    records.sort(key=lambda record:record["query_id"])
    by_query={r["query_id"]:r for r in records}
    strata=[];coverage=[];alias_inventory=[]
    for grouping in ("source","patch_cap","action_group","same_group"):
        values=sorted({str(r[grouping]) for r in records})
        for value in values:
            selected=[r for r in records if str(r[grouping])==value]
            for a,b in PAIRS:
                name=a+"->"+b;counts=Counter(r["pair_relations"][name] for r in selected)
                both_strict=sum(r["labels"][a] in ("a","b") and r["labels"][b] in ("a","b") for r in selected)
                aliases=[r for r in selected if all(r["pair_aliases"][name].values())]
                row={"stratum":grouping,"value":value,"pair":name,"total":len(selected),"both_sides_strict":both_strict,
                    **{kind:counts[kind] for kind in ("reversal","preservation","tie","tie_to_strict","strict_to_tie","unknown")},
                    "both_root_full9_alias_queries":len(aliases),
                    "aliases_with_two_strict":sum(r["labels"][a] in ("a","b") and r["labels"][b] in ("a","b") for r in aliases),
                    "alias_strict_reversals":sum(r["pair_relations"][name]=="reversal" for r in aliases)}
                strata.append(row)
            for config in CONFIGS:
                counts=Counter(r["labels"][config] for r in selected)
                coverage.append({"stratum":grouping,"value":value,"config":config,"total":len(selected),
                    **{label:counts[label] for label in ("a","b","tie","unknown")},
                    "four_strict":sum(r["all_four_strict"] for r in selected),
                    "joint_only":sum(r["joint_only_reversal"] for r in selected)})
    for record in records:
        for a,b in PAIRS:
            name=a+"->"+b
            alias_inventory.append({"query_id":record["query_id"],"source":record["source"],"patch_cap":record["patch_cap"],
                "action_group":record["action_group"],"pair":name,"a_equal_full9":record["pair_aliases"][name]["a"],
                "b_equal_full9":record["pair_aliases"][name]["b"],"relation":record["pair_relations"][name],
                "two_strict":record["labels"][a] in ("a","b") and record["labels"][b] in ("a","b")})
    deltas=[];comparison=[]
    for interface,rows in (("BB",bb),("commit",commits)):
        states=defaultdict(dict)
        for row in rows:states[(row["query_id"],row["side"])][row["head"]]=row
        for (query_id,config),heads in states.items():
            assert set(heads)==set(HEADS)
            base=heads["degree"]
            for head in HEADS[1:]:
                row=heads[head]
                fields=(("BB_quality","lower_exact"),) if interface=="BB" else (("commit_raw","full_schedule_unguarded_value_exact"),("commit_guarded","full_schedule_guarded_value_exact"))
                for metric,field in fields:
                    delta=Fraction(row[field])-Fraction(base[field])
                    deltas.append({"interface":interface,"metric":metric,"query_id":query_id,"source":row["source"],
                        "patch_cap":row["patch_cap"],"action_group":row["action_group"],"config":config,"head":head,
                        "delta_seconds":float(delta),"delta_exact":str(delta),
                        "win":delta>0,"loss":delta<0,"tie":delta==0,
                        "baseline_value_exact":base[field],"head_value_exact":row[field],
                        "head_cost":row["total_operation_proxy"] if interface=="BB" else row["operation_proxy"],
                        "baseline_cost":base["total_operation_proxy"] if interface=="BB" else base["operation_proxy"],
                        "head_wall_seconds":row["total_wall_seconds"] if interface=="BB" else row["wall_seconds"],
                        "baseline_wall_seconds":base["total_wall_seconds"] if interface=="BB" else base["wall_seconds"]})
        for grouping in ("all","source","patch_cap","action_group"):
            values=["all"] if grouping=="all" else sorted({str(r[grouping]) for r in rows})
            for value in values:
                selected=[r for r in rows if grouping=="all" or str(r[grouping])==value]
                for head in HEADS:
                    part=[r for r in selected if r["head"]==head]
                    cost_key="total_operation_proxy" if interface=="BB" else "operation_proxy"
                    time_key="total_wall_seconds" if interface=="BB" else "wall_seconds"
                    item={"interface":interface,"stratum":grouping,"value":value,"head":head,"states":len(part),
                        "total_operation_proxy":sum(r[cost_key] for r in part),"total_wall_seconds":sum(r[time_key] for r in part)}
                    if interface=="BB":item.update(exact_states=sum(r["restricted_exact"] for r in part),search_nodes=sum(r["search_nodes"] for r in part),
                        root_pruned=sum(r["root_pruned"] for r in part),pivot_count=sum(r["pivot_count"] for r in part),
                        priority_read_states=sum(r["head_called"] for r in part))
                    else:item.update(strict_fit=sum(r["choice_matches_strict_certificate"] is True for r in part),
                        strict_denominator=sum(r["choice_matches_strict_certificate"] is not None for r in part),
                        negative_raw_gain=sum(Fraction(r["unguarded_gain_exact"])<0 for r in part),guard_accepted=sum(r["positive_gain_guard_accepted"] for r in part))
                    comparison.append(item)
    paired=[]
    for grouping in ("all","source","patch_cap","action_group","config"):
        values=["all"] if grouping=="all" else sorted({str(r[grouping]) for r in deltas})
        for value in values:
            for metric in ("BB_quality","commit_raw","commit_guarded"):
                for head in HEADS[1:]:
                    selected=[r for r in deltas if r["metric"]==metric and r["head"]==head and (grouping=="all" or str(r[grouping])==value)]
                    if not selected:continue
                    ratio=sum(r["head_cost"] for r in selected)/sum(r["baseline_cost"] for r in selected)
                    paired.append({"stratum":grouping,"value":value,"metric":metric,"head":head,"states":len(selected),
                        "wins":sum(r["win"] for r in selected),"losses":sum(r["loss"] for r in selected),"ties":sum(r["tie"] for r in selected),
                        "mean_delta_seconds":sum(r["delta_seconds"] for r in selected)/len(selected),
                        "median_delta_seconds":statistics.median(r["delta_seconds"] for r in selected),"operation_ratio":ratio,
                        "wall_ratio":sum(r["head_wall_seconds"] for r in selected)/sum(r["baseline_wall_seconds"] for r in selected)})
    demanded=quotient_profile(read(root/"complete_demanded_quotient.json"))
    union=quotient_profile(read(root/"new_old_quotient_union.json"))
    choose=lambda predicate:next((r for r in records if predicate(r)),None)
    joint_case=choose(lambda r:r["all_four_strict"] and r["joint_only_reversal"])
    interaction_case=choose(lambda r:r["all_four_strict"] and r["interaction"]["sign"] in ("positive","negative") and "reversal" in r["pair_relations"].values())
    marginal_case=choose(lambda r:any(r["pair_relations"][name]=="reversal" for name in ("A->W","A->E","W->J","E->J")))
    alias_case=choose(lambda r:any(r["pair_relations"][name]=="reversal" and all(aliases.values()) for name,aliases in r["pair_aliases"].items()))
    examples={"selection":"lexicographically first query satisfying prereclared criterion; no selection by head winner",
        "joint_only_strict":joint_case,"strict_interaction_with_reversal":interaction_case,
        "marginal_reversal":marginal_case,"both_root_alias_strict_reversal":alias_case,
        "new_cycle_trace":demanded["cycle_trace"],"union_cycle_trace":union["cycle_trace"]}
    profile={"version":"hetero_formal_readonly_report_v1","numeric_namespace":NAMESPACE,
        "scope":"TRAIN developmental evidence in two source groups, 0 TEST; commonF/P/X conditional values; no newLLM",
        "input_root":str(root),"input_receipts":{"registration_sha256":digest(root/"registration.json"),"acceptance_sha256":digest(root/"acceptance.json"),
            "new_quotient_sha256":digest(root/"complete_demanded_quotient.json"),"union_quotient_sha256":digest(root/"new_old_quotient_union.json"),
            "report_script_sha256":digest(Path(__file__))},"inventory":inventory,
        "completed_sources":acceptance["completed_sources"],"planned_quadqueries":120,"observed_quadqueries":len(records),
        "unavailable_quadqueries":sum(s["unavailable"] for s in acceptance["summaries"]),
        "forced_space_coverage":dict(audit_counts),"four_side_strict":sum(r["all_four_strict"] for r in records),
        "joint_only_reversal":sum(r["joint_only_reversal"] for r in records),
        "interaction_signs":dict(Counter(r["interaction"]["sign"] for r in records)),
        "interaction_width_seconds":distribution((r["interaction"]["upper_ticks"]-r["interaction"]["lower_ticks"])/SCALE for r in records),
        "patterns":[{"pattern":"".join(p),"count":sum(r["pattern"]=="".join(p) for r in records)} for p in itertools.product("+-",repeat=4)],
        "action_group_inventory":dict(Counter(r["action_group"] for r in records)),
        "demanded_quotient":demanded,"old_new_union_quotient":union,
        "relations_by_stratum":strata,"label_coverage_by_stratum":coverage,
        "execution_costs_and_fit":comparison,"paired_execution":paired,"selected_cases":examples,
        "complexity_question":{"genuine_joint_only_preference_observed":bool(joint_case),
            "certified_information_obstruction":union["directed_cycle"],
            "LLM_advantage_tested":False,"automatic_P1":False,
            "answer_rule":"distinguish added constraint interactions, information obstruction, and deployed quality/cost; no one implies the others"},
        "audit":{"performed":args.audit,"scope":"saved lower witnesses and root clique partitions, phi equality, derived interval/relations/cycle-trace arithmetic",
            "frontier_note":"final frontier bound and search partition completeness rest on the frozen solver receipt; no repeat oracle search",
            "all_checked_assertions_passed":True},
        "satellite_600_axis":"mathematically screened out before labels; no future rerun authorized by these results",
        "generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    table(out/"source_patch_relations.csv",strata);table(out/"label_coverage.csv",coverage)
    table(out/"alias_coverage.csv",alias_inventory);table(out/"execution_deltas.csv",deltas)
    table(out/"execution_comparison.csv",paired);table(out/"execution_costs_and_fit.csv",comparison)
    dump(out/"selected_cases.json",examples);dump(out/"report_profile.json",profile)
    print(json.dumps({"completed_sources":profile["completed_sources"],"quadqueries":len(records),"new_cycle":demanded["directed_cycle"],
        "union_cycle":union["directed_cycle"],"joint_only":profile["joint_only_reversal"],"output_root":str(out)},ensure_ascii=False))

def main():
    ext=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root",type=Path,required=True,help="Authoritative downloaded formal quad_evidence directory")
    parser.add_argument("--extension-root",type=Path,default=ext)
    parser.add_argument("--output-root",type=Path,default=ext/"analysis"/"formal_report")
    parser.add_argument("--audit",action="store_true",help="One consolidated saved-evidence check; no solving")
    parser.add_argument("--allow-partial",action="store_true",help="Explicit schema-only pilot check; cannot imply 4-source formal completeness")
    args=parser.parse_args();analyse(args)

if __name__=="__main__":main()
