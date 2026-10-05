import datetime,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];out=root/'train_round2';out.mkdir(exist_ok=True)
receipt=out/'started.json'
if receipt.exists():raise SystemExit('Already launched; never duplicate candidate evaluations')
argv=[sys.executable,str(root/'scripts/train_candidate_runner.py'),'--register','--execute',
      '--manifest',str(out/'registration/manifest.json'),'--data-root','/root/autodl-tmp/cipheur_stk_p0_20261005_001/data',
      '--cipheur-root',str(root/'code'),'--output-root',str(out),'--protocol',str(root/'protocol.pre_generation.json'),
      '--program-bank',str(root/'round2_bank.json'),'--shuffle-seed','20261006']
with (out/'runner.stdout').open('wb') as stdout,(out/'runner.stderr').open('wb') as stderr:
    proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
state={'pid':proc.pid,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,
       'scope':'TRAIN full schedules only; newly generated round2 candidates, no repeated first-round evaluations'}
receipt.write_text(json.dumps(state,indent=2),encoding='utf-8');print(json.dumps(state))
