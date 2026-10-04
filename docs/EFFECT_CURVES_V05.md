# Frozen-program effect curves (v05)

These are descriptive, post-outcome analyses of unchanged v04 programs and completed immutable receipts. They do not introduce a new candidate, retrain a model, access an online oracle, or claim causal LLM superiority.

## What the LLM evidence supports

The offline assistant proposed typed structural feature–rule pairs. The TRAIN-selected joint program uses the neighborhood clique-cover feature. Its held-out complete-schedule quality exceeds the selected degree and rule-only controls on standard and dense/long populations. The selected free-synthesis program is slightly better on those same populations. Unequal candidate banks and one continuing assistant authoring session prevent a model-level or token-matched causal claim. Native published solvers remain stronger in the existing algorithmic comparison.

## Figures

`paper/figures/effect_curves_v05.pdf` has two complementary curve panels: complete-schedule paired gain over the selected rule-only program by instance size and resource regime on dense/long scheduling; and actual paired prefix reward gain versus eliminated-vertex fraction against degree, rule-only and free-synthesis on that same predefined population. The compact dense/long view is a post-outcome diagnostic, not a newly selected confirmatory comparison. The complete-schedule gain pools equal left/right assignment; it does not claim gain from tightening alone.

`paper/figures/heap_scaling_v05.pdf` gives the paired full-scan/heap CPU ratio curve for the identical frozen AST across all fresh populations. It has a separate execution question and does not imply quality improvement.

`paper/figures/effect_curves_all_populations_v05.pdf` retains every predefined standard, dense/long and C3 population, with both final gain and decision trajectories. No population is removed from the source evidence.

All fonts are Arial, at least 9 pt at the native 7-inch figure width. Controls retain color and line/marker shape; heap populations have a separate legend. Curves connect measured sizes without a fitted trend or invented intermediate experiments.

## Exact semantics

Reward ratios divide by each original context's best independently verified feasible complete reward in the original comparison pool, not a proven optimum. A plotted difference is 100 × (joint ratio − control ratio), measured in percentage points. The best reward is held fixed for the two policies in each paired difference.

The trajectory x-coordinate is 1 − |active after commitment| / |initially active|. Its y-coordinate is the sum of original graph weights of the recorded feasible prefix, normalized by the same original comparison denominator. The curve is a right-continuous step observation, sampled on 101 fixed fractions without interpolating reward across a deletion. Initial boundary commitments contribute their original weight. Every action and active-set count is replayed against the original graph. Per-action CPU timestamps were never logged; these are constructive decision trajectories, not anytime curves or learning convergence.

All four selected policies complete on all 456 contexts. All 1,368 primary-AST scan/heap pairs complete and have identical traces, selections and exact reward. CPU ratios use the median of three order-balanced repeats within a graph context; repeats are not treated as independent graphs. CPU ratios reflect execution engineering, rather than improved scheduling reward or improved LLM reasoning.

95% percentile intervals resample whole source clusters, preserving both sides of each intervention and all resource regimes sharing that source. The trajectory bootstrap uses the same cluster draws at every fraction. Its shaded bands are pointwise intervals, not simultaneous confidence bands. C3 size-specific curves have only three source clusters and must be interpreted cautiously.

## Complete paired gain by size

| Population | n | Contexts | Joint − degree (pp) | Joint − rule only (pp) | Joint − free synthesis (pp) |
|---|---:|---:|---:|---:|---:|
| Standard | 64 | 72 | +1.120 [+0.680, +1.557] | +0.573 [+0.199, +0.957] | -0.093 [-0.353, +0.172] |
| Standard | 128 | 72 | +0.779 [+0.571, +1.003] | +0.421 [+0.252, +0.602] | -0.046 [-0.171, +0.102] |
| Standard | 256 | 72 | +1.052 [+0.824, +1.255] | +0.614 [+0.426, +0.781] | -0.086 [-0.185, +0.009] |
| Dense / long | 64 | 72 | +0.521 [-0.688, +1.538] | +0.455 [-0.736, +1.520] | -0.233 [-1.135, +0.579] |
| Dense / long | 128 | 72 | +3.110 [+1.645, +4.506] | +2.959 [+1.480, +4.466] | -0.168 [-0.808, +0.437] |
| Dense / long | 256 | 72 | +1.303 [+0.758, +1.831] | +1.353 [+0.868, +1.868] | -0.095 [-0.552, +0.275] |
| C3 contacts | 64 | 6 | +1.579 [+0.000, +4.014] | +1.579 [+0.000, +4.014] | +0.025 [+0.009, +0.054] |
| C3 contacts | 128 | 6 | +0.519 [-0.802, +2.290] | +0.519 [-0.802, +2.290] | +0.146 [-0.002, +0.365] |
| C3 contacts | 256 | 6 | -1.910 [-3.084, -1.302] | -1.917 [-3.084, -1.302] | +0.122 [-0.015, +0.263] |
| C3 contacts | 512 | 6 | +1.903 [-1.319, +5.504] | +3.090 [+0.792, +4.561] | +0.406 [-0.111, +0.932] |

## Same-AST execution curve

| Population | n | Contexts | Mean context-median scan/heap CPU ratio (95% CI) |
|---|---:|---:|---:|
| Standard | 64 | 72 | 7.079 [6.899, 7.271] |
| Standard | 128 | 72 | 13.145 [12.887, 13.395] |
| Standard | 256 | 72 | 26.129 [25.727, 26.533] |
| Dense / long | 64 | 72 | 1.093 [1.054, 1.134] |
| Dense / long | 128 | 72 | 1.159 [1.131, 1.186] |
| Dense / long | 256 | 72 | 1.309 [1.255, 1.361] |
| C3 contacts | 64 | 6 | 5.611 [5.053, 6.702] |
| C3 contacts | 128 | 6 | 4.321 [3.959, 4.823] |
| C3 contacts | 256 | 6 | 3.539 [3.510, 3.590] |
| C3 contacts | 512 | 6 | 4.973 [3.870, 5.796] |

## Reproducibility and checks

Run `python scripts/build_effect_curves_v05.py` from a clone with the plotting dependencies. Archives are read directly without extraction. Source files and member SHA-256 receipts, all context-level paired gains, all 101-fraction trajectories, replayed raw action prefixes, exact final reward checks and plot metadata are in `experiments/analysis/v05/effect_curves.json`.

Independent graph/weight replay performed 230,283 checks across 1,824 completed schedules. All 1,368 heap pair ratios are recomputed from recorded CPU seconds and reconcile with saved pair ratios; all aggregate means match the earlier immutable-source v04 heap analysis to 1e−12. Every size-specific group retains equal left/right assignment. All trajectory endpoints reconcile with the complete-schedule paired quality differences to 1e−12.

No source archive, selected AST, solver result, previous analysis, paper section, or frozen-program selection is changed by this builder.
