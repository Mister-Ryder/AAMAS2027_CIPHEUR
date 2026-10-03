"""Parallel graph-scale screening. Results are append-only, one task per graph."""
from __future__ import annotations
import argparse,json,time,os,sys,platform
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ProcessPoolExecutor,as_completed
from .study_data import build_study
from .graph_features import FeatureRuleProgram,schedule_feature_program,NEIGHBOR_EDGE_MIN,NEIGHBOR_EDGE_COUNT
from .strong_baselines import swap_search,milp_reference
from .model import Graph

def write(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def methods():
    return [FeatureRuleProgram('weight',[],'weight'),
        FeatureRuleProgram('degree',[],'weight/max(1,degree)'),
        FeatureRuleProgram('weighted_conflict',[],'weight/max(1,conflict_weight)'),
        FeatureRuleProgram('v02_joint',[{'name':'redundancy','expression':NEIGHBOR_EDGE_MIN}],
                           'weight-0.6*conflict_weight+redundancy/max(1,degree)'),
        FeatureRuleProgram('structural_ratio',[{'name':'triangles','expression':NEIGHBOR_EDGE_COUNT}],
                           'weight/max(1,degree-2*triangles/max(1,degree))')]

def task(item):
    pair,side,config=item
    graph=Graph.from_dict(pair[side]); rows=[]
    if config.get('backend')=='compiled':
        from .compiled import schedule_compiled
        execute=schedule_compiled
    else:
        execute=schedule_feature_program
    for program in methods():
        started=time.perf_counter()
        result=execute(graph,program,pair['fixed'],pair['excluded'])
        rows.append({'method':program.name,'value':result['value'],'selected':result['selected'],
            'feasible':result['feasible'],'seconds':time.perf_counter()-started,
            'feature_work':result['feature_work']})
    initial=max(rows,key=lambda r:r['value'])
    improved=swap_search(graph,initial['selected'],pair['fixed'],pair['excluded'],
                         seconds=config.get('local_search_seconds',2))
    rows.append({'method':'multi_start_1to2_search',**improved,'feature_work':None})
    started=time.perf_counter()
    try:
        reference=milp_reference(graph,pair['fixed'],pair['excluded'],seconds=config.get('milp_seconds',10))
        reference['seconds']=time.perf_counter()-started
        rows.append({'method':'HiGHS_MILP',**reference,'value':reference['lower'],'feature_work':None})
    except Exception as error:
        reference={'error':type(error).__name__,'message':str(error),'scope':'floating_milp_reference'}
    return {'id':pair['id'],'split':pair['source']['split'],'side':side,'family':pair['family'],
        'n':len(graph.nodes),'m':len(graph.edges),'graph_sha256':graph.digest(),
        'changed_edges':len(Graph.from_dict(pair['left']).edges^Graph.from_dict(pair['right']).edges),
        'methods':rows,'reference':reference}

def run(config_path,output,splits,workers):
    config=json.loads(Path(config_path).read_text(encoding='utf-8'))
    root=Path(output)
    if root.exists(): raise ValueError('Preserve previous run: choose a fresh output')
    root.mkdir(parents=True)
    suite=build_study(config)
    write(root/'config.json',config);write(root/'data_protocol.json',suite['protocol'])
    serial={s:[{**p,'left':p['left'].to_dict(),'right':p['right'].to_dict()} for p in suite[s]] for s in splits}
    write(root/'data.json',serial)
    source={p.name:sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    write(root/'execution.json',{'python':sys.version,'platform':platform.platform(),'workers':workers,
        'source_sha256':source,'splits':splits,'test_accessed':'test' in splits,
        'interpretation':'development_screening' if 'test' not in splits else 'frozen_holdout_evaluation'})
    tasks=[(p,side,config) for s in splits for p in serial[s] for side in ('left','right')]
    count=0; started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool, (root/'results.jsonl').open('w',encoding='utf-8') as stream:
        futures=[pool.submit(task,t) for t in tasks]
        for future in as_completed(futures):
            row=future.result();stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
            count+=1
            if count%10==0 or count==len(tasks):
                write(root/'progress.json',{'completed':count,'total':len(tasks),'seconds':time.perf_counter()-started})
                print(json.dumps({'completed':count,'total':len(tasks)}),flush=True)
    write(root/'complete.json',{'completed':count,'total':len(tasks),'seconds':time.perf_counter()-started,
        'results_sha256':sha256((root/'results.jsonl').read_bytes()).hexdigest()})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--splits',nargs='+',default=['train','validation']);parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args();run(args.config,args.output,args.splits,args.workers)
