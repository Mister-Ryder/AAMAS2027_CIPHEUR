"""Lossless, explicit count-schema adapter; never performs an audit or a search.

The original independent report is immutable. This separate receipt changes
only dict/list count representation for frozen consumers requiring integers,
and binds both the original bytes and this adapter's bytes. It refuses failed
reports, inconsistent totals, and replacement of an existing receipt.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def normalize(original, expected_sha256, output):
    original, output = Path(original), Path(output)
    if output.exists():
        raise ValueError("Preserve every original and adapted receipt; no overwrite")
    if digest(original) != expected_sha256:
        raise ValueError("Original independent report byte binding changed")
    raw = original.read_bytes()
    report = json.loads(raw)
    checks, errors = report.get("checks"), report.get("errors")
    if (not isinstance(checks, dict) or not checks
            or any(type(v) is not int or v < 0 for v in checks.values())
            or sum(checks.values()) < 1
            or type(report.get("total_checks")) is not int
            or report.get("total_checks") != sum(checks.values())):
        raise ValueError("Require actual positive, consistent independent check counts")
    if (not isinstance(errors, list) or errors
            or type(report.get("error_count")) is not int or report.get("error_count") != 0):
        raise ValueError("Failed or inconsistent independent audit cannot be adapted")
    if any(k in report for k in ("original_check_categories", "original_error_records", "schema_adapter")):
        raise ValueError("Do not normalize an existing adapter or obscure its provenance")
    adapted = {**report, "checks": sum(checks.values()), "errors": len(errors),
               "original_check_categories": checks, "original_error_records": errors,
               "schema_adapter": {
                   "version": "v06_explicit_independent_count_schema_adapter_001",
                   "original_report_name": original.name,
                   "original_report_sha256": expected_sha256,
                   "adapter_source_sha256": digest(__file__),
                   "scope": "Count representation only; this receipt performs no new independent checks.",
                   "no_new_checks_or_reexecution": True,
                   "original_bytes_and_findings_unchanged": True}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(adapted, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    if original.read_bytes() != raw:
        raise ValueError("Original independent report changed during adaptation")
    return {"original_report_sha256": expected_sha256, "adapted_receipt_sha256": digest(output),
            "checks": adapted["checks"], "errors": adapted["errors"], "new_checks_performed": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(normalize(args.original, args.original_sha256, args.out)))
