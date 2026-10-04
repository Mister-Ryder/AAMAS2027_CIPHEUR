"""Preregistered public-unit-graph aliases: fixed policy, no new synthesis.

Full DIMACS graphs and source-derived induced graphs are separate tracks.
Pairs are frozen before certificates. Unknowns, shortfalls and deadlines are
retained. This evidence diagnostic neither selects nor modifies a programme.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import signal
import tarfile
import time

from .graph_features import FeatureRuleProgram
from .model import Graph
from .representation import vector_key
from .relevance_synthesis_v04 import CancelledCompletionOracle

ROOT=Path(__file__).resolve().parents[1]


def file_hash(path):return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):return sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def write(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")


def base_alias_pairs(graph,max_pairs):
    base=FeatureRuleProgram("base_diagnostic",[],"weight","Fixed nine-field representation.")
    active=graph.available()
    vectors={v:base.evaluate_features(graph,v,active) for v in sorted(active)}
    pairs=[(a,b) for a,b in sorted(graph.edges) if vector_key(vectors[a])==vector_key(vectors[b])]
    return [{"a":a,"b":b,"a_base9":vectors[a],"b_base9":vectors[b]} for a,b in pairs[:max_pairs]],len(pairs)


def induced_subset(graph,source_id,size,salt):
    chosen=set(sorted(graph.nodes,key=lambda v:sha256((salt+"|"+source_id+"|"+v).encode()).digest())[:size])
    return Graph(graph.name+"_induced"+str(size),tuple(c for c in graph.contacts if c.id in chosen),
                 frozenset((a,b) for a,b in graph.edges if a in chosen and b in chosen),graph.constraints,
                 {"origin":"source_derived_hash_ordered_induced_graph","source_graph_digest":graph.digest(),
                  "source_id":source_id,"subset_salt":salt,"subset_size":size,"selected_original_vertices":sorted(chosen)})


def prepare(config_path,output):
    config=json.loads(Path(config_path).read_text(encoding="utf-8"))
    if config["version"]!="public_alias_v05_001":raise ValueError("Unknown public alias protocol")
    archive=ROOT/config["input_archive"]
    if file_hash(archive)!=config["input_archive_sha256"]:raise ValueError("Public INPUT archive bytes changed")
    program_path=ROOT/config["frozen_program"]
    if file_hash(program_path)!=config["frozen_program_bytes_sha256"]:raise ValueError("Frozen V04 programme bytes changed")
    program=FeatureRuleProgram.from_dict(json.loads(program_path.read_text(encoding="utf-8"))).to_dict()
    if canonical(program)!=config["frozen_program_canonical_sha256"]:raise ValueError("Frozen V04 AST changed")
    with tarfile.open(archive,"r:gz") as tar:
        members=[m for m in tar.getmembers() if m.isfile() and Path(m.name).name=="data.json"]
        if len(members)!=1:raise ValueError("Ambiguous public input member")
        raw=tar.extractfile(members[0]).read();data=json.loads(raw)
    records=[]
    for source in sorted(data["public"],key=lambda r:r["id"]):
        if source["source"]["weight_mode"]!="unit":continue
        original=Graph.from_dict(source["graph"])
        if any(c.weight!=1 for c in original.contacts):raise ValueError("Unit track has nonunit weights")
        cases=[]
        if source["family"]=="DIMACS" and len(original.nodes)<=config["full_max_vertices"]:
            cases.append(("full_public_unit",original))
        cases.append(("source_induced32_unit",induced_subset(original,source["id"],config["induced_vertices"],config["subset_salt"])))
        for track,graph in cases:
            queries,total=base_alias_pairs(graph,config["max_alias_pairs_per_state"])
            records.append({"id":track+":"+source["id"],"track":track,"source_id":source["id"],"cluster":source["cluster"],
                            "source_graph_digest":original.digest(),"source_metadata":source["source"],"graph":graph.to_dict(),
                            "graph_digest":graph.digest(),"fixed":[],"excluded":[],"queries":queries,
                            "eligible_alias_competing_pairs":total,"requested_query_quota":config["max_alias_pairs_per_state"],
                            "query_shortfall":max(0,config["max_alias_pairs_per_state"]-len(queries)),
                            "scope":"full benchmark" if track=="full_public_unit" else "source-derived induced graph; not full benchmark or physical scheduling"})
    counts=Counter(r["track"] for r in records)
    if counts!={"full_public_unit":13,"source_induced32_unit":48}:raise ValueError("Registered INPUT track population changed")
    output=Path(output)
    if output.exists():raise ValueError("Preserve registered input/query plan")
    output.mkdir(parents=True)
    write(output/"config.json",config);write(output/"program.json",program)
    write(output/"data.json",{"version":"public_alias_query_plan_v05_001","records":records,"before_oracle_queries":True,
                             "input_member_sha256":sha256(raw).hexdigest(),"oracle_queries_during_prepare":0,"new_model_calls":0,
                             "track_counts":dict(counts),"planned_queries":sum(len(r["queries"]) for r in records)})
    write(output/"freeze_receipt.json",{"version":"public_alias_input_freeze_v05_001","config_sha256":file_hash(output/"config.json"),
                                       "program_sha256":file_hash(output/"program.json"),"data_sha256":file_hash(output/"data.json"),
                                       "before_any_query":True,"input_archive_sha256":config["input_archive_sha256"],
                                       "source_sha256":source_receipt(),"no_programme_selection":True})
    print(json.dumps({"prepared":str(output),"tracks":dict(counts),"planned_queries":sum(len(r["queries"]) for r in records)}),flush=True)


def source_receipt():
    names=("public_alias_v05.py","graph_features.py","model.py","programs.py","representation.py","relevance_synthesis_v04.py","oracle.py","compiled.py","refinement.py")
    return {n:file_hash(Path(__file__).parent/n) for n in names}


class WallDeadline(TimeoutError):pass


def alarm_handler(signum,frame):raise WallDeadline("Registered graph-state wall cap reached")


def run_state(task):
    record,config,program=task
    started,cpu=time.perf_counter(),time.process_time()
    graph=Graph.from_dict(record["graph"]);rows=[]
    oracle=CancelledCompletionOracle(graph,record["fixed"],record["excluded"],**config["oracle"])
    parsed=FeatureRuleProgram.from_dict(program);active=graph.available()
    scores={};features={};interrupted=False
    enforce=config.get("enforce_wall_cap",True)
    previous=None
    if enforce:
        if not hasattr(signal,"SIGALRM"):raise RuntimeError("Linux SIGALRM is required for the registered execution wall cap")
        previous=signal.signal(signal.SIGALRM,alarm_handler)
        signal.setitimer(signal.ITIMER_REAL,config["state_wall_seconds"])
    try:
        for query in record["queries"]:
            for v in (query["a"],query["b"]):
                if v not in features:
                    features[v]=parsed.evaluate_features(graph,v,active)
                    scores[v]=parsed._rank(features[v])
            delta=oracle.difference(query["a"],query["b"],config["epsilon"])
            preferred=delta["preferred"]
            row={**query,"difference":delta,"primary_features":{v:features[v] for v in (query["a"],query["b"])},
                 "primary_scores":{v:scores[v] for v in (query["a"],query["b"])},"query_completed":True,
                 "base_representation_self_loop":preferred is not None,
                 "primary_declared_features_separate":vector_key(features[query["a"]])!=vector_key(features[query["b"]]),
                 "primary_strict_pair_agreement":None if preferred is None else scores[preferred]>scores[query["b"] if preferred==query["a"] else query["a"]]}
            rows.append(row)
    except WallDeadline:
        interrupted=True
    finally:
        if enforce:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
    for query in record["queries"][len(rows):]:
        rows.append({**query,"query_completed":False,"difference":None,"status":"wall_cap_unresolved",
                     "base_representation_self_loop":None,"primary_declared_features_separate":None,"primary_strict_pair_agreement":None})
    return {"id":record["id"],"track":record["track"],"source_id":record["source_id"],"cluster":record["cluster"],
            "graph_digest":record["graph_digest"],"size":len(graph.nodes),"planned_queries":len(record["queries"]),
            "query_shortfall":record["query_shortfall"],"rows":rows,"oracle_budget":oracle.receipt(),
            "wall_cap_interrupted":interrupted,"interrupted_inflight_call_not_in_completed_node_receipt":interrupted,
            "cpu_seconds":time.process_time()-cpu,"wall_seconds":time.perf_counter()-started,
            "no_model_call_no_programme_selection":True,"scope":record["scope"]}


def run(plan,output,workers):
    plan=Path(plan);receipt=json.loads((plan/"freeze_receipt.json").read_text(encoding="utf-8"))
    if not receipt["before_any_query"]:raise ValueError("Input/query freeze required")
    for name,key in [("config.json","config_sha256"),("program.json","program_sha256"),("data.json","data_sha256")]:
        if file_hash(plan/name)!=receipt[key]:raise ValueError("Frozen query artifact changed: "+name)
    if source_receipt()!=receipt["source_sha256"]:raise ValueError("Registered semantic source changed")
    config=json.loads((plan/"config.json").read_text(encoding="utf-8"));program=json.loads((plan/"program.json").read_text(encoding="utf-8"))
    data=json.loads((plan/"data.json").read_text(encoding="utf-8"))
    if workers!=config["workers"] or config["enforce_wall_cap"] is not True:raise ValueError("Registered worker/wall-cap protocol differs")
    if not hasattr(signal,"SIGALRM"):raise RuntimeError("Execute the registered wall-capped study on Linux")
    output=Path(output)
    if output.exists():raise ValueError("Preserve previous diagnostic results")
    output.mkdir(parents=True)
    for name in ("config.json","program.json","data.json","freeze_receipt.json"):(output/name).write_bytes((plan/name).read_bytes())
    write(output/"execution.json",{"source_sha256":source_receipt(),"input_freeze_sha256":file_hash(plan/"freeze_receipt.json"),
                                   "workers":workers,"state_wall_seconds":config["state_wall_seconds"],"new_model_calls":0,
                                   "new_programme_selection":False,"no_frozen_AST_change":True,"query_order_frozen_before_queries":True})
    results=[]
    with (output/"results.jsonl").open("w",encoding="utf-8") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(run_state,(r,config,program)) for r in data["records"]]
            for f in as_completed(futures):
                row=f.result();stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n");stream.flush();results.append(row)
    summary={}
    for track in sorted({r["track"] for r in results}):
        contexts=[r for r in results if r["track"]==track]
        statuses=Counter(q["difference"]["status"] if q["query_completed"] else "wall_cap_unresolved" for r in contexts for q in r["rows"])
        summary[track]={"states":len(contexts),"assigned_queries":sum(r["planned_queries"] for r in contexts),"query_shortfall":sum(r["query_shortfall"] for r in contexts),
                        "status":dict(statuses),"strict_self_loops":sum(q["base_representation_self_loop"] is True for r in contexts for q in r["rows"]),
                        "primary_pair_agreements":sum(q["primary_strict_pair_agreement"] is True for r in contexts for q in r["rows"]),
                        "interrupted_states":sum(r["wall_cap_interrupted"] for r in contexts)}
    write(output/"complete.json",{"execution_complete":True,"states":len(results),"track_summary":summary,"results_sha256":file_hash(output/"results.jsonl"),
                                 "unknowns_retained":True,"full_and_induced_never_pooled":True,"LLM_benefit_not_identified":True})
    print(json.dumps({"complete":True,"output":str(output),"summary":summary}),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="mode",required=True)
    q=s.add_parser("prepare");q.add_argument("--config",required=True);q.add_argument("--out",required=True)
    q=s.add_parser("run");q.add_argument("--plan",required=True);q.add_argument("--out",required=True);q.add_argument("--workers",type=int,default=4)
    a=p.parse_args()
    if a.mode=="prepare":prepare(a.config,a.out)
    else:run(a.plan,a.out,a.workers)
