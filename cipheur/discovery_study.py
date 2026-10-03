"""Independent proposal-batch comparison with development-only program selection."""
from __future__ import annotations
import argparse,ast,json,time,statistics,re
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ProcessPoolExecutor,as_completed
from .graph_features import FeatureRuleProgram,NEIGHBOR_EDGE_MIN,NEIGHBOR_EDGE_COUNT
from .compiled import schedule_compiled
from .model import Graph
from .representation import diagnose_representation,ranking_report
from .refinement import minimum_cost_refinement
from .scale_study import write

def enumeration():
    neighbor={'op':'neighbors','args':[{'op':'root','args':[]}]}
    catalogue=[('edge_count',NEIGHBOR_EDGE_COUNT),('edge_min',NEIGHBOR_EDGE_MIN),
       ('cover',{'op':'clique_cover_weight','args':[neighbor]}),
       ('greedy',{'op':'greedy_independent_weight','args':[neighbor]})]
    result=[]
    for name,expression in catalogue:
        for k,rule in enumerate(['weight/max(1,f)','weight-0.25*f','weight-0.6*conflict_weight+f/max(1,degree)',
                               'weight/max(1,degree-2*f/max(1,conflict_weight))',
                               'weight/(1+degree)+0.1*f/max(1,conflict_weight)',
                               'weight/(1+conflict_weight/max(1,weight))-0.1*f']):
            result.append({'name':f'enum_{name}_{k}','features':[{'name':'f','expression':expression}],
                           'rule':rule,'rationale':'Prespecified deterministic expression enumeration.'})
    return result

def assess(item):
    arm,index,source,specs,validation,references=item
    started=time.perf_counter();program=FeatureRuleProgram.from_dict(source)
    consistency=ranking_report(program,specs);diagnosis=diagnose_representation(program,specs)
    rows=[]
    for pair in validation:
        for side in ('left','right'):
            graph=Graph.from_dict(pair[side]);begin=time.perf_counter()
            result=schedule_compiled(graph,program,pair['fixed'],pair['excluded'])
            key=pair['id']+':'+side;reference=references[key]
            upper=reference.get('upper')
            rows.append({'id':pair['id'],'side':side,'family':pair['family'],'n':len(graph.nodes),
                'value':result['value'],'ratio':result['value']/upper if upper else None,
                'feature_work':result['feature_work'],'seconds':time.perf_counter()-begin,
                'feasible':result['feasible'],'selected':result['selected']})
    valid=[r for r in rows if r['ratio'] is not None]
    return {'arm':arm,'index':index,'name':program.name,'program':program.to_dict(),
        'consistency':consistency['fraction'],'contradictory':diagnosis['contradictory'],
        'quality':statistics.fmean(r['ratio'] for r in valid),
        'feature_work':statistics.fmean(r['feature_work'] for r in rows),
        'seconds':time.perf_counter()-started,'rows':rows}

