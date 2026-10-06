"""Exact full-base9 equality census across completed P0 graph occurrences.

This is an input census, not a certificate oracle or a demanded quotient.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from build_graphs import BASE9_NAMES, ROOT, load_graph, write_json


def run(root: Path) -> dict:
    chunks, graph_rows, boundaries = [], [], [0]
    for summary_path in sorted((root / "graphs").glob("*/summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for item in summary["graphs"]:
            path = summary_path.parent / f"{item['config_id']}.npz"
            data = load_graph(path)
            vectors = data["base9_integer_coordinates"]
            chunks.append(vectors)
            graph_rows.append({"source_id": summary["source_id"], "config_id": item["config_id"],
                               "n": len(vectors), "npz_sha256": item["npz_sha256"],
                               "source_group": summary["source_metadata"]["source_group"],
                               "contact_ids": data["contact_id"].tolist()})
            boundaries.append(boundaries[-1] + len(vectors))
    if not chunks:
        raise ValueError("No completed graph sources")
    vectors = np.concatenate(chunks, axis=0)
    _, inverse, counts = np.unique(vectors, axis=0, return_inverse=True, return_counts=True)
    aliases = []
    for group in np.flatnonzero(counts > 1):
        occurrence_indices = np.flatnonzero(inverse == group)
        members = []
        for index in occurrence_indices:
            graph_index = int(np.searchsorted(boundaries, index, side="right") - 1)
            node = int(index - boundaries[graph_index])
            graph = graph_rows[graph_index]
            members.append({"source_id": graph["source_id"], "config_id": graph["config_id"],
                            "node_index": node, "contact_id": graph["contact_ids"][node]})
        aliases.append({"vector_integer_coordinates": vectors[occurrence_indices[0]].tolist(),
                        "members": members})
    result = {
        "feature_semantics_namespace": "exact_microtick_base9_v1", "feature_names": list(BASE9_NAMES),
        "scope": "Every completed P0 source/configuration, all contacts active, F=X=empty",
        "graph_count": len(graph_rows), "full_graph_action_occurrences": len(vectors),
        "distinct_vectors": len(counts), "alias_classes": len(aliases),
        "aliased_occurrences": int(counts[counts > 1].sum()), "classes": aliases,
        "graphs": [{key: value for key, value in graph.items() if key != "contact_ids"} for graph in graph_rows],
        "inference_limit": "This complete full-graph equality census does not compute the strict demanded quotient for actual restricted states. A same-contact feature vector may recur in different states; no multi-state G2 decision is made here.",
        "does_not_establish_G2": True, "does_not_compute_complete_demanded_quotient": True,
        "no_approximate_matching": True, "no_weight_or_time_changes": True,
    }
    write_json(root / "analysis" / "fullgraph_cross_source_base9_census.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps({key: result[key] for key in ("graph_count", "full_graph_action_occurrences", "distinct_vectors", "alias_classes")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
