"""Small arithmetic summary of already frozen input evidence; no graph/solver calls.

This does not select a winning dataset from scheduling outcomes. Exact input
identity, competition and symmetry results are kept separate from unknown
preferences and unmeasured deployment quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "experiments/analysis/v07/source_overlap_001.json": None,
    "experiments/discovery/contact_scene_screen_v07_002/screen_summary.json":
        "f01d60e86231cef5f726e22353400e7ad39159c85ecf86859d1f637d220dd6dc",
    "experiments/discovery/scene_alias_classification_v07_003/classification_summary.json":
        "4b71e538fbdaa1a8c4fb8e32035403c30bba4f7f14a7c0e635e846114c4104d7",
    "experiments/analysis/v07/public_benchmark_scenario_metadata_001.json":
        "8ae17b9c5c8b32769f8bd193e43e349f6a067addbcddb4dc5a8ae790baf6982e",
    "experiments/analysis/v07/satnet_input_profile_001.json":
        "02002ffe80606be21ecce0bbb2c2f501ea86dff5ea49bf3d025fc2016d87fe72",
}


def summarize():
    evidence, receipts = {}, {}
    for path, pin in PINS.items():
        raw = (ROOT / path).read_bytes()
        digest = sha256(raw).hexdigest()
        if pin is not None and digest != pin:
            raise ValueError(f"Frozen input changed: {path}")
        evidence[path] = json.loads(raw)
        receipts[path] = digest
    overlap, screen, aliases, public, satnet = evidence.values()
    if screen["completed_graphs"] != 48 or aliases["classified_alias_pairs"] != 556:
        raise ValueError("Only the complete frozen census is supported")
    by_source = []
    for name in ("C6", "W6"):
        changes = [r for r in screen["paired_changes"] if r["source"] == name]
        records = [r for r in screen["records"] if r["source"] == name]
        roots = sum(r["n"] for r in changes)
        changed = sum(r["roots_with_changed_neighbors"] for r in changes)
        split = overlap["canonical_chronological_splits"][name + ".csv"]
        by_source.append({"source": name, "full_contacts": sum(split["whole_day_unique_counts"]),
            "start_day_counts": split["whole_day_unique_counts"],
            "training_windows": len(changes), "configuration_graphs": len(records),
            "window_contact_min": min(r["n"] for r in records),
            "window_contact_max": max(r["n"] for r in records),
            "added_edges": sum(r["added_edges"] for r in changes),
            "changed_neighborhood_roots": changed, "training_contacts": roots,
            "changed_root_fraction_exact": str(Fraction(changed, roots)),
            "all_initial_graphs_connected": all(r["component_count"] == 1 for r in records),
            "start_day_key_intersections": [r["intersection"] for r in split["opportunity_key_split_relations"]],
            "link_boundary_spills": [r["link_end_after_day_boundary"] for r in split["boundary_contacts"]]})
    occurrences = [pair for graph in aliases["graphs"] for pair in graph["pairs"]]
    compatible = sum(not pair["adjacent"] for pair in occurrences)
    competing = len(occurrences) - compatible
    competing_kinds = Counter(pair["kind"] for pair in occurrences if pair["adjacent"])
    cross = aliases["cross_configuration"]
    both_competing = sum(pair["gap340"]["adjacent"] and pair["gap680"]["adjacent"] for pair in cross)
    neither_competing = sum(not pair["gap340"]["adjacent"] and not pair["gap680"]["adjacent"] for pair in cross)
    total_action_occurrences = sum(graph["n"] for graph in aliases["graphs"])
    return {
        "version": "v07_input_evidence_arithmetic_004", "source_sha256": receipts,
        "source_and_split": {"within_series_containment_pairs": len(overlap["all_within_series_containments"]),
            "all_within_series_earlier_nested": all(r["left_subset_of_right"] for r in overlap["all_within_series_containments"]),
            "C6_W6_opportunity_intersection": overlap["C6_vs_W6_opportunity_keys"]["intersection"],
            "canonical_sources": by_source,
            "limits": "Distinct start-day contact keys do not establish independent resources or physical calendar feasibility; whole-corpus novelty is not asserted."},
        "alias_and_competition": {"all_alias_occurrences": len(occurrences),
            "all_action_occurrences": total_action_occurrences,
            "actions_in_alias_fraction_exact": str(Fraction(2 * len(occurrences), total_action_occurrences)),
            "compatible_alias_occurrences": compatible, "competing_alias_occurrences": competing,
            "competing_alias_kinds": dict(competing_kinds),
            "unique_cross_configuration_pairs": len(cross),
            "both_configurations_competing_pairs": both_competing,
            "both_configurations_compatible_pairs": neither_competing,
            "mixed_competition_pairs": len(cross) - both_competing - neither_competing,
            "proved_empty_boundary_tie_occurrences": sum(p["kind"] != "non_twins" for p in occurrences),
            "non_twin_alias_occurrences": sum(p["kind"] == "non_twins" for p in occurrences),
            "weighted_WL2_distinguished_occurrences": sum(p["unmarked_weighted_WL2_separates"] for p in occurrences),
            "strict_preferences": "Not inferred by this input-only arithmetic. Consult separately frozen conditional certificates.",
            "complete_schedule_improvement": "Not measured by these input-only passes."},
        "public_corpora": [{"corpus": r["corpus"], "graphs": r["graph_count"], "n_range": r["n_range"],
            "contact_metadata_present": r["contacts_or_resource_times_in_supplied_graph_schema"],
            "domain_configuration_reconstructable": r["domain_counterfactual_reconstructable_from_supplied_graph"]}
            for r in public["corpora"]],
        "satnet": {"request_week_count": len(satnet["weekly"]),
            "fixed_track_mwis_lossless_status": satnet["fixed_track_mwis_lossless_status"],
            "all_week_request_ids_disjoint": all(r["exact_request_track_id_intersection"] == 0 for r in satnet["pairwise_week_relations"]),
            "all_week_time_extents_disjoint": all(r["time_extents_disjoint"] for r in satnet["pairwise_week_relations"])},
        "graph_builds": 0, "optimizer_calls": 0, "oracle_calls": 0, "model_calls": 0,
        "heldout_graphs_or_outcomes_accessed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    target = Path(args.out)
    if target.exists():
        raise ValueError("Use a new arithmetic-output namespace")
    result = summarize()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["alias_and_competition"], ensure_ascii=False))
