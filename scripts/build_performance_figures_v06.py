"""Fixed compact panels from root-authorized final V003 analysis only.

No raw/compact assignment rows, run archive, graph, AST, programme, solver,
oracle, authoring response, bootstrap or live progress is read or executed.
All recipes and eight displayed series are outcome-free constants.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "experiments/discovery/performance_r2_eoh_test_v06_003_registered_001/server_input_preparation/context_inventory.json"
INVENTORY_SHA256 = "f4d204d75ee2eb9e05b40405ae25bd47a0b4c3714df27a28a0b4930b857cc917"
ANALYZER = ROOT / "scripts/analyze_performance_test_v06.py"
CONFIG_SHA256 = {
    "configs/analysis_v06_001.json": "52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1",
    "configs/analysis_refinement_v06_002.json": "f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769",
}
AUDITOR_SHA256 = "59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a"
HELPER_SHA256 = {
    "scripts/verify_public_alias_v05.py": "6b349b659bad3acfd3a9e1abbf9046a984f8f66df05068841c1ba8c076aa959a",
    "scripts/verify_matched_llm_v05.py": "52b331fea2214642ac50ffe3996c95a6fb9893320e50df84e1371f8fedae087b",
    "scripts/verify_synthesis_train_v06.py": "941264da65d8aac3ccb9242de75ebff4c7f8cc29eb602e071be11d4e25dc8322",
}
TARGETS = (0.1, 1.0, 5.0)
CONTRAST = "versus_fixed_full_CHILS_seed1"
GAIN = "percent_gain_exact"
CPU = "standalone_cpu_seconds"
SCOPE = "population_family"
BLUE, PURPLE, ORANGE, GRAY, INK = "#176B9B", "#71559C", "#D36B32", "#687782", "#243640"
WIDTH, HEIGHT = 3.35, 2.15


@dataclass(frozen=True)
class Series:
    key: str
    label: str
    track: str
    first: str
    color: str
    marker: str
    linestyle: str
    filled: bool = False
    markersize: float = 3.6


# This order is fixed before opening any performance analysis.
SERIES = (
    Series("CHILS", "CHILS (3 seeds)", "native", "native:CHILS", GRAY, "s", "-"),
    Series("CHILS_ILS", "CHILS-ILS (3)", "native", "native:CHILS_ILS", GRAY, "v", "--"),
    Series("M2WIS", "M2WIS (3 seeds)", "native", "native:M2WIS", ORANGE, "^", ":"),
    Series("Struction", "Struction", "native", "native:Struction", ORANGE, "D", "-."),
    Series("WeightedBR", "WeightedBR", "native", "native:WeightedBR", GRAY, "x", ":"),
    Series("joint_W_cold", "Joint W / Degree", "cold_Degree", "joint_W", BLUE, "D", "--", False, 5.0),
    Series("joint_W_warm", "Joint W / CHILS", "warm_CHILS", "joint_W", BLUE, "s", "-", True, 3.4),
    Series("EoH_warm", "EoH-DSL / CHILS", "warm_CHILS", "published_EoH_DSL_quality", PURPLE, "o", "--", False, 5.5),
)

# Source groups are a complete inventory, never ranked by measured outcome.
GROUPS = (
    ("fresh_standard_balanced", "standard_balanced", "Standard / balanced", 36, 18),
    ("fresh_standard_ground_scarce", "standard_ground_scarce", "Standard / ground scarce", 36, 18),
    ("fresh_standard_satellite_scarce", "standard_satellite_scarce", "Standard / satellite scarce", 36, 18),
    ("fresh_dense_long_balanced", "dense_long_balanced", "Dense-long / balanced", 36, 18),
    ("fresh_dense_long_ground_scarce", "dense_long_ground_scarce", "Dense-long / ground scarce", 36, 18),
    ("fresh_dense_long_satellite_scarce", "dense_long_satellite_scarce", "Dense-long / satellite scarce", 36, 18),
    ("WDP", "WDP_1xx", "WDP 1xx", 5, 5),
    ("WDP", "WDP_2xx", "WDP 2xx", 6, 6),
    ("WDP", "WDP_4xx", "WDP 4xx", 6, 6),
    ("WDP", "WDP_5xx", "WDP 5xx", 4, 4),
    ("WDP", "WDP_6xx", "WDP 6xx", 4, 4),
    ("UAI_Segmentation", "Segmentation", "UAI Segmentation", 3, 3),
    ("UAI_Grids_CHILS64", "Grids", "UAI Grids / exact 64-bit", 10, 10),
    ("C3_interval_exploratory", None, "C3 interval / exploratory", 24, 12),
    ("C3_legacy_exploratory", None, "C3 legacy / exploratory", 24, 12),
)
MAIN_RECIPES = (
    ("fresh_standard_balanced", "standard_balanced"),
    ("fresh_dense_long_ground_scarce", "dense_long_ground_scarce"),
    ("WDP", "WDP_4xx"),
    ("UAI_Grids_CHILS64", "Grids"),
)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def finite(value):
    if value is None:
        return None
    require(type(value) in (int, float) and math.isfinite(value), "Nonfinite/non-numeric plotted statistic")
    return float(value)


def load_bound_analysis(analysis_path, expected_sha256, audit_path):
    """Read approved aggregate bytes and their audit; never read assignment rows."""
    require(valid_sha(expected_sha256), "Supply the root-provided final analysis SHA256")
    require(digest(analysis_path) == expected_sha256, "Analysis bytes differ from the root-provided SHA256")
    analysis = json.loads(Path(analysis_path).read_bytes())
    require(analysis.get("version") == "v06_audited_performance_analysis_001", "Unsupported analysis version")
    require(analysis.get("analysis_source_sha256") == digest(ANALYZER), "Analysis source differs from final local analyzer")
    require(analysis.get("analysis_config_sha256") == CONFIG_SHA256, "Registered analysis scope changed")
    require(all(digest(ROOT / n) == s for n, s in CONFIG_SHA256.items()), "Local registered analysis bytes changed")
    require(analysis.get("assignments") == 52548 and analysis.get("bootstrap_replicates") == 2000
            and analysis.get("bootstrap_seed") == 261004, "Not the frozen complete-frame analysis")
    require(analysis.get("no_TEST_selection") is True
            and analysis.get("raw_objectives_never_pooled_across_families") is True,
            "Missing frozen no-selection/family separation scope")
    audit_sha = digest(audit_path)
    require(audit_sha == analysis.get("independent_audit_sha256")
            == analysis.get("independent_audit_authorization_sha256"), "Audit is not the linked root-authorized report")
    audit = json.loads(Path(audit_path).read_bytes())
    require(audit.get("version") == "v06_independent_performance_TEST_audit_001"
            and type(audit.get("errors")) is int and audit["errors"] == 0
            and audit.get("error_details") == [], "Require a final zero-error independent audit")
    require(type(audit.get("checks")) is int and audit["checks"] > 0, "Audit check count absent")
    require(audit.get("audit_source_sha256") == AUDITOR_SHA256
            == digest(ROOT / "scripts/verify_performance_test_v06.py"), "Independent verifier source changed")
    require(audit.get("independent_helper_sha256") == HELPER_SHA256
            and all(digest(ROOT / n) == s for n, s in HELPER_SHA256.items()), "Independent helper closure changed")
    require(valid_sha(analysis.get("archive_sha256")) and audit.get("archive_sha256") == analysis["archive_sha256"],
            "Original archive binding absent or changed")
    require(valid_sha(analysis.get("audited_rows_sha256"))
            and audit.get("audited_rows_sha256") == analysis["audited_rows_sha256"], "Audited input-row binding changed")
    require(audit.get("registered_constants") == analysis.get("registered_constants"), "Audit/analysis frame differs")
    constants = analysis["registered_constants"]
    require(constants.get("wall_targets") == [0.1, 1, 5] and constants.get("total_contexts") == 302
            and constants.get("total_assignments") == 52548 and constants.get("policy_slots") == 23,
            "Not the original V003 matrix")
    policies = audit.get("policies")
    require(isinstance(policies, list) and len(policies) == 23, "All 23 frozen policy metadata identities are required")
    return analysis, audit, {"analysis_path": str(Path(analysis_path).resolve()), "analysis_sha256": expected_sha256,
        "audit_path": str(Path(audit_path).resolve()), "audit_sha256": audit_sha,
        "archive_sha256": analysis["archive_sha256"], "audited_rows_sha256": analysis["audited_rows_sha256"],
        "analysis_source_sha256": analysis["analysis_source_sha256"], "audit_source_sha256": AUDITOR_SHA256,
        "independent_helper_sha256": HELPER_SHA256, "analysis_config_sha256": CONFIG_SHA256,
        "registered_constants": constants}


def input_group_inventory():
    require(digest(INVENTORY) == INVENTORY_SHA256, "Outcome-free source inventory bytes changed")
    contexts = json.loads(INVENTORY.read_bytes())["contexts"]
    expected = {(p, f): (n, s) for p, f, _, n, s in GROUPS}
    grouped = {key: [] for key in expected}
    for row in contexts:
        key = row["population"], row.get("family")
        require(key in grouped, "Unexpected frozen input family")
        grouped[key].append(row)
    output = {}
    for key, rows in grouped.items():
        clusters = sorted({r.get("source_cluster") or r.get("cluster") or r.get("pair_id") or r["id"] for r in rows})
        require((len(rows), len(clusters)) == expected[key], "Fixed group/source denominator changed")
        output[key] = {"assigned_contexts": len(rows), "assigned_source_clusters": len(clusters),
            "source_clusters": clusters, "context_ids": sorted(r["id"] for r in rows), "n": sorted({r["n"] for r in rows}),
            "previously_exposed_exploratory": key[0].startswith("C3_")}
    require(len(contexts) == 302 and len(grouped) == 15, "Retain all 302 inputs and 15 groups")
    return output


def metric_receipt(metric, assigned, source_count):
    require(isinstance(metric, dict), "Analysis metric missing")
    require(metric.get("assigned_contexts") == assigned and metric.get("assigned_clusters") == source_count,
            "Statistic denominator differs from frozen source inventory")
    for key, maximum in (("defined_contexts", assigned), ("defined_clusters", source_count)):
        require(type(metric.get(key)) is int and 0 <= metric[key] <= maximum, "Invalid metric coverage")
    require(metric.get("requested_bootstrap_replicates") == 2000, "Interval uses a different bootstrap")
    mean = finite(metric.get("mean"))
    ci = metric.get("ci95")
    require(isinstance(ci, list) and len(ci) == 2, "Missing exact stored interval")
    low, high = map(finite, ci)
    require((mean is None) == (metric["defined_contexts"] == 0), "Null estimate/coverage inconsistent")
    require((low is None) == (high is None), "Half-defined interval")
    require(low is None or low <= high, "Reversed interval")
    require(mean is not None or (low is None and high is None), "Null estimate has invented uncertainty")
    if metric.get("mean_exact") is not None:
        # Only a consistency bound: plotted y is the stored float mean itself.
        exact_mean = float(Fraction(metric["mean_exact"]))
        require(mean is not None and math.isclose(mean, exact_mean, rel_tol=1e-12, abs_tol=1e-12),
                "Stored exact and numeric point estimates disagree")
    return {"mean": mean, "mean_exact": metric.get("mean_exact"), "ci95": [low, high],
        **{k: metric.get(k) for k in ("assigned_contexts", "defined_contexts", "assigned_clusters", "defined_clusters",
            "requested_bootstrap_replicates", "defined_bootstrap_replicates", "interval_scope")}}


def curve_for(analysis, collection, population, family, series, contrast=False):
    name = "first" if contrast else "estimate"
    matches = [(i, c) for i, c in enumerate(analysis[collection]) if c["scope"] == SCOPE
        and c["population"] == population and c["family"] == family and c.get("n") is None
        and c.get("regime") is None and c.get("profile") is None
        and c["track"] == series.track and c[name] == series.first
        and (not contrast or c["contrast"] == CONTRAST)]
    require(len(matches) == 1, "One original three-target aggregate curve required: " + series.key)
    index, curve = matches[0]
    require([float(p["target"]) for p in curve["points"]] == list(TARGETS), "A frozen target was omitted or reordered")
    return index, curve


def panel_data(analysis, groups):
    output = []
    for population, family, title, _, _ in GROUPS:
        inventory = groups[population, family]
        rows = []
        for series in SERIES:
            gi, gain_curve = curve_for(analysis, "contrast_budget_curves", population, family, series, True)
            ci, cost_curve = curve_for(analysis, "role_budget_curves", population, family, series)
            points = []
            for index, (g, c) in enumerate(zip(gain_curve["points"], cost_curve["points"])):
                gain = metric_receipt(g["metrics"][GAIN], inventory["assigned_contexts"], inventory["assigned_source_clusters"])
                cpu = metric_receipt(c["metrics"][CPU], inventory["assigned_contexts"], inventory["assigned_source_clusters"])
                points.append({"target": TARGETS[index], "gain": gain, "cpu": cpu,
                    "gain_analysis_pointer": f"/contrast_budget_curves/{gi}/points/{index}/metrics/{GAIN}",
                    "cpu_analysis_pointer": f"/role_budget_curves/{ci}/points/{index}/metrics/{CPU}",
                    "quality_member_coverage": c["coverage"], "quality_complete_contexts": c["complete_contexts"],
                    "measurement_member_counts": c["measurement_member_counts"],
                    "status_counts": c["status_counts"], "cost_scope": c["cost_scope"]})
            rows.append({"series": asdict(series), "points": points,
                "gain_valid_targets": sum(p["gain"]["mean"] is not None for p in points),
                "cpu_gain_valid_targets": sum(p["gain"]["mean"] is not None and p["cpu"]["mean"] is not None for p in points)})
        output.append({"population": population, "family": family, "title": title,
            "main_recipe": (population, family) in MAIN_RECIPES, "inventory": inventory, "series": rows})
    return output


def gain_limits(panels):
    values = [0.0]
    for panel in panels:
        for row in panel["series"]:
            for point in row["points"]:
                values += [v for v in (point["gain"]["mean"], *point["gain"]["ci95"]) if v is not None]
    low, high = min(values), max(values)
    span = high - low
    padding = span * .08 if span else 1.0
    return low - padding, high + padding


def slug(panel):
    return re.sub("[^a-zA-Z0-9_]+", "_", panel["population"] + "__" + (panel["family"] or "all"))


def configure_plotting():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.findfont("Arial", fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
        "axes.titlesize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": GRAY, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK, "figure.facecolor": "white", "savefig.facecolor": "white"})
    return plt


def finish_figure(fig, stem, out):
    """One bounded rendering check; no crop that silently changes native geometry."""
    from matplotlib.text import Text
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    for text in fig.findobj(Text):
        if not text.get_visible() or not text.get_text():
            continue
        box = text.get_window_extent(renderer)
        require(box.x0 >= bounds.x0 - 1 and box.x1 <= bounds.x1 + 1
                and box.y0 >= bounds.y0 - 1 and box.y1 <= bounds.y1 + 1,
                "Text outside native panel: " + text.get_text())
        require(text.get_fontsize() >= 9, "Printed font below 9pt")
    outputs = {}
    for extension in ("pdf", "png"):
        destination = out / f"{stem}.{extension}"
        require(not destination.exists(), "Never overwrite a prior figure")
        fig.savefig(destination, dpi=300)
        outputs[destination.name] = digest(destination)
    return outputs


def draw_panel(plt, panel, ylim, out, cpu=False):
    import numpy as np
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    fig = plt.figure(figsize=(WIDTH, HEIGHT))
    ax = fig.add_axes([.20, .35, .78, .51])
    ax.grid(axis="y", alpha=.15, linewidth=.5)
    ax.set_axisbelow(True)
    ax.axhline(0, color=GRAY, lw=.7, ls=":")
    ax.set_ylim(ylim)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, prune="both"))
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_powerlimits((-4, 5))
    ax.yaxis.set_major_formatter(formatter)
    ax.set_ylabel("Gain vs CHILS seed 1 (%)", labelpad=3)
    ax.tick_params(length=3, pad=2)
    if not cpu:
        ax.set_xscale("log")
        ax.set(xlim=(.085, 5.85), xticks=TARGETS, xticklabels=["0.1", "1", "5"])
        ax.set_xlabel("Nominal wall target (s)", labelpad=3)
    else:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3, prune="upper"))
        ax.set_xlabel("Measured standalone CPU (s)", labelpad=3)
        ax.set_xlim(left=0)
    inventory = panel["inventory"]
    fig.text(.5, .94, f"{panel['title']}  (N={inventory['assigned_contexts']}, S={inventory['assigned_source_clusters']})",
             ha="center", va="center", fontsize=9)
    plot_arrays, checks = [], []
    for row in panel["series"]:
        style, points = row["series"], row["points"]
        xs = [p["cpu"]["mean"] if cpu else p["target"] for p in points]
        ys = [p["gain"]["mean"] for p in points]
        x = np.array([np.nan if v is None else v for v in xs])
        y = np.array([np.nan if v is None else v for v in ys])
        line, = ax.plot(x, y, color=style["color"], linestyle=style["linestyle"], lw=1.1,
            marker=style["marker"], ms=style["markersize"], markeredgewidth=.9,
            markerfacecolor=style["color"] if style["filled"] else "none", label=style["label"])
        np.testing.assert_array_equal(line.get_xdata(), x)
        np.testing.assert_array_equal(line.get_ydata(), y)
        # Segments preserve asymmetric endpoints even if a mean lies outside its CI.
        expected_vertical, expected_horizontal = [], []
        for xx, yy, point in zip(xs, ys, points):
            lo, hi = point["gain"]["ci95"]
            if xx is not None and yy is not None and lo is not None:
                expected_vertical.append([[xx, lo], [xx, hi]])
            cl, ch = point["cpu"]["ci95"]
            if cpu and xx is not None and yy is not None and cl is not None:
                expected_horizontal.append([[cl, yy], [ch, yy]])
        if expected_vertical:
            segments = ax.vlines([v[0][0] for v in expected_vertical], [v[0][1] for v in expected_vertical],
                [v[1][1] for v in expected_vertical], color=style["color"], lw=.7, alpha=.35).get_segments()
            np.testing.assert_array_equal(np.asarray(segments), np.asarray(expected_vertical))
        if expected_horizontal:
            segments = ax.hlines([v[0][1] for v in expected_horizontal], [v[0][0] for v in expected_horizontal],
                [v[1][0] for v in expected_horizontal], color=style["color"], lw=.7, alpha=.25).get_segments()
            np.testing.assert_array_equal(np.asarray(segments), np.asarray(expected_horizontal))
        plot_arrays.append({"series_key": style["key"], "target": list(TARGETS), "x": xs, "y": ys,
            "gain_ci95": [p["gain"]["ci95"] for p in points],
            "cpu_ci95": [p["cpu"]["ci95"] for p in points] if cpu else None,
            "drawn_vertical_segments": expected_vertical, "drawn_horizontal_segments": expected_horizontal,
            "valid_target_count": sum(xx is not None and yy is not None for xx, yy in zip(xs, ys)),
            "quality_defined_contexts": [p["gain"]["defined_contexts"] for p in points],
            "quality_defined_clusters": [p["gain"]["defined_clusters"] for p in points],
            "cost_defined_contexts": [p["cpu"]["defined_contexts"] for p in points],
            "cost_defined_clusters": [p["cpu"]["defined_clusters"] for p in points]})
        checks.append(style["key"] + ": artist coordinates and CI segments equal stored analysis arrays")
    missing = [sum(r["points"][i]["gain"]["mean"] is None
        or (cpu and r["points"][i]["cpu"]["mean"] is None) for r in panel["series"]) for i in range(3)]
    fig.text(.5, .025, "Missing series (0.1/1/5 s): " + " / ".join(map(str, missing)),
             ha="center", va="bottom", fontsize=9)
    if cpu:
        fig.text(.5, .102, "Cost / quality coverage differs; see receipt", ha="center", va="bottom", fontsize=9)
    else:
        ranges = []
        for i in range(3):
            counts = [r["points"][i]["gain"]["defined_contexts"] for r in panel["series"]]
            ranges.append(f"{min(counts)}–{max(counts)}")
        fig.text(.5, .102, "Defined Q pairs: " + " / ".join(ranges), ha="center", va="bottom", fontsize=9)
    if cpu:
        # Include every measured coordinate/CPU interval; no clipped costs or Pareto envelope.
        costs = [v for r in panel["series"] for p in r["points"]
                 for v in (p["cpu"]["mean"], *p["cpu"]["ci95"]) if v is not None]
        upper = max(costs, default=1.0)
        ax.set_xlim(0, upper * 1.08 if upper > 0 else 1)
    stem = ("performance_cpu_gain_v06__" if cpu else "performance_gain_v06__") + slug(panel)
    files = finish_figure(fig, stem, out)
    plt.close(fig)
    return {"files_sha256": files, "geometry_inches": [WIDTH, HEIGHT], "font_points": 9,
        "population": panel["population"], "family": panel["family"], "main_recipe": panel["main_recipe"],
        "panel_kind": "conditional_cpu_vs_gain" if cpu else "nominal_budget_vs_gain",
        "gain_ylim": list(ylim), "missing_series_counts_by_target": missing, "arrays": plot_arrays, "checks": checks,
        "x_scope": "Measured conditional standalone CPU means, ordered by nominal target; cost and quality coverage differ."
            if cpu else "Three nominal wall targets; line segments are budget comparisons, not an anytime or learning trace."}


def draw_legend(plt, out):
    handles = [plt.Line2D([], [], color=s.color, linestyle=s.linestyle, lw=1.1, marker=s.marker,
        ms=s.markersize, markeredgewidth=.9, markerfacecolor=s.color if s.filled else "none", label=s.label) for s in SERIES]
    fig = plt.figure(figsize=(7.0, .52))
    fig.legend(handles=handles, loc="center", ncol=4, frameon=False, handlelength=1.55,
               columnspacing=1.15, handletextpad=.4, labelspacing=.55, fontsize=9)
    outputs = finish_figure(fig, "performance_series_legend_v06", out)
    plt.close(fig)
    return {"files_sha256": outputs, "geometry_inches": [7.0, .52], "font_points": 9,
            "series_order": [s.key for s in SERIES], "external_shared_legend": True}


def build(analysis_path, analysis_sha256, audit_path, out):
    out = Path(out)
    require(not out.exists(), "Use a new figure output directory; prior files remain immutable")
    analysis, audit, binding = load_bound_analysis(analysis_path, analysis_sha256, audit_path)
    groups = input_group_inventory()
    panels = panel_data(analysis, groups)
    main_ylim = gain_limits([p for p in panels if p["main_recipe"]])
    plt = configure_plotting()
    out.mkdir(parents=True)
    outputs = []
    for panel in panels:
        ylim = main_ylim if panel["main_recipe"] else gain_limits([panel])
        result = draw_panel(plt, panel, ylim, out)
        result["gain_axis_scope"] = "Shared across all four predeclared main panels" if panel["main_recipe"] else "Independent family scale; zero and all negative estimates/intervals included"
        outputs.append(result)
    for panel in panels:
        if panel["main_recipe"]:
            outputs.append(draw_panel(plt, panel, main_ylim, out, cpu=True))
    legend = draw_legend(plt, out)
    receipt = {"version": "v06_fixed_performance_figure_recipes_001", "script_sha256": digest(__file__),
        "input_binding": binding, "frozen_context_inventory_sha256": INVENTORY_SHA256,
        "targets": list(TARGETS), "main_recipes": [list(p) for p in MAIN_RECIPES],
        "series": [asdict(s) for s in SERIES], "all15_group_arrays_and_coverage": panels,
        "fixed23_policy_metadata": audit["policies"], "rendered_panels": outputs, "legend": legend,
        "gain_metric": GAIN, "reference": "Native full-target CHILS seed1, fixed before TEST; native CHILS curve remains its three-seed mean.",
        "uncertainty": "Reused stored 95% source/pair-cluster bootstrap intervals, 2000 replicates seed261004; no new resampling.",
        "quality_scope": "Mean paired percentage gain on defined complete-member groups with defined fixed reference; exact per-target coverage is retained.",
        "cpu_scope": "Separate conditional measured standalone CPU includes charged shared warm initializer; coverage can differ from quality. No Pareto-optimality or equal-compute claim.",
        "no_TEST_selection": True, "new_bootstrap": False, "scientific_or_program_execution": False,
        "raw_or_live_result_rows_read": False, "negative_gains_and_null_targets_preserved": True,
        "no_main_latex_edits": True}
    destination = out / "performance_figure_receipt_v06.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {"out": str(out.resolve()), "gain_panels": 15, "cpu_panels": 4, "shared_legends": 1,
            "receipt_sha256": digest(destination), "analysis_sha256": analysis_sha256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", required=True, help="Final analysis.json only")
    parser.add_argument("--analysis-sha256", required=True, help="Exact final analysis SHA256 supplied by root")
    parser.add_argument("--audit", required=True, help="Linked root-authorized zero-error independent report")
    parser.add_argument("--out", required=True, help="New directory for vector panels, PNGs and source-array receipt")
    args = parser.parse_args()
    print(json.dumps(build(args.analysis, args.analysis_sha256, args.audit, args.out)))


if __name__ == "__main__":
    main()
