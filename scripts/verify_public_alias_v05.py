"""Read-only independent public-alias verification; no LLM or policy change.

Independently rebuilds base vectors, conditioned partitions, exact arithmetic,
lower witnesses and the fixed primary's neighborhood cover. Components <=32
also receive an independent memoized exact recurrence with a declared state
ceiling. Large strict-pair component upper bounds receive a separate unit
complement-colouring decision proof; other large frontiers remain unverified.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import tarfile
import time
import zipfile


def digest(raw):return sha256(raw).hexdigest()


def canonical(value):return digest(json.dumps(value,sort_keys=True,separators=(",",":")).encode())


def read_members(path,names):
    path=Path(path);raw={}
    if path.is_dir():
        for name in names:raw[name]=(path/name).read_bytes()
    else:
        with tarfile.open(path,"r:gz") as tar:
            for member in tar.getmembers():
                name=Path(member.name).name
                if member.isfile() and name in names:
                    if name in raw:raise ValueError("Ambiguous archive member: "+name)
                    raw[name]=tar.extractfile(member).read()
    if set(raw)!=set(names):raise ValueError("Missing diagnostic output members")
    return raw


def view(source):
    nodes={c["id"]:c for c in source["contacts"]}
    if len(nodes)!=len(source["contacts"]):raise ValueError("Duplicate graph vertex")
    edges={tuple(sorted(e)) for e in source["edges"]};adj={v:set() for v in nodes}
    for a,b in edges:
        if a==b or a not in nodes or b not in nodes:raise ValueError("Invalid graph edge")
        adj[a].add(b);adj[b].add(a)
    return nodes,edges,adj


def graph_digest(source):
    value={k:v for k,v in source.items() if k not in ("name","provenance")}
    return digest(json.dumps(value,sort_keys=True).encode())


def base9(source,nodes,adj,v):
    neighbors=adj[v];c=nodes[v];constraints=source.get("constraints",{})
    return {"weight":c["weight"],"duration":c["end"]-c["start"],"degree":len(neighbors),
            "conflict_weight":math.fsum(nodes[u]["weight"] for u in neighbors),
            "max_conflict_weight":max((nodes[u]["weight"] for u in neighbors),default=0),
            "compatible_weight":math.fsum(nodes[u]["weight"] for u in nodes.keys()-neighbors-{v}),
            "remaining_count":len(nodes),"station_gap":constraints.get("station_gap",constraints.get("ground_trans_time",0)),
            "satellite_gap":constraints.get("satellite_gap",constraints.get("satellite_change_time",0))}


def exact_vector(value):return tuple((k,Fraction(v)) for k,v in sorted(value.items()))


def components(adj,vertices):
    remaining=set(vertices);parts=[]
    while remaining:
        seed=min(remaining);remaining.remove(seed);found={seed};stack=[seed]
        while stack:
            nxt=adj[stack.pop()]&remaining;remaining-=nxt;found|=nxt;stack.extend(sorted(nxt))
        parts.append(tuple(sorted(found)))
    return set(parts)


class VerificationLimit(RuntimeError):pass


def exact_alpha(nodes,adj,vertices,max_states=1000000):
    """Independent exact include/exclude recurrence, without oracle calls."""
    labels=tuple(sorted(vertices));indices={v:i for i,v in enumerate(labels)}
    masks=[sum(1<<indices[u] for u in adj[v]&set(labels)) for v in labels]
    weights=[Fraction(nodes[v]["weight"]) for v in labels];states=0
    @lru_cache(None)
    def search(mask):
        nonlocal states
        states+=1
        if states>max_states:raise VerificationLimit("Independent component verification state ceiling")
        if mask==0:return Fraction(0)
        indices_active=[i for i in range(len(labels)) if mask&(1<<i)]
        chosen=max(indices_active,key=lambda i:((masks[i]&mask).bit_count(),weights[i],-i))
        rest=mask&~(1<<chosen)
        return max(search(rest),weights[chosen]+search(rest&~masks[chosen]))
    return search((1<<len(labels))-1),states


def unit_upper_decision(nodes,adj,vertices,upper,max_states=1000000,max_seconds=55):
    """Independently prove a saved unit upper bound by complement colouring.

    A proper colouring of a candidate complement subgraph bounds its clique
    size. Enumerate clique extensions with colour pruning to decide whether a
    clique of size upper+1 exists. This is distinct from the executed oracle's
    weighted binary include/exclude search. Limits produce unverified scope,
    never an asserted certificate.
    """
    if any(nodes[v]["weight"]!=1 for v in vertices):raise ValueError("Unit verifier requires unit weights")
    if Fraction(upper).denominator!=1:raise ValueError("Unit upper bound must be integral")
    labels=tuple(sorted(vertices));indices={v:i for i,v in enumerate(labels)}
    full=(1<<len(labels))-1
    compatibility=[full&~(sum(1<<indices[u] for u in adj[v]&set(labels))|(1<<indices[v])) for v in labels]
    target=int(upper)+1;states=0;deadline=time.perf_counter()+max_seconds
    def colour_order(mask):
        remaining=mask;order=[];colours=[];colour=0
        while remaining:
            colour+=1;available=remaining
            while available:
                bit=available&-available;v=bit.bit_length()-1
                order.append(v);colours.append(colour)
                remaining^=bit;available&=remaining&~compatibility[v]
        return order,colours
    def decide(mask,depth):
        nonlocal states
        states+=1
        if states>max_states or time.perf_counter()>deadline:
            raise VerificationLimit("Independent unit-colouring decision verification ceiling")
        if depth>=target:return True
        if depth+mask.bit_count()<target:return False
        order,colours=colour_order(mask)
        for index in range(len(order)-1,-1,-1):
            if depth+colours[index]<target:return False
            vertex=order[index];bit=1<<vertex
            if decide(mask&compatibility[vertex],depth+1):return True
            mask^=bit
        return False
    counterexample=decide(full,0)
    return not counterexample,states


def primary_cover(nodes,adj,root):
    order=sorted(adj[root],key=lambda v:(-nodes[v]["weight"],v));remaining=set(order);terms=[]
    for v in order:
        if v not in remaining:continue
        group=[v];remaining.remove(v)
        for u in order:
            if u in remaining and all(u in adj[q] for q in group):group.append(u);remaining.remove(u)
        terms.append(max(nodes[u]["weight"] for u in group))
    return math.fsum(terms)


def audit(path,source_zip,output,max_states,public_inputs=None):
    names=("config.json","program.json","data.json","freeze_receipt.json","execution.json","results.jsonl","complete.json")
    raw=read_members(path,names)
    obj={n:([json.loads(line) for line in data.splitlines() if line] if n.endswith(".jsonl") else json.loads(data)) for n,data in raw.items()}
    checks=Counter();warnings=Counter();issues=[];cache={};exact_states=0
    upper_cache={};upper_states=0;strict_details=[]
    def require(condition,kind,where):
        checks[kind]+=1
        if not condition:issues.append({"kind":kind,"where":where})
    freeze,config=obj["freeze_receipt.json"],obj["config.json"]
    for name,key in [("config.json","config_sha256"),("program.json","program_sha256"),("data.json","data_sha256")]:
        require(digest(raw[name])==freeze[key],"frozen_bytes",name)
    require(digest(raw["freeze_receipt.json"])==obj["execution.json"]["input_freeze_sha256"],"execution_input_freeze","execution")
    require(freeze["before_any_query"] is True and obj["data.json"]["before_oracle_queries"] is True,"prequery_freeze","freeze")
    require(obj["execution.json"]["source_sha256"]==freeze["source_sha256"],"executed_source_identity","execution")
    require(obj["execution.json"]["workers"]==config["workers"]==4 and obj["execution.json"]["state_wall_seconds"]==config["state_wall_seconds"]==120,
            "registered_workers_wall_cap","execution")
    with zipfile.ZipFile(source_zip) as z:
        manifest=json.loads(z.read("MANIFEST.json"))["files"]
        for name,expected in freeze["source_sha256"].items():
            require(digest(z.read("cipheur/"+name))==expected==manifest["cipheur/"+name],"source_snapshot_hash",name)
        for name in ("config.json","program.json","data.json","freeze_receipt.json"):
            require(z.read("experiments/discovery/public_alias_v05/"+name)==raw[name],"prepared_capsule_bytes",name)
    require(canonical(obj["program.json"])==config["frozen_program_canonical_sha256"],"unchanged_fixed_primary","program")
    require(obj["execution.json"]["new_model_calls"]==0 and obj["execution.json"]["new_programme_selection"] is False,"no_new_model_selection","execution")
    records={r["id"]:r for r in obj["data.json"]["records"]};results=obj["results.jsonl"]
    require(len(results)==len(records)==61 and len({r["id"] for r in results})==61,"assigned_state_population","results")
    if public_inputs is not None:
        require(digest(Path(public_inputs).read_bytes())==config["input_archive_sha256"],"original_public_input_archive_hash","inputs")
        original_raw=read_members(public_inputs,("data.json",))["data.json"]
        require(digest(original_raw)==obj["data.json"]["input_member_sha256"],"original_public_input_member_hash","inputs")
        originals={r["id"]:r for r in json.loads(original_raw)["public"] if r["source"]["weight_mode"]=="unit"}
        expected_ids={"source_induced32_unit:"+sid for sid in originals}
        expected_ids|={"full_public_unit:"+sid for sid,r in originals.items() if r["family"]=="DIMACS" and len(r["graph"]["contacts"])<=config["full_max_vertices"]}
        require(set(records)==expected_ids,"original_input_derived_population","inputs")
        for rid,record in records.items():
            original=originals[record["source_id"]];source=original["graph"]
            require(record["source_graph_digest"]==graph_digest(source) and record["source_metadata"]==original["source"] and record["cluster"]==original["cluster"],
                    "original_source_metadata",rid)
            if record["track"]=="full_public_unit":require(record["graph"]==source,"full_graph_exact_input_identity",rid)
            else:
                chosen=set(sorted((c["id"] for c in source["contacts"]),key=lambda v:sha256((config["subset_salt"]+"|"+record["source_id"]+"|"+v).encode()).digest())[:config["induced_vertices"]])
                expected={"name":source["name"]+"_induced"+str(config["induced_vertices"]),
                          "contacts":[c for c in source["contacts"] if c["id"] in chosen],"edges":[e for e in source["edges"] if set(e)<=chosen],
                          "constraints":source["constraints"],"provenance":{"origin":"source_derived_hash_ordered_induced_graph","source_graph_digest":graph_digest(source),
                          "source_id":record["source_id"],"subset_salt":config["subset_salt"],"subset_size":config["induced_vertices"],"selected_original_vertices":sorted(chosen)}}
                require(record["graph"]==expected,"independent_hash_subset_and_induced_edges",rid)
    summaries={}
    for result in results:
        record=records[result["id"]];where=result["id"];g=record["graph"];nodes,edges,adj=view(g)
        require(graph_digest(g)==record["graph_digest"]==result["graph_digest"],"original_graph_identity",where)
        require(all(c["weight"]==1 for c in nodes.values()),"unit_weights",where)
        require(record["fixed"]==[] and record["excluded"]==[],"initial_empty_boundary",where)
        require(len(result["rows"])==len(record["queries"])==result["planned_queries"],"assigned_query_population",where)
        vectors={v:base9(g,nodes,adj,v) for v in nodes}
        ordered=[(a,b) for a,b in sorted(edges) if exact_vector(vectors[a])==exact_vector(vectors[b])]
        require([(q["a"],q["b"]) for q in record["queries"]]==ordered[:8],"input_only_exact_query_order",where)
        require(record["eligible_alias_competing_pairs"]==len(ordered),"alias_population",where)
        require(record["query_shortfall"]==max(0,8-len(record["queries"]))==result["query_shortfall"],"retained_shortfall",where)
        require(result["oracle_budget"]["expanded_nodes"]<=config["oracle"]["max_nodes"] and result["oracle_budget"]["calls"]<=config["oracle"]["max_calls"],"completed_oracle_budget",where)
        incomplete=False
        for index,(query,row) in enumerate(zip(record["queries"],result["rows"])):
            qw=where+":"+str(index);a,b=query["a"],query["b"]
            require(all(row[k]==query[k] for k in query),"frozen_query_payload",qw)
            require(query["a_base9"]==vectors[a] and query["b_base9"]==vectors[b] and exact_vector(vectors[a])==exact_vector(vectors[b]),"independent_all_nine_alias",qw)
            if not row["query_completed"]:
                incomplete=True
                require(row["difference"] is None and row["base_representation_self_loop"] is None and result["wall_cap_interrupted"],"wall_unknown_not_fabricated",qw)
                continue
            require(not incomplete,"completed_queries_are_frozen_prefix",qw)
            d=row["difference"];pa=components(adj,nodes.keys()-adj[a]-{a});pb=components(adj,nodes.keys()-adj[b]-{b})
            require(set(map(tuple,d["cancelled_components"]))==pa&pb,"exact_common_cancellation",qw)
            expected={"a":pa-pb,"b":pb-pa};bounds={};all_exact_checked=True
            for side in ("a","b"):
                require(set(tuple(p["vertices"]) for p in d["unmatched"][side])==expected[side],"complete_unmatched_partition",qw+side)
                for component in d["unmatched"][side]:
                    vertices=tuple(component["vertices"]);bound=component["bound"];lo=Fraction(bound["lower_exact"]);hi=Fraction(bound["upper_exact"])
                    selection=bound["selected"]
                    require(len(selection)==len(set(selection)) and set(selection)<=set(vertices) and not any(u in adj[v] for i,v in enumerate(selection) for u in selection[i+1:]),"independent_lower_feasible",qw)
                    require(sum((Fraction(nodes[v]["weight"]) for v in selection),Fraction(0))==lo,"independent_lower_reward",qw)
                    require(0<=lo<=hi<=sum((Fraction(nodes[v]["weight"]) for v in vertices),Fraction(0)),"interval_order_weight_ceiling",qw)
                    require(bound["exact"]==(lo==hi),"component_exact_flag",qw)
                    key=(record["graph_digest"],vertices)
                    if len(vertices)<=32:
                        if key not in cache:
                            try:
                                value,spent=exact_alpha(nodes,adj,vertices,max_states);cache[key]=value;exact_states+=spent
                            except VerificationLimit:cache[key]=None;warnings["independent_component_state_ceiling"]+=1
                        if cache[key] is not None:require(lo<=cache[key]<=hi,"independent_small_component_optimum",qw)
                        else:all_exact_checked=False
                    else:all_exact_checked=False;warnings["large_component_upper_frontier_not_exported"]+=1
                    bounds[side,vertices]=lo,hi
            weight=Fraction(nodes[a]["weight"])-Fraction(nodes[b]["weight"])
            lower=weight+sum((bounds["a",v][0] for v in expected["a"]),Fraction(0))-sum((bounds["b",v][1] for v in expected["b"]),Fraction(0))
            upper=weight+sum((bounds["a",v][1] for v in expected["a"]),Fraction(0))-sum((bounds["b",v][0] for v in expected["b"]),Fraction(0))
            require(lower==Fraction(d["lower_exact"]) and upper==Fraction(d["upper_exact"]),"independent_cancelled_interval_arithmetic",qw)
            require(Fraction(d["lower"])<=lower<=upper<=Fraction(d["upper"]) and d["exact"]==(lower==upper),"outward_float_interval_exact_flag",qw)
            epsilon=Fraction(config["epsilon"]);preferred=a if lower>epsilon else b if upper < -epsilon else None
            status="strict" if preferred is not None else "exact_tie" if lower==upper==0 else "unknown"
            require(d["preferred"]==preferred and d["status"]==status,"independent_strict_label",qw)
            require(row["base_representation_self_loop"]==(preferred is not None),"self_loop_obstruction_scope",qw)
            if preferred is not None:
                if not all_exact_checked:
                    all_upper_checked=True
                    for side in ("a","b"):
                        for vertices in expected[side]:
                            if len(vertices)<=32 and cache.get((record["graph_digest"],vertices)) is not None:continue
                            hi=bounds[side,vertices][1];key=(record["graph_digest"],vertices,hi)
                            if key not in upper_cache:
                                try:
                                    proved,spent=unit_upper_decision(nodes,adj,vertices,hi,max_states)
                                    upper_cache[key]=proved;upper_states+=spent
                                except VerificationLimit:
                                    upper_cache[key]=None;warnings["independent_large_upper_verification_ceiling"]+=1
                            if upper_cache[key] is None:all_upper_checked=False
                            else:require(upper_cache[key],"independent_unit_colouring_upper_proof",qw)
                    all_exact_checked=all_upper_checked
                warnings["strict_independently_upper_checked" if all_exact_checked else "strict_unverified_upper_scope"]+=1
            features={v:{**vectors[v],"nc":primary_cover(nodes,adj,v)} for v in (a,b)}
            scores={v:float(nodes[v]["weight"])/max(.000001,float(nodes[v]["weight"]),features[v]["nc"]) for v in (a,b)}
            require(row["primary_features"]==features and row["primary_scores"]==scores,"independent_fixed_primary_features_scores",qw)
            require(row["primary_declared_features_separate"]==(exact_vector(features[a])!=exact_vector(features[b])),"primary_separation_not_score_fit",qw)
            require(row["primary_strict_pair_agreement"]==(None if preferred is None else scores[preferred]>scores[b if preferred==a else a]),"primary_pair_agreement_not_argmax",qw)
            if preferred is not None:
                strict_details.append({"id":where,"track":result["track"],"graph_name":g["name"],"pair":[a,b],"preferred":preferred,
                    "delta_exact":[str(lower),str(upper)],"base9":vectors[a],"primary_nc":[features[a]["nc"],features[b]["nc"]],
                    "primary_scores":scores,"declared_features_separate":row["primary_declared_features_separate"],
                    "primary_pair_agreement":row["primary_strict_pair_agreement"],"all_upper_bounds_independently_verified":all_exact_checked,
                    "unmatched_component_sizes":{s:[len(v) for v in sorted(expected[s])] for s in ("a","b")}})
    for track in sorted({r["track"] for r in results}):
        subset=[r for r in results if r["track"]==track]
        summaries[track]={"states":len(subset),"assigned_queries":sum(r["planned_queries"] for r in subset),"query_shortfall":sum(r["query_shortfall"] for r in subset),
                          "status":dict(Counter(q["difference"]["status"] if q["query_completed"] else "wall_cap_unresolved" for r in subset for q in r["rows"])),
                          "strict_self_loops":sum(q["base_representation_self_loop"] is True for r in subset for q in r["rows"]),
                          "primary_pair_agreements":sum(q["primary_strict_pair_agreement"] is True for r in subset for q in r["rows"]),
                          "interrupted_states":sum(r["wall_cap_interrupted"] for r in subset)}
    require(summaries==obj["complete.json"]["track_summary"] and obj["complete.json"]["results_sha256"]==digest(raw["results.jsonl"]),"recomputed_complete_summary","complete")
    report={"archive":str(path),"archive_sha256":digest(Path(path).read_bytes()) if Path(path).is_file() else None,
            "source_zip":str(source_zip),"source_zip_sha256":digest(Path(source_zip).read_bytes()),"original_public_input_archive_sha256":digest(Path(public_inputs).read_bytes()) if public_inputs else None,
            "audit_script_sha256":digest(Path(__file__).read_bytes()),"checks":dict(checks),"errors":issues,
            "track_summary":summaries,"verification_scope_counts":dict(warnings),"independent_exact_components":sum(v is not None for v in cache.values()),
            "independent_component_states":exact_states,"independent_per_component_state_limit":max_states,
            "independent_unit_colouring_upper_components":sum(v is True for v in upper_cache.values()),"independent_unit_colouring_upper_states":upper_states,
            "strict_pairs":strict_details,"original_public_input_derivation_checked":public_inputs is not None,
            "scope":["No query/policy/LLM rerun or programme selection. Exact component recurrence is independent verification of saved intervals.",
                     "Small components use exact recurrence; large components in strict pairs use independent unit complement-colouring upper decision verification with explicit limits.",
                     "Large unmatched-component upper frontiers for unknown/tie rows remain executed-oracle receipts, not independently exported proof trees.",
                     "Full public benchmarks and source-induced graphs retain separate populations and shared source dependence.",
                     "A strict base alias establishes this finite pointwise obstruction; fixed-primary pair agreement is not actual argmax or whole-schedule quality."]}
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"errors":len(issues),"checks":sum(checks.values()),"summary":summaries,"verification_scope_counts":dict(warnings)}),flush=True)
    if issues:raise SystemExit(1)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--archive",required=True);p.add_argument("--source-zip",required=True);p.add_argument("--out",required=True);p.add_argument("--max-independent-states",type=int,default=1000000)
    p.add_argument("--public-inputs",help="Original released public INPUT archive; reads only data.json")
    a=p.parse_args();audit(a.archive,a.source_zip,a.out,a.max_independent_states,a.public_inputs)
