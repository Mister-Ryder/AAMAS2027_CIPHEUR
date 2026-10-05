"""Evaluate every frozen TRAIN strict requirement with the deployment scorer.

This is score evaluation only, not optimization. No VAL/TEST data is read.
Scores are returned by StationLocalEvaluator and their binary values are then
compared exactly as Fraction(score), at the declared decimal score margin.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
import sys
import time

from train_context import PROJECT, DEFAULT_DATA, SOURCES, TAGS, digest, encoded, require

sys.path.insert(0, str(PROJECT))
from cipheur.graph_features import FeatureRuleProgram
from cipheur.repair_v06 import _Meter
from full_schedule_execution import load_graph, StationLocalEvaluator, NAMESPACE


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate(bank_path, data_root, output_root, context_root, program_id=None, margin="0.00000001"):
    bank = read(bank_path)
    candidates = [p for p in bank["programs"] if program_id is None or p["id"] == program_id]
    require(candidates and (program_id is None or len(candidates) == 1), "Candidate id must resolve")
    context = read(context_root / "context" / "train_context.json")
    profile = read(context_root / "context" / "train_context_profile.json")
    require(digest(context_root / "context" / "train_context.json") == profile["context_sha256"], "TRAIN context changed")
    snapshot = read(context_root / "context" / "train_evidence_snapshot.json")
    require(digest(context_root / "context" / "train_evidence_snapshot.json") == profile["evidence_snapshot_sha256"], "Evidence changed")
    requirements = snapshot["raw_strict_requirements"]
    require(len(requirements) == len(context["common"]["strict_relations"]) == 743,
            "Every one of the743 frozen requirements must be evaluated")
    require(all(row["source"] in SOURCES for row in requirements), "Evidence outside TRAIN")
    inventory = {}

    def expected_suffix(path, suffix):
        matches = [v["sha256"] for k, v in profile["input_inventory"].items() if k.replace("\\", "/").endswith(suffix)]
        require(len(matches) == 1 and digest(path) == matches[0], "Frozen input mismatch: " + suffix)
        inventory[str(path)] = digest(path)

    stages = dict(p0=data_root / "analysis" / "p0", expanded=data_root / "analysis" / "patch_interface_probe",
                  heterogeneous=data_root / "extensions" / "heterogeneous_ground_v1" / "analysis" / "quad_evidence")
    queries = {}
    for stage, folder in stages.items():
        for source in SOURCES:
            path = folder / source / "query_manifest.json"
            suffix = ("/analysis/p0/" if stage == "p0" else "/analysis/patch_interface_probe/" if stage == "expanded"
                      else "/extensions/heterogeneous_ground_v1/analysis/quad_evidence/") + source + "/query_manifest.json"
            expected_suffix(path, suffix)
            manifest = read(path)
            require(manifest["prepared_before_labels"], "Query manifest was not prepared before labels")
            for query in manifest["queries"]:
                queries[stage, source, query["id"]] = query
    graphs, load_receipts = {}, {}
    graph_root = data_root / "extensions" / "heterogeneous_ground_v1" / "graphs"
    for source in SOURCES:
        manifest = read(stages["heterogeneous"] / source / "query_manifest.json")
        for side, tag in TAGS.items():
            npz, meta = graph_root / source / (tag + ".npz"), graph_root / source / (tag + ".json")
            require(digest(npz) == manifest["graph_npz_sha256"][side], "Graph differs from formal TRAIN evidence")
            meter = _Meter(None, "cpu", None, 0)
            graph, receipt = load_graph(npz, meta, meter)
            require(graph.provenance["metadata"]["source_id"] == source, "Graph source mismatch")
            graphs[source, side] = graph
            load_receipts[source + ":" + side] = receipt
            inventory[str(npz)], inventory[str(meta)] = digest(npz), digest(meta)

    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    exact_margin = Fraction(margin)
    for candidate in candidates:
        started_cpu, started_wall = time.process_time(), time.perf_counter()
        program = FeatureRuleProgram.from_dict(candidate["program"])
        require(not ("rule_only" in candidate.get("arm", "") and program.features), "Rule-only has extra features")
        states, score_cache, checks = {}, {}, []
        for index, requirement in enumerate(requirements):
            stage, source, query_id, side = (requirement[k] for k in ("stage", "source", "query_id", "side"))
            side = dict(left="A", right="J").get(side, side)
            require(side in TAGS, "Unexpected configuration")
            query = queries[stage, source, query_id]
            graph = graphs[source, side]
            # Original manifests define exactly the same frozen variableP domain.
            # No new boundary or oracle query is formed here.
            state_key = (source, side, query["patch_indices_sha256"])
            preferred, other = requirement["preferred_contact_id"], requirement["other_contact_id"]
            row = dict(requirement_id="r" + str(index), stage=stage, source=source,
                       query_id=query_id, side=side, preferred_contact_id=preferred, other_contact_id=other)
            try:
                if state_key not in states:
                    ids = tuple(graph.nodes)
                    active = {ids[i] for i in query["patch_indices"]}
                    require(preferred in active and other in active, "Compared root is outside recordedP")
                    meter = {}
                    evaluator = StationLocalEvaluator(graph, program, active, meter, score_slice=True)
                    states[state_key] = (evaluator, meter)
                evaluator, meter = states[state_key]
                scores = []
                for node in (preferred, other):
                    key = (state_key, node)
                    if key not in score_cache:
                        score_cache[key] = evaluator.score(node)
                    scores.append(score_cache[key])
                gap = Fraction(scores[0]) - Fraction(scores[1])
                row.update(passed=gap > exact_margin, score_preferred=scores[0], score_other=scores[1],
                           score_preferred_hex=scores[0].hex(), score_other_hex=scores[1].hex(),
                           exact_binary_score_gap=str(gap), arithmetic_error=None)
            except Exception as error:
                row.update(passed=False, arithmetic_error=type(error).__name__ + ":" + str(error))
            checks.append(row)
        counts = Counter(r["stage"] for r in checks if r["passed"])
        denominators = Counter(r["stage"] for r in checks)
        result = dict(program_id=candidate["id"], arm=candidate.get("arm"), split="TRAIN", source_ids=list(SOURCES),
            total_requirements=743, passed_requirements=sum(r["passed"] for r in checks),
            strict_fit_fraction=sum(r["passed"] for r in checks) / 743,
            score_margin_exact=str(exact_margin), comparison="exact rational comparison of returned binary float scores",
            numeric_namespace=NAMESPACE, actual_scorer="full_schedule_execution.StationLocalEvaluator.score(score_slice=True)",
            passed_by_stage=dict(counts), total_by_stage=dict(denominators),
            arithmetic_error_count=sum(r["arithmetic_error"] is not None for r in checks),
            unique_score_states=len(states), scored_root_occurrences=len(score_cache),
            offline_fit_feature_work=sum(m.get("feature_work", 0) for _, m in states.values()),
            offline_fit_cpu_seconds=time.process_time() - started_cpu,
            offline_fit_wall_seconds=time.perf_counter() - started_wall,
            cost_scope="Cached offline score-fit evaluation only; does not replace complete-schedule charged cost",
            feature_count=len(program.features), candidate_program=candidate["program"], checks=checks,
            VAL_read=False, TEST_read=False, optimizer_calls=0, model_calls=0,
            program_bank_sha256=digest(bank_path), execution_module_sha256=digest(Path(__file__).with_name("full_schedule_execution.py")),
            context_sha256=profile["context_sha256"], input_inventory=inventory)
        destination = output_root / (candidate["id"].replace("|", "_").replace(":", "_") + ".json")
        require(not destination.exists(), "Do not overwrite a fit result")
        destination.write_text(encoded(result) + "\n", encoding="utf-8")
        results.append({k: result[k] for k in ("program_id", "arm", "strict_fit_fraction", "passed_requirements", "total_requirements",
                       "passed_by_stage", "total_by_stage", "arithmetic_error_count", "offline_fit_feature_work", "offline_fit_cpu_seconds")})
        print(encoded(results[-1]), flush=True)
    return results


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-bank", type=Path, required=True)
    parser.add_argument("--program-id")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--context-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--score-margin", default="0.00000001")
    args = parser.parse_args()
    evaluate(args.program_bank, args.data_root.resolve(), args.output_root.resolve(), args.context_root.resolve(),
             args.program_id, args.score_margin)


if __name__ == "__main__":
    main()
