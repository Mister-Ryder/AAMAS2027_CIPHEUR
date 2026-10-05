"""One fresh complete scheduling solve with common exact input/seed contracts."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
import traceback

SCRIPT = Path(__file__).resolve()
METHODS = ('llm_witness', 'llm_feedback', 'grammar_online', 'witness_fixed',
           'witness_base9', 'degree', 'chils_ils', 'chils', 'cp_sat')
DEFAULT_CODE = SCRIPT.parents[3]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    def reject(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=_pairs,
                      parse_constant=reject)


def save_new(path, value):
    """Publish a completed JSON file atomically, refusing existing destinations."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError('Refusing to overwrite: ' + str(path))
    def default(item):
        if isinstance(item, Fraction): return str(item)
        if isinstance(item, Path): return str(item)
        raise TypeError(type(item).__name__ + ' is not JSON serializable')
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                     allow_nan=False, default=default).encode('utf-8') + b'\n'
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def degree_recipe():
    return dict(name='degree_same_kernel', features=[], rule='weight / (1 + degree)',
        coefficients=[1, 0, 0, 0],
        patch_policy=dict(anchor='uniform', destroy_count=6, patch_cap=32,
                          expand_hops=1, reconstruction='greedy'),
        evaluation_plan=dict(feature_scope='patch', max_feature_cpu_fraction=.2, lazy=True),
        adaptation_template=dict(mutation_scales=[0, 0, 0, 0], stagnation_trials=16,
                                 action='mutate'),
        rationale='Fixed degree rule in the identical feasible anytime kernel.')


def load_bank(path, validate_recipe, representation_disabled=False):
    bank = read_json(path)
    if (not isinstance(bank, dict) or set(bank) != {'schema_version', 'recipes'} or
            bank['schema_version'] != 'stk_online_llm_v2'):
        raise ValueError('Expected the strict stk_online_llm_v2 recipe bank')
    if not isinstance(bank['recipes'], list) or not 1 <= len(bank['recipes']) <= 32:
        raise ValueError('Expected one to 32 recipe templates')
    bank = deepcopy(bank)
    names = set()
    for recipe in bank['recipes']:
        validate_recipe(recipe)
        if recipe['name'] in names:
            raise ValueError('Duplicate recipe name')
        names.add(recipe['name'])
        if representation_disabled:
            added = {feature['name'] for feature in recipe['features']}
            class RemoveFeatures(ast.NodeTransformer):
                def visit_Name(self, node):
                    return ast.copy_location(ast.Constant(0), node) if node.id in added else node
            tree = RemoveFeatures().visit(ast.parse(recipe['rule'], mode='eval'))
            recipe['rule'] = ast.unparse(ast.fix_missing_locations(tree))
            recipe['features'] = []
            validate_recipe(recipe)
    return bank


def child_cpu():
    try:
        import resource
        row = resource.getrusage(resource.RUSAGE_CHILDREN)
        return row.ru_utime + row.ru_stime
    except ImportError:
        return None


def total_cpu(start, children_start):
    now = child_cpu()
    return time.process_time() - start + (now - children_start
        if now is not None and children_start is not None else 0.)


def _base_result(graph, state, start):
    return dict(seed_value_ticks=state.value, value_ticks=state.value,
        selected=sorted(state.selected), stats={}, controller={}, trials=[],
        certificates=[], conditional_local_bound_calls=0, online_llm_calls=0,
        external_oracle_calls=0, policy_reset_at_instance_start=True,
        best_so_far=[dict(cpu_seconds=time.process_time()-start,
                         value_ticks=state.value, stage='degree_seed')])


