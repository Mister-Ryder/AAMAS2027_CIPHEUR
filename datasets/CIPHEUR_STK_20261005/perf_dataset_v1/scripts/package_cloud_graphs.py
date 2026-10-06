"""Byte-preserving held-out graph archive; no raw windows, labels or scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

PERF_ROOT = Path(__file__).resolve().parents[1]
BASE_ROOT = PERF_ROOT.parent
SOURCES = ("CP-AU-r006", "CP-AP-r006", "CP-AU-r008", "CP-AP-r008", "CP-AU-r009", "CP-AP-r009")
TRAIN_SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
TRAIN_CONFIGS = ("gW0340_gE0340_s0150", "gW1200_gE0340_s0150", "gW0340_gE1200_s0150", "gW1200_gE1200_s0150")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", help="Requested comma-separated physical sources; default all ready")
    args = parser.parse_args()
    requested = args.sources.split(",") if args.sources else list(SOURCES)
    if any(source not in SOURCES for source in requested):
        raise ValueError("Unregistered performance source")
    ready = []
    for source in requested:
        path = PERF_ROOT / "graphs" / source / "summary.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "success":
            ready.append(source)
        elif args.sources:
            raise RuntimeError(f"Explicitly requested source is not ready: {source}")
    if not ready:
        raise RuntimeError("No complete graph sources to package")
    members, graph_records = [], []
    for source in ready:
        folder = PERF_ROOT / "graphs" / source
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        if summary["unique_graph_configurations"] != 8:
            raise RuntimeError("Expected eight unique configurations")
        for metadata in summary["graphs"]:
            path = folder / f"{metadata['config_id']}.npz"
            if sha(path) != metadata["npz_sha256"]:
                raise RuntimeError(f"Local NPZ bytes disagree with their metadata: {path}")
            graph_records.append({"source_id": source, "source_group": metadata["source_group"],
                                  "config_id": metadata["config_id"],
                                  "split": {"validation": "val", "val": "val", "test": "test"}[metadata["split"]],
                                  "original_split": metadata["split"],
                                  "archive_path": f"data/graphs/{source}/{path.name}",
                                  "npz_sha256": metadata["npz_sha256"]})
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix in (".npz", ".json"):
                members.append((path, f"data/graphs/{source}/{path.name}"))
    # Configuration and source index are JSON provenance, not raw opportunities.
    for relative in ("source_plan/perf_graph_parameters.json", "source_index.json"):
        path = PERF_ROOT / relative
        members.append((path, "data/" + relative))
    train_references = []
    for source in TRAIN_SOURCES:
        for config in TRAIN_CONFIGS:
            path = BASE_ROOT / "extensions" / "heterogeneous_ground_v1" / "graphs" / source / f"{config}.npz"
            train_references.append({"source_id": source, "config_id": config, "split": "train",
                                     "existing_dataset_relative_path": str(path.relative_to(BASE_ROOT)).replace("\\", "/"),
                                     "npz_sha256": sha(path), "bundled": False,
                                     "cloud_path_resolution": "Resolve below root-managed existing TRAIN dataset directory; do not copy into this held-out archive."})
    manifest = {
        "schema_version": "cipheur-portable-heldout-input-graph-archive-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_ids": ready, "source_group_count": len({g["source_group"] for g in graph_records}),
        "graph_count": len(graph_records), "graph_records": graph_records,
        "contains_raw_or_labels_or_scores": False,
        "scientific_artifact_rewritten": False,
        "split_alias_note": "Archive NPZ and metadata bytes preserve original validation/test. Only this manifest uses val/test aliases, matching the benchmark normalized_split adapter.",
        "all_six_new_sources_complete": len(ready) == 6,
        "file_hashes": [{"archive_path": name, "sha256": sha(path), "size_bytes": path.stat().st_size}
                        for path, name in members],
        "existing_training_graph_references": train_references,
        "training_references_bundled": False,
        "test_policy": "Only input provenance and graph integrity are bundled. No TEST optimization/evidence/tuning/heuristic scoring is executed by packaging.",
    }
    destination = PERF_ROOT / "cloud_graphs.zip"
    temporary = PERF_ROOT / "cloud_graphs.zip.tmp"
    encoded_manifest = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
        for path, name in members:
            # NPZ is already compressed; archival preserves its original bytes.
            archive.write(path, name, compress_type=zipfile.ZIP_STORED if path.suffix == ".npz" else zipfile.ZIP_DEFLATED)
        archive.writestr("data/hash_manifest.json", encoded_manifest, compress_type=zipfile.ZIP_DEFLATED)
    temporary.replace(destination)
    external = {**manifest, "zip_filename": destination.name, "zip_sha256": sha(destination),
                "zip_size_bytes": destination.stat().st_size,
                "internal_hash_manifest_sha256": hashlib.sha256(encoded_manifest).hexdigest()}
    (PERF_ROOT / "cloud_graphs.manifest.json").write_text(json.dumps(external, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"zip": str(destination), "graphs": len(graph_records), "sources": ready,
                      "zip_sha256": external["zip_sha256"], "zip_size_bytes": external["zip_size_bytes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
