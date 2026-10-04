"""Append a manual resolution of one failed permitted packet-read tool.

The first authoring audit and all original evidence remain untouched. This
does not assess graph interfaces, rule fit, repair quality or TEST behavior.
The project parser is used only as a static normalization crosscheck against
the independent parser; no program is evaluated and no candidate is edited.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_authoring_v06 import audit, raw_slots
from scripts.verify_matched_llm_v05 import canonical

EXPECTED_EVENT_SHA = "42cf860e46f1771b8fee2b737e39205744e8688955085f9668a6d5e5f38cc2ce"
EXPECTED_FIRST_AUDIT_SHA = "1a815f0313666edd2a0c21d8e7214ae5b5d4fd9479ffe2f91cb2710b679aca95"
PARENT = ROOT / "experiments/discovery/v06_authoring_001"
SUPPLEMENT = ROOT / "experiments/discovery/v06_authoring_supplement_001"
FIRST = ROOT / "experiments/analysis/v06/authoring_audit_v06_001.json"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def project_static_slots(payload, block, arm):
    """Original typed parser reference only; no graph or score method calls."""
    from cipheur.graph_features import FeatureRuleProgram
    valid = (isinstance(payload, dict) and set(payload) == {"version", "block", "arm", "candidates"}
             and payload["version"] == "matched_cold_bank_v06"
             and type(payload["block"]) is int and payload["block"] == block
             and payload["arm"] == arm and isinstance(payload["candidates"], list))
    candidates = payload["candidates"] if valid else []
    bad = not valid or len(candidates) > 8
    seen, result = set(), []
    for slot in range(8):
        row = {"id": f"block_{block}_{arm}:{slot}", "block": block,
               "arm": arm, "slot": slot, "program": None}
        if bad:
            row["status"] = "invalid_response_schema"
        elif slot >= len(candidates):
            row["status"] = "missing_slot"
        else:
            try:
                p = FeatureRuleProgram.from_dict(candidates[slot]).to_dict()
                key = canonical({k: p[k] for k in ("features", "rule")})
                if key in seen:
                    row["status"] = "duplicate_deployment_AST_within_batch"
                else:
                    seen.add(key)
                    row.update(status="static_valid", program=p,
                               program_sha256=canonical(p), deployment_AST_sha256=key)
            except (TypeError, ValueError, KeyError, RecursionError):
                row["status"] = "invalid_candidate"
        result.append(row)
    return result


def review():
    first = json.loads(FIRST.read_bytes())
    repeated = audit(PARENT, SUPPLEMENT)
    checks, errors = Counter(), []

    def require(condition, kind, context):
        checks[kind] += 1
        if not condition:
            errors.append({"kind": kind, "context": context})

    require(digest(FIRST) == EXPECTED_FIRST_AUDIT_SHA, "immutable_first_audit_hash", "first")
    expected_flag = {"kind": "other_tool_requires_manual_access_review", "context": "block_4_witness"}
    require(first["errors"] == [expected_flag] and repeated["errors"] == [expected_flag], "only_expected_manual_review_flag", "first_and_replay")
    require(first == repeated, "independent_read_only_audit_replay_identity", "all265_checks_and_inputs")
    event_path = SUPPLEMENT / "receipts/block_4_witness.events.jsonl"
    require(digest(event_path) == EXPECTED_EVENT_SHA, "exact_manual_review_event_hash", "block_4_witness")
    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    items = [e["item"] for e in events if e.get("type") == "item.completed"
             and e.get("item", {}).get("type") == "mcp_tool_call"]
    require(len(items) == 1, "single_unrecognized_completed_tool", "block_4_witness")
    item = items[0] if len(items) == 1 else {}
    expected_code = ("var frozenPacketText = await (await import('node:fs/promises')).readFile("
        "'E:/01-Joycecyq/2026-AAMAS/第二篇/.research/v06_cli_workspaces/block_4_witness/packet.json',"
        "'utf8'); nodeRepl.write(frozenPacketText);")
    require(item.get("server") == "node_repl" and item.get("tool") == "js"
            and item.get("arguments", {}).get("code") == expected_code,
            "only_permitted_session_packet_requested", "item_4")
    require(item.get("status") == "failed" and item.get("id") == "item_4", "tool_failed", "item_4")
    content = item.get("result", {}).get("content", [])
    text = content[0].get("text", "") if len(content) == 1 else ""
    require(len(content) == 1 and content[0].get("type") == "text"
            and text.startswith("node_repl kernel exited unexpectedly\n\nnode_repl diagnostics: "),
            "diagnostics_only_no_file_contents", "item_4")
    marker = "node_repl diagnostics: "
    diagnostics = json.loads(text.split(marker, 1)[1]) if marker in text else {}
    require(diagnostics.get("kernel_status") == "exited(code=1)"
            and diagnostics.get("kernel_stderr_tail") == "windows sandbox failed: helper_unknown_error: apply deny-read ACLs"
            and diagnostics.get("reason") == "stdout_eof" and diagnostics.get("stream_error") is None,
            "kernel_sandbox_failed_no_successful_access", "item_4")

    all_slots, per_cell = [], {}
    for block in range(5):
        directory = PARENT if block < 4 else SUPPLEMENT
        for arm in ("witness", "relations", "objective"):
            name = f"block_{block}_{arm}.json"
            try:
                payload = json.loads((directory / "responses" / name).read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                payload = None
            independent = raw_slots(payload, block, arm)
            original_parser = project_static_slots(payload, block, arm)
            for a, b in zip(independent, original_parser):
                require(a == b, "independent_project_static_normalization_identity", a["id"])
                if a["program"] is not None:
                    require(canonical(a["program"]) == a["program_sha256"], "canonical_program_binding", a["id"])
                    require(canonical({k: a["program"][k] for k in ("features", "rule")}) == a["deployment_AST_sha256"],
                            "canonical_deployment_AST_binding", a["id"])
            all_slots.extend(independent)
            per_cell[name[:-5]] = dict(Counter(r["status"] for r in independent))
    require(all_slots == first["raw_slot_static_inventory"], "all120_raw_positions_unchanged", "slots")
    require(len(all_slots) == 120 and len({r["id"] for r in all_slots}) == 120, "all120_unique_original_positions", "slots")
    require(first["matched_transport_complete_blocks"] == [1, 2, 3, 4], "fixed_first_four_transport_complete_blocks", "blocks")
    require([s["cell"] for s in first["sessions"] if not s["complete_transport"]] == ["block_0_relations"],
            "only_original_capacity_transport_failure", "sessions")

    # Absence is recorded narrowly: registered candidate-assessment artifacts,
    # plus all available author-tool events, not an unverifiable universal claim.
    forbidden_studies = list((ROOT / "experiments/runs/v06").glob("synthesis_train*"))
    output = ROOT / "output/synthesis_train_server_v06_001"
    require(not forbidden_studies and not output.exists(), "no_registered_candidate_assessment_artifact_before_review", "filesystem")
    completion = json.loads((SUPPLEMENT / "authoring_completion.json").read_bytes())
    reviewed_at = datetime.now(timezone.utc).isoformat()
    report = dict(first)
    report["version"] = "independent_v06_authoring_reviewed_audit_001"
    report["predecessor"] = {"path": FIRST.relative_to(ROOT).as_posix(), "sha256": digest(FIRST),
                              "checks": first["total_checks"], "flags_retained": first["errors"]}
    report["errors"] = errors
    report["error_count"] = len(errors)
    report["manual_review_checks"] = dict(checks)
    report["total_checks"] = first["total_checks"] + sum(checks.values())
    report["manual_resolutions"] = [{"original_flag": expected_flag, "event_sha256": EXPECTED_EVENT_SHA,
        "completed_item_id": "item_4", "completed_event_line": 9,
        "requested_path_scope": "Only permitted packet.json in the same block_4_witness isolated session",
        "tool_status": "failed", "kernel_status": diagnostics.get("kernel_status"),
        "sandbox_failure": diagnostics.get("kernel_stderr_tail"), "returned_data": "diagnostics only, no file contents",
        "successful_external_file_result_browser_or_outcome_access": False,
        "resolution": "No contamination: attempted permitted packet read failed before kernel/file access; retained as additional unsuccessful tool work."}]
    report["reviewed_at_utc"] = reviewed_at
    report["last_authoring_completion_utc"] = completion["completed_utc"]
    report["raw_slot_status_counts"] = per_cell
    report["metadata"] = {**first["metadata"], "review_script_sha256": digest(__file__),
        "initial_audit_sha256": digest(FIRST), "resolved_event_sha256": EXPECTED_EVENT_SHA,
        "original_typed_parser_sha256": digest(ROOT / "cipheur/graph_features.py")}
    report["source_and_receipt_bindings"] = {**first["source_and_receipt_bindings"],
        __file__.replace(str(ROOT) + "\\", "").replace("\\", "/"): digest(__file__),
        FIRST.relative_to(ROOT).as_posix(): digest(FIRST)}
    report["scope"] = first["scope"] + [
        "The first audit's sole unrecognized node_repl type flag is preserved and resolved against exact event bytes, not erased.",
        "All120 independent static normalized positions match the frozen original typed-parser normalization; no graph, score, quotient or repair method is called.",
        "Authors received full frozen packet and prompt bytes inline in stdin despite failed duplicate file-read attempts.",
        "No registered candidate-assessment output existed at this review; available author events contain no candidate or TEST evaluation. Earlier Degree feedback/evidence acquisition are distinct authorized TRAIN studies.",
        "Block4 witness's additional unsuccessful kernel attempt and block2 objective's empty waits remain cost receipts; actual inference compute is not matched."]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = ROOT / args.out
    if output.exists():
        raise ValueError("Preserve the first reviewed report")
    report = review()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": report["total_checks"], "errors": report["error_count"],
        "matched_blocks": report["matched_transport_complete_blocks"], "raw_slots": report["raw_slot_count"],
        "reviewed_report_sha256": digest(output)}))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
