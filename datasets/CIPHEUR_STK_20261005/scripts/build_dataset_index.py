"""Index completed artifacts from saved manifests, without rerunning experiments."""
from pathlib import Path
import datetime
import hashlib
import json

root = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((root/name).read_text(encoding='utf-8'))
main = read('analysis/p0/acceptance.json')
probe = read('analysis/patch_interface_probe/acceptance.json')
joint = read('analysis/joint_quotient/union_receipt.json')
physical = read('STK_P0_RUN_MANIFEST.json')
jobs = []
for path in sorted((root/'analysis/cloud_execution/jobs').glob('*.json')):
    item = json.loads(path.read_text())
    jobs.append(dict(file=path.relative_to(root).as_posix(), state=item.get('state'),
        exit_code=item.get('exit_code'), host=item.get('hostname', item.get('host')),
        started_utc=item.get('started_utc'), finished_utc=item.get('finished_utc')))
references = ['STK_P0_RUN_MANIFEST.json', 'source_plan/CIPHEUR_parameters.json',
    'analysis/input_contract.json', 'analysis/dataset_profile.json', 'analysis/execution_profile.json',
    'analysis/cloud_code_snapshot.json', 'analysis/cloud_code_bundle.zip',
    'analysis/p0/acceptance.json', 'analysis/patch_interface_probe/acceptance.json',
    'analysis/joint_quotient/union_receipt.json', 'analysis/joint_quotient/complete_demanded_quotient_union.json']
for pattern in ['raw/*/manifest.json', 'graphs/*/summary.json']:
    references.extend(p.relative_to(root).as_posix() for p in sorted(root.glob(pattern)))
references.extend('scripts/'+name for name in ['p0_evidence.py', 'p0_patch_interface_probe.py',
    'aggregate_union.py', 'stk_generate.py', 'build_graphs.py', 'profile_dataset.py', 'profile_execution.py'])
index = dict(dataset='CIPHEUR_STK_20261005',
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='P0_DATA_AND_DIAGNOSTICS_COMPLETE_G2_NOT_ESTABLISHED',
    root_relative_paths=True, source_groups=2, raw_libraries=4,
    full_planning_contacts=physical['total_full_planning_contacts'], graphs=16,
    split='TRAIN only', validation_sources_read=0, test_sources_read=0,
    main_queries=sum(s['queries'] for s in main['source_summaries']),
    main_relations={label:sum(s['relations'].get(label, 0) for s in main['source_summaries'])
                   for label in ['reversal', 'preservation']},
    interface_queries=sum(s['executed_queries'] for s in probe['source_summaries']),
    interface_different_value_states=probe['B&B']['different_final_patch_value_states'],
    interface_states=probe['B&B']['states'],
    joint_quotient={k:v for k,v in joint.items() if k != 'inventory'},
    P1_started=False, P2_started=False, LLM_calls_in_this_study=0,
    formal_cloud_jobs=jobs,
    references=[dict(path=name, bytes=(root/name).stat().st_size,
        sha256=hashlib.sha256((root/name).read_bytes()).hexdigest()) for name in references],
    primary_report='analysis/P0证据分析.md',
    authoritative_results=['analysis/p0', 'analysis/patch_interface_probe', 'analysis/joint_quotient'],
    limitations=['Idealized geometry; future EOP values are forecasts',
        'Microsecond encoding is not a claim of physical event accuracy',
        'Certificates are restricted F/P/X optima, not full72h optima',
        'No cycle in finite demands does not prove global absence of an obstruction',
        'Old frozen head is a control; no new LLM synthesis advantage claimed',
        'Four libraries and overlapping patches are not independent statistical samples'])
(root/'DATASET_INDEX.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'cloud_jobs':len(jobs), 'job_states':[j['state'] for j in jobs],
    'contacts':index['full_planning_contacts'], 'graphs':index['graphs'],
    'G2':joint['G2'], 'index_written':True}))
