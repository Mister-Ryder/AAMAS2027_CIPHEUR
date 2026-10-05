"""Complete-graph anytime MWIS scheduling with genuinely committing heads.

No offline value oracle or model provider is imported. Head construction and
repair proposals select their own actions irrevocably; common completion only
fills the remaining legal domain. Saved incumbent guards never erase raw loss.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import heapq
import itertools
import json
import math
from pathlib import Path
import random
import time
import numpy as np

from cipheur.compiled import CompiledEvaluator, _CompiledSnapshot, _LazyScoreLocals
from cipheur.graph_features import FeatureRuleProgram, _BASE_EXPRESSIONS, _charge
from cipheur.model import Contact, Graph
from cipheur.repair_v06 import _Meter, _Stopped
from cipheur.score_heap_v04 import score_locality

SCALE=1000000
NAMESPACE="heterogeneous_station_local_base9_full_schedule_v1"

def value_ticks(graph,nodes):return sum(graph.provenance["weight_ticks"][v] for v in nodes)
def value_exact(graph,nodes):return str(Fraction(value_ticks(graph,nodes),SCALE))
def load_graph(npz_path,metadata_path,meter):
    started=time.process_time()
    with np.load(npz_path,allow_pickle=False) as stored:z={k:stored[k].copy() for k in stored.files}
    meta=json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    ids=[str(v) for v in z["contact_id"]]
    weights=[int(v) for v in z["weight_ticks"]]
    if "ground_gap_by_node_ticks" in z:node_gaps=[int(v) for v in z["ground_gap_by_node_ticks"]]
    else:node_gaps=[int(z["ground_gap_ticks"].item())]*len(ids)
    antenna_gaps={}
    for i,antenna in enumerate(z["antenna_id"]):
        antenna=str(antenna);gap=Fraction(node_gaps[i],SCALE)
        if gap.denominator!=1:raise ValueError("Contract requires integral gap seconds")
        if antenna in antenna_gaps and antenna_gaps[antenna]!=int(gap):raise ValueError("Inconsistent antenna gaps")
        antenna_gaps[antenna]=int(gap)
    if "station_gap_by_antenna_seconds" in meta and antenna_gaps!=meta["station_gap_by_antenna_seconds"]:
        raise ValueError("Station metadata does not match every root field")
    satellite_gap=Fraction(int(z["satellite_gap_ticks"].item()),SCALE)
    if satellite_gap.denominator!=1:raise ValueError("Contract requires integral satellite gap seconds")
    contacts=tuple(Contact(ids[i],Fraction(weights[i],SCALE),str(z["satellite_id"][i]),str(z["antenna_id"][i]),
        Fraction(int(z["start_ticks"][i]),SCALE),Fraction(int(z["end_ticks"][i]),SCALE)) for i in range(len(ids)))
    graph=Graph(str(meta.get("source_id",z["source_id"].item()))+":"+str(meta.get("config_id",Path(npz_path).stem)),
        contacts,frozenset((ids[int(a)],ids[int(b)]) for a,b in zip(z["edge_u"],z["edge_v"])),
        {"station_gap_mode":"per_antenna","station_gap_by_antenna":antenna_gaps,"satellite_gap":int(satellite_gap)},
        {"weight_ticks":dict(zip(ids,weights)),"metadata":meta,"numeric_namespace":NAMESPACE})
    # Bulk input work/time is charged; a mandatory seed can still be retained if
    # input parsing alone exceeded the target, with explicit overshoot recorded.
    meter.sealed=True;meter.tick("input_array_and_graph_materialization",len(ids)+2*len(graph.edges));meter.sealed=False
    return graph,{"input_cpu_seconds":time.process_time()-started,"nodes":len(ids),"edges":len(graph.edges)}

class StationLocalEvaluator(CompiledEvaluator):
    def score(self,node):
        if node not in self.active:raise ValueError("Scored root is not active")
        if self._snapshot is None:
            before=self.meter["feature_work"]
            _charge(self.meter,"snapshot_materialize",len(self.active));self._snapshot=_CompiledSnapshot(self)
            self.meter["query_work"]+=self.meter["feature_work"]-before
        expressions={**_BASE_EXPRESSIONS,**dict(self.program._expressions)}
        elapsed=[0.]
        def getter(name):
            before=self.meter["feature_work"];start=time.perf_counter()
            try:
                _charge(self.meter,"scorer_input_lookup")
                if name in expressions:return self._snapshot.evaluate(expressions[name],node)
                if name=="station_gap":
                    _charge(self.meter,"constraint_read",2);_charge(self.meter,"station_local_root_field_read")
                    antenna=self.graph.nodes[node].station;_charge(self.meter,"station_local_mapping_read")
                    return self.graph.constraints["station_gap_by_antenna"][antenna]
                if name=="satellite_gap":_charge(self.meter,"constraint_read",2);return self.graph.constraints["satellite_gap"]
                raise ValueError("Unknown score input:"+name)
            finally:
                self.meter["query_work"]+=self.meter["feature_work"]-before
                duration=time.perf_counter()-start;self.meter["feature_seconds"]+=duration;elapsed[0]+=duration
        started=time.perf_counter()
        try:result=float(eval(self.program.code,{"__builtins__":{}},_LazyScoreLocals(getter)))
        finally:self.meter["scoring_seconds"]+=max(0.,time.perf_counter()-started-elapsed[0])
        if not math.isfinite(result) or abs(result)>1e15:raise ValueError("Nonfinite or unbounded programme score")
        return result

def static_completion(graph,domain,initial,meter):
    """Complete a preserved head prefix, never remove/reorder its choices."""
    chosen=set(initial);domain=set(domain)
    if not graph.feasible(chosen) or not chosen<=domain:raise AssertionError("Invalid preserved prefix")
    blocked=set(chosen)
    for node in chosen:blocked.update(graph.adj[node])
    weights=graph.provenance["weight_ticks"]
    order=sorted(domain-blocked,key=lambda node:(-Fraction(weights[node],1+len(graph.adj[node]&domain)),node))
    meter.tick("common_static_degree_completion",len(domain)+sum(len(graph.adj[node]) for node in domain))
    for node in order:
        if node not in blocked:chosen.add(node);blocked.update(graph.adj[node])
    return chosen

def committing_greedy(graph,program,domain,meter,rng,rcl=1):
    """Exact dynamic priority policy; incomplete prefix remains externally visible."""
    chosen=set();trace=[];stats=defaultdict(int);status="complete";error=None
    locality=score_locality(program);evaluator=None;heap=[];versions={}
    def refresh(nodes):
        for node in sorted(nodes):
            meter.tick("head_score_call");stats["score_evaluations"]+=1
            score=evaluator.score(node);version=versions.get(node,0)+1;versions[node]=version
            meter.tick("head_heap_push");heapq.heappush(heap,(-score,node,version))
    try:
        evaluator=StationLocalEvaluator(graph,program,domain,meter,score_slice=True)
        if locality["eligible_local"]:refresh(evaluator.active)
        while evaluator.active:
            meter.check()
            if not locality["eligible_local"]:
                heap=[];stats["global_rescores"]+=1;refresh(evaluator.active)
            options=[]
            while heap and len(options)<rcl:
                meter.tick("head_heap_pop");entry=heapq.heappop(heap)
                if entry[1] in evaluator.active and versions.get(entry[1])==entry[2]:options.append(entry)
            if not options:raise AssertionError("No score available for active root")
            entry=options[rng.randrange(len(options))] if rcl>1 else options[0]
            for alternative in options:
                if alternative is not entry:heapq.heappush(heap,alternative);meter.tick("head_heap_push")
            score,node,_=entry;chosen.add(node);stats["head_commits"]+=1
            trace.append({"node":node,"score":-score,"active_count":len(evaluator.active)})
            removed={node}|evaluator.neighbors[node];dirty=set()
            if locality["eligible_local"] and not locality["static_scores"]:
                for deleted in removed:
                    dirty.update(evaluator.neighbors[deleted]);meter.tick("head_dirty_frontier",len(evaluator.neighbors[deleted]))
                dirty-=removed
            evaluator.remove({node}|graph.adj[node])
            for deleted in removed:versions.pop(deleted,None)
            if locality["eligible_local"]:refresh(dirty)
    except _Stopped as failure:status="deadline";error=str(failure)
    except Exception as failure:status="programme_error";error=type(failure).__name__+":"+str(failure)
    return {"prefix":chosen,"trace":trace,"stats":dict(stats),"status":status,"error":error,
        "locality":locality,"scope":"full_active" if len(domain)==len(graph.nodes) else "repair_active"}

def shared_swap(graph,selected,meter,max_rounds):
    """Classic improving one-to-one/one-to-two swaps, no oracle or head labels."""
    current=set(selected);weights=graph.provenance["weight_ticks"];steps=[]
    try:
        for iteration in range(max_rounds):
            groups=defaultdict(list);best=None
            for node in sorted(graph.nodes.keys()-current):
                meter.tick("swap_blocker_scan",len(graph.adj[node])+1)
                blockers=graph.adj[node]&current
                gain=weights[node]-sum(weights[v] for v in blockers)
                if gain>0:
                    proposal=(gain,(node,),tuple(sorted(blockers)))
                    if best is None or proposal>best:best=proposal
                if len(blockers)==1:groups[next(iter(blockers))].append(node)
            for removed,pool in sorted(groups.items()):
                for a,b in itertools.combinations(pool,2):
                    meter.tick("swap_pair_edge_test")
                    if b in graph.adj[a]:continue
                    gain=weights[a]+weights[b]-weights[removed]
                    if gain>0:
                        proposal=(gain,(a,b),(removed,))
                        if best is None or proposal>best:best=proposal
            if best is None:break
            gain,added,removed=best;current.difference_update(removed);current.update(added)
            steps.append({"gain_ticks":gain,"added":added,"removed":removed})
    except _Stopped:pass
    return current,steps

def repair_domain(graph,selected,destroy,cap,meter):
    neighborhood=set(destroy)
    for node in destroy:neighborhood.update(graph.adj[node]);meter.tick("repair_neighborhood_scan",len(graph.adj[node]))
    outside=selected-destroy
    eligible=[]
    for node in sorted(neighborhood-destroy):
        meter.tick("repair_external_boundary_check",len(graph.adj[node]))
        if not(graph.adj[node]&outside):eligible.append(node)
    weights=graph.provenance["weight_ticks"]
    eligible.sort(key=lambda node:(-Fraction(weights[node],1+len(graph.adj[node])),node))
    return set(destroy)|set(eligible[:max(0,cap-len(destroy))]),outside,len(destroy)+len(eligible)

def cp_sat(graph,seed,meter,random_seed):
    """Full integer graph model; input/model cost precedes single-worker solve."""
    started=time.process_time();details={"worker_count":1,"online_oracle_calls":0}
    try:
        from ortools.sat.python import cp_model
        model=cp_model.CpModel();nodes=sorted(graph.nodes)
        variables={node:model.new_bool_var("x"+str(i)) for i,node in enumerate(nodes)}
        meter.tick("cp_sat_bool_variables",len(nodes))
        for a,b in sorted(graph.edges):
            model.add(variables[a]+variables[b]<=1);meter.tick("cp_sat_edge_constraint")
        weights=graph.provenance["weight_ticks"]
        if sum(weights.values())>=2**63:raise ValueError("Int64 objective range exceeded")
        model.maximize(sum(weights[node]*variables[node] for node in nodes))
        for node in nodes:model.add_hint(variables[node],int(node in seed));meter.tick("cp_sat_hint")
        remaining=max(0.,meter.deadline-time.process_time())
        if remaining<=0:raise _Stopped("model_build_exhausted_budget")
        solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
        solver.parameters.max_time_in_seconds=remaining;solver.parameters.random_seed=random_seed
        curve=[]
        class Progress(cp_model.CpSolverSolutionCallback):
            def on_solution_callback(self):
                # Saved timings include callback cost. Integer objective is
                # measured from the actual assignment, not rounded rewards.
                reward=sum(weights[node]*self.value(variables[node]) for node in nodes)
                curve.append({"value_ticks":reward,"cpu_seconds":time.process_time()-meter.cpu_start,
                    "wall_seconds":time.perf_counter()-meter.wall_start,"stage":"cp_sat_incumbent"})
        status=solver.solve(model,Progress())
        details.update(status=solver.status_name(status),best_objective_bound_ticks=solver.best_objective_bound,
            branches=solver.num_branches,conflicts=solver.num_conflicts,solver_wall_seconds=solver.wall_time,
            model_and_solve_cpu_seconds=time.process_time()-started,
            incumbent_curve=curve,
            upper_bound_note="solver-reported bound, not reused as a certified ranking oracle")
        if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):return {node for node in nodes if solver.value(variables[node])},details
    except ImportError:details.update(status="dependency_unavailable",dependency="ortools")
    except _Stopped as failure:details.update(status="budget_exhausted",reason=str(failure))
    except Exception as failure:details.update(status="solver_error",error=type(failure).__name__+":"+str(failure))
    return set(seed),details

def default_program(method):
    rule="weight" if method=="weight" else "weight/max(1,degree)"
    return FeatureRuleProgram("classic_"+method,[],rule,"Classical comparison head")

def run_full_schedule(graph,method,seconds,seed,program=None,meter=None,patch_cap=128,
                      destroy_cycle=(16,32),swap_rounds=2,construction_fraction=.2,swap_fraction=.1,max_repairs=10000,native_runner=None):
    if meter is None:meter=_Meter(seconds,"cpu",None,0)
    deadline=meter.cpu_start+seconds;meter.deadline=deadline
    stats={"online_llm_calls":0,"conditional_oracle_calls":0,"head_score_evaluations":0,"head_commits":0}
    curves=[];repairs=[];phases={};rng_construct=random.Random(seed);rng_repair=random.Random(seed)
    def snapshot(stage,current,extra=None):
        child=phases.get("native_published",{}).get("child_cpu_seconds",0.)
        curves.append({"stage":stage,"cpu_seconds":time.process_time()-meter.cpu_start+float(child or 0.),
            "wall_seconds":time.perf_counter()-meter.wall_start,"value_ticks":value_ticks(graph,current),
            "value_exact":value_exact(graph,current),**(extra or {})})
    meter.sealed=True
    incumbent=static_completion(graph,set(graph.nodes),set(),meter);meter.sealed=False
    seed_set=set(incumbent);seed_ticks=value_ticks(graph,incumbent);snapshot("common_degree_seed",incumbent)
    phases["seed_ticks"]=seed_ticks
    if method=="cp_sat":
        proposal,details=cp_sat(graph,incumbent,meter,seed);phases["cp_sat"]=details
        curves.extend(p for p in details.get("incumbent_curve",[]) if p["value_ticks"]>=seed_ticks)
        raw=value_ticks(graph,proposal);phases["cp_sat_raw_ticks"]=raw
        if raw>value_ticks(graph,incumbent):incumbent=proposal;snapshot("cp_sat_improvement",incumbent)
    elif method in ("chils","chils_ils"):
        remaining=max(0.,deadline-time.process_time())
        if native_runner is None:details={"status":"native_runner_unavailable","selected":None}
        else:
            try:details=native_runner(graph,incumbent,remaining,seed)
            except Exception as failure:details={"status":"native_wrapper_error","selected":None,"error":type(failure).__name__+":"+str(failure)}
        phases["native_published"]=details
        if details.get("selected") is not None:
            proposed=set(details["selected"])
            if not graph.feasible(proposed):raise AssertionError("Native solver output violates original fullgraph")
            raw=value_ticks(graph,proposed);phases["native_raw_ticks"]=raw
            if raw>value_ticks(graph,incumbent):incumbent=proposed;snapshot("native_improvement",incumbent)
    else:
        if program is None:program=default_program(method)
        if not isinstance(program,FeatureRuleProgram):program=FeatureRuleProgram.from_dict(program)
        phase_end=min(deadline,time.process_time()+seconds*construction_fraction)
        meter.deadline=phase_end;meter.reason=None
        construction=committing_greedy(graph,program,set(graph.nodes),meter,rng_construct,8 if method=="grasp" else 1)
        meter.sealed=True
        proposed=static_completion(graph,set(graph.nodes),construction["prefix"],meter) if construction["prefix"] else set(seed_set)
        meter.sealed=False
        raw=value_ticks(graph,proposed);accepted=raw>value_ticks(graph,incumbent)
        if accepted:incumbent=proposed;snapshot("head_construction",incumbent)
        phases["construction"]={k:v for k,v in construction.items() if k!="prefix"}
        phases["construction"].update(raw_full_value_ticks=raw,raw_delta_from_seed_ticks=raw-seed_ticks,
            accepted_by_guard=accepted,prefix_nodes=len(construction["prefix"]),
            completion_fallback=construction["status"]!="complete")
        stats["head_score_evaluations"]+=construction["stats"].get("score_evaluations",0)
        stats["head_commits"]+=construction["stats"].get("head_commits",0)
        meter.reason=None;meter.deadline=deadline if method=="local2swap" else min(deadline,time.process_time()+seconds*swap_fraction)
        incumbent,swap_steps=shared_swap(graph,incumbent,meter,max_repairs if method=="local2swap" else swap_rounds)
        phases["shared_swap"]={"steps":swap_steps,"round_limit":swap_rounds}
        if swap_steps:snapshot("shared_swap",incumbent)
        meter.reason=None;meter.deadline=deadline
        for iteration in range(0 if method=="local2swap" else max_repairs):
            if time.process_time()>=deadline:break
            goal=destroy_cycle[iteration%len(destroy_cycle)]
            destroy=set(rng_repair.sample(sorted(incumbent),min(goal,len(incumbent))))
            if not destroy:break
            record={"iteration":iteration,"destroy_count":len(destroy),"destroy_ids":sorted(destroy),"status":"domain_build"}
            try:
                domain,outside,unrestricted_size=repair_domain(graph,incumbent,destroy,patch_cap,meter)
                record.update(active_count=len(domain),unrestricted_candidate_count=unrestricted_size,
                    active_ids=sorted(domain),feature_active_scope="repair_active")
                proposal=committing_greedy(graph,program,domain,meter,rng_construct,8 if method=="grasp" else 1)
                meter.sealed=True
                replacement=static_completion(graph,domain,proposal["prefix"],meter);meter.sealed=False
                raw_ticks=value_ticks(graph,replacement);before=value_ticks(graph,destroy)
                record.update(status=proposal["status"],error=proposal["error"],head_stats=proposal["stats"],
                    raw_gain_ticks=raw_ticks-before,raw_patch_value_ticks=raw_ticks,initial_patch_ticks=before,
                    committed=raw_ticks>before,completion_fallback=proposal["status"]!="complete",
                    head_trace=proposal["trace"],selected_replacement=sorted(replacement))
                stats["head_score_evaluations"]+=proposal["stats"].get("score_evaluations",0)
                stats["head_commits"]+=proposal["stats"].get("head_commits",0)
                if raw_ticks>before:
                    incumbent=outside|replacement;snapshot("head_repair",incumbent,{"iteration":iteration})
                repairs.append(record)
                if proposal["status"] in ("deadline","programme_error"):break
            except _Stopped as failure:
                record.update(status="deadline",error=str(failure),committed=False);repairs.append(record);break
    meter.sealed=True
    incumbent=static_completion(graph,set(graph.nodes),incumbent,meter)
    meter.tick("full_graph_final_validation",len(graph.nodes)+len(graph.edges)+len(incumbent))
    if not graph.feasible(incumbent):raise AssertionError("Final complete-graph schedule is infeasible")
    if value_ticks(graph,incumbent)<seed_ticks:raise AssertionError("Anytime incumbent lost common seed")
    snapshot("final",incumbent)
    parent_cpu=time.process_time()-meter.cpu_start
    native_child_cpu=phases["native_published"].get("child_cpu_seconds") if "native_published" in phases else 0.
    total_cpu=parent_cpu+float(native_child_cpu or 0.)
    return {"selected":sorted(incumbent),"value_ticks":value_ticks(graph,incumbent),"value_exact":value_exact(graph,incumbent),
        "feasible":True,"nodes":len(graph.nodes),"edges":len(graph.edges),"selected_count":len(incumbent),
        "selected_set_sha256":sha256(json.dumps(sorted(incumbent)).encode()).hexdigest(),
        "method":method,"seed":seed,"declared_cpu_seconds":seconds,"cpu_seconds":total_cpu,
        "parent_cpu_seconds":parent_cpu,"native_child_cpu_seconds":native_child_cpu,
        "native_cpu_measurement_available":native_child_cpu is not None,
        "wall_seconds":time.perf_counter()-meter.wall_start,"budget_clock":"cpu","deadline_soft_overshoot":total_cpu>seconds,
        "seed_value_ticks":seed_ticks,"seed_selected":sorted(seed_set),"phases":phases,"repairs":repairs,"best_so_far":curves,
        "stats":stats,"meter":dict(meter),"patch_cap":patch_cap,"destroy_cycle":destroy_cycle,
        "scope":"complete graph MWIS feasible schedule; repair subdomains are search components, not evaluation datasets",
        "head_priority_role":"irrevocable greedy action commit; no forced-completion oracle as pivot",
        "exact_global_optimum_claimed":False,"numeric_namespace":NAMESPACE,
        "head_ever_committed":stats["head_commits"]>0,
        "standard_components":"common degree seed, dynamic greedy head, improving 1/2 swaps, bounded ruin/recreate",
        "unavoidable_overshoot_scope":"complete feasible remainder and final validation; all observed time/work retained"}
