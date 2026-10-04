"""Sequential cloud assays after the original performance batch has terminated.

This operational wrapper never changes a scientific source, selects a program,
reads a solver objective for a scheduling decision, retries an assay, or issues
an LLM request. Original prepared registrations and root releases authorize the
three commands. Waiting avoids overlapping the measured solver workloads.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json,os,platform,subprocess,sys,tarfile,time
from pathlib import Path

def digest(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2)+'\n')
def live(pid):
    stat=Path('/proc')/str(pid)/'stat'
    try:return stat.read_text().split(') ',1)[1].split()[0] not in ('Z','X')
    except FileNotFoundError:return False
def verify_prepared(registration):
    freeze=read(registration/'freeze_receipt.json')
    for name,h in freeze['artifact_sha256'].items():
        path=(registration/name).resolve()
        if not path.is_relative_to(registration.resolve()) or digest(path)!=h:
            raise ValueError('Prepared assay artifact changed: '+name)
    return digest(registration/'freeze_receipt.json')

def run(heldout_root,bridge_root,performance_root,out):
    if platform.system()!='Linux':raise ValueError('Cloud-only operational wrapper')
    heldout_root,bridge_root,performance_root,out=map(lambda p:Path(p).resolve(),(heldout_root,bridge_root,performance_root,out))
    if out.exists():raise ValueError('Preserve original queue, commands and observations')
    r2=heldout_root/'experiments/discovery/v06_R2_heldout_server_002'
    eoh=heldout_root/'experiments/discovery/v06_published_EoH_heldout_prepared_server_001'
    r2_freeze,eoh_freeze=verify_prepared(r2),verify_prepared(eoh)
    main_sha=digest(r2/'root_release.json')
    if main_sha!='8e69f14051ce731332b11aaefa2f60c2ace38780e4f20dfb9429974555ca83d1':raise ValueError('Original main TEST release changed')
    eoh_sha=digest(eoh/'root_release.json')
    if eoh_sha!='6d13879f9126971dc9d0510739f20ae68339a81f8baf1e249c3517ea343d8dde':raise ValueError('EoH addon release changed')
    bridge_receipt=read(bridge_root/'capsule_receipt.json')
    for name,h in bridge_receipt['files_sha256'].items():
        if digest(bridge_root/name)!=h:raise ValueError('Original bridge capsule changed')
    bridge_release=bridge_root/'experiments/discovery/v06_test_release_002/TRAIN_patch_bridge_root_release_001.json'
    bridge_sha=digest(bridge_release)
    if bridge_sha!=bridge_receipt['root_release_sha256']:raise ValueError('Bridge root release changed')
    perf_out=performance_root/'output/performance_r2_eoh_test_v06_003_inputs'
    perf_launch=read(perf_out/'launch_receipt.json')
    perf_launcher=read(performance_root/'identity_staging_and_launch_receipt.json')
    if digest(perf_out/'root_release.json')!='5b6f82647e282a4491ad3b49775a21cf91afddfc1c2f46ea1defdad9d13e5063':
        raise ValueError('Performance root release changed')
    python=sys.executable
    assays=[
        {'name':'v06_R2_heldout_results_server_002','root':heldout_root,'registration':r2,
         'freeze_sha256':r2_freeze,'root_release_sha256':main_sha,
         'command':[python,'-B','-m','cipheur.heldout_refinement_v06','run','--registration',str(r2),
                    '--out',str(heldout_root/'output/v06_R2_heldout_results_server_002'),'--root-release-sha256',main_sha]},
        {'name':'v06_EoH_heldout_results_server_001','root':heldout_root,'registration':eoh,
         'freeze_sha256':eoh_freeze,'root_release_sha256':eoh_sha,
         'command':[python,'-B','-m','cipheur.heldout_published_eoh_v06','run','--registration',str(eoh),
                    '--registration-sha256',eoh_freeze,'--out',str(heldout_root/'output/v06_EoH_heldout_results_server_001'),
                    '--root-release-sha256',eoh_sha]},
        {'name':'v06_TRAIN_patch_bridge_results_server_001','root':bridge_root,
         'registration':bridge_root/'experiments/discovery/v06_patch_bridge_001',
         'freeze_sha256':bridge_receipt['bridge_freeze_sha256'],'root_release_sha256':bridge_sha,
         'command':[python,'-B','scripts/patch_ranking_bridge_v06.py','run',
                    '--registration',str(bridge_root/'experiments/discovery/v06_patch_bridge_001'),
                    '--programmes',str(bridge_root/'experiments/discovery/v06_patch_bridge_programs_frozen_001/program_inventory.json'),
                    '--release',str(bridge_release),'--release-sha256',bridge_sha,
                    '--out',str(bridge_root/'output/v06_TRAIN_patch_bridge_results_server_001')]}
    ]
    for assay in assays:
        if (assay['root']/'output'/assay['name']).exists():raise ValueError('Assay already has observations; no retry')
    out.mkdir(parents=True)
    plan={'version':'v06_sequential_postperformance_cloud_assays_001','created_utc':datetime.now(timezone.utc).isoformat(),
        'wrapper_sha256':digest(__file__),'before_any_assay_execution':True,'original_scientific_runtimes_unchanged':True,
        'waiting_performance_launcher_pid':perf_launcher['launcher_pid'],'waiting_performance_worker_pid':perf_launch['child_pid'],
        'no_workload_overlap':True,'retries':0,'additional_outer_assay_guard':None,
        'assays':[{**a,'root':str(a['root']),'registration':str(a['registration'])} for a in assays],
        'online_model_calls':0,'extra_original_full_TEST_certificate_calls':0}
    write_new(out/'queue_plan.json',plan)
    while not (perf_out/'server_execution_receipt.json').exists() or live(perf_launcher['launcher_pid']) or live(perf_launch['child_pid']):
        status={'phase':'waiting_for_original_performance_batch_and_archive','timestamp_unix':time.time(),
                'performance_launcher_live':live(perf_launcher['launcher_pid']),'performance_worker_live':live(perf_launch['child_pid'])}
        (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
        time.sleep(15)
    write_new(out/'performance_terminal_dependency.json',{'receipt':read(perf_out/'server_execution_receipt.json'),
        'receipt_sha256':digest(perf_out/'server_execution_receipt.json'),'launcher_live':False,'worker_live':False,'timestamp_unix':time.time()})
    for index,assay in enumerate(assays):
        root=assay['root'];result=root/'output'/assay['name'];start=time.monotonic()
        (out/'status.json').write_text(json.dumps({'phase':'assay_running','assay':assay['name'],'timestamp_unix':time.time()},indent=2)+'\n')
        with (out/(assay['name']+'.log')).open('xb') as log:
            child=subprocess.Popen(assay['command'],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=True,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
            write_new(out/(assay['name']+'_launch.json'),{'pid':child.pid,'command':assay['command'],'timestamp_unix':time.time(),
                'source_prepared_freeze_sha256':assay['freeze_sha256'],'root_release_sha256':assay['root_release_sha256'],'attempt':1})
            code=child.wait()
        receipt={'assay':assay['name'],'exit_code':code,'wall_seconds':time.monotonic()-start,'retries':0,'partial_results_retained':True,
            'root_release_sha256':assay['root_release_sha256'],'registration_freeze_sha256':assay['freeze_sha256'],
            'log_sha256':digest(out/(assay['name']+'.log')),'completed_marker_exists':(result/'complete.json').exists()}
        write_new(out/(assay['name']+'_execution.json'),receipt)
        archive=root/'experiments/runs/v06'/(assay['name']+'.tar.gz');archive.parent.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,'x:gz') as tar:
            if result.exists():tar.add(result,arcname=assay['name'])
            tar.add(assay['registration'],arcname='registration')
            for name in ('queue_plan.json','performance_terminal_dependency.json',assay['name']+'.log',
                         assay['name']+'_launch.json',assay['name']+'_execution.json'):
                tar.add(out/name,arcname='transport/'+name)
            tar.add(__file__,arcname='transport/sequential_queue_wrapper.py')
        write_new(out/(assay['name']+'_archive.json'),{'archive':str(archive),'archive_sha256':digest(archive),'bytes':archive.stat().st_size,
            'exit_code':code,'all_original_result_bytes_retained':True})
    write_new(out/'queue_complete.json',{'all_three_assays_attempted_once':True,'timestamp_unix':time.time(),'retries':0})
    (out/'status.json').write_text(json.dumps({'phase':'all_assays_terminal','timestamp_unix':time.time()},indent=2)+'\n')
    print(json.dumps({'queue_complete':str(out/'queue_complete.json')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('heldout-root','bridge-root','performance-root','out'):parser.add_argument('--'+name,required=True)
    run(**vars(parser.parse_args()))
