from pathlib import Path
from datetime import datetime,timezone
import json,resource,subprocess,time,tarfile
root=Path('/root/autodl-tmp/aamas2027_v06_catalogue_cost_001')
started=datetime.now(timezone.utc).isoformat()
before=resource.getrusage(resource.RUSAGE_CHILDREN)
wall=time.perf_counter()
command=['timeout','--signal=TERM','--kill-after=30s','7200','/root/autodl-tmp/aamas2027_v03/py311/bin/python','scripts/run_catalogue_refinement_v06.py','execute','--study','study','--out','results','--workers','8']
with (root/'study.log').open('xb') as stream:
    child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
    code=child.wait()
after=resource.getrusage(resource.RUSAGE_CHILDREN)
receipt={'start_UTC':started,'end_UTC':datetime.now(timezone.utc).isoformat(),'exit_code':code,'outer_wall_seconds':time.perf_counter()-wall,'outer_child_user_CPU_seconds':after.ru_utime-before.ru_utime,'outer_child_system_CPU_seconds':after.ru_stime-before.ru_stime,'outer_guard_seconds':7200,'outer_guard_is_not_master_or_feature_budget':True,'all_partial_results_preserved':True,'no_TEST_or_R2_consumption':True,'command':command}
(root/'process_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
archive=Path('/root/autodl-tmp/aamas2027_v06_catalogue_cost_001.tar.gz')
with tarfile.open(archive,'x:gz') as tar:
    tar.add(root,arcname=root.name)
if archive.stat().st_size>=100000000: raise ValueError('archive exceeds declared100MB bound; retained without substitution')