def run_native(graph, state, args, start, children_start, feasible):
    result = _base_result(graph, state, start)
    native = dict(population=1 if args.method == 'chils_ils' else 4, native_threads=1,
                  publication='10.4230/LIPIcs.SEA.2025.22', native_trace_unavailable=True,
                  objective_transport='original integer microsecond ticks',
                  vertex_transport='METIS 1-based contiguous indices', solver_invoked=False)
    result['native'] = native
    remaining = args.seconds - total_cpu(start, children_start)
    if remaining <= 0:
        native['status'] = 'budget_exhausted_before_native'
        return result
    executable = args.native_executable or os.environ.get('CHILS_EXECUTABLE')
    if not executable or not Path(executable).is_file():
        raise FileNotFoundError('Provide --native-executable or CHILS_EXECUTABLE')
    native['executable_sha256'] = digest(executable)
    nodes = sorted(graph.weights)
    if nodes != list(range(len(nodes))):
        raise ValueError('Native transport requires contiguous zero-based internal vertices')
    if (any(w <= 0 or w >= 2**63 for w in graph.weights.values()) or
            sum(graph.weights.values()) >= 2**63):
        raise ValueError('Original integer weights exceed the signed64 CHILS contract')
    with tempfile.TemporaryDirectory(prefix='stk-online-chils-') as folder:
        folder = Path(folder)
        source, initial, output = (folder/'graph.metis', folder/'initial.ids', folder/'selected.ids')
        with source.open('w', encoding='ascii') as stream:
            stream.write(f'{len(nodes)} {sum(len(graph.adjacency[v]) for v in nodes)//2} 10\n')
            for node in nodes:
                stream.write(str(graph.weights[node])+' '+' '.join(
                    str(other+1) for other in sorted(graph.adjacency[node]))+'\n')
        initial.write_text(''.join(str(v+1)+'\n' for v in sorted(state.selected)), encoding='ascii')
        native.update(input_sha256=digest(source), initial_sha256=digest(initial))
        remaining = args.seconds - total_cpu(start, children_start)
        if remaining <= 0:
            native['status'] = 'budget_exhausted_after_transport'
            return result
        command = [str(executable), '-g', str(source), '-i', str(initial), '-o', str(output),
                   '-p', str(native['population']), '-c', '1', '-t', str(remaining),
                   '-s', '0', '-r', str(args.seed)]
        native.update(solver_invoked=True, native_time_parameter_seconds=remaining,
                      native_time_parameter_scope='native nominal time target; total CPU measured separately',
                      command=command)
        before = child_cpu()
        environment = {**os.environ, 'OMP_NUM_THREADS':'1', 'OPENBLAS_NUM_THREADS':'1',
                       'MKL_NUM_THREADS':'1', 'NUMEXPR_NUM_THREADS':'1'}
        try:
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=max(5., remaining+3.), env=environment, check=False)
            native.update(exit_code=process.returncode,
                stdout=process.stdout.decode('utf-8', 'replace')[-12000:],
                stderr=process.stderr.decode('utf-8', 'replace')[-4000:],
                status='ok' if process.returncode == 0 else 'native_failed')
        except subprocess.TimeoutExpired as error:
            native.update(status='native_wall_guard_timeout', exit_code=None,
                stdout=(error.stdout or b'').decode('utf-8', 'replace')[-12000:],
                stderr=(error.stderr or b'').decode('utf-8', 'replace')[-4000:])
        after = child_cpu()
        native['child_cpu_seconds'] = after-before if after is not None and before is not None else None
        if output.is_file():
            ids = [int(value) for value in output.read_text(encoding='ascii').split()]
            if len(ids) != len(set(ids)) or any(v < 1 or v > len(nodes) for v in ids):
                raise ValueError('Malformed 1-based native solution')
            chosen = {v-1 for v in ids}
            if not feasible(graph, chosen):
                raise ValueError('Native solution is infeasible in the original graph')
            native.update(solution_sha256=digest(output), raw_value_ticks=sum(graph.weights[v] for v in chosen))
            if native['raw_value_ticks'] > state.value:
                result.update(selected=sorted(chosen), value_ticks=native['raw_value_ticks'])
                result['best_so_far'].append(dict(cpu_seconds=total_cpu(start, children_start),
                    value_ticks=result['value_ticks'], stage='native_final_observed'))
        elif native['status'] == 'ok':
            native['status'] = 'missing_native_solution'
    result['execution_status'] = ('ok' if native['status'] == 'ok' or
        native['status'].startswith('budget_exhausted') else native['status']+'_seed_guard')
    return result


