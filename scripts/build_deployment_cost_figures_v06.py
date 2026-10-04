"""Presentation-only T=5 CPU scaling from final per-context audited estimates.

Two fixed original scheduling families, all three registered sizes, and all
five native families plus warm Degree/joint-W/EoH remain. Points are paired
source means, not repeated anytime observations. No bootstrap or solver runs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics
import numpy as np
import build_performance_figures_v06 as style
from build_warm_deployment_figures_v06 import WARM_SERIES

ANALYSIS_SHA256 = "839324710784ba71ee40c25ea199b527ff346fb7ec1209f97756ed2d9513aaf9"
FAMILIES = (("fresh_standard_balanced", "standard_balanced", "Standard / balanced"),
            ("fresh_dense_long_ground_scarce", "dense_long_ground_scarce", "Dense-long / ground scarce"))
SIZES = (512, 1024, 2048)


def build(context_file, analysis_sha256, out):
    style.require(analysis_sha256 == ANALYSIS_SHA256, "Use the root-authorized final analysis")
    out = Path(out)
    style.require(not out.exists(), "New presentation output directory required")
    rows = []
    source_hash = hashlib.sha256()
    frame = {(p, f) for p, f, _ in FAMILIES}
    keys = {(s.track, s.first) for s in WARM_SERIES}
    with Path(context_file).open("rb") as stream:
        for line in stream:
            source_hash.update(line)
            row = json.loads(line)
            if (row["population"], row["family"]) in frame and row["target"] == 5.0 and (row["track"], row["estimate"]) in keys:
                style.require(row["n"] in SIZES, "Unexpected frozen size")
                rows.append(row)
    panels = []
    for population, family, title in FAMILIES:
        series = []
        for spec in WARM_SERIES:
            points = []
            for n in SIZES:
                selected = [r for r in rows if r["population"] == population and r["family"] == family and r["n"] == n
                            and r["track"] == spec.track and r["estimate"] == spec.first]
                style.require(len(selected) == 12 and len({r["id"] for r in selected}) == 12, "Retain twelve original endpoints per size/series")
                clusters = {}
                for row in selected:
                    clusters.setdefault(row["cluster"], []).append(row)
                style.require(len(clusters) == 6 and all(len(c) == 2 for c in clusters.values()), "Preserve both sides of each source pair")
                observations = []
                for cluster, pair in sorted(clusters.items()):
                    times = [r["standalone_cpu_seconds"] for r in pair if r["standalone_cpu_seconds"] is not None]
                    observations.append({"cluster": cluster, "cpu_seconds": statistics.mean(times) if times else None,
                        "known_endpoints": len(times), "endpoints": [{"id": r["id"], "cpu_seconds": r["standalone_cpu_seconds"],
                        "known_cpu_members": r["standalone_cpu_seconds_defined_members"], "requested_members": r["requested_members"],
                        "successful_members": r["successful_members"], "returned_members": r["returned_members"],
                        "errors": r["error_counts"]} for r in pair]})
                values = [v["cpu_seconds"] for v in observations if v["cpu_seconds"] is not None]
                points.append({"n": n, "mean_cpu_seconds": statistics.mean(values) if values else None,
                    "defined_source_pairs": len(values), "assigned_source_pairs": 6, "observations": observations})
            series.append({"key": spec.key, "label": spec.label, "track": spec.track, "estimate": spec.first, "points": points})
        panels.append({"population": population, "family": family, "title": title, "series": series})
    plt = style.configure_plotting()
    out.mkdir(parents=True)
    outputs = []
    for panel in panels:
        fig = plt.figure(figsize=(3.35, 1.80))
        ax = fig.add_axes([.19, .33, .79, .55])
        ax.set_xscale("log", base=2)
        ax.set(xlim=(460, 2310), xticks=SIZES, xticklabels=[str(n) for n in SIZES], xlabel="Number of contacts", ylabel="Standalone CPU (s)")
        ax.grid(axis="y", alpha=.16, lw=.5)
        ax.tick_params(length=3, pad=2)
        ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=4, prune="upper"))
        maximum = max((o["cpu_seconds"] for s in panel["series"] for p in s["points"] for o in p["observations"] if o["cpu_seconds"] is not None), default=1)
        ax.set_ylim(0, maximum * 1.10)
        for spec, curve in zip(WARM_SERIES, panel["series"]):
            xs = np.array(SIZES)
            ys = np.array([np.nan if p["mean_cpu_seconds"] is None else p["mean_cpu_seconds"] for p in curve["points"]])
            line, = ax.plot(xs, ys, color=spec.color, ls=spec.linestyle, lw=1.1, marker=spec.marker, ms=spec.markersize,
                markeredgewidth=.9, markerfacecolor=spec.color if spec.filled else "none")
            np.testing.assert_array_equal(line.get_xdata(), xs)
            np.testing.assert_array_equal(line.get_ydata(), ys)
            for p in curve["points"]:
                values = [o["cpu_seconds"] for o in p["observations"] if o["cpu_seconds"] is not None]
                ax.scatter([p["n"]] * len(values), values, marker=spec.marker, s=8, color=spec.color, alpha=.16, linewidths=0)
        fig.text(.5, .98, panel["title"], ha="center", va="top", fontsize=9)
        fig.text(.5, .015, "T = 5 s; 6 paired sources per size", ha="center", va="bottom", fontsize=9)
        files = style.finish_figure(fig, "performance_cpu_scaling_v06__" + style.slug(panel), out)
        plt.close(fig)
        outputs.append({"files_sha256": files, "geometry_inches": [3.35, 1.80], "font_points": 9, "population": panel["population"], "family": panel["family"]})
    original_series = style.SERIES
    style.SERIES = WARM_SERIES
    original_finish = style.finish_figure
    style.finish_figure = lambda fig, stem, dest: original_finish(fig, "performance_cpu_scaling_legend_v06", dest)
    legend = style.draw_legend(plt, out)
    style.SERIES = original_series
    receipt = {"version": "v06_fixed_two_family_deployment_CPU_scaling_001", "analysis_sha256": analysis_sha256,
        "context_estimates_path": str(Path(context_file).resolve()), "context_estimates_sha256": source_hash.hexdigest(),
        "renderer_sha256": style.digest(__file__), "target": 5, "sizes": list(SIZES), "panel_arrays": panels,
        "rendered_panels": outputs, "legend": legend, "means": "Frozen native seeds/author members are already averaged within context; both endpoints are averaged within pair, then six paired-source costs are averaged per size.",
        "cost_scope": "Measured standalone CPU includes the full charged shared CHILS initializer for every warm policy plus its own repair. Shared graph loading is separate. Known failed-attempt costs are not quality values; endpoint/member coverage is retained.",
        "no_new_bootstrap": True, "no_new_solver_or_program_execution": True, "no_TEST_selection": True,
        "no_anytime_or_LLM_speed_superiority_claim": True, "old_full_and_warm_gain_artifacts_unchanged": True}
    path = out / "performance_cpu_scaling_receipt_v06.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {"out": str(out.resolve()), "panels": 2, "receipt_sha256": style.digest(path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-estimates", required=True)
    parser.add_argument("--analysis-sha256", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.context_estimates, args.analysis_sha256, args.out)))
