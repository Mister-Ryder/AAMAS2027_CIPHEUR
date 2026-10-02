"""Auditable offline pilot: prepare training evidence, freeze, then evaluate.

python -m cipheur.experiments prepare --config ... --output ...
python -m cipheur.experiments evaluate --output ... --candidates ...
"""
from __future__ import annotations
import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import statistics
import shutil
import time

from .experiment_data import make_suite
from .graph_features import FeatureRuleProgram, graph_operation_library, schedule_feature_program
from .model import Graph
from .oracle import Budget, certify_pair, solve
from .representation import diagnose_representation, ranking_report
from .v51_adapter import verify_v51_selection


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def serialize_pair(pair):
    return {**pair, "left": pair["left"].to_dict(), "right": pair["right"].to_dict()}


def certify_records(records, settings):
    budget = Budget(settings["max_calls"], settings["max_nodes"])
    specs, attempts = [], []
    for pair in records:
        before = budget.to_dict()
        spec = None
        if pair["a"] is None:
            detail = {"reason": "no_common_competing_actions"}
        else:
            left, right = Graph.from_dict(pair["left"]), Graph.from_dict(pair["right"])
            try:
                # Pilot subproblems are small: use the entire residual region.
                # The general oracle still supports progressive local regions.
                spec, detail = certify_pair(left, right, pair["a"], pair["b"], budget,
                    pair["fixed"], pair["excluded"], initial_region=set(left.nodes),
                    max_region=max(len(left.nodes), 1), nodes_per_call=settings["nodes_per_call"],
                    include_preservation=True)
            except RuntimeError:
                detail = {"reason": "oracle_budget_exhausted"}
        attempts.append({"id": pair["id"], "family": pair["family"],
                         "relation": spec["relation"] if spec else "unknown",
                         "before": before, "after": budget.to_dict(), "detail": detail})
        if spec:
            spec.update(id=pair["id"], family=pair["family"])
            specs.append(spec)
    return specs, attempts, budget.to_dict()


def prepare(config_path, output):
    root = Path(output)
    if root.exists():
        raise ValueError("Use a fresh run directory; existing runs are never overwritten")
    config = load(config_path)
    suite = make_suite(config)
    records = {split: [serialize_pair(p) for p in suite[split]] for split in ("train", "validation", "test")}
    root.mkdir(parents=True)
    save(root / "config.json", config)
    save(root / "data.json", records)
    save(root / "data_protocol.json", {k: v for k, v in suite.items() if k not in records})
    specs, attempts, budget = certify_records(records["train"], config["oracle"])
    save(root / "train_specifications.json", specs)
    save(root / "train_acquisition.json", {"attempts": attempts, "budget": budget})
    base = FeatureRuleProgram("initial_weight", [], "weight")
    diagnosis = diagnose_representation(base, specs)
    request = {"system": "Synthesize a typed graph feature/ranking pair for static weighted independent-set scheduling. Use only provided offline training evidence and graph operations. Never call an oracle at deployment.",
               "user": {"diagnosis": diagnosis, "specifications": specs,
                        "operations": graph_operation_library(),
                        "selection": config["selection"]},
               "provenance": config["synthesis_provenance"]}
    save(root / "training_request.json", request)
    save(root / "initial_diagnosis.json", diagnosis)
    print(json.dumps({"prepared": str(root), "split_counts": {s: len(p) for s, p in records.items()},
                      "certified": len(specs), "budget": budget,
                      "initial_contradictory": diagnosis["contradictory"]}))


def evaluate_program(program, records, references=None, reference_nodes=100000):
    rows = []
    for pair in records:
        for side in ("left", "right"):
            graph = Graph.from_dict(pair[side])
            key = pair["id"] + ":" + side
            started = time.perf_counter()
            result = schedule_feature_program(graph, program, pair["fixed"], pair["excluded"])
            seconds = time.perf_counter() - started
            if references is not None and key in references:
                reference = references[key]
            else:
                bound = solve(graph, fixed=pair["fixed"], excluded=pair["excluded"], max_nodes=reference_nodes)
                reference = {"lower": bound.lower, "upper": bound.upper, "exact": bound.exact,
                             "expanded": bound.expanded}
                if references is not None:
                    references[key] = reference
            rows.append({"program": program.name, "id": pair["id"], "side": side,
                         "family": pair["family"], "n": len(graph.nodes), "m": len(graph.edges),
                         "value": result["value"], "ratio": result["value"] / reference["upper"] if reference["upper"] else 1.0,
                         "reference_exact": reference["exact"], "reference_lower": reference["lower"],
                         "reference_upper": reference["upper"], "feasible": result["feasible"],
                         "feature_work": result["feature_work"], "feature_seconds": result["feature_seconds"],
                         "scoring_seconds": result["scoring_seconds"], "seconds": seconds,
                         "selected": result["selected"]})
    return rows


