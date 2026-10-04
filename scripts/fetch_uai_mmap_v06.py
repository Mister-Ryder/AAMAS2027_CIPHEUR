"""Fetch every pinned UAI/MMAP input; inventory exact weights without solving."""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha1, sha256
import json
from math import gcd, lcm
from pathlib import Path
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "experiments/discovery/v06_public_metadata_001/inventory.json"
PLAN = ROOT / "experiments/discovery/uai_mmap_v06_001"
OUT = ROOT / "output/uai_mmap_v06_001"
COMMIT = "a0fd6b631136255807a98727b496a09a65b3301d"
SALT = "v06_uai_mmap_source_cluster_split_001"


def digest(raw):
    return sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n").encode("utf-8"))


def prepare():
    if PLAN.exists():
        raise ValueError("Preserve original outcome-free input-selection protocol")
    metadata = json.loads(META.read_text())
    assert metadata["commit"] == COMMIT and metadata["truncated"] is False
    sources = [r for r in metadata["tree"] if r["type"] == "blob" and
               r["path"].startswith("UAI/MMAP/") and r["path"].endswith(".mwvc")]
    assert len(sources) == 81 and sum(r["size"] for r in sources) == 11266187
    clusters = sorted({Path(r["path"]).stem for r in sources},
                      key=lambda s: sha256((SALT + "|" + s).encode()).digest())
    train = set(clusters[:len(clusters)//2])
    rows = [{"path": r["path"], "git_blob_sha1": r["sha"], "declared_bytes": r["size"],
             "source_cluster": Path(r["path"]).stem,
             "family": Path(r["path"]).stem.rsplit("_", 1)[0],
             "split": "train" if Path(r["path"]).stem in train else "test"}
            for r in sorted(sources, key=lambda r: r["path"])]
    protocol = {"version": "uai_mmap_input_inventory_v06_001", "before_any_optimization": True,
                "repository": "jamestrimble/max-weight-clique-instances", "commit": COMMIT,
                "metadata_sha256": digest(META.read_bytes()), "sources": rows,
                "all_declared_81_mmap_files_retained": True,
                "split_salt": SALT, "split_scope": "SHA-ordered original source instance cluster; all future derived views stay in that cluster",
                "train_clusters": 40, "test_clusters": 41,
                "family_disjoint": False, "performance_selection_permitted": False,
                "source_order_is_not_performance_order": True,
                "graph_orientation": "native supplied edges are MWIS conflicts; no complement",
                "exact_weight_parser": "fractions.Fraction on raw weight strings, no binary float conversion or rounding",
                "native_encoding_inventory": "direct exact denominator LCM and conservative signed32 sum; separate exact common-GCD reduction feasibility",
                "zero_negative_and_format_failures_retained": True,
                "download_failures_retained": True, "graph_queries": 0,
                "script_sha256": digest(Path(__file__).read_bytes())}
    write(PLAN / "protocol.json", protocol)
    write(PLAN / "freeze_receipt.json", {"before_any_optimization": True,
          "protocol_sha256": digest((PLAN / "protocol.json").read_bytes()),
          "script_sha256": protocol["script_sha256"], "metadata_sha256": protocol["metadata_sha256"]})
    print(json.dumps({"protocol_sha256": digest((PLAN / "protocol.json").read_bytes()),
                      "files": len(rows), "train_clusters": 40, "test_clusters": 41}), flush=True)


def parse_dimacs(raw):
    weights, edges, header, edge_lines = {}, set(), None, 0
    duplicate_edges = 0
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        tokens = line.split()
        if not tokens or tokens[0] in ("c", "#"):
            continue
        if tokens[0] == "p":
            if len(tokens) != 4 or header is not None:
                raise ValueError(f"Invalid/repeated header at line {number}")
            header = (tokens[1], int(tokens[2]), int(tokens[3]))
        elif tokens[0] == "n":
            if len(tokens) != 3:
                raise ValueError(f"Invalid weight row at line {number}")
            node, weight = int(tokens[1]), Fraction(tokens[2])
            if node in weights:
                raise ValueError(f"Repeated vertex weight at line {number}")
            weights[node] = weight
        elif tokens[0] == "e":
            if len(tokens) != 3:
                raise ValueError(f"Invalid edge row at line {number}")
            a, b = int(tokens[1]), int(tokens[2])
            if a == b:
                raise ValueError(f"Self-loop at line {number}")
            edge = tuple(sorted((a, b)))
            duplicate_edges += edge in edges
            edges.add(edge)
            edge_lines += 1
        else:
            raise ValueError(f"Unknown row type {tokens[0]} at line {number}")
    if header is None or header[0] not in ("edge", "edges", "col"):
        raise ValueError("Missing/unsupported DIMACS graph header")
    kind, n, m = header
    if n < 0 or m < 0 or set(weights) != set(range(1, n+1)):
        raise ValueError("Weight rows must cover exactly vertices 1..n")
    if any(a not in weights or b not in weights for a, b in edges):
        raise ValueError("Edge endpoint outside declared graph")
    if edge_lines != m:
        raise ValueError("Declared edge count differs from raw edge rows")
    scale = 1
    for weight in weights.values():
        scale = lcm(scale, weight.denominator)
    scaled = [int(weights[v] * scale) for v in sorted(weights)]
    divisor = 0
    for weight in scaled:
        divisor = gcd(divisor, abs(weight))
    reduced = [weight // max(1, divisor) for weight in scaled]
    direct = all(w >= 0 for w in scaled) and sum(scaled) <= 2**31-1
    reduction = all(w >= 0 for w in reduced) and sum(reduced) <= 2**31-1
    return {"n": n, "m_declared": m, "m_unique": len(edges),
            "duplicate_edges": duplicate_edges, "header_kind": kind,
            "density": 2*len(edges)/(n*(n-1)) if n > 1 else 0,
            "min_weight_exact": str(min(weights.values())) if weights else None,
            "max_weight_exact": str(max(weights.values())) if weights else None,
            "sum_weight_exact": str(sum(weights.values(), Fraction(0))),
            "weight_integer_count": sum(w.denominator == 1 for w in weights.values()),
            "zero_weights": sum(w == 0 for w in weights.values()),
            "negative_weights": sum(w < 0 for w in weights.values()),
            "unique_weights": len(set(weights.values())),
            "exact_denominator_scale": str(scale), "scaled_total_weight": str(sum(scaled)),
            "integer_common_gcd": str(divisor), "gcd_reduced_total_weight": str(sum(reduced)),
            "direct_native_signed32_compatible": direct,
            "gcd_reduced_native_signed32_compatible": reduction,
            "weight_exact_digest": digest(json.dumps({str(v): str(weights[v]) for v in sorted(weights)},
                                                     sort_keys=True).encode()),
            "edge_digest": digest(json.dumps(sorted(edges)).encode())}


def fetch():
    protocol = json.loads((PLAN / "protocol.json").read_text())
    frozen = json.loads((PLAN / "freeze_receipt.json").read_text())
    assert digest((PLAN / "protocol.json").read_bytes()) == frozen["protocol_sha256"]
    assert digest(Path(__file__).read_bytes()) == frozen["script_sha256"]
    assert protocol["before_any_optimization"] and protocol["performance_selection_permitted"] is False
    if OUT.exists():
        raise ValueError("Preserve first raw-input acquisition receipt; no overwrite")
    OUT.mkdir(parents=True)
    records = []
    started = time.perf_counter()
    for source in protocol["sources"]:
        record = dict(source)
        url = f"https://raw.githubusercontent.com/{protocol['repository']}/{COMMIT}/{source['path']}"
        record["url"] = url
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "AAMAS-outcome-free-input-inventory"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
            if len(raw) != source["declared_bytes"]:
                raise ValueError("Raw byte count differs from pinned tree")
            blob = sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if blob != source["git_blob_sha1"]:
                raise ValueError("Raw Git blob identity differs from pinned tree")
            path = OUT / source["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            record.update(download_status="complete", raw_sha256=digest(raw), raw_bytes=len(raw))
            try:
                record.update(parse_status="valid", **parse_dimacs(raw))
            except Exception as error:
                record.update(parse_status="error", parse_error={"type": type(error).__name__, "message": str(error)})
        except Exception as error:
            record.update(download_status="error", download_error={"type": type(error).__name__, "message": str(error)})
        records.append(record)
        write(OUT / "progress.json", {"assigned": len(protocol["sources"]), "returned": len(records),
              "status": dict(Counter(r["download_status"] for r in records))})
    write(OUT / "inventory.json", {"records": records, "graph_optimizations": 0,
                                   "protocol_sha256": frozen["protocol_sha256"]})
    for name in ("protocol.json", "freeze_receipt.json"):
        (OUT / name).write_bytes((PLAN / name).read_bytes())
    write(OUT / "complete.json", {"assigned": 81, "returned": len(records),
          "download_status": dict(Counter(r["download_status"] for r in records)),
          "parse_status": dict(Counter(r.get("parse_status", "not_downloaded") for r in records)),
          "raw_bytes": sum(r.get("raw_bytes", 0) for r in records),
          "inventory_sha256": digest((OUT / "inventory.json").read_bytes()),
          "script_sha256": frozen["script_sha256"], "protocol_sha256": frozen["protocol_sha256"],
          "wall_seconds": time.perf_counter()-started, "graph_optimizations": 0,
          "test_graph_optimizations": 0, "all_failed_sources_retained": True})
    archive = ROOT / "experiments/runs/v06/uai_mmap_inputs_v06_001.tar.gz"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(OUT, arcname="uai_mmap_v06_001")
    write(PLAN / "acquisition_receipt.json", {"archive_sha256": digest(archive.read_bytes()),
          "archive_bytes": archive.stat().st_size, "complete_sha256": digest((OUT / "complete.json").read_bytes()),
          "no_benchmark_solver_calls": True})
    print(json.dumps(json.loads((OUT / "complete.json").read_text())), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "fetch"))
    args = parser.parse_args()
    prepare() if args.mode == "prepare" else fetch()
