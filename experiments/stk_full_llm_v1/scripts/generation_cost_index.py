"""Index observed native-CLI synthesis usage without estimating a served model.

No model is invoked. Missing usage stays unknown; cache and reasoning are
separate subcounts, never silently added to the input+output token total.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path

from llm_cli_proposer import event_audit
from train_context import CONDITIONS, digest, freeze_json, require

ROOT = Path(__file__).resolve().parents[1]
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def one_call(folder):
    plan_path = folder / "call_plan.json"
    plan = read(plan_path)
    receipt_path = folder / "execution_receipt.json"
    events_path = folder / "events.jsonl"
    report_path = folder / "ingest_report.v2.json"
    receipt = read(receipt_path) if receipt_path.is_file() else None
    audit = event_audit(events_path) if events_path.is_file() else None
    report = read(report_path) if report_path.is_file() else None
    if report is not None:
        require(report["audit_version"] == 2 and report["call_id"] == plan["call_id"], "Wrong ingest audit identity")
    usage = audit["usage_sum"] if audit is not None else {}
    tokens = {name: usage.get(name) for name in TOKEN_FIELDS}
    if tokens["output_tokens"] is not None and tokens["reasoning_output_tokens"] is not None:
        require(0 <= tokens["reasoning_output_tokens"] <= tokens["output_tokens"], "Reasoning subcount exceeds output")
    if tokens["input_tokens"] is not None and tokens["cached_input_tokens"] is not None:
        require(0 <= tokens["cached_input_tokens"] <= tokens["input_tokens"], "Cache-read subcount exceeds input")
    total = tokens["input_tokens"] + tokens["output_tokens"] if all(tokens[name] is not None for name in ("input_tokens", "output_tokens")) else None
    if receipt is not None:
        require(receipt["call_id"] == plan["call_id"] and receipt["prompt_sha256"] == plan["prompt_sha256"], "Invocation receipt identity mismatch")
    raw_paths = [plan_path]
    for path in (receipt_path, events_path, report_path, folder / "response.json", folder / "stderr.txt"):
        if path.is_file():
            raw_paths.append(path)
    # A request is budget-consuming even if rejected: no valid-slot replacement.
    actual_attempt_observed = receipt is not None or (events_path.is_file() and events_path.stat().st_size > 0)
    return {"call_id": plan["call_id"], "arm": plan["condition"], "round": plan["round"], "batch": plan["batch"],
        "requested_model_label": plan["model_requested"], "requested_reasoning_effort": plan["reasoning_effort_requested"],
        "observed_model_label": audit["model_observed"] if audit is not None else "unknown",
        "served_model_version": "unknown", "served_model_version_inferred_from_request": False,
        "candidates_requested": plan["candidates_requested"],
        "candidate_slots_consumed": plan["candidates_requested"] if actual_attempt_observed else 0,
        "valid_candidates": report["valid_candidates"] if report is not None else None,
        "rejected_slots": len(report["rejected"]) if report is not None else None,
        "ingest_gate_errors": report["gate_errors"] if report is not None else None,
        "validity_status": "audited_v2" if report is not None else "not_yet_ingested",
        "attempt_observed": actual_attempt_observed, "receipt_present": receipt is not None,
        "exit_code": receipt.get("exit_code") if receipt else None,
        "timed_out": receipt.get("timed_out", receipt.get("timeout", False)) if receipt else None,
        "started_utc": receipt.get("started_utc") if receipt else None,
        "ended_utc": receipt.get("ended_utc") if receipt else None,
        "wall_seconds": receipt.get("wall_seconds") if receipt else None,
        "prompt_bytes": plan["prompt_bytes"], "tokens": tokens,
        "input_plus_output_tokens": total,
        "completed_turns": audit["turns_completed"] if audit is not None else None,
        "tool_call_count": audit["tool_call_count"] if audit is not None else None,
        "CLI_error_events": audit["errors"] if audit is not None else None,
        "CLI_configuration_diagnostic_count": len(audit["diagnostics"]) if audit is not None else None,
        "raw_usage_records": audit["usage_records"] if audit is not None else None,
        "evidence_sha256": {path.name: digest(path) for path in raw_paths},
        "response_sha256": digest(folder / "response.json") if (folder / "response.json").is_file() else None,
        "context_sha256": plan["context_sha256"], "feedback_sha256": plan["feedback_sha256"]}


def aggregate(rows):
    fields = {name: {"known_sum": sum(row["tokens"][name] for row in rows if row["tokens"][name] is not None),
                     "calls_with_reported_field": sum(row["tokens"][name] is not None for row in rows),
                     "calls_without_reported_field": sum(row["tokens"][name] is None for row in rows)} for name in TOKEN_FIELDS}
    walls = [row["wall_seconds"] for row in rows if row["wall_seconds"] is not None]
    starts = [datetime.fromisoformat(row["started_utc"].replace("Z", "+00:00")) for row in rows if row["started_utc"]]
    ends = [datetime.fromisoformat(row["ended_utc"].replace("Z", "+00:00")) for row in rows if row["ended_utc"]]
    return {"registered_calls": len(rows), "actual_attempts_observed": sum(row["attempt_observed"] for row in rows),
        "candidate_slots_consumed": sum(row["candidate_slots_consumed"] for row in rows),
        "audited_calls": sum(row["valid_candidates"] is not None for row in rows),
        "valid_candidates_on_audited_calls": sum(row["valid_candidates"] for row in rows if row["valid_candidates"] is not None),
        "rejected_slots_on_audited_calls": sum(row["rejected_slots"] for row in rows if row["rejected_slots"] is not None),
        "reported_tool_calls": sum(row["tool_call_count"] for row in rows if row["tool_call_count"] is not None),
        "observed_model_unknown_calls": sum(row["observed_model_label"] == "unknown" for row in rows),
        "tokens": fields, "input_plus_output_known_sum": sum(row["input_plus_output_tokens"] for row in rows if row["input_plus_output_tokens"] is not None),
        "input_plus_output_calls_with_complete_usage": sum(row["input_plus_output_tokens"] is not None for row in rows),
        "sum_per_call_wall_seconds": sum(walls),
        "observed_parallel_makespan_seconds": (max(ends) - min(starts)).total_seconds() if starts and ends else None,
        "time_scope": "per-call wall sums count concurrent calls repeatedly; makespan is min emitted start to max emitted end, not billed compute",
        "currency_cost": None, "currency_cost_reason": "No provider billing receipt or verified per-token tariff is available"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls-root", type=Path, default=ROOT / "llm_calls")
    parser.add_argument("--round", type=int, choices=(1, 2), action="append", help="Omit to index all registered plans")
    parser.add_argument("--completed-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for path in sorted(args.calls_root.glob("*/call_plan.json")):
        plan = read(path)
        require(plan["condition"] in CONDITIONS and plan["round"] in (1, 2) and plan["batch"] in (0, 1), "Unregistered model condition")
        if args.round and plan["round"] not in args.round:
            continue
        if args.completed_only and not (path.parent / "execution_receipt.json").is_file():
            continue
        rows.append(one_call(path.parent))
    require(rows, "No matching registered calls")
    groups = defaultdict(list)
    for row in rows:
        groups[row["arm"]].append(row)
    output = {"version": "real_LLM_generation_cost_index_v1", "calls": rows, "overall": aggregate(rows),
        "by_arm": {arm: aggregate(group) for arm, group in sorted(groups.items())},
        "counting_policy": "Raw CLI token fields preserved. reasoning_output_tokens is a subset of output_tokens, cached_input_tokens a reported input subcount; cache-write is a separate emitted field. None means unavailable, never zero. Input+output never re-adds subcounts.",
        "served_model_policy": "Record actual emitted metadata label only; the requested gpt-6.1-sol label is not evidence of the served model version. No model-authored rationale is mined for identity.",
        "scope": "offline synthesis only; excludes separate offline evidence/fit/full TRAIN/VAL optimizer costs, reported by their own receipts",
        "failed_calls_retained": True, "automatic_retry": False,
        "offline_LLM_calls_actual": sum(row["attempt_observed"] for row in rows),
        "index_generation_model_calls": 0, "index_generation_optimizer_calls": 0}
    freeze_json(args.output, output)
    print(json.dumps({"output": str(args.output), "sha256": digest(args.output), "overall": output["overall"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
