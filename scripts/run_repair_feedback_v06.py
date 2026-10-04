"""Frozen TRAIN-only Degree feedback for the shared V06 repair kernel.

Prepare binds inputs, exact configuration and runtime sources before execution.
Run verifies that receipt. Mixed input inventories are allowed, but only rows
explicitly marked train are materialized or executed. No programme selection,
TEST execution, conditional oracle, native solver or LLM call is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE_NAMES = ("cipheur/__init__.py", "cipheur/model.py", "cipheur/programs.py",
                "cipheur/graph_features.py", "cipheur/compiled.py", "cipheur/repair_v06.py",
                "scripts/run_repair_feedback_v06.py")
# Capture before importing the runtime: later receipt checks refuse files
# changed after startup instead of blessing new bytes with already loaded code.
STARTUP_SOURCE_SHA256 = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_NAMES}
from cipheur.model import Graph
from cipheur.repair_v06 import RepairConfig, repair_schedule

SECONDS = 0.5
CLOCK = "wall"
CONFIG = RepairConfig(max_patch_vertices=24, max_destroy=4, max_patches=32,
                      expansion_steps=1, node_budget_per_patch=128,
                      max_search_nodes=4096, max_work=200000,
                      upper_pruning=True, policy_scope="branch")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(obj):
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def runtime_sources():
    current = {name: digest(ROOT / name) for name in SOURCE_NAMES}
    if current != STARTUP_SOURCE_SHA256:
        raise ValueError("Runtime source files changed after process startup/import")
    return current


def write(path, obj):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def train_contexts(data, split="train"):
    """Normalize TRAIN identities without materializing any other split graph."""
    if split != "train":
        raise ValueError("Repair authoring feedback is restricted to split=train")
    if not isinstance(data, dict):
        raise ValueError("Input must be an explicit split-bearing data object")
    if "train" in data:
        records, inferred = data["train"], True
    elif "records" in data:
        records, inferred = data["records"], False
    elif "contexts" in data:
        records, inferred = data["contexts"], data.get("split") == "train"
    else:
        raise ValueError("Expected train, records or contexts graph-record list")
    if not isinstance(records, list):
        raise ValueError("Graph-record inventory must be a list")
    selected = []
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Every graph record must be an object")
        row_split = row.get("split", "train" if inferred else None)
        if row_split not in ("train", "validation", "test", "public"):
            raise ValueError("Each record requires a recognized explicit split")
        if inferred and row_split != "train":
            raise ValueError("Contradictory split inside the TRAIN inventory")
        if row_split != "train":
            continue
        if not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("Every TRAIN graph needs a nonempty string identity")
        sides = ("graph",) if "graph" in row else ("left", "right")
        for side in sides:
            if not isinstance(row.get(side), dict):
                raise ValueError("Every TRAIN context requires a serialized graph")
            identity = row["id"] if side == "graph" else row["id"] + ":" + side
            selected.append({"id": identity, "pair_id": row.get("pair_id", row.get("pair", row["id"])),
                "side": row.get("side", side), "split": "train",
                "family": row.get("family", "unspecified"), "cluster": row.get("cluster", row["id"]),
                "graph": row[side], "fixed": row.get("fixed", []), "excluded": row.get("excluded", []),
                "declared_graph_digest": (row.get("graph_digest", row.get("graph_sha256"))
                                          if side == "graph" else row.get(side + "_graph_digest"))})
    if not selected or len({c["id"] for c in selected}) != len(selected):
        raise ValueError("TRAIN context identities must be nonempty and unique")
    return sorted(selected, key=lambda c: c["id"])


def prepare(data_path, output, workers, split="train"):
    data_path, output = Path(data_path), Path(output)
    if type(workers) is not int or not 1 <= workers <= 64:
        raise ValueError("workers must be an integer between 1 and 64")
    input_bytes = data_path.read_bytes()
    contexts = train_contexts(json.loads(input_bytes), split)
    identities = []
    for context in contexts:
        graph = Graph.from_dict(context["graph"])
        graph.available(context["fixed"], context["excluded"])
        graph_digest = graph.digest()
        if (context["declared_graph_digest"] is not None and
                context["declared_graph_digest"] != graph_digest):
            raise ValueError("Declared TRAIN graph identity does not match serialized graph")
        context["graph_sha256"] = graph_digest
        identities.append({"id": context["id"], "graph_sha256": graph_digest,
                           "fixed": context["fixed"], "excluded": context["excluded"]})
    protocol = {"version": "repair_degree_feedback_v06_001", "split": "train",
        "before_any_feedback_execution": True, "method": "shared_kernel_degree",
        "priority": "degree", "random_seed": 1, "workers": workers,
        "declared_seconds": SECONDS, "deadline_clock": CLOCK, "repair_config": asdict(CONFIG),
        "contexts": len(contexts), "context_identity_sha256": canonical_hash(identities),
        "input_sha256": sha256(input_bytes).hexdigest(),
        "selected_contexts_sha256": canonical_hash(contexts),
        "family_counts": dict(Counter(c["family"] for c in contexts)),
        "source_sha256": runtime_sources(),
        "scope": "TRAIN-only shared Degree repair feedback; no selection or TEST execution",
        "quality": "Exact feasible incumbent reward; no optimum-normalized percentage claimed",
        "timing_scope": "Kernel .5 wall-second cooperative target starts before parsing/init; graph reconstruction separately measured. Actual CPU/wall and overshoot retained.",
        "status_scope": "All assigned rows retained. Budget caps are normal anytime termination; programme/runner errors explicit. Completed assignment is not an optimum proof or uncapped schedule completion.",
        "reuse": "All subsequent authoring arms must reuse this exact repair configuration, deadline clock and target before new feedback outcomes.",
        "oracle_calls": 0, "online_model_calls": 0}
    output.mkdir(parents=True, exist_ok=False)
    write(output / "training_contexts.json", {"contexts": contexts})
    write(output / "protocol.json", protocol)
    write(output / "freeze_receipt.json", {"version": protocol["version"],
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "before_any_feedback_execution": True, "protocol_sha256": digest(output / "protocol.json"),
        "training_contexts_sha256": digest(output / "training_contexts.json"),
        "source_sha256": protocol["source_sha256"], "input_sha256": protocol["input_sha256"]})
    return protocol


def verify_prepared(data_path, output, workers, split="train"):
    if split != "train":
        raise ValueError("Repair authoring feedback is restricted to split=train")
    output = Path(output)
    receipt = json.loads((output / "freeze_receipt.json").read_text(encoding="utf-8"))
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    if receipt["before_any_feedback_execution"] is not True:
        raise ValueError("Feedback requires a pre-execution source/config freeze")
    for name in ("protocol", "training_contexts"):
        if digest(output / (name + ".json")) != receipt[name + "_sha256"]:
            raise ValueError("Prepared feedback bytes changed: " + name)
    if digest(data_path) != receipt["input_sha256"]:
        raise ValueError("Original input bytes changed after feedback freeze")
    if protocol["workers"] != workers or protocol["split"] != "train":
        raise ValueError("Execution workers/split differ from frozen feedback protocol")
    if (protocol["repair_config"] != asdict(CONFIG) or protocol["declared_seconds"] != SECONDS
            or protocol["deadline_clock"] != CLOCK):
        raise ValueError("Execution configuration differs from the fixed feedback contract")
    if receipt["source_sha256"] != protocol["source_sha256"]:
        raise ValueError("Conflicting frozen source inventories")
    if runtime_sources() != receipt["source_sha256"]:
        raise ValueError("Loaded startup source differs from the frozen feedback runtime")
    for name, expected in receipt["source_sha256"].items():
        if name not in SOURCE_NAMES or digest(ROOT / name) != expected:
            raise ValueError("Feedback runtime source changed: " + name)
    if set(receipt["source_sha256"]) != set(SOURCE_NAMES):
        raise ValueError("Feedback source inventory incomplete")
    contexts = json.loads((output / "training_contexts.json").read_text(encoding="utf-8"))["contexts"]
    if (len(contexts) != protocol["contexts"] or canonical_hash(contexts) != protocol["selected_contexts_sha256"]
            or any(c["split"] != "train" for c in contexts)):
        raise ValueError("Frozen TRAIN execution identities changed")
    return protocol, contexts


def execute_context(context):
    started_cpu, started_wall = time.process_time(), time.perf_counter()
    row = {k: context[k] for k in ("id", "pair_id", "side", "split", "family", "cluster", "graph_sha256")}
    row.update(method="shared_kernel_degree", fixed=context["fixed"], excluded=context["excluded"])
    try:
        if context["split"] != "train":
            raise ValueError("Worker refuses a non-TRAIN execution target")
        graph = Graph.from_dict(context["graph"])
        if graph.digest() != context["graph_sha256"]:
            raise ValueError("Worker graph identity mismatch")
        row.update(n=len(graph.nodes), m=len(graph.edges),
                   graph_materialization_cpu_seconds=time.process_time() - started_cpu,
                   graph_materialization_wall_seconds=time.perf_counter() - started_wall)
        row["result"] = repair_schedule(graph, priority="degree", fixed=context["fixed"],
            excluded=context["excluded"], seconds=SECONDS, clock=CLOCK, config=CONFIG, random_seed=1)
        row["assignment_returned"] = True
    except Exception as failure:
        row.update(assignment_returned=True, result=None,
                   runner_error={"type": type(failure).__name__, "message": str(failure)})
    row.update(task_cpu_seconds=time.process_time() - started_cpu,
               task_wall_seconds=time.perf_counter() - started_wall)
    return row


def run(data_path, output, workers, split="train"):
    output = Path(output)
    protocol, contexts = verify_prepared(data_path, output, workers, split)
    results = output / "results.jsonl"
    if results.exists() or (output / "completion.json").exists():
        raise ValueError("Preserve existing feedback output; use a new frozen run directory")
    started = time.perf_counter()
    counts, statuses = Counter(), Counter()
    with results.open("x", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(execute_context, c): c for c in contexts}
            for future in as_completed(futures):
                context = futures[future]
                try:
                    row = future.result()
                except Exception as failure:
                    row = {k: context[k] for k in ("id", "split", "family", "graph_sha256")}
                    row.update(method="shared_kernel_degree", assignment_returned=True, result=None,
                        runner_error={"type": type(failure).__name__, "message": str(failure)})
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                counts["returned"] += 1
                result = row.get("result")
                counts["runner_errors"] += result is None
                if result is not None:
                    counts["kernel_completed"] += result["completed"]
                    counts["kernel_errors"] += not result["completed"]
                    counts["feasible_incumbents"] += result["feasible"]
                    counts["initialization_complete"] += result["initialization_complete"]
                    counts["budget_exhausted"] += result["budget_exhausted"]
                    statuses[result["status"]] += 1
                else:
                    statuses["runner_error"] += 1
                write(output / "progress.json", {"assigned": len(contexts), **dict(counts),
                      "status_counts": dict(statuses), "wall_seconds": time.perf_counter() - started})
    completion = {"version": protocol["version"], "split": "train", "assigned": len(contexts),
        **dict(counts), "all_assignments_returned": counts["returned"] == len(contexts),
        "status_counts": dict(statuses), "wall_seconds": time.perf_counter() - started,
        "protocol_sha256": digest(output / "protocol.json"), "results_sha256": digest(results),
        "source_sha256": protocol["source_sha256"], "python": platform.python_version(),
        "platform": platform.platform(), "test_executions": 0, "programme_selection": False,
        "scope": "Assignment completion does not imply solver optimality or initialization completion"}
    write(output / "completion.json", completion)
    return completion


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--split", default="train")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.split != "train":
        parser.error("Only TRAIN feedback is authorized")
    if not args.run:
        receipt = prepare(args.data, args.out, args.workers, args.split)
    if not args.prepare_only:
        receipt = run(args.data, args.out, args.workers, args.split)
    print(json.dumps(receipt, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
