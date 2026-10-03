"""Controlled evidence/bound/refinement/runtime development experiments."""
from __future__ import annotations
import json,argparse,time,sys,platform
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ProcessPoolExecutor,as_completed
from .model import Graph
from .graph_features import FeatureRuleProgram,schedule_feature_program,NEIGHBOR_EDGE_MIN,NEIGHBOR_EDGE_COUNT
from .compiled import schedule_compiled
from .oracle import Budget
from .residual_evidence import acquire_rollout_evidence,evidence_relevance
from .refinement import minimum_cost_refinement
from .representation import diagnose_representation,ranking_report
from .scale_study import write

def evidence_task(item):
    pair,strategy,upper_method=item
    program=FeatureRuleProgram('weight_anchor',[],'weight')
    budget=Budget(max_calls=40,max_nodes=8000)
    started=time.perf_counter()
    specs,attempts=acquire_rollout_evidence([pair],program,budget,strategy=strategy,
        max_steps=2,max_attempts=4,max_witnesses=2,nodes_per_call=500,max_region=128,
        upper_method=upper_method,seed=41)
    for i,spec in enumerate(specs):
        spec.update(id=pair['id']+f'_{strategy}_{upper_method}_{i}',family=pair['family'])
    return {'id':pair['id'],'family':pair['family'],'n':len(pair['left']['contacts']),
        'strategy':strategy,'upper_method':upper_method,'specifications':specs,
        'attempts':attempts,'budget':budget.to_dict(),'seconds':time.perf_counter()-started}

def runtime_task(pair):
    program=FeatureRuleProgram('structural_runtime',[{'name':'redundancy','expression':NEIGHBOR_EDGE_MIN}],
        'weight-0.6*conflict_weight+redundancy/max(1,degree)')
    rows=[]
    for side in ('left','right'):
        graph=Graph.from_dict(pair[side]);runs=[]
        for repetition in range(3):
            order=[('reference',schedule_feature_program),('compiled',schedule_compiled)]
            if repetition%2:order.reverse()
            for backend,fn in order:
                started=time.perf_counter();result=fn(graph,program,pair['fixed'],pair['excluded'])
                runs.append({'backend':backend,'repetition':repetition,'seconds':time.perf_counter()-started,
                    'feature_work':result['feature_work'],'selected':result['selected'],'trace':result['trace'],
                    'value':result['value'],'feasible':result['feasible'],
                    'update_work':result.get('update_work'),'query_work':result.get('query_work'),
                    'initialization_work':result.get('initialization_work')})
        assert all(r['trace']==runs[0]['trace'] for r in runs)
        rows.append({'id':pair['id'],'side':side,'family':pair['family'],'n':len(graph.nodes),
                    'm':len(graph.edges),'equivalent_traces':True,'runs':runs})
    return rows

def run(data_path,output,workers):
    root=Path(output)
    if root.exists():raise ValueError('Fresh output required')
    root.mkdir(parents=True)
    data=json.loads(Path(data_path).read_text(encoding='utf-8'))
    train=data['train'];assert 'test' not in data
    write(root/'execution.json',{'python':sys.version,'platform':platform.platform(),
        'data_sha256':sha256(Path(data_path).read_bytes()).hexdigest(),'test_accessed':False,
        'source_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}})
    # These are prespecified size/identity filters, with no performance selection.
    evidence_pairs=[p for p in train if len(p['left']['contacts'])<=128]
    evidence_jobs=[(p,strategy,upper) for p in evidence_pairs
        for strategy,upper in [('anchored','weighted_clique_cover'),('uniform','weighted_clique_cover'),
                               ('anchored','weight_sum')]]
    specs=[];evidence=[]
    with ProcessPoolExecutor(max_workers=workers) as pool, (root/'evidence_results.jsonl').open('w',encoding='utf-8') as stream:
        for future in as_completed([pool.submit(evidence_task,t) for t in evidence_jobs]):
            row=future.result();stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush();evidence.append(row)
            if row['strategy']=='anchored' and row['upper_method']=='weighted_clique_cover':
                specs.extend(row['specifications'])
            if len(evidence)%10==0: print(json.dumps({'evidence_completed':len(evidence),'total':len(evidence_jobs)}),flush=True)
    specs.sort(key=lambda s:s['id']);write(root/'train_specifications.json',specs)
    base=FeatureRuleProgram('base',[],'weight')
    catalogue=[{'name':'neigh_edges','expression':NEIGHBOR_EDGE_COUNT},
               {'name':'neigh_min','expression':NEIGHBOR_EDGE_MIN},
               {'name':'neigh_cover','expression':{'op':'clique_cover_weight','args':[
                    {'op':'neighbors','args':[{'op':'root','args':[]}]}]}},
               {'name':'neigh_greedy','expression':{'op':'greedy_independent_weight','args':[
                    {'op':'neighbors','args':[{'op':'root','args':[]}]}]}}]
    diagnosis=diagnose_representation(base,specs)
    repair=minimum_cost_refinement(base,specs,catalogue)
    write(root/'initial_diagnosis.json',diagnosis);write(root/'repair.json',repair)
    write(root/'catalogue.json',catalogue)
    # Repeat timings with reversed order, retaining traces and all phase work.
    runtime_pairs=[p for p in data['validation'] if p['family']!='diagnostic']
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool, (root/'runtime_results.jsonl').open('w',encoding='utf-8') as stream:
        for future in as_completed([pool.submit(runtime_task,p) for p in runtime_pairs]):
            for row in future.result():rows.append(row);stream.write(json.dumps(row,allow_nan=False)+'\n')
            stream.flush()
            if len(rows)%20==0:print(json.dumps({'runtime_contexts':len(rows),'total':2*len(runtime_pairs)}),flush=True)
    write(root/'complete.json',{'evidence_tasks':len(evidence),'specifications':len(specs),
        'runtime_contexts':len(rows),'contradictory':diagnosis['contradictory'],
        'repair_names':repair['selected_names'],'repair_optimal':repair['optimal']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--output',required=True)
    p.add_argument('--workers',type=int,default=8);a=p.parse_args();run(a.data,a.output,a.workers)
