"""Fresh-instance follow-up using an unchanged, previously frozen method bank.

Run with ``python -m cipheur.followup --pilot ... --output ...``.
Generation and anti-overlap exclusions do not use oracle or performance labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import statistics

from .experiment_data import SPLITS, make_suite, _choose_actions, _record
from .experiments import aggregate, certify_records, digest, evaluate_program, load, save, serialize_pair
from .graph_features import FeatureRuleProgram
from .model import Graph
from .representation import ranking_report
from .v51_adapter import verify_v51_selection


DEFAULT_COUNTS = {"diagnostic": 24, "random_temporal": 32, "c3": 16}


def _count_at(config: dict, family: str, split: str) -> int:
    value = config["counts"].get(family, 0)
    value = value.get(split, 0) if isinstance(value, dict) else value
    if type(value) is not int or value < 0:
        raise ValueError("Prior family counts must be nonnegative integers")
    return value


def _as_graph(value) -> Graph:
    return value if isinstance(value, Graph) else Graph.from_dict(value)


def prior_identities(data: dict) -> dict:
    """Protect every prior split, not merely the earlier held-out test set."""
    record_ids, instances, graphs, seeds, original_ids = set(), set(), set(), set(), set()
    for split in SPLITS:
        for record in data.get(split, ()):
            record_ids.add(record["id"])
            instances.add(record["source"]["instance_fingerprint"])
            for side in ("left", "right"):
                graphs.add(_as_graph(record[side]).digest())
            seed = record["source"].get("seed")
            if seed is not None:
                seeds.add(seed)
            original_ids.update(record["source"].get("original_ids", ()))
    return {"record_ids": record_ids, "instances": instances, "graphs": graphs,
            "seeds": seeds, "original_ids": original_ids}


def _protect_c3(record: dict, old_original_ids: set[int]) -> tuple[dict | None, dict]:
    """Remove already-used opportunities by identity and keep induced semantics.

    Legacy conflicts are pairwise, so an induced subgraph preserves the exact
    predicates. The original verifier can still check retained selections in
    the larger, pre-exclusion window graph: discarded opportunities are never
    selected. No quality outcome or graph-change condition affects retention.
    """
    original_ids = record["source"].get("original_ids", ())
    removed = sorted(set(original_ids) & old_original_ids)
    receipt = {"id": record["id"], "prior_opportunities_removed": removed,
               "prior_opportunities_removed_count": len(removed),
               "retained_opportunities": len(original_ids) - len(removed)}
    if not removed:
        return record, receipt
    retained_ids = [value for value in original_ids if value not in old_original_ids]
    if not retained_ids:
        receipt["retention_reason"] = "no_unseen_opportunities_after_identity_exclusion"
        return None, receipt
    retained = {str(value) for value in retained_ids}
    pair = []
    for side in ("left", "right"):
        before = record[side]
        graph = Graph(before.name + "_unseen", tuple(c for c in before.contacts if c.id in retained),
                      frozenset(edge for edge in before.edges if set(edge) <= retained),
                      dict(before.constraints),
                      {**before.provenance, "original_ids": retained_ids,
                       "followup_prior_opportunities_removed": removed,
                       "legacy_verifier_context_scope": "pre_exclusion_window_graph"})
        if hasattr(before, "_v51_context"):
            graph._v51_context = before._v51_context
        pair.append(graph)
    fixed = tuple(value for value in record["fixed"] if value in retained)
    excluded = tuple(value for value in record["excluded"] if value in retained)
    source = {**record["source"], "original_ids": retained_ids,
              "arc_metadata": {key: value for key, value in record["source"].get("arc_metadata", {}).items()
                               if key in retained},
              "identity_exclusion": receipt,
              "cap_then_identity_exclusion": True}
    return _record(record["id"], "c3", pair[0], pair[1], source, fixed, excluded,
                   actions=_choose_actions(pair[0], pair[1], fixed, excluded)), receipt


def fresh_records(suite: dict, prior_data: dict, prior_config: dict) -> tuple[list[dict], dict]:
    """Retain only later-index test records and audit them against all old splits."""
    protected = prior_identities(prior_data)
    thresholds = {family: _count_at(prior_config, family, "test") for family in DEFAULT_COUNTS}
    records, exclusions = [], []
    rejected_prefix = Counter()
    for record in suite["test"]:
        family = record["family"]
        index = int(record["id"].rsplit("_", 1)[1])
        if index < thresholds[family]:
            rejected_prefix[family] += 1
            continue
        if family == "c3":
            record, receipt = _protect_c3(record, protected["original_ids"])
            exclusions.append(receipt)
            if record is None:
                continue
        records.append(record)
    seen_records, seen_instances, seen_graphs, seen_seeds, seen_originals = set(), set(), set(), set(), set()
    for record in records:
        if record["id"] in protected["record_ids"] or record["id"] in seen_records:
            raise ValueError("Follow-up record ID overlaps an earlier/new record")
        seen_records.add(record["id"])
        instance = record["source"]["instance_fingerprint"]
        if instance in protected["instances"] or instance in seen_instances:
            raise ValueError("Follow-up physical instance overlaps an earlier/new instance")
        seen_instances.add(instance)
        for side in ("left", "right"):
            graph = record[side]
            fingerprint = graph.digest()
            if fingerprint in protected["graphs"] or fingerprint in seen_graphs:
                raise ValueError("Follow-up graph overlaps an earlier/new graph")
            seen_graphs.add(fingerprint)
            graph.available(record["fixed"], record["excluded"])
        seed = record["source"].get("seed")
        if seed is not None:
            if seed in protected["seeds"] or seed in seen_seeds:
                raise ValueError("Follow-up seed overlaps an earlier/new seed")
            seen_seeds.add(seed)
        original_ids = set(record["source"].get("original_ids", ()))
        if original_ids & (protected["original_ids"] | seen_originals):
            raise ValueError("Follow-up original C3 opportunity overlaps prior/new data")
        seen_originals.update(original_ids)
    audit = {"passed": True, "compared_against_prior_splits": list(SPLITS),
             "index_thresholds": thresholds, "prefix_pairs_excluded": dict(rejected_prefix),
             "identity_exclusions": exclusions,
             "prior_original_opportunities_removed": sum(row["prior_opportunities_removed_count"] for row in exclusions),
             "retained_pairs": len(records), "families": dict(Counter(r["family"] for r in records)),
             "prior_record_count": len(protected["record_ids"]), "prior_graph_count": len(protected["graphs"]),
             "prior_original_opportunity_count": len(protected["original_ids"]),
             "fresh_instance_fingerprints": len(seen_instances), "fresh_graph_fingerprints": len(seen_graphs),
             "fresh_original_opportunities": len(seen_originals), "fresh_synthetic_seeds": len(seen_seeds),
             "oracle_or_performance_filtering": False}
    return records, audit


def _legacy_checks(rows, records: dict[str, dict]) -> list[dict]:
    checks = []
    for row in rows:
        if row["family"] != "c3":
            continue
        record = records[row["id"]]
        graph = record[row["side"]]
        result = verify_v51_selection(graph, row["selected"])
        result.update(method=row["method"], id=row["id"], side=row["side"])
        checks.append(result)
        row["legacy_verifier_feasible"] = result["feasible"]
        if not result["feasible"]:
            raise AssertionError("Original V51 verifier rejected a frozen-program schedule")
    return checks


def _spec_summary(program, specifications) -> dict:
    result = ranking_report(program, specifications)
    result["by_family"] = {
        family: ranking_report(program, [s for s in specifications if s["family"] == family])
        for family in sorted({s["family"] for s in specifications})}
    result["by_relation"] = {
        relation: ranking_report(program, [s for s in specifications if s["relation"] == relation])
        for relation in sorted({s["relation"] for s in specifications})}
    return result


def run(pilot: Path | str, output: Path | str, *, counts: dict | None = None,
        reference_nodes: int | None = None) -> dict:
    """Execute once in a fresh directory without updating a frozen program."""
    pilot, output = Path(pilot).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError("Follow-up output already exists; existing runs are never overwritten")
    prior_config, prior_data = load(pilot / "config.json"), load(pilot / "data.json")
    frozen_path = pilot / "frozen_programs.json"
    frozen_bytes = frozen_path.read_bytes()
    frozen = json.loads(frozen_bytes)
    if not isinstance(frozen, dict) or not frozen:
        raise ValueError("A nonempty previously frozen method bank is required")
    programs = {method: FeatureRuleProgram.from_dict(candidate) for method, candidate in frozen.items()}
    config = {**prior_config, "study": "fresh_instance_frozen_program_followup_v0.2.0",
              "counts": counts or dict(DEFAULT_COUNTS),
              "reference_max_nodes": max(reference_nodes or prior_config.get("reference_max_nodes", 100000), 100000),
              "prior_run": str(pilot), "refit_or_candidate_selection": False,
              "online_llm_calls": 0, "online_oracle_calls": 0}
    for family in DEFAULT_COUNTS:
        if _count_at(config, family, "test") < _count_at(prior_config, family, "test"):
            raise ValueError("Expanded counts cannot be smaller than prior requested test counts")
    # Copy the exact old file before any new objective or certificate is read.
    output.mkdir(parents=True)
    (output / "frozen_programs.json").write_bytes(frozen_bytes)
    save(output / "config.json", config)
    suite = make_suite(config)
    records, audit = fresh_records(suite, prior_data, prior_config)
    serialized = [serialize_pair(record) for record in records]
    save(output / "generated_suite.json", {split: [serialize_pair(record) for record in suite[split]] for split in SPLITS})
    save(output / "data.json", {"test": serialized})
    save(output / "data_protocol.json", {"base_protocol": suite["protocol"], "base_audit": suite["audit"],
        "generation_coverage": suite["coverage"], "cross_run_audit": audit,
        "followup_scope": "fresh_instances_under_same_previously_heldout_test_configurations",
        "c3_window_partition_changed_with_expanded_count": True,
        "c3_identity_exclusion_order": "declared_raw_generation_then_prior_ID_exclusion",
        "oracle_or_performance_filtering": False})
    source_hashes = {}
    for path in sorted(Path(__file__).parent.glob("*.py")):
        raw = path.read_bytes()
        snapshot = output / "source_snapshot" / "cipheur" / path.name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(raw)
        source_hashes[path.name] = sha256(raw).hexdigest()
    previous_inputs = ("config.json", "data.json", "frozen_programs.json", "freeze_receipt.json")
    save(output / "freeze_receipt.json", {
        "prior_run": str(pilot), "prior_inputs_sha256": {
            name: digest(pilot / name) for name in previous_inputs if (pilot / name).is_file()},
        "frozen_programs_sha256": digest(output / "frozen_programs.json"),
        "frozen_file_byte_identical_to_prior": frozen_bytes == (output / "frozen_programs.json").read_bytes(),
        "data_sha256": digest(output / "data.json"), "raw_generation_sha256": digest(output / "generated_suite.json"),
        "data_protocol_sha256": digest(output / "data_protocol.json"), "config_sha256": digest(output / "config.json"),
        "source_sha256": source_hashes, "python": platform.python_version(), "platform": platform.platform(),
        "new_training_or_validation_selection": False, "test_evaluation_started_after_freeze": True,
        "automated_llm_calls": 0, "certificate_and_reference_calls_are_offline_evaluation_only": True})
    # New test certificates and reference bounds follow the persisted freeze.
    specifications, attempts, budget = certify_records(serialized, config["oracle"])
    save(output / "test_specifications.json", specifications)
    save(output / "test_acquisition.json", {"attempts": attempts, "budget": budget})
    refs, all_rows, summaries, reports, legacy_checks = {}, [], {}, {}, []
    by_id = {record["id"]: record for record in records}
    for method, program in programs.items():
        rows = evaluate_program(program, serialized, refs, config["reference_max_nodes"])
        for row in rows:
            row["method"] = method
            row["legacy_verifier_feasible"] = None
        legacy_checks.extend(_legacy_checks(rows, by_id))
        all_rows.extend(rows)
        summaries[method] = aggregate(rows)
        reports[method] = _spec_summary(program, specifications)
    acquisition_reasons = dict(Counter(row["detail"]["reason"] for row in attempts))
    summary = {"test": summaries, "specifications": reports, "test_budget": budget,
               "cross_run_audit": audit, "acquisition_reasons": acquisition_reasons,
               "certified_pairs": len(specifications), "reference_contexts": len(refs),
               "exact_reference_contexts": sum(row["exact"] for row in refs.values()),
               "all_schedules_feasible": all(row["feasible"] for row in all_rows),
               "legacy_verifier": {"checked_contexts": len(legacy_checks),
                                   "feasible_contexts": sum(row["feasible"] for row in legacy_checks)},
               "selection_names": {method: candidate["name"] for method, candidate in frozen.items()},
               "distinct_frozen_programs": len({json.dumps(value, sort_keys=True) for value in frozen.values()}),
               "scope": "fresh_instance_stress_test_of_previous_frozen_programs_no_refit",
               "llm_advantage_claim": False, "full_c3_performance_claim": False}
    save(output / "test_metrics.json", all_rows)
    save(output / "test_reference_bounds.json", refs)
    save(output / "legacy_verification.json", legacy_checks)
    save(output / "summary.json", summary)
    fields = [key for key in all_rows[0] if key != "selected"] if all_rows else []
    with (output / "test_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    if frozen_path.read_bytes() != frozen_bytes:
        raise AssertionError("Prior frozen method bank changed during follow-up execution")
    save(output / "result_receipt.json", {
        path.relative_to(output).as_posix(): digest(path) for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "result_receipt.json"})
    print(json.dumps({"run": str(output), "families": audit["families"],
                      "contexts": len(refs), "exact_references": summary["exact_reference_contexts"],
                      "test_ratios": {method: groups.get("all", {}).get("mean_ratio") for method, groups in summaries.items()},
                      "legacy_verifier": summary["legacy_verifier"]}))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.pilot, args.output)


if __name__ == "__main__":
    main()
