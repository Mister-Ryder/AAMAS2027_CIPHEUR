"""Execute pre-registered, isolated CLI calls; preserve every real outcome."""
import argparse, concurrent.futures, datetime, hashlib, json, pathlib, subprocess, time

def run(plan_path):
    plan = json.loads(pathlib.Path(plan_path).read_text(encoding='utf-8'))
    receipt_path = pathlib.Path(plan['receipt_path'])
    if receipt_path.exists():
        return {'call_id':plan['call_id'], 'status':'already_recorded'}
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t = time.monotonic()
    receipt = {'call_id':plan['call_id'], 'started_utc':started, 'timeout_seconds':1200,
               'argv':plan['argv'], 'model_requested':plan['model_requested'],
               'model_observed':'unknown', 'prompt_sha256':plan['prompt_sha256']}
    print(json.dumps({'started':plan['call_id'], 'utc':started}), flush=True)
    with open(plan['stdin_path'],'rb') as inp, open(plan['stdout_path'],'wb') as out, open(plan['stderr_path'],'wb') as err:
        try:
            proc = subprocess.Popen(plan['argv'], stdin=inp, stdout=out, stderr=err,
                                    cwd=plan['working_directory'], creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            receipt['pid'] = proc.pid
            try:
                receipt['exit_code'] = proc.wait(timeout=1200)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
                receipt.update(exit_code=proc.returncode, timed_out=True)
        except Exception as exc:
            receipt.update(exit_code=None, error=repr(exc))
    receipt['wall_seconds'] = time.monotonic()-t
    receipt['ended_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    response = pathlib.Path(plan['response_path'])
    receipt['response_exists'] = response.is_file()
    if response.is_file():
        receipt['response_sha256'] = hashlib.sha256(response.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:receipt.get(k) for k in ['call_id','exit_code','wall_seconds','response_exists','timed_out']}),flush=True)
    return receipt

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--calls-root',required=True); ap.add_argument('--round',type=int,required=True); ap.add_argument('--workers',type=int,default=6)
    args=ap.parse_args()
    plans=sorted(pathlib.Path(args.calls_root).glob(f'*.r{args.round}.b*/call_plan.json'))
    if not plans: raise SystemExit('No registered plans')
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run,plans))
