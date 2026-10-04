"""Presentation-only table and observed-size coverage from frozen transfer data.

No execution, authoring, candidate selection, resampling or bound replacement.
Expose live artists and source arrays for separate read-only inspection.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import statistics
import tarfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STEM = "matched_transfer_exploratory_v05_001"
ARMS = ("witness", "relations", "objective")
POPS = ("DIMACS_unit", "DIMACS_hash_weighted", "SATLIB_unit", "SATLIB_hash_weighted", "C3")
LABELS = {"witness": "A Witness", "relations": "B Relations", "objective": "C Objective", "Degree": "Degree (compiled)"}
BLUE, PURPLE, ORANGE, GRAY, INK = "#176B9B", "#71559C", "#D36B32", "#687782", "#243640"
TABLE = ROOT / "paper/generated/matched_transfer_table_v05.tex"
FIGURE = ROOT / "paper/figures/transfer_coverage_compact_v05"
REPORT = ROOT / "docs/TRANSFER_PRESENTATION_V05.md"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read_inputs():
    analysis_path = ROOT / "experiments/analysis/v05" / (STEM + ".json")
    archive = ROOT / "experiments/runs/v05" / (STEM + ".tar.gz")
    audit_path = ROOT / "experiments/analysis/v05/matched_transfer_audit_v05_001.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert digest(archive) == analysis["archive_sha256"] == audit["archive_sha256"]
    assert digest(analysis_path) == audit["publisher_analysis_sha256"]
    assert not audit["errors"]
    with tarfile.open(archive, "r:gz") as tar:
        data = tar.extractfile(STEM + "/data.json").read()
        protocol = json.load(tar.extractfile(STEM + "/protocol.json"))
        contexts = json.loads(data)["contexts"]
        rows = [json.loads(line) for line in tar.extractfile(STEM + "/results.jsonl") if line.strip()]
    assert sha256(data).hexdigest() == protocol["data_sha256"] == audit["data_sha256"]
    assert len(contexts) == len(rows) == 120
    assert {c["id"] for c in contexts} == {r["id"] for r in rows}
    assert sum(len(r["rows"]) for r in rows) == 1560
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in (analysis_path, archive, audit_path)}
    return analysis, contexts, rows, sources


def tables_and_curves(analysis, contexts, rows):
    lookup = {r["id"]: {m["method"]: m for m in r["rows"]} for r in rows}
    assert len(lookup) == 120
    checks = {"raw_quality_values": 0, "block_mean_values": 0, "table_cells": 0,
              "coverage_strata": 0, "exact_group_rate_comparisons": 0, "plotted_line_arrays": 0}
    table = {a: [] for a in (*ARMS, "Degree")}
    for pop in POPS:
        cases = [c for c in contexts if c["population"] == pop]
        p = analysis["populations"][pop]
        assert [c["id"] for c in cases] == p["context_ids"]
        for method, record in p["methods"].items():
            values = []
            for c in cases:
                m = lookup[c["id"]][method]
                value = 100 * float(Fraction(m["value_exact"]) / Fraction(c["reference"]["formal_upper_exact"])) if m["completed"] else 0.0
                values.append(value)
            assert values == record["quality_to_upper_percent"]
            assert statistics.mean(values) == record["mean_quality_to_formal_upper_percent"]
            checks["raw_quality_values"] += len(values)
        for arm in ARMS:
            data = p["arms"][arm]
            means = [p["methods"][f"block_{b}_{arm}"]["mean_quality_to_formal_upper_percent"] for b in range(4)]
            assert means == data["block_quality_to_formal_upper_percent"]
            assert statistics.mean(means) == data["equal_block_mean_quality_to_formal_upper_percent"]
            assert sum(p["methods"][f"block_{b}_{arm}"]["completed"] for b in range(4)) == data["completed"]
            table[arm].append({"population": pop, "quality": data["equal_block_mean_quality_to_formal_upper_percent"],
                "completed": data["completed"], "assigned": data["assigned"]})
            checks["block_mean_values"] += 4
            checks["table_cells"] += 1
        d = p["degree"]
        table["Degree"].append({"population": pop, "quality": d["mean_quality_to_formal_upper_percent"], "completed": d["completed"], "assigned": d["assigned"]})
        checks["table_cells"] += 1
    coverage = {}
    for family in ("C3", "SATLIB"):
        coverage[family] = {}
        for arm in (*ARMS, "Degree"):
            groups = defaultdict(lambda: [0, 0])
            for c in contexts:
                if c["population"] != family and not c["population"].startswith(family + "_"):
                    continue
                for method, m in lookup[c["id"]].items():
                    matches = method == "Degree" if arm == "Degree" else method.endswith("_" + arm)
                    if matches:
                        groups[c["n"]][0] += int(m["completed"])
                        groups[c["n"]][1] += 1
            x = sorted(groups)
            numerators = [groups[n][0] for n in x]
            denominators = [groups[n][1] for n in x]
            fractions = [Fraction(a, b) for a, b in zip(numerators, denominators)]
            coverage[family][arm] = {"n": x, "completed": numerators, "assigned": denominators,
                "rate_exact": [str(v) for v in fractions], "percent": [100 * float(v) for v in fractions]}
            checks["coverage_strata"] += len(x)
            assert x == ([64, 128, 256, 512] if family == "C3" else [273, 654, 975])
            assert denominators == ([6 if arm == "Degree" else 24] * 4 if family == "C3" else [20 if arm == "Degree" else 80] * 3)
    for family, group in (("C3", ("relations", "objective", "Degree")), ("SATLIB", ARMS)):
        first = coverage[family][group[0]]
        for arm in group[1:]:
            other = coverage[family][arm]
            assert first["n"] == other["n"] and first["rate_exact"] == other["rate_exact"]
            checks["exact_group_rate_comparisons"] += len(first["n"])
    assert checks["raw_quality_values"] == 1560 and checks["table_cells"] == 20
    assert checks["block_mean_values"] == 60 and checks["coverage_strata"] == 28
    return table, coverage, checks


def render_table(table):
    # Compare displayed two-decimal quality, retaining ties after rounding.
    maxima = [max(float(f"{table[a][i]['quality']:.2f}") for a in table) for i in range(5)]
    lines = ["% Presentation only: bound to frozen exploratory transfer archive and independently audited analysis.",
        r"\begin{table*}[t]", r"\centering",
        r"\caption{Exploratory transfer on 120 reused contexts, without reselection. Cells: failure-zero mean $100W/U$ (completed/assigned), using prior clique upper $U$ and equal authoring-block weights. All arms use the compiled five-CPU-second target after AST parsing. Blue identifies Witness; bold marks displayed column maxima, including ties, without significance.}",
        r"\label{tab:matched-transfer}", r"\setlength{\tabcolsep}{4pt}", r"\begin{tabular}{lccccc}", r"\toprule",
        r"Arm & DIMACS unit & DIMACS hash & SATLIB unit & SATLIB hash & C3 \\", r"\midrule"]
    for arm in (*ARMS, "Degree"):
        cells = []
        for i, c in enumerate(table[arm]):
            value = f"{c['quality']:.2f}"
            if float(value) == maxima[i]:
                value = r"\textbf{" + value + "}"
            cells.append(f"{value} ({c['completed']}/{c['assigned']})")
        prefix = r"\rowcolor{blue!7} " if arm == "witness" else ""
        lines.append(prefix + LABELS[arm] + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def build_panel(coverage, checks):
    font_manager.findfont("Arial", fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": GRAY, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK, "figure.facecolor": "white", "savefig.facecolor": "white"})
    fig = plt.figure(figsize=(3.35, 1.70))
    ax = fig.add_axes([.18, .255, .80, .48])
    styles = (("C3", "relations", "C3 R/O/D", PURPLE, "o", "--", 5.3, "white", 4),
              ("C3", "witness", "C3 W", BLUE, "s", "-", 3.0, BLUE, 5),
              ("SATLIB", "witness", "SAT W/R/O", ORANGE, "^", "-.", 4.0, ORANGE, 3),
              ("SATLIB", "Degree", "SAT D", GRAY, "D", ":", 4.8, "white", 2))
    handles = []
    for family, arm, label, color, marker, ls, ms, fill, order in styles:
        data = coverage[family][arm]
        line, = ax.plot(data["n"], data["percent"], label=label, color=color, marker=marker,
            ls=ls, lw=1.15, ms=ms, markerfacecolor=fill, markeredgewidth=.9, zorder=order)
        np.testing.assert_array_equal(line.get_xdata(), data["n"])
        np.testing.assert_array_equal(line.get_ydata(), data["percent"])
        checks["plotted_line_arrays"] += 2
        handles.append(line)
    # Legend order starts with the focal arm, while the open comparator is
    # drawn first so exact equal positions remain visibly equal (no jitter).
    fig.legend(handles=[handles[i] for i in (1,0,2,3)], loc="upper center", bbox_to_anchor=(.56,1.005),
        ncol=2, frameon=False, handlelength=1.35, handletextpad=.3,
        columnspacing=.75, labelspacing=.25, borderaxespad=.1)
    ax.set_xscale("log", base=2)
    ax.set(xlim=(58, 1100), ylim=(-5, 108), xlabel="Vertices n (log)", ylabel="Completed (%)")
    ax.set_xticks([64, 128, 256, 512, 975], ["64", "128", "256", "512", "975"])
    ax.set_yticks([0, 50, 100])
    ax.minorticks_off()
    ax.tick_params(pad=2, length=3)
    ax.xaxis.labelpad = 3
    ax.yaxis.labelpad = 3
    ax.grid(axis="y", alpha=.15, lw=.5)
    return fig


def validate_text(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text():
            continue
        assert text.get_fontsize() >= 9
        extent = text.get_window_extent(renderer)
        assert bounds.x0-.5 <= extent.x0 <= extent.x1 <= bounds.x1+.5, text.get_text()
        assert bounds.y0-.5 <= extent.y0 <= extent.y1 <= bounds.y1+.5, text.get_text()


def main():
    analysis, contexts, rows, sources = read_inputs()
    table, coverage, checks = tables_and_curves(analysis, contexts, rows)
    fig = build_panel(coverage, checks)
    validate_text(fig)
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(render_table(table), encoding="utf-8", newline="\n")
    fig.savefig(FIGURE.with_suffix(".pdf"))
    fig.savefig(FIGURE.with_suffix(".png"), dpi=300)
    plt.close(fig)
    lines = ["# Exploratory transfer presentation (V05)", "",
        "Presentation-only outputs read the unchanged archive and independently audited publisher JSON. No execution, synthesis, selection, resampling or bound computation is rerun.", "",
        "## Table", "",
        "Four arm rows by five population columns use the same failure-zero mean percentage of old certified clique U. The four frozen bank/block means are weighted equally, with all assigned failures retained. Coverage counts are shown alongside every value. The Witness row has a blue!7 background; the largest displayed two-decimal quality in each column is bold, including ties. Neither styling encodes statistical significance or native-solver superiority. Unit and hash-weight quality are never pooled. The separate companion experiment report retains prior best-feasible L ratios and all block values.", "",
        "Degree (compiled) is the common new-study reference, using the same compiled score-slice backend and five-second cooperative target after AST parse. It is distinct from the prior interpreter/native timing study; recorded assignment times include parse, evaluator initialization, complete scheduling, validation and cap overshoot. No native old-host costs are added to this table.", "",
        "## Coverage panel", "",
        "Native width/height: 3.35 x 1.70 inches; Arial 9pt for every visible label. Use at least 3.35 inches in print. Markers and line styles provide redundant distinctions. The four displayed groups are combined only after exact equality of completion FRACTIONS is proved; their trial denominators remain separate. Connecting lines show observed size strata, not an interpolated experiment, fitted scaling law, anytime trace, learning curve or statistical confidence interval.", "",
        "W = Witness, R = Relations, O = Objective, D = compiled Degree; SAT = SATLIB. C3 has six paired-context observations at each size and all four frozen programs per arm. The two SATLIB weight modes are pooled by adding completed and assigned counts for coverage only. Ten source graphs per weight mode at each size give 80 assignments per arm and 20 Degree assignments. Duplicate weight views are not independent sources. All real marker positions are retained; a readable subset of x ticks is labelled because 256 and 273 are close on log scale.", "",
        "| Family | Arm | n | Completed | Assigned | Exact fraction | Percent |", "|---|---|---:|---:|---:|---:|---:|"]
    for family, arms in coverage.items():
        for arm, c in arms.items():
            for values in zip(c["n"], c["completed"], c["assigned"], c["rate_exact"], c["percent"]):
                n, done, assigned, fraction, percent = values
                lines.append(f"| {family} | {arm} | {n} | {done} | {assigned} | {fraction} | {percent:.6f} |")
    lines += ["", "## Source binding and array checks", "", "`" + json.dumps(checks, sort_keys=True) + "`", "",
        "All 1,560 per-context source qualities are exactly matched to the analysis JSON; 60 block means, 20 table cells, all 28 coverage strata and 14 exact grouped-rate comparisons are checked. The plotted four x/y array pairs equal the raw-stratum arrays exactly. All visible text extents remain inside the native canvas. Independent PDF/render/artist inspection is a separate verification step.", "",
        "| Immutable source | SHA256 |", "|---|---|"]
    for name, expected in sources.items():
        assert digest(ROOT / name) == expected
        lines.append(f"| `{name}` | `{expected}` |")
    lines += ["", "| Presentation output | SHA256 |", "|---|---|"]
    for path in (TABLE, FIGURE.with_suffix(".pdf"), FIGURE.with_suffix(".png")):
        lines.append(f"| `{path.relative_to(ROOT).as_posix()}` | `{digest(path)}` |")
    lines += ["", "The extension reuses 120 old V04 contexts and is exploratory. The plot exposes coverage loss with scale; it does not turn an observed limitation into a positive LLM effect. C3 Witness is 19/24 at n=512; the other C3 curves are 100%. SATLIB arm completion drops from 80/80 at n=273 to zero at both larger observed sizes; compiled Degree retains 20/20 at n=654 and also fails at n=975.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"table": str(TABLE), "figure": str(FIGURE), "inches": [3.35, 1.70], "checks": checks}))


if __name__ == "__main__":
    main()
