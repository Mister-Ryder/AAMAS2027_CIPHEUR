"""Prepare condition-isolated TRAIN feedback and the final six proposal plans.

This is a read-only result summarizer, never a model or optimizer invocation.
Each arm sees only its own two first-round batches and the same classical
reference records. Non-LLM candidates and other arms are never disclosed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from types import SimpleNamespace

from train_context import CONDITIONS, SOURCES, digest, freeze_json, require
from joint_select import load_banks, load_fit, read_paid_roots, paired_reference, ratio, summarise_candidate, train_key

ROOT = Path(__file__).resolve().parents[1]
CLASSICAL = ("degree", "weight", "grasp", "local2swap", "cp_sat", "chils_ils", "chils")


def mean(values):
    return sum(values) / len(values) if values else None


def classical_view(rows, reference):
    by_method = defaultdict(list)
    for row in rows:
        train_key(row)
        if row["method"] in CLASSICAL and not row.get("program_id"):
            by_method[row["method"]].append(row)
    answer = []
    for method in CLASSICAL:
        group = by_method.get(method, [])
        mapped = {train_key(row): row for row in group}
        require(len(mapped) == len(group), "Classical reference contains a repeated graph")
        item = {"method": method, "feasible_records": len(group), "expected_records": 16,
                "complete_denominator": len(group) == 16}
        if len(group) == 16:
            item.update(mean_paired_reward_over_degree=ratio(sum((Fraction(row["value_ticks"], reference[key]["value_ticks"])
                for key, row in mapped.items()), Fraction()) / 16),
                mean_cpu_seconds=mean([row["cpu_seconds"] for row in group]),
                mean_wall_seconds=mean([row["wall_seconds"] for row in group]),
                mean_feature_work=ratio(sum((Fraction(row["meter"]["feature_work"]) for row in group), Fraction()) / 16))
        answer.append(item)
    return answer


def program_view(item, fit, descriptor, rows):
    # No cross-arm observations or extra structural witnesses are inferred.
    view = {"id": item["id"], "round": item["round"], "batch": item["batch"], "slot": item["slot"],
        "program": item["program"], "strict_fit": {"passed": fit["passed_requirements"], "total": 743,
            "fraction": ratio(Fraction(fit["passed_requirements"], 743)), "passed_by_stage": fit["passed_by_stage"],
            "total_by_stage": fit["total_by_stage"], "arithmetic_error_count": fit["arithmetic_error_count"]},
        "full_schedule_TRAIN": {"eligible_complete16": descriptor["eligible"],
            "missing_or_invalid_reasons": descriptor["ineligibility_reasons"], "metrics": descriptor["metrics"],
            "feasible_paid_records": descriptor["paid_record_count"], "expected_paid_records": 16,
            "head_committed_records": descriptor["head_committed_record_count"],
            "programme_error_count": descriptor["programme_error_count"],
            "mean_cpu_seconds": mean([row["cpu_seconds"] for row in rows]),
            "mean_wall_seconds": mean([row["wall_seconds"] for row in rows]),
            "construction_status_counts": dict(Counter(row.get("phase_statuses", {}).get("construction", {}).get("status",
                row.get("phases", {}).get("construction", {}).get("status", "unknown")) for row in rows)),
            "deadline_soft_overshoot_records": sum(bool(row.get("deadline_soft_overshoot")) for row in rows),
            "per_graph": []}}
    for row in descriptor["per_graph"]:
        view["full_schedule_TRAIN"]["per_graph"].append({key: row[key] for key in
            ("source", "config", "value_ticks", "degree_value_ticks", "ratio", "feature_work", "head_ever_committed")})
    return view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-bank", type=Path, required=True, help="The48 actual first-round LLM programs only")
    parser.add_argument("--fit-root", type=Path, required=True)
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--prepare-round2", action="store_true", help="Only writes6 plans; never executes native CLI")
    args = parser.parse_args()
    items, bank_inputs = load_banks([args.program_bank])
    require(len(items) == 48 and set(item["arm"] for item in items.values()) == set(CONDITIONS), "Feedback requires exactly the initial48 LLM programs")
    require(all(item["round"] == 1 for item in items.values()), "Feedback is permitted only once after round1")
    results, failures, execution_inputs = read_paid_roots([args.execution_root])
    reference = paired_reference(results, train_key)
    require(len(reference) == 16, "Feedback needs the same complete16 classical degree references")
    by_id = defaultdict(list)
    for row in results:
        train_key(row)
        if row.get("program_id") in items:
            by_id[row["program_id"]].append(row)
    shared_baselines = classical_view(results, reference)
    outputs, index = {}, {}
    for arm in CONDITIONS:
        own = [item for item in items.values() if item["arm"] == arm]
        own.sort(key=lambda item: (item["batch"], item["slot"]))
        require(len(own) == 16 and Counter(item["batch"] for item in own) == {0: 8, 1: 8}, "Missing first-round condition batch")
        views, inputs = [], dict(bank_inputs, **execution_inputs)
        for item in own:
            fit, path = load_fit(item, [args.fit_root])
            inputs[str(path.resolve())] = digest(path)
            descriptor = summarise_candidate(item, fit, by_id[item["id"]], reference)
            views.append(program_view(item, fit, descriptor, by_id[item["id"]]))
        own_ids = {item["id"] for item in own}
        own_failures = [{key: row.get(key) for key in ("job_id", "program_id", "source", "config", "status")}
                        for row in failures if row.get("program_id") in own_ids]
        feedback = {"version": "condition_isolated_TRAIN_feedback_v1", "split": "TRAIN", "arm": arm,
            "source_ids": list(SOURCES), "configs": ["A", "W", "E", "J"], "declared_CPU_seconds": 2, "seed": 2,
            "next_round": 2, "exactly_one_feedback_round": True, "shared_classical_reference": shared_baselines,
            "own_two_batch_candidates": views, "own_paid_failures": own_failures,
            "interpretation": "Higher fit does not establish full-schedule benefit. Q is mean of16 graph-specific rewards/degree, not ratio of pooled means. Actual feature_work is deployed operation proxy; CPU includes input/common kernel/feature computation. Feasible seed-guard fallback and programme errors remain in quality/cost. Other conditions and grammar results are withheld.",
            "representation_policy": "rule-only features remain[]" if arm == "relations_rule_only" else "unchanged full typed graph-operation library; generic current-active computation only",
            "VAL_read": False, "TEST_read": False, "other_arm_programs_or_results_supplied": False,
            "grammar_programs_or_results_supplied": False, "optimizer_calls": 0, "model_calls": 0,
            "input_evidence_sha256": inputs}
        path = args.output_root / "feedback" / (arm + ".round1.json")
        freeze_json(path, feedback)
        outputs[arm] = path
        index[arm] = {"path": str(path.resolve()), "sha256": digest(path), "own_candidates": len(views),
                      "eligible_complete16": sum(view["full_schedule_TRAIN"]["eligible_complete16"] for view in views)}
    freeze_json(args.output_root / "feedback" / "round1_index.json", {"version": "feedback_index_v1", "arms": index,
        "split": "TRAIN", "same_classical_references": True, "model_calls": 0, "optimizer_calls": 0})
    if args.prepare_round2:
        from llm_cli_proposer import prepare
        for arm in CONDITIONS:
            for batch in (0, 1):
                prepare(SimpleNamespace(output_root=args.output_root, condition=arm, round=2, batch=batch, feedback=outputs[arm], cli_executable=None))
    print(json.dumps({"feedback": index, "round2_plans_prepared": args.prepare_round2, "model_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
