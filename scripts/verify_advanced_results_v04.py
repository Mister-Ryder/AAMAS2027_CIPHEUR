"""Independent streaming audit of completed v04 advanced-comparison archives.

No archive extraction, model/solver calls, quality selection, or study reruns.
Selections, clique partitions, native output mapping, failure accounting and
bootstrap summaries are recomputed from original saved graph data. C3 selections
are additionally checked with the pinned original physical source verifier.
"""
from collections import Counter, defaultdict
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from math import lcm
import argparse
import itertools
import json
from pathlib import Path, PurePosixPath
import statistics
import sys
import zipfile

import numpy as np
import verify_v03_evidence as audit

ROOT = Path(__file__).resolve().parents[1]
SOLVERS = ("CHILS", "M2WIS", "Struction", "WeightedBR")
FIXED = ("baseline_weight", "baseline_degree", "baseline_weighted_conflict",
         "baseline_v02_joint", "baseline_structural_ratio")
SEED, REPLICATIONS = 20261003, 2000


def display_path(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def contains(value, programme):
    def expression(e):
        return {"op":"const","value":float(e["value"])} if e["op"]=="const" else {"op":e["op"],"args":[expression(a) for a in e.get("args",[])]}
    if isinstance(value,dict) and set(value)=={"name","features","rule","rationale"}:
        canonical={**value,"features":[{"name":f["name"],"expression":expression(f["expression"])} for f in value["features"]]}
        if canonical==programme:return True
    return value == programme or (isinstance(value,dict) and any(contains(v,programme) for v in value.values())) or (isinstance(value,list) and any(contains(v,programme) for v in value))


def contexts(data):
    result = {}
    if "public" in data:
        for p in data["public"]:
            result[p["id"]+":graph"] = {"pair_id":p["id"],"side":"graph","split":"public",
                "family":p["family"],"cluster":str(p.get("cluster",p["id"])),
                "fixed":p.get("fixed",[]),"excluded":p.get("excluded",[]),
                "graph":p["graph"],"weight_mode":p.get("source",{}).get("weight_mode")}
    else:
        for p in data["test"]:
            for side in ("left","right"):
                seed=p.get("source",{}).get("seed")
                result[p["id"]+":"+side] = {"pair_id":p["id"],"side":side,"split":"test",
                    "family":p["family"],"cluster":str(seed) if seed is not None else p["id"],
                    "fixed":p.get("fixed",[]),"excluded":p.get("excluded",[]),
                    "graph":p[side],"weight_mode":None}
    return result


def trace(g,row,fixed,excluded,where):
    available = g.available(fixed,excluded)
    actions = []
    for step in row.get("trace",[]):
        v = step["selected"]
        audit.require(v in available and step["remaining_count"] == len(available), "advanced_trace_active_state",where,"selected/count inconsistent")
        audit.require(isinstance(step["score"],(int,float)) and np.isfinite(step["score"]),"advanced_trace_finite_score",where,"invalid score")
        if v not in available: break
        actions.append(v); available -= {v}|g.adj[v]
    audit.require(not available and set(actions)|set(fixed) == set(row["selected"]),"advanced_trace_complete_selection",where,"trace leaves residual or differs from returned set")
    audit.require(row["feature_work"] == sum(row[k] for k in ("initialization_work","update_work","query_work")),"advanced_compiler_work_accounting",where,"work components differ")


def native_input(g,fixed,excluded):
    active = sorted(g.available(fixed,excluded)); aset=set(active)
    index = {v:i+1 for i,v in enumerate(active)}
    scale = 1
    for v in active: scale=lcm(scale,g.weights[v].denominator)
    edges=sum(len(g.adj[v]&aset) for v in active)//2
    lines=[f"{len(active)} {edges} 10"]
    lines += [str(int(g.weights[v]*scale))+" "+" ".join(str(index[u]) for u in sorted(g.adj[v]&aset,key=lambda u:index[u])) for v in active]
    return active,scale,sha256(("\n".join(lines)+"\n").encode()).hexdigest()


def native_row(g,row,fixed,active,scale,input_hash,binaries,phase,where):
    name=row["method"]; base="CHILS" if name=="CHILS_ILS" else name
    audit.require(row.get("integer_scale")==scale and row.get("input_sha256")==input_hash,"advanced_native_exact_input",where,"integer input/hash mismatch")
    audit.require(row.get("executable_sha256")==binaries[base]["sha256"],"advanced_native_binary_identity",where,"binary differs from preflight/execution")
    audit.require(row["declared_seconds"]==phase["official_seconds"] and row["hard_wall_seconds"]==phase["hard_wall_seconds"] and row["threads_declared"]==row.get("threads")==1,"advanced_native_budget_threads",where,"budget/thread receipt differs")
    if not active: return
    command=row.get("command",row.get("adapter_result",{}).get("command",[]))
    audit.require(command and command[0]==binaries[base]["path"],"advanced_native_command_executable",where,"wrong command path")
    if base=="CHILS":
        flags={command[i]:command[i+1] for i in range(1,len(command)-1,2)}
        audit.require(flags.get("-p")==("1" if name=="CHILS_ILS" else "4") and flags.get("-c")=="1" and flags.get("-s")=="0.1" and float(flags.get("-t",-1))==phase["official_seconds"] and flags.get("-r")==str(row["seed"]),"advanced_chils_declared_setting",where,"CHILS/ILS settings differ")
    else:
        audit.require(f"--seed={row['seed']}" in command and f"--time_limit={phase['official_seconds']}" in command,"advanced_kamis_declared_setting",where,"seed/time differs")
        if base=="M2WIS":
            audit.require("--config=mmwis" in command and f"--evo_time_limit={phase['official_seconds']}" in command and f"--ils_time_limit={phase['official_seconds']}" in command,"advanced_m2wis_declared_setting",where,"M2WIS mode differs")
    if not row["completed"]: return
    values=list(map(int,row["solution_text"].split()))
    if row["output_format"]=="partition_flags":
        audit.require(len(values)==len(active) and set(values)<={0,1},"advanced_native_output_flags",where,"malformed output flags")
        selected=list(fixed)+[v for v,f in zip(active,values) if f==1]
    elif row["output_format"]=="one_based_ids":
        audit.require(len(values)==len(set(values)) and all(1<=v<=len(active) for v in values),"advanced_native_output_ids",where,"malformed output IDs")
        selected=list(fixed)+[active[v-1] for v in values]
    else:
        audit.issue("advanced_native_output_format",where,str(row["output_format"]));return
    audit.require(sorted(selected)==row["selected"],"advanced_native_original_mapping",where,"saved native output maps to different contacts")


def formal(g,reference,fixed,excluded,completed,where):
    partition=reference.get("clique_partition",[]);seen=set();upper=g.value(fixed)
    for clique in partition:
        members=set(clique)
        valid=bool(clique) and len(members)==len(clique) and not members&seen and members<=g.contacts.keys()
        audit.require(valid,"advanced_clique_partition_valid",where,"empty, overlap, duplicate or unknown vertex")
        if valid:
            audit.require(all(b in g.adj[a] for a,b in itertools.combinations(clique,2)),"advanced_clique_edges",where,"saved clique has nonedge")
            upper += max(g.weights[v] for v in clique)
        seen.update(members)
    audit.require(seen==g.available(fixed,excluded),"advanced_clique_residual_coverage",where,"partition does not cover active residual")
    audit.require(reference.get("formal_upper_exact") is not None and Fraction(reference["formal_upper_exact"])==upper,"advanced_clique_exact_upper",where,"upper value differs")
    audit.require(Fraction(reference["formal_upper"])>=upper and reference["coverage_edges_and_disjointness_checked"] is True,"advanced_clique_outward_rounding",where,"upper rounded inward or unchecked")
    best=max(completed,key=lambda r:Fraction(r["value_exact"]),default=None)
    lower=Fraction(best["value_exact"]) if best else g.value(fixed)
    audit.require(Fraction(reference["best_verified_lower_exact"])==lower and lower<=upper,"advanced_reference_best_feasible",where,"best incumbent differs/exceeds formal upper")
    audit.check_selection(g,reference["lower_witness"],reference["best_verified_lower"],fixed,excluded,where+"/reference")
    audit.require(g.value(reference["lower_witness"])==lower and reference["lower_witness_method"]==(best["method"] if best else "a_priori_fixed_boundary"),"advanced_reference_witness_identity",where,"reference witness differs")
    audit.require(reference["numerical_dual_is_formal_certificate"] is False and reference["independent_exact_proof"]==(upper==lower),"advanced_reference_formal_scope",where,"floating endpoint promoted or exact-equality scope wrong")
    numeric=reference.get("numerical_upper")
    audit.require(reference["numerical_upper_below_verified_lower"]==(numeric is not None and Fraction(numeric)<lower),"advanced_reference_numerical_lower_flag",where,"numerical inconsistency flag differs")
    return upper,lower


def bootstrap(rows,key):
    blocks=defaultdict(lambda:defaultdict(list))
    for r in rows: blocks[r["stratum"]][r["cluster"]].append(r[key])
    finite=[r[key] for r in rows if r[key] is not None]
    if not finite:return None
    rng=np.random.default_rng(SEED);sums=np.zeros(REPLICATIONS);counts=np.zeros(REPLICATIONS)
    clusters={}
    for stratum,groups in sorted(blocks.items()):
        values=[[v for v in groups[c] if v is not None] for c in sorted(groups)]
        clusters[stratum]=len(values)
        sampled=rng.integers(0,len(values),size=(REPLICATIONS,len(values)))
        sums += np.asarray([sum(v) for v in values])[sampled].sum(axis=1)
        counts += np.asarray([len(v) for v in values])[sampled].sum(axis=1)
    lo,hi=np.quantile(sums[counts>0]/counts[counts>0],[.025,.975])
    return {"estimate":statistics.fmean(finite),"lower":float(lo),"upper":float(hi),"source_clusters":clusters,"assigned_contexts":len(rows),"finite_contexts":len(finite),"replications":REPLICATIONS,"seed":SEED}


def summarise(flat,dataset,saved,phase):
    groups=defaultdict(list)
    for r in flat:groups[r["population"]].append(r)
    output={}
    for name,rows in sorted(groups.items()):
        methods={};savedgroup=next((g for g in (saved or {}).get("groups",[]) if g["population"]==name),None)
        for method in sorted({r["method"] for r in rows}):
            selected=[r for r in rows if r["method"]==method]
            metrics={k:bootstrap(selected,k) for k in ("competitive","formal","coverage","reward_zero","reward_completed","wall","formal_completed")}
            result={"contexts":len(selected),"requested_runs":sum(r["requested"] for r in selected),"completed_runs":sum(r["completed"] for r in selected),"failed_runs":sum(r["requested"]-r["completed"] for r in selected),"median_wall_all_assigned":statistics.median(r["wall"] for r in selected) if all(r["wall"] is not None for r in selected) else None,**metrics}
            if method=="fixed_classical_1to2_search":
                result["median_classical_initializers_plus_search_wall"] = statistics.median(r["initializer_plus_search_wall"] for r in selected)
                result["cost_scope"] = "Saved search-only wall plus all five assigned fixed classical initializer walls, including failed initializers"
            methods[method]=result
            if savedgroup:
                s=savedgroup["methods"][method]
                for k in ("requested_runs","completed_runs","failed_runs"):audit.require(result[k]==s[k],"advanced_analysis_population_counts",phase+"/"+name+"/"+method,k)
                maps={"competitive":"competitive_ratio_failure_zero","formal":"formal_upper_ratio_failure_zero","coverage":"completion_rate","reward_zero":"reward_zero","reward_completed":"reward_completed","wall":"mean_wall_seconds_all_assigned","formal_completed":"formal_upper_ratio_completed"}
                for k,target in maps.items():
                    a,b=metrics[k],s[target]
                    audit.require((a is None)==(b is None),"advanced_analysis_metric_missingness",phase+"/"+name+"/"+method,k)
                    if a and b:
                        audit.require(all(abs(a[v]-b[v])<1e-12 for v in ("estimate","lower","upper")),"advanced_analysis_cluster_ci",phase+"/"+name+"/"+method,k)
                        audit.require(a["source_clusters"]==b["source_clusters"],"advanced_analysis_cluster_grain",phase+"/"+name+"/"+method,k)
                audit.require(result["median_wall_all_assigned"]==s["median_wall_seconds_all_assigned"],"advanced_analysis_assigned_wall_median",phase+"/"+name+"/"+method,"median differs")
        lookup={(r["id"],r["method"]):r for r in rows};deltas={}
        for method in methods:
            if method=="guided_v04":continue
            pairs=[]
            for r in rows:
                if r["method"]=="guided_v04":
                    other=lookup[(r["id"],method)]
                    pairs.append({**r,"difference":r["competitive"]-other["competitive"] if r["competitive"] is not None and other["competitive"] is not None else None})
            deltas["guided_minus_"+method]=bootstrap(pairs,"difference")
            if savedgroup:
                a=deltas["guided_minus_"+method];b=savedgroup["paired_competitive_quality_differences"]["guided_minus_"+method]
                audit.require((a is None and b is None) or (a and b and all(abs(a[v]-b[v])<1e-12 for v in ("estimate","lower","upper"))),"advanced_analysis_paired_ci",phase+"/"+name+"/"+method,"delta/CI differs")
        output[name]={"contexts":len({r["id"] for r in rows}),"methods":methods,"paired_competitive_differences":deltas}
        if phase=="long_results.jsonl" and any(sum(m["competitive"]["source_clusters"].values())<2 for m in methods.values() if m["competitive"]):
            audit.issue("advanced_long_subset_one_cluster",name,"standard/dense subset has one shared seed block; degenerate bootstrap endpoints do not establish population precision","warning")
    return output


def run(path,source,dataset,output,stable_root=None,freeze_archive=None):
    wanted={"data.json","frozen_programs.json","original_config.json","config.json","programs.json","context_plan.json","execution.json","complete.json","additional_programme_receipts.json","additional_source_0.json","additional_source_1.json","additional_source_2.json"}
    meta,hashes=audit.json_members(path,wanted)
    config,exe,done=meta["config.json"],meta["execution.json"],meta["complete.json"]
    input_protocol=meta["data.json"].get("protocol",{})
    expected=contexts(meta.pop("data.json"));frozen=meta["frozen_programs.json"];programmes=meta["programs.json"]
    audit.require(len(expected)=={"fresh":456,"public":96,"sparse":8}[dataset],"advanced_expected_input_population",dataset,"input contexts differ")
    for field,member in (("data_sha256","data.json"),("frozen_sha256","frozen_programs.json"),("config_sha256","original_config.json")):
        audit.require(exe[field]==hashes[member],"advanced_execution_input_byte_hash",member,"byte hash differs")
    freeze_archive=Path(freeze_archive) if freeze_archive is not None else ROOT/"experiments/runs/v04/relevance_train_v04_001.tar.gz"
    original_freeze,freeze_hashes=audit.json_members(freeze_archive,{"frozen_programs.json"})
    audit.require(hashes["frozen_programs.json"]==freeze_hashes["frozen_programs.json"] and frozen==original_freeze["frozen_programs.json"] and frozen["test_accessed"] is False and frozen["selection_split"]=="train","advanced_original_train_freeze",dataset,"freeze differs/access declaration wrong")
    audit.require(done["execution_complete"] is True and done["selection_permitted"] is False and exe["selection_permitted"] is False and config["selection_permitted"] is False,"advanced_completed_no_selection",dataset,"not complete/no-selection declaration differs")
    audit.require(config["seeds"]==[1,2,3] and config["official_seconds"]==config["program_cpu_seconds"]==5 and config["milp_seconds"]==10 and config["local_search_seconds"]==2 and config["score_slice"] is True,"advanced_prespecified_distinct_budgets",dataset,"budget or seed allocation differs")
    native=json.loads((ROOT/"experiments/analysis/v04/native_preflight_v04.json").read_bytes())
    audit.require(all(exe["executables"][s]["sha256"]==native["binary_sha256"][s] for s in SOLVERS),"advanced_native_preflight_binaries",dataset,"execution binary differs from native preflight")
    config_provenance={"exact_prefrozen_bytes":True,"extension_scope":None}
    with zipfile.ZipFile(source) as z:
        inventory={PurePosixPath(n).name:sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith("cipheur/") and n.endswith(".py")}
        audit.require(inventory==exe["source_sha256"],"advanced_complete_source_snapshot_match",dataset,"source archive differs from executed manifest")
        candidates=[n for n in z.namelist() if n.startswith("configs/advanced_")]
        exact_config=any(sha256(z.read(n)).hexdigest()==hashes["original_config.json"] for n in candidates)
        if dataset=="sparse":
            # A separately declared extension config repairs only receipt paths
            # and removes the public-only long subset. Do not invent a byte match.
            original=meta["original_config.json"]
            public=json.loads(z.read("configs/advanced_public_v04_remote.json"))
            def scientific_settings(value):
                value=json.loads(json.dumps(value))
                for key in ("long_budget","long_subset_rule","extension_scope","startup_repair"):
                    value.pop(key,None)
                for entry in value.get("additional_programmes",[]):
                    entry["source_receipt"].pop("path",None)
                return value
            audit.require(scientific_settings(original)==scientific_settings(public),"advanced_sparse_scientific_settings_unchanged",dataset,"extension changes AST/native/budget settings beyond location repair")
            audit.require(bool(original.get("extension_scope")) and bool(original.get("startup_repair")),"advanced_sparse_extension_declared",dataset,"extension declaration missing")
            config_provenance={"exact_prefrozen_bytes":exact_config,"same_scientific_settings_as":"configs/advanced_public_v04_remote.json","extension_scope":original.get("extension_scope"),"startup_repair":original.get("startup_repair"),"allowed_differences":["source receipt paths","no public long subset","extension and repair declarations"]}
            if not exact_config:audit.issue("advanced_sparse_extension_config_not_in_original_zip",dataset,"Exact extension-config bytes are not in the original advanced source ZIP; scientific settings and unchanged receipt payloads independently reconcile.","warning")
        else:
            audit.require(exact_config,"advanced_prefrozen_original_config_bytes",dataset,"original config not found exactly in pre-execution source snapshot")
        for name,p in programmes.items():
            if name in frozen["programs"]:audit.require(p==frozen["programs"][name],"advanced_executed_train_ast_identical",name,"AST differs from TRAIN freeze")
            else:
                r=meta["additional_programme_receipts.json"][name];payload=meta[r["archive_file"]]
                audit.require(hashes[r["archive_file"]]==r["sha256"] and sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()==r["programme_sha256"] and contains(payload,p),"advanced_additional_ast_source_witness",name,"additional AST receipt mismatch")
                audit.require(any(sha256(z.read(n)).hexdigest()==r["sha256"] for n in z.namelist() if n.endswith(".json")),"advanced_additional_source_prefrozen_bytes",name,"additional source not in source snapshot")
    plan=meta["context_plan.json"]
    audit.require(plan["requested_contexts"]==len(expected)==len(plan["contexts"]) and plan["outcome_filtering_permitted"] is False,"advanced_context_plan_complete",dataset,"plan count/filtering differs")
    for r in plan["contexts"]:
        p=expected.get(r["id"])
        audit.require(p is not None and all(r[k]==p[k] for k in ("pair_id","side","split","family","cluster","fixed","excluded")) and r["graph_sha256"]==audit.view(p["graph"]).digest,"advanced_context_plan_identity",r["id"],"saved plan differs from original input")
    summary_path=ROOT/"experiments/analysis/v04/summary.json"
    saved=json.loads(summary_path.read_bytes()).get(dataset) if summary_path.is_file() else None
    if saved and saved["source"]["sha256"]!=audit.file_digest(path):saved=None
    sys.path.insert(0,str(ROOT));from cipheur.v51_adapter import _load_legacy
    physical,original={},{}
    c3=any(p["family"]=="c3" for p in expected.values())
    if c3:
        if stable_root is None:
            raise ValueError("C3 physical verification requires --stable-root pointing to the hash-pinned original V51 source and C3.csv; verification cannot be skipped")
        stable=Path(stable_root).expanduser().resolve()
        c3_protocol=input_protocol["c3"]
        for name,receipt in c3_protocol["source_files"].items():
            if audit.file_digest(stable/"SNSD_V51_FINAL/src/snsd_core"/name)!=receipt["sha256"]:
                raise ValueError("Relocated original C3 source hash differs: "+name)
        csv=stable/"SNSD_V51_FINAL/data/C3.csv"
        if audit.file_digest(csv)!=c3_protocol["data_sha256"]:
            raise ValueError("Relocated original C3.csv hash differs")
        legacy,receipts=_load_legacy(stable)
        arcs={a.id:a for a in legacy["data"].load_arcs(str(csv)).arcs}
        for key,p in expected.items():
            if p["family"]!="c3":continue
            ids=p["graph"]["provenance"]["original_ids"];local=tuple(replace(arcs[v],id=i) for i,v in enumerate(ids))
            g=legacy["graph"].build_conflict_graph(local,legacy["graph"].ConflictParameters(**{k:v for k,v in p["graph"]["constraints"].items() if k!="model"}))
            audit.require({tuple(sorted((str(ids[int(a)]),str(ids[int(b)])))) for a,b in g.edges}==audit.view(p["graph"]).edges,"advanced_c3_original_graph_reconstruction",key,"physical source edges differ")
            original[key]=(g,{str(v):i for i,v in enumerate(ids)})
        physical={"graph_reconstructions":len(original),"completed_solution_checks":0,"source_sha256":{k:v["sha256"] for k,v in receipts.items()},"original_data_sha256":audit.file_digest(csv),"stable_root":str(stable)}
    phases={};members=set()
    for member,handle,full in audit.stream(path):
        audit.require(full not in members,"advanced_unique_archive_member",str(path),full);members.add(full)
        if member not in ("results.jsonl","long_results.jsonl"):continue
        short=member=="results.jsonl";wanted_ids=set(expected) if short else set(plan["long_context_ids"])
        seen=set();flat=[];hasher=sha256();failures=Counter();statuses=Counter();assigned=Counter();complete_counts=Counter();parity=Counter();reference_flags=Counter();context_failures=0
        phase_saved=next(p for p in done["phases"] if p["phase"]["name"]==("short_5s" if short else "representative_30s"));phase=phase_saved["phase"]
        native_names=list(SOLVERS)+(["CHILS_ILS"] if short and config.get("chils_ils_short") else [])
        expected_methods=Counter({m:3 for m in native_names})+Counter({m:1 for m in list(programmes)+list(FIXED)+["fixed_classical_1to2_search","HiGHS_MILP"]+[n+"_full_interface" for n in config.get("full_interface_programme_ids",[])]})
        for line in handle:
            hasher.update(line);r=json.loads(line);where=member+"/"+r["id"];p=expected.get(r["id"])
            audit.require(r["id"] in wanted_ids and r["id"] not in seen,"advanced_phase_context_identity",where,"duplicate/unassigned context")
            seen.add(r["id"])
            if p is None:continue
            g=audit.view(p["graph"]);f,x=p["fixed"],p["excluded"]
            audit.require(all(r[k]==p[k] for k in ("pair_id","side","split","family","cluster","fixed","excluded")) and r["graph_sha256"]==g.digest and r["n"]==len(g.contacts) and r["m"]==len(g.edges),"advanced_result_original_graph_identity",where,"graph/context metadata differs")
            audit.require(r["phase"]==phase and r["selection_permitted"] is False,"advanced_result_phase_scope",where,"phase or selection differs")
            audit.require(Counter(m["method"] for m in r["methods"])==expected_methods,"advanced_method_population",where,"missing/extra method or seed")
            by=defaultdict(list);completed=[];active,scale,input_hash=native_input(g,f,x)
            for row in r["methods"]:
                name=row["method"];w=where+"/"+name+"/"+str(row.get("seed","single"));by[name].append(row);assigned[name]+=1;statuses[name+"/"+row["status"]]+=1
                audit.require(isinstance(row.get("seconds"),(int,float)) and np.isfinite(row["seconds"]) and row["seconds"]>=0,"advanced_all_assigned_wall_cost_retained",w,"missing/nonfinite/negative elapsed cost")
                for field in ("cpu_seconds","child_cpu_seconds","adapter_cpu_seconds"):
                    if field in row:audit.require(isinstance(row[field],(int,float)) and np.isfinite(row[field]) and row[field]>=0,"advanced_observed_cpu_cost_valid",w,field)
                audit.require(row["fallback_used"] is False and row["exact_optimum_claimed"] is False,"advanced_method_no_fallback_no_optimum",w,"scope/fallback differs")
                audit.require(row["completed"]==(row.get("value") is not None),"advanced_method_completion_null",w,"completion and reward disagree")
                if row["completed"]:
                    audit.check_selection(g,row["selected"],row["value"],f,x,w)
                    audit.require(row["feasible"] is True and g.value(row["selected"])==Fraction(row["value_exact"]),"advanced_selected_exact_reward",w,"exact reward differs")
                    completed.append(row);complete_counts[name]+=1
                    if "trace" in row:trace(g,row,f,x,w)
                else:
                    failures[name]+=1
                    audit.require(all(row.get(k) is None for k in ("selected","value","value_exact","feasible","trace")),"advanced_failure_no_partial_schedule",w,"failed row returns partial/fallback reward")
                    audit.require(row.get("returned_result") is None,"advanced_failure_no_nested_partial_result",w,"nested partial schedule retained")
                if row["kind"]=="published":native_row(g,row,f,active,scale,input_hash,exe["executables"],phase,w)
                elif "declared_cpu_seconds" in row:
                    audit.require(row["declared_cpu_seconds"]==5,"advanced_constructive_budget",w,"constructive CPU target differs")
                if r["family"]=="c3" and row["completed"]:
                    old,mapping=original[r["id"]];check=legacy["verifier"].verify_selected_ids(old,[mapping[v] for v in row["selected"]])
                    actual={"feasible":check.feasible,"conflicts":len(check.conflicting_edges),"duplicates":len(check.duplicate_ids),"invalid":len(check.invalid_ids)}
                    receipt=r["source_verifier"].get("checks",{}).get(name+":"+str(row.get("seed","single")))
                    audit.require(actual==receipt and actual=={"feasible":True,"conflicts":0,"duplicates":0,"invalid":0},"advanced_c3_original_selected_verification",w,"original verifier or receipt mismatch")
                    physical["completed_solution_checks"]+=1
            context_failures+=bool(any(not m["completed"] for m in r["methods"]))
            local=by["fixed_classical_1to2_search"][0]
            classical=[by[n][0] for n in FIXED if by[n][0]["completed"]]
            initial=min(classical,key=lambda m:(-Fraction(m["value_exact"]),m["method"]),default=None)
            audit.require(initial is None or local["initial_method"]==initial["method"],"advanced_local_best_completed_classical_initializer",where,"local initializer differs from best completed classical baseline")
            audit.require(not local["completed"] or (initial is not None and Fraction(local["value_exact"])>=Fraction(initial["value_exact"])),"advanced_local_monotone_from_initializer",where,"local search loses initial reward or substitutes a fallback")
            audit.require(local["declared_seconds"]==2,"advanced_local_distinct_budget",where,"local exchange-search budget differs")
            if r["family"]=="c3":
                s=r["source_verifier"]
                audit.require(s["checked"] is True and s["reconstructed_edges_identical"] is True and s["source_sha256"]==physical["source_sha256"] and len(s["checks"])==len(completed),"advanced_c3_physical_receipt_complete",where,"missing graph/solution/source confirmations")
            upper,lower=formal(g,r["reference"],f,x,completed,where)
            reference_flags["formal_clique_upper_available"]+=1;reference_flags["formal_lower_equals_upper"]+=upper==lower
            numerical=by["HiGHS_MILP"][0]
            reference_flags["numerical_solver_status_"+str(numerical.get("solver_status"))]+=1
            audit.require(r["reference"]["numerical_upper"]==numerical.get("numerical_upper") and r["reference"]["numerical_solver_status"]==numerical.get("solver_status"),"advanced_numerical_reference_identity",where,"numerical result differs")
            for name,group in by.items():
                published=group[0]["kind"]=="published"
                audit.require(sorted(m.get("seed") for m in group)==[1,2,3] if published else len(group)==1,"advanced_three_seed_grain",where+"/"+name,"seed repetitions/grain differs")
                values=[Fraction(m["value_exact"]) if m["completed"] else Fraction(0) for m in group]
                done_values=[v for m,v in zip(group,values) if m["completed"]];mean=sum(values)/len(values);done_mean=sum(done_values)/len(done_values) if done_values else None
                formal_ratio=float(mean/upper) if upper else len(done_values)/len(values)
                competitive=float(mean/lower) if lower else len(done_values)/len(values)
                saved_method=r["method_summary"][name]
                audit.require(saved_method["requested_runs"]==len(values) and saved_method["completed_runs"]==len(done_values) and saved_method["failed_runs"]==len(values)-len(done_values) and audit.near(saved_method["primary_reward_mean_zero_accounted"],mean) and audit.near(saved_method["primary_quality_mean_zero_accounted"],formal_ratio),"advanced_saved_failure_zero_aggregation",where+"/"+name,"saved per-context summary differs")
                for m,v in zip(group,values):audit.require(audit.near(m["quality_to_formal_upper"],float(v/upper) if upper else int(m["completed"])),"advanced_row_formal_quality",where+"/"+name,"saved quality differs")
                stratum="standard" if r["family"].startswith("standard_") else "dense_long" if r["family"].startswith("dense_long_") else r["family"]
                population=stratum if dataset=="fresh" else ("SNAP" if dataset=="sparse" else r["family"])+"/"+str(p["weight_mode"])
                flat.append({"id":r["id"],"population":population,"stratum":stratum,"cluster":r["cluster"],"method":name,"requested":len(values),"completed":len(done_values),"coverage":len(done_values)/len(values),"reward_zero":float(mean),"reward_completed":float(done_mean) if done_mean is not None else None,"competitive":competitive,"formal":formal_ratio,"formal_completed":float(done_mean/upper) if done_mean is not None and upper else None,"wall":statistics.fmean(m["seconds"] for m in group) if all(m.get("seconds") is not None for m in group) else None,"initializer_plus_search_wall":sum(by[n][0]["seconds"] for n in FIXED)+local["seconds"]})
            for name,record in r["full_interface_parity"].items():
                a,b=by[name][0],by[name+"_full_interface"][0];both=a["completed"] and b["completed"]
                audit.require(record["both_completed"]==both and record["programme_definition_identical"] is True and record["selection_permitted"] is False,"advanced_interface_parity_scope",where+"/"+name,"parity scope differs")
                for k,savedkey in (("selected","selection_identical"),("trace","trace_identical"),("value_exact","exact_value_identical")):
                    equal=(a[k]==b[k]) if both else None
                    audit.require(record[savedkey]==equal,"advanced_interface_parity_recomputed",where+"/"+name,k)
                    if both:audit.require(equal,"advanced_interface_exact_equivalence",where+"/"+name,k)
                parity["both_completed" if both else "unassessable"]+=1
            if "guided_primary_only_ablation" in by and programmes["guided_primary_only_ablation"]==programmes["guided_v04"]:
                a,b=by["guided_primary_only_ablation"][0],by["guided_v04"][0]
                if a["completed"] and b["completed"]:audit.require(all(a[k]==b[k] for k in ("trace","selected","value_exact")),"advanced_same_ast_primary_ablation",where,"identical primary-only AST produces different result")
        audit.require(seen==wanted_ids and len(seen)==phase_saved["processed_contexts"]==phase_saved["requested_contexts"] and phase_saved["execution_complete"] is True,"advanced_phase_assignment_complete",member,"missing/extra contexts or partial harness")
        audit.require(hasher.hexdigest()==phase_saved["results_sha256"] and dict(failures)==phase_saved["failed_method_runs"] and context_failures==phase_saved["contexts_with_method_failures"] and phase_saved["all_requested_methods_completed"]==(not bool(failures)),"advanced_phase_hash_failure_accounting",member,"saved completion/failure/hash mismatch")
        phase_summary=saved.get("short" if short else "long_prespecified_subset") if saved else None
        phases[member]={"contexts":len(seen),"assigned_runs":sum(assigned.values()),"rows_per_context":sum(expected_methods.values()),"method_assigned_runs":dict(assigned),"method_completed_runs":dict(complete_counts),"failed_method_runs":dict(failures),"method_statuses":dict(statuses),"full_interface_parity":dict(parity),"reference_counts":dict(reference_flags),"groups":summarise(flat,dataset,phase_summary,member)}
    report={"archive":display_path(path),"archive_sha256":audit.file_digest(path),"dataset":dataset,"source_snapshot":display_path(source),"source_snapshot_sha256":audit.file_digest(source),"executed_source_files":len(exe["source_sha256"]),"input_member_sha256":hashes["data.json"],"train_freeze_sha256":hashes["frozen_programs.json"],"train_freeze_archive_sha256":audit.file_digest(freeze_archive),"config_member_sha256":hashes["original_config.json"],"phases":phases,"physical_source":physical,"independent_bootstrap_compared_to_saved_analysis":saved is not None,"checks":dict(audit.CHECKS),"issues":list(audit.ISSUES.values()),"scope":["Original graph witnesses, exact clique partitions, native integer input/output mapping and seed means independently verified.","C3 graphs and every completed selection rebuilt/reverified with pinned original physical source code; temporal graph construction was checked in fresh_input_audit.json.","Full-interface/sliced actual traces compared directly; this audit does not rerun all rankings or native searches.","100% competitive reward is relative to strongest saved feasible witness, not an optimality certificate; floating HiGHS endpoints remain numerical.","Source/config/freeze bytes and no-selection declarations checked; unseen external access is not observable from archives.","Native binary hashes matched executed/preflight receipts; remote binaries not independently rehashed locally.","Shared seed/source blocks and both pair sides retained in 2000 bootstrap replicates; long subset precision/generalization is limited.","Native wall metric is median across context mean seed-wall times, not total cost of all three runs.","Local search-only row time excludes initialization; additional audit metric sums all five assigned classical initialization costs and search cost."]}
    report["config_provenance"]=config_provenance
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--archive",required=True);p.add_argument("--source",default="experiments/source_snapshots/v04/advanced_v04_003_source.zip");p.add_argument("--dataset",choices=("fresh","public","sparse"),required=True);p.add_argument("--output",required=True)
    p.add_argument("--stable-root",type=Path,help="Required for C3: relocate the same hash-pinned original V51 source and C3.csv")
    p.add_argument("--freeze-archive",type=Path,default=ROOT/"experiments/runs/v04/relevance_train_v04_001.tar.gz")
    args=p.parse_args();report=run((ROOT/args.archive).resolve(),(ROOT/args.source).resolve(),args.dataset,(ROOT/args.output).resolve(),args.stable_root,args.freeze_archive)
    print(json.dumps({"output":args.output,"checks":sum(audit.CHECKS.values()),"issues":report["issues"],"phases":{k:{q:v[q] for q in ("contexts","assigned_runs","failed_method_runs","full_interface_parity","reference_counts")} for k,v in report["phases"].items()},"physical":report["physical_source"]}))
    raise SystemExit(int(any(i["severity"]=="error" for i in report["issues"])))
