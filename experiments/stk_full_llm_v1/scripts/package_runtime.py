"""Package only research runtime and explicitly named, non-secret artifacts."""
import hashlib,json,pathlib,zipfile
here=pathlib.Path(__file__).resolve().parents[1]
repo=here.parents[1]
out=here/'cloud';out.mkdir(exist_ok=True)
archive=out/'runtime.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((repo/'cipheur').glob('*.py')):z.write(p,'code/cipheur/'+p.name)
    for p in sorted((here/'scripts').glob('*.py')):z.write(p,'scripts/'+p.name)
    z.write(here/'protocol.pre_generation.json','protocol.pre_generation.json')
    z.write(repo/'examples/frozen_joint_bank_v06.json','old_frozen_bank.json')
manifest={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':[]}
with zipfile.ZipFile(archive) as z:
    manifest['files']=[{'path':n,'sha256':hashlib.sha256(z.read(n)).hexdigest()} for n in z.namelist()]
(out/'runtime_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'path':str(archive),'sha256':manifest['archive_sha256'],'file_count':len(manifest['files'])}))