def aggregate(rows):
    groups = {"all": rows}
    for family in sorted({row["family"] for row in rows}):
        groups[family] = [row for row in rows if row["family"] == family]
    return {family: {"contexts": len(part), "pairs": len({r["id"] for r in part}),
                     "mean_ratio": statistics.fmean(r["ratio"] for r in part),
                     "mean_seconds": statistics.fmean(r["seconds"] for r in part),
                     "mean_feature_work": statistics.fmean(r["feature_work"] for r in part),
                     "exact_references": sum(r["reference_exact"] for r in part),
                     "feasible": sum(r["feasible"] for r in part)}
            for family, part in groups.items() if part}


def evaluate(output, candidates_path):
    root = Path(output)
    if (root / "frozen_programs.json").exists():
        raise ValueError("Run already frozen/evaluated; use a new run for follow-up experiments")
    config, data = load(root / "config.json"), load(root / "data.json")
    bank = load(candidates_path)
    programs = [FeatureRuleProgram.from_dict(candidate) for candidate in bank["candidates"]]
    if len({p.name for p in programs}) != len(programs):
        raise ValueError("Candidate names must be unique")
    save(root / "candidate_bank.json", bank)
    specs = load(root / "train_specifications.json")
    refs, assessments = {}, []
    for index, program in enumerate(programs):
        report = ranking_report(program, specs)
        diagnosis = diagnose_representation(program, specs)
        rows = evaluate_program(program, data["validation"], refs, config["reference_max_nodes"])
        quality = statistics.fmean(r["ratio"] for r in rows)
        work = statistics.fmean(r["feature_work"] for r in rows)
        assessments.append({"candidate": index, "name": program.name, "spec_fraction": report["fraction"],
                            "contradictory": diagnosis["contradictory"], "quality": quality, "feature_work": work,
                            "ranking_checks": report["checks"], "validation": aggregate(rows),
                            "origin": bank.get("candidate_origins", {}).get(program.name, "assistant")})
    base_work = assessments[0]["feature_work"]
    penalty = config["selection"]["cost_penalty"]
    for row in assessments:
        row["utility"] = row["quality"] - penalty * (row["feature_work"] / max(base_work, 1) - 1)
    save(root / "candidate_assessments.json", assessments)
    def choose(pool):
        return max(pool, key=lambda r: (r["utility"], r["quality"], -r["feature_work"], -r["candidate"]))
    threshold = config["selection"]["min_spec_fraction"]
    eligible = [r for r in assessments if (r["spec_fraction"] is None or r["spec_fraction"] >= threshold)]
    # Targeted representation repair first discards representations with exact
    # contradictions. Free joint search receives the identical bank/evidence/
    # evaluations and uses specifications without the alias-diagnosis gate.
    targeted = [r for r in eligible if not r["contradictory"]]
    if not targeted:
        raise ValueError("No representation-repaired candidate meets the declared specification threshold")
    rule_only = [r for r in assessments if not programs[r["candidate"]].features]
    non_llm = [r for r in assessments if r["origin"] == "enumerated"]
    selected = {"targeted_joint": choose(targeted), "free_joint": choose(eligible),
                "quality_only_joint": choose(assessments), "rule_only": choose(rule_only),
                "non_llm_enumeration": choose(non_llm),
                "weight": assessments[0], "weight_degree": assessments[1], "weighted_conflict": assessments[2]}
    frozen = {name: programs[row["candidate"]].to_dict() for name, row in selected.items()}
    # Save every training/validation selection result and hash BEFORE touching
    # held-out objective values or certificates. One program per method applies
    # to every test instance and configuration.
    save(root / "selection.json", {"methods": selected, "cost_penalty": penalty, "threshold": threshold,
        "pool_sizes": {"shared_bank": len(assessments), "eligible": len(eligible), "targeted": len(targeted),
                       "rule_only": len(rule_only), "non_llm_enumeration": len(non_llm)},
        "comparison_scope": "Shared-bank selection ablation; not independent free-form LLM search"})
    save(root / "frozen_programs.json", frozen)
    source_files = sorted(Path(__file__).parent.glob("*.py"))
    for path in source_files:
        snapshot = root / "source_snapshot" / "cipheur" / path.name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, snapshot)
    save(root / "freeze_receipt.json", {"data_sha256": digest(root / "data.json"),
        "candidate_bank_sha256": digest(root / "candidate_bank.json"),
        "frozen_programs_sha256": digest(root / "frozen_programs.json"),
        "config_sha256": digest(root / "config.json"),
        "evidence_and_selection_sha256": {name: digest(root / name) for name in
            ("train_specifications.json", "train_acquisition.json", "training_request.json",
             "initial_diagnosis.json", "selection.json", "candidate_assessments.json")},
        "source_sha256": {p.name: digest(p) for p in source_files},
        "python": platform.python_version(), "platform": platform.platform(),
        "test_evaluation_started_after_freeze": True,
        "automated_llm_calls": config["synthesis_provenance"]["automated_llm_calls"]})
    test_specs, test_attempts, test_budget = certify_records(data["test"], config["oracle"])
    save(root / "test_specifications.json", test_specs)
    save(root / "test_acquisition.json", {"attempts": test_attempts, "budget": test_budget})
    test_refs, all_rows, summaries, reports = {}, [], {}, {}
    for method, candidate in frozen.items():
        program = FeatureRuleProgram.from_dict(candidate)
        rows = evaluate_program(program, data["test"], test_refs, config["reference_max_nodes"])
        for row in rows:
            row["method"] = method
        all_rows.extend(rows)
        summaries[method] = aggregate(rows)
        reports[method] = ranking_report(program, test_specs)
    save(root / "test_metrics.json", all_rows)
    save(root / "summary.json", {"test": summaries, "specifications": reports, "test_budget": test_budget,
                                 "selection_names": {k: v["name"] for k, v in frozen.items()}})
    save(root / "test_reference_bounds.json", test_refs)
    runtime_pairs = {p["id"]: p for p in make_suite(config)["test"] if p["family"] == "c3"}
    source_checks = []
    for row in all_rows:
        if row["family"] != "c3":
            continue
        pair = runtime_pairs[row["id"]]
        graph = pair[row["side"]]
        serialized = next(p[row["side"]] for p in data["test"] if p["id"] == row["id"])
        if graph.digest() != Graph.from_dict(serialized).digest():
            raise ValueError("Source-derived graph changed before independent legacy verification")
        checked = verify_v51_selection(graph, row["selected"])
        if not checked["feasible"]:
            raise AssertionError("Original V51 verifier rejected a schedule")
        source_checks.append({"method": row["method"], "id": row["id"], "side": row["side"], **checked})
    save(root / "legacy_verification.json", source_checks)
    csv_fields = [k for k in all_rows[0] if k != "selected"] if all_rows else []
    with (root / "test_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    save(root / "result_receipt.json", {p.name: digest(p) for p in root.glob("*.json") if p.name != "result_receipt.json"})
    print(json.dumps({"run": str(root), "selected": {k: p["name"] for k, p in frozen.items()},
                      "test": {k: v["all"]["mean_ratio"] for k, v in summaries.items()},
                      "test_certified": len(test_specs)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "evaluate"))
    parser.add_argument("--config")
    parser.add_argument("--output", required=True)
    parser.add_argument("--candidates")
    args = parser.parse_args()
    if args.phase == "prepare":
        if not args.config:
            parser.error("prepare requires --config")
        prepare(args.config, args.output)
    else:
        if not args.candidates:
            parser.error("evaluate requires --candidates")
        evaluate(args.output, args.candidates)


if __name__ == "__main__":
    main()
