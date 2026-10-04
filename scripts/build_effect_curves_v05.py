"""Source-backed diagnostic curves for the unchanged v04 frozen programs.

The x-axis of a constructive trajectory is residual-vertex elimination, never
elapsed time: the original receipts contain no per-action CPU timestamps. No
new program selection, oracle call, or experiment is performed here. Completed
immutable receipts and graph weights supply every displayed observation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.model import Graph
from build_result_figures_v03 import BLUE, ORANGE, PURPLE, GRAY, INK, style, save
from build_result_figures_v04 import read_archive, identity, interval

OUT = ROOT / "experiments/analysis/v05"
METHODS = ("guided_v04", "baseline", "rule_v03", "free_v03")
CONTROLS = (("baseline", "Degree", GRAY, "^", "-."),
            ("rule_v03", "Rule only", BLUE, "s", "-"),
            ("free_v03", "Free synthesis", ORANGE, "o", "--"))
POPULATIONS = (("standard", "Standard", BLUE, "o", "-"),
               ("dense_long", "Dense / long", PURPLE, "s", "--"),
               ("c3", "C3 contacts", ORANGE, "^", "-."))
GRID = np.linspace(0, 1, 101)


def receipt(path):
    return {"path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path.read_bytes()).hexdigest()}


def exact_weight(graph, node):
    return Fraction(str(graph.nodes[node].weight))


def replay_prefixes(graph, context, run, denominator):
    """Check every recorded deletion/weight against the source graph independently.

    Replay uses only the saved action order and original graph; the compiled
    evaluator, learned score function, and conditional bound oracle are unused.
    """
    if not run["completed"] or run["fallback_used"]:
        raise ValueError("This complete-trace diagnostic requires a finished original run")
    active = graph.available(context["fixed"], context["excluded"])
    initial_count = len(active)
    chosen = list(context["fixed"])
    value = sum((exact_weight(graph, v) for v in chosen), Fraction())
    x, y = [0.0], [float(value / denominator)]
    checks = 0
    for entry in run["trace"]:
        node = entry["selected"]
        assert entry["remaining_count"] == len(active)
        assert node in active and node not in chosen
        assert all(node not in graph.adj[v] for v in chosen)
        chosen.append(node)
        value += exact_weight(graph, node)
        active.difference_update({node} | graph.adj[node])
        x.append(1 - len(active) / initial_count if initial_count else 1.0)
        y.append(float(value / denominator))
        checks += 3
    assert not active
    assert sorted(chosen) == sorted(run["selected"])
    assert value == Fraction(run["value_exact"])
    assert graph.feasible(chosen)
    assert all(a < b for a, b in zip(x, x[1:]))
    assert all(a <= b for a, b in zip(y, y[1:]))
    assert x[-1] == 1.0
    # Right-continuous observation on an elimination grid: no interpolation
    # across jumps, and an action is included only after its actual deletion.
    indices = np.searchsorted(np.asarray(x), GRID, side="right") - 1
    curve = np.asarray(y)[indices].tolist()
    assert curve[-1] == float(value / denominator)
    return curve, {"action_count": len(run["trace"]), "initial_active_count": initial_count,
                   "last_reward_exact": str(value), "checks": checks + 8,
                   "prefixes": [[xx, yy] for xx, yy in zip(x, y)]}


def vector_interval(rows, key):
    """Pointwise 95% source-cluster bootstrap on complete paired trajectories.

    The same draw weights apply at every progress fraction. Bands are pointwise,
    not simultaneous confidence bands, and all source sides/regimes are kept.
    """
    blocks = defaultdict(list)
    for row in rows:
        blocks[row["cluster"]].append(row[key])
    arrays = [np.asarray(v, dtype=float) for _, v in sorted(blocks.items())]
    assert arrays and all(a.shape[1] == len(GRID) for a in arrays)
    rng = np.random.default_rng(20261003)
    draws = rng.integers(0, len(arrays), size=(2000, len(arrays)))
    sums = np.asarray([a.sum(axis=0) for a in arrays])
    counts = np.asarray([len(a) for a in arrays])
    totals = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)[:, None]
    lo, hi = np.quantile(totals, [.025, .975], axis=0)
    raw = np.asarray([r[key] for r in rows])
    means = raw.mean(axis=0)
    # A separate scalar arithmetic path checks all 101 plotted estimates.
    assert all(abs(statistics.fmean(v) - observed) < 1e-12
               for v, observed in zip(raw.T.tolist(), means))
    return {"grid": GRID.tolist(), "estimate": means.tolist(), "lower": lo.tolist(),
            "upper": hi.tolist(), "assigned_contexts": len(rows),
            "source_clusters": len(blocks), "level": .95, "replications": 2000,
            "seed": 20261003, "band_scope": "pointwise, not simultaneous",
            "method": "source_cluster_percentile_bootstrap_same_draws_at_all_progress_points"}


def analyse_quality(archive):
    contexts = archive["results.jsonl"]
    phase = next(p for p in archive["complete.json"]["phases"]
                 if p["phase"]["name"] == "short_5s")
    assert phase["execution_complete"] and len(contexts) == phase["requested_contexts"] == 456
    assert archive["execution.json"]["selection_permitted"] is False
    assert archive["frozen_programs.json"]["test_accessed"] is False
    pairs = {p["id"]: p for p in archive["data.json"]["test"]}
    values, trajectories, replay_receipts, counts = [], [], [], Counter()
    check_count = 0
    for context in contexts:
        pair = pairs[context["pair_id"]]
        graph = Graph.from_dict(pair[context["side"]])
        assert graph.digest() == context["graph_sha256"]
        assert len(graph.nodes) == context["n"]
        population, cluster = identity(context["family"], context["cluster"])
        denominator = Fraction(context["reference"]["best_verified_lower_exact"])
        assert denominator > 0
        selected = {m["method"]: m for m in context["methods"] if m["method"] in METHODS}
        assert set(selected) == set(METHODS)
        curves, qualities = {}, {}
        for name, run in selected.items():
            counts[name + "/assigned"] += 1
            counts[name + "/completed"] += int(run["completed"])
            curve, replay = replay_prefixes(graph, context, run, denominator)
            curves[name] = curve
            qualities[name] = float(Fraction(run["value_exact"]) / denominator)
            check_count += replay["checks"]
            replay_receipts.append({"context": context["id"], "method": name,
                                    "graph_sha256": graph.digest(), **replay})
        common = {"id": context["id"], "pair_id": context["pair_id"], "side": context["side"],
                  "stratum": population, "cluster": str(cluster), "n": context["n"],
                  "family": context["family"], "normalizer_exact": str(denominator)}
        for control, *_ in CONTROLS:
            difference = 100 * (qualities["guided_v04"] - qualities[control])
            values.append({**common, "control": control, "difference_pp": difference,
                           "joint_ratio": qualities["guided_v04"], "control_ratio": qualities[control]})
            delta = (100 * (np.asarray(curves["guided_v04"]) - np.asarray(curves[control]))).tolist()
            assert abs(delta[-1] - difference) < 1e-12
            trajectories.append({**common, "control": control, "paired_gain_pp": delta})
    assert len({c["id"] for c in contexts}) == 456
    assert all(counts[m + "/completed"] == counts[m + "/assigned"] == 456 for m in METHODS)
    gains, progress = {}, {}
    for population, *_ in POPULATIONS:
        rows = [r for r in values if r["stratum"] == population]
        sizes = sorted({r["n"] for r in rows})
        gains[population] = {}
        progress[population] = {}
        for control, *_ in CONTROLS:
            selected_rows = [r for r in rows if r["control"] == control]
            entries = []
            for size in sizes:
                rs = [r for r in selected_rows if r["n"] == size]
                ci = interval(rs, "difference_pp")
                assert abs(ci["estimate"] - statistics.fmean(r["difference_pp"] for r in rs)) < 1e-12
                assert len(rs) == (6 if population == "c3" else 72)
                assert Counter(r["side"] for r in rs) == {"left": len(rs)//2, "right": len(rs)//2}
                entries.append({"n": size, **ci})
            gains[population][control] = entries
            rs = [r for r in trajectories if r["stratum"] == population and r["control"] == control]
            curve = vector_interval(rs, "paired_gain_pp")
            assert abs(curve["estimate"][-1] - statistics.fmean(r["difference_pp"] for r in selected_rows)) < 1e-12
            progress[population][control] = curve
    regimes = {}
    for population in ("standard", "dense_long"):
        regimes[population] = {}
        for regime in ("balanced", "ground_scarce", "satellite_scarce"):
            rows = [r for r in values if r["family"] == population+"_"+regime and r["control"] == "rule_v03"]
            curves = []
            for size in sorted({r["n"] for r in rows}):
                rs = [r for r in rows if r["n"] == size]
                assert len(rs) == 24
                assert Counter(r["side"] for r in rs) == {"left": 12, "right": 12}
                curves.append({"n": size, **interval(rs, "difference_pp")})
            regimes[population][regime] = curves
    # Save exact left/right intervention contrasts as a separate diagnostic.
    # The published size curve pools both sides; it is not this difference-in-
    # differences contrast, which can have a different sign and interpretation.
    paired_interventions = []
    by_pair = defaultdict(dict)
    for row in values:
        by_pair[row["pair_id"], row["control"]][row["side"]] = row
    for (pair_id, control), sides in by_pair.items():
        assert set(sides) == {"left", "right"}
        left, right = sides["left"], sides["right"]
        assert left["family"] == right["family"] and left["n"] == right["n"]
        paired_interventions.append({"pair_id": pair_id, "control": control,
            "stratum": left["stratum"], "cluster": left["cluster"], "n": left["n"], "family": left["family"],
            "left_joint_minus_control_pp": left["difference_pp"],
            "right_joint_minus_control_pp": right["difference_pp"],
            "change_in_joint_advantage_pp": right["difference_pp"]-left["difference_pp"]})
    return {"coverage": dict(counts), "trace_validation_checks": check_count,
            "pointwise_curves": progress, "size_gain_curves": gains,
            "rule_only_gain_by_regime": regimes, "paired_intervention_contrasts": paired_interventions,
            "context_paired_schedule_gains": values, "context_paired_trajectories": trajectories,
            "independently_replayed_prefixes": replay_receipts,
            "normalization": "per-context best independently verified feasible complete reward in the original comparison pool; not an optimum",
            "trajectory_x": "fraction of initially active vertices eliminated after recorded kernel commitments; zero time information",
            "diagnostic_status": "post-outcome descriptive analysis of already frozen programs; no candidate or hypothesis selected here"}


def analyse_heap(archive):
    contexts = archive["results.jsonl"]
    assert archive["complete.json"]["complete"] and len(contexts) == 456
    assert archive["execution.json"]["selection_permitted"] is False
    rows = []
    for context in contexts:
        population, cluster = identity(context["family"], context["cluster"])
        pairs = [p for p in context["paired"] if p["arm"] == "primary"]
        assert len(pairs) == 3 and all(p["both_completed"] for p in pairs)
        assert all(p["exact_trace_selection_value_parity"] is True for p in pairs)
        runs = {(r["backend"], r["repetition"]): r for r in context["runs"] if r["arm"] == "primary"}
        ratios = []
        for repetition in range(3):
            full, heap = runs["full_scan", repetition], runs["heap", repetition]
            assert full["completed"] and heap["completed"]
            assert full["trace"] == heap["trace"] and full["selected"] == heap["selected"]
            assert Fraction(full["value_exact"]) == Fraction(heap["value_exact"])
            observed = full["cpu_seconds"] / heap["cpu_seconds"]
            saved = next(p for p in pairs if p["repetition"] == repetition)["full_over_heap_cpu"]
            assert abs(saved - observed) < 1e-12
            ratios.append(observed)
        rows.append({"id": context["id"], "side": context["side"], "n": context["n"],
                     "stratum": population, "cluster": str(cluster),
                     "ratio": statistics.median(ratios), "matched_repeat_ratios": ratios})
    curves = {}
    for population, *_ in POPULATIONS:
        rs = [r for r in rows if r["stratum"] == population]
        curve = []
        for size in sorted({r["n"] for r in rs}):
            selected = [r for r in rs if r["n"] == size]
            ci = interval(selected, "ratio")
            assert len(selected) == (6 if population == "c3" else 72)
            curve.append({"n": size, **ci})
        curves[population] = curve
    # Independently reconcile the earlier publication's aggregate estimates.
    earlier_path = ROOT / "experiments/analysis/v04/heap_summary.json"
    earlier = json.loads(earlier_path.read_text(encoding="utf-8"))
    for population, *_ in POPULATIONS:
        rs = [r for r in rows if r["stratum"] == population]
        saved = earlier["fresh"]["groups"][population+"/primary"]["cpu_ratio_conditional"]["estimate"]
        assert abs(saved - statistics.fmean(r["ratio"] for r in rs)) < 1e-12
    return {"contexts": len(rows), "assigned_repeat_pairs": 3 * len(rows),
            "assessable_repeat_pairs": 3 * len(rows), "exact_trace_selection_value_parity_pairs": 3 * len(rows),
            "curves": curves, "context_median_ratios": rows,
            "earlier_analysis_receipt": receipt(earlier_path),
            "scope": "same TRAIN-frozen primary AST, exact schedule parity; mean of per-context median full-scan/heap CPU ratios; not LLM or schedule-quality improvement"}


def draw_gain(ax, data, population, title):
    for control, label, color, marker, ls in CONTROLS:
        curve = data[population][control]
        x = [r["n"] for r in curve]
        y, lo, hi = [np.asarray([r[k] for r in curve]) for k in ("estimate", "lower", "upper")]
        ax.plot(x, y, c=color, ls=ls, marker=marker, lw=1.4, ms=4, label=label)
        ax.fill_between(x, lo, hi, color=color, alpha=.10, linewidth=0)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xscale("log", base=2)
    ax.set_xticks([64, 128, 256] if population != "c3" else [64, 128, 256, 512],
                  ["64", "128", "256"] if population != "c3" else ["64", "128", "256", "512"])
    ax.set_xlabel("Contacts n")
    ax.set_ylabel("Joint − control reward (pp)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=.15)


def draw_progress(ax, data, population, title):
    for control, label, color, marker, ls in CONTROLS:
        curve = data[population][control]
        x, y, lo, hi = [np.asarray(curve[k]) for k in ("grid", "estimate", "lower", "upper")]
        ax.plot(x, y, c=color, ls=ls, lw=1.35, label=label,
                zorder=5 if control == "baseline" else 4)
        ax.fill_between(x, lo, hi, color=color, alpha=.10, linewidth=0)
        ax.plot(x[-1], y[-1], marker=marker, color=color, ms=4)
        if control == "baseline":
            # Markers retain an overlapping degree trace's visible identity;
            # its true values are never jittered or shifted.
            ax.plot(x[20:100:20], y[20:100:20], marker=marker, color=color,
                    ms=3, ls="none", zorder=6)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1], ["0", "¼", "½", "¾", "1"])
    ax.set_xlabel("Eliminated-vertex fraction")
    ax.set_ylabel("Paired prefix gain (pp)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=.15)


def draw_heap(ax, data, title):
    for population, label, color, marker, ls in POPULATIONS:
        curve = data[population]
        x = [r["n"] for r in curve]
        y, lo, hi = [np.asarray([r[k] for r in curve]) for k in ("estimate", "lower", "upper")]
        ax.plot(x, y, c=color, ls=ls, marker=marker, lw=1.4, ms=4, label=label)
        ax.fill_between(x, lo, hi, color=color, alpha=.10, linewidth=0)
    ax.axhline(1, color=INK, lw=.8)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks([64, 128, 256, 512], ["64", "128", "256", "512"])
    ax.set_yticks([1, 2, 4, 8, 16, 32], ["1", "2", "4", "8", "16", "32"])
    ax.set_xlabel("Contacts n")
    ax.set_ylabel("Scan / heap CPU ratio")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=.15)


def build_figures(summary):
    style()
    # Two complementary scheduling questions. Resource regimes get a separate
    # legend from policy controls; colors never silently change interpretation.
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    fig.subplots_adjust(left=.08, right=.985, bottom=.28, top=.75, wspace=.39)
    regime_colors = (("balanced", "Balanced", PURPLE, "o", "-"),
                     ("ground_scarce", "Ground scarce", BLUE, "s", "--"),
                     ("satellite_scarce", "Satellite scarce", ORANGE, "^", "-."))
    ax = axes[0]
    for regime, label, color, marker, ls in regime_colors:
        curve = summary["quality"]["rule_only_gain_by_regime"]["dense_long"][regime]
        x = [r["n"] for r in curve]
        y, lo, hi = [np.asarray([r[k] for r in curve]) for k in ("estimate", "lower", "upper")]
        ax.plot(x, y, c=color, ls=ls, marker=marker, lw=1.4, ms=4, label=label)
        ax.fill_between(x, lo, hi, color=color, alpha=.10, linewidth=0)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xscale("log", base=2)
    ax.set_xticks([64, 128, 256], ["64", "128", "256"])
    ax.set_xlabel("Contacts n")
    ax.set_ylabel("Joint − rule-only reward (pp)")
    ax.set_title("(a) Benefit depends on constraints", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=.15)
    draw_progress(axes[1], summary["quality"]["pointwise_curves"], "dense_long", "(b) Actual decision trajectories")
    for ax in axes:
        ax.legend(loc="upper left", bbox_to_anchor=(0, 1.46), frameon=False,
                   ncol=2, handlelength=1.5, handletextpad=.4, columnspacing=.8,
                   labelspacing=.2, fontsize=9)
    fig.text(.5, .085, "Dense / long: 216 complete contexts · 24 per regime / size · 95% source-cluster intervals", ha="center", fontsize=9)
    fig.text(.5, .025, "Actual feasible prefix reward; elimination progress is not CPU time", ha="center", fontsize=9)
    save(fig, "effect_curves_v05")

    fig, ax = plt.subplots(figsize=(7.0, 2.5))
    fig.subplots_adjust(left=.085, right=.985, bottom=.25, top=.79)
    draw_heap(ax, summary["heap"]["curves"], "Same frozen AST: execution scaling")
    ax.legend(loc="upper center", bbox_to_anchor=(.53, 1.31), frameon=False,
              ncol=3, handlelength=1.6, columnspacing=1.8)
    fig.text(.5, .045, "456 contexts · 1,368 exact trace / selection / reward pairs · 3 repeats per context", ha="center", fontsize=9)
    save(fig, "heap_scaling_v05")

    # Full predefined-population companion prevents the dense diagnostic from
    # concealing standard or C3 findings. Publication placement is a root choice.
    fig, axes = plt.subplots(2, 3, figsize=(7.0, 5.1))
    fig.subplots_adjust(left=.08, right=.99, bottom=.12, top=.90, hspace=.70, wspace=.45)
    for i, (population, label, *_rest) in enumerate(POPULATIONS):
        draw_gain(axes[0, i], summary["quality"]["size_gain_curves"], population, f"({chr(97+i)}) {label}: final gain")
        draw_progress(axes[1, i], summary["quality"]["pointwise_curves"], population, f"({chr(100+i)}) {label}: trajectories")
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(.51, 1.0),
               frameon=False, ncol=3, columnspacing=1.8, handlelength=1.6)
    fig.text(.5, .02, "All 456 held-out contexts · actual action traces · source-cluster 95% pointwise intervals", ha="center", fontsize=9)
    save(fig, "effect_curves_all_populations_v05")


def write_report(summary):
    q, h = summary["quality"], summary["heap"]
    lines = ["# Frozen-program effect curves (v05)", "",
             "These are descriptive, post-outcome analyses of unchanged v04 programs and completed immutable receipts. They do not introduce a new candidate, retrain a model, access an online oracle, or claim causal LLM superiority.", "",
             "## What the LLM evidence supports", "",
             "The offline assistant proposed typed structural feature–rule pairs. The TRAIN-selected joint program uses the neighborhood clique-cover feature. Its held-out complete-schedule quality exceeds the selected degree and rule-only controls on standard and dense/long populations. The selected free-synthesis program is slightly better on those same populations. Unequal candidate banks and one continuing assistant authoring session prevent a model-level or token-matched causal claim. Native published solvers remain stronger in the existing algorithmic comparison.", "",
             "## Figures", "",
             "`paper/figures/effect_curves_v05.pdf` has two complementary curve panels: complete-schedule paired gain over the selected rule-only program by instance size and resource regime on dense/long scheduling; and actual paired prefix reward gain versus eliminated-vertex fraction against degree, rule-only and free-synthesis on that same predefined population. The compact dense/long view is a post-outcome diagnostic, not a newly selected confirmatory comparison. The complete-schedule gain pools equal left/right assignment; it does not claim gain from tightening alone.", "",
             "`paper/figures/heap_scaling_v05.pdf` gives the paired full-scan/heap CPU ratio curve for the identical frozen AST across all fresh populations. It has a separate execution question and does not imply quality improvement.", "",
             "`paper/figures/effect_curves_all_populations_v05.pdf` retains every predefined standard, dense/long and C3 population, with both final gain and decision trajectories. No population is removed from the source evidence.", "",
             "All fonts are Arial, at least 9 pt at the native 7-inch figure width. Controls retain color and line/marker shape; heap populations have a separate legend. Curves connect measured sizes without a fitted trend or invented intermediate experiments.", "",
             "## Exact semantics", "",
             "Reward ratios divide by each original context's best independently verified feasible complete reward in the original comparison pool, not a proven optimum. A plotted difference is 100 × (joint ratio − control ratio), measured in percentage points. The best reward is held fixed for the two policies in each paired difference.", "",
             "The trajectory x-coordinate is 1 − |active after commitment| / |initially active|. Its y-coordinate is the sum of original graph weights of the recorded feasible prefix, normalized by the same original comparison denominator. The curve is a right-continuous step observation, sampled on 101 fixed fractions without interpolating reward across a deletion. Initial boundary commitments contribute their original weight. Every action and active-set count is replayed against the original graph. Per-action CPU timestamps were never logged; these are constructive decision trajectories, not anytime curves or learning convergence.", "",
             "All four selected policies complete on all 456 contexts. All 1,368 primary-AST scan/heap pairs complete and have identical traces, selections and exact reward. CPU ratios use the median of three order-balanced repeats within a graph context; repeats are not treated as independent graphs. CPU ratios reflect execution engineering, rather than improved scheduling reward or improved LLM reasoning.", "",
             "95% percentile intervals resample whole source clusters, preserving both sides of each intervention and all resource regimes sharing that source. The trajectory bootstrap uses the same cluster draws at every fraction. Its shaded bands are pointwise intervals, not simultaneous confidence bands. C3 size-specific curves have only three source clusters and must be interpreted cautiously.", "",
             "## Complete paired gain by size", "",
             "| Population | n | Contexts | Joint − degree (pp) | Joint − rule only (pp) | Joint − free synthesis (pp) |",
             "|---|---:|---:|---:|---:|---:|"]
    for population, label, *_ in POPULATIONS:
        curves = q["size_gain_curves"][population]
        for i, entry in enumerate(curves["baseline"]):
            displays = []
            for control, *_ in CONTROLS:
                r = curves[control][i]
                displays.append(f"{r['estimate']:+.3f} [{r['lower']:+.3f}, {r['upper']:+.3f}]")
            lines.append(f"| {label} | {entry['n']} | {entry['assigned_contexts']} | " + " | ".join(displays) + " |")
    lines += ["", "## Same-AST execution curve", "",
              "| Population | n | Contexts | Mean context-median scan/heap CPU ratio (95% CI) |",
              "|---|---:|---:|---:|"]
    for population, label, *_ in POPULATIONS:
        for r in h["curves"][population]:
            lines.append(f"| {label} | {r['n']} | {r['assigned_contexts']} | {r['estimate']:.3f} [{r['lower']:.3f}, {r['upper']:.3f}] |")
    lines += ["", "## Reproducibility and checks", "",
              "Run `python scripts/build_effect_curves_v05.py` from a clone with the plotting dependencies. Archives are read directly without extraction. Source files and member SHA-256 receipts, all context-level paired gains, all 101-fraction trajectories, replayed raw action prefixes, exact final reward checks and plot metadata are in `experiments/analysis/v05/effect_curves.json`.", "",
              f"Independent graph/weight replay performed {q['trace_validation_checks']:,} checks across 1,824 completed schedules. All 1,368 heap pair ratios are recomputed from recorded CPU seconds and reconcile with saved pair ratios; all aggregate means match the earlier immutable-source v04 heap analysis to 1e−12. Every size-specific group retains equal left/right assignment. All trajectory endpoints reconcile with the complete-schedule paired quality differences to 1e−12.", "",
              "No source archive, selected AST, solver result, previous analysis, paper section, or frozen-program selection is changed by this builder.", ""]
    (ROOT / "docs/EFFECT_CURVES_V05.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    paths = {"advanced_fresh": ROOT / "experiments/runs/v04/advanced_fresh_v04_001.tar.gz",
             "heap_fresh": ROOT / "experiments/runs/v04/heap_fresh_v04_001.tar.gz"}
    archives = {k: read_archive(p) for k, p in paths.items()}
    summary = {"version": "frozen_program_effect_curves_v05", "selection_permitted": False,
               "sources": {k: {"archive": a["_source"], "members": a["_member_sha256"]} for k, a in archives.items()},
               "builder": receipt(Path(__file__).resolve()),
               "quality": analyse_quality(archives["advanced_fresh"]),
               "heap": analyse_heap(archives["heap_fresh"]),
               "plot_metadata": {"font": "Arial", "minimum_font_pt": 9,
                   "effect_curves_v05": {"width_inches": 7, "height_inches": 2.9, "panels": 2},
                   "heap_scaling_v05": {"width_inches": 7, "height_inches": 2.5, "panels": 1},
                   "effect_curves_all_populations_v05": {"width_inches": 7, "height_inches": 5.1, "panels": 6}}}
    OUT.mkdir(parents=True, exist_ok=True)
    build_figures(summary)
    write_report(summary)
    (OUT / "effect_curves.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"schedule_contexts": 456, "schedule_traces": 1824,
                      "trace_validation_checks": summary["quality"]["trace_validation_checks"],
                      "exact_heap_pairs": summary["heap"]["exact_trace_selection_value_parity_pairs"],
                      "outputs": ["effect_curves_v05", "effect_curves_all_populations_v05"]}))


if __name__ == "__main__":
    main()
