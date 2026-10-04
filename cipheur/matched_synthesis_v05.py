"""Equal-slot, cold-prompt evidence pilot, isolated from immutable v04 results.

The three arms differ only in authoring evidence. Every arm uses the same
typed grammar, declared-interface gate, TRAIN utility, and compiled runtime.
No LLM is invoked by this runner. Authoring responses are immutable inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import statistics
import tarfile
import time

from .compiled import schedule_compiled
from .experiment_data import instance_fingerprint
from .graph_features import FeatureRuleProgram
from .model import Graph
from .oracle import solve, exact_value
from .refinement import diagnose_occurrences
from .relevance_synthesis_v04 import _Meter, fresh_temporal_pair

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("witness", "relations", "objective")


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def fresh_directory(path):
    path = Path(path)
    if path.exists():
        raise ValueError("Preserve previous observations: choose a fresh output directory")
    path.mkdir(parents=True)
    return path


def source_receipt():
    names = ("matched_synthesis_v05.py", "compiled.py", "model.py", "graph_features.py", "programs.py", "representation.py", "refinement.py", "oracle.py", "relevance_synthesis_v04.py", "experiment_data.py")
    return {name: file_hash(Path(__file__).parent / name) for name in names}


def load_study(path):
    path = Path(path)
    protocol = json.loads((path / "protocol.json").read_text(encoding="utf-8"))
    freeze = json.loads((path / "freeze_receipt.json").read_text(encoding="utf-8"))
    if protocol["version"] != "matched_synthesis_v05_001" or protocol["arms"] != list(ARMS):
        raise ValueError("Unknown registered pilot")
    if file_hash(path / "protocol.json") != freeze["protocol_sha256"] or freeze["before_authoring"] is not True:
        raise ValueError("Preregistered protocol bytes changed")
    if file_hash(path / "training_evidence.json") != protocol["training_evidence_sha256"]:
        raise ValueError("TRAIN evidence changed")
    if freeze["packet_sha256"] != protocol["packet_sha256"]:
        raise ValueError("Packet inventory changed")
    for name, expected in protocol["packet_sha256"].items():
        if file_hash(path / name) != expected:
            raise ValueError("Authoring packet changed: " + name)
    return path, protocol, freeze


def validate_response(payload, block, arm, slots=12):
    """Keep exact output slots; no repair or replacement of authoring failures."""
    good_schema = (isinstance(payload, dict) and set(payload) == {"version", "block", "arm", "candidates"}
                   and payload["version"] == "matched_cold_bank_v05" and payload["block"] == block
                   and payload["arm"] == arm and isinstance(payload["candidates"], list))
    candidates = payload["candidates"] if good_schema else []
    schema_error = not good_schema or len(candidates) > slots
    entries, seen = [], set()
    for index in range(slots):
        row = {"id": f"block_{block}_{arm}:{index}", "arm": arm, "block": block, "slot": index, "program": None}
        if schema_error:
            row["status"] = "invalid_response_schema"
        elif index >= len(candidates):
            row["status"] = "missing_slot"
        else:
            try:
                program = FeatureRuleProgram.from_dict(candidates[index]).to_dict()
                # Names and rationales do not distinguish deployment ASTs.
                key = canonical({k: program[k] for k in ("features", "rule")})
                if key in seen:
                    row["status"] = "duplicate_deployment_AST_within_batch"
                else:
                    seen.add(key)
                    row.update(status="static_valid", program=program, program_sha256=canonical(program), deployment_AST_sha256=key)
            except (TypeError, ValueError, KeyError, RecursionError) as error:
                row.update(status="invalid_candidate", error_type=type(error).__name__, error=str(error))
        entries.append(row)
    return entries


def load_bank(study, protocol):
    amendment_path = study / "transport_amendment.json"
    completion_path = study / "authoring_completion.json"
    if not amendment_path.is_file() or not completion_path.is_file():
        raise ValueError("Freeze all 12 amended-transport authoring responses before any candidate assessment")
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if (amendment["original_protocol_sha256"] != file_hash(study / "protocol.json")
            or amendment["decided_before_any_v05_candidate_assessment"] is not True
            or completion["version"] != "matched_cli_authoring_completion_v05"
            or completion["transport_amendment_sha256"] != file_hash(amendment_path)
            or completion["all_authoring_completed_before_assessment"] is not True
            or completion["same_requested_model_and_settings_all_cells"] is not True):
        raise ValueError("Incomplete or changed pre-outcome authoring transport amendment")
    expected_names = {f"block_{b}_{a}.json" for b in range(protocol["blocks"]) for a in ARMS}
    if set(completion["response_sha256"]) != expected_names:
        raise ValueError("Authoring completion must cover every assigned CLI cell")
    bank, receipts = [], []
    for block in range(protocol["blocks"]):
        for arm in ARMS:
            name = f"block_{block}_{arm}.json"
            path = study / "responses" / name
            if not path.is_file():
                raise ValueError("Authoring session not recorded: " + name)
            if file_hash(path) != completion["response_sha256"][name]:
                raise ValueError("An authoring response changed after the all-cell freeze: " + name)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                parse_error = None
            except (ValueError, UnicodeError) as error:
                payload, parse_error = None, type(error).__name__
            entries = validate_response(payload, block, arm, protocol["slots_per_block_arm"])
            bank.extend(entries)
            receipts.append({"block": block, "arm": arm, "file": name, "sha256": file_hash(path),
                             "parse_error": parse_error, "slot_status": dict(Counter(e["status"] for e in entries))})
    if len(bank) != protocol["requested_slots"]:
        raise ValueError("Assigned authoring slot count changed")
    return bank, receipts


def execute(graph, program, fixed=(), excluded=(), seconds=5):
    started, cpu = time.perf_counter(), time.process_time()
    try:
        result = schedule_compiled(graph, FeatureRuleProgram.from_dict(program), fixed, excluded,
                                   meter=_Meter(seconds), score_slice=True)
        if not graph.feasible(result["selected"]):
            raise AssertionError("Completed schedule violates graph feasibility")
        row = {"completed": True, "status": "completed", "value": result["value"],
               "value_exact": str(exact_value(graph, result["selected"])), "feature_work": result["feature_work"],
               "selected": result["selected"], "trace": result["trace"]}
    except (TimeoutError, ValueError, ArithmeticError, RecursionError) as error:
        row = {"completed": False, "status": type(error).__name__, "error": str(error), "value": None,
               "value_exact": None, "feature_work": None, "selected": None, "trace": None}
    row.update(cpu_seconds=time.process_time()-cpu, wall_seconds=time.perf_counter()-started)
    return row


def train_context(task):
    context, bank, seconds = task
    graph = Graph.from_dict(context["graph"])
    # Rotate predetermined assignment order by graph identity. All rows remain
    # assigned, including rejected output slots; no reward is read for ordering.
    shift = int(graph.digest()[:8], 16) % len(bank)
    order = bank[shift:] + bank[:shift]
    rows = []
    for entry in order:
        if entry["program"] is None:
            r = {"completed": False, "status": entry["status"], "value": None, "value_exact": None,
                 "feature_work": None, "selected": None, "trace": None, "cpu_seconds": 0.0, "wall_seconds": 0.0}
        else:
            r = execute(graph, entry["program"], context["fixed"], context["excluded"], seconds)
        rows.append({"candidate_id": entry["id"], **r})
    return {"pair_id": context["pair_id"], "side": context["side"], "family": context["family"],
            "graph_digest": graph.digest(), "size": len(graph.nodes), "fixed_reward_reference": context["fixed_reward_reference"],
            "fixed_degree_work": context["fixed_degree_work"], "rows": rows}


def information_gate(task):
    entry, evidence = task
    if entry["program"] is None:
        return {"candidate_id": entry["id"], "passed": False, "status": entry["status"]}
    program = FeatureRuleProgram.from_dict(entry["program"])
    graphs = {sid: (Graph.from_dict(row["graph"]), row["fixed"], row["excluded"]) for sid, row in evidence["states"].items()}
    vectors, scores = {}, {}
    started, cpu = time.perf_counter(), time.process_time()
    try:
        for oid, binding in evidence["endpoints"].items():
            g, f, x = graphs[binding["prefix"]]
            vectors[oid] = program.evaluate_features(g, binding["node"], g.available(f,x))
            try:
                scores[oid] = program._rank(vectors[oid])
            except (ValueError, ArithmeticError):
                scores[oid] = None
        diagnosis = diagnose_occurrences(vectors, evidence["requirements"])
        actual = [r for r in evidence["requirements"] if r["metadata"]["kind"] == "cancelled_actual_action"]
        actual_diag = diagnose_occurrences(vectors, actual)
        counts = Counter()
        for r in evidence["requirements"]:
            p, n = scores[r["preferred"]], scores[r["other"]]
            counts["invalid_score" if p is None or n is None else "agree" if p > n else "tie" if p == n else "violate"] += 1
        result = {"candidate_id": entry["id"], "passed": not diagnosis["contradictory"], "status": "completed",
                  "full_quotient": diagnosis, "actual_only_quotient": actual_diag, "scalar_agreement": dict(counts)}
    except (ValueError, ArithmeticError, RecursionError) as error:
        result = {"candidate_id": entry["id"], "passed": False, "status": "feature_runtime_error", "error": str(error)}
    result.update(cpu_seconds=time.process_time()-cpu, wall_seconds=time.perf_counter()-started)
    return result


def select(bank, contexts, gates, penalty=.002):
    gate = {g["candidate_id"]:g for g in gates}
    rows = defaultdict(list)
    for c in contexts:
        for r in c["rows"]:
            quality = r["value"]/c["fixed_reward_reference"] if r["completed"] and c["fixed_reward_reference"] else 0
            work = r["feature_work"]/max(1,c["fixed_degree_work"]) if r["completed"] else 100
            rows[r["candidate_id"]].append({"family":c["family"], "quality":quality, "work":work, "completed":r["completed"]})
    assessments = []
    for entry in bank:
        grouped = defaultdict(list)
        for r in rows[entry["id"]]: grouped[r["family"]].append(r)
        quality = statistics.fmean(statistics.fmean(r["quality"] for r in rs) for rs in grouped.values())
        work = statistics.fmean(statistics.fmean(r["work"] for r in rs) for rs in grouped.values())
        assessments.append({**entry, "gate_passed": gate[entry["id"]]["passed"], "quality": quality, "relative_work":work,
                            "utility":quality-penalty*(work-1), "completed_contexts":sum(r["completed"] for r in rows[entry["id"]]),
                            "assigned_contexts":len(rows[entry["id"]])})
    programs, choices = {}, {}
    for block in sorted({e["block"] for e in bank}):
        for arm in ARMS:
            name = f"block_{block}_{arm}"
            pool = [r for r in assessments if r["block"]==block and r["arm"]==arm and r["gate_passed"]]
            if pool:
                best = max(pool,key=lambda r:(r["utility"],-r["slot"]))
                programs[name] = best["program"]
                choices[name] = {"selected_id":best["id"], "eligible_slots":len(pool), "utility":best["utility"]}
            else:
                choices[name] = {"selected_id":None,"eligible_slots":0,"reason":"no_static_finite_acyclic_candidate", "fallback_used":False}
    return assessments,programs,choices


def parallel_collect(function, tasks, workers, path):
    results = []
    with Path(path).open("w",encoding="utf-8") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(function,t) for t in tasks]
            for future in as_completed(futures):
                row = future.result()
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n");stream.flush()
                results.append(row)
    return results


def run_train(study, output, workers):
    study,protocol,receipt = load_study(study)
    bank,responses = load_bank(study,protocol)
    if not (study/"prior_input_inventory.json").is_file():
        raise ValueError("Freeze the released prior INPUT inventory before TRAIN dispatch")
    evidence = json.loads((study/"training_evidence.json").read_text(encoding="utf-8"))
    output = fresh_directory(output)
    write(output/"protocol.json",protocol);write(output/"candidate_bank.json",bank);write(output/"authoring_responses.json",responses)
    for r in responses:
        raw=(study/"responses"/r["file"]).read_bytes()
        (output/r["file"]).write_bytes(raw)
    execution={"source_sha256":source_receipt(),"protocol_sha256":receipt["protocol_sha256"],
               "transport_amendment_sha256":file_hash(study/"transport_amendment.json"),
               "authoring_completion_sha256":file_hash(study/"authoring_completion.json"),
               "prior_input_inventory_sha256":file_hash(study/"prior_input_inventory.json"),
               "training_evidence_sha256":protocol["training_evidence_sha256"],"external_model_calls":0,"test_outcomes_read":False,
               "workers":workers,"requested_contexts":len(evidence["contexts"]),"requested_slots":len(bank),"scope":"new matched authoring pilot; TRAIN-only numerical selection"}
    write(output/"execution.json",execution)
    gates=parallel_collect(information_gate,[(e,evidence) for e in bank],workers,output/"information_gates.jsonl")
    contexts=parallel_collect(train_context,[(c,bank,protocol["cpu_seconds"]) for c in evidence["contexts"]],workers,output/"training_results.jsonl")
    assessments,programs,choices=select(bank,contexts,gates,protocol["selection"]["cost_penalty"])
    write(output/"assessments.json",assessments)
    frozen={"version":"matched_freeze_v05_001","selection_split":"train","test_accessed":False,
            "programs":programs,"selection":choices,"protocol_sha256":receipt["protocol_sha256"],
            "training_evidence_sha256":protocol["training_evidence_sha256"],"candidate_bank_sha256":file_hash(output/"candidate_bank.json"),
            "response_sha256":{r["file"]:r["sha256"] for r in responses},"source_sha256":execution["source_sha256"],
            "transport_amendment_sha256":execution["transport_amendment_sha256"],
            "authoring_completion_sha256":execution["authoring_completion_sha256"],
            "prior_input_inventory_sha256":execution["prior_input_inventory_sha256"],
            "all_assigned_banks":12,"no_eligible_banks":12-len(programs),"no_replacement_no_fallback":True}
    write(output/"frozen_programs.json",frozen)
    write(output/"complete.json",{"complete":True,"contexts":len(contexts),"slots":len(bank),
                                 "attempts":sum(len(c["rows"]) for c in contexts),"frozen_sha256":file_hash(output/"frozen_programs.json")})
    print(json.dumps({"complete":True,"output":str(output),"selected_banks":len(programs)}),flush=True)


def nested_inputs(value, seeds, graphs, fingerprints):
    if isinstance(value,dict):
        if "seed" in value and isinstance(value["seed"],int): seeds.add(value["seed"])
        if {"name","contacts","edges"} <= value.keys():
            g=Graph.from_dict(value);graphs.add(g.digest());fingerprints.add(instance_fingerprint(g.contacts))
        for v in value.values():nested_inputs(v,seeds,graphs,fingerprints)
    elif isinstance(value,list):
        for v in value:nested_inputs(v,seeds,graphs,fingerprints)


def prior_input_inventory():
    seeds,graphs,fingerprints,receipts=set(),set(),set(),[]
    for path in sorted((ROOT/"experiments/runs").rglob("*.tar.gz")):
        with tarfile.open(path,"r:gz") as tar:
            for member in tar.getmembers():
                if member.isfile() and Path(member.name).name=="data.json":
                    raw=tar.extractfile(member).read();value=json.loads(raw)
                    nested_inputs(value,seeds,graphs,fingerprints)
                    receipts.append({"archive":path.relative_to(ROOT).as_posix(),"member":member.name,"input_sha256":sha256(raw).hexdigest()})
    return seeds,graphs,fingerprints,receipts


def run_inventory(study,output):
    study,protocol,receipt=load_study(study)
    output=Path(output)
    if output.exists():raise ValueError("Preserve previous prior INPUT inventory")
    seeds,graphs,fingerprints,receipts=prior_input_inventory()
    ranges=[(protocol["test"]["namespace"],protocol["test"]["namespace"]+3000000),
            (protocol["test"]["namespace"]+100000000,protocol["test"]["namespace"]+103000000)]
    if any(lo<=seed<hi for seed in seeds for lo,hi in ranges):
        raise ValueError("Registered namespace collides with a released prior INPUT seed")
    write(output,{"version":"released_prior_inputs_v05_001","protocol_sha256":receipt["protocol_sha256"],
                  "seeds":sorted(seeds),"graph_digests":sorted(graphs),"contact_fingerprints":sorted(fingerprints),
                  "inputs":receipts,"outcomes_read":False,"new_registered_namespace_overlap":False,
                  "scope":"All released tar data.json INPUT members present at the pre-TRAIN scan; no outcome member read. Unknown private exposures cannot be inferred."})
    print(json.dumps({"prior_inputs":len(receipts),"seeds":len(seeds),"graphs":len(graphs),"contact_fingerprints":len(fingerprints),"sha256":file_hash(output)}),flush=True)


def load_frozen(study,path):
    study,protocol,receipt=load_study(study)
    frozen=json.loads(Path(path).read_text(encoding="utf-8"))
    if frozen["version"]!="matched_freeze_v05_001" or frozen["test_accessed"] is not False or frozen["selection_split"]!="train":
        raise ValueError("A new TRAIN-only freeze is required")
    if frozen["protocol_sha256"]!=receipt["protocol_sha256"]:
        raise ValueError("TRAIN freeze belongs to another protocol")
    if (file_hash(study/"transport_amendment.json") != frozen["transport_amendment_sha256"]
            or file_hash(study/"authoring_completion.json") != frozen["authoring_completion_sha256"]):
        raise ValueError("Authoring transport or all-cell completion changed after TRAIN")
    if file_hash(study/"prior_input_inventory.json")!=frozen["prior_input_inventory_sha256"]:
        raise ValueError("Released prior INPUT inventory changed after TRAIN")
    for name,expected in frozen["response_sha256"].items():
        if file_hash(study/"responses"/name)!=expected:raise ValueError("An authoring response changed after TRAIN")
    for name,expected in frozen["source_sha256"].items():
        if file_hash(Path(__file__).parent/name)!=expected:raise ValueError("Execution source changed after TRAIN: "+name)
    return study,protocol,frozen


def run_fresh(study,frozen_path,output):
    study,protocol,frozen=load_frozen(study,frozen_path)
    prior=json.loads((study/"prior_input_inventory.json").read_text(encoding="utf-8"))
    if prior["protocol_sha256"]!=frozen["protocol_sha256"] or prior["outcomes_read"] is not False:
        raise ValueError("Prior INPUT inventory belongs to another protocol")
    old_seeds,old_graphs,old_fingerprints,inventory=set(prior["seeds"]),set(prior["graph_digests"]),set(prior["contact_fingerprints"]),prior["inputs"]
    config=protocol["test"];records=[]
    for profile in config["profiles"]:
        for regime in config["regimes"]:
            for size in config["sizes"]:
                for index in range(config["pairs_per_cell"]):
                    pair=fresh_temporal_pair("test",size,index,regime,profile,config["namespace"])
                    if pair["source"]["seed"] in old_seeds:raise ValueError("Fresh seed is in a released prior input")
                    pair["id"]=pair["id"].replace("v04_","v05_",1)
                    pair["source"]["origin"]="v05_preregistered_fresh_generator"
                    for side in ("left","right"):
                        pair[side]["name"]=pair["id"]+"_"+side
                        g=Graph.from_dict(pair[side])
                        if g.digest() in old_graphs or instance_fingerprint(g.contacts) in old_fingerprints:
                            raise ValueError("Fresh graph/contacts equal a released prior input")
                    records.append(pair)
    if len(records)!=config["pairs"] or 2*len(records)!=config["contexts"]:raise ValueError("TEST population arithmetic changed")
    output=fresh_directory(output)
    write(output/"data.json",{"test":records,"protocol":{"version":"matched_fresh_v05_001","selection_frozen_sha256":file_hash(frozen_path),
                                                            "protocol_sha256":frozen["protocol_sha256"],"outcome_filtering":False,
                                                            "no_C3":True,"source":"new temporal contacts from prespecified namespace"}})
    write(output/"prior_input_inventory.json",{"inputs":inventory,"unique_seeds":len(old_seeds),"unique_graphs":len(old_graphs),
                                              "unique_contact_fingerprints":len(old_fingerprints),"outcomes_read":False,
                                              "scope":"released tar input members only; unrecorded private exposures cannot be inferred"})
    write(output/"complete.json",{"complete":True,"pairs":len(records),"contexts":2*len(records),"data_sha256":file_hash(output/"data.json"),
                                 "no_prior_input_identity_overlap":True,"no_physical_C3_claim":True})
    print(json.dumps({"complete":True,"output":str(output),"contexts":2*len(records)}),flush=True)


def test_context(task):
    pair,side,programs,selection,seconds=task
    g=Graph.from_dict(pair[side]);rows=[]
    for name in sorted(selection):
        if name not in programs:
            row={"completed":False,"status":"no_eligible_training_slot","value":None,"value_exact":None,
                 "feature_work":None,"selected":None,"trace":None,"cpu_seconds":0,"wall_seconds":0}
        else:row=execute(g,programs[name],pair["fixed"],pair["excluded"],seconds)
        rows.append({"method":name,**row})
    degree=FeatureRuleProgram("fixed_degree_reference",[],"weight/max(1,degree)","Fixed classical test reference.").to_dict()
    rows.append({"method":"degree",**execute(g,degree,pair["fixed"],pair["excluded"],seconds)})
    # This reference computation is offline evaluation, separately timed and
    # never used by the deployed ranker or by any programme selection.
    bound=solve(g,max_nodes=0)
    return {"pair_id":pair["id"],"side":side,"family":pair["family"],"source":pair["source"],"size":len(g.nodes),
            "graph_digest":g.digest(),"reference":{"upper_exact":bound.upper_exact,"lower_exact":bound.lower_exact,
                                                       "scope":"zero-search weighted clique upper; not a proven optimum"},"rows":rows}


def run_evaluate(study,frozen_path,data_path,output,workers):
    study,protocol,frozen=load_frozen(study,frozen_path)
    data=json.loads(Path(data_path).read_text(encoding="utf-8"))
    if data["protocol"]["selection_frozen_sha256"]!=file_hash(frozen_path) or data["protocol"]["protocol_sha256"]!=frozen["protocol_sha256"]:
        raise ValueError("Fresh input does not bind this TRAIN freeze")
    if len(data["test"])*2!=protocol["test"]["contexts"]:raise ValueError("Fresh assigned count differs")
    output=fresh_directory(output)
    (output/"data.json").write_bytes(Path(data_path).read_bytes());(output/"frozen_programs.json").write_bytes(Path(frozen_path).read_bytes())
    write(output/"execution.json",{"source_sha256":source_receipt(),"data_sha256":file_hash(data_path),"freeze_sha256":file_hash(frozen_path),
                                  "protocol_sha256":frozen["protocol_sha256"],"workers":workers,"cpu_seconds":protocol["cpu_seconds"],
                                  "external_model_calls":0,"online_oracle_calls":0,"offline_reference_calls":protocol["test"]["contexts"],
                                  "new_program_selection":False,"four_block_pilot_not_population_superiority":True})
    contexts=parallel_collect(test_context,[(p,s,frozen["programs"],frozen["selection"],protocol["cpu_seconds"]) for p in data["test"] for s in ("left","right")],workers,output/"results.jsonl")
    write(output/"complete.json",{"complete":True,"contexts":len(contexts),"assigned_runs":sum(len(c["rows"]) for c in contexts),
                                 "completed_runs":sum(r["completed"] for c in contexts for r in c["rows"]),"results_sha256":file_hash(output/"results.jsonl")})
    print(json.dumps({"complete":True,"output":str(output),"contexts":len(contexts)}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="mode",required=True)
    for mode in ("inventory","train","fresh","evaluate"):
        p=sub.add_parser(mode);p.add_argument("--study",required=True);p.add_argument("--out",required=True)
        if mode in ("fresh","evaluate"):p.add_argument("--frozen",required=True)
        if mode=="evaluate":p.add_argument("--data",required=True)
        if mode in ("train","evaluate"):p.add_argument("--workers",type=int,default=8)
    a=parser.parse_args()
    if hasattr(a,"workers") and not 1<=a.workers<=32:raise ValueError("Workers must be 1..32")
    if a.mode=="inventory":run_inventory(a.study,a.out)
    elif a.mode=="train":run_train(a.study,a.out,a.workers)
    elif a.mode=="fresh":run_fresh(a.study,a.frozen,a.out)
    else:run_evaluate(a.study,a.frozen,a.data,a.out,a.workers)


if __name__=="__main__":main()
