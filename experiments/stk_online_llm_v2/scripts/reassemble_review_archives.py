"""Reassemble exact Git-managed raw-result archive parts for expert review."""
import argparse
import hashlib
import json
from pathlib import Path


def main(manifest, destination):
    manifest=Path(manifest);record=json.loads(manifest.read_text(encoding='utf-8'))
    destination=Path(destination) if destination else manifest.parent/record['archive_name']
    if destination.exists():raise FileExistsError('Preserving existing archive: '+str(destination))
    destination.parent.mkdir(parents=True,exist_ok=True)
    total=hashlib.sha256();size=0
    with destination.open('xb') as output:
        for part in record['parts']:
            name=part['name']
            if Path(name).name!=name:raise ValueError('Part must be a direct file name')
            data=(manifest.parent/name).read_bytes()
            if len(data)!=part['bytes'] or hashlib.sha256(data).hexdigest()!=part['sha256']:
                raise ValueError('Part differs: '+name)
            output.write(data);total.update(data);size+=len(data)
    if size!=record['archive_bytes'] or total.hexdigest()!=record['archive_sha256']:
        raise ValueError('Full archive differs; preserve for inspection')
    print(json.dumps(dict(status='complete',path=str(destination),bytes=size,sha256=total.hexdigest())))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True,type=Path)
    ap.add_argument('--destination',type=Path);args=ap.parse_args()
    main(args.manifest,args.destination)
