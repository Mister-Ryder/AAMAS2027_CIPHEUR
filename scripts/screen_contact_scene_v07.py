"""Input-only TRAIN scene census; no scheduling, conditional oracle or LLM.

Canonical source identities normalize whitespace and terminal quote characters.
Conflict predicates are imported byte-for-byte from the frozen V51 graph source.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import platform
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_STABLE = Path("E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE")
BASE9 = ("weight", "duration", "degree", "conflict_weight", "max_conflict_weight",
         "compatible_weight", "station_gap", "satellite_gap", "remaining_count")
LOCAL_SOURCES = ("scripts/screen_contact_scene_v07.py", "cipheur/v51_adapter.py",
                 "cipheur/model.py", "cipheur/__init__.py")
LEGACY_SOURCES = ("data.py", "graph.py", "verifier.py")


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_json(path, value):
    Path(path).write_bytes(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False).encode("utf-8") + b"\n")


def clean(value):
    return value.strip().lstrip("\ufeff").strip("'\"").strip()


def source_closure(stable):
    result = {name: digest((ROOT / name).read_bytes()) for name in LOCAL_SOURCES}
    legacy = Path(stable) / "SNSD_V51_FINAL/src/snsd_core"
    result.update({"legacy/" + name: digest((legacy / name).read_bytes())
                   for name in LEGACY_SOURCES})
    return result


def read_train(source, origin, days):
    """Parse input only; materialize contacts/hash identities for TRAIN alone."""
    raw = Path(source["path"]).read_bytes()
    if digest(raw) != source["sha256"]:
        raise ValueError("Source CSV hash mismatch: " + source["name"])
    rows = csv.reader(io.StringIO(raw.decode("gb18030", errors="strict"), newline=""))
    header = next(rows)
    if len(header) != 12:
        raise ValueError("Expected the canonical 12-column source header")
    if "地面站" not in clean(header[0]) or "卫星" not in clean(header[1]):
        raise ValueError("Unexpected ground/satellite prefix")
    windows = {day * 12 + hour: [] for day in days for hour in range(12)}
    total, day_counts, min_start, max_end = 0, Counter(), None, None
    ground_map, satellite_map = {}, {}
    normalized_quote_fields = 0
    for row_id, row in enumerate(rows):
        if len(row) != 12:
            raise ValueError("Wrong row width at CSV data row " + str(row_id))
        # Exact integer parsing: no float fallback or time/reward quantization.
        start, end = int(clean(row[2])), int(clean(row[3]))
        if end <= start or start < origin:
            raise ValueError("Invalid source interval at row " + str(row_id))
        day = (start - origin) // 86400
        day_counts[day] += 1
        total += 1
        min_start = start if min_start is None else min(min_start, start)
        max_end = end if max_end is None else max(max_end, end)
        if day not in days:
            continue
        fields = [clean(item) for item in row[:6]]
        ground, satellite = fields[:2]
        trace_start, trace_end = int(fields[4]), int(fields[5])
        if not ground or not satellite or trace_start > start or trace_end < end:
            raise ValueError("Invalid resource/tracking fields at row " + str(row_id))
        normalized_quote_fields += sum(row[i].strip() != fields[i] for i in (0, 1))
        ground_id = ground_map.setdefault(ground, len(ground_map))
        satellite_id = satellite_map.setdefault(satellite, len(satellite_map))
        normalized_identity = [ground, satellite, start, end, trace_start, trace_end]
        item = {"original_row_id": row_id, "row_sha256": digest(canonical(normalized_identity)),
                "ground": ground_id, "satellite": satellite_id,
                "ground_name": ground, "satellite_name": satellite,
                "link_st": start, "link_et": end,
                "trace_st": trace_start, "trace_et": trace_end}
        window = (start - origin) // 7200
        windows[window].append(item)
    if min_start != origin:
        raise ValueError("Declared time origin differs from observed minimum start")
    inventory = []
    for window, contacts in sorted(windows.items()):
        hashes = [item["row_sha256"] for item in contacts]
        inventory.append({"source": source["name"], "window": window,
                          "day": window // 12, "start": origin + window * 7200,
                          "end": origin + (window + 1) * 7200, "n": len(contacts),
                          "crossing_window_end": sum(item["link_et"] > origin + (window + 1) * 7200
                                                      for item in contacts),
                          "row_sha256": hashes, "ordered_rows_sha256": digest(canonical(hashes))})
    metadata = {"source": source["name"], "source_sha256": source["sha256"],
                "encoding": "strict gb18030", "total_rows": total,
                "day_start_counts": {str(day): count for day, count in sorted(day_counts.items())},
                "minimum_start": min_start, "maximum_end": max_end,
                "train_rows": sum(map(len, windows.values())),
                "train_ground_count": len(ground_map), "train_satellite_count": len(satellite_map),
                "train_normalized_quote_fields": normalized_quote_fields,
                "nontrain_contact_materialization": 0, "nontrain_graphs": 0}
    return windows, inventory, metadata


def quantiles(values):
    values = sorted(values)
    if not values:
        return {name: None for name in ("min", "p05", "median", "p95", "max")}
    n = len(values)
    return {"min": values[0], "p05": values[int(.05 * (n - 1))],
            "median": (values[(n - 1) // 2] + values[n // 2]) / 2,
            "p95": values[int(.95 * (n - 1))], "max": values[-1]}


def alias_census(keys, descriptors=None):
    groups = defaultdict(list)
    for index, key in enumerate(keys):
        groups[key].append(index)
    repeated = [members for members in groups.values() if len(members) > 1]
    split = [] if descriptors is None else [members for members in repeated
             if len({descriptors[index] for index in members}) > 1]
    return {"actions": len(keys), "distinct_classes": len(groups),
            "non_singleton_classes": len(repeated),
            "actions_in_non_singleton_classes": sum(map(len, repeated)),
            "unordered_equal_pairs": sum(len(g) * (len(g) - 1) // 2 for g in repeated),
            "largest_class": max(map(len, groups.values()), default=0),
            "class_size_histogram": dict(sorted(Counter(map(len, groups.values())).items())),
            "classes_split_by_declared_descriptor": len(split),
            "actions_in_descriptor_split_classes": sum(map(len, split))}


def analyze_graph(graph, arcs, ground_gap):
    n = len(arcs)
    adjacency = [set(map(int, graph.neighbors(v))) for v in range(n)]
    weights = [arc.link_time for arc in arcs]
    total = sum(weights)
    if total >= 2 ** 53:
        raise ValueError("Integer features exceed the exact binary64 integer range")
    edge_masks = [Counter() for _ in range(n)]
    for (u, v), mask in zip(graph.edges, graph.edge_types):
        edge_masks[int(u)][int(mask)] += 1
        edge_masks[int(v)][int(mask)] += 1
    features, descriptors, patterns = [], [], Counter()
    root_pattern_presence = Counter()
    for v in range(n):
        neighbor_weights = [weights[u] for u in adjacency[v]]
        conflict = sum(neighbor_weights)
        features.append((weights[v], weights[v], len(adjacency[v]), conflict,
                         max(neighbor_weights, default=0), total - weights[v] - conflict,
                         ground_gap, 150, n))
        # Coarse domain descriptor only; it is not an isomorphism certificate.
        counts = edge_masks[v]
        descriptor = (len(adjacency[v]), counts[1], counts[2], counts[3],
                      len({arcs[u].ground for u in adjacency[v]}),
                      len({arcs[u].satellite for u in adjacency[v]}))
        descriptors.append(descriptor)
        for first in (1, 2, 3):
            for second in range(first, 4):
                count = (counts[first] * (counts[first] - 1) // 2 if first == second
                         else counts[first] * counts[second])
                key = f"spokes_{first}_{second}"
                patterns[key] += count
                root_pattern_presence[key] += bool(count)
    sizes, unseen = [], set(range(n))
    while unseen:
        seed = unseen.pop()
        stack, size = [seed], 0
        while stack:
            current = stack.pop()
            size += 1
            new = adjacency[current] & unseen
            unseen.difference_update(new)
            stack.extend(new)
        sizes.append(size)
    m = graph.num_edges
    result = {"n": n, "m": m, "density": 2 * m / (n * (n - 1)) if n > 1 else 0,
              "legacy_graph_sha256": graph.graph_hash, "total_weight_exact": str(total),
              "degree": quantiles([len(neighbors) for neighbors in adjacency]),
              "degree_histogram": dict(sorted(Counter(map(len, adjacency)).items())),
              "component_count": len(sizes), "component_sizes": sorted(sizes, reverse=True),
              "component_size_histogram": dict(sorted(Counter(sizes).items())),
              "isolated_contacts": sum(not neighbors for neighbors in adjacency),
              "edge_reason_counts": dict(sorted(Counter(map(int, graph.edge_types)).items())),
              "base9_aliases": alias_census(features, descriptors),
              "degree_only_aliases": alias_census([(len(x),) for x in adjacency]),
              "weight_duration_degree_aliases": alias_census([f[:3] for f in features], descriptors),
              "root_descriptor_census": dict(sorted(Counter(
                  ",".join(map(str, item)) for item in descriptors).items())),
              "centered_spoke_type_counts": dict(sorted(patterns.items())),
              "roots_with_centered_spoke_type": dict(sorted(root_pattern_presence.items()))}
    return result, adjacency, features


def screen_window(task):
    start_wall, start_cpu = time.perf_counter(), time.process_time()
    from cipheur.v51_adapter import _load_legacy
    modules, _ = _load_legacy(Path(task["stable_root"]))
    Arc = modules["data"].Arc
    arcs = tuple(Arc(id=index, priority=0.0,
                     **{key: value for key, value in item.items()
                        if key not in ("original_row_id", "row_sha256")})
                 for index, item in enumerate(task["contacts"]))
    records, retained = [], []
    for gap in (340, 680):
        params = modules["graph"].ConflictParameters(gap, 150, 300)
        graph = modules["graph"].build_conflict_graph(arcs, params)
        record, adjacency, features = analyze_graph(graph, arcs, gap)
        record.update({"id": f"{task['source']}|day{task['window']//12}|window{task['window']%12:02d}|g{gap}",
                       "source": task["source"], "split": "TRAIN", "day": task["window"] // 12,
                       "window": task["window"], "ground_trans_time": gap,
                       "satellite_change_time": 150, "satellite_trans_time": 300,
                       "boundary": {"fixed": [], "excluded": []},
                       "ordered_rows_sha256": task["ordered_rows_sha256"]})
        records.append(record)
        retained.append((graph, adjacency, features))
    old, new = retained
    old_edges = {tuple(map(int, edge)): int(mask) for edge, mask in zip(old[0].edges, old[0].edge_types)}
    new_edges = {tuple(map(int, edge)): int(mask) for edge, mask in zip(new[0].edges, new[0].edge_types)}
    if not old_edges.keys() <= new_edges.keys():
        raise AssertionError("Increasing only ground gap unexpectedly removed an edge")
    changed_roots = sum(a != b for a, b in zip(old[1], new[1]))
    change = {"source": task["source"], "window": task["window"], "n": len(arcs),
              "before": 340, "after": 680, "added_edges": len(new_edges.keys() - old_edges.keys()),
              "removed_edges": 0, "edge_reason_only_changes": sum(
                  old_edges[edge] != new_edges[edge] for edge in old_edges),
              "roots_with_changed_neighbors": changed_roots,
              "base9_changed_actions": sum(a != b for a, b in zip(old[2], new[2])),
              "graph_only7_changed_actions": sum(a[:6] + a[8:] != b[:6] + b[8:]
                                                    for a, b in zip(old[2], new[2])),
              "standalone_worker_wall_seconds": time.perf_counter() - start_wall,
              "standalone_worker_cpu_seconds": time.process_time() - start_cpu}
    return {"records": records, "paired_change": change}


def prepare(args):
    out = Path(args.out).resolve()
    if out.exists():
        raise ValueError("Preserve original input screen namespace; use a new directory")
    if args.days != [0] or args.origin != 0 or args.workers != 8:
        raise ValueError("This release is fixed to day0, origin0 and eight workers")
    sources = []
    expected = dict(item.split("=", 1) for item in args.source_sha256)
    for item in args.source:
        name, path = item.split("=", 1)
        if name not in ("C6", "W6") or name not in expected or len(expected[name]) != 64:
            raise ValueError("Require C6/W6 source SHA pins from metadata profiles")
        sources.append({"name": name, "path": str(Path(path).resolve()), "sha256": expected[name]})
    if sorted(source["name"] for source in sources) != ["C6", "W6"]:
        raise ValueError("Exactly the two canonical C6/W6 sources are required")
    metadata, inventories = [], []
    for source in sources:
        _, inventory, meta = read_train(source, args.origin, set(args.days))
        metadata.append(meta)
        inventories.extend(inventory)
    closure = source_closure(args.stable_root)
    out.mkdir(parents=True)
    protocol = {"version": "contact_scene_screen_v07_001", "before_any_graph": True,
                "sources": sources, "time_origin_seconds": 0,
                "train_days": [0], "validation_days_not_built": [1], "heldout_days_not_built": [2],
                "window_seconds": 7200, "window_ownership": "half-open link-start only; never clip end",
                "normalization": "strict GB18030; trim whitespace/BOM then all terminal single/double quotes; exact integer times",
                "legacy_loader_difference": "Identity quote normalization also handles unmatched terminal quotes; inherited conflict predicates are unchanged",
                "objective": "Original link duration, exact nonnegative integer; priority is not the objective",
                "graph_model": "Original V51 legacy ground and satellite predicates, not ideal interval conflicts",
                "ground_gaps": [340, 680], "satellite_change_time": 150, "satellite_trans_time": 300,
                "base9_fields": list(BASE9),
                "satellite_gap_base_feature": "satellite_change_time=150, matching existing programs.features fallback",
                "window_count": 24, "graph_count": 48, "workers": 8,
                "boundary": {"fixed": [], "excluded": []},
                "patterns": "unordered two-spoke reason-mask classes 1/2/3; no rim-edge classification, not induced-wedge/triangle counts",
                "no_screening_filters": True, "optimizer_calls": 0, "oracle_calls": 0,
                "model_calls": 0, "source_sha256": closure}
    write_json(out / "protocol.json", protocol)
    write_json(out / "train_identity_inventory.json", {"metadata": metadata, "windows": inventories})
    snapshot = out / "source_snapshot.zip"
    with zipfile.ZipFile(snapshot, "x", compression=zipfile.ZIP_DEFLATED) as capsule:
        for name in LOCAL_SOURCES:
            capsule.writestr(name, (ROOT / name).read_bytes())
        for name in LEGACY_SOURCES:
            capsule.writestr("legacy/" + name, (Path(args.stable_root) /
                             "SNSD_V51_FINAL/src/snsd_core" / name).read_bytes())
    write_json(out / "freeze_receipt.json", {"before_any_graph": True,
               "protocol_sha256": digest((out / "protocol.json").read_bytes()),
               "identity_sha256": digest((out / "train_identity_inventory.json").read_bytes()),
               "source_snapshot_sha256": digest(snapshot.read_bytes()), "source_sha256": closure,
               "stable_root": str(Path(args.stable_root).resolve()), "created_unix": time.time()})
    print(json.dumps({"prepared": str(out), "graphs": 48, "graph_calls": 0}), flush=True)


def run(args):
    out = Path(args.out).resolve()
    if (out / "execution_receipt.json").exists():
        raise ValueError("Do not replay or overwrite the original screening execution")
    protocol = json.loads((out / "protocol.json").read_bytes())
    freeze = json.loads((out / "freeze_receipt.json").read_bytes())
    for name, field in (("protocol.json", "protocol_sha256"),
                        ("train_identity_inventory.json", "identity_sha256"),
                        ("source_snapshot.zip", "source_snapshot_sha256")):
        if digest((out / name).read_bytes()) != freeze[field]:
            raise ValueError("Frozen input/source receipt mismatch")
    if source_closure(freeze["stable_root"]) != freeze["source_sha256"]:
        raise ValueError("Source closure changed after freeze")
    inventory = json.loads((out / "train_identity_inventory.json").read_bytes())
    tasks, rebuilt_inventory, metadata = [], [], []
    for source in protocol["sources"]:
        windows, source_inventory, meta = read_train(source, 0, {0})
        metadata.append(meta)
        rebuilt_inventory.extend(source_inventory)
        by_window = {record["window"]: record for record in source_inventory}
        for window, contacts in sorted(windows.items()):
            tasks.append({"source": source["name"], "window": window, "contacts": contacts,
                          "stable_root": freeze["stable_root"],
                          "ordered_rows_sha256": by_window[window]["ordered_rows_sha256"]})
    if {"metadata": metadata, "windows": rebuilt_inventory} != inventory or len(tasks) != 24:
        raise ValueError("TRAIN identity inventory differs from prepared bytes")
    begin = time.time()
    write_json(out / "execution_receipt.json", {"start_unix": begin, "python": sys.version,
               "platform": platform.platform(), "workers": 8, "tasks": 24, "graphs": 48,
               "protocol_sha256": freeze["protocol_sha256"],
               "source_snapshot_sha256": freeze["source_snapshot_sha256"],
               "optimizer_calls": 0, "oracle_calls": 0, "model_calls": 0})
    records, changes, failures = [], [], []
    with (out / "window_results.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(screen_window, task): (task["source"], task["window"])
                       for task in tasks}
            for future in as_completed(futures):
                source, window = futures[future]
                try:
                    result = future.result()
                    records.extend(result["records"])
                    changes.append(result["paired_change"])
                    stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
                except Exception as error:
                    failure = {"source": source, "window": window,
                               "error": type(error).__name__ + ": " + str(error),
                               "assigned_graphs": 2}
                    failures.append(failure)
                    stream.write(json.dumps({"failure": failure}, ensure_ascii=False) + "\n")
                stream.flush()
                print(json.dumps({"finished_windows": len(changes) + len(failures),
                                  "assigned_windows": 24, "failures": len(failures)}), flush=True)
    summary = {"protocol_sha256": freeze["protocol_sha256"], "assigned_graphs": 48,
               "completed_graphs": len(records), "assigned_windows": 24,
               "completed_windows": len(changes), "failures": failures,
               "records": sorted(records, key=lambda item: item["id"]),
               "paired_changes": sorted(changes, key=lambda item: (item["source"], item["window"])),
               "elapsed_wall_seconds": time.time() - begin,
               "optimizer_calls": 0, "oracle_calls": 0, "model_calls": 0, "nontrain_graphs": 0}
    write_json(out / "screen_summary.json", summary)
    write_json(out / "completion_receipt.json", {"terminal": True,
               "assigned_graphs": 48, "completed_graphs": len(records), "failed_windows": len(failures),
               "summary_sha256": digest((out / "screen_summary.json").read_bytes()),
               "window_results_sha256": digest((out / "window_results.jsonl").read_bytes()),
               "protocol_sha256": freeze["protocol_sha256"], "finish_unix": time.time()})
    print(json.dumps({"terminal": True, "completed_graphs": len(records), "failed_windows": len(failures)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--source-sha256", action="append", default=[])
    parser.add_argument("--days", type=int, nargs="+", default=[0])
    parser.add_argument("--origin", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--stable-root", default=str(DEFAULT_STABLE))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else run)(args)


if __name__ == "__main__":
    main()
