"""Execute registered jobs once, with disjoint Linux worker CPU affinities."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback

from benchmark import METHODS, SCRIPT as BENCHMARK, compact_projection, digest, read_json, save_new


def read_jobs(path):
    path=Path(path)
    if 'pending' in path.name.lower():
        raise ValueError('Pending registration is not executable')
    if path.suffix=='.jsonl':
        rows=[]
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip(): rows.append(json.loads(line))
    else:
        value=read_json(path);rows=value['jobs'] if isinstance(value,dict) else value
    if not isinstance(rows,list) or not rows: raise ValueError('Expected a nonempty registered job list')
    seen=set()
    for row in rows:
        if row.get('ready_to_execute') is False:
            raise ValueError('Registration has ready_to_execute=false')
        identifier=row.get('job_id',row.get('id'))
        if (not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,220}',identifier)
                or identifier in ('.','..') or identifier in seen):
            raise ValueError('Invalid or duplicate registered job_id')
        row['job_id']=identifier;seen.add(identifier)
    return rows


def make_command(job,args,output):
    argv=job.get('argv')
    if argv is not None:
        if not isinstance(argv,list) or not all(isinstance(v,str) for v in argv):
            raise ValueError('Registered argv must be a list of strings')
        command=([args.python,str(BENCHMARK)]+argv if argv and argv[0].startswith('--') else list(argv))
        if '--output' not in command: command.extend(['--output',str(output)])
        else:
            target=Path(command[command.index('--output')+1]).resolve()
            if target!=output.resolve(): raise ValueError('Registered output disagrees with argv')
        if '--job-id' not in command: command.extend(['--job-id',job['job_id']])
    else:
        command=[args.python,str(BENCHMARK)]
        aliases={'seconds':('seconds','budget_cpu_seconds','budget_seconds','declared_cpu_seconds')}
        for field in ('method','graph','metadata','seconds','seed','source','config','split','bank'):
            value=next((job[k] for k in aliases.get(field,(field,)) if k in job),None)
            if value is not None: command.extend(['--'+field,str(value)])
        command.extend(['--job-id',job['job_id'],'--output',str(output)])
    for name in ('cipheur_root','native_executable','protocol'):
        flag='--'+name.replace('_','-')
        value=job.get(name,getattr(args,name,None))
        if value and flag not in command: command.extend([flag,str(value)])
    return command


def affinity_pool(workers):
    if not hasattr(os,'sched_getaffinity'): return [None]*workers,'affinity_unavailable'
    allowed=sorted(os.sched_getaffinity(0))
    preferred=[cpu for cpu in allowed if 24<=cpu<=31]
    cpus=(preferred or allowed)[:workers]
    if not cpus: raise ValueError('No allowed CPU for workers')
    if not shutil.which('taskset'): raise RuntimeError('Linux affinity requires taskset')
    return cpus,'allowed_intersection_24_31' if preferred else 'fallback_actual_allowed_cpus'


def run(args):
    wall_start,cpu_start=time.perf_counter(),time.process_time()
    root=args.output_root.resolve();root.mkdir(parents=True,exist_ok=True)
    for name in ('queue_registration.json','execution_summary.json','metrics.json'):
        if (root/name).exists(): raise FileExistsError('Refusing repeat queue: '+str(root/name))
    jobs=read_jobs(args.jobs)
    cpus,affinity_mode=affinity_pool(args.workers)
    work=queue.Queue();outputs=set()
    for job in jobs:
        output=Path(job.get('output',root/'results'/(job['job_id']+'.json'))).resolve()
        if output in outputs: raise ValueError('Duplicate registered output path')
        outputs.add(output);job['_output']=str(output)
        if output.exists(): raise FileExistsError('Registered output already exists: '+str(output))
        work.put(job)
    save_new(root/'queue_registration.json',dict(version='stk_online_llm_v2_queue',
        jobs_path=str(args.jobs.resolve()),jobs_sha256=digest(args.jobs),jobs=len(jobs),
        requested_workers=args.workers,effective_workers=len(cpus),worker_cpu_ids=cpus,
        affinity_mode=affinity_mode,benchmark_sha256=digest(BENCHMARK),
        queue_sha256=digest(Path(__file__)),protocol_sha256=digest(args.protocol) if args.protocol else None,
        no_automatic_retry=True,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    statuses,records=[],[];lock=threading.Lock()
    def worker(cpu):
        while True:
            try:job=work.get_nowait()
            except queue.Empty:return
            identifier=job['job_id'];output=Path(job['_output']);started=time.perf_counter()
            receipt=dict(job_id=identifier,worker_cpu=cpu,output=str(output),status='starting')
            try:
                command=make_command(job,args,output)
                if cpu is not None:command=['taskset','-c',str(cpu)]+command
                receipt['command']=command
                logroot=root/'logs';logroot.mkdir(parents=True,exist_ok=True)
                environment={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
                    'MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1','PYTHONHASHSEED':'0'}
                with (logroot/(identifier+'.stdout')).open('xb') as stdout, (logroot/(identifier+'.stderr')).open('xb') as stderr:
                    process=subprocess.run(command,stdout=stdout,stderr=stderr,env=environment,
                                           check=False,timeout=args.hard_wall_seconds)
                receipt['returncode']=process.returncode
                if process.returncode!=0: raise RuntimeError('Benchmark process exit '+str(process.returncode))
                if not output.is_file():raise RuntimeError('Benchmark returned no output artifact')
                result=read_json(output)
                if result.get('job_id')!=identifier: raise ValueError('Output job_id mismatch')
                if result.get('method') not in METHODS: raise ValueError('Unknown output method')
                for field in ('method','source','config','split','seed'):
                    if field in job and result.get(field)!=job[field]:
                        raise ValueError('Output differs from registered '+field)
                if 'seconds' in job and result.get('budget_cpu_seconds')!=job['seconds']:
                    raise ValueError('Output differs from registered CPU budget')
                for field in ('input_graph_sha256','metadata_sha256','bank_sha256','controller_config_sha256'):
                    if field in job and result.get(field)!=job[field]:
                        raise ValueError('Output differs from registered '+field)
                registered=job.get('code_hashes',{})
                for name,actual in result.get('module_sha256',{}).items():
                    relative='code/cipheur/online_v2/'+name+'.py'
                    if relative in registered and registered[relative]!=actual:
                        raise ValueError('Output uses changed module '+name)
                if ('scripts/benchmark.py' in registered and
                        registered['scripts/benchmark.py']!=result.get('script_sha256')):
                    raise ValueError('Output uses changed benchmark script')
                receipt.update(status='complete',execution_status=result.get('execution_status'),
                               output_sha256=digest(output),feasible=result.get('feasible'))
                projection=compact_projection(result)
                projection.update(job_id=identifier,output=str(output),output_sha256=receipt['output_sha256'])
                with lock:records.append(projection)
            except Exception as error:
                receipt.update(status='failed',error=repr(error),traceback=traceback.format_exc())
            receipt['wall_seconds']=time.perf_counter()-started
            try:save_new(root/'receipts'/(identifier+'.json'),receipt)
            except Exception as error:
                receipt.update(status='receipt_write_failed',receipt_error=repr(error))
            with lock:
                statuses.append(receipt)
                print(json.dumps(dict(job_id=identifier,status=receipt['status'],
                    execution_status=receipt.get('execution_status'),done=len(statuses),total=len(jobs)),
                    ensure_ascii=False),flush=True)
            work.task_done()
    threads=[threading.Thread(target=worker,args=(cpu,),daemon=False) for cpu in cpus]
    for thread in threads:thread.start()
    for thread in threads:thread.join()
    order={job['job_id']:i for i,job in enumerate(jobs)}
    statuses.sort(key=lambda row:order[row['job_id']]);records.sort(key=lambda row:order[row['job_id']])
    failures=[row for row in statuses if row['status']!='complete']
    method_errors=[row for row in records if row.get('execution_status')!='ok']
    summary=dict(version='stk_online_llm_v2_queue',all_job_count=len(jobs),
        complete_job_count=len(statuses)-len(failures),failed_job_count=len(failures),
        method_error_or_non_ok_count=len(method_errors),all_attempted=len(statuses)==len(jobs),
        failed_jobs=failures,execution_status_counts=dict(Counter(r.get('execution_status') for r in records)),
        worker_cpu_ids=cpus,wall_seconds=time.perf_counter()-wall_start,
        queue_parent_cpu_seconds=time.process_time()-cpu_start,
        benchmark_cpu_excludes_queue_dispatch_overhead=True,no_automatic_retry=True,
        jobs_sha256=digest(args.jobs),queue_sha256=digest(Path(__file__)),
        benchmark_sha256=digest(BENCHMARK),statuses=statuses)
    save_new(root/'metrics.json',dict(records=records,failed_jobs=failures,all_job_count=len(jobs),
                                    method_error_or_non_ok_count=len(method_errors)))
    summary['metrics_sha256']=digest(root/'metrics.json')
    save_new(root/'execution_summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--cipheur-root',type=Path);parser.add_argument('--native-executable')
    parser.add_argument('--protocol',type=Path)
    parser.add_argument('--hard-wall-seconds',type=float,default=None,
                        help='Optional per-job hard guard, distinct from optimizer CPU budget')
    args=parser.parse_args()
    if args.workers<1:parser.error('--workers must be positive')
    summary=run(args)
    print(json.dumps({k:summary[k] for k in ('all_job_count','complete_job_count','failed_job_count',
        'method_error_or_non_ok_count','wall_seconds')},ensure_ascii=False))
    return 1 if summary['failed_job_count'] else 0


if __name__=='__main__':sys.exit(main())
