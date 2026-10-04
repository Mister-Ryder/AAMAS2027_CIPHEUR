"""Check original opportunity overlap and candidate chronological splits.

This reads supplied contact inputs, not schedules or decision labels. It does
not generate a graph, run an optimizer, select an algorithm, or infer that an
input distribution activates the proposed representation mechanism.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

def load(path):
    raw=path.read_bytes()
    text=raw.decode('gb18030',errors='strict')
    reader=csv.reader(text.splitlines())
    header=next(reader); keys=[]
    for line,row in enumerate(reader,2):
        if len(row)!=12:raise ValueError(f'{path.name}:{line}: expected 12 columns')
        identifiers=tuple(v.strip().strip("'\"") for v in row[:2])
        if not all(identifiers):raise ValueError('Missing resource identifier')
        times=tuple(int(v.strip()) for v in row[2:6])
        if not times[2]<=times[0]<times[1]<=times[3]:
            raise ValueError(f'{path.name}:{line}: invalid contact/tracking times')
        keys.append((*identifiers,*times))
    return {'name':path.name,'sha256':hashlib.sha256(raw).hexdigest(),
            'bytes':len(raw),'rows':len(keys),'header':header},keys

def subset_proof(a,b):
    left=set(a);right=set(b)
    return {'left_unique':len(left),'right_unique':len(right),
            'intersection':len(left&right),'left_only':len(left-right),
            'right_only':len(right-left),'left_subset_of_right':left<=right}

def build(folder,out):
    folder=Path(folder);out=Path(out)
    if out.exists():raise ValueError('Use a new output path')
    meta={};keys={}
    for family in ('C','W'):
        for number in range(1,7):
            name=f'{family}{number}.csv';meta[name],keys[name]=load(folder/name)
    containments=[]
    for family in ('C','W'):
        for i in range(1,7):
            for j in range(i+1,7):
                a=f'{family}{i}.csv';b=f'{family}{j}.csv'
                containments.append({'left':a,'right':b,**subset_proof(keys[a],keys[b])})
    canonical={}; day_seconds=86400
    for name in ('C6.csv','W6.csv'):
        days={day:[k for k in keys[name] if k[2]//day_seconds==day] for day in range(3)}
        assigned=sum(len(v) for v in days.values())
        if assigned!=len(keys[name]):raise ValueError('Actual source extends outside the proposed three-day frame')
        split_relations=[]
        for a,b in ((0,1),(0,2),(1,2)):
            split_relations.append({'left_start_day':a,'right_start_day':b,**subset_proof(days[a],days[b])})
        boundary=[]
        for day,rows in days.items():
            boundary.append({'start_day':day,'assigned_rows':len(rows),
                             'link_end_after_day_boundary':sum(k[3]>(day+1)*day_seconds for k in rows),
                             'tracking_end_after_day_boundary':sum(k[5]>(day+1)*day_seconds for k in rows)})
        canonical[name]={'split_role_candidate':{'day_0':'TRAIN','day_1':'validation','day_2':'retrospective_temporal_TEST'},
            'no_same_opportunity_key_between_days':all(r['intersection']==0 for r in split_relations),
            'opportunity_key_split_relations':split_relations,'boundary_contacts':boundary,
            'whole_day_unique_counts':[len(set(days[d])) for d in range(3)]}
    report={'version':'v07_scene_input_overlap_001','source_grain':'one original contact/tracking opportunity, first six normalized columns',
        'normalization':'strip surrounding ASCII quotes/whitespace from resource labels; exact integer times; no rounding/duration clipping',
        'source_metadata':list(meta.values()),'all_within_series_containments':containments,
        'C6_vs_W6_opportunity_keys':subset_proof(keys['C6.csv'],keys['W6.csv']),
        'canonical_chronological_splits':canonical,
        'no_scheduling_oracle_or_model_execution':True,
        'limits':['Original row disjointness does not establish independence of recurring resources or temporal context.',
                  'Boundary-crossing contacts remain intact; separately solved windows cannot be stitched into a feasible whole-day schedule.',
                  'An input-compatible dataset does not establish strict representation conflicts, certified transfer, or optimizer advantage.',
                  'Prior C3 exposure remains documented; metadata inspection is not a corpus-unseen experiment.']}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'out':str(out),'nested_series':all(r['left_subset_of_right'] for r in containments),
                     'canonical_C6_W6_overlap':report['C6_vs_W6_opportunity_keys']['intersection'],
                     'rows':{n:meta[n]['rows'] for n in ('C6.csv','W6.csv')},
                     'day_split_intersections':{n:[r['intersection'] for r in v['opportunity_key_split_relations']] for n,v in canonical.items()}},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();build(a.data_dir,a.out)
