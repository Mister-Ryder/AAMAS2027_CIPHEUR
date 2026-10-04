"""Render the common-CHILS deployment scope from final audited aggregates only.

This additive presentation does not replace the complete cold/warm figure bank.
Its fixed four families and eight series include every published native family,
joint-W, EoH-DSL, and the same-backbone Degree control. No scientific calculation
or program selection is performed.
"""
from pathlib import Path
from dataclasses import asdict
import argparse
import json
import build_performance_figures_v06 as base


FULL_RENDERER_SHA256 = "4f17c7c1ca8057a7f2061ece38689bd9c3520c65240267c6d2fbf4674fa43297"
FULL_RECEIPT = base.ROOT / "experiments/analysis/v06/performance_figures_v06_003_render_002/performance_figure_receipt_v06.json"
FULL_RECEIPT_SHA256 = "74db4251e376a5dd98d44fc01135a5dbae84c1ec2212f3eb49e689620aa13db7"
WARM_SERIES = (*base.SERIES[:5],
    base.Series("Degree_warm", "Degree / CHILS", "warm_CHILS", "Degree", base.GRAY, "h", "-.", False, 7.2),
    base.SERIES[6], base.SERIES[7])


def build(analysis_path, analysis_sha256, audit_path, out):
    out = Path(out)
    base.require(not out.exists(), "Use a new warm-presentation output directory")
    base.require(base.digest(Path(base.__file__)) == FULL_RENDERER_SHA256, "Original renderer bytes changed")
    base.require(base.digest(FULL_RECEIPT) == FULL_RECEIPT_SHA256, "Complete supporting figure receipt changed")
    analysis, audit, binding = base.load_bound_analysis(analysis_path, analysis_sha256, audit_path)
    inventory = base.input_group_inventory()
    original_groups = base.GROUPS
    base.GROUPS = tuple(g for g in original_groups if (g[0], g[1]) in base.MAIN_RECIPES)
    base.SERIES = WARM_SERIES
    base.HEIGHT = 1.90
    panels = base.panel_data(analysis, inventory)
    base.require(len(panels) == 4 and all(p["main_recipe"] for p in panels), "Preserve all four original main families")
    ylim = base.gain_limits(panels)
    plt = base.configure_plotting()
    original_finish = base.finish_figure
    current_panel = {}

    def finish_warm(fig, stem, destination):
        if stem.startswith("performance_gain_v06__"):
            stem = "performance_warm_gain_v06__" + stem[len("performance_gain_v06__"):]
            fig.axes[0].set_ylabel("Paired gain (%)", labelpad=3)
            joint = next(s for s in current_panel["panel"]["series"] if s["series"]["key"] == "joint_W_warm")
            counts = " / ".join(f'{p["gain"]["defined_contexts"]}/{p["gain"]["assigned_contexts"]}' for p in joint["points"])
            for text in fig.texts:
                if text.get_text().startswith("Defined Q pairs:"):
                    text.set_text("Joint W pairs: " + counts)
        elif stem == "performance_series_legend_v06":
            stem = "performance_warm_series_legend_v06"
        else:
            raise ValueError("Unexpected warm-presentation asset")
        return original_finish(fig, stem, destination)

    base.finish_figure = finish_warm
    out.mkdir(parents=True)
    outputs = []
    for panel in panels:
        current_panel["panel"] = panel
        result = base.draw_panel(plt, panel, ylim, out)
        result["gain_axis_scope"] = "Shared across all four fixed families; includes every warm/native estimate and interval, zero and negatives"
        result["deployment_scope"] = "Common CHILS initialization for every policy; native full-target comparators remain separate"
        outputs.append(result)
    legend = base.draw_legend(plt, out)
    receipt = {"version": "v06_common_CHILS_deployment_presentation_001",
        "script_sha256": base.digest(__file__), "original_renderer_sha256": FULL_RENDERER_SHA256,
        "input_binding": binding, "frozen_context_inventory_sha256": base.INVENTORY_SHA256,
        "complete_cold_warm_support_receipt": str(FULL_RECEIPT.resolve()),
        "complete_cold_warm_support_receipt_sha256": FULL_RECEIPT_SHA256,
        "complete_support_report": "docs/V06_PERFORMANCE_RESULTS_003.md",
        "targets": list(base.TARGETS), "fixed_main_recipes": [list(p) for p in base.MAIN_RECIPES],
        "series": [asdict(s) for s in WARM_SERIES], "fixed23_policy_metadata": audit["policies"],
        "all_four_arrays_and_coverage": panels, "rendered_panels": outputs, "legend": legend,
        "gain_metric": base.GAIN, "reference": "Full-target native CHILS seed1 at the corresponding nominal target",
        "scope": "Unified common-CHILS incumbent deployment; no cold policy curve in this main presentation",
        "no_TEST_winner_selection": True, "no_analysis_or_scientific_rerun": True,
        "stored_mean_CI_and_denominators_reused": True, "missing_joint_points_preserved": True,
        "no_incremental_LLM_quality_claim": True, "nominal_budget_curve_is_not_anytime": True,
        "original_full_series_figures_receipt_and_report_unchanged": True}
    path = out / "performance_warm_figure_receipt_v06.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {"out": str(out.resolve()), "main_panels": 4, "shared_legends": 1,
            "receipt_sha256": base.digest(path), "analysis_sha256": analysis_sha256}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--analysis-sha256", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.analysis, args.analysis_sha256, args.audit, args.out)))
