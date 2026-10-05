"""Incremental feasible MWIS kernel with accountable LLM operator participation.

All objectives and gain guards are integer ticks. Small repair domains have
explicit fixed outside boundaries; LLM output never owns feasibility checks.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import random
import time
from pathlib import Path
import numpy as np

from .controller import OnlineController
from .typed import PatchEvaluator, validate_recipe
from .certificates import local_certificates, EvidenceArchive

@dataclass
class IntGraph:
    adjacency: dict
    weights: dict
    contact_ids: list
    metadata: dict
    source_metadata: dict
    edge_u: np.ndarray
    edge_v: np.ndarray

def load_graph(path, metadata_path):
    with np.load(path,allow_pickle=False) as z:
        ids=[str(x) for x in z['contact_id']]
        weights={i:int(w) for i,w in enumerate(z['weight_ticks'])}
        adj={i:set() for i in weights}
        u=z['edge_u'].astype(np.int64);v=z['edge_v'].astype(np.int64)
        for a,b in zip(u,v):
            a=int(a);b=int(b);adj[a].add(b);adj[b].add(a)
        gap=z['ground_gap_by_node_ticks'] if 'ground_gap_by_node_ticks' in z else [int(z['ground_gap_ticks'].item())]*len(ids)
        data=dict(weight_scale=1000000,
            duration={i:Fraction(int(b)-int(a),1000000) for i,(a,b) in enumerate(zip(z['start_ticks'],z['end_ticks']))},
            station_gap={i:Fraction(int(g),1000000) for i,g in enumerate(gap)},
            satellite_gap=Fraction(int(z['satellite_gap_ticks'].item()),1000000),
            station={i:str(x) for i,x in enumerate(z['antenna_id'])},
            satellite={i:str(x) for i,x in enumerate(z['satellite_id'])})
    meta=json.loads(Path(metadata_path).read_text(encoding='utf-8'))
    return IntGraph(adj,weights,ids,data,meta,u,v)

class Incumbent:
    def __init__(self, graph, initial=()):
        self.graph=graph;self.selected=set();self.order=[];self.positions={}
        self.blockers=[0]*len(graph.weights);self.value=0
        for node in initial:self.add(node)
    def add(self,node):
        if node in self.selected or self.blockers[node]:raise AssertionError('Infeasible insertion')
        self.positions[node]=len(self.order);self.order.append(node);self.selected.add(node)
        self.value+=self.graph.weights[node]
        for other in self.graph.adjacency[node]:self.blockers[other]+=1
    def remove(self,node):
        pos=self.positions.pop(node);last=self.order.pop()
        if pos<len(self.order):self.order[pos]=last;self.positions[last]=pos
        self.selected.remove(node);self.value-=self.graph.weights[node]
        for other in self.graph.adjacency[node]:self.blockers[other]-=1
    def commit(self,removed,added):
        before=self.value
        if sum(self.graph.weights[v] for v in added)<=sum(self.graph.weights[v] for v in removed):return False
        for v in removed:self.remove(v)
        try:
            for v in added:self.add(v)
        except Exception:
            for v in set(added)&self.selected:self.remove(v)
            for v in removed:self.add(v)
            raise
        assert self.value>before
        return True

def degree_seed(graph, initial=()):
    state=Incumbent(graph,initial)
    for node in sorted(graph.weights,key=lambda v:(-graph.weights[v]/(1+len(graph.adjacency[v])),v)):
        if node not in state.selected and not state.blockers[node]:state.add(node)
    return state

def feasible(graph,chosen):
    return all(not(graph.adjacency[v]&chosen) for v in chosen)

def shared_exchange(state,rng,samples=48):
    """Sampled weighted 1/2-exchanges; shared by every in-project variant."""
    graph=state.graph;best=(0,(),());groups=defaultdict(list)
    for _ in range(samples):
        v=rng.randrange(len(graph.weights))
        if v in state.selected or state.blockers[v]>2:continue
        removed=tuple(graph.adjacency[v]&state.selected)
        gain=graph.weights[v]-sum(graph.weights[x] for x in removed)
        if gain>best[0]:best=(gain,(v,),removed)
        if len(removed)==1:groups[removed[0]].append(v)
    for root,pool in groups.items():
        for i,a in enumerate(pool):
            for b in pool[i+1:]:
                if a!=b and b not in graph.adjacency[a]:
                    gain=graph.weights[a]+graph.weights[b]-graph.weights[root]
                    if gain>best[0]:best=(gain,(a,b),(root,))
    if best[0]>0:state.commit(set(best[2]),set(best[1]))
    return best[0]

def choose_patch(state,recipe,rng,rejected):
    """Operator selects location and size; exact outside check owns legality."""
    graph=state.graph;policy=recipe['patch_policy'];k=policy['destroy_count']
    if not state.order:return set(),set(),dict(anchor_policy=policy['anchor'])
    mode=policy['anchor'];destroy=set();anchor=None
    if mode=='rejection_frontier' and rejected:
        pool=list(set(rejected[rng.randrange(len(rejected))])&state.selected)
        if pool:anchor=rng.choice(pool);destroy.add(anchor)
    if mode in ('blocked_gain','resource_boundary'):
        candidates=[]
        for _ in range(32):
            v=rng.randrange(len(graph.weights))
            if v in state.selected or state.blockers[v]>k:continue
            blockers=graph.adjacency[v]&state.selected
            if not blockers:continue
            loss=sum(graph.weights[x] for x in blockers)
            priority=graph.weights[v]/max(1,loss)
            if mode=='resource_boundary':
                # Resource coupling, not a lookup table for gap configurations.
                resources={(graph.metadata['station'][x],graph.metadata['satellite'][x]) for x in blockers}
                priority*=1+len(resources)/max(1,len(blockers))
            candidates.append((priority,v,blockers))
        if candidates:
            _,anchor,blockers=max(candidates,key=lambda x:(x[0],x[1]));destroy.update(blockers)
    if anchor is None:anchor=rng.choice(state.order);destroy.add(anchor)
    # Selected contacts compete through unselected contacts; selected nodes
    # cannot be direct adjacent neighbors in a feasible incumbent.
    frontier=set()
    for v in destroy:frontier.update(graph.adjacency[v])
    coupled=set()
    for v in frontier:coupled.update(graph.adjacency[v]&state.selected)
    pool=sorted(coupled-destroy)
    if pool:
        destroy.update(rng.sample(pool,min(max(0,k-len(destroy)),len(pool))))
    if len(destroy)<k:
        destroy.update(rng.sample(state.order,min(k-len(destroy),len(state.order))))
    outside=state.selected-destroy
    domain=set(destroy)
    for v in destroy:domain.update(graph.adjacency[v])
    if policy['expand_hops']==2:
        expanded=set(domain)
        for v in domain:expanded.update(graph.adjacency[v])
        domain=expanded
    legal=[v for v in domain-destroy-outside if not(graph.adjacency[v]&outside)]
    legal.sort(key=lambda v:(-graph.weights[v]/(1+len(graph.adjacency[v]&domain)),v))
    patch=destroy|set(legal[:max(0,policy['patch_cap']-len(destroy))])
    return destroy,patch,dict(anchor_policy=mode,anchor_node=anchor,destroy_size=len(destroy),
        patch_size=len(patch),uncapped_eligible=len(legal)+len(destroy),outside_count=len(outside))

def local_exchange(adj,weights,selected,deadline):
    current=set(selected)
    while time.process_time()<deadline:
        best=(0,(),());groups=defaultdict(list)
        for v in adj.keys()-current:
            blockers=adj[v]&current;gain=weights[v]-sum(weights[x] for x in blockers)
            if gain>best[0]:best=(gain,(v,),tuple(blockers))
            if len(blockers)==1:groups[next(iter(blockers))].append(v)
        for root,pool in groups.items():
            for i,a in enumerate(pool):
                for b in pool[i+1:]:
                    if b not in adj[a]:
                        gain=weights[a]+weights[b]-weights[root]
                        if gain>best[0]:best=(gain,(a,b),(root,))
        if best[0]<=0:break
        current.difference_update(best[2]);current.update(best[1])
    return current

def reconstruct(graph,patch,recipe,coefficients,rng,deadline):
    adj={v:graph.adjacency[v]&patch for v in patch}
    selected=set();rank_trace=[];status='complete';started=time.process_time()
    try:
        ev=PatchEvaluator(adj,graph.weights,recipe,coefficients,set(patch),set(patch),graph.metadata,deadline)
    except TimeoutError as exc:
        return selected,dict(status='TimeoutError:'+str(exc),rank_value_ticks=0,exchange_added_ticks=0,
            rank_commits=0,rank_trace=[],feature_stats={},reconstruction_cpu_seconds=time.process_time()-started)
    feature_limit=recipe['evaluation_plan']['max_feature_cpu_fraction']*max(0,deadline-started)
    try:
        while ev.active:
            ranking=sorted(((ev.score(v),v) for v in ev.active),reverse=True)
            if ev.stats.get('feature_cpu',ev.stats.get('feature_cpu_seconds',0))>feature_limit:
                raise TimeoutError('feature_cpu_fraction')
            if time.process_time()>=deadline:raise TimeoutError('trial_cpu_deadline')
            top=ranking[:3] if recipe['patch_policy']['reconstruction']=='rcl' else ranking[:1]
            score,node=rng.choice(top);selected.add(node)
            rank_trace.append(dict(node=node,score=float(score),active_count=len(ev.active)))
            ev.remove({node}|adj[node])
    except (TimeoutError,ArithmeticError,ValueError) as exc:
        status=type(exc).__name__+':'+str(exc)
    rank_value=sum(graph.weights[x] for x in selected)
    if status=='complete' and recipe['patch_policy']['reconstruction']=='exchange':
        selected=local_exchange(adj,graph.weights,selected,deadline)
    return selected,dict(status=status,rank_value_ticks=rank_value,
        exchange_added_ticks=sum(graph.weights[x] for x in selected)-rank_value,
        rank_commits=len(rank_trace),rank_trace=rank_trace,feature_stats=dict(ev.stats),
        reconstruction_cpu_seconds=time.process_time()-started)

def solve(graph,recipes,seconds,seed,*,mode='online',initial=(),instance_id='instance',cpu_start=None,controller_config=None):
    started=time.process_time() if cpu_start is None else cpu_start;wall=time.perf_counter();deadline=started+seconds
    for recipe in recipes:validate_recipe(recipe)
    events=[];rng=random.Random(seed);controller=OnlineController(recipes,instance_id,mode=mode,seed=seed,
        log_callback=events.append,config=controller_config)
    state=degree_seed(graph,initial);seed_value=state.value
    curve=[dict(cpu_seconds=time.process_time()-started,value_ticks=state.value,stage='degree_seed')]
    logs=[];rejected=deque(maxlen=16);archives={};certificates=[]
    totals=defaultdict(int);trial=0
    while time.process_time()<deadline:
        trial+=1
        if trial%4==0:
            gain=shared_exchange(state,rng)
            totals['shared_exchange_attempts']+=1;totals['shared_exchange_gain_ticks']+=gain
            if gain:curve.append(dict(cpu_seconds=time.process_time()-started,value_ticks=state.value,stage='shared_exchange'))
        if time.process_time()>=deadline:break
        trial_start=time.process_time();genome=controller.select(rng,dict(trial=trial,value_ticks=state.value))
        destroy,patch,patch_detail=choose_patch(state,genome.recipe,rng,rejected)
        if not patch:break
        fixed_outside=state.selected-destroy
        removed=sum(graph.weights[x] for x in destroy)
        trial_deadline=min(deadline,trial_start+(0.02 if seconds<=2 else 0.05 if seconds<=10 else 0.1))
        parent=None;race=None
        if controller_config and controller_config.get('paired_race') and genome.parent_id:
            if not controller.statistics[genome.id]['observations']:
                parent=next((g for g in controller.population if g.id==genome.parent_id),None)
        rng_state=rng.getstate()
        reconstruction_allowance=max(0.,trial_deadline-time.process_time())
        proposal,details=reconstruct(graph,patch,genome.recipe,genome.coefficients,rng,trial_deadline)
        child_details=details
        raw_gain=sum(graph.weights[x] for x in proposal)-removed
        committed_genome=genome;selected_details=details;selected_proposal=proposal
        selected_gain=raw_gain
        if parent is not None and time.process_time()<deadline:
            parent_rng=random.Random();parent_rng.setstate(rng_state)
            parent_started=time.process_time()
            parent_proposal,parent_details=reconstruct(graph,patch,parent.recipe,parent.coefficients,parent_rng,
                min(deadline,parent_started+reconstruction_allowance))
            parent_gain=sum(graph.weights[v] for v in parent_proposal)-removed
            parent_duration=time.process_time()-parent_started
            controller.observe(parent.id,parent_gain,removed,parent_duration,cert_fit=None)
            race=dict(parent_id=parent.id,parent_program_hash=parent.program_hash,
                same_patch=True,same_fixed_outside=True,parent_raw_gain_ticks=parent_gain,
                requested_reconstruction_cpu_allowance=reconstruction_allowance,
                parent_allowance_truncated_by_total_budget=deadline<parent_started+reconstruction_allowance,
                parent_cpu_seconds=parent_duration,parent_status=parent_details['status'],
                parent_feature_stats=parent_details['feature_stats'],parent_rank_commits=parent_details['rank_commits'])
            totals['paired_races']+=1
            if parent_details['status']=='complete' and (details['status']!='complete' or parent_gain>raw_gain):
                selected_proposal=parent_proposal;selected_details=parent_details;selected_gain=parent_gain;committed_genome=parent
                totals['paired_parent_wins']+=1
            else:totals['paired_child_wins_or_ties']+=1
            race['winner_id']=committed_genome.id
        proposal=selected_proposal;details=selected_details;accepted=details['status']=='complete' and selected_gain>0
        if accepted:
            outside=state.selected-destroy
            if proposal&outside or not feasible(graph,proposal) or any(graph.adjacency[x]&outside for x in proposal):
                raise AssertionError('Kernel rejected an infeasible operator proposal')
            state.commit(destroy,proposal)
            totals['operator_accepted']+=1;totals['operator_gain_ticks']+=selected_gain
            totals['rank_stage_gain_ticks']+=details['rank_value_ticks']-removed
            totals['local_exchange_added_ticks']+=details['exchange_added_ticks']
            curve.append(dict(cpu_seconds=time.process_time()-started,value_ticks=state.value,
                stage='operator_repair',genome_id=committed_genome.id,trial=trial))
        else:
            rejected.append(tuple(patch));totals['operator_rejected']+=1
        if raw_gain<0:totals['raw_negative_proposals']+=1
        if child_details['status']!='complete':totals['trial_timeout_or_error']+=1
        cert_fit=None
        if trial%32==0 and time.process_time()<deadline:
            local_adj={v:graph.adjacency[v]&patch for v in patch}
            first=max(patch,key=lambda v:(graph.weights[v],v))
            competitors=local_adj[first]
            roots=[first,max(competitors,key=lambda v:(graph.weights[v],v))] if competitors else sorted(patch)[:2]
            bounds=local_certificates(local_adj,graph.weights,patch,roots,deadline=min(deadline,time.process_time()+.003))
            try:
                ev=PatchEvaluator(local_adj,graph.weights,genome.recipe,genome.coefficients,patch,patch,graph.metadata,min(deadline,time.process_time()+.003))
                values={v:ev.feature_values(v) for v in roots}
                coordinate_names=('weight','duration','degree','conflict_weight','max_conflict_weight','compatible_weight',
                    'station_gap','satellite_gap','remaining_count')+tuple(f['name'] for f in genome.features)
                vectors={v:tuple(values[v][k] for k in coordinate_names) for v in roots}
                boundary=dict(fixed_outside=sorted(fixed_outside),active_patch=sorted(patch),
                    excluded_count=len(graph.weights)-len(fixed_outside)-len(patch),
                    edges=sorted((a,b) for a in patch for b in local_adj[a] if a<b))
                for row in bounds['pairs']:row['boundary_commitments']=boundary
                key=genome.representation_hash
                if key not in archives:
                    if len(archives)>=16:archives.pop(next(iter(archives)))
                    archives[key]=EvidenceArchive(max_contexts=16)
                gate=archives[key].add(f'{instance_id}:trial{trial}',vectors,bounds['pairs'])
                gate.update(representation_hash=key,coordinate_names=list(coordinate_names))
                if gate.get('has_cycle'):
                    controller.notify_cycle(f'trial{trial}',{**gate,'instance_id':instance_id})
                pairs=[r for r in bounds['pairs'] if r.get('preferred_root') is not None]
                if pairs:cert_fit=sum(ev.score(r['preferred_root'])>ev.score(r['b'] if r['preferred_root']==r['a'] else r['a']) for r in pairs)/len(pairs)
                certificates.append(dict(trial=trial,bounds=bounds,archive_gate=gate,fit=cert_fit))
            except TimeoutError:
                certificates.append(dict(trial=trial,bounds=bounds,feature_diagnostic_timeout=True))
        duration=time.process_time()-trial_start
        # An incomplete prefix also loses objective after the destroy operation.
        # Its signed raw loss is retained in round2 instead of a zero credit.
        observed_gain=raw_gain if controller_config or child_details['status']=='complete' else 0
        controller.observe(genome.id,observed_gain,removed,max(1e-9,duration-(race['parent_cpu_seconds'] if race else 0)),cert_fit=cert_fit)
        totals['operator_attempts']+=1;totals['rank_commits']+=child_details['rank_commits']+(race['parent_rank_commits'] if race else 0)
        logs.append(dict(trial=trial,genome_id=genome.id,program_hash=genome.program_hash,
            recipe_name=genome.recipe['name'],coefficients=genome.coefficients,
            patch=patch_detail,removed_ticks=removed,raw_gain_ticks=raw_gain,
            accepted=accepted,child_accepted=accepted and committed_genome.id==genome.id,
            committed_genome_id=committed_genome.id,
            accepted_gain_ticks=selected_gain if accepted else 0,paired_race=race,
            accepted_proposal_details=details if accepted else None,
            cpu_seconds=duration,cert_fit=cert_fit,**child_details))
    final_check=feasible(graph,state.selected)
    if not final_check:raise AssertionError('Final graph feasibility failed')
    # Final mandatory check is charged even when it creates soft overshoot.
    summary=controller.snapshot();summary['events']=events
    return dict(version='stk_online_llm_v2',instance_id=instance_id,seed=seed,mode=mode,
        budget_cpu_seconds=seconds,cpu_seconds=time.process_time()-started,wall_seconds=time.perf_counter()-wall,
        seed_value_ticks=seed_value,value_ticks=state.value,value_exact=str(Fraction(state.value,1000000)),
        selected=sorted(state.selected),selected_contact_ids=[graph.contact_ids[x] for x in sorted(state.selected)],
        feasible=final_check,stats=dict(totals),best_so_far=curve,trials=logs,
        controller=summary,certificates=certificates,online_llm_calls=0,external_oracle_calls=0,
        conditional_local_bound_calls=len(certificates),
        attribution='operator_repair includes LLM location/ranking and optional common local exchange; those components have separate logged gains. Internal local bounds are separate and their solutions are not committed.',
        policy_reset_at_instance_start=True)
