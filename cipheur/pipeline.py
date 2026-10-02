from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import shutil
import sys
import time

from .acquisition import acquire
from .model import Contact, Graph, reversal_fixture, temporal_graph
from .oracle import Budget
from .programs import FEATURES, PROGRAM_SCHEMA, Program, features, requirement_report, schedule
from .providers import generate_candidate, ProviderError


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def sha_file(path):
    return sha256(path.read_bytes()).hexdigest()


def write_receipt(output, source_hashes, train, validation, provider, scope):
    receipt = {"created_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
               "python": sys.version, "source_sha256": source_hashes,
               "data_graph_sha256": [g.digest() for g in train + validation],
               "artifact_sha256": {str(p.relative_to(output)): sha_file(p)
                                   for p in sorted(output.rglob("*")) if p.is_file() and p.name != "receipt.json"},
               "provider": provider, "scope": scope}
    write_json(output / "receipt.json", receipt)


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    config["_config_path"] = str(Path(path).resolve())
    return config


def resolve_path(config, value):
    path = Path(value)
    return path if path.is_absolute() else Path(config["_config_path"]).parent / path


def dataset(config):
    spec = config.get("data", {"type": "synthetic"})
    if spec["type"] == "v51":
        from .v51_adapter import load_v51_pair
        pairs = [load_v51_pair(Path(spec["stable_root"]),
                              Path(spec["csv_path"]) if spec.get("csv_path") else None,
                              limit=spec.get("limit", 64), parameter=spec.get("parameter", "ground_trans_time"),
                              before=spec.get("before", 340), after=spec.get("after", 500))]
    elif spec["type"] == "synthetic":
        pairs = [reversal_fixture(scale, f"_{i}") for i, scale in enumerate((1.0, 1.25, 0.8))]
    else:
        raise ValueError("Unknown data type")
    # Training environments support witness acquisition; validation environments
    # support candidate ranking. This smoke suite is NOT a test/generalization benchmark.
    train = [graph for pair in pairs for graph in pair]
    rng = random.Random(config.get("seed", 7))
    validation = []
    for k in range(3):
        contacts = [Contact(f"v{k}_{i}", rng.randint(2, 12), f"s{rng.randrange(3)}",
                            f"g{rng.randrange(3)}", start := rng.randrange(8),
                            start + rng.randrange(1, 4)) for i in range(10)]
        validation.append(temporal_graph(f"synthetic_validation_{k}", contacts, station_gap=k))
    return pairs, train, validation


def evaluate(program, witnesses, train, validation):
    requirements = requirement_report(program, witnesses)
    rows = [{"split": split, "graph": g.name, **schedule(g, program)}
            for split, graphs in (("train", train), ("validation", validation)) for g in graphs]
    return {"requirements": requirements, "schedules": rows,
            "validation_value": sum(r["value"] for r in rows if r["split"] == "validation"),
            "train_value": sum(r["value"] for r in rows if r["split"] == "train")}


def build_request(incumbent, witnesses, report, feedback="paired", max_prompt_witnesses=8, previous_attempts=()):
    compact = []
    for witness in witnesses[-max_prompt_witnesses:]:
        entry = {k: witness[k] for k in ("intervention", "a", "b", "region", "certificate_scope")}
        entry["bounds"] = {key: {field: value[field] for field in ("lower", "upper", "exact")}
                           for key, value in witness["bounds"].items()}
        entry["contexts"] = []
        for side in ("left", "right"):
            graph = Graph.from_dict(witness[side])
            active = graph.available(witness["fixed"], witness["excluded"])
            entry["contexts"].append({"side": side, "constraints": graph.constraints,
                                      "preferred": witness[side + "_preferred"],
                                      "features": {v: features(graph, v, active) for v in (witness["a"], witness["b"])}})
        compact.append(entry)
    if feedback == "scalar":
        compact = []
    elif feedback == "unpaired":
        compact = [context for w in compact for context in w["contexts"]]
    elif feedback != "paired":
        raise ValueError("Unknown feedback mode")
    system = ("You synthesize a compact state-dependent priority expression for a fixed greedy MWIS kernel. "
              "Return only a JSON object matching the supplied schema. Do not solve instances directly. "
              "Use numeric literals, arithmetic + - * /, comparisons, conditional expressions, min/max/abs. "
              "Only these feature names are allowed: " + ", ".join(FEATURES) + ". "
              "No imports, attributes, loops, file/network access, action ids, or instance-name rules. "
              "Strict paired requirements must both hold; a feasible kernel is guaranteed separately. "
              "Avoid near-zero division and excessive program size.")
    payload = {"incumbent": incumbent.to_dict(), "feedback_mode": feedback,
               "evidence": compact, "incumbent_validation_value": report["validation_value"],
               "incumbent_training_value": report["train_value"],
               "requirement_checks": report["requirements"] if feedback == "paired" else None,
               "previous_attempts": list(previous_attempts)[-3:],
               "scope": "development_only_no_test_data"}
    return {"system": system, "user": json.dumps(payload, ensure_ascii=False), "schema": PROGRAM_SCHEMA}


