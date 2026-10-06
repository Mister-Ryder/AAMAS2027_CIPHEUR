"""Run one bounded interface diagnostic and record actual cloud execution."""
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
args = parser.parse_args()
root = args.workspace.resolve()
script = root / 'data/scripts/p0_patch_interface_probe.py'
sha = hashlib.sha256(script.read_bytes()).hexdigest()
if sha != 'dd8db60b8118839da34862c87870c7f62e548d4573c63f02eb1d1d68fb27c872':
    raise ValueError('Frozen diagnostic script changed')
if not (root / 'data/analysis/p0' / args.source / 'summary.json').exists():
    raise ValueError('Complete original P0 source required')
receipt_path = root / 'jobs' / f'probe_{args.source}.json'
if receipt_path.exists():
    raise ValueError('Existing execution receipt; do not overwrite')
argv = [sys.executable, str(script), '--data-root', str(root/'data'),
        '--cipheur-root', str(root/'code'), '--p0-output-root', str(root/'data/analysis/p0'),
        '--output-root', str(root/'data/analysis/patch_interface_probe'), '--source', args.source]
record = dict(state='running', source=args.source, wrapper_pid=os.getpid(),
              host=socket.gethostname(), platform=platform.platform(), python=sys.version,
              argv=argv, script_sha256=sha,
              started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
receipt_path.write_text(json.dumps(record, indent=2))
start = time.perf_counter()
with (root/'jobs'/f'probe_{args.source}.log').open('w') as log:
    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
    record['analysis_pid'] = process.pid
    receipt_path.write_text(json.dumps(record, indent=2))
    exit_code = process.wait()
record.update(state='completed' if exit_code == 0 else 'failed', exit_code=exit_code,
              wall_seconds=time.perf_counter()-start,
              finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
receipt_path.write_text(json.dumps(record, indent=2))
sys.exit(exit_code)
