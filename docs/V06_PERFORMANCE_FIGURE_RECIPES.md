# Fixed V06 performance figure recipes

This is an implementation plan fixed before reading any performance outcome. The builder uses the Data Visualization skill's static scientific-figure workflow. It reads only a root-authorized **final `analysis.json`**, its linked zero-error independent audit, and the already frozen 302-context metadata inventory. It never reads a run archive, raw/compact assignment stream, graph, AST, author response, live progress, or held-out candidate output. It performs no solver, programme, LLM, bootstrap, selection, or additional experiment.

## Invocation and source gate

```text
python scripts/build_performance_figures_v06.py --analysis FINAL_ANALYSIS_DIRECTORY/analysis.json --analysis-sha256 ROOT_PROVIDED_FINAL_ANALYSIS_SHA256 --audit LINKED_FINAL_INDEPENDENT_AUDIT.json --out NEW_FIGURE_DIRECTORY
```

The expected final analysis SHA is mandatory and must come from root after the final statistical analysis. Existing output directories are refused. The builder checks the final analysis version/source, its exact two registered configuration hashes, 52,548 assignments, bootstrap parameters 2,000/261004, and no-TEST-selection/family-separation flags. It binds the audit report bytes to both analysis audit fields, requires zero errors, and checks the independently reviewed verifier/helper source closure, original archive and audited-row hashes, and 302/23/52,548/three-target constants. The linked audit is a provenance input; neither its raw source assignments nor the run archive are reopened.

The outcome-free metadata inventory has SHA `f4d204d75ee2eb9e05b40405ae25bd47a0b4c3714df27a28a0b4930b857cc917`. This fixed file supplies the complete family list, source denominators, context identities, and graph-size inventory. It contains no optimized reward used by the figure builder. C3 `family=None` is preserved literally instead of inventing a new scientific family or pooling its two exploratory models.

## All source groups, fixed before outcomes

| Population / family | Assigned contexts | Source/pair clusters |
|---|---:|---:|
| `fresh_standard_balanced / standard_balanced` | 36 | 18 |
| `fresh_standard_ground_scarce / standard_ground_scarce` | 36 | 18 |
| `fresh_standard_satellite_scarce / standard_satellite_scarce` | 36 | 18 |
| `fresh_dense_long_balanced / dense_long_balanced` | 36 | 18 |
| `fresh_dense_long_ground_scarce / dense_long_ground_scarce` | 36 | 18 |
| `fresh_dense_long_satellite_scarce / dense_long_satellite_scarce` | 36 | 18 |
| `WDP / WDP_1xx` | 5 | 5 |
| `WDP / WDP_2xx` | 6 | 6 |
| `WDP / WDP_4xx` | 6 | 6 |
| `WDP / WDP_5xx` | 4 | 4 |
| `WDP / WDP_6xx` | 4 | 4 |
| `UAI_Segmentation / Segmentation` | 3 | 3 |
| `UAI_Grids_CHILS64 / Grids` | 10 | 10 |
| `C3_interval_exploratory / null` | 24 | 12 |
| `C3_legacy_exploratory / null` | 24 | 12 |

All 15 groups generate independent gain panels. The **four main recipes are fixed** as standard-balanced, dense-long-ground-scarce, WDP 4xx, and exact-64-bit UAI Grids. They represent preselected problem types, not the best-performing family. All other families and both previously exposed C3 models remain available; none is silently dropped for a negative or all-null result.

## Exactly eight fixed curves

| Display | Analysis track | Frozen aggregate identity |
|---|---|---|
| CHILS (3 seeds) | `native` | `native:CHILS` |
| CHILS-ILS (3) | `native` | `native:CHILS_ILS` |
| M2WIS (3 seeds) | `native` | `native:M2WIS` |
| Struction | `native` | `native:Struction` |
| WeightedBR | `native` | `native:WeightedBR` |
| Joint W / Degree | `cold_Degree` | `joint_W` |
| Joint W / CHILS | `warm_CHILS` | `joint_W` |
| EoH-DSL / CHILS | `warm_CHILS` | `published_EoH_DSL_quality` |

The y metric is the existing `percent_gain_exact` interval from `contrast_budget_curves`, scope `population_family`, contrast `versus_fixed_full_CHILS_seed1`. The renderer copies its stored floating-point mean and `ci95` exactly; it preserves the rational mean string in the receipt. It neither recomputes bootstrap intervals nor averages interval endpoints. Native seeds were already averaged inside each source by the analyzer, and the four frozen policy identities were already averaged inside each context. The builder does not pick an identity or seed by TEST reward.

The reference is always full-target native **CHILS seed 1**, already fixed in analysis. The CHILS plotted curve is its actual three-seed average relative to that fixed seed-1 reference. It is not forced to zero. The horizontal zero guide represents equality to the reference. Missing/unsupported/error member groups yield null paired estimates, not zero reward.

## Geometry, missingness, and scales

Every data panel is a separate vector PDF and 300-dpi PNG at **3.35 × 2.15 inches**, Arial **9 pt** at its native printed width. The common eight-series legend is an independent **7.0 × 0.52 inch** PDF/PNG with 9-pt text, suitable for placement beneath paired/minipage plots. It retains all methods even when a source group's entire curve is null.

