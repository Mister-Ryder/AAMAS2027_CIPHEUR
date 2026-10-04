"""Verify V05 bytes/assignment inventories while preserving the V04 release.

This is a reproducibility check. Scientific and rendered-figure reviews are
separate records; successful assignment execution does not mean solver success.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile
from verify_release_v04 import archive_inventory, completion_checks, digest, digest_stream, safe_name

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'manifest/RELEASE_V05_SHA256.json'
LEGACY_COMMIT = 'de0f70565eb56ceb6c2d2324481017a94782ec62'
TRANSFER_STEM = 'matched_transfer_exploratory_v05_001'
TRANSFER_PROTOCOL_SHA256 = '8f785558ace072936baf2e29b2c3585c1cf3fd8528036ad2398695f9cb061288'
TRANSFER_SOURCE_SHA256 = '81cee9ea27374ba055cc15a6af11d810c7aad68982a1830fbae045d202031b62'
TRANSFER_RUN_SHA256 = '4b4888820ac71797aa5f1e05980f0216fd94acac2f9e17f65340001fdc8536a2'
TRANSFER_AUDIT_SHA256 = 'c5036112bb35d4d413b2cd4ef0821d507dbe08502fc5c9e251afdb4348b89231'
TRANSFER_POPULATIONS = {'DIMACS_unit':18, 'DIMACS_hash_weighted':18,
                        'SATLIB_unit':30, 'SATLIB_hash_weighted':30, 'C3':24}

def paths():
    output = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'], cwd=ROOT)
    return sorted({x.decode('utf-8') for x in output.split(b'\0') if x
                   and x.decode('utf-8') != MANIFEST.relative_to(ROOT).as_posix()})

def legacy_checks():
    legacy = json.loads((ROOT/'manifest/RELEASE_V04_SHA256.json').read_text(encoding='utf-8'))
    prefixes = ('experiments/', 'baselines/')
    names = [n for n in legacy['files'] if n.startswith(prefixes)
             or n in ('paper/aamas.cls','paper/ACM-Reference-Format.bst')
             or n.startswith('paper/figures/')]
    for name in names:
        assert digest(ROOT/safe_name(name)) == legacy['files'][name], 'Changed legacy evidence/template: '+name
    return {'release_commit':LEGACY_COMMIT, 'preserved_evidence_asset_files':len(names),
            'old_full_release_manifest_sha256':digest(ROOT/'manifest/RELEASE_V04_SHA256.json'),
            'completed_studies':completion_checks(),
            'scope':'V04 current evidence/assets remain unchanged; old source/paper are recoverable at the immutable release commit'}

def read_member(stem, name):
    archive = ROOT/'experiments/runs/v05'/(stem+'.tar.gz')
    with tarfile.open(archive,'r:gz') as tar:
        return json.load(tar.extractfile(stem+'/'+name))

def source_snapshot(stem):
    """Check the preserved source capsule, without extracting or interpreting it."""
    receipt_path = ROOT/'experiments/source_snapshots/v05'/(stem+'_source_receipt.json')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    archive = ROOT/safe_name(receipt['archive'])
    assert digest(archive) == receipt['sha256'], 'Changed source capsule: '+stem
    assert archive.stat().st_size == receipt['bytes']
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        assert len(names) == len(set(names)), 'Duplicate source capsule member: '+stem
        for name in names:
            safe_name(name)
        assert set(names) == set(receipt['files']) | {'MANIFEST.json'}
        manifest = json.loads(source.read('MANIFEST.json'))
        assert manifest['files'] == receipt['files']
        for name, expected in receipt['files'].items():
            with source.open(safe_name(name).as_posix()) as stream:
                assert digest_stream(stream) == expected, 'Changed capsule source: '+name
    return receipt

def public_study():
    """Link the frozen public query plan to completed, separate-track execution."""
    stem = 'public_alias_v05_001'
    study = ROOT/'experiments/discovery/public_alias_v05'
    freeze = json.loads((study/'freeze_receipt.json').read_text(encoding='utf-8'))
    config = json.loads((study/'config.json').read_text(encoding='utf-8'))
    source = source_snapshot(stem)
    assert freeze['version'] == 'public_alias_input_freeze_v05_001'
    assert config['version'] == stem and freeze['before_any_query'] is True
    assert freeze['no_programme_selection'] is True
    for name, key in (('config.json','config_sha256'), ('program.json','program_sha256'),
                      ('data.json','data_sha256')):
        expected = digest(study/name)
        assert expected == freeze[key]
        assert expected == source['files']['experiments/discovery/public_alias_v05/'+name]
    assert digest(study/'freeze_receipt.json') == source['files']['experiments/discovery/public_alias_v05/freeze_receipt.json']
    assert digest(ROOT/safe_name(config['input_archive'])) == config['input_archive_sha256'] == freeze['input_archive_sha256']
    assert digest(ROOT/safe_name(config['frozen_program'])) == config['frozen_program_bytes_sha256']
    program = json.loads((study/'program.json').read_text(encoding='utf-8'))
    original_program = json.loads((ROOT/safe_name(config['frozen_program'])).read_text(encoding='utf-8'))
    assert program == original_program
    canonical = sha256(json.dumps(program,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert canonical == config['frozen_program_canonical_sha256']
    assert config['registered_graph_states'] == 61 and config['workers'] == 4
    assert config['no_new_model_calls'] and config['no_programme_selection_or_tuning']
    assert config['induced_track_is_not_full_benchmark_or_natural_physical_scheduling']
    assert config['all_unknowns_and_query_shortfalls_retained']
    for name, expected in freeze['source_sha256'].items():
        assert source['files']['cipheur/'+safe_name(name).as_posix()] == expected
    execution = read_member(stem,'execution.json')
    assert execution['source_sha256'] == freeze['source_sha256']
    assert execution['input_freeze_sha256'] == digest(study/'freeze_receipt.json')
    assert execution['workers'] == config['workers']
    assert execution['state_wall_seconds'] == config['state_wall_seconds']
    assert execution['new_model_calls'] == 0 and execution['new_programme_selection'] is False
    assert execution['no_frozen_AST_change'] is True and execution['query_order_frozen_before_queries'] is True
    complete = read_member(stem,'complete.json')
    assert complete['execution_complete'] is True and complete['states'] == 61
    assert complete['unknowns_retained'] and complete['full_and_induced_never_pooled']
    assert complete['LLM_benefit_not_identified'] is True
    tracks = complete['track_summary']
    assert set(tracks) == {'full_public_unit','source_induced32_unit'}
    assert tracks['full_public_unit']['states'] == 13
    assert tracks['source_induced32_unit']['states'] == 48
    assert sum(t['states'] for t in tracks.values()) == complete['states']
    assert sum(t['assigned_queries'] for t in tracks.values()) == 324
    assert sum(t['query_shortfall'] for t in tracks.values()) == 61*8-324
    for track in tracks.values():
        assert sum(track['status'].values()) == track['assigned_queries']
        assert track['strict_self_loops'] == track['status'].get('strict',0)
        assert 0 <= track['primary_pair_agreements'] <= track['strict_self_loops']
    with tarfile.open(ROOT/'experiments/runs/v05'/(stem+'.tar.gz'),'r:gz') as run:
        for name in ('config.json','program.json','data.json','freeze_receipt.json'):
            assert digest_stream(run.extractfile(stem+'/'+name)) == digest(study/name)
        assert digest_stream(run.extractfile(stem+'/results.jsonl')) == complete['results_sha256']
        assert sum(bool(line.strip()) for line in run.extractfile(stem+'/results.jsonl')) == complete['states']
    return complete

def transfer_study():
    """Bind the repeated-graph extension without rerunning execution or audits.

    External stable-source CSV access is not required for a clean Git archive:
    its original byte identity is retained in every frozen C3 source record and
    the separate independent audit. No host-specific recorded path is opened.
    """
    stem = TRANSFER_STEM
    study = ROOT/'experiments/discovery'/stem
    source_path = ROOT/'experiments/source_snapshots/v05'/(stem+'_source.zip')
    receipt_path = source_path.with_name(stem+'_source_receipt.json')
    source = json.loads(receipt_path.read_text(encoding='utf-8'))
    assert source['before_any_extension_execution'] is True
    assert digest(source_path) == source['source_zip_sha256'] == TRANSFER_SOURCE_SHA256
    protocol = json.loads((study/'protocol.json').read_text(encoding='utf-8'))
    freeze = json.loads((study/'freeze_receipt.json').read_text(encoding='utf-8'))
    data = json.loads((study/'data.json').read_text(encoding='utf-8'))
    frozen = json.loads((study/'frozen_programs.json').read_text(encoding='utf-8'))
    clarification = json.loads((study/'budget_scope_clarification.json').read_text(encoding='utf-8'))
    assert digest(study/'protocol.json') == freeze['protocol_sha256'] == TRANSFER_PROTOCOL_SHA256
    assert protocol['version'] == freeze['version'] == stem
    assert protocol['before_any_extension_execution'] is freeze['before_any_extension_execution'] is True
    assert protocol['no_authoring_no_test_selection'] and protocol['all_assigned_banks_retained']
    assert protocol['contexts'] == 120 and protocol['methods_per_context'] == 13 and protocol['assignments'] == 1560
    assert protocol['population_counts'] == TRANSFER_POPULATIONS
    assert protocol['program_cpu_seconds'] == 5 and protocol['workers'] == 16
    assert protocol['hard_wall_safety_no_context_progress_seconds'] == 1800
    for name in ('data', 'frozen_programs'):
        assert digest(study/(name+'.json')) == freeze[name+'_sha256'] == protocol[name+'_sha256']
    assert digest(ROOT/'configs/matched_transfer_exploratory_v05.json') == protocol['config_sha256']
    with zipfile.ZipFile(source_path) as capsule:
        names = capsule.namelist()
        assert len(names) == len(set(names)) and set(names) == set(source['file_sha256'])
        for name, expected in source['file_sha256'].items():
            safe_name(name)
            assert sha256(capsule.read(name)).hexdigest() == expected == digest(ROOT/safe_name(name))
        for name, expected in freeze['source_sha256'].items():
            assert source['file_sha256'][safe_name(name).as_posix()] == expected
        for name, expected in frozen['source_sha256'].items():
            assert source['file_sha256']['cipheur/'+safe_name(name).as_posix()] == expected
        assert not any(name.endswith('/budget_scope_clarification.json') for name in names), 'Clarification is append-only, not the original freeze'
    methods = {f'block_{block}_{arm}' for block in range(4) for arm in ('witness','relations','objective')}
    assert set(protocol['programs']) == set(frozen['programs']) == set(frozen['selection']) == methods
    assert frozen['selection_split'] == 'train' and frozen['test_accessed'] is False
    source_archives = {'public':'experiments/runs/v04/advanced_public_v04_001.tar.gz',
                       'fresh':'experiments/runs/v04/advanced_fresh_v04_001.tar.gz',
                       'train':'experiments/runs/v05/matched_train_v05_001.tar.gz'}
    for kind, name in source_archives.items():
        assert digest(ROOT/safe_name(name)) == protocol['source_archive_sha256'][kind]
    with tarfile.open(ROOT/safe_name(source_archives['train']), 'r:gz') as train:
        assert digest_stream(train.extractfile('matched_train_v05_001/frozen_programs.json')) == protocol['frozen_programs_sha256']
    contexts = data['contexts']
    assert len(contexts) == len({c['id'] for c in contexts}) == 120
    assert dict(Counter(c['population'] for c in contexts)) == TRANSFER_POPULATIONS
    csv_hashes = {c['source']['source_data_sha256'] for c in contexts if c['population'] == 'C3'}
    assert len(csv_hashes) == 1
    for c in contexts:
        if c['population'] == 'C3':
            assert c['source']['source_data_sha256'] == c['graph']['provenance']['source_data_sha256']
            assert c['source']['original_ids'] == c['graph']['provenance']['original_ids']
    assert clarification['original_protocol_sha256'] == TRANSFER_PROTOCOL_SHA256
    assert clarification['source_zip_sha256'] == TRANSFER_SOURCE_SHA256
    assert clarification['code_execution_backend_budget_unchanged'] is True
    assert clarification['clarification_before_analysis'] is True
    assert clarification['new_result_rewards_accessed_for_this_clarification'] is False
    assert 'before _Meter(5)' in clarification['exact_cap_scope']
    assert 'Every 128 meter writes' in clarification['exact_cap_scope']
    assert 'before FeatureRuleProgram.from_dict' in clarification['recorded_assignment_cpu_wall_scope']
    archive_path = ROOT/'experiments/runs/v05'/(stem+'.tar.gz')
    assert digest(archive_path) == TRANSFER_RUN_SHA256
    with tarfile.open(archive_path, 'r:gz') as archive:
        for name in ('protocol.json','freeze_receipt.json','data.json','frozen_programs.json','budget_scope_clarification.json'):
            assert digest_stream(archive.extractfile(stem+'/'+name)) == digest(study/name)
        execution = json.load(archive.extractfile(stem+'/execution.json'))
        complete = json.load(archive.extractfile(stem+'/complete.json'))
        validation = json.load(archive.extractfile(stem+'/validation.json'))
        assert execution['protocol_sha256'] == complete['protocol_sha256'] == TRANSFER_PROTOCOL_SHA256
        assert execution['source_zip_sha256'] == complete['source_zip_sha256'] == TRANSFER_SOURCE_SHA256
        assert execution['workers'] == 16
        timestamp = lambda value:datetime.fromisoformat(value.replace('Z','+00:00'))
        assert timestamp(freeze['created_utc']) <= timestamp(execution['started_utc']) <= timestamp(clarification['created_utc'])
        assert complete['complete'] is True and complete['contexts'] == 120 and complete['assignments'] == 1560
        assert complete['completed_assignments'] == 1007 and complete['failure_status_counts'] == {'_CPUCap':553}
        assert complete['hard_wall_safety_triggered'] is False and validation['errors'] == 0
        assert complete['frozen_programs_sha256'] == protocol['frozen_programs_sha256']
        assert digest_stream(archive.extractfile(stem+'/results.jsonl')) == complete['results_sha256']
        assert digest_stream(archive.extractfile(stem+'/validation.json')) == complete['validation_sha256']
        rows = [json.loads(line) for line in archive.extractfile(stem+'/results.jsonl') if line.strip()]
    assert len(rows) == len({r['id'] for r in rows}) == 120
    assert {r['id'] for r in rows} == {c['id'] for c in contexts}
    failures, completed = Counter(), 0
    for context in rows:
        assigned = context['rows']
        assert len(assigned) == 13 and {r['method'] for r in assigned} == methods | {'Degree'}
        for row in assigned:
            assert type(row['completed']) is bool
            completed += row['completed']
            if not row['completed']:
                failures[row['status']] += 1
                assert all(row[field] is None for field in ('value','value_exact','selected','trace','feature_work'))
    assert completed == complete['completed_assignments'] and dict(failures) == complete['failure_status_counts']
    analysis_path = ROOT/'experiments/analysis/v05'/(stem+'.json')
    analysis = json.loads(analysis_path.read_text(encoding='utf-8'))
    assert analysis['exploratory'] is True
    assert analysis['archive_sha256'] == TRANSFER_RUN_SHA256
    assert analysis['protocol_sha256'] == TRANSFER_PROTOCOL_SHA256 and analysis['source_zip_sha256'] == TRANSFER_SOURCE_SHA256
    assert analysis['complete'] == complete and set(analysis['populations']) == set(TRANSFER_POPULATIONS)
    return {'complete':complete, 'archive_sha256':TRANSFER_RUN_SHA256,
            'protocol_sha256':TRANSFER_PROTOCOL_SHA256, 'source_zip_sha256':TRANSFER_SOURCE_SHA256,
            'data_sha256':protocol['data_sha256'], 'frozen_programs_sha256':protocol['frozen_programs_sha256'],
            'budget_scope_clarification_sha256':digest(study/'budget_scope_clarification.json'),
            'publisher_analysis_sha256':digest(analysis_path), 'analysis':analysis,
            'original_source_archive_sha256':protocol['source_archive_sha256'],
            'original_C3_csv_sha256':next(iter(csv_hashes)),
            'scope':'Exploratory deployment on repeated V04 graphs; fixed U/L and all failures retained; parse precedes cooperative meter, actual timers include it'}

def new_studies():
    study = ROOT/'experiments/discovery/v05'
    protocol = json.loads((study/'protocol.json').read_text(encoding='utf-8'))
    freeze = json.loads((study/'freeze_receipt.json').read_text(encoding='utf-8'))
    completion = json.loads((study/'authoring_completion.json').read_text(encoding='utf-8'))
    assert digest(study/'protocol.json') == freeze['protocol_sha256']
    assert completion['all_authoring_completed_before_assessment'] is True
    assert completion['same_requested_model_and_settings_all_cells'] is True
    assert completion['transport_amendment_sha256'] == digest(study/'transport_amendment.json')
    for name, expected in protocol['packet_sha256'].items():
        assert digest(study/safe_name(name)) == expected
    cells = {f'block_{block}_{arm}.json' for block in range(4)
             for arm in ('witness','relations','objective')}
    assert set(completion['response_sha256']) == cells
    for name, expected in completion['response_sha256'].items():
        assert digest(study/'responses'/safe_name(name)) == expected
    records = {}
    for stem in ('matched_train_v05_001','matched_fresh_v05_001','matched_eval_v05_001'):
        receipt = read_member(stem,'complete.json')
        assert receipt['complete'] is True
        if stem.startswith('matched_train'):
            assert receipt['contexts']==66 and receipt['slots']==144 and receipt['attempts']==66*144
            frozen = read_member(stem,'frozen_programs.json')
            assert frozen['selection_split']=='train' and frozen['test_accessed'] is False
            assert frozen['all_assigned_banks']==12
            assert frozen['no_replacement_no_fallback'] is True
            assert frozen['response_sha256']==completion['response_sha256']
        elif stem.startswith('matched_fresh'):
            assert receipt['pairs']==108 and receipt['contexts']==216
            assert receipt['no_prior_input_identity_overlap'] is True
        else:
            assert receipt['contexts']==216 and receipt['assigned_runs']==216*13
        records[stem]=receipt
    for stem in ('matched_train_v05_001','matched_eval_v05_001'):
        with tarfile.open(ROOT/'experiments/runs/v05'/(stem+'.tar.gz'),'r:gz') as tar:
            receipt = records[stem]
            if stem.startswith('matched_train'):
                assert digest_stream(tar.extractfile(stem+'/frozen_programs.json')) == receipt['frozen_sha256']
            else:
                assert digest_stream(tar.extractfile(stem+'/results.jsonl')) == receipt['results_sha256']
    records['public_alias_v05_001'] = public_study()
    transfer = transfer_study()
    records[TRANSFER_STEM] = {k:v for k,v in transfer.items() if k != 'analysis'}
    return records

def transfer_audit_checks(audit, bindings):
    """Pure-data checks allow rejection probes without modifying evidence."""
    assert audit['version'] == 'matched_transfer_independent_audit_v05_001'
    assert audit['errors'] == []
    assert audit['checks'] and all(type(n) is int and n >= 0 for n in audit['checks'].values())
    assert sum(audit['checks'].values()) == 141652
    for field in ('archive_sha256','protocol_sha256','source_zip_sha256','data_sha256',
                  'frozen_programs_sha256','budget_scope_clarification_sha256','publisher_analysis_sha256',
                  'original_source_archive_sha256','original_C3_csv_sha256'):
        assert audit[field] == bindings[field], 'Changed transfer audit binding: '+field
    recorded_archive = audit['archive'].replace('\\','/')
    relative_archive = 'experiments/runs/v05/'+TRANSFER_STEM+'.tar.gz'
    assert recorded_archive == relative_archive or recorded_archive.endswith('/'+relative_archive)
    assert audit['contexts'] == TRANSFER_POPULATIONS and audit['assignments'] == 1560
    assert audit['completed_assignments'] == bindings['complete']['completed_assignments'] == 1007
    assert audit['failure_status_counts'] == bindings['complete']['failure_status_counts'] == {'_CPUCap':553}
    assert len(audit['first_argmax_checked']) == len(set(audit['first_argmax_checked'])) == 130
    assert audit['first_argmax_skipped'] == []
    counts = {'independent_complete_schedule_reward':1007, 'retained_failed_assignment':553,
              'all_13_assigned_methods_retained':120, 'independent_bounded_first_argmax':130,
              'exact_original_upper_denominator':120, 'exact_original_lower_denominator':120,
              'independent_all_four_equal_block_arm_means':15, 'original_C3_source_csv_bytes_and_contact_ids':24,
              'independent_source_parse_before_meter_argument_order':1,
              'independent_source_actual_timers_before_AST_parse':1,
              'independent_source_cooperative_CPU_deadline_every_128_writes':1}
    for name, expected in counts.items():
        assert audit['checks'][name] == expected, 'Incomplete transfer audit coverage: '+name
    assert set(audit['independent_summaries']) == set(TRANSFER_POPULATIONS)
    for pop, count in TRANSFER_POPULATIONS.items():
        summary, published = audit['independent_summaries'][pop], bindings['analysis']['populations'][pop]
        assert summary['contexts'] == published['contexts'] == count
        assert summary['contrasts_pp'] == published['contrasts']
        for arm in ('witness','relations','objective'):
            a, p = summary['arms'][arm], published['arms'][arm]
            assert len(a['block_percent_U']) == len(a['block_percent_L']) == 4
            assert a['block_percent_U'] == p['block_quality_to_formal_upper_percent']
            assert a['block_percent_L'] == p['block_quality_to_prior_best_feasible_percent']
            assert a['mean_percent_U'] == p['equal_block_mean_quality_to_formal_upper_percent']
            assert a['mean_percent_L'] == p['equal_block_mean_quality_to_prior_best_feasible_percent']
            assert a['assigned'] == p['assigned'] == 4*count and a['completed'] == p['completed']
        degree, published_degree = summary['degree'], published['degree']
        assert degree['assigned'] == published_degree['assigned'] == count
        assert degree['completed'] == published_degree['completed']
        assert degree['mean_percent_U'] == published_degree['mean_quality_to_formal_upper_percent']
        assert degree['mean_percent_L'] == published_degree['mean_quality_to_prior_best_feasible_percent']

def zero_error_audit(name):
    path = ROOT/safe_name(name)
    record = json.loads(path.read_text(encoding='utf-8'))
    assert record['errors'] == [], 'Independent audit reports errors: '+name
    checks = record['checks']
    assert checks and all(type(count) is int and count >= 0 for count in checks.values())
    assert sum(checks.values()) > 0, 'Empty independent audit: '+name
    return record

def independent_audits():
    """Bind zero-error audit metadata to the exact result and source archives."""
    source = {kind:source_snapshot(stem) for kind,stem in
              (('matched','matched_v05_001'),('public','public_alias_v05_001'))}
    names = {'matched':'experiments/analysis/v05/matched_final_audit_v05_001.json',
             'public':'experiments/analysis/v05/public_alias_audit_v05_001.json',
             'authoring':'experiments/analysis/v05/matched_authoring_costs_v05_001.json',
             'transfer':'experiments/analysis/v05/matched_transfer_audit_v05_001.json'}
    audits = {kind:zero_error_audit(name) for kind,name in names.items()}
    for kind, script in (('matched','scripts/verify_matched_llm_v05.py'),
                         ('public','scripts/verify_public_alias_v05.py')):
        assert audits[kind]['audit_script_sha256'] == digest(ROOT/safe_name(script))
    matched = audits['matched']
    for field, stem in (('training_archive','matched_train_v05_001'),
                        ('evaluation_archive','matched_eval_v05_001')):
        expected = 'experiments/runs/v05/'+stem+'.tar.gz'
        assert matched[field] == expected, 'Matched audit must cover frozen TRAIN and fresh evaluation'
        assert matched[field+'_sha256'] == digest(ROOT/safe_name(expected))
    assert matched['source_zip_sha256'] == source['matched']['sha256']
    public = audits['public']
    public_archive = 'experiments/runs/v05/public_alias_v05_001.tar.gz'
    public_input = 'experiments/runs/v04/public_data_v04_002.tar.gz'
    assert public['archive'] == public_archive
    assert public['archive_sha256'] == digest(ROOT/safe_name(public_archive))
    assert public['source_zip'] == source['public']['archive']
    assert public['source_zip_sha256'] == source['public']['sha256']
    assert public['original_public_input_archive_sha256'] == digest(ROOT/safe_name(public_input))
    assert public['original_public_input_derivation_checked'] is True
    complete = read_member('public_alias_v05_001','complete.json')
    assert public['track_summary'] == complete['track_summary']
    strict = sum(t['strict_self_loops'] for t in complete['track_summary'].values())
    assert public['verification_scope_counts']['strict_independently_upper_checked'] == strict
    costs = audits['authoring']
    study = ROOT/'experiments/discovery/v05'
    assert costs['authoring_completion_sha256'] == digest(study/'authoring_completion.json')
    assert costs['all_requested_settings_identical'] is True
    completion = json.loads((study/'authoring_completion.json').read_text(encoding='utf-8'))
    expected_cells = {f'block_{block}_{arm}' for block in range(4)
                      for arm in ('witness','relations','objective')}
    assert len(costs['sessions']) == 12
    assert {session['cell'] for session in costs['sessions']} == expected_cells
    for session in costs['sessions']:
        receipt = study/safe_name(completion['receipt_paths'][session['cell']])
        assert digest(receipt) == session['receipt_sha256']
        event = receipt.with_name(receipt.name.replace('.receipt.json','.events.jsonl'))
        assert digest(event) == session['raw_event_sha256']
    transfer = audits['transfer']
    assert digest(ROOT/safe_name(names['transfer'])) == TRANSFER_AUDIT_SHA256
    transfer_audit_checks(transfer, transfer_study())
    assert transfer['audit_script_sha256'] == digest(ROOT/'scripts/verify_matched_transfer_v05.py')
    for name, expected in transfer['independent_helper_sha256'].items():
        assert name in ('verify_matched_llm_v05.py','verify_public_alias_v05.py')
        assert digest(ROOT/'scripts'/safe_name(name)) == expected
    assert set(transfer['independent_helper_sha256']) == {'verify_matched_llm_v05.py','verify_public_alias_v05.py'}
    return {kind:{'path':names[kind], 'sha256':digest(ROOT/safe_name(names[kind])),
                  'checks':sum(record['checks'].values()), 'errors':0,
                  'warnings':len(record.get('warnings',[]))}
            for kind,record in audits.items()}

def bibliography_checks():
    """Reject actual preprint metadata; explanatory comment lines are ignored."""
    records, keys = {}, []
    for name in ('paper/references_v03.bib','paper/references_extension_v05.bib'):
        text = (ROOT/safe_name(name)).read_text(encoding='utf-8')
        fields = '\n'.join(line.split('%',1)[0] for line in text.splitlines())
        assert not re.search(r'arxiv|eprint|preprint', fields, re.I), 'Preprint bibliography entry: '+name
        entries = re.findall(r'@\w+\s*\{\s*([^,\s]+)', fields)
        assert entries, 'Empty bibliography database: '+name
        keys.extend(entries)
        records[name] = {'sha256':digest(ROOT/safe_name(name)), 'entries':len(entries)}
    assert len(keys) == len(set(keys)), 'Duplicate bibliography keys across databases'
    return records

def paper_layout():
    from pypdf import PdfReader
    pages=PdfReader(ROOT/'paper/main.pdf').pages
    assert len(pages) == 9, 'Final paper must contain exactly eight body pages and one reference page'
    texts=[p.extract_text() or '' for p in pages]
    start=[i for i,t in enumerate(texts) if re.search(r'^\s*References\s*$',t,re.M|re.I)]
    assert start==[8], 'References must begin after exactly eight body pages'
    assert re.search(r'^\s*\d+\s+Conclusion\s*$',texts[7],re.M)
    body='\n'.join(texts[:8])
    figures=re.findall(r'Figure\s+(\d+)\s*:',body)
    tables=re.findall(r'Table\s+(\d+)\s*:',body)
    assert figures==[str(n) for n in range(1,len(figures)+1)]
    assert sorted(map(int,tables))==list(range(1,len(tables)+1))
    assert len(figures)>=5 and len(tables)>=2
    return {'body_pages':8,'reference_pages':len(pages)-8,'total_pages':len(pages),
            'main_figures':len(figures),'main_tables':len(tables),
            'scope':'PDF text/page allocation; render and semantic reviews are separate documented checks'}

def verify(create=False, layout=False):
    source=(ROOT/'paper/main.tex').read_text(encoding='utf-8')
    assert '\\documentclass[sigconf,anonymous,balance=false]{aamas}' in source
    bibliography = bibliography_checks()
    if create:
        assert layout, 'Creating a release requires checking the actual PDF'
        names=paths()
        payload={'release':'0.5.0','date':'2026-10-03','paper':paper_layout(),
                 'files':{n:digest(ROOT/safe_name(n)) for n in names},
                 'archives':archive_inventory(names),'legacy':legacy_checks(),'studies':new_studies(),
                 'independent_audits':independent_audits(),
                 'bibliography':bibliography,
                 'scope':'Exact identities and assigned-run completion; solver failures and scientific limitations retained'}
        MANIFEST.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    else:
        payload=json.loads(MANIFEST.read_text(encoding='utf-8'))
        assert payload['release']=='0.5.0'
        for name,expected in payload['files'].items():
            assert digest(ROOT/safe_name(name))==expected, 'Changed V05 release file: '+name
        assert archive_inventory(payload['files'])==payload['archives']
        assert legacy_checks()==payload['legacy'] and new_studies()==payload['studies']
        assert independent_audits()==payload['independent_audits']
        assert bibliography == payload['bibliography']
        if layout: assert paper_layout()==payload['paper']
    print(f"Verified V05: {len(payload['files'])} files; {len(payload['archives'])} archive inventories; 144 original proposal slots; failures retained")

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write',action='store_true')
    p.add_argument('--paper-layout',action='store_true')
    a=p.parse_args(); verify(a.write,a.paper_layout)