def run_cp_sat(graph, state, args, start, children_start):
    result = _base_result(graph, state, start)
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    variables = {v:model.NewBoolVar('v'+str(v)) for v in sorted(graph.weights)}
    for a in graph.weights:
        for b in graph.adjacency[a]:
            if a < b: model.Add(variables[a]+variables[b] <= 1)
    if sum(graph.weights.values()) >= 2**62:
        raise ValueError('Integer objective is outside the conservative CP-SAT int64 domain')
    model.Maximize(sum(graph.weights[v]*variables[v] for v in variables))
    for v in variables: model.AddHint(variables[v], int(v in state.selected))
    remaining = args.seconds-total_cpu(start, children_start)
    result['cp_sat'] = dict(threads=1, solver_invoked=False,
        objective_transport='original integer microsecond ticks', hint='common degree feasible incumbent')
    if remaining <= 0:
        result['cp_sat']['status'] = 'budget_exhausted_after_model_encoding'
        return result
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = args.seed
    solver.parameters.max_time_in_seconds = remaining
    class Callback(cp_model.CpSolverSolutionCallback):
        def __init__(self): super().__init__(); self.count = 0
        def on_solution_callback(self):
            self.count += 1
            chosen = [v for v in variables if self.BooleanValue(variables[v])]
            value = sum(graph.weights[v] for v in chosen)
            if value > result['value_ticks']:
                result.update(selected=chosen, value_ticks=value)
                result['best_so_far'].append(dict(cpu_seconds=total_cpu(start, children_start),
                    value_ticks=value, stage='cp_sat_solution_callback'))
            if total_cpu(start, children_start) >= args.seconds: self.StopSearch()
    callback = Callback()
    status = solver.Solve(model, callback)
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        chosen = [v for v in variables if solver.BooleanValue(variables[v])]
        value = sum(graph.weights[v] for v in chosen)
        if value > result['value_ticks']:
            result.update(selected=chosen, value_ticks=value)
            result['best_so_far'].append(dict(cpu_seconds=total_cpu(start, children_start),
                value_ticks=value, stage='cp_sat_return_observed'))
    result['cp_sat'].update(solver_invoked=True, status=solver.StatusName(status),
        callback_count=callback.count, branches=solver.NumBranches(), conflicts=solver.NumConflicts(),
        best_bound_native_float=solver.BestObjectiveBound(),
        time_limit_parameter_seconds=remaining,
        time_limit_parameter_scope='CP-SAT wall target; total CPU measured separately')
    result['full_solver_calls'] = 1
    return result


