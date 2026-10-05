"""Lossless metric projection for feedback and review, retaining failures separately."""
import argparse,hashlib,json,pathlib
FIELDS=('method','program_id','program_arm','source','config','graph_config_id','split','seed','declared_cpu_seconds',
        'nodes','edges','selected_count','selected_set_sha256','parent_cpu_seconds','deadline_soft_overshoot',
        'value_ticks','value_exact','seed_value_ticks','feasible','cpu_seconds','wall_seconds',
        'cpu_seconds_including_record_encoding','wall_seconds_including_record_encoding',
        'stats','meter','head_ever_committed','loading','native_child_cpu_seconds','native_cpu_measurement_available',
        'numeric_namespace','input_graph_sha256','metadata_sha256','program_bank_sha256','protocol_sha256',
        'script_sha256','execution_module_sha256','cpu_affinity','serialization_measurement','unavoidable_overshoot_scope')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage-root',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--include-curves',action='store_true');a=ap.parse_args()
    records=[]
    for p in sorted((a.stage_root/'results').glob('*.json')):
        r=json.loads(p.read_text(encoding='utf-8'));c={k:r.get(k) for k in FIELDS}
        c['budget_seconds']=r.get('declared_cpu_seconds')
        c['job_id']=p.stem;c['result_sha256']=digest(p);c['result_relative_path']=p.relative_to(a.stage_root).as_posix()
        phases=r.get('phases',{});c['phase_statuses']={k:{x:v.get(x) for x in ['status','error','value_ticks','raw_value_ticks','guarded_value_ticks']} for k,v in phases.items() if isinstance(v,dict)}
        construction=phases.get('construction',{})
        c['construction_summary']={k:construction.get(k) for k in ['status','error','raw_full_value_ticks','raw_delta_from_seed_ticks','accepted_by_guard','prefix_nodes','completion_fallback']}
        repairs=r.get('repairs',[]);gains=[int(v['raw_gain_ticks']) for v in repairs if v.get('raw_gain_ticks') is not None]
        c['repair_summary']={'count':len(repairs),'accepted_count':sum(bool(v.get('committed')) for v in repairs),
            'negative_raw_gain_count':sum(g<0 for g in gains),'zero_raw_gain_count':sum(g==0 for g in gains),
            'raw_gain_ticks_sum':sum(gains),'raw_gain_ticks_min':min(gains) if gains else None,
            'raw_gain_ticks_max':max(gains) if gains else None}
        c['programme_error_count']=sum(v.get('status')=='programme_error' for v in r.get('repairs',[]))+int(phases.get('construction',{}).get('status')=='programme_error')
        c['repair_count']=len(r.get('repairs',[]))
        if a.include_curves:c['best_so_far']=r.get('best_so_far',[])
        records.append(c)
    jobs=[]
    jp=a.stage_root/'jobs.jsonl'
    if jp.is_file():jobs=[json.loads(line) for line in jp.read_text(encoding='utf-8').splitlines() if line.strip()]
    job_map={j.get('job_id'):j for j in jobs}
    for r in records:
        j=job_map.get(r['job_id'],{})
        r['config_alias']=j.get('config',r['config'])
        r['execution_status']=j.get('status','unknown')
    out={'version':'full_schedule_metric_projection_v1','records':records,'result_count':len(records),
         'all_job_count':len(jobs),'failed_jobs':[j for j in jobs if j.get('status')!='complete'],
         'scope':'all complete artifacts; failures explicitly retained; not a rerun or candidate pruning',
         'stage_root_provenance':str(a.stage_root),'jobs_sha256':digest(jp) if jp.is_file() else None}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'results':len(records),'jobs':len(jobs),'failures':len(out['failed_jobs']),'sha256':digest(a.output)}))
if __name__=='__main__':main()
