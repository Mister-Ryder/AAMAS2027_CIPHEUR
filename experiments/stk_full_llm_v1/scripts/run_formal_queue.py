"""Register both frozen formal grids, then execute serially with eight CPUs total."""
import datetime,hashlib,json,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parents[1]
old=pathlib.Path('/root/autodl-tmp/cipheur_stk_p0_20261005_001/data')
runner=root/'scripts/stage_schedule_runner.py';bank=root/'frozen_final8.json';protocol=root/'protocol.frozen.json';ids=root/'final_program_ids.json'
native='/root/autodl-tmp/aamas2027_v03/baselines/CHILS/CHILS'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt=root/'formal_queue_receipt.json'
if receipt.exists():raise SystemExit('Formal queue was already started; do not rerun')
state={'started_utc':now(),'queue_pid':__import__('os').getpid(),'status':'pre_registering',
       'bank_sha256':sha(bank),'protocol_sha256':sha(protocol),'final_program_ids_sha256':sha(ids),
       'solver_cores_total':8,'stages':[]}
with receipt.open('x',encoding='utf-8') as f:json.dump(state,f,indent=2)
def save():receipt.write_text(json.dumps(state,indent=2),encoding='utf-8')
for stage,datapath in [('final_train',old),('test',root/'data')]:
    path=root/stage;path.mkdir(exist_ok=True)
    common=[sys.executable,str(runner),'--stage',stage,'--manifest',str(path/'registration/manifest.json'),
            '--data-root',str(datapath),'--cipheur-root',str(root/'code'),'--native-executable',native]
    register=common+['--register','--program-bank',str(bank),'--program-ids-json',str(ids),'--protocol',str(protocol),
                    '--budgets','2','10','--seeds','2','3','5','--shuffle-seed','20261007' if stage=='test' else '20261006']
    if stage=='final_train':register+=['--graph-root',str(old/'extensions/heterogeneous_ground_v1/graphs')]
    for m in ['degree','weight','grasp','local2swap','cp_sat','chils_ils','chils']:register+=['--method',m]
    entry={'stage':stage,'path':str(path),'registration_argv':register,'execution_argv':common+['--execute','--output-root',str(path/'results')]}
    with (path/'registration.stdout.txt').open('w') as out,(path/'registration.stderr.txt').open('w') as err:
        code=subprocess.run(register,stdout=out,stderr=err).returncode
    entry['registration_exitcode']=code;state['stages'].append(entry);save()
    if code:state['status']='registration_failed';save();raise SystemExit(code)
state['status']='executing_frozen_stages';save()
for entry in state['stages']:
    path=pathlib.Path(entry['path']);entry['started_utc']=now();save()
    with (path/'execution.stdout.txt').open('w') as out,(path/'execution.stderr.txt').open('w') as err:
        entry['execution_exitcode']=subprocess.run(entry['execution_argv'],stdout=out,stderr=err).returncode
    entry['ended_utc']=now();save()
    if entry['execution_exitcode']:state['status']='execution_incomplete';save();raise SystemExit(entry['execution_exitcode'])
    compact=[sys.executable,str(root/'scripts/compact_results.py'),'--stage-root',str(path/'results'),
             '--output',str(path/'metrics.json'),'--include-curves']
    entry['projection_exitcode']=subprocess.run(compact).returncode;save()
state.update(status='all_formal_stages_complete',ended_utc=now());save()
print(json.dumps(state))
