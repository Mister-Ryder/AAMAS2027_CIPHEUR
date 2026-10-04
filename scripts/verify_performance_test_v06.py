"""Stream-audit the immutable V003 TEST execution, without solver/runtime imports.

Two archive passes keep only one decoded graph and context journal in memory.
Exact rewards, native contracts, common initialization, every retained patch
proof and charged phase sums are reconstructed independently. Verification CPU
is never an experimental timing. Failed/unreturned requests stay in the frame.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import heapq,json,math
from pathlib import Path,PurePosixPath
import sys,tarfile,tempfile,time,zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.verify_public_alias_v05 import view,graph_digest,exact_alpha
from scripts.verify_matched_llm_v05 import FeatureView
from scripts.verify_synthesis_train_v06 import feasible,score_lazy

STEM='performance_r2_eoh_test_v06_003_inputs'
STUDY=ROOT/'experiments/discovery/performance_r2_eoh_test_v06_003_registered_001'
RELEASE=ROOT/'experiments/discovery/v06_test_release_002/performance_root_release.json'

def digest(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def canonical(x):return sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def key(r):
    if 'nominal_wall_target_seconds' in r:
        target=r['nominal_wall_target_seconds']
        if 'target' in r and r['target']!=target:raise ValueError('Conflicting nominal/compact target fields')
    else:target=r['target']
    return r['id'],target,r['track'],r['method'],r['seed']
def nonnegative(x):return type(x) in (int,float) and math.isfinite(x) and x>=0

def cohort(p):
    if p['kind']=='genuine_R2_witness_joint':return 'joint_W'
    if p['kind']=='nonguarded_R2_quality_comparator':return 'quality_'+{'witness':'W','relations':'R','objective':'O'}[p['arm']]
    if p['kind']=='nonguarded_published_EoH_DSL_quality':return 'published_EoH_DSL_quality'
    if p['kind']=='quality_only_fixed_control':return {'enumerated_structural':'control_structural','fixed_base9':'control_base9'}[p['arm']]
    if p['method_id']=='Degree':return 'Degree'
    raise ValueError('Unregistered policy cohort')

def safe_member(m):
    p=PurePosixPath(m.name)
    if '..' in p.parts or p.is_absolute() or '\\' in m.name or not (m.isfile() or m.isdir()):
        raise ValueError('Unsafe archive member: '+m.name)

def expected_keys(contexts,protocol,programs):
    for c in contexts:
        for target in protocol['wall_targets']:
            for m in protocol['native_requests']:yield c['id'],target,'native',m['method'],m['seed']
            yield c['id'],target,'common_initializer','CHILS_half',1
            for track in ('cold_Degree','warm_CHILS'):
                for p in programs:yield c['id'],target,track,p['method_id'],1

class Audit:
    def __init__(self):self.checks=Counter();self.errors=[];self.totals=Counter()
    def check(self,ok,kind,where=''):
        self.checks[kind]+=1
        if not ok:self.errors.append({'kind':kind,'where':where})

def successful_initializer(row):
    result=row.get('result') if isinstance(row,dict) else None
    return (isinstance(row,dict) and row.get('runner_error') is None
        and row.get('successful_assignment') is True and isinstance(result,dict)
        and result.get('completed') is True and result.get('feasible') is True)

def policy_phase_receipts(row,program,initial_row,audit,where):
    """Check the original runner's executed/skipped phase and failure receipts."""
    warm=row['track']=='warm_CHILS';initial=initial_row.get('result') if initial_row else None
    executed=program['available'] is True and (not warm or successful_initializer(initial_row))
    audit.check(row.get('policy_nominal_seconds')==row['nominal_wall_target_seconds']*(.5 if warm else 1),
        'original_policy_phase_nominal_target',where)
    times=(row.get('policy_wrapper_wall_seconds'),row.get('policy_wrapper_cpu_seconds'))
    audit.check(all(nonnegative(x) for x in times) if executed else all(x is None for x in times),
        'executed_policy_phase_has_both_nonnegative_times',where)
    if row.get('result') is not None:
        audit.check(executed,'returned_policy_requires_executed_phase',where)
    error=row.get('runner_error')
    if error and error['type']=='NativeInitializerUnavailable':
        audit.check(warm and program['available'] is True and not successful_initializer(initial_row)
            and row.get('result') is None and row.get('advanced_track_available') is False
            and row.get('native_initial_result')==initial
            and row.get('shared_initializer_receipt_sha256')==(canonical(initial) if initial else None),
            'initializer_failure_no_fallback_and_exact_failed_receipt',where)

