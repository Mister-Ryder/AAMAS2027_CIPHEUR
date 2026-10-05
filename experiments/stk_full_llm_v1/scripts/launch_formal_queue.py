"""Start the pre-frozen formal queue once without occupying the SSH session."""
import datetime,json,pathlib,subprocess,sys

root=pathlib.Path(__file__).resolve().parents[1]
receipt=root/'formal_queue_start.json'
if receipt.exists() or (root/'formal_queue_receipt.json').exists():
    raise SystemExit('Existing formal queue; do not duplicate')
for filename in ['frozen_final8.json','final_program_ids.json','protocol.frozen.json']:
    if not (root/filename).is_file():raise SystemExit('Missing final freeze: '+filename)
with receipt.open('x',encoding='utf-8') as record:
    with (root/'formal_queue.stdout.txt').open('w') as out,(root/'formal_queue.stderr.txt').open('w') as err:
        process=subprocess.Popen([sys.executable,str(root/'scripts/run_formal_queue.py')],
                                 stdout=out,stderr=err,start_new_session=True)
    data={'pid':process.pid,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'stages':['final_train','test'],'solver_cores_total':8,
          'execution':'serial, after exact programme and protocol freeze'}
    json.dump(data,record,indent=2)
print(json.dumps(data))
