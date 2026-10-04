"""Frozen server-only classical calibration on all supported V06 TRAIN sources.

The input split was registered before acquisition. This study never imports
authoring/oracle code and never materializes a TEST graph. Native wall targets
are nominal internal targets; the separate outer guard is not a matched
end-to-end deadline. Exact encoding limitations remain explicit null results.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STEM = "classic_public_train_v06_001"
STAGE = ROOT / "experiments/discovery" / STEM
CONFIG_PATH = ROOT / "configs/classic_public_train_v06_001.json"
CAPSULE = ROOT / "experiments/source_snapshots/v06" / (STEM + "_source.zip")
OUT = ROOT / "output" / STEM
SOURCES = ("cipheur/__init__.py", "cipheur/model.py", "cipheur/programs.py",
           "cipheur/graph_features.py", "cipheur/compiled.py", "cipheur/repair_v06.py",
           "cipheur/advanced_baselines.py", "cipheur/advanced_baselines_v06.py",
           "scripts/fetch_uai_mmap_v06.py", "scripts/run_classic_public_train_v06.py")
STARTUP = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
from cipheur.model import Contact, Graph
from cipheur.repair_v06 import RepairConfig, repair_schedule
from cipheur.advanced_baselines_v06 import run_solver
from scripts.fetch_uai_mmap_v06 import parse_dimacs

INPUTS = {
    "WDP": {
        "inventory": "experiments/analysis/v06/wdp_inventory_v06_001.json",
        "inventory_sha256": "d7899055c070ea5fe9a066acb7d70b540fa6aadef162dfdbf0b080ae07d6521b",
        "archive": "experiments/runs/v06/wdp_inputs_v06_001.tar.gz",
        "archive_sha256": "b47996fd674af7d4a1c2543c628b0d51f204d6c66f8bbd74687d3148a9f67c06",
        "member_root": "wdp_inputs_v06_001", "weight_scale": 1,
        "orientation": "exact complement of original maximum-weight-clique graph"},
    "UAI": {
        "inventory": "experiments/analysis/v06/uai_mmap_inventory_v06_001.json",
        "inventory_sha256": "d1ba42377fb00e25e8ad5e91815406172f150f6481b7c9203c60b30eb113bd7f",
        "archive": "experiments/runs/v06/uai_mmap_inputs_v06_001.tar.gz",
        "archive_sha256": "4c9d8decb20d771f581dbbbee825408a42baa36eab353fb80f3991af47bb0940",
        "member_root": "uai_mmap_v06_001", "weight_scale": 100000,
        "orientation": "original native MWIS conflict edges"}}
METHODS = [{"method": name, "seed": seed} for name, seeds in
           (("CHILS", (1, 2, 3)), ("CHILS_ILS", (1, 2, 3)),
            ("M2WIS", (1, 2, 3)), ("Struction", (1,)),
            ("WeightedBR", (1,)), ("Degree", (1,))) for seed in seeds]
REPAIR = {"max_patch_vertices": 24, "max_destroy": 4, "max_patches": 512,
          "expansion_steps": 1, "node_budget_per_patch": 128,
          "max_search_nodes": 65536, "max_work": None,
          "upper_pruning": True, "policy_scope": "branch"}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical(obj):
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                  separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n").encode())
    os.replace(temp, path)


def source_inventory():
    current = {n: digest(ROOT / n) for n in SOURCES}
    if current != STARTUP:
        raise ValueError("Runtime source changed after startup/import")
    return current


def input_records():
    selected, all_uai = [], []
    for family, binding in INPUTS.items():
        assert digest(ROOT / binding["inventory"]) == binding["inventory_sha256"]
        assert digest(ROOT / binding["archive"]) == binding["archive_sha256"]
        inventory = json.loads((ROOT / binding["inventory"]).read_bytes())["records"]
        if family == "UAI":
            all_uai = inventory
        for record in inventory:
            if record.get("split") != "train" or record.get("parse_status") != "valid":
                continue
            if family == "UAI" and not record["direct_native_signed32_compatible"]:
                continue
            selected.append({**record, "input_family": family,
                "id": family + ":" + record["source_cluster"],
                "source_weight_scale": binding["weight_scale"],
                "orientation": binding["orientation"]})
    assert len(selected) == 28
    assert Counter(r["input_family"] for r in selected) == {"WDP": 25, "UAI": 3}
    assert {r["source_cluster"] for r in selected if r["input_family"] == "UAI"} == {
        "Segmentation_12", "Segmentation_13", "Segmentation_16"}
    return sorted(selected, key=lambda r: r["id"]), all_uai


def package():
    if STAGE.exists() or CAPSULE.exists() or CONFIG_PATH.exists():
        raise ValueError("Preserve first calibration registration; no overwrite")
    assert digest(ROOT / "cipheur/advanced_baselines_v06.py") == "713364f084ef9c3538be275b2437e681e6a9d0457dbc028d621ba0bc71ee4477"
    assert digest(ROOT / "cipheur/repair_v06.py") == "c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3"
    records, uai = input_records()
    executables = json.loads((ROOT / "configs/advanced_public_v04_remote.json").read_bytes())["executables"]
    config = {"version": STEM, "before_any_calibration_outcomes": True,
        "split": "train", "workers": 8, "wall_targets": [0.1, 1, 5],
        "methods": METHODS, "repair_config": REPAIR, "degree_priority": "degree",
        "degree_clock": "wall", "native_hard_wall_guard_seconds": 30,
        "whole_batch_wall_guard_seconds": 3600, "executables": executables,
        "inputs": INPUTS, "selected_sources": records,
        "assigned_sources": 28, "assigned_requests": 1008,
        "predetermined_unsupported_wdp_native_requests": 375,
        "all_original_uai_sources": 81, "unsupported_uai_exact_encodings": 75,
        "unsupported_uai_original_inventory_retained": uai,
        "dataset_selection": "Previously registered source-SHA TRAIN split; all 25 WDP TRAIN sources and all three exact-scalable Segmentation TRAIN sources; no outcome-based filtering",
        "encoding": "Preserve WDP integer weights and complement all source edges; UAI Fraction(raw_string)*100000 exact integer, no rounding",
        "timing_scope": "Graph JSON loading/reconstruction measured once per source; each native wrapper includes METIS preparation/startup/I/O/checking with nominal internal wall target; Degree timer includes validation/init/search/checking with cooperative wall target. Actual CPU/wall and overshoot retained; targets are not matched end-to-end hard deadlines.",
        "unsupported_scope": "Encoding limitation returns null reward/selection, never zero-quality failure. Supported solver errors/timeouts remain explicit null; no fallback or replacement.",
        "degree_caps": "Time, patch, search-node and work caps are normal anytime completion with feasible incumbent; not full-search completion or optimality.",
        "shared_startup": "Interpreter/import/preparation/pool overhead is measured at batch level, never added repeatedly to each request",
        "native_language": "Published C/C++ versus Python shared-kernel implementation; equal nominal target is not a claim of language-independent fairness",
        "use_restriction": "Classical TRAIN calibration only; excluded from LLM authoring packets, supplements and the frozen original 120-state selector",
        "test_executions_permitted": False, "oracle_calls": 0, "model_calls": 0,
        "source_sha256": source_inventory()}
    write(CONFIG_PATH, config)
    write(STAGE / "registration.json", {"before_any_calibration_outcomes": True,
          "registered_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "config_sha256": digest(CONFIG_PATH), "input_bindings": INPUTS,
          "source_sha256": config["source_sha256"]})
    names = (*SOURCES, CONFIG_PATH.relative_to(ROOT).as_posix(),
             "experiments/discovery/" + STEM + "/registration.json",
             INPUTS["WDP"]["inventory"], INPUTS["UAI"]["inventory"])
    inventory = {n: digest(ROOT / n) for n in names}
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for n in sorted(inventory):
            entry = zipfile.ZipInfo(n, (2026, 10, 4, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (ROOT / n).read_bytes())
    receipt = {"before_any_calibration_outcomes": True, "source_zip_sha256": digest(CAPSULE),
        "source_zip": CAPSULE.relative_to(ROOT).as_posix(), "files_sha256": inventory,
        "config_sha256": digest(CONFIG_PATH), "assigned_requests": 1008}
    write(STAGE / "capsule_receipt.json", receipt)
    print(json.dumps(receipt), flush=True)


def verify_package():
    receipt = json.loads((STAGE / "capsule_receipt.json").read_bytes())
    assert digest(CAPSULE) == receipt["source_zip_sha256"]
    for n, expected in receipt["files_sha256"].items():
        assert digest(ROOT / n) == expected, n
    config = json.loads(CONFIG_PATH.read_bytes())
    assert config["before_any_calibration_outcomes"] and not config["test_executions_permitted"]
    assert config["split"] == "train" and config["workers"] == 8
    assert config["wall_targets"] == [0.1, 1, 5] and config["methods"] == METHODS
    assert config["repair_config"] == REPAIR and config["source_sha256"] == source_inventory()
    assert asdict(RepairConfig(**REPAIR)) == REPAIR
    for binding in INPUTS.values():
        assert digest(ROOT / binding["archive"]) == binding["archive_sha256"]
    for executable in config["executables"].values():
        assert digest(executable["path"]) == executable["sha256"]
    return config, receipt


def raw_graph(raw, record):
    """Independent raw-to-Graph mapping; exact public graph remains authoritative."""
    stats = parse_dimacs(raw)
    assert stats["n"] == record["n"] and stats["m_unique"] == record["m_unique"]
    assert stats["duplicate_edges"] == 0 and stats["negative_weights"] == stats["zero_weights"] == 0
    assert stats["weight_exact_digest"] == record["weight_exact_digest"]
    assert stats["edge_digest"] == record["edge_digest"]
    weights, source_edges = {}, set()
    for line in raw.decode().splitlines():
        parts = line.split()
        if parts and parts[0] == "n":
            value = Fraction(parts[2]) * record["source_weight_scale"]
            if value.denominator != 1:
                raise ValueError("Exact public weight cannot be represented by registered integer scale")
            weights[int(parts[1])] = int(value)
        elif parts and parts[0] == "e":
            source_edges.add(tuple(sorted((int(parts[1]), int(parts[2])))))
    n = stats["n"]
    ids = {i: f"v{i:05d}" for i in range(1, n + 1)}
    contacts = tuple(Contact(ids[i], weights[i], "public_sat_" + ids[i],
                     "public_ground_" + ids[i], 0, 1) for i in range(1, n + 1))
    if record["input_family"] == "WDP":
        edges = frozenset((ids[a], ids[b]) for a, b in combinations(range(1, n + 1), 2)
                          if (a, b) not in source_edges)
        assert len(edges) + len(source_edges) == n*(n-1)//2
    else:
        edges = frozenset((ids[a], ids[b]) for a, b in source_edges)
    graph = Graph(record["id"], contacts, edges,
        {"model": "authoritative_public_conflict_graph", "source_weight_scale": record["source_weight_scale"]},
        {"source_path": record["path"], "source_sha256": record["raw_sha256"],
         "source_cluster": record["source_cluster"], "orientation": record["orientation"],
         "contact_attributes_are_carrier_only": True})
    return graph


def prepare(config, capsule):
    if OUT.exists():
        raise ValueError("Do not overwrite or resume existing calibration outputs")
    OUT.mkdir(parents=True)
    records = []
    with tarfile.open(ROOT / INPUTS["WDP"]["archive"], "r:gz") as wdp, \
         tarfile.open(ROOT / INPUTS["UAI"]["archive"], "r:gz") as uai:
        archives = {"WDP": wdp, "UAI": uai}
        for record in config["selected_sources"]:
            assert record["split"] == "train"
            binding = INPUTS[record["input_family"]]
            raw = archives[record["input_family"]].extractfile(binding["member_root"] + "/" + record["path"]).read()
            assert sha256(raw).hexdigest() == record["raw_sha256"]
            graph = raw_graph(raw, record)
            name = "graphs/" + sha256(record["id"].encode()).hexdigest()[:16] + ".json"
            write(OUT / name, graph.to_dict())
            records.append({**record, "graph_file": name, "graph_file_sha256": digest(OUT / name),
                            "graph_sha256": graph.digest(), "m_conflict": len(graph.edges)})
    protocol = {**config, "contexts": records, "prepared_before_any_solver": True,
                "source_zip_sha256": capsule["source_zip_sha256"],
                "config_sha256": digest(CONFIG_PATH), "context_identity_sha256": canonical(records)}
    write(OUT / "protocol.json", protocol)
    write(OUT / "freeze_receipt.json", {"before_any_calibration_outcomes": True,
          "prepared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "protocol_sha256": digest(OUT / "protocol.json"),
          "context_identity_sha256": canonical(records),
          "source_zip_sha256": capsule["source_zip_sha256"],
          "graph_files_sha256": {r["graph_file"]: r["graph_file_sha256"] for r in records}})
    return protocol


def assignments(context, config):
    for target in config["wall_targets"]:
        for method in config["methods"]:
            yield {"id": context["id"], "source_cluster": context["source_cluster"],
                "family": context["family"], "input_family": context["input_family"],
                "split": "train", "source_path": context["path"], "source_sha256": context["raw_sha256"],
                "graph_sha256": context["graph_sha256"], "n": context["n"], "m": context["m_conflict"],
                "source_weight_scale": context["source_weight_scale"],
                "nominal_wall_target_seconds": target, **method}


def assignment_key(row):
    return row["id"], row["nominal_wall_target_seconds"], row["method"], row["seed"]


def journal_path(context, output):
    return Path(output) / "context_results" / (sha256(context["id"].encode()).hexdigest()[:16] + ".jsonl")


def execute_context(context, config, output):
    output = Path(output)
    assert context["split"] == "train"
    wall0, cpu0 = time.perf_counter(), time.process_time()
    graph = None
    loading_error = None
    try:
        assert digest(output / context["graph_file"]) == context["graph_file_sha256"]
        graph = Graph.from_dict(json.loads((output / context["graph_file"]).read_bytes()))
        assert graph.digest() == context["graph_sha256"]
    except Exception as error:
        loading_error = {"type": type(error).__name__, "message": str(error)}
    loading = {"graph_load_wall_seconds": time.perf_counter() - wall0,
               "graph_load_cpu_seconds": time.process_time() - cpu0,
               "loading_scope": "Once-per-source graph JSON read/hash/reconstruction; shared by all 36 requests"}
    write(output / "context_loading" / (sha256(context["id"].encode()).hexdigest()[:16] + ".json"),
          {"id": context["id"], "graph_sha256": context["graph_sha256"], **loading,
           "loading_error": loading_error})
    result_path = journal_path(context, output)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in assignments(context, config):
            wall, cpu = time.perf_counter(), time.process_time()
            result = None
            error = loading_error
            if error is None:
                try:
                    if row["method"] == "Degree":
                        result = repair_schedule(graph, priority="degree", seconds=row["nominal_wall_target_seconds"],
                            clock="wall", config=RepairConfig(**config["repair_config"]), random_seed=1)
                    else:
                        name = "CHILS" if row["method"] == "CHILS_ILS" else row["method"]
                        executable = config["executables"][name]
                        result = run_solver(graph, executable["path"], row["method"],
                            seconds=row["nominal_wall_target_seconds"], seed=row["seed"],
                            hard_wall_seconds=config["native_hard_wall_guard_seconds"])
                        if result.get("solver_invoked"):
                            assert result["executable_sha256"] == executable["sha256"]
                    value = result.get("value_exact")
                    row["value_exact_original_objective"] = (str(Fraction(value) / row["source_weight_scale"])
                                                              if value is not None else None)
                except Exception as failure:
                    error = {"type": type(failure).__name__, "message": str(failure)}
            row.update(result=result, runner_error=error, assignment_returned=True,
                wrapper_wall_seconds=time.perf_counter() - wall,
                wrapper_self_cpu_seconds=time.process_time() - cpu,
                graph_loading_receipt_shared=context["id"],
                value_exact_original_objective=row.get("value_exact_original_objective"))
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
    return context["id"]


def read_context_results(context, config, output, future_error=None):
    rows = []
    path = journal_path(context, output)
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # Keep the original journal byte-for-byte; record its incomplete
                # assignment as an explicit worker failure in the merged file.
                break
    existing = {assignment_key(r) for r in rows}
    if len(existing) != len(rows):
        raise ValueError("Duplicate assignment in persistent worker journal")
    for row in assignments(context, config):
        if assignment_key(row) not in existing:
            row.update(result=None, runner_error=future_error or {"type": "MissingWorkerReceipt",
                "message": "Predetermined assignment missing from persistent worker journal"},
                assignment_returned=True, wrapper_wall_seconds=None, wrapper_self_cpu_seconds=None,
                value_exact_original_objective=None)
            rows.append(row)
    assert len(rows) == 36 and {assignment_key(r) for r in rows} == {
        assignment_key(r) for r in assignments(context, config)}
    return rows


def worker_run():
    config, _ = verify_package()
    protocol = json.loads((OUT / "protocol.json").read_bytes())
    frozen = json.loads((OUT / "freeze_receipt.json").read_bytes())
    assert digest(OUT / "protocol.json") == frozen["protocol_sha256"]
    assert protocol["source_sha256"] == source_inventory() and protocol["config_sha256"] == digest(CONFIG_PATH)
    assert canonical(protocol["contexts"]) == frozen["context_identity_sha256"]
    if (OUT / "results.jsonl").exists() or (OUT / "completion.json").exists():
        raise ValueError("Preserve first calibration results; no rerun or resume")
    started = time.perf_counter()
    counts, statuses = Counter(), Counter()
    with (OUT / "results.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=config["workers"]) as pool:
            futures = {pool.submit(execute_context, c, config, str(OUT)): c for c in protocol["contexts"]}
            for future in as_completed(futures):
                context = futures[future]
                error = None
                try:
                    assert future.result() == context["id"]
                except Exception as failure:
                    error = {"type": type(failure).__name__, "message": str(failure)}
                for row in read_context_results(context, config, OUT, error):
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                    counts["returned"] += 1
                    result = row.get("result")
                    if row.get("runner_error") or result is None:
                        statuses["runner_error"] += 1
                    else:
                        statuses[result["status"]] += 1
                        counts["feasible_incumbents"] += bool(result.get("feasible"))
                        counts["completed_requests"] += bool(result.get("completed"))
                        counts["encoding_not_supported"] += result["status"] == "encoding_not_supported"
                stream.flush()
                counts["sources_returned"] += 1
                write(OUT / "progress.json", {"assigned": 1008, **dict(counts),
                      "status_counts": dict(statuses), "wall_seconds": time.perf_counter() - started})
    assert counts["returned"] == 1008
    completion = {"version": STEM, "split": "train", "assigned": 1008, **dict(counts),
        "status_counts": dict(statuses), "wall_seconds": time.perf_counter() - started,
        "results_sha256": digest(OUT / "results.jsonl"), "protocol_sha256": frozen["protocol_sha256"],
        "source_zip_sha256": protocol["source_zip_sha256"], "test_executions": 0,
        "authoring_or_selector_changes": False, "oracle_calls": 0, "model_calls": 0}
    write(OUT / "completion.json", completion)
    print(json.dumps(completion), flush=True)


def optional(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def server_run():
    if platform.system() != "Linux":
        raise ValueError("Research calibration is server-only; local execution prohibited")
    started = time.perf_counter()
    config, capsule = verify_package()
    if (STAGE / "host_receipt.json").exists():
        raise ValueError("Preserve original execution host receipt")
    host = {"before_any_calibration_outcomes": True, "timestamp_unix": time.time(),
        "pid": os.getpid(), "python": sys.version, "platform": platform.platform(),
        "workers": 8, "cgroup_cpu_max": optional("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": optional("/sys/fs/cgroup/memory.max"),
        "cgroup_memory_current": optional("/sys/fs/cgroup/memory.current"),
        "cpu_model": next((s.partition(":")[2].strip() for s in Path("/proc/cpuinfo").read_text().splitlines()
                          if s.startswith("model name")), None),
        "process_inventory": subprocess.check_output(["ps", "-eo", "pid,comm,pcpu,pmem", "--sort=-pcpu"],
                                                      text=True).splitlines()[:25],
        "source_zip_sha256": capsule["source_zip_sha256"], "config_sha256": digest(CONFIG_PATH),
        "test_executions_permitted": False}
    write(STAGE / "host_receipt.json", host)
    protocol = prepare(config, capsule)
    prepare_wall = time.perf_counter() - started
    assert protocol["prepared_before_any_solver"]
    log = ROOT / (STEM + ".worker.log")
    guard = False
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    with log.open("xb") as stream:
        child = subprocess.Popen([sys.executable, "scripts/run_classic_public_train_v06.py", "worker-run"],
            cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        write(STAGE / "launch_receipt.json", {"timestamp_unix": time.time(), "child_pid": child.pid,
            "protocol_sha256": digest(OUT / "protocol.json"), "freeze_receipt_sha256": digest(OUT / "freeze_receipt.json"),
            "host_receipt_sha256": digest(STAGE / "host_receipt.json"), "prepared_before_child_launch": True,
            "workers": 8, "assigned_requests": 1008})
        try:
            code = child.wait(timeout=config["whole_batch_wall_guard_seconds"])
        except subprocess.TimeoutExpired:
            guard = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait()
    for name in ("registration.json", "capsule_receipt.json", "host_receipt.json", "launch_receipt.json"):
        (OUT / name).write_bytes((STAGE / name).read_bytes())
    (OUT / "registered_config.json").write_bytes(CONFIG_PATH.read_bytes())
    (OUT / "worker.log").write_bytes(log.read_bytes())
    write(OUT / "server_execution_receipt.json", {"append_only": True,
        "source_zip_sha256": capsule["source_zip_sha256"],
        "host_receipt_sha256": digest(STAGE / "host_receipt.json"),
        "full_verify_prepare_run_wall_seconds": time.perf_counter() - started,
        "shared_verify_and_prepare_wall_seconds": prepare_wall,
        "whole_batch_guard_triggered": guard, "exit_code": code,
        "all_partial_outcomes_retained": True, "query_retries": 0,
        "test_executions": 0, "graph_loading_not_repeated_in_each_policy_time": True})
    archive = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(OUT, arcname=STEM)
    write(STAGE / "archive_receipt.json", {"archive_sha256": digest(archive),
        "archive_bytes": archive.stat().st_size,
        "execution_complete": (OUT / "completion.json").exists() and code == 0 and not guard})
    print(json.dumps(json.loads((STAGE / "archive_receipt.json").read_bytes())), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("package", "server-run", "worker-run"))
    args = parser.parse_args()
    {"package": package, "server-run": server_run, "worker-run": worker_run}[args.mode]()
