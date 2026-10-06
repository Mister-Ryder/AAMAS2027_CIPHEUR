"""Four station-group configurations and explicit station-local base9 adapter.

No new physics, graph edits, task weights, solver algorithm, or LLM calls.
All queries/boundaries are inherited unchanged from the pre-label expanded
P0 manifests and their common strong-configuration Degree incumbent.
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
from cipheur.repair_v06 import _Meter, _solve, _priorities, _initialize
from cipheur.compiled import CompiledEvaluator, _CompiledSnapshot, _LazyScoreLocals
from cipheur.graph_features import _BASE_EXPRESSIONS, _charge
import math

CONFIGS={"A":(340,340),"W":(1200,340),"E":(340,1200),"J":(1200,1200)}
PAIRS=(("A","J"),("A","W"),("A","E"),("W","J"),("E","J"),("W","E"))
CAPS=((8,16),(16,64),(32,128))
QUERY_SECONDS=2.
EPSILON_TICKS=1
HEADS=("degree","existing_frozen","certified_reference")
NAMESPACE="heterogeneous_station_local_base9_v1"


class StationLocalEvaluator(CompiledEvaluator):
    """Same programme/DAG/other8 fields, explicitly root-local station gap."""
    def _station_gap(self,node):
        _charge(self.meter,"constraint_read",2)
        _charge(self.meter,"station_local_root_field_read")
        antenna=self.graph.nodes[node].station
        _charge(self.meter,"station_local_mapping_read")
        return self.graph.constraints["station_gap_by_antenna"][antenna]

    def feature_values(self,node):
        if node not in self.active:raise ValueError("Scored node must be active")
        before=self.meter["feature_work"];started=time.perf_counter()
        try:
            if self._snapshot is None:
                _charge(self.meter,"snapshot_materialize",len(self.active));self._snapshot=_CompiledSnapshot(self)
            values={name:self._snapshot.evaluate(expression,node) for name,expression in _BASE_EXPRESSIONS.items()
                    if not self.score_slice or name in self.required_names}
            for name,expression in self.program._expressions:
                if not self.score_slice or name in self.required_names:values[name]=self._snapshot.evaluate(expression,node)
            if not self.score_slice or "station_gap" in self.required_names:values["station_gap"]=self._station_gap(node)
            if not self.score_slice or "satellite_gap" in self.required_names:
                _charge(self.meter,"constraint_read",2);values["satellite_gap"]=self.graph.constraints["satellite_gap"]
            return values
        finally:
            self.meter["query_work"]+=self.meter["feature_work"]-before
            self.meter["feature_seconds"]+=time.perf_counter()-started

    def score(self,node):
        if not self.score_slice:return self.program._rank(self.feature_values(node),self.meter)
        if node not in self.active:raise ValueError("Scored node must be active")
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
                if name=="station_gap":return self._station_gap(node)
                if name=="satellite_gap":
                    _charge(self.meter,"constraint_read",2);return self.graph.constraints["satellite_gap"]
                raise ValueError("Unknown scorer input:"+name)
            finally:
                self.meter["query_work"]+=self.meter["feature_work"]-before
                duration=time.perf_counter()-start;self.meter["feature_seconds"]+=duration;elapsed[0]+=duration
        started=time.perf_counter()
        try:value=float(eval(self.program.code,{"__builtins__":{}},_LazyScoreLocals(getter)))
        except(ZeroDivisionError,TypeError,ValueError,OverflowError) as error:raise ValueError("Invalid score:"+str(error)) from error
        finally:self.meter["scoring_seconds"]+=max(0.,time.perf_counter()-started-elapsed[0])
        if not math.isfinite(value) or abs(value)>1e15:raise ValueError("Nonfinite/bounded score violation")
        return value


def local_phi(graph,node,patch):
    adjacent=graph.adj[node]&patch;terms={v:Fraction(float(graph.nodes[v].weight)) for v in patch}
    neighbor_sum=sum((terms[v] for v in adjacent),Fraction());total=sum(terms.values(),Fraction())
    contact=graph.nodes[node]
    values={"weight":contact.weight,"duration":contact.end-contact.start,"degree":len(adjacent),
        "conflict_weight":float(neighbor_sum),"max_conflict_weight":max((graph.nodes[v].weight for v in adjacent),default=0),
        "compatible_weight":float(total-neighbor_sum-terms[node]),
        "station_gap":graph.constraints["station_gap_by_antenna"][contact.station],
        "satellite_gap":graph.constraints["satellite_gap"],"remaining_count":len(patch)}
    return tuple(str(Fraction(values[name])) for name in core.FEATURES)


def tag(config):
    w,e=CONFIGS[config]
    return f"gW{w:04d}_gE{e:04d}_s0150"


def register():
    bank=core.PROJECT/"examples"/"frozen_joint_bank_v06.json"
    frozen=json.loads(bank.read_text(encoding="utf-8"))["programs"][0]
    fixture_path=EXT/"analysis"/"adapter_fixture.json"
    fixture=json.loads(fixture_path.read_text(encoding="utf-8"))
    if not fixture["all_passed"] or fixture["production_script_sha256"]!=core.digest(SCRIPT):raise ValueError("Station-local adapter fixture missing or stale")
    value={"stage":"single heterogeneous west/east ground-resource TRAIN extension",
        "physical_data":"same four original STK libraries, two source groups; no additional physical axis or TEST",
        "configurations_seconds":CONFIGS,"primary_pair":"A->J",
        "station_groups":{"west_longitudes_deg":[88,94,100],"east_longitudes_deg":[106,112,118],"each_sites":6},
        "factorial_pairs":{"west":"A->W","east":"A->E","east_at_strong_west":"W->J","west_at_strong_east":"E->J","secondary_cross_diagonal":"W->E"},
        "anchors":"reuse all30 original pre-label patch_interface_probe manifest queries and commonJ incumbent, never read old labels or winners",
        "patch_caps":CAPS,"patch_rule":"unchanged registered old expanded F/P/X/D/a/b; J edgegraph is identical oldg1200_s150",
        "boundary":"same completecontacts,F,P,X=V minus(F unionP), and competing feasiblea/b inall4configs; A is weakest",
        "inventory":{"sources":list(core.SOURCES),"anchors_per_source":10,"quadqueries_per_source":30,"total_quadqueries":120},
        "certificate":"8 forced spaces perquadquery, shared2second wall budget, same 1tick epsilon; valid lower witnesses and min(root,frontier) clique upper enclosure",
        "certificate_scope":"restricted outside-fixed patch, frozen microsecond numeric instance, not72h global optimum",
        "strict_patterns":"all16patterns of4strict signs inA,W,E,J order; partial/tie/unavailable separately retained",
        "joint_only_reversal":"four sides all strict, A=W=E direction andJ opposite; denominator four-side-strict quadqueries, also report all planned slots",
        "interaction":"I=Delta_J-Delta_W-Delta_E+Delta_A; sound[LJ-UW-UE+LA,UJ-LW-LE+UA], eachDelta=Va-Vb under sameF/P/X",
        "derived_pair_relations":"all6 pairs derived from saved4side labels, no extra solver calls; unknown cannot count as preservation",
        "numeric_namespace":NAMESPACE,
        "station_gap_semantics":"root contact antenna actual gap; no global mean/min/zero substitute. Original uniform340/1200 scalar is valid uniform special case; other groups are visible through complete currentgraph",
        "adapter_cost":"original DAG/scorer counters retained; additional station_local_root_field_read and station_local_mapping_read charged only when station_gap actually read",
        "old_AJ_bound_reuse":False,
        "adapter_fixture_sha256":core.digest(fixture_path),
        "execution":{"B&B":"unchanged actual frozen repair solve, lazy heads, same2000nodes perhead, allcosts recorded",
            "commit":"separate diagnostic pairwisecommit+common dynamicDegree completion, raw and common positivegain guard results",
            "heads":HEADS,"reference":"strict side certificate only; otherwise explicitDegree fallback; offline development probe"},
        "frozen_id":frozen["id"],"frozen_program":frozen["program"],
        "frozen_bank_sha256":core.digest(bank),
        "dependencies_sha256":{"p0_evidence.py":core.digest(BASE/"scripts"/"p0_evidence.py"),
            "p0_patch_interface_probe.py":core.digest(BASE/"scripts"/"p0_patch_interface_probe.py"),
            "repair_v06.py":core.digest(core.PROJECT/"cipheur"/"repair_v06.py"),
            "compiled.py":core.digest(core.PROJECT/"cipheur"/"compiled.py")},
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
    actuals=int(z["satellite_gap_ticks"].item())
    if actuals!=150*core.SCALE:raise ValueError("Satellite gap must remain150")
    node_gaps=z["ground_gap_by_node_ticks"]
    if len(node_gaps)!=len(z["contact_id"]):raise ValueError("No exact per-node ground gap")
    by_antenna={}
    for antenna,ticks in zip(z["antenna_id"],node_gaps):
        name=str(antenna);gap=Fraction(int(ticks),core.SCALE)
        if name in by_antenna and by_antenna[name]!=gap:raise ValueError("Antenna gap inconsistent across contacts")
        by_antenna[name]=gap
    if any(v not in (Fraction(340),Fraction(1200)) for v in by_antenna.values()):raise ValueError("Unexpected ground gap")
    meta=json.loads((EXT/"graphs"/source/(tag(config)+".json")).read_text(encoding="utf-8"))
    if meta["station_gap_mode"]!="per_antenna" or meta["satellite_gap_seconds"]!=150:raise ValueError("Graph constraint metadata mismatch")
    expected_map={k:Fraction(v) for k,v in meta["station_gap_by_antenna_seconds"].items()}
    if by_antenna!=expected_map or len(by_antenna)!=12:raise ValueError("Root gap field does not exactly join antenna metadata")
    groups=meta["antenna_group"]
    if set(groups)!=set(by_antenna) or set(groups.values())!={"west","east"}:raise ValueError("Invalid resource groups")
    for antenna,group in groups.items():
        if by_antenna[antenna]!=CONFIGS[config][0 if group=="west" else 1]:raise ValueError("Station group configuration mismatch")
    map_pairs={str(k):Fraction(int(v),core.SCALE) for k,v in zip(z["ground_gap_antenna_ids"],z["ground_gap_antenna_ticks"])}
    if map_pairs!=by_antenna:raise ValueError("NPZ antenna map mismatch")
    if "ground_gap_ticks" in z:raise ValueError("Heterogeneous graph must have no global ground gap scalar")
    ids=[str(x) for x in z["contact_id"]]
    contacts=tuple(core.Contact(ids[i],Fraction(int(z["weight_ticks"][i]),core.SCALE),
        str(z["satellite_id"][i]),str(z["antenna_id"][i]),
        Fraction(int(z["start_ticks"][i]),core.SCALE),Fraction(int(z["end_ticks"][i]),core.SCALE)) for i in range(len(ids)))
    edges=frozenset((ids[int(a)],ids[int(b)]) for a,b in zip(z["edge_u"],z["edge_v"]))
    graph=core.Graph(source+"-"+tag(config),contacts,edges,
        dict(station_gap_mode="per_antenna",station_gap_by_antenna={k:int(v) for k,v in by_antenna.items()},
             satellite_gap=150,model="complete_contact_heterogeneous_ground_gap_v1"))
    if config in ("A","J"):
        expected=Fraction(340 if config=="A" else 1200)
        if set(by_antenna.values())!={expected}:raise ValueError("Uniform A/J metadata mismatch")
    return graph,ids


def prepare(source,graphs,ids,out):
    start=time.perf_counter();j=graphs["J"]
    old_path=OLDPROBE/source/"query_manifest.json"
    original=json.loads(old_path.read_text(encoding="utf-8"))
    incumbent_path=P0/source/"external_incumbent.json"
    incumbent_record=json.loads(incumbent_path.read_text(encoding="utf-8"))
    incumbent={ids[i] for i in incumbent_record["selected_indices"]}
    if not j.feasible(incumbent):raise AssertionError("Original J incumbent must remain feasible")
    core.dump(out/"external_incumbent_J.json",incumbent_record|{"original_file_sha256":core.digest(incumbent_path),
        "purpose":"identical oldJ external schedule, no new optimizer or result-based selection"})
    queries=[]
    for original_query in original["queries"]:
        query=json.loads(json.dumps(original_query))
        if query.get("status")=="unavailable":queries.append(query);continue
        a,b=ids[query["a"]],ids[query["b"]]
        if a!=query["a_contact_id"] or b!=query["b_contact_id"]:raise AssertionError("Original indices remapped")
        fixed={ids[i] for i in query["fixed_indices"]};destroy={ids[i] for i in query["destroy_indices"]}
        patch={ids[i] for i in query["patch_indices"]}
        if fixed|destroy!=incumbent or fixed&destroy or not destroy<=(patch):raise AssertionError("Original J boundary changed")
        for config,graph in graphs.items():
            if not graph.feasible(fixed) or b not in graph.adj[a] or any(graph.adj[v]&fixed for v in patch):
                raise AssertionError("Same fourconfig boundary not available:"+config)
        query.update(all4actions_feasible_competing=True,origin_manifest_sha256=core.digest(old_path),
            representation_namespace=NAMESPACE)
        queries.append(query)
    if len(queries)!=30:raise AssertionError("Must retain all30 original registered query slots")
    value={"source":source,"queries":queries,"prepared_before_labels":True,
        "original_prelabel_patch_manifest_sha256":core.digest(old_path),
        "graph_npz_sha256":{c:core.digest(EXT/"graphs"/source/(tag(c)+".npz")) for c in CONFIGS},
        "old_label_reused":False,"budget":"all8spaces recertified under equal2seconds",
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
    ilo=signs["J"]["lower_ticks"]-signs["W"]["upper_ticks"]-signs["E"]["upper_ticks"]+signs["A"]["lower_ticks"]
    ihi=signs["J"]["upper_ticks"]-signs["W"]["lower_ticks"]-signs["E"]["lower_ticks"]+signs["A"]["upper_ticks"]
    isign="positive" if ilo>EPSILON_TICKS else "negative" if ihi< -EPSILON_TICKS else "tie" if ilo==ihi==0 else "unknown"
    return {"query_id":query["id"],"scope":"same restrictedP/F/X underfourresource configurations",
        "bounds":bounds,"signs":signs,"pair_relations":relations,
        "all_four_strict":strict4,"strict_pattern_AWEJ_order":pattern,
        "pattern_config_order":["A","W","E","J"],
        "joint_only_reversal":strict4 and labels["A"]==labels["W"]==labels["E"] and labels["J"]!=labels["A"],
        "interaction":{"lower_ticks":ilo,"upper_ticks":ihi,"sign":isign,"epsilon_ticks":EPSILON_TICKS,
            "formula":"DeltaJ-DeltaW-DeltaE+DeltaA; [LJ-UW-UE+LA,UJ-LW-LE+UA]"},
        "common_fixed_reward_ticks":sum(int(arrays["A"]["weight_ticks"][i]) for i in query["fixed_indices"]),
        "bound_value_scope":"variable patch contribution; same fixed reward cancels fromeveryDelta",
        "wall_seconds":time.perf_counter()-start,"declared_wall_seconds":QUERY_SECONDS,
        "budget_soft_overshoot_note":"final legitimate bound/witness validation is included inactualtime"}


NODES=2000
SCALE=core.SCALE


def _adapter_priorities(graph,nodes,program,kind,rng,meter):
    if kind!="program":return _priorities(graph,nodes,program,kind,rng,meter)
    evaluator=StationLocalEvaluator(graph,program,nodes,meter,score_slice=True)
    values={}
    for node in sorted(nodes):
        meter.tick("priority_score");values[node]=evaluator.score(node)
    return values


def run_bb(graph, ids, query, cert, side, program):
    patch = {ids[i] for i in query["patch_indices"]}
    fixed = {ids[i] for i in query["fixed_indices"]}
    destroy = {ids[i] for i in query["destroy_indices"]}
    initial = fixed | destroy
    a, b = ids[query["a"]], ids[query["b"]]
    preferred = cert["signs"][side]["preference"]
    rows = []
    for head in ("degree","existing_frozen","certified_reference"):
        meter=_Meter(None,"cpu",None,NODES)
        weights={v:graph.nodes[v].weight for v in patch}
        meter.tick("exact_weight_conversion",len(patch))
        called,head_seconds,changed=False,0.,False
        def factory(region):
            nonlocal called,head_seconds,changed
            called=True
            start=time.perf_counter()
            scores=_adapter_priorities(graph,region,program,"program" if head=="existing_frozen" else "degree",None,meter)
            if head=="certified_reference" and preferred in ("a","b"):
                meter.tick("offline_reference_lookup")
                good,bad=(a,b) if preferred=="a" else (b,a)
                if scores[good]<=scores[bad]:
                    if scores[good]<scores[bad]:scores[good],scores[bad]=scores[bad],scores[good]
                    else:scores[good]+=Fraction(1,SCALE)
                    changed=True
            head_seconds=time.perf_counter()-start
            return scores
        result=_solve(graph,patch,destroy,weights,factory,meter,NODES,True)
        updated=fixed|set(result["local_selected"])
        meter.sealed=True
        meter.tick("final_validation",len(updated)+sum(len(graph.adj[v]) for v in updated))
        if not graph.feasible(updated) or not fixed<=updated or sum((graph.nodes[v].weight for v in updated),Fraction())<sum((graph.nodes[v].weight for v in initial),Fraction()):
            raise AssertionError("Actual solver returned invalid full-schedule patch")
        result.update(gain_exact=str(Fraction(result["lower_exact"])-sum((graph.nodes[v].weight for v in destroy),Fraction())),
            cpu_seconds=time.process_time()-meter.cpu_start,wall_seconds=time.perf_counter()-meter.wall_start,meter=dict(meter))
        row = {k:result[k] for k in ("lower_exact","upper_exact","restricted_exact","termination",
            "search_nodes","bound_cuts","priority_order","common_degree_order","greedy_passes",
            "pivot_count","degree_pivot_disagreements","root_pruned","gain_exact",
            "local_selected","cpu_seconds","wall_seconds","meter")}
        row.update(head=head, query_id=query["id"], side=side,
            head_called=called,head_preparation_wall_seconds=head_seconds,
            head_meter={"feature_work":meter.get("feature_work",0),"feature_primitives":meter.get("feature_primitives",{})},
            total_wall_seconds=result["wall_seconds"],
            total_operation_proxy=meter.get("feature_work",0)+meter.get("repair_work",0),
            preferred_probe_action=preferred, reference_degree_pair_changed=changed if head=="certified_reference" else None,
            committed=Fraction(result["gain_exact"])>0,
            selected_set_sha256=core.sha256(json.dumps(sorted(updated)).encode()).hexdigest(),
            full_schedule_value_exact=str(sum((graph.nodes[v].weight for v in updated),Fraction())),
            first_greedy_improvement=None)
        baseline = sum((graph.nodes[v].weight for v in destroy), Fraction())
        for i, p in enumerate(result["greedy_passes"]):
            if Fraction(p["value_exact"]) > baseline:
                row["first_greedy_improvement"] = {"pass_index":i,"pass_type":p["order"],
                    "value_exact":p["value_exact"],"complete":p["complete"]}
                break
        rows.append(row)
    return rows

def run_commit(graph,ids,query,cert,side,program):
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
            evaluator=StationLocalEvaluator(graph,program,patch,meter,score_slice=True)
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


def source_graphs(source):
    arrays={c:core.load(EXT/"graphs"/source/(tag(c)+".npz")) for c in CONFIGS}
    graphs={};ids=None
    for c in CONFIGS:
        graph,these=build_graph(arrays[c],source,c);graphs[c]=graph
        if ids is None:ids=these
        if these!=ids or graph.contacts!=graphs["A"].contacts:raise AssertionError("Different quadcontacts")
    if not(graphs["A"].edges<=graphs["W"].edges and graphs["A"].edges<=graphs["E"].edges and
            graphs["J"].edges==graphs["W"].edges|graphs["E"].edges):raise AssertionError("Invalid resourcecrossing")
    return arrays,graphs,ids


def process_source(source,registration,limit_anchors=None):
    out=OUTPUT/source;out.mkdir(parents=True,exist_ok=True)
    arrays,graphs,ids=source_graphs(source)
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
                    "preferred_phi":list(local_phi(graph,ids[good],patch)),"other_phi":list(local_phi(graph,ids[bad],patch)),
                    "numeric_namespace":NAMESPACE})
            tp=out/"bb_traces"/(identity+"_"+config+".json")
            rows=json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else run_bb(graph,ids,query,cert,config,program)
            core.dump(tp,rows);bb.extend(rows)
            tp=out/"commit_traces"/(identity+"_"+config+".json")
            rows=json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else run_commit(graph,ids,query,cert,config,program)
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
    q=core.quotient(requirements);q["numeric_namespace"]=NAMESPACE;core.dump(OUTPUT/"complete_demanded_quotient.json",q)
    patterns=Counter(c["strict_pattern_AWEJ_order"] for c in certificates if c["all_four_strict"])
    pattern_table=[{"pattern":"".join(p),"count":patterns["".join(p)],"joint_only_reversal":"".join(p) in ("+++-","---+")} for p in itertools.product("+-",repeat=4)]
    core.dump(OUTPUT/"all16_strict_pattern_table.json",{"config_order":["A","W","E","J"],"patterns":pattern_table,
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
    for r in requirements:r["evidence_stage"]="heterogeneous_ground_quad";combined.append(r)
    union=core.quotient(combined);union["numeric_namespace"]=NAMESPACE+"_uniform_compatible_union"
    union["compatibility"]="old station_gap is actual root antenna gap in uniform special case; verified adapter fixture; remaining8 numeric coordinates identical"
    core.dump(OUTPUT/"new_old_quotient_union.json",union)
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
    if args.register_only:
        for source in core.SOURCES:
            arrays,graphs,ids=source_graphs(source)
            out=OUTPUT/source;out.mkdir(parents=True,exist_ok=True)
            manifest_path=out/"query_manifest.json"
            if not manifest_path.exists():prepare(source,graphs,ids,out)
        return
    if not args.aggregate_only:
        for source in ((args.source,) if args.source else core.SOURCES):process_source(source,registration,args.limit_anchors)
    if not args.no_aggregate:aggregate()


if __name__=="__main__":main()
