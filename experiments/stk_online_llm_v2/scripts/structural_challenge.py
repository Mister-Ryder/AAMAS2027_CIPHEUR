"""Exact offline information gate on the existing TRAIN E/J 64-node witness.

Computes actual new PatchEvaluator feature_values, not a scheduling experiment.
All banks are retained; no outcome is used to select or repair a recipe.  This
new Fraction-seconds namespace is not the old binary-fsum interface.  The graph
is the *complete restricted P=64 patch*, not the complete 12k scheduling graph.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OLD = PROJECT / "experiments" / "stk_full_llm_v1"
sys.path.insert(0, str(PROJECT))
from cipheur.online_v2.typed import BASE_NAMES, PatchEvaluator, validate_recipe


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(values):
    return {name: str(value) for name, value in values.items()}


def graph_input(graph):
    nodes = graph["local_node_indices"]
    if nodes != list(range(64)) or (graph["a"], graph["b"]) != (23, 24):
        raise ValueError("This registered challenge is exactly P64 and roots23/24")
    adjacency = {node: set() for node in nodes}
    for u, v in graph["edges"]:
        if u == v or u not in adjacency or v not in adjacency:
            raise ValueError("Invalid saved local edge")
        adjacency[u].add(v)
        adjacency[v].add(u)
    seconds = [Fraction(value) for value in graph["weight_seconds"]]
    weights = {}
    for node, value in zip(nodes, seconds):
        ticks = value * 1_000_000
        if ticks.denominator != 1:
            raise ValueError("Frozen contact-duration weight is not an exact microtick")
        weights[node] = int(ticks)
    if len(weights) != 64 or len(graph["root_station_gap_seconds"]) != 64:
        raise ValueError("Incomplete frozen metadata")
    metadata = {"weight_scale": 1_000_000,
                "duration": {node: value for node, value in zip(nodes, seconds)},
                "station_gap": dict(zip(nodes, graph["root_station_gap_seconds"])),
                "satellite_gap": 150}
    return adjacency, weights, set(nodes), metadata


def small_quotient(values):
    """The two already certified strict requirements on all four occurrences."""
    vectors = {}
    occurrence_to_class = {}
    for side in ("E", "J"):
        for root in (23, 24):
            vector = tuple(values[side][root].items())
            if vector not in vectors:
                vectors[vector] = f"q{len(vectors)}"
            occurrence_to_class[(side, root)] = vectors[vector]
    edges = [(occurrence_to_class[("E", 23)], occurrence_to_class[("E", 24)]),
             (occurrence_to_class[("J", 24)], occurrence_to_class[("J", 23)])]
    self_loop = any(u == v for u, v in edges)
    two_cycle = edges[0] == (edges[1][1], edges[1][0])
    return {"classes": len(vectors), "strict_edges": edges,
            "self_loop": self_loop, "has_cycle": self_loop or two_cycle,
            "scope": "Only this registered two-requirement challenge; not the complete archive"}


def evaluate_recipe(recipe, graphs):
    validate_recipe(recipe)
    side_values, side_scores, side_stats = {}, {}, {}
    started = time.process_time()
    for side in ("E", "J"):
        adjacency, weights, active, metadata = graphs[side]
        program = {key: deepcopy(recipe[key]) for key in ("name", "features", "rule", "rationale")}
        evaluator = PatchEvaluator(adjacency, weights, program, recipe["coefficients"],
                                   set(active), set(active), metadata=metadata)
        side_values[side] = {}
        side_scores[side] = {}
        for root in (23, 24):
            values = evaluator.feature_values(root)
            side_values[side][root] = {name: values[name] for name in
                                      BASE_NAMES + tuple(f["name"] for f in recipe["features"])}
            side_scores[side][root] = evaluator.score(root)
        side_stats[side] = deepcopy(evaluator.stats)
    names = tuple(f["name"] for f in recipe["features"])
    base_same = {str(root): all(side_values["E"][root][name] == side_values["J"][root][name]
                               for name in BASE_NAMES) for root in (23, 24)}
    changed = {str(root): [name for name in names if side_values["E"][root][name] != side_values["J"][root][name]]
               for root in (23, 24)}
    directions = {}
    for side in ("E", "J"):
        difference = side_scores[side][23] - side_scores[side][24]
        directions[side] = "a" if difference > 1e-8 else "b" if difference < -1e-8 else "score_tie"
    matches = directions["E"] == "a" and directions["J"] == "b"
    return {"status": "evaluated", "base9_same_E_J_per_root": base_same,
            "added_features_changed_E_J_per_root": changed,
            "added_representation_distinguishes_at_least_one_root": any(changed.values()),
            "both_roots_still_full_representation_alias": not any(changed.values()) and all(base_same.values()),
            "feature_values": {side: {str(root): encoded(values) for root, values in rows.items()}
                               for side, rows in side_values.items()},
            "initial_coefficient_scores": {side: {str(root): score for root, score in rows.items()}
                                           for side, rows in side_scores.items()},
            "initial_rule_directions": directions,
            "initial_rule_matches_both_existing_strict_requirements": matches,
            "challenge_complete_quotient": small_quotient(side_values),
            "diagnostic_cpu_seconds": time.process_time() - started,
            "diagnostic_evaluator_stats": side_stats,
            "schedule_advantage_measured": False,
            "cache_note": "feature_values is a full offline diagnostic; subsequent scores use warm caches. Diagnostic work is not deployment throughput."}


def main(output_root=ROOT, context_path=None, bank_paths=None):
    output_root = Path(output_root).resolve()
    context_path = Path(context_path or OLD / "context" / "train_context.json").resolve()
    context = json.loads(context_path.read_text(encoding="utf-8"))
    witness = context["witness_only"]
    if witness["source"] != "CP-AU-r000" or witness["boundary"]["active_P_count"] != 64:
        raise ValueError("Unexpected registered TRAIN witness")
    graphs = {side: graph_input(witness["same_local_graphs"][side]) for side in ("E", "J")}
    if graphs["E"][1] != graphs["J"][1] or graphs["E"][2] != graphs["J"][2]:
        raise ValueError("Changed input weights/patch would invalidate this challenge")
    bank_paths = bank_paths or [output_root / "banks" / f"{name}.json" for name in
                               ("witness_operators", "feedback_operators", "grammar_operators")]
    rows, bank_sources = [], []
    for bank_path in map(Path, bank_paths):
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        if bank["schema_version"] != "stk_online_llm_v2":
            raise ValueError("Unexpected recipe schema")
        bank_sources.append({"path": str(bank_path.resolve()), "sha256": digest(bank_path),
                             "recipes": len(bank["recipes"])})
        for slot, recipe in enumerate(bank["recipes"]):
            row = {"bank": bank_path.stem, "slot": slot, "name": recipe["name"],
                   "recipe_sha256": hashlib.sha256(json.dumps(recipe, sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}
            try:
                row.update(evaluate_recipe(recipe, graphs))
            except Exception as error:
                row.update(status="evaluation_error", error=f"{type(error).__name__}: {error}",
                           recipe_removed_or_repaired=False, schedule_advantage_measured=False)
            rows.append(row)
    summary = []
    for bank in sorted({row["bank"] for row in rows}):
        group = [row for row in rows if row["bank"] == bank]
        evaluated = [row for row in group if row["status"] == "evaluated"]
        summary.append({"bank": bank, "recipes": len(group), "evaluated": len(evaluated),
                        "evaluation_errors": len(group) - len(evaluated),
                        "added_representation_distinguishes": sum(r["added_representation_distinguishes_at_least_one_root"] for r in evaluated),
                        "initial_rule_matches_both_strict_requirements": sum(r["initial_rule_matches_both_existing_strict_requirements"] for r in evaluated),
                        "remaining_challenge_cycles": sum(r["challenge_complete_quotient"]["has_cycle"] for r in evaluated)})
    report = {"version": "stk_online_llm_v2_registered_structural_challenge", "split": "TRAIN",
              "namespace": "exact_fraction_seconds_patch_station_local_v2",
              "context_sha256": digest(context_path), "context_path": str(context_path),
              "source": witness["source"], "query_id": witness["query_id"], "roots_local": [23, 24],
              "boundary": witness["boundary"], "graph_scope": "Complete restricted P64 graph under common F/P/X; not the complete12k graph or full72h optimum",
              "duration_metadata": "This frozen contact-duration objective equals the exact duration; input Fraction seconds converted losslessly to microticks. Station gap is the stored per-root map; satellite gap150seconds.",
              "old_numeric_namespace_reused": False,
              "strict_certificate_directions": {"E": "a", "J": "b"},
              "banks": bank_sources, "summary": summary, "rows": rows,
              "bank_selection_or_mutation_from_this_result": False,
              "schedule_advantage_claim": False,
              "limitation": "Distinguishing one known TRAIN witness is an information-capacity check, not full-archive consistency, ranking correctness after evolution, TEST generalization or schedule quality.",
              "source_sha256": digest(__file__),
              "typed_source_sha256": digest(PROJECT / "cipheur" / "online_v2" / "typed.py")}
    folder = output_root / "analysis"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "structural_challenge.json").write_text(json.dumps(report, ensure_ascii=False,
                                            indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (folder / "structural_challenge.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["bank", "slot", "name", "status", "added_representation_distinguishes_at_least_one_root",
                  "initial_rule_matches_both_existing_strict_requirements", "both_roots_still_full_representation_alias"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"summary": summary, "report": str(folder / "structural_challenge.json"),
                      "schedule_advantage_claim": False}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--bank", type=Path, action="append")
    args = parser.parse_args()
    main(args.output_root, args.context, args.bank)
