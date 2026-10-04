"""Independent provenance audit for all fifteen frozen V06 R2 author sessions.

Registration-only mode never opens any R2 response, session receipt or event.
Full audit refuses to read those files until the all-fifteen completion freeze
exists and matches the pinned original protocol and runtime binding. Static
normalization is independent of the R2 loader; no candidate is evaluated.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_authoring_v06 import raw_slots
from scripts.verify_matched_llm_v05 import canonical

DEFAULT = "experiments/discovery/v06_refinement_draft_003"
PROTO_SHA = "fd6214a89e15a59c6ec75e6348872c63b508a8b667076f03f0c8f933fcbd694f"
RUNTIME_SHA = "829b79c7e6b34d652dd2334b565027e291dd5ec7f4cd0bc3c0b8151433104d78"
ARMS = ("witness", "relations", "objective")
CLI = Path("C:/Users/JIA/AppData/Local/OpenAI/Codex/bin/de8a38d2100ae498/codex.exe")


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Checks:
    def __init__(self):
        self.checks, self.errors, self.bindings = Counter(), [], {}

    def require(self, ok, kind, context=""):
        self.checks[kind] += 1
        if not ok:
            self.errors.append({"kind": kind, "context": context})

    def bind(self, path):
        path = Path(path)
        value = digest(path)
        try:
            name = path.relative_to(ROOT).as_posix()
        except ValueError:
            name = str(path).replace("\\", "/")
        self.bindings[name] = value
        return value


def registration(study, checks):
    """Only frozen inputs; no session output filename is opened here."""
    c = checks
    c.require(c.bind(study / "protocol.json") == PROTO_SHA, "pinned_R2_protocol")
    c.require(c.bind(study / "transport_runtime_binding.json") == RUNTIME_SHA, "pinned_R2_runtime_binding")
    p, r, f = (load(study / n) for n in ("protocol.json", "transport_runtime_binding.json", "freeze_receipt.json"))
    c.bind(study / "freeze_receipt.json")
    c.require(p["version"] == "matched_refinement_round_v06_002"
        and p["status"] == "FROZEN_BEFORE_ROUND2_AUTHORING"
        and p["registered_before_round2_authoring"] and not p["test_accessed"]
        and p["blocks"] == 5 and p["arms"] == list(ARMS)
        and p["slots_per_block_arm"] == 8 and p["requested_slots"] == 120
        and p["no_adaptive_supplement"] and p["no_retry_or_replacement"], "fixed_five_whole_blocks_120_rawpositions")
    c.require(f["before_round2_authoring"] and f["protocol_sha256"] == PROTO_SHA
        and f["packet_sha256"] == p["packet_sha256"]
        and f["training_evidence_sha256"] == p["training_evidence_sha256"], "pre_generation_freeze_protocol_binding")
    c.require(r["before_any_R2_authoring_or_candidate_assessment"] and r["workers"] == 2
        and r["timeout_seconds"] == 1800 and r["no_retry"]
        and r["workspace_namespace"] == ".research/v06_refinement_cli_workspaces/{study_name}/{block_arm}"
        and r["served_model_not_inferred_from_requested_settings"], "fresh_runtime_namespace_declared_scope")
    for key, path in (("authoring_transport_sha256", ROOT / "scripts/author_refinement_cli_v06.py"),
        ("transport_helper_sha256", ROOT / "scripts/author_matched_cli_v06.py"),
        ("R2_assessment_sha256", ROOT / "cipheur/refinement_study_v06.py"),
        ("preparation_receipt_sha256", study / "preparation_receipt.json"),
        ("draft_protocol_sha256", study / "draft_protocol.json"),
        ("selection_plan_sha256", study / "selection_plan.json"),
        ("independent_packet_audit_sha256", ROOT / "experiments/analysis/v06/refinement_packet_audit_v06_002.json")):
        c.require(c.bind(path) == r[key], "frozen_runtime_dependency", key)
    if CLI.is_file():
        c.require(c.bind(CLI) == r["cli_executable_sha256"], "registered_native_CLI_binary")
    c.require(p["source_sha256"]["authoring_transport"] == r["authoring_transport_sha256"], "protocol_runtime_same_driver")
    c.require(c.bind(study / "training_evidence.json") == p["training_evidence_sha256"], "unchanged_TRAIN_frame")
    c.require(c.bind(study / "selection_plan.json") == p["selection_plan_sha256"]
        == f["selection_plan_sha256"] == r["selection_plan_sha256"], "uniform_roles_unchanged")
    for name, expected in p["packet_sha256"].items():
        c.require(c.bind(study / name) == expected, "frozen_packet_and_prompt", name)
    for name, expected in p["all_unchanged_assessment_sources"].items():
        c.require(c.bind(ROOT / "cipheur" / name) == expected, "original_assessment_semantics_unchanged", name)
    c.bind(ROOT / "scripts/verify_authoring_v06.py")
    c.bind(ROOT / "scripts/verify_matched_llm_v05.py")
    c.bind(__file__)
    return p, r, f


def report_registration(study):
    c = Checks()
    p, r, f = registration(study, c)
    return {"version": "independent_R2_registration_only_audit_v06_002",
        "checks": dict(c.checks), "total_checks": sum(c.checks.values()),
        "errors": c.errors, "error_count": len(c.errors),
        "metadata": {"protocol_sha256": PROTO_SHA, "runtime_binding_sha256": RUNTIME_SHA,
            "audit_script_sha256": digest(__file__), "freeze_sha256": digest(study / "freeze_receipt.json")},
        "source_and_receipt_bindings": c.bindings,
        "scope": ["Only pre-generation protocol/runtime/source/packet inputs were opened.",
            "No R2 response, session receipt, candidate content or author event was read or normalized.",
            "No model, conditional oracle, graph interface or scheduling evaluator was called."]}


def command_scope(command, allowed):
    """Conservative whitelist of a single Get-Content packet read."""
    normalized = command.replace("\\", "/").lower()
    if "get-content" not in normalized or "packet.json" not in normalized:
        return False
    forbidden = (";", "&", "|", "`", "$", "..", "\n", "\r", "<", ">", "?", "*",
                 "invoke-", "python", "curl", "wget", "http", "set-content", "out-file")
    if any(word in normalized for word in forbidden):
        return False
    # Absolute packet requests must point at this session's own packet.
    paths = re.findall(r"(?:[a-z]:/[^\r\n\"']*packet\.json)", normalized)
    if paths and any(p != allowed.replace("\\", "/").lower() for p in paths):
        return False
    # Demand one packet argument, not merely a command mentioning packet.json.
    # Conservative unknown forms are flagged for manual review after freezing.
    tail = normalized[normalized.index("get-content"):]
    packet = "(?:packet\\.json|" + re.escape(allowed.replace("\\", "/").lower()) + ")"
    options = r"(?:(?:-raw|-literalpath|-path)\s+)*"
    pattern = r"get-content\s+" + options + r"[\"']?" + packet + r"[\"']?\s*(?:-raw)?\s*[\"']?"
    return re.fullmatch(pattern, tail) is not None


def review_tool(item, allowed):
    """Return a narrow access disposition, never count failed ACL as access."""
    kind = item.get("type")
    if kind == "command_execution":
        command = item.get("command", "")
        denied = (item.get("exit_code") == -1 and item.get("aggregated_output") ==
                  "Failed to create unified exec process: helper_unknown_error: apply deny-read ACLs")
        permitted = command_scope(command, allowed)
        if denied:
            disposition = "denied_before_process_creation_no_access"
            resolved = True
        elif permitted:
            disposition = "permitted_same_packet_read"
            resolved = True
        else:
            disposition = "command_requires_manual_access_review"
            resolved = False
        return {"type": kind, "id": item.get("id"), "status": item.get("status"),
            "command_sha256": sha256(command.encode()).hexdigest(), "exit_code": item.get("exit_code"),
            "requested_only_same_packet": permitted, "denied_before_process_creation": denied,
            "disposition": disposition, "resolved_no_external_access": resolved,
            "failed_forbidden_attempt": denied and not permitted}
    if kind == "collab_tool_call":
        empty = (item.get("tool") == "wait" and not item.get("receiver_thread_ids")
                 and not item.get("agents_states") and item.get("prompt") is None)
        return {"type": kind, "id": item.get("id"), "status": item.get("status"), "tool": item.get("tool"),
            "disposition": "empty_wait_no_external_content" if empty else "collaboration_requires_manual_access_review",
            "resolved_no_external_access": empty}
    if kind == "mcp_tool_call":
        code = item.get("arguments", {}).get("code", "")
        content = (item.get("result") or {}).get("content", [])
        text = content[0].get("text", "") if len(content) == 1 and content[0].get("type") == "text" else ""
        marker = "node_repl diagnostics: "
        diagnostics = {}
        if marker in text:
            try:
                diagnostics = json.loads(text.split(marker, 1)[1])
            except ValueError:
                pass
        paths = re.findall(r"(?:[A-Za-z]:[/\\][^\r\n\"']*packet\.json)", code)
        only_packet = bool(paths) and all(p.replace("\\", "/").lower() == allowed.lower() for p in paths)
        failed_kernel = (item.get("server") == "node_repl" and item.get("tool") == "js"
            and item.get("status") == "failed" and text.startswith("node_repl kernel exited unexpectedly\n\n" + marker)
            and diagnostics.get("kernel_status") == "exited(code=1)"
            and diagnostics.get("kernel_stderr_tail") == "windows sandbox failed: helper_unknown_error: apply deny-read ACLs"
            and diagnostics.get("reason") == "stdout_eof" and diagnostics.get("stream_error") is None)
        return {"type": kind, "id": item.get("id"), "status": item.get("status"),
            "server": item.get("server"), "tool": item.get("tool"), "arguments_sha256": canonical(item.get("arguments", {})),
            "requested_same_packet_path": only_packet, "failed_kernel_before_file_access": failed_kernel,
            "disposition": "failed_ACL_kernel_diagnostics_only_no_access" if failed_kernel else "MCP_requires_manual_access_review",
            "resolved_no_external_access": failed_kernel,
            "failed_forbidden_attempt": failed_kernel and not only_packet}
    return {"type": kind, "id": item.get("id"), "status": item.get("status"),
        "disposition": "unknown_tool_requires_manual_access_review", "resolved_no_external_access": False}


def audit(study):
    # Hard gate precedes EVERY R2 session/response/event read and normalization.
    completion_path = study / "authoring_completion.json"
    if not completion_path.is_file():
        raise ValueError("All fifteen R2 authoring sessions must finish and freeze before this audit reads any output")
    complete = load(completion_path)
    names = {f"block_{b}_{a}.json" for b in range(5) for a in ARMS}
    if not (complete.get("version") == "R2_matched_cli_authoring_completion_v06"
        and complete.get("protocol_sha256") == PROTO_SHA
        and complete.get("transport_runtime_binding_sha256") == RUNTIME_SHA
        and complete.get("all15_R2_requests_frozen_before_assessment") is True
        and complete.get("same_requested_model_and_settings_all_cells") is True
        and complete.get("no_assessment_or_retry") is True and complete.get("no_TEST_access") is True
        and set(complete.get("response_sha256", {})) == names):
        raise ValueError("The all-fifteen completion freeze is incomplete or changes registered protocol/runtime")
    c = Checks()
    p, runtime, freeze = registration(study, c)
    c.bind(completion_path)
    freeze_time = datetime.fromisoformat(freeze["utc"])
    completed_time = datetime.fromisoformat(complete["completed_utc"])
    c.require(freeze_time < completed_time, "authoring_completion_after_pre_generation_freeze")
    c.require(set(complete["receipt_paths"]) == {n[:-5] for n in names}, "all_fifteen_receipt_identities")
    sessions, slots, actual_external, warnings = [], [], [], []
    thread_ids = []
    for b in range(5):
        for arm in ARMS:
            stem = f"block_{b}_{arm}"
            receipt_path = study / "receipts" / (stem + ".receipt.json")
            receipt = load(receipt_path)
            c.bind(receipt_path)
            c.require(complete["receipt_paths"][stem] == "receipts/" + stem + ".receipt.json", "completion_exact_receipt_path", stem)
            response = study / "responses" / (stem + ".json")
            event_path = study / "receipts" / (stem + ".events.jsonl")
            paths = {"response_sha256": response, "packet_sha256": study / "packets" / (stem + ".json"),
                "frozen_prompt_sha256": study / "packets" / (stem + ".prompt.md"),
                "wrapper_prompt_sha256": study / "receipts" / (stem + ".input.txt"),
                "raw_event_sha256": event_path, "raw_stderr_sha256": study / "receipts" / (stem + ".stderr.txt")}
            for field, path in paths.items():
                c.require(c.bind(path) == receipt[field], "session_original_bytes_binding", stem + "/" + field)
            last = study / "receipts" / (stem + ".last_message.txt")
            c.bind(last)
            c.require(response.read_bytes() == last.read_bytes()
                and digest(response) == complete["response_sha256"][stem + ".json"], "exact_unmodified_last_raw_response", stem)
            c.require(receipt["cell"] == stem and receipt["block"] == b and receipt["arm"] == arm
                and receipt["no_retry"] and receipt["no_candidate_assessment"]
                and receipt["study_kind"] == "warm_start_targeted_TRAIN_refinement", "fixed_session_identity_no_controller_retry", stem)
            c.require(receipt["requested_configuration"] == runtime["requested_configuration"]
                and receipt["cli_executable_sha256"] == runtime["cli_executable_sha256"], "same_requested_model_settings_CLI", stem)
            expected_flags = ["exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
                "--json", "--cd", "ISOLATED_R2_PACKET_DIRECTORY", "--output-last-message", "CONTROLLER_RECEIPT", "-"]
            c.require(receipt["command_flags"] == expected_flags, "fresh_ephemeral_readonly_no_model_override", stem)
            wall = receipt["wall_seconds"]
            c.require(type(wall) in (int, float) and math.isfinite(wall) and wall >= 0
                and type(receipt["exit_code"]) is int and type(receipt["timed_out"]) is bool,
                "finite_original_wall_exit_timeout_receipt", stem)
            wrapper = paths["wrapper_prompt_sha256"].read_text(encoding="utf-8")
            c.require(paths["frozen_prompt_sha256"].read_text(encoding="utf-8") in wrapper
                and paths["packet_sha256"].read_text(encoding="utf-8") in wrapper,
                "full_original_packet_prompt_inline_in_stdin", stem)
            allowed = str(ROOT / ".research/v06_refinement_cli_workspaces" / study.name / stem / "packet.json").replace("\\", "/")
            copied_packet = Path(allowed)
            if copied_packet.is_file():
                c.require(c.bind(copied_packet) == digest(paths["packet_sha256"]), "isolated_session_only_packet_original_bytes", stem)
                # Inventory is local provenance only, not author-request output.
                inventory = sorted(q.name for q in copied_packet.parent.iterdir())
                c.require(inventory == ["packet.json"], "no_shared_candidate_output_or_other_workspace_files", stem)
            usage, observed, tools, types, errors = [], [], [], Counter(), []
            event_lines = event_path.read_text(encoding="utf-8").splitlines()
            completed_items = {}
            for i, line in enumerate(event_lines, 1):
                try:
                    event = json.loads(line)
                except ValueError:
                    c.require(False, "valid_raw_event_JSON", stem + "/" + str(i))
                    continue
                types[event.get("type")] += 1
                if event.get("usage") is not None:
                    usage.append({"event_type": event.get("type"), "usage": event["usage"]})
                if event.get("model") is not None:
                    observed.append(event["model"])
                if event.get("type") == "thread.started":
                    thread_ids.append(event.get("thread_id"))
                if event.get("type") in ("error", "turn.failed"):
                    errors.append({"event_line": i, "type": event.get("type"), "event_sha256": canonical(event),
                        "error": event.get("message", event.get("error"))})
                item = event.get("item") or {}
                if event.get("type") == "item.completed":
                    if item.get("id") in completed_items:
                        c.require(False, "unique_completed_tool_item", stem + "/" + str(item.get("id")))
                    completed_items[item.get("id")] = item
                    if item.get("type") in ("error", "agent_message", "reasoning"):
                        continue
                    reviewed = review_tool(item, allowed)
                    reviewed.update(event_line=i, event_sha256=canonical(event), raw_event_sha256=digest(event_path))
                    tools.append(reviewed)
                    if not reviewed["resolved_no_external_access"]:
                        c.require(False, "tool_requires_manual_successful_access_review", stem + "/" + str(item.get("id")))
                        actual_external.append({"cell": stem, "item_id": item.get("id"),
                            "disposition": reviewed["disposition"], "status": item.get("status"), "confirmed": False})
                    if reviewed.get("failed_forbidden_attempt"):
                        warnings.append({"cell": stem, "item_id": item.get("id"),
                            "kind": "forbidden_target_attempt_denied_before_access", "actual_access": False})
            # An unfinished tool item cannot be presumed harmless on timeout.
            starts = [json.loads(l) for l in event_lines if l.strip()]
            for event in starts:
                item = event.get("item") or {}
                if event.get("type") in ("item.started", "item.updated") and item.get("type") not in ("agent_message", "reasoning"):
                    c.require(item.get("id") in completed_items, "all_tool_starts_have_access_disposition", stem + "/" + str(item.get("id")))
            c.require((usage or None) == receipt["usage_events"] and (observed or None) == receipt["observed_model"],
                "original_event_usage_servedmodel_replayed", stem)
            for u in usage:
                v = u["usage"]
                c.require(all(type(n) is int and n >= 0 for n in v.values()), "reported_usage_nonnegative_integer", stem)
                if "input_tokens" in v and "cached_input_tokens" in v:
                    c.require(v["cached_input_tokens"] <= v["input_tokens"], "cached_input_subset_never_added_twice", stem)
            c.require(types["thread.started"] == 1 and types["turn.started"] == 1,
                "one_fresh_thread_and_authoring_turn", stem)
            complete_transport = receipt["exit_code"] == 0 and not receipt["timed_out"] and response.stat().st_size > 0
            try:
                payload = json.loads(response.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                payload = None
            original_slots = raw_slots(payload, b, arm)
            for row in original_slots:
                if row["program"] is not None:
                    c.require(canonical(row["program"]) == row["program_sha256"]
                        and canonical({k: row["program"][k] for k in ("features", "rule")}) == row["deployment_AST_sha256"],
                        "independent_static_program_AST_identity", row["id"])
            slots.extend(original_slots)
            sessions.append({"cell": stem, "block": b, "arm": arm,
                "complete_transport": complete_transport, "exit_code": receipt["exit_code"], "timed_out": receipt["timed_out"],
                "wall_seconds": wall, "requested_configuration": receipt["requested_configuration"],
                "observed_model": observed or None, "usage_events": usage or None,
                "reported_usage_totals": {k: sum(u["usage"].get(k, 0) for u in usage) for k in
                    ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")},
                "usage_known": bool(usage), "event_types": dict(types), "tool_history_dispositions": tools,
                "provider_errors": errors, "response_sha256": digest(response), "raw_event_sha256": digest(event_path),
                "receipt_sha256": digest(receipt_path), "response_bytes": response.stat().st_size})
    c.require(len(sessions) == 15 and len(slots) == 120 and len({s["id"] for s in slots}) == 120,
        "all_fifteen_requests_all120_static_positions")
    c.require(len(thread_ids) == len(set(thread_ids)) == 15 and None not in thread_ids,
        "all_fifteen_distinct_fresh_thread_IDs")
    failed = [s["cell"] for s in sessions if s["exit_code"] or s["timed_out"]]
    c.require(set(failed) == set(complete["failed_transport_cells"]), "all_transport_failures_retained_in_completion")
    matched = [b for b in range(5) if all(s["complete_transport"] for s in sessions if s["block"] == b)][:4]
    summaries = {}
    for label, included in (("all_five_fixed_blocks", set(range(5))), ("conditional_matched_blocks", set(matched))):
        summaries[label] = {}
        for arm in ARMS:
            ss = [s for s in sessions if s["arm"] == arm and s["block"] in included]
            summaries[label][arm] = {"sessions": len(ss), "original_slots": len(ss) * 8,
                "transport_complete": sum(s["complete_transport"] for s in ss),
                "reported_usage_sessions": sum(s["usage_known"] for s in ss),
                "unknown_usage_sessions": sum(not s["usage_known"] for s in ss),
                "reported_usage_totals": {k: sum(s["reported_usage_totals"][k] for s in ss) for k in
                    ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")},
                "mean_original_session_wall_seconds": statistics.fmean(s["wall_seconds"] for s in ss) if ss else None}
    return {"version": "independent_R2_authoring_audit_v06_002", "total_checks": sum(c.checks.values()),
        "checks": dict(c.checks), "errors": c.errors, "error_count": len(c.errors),
        "metadata": {"completion_sha256": digest(completion_path), "protocol_sha256": PROTO_SHA,
            "runtime_binding_sha256": RUNTIME_SHA, "audit_script_sha256": digest(__file__),
            "independent_static_parser_sha256": digest(ROOT / "scripts/verify_authoring_v06.py"),
            "last_authoring_completion_utc": complete["completed_utc"],
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat()},
        "source_and_receipt_bindings": c.bindings, "sessions": sessions, "summary": summaries,
        "matched_transport_complete_blocks": matched, "raw_slot_count": len(slots),
        "raw_slot_static_inventory": slots,
        "raw_slot_status_counts": {f"block_{b}_{a}": dict(Counter(s["status"] for s in slots if s["block"] == b and s["arm"] == a))
            for b in range(5) for a in ARMS},
        "tool_access_requires_manual_review": actual_external, "warnings": warnings,
        "scope": ["All fifteen completion freeze and fixed protocol/runtime are checked before session/tool/response reads.",
            "Static normalization only: no scalar feature evaluation, quotient/gate, schedule quality, candidate selection or TEST query is run.",
            "First-four whole transport-complete cohort is computed independently of raw candidate contents and remains transport-conditional.",
            "Five whole blocks were fixed in advance; all120positions, missing/invalid/duplicate slots and capacity/time failures remain retained.",
            "Unrecognized or successful external tool access requires manual review; failed pre-process/kernel ACL attempts do not count as data access.",
            "Unknown served model remains null; requested setting agreement does not prove served model identity.",
            "Reported cached input is a subset of input; absent usage is unknown rather than measured zero, and reported usage is not backend-call count or cost.",
            "Original wall receipts are bound, not remeasured; per-session precise UTC start/end are not emitted by this driver.",
            "Slots/settings match; prompt length, actual tokens, latency and backend compute are not equalized.",
            "R2 is conditional warm repair of an R1-selected seed; R1's9/12 failed barrier and identical TRAIN quality remain unchanged."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", default=DEFAULT)
    parser.add_argument("--out", required=True)
    parser.add_argument("--registration-only", action="store_true")
    args = parser.parse_args()
    output = ROOT / args.out
    if output.exists():
        raise ValueError("Never replace an independent R2 audit; use a separate appended review for later flags")
    result = report_registration(ROOT / args.study) if args.registration_only else audit(ROOT / args.study)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": result["total_checks"], "errors": result["error_count"],
        "registration_only": args.registration_only, "matched_blocks": result.get("matched_transport_complete_blocks"),
        "raw_slots": result.get("raw_slot_count"), "audit_sha256": digest(output)}), flush=True)
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
