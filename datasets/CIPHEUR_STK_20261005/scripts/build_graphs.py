"""CIPHEUR P0 capacity-one graphs, exact microsecond serialization.

This module is independent of the earlier V51 conflict predicate and does not
modify the research repository. Contacts are entire STK visibility intervals.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np


VERSION = "cipheur-full-contact-capacity1-microtick-v1"
TICKS_PER_SECOND = 1_000_000
HORIZON_TICKS = 72 * 3600 * TICKS_PER_SECOND
INT64_MAX = np.iinfo(np.int64).max
BASE9_NAMES = (
    "weight", "duration", "degree", "conflict_weight", "max_conflict_weight",
    "compatible_weight", "station_gap", "satellite_gap", "remaining_count",
)
EDGE_MASK = {"ground": 1, "satellite": 2, "overlap": 4, "gap_only": 8}
ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ticks(value: str, name: str = "time") -> int:
    """Accept exactly representable microticks; never truncate or round."""
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError(f"Nonfinite {name}: {value}")
    scaled = number * TICKS_PER_SECOND
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{name} has nonzero precision beyond a microsecond: {value}")
    result = int(scaled)
    if abs(result) > INT64_MAX:
        raise OverflowError(f"{name} exceeds signed int64: {value}")
    return result


def sec_text(value: int) -> str:
    return format(Decimal(int(value)) / TICKS_PER_SECOND, ".6f")


def array_hash(*arrays) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        if array.dtype.kind in "USO":
            for value in array.tolist():
                text = str(value).encode("utf-8")
                digest.update(len(text).to_bytes(8, "little"))
                digest.update(text)
        else:
            digest.update(str(array.dtype).encode("ascii"))
            digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def read_contacts(path: Path, parameters: dict, source_id: str | None = None) -> tuple[dict, dict, list]:
    manifest_path = path.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "success":
        raise ValueError("Only a successful complete STK opportunity library may be graphed")
    if not (manifest.get("formal_dataset") is True and
            manifest.get("eop_loaded_covers_padded_propagation") is True and
            manifest.get("eop_actual_table_matches_source") is True):
        raise ValueError("Library lacks the required formal fresh-EOP loading and coverage receipt")
    eop_receipt_path = path.parent / manifest["eop_receipt_file"]
    eop_receipt = json.loads(eop_receipt_path.read_text(encoding="utf-8"))
    eop_source_path = path.parents[2] / "source_dependencies" / "EOP-v1.1.txt"
    frozen_parameters_path = path.parents[2] / "source_plan" / "CIPHEUR_parameters.json"
    if manifest.get("parameters_sha256") != sha256_file(frozen_parameters_path):
        raise ValueError("The successful STK library was generated from different parameter bytes")
    if not (eop_receipt.get("covers_entire_padded_propagation") is True and
            eop_receipt.get("table_matches_source") is True and
            eop_receipt.get("source_sha256") == manifest["eop_sha256"] == sha256_file(eop_source_path)):
        raise ValueError("Fresh EOP provenance does not match the frozen actual-STK loading receipt")
    raw_hash = sha256_file(path)
    if manifest.get("contacts_sha256") != raw_hash:
        raise ValueError("Contact bytes disagree with the successful STK manifest")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "source_group", "geometry_id", "replicate_id", "epoch_utc",
            "contact_id", "pass_id", "satellite_id", "site_id", "antenna_id",
            "start_seconds", "end_seconds", "duration_seconds", "crosses_horizon",
            "access_settings_hash",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing contact columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("No contacts; an empty raw library needs an explicit diagnostic, not a graph")
    geometries = {row["geometry_id"] for row in rows}
    replicates = {row["replicate_id"] for row in rows}
    source_groups = {row["source_group"] for row in rows}
    epochs = {row["epoch_utc"] for row in rows}
    settings_hashes = {row["access_settings_hash"] for row in rows}
    if any(len(values) != 1 for values in (geometries, replicates, source_groups, epochs, settings_hashes)):
        raise ValueError("One contact CSV must contain exactly one physical scene and one access setting")
    scene_matches = [scene for scene in parameters["scene_definitions"]
                     if scene["geometry_id"] in geometries and scene["replicate_id"] in replicates]
    if len(scene_matches) != 1:
        raise ValueError("Physical scene not uniquely found in the frozen parameters")
    scene = scene_matches[0]
    if source_id is not None and source_id != scene["scene_id"]:
        raise ValueError(f"Source ID disagrees: {source_id} != {scene['scene_id']}")
    if source_groups != {scene["source_group"]}:
        raise ValueError("Source group disagrees with frozen split assignment")
    if epochs != {scene["epoch_utc"]}:
        raise ValueError("Epoch disagrees with the frozen physical scene")
    satellites = {sat["satellite_id"] for sat in scene["satellites"]}
    stations = {site["site_id"]: site["antenna_id"] for site in parameters["stations"]}
    rows.sort(key=lambda row: row["contact_id"])
    contact_ids = [row["contact_id"] for row in rows]
    if len(set(contact_ids)) != len(contact_ids):
        raise ValueError("Duplicate contact IDs")
    starts, ends, original_duration_differences = [], [], []
    opportunity_keys = set()
    for row in rows:
        start, end = ticks(row["start_seconds"], "start_seconds"), ticks(row["end_seconds"], "end_seconds")
        if row["crosses_horizon"].lower() not in ("false", "0", "no", ""):
            raise ValueError("Boundary-crossing interval found in the retained full-contact library")
        if not 0 <= start < end <= HORIZON_TICKS:
            raise ValueError(f"Contact is not positive and entirely within the 72-hour horizon: {row['contact_id']}")
        if row["satellite_id"] not in satellites:
            raise ValueError(f"Unknown satellite: {row['satellite_id']}")
        if stations.get(row["site_id"]) != row["antenna_id"]:
            raise ValueError(f"Site/antenna does not match the frozen capacity-one station map: {row['site_id']}")
        key = (row["satellite_id"], row["antenna_id"], start, end)
        if key in opportunity_keys:
            raise ValueError(f"Duplicated physical opportunity: {row['contact_id']}")
        opportunity_keys.add(key)
        serialized_duration = ticks(row["duration_seconds"], "duration_seconds")
        if serialized_duration != end - start:
            original_duration_differences.append({
                "contact_id": row["contact_id"], "reported_duration_ticks": serialized_duration,
                "endpoint_difference_ticks": end - start,
            })
        starts.append(start)
        ends.append(end)
    start_array, end_array = np.array(starts, np.int64), np.array(ends, np.int64)
    weight_array = end_array - start_array
    total_weight = sum(int(value) for value in weight_array)
    if total_weight > INT64_MAX:
        raise OverflowError("Total weight, and therefore a base9 sum, exceeds signed int64")
    data = {
        "contact_id": np.array(contact_ids, dtype=str),
        "pass_id": np.array([row["pass_id"] for row in rows], dtype=str),
        "satellite_id": np.array([row["satellite_id"] for row in rows], dtype=str),
        "site_id": np.array([row["site_id"] for row in rows], dtype=str),
        "antenna_id": np.array([row["antenna_id"] for row in rows], dtype=str),
        "start_ticks": start_array, "end_ticks": end_array, "weight_ticks": weight_array,
    }
    metadata = {
        "source_id": scene["scene_id"], "source_group": scene["source_group"],
        "geometry_id": scene["geometry_id"], "replicate_id": scene["replicate_id"],
        "split": scene["split"], "epoch_utc": scene["epoch_utc"],
        "horizon_stop_utc": scene["horizon_stop_utc"],
        "raw_contacts_path": str(path.resolve()), "raw_contacts_sha256": sha256_file(path),
        "stk_manifest_sha256": sha256_file(manifest_path),
        "eop_loaded_receipt_sha256": sha256_file(eop_receipt_path),
        "eop_source_sha256": manifest["eop_sha256"],
        "formal_fresh_eop_dataset": True,
        "future_eop_values_are_forecasts": eop_receipt.get("future_values_are_forecasts"),
        "access_settings_hash": next(iter(settings_hashes)),
        "node_mapping_sha256": array_hash(data["contact_id"], data["pass_id"], data["satellite_id"],
                                          data["site_id"], data["antenna_id"], start_array, end_array),
        "weight_ticks_sha256": array_hash(weight_array),
        "reported_duration_difference_count": len(original_duration_differences),
        "reported_duration_differences": original_duration_differences,
        "weight_semantics": "end_ticks - start_ticks; no rounding after reading frozen endpoints",
        "contact_count": len(rows), "unique_satellites": len(set(data["satellite_id"].tolist())),
        "unique_antennas": len(set(data["antenna_id"].tolist())),
        "total_weight_ticks": total_weight,
        "duration_uniqueness": duration_census(weight_array),
    }
    return data, metadata, rows


def duration_census(weights: np.ndarray) -> dict:
    _, inverse, counts = np.unique(weights, return_inverse=True, return_counts=True)
    duplicate_classes = [np.flatnonzero(inverse == group).tolist()
                         for group in np.flatnonzero(counts > 1)]
    unique = not duplicate_classes
    return {
        "duration_classes": len(counts), "contacts": len(weights),
        "duplicate_duration_classes": len(duplicate_classes),
        "duplicate_duration_contact_occurrences": int(counts[counts > 1].sum()),
        "duplicate_duration_node_groups": duplicate_classes,
        "all_durations_unique": unique,
        "necessary_condition_result": (
            "Distinct-contact full-base9 equality is impossible in every active subset or boundary of this library, because the unchanged weight coordinate is injective."
            if unique else "Repeated duration is only a necessary condition; complete base9 equality and strict decision labels still need separate checks."
        ),
        "scope_note": "No claim about equality for the same contact in different residual states, or about rule-grammar fit; no oracle labels were used.",
    }


def resource_edges(data: dict, resource: str, gap_ticks: int, resource_bit: int) -> tuple[np.ndarray, np.ndarray]:
    n = len(data["contact_id"])
    groups = defaultdict(list)
    for node, identity in enumerate(data[resource].tolist()):
        groups[identity].append(node)
    keys, masks = [], []
    for group in groups.values():
        # Node numbering is contact-ID order, which is the explicit secondary key.
        order = np.array(sorted(group, key=lambda node: (int(data["start_ticks"][node]), node)), dtype=np.int64)
        starts = data["start_ticks"][order]
        for position, node in enumerate(order):
            finish = int(data["end_ticks"][node])
            stop = int(np.searchsorted(starts, finish + gap_ticks, side="left"))
            other = order[position + 1:stop]
            if not len(other):
                continue
            first, second = np.minimum(node, other), np.maximum(node, other)
            keys.append(first * n + second)
            overlap = data["start_ticks"][other] < finish
            masks.append((resource_bit | np.where(overlap, EDGE_MASK["overlap"], EDGE_MASK["gap_only"])).astype(np.uint8))
    if not keys:
        return np.empty(0, np.int64), np.empty(0, np.uint8)
    return np.concatenate(keys), np.concatenate(masks)


def build_edges(data: dict, ground_gap_ticks: int, satellite_gap_ticks: int) -> dict:
    n = len(data["contact_id"])
    if ground_gap_ticks < 0 or satellite_gap_ticks < 0:
        raise ValueError("Negative switching gap")
    if n >= 2**32 or n * n > INT64_MAX:
        raise OverflowError("Packed edge indexing is too large")
    ground_keys, ground_masks = resource_edges(data, "antenna_id", ground_gap_ticks, EDGE_MASK["ground"])
    satellite_keys, satellite_masks = resource_edges(data, "satellite_id", satellite_gap_ticks, EDGE_MASK["satellite"])
    all_keys = np.concatenate((ground_keys, satellite_keys))
    all_masks = np.concatenate((ground_masks, satellite_masks))
    order = np.argsort(all_keys, kind="stable")
    sorted_keys, sorted_masks = all_keys[order], all_masks[order]
    keys, first = np.unique(sorted_keys, return_index=True)
    masks = np.bitwise_or.reduceat(sorted_masks, first) if len(first) else np.empty(0, np.uint8)
    u, v = (keys // n).astype(np.uint32), (keys % n).astype(np.uint32)
    rows = np.concatenate((u, v))
    neighbors = np.concatenate((v, u))
    adjacency_order = np.lexsort((neighbors, rows))
    degree = np.bincount(rows.astype(np.int64), minlength=n).astype(np.int64)
    indptr = np.empty(n + 1, np.int64)
    indptr[0], indptr[1:] = 0, np.cumsum(degree)
    return {"edge_u": u, "edge_v": v, "edge_mask": masks,
            "indptr": indptr, "indices": neighbors[adjacency_order], "edge_keys": keys}


def boundary_sensitivity(data: dict, resource: str, gap_ticks: int, radius_ticks=2_000) -> dict:
    """Inspect connected AND unconnected resource pairs around the gap equality."""
    groups = defaultdict(list)
    for node, identity in enumerate(data[resource].tolist()):
        groups[identity].append(node)
    closest, near_count, near_conflicting, near_compatible, exact_equal = None, 0, 0, 0, 0
    examples = []
    for identity, members in groups.items():
        order = np.array(sorted(members, key=lambda node: (int(data["start_ticks"][node]), node)), np.int64)
        starts = data["start_ticks"][order]
        for position, node in enumerate(order[:-1]):
            target = int(data["end_ticks"][node]) + gap_ticks
            insertion = int(np.searchsorted(starts, target, side="left"))
            for j in (insertion - 1, insertion):
                if position < j < len(order):
                    margin = int(starts[j]) - target
                    if closest is None or abs(margin) < closest[0]:
                        closest = (abs(margin), margin, int(node), int(order[j]), identity)
            low = max(position + 1, int(np.searchsorted(starts, target - radius_ticks, side="left")))
            high = int(np.searchsorted(starts, target + radius_ticks, side="right"))
            for other in order[low:high]:
                margin = int(data["start_ticks"][other]) - target
                near_count += 1
                near_conflicting += int(margin < 0)
                near_compatible += int(margin >= 0)
                exact_equal += int(margin == 0)
                if len(examples) < 20:
                    examples.append({"earlier_contact": str(data["contact_id"][node]),
                                     "later_contact": str(data["contact_id"][other]),
                                     "resource_id": identity, "signed_margin_ticks": margin,
                                     "resource_conflict": margin < 0})
    closest_row = None if closest is None else {
        "absolute_margin_ticks": closest[0], "signed_margin_ticks": closest[1],
        "earlier_contact": str(data["contact_id"][closest[2]]),
        "later_contact": str(data["contact_id"][closest[3]]), "resource_id": closest[4],
    }
    return {"resource_field": resource, "gap_ticks": gap_ticks,
            "near_boundary_radius_ticks": radius_ticks, "near_boundary_pair_count": near_count,
            "near_conflicting_pairs": near_conflicting, "near_compatible_pairs": near_compatible,
            "exact_gap_equality_pairs": exact_equal, "closest_pair": closest_row, "examples": examples,
            "interpretation": "A diagnostic neighborhood around the numerical switching-gap boundary, including nonedges. STK Time Convergence is not treated as a rigorous physical error bound."}


def base9_full(data: dict, graph: dict, ground_gap_ticks: int, satellite_gap_ticks: int) -> tuple[np.ndarray, dict]:
    n, weights = len(data["contact_id"]), data["weight_ticks"]
    u, v = graph["edge_u"], graph["edge_v"]
    neighbor_sums, neighbor_maxima = np.zeros(n, np.int64), np.zeros(n, np.int64)
    np.add.at(neighbor_sums, u, weights[v])
    np.add.at(neighbor_sums, v, weights[u])
    np.maximum.at(neighbor_maxima, u, weights[v])
    np.maximum.at(neighbor_maxima, v, weights[u])
    degrees = np.diff(graph["indptr"])
    total = sum(int(value) for value in weights)
    vectors = np.column_stack((
        weights, weights, degrees, neighbor_sums, neighbor_maxima,
        total - weights - neighbor_sums,
        np.full(n, ground_gap_ticks, np.int64), np.full(n, satellite_gap_ticks, np.int64),
        np.full(n, n, np.int64),
    ))
    _, inverse, counts = np.unique(vectors, axis=0, return_inverse=True, return_counts=True)
    classes = [np.flatnonzero(inverse == index).tolist() for index in np.flatnonzero(counts > 1)]
    # Adjacency is the actual competing-action condition, not merely a collision.
    edge_keys = set(graph["edge_keys"].tolist()) if classes else set()
    aliases = []
    competing_pairs = 0
    for members in classes:
        pairs = [[int(a), int(b)] for k, a in enumerate(members) for b in members[k + 1:] if a * n + b in edge_keys]
        competing_pairs += len(pairs)
        aliases.append({"nodes": members, "contact_ids": data["contact_id"][members].tolist(),
                        "vector_integer_coordinates": vectors[members[0]].tolist(), "competing_pairs": pairs})
    census = {
        "feature_semantics_namespace": "exact_microtick_base9_v1",
        "feature_names": list(BASE9_NAMES),
        "feature_units": ["microsecond", "microsecond", "count", "microsecond", "microsecond",
                          "microsecond", "microsecond", "microsecond", "count"],
        "semantic_scope": "all retained full contacts active; F=X=empty; exact endpoint-difference integer weights",
        "alias_classes": len(classes), "aliased_action_occurrences": int(counts[counts > 1].sum()),
        "competing_alias_pairs": competing_pairs, "classes": aliases,
        "requires_oracle_for_strict_obstruction": bool(classes),
        "strict_obstruction_established": False,
        "interpretation": (
            "No full-graph base9 collisions; this does not prove absence of multi-state quotient cycles."
            if not classes else "Exact full-graph collisions are candidates only; no strict preference has been inferred."
        ),
        "old_code_semantics": {
            "names": list(BASE9_NAMES),
            "reference": "cipheur/graph_features.py:_BASE_EXPRESSIONS and _FeatureState.feature_values; cipheur/compiled.py:_float_term",
            "difference": "Earlier reference converts weight terms to binary float for math.fsum; duration subtracts binary float endpoints. This dataset freezes rational seconds as microticks; no new scientific evidence is inherited from older float equality classes.",
            "note": "No endpoint precision coarsening is performed by this builder. Six-decimal serialization is fixed upstream before labels; its physical numerical tolerance remains STK Access's stated 0.001 seconds.",
        },
        "actual_head_namespace": "fraction_seconds_binary_fsum_base9_v1; distinct from this exact-integer census",
        "cross_configuration_note": "station_gap is an explicit base9 coordinate; different ground-gap configurations cannot alias as complete vectors.",
    }
    return vectors, census


def degree_distribution(degrees: np.ndarray) -> dict:
    values, counts = np.unique(degrees, return_counts=True)
    return {
        "minimum": int(degrees.min()), "maximum": int(degrees.max()),
        "mean": float(degrees.mean()), "median": float(np.median(degrees)),
        "quantiles": {str(q): float(np.quantile(degrees, q)) for q in (0.05, 0.25, 0.75, 0.95, 0.99)},
        "histogram": [[int(value), int(count)] for value, count in zip(values, counts)],
    }


def component_sizes(n: int, u: np.ndarray, v: np.ndarray) -> list[int]:
    parent, sizes = list(range(n)), [1] * n

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in zip(u.tolist(), v.tolist()):
        a, b = find(a), find(b)
        if a == b:
            continue
        if sizes[a] < sizes[b]:
            a, b = b, a
        parent[b] = a
        sizes[a] += sizes[b]
    return sorted((sizes[node] for node in range(n) if find(node) == node), reverse=True)


def write_node_mapping(path: Path, rows: list[dict], data: dict) -> None:
    fields = ["node_index", "contact_id", "pass_id", "source_group", "geometry_id", "replicate_id",
              "satellite_id", "site_id", "antenna_id", "start_seconds", "end_seconds", "weight_seconds",
              "start_ticks", "end_ticks", "weight_ticks"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow({"node_index": index, **{name: row[name] for name in fields if name in row},
                             "start_seconds": sec_text(data["start_ticks"][index]),
                             "end_seconds": sec_text(data["end_ticks"][index]),
                             "weight_seconds": sec_text(data["weight_ticks"][index]),
                             "start_ticks": int(data["start_ticks"][index]),
                             "end_ticks": int(data["end_ticks"][index]),
                             "weight_ticks": int(data["weight_ticks"][index])})


def build_source(contacts_path: Path, output_root: Path = ROOT, source_id: str | None = None,
                 ground_gaps=(340, 680, 1200, 1800), replace=False) -> dict:
    parameters_path = output_root / "source_plan" / "CIPHEUR_parameters.json"
    parameters = json.loads(parameters_path.read_text(encoding="utf-8"))
    data, source_metadata, rows = read_contacts(contacts_path, parameters, source_id)
    source_id = source_metadata["source_id"]
    source_directory = output_root / "graphs" / source_id
    if (source_directory / "summary.json").exists() and not replace:
        raise FileExistsError(f"Graph source already exists: {source_directory}; use --replace explicitly to rebuild")
    source_directory.mkdir(parents=True, exist_ok=True)
    write_node_mapping(source_directory / "contacts_nodes.csv", rows, data)
    write_json(source_directory / "source_metadata.json", source_metadata)
    satellite_gap = parameters["common_settings"]["satellite_switching_gap_seconds"]
    if satellite_gap != 150:
        raise ValueError("P0 fixed satellite gap must remain 150 seconds")
    previous, comparison_rows, graph_rows = None, [], []
    initial_keys, initial_m = None, None
    for gap in sorted(ground_gaps):
        started = perf_counter()
        config_id = f"g{gap:04d}"
        gap_ticks, sat_ticks = ticks(str(gap)), ticks(str(satellite_gap))
        graph = build_edges(data, gap_ticks, sat_ticks)
        vectors, census = base9_full(data, graph, gap_ticks, sat_ticks)
        if initial_keys is None:
            initial_keys, initial_m = graph["edge_keys"], len(graph["edge_keys"])
        if previous is not None:
            old_gap, old_keys = previous
            deleted = np.setdiff1d(old_keys, graph["edge_keys"], assume_unique=True)
            added = np.setdiff1d(graph["edge_keys"], old_keys, assume_unique=True)
            if len(deleted):
                raise AssertionError("Increasing ground gap deleted graph edges")
            added_masks = graph["edge_mask"][np.searchsorted(graph["edge_keys"], added)]
            if len(added_masks) and not np.all(added_masks == (EDGE_MASK["ground"] | EDGE_MASK["gap_only"])):
                raise AssertionError("A pure ground-gap intervention introduced a nonground or overlap edge")
            comparison_rows.append({"from_ground_gap_seconds": old_gap, "to_ground_gap_seconds": gap,
                                    "deleted_edges": 0, "added_edges": len(added),
                                    "r_E": len(added) / max(1, len(old_keys)), "monotone": True,
                                    "all_added_edges_are_ground_gap_only": True})
        increase_from_base = np.setdiff1d(graph["edge_keys"], initial_keys, assume_unique=True)
        n, m = len(data["contact_id"]), len(graph["edge_u"])
        sizes = component_sizes(n, graph["edge_u"], graph["edge_v"])
        degree = np.diff(graph["indptr"])
        if int(degree.sum()) != 2 * m:
            raise AssertionError("Degree-sum invariant failed")
        payload = {**data, **{key: value for key, value in graph.items() if key != "edge_keys"},
                   "base9_integer_coordinates": vectors,
                   "ground_gap_ticks": np.array(gap_ticks, np.int64),
                   "satellite_gap_ticks": np.array(sat_ticks, np.int64),
                   "ticks_per_second": np.array(TICKS_PER_SECOND, np.int64),
                   "source_id": np.array(source_id), "source_group": np.array(source_metadata["source_group"]),
                   "geometry_id": np.array(source_metadata["geometry_id"]),
                   "replicate_id": np.array(source_metadata["replicate_id"]),
                   "split": np.array(source_metadata["split"]), "config_id": np.array(config_id),
                   "builder_version": np.array(VERSION)}
        npz_path = source_directory / f"{config_id}.npz"
        np.savez_compressed(npz_path, **payload)
        stats = {
            "n": n, "m": m, "average_degree_2m_over_n": 2 * m / n,
            "density": 2 * m / (n * (n - 1)) if n > 1 else 0,
            "degree_distribution": degree_distribution(degree),
            "component_count": len(sizes), "component_sizes_descending": sizes,
            "edge_mask_counts": {name: int(np.count_nonzero(graph["edge_mask"] & bit)) for name, bit in EDGE_MASK.items()},
            "edge_mask_exact_histogram": {str(mask): int(np.count_nonzero(graph["edge_mask"] == mask))
                                          for mask in np.unique(graph["edge_mask"]).tolist()},
            "r_E_from_smallest_gap": len(increase_from_base) / max(1, initial_m),
            "near_boundary_diagnostics": {
                "ground": boundary_sensitivity(data, "antenna_id", gap_ticks),
                "satellite": boundary_sensitivity(data, "satellite_id", sat_ticks),
            },
        }
        metadata = {
            "version": VERSION, "source_id": source_id, "source_group": source_metadata["source_group"],
            "split": source_metadata["split"], "config_id": config_id,
            "ground_gap_seconds": gap, "satellite_gap_seconds": satellite_gap,
            "model": parameters["common_settings"]["model"],
            "conflict_rule": parameters["common_settings"]["edge_rule"],
            "interval_semantics": "entire unmodified half-open interval [s,e), capacity one; equality at end+gap is compatible",
            "tick_resolution_seconds": "0.000001", "floating_point_edge_tests": False,
            "edge_mask": EDGE_MASK,
            "edge_mask_note": "Ground/satellite bits may coexist. Overlap means later start < earlier end; gap_only means no interval overlap but insufficient switching gap. These bits describe shared-resource conflicts, not physical radio links.",
            "node_mapping_sha256": source_metadata["node_mapping_sha256"],
            "weight_ticks_sha256": source_metadata["weight_ticks_sha256"],
            "raw_contacts_sha256": source_metadata["raw_contacts_sha256"],
            "parameters_sha256": sha256_file(parameters_path),
            "builder_sha256": sha256_file(Path(__file__)),
            "edge_arrays_sha256": array_hash(graph["edge_u"], graph["edge_v"], graph["edge_mask"]),
            "npz_sha256": sha256_file(npz_path), "stats": stats,
            "base9_census_file": f"{config_id}_base9_census.json",
            "build_seconds": perf_counter() - started,
        }
        write_json(source_directory / f"{config_id}_base9_census.json", census)
        write_json(source_directory / f"{config_id}.json", metadata)
        graph_rows.append(metadata)
        previous = gap, graph["edge_keys"]
    summary = {"version": VERSION, "source_id": source_id, "source_metadata": source_metadata,
               "graphs": graph_rows, "monotonicity": comparison_rows,
               "same_vertex_and_weight_hash_for_every_config": True,
               "uses_old_legacy_conflict_predicate": False,
               "optimization_or_oracle_executed": False}
    write_json(source_directory / "summary.json", summary)
    return summary


def aggregate_sources(output_root: Path = ROOT) -> dict:
    """Summarize only completed graph sources; no oracle or TEST-label access."""
    summaries = [json.loads(path.read_text(encoding="utf-8"))
                 for path in sorted((output_root / "graphs").glob("*/summary.json"))]
    occurrences = defaultdict(list)
    all_graphs, source_groups = [], {}
    for summary in summaries:
        source_id = summary["source_id"]
        source = summary["source_metadata"]
        source_groups.setdefault(source["source_group"], []).append(source_id)
        first_graph = load_graph(output_root / "graphs" / source_id / f"{summary['graphs'][0]['config_id']}.npz")
        for index, weight in enumerate(first_graph["weight_ticks"].tolist()):
            occurrences[weight].append({"source_id": source_id, "node_index": index,
                                        "contact_id": str(first_graph["contact_id"][index])})
        for graph in summary["graphs"]:
            census = json.loads((output_root / "graphs" / source_id / graph["base9_census_file"]).read_text(encoding="utf-8"))
            all_graphs.append({"source_id": source_id, "source_group": source["source_group"],
                              "split": source["split"], "geometry_id": source["geometry_id"],
                              "replicate_id": source["replicate_id"], "config_id": graph["config_id"],
                              "n": graph["stats"]["n"], "m": graph["stats"]["m"],
                              "mean_degree": graph["stats"]["average_degree_2m_over_n"],
                              "r_E_from_g0340": graph["stats"]["r_E_from_smallest_gap"],
                              "base9_alias_classes": census["alias_classes"],
                              "base9_aliased_actions": census["aliased_action_occurrences"],
                              "base9_competing_alias_pairs": census["competing_alias_pairs"],
                              "ground_near_boundary_pairs": graph["stats"]["near_boundary_diagnostics"]["ground"]["near_boundary_pair_count"],
                              "satellite_near_boundary_pairs": graph["stats"]["near_boundary_diagnostics"]["satellite"]["near_boundary_pair_count"]})
    repeated = [{"duration_ticks": weight, "occurrences": members}
                for weight, members in sorted(occurrences.items()) if len(members) > 1]
    result = {
        "builder_version": VERSION, "completed_opportunity_libraries": len(summaries),
        "physical_source_groups": source_groups, "source_group_count": len(source_groups),
        "graph_count": len(all_graphs), "graphs": all_graphs,
        "contact_occurrences_without_repeating_gap_configurations": sum(len(rows) for rows in occurrences.values()),
        "distinct_duration_values_across_libraries": len(occurrences),
        "cross_library_duplicate_duration_classes": len(repeated),
        "duplicate_duration_classes": repeated,
        "all_duration_values_injective_across_completed_libraries": not repeated,
        "inference_limit": "Injective duration excludes exact equal complete-base9 for distinct persistent contacts across these libraries, in any residual states. It does not exclude repeated feature vectors for the same contact across states or prove that a multi-state demanded quotient has no cycles. Complete strict requirements and exact equality joins belong to the evidence stage.",
        "statistical_unit": "source_group; uniform/paired companions and all gaps remain together",
        "no_oracle_or_optimizer_executed": True,
    }
    analysis_directory = output_root / "analysis"
    analysis_directory.mkdir(parents=True, exist_ok=True)
    write_json(analysis_directory / "graph_screen_summary.json", result)
    if all_graphs:
        with (analysis_directory / "graph_screen.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(all_graphs[0]))
            writer.writeheader()
            writer.writerows(all_graphs)
    return result


def load_graph(path: str | Path) -> dict:
    """Load persistent arrays without a retained ZipFile or pickle dependency."""
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def self_test() -> dict:
    # All synthetic numbers here are test fixtures, never research contacts.
    # a contains b; a and c share a start; d begins exactly at a.end+gap.
    data = {
        "contact_id": np.array(["a", "b", "c", "d", "e"]),
        "antenna_id": np.array(["g", "g", "g", "g", "h"]),
        "satellite_id": np.array(["sa", "sb", "sc", "sd", "sa"]),
        "start_ticks": np.array([0, 2, 0, 12, 11], np.int64),
        "end_ticks": np.array([10, 3, 4, 20, 15], np.int64),
    }
    data["weight_ticks"] = data["end_ticks"] - data["start_ticks"]
    graph = build_edges(data, 2, 2)
    actual = {(int(a), int(b)): int(mask) for a, b, mask in zip(graph["edge_u"], graph["edge_v"], graph["edge_mask"])}
    assert actual == {(0, 1): 5, (0, 2): 5, (0, 4): 10, (1, 2): 5}, actual
    assert (0, 3) not in actual  # Exact switching-gap equality is compatible.
    stricter = build_edges(data, 3, 2)
    assert set(graph["edge_keys"].tolist()) <= set(stricter["edge_keys"].tolist())
    assert (0, 3) in set(zip(stricter["edge_u"].tolist(), stricter["edge_v"].tolist()))
    assert ticks("1.000001") == 1_000_001
    try:
        ticks("1.0000001")
    except ValueError:
        pass
    else:
        raise AssertionError("Submicrosecond input was silently rounded")
    vectors, census = base9_full(data, graph, 2, 2)
    assert np.all(vectors[:, 0] == data["weight_ticks"])
    assert np.all(vectors[:, 1] == data["weight_ticks"])
    assert np.all(vectors[:, 3] + vectors[:, 5] + vectors[:, 0] == sum(data["weight_ticks"]))
    near = boundary_sensitivity(data, "antenna_id", 2, radius_ticks=0)
    assert near["exact_gap_equality_pairs"] == 1
    assert near["near_compatible_pairs"] == 1 and near["near_conflicting_pairs"] == 0
    return {"passed": True, "checks": ["containment", "same_start", "half_open_equality", "satellite_gap",
                                          "monotone_ground_gap", "no_time_coarsening", "exact_base9_partition",
                                          "boundary_sensitivity_includes_nonedges"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contacts", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source-id")
    parser.add_argument("--ground-gaps", default="340,680,1200,1800")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False))
    if args.contacts:
        summary = build_source(args.contacts, args.root, args.source_id,
                               tuple(int(value) for value in args.ground_gaps.split(",")), args.replace)
        print(json.dumps({"source_id": summary["source_id"], "graphs": [
            {"config": item["config_id"], "n": item["stats"]["n"], "m": item["stats"]["m"],
             "degree": item["stats"]["average_degree_2m_over_n"]} for item in summary["graphs"]]}, ensure_ascii=False))
    if args.aggregate:
        result = aggregate_sources(args.root)
        print(json.dumps({key: result[key] for key in ("completed_opportunity_libraries", "source_group_count", "graph_count", "cross_library_duplicate_duration_classes")}, ensure_ascii=False))
    if not args.contacts and not args.self_test and not args.aggregate:
        parser.error("Supply --contacts, --self-test or --aggregate")


if __name__ == "__main__":
    main()
