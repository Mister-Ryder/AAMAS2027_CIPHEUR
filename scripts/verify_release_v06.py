"""Verify a final V06 release, retaining historical evidence and exact bytes.

The final delivery contract is written only after the complete result analyses
and eight-body-page PDF exist. Routine CI verifies hashes and recorded result
identities; it does not rerun experiments, optimizers, or expensive mathematics.
"""
from __future__ import annotations
import argparse
from datetime import date
from hashlib import sha256
import json,re,subprocess
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'manifest/RELEASE_V06_SHA256.json'
RESULTS={
    'performance':'experiments/analysis/v06/performance_TEST_audit_v06_003.json',
    'R2':'experiments/analysis/v06/R2_heldout_result_audit_v06_002.json',
    'EoH':'experiments/analysis/v06/EoH_heldout_result_audit_v06_001.json',
    'bridge':'experiments/analysis/v06/TRAIN_patch_bridge_audit_v06_001.json',
}
ANALYSES={
    'performance':'experiments/analysis/v06/performance_TEST_analysis_v06_003/analysis.json',
    'heldout':'experiments/analysis/v06/heldout_mechanism_analysis_v06_001.json',
}
PERFORMANCE_BINDING='experiments/analysis/v06/performance_analysis_binding_v06_003.json'
PERFORMANCE_PACKS=(
    'experiments/analysis/v06/performance_analysis_parts_v06_003/manifest.json',
    'experiments/analysis/v06/performance_identity_estimates_parts_v06_003/manifest.json',
    'experiments/analysis/v06/performance_identity_contrasts_parts_v06_003/manifest.json',
)
BIBS=('paper/references_v03.bib','paper/references_extension_v05.bib','paper/drafts/v06/new_references.bib')

def path(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:raise ValueError('Unsafe release path')
    dest=(ROOT/Path(*p.parts)).resolve()
    if not dest.is_relative_to(ROOT.resolve()):raise ValueError('Release path leaves repository')
    return dest

def digest(name):
    h=sha256()
    with Path(name).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def bibliography():
    keys=[];result={}
    for name in BIBS:
        text=path(name).read_text(encoding='utf-8');fields='\n'.join(s.split('%',1)[0] for s in text.splitlines())
        if re.search(r'arxiv|eprint|preprint',fields,re.I):raise ValueError('Preprint in active bibliography')
        found=re.findall(r'@\w+\s*\{\s*([^,\s]+)',fields);keys.extend(found)
        result[name]={'sha256':digest(path(name)),'entries':len(found)}
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate active citation key')
    return result

def write_performance_binding():
    """Read the full final analysis once; routine CI uses its exact-byte parts."""
    canonical=path(ANALYSES['performance']);data=json.loads(canonical.read_bytes())
    if data.get('version')!='v06_audited_performance_analysis_001' or data.get('assignments')!=52548 or data.get('no_TEST_selection') is not True:
        raise ValueError('Require the complete frozen performance analysis')
    record={k:data[k] for k in ('version','assignments','independent_audit_sha256',
        'audited_rows_sha256','archive_sha256','bootstrap_replicates','bootstrap_seed',
        'analysis_source_sha256','analysis_config_sha256','registered_constants','no_TEST_selection')}
    record.update(canonical_path=ANALYSES['performance'],bytes=canonical.stat().st_size,sha256=digest(canonical),
        scope='Metadata extracted once from the complete analysis; exact canonical bytes are losslessly retained in parts.')
    dest=path(PERFORMANCE_BINDING)
    if dest.exists():
        if json.loads(dest.read_bytes())!=record:raise ValueError('Preserve a differing analysis binding')
    else:
        with dest.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(record,indent=2)+'\n')

