"""Export one complete TRAIN development trajectory without rerunning work.

Only the two explicit experiment roots/stages below may be read. Raw output
SHA256 values are inherited from the bound, successful one-pass enrichment;
raw files are streamed once to ZIP without an additional hashing pass.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile


ALLOWED = {
    "/root/autodl-tmp/cipheur_stk_online_llm_20261006_001": "development",
    "/root/autodl-tmp/cipheur_stk_online_llm_20261006_002": "development_round2",
}
COUNT = 144
CHUNK = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def contained_file(path, directory):
    path = Path(path).resolve(strict=True)
    require(path.is_file() and path.is_relative_to(directory), "File outside approved scope: " + str(path))
    return path


def read_json_once(path, scope, buffers):
    path = contained_file(path, scope)
    data = path.read_bytes()
    buffers[path] = data
    return json.loads(data)


def stat_identity(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def stream_member(archive, path, member, inherited_sha=None):
    before = stat_identity(path)
    hasher = None if inherited_sha else hashlib.sha256()
    size = 0
    with path.open("rb") as source, archive.open(member, "w", force_zip64=True) as target:
        while block := source.read(CHUNK):
            target.write(block)
            size += len(block)
            if hasher is not None:
                hasher.update(block)
    require(stat_identity(path) == before and size == before[2], "Source changed during archive: " + str(path))
    return size, inherited_sha if inherited_sha else hasher.hexdigest()


def complete_stage(root, stage):
    stage_root = (root / stage).resolve(strict=True)
    require(stage_root == root / stage and stage_root.is_dir(), "Stage must be the exact approved directory")
    buffers = {}
    summary = read_json_once(stage_root / "execution_summary.json", stage_root, buffers)
    metrics = read_json_once(stage_root / "metrics.json", stage_root, buffers)
    require(summary.get("all_attempted") is True and summary.get("all_job_count") == COUNT
            and summary.get("complete_job_count") == COUNT and summary.get("failed_job_count") == 0
            and summary.get("method_error_or_non_ok_count") == 0 and not summary.get("failed_jobs")
            and summary.get("execution_status_counts") == {"ok": COUNT}, "Stage is not complete144/0failed/ok")
    records = metrics.get("records", [])
    require(metrics.get("all_job_count") == COUNT and len(records) == COUNT
            and metrics.get("method_error_or_non_ok_count") == 0 and not metrics.get("failed_jobs"),
            "Incomplete/error metrics")
    metrics_path = (stage_root / "metrics.json").resolve()
    summary_path = (stage_root / "execution_summary.json").resolve()
    require(summary.get("metrics_sha256") == digest(buffers[metrics_path]), "Metrics/summary SHA mismatch")
    queue = read_json_once(stage_root / "queue_registration.json", stage_root, buffers)
    require(queue.get("jobs") == COUNT and queue.get("jobs_sha256") == summary.get("jobs_sha256")
            and valid_sha(queue.get("jobs_sha256")), "Queue registration/summary binding mismatch")
    for key in ("benchmark_sha256", "queue_sha256"):
        require(valid_sha(queue.get(key)) and queue.get(key) == summary.get(key), "Queue/runtime receipt differs: " + key)
    lookup = {row.get("job_id"): row for row in records}
    require(len(lookup) == COUNT and None not in lookup, "Missing/duplicate metric job_id")
    statuses = {row.get("job_id"): row for row in summary.get("statuses", [])}
    require(len(statuses) == COUNT and set(statuses) == set(lookup), "Summary status denominator differs")
    enriched = read_json_once(stage_root / "enriched_metrics.json", stage_root, buffers)
    require(enriched.get("complete") is True and not enriched.get("errors")
            and enriched.get("raw_sources_checked_once") is True and enriched.get("all_job_count") == COUNT,
            "Prior one-pass raw verification is incomplete")
    require(enriched.get("metrics_sha256") == summary["metrics_sha256"]
            and enriched.get("execution_summary_sha256") == digest(buffers[summary_path]),
            "Enrichment belongs to different summary/metrics")
    enriched_rows = enriched.get("records", [])
    enriched_map = {row.get("job_id"): row for row in enriched_rows}
    require(len(enriched_rows) == COUNT and len(enriched_map) == COUNT and set(enriched_map) == set(lookup),
            "Enrichment job denominator differs")
    result_root = (stage_root / "results").resolve(strict=True)
    require(result_root == stage_root / "results", "Results directory resolves outside exact stage")
    receipt_root = (stage_root / "receipts").resolve(strict=True)
    require(receipt_root == stage_root / "receipts", "Receipts directory resolves outside exact stage")
    receipt_paths = list(receipt_root.glob("*.json"))
    require(len(receipt_paths) == COUNT, "Expected exactly144 per-job receipts")
    receipts = {}
    for path in receipt_paths:
        row = read_json_once(path, stage_root, buffers)
        require(row.get("job_id") not in receipts, "Duplicate per-job receipt")
        receipts[row.get("job_id")] = row
    require(set(receipts) == set(lookup), "Per-job receipt denominator differs")
    raw_files = {}
    for identifier, row in lookup.items():
        require(row.get("execution_status") == "ok" and row.get("feasible") is True and row.get("split") == "train",
                "Non-ok, non-feasible or non-TRAIN metric")
        require(valid_sha(row.get("output_sha256")), "Missing raw output SHA")
        output = contained_file(row["output"], result_root)
        require(output.parent == result_root and output.suffix == ".json", "Raw output must be a direct result JSON")
        require(output not in raw_files, "Repeated raw output path")
        for other in (statuses[identifier], receipts[identifier]):
            require(other.get("status") == "complete" and other.get("execution_status") == "ok"
                    and other.get("feasible") is True and other.get("returncode") == 0
                    and other.get("output_sha256") == row["output_sha256"]
                    and contained_file(other["output"], result_root) == output,
                    "Status/receipt is not bound to complete raw output")
        prior = enriched_map[identifier]
        require(prior.get("raw_output_sha256") == row["output_sha256"]
                and contained_file(prior["raw_output_path"], result_root) == output,
                "Raw output has no matching prior one-pass verification")
        raw_files[output] = (identifier, row["output_sha256"])
    return stage_root, buffers, raw_files


def export(root, stage, output):
    # Do not resolve/open user-supplied roots until lexical scope is accepted.
    root = Path(root)
    require(str(root) in ALLOWED and ALLOWED[str(root)] == stage, "Only the two explicit root/stage pairs are authorized")
    require(root.resolve(strict=True) == root, "Approved cloud root must not resolve elsewhere")
    stage_root, buffers, raw_files = complete_stage(root, stage)
    snapshots = sorted(root.glob("runtime_*.zip"))
    require(snapshots, "Missing runtime_*.zip source snapshot")
    snapshots = [contained_file(path, root) for path in snapshots]
    require(all(path.parent == root for path in snapshots), "Runtime snapshot must be directly in approved root")
    output = Path(output) if output else root / "review_archives" / (stage + "_full_trajectory.zip")
    output = output.resolve()
    require(output.is_relative_to(root) and output.suffix == ".zip" and not output.is_relative_to(stage_root),
            "Archive must be a new ZIP inside approved root and outside source stage")
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    require(not output.exists() and not receipt_path.exists(), "Refusing to overwrite archive/receipt")
    require(output not in snapshots, "Archive cannot replace a runtime snapshot")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    def entry(path, size, file_sha, origin, job_id=None):
        item = {"archive_member": path.relative_to(root).as_posix(), "original_path": str(path),
                "original_bytes": size, "sha256": file_sha, "sha256_origin": origin}
        if job_id is not None:
            item["job_id"] = job_id
        entries.append(item)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for path, data in sorted(buffers.items()):
            archive.writestr(path.relative_to(root).as_posix(), data)
            entry(path, len(data), digest(data), "computed_from_single_read_in_export")
        for path, (job_id, recorded_sha) in sorted(raw_files.items()):
            size, file_sha = stream_member(archive, path, path.relative_to(root).as_posix(), recorded_sha)
            entry(path, size, file_sha, "inherited_bound_queue_and_prior_one_pass_enrichment", job_id)
        for path in snapshots:
            size, file_sha = stream_member(archive, path, path.relative_to(root).as_posix())
            entry(path, size, file_sha, "computed_while_streaming_to_archive")
        manifest = {"schema_version": "stk_online_review_archive_v1", "stage": stage,
                    "created_utc": datetime.now(timezone.utc).isoformat(), "approved_root": str(root),
                    "complete_job_count": COUNT, "original_member_count": len(entries),
                    "original_bytes": sum(item["original_bytes"] for item in entries), "entries": entries,
                    "raw_sha_policy": "Inherited from recorded outputSHA bound to complete prior enrichment; not rehashed in export.",
                    "scope": "This stage's metrics, summary, queue registration, enrichment, 144 receipts, 144 raw results, and root runtime_*.zip only.",
                    "source_files_modified": False, "optimizer_calls": 0, "model_calls": 0, "test_results_read": False}
        archive.writestr("review_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    archive_hash = hashlib.sha256()
    with output.open("rb") as archive_source:
        while block := archive_source.read(CHUNK):
            archive_hash.update(block)
    receipt = {"schema_version": "stk_online_review_export_receipt_v1", "status": "complete",
               "approved_root": str(root), "stage": stage, "archive_path": str(output),
               "archive_sha256": archive_hash.hexdigest(), "compressed_archive_bytes": output.stat().st_size,
               "original_member_count": len(entries), "original_bytes": manifest["original_bytes"],
               "raw_result_count": len(raw_files), "receipt_count": COUNT, "runtime_snapshot_count": len(snapshots),
               "zip_compression_level": 1, "read_only_scope": manifest["scope"], "source_files_modified": False,
               "raw_sha_recomputed": False, "prior_enrichment_complete_bound": True,
               "optimizer_calls": 0, "model_calls": 0, "test_results_read": False,
               "archive_manifest_member": "review_manifest.json", "created_utc": datetime.now(timezone.utc).isoformat()}
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, choices=tuple(ALLOWED))
    parser.add_argument("--stage", required=True, choices=tuple(ALLOWED.values()))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.root, args.stage, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
