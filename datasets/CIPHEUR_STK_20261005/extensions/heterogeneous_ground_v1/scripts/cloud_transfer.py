"""Safe input and result transfer limited to the owned study workspace."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--unpack', action='store_true')
parser.add_argument('--collect', action='store_true')
args = parser.parse_args()
root = args.workspace.resolve()
extension = root/'data/extensions/heterogeneous_ground_v1'
if args.unpack:
    with zipfile.ZipFile(root/'heterogeneous_graph_input.zip') as archive:
        for item in archive.infolist():
            if not (root/item.filename).resolve().is_relative_to(root):
                raise ValueError('Unsafe ZIP path')
        archive.extractall(root)
    snapshot = json.loads((root/'heterogeneous_graph_input_snapshot.json').read_text())
    for item in snapshot:
        path = root/item['member']
        if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Input mismatch: {item["member"]}')
    print(json.dumps({'verified_input_files':len(snapshot)}))
if args.collect:
    files = []
    for directory in ('analysis', 'cloud_jobs'):
        files.extend(p for p in (extension/directory).rglob('*') if p.is_file())
    files.extend(p for p in extension.glob('*.json'))
    files.extend(p for p in (extension/'scripts').glob('*.py'))
    destination = extension/'cloud_results.zip'
    snapshot = []
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            member = path.relative_to(extension).as_posix()
            content = path.read_bytes()
            archive.writestr(member, content)
            snapshot.append({'member':member, 'bytes':len(content), 'sha256':hashlib.sha256(content).hexdigest()})
        archive.writestr('result_snapshot.json', json.dumps(snapshot, indent=2))
    print(json.dumps({'result_members':len(snapshot), 'zip_bytes':destination.stat().st_size}))