def preflight(config):
    if type(config.get("rounds", 2)) is not int or not 1 <= config.get("rounds", 2) <= 100:
        raise ValueError("rounds must be an integer in [1, 100]")
    pairs, train, validation = dataset(config)
    for g in train + validation:
        if not g.feasible([]):
            raise ValueError("Invalid graph")
    provider = config.get("provider", {})
    if provider.get("type") == "replay":
        path = resolve_path(config, provider["path"])
        Program(**json.loads(path.read_text(encoding="utf-8-sig")))
    return {"status": "ready", "python": sys.version.split()[0],
            "provider": provider.get("type"), "pair_count": len(pairs),
            "train_graphs": len(train), "validation_graphs": len(validation),
            "claims": "data_and_interfaces_only_no_effectiveness_validation"}


def run(config, output):
    output = Path(output).resolve()
    # A run is immutable: never overwrite earlier provenance and model records.
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    write_json(output / "config.json", config)
    write_json(output / "preflight.json", preflight(config))
    source_root = Path(__file__).resolve().parent.parent
    source_hashes = {}
    for folder in ("cipheur", "tests", "configs", "examples"):
        for source in sorted((source_root / folder).rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts and source.suffix in (".py", ".json"):
                relative = source.relative_to(source_root)
                target = output / "source_snapshot" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                source_hashes[str(relative)] = sha_file(source)
    pairs, train, validation = dataset(config)
    write_json(output / "graphs.json", {"pairs": [[g.to_dict() for g in pair] for pair in pairs],
                                         "validation": [g.to_dict() for g in validation]})
    budget_config = config.get("oracle", {})
    budget = Budget(budget_config.get("max_calls", 80), budget_config.get("max_nodes", 100000))
    incumbent = Program("weight", "weight", "Static baseline; no LLM call")
    archive, witnesses, acquisition_log, events = [], [], [], []
    live_calls = external_commands = 0
    def event(kind, **fields):
        item = {"event": kind, **fields}
        events.append(item)
        with (output / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False, allow_nan=False) + "\n")
    event("started", purpose="smoke_integration_only", provider=config["provider"]["type"])
    for round_index in range(config.get("rounds", 2)):
        acquisition = config.get("acquisition", {})
        fresh, attempts = acquire(pairs, incumbent, budget,
                                  max_attempts=acquisition.get("max_attempts", 6),
                                  max_witnesses=acquisition.get("max_witnesses", 3),
                                  strategy=acquisition.get("strategy", "disagreement"),
                                  max_region=budget_config.get("max_region", 64),
                                  nodes_per_call=budget_config.get("nodes_per_call", 10000),
                                  known_keys={(w["left"]["name"], w["right"]["name"], w["a"], w["b"]) for w in witnesses})
        acquisition_log.extend(attempts)
        for witness in fresh:
            key = (witness["left"]["name"], witness["right"]["name"], witness["a"], witness["b"])
            old_keys = {(w["left"]["name"], w["right"]["name"], w["a"], w["b"]) for w in witnesses}
            if key not in old_keys:
                witnesses.append(witness)
        # Re-evaluate every archived program against all requirements, including new evidence.
        pool = [incumbent] + [Program(**c["program"]) for c in archive if c.get("valid_program")]
        scored = [(p, evaluate(p, witnesses, train, validation)) for p in pool]
        eligible = [(p, r) for p, r in scored if r["requirements"]["all_passed"]]
        if eligible:
            incumbent, incumbent_report = max(eligible, key=lambda pr: (pr[1]["validation_value"], -len(pr[0].expression)))
        else:
            incumbent_report = evaluate(incumbent, witnesses, train, validation)
        round_dir = output / f"round_{round_index:03d}"
        round_dir.mkdir()
        request = build_request(incumbent, witnesses, incumbent_report,
                                config.get("feedback", "paired"), previous_attempts=[
            {"program": c.get("program"), "accepted": c["accepted"], "error": c.get("error"),
             "requirements": c.get("report", {}).get("requirements") if config.get("feedback", "paired") == "paired" else None,
             "validation_value": c.get("report", {}).get("validation_value")} for c in archive])
        write_json(round_dir / "request.json", request)
        provider = dict(config["provider"])
        if provider["type"] == "replay":
            provider["path"] = str(resolve_path(config, provider["path"]).resolve())
        try:
            candidate_dict, metadata = generate_candidate(provider, request, round_dir)
            live_calls += int(metadata.get("live_llm", False))
            external_commands += int(metadata.get("backend") == "external_command")
            write_json(round_dir / "provider.json", metadata)
            write_json(round_dir / "candidate_response.json", candidate_dict)
            try:
                candidate = Program(**candidate_dict)
                report = evaluate(candidate, witnesses, train, validation)
            except (ValueError, SyntaxError, TypeError) as error:
                record = {"round": round_index, "program": candidate_dict, "valid_program": False,
                          "accepted": False, "error": str(error), "provider": metadata}
                archive.append(record)
                write_json(round_dir / "assessment.json", record)
                event("candidate_rejected_invalid", round=round_index, error=str(error))
                continue
            satisfies = report["requirements"]["all_passed"]
            incumbent_satisfies = incumbent_report["requirements"]["all_passed"]
            accepted = satisfies and (not incumbent_satisfies or report["validation_value"] >= incumbent_report["validation_value"])
            record = {"round": round_index, "program": candidate.to_dict(), "report": report,
                      "valid_program": True, "accepted": accepted, "provider": metadata}
            archive.append(record)
            write_json(round_dir / "candidate.json", candidate.to_dict())
            write_json(round_dir / "assessment.json", record)
            if accepted:
                incumbent, incumbent_report = candidate, report
            event("candidate_assessed", round=round_index, accepted=accepted,
                  requirement_passed=report["requirements"]["passed"],
                  requirement_total=report["requirements"]["total"])
        except (ProviderError, ValueError, SyntaxError, TypeError) as error:
            # Failure is visible and ends the run; never substitute a pretend model result.
            event("candidate_failed", round=round_index, error=str(error))
            write_json(output / "failure.json", {"error": str(error), "round": round_index,
                                                  "oracle": budget.to_dict()})
            write_json(output / "witnesses.json", witnesses)
            write_json(output / "acquisition.json", acquisition_log)
            write_json(output / "archive.json", archive)
            write_receipt(output, source_hashes, train, validation, config["provider"]["type"], "failed_development_smoke")
            raise
    final_report = evaluate(incumbent, witnesses, train, validation)
    write_json(output / "selected_program.json", incumbent.to_dict())
    write_json(output / "witnesses.json", witnesses)
    write_json(output / "acquisition.json", acquisition_log)
    write_json(output / "archive.json", archive)
    write_json(output / "assessment.json", final_report)
    summary = {"status": "completed", "purpose": "smoke_integration_only",
               "effectiveness_validated": False, "live_llm_calls": live_calls,
               "external_command_calls": external_commands, "witness_count": len(witnesses),
               "selected_program": incumbent.to_dict(), "requirements": final_report["requirements"],
               "all_schedules_feasible": all(r["feasible"] for r in final_report["schedules"]),
               "oracle": budget.to_dict(), "elapsed_seconds": time.perf_counter() - started,
               "formal_test_split_used": False}
    summary["paired_signal_available"] = bool(witnesses)
    summary["selected_program_satisfies_certified_pairs"] = bool(witnesses) and final_report["requirements"]["all_passed"]
    summary["provider_attempts"] = len(archive)
    summary["candidate_rejections"] = sum(not c["accepted"] for c in archive)
    write_json(output / "summary.json", summary)
    event("completed", witness_count=len(witnesses), live_llm_calls=live_calls)
    write_receipt(output, source_hashes, train, validation, config["provider"]["type"], "development_smoke")
    return summary
