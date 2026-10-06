"""Declared west/east antenna-gap factorial, reusing unchanged P0 intervals."""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import csv
import json
from pathlib import Path
import sys

import numpy as np

EXTENSION_ROOT = Path(__file__).resolve().parents[1]
BASE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE_ROOT / "scripts"))
sys.path.insert(0, str(BASE_ROOT / "extensions" / "joint_resource_v1" / "scripts"))
import build_graphs as p0
import build_joint_graphs as common

VERSION = "cipheur-heterogeneous-ground-factorial-v1"
CONFIGS = (
    ("A", "gW0340_gE0340_s0150", 340, 340, "g0340"),
    ("W", "gW1200_gE0340_s0150", 1200, 340, None),
    ("E", "gW0340_gE1200_s0150", 340, 1200, None),
    ("J", "gW1200_gE1200_s0150", 1200, 1200, "g1200"),
)


def groups_and_maps(parameters: dict) -> tuple[dict, dict]:
    groups, sites = {}, {}
    for station in parameters["stations"]:
        longitude = station["longitude_deg_east"]
        if longitude in (88, 94, 100):
            group = "west"
        elif longitude in (106, 112, 118):
            group = "east"
        else:
            raise ValueError("Station outside the declared geographic factor partition")
        groups[station["antenna_id"]] = group
        sites[station["antenna_id"]] = station["site_id"]
    if list(groups.values()).count("west") != 6 or list(groups.values()).count("east") != 6:
        raise ValueError("Expected six west and six east antennas")
    return groups, sites


def station_map(groups: dict, west: int, east: int) -> dict:
    return {antenna: west if group == "west" else east for antenna, group in groups.items()}


def declare(root: Path, base: Path, groups: dict) -> Path:
    value = {
        "version": VERSION, "development_only": True, "source_ids": list(common.SOURCES),
        "parent_parameters_sha256": p0.sha256_file(base / "source_plan" / "CIPHEUR_parameters.json"),
        "station_gap_mode": "per_antenna", "antenna_group": groups,
        "group_definition": {"west_longitudes_deg": [88, 94, 100], "east_longitudes_deg": [106, 112, 118]},
        "satellite_gap_seconds": 150,
        "configurations": [{"factorial_id": key, "config_id": tag,
                            "station_gap_by_antenna_seconds": station_map(groups, west, east)}
                           for key, tag, west, east, _ in CONFIGS],
        "contact_contract": "Same original P0 complete visibility intervals, vertices, resources, and weight=end-start. No additional time rounding or weight changes.",
        "base9_station_gap_semantics": "For root contact v, station_gap(v)=gap_by_antenna[v.antenna]; no mean or global surrogate.",
        "all_gap_entries_are_development_parameters": True,
        "source_group_contract": "Original TRAIN development groups retained; geometry companions and all four configurations remain together.",
        "new_STK_or_oracle_calls": False,
    }
    path = root / "source_plan" / "extension_parameters.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != value:
        raise ValueError("Predeclared extension parameters changed")
    if not path.exists():
        p0.write_json(path, value)
    return path


