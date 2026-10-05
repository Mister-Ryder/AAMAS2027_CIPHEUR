import datetime,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
out=root/'train_round1'
out.mkdir(exist_ok=True)
receipt=out/'started.json'
if receipt.exists(): raise SystemExit('Already launched; do not duplicate registered runs')
bank=json.loads((root/'old_frozen_bank.json').read_text(encoding='utf-8'))
bank['programs']=[bank['programs'][0]]
(root/'old_first_bank.json').write_text(json.dumps(bank,ensure_ascii=False),encoding='utf-8')
argv=[sys.executable,str(root/'scripts/train_candidate_runner.py'),'--register','--execute',
      '--manifest',str(out/'registration/manifest.json'),'--data-root','/root/autodl-tmp/cipheur_stk_p0_20261005_001/data',
      '--cipheur-root',str(root/'code'),'--output-root',str(out),
      '--protocol',str(root/'protocol.pre_generation.json'),'--program-bank',str(root/'round1_bank.json'),
      '--program-bank',str(root/'grammar_bank.json'),'--program-bank',str(root/'old_first_bank.json'),
      '--native-executable','/root/autodl-tmp/aamas2027_v03/baselines/CHILS/CHILS']
for method in ['degree','weight','grasp','local2swap','cp_sat','chils_ils','chils']:argv+=['--method',method]
with (out/'runner.stdout').open('wb') as stdout,(out/'runner.stderr').open('wb') as stderr:
    proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
state={'pid':proc.pid,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'scope':'TRAIN only'}
receipt.write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