The design uses the established blue `#176B9B`, purple `#71559C`, orange `#D36B32`, and gray `#687782`; line/marker shapes distinguish methods. Joint warm W uses a small filled blue square, while overlapping cold/EoH markers are larger and transparent. No jitter changes measured coordinates. No legend chooses or highlights a winning result.

Budget x coordinates are exactly **0.1, 1, and 5 nominal wall seconds**, on a logarithmic axis. Three-point lines compare registered budgets; they are not learning curves or native anytime trajectories. Null values create real gaps in the line. The footer shows missing-series counts at every original target and the range of defined quality-pair counts. The title's `N/S` are assigned contexts/source clusters, not successful observations. Each curve's exact context/source coverage and valid-target count remain in the receipt.

The four main panels share a y range computed from zero and **all eight curves' means and interval endpoints across those four fixed groups**. Other family panels use separate complete ranges and record that scope in the receipt. Every range includes zero, all observed negative estimates, and all interval endpoints; no favourable axis cut or clipped negative gain is permitted. Different supplementary family scales must be acknowledged when comparing their magnitudes.

## Additional CPU-versus-gain panels

The same four fixed main recipes also produce separate CPU-versus-gain panels. x is the stored conditional `standalone_cpu_seconds` mean/interval from `role_budget_curves`; y is the existing fixed-reference paired gain. All three target identities remain ordered and recorded; missing x or y creates a gap. Horizontal and vertical segments preserve the original asymmetric intervals, including cases where the point lies outside an interval. No Pareto frontier or interpolated optimum is computed.

**Cost and quality coverage can differ.** Known costs include measured failed attempts, whereas quality requires every requested seed/policy member and the fixed reference. These axes can therefore summarize different conditional subsets. This qualification is printed inside every CPU panel; exact cost and quality context/source/member counts are retained per target. These plots illustrate registered operating points, not matched-end-to-end compute or Pareto superiority. Nominal C++/Python internal wall targets, phase startup, and actual CPU are not interchangeable.

The warm standalone CPU statistic already charges each policy the full common CHILS initializer plus its own repair. The plot does not amortize shared initialization over policies. Shared graph-load and phase timing scopes remain in the analysis/receipt; no authoring/token cost is inferred from the execution point.

## Files and receipt

The new output directory contains:

- 15 `performance_gain_v06__POPULATION__FAMILY.pdf/png` pairs;
- four `performance_cpu_gain_v06__POPULATION__FAMILY.pdf/png` pairs;
- `performance_series_legend_v06.pdf/png`;
- `performance_figure_receipt_v06.json`.

The receipt binds every output hash to the approved analysis/audit/archive/rows/source/config/inventory hashes. It records all 15 groups, all eight series, all three target values including nulls, direct JSON pointers to each original statistic, exact/numeric means, complete interval endpoints, source counts, successful/returned/assigned member counts, status counts, cost measurement counts, valid-target counts, frozen 23-policy metadata and seed/winner origins, and precise x/y interpretation.

At actual construction the builder verifies plotted line coordinates and every horizontal/vertical CI segment against the loaded arrays. A single bounded rendered check rejects text outside the native panel and any visible font below 9 pt. It does not crop away labels or alter canvas size to pass. Root can place the separate panels through LaTeX; this task does not modify `main.tex`.

## Implementation status

The CLI/source is prepared without reading final performance data. Only a syntax/CLI check is needed at this stage; there is no additional audit or broad test suite. Scientific rendering, numeric artifact receipts, and actual-data visual inspection are deferred until root supplies the final analysis SHA and linked zero-error audit. No current efficacy, baseline advantage, confidence interval, coverage value, or acceptance claim is made here.
# Final audit-backed rendering

The authorized analysis SHA256 is `839324710784ba71ee40c25ea199b527ff346fb7ec1209f97756ed2d9513aaf9`; its linked independent audit SHA256 is `db7209ad60c4d2f1cff07ec50b2bf26fd5d473153c56d809ff416f6781de22d6`. The complete rendering is saved in `experiments/analysis/v06/performance_figures_v06_003_render_002`, with receipt SHA256 `74db4251e376a5dd98d44fc01135a5dbae84c1ec2212f3eb49e689620aa13db7` and final builder SHA256 `4f17c7c1ca8057a7f2061ece38689bd9c3520c65240267c6d2fbf4674fa43297`.

All 15 fixed family gain panels, four fixed-main CPU/gain panels, and the separate shared legend were rendered. The four main gain PDFs and legend were copied to `paper/figures`; all other panels remain available in the analysis output directory. Four main PNGs and the shared legend were inspected for actual visibility after rendering. Stored artist coordinates and interval endpoints are checked directly against their linked aggregate arrays during construction.

The first presentation attempt remains as partial output in `performance_figures_v06_003`: Matplotlib's automatic outer tick text triggered the bounds guard before the last panel. Pruning those automatic outer tick labels corrected presentation; no source cohort, program, statistic, interval, objective, or analysis execution changed. The final scientific interpretation and complete per-family gain/CPU/coverage tables are in `docs/V06_PERFORMANCE_RESULTS_003.md`. The results do not establish a general scheduling-quality or speed advantage for joint-W.
