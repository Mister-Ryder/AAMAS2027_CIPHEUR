"""Explicit weighted independent-set comparison algorithms and MILP reference."""
from __future__ import annotations
from itertools import combinations
import time, math
from .graph_features import FeatureRuleProgram, schedule_feature_program

def swap_search(graph,initial,fixed=(),excluded=(),max_rounds=100,seconds=2.):
    """Deterministic improving 1->1 and 1->2 swaps, followed by maximal completion."""
    started=time.perf_counter()
    selected=set(initial); fixed=set(fixed); legal=graph.available(fixed,excluded)
    iterations=0
    while iterations<max_rounds and time.perf_counter()-started<seconds:
        iterations+=1
        best=None
        outside=sorted(legal-selected)
        blockers={v:graph.adj[v]&selected for v in outside}
        for v in outside:
            if blockers[v]&fixed: continue
            gain=graph.nodes[v].weight-graph.value(blockers[v])
            if gain>1e-9:
                candidate=(gain,(v,),tuple(sorted(blockers[v])))
                if best is None or candidate>best: best=candidate
        # Each member replaces the same single incumbent or nothing. No quadratic
        # all-pairs construction for unrelated nodes; this is a named 1->2 baseline.
        groups={}
        for v in outside:
            if len(blockers[v])<=1 and not blockers[v]&fixed:
                groups.setdefault(tuple(sorted(blockers[v])),[]).append(v)
        for removed, pool in groups.items():
            for a,b in combinations(pool,2):
                if time.perf_counter()-started>=seconds: break
                if b in graph.adj[a]: continue
                gain=graph.nodes[a].weight+graph.nodes[b].weight-graph.value(removed)
                if gain>1e-9:
                    candidate=(gain,(a,b),removed)
                    if best is None or candidate>best: best=candidate
        if best is None: break
        _,added,removed=best
        selected.difference_update(removed);selected.update(added)
        for v in sorted(legal-selected,key=lambda v:(-graph.nodes[v].weight,v)):
            if not graph.adj[v]&selected: selected.add(v)
    assert graph.feasible(selected)
    return {'selected':sorted(selected),'value':graph.value(selected),'feasible':True,
            'iterations':iterations,'seconds':time.perf_counter()-started}

def milp_reference(graph,fixed=(),excluded=(),seconds=10.):
    """HiGHS MILP comparator; floating solver gaps are not formal certificates."""
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import csc_matrix
    nodes=sorted(graph.available(fixed,excluded)); index={v:i for i,v in enumerate(nodes)}
    if not nodes:
        value=graph.value(fixed)
        return {'lower':value,'upper':value,'selected':list(fixed),'solver_status':0,
                'mip_gap':0.,'exact':False,'scope':'floating_milp_reference'}
    rows=[];columns=[];values=[];r=0
    for a,b in sorted(graph.edges):
        if a in index and b in index:
            rows.extend((r,r));columns.extend((index[a],index[b]));values.extend((1.,1.));r+=1
    matrix=csc_matrix((values,(rows,columns)),shape=(r,len(nodes)))
    constraints=LinearConstraint(matrix,-np.inf,np.ones(r)) if r else None
    weights=np.asarray([graph.nodes[v].weight for v in nodes],dtype=float)
    result=milp(-weights,integrality=np.ones(len(nodes)),bounds=Bounds(0,1),
                constraints=constraints,options={'time_limit':seconds,'mip_rel_gap':1e-7,'threads':1})
    selected=list(fixed)
    if result.x is not None: selected.extend(v for v,x in zip(nodes,result.x) if x>.5)
    if not graph.feasible(selected): raise AssertionError('MILP returned infeasible selection')
    lower=graph.value(selected)
    dual=getattr(result,'mip_dual_bound',None)
    upper=graph.value(fixed)-float(dual) if dual is not None and math.isfinite(dual) else None
    return {'lower':lower,'upper':upper,'selected':sorted(selected),'solver_status':int(result.status),
            'mip_gap':float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None,
            'exact':False,'scope':'floating_milp_reference','feasible':True}
