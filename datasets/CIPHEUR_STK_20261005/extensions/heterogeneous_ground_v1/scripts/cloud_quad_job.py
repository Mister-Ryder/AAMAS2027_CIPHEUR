"""One independent, CPU-pinned cloud execution of registered joint evidence."""
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
parser.add_argument('--source', choices=['CP-AU-r000', 'CP-AP-r000', 'CP-AU-r001', 'CP-AP-r001'], required=True)
parser.add_argument('--cpu', type=int, required=True)
parser.add_argument('--script-sha256', required=True)
args = parser.parse_args()
root = args.workspace.resolve()
extension = root/'data/extensions/heterogeneous_ground_v1'
script = extension/'scripts/heterogeneous_evidence.py'
digest = hashlib.sha256(script.read_bytes()).hexdigest()
if digest != args.script_sha256:
    raise ValueError('Frozen joint evidence script changed')
if args.cpu not in os.sched_getaffinity(0):
    raise ValueError('CPU outside permitted affinity')
jobs = extension/'cloud_jobs'; jobs.mkdir(exist_ok=True)
receipt_path = jobs/(args.source+'.json')
if receipt_path.exists():
    raise ValueError('Do not overwrite an existing cloud job')
os.sched_setaffinity(0, {args.cpu})
argv = [sys.executable, str(script), '--data-root', str(root/'data'),
    '--cipheur-root', str(root/'code'), '--extension-root', str(extension), '--source', args.source,
    '--no-aggregate']
receipt = dict(state='running', source=args.source, wrapper_pid=os.getpid(),
    hostname=socket.gethostname(), platform=platform.platform(), python=sys.version,
    affinity=sorted(os.sched_getaffinity(0)), initial_load=os.getloadavg(), argv=argv,
    evidence_script_sha256=digest,
    graph_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((extension/'graphs'/args.source).glob('*.npz'))},
    started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='Two-resource-group heterogeneous TRAIN development; same four original STK libraries',
    timing_interpretation='Per-head diagnostic timing on a shared host; not repeated equal-time benchmark')
receipt_path.write_text(json.dumps(receipt, indent=2))
env = os.environ.copy()
env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONHASHSEED='0')
start = time.perf_counter()
try:
    with (jobs/(args.source+'.log')).open('w') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env)
        receipt['analysis_pid'] = process.pid
        receipt_path.write_text(json.dumps(receipt, indent=2))
        code = process.wait()
    receipt.update(state='completed' if code == 0 else 'failed', exit_code=code)
except Exception as error:
    code = 1
    receipt.update(state='failed', error=repr(error))
receipt.update(wall_seconds=time.perf_counter()-start,
    finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
receipt_path.write_text(json.dumps(receipt, indent=2))
sys.exit(code)
