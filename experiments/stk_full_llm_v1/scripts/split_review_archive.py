"""Store a review archive in exact ordered 48 MiB parts for public Git."""
import argparse,hashlib,json,pathlib

ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);a=ap.parse_args()
archive=a.archive.resolve();parts=[];total=hashlib.sha256()
with archive.open('rb') as f:
    i=1
    for block in iter(lambda:f.read(48*1024*1024),b''):
        target=archive.with_name(archive.name+'.part%02d'%i)
        if target.exists():raise SystemExit('Preserve existing part: '+str(target))
        target.write_bytes(block);total.update(block)
        parts.append({'path':target.name,'bytes':len(block),'sha256':hashlib.sha256(block).hexdigest()});i+=1
manifest={'archive_name':archive.name,'archive_bytes':archive.stat().st_size,'archive_sha256':total.hexdigest(),
          'parts_in_order':parts,'reconstruction':'Concatenate bytes in listed order, verify SHA256, then open the archive.'}
path=archive.with_name(archive.name+'.parts.json')
if path.exists():raise SystemExit('Preserve existing manifest')
path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'parts':len(parts),'bytes':manifest['archive_bytes'],'sha256':manifest['archive_sha256']}))
