"""Presentation-only R2 authoring wall/gate plot from frozen receipt metadata.

No raw response, programme, TEST, optimizer, oracle or new audit is accessed.
Bank wall is measured session wall, not interpolated candidate completion time.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments/analysis/v06/refinement_train_audit_v06_002.json"
AUDIT_SHA = "a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34"
RECEIPTS = ROOT / "experiments/discovery/v06_refinement_draft_003/receipts"
ARMS = {"witness": ("W", "#71559C"), "relations": ("R", "#176B9B"),
        "objective": ("O", "#687782")}


def digest(raw):
    return sha256(raw).hexdigest()


def prepare():
    raw = AUDIT.read_bytes()
    if digest(raw) != AUDIT_SHA:
        raise ValueError("Use the original frozen TRAIN gate audit")
    audit = json.loads(raw)
    if audit["error_count"] != 0 or audit["raw_slot_count"] != 120:
        raise ValueError("Require the complete existing zero-error TRAIN audit")
    candidates = audit["candidate_summaries"]
    inputs = {AUDIT.relative_to(ROOT).as_posix(): AUDIT_SHA}
    banks = []
    for arm in ARMS:
        for block in range(5):
            rows = sorted((r for r in candidates if r["arm"] == arm and r["block"] == block),
                          key=lambda r: r["slot"])
            if [r["slot"] for r in rows] != list(range(8)):
                raise ValueError("Retain all eight original proposal positions")
            path = RECEIPTS / f"block_{block}_{arm}.receipt.json"
            raw = path.read_bytes()
            receipt = json.loads(raw)
            wall = receipt["wall_seconds"]
            if type(wall) not in (int, float) or not math.isfinite(wall) or wall <= 0:
                raise ValueError("A genuine measured positive bank wall is required")
            if receipt["arm"] != arm or receipt["block"] != block:
                raise ValueError("Bank metadata identity differs")
            inputs[path.relative_to(ROOT).as_posix()] = digest(raw)
            banks.append({"arm": arm, "block": block, "matched4": block < 4,
                          "original_positions": len(rows), "eligible": sum(int(r["eligible"]) for r in rows),
                          "actual_call_wall_seconds": wall, "actual_call_wall_exact": str(Fraction(str(wall))),
                          "receipt_sha256": digest(raw), "candidate_ids": [r["id"] for r in rows],
                          "requested_configuration": receipt.get("requested_configuration"),
                          "observed_model": receipt.get("observed_model")})
    cohorts = []
    for scope, blocks in (("matched4", range(4)), ("all5", range(5))):
        for arm in ARMS:
            selected = [b for b in banks if b["arm"] == arm and b["block"] in blocks]
            wall = sum((Fraction(b["actual_call_wall_exact"]) for b in selected), Fraction())
            eligible = sum(b["eligible"] for b in selected)
            cohorts.append({"scope": scope, "arm": arm, "banks": len(selected),
                            "original_positions": sum(b["original_positions"] for b in selected),
                            "eligible": eligible, "cumulative_call_wall_seconds_exact": str(wall),
                            "mean_bank_wall_seconds_exact": str(wall / len(selected)),
                            "mean_bank_eligible_exact": str(Fraction(eligible, len(selected))),
                            "eligible_per_1000_cumulative_call_wall_exact": str(1000 * eligible / wall)})
    return banks, cohorts, inputs


def build(out):
    out = Path(out)
    note = ROOT / "docs/V06_REFINEMENT_AUTHORING_EFFICIENCY_001.md"
    if out.exists() or note.exists():
        raise ValueError("Preserve prior presentation artifacts; output must be new")
    banks, cohorts, inputs = prepare()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.findfont("Arial", fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#687782", "axes.labelcolor": "#243640",
        "text.color": "#243640", "xtick.color": "#243640", "ytick.color": "#243640",
        "figure.facecolor": "white", "savefig.facecolor": "white"})
    out.mkdir(parents=True)
    fig = plt.figure(figsize=(3.35, 1.9))
    ax = fig.add_axes([.155, .26, .81, .55])
    for arm, (label, color) in ARMS.items():
        b = [r for r in banks if r["arm"] == arm and r["matched4"]]
        ax.scatter([r["actual_call_wall_seconds"] for r in b], [r["eligible"] for r in b],
                   color=color, s=19, linewidths=.7, label=label, zorder=3)
        fifth = next(r for r in banks if r["arm"] == arm and not r["matched4"])
        ax.scatter([fifth["actual_call_wall_seconds"]], [fifth["eligible"]], marker="D",
                   facecolors="none", edgecolors=color, s=27, linewidths=.9, zorder=3)
        mean = next(r for r in cohorts if r["scope"] == "matched4" and r["arm"] == arm)
        ax.scatter([float(Fraction(mean["mean_bank_wall_seconds_exact"]))],
                   [float(Fraction(mean["mean_bank_eligible_exact"]))],
                   marker="+", color=color, s=60, linewidths=1.3, zorder=4)
    upper = math.ceil(max(r["actual_call_wall_seconds"] for r in banks) / 200) * 200
    ax.set(xlim=(0, upper), ylim=(-.3, 8.4), yticks=[0, 2, 4, 6, 8],
           xlabel="Actual author-call wall (s)", ylabel="Eligible proposals")
    ax.grid(axis="y", alpha=.15, lw=.5)
    ax.tick_params(length=3, pad=2)
    ax.xaxis.labelpad = 3
    ax.yaxis.labelpad = 3
    fig.legend(loc="upper center", bbox_to_anchor=(.56, 1.015), ncol=3, frameon=False,
               handlelength=.8, handletextpad=.25, columnspacing=.8)
    key = [plt.Line2D([], [], marker="o", color="#243640", lw=0, ms=3.5, label="Blocks 0–3"),
           plt.Line2D([], [], marker="D", mfc="none", color="#243640", lw=0, ms=3.5, label="Block 4"),
           plt.Line2D([], [], marker="+", color="#243640", lw=0, ms=5, label="Matched4 mean")]
    fig.legend(handles=key, loc="lower center", bbox_to_anchor=(.5, -.015), ncol=3,
               frameon=False, handlelength=.6, handletextpad=.25, columnspacing=.6)
    outputs = {}
    for ext in ("pdf", "png"):
        path = out / f"refinement_authoring_efficiency_v06.{ext}"
        fig.savefig(path, dpi=300)
        outputs[path.name] = digest(path.read_bytes())
    plt.close(fig)
    report = {"version": "v06_R2_authoring_efficiency_presentation_001", "banks": banks,
              "cohorts": cohorts, "input_sha256": inputs, "outputs_sha256": outputs,
              "renderer_sha256": digest(Path(__file__).read_bytes()), "geometry_inches": [3.35, 1.9],
              "font": "Arial9", "TRAIN_only": True, "TEST_accessed": False,
              "new_audit_or_experiment_or_model_or_oracle_calls": 0,
              "scope": "Descriptive fixed warm-seed authoring banks. Matched4 was preregistered; fifth retained. "
                       "Cumulative call-wall is the sum of observed bank session wall, not concurrent elapsed time, "
                       "candidate completion time, matched compute or model-population efficacy."}
    side = out / "authoring_efficiency_v06.json"
    side.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# V06 actual authoring efficiency: frozen receipt presentation", "",
        "This is a presentation of already audited R2 gate counts and original bank author-call wall receipts. "
        "It invokes no new audit, optimizer, oracle, programme evaluation or model call; no raw response or TEST is read. "
        "All five banks per arm remain. The preregistered first four matched banks are descriptive conditional cohorts, "
        "not independent model-population samples or equal-compute treatments.", "",
        "## Actual bank records", "",
        "Each call proposes eight original positions. Wall is measured once for the complete bank call; "
        "no candidate completion time is interpolated. Exact decimal receipt values are retained below.", "",
        "| Arm | Block | Matched4 | Eligible/original | Actual author-call wall seconds |",
        "|---|---:|---|---:|---:|"]
    for b in banks:
        lines.append(f"| {ARMS[b['arm']][0]} | {b['block']} | {b['matched4']} | {b['eligible']}/8 | {b['actual_call_wall_seconds']} |")
    lines += ["", "## Exact-denominator throughput", "",
        "Throughput = 1000 × eligible proposals / sum of actual call-wall seconds in the specified cohort. "
        "It counts genuine gate-eligible original proposals, not learned quality gain or fitted scalars. "
        "Decimal displays are rounded only here; the sidecar retains exact rational denominators and rates.", "",
        "| Scope | Arm | Eligible/original | Cumulative call-wall seconds | Mean bank wall seconds | Eligible per 1000 cumulative call-wall seconds |",
        "|---|---|---:|---:|---:|---:|"]
    for c in cohorts:
        wall = float(Fraction(c["cumulative_call_wall_seconds_exact"]))
        mean = float(Fraction(c["mean_bank_wall_seconds_exact"]))
        rate = float(Fraction(c["eligible_per_1000_cumulative_call_wall_exact"]))
        lines.append(f"| {c['scope']} | {ARMS[c['arm']][0]} | {c['eligible']}/{c['original_positions']} | {wall:.12f} | {mean:.12f} | {rate:.12f} |")
    lines += ["", "## Suggested caption and limits", "",
        "Eligible original proposals versus measured author-call wall in all five warm-repair banks. "
        "Filled circles show blocks0–3, hollow diamonds retain block4, and crosses mark preregistered matched-four "
        "bank means. Every bank proposes eight positions. Session wall is not candidate latency or concurrent elapsed time; "
        "these conditional descriptive ratios do not establish equal compute, served-model identity, scalar consistency "
        "or scheduling-quality superiority.", "",
        "Requested model is gpt-6.1-sol with ultra reasoning; served backend is recorded only as original receipt metadata "
        "and remains unknown when null. No response prose or programme AST enters this plot. "
        "R2 banks are batch proposal sessions, so throughput must not be equated to EoH's sequential refinement protocol.", "",
        "## Provenance", "",
        f"Original gate audit SHA: `{AUDIT_SHA}`. Renderer and all15 receipt byte hashes, bank IDs, requested configuration "
        "and original observed-model values are retained in the presentation sidecar. No source/data/audit is modified.", "",
        f"Output directory: `{out.relative_to(ROOT).as_posix() if out.is_absolute() else out.as_posix()}`.", "",
        f"Sidecar SHA: `{digest(side.read_bytes())}`.", "",
        "| Figure | SHA256 |", "|---|---|"]
    for name, h in outputs.items():
        lines.append(f"| {name} | {h} |")
    note.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "banks": len(banks), "cohorts": cohorts,
                      "sidecar_sha256": digest(side.read_bytes()), "note_sha256": digest(note.read_bytes()),
                      "outputs_sha256": outputs}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    build(parser.parse_args().out)
