"""Evaluate immutable selected programs once on predeclared held-out pairs.

No candidate generation, ranking feedback, or selection occurs in this module.
Additional offline evidence is returned for evaluation only.
"""
from __future__ import annotations
import argparse,json,time,sys,platform
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ProcessPoolExecutor,as_completed
from .model import Graph
from .study_data import build_study
from .scale_study import write,methods
from .graph_features import FeatureRuleProgram
from .compiled import schedule_compiled
from .strong_baselines import swap_search,milp_reference
from .source_audit import check_source_graph

class ProgramBudgetExceeded(TimeoutError):pass

class BudgetMeter(dict):
    """Cooperative measurement guard at charged-work updates, without signals."""
    def __init__(self,seconds):
        super().__init__();self.deadline=time.process_time()+seconds;self.writes=0
    def __setitem__(self,key,value):
        self.writes+=1
        if self.writes%256==0 and time.process_time()>self.deadline:
            raise ProgramBudgetExceeded('Declared program CPU budget exceeded')
        return super().__setitem__(key,value)

def execute_with_budget(graph,program,fixed,excluded,seconds=None,score_slice=False):
    """External measurement limit; never repair, replace, or resume a program."""
    if seconds is None:return schedule_compiled(graph,program,fixed,excluded,score_slice=score_slice)
    return schedule_compiled(graph,program,fixed,excluded,meter=BudgetMeter(seconds),score_slice=score_slice)

def task(item):
    pair,side,config,programs=item
    graph=Graph.from_dict(pair[side]); rows=[]
    for name,raw in programs.items():
        program=FeatureRuleProgram.from_dict(raw); start=time.perf_counter()
        cpu_start=time.process_time()
        try:result=execute_with_budget(graph,program,pair['fixed'],pair['excluded'],config.get('program_cpu_seconds'),config.get('score_slice',False))
        except ProgramBudgetExceeded:
            rows.append({'method':name,'program_name':program.name,'value':None,'selected':None,
                'feasible':None,'completed':False,'status':'CPU_budget_exceeded',
                'cpu_seconds':time.process_time()-cpu_start,'seconds':time.perf_counter()-start,
                'feature_work':None})
            continue
        if not result['feasible']:raise AssertionError('Frozen program infeasible')
        rows.append({'method':name,'program_name':program.name,'value':result['value'],
            'selected':result['selected'],'feasible':True,'completed':True,'cpu_seconds':time.process_time()-cpu_start,'seconds':time.perf_counter()-start,
            'feature_work':result['feature_work'],'compilation':result.get('compilation')})
    # The local-search comparator starts from classical fixed baselines only;
    # it never benefits from the evaluated generated programs.
    fixed_rows=[r for r in rows if r['method'].startswith('baseline_') and r['completed']]
    if fixed_rows:
        initial=max(fixed_rows,key=lambda r:r['value'])
        improved=swap_search(graph,initial['selected'],pair['fixed'],pair['excluded'],
                             seconds=config.get('local_search_seconds',2))
        improved.update({'completed':True,'initial_method':initial['method']})
    else:
        improved={'value':None,'selected':None,'feasible':None,'completed':False,
                  'status':'no_completed_classical_initialization','seconds':0.0}
    rows.append({'method':'multi_start_1to2_search',**improved,'feature_work':None})
    start=time.perf_counter()
    reference=milp_reference(graph,pair['fixed'],pair['excluded'],seconds=config.get('milp_seconds',10))
    reference['seconds']=time.perf_counter()-start
    rows.append({'method':'HiGHS_MILP',**reference,'value':reference['lower'],'feature_work':None})
    audit=check_source_graph(graph,{r['method']:r['selected'] for r in rows if r['selected'] is not None},config['stable_root']) if pair['family']=='c3' else {'applicable':False}
    return {'id':pair['id'],'split':'test','side':side,'family':pair['family'],
        'n':len(graph.nodes),'m':len(graph.edges),'graph_sha256':graph.digest(),
        'cluster':str(pair['source'].get('seed')) if pair['source'].get('seed') is not None else pair['id'],
        'changed_edges':len(Graph.from_dict(pair['left']).edges^Graph.from_dict(pair['right']).edges),
        'methods':rows,'reference':reference,'source_verifier':audit}

