"""TRAIN-only quotient diagnostic for frozen final feature-rule programs.

Append only additional library features whose names occur in the real rule's
co_names. Values come from the same compiled runtime and station-local graph
interface. This analyses existing743 labels; no new oracle or optimization.
The static-access gate can include a feature skipped by a conditional branch,
so actual lazy reads and exact fitted scores are recorded separately.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from train_context import PROJECT, DEFAULT_DATA, SOURCES, TAGS, FEATURES, digest, encoded, freeze_json, require
from joint_select import load_banks, load_fit

sys.path.insert(0, str(PROJECT))
from cipheur.graph_features import FeatureRuleProgram, _BASE_EXPRESSIONS
from cipheur.repair_v06 import _Meter
import full_schedule_execution as execution

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def exact(value):
    require(isinstance(value, (int, float, Fraction)) and math.isfinite(value), "Nonfinite or nonnumeric returned feature")
    return str(Fraction(value))


def hash_vector(vector):
    return hashlib.sha256(encoded(vector).encode("utf-8")).hexdigest()


def load_train(data_root):
    context = read(ROOT / "context/train_context.json")
    profile = read(ROOT / "context/train_context_profile.json")
    require(digest(ROOT / "context/train_context.json") == profile["context_sha256"], "TRAIN context changed")
    snapshot_path = ROOT / "context/train_evidence_snapshot.json"
    require(digest(snapshot_path) == profile["evidence_snapshot_sha256"], "TRAIN labels changed")
    requirements = read(snapshot_path)["raw_strict_requirements"]
    require(len(requirements) == 743 and all(row["source"] in SOURCES for row in requirements), "Must use all743 TRAIN labels")
    inventory, queries, graphs = {}, {}, {}
    stage_paths = {"p0": data_root / "analysis/p0", "expanded": data_root / "analysis/patch_interface_probe",
        "heterogeneous": data_root / "extensions/heterogeneous_ground_v1/analysis/quad_evidence"}
    for stage, folder in stage_paths.items():
        for source in SOURCES:
            path = folder / source / "query_manifest.json"
            expected = [item["sha256"] for key, item in profile["input_inventory"].items()
                        if key.replace("\\", "/").endswith("/" + path.relative_to(data_root).as_posix())]
            require(len(expected) == 1 and digest(path) == expected[0], "Recorded TRAIN query changed")
            manifest = read(path)
            require(manifest["prepared_before_labels"], "Query was not frozen before labels")
            inventory[str(path)] = digest(path)
            for query in manifest["queries"]:
                queries[stage, source, query["id"]] = query
    graph_root = data_root / "extensions/heterogeneous_ground_v1/graphs"
    for source in SOURCES:
        manifest = read(stage_paths["heterogeneous"] / source / "query_manifest.json")
        for side, tag in TAGS.items():
            npz, metadata = graph_root / source / (tag + ".npz"), graph_root / source / (tag + ".json")
            require(digest(npz) == manifest["graph_npz_sha256"][side], "Frozen TRAIN graph changed")
            graph, _ = execution.load_graph(npz, metadata, _Meter(None, "cpu", None, 0))
            require(graph.provenance["metadata"]["split"] == "train", "Graph not TRAIN")
            graphs[source, side] = graph
            inventory[str(npz)], inventory[str(metadata)] = digest(npz), digest(metadata)
    return context, profile, requirements, queries, graphs, inventory


def quotient(vectors, requirements):
    """Complete demanded finite quotient, with self-loops and all SCCs."""
    adjacency, reverse, demand = defaultdict(set), defaultdict(set), defaultdict(list)
    nodes = set(vectors)
    for row in requirements:
        a, b = row["preferred_vector_id"], row["other_vector_id"]
        adjacency[a].add(b)
        reverse[b].add(a)
        demand[a, b].append(row["requirement_id"])
    visited, order = set(), []
    for start in sorted(nodes):
        if start in visited:
            continue
        stack = [(start, False)]
        while stack:
            node, done = stack.pop()
            if done:
                order.append(node)
            elif node not in visited:
                visited.add(node)
                stack.append((node, True))
                stack.extend((other, False) for other in sorted(adjacency[node], reverse=True) if other not in visited)
    visited, components = set(), []
    for start in reversed(order):
        if start in visited:
            continue
        members, stack = [], [start]
        visited.add(start)
        while stack:
            node = stack.pop()
            members.append(node)
            for other in sorted(reverse[node], reverse=True):
                if other not in visited:
                    visited.add(other)
                    stack.append(other)
        components.append(sorted(members))
    component_for = {node: index for index, members in enumerate(components) for node in members}
    cyclic = {index for index, members in enumerate(components) if len(members) > 1 or (members[0], members[0]) in demand}
    two_cycles = sorted({tuple(sorted((a, b))) for a, b in demand if a != b and (b, a) in demand})
    self_loops = sorted((a, rows) for (a, b), rows in demand.items() if a == b)
    cycle_rows = [row for row in requirements if component_for[row["preferred_vector_id"]] == component_for[row["other_vector_id"]]
                  and component_for[row["preferred_vector_id"]] in cyclic]
    return {"vector_count": len(nodes), "strict_requirement_occurrences": len(requirements),
        "unique_directed_demand_edges": len(demand), "self_loop_edges": len(self_loops),
        "self_loop_requirement_occurrences": sum(len(rows) for _, rows in self_loops),
        "opposite_direction_pair_count": len(two_cycles), "opposite_direction_pairs": [list(pair) for pair in two_cycles],
        "SCC_count": len(components), "cyclic_SCC_count": len(cyclic),
        "cyclic_SCC_sizes": sorted((len(components[index]) for index in cyclic), reverse=True),
        "strict_requirement_occurrences_in_cyclic_SCC": len(cycle_rows),
        "cyclic_requirement_ids": [row["requirement_id"] for row in cycle_rows],
        "cyclic_SCCs": [components[index] for index in sorted(cyclic)],
        "finite_strict_pointwise_representation_consistent": not cyclic,
        "interpretation": "Acyclicity is finite information consistency for these frozen labels; it neither fits a rule nor establishes full-schedule gain. Cycles require incompatible strict order on equal exact numeric representation values."}


def analyse(item, fit, requirements, queries, graphs):
    started = time.perf_counter()
    program = FeatureRuleProgram.from_dict(item["program"])
    added_names = sorted(set(program.code.co_names) & {name for name, _ in program._expressions})
    states, roots, extended_vectors, base_vectors, rows = {}, {}, {}, {}, []
    original_lazy = execution._LazyScoreLocals
    current_reads = []

    class CaptureLazy(original_lazy):
        def __missing__(self, key):
            current_reads.append(key)
            return super().__missing__(key)

    # Process-local transparent observer; the frozen scorer files are unchanged.
    execution._LazyScoreLocals = CaptureLazy
    try:
        fit_checks = {row["requirement_id"]: row for row in fit["checks"]}
        for index, requirement in enumerate(requirements):
            stage, source, query_id, side = (requirement[key] for key in ("stage", "source", "query_id", "side"))
            side = {"left": "A", "right": "J"}.get(side, side)
            graph = graphs[source, side]
            query = queries[stage, source, query_id]
            state_key = source, side, query["patch_indices_sha256"]
            if state_key not in states:
                ids = tuple(graph.nodes)
                active = {ids[i] for i in query["patch_indices"]}
                # All base9 values have to be materialized for this diagnostic.
                # Their maintained numeric semantics match score_slice=True;
                # exact deployed score agreement is required below.
                states[state_key] = execution.StationLocalEvaluator(graph, program, active, {}, score_slice=False)
            evaluator = states[state_key]
            root_values = []
            for root in (requirement["preferred_contact_id"], requirement["other_contact_id"]):
                key = state_key, root
                if key not in roots:
                    current_reads.clear()
                    score = evaluator.score(root)
                    actual_reads = tuple(current_reads)
                    expressions = {**_BASE_EXPRESSIONS, **dict(program._expressions)}
                    values = {name: evaluator._snapshot.evaluate(expression, root) for name, expression in expressions.items()
                              if name in FEATURES or name in added_names}
                    values["station_gap"] = graph.constraints["station_gap_by_antenna"][graph.nodes[root].station]
                    values["satellite_gap"] = graph.constraints["satellite_gap"]
                    base = [exact(values[name]) for name in FEATURES]
                    extra = [exact(values[name]) for name in added_names]
                    full = base + extra
                    base_id, full_id = hash_vector(base), hash_vector(full)
                    base_vectors[base_id], extended_vectors[full_id] = base, full
                    roots[key] = {"base9_id": base_id, "representation_id": full_id, "score_hex": score.hex(),
                        "score_exact": exact(score), "actual_lazy_reads": list(actual_reads),
                        "appended_feature_types": [type(values[name]).__name__ for name in added_names],
                        "static_feature_names_not_read_by_this_branch": sorted(set(added_names) - set(actual_reads))}
                root_values.append(roots[key])
            row = {"requirement_id": "r" + str(index), "stage": stage, "source": source, "query_id": query_id, "side": side,
                "preferred_base9_id": root_values[0]["base9_id"], "other_base9_id": root_values[1]["base9_id"],
                "preferred_vector_id": root_values[0]["representation_id"], "other_vector_id": root_values[1]["representation_id"],
                "preferred": root_values[0], "other": root_values[1]}
            expected = fit_checks[row["requirement_id"]]
            require(expected["arithmetic_error"] is None and root_values[0]["score_hex"] == expected["score_preferred_hex"]
                    and root_values[1]["score_hex"] == expected["score_other_hex"], "Diagnostic score differs from deployed frozen scorefit")
            rows.append(row)
    finally:
        execution._LazyScoreLocals = original_lazy
    base_rows = [dict(row, preferred_vector_id=row["preferred_base9_id"], other_vector_id=row["other_base9_id"]) for row in rows]
    base_gate, extended_gate = quotient(base_vectors, base_rows), quotient(extended_vectors, rows)
    scores_by_vector = defaultdict(set)
    for root in roots.values():
        scores_by_vector[root["representation_id"]].add(root["score_exact"])
    # Numeric normalization never silently stands in for a deterministic runtime.
    inconsistent_score_keys = [key for key, values in scores_by_vector.items() if len(values) > 1]
    require(not inconsistent_score_keys, "Equal extended numeric vectors produced unequal deployed scores; gate cannot establish pointwise contradiction")
    return {"program_id": item["id"], "arm": item["arm"], "split": "TRAIN", "source_ids": list(SOURCES),
        "features_appended": added_names, "declared_unreferenced_features_excluded": sorted({name for name, _ in program._expressions} - set(added_names)),
        "representation_definition": "original complete nine exact numeric values followed by co_names-referenced additional library feature return values",
        "base_feature_order": list(FEATURES), "exact_value_namespace": execution.NAMESPACE + ":returned_numeric_Fraction_key",
        "original_base9_quotient": base_gate, "extended_quotient": extended_gate,
        "extension_breaks_prior_cyclic_requirements": sorted(set(base_gate["cyclic_requirement_ids"]) - set(extended_gate["cyclic_requirement_ids"])),
        "strict_fit": {"passed": fit["passed_requirements"], "total": 743, "exact": str(Fraction(fit["passed_requirements"], 743))},
        "static_feature_input_not_read_root_occurrences": sum(bool(root["static_feature_names_not_read_by_this_branch"]) for root in roots.values()),
        "root_occurrences_evaluated": len(roots), "unique_states": len(states),
        "equal_vector_different_score_count": len(inconsistent_score_keys),
        "static_access_caveat": "co_names includes features in conditional branches not always read; acyclicity is potential representation consistency, not proof that the chosen score actually uses the distinction",
        "rows": rows, "vectors": extended_vectors, "base_vectors": base_vectors,
        "offline_diagnostic_feature_work": sum(evaluator.meter["feature_work"] for evaluator in states.values()),
        "offline_diagnostic_wall_seconds": time.perf_counter() - started,
        "work_scope": "materializing fullbase9 plus static named library features on TRAIN residual states only; not deployment cost or a new optimizer run",
        "execution_module_sha256": digest(Path(execution.__file__)), "fit_execution_module_sha256": fit["execution_module_sha256"],
        "VAL_data_read": False, "TEST_data_read": False, "new_solver_calls": 0, "new_model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-selection", type=Path, required=True, help="Frozen finalselection IDs only; no VAL graph/results are opened")
    parser.add_argument("--expected-program-count", type=int, default=7, help="Explicit frozen diagnostic count; default is the7 main selected programs")
    parser.add_argument("--program-bank", type=Path, action="append", required=True)
    parser.add_argument("--fit-root", type=Path, action="append", required=True)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    selection = read(args.final_selection)
    identifiers = sorted({group["selected_id"] for group in selection["groups"].values()}) if "groups" in selection else sorted(selection["program_ids"])
    require(len(identifiers) == len(set(identifiers)) == args.expected_program_count,
            "Frozen program count does not match explicit requested scope")
    items, bank_inputs = load_banks(args.program_bank)
    require(set(identifiers) <= items.keys(), "Final selected program absent from frozen bank")
    context, profile, requirements, queries, graphs, inventory = load_train(args.data_root.resolve())
    summary = []
    for identifier in identifiers:
        item = items[identifier]
        fit, fit_path = load_fit(item, args.fit_root)
        require(fit["execution_module_sha256"] == digest(Path(execution.__file__)), "Frozen fit/scorer mismatch")
        result = analyse(item, fit, requirements, queries, graphs)
        result["inputs_sha256"] = dict(inventory, **bank_inputs)
        result["inputs_sha256"][str(fit_path)] = digest(fit_path)
        result["finalselection_sha256"] = digest(args.final_selection)
        destination = args.output_root / (identifier + ".json")
        freeze_json(destination, result)
        row = {key: result[key] for key in ("program_id", "arm", "features_appended", "strict_fit", "static_feature_input_not_read_root_occurrences")}
        row.update(base9_cyclic_SCC=result["original_base9_quotient"]["cyclic_SCC_count"],
            extended_cyclic_SCC=result["extended_quotient"]["cyclic_SCC_count"],
            base9_opposite_pairs=result["original_base9_quotient"]["opposite_direction_pair_count"],
            extended_opposite_pairs=result["extended_quotient"]["opposite_direction_pair_count"],
            representation_consistent=result["extended_quotient"]["finite_strict_pointwise_representation_consistent"],
            report_sha256=digest(destination), report_file=destination.name)
        summary.append(row)
        print(encoded(row), flush=True)
    freeze_json(args.output_root / "information_gate_summary.json", {"version": "selected_program_TRAIN_information_gate_v1", "programs": summary,
        "scope": "All743 existingTRAIN labels; final IDs read from selection but no VAL graph/value artifact is opened; no new performance selection or oracle",
        "context_sha256": profile["context_sha256"], "finalselection_sha256": digest(args.final_selection),
        "VAL_graph_data_read": False, "TEST_data_read": False, "new_solver_calls": 0, "new_model_calls": 0})


if __name__ == "__main__":
    main()
