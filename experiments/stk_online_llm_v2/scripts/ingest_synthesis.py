"""Gate actual model completions without repairing or replacing their recipes.

Uses the previous study's exact event_audit function.  Failed API attempts and
pending calls remain in audit.json.  Whole calls pass only when every original
recipe passes the recorded JSON schema and the executable typed validator.
No model, optimizer, cloud, historical fit, VAL or TEST outcomes are accessed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OLD = PROJECT / "experiments" / "stk_full_llm_v1"
ARMS = ("witness_operators", "feedback_operators")


def digest(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_event_audit(old_root):
    """Import the original function rather than interpreting tools anew."""
    scripts = Path(old_root) / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("cipheur_v1_actual_event_audit", scripts / "llm_cli_proposer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.event_audit


def validate_response_schema(instance, schema):
    """Validate the entire known schema vocabulary without extra dependencies.

    This is a closed-vocabulary JSON Schema evaluator for these recorded schemas,
    not a general JSON Schema implementation.  An unsupported keyword is fatal;
    it cannot silently weaken a gate.  $ref/anyOf/oneOf/type/required/properties/
    additionalProperties/enum/const/array lengths/numeric/string bounds/pattern
    are enforced.  The executable typed checker additionally enforces result
    types, safe numeric rule ASTs and expression size/depth bounds.
    """
    supported = {"$schema", "$id", "$defs", "$ref", "title", "description",
                 "type", "properties", "required", "additionalProperties",
                 "enum", "const", "items", "minItems", "maxItems", "minimum",
                 "maximum", "minLength", "maxLength", "pattern", "oneOf", "anyOf"}

    def resolve(reference):
        if not isinstance(reference, str) or not reference.startswith("#/"):
            raise ValueError("Only recorded local schema references are supported")
        result = schema
        for component in reference[2:].split("/"):
            result = result[component.replace("~1", "/").replace("~0", "~")]
        return result

    def visit(value, current, location="$", depth=0):
        if depth > 128 or not isinstance(current, dict):
            raise ValueError("Invalid or excessively deep recorded schema")
        unknown = set(current) - supported
        if unknown:
            raise ValueError("Unsupported schema keywords: " + repr(sorted(unknown)))
        if "$ref" in current:
            visit(value, resolve(current["$ref"]), location, depth + 1)
        for union in ("anyOf", "oneOf"):
            if union in current:
                matches = 0
                for branch in current[union]:
                    try:
                        visit(value, branch, location, depth + 1)
                        matches += 1
                    except ValueError:
                        pass
                if not matches or (union == "oneOf" and matches != 1):
                    raise ValueError(location + ": " + union + " failed")
        kind = current.get("type")
        matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
                   "string": isinstance(value, str), "boolean": type(value) is bool,
                   "null": value is None, "integer": type(value) is int,
                   "number": type(value) in (int, float) and math.isfinite(value)}
        if kind is not None and (kind not in matches or not matches[kind]):
            raise ValueError(location + ": unexpected JSON type")
        if "const" in current and (type(value) is not type(current["const"]) or value != current["const"]):
            raise ValueError(location + ": const differs")
        if "enum" in current and not any(type(value) is type(v) and value == v for v in current["enum"]):
            raise ValueError(location + ": enum differs")
        if isinstance(value, dict):
            properties = current.get("properties", {})
            missing = set(current.get("required", [])) - set(value)
            if missing:
                raise ValueError(location + ": missing " + repr(sorted(missing)))
            if current.get("additionalProperties") is False and set(value) - set(properties):
                raise ValueError(location + ": additional fields")
            for key, item in value.items():
                if key in properties:
                    visit(item, properties[key], location + "." + key, depth + 1)
        elif isinstance(value, list):
            if len(value) < current.get("minItems", 0) or len(value) > current.get("maxItems", math.inf):
                raise ValueError(location + ": array length differs")
            if "items" in current:
                for index, item in enumerate(value):
                    visit(item, current["items"], f"{location}[{index}]", depth + 1)
        elif isinstance(value, str):
            if len(value) < current.get("minLength", 0) or len(value) > current.get("maxLength", math.inf):
                raise ValueError(location + ": string length differs")
            if "pattern" in current and re.search(current["pattern"], value) is None:
                raise ValueError(location + ": pattern differs")
        elif type(value) in (int, float):
            if not math.isfinite(value) or value < current.get("minimum", -math.inf) or value > current.get("maximum", math.inf):
                raise ValueError(location + ": numeric bound differs")
    visit(instance, schema)


def inspect_call(folder, event_audit):
    plan_path = folder / "call_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    call_id = plan.get("call_id", folder.name)
    arm = next((a for a in ARMS if str(call_id).startswith(a + ".r1.b")), None)
    if arm is None:
        return None, []
    paths = {key: folder / filename for key, filename in
             (("prompt", "prompt.txt"), ("schema", "response_schema.json"),
              ("receipt", "execution_receipt.json"), ("events", "events.jsonl"),
              ("response", "response.json"), ("stderr", "stderr.txt"))}
    report = {"actual_attempt_id": folder.name, "call_id": call_id, "arm": arm,
              "folder": str(folder), "actual_invocation_recorded": paths["receipt"].is_file(),
              "files_sha256": {key: digest(path) for key, path in paths.items()},
              "call_plan_sha256": digest(plan_path), "gate_errors": [],
              "recipes_requested": plan.get("recipes_requested", 6), "recipes_valid": 0,
              "invalid_recipes": [], "model_requested": plan.get("model_requested"),
              "model_observed": "unknown", "silent_replacement": False}
    errors = report["gate_errors"]
    receipt = {}
    if paths["receipt"].is_file():
        try:
            receipt = json.loads(paths["receipt"].read_text(encoding="utf-8"))
        except Exception as error:
            errors.append("unreadable actual receipt: " + str(error))
    report["execution_receipt"] = receipt
    report["status"] = "pending" if not receipt or receipt.get("state") == "running" else "rejected"
    report["wall_seconds"] = receipt.get("wall_seconds")
    audit = None
    if paths["events"].is_file():
        try:
            audit = event_audit(paths["events"])
        except Exception as error:
            errors.append("unreadable event stream: " + str(error))
    else:
        errors.append("actual event stream missing")
    report["event_audit"] = audit
    if audit:
        report["model_observed"] = audit["model_observed"]
        report["usage"] = audit["usage_sum"]
    else:
        report["usage"] = {}
    if report["status"] == "pending":
        return report, []
    if receipt.get("exit_code") != 0:
        errors.append("actual invocation has nonzero or unavailable exit code")
    if audit:
        if audit["tool_call_count"] != 0:
            errors.append("actual tool actions contaminate stdin-only synthesis")
        if audit["turns_completed"] != 1 or audit["errors"]:
            errors.append("requires exactly one completed turn and no failed/error event")
    if report["files_sha256"]["prompt"] != plan.get("prompt_sha256"):
        errors.append("recorded prompt SHA differs")
    if report["files_sha256"]["schema"] != plan.get("schema_sha256"):
        errors.append("recorded response-schema SHA differs")
    response = None
    try:
        response = json.loads(paths["response"].read_text(encoding="utf-8"))
        schema = json.loads(paths["schema"].read_text(encoding="utf-8"))
        validate_response_schema(response, schema)
        if len(response["recipes"]) != report["recipes_requested"]:
            raise ValueError("Original requested recipe count differs")
        from cipheur.online_v2.typed import validate_recipe
        for slot, proposed in enumerate(response["recipes"]):
            try:
                validate_recipe(proposed)
            except Exception as error:
                report["invalid_recipes"].append({"slot": slot, "reason": str(error),
                                                   "original_proposed_recipe": proposed})
        if report["invalid_recipes"]:
            raise ValueError("A bad original recipe excludes its entire call; no replacement")
    except Exception as error:
        errors.append("original response validation failed: " + str(error))
    failure_text = json.dumps(audit or {}, ensure_ascii=False)
    if paths["stderr"].is_file():
        failure_text += paths["stderr"].read_text(encoding="utf-8", errors="replace")
    report["api_schema_oneof_error"] = receipt.get("exit_code") != 0 and "oneOf" in failure_text
    if errors:
        return report, []
    report["status"] = "accepted"
    report["recipes_valid"] = len(response["recipes"])
    report["recipe_slots"] = [{"slot": slot, "name": recipe["name"],
                                "recipe_sha256": hashlib.sha256(json.dumps(recipe, sort_keys=True,
                                 separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}
                               for slot, recipe in enumerate(response["recipes"])]
    return report, response["recipes"]


def ingest(output_root=ROOT, old_root=OLD, allow_pending=False):
    output_root, old_root = Path(output_root).resolve(), Path(old_root).resolve()
    sys.path.insert(0, str(PROJECT))
    event_audit = load_event_audit(old_root)
    reports, by_arm = [], {arm: [] for arm in ARMS}
    for folder in sorted((output_root / "llm_calls").iterdir()):
        if not folder.is_dir() or not (folder / "call_plan.json").is_file():
            continue
        report, recipes = inspect_call(folder, event_audit)
        if report is not None:
            reports.append(report)
            by_arm[report["arm"]].extend(recipes)
    totals = Counter()
    for report in reports:
        for key, value in report["usage"].items():
            if type(value) is int:
                totals[key] += value
    pending = [report["actual_attempt_id"] for report in reports if report["status"] == "pending"]
    audit = {"version": "stk_online_llm_v2_actual_call_audit", "calls": reports,
             "actual_calls_recorded": sum(r["actual_invocation_recorded"] for r in reports),
             "accepted_calls": sum(r["status"] == "accepted" for r in reports),
             "api_schema_oneof_failed_calls": sum(r.get("api_schema_oneof_error", False) for r in reports),
             "pending_calls": pending, "usage_sum_known": dict(totals),
             "usage_missing_actual_calls": [r["actual_attempt_id"] for r in reports
                 if r["actual_invocation_recorded"] and not r["usage"]],
             "wall_seconds_known_sum": sum(r["wall_seconds"] for r in reports
                 if type(r["wall_seconds"]) in (int, float)),
             "served_model_policy": "Only actual event metadata; requested labels and model-authored claims do not identify the served version",
             "event_audit_source_sha256": digest(old_root / "scripts" / "llm_cli_proposer.py"),
             "ingestion_source_sha256": digest(__file__),
             "selection_by_quality_fit_or_structural_challenge": False,
             "failed_calls_preserved": True, "silent_recipe_replacement": False,
             "USD_cost": None, "USD_cost_reason": "No invoice or known served-model billing metadata supplied",
             "banks": {}}
    ready = not pending or allow_pending
    for arm, recipes in by_arm.items():
        names = Counter(recipe["name"] for recipe in recipes)
        bank_path = output_root / "banks" / (arm + ".json")
        audit["banks"][arm] = {"path": str(bank_path), "recipes": len(recipes),
                               "duplicate_names_retained": [name for name, count in names.items() if count > 1],
                               "written": bool(ready and recipes)}
        if ready and recipes:
            save(bank_path, {"schema_version": "stk_online_llm_v2", "recipes": recipes})
            audit["banks"][arm]["sha256"] = digest(bank_path)
    save(output_root / "audit.json", audit)
    print(json.dumps({"actual_calls": audit["actual_calls_recorded"],
                      "accepted_calls": audit["accepted_calls"], "pending": pending,
                      "recipes": {arm: len(recipes) for arm, recipes in by_arm.items()},
                      "audit": str(output_root / "audit.json")}, ensure_ascii=False))
    return 0 if ready and all(by_arm.values()) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--old-root", type=Path, default=OLD)
    parser.add_argument("--allow-pending", action="store_true", help="Explicit partial banks, never a final freeze")
    args = parser.parse_args()
    raise SystemExit(ingest(args.output_root, args.old_root, args.allow_pending))
