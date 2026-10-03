"""Offline actual-next-action regret intervals for an immutable program bank."""
import argparse,json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from .scale_study import write
from .graph_features import FeatureRuleProgram
from .residual_evidence import evidence_relevance

def task(item):
    name,raw,specs,nodes=item
    return name,evidence_relevance(FeatureRuleProgram.from_dict(raw),specs,regret_nodes=nodes)

def run(frozen,specifications,output,nodes,workers):
    root=Path(output)
    if root.exists():raise ValueError('Fresh output required')
    root.mkdir(parents=True)
    bank=json.loads(Path(frozen).read_text())['programs']
    specs=json.loads(Path(specifications).read_text())
    selected={k:bank[k] for k in ('guided','free','rule','enumerated','guided_minimum_interface','guided_no_cost','guided_natural_validation')}
    selected['weight']=FeatureRuleProgram('weight',[],'weight').to_dict()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for f in as_completed([pool.submit(task,(k,v,specs,nodes)) for k,v in selected.items()]):
            name,report=f.result();write(root/(name+'.json'),report)
            print(json.dumps({'completed':name}),flush=True)
    write(root/'complete.json',{'programs':len(selected),'specifications':len(specs),
          'branch_nodes_per_reference':nodes,'labels_used_for_selection':False,
          'scope':'Offline evaluation of actual choices, including pair escape; not online deployment calls.'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frozen',required=True);p.add_argument('--specifications',required=True)
    p.add_argument('--output',required=True);p.add_argument('--nodes',type=int,default=1000);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();run(a.frozen,a.specifications,a.output,a.nodes,a.workers)
