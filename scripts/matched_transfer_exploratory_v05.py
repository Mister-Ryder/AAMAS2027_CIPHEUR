"""Exploratory transfer of all twelve TRAIN-frozen V05 winners, without selection.

Prepare verifies immutable context identities and old formal U/feasible L, then
locks the input, protocol and code capsule before run. No synthesis/oracle calls.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.model import Graph
from cipheur.matched_synthesis_v05 import execute, source_receipt
from cipheur.source_audit import check_source_graph

STEM = "matched_transfer_exploratory_v05_001"
ARMS = ("witness", "relations", "objective")
DEGREE = {"name": "fixed_degree_reference", "features": [], "rule": "weight/max(1,degree)", "rationale": "Fixed classical transfer reference"}
PUBLIC = ROOT / "experiments/runs/v04/advanced_public_v04_001.tar.gz"
FRESH = ROOT / "experiments/runs/v04/advanced_fresh_v04_001.tar.gz"
TRAIN = ROOT / "experiments/runs/v05/matched_train_v05_001.tar.gz"
STUDY = ROOT / "experiments/discovery" / STEM
CAPSULE = ROOT / "experiments/source_snapshots/v05" / (STEM + "_source.zip")
CAPSULE_RECEIPT = CAPSULE.with_name(STEM + "_source_receipt.json")
CONFIG = ROOT / "configs/matched_transfer_exploratory_v05.json"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def archive_members(path):
    stem = Path(path).name.removesuffix(".tar.gz")
    with tarfile.open(path, "r:gz") as tar:
        data = json.load(tar.extractfile(stem + "/data.json"))
        rows = [json.loads(x) for x in tar.extractfile(stem + "/results.jsonl") if x.strip()]
    return data, {r["id"]: r for r in rows}


def exact_value(g, selected):
    return sum((Fraction(g.nodes[v].weight) for v in selected), Fraction())


def verify_reference(context):
    g = Graph.from_dict(context["graph"])
    assert g.digest() == context["graph_sha256"]
    f, x, ref = context["fixed"], context["excluded"], context["reference"]
    active = g.available(f, x)
    parts = ref["clique_partition"]
    flattened = [v for part in parts for v in part]
    assert len(flattened) == len(set(flattened)) and set(flattened) == active
    checks = 3
    for part in parts:
        assert part
        for i, a in enumerate(part):
            for b in part[i+1:]:
                assert b in g.adj[a]
                checks += 1
    upper = exact_value(g, f) + sum((max(Fraction(g.nodes[v].weight) for v in part) for part in parts), Fraction())
    assert upper == Fraction(ref["formal_upper_exact"]) and upper > 0
    chosen = ref["lower_witness"]
    assert g.feasible(chosen) and set(f) <= set(chosen) and not set(x).intersection(chosen)
    lower = exact_value(g, chosen)
    assert lower == Fraction(ref["best_verified_lower_exact"]) and 0 < lower <= upper
    return checks + 4


def context(original, graph, source, population):
    keys = ("id", "pair_id", "side", "split", "family", "cluster", "n", "m", "graph_sha256", "fixed", "excluded")
    row = {k: original[k] for k in keys}
    row.update(graph=graph, source=source, population=population, reference={k: original["reference"][k] for k in
        ("formal_upper_exact", "formal_upper_method", "clique_partition", "best_verified_lower_exact", "lower_witness", "lower_witness_method")})
    return row


def prepare():
    if STUDY.exists() or CAPSULE.exists():
        raise ValueError("Preserve the registered study; do not replace it")
    config = load(CONFIG)
    public, public_rows = archive_members(PUBLIC)
    fresh, fresh_rows = archive_members(FRESH)
    contexts = []
    for item in public["public"]:
        population = item["family"] + "_" + item["source"]["weight_mode"]
        contexts.append(context(public_rows[item["id"] + ":graph"], item["graph"], item["source"], population))
    for item in fresh["test"]:
        if item["family"] == "c3":
            for side in ("left", "right"):
                contexts.append(context(fresh_rows[item["id"] + ":" + side], item[side], item["source"], "C3"))
    contexts.sort(key=lambda c: c["id"])
    assert len(contexts) == 120 and len({c["id"] for c in contexts}) == 120
    counts = dict(Counter(c["population"] for c in contexts))
    assert counts == {"DIMACS_unit": 18, "DIMACS_hash_weighted": 18, "SATLIB_unit": 30, "SATLIB_hash_weighted": 30, "C3": 24}, counts
    reference_checks = sum(verify_reference(c) for c in contexts)
    with tarfile.open(TRAIN, "r:gz") as tar:
        frozen_bytes = tar.extractfile("matched_train_v05_001/frozen_programs.json").read()
    frozen = json.loads(frozen_bytes)
    expected = {f"block_{b}_{a}" for b in range(4) for a in ARMS}
    assert set(frozen["programs"]) == set(frozen["selection"]) == expected
    assert frozen["selection_split"] == "train" and not frozen["test_accessed"]
    assert frozen["source_sha256"] == source_receipt()
    STUDY.mkdir(parents=True)
    (STUDY / "frozen_programs.json").write_bytes(frozen_bytes)
    write(STUDY / "data.json", {"contexts": contexts})
    protocol = {"version": STEM, "design": "exploratory post-V05 frozen-program transfer; not a new confirmatory population",
        "before_any_extension_execution": True, "no_authoring_no_test_selection": True, "seed": 1,
        "contexts": 120, "methods_per_context": 13, "assignments": 1560, "population_counts": counts,
        "programs": sorted(expected), "reference_program": DEGREE, "all_assigned_banks_retained": True,
        "backend": "cipheur.matched_synthesis_v05.execute -> schedule_compiled(score_slice=True), unchanged",
        "program_cpu_seconds": config["program_cpu_seconds"], "workers": config["workers"],
        "hard_wall_safety_no_context_progress_seconds": config["hard_wall_safety_no_context_progress_seconds"],
        "budget_scope": "Program parse/compile, evaluator initialization, updates and complete schedule are inside original cooperative CPU meter; graph materialization and source validation recorded separately. Overshoot retained.",
        "execution_order": "Lexical context inventory; per-context sorted 13 method IDs rotated by graph digest, without outcomes; one deterministic schedule per assignment.",
        "hard_wall_policy": "Only if no completed context for 1800 seconds, stop workers and record all unfinished assignments as explicit zero-quality failures; no alternate backend or fallback.",
        "quality": "100*exact feasible reward/pre-existing independently verified formal clique upper U; incomplete assignment is zero. Secondary 100*reward/pre-existing best feasible L may exceed 100. U and L never replaced by these new results.",
        "aggregation": "Five populations separately; per arm report four fixed block means and equal-block mean, completion counts and failure types; common single Degree reference. No deduplication of identical ASTs, no winner reselection, no failure censoring.",
        "scope": "The same 48 public source graphs occur in both unit and deterministic hash-weight variants; the existing 24 C3 contexts are 12 paired source subproblems, not 24 independent fresh satellites. These contexts were observed in V04. Transfer is exploratory.",
        "timing_scope": "Only new same-host 13-method assignments are comparable; archived native V04 baselines and their old-server timings remain a distinct study.",
        "source_archive_sha256": {"public": digest(PUBLIC), "fresh": digest(FRESH), "train": digest(TRAIN)},
        "config_sha256": digest(CONFIG), "frozen_programs_sha256": digest(STUDY / "frozen_programs.json"),
        "data_sha256": digest(STUDY / "data.json"), "pre_execution_reference_checks": reference_checks}
    write(STUDY / "protocol.json", protocol)
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted((ROOT / "cipheur").glob("*.py"))}
    sources[Path(__file__).relative_to(ROOT).as_posix()] = digest(__file__)
    sources[CONFIG.relative_to(ROOT).as_posix()] = digest(CONFIG)
    freeze = {"version": STEM, "before_any_extension_execution": True, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol_sha256": digest(STUDY / "protocol.json"), "data_sha256": protocol["data_sha256"],
        "frozen_programs_sha256": protocol["frozen_programs_sha256"], "source_sha256": sources}
    write(STUDY / "freeze_receipt.json", freeze)
    paths = [ROOT / name for name in sources] + sorted(STUDY.glob("*.json"))
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.relative_to(ROOT).as_posix())
    write(CAPSULE_RECEIPT, {"version": STEM, "before_any_extension_execution": True,
        "source_zip_sha256": digest(CAPSULE), "file_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}})
    print(json.dumps({"protocol_sha256": freeze["protocol_sha256"], "source_zip_sha256": digest(CAPSULE), "contexts": counts, "reference_checks": reference_checks}), flush=True)


def check_freeze():
    protocol, frozen, data, freeze = (load(STUDY / p) for p in ("protocol.json", "frozen_programs.json", "data.json", "freeze_receipt.json"))
    assert freeze["before_any_extension_execution"] is True
    for name in ("protocol", "data", "frozen_programs"):
        assert digest(STUDY / (name + ".json")) == freeze[name + "_sha256"]
    assert frozen["source_sha256"] == source_receipt()
    for path, expected in freeze["source_sha256"].items():
        assert digest(ROOT / path) == expected, path
    receipt = load(CAPSULE_RECEIPT)
    assert receipt["before_any_extension_execution"] is True and digest(CAPSULE) == receipt["source_zip_sha256"]
    with zipfile.ZipFile(CAPSULE) as z:
        assert set(z.namelist()) == set(receipt["file_sha256"])
        for name, expected in receipt["file_sha256"].items():
            assert sha256(z.read(name)).hexdigest() == expected == digest(ROOT / name), name
    return protocol, frozen, data["contexts"]


def failed(method, status, error):
    return {"method": method, "completed": False, "status": status, "error": error,
        "value": None, "value_exact": None, "feature_work": None, "selected": None, "trace": None,
        "cpu_seconds": None, "wall_seconds": None, "actual_assignment_cpu_known": False}


def run_context(task):
    context, programs, seconds = task
    start, cpu = time.perf_counter(), time.process_time()
    graph = Graph.from_dict(context["graph"])
    graph_cpu, graph_wall = time.process_time() - cpu, time.perf_counter() - start
    methods = sorted(programs)
    shift = int(context["graph_sha256"][:8], 16) % len(methods)
    methods = methods[shift:] + methods[:shift]
    rows = [{"method": name, **execute(graph, programs[name], context["fixed"], context["excluded"], seconds)} for name in methods]
    return {"id": context["id"], "population": context["population"], "graph_sha256": graph.digest(), "n": len(graph.nodes), "m": len(graph.edges),
        "graph_materialization_cpu_seconds": graph_cpu, "graph_materialization_wall_seconds": graph_wall,
        "context_cpu_seconds": time.process_time() - cpu, "context_wall_seconds": time.perf_counter() - start,
        "method_order": methods, "rows": rows}


def run(output, stable_root):
    protocol, frozen, contexts = check_freeze()
    output = Path(output)
    if output.exists():
        raise ValueError("Preserve prior run; choose fresh output directory")
    output.mkdir(parents=True)
    for p in STUDY.glob("*.json"):
        shutil.copyfile(p, output / p.name)
    programs = dict(frozen["programs"])
    programs["Degree"] = DEGREE
    started = time.perf_counter()
    source_started, source_cpu = time.perf_counter(), time.process_time()
    source_checks = {}
    for c in contexts:
        if c["population"] == "C3":
            source_checks[c["id"]] = check_source_graph(Graph.from_dict(c["graph"]), {}, stable_root)
    write(output / "execution.json", {"version": STEM, "pid": os.getpid(), "platform": platform.platform(), "python": sys.version,
        "workers": protocol["workers"], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol_sha256": digest(STUDY / "protocol.json"), "source_zip_sha256": digest(CAPSULE),
        "pre_run_C3_reconstruction": source_checks, "source_validation_cpu_seconds": time.process_time()-source_cpu,
        "source_validation_wall_seconds": time.perf_counter()-source_started, "source_validation_budget_separate": True})
    print(json.dumps({"pid": os.getpid(), "output": str(output), "assignments": 1560, "workers": protocol["workers"], "state": "RUNNING"}), flush=True)
    executor = ProcessPoolExecutor(max_workers=protocol["workers"])
    pending = {executor.submit(run_context, (c, programs, protocol["program_cpu_seconds"])): c for c in contexts}
    completed, last_progress, hard_stop = [], time.perf_counter(), False
    with (output / "results.jsonl").open("w", encoding="utf-8") as stream:
        while pending:
            done, _ = wait(pending, timeout=1, return_when=FIRST_COMPLETED)
            if not done and time.perf_counter()-last_progress > protocol["hard_wall_safety_no_context_progress_seconds"]:
                hard_stop = True
                for process in executor._processes.values():
                    process.terminate()
                for future, c in pending.items():
                    r = {"id": c["id"], "population": c["population"], "graph_sha256": c["graph_sha256"], "n": c["n"], "m": c["m"],
                        "rows": [failed(name, "declared_no_progress_hard_wall_safety", "Unfinished assignment; partial results unavailable") for name in sorted(programs)]}
                    stream.write(json.dumps(r, ensure_ascii=False, allow_nan=False)+"\n")
                    completed.append(r)
                stream.flush()
                pending.clear()
                break
            for future in done:
                c = pending.pop(future)
                try:
                    r = future.result()
                except Exception as error:
                    r = {"id": c["id"], "population": c["population"], "graph_sha256": c["graph_sha256"], "n": c["n"], "m": c["m"],
                        "rows": [failed(name, "context_worker_exception", type(error).__name__ + ": " + str(error)) for name in sorted(programs)]}
                stream.write(json.dumps(r, ensure_ascii=False, allow_nan=False)+"\n")
                stream.flush()
                completed.append(r)
                last_progress = time.perf_counter()
                write(output / "progress.json", {"contexts_finished": len(completed), "contexts_assigned": 120, "assignment_rows": len(completed)*13, "elapsed_wall_seconds": time.perf_counter()-started})
                print(f"CONTEXTS {len(completed)}/120 ROWS {len(completed)*13}/1560", flush=True)
    executor.shutdown(wait=not hard_stop, cancel_futures=True)
    validation_started, validation_cpu = time.perf_counter(), time.process_time()
    check_count, physical_checks = 0, {}
    for c in contexts:
        r = next(r for r in completed if r["id"] == c["id"])
        g = Graph.from_dict(c["graph"])
        assert set(m["method"] for m in r["rows"]) == set(programs) and len(r["rows"]) == 13
        selections = {}
        for m in r["rows"]:
            if not m["completed"]:
                assert m["value"] is None and m["selected"] is None
                check_count += 1
                continue
            selected = m["selected"]
            assert g.feasible(selected) and set(c["fixed"]) <= set(selected) and not set(c["excluded"]).intersection(selected)
            assert exact_value(g, selected) == Fraction(m["value_exact"]) <= Fraction(c["reference"]["formal_upper_exact"])
            active, traced = g.available(c["fixed"], c["excluded"]), []
            for step in m["trace"]:
                v = step["selected"]
                assert v in active and step["remaining_count"] == len(active)
                active.difference_update({v} | g.adj[v])
                traced.append(v)
                check_count += 2
            assert not active and set(traced) | set(c["fixed"]) == set(selected)
            selections[m["method"]] = selected
            check_count += 4
        if c["population"] == "C3":
            physical_checks[c["id"]] = check_source_graph(g, selections, stable_root)
    write(output / "validation.json", {"errors": 0, "checks": check_count, "C3_source_verifier": physical_checks,
        "cpu_seconds": time.process_time()-validation_cpu, "wall_seconds": time.perf_counter()-validation_started,
        "scope": "Independent exact reward, graph/boundary feasibility, complete deletion trace and source C3 predicates; no additional score first-argmax recomputation."})
    allrows = [m for r in completed for m in r["rows"]]
    assert len(completed) == 120 and len(allrows) == 1560
    write(output / "complete.json", {"version": STEM, "complete": True, "contexts": 120, "assignments": 1560,
        "completed_assignments": sum(m["completed"] for m in allrows), "failure_status_counts": dict(Counter(m["status"] for m in allrows if not m["completed"])),
        "hard_wall_safety_triggered": hard_stop, "elapsed_wall_seconds": time.perf_counter()-started,
        "protocol_sha256": digest(STUDY / "protocol.json"), "source_zip_sha256": digest(CAPSULE), "frozen_programs_sha256": digest(STUDY / "frozen_programs.json"),
        "results_sha256": digest(output / "results.jsonl"), "validation_sha256": digest(output / "validation.json")})
    archive = ROOT / "experiments/runs/v05" / (STEM + ".tar.gz")
    if archive.exists():
        raise ValueError("Preserve prior archive")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(output, arcname=STEM)
    print(json.dumps({"state": "COMPLETE", "archive": str(archive), "sha256": digest(archive), "complete": load(output / "complete.json")}), flush=True)


def analyze():
    protocol, _, contexts = check_freeze()
    archive = ROOT / "experiments/runs/v05" / (STEM + ".tar.gz")
    with tarfile.open(archive, "r:gz") as tar:
        rows = [json.loads(line) for line in tar.extractfile(STEM + "/results.jsonl") if line.strip()]
        complete = json.load(tar.extractfile(STEM + "/complete.json"))
        validation = json.load(tar.extractfile(STEM + "/validation.json"))
    assert complete["complete"] and len(rows) == 120 and validation["errors"] == 0
    by_id = {r["id"]: {m["method"]: m for m in r["rows"]} for r in rows}
    populations = {}
    for population in protocol["population_counts"]:
        cases = [c for c in contexts if c["population"] == population]
        methods = {}
        for name in sorted(next(iter(by_id.values()))):
            assigned = [by_id[c["id"]][name] for c in cases]
            upper = [100*float(Fraction(m["value_exact"])/Fraction(c["reference"]["formal_upper_exact"])) if m["completed"] else 0.0 for c,m in zip(cases,assigned)]
            lower = [100*float(Fraction(m["value_exact"])/Fraction(c["reference"]["best_verified_lower_exact"])) if m["completed"] else 0.0 for c,m in zip(cases,assigned)]
            methods[name] = {"assigned": len(assigned), "completed": sum(m["completed"] for m in assigned), "mean_quality_to_formal_upper_percent": statistics.mean(upper),
                "mean_quality_to_prior_best_feasible_percent": statistics.mean(lower), "quality_to_upper_percent": upper, "quality_to_prior_feasible_percent": lower,
                "failure_status_counts": dict(Counter(m["status"] for m in assigned if not m["completed"])),
                "mean_cpu_seconds_all_known_assignments": statistics.mean(m["cpu_seconds"] for m in assigned if m["cpu_seconds"] is not None),
                "mean_wall_seconds_all_known_assignments": statistics.mean(m["wall_seconds"] for m in assigned if m["wall_seconds"] is not None),
                "known_timing_assignments": sum(m["cpu_seconds"] is not None for m in assigned)}
        arms = {}
        for arm in ARMS:
            blocks = [methods[f"block_{b}_{arm}"] for b in range(4)]
            arms[arm] = {"assigned": 4*len(cases), "completed": sum(b["completed"] for b in blocks),
                "equal_block_mean_quality_to_formal_upper_percent": statistics.mean(b["mean_quality_to_formal_upper_percent"] for b in blocks),
                "block_quality_to_formal_upper_percent": [b["mean_quality_to_formal_upper_percent"] for b in blocks],
                "equal_block_mean_quality_to_prior_best_feasible_percent": statistics.mean(b["mean_quality_to_prior_best_feasible_percent"] for b in blocks),
                "block_quality_to_prior_best_feasible_percent": [b["mean_quality_to_prior_best_feasible_percent"] for b in blocks],
                "equal_block_mean_cpu_seconds": statistics.mean(b["mean_cpu_seconds_all_known_assignments"] for b in blocks),
                "equal_block_mean_wall_seconds": statistics.mean(b["mean_wall_seconds_all_known_assignments"] for b in blocks)}
        contrasts = {f"{a}_minus_{b}_pp": arms[a]["equal_block_mean_quality_to_formal_upper_percent"] - arms[b]["equal_block_mean_quality_to_formal_upper_percent"] for a,b in (("witness","relations"),("witness","objective"),("relations","objective"))}
        populations[population] = {"contexts": len(cases), "context_ids": [c["id"] for c in cases], "methods": methods, "arms": arms, "degree": methods["Degree"], "contrasts": contrasts}
    target = ROOT / "experiments/analysis/v05" / (STEM + ".json")
    write(target, {"version": STEM, "exploratory": True, "protocol_sha256": digest(STUDY / "protocol.json"), "archive_sha256": digest(archive), "source_zip_sha256": digest(CAPSULE),
        "complete": complete, "validation_checks": validation["checks"], "populations": populations,
        "limits": ["Prior observed graphs, not fresh independent held-out populations", "Four authoring blocks are descriptive paired units, no significance or general LLM superiority claim", "Failure-zero U normalization and prior fixed-L normalization differ from original V05 fresh TEST q", "All new timings same host; old native baseline timings not pooled"]})
    lines = ["# Exploratory frozen-program transfer V05", "", "All twelve TRAIN-frozen winners were executed; no reselection. Five source populations remain separate. Quality is failure-zero percentage of the prior verified clique upper bound U, not percentage of an exact optimum. Best-feasible L stays fixed from V04. The previously observed public/C3 contexts make this extension exploratory.", "", "| Population | n contexts | Witness %U (coverage) | Relations %U (coverage) | Objective %U (coverage) | Degree %U (coverage) |", "|---|---:|---:|---:|---:|---:|"]
    for pop,p in populations.items():
        cells = [f"{p['arms'][a]['equal_block_mean_quality_to_formal_upper_percent']:.3f} ({p['arms'][a]['completed']}/{p['arms'][a]['assigned']})" for a in ARMS]
        d = p["degree"]
        lines.append(f"| {pop} | {p['contexts']} | " + " | ".join(cells) + f" | {d['mean_quality_to_formal_upper_percent']:.3f} ({d['completed']}/{d['assigned']}) |")
    lines += ["", "Raw traces, all timeout records, per-block values, fixed-denominator witnesses, source reconstruction and timing receipts are in the bound archive/JSON. No new native solver trajectory or LLM learning curve was invented.", "", "Protocol SHA256: `" + digest(STUDY / "protocol.json") + "`", "Archive SHA256: `" + digest(archive) + "`"]
    target.with_suffix(".md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"analysis": str(target), "populations": {k: {"arms":v["arms"],"degree":{q:v["degree"][q] for q in ("assigned","completed","mean_quality_to_formal_upper_percent")}} for k,v in populations.items()}}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run", "analyze"))
    parser.add_argument("--output", default=str(ROOT / ".research" / STEM))
    parser.add_argument("--stable-root", default="E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "run":
        run(args.output, args.stable_root)
    else:
        analyze()
