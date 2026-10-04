"""Independent original72 frozen TEST certificate verifier; never a production oracle.

Reuses only the unchanged independent graph/recurrence helpers and exact
certificate-comparison logic from the separately audited TRAIN verifier.
No production scheduling/oracle module, author, selector or assessor is imported.
"""
from __future__ import annotations
import argparse,ast,json,math,sys,time,zipfile,tarfile
from collections import Counter,defaultdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.verify_evidence_v06 import rebuild_inventory
from scripts.verify_public_alias_v05 import read_members,view,graph_digest,base9,exact_vector,components,exact_alpha,VerificationLimit

def digest(data):return sha256(data).hexdigest()
def audit(archive,archive_sha256,capsule,capsule_receipt,release,release_sha256,out,max_states=1000000):
    started=time.perf_counter()
    checks,errors=Counter(),[]
    def require(ok,kind,where):
        checks[kind]+=1
        if not ok:errors.append({'kind':kind,'where':where})
    archive,capsule,capsule_receipt,release,out=map(Path,(archive,capsule,capsule_receipt,release,out))
    if out.exists():raise ValueError('Never replace an independent verification receipt')
    root=json.loads(release.read_bytes());receipt=json.loads(capsule_receipt.read_bytes())
    require(digest(release.read_bytes())==release_sha256==receipt['root_release_sha256'],'prior_main_root_byte_binding','release')
    require(root['version']=='v06_R2_root_TEST_release_002' and root['allow_TEST'] is True and root['before_any_TEST_labels_or_performance'] is True and root['published_EoH_all32_and4_seed_fitness_frozen_before_TEST'] is True and root['selection_split']=='train' and root['test_accessed'] is False and len(root['programs'])==4,'complete_prior_R2_EoH_release','release')
    require(digest(archive.read_bytes())==archive_sha256,'raw_server_archive_binding','archive')
    require(digest(capsule.read_bytes())==receipt['source_zip_sha256'] and receipt['before_any_TEST_certificate_query'] is True,'prequery_source_capsule_binding','capsule')
    with zipfile.ZipFile(capsule) as z:
        require(set(z.namelist())==set(receipt['files_sha256']) and len(z.namelist())==len(receipt['files_sha256']),'complete_source_capsule_inventory','capsule')
        for name,pin in receipt['files_sha256'].items():require(digest(z.read(name))==pin,'capsule_member_bytes',name)
        require(digest(z.read('scripts/run_evidence_test_server_v06.py'))==root['TEST_certificate_execution_wrapper_sha256'],'released_wrapper_bytes','wrapper')
        oracle=ast.parse(z.read('cipheur/relevance_synthesis_v04.py'))
        cls=next(n for n in oracle.body if isinstance(n,ast.ClassDef) and n.name=='CancelledCompletionOracle')
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='difference')
        epsilon=fn.args.defaults[-1].value
        require(epsilon==1e-8,'unchanged_source_label_epsilon','oracle')
    with tarfile.open(archive,'r:gz') as t:
        for m in t:
            require(not m.issym() and not m.islnk() and not m.name.startswith('/') and '..' not in Path(m.name).parts,'safe_archive_member',m.name)
    names=('data.json','protocol.json','freeze_receipt.json','results.jsonl','complete.json','execution.json','root_release.json','execution_plan.json','host_receipt.json','launch_receipt.json','server_execution_receipt.json')
    raw=read_members(archive,names)
    data,protocol,freeze=(json.loads(raw[n]) for n in ('data.json','protocol.json','freeze_receipt.json'))
    for name,field in [('data.json','original_data_sha256'),('protocol.json','original_query_protocol_sha256'),('freeze_receipt.json','original_evidence_freeze_sha256')]:require(digest(raw[name])==root[field],'root_frozen_original_input',name)
    require(raw['root_release.json']==release.read_bytes(),'executed_exact_root_bytes','execution')
    execution,complete,plan,host,launch,server=(json.loads(raw[n]) for n in ('execution.json','complete.json','execution_plan.json','host_receipt.json','launch_receipt.json','server_execution_receipt.json'))
    require(execution['split']==complete['split']==plan['split']=='test' and execution['programme_freeze_sha256']==complete['programme_freeze_sha256']==plan['programme_freeze_sha256']==release_sha256,'TEST_programme_freeze_is_main_root_hash','execution')
    require(execution['source_sha256']==freeze['source_sha256'] and freeze['before_any_oracle_query'] is True and protocol['before_any_oracle_query'] is True,'original_semantic_source_and_query_freeze','execution')
    for name,pin in freeze['source_sha256'].items():require(receipt['files_sha256'].get('cipheur/'+name)==pin,'executed_frozen_source_closure',name)
    require(plan['before_any_TEST_certificate_query'] is True and host['before_any_TEST_certificate_query'] is True and launch['timestamp_unix']>=host['timestamp_unix'] and plan['workers']==host['workers']==execution['workers']==8,'prequery_plan_host_launch','execution')
    require(server['exit_code']==0 and server['whole_job_guard_triggered'] is False and server['query_retries']==plan['query_retries']==0 and server['original_complete_sha256']==digest(raw['complete.json']) and server['original_results_sha256']==digest(raw['results.jsonl']),'retained_zero_retry_server_execution','execution')
    _,states=rebuild_inventory(data['records'],protocol,require)
    results=[json.loads(line) for line in raw['results.jsonl'].splitlines() if line]
    require(len(states)==len(results)==len({r['id'] for r in results})==72 and {r['id'] for r in results}=={r['id'] for r in states},'all_original72_TEST_states','results')
    by_id = {r["id"]: r for r in results}
    exact_cache, exact_states, unverified = {}, 0, []
    counts, summaries, paired = Counter(), defaultdict(Counter), defaultdict(dict)
    strict_details = []
    def optimum(identity, nodes, adj, part):
        nonlocal exact_states
        key = identity, tuple(sorted(part))
        if key not in exact_cache:
            try:
                value, spent = exact_alpha(nodes, adj, key[1], max_states)
                exact_cache[key] = value
                exact_states += spent
            except VerificationLimit:
                exact_cache[key] = None
                unverified.append({"state": identity, "component": list(key[1])})
        return exact_cache[key]

    for index, record in enumerate(sorted(states, key=lambda r: r["id"])):
        ident, result = record["id"], by_id[record["id"]]
        graph = record["graph"]
        nodes, edges, adj = view(graph)
        require(len(nodes) <= 32 and all(c["weight"] == 1 for c in nodes.values())
                and record["fixed"] == record["excluded"] == [], "small_unit_empty_boundary", ident)
        require(result["graph_digest"] == record["graph_digest"] == graph_digest(graph)
                and result["split"] == "test" and result["family"] == record["family"]
                and result["cluster"] == record["cluster"] and result["quota"] == record["quota"],
                "result_original_state_quota_identity", ident)
        require(len(result["rows"]) == len(record["queries"]), "all_prescheduled_queries_retained", ident)
        meter = result["oracle_budget"]
        require(0 <= meter["calls"] <= 1024 and 0 <= meter["expanded_nodes"] <= 2000000
                and meter["max_nodes"] == 2000000 and meter["max_calls"] == 1024,
                "executed_state_budget_receipt", ident)
        for field in ("elapsed_seconds", "solve_elapsed_seconds"):
            require(math.isfinite(meter[field]) and meter[field] >= 0,
                    "recorded_nonnegative_oracle_time", ident + ":" + field)
        unique_bounds = {}
        for qindex, (query, row) in enumerate(zip(record["queries"], result["rows"])):
            where = ident + ":" + str(qindex)
            a, b, difference = query["a"], query["b"], row["difference"]
            require(all(row[k] == query[k] for k in query) and (a, b) in edges
                    and a != b and difference["a"] == a and difference["b"] == b,
                    "frozen_competing_feasible_query_payload", where)
            alias = exact_vector(base9(graph, nodes, adj, a)) == exact_vector(base9(graph, nodes, adj, b))
            side_index = 0 if not record["paired"] or record["side"] == "left" else 1
            require(alias == query["base_alias_by_side"][side_index]
                    and query["kind"] == ("alias" if any(query["base_alias_by_side"]) else "control"),
                    "independent_per_side_alias_semantics", where)
            pa, pb = components(adj, nodes.keys() - adj[a] - {a}), components(adj, nodes.keys() - adj[b] - {b})
            require(set(map(tuple, difference["cancelled_components"])) == pa & pb,
                    "exact_common_component_cancellation", where)
            partitions, side_bounds = {"a": pa-pb, "b": pb-pa}, {}
            for side in ("a", "b"):
                exported = difference["unmatched"][side]
                require(len(exported) == len(partitions[side])
                        and set(tuple(p["vertices"]) for p in exported) == partitions[side],
                        "complete_unmatched_component_partition", where + side)
                for component in exported:
                    part, bound = tuple(component["vertices"]), component["bound"]
                    lo, hi = Fraction(bound["lower_exact"]), Fraction(bound["upper_exact"])
                    chosen = bound["selected"]
                    require(len(chosen) == len(set(chosen)) and set(chosen) <= set(part)
                            and not any(adj[v] & set(chosen) for v in chosen),
                            "component_lower_witness_feasibility", where)
                    require(sum((Fraction(nodes[v]["weight"]) for v in chosen), Fraction()) == lo
                            and 0 <= lo <= hi <= len(part) and bound["exact"] == (lo == hi),
                            "component_exact_reward_interval_flag", where)
                    value = optimum(ident, nodes, adj, part)
                    require(value is not None and lo <= value <= hi,
                            "independent_component_optimum_enclosed", where)
                    require(0 <= bound["expanded"] <= 50000, "per_component_expansion_ceiling", where)
                    if part in unique_bounds:
                        require(bound == unique_bounds[part], "within_state_bound_cache_identity", where)
                    unique_bounds[part] = bound
                    side_bounds[side, part] = lo, hi
            forced = Fraction(nodes[a]["weight"]) - Fraction(nodes[b]["weight"])
            lower = forced + sum((side_bounds["a", p][0] for p in partitions["a"]), Fraction())
            lower -= sum((side_bounds["b", p][1] for p in partitions["b"]), Fraction())
            upper = forced + sum((side_bounds["a", p][1] for p in partitions["a"]), Fraction())
            upper -= sum((side_bounds["b", p][0] for p in partitions["b"]), Fraction())
            require(lower == Fraction(difference["lower_exact"]) and upper == Fraction(difference["upper_exact"])
                    and difference["forced_weight_difference_exact"] == str(forced),
                    "exact_cancelled_signed_interval_arithmetic", where)
            require(Fraction(difference["lower"]) <= lower <= upper <= Fraction(difference["upper"])
                    and difference["exact"] == (lower == upper),
                    "outward_float_enclosure_and_exact_flag", where)
            full_a = [optimum(ident, nodes, adj, p) for p in pa]
            full_b = [optimum(ident, nodes, adj, p) for p in pb]
            if all(v is not None for v in full_a + full_b):
                truth = forced + sum(full_a, Fraction()) - sum(full_b, Fraction())
                require(lower <= truth <= upper, "independent_full_conditional_value_difference", where)
            else:
                truth = None
                require(False, "independent_full_conditional_unverified", where)
            preferred = a if lower > Fraction(epsilon) else b if upper < -Fraction(epsilon) else None
            status = "strict" if preferred is not None else "exact_tie" if lower == upper == 0 else "unknown"
            require(difference["preferred"] == preferred and difference["status"] == status,
                    "independent_strict_tie_unknown_sign", where)
            if preferred:
                require(truth is not None and (truth > 0 if preferred == a else truth < 0),
                        "strict_label_independent_truth_sign", where)
                strict_details.append({"id": ident, "a": a, "b": b, "kind": query["kind"],
                    "preferred": preferred, "delta_exact": str(truth), "per_side_alias": alias,
                    "family": record["family"], "cluster": record["cluster"]})
            if status == "exact_tie":
                require(truth == 0, "exact_tie_independent_truth", where)
            counts[status] += 1
            summaries[record["family"]][status] += 1
            summaries[record["family"]][query["kind"] + "_queries"] += 1
            summaries[record["family"]]["actual_side_alias_queries"] += alias
            summaries[record["family"]]["strict_actual_side_alias"] += alias and status == "strict"
            counts["actual_side_alias_queries"] += alias
            counts["strict_actual_side_alias"] += alias and status == "strict"
            if record["paired"]:
                paired[record["pair"]][record["side"], a, b] = {
                    "status": status, "preferred": preferred, "delta_exact": str(truth), "alias": alias}
        calls = sum(v["reason"] != "call_budget_trivial_interval" for v in unique_bounds.values())
        require(meter["cache_components"] == len(unique_bounds) and meter["calls"] == calls
                and meter["expanded_nodes"] == sum(v["expanded"] for v in unique_bounds.values()),
                "unique_component_call_and_expansion_accounting", ident)
        if index % 40 == 39:
            print(json.dumps({"checked_TEST_states": index+1, "errors_so_far": len(errors)}), flush=True)

    relations, pair_details = Counter(), []
    for pair, values in sorted(paired.items()):
        keys = sorted({(a, b) for side, a, b in values})
        for a, b in keys:
            left, right = values["left", a, b], values["right", a, b]
            if left["status"] == right["status"] == "strict":
                kind = "strict_preservation" if left["preferred"] == right["preferred"] else "strict_reversal"
            elif left["status"] == right["status"] == "exact_tie":
                kind = "tie_on_both_sides"
            elif "unknown" in (left["status"], right["status"]):
                kind = "unknown_endpoint"
            else:
                kind = "tie_to_strict" if left["status"] == "exact_tie" else "strict_to_tie"
            relations[kind] += 1
            pair_details.append({"pair": pair, "a": a, "b": b, "classification": kind,
                                 "left": left, "right": right})
    status_counts={k:counts[k] for k in ('strict','exact_tie','unknown') if counts[k]}
    shortfall=sum(q['shortfall'] for r in states for q in r['quota'].values())
    expected_queries=sum(len(r['queries']) for r in states)
    require(complete['execution_complete'] is True and complete['states']==72 and complete['query_status']==status_counts and complete['query_shortfalls']==shortfall and complete['results_sha256']==digest(raw['results.jsonl']) and complete['unknowns_retained'] is True,'independent_complete_query_status_shortfall_and_bytes','complete')
    require(sum(status_counts.values())==expected_queries and not unverified,'all_original_query_slots_and_independent_verifications','complete')
    report={'version':'v06_original72_TEST_certificates_independent_audit_001','checks':sum(checks.values()),'checks_by_kind':dict(checks),'errors':len(errors),'error_records':errors,'archive_sha256':archive_sha256,'source_zip_sha256':receipt['source_zip_sha256'],'root_release_sha256':release_sha256,'results_sha256':digest(raw['results.jsonl']),'TEST_states':72,'TEST_queries':expected_queries,'query_status':status_counts,'quota_shortfalls':shortfall,'family_summary':{k:dict(v) for k,v in summaries.items()},'paired_classifications':dict(relations),'paired_details':pair_details,'strict_details':strict_details,'exact_components':len(exact_cache),'independent_exact_recurrence_states':exact_states,'unverified_components':unverified,'max_independent_states_per_component':max_states,'audit_script_sha256':digest(Path(__file__).read_bytes()),'independent_helpers_sha256':{n:digest((ROOT/n).read_bytes()) for n in ['scripts/verify_evidence_v06.py','scripts/verify_public_alias_v05.py']},'verification_wall_seconds':time.perf_counter()-started,'production_queries_or_programme_runs':0,'programme_selection_or_authoring':False,'scope':'Exact postfreeze verification of every retained original TEST certificate; no production oracle/assessor/scheduler imported, no tuning or new evidence queries.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'checks':report['checks'],'errors':len(errors),'status':status_counts,'paired':dict(relations),'audit_sha256':digest(out.read_bytes())}))
    if errors:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('archive','archive-sha256','capsule','capsule-receipt','release','release-sha256','out'):p.add_argument('--'+n,required=True)
    p.add_argument('--max-states',type=int,default=1000000)
    audit(**vars(p.parse_args()))
