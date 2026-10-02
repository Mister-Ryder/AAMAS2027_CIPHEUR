"""Offline joint representation/rule synthesis on prepared development splits.

python -m cipheur.joint_pipeline --prepared-run RUN --config CONFIG --output NEW
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import shutil
import statistics
import time

from .experiments import evaluate_program
from .feature_provider import feature_program_schema, generate_feature_candidate
from .graph_features import FeatureRuleProgram, graph_operation_library
from .providers import ProviderError
from .representation import diagnose_representation, ranking_report


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _settings(config, prepared_config):
    rounds = config.get("rounds", 1)
    if type(rounds) is not int or not 1 <= rounds <= 100:
        raise ValueError("rounds must be an integer in [1, 100]")
    selection = {**prepared_config.get("selection", {}), **config.get("selection", {})}
    threshold = selection.get("min_spec_fraction", 0.75)
    penalty = selection.get("cost_penalty", 0.002)
    if (type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1
            or type(penalty) not in (int, float) or not math.isfinite(penalty) or penalty < 0):
        raise ValueError("Selection threshold and cost penalty must be finite and valid")
    budget = config.get("provider_budget", {})
    max_http = budget.get("max_http_attempts", rounds)
    max_seconds = budget.get("max_seconds")
    if type(max_http) is not int or max_http < 0:
        raise ValueError("max_http_attempts must be a nonnegative integer")
    if max_seconds is not None and (type(max_seconds) not in (int, float)
                                    or not math.isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError("max_seconds must be a positive finite number")
    reference_nodes = config.get("reference_max_nodes", prepared_config.get("reference_max_nodes", 100000))
    if type(reference_nodes) is not int or reference_nodes < 0:
        raise ValueError("reference_max_nodes must be a nonnegative integer")
    providers = config.get("providers")
    if providers is not None:
        if not isinstance(providers, list) or not providers or any(not isinstance(p, dict) for p in providers):
            raise ValueError("providers must be a nonempty list of provider configurations")
    elif not isinstance(config.get("provider"), dict):
        raise ValueError("A provider or providers list must be explicitly configured")
    return rounds, threshold, penalty, max_http, max_seconds, reference_nodes


def _assessment(program, specifications, validation, references, reference_nodes,
                threshold, penalty, base_work=None):
    rankings = ranking_report(program, specifications)
    diagnosis = diagnose_representation(program, specifications)
    rows = evaluate_program(program, validation, references, reference_nodes)
    quality = statistics.fmean(row["ratio"] for row in rows)
    work = statistics.fmean(row["feature_work"] for row in rows)
    normalization = work if base_work is None else base_work
    utility = quality - penalty * (work / max(normalization, 1) - 1)
    eligible = (not diagnosis["contradictory"] and
                (rankings["fraction"] is None or rankings["fraction"] >= threshold))
    return {"name": program.name, "spec_fraction": rankings["fraction"],
            "contradictory": diagnosis["contradictory"], "quality": quality,
            "feature_work": work, "utility": utility, "eligible": eligible,
            "rankings": rankings, "diagnosis": diagnosis, "validation": rows,
            "all_schedules_feasible": all(row["feasible"] for row in rows)}


def _request(training_request, incumbent, assessment, specifications, history, threshold, penalty):
    system = training_request.get("system", "Synthesize a typed graph feature and safe ranking-rule pair.")
    system += (" Return exactly one JSON object containing name, features, rule, and rationale. "
               "Use the typed graph-operation library; at most six features, at most 48 expression "
               "nodes and depth eight. Only declared feature names and safe numeric arithmetic, "
               "comparisons, conditionals, min/max/abs are allowed in the rule. "
               "Repair exact representation contradictions using the structural witnesses before "
               "tuning a scoring rule. Scheduling execution cannot call an LLM or an optimization oracle.")
    payload = {"scope": "training_evidence_and_validation_only_no_test_access",
               "prepared_training_context": training_request.get("user", {}),
               "incumbent": incumbent.to_dict(), "specifications": specifications,
               "current_representation_diagnosis": assessment["diagnosis"],
               "structural_witnesses": assessment["diagnosis"]["structural_witnesses"],
               "ranking_checks": assessment["rankings"], "operations": graph_operation_library(),
               "validation_summary": {name: assessment[name] for name in
                                      ("quality", "feature_work", "utility", "eligible")},
               "selection": {"min_spec_fraction": threshold, "cost_penalty": penalty},
               "previous_attempts": history[-8:]}
    return {"system": system, "user": json.dumps(payload, ensure_ascii=False, allow_nan=False),
            "schema": feature_program_schema()}


def _provider_at(config, index, config_root):
    if "providers" in config:
        if index >= len(config["providers"]):
            return None
        provider = dict(config["providers"][index])
    else:
        provider = dict(config["provider"])
    if provider.get("type") == "replay" and isinstance(provider.get("path"), str):
        source = Path(provider["path"])
        provider["path"] = str(source if source.is_absolute() else (config_root / source).resolve())
    return provider


def run(prepared_run, config, output):
    """Run autonomous, budgeted development rounds and export a frozen program.

    ``config`` may be a JSON path or a dictionary. Relative replay paths resolve
    against the configuration file, or the current directory for dictionaries.
    No test split, held-out certificate, or test metric is inspected.
    """
    prepared, target = Path(prepared_run).resolve(), Path(output).resolve()
    if target.exists():
        raise ValueError("Use a fresh output directory; earlier synthesis runs are never overwritten")
    if isinstance(config, (str, Path)):
        config_path = Path(config).resolve()
        config_root, config = config_path.parent, _load(config_path)
    else:
        config_root = Path.cwd()
    if not isinstance(config, dict):
        raise ValueError("Joint synthesis configuration must be a dictionary")
    prepared_config = _load(prepared / "config.json")
    settings = _settings(config, prepared_config)
    rounds, threshold, penalty, max_http, max_seconds, reference_nodes = settings
    specifications = _load(prepared / "train_specifications.json")
    training_request = _load(prepared / "training_request.json")
    # Deserialization necessarily parses data.json as a whole; subsequent access
    # is restricted to the declared development keys. No test record is touched.
    serialized = _load(prepared / "data.json")
    development = {"train": serialized["train"], "validation": serialized["validation"]}
    del serialized
    if not development["validation"]:
        raise ValueError("Joint selection requires a nonempty validation split")
    initial = config.get("initial_program", {"name": "initial_weight", "features": [],
                                            "rule": "weight", "rationale": "Static initial baseline"})
    incumbent = FeatureRuleProgram.from_dict(initial)
    target.mkdir(parents=True)
    started = time.monotonic()
    _save(target / "config.json", config)
    _save(target / "development_data.json", development)
    _save(target / "train_specifications.json", specifications)
    _save(target / "prepared_training_request.json", training_request)
    references, assessments, history = {}, [], []
    current = _assessment(incumbent, specifications, development["validation"], references,
                          reference_nodes, threshold, penalty)
    base_work = current["feature_work"]
    current["round"] = -1
    assessments.append(current)
    _save(target / "initial_assessment.json", current)
    counters = {"http_generation_attempts": 0, "automated_llm_calls": 0,
                "external_llm_commands": 0, "replay_calls": 0,
                "provider_failures": 0, "candidate_rejections": 0}
    stop_reason = "round_budget_complete"
    for index in range(rounds):
        remaining_seconds = None if max_seconds is None else max_seconds - (time.monotonic() - started)
        if remaining_seconds is not None and remaining_seconds <= 0:
            stop_reason = "wall_time_budget_exhausted"
            break
        provider = _provider_at(config, index, config_root)
        if provider is None:
            stop_reason = "configured_provider_sequence_complete"
            break
        is_http = provider.get("type") in ("openai_responses", "openai_compatible")
        if is_http and counters["http_generation_attempts"] >= max_http:
            stop_reason = "http_attempt_budget_exhausted"
            break
        if is_http:
            counters["http_generation_attempts"] += 1
        if remaining_seconds is not None and provider.get("type") != "replay":
            configured_timeout = provider.get("timeout_seconds", 90)
            if type(configured_timeout) in (int, float) and math.isfinite(configured_timeout):
                provider["timeout_seconds"] = min(configured_timeout, remaining_seconds)
        round_root = target / f"round_{index:03d}"
        round_root.mkdir()
        request = _request(training_request, incumbent, current, specifications, history, threshold, penalty)
        _save(round_root / "request.json", request)
        event = {"round": index, "accepted": False, "provider_type": provider.get("type")}
        try:
            candidate, provenance = generate_feature_candidate(provider, request, round_root)
            _save(round_root / "candidate_response.json", candidate)
            _save(round_root / "provider_receipt.json", provenance)
            if is_http and provenance.get("live_llm") is True:
                counters["automated_llm_calls"] += 1
            elif provenance.get("backend") == "external_command" and provenance.get("live_llm") is True:
                counters["external_llm_commands"] += 1
            elif provenance.get("backend") == "replay":
                counters["replay_calls"] += 1
            program = FeatureRuleProgram.from_dict(candidate)
            assessment = _assessment(program, specifications, development["validation"], references,
                                     reference_nodes, threshold, penalty, base_work)
            assessment["round"] = index
            assessments.append(assessment)
            better = (assessment["utility"], assessment["quality"], -assessment["feature_work"]) > (
                current["utility"], current["quality"], -current["feature_work"])
            if assessment["eligible"] and (not current["eligible"] or better):
                incumbent, current = program, assessment
                event.update(accepted=True, reason="eligible_joint_selection")
            else:
                counters["candidate_rejections"] += 1
                reason = ("representation_contradiction" if assessment["contradictory"] else
                          "specification_threshold_not_met" if not assessment["eligible"] else
                          "no_validation_utility_improvement")
                event["reason"] = reason
            event.update(candidate=program.to_dict(), spec_fraction=assessment["spec_fraction"],
                         contradictory=assessment["contradictory"], quality=assessment["quality"],
                         feature_work=assessment["feature_work"], utility=assessment["utility"])
            _save(round_root / "assessment.json", {**assessment, "accepted": event["accepted"],
                                                    "reason": event["reason"]})
        except ProviderError as error:
            counters["provider_failures"] += 1
            event.update(reason="provider_or_typed_validation_failure", error=str(error))
            _save(round_root / "failure.json", event)
        except (ValueError, TypeError, ArithmeticError, KeyError) as error:
            counters["candidate_rejections"] += 1
            event.update(reason="candidate_evaluation_failure", error=type(error).__name__)
            _save(round_root / "failure.json", event)
        history.append(event)
        _save(target / "events.json", history)
    _save(target / "candidate_assessments.json", assessments)
    _save(target / "validation_reference_bounds.json", references)
    _save(target / "selected_program.json", incumbent.to_dict())
    _save(target / "selected_assessment.json", current)
    status = "completed" if current["eligible"] else "no_eligible_candidate"
    summary = {"status": status, "selected": incumbent.name, "selected_is_eligible": current["eligible"],
               "representation_repaired": not current["contradictory"], "stop_reason": stop_reason,
               "rounds_completed": len(history), "selection": {"min_spec_fraction": threshold,
               "cost_penalty": penalty, "normalization_base_work": base_work},
               "development_counts": {key: len(value) for key, value in development.items()},
               "certified_training_specifications": len(specifications), **counters,
               "test_data_accessed": False, "online_llm_or_oracle_calls_at_deployment": 0,
               "effectiveness_validated": False, "elapsed_seconds": time.monotonic() - started}
    _save(target / "summary.json", summary)
    source_hashes = {}
    for source in sorted(Path(__file__).parent.glob("*.py")):
        destination = target / "source_snapshot" / "cipheur" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        source_hashes[source.name] = _digest(source)
    _save(target / "freeze_receipt.json", {
        "prepared_run": str(prepared), "prepared_training_artifact_sha256": {
            name: _digest(prepared / name) for name in
            ("config.json", "training_request.json", "train_specifications.json")},
        "selected_program_sha256": _digest(target / "selected_program.json"),
        "source_sha256": source_hashes, "python": platform.python_version(),
        "used_splits": ["train", "validation"], "held_out_evaluation_performed": False,
        "artifact_sha256": {path.relative_to(target).as_posix(): _digest(path)
                            for path in sorted(target.rglob("*.json"))}, **counters})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-run", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.prepared_run, args.config, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
