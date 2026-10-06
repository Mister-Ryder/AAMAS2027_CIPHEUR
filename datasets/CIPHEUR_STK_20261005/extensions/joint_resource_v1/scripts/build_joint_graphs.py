"""One preregistered two-axis resource intervention over the unchanged P0 contacts.

P0 files are read only. Existing A/G graph arrays are reused; only S/J are newly
built. This module never starts STK, runs an optimizer, or accesses labels.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import csv
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

EXTENSION_ROOT = Path(__file__).resolve().parents[1]
BASE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE_ROOT / "scripts"))
import build_graphs as p0

VERSION = "cipheur-joint-resource-factorial-v1"
SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
CONFIGS = (
    ("A", "g0340_s0150", 340, 150, "g0340"),
    ("G", "g1200_s0150", 1200, 150, "g1200"),
    ("S", "g0340_s0600", 340, 600, None),
    ("J", "g1200_s0600", 1200, 600, None),
)


def declare(extension_root: Path, base_root: Path) -> tuple[dict, Path]:
    """Freeze extension parameters before any new graph or label is computed."""
    value = {
        "version": VERSION, "development_only": True,
        "physical_source_reuse": list(SOURCES), "new_STK_propagation": False,
        "parent_parameters_sha256": p0.sha256_file(base_root / "source_plan" / "CIPHEUR_parameters.json"),
        "parent_graph_builder_sha256": p0.sha256_file(base_root / "scripts" / "build_graphs.py"),
        "configurations": [{"factorial_id": key, "config_id": tag,
                            "ground_gap_seconds": ground, "satellite_gap_seconds": satellite}
                           for key, tag, ground, satellite, _ in CONFIGS],
        "satellite_600_note": "Preregistered development stress value, not a measured hardware switching time.",
        "model": "Unchanged complete visibility intervals; satellite/antenna capacity one; symmetric resource gap conflicts.",
        "contact_and_weight_contract": "Same P0 vertices, resources, complete endpoints, and weight=end-start; no new rounding, slicing, reward reassignment, or tasks.",
        "integer_tick_seconds": "0.000001",
        "source_group_contract": "Both geometry companions and all configurations remain in their original TRAIN development source group; two source groups are not 16 independent replications.",
        "edge_lattice_identity": "E_A subset E_G and E_S; E_J = E_G union E_S.",
        "factor_overlap_definition": "(E_G minus E_A) intersection (E_S minus E_A), distinct from physical overlap intervals.",
        "new_numerical_diagnostics_only": "List every same-satellite pair within +/-0.002 seconds of the new satellite600 threshold, including nonedges. Root decides targeted STK calculations; no new STK calls here.",
        "no_label_access": True,
    }
    path = extension_root / "source_plan" / "extension_parameters.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError("Extension parameter declaration already exists with different values")
    else:
        p0.write_json(path, value)
    return value, path


def as_graph(payload: dict) -> dict:
    n = len(payload["contact_id"])
    return {"edge_u": payload["edge_u"], "edge_v": payload["edge_v"],
            "edge_mask": payload["edge_mask"], "indptr": payload["indptr"], "indices": payload["indices"],
            "edge_keys": payload["edge_u"].astype(np.int64) * n + payload["edge_v"].astype(np.int64)}


def stats_new(data: dict, graph: dict, ground: int, satellite: int) -> dict:
    n, m = len(data["contact_id"]), len(graph["edge_u"])
    degrees = np.diff(graph["indptr"])
    if int(degrees.sum()) != 2 * m:
        raise AssertionError("New graph degree-sum invariant failed")
    components = p0.component_sizes(n, graph["edge_u"], graph["edge_v"])
    return {
        "n": n, "m": m, "average_degree_2m_over_n": 2 * m / n,
        "density": 2 * m / (n * (n - 1)), "degree_distribution": p0.degree_distribution(degrees),
        "component_count": len(components), "component_sizes_descending": components,
        "edge_mask_counts": {name: int(np.count_nonzero(graph["edge_mask"] & bit))
                             for name, bit in p0.EDGE_MASK.items()},
        "edge_mask_exact_histogram": {str(mask): int(np.count_nonzero(graph["edge_mask"] == mask))
                                      for mask in np.unique(graph["edge_mask"]).tolist()},
        "near_boundary_diagnostics": {
            "ground": p0.boundary_sensitivity(data, "antenna_id", p0.ticks(str(ground))),
            "satellite": p0.boundary_sensitivity(data, "satellite_id", p0.ticks(str(satellite))),
        },
    }


def difference_and_monotonicity(low: dict, high: dict, expected_resource: str | None) -> dict:
    deleted = np.setdiff1d(low["edge_keys"], high["edge_keys"], assume_unique=True)
    added = np.setdiff1d(high["edge_keys"], low["edge_keys"], assume_unique=True)
    if len(deleted):
        raise AssertionError("Strengthening a nonnegative resource gap removed edges")
    masks = high["edge_mask"][np.searchsorted(high["edge_keys"], added)]
    if expected_resource:
        required = p0.EDGE_MASK[expected_resource] | p0.EDGE_MASK["gap_only"]
        if len(masks) and not np.all((masks & required) == required):
            raise AssertionError("New factor edges do not come from the declared gap axis")
    return {
        "added_edges": len(added), "deleted_edges": 0,
        "r_E": len(added) / max(1, len(low["edge_keys"])), "monotone": True,
        "expected_added_resource": expected_resource,
        "added_edge_mask_histogram": {str(mask): int(np.count_nonzero(masks == mask))
                                      for mask in np.unique(masks).tolist()},
    }


def complete_near_pairs(data: dict, resource: str, gap_ticks: int, radius=2_000) -> list[dict]:
    """All near-threshold pairs, with no diagnostic-example truncation."""
    groups = defaultdict(list)
    for node, identity in enumerate(data[resource].tolist()):
        groups[identity].append(node)
    result = []
    for identity in sorted(groups):
        order = np.array(sorted(groups[identity], key=lambda node: (int(data["start_ticks"][node]), node)), np.int64)
        starts = data["start_ticks"][order]
        for position, node in enumerate(order[:-1]):
            target = int(data["end_ticks"][node]) + gap_ticks
            lo = max(position + 1, int(np.searchsorted(starts, target - radius, side="left")))
            hi = int(np.searchsorted(starts, target + radius, side="right"))
            for other in order[lo:hi]:
                result.append({"earlier_node_index": int(node), "later_node_index": int(other),
                               "resource_id": identity,
                               "signed_margin_ticks": int(data["start_ticks"][other]) - target})
    return result


def contact_row(data: dict, node: int) -> dict:
    return {"node_index": node, "contact_id": str(data["contact_id"][node]),
            "satellite_id": str(data["satellite_id"][node]), "site_id": str(data["site_id"][node]),
            "antenna_id": str(data["antenna_id"][node]), "start_ticks": int(data["start_ticks"][node]),
            "end_ticks": int(data["end_ticks"][node]), "weight_ticks": int(data["weight_ticks"][node])}


def build_source(source: str, base_root: Path, extension_root: Path, declaration_path: Path) -> dict:
    out = extension_root / "graphs" / source
    if (out / "summary.json").exists():
        raise FileExistsError(f"Completed extension source already exists: {out}; no silent replacement")
    parameters = json.loads((base_root / "source_plan" / "CIPHEUR_parameters.json").read_text(encoding="utf-8"))
    raw_path = base_root / "raw" / source / "contacts.csv"
    data, source_metadata, rows = p0.read_contacts(raw_path, parameters, source)
    out.mkdir(parents=True, exist_ok=True)
    p0.write_node_mapping(out / "contacts_nodes.csv", rows, data)
    p0.write_json(out / "source_metadata.json", {**source_metadata, "extension_version": VERSION})
    graphs, graph_rows, censuses = {}, [], {}
    for key, tag, ground, satellite, parent_tag in CONFIGS:
        started = perf_counter()
        parent_npz_path = None
        if parent_tag is not None:
            parent_dir = base_root / "graphs" / source
            parent_npz_path = parent_dir / f"{parent_tag}.npz"
            payload = p0.load_graph(parent_npz_path)
            graph = as_graph(payload)
            stats = copy.deepcopy(json.loads((parent_dir / f"{parent_tag}.json").read_text(encoding="utf-8"))["stats"])
            census = json.loads((parent_dir / f"{parent_tag}_base9_census.json").read_text(encoding="utf-8"))
            vectors = payload["base9_integer_coordinates"]
        else:
            graph = p0.build_edges(data, p0.ticks(str(ground)), p0.ticks(str(satellite)))
            vectors, census = p0.base9_full(data, graph, p0.ticks(str(ground)), p0.ticks(str(satellite)))
            stats = stats_new(data, graph, ground, satellite)
            payload = {**data, **{name: value for name, value in graph.items() if name != "edge_keys"},
                       "base9_integer_coordinates": vectors,
                       "ground_gap_ticks": np.array(p0.ticks(str(ground)), np.int64),
                       "satellite_gap_ticks": np.array(p0.ticks(str(satellite)), np.int64),
                       "ticks_per_second": np.array(p0.TICKS_PER_SECOND, np.int64),
                       "source_id": np.array(source), "source_group": np.array(source_metadata["source_group"]),
                       "geometry_id": np.array(source_metadata["geometry_id"]),
                       "replicate_id": np.array(source_metadata["replicate_id"]), "split": np.array(source_metadata["split"])}
        stats.pop("r_E_from_smallest_gap", None)
        census["cross_configuration_note"] = "Both ground and satellite gap are explicit complete-base9 coordinates; changing either coordinate prevents complete-vector equality across those configurations. Restricted states still need their own demanded quotient."
        payload["config_id"] = np.array(tag)
        payload["factorial_id"] = np.array(key)
        payload["builder_version"] = np.array(VERSION)
        for field in ("contact_id", "pass_id", "satellite_id", "site_id", "antenna_id", "start_ticks", "end_ticks", "weight_ticks"):
            if not np.array_equal(payload[field], data[field]):
                raise AssertionError(f"Extension changed frozen source field: {field}")
        path = out / f"{tag}.npz"
        np.savez_compressed(path, **payload)
        metadata = {
            "version": VERSION, "source_id": source, "source_group": source_metadata["source_group"],
            "split": source_metadata["split"], "factorial_id": key, "config_id": tag,
            "ground_gap_seconds": ground, "satellite_gap_seconds": satellite,
            "satellite600_is_development_pressure_not_hardware_measurement": True,
            "model": parameters["common_settings"]["model"],
            "conflict_rule": parameters["common_settings"]["edge_rule"],
            "tick_resolution_seconds": "0.000001", "floating_point_edge_tests": False,
            "edge_mask": p0.EDGE_MASK, "node_mapping_sha256": source_metadata["node_mapping_sha256"],
            "weight_ticks_sha256": source_metadata["weight_ticks_sha256"],
            "raw_contacts_sha256": source_metadata["raw_contacts_sha256"],
            "raw_manifest_sha256": source_metadata["stk_manifest_sha256"],
            "extension_parameters_sha256": p0.sha256_file(declaration_path),
            "builder_sha256": p0.sha256_file(Path(__file__)),
            "parent_graph_builder_sha256": p0.sha256_file(base_root / "scripts" / "build_graphs.py"),
            "reused_parent_graph_arrays": parent_tag is not None,
            "parent_npz_sha256": p0.sha256_file(parent_npz_path) if parent_npz_path else None,
            "edge_arrays_sha256": p0.array_hash(graph["edge_u"], graph["edge_v"], graph["edge_mask"]),
            "npz_sha256": p0.sha256_file(path), "stats": stats,
            "base9_census_file": f"{tag}_base9_census.json", "build_seconds": perf_counter() - started,
        }
        p0.write_json(out / f"{tag}.json", metadata)
        p0.write_json(out / f"{tag}_base9_census.json", census)
        graphs[key], censuses[key] = graph, census
        graph_rows.append(metadata)
    A, G, S, J = (graphs[key] for key in ("A", "G", "S", "J"))
    transitions = {
        "A_to_G_ground": difference_and_monotonicity(A, G, "ground"),
        "A_to_S_satellite": difference_and_monotonicity(A, S, "satellite"),
        "G_to_J_satellite": difference_and_monotonicity(G, J, "satellite"),
        "S_to_J_ground": difference_and_monotonicity(S, J, "ground"),
        "A_to_J_joint": difference_and_monotonicity(A, J, None),
    }
    dg = np.setdiff1d(G["edge_keys"], A["edge_keys"], assume_unique=True)
    ds = np.setdiff1d(S["edge_keys"], A["edge_keys"], assume_unique=True)
    both = np.intersect1d(dg, ds, assume_unique=True)
    combined = np.union1d(G["edge_keys"], S["edge_keys"])
    if not np.array_equal(combined, J["edge_keys"]):
        raise AssertionError("Factorial edge lattice does not satisfy E_J = E_G union E_S")
    if len(J["edge_keys"]) != len(A["edge_keys"]) + len(dg) + len(ds) - len(both):
        raise AssertionError("Joint edge count does not satisfy exact inclusion-exclusion")
    n = len(data["contact_id"])
    overlap_rows = [[int(key // n), int(key % n)] for key in both]
    def axis_degrees(keys):
        return np.bincount(np.concatenate((keys // n, keys % n)), minlength=n).astype(np.int64)
    degree_ground, degree_satellite, degree_both = (axis_degrees(keys) for keys in (dg, ds, both))
    mixed_slots = degree_ground * degree_satellite
    with (out / "node_axis_degrees.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["node_index", "contact_id", "new_ground_degree_dG", "new_satellite_degree_dS",
                         "both_axis_added_edge_degree", "dG_times_dS", "distinct_edge_factor_slots"])
        writer.writerows([index, str(data["contact_id"][index]), int(degree_ground[index]), int(degree_satellite[index]),
                          int(degree_both[index]), int(mixed_slots[index]), int(mixed_slots[index] - degree_both[index])]
                         for index in range(n))
    interaction = {
        "new_ground_axis_edges": len(dg), "new_satellite_axis_edges": len(ds),
        "axis_added_edge_intersection": len(both), "ground_only_new_edges": len(dg) - len(both),
        "satellite_only_new_edges": len(ds) - len(both),
        "both_axis_new_edge_node_pairs": overlap_rows,
        "joint_new_edges": len(J["edge_keys"]) - len(A["edge_keys"]),
        "exact_union_identity": True, "exact_count_inclusion_exclusion": True,
        "edge_count_interaction_mJ_minus_mG_minus_mS_plus_mA": -len(both),
        "nodes_with_both_new_ground_and_new_satellite_degree_positive": int(np.count_nonzero((degree_ground > 0) & (degree_satellite > 0))),
        "sum_dG_times_dS_mixed_new_edge_wedges": int(mixed_slots.sum()),
        "mixed_distinct_edge_factor_slots": int((mixed_slots - degree_both).sum()),
        "mixed_wedge_note": "sum(dG*dS) counts common-center G/S-typed incidence slots, not independent samples or proven optimization interactions. If an edge lies in both added sets, the same-edge slots are removed in mixed_distinct_edge_factor_slots.",
        "node_axis_degree_csv": "node_axis_degrees.csv",
        "interpretation": "Overlap counts a shared graph edge newly introduced by either factor; zero does not prove additive scheduling objectives or absence of joint preference effects.",
    }
    near_records = []
    all_sets = {key: set(value["edge_keys"].tolist()) for key, value in graphs.items()}
    for pair in complete_near_pairs(data, "satellite_id", p0.ticks("600")):
        earlier, later = pair["earlier_node_index"], pair["later_node_index"]
        lo, hi = sorted((earlier, later))
        packed = lo * n + hi
        same_antenna = data["antenna_id"][earlier] == data["antenna_id"][later]
        ground_margin = int(data["start_ticks"][later] - data["end_ticks"][earlier]) if same_antenna else None
        near_records.append({
            **pair, "source_id": source, "source_group": source_metadata["source_group"],
            "epoch_utc": source_metadata["epoch_utc"], "scene_file": json.loads((raw_path.parent / "manifest.json").read_text(encoding="utf-8"))["scene_file"],
            "threshold_resource": "satellite", "satellite_gap_seconds": 600,
            "earlier": contact_row(data, earlier), "later": contact_row(data, later),
            "same_ground_antenna": bool(same_antenna),
            "ground340_signed_margin_ticks": ground_margin - p0.ticks("340") if same_antenna else None,
            "ground1200_signed_margin_ticks": ground_margin - p0.ticks("1200") if same_antenna else None,
            "edge_state_by_factorial_config": {key: packed in value for key, value in all_sets.items()},
            "satellite600_resource_conflict": pair["signed_margin_ticks"] < 0,
            "original_raw_manifest_sha256": source_metadata["stk_manifest_sha256"],
            "original_contacts_sha256": source_metadata["raw_contacts_sha256"],
        })
    if len(near_records) != graph_rows[2]["stats"]["near_boundary_diagnostics"]["satellite"]["near_boundary_pair_count"]:
        raise AssertionError("Full new satellite near-pair list and diagnostic count disagree")
    summary = {
        "version": VERSION, "source_id": source, "source_metadata": source_metadata,
        "graphs": graph_rows, "transitions": transitions, "axis_overlap": interaction,
        "new_satellite600_near_pairs": near_records,
        "same_vertex_and_weight_hash_for_every_config": True,
        "original_P0_files_modified": False, "new_STK_or_oracle_calls": False,
    }
    p0.write_json(out / "summary.json", summary)
    return summary


def aggregate(extension_root: Path) -> dict:
    summaries = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((extension_root / "graphs").glob("*/summary.json"))]
    graph_rows, sources, near_records, chunks = [], [], [], []
    for summary in summaries:
        source = summary["source_id"]
        sources.append({"source_id": source, "source_group": summary["source_metadata"]["source_group"],
                        "n": summary["source_metadata"]["contact_count"], "axis_overlap": summary["axis_overlap"],
                        "transitions": summary["transitions"]})
        near_records.extend(summary["new_satellite600_near_pairs"])
        for graph in summary["graphs"]:
            path = extension_root / "graphs" / source / f"{graph['config_id']}.npz"
            data = p0.load_graph(path)
            chunks.append(data["base9_integer_coordinates"])
            census = json.loads((path.parent / graph["base9_census_file"]).read_text(encoding="utf-8"))
            graph_rows.append({"source_id": source, "source_group": graph["source_group"],
                               "factorial_id": graph["factorial_id"], "config_id": graph["config_id"],
                               "ground_gap_seconds": graph["ground_gap_seconds"], "satellite_gap_seconds": graph["satellite_gap_seconds"],
                               "n": graph["stats"]["n"], "m": graph["stats"]["m"],
                               "mean_degree": graph["stats"]["average_degree_2m_over_n"],
                               "components": graph["stats"]["component_count"], "full_base9_alias_classes": census["alias_classes"],
                               "new_satellite600_near_pair_count": graph["stats"]["near_boundary_diagnostics"]["satellite"]["near_boundary_pair_count"] if graph["satellite_gap_seconds"] == 600 else 0})
    if not graph_rows:
        raise ValueError("No completed extension graphs")
    vectors = np.concatenate(chunks)
    _, counts = np.unique(vectors, axis=0, return_counts=True)
    result = {
        "version": VERSION, "opportunity_libraries": len(summaries), "graphs": graph_rows,
        "sources": sources, "new_satellite600_near_pair_count": len(near_records),
        "full_graph_integer_base9_census": {"namespace": "exact_microtick_base9_v1", "occurrences": len(vectors),
                                           "unique_vectors": len(counts), "alias_classes": int(np.count_nonzero(counts > 1)),
                                           "scope": "All contacts active and empty boundary only; no actual restricted-state demanded quotient or G2 conclusion."},
        "new_STK_propagation": False, "parent_P0_unchanged": True,
    }
    p0.write_json(extension_root / "analysis" / "joint_graph_summary.json", result)
    p0.write_json(extension_root / "analysis" / "new_satellite600_near_boundaries.json", {
        "version": VERSION, "threshold_resource": "satellite", "gap_seconds": 600,
        "diagnostic_radius_ticks": 2_000, "record_count": len(near_records), "records": near_records,
        "no_new_STK_calls_performed": True, "root_decides_targeted_checks": True,
        "interpretation": "Numerical boundary neighborhood, not a rigorous physical error bound; original frozen contacts and graph edges remain unchanged.",
    })
    with (extension_root / "analysis" / "joint_graph_screen.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(graph_rows[0]))
        writer.writeheader()
        writer.writerows(graph_rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", type=Path, default=BASE_ROOT)
    parser.add_argument("--root", type=Path, default=EXTENSION_ROOT)
    parser.add_argument("--sources", default=",".join(SOURCES))
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()
    if not args.aggregate_only:
        _, declaration_path = declare(args.root, args.base_root)
        for source in args.sources.split(","):
            if source not in SOURCES:
                raise ValueError("Unregistered source for the single extension")
            summary = build_source(source, args.base_root, args.root, declaration_path)
            print(json.dumps({"source_id": source, "edges": {row["factorial_id"]: row["stats"]["m"] for row in summary["graphs"]},
                              "axis_overlap": summary["axis_overlap"], "new_satellite_near_pair_count": len(summary["new_satellite600_near_pairs"])}, ensure_ascii=False), flush=True)
    result = aggregate(args.root)
    print(json.dumps({"libraries": result["opportunity_libraries"], "graphs": len(result["graphs"]),
                      "new_satellite600_near_pairs": result["new_satellite600_near_pair_count"],
                      "full_graph_integer_base9_census": result["full_graph_integer_base9_census"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
