"""Read-only, formal heterogeneous-constraint diagnostics; no solver imports.

Run with Python 3.13 after all four cloud jobs and the aggregate are downloaded.
Outputs one compact three-panel PDF/PNG and exact, source-backed plot_profile.json.
All observed negative, equal and positive paired changes remain in the profile.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np


SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
CONFIGS = ("A", "W", "E", "J")
PAIRS = ("A->W", "A->E", "A->J", "W->E", "W->J", "E->J")
HEADS = ("degree", "existing_frozen", "certified_reference")
NAMESPACE = "heterogeneous_station_local_base9_v1"
COLORS = dict(blue="#26689A", amber="#B97520", charcoal="#34383B",
              gray="#C5C9CC", grid="#E5E7E9", paper="#FFFFFF")
RELATIONS = ("reversal", "preservation", "tie", "tie_to_strict", "strict_to_tie", "unknown", "unavailable")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, inventory: dict) -> dict | list:
    value = json.loads(path.read_text(encoding="utf-8"))
    inventory[str(path)] = dict(sha256=sha256(path), bytes=path.stat().st_size)
    return value


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def source_data(extension: Path, formal: Path, witness_id: str):
    """Check finite coverage and retain the exact rows actually plotted."""
    require(formal.name == "quad_evidence" and "pilot" not in str(formal).lower(),
            "Only the canonical formal quad_evidence directory is accepted")
    inventory = {}
    registration = read_json(formal / "registration.json", inventory)
    acceptance = read_json(formal / "acceptance.json", inventory)
    require(registration["numeric_namespace"] == NAMESPACE, "Unexpected execution namespace")
    require(registration["inventory"]["total_quadqueries"] == 120, "Unexpected registration denominator")
    require(acceptance["completed_sources"] == 4 and acceptance["quadqueries"] == 120,
            "All four sources and all 120 predeclared slots must be complete")
    require(acceptance["model_calls"] == 0, "This is a no-LLM diagnostic figure")
    cloud_root = extension / "cloud_execution"
    receipts = []
    for source in SOURCES:
        receipt = read_json(cloud_root / "cloud_jobs" / (source + ".json"), inventory)
        require(receipt["state"] == "completed" and receipt["exit_code"] == 0,
                "Formal cloud job did not complete: " + source)
        require("--limit-anchors" not in receipt["argv"], "Pilot-limited cloud argv is forbidden")
        require(receipt["evidence_script_sha256"] == registration["script_sha256"],
                "Cloud worker and registration script hashes differ")
        receipts.append(receipt)
    download_path = cloud_root / "LOCAL_DOWNLOAD_RECEIPT.json"
    if download_path.exists():
        read_json(download_path, inventory)
    graph_summary = read_json(extension / "analysis" / "heterogeneous_graph_summary.json", inventory)
    inputs = graph_summary["graphs"]
    require(len(inputs) == 16, "All sixteen input graphs are required")

    certificates, queries, traces = [], {}, {"bb_traces": {}, "commit_traces": {}}
    unavailable = 0
    witness_requirements = None
    for source in SOURCES:
        folder = formal / source
        summary = read_json(folder / "summary.json", inventory)
        manifest = read_json(folder / "query_manifest.json", inventory)
        require(summary["executed_quadqueries"] == summary["planned_quadqueries"] == 30,
                "Source coverage is not the registered 30 slots")
        require(manifest["prepared_before_labels"] and len(manifest["queries"]) == 30,
                "Missing complete pre-label query manifest")
        for query in manifest["queries"]:
            key = (source, query["id"])
            require(key not in queries, "Duplicate registered query")
            queries[key] = query
            if query.get("status") == "unavailable":
                unavailable += 1
                continue
            identity = f"q{query['anchor_slot']:03d}_d{query['destroy_target']:02d}"
            certificate_path = folder / "certificates" / (identity + ".json")
            certificate = read_json(certificate_path, inventory)
            require(certificate["query_id"] == query["id"], "Certificate identity mismatch")
            certificates.append(dict(source=source, query_id=query["id"],
                                     certificate=certificate,
                                     certificate_path=str(certificate_path),
                                     patch_cap=query["patch_cap"],
                                     patch_size=len(query["patch_indices"])))
            for sub in traces:
                for side in CONFIGS:
                    rows = read_json(folder / sub / (identity + "_" + side + ".json"), inventory)
                    require(len(rows) == 3 and {r["head"] for r in rows} == set(HEADS),
                            "Each completed state must contain all three execution heads")
                    state = (source, query["id"], side)
                    require(state not in traces[sub], "Duplicate execution state")
                    require(all(r["query_id"] == query["id"] and r["side"] == side for r in rows),
                            "Execution state identity mismatch")
                    traces[sub][state] = {row["head"]: row for row in rows}
            if query["id"] == witness_id:
                witness_requirements = read_json(folder / "strict_requirements.json", inventory)

    require(len(certificates) + unavailable == 120, "Certificate slots do not reconcile")
    counts = {pair: Counter({relation: 0 for relation in RELATIONS}) for pair in PAIRS}
    for item in certificates:
        for pair in PAIRS:
            relation = item["certificate"]["pair_relations"][pair]
            require(relation in RELATIONS, "Unknown relation class")
            counts[pair][relation] += 1
    for pair in PAIRS:
        counts[pair]["unavailable"] = unavailable
        require(sum(counts[pair].values()) == 120, "Pair denominator mismatch")
        require({k: v for k, v in counts[pair].items() if v and k != "unavailable"}
                == acceptance["relations"][pair], "Pair chart disagrees with formal aggregate")

    selected = [item for item in certificates if item["query_id"] == witness_id]
    require(len(selected) == 1 and witness_requirements is not None, "Requested witness is missing")
    witness = selected[0]
    requirements = {r["side"]: r for r in witness_requirements
                    if r["query_id"] == witness_id and r["side"] in ("E", "J")}
    require(set(requirements) == {"E", "J"}, "Witness needs two strict E/J requirements")
    e, j = requirements["E"], requirements["J"]
    require(e["numeric_namespace"] == j["numeric_namespace"] == NAMESPACE,
            "Witness namespace mismatch")
    require(e["boundary_hash"] == j["boundary_hash"], "Witness boundary differs")
    require(e["preferred_contact_id"] == j["other_contact_id"]
            and e["other_contact_id"] == j["preferred_contact_id"], "Witness does not reverse the same pair")
    require(e["preferred_phi"] == j["other_phi"] and e["other_phi"] == j["preferred_phi"],
            "Full execution base9 must be exactly equal for each contact across E/J")
    require(e["certificate_sha256"] == j["certificate_sha256"]
            == inventory[witness["certificate_path"]]["sha256"], "Witness provenance mismatch")
    witness["strict_requirements"] = requirements
    return inventory, registration, acceptance, inputs, certificates, counts, traces, witness, receipts


def paired_changes(traces: dict) -> dict:
    metrics = dict(bb_traces="full_schedule_value_exact",
                   commit_traces="full_schedule_guarded_value_exact")
    result = {}
    for interface, states in traces.items():
        result[interface] = {}
        for head in ("existing_frozen", "certified_reference"):
            rows = []
            for (source, query_id, side), heads in sorted(states.items()):
                baseline, candidate = heads["degree"], heads[head]
                delta = Fraction(candidate[metrics[interface]]) - Fraction(baseline[metrics[interface]])
                op_key = "total_operation_proxy" if interface == "bb_traces" else "operation_proxy"
                time_key = "total_wall_seconds" if interface == "bb_traces" else "wall_seconds"
                rows.append(dict(source=source, query_id=query_id, side=side,
                    degree_value_exact=baseline[metrics[interface]], head_value_exact=candidate[metrics[interface]],
                    delta_seconds_exact=str(delta), delta_seconds=float(delta),
                    direction="gain" if delta > 0 else "loss" if delta < 0 else "equal",
                    operation_proxy_delta=candidate[op_key] - baseline[op_key],
                    diagnostic_wall_seconds_delta=candidate[time_key] - baseline[time_key],
                    degree_restricted_exact=baseline.get("restricted_exact"),
                    head_restricted_exact=candidate.get("restricted_exact"),
                    reference_uses_strict_certificate=candidate.get("reference_uses_strict_certificate")))
            counts = Counter(r["direction"] for r in rows)
            result[interface][head] = dict(metric=metrics[interface], denominator=len(rows),
                loss=counts["loss"], equal=counts["equal"], gain=counts["gain"],
                operation_proxy_delta_sum=sum(r["operation_proxy_delta"] for r in rows),
                diagnostic_wall_seconds_delta_sum=sum(r["diagnostic_wall_seconds_delta"] for r in rows),
                rows=rows)
    return result


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8.5,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.labelsize": 8.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.edgecolor": COLORS["charcoal"], "axes.linewidth": .7,
        "text.color": COLORS["charcoal"], "axes.labelcolor": COLORS["charcoal"],
        "xtick.color": COLORS["charcoal"], "ytick.color": COLORS["charcoal"],
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
    })


def axis_finish(axis, grid="x"):
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis=grid, color=COLORS["grid"], linewidth=.6, zorder=0)
    axis.tick_params(length=3, width=.7)
    axis.set_axisbelow(True)


def render(inputs: list, counts: dict, witness: dict, changes: dict, acceptance: dict, certificates: list, output: Path):
    style()
    figure = plt.figure(figsize=(11.7, 5.0), facecolor="white")
    grid = figure.add_gridspec(1, 3, width_ratios=(1.0, 1.55, 1.52),
                              left=.062, right=.985, bottom=.245, top=.87, wspace=.40)
    a = figure.add_subplot(grid[0])
    b_grid = grid[1].subgridspec(2, 1, height_ratios=(1.20, 1.05), hspace=.57)
    b_case, b_relations = figure.add_subplot(b_grid[0]), figure.add_subplot(b_grid[1])
    c = figure.add_subplot(grid[2])

    # Categorical connections pair the same source; they are not a temporal trend.
    source_style = {
        "CP-AU-r000": (COLORS["blue"], "o", "-", True),
        "CP-AU-r001": (COLORS["blue"], "s", "--", False),
        "CP-AP-r000": (COLORS["charcoal"], "o", "-", True),
        "CP-AP-r001": (COLORS["charcoal"], "s", "--", False),
    }
    for source in SOURCES:
        values = {r["factorial_id"]: r["m"] / 1000 for r in inputs if r["source_id"] == source}
        require(set(values) == set(CONFIGS), "Incomplete input series")
        color, marker, line, filled = source_style[source]
        a.plot(range(4), [values[k] for k in CONFIGS], color=color, linestyle=line,
               marker=marker, markersize=4.3, markerfacecolor=color if filled else "white",
               markeredgewidth=.8, linewidth=1.05, label=source.removeprefix("CP-"))
    a.set_title("(a) Input graph changes", loc="left", pad=9)
    a.set_xticks(range(4), CONFIGS)
    a.set_xlim(-.22, 3.22)
    a.set_ylim(74, 136)
    a.set_yticks((80, 100, 120))
    a.set_ylabel("Conflict edges (thousands)")
    a.set_xlabel("Ground-constraint configuration")
    axis_finish(a, "y")
    a.legend(loc="upper left", frameon=False, fontsize=7.5, labelspacing=.5,
             handlelength=1.7, borderaxespad=.2)

    # A sound interval is drawn as an interval, never as an unproved point estimate.
    signs = witness["certificate"]["signs"]
    for index, side in enumerate(CONFIGS):
        lower, upper = (signs[side][key] / 1_000_000 for key in ("lower_ticks", "upper_ticks"))
        color = COLORS["blue"] if side == "E" else COLORS["amber"] if side == "J" else COLORS["charcoal"]
        if lower == upper:
            b_case.scatter(lower, index, s=26, marker="D" if side == "J" else "o",
                           facecolor=color, edgecolor="white", linewidth=.4, zorder=3)
            if side in ("E", "J"):
                b_case.annotate(f"{lower:+.1f}", (lower, index), xytext=(-3, 9),
                                textcoords="offset points", color=color, fontsize=8, ha="center")
        else:
            b_case.hlines(index, lower, upper, color=color, linewidth=1.3)
            b_case.vlines((lower, upper), index - .09, index + .09, color=color, linewidth=1.0)
    b_case.axvline(0, color=COLORS["charcoal"], linewidth=.85, linestyle=":")
    b_case.set_yticks(range(4), CONFIGS)
    b_case.set_ylim(3.55, -.70)
    b_case.set_xlim(-1150, 450)
    b_case.set_xticks((-1000, -500, 0))
    b_case.set_xlabel(r"Certified $V(a)-V(b)$ interval (s)", labelpad=2)
    b_case.set_title("(b) Same representation, opposite decision", loc="left", pad=9)
    # The equal full base9 keys come from the saved strict requirements, not a visual approximation.
    b_case.plot([245, 280, 280, 245], [2, 2, 3, 3], color=COLORS["charcoal"], linewidth=.8)
    b_case.text(225, 2.5, r"$\phi_E(a)=\phi_J(a)$" + "\n" + r"$\phi_E(b)=\phi_J(b)$",
                ha="right", va="center", fontsize=7.8)
    axis_finish(b_case)

    relation_styles = {
        "reversal": (COLORS["amber"], "", "Reversal"),
        "preservation": (COLORS["blue"], "", "Preserved"),
        "tie": ("white", "..", "Exact tie"),
        "tie_to_strict": ("#E4CBA7", "/", "Tie to strict"),
        "strict_to_tie": ("#E4CBA7", "\\", "Strict to tie"),
        "unknown": (COLORS["gray"], "///", "Unknown"),
        "unavailable": (COLORS["charcoal"], "xx", "Unavailable"),
    }
    left = np.zeros(len(PAIRS))
    handles = []
    for relation in RELATIONS:
        values = np.array([counts[pair][relation] for pair in PAIRS])
        if not np.any(values):
            continue
        color, hatch, label = relation_styles[relation]
        b_relations.barh(range(len(PAIRS)), values, left=left, height=.66,
                         color=color, hatch=hatch, edgecolor="white", linewidth=.4)
        handles.append(Patch(facecolor=color, edgecolor="#777777", hatch=hatch, label=label))
        left += values
    b_relations.set_yticks(range(len(PAIRS)), [p.replace("->", "–") for p in PAIRS])
    b_relations.invert_yaxis()
    b_relations.set_xlim(0, 120)
    b_relations.set_xticks((0, 40, 80, 120))
    b_relations.set_xlabel("Certified relation counts (120 slots per pair)", labelpad=2)
    axis_finish(b_relations)
    b_relations.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 1.27),
                       ncol=min(3, len(handles)), fontsize=7.5, handlelength=1.05,
                       columnspacing=.9, frameon=False, borderaxespad=0)

    # Reward is not jittered. Vertical offsets only separate nonzero paired observations.
    c.set_title("(c) Execution reward changes", loc="left", pad=9)
    row_specs = (("bb_traces", "existing_frozen", "BB · Frozen"),
                 ("bb_traces", "certified_reference", "BB · Reference*"),
                 ("commit_traces", "existing_frozen", "Commit · Frozen"),
                 ("commit_traces", "certified_reference", "Commit · Reference*"))
    displayed = []
    for index, (interface, head, label) in enumerate(row_specs):
        data = changes[interface][head]
        c.text(.018, index - .35, label + f"   = {data['equal']}/{data['denominator']}",
               transform=c.get_yaxis_transform(), fontsize=7.8, ha="left", va="center")
        nonzero = [row for row in data["rows"] if row["direction"] != "equal"]
        if not nonzero:
            c.text(85, index, "All paired values equal", fontsize=7.7, color="#666666", va="center")
            displayed.append(dict(interface=interface, head=head, nonzero=0))
            continue
        values = np.array([row["delta_seconds"] for row in nonzero])
        # Deterministic indexing, no bootstrap or probabilistic interpretation.
        jitter = (((np.arange(len(values)) * 37) % 101) / 100 - .5) * .40
        for positive in (False, True):
            mask = values > 0 if positive else values < 0
            c.scatter(values[mask], index + jitter[mask], s=12, alpha=.55,
                      color=COLORS["blue"] if positive else COLORS["amber"],
                      marker="o" if positive else "v", edgecolors="none", zorder=2)
        median = float(np.median(values))
        c.scatter(median, index, s=30, marker="D", facecolor="white",
                  edgecolor=COLORS["charcoal"], linewidth=.9, zorder=4)
        displayed.append(dict(interface=interface, head=head, nonzero=len(nonzero),
                              nonzero_median_seconds=median))
    c.axvline(0, color=COLORS["charcoal"], linewidth=.85, linestyle=":")
    c.set_yticks(range(4), [""] * 4)
    c.tick_params(axis="y", length=0)
    c.set_ylim(3.60, -.70)
    all_changes = [r["delta_seconds"] for v in changes.values() for d in v.values() for r in d["rows"]]
    lower, upper = min(all_changes), max(all_changes)
    padding = max((upper - lower) * .10, 1)
    c.set_xlim(lower - padding, max(upper + padding, 430))
    c.set_xlabel("Complete-schedule reward Δ vs Degree (s)")
    c.legend(handles=[Line2D([], [], color=COLORS["amber"], linestyle="none", marker="v", markersize=4, label="Loss"),
                      Line2D([], [], color=COLORS["blue"], linestyle="none", marker="o", markersize=4, label="Gain"),
                      Line2D([], [], color=COLORS["charcoal"], markerfacecolor="white", linestyle="none", marker="D", markersize=4, label="Median (nonzero)")],
             loc="upper left", bbox_to_anchor=(0, -.20), ncol=3, frameon=False,
             fontsize=7.5, handlelength=1.0, columnspacing=.8, borderaxespad=0)
    axis_finish(c)

    figure.suptitle("Heterogeneous ground-constraint diagnostics", fontsize=12, fontweight="bold", x=.062, ha="left", y=.97)
    figure.text(.062, .925, "Frozen STK opportunities · 4 libraries / 2 source groups · TRAIN development only",
                fontsize=8.5, color="#666666")
    figure.text(.062, .135,
        "A: both groups 340 s; W/E: one group 1200 s; J: both 1200 s. Satellite gap = 150 s; vertices and rewards fixed.", fontsize=8)
    interaction = acceptance["interaction"]
    nonzero_i = interaction.get("positive", 0) + interaction.get("negative", 0)
    figure.text(.062, .095,
        f"Witness: {witness['query_id']} (|P|={witness['patch_size']}). Four-side strict: {acceptance['four_strict_denominator']}/120; "
        f"joint-only reversals: {acceptance['joint_only_reversals']}.", fontsize=8)
    cap128 = [item for item in certificates if item['patch_cap'] == 128]
    all_unknown128 = sum(all(s['preference'] == 'unknown' for s in item['certificate']['signs'].values()) for item in cap128)
    figure.text(.062, .057,
        f"Cap 128: {all_unknown128}/{len(cap128)} queries unknown on all 4 sides. "
        f"Interaction I: {nonzero_i} nonzero / {interaction.get('tie', 0)} exact zero / {interaction.get('unknown', 0)} unknown.", fontsize=8)
    figure.text(.062, .019,
        "Bounds refer to the same restricted P/F/X. Reference* uses offline strict certificates (Degree fallback); no LLM calls. "
        "Execution dots omit exact-zero pairs; = counts retain all states.", fontsize=7.8)
    output.mkdir(parents=True, exist_ok=True)
    pdf, png = output / "heterogeneous_joint_diagnostics.pdf", output / "heterogeneous_joint_diagnostics.png"
    figure.savefig(pdf, metadata={"Title": "Heterogeneous ground-constraint diagnostics", "Author": "CIPHEUR research diagnostics"})
    figure.savefig(png, dpi=300)
    plt.close(figure)
    return pdf, png, displayed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--witness-query", default="CP-AU-r000:q008:d16")
    args = parser.parse_args()
    extension = args.extension_root.resolve()
    formal, output = extension / "analysis" / "quad_evidence", extension / "analysis" / "figures"
    values = source_data(extension, formal, args.witness_query)
    inventory, registration, acceptance, inputs, certificates, counts, traces, witness, receipts = values
    changes = paired_changes(traces)
    pdf, png, displayed = render(inputs, counts, witness, changes, acceptance, certificates, output)
    profile = dict(
        schema="heterogeneous_joint_diagnostics_plot_profile_v1",
        created_utc=datetime.now(timezone.utc).isoformat(),
        plot_script_sha256=sha256(Path(__file__)),
        runtime=dict(python=sys.version, platform=platform.platform(), matplotlib=matplotlib.__version__, numpy=np.__version__),
        scope="formal cloud TRAIN restricted P/F/X diagnostics, no TEST / LLM / global-optimum claim",
        formal_root=str(formal), numeric_namespace=NAMESPACE,
        source_groups=acceptance["source_groups"], independent_source_groups=2,
        cloud_completed_sources=[r["source"] for r in receipts],
        inventory=inventory,
        panel_a=dict(unit="conflict edges / 1000", rows=inputs,
                     connection="same-source categorical pairing, not a temporal trend; focused linear axis 74..136k"),
        panel_b=dict(planned_queries=120, relation_counts={p: dict(v) for p, v in counts.items()},
                     unknown_is_not_preservation=True,
                     witness_selection="Named post-label illustrative strict two-cycle, not an unbiased rate sample",
                     witness=witness, four_side_strict=acceptance["four_strict_denominator"],
                     joint_only_reversals=acceptance["joint_only_reversals"], interaction=acceptance["interaction"],
                     sound_intervals=[dict(source=x["source"], query_id=x["query_id"], patch_cap=x["patch_cap"],
                                          patch_size=x["patch_size"], signs=x["certificate"]["signs"],
                                          interaction=x["certificate"]["interaction"]) for x in certificates]),
        panel_c=dict(pairing="(source, query_id, side), head minus Degree, exact Fraction seconds",
                     bb_metric="full_schedule_value_exact; lower feasible output, not certified optimum unless restricted_exact",
                     commit_metric="full_schedule_guarded_value_exact; original positive-gain guard applied to every head",
                     reference="Offline strict-side preference, Degree fallback for unknown/tie; not a deployable baseline",
                     zero_policy="Every exact-zero pair retained in denominator/profile; not drawn as a degenerate distribution",
                     display_jitter="Deterministic vertical-only separation; reward coordinate never jittered",
                     inferential_policy="No CI, significance or independent-sample claim for overlapping restricted states",
                     timing_policy="Shared-host diagnostic wall times are retained but not shown as an equal-time benchmark",
                     plotted_nonzero_rows=displayed, paired_changes=changes),
        outputs={p.name: dict(path=str(p), sha256=sha256(p), bytes=p.stat().st_size) for p in (pdf, png)},
        frozen_data_modified=False, solver_calls=0, model_calls=0,
    )
    dump(output / "plot_profile.json", profile)
    print(json.dumps(dict(pdf=str(pdf), png=str(png), profile=str(output / "plot_profile.json"),
                          planned_queries=120, displayed_witness=args.witness_query), ensure_ascii=False))


if __name__ == "__main__":
    main()