def evidence_task(item):
    pair,programs=item
    from .oracle import Budget
    from .residual_evidence import acquire_rollout_evidence,evidence_relevance
    from .representation import diagnose_representation,ranking_report
    base=FeatureRuleProgram('evidence_anchor',[],'weight')
    budget=Budget(max_calls=40,max_nodes=8000)
    specs,attempts=acquire_rollout_evidence([pair],base,budget,max_steps=1,max_attempts=2,
                  max_witnesses=1,nodes_per_call=500,max_region=128)
    reports={}
    for name,raw in programs.items():
        # Evidence needs only primary generation arms and fixed baselines;
        # whole-residual expensive selection controls are assessed by schedules.
        if name not in ('guided','free','rule','enumerated','baseline_weight','baseline_degree'):continue
        p=FeatureRuleProgram.from_dict(raw)
        reports[name]={'ranking':ranking_report(p,specs),'quotient':diagnose_representation(p,specs),
                       'relevance':evidence_relevance(p,specs)}
    return {'id':pair['id'],'family':pair['family'],'specifications':specs,'attempts':attempts,
            'budget':budget.to_dict(),'reports':reports}

def run(config_path,frozen_path,output,workers):
    config=json.loads(Path(config_path).read_text(encoding='utf-8'))
    freeze=json.loads(Path(frozen_path).read_text(encoding='utf-8'))
    if freeze.get('test_accessed') is not False:raise ValueError('Require pre-test program freeze')
    root=Path(output)
    if root.exists():raise ValueError('Fresh output required')
    root.mkdir(parents=True)
    programs={k:v for k,v in freeze['programs'].items()}
    for p in methods():programs['baseline_'+p.name]=p.to_dict()
    write(root/'programs.json',programs);write(root/'config.json',config)
    write(root/'execution.json',{'python':sys.version,'platform':platform.platform(),'workers':workers,
        'selection_permitted':False,'frozen_sha256':sha256(Path(frozen_path).read_bytes()).hexdigest(),
        'source_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}})
    suite=build_study(config);write(root/'data_protocol.json',suite['protocol'])
    pairs=[{**p,'left':p['left'].to_dict(),'right':p['right'].to_dict()} for p in suite['test']]
    write(root/'data.json',{'test':pairs})
    start=time.perf_counter();count=0
    tasks=[(p,side,config,programs) for p in pairs for side in ('left','right')]
    with ProcessPoolExecutor(max_workers=workers) as pool,(root/'results.jsonl').open('w',encoding='utf-8') as out:
        for f in as_completed([pool.submit(task,t) for t in tasks]):
            row=f.result();out.write(json.dumps(row,allow_nan=False)+'\n');out.flush();count+=1
            if count%10==0 or count==len(tasks):
                write(root/'progress.json',{'completed':count,'total':len(tasks),'seconds':time.perf_counter()-start})
                print(json.dumps({'completed':count,'total':len(tasks)}),flush=True)
    eligible=[p for p in pairs if len(p['left']['contacts'])<=128]
    with ProcessPoolExecutor(max_workers=workers) as pool,(root/'test_evidence.jsonl').open('w',encoding='utf-8') as out:
        for f in as_completed([pool.submit(evidence_task,(p,programs)) for p in eligible]):
            out.write(json.dumps(f.result(),allow_nan=False)+'\n');out.flush()
    write(root/'complete.json',{'completed':count,'test_pairs':len(pairs),'evidence_pairs':len(eligible),
        'seconds':time.perf_counter()-start,'selection_permitted':False,
        'results_sha256':sha256((root/'results.jsonl').read_bytes()).hexdigest()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--frozen',required=True)
    p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();run(a.config,a.frozen,a.output,a.workers)
