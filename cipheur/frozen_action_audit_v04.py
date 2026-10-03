"""Offline held-out actual-action audit of immutable TRAIN-selected programs.

Uses the existing sound TRAIN audit engine for evidence acquisition only.
No synthesis, parameter fitting, program selection, or online oracle calls.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys
import time
import zipfile

from .relevance_synthesis_v04 import train_context


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def task(payload):
    pair, side, bank, config, hashes = payload
    for name,expected in hashes.items():
        if sha256((Path(__file__).parent/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen evidence source changed: '+name)
    started=time.perf_counter()
    try:
        row=train_context((pair,side,bank,config))
        row.update(execution_complete=True,selection_permitted=False,
                   scope='offline held-out actual-action audit; finite frozen pool; no selection or proposal changes')
    except Exception as e:
        row={'pair_id':pair['id'],'side':side,'family':pair['family'],'graph':pair[side],
             'execution_complete':False,'selection_permitted':False,'rows':[],'states':[],
             'error':{'type':type(e).__name__,'message':str(e)},'scope':'explicit audit failure; no replacement evidence'}
    row['seconds']=time.perf_counter()-started
    return row


def run(data_path,frozen_path,config_path,out,workers=8):
    data_bytes,frozen_bytes,config_bytes=[Path(p).read_bytes() for p in (data_path,frozen_path,config_path)]
    config=json.loads(config_bytes);data=json.loads(data_bytes);frozen=json.loads(frozen_bytes)
    if (sha256(data_bytes).hexdigest()!=config['data_sha256'] or
        sha256(frozen_bytes).hexdigest()!=config['frozen_sha256'] or
        frozen['selection_split']!='train' or frozen['test_accessed'] is not False or
        config['selection_permitted'] is not False):
        raise ValueError('Require exact fixed data and TRAIN-only freeze')
    bank=[{'id':name,'program':frozen['programs'][name]} for name in config['program_ids']]
    if len(bank)!=len(set(config['program_ids'])):
        raise ValueError('Duplicate declared frozen pool program')
    tasks=[]
    for split in config['splits']:
        for pair in data[split]:
            for side in ('left','right'):tasks.append((pair,side,bank,config))
    if len(tasks)!=config['contexts']:
        raise ValueError('Fixed held-out context frame mismatch')
    root=Path(out);root.mkdir(parents=True,exist_ok=False)
    hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    (root/'data.json').write_bytes(data_bytes);(root/'frozen_programs.json').write_bytes(frozen_bytes)
    (root/'config.json').write_bytes(config_bytes);write(root/'program_pool.json',bank)
    with zipfile.ZipFile(root/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in hashes:z.write(Path(__file__).parent/name,'cipheur/'+name)
        z.writestr('config.json',config_bytes)
    write(root/'execution.json',{'scope':config['scope'],'data_sha256':sha256(data_bytes).hexdigest(),
        'frozen_sha256':sha256(frozen_bytes).hexdigest(),'config_sha256':sha256(config_bytes).hexdigest(),
        'source_sha256':hashes,'source_snapshot_sha256':sha256((root/'source_snapshot.zip').read_bytes()).hexdigest(),
        'workers':workers,'python':sys.version,'selection_permitted':False,'contexts':len(tasks),
        'model_calls':0,'oracle_scope':'offline audit only; deployed scoring program unchanged',
        'state_selection':'initial and most-covered recorded state within first two commitments; maximum two states per context',
        'population':'all 132 unused validation and 456 test contexts; original quality-study ASTs unchanged'})
    processed=failures=0;start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool,(root/'results.jsonl').open('w',encoding='utf-8') as stream:
        futures=[pool.submit(task,p+(hashes,)) for p in tasks]
        for future in as_completed(futures):
            row=future.result();processed+=1;failures+=not row['execution_complete']
            stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
            write(root/'progress.json',{'processed_contexts':processed,'assigned_contexts':len(tasks),
                                      'audit_failures':failures,'seconds':time.perf_counter()-start})
    write(root/'complete.json',{'execution_complete':processed==len(tasks),'contexts':processed,
        'audit_failures':failures,'selection_permitted':False,'results_sha256':sha256((root/'results.jsonl').read_bytes()).hexdigest()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data','frozen','config','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();run(a.data,a.frozen,a.config,a.out,a.workers)


if __name__=='__main__':main()
