# V06 held-out figure recipes: prepared before outcome reads

This file declares the recipes before any actual analyzed held-out report is opened. It describes prepared plotting code, not findings or rendered figures. `scripts/build_heldout_figures_v06.py` does not execute a programme, scorer, scheduler, solver or oracle, and does not read raw archives or live result directories. No preparation tests, actual data plotting or paper/main edits are requested or performed here.

## Input and invocation

Root supplies the final `v06_R2_EoH_heldout_mechanism_analysis_001` report and its exact authorized SHA256. The constructor checks that digest before interpreting the report. It requires the prepared analyzer/config bindings, two positive-check/zero-error independent audit bindings, the original 31 identities/72 states/six variants and no reexecution/selection/oracle calls. It opens only the report's hash-bound `_compact.json`, verifies its metadata/frame and original counts, and uses the existing analyzed summaries. It never opens a canonical raw TEST archive. A copied final report may refer to an unavailable old host path; only a same-named compact beside the report with the exact bound digest may substitute.

The prepared analyzer SHA is `5acedcb11f0a407e377b98a24162ae9f1864a0e275faa5a28f59ccb323fb54d2`. The final analysis digest is unknown until root completes and freezes that analysis. A different analyzer schema/source requires an explicit new preparation binding; a guessed/current unfinished report is not accepted.

```powershell
python -B scripts/build_heldout_figures_v06.py --analysis "FINAL_HELDOUT_ANALYSIS_JSON" --analysis-sha256 "ROOT_FINAL_ANALYSIS_SHA256" --out "NEW_FIGURE_DIRECTORY"
```

Optional `--all-identities` additionally renders the two fixed all31 supplementary panels. It does not change the main21 panels or discard anything. Existing output directories are refused. Dependencies are Matplotlib and an available Arial font; missing Arial fails instead of silently changing typeface. Actual constructor checks compare rendered collection/connector arrays to the exact-derived plotted coordinates; no additional research experiment or resampling is involved.

## Fixed main21 identity recipe

The main subset uses roles, before inspecting outcomes: 4 `proposed_witness_joint`, 12 `nonguarded_quality_comparator` (4 witness, 4 relations, 4 objective), 4 `nonguarded_published_quality_baseline`, and 1 `classical_Degree`. Thus all four R2 authoring blocks remain individual dots in every role, and all four EoH pipeline identities remain. The remaining 8 enumerated controls and 2 TRAIN-selected controls are always retained in the sidecar and optional all31 panels. No gate, fit, quality, effect size or missingness selects the main subset.

Duplicate deployment ASTs remain separate requested identity positions at their true coordinates. No jitter fabricates separation. EoH shared-seed winners keep their original origin and source ID; four coincident pipeline outputs are not four newly learned programmes or independent model draws. W joint and W quality have distinct symbols despite their shared purple color; their selector/framework roles are not pooled. Authoring blocks are never averaged into one graphical point.

## Two separate panels

| Output stem | Horizontal coordinate | Vertical coordinate |
|---|---|---|
| `heldout_strict_alias_movement_v06` | Actual strict scalar fit | Actual base-alias strict scalar fit |
| `heldout_pair_joint_movement_v06` | Strict-preservation joint correctness | Strict-reversal joint correctness |

Each original observation is a hollow marker. The corresponding full five-rename mean is a smaller solid marker, so an unmoved point retains a visible hollow ring. Thin connectors join only identities with both complete coordinate points. Axes always span 0–100%; the faint diagonal denotes equal coordinate values, not a regression. A point is absent if either coordinate is null, and each panel explicitly shows assigned n and missing coordinate-point counts for original/mean. A zero-denominator or missing metric is never plotted at zero.

Strict and base-alias coordinates use `full_members_mean_exact` from each original mechanism summary. Their rename coordinates use the existing `five_rename_source_bootstrap` collapsed-query `all5_mean_fit` exact statistic, verified equal to the exact mean of all five full per-variant means with unchanged denominators. No CI is averaged or reestimated.

The paired panel uses each variant's existing `pair_categories.strict_preservation/strict_reversal.joint_correctness.full_members_mean_exact`. Both original endpoint predictions must pass. Its solid point is the exact equal-five mean of those five existing complete per-variant values; assigned category denominators must be unchanged, and every required rename must be measured. No observed-only mean fills a missing variant. Tie-both, strict/tie transitions and unknown intervals remain separate analyzed categories and are not relabeled as reversal failures. No endpoint, permutation or repeated AST becomes a new independent sample.

## Style, assembly and complete sidecar

Each panel is an independent 3.35 × 2.15 inch PDF vector file and 300 dpi PNG, with Arial 9 pt and white background. The catalogue palette is purple `#71559C` for W, blue `#176B9B` for R, gray `#687782` for O, orange `#D36B32` for EoH, and ink `#243640` for Degree. Symbols distinguish W joint/W quality, R, O, EoH and Degree. Optional extra controls use gray distinct symbols. There is no dense explanatory paragraph or embedded multi-panel layout; LaTeX supplies panel letters/caption and assembles the native-width files. Shrinking below native width also shrinks the stated type size.

`heldout_figure_arrays_v06.json` contains all31 identities, original and all five per-metric exact numerators/denominators/fractions, full rename means and nulls, main membership, source IDs, original role/block/AST/origin metadata, dependent duplicate-AST groups and EoH origin counts. It also records the exact analysis/compact hashes, full audit/protocol/root/source provenance metadata, plotted coordinates/IDs, missing counts, connectors, output hashes, figure code/recipe hashes and geometry. Rendering assertions are mapping checks, not a second scientific audit. Complete normal/error/null coverage and causal/statistical limits remain in the authorized analysis; these two mechanism panels do not claim scheduling superiority, independence or accepted-paper guarantees.

This recipe is prepared only. Actual sidecar numbers, tables and panels are created solely after root invokes the command on the frozen final analysis.
