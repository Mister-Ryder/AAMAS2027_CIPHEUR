"""Independent postfreeze R2/EoH audit; no production scheduler/oracle imported.

Rebuilds the prescribed bijections, all numeric strict predictions and quotient
obstructions, paired classifications, retained incumbents and patch proofs.
Saved wall/CPU/work remain execution receipts, not remeasured benchmarks.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
from fractions import Fraction
from hashlib import sha256
import json,math
from pathlib import Path,PurePosixPath
import sys,tarfile,time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.verify_matched_llm_v05 import BASE,FeatureView,boundary,canonical,normalized_program,quotient
from scripts.verify_public_alias_v05 import view,graph_digest,exact_vector,exact_alpha
from scripts.verify_synthesis_train_v06 import feasible,exact_value,score_lazy,interface

SALT='V06_RELABEL_ROBUSTNESS_20261004_001'
VARIANTS=['original']+[f'relabel_{i}' for i in range(5)]
KINDS={'R2':('v06_R2_heldout_results_server_002',27,162,11664),
       'EoH':('v06_EoH_heldout_results_server_001',4,24,1728)}
def digest(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def raw_hash(raw):return sha256(raw).hexdigest()

def transport(records,labels,index):
    """Separate typed isomorphism reconstruction; interval strings untouched."""
    ids=defaultdict(set)
    for r in records:ids[r['cluster']].update(c['id'] for c in r['graph']['contacts'])
    maps={cluster:{v:f'r{i:03d}' for i,v in enumerate(sorted(vertices,
        key=lambda v:(sha256(f'{SALT}|{cluster}|{index}|{v}'.encode()).digest(),v)))} for cluster,vertices in ids.items()}
    rs,ls=[],[]
    for old in records:
        r=deepcopy(old);m=maps[r['cluster']];g=r['graph']
        g['name']+=f'_relabel_{index}'
        for c in g['contacts']:c['id']=m[c['id']]
        g['edges']=[list(e) for e in sorted({tuple(sorted((m[a],m[b]))) for a,b in g['edges']})]
        r.update(original_graph_digest=old['graph_digest'],graph_digest=graph_digest(g),relabel_index=index,
                 fixed=[m[v] for v in old['fixed']],excluded=[m[v] for v in old['excluded']])
        for q in r['queries']:q['a'],q['b']=m[q['a']],m[q['b']]
        rs.append(r)
    rmap={r['id']:r for r in rs}
    for old in labels:
        l=deepcopy(old);m=maps[l['cluster']]
        l.update(original_graph_digest=old['graph_digest'],graph_digest=rmap[l['id']]['graph_digest'])
        for q in l['rows']:
            q['a'],q['b']=m[q['a']],m[q['b']];d=q['difference']
            for key in ('a','b','preferred'):
                if d.get(key) is not None:d[key]=m[d[key]]
            d['cancelled_components']=[sorted(m[v] for v in c) for c in d.get('cancelled_components',[])]
            for sides in d.get('unmatched',{}).values():
                for c in sides:
                    c['vertices']=sorted(m[v] for v in c['vertices'])
                    c['bound']['selected']=sorted(m[v] for v in c['bound'].get('selected',[]))
        ls.append(l)
    return rs,ls,maps

def pairing(query_checks):
    sides=defaultdict(dict)
    for q in query_checks:
        if q['pair'] is not None:
            k=(q['pair'],q['query_index'])
            if q['side'] in sides[k]:raise ValueError('Duplicate paired endpoint')
            sides[k][q['side']]=q
    rows=[]
    for (pair,index),s in sorted(sides.items()):
        if set(s)!={'left','right'}:raise ValueError('Incomplete original paired query')
        l,r=s['left'],s['right'];a,b=l['certificate_status'],r['certificate_status']
        if (l['a'],l['b'],l['cluster'])!=(r['a'],r['b'],r['cluster']):raise ValueError('Paired action/cluster alignment changed')
        if a==b=='strict':category='strict_preservation' if l['preferred']==r['preferred'] else 'strict_reversal';passed=l['passed'] and r['passed']
        elif a==b=='exact_tie':category='exact_tie_both';passed=None
        elif 'unknown' in (a,b):category='incomplete_interval';passed=None
        else:category='strict_to_tie' if a=='strict' else 'tie_to_strict';passed=None
        rows.append({'pair':pair,'cluster':l['cluster'],'query_index':index,'a':l['a'],'b':l['b'],'category':category,
            'pair_passed':passed,'left_passed':l['passed'],'right_passed':r['passed'],
            'left_preferred':l['preferred'],'right_preferred':r['preferred']})
    return rows

def robustness(kind,entries,rows):
    """Reconstruct saved summary from all six original assignments, with nulls."""
    summary=[]
    for entry in entries:
        observed={r['variant']:r for r in rows if r['id']==entry['id']}
        scores=[(observed[v].get('interface') or {}).get('strict_passed') for v in VARIANTS[1:]]
        totals=[(observed[v].get('interface') or {}).get('strict_total') for v in VARIANTS[1:]]
        available=all(s is not None for s in scores)
        r={'id':entry['id'],'identity':entry,'missing_baseline':entry.get('missing_baseline',False),
            'original_strict_passed':(observed['original'].get('interface') or {}).get('strict_passed'),
            'original_strict_total':(observed['original'].get('interface') or {}).get('strict_total'),
            'all5_relabel_strict_passed':scores,'all5_relabel_strict_total':totals,
            'mean_relabel_strict_passed':sum(scores)/5 if available else None,
            'worst_relabel_strict_passed':min(scores) if available else None}
        if kind=='R2':r.update(all5_fit_measurements_available=available,role_scope=observed['original']['role_scope'])
        else:
            qualities=[(observed[v].get('kernel_summary') or {}).get('macro_quality_exact') for v in VARIANTS]
            works=[(observed[v].get('kernel_summary') or {}).get('macro_work_exact') for v in VARIANTS]
            q5=[Fraction(q) for q in qualities[1:]] if all(q is not None for q in qualities[1:]) else None
            r.update(all6_variant_macro_quality_exact=qualities,all6_variant_macro_work_exact=works,
                mean_relabel_macro_quality_exact=str(sum(q5,Fraction())/5) if q5 is not None else None,
                worst_relabel_macro_quality_exact=str(min(q5)) if q5 is not None else None)
        summary.append(r)
    return summary

class Audit:
    def __init__(self):self.checks=Counter();self.errors=[];self.totals=Counter();self.exact={};self.priorities={}
    def check(self,condition,kind,where=''):
        self.checks[kind]+=1
        if not condition:self.errors.append({'kind':kind,'where':where})
    def witnesses(self,saved,vectors,requirements,where):
        self.check(bool(saved['structural_witnesses'])==saved['contradictory'],'explicit_obstruction_witness_presence',where)
        for w in saved['structural_witnesses']:
            arcs,joins=w['requirements'],w['equality_joins']
            self.check(bool(arcs) and len(arcs)==len(joins),'complete_cycle_witness',where)
            self.check(w['kind']==('self_loop' if len(arcs)==1 else 'directed_cycle'),'actual_cycle_witness_kind',where)
            for i,(arc,join) in enumerate(zip(arcs,joins)):
                self.check({k:arc[k] for k in requirements[arc['requirement_index']]}==requirements[arc['requirement_index']],
                    'actual_certified_cycle_arc',where)
                negative,positive=arc['other'],arcs[(i+1)%len(arcs)]['preferred']
                self.check(join['negative']==negative and join['positive']==positive and join['negative_vector']==vectors[negative]
                    and join['positive_vector']==vectors[positive] and exact_vector(vectors[negative])==exact_vector(vectors[positive]),
                    'exact_equality_join',where)
    def kernel(self,record,result,entry,cfg,where):
        nodes,_,adj=view(record['graph']);fixed,excluded=set(record['fixed']),set(record['excluded'])
        legal=boundary(nodes,adj,fixed,excluded);value=lambda selected:exact_value(nodes,selected)
        self.check(result['config']==cfg['repair_config'] and result['declared_seconds']==cfg['seconds']
            and result['deadline_clock']==cfg['clock'] and result['priority']==entry['priority'],'unchanged_kernel_caps_and_priority',where)
        self.check(result['feasible'] and result['incumbent_available'] and not result['fallback_used']
            and result['online_model_calls']==result['conditional_oracle_calls']==0 and not result['exact_optimum_claimed']
            and feasible(nodes,adj,result['selected'],fixed,excluded) and Fraction(result['value_exact'])==value(result['selected']),
            'retained_original_graph_exact_objective_boundary',where)
        self.check(result['completed']==(result['error'] is None),'ordinary_budget_stop_separate_from_error',where)
        incumbent,active=set(fixed),set(legal)-fixed
        for v in fixed:active-=adj[v]
        for step in result['initializer_trace']:
            chosen=min(active,key=lambda v:(-Fraction(nodes[v]['weight'])/max(1,len(adj[v]&active)),v))
            self.check(step['selected']==chosen and step['available']==len(active)
                and Fraction(step['score_exact'])==Fraction(nodes[chosen]['weight'])/max(1,len(adj[chosen]&active)),
                'every_common_degree_initializer_prefix',where)
            incumbent.add(chosen);active-={chosen}|adj[chosen]
        self.check(sorted(incumbent)==result['initial_selected'] and value(incumbent)==Fraction(result['initial_value_exact'])
            and (not result['initialization_complete'] or not active),'initial_incumbent_and_stop_scope',where)
        self.check(Fraction(result['starting_value_exact'])==value(fixed),'permanent_boundary_start',where)
        global_scores={v:Fraction(nodes[v]['weight'])/max(1,len(adj[v]&legal)) for v in legal}
        commits=expanded=0
        for p in result['patch_trace']:
            self.totals['saved_patch_traces']+=1;destroy=set(p['destroy']);outside=incumbent-destroy
            free=set(nodes)-outside-excluded
            for v in outside:free-=adj[v]
            replacement=set(p['local_selected'])
            self.check(destroy<=incumbent and not destroy&fixed and len(destroy)<=cfg['repair_config']['max_destroy']
                and p['target'] in legal-incumbent and adj[p['target']]&incumbent<=destroy
                and Fraction(p['incumbent_patch_exact'])==value(destroy),'legal_destroy_and_outside_commitment',where)
            self.check(feasible(nodes,adj,replacement) and Fraction(p['lower_exact'])==value(replacement)
                and value(replacement)>=value(destroy),'feasible_restricted_lower',where)
            if p['patch'] is None:
                self.check(p['stage']=='region_construction' and replacement==destroy and not p['committed']
                    and p['upper_exact'] is None and not p['restricted_exact'],'unconstructed_patch_not_fabricated',where)
            else:
                patch=set(p['patch']);keep=set(destroy)
                if len(keep)<cfg['repair_config']['max_patch_vertices']:keep.add(p['target'])
                extras=sorted(free-keep,key=lambda v:(-global_scores[v],v))
                expected=keep|set(extras[:cfg['repair_config']['max_patch_vertices']-len(keep)])
                self.check(patch==expected and destroy<=patch<=free and replacement<=patch and p['full_region_size']==len(free)
                    and p['restricted']==(patch!=free),'unchanged_exact_D_preserving_restriction',where)
                if p['root_upper_exact'] is None:
                    self.check(p['upper_exact'] is None and not p['restricted_exact'] and not p['root_clique_cover'],
                        'interrupted_root_bound_remains_unknown',where)
                else:
                    cover=p['root_clique_cover'];flat=[v for c in cover for v in c]
                    self.check(len(flat)==len(set(flat)) and set(flat)==patch
                        and all(c and all(b in adj[a] for i,a in enumerate(c) for b in c[i+1:]) for c in cover),
                        'root_clique_partition_proof',where)
                    upper=sum((max(Fraction(nodes[v]['weight']) for v in c) for c in cover),Fraction())
                    self.check(upper==Fraction(p['root_upper_exact']) and upper>=value(replacement),'sound_root_upper',where)
                    if p['restricted_exact']:
                        key=(record['graph_digest'],tuple(sorted(patch)))
                        if key not in self.exact:self.exact[key]=exact_alpha(nodes,adj,patch,max_states=1000000)
                        self.check(self.exact[key][0]==value(replacement)==Fraction(p['upper_exact']),
                            'independent_exact_restricted_optimum',where)
                    else:self.check(Fraction(p['upper_exact'])==upper,'interrupted_search_keeps_sound_bound',where)
                if p['priority_order']:
                    key=(entry['priority'],canonical(entry['program']),record['graph_digest'],tuple(sorted(patch)))
                    degree=sorted(patch,key=lambda v:(-Fraction(nodes[v]['weight'])/max(1,len(adj[v]&patch)),v))
                    if key not in self.priorities:
                        if entry['priority']=='degree':order=degree
                        else:
                            state=FeatureView(record['graph'],active=patch)
                            scores={v:score_lazy(entry['program'],state,v) for v in sorted(patch)}
                            order=sorted(patch,key=lambda v:(-scores[v],v))
                        self.priorities[key]=order
                    order=self.priorities[key]
                    self.check(p['priority_order']==order,'independent_complete_local_priority_order',where)
                    if p['common_degree_order']:self.check(p['common_degree_order']==degree,'common_degree_priority_order',where)
                    for g in p['greedy_passes']:
                        greedy_order=order if g['order']=='priority' else degree
                        remaining,taken,attainable=set(patch),set(),{Fraction()}
                        for v in greedy_order:
                            if v in remaining:taken.add(v);remaining-={v}|adj[v]
                            attainable.add(value(taken))
                        self.check(Fraction(g['value_exact']) in attainable
                            and (not g['complete'] or Fraction(g['value_exact'])==value(taken)),
                            'local_greedy_full_or_feasible_prefix',where)
            gain=value(replacement)-value(destroy)
            self.check(Fraction(p['gain_exact'])==gain and p['committed']==(gain>0),'strict_positive_commit',where)
            if p['committed']:
                updated=outside|replacement
                self.check(feasible(nodes,adj,updated,fixed,excluded) and value(updated)>value(incumbent),
                    'monotone_global_feasible_commit',where)
                incumbent=updated;commits+=1
            self.check(0<=p['search_nodes']<=cfg['repair_config']['node_budget_per_patch'],'per_patch_node_cap',where)
            expanded+=p['search_nodes']
        self.check(sorted(incumbent)==result['selected'] and commits==result['improvements']
            and len(result['patch_trace'])==result['patches_attempted']<=cfg['repair_config']['max_patches'],'every_patch_replay_final_identity',where)
        meter=result['meter']
        self.check(expanded<=meter['search_nodes']<=cfg['repair_config']['max_search_nodes'],'global_charged_search_node_cap',where)
        for name in ('feature','repair'):
            work,parts=meter[name+'_work'],meter[name+'_primitives']
            self.check(type(work)is int and work>=0 and all(type(v)is int and v>=0 for v in parts.values())
                and sum(parts.values())<=work and (result['global_budget_exhausted'] or sum(parts.values())==work),
                'charged_primitive_breakdown_with_interrupted_tick',where)
        self.check(all(math.isfinite(result[k]) and result[k]>=0 for k in ('wall_seconds','cpu_seconds')),
            'saved_actual_nonnegative_times_not_remeasured',where)
        self.totals['verified_kernel_assignments']+=1

def audit(kind,archive,expected_sha,out):
    start=time.perf_counter();a=Audit();archive,out=Path(archive),Path(out)
    if out.exists():raise ValueError('Preserve every independent audit')
    stem,nident,assigned,nstates=KINDS[kind]
    if digest(archive)!=expected_sha:raise ValueError('Actual server archive byte binding failed')
    with tarfile.open(archive,'r:gz') as tar:
        members={}
        for m in tar.getmembers():
            if '..' in PurePosixPath(m.name).parts or m.name.startswith('/') or not (m.isdir() or m.isfile()):raise ValueError('Unsafe result member')
            if m.isfile():
                if m.name in members:raise ValueError('Duplicate result archive member')
                members[m.name]=tar.extractfile(m).read()
    read=lambda name:json.loads(members[name])
    freeze=read('registration/freeze_receipt.json');proto=read('registration/protocol.json')
    queue=json.loads((ROOT/'experiments/discovery/v06_test_release_002/sequential_cloud_queue_plan.json').read_bytes())
    binding=next(q for q in queue['assays'] if q['name']==stem)
    a.check(raw_hash(members['registration/freeze_receipt.json'])==binding['freeze_sha256'],
        'independently_pinned_original_prepared_registration')
    for name,h in freeze['artifact_sha256'].items():a.check(raw_hash(members['registration/'+name])==h,'immutable_prepared_artifact',name)
    for name,h in proto['source_sha256'].items():
        a.check(raw_hash(members['registration/source_snapshot/'+name])==h==digest(ROOT/'cipheur'/name),
            'unchanged_registered_scientific_source',name)
    a.check(len(proto['entries'])==nident and proto['variants']==VARIANTS and proto['requested_state_assignments']==nstates,
        'all_requested_frozen_roles_and_variants')
    root=read('registration/root_release.json');execution=read(stem+'/execution.json');complete=read(stem+'/complete.json')
    a.check(raw_hash(members['registration/root_release.json'])==proto['root_release_sha256']==execution['root_release_sha256'],
        'executed_exact_original_root_release')
    a.check(proto['root_release_sha256']==binding['root_release_sha256'] and execution['registration_sha256']==
        (raw_hash(members['registration/protocol.json']) if kind=='R2' else binding['freeze_sha256'])
        and execution['workers']==proto['workers']==8 and execution['assignments']==assigned
        and execution['requested_state_assignments']==nstates and execution['source_sha256']==proto['source_sha256'],
        'execution_source_registration_workers_and_frame_binding')
    for field in (('selection_sha256','controls_selection_sha256','test_certificate_sha256') if kind=='R2' else
                  ('EoH_selection_sha256','R2_selection_sha256','R2_test_certificate_sha256')):
        a.check(execution[field]==proto[field],'execution_selection_and_certificate_binding',field)
    a.check(execution['selection_performed'] is False and execution['extra_oracle_calls']==0 and execution['split']=='test',
        'no_TEST_selection_or_extra_queries')
    records=read('registration/test_inputs.json')['records'];labels=read('registration/test_certificates.json')['labels']
    cert_audit=json.loads((ROOT/'experiments/analysis/v06/evidence_TEST_audit_v06_002.json').read_bytes())
    a.check(cert_audit['errors']==0 and cert_audit['root_release_sha256']=='8e69f14051ce731332b11aaefa2f60c2ace38780e4f20dfb9429974555ca83d1',
        'prior_independent_TEST_certificate_proof')
    with tarfile.open(ROOT/'experiments/runs/v06/v06_evidence_test_002.tar.gz','r:gz') as tar:
        original=tar.extractfile('v06_evidence_test_002/results.jsonl').read()
        a.check(raw_hash(original)==cert_audit['results_sha256'],'prior_certified_result_bytes')
        a.check(labels==[json.loads(line) for line in original.splitlines() if line],'all_original_TEST_labels_byte_payload')
        data=json.load(tar.extractfile('v06_evidence_test_002/data.json'))
    a.check(records==[r for r in data['records'] if r['split']=='test'] and len(records)==72,'all_original_TEST_input_payloads')
    variants={'original':(records,labels)};planned=read('registration/relabel_inventory.json')
    for i,p in enumerate(planned):
        rs,ls,mapping=transport(records,labels,i)
        a.check(p['index']==i and p['variant']==f'relabel_{i}' and p['mappings']==mapping
            and p['graph_digests']=={r['id']:r['graph_digest'] for r in rs},'independent_all_five_paired_bijections',str(i))
        variants[f'relabel_{i}']=(rs,ls)
    entries={e['id']:e for e in proto['entries']};seen=set();interfaces={};summaries=[];statuses=Counter();all_rows=[]
    raw_rows=members[stem+'/results.jsonl']
    for line in raw_rows.splitlines():
        row=json.loads(line);key=(row['id'],row['variant']);where='|'.join(key)
        all_rows.append(row)
        a.check(key not in seen and key[0] in entries and key[1] in variants,'assigned_identity_variant_once',where);seen.add(key)
        entry=entries[row['id']];a.check(row['identity']==entry and row['split']=='test','exact_frozen_programme_identity',where)
        a.check(row['selection_performed'] is False and row['extra_oracle_calls']==0,'each_assignment_no_selection_or_oracle',where)
        rs,ls=variants[row['variant']];rmap={r['id']:r for r in rs};lmap={l['id']:l for l in ls}
        if row.get('assignment_status')=='worker_error':
            a.check(row.get('worker_error_type') is not None and 'worker_error' in row and row['kernel_rows']==[],
                'explicit_worker_failure_retains_unmeasured_requested_states',where)
            a.check(row.get('interface') is None and row.get('paired_checks') is None and row.get('kernel_summary') is None,
                'worker_error_has_no_fabricated_measurement',where)
            a.totals['worker_failed_state_assignments']+=72
            summaries.append({'id':row['id'],'variant':row['variant'],'worker_error':True,
                'verified_incumbents':0,'normal_completed':0,'unmeasured_requested_states':72})
            continue
        if entry.get('missing_baseline'):
            a.check(row.get('interface') is None and row.get('kernel_summary') is None and len(row['kernel_rows'])==72
                and all(q.get('result') is None for q in row['kernel_rows']),'null_identity_no_fallback_measurement',where)
            a.check({q['id'] for q in row['kernel_rows']}==set(rmap) and all(q['family']==rmap[q['id']]['family']
                and q['cluster']==rmap[q['id']]['cluster'] and q['split']=='test' and q['missing_baseline'] for q in row['kernel_rows'])
                and row['paired_checks'] is None and row['actual_cpu_seconds'] is None and row['actual_wall_seconds'] is None
                and row['assignment_status']=='missing_quality_comparator','complete_missing_identity_state_frame_and_null_times',where)
            a.check(row['kernel_coverage']=={'assigned_states':72,'returned_states':72,'missing_states':72,'normal_completed':0,
                'verified_incumbents':0,'errors':0,'normal_budget_stops':0},'missing_identity_coverage_not_error_or_measurement',where)
            summaries.append({'id':row['id'],'variant':row['variant'],'missing':True});continue
        program=normalized_program(entry['program']);ik=(canonical(program),row['variant'])
        if row.get('interface') is not None:
            if ik not in interfaces:interfaces[ik]=interface(program,rs,lmap)
            ref,vectors,declared,requirements=interfaces[ik];saved=row['interface']
            for k in ('demanded_features','strict_total','strict_passed','alias_strict_total','alias_strict_passed','full_observed_consistency'):
                a.check(saved[k]==ref[k],'independent_actual_interface_fit',where+':'+k)
            a.check([{k:q[k] for k in r} for q,r in zip(saved['strict_checks'],ref['strict_checks'])]==ref['strict_checks']
                and len(saved['strict_checks'])==len(ref['strict_checks']),'all_independent_strict_numeric_predictions',where)
            for name,vv in (('quotient',vectors),('declared_quotient',declared)):
                a.check(all(saved[name][k]==ref[name][k] for k in ref[name]),'complete_independent_quotient',where+':'+name)
                a.witnesses(saved[name],vv,requirements,where+':'+name)
            for q in ref['strict_checks']:
                p=q['preferred'];n=q['b'] if p==q['a'] else q['a'];prefix=q['state']+'|'
                base=lambda v:{k:vectors[prefix+v][k] for k in BASE}
                a.check(q['actual_base_alias']==(exact_vector(base(p))==exact_vector(base(n))),
                    'independent_actual_base_signature_alias',where)
            expected_queries=[];strict_iter=iter(ref['strict_checks'])
            for r in sorted(rs,key=lambda r:r['id']):
                for index,q in enumerate(lmap[r['id']]['rows']):
                    d=q['difference'];expected={'state':r['id'],'split':'test','cluster':r['cluster'],'family':r['family'],
                        'pair':r.get('pair'),'side':r.get('side'),'query_index':index,'a':q['a'],'b':q['b'],
                        'query_kind':q['kind'],'certificate_status':d['status'],'preferred':d['preferred'],
                        'lower_exact':d['lower_exact'],'upper_exact':d['upper_exact'],'passed':None,'score_a':None,'score_b':None}
                    if d['status']=='strict':
                        prediction=next(strict_iter);p=d['preferred'];n=q['b'] if p==q['a'] else q['a']
                        expected.update(prediction,score_a=prediction['score_preferred'] if q['a']==p else prediction['score_other'],
                            score_b=prediction['score_preferred'] if q['b']==p else prediction['score_other'],
                            demanded_feature_alias=exact_vector(vectors[r['id']+'|'+p])==exact_vector(vectors[r['id']+'|'+n]))
                    expected_queries.append(expected)
            a.check(saved['query_checks']==expected_queries,'all_strict_tied_unknown_query_payloads',where)
            a.check(row['paired_checks']==pairing(expected_queries),'all_paired_reversal_preservation_and_ties',where)
            a.check(saved['certificate_status']==dict(Counter(q['certificate_status'] for q in expected_queries))
                and saved['planned_queries']==len(expected_queries),'complete_certificate_status_counts',where)
            a.check(saved['quota_shortfalls']==sum(q['shortfall'] for r in rs for q in r['quota'].values()),
                'all_original_query_quota_shortfalls',where)
        else:a.check('interface_error' in row or 'worker_error' in row,'explicit_absent_interface_reason',where)
        kr=row['kernel_rows'];a.check(len(kr)==72 and {q['id'] for q in kr}==set(rmap),'all_assigned_original_state_receipts',where)
        fq,fw=defaultdict(list),defaultdict(list);verified=normal=errors=budget=0;local_status=Counter()
        for q in kr:
            r=rmap[q['id']];a.check(q['family']==r['family'] and q['cluster']==r['cluster'] and q['split']=='test','state_cluster_family_identity',where)
            result=q.get('result')
            if result is None:
                a.check('error' in q or q.get('missing_baseline'),'explicit_absent_kernel_result',where);errors+=1
                local_status['worker_or_validation_error']+=1;continue
            a.kernel(r,result,entry,proto['kernel_config'],where+'|'+r['id']);verified+=1;normal+=int(result['completed']);errors+=int(not result['completed'])
            statuses[result['status']]+=1;denom=sum((Fraction(c['weight']) for c in r['graph']['contacts']),Fraction())
            local_status[result['status']]+=1;budget+=int(result['completed'] and result['budget_exhausted'])
            fq[r['family']].append(Fraction(result['value_exact'])/denom if denom else Fraction(1))
            fw[r['family']].append(result['meter']['feature_work']+result['meter']['repair_work'])
        cov=row['kernel_coverage']
        a.check(cov['assigned_states']==cov['returned_states']==72 and cov['verified_incumbents']==verified
            and cov['normal_completed']==normal and cov['errors']==errors and cov['normal_budget_stops']==budget
            and cov['status']==dict(local_status),'complete_feasible_error_coverage',where)
        if verified==72:
            means={f:sum(values,Fraction())/len(values) for f,values in fq.items()};works={f:Fraction(sum(values),len(values)) for f,values in fw.items()}
            expected={'macro_quality_exact':str(sum(means.values(),Fraction())/len(means)),'macro_work_exact':str(sum(works.values(),Fraction())/len(works)),
                'family_reward_over_total_weight':{f:str(v) for f,v in means.items()},'family_work':{f:str(v) for f,v in works.items()}}
            a.check(row['kernel_summary']==expected,'exact_family_macro_reward_and_work',where)
        else:a.check(row.get('kernel_summary') is None,'incomplete_macro_not_fabricated',where)
        summaries.append({'id':row['id'],'variant':row['variant'],'strict_passed':(row.get('interface') or {}).get('strict_passed'),
            'strict_total':(row.get('interface') or {}).get('strict_total'),'alias_passed':(row.get('interface') or {}).get('alias_strict_passed'),
            'quotient_contradictory':(row.get('interface') or {}).get('quotient',{}).get('contradictory'),
            'verified_incumbents':verified,'normal_completed':normal,'kernel_errors':errors,'kernel_summary':row.get('kernel_summary')})
    a.check(seen=={(e,v) for e in entries for v in VARIANTS} and len(seen)==assigned,'complete_requested_identity_variant_frame')
    a.check(complete['execution_complete'] is True and complete['assigned']==complete['returned_assignments']==assigned
        and complete['requested_state_assignments']==nstates and complete['results_sha256']==raw_hash(raw_rows),
        'terminal_complete_marker_and_original_result_bytes')
    measured=[r for r in all_rows if r['assignment_status']!='missing_quality_comparator']
    a.check(complete['missing_assignments']==sum(r['assignment_status']=='missing_quality_comparator' for r in all_rows)
        and complete['worker_errors']==sum('worker_error' in r for r in all_rows)
        and complete['interface_errors']==sum('interface_error' in r for r in measured)
        and complete['kernel_errors']==sum(r.get('kernel_coverage',{}).get('errors',72) for r in measured)
        and complete['root_release_sha256']==proto['root_release_sha256'] and complete['selection_performed'] is False
        and complete['extra_oracle_calls']==0 and complete['no_fallback'], 'terminal_all_failure_and_missing_counts')
    a.check(read(stem+'/robustness_summary.json')==robustness(kind,proto['entries'],all_rows),
        'all_original_five_relabel_mean_worst_and_null_summary')
    report={'version':'v06_independent_'+kind+'_heldout_result_audit_001','checked_utc':datetime.now(timezone.utc).isoformat(),
        'archive_sha256':expected_sha,'kind':kind,'checks':sum(a.checks.values()),'checks_by_kind':dict(a.checks),
        'errors':len(a.errors),'error_records':a.errors,'totals':dict(a.totals),'executed_status_counts':dict(statuses),
        'verified_identity_variant_count':len(seen),'requested_state_assignments':nstates,'programme_summaries':summaries,
        'independent_exact_patch_queries':len(a.exact),'independent_exact_verifier_states':sum(x[1] for x in a.exact.values()),
        'audit_script_sha256':digest(__file__),'independent_helper_sha256':{n:digest(ROOT/n) for n in
            ('scripts/verify_matched_llm_v05.py','scripts/verify_public_alias_v05.py','scripts/verify_synthesis_train_v06.py')},
        'verification_wall_seconds':time.perf_counter()-start,'production_scheduler_or_oracle_calls':0,'programme_selection':False,
        'scope':'Separate root-executed independent numeric/graph/trace reconstruction; actual execution timings/work retained, error incumbents remain diagnostics, no new experimental rollout or TEST tuning.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'kind':kind,'checks':report['checks'],'errors':report['errors'],'audit_sha256':digest(out)}))
    if a.errors:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=KINDS,required=True)
    for name in ('archive','archive-sha256','out'):p.add_argument('--'+name,required=True)
    args=vars(p.parse_args());args['expected_sha']=args.pop('archive_sha256');audit(**args)