def run(data_path,scale_results,discovery,output,workers):
    root=Path(output)
    if root.exists():raise ValueError('Fresh output required')
    root.mkdir(parents=True);disc=Path(discovery)
    data=json.loads(Path(data_path).read_text(encoding='utf-8'));assert 'test' not in data
    specs=json.loads((disc/'seed_specifications.json').read_text(encoding='utf-8'))
    validation=[p for p in data['validation'] if len(p['left']['contacts'])<=128]
    references={}
    for line in Path(scale_results).read_text(encoding='utf-8').splitlines():
        row=json.loads(line)
        if row['split']=='validation':references[row['id']+':'+row['side']]=row['reference']
    banks={arm:json.loads((disc/(arm+'_batch.json')).read_text(encoding='utf-8'))['candidates']
           for arm in ('guided','free','rule')}
    banks['enumerated']=enumeration()
    if any(len(bank)!=24 for bank in banks.values()):raise ValueError('Matched candidate budget must be 24')
    write(root/'candidate_banks.json',banks)
    catalogue=[];seen=set()
    for candidate in banks['guided']:
        for feature in candidate['features']:
            encoded=json.dumps(feature['expression'],sort_keys=True,separators=(',',':'))
            if encoded not in seen:
                seen.add(encoded);catalogue.append({'name':f'catalogue_{len(catalogue)}','expression':feature['expression']})
    # Catalogue masters are exact only for finite small libraries. A bound is
    # declared instead of silently claiming global minimum after truncation.
    repair=minimum_cost_refinement(FeatureRuleProgram('base',[],'weight'),specs,catalogue,
                                   max_master_subsets=500000,max_rounds=64)
    write(root/'representation_repair.json',repair)
    selected_shapes={json.dumps(f['expression'],sort_keys=True,separators=(',',':')) for f in repair['selected_features']}
    tasks=[(arm,i,c,specs,validation,references) for arm,bank in banks.items() for i,c in enumerate(bank)]
    tasks.append(('baseline',0,FeatureRuleProgram('cost_reference',[],'weight/max(1,degree)').to_dict(),
                   specs,validation,references))
    assessments=[]
    with ProcessPoolExecutor(max_workers=workers) as pool, (root/'candidate_assessments.jsonl').open('w',encoding='utf-8') as stream:
        for f in as_completed([pool.submit(assess,t) for t in tasks]):
            row=f.result();assessments.append(row);stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
            print(json.dumps({'assessed':len(assessments),'total':len(tasks)}),flush=True)
    c_ref=next(r['feature_work'] for r in assessments if r['arm']=='baseline')
    selected={};curves=[]
    for arm in banks:
        for prefix in (8,16,24):
            candidates=[r for r in assessments if r['arm']==arm and r['index']<prefix]
            for r in candidates:r['utility']=r['quality']-.002*(r['feature_work']/max(1,c_ref)-1)
            if arm=='guided':
                candidates=[r for r in candidates if not r['contradictory'] and r['consistency']>=.75 and
                   {json.dumps(f['expression'],sort_keys=True,separators=(',',':')) for f in r['program']['features']}<=selected_shapes]
            else:candidates=[r for r in candidates if r['consistency']>=.75 or arm=='rule']
            chosen=max(candidates,key=lambda r:(r['utility'],r['quality'],-r['feature_work'],-r['index'])) if candidates else None
            curves.append({'arm':arm,'budget':prefix,'eligible':len(candidates),
                'name':chosen['name'] if chosen else None,'quality':chosen['quality'] if chosen else None,
                'consistency':chosen['consistency'] if chosen else None,'work':chosen['feature_work'] if chosen else None})
            if prefix==24 and chosen:selected[arm]=chosen['program']
    # Factorial selection controls use the same guided proposals, separated from
    # the independent GENERATION comparison above.
    guided=[r for r in assessments if r['arm']=='guided']
    for label,pool,penalty in [('guided_no_cost',guided,0.),('guided_no_consistency',guided,.002),
                              ('guided_no_master',guided,.002)]:
        if label!='guided_no_consistency':pool=[r for r in pool if r['consistency']>=.75 and not r['contradictory']]
        if pool:
            chosen=max(pool,key=lambda r:(r['quality']-penalty*(r['feature_work']/max(1,c_ref)-1),-r['index']))
            selected[label]=chosen['program']
    write(root/'discovery_curves.json',curves)
    write(root/'frozen_programs.json',{'programs':selected,'test_accessed':False,
        'candidate_budget_per_arm':24,'assistant_generation_calls_per_arm':1,'API_calls':0,
        'selection':{'lambda':.002,'tau':.75,'validation_max_n':128,'guided_exact_selected_interface':True},
        'known_scope':'one_assistant_batch_per_arm_no_token_count_available',
        'input_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in [Path(data_path),Path(scale_results),
                            disc/'seed_specifications.json',disc/'guided_batch.json',disc/'free_batch.json',disc/'rule_batch.json']}})
    write(root/'complete.json',{'assessed':len(assessments),'validation_contexts':2*len(validation),
        'selected':{arm:p['name'] for arm,p in selected.items()},'repair_optimal':repair['optimal'],
        'repair_names':repair['selected_names']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--scale-results',required=True)
    p.add_argument('--discovery',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();run(a.data,a.scale_results,a.discovery,a.output,a.workers)
