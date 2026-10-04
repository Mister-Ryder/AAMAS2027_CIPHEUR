"""Read-only independent matched-pilot audit after authoring and TRAIN freeze.

No project semantic modules are imported. This reconstructs static authoring
slots, all declared-feature quotient gates and scalar agreements, TRAIN utility
and selection, every saved schedule's boundary/trace/feasibility/value, and
optional fresh TEST population/summary. Execution work and timeout receipts
remain executed measurements; this verifier does not remeasure their costs.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter,defaultdict,deque
from fractions import Fraction
from hashlib import sha256
import json
import keyword
import math
from pathlib import Path
import statistics
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_public_alias_v05 import read_members,view,graph_digest,exact_vector

ARMS=("witness","relations","objective")
BASE=("weight","duration","degree","conflict_weight","max_conflict_weight","compatible_weight","remaining_count","station_gap","satellite_gap")
SIGNATURES={
 "root":((),"Node"),"available":((),"NodeSet"),"neighbors":(("Node",),"NodeSet"),"singleton":(("Node",),"NodeSet"),
 "union":(("NodeSet","NodeSet"),"NodeSet"),"intersection":(("NodeSet","NodeSet"),"NodeSet"),"difference":(("NodeSet","NodeSet"),"NodeSet"),
 "induced_edges":(("NodeSet",),"EdgeSet"),"count":(("NodeSet|EdgeSet",),"Number"),"sum_weights":(("NodeSet",),"Number"),
 "max_weight":(("NodeSet",),"Number"),"clique_cover_weight":(("NodeSet",),"Number"),"greedy_independent_weight":(("NodeSet",),"Number"),
 "edge_min_weight_sum":(("EdgeSet",),"Number"),"edge_weight_product_sum":(("EdgeSet",),"Number"),"weight":(("Node",),"Number"),
 "duration":(("Node",),"Number"),"const":((),"Number"),"add":(("Number","Number"),"Number"),"sub":(("Number","Number"),"Number"),
 "mul":(("Number","Number"),"Number"),"div":(("Number","Number"),"Number"),"min":(("Number","Number"),"Number"),
 "max":(("Number","Number"),"Number"),"abs":(("Number",),"Number")}


def digest(raw):return sha256(raw).hexdigest()
def canonical(value):return digest(json.dumps(value,sort_keys=True,separators=(",",":")).encode())


def normalized_expression(source):
    count=0
    def walk(item,depth):
        nonlocal count
        count+=1
        if count>48 or depth>8 or not isinstance(item,dict) or not isinstance(item.get("op"),str):raise ValueError("Expression size/schema")
        op=item["op"]
        if op not in SIGNATURES:raise ValueError("Unknown typed operation")
        if op=="const":
            if set(item)!={"op","value"} or type(item["value"]) not in (int,float) or not math.isfinite(item["value"]) or abs(item["value"])>1e9:raise ValueError("Constant schema/range")
            return {"op":op,"value":float(item["value"])},"Number"
        if set(item)-{"op","args"} or not isinstance(item.get("args",[]),list):raise ValueError("Operation schema")
        arguments=item.get("args",[]);wanted,result=SIGNATURES[op]
        if len(arguments)!=len(wanted):raise ValueError("Operation arity")
        parsed=[walk(x,depth+1) for x in arguments]
        if any(p[1] not in w.split("|") for p,w in zip(parsed,wanted)):raise ValueError("Typed argument mismatch")
        return {"op":op,"args":[p[0] for p in parsed]},result
    normalized,kind=walk(source,1)
    if kind!="Number":raise ValueError("Feature must be numeric")
    return normalized


def rule_code(rule,names):
    if not isinstance(rule,str) or not rule.strip() or len(rule)>2000:raise ValueError("Rule string range")
    tree=ast.parse(rule,mode="eval");nodes=list(ast.walk(tree))
    if len(nodes)>256:raise ValueError("Rule AST limit")
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.IfExp,ast.Compare,ast.BoolOp,ast.Name,ast.Load,ast.Constant,ast.Call,
             ast.Add,ast.Sub,ast.Mult,ast.Div,ast.USub,ast.UAdd,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Eq,ast.NotEq,ast.And,ast.Or,ast.Not)
    for node in nodes:
        if not isinstance(node,allowed):raise ValueError("Rule AST operation")
        if isinstance(node,ast.Name) and node.id not in tuple(names)+("min","max","abs"):raise ValueError("Rule unknown variable")
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in ("min","max","abs") or node.keywords or not 1<=len(node.args)<=8 or node.func.id=="abs" and len(node.args)!=1):raise ValueError("Rule function restriction")
        if isinstance(node,ast.Constant) and (type(node.value) not in (int,float) or not math.isfinite(node.value) or abs(node.value)>1e9):raise ValueError("Rule literal restriction")
    return compile(tree,"<independent matched verifier>","eval")


def normalized_program(source):
    if not isinstance(source,dict) or set(source)!={"name","features","rule","rationale"}:raise ValueError("Candidate object schema")
    if not isinstance(source["name"],str) or not source["name"].strip() or len(source["name"])>200:raise ValueError("Name range")
    if not isinstance(source["rationale"],str) or len(source["rationale"])>20000:raise ValueError("Rationale range")
    if not isinstance(source["features"],list) or len(source["features"])>6:raise ValueError("Feature count")
    seen=set(BASE+("min","max","abs"));features=[]
    for f in source["features"]:
        if not isinstance(f,dict) or set(f)!={"name","expression"}:raise ValueError("Feature schema")
        name=f["name"]
        if not isinstance(name,str) or len(name)>80 or not name.isascii() or not name.isidentifier() or keyword.iskeyword(name) or name.startswith("__") or name in seen:raise ValueError("Feature name restriction")
        seen.add(name);features.append({"name":name,"expression":normalized_expression(f["expression"])})
    result={**source,"features":features};rule_code(result["rule"],seen)
    return result


def slots(payload,block,arm):
    schema=isinstance(payload,dict) and set(payload)=={"version","block","arm","candidates"} and payload["version"]=="matched_cold_bank_v05" and payload["block"]==block and payload["arm"]==arm and isinstance(payload["candidates"],list)
    candidates=payload["candidates"] if schema else [];invalid=not schema or len(candidates)>12;seen=set();result=[]
    for slot in range(12):
        row={"id":f"block_{block}_{arm}:{slot}","arm":arm,"block":block,"slot":slot,"program":None}
        if invalid:row["status"]="invalid_response_schema"
        elif slot>=len(candidates):row["status"]="missing_slot"
        else:
            try:
                program=normalized_program(candidates[slot]);key=canonical({k:program[k] for k in ("features","rule")})
                if key in seen:row["status"]="duplicate_deployment_AST_within_batch"
                else:
                    seen.add(key);row.update(status="static_valid",program=program,program_sha256=canonical(program),deployment_AST_sha256=key)
            except (TypeError,ValueError,KeyError,RecursionError,SyntaxError):row["status"]="invalid_candidate"
        result.append(row)
    return result


def boundary(nodes,adj,fixed,excluded):
    if len(fixed)!=len(set(fixed)) or not set(fixed)<=nodes.keys() or not set(excluded)<=nodes.keys() or set(fixed)&set(excluded) or any(adj[v]&set(fixed) for v in fixed):raise ValueError("Invalid boundary")
    blocked=set(fixed)|set(excluded)
    for v in fixed:blocked|=adj[v]
    return frozenset(nodes.keys()-blocked)


class FeatureView:
    def __init__(self,source,fixed=(),excluded=(),active=None):
        self.source=source;self.nodes,self.edges,self.adj=view(source)
        self.active=boundary(self.nodes,self.adj,fixed,excluded) if active is None else frozenset(active)
        self.cache={}
    def base(self,v):
        ns=self.adj[v]&self.active;c=self.nodes[v];constraints=self.source.get("constraints",{})
        return {"weight":c["weight"],"duration":c["end"]-c["start"],"degree":len(ns),
                "conflict_weight":math.fsum(self.nodes[u]["weight"] for u in sorted(ns)),"max_conflict_weight":max((self.nodes[u]["weight"] for u in sorted(ns)),default=0),
                "compatible_weight":math.fsum(self.nodes[u]["weight"] for u in sorted(self.active-ns-{v})),"remaining_count":len(self.active),
                "station_gap":constraints.get("station_gap",constraints.get("ground_trans_time",0)),"satellite_gap":constraints.get("satellite_gap",constraints.get("satellite_change_time",0))}
    def operation(self,e,root):
        key=(canonical(e),root)
        if key in self.cache:return self.cache[key]
        op=e["op"];args=[self.operation(a,root) for a in e.get("args",[])];nodes,adj=self.nodes,self.adj
        if op=="root":value=root
        elif op=="available":value=self.active
        elif op=="neighbors":value=frozenset(adj[args[0]]&self.active)
        elif op=="singleton":value=frozenset({args[0]})&self.active
        elif op=="union":value=args[0]|args[1]
        elif op=="intersection":value=args[0]&args[1]
        elif op=="difference":value=args[0]-args[1]
        elif op=="induced_edges":value=frozenset(e for e in self.edges if set(e)<=args[0])
        elif op=="count":value=len(args[0])
        elif op=="sum_weights":value=math.fsum(nodes[v]["weight"] for v in sorted(args[0]))
        elif op=="max_weight":value=max((nodes[v]["weight"] for v in sorted(args[0])),default=0)
        elif op in ("clique_cover_weight","greedy_independent_weight"):
            order=sorted(args[0],key=lambda v:(-nodes[v]["weight"],v));remaining=set(order);terms=[]
            for v in order:
                if v not in remaining:continue
                if op=="greedy_independent_weight":terms.append(nodes[v]["weight"]);remaining-={v}|adj[v]
                else:
                    group=[v];remaining.remove(v)
                    for u in order:
                        if u in remaining and all(u in adj[q] for q in group):group.append(u);remaining.remove(u)
                    terms.append(max(nodes[u]["weight"] for u in group))
            value=math.fsum(terms)
        elif op=="edge_min_weight_sum":value=math.fsum(min(nodes[a]["weight"],nodes[b]["weight"]) for a,b in sorted(args[0]))
        elif op=="edge_weight_product_sum":value=math.fsum(nodes[a]["weight"]*nodes[b]["weight"] for a,b in sorted(args[0]))
        elif op=="weight":value=nodes[args[0]]["weight"]
        elif op=="duration":value=nodes[args[0]]["end"]-nodes[args[0]]["start"]
        elif op=="const":value=e["value"]
        elif op=="add":value=args[0]+args[1]
        elif op=="sub":value=args[0]-args[1]
        elif op=="mul":value=args[0]*args[1]
        elif op=="div":value=args[0]/args[1]
        elif op=="min":value=min(args)
        elif op=="max":value=max(args)
        else:value=abs(args[0])
        if SIGNATURES[op][1]=="Number" and not math.isfinite(value):raise ValueError("Nonfinite feature")
        self.cache[key]=value;return value
    def features(self,program,node):
        if node not in self.active:raise ValueError("Scored node not available")
        result={**self.base(node),**{f["name"]:self.operation(f["expression"],node) for f in program["features"]}}
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in result.values()):raise ValueError("Nonfinite feature interface")
        return result


def rank(program,values):
    result=float(eval(rule_code(program["rule"],values),{"__builtins__":{}},{**values,"min":min,"max":max,"abs":abs}))
    if not math.isfinite(result) or abs(result)>1e15:raise ValueError("Score range")
    return result


def quotient(vectors,requirements):
    keys={oid:exact_vector(v) for oid,v in vectors.items()};edges=set((keys[r["preferred"]],keys[r["other"]]) for r in requirements)
    vertices=set(v for e in edges for v in e);adj={v:set() for v in vertices};incoming={v:0 for v in vertices}
    for a,b in edges:adj[a].add(b);incoming[b]+=1
    ready=deque(v for v in vertices if incoming[v]==0);visited=0
    while ready:
        v=ready.popleft();visited+=1
        for u in adj[v]:
            incoming[u]-=1
            if incoming[u]==0:ready.append(u)
    return {"contradictory":visited!=len(vertices),"quotient_nodes":len(vertices),"quotient_edges":len(edges),
            "self_loop_requirements":sum(keys[r["preferred"]]==keys[r["other"]] for r in requirements)}


def gate(program,evidence,states):
    try:
        vectors={oid:states[b["prefix"]].features(program,b["node"]) for oid,b in evidence["endpoints"].items()};scores={}
        for oid,vector in vectors.items():
            try:scores[oid]=rank(program,vector)
            except (TypeError,ValueError,ArithmeticError):scores[oid]=None
        full=quotient(vectors,evidence["requirements"])
        actual=quotient(vectors,[r for r in evidence["requirements"] if r["metadata"]["kind"]=="cancelled_actual_action"])
        agreement=Counter()
        for r in evidence["requirements"]:
            p,n=scores[r["preferred"]],scores[r["other"]]
            agreement["invalid_score" if p is None or n is None else "agree" if p>n else "tie" if p==n else "violate"]+=1
        return {"passed":not full["contradictory"],"status":"completed","full_quotient":full,"actual_only_quotient":actual,"scalar_agreement":dict(agreement)}
    except (TypeError,ValueError,ArithmeticError,RecursionError):return {"passed":False,"status":"feature_runtime_error"}


def check_schedule(row,context,require,where):
    nullable=("value","value_exact","feature_work","selected","trace")
    if not row["completed"]:
        require(all(row.get(k) is None for k in nullable),"retained_failed_assignment",where);return
    g=context["graph"];nodes,edges,adj=view(g);chosen=row["selected"];active=boundary(nodes,adj,context["fixed"],context["excluded"])
    require(len(chosen)==len(set(chosen)) and set(chosen)<=nodes.keys() and not any(adj[v]&set(chosen) for v in chosen),"independent_complete_schedule_feasibility",where)
    require(set(context["fixed"])<=set(chosen) and not set(context["excluded"])&set(chosen),"preserved_explicit_boundary",where)
    exact=sum((Fraction(nodes[v]["weight"]) for v in chosen),Fraction(0))
    require(Fraction(row["value_exact"])==exact and row["value"]==math.fsum(nodes[v]["weight"] for v in chosen),"independent_complete_schedule_reward",where)
    require(type(row["feature_work"]) is int and row["feature_work"]>=0,"nonnegative_executed_work_receipt",where)
    tracechosen=[]
    for step,t in enumerate(row["trace"]):
        require(t["selected"] in active and t["remaining_count"]==len(active) and math.isfinite(t["score"]),"trace_available_counts_scores",where+":"+str(step))
        tracechosen.append(t["selected"]);active-=adj[t["selected"]]|{t["selected"]}
    require(not active and sorted(list(context["fixed"])+tracechosen)==chosen,"complete_maximal_trace_reconstructs_schedule",where)


def independent_reference(source):
    nodes,edges,adj=view(source);remaining=set(nodes)
    order=sorted(nodes,key=lambda v:(-len(adj[v]),-nodes[v]["weight"],v));cliques=[]
    for v in order:
        if v not in remaining:continue
        group=[v];remaining.remove(v)
        for u in order:
            if u in remaining and all(u in adj[q] for q in group):group.append(u);remaining.remove(u)
        cliques.append(group)
    seen=set()
    for clique in cliques:
        if seen&set(clique) or any(u not in adj[v] for i,v in enumerate(clique) for u in clique[i+1:]):raise ValueError("Invalid independent reference clique cover")
        seen|=set(clique)
    if seen!=set(nodes):raise ValueError("Incomplete independent reference cover")
    upper=sum((max(Fraction(nodes[v]["weight"]) for v in c) for c in cliques),Fraction(0))
    selected=[]
    for v in sorted(nodes,key=lambda v:(-nodes[v]["weight"],v)):
        if not adj[v]&set(selected):selected.append(v)
    lower=sum((Fraction(nodes[v]["weight"]) for v in selected),Fraction(0))
    return lower,upper


def first_action(program,state):
    """Independent demanded-score first argmax; no policy rollout or tuning."""
    referenced={n.id for n in ast.walk(ast.parse(program["rule"],mode="eval")) if isinstance(n,ast.Name)}
    demanded={**program,"features":[f for f in program["features"] if f["name"] in referenced]}
    scores={v:rank(demanded,state.features(demanded,v)) for v in sorted(state.active)}
    choice=min(scores,key=lambda v:(-scores[v],v)) if scores else None
    return choice,None if choice is None else scores[choice]


def audit(study,training,source_zip,output,evaluation=None):
    study=Path(study)
    # Authoring metadata and completed TRAIN artifacts are required before raw
    # responses are read. This function never evaluates incomplete authoring.
    completion_raw=(study/"authoring_completion.json").read_bytes();completion=json.loads(completion_raw)
    if completion["all_authoring_completed_before_assessment"] is not True:raise ValueError("No all-cell authoring freeze")
    names=("protocol.json","candidate_bank.json","authoring_responses.json","execution.json","information_gates.jsonl","training_results.jsonl","assessments.json","frozen_programs.json","complete.json")+tuple(f"block_{b}_{a}.json" for b in range(4) for a in ARMS)
    raw=read_members(training,names)
    obj={n:([json.loads(l) for l in v.splitlines() if l] if n.endswith(".jsonl") else json.loads(v)) for n,v in raw.items() if not n.startswith("block_")}
    if obj["complete.json"]["complete"] is not True:raise ValueError("Completed TRAIN archive required")
    checks=Counter();issues=[];warnings=[]
    def require(condition,kind,where):
        checks[kind]+=1
        if not condition:issues.append({"kind":kind,"where":where})
    p_raw=(study/"protocol.json").read_bytes();protocol=json.loads(p_raw);freeze=json.loads((study/"freeze_receipt.json").read_bytes());frozen=obj["frozen_programs.json"];execution=obj["execution.json"]
    require(digest(p_raw)==freeze["protocol_sha256"]==execution["protocol_sha256"]==frozen["protocol_sha256"],"original_protocol_hash","protocol")
    require(json.loads(raw["protocol.json"])==protocol,"copied_protocol_content","train")
    for file,key in [("transport_amendment.json","transport_amendment_sha256"),("authoring_completion.json","authoring_completion_sha256"),("prior_input_inventory.json","prior_input_inventory_sha256"),("training_evidence.json","training_evidence_sha256")]:
        require(digest((study/file).read_bytes())==execution[key]==frozen[key],"training_input_identity",file)
    require(completion["transport_amendment_sha256"]==execution["transport_amendment_sha256"] and completion["same_requested_model_and_settings_all_cells"] is True,"author_transport_completion","completion")
    amendment=json.loads((study/"transport_amendment.json").read_bytes())
    require(amendment["original_protocol_sha256"]==freeze["protocol_sha256"] and amendment["decided_before_any_v05_candidate_assessment"] is True,"transport_amendment_scope","amendment")
    require(frozen["selection_split"]=="train" and frozen["test_accessed"] is False and execution["test_outcomes_read"] is False and execution["external_model_calls"]==0,"train_only_numerical_selection","execution")
    with zipfile.ZipFile(source_zip) as z:
        manifest=json.loads(z.read("MANIFEST.json"))["files"]
        for name,expected in frozen["source_sha256"].items():require(digest(z.read("cipheur/"+name))==expected==manifest["cipheur/"+name]==execution["source_sha256"][name],"frozen_execution_source",name)
        for name in ("protocol.json","freeze_receipt.json","training_evidence.json","transport_amendment.json","prior_input_inventory.json"):
            require(z.read("experiments/discovery/v05/"+name)==(study/name).read_bytes(),"original_capsule_bytes",name)
    for name,expected in protocol["packet_sha256"].items():require(digest((study/name).read_bytes())==expected,"original_packet_hash",name)
    packet_relations=None
    for b in range(4):
        for arm in ARMS:
            packet=json.loads((study/"packets"/f"block_{b}_{arm}.json").read_bytes())
            common={k:v for k,v in packet.items() if k not in ("version","block","arm","certified_relations","explicit_cycle_joins")}
            require(canonical(common)==protocol["packet_common_sha256"],"identical_common_authoring_graphs_grammar_feedback",f"block_{b}_{arm}")
            require(("certified_relations" in packet)==(arm!="objective") and ("explicit_cycle_joins" in packet)==(arm=="witness"),"registered_prompt_arm_differences",f"block_{b}_{arm}")
            if arm!="objective":
                if packet_relations is None:packet_relations=packet["certified_relations"]
                require(packet["certified_relations"]==packet_relations and len(packet_relations)==17,"identical_relational_labels_A_B",f"block_{b}_{arm}")
            if "signed near-zero guard" in packet["operation_notes"]["div"]:
                warnings.append({"cell":f"block_{b}_{arm}","kind":"common_packet_div_note_mismatch","scope":"Packet describes a signed near-zero guard; actual frozen typed feature division rejects zero and otherwise divides normally. No packet, source or candidate repair."})
    reconstructed=[]
    for b in range(4):
        for arm in ARMS:
            name=f"block_{b}_{arm}.json";response=(study/"responses"/name).read_bytes()
            require(response==raw[name] and digest(response)==completion["response_sha256"][name]==frozen["response_sha256"][name],"unmodified_exact_author_response",name)
            try:payload=json.loads(response)
            except (ValueError,UnicodeError):payload=None
            reconstructed+=slots(payload,b,arm)
    bank=obj["candidate_bank.json"];require(len(bank)==len(reconstructed)==144,"all_assigned_slots_retained","bank")
    for expected,actual in zip(reconstructed,bank):require(all(actual.get(k)==v for k,v in expected.items()),"independent_static_slot_classification",expected["id"])
    syntactic_seen={};feature_usage=[]
    for entry in bank:
        if entry["program"] is None:continue
        program=entry["program"];tree=ast.parse(program["rule"],mode="eval")
        syntactic_key=entry["block"],entry["arm"],canonical({"features":program["features"],"rule_ast":ast.dump(tree,include_attributes=False)})
        if syntactic_key in syntactic_seen:warnings.append({"kind":"AST_equivalent_rule_string_variant_retained","candidate_id":entry["id"],"prior_candidate_id":syntactic_seen[syntactic_key],"scope":"Authoritative duplicate gate hashes exact rule text. No slot status, selection or result changed."})
        else:syntactic_seen[syntactic_key]=entry["id"]
        referenced={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)};declared=[f["name"] for f in program["features"]]
        feature_usage.append({"candidate_id":entry["id"],"declared_features":declared,"rule_references":[n for n in declared if n in referenced],"unused_declared_features":[n for n in declared if n not in referenced]})
    require(digest(raw["candidate_bank.json"])==frozen["candidate_bank_sha256"],"frozen_bank_bytes","bank")
    evidence=json.loads((study/"training_evidence.json").read_bytes());contexts=obj["training_results.jsonl"]
    sourcecontexts={(c["pair_id"],c["side"]):c for c in evidence["contexts"]}
    require(len(contexts)==len(sourcecontexts)==66 and len({(c["pair_id"],c["side"]) for c in contexts})==66,"assigned_training_context_population","contexts")
    bankids={e["id"] for e in bank};gates={g["candidate_id"]:g for g in obj["information_gates.jsonl"]}
    require(set(gates)==bankids,"assigned_gate_population","gates")
    states={sid:FeatureView(s["graph"],s["fixed"],s["excluded"]) for sid,s in evidence["states"].items()};independent_gates=[]
    for index,entry in enumerate(bank):
        if entry["program"] is None:expected={"passed":False,"status":entry["status"]}
        else:expected=gate(entry["program"],evidence,states)
        saved=gates[entry["id"]]
        require(saved["passed"]==expected["passed"] and saved["status"]==expected["status"],"independent_declared_interface_gate",entry["id"])
        if expected["status"]=="completed":
            for field in ("full_quotient","actual_only_quotient"):
                require(all(saved[field][k]==v for k,v in expected[field].items()),"independent_exact_quotient",entry["id"]+field)
            require(saved["scalar_agreement"]==expected["scalar_agreement"],"independent_scalar_agreement",entry["id"])
        independent_gates.append({"candidate_id":entry["id"],**expected})
        if index%12==11:print(json.dumps({"gates_verified":index+1,"errors":len(issues)}),flush=True)
    quality_rows=defaultdict(list)
    for context in contexts:
        key=context["pair_id"],context["side"];source=sourcecontexts[key];where="|".join(key)
        require(graph_digest(source["graph"])==context["graph_digest"] and context["family"]==source["family"] and context["fixed_reward_reference"]==source["fixed_reward_reference"] and context["fixed_degree_work"]==source["fixed_degree_work"],"original_training_graph_references",where)
        require(len(context["rows"])==144 and {r["candidate_id"] for r in context["rows"]}==bankids,"assigned_training_attempt_population",where)
        for r in context["rows"]:
            check_schedule(r,source,require,where+":"+r["candidate_id"])
            quality=r["value"]/source["fixed_reward_reference"] if r["completed"] and source["fixed_reward_reference"] else 0
            work=r["feature_work"]/max(1,source["fixed_degree_work"]) if r["completed"] else 100
            quality_rows[r["candidate_id"]].append({"family":source["family"],"quality":quality,"work":work,"completed":r["completed"]})
    assessments={a["id"]:a for a in obj["assessments.json"]};require(set(assessments)==bankids,"all_assessments_retained","assessments")
    for entry in bank:
        rows=quality_rows[entry["id"]];groups=defaultdict(list)
        for r in rows:groups[r["family"]].append(r)
        quality=statistics.fmean(statistics.fmean(r["quality"] for r in group) for group in groups.values())
        work=statistics.fmean(statistics.fmean(r["work"] for r in group) for group in groups.values())
        utility=quality-protocol["selection"]["cost_penalty"]*(work-1);actual=assessments[entry["id"]]
        require(actual["quality"]==quality and actual["relative_work"]==work and actual["utility"]==utility and actual["assigned_contexts"]==66 and actual["completed_contexts"]==sum(r["completed"] for r in rows) and actual["gate_passed"]==gates[entry["id"]]["passed"],"independent_equal_family_quality_work_utility",entry["id"])
    for b in range(4):
        for arm in ARMS:
            key=f"block_{b}_{arm}";pool=[a for a in assessments.values() if a["block"]==b and a["arm"]==arm and a["gate_passed"]]
            if pool:
                best=max(pool,key=lambda a:(a["utility"],-a["slot"]))
                require(frozen["selection"][key]["selected_id"]==best["id"] and frozen["programs"][key]==best["program"] and frozen["selection"][key]["utility"]==best["utility"] and frozen["selection"][key]["eligible_slots"]==len(pool),"independent_train_selection",key)
            else:require(frozen["selection"][key]["selected_id"] is None and key not in frozen["programs"] and frozen["selection"][key]["fallback_used"] is False,"retained_empty_bank_no_fallback",key)
    require(obj["complete.json"]["attempts"]==66*144 and obj["complete.json"]["frozen_sha256"]==digest(raw["frozen_programs.json"]),"training_completion_receipt","complete")
    testsummary=None
    if evaluation is not None:
        traw=read_members(evaluation,("data.json","frozen_programs.json","execution.json","results.jsonl","complete.json"))
        tobj={n:([json.loads(l) for l in v.splitlines() if l] if n.endswith(".jsonl") else json.loads(v)) for n,v in traw.items()}
        require(traw["frozen_programs.json"]==raw["frozen_programs.json"] and tobj["execution.json"]["freeze_sha256"]==digest(raw["frozen_programs.json"]),"unchanged_test_frozen_programs","test")
        require(tobj["execution.json"]["data_sha256"]==digest(traw["data.json"]) and tobj["data.json"]["protocol"]["selection_frozen_sha256"]==digest(raw["frozen_programs.json"]),"test_input_freeze","test")
        require(tobj["execution.json"]["new_program_selection"] is False and tobj["execution.json"]["external_model_calls"]==tobj["execution.json"]["online_oracle_calls"]==0,"no_online_model_oracle_selection","test")
        pairs=tobj["data.json"]["test"];results=tobj["results.jsonl"];inputs={(p["id"],s):{"graph":p[s],"fixed":p["fixed"],"excluded":p["excluded"],"family":p["family"],"source":p["source"]} for p in pairs for s in ("left","right")}
        require(len(pairs)==108 and len(inputs)==len(results)==216 and len({(r["pair_id"],r["side"]) for r in results})==216,"assigned_fresh_context_population","test")
        prior=json.loads((study/"prior_input_inventory.json").read_bytes());oldgraphs=set(prior["graph_digests"]);oldseeds=set(prior["seeds"]);oldfingerprints=set(prior["contact_fingerprints"])
        expected_ids={f"v05_{profile}_test_{regime}_{size}_{index:04d}" for profile in protocol["test"]["profiles"] for regime in protocol["test"]["regimes"] for size in protocol["test"]["sizes"] for index in range(protocol["test"]["pairs_per_cell"])}
        require({p["id"] for p in pairs}==expected_ids,"registered_fresh_strata_all_prespecified_indices","test")
        for p in pairs:
            source=p["source"];index=int(p["id"].rsplit("_",1)[1]);expected_seed=protocol["test"]["namespace"]+2000000+source["size"]*1000+index+(100000000 if source["profile"]=="dense_long" else 0)
            require(source["seed"] not in oldseeds and source["seed"]==expected_seed,"fresh_seed_disjoint_prior_inputs",p["id"])
            require(p["left"]["contacts"]==p["right"]["contacts"] and p["fixed"]==p["excluded"]==[] and source["outcome_filtering"] is False,"paired_static_contacts_empty_boundary_unfiltered",p["id"])
            for side in ("left","right"):
                fingerprint=digest(json.dumps(sorted(p[side]["contacts"],key=lambda c:c["id"]),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
                require(fingerprint not in oldfingerprints,"fresh_contacts_disjoint_prior_inputs",p["id"]+side)
        methods=set(frozen["selection"])|{"degree"};completed=Counter();qualities=defaultdict(list)
        for result in results:
            key=result["pair_id"],result["side"];source=inputs[key];where="|".join(key)
            require(graph_digest(source["graph"])==result["graph_digest"] and result["graph_digest"] not in oldgraphs and source["family"]==result["family"] and source["source"]==result["source"],"independent_fresh_graph_identity",where)
            require(len(result["rows"])==13 and {r["method"] for r in result["rows"]}==methods,"assigned_test_methods",where)
            lo,hi=independent_reference(source["graph"])
            require(Fraction(result["reference"]["upper_exact"])==hi and Fraction(result["reference"]["lower_exact"])==lo,"independent_zero_search_reference_clique_upper",where)
            state=FeatureView(source["graph"],source["fixed"],source["excluded"])
            for row in result["rows"]:
                check_schedule(row,source,require,where+":"+row["method"]);completed[row["method"]]+=row["completed"]
                qualities[row["method"]].append(float(Fraction(row["value_exact"])/Fraction(result["reference"]["upper_exact"])) if row["completed"] else 0)
                if row["completed"]:
                    program=frozen["programs"][row["method"]] if row["method"]!="degree" else {"name":"degree","features":[],"rule":"weight/max(1,degree)","rationale":"Independent fixed reference"}
                    choice,score=first_action(program,state);first=row["trace"][0]
                    require(first["selected"]==choice and first["score"]==score,"independent_all_test_first_argmax",where+":"+row["method"])
        require(tobj["complete.json"]["assigned_runs"]==216*13 and tobj["complete.json"]["completed_runs"]==sum(completed.values()) and tobj["complete.json"]["results_sha256"]==digest(traw["results.jsonl"]),"test_completion_summary","complete")
        testsummary={"contexts":216,"completed":dict(completed),"mean_upper_bound_ratio":{m:statistics.fmean(v) for m,v in qualities.items()},"scope":"Descriptive fixed-bank results. Four authoring blocks are the generation unit; upper bound is not an optimum."}
    report={"training_archive":str(training),"training_archive_sha256":digest(Path(training).read_bytes()) if Path(training).is_file() else None,
            "evaluation_archive":str(evaluation) if evaluation else None,"evaluation_archive_sha256":digest(Path(evaluation).read_bytes()) if evaluation and Path(evaluation).is_file() else None,
            "source_zip_sha256":digest(Path(source_zip).read_bytes()),"audit_script_sha256":digest(Path(__file__).read_bytes()),"checks":dict(checks),"errors":issues,"warnings":warnings,
            "slot_status_by_arm":{a:dict(Counter(e["status"] for e in bank if e["arm"]==a)) for a in ARMS},"independent_gates":independent_gates,"declared_feature_rule_usage":feature_usage,"frozen_selection":frozen["selection"],"test_summary":testsummary,
            "scope":["All declared-feature gates and scalar-agreement counts independently evaluated on the frozen 824 requirements.","All complete saved schedules independently checked for graph feasibility, explicit boundary, trace evolution and exact reward. Every completed TEST first-action argmax is independently checked; later-step scores are not reexecuted.","TEST zero-search weighted clique upper references are independently rebuilt and checked; these are upper bounds, not proven optima.","Feature-work and CPU timeout counts remain saved executed measurements; selection arithmetic is independently reproduced.","No candidate repair, replacement, reauthoring, fresh policy selection, online model/oracle calls or new evaluation queries.","Four generation blocks cannot support a strong model-population superiority claim; requested settings are not proof of actual served model if metadata is unavailable."]}
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"errors":len(issues),"checks":sum(checks.values()),"slot_status_by_arm":report["slot_status_by_arm"],"test_summary":testsummary}),flush=True)
    if issues:raise SystemExit(1)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--study",required=True);p.add_argument("--train",required=True);p.add_argument("--source-zip",required=True);p.add_argument("--out",required=True);p.add_argument("--eval")
    args=p.parse_args();audit(args.study,args.train,args.source_zip,args.out,args.eval)