def compact_projection(result):
    """Keep accountable counts/curves/parameters; omit full trials and event logs."""
    trials = result.get('trials', [])
    feature_cpu = sum(float(row.get('feature_stats', {}).get('feature_cpu', 0.))+
        float((row.get('paired_race') or {}).get('parent_feature_stats',{}).get('feature_cpu',0)) for row in trials)
    scoring_cpu = sum(float(row.get('feature_stats', {}).get('scoring_cpu', 0.))+
        float((row.get('paired_race') or {}).get('parent_feature_stats',{}).get('scoring_cpu',0)) for row in trials)
    controller = result.get('controller', {})
    compact_controller = {key:controller.get(key) for key in (
        'instance_id','mode','selected_count','update_count','mutation_count','cycle_notifications',
        'witness_mutations','stagnation_count','historical_prior_used') if key in controller}
    compact_controller['event_counts'] = dict(Counter(row.get('event') for row in controller.get('events', [])))
    credits=controller.get('statistics',{})
    compact_controller['credit_totals']={name:sum(row.get(name,0) for row in credits.values())
        for name in ('selections','observations','positive','negative','gain_ticks','cpu_seconds',
                     'fit_sum','fit_observations')}
    compact_controller['credited_genome_count']=len(credits)
    compact_controller['final_population'] = [dict(id=row['id'],
        program_hash=row.get('program_hash'), representation_hash=row.get('representation_hash'),
        generation=row.get('generation'), mutation_kind=row.get('mutation_kind'),
        recipe_name=row.get('recipe', {}).get('name'), coefficients=row.get('recipe', {}).get('coefficients'),
        patch_policy=row.get('recipe', {}).get('patch_policy'),
        feature_names=[f['name'] for f in row.get('recipe', {}).get('features', [])],
        credit=credits.get(row['id'],{}))
        for row in controller.get('population', [])]
    keys = ('version','job_id','instance_id','source','config','split','method','seed','mode',
        'budget_cpu_seconds','cpu_seconds','parent_cpu_seconds','child_cpu_seconds','wall_seconds',
        'soft_cpu_overshoot_seconds','soft_cpu_budget_exceeded','seed_value_ticks','value_ticks',
        'value_exact','feasible','execution_status','stats','best_so_far','input_graph_sha256',
        'metadata_sha256','bank_sha256','effective_bank_sha256','recipe_hashes','module_sha256',
        'script_sha256','protocol_sha256','controller_config_sha256','representation_disabled','conditional_local_bound_calls',
        'online_llm_calls','external_oracle_calls','cpu_affinity','provenance')
    output = {key:result.get(key) for key in keys if key in result}
    output.update(controller=compact_controller, feature_cpu_seconds=feature_cpu,
        scoring_cpu_seconds=scoring_cpu,
        feature_cpu_scope='reconstruction only; all diagnostic/controller CPU remains in total CPU',
        trial_summary=dict(count=len(trials), accepted=sum(bool(r.get('accepted')) for r in trials),
            negative_raw=sum(r.get('raw_gain_ticks',0)<0 for r in trials),
            status_counts=dict(Counter(r.get('status') for r in trials)),
            rank_commits=sum(int(r.get('rank_commits',0))+int((r.get('paired_race') or {}).get('parent_rank_commits',0)) for r in trials)))
    operations=Counter();reads=Counter()
    for row in trials:
        operations.update(row.get('feature_stats',{}).get('op_counts',{}))
        reads.update(row.get('feature_stats',{}).get('feature_reads',{}))
        operations.update((row.get('paired_race') or {}).get('parent_feature_stats',{}).get('op_counts',{}))
        reads.update((row.get('paired_race') or {}).get('parent_feature_stats',{}).get('feature_reads',{}))
    output['feature_operation_counts']=dict(operations)
    output['actual_added_feature_reads']=dict(reads)
    if 'native' in result: output['native']={k:v for k,v in result['native'].items() if k not in ('stdout','stderr','command')}
    if 'cp_sat' in result: output['cp_sat']=result['cp_sat']
    if 'error' in result: output['error']=result['error']
    return output