class GraphAudit:
    def __init__(self,graph,audit):
        self.source=graph;self.a=audit;self.nodes,self.edges,self.adj=view(graph)
        self.weights={v:Fraction(c['weight']) for v,c in self.nodes.items()}
        self.ids=sorted(self.nodes);self.index={v:i+1 for i,v in enumerate(self.ids)}
        self.global_order=sorted(self.ids,key=lambda v:(-self.weights[v]/max(1,len(self.adj[v])),v))
        self.initial_cache={};self.restriction_cache={};self.priority_cache={};self.exact_cache={}
        scale=math.lcm(*(w.denominator for w in self.weights.values()))
        h=sha256(f'{len(self.ids)} {len(self.edges)} 10\n'.encode())
        for v in self.ids:
            h.update((str(int(self.weights[v]*scale))+' '+' '.join(map(str,sorted(self.index[u] for u in self.adj[v])))+'\n').encode())
        self.integer_scale=scale;self.metis_sha=h.hexdigest();self.total_integer=sum(int(w*scale) for w in self.weights.values())

    def value(self,chosen):return sum((self.weights[v] for v in chosen),Fraction())

    def initialize(self,result,start,where):
        trace=result['initializer_trace'];cachekey=(tuple(sorted(start)),canonical(trace))
        if cachekey in self.initial_cache:incumbent,remaining=self.initial_cache[cachekey];return set(incumbent),remaining
        incumbent=set(start);active=set(self.ids)-incumbent
        for v in incumbent:active-=self.adj[v]
        degrees={v:len(self.adj[v]&active) for v in active};heap=[]
        for v in active:heapq.heappush(heap,(-self.weights[v]/max(1,degrees[v]),v,degrees[v]))
        for step in trace:
            while heap:
                negative,v,d=heapq.heappop(heap)
                if v in active and d==degrees[v]:break
            else:raise ValueError('Initializer trace exceeds independent legal active set')
            self.a.check(step['selected']==v and step['available']==len(active) and Fraction(step['score_exact'])==-negative,
                'exact_common_degree_prefix',where)
            deleted=({v}|self.adj[v])&active;incumbent.add(v);active-=deleted;affected=set()
            for u in deleted:
                for n in self.adj[u]&active:degrees[n]-=1;affected.add(n)
            for n in affected:heapq.heappush(heap,(-self.weights[n]/max(1,degrees[n]),n,degrees[n]))
        self.initial_cache[cachekey]=(frozenset(incumbent),len(active));return incumbent,len(active)

    def restriction(self,incumbent,p,cfg):
        k=(tuple(sorted(incumbent)),tuple(p['destroy']),p['target'])
        if k in self.restriction_cache:return self.restriction_cache[k]
        destroy=set(p['destroy']);outside=incumbent-destroy;blocked=set(outside)
        for v in outside:blocked|=self.adj[v]
        keep=set(destroy)
        if len(keep)<cfg['max_patch_vertices']:keep.add(p['target'])
        for v in self.global_order:
            if len(keep)>=cfg['max_patch_vertices']:break
            if v not in blocked:keep.add(v)
        result=(frozenset(keep),len(self.ids)-len(blocked));self.restriction_cache[k]=result;return result

    def order(self,patch,program,priority):
        k=(tuple(sorted(patch)),canonical(program),priority)
        if k not in self.priority_cache:
            degree=sorted(patch,key=lambda v:(-self.weights[v]/max(1,len(self.adj[v]&patch)),v))
            if priority=='degree':order=degree
            else:
                # All typed vertex-set operations are subsets of active. This
                # induced edge view has identical semantics to the full scan.
                state=FeatureView.__new__(FeatureView);state.source=self.source;state.nodes=self.nodes;state.adj=self.adj
                state.active=frozenset(patch);state.cache={}
                state.edges={tuple(sorted((v,u))) for v in patch for u in self.adj[v]&patch}
                scores={v:score_lazy(program,state,v) for v in sorted(patch)}
                order=sorted(patch,key=lambda v:(-scores[v],v))
            self.priority_cache[k]=(order,degree)
        return self.priority_cache[k]

    def kernel(self,result,program,protocol,target,start,where):
        a=self.a;cfg=protocol['repair_config'];priority='degree' if program['method_id']=='Degree' else 'program'
        a.check(program['available'] is True,'available_frozen_identity_no_fallback',where)
        a.check(result['config']==cfg and result['priority']==priority and result['declared_seconds']==target
            and result['deadline_clock']=='wall' and result['random_seed']==1,'frozen_shared_kernel_contract',where)
        a.check(result['feasible'] and result['incumbent_available'] and not result['fallback_used']
            and result['online_model_calls']==result['conditional_oracle_calls']==0 and not result['exact_optimum_claimed'],
            'no_online_model_oracle_global_optimum_or_fallback',where)
        a.check(result['completed']==(result['error'] is None),'programme_error_not_anytime_completion',where)
        incumbent,remaining=self.initialize(result,start,where)
        a.check(sorted(incumbent)==result['initial_selected'] and self.value(incumbent)==Fraction(result['initial_value_exact'])
            and (not result['initialization_complete'] or remaining==0),'retained_seed_and_prefix_scope',where)
        a.check(Fraction(result['starting_value_exact'])==self.value(start),'actual_supplied_initializer',where)
        commits=expanded=0
        for p in result['patch_trace']:
            a.totals['patch_traces']+=1;destroy=set(p['destroy']);outside=incumbent-destroy;replacement=set(p['local_selected'])
            a.check(destroy<=incumbent and len(destroy)<=cfg['max_destroy'] and p['target'] not in incumbent
                and self.adj[p['target']]&incumbent<=destroy and Fraction(p['incumbent_patch_exact'])==self.value(destroy),
                'legal_destroy_boundary',where)
            a.check(feasible(self.nodes,self.adj,p['local_selected']) and Fraction(p['lower_exact'])==self.value(replacement)
                and self.value(replacement)>=self.value(destroy),'exact_feasible_patch_lower',where)
            if p['patch'] is None:
                a.check(p['stage']=='region_construction' and replacement==destroy and not p['committed']
                    and p['upper_exact'] is None and not p['restricted_exact'],'interrupted_region_not_computed',where)
            else:
                patch=set(p['patch']);expected,nfree=self.restriction(incumbent,p,cfg)
                a.check(patch==expected and replacement<=patch and p['full_region_size']==nfree
                    and p['restricted']==(len(patch)!=nfree),'exact_common_degree_patch_restriction',where)
                if p['root_upper_exact'] is None:
                    a.check(p['upper_exact'] is None and not p['restricted_exact'] and not p['root_clique_cover'],
                        'uncomputed_root_upper_remains_unknown',where)
                else:
                    cover=p['root_clique_cover'];flat=[v for c in cover for v in c]
                    a.check(len(flat)==len(set(flat)) and set(flat)==patch and all(c and all(b in self.adj[v]
                        for i,v in enumerate(c) for b in c[i+1:]) for c in cover),'clique_partition_upper_proof',where)
                    upper=sum((max(self.weights[v] for v in c) for c in cover),Fraction())
                    a.check(upper==Fraction(p['root_upper_exact']) and upper>=self.value(replacement),'exact_sound_root_enclosure',where)
                    if p['restricted_exact']:
                        k=tuple(sorted(patch))
                        if k not in self.exact_cache:self.exact_cache[k]=exact_alpha(self.nodes,self.adj,patch,max_states=1000000)
                        a.check(self.exact_cache[k][0]==self.value(replacement)==Fraction(p['upper_exact']),
                            'independent_restricted_optimum',where)
                    else:a.check(Fraction(p['upper_exact'])==upper,'partial_search_retains_upper',where)
                if p['priority_order']:
                    order,degree=self.order(patch,program['program'],priority)
                    a.check(p['priority_order']==order and (not p['common_degree_order'] or p['common_degree_order']==degree),
                        'independent_local_priority_order',where)
                    for g in p['greedy_passes']:
                        remaining=set(patch);taken=set();prefix={Fraction()}
                        for v in order if g['order']=='priority' else degree:
                            if v in remaining:taken.add(v);remaining-={v}|self.adj[v]
                            prefix.add(self.value(taken))
                        a.check(Fraction(g['value_exact']) in prefix and (not g['complete'] or Fraction(g['value_exact'])==self.value(taken)),
                            'local_greedy_prefix_or_complete_reward',where)
            gain=self.value(replacement)-self.value(destroy)
            a.check(Fraction(p['gain_exact'])==gain and p['committed']==(gain>0),'strict_improvement_commit_rule',where)
            if p['committed']:
                incumbent=outside|replacement;commits+=1
                a.check(feasible(self.nodes,self.adj,incumbent),'global_commit_original_feasibility',where)
            a.check(0<=p['search_nodes']<=cfg['node_budget_per_patch'],'per_patch_node_cap',where);expanded+=p['search_nodes']
        a.check(sorted(incumbent)==result['selected'] and commits==result['improvements']
            and len(result['patch_trace'])==result['patches_attempted']<=cfg['max_patches'],'complete_retained_incumbent_replay',where)
        meter=result['meter'];a.check(expanded<=meter['search_nodes']<=cfg['max_search_nodes'],'global_node_cap',where)
        for name in ('feature','repair'):
            work,parts=meter[name+'_work'],meter[name+'_primitives']
            a.check(type(work)is int and work>=0 and all(type(v)is int and v>=0 for v in parts.values())
                and sum(parts.values())<=work and (result['global_budget_exhausted'] or sum(parts.values())==work),
                'charged_work_primitive_receipts',where)
        a.check(all(nonnegative(result[k]) for k in ('wall_seconds','cpu_seconds')),'actual_kernel_time_receipts',where)
        a.totals['kernel_results_verified']+=1

    def native(self,r,result,protocol,where):
        a=self.a;method='CHILS' if r['track']=='common_initializer' else r['method'];target=r['nominal_wall_target_seconds']*(.5 if r['track']=='common_initializer' else 1)
        limit=2**63-1 if method in ('CHILS','CHILS_ILS') else 2**31-1
        supported=self.total_integer<=limit and all(0<=w*self.integer_scale<=limit for w in self.weights.values())
        a.check(result['method']==method and result['seed']==r['seed'] and result['declared_seconds']==target
            and result['hard_wall_seconds']==30 and result['threads']==1 and not result['exact_optimum_claimed'],
            'native_nominal_budget_and_identity',where)
        a.check(all(nonnegative(result[k]) for k in ('wrapper_wall_seconds','wrapper_self_cpu_seconds','seconds')),
            'individual_native_wrapper_time_receipts',where)
        if not supported:
            a.check(result['status']=='encoding_not_supported' and not result['solver_invoked'] and result['selected'] is None
                and result['completed'] is False and result['feasible'] is None,'explicit_lossless_encoding_limitation',where);return
        executable=protocol['executables']['CHILS' if method=='CHILS_ILS' else method]
        a.check(result['input_sha256']==self.metis_sha and result['integer_scale']==self.integer_scale
            and result['executable_sha256']==executable['sha256'],'native_exact_graph_and_binary_binding',where)
        command=result['command']
        graph_path=PurePosixPath(command[2] if method in ('CHILS','CHILS_ILS') else command[1])
        solution_path=PurePosixPath(command[4] if method in ('CHILS','CHILS_ILS') else command[2].removeprefix('--output='))
        a.check(graph_path.is_absolute() and graph_path.name=='input.graph' and solution_path.name=='solution.txt'
            and graph_path.parent==solution_path.parent and graph_path.parent.name.startswith('cipheur_v06_solver_'),
            'native_input_output_temporary_file_contract',where)
        if method in ('CHILS','CHILS_ILS'):
            a.check(len(command)==15 and command[0]==executable['path'] and command[1]=='-g' and command[3]=='-o'
                and command[5:]==['-p','1' if method=='CHILS_ILS' else '4','-c','1','-s','0.1','-t',str(target),'-r',str(r['seed'])],
                'published_CHILS_command',where)
        else:
            suffix=[f'--time_limit={target}',f'--seed={r["seed"]}']
            if method=='M2WIS':suffix+=['--config=mmwis',f'--evo_time_limit={target}',f'--ils_time_limit={target}']
            a.check(command[0]==executable['path'] and command[2].startswith('--output=') and command[3:]==suffix,
                'published_native_command',where)
        a.check(result['solver_invoked'] and nonnegative(result['child_cpu_seconds']),'native_child_execution_receipt',where)
        a.check(result['nominal_target_exceeded']==(result['seconds']>target),'actual_native_overshoot_receipt',where)
        if result['completed']:
            raw=[int(x) for x in result['solution_text'].split()]
            if method in ('CHILS','CHILS_ILS'):
                valid=len(raw)==len(set(raw)) and all(1<=x<=len(self.ids) for x in raw)
                chosen=sorted(self.ids[x-1] for x in raw) if valid else []
                a.check(valid and result['output_format']=='one_based_ids' and chosen==result['selected'],'native_saved_ID_solution',where)
            else:
                valid=len(raw)==len(self.ids) and set(raw)<={0,1};chosen=[v for v,f in zip(self.ids,raw) if f==1]
                a.check(valid and result['output_format']=='partition_flags' and chosen==result['selected'],'native_saved_flag_solution',where)
            a.check(result['returncode']==0 and result['status']=='checked_feasible_incumbent','native_successful_exit',where)
        else:a.check(result['selected'] is None and result['status'] in ('hard_guard_timeout','solver_output_error'),
            'native_failures_have_no_success_objective',where)

