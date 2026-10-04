"""Prepared, fixed-recipe panels from final audit-bound heldout analysis only.

No raw archive, live result, programme, scorer, scheduler or oracle is accessed.
Root supplies the final analysis SHA; the report binds the compact's exact bytes.
All 31 identities survive in the sidecar; the declared main panel uses 21 roles.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ["original"] + [f"relabel_{i}" for i in range(5)]
ANALYZER_SHA256 = "5acedcb11f0a407e377b98a24162ae9f1864a0e275faa5a28f59ccb323fb54d2"
CONFIG_SHA256 = {
    "configs/analysis_v06_001.json": "52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1",
    "configs/analysis_refinement_v06_002.json": "f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769",
}
ROLE_COUNTS = {"proposed_witness_joint": 4, "nonguarded_quality_comparator": 12,
               "TRAIN_quality_only_control": 2, "classical_Degree": 1,
               "complete_relabel_control_bank": 8, "nonguarded_published_quality_baseline": 4}
MAIN_ROLES = {"proposed_witness_joint", "nonguarded_quality_comparator",
              "classical_Degree", "nonguarded_published_quality_baseline"}
BLUE, PURPLE, ORANGE, GRAY, INK = "#176B9B", "#71559C", "#D36B32", "#687782", "#243640"
STYLES = {
    "W_joint": ("W joint", PURPLE, "D"), "W_quality": ("W quality", PURPLE, "o"),
    "R": ("R", BLUE, "^"), "O": ("O", GRAY, "s"), "EoH": ("EoH", ORANGE, "p"),
    "Degree": ("Degree", INK, "P"), "TRAIN_control": ("TRAIN ctl.", GRAY, "v"),
    "enumerated_control": ("Bank", GRAY, "h"),
}
PANELS = {
    "heldout_strict_alias_movement_v06": ("strict_fit", "base_alias_fit", "Strict fit (%)", "Base-alias fit (%)"),
    "heldout_pair_joint_movement_v06": ("preservation_joint_fit", "reversal_joint_fit",
                                        "Preservation joint fit (%)", "Reversal joint fit (%)"),
}


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_bound_analysis(path, expected_sha256):
    """Verify the final report before opening its sole hash-bound compact input."""
    path = Path(path).resolve()
    require(sha(expected_sha256) and digest(path) == expected_sha256, "Root final analysis SHA256 mismatch")
    report = json.loads(path.read_bytes())
    require(report.get("version") == "v06_R2_EoH_heldout_mechanism_analysis_001", "Unsupported final analysis schema")
    meta = report["metadata"]
    require(meta.get("analyzer_source_sha256") == ANALYZER_SHA256
            and meta.get("analysis_config_sha256") == CONFIG_SHA256, "Prepared analyzer/config binding changed")
    require(meta.get("programme_reexecution") is False and meta.get("selection_performed") is False
            and meta.get("online_model_or_oracle_calls") == 0
            and meta.get("source_and_pair_clusters_preserved") is True, "Require frozen outcome-free analysis")
    bindings = meta["input_bindings"]
    require(len(bindings) == 2 and {b["kind"] for b in bindings} == {"R2", "EoH"}, "Both completed audited batches are required")
    for b in bindings:
        require(type(b.get("independent_audit_errors")) is int and b["independent_audit_errors"] == 0
                and type(b.get("independent_audit_checks")) is int and b["independent_audit_checks"] > 0,
                "Require positive-check, zero-error independent audit bindings")
        for field in ("archive_sha256", "independent_audit_sha256", "independent_auditor_source_sha256",
                      "results_sha256", "terminal_marker_sha256", "protocol_sha256", "root_release_sha256"):
            require(sha(b.get(field)), "Incomplete provenance field: " + field)
        helpers = b.get("independent_helper_sha256")
        require(isinstance(helpers, dict) and len(helpers) == 3 and all(sha(v) for v in helpers.values()),
                "Complete independent helper closure is required")
    compact_reference = Path(report["compact_file"])
    compact_path = compact_reference if compact_reference.is_absolute() else ROOT / compact_reference
    if not compact_path.is_file():
        # A copied final bundle may retain its original host path. Only the
        # exact named compact beside the report is eligible, with the same SHA.
        compact_path = path.parent / compact_reference.name
    require(sha(report.get("compact_sha256")) and digest(compact_path) == report["compact_sha256"],
            "Final compact bytes do not match the authorized analysis")
    compact = json.loads(compact_path.read_bytes())
    require(compact.get("version") == "v06_R2_EoH_heldout_analysis_compact_001"
            and compact.get("metadata") == meta and compact.get("frame") == report["frame"],
            "Compact schema/metadata/frame differs from final analysis")
    frame = report["frame"]
    require(frame["R2_identities"] == 27 and frame["EoH_identities"] == 4 and frame["states"] == 72
            and frame["variants"] == VARIANTS and frame["kernel_positions"] == 13392,
            "All original identities/states/variants must remain")
    require(len(compact["kernel_rows"]) == 13392 and len(compact["assignment_rows"]) == 186
            and len(compact["query_rows"]) == frame["query_positions"]
            and len(compact["pair_rows"]) == frame["pair_positions"], "Complete analyzed compact frame is required")
    identities = report["identities"]
    require(len(identities) == 31 and len({e["id"] for e in identities}) == 31
            and Counter(e["role"] for e in identities) == ROLE_COUNTS, "All31 original role identities are required")
    require({(r["program_id"], r["variant"]) for r in compact["assignment_rows"]}
            == {(e["id"], v) for e in identities for v in VARIANTS}, "Identity/variant positions omitted")
    return report, compact_path


def statistic(saved):
    """Use the existing exact full-denominator statistic; do not zero-fill."""
    n, measured = saved["assigned_members"], saved["measured_members"]
    require(type(n) is int and type(measured) is int and 0 <= measured <= n,
            "Invalid analyzed metric denominator")
    exact = saved["full_members_mean_exact"]
    if exact is None:
        require(n == 0 or measured < n, "Complete nonempty metric has an unexplained null mean")
        value = None
    else:
        require(isinstance(exact, (str, int)) and not isinstance(exact, bool) and n > 0 and measured == n,
                "A full metric requires every original member")
        value = Fraction(exact)
        require(0 <= value <= 1 and value == Fraction(saved["measured_sum_exact"]) / n,
                "Metric is not the analyzed exact fit fraction")
    return {"assigned": n, "measured": measured, "missing": n - measured,
            "numerator_exact": saved["measured_sum_exact"], "fraction_exact": str(value) if value is not None else None,
            "percent": float(100 * value) if value is not None else None}


def metric_variants(summary, name):
    result = {}
    for variant in VARIANTS:
        mechanism = summary["variants"][variant]["mechanism"]
        if name in ("strict_fit", "base_alias_fit"):
            saved = mechanism["strict_fit" if name == "strict_fit" else "actual_base_alias_strict_fit"]
        else:
            category = "strict_reversal" if name == "reversal_joint_fit" else "strict_preservation"
            saved = mechanism["pair_categories"][category]["joint_correctness"]
        result[variant] = statistic(saved)
    return result


def metric(summary, name):
    variants = metric_variants(summary, name)
    relabels = [variants[v] for v in VARIANTS[1:]]
    require(len({r["assigned"] for r in relabels}) == 1, "Renamings changed the metric denominator")
    known = all(r["fraction_exact"] is not None for r in relabels)
    mean = sum((Fraction(r["fraction_exact"]) for r in relabels), Fraction()) / 5 if known else None
    collapsed = None
    if name in ("strict_fit", "base_alias_fit"):
        key = "strict_fit" if name == "strict_fit" else "alias_strict_fit"
        collapsed = statistic(summary["five_rename_source_bootstrap"][key]["all5_mean_fit"])
        require(collapsed["assigned"] == relabels[0]["assigned"]
                and collapsed["fraction_exact"] == (str(mean) if mean is not None else None),
                "Existing collapsed five-rename statistic disagrees with exact variant means")
    return {"original": variants["original"], "renamed_mean": {
            "fraction_exact": str(mean) if mean is not None else None,
            "percent": float(100 * mean) if mean is not None else None,
            "assigned_per_rename": relabels[0]["assigned"],
            "measured_renames": sum(r["fraction_exact"] is not None for r in relabels),
            "all5_required": True, "collapsed_query_statistic": collapsed}, "variants": variants}


def group(identity):
    role = identity["role"]
    if role == "proposed_witness_joint":
        return "W_joint"
    if role == "nonguarded_quality_comparator":
        return {"witness": "W_quality", "relations": "R", "objective": "O"}[identity["arm"]]
    return {"classical_Degree": "Degree", "nonguarded_published_quality_baseline": "EoH",
            "TRAIN_quality_only_control": "TRAIN_control", "complete_relabel_control_bank": "enumerated_control"}[role]


def arrays(report):
    """The21 subset is role-declared before outcome reads; no outcome selector."""
    identities = {e["id"]: e for e in report["identities"]}
    summaries = {s["identity"]["id"]: s for s in report["summaries"]}
    require(len(report["summaries"]) == 31 and set(summaries) == set(identities), "Every identity needs its analyzed summary")
    output = []
    for identity in sorted(identities.values(), key=lambda e: (group(e), str(e.get("block")), e["id"])):
        summary = summaries[identity["id"]]
        require(summary["identity"] == identity and set(summary["variants"]) == set(VARIANTS), "Frozen summary identity changed")
        output.append({"identity": identity, "plot_group": group(identity), "main21": identity["role"] in MAIN_ROLES,
                       "metrics": {name: metric(summary, name) for name in
                                   ("strict_fit", "base_alias_fit", "reversal_joint_fit", "preservation_joint_fit")}})
    main = [r for r in output if r["main21"]]
    require(len(main) == 21 and Counter(r["plot_group"] for r in main)
            == {"W_joint": 4, "W_quality": 4, "R": 4, "O": 4, "EoH": 4, "Degree": 1}, "Fixed main21 role recipe changed")
    for role in ("W_joint", "W_quality", "R", "O"):
        require(len({r["identity"]["block"] for r in main if r["plot_group"] == role}) == 4,
                "All four authoring blocks must remain as individual dots")
    return output


def coordinate(row, x, y, phase):
    values = [row["metrics"][name][phase]["percent"] for name in (x, y)]
    return values if all(v is not None for v in values) else None


def render(name, spec, rows, out, plt):
    x, y, xlabel, ylabel = spec
    fig = plt.figure(figsize=(3.35, 2.15))
    ax = fig.add_axes([.18, .28, .57, .66])
    ax.set(xlim=(0, 100), ylim=(0, 100), xticks=[0, 50, 100], yticks=[0, 50, 100],
           xlabel=xlabel, ylabel=ylabel)
    ax.grid(alpha=.15, linewidth=.45)
    ax.set_axisbelow(True)
    ax.plot([0, 100], [0, 100], color=GRAY, lw=.55, ls="--", alpha=.4, zorder=0)
    ax.tick_params(length=3, pad=2)
    ax.xaxis.labelpad = ax.yaxis.labelpad = 3
    plotted, missing, connections = {}, {}, 0
    for phase in ("original", "renamed_mean"):
        plotted[phase] = []
        missing[phase] = sum(coordinate(r, x, y, phase) is None for r in rows)
    for r in rows:
        original, renamed = [coordinate(r, x, y, phase) for phase in ("original", "renamed_mean")]
        if original is not None and renamed is not None:
            line, = ax.plot([original[0], renamed[0]], [original[1], renamed[1]],
                            color=STYLES[r["plot_group"]][1], lw=.55, alpha=.5, zorder=1)
            assert list(line.get_xdata()) == [original[0], renamed[0]]
            assert list(line.get_ydata()) == [original[1], renamed[1]]
            connections += 1
    handles = []
    for key, (label, color, marker) in STYLES.items():
        members = [r for r in rows if r["plot_group"] == key]
        if not members:
            continue
        handles.append(plt.Line2D([], [], color=color, marker=marker, linestyle="None", markersize=4, label=label))
        for phase in ("original", "renamed_mean"):
            measured = [(r, coordinate(r, x, y, phase)) for r in members]
            measured = [(r, xy) for r, xy in measured if xy is not None]
            if not measured:
                continue
            xy = [point for _, point in measured]
            marks = ax.scatter([p[0] for p in xy], [p[1] for p in xy], marker=marker,
                s=29 if phase == "original" else 12, edgecolors=color,
                facecolors="none" if phase == "original" else color, linewidths=.8,
                alpha=.9, clip_on=False, zorder=3 if phase == "original" else 4)
            assert marks.get_offsets().tolist() == xy
            plotted[phase].extend({"id": r["identity"]["id"], "percent_xy": point} for r, point in measured)
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(.995, .96), frameon=False,
               handlelength=.7, handletextpad=.3, labelspacing=.5, borderpad=0)
    encoding = [plt.Line2D([], [], color=INK, marker="o", mfc="none", lw=0, ms=4, label="Original"),
                plt.Line2D([], [], color=INK, marker="o", mfc=INK, lw=0, ms=3, label="5-rename mean")]
    fig.legend(handles=encoding, loc="lower center", bbox_to_anchor=(.50, .075), ncol=2,
               frameon=False, handlelength=.7, handletextpad=.3, columnspacing=.8)
    fig.text(.50, .015, f"n={len(rows)}; missing (original / mean): {missing['original']} / {missing['renamed_mean']}",
             ha="center", va="bottom", fontsize=9)
    assert all(len(plotted[p]) + missing[p] == len(rows) for p in plotted)
    outputs = {}
    for ext in ("pdf", "png"):
        path = out / (name + "." + ext)
        fig.savefig(path, dpi=300)
        outputs[path.name] = digest(path)
    plt.close(fig)
    return {"axes": [x, y], "assigned_identities": len(rows), "plotted": plotted,
            "missing_coordinate_points": missing, "connectors": connections, "outputs_sha256": outputs}


def build(analysis, analysis_sha256, out, all_identities=False):
    out = Path(out)
    require(not out.exists(), "Preserve prior outputs; choose a new figure directory")
    report, compact_path = load_bound_analysis(analysis, analysis_sha256)
    data = arrays(report)
    # Import plotting dependencies only after final artifact and array checks.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.findfont("Arial", fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": GRAY, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK, "figure.facecolor": "white", "savefig.facecolor": "white"})
    out.mkdir(parents=True)
    panels = {name: render(name, spec, [r for r in data if r["main21"]], out, plt) for name, spec in PANELS.items()}
    if all_identities:
        panels.update({name + "_all31": render(name + "_all31", spec, data, out, plt) for name, spec in PANELS.items()})
    sidecar = {"version": "v06_predeclared_heldout_figure_arrays_001", "analysis_sha256": analysis_sha256,
        "compact_sha256": report["compact_sha256"], "compact_file_resolved": str(compact_path),
        "input_metadata": report["metadata"], "frame": report["frame"], "all31_identities": data,
        "dependent_duplicate_AST_groups": report["dependent_duplicate_AST_groups"],
        "EoH_pipeline_origin_counts": report["EoH_pipeline_origin_counts"], "panels": panels,
        "script_sha256": digest(__file__), "recipe_sha256": digest(ROOT / "docs/V06_HELDOUT_FIGURE_RECIPES.md"),
        "geometry_inches": [3.35, 2.15], "font": "Arial9", "new_resampling_or_policy_or_oracle_execution": False,
        "scope": "Each frozen identity has an original hollow point and full five-rename mean solid point. "
                 "Coincident identities are retained without jitter; null coordinates are counted, never zero-filled. "
                 "No block or permutation is declared an independent draw; no confidence intervals are averaged."}
    with (out / "heldout_figure_arrays_v06.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(sidecar, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"out": str(out), "panels": len(panels), "identities": len(data),
                      "sidecar_sha256": digest(out / "heldout_figure_arrays_v06.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--analysis-sha256", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--all-identities", action="store_true", help="Add fixed all31 supplementary versions; always retain all31 sidecar")
    arguments = parser.parse_args()
    build(arguments.analysis, arguments.analysis_sha256, arguments.out, arguments.all_identities)