def run(args):
    code_root = Path(args.cipheur_root or DEFAULT_CODE).resolve()
    sys.path.insert(0, str(code_root))
    from cipheur.online_v2.solver import load_graph, degree_seed, solve, feasible
    from cipheur.online_v2.typed import validate_recipe
    cpu_start, wall_start, children_start = time.process_time(), time.perf_counter(), child_cpu()
    start_utc = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    result, graph, bank, controller_config = {}, None, None, None
    try:
        graph = load_graph(args.graph, args.metadata)
        if args.method == 'degree':
            bank = dict(schema_version='stk_online_llm_v2', recipes=[degree_recipe()])
        elif args.method in METHODS[:5]:
            if not args.bank: raise ValueError('--bank is required for recipe methods')
            bank = load_bank(args.bank, validate_recipe, args.method == 'witness_base9')
        if args.method in METHODS[:6]:
            if args.controller_config:controller_config=read_json(args.controller_config)
            mode = 'fixed' if args.method in ('degree','witness_fixed') else 'online'
            result = solve(graph, bank['recipes'], args.seconds, args.seed, mode=mode,
                instance_id=args.job_id or f'{args.source}:{args.config}:{args.seed}', cpu_start=cpu_start,
                controller_config=controller_config)
        else:
            state = degree_seed(graph)
            result = (run_native(graph, state, args, cpu_start, children_start, feasible)
                      if args.method in ('chils_ils','chils') else
                      run_cp_sat(graph, state, args, cpu_start, children_start))
        chosen = set(result['selected'])
        if not chosen <= graph.weights.keys() or not feasible(graph, chosen):
            raise AssertionError('Mandatory final original-graph feasibility check failed')
        result['feasible'] = True
        result['value_ticks'] = sum(graph.weights[v] for v in chosen)
    except Exception as error:
        result = dict(execution_status='method_error_seed_guard' if graph else 'input_error',
                      error=repr(error), traceback=traceback.format_exc(), online_llm_calls=0)
        if graph is not None:
            state = degree_seed(graph)
            result.update(_base_result(graph, state, cpu_start), feasible=feasible(graph,state.selected),
                          fallback_seed_recomputed=True)
    metadata = graph.source_metadata if graph is not None else {}
    module_paths = {name:code_root/'cipheur'/'online_v2'/f'{name}.py'
                    for name in ('solver','typed','controller','certificates')}
    result.update(version='stk_online_llm_v2', job_id=args.job_id,
        source=args.source or metadata.get('source_group') or metadata.get('source'),
        config=args.config or metadata.get('config_id'), split=args.split,
        method=args.method, seed=args.seed, budget_cpu_seconds=args.seconds,
        execution_status=result.get('execution_status','ok'),
        input_graph_sha256=digest(args.graph), metadata_sha256=digest(args.metadata),
        bank_sha256=digest(args.bank) if args.bank else None,
        effective_bank_sha256=canonical_hash(bank) if bank else None,
        recipe_hashes=[canonical_hash(recipe) for recipe in bank['recipes']] if bank else [],
        protocol_sha256=digest(args.protocol) if args.protocol else None,
        controller_config_sha256=digest(args.controller_config) if args.controller_config else None,
        module_sha256={name:digest(path) for name,path in module_paths.items()},
        script_sha256=digest(SCRIPT), representation_disabled=args.method=='witness_base9',
        value_exact=str(Fraction(result['value_ticks'],1000000)) if 'value_ticks' in result else None,
        selected_contact_ids=[graph.contact_ids[v] for v in result.get('selected',[])] if graph else [],
        provenance=dict(start_utc=start_utc, hostname=socket.gethostname(), platform=platform.platform(),
            python=sys.version, pid=os.getpid(), cipheur_root=str(code_root),
            input_and_common_seed_in_budget=True, historical_result_reused=False,
            seed_contract='same online_v2.solver.degree_seed for every method',
            objective='original complete-duration integer microsecond ticks',
            degree_control='fixed degree recipe in the shared anytime kernel',
            serialization_outside_optimizer_budget=True),
        cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None)
    now_children=child_cpu()
    child_elapsed=now_children-children_start if now_children is not None and children_start is not None else None
    parent_elapsed=time.process_time()-cpu_start
    result.update(parent_cpu_seconds=parent_elapsed, child_cpu_seconds=child_elapsed,
        child_cpu_measurement_available=child_elapsed is not None,
        cpu_seconds=parent_elapsed+(child_elapsed or 0.), wall_seconds=time.perf_counter()-wall_start)
    result['soft_cpu_overshoot_seconds']=max(0.,result['cpu_seconds']-args.seconds)
    result['soft_cpu_budget_exceeded']=result['cpu_seconds']>args.seconds
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cipheur-root',type=Path)
    parser.add_argument('--method',choices=METHODS,required=True)
    parser.add_argument('--bank',type=Path)
    parser.add_argument('--seconds',type=float,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--graph',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native-executable')
    parser.add_argument('--source');parser.add_argument('--config');parser.add_argument('--split')
    parser.add_argument('--job-id');parser.add_argument('--protocol',type=Path)
    parser.add_argument('--controller-config',type=Path)
    args=parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds<=0:
        parser.error('--seconds must be a positive finite CPU budget')
    if args.output.exists(): raise FileExistsError('Refusing existing output '+str(args.output))
    result=run(args)
    result['payload_sha256']=canonical_hash(result)
    save_new(args.output,result)
    print(json.dumps(dict(output=str(args.output),output_sha256=digest(args.output),
        method=args.method,execution_status=result['execution_status'],value_ticks=result.get('value_ticks'),
        feasible=result.get('feasible'),cpu_seconds=result['cpu_seconds']),ensure_ascii=False))


if __name__=='__main__': main()
