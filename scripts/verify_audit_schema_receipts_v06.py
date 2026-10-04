"""Independent field/byte comparator for count receipts, not a scientific audit.

Does not import or execute the normalizer, production assessor, model or solver.
Runs the design conditions separately on retained original and adapted files.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "refinement_train_audit_v06_002": "a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34",
    "refinement_authoring_audit_v06_002": "2c3327ae92e0deccabb054636bcabfd9e31ed317679837fc26b31243128b7f7c",
    "refinement_packet_audit_v06_002": "7cabb43f86f1346dfd7b0156c096fc05bfd70c6f24850ee663394137f803837c"}
ADAPTER_PIN = "d22bb897f2170359e8acc73ec614522bbef70ef5aeeb855b46b0d1238163c457"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def verify(out):
    checks, errors, rows = 0, [], []
    def check(value, label):
        nonlocal checks
        checks += 1
        if not value:
            errors.append(label)
    adapter = ROOT / "scripts/normalize_audit_receipt_v06.py"
    check(digest(adapter) == ADAPTER_PIN, "exact reviewed count-adapter bytes")
    for stem, expected in PINS.items():
        original = ROOT / "experiments/analysis/v06" / (stem + ".json")
        adapted = original.with_name(stem + "_scalar_receipt_001.json")
        a, b = json.loads(original.read_bytes()), json.loads(adapted.read_bytes())
        check(digest(original) == expected, stem + ": original independent bytes")
        cats = a["checks"]
        check(type(cats) is dict and len(cats) > 0, stem + ": actual categorized checks")
        check(all(type(v) is int and v >= 0 for v in cats.values()), stem + ": nonnegative integer counts")
        check(type(a["total_checks"]) is int and a["total_checks"] == sum(cats.values()) > 0,
              stem + ": positive consistent total")
        check(type(a["errors"]) is list and a["errors"] == [] and type(a["error_count"]) is int
              and a["error_count"] == 0, stem + ": original zero errors")
        check(type(b["checks"]) is int and b["checks"] == a["total_checks"] and type(b["errors"]) is int
              and b["errors"] == 0, stem + ": exact count representation")
        check(b["original_check_categories"] == cats and b["original_error_records"] == a["errors"],
              stem + ": categories and records retained")
        check(set(b) == set(a) | {"schema_adapter", "original_check_categories", "original_error_records"},
              stem + ": exact field inventory")
        for key, value in a.items():
            if key not in ("checks", "errors"):
                check(b[key] == value, stem + ": unchanged finding " + key)
        binding = b["schema_adapter"]
        check(binding["original_report_sha256"] == expected and binding["adapter_source_sha256"] == ADAPTER_PIN
              and binding["no_new_checks_or_reexecution"] is True
              and binding["original_bytes_and_findings_unchanged"] is True,
              stem + ": explicit original/source/count-only provenance")
        rows.append({"stem": stem, "original_report_sha256": expected,
                     "adapted_receipt_sha256": digest(adapted), "original_scientific_check_total": a["total_checks"]})
    report = {"version": "v06_count_schema_byte_field_review_001", "review_execution_by": "root",
              "design_independently_reviewed_by": "/root/v05_llm_audit before its subsequent account-quota failure",
              "checks": checks, "errors": len(errors), "error_records": errors,
              "schema_only_approved": not errors, "adapter_source_sha256": ADAPTER_PIN,
              "comparator_source_sha256": digest(__file__), "reports": rows,
              "new_scientific_audits_or_checks": 0, "TEST_accessed": False,
              "scope": "Separate byte/field compatibility review only; original independent scientific audits remain authoritative."}
    out = Path(out)
    if out.exists():
        raise ValueError("Review receipts cannot be overwritten")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"checks": checks, "errors": len(errors), "review_sha256": digest(out)}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    verify(parser.parse_args().out)
