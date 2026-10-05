"""Launch only this experiment's registered queue, with a recoverable receipt."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--python',required=True);ap.add_argument('--stage',choices=('development','development_round2','comparison'),required=True)
    args=ap.parse_args();root=args.root.resolve()
    assert root.parent==Path('/root/autodl-tmp') and root.name in ('cipheur_stk_online_llm_20261006_001','cipheur_stk_online_llm_20261006_002')
    jobs=root/'registrations'/args.stage/'jobs.jsonl';reg=jobs.with_name('registration.json')
    assert jobs.is_file() and reg.is_file()
    registration=json.loads(reg.read_text(encoding='utf-8'))
    assert registration['status']=='ready'
    assert hashlib.sha256(jobs.read_bytes()).hexdigest()==registration['jobs_sha256']
    receipt=root/(args.stage+'_launch.json');assert not receipt.exists(),'No duplicate queue launch'
    argv=[args.python,str(root/'scripts/run_queue.py'),'--jobs',str(jobs),
        '--output-root',str(root/args.stage),'--workers','8','--hard-wall-seconds','180',
        '--protocol',str(reg)]
    with (root/(args.stage+'_queue.log')).open('xb') as stream:
        proc=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    record=dict(pid=proc.pid,argv=argv,stage=args.stage,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        jobs_sha256=registration['jobs_sha256'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        owned_root=str(root),other_projects_touched=False)
    receipt.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record))
