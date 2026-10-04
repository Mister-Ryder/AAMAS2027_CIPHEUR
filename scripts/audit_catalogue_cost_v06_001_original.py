"""Read-only catalogue audit: replay features/cuts/quotients; NEVER run a master."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
from fractions import Fraction
from collections import Counter, deque
from datetime import datetime, timezone
import json, math, sys, tarfile, time, zipfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT / 'experiments/discovery/v06_catalogue_cost_server_001/remote'
OUT = ROOT / 'experiments/analysis/v06/catalogue_cost_audit_v06_001.json'
sys.dont_write_bytecode = True
sys.path.insert(0, str(REMOTE))
from cipheur.graph_features import FeatureRuleProgram, _FeatureState, graph_operation_library
from cipheur.model import Graph

started = time.perf_counter()
checks = Counter()
def verify(condition, category):
    checks[category] += 1
    if not condition:
        raise AssertionError(category)
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def digest(path): return sha256(Path(path).read_bytes()).hexdigest()
def canonical(v): return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
def exact(v):
    verify(type(v) in (int, float) and math.isfinite(v), 'finite_numeric')
    return Fraction(v)
def vectors_equal(a, b): return set(a) == set(b) and all(exact(a[k]) == exact(b[k]) for k in a)

archive = ROOT / 'experiments/runs/v06/catalogue_cost_server_v06_001.tar.gz'
verify(digest(archive) == 'dab90de26a486d11174ba10f06723c8c02ae277aa2907d643fe36909107ecc05', 'archive_SHA')
file_sha = {}
with tarfile.open(archive) as tar:
    seen = set()
    for member in tar:
        name = PurePosixPath(member.name)
        verify(not name.is_absolute() and '..' not in name.parts and '\\' not in member.name and not member.issym() and not member.islnk(), 'safe_archive_inventory')
        if member.isdir(): continue
        verify(member.isfile() and member.name not in seen, 'unique_regular_archive_member')
        seen.add(member.name)
        relative = '/'.join(name.parts[1:])
        data = tar.extractfile(member).read()
        file_sha[relative] = sha256(data).hexdigest()
        verify((REMOTE / relative).read_bytes() == data, 'archive_extraction_byte_parity')
verify(len(file_sha) == 29, 'archive_file_count')
protocol = read(REMOTE / 'study/protocol.json')
freeze = read(REMOTE / 'study/freeze_receipt.json')
cap = read(REMOTE / 'source_capsule_receipt.json')
verify(digest(REMOTE / 'source_capsule.zip') == cap['source_capsule_sha256'] == '2c19af4c639926e457b9bcdbf5c2eb5dd9b23c23055af748da5217003c7a64f6', 'capsule_SHA')
verify(digest(REMOTE / 'study/protocol.json') == freeze['protocol_sha256'] == 'b0e9949454d0b4f6bc0516e5b9fdce27b660cc7e4417e766549e48b33c9851ca', 'protocol_SHA')
with zipfile.ZipFile(REMOTE / 'source_capsule.zip') as z:
    verify(set(z.namelist()) == set(cap['member_sha256']), 'capsule_inventory')
    for name, value in cap['member_sha256'].items():
        verify(sha256(z.read(name)).hexdigest() == value == digest(REMOTE / name), 'capsule_source_input_SHA')
for name, value in protocol['source_sha256'].items():
    verify(digest(REMOTE / name) == value, 'frozen_runtime_SHA')
for name, value in freeze['input_sha256'].items():
    verify(digest(REMOTE / 'study' / name) == value, 'frozen_input_SHA')
verify(protocol['max_selected'] == 6 and protocol['max_rounds'] == 128 and protocol['max_master_subsets'] == 250000, 'budget_registration')
verify(protocol['typed_library_operations'] == len(graph_operation_library()) == 25, 'typed_library_operations')
complete = read(REMOTE / 'results/complete.json')
for key, path in [('feature_rows_sha256','feature_rows.jsonl'),('results_sha256','results.jsonl'),('execution_sha256','execution.json')]:
    verify(digest(REMOTE/'results'/path) == complete[key], 'complete_receipt_output_SHA')

entries = read(REMOTE / 'study/catalogue.json')['catalogue']
names = [e['name'] for e in entries]
index = {n:i for i,n in enumerate(names)}
verify(len(names) == len(set(names)) == 53 and names == sorted(names), 'canonical_catalogue_inventory')
for e in entries:
    verify(sha256(canonical(e['expression'])).hexdigest() == e['expression_sha256'] == e['name'][2:], 'canonical_expression_SHA')
evidence = read(REMOTE / 'study/training_evidence.json')
binding_saved = read(REMOTE / 'study/occurrence_bindings.json')
graphs, active, endpoints, bindings, requirements = {}, {}, {}, {}, []
labels = {r['id']:r for r in evidence['labels']}
verify(len(evidence['records']) == len(labels) == 120, 'TRAIN_record_count')
for r in sorted(evidence['records'], key=lambda r:r['id']):
    sid = r['id']; g = Graph.from_dict(r['graph'])
    verify(r['split'] == labels[sid]['split'] == 'train' and g.digest() == r['graph_digest'] == labels[sid]['graph_digest'], 'TRAIN_graph_label_binding')
    verify(g.feasible(r['fixed']) and not set(r['fixed']) & set(r['excluded']), 'fixed_excluded_feasibility')
    A = g.available(r['fixed'], r['excluded'])
    manual = set(g.nodes) - set(r['fixed']) - set(r['excluded'])
    for v in r['fixed']: manual -= g.adj[v]
    verify(A == manual, 'actual_F_X_boundary')
    strict = [q for q in labels[sid]['rows'] if q['difference']['status'] == 'strict']
    ends = sorted({q[k] for q in strict for k in ('a','b')})
    for v in ends:
        oid = sid+'|'+v
        verify(v in A and oid not in bindings, 'certified_occurrence_binding')
        bindings[oid] = {'state':sid,'node':v,'graph_digest':g.digest(),'fixed':sorted(r['fixed']),'excluded':sorted(r['excluded'])}
    for i,q in enumerate(strict):
        a,b = q['a'],q['b']; p=q['difference']['preferred']; n=b if p==a else a
        verify(p in (a,b) and a != b and b in g.adj[a], 'strict_arc_legal_adjacency')
        lo,hi=Fraction(q['difference']['lower_exact']),Fraction(q['difference']['upper_exact'])
        if p==b: lo,hi=-hi,-lo
        verify(0 < lo <= hi, 'saved_strict_enclosure_orientation')
        requirements.append({'preferred':sid+'|'+p,'other':sid+'|'+n,'state':sid,'query_index':i,'lower_exact':str(lo),'upper_exact':str(hi)})
    graphs[sid],active[sid],endpoints[sid]=g,A,ends
verify(bindings == binding_saved['bindings'] and requirements == binding_saved['requirements'], 'reconstructed_occurrence_requirement_identity')
verify(len(bindings)==864 and len(requirements)==594, 'full_evidence_frame')

features = {r['id']:r for r in rows(REMOTE / 'results/feature_rows.jsonl')}
verify(set(features) == {'base9',*names} and len(features)==54, 'feature_assignment_inventory')
costs = {}; primitive_totals=Counter()

def direct_value(e, node, g, A):
    """Independent, uncached value interpreter; no production evaluator calls."""
    args=[direct_value(x,node,g,A) for x in e.get('args',[])]
    op=e['op']
    if op=='root': return node
    if op=='available': return frozenset(A)
    if op=='neighbors': return frozenset(g.adj[args[0]] & A)
    if op=='singleton': return frozenset([args[0]]) if args[0] in A else frozenset()
    if op=='union': return args[0]|args[1]
    if op=='intersection': return args[0]&args[1]
    if op=='difference': return args[0]-args[1]
    if op=='count': return len(args[0])
    if op=='induced_edges':
        ns=sorted(args[0]); return frozenset((a,b) for i,a in enumerate(ns) for b in ns[i+1:] if b in g.adj[a])
    if op in ('sum_weights','max_weight'):
        ws=[g.nodes[v].weight for v in sorted(args[0])]
        return math.fsum(ws) if op=='sum_weights' else max(ws,default=0.0)
    if op=='weight': return g.nodes[args[0]].weight
    if op=='duration': return g.nodes[args[0]].end-g.nodes[args[0]].start
    if op=='const': return e['value']
    if op in ('greedy_independent_weight','clique_cover_weight'):
        left=set(args[0]); order=sorted(left,key=lambda v:(-g.nodes[v].weight,v)); terms=[]
        for v in order:
            if v not in left: continue
            if op=='greedy_independent_weight':
                terms.append(g.nodes[v].weight); left -= g.adj[v]|{v}
            else:
                clique=[v]; left.remove(v)
                for u in order:
                    if u in left and all(u in g.adj[q] for q in clique): clique.append(u);left.remove(u)
                terms.append(max(g.nodes[q].weight for q in clique))
        return math.fsum(terms)
    if op in ('edge_min_weight_sum','edge_weight_product_sum'):
        return math.fsum(min(g.nodes[a].weight,g.nodes[b].weight) if op=='edge_min_weight_sum' else g.nodes[a].weight*g.nodes[b].weight for a,b in sorted(args[0]))
    if op=='add': return args[0]+args[1]
    if op=='sub': return args[0]-args[1]
    if op=='mul': return args[0]*args[1]
    if op=='div': return args[0]/args[1]
    if op=='min': return min(args)
    if op=='max': return max(args)
    if op=='abs': return abs(args[0])
    raise AssertionError('unimplemented independently evaluated op')

feature_audit=[]
for entry in [None]+entries:
    name='base9' if entry is None else entry['name']; row=features[name]
    verify(row['completed'] and row['status']=='completed' and set(row['values'])==set(bindings), 'completed_full_feature_coverage')
    program=FeatureRuleProgram('audit',[] if entry is None else [{'name':name,'expression':entry['expression']}],'weight')
    expr=None if entry is None else program._expressions[0][1]
    meter={}; value_count=0
    for sid in sorted(graphs):
        g,A=graphs[sid],active[sid]
        for node in endpoints[sid]:
            oid=sid+'|'+node; state=_FeatureState(g,A,meter)
            value=state.feature_values(program,node) if entry is None else state.evaluate(expr,node)
            stored=row['values'][oid]
            if entry is None:
                N=g.adj[node]&A; direct={'weight':g.nodes[node].weight,'duration':g.nodes[node].end-g.nodes[node].start,'degree':len(N),'conflict_weight':math.fsum(g.nodes[v].weight for v in sorted(N)),'max_conflict_weight':max((g.nodes[v].weight for v in N),default=0.0),'compatible_weight':math.fsum(g.nodes[v].weight for v in sorted(A-N-{node})),'remaining_count':len(A),'station_gap':g.constraints.get('station_gap',g.constraints.get('ground_trans_time',0)),'satellite_gap':g.constraints.get('satellite_gap',g.constraints.get('satellite_change_time',0))}
                verify(vectors_equal(value,stored) and vectors_equal(direct,stored), 'base9_value_frozen_and_independent_replay')
                value_count += len(stored)
            else:
                direct=direct_value(entry['expression'],node,g,A)
                verify(exact(value)==exact(stored)==exact(direct), 'feature_value_frozen_and_independent_replay')
                value_count += 1
    work=meter.get('feature_work',0)
    verify(work==row['measured_standalone_work']==row['positive_additive_cost'] and work>0, 'exact_standalone_work_replay')
    verify(meter['feature_primitives']==row['meter']['feature_primitives'] and sum(meter['feature_primitives'].values())==work, 'primitive_breakdown_replay')
    primitive_totals.update(meter['feature_primitives'])
    if entry is not None: costs[name]=work
    feature_audit.append({'id':name,'catalogue_index':None if entry is None else index[name],'exact_value_count':value_count,'work':work,'CPU_seconds_server':row['CPU_seconds'],'wall_seconds_server':row['wall_seconds'],'primitive_work':meter['feature_primitives'],'values_sha256_canonical':sha256(canonical(row['values'])).hexdigest()})

base=features['base9']['values']; vals={n:features[n]['values'] for n in names}
def vector(oid, selected): return {**base[oid],**{n:vals[n][oid] for n in selected}}
def fullQ(selected):
    groups={};classes={}
    for oid in sorted(bindings):
        sig=tuple((k,exact(v)) for k,v in sorted(vector(oid,selected).items()))
        classes[oid]=groups.setdefault(sig,len(groups))
    adj=[set() for _ in groups];ind=[0]*len(groups);selfloops=0
    for r in requirements:
        a,b=classes[r['preferred']],classes[r['other']]
        selfloops += a==b
        if b not in adj[a]: adj[a].add(b);ind[b]+=1
    queue=deque(i for i,d in enumerate(ind) if d==0);removed=0
    while queue:
        a=queue.popleft();removed+=1
        for b in adj[a]:
            ind[b]-=1
            if not ind[b]: queue.append(b)
    return {'acyclic':removed==len(groups),'quotient_nodes':len(groups),'quotient_edges':sum(map(len,adj)),'self_loop_requirements':selfloops}
def qparity(independent, production):
    return independent['acyclic'] != production['contradictory'] and all(independent[k]==production[k] for k in ('quotient_nodes','quotient_edges','self_loop_requirements'))
plans={r['id']:r for r in protocol['catalogue_plans']}
results={r['id']:r for r in rows(REMOTE/'results/results.jsonl')}
verify(set(results)==set(plans), 'catalogue_assignment_inventory')
case_audit=[]
for cid in ('prefix_4','prefix_8','prefix_16','full_53'):
    row=results[cid];p=row['production'];plan=plans[cid];allowed=plan['names'];covers=[];wdetails=[]
    verify(row['completed'] and p['max_selected']==6, 'catalogue_assignment_returned')
    for i,w in enumerate(p['witnesses']):
        selected=w['separated_after_selected'];arcs=w['requirements'];joins=w['equality_joins']
        verify(len(arcs)==len(joins)>0 and i==w['id'], 'concrete_closed_walk')
        for j,(arc,join) in enumerate(zip(arcs,joins)):
            original=requirements[arc['requirement_index']]
            verify(all(arc[k]==original[k] for k in original), 'concrete_original_strict_arc')
            verify(join['negative']==arc['other'] and join['positive']==arcs[(j+1)%len(arcs)]['preferred'], 'concrete_cyclic_join_endpoints')
            v1,v2=vector(join['negative'],selected),vector(join['positive'],selected)
            verify(vectors_equal(v1,v2) and vectors_equal(v1,join['negative_vector']) and vectors_equal(v2,join['positive_vector']), 'exact_current_interface_join')
        cover=sorted(n for n in allowed if any(exact(vals[n][j['negative']]) != exact(vals[n][j['positive']]) for j in joins))
        verify(cover==w['separating_features'], 'necessary_cut_membership_all_features')
        covers.append(cover)
        verify(cover==row['audit']['cut_checks'][i]['separating_features'], 'server_cut_audit_parity')
        wdetails.append({'id':i,'kind':w['kind'],'arcs':arcs,'joins':[{'negative':j['negative'],'positive':j['positive']} for j in joins],'separating_indices':[index[n] for n in cover],'selected_before_indices':[index[n] for n in selected]})
    round_audit=[]
    for i,t in enumerate(p['rounds']):
        selected=t['selected_names'];q=fullQ(selected);cost=sum(costs[n] for n in selected)
        verify(t['cuts']==covers[:i+1] and all(set(selected)&set(c) for c in t['cuts']), 'all_accumulated_cuts_retained_and_hit')
        verify(len(selected)<=6 and cost==Fraction(t['cost_exact']), 'selected_K_and_exact_cost')
        verify(qparity(q,t['quotient']) and q==row['audit']['round_checks'][i]['full_quotient_verified'], 'entire594_round_quotient_parity')
        d=row['audit']['round_checks'][i]['independent_DP']
        verify(d['complete'] and d['feasible'] and Fraction(d['cost_exact'])==cost and len(d['selected_names'])<=6 and all(set(d['selected_names'])&set(c) for c in t['cuts']) and sum(costs[n] for n in d['selected_names'])==cost, 'saved_independent_DP_feasible_cost_receipt')
        round_audit.append({'round':i,'selected_indices':[index[n] for n in selected],'cost_exact':str(cost),'quotient':q,'server_DP_states':d['states'],'server_DP_complete':d['complete'],'master_subsets_cumulative':t['master_subsets_evaluated']})
    final=fullQ(p['selected_names']);verify(qparity(final,p['diagnosis']) and final==row['audit']['final_full_quotient'], 'entire594_final_quotient_parity')
    verify(sum(costs[n] for n in p['selected_names'])==Fraction(p['cost_exact']), 'final_exact_cost')
    unbreakable=None
    if cid!='full_53':
        w=p['witnesses'][-1]
        verify(p['reason']=='catalogue_cannot_separate_witness' and not w['separating_features'] and not p['optimal'] and not p['repaired'], 'retained_unresolved_no_empty_cut_relaxation')
        for j in w['equality_joins']:
            verify(vectors_equal(vector(j['negative'],allowed),vector(j['positive'],allowed)), 'unbreakable_cycle_even_all_catalogue_features')
        allQ=fullQ(allowed);verify(not allQ['acyclic'], 'full_prefix_still_cyclic')
        unbreakable={'all_catalogue_features_quotient':allQ,'last_witness_id':w['id'],'all_subsets_infeasible_by_preserved_concrete_walk':True,'scope':'even without K bound, this exact catalogue cannot split the surviving walk'}
        enumeration=row['audit']['exhaustive'];expected=sum(math.comb(len(allowed),k) for k in range(min(6,len(allowed))+1))
        verify(enumeration['complete'] and not enumeration['feasible'] and enumeration['subsets_enumerated']==enumeration['quotient_checks']==expected, 'saved_exhaustive_complete_inventory')
    else:
        verify(p['optimal'] and p['repaired'] and final['acyclic'] and row['status']=='resolved_additive_minimum', 'resolved_scope')
    case_audit.append({'id':cid,'catalogue_size':len(allowed),'execution_completed':row['completed'],'scientific_status_original':row['status'],'reason':p['reason'],'selected_indices':[index[n] for n in p['selected_names']],'current_subset_cost_exact':p['cost_exact'],'current_subset_is_acyclic':final['acyclic'],'rounds':len(p['rounds']),'witnesses':len(p['witnesses']),'master_subsets':p['master_subsets_evaluated'],'quotient_evaluations':p['quotient_evaluations'],'final_quotient':final,'production_CPU_seconds':row['production_CPU_seconds'],'production_wall_seconds':row['production_wall_seconds'],'including_server_audit_CPU_seconds':row['CPU_seconds'],'including_server_audit_wall_seconds':row['wall_seconds'],'server_DP_states_total':row['audit']['independent_DP_states_total'],'server_exhaustive_receipt':row['audit']['exhaustive'],'unbreakable_prefix_proof':unbreakable,'trace':round_audit,'witnesses_detail':wdetails})

# Verify an explicit lower-bound certificate. No DP, B&B, subset enumeration or
# any optimization is executed by this reviewer. For nonnegative y_j and each
# feature f, sum_{j:f in cut_j} y_j <= c_f implies every cut cover costs >=sum y.
full=results['full_53']['production']
dual={4:394682,6:799655,7:147167,8:29964}
dual_rows=[]
for name in names:
    load=sum(y for cut,y in dual.items() if name in full['witnesses'][cut]['separating_features'])
    verify(0<=load<=costs[name], 'exact_cut_dual_feature_inequality')
    dual_rows.append({'name':name,'index':index[name],'cost':costs[name],'dual_load':load,'slack':costs[name]-load})
lower=sum(dual.values())
verify(lower==Fraction(full['cost_exact'])==sum(costs[n] for n in full['selected_names']), 'independent_global_fixed_catalogue_lower_bound_matches_feasible_upper')
verify(all(set(full['selected_names'])&set(w['separating_features']) for w in full['witnesses']), 'dual_attaining_candidate_hits_every_cut')
baseQ=fullQ(())
process=read(REMOTE/'process_receipt.json')
output={'version':'v06_catalogue_cost_independent_audit_001','utc':datetime.now(timezone.utc).isoformat(),'elapsed_wall_seconds':time.perf_counter()-started,'passed':True,'errors':[],
 'scope':'Existing TRAIN server observations only; read-only frozen feature replay, independent uncached value interpreter, full quotient/walk/cut checks, saved DP/exhaustive receipt and algorithm review, exact non-optimization minimum-cost lower-bound certificate. No new optimization, oracle, R2 or TEST access.',
 'original_conditional_certificates':'Saved strictly positive exact enclosures/orientations and source bindings checked here; MWIS/oracle solves were not rerun. Original TRAIN certificates were independently audited before this study.',
 'not_executed':['minimum_cost_vector_refinement','independent_cut_master','exhaustive_refinement','solve_catalogue','audit_refinement','conditional oracle','scheduling policy','R2 file access','TEST file access'],
 'audit_helper_sha256':digest(__file__),'archive':{'path':str(archive.relative_to(ROOT)).replace('\\','/'),'sha256':digest(archive),'bytes':archive.stat().st_size,'file_count':len(file_sha),'all_member_sha256':file_sha},
 'capsule_sha256':cap['source_capsule_sha256'],'protocol_sha256':digest(REMOTE/'study/protocol.json'),'source_sha256':protocol['source_sha256'],'input_sha256':freeze['input_sha256'],
 'frame':{'TRAIN_states':len(graphs),'strict_requirements':len(requirements),'unique_endpoint_occurrences':len(bindings),'unit_weights_all':all(v.weight==1 for g in graphs.values() for v in g.nodes.values()),'graph_sizes':dict(Counter(len(g.nodes) for g in graphs.values())),'catalogue_size':len(names),'base_features':protocol['base_features'],'base9_quotient':baseQ},
 'checks':dict(checks),'check_count':sum(checks.values()),'feature_replay':feature_audit,'primitive_work_total_all54_assignments':dict(primitive_totals),
 'cases':case_audit,'fixed_catalogue_minimum_certificate':{'necessary_cut_weights_by_zero_based_id':{str(k):v for k,v in dual.items()},'exact_lower_bound':str(lower),'exact_acyclic_attaining_cost':full['cost_exact'],'all53_feature_dual_inequalities':dual_rows,'max_selected':6,'attaining_feature_count':len(full['selected_names']),'minimum_cost_independently_proved_without_rerunning_optimizer':True,'also_valid_without_K_for_this_fixed_catalogue':True,'scope':'positive additive standalone feature work over this fixed evidence and catalogue; not a uniqueness/minimum-cardinality/scalar-rule/runtime theorem'},
 'saved_independent_optimizer_review':{'DP_algorithm':'finite memoized recursion on uncovered-cut bitmask and remaining K; each chosen feature removes all its cuts, cannot be reselected; exact positive integer costs and lex tie; every saved round DP complete and cost/feasible subset agrees','DP_summary_not_full_proof_trace':True,'DP_recomputed_by_reviewer':False,'exhaustive_algorithm':'every combination cardinality 0..K; only cost-dominated fullQ tests skipped after a feasible best; all three infeasible cases saved quotient_checks equal full subset count','exhaustive_recomputed_by_reviewer':False,'independent_closure':'prefix impossibility proved directly by preserved closed walk even with all prefix features; full catalogue minimum proved by explicit exact dual certificate plus entire594 DAG'},
 'server_process_receipt':process,'assignment_receipt':complete,'selected_features':[{'index':index[n],'name':n,'expression':entries[index[n]]['expression'],'standalone_cost':costs[n],'share_of_minimum':costs[n]/lower,'original_metadata_sources':entries[index[n]]['original_metadata_sources']} for n in full['selected_names']]}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(output,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps({'passed':True,'checks':sum(checks.values()),'elapsed_wall_seconds':output['elapsed_wall_seconds'],'minimum':lower,'selected_indices':[index[n] for n in full['selected_names']],'baseQ':baseQ,'output':str(OUT)},ensure_ascii=True))
