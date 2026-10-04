"""Independent V06 cold-authoring provenance and raw-position audit.

Requires both all-cell completion freezes before parsing any candidate JSON.
No project synthesis, graph, oracle, scorer or repair module is imported.
Static DSL normalization uses an existing independent audit implementation;
no graph evaluation, scalar fit, selection-quality or TEST query is run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_matched_llm_v05 import canonical, normalized_program

ARMS = ("witness", "relations", "objective")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def raw_slots(payload, block, arm):
    """Reconstruct eight positions without executing their expressions."""
    valid = (isinstance(payload, dict)
             and set(payload) == {"version", "block", "arm", "candidates"}
             and payload["version"] == "matched_cold_bank_v06"
             and type(payload["block"]) is int and payload["block"] == block
             and payload["arm"] == arm
             and isinstance(payload["candidates"], list))
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
                program = normalized_program(candidates[slot])
                key = canonical({k: program[k] for k in ("features", "rule")})
                if key in seen:
                    row["status"] = "duplicate_deployment_AST_within_batch"
                else:
                    seen.add(key)
                    row.update(status="static_valid", program=program,
                               program_sha256=canonical(program),
                               deployment_AST_sha256=key)
            except (TypeError, ValueError, KeyError, RecursionError, SyntaxError):
                row["status"] = "invalid_candidate"
        result.append(row)
    return result


def audit(parent, supplement):
    parent, supplement = Path(parent), Path(supplement)
    # These reads precede and gate all candidate parsing.
    original_completion = json.loads((parent / "authoring_completion.json").read_text(encoding="utf-8"))
    added_completion = json.loads((supplement / "authoring_completion.json").read_text(encoding="utf-8"))
    if not (original_completion["all_authoring_completed_before_assessment"]
            and added_completion["all_authoring_completed_before_assessment"]):
        raise ValueError("Both authoring completion freezes must exist before raw-slot parsing")

    checks, errors, bindings = Counter(), [], {}
    sessions, slots = [], []

    def require(condition, kind, context):
        checks[kind] += 1
        if not condition:
            errors.append({"kind": kind, "context": context})

    def bind(path):
        path = Path(path)
        bindings[str(path.relative_to(ROOT)).replace("\\", "/")] = digest(path)
        return digest(path)

    original = json.loads((parent / "protocol.json").read_text(encoding="utf-8"))
    added = json.loads((supplement / "protocol.json").read_text(encoding="utf-8"))
    scope = json.loads((supplement / "ANALYSIS_SCOPE.json").read_text(encoding="utf-8"))
    amendment = json.loads((parent / "transport_amendment.json").read_text(encoding="utf-8"))
    for directory in (parent, supplement):
        for name in ("protocol.json", "freeze_receipt.json", "authoring_completion.json"):
            bind(directory / name)
    bind(parent / "transport_amendment.json")
    bind(supplement / "ANALYSIS_SCOPE.json")
    require(added["parent_protocol_sha256"] == digest(parent / "protocol.json"), "parent_protocol_binding", "supplement")
    require(scope["supplement_protocol_sha256"] == digest(supplement / "protocol.json"), "analysis_scope_binding", "supplement")
    require(added_completion["parent_completion_sha256"] == digest(parent / "authoring_completion.json"), "parent_completion_binding", "supplement")
    require(added_completion["supplement_protocol_sha256"] == digest(supplement / "protocol.json"), "supplement_completion_binding", "supplement")
    require(original_completion["transport_amendment_sha256"] == digest(parent / "transport_amendment.json"), "transport_amendment_binding", "parent")
    require(amendment["original_protocol_sha256"] == digest(parent / "protocol.json"), "original_protocol_transport_binding", "parent")
    require(original["blocks"] == 4 and original["slots_per_block_arm"] == 8
            and original["arms"] == list(ARMS) and added["supplement_blocks"] == [4]
            and added["total_original_slots"] == 120, "fixed_4_plus_1_inventory", "registration")
    require(added["decided_before_any_candidate_assessment"] is True
            and added["candidate_scores_read"] == 0 and added["TEST_queries"] == 0
            and added["no_failed_cell_retry"] is True
            and scope["registered_before_supplement_authoring_and_any_candidate_assessment"] is True,
            "before_assessment_fixed_supplement", "registration")
    require(bind(parent / "training_evidence.json") == original["training_evidence_sha256"], "training_frame_binding", "parent")
    for key, filename in (("assessment", "synthesis_study_v06.py"), ("kernel", "repair_v06.py"),
                          ("typed_library", "graph_features.py"), ("compiled_runtime", "compiled.py")):
        require(bind(ROOT / "cipheur" / filename) == original["source_sha256"][key], "unchanged_original_semantics", filename)
    bind(ROOT / "cipheur/synthesis_extension_v06.py")
    bind(ROOT / "scripts/verify_matched_llm_v05.py")
    bind(ROOT / "scripts/verify_public_alias_v05.py")

    for directory, protocol, completion, blocks in (
            (parent, original, original_completion, range(4)),
            (supplement, added, added_completion, range(4, 5))):
        freeze = json.loads((directory / "freeze_receipt.json").read_text(encoding="utf-8"))
        require(freeze["protocol_sha256"] == digest(directory / "protocol.json"), "freeze_protocol_binding", directory.name)
        for name, expected in protocol["packet_sha256"].items():
            require(bind(directory / name) == expected, "frozen_packet_binding", name)
        expected_names = {f"block_{b}_{a}.json" for b in blocks for a in ARMS}
        require(set(completion["response_sha256"]) == expected_names, "all_registered_sessions_completed", directory.name)
        for block in blocks:
            for arm in ARMS:
                stem = f"block_{block}_{arm}"
                receipt_path = directory / "receipts" / (stem + ".receipt.json")
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                bind(receipt_path)
                response = directory / "responses" / (stem + ".json")
                packet = directory / "packets" / (stem + ".json")
                prompt = directory / "packets" / (stem + ".prompt.md")
                event_path = directory / "receipts" / (stem + ".events.jsonl")
                wrapper = directory / "receipts" / (stem + ".input.txt")
                last_message = directory / "receipts" / (stem + ".last_message.txt")
                for field, path in (("response_sha256", response), ("raw_event_sha256", event_path),
                                    ("raw_stderr_sha256", directory / "receipts" / (stem + ".stderr.txt")),
                                    ("packet_sha256", packet), ("frozen_prompt_sha256", prompt),
                                    ("wrapper_prompt_sha256", wrapper)):
                    require(bind(path) == receipt[field], "session_byte_binding", stem + ":" + field)
                bind(last_message)
                require(response.read_bytes() == last_message.read_bytes()
                        and digest(response) == completion["response_sha256"][stem + ".json"],
                        "exact_unmodified_raw_response", stem)
                require(receipt["cell"] == stem and receipt["block"] == block and receipt["arm"] == arm
                        and receipt["no_retry"] is True and receipt["no_candidate_assessment"] is True,
                        "fixed_session_identity_no_retry", stem)
                require(receipt["requested_configuration"] == added["parent_requested_configuration"], "same_requested_configuration", stem)
                require(prompt.read_text(encoding="utf-8") in wrapper.read_text(encoding="utf-8")
                        and packet.read_text(encoding="utf-8") in wrapper.read_text(encoding="utf-8"),
                        "inline_original_prompt_packet", stem)

                usage, observed, commands, collaborations, other_tools, types = [], [], [], [], [], Counter()
                for line in event_path.read_text(encoding="utf-8").splitlines():
                    event = json.loads(line)
                    types[event.get("type")] += 1
                    if event.get("usage") is not None:
                        usage.append({"event_type": event.get("type"), "usage": event["usage"]})
                    if event.get("model") is not None:
                        observed.append(event["model"])
                    if event.get("type") != "item.completed":
                        continue
                    item = event.get("item", {})
                    if item.get("type") == "command_execution":
                        command = item.get("command", "")
                        denied_precreation = (item.get("exit_code") == -1
                            and item.get("aggregated_output") == "Failed to create unified exec process: helper_unknown_error: apply deny-read ACLs")
                        only_packet = ("Get-Content" in command and "packet.json" in command
                                       and ".." not in command and "python" not in command.lower())
                        commands.append({"command_sha256": sha256(command.encode()).hexdigest(),
                                         "requested_only_packet": only_packet,
                                         "exit_code": item.get("exit_code"), "status": item.get("status"),
                                         "denied_before_process_creation": denied_precreation})
                        require(only_packet and denied_precreation, "recorded_packet_command_denied_precreation", stem)
                    elif item.get("type") == "collab_tool_call":
                        empty = (item.get("tool") == "wait" and not item.get("receiver_thread_ids")
                                 and not item.get("agents_states") and item.get("prompt") is None)
                        collaborations.append({"tool": item.get("tool"), "empty_targets_and_states": empty,
                                               "status": item.get("status")})
                        require(empty, "empty_wait_no_received_external_content", stem)
                    elif item.get("type") not in ("error", "agent_message", "reasoning"):
                        other_tools.append({"type": item.get("type"), "status": item.get("status")})
                        require(False, "other_tool_requires_manual_access_review", stem)
                require((usage or None) == receipt["usage_events"]
                        and (observed or None) == receipt["observed_model"], "replayed_usage_served_model_metadata", stem)
                if directory == parent:
                    require(completion["actual_model_and_usage"][stem] == {
                        k: receipt[k] for k in ("requested_configuration", "observed_model", "usage_events")},
                        "completion_model_usage_binding", stem)
                complete_transport = receipt["exit_code"] == 0 and not receipt["timed_out"] and response.stat().st_size > 0
                require(types["thread.started"] == 1 and types["turn.started"] == 1, "single_cold_thread_turn", stem)
                session = {"cell": stem, "block": block, "arm": arm, "complete_transport": complete_transport,
                    "requested_configuration": receipt["requested_configuration"], "observed_model": observed or None,
                    "usage_events": usage or None, "usage_totals": {k: sum(e["usage"].get(k, 0) for e in usage)
                      for k in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")},
                    "wall_seconds": receipt["wall_seconds"], "exit_code": receipt["exit_code"],
                    "timed_out": receipt["timed_out"], "commands": commands,
                    "collaboration_calls": collaborations, "other_tools": other_tools,
                    "event_types": dict(types), "receipt_sha256": digest(receipt_path),
                    "response_sha256": digest(response), "cli_executable_sha256": receipt["cli_executable_sha256"]}
                sessions.append(session)
                try:
                    payload = json.loads(response.read_text(encoding="utf-8"))
                except (ValueError, UnicodeError):
                    payload = None
                slots.extend(raw_slots(payload, block, arm))

    for arm in ARMS:
        original_packet = json.loads((parent / "packets" / f"block_0_{arm}.json").read_text(encoding="utf-8"))
        added_packet = json.loads((supplement / "packets" / f"block_4_{arm}.json").read_text(encoding="utf-8"))
        expected = deepcopy(original_packet)
        expected["block"] = 4
        expected["output_schema"]["block"] = "integer4"
        require(added_packet == expected, "supplement_only_block_metadata_changes", arm)
        original_prompt = (parent / "packets" / f"block_0_{arm}.prompt.md").read_text(encoding="utf-8")
        require((supplement / "packets" / f"block_4_{arm}.prompt.md").read_text(encoding="utf-8")
                == original_prompt.replace("block 0,", "block 4,"), "supplement_same_prompt_conditions", arm)
    require(len(sessions) == 15 and len(slots) == 120 and len({r["id"] for r in slots}) == 120,
            "all_fifteen_sessions_120_raw_slots", "inventory")
    require(len({s["cli_executable_sha256"] for s in sessions}) == 1, "same_cli_binary", "sessions")
    matched = [b for b in range(5) if all(s["complete_transport"] for s in sessions if s["block"] == b)][:4]
    statuses = {f"block_{b}_{a}": dict(Counter(r["status"] for r in slots if r["block"] == b and r["arm"] == a))
                for b in range(5) for a in ARMS}
    summary = {}
    for label, included in (("all_15_sessions", set(range(5))), ("original_four_blocks", set(range(4))),
                            ("conditional_matched_blocks", set(matched))):
        summary[label] = {}
        for arm in ARMS:
            ss = [s for s in sessions if s["arm"] == arm and s["block"] in included]
            summary[label][arm] = {"sessions": len(ss), "original_slots": 8 * len(ss),
                "complete_transport_sessions": sum(s["complete_transport"] for s in ss),
                "reported_usage_sessions": sum(s["usage_events"] is not None for s in ss),
                "usage_totals": {k: sum(s["usage_totals"][k] for s in ss) for k in ss[0]["usage_totals"]} if ss else {},
                "mean_session_wall_seconds": statistics.fmean(s["wall_seconds"] for s in ss) if ss else None}
    bind(__file__)
    return {"version": "independent_v06_authoring_audit_001", "checks": dict(checks),
        "total_checks": sum(checks.values()), "errors": errors, "metadata": {
            "parent_protocol_sha256": digest(parent / "protocol.json"),
            "parent_completion_sha256": digest(parent / "authoring_completion.json"),
            "supplement_protocol_sha256": digest(supplement / "protocol.json"),
            "supplement_completion_sha256": digest(supplement / "authoring_completion.json"),
            "analysis_scope_sha256": digest(supplement / "ANALYSIS_SCOPE.json"),
            "audit_script_sha256": digest(__file__)},
        "source_and_receipt_bindings": bindings, "sessions": sessions, "summary": summary,
        "matched_transport_complete_blocks": matched, "raw_slot_count": len(slots),
        "raw_slot_status_counts": statuses, "raw_slot_static_inventory": slots,
        "scope": ["Both completion freezes are required before raw candidate parsing.",
            "Static syntax/type normalization only; no TRAIN graph or rule-fit evaluation, candidate selection or TEST query.",
            "Whole-block transport inclusion is independent of candidate JSON/DSL and conditional on successful provider transport.",
            "Original intention-to-author failures remain present; exactly one fixed supplementary block, no retries or model switches.",
            "Requested configuration is observed; served-model identity is unknown where events omit it.",
            "Cached input tokens are a subset of reported input; reported usage is not a count of backend calls or a monetary-cost estimate.",
            "Command attempts denied before process creation did not read packet or external data; empty-target waits returned no external content.",
            "Model/slot settings match; actual token usage, latency and backend compute are not matched."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", default="experiments/discovery/v06_authoring_001")
    parser.add_argument("--supplement", default="experiments/discovery/v06_authoring_supplement_001")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = audit(ROOT / args.parent, ROOT / args.supplement)
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": report["total_checks"], "errors": len(report["errors"]),
                      "matched_blocks": report["matched_transport_complete_blocks"], "slots": report["raw_slot_count"]}))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
