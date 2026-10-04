"""Independent frozen EoH provenance/population audit, never an assessor.

Registration-only mode reads static files. Full mode requires the final
all32-position selection freeze before opening author responses/fitness.
No production module, loader, population manager or model is imported.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_matched_llm_v05 import canonical, normalized_program
from scripts.verify_public_alias_v05 import graph_digest
from scripts.verify_refinement_authoring_v06 import review_tool

STUDY = ROOT / "experiments/discovery/v06_published_eoh_001"
PROTO_SHA = "7885a103ffd550ae8e50b95367220d3967e62d73eb17e5a6dfd31493d0a9e283"
FREEZE_SHA = "2a39ca3712ded168e176d971623db6439bc6d7ceee1502cf089239f686863c13"
RELEASE_SHA = "6f3a7059c92bebbf2905cdf51a9eda681a73d8990f3f254fc567c3b461ad9c35"
PLAN_SHA = "be8262cac7e7effcbf2aaf6289ec470331175095bb31586fae1c38fe698e3533"
SEED_SHA = "83dc9ce30a4d7ff8c529c36d33b3aa4d47276480a88da3ca4bc6a48b391c156c"
TOOL_AUDITOR_SHA = "e1969e06145d8b893da8a227b99aa9a9774647ccba64722b44477297e0ea6bec"
OPS = ("i1", "i1", "e1", "e2", "m1", "m2", "m3", "e2")
FORBIDDEN = {"labels", "queries", "strict_fit", "strict_passed", "quotient", "strict_checks",
    "witness", "equality_joins", "gate", "eligible", "base_alias_by_side", "lower_exact", "upper_exact",
    "cancelled_components", "certificate"}
FEEDBACK_KEYS = {"id", "run", "slot", "operator", "program_sha256", "quality_covered", "status",
    "macro_quality_exact", "macro_work_exact", "family_quality", "family_work", "assigned_states",
    "completed_feasible_states", "error_count", "unexecuted_states"}
INSTRUCTION = {
    "i1": "Describe a new heuristic thought in one sentence and implement it as the typed program; the shared warm seed supplies the starting context.",
    "e1": "Explore a heuristic with a form as different as possible from the selected parent thoughts/programs.",
    "e2": "Identify the parents' common backbone, then explore a different heuristic motivated by that backbone and describe its thought.",
    "m1": "Modify the selected parent thought/program to seek better complete-schedule performance.",
    "m2": "Identify and change numerical parameters of the parent score/feature expressions while retaining the algorithmic structure.",
    "m3": "Analyze the parent's redundant components and simplify its typed feature/rule implementation for efficiency and generalization.",
}


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for b in iter(lambda: stream.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


class Checks:
    def __init__(self):
        self.counts, self.errors, self.bindings = Counter(), [], {}

    def require(self, ok, kind, where=""):
        self.counts[kind] += 1
        if not ok:
            self.errors.append({"kind": kind, "where": where})

    def bind(self, path):
        p = Path(path); h = digest(p)
        self.bindings[p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix()] = h
        return h


def label_free(value):
    if isinstance(value, dict):
        return not set(value) & FORBIDDEN and all(label_free(v) for v in value.values())
    if isinstance(value, list):
        return all(label_free(v) for v in value)
    return True


def objective(q):
    """Independent binary-double rint(scale)/scale, matching np.round(q,5)."""
    return round(-float(Fraction(q)) * 100000.0) / 100000.0


def population(rows):
    unique, seen = [], set()
    for row in rows:
        if not row["feedback"]["quality_covered"]:
            continue
        obj = objective(row["feedback"]["macro_quality_exact"])
        if obj not in seen:
            seen.add(obj); unique.append({**row, "objective": obj})
    return sorted(unique, key=lambda r: r["objective"])[:2]


def draw(pop, count, run, slot, salt):
    seed = int.from_bytes(sha256(f"{salt}|{run}|{slot}|parents".encode()).digest(), "big")
    rng = random.Random(seed)
    return rng.choices(pop, weights=[1 / (i + 1 + len(pop)) for i in range(len(pop))], k=count)


def static(study, c):
    p, freeze, release, config, context, inputs, seed, transport = (load(study / n) for n in
        ("protocol.json", "freeze_receipt.json", "root_authoring_release.json", "config.json", "common_context.json",
         "train_inputs.json", "seed.json", "transport_binding.json"))
    for name, expected in (("protocol.json", PROTO_SHA), ("freeze_receipt.json", FREEZE_SHA),
                           ("root_authoring_release.json", RELEASE_SHA)):
        c.require(c.bind(study / name) == expected, "pinned_pre_authoring_registration", name)
    c.require(freeze["before_any_published_authoring_or_fitness"] is True, "before_any_author_or_fitness_freeze")
    for name, expected in freeze["artifact_sha256"].items():
        c.require(c.bind(study / name.replace("\\", "/")) == expected, "all_original_static_frozen_bytes", name)
    for name, expected in p["source_sha256"].items():
        c.require(c.bind(ROOT / name) == expected == digest(study / "source_snapshot" / name), "original_source_snapshot_identity", name)
    c.require(c.bind(ROOT / "scripts/verify_refinement_authoring_v06.py") == TOOL_AUDITOR_SHA,
              "independent_tool_scope_verifier_pinned")
    plan_path = ROOT / "experiments/discovery/v06_published_eoh_inputs_001/execution_plan.json"
    plan = load(plan_path)
    c.require(c.bind(plan_path) == PLAN_SHA == release["execution_plan_sha256"]
        and plan["waves"] == [[0, 1], [2, 3]] and plan["max_concurrent_local_author_calls"] == 2
        and plan["fitness_transactions_serialized"] and plan["workers_per_fitness_transaction"] == 8
        and plan["next_slot_requires_previous_hash_bound_feedback_ingested"]
        and plan["new_wave_requires_previous_wave_positions_disposed"], "root_pre_authoring_two_wave_execution_plan")
    c.require(release["allow_authoring"] and not release["TEST_allowed"] and release["requested_positions"] == 32
        and p["split"] == "train" and p["TEST_accessed"] is False and p["feedback_certificate_access"] is False,
        "root_TRAIN_only_original32_release")
    c.require(config["operator_sequence"] == list(OPS) and config["fixed_blocks"] == 4 and config["slots_per_block"] == 8
        and config["population_size"] == 2 and config["server_workers"] == 8, "fixed_operator_population_budget")
    c.require(seed["TRAIN_label_selected_history"] is True and canonical(seed["program"]) == SEED_SHA
        == p["shared_R1_warm_seed_sha256"] and normalized_program(seed["program"]) == seed["program"],
        "exact_R2_visible_seed_with_label_selected_history_disclosed")
    records = inputs["records"]
    c.require(len(records) == 120 and len({r["id"] for r in records}) == 120 and label_free(records)
        and all(set(r) == {"id", "split", "family", "cluster", "graph", "graph_digest", "fixed", "excluded"}
                and r["split"] == "train" for r in records), "full120_label_free_TRAIN_input_frame")
    for record in records:
        c.require(graph_digest(record["graph"]) == record["graph_digest"], "independent_TRAIN_graph_digest", record["id"])
    rmap = {r["id"]: r for r in records}
    c.require(set(context) == {"task", "typed_grammar", "TRAIN_examples"} and label_free(context)
        and all(r == rmap.get(r.get("id")) for r in context["TRAIN_examples"]), "label_free_unchanged_author_examples")
    for field, name in (("config_sha256", "config.json"), ("seed_binding_sha256", "seed.json"),
                        ("training_states_sha256", "train_inputs.json"), ("kernel_config_sha256", "kernel_config.json"),
                        ("transport_binding_sha256", "transport_binding.json")):
        c.require(digest(study / name) == p[field], "protocol_original_input_binding", field)
    return p, config, context, records, seed, transport


def final_gate(study):
    """Check only final inventory metadata before any output/program read."""
    path = study / "selection.json"
    if not path.is_file():
        raise ValueError("Final four EoH outputs and all32 original positions are not frozen; do not audit evolving outputs")
    selection = load(path)
    expected = [(r, s, f"run_{r}_slot_{s}") for r in range(4) for s in range(8)]
    if (selection.get("version") != "v06_published_EoH_DSL_TRAIN_quality_selection_001"
        or selection.get("all32_positions_frozen") is not True or selection.get("TEST_accessed") is not False
        or selection.get("requested_positions") != 32 or selection.get("protocol_sha256") != PROTO_SHA
        or selection.get("root_authoring_release_sha256") != RELEASE_SHA
        or len(selection.get("programs", [])) != 4
        or [(p["run"], p["slot"], p["id"]) for p in selection.get("original_positions", [])] != expected):
        raise ValueError("Final all32/four-output freeze has incomplete identities or changed protocol")
    # Four actual seed assessments must also exist; a mere flag cannot invent them.
    for run in range(4):
        for name in ("seed.json", "seed.receipt.json"):
            if not (study / "fitness" / f"run_{run}" / name).is_file():
                raise ValueError("All four original seed fitness observations must freeze first")
    return selection


def feedback(study, run, slot, p, c):
    path = study / "fitness" / f"run_{run}" / ("seed.json" if slot is None else f"slot_{slot}.json")
    f, receipt = load(path), load(path.with_suffix(".receipt.json"))
    c.require(set(f) == FEEDBACK_KEYS and label_free(f) and f["run"] == run and f["slot"] == slot,
              "exact_label_free_feedback_schema_identity", str(path))
    c.require(c.bind(path) == receipt["feedback_sha256"] and receipt["source_sha256"] == p["source_sha256"]
        and receipt["protocol_sha256"] == PROTO_SHA and receipt["training_states_sha256"] == p["training_states_sha256"]
        and receipt["root_release_sha256"] == RELEASE_SHA and receipt["split"] == "train"
        and receipt["TEST_accessed"] is False and receipt["certificate_access"] is False,
        "frozen_server_feedback_import_receipt", str(path))
    c.bind(path.with_suffix(".receipt.json"))
    return f


def expected_request(run, slot, pop, seed, seed_feedback, context, p, config):
    req = {"version": "v06_published_EoH_transaction_001", "run": run, "slot": slot,
        "id": f"run_{run}:warm_seed" if slot is None else f"run_{run}_slot_{slot}",
        "operator": "seed" if slot is None else OPS[slot], "protocol_sha256": PROTO_SHA,
        "root_release_sha256": RELEASE_SHA, "training_states_sha256": p["training_states_sha256"],
        "parents": [], "population_before": []}
    if slot is None:
        req["program"] = seed["program"]
        return req
    parents = [] if OPS[slot] == "i1" else draw(pop, 2 if OPS[slot] in ("e1", "e2") else 1, run, slot, config["rng_salt"])
    req["parents"] = [r["id"] for r in parents]
    req["population_before"] = [{"id": r["id"], "objective": r["objective"]} for r in pop]
    req["packet"] = {"task": context, "operator": OPS[slot], "warm_seed": seed["program"],
        "warm_seed_fitness": seed_feedback, "parents": [{"id": r["id"], "thought": r["program"]["rationale"],
        "program": r["program"], "fitness_feedback": r["feedback"]} for r in parents],
        "output": "Exactly one FeatureRuleProgram JSON object: name,features,rule,rationale; no batch"}
    return req


def request_and_author(study, run, slot, expected, transport, c):
    stem = f"run_{run}_slot_{slot}"
    call, request = study / "calls" / stem, study / "requests" / (stem + ".json")
    req, receipt = load(request), load(call / "receipt.json")
    c.require(req == expected and label_free(req["packet"]), "independent_operator_with_replacement_parent_packet_recipe", stem)
    c.require(c.bind(request) == receipt["request_sha256"] == c.bind(call / "request.json"), "immutable_author_request_identity", stem)
    for field, name in (("response_sha256", "response.json"), ("wrapper_sha256", "input.txt"),
                        ("raw_event_sha256", "events.jsonl"), ("raw_stderr_sha256", "stderr.txt")):
        c.require(c.bind(call / name) == receipt[field], "all_exact_original_author_bytes", stem + "/" + field)
    c.bind(call / "receipt.json"); c.bind(call / "last_message.txt")
    c.require((call / "last_message.txt").read_bytes() == (call / "response.json").read_bytes(), "exact_unmodified_final_response", stem)
    c.require((receipt["id"], receipt["run"], receipt["slot"], receipt["operator"]) == (stem, run, slot, OPS[slot])
        and receipt["root_release_sha256"] == RELEASE_SHA and receipt["no_retry"] is True
        and receipt["no_candidate_assessment"] is True and receipt["TEST_accessed"] is False
        and receipt["requested_configuration"] == transport["requested_configuration"]
        and receipt["cli_executable_sha256"] == transport["cli_executable_sha256"], "single_original_native_call_same_requested_configuration", stem)
    prompt = (call / "input.txt").read_text(encoding="utf-8")
    c.require(prompt.endswith(json.dumps(req["packet"], ensure_ascii=False)) and INSTRUCTION[OPS[slot]] in prompt
        and "Read only the packet supplied below or packet.json." in prompt and "run no evaluation" in prompt,
        "full_original_label_free_packet_inline_operator_isolation", stem)
    allowed = (ROOT / ".research/v06_published_eoh_cli_workspaces" / study.name / stem / "packet.json").as_posix()
    work = Path(allowed)
    if work.exists():
        c.require(load(work) == req["packet"] and sorted(p.name for p in work.parent.iterdir()) == ["packet.json"],
                  "isolated_author_workspace_packet_only", stem)
        c.bind(work)
    usage, models, tool_history, thread_ids, event_errors = [], [], [], [], []
    started_tools, completed_tools = set(), set()
    for i, line in enumerate((call / "events.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except ValueError:
            c.require(False, "valid_original_event_JSON", stem + "/" + str(i)); continue
        if event.get("usage") is not None:
            usage.append({"event_type": event.get("type"), "usage": event["usage"]})
        if event.get("model") is not None:
            models.append(event["model"])
        if event.get("type") == "thread.started":
            thread_ids.append(event.get("thread_id"))
        if event.get("type") in ("error", "turn.failed"):
            event_errors.append({"line": i, "type": event.get("type"), "sha256": canonical(event)})
        item = event.get("item") or {}
        if event.get("type") == "item.started" and item.get("type") not in ("agent_message", "reasoning", "error"):
            started_tools.add(item.get("id"))
        if event.get("type") == "item.completed" and item.get("type") not in ("agent_message", "reasoning", "error"):
            completed_tools.add(item.get("id"))
            reviewed = review_tool(item, allowed)
            reviewed.update(event_line=i, event_sha256=canonical(event), raw_events_sha256=receipt["raw_event_sha256"])
            tool_history.append(reviewed)
            c.require(reviewed["resolved_no_external_access"], "no_successful_external_outcome_or_shared_write_tool_access", stem + "/" + str(i))
    c.require(started_tools <= completed_tools, "no_unresolved_started_tool_access_before_termination", stem)
    c.require(receipt["usage_events"] == (usage or None) and receipt["observed_model"] == (models or None),
              "actual_usage_and_served_model_unknown_preserved", stem)
    c.require(type(receipt["wall_seconds"]) in (int, float) and math.isfinite(receipt["wall_seconds"])
        and receipt["wall_seconds"] >= 0 and type(receipt["timed_out"]) is bool,
        "finite_original_author_wall_timeout_metadata", stem)
    static_program, static_error = None, None
    if receipt.get("exit_code") == 0 and not receipt["timed_out"] and receipt.get("spawn_error") is None:
        try:
            static_program = normalized_program(load(call / "response.json"))
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            static_error = type(error).__name__
    else:
        static_error = "original_transport_failure"
    return {"id": stem, "run": run, "slot": slot, "operator": OPS[slot], "program": static_program,
        "program_sha256": canonical(static_program) if static_program is not None else None,
        "static_error": static_error, "receipt_sha256": digest(call / "receipt.json"),
        "response_sha256": digest(call / "response.json"), "thread_ids": thread_ids, "tool_history": tool_history,
        "observed_model": models or None, "usage_events": usage or None, "event_errors": event_errors,
        "requested_configuration": receipt["requested_configuration"], "wall_seconds": receipt["wall_seconds"],
        "exit_code": receipt["exit_code"], "timed_out": receipt["timed_out"]}


def final_report(study, registration_only=False):
    selected = None if registration_only else final_gate(study)
    c = Checks(); p, config, context, records, seed, transport = static(study, c)
    if registration_only:
        return {"version": "independent_published_EoH_static_registration_review_001", "audit_phase": "registration",
            "checks": sum(c.counts.values()), "checks_by_kind": dict(c.counts), "errors": len(c.errors),
            "error_details": c.errors, "TEST_accessed": False, "all32_positions_frozen": False,
            "protocol_sha256": PROTO_SHA, "source_and_receipt_bindings": c.bindings}
    selection_sha = c.bind(study / "selection.json")
    c.require(selected["no_retry_or_fallback_authored_output"] and selected["future_performance_registration_required"],
              "no_TEST_selection_or_hidden_authored_fallback")
    sessions, populations, expected_outputs, unissued, repeated_parents = [], [], [], [], 0
    allpositions = {q["id"]: q for q in selected["original_positions"]}
    for run in range(4):
        sf = feedback(study, run, None, p, c)
        seed_req = study / "requests" / f"run_{run}_seed.json"
        c.require(load(seed_req) == expected_request(run, None, [], seed, sf, context, p, config), "exact_original_seed_request", run)
        c.bind(seed_req)
        pop = population([{"id": f"run_{run}:warm_seed", "program": seed["program"], "feedback": sf}])
        for slot in range(8):
            stem = f"run_{run}_slot_{slot}"
            if not sf["quality_covered"]:
                inv = allpositions[stem]
                c.require(inv["status"] == "unissued_seed_execution_failure"
                    and all(inv[k] is None for k in ("feedback_sha256", "receipt_sha256", "response_sha256"))
                    and not (study / "calls" / stem).exists(), "seed_failure_preserved_unissued_original_position", stem)
                unissued.append(stem); continue
            expected = expected_request(run, slot, pop, seed, sf, context, p, config)
            session = request_and_author(study, run, slot, expected, transport, c)
            sessions.append(session)
            repeated_parents += len(expected["parents"]) != len(set(expected["parents"]))
            f = feedback(study, run, slot, p, c)
            inv = allpositions[stem]
            c.require(inv["operator"] == OPS[slot] and inv["status"] == f["status"]
                and inv["feedback_sha256"] == digest(study / "fitness" / f"run_{run}" / f"slot_{slot}.json")
                and inv["receipt_sha256"] == session["receipt_sha256"] and inv["response_sha256"] == session["response_sha256"],
                "final_selection_all_original_position_receipts", stem)
            if f["quality_covered"]:
                c.require(session["program"] is not None and f["program_sha256"] == session["program_sha256"],
                          "feedback_bound_to_exact_original_static_author_program", stem)
                pop = population(pop + [{"id": stem, "program": session["program"], "feedback": f}])
            populations.append({"run": run, "slot": slot, "parents": expected["parents"],
                "population_before": expected["population_before"],
                "population_after": [{"id": r["id"], "objective": r["objective"]} for r in pop]})
        best = pop[0] if pop else None
        expected_outputs.append({"id": f"published_EoH_DSL_quality:run_{run}", "run": run,
            "role": "nonguarded_published_quality_baseline", "joint_gate_required": False,
            "program": best["program"] if best else None, "program_sha256": canonical(best["program"]) if best else None,
            "source_id": best["id"] if best else None,
            "winner_origin": "shared_R1_warm_seed" if best and best["id"].endswith(":warm_seed") else "genuine_EoH_author_slot" if best else "missing",
            "TRAIN_label_selected_seed_history": True, "gate_fit_not_used_for_selection": True})
    c.require(selected["programs"] == expected_outputs, "four_exact_rounded_quality_first_equal_objective_pipeline_outputs")
    c.require(len(sessions) + len(unissued) == 32 and selected["native_CLI_spawned_attempts"]
        == sum(s["exit_code"] is not None for s in sessions), "all_original32_dispositions_without_retries")
    threads = [t for s in sessions for t in s["thread_ids"]]
    c.require(len(threads) == len(set(threads)), "distinct_fresh_ephemeral_author_threads")
    return {"version": "independent_published_EoH_frozen_authoring_audit_001", "audit_phase": "authoring",
        "checks": sum(c.counts.values()), "checks_by_kind": dict(c.counts), "errors": len(c.errors), "error_details": c.errors,
        "selection_sha256": selection_sha, "protocol_sha256": PROTO_SHA, "root_authoring_release_sha256": RELEASE_SHA,
        "all32_positions_frozen": True, "TEST_accessed": False, "original_position_count": 32,
        "seed_fitness_count": 4, "native_author_positions": len(sessions), "unissued_positions": unissued,
        "repeated_parent_requests_with_replacement": repeated_parents,
        "four_pipeline_outputs": expected_outputs, "sessions": sessions, "independent_population_history": populations,
        "source_and_receipt_bindings": c.bindings, "audit_script_sha256": digest(__file__),
        "limits": ["Requested model/configuration does not identify the served model when raw events omit it",
            "Driver receipts contain author wall duration but no absolute start/end timestamps; max-two occupancy is a root plan/runtime-source claim, not independently timed proof",
            "TRAIN work is reported to authors but is not a population, parent or final-winner tie-break",
            "Shared warm seed was selected using R1 labelled evidence; subsequent EoH feedback is label-free",
            "Fitness correctness is certified by the separate independent TRAIN trace audit, not these imported feedback values"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", default=str(STUDY)); p.add_argument("--out", required=True)
    p.add_argument("--registration-only", action="store_true")
    a = p.parse_args(); out = Path(a.out)
    if out.exists():
        raise ValueError("Preserve every original audit report; use a new reviewed report for manual resolutions")
    report = final_report(Path(a.study), a.registration_only)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"phase": report["audit_phase"], "checks": report["checks"], "errors": report["errors"],
                      "report_sha256": digest(out)}))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
