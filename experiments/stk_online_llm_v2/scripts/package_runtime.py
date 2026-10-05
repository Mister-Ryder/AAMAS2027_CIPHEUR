"""Package the exact registered executable sources, not a live working tree."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(registration, output):
    registration=Path(registration);output=Path(output)
    reg=json.loads(registration.read_text(encoding='utf-8'))
    if reg['status']!='ready':raise ValueError('Ready registration required')
    if output.exists():raise FileExistsError(output)
    items={}
    for row in reg['code']:
        data=Path(row['local_path']).read_bytes()
        if sha(data)!=row['sha256']:raise ValueError('Changed registered source: '+row['local_path'])
        items[row['relative_runtime_path']]=data
    for kind in ('banks','controller_configs'):
        for row in reg.get(kind,{}).values():
            data=Path(row['local_path']).read_bytes()
            if sha(data)!=row['sha256']:raise ValueError('Changed registered declaration')
            items[Path(row['local_path']).parent.name+'/'+Path(row['local_path']).name]=data
    jobs=registration.parent/reg['jobs_filename'];data=jobs.read_bytes()
    if sha(data)!=reg['jobs_sha256']:raise ValueError('Changed registered jobs')
    items['registrations/'+reg['stage']+'/jobs.jsonl']=data
    items['registrations/'+reg['stage']+'/registration.json']=registration.read_bytes()
    manifest={name:sha(data) for name,data in items.items()}
    items['runtime_manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(items.items()):archive.writestr(name,data)
    print(json.dumps(dict(path=str(output),sha256=sha(output.read_bytes()),members=len(items))))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--registration',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    main(args.registration,args.output)
