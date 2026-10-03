"""Immutable TRAIN cancellation audit and completed v04 solver comparisons.

Use --fresh-archive/--public-archive only for completed advanced_study_v04 archives.
Without them, publish the real TRAIN audit and the input inventory; no held-out
outcome is invented. Native solvers use the mean of seeds 1/2/3, including zeros
for failure, with context-level source clustering rather than seed replication.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import statistics
import tarfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from build_result_figures_v03 import style, save, BLUE, ORANGE, GRAY, INK, PURPLE, SEED, REPLICATIONS

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments/runs/v04"
OUT = ROOT / "experiments/analysis/v04"
SOLVERS = ("CHILS", "M2WIS", "Struction", "WeightedBR")
DISPLAY = [
    ("guided_v04", "Frozen joint program", PURPLE, "o"),
    ("CHILS_ILS", "CHILS: short-budget ILS", BLUE, "s"),
    ("CHILS", "CHILS: concurrent", GRAY, "^"),
    ("M2WIS", r"M$^2$WIS", "#9A8667", "D"),
    ("Struction", "Struction", "#719477", "v"),
    ("WeightedBR", "Weighted branch-reduce", "#8A8EA3", "P"),
    ("HiGHS_MILP", "HiGHS (10 s)", ORANGE, "X"),
]


def read_archive(path):
    path = Path(path)
    contents = {}
    hashes = {}
    with tarfile.open(path) as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith((".json", ".jsonl")):
                continue
            key = Path(member.name).name
            if key in contents:
                raise ValueError(f"Ambiguous duplicate archive basename: {key}")
            raw = tar.extractfile(member).read().decode("utf-8")
            hashes[key] = sha256(raw.encode("utf-8")).hexdigest()
            contents[key] = ([json.loads(line) for line in raw.splitlines() if line]
                             if key.endswith(".jsonl") else json.loads(raw))
    try:
        relative = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        relative = str(path.resolve())
    contents["_source"] = {"path": relative, "sha256": sha256(path.read_bytes()).hexdigest()}
    contents["_member_sha256"] = hashes
    return contents


def identity(family, cluster):
    if family.startswith(("standard_", "temporal_")):
        return "standard", str(cluster)
    if family.startswith("dense_long_"):
        return "dense_long", str(cluster)
    if family.lower() == "c3":
        return "c3", str(cluster)
    return family, str(cluster)


def interval(rows, key):
    """Mean CI on the full assigned context frame; None is conditional missing."""
    blocks = defaultdict(lambda: defaultdict(list))
    for row in rows:
        blocks[row["stratum"]][row["cluster"]].append(row[key])
    observed = [r[key] for r in rows if r[key] is not None]
    if not observed:
        return None
    rng = np.random.default_rng(SEED)
    sums, counts = np.zeros(REPLICATIONS), np.zeros(REPLICATIONS)
    cluster_counts = {}
    for stratum, groups in sorted(blocks.items()):
        arrays = [[v for v in values if v is not None] for _, values in sorted(groups.items())]
        cluster_counts[stratum] = len(arrays)
        draws = rng.integers(0, len(arrays), size=(REPLICATIONS, len(arrays)))
        sums += np.asarray([sum(a) for a in arrays])[draws].sum(axis=1)
        counts += np.asarray([len(a) for a in arrays])[draws].sum(axis=1)
    estimates = sums[counts > 0] / counts[counts > 0]
    lo, hi = np.quantile(estimates, [.025, .975])
    return {"estimate": statistics.fmean(observed), "lower": float(lo), "upper": float(hi),
            "level": .95, "replications": REPLICATIONS, "seed": SEED,
            "assigned_contexts": len(rows), "finite_contexts": len(observed),
            "source_clusters": cluster_counts, "method": "stratified_source_cluster_percentile_bootstrap"}


def cancellation_summary():
    path = OUT / "pure_cancellation_training.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    train = read_archive(RUNS / "relevance_train_v04_001.tar.gz")
    pairs = {p["id"]: p for p in train["data.json"]["train"]}
    rows = []
    for row in data["comparisons"]:
        p = pairs[row["pair_id"]]
        cluster = p.get("source", {}).get("seed")
        stratum, cluster = identity(p["family"], cluster if cluster is not None else p["id"])
        lo, hi, ulo, uhi = (Fraction(row[k]) for k in ["cancelled_lower_exact", "cancelled_upper_exact",
                                            "uncancelled_same_bounds_lower_exact", "uncancelled_same_bounds_upper_exact"])
        assert ulo <= lo <= hi <= uhi
        assert not row["unmatched_bounds_reoptimized"]
        rows.append({**row, "stratum": stratum, "cluster": cluster,
                     "cancelled_width": float(hi-lo), "uncancelled_width": float(uhi-ulo),
                     "width_reduction": float((uhi-ulo)-(hi-lo)), "exact_tie": lo == hi == 0})
    s = data["summary"]
    assert len(rows) == s["comparisons"] == 396
    assert sum(r["width_reduction"] > 0 for r in rows) == s["width_reductions"] == 199
    assert sum(r["cancelled_strict"] for r in rows) == sum(r["uncancelled_strict"] for r in rows) == 33
    return {"scope": s["scope"], "source": {"path": path.relative_to(ROOT).as_posix(),
             "sha256": sha256(path.read_bytes()).hexdigest()}, "train_source": train["_source"],
            "comparison_count": len(rows), "strictly_narrower": 199, "nested": len(rows),
            "uncancelled_strict": 33, "cancelled_strict": 33, "strict_gains": 0, "strict_losses": 0,
            "exact_ties": sum(r["exact_tie"] for r in rows), "unresolved": s["cancelled_unresolved"],
            "median_uncancelled_width": statistics.median(r["uncancelled_width"] for r in rows),
            "median_cancelled_width": statistics.median(r["cancelled_width"] for r in rows),
            "mean_paired_width_reduction": interval(rows, "width_reduction"),
            "cost_scope": "offline audit only; zero search expansion, common membership work/wall from source summary",
            "audit_cost": {k: s[k] for k in ("new_search_expanded_nodes", "common_membership_check_units", "common_wall_seconds")},
            "strategy_contrast": {"whole_residual_strict": 10, "component_cancelled_strict": 33,
                "scope": "distinct bounding strategies; not isolated cancellation yield"},
            "rows": rows}


def input_inventory():
    out = {}
    for name in ("fresh_data_v04_002", "public_data_v04_002"):
        data = read_archive(RUNS / (name+".tar.gz"))
        if "public" in data["data.json"]:
            records = data["data.json"]["public"]
            counts = Counter((p["family"], p["source"]["weight_mode"]) for p in records)
            out["public"] = {"source": data["_source"], "assigned_contexts": len(records),
                             "populations": {f"{f}/{w}": n for (f, w), n in counts.items()}}
        else:
            records = data["data.json"]["test"]
            out["fresh"] = {"source": data["_source"], "assigned_contexts": 2*len(records),
                            "populations": {k: 2*v for k, v in Counter(p["family"] for p in records).items()}}
    return out


def population_groups(rows, dataset):
    if dataset == "fresh":
        return [(name, [r for r in rows if r["stratum"] == name]) for name in ("standard", "dense_long", "c3")]
    if dataset == "sparse":
        return [("SNAP/"+weight,[r for r in rows if r["weight_mode"] == weight])
                for weight in ("unit","hash_weighted")]
    return [(f"{family}/{weight}", [r for r in rows if r["family"] == family and r["weight_mode"] == weight])
            for family in ("DIMACS", "SATLIB") for weight in ("unit", "hash_weighted")]


def phase_summary(archive, filename, dataset):
    contexts = archive[filename+".jsonl"]
    phase = next(p for p in archive["complete.json"]["phases"] if
                 p["phase"]["name"] == contexts[0]["phase"]["name"])
    assert phase["execution_complete"] and len(contexts) == phase["requested_contexts"]
    assert len({c["id"] for c in contexts}) == len(contexts)
    assert archive["execution.json"]["selection_permitted"] is False
    data = archive["data.json"]
    records = {p["id"]: p for p in data.get("public", data.get("test", []))}
    flat, parity = [], defaultdict(list)
    for c in contexts:
        p = records[c["pair_id"]]
        stratum, cluster = identity(c["family"], c["cluster"])
        weight = p.get("source", {}).get("weight_mode")
        upper = c["reference"].get("formal_upper_exact")
        lower = c["reference"].get("best_verified_lower_exact")
        formal = Fraction(upper) if upper is not None else None
        best = Fraction(lower) if lower is not None else None
        by_method = defaultdict(list)
        for m in c["methods"]:
            assert m["completed"] == (m.get("value") is not None)
            if m["completed"]:
                assert m["feasible"] is True and m.get("value_exact") is not None
            by_method[m["method"]].append(m)
        for method, runs in by_method.items():
            if runs[0]["kind"] == "published":
                assert sorted(m["seed"] for m in runs) == [1, 2, 3]
            else:
                assert len(runs) == 1
            values = [Fraction(m["value_exact"]) if m["completed"] else Fraction(0) for m in runs]
            completed = [m for m in runs if m["completed"]]
            mean = sum(values) / len(values)
            completed_mean = sum(Fraction(m["value_exact"]) for m in completed)/len(completed) if completed else None
            formal_ratio = float(mean/formal) if formal and formal > 0 else (len(completed)/len(runs) if formal == 0 else None)
            competitive_ratio = float(mean/best) if best and best > 0 else (len(completed)/len(runs) if best == 0 else (0.0 if not completed else None))
            saved = c.get("method_summary", {}).get(method)
            if saved:
                assert abs(saved["primary_reward_mean_zero_accounted"]-float(mean)) < 1e-7
            flat.append({"id": c["id"], "pair_id": c["pair_id"], "side": c["side"], "family": c["family"],
                "stratum": stratum, "cluster": cluster, "weight_mode": weight, "n": c.get("n"), "method": method,
                "requested_runs": len(runs), "completed_runs": len(completed), "failure_runs": len(runs)-len(completed),
                "complete_context": len(completed) == len(runs), "coverage": len(completed)/len(runs),
                "reward_zero": float(mean), "reward_completed": float(completed_mean) if completed_mean is not None else None,
                "quality_formal": formal_ratio, "quality_competitive": competitive_ratio,
                "quality_formal_completed": float(completed_mean/formal) if completed_mean is not None and formal and formal > 0 else None,
                "wall_seconds": statistics.fmean(m["seconds"] for m in runs) if all(m.get("seconds") is not None for m in runs) else None,
                "cpu_seconds": statistics.fmean(m["cpu_seconds"] for m in runs) if all(m.get("cpu_seconds") is not None for m in runs) else None,
                "feature_work": statistics.fmean(m["feature_work"] for m in runs) if all(m.get("feature_work") is not None for m in runs) else None})
        for method, receipt in c.get("full_interface_parity", {}).items():
            parity[method].append(receipt)
    groups = []
    # No combined public/private mean, and no standard/dense/C3 outcome pooling.
    for population, rows in population_groups(flat, dataset):
        if not rows:
            continue
        methods = {}
        for method in sorted({r["method"] for r in rows}):
            rs = [r for r in rows if r["method"] == method]
            methods[method] = {"assigned_contexts": len(rs), "requested_runs": sum(r["requested_runs"] for r in rs),
                "completed_runs": sum(r["completed_runs"] for r in rs), "failed_runs": sum(r["failure_runs"] for r in rs),
                "all_seeds_completed_contexts": sum(r["complete_context"] for r in rs),
                "completion_rate": interval(rs, "coverage"), "reward_zero": interval(rs, "reward_zero"),
                "reward_completed": interval(rs, "reward_completed"),
                "formal_upper_ratio_failure_zero": interval(rs, "quality_formal"),
                "competitive_ratio_failure_zero": interval(rs, "quality_competitive"),
                "formal_upper_ratio_completed": interval(rs, "quality_formal_completed"),
                "mean_wall_seconds_all_assigned": interval(rs, "wall_seconds"),
                "median_wall_seconds_all_assigned": statistics.median(r["wall_seconds"] for r in rs) if all(r["wall_seconds"] is not None for r in rs) else None,
                "wall_cost_available_contexts": sum(r["wall_seconds"] is not None for r in rs),
                "conditional_quality_scope": "equal-context mean of the completed-seed mean; failed source clusters retained in resampling",
                "median_cpu_seconds_all_assigned": statistics.median(r["cpu_seconds"] for r in rs) if all(r["cpu_seconds"] is not None for r in rs) else None,
                "mean_feature_work_if_available": statistics.fmean(r["feature_work"] for r in rs) if all(r["feature_work"] is not None for r in rs) else None}
        indexed = {(r["id"], r["method"]): r for r in rows}
        deltas = {}
        guided = [r for r in rows if r["method"] == "guided_v04"]
        for method in methods:
            if method == "guided_v04" or not guided:
                continue
            paired = []
            for r in guided:
                other = indexed[(r["id"], method)]
                a, b = r["quality_competitive"], other["quality_competitive"]
                paired.append({**r, "difference": a-b if a is not None and b is not None else None})
            deltas["guided_minus_"+method] = interval(paired, "difference")
        groups.append({"population": population, "contexts": len({r["id"] for r in rows}), "methods": methods,
                       "paired_competitive_quality_differences": deltas})
    return {"phase": phase, "groups": groups, "formal_reference_contexts": sum(c["reference"].get("formal_upper_exact") is not None for c in contexts),
            "exactly_proved_contexts": sum(c["reference"].get("independent_exact_proof", False) for c in contexts),
            "source_verifier": dict(Counter(str(c.get("source_verifier", {}).get("status")) for c in contexts)),
            "interface_parity": {method: {"assigned": len(rs), "both_completed": sum(r["both_completed"] for r in rs),
               "completed_selection_mismatches": sum(r["selection_identical"] is False for r in rs),
               "completed_trace_mismatches": sum(r["trace_identical"] is False for r in rs),
               "completed_value_mismatches": sum(r["exact_value_identical"] is False for r in rs)} for method, rs in parity.items()}}


def completed_comparison(path, dataset, expected):
    data = read_archive(path)
    assert data["complete.json"]["execution_complete"]
    assert data["execution.json"]["programme_backend"] == "schedule_compiled(score_slice=True)"
    assert data["execution.json"]["data_sha256"] == data["_member_sha256"]["data.json"]
    assert data["execution.json"]["frozen_sha256"] == data["_member_sha256"]["frozen_programs.json"]
    assert len(data["results.jsonl"]) == expected
    result = {"source": data["_source"], "completion": data["complete.json"], "execution": data["execution.json"],
              "short": phase_summary(data, "results", dataset)}
    if "long_results.jsonl" in data:
        result["long_prespecified_subset"] = phase_summary(data, "long_results", dataset)
    return result


def cancellation_figure(summary):
    rows = summary["pure_cancellation"]["rows"]
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.6))
    fig.subplots_adjust(left=.09, right=.99, bottom=.25, top=.78, wspace=.43)
    for key, color, label in [("uncancelled_width", GRAY, "Same bounds, no cancellation"),
                               ("cancelled_width", BLUE, "Common components cancelled")]:
        x = np.sort([r[key] for r in rows]); y = np.arange(1, len(x)+1)/len(x)
        axes[0].step(x, y, where="post", color=color, lw=1.6, label=label)
    axes[0].set_xscale("symlog", linthresh=1); axes[0].set_ylim(0, 1.02)
    axes[0].set_ylabel("TRAIN comparisons (fraction)")
    axes[0].set_xlabel("Exact difference-interval width")
    axes[0].set_title("(a) Paired uncertainty distribution", loc="left", fontweight="bold")
    x = [r["uncancelled_width"] for r in rows]; y = [r["cancelled_width"] for r in rows]
    axes[1].scatter(x, y, c=[BLUE if r["width_reduction"] > 0 else GRAY for r in rows], s=12, alpha=.65, edgecolors="none")
    limit = max(x)*1.1
    axes[1].plot([0, limit], [0, limit], color=GRAY, ls="--", lw=.8)
    axes[1].set_xscale("symlog", linthresh=1); axes[1].set_yscale("symlog", linthresh=1)
    axes[1].set_xlabel("Width without cancellation"); axes[1].set_ylabel("Width after cancellation")
    axes[1].set_title("(b) All 396 intervals are nested", loc="left", fontweight="bold")
    for ax in axes:
        ax.grid(alpha=.15)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, frameon=False)
    fig.text(.5, .02, "199 narrower; median 86.75 → 36; strict certificates 33 → 33 (no gains or losses)", ha="center", fontsize=9)
    save(fig, "cancellation_uncertainty_v04")


def comparison_figure(result, dataset):
    groups = result["short"]["groups"]
    fig, axes = plt.subplots(1, len(groups), figsize=(7, 2.85), squeeze=False)
    fig.subplots_adjust(left=.085, right=.99, bottom=.25, top=.64, wspace=.38)
    lows = [100*g['methods'][a]['competitive_ratio_failure_zero']['lower']
            for g in groups for a,_,_,_ in DISPLAY if a in g['methods']
            and g['methods'][a]['competitive_ratio_failure_zero']]
    floor = max(0, 5*np.floor((min(lows)-1)/5)) if lows else 0
    for i, group in enumerate(groups):
        ax = axes[0, i]
        for arm, label, color, marker in DISPLAY:
            if arm not in group["methods"]:
                continue
            m = group["methods"][arm]
            ci = m["competitive_ratio_failure_zero"]
            if ci is None:
                continue
            y, lo, hi = [100*ci[k] for k in ("estimate", "lower", "upper")]
            x = m["median_wall_seconds_all_assigned"]
            if x is None or x <= 0:
                continue
            ax.errorbar(x, y, yerr=[[y-lo], [hi-y]], marker=marker, ms=4.5, lw=1,
                        color=color, capsize=2, ls="none", label=label)
        ax.set_xscale("log"); ax.set_xlabel("Median elapsed wall (s)")
        names = {"standard":"Standard", "dense_long":"Dense / long", "c3":"C3 contacts"}
        title = names.get(group['population'], group['population'].replace('/hash_weighted',' / W').replace('/unit',' / U').replace('SNAP/','SNAP / '))
        ax.set_title(title+f"\n{group['contexts']} contexts", loc="left", fontweight="bold", fontsize=9)
        ax.set_ylim(floor, 100.7); ax.grid(alpha=.15)
        ax.minorticks_off()
    axes[0, 0].set_ylabel("Reward / best verified feasible (%)")
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="upper center", ncol=3, frameon=False,
               columnspacing=1.1, handletextpad=.4)
    fig.text(.5, .015, "Failure reward = 0; native mean of 3 seeds; distinct budgets; 95% source-cluster CIs", ha="center", fontsize=9)
    save(fig, f"quality_cost_{dataset}_v04")


def coverage_figure(result, dataset):
    groups = result["short"]["groups"]
    fig, axes = plt.subplots(1, len(groups), figsize=(7, 1.95), sharey=True, squeeze=False)
    fig.subplots_adjust(left=.19, right=.99, bottom=.30, top=.79, wspace=.28)
    shown = [(a,l,c) for a,l,c,_ in DISPLAY if all(a in g["methods"] for g in groups)]
    for i, group in enumerate(groups):
        ax = axes[0, i]
        for y, (arm, label, color) in zip(range(len(shown)-1, -1, -1), shown):
            ci = group["methods"][arm]["completion_rate"]
            x, lo, hi = [100*ci[k] for k in ("estimate", "lower", "upper")]
            ax.errorbar(x, y, xerr=[[x-lo], [hi-x]], color=color, marker="o", ms=4,
                        ls="none", capsize=2, lw=1)
        ax.set_xlim(-3, 103); ax.set_xticks([0, 50, 100]); ax.set_ylim(-.6, len(shown)-.4)
        ax.set_title(group["population"].replace("/", "\n"), loc="left", fontweight="bold")
        ax.set_xlabel("Completed runs (%)"); ax.grid(axis="x", alpha=.15)
        ax.set_yticks(range(len(shown)-1, -1, -1), [l for _,l,_ in shown])
    save(fig, f"coverage_{dataset}_v04")


def combined_quality_figure(summary):
    """Full-width source-backed comparison, with explicit unequal ordinate ranges."""
    fig = plt.figure(figsize=(7,3.95))
    grid = fig.add_gridspec(2,12,left=.09,right=.99,bottom=.17,top=.74,
                           hspace=.95,wspace=1.20)
    handles = None
    for row,dataset,step in [(0,'fresh',4),(1,'public',3)]:
        groups = summary[dataset]['short']['groups']
        for i,g in enumerate(groups):
            ax = fig.add_subplot(grid[row,i*step:(i+1)*step])
            for arm,label,color,marker in DISPLAY:
                m = g['methods'][arm]
                ci = m['competitive_ratio_failure_zero']
                if ci is None: continue
                y,lo,hi = [100*ci[k] for k in ('estimate','lower','upper')]
                x = m['median_wall_seconds_all_assigned']
                if x is None or x<=0: continue
                ax.errorbar(x,y,yerr=[[y-lo],[hi-y]],marker=marker,ms=4.5,lw=1,
                            color=color,capsize=2,ls='none',label=label)
            if handles is None: handles = ax.get_legend_handles_labels()
            if dataset=='fresh':
                names = {'standard':'Standard','dense_long':'Dense / long','c3':'C3 contacts'}
                title = names[g['population']]+f" ({g['contexts']})"
                ax.set_ylim(90,100.7);ax.set_yticks([90,95,100])
            else:
                family,mode = g['population'].split('/')
                title = family+' '+('U' if mode=='unit' else 'W')+f" ({g['contexts']})"
                ax.set_ylim(0,100.7);ax.set_yticks([0,50,100])
            ax.set_title(title,loc='left',fontweight='bold',fontsize=9)
            ax.set_xscale('log');ax.minorticks_off();ax.grid(alpha=.15)
            if i==0: ax.set_ylabel('Competitive reward (%)')
    fig.legend(*handles,loc='upper center',ncol=3,frameon=False,
               columnspacing=.8,handletextpad=.3,bbox_to_anchor=(.5,1.01))
    fig.text(.09,.82,'(a) Fresh scheduling: ordinate 90–100%',fontweight='bold',fontsize=9)
    fig.text(.09,.46,'(b) Public transfer: 0–100%; U=unit, W=weighted',fontweight='bold',fontsize=9)
    fig.text(.5,.075,'Median elapsed wall (s), log scale',ha='center',fontsize=9)
    fig.text(.5,.015,'Failure = 0; native 3-seed mean; distinct budgets; 95% source-cluster CIs',ha='center',fontsize=9)
    save(fig,'quality_cost_combined_v04')


def report(summary):
    c = summary["pure_cancellation"]
    lines = ["# v04 source-backed quantitative analysis", "",
       "This analysis uses immutable archived observations. Fresh and public outcomes remain separate; public DIMACS/SATLIB and unit/hash-weighted graphs are not pooled. "
       "The four native comparators retain seeds 1, 2, 3 as a per-context mean with failure reward zero. Seeds are not treated as independent graph samples.", "",
       "## Isolated TRAIN common-component cancellation", "",
       "396 saved action comparisons use identical zero-search bounds on the unmatched components. Cancelling the common components makes all 396 intervals nested and 199 strictly narrower. "
       "Median width is 86.75 without cancellation and 36 after cancellation. Strict certificates stay 33→33, with zero gains or losses; 61 exact ties and 302 unresolved comparisons remain. "
       "The separate whole-residual-versus-component strategy comparison has 10→33 strict relations and does not isolate cancellation.", "",
       f"Mean paired width reduction: {c['mean_paired_width_reduction']['estimate']:.6f}, 95% source-cluster CI "
       f"[{c['mean_paired_width_reduction']['lower']:.6f}, {c['mean_paired_width_reduction']['upper']:.6f}]. "
       "Action comparisons sharing a TRAIN source are kept together. The figure CDF is the observed finite-bank distribution, not a confidence band.", "",
       "`cancellation_uncertainty_v04.pdf` is 7 × 2.6 inches with Arial 9 pt. Suggested caption: **Matched TRAIN cancellation audit. "
       "Each comparison keeps the same unmatched zero-search bounds. Cancelling common components narrows 199 of 396 intervals and preserves interval nesting, "
       "but the number of strict certificates remains 33. The separate whole-residual strategy comparison is not plotted.**", "",
       "## Outcome population inventory", "", "| Population | Assigned contexts |", "|---|---:|"]
    for kind, inv in summary["input_inventory"].items():
        for name, count in inv["populations"].items():
            lines.append(f"| {kind}: {name} | {count} |")
    lines += ["", "## Completed comparisons", ""]
    for dataset in ("fresh", "public", "sparse"):
        if dataset not in summary:
            lines += [f"{dataset.capitalize()} outcomes: pending a completed advanced-study archive; no outcome panel is generated.", ""]
            continue
        for phase_key in ("short", "long_prespecified_subset"):
            if phase_key not in summary[dataset]:
                continue
            lines += [f"### {dataset}: {phase_key}", "", "| Population | Method | Completed / requested runs | Failure-zero competitive ratio, % (95% CI) | Mean formal-upper ratio, % | Median wall, s |",
                "|---|---|---:|---:|---:|---:|"]
            for group in summary[dataset][phase_key]["groups"]:
                for method, m in group["methods"].items():
                    q, f = m["competitive_ratio_failure_zero"], m["formal_upper_ratio_failure_zero"]
                    qtext = f"{100*q['estimate']:.5f} [{100*q['lower']:.5f}, {100*q['upper']:.5f}]" if q else "unavailable"
                    ftext = f"{100*f['estimate']:.5f}" if f else "unavailable"
                    wall = m['median_wall_seconds_all_assigned']
                    wall_text = f"{wall:.6f}" if wall is not None else "unavailable"
                    lines.append(f"| {group['population']} | {method} | {m['completed_runs']}/{m['requested_runs']} | {qtext} | {ftext} | {wall_text} |")
    lines += ["", "Competitive normalization is descriptive reward relative to the strongest archived independently verified feasible witness in the same context. "
       "It is not a claim of optimality. Exact clique-upper ratios and reference coverage are also retained. "
       "A missing reference remains unavailable, and a failed solver remains assigned with reward zero; neither silently disappears. "
       "Wall time includes all assigned runs. Native official budgets, cooperative constructive CPU targets, MILP and local-search budgets differ. "
       "Long-budget results remain a separate prespecified subset. Full-interface parity is assessed only when both executions complete, with the unassessable count retained.", ""]
    (ROOT / "docs/RESULT_ANALYSIS_V04.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-archive", type=Path)
    parser.add_argument("--public-archive", type=Path)
    parser.add_argument("--sparse-archive", type=Path)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    summary = {"version": "v04_source_analysis", "pure_cancellation": cancellation_summary(),
               "input_inventory": input_inventory(), "seed_aggregation": "per context arithmetic mean of all native seeds 1/2/3; failure zero; never best of three",
               "selection_scope": "frozen TRAIN-only programmes; analysis never mutates programme or data"}
    for name, path, expected in [("fresh", args.fresh_archive, 456), ("public", args.public_archive, 96),
                                 ("sparse", args.sparse_archive, 8)]:
        if path:
            summary[name] = completed_comparison(path, name, expected)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    report(summary)
    if not args.no_figures:
        style(); cancellation_figure(summary)
        for dataset in ("fresh", "public", "sparse"):
            if dataset in summary:
                comparison_figure(summary[dataset], dataset)
                coverage_figure(summary[dataset], dataset)
        if 'fresh' in summary and 'public' in summary:
            combined_quality_figure(summary)
    print("Completed source-backed v04 analysis: "+", ".join(k for k in ('fresh','public','sparse') if k in summary))


if __name__ == "__main__":
    main()
