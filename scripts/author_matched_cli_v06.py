"""Run the V06 preregistered cold authoring cells; never assess candidates here.

Each native CLI session sees only its own frozen packet. Exact last messages
and event receipts are retained, including malformed or unsuccessful outputs.
No model override, credential access, candidate repair or outcome retry occurs.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CLI = Path('C:/Users/JIA/AppData/Local/OpenAI/Codex/bin/de8a38d2100ae498/codex.exe')
ARMS = ('witness', 'relations', 'objective')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def safe_configuration():
    # Read ordinary configuration only; never load any authentication file.
    path = Path.home() / '.codex' / 'config.toml'
    value = tomllib.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    return {key: value.get(key) for key in ('model', 'model_provider', 'model_reasoning_effort', 'model_reasoning_summary', 'profile')}

def execute_cell(block, arm, study, configured):
    stem = f'block_{block}_{arm}'
    work = ROOT / '.research' / 'v06_cli_workspaces' / stem
    if work.exists():
        raise RuntimeError('An authoring cell already exists; do not retry: ' + stem)
    work.mkdir(parents=True)
    receipts = study / 'receipts'
    packet = study / 'packets' / (stem + '.json')
    prompt_file = study / 'packets' / (stem + '.prompt.md')
    shutil.copyfile(packet, work / 'packet.json')
    prompt = prompt_file.read_text(encoding='utf-8')
    # A documented transport wrapper changes output location only. The frozen
    # scientific packet and its instructions are included verbatim below.
    wrapper = ('Registered V06 transport: this is a fresh isolated noninteractive authoring session. '
        'The frozen packet is provided below and also at packet.json in your current directory. '
        'Treat the absolute packet/response paths in the original prompt as provenance only. '
        'Read no files other than packet.json. Do not run evaluations, inspect existing programs, '
        'consult the internet, or access another directory. Return the exact requested JSON as your '
        'final assistant message, without Markdown fences or prose; the controller saves it. '
        'Do not attempt to write the original response path. All candidate failures will be retained.\n\n'
        'ORIGINAL FROZEN PROMPT\n' + prompt + '\nFROZEN PACKET\n' + packet.read_text(encoding='utf-8'))
    (receipts / (stem + '.input.txt')).write_text(wrapper, encoding='utf-8')
    raw_final = receipts / (stem + '.last_message.txt')
    events = receipts / (stem + '.events.jsonl')
    errors = receipts / (stem + '.stderr.txt')
    cmd = [str(CLI), 'exec', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only',
           '--json', '--cd', str(work), '--output-last-message', str(raw_final), '-']
    if safe_configuration() != configured:
        raise RuntimeError('Requested model/settings changed before authoring')
    started = time.time()
    print(json.dumps({'started': stem, 'utc': datetime.now(timezone.utc).isoformat()}), flush=True)
    with events.open('wb') as stdout, errors.open('wb') as stderr:
        child = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            child.communicate(wrapper.encode('utf-8'), timeout=1800)
            timed_out = False
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
            timed_out = True
    # Preserve a failed transport as an empty/malformed response, never repair it.
    if not raw_final.is_file():
        raw_final.write_bytes(b'')
    response = study / 'responses' / (stem + '.json')
    if response.exists():
        raise RuntimeError('Response already exists; no overwrite: ' + stem)
    shutil.copyfile(raw_final, response)
    usage = []
    observed_model = []
    for line in events.read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('usage') is not None:
            usage.append({'event_type': event.get('type'), 'usage': event['usage']})
        if event.get('model') is not None:
            observed_model.append(event['model'])
    receipt = {'cell': stem, 'block': block, 'arm': arm, 'exit_code': child.returncode,
        'timed_out': timed_out, 'wall_seconds': time.time()-started,
        'requested_configuration': configured, 'observed_model': observed_model or None,
        'usage_events': usage or None, 'packet_sha256': digest(packet),
        'frozen_prompt_sha256': digest(prompt_file),
        'wrapper_prompt_sha256': digest(receipts / (stem + '.input.txt')),
        'response_sha256': digest(response), 'cli_executable_sha256': digest(CLI),
        'command_flags': ['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--json','--cd','ISOLATED_PACKET_DIRECTORY','--output-last-message','CONTROLLER_RECEIPT','-'],
        'raw_event_sha256': digest(events), 'raw_stderr_sha256': digest(errors),
        'no_retry': True, 'no_candidate_assessment': True}
    write(receipts / (stem + '.receipt.json'), receipt)
    print(json.dumps({'completed': stem, 'exit_code': child.returncode, 'wall_seconds': receipt['wall_seconds'], 'response_bytes': response.stat().st_size}), flush=True)
    return receipt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', default='experiments/discovery/v06_authoring_001')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    study = ROOT / args.study
    if (study / 'authoring_completion.json').exists():
        raise RuntimeError('All-cell V06 authoring was already frozen; no rerun')
    protocol = json.loads((study / 'protocol.json').read_text(encoding='utf-8'))
    amendment = json.loads((study / 'transport_amendment.json').read_text(encoding='utf-8'))
    if digest(study / 'protocol.json') != amendment['original_protocol_sha256']:
        raise RuntimeError('Frozen protocol changed')
    for cell in amendment['cells']:
        if digest(study / 'packets' / cell['response_file']) != cell['packet_sha256']:
            raise RuntimeError('Frozen packet changed')
    for name in ('responses', 'receipts'):
        (study / name).mkdir(exist_ok=True)
    if list((study / 'responses').iterdir()) or list((study / 'receipts').iterdir()):
        raise RuntimeError('Preserve prior authoring files; expected an empty registered transport inventory')
    configured = safe_configuration()
    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(execute_cell, block, arm, study, configured)
                   for block in range(protocol['blocks']) for arm in ARMS]
        for future in as_completed(futures):
            records.append(future.result())
    if safe_configuration() != configured or len(records) != protocol['blocks'] * len(ARMS):
        raise RuntimeError('Incomplete or settings-changed authoring: assessment prohibited')
    completion = {'version': 'matched_cli_authoring_completion_v06',
        'transport_amendment_sha256': digest(study / 'transport_amendment.json'),
        'all_authoring_completed_before_assessment': True,
        'same_requested_model_and_settings_all_cells': True,
        'response_sha256': {r['cell']+'.json': r['response_sha256'] for r in sorted(records, key=lambda r:r['cell'])},
        'receipt_paths': {r['cell']: 'receipts/'+r['cell']+'.receipt.json' for r in records},
        'actual_model_and_usage': {r['cell']: {'requested_configuration':r['requested_configuration'], 'observed_model':r['observed_model'], 'usage_events':r['usage_events']} for r in records},
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'failed_transport_cells': [r['cell'] for r in records if r['exit_code'] or r['timed_out']],
        'no_candidate_assessment_or_replacement': True}
    write(study / 'authoring_completion.json', completion)
    print(json.dumps({'all_registered_authoring_cells_frozen': True, 'completion_sha256': digest(study/'authoring_completion.json')}), flush=True)

if __name__ == '__main__':
    main()
