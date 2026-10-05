"""Byte-identical, unlabeled graph transport for expert reruns; never score TEST."""
import hashlib,json,pathlib,zipfile
study=pathlib.Path(__file__).resolve().parents[1]
data=study.parents[2]/'data'/'两篇论文数据定制化构建'/'CIPHEUR_STK_20261005'
out=study/'review_inputs';out.mkdir(exist_ok=True)
archive=out/'complete_graph_inputs.zip'
inventory=[]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    paths=[]
    for source in ['CP-AU-r000','CP-AP-r000','CP-AU-r001','CP-AP-r001']:
        for tag in ['gW0340_gE0340_s0150','gW1200_gE0340_s0150','gW0340_gE1200_s0150','gW1200_gE1200_s0150']:
            for ext in ['.npz','.json']:
                p=data/'extensions/heterogeneous_ground_v1/graphs'/source/(tag+ext)
                paths.append((p,'train/graphs/'+source+'/'+p.name))
    for source in ['CP-AU-r006','CP-AP-r006','CP-AU-r008','CP-AP-r008','CP-AU-r009','CP-AP-r009']:
        for p in sorted((data/'perf_dataset_v1/graphs'/source).glob('*')):
            if p.suffix in ['.npz','.json'] and p.stem.startswith('g'):
                paths.append((p,'heldout/graphs/'+source+'/'+p.name))
    for p,name in paths:
        z.write(p,name);inventory.append({'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    z.writestr('graph_input_inventory.json',json.dumps({'files':inventory,'scope':'unlabeled byte transport; no optimizer/feature or outcome selection'},ensure_ascii=False))
    z.write(data/'perf_dataset_v1/source_index.json','heldout/source_index.json')
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
parts=[];size=48*1024*1024
with archive.open('rb') as f:
    i=1
    while True:
        b=f.read(size)
        if not b:break
        p=out/('complete_graph_inputs.zip.part%02d'%i);p.write_bytes(b)
        parts.append({'path':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});i+=1
manifest={'archive_name':archive.name,'archive_sha256':sha,'archive_bytes':archive.stat().st_size,'parts_in_order':parts,'files':inventory,
          'reconstruction':'Concatenate binary parts in listed order, verify archive SHA256, unzip. train/graph root has16; heldout root has48 (16VAL including8unused configurations,32TEST). FormalVAL uses only A/W/E/J.'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(inventory),'archive_bytes':archive.stat().st_size,'archive_sha256':sha,'parts':len(parts)}))
