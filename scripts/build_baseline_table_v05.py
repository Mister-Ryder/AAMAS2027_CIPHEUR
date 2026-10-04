"""Build the main baseline table from immutable v04 observations, without reruns.

All point estimates are recomputed independently with exact Fraction rewards.
The saved source-cluster intervals are retained only after checking their means.
No solver, scheduling policy, model, selection or bootstrap is executed here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import statistics
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_SHA256 = "8116ed245ab2fe612818d19a50493d75ad47e080d69d3ef57de0597d47abe090"
ARCHIVES = {
    "fresh": ("advanced_fresh_v04_001", "4bbddde5655edf06b6959ada796166ff44b909e8bec9f8d5383e1796cdab7828"),
    "public": ("advanced_public_v04_001", "b37999eb75b52a12da80ae071984791e37bff54a8351c836fc4ac7a800e29050"),
}
AUDIT_SHA256 = {
    "fresh": "19bb6f6b751cff3aa9f13fe341febe6fdbf87e4a29c41726f3561219526e417a",
    "public": "3a322f0181c7377ba021b5f07c3346e53dfacbff37bb2696da6d0c8fba9e3c19",
}
POPULATIONS = (
    ("fresh", "standard", "Standard", 216),
    ("fresh", "dense_long", "Dense/long", 216),
    ("fresh", "c3", "C3", 24),
    ("public", "DIMACS/unit", "DIMACS unit", 18),
    ("public", "DIMACS/hash_weighted", "DIMACS hash", 18),
    ("public", "SATLIB/unit", "SATLIB unit", 30),
    ("public", "SATLIB/hash_weighted", "SATLIB hash", 30),
)
PUBLISHED = ("CHILS", "CHILS_ILS", "M2WIS", "Struction", "WeightedBR")
CLASSICAL = ("baseline_weight", "baseline_degree", "baseline_weighted_conflict", "baseline_v02_joint", "baseline_structural_ratio")
MAIN_METHODS = (
    ("CHILS", "CHILS", r"CHILS~\cite{grossmann2025chils}"),
    ("CHILS_ILS", "CHILS-ILS", r"CHILS-ILS~\cite{grossmann2025chils}"),
    ("M2WIS", "M2WIS", r"M$^2$WIS~\cite{grossmann2024mmwis}"),
    ("Struction", "Struction", r"Struction~\cite{gellner2021struction}"),
    ("WeightedBR", "WeightedBR", r"WeightedBR~\cite{lamm2019weighted}"),
    ("HiGHS_MILP", "HiGHS MILP", r"HiGHS MILP~\cite{huangfu2018highs}"),
    ("baseline_degree", "Degree", "Degree"),
    ("rule_v03", "Rule-only synthesis", "Rule-only synthesis"),
    ("free_v03", "Free synthesis", "Free synthesis"),
    ("enumerated_v03", "Enumeration", "Enumeration"),
    ("fixed_classical_1to2_search", "Classical exchange", "Classical exchange"),
    ("guided_v04", "Guided primary", r"\textbf{Guided primary}"),
)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def close(actual, expected, name):
    check(actual is not None and expected is not None and abs(actual - expected) < 1e-10,
          f"Saved summary mismatch for {name}: {actual!r} != {expected!r}")


def read_member(tar, stem, name):
    member = tar.getmember(stem + "/" + name)
    check(member.isfile(), f"Nonregular member: {member.name}")
    return tar.extractfile(member).read()


def population(context, record, dataset):
    family = context["family"]
    if dataset == "public":
        mode = record["source"]["weight_mode"]
        check(family in ("DIMACS", "SATLIB") and mode in ("unit", "hash_weighted"), "Unknown public population")
        return family + "/" + mode
    if family.startswith(("standard_", "temporal_")):
        return "standard"
    if family.startswith("dense_long_"):
        return "dense_long"
    check(family.lower() == "c3", f"Unknown fresh population: {family}")
    return "c3"


def archive_rows(dataset, directory, summary):
    stem, pinned = ARCHIVES[dataset]
    path = directory / (stem + ".tar.gz")
    check(digest(path) == pinned == summary[dataset]["source"]["sha256"], f"Archive identity mismatch: {path}")
    grouped = defaultdict(lambda: defaultdict(list))
    ids, sources = set(), {}
    with tarfile.open(path, "r:gz") as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        check(len(names) == len(set(names)), "Duplicate archive member")
        for member in members:
            name = PurePosixPath(member.name)
            check(not name.is_absolute() and ".." not in name.parts and "\\" not in member.name
                  and ":" not in member.name and (member.isfile() or member.isdir()), "Unsafe archive member")
        raw = {name: read_member(tar, stem, name) for name in
               ("data.json", "results.jsonl", "complete.json", "execution.json", "frozen_programs.json", "original_config.json")}
        hashes = {name: sha256(value).hexdigest() for name, value in raw.items()}
        complete, execution = json.loads(raw["complete.json"]), json.loads(raw["execution.json"])
        phase = complete["phases"][0]
        check(complete["execution_complete"] is True and complete["selection_permitted"] is False,
              "Archive is incomplete or permits selection")
        check(phase["execution_complete"] is True and phase["results_sha256"] == hashes["results.jsonl"], "Short-results hash/completion mismatch")
        check(execution["selection_permitted"] is False and execution["data_sha256"] == hashes["data.json"]
              and execution["frozen_sha256"] == hashes["frozen_programs.json"]
              and execution["config_sha256"] == hashes["original_config.json"], "Executed input/freeze/config mismatch")
        check(execution["programme_backend"] == "schedule_compiled(score_slice=True)", "Wrong frozen backend")
        data = json.loads(raw["data.json"])
        records = {p["id"]: p for p in data["public" if dataset == "public" else "test"]}
        method_frame = None
        for line in raw["results.jsonl"].splitlines():
            if not line:
                continue
            context = json.loads(line)
            check(context["id"] not in ids and context["selection_permitted"] is False, "Duplicate context/selection changed")
            ids.add(context["id"])
            check(context["phase"]["name"] == "short_5s", "Long-budget rows cannot enter short table")
            group = population(context, records[context["pair_id"]], dataset)
            by_method = defaultdict(list)
            for run in context["methods"]:
                by_method[run["method"]].append(run)
                check(run["completed"] == (run.get("value") is not None), "Failure/value mismatch")
                check(not run.get("fallback_used", False), "Fallback result cannot enter comparison")
                if run["completed"]:
                    check(run["feasible"] is True and run.get("value_exact") is not None, "Unverified completed reward")
            if method_frame is None:
                method_frame = set(by_method)
            check(set(by_method) == method_frame, "Different method assignment frame")
            check(all(name in by_method and len(by_method[name]) == 1 for name in CLASSICAL), "Classical initializer frame mismatch")
            best = Fraction(context["reference"]["best_verified_lower_exact"])
            check(best >= 0, "Negative reference")
            local = by_method["fixed_classical_1to2_search"][0]
            initializer_times = [by_method[name][0].get("seconds") for name in CLASSICAL]
            for name, runs in by_method.items():
                if name in PUBLISHED:
                    check(sorted(r["seed"] for r in runs) == [1, 2, 3]
                          and all(r["kind"] == "published" for r in runs), "Native seed/kind mismatch")
                else:
                    check(len(runs) == 1, "Constructive method repeated unexpectedly")
                rewards = [Fraction(r["value_exact"]) if r["completed"] else Fraction(0) for r in runs]
                check(all(0 <= value <= best for value in rewards), "Reward outside verified feasible reference")
                mean_reward = sum(rewards, Fraction(0)) / len(runs)
                coverage = Fraction(sum(r["completed"] for r in runs), len(runs))
                ratio = mean_reward / best if best else coverage
                times = [r.get("seconds") for r in runs]
                wall = statistics.fmean(times) if all(t is not None for t in times) else None
                standalone = wall
                if name == "fixed_classical_1to2_search":
                    standalone = sum(initializer_times) + local["seconds"] if all(t is not None for t in initializer_times) and local.get("seconds") is not None else None
                saved = context.get("method_summary", {}).get(name)
                if saved:
                    close(float(mean_reward), saved["primary_reward_mean_zero_accounted"], f"{context['id']}/{name}/seed mean")
                grouped[group][name].append({"context_id": context["id"], "quality_exact": str(ratio),
                    "quality": float(ratio), "completed": sum(r["completed"] for r in runs),
                    "requested": len(runs), "wall": wall, "standalone_wall": standalone})
        check(len(ids) == phase["processed_contexts"] == phase["requested_contexts"], "Not all assigned contexts recorded")
        sources = {"archive": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                   "archive_sha256": pinned, "member_sha256": hashes, "executables": execution["executables"],
                   "executed_source_sha256": execution["source_sha256"], "budget_scope": execution["budget_scope"]}
    return grouped, sources


def summarize(dataset, rows, saved):
    result = {}
    groups = {g["population"]: g for g in saved[dataset]["short"]["groups"]}
    for name, methods in rows.items():
        group = groups[name]
        result[name] = {"contexts": group["contexts"], "methods": {}}
        for method, values in methods.items():
            expected = group["methods"][method]
            check(len(values) == group["contexts"] == expected["assigned_contexts"], "Context denominator mismatch")
            total = sum((Fraction(r["quality_exact"]) for r in values), Fraction(0)) / len(values)
            requested, completed = sum(r["requested"] for r in values), sum(r["completed"] for r in values)
            check((requested, completed) == (expected["requested_runs"], expected["completed_runs"]), "Completion count mismatch")
            close(float(total), expected["competitive_ratio_failure_zero"]["estimate"], f"{name}/{method}/quality")
            close(completed / requested, expected["completion_rate"]["estimate"], f"{name}/{method}/coverage")
            times, standalone = [r["wall"] for r in values], [r["standalone_wall"] for r in values]
            median = statistics.median(times) if all(t is not None for t in times) else None
            if median is None:
                check(expected["median_wall_seconds_all_assigned"] is None, "Missing-time policy mismatch")
            else:
                close(median, expected["median_wall_seconds_all_assigned"], f"{name}/{method}/elapsed")
            standalone_median = statistics.median(standalone) if all(t is not None for t in standalone) else None
            result[name]["methods"][method] = {"competitive_reward_ratio_exact": str(total),
                "competitive_reward_pct": 100 * float(total), "completed_runs": completed,
                "requested_runs": requested, "coverage_pct": 100 * completed / requested,
                "median_wall_seconds_all_assigned": median, "median_standalone_wall_seconds_all_assigned": standalone_median,
                "quality_source_cluster_interval": expected["competitive_ratio_failure_zero"],
                "context_statistics": values}
        deltas = {}
        for method in methods:
            if method == "guided_v04":
                continue
            primary = {r["context_id"]: Fraction(r["quality_exact"]) for r in methods["guided_v04"]}
            differences = [primary[r["context_id"]] - Fraction(r["quality_exact"]) for r in methods[method]]
            mean = sum(differences, Fraction(0)) / len(differences)
            interval = group["paired_competitive_quality_differences"]["guided_minus_" + method]
            close(float(mean), interval["estimate"], f"{name}/{method}/paired difference")
            deltas[method] = {"percentage_points": 100 * float(mean), "source_cluster_interval": interval}
        result[name]["guided_minus_control"] = deltas
    return result


def coverage_text(value):
    return "100" if value["completed_runs"] == value["requested_runs"] else f"{value['coverage_pct']:.1f}"


def render_tex(result):
    headers = [r"\shortstack{Standard\\216}", r"\shortstack{Dense/long\\216}", r"\shortstack{C3\\24}",
               r"\shortstack{DIMACS\\unit: 18}", r"\shortstack{DIMACS\\hash: 18}",
               r"\shortstack{SATLIB\\unit: 30}", r"\shortstack{SATLIB\\hash: 30}"]
    lines = ["% Generated from immutable observations by scripts/build_baseline_table_v05.py.",
             r"\begin{table*}[t]", r"\centering",
             r"\caption{Executed baselines on seven separate populations. Upper panel: failure-zero competitive reward \%, with completed-run \% in parentheses. Lower panel: median elapsed seconds, including all five initializers for classical exchange. Native quality/time average three seeds within each context; budgets are distinct.}",
             r"\label{tab:baseline-v05}", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{lrrrrrrr}", r"\toprule", "Method & " + " & ".join(headers) + r" \\",
             r"\midrule", r"\multicolumn{8}{l}{\textit{Competitive reward (run coverage), both \%}} \\"]
    for method, _, label in MAIN_METHODS:
        cells = [f"{result[group]['methods'][method]['competitive_reward_pct']:.2f} ({coverage_text(result[group]['methods'][method])})" for _, group, _, _ in POPULATIONS]
        lines.append(label + " & " + " & ".join(cells) + r" \\")
    lines.extend([r"\midrule", r"\multicolumn{8}{l}{\textit{Median all-assigned elapsed time (seconds)}} \\"])
    for method, _, label in MAIN_METHODS:
        cells = []
        for _, group, _, _ in POPULATIONS:
            time = result[group]["methods"][method]["median_standalone_wall_seconds_all_assigned"]
            cells.append("--" if time is None else f"{time:.3f}")
        lines.append(label + " & " + " & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""])
    return "\n".join(lines)


def render_md(payload):
    result = payload["populations"]
    lines = ["# Executed v04 baseline comparison for the v05 presentation", "",
             "No new experiments, programme selection, solver calls or model calls were performed. All point values below are independently recomputed from the two immutable short-budget archives with exact Fraction rewards and reconciled with the saved v04 summary and independent archive audits. The standalone exchange cost is independently recomputed and checked against the archived audit. Long-budget subsets, SNAP and later heap extensions do not enter these seven columns.", "",
             "Competitive reward is the equal-context mean of reward divided by the strongest saved verified feasible witness. Native seeds 1/2/3 are averaged within a context, with failure reward zero; they are not independent graph samples. Coverage is completed/requested method runs. A 100% ratio is not a proof of optimality. Source-cluster intervals are retained from the independently audited v04 summary after checking their point estimates; this builder does not recompute the bootstrap.", "",
             "The main table uses twelve methods. Full numerical controls below retain all twenty-three actually executed method IDs. Free/rule-only synthesis are project controls, not implementations of EoH or ReEvo. CHILS-ILS is the executed one-population ILS setting of the published CHILS implementation, not another independently published algorithm.", "",
             "Elapsed time is a context median; published-method context times first average all three seed times. These are not summed seed costs. Classical exchange times include all five assigned classical initializers, including failed attempts, plus exchange search. Missing times remain unavailable. Constructive policies have a five-process-CPU-second cooperative target, native solvers a five-second native limit plus hard wall, HiGHS ten seconds, and exchange two seconds after initialization. Total computation is unmatched.", "",
             "HiGHS MILP cites Huangfu and Hall (2018), *Parallelizing the dual revised simplex method*, Mathematical Programming Computation 10(1):119–142, DOI 10.1007/s12532-017-0130-5, using `huangfu2018highs`. This is the [official HiGHS academic acknowledgment recommendation](https://highs.dev/#background), independently checked on 2026-10-03 and linked to the [publisher record](https://link.springer.com/article/10.1007/s12532-017-0130-5). It acknowledges the executed software; the article concerns dual revised simplex and is not represented as a separate MILP-specific algorithm publication.", ""]
    for dataset, group, label, _ in POPULATIONS:
        lines.extend([f"## {label}", "", "| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |", "|---|---:|---:|---:|"])
        for method, value in result[group]["methods"].items():
            ci = value["quality_source_cluster_interval"]
            time = value["median_standalone_wall_seconds_all_assigned"]
            lines.append(f"| {method} | {value['competitive_reward_pct']:.5f} [{100*ci['lower']:.5f}, {100*ci['upper']:.5f}] | {value['completed_runs']}/{value['requested_runs']} | {'unavailable' if time is None else f'{time:.6f}'} |")
        lines.append("")
    lines.extend(["## What the LLM comparison supports", "",
                  "The frozen structural primary improves Degree by 0.984 and 1.645 percentage points on standard and dense/long scheduling, with positive paired source-cluster intervals. It improves the rule-only control by 0.536 and 1.589 points there. Free synthesis has higher standard/dense point means by 0.075/0.166 points; both primary-minus-Free intervals cross zero. C3 primary-minus-Free is +0.175 points [0.036, 0.346], whereas primary-minus-Degree and primary-minus-rule intervals cross zero. This is mixed selected-program evidence, not a general model-level advantage.", "",
                  "Published implementations and the classical exchange control exceed the primary on fresh reward. Public failures further limit transfer. Unequal proposal counts (12 guided versus 24 historical controls), one continuing guided authoring session, unavailable token costs, changed evidence and unmatched computation prevent causal attribution to LLM guidance. The actual-regret tie-break selected the same AST as the primary-only ablation. Representation refinement, structural scoring and pure execution optimizations have their own evidence; they do not establish LLM superiority.", "",
                  "Missing evidence: matched-budget repeated authoring sessions; a controlled guidance-versus-no-guidance experiment with identical proposal/checking compute; canonical executed EoH/ReEvo comparisons; and actual native anytime trajectories. Frozen rollout prefixes are construction progress, not CPU-time progress or an LLM learning curve.", "", "## Immutable sources", ""])
    for name, source in payload["sources"].items():
        lines.extend([f"- {name}: `{source['path']}` — SHA256 `{source['sha256']}`"])
    lines.extend(["", "The JSON includes exact ratios, context-level denominators, all elapsed values, member/source/executable receipts and the saved interval definitions. Main-table decimal rounding does not change the underlying values.", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=ROOT / "experiments/analysis/v04/summary.json")
    parser.add_argument("--archives", type=Path, default=ROOT / "experiments/runs/v04")
    parser.add_argument("--tex", type=Path, default=ROOT / "paper/generated/baseline_table_v05.tex")
    parser.add_argument("--json", type=Path, default=ROOT / "experiments/analysis/v05/baseline_table_v05.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/BASELINE_COMPARISON_V05.md")
    args = parser.parse_args(argv)
    check(digest(args.summary) == SUMMARY_SHA256, "Reviewed v04 summary bytes changed")
    saved = json.loads(args.summary.read_text(encoding="utf-8"))
    result, source_details = {}, {}
    for dataset in ARCHIVES:
        raw, provenance = archive_rows(dataset, args.archives.resolve(), saved)
        result.update(summarize(dataset, raw, saved))
        source_details[dataset] = provenance
    audit_sources = {}
    for dataset in ARCHIVES:
        path = ROOT / "experiments/analysis/v04" / ("advanced_" + dataset + "_audit.json")
        check(digest(path) == AUDIT_SHA256[dataset], "Independent audit bytes changed")
        audit = json.loads(path.read_text(encoding="utf-8"))
        check(audit["archive_sha256"] == ARCHIVES[dataset][1], "Independent audit archive mismatch")
        for group, data in audit["phases"]["results.jsonl"]["groups"].items():
            for method, value in data["methods"].items():
                calculated = result[group]["methods"][method]
                close(calculated["competitive_reward_pct"] / 100, value["competitive"]["estimate"], f"audit/{group}/{method}/quality")
                check(calculated["completed_runs"] == value["completed_runs"] and calculated["requested_runs"] == value["requested_runs"], "Audit denominator mismatch")
            local = data["methods"]["fixed_classical_1to2_search"]
            close(result[group]["methods"]["fixed_classical_1to2_search"]["median_standalone_wall_seconds_all_assigned"], local["median_classical_initializers_plus_search_wall"], f"audit/{group}/standalone exchange time")
        audit_sources[dataset + "_audit"] = {"path": path.relative_to(ROOT).as_posix(), "sha256": AUDIT_SHA256[dataset]}
    for _, name, _, count in POPULATIONS:
        check(result[name]["contexts"] == count, "Population count mismatch")
    payload = {"version": "v05_presentation_of_frozen_v04_observations", "no_new_experiments": True,
               "selection_permitted": False, "main_method_ids": [m[0] for m in MAIN_METHODS],
               "population_order": [p[1] for p in POPULATIONS], "populations": result,
               "sources": {"summary": {"path": args.summary.relative_to(ROOT).as_posix() if args.summary.is_relative_to(ROOT) else str(args.summary), "sha256": SUMMARY_SHA256},
                           **{dataset: {"path": p["archive"], "sha256": p["archive_sha256"]} for dataset, p in source_details.items()}, **audit_sources},
               "archive_receipts": source_details,
               "scope": "Independent exact point recomputation and reconciliation; saved source-cluster intervals; no new bootstrap or independent physical-source/solver audit"}
    tex = render_tex(result)
    for path, content in ((args.tex, tex), (args.json, json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"), (args.markdown, render_md(payload))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(json.dumps({"populations": len(result), "main_methods": len(MAIN_METHODS), "all_methods_per_population": sorted({len(g['methods']) for g in result.values()}), "source_hashes": payload["sources"], "tex": str(args.tex)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
