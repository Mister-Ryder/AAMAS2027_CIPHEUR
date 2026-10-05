"""Build a TRAIN-only failure packet and plan actual isolated model calls.

The response is data. The executable kernel validates all programs and owns
feasibility, time limits, acceptance, and current-instance state.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OLD = PROJECT / 'experiments' / 'stk_full_llm_v1'
sys.path.insert(0, str(OLD / 'scripts'))
from llm_cli_proposer import representative_view

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def build_packet():
    metric_path = OLD / 'cloud' / 'final_train' / 'metrics.json'
    context_path = OLD / 'context' / 'train_context.json'
    metrics = json.loads(metric_path.read_text(encoding='utf-8'))
    rows = metrics['records']
    assert len(rows) == 1440 and all(r['split'] == 'train' for r in rows)
    assert {r['source'] for r in rows} == {'CP-AU-r000','CP-AP-r000','CP-AU-r001','CP-AP-r001'}
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get('program_id') or r['method'], r['declared_cpu_seconds'])].append(r)
    table = []
    for (method, budget), records in sorted(groups.items()):
        mean = lambda f: sum(f(r) for r in records) / len(records)
        table.append(dict(method=method, budget_cpu_seconds=budget, runs=len(records),
            mean_reward_seconds=mean(lambda r: r['value_ticks']/1e6),
            mean_actual_cpu_seconds=mean(lambda r: r['cpu_seconds']),
            mean_feature_cpu_seconds=(mean(lambda r:r['meter']['feature_seconds']) if all('feature_seconds' in r['meter'] for r in records) else None),
            mean_head_commits=mean(lambda r:r['stats']['head_commits']),
            mean_repair_attempts=mean(lambda r:r['repair_summary']['count']),
            accepted_repairs=sum(r['repair_summary']['accepted_count'] for r in records),
            negative_raw_repairs=sum(r['repair_summary']['negative_raw_gain_count'] for r in records),
            negative_raw_constructions=sum((r['construction_summary'].get('raw_delta_from_seed_ticks') or 0)<0 for r in records)))
    # Same physical TRAIN graph/seed, representative traces, no cherry-picked victory.
    trace_records = []
    allowed = {'degree','chils_ils','chils','witness_joint.r1.b1.s0','witness_joint.r2.b0.s2','joint|block_0_witness:2'}
    for r in rows:
        method = r.get('program_id') or r['method']
        if method not in allowed or r['source']!='CP-AU-r000' or r['seed']!=2 or r['declared_cpu_seconds']!=10:
            continue
        curve = r.get('best_so_far',[])
        indices = sorted({round(i*(len(curve)-1)/min(15,len(curve)-1)) for i in range(min(16,len(curve)))}) if len(curve)>1 else [0] if curve else []
        trace_records.append(dict(method=method, config=r['config'],
            curve_samples=[curve[i] for i in indices], curve_point_count=len(curve),
            native_trace_unavailable=method.startswith('chils'),
            construction=r.get('construction_summary'), repair=r.get('repair_summary'),
            feature_cpu_seconds=r['meter'].get('feature_seconds')))
    context = json.loads(context_path.read_text(encoding='utf-8'))
    common, sampling = representative_view(context)
    # Old deployment instructions are removed; they are obsolete experimental context.
    for key in ('deployment','synthesis_objective','grammar_policy','library'):
        common.pop(key,None)
    packet = dict(version='current_instance_operator_synthesis_v2', split='TRAIN',
        source_groups=['r000','r001'], source_ids=sorted({r['source'] for r in rows}),
        forbidden_sources='No VAL or TEST outcomes have been read for this redesign.',
        source_receipts={'metrics_sha256':digest(metric_path),'context_sha256':digest(context_path)},
        complete_schedule_performance=table, runtime_failure_traces=trace_records,
        certified_relations=common, relation_sampling=sampling,
        structural_witness=context['witness_only'],
        interpretations=[
            'All eight old heads were worse than CHILS p1 and p4 even on TRAIN; no test shift explanation can remove this deficit.',
            'Feature capacity and local strict fit did not translate to complete schedule gain. Higher fit is not the online fitness.',
            'The old reference spent about 9.20 of 10.01 CPU seconds on features and made only about23 head commits; full-graph repeated feature evaluation is an actual bottleneck.',
            'Guarded negative proposals consumed time although the best feasible incumbent remained safe.',
            'The selected seven new heads had no added features; neither Witness nor LLM-specific representation benefit was established.',
            'A base9 quotient cycle proves no common pointwise score satisfies the archive. It does not prove all stateful online algorithms need new features.',
            'No earlier performance result demonstrates that the new operator design wins. It must be tested.'])
    save(ROOT/'context'/'train_failure_packet.json', packet)
    return packet

def prepare(args):
    packet = build_packet()
    schema_template = ROOT/'schema.json'
    assert schema_template.is_file(), 'Controller agent must finish the strict schema first'
    for arm in ('witness_operators','feedback_operators'):
        call = ROOT/'llm_calls'/f'{arm}.r1.b{args.batch}'
        if call.exists():
            raise ValueError('Do not overwrite an actual call or silently retry')
        call.mkdir(parents=True)
        schema=call/'response_schema.json'
        def api_schema(value):
            if isinstance(value,list):return [api_schema(v) for v in value]
            if not isinstance(value,dict):return value
            return {('anyOf' if k=='oneOf' else 'enum' if k=='const' else k):
                [v] if k=='const' else api_schema(v) for k,v in value.items() if k not in ('$schema','$id')}
        output_schema=api_schema(json.loads(schema_template.read_text(encoding='utf-8')))
        output_schema['properties']['recipes']['minItems']=6
        output_schema['properties']['recipes']['maxItems']=6
        save(schema,output_schema)
        body = dict(packet)
        if arm == 'feedback_operators':
            body.pop('structural_witness')
        prompt = '''You are the actual LLM program-synthesis component of an optimization study.
Only this stdin packet is allowed. Do not use tools, files, shell, browsing, plans, subagents or any external input.
Return a single JSON object matching the provided schema. Generate exactly SIX diverse operator recipes.
You must expand LLM participation beyond scoring into the observed bottlenecks: patch anchoring,
destroy-reconstruct choices, local lazy feature computation, and stagnation/evolution actions.
This is not a historically trained frozen scoring head. Your parametric recipes are instantiated,
combined and mutated during the current complete scheduling solve, judged by actual feasible reward
improvement and CPU cost. Every independent instance resets population, credit and caches.
The title's core stays certified decision evidence -> representation conflict -> structural witness ->
typed structural-feature/ranking composition -> joint consistency, schedule quality, and cost.
The witness condition receives the exact structural witness; the feedback-only control does not.
Do not promise performance or treat your rationale as a mathematical certificate.

DECLARATIVE EXECUTION CONTRACT:
All numeric weights/durations in feature scoring are seconds, exact objective uses integer microseconds.
Base rule variables: weight, duration, degree, neighbor_weight_sum, neighbor_max_weight,
station_gap (root station's current gap), satellite_gap, active_count. Parameters c0,c1,c2,c3.
Legacy aliases conflict_weight=neighbor_weight_sum, max_conflict_weight=neighbor_max_weight,
remaining_count=active_count, compatible_weight=sum(active minus root closed neighborhood).
Rule permits only numeric constants, arithmetic + - * /, comparisons, boolean conditions,
conditional expression, and min/max/abs. No power, attributes, import, function definitions or indexing.
Every new feature actually participates in the rule; choose at most3 per recipe, <=48 tree nodes/depth8.
Typed Node is root; NodeSet: available (CURRENT residual), patch_init (original repair domain),
neighbors(Node), neighbors_of_set(NodeSet), singleton(Node), union/intersection/difference(NodeSet,NodeSet).
Neighbors are restricted to the CURRENT residual. EdgeSet: induced_edges(NodeSet), incident_edges(NodeSet).
incident_edges has both endpoints in current residual and at least one endpoint in the named set,
undirected edges deduplicated. Numeric graph ops: count(NodeSet or EdgeSet), sum_weights(NodeSet),
max_weight(NodeSet), clique_cover_weight(NodeSet), greedy_independent_weight(NodeSet),
edge_min_weight_sum(EdgeSet), edge_weight_product_sum(EdgeSet), weight(Node),duration(Node),
add/sub/mul/div/min/max(Number,Number),abs(Number),const(value).
root/available/patch_init have args=[]; const has op/value; all others op/args.
All queries exact on explicitly bounded P; a feature cannot silently sample/truncate.
Graph coefficients cannot memorize contact IDs, config labels or particular gap values.
Denominators guarded generically. Full12k graph scoring and global residual cover are excluded;
patch computation<=64 nodes, all scans/cache/build/invalidation charged.
Patch policy anchors: uniform (sample selected), blocked_gain (sample unselected and inspect current blockers),
rejection_frontier (sample previous rejected repair region), resource_boundary (sample same-resource selected contacts).
Destroy_count1..12 removes current selected contacts, adds their legal neighbors, fixes all outside contacts;
cap16..64, expand_hops1..2. Extra nodes must pass exact outside feasibility.
Reconstruction greedy=your dynamic ranking actually chooses each root; rcl=random choice from top3;
exchange=your ranking first constructs, then a shared weighted improving1/2-swap can augment it.
Kernel keeps best-so-far feasible schedule, records every raw negative/zero proposal, checks integer gain,
controls deadlines, and never accepts an LLM claim as feasibility or bounds.
evaluation_plan max_feature_cpu_fraction caps a trial; a timed-out partial proposal is rejected, not falsely evaluated.
adaptation_template affects the actual mutation/stagnation controller. Online mutation can adjust
coefficients, patch size/anchor/reconstruction, combine your feature expressions with another recipe,
and alter their rule composition; a fixed recipe ensemble alone is insufficient.
Create useful and computationally modest structural distinctions, cost plans and search strategies.
Include at least one genuinely cheap structural recipe and diverse destroy/reconstruct mechanisms.
The schema and actual interpreter define supported operations; no invented operation or unexecuted plan.

TRAIN-ONLY EVIDENCE JSON:
'''+json.dumps(body,ensure_ascii=False,separators=(',',':'))
        prompt_path=call/'prompt.txt'; prompt_path.write_text(prompt,encoding='utf-8')
        cwd=Path(tempfile.mkdtemp(prefix='cipheur-v2-llm-isolated-'))
        executable=args.cli or shutil.which('codex')
        assert executable, 'Native CLI is required for real model participation'
        argv=[str(executable),'exec','--ignore-user-config','--ignore-rules','--model','gpt-6.1-sol',
            '--sandbox','read-only','--skip-git-repo-check','--ephemeral','--json','--color','never',
            '--cd',str(cwd),'--output-schema',str(schema.resolve()),'-o',str((call/'response.json').resolve())]
        config=dict(model_reasoning_effort='ultra', web_search='disabled', project_doc_max_bytes=0,
            developer_instructions='Only stdin evidence. Pure JSON completion. No tools or filesystem access.')
        disabled=('shell_tool','unified_exec','shell_snapshot','apps','plugins','browser_use',
            'browser_use_external','computer_use','in_app_browser','multi_agent','memories','hooks',
            'code_mode_host','view_image','image_generation','workspace_dependencies','skill_search',
            'skill_mcp_dependency_install','sleep_tool','goals')
        for feature in disabled: config['features.'+feature]=False
        config['features.skip_host_skill_discovery']=True
        for key,value in config.items():argv.extend(['-c',key+'='+json.dumps(value)])
        argv.append('-')
        plan=dict(call_id=call.name,argv=argv,working_directory=str(cwd),stdin_path=str(prompt_path.resolve()),
            stdout_path=str((call/'events.jsonl').resolve()),stderr_path=str((call/'stderr.txt').resolve()),
            response_path=str((call/'response.json').resolve()),receipt_path=str((call/'execution_receipt.json').resolve()),
            model_requested='gpt-6.1-sol',model_observed='unknown',reasoning_effort_requested='ultra',
            prompt_sha256=digest(prompt_path),schema_sha256=digest(schema),
            TRAIN_packet_sha256=digest(ROOT/'context'/'train_failure_packet.json'),
            VAL_outcomes_used=False,TEST_outcomes_used=False,recipes_requested=6)
        save(call/'call_plan.json',plan)
        print(json.dumps(dict(call_id=call.name,prompt_bytes=prompt_path.stat().st_size),ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cli');ap.add_argument('--batch',type=int,default=0);args=ap.parse_args();prepare(args)
