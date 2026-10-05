"""Prepare two real round-two model calls from the complete TRAIN development.

No model, optimizer, VAL or TEST run is invoked.  The diagnostic source comes
from the actual round-one cloud ZIP, never from files under live modification.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=ROOT/'llm_controller_schema.json'
METRICS=ROOT/'cloud/development/metrics.json'
SNAPSHOT=ROOT/'cloud/runtime_profile.zip'
ARMS=('witness_operators','feedback_operators')
METHODS=('llm_witness','llm_feedback','grammar_online','witness_fixed',
         'witness_base9','degree','chils_ils','chils','cp_sat')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(obj,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def api_schema(value):
    if isinstance(value,list):return [api_schema(v) for v in value]
    if not isinstance(value,dict):return value
    answer={}
    for key,item in value.items():
        if key in ('$schema','$id'):continue
        if key=='const':answer['enum']=[item]
        else:answer['anyOf' if key=='oneOf' else key]=api_schema(item)
    return answer


def controller_schema():
    old=api_schema(json.loads((ROOT/'schema.json').read_text(encoding='utf-8')))
    return dict(title='LLM proposed current-instance controller and six typed recipes',
        description='Declarations only; executable validation is separate from model provenance.',
        type='object',additionalProperties=False,
        required=['schema_version','controller_config','recipes','rationale'],
        properties=dict(schema_version=dict(type='string',enum=['stk_online_controller_v2']),
            controller_config=dict(type='object',additionalProperties=False,
                required=['credit_metric','evolve_every','parameter_mode','structural_mode','paired_race'],
                properties=dict(
                    credit_metric=dict(type='string',enum=['absolute_signed_gain_per_cpu','relative_gain_per_cpu']),
                    evolve_every=dict(type='integer',enum=[8,32,64]),
                    parameter_mode=dict(type='string',enum=['additive','bounded_relative']),
                    structural_mode=dict(type='string',enum=['legacy_mixed','atomic_template','same_operator_rewrite']),
                    paired_race=dict(type='boolean'))),
            recipes=dict(type='array',minItems=6,maxItems=6,items={'$ref':'#/$defs/recipe'}),
            rationale=dict(type='string',maxLength=20000)),
        **{'$defs':old['$defs']})


def source_snippets(records):
    requests={'controller':{'rate','select','observe','_parameter_mutation','_structural_mutation',
                            '_attach_feature','_mutant','_witness_mutant'},
              'solver':{'solve','reconstruct','choose_patch','shared_exchange'}}
    result={}
    with zipfile.ZipFile(SNAPSHOT) as archive:
        for module,wanted in requests.items():
            member=f'code/cipheur/online_v2/{module}.py'
            raw=archive.read(member);digest=hashlib.sha256(raw).hexdigest()
            observed={row['module_sha256'][module] for row in records}
            if observed!={digest}:raise ValueError('Snapshot does not match actual development '+module)
            text=raw.decode('utf-8');lines=text.splitlines();snippets=[]
            for node in ast.walk(ast.parse(text)):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
                    snippets.append(dict(name=node.name,start_line=node.lineno,
                        source='\n'.join(lines[node.lineno-1:node.end_lineno])))
            snippets.sort(key=lambda row:row['start_line'])
            result[module]=dict(zip_member=member,sha256=digest,
                matches_all_144_development_records=True,snippets=snippets)
    return result


def curve_samples(curve):
    if not curve:return []
    # Keep actual observed events, not invented/interpolated native progress.
    positions={0,len(curve)-1}
    for target in (.25,.5,1.,2.,4.,6.,8.,10.):
        positions.add(min(range(len(curve)),key=lambda i:abs(curve[i]['cpu_seconds']-target)))
    return [dict(cpu_seconds=curve[i]['cpu_seconds'],value_ticks=curve[i]['value_ticks'],
                 stage=curve[i].get('stage')) for i in sorted(positions)]


def build_feedback():
    data=json.loads(METRICS.read_text(encoding='utf-8'));records=data['records']
    allowed={'CP-AU-r000','CP-AP-r000','CP-AU-r001','CP-AP-r001'}
    if (len(records)!=144 or data.get('failed_jobs') or
            any(row['split']!='train' or row['source'] not in allowed or
                row['seed']!=2 or row['budget_cpu_seconds']!=10 for row in records)):
        raise ValueError('Expected complete TRAIN-only 144-run development, seed2,10CPU seconds')
    groups=defaultdict(list)
    for row in records:groups[row['method']].append(row)
    if set(groups)!=set(METHODS) or any(len(rows)!=16 for rows in groups.values()):
        raise ValueError('Development method/graph denominators differ')
    degree={(r['source'],r['config']):r for r in groups['degree']}
    full_rows=[]
    for row in records:
        reference=degree[(row['source'],row['config'])]
        selected={key:row.get(key) for key in ('job_id','source','config','method','seed','budget_cpu_seconds',
            'value_ticks','seed_value_ticks','cpu_seconds','parent_cpu_seconds','child_cpu_seconds',
            'wall_seconds','execution_status','feasible','soft_cpu_overshoot_seconds','stats',
            'feature_cpu_seconds','scoring_cpu_seconds','feature_cpu_scope','trial_summary',
            'conditional_local_bound_calls')}
        controller=row.get('controller',{})
        selected['controller']={key:controller.get(key) for key in ('selected_count','update_count',
            'mutation_count','cycle_notifications','witness_mutations','stagnation_count','historical_prior_used')}
        selected['final_population_parameters']=controller.get('final_population',[])
        selected.update(paired_minus_degree_ticks=row['value_ticks']-reference['value_ticks'],
            complete_curve_point_count=len(row.get('best_so_far',[])),
            actual_curve_samples=curve_samples(row.get('best_so_far',[])),
            native_curve_unavailable=row['method'] in ('chils','chils_ils'))
        if 'native' in row:selected['native']=row['native']
        if 'cp_sat' in row:selected['cp_sat']=row['cp_sat']
        full_rows.append(selected)
    table=[]
    for method in METHODS:
        rows=groups[method]
        def mean(key):return sum(r.get(key,0) or 0 for r in rows)/len(rows)
        table.append(dict(method=method,runs=16,
            mean_reward_seconds=mean('value_ticks')/1e6,
            mean_paired_minus_degree_seconds=sum(r['value_ticks']-degree[(r['source'],r['config'])]['value_ticks'] for r in rows)/16e6,
            mean_actual_cpu_seconds=mean('cpu_seconds'),
            mean_feature_cpu_seconds=mean('feature_cpu_seconds'),
            negative_raw_proposals=sum(r.get('stats',{}).get('raw_negative_proposals',0) for r in rows),
            mutation_count=sum(r.get('controller',{}).get('mutation_count',0) or 0 for r in rows),
            update_count=sum(r.get('controller',{}).get('update_count',0) or 0 for r in rows),
            accepted_operators=sum(r.get('stats',{}).get('operator_accepted',0) for r in rows),
            timedout_or_error_trials=sum(r.get('stats',{}).get('trial_timeout_or_error',0) for r in rows)))
    by_source=defaultdict(list)
    for row in full_rows:by_source[(row['method'],row['source'])].append(row)
    coverage=[]
    for (method,source),rows in sorted(by_source.items()):
        if len(rows)!=4:raise ValueError('Each method/source must cover all four configurations')
        coverage.append(dict(method=method,source=source,runs=4,configs=sorted(r['config'] for r in rows),
            mean_reward_seconds=sum(r['value_ticks'] for r in rows)/4e6,
            mean_paired_minus_degree_seconds=sum(r['paired_minus_degree_ticks'] for r in rows)/4e6,
            mean_actual_cpu_seconds=sum(r['cpu_seconds'] for r in rows)/4,
            mean_feature_cpu_seconds=sum(r['feature_cpu_seconds'] or 0 for r in rows)/4,
            negative_raw_proposals=sum(r['stats'].get('raw_negative_proposals',0) for r in rows),
            operator_attempts=sum(r['stats'].get('operator_attempts',0) for r in rows),
            controller_updates=sum(r['controller'].get('update_count',0) or 0 for r in rows),
            mutations=sum(r['controller'].get('mutation_count',0) or 0 for r in rows)))
    curves=[]
    for row in full_rows:
        if row['source']=='CP-AU-r000' and any('__'+side+'__' in row['job_id'] for side in ('E','J')):
            curves.append({key:row[key] for key in ('source','config','method','value_ticks',
                'seed_value_ticks','cpu_seconds','feature_cpu_seconds','trial_summary','stats','controller',
                'actual_curve_samples','complete_curve_point_count','native_curve_unavailable')})
    if len(curves)!=18:raise ValueError('Expected exactly nine-method E/J representative curves')
    return dict(version='controller_round2_train_feedback',split='TRAIN',
        sources=sorted(allowed),independent_source_groups=['r000','r001'],
        metrics_sha256=sha(METRICS),actual_source_zip_sha256=sha(SNAPSHOT),
        full_run_denominator=144,methods_each_16=True,method_source_coverage_summary=coverage,
        representative_curves=curves,
        method_aggregate=table,
        curves='Prespecified CP-AU-r000 E/J seed2, all nine methods, at most10 actual event checkpoints; no interpolation. All144 full curves remain in source metrics.',
        feature_cost_note='Projection feature_cpu is reconstruction only; diagnostic/controller CPU is included in total CPU.',
        actual_round1_source=source_snippets(records),
        TEST_outcomes_used=False,VAL_outcomes_used=False,
        observations_and_limits=[
            'Round-one witness and feedback remain below the degree same-kernel control and published CHILS on mean TRAIN complete reward.',
            'More mutation or actual feature reads are participation measurements, not evidence of a reward advantage.',
            'Negative proposed gains were rejected by the feasibility/gain guard but still consumed optimization CPU.',
            'Relative gain divided by destroyed incumbent weight can favor a smaller absolute improvement. Equal CPU examples:100 gained/10000 destroyed=.01;50 gained/1000 destroyed=.05. Absolute gain/cost ranks the first higher.',
            'The current typed library verifies Numeric result types, not physical dimensions. Adding seconds, dimensionless counts or squared-second edge products is allowed syntactically; semantics require consistent normalization/units.',
            'Semantic drift of actual recipe mutations is a hypothesis suggested by code, not a proven causal explanation of measured deficits.',
            'A complete archive cycle constrains one common pointwise score; it does not make all time-varying controllers impossible.',
            'Controller changes must be tested freshly within each current instance. No historically selected fixed score may replace online evolution.'])


PROMPT='''You are the actual LLM proposing a current-instance optimization controller, not merely a fixed ranking head.
Only this stdin evidence is authorized. Do not use tools, files, shell, browsing, plans, subagents or external inputs.
Return ONLY one JSON object matching the provided schema: schema_version stk_online_controller_v2,
one controller_config, exactly SIX diverse typed recipes, and a mathematical/engineering rationale.
Do not promise superior performance or turn a code-level risk into a proven explanation.

Use the complete 144 TRAIN outcomes, actual curve observations, CPU/feature costs, negative proposals,
controller update/mutation counts, and the ACTUAL round-one source snapshot to improve the optimizer.
All outcomes are TRAIN development, not held-out TEST. No future outcomes are available.
Other arms' complete performance numbers are common references; only your own arm's recipe source is supplied.

CONTROLLER OPTIONS TO BE IMPLEMENTED AND SAFELY VALIDATED:
credit_metric: absolute_signed_gain_per_cpu means the actual signed change in the global complete-schedule
objective divided by charged CPU, with negative raw proposals retained. relative_gain_per_cpu uses the
same actual gain divided additionally by destroyed incumbent weight. Explain the patch-size bias;
do not quietly replace rejected negative gains by zero or reward ranking fit instead of real scheduling.
evolve_every:8/32/64 current-instance observations. Address mutation frequency versus useful evaluation.
parameter_mode:additive reproduces clipped additive mutation; bounded_relative keeps parameter perturbations
near the original LLM parameter scales and within the global finite coefficient limits. It does not infer units.
structural_mode:legacy_mixed reproduces unrestricted Numeric-compatible feature/rule composition;
atomic_template keeps a complete paid LLM feature+rule block together, while policy and nearby parameters
can evolve; same_operator_rewrite substitutes only existing LLM feature templates with the same outer operator.
Same outer operator is a bounded search heuristic, not a mathematical guarantee of dimensional equivalence.
paired_race: a new child and its parent reconstruct the SAME actual F/P boundary and compete by real feasible
raw gains and charged costs. Both costs count. This isolates ranking/reconstruction, not different anchor policies.
All options operate online in the current independent instance; population, credits and caches reset per instance.
The source program is frozen, its feature/rule/controller state evolves. No online LLM or external answer oracle.

KEEP THE CORE: certified decision evidence -> exact representation conflict -> structural witness ->
LLM typed structural-feature/ranking composition -> joint consistency, actual schedule quality and cost.
Witness receives the structural witness; feedback-only receives the same relations/outcomes without that witness.
Features must matter in their rule and be cheap enough to produce actual committed improvements.
Explain normalized feature dimensions in the rationale, and how block-preserving mutation protects semantics.
The experiment has not established that information repair or LLM participation improves full scheduling.

DISCLOSED ENGINEERING CORRECTION (not an LLM discovery): the measured r1 solver builds the archive
using only base9 and shares it across all genomes. Consequently a base9 cycle can keep notifying even
after a genome expands its representation; this is not a certified contradiction of that expanded
current representation. R2 will isolate archives by exact representation_hash semantics and use
base9 plus the actual current added-feature coordinates, recomputing retained context vectors under
one common representation. This correction is provided by the engineers and does not establish a
new performance advantage. Propose witness-guided, drift-resistant feature/rule compositions under
the corrected interface. Do not claim that a base9 cycle proves every expanded genome is insufficient.

EXECUTABLE RECIPE CONTRACT (unchanged strict recipe schema):
features name/expression; rule uses base9 weight,duration,degree,conflict_weight,max_conflict_weight,
compatible_weight,station_gap,satellite_gap,remaining_count, aliases neighbor_weight_sum,
neighbor_max_weight,active_count, c0..c3, and your added feature names.
Rule syntax:+ - * /, numeric comparisons/boolean conditions/conditional expressions,min/max/abs.
No power, attributes, indexing, imports or functions. Guard denominators generically.
Objective is exact integer microseconds; weight/duration graph feature units are seconds.
Node:root; NodeSet:available=current residual,patch_init=initial P,neighbors(root),neighbors_of_set,
singleton,union,intersection,difference. EdgeSet:induced_edges,incident_edges, both endpoints current residual,
undirected deduplicated. Number:count,sum_weights,max_weight,clique_cover_weight,greedy_independent_weight,
edge_min_weight_sum,edge_weight_product_sum,weight,duration,add/sub/mul/div/min/max/abs,const.
const has op/value; others op/args; zero-argument operations args=[]. At most6 features,48tree nodes/depth8.
P<=64; no full12k graph rescoring. No hidden truncation or uncharged cache maintenance.
Anchors:uniform,blocked_gain,rejection_frontier,resource_boundary. destroy_count1..12,patch_cap16..64,
expand_hops1..2; reconstruction greedy/rcl/exchange. Evaluation plan:feature_scope patch,lazy true,
max_feature_cpu_fraction .05..0.30. Adaptation scales exactly4 nonnegative numbers,stagnation_trials8..128,
action mutate/diversify/switch_recipe; coefficients4 numbers within[-16,16].
No contact ID, config label or particular gap-value memorization. The kernel owns outside compatibility,
feasibility, integer positive-gain commits and deadlines. Partial/timed-out proposals cannot be mislabeled successful.
Give six coherent, diverse compositions, including cheap useful structural features and cost-conscious policies.

TRAIN-ONLY EVIDENCE JSON:
'''


def prepare(args):
    targets=[ROOT/'llm_calls'/f'{arm}.r2.b0' for arm in ARMS]
    if any(path.exists() for path in targets):raise FileExistsError('Existing round-two call directory; no overwrite or silent retry')
    schema=controller_schema()
    if SCHEMA.exists():
        if json.loads(SCHEMA.read_text(encoding='utf-8'))!=schema:raise ValueError('Existing controller schema differs')
    else:save_new(SCHEMA,schema)
    feedback=build_feedback()
    prior=json.loads((ROOT/'context/train_failure_packet.json').read_text(encoding='utf-8'))
    for arm,target in zip(ARMS,targets):
        own_bank=ROOT/'banks'/f'{arm}.json'
        body=dict(feedback)
        body['own_paid_round1_bank']=json.loads(own_bank.read_text(encoding='utf-8'))
        body['own_paid_round1_bank_sha256']=sha(own_bank)
        body['common_certified_relations']=prior['certified_relations']
        if arm=='witness_operators':body['structural_witness']=prior['structural_witness']
        target.mkdir(parents=True)
        packet=target/'train_feedback_packet.json';save_new(packet,body)
        schema_path=target/'response_schema.json';save_new(schema_path,schema)
        prompt=target/'prompt.txt';prompt.write_text(PROMPT+json.dumps(body,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        old_plan=ROOT/'llm_calls'/f'{arm}.r1.b1'/'call_plan.json'
        if not old_plan.exists():old_plan=ROOT/'llm_calls'/f'{arm}.r1.b0'/'call_plan.json'
        old=json.loads(old_plan.read_text(encoding='utf-8'))
        # Clone the already-used actual isolated CLI configuration, changing paths only.
        argv=list(old['argv']);cwd=Path(tempfile.mkdtemp(prefix='cipheur-v2-controller-isolated-'))
        for flag,value in (('--cd',cwd),('--output-schema',schema_path.resolve()),('-o',(target/'response.json').resolve())):
            argv[argv.index(flag)+1]=str(value)
        if args.cli:argv[0]=args.cli
        plan=dict(call_id=target.name,argv=argv,working_directory=str(cwd),stdin_path=str(prompt.resolve()),
            stdout_path=str((target/'events.jsonl').resolve()),stderr_path=str((target/'stderr.txt').resolve()),
            response_path=str((target/'response.json').resolve()),receipt_path=str((target/'execution_receipt.json').resolve()),
            model_requested='gpt-6.1-sol',model_observed='unknown',reasoning_effort_requested='ultra',
            prompt_sha256=sha(prompt),schema_sha256=sha(schema_path),TRAIN_packet_sha256=sha(packet),
            TRAIN_metrics_sha256=sha(METRICS),actual_round1_source_zip_sha256=sha(SNAPSHOT),
            prior_cli_plan_sha256=sha(old_plan),VAL_outcomes_used=False,TEST_outcomes_used=False,
            recipes_requested=6,controller_config_requested=True,
            response_schema_version='stk_online_controller_v2',
            ingest_note='New top-level controller_config and recipes require round2 ingest; old round1 bank ingester must not silently drop fields.')
        save_new(target/'call_plan.json',plan)
        print(json.dumps(dict(call_id=target.name,prompt_bytes=prompt.stat().st_size,
            plan=str(target/'call_plan.json'),schema_sha256=sha(schema_path)),ensure_ascii=False))


def compact_existing(args):
    """Create a new compact plan without modifying either unexecuted prior plan."""
    feedback=build_feedback()
    prior=json.loads((ROOT/'context/train_failure_packet.json').read_text(encoding='utf-8'))
    for arm in ARMS:
        target=ROOT/'llm_calls'/f'{arm}.r2.b0'
        if (target/'response.json').exists() or (target/'events.jsonl').exists():
            raise ValueError('An actual call has started; do not alter its inputs')
        bank=ROOT/'banks'/f'{arm}.json'
        body=dict(feedback,own_paid_round1_bank=json.loads(bank.read_text(encoding='utf-8')),
                  own_paid_round1_bank_sha256=sha(bank),common_certified_relations=prior['certified_relations'])
        if arm=='witness_operators':body['structural_witness']=prior['structural_witness']
        packet=target/'train_feedback_packet.compact.json';save_new(packet,body)
        prompt=target/'prompt.compact.txt'
        with prompt.open('x',encoding='utf-8') as stream:
            stream.write(PROMPT+json.dumps(body,ensure_ascii=False,separators=(',',':')))
        if prompt.stat().st_size>180000:raise ValueError('Compact prompt still exceeds180KB')
        plan=json.loads((target/'call_plan.final.json').read_text(encoding='utf-8'))
        plan.update(stdin_path=str(prompt.resolve()),prompt_sha256=sha(prompt),
            TRAIN_packet_sha256=sha(packet),unexecuted_final_plan_sha256=sha(target/'call_plan.final.json'),
            prompt_compression='All144 contribute to9method and36method/source summaries; only prespecified18E/J curves, no population coefficients.')
        save_new(target/'call_plan.compact.json',plan)
        save_new(target/'NOT_EXECUTED_INITIAL_PLANS.json',dict(status='NOT_EXECUTED',
            plans=[dict(path=name,sha256=sha(target/name)) for name in ('call_plan.json','call_plan.final.json')],
            actual_plan_to_run='call_plan.compact.json',prior_inputs_preserved=True))
        print(json.dumps(dict(call_id=target.name,actual_plan=str(target/'call_plan.compact.json'),
            prompt_bytes=prompt.stat().st_size,prompt_sha256=sha(prompt)),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cli')
    parser.add_argument('--compact-existing',action='store_true')
    args=parser.parse_args()
    compact_existing(args) if args.compact_existing else prepare(args)
