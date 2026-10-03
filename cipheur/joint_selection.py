"""Prespecified full-pair utility and transfer controls, frozen before test.

The minimum-interface pool is an ablation: additive representation cost alone
must not prohibit a more expensive but useful representation--rule pair.
"""
import argparse,json,statistics
from pathlib import Path
from hashlib import sha256
from .scale_study import write

def freeze(discovery,output):
    root=Path(discovery)
    original=json.loads((root/'frozen_programs.json').read_text())
    rows=[json.loads(s) for s in (root/'candidate_assessments.jsonl').read_text().splitlines()]
    cref=next(r['feature_work'] for r in rows if r['arm']=='baseline')
    programs=dict(original['programs']);programs['guided_minimum_interface']=programs.pop('guided')
    selected=[]
    def choose(label,arm,penalty=.002,max_features=6,natural=False):
        pool=[r for r in rows if r['arm']==arm and (arm=='rule' or (r['consistency']>=.75 and not r['contradictory']))
              and len(r['program']['features'])<=max_features]
        def quality(r):
            rr=[x['ratio'] for x in r['rows'] if x['ratio'] is not None and (not natural or x['family']!='diagnostic')]
            return statistics.fmean(rr)
        if not pool:
            selected.append({'label':label,'eligible':0});return
        winner=max(pool,key=lambda r:(quality(r)-penalty*(r['feature_work']/max(1,cref)-1),quality(r),-r['feature_work'],-r['index']))
        programs[label]=winner['program']
        selected.append({'label':label,'eligible':len(pool),'program':winner['name'],'quality':quality(winner),
                        'work':winner['feature_work'],'consistency':winner['consistency'],'lambda':penalty,
                        'feature_limit':max_features,'natural_validation_only':natural})
    choose('guided','guided')
    # Same representation/consistency gate for the free-generation comparison.
    choose('free','free');choose('enumerated','enumerated')
    choose('guided_low_penalty','guided',.0005);choose('guided_high_penalty','guided',.008)
    choose('guided_one_feature','guided',max_features=1)
    choose('guided_natural_validation','guided',natural=True)
    curves=[]
    for arm in ('guided','free','rule','enumerated'):
        for prefix in (8,16,24):
            pool=[r for r in rows if r['arm']==arm and r['index']<prefix and
                  (arm=='rule' or (r['consistency']>=.75 and not r['contradictory']))]
            w=max(pool,key=lambda r:(r['quality']-.002*(r['feature_work']/max(1,cref)-1),r['quality'],-r['feature_work'],-r['index'])) if pool else None
            curves.append({'arm':arm,'budget':prefix,'eligible':len(pool),'name':w['name'] if w else None,
                           'quality':w['quality'] if w else None,'work':w['feature_work'] if w else None,
                           'consistency':w['consistency'] if w else None})
    write(output,{**original,'programs':programs,'selection':{'lambda':.002,'tau':.75,'validation_max_n':128,
        'joint_feature_rule_utility':True,'minimum_interface_is_ablation':True,'matched_candidate_counts':True},
        'selection_details':selected,'joint_prefix_curves':curves,
        'input_assessments_sha256':sha256((root/'candidate_assessments.jsonl').read_bytes()).hexdigest(),
        'protocol':'Declared before opening any test outcome; no new candidate generation.'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--discovery',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();freeze(a.discovery,a.output)
