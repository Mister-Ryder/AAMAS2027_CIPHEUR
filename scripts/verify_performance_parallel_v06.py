"""Parallel orchestration of the unchanged independent V003 TEST verifier.

No experimental runtime is invoked. Six bounded context workers call the
original mathematical auditor; parent retains archive/source/frame checks,
original journal ordering, all failed/null positions and terminal receipts.
"""
from __future__ import annotations
import argparse
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from hashlib import sha256
import json, math
from pathlib import Path, PurePosixPath
import sys, tarfile, tempfile, time, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import verify_performance_test_v06 as original
from scripts.verify_performance_test_v06 import (
    Audit, GraphAudit, STEM, STUDY, RELEASE, digest, canonical, key, cohort,
    safe_member, expected_keys, nonnegative, successful_initializer,
    policy_phase_receipts, graph_digest, feasible,
)

MATH_SOURCE_SHA256 = '59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a'
MAX_WORKERS = 6
if digest(original.__file__) != MATH_SOURCE_SHA256:
    raise ValueError('Original independent mathematical source changed')
_WORKER_DATA = None


def _initialize_worker(protocol, byp, byid, aggregated, loading, execution):
    global _WORKER_DATA
    if digest(original.__file__) != MATH_SOURCE_SHA256:
        raise ValueError('Spawned worker original mathematical source changed')
    _WORKER_DATA = (protocol, byp, byid, aggregated, loading, execution)


def _worker_result(a, status, seen, hashes, keys, compact_rows, context_id):
    return {'checks': a.checks, 'errors': a.errors, 'totals': a.totals,
            'status': status, 'seen': seen, 'journal_hashes': hashes,
            'assignment_keys': keys, 'compact_rows': compact_rows,
            'context_id': context_id}


