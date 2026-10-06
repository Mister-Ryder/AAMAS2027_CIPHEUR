"""Build only the eight declared VAL/TEST input graphs; no labels or optimization.

Reads new, successful STK physical sources from the original data root. Outputs
only to perf_dataset_v1/graphs and keeps all pre-existing graph indexes intact.
No feature-selection census, oracle, LLM, heuristic score, or solver is called.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

PERF_ROOT = Path(__file__).resolve().parents[1]
BASE_ROOT = PERF_ROOT.parent
sys.path.insert(0, str(BASE_ROOT / "scripts"))
sys.path.insert(0, str(BASE_ROOT / "extensions" / "heterogeneous_ground_v1" / "scripts"))
import build_graphs as p0
import build_heterogeneous_graphs as hetero

VERSION = "cipheur-heldout-perf-input-graphs-v1"
SOURCES = ("CP-AU-r006", "CP-AP-r006", "CP-AU-r008", "CP-AP-r008", "CP-AU-r009", "CP-AP-r009")
CONFIGS = (
    ("g0340", 340, 340, "uniform", ["A"]),
    ("g0680", 680, 680, "uniform", []),
    ("g1200", 1200, 1200, "uniform", ["J"]),
    ("g1800", 1800, 1800, "uniform_stress", []),
    ("gW1200_gE0340_s0150", 1200, 340, "heterogeneous", ["W"]),
    ("gW0340_gE1200_s0150", 340, 1200, "heterogeneous", ["E"]),
    ("gW0680_gE1200_s0150", 680, 1200, "unseen_mixed", []),
    ("gW1200_gE0680_s0150", 1200, 680, "unseen_mixed", []),
)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def declaration(parameters, groups):
    value = {
        "version": VERSION, "source_ids": list(SOURCES),
        "parent_parameters_sha256": p0.sha256_file(BASE_ROOT / "source_plan" / "CIPHEUR_parameters.json"),
        "satellite_gap_seconds": 150, "station_gap_mode": "per_antenna",
        "antenna_group": groups,
        "group_definition": {"west_longitudes_deg": [88, 94, 100], "east_longitudes_deg": [106, 112, 118]},
        "configurations": [{"config_id": tag, "west_gap_seconds": west, "east_gap_seconds": east,
                            "family": family, "factorial_aliases": aliases,
                            "station_gap_by_antenna_seconds": hetero.station_map(groups, west, east)}
                           for tag, west, east, family, aliases in CONFIGS],
        "unique_configurations_per_physical_source": 8,
        "A_J_deduplication": "A references g0340; J references g1200. Do not count duplicate A/J graph copies.",
        "physical_contract": "Original full windows, exact frozen microticks, capacity one, duration=end-start; no new truncation, quantization, weights or visibility geometry.",
        "test_policy": "Input construction/QC only; TEST evidence, tuning, heuristic scores and evaluation remain barred until every scoring program is frozen by the root workflow.",
        "no_labels_no_optimizer_no_LLM": True,
    }
    path = PERF_ROOT / "source_plan" / "perf_graph_parameters.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RuntimeError("The fixed performance graph configuration declaration changed")
    else:
        write_json(path, value)
    return path


def full_active_coordinates(data, graph, local_gaps):
    """Deterministic interface coordinates only; no fit, ranking, alias census."""
    n, weights = len(data["contact_id"]), data["weight_ticks"]
    neighbor_sums, maxima = np.zeros(n, np.int64), np.zeros(n, np.int64)
    u, v = graph["edge_u"], graph["edge_v"]
    np.add.at(neighbor_sums, u, weights[v])
    np.add.at(neighbor_sums, v, weights[u])
    np.maximum.at(maxima, u, weights[v])
    np.maximum.at(maxima, v, weights[u])
    total = sum(int(w) for w in weights)
    return np.column_stack((weights, weights, np.diff(graph["indptr"]), neighbor_sums, maxima,
                            total - weights - neighbor_sums, local_gaps,
                            np.full(n, p0.ticks("150"), np.int64), np.full(n, n, np.int64)))


def integrity(data, graph, local_gaps):
    n, m = len(data["contact_id"]), len(graph["edge_u"])
    u, v, keys = graph["edge_u"], graph["edge_v"], graph["edge_keys"]
    if len(keys) != m or not np.all(u < v) or (m and not np.all(keys[1:] > keys[:-1])):
        raise AssertionError("Graph has duplicate, unordered or invalid edges")
    if len(graph["indices"]) != 2 * m or int(graph["indptr"][-1]) != 2 * m:
        raise AssertionError("CSR degree-sum/length invariant failed")
    # Check every published edge against the actual per-resource strict rule.
    earlier_u = (data["start_ticks"][u] < data["start_ticks"][v]) | (
        (data["start_ticks"][u] == data["start_ticks"][v]) & (u < v))
    earlier, later = np.where(earlier_u, u, v), np.where(earlier_u, v, u)
    gap = data["start_ticks"][later] - data["end_ticks"][earlier]
    ground = (data["antenna_id"][u] == data["antenna_id"][v]) & (gap < local_gaps[earlier])
    satellite = (data["satellite_id"][u] == data["satellite_id"][v]) & (gap < p0.ticks("150"))
    if not np.all(ground | satellite):
        raise AssertionError("Published edge violates the declared shared-resource conflict rule")
    expected = (ground.astype(np.uint8) | (satellite.astype(np.uint8) * 2)
                | np.where(gap < 0, 4, 8).astype(np.uint8))
    if not np.array_equal(expected, graph["edge_mask"]):
        raise AssertionError("Edge reason masks disagree with the actual contact resources")
    return {"sorted_unique_nonself_edges": True, "csr_degree_sum_equals_2m": True,
            "all_edges_match_actual_resource_predicate": True,
            "edge_reason_masks_match_predicate": True,
            "frozen_duration_equals_endpoint_difference": bool(np.array_equal(data["weight_ticks"], data["end_ticks"] - data["start_ticks"]))}


def build_source(source, parameters, groups, declared):
    if source not in SOURCES:
        raise ValueError("Only the six predeclared held-out physical sources are permitted")
    out = PERF_ROOT / "graphs" / source
    if out.exists():
        raise FileExistsError(f"No replacement of existing performance source: {out}")
    data, source_metadata, rows = p0.read_contacts(BASE_ROOT / "raw" / source / "contacts.csv", parameters, source)
    # Avoid publishing development-oriented alias interpretations on held-out data.
    source_metadata.pop("duration_uniqueness", None)
    if source_metadata["split"] != ("validation" if source.endswith("r006") else "test"):
        raise ValueError("Frozen source split mismatch")
    out.mkdir(parents=True)
    p0.write_node_mapping(out / "contacts_nodes.csv", rows, data)
    write_json(out / "source_metadata.json", source_metadata)
    started = time.perf_counter()
    manifest = {"status": "running", "version": VERSION, "source_id": source,
                "source_group": source_metadata["source_group"], "split": source_metadata["split"],
                "raw_manifest_sha256": source_metadata["stk_manifest_sha256"],
                "raw_contacts_sha256": source_metadata["raw_contacts_sha256"],
                "configuration_declaration_sha256": p0.sha256_file(declared),
                "scoring_or_labels_executed": False, "complete_configurations": 0}
    write_json(out / "manifest.json", manifest)
    try:
        sat_keys, sat_masks = p0.resource_edges(data, "satellite_id", p0.ticks("150"), 2)
        satellite_part = (p0.ticks("150"), sat_keys, sat_masks)
        graph_rows = []
        node_groups = np.array([groups[a] for a in data["antenna_id"].tolist()])
        for tag, west, east, family, aliases in CONFIGS:
            mapping = hetero.station_map(groups, west, east)
            mapping_ticks = {antenna: p0.ticks(str(value)) for antenna, value in mapping.items()}
            local_gaps = np.array([mapping_ticks[a] for a in data["antenna_id"].tolist()], np.int64)
            graph = hetero.build_per_antenna_edges(data, mapping_ticks, p0.ticks("150"), satellite_part)
            checks = integrity(data, graph, local_gaps)
            payload = {
                **data, **{key: value for key, value in graph.items() if key != "edge_keys"},
                "base9_integer_coordinates": full_active_coordinates(data, graph, local_gaps),
                "ground_gap_by_node_ticks": local_gaps,
                "ground_gap_antenna_ids": np.array(list(mapping_ticks)),
                "ground_gap_antenna_ticks": np.array(list(mapping_ticks.values()), np.int64),
                "station_gap_mode": np.array("per_antenna"), "antenna_group_by_node": node_groups,
                "satellite_gap_ticks": np.array(p0.ticks("150"), np.int64),
                "ticks_per_second": np.array(p0.TICKS_PER_SECOND, np.int64),
                "source_id": np.array(source), "source_group": np.array(source_metadata["source_group"]),
                "geometry_id": np.array(source_metadata["geometry_id"]), "replicate_id": np.array(source_metadata["replicate_id"]),
                "split": np.array(source_metadata["split"]), "config_id": np.array(tag), "builder_version": np.array(VERSION),
            }
            if west == east:
                payload["ground_gap_ticks"] = np.array(p0.ticks(str(west)), np.int64)
            path = out / f"{tag}.npz"
            np.savez_compressed(path, **payload)
            near = hetero.ground_diagnostics(data, mapping_ticks)
            near["interpretation"] = "Input timing-boundary QC only; no prior-source sensitivity receipt is transferred to this new physical source and no rigorous physical timing error bound is claimed."
            metadata = {
                "version": VERSION, "source_id": source, "source_group": source_metadata["source_group"],
                "split": source_metadata["split"], "config_id": tag, "family": family, "factorial_aliases": aliases,
                "station_gap_mode": "per_antenna", "station_gap_by_antenna_seconds": mapping,
                "antenna_group": groups, "west_gap_seconds": west, "east_gap_seconds": east, "satellite_gap_seconds": 150,
                "node_mapping_sha256": source_metadata["node_mapping_sha256"],
                "weight_ticks_sha256": source_metadata["weight_ticks_sha256"],
                "raw_contacts_sha256": source_metadata["raw_contacts_sha256"], "raw_manifest_sha256": source_metadata["stk_manifest_sha256"],
                "configuration_declaration_sha256": p0.sha256_file(declared),
                "builder_sha256": p0.sha256_file(Path(__file__)),
                "parent_p0_builder_sha256": p0.sha256_file(BASE_ROOT / "scripts" / "build_graphs.py"),
                "parent_heterogeneous_builder_sha256": p0.sha256_file(BASE_ROOT / "extensions" / "heterogeneous_ground_v1" / "scripts" / "build_heterogeneous_graphs.py"),
                "edge_arrays_sha256": p0.array_hash(graph["edge_u"], graph["edge_v"], graph["edge_mask"]),
                "npz_sha256": p0.sha256_file(path), "edge_mask": p0.EDGE_MASK,
                "stats": {"n": len(data["contact_id"]), "m": len(graph["edge_u"]),
                          "near_boundary_diagnostics": {"ground": near}},
                "input_integrity_checks": checks, "optimization_labels_or_scores_executed": False,
            }
            write_json(out / f"{tag}.json", metadata)
            graph_rows.append(metadata)
            manifest["complete_configurations"] = len(graph_rows)
            write_json(out / "manifest.json", manifest)
        summary = {"status": "success", "version": VERSION, "source_id": source,
                   "source_metadata": source_metadata, "graphs": graph_rows,
                   "same_vertex_and_weight_for_all_configurations": True,
                   "unique_graph_configurations": 8, "optimization_labels_or_scores_executed": False,
                   "build_seconds": time.perf_counter() - started}
        write_json(out / "summary.json", summary)
        manifest.update(status="success", build_seconds=summary["build_seconds"],
                        summary_sha256=p0.sha256_file(out / "summary.json"))
        write_json(out / "manifest.json", manifest)
        print(json.dumps({"source": source, "split": source_metadata["split"], "graphs_ready": 8,
                          "only_input_QC": True, "graph_directory": str(out)}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        manifest.update(status="failed", error=str(exc))
        write_json(out / "manifest.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default=",".join(SOURCES))
    parser.add_argument("--wait-for-ready", action="store_true",
                        help="Wait for these physical generators; no evaluation is triggered")
    args = parser.parse_args()
    sources = args.sources.split(",")
    if not sources or any(source not in SOURCES for source in sources):
        raise ValueError("Unknown requested physical source")
    parameters = json.loads((BASE_ROOT / "source_plan" / "CIPHEUR_parameters.json").read_text(encoding="utf-8"))
    groups, _ = hetero.groups_and_maps(parameters)
    declared = declaration(parameters, groups)
    pending = list(sources)
    while pending:
        progressed = False
        for source in list(pending):
            existing = PERF_ROOT / "graphs" / source / "summary.json"
            if existing.exists():
                old = json.loads(existing.read_text(encoding="utf-8"))
                if old.get("status") != "success":
                    raise RuntimeError(f"Existing graph source is incomplete: {source}")
                pending.remove(source)
                continue
            manifest_path = BASE_ROOT / "raw" / source / "manifest.json"
            status = json.loads(manifest_path.read_text(encoding="utf-8"))["status"] if manifest_path.exists() else "planned"
            if status == "failed":
                raise RuntimeError(f"Physical source failed: {source}; preserve its receipt")
            if status == "success":
                build_source(source, parameters, groups, declared)
                pending.remove(source)
                progressed = True
        if pending:
            if not args.wait_for_ready:
                raise RuntimeError(f"Physical sources are not ready: {pending}")
            if not progressed:
                time.sleep(20)


if __name__ == "__main__":
    main()
