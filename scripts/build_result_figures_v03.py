"""Source-backed v03 quantitative analysis and publication figures.

Archives are read directly and never extracted into the repository. Development
and unbounded follow-ups remain separate from complete cooperative003 primary
evaluation. Cluster bootstrap retains both sides,
all conditions, shared temporal seeds across regimes, and C3 source blocks.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys
import tarfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "experiments" / "runs" / "v03"
OUT = ROOT / "experiments" / "analysis" / "v03"
FIGURES = ROOT / "paper" / "figures"
BLUE, ORANGE, GRAY, INK, PURPLE = "#176B9B", "#D36B32", "#687782", "#243640", "#71559C"
SEED, REPLICATIONS = 20261003, 2000
_BOOTSTRAP_WEIGHTS = {}
CONDITIONS = [("anchored", "weighted_clique_cover"),
              ("uniform", "weighted_clique_cover"), ("anchored", "weight_sum")]
LABELS = ["Ranked / clique", "Uniform / clique", "Ranked / sum"]


def archive(name):
    path = RUNS / (name + ".tar.gz")
    result = {}
    with tarfile.open(path) as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith((".json", ".jsonl")):
                content = tar.extractfile(member).read().decode("utf-8")
                key = Path(member.name).name
                result[key] = ([json.loads(row) for row in content.splitlines() if row]
                               if key.endswith("jsonl") else json.loads(content))
    result["_provenance"] = {"path": path.relative_to(ROOT).as_posix(),
                             "sha256": sha256(path.read_bytes()).hexdigest()}
    return result


def cluster_identity(pair):
    """Disjoint C3 source subproblem is its block; temporal regimes share seed."""
    if pair["family"].startswith("temporal_"):
        return "temporal", str(pair["source"]["seed"])
    if pair["family"].startswith("dense_long_"):
        return "dense_long", str(pair["source"]["seed"])
    if pair["family"] == "c3":
        return "c3", pair["id"]
    return "diagnostic", pair["id"]


def clustered_interval(rows, value, pair_map, statistic="mean", seed=SEED):
    """Stratified percentile bootstrap of clusters, preserving every row.

    Strata keep the temporal/C3/probe mixture fixed. Shared seeds are the
    temporal sampling unit, not a regime-specific pair or graph context.
    """
    if not rows:
        return None
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        stratum, cluster = cluster_identity(pair_map[row["id"]])
        groups[stratum][cluster].append(float(value(row)))
    arrays = {s: [np.asarray(v) for _, v in sorted(clusters.items())]
              for s, clusters in sorted(groups.items())}
    raw = np.asarray([value(row) for row in rows], dtype=float)
    if not np.isfinite(raw).any():
        return None
    func = np.nanmean if statistic == "mean" else np.nanmedian
    observed = float(func(raw))
    rng = np.random.default_rng(seed)
    if statistic == "mean":
        # Resample the full assignment frame even for completed-case means.
        # A failed row has NaN here, not a missing source cluster or zero reward.
        sizes = tuple(len(blocks) for blocks in arrays.values())
        cache_key = (sizes, seed, REPLICATIONS)
        if cache_key not in _BOOTSTRAP_WEIGHTS:
            weights = [np.zeros((REPLICATIONS, n), dtype=int) for n in sizes]
            for w, n in zip(weights, sizes):
                draws = rng.integers(0, n, size=(REPLICATIONS, n))
                for replication, indices in enumerate(draws):
                    w[replication] = np.bincount(indices, minlength=n)
            _BOOTSTRAP_WEIGHTS[cache_key] = weights
        numerator, denominator = np.zeros(REPLICATIONS), np.zeros(REPLICATIONS)
        for blocks, weights in zip(arrays.values(), _BOOTSTRAP_WEIGHTS[cache_key]):
            numerator += weights @ np.asarray([np.nansum(b) for b in blocks])
            denominator += weights @ np.asarray([np.isfinite(b).sum() for b in blocks])
        estimates = numerator[denominator > 0] / denominator[denominator > 0]
    else:
        estimates = []
        for _ in range(REPLICATIONS):
            sample = []
            for blocks in arrays.values():
                for index in rng.integers(0, len(blocks), size=len(blocks)):
                    sample.extend(blocks[index])
            if np.isfinite(sample).any():
                estimates.append(func(sample))
    lo, hi = np.quantile(estimates, [.025, .975])
    return {"estimate": observed, "lower": float(lo), "upper": float(hi),
            "level": .95, "statistic": statistic, "rows": len(rows), "finite_rows": int(np.isfinite(raw).sum()),
            "clusters": {s: len(v) for s, v in arrays.items()},
            "method": "stratified_cluster_percentile_bootstrap", "replications": REPLICATIONS,
            "seed": seed}


def evidence_summary(mechanisms, pair_map):
    result = []
    rows = mechanisms["evidence_results.jsonl"]
    assert len(rows) == 186 and len({r["id"] for r in rows}) == 62
    for condition, label in zip(CONDITIONS, LABELS):
        selected = [r for r in rows if (r["strategy"], r["upper_method"]) == condition]
        assert len(selected) == 62
        group_rows = []
        for population in ("all", "diagnostic", "non_diagnostic"):
            subset = [r for r in selected if population == "all" or
                      (r["family"] == "diagnostic") == (population == "diagnostic")]
            specs = [s for r in subset for s in r["specifications"]]
            counts = Counter(s["relation"] for s in specs)
            reasons = Counter(a["reason"] for r in subset for a in r["attempts"])
            group_rows.append({"population": population, "pairs": len(subset),
                               "attempts": sum(len(r["attempts"]) for r in subset),
                               "certified_relations": len(specs), "relation_counts": dict(counts),
                               "pairs_with_certificate": sum(bool(r["specifications"]) for r in subset),
                               "attempt_reasons": dict(reasons),
                               "expanded_nodes": sum(r["budget"]["expanded_nodes"] for r in subset),
                               "conditional_calls": sum(r["budget"]["calls"] for r in subset),
                               "task_seconds_sum": sum(r["seconds"] for r in subset),
                               "relations_per_pair": clustered_interval(subset,
                                   lambda r: len(r["specifications"]), pair_map)})
        families = {}
        for family in sorted({r["family"] for r in selected}):
            subset = [r for r in selected if r["family"] == family]
            families[family] = {"pairs": len(subset), "attempts": sum(len(r["attempts"]) for r in subset),
                                "relation_counts": dict(Counter(s["relation"] for r in subset for s in r["specifications"])),
                                "attempt_reasons": dict(Counter(a["reason"] for r in subset for a in r["attempts"]))}
        result.append({"label": label, "strategy": condition[0], "upper_method": condition[1],
                       "populations": group_rows, "families": families})
    # Paired differences keep every arm outcome on the same sampled pair.
    natural = [r for r in rows if r["family"] != "diagnostic"]
    indexed = {(r["id"], r["strategy"], r["upper_method"]): r for r in natural}
    base = [r for r in natural if (r["strategy"], r["upper_method"]) == CONDITIONS[0]]
    deltas = {}
    for other in CONDITIONS[1:]:
        deltas[f"ranked_clique_minus_{other[0]}_{other[1]}"] = clustered_interval(base,
            lambda r: len(r["specifications"]) - len(indexed[(r["id"], *other)]["specifications"]), pair_map)
    return {"conditions": result, "non_diagnostic_paired_differences_relations_per_pair": deltas}


def quotient_summary(mechanisms):
    from cipheur.graph_features import FeatureRuleProgram
    from cipheur.representation import diagnose_representation
    specs = mechanisms["train_specifications.json"]
    base = FeatureRuleProgram("analysis_base", [], "weight")
    outputs = {}
    for name, subset in (("all", specs), ("diagnostic", [s for s in specs if s["family"] == "diagnostic"]),
                         ("non_diagnostic", [s for s in specs if s["family"] != "diagnostic"])):
        d = diagnose_representation(base, subset)
        outputs[name] = {k: d[k] for k in ("quotient_nodes", "quotient_edges", "self_loop_requirements", "contradictory")}
        outputs[name]["specifications"] = len(subset)
    archived = mechanisms["initial_diagnosis.json"]
    for key in ("quotient_nodes", "quotient_edges", "self_loop_requirements", "contradictory"):
        assert outputs["all"][key] == archived[key]
    repair = mechanisms["repair.json"]
    outputs["repair"] = {k: repair[k] for k in ("selected_names", "cost", "cost_exact", "repaired", "optimal",
                                               "master_subsets_evaluated", "objective_scope", "feature_costs")}
    outputs["repaired_quotient"] = {k: repair["diagnosis"][k] for k in
                                   ("quotient_nodes", "quotient_edges", "self_loop_requirements", "contradictory")}
    assert outputs["all"]["self_loop_requirements"] == 64
    assert outputs["non_diagnostic"]["self_loop_requirements"] == 0
    return outputs


def discovery_summary(discovery, frozen, pair_map):
    rows = discovery["candidate_assessments.jsonl"]
    assert len(rows) == 97
    indexed = {r["name"]: r for r in rows}
    assert len(indexed) == len(rows)
    source_details = {r["label"]: r for r in frozen["selection_details"]}
    selected = {}
    for arm, program in frozen["programs"].items():
        r = indexed[program["name"]]
        families = {}
        for population in ("all", "diagnostic", "temporal", "c3", "non_diagnostic"):
            subset = [x for x in r["rows"] if x["ratio"] is not None and
                      (population == "all" or (population == "diagnostic" and x["family"] == "diagnostic") or
                       (population == "temporal" and x["family"].startswith("temporal_")) or
                       (population == "c3" and x["family"] == "c3") or
                       (population == "non_diagnostic" and x["family"] != "diagnostic"))]
            families[population] = {"contexts": len(subset), "pairs": len({x["id"] for x in subset}),
                                    "quality": clustered_interval(subset, lambda x: x["ratio"], pair_map),
                                    "mean_work": statistics.fmean(x["feature_work"] for x in subset) if subset else None}
        selected[arm] = {"name": program["name"], "quality_validation_mix": r["quality"],
                         "mean_feature_work_validation_mix": r["feature_work"],
                         "consistency": r["consistency"], "observed_quotient_cyclic": r["contradictory"],
                         "features": len(program["features"]), "family_summaries": families,
                         "selection_detail": source_details.get(arm)}
    for curve in frozen["joint_prefix_curves"]:
        r = indexed[curve["name"]]
        assert abs(curve["quality"] - r["quality"]) < 1e-12
    guided_rows = indexed[frozen["programs"]["guided"]["name"]]["rows"]
    paired_differences = {}
    for arm in ("free", "rule", "enumerated", "guided_one_feature", "guided_no_cost",
                "guided_minimum_interface", "guided_natural_validation"):
        other = {(x["id"], x["side"]): x for x in indexed[frozen["programs"][arm]["name"]]["rows"]}
        paired_differences["guided_minus_" + arm] = {}
        for population in ("all", "non_diagnostic", "temporal", "c3"):
            subset = [x for x in guided_rows if population == "all" or
                      (population == "non_diagnostic" and x["family"] != "diagnostic") or
                      (population == "temporal" and x["family"].startswith("temporal_")) or
                      (population == "c3" and x["family"] == "c3")]
            paired_differences["guided_minus_" + arm][population] = clustered_interval(subset,
                lambda x: x["ratio"] - other[(x["id"], x["side"])]["ratio"], pair_map)
    return {"candidate_counts": dict(Counter(r["arm"] for r in rows)),
            "frozen_joint_receipt": {k: frozen[k] for k in ("test_accessed", "candidate_budget_per_arm",
                "assistant_generation_calls_per_arm", "API_calls", "selection", "known_scope", "protocol")},
            "model_provenance": {"model": "gpt-6.1-sol", "reasoning_effort": "ultra",
                                 "authority": "root_verified_session_turn_context", "tokens": None},
            "prefix_curves": frozen["joint_prefix_curves"], "selected": selected,
            "paired_validation_quality_differences": paired_differences,
            "validation_contexts": discovery["complete.json"]["validation_contexts"],
            "assessment_seconds_sum": sum(r["seconds"] for r in rows),
            "all_schedules_feasible": all(x["feasible"] for r in rows for x in r["rows"]),
            "interpretation": "one independently authored bank per arm; selection gates differ; no model-level generation replication"}


def runtime_summary(mechanisms, pair_map):
    contexts = []
    for r in mechanisms["runtime_results.jsonl"]:
        assert r["equivalent_traces"]
        assert len(r["runs"]) == 6 and all(x["feasible"] for x in r["runs"])
        med = {b: {key: statistics.median(x[key] for x in r["runs"] if x["backend"] == b)
                   for key in ("seconds", "feature_work")} for b in ("reference", "compiled")}
        compiled = [x for x in r["runs"] if x["backend"] == "compiled"]
        assert all(x["feature_work"] == x["initialization_work"] + x["update_work"] + x["query_work"] for x in compiled)
        contexts.append({"id": r["id"], "side": r["side"], "family": r["family"], "n": r["n"], "m": r["m"],
                         "speedup": med["reference"]["seconds"] / med["compiled"]["seconds"],
                         "work_reduction": med["reference"]["feature_work"] / med["compiled"]["feature_work"],
                         "reference_seconds": med["reference"]["seconds"], "compiled_seconds": med["compiled"]["seconds"],
                         "phase_work": {k: statistics.median(x[k] for x in compiled) for k in
                                        ("initialization_work", "update_work", "query_work")},
                         "compiled_work": med["compiled"]["feature_work"]})
    sizes = []
    for n in sorted({r["n"] for r in contexts}):
        subset = [r for r in contexts if r["n"] == n]
        total = sum(r["compiled_work"] for r in subset)
        sizes.append({"n": n, "contexts": len(subset), "pairs": len({r["id"] for r in subset}),
                      "families": dict(Counter(r["family"] for r in subset)),
                      "speedup": clustered_interval(subset, lambda r: r["speedup"], pair_map, "median"),
                      "work_reduction": clustered_interval(subset, lambda r: r["work_reduction"], pair_map, "median"),
                      "phase_work_share": {k: sum(r["phase_work"][k] for r in subset)/total for k in
                                           ("initialization_work", "update_work", "query_work")},
                      "median_seconds": {b: statistics.median(r[b+"_seconds"] for r in subset)
                                         for b in ("reference", "compiled")}})
    return {"contexts": len(contexts), "pairs": len({r["id"] for r in contexts}),
            "repetitions_per_backend_context": 3, "matched_traces": len(contexts),
            "sizes": sizes, "context_rows": contexts,
            "scope": "fixed structural_runtime edge-min-weight-sum feature and ranking rule",
            "timing_aggregation": "median of 3 runs per backend/context, then median of paired context ratios",
            "phase_share_aggregation": "ratio of summed compiled phase work to summed total work"}


def scalability_summary(study):
    """Development-only large-graph stress run, without frozen v03 programs."""
    rows = study["results.jsonl"]
    pair_map = {p["id"]: p for split in study["data.json"].values() for p in split}
    assert len(rows) == study["complete.json"]["completed"] == 56
    assert len({(r["id"], r["side"]) for r in rows}) == len(rows)
    groups = []
    for family, n in sorted({(r["family"], r["n"]) for r in rows}):
        subset = [r for r in rows if (r["family"], r["n"]) == (family, n)]
        methods = {}
        for method in sorted({m["method"] for r in subset for m in r["methods"]}):
            values = [{"id": r["id"], "side": r["side"], "quality": m["value"] / r["reference"]["upper"],
                       "seconds": m["seconds"], "feature_work": m.get("feature_work")}
                      for r in subset for m in r["methods"] if m["method"] == method]
            methods[method] = {"quality": clustered_interval(values, lambda x: x["quality"], pair_map),
                               "median_seconds": statistics.median(x["seconds"] for x in values),
                               "mean_work": statistics.fmean(x["feature_work"] for x in values)
                               if all(x["feature_work"] is not None for x in values) else None}
        groups.append({"family": family, "n": n, "contexts": len(subset),
                       "pairs": len({r["id"] for r in subset}),
                       "reference_status": dict(Counter(str(r["reference"]["solver_status"]) for r in subset)),
                       "reference_gap_range": [min(r["reference"]["mip_gap"] for r in subset),
                                               max(r["reference"]["mip_gap"] for r in subset)],
                       "methods": methods})
    return {"completion": study["complete.json"], "execution": study["execution.json"],
            "contexts": len(rows), "pairs": len(pair_map), "groups": groups,
            "all_schedules_feasible": all(m["feasible"] for r in rows for m in r["methods"]),
            "reference_status": dict(Counter(str(r["reference"]["solver_status"]) for r in rows)),
            "scope": "large development stress screen; existing baselines only; no frozen v03 guided program"}


def relevance_summary(study, mechanisms, pair_map):
    specs = {s["id"]: s for s in mechanisms["train_specifications.json"]}
    result = {"receipt": study["complete.json"], "programs": {},
              "regret_scope": "actual next action at reachable saved boundary; offline branch-node bounded reference; weight units",
              "original_bank_scope": "51 acquired rollout specifications; certificate-selected training sample"}
    for filename, report in study.items():
        if filename.startswith("_") or filename == "complete.json":
            continue
        arm = filename.removesuffix(".json")
        rows = [{**r, "id": specs[r["specification"]]["acquisition"]["id"],
                 "family": specs[r["specification"]]["family"]} for r in report["rows"]]
        assert len(rows) == 102
        populations = {}
        for population in ("all", "diagnostic", "non_diagnostic", "temporal", "c3"):
            subset = [r for r in rows if population == "all" or
                      (population == "diagnostic" and r["family"] == "diagnostic") or
                      (population == "non_diagnostic" and r["family"] != "diagnostic") or
                      (population == "temporal" and r["family"].startswith("temporal_")) or
                      (population == "c3" and r["family"] == "c3")]
            reached = [r for r in subset if r["boundary_reachable"]]
            regrets = [r for r in reached if r.get("conditional_regret") is not None]
            choices = [r for r in subset if r["chosen_action_consistent"] is not None]
            actual_choices = [r for r in reached if r["chosen_action_consistent"] is not None]
            assert len(regrets) == len(reached)
            populations[population] = {
                "side_requirements": len(subset), "reachable": len(reached),
                "all_boundary_escape": sum(r["next_action_escape"] for r in subset),
                "reachable_escape": sum(r["next_action_escape"] for r in reached),
                "all_boundary_pair_choices": len(choices),
                "all_boundary_consistent_pair_choices": sum(r["chosen_action_consistent"] for r in choices),
                "reachable_pair_choices": len(actual_choices),
                "reachable_consistent_pair_choices": sum(r["chosen_action_consistent"] for r in actual_choices),
                "reachability_fraction": clustered_interval(subset, lambda r: r["boundary_reachable"], pair_map),
                "reachable_escape_fraction": clustered_interval(reached, lambda r: r["next_action_escape"], pair_map),
                "regret_observed_rows": len(regrets),
                "exact_regret_rows": sum(r["conditional_regret"]["reference_exact"] and
                                          r["conditional_regret"]["chosen_completion_exact"] for r in regrets),
                "certified_positive_regret_rows": sum(r["conditional_regret"]["lower"] > 0 for r in regrets),
                "certified_zero_regret_rows": sum(r["conditional_regret"]["upper"] == 0 for r in regrets),
                "unresolved_zero_vs_positive_rows": sum(r["conditional_regret"]["lower"] == 0 and
                                                         r["conditional_regret"]["upper"] > 0 for r in regrets),
                "mean_regret_bound": [statistics.fmean(r["conditional_regret"][k] for r in regrets)
                                      for k in ("lower", "upper")] if regrets else None,
                "mean_lower_regret_cluster_ci": clustered_interval(regrets,
                    lambda r: r["conditional_regret"]["lower"], pair_map),
                "mean_upper_regret_cluster_ci": clustered_interval(regrets,
                    lambda r: r["conditional_regret"]["upper"], pair_map),
                "oracle_expanded_nodes": sum(r["conditional_regret"]["expanded_nodes"] for r in regrets)}
        result["programs"][arm] = {"saved_totals": {k: v for k, v in report.items() if k != "rows"},
                                   "populations": populations, "rows": rows}
    return result


def inference_summary(study, frozen, budget_scope):
    """Keep assigned contexts, completed schedules and timeouts distinct."""
    rows = study["results.jsonl"]
    pairs = {p["id"]: p for split in study["data.json"].values() for p in split}
    assert len({(r["id"], r["side"]) for r in rows}) == len(rows)
    assert study["execution.json"]["frozen_sha256"] == sha256(
        (ROOT / "experiments/discovery/v03/frozen_joint_001.json").read_bytes()).hexdigest()
    flattened = []
    for r in rows:
        for method in r["methods"]:
            completed = method.get("completed", method.get("value") is not None)
            assert completed == (method.get("value") is not None)
            if method["method"] in frozen["programs"]:
                assert method["program_name"] == frozen["programs"][method["method"]]["name"]
            flattened.append({**method, "id": r["id"], "side": r["side"], "family": r["family"],
                              "n": r["n"], "completed": completed,
                              "quality_zero_normalized": method["value"] / r["reference"]["upper"]
                              if completed else 0.0})
    groups = []
    selectors = [("all", lambda r: True),
                 ("non_diagnostic", lambda r: r["family"] != "diagnostic"),
                 ("temporal", lambda r: r["family"].startswith("temporal_")),
                 ("dense_long", lambda r: r["family"].startswith("dense_long_"))] + [(f, lambda r, f=f: r["family"] == f)
                 for f in sorted({r["family"] for r in rows})] + [
                 ("n_" + str(n), lambda r, n=n: r["n"] == n) for n in sorted({r["n"] for r in rows})]
    for label, select in selectors:
        if not any(select(r) for r in rows):
            continue
        methods = {}
        for method in sorted({r["method"] for r in flattened}):
            subset = [r for r in flattened if r["method"] == method and select(r)]
            done = [r for r in subset if r["completed"]]
            work_rows = [r for r in done if r.get("feature_work") is not None]
            methods[method] = {"assigned_contexts": len(subset), "completed_contexts": len(done),
                               "failed_contexts": len(subset)-len(done),
                               "completed_feasible": sum(r.get("feasible") is True for r in done),
                               "completion_rate": clustered_interval(subset, lambda r: r["completed"], pairs),
                               "all_context_quality_zero_normalized": clustered_interval(subset,
                                  lambda r: r["quality_zero_normalized"], pairs),
                               "completed_context_quality": clustered_interval(subset,
                                  lambda r: r["quality_zero_normalized"] if r["completed"] else float("nan"), pairs),
                               "mean_wall_seconds_all_contexts": clustered_interval(subset, lambda r: r["seconds"], pairs),
                               "median_wall_seconds_all_contexts": statistics.median(r["seconds"] for r in subset),
                               "median_wall_seconds_completed": statistics.median(r["seconds"] for r in done) if done else None,
                               "median_cpu_seconds_all_contexts": statistics.median(r["cpu_seconds"] for r in subset)
                               if all(r.get("cpu_seconds") is not None for r in subset) else None,
                               "mean_cpu_seconds_all_contexts": clustered_interval(subset, lambda r: r["cpu_seconds"], pairs)
                               if all(r.get("cpu_seconds") is not None for r in subset) else None,
                               "cpu_above_five_seconds": sum(r.get("cpu_seconds", 0) > 5 for r in subset),
                               "mean_feature_work_completed": statistics.fmean(r["feature_work"] for r in work_rows)
                               if len(work_rows) == len(done) and done else None,
                               "cost_scope": "wall/CPU all assigned rows; feature work completed schedules only"}
        group_rows = [r for r in rows if select(r)]
        groups.append({"population": label, "contexts": len(group_rows),
                       "pairs": len({r["id"] for r in group_rows}), "methods": methods})
    comparisons, population_comparisons = {}, {}
    guided = [r for r in flattened if r["method"] == "guided"]
    for arm in ("free", "enumerated", "rule", "guided_one_feature", "guided_minimum_interface",
                "guided_natural_validation", "guided_no_cost",
                "baseline_weighted_conflict", "baseline_v02_joint", "multi_start_1to2_search"):
        other = {(r["id"], r["side"]): r for r in flattened if r["method"] == arm}
        comparisons["guided_minus_" + arm] = clustered_interval(guided,
            lambda r: r["quality_zero_normalized"] - other[(r["id"], r["side"])]["quality_zero_normalized"], pairs)
        for label, select in selectors:
            selected = [r for r in guided if select(r)]
            if selected:
                population_comparisons.setdefault(label, {})["guided_minus_" + arm] = clustered_interval(selected,
                    lambda r: r["quality_zero_normalized"] - other[(r["id"], r["side"])]["quality_zero_normalized"], pairs)
    evidence = study.get("test_evidence.jsonl", [])
    specs = [s for r in evidence for s in r["specifications"]]
    reports = {}
    report_arms = set.intersection(*(set(r["reports"]) for r in evidence)) if evidence else set()
    for arm in sorted(report_arms):
        rankings = [r["reports"][arm]["ranking"] for r in evidence]
        relations = [r["reports"][arm]["relevance"] for r in evidence]
        reports[arm] = {"score_requirements": sum(r["total"] for r in rankings),
                        "score_passed": sum(r["passed"] for r in rankings),
                        **{key: sum(r[key] for r in relations) for key in
                           ("total_side_requirements", "boundary_reachable", "next_action_escape",
                            "pair_choices", "consistent_pair_choices")}}
    from cipheur.graph_features import FeatureRuleProgram
    from cipheur.representation import diagnose_representation
    base_diagnosis = diagnose_representation(FeatureRuleProgram("analysis_base", [], "weight"), specs)
    return {"budget_scope": budget_scope, "completion": study["complete.json"],
            "execution": study["execution.json"], "contexts": len(rows), "pairs": len(pairs),
            "groups": groups, "paired_quality_differences_zero_normalized": comparisons,
            "population_paired_quality_differences_zero_normalized": population_comparisons,
            "reference_scope": "floating HiGHS MILP upper; reward/reference is not a formal optimality certificate",
            "reference_status": dict(Counter(str(r["reference"]["solver_status"]) for r in rows)),
            "reference_gap_range": [min(r["reference"]["mip_gap"] for r in rows),
                                    max(r["reference"]["mip_gap"] for r in rows)],
            "evidence": {"queried_pairs": len(evidence), "certified_specifications": len(specs),
                         "relations": dict(Counter(s["relation"] for s in specs)),
                         "attempt_reasons": dict(Counter(a["reason"] for r in evidence for a in r["attempts"])),
                         "base_quotient": {k: base_diagnosis[k] for k in
                           ("quotient_nodes", "quotient_edges", "self_loop_requirements", "contradictory")},
                         "program_reports": reports},
            "cluster_scope": "temporal and dense_long source seeds across three regimes in separate strata; C3 source block; both graph sides retained",
            "compiler_scope": "full declared interface, score_slice=False; never relabel as v04 demand slicing",
            "interpretation": "supplementary unbounded transfer; never pooled with bounded primary evaluation"
                              if budget_scope == "unbounded" else "primary bounded inference evaluation"}


def program_diagnosis(transfer, dev, discovery, mechanisms, relevance, frozen):
    rows = transfer["results.jsonl"]
    pairs = {p["id"]: p for split in transfer["data.json"].values() for p in split}
    index = {(r["id"], r["side"], m["method"]): m for r in rows for m in r["methods"]}
    controls = ("free", "rule", "enumerated", "guided_one_feature", "guided_minimum_interface",
                "guided_natural_validation", "guided_no_cost", "guided_no_consistency", "guided_no_master",
                "guided_low_penalty", "guided_high_penalty")
    comparisons = {}
    for arm in controls:
        comparisons[arm] = {
            "contexts_identical_value": sum(index[(r["id"], r["side"], "guided")]["value"] ==
                                            index[(r["id"], r["side"], arm)]["value"] for r in rows),
            "contexts_identical_ordered_schedule": sum(index[(r["id"], r["side"], "guided")]["selected"] ==
                                                       index[(r["id"], r["side"], arm)]["selected"] for r in rows),
            "g05_wall_time_divided_by_control": clustered_interval(rows,
                lambda r: index[(r["id"], r["side"], "guided")]["seconds"] /
                          index[(r["id"], r["side"], arm)]["seconds"], pairs, "median"),
            "g05_work_divided_by_control": clustered_interval(rows,
                lambda r: index[(r["id"], r["side"], "guided")]["feature_work"] /
                          index[(r["id"], r["side"], arm)]["feature_work"], pairs, "median")}
    g01_free_equal = all(index[(r["id"], r["side"], "guided_one_feature")]["selected"] ==
                        index[(r["id"], r["side"], "free")]["selected"] and
                        index[(r["id"], r["side"], "guided_one_feature")]["feature_work"] ==
                        index[(r["id"], r["side"], "free")]["feature_work"] for r in rows)
    def structure(data):
        output = []
        for split, ps in data.items():
            for pair in ps:
                if pair["family"] == "diagnostic":
                    continue
                for side in ("left", "right"):
                    graph = pair[side]
                    n = len(graph["contacts"])
                    m = len(graph["edges"])
                    degrees = Counter(v for edge in graph["edges"] for v in edge)
                    output.append({"id": pair["id"], "side": side, "family": pair["family"],
                                   "n": n, "density": 2*m/(n*(n-1)),
                                   "mean_degree": 2*m/n, "mean_retained_count": n-1-2*m/n,
                                   "mean_retained_fraction": (n-1-2*m/n)/n,
                                   "neighbor_pair_checks": sum(d*(d-1)//2 for d in degrees.values())})
        result = []
        for family, n in sorted({(r["family"], r["n"]) for r in output}):
            group = [r for r in output if (r["family"], r["n"]) == (family, n)]
            result.append({"family": family, "n": n, "contexts": len(group),
                           **{k: statistics.fmean(r[k] for r in group) for k in
                              ("density", "mean_degree", "mean_retained_count", "mean_retained_fraction",
                               "neighbor_pair_checks")}})
        return result
    schedule_lengths = {}
    candidates = {r["name"]: r for r in discovery["candidate_assessments.jsonl"]}
    for arm in ("guided", "guided_one_feature", "guided_minimum_interface", "guided_natural_validation", "guided_no_cost"):
        validation = candidates[frozen["programs"][arm]["name"]]["rows"]
        scopes = {"development_validation": [r for r in validation if r["family"] != "diagnostic"],
                  "unbounded_transfer": [{"n": r["n"], "family": r["family"],
                       "selected": index[(r["id"], r["side"], arm)]["selected"]} for r in rows]}
        schedule_lengths[arm] = {}
        for scope, rs in scopes.items():
            schedule_lengths[arm][scope] = [{"n": n, "contexts": len(group),
                                             "mean_selected": statistics.fmean(len(r["selected"]) for r in group),
                                             "median_selected": statistics.median(len(r["selected"]) for r in group)}
                for n in sorted({r["n"] for r in rs}) for group in [[r for r in rs if r["n"] == n]]]
    lowerings = {arm: index[(rows[0]["id"], rows[0]["side"], arm)]["compilation"]["lowered_aggregates"]
                for arm in ("guided", "guided_one_feature", "guided_minimum_interface", "guided_natural_validation", "guided_no_cost")}
    from cipheur.graph_features import FeatureRuleProgram
    from cipheur.model import Graph
    case_spec = next(s for s in mechanisms["train_specifications.json"] if
                     s["id"] == "c3_train_64_0001_anchored_weighted_clique_cover_0")
    case_graph = Graph.from_dict(case_spec["left"])
    active = case_graph.available(case_spec["fixed"], case_spec["excluded"])
    case_scores = {}
    for arm in ("guided", "free", "rule", "enumerated", "guided_minimum_interface",
                "guided_natural_validation", "guided_no_cost"):
        program = FeatureRuleProgram.from_dict(frozen["programs"][arm])
        case_scores[arm] = {}
        for node in ("35170", "28126", "34982"):
            values = program.evaluate_features(case_graph, node, active)
            case_scores[arm][node] = {"values": values, "score": program._rank(values)}
    env = case_scores["guided"]["28126"]["values"]
    assert env["neighbor_edge_count"] == env["degree"]*(env["degree"]-1)//2
    actual_choices = {arm: next(r for r in report["rows"] if r["specification"] == case_spec["id"] and
                                r["side"] == "left") for arm, report in relevance["programs"].items()} if relevance else {}
    case = {"specification": case_spec["id"], "side": "left", "fixed": case_spec["fixed"],
            "excluded": case_spec["excluded"], "source_scope": "original TRAIN evidence bank",
            "scores": case_scores, "saved_actual_choices_and_regret": actual_choices,
            "node_28126_neighborhood_is_clique": True,
            "node_28126_exact_neighborhood_independent_weight": env["max_conflict_weight"],
            "node_28126_g05_estimated_local_loss": env["weight"] - case_scores["guided"]["28126"]["score"],
            "derived_feature_source_sha256": sha256((ROOT / "cipheur/graph_features.py").read_bytes()).hexdigest()}
    return {"scope": "descriptive diagnosis of saved frozen programs and old unbounded transfer; no retuning",
            "programs": {arm: frozen["programs"][arm] for arm in ("guided", *controls)},
            "transfer_g05_comparisons": comparisons, "g01_free_order_and_work_equal_all_216": g01_free_equal,
            "initial_graph_structure": {"development": structure(dev["data.json"]),
                                        "unbounded_transfer": structure(transfer["data.json"])},
            "schedule_lengths": schedule_lengths, "compiled_lowered_aggregates": lowerings,
            "audited_train_case": case,
            "regret_population_scope": "original certificate-selected bank; reached-boundary coverage differs across programs",
            "primary_plot_status": "awaiting cooperative003 primary and transfer archives"}


def style():
    font_manager.findfont("Arial", fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
                         "axes.titlesize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
                         "legend.fontsize": 9, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": GRAY, "axes.labelcolor": INK, "text.color": INK,
                         "xtick.color": INK, "ytick.color": INK,
                         "savefig.facecolor": "white", "figure.facecolor": "white"})


def save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(FIGURES / f"{name}.{suffix}", dpi=300)
    plt.close(fig)


def evidence_figure(summary):
    fig = plt.figure(figsize=(7, 2.65))
    gs = fig.add_gridspec(1, 3, left=.07, right=.99, bottom=.27, top=.86, wspace=.55,
                         width_ratios=[1.05, 1, 1.1])
    a, b, c = [fig.add_subplot(gs[0, i]) for i in range(3)]
    natural = [next(p for p in r["populations"] if p["population"] == "non_diagnostic")
               for r in summary["evidence"]["conditions"]]
    x = np.arange(3)
    rev = [p["relation_counts"].get("reversal", 0) for p in natural]
    pre = [p["relation_counts"].get("preservation", 0) for p in natural]
    a.bar(x, pre, color=BLUE, width=.57, label="Preservation")
    a.bar(x, rev, bottom=pre, color=ORANGE, width=.57, label="Reversal")
    for xx, pp, rr in zip(x, pre, rev):
        a.text(xx, pp+rr+.5, str(pp+rr), ha="center", fontsize=9)
    a.set_xticks(x, ["Ranked\nclique", "Uniform\nclique", "Ranked\nsum"])
    a.set_ylabel("Certified relations")
    a.set_ylim(0, 30)
    a.set_title("(a) Non-probe evidence", loc="left", fontweight="bold")
    a.legend(loc="upper left", frameon=False, ncol=1,
             handlelength=.8, handletextpad=.4, labelspacing=.2)
    b.set_title("(b) Original rollout bank", loc="left", fontweight="bold")
    values = [64, 0, 0]
    b.barh([2, 1, 0], values, height=.53, color=[ORANGE, GRAY, BLUE])
    b.scatter([0, 0], [1, 0], c=[GRAY, BLUE], marker="|", s=120, linewidth=2, zorder=3)
    b.set_yticks([2, 1, 0], ["Probe\nbase", "Other\nbase", "All\nrepaired"])
    for yy, vv in zip([2, 1, 0], values):
        b.text(vv+3, yy, str(vv), va="center", fontsize=9)
    b.set_xlim(0, 81)
    b.set_xticks([0, 32, 64])
    b.set_xlabel("Strict self-loop\nrequirements")
    b.set_ylim(-.65, 2.65)
    c.set_title("(c) Frozen prefix selection", loc="left", fontweight="bold")
    colors = {"guided": BLUE, "free": GRAY, "rule": GRAY, "enumerated": INK}
    formats = {"guided": ("o", "-"), "free": ("s", "--"), "rule": ("^", ":"), "enumerated": ("D", "-.")}
    labels = {"guided": "Guided", "free": "Free", "rule": "Rule only", "enumerated": "Enumeration"}
    for arm in colors:
        rows = [r for r in summary["discovery"]["prefix_curves"] if r["arm"] == arm]
        marker, linestyle = formats[arm]
        c.plot([r["budget"] for r in rows], [100*r["quality"] for r in rows], color=colors[arm],
               marker=marker, ls=linestyle, ms=4, linewidth=1.25, label=labels[arm])
    c.set_xticks([8, 16, 24])
    c.set_xlim(6, 26)
    c.set_ylim(98.9, 99.8)
    c.set_yticks([99.0, 99.3, 99.6])
    c.set_ylabel("Validation quality (%)", labelpad=2)
    c.set_xlabel("Candidate prefix budget")
    c.legend(frameon=False, loc="upper left", ncol=2,
             handlelength=.9, handletextpad=.35, columnspacing=.55, labelspacing=.2)
    save(fig, "evidence_discovery_v03")


def runtime_figure(summary):
    fig, ax = plt.subplots(figsize=(3.33, 2.45))
    fig.subplots_adjust(left=.19, right=.98, bottom=.24, top=.81)
    rows = summary["runtime"]["sizes"]
    x = np.log2([r["n"] for r in rows])
    y = np.asarray([r["speedup"]["estimate"] for r in rows])
    lo = np.asarray([r["speedup"]["lower"] for r in rows])
    hi = np.asarray([r["speedup"]["upper"] for r in rows])
    ax.errorbar(x, y, yerr=np.vstack([y-lo, hi-y]), color=BLUE, marker="o", ms=4,
                lw=1.3, capsize=3, elinewidth=1)
    ax.axhline(1, color=GRAY, lw=.9, ls="--")
    ax.set_xticks(x, [str(r["n"]) for r in rows])
    ax.set_xlabel("Contacts")
    ax.set_ylabel("Interpreter / compiled time")
    ax.set_ylim(.8, max(hi)*1.09)
    ax.set_title("Fixed structural rule: matched traces", loc="left", fontweight="bold", pad=12)
    save(fig, "runtime_v03")


def final_outcome_figure(summary):
    """Negative v03 result, with the same denominator in all three panels."""
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.85))
    fig.subplots_adjust(left=.085, right=.995, bottom=.27, top=.76, wspace=.62)
    arms = ["guided", "free", "rule", "enumerated", "guided_minimum_interface", "guided_no_cost"]
    labels = ["Guided g05", "Free", "Rule only", "Enumeration", "Minimum interface g03", "No cost g18"]
    colors = [PURPLE, GRAY, GRAY, INK, BLUE, ORANGE]
    populations = [("Held-out\n(non-probe)", summary["holdout_cooperative_003"], "non_diagnostic"),
                   ("Dense-long\ntransfer", summary["transfer_cooperative_003"], "all")]
    for index, (arm, label, color) in enumerate(zip(arms, labels, colors)):
        offset = (index - (len(arms)-1)/2)*.105
        for x, (_, result, population) in enumerate(populations):
            m = next(g for g in result["groups"] if g["population"] == population)["methods"][arm]
            for ax, key in zip(axes[:2], ["all_context_quality_zero_normalized", "completion_rate"]):
                ci = m[key]
                y, lo, hi = [100*ci[k] for k in ("estimate", "lower", "upper")]
                ax.errorbar(x+offset, y, yerr=[[y-lo], [hi-y]], color=color,
                            marker=["o", "s", "^", "D", "v", "X"][index], ms=4,
                            linestyle="none", capsize=2, lw=1, label=label if x == 0 else None)
            axes[2].scatter(x+offset, m["median_cpu_seconds_all_contexts"], color=color,
                            marker=["o", "s", "^", "D", "v", "X"][index], s=22)
    titles = ["(a) Reward / reference", "(b) Completion", "(c) CPU cost"]
    for ax, title in zip(axes, titles):
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xticks([0, 1], [p[0] for p in populations]); ax.set_xlim(-.4, 1.4)
        ax.grid(axis="y", alpha=.16)
    axes[0].set_ylabel("Failure-zero mean (%)"); axes[0].set_ylim(0, 105)
    axes[1].set_ylabel("Completed contexts (%)"); axes[1].set_ylim(0, 105)
    axes[2].set_ylabel("Median process CPU (s)"); axes[2].set_yscale("log")
    axes[2].axhline(5, color=ORANGE, lw=.8, ls=":")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(.52, 1.01), columnspacing=1.1, handletextpad=.3)
    save(fig, "outcomes_cooperative_v03")


def final_report(summary):
    path = ROOT / "docs/RESULT_ANALYSIS_V03.md"
    marker = "<!-- FINAL_COOPERATIVE_003 -->"
    old = path.read_text(encoding="utf-8").split(marker)[0].rstrip()
    lines = [marker, "", "## Completed cooperative003 evaluation", "",
             "The two immutable archives contain all 840 held-out contexts and all 216 dense-long transfer contexts. "
             "Constructive programs use the full declared interface (`score_slice=False`) with a cooperative five-process-CPU-second target. "
             "HiGHS uses ten seconds and local search two seconds; these are distinct budgets. Failure has reward zero in the all-assigned mean. "
             "Completed-case quality and completion are separate outcomes. Reference ratios use the archived floating MILP upper, not a formal optimality proof.", "",
             "The stratified 2,000-replicate bootstrap samples source seeds across all three temporal regimes and both graph sides, "
             "C3 source blocks, and diagnostic pairs. Conditional-quality bootstrap retains failed clusters in its assignment frame. "
             "The two populations are never pooled.", ""]
    arms = ["guided", "free", "rule", "enumerated", "guided_one_feature", "guided_minimum_interface",
            "guided_natural_validation", "guided_no_cost", "multi_start_1to2_search"]
    for title, key in [("Held-out (840 contexts; includes diagnostic probes)", "holdout_cooperative_003"),
                       ("Dense-long transfer (216 contexts)", "transfer_cooperative_003")]:
        result = summary[key]; methods = next(g for g in result["groups"] if g["population"] == "all")["methods"]
        lines += [f"### {title}", "", "| Frozen method | Completed / assigned | All-assigned ratio, % (95% CI) | Completed-case ratio, % | Median CPU, s | Median wall, s |",
                  "|---|---:|---:|---:|---:|---:|"]
        for arm in arms:
            m = methods[arm]; q = m["all_context_quality_zero_normalized"]; cq = m["completed_context_quality"]
            cpu = m["median_cpu_seconds_all_contexts"]
            cpu_text = f"{cpu:.6f}" if cpu is not None else "unavailable"
            lines.append(f"| {arm} | {m['completed_contexts']}/{m['assigned_contexts']} | "
                         f"{100*q['estimate']:.6f} [{100*q['lower']:.6f}, {100*q['upper']:.6f}] | "
                         f"{100*cq['estimate']:.6f} | {cpu_text} | {m['median_wall_seconds_all_contexts']:.6f} |")
        d = result["paired_quality_differences_zero_normalized"]["guided_minus_rule"]
        lines += ["", f"Guided−rule paired all-assigned difference: {100*d['estimate']:.6f} percentage points "
                  f"(95% CI [{100*d['lower']:.6f}, {100*d['upper']:.6f}]).", ""]
    lines += ["### Figure choice and limits", "",
              "`outcomes_cooperative_v03.pdf` is a 7 × 2.85 inch, three-panel gallery figure with non-probe held-out quality, "
              "completion, and all-assigned median CPU alongside dense-long transfer. It keeps the negative result visible. "
              "The 95% intervals in quality/completion are source-cluster intervals; median CPU points are descriptive. "
              "The standalone runtime plot remains a fixed-rule implementation comparison and is not evidence of every frozen program's speed.", "",
              "Suggested caption (42 words): **Full-interface v03 evaluation under a cooperative five-CPU-second target. "
              "Failure receives zero reward in panel (a); panel (b) shows completion. Quality and completion intervals resample source clusters. "
              "Panel (c) reports all-assigned median CPU, including unsuccessful runs. Diagnostic probes are omitted here.**", "",
              "The saved g05, g01/g03/g12/g18 diagnoses remain descriptive. Identical ablations cannot establish a mechanism benefit. "
              "Successful TRAIN examples do not attribute aggregate held-out failure to one mechanism. Fresh v04 data are a separate evaluation after a TRAIN-only freeze.", ""]
    path.write_text(old+"\n\n"+"\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    dev, mechanisms, discovery = [archive(n) for n in ("development_scale_001", "mechanisms_001", "discovery_001")]
    frozen_path = ROOT / "experiments" / "discovery" / "v03" / "frozen_joint_001.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    pairs = {p["id"]: p for split in dev["data.json"].values() for p in split}
    assert len(pairs) == 190
    summary = {"version": "v03_source_analysis", "sources": [x["_provenance"] for x in (dev, mechanisms, discovery)] +
                [{"path": frozen_path.relative_to(ROOT).as_posix(), "sha256": sha256(frozen_path.read_bytes()).hexdigest()}],
               "uncertainty": {"seed": SEED, "replications": REPLICATIONS, "level": .95,
                               "unit": "shared temporal or dense_long source seed across regimes in separate strata; C3 source block; both paired graph contexts retained"},
               "development": {"completion": dev["complete.json"], "execution": dev["execution.json"],
                               "pairs": {s: len(p) for s, p in dev["data.json"].items()},
                               "families": dict(Counter(r["family"] for r in dev["results.jsonl"])),
                               "reference_status": dict(Counter(str(r["reference"]["solver_status"]) for r in dev["results.jsonl"])),
                               "reference_gaps": [r["reference"]["mip_gap"] for r in dev["results.jsonl"]],
                               "all_schedules_feasible": all(m["feasible"] for r in dev["results.jsonl"] for m in r["methods"]),
                               "reference_scope": "floating_milp_reference; not exact certificate"},
               "evidence": evidence_summary(mechanisms, pairs), "quotient": quotient_summary(mechanisms),
               "discovery": discovery_summary(discovery, frozen, pairs),
               "runtime": runtime_summary(mechanisms, pairs), "heldout_status": "awaiting primary cooperative003 and transfer cooperative003 archives; unbounded transfer supplementary"}
    if (RUNS / "scalability_001.tar.gz").exists():
        pressure = archive("scalability_001")
        summary["scalability"] = scalability_summary(pressure)
        summary["sources"].append(pressure["_provenance"])
    if (RUNS / "relevance_001.tar.gz").exists():
        relevance = archive("relevance_001")
        summary["relevance"] = relevance_summary(relevance, mechanisms, pairs)
        summary["sources"].append(relevance["_provenance"])
    if (RUNS / "transfer_001.tar.gz").exists():
        transfer = archive("transfer_001")
        summary["transfer_unbounded"] = inference_summary(transfer, frozen, "unbounded")
        summary["sources"].append(transfer["_provenance"])
        summary["program_diagnosis"] = program_diagnosis(transfer, dev, discovery, mechanisms, summary.get("relevance"), frozen)
    for name, expected in [("holdout_cooperative_003", 840), ("transfer_cooperative_003", 216)]:
        if (RUNS / (name+".tar.gz")).exists():
            completed = archive(name)
            assert len(completed["results.jsonl"]) == completed["complete.json"]["completed"] == expected
            summary[name] = inference_summary(completed, frozen, "cooperative_5_process_CPU_seconds")
            summary["sources"].append(completed["_provenance"])
    if "holdout_cooperative_003" in summary and "transfer_cooperative_003" in summary:
        summary["heldout_status"] = "complete840 primary and complete216 transfer; immutable v03 full-interface compilation"
        summary["program_diagnosis"]["primary_plot_status"] = summary["heldout_status"]
        final_report(summary)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    if not args.no_figures:
        style()
        evidence_figure(summary)
        runtime_figure(summary)
        if "holdout_cooperative_003" in summary and "transfer_cooperative_003" in summary:
            final_outcome_figure(summary)
    print("Completed v03 source analysis; source hashes, cluster CIs and all figure values are in experiments/analysis/v03/summary.json")


if __name__ == "__main__":
    main()
