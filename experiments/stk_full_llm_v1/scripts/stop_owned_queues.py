"""Stop only the two recorded study queues after the user's design redirect."""
import datetime,json,os,pathlib,signal,time

root=pathlib.Path(__file__).resolve().parents[1]
expected={13551:str(root/'scripts/run_formal_queue.py'),
          16446:str(root/'scripts/run_feature_diagnostic_queue.py')}

def process(pid):
    try:
        raw=pathlib.Path('/proc/%d/stat'%pid).read_text(); fields=raw[raw.rfind(')')+2:].split()
        cmd=pathlib.Path('/proc/%d/cmdline'%pid).read_bytes().replace(b'\0',b' ').decode(errors='replace')
        return {'pid':pid,'state':fields[0],'ppid':int(fields[1]),'start_ticks':int(fields[19]),'cmd':cmd}
    except (FileNotFoundError,ProcessLookupError):return None

def send(record,sig):
    current=process(record['pid'])
    if current and current['start_ticks']==record['start_ticks'] and current['state']!='Z':
        try:os.kill(record['pid'],sig)
        except ProcessLookupError:pass

targets={}
for pid,command in expected.items():
    p=process(pid)
    if p:
        if command not in p['cmd']:raise SystemExit('Recorded queue PID now belongs to another command; stop refused')
        targets[pid]=p;send(p,signal.SIGSTOP)
for _ in range(6):
    table={int(p.name):process(int(p.name)) for p in pathlib.Path('/proc').iterdir() if p.name.isdigit()}
    table={k:v for k,v in table.items() if v is not None}
    changed=True
    while changed:
        changed=False
        for pid,p in table.items():
            if pid not in targets and p['ppid'] in targets:
                targets[pid]=p;send(p,signal.SIGSTOP);changed=True
    time.sleep(.1)
for p in targets.values():send(p,signal.SIGTERM)
for p in targets.values():send(p,signal.SIGCONT)
time.sleep(2)
survivors=[p for p in targets.values() if (q:=process(p['pid'])) and q['start_ticks']==p['start_ticks'] and q['state']!='Z']
for p in survivors:send(p,signal.SIGKILL)
time.sleep(.3)
live=[p['pid'] for p in targets.values() if (q:=process(p['pid'])) and q['start_ticks']==p['start_ticks'] and q['state']!='Z']
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
reason='User requested instance-local adaptive heuristic/evolution; old frozen-selection study stopped, all artifacts retained.'
for name in ['formal_queue_receipt.json','feature_diagnostic_queue_receipt.json']:
    path=root/name
    if path.is_file():
        backup=path.with_name(path.stem+'.before_user_redirect.json')
        if backup.exists():raise SystemExit('Keep previous cancellation evidence')
        backup.write_bytes(path.read_bytes())
        data=json.loads(path.read_text());data.update(status='cancelled',ended_utc=now,cancelled_by='user_design_redirect',reason=reason)
        path.write_text(json.dumps(data,indent=2)+'\n')
receipt={'utc':now,'reason':reason,'verified_queue_roots':list(expected),'stopped_processes':list(targets.values()),
         'still_running_owned_pids':live,'test_result_files_preserved':len(list((root/'test/results/results').glob('*.json'))),
         'new_protocol_required':True,'other_projects_touched':False}
path=root/'user_design_redirect.json'
with path.open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps({'stopped_owned_processes':len(targets),'still_running_owned_pids':live,
                  'test_files_preserved':receipt['test_result_files_preserved'],'receipt':str(path)}))
if live:raise SystemExit(2)
