"""Frozen-AST paired timing extension on saved SNAP or fresh scheduling inputs.

No graph/program generation, selection, conditional oracle, or native solver.
The original confirmatory runner is unchanged. Source/config/data/freeze bytes
are archived before workers begin, and failures remain no-schedule rows.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import time
import zipfile

from .compiled import schedule_compiled
from .graph_features import FeatureRuleProgram
from .model import Graph
from .score_heap_v04 import schedule_heap, score_locality


SOURCES = ("__init__.py", "compiled.py", "graph_features.py", "model.py",
           "programs.py", "score_heap_v04.py", "heap_study_v04.py")


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False)+"\n", encoding="utf-8")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class CPUExceeded(TimeoutError):
    pass


class CPUMeter(dict):
    def __init__(self, seconds):
        super().__init__()
        self.deadline = time.process_time()+seconds
        self.writes = 0

    def __setitem__(self, key, value):
        self.writes += 1
        if self.writes % 128 == 0 and time.process_time() > self.deadline:
            raise CPUExceeded("Cooperative process-CPU target exceeded")
        return super().__setitem__(key, value)


def validate_config(config):
    protocol = (config.get("version"), config.get("program_cpu_seconds"))
    if (protocol not in {("fixed_ast_heap_execution_extension_v04", 5),
                         ("fixed_ast_heap_execution_extension_v04_30s", 30)}
            or config.get("repetitions") != 3
            or config.get("score_slice") is not True
            or config.get("selection_permitted") is not False
            or config.get("backends") != ["full_scan", "heap"]
            or config.get("program_arms") != {"primary":"guided_v04", "degree":"baseline"}
            or config.get("expected_contexts") != {"public":8, "test":456}):
        raise ValueError("Require the fixed heap-extension protocol without outcome selection")
    hashes = [config.get("train_freeze_sha256")]
    hashes += list(config.get("input_sha256", {}).values())
    hashes += list(config.get("program_sha256", {}).values())
    if (set(config.get("input_sha256", {})) != {"public", "test"}
            or set(config.get("program_sha256", {})) != {"primary", "degree"}
            or any(not isinstance(h, str) or len(h) != 64
                   or any(c not in "0123456789abcdef" for c in h) for h in hashes)):
        raise ValueError("Require pinned input, TRAIN freeze and program byte hashes")
    return config


def normalise_contexts(data):
    contexts = []
    if "public" in data:
        population = "public"
        for r in data["public"]:
            contexts.append({"id":r["id"]+":graph", "pair_id":r["id"], "side":"graph",
                "split":"public", "family":r["family"], "cluster":str(r.get("cluster",r["id"])),
                "graph":r["graph"], "fixed":list(r.get("fixed",())), "excluded":list(r.get("excluded",()))})
    else:
        population = "test"
        if "test" not in data:
            raise ValueError("Fresh saved input must contain the declared test population")
        for r in data["test"]:
            cluster = r.get("source",{}).get("seed")
            for side in ("left", "right"):
                contexts.append({"id":r["id"]+":"+side, "pair_id":r["id"], "side":side,
                    "split":"test", "family":r["family"], "cluster":str(cluster) if cluster is not None else r["id"],
                    "graph":r[side], "fixed":list(r.get("fixed",())), "excluded":list(r.get("excluded",()))})
    if len({c["id"] for c in contexts}) != len(contexts):
        raise ValueError("Duplicate saved context identity")
    for c in contexts:
        Graph.from_dict(c["graph"]).available(c["fixed"],c["excluded"])
    return population, sorted(contexts,key=lambda c:c["id"])


def execute_backend(graph, source, backend, fixed, excluded, seconds):
    start, cpu = time.perf_counter(), time.process_time()
    common = {"backend":backend, "program_name":source["name"], "program_sha256":digest(source),
              "declared_cpu_seconds":seconds, "score_slice":True, "fallback_used":False}
    try:
        meter = CPUMeter(seconds)
        program = FeatureRuleProgram.from_dict(source)
        if backend == "full_scan":
            result = schedule_compiled(graph,program,fixed,excluded,meter=meter,score_slice=True)
        elif backend == "heap":
            result = schedule_heap(graph,program,fixed,excluded,meter=meter)
        else:
            raise ValueError("Unknown paired execution backend")
        selected = result["selected"]
        if not graph.feasible(selected) or not set(fixed) <= set(selected) or set(selected)&set(excluded):
            raise ValueError("Returned schedule fails graph/boundary feasibility")
        exact = sum((Fraction(graph.nodes[v].weight) for v in selected),Fraction(0))
        if result["value"] != graph.value(selected):
            raise ValueError("Returned reward differs from original graph")
        row = {**result, **common, "completed":True, "status":"checked_feasible_schedule",
               "value_exact":str(exact), "locality":score_locality(program),
               "score_evaluations":sum(r["remaining_count"] for r in result["trace"]) if backend == "full_scan" else result["score_heap"]["score_evaluations"]}
    except Exception as error:
        row = {**common, "completed":False, "selected":None, "value":None, "value_exact":None,
               "trace":None, "feasible":None, "feature_work":None, "score_evaluations":None,
               "status":"CPU_budget_exceeded" if isinstance(error,CPUExceeded) else "execution_exception",
               "error":{"type":type(error).__name__, "message":str(error)}}
    row.update(cpu_seconds=time.process_time()-cpu, seconds=time.perf_counter()-start)
    return row


def backend_order(context_index, repetition, program_index):
    return ["full_scan", "heap"] if (context_index+repetition+program_index)%2 == 0 else ["heap", "full_scan"]


def process_context(task):
    context, index, programs, config, source_hashes = task
    for name, expected in source_hashes.items():
        if sha256((Path(__file__).parent/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Execution source changed after freeze: "+name)
    graph = Graph.from_dict(context["graph"])
    rows, parity = [], []
    names = list(config["program_arms"])
    for rep in range(config["repetitions"]):
        for arm in (names if (index+rep)%2 == 0 else list(reversed(names))):
            pindex = names.index(arm)
            paired = {}
            for position,backend in enumerate(backend_order(index,rep,pindex)):
                row = execute_backend(graph,programs[arm],backend,context["fixed"],context["excluded"],config["program_cpu_seconds"])
                row.update(arm=arm, repetition=rep, sequence=len(rows), pair_position=position)
                rows.append(row); paired[backend] = row
            full, heap = paired["full_scan"],paired["heap"]
            both = full["completed"] and heap["completed"]
            equal = all(full[k] == heap[k] for k in ("trace","selected","value","value_exact")) if both else None
            parity.append({"arm":arm, "repetition":rep, "both_completed":both,
                "exact_trace_selection_value_parity":equal,
                "full_over_heap_cpu":full["cpu_seconds"]/heap["cpu_seconds"] if both and heap["cpu_seconds"] > 0 else None,
                "full_over_heap_work":full["feature_work"]/heap["feature_work"] if both and heap["feature_work"] > 0 else None,
                "score_evaluations_saved":full["score_evaluations"]-heap["score_evaluations"] if both else None,
                "failed_backends":[b for b in config["backends"] if not paired[b]["completed"]]})
    return {**{k:v for k,v in context.items() if k!="graph"}, "n":len(graph.nodes), "m":len(graph.edges),
            "graph_sha256":graph.digest(), "runs":rows, "paired":parity, "selection_permitted":False}


def run(data_path, frozen_path, config_path, output, workers=1):
    config_bytes, frozen_bytes, data_bytes = (Path(p).read_bytes() for p in (config_path,frozen_path,data_path))
    config = validate_config(json.loads(config_bytes))
    frozen = json.loads(frozen_bytes)
    if sha256(frozen_bytes).hexdigest() != config["train_freeze_sha256"]:
        raise ValueError("TRAIN freeze bytes differ from prespecified extension")
    if frozen.get("test_accessed") is not False or frozen.get("selection_split") != "train":
        raise ValueError("Require immutable TRAIN-only program freeze")
    programs = {arm:frozen["programs"][source] for arm,source in config["program_arms"].items()}
    if programs["degree"]["name"] != config["required_degree_name"]:
        raise ValueError("Degree comparator differs from declared frozen arm")
    for p in programs.values(): FeatureRuleProgram.from_dict(p)
    if {k:digest(v) for k,v in programs.items()} != config["program_sha256"]:
        raise ValueError("Executed AST differs from the frozen primary/degree programs")
    population, contexts = normalise_contexts(json.loads(data_bytes))
    if sha256(data_bytes).hexdigest() != config["input_sha256"][population]:
        raise ValueError("Saved input bytes differ from prespecified extension")
    if len(contexts) != config["expected_contexts"][population]:
        raise ValueError("Saved population count differs from prespecified extension")
    if not isinstance(workers,int) or workers < 1: raise ValueError("Workers must be a positive integer")
    root = Path(output); root.mkdir(parents=True,exist_ok=False)
    (root/"config.json").write_bytes(config_bytes)
    (root/"data.json").write_bytes(data_bytes)
    (root/"frozen_programs.json").write_bytes(frozen_bytes)
    write(root/"executed_programs.json",programs)
    source_hashes = {name:sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in SOURCES}
    # This source package is completed before any timing worker starts.
    with zipfile.ZipFile(root/"source_snapshot.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCES: archive.write(Path(__file__).parent/name,"cipheur/"+name)
        archive.writestr("config.json",config_bytes)
        archive.writestr("frozen_programs.json",frozen_bytes)
    write(root/"execution.json",{"scope":config["scope"], "population":population, "contexts":len(contexts),
        "repetitions":config["repetitions"], "runs_per_context":12, "workers":workers,
        "input_path":str(data_path), "input_sha256":sha256(data_bytes).hexdigest(),
        "config_sha256":sha256(config_bytes).hexdigest(), "train_freeze_sha256":sha256(frozen_bytes).hexdigest(),
        "candidate_bank_sha256":frozen["candidate_bank_sha256"], "source_sha256":source_hashes,
        "source_snapshot_sha256":sha256((root/"source_snapshot.zip").read_bytes()).hexdigest(),
        "program_sha256":{k:digest(v) for k,v in programs.items()}, "selection_permitted":False,
        "original_confirmatory_runner_modified":False, "python":sys.version,
        "platform":platform.platform(), "processor":platform.processor(),
        "budget_scope":config["budget_scope"], "timing_scope":"AST parse, evaluator/compiler/heap initialization, scoring, updates, final graph verification",
        "failure_policy":config["failure_policy"]})
    tasks = [(c,i,programs,config,source_hashes) for i,c in enumerate(contexts)]
    counts, parity_failures, processed, hasher = Counter(),0,0,sha256()
    with ProcessPoolExecutor(max_workers=workers) as pool, (root/"results.jsonl").open("w",encoding="utf-8",newline="") as stream:
        for future in as_completed([pool.submit(process_context,t) for t in tasks]):
            result = future.result(); processed += 1
            line = json.dumps(result,ensure_ascii=False,allow_nan=False)+"\n"
            stream.write(line); stream.flush(); hasher.update(line.encode("utf-8"))
            for row in result["runs"]: counts[row["arm"]+"/"+row["backend"]+"/"+("completed" if row["completed"] else "failed")] += 1
            parity_failures += sum(p["exact_trace_selection_value_parity"] is False for p in result["paired"])
            write(root/"progress.json",{"completed_contexts":processed,"assigned_contexts":len(contexts),"method_counts":dict(counts),"parity_failures":parity_failures})
            print(json.dumps({"completed_contexts":processed,"assigned_contexts":len(contexts),"parity_failures":parity_failures}),flush=True)
    write(root/"complete.json",{"complete":True,"contexts":processed,"runs":processed*12,
        "method_counts":dict(counts),"parity_failures":parity_failures,"results_sha256":hasher.hexdigest(),
        "all_completed_pairs_match":parity_failures == 0,
        "selection_permitted":False,"scope":config["scope"]})
    return {"contexts":processed,"runs":processed*12,"parity_failures":parity_failures}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",required=True); p.add_argument("--frozen",required=True)
    p.add_argument("--config",default="configs/heap_extension_v04.json")
    p.add_argument("--out",required=True); p.add_argument("--workers",type=int,default=1)
    args = p.parse_args()
    result = run(args.data,args.frozen,args.config,args.out,args.workers)
    return int(result["parity_failures"] != 0)


if __name__ == "__main__": raise SystemExit(main())
