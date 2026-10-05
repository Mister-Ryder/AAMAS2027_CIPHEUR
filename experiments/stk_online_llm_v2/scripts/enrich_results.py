"""Read completed raw jobs to enrich compact mechanism/cost projections.

No optimizer, model or graph solve is imported.  Each raw JSON is read once and
checked against its recorded output SHA.  Run on the server if full trial files
were not downloaded.  Missing trial evidence is an error, never fabricated zero.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_input(root):
    metrics_bytes = (root / "metrics.json").read_bytes()
    summary = json.loads((root / "execution_summary.json").read_text(encoding="utf-8"))
    metrics = json.loads(metrics_bytes)
    total = metrics["all_job_count"]
    if (not summary.get("all_attempted") or summary.get("all_job_count") != total
            or summary.get("complete_job_count") != total or summary.get("failed_job_count") != 0
            or summary.get("method_error_or_non_ok_count") != 0
            or metrics.get("method_error_or_non_ok_count") != 0 or metrics.get("failed_jobs")
            or len(metrics["records"]) != total):
        raise ValueError("Enrichment requires a complete, error-free queue")
    if summary.get("metrics_sha256") != digest(metrics_bytes):
        raise ValueError("Recorded metrics SHA differs")
    if any(r.get("feasible") is not True or r.get("execution_status") != "ok" for r in metrics["records"]):
        raise ValueError("Non-feasible/non-ok method output")
    return metrics, summary, digest(metrics_bytes)


def raw_path(root, projection, raw_root=None):
    filename = projection["job_id"] + ".json"
    candidates = []
    if raw_root:
        candidates.extend([raw_root / filename, raw_root / "results" / filename])
    candidates.append(root / "results" / filename)
    if projection.get("output"):
        candidates.append(Path(projection["output"]))
    return next((path for path in candidates if path.is_file()), None)


def enrich_one(raw, projection):
    for key in ("job_id", "source", "config", "method", "seed", "budget_cpu_seconds"):
        if raw.get(key) != projection.get(key):
            raise ValueError("Raw/projection differs in " + key)
    if raw.get("execution_status") != "ok" or raw.get("feasible") is not True:
        raise ValueError("Invalid raw method result")
    trials = raw.get("trials", [])
    feature_reads, diagnostic_reads, operations = Counter(), Counter(), Counter()
    child_feature_reads, parent_feature_reads, parent_operations = Counter(), Counter(), Counter()
    anchors, statuses, selected_genomes = Counter(), Counter(), Counter()
    parent_genomes, accepted_genomes, parent_statuses = Counter(), Counter(), Counter()
    feature_cpu = scoring_cpu = trial_cpu = 0.0
    child_feature_cpu = child_scoring_cpu = parent_feature_cpu = parent_scoring_cpu = parent_cpu = 0.0
    accepted_gain = accepted_rank_gain = accepted_local_exchange_gain = 0
    accepted_child_gain = accepted_parent_gain = accepted_rank_commits = 0
    race_count = parent_winners = child_winners = parent_accepted = child_accepted = 0
    parent_negatives = parent_rank_commits = raw_equal_races = 0
    for row in trials:
        stats = row.get("feature_stats", {})
        child_feature_reads.update(stats.get("feature_reads", {}))
        feature_reads.update(stats.get("feature_reads", {}))
        diagnostic_reads.update(stats.get("diagnostic_feature_reads", {}))
        operations.update(stats.get("op_counts", {}))
        child_feature_cpu += float(stats.get("feature_cpu", 0.))
        child_scoring_cpu += float(stats.get("scoring_cpu", 0.))
        # cpu_seconds already charges the whole trial, including a parent race;
        # adding parent_cpu again would double-count the actual solve budget.
        trial_cpu += float(row.get("cpu_seconds", 0.))
        anchors[row.get("patch", {}).get("anchor_policy", "unrecorded")] += 1
        statuses[row.get("status", "unrecorded")] += 1
        selected_genomes[row.get("genome_id", "unrecorded")] += 1
        race = row.get("paired_race")
        winner = row.get("genome_id", "unrecorded")
        if race:
            required = {"parent_id", "winner_id", "parent_raw_gain_ticks", "parent_cpu_seconds",
                        "parent_status", "parent_feature_stats", "parent_rank_commits"}
            if not required <= race.keys() or not isinstance(race["parent_feature_stats"], dict):
                raise ValueError("Incomplete paired-race evidence")
            race_count += 1
            winner = race["winner_id"]
            if winner not in (row["genome_id"], race["parent_id"]):
                raise ValueError("Race winner is neither evaluated child nor parent")
            if row.get("committed_genome_id", winner) != winner:
                raise ValueError("Recorded winning proposal genome differs")
            parent_winners += winner == race["parent_id"]
            child_winners += winner == row["genome_id"]
            parent_negatives += race["parent_raw_gain_ticks"] < 0
            raw_equal_races += race["parent_raw_gain_ticks"] == row["raw_gain_ticks"]
            parent_rank_commits += int(race["parent_rank_commits"])
            parent_cpu += float(race["parent_cpu_seconds"])
            parent_statuses[race["parent_status"]] += 1
            parent_genomes[race["parent_id"]] += 1
            parent_stats = race["parent_feature_stats"]
            parent_feature_reads.update(parent_stats.get("feature_reads", {}))
            feature_reads.update(parent_stats.get("feature_reads", {}))
            diagnostic_reads.update(parent_stats.get("diagnostic_feature_reads", {}))
            parent_operations.update(parent_stats.get("op_counts", {}))
            operations.update(parent_stats.get("op_counts", {}))
            parent_feature_cpu += float(parent_stats.get("feature_cpu", 0.))
            parent_scoring_cpu += float(parent_stats.get("scoring_cpu", 0.))
        inferred_child_accepted = bool(row.get("accepted")) and winner == row.get("genome_id", "unrecorded")
        if "child_accepted" in row and row["child_accepted"] != inferred_child_accepted:
            raise ValueError("child_accepted contradicts winning accepted proposal")
        child_accepted += inferred_child_accepted
        if row.get("accepted"):
            # In r2 top-level raw_gain/details deliberately retain the child,
            # even when a parent wins. Attribute only the accepted winner.
            if "accepted_proposal_details" in row:
                details = row["accepted_proposal_details"]
                if not isinstance(details, dict):
                    raise ValueError("Accepted proposal details are missing")
            elif race:
                raise ValueError("A raced accepted proposal lacks winner details")
            else:
                details = row  # Exact legacy r1 behavior.
            gain = int(row.get("accepted_gain_ticks", row["raw_gain_ticks"]))
            rank_gain = int(details.get("rank_value_ticks", 0)) - int(row.get("removed_ticks", 0))
            exchange_gain = int(details.get("exchange_added_ticks", 0))
            if gain != rank_gain + exchange_gain:
                raise ValueError("Accepted winner ranking/exchange gains do not reconcile")
            accepted_gain += gain
            accepted_rank_gain += rank_gain
            accepted_local_exchange_gain += exchange_gain
            accepted_rank_commits += int(details.get("rank_commits", 0))
            accepted_genomes[winner] += 1
            if inferred_child_accepted:
                accepted_child_gain += gain
            else:
                parent_accepted += 1
                accepted_parent_gain += gain
        elif row.get("accepted_gain_ticks", 0) != 0:
            raise ValueError("Rejected proposal has nonzero accepted gain")
    feature_cpu = child_feature_cpu + parent_feature_cpu
    scoring_cpu = child_scoring_cpu + parent_scoring_cpu
    controller = raw.get("controller", {})
    events = controller.get("events", [])
    mutations, selected_mutation_kinds, events_by_type = Counter(), Counter(), Counter()
    raced_parent_mutation_kinds, accepted_mutation_kinds = Counter(), Counter()
    generations, coefficients, policies = set(), set(), set()
    representation_updates = program_updates = 0
    for event in events:
        events_by_type[event.get("event", "unrecorded")] += 1
        if event.get("event") == "genome_created":
            genome = event["genome"]
            kind = genome["mutation_kind"]
            if kind != "seed":
                mutations[kind] += 1
            selected_mutation_kinds[kind] += selected_genomes.get(genome["id"], 0)
            raced_parent_mutation_kinds[kind] += parent_genomes.get(genome["id"], 0)
            accepted_mutation_kinds[kind] += accepted_genomes.get(genome["id"], 0)
            generations.add(genome.get("generation", 0))
            coefficients.add(tuple(genome["recipe"]["coefficients"]))
            policies.add(json.dumps(genome["recipe"]["patch_policy"], sort_keys=True))
            representation_updates += bool(event.get("actual_representation_changed"))
            program_updates += kind != "seed" and bool(event.get("actual_program_changed"))
    preferences = Counter()
    cycle_contexts = 0
    for frame in raw.get("certificates", []):
        preferences.update(pair.get("preference", "unavailable") for pair in frame.get("bounds", {}).get("pairs", []))
        cycle_contexts += bool(frame.get("archive_gate", {}).get("has_cycle"))
    solver_stats = raw.get("stats", {})
    attribution_applies = "operator_attempts" in solver_stats
    total_delta = int(raw["value_ticks"]) - int(raw["seed_value_ticks"])
    shared_gain = int(solver_stats.get("shared_exchange_gain_ticks", 0))
    reconciliation = (total_delta == accepted_gain + shared_gain
                      and accepted_gain == accepted_rank_gain + accepted_local_exchange_gain) if attribution_applies else None
    if attribution_applies and not reconciliation:
        raise ValueError("Logged accepted/shared gain does not reconcile to complete reward")
    return {"job_id": raw["job_id"], "source": raw["source"], "config": raw["config"],
            "method": raw["method"], "seed": raw["seed"], "budget_cpu_seconds": raw["budget_cpu_seconds"],
            "actual_added_feature_reads": dict(feature_reads),
            "actual_added_feature_read_count": sum(feature_reads.values()),
            "child_added_feature_reads": dict(child_feature_reads),
            "raced_parent_added_feature_reads": dict(parent_feature_reads),
            "reconstruction_diagnostic_feature_reads": dict(diagnostic_reads),
            "feature_operation_counts": dict(operations), "anchor_usage": dict(anchors),
            "raced_parent_feature_operation_counts": dict(parent_operations),
            "mutation_created_by_kind": dict(mutations), "selected_genome_mutation_kind_usage": dict(selected_mutation_kinds),
            "raced_parent_mutation_kind_usage": dict(raced_parent_mutation_kinds),
            "accepted_proposal_mutation_kind_usage": dict(accepted_mutation_kinds),
            "program_hash_updates_created": program_updates,
            "representation_hash_updates_created": representation_updates,
            "distinct_created_coefficient_vectors": len(coefficients),
            "distinct_created_patch_policies": len(policies), "max_created_generation": max(generations, default=0),
            "controller_event_counts": dict(events_by_type),
            "trial_summary": {"count": len(trials), "accepted": sum(bool(r.get("accepted")) for r in trials),
                              "negative_raw": sum(r.get("raw_gain_ticks", 0) < 0 for r in trials),
                              "child_accepted": child_accepted, "parent_accepted": parent_accepted,
                              "rank_commits": sum(int(r.get("rank_commits", 0)) for r in trials) + parent_rank_commits,
                              "child_rank_commits": sum(int(r.get("rank_commits", 0)) for r in trials),
                              "raced_parent_rank_commits": parent_rank_commits,
                              "accepted_proposal_rank_commits": accepted_rank_commits,
                              "child_signed_raw_gain_ticks_sum": sum(int(r.get("raw_gain_ticks", 0)) for r in trials),
                              "status_counts": dict(statuses)},
            "paired_race_summary": {"count": race_count, "parent_winners": parent_winners,
                                    "child_winners_or_ties": child_winners,
                                    "raw_gain_equal": raw_equal_races,
                                    "parent_negative_raw": parent_negatives,
                                    "parent_status_counts": dict(parent_statuses),
                                    "parent_cpu_seconds": parent_cpu,
                                    "parent_cpu_included_in_trial_cpu": True},
            "feature_cpu_seconds": feature_cpu, "scoring_cpu_seconds": scoring_cpu,
            "child_feature_cpu_seconds": child_feature_cpu, "raced_parent_feature_cpu_seconds": parent_feature_cpu,
            "child_scoring_cpu_seconds": child_scoring_cpu, "raced_parent_scoring_cpu_seconds": parent_scoring_cpu,
            "trial_cpu_seconds": trial_cpu, "total_cpu_seconds": raw.get("cpu_seconds"),
            "controller_cpu_seconds": None,
            "controller_cpu_note": "Included in total CPU; no separate exact timer recorded",
            "certificate_pair_status_counts": dict(preferences), "archive_cycle_contexts": cycle_contexts,
            "certificate_call_count": len(raw.get("certificates", [])),
            "accepted_operator_gain_ticks": accepted_gain if attribution_applies else None,
            "accepted_child_proposal_gain_ticks": accepted_child_gain if attribution_applies else None,
            "accepted_parent_proposal_gain_ticks": accepted_parent_gain if attribution_applies else None,
            "accepted_rank_stage_gain_ticks": accepted_rank_gain if attribution_applies else None,
            "accepted_patch_common_exchange_gain_ticks": accepted_local_exchange_gain if attribution_applies else None,
            "shared_global_exchange_gain_ticks": shared_gain if attribution_applies else None,
            "gain_reconciliation_valid": reconciliation,
            "attribution_note": "All actual child and raced-parent feature/scoring work is counted. Trial CPU already includes parent CPU. Child raw signed gains remain intact even when a parent wins. Accepted gains use winning-proposal details, including ranking and common patch exchange; commits alone do not prove causal LLM benefit. Certificate diagnostic reads are not reconstructed from missing counters."}


def main(input_root, output=None, raw_root=None):
    root = Path(input_root).resolve()
    raw_root = Path(raw_root).resolve() if raw_root else None
    metrics, summary, metrics_sha = complete_input(root)
    records, errors = [], []
    for projection in metrics["records"]:
        try:
            path = raw_path(root, projection, raw_root)
            if path is None:
                raise FileNotFoundError("Original raw job JSON missing; run enrichment on server")
            data = path.read_bytes()
            actual_sha = digest(data)
            if not projection.get("output_sha256") or projection["output_sha256"] != actual_sha:
                raise ValueError("Original output SHA differs")
            row = enrich_one(json.loads(data), projection)
            row.update(raw_output_sha256=actual_sha, raw_output_path=str(path))
            records.append(row)
        except Exception as error:
            errors.append({"job_id": projection["job_id"], "error": f"{type(error).__name__}: {error}"})
    report = {"version": "stk_online_llm_v2_read_only_enrichment", "metrics_sha256": metrics_sha,
              "execution_summary_sha256": digest((root / "execution_summary.json").read_bytes()),
              "source_sha256": digest(Path(__file__).read_bytes()), "all_job_count": metrics["all_job_count"],
              "complete": not errors and len(records) == metrics["all_job_count"],
              "records": records, "errors": errors, "optimizer_calls": 0, "model_calls": 0,
              "raw_sources_checked_once": True}
    destination = Path(output) if output else root / "enriched_metrics.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"enriched": len(records), "errors": len(errors), "output": str(destination)}, ensure_ascii=False))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-root", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.input_root, args.output, args.raw_root))
