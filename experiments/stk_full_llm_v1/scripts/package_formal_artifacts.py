"""Archive only the completed study's full result JSON, with per-file hashes."""
import datetime,hashlib,json,pathlib,zipfile

root=pathlib.Path(__file__).resolve().parents[1]
stages=['final_train','test','feature_diagnostic_train','feature_diagnostic_test']
out=root/'review_artifacts';out.mkdir(exist_ok=True)
archive=out/'formal_full_json.zip'
manifest_path=out/'manifest.json'
if archive.exists() or manifest_path.exists():raise SystemExit('Keep existing review archive')
files=[]
for stage in stages:
    base=root/stage
    summary=json.loads((base/'results/execution_summary.json').read_text())
    if summary['registered_jobs']!=summary['recorded_jobs'] or summary.get('missing_job_ids'):
        raise SystemExit('Incomplete formal grid: '+stage)
    for p in sorted((base/'results/results').glob('*.json')):
        files.append((p,stage+'/results/'+p.name))
    for p in [base/'results/jobs.jsonl',base/'results/execution_summary.json',
              base/'registration/manifest.json',base/'registration/programme_bank.json',
              base/'registration/protocol.json']:
        files.append((p,stage+'/'+p.relative_to(base).as_posix()))
inventory=[]
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p,name in files:
        data=p.read_bytes()
        inventory.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
        z.writestr(name,data)
    z.writestr('file_inventory.json',json.dumps(inventory,indent=2))
digest=hashlib.sha256()
with archive.open('rb') as f:
    for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
manifest={'archive':archive.name,'sha256':digest.hexdigest(),'bytes':archive.stat().st_size,
          'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'files':inventory,'scope':'Full registered result JSON and registration only; no credentials, runtime or duplicate native graph files.'}
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'archive':str(archive),'sha256':manifest['sha256'],'bytes':manifest['bytes'],'files':len(inventory)}))
