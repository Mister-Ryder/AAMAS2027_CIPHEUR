"""Outcome-free sparse SNAP transfer inputs with explicit graph conversion.

All observed vertices are retained in an explicitly declared simple-network
projection. Self-loop arcs are dropped and reported: this changes the MWIS
semantics of an original looped graph and is not claimed to preserve that
problem. Unknown isolated-node identities are never invented. This extension
is separate from the original public challenge suite.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
import tarfile
from urllib.request import Request, urlopen

from .model import Contact, Graph


def parse_snap(raw, *, source_directed=False, self_loop_policy="drop_loop_arcs"):
    if type(source_directed) is not bool or self_loop_policy not in ("drop_loop_arcs", "reject"):
        raise ValueError("Explicit direction and self-loop policy required")
    text = raw.decode("ascii")
    vertices, arcs, comments, raw_rows, loop_rows = set(), set(), [], 0, 0
    declarations = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            comments.append(line)
            match = re.search(r"\bNodes:\s*(\d+)\s+Edges:\s*(\d+)\b", line, re.I)
            if match:
                declarations.append(tuple(map(int, match.groups())))
            continue
        fields = line.split()
        if len(fields) != 2 or not all(re.fullmatch(r"[+-]?\d+", v) for v in fields):
            raise ValueError("Expected two integer edge endpoints at line " + str(number))
        a, b = map(int, fields)
        vertices.update((a, b)); arcs.add((a, b)); raw_rows += 1
        loop_rows += a == b
    if len(set(declarations)) > 1:
        raise ValueError("Inconsistent SNAP header declarations")
    loops = {a for a, b in arcs if a == b}
    if loops and self_loop_policy == "reject":
        raise ValueError("Self-loop-bearing source vertices cannot be silently made eligible")
    before = {tuple(sorted((a, b))) for a, b in arcs if a != b}
    eligible = vertices
    edges = frozenset(before)
    # Independent recheck against the original directed/undirected edge rows.
    rebuilt = {tuple(sorted((a, b))) for a, b in arcs if a in eligible and b in eligible and a != b}
    if edges != rebuilt or any(a == b or a not in eligible or b not in eligible for a, b in edges):
        raise AssertionError("Canonical source-edge verification failed")
    declared_nodes, declared_edges = declarations[0] if declarations else (None, None)
    receipt = {"comments": comments, "header_declared_nodes": declared_nodes,
        "header_declared_edges": declared_edges, "observed_original_vertices": len(vertices),
        "original_vertex_ids": sorted(vertices), "raw_edge_rows": raw_rows,
        "unique_ordered_arcs": len(arcs), "duplicate_ordered_rows": raw_rows - len(arcs),
        "raw_self_loop_rows": loop_rows, "unique_self_loop_vertices": len(loops),
        "self_loop_vertex_ids": sorted(loops), "self_loop_policy": self_loop_policy,
        "canonical_nonloop_edges_before_restriction": len(before),
        "repeated_or_reverse_nonloop_rows": raw_rows - loop_rows - len(before),
        "removed_vertex_count": 0, "canonical_self_loop_arcs_removed": len(loops),
        "retained_vertices": len(eligible), "retained_edges": len(edges),
        "header_node_count_matches_observed": declared_nodes is None or declared_nodes == len(vertices),
        "header_edge_count_matches_raw_rows": declared_edges is None or declared_edges == raw_rows,
        "source_directed": source_directed,
        "conversion": "undirected simple projection; retain all observed vertices; deduplicate unordered edges and discard self-loop arcs",
        "original_looped_MWIS_preservation_claimed": False,
        "self_loop_semantics": "self-links are not treated as exclusion conflicts; looped-graph MWIS eligibility changes explicitly",
        "conversion_edge_sets_verified": True, "invented_isolated_vertices": 0,
        "decompressed_sha256": sha256(raw).hexdigest()}
    return tuple(sorted(eligible)), edges, receipt


def graph_record(name, vertices, edges, source, weight_mode):
    if weight_mode not in ("unit", "hash_weighted"):
        raise ValueError("Unknown declared weight mode")
    def weight(vertex):
        return 1 if weight_mode == "unit" else 1 + int(sha256(
            f"20261003:{name}:{vertex}".encode()).hexdigest(), 16) % 20
    contacts = tuple(Contact(str(v), weight(v), "public_graph", str(v), 0, 1) for v in vertices)
    canonical = frozenset(tuple(sorted((str(a), str(b)))) for a, b in edges)
    identifier = "SNAP_" + name + "_" + weight_mode
    graph = Graph(identifier, contacts, canonical,
        {"model": "explicit_public_conflict_graph", "station_gap": 0, "satellite_gap": 0},
        {"public_source": name, "weight_mode": weight_mode, "physical_scheduling_claim": False,
         "self_loop_conversion": source["self_loop_policy"]})
    if graph.edges != canonical or sum(len(a) for a in graph.adj.values()) != 2 * len(edges):
        raise AssertionError("Graph roundtrip/source edge verification failed")
    return {"id": identifier, "family": "SNAP_sparse", "cluster": name,
        "graph": graph.to_dict(), "fixed": [], "excluded": [],
        "source": {**source, "weight_mode": weight_mode,
            "weighted_extension": "SHA25620261003 original source vertex weights1..20" if weight_mode != "unit" else None,
            "weight_formula": "1+int(SHA256('20261003:'+dataset_name+':'+original_integer_ID),16)%20" if weight_mode != "unit" else "unit",
            "physical_scheduling_claim": False}}


def prepare(config_path, output, cache=None, archive_path=None):
    config_bytes = Path(config_path).read_bytes(); config = json.loads(config_bytes)
    if config.get("self_loop_policy") != "drop_loop_arcs" or config.get("node_count_mismatch_policy") != "unavailable":
        raise ValueError("This fixed extension requires explicit simple projection and no invented isolates")
    if config.get("weight_modes") != ["unit", "hash_weighted"]:
        raise ValueError("Fixed unit and hash-weighted modes required")
    root = Path(output); root.mkdir(parents=True, exist_ok=False)
    rawroot = root / "raw"; rawroot.mkdir()
    records, receipts, unavailable, pinned = [], [], [], []
    def write(name, value):
        (root / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    write("config.json", config)
    write("protocol_before_fetch.json", {"declared_sources": config["datasets"],
        "declared_contexts": 2 * len(config["datasets"]), "config_sha256": sha256(config_bytes).hexdigest(),
        "created_utc": datetime.now(timezone.utc).isoformat(), "outcome_selection": False,
        "solver_calls": 0, "programme_changes": 0, "scope": config["scope"]})
    for dataset in config["datasets"]:
        name, url = dataset["name"], dataset["url"]
        receipt = {"id": name, **dataset}
        try:
            filename = url.rsplit("/", 1)[-1]
            cached = Path(cache) / filename if cache else None
            if cached and cached.is_file():
                compressed = cached.read_bytes(); fetched = "supplied_raw_cache"
            else:
                with urlopen(Request(url, headers={"User-Agent": "CIPHeur-research-input-preparation"}), timeout=30) as response:
                    compressed = response.read()
                    receipt["response_url"] = response.url
                    receipt["http_content_length"] = response.headers.get("Content-Length")
                    receipt["http_last_modified"] = response.headers.get("Last-Modified")
                fetched = "official_HTTPS"
            digest = sha256(compressed).hexdigest()
            receipt.update(compressed_sha256=digest, raw_bytes=len(compressed), acquisition=fetched)
            (rawroot / filename).write_bytes(compressed)
            if dataset.get("sha256") and digest != dataset["sha256"]:
                raise ValueError("Pinned raw source hash mismatch")
            vertices, edges, parsed = parse_snap(gzip.decompress(compressed),
                source_directed=dataset["directed"], self_loop_policy=config["self_loop_policy"])
            receipt.update(parsed)
            expected = dataset["official_declared_nodes"]
            if (parsed["observed_original_vertices"] != expected
                    or not parsed["header_node_count_matches_observed"]):
                raise ValueError("Declared vertex count differs from observed endpoint IDs; isolated identities are unknown")
            receipt["official_edge_count_matches_canonical_including_loops"] = (
                dataset["official_declared_edges"] == parsed["canonical_nonloop_edges_before_restriction"] + parsed["unique_self_loop_vertices"])
            receipts.append(receipt)
            pinned.append({**dataset, "sha256": digest})
            records.extend(graph_record(name, vertices, edges, receipt, mode) for mode in config["weight_modes"])
        except Exception as error:
            unavailable.append({**receipt, "error": {"type": type(error).__name__, "message": str(error)}})
        print(json.dumps({"source": name, "prepared_contexts": len(records), "unavailable_sources": len(unavailable)}), flush=True)
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate prepared instance IDs")
    write("data.json", {"public": records}); write("source_receipts.json", receipts)
    write("pinned_config.json", {**config, "datasets": pinned})
    write("protocol.json", {"config_sha256": sha256(config_bytes).hexdigest(),
        "declared_contexts": 2 * len(config["datasets"]), "retained_contexts": len(records),
        "unavailable_sources": unavailable, "outcome_selection": False, "solver_calls": 0,
        "programme_changes": 0, "scope": config["scope"], "original_challenge_protocol_unchanged": True,
        "independent_unit": "four source graphs; two weight modes share each source"})
    write("complete.json", {"input_preparation_complete": True, "all_declared_sources_retained": not unavailable,
        "retained_contexts": len(records), "unavailable_sources": len(unavailable),
        "data_sha256": sha256((root / "data.json").read_bytes()).hexdigest(), "solver_calls": 0})
    if archive_path:
        target = Path(archive_path)
        if target.exists():
            raise FileExistsError("Preserve existing input archive")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(target, "w:gz") as archive:
            archive.add(root, arcname=root.name)
    return records, receipts, unavailable


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--cache"); parser.add_argument("--archive")
    args = parser.parse_args()
    prepare(args.config, args.output, args.cache, args.archive)