def result_contract():
    audits={k:json.loads(path(n).read_bytes()) for k,n in RESULTS.items()}
    for key,report in audits.items():
        if type(report.get('errors')) is not int or report['errors']!=0 or type(report.get('checks')) is not int or report['checks']<=0:
            raise ValueError('Final independent result audit not passed: '+key)
    if audits['performance']['registered_constants']['total_assignments']!=52548:
        raise ValueError('Incomplete performance frame')
    if audits['R2']['requested_state_assignments']!=11664 or audits['EoH']['requested_state_assignments']!=1728:
        raise ValueError('Incomplete heldout frame')
    if audits['bridge']['assigned_score_positions']!=2760 or audits['bridge']['query_union_count']!=159:
        raise ValueError('Incomplete frozen patch bridge')
    performance=json.loads(path(PERFORMANCE_BINDING).read_bytes())
    heldout=json.loads(path(ANALYSES['heldout']).read_bytes())
    if performance['independent_audit_sha256']!=digest(path(RESULTS['performance'])) or performance['assignments']!=52548:
        raise ValueError('Performance analysis not bound to final audit')
    if performance['bootstrap_replicates']!=2000 or performance['bootstrap_seed']!=261004 or performance['no_TEST_selection'] is not True:
        raise ValueError('Changed frozen performance statistics')
    performance_packs=[]
    for name in PERFORMANCE_PACKS:
        pack=json.loads(path(name).read_bytes())
        if pack.get('version')!='v06_lossless_evidence_parts_001' or pack.get('content_transformations') is not False:
            raise ValueError('Unknown performance evidence packaging')
        if sum(p['bytes'] for p in pack['parts'])!=pack['bytes'] or len({p['path'] for p in pack['parts']})!=len(pack['parts']):
            raise ValueError('Incomplete performance evidence parts')
        performance_packs.append({'manifest':name,'manifest_sha256':digest(path(name)),**pack})
    if performance_packs[0]['canonical_path']!=ANALYSES['performance'] or performance_packs[0]['sha256']!=performance['sha256'] or performance_packs[0]['bytes']!=performance['bytes']:
        raise ValueError('Complete performance analysis bytes differ from binding')
    if heldout['frame']['kernel_positions']!=13392:raise ValueError('Heldout analysis omitted identities')
    if {b['independent_audit_sha256'] for b in heldout['metadata']['input_bindings']}!={digest(path(RESULTS['R2'])),digest(path(RESULTS['EoH']))}:
        raise ValueError('Heldout analysis not bound to final audits')
    asset_name='manifest/RELEASE_V06_ASSETS.json';assets=json.loads(path(asset_name).read_bytes())
    if assets.get('version')!='v06_public_release_assets_001' or assets.get('release')!='v0.6.0':
        raise ValueError('Missing large public evidence contract')
    if len(assets['assets'])!=1:raise ValueError('Unexpected evidence asset frame')
    asset=assets['assets'][0]
    if asset['sha256']!=audits['performance']['archive_sha256'] or asset['bytes']!=1493400484:
        raise ValueError('Large public evidence differs from audited cloud archive')
    expected_name='performance_r2_eoh_test_v06_003_inputs.tar.gz'
    if asset['name']!=expected_name or asset['canonical_path']!='experiments/runs/v06/'+expected_name or asset['url']!='https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR/releases/download/v0.6.0/'+expected_name:
        raise ValueError('Unexpected public evidence location')
    compact_pack_name='experiments/analysis/v06/heldout_compact_parts_v06_001/manifest.json'
    compact_pack=json.loads(path(compact_pack_name).read_bytes())
    if compact_pack.get('version')!='v06_lossless_evidence_parts_001' or compact_pack['sha256']!=heldout['compact_sha256'] or compact_pack['canonical_path']!='experiments/analysis/v06/heldout_mechanism_analysis_v06_001_compact.json' or compact_pack.get('content_transformations') is not False:
        raise ValueError('Full heldout compact not losslessly preserved')
    if sum(r['bytes'] for r in compact_pack['parts'])!=compact_pack['bytes'] or len({r['path'] for r in compact_pack['parts']})!=len(compact_pack['parts']):
        raise ValueError('Incomplete heldout evidence parts')
    return {'audits':{k:{'path':RESULTS[k],'sha256':digest(path(RESULTS[k])),'checks':r['checks'],'errors':0} for k,r in audits.items()},
        'analyses':{'performance':{'path':ANALYSES['performance'],'sha256':performance['sha256'],
            'binding':PERFORMANCE_BINDING,'binding_sha256':digest(path(PERFORMANCE_BINDING))},
            'heldout':{'path':ANALYSES['heldout'],'sha256':digest(path(ANALYSES['heldout']))}},
        'performance_lossless_evidence':performance_packs,
        'public_large_evidence':{'manifest':asset_name,'sha256':digest(path(asset_name)),'assets':assets['assets']},
        'heldout_compact_evidence':{'manifest':compact_pack_name,'sha256':digest(path(compact_pack_name)),'canonical_sha256':compact_pack['sha256'],'bytes':compact_pack['bytes'],'parts':compact_pack['parts']}}

