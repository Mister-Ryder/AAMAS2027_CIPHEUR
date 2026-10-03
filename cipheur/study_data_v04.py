"""Fresh v04 input builder; read prior input manifests, never prior outcomes.

The caller supplies every previously exposed v03 input container. Completeness
of that inventory is a declared protocol obligation, not something a filesystem
scan or this module can infer. C3 source IDs are excluded globally before any
new day-specific block is constructed; short blocks remain missing.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from .experiment_data import _record
from .model import Graph
from .relevance_synthesis_v04 import fresh_temporal_data
from .study_data import build_study


def _input_payload(path):
    path = Path(path)
    if path.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(path) as archive:
            members = [m for m in archive.getmembers() if m.isfile()
                       and (m.name == "data.json" or m.name.endswith("/data.json"))]
            if len(members) != 1:
                raise ValueError("Prior archive must identify exactly one data.json input member")
            payload = archive.extractfile(members[0]).read()
            member = members[0].name
    else:
        payload, member = path.read_bytes(), None
    return json.loads(payload), {"path": str(path), "member": member,
                               "input_sha256": sha256(payload).hexdigest()}


def prior_id_manifest(paths):
    """Collect ALL source original IDs in supplied train/validation/test inputs."""
    excluded, sources, source_hashes = set(), [], set()
    for path in paths:
        data, receipt = _input_payload(path)
        splits = [split for split in ("train", "validation", "test") if split in data]
        if not splits or any(not isinstance(data[s], list) for s in splits):
            raise ValueError("Prior input must contain explicit graph-record split lists")
        counts = {}
        for split in splits:
            counts[split] = {"records": len(data[split]), "c3_records": 0, "c3_ids": 0}
            for record in data[split]:
                if record.get("family") != "c3":
                    continue
                ids = record.get("source", {}).get("original_ids")
                if ids is None:
                    ids = record.get("left", {}).get("provenance", {}).get("original_ids")
                if not isinstance(ids, list) or not ids:
                    raise ValueError("Every prior C3 input must expose its original source IDs")
                normalized = [int(i) for i in ids]
                if len(set(normalized)) != len(normalized):
                    raise ValueError("Duplicate original IDs inside prior C3 source block")
                for side in ("left", "right"):
                    observed = {int(c["id"]) for c in record[side]["contacts"]}
                    if observed != set(normalized):
                        raise ValueError("Prior C3 original-ID manifest must match every actual contact on both sides")
                source = record.get("source", {})
                data_hash = source.get("source_data_sha256") or source.get("source_data", {}).get("sha256")
                if not data_hash:
                    raise ValueError("Prior C3 input requires an immutable source-data SHA256")
                source_hashes.add(data_hash)
                excluded.update(normalized)
                counts[split]["c3_records"] += 1
                counts[split]["c3_ids"] += len(normalized)
        sources.append({**receipt, "split_counts": counts})
    return {"version": "v04_prior_input_source_id_manifest", "sources": sources,
        "original_ids": sorted(excluded), "unique_original_ids": len(excluded),
        "source_data_sha256": sorted(source_hashes),
        "scope": "union of supplied prior input containers; caller must enumerate all exposed v03 inputs",
        "outcomes_read": False}


def build_fresh_study(config, frozen, prior_manifest=None, stable_root=None):
    """Build fresh validation/test inputs only after a TRAIN freeze receipt."""
    if (frozen.get("test_accessed") is not False or frozen.get("selection_split") != "train"
            or not frozen.get("programs")):
        raise ValueError("Fresh evaluation generation requires a nonempty TRAIN freeze with test_accessed=false")
    result = fresh_temporal_data(config)
    # The standard record schema carries contact and graph identity receipts and
    # an outcome-independent common-edge diagnostic plan used by later runners.
    for split, records in result.items():
        result[split] = [_record(p["id"], p["family"], Graph.from_dict(p["left"]),
                         Graph.from_dict(p["right"]), p["source"], p["fixed"], p["excluded"])
                         for p in records]
    c3_receipt = {"requested": bool(stable_root), "not_generated": not bool(stable_root)}
    if stable_root:
        if not prior_manifest or not prior_manifest.get("original_ids"):
            raise ValueError("Fresh C3 requires nonempty global prior original-ID exclusion manifest")
        excluded = set(prior_manifest["original_ids"])
        c3 = build_study({"regimes": [], "diagnostic_per_split": 0,
            "stable_root": stable_root, "exclude_original_ids": sorted(excluded),
            "c3_sizes": config["c3_target_sizes"],
            "c3_per_size": {"train": 0, "validation": config["c3_pairs_per_size"],
                            "test": config["c3_pairs_per_size"]}})
        if set(prior_manifest.get("source_data_sha256", ())) != {c3["protocol"]["c3"]["data_sha256"]}:
            raise ValueError("Every prior C3 manifest must refer to the same immutable data source as the fresh builder")
        used = set()
        for split in ("validation", "test"):
            for record in c3[split]:
                ids = set(record["source"]["original_ids"])
                if ids & excluded or ids & used:
                    raise AssertionError("Fresh C3 source identity overlap")
                used.update(ids)
                record["id"] = "v04_" + record["id"]
                record["source"]["origin"] = "v04_disjoint_c3_source_block"
                result[split].append(record)
        c3_receipt = {**c3["protocol"]["c3"], "requested": True,
            "excluded_original_ids_sha256": sha256(json.dumps(sorted(excluded)).encode()).hexdigest(),
            "prior_manifest_sha256": sha256(json.dumps(prior_manifest, sort_keys=True).encode()).hexdigest(),
            "scope": "unused day-1/day-2 C3 source contacts after global supplied-input exclusion; same physical data source",
            "inventory_completeness_is_caller_protocol_obligation": True}
    result["protocol"] = {"version": "fresh_v04_inputs_001", "outcome_filtering": False,
        "oracle_calls_during_generation": 0, "freeze_test_accessed": frozen["test_accessed"],
        "candidate_bank_sha256": frozen.get("candidate_bank_sha256"), "score_slice": True,
        "counts": {split: len(result[split]) for split in ("validation", "test")},
        "temporal_seed_namespace": config["seed_namespace"], "c3": c3_receipt,
        "split_rule": "fresh synthetic seed ranges; C3 day-1 validation and day-2 test after all supplied prior IDs excluded",
        "statistical_unit": config["independent_unit"]}
    for split in ("validation", "test"):
        result[split] = [{**record, "left": record["left"].to_dict(),
                          "right": record["right"].to_dict()}
                         for record in result[split]]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--frozen", required=True)
    parser.add_argument("--prior-input", nargs="+", default=[])
    parser.add_argument("--stable-root")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    frozen_bytes = Path(args.frozen).read_bytes()
    frozen = json.loads(frozen_bytes)
    manifest = prior_id_manifest(args.prior_input)
    result = build_fresh_study(config, frozen, manifest, args.stable_root)
    result["protocol"]["frozen_receipt_sha256"] = sha256(frozen_bytes).hexdigest()
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=False)
    for name, value in (("data.json", result), ("prior_original_id_manifest.json", manifest),
                        ("protocol.json", result["protocol"])):
        (root / name).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                          allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