def audit(archive,archive_sha,out,rows_out):
    began=time.perf_counter();archive,out,rows_out=map(Path,(archive,out,rows_out));a=Audit()
    if out.exists() or rows_out.exists():raise ValueError('Preserve previous audit and compact rows')
    if digest(archive)!=archive_sha:raise ValueError('Actual canonical server archive SHA mismatch')
    protocol=json.loads((STUDY/'protocol.json').read_bytes());deployment=json.loads((STUDY/'deployment.json').read_bytes())
    for path,h in ((STUDY/'protocol.json','59395b0b7f4c8460da8e58bcdccaa292b189a627716e1e050c52b7a659ba4cfa'),
                   (STUDY/'source.zip','b08d95b17d571a19a062109726e0bb7f4f80322addcd099b73b8f3568c494f09'),
                   (STUDY/'deployment.json','4873ed683327f2e271c36dacac625df52bb8dd0a678dc293035946b27ba126fb'),
                   (STUDY/'server_input_preparation/input_freeze.json','42f7e9606499e379063c81d66d96beaa9cefb77be57be66c6076784ff33e4689'),
                   (RELEASE,'5b6f82647e282a4491ad3b49775a21cf91afddfc1c2f46ea1defdad9d13e5063')):
        if digest(path)!=h:raise ValueError('Pre-query scientific binding changed: '+str(path))
    inventory=json.loads((STUDY/'server_input_preparation/context_inventory.json').read_bytes());contexts=inventory['contexts'];byid={c['id']:c for c in contexts}
    programs=deployment['programs'];byp={p['method_id']:p for p in programs};expected=set(expected_keys(contexts,protocol,programs))
    a.check(len(contexts)==302 and len(programs)==23 and len(expected)==52548,'complete_preregistered_frame')
    a.check(protocol['repair_config']['policy_scope']=='branch','shared_Degree_target_and_restriction')
    for n,h in protocol['source_sha256'].items():a.check(digest(ROOT/n)==h,'unchanged_scientific_source',n)
    with zipfile.ZipFile(STUDY/'source.zip') as z:
        for n,h in protocol['source_sha256'].items():a.check(sha256(z.read(n)).hexdigest()==h,'original_source_capsule',n)
    bindings={};aggregated={};aggregated_nulls={};journal_hashes={};journal_paths={};unreturned=[];members={};status=Counter();seen=set();compact_count=0
    partial_aggregate=False
    stage_root=ROOT/'.research/performance_audit_staging';stage_root.mkdir(parents=True,exist_ok=True)
    rows_out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v003_',dir=stage_root) as stage:
        stage=Path(stage)
        with tarfile.open(archive,'r|gz') as tar:
            for m in tar:
                safe_member(m)
                if not m.isfile():continue
                if m.name in members:raise ValueError('Duplicate archive member')
                stream=tar.extractfile(m);h=sha256();relative=PurePosixPath(m.name)
                if relative.parts[0]!=STEM:raise ValueError('Unexpected execution archive root')
                name='/'.join(relative.parts[1:])
                if name.startswith('graphs/'):
                    dest=stage/relative.name
                    with dest.open('xb') as f:
                        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b);f.write(b)
                elif name=='results.jsonl':
                    for line in stream:
                        h.update(line)
                        if not line.strip():continue
                        try:r=json.loads(line)
                        except json.JSONDecodeError:
                            tail=stream.read();h.update(tail)
                            if tail:raise ValueError('Malformed aggregate line before archive member end')
                            partial_aggregate=True;break
                        k=key(r)
                        if k in aggregated:raise ValueError('Duplicate aggregate assignment')
                        aggregated[k]=canonical(r)
                        if r.get('result') is None:aggregated_nulls[k]=r
                elif name.startswith('context_results/'):
                    # Journals are audited in the second stream, after graphs
                    # and all launch/selection byte bindings are known.
                    for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
                    journal_paths[name]=m.size
                else:
                    raw=stream.read();h.update(raw)
                    if name.endswith('.json') and not name.startswith('graphs/'):bindings[name]=json.loads(raw)
                    elif name=='unreturned_assignments.jsonl':unreturned=[json.loads(l) for l in raw.splitlines() if l]
                members[m.name]=h.hexdigest()
        frozen=bindings['input_freeze.json'];host=bindings['host_receipt.json'];execution=bindings['server_execution_receipt.json']
        for n in ('protocol.json','deployment.json','TRAIN_selection.json','controls_TRAIN_selection.json','independent_TRAIN_audit.json',
                  'published_EoH_TRAIN_selection.json','published_EoH_author_audit.json','published_EoH_TRAIN_audit.json'):
            a.check(members[STEM+'/'+n]==digest(STUDY/n),'executed_exact_predeclared_identity_binding',n)
        a.check(members[STEM+'/root_release.json']==digest(RELEASE)==host['root_release_sha256'],
            'actual_root_authorized_launch')
        a.check(members[STEM+'/context_inventory.json']==digest(STUDY/'server_input_preparation/context_inventory.json')==frozen['context_inventory_sha256']
            and members[STEM+'/input_freeze.json']==digest(STUDY/'server_input_preparation/input_freeze.json'),
            'original_complete_prepared_context_frame')
        a.check(execution['retries']==0 and execution['all_partial_journals_retained'] and host['workers']==8,'original_execution_no_retry')
        a.check(not partial_aggregate or execution['whole_batch_guard_triggered'] or execution['exit_code']!=0,
            'partial_aggregate_tail_only_after_original_batch_interruption')
        a.check(execution['source_zip_sha256']==deployment['source_zip_sha256']==host['source_zip_sha256']
            and host['before_any_TEST_solver_outcomes'] and bindings['launch_receipt.json']['assigned']==52548
            and bindings['launch_receipt.json']['root_release_sha256']==host['root_release_sha256']
            and bindings['launch_receipt.json']['whole_batch_wall_guard_seconds']==14400,
            'host_launch_execution_complete_source_and_guard_binding')
        for c in contexts:a.check(members[STEM+'/'+c['graph_file']]==c['graph_file_sha256']==frozen['graph_files_sha256'][c['graph_file']],
            'original_lossless_graph_bytes',c['id'])
        with rows_out.open('x',encoding='utf-8',newline='\n') as compact,tarfile.open(archive,'r|gz') as tar:
            for m in tar:
                if not m.isfile() or not m.name.startswith(STEM+'/context_results/'):continue
                stream=tar.extractfile(m);rawlines=list(stream);h=sha256(b''.join(rawlines)).hexdigest()
                a.check(h==members[m.name],'journal_second_pass_same_bytes',m.name)
                rows=[];partial=False
                for i,line in enumerate(rawlines):
                    try:r=json.loads(line)
                    except json.JSONDecodeError:
                        a.check(i==len(rawlines)-1 and (execution['whole_batch_guard_triggered'] or execution['exit_code']!=0),
                            'partial_final_line_only_after_guard_or_failure',m.name);partial=True;break
                    rows.append(r)
                if not rows:continue
                c=byid[rows[0]['id']];token=sha256(c['id'].encode()).hexdigest()[:16]
                a.check(m.name==STEM+'/context_results/'+token+'.jsonl' and all(r['id']==c['id'] for r in rows),'journal_context_identity',m.name)
                graph=json.loads((stage/PurePosixPath(c['graph_file']).name).read_bytes());g=GraphAudit(graph,a)
                a.check(graph_digest(graph)==c['graph_sha256'] and len(g.nodes)==c['n'] and len(g.edges)==c['m']
                    and len(graph['edges'])==len(g.edges) and g.value(g.nodes)/c['source_weight_scale']==Fraction(c['total_source_weight_exact']),
                    'independent_graph_identity_and_original_units',c['id'])
                loading=bindings.get('context_loading/'+token+'.json',{});inits={};init_rows={}
                for r in rows:
                    k=key(r);where='|'.join(map(str,k));a.check(k in expected and k not in seen,'every_unique_original_assignment',where);seen.add(k)
                    if k in aggregated:a.check(canonical(r)==aggregated[k],'journal_aggregate_exact_row_identity',where)
                    journal_hashes[k]=canonical(r)
                    for field in ('population','split','n','m','graph_sha256','source_weight_scale','total_source_weight_exact'):
                        a.check(r[field]==c[field],'original_context_row_metadata',where+':'+field)
                    a.check(r.get('pair_id')==c.get('pair_id') and r.get('side')==c.get('side'),'original_paired_endpoint_metadata',where)
                    result=r.get('result');error=r.get('runner_error');ok=error is None and result is not None and result.get('completed') is True and result.get('feasible') is True
                    a.check(r['successful_assignment']==ok and r['assignment_returned'],'success_scope_and_returned_flag',where)
                    reward=None
                    if result and result.get('selected') is not None:
                        a.check(feasible(g.nodes,g.adj,result['selected']),'original_graph_selected_feasibility',where)
                        reward=g.value(result['selected'])/c['source_weight_scale']
                        a.check(Fraction(result['value_exact'])==reward*c['source_weight_scale'],'exact_original_reward',where)
                    a.check(r.get('value_exact_original_objective')==(str(reward) if reward is not None else None)
                        and r['quality_reward_exact_original_objective']==(str(reward) if ok else None)
                        and r.get('diagnostic_retained_reward_exact_original_objective')==(str(reward) if not ok and reward is not None else None),
                        'no_failed_incumbent_in_success_quality',where)
                    a.check(r.get('input_total_weight_fraction_exact')==(str(reward/Fraction(c['total_source_weight_exact'])) if ok else None),
                        'exact_total_weight_fraction_not_optimum',where)
                    wall=cpu=nwall=ncpu=pwall=pcpu=None;work=search=None
                    if r['track'] in ('native','common_initializer') and result:
                        g.native(r,result,protocol,where);wall=nwall=result['wrapper_wall_seconds'];cpu=ncpu=result['wrapper_self_cpu_seconds']+result.get('child_cpu_seconds',0)
                        if r['track']=='common_initializer':
                            inits[r['nominal_wall_target_seconds']]=result
                            init_rows[r['nominal_wall_target_seconds']]=r
                            a.check(r['shared_initializer_receipt_sha256']==canonical(result),'shared_initializer_exact_receipt',where)
                    elif r['track'] in ('cold_Degree','warm_CHILS'):
                        p=byp[r['method']]
                        mapping={'program_kind':'kind','program_role':'role','program_sha256':'program_sha256','joint_eligible':'joint_eligible',
                                 'authoring_block':'block','authoring_arm':'arm','source_candidate_id':'source_candidate_id','published_authoring_run':'run','published_winner_origin':'winner_origin'}
                        for f,pf in mapping.items():a.check(r[f]==p.get(pf),'preserved_frozen_program_role',where+':'+f)
                        init=inits.get(r['nominal_wall_target_seconds']);warm=r['track']=='warm_CHILS';phase=r['nominal_wall_target_seconds']*(.5 if warm else 1)
                        policy_phase_receipts(r,p,init_rows.get(r['nominal_wall_target_seconds']),a,where)
                        if r.get('policy_wrapper_wall_seconds') is not None:
                            pwall=r['policy_wrapper_wall_seconds'];pcpu=r['policy_wrapper_cpu_seconds'];wall=pwall;cpu=pcpu
                            a.check(nonnegative(pwall) and nonnegative(pcpu),'individual_policy_phase_times_nonnegative',where)
                            if warm and init is not None and init['completed'] and init['feasible']:
                                nwall=init['wrapper_wall_seconds'];ncpu=init['wrapper_self_cpu_seconds']+init.get('child_cpu_seconds',0)
                                wall=nwall+pwall;cpu=ncpu+pcpu
                                a.check(r['standalone_pipeline_wall_seconds']==wall and r['standalone_pipeline_cpu_seconds']==cpu,
                                    'exception_or_normal_policy_phase_cost_preserved',where)
                        if result:
                            a.check(p['available'] is True,'unavailable_identity_cannot_return_fallback',where)
                            if warm:
                                init_row=init_rows.get(r['nominal_wall_target_seconds'],{})
                                a.check(init_row.get('runner_error') is None and init_row.get('successful_assignment') is True
                                    and init is not None and init['completed'] is True and init['feasible'] is True,
                                    'warm_requires_error_free_successful_original_initializer_row',where)
                            start=init['selected'] if warm else []
                            g.kernel(result,p,protocol,phase,start,where)
                            pwall=r['policy_wrapper_wall_seconds'];pcpu=r['policy_wrapper_cpu_seconds'];wall=pwall;cpu=pcpu
                            work=result['meter']['feature_work']+result['meter']['repair_work'];search=result['meter']['search_nodes']
                            if warm:
                                nwall=init['wrapper_wall_seconds'];ncpu=init['wrapper_self_cpu_seconds']+init.get('child_cpu_seconds',0);wall=nwall+pwall;cpu=ncpu+pcpu
                                a.check(r['native_initial_selected']==init['selected'] and r['native_initial_value_exact']==init['value_exact']
                                    and r['shared_initializer_receipt_sha256']==canonical(init) and Fraction(result['value_exact'])>=Fraction(init['value_exact'])
                                    and r['standalone_pipeline_wall_seconds']==wall and r['standalone_pipeline_cpu_seconds']==cpu
                                    and r['native_initialization_cost_shared_in_actual_execution'] and r['advanced_track_available'],
                                    'full_initializer_cost_charged_and_monotone_warm_seed',where)
                        else:
                            a.check(not ok and error is not None,'missing_or_failed_policy_remains_null',where)
                            if error and error['type']=='MissingFrozenQualityOnlyPosition':a.check(not p['available'],'missing_frozen_identity_no_replacement',where)
                    if wall is not None:a.check(all(nonnegative(x) for x in (wall,cpu)),'actual_standalone_time_receipts',where)
                    statusname=result['status'] if result else (error['type'] if error else 'missing_error')
                    status[r['track']+':'+statusname]+=1
                    row={f:c.get(f) for f in ('id','population','family','n','cluster','pair_id','side','source_cluster')}
                    row['source_cluster']=c.get('source_cluster') or c.get('cluster') or c.get('pair_id')
                    row.update(regime=c.get('regime',c.get('source',{}).get('regime')),profile=c.get('profile',c.get('source',{}).get('profile')))
                    row.update(target=r['nominal_wall_target_seconds'],track=r['track'],method=r['method'],seed=r['seed'],
                        analysis_cohort=cohort(byp[r['method']]) if r['method'] in byp else r['method'],
                        success=ok,returned=True,status=statusname,error=error or (result.get('error') if result else None),
                        reward_exact=str(reward) if ok else None,diagnostic_reward_exact=str(reward) if not ok and reward is not None else None,
                        total_exact=c['total_source_weight_exact'],standalone_wall_seconds=wall,standalone_cpu_seconds=cpu,
                        native_wall_seconds=nwall,native_cpu_seconds=ncpu,policy_wall_seconds=pwall,policy_cpu_seconds=pcpu,
                        shared_graph_load_wall_seconds=loading.get('shared_graph_load_wall_seconds'),shared_graph_load_cpu_seconds=loading.get('shared_graph_load_cpu_seconds'),
                        work=work,search_nodes=search,feature_work=result.get('meter',{}).get('feature_work') if result else None)
                    for f in ('program_kind','program_role','program_sha256','authoring_block','authoring_arm','source_candidate_id','published_winner_origin'):
                        row[f]=r.get(f)
                    compact.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');compact_count+=1
                print(json.dumps({'verified_context':c['id'],'assignments_so_far':compact_count,'errors':len(a.errors)}),flush=True)
                del g,graph,rawlines,rows
            # Aggregate-generated missing worker receipts are absent from the
            # journals. Preserve them as explicit nulls, not fabricated times.
            missing_aggregated=[]
            for k,h in aggregated.items():
                if k not in seen:
                    r=aggregated_nulls.get(k)
                    a.check(r is not None and r.get('runner_error') is not None and r['result'] is None and r['assignment_returned'] is True,
                        'aggregate_worker_failure_is_explicit_null',str(k))
                    if r is not None:missing_aggregated.append(r)
            for r in unreturned+missing_aggregated:
                k=key(r);a.check(k in expected and k not in seen and r['assignment_returned']==(r in missing_aggregated)
                    and not r['successful_assignment'] and r['result'] is None and r['quality_reward_exact_original_objective'] is None,
                    'every_guard_unreturned_request_explicit_null',str(k));seen.add(k)
                c=byid[r['id']]
                for field in ('population','split','n','m','graph_sha256','source_weight_scale','total_source_weight_exact'):
                    a.check(r[field]==c[field],'unmeasured_row_original_context_metadata',str(k)+':'+field)
                a.check(r.get('value_exact_original_objective') is None and r.get('diagnostic_retained_reward_exact_original_objective') is None
                    and r.get('input_total_weight_fraction_exact') is None and all(r.get(f) is None for f in
                    ('standalone_pipeline_wall_seconds','standalone_pipeline_cpu_seconds','policy_wrapper_wall_seconds','policy_wrapper_cpu_seconds')),
                    'unmeasured_stub_has_no_diagnostic_reward_or_fabricated_times',str(k))
                if r['method'] in byp:
                    p=byp[r['method']]
                    for f,pf in {'program_kind':'kind','program_role':'role','program_sha256':'program_sha256','joint_eligible':'joint_eligible',
                                 'authoring_block':'block','authoring_arm':'arm','source_candidate_id':'source_candidate_id',
                                 'published_authoring_run':'run','published_winner_origin':'winner_origin'}.items():
                        a.check(r[f]==p.get(pf),'unmeasured_stub_frozen_program_role',str(k)+':'+f)
                c=byid[r['id']];row={f:c.get(f) for f in ('id','population','family','n','cluster','pair_id','side','source_cluster')}
                row['source_cluster']=c.get('source_cluster') or c.get('cluster') or c.get('pair_id')
                row.update(regime=c.get('regime',c.get('source',{}).get('regime')),profile=c.get('profile',c.get('source',{}).get('profile')))
                row.update(target=r['nominal_wall_target_seconds'],track=r['track'],method=r['method'],seed=r['seed'],success=False,returned=r['assignment_returned'],
                    analysis_cohort=cohort(byp[r['method']]) if r['method'] in byp else r['method'],
                    status=r['runner_error']['type'],error=r['runner_error'],reward_exact=None,diagnostic_reward_exact=None,total_exact=c['total_source_weight_exact'],
                    standalone_wall_seconds=None,standalone_cpu_seconds=None,native_wall_seconds=None,native_cpu_seconds=None,policy_wall_seconds=None,policy_cpu_seconds=None,
                    shared_graph_load_wall_seconds=None,shared_graph_load_cpu_seconds=None,work=None,search_nodes=None,feature_work=None)
                for f in ('program_kind','program_role','program_sha256','authoring_block','authoring_arm','source_candidate_id','published_winner_origin'):row[f]=r.get(f)
                compact.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');compact_count+=1;status[r['track']+':'+row['status']]+=1
    a.check(seen==expected and compact_count==len(expected),'complete_frame_including_missing_and_failed')
    if 'completion.json' in bindings:
        complete=bindings['completion.json'];a.check(complete['returned']==complete['assigned']==52548 and complete['contexts']==302
            and complete['results_sha256']==members[STEM+'/results.jsonl'] and complete['online_model_calls']==complete['conditional_oracle_calls']==0
            and complete['all_rows_retained'] and not unreturned and set(aggregated)==expected,'terminal_complete_original_batch')
        a.check(complete['deployment_sha256']==digest(STUDY/'deployment.json') and complete['protocol_sha256']==digest(STUDY/'protocol.json')
            and execution['exit_code']==0 and execution['whole_batch_guard_triggered'] is False and not partial_aggregate,
            'complete_batch_exact_deployment_protocol_and_successful_exit')
        a.check(Counter(complete['status_counts'])==status,'terminal_status_count_reconstruction')
    else:a.check(execution['whole_batch_guard_triggered'] or execution['exit_code']!=0,'incomplete_batch_guard_or_error_explicit')
    report={'version':'v06_independent_performance_TEST_audit_001',
        'errors':len(a.errors),'error_details':a.errors,'checks':sum(a.checks.values()),'checks_by_kind':dict(a.checks),
        'totals':dict(a.totals),'archive_sha256':archive_sha,'audited_rows_sha256':digest(rows_out),'audited_rows_path':str(rows_out),
        'audit_source_sha256':digest(__file__),'registered_constants':{'wall_targets':[.1,1,5],'total_contexts':302,'total_assignments':52548,'policy_slots':23},
        'independent_helper_sha256':{n:digest(ROOT/n) for n in
            ('scripts/verify_public_alias_v05.py','scripts/verify_matched_llm_v05.py','scripts/verify_synthesis_train_v06.py')},
        'policies':[{'method':p['method_id'],'analysis_cohort':cohort(p),'program_kind':p['kind'],'program_role':p['role'],
            'authoring_block':p.get('block'),'authoring_arm':p.get('arm'),'program_sha256':p.get('program_sha256'),
            'published_winner_origin':p.get('winner_origin')} for p in programs],
        'status_counts':dict(status),'host':host,'execution':execution,'wall_seconds_verification_only':time.perf_counter()-began,
        'scope':'Independent root mathematical/receipt audit; no scheduler, solver or conditional oracle import/call; exactness only for explicit saved restricted patches. Mechanical verification is distinct from separately staffed review.'}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'errors':report['errors'],'checks':report['checks'],'audited_rows':compact_count}),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',required=True);p.add_argument('--archive-sha256',required=True)
    p.add_argument('--out',required=True);p.add_argument('--rows-out',required=True);args=p.parse_args()
    result=audit(args.archive,args.archive_sha256,args.out,args.rows_out)
    sys.exit(bool(result['errors']))
