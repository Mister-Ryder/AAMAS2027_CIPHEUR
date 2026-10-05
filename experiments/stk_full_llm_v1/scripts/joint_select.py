"""Predeclared TRAIN Pareto shortlist and quality-first VALIDATION selection.

No optimizer, graph loader or model is called. This module reads paid result
records only. Register the rule before reading candidate schedule outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path

from train_context import CONDITIONS, SOURCES, encoded, digest, freeze_json, require

ROOT = Path(__file__).resolve().parents[1]
POLICY = {
    "version": "joint_shortlist_v1_pre_results",
    "TRAIN_sources": list(SOURCES), "TRAIN_configs": ["A", "W", "E", "J"],
    "TRAIN_seconds": 2, "TRAIN_seed": 2, "strict_fit_denominator": 743,
    "objectives": {
        "Q": "arithmetic mean of candidate_reward_ticks/degree_reward_ticks over all16 matched TRAIN graphs; maximize",
        "G": "passed exact deployed-score strict requirements/743; maximize",
        "C": "arithmetic mean of actual deployment meter.feature_work over the same16 TRAIN records; minimize; operation proxy, not FLOPs",
    },
    "shortlist_groups": "one pool per LLM arm/batch across rounds; one32-candidate nonLLM_grammar pool",
    "maximum_distinct_contents_per_group": 4,
    "paid_duplicates": "retain all paid result records; same program_content_sha256 represented by lexicographically smallest eligible id within group",
    "algorithm": "non-dominated layers; in each layer prioritize max Q, max G, min C endpoints in that order, then minimum sum of three competition ordinal ranks within that layer; repeat next layer until4; every tie resolved by lexicographic id",
    "ineligible": "missing or nonfeasible full schedule, not all16 graphs, wrong budget/seed/split, missing actual feature_work, missing exact743 fit; retain explicit reasons and never reduce denominators",
    "programme_errors": "feasible guarded fallback records remain in objectives with actual measured quality/cost; expose errors and zero-commit counts",
    "VALIDATION_sources": ["CP-AU-r006", "CP-AP-r006"],
    "VALIDATION_configs": ["A", "W", "E", "J"],
    "VALIDATION_seconds": [2, 10], "VALIDATION_seeds": [2],
    "VALIDATION_rule": "one final per fixed shortlist group by mean per-graph reward/degree over8 graphs x2 budgets; equal exact quality only: higher TRAIN G, lower TRAIN C, lexicographic id",
    "TEST_reads": False, "selection_does_not_claim_fit_implies_schedule_gain": True,
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ratio(value):
    return {"exact": str(value), "float": float(value)}


def load_banks(paths):
    items, provenance = {}, {}
    for path in paths:
        path = Path(path)
        provenance[str(path.resolve())] = digest(path)
        bank = read(path)
        for item in bank["programs"]:
            require(item["id"] not in items, "Duplicate candidate id across banks")
            items[item["id"]] = item
    return items, provenance


def content_hash(item):
    # Existing proposal banks define program content by executable features/rule;
    # naming and rationale changes do not constitute another executable program.
    import hashlib
    actual = hashlib.sha256(encoded({"features": item["program"]["features"],
                                    "rule": item["program"]["rule"]}).encode("utf-8")).hexdigest()
    require(item.get("program_content_sha256", actual) == actual, "Candidate content hash mismatch")
    return actual


def group_name(item):
    if item["arm"] == "nonllm_grammar":
        return "nonllm_grammar"
    require(item["arm"] in CONDITIONS and item.get("batch") in (0, 1), "Unregistered candidate arm/batch")
    return item["arm"] + ".b" + str(item["batch"])


def load_fit(item, roots):
    matches = [Path(root) / (item["id"] + ".json") for root in roots]
    matches = [path for path in matches if path.is_file()]
    require(len(matches) == 1, "Expected one complete743 TRAIN fit for " + item["id"])
    path = matches[0]
    value = read(path)
    require(value["split"] == "TRAIN" and value["source_ids"] == list(SOURCES)
            and not value["VAL_read"] and not value["TEST_read"], "Fit uses non-TRAIN sources")
    require(value["total_requirements"] == 743 and value["program_id"] == item["id"], "Fit identity/denominator mismatch")
    require(value["candidate_program"] == item["program"], "Fit evaluated a different candidate program")
    return value, path


def read_paid_roots(roots):
    """Return complete raw results and explicit paid failures, no hidden reruns."""
    results, failures, provenance = [], [], {}
    for root in roots:
        root = Path(root)
        summary_path = root / "execution_summary.json"
        summary = read(summary_path)
        require(not summary["missing_job_ids"] and not summary["worker_failures"], "Formal execution is incomplete")
        require(all(code == 0 for code in summary["worker_exit_codes"]), "Formal worker exited unsuccessfully")
        provenance[str(summary_path.resolve())] = digest(summary_path)
        jobs_path = root / "jobs.jsonl"
        provenance[str(jobs_path.resolve())] = digest(jobs_path)
        records = [json.loads(line) for line in jobs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        require(len(records) == summary["registered_jobs"] == summary["recorded_jobs"], "Formal job denominator mismatch")
        require(len({record["job_id"] for record in records}) == len(records), "Duplicate paid job record")
        compact_path = root / "metrics.json"
        compact = None
        if compact_path.is_file():
            projection = read(compact_path)
            require(projection["version"] == "full_schedule_metric_projection_v1"
                    and projection["all_job_count"] == len(records)
                    and projection["jobs_sha256"] == digest(jobs_path), "Compact projection does not match paid job log")
            compact = {row["job_id"]: row for row in projection["records"]}
            require(len(compact) == len(projection["records"]), "Compact projection contains duplicate job id")
            provenance[str(compact_path.resolve())] = digest(compact_path)
        for record in records:
            path = root / "results" / (record["job_id"] + ".json")
            has_result = record["job_id"] in compact if compact is not None else path.is_file()
            if record["status"] != "complete" or not has_result:
                failures.append({"job_id": record["job_id"], "program_id": record.get("program_id"),
                    "source": record["source"], "config": record["config"], "status": record["status"], "record": record})
                continue
            result = dict(compact[record["job_id"]]) if compact is not None else read(path)
            if compact is not None:
                result["raw_config"] = result["config"]
                result["config"] = result["config_alias"]
                require(result["execution_status"] == record["status"], "Compact execution status mismatch")
            require(result["source"] == record["source"] and result["config"] == record["config"]
                    and result["program_id"] == record.get("program_id"), "Paid result identity mismatch")
            require(result["feasible"] is True, "Result marked complete without feasible schedule")
            result = dict(result, paid_result_path=str(path.resolve()),
                          paid_result_sha256=result["result_sha256"] if compact is not None else digest(path),
                          paid_record=record)
            results.append(result)
    return results, failures, provenance


def train_key(row):
    require(row["split"] == "train" and row["source"] in SOURCES and row["config"] in ("A", "W", "E", "J"), "Non-TRAIN result supplied")
    require(Fraction(str(row["declared_cpu_seconds"])) == 2 and row["seed"] == 2, "TRAIN budget/seed mismatch")
    return row["source"], row["config"]


def paired_reference(rows, key_function):
    reference = {}
    for row in rows:
        if row["method"] == "degree" and not row.get("program_id"):
            key = key_function(row)
            require(key not in reference, "Degree reference repeated for matched item")
            require(row["value_ticks"] > 0, "Nonpositive degree reference reward")
            reference[key] = row
    return reference


def summarise_candidate(item, fit, rows, reference):
    mapped, reasons = {}, []
    for row in rows:
        key = train_key(row)
        require(key not in mapped, "Candidate has repeated TRAIN execution")
        require(row["execution_module_sha256"] == fit["execution_module_sha256"]
                and row["numeric_namespace"] == fit["numeric_namespace"], "Fit and deployment use different scorer semantics")
        if "program" in row:
            require(row["program"] == item["program"], "Paid candidate program differs from bank")
        # Compact projection retains the frozen bank SHA and exact program id;
        # source is the registered bank, not a reconstructed or repaired program.
        require(row.get("program_bank_sha256"), "Missing frozen paid program-bank SHA")
        mapped[key] = row
    expected = {(source, config) for source in SOURCES for config in ("A", "W", "E", "J")}
    if set(mapped) != expected:
        reasons.append("requires all16 feasible paid TRAIN schedules")
    if any("feature_work" not in row.get("meter", {}) for row in mapped.values()):
        reasons.append("missing actual deployment feature_work")
    metrics = None
    if not reasons:
        q = sum((Fraction(mapped[key]["value_ticks"], reference[key]["value_ticks"]) for key in expected), Fraction()) / 16
        c = sum((Fraction(mapped[key]["meter"]["feature_work"]) for key in expected), Fraction()) / 16
        g = Fraction(fit["passed_requirements"], 743)
        metrics = {"Q": ratio(q), "G": ratio(g), "C": ratio(c)}
    errors = sum(int(row.get("paid_record", {}).get("execution_health", {}).get("programme_error_count", 0)) for row in rows)
    return {"program_id": item["id"], "arm": item["arm"], "batch": item.get("batch"),
        "round": item.get("round"), "group": group_name(item), "program_content_sha256": content_hash(item),
        "eligible": not reasons, "ineligibility_reasons": reasons, "metrics": metrics,
        "paid_record_count": len(rows), "expected_record_count": 16,
        "programme_error_count": errors, "head_committed_record_count": sum(bool(row.get("head_ever_committed")) for row in rows),
        "strict_passed": fit["passed_requirements"], "strict_total": 743,
        "arithmetic_error_count": fit["arithmetic_error_count"],
        "per_graph": [{"source": key[0], "config": key[1], "value_ticks": row["value_ticks"],
            "degree_value_ticks": reference[key]["value_ticks"], "ratio": ratio(Fraction(row["value_ticks"], reference[key]["value_ticks"])),
            "feature_work": row.get("meter", {}).get("feature_work"), "cpu_seconds": row["cpu_seconds"],
            "wall_seconds": row["wall_seconds"], "head_ever_committed": row.get("head_ever_committed"),
            "paid_result_path": row["paid_result_path"], "paid_result_sha256": row["paid_result_sha256"]}
            for key, row in sorted(mapped.items())]}


def objectives(row):
    metrics = row["metrics"]
    return Fraction(metrics["Q"]["exact"]), Fraction(metrics["G"]["exact"]), -Fraction(metrics["C"]["exact"])


def pareto_layers(rows):
    remaining, layers = list(rows), []
    while remaining:
        layer = []
        for row in remaining:
            x = objectives(row)
            dominated = any(all(a >= b for a, b in zip(objectives(other), x))
                            and any(a > b for a, b in zip(objectives(other), x)) for other in remaining)
            if not dominated:
                layer.append(row)
        require(layer, "Pareto layer is empty")
        layers.append(sorted(layer, key=lambda row: row["program_id"]))
        ids = {row["program_id"] for row in layer}
        remaining = [row for row in remaining if row["program_id"] not in ids]
    return layers


def shortlist(rows):
    representatives, duplicates = [], []
    contents = defaultdict(list)
    for row in rows:
        if row["eligible"]:
            contents[row["program_content_sha256"]].append(row)
    for content, members in sorted(contents.items()):
        members.sort(key=lambda row: row["program_id"])
        representatives.append(members[0])
        duplicates.extend({"program_id": row["program_id"], "representative_id": members[0]["program_id"],
            "reason": "same normalized executable features/rule program_content_sha256; paid record retained"} for row in members[1:])
    layers = pareto_layers(representatives)
    selected, decisions = [], []
    for layer_index, layer in enumerate(layers):
        def add(row, why):
            if len(selected) < 4 and row["program_id"] not in selected:
                selected.append(row["program_id"])
                decisions.append({"program_id": row["program_id"], "pareto_layer": layer_index,
                                  "reason": why, "metrics": row["metrics"]})
        for axis, name in enumerate(("max Q endpoint", "max G endpoint", "min C endpoint")):
            endpoint = min(layer, key=lambda row: (-objectives(row)[axis], row["program_id"]))
            add(endpoint, name)
        ordinal = {}
        for row in layer:
            values = objectives(row)
            ranks = [1 + sum(objectives(other)[axis] > values[axis] for other in layer) for axis in range(3)]
            ordinal[row["program_id"]] = ranks
        for row in sorted(layer, key=lambda row: (sum(ordinal[row["program_id"]]), row["program_id"])):
            add(row, "minimum within-layer three-objective competition-rank sum=" + str(sum(ordinal[row["program_id"]])))
        if len(selected) >= 4:
            break
    return {"selected_ids": selected, "selection_decisions": decisions, "duplicates_retained_not_shortlisted": duplicates,
            "pareto_layers": [[row["program_id"] for row in layer] for layer in layers],
            "eligible_unique_contents": len(representatives), "paid_candidate_count": len(rows)}


def train(args):
    policy = read(args.policy)
    require(policy == POLICY, "Selection policy changed after registration")
    items, inputs = load_banks(args.program_bank)
    results, paid_failures, execution_inputs = read_paid_roots(args.execution_root)
    inputs.update(execution_inputs)
    reference_rows, _, reference_inputs = read_paid_roots([args.reference_root])
    inputs.update(reference_inputs)
    reference = paired_reference(reference_rows, train_key)
    require(len(reference) == 16, "Need all16 common paid degree references")
    by_id = defaultdict(list)
    for row in results:
        train_key(row)
        if row.get("program_id") in items:
            by_id[row["program_id"]].append(row)
    descriptors, groups = [], defaultdict(list)
    for identifier, item in sorted(items.items()):
        fit, path = load_fit(item, args.fit_root)
        inputs[str(path.resolve())] = digest(path)
        descriptor = summarise_candidate(item, fit, by_id[identifier], reference)
        descriptors.append(descriptor)
        groups[descriptor["group"]].append(descriptor)
    output = {"version": "TRAIN_joint_shortlist_v1", "split": "TRAIN", "source_ids": list(SOURCES),
        "policy_sha256": digest(args.policy), "inputs_sha256": inputs, "paid_failures": paid_failures,
        "groups": {name: shortlist(rows) for name, rows in sorted(groups.items())}, "candidates": descriptors,
        "VAL_reads": False, "TEST_reads": False, "optimizer_calls": 0, "model_calls": 0}
    freeze_json(args.output, output)
    print(json.dumps({"output": str(args.output), "groups": {name: value["selected_ids"] for name, value in output["groups"].items()}}, ensure_ascii=False))


def val_key(row):
    require(row["split"] == "val" and row["source"] in POLICY["VALIDATION_sources"] and row["config"] in POLICY["VALIDATION_configs"], "Non-VALIDATION result supplied")
    budget = Fraction(str(row["declared_cpu_seconds"]))
    require(budget in (2, 10) and row["seed"] in POLICY["VALIDATION_seeds"], "VALIDATION budget/seed not fixed")
    return row["source"], row["config"], int(budget), row["seed"]


def validate(args):
    require(read(args.policy) == POLICY, "Selection policy changed after registration")
    train_shortlist = read(args.train_shortlist)
    require(train_shortlist["split"] == "TRAIN" and train_shortlist["policy_sha256"] == digest(args.policy), "TRAIN shortlist does not match fixed rule")
    results, failures, inputs = read_paid_roots(args.execution_root)
    reference = paired_reference(results, val_key)
    expected = {(source, config, budget, seed) for source in POLICY["VALIDATION_sources"]
        for config in POLICY["VALIDATION_configs"] for budget in (2, 10) for seed in POLICY["VALIDATION_seeds"]}
    require(set(reference) == expected, "Need all16 paired degree VALIDATION references")
    permitted = {identifier for group in train_shortlist["groups"].values() for identifier in group["selected_ids"]}
    by_id = defaultdict(dict)
    for row in results:
        key = val_key(row)
        if row.get("program_id"):
            require(row["program_id"] in permitted, "Unshortlisted candidate accessed VALIDATION")
            require(key not in by_id[row["program_id"]], "Duplicate VALIDATION execution")
            by_id[row["program_id"]][key] = row
    train_metrics = {row["program_id"]: row["metrics"] for row in train_shortlist["candidates"]}
    groups, candidates = {}, {}
    for group_name_, group in train_shortlist["groups"].items():
        ranked = []
        for identifier in group["selected_ids"]:
            mapped = by_id[identifier]
            if set(mapped) != expected:
                candidates[identifier] = {"eligible": False, "reason": "incomplete feasible VALIDATION denominator", "paid_records": len(mapped)}
                continue
            q = sum((Fraction(mapped[key]["value_ticks"], reference[key]["value_ticks"]) for key in expected), Fraction()) / len(expected)
            candidates[identifier] = {"eligible": True, "VALIDATION_Q": ratio(q), "denominator": len(expected), "TRAIN_metrics": train_metrics[identifier]}
            ranked.append((q, Fraction(train_metrics[identifier]["G"]["exact"]), -Fraction(train_metrics[identifier]["C"]["exact"]), identifier))
        require(ranked, "No complete shortlisted candidate for group " + group_name_)
        ranked.sort(key=lambda value: (-value[0], -value[1], -value[2], value[3]))
        groups[group_name_] = {"selected_id": ranked[0][3], "ordered_ids": [value[3] for value in ranked],
            "selection_reason": "highest exact mean paired VALIDATION quality; only exact ties use TRAIN fit, cost, id"}
    freeze_json(args.output, {"version": "VALIDATION_final_selection_v1", "split": "VALIDATION", "groups": groups,
        "candidates": candidates, "paid_failures": failures, "inputs_sha256": inputs,
        "TRAIN_shortlist_sha256": digest(args.train_shortlist), "policy_sha256": digest(args.policy), "TEST_reads": False,
        "optimizer_calls": 0, "model_calls": 0})
    print(json.dumps({"output": str(args.output), "selected": {name: group["selected_id"] for name, group in groups.items()}}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("--output", type=Path, default=ROOT / "selection_rule.pre_results.json")
    for command in ("train", "val"):
        p = sub.add_parser(command)
        p.add_argument("--policy", type=Path, default=ROOT / "selection_rule.pre_results.json")
        p.add_argument("--execution-root", type=Path, action="append", required=True)
        p.add_argument("--output", type=Path, required=True)
        if command == "train":
            p.add_argument("--program-bank", type=Path, action="append", required=True)
            p.add_argument("--fit-root", type=Path, action="append", required=True)
            p.add_argument("--reference-root", type=Path, required=True)
        else:
            p.add_argument("--train-shortlist", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "register":
        freeze_json(args.output, POLICY)
        print(json.dumps({"policy": str(args.output), "sha256": digest(args.output), "schedule_outcomes_read": False}))
    elif args.command == "train":
        train(args)
    else:
        validate(args)


if __name__ == "__main__":
    main()
