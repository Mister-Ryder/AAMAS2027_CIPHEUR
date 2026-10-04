"""Outcome-free pinned WDP acquisition, exact weights and MWIS complement inventory."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha1, sha256
import json
from pathlib import Path
import sys
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.fetch_uai_mmap_v06 import parse_dimacs

META = ROOT / "experiments/discovery/v06_public_metadata_001/inventory.json"
PLAN = ROOT / "experiments/discovery/wdp_inputs_v06_001"
OUT = ROOT / "output/wdp_inputs_v06_001"
COMMIT = "a0fd6b631136255807a98727b496a09a65b3301d"
SALT = "v06_wdp_source_cluster_split_001"
SOURCES = ("scripts/fetch_wdp_v06.py", "scripts/fetch_uai_mmap_v06.py")


def digest(raw):
    return sha256(raw).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def prepare():
    if PLAN.exists():
        raise ValueError("Preserve registered WDP population and source split")
    metadata = json.loads(META.read_text())
    assert metadata["commit"] == COMMIT and metadata["truncated"] is False
    files = [r for r in metadata["tree"] if r["type"] == "blob" and r["path"].startswith("WDP/")]
    graphs = [r for r in files if r["path"].endswith(".grf")]
    assert len(files) == 51 and len(graphs) == 50
    assert sum(r["size"] for r in files) == 45017977
    clusters = sorted([Path(r["path"]).stem for r in graphs],
                      key=lambda s: digest((SALT + "|" + s).encode()))
    train = set(clusters[:25])
    sources = [{"path": r["path"], "git_blob_sha1": r["sha"], "declared_bytes": r["size"],
                "is_graph": r["path"].endswith(".grf"),
                "source_cluster": Path(r["path"]).stem if r["path"].endswith(".grf") else None,
                "family": "WDP_" + Path(r["path"]).stem[2] + "xx" if r["path"].endswith(".grf") else None,
                "split": ("train" if Path(r["path"]).stem in train else "test") if r["path"].endswith(".grf") else "metadata"}
               for r in sorted(files, key=lambda r: r["path"])]
    protocol = {"version": "wdp_inputs_v06_001", "before_any_optimization": True,
                "repository": "jamestrimble/max-weight-clique-instances", "commit": COMMIT,
                "metadata_sha256": digest(META.read_bytes()), "sources": sources,
                "all_raw_graphs_retained": 50, "metadata_files": 1,
                "split_salt": SALT, "train_clusters": 25, "test_clusters": 25,
                "split_scope": "SHA-ordered original .grf source cluster; all derived views/weights/seeds remain in source cluster",
                "family_disjoint": False, "performance_filtering_permitted": False,
                "graph_orientation": "source is maximum-weight clique; future MWIS conflict edges are the exact simple undirected complement, preserving weights and vertices",
                "raw_input_not_mutated": True,
                "exact_weight_parser": "Fraction(raw string); no float conversion or rounding",
                "encoding_inventory": "exact rational denominator LCM; conservative signed32 total; common-GCD-reduced compatibility separately reported",
                "format_zero_negative_download_and_encoding_failures_retained": True,
                "optimization_calls": 0,
                "source_sha256": {n: digest((ROOT/n).read_bytes()) for n in SOURCES}}
    write(PLAN / "protocol.json", protocol)
    write(PLAN / "freeze_receipt.json", {"before_any_download": True, "before_any_optimization": True,
          "protocol_sha256": digest((PLAN/"protocol.json").read_bytes()), "source_sha256": protocol["source_sha256"]})
    print(json.dumps({"protocol_sha256": digest((PLAN/"protocol.json").read_bytes()), "graphs": 50, "train": 25, "test": 25}), flush=True)


def fetch():
    protocol = json.loads((PLAN/"protocol.json").read_text())
    frozen = json.loads((PLAN/"freeze_receipt.json").read_text())
    assert digest((PLAN/"protocol.json").read_bytes()) == frozen["protocol_sha256"]
    for name, expected in frozen["source_sha256"].items():
        assert digest((ROOT/name).read_bytes()) == expected, name
    assert protocol["before_any_optimization"] and not protocol["performance_filtering_permitted"]
    if OUT.exists():
        raise ValueError("Preserve first pinned WDP raw acquisition")
    OUT.mkdir(parents=True)
    rows, started = [], time.perf_counter()
    for source in protocol["sources"]:
        row = dict(source)
        row["url"] = f"https://raw.githubusercontent.com/{protocol['repository']}/{COMMIT}/{source['path']}"
        try:
            request = urllib.request.Request(row["url"], headers={"User-Agent": "AAMAS-outcome-free-WDP-inventory"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
            assert len(raw) == source["declared_bytes"], "Pinned byte count mismatch"
            assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == source["git_blob_sha1"], "Pinned Git blob mismatch"
            path = OUT/source["path"]; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            row.update(download_status="complete", raw_sha256=digest(raw), raw_bytes=len(raw))
            if source["is_graph"]:
                try:
                    parsed = parse_dimacs(raw)
                    row.update(parse_status="valid", **parsed,
                               mwis_complement_edges=parsed["n"]*(parsed["n"]-1)//2-parsed["m_unique"])
                except Exception as error:
                    row.update(parse_status="error", parse_error={"type": type(error).__name__, "message": str(error)})
            else:
                row["parse_status"] = "metadata"
        except Exception as error:
            row.update(download_status="error", download_error={"type": type(error).__name__, "message": str(error)})
        rows.append(row)
        write(OUT/"progress.json", {"assigned": 51, "returned": len(rows),
              "download_status": dict(Counter(r["download_status"] for r in rows))})
    write(OUT/"inventory.json", {"records": rows, "optimization_calls": 0,
                                "protocol_sha256": frozen["protocol_sha256"]})
    for name in ("protocol.json", "freeze_receipt.json"):
        (OUT/name).write_bytes((PLAN/name).read_bytes())
    write(OUT/"complete.json", {"assigned": 51, "graph_files": 50, "returned": len(rows),
          "download_status": dict(Counter(r["download_status"] for r in rows)),
          "parse_status": dict(Counter(r.get("parse_status", "not_downloaded") for r in rows)),
          "raw_bytes": sum(r.get("raw_bytes", 0) for r in rows),
          "inventory_sha256": digest((OUT/"inventory.json").read_bytes()),
          "protocol_sha256": frozen["protocol_sha256"], "source_sha256": frozen["source_sha256"],
          "wall_seconds": time.perf_counter()-started, "optimization_calls": 0,
          "all_failed_sources_retained": True})
    archive = ROOT/"experiments/runs/v06/wdp_inputs_v06_001.tar.gz"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "x:gz") as tar:
        tar.add(OUT, arcname="wdp_inputs_v06_001")
    write(PLAN/"acquisition_receipt.json", {"archive_sha256": digest(archive.read_bytes()),
          "archive_bytes": archive.stat().st_size, "complete_sha256": digest((OUT/"complete.json").read_bytes()),
          "optimization_calls": 0})
    print(json.dumps(json.loads((OUT/"complete.json").read_text())), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "fetch"))
    args = parser.parse_args()
    prepare() if args.mode == "prepare" else fetch()