def audit_context(job):
    """Original per-context loop; only I/O and global uniqueness move to parent."""
    journal_name, journal_path, expected_hash, stage_dir = job
    protocol, byp, byid, aggregated, bindings, execution = _WORKER_DATA
    a = Audit(); status = Counter(); seen = set(); journal_hashes = {}
    assignment_keys = []; compact_rows = []; stage = Path(stage_dir)
    with Path(journal_path).open('rb') as stream:
        rawlines = list(stream)
    h = sha256(b''.join(rawlines)).hexdigest()
    a.check(h == expected_hash, 'journal_second_pass_same_bytes', journal_name)
    rows=[];partial=False
    for i,line in enumerate(rawlines):
        try:r=json.loads(line)
        except json.JSONDecodeError:
            a.check(i==len(rawlines)-1 and (execution['whole_batch_guard_triggered'] or execution['exit_code']!=0),
                'partial_final_line_only_after_guard_or_failure',journal_name);partial=True;break
        rows.append(r)
    if not rows:return _worker_result(a,status,seen,journal_hashes,assignment_keys,compact_rows,None)
    c=byid[rows[0]['id']];token=sha256(c['id'].encode()).hexdigest()[:16]
    a.check(journal_name==STEM+'/context_results/'+token+'.jsonl' and all(r['id']==c['id'] for r in rows),'journal_context_identity',journal_name)
    graph=json.loads((stage/PurePosixPath(c['graph_file']).name).read_bytes());g=GraphAudit(graph,a)
    a.check(graph_digest(graph)==c['graph_sha256'] and len(g.nodes)==c['n'] and len(g.edges)==c['m']
        and len(graph['edges'])==len(g.edges) and g.value(g.nodes)/c['source_weight_scale']==Fraction(c['total_source_weight_exact']),
        'independent_graph_identity_and_original_units',c['id'])
    loading=bindings.get('context_loading/'+token+'.json',{});inits={};init_rows={}
    for r in rows:
        k=key(r);where='|'.join(map(str,k));assignment_keys.append(k);seen.add(k)
        if k in aggregated:a.check(canonical(r)==aggregated[k],'journal_aggregate_exact_row_identity',where)
        journal_hashes[k]=canonical(r)
        for field in ('population','split','n','m','graph_sha256','source_weight_scale','total_source_weight_exact'):
            a.check(r[field]==c[field],'original_context_row_metadata',where+':'+field)
        a.check(r.get('pair_id')==c.get('pair_id') and r.get('side')==c.get('side'),'original_paired_endpoint_metadata',where)
        result=r.get('result');error=r.get('runner_error');ok=error is None and result is not None and result.get('completed') is True and result.get('feasible') is True
        a.check(r['successful_assignment']==ok and r['assignment_returned'],'success_scope_and_returned_flag',where)
        reward=None
        if result and result.get('selected') is not None:
            a.check(feasible(g.nodes,g.adj,result['selected']),'original_graph_selected_feasibility',where)
            reward=g.value(result['selected'])/c['source_weight_scale']
            a.check(Fraction(result['value_exact'])==reward*c['source_weight_scale'],'exact_original_reward',where)
        a.check(r.get('value_exact_original_objective')==(str(reward) if reward is not None else None)
            and r['quality_reward_exact_original_objective']==(str(reward) if ok else None)
            and r.get('diagnostic_retained_reward_exact_original_objective')==(str(reward) if not ok and reward is not None else None),
            'no_failed_incumbent_in_success_quality',where)
        a.check(r.get('input_total_weight_fraction_exact')==(str(reward/Fraction(c['total_source_weight_exact'])) if ok else None),
            'exact_total_weight_fraction_not_optimum',where)
        wall=cpu=nwall=ncpu=pwall=pcpu=None;work=search=None
        if r['track'] in ('native','common_initializer') and result:
            g.native(r,result,protocol,where);wall=nwall=result['wrapper_wall_seconds'];cpu=ncpu=result['wrapper_self_cpu_seconds']+result.get('child_cpu_seconds',0)
            if r['track']=='common_initializer':
                inits[r['nominal_wall_target_seconds']]=result
                init_rows[r['nominal_wall_target_seconds']]=r
                a.check(r['shared_initializer_receipt_sha256']==canonical(result),'shared_initializer_exact_receipt',where)
        elif r['track'] in ('cold_Degree','warm_CHILS'):
            p=byp[r['method']]
            mapping={'program_kind':'kind','program_role':'role','program_sha256':'program_sha256','joint_eligible':'joint_eligible',
                     'authoring_block':'block','authoring_arm':'arm','source_candidate_id':'source_candidate_id','published_authoring_run':'run','published_winner_origin':'winner_origin'}
            for f,pf in mapping.items():a.check(r[f]==p.get(pf),'preserved_frozen_program_role',where+':'+f)
            init=inits.get(r['nominal_wall_target_seconds']);warm=r['track']=='warm_CHILS';phase=r['nominal_wall_target_seconds']*(.5 if warm else 1)
            policy_phase_receipts(r,p,init_rows.get(r['nominal_wall_target_seconds']),a,where)
            if r.get('policy_wrapper_wall_seconds') is not None:
                pwall=r['policy_wrapper_wall_seconds'];pcpu=r['policy_wrapper_cpu_seconds'];wall=pwall;cpu=pcpu
                a.check(nonnegative(pwall) and nonnegative(pcpu),'individual_policy_phase_times_nonnegative',where)
                if warm and init is not None and init['completed'] and init['feasible']:
                    nwall=init['wrapper_wall_seconds'];ncpu=init['wrapper_self_cpu_seconds']+init.get('child_cpu_seconds',0)
                    wall=nwall+pwall;cpu=ncpu+pcpu
                    a.check(r['standalone_pipeline_wall_seconds']==wall and r['standalone_pipeline_cpu_seconds']==cpu,
                        'exception_or_normal_policy_phase_cost_preserved',where)
            if result:
                a.check(p['available'] is True,'unavailable_identity_cannot_return_fallback',where)
                if warm:
                    init_row=init_rows.get(r['nominal_wall_target_seconds'],{})
                    a.check(init_row.get('runner_error') is None and init_row.get('successful_assignment') is True
                        and init is not None and init['completed'] is True and init['feasible'] is True,
                        'warm_requires_error_free_successful_original_initializer_row',where)
                start=init['selected'] if warm else []
                g.kernel(result,p,protocol,phase,start,where)
                pwall=r['policy_wrapper_wall_seconds'];pcpu=r['policy_wrapper_cpu_seconds'];wall=pwall;cpu=pcpu
                work=result['meter']['feature_work']+result['meter']['repair_work'];search=result['meter']['search_nodes']
                if warm:
                    nwall=init['wrapper_wall_seconds'];ncpu=init['wrapper_self_cpu_seconds']+init.get('child_cpu_seconds',0);wall=nwall+pwall;cpu=ncpu+pcpu
                    a.check(r['native_initial_selected']==init['selected'] and r['native_initial_value_exact']==init['value_exact']
                        and r['shared_initializer_receipt_sha256']==canonical(init) and Fraction(result['value_exact'])>=Fraction(init['value_exact'])
                        and r['standalone_pipeline_wall_seconds']==wall and r['standalone_pipeline_cpu_seconds']==cpu
                        and r['native_initialization_cost_shared_in_actual_execution'] and r['advanced_track_available'],
                        'full_initializer_cost_charged_and_monotone_warm_seed',where)
            else:
                a.check(not ok and error is not None,'missing_or_failed_policy_remains_null',where)
                if error and error['type']=='MissingFrozenQualityOnlyPosition':a.check(not p['available'],'missing_frozen_identity_no_replacement',where)
        if wall is not None:a.check(all(nonnegative(x) for x in (wall,cpu)),'actual_standalone_time_receipts',where)
        statusname=result['status'] if result else (error['type'] if error else 'missing_error')
        status[r['track']+':'+statusname]+=1
        row={f:c.get(f) for f in ('id','population','family','n','cluster','pair_id','side','source_cluster')}
        row['source_cluster']=c.get('source_cluster') or c.get('cluster') or c.get('pair_id')
        row.update(regime=c.get('regime',c.get('source',{}).get('regime')),profile=c.get('profile',c.get('source',{}).get('profile')))
        row.update(target=r['nominal_wall_target_seconds'],track=r['track'],method=r['method'],seed=r['seed'],
            analysis_cohort=cohort(byp[r['method']]) if r['method'] in byp else r['method'],
            success=ok,returned=True,status=statusname,error=error or (result.get('error') if result else None),
            reward_exact=str(reward) if ok else None,diagnostic_reward_exact=str(reward) if not ok and reward is not None else None,
            total_exact=c['total_source_weight_exact'],standalone_wall_seconds=wall,standalone_cpu_seconds=cpu,
            native_wall_seconds=nwall,native_cpu_seconds=ncpu,policy_wall_seconds=pwall,policy_cpu_seconds=pcpu,
            shared_graph_load_wall_seconds=loading.get('shared_graph_load_wall_seconds'),shared_graph_load_cpu_seconds=loading.get('shared_graph_load_cpu_seconds'),
            work=work,search_nodes=search,feature_work=result.get('meter',{}).get('feature_work') if result else None)
        for f in ('program_kind','program_role','program_sha256','authoring_block','authoring_arm','source_candidate_id','published_winner_origin'):
            row[f]=r.get(f)
        compact_rows.append(row)
    return _worker_result(a,status,seen,journal_hashes,assignment_keys,compact_rows,c['id'])


