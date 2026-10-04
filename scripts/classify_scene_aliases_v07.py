"""Exact input symmetry classification of the frozen C6/W6 TRAIN aliases.

No optimizer/oracle/model call. Equal-weight transposition automorphisms imply
conditional inclusion ties at the declared empty fixed/excluded boundary.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import screen_contact_scene_v07 as scene


def wl_colors(weights, adjacency, masks, marked):
    """Two fixed exact refinements; class internment uses tuple equality."""
    initial = [(weight, weight) for weight in weights]
    unique = {key: index for index, key in enumerate(sorted(set(initial)))}
    colors = [unique[key] for key in initial]
    rounds = []
    for _ in range(2):
        keys = []
        for v, neighbors in enumerate(adjacency):
            counts = Counter((masks[v][u] if marked else 0, colors[u]) for u in neighbors)
            keys.append((colors[v], tuple(sorted((mask, color, count)
                                                 for (mask, color), count in counts.items()))))
        intern = {key: index for index, key in enumerate(sorted(set(keys)))}
        colors = [intern[key] for key in keys]
        rounds.append(colors)
    return rounds


def classify_graph(graph, arcs, rows, gap):
    n = len(arcs)
    weights = [arc.link_time for arc in arcs]
    total = sum(weights)
    adjacency = [set(map(int, graph.neighbors(v))) for v in range(n)]
    masks = [dict() for _ in range(n)]
    for (u, v), mask in zip(graph.edges, graph.edge_types):
        masks[int(u)][int(v)] = int(mask)
        masks[int(v)][int(u)] = int(mask)
    vectors, groups = [], defaultdict(list)
    for v, neighbors in enumerate(adjacency):
        neighbor_weights = [weights[u] for u in neighbors]
        conflict = sum(neighbor_weights)
        key = (weights[v], weights[v], len(neighbors), conflict,
               max(neighbor_weights, default=0), total - weights[v] - conflict, gap, 150, n)
        vectors.append(key)
        groups[key].append(v)
    unmarked = wl_colors(weights, adjacency, masks, False)
    marked = wl_colors(weights, adjacency, masks, True)

    def pair_status(a, b):
        ext_a, ext_b = adjacency[a] - {b}, adjacency[b] - {a}
        same_external = ext_a == ext_b
        same_weight = weights[a] == weights[b]
        adjacent = b in adjacency[a]
        twin = same_weight and same_external
        kind = ("adjacent_true_twins" if adjacent else "nonadjacent_open_twins") if twin else "non_twins"
        reason_preserved = same_external and all(masks[a][u] == masks[b][u] for u in ext_a)
        result = {"base9_alias": vectors[a] == vectors[b], "kind": kind,
                  "weights_equal": same_weight, "adjacent": adjacent,
                  "external_neighbors_equal": same_external,
                  "external_neighbor_counts": [len(ext_a), len(ext_b)],
                  "edge_reason_preserved_by_swap": reason_preserved,
                  "unmarked_weighted_WL1_separates": unmarked[0][a] != unmarked[0][b],
                  "unmarked_weighted_WL2_separates": unmarked[1][a] != unmarked[1][b],
                  "marked_weighted_WL1_separates": marked[0][a] != marked[0][b],
                  "marked_weighted_WL2_separates": marked[1][a] != marked[1][b],
                  "root_edge_reason_degrees": [dict(sorted(Counter(masks[v].values()).items())) for v in (a, b)],
                  "external_neighbors_sha256": [scene.digest(scene.canonical(sorted(rows[u] for u in ext)))
                                                for ext in (ext_a, ext_b)]}
        if twin:
            result["conditional_tie_proof"] = {
                "kind": "equal_weight_transposition_automorphism",
                "graph_sha256": graph.graph_hash,
                "boundary": {"fixed": [], "excluded": []},
                "actions_available": True, "same_weight": True,
                "same_neighbors_outside_pair": True,
                "forced_inclusion_value_difference_exact": "0",
                "scope": "unmarked weighted MWIS; does not assert marked-resource automorphism or optimum value"}
        return result

    pair_indices = [(members[i], members[j]) for members in groups.values()
                    for i in range(len(members)) for j in range(i + 1, len(members))]
    return pair_indices, pair_status


def classify_window(task):
    from cipheur.v51_adapter import _load_legacy
    legacy, _ = _load_legacy(Path(task["stable_root"]))
    Arc = legacy["data"].Arc
    arcs = tuple(Arc(id=index, priority=0.0,
                 **{key: value for key, value in item.items()
                    if key not in ("original_row_id", "row_sha256")})
                 for index, item in enumerate(task["contacts"]))
    rows = [item["row_sha256"] for item in task["contacts"]]
    statuses, graph_rows = {}, []
    for gap in (340, 680):
        graph = legacy["graph"].build_conflict_graph(arcs, legacy["graph"].ConflictParameters(gap, 150, 300))
        indices, status = classify_graph(graph, arcs, rows, gap)
        statuses[gap] = (indices, status)
        pairs = []
        for a, b in indices:
            pairs.append({"a_row_sha256": rows[a], "b_row_sha256": rows[b], **status(a, b)})
        counts = Counter(pair["kind"] for pair in pairs)
        graph_rows.append({"source": task["source"], "window": task["window"], "day": 0,
                           "ground_gap": gap, "n": len(arcs), "graph_sha256": graph.graph_hash,
                           "alias_pairs_assigned": len(pairs),
                           "kind_counts": {key: counts[key] for key in (
                               "adjacent_true_twins", "nonadjacent_open_twins", "non_twins")},
                           "pairs": pairs})
    union = set(statuses[340][0]) | set(statuses[680][0])
    cross = [{"source": task["source"], "window": task["window"],
              "a_row_sha256": rows[a], "b_row_sha256": rows[b],
              "gap340": statuses[340][1](a, b), "gap680": statuses[680][1](a, b)}
             for a, b in sorted(union)]
    return {"graphs": graph_rows, "cross_configuration": cross}


def prepare(args):
    out, screen = Path(args.out).resolve(), Path(args.screen).resolve()
    if out.exists():
        raise ValueError("Use a new classification namespace; preserve original bytes")
    old_freeze = json.loads((screen / "freeze_receipt.json").read_bytes())
    old_complete = json.loads((screen / "completion_receipt.json").read_bytes())
    if old_complete["completed_graphs"] != 48 or old_complete["failed_windows"] != 0:
        raise ValueError("Require complete prior TRAIN-only input census")
    if scene.source_closure(old_freeze["stable_root"]) != old_freeze["source_sha256"]:
        raise ValueError("Original frozen source changed")
    bindings = {name: scene.digest((screen / name).read_bytes()) for name in (
        "protocol.json", "freeze_receipt.json", "train_identity_inventory.json",
        "source_snapshot.zip", "screen_summary.json", "completion_receipt.json")}
    if bindings["screen_summary.json"] != old_complete["summary_sha256"]:
        raise ValueError("Original census completion binding mismatch")
    protocol = {"version": "scene_alias_classification_v07_003", "before_graph_rebuild": True,
                "screen_namespace": str(screen), "screen_bindings": bindings,
                "source_closure": scene.source_closure(old_freeze["stable_root"]),
                "classifier_sha256": scene.digest(Path(__file__).read_bytes()),
                "assigned_graphs": 48, "assigned_alias_pairs": 556, "workers": 8,
                "train_days": [0], "nontrain_graphs": 0, "ground_gaps": [340, 680],
                "boundary": {"fixed": [], "excluded": []},
                "proof": "equal weights and equal neighbor sets outside pair imply unmarked weighted transposition automorphism and forced-value tie",
                "WL": "two exact tuple-interned refinements; initial colors(weight,duration); unmarked and reason-mask-marked separately",
                "WL_scope": "different color proves representation distinction, not a strict preferred action; same color is not isomorphism",
                "optimizer_calls": 0, "oracle_calls": 0, "model_calls": 0,
                "no_pair_filters": True}
    out.mkdir(parents=True)
    scene.write_json(out / "protocol.json", protocol)
    with zipfile.ZipFile(out / "source_capsule.zip", "x", compression=zipfile.ZIP_DEFLATED) as capsule:
        capsule.writestr("scripts/classify_scene_aliases_v07.py", Path(__file__).read_bytes())
        for name in bindings:
            capsule.writestr("original_screen/" + name, (screen / name).read_bytes())
    scene.write_json(out / "freeze_receipt.json", {
        "before_graph_rebuild": True, "created_unix": time.time(),
        "protocol_sha256": scene.digest((out / "protocol.json").read_bytes()),
        "source_capsule_sha256": scene.digest((out / "source_capsule.zip").read_bytes())})
    print(json.dumps({"prepared": str(out), "graph_calls": 0}), flush=True)


def run(args):
    out = Path(args.out).resolve()
    if (out / "execution_receipt.json").exists():
        raise ValueError("Preserve the first classification execution")
    protocol = json.loads((out / "protocol.json").read_bytes())
    freeze = json.loads((out / "freeze_receipt.json").read_bytes())
    if scene.digest((out / "protocol.json").read_bytes()) != freeze["protocol_sha256"]:
        raise ValueError("Frozen classification protocol mismatch")
    if scene.digest(Path(__file__).read_bytes()) != protocol["classifier_sha256"]:
        raise ValueError("Classifier source changed after freeze")
    screen = Path(protocol["screen_namespace"])
    for name, expected in protocol["screen_bindings"].items():
        if scene.digest((screen / name).read_bytes()) != expected:
            raise ValueError("Prior screen artifact changed: " + name)
    old_freeze = json.loads((screen / "freeze_receipt.json").read_bytes())
    if scene.source_closure(old_freeze["stable_root"]) != protocol["source_closure"]:
        raise ValueError("Original input-builder source changed")
    old_protocol = json.loads((screen / "protocol.json").read_bytes())
    old_summary = json.loads((screen / "screen_summary.json").read_bytes())
    old_records = {(r["source"], r["window"], r["ground_trans_time"]): r for r in old_summary["records"]}
    tasks = []
    for source in old_protocol["sources"]:
        windows, inventory, _ = scene.read_train(source, 0, {0})
        for window, contacts in sorted(windows.items()):
            tasks.append({"source": source["name"], "window": window,
                          "contacts": contacts, "stable_root": old_freeze["stable_root"]})
    if len(tasks) != 24:
        raise ValueError("Incomplete prescribed window frame")
    begin = time.time()
    scene.write_json(out / "execution_receipt.json", {
        "start_unix": begin, "workers": 8, "assigned_windows": 24,
        "protocol_sha256": freeze["protocol_sha256"], "optimizer_calls": 0,
        "oracle_calls": 0, "model_calls": 0})
    graphs, cross, failures = [], [], []
    with (out / "window_classifications.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(classify_window, task): (task["source"], task["window"])
                       for task in tasks}
            for future in as_completed(futures):
                source, window = futures[future]
                try:
                    result = future.result()
                    for record in result["graphs"]:
                        previous = old_records[(source, window, record["ground_gap"])]
                        if (record["graph_sha256"] != previous["legacy_graph_sha256"] or
                            record["alias_pairs_assigned"] != previous["base9_aliases"]["unordered_equal_pairs"]):
                            raise ValueError("Rebuilt input graph/alias census differs from the original")
                    graphs.extend(result["graphs"])
                    cross.extend(result["cross_configuration"])
                    stream.write(json.dumps(result, allow_nan=False) + "\n")
                except Exception as error:
                    failure = {"source": source, "window": window,
                               "error": type(error).__name__ + ": " + str(error)}
                    failures.append(failure)
                    stream.write(json.dumps({"failure": failure}) + "\n")
                stream.flush()
    counts = Counter()
    for graph in graphs:
        counts.update(graph["kind_counts"])
    summary = {"assigned_graphs": 48, "completed_graphs": len(graphs),
               "assigned_alias_pairs": 556, "classified_alias_pairs": sum(counts.values()),
               "kind_counts": dict(counts), "failures": failures,
               "graphs": sorted(graphs, key=lambda g: (g["source"], g["window"], g["ground_gap"])),
               "cross_configuration": sorted(cross, key=lambda p: (p["source"], p["window"], p["a_row_sha256"], p["b_row_sha256"])),
               "elapsed_wall_seconds": time.time() - begin,
               "protocol_sha256": freeze["protocol_sha256"], "optimizer_calls": 0,
               "oracle_calls": 0, "model_calls": 0, "nontrain_graphs": 0}
    scene.write_json(out / "classification_summary.json", summary)
    scene.write_json(out / "completion_receipt.json", {
        "terminal": True, "finish_unix": time.time(), "completed_graphs": len(graphs),
        "classified_alias_pairs": sum(counts.values()), "failed_windows": len(failures),
        "summary_sha256": scene.digest((out / "classification_summary.json").read_bytes()),
        "window_results_sha256": scene.digest((out / "window_classifications.jsonl").read_bytes())})
    print(json.dumps({"terminal": True, "graphs": len(graphs), "counts": dict(counts),
                      "failures": len(failures)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--screen")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else run)(args)


if __name__ == "__main__":
    main()
