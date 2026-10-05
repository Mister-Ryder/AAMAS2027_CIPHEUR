"""Analyze released, frozen complete-schedule outputs; never load/score a graph.

Preparation is data-free. Formal analysis requires an explicit release flag,
the frozen protocol and bank, and paid result projections. Exact reward ticks
are retained. Static figures are optional; analytical CSV/JSON/MD need only the
standard library. No optimiser, STK, LLM or conditional oracle is imported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

VERSION = "complete_schedule_analysis_v1_pre_results"
TICKS = 1_000_000
CONFIGS = ["g0340", "g0680", "g1200", "g1800", "gW1200_gE0340_s0150",
           "gW0340_gE1200_s0150", "gW0680_gE1200_s0150", "gW1200_gE0680_s0150"]
ALIASES = dict(zip(["A", "M", "J", "stress", "W", "E", "MW", "ME"], CONFIGS))
LABELS = dict(zip(CONFIGS, ["340/340", "680/680", "1200/1200", "1800/1800",
                           "1200/340", "340/1200", "680/1200", "1200/680"]))
KNOWN = {CONFIGS[i] for i in (0, 2, 4, 5)}
UNIFORM = set(CONFIGS[:4])
UNSEEN = {CONFIGS[i] for i in (1, 3, 6, 7)}
BASELINES = ["degree", "weight", "grasp", "local2swap", "cp_sat", "chils_ils", "chils"]
COLOURS = {"witness_joint": "#0072B2", "relations_joint": "#009E73",
           "relations_rule_only": "#D55E00", "nonllm_grammar": "#777777",
           "old_frozen": "#8C6BB1", "degree": "#30343B", "weight": "#6A7F8A",
           "grasp": "#CC79A7", "local2swap": "#56B4E9", "cp_sat": "#666666",
           "chils": "#B8860B", "chils_ils": "#A39B69"}

REGISTRATION = {
    "version": VERSION,
    "registered_before_formal_results": True,
    "data_access": "Paid result JSON only; no input graph, scoring, STK, optimizer or model call.",
    "primary_metric": "Final complete feasible schedule value_ticks / 1000000 seconds; exact rational arithmetic until display.",
    "main_budget_interpretation": "Declared 2/10 CPU-second budget; retain complete final output and report actual total CPU and overshoot jointly. Not a strict hard-deadline winner claim.",
    "paired_key": ["split", "source", "canonical_config", "seed", "declared_cpu_seconds", "input_graph_sha256"],
    "comparison_baselines": ["degree", "chils", "chils_ils", "cp_sat", "weight", "grasp", "local2swap"],
    "statistical_unit": "Physical source group r008 or r009. Configurations, AU/AP geometries and seeds are repeated measurements, not independent n.",
    "aggregation": "Equal seed mean within config/source; equal config mean within source; equal AU/AP source mean within physical group; equal r008/r009 group mean. Expose each group. No significance test or CI with n=2.",
    "llm_batches": "Every frozen selected programme in both generation batches is reported individually. No analyst selection, best-batch pooling or TEST-based programme removal.",
    "costs": ["cpu_seconds", "wall_seconds", "native_child_cpu_seconds", "cpu_seconds_including_record_encoding", "feature_seconds", "scoring_seconds", "feature_work", "query_work", "head_score_evaluations", "head_commits"],
    "failure_policy": "Missing/nonfeasible output is NA, never zero. Valid common-kernel fallback retains quality plus explicit native/programme failure, guard and zero-commit status.",
    "anytime_policy": "Only actual committed best-so-far event steps. No synthetic interpolation. Native CHILS internal trace missing is observation-limited/NA, not no internal progress. Native seed/end markers do not support hard-deadline superiority.",
    "saturation_policy": "All-zero or saturated effects get exact tables and an unavailable/no-visible-signal figure receipt; no fabricated curve or exaggerated effect.",
    "families": {"known": sorted(KNOWN), "uniform": CONFIGS[:4], "heterogeneous": CONFIGS[4:], "unseen": sorted(UNSEEN), "stress": ["g1800"]},
    "figures": {
        "configuration_response": "Paired delta seconds vs Degree and CHILS population4 at 2/10s; equal physical-group heatmaps with symmetric shared scale and exact-value table.",
        "quality_cost": "Actual total CPU vs paired complete-quality delta, same programme colour and batch marker; feature CPU shown separately. No causal/Pareto claim.",
        "anytime": {"source": "CP-AU-r008", "seed": 2, "configs": [ALIASES["W"], ALIASES["MW"]], "budgets": [2, 10], "selection": "Fixed before results, never choose the most favourable TEST example."},
        "chain": "Selected-programme strict TRAIN fit, TRAIN complete-quality gain and TEST complete-quality gain at 2s, matching known configurations. Descriptive chain only, not proof of causation. Missing/saturated input is explicitly NA/table.",
    },
    "style": {"type": "static scientific", "size_inches": [7.1, 4.3], "font_points": 8, "output": ["PDF", "PNG300dpi", "individual_panel_PDF"], "batch0": "filled/solid", "batch1": "open/dashed", "group_range": "observed physical-group range, not confidence interval", "palette": COLOURS},
    "baseline_sources": {
        "chils": {"paper": "Concurrent Iterated Local Search for the Maximum Weight Independent Set Problem, SEA 2025", "url": "https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SEA.2025.22", "implementation": "https://github.com/KarlsruheMIS/CHILS", "git": "515952724cd3dcc6c4365a340ecf0f1da782119a", "threads": 1, "populations": [1, 4]},
        "cp_sat": {"paper": "The CP-SAT-LP Solver (Invited Talk), CP 2023", "url": "https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2023.3", "ortools": "9.15.6755", "workers": 1},
        "classical_heads": "Degree/weight/GRASP in the same project kernel; local2swap is project LS. Do not claim full published-method reproduction.",
    },
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def csv_dump(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r if not k.startswith("_")))
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                             for k, v in row.items() if k in keys})


def canonical(config):
    if config in ALIASES: return ALIASES[config]
    match = re.fullmatch(r"gW(\d{4})_gE\1_s0150", str(config))
    if match: return "g" + match[1]
    if config not in CONFIGS: raise ValueError("Unregistered configuration: " + str(config))
    return config


def exact_fields(name, value):
    return {name + "_exact": str(value) if value is not None else None,
            name: float(value) if value is not None else None}


def avg(values):
    return sum(values, Fraction(0)) / len(values) if values else None


def finite_number(value):
    return value is not None and not isinstance(value, bool) and math.isfinite(float(value))


def optional_number(value):
    return float(value) if finite_number(value) else None


def group(source):
    match = re.fullmatch(r"CP-(AU|AP)-(r\d{3})", str(source))
    if not match: raise ValueError("Unknown physical source: " + str(source))
    return match[2], match[1]


def batch(item):
    if item.get("batch") is not None: return item["batch"]
    match = re.search(r"\.b(\d+)\.", item.get("id", ""))
    return int(match[1]) if match else None


def normalise(result, file_path, bank, protocol, protocol_sha, bank_sha):
    split = {"validation": "val", "val": "val", "train": "train", "test": "test"}.get(str(result.get("split", "")).lower())
    if split is None: raise ValueError("Result has unknown split: " + str(file_path))
    source = result["source"]; physical_group, geometry = group(source)
    cfg = canonical(result.get("graph_config_id") or result["config"])
    method = result["method"]; pid = result.get("program_id")
    item = bank.get(pid, {})
    if method == "program" and pid not in bank: raise ValueError("Programme missing from frozen bank: " + str(pid))
    if split == "test":
        if source not in protocol["test_sources"]: raise ValueError("TEST source not frozen")
        if result.get("protocol_sha256") != protocol_sha: raise ValueError("TEST result protocol hash differs from supplied frozen protocol")
        if method == "program" and (pid not in protocol["final_program_ids"] or result.get("program_bank_sha256") != bank_sha):
            raise ValueError("TEST programme not in unchanged frozen final bank")
    declared = result.get("declared_cpu_seconds", result.get("budget_seconds"))
    if not finite_number(declared) or float(declared) <= 0: raise ValueError("Missing declared CPU budget")
    seed = result["seed"]
    if split == "test" and (float(declared) not in protocol.get("budgets_seconds", protocol.get("execution_cpu_seconds", [])) or seed not in protocol.get("seeds", protocol.get("formal_seeds", []))):
        raise ValueError("Unregistered TEST budget or seed")
    ticks = result.get("value_ticks"); valid = result.get("feasible") is True and isinstance(ticks, int) and not isinstance(ticks, bool)
    if result.get("feasible") is True and not valid: raise ValueError("Feasible output lacks exact integer reward")
    if valid and result.get("value_exact") is not None and Fraction(str(result["value_exact"])) != Fraction(ticks, TICKS):
        raise ValueError("value_exact differs from exact ticks")
    cpu = optional_number(result.get("cpu_seconds")); wall = optional_number(result.get("wall_seconds"))
    phases = result.get("phases") or {}; phase_statuses = result.get("phase_statuses") or {}
    construction = result.get("construction_summary") or phases.get("construction") or {}
    native = phases.get("native_published") or phase_statuses.get("native_published") or {}
    repairs = result.get("repairs"); repair_summary = result.get("repair_summary")
    if repair_summary is None and isinstance(repairs, list):
        gains = [int(r["raw_gain_ticks"]) for r in repairs if r.get("raw_gain_ticks") is not None]
        repair_summary = {"count": len(repairs), "accepted_count": sum(bool(r.get("committed")) for r in repairs),
                          "negative_raw_gain_count": sum(x < 0 for x in gains), "zero_raw_gain_count": sum(x == 0 for x in gains),
                          "raw_gain_ticks_sum": sum(gains), "raw_gain_ticks_min": min(gains) if gains else None,
                          "raw_gain_ticks_max": max(gains) if gains else None}
    stats = result.get("stats") or {}; meter = result.get("meter") or {}
    if stats.get("online_llm_calls", 0) != 0 or stats.get("conditional_oracle_calls", 0) != 0:
        raise ValueError("Frozen deployment includes online model/oracle call")
    error_count = result.get("programme_error_count")
    if error_count is None and isinstance(repairs, list):
        error_count = sum(r.get("status") == "programme_error" for r in repairs) + int(construction.get("status") == "programme_error")
    arm = result.get("program_arm") or item.get("arm") or method
    row = {"split": split, "source": source, "source_group": physical_group, "geometry": geometry,
           "config": cfg, "config_label_W_E_seconds": LABELS[cfg], "seed": seed,
           "declared_cpu_seconds": float(declared), "method": method, "variant": pid if method == "program" else method,
           "program_id": pid, "arm": arm, "batch": batch(item), "round": item.get("round"),
           "complete_feasible": valid, "value_ticks": ticks if valid else None,
           "value_seconds_exact": str(Fraction(ticks, TICKS)) if valid else None,
           "value_seconds": float(Fraction(ticks, TICKS)) if valid else None,
           "seed_value_ticks": result.get("seed_value_ticks"), "cpu_seconds": cpu, "wall_seconds": wall,
           "overshoot_seconds": max(0., cpu - float(declared)) if cpu is not None else None,
           "over_declared_budget": cpu > float(declared) if cpu is not None else None,
           "cpu_seconds_including_record_encoding": optional_number(result.get("cpu_seconds_including_record_encoding")),
           "native_child_cpu_seconds": optional_number(result.get("native_child_cpu_seconds")),
           "native_cpu_measurement_available": result.get("native_cpu_measurement_available"),
           "native_status": native.get("status") if method.startswith("chils") else None,
           "native_internal_trace_available": False if method.startswith("chils") else None,
           "execution_status": result.get("execution_status", "unrecorded"),
           "head_ever_committed": result.get("head_ever_committed"), "head_commits": stats.get("head_commits"),
           "head_score_evaluations": stats.get("head_score_evaluations"), "online_llm_calls": stats.get("online_llm_calls"),
           "conditional_oracle_calls": stats.get("conditional_oracle_calls"), "programme_error_count": error_count,
           "construction_status": construction.get("status"), "construction_accepted_by_guard": construction.get("accepted_by_guard"),
           "construction_raw_delta_ticks": construction.get("raw_delta_from_seed_ticks"),
           "construction_raw_value_ticks": construction.get("raw_full_value_ticks"), "construction_completion_fallback": construction.get("completion_fallback"),
           "repair_summary": repair_summary, "phase_statuses": phase_statuses,
           "feature_seconds": optional_number(meter.get("feature_seconds")), "scoring_seconds": optional_number(meter.get("scoring_seconds")),
           "feature_work": optional_number(meter.get("feature_work")), "query_work": optional_number(meter.get("query_work")),
           "input_graph_sha256": result.get("input_graph_sha256"), "program_bank_sha256": result.get("program_bank_sha256"),
           "protocol_sha256": result.get("protocol_sha256"), "execution_module_sha256": result.get("execution_module_sha256"),
           "result_sha256": result.get("result_sha256"), "result_relative_path": result.get("result_relative_path"),
           "projection_file": str(file_path), "job_id": result.get("job_id"),
           "_events": result.get("best_so_far", []), "_item": item}
    return row


def key(row):
    return (row["split"], row["source"], row["config"], row["seed"], row["declared_cpu_seconds"], row["variant"])


def load_results(paths, bank, protocol, protocol_sha, bank_sha):
    records, failures, provenance, seen, excluded = [], [], [], {}, []
    for path in paths:
        path = Path(path).resolve(); obj = read(path)
        provenance.append({"path": str(path), "sha256": sha(path)})
        values = obj.get("records", [obj]) if isinstance(obj, dict) else obj
        failures.extend(obj.get("failed_jobs", []) if isinstance(obj, dict) else [])
        for raw in values:
            # Retain explicit exclusions, but never TEST-select programme quality.
            if raw.get("method") == "program" and raw.get("program_id") not in protocol["final_program_ids"]:
                if str(raw.get("split", "")).lower() == "test": raise ValueError("Unselected programme in TEST results")
                excluded.append({"program_id": raw.get("program_id"), "split": raw.get("split"), "file": str(path), "reason": "not in frozen final_program_ids"}); continue
            row = normalise(raw, path, bank, protocol, protocol_sha, bank_sha); k = key(row)
            if k in seen:
                old = seen[k]
                if old.get("result_sha256") and old["result_sha256"] == row.get("result_sha256"): continue
                # Raw representative of already projected paid job is allowed only if exact output/identity match.
                comparable = ["value_ticks", "complete_feasible", "cpu_seconds", "input_graph_sha256", "execution_module_sha256"]
                if all(old.get(c) == row.get(c) for c in comparable) and old.get("job_id") == row.get("job_id"):
                    if row["_events"]: old["_events"] = row["_events"]
                    continue
                raise ValueError("Conflicting repeated paid result for " + repr(k))
            records.append(row); seen[k] = row
    return records, failures, provenance, excluded


def pair_records(records):
    lookup = {key(r): r for r in records}; pairs, missing = [], []
    for row in records:
        for baseline in BASELINES:
            if row["variant"] == baseline: continue
            pkey = key(row)[:-1] + (baseline,); ref = lookup.get(pkey)
            if ref is None or not row["complete_feasible"] or not ref["complete_feasible"]:
                missing.append({"variant": row["variant"], "baseline": baseline, "split": row["split"], "source": row["source"],
                                "config": row["config"], "seed": row["seed"], "budget": row["declared_cpu_seconds"], "reason": "missing/nonfeasible paired output"}); continue
            if not row["input_graph_sha256"] or row["input_graph_sha256"] != ref["input_graph_sha256"]:
                raise ValueError("Paired comparison input graph hash differs")
            delta = row["value_ticks"] - ref["value_ticks"]
            pairs.append({k: row[k] for k in ("split", "source", "source_group", "geometry", "config", "seed", "declared_cpu_seconds", "variant", "arm", "batch", "program_id")}
                         | {"baseline": baseline, "delta_ticks": delta, "delta_seconds_exact": str(Fraction(delta, TICKS)),
                            "delta_seconds": delta / TICKS, "value_ticks": row["value_ticks"], "baseline_value_ticks": ref["value_ticks"],
                            "cpu_seconds": row["cpu_seconds"], "baseline_cpu_seconds": ref["cpu_seconds"],
                            "native_baseline_status": ref["native_status"], "input_graph_sha256": row["input_graph_sha256"]})
    return pairs, missing


def family_configs(family):
    return {"all": set(CONFIGS), "known": KNOWN, "uniform": UNIFORM, "heterogeneous": set(CONFIGS) - UNIFORM,
            "unseen": UNSEEN, "stress": {"g1800"}}.get(family, {family.split(":", 1)[1]} if family.startswith("config:") else set())


def hierarchical_mean(rows, getter):
    """Exact equal weights at each prespecified repeated-measurement layer."""
    cells = defaultdict(list)
    for row in rows:
        value = getter(row)
        if value is not None: cells[(row["source_group"], row["source"], row["config"])].append(value)
    source_values = defaultdict(list)
    for (sg, source, cfg), vals in cells.items(): source_values[(sg, source)].append(avg(vals))
    group_values = defaultdict(list)
    for (sg, source), vals in source_values.items(): group_values[sg].append(avg(vals))
    groups = {sg: avg(vals) for sg, vals in group_values.items()}
    return avg(list(groups.values())), groups, len(cells)


def summarise_pairs(pairs):
    buckets = defaultdict(list)
    families = ["all", "known", "uniform", "heterogeneous", "unseen", "stress"] + ["config:" + c for c in CONFIGS]
    for row in pairs:
        for family in families:
            if row["config"] in family_configs(family): buckets[(row["split"], row["declared_cpu_seconds"], row["variant"], row["baseline"], family)].append(row)
    summaries = []
    for (split, budget, variant, baseline, family), rows in sorted(buckets.items()):
        value, groups, cells = hierarchical_mean(rows, lambda r: Fraction(r["delta_ticks"], TICKS))
        summary = {"split": split, "budget": budget, "variant": variant, "arm": rows[0]["arm"], "batch": rows[0]["batch"],
                   "baseline": baseline, "family": family, "paired_runs": len(rows), "source_config_cells": cells,
                   "independent_physical_groups": len(groups), "groups_exact": {g: str(v) for g, v in sorted(groups.items())}}
        summary.update(exact_fields("mean_delta_seconds", value))
        summary.update(exact_fields("group_min_seconds", min(groups.values()) if groups else None))
        summary.update(exact_fields("group_max_seconds", max(groups.values()) if groups else None))
        # Descriptive repeated-observation counts; never independent sample n.
        summary.update(positive_paired_runs=sum(r["delta_ticks"] > 0 for r in rows), zero_paired_runs=sum(r["delta_ticks"] == 0 for r in rows), negative_paired_runs=sum(r["delta_ticks"] < 0 for r in rows))
        summaries.append(summary)
    return summaries


def summarise_quality(records):
    buckets = defaultdict(list)
    for r in records: buckets[(r["split"], r["declared_cpu_seconds"], r["variant"])].append(r)
    output = []
    metrics = ["cpu_seconds", "wall_seconds", "overshoot_seconds", "feature_seconds", "scoring_seconds", "feature_work", "query_work", "head_commits", "head_score_evaluations", "programme_error_count"]
    for (split, budget, variant), rows in sorted(buckets.items()):
        value, groups, cells = hierarchical_mean(rows, lambda r: Fraction(r["value_ticks"], TICKS) if r["complete_feasible"] else None)
        item = {"split": split, "budget": budget, "variant": variant, "arm": rows[0]["arm"], "batch": rows[0]["batch"],
                "observed_runs": len(rows), "complete_feasible_runs": sum(r["complete_feasible"] for r in rows),
                "independent_physical_groups": len(groups), "groups_exact": {g: str(v) for g, v in sorted(groups.items())},
                "native_status_counts": dict(Counter(r["native_status"] for r in rows if r["native_status"] is not None)),
                "construction_status_counts": dict(Counter(r["construction_status"] for r in rows if r["construction_status"] is not None))}
        item.update(exact_fields("mean_value_seconds", value))
        for metric in metrics:
            mean, _, _ = hierarchical_mean(rows, lambda r: Fraction(str(r[metric])) if r[metric] is not None else None)
            item["mean_" + metric] = float(mean) if mean is not None else None
            item[metric + "_observed_runs"] = sum(r[metric] is not None for r in rows)
        for name in ("over_declared_budget", "head_ever_committed", "construction_accepted_by_guard"):
            mean, _, _ = hierarchical_mean(rows, lambda r: Fraction(int(r[name])) if r[name] is not None else None)
            item[name + "_rate"] = float(mean) if mean is not None else None
            item[name + "_observed_runs"] = sum(r[name] is not None for r in rows)
        item["negative_raw_construction_runs"] = sum(r["construction_raw_delta_ticks"] is not None and r["construction_raw_delta_ticks"] < 0 for r in rows)
        item["repair_negative_raw_gain_count"] = sum((r["repair_summary"] or {}).get("negative_raw_gain_count", 0) for r in rows)
        item["repair_accepted_count"] = sum((r["repair_summary"] or {}).get("accepted_count", 0) for r in rows)
        output.append(item)
    return output


def observable_at_budget(row):
    # A CHILS seed-only trace is not a native hard-deadline quality observation.
    if row["method"].startswith("chils"):
        native = [e for e in row["_events"] if e.get("stage") == "native_improvement" and e.get("cpu_seconds", math.inf) <= row["declared_cpu_seconds"]]
        return max((e["value_ticks"] for e in native), default=None), "native internal trace unavailable; final-only observation"
    events = [e for e in row["_events"] if e.get("cpu_seconds", math.inf) <= row["declared_cpu_seconds"]]
    return max((e["value_ticks"] for e in events), default=None), "observable committed incumbent only"


def trace_rows(records):
    output = []
    for row in records:
        last_t = -math.inf; last_v = -math.inf
        for n, event in enumerate(row["_events"]):
            t = event.get("cpu_seconds"); value = event.get("value_ticks")
            if not finite_number(t) or not isinstance(value, int): raise ValueError("Malformed paid event trace")
            if float(t) < last_t or value < last_v: raise ValueError("Nonmonotonic true incumbent trace")
            last_t = float(t); last_v = value
            output.append({k: row[k] for k in ("split", "source", "config", "seed", "declared_cpu_seconds", "variant", "method")}
                          | {"event_index": n, "stage": event.get("stage"), "cpu_seconds": t, "wall_seconds": event.get("wall_seconds"),
                             "value_ticks": value, "value_seconds_exact": str(Fraction(value, TICKS)), "native_internal_trace_available": row["native_internal_trace_available"]})
        observed, caveat = observable_at_budget(row)
        row["observed_value_at_budget_ticks"] = observed
        row["observed_value_at_budget_caveat"] = caveat
    return output


def check_coverage(records, protocol):
    test = [r for r in records if r["split"] == "test"]
    methods = list(protocol.get("formal_methods", protocol.get("methods", BASELINES)))
    methods = [m for m in methods if m != "program"]
    variants = methods + list(protocol["final_program_ids"])
    budgets = protocol.get("budgets_seconds", protocol.get("execution_cpu_seconds", []))
    seeds = protocol.get("seeds", protocol.get("formal_seeds", []))
    expected = set(itertools.product(protocol["test_sources"], CONFIGS, seeds, map(float, budgets), variants))
    observed = {(r["source"], r["config"], r["seed"], r["declared_cpu_seconds"], r["variant"]) for r in test}
    missing = expected - observed; extra = observed - expected
    return {"expected_test_runs": len(expected), "observed_test_runs": len(observed),
            "missing_test_runs": [list(v) for v in sorted(missing)], "unregistered_test_runs": [list(v) for v in sorted(extra)],
            "expected_physical_groups": ["r008", "r009"], "expected_seed_ids": list(seeds)}


def load_fit(paths, selected, bank, provenance):
    fits = {}
    for root in paths:
        for pid in selected:
            path = Path(root) / (pid + ".json")
            if not path.is_file(): continue
            if pid in fits: raise ValueError("Repeated selected TRAIN fit")
            value = read(path)
            if value.get("program_id") != pid or str(value.get("split", "")).lower() != "train" or value.get("VAL_read") or value.get("TEST_read"):
                raise ValueError("Fit is not TRAIN-only selected programme")
            if value.get("total_requirements") != 743 or value.get("candidate_program") != bank[pid]["program"]:
                raise ValueError("Fit contract or programme content differs")
            value["strict_fit_exact"] = str(Fraction(value["passed_requirements"], value["total_requirements"]))
            fits[pid] = value; provenance.append({"path": str(path.resolve()), "sha256": sha(path), "kind": "selected_TRAIN_fit"})
    return fits


def chain_rows(summaries, fits, selected):
    lookup = {(s["split"], s["budget"], s["variant"], s["baseline"], s["family"]): s for s in summaries}
    rows = []
    for pid in selected:
        train = lookup.get(("train", 2., pid, "degree", "known")); test = lookup.get(("test", 2., pid, "degree", "known")); fit = fits.get(pid)
        rows.append({"program_id": pid, "strict_fit_exact": fit.get("strict_fit_exact") if fit else None,
                     "strict_fit_fraction": float(Fraction(fit["strict_fit_exact"])) if fit else None,
                     "fit_passed": fit.get("passed_requirements") if fit else None, "fit_total": fit.get("total_requirements") if fit else None,
                     "train_delta_seconds": train["mean_delta_seconds"] if train else None, "train_delta_seconds_exact": train["mean_delta_seconds_exact"] if train else None,
                     "test_delta_seconds": test["mean_delta_seconds"] if test else None, "test_delta_seconds_exact": test["mean_delta_seconds_exact"] if test else None,
                     "scope": "2s; equal known A/W/E/J; descriptive fit-to-quality chain; not causal proof"})
    return rows


def style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
                         "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5, "figure.dpi": 150,
                         "savefig.dpi": 300, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.edgecolor": "#50545B",
                         "axes.linewidth": .6, "text.color": "#30343B", "axes.spines.top": False, "axes.spines.right": False,
                         "grid.color": "#D9DCE1", "grid.linewidth": .5, "axes.axisbelow": True})
    return plt


def variant_label(variant, bank):
    if variant not in bank: return {"chils": "CHILS p4", "chils_ils": "CHILS p1", "local2swap": "LS2", "cp_sat": "CP-SAT"}.get(variant, variant.title())
    item = bank[variant]; name = {"witness_joint": "Witness", "relations_joint": "Relations", "relations_rule_only": "Rule-only", "nonllm_grammar": "Grammar", "old_frozen": "Old"}.get(item["arm"], item["arm"])
    b = batch(item); return name + (" b" + str(b) if b is not None else "")


def colour(variant, bank):
    arm = bank.get(variant, {}).get("arm", variant)
    return COLOURS.get(arm, COLOURS["old_frozen"] if "old_frozen" in arm else "#777777")


def save_figure(fig, axes, output, name, plt):
    paths = []
    fig.canvas.draw()
    for ext in ("pdf", "png"):
        path = output / (name + "." + ext); fig.savefig(path, bbox_inches="tight"); paths.append(str(path))
    # Genuine cropped panel exports allow LaTeX to control compact layout.
    for i, ax in enumerate(axes):
        bbox = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted()).expanded(1.04, 1.08)
        path = output / (name + "_panel" + str(i + 1) + ".pdf")
        fig.savefig(path, bbox_inches=bbox); paths.append(str(path))
    plt.close(fig); return paths


def plots(output, records, pairs, summaries, quality, chain, bank, protocol):
    plt = style(); output.mkdir(parents=True, exist_ok=True); receipts = []
    selected = list(protocol["final_program_ids"])
    lookup = {(s["split"], s["budget"], s["variant"], s["baseline"], s["family"]): s for s in summaries}
    # 1. Configuration response. Structural controls retained in rows as well.
    values = [s["mean_delta_seconds"] for s in summaries if s["split"] == "test" and s["family"].startswith("config:") and s["variant"] in selected and s["baseline"] in ("degree", "chils")]
    if not values or not any(v != 0 for v in values):
        receipts.append({"figure": "configuration_response", "status": "table_only", "reason": "no nonzero paired config effect or missing observations", "evidence": "paired_summary.csv"})
    else:
        import numpy as np
        fig, axs = plt.subplots(2, 2, figsize=(7.1, 4.3), constrained_layout=True)
        limit = max(abs(v) for v in values); image = None
        for ax, (baseline, budget) in zip(axs.flat, itertools.product(("degree", "chils"), (2., 10.))):
            matrix = np.array([[lookup.get(("test", budget, pid, baseline, "config:" + cfg), {}).get("mean_delta_seconds", np.nan) for cfg in CONFIGS] for pid in selected])
            image = ax.imshow(matrix, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
            ax.set_xticks(range(8), [LABELS[c] for c in CONFIGS], rotation=45, ha="right")
            ax.set_yticks(range(len(selected)), [variant_label(p, bank) for p in selected])
            ax.set_title("vs " + variant_label(baseline, bank) + ", " + str(int(budget)) + "s")
            for (i, j), v in np.ndenumerate(matrix):
                if math.isfinite(float(v)): ax.text(j, i, format(float(v), ".2g"), ha="center", va="center", fontsize=5.7, color="white" if abs(v) > .65 * limit else "#30343B")
        fig.colorbar(image, ax=list(axs.flat), shrink=.72, label="Paired complete-quality difference (s)")
        receipts.append({"figure": "configuration_response", "status": "rendered", "paths": save_figure(fig, list(axs.flat), output, "fig01_configuration_response", plt), "caption": "Equal r008/r009 mean paired complete schedule differences at declared CPU budgets. W/E turnaround in seconds; saturated cells and native failures remain in exact tables. Actual CPU/overshoot is reported separately."})
    # 2. Quality and actual cost, with known/unseen cells retained.
    validpairs = [r for r in pairs if r["split"] == "test" and r["baseline"] == "degree" and r["variant"] in selected and r["cpu_seconds"] is not None]
    if validpairs:
        fig, axs = plt.subplots(2, 2, figsize=(7.1, 4.3), constrained_layout=True)
        for ax, budget in zip(axs[0], (2., 10.)):
            for pid in selected:
                points = [p for p in validpairs if p["variant"] == pid and p["declared_cpu_seconds"] == budget]
                for sg, marker in (("r008", "o"), ("r009", "s")):
                    sub = [p for p in points if p["source_group"] == sg]; m, _, _ = hierarchical_mean(sub, lambda r: Fraction(r["delta_ticks"], TICKS)); cpu, _, _ = hierarchical_mean(sub, lambda r: Fraction(str(r["cpu_seconds"])))
                    if m is not None and cpu is not None: ax.scatter(float(cpu), float(m), s=32, marker=marker, edgecolors=colour(pid, bank), facecolors="none" if batch(bank[pid]) == 1 else colour(pid, bank), linewidths=.8, label=variant_label(pid, bank) if sg == "r008" else None)
            ax.axhline(0, color="#747B85", lw=.6); ax.axvline(budget, color="#747B85", lw=.6, ls=":"); ax.grid(True)
            ax.set(title=str(int(budget)) + "s declared", xlabel="Actual total CPU (s)", ylabel="Paired gain vs Degree (s)")
        for ax, budget in zip(axs[1], (2., 10.)):
            for i, pid in enumerate(selected):
                q = next((q for q in quality if q["split"] == "test" and q["budget"] == budget and q["variant"] == pid), None)
                if q and q["mean_feature_seconds"] is not None: ax.bar(i, q["mean_feature_seconds"], color=colour(pid, bank), width=.7, hatch="//" if batch(bank[pid]) == 1 else None)
            ax.set_xticks(range(len(selected)), [variant_label(p, bank) for p in selected], rotation=35, ha="right"); ax.set(ylabel="Feature CPU (s)", title=str(int(budget)) + "s cost"); ax.grid(axis="y")
        axs[0, 0].legend(ncol=2, loc="best")
        receipts.append({"figure": "quality_cost", "status": "rendered", "paths": save_figure(fig, list(axs.flat), output, "fig02_quality_cost", plt), "caption": "Points are r008/r009 physical-group means (circle/square), not independent configurations. Filled/open marks show LLM batch0/1. Quality is complete final output; vertical line is declared budget and actual total CPU exposes overshoot. Feature cost includes observed computation, missing cost is NA."})
    else: receipts.append({"figure": "quality_cost", "status": "unavailable", "reason": "no valid paired quality/CPU records"})
    # 3. Registered representative, actual steps; native CHILS only markers.
    spec = REGISTRATION["figures"]["anytime"]
    examples = [r for r in records if r["split"] == "test" and r["source"] == spec["source"] and r["seed"] == spec["seed"] and r["config"] in spec["configs"] and r["declared_cpu_seconds"] in spec["budgets"] and (r["variant"] in selected or r["variant"] in ("degree", "chils", "chils_ils"))]
    meaningful = any(len({e.get("value_ticks") for e in r["_events"]}) > 1 and not r["method"].startswith("chils") for r in examples)
    if meaningful:
        fig, axs = plt.subplots(2, 2, figsize=(7.1, 4.3), constrained_layout=True)
        for ax, (cfg, budget) in zip(axs.flat, itertools.product(spec["configs"], spec["budgets"])):
            candidates = [r for r in examples if r["config"] == cfg and r["declared_cpu_seconds"] == budget]
            for row in candidates:
                events = row["_events"]
                if not events: continue
                seed_ticks = row["seed_value_ticks"]
                if seed_ticks is None: continue
                xs = [e["cpu_seconds"] for e in events]; ys = [(e["value_ticks"] - seed_ticks) / TICKS for e in events]
                pid = row["variant"]; kwargs = {"color": colour(pid, bank), "label": variant_label(pid, bank)}
                if row["method"].startswith("chils"):
                    ax.scatter([xs[0], xs[-1]], [ys[0], ys[-1]], s=17, marker="x", **kwargs)
                else: ax.step(xs, ys, where="post", lw=1., ls="--" if batch(bank.get(pid, {})) == 1 else "-", **kwargs)
            ax.axvline(budget, color="#747B85", ls=":", lw=.6); ax.grid(True)
            ax.set(title=LABELS[cfg] + ", " + str(budget) + "s", xlabel="Actual total CPU (s)", ylabel="Gain over common seed (s)")
        axs[0, 0].legend(ncol=2, loc="best")
        receipts.append({"figure": "anytime", "status": "rendered", "paths": save_figure(fig, list(axs.flat), output, "fig03_real_anytime", plt), "caption": "Preselected AU-r008, seed2, W and unseen mixed turnaround. Step functions use genuine committed incumbents only; CHILS marks only observed start/end with unavailable internal trace. Delayed final validation is retained. This figure does not establish native hard-deadline superiority."})
    else: receipts.append({"figure": "anytime", "status": "table_only", "reason": "registered representative missing/flat or native-only endpoint observations", "evidence": "real_incumbent_events.csv"})
    # 4. Descriptive training evidence -> actual complete-schedule gains.
    completechain = [c for c in chain if all(c.get(k) is not None for k in ("strict_fit_fraction", "train_delta_seconds", "test_delta_seconds"))]
    if completechain and (len({c["train_delta_seconds"] for c in completechain}) > 1 or len({c["test_delta_seconds"] for c in completechain}) > 1):
        fig, axs = plt.subplots(1, 2, figsize=(7.1, 2.7), constrained_layout=True)
        for c in completechain:
            pid = c["program_id"]; kw = {"s": 35, "edgecolors": colour(pid, bank), "facecolors": "none" if batch(bank[pid]) == 1 else colour(pid, bank), "label": variant_label(pid, bank)}
            axs[0].scatter(c["strict_fit_fraction"], c["train_delta_seconds"], **kw)
            axs[1].scatter(c["train_delta_seconds"], c["test_delta_seconds"], **kw)
        axs[0].set(xlabel="Strict TRAIN fit (743 requirements)", ylabel="Complete TRAIN gain vs Degree (s)")
        axs[1].set(xlabel="Complete TRAIN gain vs Degree (s)", ylabel="Complete TEST gain vs Degree (s)")
        for ax in axs: ax.grid(True); ax.axhline(0, color="#747B85", lw=.6)
        axs[1].legend(ncol=2, loc="best")
        receipts.append({"figure": "chain", "status": "rendered", "paths": save_figure(fig, list(axs), output, "fig04_fit_quality_chain", plt), "caption": "Frozen selected programmes, both LLM batches, 2s complete schedules on matching known A/W/E/J configurations. Strict fit, TRAIN quality and TEST quality are different measurements; no causal or monotonic relationship is assumed. Saturated fit/zero quality effects remain in the table."})
    else: receipts.append({"figure": "chain", "status": "table_only", "reason": "missing selected fit/TRAIN/test chain or flat complete-quality gains", "evidence": "train_fit_quality_chain.csv"})
    return receipts


def fmt(value):
    if value is None: return "NA"
    if isinstance(value, bool): return "是" if value else "否"
    if abs(float(value)) < .001 and value != 0: return format(float(value), ".3g")
    return format(float(value), ".6g")


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines += ["| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in row) + " |" for row in rows]
    return "\n".join(lines)


def write_report(output, records, summaries, quality, chain, fits, failures, coverage, receipts, evidence, protocol, bank, partial):
    testq = [q for q in quality if q["split"] == "test"]
    lookup = {(s["budget"], s["variant"], s["baseline"], s["family"]): s for s in summaries if s["split"] == "test"}
    lines = ["# 完整 LLM 算法性能对比", "", "本报告是完整结果与限制的证据记录；不等同于论文正文，也不作录用保证。",
             "", "## 分析口径与版本", "", "主指标为最终完整可行调度的接触时长（秒），原始整数微秒奖励保留。主比较按声明的 2/10 CPU 秒预算配对，同时报告完整输出的实际总 CPU、墙钟和超预算；最终输出迟于预算仍保留，不能据此宣称严格硬截止优势。",
             "", "统计单元是独立物理来源组 **r008、r009（n=2）**；先在同来源/配置内平均种子，再平均配置、AU/AP 几何，最后等权平均两个来源组。配置和种子是重复测量，未做伪独立显著性检验或置信区间。每批 LLM 的所有冻结最终程序单独呈现，未按 TEST 效果筛除。",
             "", "缺失/不可行质量为 NA，非零。可行的共同核回退结果保留，但原生求解器失败、程序错误、guard 拒绝和零 head commit 同时报告。CPU 包含原生子进程；缺少内部 trace 的 CHILS 为观测受限，不能据 seed/end 标记推断其预算内无进展。",
             "", "- 冻结 protocol SHA256：`" + sha(evidence[0]["path"]) + "`",
             "- 分析脚本 SHA256：`" + sha(Path(__file__)) + "`",
             "- TEST 期望/已有运行：" + str(coverage["expected_test_runs"]) + "/" + str(coverage["observed_test_runs"]),
             "- 缺失/额外运行：" + str(len(coverage["missing_test_runs"])) + "/" + str(len(coverage["unregistered_test_runs"])),
             "- 状态：" + ("**部分结果，尚不具备完整比较结论。**" if partial else "注册运行覆盖完整；失败与回退仍如实呈现。"),
             "", "## 最终完整调度质量与计算成本", ""]
    qrows = []
    for q in testq:
        d = lookup.get((q["budget"], q["variant"], "degree", "all")); c = lookup.get((q["budget"], q["variant"], "chils", "all"))
        qrows.append([q["variant"], int(q["budget"]), fmt(q["mean_value_seconds"]), fmt(d["mean_delta_seconds"]) if d else "—", fmt(c["mean_delta_seconds"]) if c else "—", fmt(q["mean_cpu_seconds"]), fmt(q["mean_overshoot_seconds"]), fmt(q["over_declared_budget_rate"]), fmt(q["mean_feature_seconds"]), fmt(q["head_ever_committed_rate"])])
    lines += [table(["方法/程序", "预算s", "完整质量s", "vs Degree s", "vs CHILS p4 s", "实际CPU s", "超预算s", "超预算率", "特征CPU s", "head提交率"], qrows), "", "主表使用最终完整输出；所有计时未裁剪到声明预算。差值为正表示本方法完整质量较高，负值完整保留。完整原始与精确分数见 `complete_results.csv`、`quality_summary.csv`、`paired_runs.csv`、`paired_summary.csv`。", "", "## 约束配置响应与来源组差异", ""]
    scope = [s for s in summaries if s["split"] == "test" and s["variant"] in protocol["final_program_ids"] and s["baseline"] in ("degree", "chils") and s["family"] in ("known", "uniform", "heterogeneous", "unseen", "stress")]
    lines.append(table(["程序", "预算s", "对照", "配置组", "差值s", "r008 s", "r009 s", "正/零/负重复运行"], [[s["variant"], int(s["budget"]), s["baseline"], s["family"], fmt(s["mean_delta_seconds"]), fmt(float(Fraction(s["groups_exact"]["r008"]))) if "r008" in s["groups_exact"] else "NA", fmt(float(Fraction(s["groups_exact"]["r009"]))) if "r009" in s["groups_exact"] else "NA", str(s["positive_paired_runs"]) + "/" + str(s["zero_paired_runs"]) + "/" + str(s["negative_paired_runs"])] for s in scope]))
    lines += ["", "已见配置为 A/W/E/J；新配置包含均匀680、均匀1800压力和680/1200、1200/680混合。均匀/异质分组与已见/未见分组是两种描述维度，彼此有重叠，不能相加当作额外样本。逐配置结果在精确 CSV 中。", "", "## LLM证据链：严格拟合、训练收益与测试收益", "", table(["冻结程序", "严格TRAIN fit", "通过/总数", "TRAIN vs Degree s", "TEST vs Degree s"], [[c["program_id"], c["strict_fit_exact"] or "NA", str(c["fit_passed"]) + "/" + str(c["fit_total"]) if c["fit_total"] is not None else "NA", fmt(c["train_delta_seconds"]), fmt(c["test_delta_seconds"])] for c in chain]), "", "这条链仅描述不同测量的结果。修复信息、严格排序拟合和最终完整调度收益并不互相保证；若训练收益为零或与拟合不一致，该现象保留，不能解释为已证实的泛化优势。此表固定2s且 TRAIN/TEST 都用已见 A/W/E/J 配置，避免将配置差异混入证据链。", "", "## 原生失败、计算开销与候选回退", ""]
    issues = []
    for q in testq:
        if q["native_status_counts"] or q["construction_status_counts"] or q["negative_raw_construction_runs"] or q["repair_negative_raw_gain_count"]:
            issues.append([q["variant"], int(q["budget"]), q["complete_feasible_runs"], q["observed_runs"], json.dumps(q["native_status_counts"], ensure_ascii=False), json.dumps(q["construction_status_counts"], ensure_ascii=False), q["negative_raw_construction_runs"], q["repair_negative_raw_gain_count"], q["repair_accepted_count"], fmt(q["mean_programme_error_count"])])
    lines += [table(["方法/程序", "预算s", "可行数", "已有数", "native状态", "构造状态", "负原始构造数", "负repair次数", "接受repair次数", "平均程序错误数"], issues), "", "守护核拒绝负候选可能使完整质量不下降，但这不代表合成 head 有贡献；提交率、原始负构造和特征工作量一起解释。deadline中断、程序错误和原生求解失败分开记录。未产出结果的付费失败运行见 `failed_jobs.json`，不以零质量代替。", "", "## 图表与可观察性", ""]
    for receipt in receipts:
        lines += ["- **" + receipt["figure"] + "**：" + receipt["status"] + "。" + receipt.get("caption", receipt.get("reason", ""))]
    lines += ["", "所有图使用统一字体、颜色、批次标记和单位，并输出整图/独立小面板 PDF 与300dpi PNG。全零、饱和或不足以形成真实曲线的内容保持精确数值表，不制造中间轨迹。CHILS 仅显示可观察标记；无内部 trace 不等同于无算法进展。", "", "## baseline出处与复现边界", "", "CHILS 使用 [SEA 2025 发表版本](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SEA.2025.22)及[原始实现](https://github.com/KarlsruheMIS/CHILS)，提交 `515952724cd3dcc6c4365a340ecf0f1da782119a`；p1/p4指population，均单线程。CP-SAT引用[CP 2023发表介绍](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2023.3)，ORTools9.15.6755单worker。输入64位整数微秒权重不round。Degree/weight/GRASP为同核经典head，local2swap为本项目独立LS；不冒称完整原论文算法复现。", "", "## 证据文件", "", table(["文件", "SHA256", "类型"], [[e["path"], e["sha256"], e.get("kind", "paid result projection")] for e in evidence]), "", "- `analysis_registration.json`：结果前注册指标与图样式。", "- `coverage.json` / `analysis_audit.json`：完整性、失败、missing、native观测限制。", "- `complete_results.csv`：全部纳入结果，含失败/回退/零提交/实际成本。", "- `paired_runs.csv` / `paired_summary.csv`：exact微秒配对与来源组聚合。", "- `train_fit_quality_chain.csv`：选定程序的固定TRAIN→TEST链。", "- `real_incumbent_events.csv`：真实commit事件，不插值。", "- `figure_receipts.json`：每图来源、状态、解释与缺失原因。", "", "本报告不推断最优性，也不以两组物理来源宣称一般性统计保证。发现负差、训练收益未提升、成本过大、方法失败或无有效head提交时，应据该记录调整研究解释；不能仅因目标是展示创新而删除这些证据。", ""]
    (output / "完整LLM算法性能对比.md").write_text("\n".join(lines), encoding="utf-8")


def self_test():
    # Methodological tests only, no fabricated research artifact or chart.
    rows = [{"source_group": "r008", "source": "CP-AU-r008", "config": "g0340", "x": Fraction(1)},
            {"source_group": "r009", "source": "CP-AU-r009", "config": "g0340", "x": Fraction(9)}]
    rows += [dict(rows[0]) for _ in range(11)]
    value, groups, _ = hierarchical_mean(rows, lambda r: r["x"])
    assert value == 5 and groups == {"r008": Fraction(1), "r009": Fraction(9)}
    assert avg([Fraction(1, TICKS), Fraction(2, TICKS)]) == Fraction(3, 2 * TICKS)
    assert canonical("A") == canonical("gW0340_gE0340_s0150") == "g0340"
    native = {"method": "chils", "declared_cpu_seconds": 2., "_events": [{"stage": "common_degree_seed", "cpu_seconds": .1, "value_ticks": 1}, {"stage": "final", "cpu_seconds": 2.02, "value_ticks": 2}]}
    assert observable_at_budget(native)[0] is None
    native["method"] = "program"; assert observable_at_budget(native)[0] == 1
    assert fmt(Fraction(1, TICKS)) != "0"
    print("Analysis methodological checks passed: exact ticks, equal physical groups, config aliases, observation-limited native trace.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true", help="Write data-free preregistration only")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--released-formal-results", action="store_true", help="Root explicitly released frozen formal result artifacts")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--program-bank", type=Path)
    parser.add_argument("--results", type=Path, action="append", default=[], help="Explicit paid result projection JSON; repeat for TRAIN/VAL/TEST")
    parser.add_argument("--fit-root", type=Path, action="append", default=[])
    parser.add_argument("--allow-partial", action="store_true", help="Mark every table/report incomplete; never fill missing values")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    if args.self_test: self_test()
    if args.prepare:
        if args.results or args.protocol or args.program_bank or args.fit_root: raise ValueError("Data-free prepare cannot accept results or programme inputs")
        args.output.mkdir(parents=True, exist_ok=True); dump(args.output / "analysis_registration.json", REGISTRATION)
        print("Data-free registration written. No result, graph, model, STK or oracle input was opened."); return
    if not args.released_formal_results or not args.protocol or not args.program_bank or not args.results:
        parser.error("Formal result analysis needs release flag, frozen protocol/bank and explicit result paths; use --prepare before results.")
    protocol = read(args.protocol)
    if protocol.get("frozen") is not True: raise ValueError("Formal analysis requires frozen protocol")
    protocol_sha, bank_sha = sha(args.protocol), sha(args.program_bank)
    if protocol.get("frozen_program_bank_sha256") != bank_sha: raise ValueError("Supplied bank differs from frozen protocol")
    bank = {v["id"]: v for v in read(args.program_bank)["programs"]}
    selected = protocol["final_program_ids"]
    if any(pid not in bank for pid in selected): raise ValueError("Frozen programme absent from bank")
    records, failures, inputs, excluded = load_results(args.results, bank, protocol, protocol_sha, bank_sha)
    coverage = check_coverage(records, protocol)
    coverage["both_batch_programmes"] = {arm: sorted({batch(bank[p]) for p in selected if bank[p]["arm"] == arm and batch(bank[p]) is not None}) for arm in sorted({bank[p]["arm"] for p in selected})}
    if coverage["unregistered_test_runs"]: raise ValueError("Unregistered TEST runs cannot enter analysis")
    partial = bool(coverage["missing_test_runs"])
    if partial and not args.allow_partial: raise ValueError("Formal TEST grid incomplete; use --allow-partial only for explicitly incomplete progress report")
    args.output.mkdir(parents=True, exist_ok=True)
    previous = args.output / "analysis_registration.json"
    if previous.is_file() and read(previous) != REGISTRATION: raise ValueError("Saved pre-result registration differs; do not silently rewrite analysis plan")
    dump(previous, REGISTRATION)
    evidence = [{"path": str(args.protocol.resolve()), "sha256": protocol_sha, "kind": "frozen protocol"}, {"path": str(args.program_bank.resolve()), "sha256": bank_sha, "kind": "frozen programme bank"}] + inputs
    fits = load_fit(args.fit_root, selected, bank, evidence)
    events = trace_rows(records); pairs, missing_pairs = pair_records(records)
    summaries, quality = summarise_pairs(pairs), summarise_quality(records)
    chain = chain_rows(summaries, fits, selected)
    csv_dump(args.output / "complete_results.csv", records); csv_dump(args.output / "paired_runs.csv", pairs)
    csv_dump(args.output / "paired_summary.csv", summaries); csv_dump(args.output / "quality_summary.csv", quality)
    csv_dump(args.output / "real_incumbent_events.csv", events); csv_dump(args.output / "train_fit_quality_chain.csv", chain)
    dump(args.output / "failed_jobs.json", failures); dump(args.output / "coverage.json", coverage)
    dump(args.output / "excluded_nonfinal_programmes.json", excluded)
    receipts = plots(args.output / "figures", records, pairs, summaries, quality, chain, bank, protocol) if not args.no_plots else [{"figure": "all", "status": "not_requested"}]
    dump(args.output / "figure_receipts.json", receipts)
    dump(args.output / "analysis_audit.json", {"version": VERSION, "no_graphs_scored": True, "TEST_selection_calls": 0, "model_calls": 0, "optimizer_calls": 0, "partial": partial, "exact_ticks": True, "independent_test_groups": 2, "input_provenance": evidence, "failed_jobs": len(failures), "missing_paired_outputs": missing_pairs, "native_observation_limitation": "CHILS internal trace unavailable; observable seed/end not hard-deadline algorithm progress", "script_sha256": sha(Path(__file__))})
    write_report(args.output, records, summaries, quality, chain, fits, failures, coverage, receipts, evidence, protocol, bank, partial)
    artifacts = [p for p in args.output.rglob("*") if p.is_file() and p.name != "evidence_index.json"]
    dump(args.output / "evidence_index.json", {"version": VERSION, "inputs": evidence,
         "artifacts": [{"path": p.relative_to(args.output).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(artifacts)],
         "scope": "Reviewable output files and inputs; no optimizer/model rerun. A repeated analysis changes only derived outputs."})
    print(json.dumps({"records": len(records), "pairs": len(pairs), "failed_jobs": len(failures), "partial": partial, "report": str(args.output / "完整LLM算法性能对比.md")}, ensure_ascii=False))


if __name__ == "__main__": main()