def layout(pdf):
    from pypdf import PdfReader
    pdf=path(pdf);pages=PdfReader(pdf).pages;texts=[p.extract_text() or '' for p in pages]
    references=[i for i,t in enumerate(texts) if re.search(r'^\s*References\s*$',t,re.M|re.I)]
    if len(pages)!=9 or references!=[8]:raise ValueError('Require eight body pages and one reference page')
    body='\n'.join(texts[:8])
    if re.search(r'DRAFT RESULT INPUT|DRAFT:|Pending Result Inputs',body):raise ValueError('Pending results remain in final PDF')
    if not re.search(r'\bConclusion\b',texts[7]):raise ValueError('Body must finish on page eight')
    figures=re.findall(r'Figure\s+(\d+)\s*:',body);tables=re.findall(r'Table\s+(\d+)\s*:',body)
    if len(figures)<5 or len(tables)<2:raise ValueError('Expected substantive illustrations and comparison tables')
    return {'path':pdf.relative_to(ROOT).as_posix(),'sha256':digest(pdf),'body_pages':8,'reference_pages':1,
        'total_pages':9,'figures':len(figures),'tables':len(tables),
        'scope':'Mechanical page allocation; final scientific/visual check is recorded separately'}

def names():
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    return sorted(n for n in set(raw.decode('utf-8').split('\0')) if n and n!='manifest/RELEASE_V06_SHA256.json' and path(n).is_file())

def verify(write=False,pdf=None):
    if write:
        if not pdf or MANIFEST.exists():raise ValueError('Require final PDF and a new V06 manifest')
        write_performance_binding()
        record={'release':'0.6.0','date':date.today().isoformat(),'paper':layout(pdf),
            'bibliography':bibliography(),'results':result_contract(),
            'files':{n:{'bytes':path(n).stat().st_size,'sha256':digest(path(n))} for n in names()},
            'scope':'Exact source/results/artifacts; unsuccessful and unsupported assignments remain visible. No new experimental rollout.'}
        with MANIFEST.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    else:
        record=json.loads(MANIFEST.read_bytes())
        if record['release']!='0.6.0':raise ValueError('Wrong release contract')
        for name,r in record['files'].items():
            if path(name).stat().st_size!=r['bytes'] or digest(path(name))!=r['sha256']:raise ValueError('Changed release file: '+name)
        if bibliography()!=record['bibliography'] or result_contract()!=record['results']:raise ValueError('Changed final scientific identities')
        if pdf and layout(pdf)!=record['paper']:raise ValueError('Changed final paper allocation')
    print(json.dumps({'release':record['release'],'files':len(record['files']),'body_pages':8,'reference_pages':1,'result_audits':len(record['results']['audits'])}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--pdf')
    args=p.parse_args();verify(args.write,args.pdf)