def audit_parallel(archive,archive_sha,out,rows_out):
    began=time.perf_counter();archive,out,rows_out=map(Path,(archive,out,rows_out));a=Audit()
    if out.exists() or rows_out.exists():raise ValueError('Preserve previous audit and compact rows')
    if digest(archive)!=archive_sha:raise ValueError('Actual canonical server archive SHA mismatch')
    protocol=json.loads((STUDY/'protocol.json').read_bytes());deployment=json.loads((STUDY/'deployment.json').read_bytes())
    for path,h in ((STUDY/'protocol.json','59395b0b7f4c8460da8e58bcdccaa292b189a627716e1e050c52b7a659ba4cfa'),
                   (STUDY/'source.zip','b08d95b17d571a19a062109726e0bb7f4f80322addcd099b73b8f3568c494f09'),
                   (STUDY/'deployment.json','4873ed683327f2e271c36dacac625df52bb8dd0a678dc293035946b27ba126fb'),
                   (STUDY/'server_input_preparation/input_freeze.json','42f7e9606499e379063c81d66d96beaa9cefb77be57be66c6076784ff33e4689'),
                   (RELEASE,'5b6f82647e282a4491ad3b49775a21cf91afddfc1c2f46ea1defdad9d13e5063')):
        if digest(path)!=h:raise ValueError('Pre-query scientific binding changed: '+str(path))
    inventory=json.loads((STUDY/'server_input_preparation/context_inventory.json').read_bytes());contexts=inventory['contexts'];byid={c['id']:c for c in contexts}
    programs=deployment['programs'];byp={p['method_id']:p for p in programs};expected=set(expected_keys(contexts,protocol,programs))
    a.check(len(contexts)==302 and len(programs)==23 and len(expected)==52548,'complete_preregistered_frame')
    a.check(protocol['repair_config']['policy_scope']=='branch','shared_Degree_target_and_restriction')
    for n,h in protocol['source_sha256'].items():a.check(digest(ROOT/n)==h,'unchanged_scientific_source',n)
    with zipfile.ZipFile(STUDY/'source.zip') as z:
        for n,h in protocol['source_sha256'].items():a.check(sha256(z.read(n)).hexdigest()==h,'original_source_capsule',n)
    bindings={};aggregated={};aggregated_nulls={};journal_hashes={};journal_paths={};unreturned=[];members={};status=Counter();seen=set();compact_count=0
    partial_aggregate=False
    stage_root=ROOT/'.research/performance_parallel_audit_staging';stage_root.mkdir(parents=True,exist_ok=True)
    rows_out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v003_parallel_',dir=stage_root) as stage:
        stage=Path(stage)
        with tarfile.open(archive,'r|gz') as tar:
            for m in tar:
                safe_member(m)
                if not m.isfile():continue
                if m.name in members:raise ValueError('Duplicate archive member')
                stream=tar.extractfile(m);h=sha256();relative=PurePosixPath(m.name)
                if relative.parts[0]!=STEM:raise ValueError('Unexpected execution archive root')
                name='/'.join(relative.parts[1:])
                if name.startswith('graphs/'):
                    dest=stage/relative.name
                    with dest.open('xb') as f:
                        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b);f.write(b)
                elif name=='results.jsonl':
                    for line in stream:
                        h.update(line)
                        if not line.strip():continue
                        try:r=json.loads(line)
                        except json.JSONDecodeError:
                            tail=stream.read();h.update(tail)
                            if tail:raise ValueError('Malformed aggregate line before archive member end')
                            partial_aggregate=True;break
                        k=key(r)
                        if k in aggregated:raise ValueError('Duplicate aggregate assignment')
                        aggregated[k]=canonical(r)
                        if r.get('result') is None:aggregated_nulls[k]=r
                elif name.startswith('context_results/'):
                    # Stage exact journal bytes during the unchanged first
                    # archive/hash pass. Workers reread only these bound files.
                    journal_dir=stage/'journals';journal_dir.mkdir(exist_ok=True)
                    dest=journal_dir/relative.name
                    with dest.open('xb') as f:
                        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b);f.write(b)
                    journal_paths[name]=dest
                else:
                    raw=stream.read();h.update(raw)
                    if name.endswith('.json') and not name.startswith('graphs/'):bindings[name]=json.loads(raw)
                    elif name=='unreturned_assignments.jsonl':unreturned=[json.loads(l) for l in raw.splitlines() if l]
                members[m.name]=h.hexdigest()
        frozen=bindings['input_freeze.json'];host=bindings['host_receipt.json'];execution=bindings['server_execution_receipt.json']
        for n in ('protocol.json','deployment.json','TRAIN_selection.json','controls_TRAIN_selection.json','independent_TRAIN_audit.json',
                  'published_EoH_TRAIN_selection.json','published_EoH_author_audit.json','published_EoH_TRAIN_audit.json'):
            a.check(members[STEM+'/'+n]==digest(STUDY/n),'executed_exact_predeclared_identity_binding',n)
        a.check(members[STEM+'/root_release.json']==digest(RELEASE)==host['root_release_sha256'],
            'actual_root_authorized_launch')
        a.check(members[STEM+'/context_inventory.json']==digest(STUDY/'server_input_preparation/context_inventory.json')==frozen['context_inventory_sha256']
            and members[STEM+'/input_freeze.json']==digest(STUDY/'server_input_preparation/input_freeze.json'),
            'original_complete_prepared_context_frame')
        a.check(execution['retries']==0 and execution['all_partial_journals_retained'] and host['workers']==8,'original_execution_no_retry')
        a.check(not partial_aggregate or execution['whole_batch_guard_triggered'] or execution['exit_code']!=0,
            'partial_aggregate_tail_only_after_original_batch_interruption')
        a.check(execution['source_zip_sha256']==deployment['source_zip_sha256']==host['source_zip_sha256']
            and host['before_any_TEST_solver_outcomes'] and bindings['launch_receipt.json']['assigned']==52548
            and bindings['launch_receipt.json']['root_release_sha256']==host['root_release_sha256']
            and bindings['launch_receipt.json']['whole_batch_wall_guard_seconds']==14400,
            'host_launch_execution_complete_source_and_guard_binding')
        for c in contexts:a.check(members[STEM+'/'+c['graph_file']]==c['graph_file_sha256']==frozen['graph_files_sha256'][c['graph_file']],
            'original_lossless_graph_bytes',c['id'])
        with rows_out.open('x',encoding='utf-8',newline='\n') as compact:
            loading={name:value for name,value in bindings.items() if name.startswith('context_loading/')}
            jobs=iter((STEM+'/'+name,str(path),members[STEM+'/'+name],str(stage))
                      for name,path in journal_paths.items())
            initargs=(protocol,byp,byid,aggregated,loading,execution)
            # At most six context tasks/results exist in the process queue.
            # Consume submission order, preserving original archive ordering.
            with ProcessPoolExecutor(max_workers=MAX_WORKERS,initializer=_initialize_worker,initargs=initargs) as pool:
                pending=deque()
                for _ in range(MAX_WORKERS):
                    job=next(jobs,None)
                    if job is None:break
                    pending.append(pool.submit(audit_context,job))
                while pending:
                    result=pending.popleft().result()
                    a.checks.update(result['checks']);a.errors.extend(result['errors']);a.totals.update(result['totals'])
                    if set(result['assignment_keys'])!=result['seen']:
                        raise ValueError('Worker returned inconsistent assignment frame')
                    for k in result['assignment_keys']:
                        # This is the one original membership/uniqueness check,
                        # performed globally rather than duplicated in workers.
                        where='|'.join(map(str,k))
                        a.check(k in expected and k not in seen,'every_unique_original_assignment',where);seen.add(k)
                    journal_hashes.update(result['journal_hashes']);status.update(result['status'])
                    for row in result['compact_rows']:
                        compact.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');compact_count+=1
                    if result['context_id'] is not None:
                        print(json.dumps({'verified_context':result['context_id'],'assignments_so_far':compact_count,
                                          'errors':len(a.errors),'parallel_workers':MAX_WORKERS}),flush=True)
                    del result
                    job=next(jobs,None)
                    if job is not None:pending.append(pool.submit(audit_context,job))
            # Aggregate-generated missing worker receipts are absent from the
            # journals. Preserve them as explicit nulls, not fabricated times.
            missing_aggregated=[]
            for k,h in aggregated.items():
                if k not in seen:
                    r=aggregated_nulls.get(k)
                    a.check(r is not None and r.get('runner_error') is not None and r['result'] is None and r['assignment_returned'] is True,
                        'aggregate_worker_failure_is_explicit_null',str(k))
                    if r is not None:missing_aggregated.append(r)
            for r in unreturned+missing_aggregated:
                k=key(r);a.check(k in expected and k not in seen and r['assignment_returned']==(r in missing_aggregated)
                    and not r['successful_assignment'] and r['result'] is None and r['quality_reward_exact_original_objective'] is None,
                    'every_guard_unreturned_request_explicit_null',str(k));seen.add(k)
                c=byid[r['id']]
                for field in ('population','split','n','m','graph_sha256','source_weight_scale','total_source_weight_exact'):
                    a.check(r[field]==c[field],'unmeasured_row_original_context_metadata',str(k)+':'+field)
                a.check(r.get('value_exact_original_objective') is None and r.get('diagnostic_retained_reward_exact_original_objective') is None
                    and r.get('input_total_weight_fraction_exact') is None and all(r.get(f) is None for f in
                    ('standalone_pipeline_wall_seconds','standalone_pipeline_cpu_seconds','policy_wrapper_wall_seconds','policy_wrapper_cpu_seconds')),
                    'unmeasured_stub_has_no_diagnostic_reward_or_fabricated_times',str(k))
                if r['method'] in byp:
                    p=byp[r['method']]
                    for f,pf in {'program_kind':'kind','program_role':'role','program_sha256':'program_sha256','joint_eligible':'joint_eligible',
                                 'authoring_block':'block','authoring_arm':'arm','source_candidate_id':'source_candidate_id',
                                 'published_authoring_run':'run','published_winner_origin':'winner_origin'}.items():
                        a.check(r[f]==p.get(pf),'unmeasured_stub_frozen_program_role',str(k)+':'+f)
                c=byid[r['id']];row={f:c.get(f) for f in ('id','population','family','n','cluster','pair_id','side','source_cluster')}
                row['source_cluster']=c.get('source_cluster') or c.get('cluster') or c.get('pair_id')
                row.update(regime=c.get('regime',c.get('source',{}).get('regime')),profile=c.get('profile',c.get('source',{}).get('profile')))
                row.update(target=r['nominal_wall_target_seconds'],track=r['track'],method=r['method'],seed=r['seed'],success=False,returned=r['assignment_returned'],
                    analysis_cohort=cohort(byp[r['method']]) if r['method'] in byp else r['method'],
                    status=r['runner_error']['type'],error=r['runner_error'],reward_exact=None,diagnostic_reward_exact=None,total_exact=c['total_source_weight_exact'],
                    standalone_wall_seconds=None,standalone_cpu_seconds=None,native_wall_seconds=None,native_cpu_seconds=None,policy_wall_seconds=None,policy_cpu_seconds=None,
                    shared_graph_load_wall_seconds=None,shared_graph_load_cpu_seconds=None,work=None,search_nodes=None,feature_work=None)
                for f in ('program_kind','program_role','program_sha256','authoring_block','authoring_arm','source_candidate_id','published_winner_origin'):row[f]=r.get(f)
                compact.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');compact_count+=1;status[r['track']+':'+row['status']]+=1
    a.check(seen==expected and compact_count==len(expected),'complete_frame_including_missing_and_failed')
    if 'completion.json' in bindings:
        complete=bindings['completion.json'];a.check(complete['returned']==complete['assigned']==52548 and complete['contexts']==302
            and complete['results_sha256']==members[STEM+'/results.jsonl'] and complete['online_model_calls']==complete['conditional_oracle_calls']==0
            and complete['all_rows_retained'] and not unreturned and set(aggregated)==expected,'terminal_complete_original_batch')
        a.check(complete['deployment_sha256']==digest(STUDY/'deployment.json') and complete['protocol_sha256']==digest(STUDY/'protocol.json')
            and execution['exit_code']==0 and execution['whole_batch_guard_triggered'] is False and not partial_aggregate,
            'complete_batch_exact_deployment_protocol_and_successful_exit')
        a.check(Counter(complete['status_counts'])==status,'terminal_status_count_reconstruction')
    else:a.check(execution['whole_batch_guard_triggered'] or execution['exit_code']!=0,'incomplete_batch_guard_or_error_explicit')
    report={'version':'v06_independent_performance_TEST_audit_001',
        'errors':len(a.errors),'error_details':a.errors,'checks':sum(a.checks.values()),'checks_by_kind':dict(a.checks),
        'totals':dict(a.totals),'archive_sha256':archive_sha,'audited_rows_sha256':digest(rows_out),'audited_rows_path':str(rows_out),
        'audit_source_sha256':digest(original.__file__),'orchestrator_source_sha256':digest(__file__),'registered_constants':{'wall_targets':[.1,1,5],'total_contexts':302,'total_assignments':52548,'policy_slots':23},
        'independent_helper_sha256':{n:digest(ROOT/n) for n in
            ('scripts/verify_public_alias_v05.py','scripts/verify_matched_llm_v05.py','scripts/verify_synthesis_train_v06.py')},
        'policies':[{'method':p['method_id'],'analysis_cohort':cohort(p),'program_kind':p['kind'],'program_role':p['role'],
            'authoring_block':p.get('block'),'authoring_arm':p.get('arm'),'program_sha256':p.get('program_sha256'),
            'published_winner_origin':p.get('winner_origin')} for p in programs],
        'status_counts':dict(status),'host':host,'execution':execution,'wall_seconds_verification_only':time.perf_counter()-began,
        'scope':'Independent root mathematical/receipt audit; no scheduler, solver or conditional oracle import/call; exactness only for explicit saved restricted patches. Mechanical verification is distinct from separately staffed review.'}
    report['verification_orchestration']={'max_workers':MAX_WORKERS,'max_in_flight_contexts':MAX_WORKERS,
        'mathematical_source_sha256':MATH_SOURCE_SHA256,'context_math':'unchanged original GraphAudit and receipt checks',
        'compact_order':'original archive journal order then original explicit-null order',
        'experimental_reexecution':False,'worker_retries':0}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'errors':report['errors'],'checks':report['checks'],'audited_rows':compact_count}),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--archive-sha256',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--rows-out',required=True)
    args=parser.parse_args()
    result=audit_parallel(args.archive,args.archive_sha256,args.out,args.rows_out)
    sys.exit(bool(result['errors']))
