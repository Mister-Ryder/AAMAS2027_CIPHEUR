"""Bounded, seeded EoH-DSL prototype with manual local/server transactions.

No author call is made by this module. Linux fitness uses TRAIN-only problem
states and the original shared kernel, never certificates or information gates.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import shutil
import time
import numpy as np

from .graph_features import FeatureRuleProgram, FEATURE_RULE_SCHEMA, graph_operation_library
from .programs import FEATURES
from .model import Graph
from .repair_v06 import RepairConfig, repair_schedule
from .synthesis_study_v06 import canonical, digest, macro_quality, write
from .heldout_refinement_v06 import ORIGINAL_RUNTIME_SHA256
from .heldout_mechanism_v06 import REPAIR_CONFIG

ROOT = Path(__file__).resolve().parents[1]
OPS = ("i1", "i1", "e1", "e2", "m1", "m2", "m3", "e2")
SOURCES = tuple("cipheur/" + n for n in ORIGINAL_RUNTIME_SHA256) + (
    "cipheur/heldout_refinement_v06.py", "cipheur/heldout_mechanism_v06.py", "cipheur/__init__.py",
    "cipheur/refinement_study_v06.py",
    "cipheur/published_eoh_v06.py", "scripts/author_published_eoh_cli_v06.py", "scripts/author_matched_cli_v06.py")
FORBIDDEN = {"labels", "queries", "strict_fit", "strict_passed", "quotient", "strict_checks",
             "witness", "equality_joins", "gate", "eligible", "base_alias_by_side",
             "lower_exact", "upper_exact", "cancelled_components", "certificate"}
FEEDBACK_KEYS = {"id", "run", "slot", "operator", "program_sha256", "quality_covered",
    "status", "macro_quality_exact", "macro_work_exact", "family_quality", "family_work",
    "assigned_states", "completed_feasible_states", "error_count", "unexecuted_states"}


def source_hashes():
    return {n: digest(ROOT / n) for n in SOURCES}


def read(path):
    return json.loads(Path(path).read_bytes())


def grammar_contract():
    return {"operation_library": graph_operation_library(), "program_schema": FEATURE_RULE_SCHEMA,
        "base_features": list(FEATURES), "limits": dict(max_added_features=6, max_expression_nodes=48,
            max_expression_depth=8, max_rule_AST_nodes=256, max_rule_characters=2000),
        "rule": "Numeric feature names/constants; +,-,*,/, unary signs; numeric comparisons, and/or/not, conditional expressions; min/max with1..8arguments and abs with1argument; finite constants with absolute value<=1e9; no imports, attributes, loops or arbitrary function calls"}


def reject_labels(value):
    if isinstance(value, dict):
        if set(value) & FORBIDDEN:
            raise ValueError("Published discovery input/feedback includes certified information")
        for item in value.values():
            reject_labels(item)
    elif isinstance(value, list):
        for item in value:
            reject_labels(item)


def validate_records(records):
    if len(records) != 120 or len({r["id"] for r in records}) != 120:
        raise ValueError("Exactly120 original TRAIN problem states are required")
    reject_labels(records)
    allowed = {"id", "split", "family", "cluster", "graph", "graph_digest", "fixed", "excluded"}
    for r in records:
        if set(r) != allowed or r["split"] != "train" or Graph.from_dict(r["graph"]).digest() != r["graph_digest"]:
            raise ValueError("Changed TRAIN-only state contract")


def validate_config(cfg):
    if (cfg.get("version") != "v06_published_EoH_DSL_pre_authoring_001"
        or cfg.get("fixed_blocks") != 4 or cfg.get("slots_per_block") != 8
        or cfg.get("operator_sequence") != list(OPS) or cfg.get("population_size") != 2
        or cfg.get("server_workers") != 8 or cfg.get("request_timeout_seconds") != 1800
        or cfg.get("grammar") != dict(max_added_features=6, max_expression_nodes=48,
                                      max_expression_depth=8, max_rule_AST_nodes=256)):
        raise ValueError("Frozen published EoH candidate/operator/grammar budget changed")


def prepare(config, seed, common_context, train_inputs, kernel_config, transport_binding, out):
    out = Path(out)
    if out.exists():
        raise ValueError("Never overwrite published synthesis registration")
    cfg, seed_value, context, data, kernel, transport = map(read, (config, seed, common_context,
        train_inputs, kernel_config, transport_binding))
    validate_config(cfg); validate_records(data["records"])
    reject_labels(context)
    if (set(context) != {"task", "typed_grammar", "TRAIN_examples"}
        or context["typed_grammar"] != grammar_contract()
        or seed_value.get("TRAIN_label_selected_history") is not True
        or not isinstance(seed_value.get("R1_seed_selection_sha256"), str)
        or len(seed_value["R1_seed_selection_sha256"]) != 64
        or not isinstance(seed_value.get("source_candidate_id"), str)
        or FeatureRuleProgram.from_dict(seed_value["program"]).to_dict() != seed_value["program"]
        or canonical(seed_value["program"]) != seed_value["program_sha256"]
        or kernel["seconds"] != .5 or kernel["clock"] != "wall" or kernel["workers"] != 8
        or kernel["repair_config"] != REPAIR_CONFIG
        or set(transport["requested_configuration"]) != {"model", "model_provider", "model_reasoning_effort",
                                                        "model_reasoning_summary", "profile"}):
        raise ValueError("Common warm seed/task/transport/kernel contract changed")
    record_map = {r["id"]: r for r in data["records"]}
    if any(example != record_map.get(example.get("id")) for example in context["TRAIN_examples"]):
        raise ValueError("Every author example must be an unchanged TRAIN problem state")
    sources = source_hashes()
    for n, expected in ORIGINAL_RUNTIME_SHA256.items():
        if sources["cipheur/" + n] != expected:
            raise ValueError("Original scientific runtime changed: " + n)
    out.mkdir(parents=True)
    for name, path in (("config.json", config), ("seed.json", seed), ("common_context.json", common_context),
                       ("train_inputs.json", train_inputs), ("kernel_config.json", kernel_config),
                       ("transport_binding.json", transport_binding)):
        shutil.copyfile(path, out / name)
    for name in sources:
        target = out / "source_snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, target)
    write(out / "protocol.json", {"version": "v06_published_EoH_DSL_001", "split": "train",
        "config_sha256": digest(config), "seed_binding_sha256": digest(seed),
        "shared_R1_warm_seed_sha256": seed_value["program_sha256"],
        "R1_seed_selection_sha256": seed_value["R1_seed_selection_sha256"],
        "training_states_sha256": digest(train_inputs), "kernel_config_sha256": digest(kernel_config),
        "transport_binding_sha256": digest(transport_binding), "source_sha256": sources,
        "requested_positions": 32, "feedback_certificate_access": False,
        "R2_samples_roles_selectors_unchanged": True, "TEST_accessed": False})
    write(out / "freeze_receipt.json", {"before_any_published_authoring_or_fitness": True,
        "artifact_sha256": {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()}})
    return {"prepared": str(out), "author_calls": 0, "fitness_evaluations": 0}


def load_study(study, root_release_sha256):
    study = Path(study); freeze = read(study / "freeze_receipt.json")
    if freeze.get("before_any_published_authoring_or_fitness") is not True:
        raise ValueError("Missing published pre-authoring freeze")
    for name, expected in freeze["artifact_sha256"].items():
        if digest(study / name) != expected:
            raise ValueError("Published source/input freeze changed: " + name)
    proto = read(study / "protocol.json")
    if proto["source_sha256"] != source_hashes():
        raise ValueError("Frozen published runtime changed")
    release_path = study / "root_authoring_release.json"
    if digest(release_path) != root_release_sha256:
        raise ValueError("Published root release SHA256 changed")
    release = read(release_path)
    if (release.get("version") != "v06_published_EoH_root_authoring_release_001"
        or release.get("issued_by") != "root" or release.get("allow_authoring") is not True
        or release.get("protocol_sha256") != digest(study / "protocol.json")
        or release.get("freeze_receipt_sha256") != digest(study / "freeze_receipt.json")
        or release.get("shared_R1_warm_seed_sha256") != proto["shared_R1_warm_seed_sha256"]
        or release.get("R1_seed_selection_sha256") != proto["R1_seed_selection_sha256"]
        or release.get("requested_positions") != 32 or release.get("TEST_allowed") is not False):
        raise ValueError("Separate root-reviewed published authoring release is required")
    validate_config(read(study / "config.json"))
    return proto


def population_management(pop):
    """Official v0.1 equal-rounded-objective dedup; work never breaks a tie."""
    unique, seen = [], set()
    for row in pop:
        f = row["feedback"]
        if not f["quality_covered"]:
            continue
        obj = float(np.round(-float(Fraction(f["macro_quality_exact"])), 5))
        if obj not in seen:
            seen.add(obj); unique.append({**row, "objective": obj})
    return sorted(unique, key=lambda x: x["objective"])[:2]


def parent_draw(population, count, run, slot, salt):
    if not population:
        raise ValueError("Empty published population: preserve failure; no substitute")
    seed = int.from_bytes(sha256(f"{salt}|{run}|{slot}|parents".encode()).digest(), "big")
    rng = random.Random(seed)
    weights = [1 / (i + 1 + len(population)) for i in range(len(population))]
    return rng.choices(population, weights=weights, k=count)


def fitness_feedback(study, run, slot):
    study = Path(study)
    path = study / "fitness" / f"run_{run}" / ("seed.json" if slot is None else f"slot_{slot}.json")
    value, receipt, proto = read(path), read(path.with_suffix(".receipt.json")), read(study / "protocol.json")
    if (set(value) != FEEDBACK_KEYS or receipt["feedback_sha256"] != digest(path)
        or receipt["source_sha256"] != proto["source_sha256"]
        or receipt["protocol_sha256"] != digest(study / "protocol.json")
        or receipt["training_states_sha256"] != proto["training_states_sha256"]
        or receipt["root_release_sha256"] != digest(study / "root_authoring_release.json")
        or receipt["split"] != "train" or receipt["certificate_access"] is not False
        or receipt["TEST_accessed"] is not False or (value["run"], value["slot"]) != (run, slot)):
        raise ValueError("Imported published fitness changed after its server receipt")
    reject_labels(value)
    return value


def history_population(study, run, slot):
    study = Path(study)
    seed = read(study / "seed.json")["program"]
    seed_feedback = fitness_feedback(study, run, None)
    pop = population_management([{"id": f"run_{run}:warm_seed", "program": seed, "feedback": seed_feedback}])
    for old_slot in range(slot):
        stem = f"run_{run}_slot_{old_slot}"
        feedback = fitness_feedback(study, run, old_slot)
        if feedback["quality_covered"]:
            raw = read(study / "calls" / stem / "response.json")
            call_receipt = read(study / "calls" / stem / "receipt.json")
            if (call_receipt["response_sha256"] != digest(study / "calls" / stem / "response.json")
                or canonical(raw) != feedback["program_sha256"]):
                raise ValueError("Published parent program changed after its measured fitness")
            pop = population_management(pop + [{"id": stem, "program": raw, "feedback": feedback}])
    return pop


def make_request(study, run, slot, out, root_release_sha256):
    study, out = Path(study), Path(out)
    proto = load_study(study, root_release_sha256)
    if type(run) is not int or not 0 <= run < 4 or (slot is not None and (type(slot) is not int or not 0 <= slot < 8)):
        raise ValueError("Only original four-run/eight-slot identities are valid")
    if out.exists():
        raise ValueError("Never overwrite or retry a published request")
    request = {"version": "v06_published_EoH_transaction_001", "run": run, "slot": slot,
        "id": f"run_{run}:warm_seed" if slot is None else f"run_{run}_slot_{slot}",
        "operator": "seed" if slot is None else OPS[slot], "protocol_sha256": digest(study / "protocol.json"),
        "root_release_sha256": root_release_sha256, "training_states_sha256": proto["training_states_sha256"],
        "parents": [], "population_before": []}
    if slot is None:
        request["program"] = read(study / "seed.json")["program"]
    else:
        pop = history_population(study, run, slot)
        if not pop:
            raise ValueError("Empty published population; no fabricated author output")
        parents = [] if OPS[slot] == "i1" else parent_draw(pop, 2 if OPS[slot] in ("e1", "e2") else 1,
            run, slot, read(study / "config.json")["rng_salt"])
        request["population_before"] = [{"id": p["id"], "objective": p["objective"]} for p in pop]
        request["parents"] = [p["id"] for p in parents]
        request["packet"] = {"task": read(study / "common_context.json"), "operator": OPS[slot],
            "warm_seed": read(study / "seed.json")["program"],
            "warm_seed_fitness": fitness_feedback(study, run, None),
            "parents": [{"id": p["id"], "thought": p["program"]["rationale"], "program": p["program"],
                         "fitness_feedback": p["feedback"]} for p in parents],
            "output": "Exactly one FeatureRuleProgram JSON object: name,features,rule,rationale; no batch"}
        reject_labels(request["packet"])
    write(out, request)
    return request


def assess_state(task):
    record, raw, kernel = task
    row = {"id": record["id"], "family": record["family"], "cluster": record["cluster"]}
    try:
        graph = Graph.from_dict(record["graph"])
        result = repair_schedule(graph, raw, fixed=record["fixed"], excluded=record["excluded"], priority="program",
            seconds=kernel["seconds"], clock=kernel["clock"], config=RepairConfig(**kernel["repair_config"]))
        value = sum((Fraction(graph.nodes[n].weight) for n in result["selected"]), Fraction())
        if (not graph.feasible(result["selected"]) or not set(record["fixed"]) <= set(result["selected"])
            or set(record["excluded"]) & set(result["selected"]) or Fraction(result["value_exact"]) != value):
            raise ValueError("Independent full-graph incumbent check failed")
        row["result"] = result
    except Exception as error:
        row.update(error_type=type(error).__name__, error=str(error))
    return row


def quality_assessment(raw, records, kernel, workers=8):
    FeatureRuleProgram.from_dict(raw)
    # Public server entry checks the complete120 frame; this pure helper supports tiny tests.
    if not records or any(r["split"] != "train" for r in records):
        raise ValueError("Published fitness must never include TEST")
    reject_labels(records)
    tasks = [(r, raw, kernel) for r in sorted(records, key=lambda x: x["id"])]
    if workers == 1:
        rows = [assess_state(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(assess_state, tasks))
    covered = all(r.get("result", {}).get("completed") and r["result"]["feasible"] for r in rows)
    summary = macro_quality(rows, records) if covered else None
    return rows, summary


def evaluate(study, request, out, root_release_sha256, call_directory=None):
    if platform.system() != "Linux":
        raise ValueError("Published full-TRAIN fitness is server-only Linux")
    study, request_path, out = Path(study), Path(request), Path(out)
    if out.exists():
        raise ValueError("Never overwrite published fitness observations")
    proto = load_study(study, root_release_sha256); req = read(request_path)
    if (req["protocol_sha256"] != digest(study / "protocol.json")
        or req["root_release_sha256"] != root_release_sha256
        or req["training_states_sha256"] != proto["training_states_sha256"]):
        raise ValueError("Published request/source/state binding changed")
    if (type(req["run"]) is not int or not 0 <= req["run"] < 4
        or (req["slot"] is not None and (type(req["slot"]) is not int or not 0 <= req["slot"] < 8))
        or req["operator"] != ("seed" if req["slot"] is None else OPS[req["slot"]])
        or req["id"] != (f"run_{req['run']}:warm_seed" if req["slot"] is None else f"run_{req['run']}_slot_{req['slot']}")):
        raise ValueError("Published request identity/operator changed")
    records = read(study / "train_inputs.json")["records"]; validate_records(records)
    raw, status = None, "unparsed"
    try:
        if req["slot"] is None:
            raw = req["program"]
            if canonical(raw) != proto["shared_R1_warm_seed_sha256"]:
                raise ValueError("Published common warm seed changed")
        else:
            calls = Path(call_directory); receipt = read(calls / "receipt.json")
            transport = read(study / "transport_binding.json")
            if (receipt["request_sha256"] != digest(request_path) or receipt.get("no_retry") is not True
                or receipt["response_sha256"] != digest(calls / "response.json")
                or (receipt["id"], receipt["run"], receipt["slot"], receipt["operator"]) !=
                   (req["id"], req["run"], req["slot"], req["operator"])
                or receipt["root_release_sha256"] != root_release_sha256
                or receipt["requested_configuration"] != transport["requested_configuration"]
                or receipt["cli_executable_sha256"] != transport["cli_executable_sha256"]
                or receipt["raw_event_sha256"] != digest(calls / "events.jsonl")
                or receipt["raw_stderr_sha256"] != digest(calls / "stderr.txt")
                or receipt["wrapper_sha256"] != digest(calls / "input.txt")
                or digest(calls / "request.json") != digest(request_path)
                or receipt.get("TEST_accessed") is not False or receipt.get("no_candidate_assessment") is not True):
                raise ValueError("Published genuine-call binding changed")
            if receipt["exit_code"] != 0 or receipt["timed_out"]:
                raise ValueError("Published transport failed; original slot stays missing")
            raw = read(calls / "response.json")
        raw = FeatureRuleProgram.from_dict(raw).to_dict(); status = "static_valid"
    except (ValueError, TypeError, KeyError, UnicodeError) as error:
        raw = None; status = "invalid_or_failed_original_attempt"
        failure = {"error_type": type(error).__name__, "error": str(error)}
    cpu, wall = time.process_time(), time.perf_counter()
    rows, summary = quality_assessment(raw, records, read(study / "kernel_config.json")) if raw is not None else ([], None)
    if raw is not None:
        status = "quality_covered" if summary is not None else "kernel_error"
    feedback = {"id": req["id"], "run": req["run"], "slot": req["slot"], "operator": req["operator"],
        "program_sha256": canonical(raw) if raw is not None else None, "quality_covered": summary is not None,
        "status": status, "macro_quality_exact": summary["macro_quality_exact"] if summary else None,
        "macro_work_exact": summary["macro_work_exact"] if summary else None,
        "family_quality": summary["family_reward_over_total_weight"] if summary else None,
        "family_work": summary["family_work"] if summary else None, "assigned_states": 120,
        "completed_feasible_states": sum(bool(r.get("result", {}).get("completed") and r["result"]["feasible"]) for r in rows),
        "error_count": sum(not bool(r.get("result", {}).get("completed") and r["result"]["feasible"]) for r in rows),
        "unexecuted_states": 120 - len(rows)}
    out.mkdir(parents=True)
    write(out / "assessment.json", {"request": req, "program": raw, "kernel_rows": rows,
        "kernel_summary": summary, "failure": failure if raw is None else None,
        "actual_cpu_seconds": time.process_time() - cpu, "actual_wall_seconds": time.perf_counter() - wall,
        "certificate_access": False, "selection_performed": False})
    write(out / "feedback.json", feedback)
    write(out / "execution.json", {"request_sha256": digest(request_path), "root_release_sha256": root_release_sha256,
        "protocol_sha256": digest(study / "protocol.json"), "training_states_sha256": proto["training_states_sha256"],
        "source_sha256": proto["source_sha256"], "feedback_sha256": digest(out / "feedback.json"),
        "assessment_sha256": digest(out / "assessment.json"), "split": "train", "TEST_accessed": False,
        "certificate_access": False, "python_version": platform.python_version(), "numpy_version": np.__version__,
        "platform": platform.platform()})
    return feedback


def ingest(study, request, result, feedback_sha256, root_release_sha256):
    study, result = Path(study), Path(result)
    proto = load_study(study, root_release_sha256); req, execution = read(request), read(result / "execution.json")
    feedback = read(result / "feedback.json")
    target = study / "fitness" / f"run_{req['run']}" / ("seed.json" if req["slot"] is None else f"slot_{req['slot']}.json")
    if target.exists():
        raise ValueError("Never overwrite or reselect imported published fitness")
    if (set(feedback) != FEEDBACK_KEYS or execution["feedback_sha256"] != feedback_sha256
        or digest(result / "feedback.json") != feedback_sha256
        or execution["assessment_sha256"] != digest(result / "assessment.json")
        or execution["request_sha256"] != digest(request) or execution["root_release_sha256"] != root_release_sha256
        or execution["source_sha256"] != proto["source_sha256"]
        or execution["protocol_sha256"] != digest(study / "protocol.json")
        or execution["training_states_sha256"] != proto["training_states_sha256"]
        or execution["split"] != "train" or execution["TEST_accessed"] is not False
        or execution["certificate_access"] is not False or feedback["id"] != req["id"]
        or (feedback["run"], feedback["slot"], feedback["operator"]) != (req["run"], req["slot"], req["operator"])
        or feedback["assigned_states"] != 120
        or (feedback["quality_covered"] and feedback["completed_feasible_states"] != 120)):
        raise ValueError("Published server fitness transaction binding changed")
    reject_labels(feedback)
    write(target, feedback)
    write(target.with_suffix(".receipt.json"), execution)
    return {"imported": str(target), "no_conditional_feedback": True}


def finish(study, out, root_release_sha256):
    study, out = Path(study), Path(out); load_study(study, root_release_sha256)
    if out.exists():
        raise ValueError("Never overwrite published baseline selection")
    inventory, programs, native_spawns = [], [], 0
    for run in range(4):
        seed_failed = fitness_feedback(study, run, None)["quality_covered"] is False
        for slot in range(8):
            stem = f"run_{run}_slot_{slot}"
            if seed_failed:
                inventory.append({"id": stem, "run": run, "slot": slot, "operator": OPS[slot],
                    "feedback_sha256": None, "receipt_sha256": None, "response_sha256": None,
                    "status": "unissued_seed_execution_failure"})
                continue
            feedback = fitness_feedback(study, run, slot)
            receipt = read(study / "calls" / stem / "receipt.json")
            if receipt["response_sha256"] != digest(study / "calls" / stem / "response.json"):
                raise ValueError("Original published response changed before final freeze")
            native_spawns += receipt.get("exit_code") is not None
            inventory.append({"id": stem, "run": run, "slot": slot, "operator": OPS[slot],
                "feedback_sha256": digest(study / "fitness" / f"run_{run}" / f"slot_{slot}.json"),
                "receipt_sha256": digest(study / "calls" / stem / "receipt.json"),
                "response_sha256": receipt["response_sha256"], "status": feedback["status"]})
        pop = [] if seed_failed else history_population(study, run, 8)
        best = pop[0] if pop else None
        programs.append({"id": f"published_EoH_DSL_quality:run_{run}", "run": run,
            "role": "nonguarded_published_quality_baseline", "joint_gate_required": False,
            "program": best["program"] if best else None, "program_sha256": canonical(best["program"]) if best else None,
            "source_id": best["id"] if best else None,
            "winner_origin": "shared_R1_warm_seed" if best and best["id"].endswith(":warm_seed") else "genuine_EoH_author_slot" if best else "missing",
            "TRAIN_label_selected_seed_history": True, "gate_fit_not_used_for_selection": True})
    write(out, {"version": "v06_published_EoH_DSL_TRAIN_quality_selection_001", "programs": programs,
        "original_positions": inventory, "requested_positions": 32, "all32_positions_frozen": True,
        "native_CLI_spawned_attempts": native_spawns,
        "root_authoring_release_sha256": root_release_sha256, "protocol_sha256": digest(study / "protocol.json"),
        "no_retry_or_fallback_authored_output": True, "TEST_accessed": False,
        "future_performance_registration_required": True})
    return {"selection": str(out), "identities": 4, "TEST_accessed": False}


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="mode", required=True)
    q = sub.add_parser("prepare")
    for n in ("config", "seed", "common-context", "train-inputs", "kernel-config", "transport-binding", "out"):
        q.add_argument("--" + n, required=True)
    q = sub.add_parser("request")
    for n in ("study", "out", "root-release-sha256"):
        q.add_argument("--" + n, required=True)
    q.add_argument("--run", type=int, required=True); q.add_argument("--slot", type=int)
    q = sub.add_parser("evaluate")
    for n in ("study", "request", "out", "root-release-sha256"):
        q.add_argument("--" + n, required=True)
    q.add_argument("--call-directory")
    q = sub.add_parser("ingest")
    for n in ("study", "request", "result", "feedback-sha256", "root-release-sha256"):
        q.add_argument("--" + n, required=True)
    q = sub.add_parser("finish")
    for n in ("study", "out", "root-release-sha256"):
        q.add_argument("--" + n, required=True)
    args = vars(p.parse_args()); mode = args.pop("mode")
    action = {"prepare": prepare, "request": make_request, "evaluate": evaluate, "ingest": ingest, "finish": finish}[mode]
    print(json.dumps(action(**args), ensure_ascii=False))


if __name__ == "__main__":
    main()
