"""Run one preregistered P0 source and retain cloud execution provenance."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--source', required=True)
args = parser.parse_args()
workspace = args.workspace.resolve()
allowed = {'CP-AU-r000', 'CP-AP-r000', 'CP-AU-r001', 'CP-AP-r001'}
if args.source not in allowed:
    raise ValueError('Only the four planned P0 TRAIN libraries are enabled')
data, code = workspace/'data', workspace/'code'
script = data/'scripts/p0_evidence.py'
out = workspace/'jobs'; out.mkdir(exist_ok=True)
record_path = out/(args.source+'.json')
if record_path.exists():
    raise RuntimeError('Existing job receipt; choose a new run for retries')
argv = [sys.executable, str(script), '--data-root', str(data),
        '--cipheur-root', str(code), '--output-root', str(data/'analysis/p0'),
        '--source', args.source]
receipt = dict(source_id=args.source, state='running', wrapper_pid=os.getpid(),
    hostname=socket.gethostname(), platform=platform.platform(), python=sys.version,
    argv=argv, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    evidence_script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
    source_graph_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (data/'graphs'/args.source).glob('*.npz')},
    record_scope='Only new CIPHEUR P0 data, no previous experiment results')
record_path.write_text(json.dumps(receipt,indent=2))
started=time.perf_counter()
try:
    with (out/(args.source+'.log')).open('w') as stream:
        process=subprocess.Popen(argv,cwd=code,stdout=stream,stderr=subprocess.STDOUT)
        receipt['analysis_pid']=process.pid
        record_path.write_text(json.dumps(receipt,indent=2))
        result=process.wait()
    receipt.update(state='completed' if result==0 else 'failed',exit_code=result)
except Exception as error:
    receipt.update(state='failed',error=repr(error));result=1
receipt.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               wall_seconds=time.perf_counter()-started)
record_path.write_text(json.dumps(receipt,indent=2))
sys.exit(result)
