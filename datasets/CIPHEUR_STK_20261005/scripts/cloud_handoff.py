"""Transfer only this study's frozen inputs and inspectable cloud results."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--source')
parser.add_argument('--collect', action='store_true')
args = parser.parse_args()
root = args.workspace.resolve()
if args.source:
    if args.source not in {'CP-AU-r000', 'CP-AP-r000', 'CP-AU-r001', 'CP-AP-r001'}:
        raise ValueError('Only preregistered P0 sources')
    with zipfile.ZipFile(root / f'cloud_input_{args.source}.zip') as archive:
        for member in archive.infolist():
            target = (root / member.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Unsafe ZIP member')
        archive.extractall(root)
    snapshot = json.loads((root / f'input_snapshot_{args.source}.json').read_text())
    for item in snapshot:
        path = root / item['member']
        if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Input hash mismatch: {item["member"]}')
    print(json.dumps({'source': args.source, 'verified_members': len(snapshot)}))
if args.collect:
    files = []
    for relative in ('data/analysis/p0', 'data/analysis/patch_interface_probe', 'jobs'):
        files.extend(p for p in (root / relative).rglob('*') if p.is_file())
    files.extend(p for p in root.glob('*.json') if p.name in {'environment.json', 'code_snapshot.json'} or p.name.startswith('input_snapshot_'))
    files.extend(root.glob('probe_queue*.py'))
    destination = root / 'cloud_results.zip'
    receipt = []
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            member = path.relative_to(root).as_posix()
            content = path.read_bytes()
            archive.writestr(member, content)
            receipt.append({'member': member, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
        archive.writestr('result_snapshot.json', json.dumps(receipt, indent=2))
    print(json.dumps({'result_members': len(receipt), 'zip_bytes': destination.stat().st_size}))
