"""Register v2 development/formal jobs from metadata and hashes only.

No graph arrays, selected schedules or any quality outputs are read. Pending
grid mode is usable before banks/benchmark exist and cannot produce the ready
jobs.jsonl queue. Ready registrations are immutable and bind source/bank hashes.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath
import re
import sys

EXPERIMENT = Path(__file__).resolve().parents[1]
PROJECT = EXPERIMENT.parents[1]
DATA = PROJECT.parent / 'data' / '两篇论文数据定制化构建' / 'CIPHEUR_STK_20261005'
CLOUD = '/root/autodl-tmp/cipheur_stk_online_llm_20261006_001'
CLOUD_PYTHON = '/root/autodl-tmp/cipheur_stk_full_llm_20261005_001/venv/bin/python'
TRAIN_CLOUD = '/root/autodl-tmp/cipheur_stk_p0_20261005_001/data/extensions/heterogeneous_ground_v1/graphs'
TEST_CLOUD = '/root/autodl-tmp/cipheur_stk_full_llm_20261005_001/data/graphs'
NATIVE = '/root/autodl-tmp/aamas2027_v03/baselines/CHILS/CHILS'
METHODS = ['llm_witness', 'llm_feedback', 'grammar_online', 'witness_fixed', 'witness_base9',
           'degree', 'chils_ils', 'chils', 'cp_sat']
BANKS = {'llm_witness': 'witness_operators.json', 'llm_feedback': 'feedback_operators.json',
         'grammar_online': 'grammar_operators.json', 'witness_fixed': 'witness_operators.json',
         'witness_base9': 'witness_operators.json'}
CONTROLLER_CONFIGS = {'llm_witness': 'witness_operators.json', 'llm_feedback': 'feedback_operators.json',
                      'grammar_online': 'witness_operators.json', 'witness_fixed': 'witness_operators.json',
                      'witness_base9': 'witness_operators.json'}
CONTROLLER_FIELDS = {'credit_metric', 'evolve_every', 'parameter_mode', 'structural_mode', 'paired_race'}
DEVELOPMENT_STAGES = ('development', 'development_round2')
CONFIGS = [('A', 'g0340', 'gW0340_gE0340_s0150', 340, 340),
           ('M', 'g0680', 'gW0680_gE0680_s0150', 680, 680),
           ('J', 'g1200', 'gW1200_gE1200_s0150', 1200, 1200),
           ('stress', 'g1800', 'gW1800_gE1800_s0150', 1800, 1800),
           ('W', 'gW1200_gE0340_s0150', 'gW1200_gE0340_s0150', 1200, 340),
           ('E', 'gW0340_gE1200_s0150', 'gW0340_gE1200_s0150', 340, 1200),
           ('MW', 'gW0680_gE1200_s0150', 'gW0680_gE1200_s0150', 680, 1200),
           ('ME', 'gW1200_gE0680_s0150', 'gW1200_gE0680_s0150', 1200, 680)]

POLICY = {
    'version': 'current_instance_online_v2_comparison_v1',
    'mode': 'cold static current-configuration reoptimization',
    'adaptive_runtime': 'Parameters, recipe population, structural features and bounded current-instance decision archive may adapt during this solve; historical fit/quality tables are not loaded.',
    'freeze_boundary': 'Freeze optimizer source, metadata inputs, initialization banks, budgets/methods/seeds before formal TEST. Do not freeze per-instance evolved runtime state.',
    'runtime_reset': ['incumbent', 'genomes', 'coefficients', 'feature/cache state', 'archive', 'operator credit', 'random generator', 'timer'],
    'online_objective_is_solver_work': True,
    'no_test_quality_peek_or_selection': True,
    'no_previous_v1_quality_read_by_registration': True,
    'offline_LLM_role': 'Initialize bounded typed recipe banks/operators from TRAIN development/failure context; no online LLM call and no historical winning ranking programme is deployed as the algorithm.',
    'current_instance_evidence': 'Any current conditional calculation, witness/alias check and feature mutation is solver work inside the same total CPU budget, not a free pre-solve oracle.',
    'mid_solve_events_implemented': False, 'warm_state_transfer_implemented': False, 'arrivals_implemented': False,
    'main_metric': 'Final complete feasible schedule value_ticks/1000000 seconds with exact integer objective; same-source/config/budget/seed paired method deltas.',
    'budget': 'Total parent plus native-child CPU includes input load, initialization, patches, scoring, controller, evidence, all failed candidates and final validation. Declared and actual CPU/overshoot/wall are retained.',
    'anytime': 'Only true incumbent commit events. Native trace unavailable is observation-limited, not no progress; no interpolation.',
    'statistical_unit': 'r008/r009 physical groups. AU/AP,8configs and seed2 are repeated observations; expose both groups, equal weighting, no pseudo-independent CI/significance.',
    'failure_policy': 'Preserve missing/nonfeasible/failed jobs, raw negative gain, guard-rejected trials, programme errors, feature costs and zero updates; missing quality is NA not zero.',
    'mechanism_metrics': ['recipe/parameter/representation updates', 'actual declared-feature reads in scoring separated from diagnostic reads', 'head commits', 'raw and accepted gain', 'current evidence queries and status', 'feature CPU/ops', 'controller CPU', 'final schedule quality'],
    'dataset_scope': 'Same complete contacts and exact duration weights under8resource configurations; satellite gap150 fixed. Four independent TEST libraries form only2physical groups.',
    'limitations': ['custom STK geometry and EOP forecasts', 'static known72h contact opportunities', 'no task arrivals/queue/storage/energy/deadline workload', 'ground W/E axis only; no claim of effective independent satellite-gap axis', 'no optimum claim'],
}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def require(value, message):
    if not value: raise ValueError(message)

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sources(stage):
    replicates = ('r000', 'r001') if stage in DEVELOPMENT_STAGES else ('r008', 'r009')
    return ['CP-' + geometry + '-' + replicate for replicate in replicates for geometry in ('AU', 'AP')]

def graph_inputs(args):
    split = 'train' if args.stage in DEVELOPMENT_STAGES else 'test'
    chosen = [c for c in CONFIGS if c[0] in ('A', 'W', 'E', 'J')] if split == 'train' else CONFIGS
    local_root = args.local_data_root / ('extensions/heterogeneous_ground_v1/graphs' if split == 'train' else 'perf_dataset_v1/graphs')
    cloud_root = PurePosixPath(args.train_cloud_root if split == 'train' else args.test_cloud_root)
    result = []; identities = defaultdict(set)
    for source in sources(args.stage):
        for alias, testtag, traintag, west, east in chosen:
            tag = traintag if split == 'train' else testtag
            path = local_root / source / (tag + '.npz'); meta_path = path.with_suffix('.json')
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            require(meta.get('source_id') == source and meta.get('config_id') == tag and meta.get('split') == split, 'Input metadata identity/split differs')
            graph_hash = sha(path)
            require(meta.get('npz_sha256') == graph_hash, 'Metadata/NPZ hash differs')
            require(meta.get('source_group') == 'CP-SOURCE-' + source[-4:], 'Source group differs')
            require(meta.get('satellite_gap_seconds') == 150 and meta.get('station_gap_mode') == 'per_antenna', 'Resource contract differs')
            groups = meta['antenna_group']; mapping = meta['station_gap_by_antenna_seconds']
            require(set(groups) == set(mapping) and set(groups.values()) == {'west', 'east'} and all(mapping[a] == (west if groups[a] == 'west' else east) for a in mapping), 'W/E per-antenna policy differs')
            identity = (meta['node_mapping_sha256'], meta['weight_ticks_sha256'], meta['raw_contacts_sha256'])
            identities[source].add(identity)
            result.append({'source': source, 'source_group': meta['source_group'], 'config_alias': alias, 'config': tag,
                           'canonical_config': testtag, 'west_gap_seconds': west, 'east_gap_seconds': east, 'split': split,
                           'local_npz_path': str(path.resolve()), 'local_metadata_path': str(meta_path.resolve()),
                           'cloud_npz_path': str(cloud_root / source / path.name), 'cloud_metadata_path': str(cloud_root / source / meta_path.name),
                           'npz_sha256': graph_hash, 'metadata_sha256': sha(meta_path), 'node_mapping_sha256': identity[0],
                           'weight_ticks_sha256': identity[1], 'nodes': meta['stats']['n'], 'edges': meta['stats']['m']})
    require(all(len(v) == 1 for v in identities.values()), 'Nodes/weights differ across same-source configurations')
    require(len(result) == (16 if split == 'train' else 32), 'Fixed graph denominator differs')
    return result

def bank_inputs(args):
    answer, missing = {}, []
    sys.path.insert(0, str(PROJECT))
    from cipheur.online_v2.typed import validate_recipe
    for stem in sorted(set(BANKS.values())):
        path = args.local_bank_root / stem
        if not path.is_file(): missing.append(str(path)); continue
        obj = json.loads(path.read_text(encoding='utf-8'))
        require(isinstance(obj, dict) and set(obj) == {'schema_version', 'recipes'} and obj['schema_version'] == 'stk_online_llm_v2' and 1 <= len(obj['recipes']) <= 32, 'Bank schema differs')
        for recipe in obj['recipes']: validate_recipe(recipe)
        answer[stem] = {'local_path': str(path.resolve()), 'cloud_path': str(PurePosixPath(args.cloud_bank_root) / stem),
                        'sha256': sha(path), 'recipe_count': len(obj['recipes']), 'validation': 'strict typed declarations only; no scoring/quality selection'}
    return answer, missing

def controller_inputs(args):
    answer, missing = {}, []
    if args.controller_config_root is None: return answer, missing
    sys.path.insert(0, str(PROJECT))
    from cipheur.online_v2.controller import validate_controller_config
    for stem in sorted(set(CONTROLLER_CONFIGS.values())):
        path = args.controller_config_root / stem
        if not path.is_file(): missing.append(str(path)); continue
        obj = json.loads(path.read_text(encoding='utf-8'))
        require(isinstance(obj, dict) and set(obj) == CONTROLLER_FIELDS, 'Controller config must be a bare complete five-field declaration')
        validated = validate_controller_config(obj)
        require(validated == obj, 'Controller validation must not silently normalize the declaration')
        answer[stem] = {'local_path': str(path.resolve()), 'cloud_path': str(PurePosixPath(args.cloud_controller_config_root) / stem),
                        'sha256': sha(path), 'declaration': obj,
                        'validation': 'Strict current controller validator; original bytes and spelling retained; no solver/quality calls'}
    return answer, missing

def code_inputs(args):
    files = []
    module_root = PROJECT / 'cipheur' / 'online_v2'
    files.append((PROJECT / 'cipheur' / '__init__.py', 'code/cipheur/__init__.py'))
    for path in sorted(module_root.rglob('*.py')): files.append((path, 'code/cipheur/online_v2/' + path.relative_to(module_root).as_posix()))
    for path in sorted((EXPERIMENT / 'scripts').rglob('*.py')): files.append((path, 'scripts/' + path.relative_to(EXPERIMENT / 'scripts').as_posix()))
    files.append((EXPERIMENT / 'schema.json', 'schema.json'))
    if args.controller_config_root is not None:
        files.append((EXPERIMENT / 'llm_controller_schema.json', 'llm_controller_schema.json'))
    # Existing exact native transport source is an explicit external dependency.
    transport = PROJECT / 'experiments/stk_full_llm_v1/scripts/published_weighted_baselines.py'
    files.append((transport, 'external_dependency/published_weighted_baselines.py'))
    hashes = [{'local_path': str(p.resolve()), 'relative_runtime_path': key, 'sha256': sha(p)} for p, key in files if p.is_file()]
    benchmark = EXPERIMENT / 'scripts/benchmark.py'
    missing = [] if benchmark.is_file() else [str(benchmark)]
    return hashes, missing

def make_jobs(args, graphs, banks, code, ready, controllers=None):
    controllers = controllers or {}
    cloud = PurePosixPath(args.cloud_root); seconds = [10] if args.stage in DEVELOPMENT_STAGES else [10, 30]
    jobs = []
    code_hashes = {r['relative_runtime_path']: r['sha256'] for r in code}
    for graph, budget, method in itertools.product(graphs, seconds, METHODS):
        identity_parts = [args.stage] + ([args.revision] if args.revision != 'r1' else [])
        identifier = '__'.join(identity_parts + [graph['source'], graph['config_alias'], method, 't' + str(budget), 's2'])
        output = str(cloud / args.stage / 'results' / (identifier + '.json'))
        bank = banks.get(BANKS.get(method, ''))
        config_stem = CONTROLLER_CONFIGS.get(method) if args.controller_config_root is not None else None
        controller = controllers.get(config_stem)
        controller_path = str(PurePosixPath(args.cloud_controller_config_root) / config_stem) if config_stem else None
        argv = [args.cloud_python, str(cloud / 'scripts/benchmark.py'), '--cipheur-root', str(cloud / 'code'),
                '--graph', graph['cloud_npz_path'], '--metadata', graph['cloud_metadata_path'], '--source', graph['source'],
                '--config', graph['config'], '--split', graph['split'], '--method', method, '--seconds', str(budget),
                '--seed', '2', '--job-id', identifier, '--output', output]
        if method in BANKS: argv += ['--bank', str(PurePosixPath(args.cloud_bank_root) / BANKS[method])]
        if controller_path: argv += ['--controller-config', controller_path]
        if method in ('chils', 'chils_ils'): argv += ['--native-executable', args.native_executable]
        job = {'job_id': identifier, 'registered_order': len(jobs), 'source': graph['source'], 'source_group': graph['source_group'],
               'config': graph['config'], 'config_alias': graph['config_alias'], 'canonical_config': graph['canonical_config'],
               'split': graph['split'], 'seconds': budget, 'seed': 2, 'method': method, 'output': output,
               'graph': graph['cloud_npz_path'], 'metadata': graph['cloud_metadata_path'], 'input_graph_sha256': graph['npz_sha256'],
               'metadata_sha256': graph['metadata_sha256'], 'bank': str(PurePosixPath(args.cloud_bank_root) / BANKS[method]) if method in BANKS else None,
               'bank_sha256': bank['sha256'] if bank else None, 'code_hashes': code_hashes, 'argv': argv, 'ready_to_execute': ready}
        if args.revision != 'r1' or args.stage == 'development_round2' or args.controller_config_root is not None:
            job.update(revision=args.revision, controller_config=controller_path,
                       controller_config_sha256=controller['sha256'] if controller else None,
                       controller_source=('common LLM-generated controller with non-LLM grammar bank' if method == 'grammar_online' and controller_path
                                          else 'LLM-generated initialization controller' if controller_path else 'unchanged method default; no controller config'))
        jobs.append(job)
    require(len(jobs) == (144 if args.stage in DEVELOPMENT_STAGES else 576), 'Fixed job denominator differs')
    return jobs

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', choices=('development', 'development_round2', 'comparison'), required=True)
    ap.add_argument('--revision', default='r1', help='Registration revision; r1 preserves historical IDs/default paths')
    ap.add_argument('--output-root', type=Path)
    ap.add_argument('--prepare-grid', action='store_true', help='Register non-executable pending grid even before banks/benchmark exist')
    ap.add_argument('--local-data-root', type=Path, default=DATA)
    ap.add_argument('--local-bank-root', type=Path, help='Legacy local bank override; cloud folder stays banks in r1')
    ap.add_argument('--bank-root', type=Path, help='Local bank directory; basename is also its cloud runtime folder')
    ap.add_argument('--controller-config-root', type=Path, help='Local bare-controller directory; basename is also its cloud runtime folder')
    ap.add_argument('--cloud-root', default=CLOUD); ap.add_argument('--cloud-python', default=CLOUD_PYTHON)
    ap.add_argument('--train-cloud-root', default=TRAIN_CLOUD); ap.add_argument('--test-cloud-root', default=TEST_CLOUD)
    ap.add_argument('--native-executable', default=NATIVE)
    args = ap.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', args.revision), 'Revision must be a safe nonempty identifier')
    require(not (args.bank_root is not None and args.local_bank_root is not None), 'Use either --bank-root or legacy --local-bank-root')
    round2 = args.stage == 'development_round2'
    args.local_bank_root = args.bank_root or args.local_bank_root or EXPERIMENT / ('banks_round2' if round2 else 'banks')
    bank_folder = args.local_bank_root.name if args.bank_root is not None or round2 else 'banks'
    require(bank_folder not in ('', '.', '..'), 'Bank root must have a directory basename')
    args.cloud_bank_root = str(PurePosixPath(args.cloud_root) / bank_folder)
    if args.controller_config_root is None and round2: args.controller_config_root = EXPERIMENT / 'configs_round2'
    if args.controller_config_root is not None:
        require(args.controller_config_root.name not in ('', '.', '..'), 'Controller root must have a directory basename')
        args.cloud_controller_config_root = str(PurePosixPath(args.cloud_root) / args.controller_config_root.name)
    else: args.cloud_controller_config_root = None
    output = args.output_root or EXPERIMENT / 'registrations' / args.stage
    if args.output_root is None and args.revision != 'r1': output = output / args.revision
    registration_path = output / ('registration.pending.json' if args.prepare_grid else 'registration.json')
    require(not registration_path.exists(), 'Do not overwrite existing registration; use a new --output-root revision')
    graphs = graph_inputs(args); banks, bank_missing = bank_inputs(args); controllers, controller_missing = controller_inputs(args); code, code_missing = code_inputs(args)
    missing = bank_missing + controller_missing + code_missing
    if missing and not args.prepare_grid: raise ValueError('Ready registration is missing bank/controller/benchmark files: ' + ', '.join(missing))
    ready = not args.prepare_grid and not missing
    jobs = make_jobs(args, graphs, banks, code, ready, controllers)
    output.mkdir(parents=True, exist_ok=True)
    jobs_path = output / ('jobs.pending.jsonl' if args.prepare_grid else 'jobs.jsonl')
    require(not jobs_path.exists(), 'Do not overwrite job queue')
    jobs_path.write_text(''.join(json.dumps(j, ensure_ascii=False) + '\n' for j in jobs), encoding='utf-8')
    registration = {'version': POLICY['version'], 'registered_utc': datetime.now(timezone.utc).isoformat(), 'stage': args.stage,
                    'status': 'ready' if ready else 'pending_input_artifacts; non-executable grid', 'frozen_optimizer_source': ready,
                    'runtime_state_is_not_frozen': True, 'policy': POLICY, 'methods': METHODS, 'source_ids': sources(args.stage),
                    'budgets_cpu_seconds': [10] if args.stage in DEVELOPMENT_STAGES else [10, 30], 'seeds': [2],
                    'graph_count': len(graphs), 'job_count': len(jobs), 'graphs': graphs, 'banks': banks, 'code': code,
                    'missing_ready_artifacts': missing, 'jobs_filename': jobs_path.name, 'jobs_sha256': sha(jobs_path),
                    'old_or_new_TEST_quality_files_read': 0, 'optimizer_calls': 0, 'scoring_calls': 0, 'model_calls': 0,
                    'input_contract_check': 'Graph metadata,byte hashes,same-source node/weight hashes only; no NPZ arrays loaded.',
                    'protocol_document_sha256': sha(EXPERIMENT / 'PROTOCOL.md'),
                    'cloud_paths': {'root': args.cloud_root, 'python': args.cloud_python, 'train_graphs': args.train_cloud_root,
                                    'test_graphs': args.test_cloud_root, 'native_CHILS': args.native_executable},
                    'execution': 'Queue runs8single-CPU workers with allowed affinity; all methods same declared total CPU; no queue launched by registration.'}
    if args.revision != 'r1' or round2 or args.controller_config_root is not None:
        registration.update(revision=args.revision, controller_configs=controllers,
                            method_controller_config_stems={m: CONTROLLER_CONFIGS.get(m) if args.controller_config_root is not None else None for m in METHODS},
                            grammar_controller_control='common LLM-generated controller with non-LLM grammar bank' if args.controller_config_root is not None else 'r1 unchanged default controller',
                            controller_config_policy='Witness/fixed/base9/grammar share the same Witness controller; Feedback uses its own; Degree/CHILS/CP-SAT receive no controller config.')
        registration['cloud_paths'].update(banks=args.cloud_bank_root, controller_configs=args.cloud_controller_config_root)
    dump(registration_path, registration)
    print(json.dumps({'stage': args.stage, 'graphs': len(graphs), 'jobs': len(jobs), 'ready': ready,
                      'registration': str(registration_path), 'registration_sha256': sha(registration_path), 'missing_ready_artifacts': missing}, ensure_ascii=False))

if __name__ == '__main__': main()