def build_per_antenna_edges(data: dict, gap_by_antenna_ticks: dict, satellite_gap_ticks: int,
                           satellite_part: tuple | None = None) -> dict:
    """Pure capacity-one construction with each antenna's actual declared gap."""
    n = len(data["contact_id"])
    groups = defaultdict(list)
    for node, identity in enumerate(data["antenna_id"].tolist()):
        groups[identity].append(node)
    if set(groups) != set(gap_by_antenna_ticks):
        raise ValueError("Antenna gap mapping must cover every and only actual antenna")
    keys, masks = [], []
    for identity, members in groups.items():
        gap = int(gap_by_antenna_ticks[identity])
        if gap < 0:
            raise ValueError("Negative antenna switching gap")
        order = np.array(sorted(members, key=lambda v: (int(data["start_ticks"][v]), v)), np.int64)
        starts = data["start_ticks"][order]
        for position, node in enumerate(order):
            finish = int(data["end_ticks"][node])
            stop = int(np.searchsorted(starts, finish + gap, side="left"))
            other = order[position + 1:stop]
            if len(other):
                keys.append(np.minimum(node, other) * n + np.maximum(node, other))
                masks.append((1 | np.where(data["start_ticks"][other] < finish, 4, 8)).astype(np.uint8))
    if satellite_part is None:
        sat_keys, sat_masks = p0.resource_edges(data, "satellite_id", satellite_gap_ticks, 2)
    else:
        cached_gap, sat_keys, sat_masks = satellite_part
        if int(cached_gap) != int(satellite_gap_ticks):
            raise ValueError("Cached satellite primitive uses another gap")
    keys.append(sat_keys)
    masks.append(sat_masks)
    all_keys, all_masks = np.concatenate(keys), np.concatenate(masks)
    order = np.argsort(all_keys, kind="stable")
    unique_keys, first = np.unique(all_keys[order], return_index=True)
    merged_masks = np.bitwise_or.reduceat(all_masks[order], first)
    u, v = (unique_keys // n).astype(np.uint32), (unique_keys % n).astype(np.uint32)
    rows, neighbors = np.concatenate((u, v)), np.concatenate((v, u))
    degree = np.bincount(rows.astype(np.int64), minlength=n).astype(np.int64)
    indptr = np.concatenate((np.array([0], np.int64), np.cumsum(degree)))
    return {"edge_u": u, "edge_v": v, "edge_mask": merged_masks,
            "indptr": indptr, "indices": neighbors[np.lexsort((neighbors, rows))], "edge_keys": unique_keys}


def ground_diagnostics(data: dict, gap_ticks: dict, radius=2000) -> dict:
    groups, examples, closest = defaultdict(list), [], None
    count, conflicts = 0, 0
    for node, antenna in enumerate(data["antenna_id"].tolist()):
        groups[antenna].append(node)
    for antenna, members in groups.items():
        gap = gap_ticks[antenna]
        order = np.array(sorted(members, key=lambda v: (int(data["start_ticks"][v]), v)), np.int64)
        starts = data["start_ticks"][order]
        for position, node in enumerate(order[:-1]):
            target = int(data["end_ticks"][node]) + gap
            insertion = int(np.searchsorted(starts, target, side="left"))
            for j in (insertion - 1, insertion):
                if position < j < len(order):
                    margin = int(starts[j]) - target
                    if closest is None or abs(margin) < closest["absolute_margin_ticks"]:
                        closest = {"absolute_margin_ticks": abs(margin), "signed_margin_ticks": margin,
                                   "earlier_contact": str(data["contact_id"][node]),
                                   "later_contact": str(data["contact_id"][order[j]]),
                                   "resource_id": antenna, "resource_gap_ticks": gap}
            lo = max(position + 1, int(np.searchsorted(starts, target-radius, side="left")))
            hi = int(np.searchsorted(starts, target+radius, side="right"))
            for other in order[lo:hi]:
                margin = int(data["start_ticks"][other]) - target
                count += 1
                conflicts += int(margin < 0)
                examples.append({"earlier_contact": str(data["contact_id"][node]),
                                 "later_contact": str(data["contact_id"][other]), "resource_id": antenna,
                                 "resource_gap_ticks": gap, "signed_margin_ticks": margin,
                                 "resource_conflict": margin < 0})
    return {"resource_field": "antenna_id", "gap_mode": "per_antenna", "gap_by_antenna_ticks": gap_ticks,
            "near_boundary_radius_ticks": radius, "near_boundary_pair_count": count,
            "near_conflicting_pairs": conflicts, "near_compatible_pairs": count-conflicts,
            "closest_pair": closest, "examples": examples,
            "interpretation": "Numerical boundary neighborhood only. These 340/1200 thresholds inherit original P0 targeted sensitivity receipts; no new physical error bound is claimed."}


def census(vectors: np.ndarray, data: dict) -> dict:
    _, inverse, counts = np.unique(vectors, axis=0, return_inverse=True, return_counts=True)
    classes = []
    for group in np.flatnonzero(counts > 1):
        nodes = np.flatnonzero(inverse == group)
        classes.append({"nodes": nodes.tolist(), "contact_ids": data["contact_id"][nodes].tolist(),
                        "vector_integer_coordinates": vectors[nodes[0]].tolist()})
    return {"namespace": "exact_microtick_local_antenna_gap_base9_v1", "feature_names": list(p0.BASE9_NAMES),
            "station_gap_semantics": "Actual root antenna gap, not a mean or hidden global scalar.",
            "scope": "All contacts active, F=X=empty; exact mathematical microtick sums.",
            "alias_classes": len(classes), "aliased_occurrences": int(counts[counts > 1].sum()), "classes": classes,
            "no_strict_labels_or_demanded_quotient": True}


def stats(data: dict, graph: dict, mapping: dict, sat_diagnostic: dict) -> dict:
    n, m = len(data["contact_id"]), len(graph["edge_u"])
    degrees = np.diff(graph["indptr"])
    components = p0.component_sizes(n, graph["edge_u"], graph["edge_v"])
    return {"n": n, "m": m, "average_degree_2m_over_n": 2*m/n,
            "degree_distribution": p0.degree_distribution(degrees),
            "component_count": len(components), "component_sizes_descending": components,
            "edge_mask_counts": {name: int(np.count_nonzero(graph["edge_mask"] & bit)) for name, bit in p0.EDGE_MASK.items()},
            "near_boundary_diagnostics": {"ground": ground_diagnostics(data, mapping), "satellite": copy.deepcopy(sat_diagnostic)}}


def build_source(source: str, base: Path, root: Path, groups: dict, declaration: Path) -> dict:
    out = root / "graphs" / source
    if (out / "summary.json").exists():
        raise FileExistsError("No silent replacement of completed heterogeneous graph source")
    parameters = json.loads((base / "source_plan" / "CIPHEUR_parameters.json").read_text(encoding="utf-8"))
    data, source_meta, rows = p0.read_contacts(base / "raw" / source / "contacts.csv", parameters, source)
    parent_dir = base / "graphs" / source
    parent_payloads = {tag: p0.load_graph(parent_dir/f"{tag}.npz") for tag in ("g0340", "g1200")}
    A0, J0 = (common.as_graph(parent_payloads[tag]) for tag in ("g0340", "g1200"))
    parent_stats = {tag: json.loads((parent_dir/f"{tag}.json").read_text(encoding="utf-8"))["stats"] for tag in parent_payloads}
    sat_selected = (A0["edge_mask"] & 2) != 0
    sat_part = (p0.ticks("150"), A0["edge_keys"][sat_selected], (A0["edge_mask"][sat_selected] & 14).astype(np.uint8))
    node_groups = np.array([groups[antenna] for antenna in data["antenna_id"].tolist()])
    out.mkdir(parents=True, exist_ok=True)
    p0.write_node_mapping(out/"contacts_nodes.csv", rows, data)
    p0.write_json(out/"source_metadata.json", source_meta)
    graphs, graph_rows, matrices = {}, [], {}
    for key, tag, west, east, parent_tag in CONFIGS:
        map_seconds = station_map(groups, west, east)
        map_ticks = {antenna: p0.ticks(str(gap)) for antenna, gap in map_seconds.items()}
        local_gaps = np.array([map_ticks[antenna] for antenna in data["antenna_id"].tolist()], np.int64)
        if parent_tag:
            payload = {name: value.copy() for name, value in parent_payloads[parent_tag].items()}
            graph = common.as_graph(payload)
            graph_stats = copy.deepcopy(parent_stats[parent_tag])
            graph_stats.pop("r_E_from_smallest_gap", None)
            graph_stats["near_boundary_diagnostics"]["ground"] = ground_diagnostics(data, map_ticks)
            vectors = payload["base9_integer_coordinates"]
        else:
            graph = build_per_antenna_edges(data, map_ticks, p0.ticks("150"), sat_part)
            graph_stats = stats(data, graph, map_ticks, parent_stats["g0340"]["near_boundary_diagnostics"]["satellite"])
            # Full-active base9 depends only on root adjacency, root gap, and
            # fixed vertex weights. Other antennas' edge changes do not enter it.
            vectors = np.where((local_gaps == p0.ticks("340"))[:,None],
                               parent_payloads["g0340"]["base9_integer_coordinates"],
                               parent_payloads["g1200"]["base9_integer_coordinates"])
            payload = {**data, **{name: value for name, value in graph.items() if name != "edge_keys"},
                       "base9_integer_coordinates": vectors, "ticks_per_second": np.array(p0.TICKS_PER_SECOND,np.int64),
                       "satellite_gap_ticks": np.array(p0.ticks("150"),np.int64),
                       "source_id": np.array(source), "source_group": np.array(source_meta["source_group"]),
                       "geometry_id": np.array(source_meta["geometry_id"]), "replicate_id": np.array(source_meta["replicate_id"]),
                       "split": np.array(source_meta["split"])}
        payload.pop("ground_gap_ticks", None)
        payload.update(ground_gap_by_node_ticks=local_gaps, ground_gap_antenna_ids=np.array(list(map_ticks)),
                       ground_gap_antenna_ticks=np.array(list(map_ticks.values()),np.int64),
                       station_gap_mode=np.array("per_antenna"), antenna_group_by_node=node_groups,
                       config_id=np.array(tag), factorial_id=np.array(key), builder_version=np.array(VERSION))
        path = out/f"{tag}.npz"
        np.savez_compressed(path, **payload)
        current_census = census(vectors,data)
        p0.write_json(out/f"{tag}_base9_census.json",current_census)
        metadata = {"version":VERSION,"source_id":source,"source_group":source_meta["source_group"],"split":source_meta["split"],
                    "config_id":tag,"factorial_id":key,"station_gap_mode":"per_antenna",
                    "station_gap_by_antenna_seconds":map_seconds,"antenna_group":groups,"satellite_gap_seconds":150,
                    "node_mapping_sha256":source_meta["node_mapping_sha256"],"weight_ticks_sha256":source_meta["weight_ticks_sha256"],
                    "raw_contacts_sha256":source_meta["raw_contacts_sha256"],"raw_manifest_sha256":source_meta["stk_manifest_sha256"],
                    "extension_parameters_sha256":p0.sha256_file(declaration),"builder_sha256":p0.sha256_file(Path(__file__)),
                    "parent_graph_builder_sha256":p0.sha256_file(base/"scripts"/"build_graphs.py"),
                    "reused_P0_uniform_graph":parent_tag,"parent_npz_sha256":p0.sha256_file(parent_dir/f"{parent_tag}.npz") if parent_tag else None,
                    "edge_mask":p0.EDGE_MASK,"edge_arrays_sha256":p0.array_hash(graph["edge_u"],graph["edge_v"],graph["edge_mask"]),
                    "npz_sha256":p0.sha256_file(path),"stats":graph_stats,"base9_census_file":f"{tag}_base9_census.json"}
        p0.write_json(out/f"{tag}.json",metadata)
        graphs[key],matrices[key]=graph,vectors
        graph_rows.append(metadata)
    A,W,E,J=(graphs[key] for key in ("A","W","E","J"))
    dw=np.setdiff1d(W["edge_keys"],A["edge_keys"],assume_unique=True)
    de=np.setdiff1d(E["edge_keys"],A["edge_keys"],assume_unique=True)
    common_edges=np.intersect1d(dw,de,assume_unique=True)
    if len(common_edges) or not np.array_equal(np.union1d(W["edge_keys"],E["edge_keys"]),J["edge_keys"]):
        raise AssertionError("Geographic ground-factor edge lattice is inconsistent")
    n=len(data["contact_id"])
    def degrees(keys): return np.bincount(np.concatenate((keys//n,keys%n)),minlength=n).astype(np.int64)
    dW,dE=degrees(dw),degrees(de)
    cross=(A["edge_mask"]&2 != 0)&(node_groups[A["edge_u"]]!=node_groups[A["edge_v"]])
    cu,cv=A["edge_u"][cross],A["edge_v"][cross]
    own_new_degree=dW+dE
    exposed=(own_new_degree[cu]>0)&(own_new_degree[cv]>0)
    exposed_degree=np.bincount(np.concatenate((cu[exposed],cv[exposed])).astype(np.int64),minlength=n)
    with (out/"node_axis_degrees.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.writer(stream);writer.writerow(["node_index","contact_id","group","new_west_degree","new_east_degree","exposed_cross_group_satellite_degree"])
        writer.writerows([i,str(data["contact_id"][i]),str(node_groups[i]),int(dW[i]),int(dE[i]),int(exposed_degree[i])] for i in range(n))
    transitions={"A_to_W":common.difference_and_monotonicity(A,W,"ground"),"A_to_E":common.difference_and_monotonicity(A,E,"ground"),
                 "W_to_J":common.difference_and_monotonicity(W,J,"ground"),"E_to_J":common.difference_and_monotonicity(E,J,"ground")}
    equality={"west_A_equals_E":bool(np.array_equal(matrices["A"][node_groups=="west"],matrices["E"][node_groups=="west"])),
              "west_W_equals_J":bool(np.array_equal(matrices["W"][node_groups=="west"],matrices["J"][node_groups=="west"])),
              "east_A_equals_W":bool(np.array_equal(matrices["A"][node_groups=="east"],matrices["W"][node_groups=="east"])),
              "east_E_equals_J":bool(np.array_equal(matrices["E"][node_groups=="east"],matrices["J"][node_groups=="east"]))}
    summary={"version":VERSION,"source_id":source,"source_metadata":source_meta,"graphs":graph_rows,"transitions":transitions,
             "new_west_ground_edges":len(dw),"new_east_ground_edges":len(de),"added_axis_edge_intersection":len(common_edges),
             "same_node_mixed_new_edge_wedges":int((dW*dE).sum()),
             "mixed_wedge_note":"Zero follows from disjoint antenna groups; it is not an optimization interaction test.",
             "cross_group_same_satellite_edges":len(cu),"cross_group_satellite_links_with_both_endpoints_exposed_to_own_new_ground_edges":int(exposed.sum()),
             "coupling_note":"Input coupling exposure only, not certificates, independent samples, or demonstrated objective interaction.",
             "full_active_local_base9_remote_factor_equality":equality,"edge_union_identity":True,
             "parent_P0_unchanged":True,"new_STK_or_oracle_calls":False}
    p0.write_json(out/"summary.json",summary)
    return summary


def aggregate(root:Path)->dict:
    summaries=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((root/"graphs").glob("*/summary.json"))]
    rows,chunks=[],[]
    for s in summaries:
        for g in s["graphs"]:
            z=p0.load_graph(root/"graphs"/s["source_id"]/f"{g['config_id']}.npz")
            chunks.append(z["base9_integer_coordinates"])
            rows.append({"source_id":s["source_id"],"source_group":s["source_metadata"]["source_group"],"factorial_id":g["factorial_id"],
                         "config_id":g["config_id"],"n":g["stats"]["n"],"m":g["stats"]["m"],"mean_degree":g["stats"]["average_degree_2m_over_n"],
                         "new_west_ground_edges":s["new_west_ground_edges"],"new_east_ground_edges":s["new_east_ground_edges"],
                         "cross_group_same_satellite_edges":s["cross_group_same_satellite_edges"],
                         "cross_links_both_endpoints_exposed":s["cross_group_satellite_links_with_both_endpoints_exposed_to_own_new_ground_edges"]})
    vectors=np.concatenate(chunks)
    _,counts=np.unique(vectors,axis=0,return_counts=True)
    result={"version":VERSION,"opportunity_libraries":len(summaries),"graph_count":len(rows),"graphs":rows,
            "sources":[{k:v for k,v in s.items() if k not in ("graphs","source_metadata")} for s in summaries],
            "full_active_base9_census":{"namespace":"exact_microtick_local_antenna_gap_base9_v1","occurrences":len(vectors),
                                       "distinct_vectors":len(counts),"alias_classes":int(np.count_nonzero(counts>1)),
                                       "aliased_occurrences":int(counts[counts>1].sum()),"scope":"Full-active empty boundary, input equality only; strict demanded quotient remains the evidence group's responsibility."},
            "actual_head_requirement":"station_gap(v) reads its own antenna from the explicit mapping; do not call the unchanged global-scalar feature accessor without an extension adapter.",
            "parent_P0_unchanged":True,"new_STK_or_oracle_calls":False}
    p0.write_json(root/"analysis"/"heterogeneous_graph_summary.json",result)
    with (root/"analysis"/"heterogeneous_graph_screen.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root",type=Path,default=BASE_ROOT);parser.add_argument("--root",type=Path,default=EXTENSION_ROOT)
    parser.add_argument("--sources",default=",".join(common.SOURCES));parser.add_argument("--aggregate-only",action="store_true")
    args=parser.parse_args()
    if not args.aggregate_only:
        parameters=json.loads((args.base_root/"source_plan"/"CIPHEUR_parameters.json").read_text(encoding="utf-8"))
        groups,_=groups_and_maps(parameters);declaration=declare(args.root,args.base_root,groups)
        for source in args.sources.split(","):
            if source not in common.SOURCES:raise ValueError("Unregistered source")
            s=build_source(source,args.base_root,args.root,groups,declaration)
            print(json.dumps({"source":source,"edges":{g["factorial_id"]:g["stats"]["m"] for g in s["graphs"]},
                              "west_added":s["new_west_ground_edges"],"east_added":s["new_east_ground_edges"],
                              "cross_satellite":s["cross_group_same_satellite_edges"],"exposed_cross_satellite":s["cross_group_satellite_links_with_both_endpoints_exposed_to_own_new_ground_edges"],
                              "full_active_base9_equalities":s["full_active_local_base9_remote_factor_equality"]}),flush=True)
    result=aggregate(args.root)
    print(json.dumps({"libraries":result["opportunity_libraries"],"graphs":result["graph_count"],"full_active_base9":result["full_active_base9_census"]}),flush=True)


if __name__=="__main__":main()
