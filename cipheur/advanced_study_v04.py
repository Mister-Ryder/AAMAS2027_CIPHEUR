"""Frozen advanced MWIS comparison on saved public or scheduling inputs.

This module never generates or selects a programme or instance. Published
solvers use three prespecified seeds, with mean-of-three (including failures)
as the primary stochastic comparison. A checked clique partition supplies a
formal upper bound; a floating HiGHS dual is retained separately, not promoted
to a certificate. Every failed run stays an explicit no-schedule row.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time
import warnings

from .advanced_baselines import run_solver
from .compiled import schedule_compiled
from .graph_features import FeatureRuleProgram
from .model import Graph
from .oracle import clique_cover_upper, exact_value, greedy_clique_cover, outward
from .scale_study import methods
from .source_audit import check_source_graph
from .strong_baselines import swap_search

SOLVERS = ("CHILS", "M2WIS", "Struction", "WeightedBR")
SEEDS = (1, 2, 3)


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")


def finite(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


class ProgramCPUExceeded(TimeoutError):
    pass


class CPUMeter(dict):
    """Cooperative CPU guard; observed time and possible overshoot are logged."""
    def __init__(self, seconds):
        super().__init__()
        self.deadline = time.process_time() + seconds
        self.writes = 0

    def __setitem__(self, key, value):
        self.writes += 1
        if self.writes % 128 == 0 and time.process_time() > self.deadline:
            raise ProgramCPUExceeded("Declared constructive CPU budget exceeded")
        return super().__setitem__(key, value)


def _failure(method, kind, status, error=None, **metadata):
    row = {"method": method, "kind": kind, "completed": False,
           "selected": None, "value": None, "value_exact": None,
           "feasible": None, "status": status, "fallback_used": False,
           "exact_optimum_claimed": False, **metadata}
    if error is not None:
        row["error"] = {"type": type(error).__name__, "message": str(error)}
    return row


def _verify(graph, selected, fixed, excluded):
    if (not isinstance(selected, (list, tuple)) or not graph.feasible(selected)
            or not set(fixed) <= set(selected) or set(selected) & set(excluded)):
        raise ValueError("Returned set fails original graph/fixed/excluded feasibility")
    return {"selected": sorted(selected), "value": graph.value(selected),
            "value_exact": str(exact_value(graph, selected)), "feasible": True}


def _published(graph, fixed, excluded, name, executable, seconds, seed, hard_wall):
    start, cpu = time.perf_counter(), time.process_time()
    common = {"seed": seed, "declared_seconds": seconds, "hard_wall_seconds": hard_wall,
              "executable": str(executable), "threads_declared": 1}
    try:
        raw = run_solver(graph, executable, name, fixed, excluded,
                         seconds=seconds, seed=seed, hard_wall_seconds=hard_wall)
    except Exception as error:
        status = "input_encoding_failure" if "integer scaling" in str(error).lower() else "adapter_exception"
        return _failure(name, "published", status, error,
            **common, seconds=time.perf_counter() - start,
            adapter_cpu_seconds=time.process_time() - cpu)
    if not raw.get("completed"):
        return {**raw, **_failure(name, "published", raw.get("status", "solver_failure"),
            **common, seconds=raw.get("seconds", time.perf_counter() - start)),
            "adapter_result": raw}
    try:
        checked = _verify(graph, raw.get("selected"), fixed, excluded)
    except Exception as error:
        return _failure(name, "published", "returned_selection_invalid", error,
            **common, seconds=time.perf_counter() - start, adapter_result=raw)
    return {**raw, **common, **checked, "kind": "published", "completed": True,
            "fallback_used": False, "exact_optimum_claimed": False,
            "adapter_cpu_seconds": time.process_time() - cpu}


def _constructive(graph, fixed, excluded, name, source, kind, seconds, *, score_slice=True):
    start, cpu = time.perf_counter(), time.process_time()
    result = None
    common = {"program_name": source["name"], "declared_cpu_seconds": seconds,
              "score_slice": score_slice, "threads_declared": 1}
    try:
        result = schedule_compiled(graph, FeatureRuleProgram.from_dict(source), fixed,
            excluded, meter=CPUMeter(seconds), score_slice=score_slice)
        checked = _verify(graph, result["selected"], fixed, excluded)
        row = {"method": name, "kind": kind, "completed": True,
               "status": "checked_feasible_constructive", "fallback_used": False,
               "exact_optimum_claimed": False, **result, **checked, **common}
    except Exception as error:
        row = _failure(name, kind, "CPU_budget_exceeded" if isinstance(error, ProgramCPUExceeded)
                       else "constructive_exception", error, **common)
        if result is not None:
            row["returned_result"] = result
    row.update(cpu_seconds=time.process_time() - cpu, seconds=time.perf_counter() - start)
    return row


def _local(graph, fixed, excluded, classical, seconds):
    completed = [row for row in classical if row["completed"]]
    if not completed:
        return _failure("fixed_classical_1to2_search", "local_search",
                        "no_completed_classical_initialization", seconds=0.0,
                        declared_seconds=seconds)
    initial = min(completed, key=lambda row: (-Fraction(row["value_exact"]), row["method"]))
    start, cpu = time.perf_counter(), time.process_time()
    try:
        raw = swap_search(graph, initial["selected"], fixed, excluded, seconds=seconds)
        checked = _verify(graph, raw["selected"], fixed, excluded)
        row = {"method": "fixed_classical_1to2_search", "kind": "local_search",
               "completed": True, "status": "checked_feasible_incumbent",
               "fallback_used": False, "exact_optimum_claimed": False, **raw, **checked}
    except Exception as error:
        row = _failure("fixed_classical_1to2_search", "local_search", "local_search_exception", error)
    return {**row, "initial_method": initial["method"], "declared_seconds": seconds,
            "seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu,
            "initialization_scope": "best completed fixed classical comparator only"}


def _milp_result(graph, fixed, excluded, result, seconds, warning_messages=()):
    """Verify a numerical solver result without synthesizing an incumbent."""
    dual = finite(getattr(result, "mip_dual_bound", None))
    common = {"declared_seconds": seconds, "threads_declared": 1,
              "scope": "floating_HiGHS_MILP_comparator; numerical dual is not a formal certificate"}
    metadata = {**common, "solver_status": int(result.status), "solver_message": str(result.message),
        "mip_gap": finite(getattr(result, "mip_gap", None)),
        "mip_node_count": finite(getattr(result, "mip_node_count", None)),
        "numerical_dual_bound": dual,
        "numerical_upper": graph.value(fixed) - dual if dual is not None else None,
        "warnings": list(warning_messages)}
    if result.x is None:
        return _failure("HiGHS_MILP", "numerical_reference", "no_solver_incumbent", **metadata)
    nodes = sorted(graph.available(fixed, excluded))
    if len(result.x) != len(nodes) or not all(math.isfinite(float(x)) for x in result.x):
        raise ValueError("MILP incumbent has inconsistent dimensions or nonfinite values")
    selected = list(fixed) + [v for v, x in zip(nodes, result.x) if x > .5]
    checked = _verify(graph, selected, fixed, excluded)
    return {"method": "HiGHS_MILP", "kind": "numerical_reference", "completed": True,
            "status": "checked_feasible_incumbent", "fallback_used": False,
            "exact_optimum_claimed": False, **metadata, **checked}


def _milp(graph, fixed, excluded, seconds):
    """Keep absent incumbents absent; preserve floating duals as numerical only."""
    start, cpu = time.perf_counter(), time.process_time()
    common = {"declared_seconds": seconds, "threads_declared": 1,
              "scope": "floating_HiGHS_MILP_comparator; numerical dual is not a formal certificate"}
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import csc_matrix
        nodes = sorted(graph.available(fixed, excluded))
        if not nodes:
            return {"method": "HiGHS_MILP", "kind": "numerical_reference",
                "completed": True, "status": "empty_residual_without_solver",
                **_verify(graph, list(fixed), fixed, excluded), **common,
                "solver_status": None, "numerical_upper": graph.value(fixed),
                "numerical_dual_bound": None, "fallback_used": False,
                "exact_optimum_claimed": False, "seconds": time.perf_counter() - start,
                "cpu_seconds": time.process_time() - cpu}
        index = {v: i for i, v in enumerate(nodes)}
        rows, columns, values, count = [], [], [], 0
        for a, b in sorted(graph.edges):
            if a in index and b in index:
                rows.extend((count, count)); columns.extend((index[a], index[b]))
                values.extend((1., 1.)); count += 1
        matrix = csc_matrix((values, (rows, columns)), shape=(count, len(nodes)))
        constraints = LinearConstraint(matrix, -np.inf, np.ones(count)) if count else None
        with warnings.catch_warnings(record=True) as messages:
            warnings.simplefilter("always")
            result = milp(-np.asarray([graph.nodes[v].weight for v in nodes]),
                integrality=np.ones(len(nodes)), bounds=Bounds(0, 1), constraints=constraints,
                options={"time_limit": seconds, "mip_rel_gap": 1e-7, "threads": 1})
        row = _milp_result(graph, fixed, excluded, result, seconds, [str(w.message) for w in messages])
    except Exception as error:
        row = _failure("HiGHS_MILP", "numerical_reference", "MILP_exception", error, **common)
    return {**row, "seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu}


def _formal_upper(graph, fixed, excluded):
    start = time.perf_counter()
    active = graph.available(fixed, excluded)
    cover = greedy_clique_cover(graph, active)
    upper = exact_value(graph, fixed) + clique_cover_upper(graph, active, cover)
    return {"formal_upper_exact": str(upper), "formal_upper": outward(upper, 1),
            "formal_upper_method": "verified_weighted_clique_partition_plus_fixed",
            "clique_partition": [list(c) for c in cover], "coverage_edges_and_disjointness_checked": True,
            "seconds": time.perf_counter() - start}


def summaries(rows, upper_exact):
    """No best-of-three statistic enters the declared stochastic primary."""
    upper = Fraction(upper_exact) if upper_exact is not None else None
    for row in rows:
        row["quality_to_formal_upper"] = (float(Fraction(row["value_exact"]) / upper)
            if row["completed"] and upper else 1.0 if row["completed"] and upper == 0
            else 0.0 if not row["completed"] and upper is not None else None)
    result = {}
    for method in sorted({row["method"] for row in rows}):
        group = [row for row in rows if row["method"] == method]
        completed = [row for row in group if row["completed"]]
        published = group[0]["kind"] == "published"
        result[method] = {"kind": group[0]["kind"], "requested_runs": len(group),
            "completed_runs": len(completed), "failed_runs": len(group) - len(completed),
            "completion_rate": len(completed) / len(group),
            "primary_reward_mean_zero_accounted": statistics.fmean(row["value"] if row["completed"] else 0 for row in group),
            "completed_only_reward_mean": statistics.fmean(row["value"] for row in completed) if completed else None,
            "primary_quality_mean_zero_accounted": statistics.fmean(row["quality_to_formal_upper"] for row in group) if upper is not None else None,
            "primary_scope": "mean of three fixed seeded runs with failure value zero" if published else "single frozen deterministic/comparator run with failure value zero",
            "seeds": [row["seed"] for row in group] if published else None,
            "exact_optimum_claimed": False}
    return result


def solver_entries(config, phase):
    entries = [(name, config["executables"][name]) for name in SOLVERS]
    if config.get("chils_ils_short") and phase["official_seconds"] == 5:
        entries.append(("CHILS_ILS", config["executables"]["CHILS"]))
    return entries


def _programme_kind(name, config):
    return "additional_prespecified_programme" if name in config.get("_additional_programme_receipts", {}) else "frozen_programme"


def context_task(task):
    context, config, programmes, phase = task
    graph = Graph.from_dict(context["graph"])
    fixed, excluded = context["fixed"], context["excluded"]
    started, rows = time.perf_counter(), []
    for solver, executable in solver_entries(config, phase):
        for seed in SEEDS:
            rows.append(_published(graph, fixed, excluded, solver, executable,
                phase["official_seconds"], seed, phase["hard_wall_seconds"]))
    for name in sorted(programmes):
        rows.append(_constructive(graph, fixed, excluded, name, programmes[name],
                                  _programme_kind(name, config), config["program_cpu_seconds"]))
    for name in config.get("full_interface_programme_ids", []):
        rows.append({**_constructive(graph, fixed, excluded, name + "_full_interface", programmes[name],
            "full_interface_ablation", config["program_cpu_seconds"], score_slice=False), "same_AST_as": name})
    parity = {}
    for name in config.get("full_interface_programme_ids", []):
        sliced = next(row for row in rows if row["method"] == name)
        full = next(row for row in rows if row["method"] == name + "_full_interface")
        complete = sliced["completed"] and full["completed"]
        parity[name] = {"sliced_method": name, "full_method": name + "_full_interface",
            "both_completed": complete, "status": "checked" if complete else "not_assessable_due_to_failure",
            "selection_identical": sliced["selected"] == full["selected"] if complete else None,
            "trace_identical": sliced["trace"] == full["trace"] if complete else None,
            "exact_value_identical": sliced["value_exact"] == full["value_exact"] if complete else None,
            "programme_definition_identical": True, "selection_permitted": False}
    classical = [_constructive(graph, fixed, excluded, "baseline_" + p.name, p.to_dict(),
                              "fixed_classical", config["program_cpu_seconds"])
                 for p in methods()]
    rows.extend(classical)
    rows.append(_local(graph, fixed, excluded, classical, config["local_search_seconds"]))
    numerical = _milp(graph, fixed, excluded, config["milp_seconds"])
    rows.append(numerical)
    try:
        formal = _formal_upper(graph, fixed, excluded)
    except Exception as error:
        formal = {"formal_upper_exact": None, "formal_upper": None,
                  "coverage_edges_and_disjointness_checked": False,
                  "error": {"type": type(error).__name__, "message": str(error)}}
    completed = [row for row in rows if row["completed"]]
    # This boundary is an explicit a-priori feasible witness, never credited as
    # a solver fallback or returned programme schedule.
    lower_witness = max(completed, key=lambda row: Fraction(row["value_exact"]), default=None)
    lower = Fraction(lower_witness["value_exact"]) if lower_witness else exact_value(graph, fixed)
    exact = formal["formal_upper_exact"] is not None and lower == Fraction(formal["formal_upper_exact"])
    reference = {**formal, "best_verified_lower_exact": str(lower), "best_verified_lower": outward(lower, -1),
        "lower_witness": lower_witness["selected"] if lower_witness else list(fixed),
        "lower_witness_method": lower_witness["method"] if lower_witness else "a_priori_fixed_boundary",
        "numerical_upper": numerical.get("numerical_upper"),
        "numerical_upper_below_verified_lower": (numerical.get("numerical_upper") is not None
            and Fraction(numerical["numerical_upper"]) < lower),
        "numerical_solver_status": numerical.get("solver_status"),
        "numerical_dual_is_formal_certificate": False,
        "independent_exact_proof": exact,
        "exact_proof_kind": "exact feasible weight equals independently verified clique upper" if exact else None}
    source = {"applicable": graph.constraints.get("model") == "v51_legacy"}
    if source["applicable"]:
        if not config.get("stable_root"):
            source.update(checked=False, status="source_root_unavailable")
        else:
            try:
                source = check_source_graph(graph, {row["method"] + ":" + str(row.get("seed", "single")): row["selected"]
                    for row in completed}, config["stable_root"])
                source.update(checked=True)
            except Exception as error:
                source.update(checked=False, status="source_audit_failure",
                              error={"type": type(error).__name__, "message": str(error)})
    summary = summaries(rows, formal["formal_upper_exact"])
    return {"id": context["id"], "pair_id": context["pair_id"], "side": context["side"],
        "split": context["split"], "family": context["family"], "cluster": context["cluster"],
        "n": len(graph.nodes), "m": len(graph.edges), "graph_sha256": graph.digest(),
        "fixed": list(fixed), "excluded": list(excluded), "phase": phase,
        "methods": rows, "method_summary": summary, "reference": reference,
        "source_verifier": source, "full_interface_parity": parity, "seconds": time.perf_counter() - started,
        "context_status": "processed_with_method_failures" if any(not r["completed"] for r in rows) else "all_method_runs_completed",
        "selection_permitted": False}


def normalise_contexts(data, splits=None, context_ids=None):
    contexts = []
    if "public" in data:
        if splits not in (None, ["public"]):
            raise ValueError("Public input requires public split")
        for record in data["public"]:
            contexts.append({"id": record["id"] + ":graph", "pair_id": record["id"], "side": "graph",
                "split": "public", "family": record["family"], "cluster": record.get("cluster", record["id"]),
                "graph": record["graph"], "fixed": list(record.get("fixed", ())),
                "excluded": list(record.get("excluded", ()))})
    else:
        splits = ["test"] if splits is None else splits
        if not splits or not set(splits) <= {"test", "validation"}:
            raise ValueError("Saved scheduling inputs require explicitly declared validation/test splits")
        for split in splits:
            if split not in data:
                raise ValueError("Declared split absent from input")
            for record in data[split]:
                cluster = record.get("source", {}).get("seed")
                cluster = str(cluster) if cluster is not None else record["id"]
                for side in ("left", "right"):
                    contexts.append({"id": record["id"] + ":" + side, "pair_id": record["id"], "side": side,
                        "split": split, "family": record["family"], "cluster": cluster,
                        "graph": record[side], "fixed": list(record.get("fixed", ())),
                        "excluded": list(record.get("excluded", ()))})
    ids = [context["id"] for context in contexts]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate input context identity")
    if context_ids is not None:
        if not isinstance(context_ids, list) or len(set(context_ids)) != len(context_ids) or not set(context_ids) <= set(ids):
            raise ValueError("Context filter must be a distinct prespecified subset of input IDs")
        contexts = [c for c in contexts if c["id"] in set(context_ids)]
    for context in contexts:
        Graph.from_dict(context["graph"]).available(context["fixed"], context["excluded"])
    return contexts, len(ids)


def validate_config(config, config_root):
    result = {"official_seconds": 5.0, "hard_wall_seconds": 30.0,
        "program_cpu_seconds": 5.0, "milp_seconds": 10.0, "local_search_seconds": 2.0,
        "score_slice": True, "seeds": list(SEEDS), **config}
    for key, expected in (("official_seconds", 5), ("program_cpu_seconds", 5),
                          ("milp_seconds", 10), ("local_search_seconds", 2)):
        if result[key] != expected:
            raise ValueError("This fixed protocol requires " + key + "=" + str(expected))
    if result["score_slice"] is not True or result["seeds"] != list(SEEDS):
        raise ValueError("Require uniform sliced backend and fixed seeds 1/2/3")
    if type(result.get("chils_ils_short", False)) is not bool:
        raise ValueError("chils_ils_short must be boolean")
    if not math.isfinite(result["hard_wall_seconds"]) or result["hard_wall_seconds"] < 5:
        raise ValueError("Invalid hard wall limit")
    if set(result.get("executables", {})) != set(SOLVERS):
        raise ValueError("Explicit paths for all four official solver names are required")
    executables, receipts = {}, {}
    for name, declaration in result["executables"].items():
        declaration = {"path": declaration} if isinstance(declaration, str) else declaration
        if not isinstance(declaration, dict) or not isinstance(declaration.get("path"), str) or not declaration["path"]:
            raise ValueError("Each executable requires a nonempty native path")
        path = Path(declaration["path"])
        path = path if path.is_absolute() else Path(config_root) / path
        path = path.resolve()
        digest = sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if declaration.get("sha256") is not None and digest != declaration["sha256"]:
            raise ValueError("Executable SHA256 differs from declaration: " + name)
        executables[name] = str(path)
        receipts[name] = {**declaration, "path": str(path), "exists": path.is_file(), "sha256": digest}
    result["executables"] = executables
    long = result.get("long_budget")
    if long is not None:
        if long.get("seconds") != 30 or not isinstance(long.get("context_ids"), list) or not long["context_ids"]:
            raise ValueError("Optional long protocol requires 30 seconds and a nonempty fixed context-ID subset")
        if len(set(long["context_ids"])) != len(long["context_ids"]):
            raise ValueError("Repeated long-subset IDs")
        hard = long.get("hard_wall_seconds", 60)
        if not math.isfinite(hard) or hard < 30:
            raise ValueError("Invalid long hard-wall limit")
    return result, receipts


def _contains_programme(value, programme):
    if isinstance(value, dict):
        if set(value) == {"name", "features", "rule", "rationale"}:
            try:
                if FeatureRuleProgram.from_dict(value).to_dict() == programme:
                    return True
            except ValueError:
                pass
        return any(_contains_programme(child, programme) for child in value.values())
    if isinstance(value, list):
        return any(_contains_programme(child, programme) for child in value)
    return False


def additional_programmes(config, config_root, existing):
    """Verify prespecified extra controls without altering the original freeze."""
    entries = config.get("additional_programmes", [])
    if not isinstance(entries, list):
        raise ValueError("additional_programmes must be an explicit entry list")
    programmes, receipts, payloads = {}, {}, {}
    for entry in entries:
        if not isinstance(entry, dict) or not {"id", "program", "source_receipt"} <= entry.keys():
            raise ValueError("Additional programme needs id, raw program and source_receipt")
        name = entry["id"]
        if not isinstance(name, str) or not name or len(name) > 200 or name in existing or name in programmes:
            raise ValueError("Additional programme identity must be distinct and bounded")
        programme = FeatureRuleProgram.from_dict(entry["program"]).to_dict()
        source = entry["source_receipt"]
        if (not isinstance(source, dict) or not isinstance(source.get("path"), str)
                or not source["path"] or not isinstance(source.get("sha256"), str)):
            raise ValueError("Additional programme requires immutable source path and SHA256")
        path = Path(source["path"])
        path = (path if path.is_absolute() else Path(config_root) / path).resolve()
        payload = path.read_bytes()
        digest = sha256(payload).hexdigest()
        if digest != source["sha256"].lower():
            raise ValueError("Additional programme source SHA256 mismatch: " + name)
        if not _contains_programme(json.loads(payload), programme):
            raise ValueError("Declared source does not contain identical additional programme: " + name)
        programmes[name] = programme
        receipts[name] = {**source, "path": str(path), "sha256": digest,
            "programme_sha256": sha256(json.dumps(programme, sort_keys=True).encode()).hexdigest(),
            "identical_programme_in_source_checked": True,
            "member_of_original_TRAIN_freeze": False,
            "archive_file": "additional_source_" + str(len(receipts)) + ".json"}
        payloads[name] = payload
    return programmes, receipts, payloads


def _worker_setup():
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"


def _worker_failure(context, phase, error, programmes, config):
    planned = [(name, "published", seed) for name, _ in solver_entries(config, phase) for seed in SEEDS]
    planned += [(name, _programme_kind(name, config), None) for name in sorted(programmes)]
    planned += [(name + "_full_interface", "full_interface_ablation", None)
                for name in config.get("full_interface_programme_ids", [])]
    planned += [("baseline_" + p.name, "fixed_classical", None) for p in methods()]
    planned += [("fixed_classical_1to2_search", "local_search", None), ("HiGHS_MILP", "numerical_reference", None)]
    rows = [_failure(name, kind, "worker_failure", error, seed=seed) for name, kind, seed in planned]
    return {"id": context["id"], "pair_id": context["pair_id"], "side": context["side"],
        "split": context["split"], "family": context["family"], "cluster": context["cluster"],
        "graph_sha256": Graph.from_dict(context["graph"]).digest(), "fixed": context["fixed"], "excluded": context["excluded"],
        "phase": phase, "context_status": "worker_failure", "selection_permitted": False,
        "methods": rows, "method_summary": summaries(rows, None),
        "reference": {"independent_exact_proof": False},
        "source_verifier": {"checked": False, "status": "worker_failure"}}


def _phase(root, filename, contexts, config, programmes, phase, workers):
    started, count, failures, failed_contexts = time.perf_counter(), 0, Counter(), 0
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_setup) as pool, (root / (filename + ".jsonl")).open("w", encoding="utf-8") as stream:
        futures = {pool.submit(context_task, (context, config, programmes, phase)): context for context in contexts}
        for future in as_completed(futures):
            try:
                row = future.result()
            except Exception as error:
                row = _worker_failure(futures[future], phase, error, programmes, config)
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            count += 1
            failed = [r for r in row["methods"] if not r["completed"]]
            failures.update(r["method"] for r in failed)
            failed_contexts += bool(failed)
            progress = {"phase": phase, "processed_contexts": count, "requested_contexts": len(contexts),
                        "contexts_with_method_failures": failed_contexts,
                        "failed_method_runs": dict(failures), "seconds": time.perf_counter() - started}
            write(root / ("progress.json" if filename == "results" else filename + "_progress.json"), progress)
            print(json.dumps({"phase": phase["name"], "processed_contexts": count, "requested_contexts": len(contexts)}), flush=True)
    return {"phase": phase, "processed_contexts": count, "requested_contexts": len(contexts),
        "execution_complete": count == len(contexts), "all_requested_methods_completed": not bool(failures),
        "contexts_with_method_failures": failed_contexts, "failed_method_runs": dict(failures),
        "seconds": time.perf_counter() - started,
        "results_sha256": sha256((root / (filename + ".jsonl")).read_bytes()).hexdigest()}


def run(data_path, frozen_path, config_path, output, workers=4):
    if type(workers) is not int or workers < 1:
        raise ValueError("Workers must be a positive integer")
    data_bytes, frozen_bytes, config_bytes = (Path(p).read_bytes() for p in (data_path, frozen_path, config_path))
    frozen = json.loads(frozen_bytes)
    if frozen.get("test_accessed") is not False or frozen.get("selection_split") != "train" or not frozen.get("programs"):
        raise ValueError("Require a nonempty pre-test TRAIN programme freeze")
    config, binaries = validate_config(json.loads(config_bytes), Path(config_path).parent)
    programmes = dict(frozen["programs"])
    if config.get("program_ids") is not None:
        ids = config["program_ids"]
        if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids) or not set(ids) <= programmes.keys():
            raise ValueError("Programme IDs must be a distinct prespecified frozen subset")
        programmes = {name: programmes[name] for name in ids}
    added, additional_receipts, additional_payloads = additional_programmes(config, Path(config_path).parent, frozen["programs"])
    programmes.update(added)
    config["_additional_programme_receipts"] = additional_receipts
    full = config.get("full_interface_programme_ids", [])
    if (not isinstance(full, list) or len(set(full)) != len(full) or not set(full) <= programmes.keys()
            or any(name + "_full_interface" in programmes for name in full)):
        raise ValueError("Full-interface IDs must be a distinct subset of declared programmes with unique method names")
    if any(name.startswith("baseline_") or name in SOLVERS + ("CHILS_ILS", "HiGHS_MILP", "fixed_classical_1to2_search") for name in programmes):
        raise ValueError("Frozen programme method identity collides with comparison methods")
    for source in programmes.values():
        FeatureRuleProgram.from_dict(source)
    contexts, input_count = normalise_contexts(json.loads(data_bytes), config.get("splits"), config.get("context_ids"))
    if not contexts:
        raise ValueError("No requested input contexts; an empty run cannot be called completed comparison")
    long_ids = config.get("long_budget", {}).get("context_ids", [])
    if not set(long_ids) <= {c["id"] for c in contexts}:
        raise ValueError("Long subset must be fixed inside the requested short-budget context set")
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    (root / "data.json").write_bytes(data_bytes)
    (root / "frozen_programs.json").write_bytes(frozen_bytes)
    (root / "original_config.json").write_bytes(config_bytes)
    for name, payload in additional_payloads.items():
        (root / additional_receipts[name]["archive_file"]).write_bytes(payload)
    write(root / "additional_programme_receipts.json", additional_receipts)
    write(root / "config.json", config); write(root / "programs.json", programmes)
    plan = [{k: c[k] for k in ("id", "pair_id", "side", "split", "family", "cluster", "fixed", "excluded")}
            | {"graph_sha256": Graph.from_dict(c["graph"]).digest()} for c in contexts]
    write(root / "context_plan.json", {"input_contexts": input_count, "requested_contexts": len(contexts),
        "filtered_out_contexts": input_count - len(contexts), "contexts": plan,
        "long_context_ids": long_ids, "outcome_filtering_permitted": False})
    write(root / "execution.json", {"python": sys.version, "platform": platform.platform(), "workers": workers,
        "data_sha256": sha256(data_bytes).hexdigest(), "frozen_sha256": sha256(frozen_bytes).hexdigest(),
        "config_sha256": sha256(config_bytes).hexdigest(), "executables": binaries,
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")},
        "additional_programme_receipts": additional_receipts,
        "full_interface_programme_ids": full,
        "full_interface_ablation_scope": "identical declared AST; score_slice=false; no additional selection",
        "chils_ils_short": config.get("chils_ils_short", False),
        "selection_permitted": False, "programme_backend": "schedule_compiled(score_slice=True)",
        "stochastic_primary": "mean three seeds 1/2/3 with failure zero; completed-only mean separate",
        "binary_thread_environment": {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
        "budget_scope": "official 5-second solver budget; constructive 5 CPU seconds cooperative; MILP 10 seconds; local search 2 seconds; not matched total computation",
        "input_freshness": "caller validates input/source exclusion inventory and freeze before execution; no new input generation"})
    short = {"name": "short_5s", "official_seconds": 5, "hard_wall_seconds": config["hard_wall_seconds"]}
    phases = [_phase(root, "results", contexts, config, programmes, short, workers)]
    if long_ids:
        long = {"name": "representative_30s", "official_seconds": 30,
                "hard_wall_seconds": config["long_budget"].get("hard_wall_seconds", 60)}
        selected = [c for c in contexts if c["id"] in set(long_ids)]
        phases.append(_phase(root, "long_results", selected, config, programmes, long, workers))
    write(root / "complete.json", {"execution_complete": all(p["execution_complete"] for p in phases),
        "all_requested_methods_completed": all(p["all_requested_methods_completed"] for p in phases),
        "phases": phases, "selection_permitted": False,
        "interpretation": "execution completion is not solver success, optimality, source-feasibility or a paper-level claim"})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True); parser.add_argument("--frozen", required=True)
    parser.add_argument("--config", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    run(args.data, args.frozen, args.config, args.output, args.workers)


if __name__ == "__main__":
    main()
