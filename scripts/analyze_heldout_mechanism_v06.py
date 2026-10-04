"""Read-only analysis of complete, independently audited R2/EoH heldout batches.

No programme, feature, scheduler or oracle is executed. Missing predictions
and error incumbents remain explicit; normal-only performance is separate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import random
import tarfile

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ["original"] + [f"relabel_{i}" for i in range(5)]
KINDS = {"R2": ("v06_R2_heldout_results_server_002", 27, 162, 11664),
         "EoH": ("v06_EoH_heldout_results_server_001", 4, 24, 1728)}
REPLICATES, SEED = 2000, 261004
AUDITOR = ROOT / "scripts/verify_heldout_results_v06.py"
CONFIGS = (ROOT / "configs/analysis_v06_001.json", ROOT / "configs/analysis_refinement_v06_002.json")
CONFIG_SHA256 = {
    "configs/analysis_v06_001.json": "52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1",
    "configs/analysis_refinement_v06_002.json": "f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769",
}
INDEPENDENT_HELPERS = ("scripts/verify_matched_llm_v05.py", "scripts/verify_public_alias_v05.py",
    "scripts/verify_synthesis_train_v06.py")


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_analysis_configs(paths):
    """Byte-pin both preregistrations before any heldout archive payload read."""
    if len(paths) != len(CONFIG_SHA256):
        raise ValueError("Both exact frozen analysis configurations are required")
    hashes, configs = {}, []
    for path, (name, expected) in zip(paths, CONFIG_SHA256.items()):
        raw = Path(path).read_bytes()
        actual = sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError("Frozen analysis configuration byte hash changed: " + name)
        hashes[name] = actual
        configs.append(json.loads(raw))
    if (configs[0].get("registered_before_any_TEST_certificate_or_program_evaluation") is not True
        or configs[1].get("registered_before_any_R2_TRAIN_candidate_assessment_or_TEST_evaluation") is not True):
        raise ValueError("Registered pre-TEST analysis scopes are required")
    return hashes


def independent_helper_hashes():
    return {name: digest(ROOT / name) for name in INDEPENDENT_HELPERS}


def number(value):
    if value is None:
        return None
    if type(value) not in (str, int, float, bool, Fraction):
        raise ValueError("Unsupported numeric receipt")
    value = Fraction(value)
    if not math.isfinite(float(value)):
        raise ValueError("Nonfinite numeric receipt")
    return value


def quantile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position); upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_mean(rows, key, replicates=REPLICATES, seed=SEED):
    """Stratified cluster sampling; all rows in each source/pair stay together."""
    grouped = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    for row in rows:
        aggregate = grouped[row["family"]][row["cluster"]]
        v = number(row.get(key))
        if v is not None:
            aggregate[0] += float(v); aggregate[1] += 1
    strata = [[clusters[k] for k in sorted(clusters)] for _, clusters in sorted(grouped.items())]
    rng, samples = random.Random(seed), []
    for _ in range(replicates):
        numerator = 0.0; denominator = 0
        for stratum in strata:
            for index in rng.choices(range(len(stratum)), k=len(stratum)):
                total, count = stratum[index]
                numerator += total; denominator += count
        if denominator:
            samples.append(numerator / denominator)
    return {"method": "family-stratified source/pair-cluster percentile bootstrap",
        "replicates": replicates, "seed": seed, "valid_replicates": len(samples),
        "cluster_count": sum(len(s) for s in strata), "family_count": len(strata),
        "lower_95": quantile(samples, 0.025), "upper_95": quantile(samples, 0.975),
        "scope": "Source uncertainty conditional on these frozen programmes; not model-population uncertainty."}


def summarize(rows, key, with_bootstrap=True):
    measured = [number(r.get(key)) for r in rows if r.get(key) is not None]
    total = sum(measured, Fraction())
    conditional = total / len(measured) if measured else None
    full = conditional if rows and len(measured) == len(rows) else None
    ci = bootstrap_mean(rows, key) if with_bootstrap and rows else None
    return {"assigned_members": len(rows), "measured_members": len(measured),
        "missing_members": len(rows) - len(measured), "measured_sum_exact": str(total) if measured else None,
        "conditional_mean": float(conditional) if conditional is not None else None,
        "conditional_mean_exact": str(conditional) if conditional is not None else None,
        "full_members_mean": float(full) if full is not None else None,
        "full_members_mean_exact": str(full) if full is not None else None,
        "conditional_cluster_bootstrap": ci,
        "full_members_cluster_bootstrap": ci if full is not None else None}


def validate_audit(report, kind, archive_sha, auditor_sha, helper_sha=None):
    _, _, count, states = KINDS[kind]
    expected_helpers = independent_helper_hashes() if helper_sha is None else helper_sha
    if (report.get("version") != f"v06_independent_{kind}_heldout_result_audit_001"
        or report.get("kind") != kind or type(report.get("checks")) is not int or report["checks"] <= 0
        or type(report.get("errors")) is not int or report["errors"] != 0 or report.get("error_records") != []
        or report.get("archive_sha256") != archive_sha or report.get("audit_script_sha256") != auditor_sha
        or report.get("independent_helper_sha256") != expected_helpers
        or report.get("verified_identity_variant_count") != count
        or report.get("requested_state_assignments") != states
        or report.get("production_scheduler_or_oracle_calls") != 0 or report.get("programme_selection") is not False):
        raise ValueError("Require an exact-source, full-frame, zero-error independent heldout audit: " + kind)


def load_batch(archive, audit_path, kind):
    """Audit and terminal marker checked before any result/input payload read."""
    validate_analysis_configs(CONFIGS)
    archive, audit_path = Path(archive), Path(audit_path)
    report = json.loads(audit_path.read_bytes())
    archive_sha = digest(archive)
    validate_audit(report, kind, archive_sha, digest(AUDITOR))
    stem, nident, count, states = KINDS[kind]
    with tarfile.open(archive, "r:gz") as tar:
        files = {}
        for member in tar.getmembers():
            p = PurePosixPath(member.name)
            if ".." in p.parts or p.is_absolute() or not (member.isdir() or member.isfile()):
                raise ValueError("Unsafe archive member")
            if member.isfile():
                if member.name in files:
                    raise ValueError("Duplicate archive path")
                files[member.name] = member
        def raw(name):
            return tar.extractfile(files[name]).read()
        terminal_raw = raw(stem + "/complete.json")
        complete = json.loads(terminal_raw)
        if (complete.get("execution_complete") is not True or complete.get("assigned") != count
            or complete.get("returned_assignments") != count or complete.get("requested_state_assignments") != states
            or complete.get("selection_performed") is not False or complete.get("extra_oracle_calls") != 0
            or complete.get("no_fallback") is not True):
            raise ValueError("Incomplete/non-frozen batch is not an analysis input")
        results_raw = raw(stem + "/results.jsonl")
        if sha256(results_raw).hexdigest() != complete["results_sha256"]:
            raise ValueError("Terminal results byte hash changed")
        proto_raw = raw("registration/protocol.json")
        proto = json.loads(proto_raw)
        if len(proto["entries"]) != nident or proto["variants"] != VARIANTS or proto["requested_state_assignments"] != states:
            raise ValueError("Frozen identity/variant frame changed")
        entries = proto["entries"]
        if len({e["id"] for e in entries}) != nident:
            raise ValueError("Duplicate deployment identity")
        records = json.loads(raw("registration/test_inputs.json"))["records"]
        labels = json.loads(raw("registration/test_certificates.json"))["labels"]
        mappings = json.loads(raw("registration/relabel_inventory.json"))
        rows = [json.loads(line) for line in results_raw.splitlines() if line]
    expected = {(e["id"], v) for e in entries for v in VARIANTS}
    if len(records) != 72 or len(rows) != count or {(r["id"], r["variant"]) for r in rows} != expected:
        raise ValueError("All frozen states and identity/variant assignments are required")
    return {"kind": kind, "entries": entries, "records": records, "labels": labels,
        "mappings": mappings, "rows": rows, "complete": complete, "protocol": proto,
        "binding": {"kind": kind, "archive": str(archive), "archive_sha256": archive_sha,
            "independent_audit": str(audit_path), "independent_audit_sha256": digest(audit_path),
            "independent_auditor_source_sha256": report["audit_script_sha256"],
            "independent_helper_sha256": report["independent_helper_sha256"],
            "independent_audit_checks": report["checks"], "independent_audit_errors": 0,
            "results_sha256": complete["results_sha256"],
            "terminal_marker_sha256": sha256(terminal_raw).hexdigest(), "protocol_sha256": sha256(proto_raw).hexdigest(),
            "root_release_sha256": complete["root_release_sha256"], "source_sha256": proto["source_sha256"]}}


def catalogue(batch, variant):
    """Minimal registered label metadata, not a feature or programme evaluation."""
    lmap = {r["id"]: r for r in batch["labels"]}
    mapping = None if variant == "original" else next(p["mappings"] for p in batch["mappings"] if p["variant"] == variant)
    rows = []
    for r in sorted(batch["records"], key=lambda r: r["id"]):
        m = None if mapping is None else mapping[r["cluster"]]
        for i, q in enumerate(lmap[r["id"]]["rows"]):
            d = q["difference"]
            convert = lambda v: m[v] if m is not None and v is not None else v
            side = 0 if not r["paired"] or r.get("side") == "left" else 1
            rows.append({"state": r["id"], "family": r["family"], "cluster": r["cluster"],
                "pair": r.get("pair"), "side": r.get("side"), "query_index": i,
                "a": convert(q["a"]), "b": convert(q["b"]), "query_kind": q["kind"],
                "certificate_status": d["status"], "preferred": convert(d["preferred"]),
                "lower_exact": d["lower_exact"], "upper_exact": d["upper_exact"],
                "catalogue_base_alias": q["base_alias_by_side"][side]})
    return rows


def query_losses(row):
    result = {"certified_gap_min_exact": None, "certified_gap_weighted_specification_violation_exact": None,
        "hypothetical_pairwise_rank_choice": None, "hypothetical_pairwise_rank_choice_minimum_loss_exact": None,
        "score_tie": None, "tiny_positive_margin_failure": None}
    if row["certificate_status"] != "strict":
        return result
    a, b, p = row["a"], row["b"], row["preferred"]
    gap = Fraction(row["lower_exact"]) if p == a else -Fraction(row["upper_exact"])
    if p not in (a, b) or gap <= 0:
        raise ValueError("Strict signed interval has no sound positive preferred gap")
    result["certified_gap_min_exact"] = str(gap)
    if row.get("passed") is None or row.get("score_a") is None or row.get("score_b") is None:
        return result
    sa, sb = number(row["score_a"]), number(row["score_b"])
    chosen = a if sa > sb else b if sb > sa else min(a, b)
    ps, other = (sa, sb) if p == a else (sb, sa)
    result.update(certified_gap_weighted_specification_violation_exact=str(Fraction() if row["passed"] else gap),
        hypothetical_pairwise_rank_choice=chosen,
        hypothetical_pairwise_rank_choice_minimum_loss_exact=str(Fraction() if chosen == p else gap),
        score_tie=sa == sb, tiny_positive_margin_failure=not row["passed"] and ps > other)
    return result


def compact_queries(batch, assignment, labels):
    interface = assignment.get("interface")
    observed = {(q["state"], q["query_index"]): q for q in (interface or {}).get("query_checks", [])}
    output = []
    for label in labels:
        key = label["state"], label["query_index"]
        measured = observed.get(key)
        q = {**label, "kind": batch["kind"], "program_id": assignment["id"], "variant": assignment["variant"],
            "interface_available": interface is not None, "passed": None, "score_a": None, "score_b": None,
            "actual_base_alias": label["catalogue_base_alias"] if label["certificate_status"] == "strict" else None,
            "demanded_feature_alias": None}
        if measured is not None:
            for k in ("a", "b", "preferred", "certificate_status", "lower_exact", "upper_exact"):
                if measured[k] != label[k]:
                    raise ValueError("Audited query and frozen catalogue disagree: " + k)
            for k in ("passed", "score_a", "score_b", "actual_base_alias", "demanded_feature_alias"):
                q[k] = measured.get(k, q[k])
        elif interface is not None:
            raise ValueError("Complete audited interface omitted a planned query")
        q.update(query_losses(q))
        output.append(q)
    if len(observed) != (len(labels) if interface is not None else 0):
        raise ValueError("Unexpected extra/duplicate interface query")
    return output


def paired_rows(queries):
    grouped = defaultdict(dict)
    for q in queries:
        if q["pair"] is not None:
            key = q["program_id"], q["variant"], q["pair"], q["query_index"]
            if q["side"] in grouped[key]:
                raise ValueError("Duplicate constraint side")
            grouped[key][q["side"]] = q
    result = []
    for key, sides in sorted(grouped.items()):
        if set(sides) != {"left", "right"}:
            raise ValueError("Missing paired constraint endpoint")
        l, r = sides["left"], sides["right"]
        if (l["a"], l["b"], l["cluster"], l["family"]) != (r["a"], r["b"], r["cluster"], r["family"]):
            raise ValueError("Changed competing actions or source cluster across intervention")
        ls, rs = l["certificate_status"], r["certificate_status"]
        if ls == rs == "strict":
            category = "strict_preservation" if l["preferred"] == r["preferred"] else "strict_reversal"
            passed = l["passed"] and r["passed"] if type(l["passed"]) is bool and type(r["passed"]) is bool else None
        elif ls == rs == "exact_tie":
            category, passed = "exact_tie_both", None
        elif "unknown" in (ls, rs):
            category, passed = "incomplete_interval", None
        else:
            category, passed = "strict_to_tie" if ls == "strict" else "tie_to_strict", None
        result.append({"program_id": key[0], "variant": key[1], "pair": key[2], "query_index": key[3],
            "cluster": l["cluster"], "family": l["family"], "category": category, "pair_passed": passed,
            "left_passed": l["passed"], "right_passed": r["passed"],
            "left_preferred": l["preferred"], "right_preferred": r["preferred"]})
    return result


def compact_kernel(batch, assignment):
    observed = {r["id"]: r for r in assignment["kernel_rows"]}
    output = []
    for r in sorted(batch["records"], key=lambda r: r["id"]):
        saved = observed.get(r["id"], {})
        result = saved.get("result")
        normal = result is not None and result["completed"] is True and result["error"] is None
        retained = result is not None and result["feasible"] is True and result["incumbent_available"] is True
        meter = (result or {}).get("meter", {})
        feature, repair = meter.get("feature_work"), meter.get("repair_work")
        work = feature + repair if feature is not None and repair is not None else None
        reward = result["value_exact"] if retained else None
        output.append({"kind": batch["kind"], "program_id": assignment["id"], "variant": assignment["variant"],
            "state_id": r["id"], "family": r["family"], "cluster": r["cluster"], "pair": r.get("pair"), "side": r.get("side"),
            "missing_identity": assignment["identity"].get("missing_baseline", False),
            "worker_error": assignment.get("worker_error"), "validation_error": saved.get("error"),
            "kernel_error": (result or {}).get("error"),
            "normal_completed": normal, "verified_incumbent": retained,
            "normal_budget_stop": normal and result.get("budget_exhausted", False),
            "status": result["status"] if result is not None else "missing_identity" if assignment["identity"].get("missing_baseline") else "worker_or_validation_error",
            "diagnostic_reward_exact": reward, "normal_performance_reward_exact": reward if normal else None,
            "initial_reward_exact": (result or {}).get("initial_value_exact"),
            "diagnostic_improvement_over_initial_exact": str(Fraction(reward) - Fraction(result["initial_value_exact"])) if retained else None,
            "feature_work": feature, "repair_work": repair, "total_work": work,
            "search_nodes": meter.get("search_nodes"), "normal_total_work": work if normal else None,
            "normal_feature_work": feature if normal else None, "normal_repair_work": repair if normal else None,
            "normal_search_nodes": meter.get("search_nodes") if normal else None,
            "kernel_cpu_seconds": (result or {}).get("cpu_seconds"), "kernel_wall_seconds": (result or {}).get("wall_seconds"),
            "task_cpu_seconds": saved.get("task_cpu_seconds"), "task_wall_seconds": saved.get("task_wall_seconds"),
            "graph_materialization_cpu_seconds": saved.get("graph_materialization_cpu_seconds"),
            "graph_materialization_wall_seconds": saved.get("graph_materialization_wall_seconds"),
            "normal_kernel_cpu_seconds": (result or {}).get("cpu_seconds") if normal else None,
            "normal_kernel_wall_seconds": (result or {}).get("wall_seconds") if normal else None,
            "normal_task_cpu_seconds": saved.get("task_cpu_seconds") if normal else None,
            "normal_task_wall_seconds": saved.get("task_wall_seconds") if normal else None})
    return output


def add_degree_contrasts(kernel_rows):
    lookup = {(r["variant"], r["state_id"]): r for r in kernel_rows if r["program_id"] == "fixed_degree"}
    for row in kernel_rows:
        degree = lookup.get((row["variant"], row["state_id"]))
        available = degree is not None and row["normal_completed"] and degree["normal_completed"]
        row.update(degree_normal_completed=degree["normal_completed"] if degree is not None else False,
            degree_diagnostic_reward_exact=degree["diagnostic_reward_exact"] if degree is not None else None,
            normal_paired_degree_objective_gain_exact=None, normal_paired_degree_percentage_gain=None,
            normal_paired_degree_work_ratio=None, normal_paired_degree_cpu_ratio=None, normal_paired_degree_wall_ratio=None)
        if available:
            x, d = Fraction(row["normal_performance_reward_exact"]), Fraction(degree["normal_performance_reward_exact"])
            row["normal_paired_degree_objective_gain_exact"] = str(x - d)
            row["normal_paired_degree_percentage_gain"] = str(100 * (x - d) / abs(d)) if d else None
            for output, key in (("normal_paired_degree_work_ratio", "normal_total_work"),
                ("normal_paired_degree_cpu_ratio", "normal_kernel_cpu_seconds"), ("normal_paired_degree_wall_ratio", "normal_kernel_wall_seconds")):
                den = number(degree[key]); num = number(row[key])
                row[output] = str(num / den) if den and num is not None else None


def query_summary(rows, pairs):
    strict = [q for q in rows if q["certificate_status"] == "strict"]
    alias = [q for q in strict if q["actual_base_alias"] is True]
    families = sorted({q["family"] for q in rows})
    return {"planned_queries": len(rows), "certificate_status_counts": dict(Counter(q["certificate_status"] for q in rows)),
        "strict_fit": summarize(strict, "passed"), "actual_base_alias_strict_fit": summarize(alias, "passed"),
        "strict_score_tie_counts": {"measured": sum(q["score_tie"] is not None for q in strict), "ties": sum(q["score_tie"] is True for q in strict)},
        "tiny_positive_margin_failures": sum(q["tiny_positive_margin_failure"] is True for q in strict),
        "certified_gap_weighted_specification_violation": summarize(strict, "certified_gap_weighted_specification_violation_exact"),
        "hypothetical_pairwise_rank_choice_minimum_loss": summarize(strict, "hypothetical_pairwise_rank_choice_minimum_loss_exact"),
        "loss_aggregation_scope": {"families": families, "mixed_family_diagnostic_only": len(families) > 1,
            "primary_paper_loss_eligible": len(families) == 1,
            "units": "Unscaled conditional completion-value gaps in each source family's objective units.",
            "interpretation": "Mixed-family gap sums/means are retained diagnostics only; primary loss conclusions use per-family summaries."},
        "pair_categories": {category: {"assigned_pairs": sum(p["category"] == category for p in pairs),
            "joint_correctness": summarize([p for p in pairs if p["category"] == category], "pair_passed")}
            for category in ("strict_reversal", "strict_preservation", "exact_tie_both", "strict_to_tie", "tie_to_strict", "incomplete_interval")}}


def kernel_summary(rows):
    stats = {"assigned_states": len(rows), "normal_completed": sum(r["normal_completed"] for r in rows),
        "verified_incumbents": sum(r["verified_incumbent"] for r in rows),
        "missing_identity_states": sum(r["missing_identity"] for r in rows),
        "worker_or_validation_errors": sum(not r["missing_identity"] and not r["verified_incumbent"] for r in rows),
        "retained_error_incumbents_diagnostic_only": sum(r["verified_incumbent"] and not r["normal_completed"] for r in rows),
        "normal_budget_stops": sum(r["normal_budget_stop"] for r in rows), "status_counts": dict(Counter(r["status"] for r in rows))}
    stats["normal_performance"] = {key: summarize(rows, key) for key in (
        "normal_performance_reward_exact", "normal_total_work", "normal_feature_work", "normal_repair_work", "normal_search_nodes",
        "normal_kernel_cpu_seconds", "normal_kernel_wall_seconds", "normal_task_cpu_seconds", "normal_task_wall_seconds",
        "normal_paired_degree_objective_gain_exact", "normal_paired_degree_percentage_gain", "normal_paired_degree_work_ratio",
        "normal_paired_degree_cpu_ratio", "normal_paired_degree_wall_ratio")}
    stats["retained_incumbent_diagnostics"] = {key: summarize(rows, key, with_bootstrap=False) for key in (
        "diagnostic_reward_exact", "diagnostic_improvement_over_initial_exact", "initial_reward_exact", "total_work",
        "kernel_cpu_seconds", "kernel_wall_seconds", "task_cpu_seconds", "task_wall_seconds")}
    return stats


def robustness(variants, statistic):
    """Preserve every relabel; worst work/time is the maximum, fit/reward minimum."""
    values = [variants[v] for v in VARIANTS[1:]]
    known = [number(v) for v in values if v is not None]
    mean = sum(known, Fraction()) / len(known) if known else None
    worst = (max(known) if statistic == "cost" else min(known)) if known else None
    complete = len(known) == 5
    return {"original": variants["original"], "all5_relabels": values, "measured_relabels": len(known),
        "mean_of_observed_relabels": float(mean) if mean is not None else None,
        "worst_of_observed_relabels": float(worst) if worst is not None else None,
        "all5_mean": float(mean) if complete else None, "all5_worst": float(worst) if complete else None,
        "all5_available": complete, "worst_direction": "maximum" if statistic == "cost" else "minimum"}


def rename_source_statistics(program_id, queries, kernel_rows):
    """Collapse five dependent relabels before source bootstrap, keeping nulls."""
    query_groups, kernel_groups = defaultdict(dict), defaultdict(dict)
    for q in queries:
        if q["program_id"] == program_id and q["variant"] != "original" and q["certificate_status"] == "strict":
            query_groups[q["state"], q["query_index"]][q["variant"]] = q
    for r in kernel_rows:
        if r["program_id"] == program_id and r["variant"] != "original":
            kernel_groups[r["state_id"]][r["variant"]] = r
    collapsed_queries = []
    for group in query_groups.values():
        rows = [group[v] for v in VARIANTS[1:]]
        aliases = {r["actual_base_alias"] for r in rows}
        if len(aliases) != 1:
            raise ValueError("Relabelled base alias changed")
        values = [number(r["passed"]) for r in rows]
        known = all(v is not None for v in values)
        collapsed_queries.append({"family": rows[0]["family"], "cluster": rows[0]["cluster"],
            "actual_base_alias": rows[0]["actual_base_alias"],
            "all5_mean_fit": str(sum(values, Fraction()) / 5) if known else None,
            "all5_worst_fit": str(min(values)) if known else None})
    collapsed_kernel = []
    for group in kernel_groups.values():
        rows = [group[v] for v in VARIANTS[1:]]
        collapsed = {"family": rows[0]["family"], "cluster": rows[0]["cluster"]}
        for key, direction in (("normal_performance_reward_exact", "reward"), ("normal_paired_degree_percentage_gain", "reward"),
            ("normal_total_work", "cost"), ("normal_kernel_cpu_seconds", "cost"), ("normal_kernel_wall_seconds", "cost")):
            values = [number(r[key]) for r in rows]
            known = all(v is not None for v in values)
            collapsed["all5_mean_" + key] = str(sum(values, Fraction()) / 5) if known else None
            collapsed["all5_worst_" + key] = str(max(values) if direction == "cost" else min(values)) if known else None
        collapsed_kernel.append(collapsed)
    alias_rows = [r for r in collapsed_queries if r["actual_base_alias"]]
    return {"strict_fit": {k: summarize(collapsed_queries, k) for k in ("all5_mean_fit", "all5_worst_fit")},
        "alias_strict_fit": {k: summarize(alias_rows, k) for k in ("all5_mean_fit", "all5_worst_fit")},
        "normal_kernel_by_family": {f: {key: summarize([r for r in collapsed_kernel if r["family"] == f], key)
            for key in next(iter(collapsed_kernel)).keys() if key not in ("family", "cluster")}
            for f in sorted({r["family"] for r in collapsed_kernel})},
        "scope": "Five mappings collapse inside each query/state before resampling source clusters; no permutation is an independent source."}


def role_contrasts(identities, queries, kernel_rows):
    """Four fixed blocks are displayed, never silently treated as new model draws."""
    entries = {(e.get("block"), e.get("role"), e.get("arm")): e for e in identities if e.get("kind") == "R2"
        and e.get("role") in ("proposed_witness_joint", "nonguarded_quality_comparator")}
    qmap = defaultdict(dict); kmap = defaultdict(dict)
    for q in queries:
        qmap[q["program_id"], q["variant"]][q["state"], q["query_index"]] = q
    for r in kernel_rows:
        kmap[r["program_id"], r["variant"]][r["state_id"]] = r
    definitions = [("quality_W_minus_R", "nonguarded_quality_comparator", "witness", "nonguarded_quality_comparator", "relations"),
        ("quality_R_minus_O", "nonguarded_quality_comparator", "relations", "nonguarded_quality_comparator", "objective"),
        ("joint_W_minus_quality_W", "proposed_witness_joint", "witness", "nonguarded_quality_comparator", "witness"),
        ("joint_W_minus_quality_R", "proposed_witness_joint", "witness", "nonguarded_quality_comparator", "relations"),
        ("joint_W_minus_quality_O", "proposed_witness_joint", "witness", "nonguarded_quality_comparator", "objective")]
    results = []
    for name, ar, aa, br, ba in definitions:
        for variant in VARIANTS:
            blocks, common_target_diffs = [], []
            for block in sorted({e.get("block") for e in identities if e.get("kind") == "R2" and e.get("role") == "proposed_witness_joint"}):
                a, b = entries[block, ar, aa], entries[block, br, ba]
                x, y = qmap[a["id"], variant], qmap[b["id"], variant]
                diffs, aliases, rewards = [], [], []
                for key, q in x.items():
                    r = y[key]
                    if q["certificate_status"] != "strict":
                        continue
                    measured = q["passed"] is not None and r["passed"] is not None
                    diff = {"family": q["family"], "cluster": q["cluster"], "difference": int(q["passed"]) - int(r["passed"]) if measured else None}
                    diffs.append(diff)
                    if q["actual_base_alias"]:
                        aliases.append(diff)
                for key, q in kmap[a["id"], variant].items():
                    r = kmap[b["id"], variant][key]
                    measured = q["normal_completed"] and r["normal_completed"]
                    rewards.append({"family": q["family"], "cluster": q["cluster"], "difference": str(Fraction(q["normal_performance_reward_exact"]) - Fraction(r["normal_performance_reward_exact"])) if measured else None})
                common_target_diffs.extend(diffs)
                blocks.append({"block": block, "a": a["id"], "b": b["id"],
                    "strict_fit_difference": summarize(diffs, "difference"), "alias_strict_fit_difference": summarize(aliases, "difference"),
                    "normal_raw_objective_difference_by_family": {f: summarize([r for r in rewards if r["family"] == f], "difference") for f in sorted({r["family"] for r in rewards})}})
            means = [b["strict_fit_difference"]["full_members_mean"] for b in blocks]
            results.append({"contrast": name, "variant": variant, "blocks": blocks,
                "equal_four_block_mean_strict_fit_difference": sum(means) / 4 if len(means) == 4 and all(v is not None for v in means) else None,
                "four_block_common_source_contrast": summarize(common_target_diffs, "difference"),
                "scope": "Common-selector quality contrasts remain warm-seed conditional; joint-versus-quality includes selection. Source intervals do not establish model-population effects."})
    return results


def analyze_batches(batches):
    identities, queries, kernel_rows, assignments = [], [], [], []
    r2 = next(b for b in batches if b["kind"] == "R2")
    eoh = next(b for b in batches if b["kind"] == "EoH")
    if Counter(e["role"] for e in r2["entries"]) != Counter({"proposed_witness_joint": 4,
        "nonguarded_quality_comparator": 12, "TRAIN_quality_only_control": 2,
        "classical_Degree": 1, "complete_relabel_control_bank": 8}):
        raise ValueError("Retain the actual16 R2 outputs and11 original controls")
    if Counter(e["role"] for e in eoh["entries"]) != Counter({"nonguarded_published_quality_baseline": 4}):
        raise ValueError("Retain all four EoH quality pipeline origins")
    if r2["records"] != eoh["records"] or r2["labels"] != eoh["labels"] or r2["mappings"] != eoh["mappings"]:
        raise ValueError("EoH addon must use the exact existing R2 evidence and five mappings")
    for batch in batches:
        for e in batch["entries"]:
            identities.append({**{k: e.get(k) for k in ("id", "role", "arm", "block", "slot", "priority", "source_id", "winner_origin", "missing_baseline", "main_comparison", "joint_gate_required", "actual_joint_gate_passed")},
                "kind": batch["kind"], "program_sha256": e.get("program_sha256"),
                "deployment_AST_sha256": canonical({k: e["program"][k] for k in ("features", "rule")}) if e.get("program") is not None else None})
        catalogues = {v: catalogue(batch, v) for v in VARIANTS}
        for row in batch["rows"]:
            queries.extend(compact_queries(batch, row, catalogues[row["variant"]]))
            kernel_rows.extend(compact_kernel(batch, row))
            interface = row.get("interface") or {}
            def quotient_summary(name):
                q = interface.get(name)
                return None if q is None else {k: q.get(k) for k in ("contradictory", "quotient_nodes", "quotient_edges", "self_loop_requirements")} | {"witness_kind_counts": dict(Counter(w["kind"] for w in q.get("structural_witnesses", [])))}
            assignments.append({"program_id": row["id"], "variant": row["variant"], "kind": batch["kind"],
                "assignment_status": row["assignment_status"], "worker_error": row.get("worker_error"),
                "interface_error": row.get("interface_error"), "interface_available": row.get("interface") is not None,
                "demanded_features": interface.get("demanded_features"), "quotient": quotient_summary("quotient"),
                "declared_quotient": quotient_summary("declared_quotient"), "quota_shortfalls": interface.get("quota_shortfalls"),
                "interface_feature_work": interface.get("interface_feature_work"), "interface_cpu_seconds": interface.get("interface_cpu_seconds"),
                "interface_wall_seconds": interface.get("interface_wall_seconds"), "actual_assignment_cpu_seconds": row.get("actual_cpu_seconds"),
                "actual_assignment_wall_seconds": row.get("actual_wall_seconds")})
    if len(identities) != 31 or len(kernel_rows) != 13392 or len({e["id"] for e in identities}) != 31:
        raise ValueError("Retain all31 identities and13392 state/variant positions")
    add_degree_contrasts(kernel_rows)
    pairs = paired_rows(queries)
    summaries = []
    for e in identities:
        byvariant = {}
        for variant in VARIANTS:
            qs = [q for q in queries if q["program_id"] == e["id"] and q["variant"] == variant]
            ps = [p for p in pairs if p["program_id"] == e["id"] and p["variant"] == variant]
            ks = [r for r in kernel_rows if r["program_id"] == e["id"] and r["variant"] == variant]
            byvariant[variant] = {"mechanism": query_summary(qs, ps),
                "mechanism_by_family": {f: query_summary([q for q in qs if q["family"] == f], [p for p in ps if p["family"] == f]) for f in sorted({q["family"] for q in qs})},
                "kernel_by_family": {f: kernel_summary([r for r in ks if r["family"] == f]) for f in sorted({r["family"] for r in ks})}}
        robust = {"strict_fit": robustness({v: byvariant[v]["mechanism"]["strict_fit"]["full_members_mean"] for v in VARIANTS}, "fit"),
            "alias_strict_fit": robustness({v: byvariant[v]["mechanism"]["actual_base_alias_strict_fit"]["full_members_mean"] for v in VARIANTS}, "fit"),
            "kernel_by_family": {}}
        for family in byvariant["original"]["kernel_by_family"]:
            robust["kernel_by_family"][family] = {key: robustness({v: byvariant[v]["kernel_by_family"][family]["normal_performance"][key]["full_members_mean_exact"] for v in VARIANTS}, direction)
                for key, direction in (("normal_performance_reward_exact", "reward"), ("normal_paired_degree_percentage_gain", "reward"),
                    ("normal_total_work", "cost"), ("normal_kernel_cpu_seconds", "cost"), ("normal_kernel_wall_seconds", "cost"))}
        summaries.append({"identity": e, "variants": byvariant, "five_rename_robustness": robust,
            "five_rename_source_bootstrap": rename_source_statistics(e["id"], queries, kernel_rows)})
    groups = defaultdict(list)
    for e in identities:
        if e["deployment_AST_sha256"] is not None:
            groups[e["deployment_AST_sha256"]].append(e["id"])
    return {"identities": identities, "summaries": summaries, "query_rows": queries, "pair_rows": pairs,
        "kernel_rows": kernel_rows, "assignment_rows": assignments,
        "role_contrasts": role_contrasts(identities, queries, kernel_rows),
        "dependent_duplicate_AST_groups": [{"deployment_AST_sha256": k, "ids": v} for k, v in groups.items() if len(v) > 1],
        "EoH_pipeline_origin_counts": dict(Counter(e.get("winner_origin") for e in identities if e["kind"] == "EoH")),
        "frame": {"R2_identities": 27, "EoH_identities": 4, "states": 72, "variants": VARIANTS,
            "kernel_positions": 13392, "query_positions": len(queries), "pair_positions": len(pairs)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("r2-archive", "r2-audit", "eoh-archive", "eoh-audit", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    out = Path(args.out)
    compact = out.with_name(out.stem + "_compact.json")
    if out.exists() or compact.exists():
        raise ValueError("Analysis artifacts are immutable; choose a new output")
    config_hashes = validate_analysis_configs(CONFIGS)
    batches = [load_batch(args.r2_archive, args.r2_audit, "R2"), load_batch(args.eoh_archive, args.eoh_audit, "EoH")]
    result = analyze_batches(batches)
    rows = {k: result.pop(k) for k in ("query_rows", "pair_rows", "kernel_rows", "assignment_rows")}
    metadata = {"analyzer_source_sha256": digest(__file__), "input_bindings": [b["binding"] for b in batches],
        "analysis_config_sha256": config_hashes,
        "bootstrap_replicates": REPLICATES, "bootstrap_seed": SEED, "source_and_pair_clusters_preserved": True,
        "metric_units": {"fit": "fraction; multiply contrasts by100 for percentage points",
            "degree_percentage_gain": "100*(programme reward-Degree reward)/abs(Degree reward)",
            "loss": "Per-family conditional completion-value units; mixed-family gap summaries are retained diagnostics only.",
            "work": "audited operation-count proxy", "cpu_and_wall": "audited measured seconds"},
        "programme_reexecution": False, "online_model_or_oracle_calls": 0, "selection_performed": False}
    compact_data = {"version": "v06_R2_EoH_heldout_analysis_compact_001", "metadata": metadata, "frame": result["frame"], **rows}
    compact_raw = (json.dumps(compact_data, ensure_ascii=False, allow_nan=False) + "\n").encode()
    report = {"version": "v06_R2_EoH_heldout_mechanism_analysis_001", "created_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata, "compact_file": str(compact), "compact_sha256": sha256(compact_raw).hexdigest(), **result,
        "limits": ["All31 identities remain; duplicate ASTs, relabels and constraint endpoints are dependent, not new draws.",
            "Bootstrap intervals concern source clusters conditional on four authoring blocks, warm seed and frozen identities.",
            "Certified-gap-weighted specification violation includes margin failures; it is not actual wrong-action loss.",
            "Hypothetical pairwise rank choice minimum loss uses ID tie break at the full residual boundary, not repair pivot/greedy or online regret.",
            "Mixed-family unscaled gap sums/means are diagnostic only; primary paper loss conclusions use per-family summaries.",
            "Programme error incumbents appear only in retained diagnostics; normal-only performance and explicit coverage are separate.",
            "No graph-sum quality normalization or cross-family raw-objective pooling; paired Degree comparisons use matched normal states.",
            "Executed CPU/wall/work remain audited receipts, not new timing measurements or model-generation cost.",
            "Missing predictions/rewards/costs are null; conditional statistics and full-members statistics have explicit denominators."]}
    out.parent.mkdir(parents=True, exist_ok=True)
    with compact.open("xb") as stream:
        stream.write(compact_raw)
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"analysis_sha256": digest(out), "compact_sha256": digest(compact), "frame": result["frame"]}))


if __name__ == "__main__":
    main()
