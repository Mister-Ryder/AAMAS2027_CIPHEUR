# v03 quantitative analysis: development and completed evaluation

The completed archives support a mechanism result and a fixed-program compilation result. They do not establish a general advantage of guided generation. The final deterministic enumeration has higher validation quality than the primary guided program. In the original rollout evidence bank, the 64 contradictory self-loop requirements arise entirely from diagnostic probes and the non-probe quotient is already acyclic. This scope does not rule out aliases or contradiction in an extended census.

This report is generated from the development, mechanism, discovery, scalability, original-bank relevance and unbounded-transfer archives, plus completed `holdout_cooperative_003.tar.gz` and `transfer_cooperative_003.tar.gz`, with the newer `frozen_joint_001.json`. Numerical provenance, full precision, per-family summaries, and archive SHA-256 hashes are in `experiments/analysis/v03/summary.json`. Reproduction: `.venv/Scripts/python.exe scripts/build_result_figures_v03.py`. No archive is extracted or modified. The final cooperative003 section below retains all 840 held-out and 216 transfer contexts.

## Units and uncertainty

Quality is the arithmetic mean of per-context schedule value divided by the saved floating MILP reference upper value. These references are not exact rational certificates. Left and right graph contexts stay together. Percentages in this report are quality multiplied by 100; differences are percentage points (pp).

Intervals use 2,000 percentile bootstrap replicates, fixed random seed 20261003, and a nominal 95% level. Temporal samples cluster by the shared generator seed across all three resource regimes. C3 samples cluster by the disjoint source block/pair. The temporal/C3/probe mixture is retained by stratified resampling. Dense/long-contact transfer has its own stratum, clustered by source seed across regimes. Runtime first takes the median of three repetitions for each backend and context, then the median of paired context ratios. It is not a ratio of pooled means.

These intervals measure sensitivity to sampled instances conditional on the saved programs and data design. There is one independently authored candidate bank per assistant arm, so they do not measure model-level synthesis variation. The prefix curves are deterministic selections from these saved banks and carry no generation confidence interval.

## Evidence acquisition and repair

The mechanism archive contains 62 training pairs (20 probes and 42 non-probes), assessed under three acquisition conditions. Each condition uses rollout anchoring. The uniform condition randomizes the challenger and query order; it is not an unanchored acquisition control. R and P denote certified reversal and preservation relations.

| Acquisition condition | All pairs: R / P / total | Non-probe pairs: R / P / total | Attempts, all | Expanded nodes, all |
|---|---:|---:|---:|---:|
| Ranked, clique upper | 26 / 25 / 51 | 2 / 17 / 19 | 172 | 52,355 |
| Uniform, clique upper | 14 / 44 / 58 | 2 / 18 / 20 | 170 | 52,377 |
| Ranked, weight-sum upper | 24 / 12 / 36 | 0 / 4 / 4 | 176 | 84,138 |

On the 42 non-probe pairs, the mean relations per pair are 0.452381 [0.142857, 0.810119] for ranked/clique, 0.476190 [0.166667, 0.833333] for uniform/clique, and 0.095238 [0, 0.190476] for ranked/sum. The paired ranked/clique minus ranked/sum difference is +0.357143 [0.047619, 0.714286]. The ranked/clique minus uniform/clique difference is −0.023810 [−0.071429, 0]. Thus these saved data support the stronger bound's certificate yield, but not superior yield from ranking challengers.

Ranked/clique non-probe certificates split as C3: 0 R / 4 P; balanced: 0 R / 4 P; ground-scarce: 2 R / 3 P; satellite-scarce: 0 R / 6 P. The probes supply 24 R / 8 P. Raw counts are descriptive; neither total probes nor pooled probe quality estimates natural scheduling performance.

| Representation / population | Specifications | Quotient classes | Unique strict arcs | Self-loop strict requirements | Acyclic |
|---|---:|---:|---:|---:|---|
| Base, all | 51 | 80 | 50 | 64 | No |
| Base, probes only | 32 | 20 | 20 | 64 | No |
| Base, non-probes only | 19 | 60 | 30 | 0 | Yes |
| Repaired, all | 51 | 100 | 50 | 0 | Yes |

The fixed four-feature catalogue has additive standalone costs: neighborhood edge count 6,181; neighborhood edge-minimum sum 18,229; neighborhood clique cover 12,517; neighborhood greedy value 6,997. The exact master evaluates all 16 subsets and selects edge count at cost 6,181, in one repair round. Its optimality scope is this finite catalogue, fixed evidence, and additive standalone feature cost. It does not prove global optimality of the subsequently selected full feature–rule program or of costs with shared updates.

## Frozen generation and selection

The authoritative primary freeze is `experiments/discovery/v03/frozen_joint_001.json`, which supersedes the archive's original minimum-interface selection. The primary guided program is `g05_diminishing_pair_discount`; `g03_density_adjusted_weight_pressure` is now the minimum-interface ablation.

There are 24 candidates per guided, free, rule-only, and enumeration bank, plus one baseline assessment: 97 assessments on 124 validation contexts/62 pairs at n ≤ 128. These contexts comprise 40 probes, 72 temporal contexts, and 12 C3 contexts. Guided, free, and enumerated programs share the acyclic representation and consistency ≥ 0.75 gates, followed by whole-program quality minus 0.002 normalized compiled-work selection. Rule-only remains a comparator with its different consistency scope.

Consistency is a score-ranking fraction over the 36 strict side requirements from 18 seed specifications. It is not the frequency of actually choosing either candidate during scheduling.

| Frozen selection | Seed consistency | Mixed validation quality (%) | Mean compiled work / context | Features |
|---|---:|---:|---:|---:|
| Guided g05 | 35/36 = 97.2222% | 99.322024 | 51,820.919355 | 2 |
| Free free_04 | 34/36 = 94.4444% | 99.035743 | 47,451.112903 | 1 |
| Rule only | 4/36 = 11.1111% | 99.416780 | 43,971.040323 | 0 |
| Enumeration, final | 35/36 = 97.2222% | 99.438999 | 46,915.959677 | 1 |
| Guided, no cost g18 | 36/36 = 100% | 99.865547 | 6,136,542.467742 | 2 |
| Guided, minimum interface g03 | 34/36 = 94.4444% | 98.923889 | 40,394.491935 | 1 |

The guided, free, and rule-only winners are unchanged at prefixes 8, 16, and 24. Enumeration improves from 99.348018% at prefix 8 (`enum_edge_count_2`) to 99.438999% at 16 and 24 (`enum_edge_min_2`). There is no observed guided gain as prefix budget increases in this single bank.

| Population | Contexts / clusters | Guided quality, 95% CI (%) | Free quality, 95% CI (%) | Enumeration quality, 95% CI (%) |
|---|---|---|---|---|
| Temporal | 72 / 12 shared seeds | 99.210166 [98.985111, 99.437185] | 98.577733 [98.067712, 99.024739] | 99.392628 [99.183336, 99.586686] |
| C3 | 12 / 6 source blocks | 97.733255 [96.158137, 99.216431] | 98.569607 [97.811739, 99.407198] | 97.847222 [96.259886, 99.322709] |
| Non-probe, combined | 84 / 12 seeds + 6 blocks | 98.999179 [98.698437, 99.304621] | 98.576572 [98.150191, 99.000839] | 99.171856 [98.882135, 99.461890] |

All three have 100% quality on the 40 probes; the pooled mixed means are therefore higher than the non-probe means. The paired mixed-validation guided-minus-free difference is +0.286282 pp [−0.045098, +0.637681]; guided-minus-enumerated is −0.116975 pp [−0.289058, +0.046235]. On non-probes those differences are +0.422606 pp [−0.068706, +0.928682] and −0.172677 pp [−0.418789, +0.056070]. These are descriptive validation comparisons after selection, not unbiased test conclusions.

Removing the cost penalty selects g18, increasing mixed validation quality by 0.543522 pp while raising mean work from 51,820.919355 to 6,136,542.467742. The paired quality difference is 0.543522 [0.376885, 0.719666] pp in favor of no-cost. The minimum-interface ablation is cheaper but loses 0.398135 [0.149927, 0.651625] pp on the mixed validation set. Low and high penalties (0.0005 and 0.008) retain g05. The natural-validation-only ablation selects g12, whose actual non-probe mean is 99.301669%; the corresponding mixed mean is 99.087054%, so the two denominators must not be interchanged.

The parent session verified model `gpt-6.1-sol` with reasoning effort `ultra`; the authoring agents inherited the parent. The saved receipt records one assistant generation call per arm and zero external API calls. Token counts are unavailable. Total saved candidate assessment task time is 4,202.434538 seconds; this sum is not generation latency or wall-clock duration under parallel execution.

## Compilation runtime

This experiment assesses the fixed `structural_runtime` rule, using a neighborhood edge-minimum sum and the score `weight - 0.6*conflict_weight + redundancy/max(1, degree)`. It does not benchmark each proposal chosen by discovery. All 150 non-probe contexts / 75 pairs have identical reference-versus-compiled selection traces and feasible schedules. There are three runs per backend/context, with execution order alternated.

| Contacts | Contexts | Median paired time speedup, 95% CI | Median paired work reduction | Median reference / compiled seconds |
|---:|---:|---|---:|---|
| 32 | 24 | 1.101901 [1.086461, 1.105058] | 3.190298 | 0.019473 / 0.017693 |
| 64 | 30 | 1.205407 [1.198696, 1.209942] | 5.793580 | 0.079110 / 0.065153 |
| 128 | 30 | 1.359405 [1.353292, 1.370375] | 10.593458 | 0.327675 / 0.240901 |
| 256 | 30 | 1.722255 [1.688213, 1.743243] | 20.324298 | 1.703064 / 0.994917 |
| 512 | 30 | 2.440890 [2.432745, 2.446077] | 39.932077 | 9.576590 / 3.931775 |
| 1,024 | 6 | 4.445563 [4.404667, 4.607665] | 50.993466 | 18.693501 / 4.244031 |

The 1,024 point contains only C3 and three source blocks. The smaller sizes mix C3 and three temporal regimes; the curve does not establish a common-family scaling law. Work reduction and wall-time speedup are separate quantities. Initialization/update/query work shares at n=512 are 3.5011% / 1.9219% / 94.5770%, and at n=1,024 are 31.7969% / 17.9484% / 50.2547%; they are ratios of summed work, not average per-context fractions.

The archived development screen records Python 3.11.17, Linux 5.15, and eight workers. The mechanism timing archive does not identify CPU hardware. Retain this execution limitation in reproducibility materials; do not generalize the observed speedup to other hardware or all frozen programs.

## Large development stress screen

`scalability_001` contains 56 contexts / 28 pairs: temporal n=1,024 and 2,048, and C3 n=2,048 and 4,096. It evaluates existing baselines, not the primary frozen v03 program. All schedules are graph-feasible. Fifty floating MILP runs have solver status 0; six have status 1.

| C3 size | Contexts | MILP status 0 / 1 | Saved MILP relative gap range | Weighted-conflict mean (%) | v02 joint mean (%) | Local-search mean (%) | MILP incumbent mean (%) |
|---:|---:|---:|---|---:|---:|---:|---:|
| 2,048 | 4 | 2 / 2 | 0–0.00432265 | 94.3391 | 91.6560 | 97.0379 | 99.8670 |
| 4,096 | 4 | 0 / 4 | 0.26331301–4.90868585 | 94.7753 | 89.3165 | 96.6926 | 34.8939 |

These percentages all use the saved floating upper denominator. The very weak C3 n=4,096 MILP incumbent coverage limits interpretation; it cannot be reported as an optimal-quality benchmark. Local search has a median saved runtime of 1.2668 seconds there, versus 38.1488 seconds for weighted conflict and 50.7413 seconds for v02 joint. Its saved time and configured two-second cap do not guarantee the same amount of work across instances. The complete per-family stress table and cluster intervals are retained in the JSON rather than spending a main-paper figure on a screen that omits the frozen proposed method.

## Actual-next-action relevance on the original bank

`relevance_001` audits eight programs on the 51 acquired training specifications / 102 side requirements. Each reference and chosen-completion solve has a 1,000 expanded-node limit. Oracle labels are offline diagnostics and are not used for selection or deployment. Regret is the difference between the best residual completion and the completion constrained to the program's actual next action, at a saved boundary that its rollout reaches. It includes actions that escape the designated pair.

For each audited action, the reference lower minus chosen-completion upper gives a nonnegative regret lower bound, while reference upper minus chosen-completion lower gives an upper bound. The table gives the mean of these bounds in weight units, not a 95% confidence interval. The JSON separately contains clustered uncertainty for each mean endpoint. These are conditional on reachable boundaries; missing regret for unreachable boundaries is not assigned zero.

| Program | Reachable / 102 | Escape among reachable | Consistent actual pair choices / actual pair choices | Mean regret bound, reachable | Positive / zero / unresolved regret |
|---|---:|---:|---:|---|---:|
| Guided g05 | 88 / 102 | 88 / 88 | 0 / 0 | [4.409091, 5.161932] | 4 / 83 / 1 |
| Free | 88 / 102 | 64 / 88 | 24 / 24 | [0.045455, 0.798295] | 2 / 85 / 1 |
| Rule only | 88 / 102 | 88 / 88 | 0 / 0 | [0.045455, 0.798295] | 2 / 85 / 1 |
| Enumeration | 88 / 102 | 88 / 88 | 0 / 0 | [0.045455, 0.798295] | 2 / 85 / 1 |
| Minimum interface g03 | 88 / 102 | 87 / 88 | 1 / 1 | [0, 0.752841] | 0 / 87 / 1 |
| No cost g18 | 86 / 102 | 80 / 86 | 6 / 6 | [0, 0.706395] | 0 / 85 / 1 |
| Natural validation g12 | 86 / 102 | 84 / 86 | 2 / 2 | [0.825581, 1.595930] | 10 / 75 / 1 |
| Weight anchor | 102 / 102 | 0 / 102 | 60 / 102 | [6.409314, 7.058824] | 64 / 37 / 1 |

Each primary program's 88 reached requirements comprise 64 probe and 24 non-probe requirements. All 64 guided probe actions escape the pair but have exact zero regret. Therefore escape is not itself a failure. On the 24 reachable non-probe requirements, guided mean regret lies in [16.166667, 18.927083] with four certified positive, nineteen certified zero, and one unresolved; free, rule-only, and enumeration each lie in [0.166667, 2.927083] with two positive, twenty-one zero, and one unresolved. Twenty-three of these twenty-four regrets have exact reference and chosen-completion values. This audit supplies a negative action-level result for guided on the original certificate-selected bank.

The saved aggregate escape fractions (e.g., guided 98/102) include counterfactual rankings at unreachable boundaries. They must not be labeled actual executed choice frequencies. Likewise, the four saved guided pair choices are all at unreachable boundaries; guided has zero actual pair choices at reached boundaries in this bank. Score consistency (35/36 seed requirements or a separate 51-specification ranking audit) cannot establish actual-next-action quality.

## Unbounded dense/long-contact transfer: supplementary only

`transfer_001` is complete with 216 contexts / 108 pairs, containing 36 source seeds shared across three resource regimes. There are 72 contexts at each of n=64, 128, and 256. These are new seeds, a horizon of 0.18n, and durations up to 48 rather than the primary generator's 1.8n horizon and maximum duration 12. The saved freeze hash matches `frozen_joint_001.json`; selection was forbidden. All nineteen methods return schedules for all 216 contexts, and all returned schedules are graph-feasible. All saved floating MILP statuses are 0 with reported zero gap.

The table retains this unbounded run's own cost scope. It must not be pooled with five-CPU-second bounded002 outcomes. Because coverage is 216/216 for every method here, completed-context and zero-normalized all-context means coincide.

| Program / method | Quality, 95% cluster CI (%) | Median saved wall seconds | Mean compiled work |
|---|---|---:|---:|
| Guided g05 | 89.89742 [88.65290, 91.09636] | 0.577544 | 1,195,526.037037 |
| Free | 79.37512 [76.31730, 82.41929] | 0.543913 | 1,171,926.879630 |
| Rule only | 93.94712 [93.15439, 94.68491] | 0.054337 | 77,438.111111 |
| Enumeration | 89.73313 [88.55185, 90.90405] | 0.570218 | 1,194,237.805556 |
| Minimum interface g03 | 93.83499 [92.93576, 94.74795] | 0.171130 | 681,555.555556 |
| No cost g18 | 98.23706 [97.80298, 98.62182] | 0.361532 | 3,673,256.953704 |
| Natural validation g12 | 89.86323 [88.26258, 91.39859] | 0.063358 | 269,320.032407 |
| Weighted-conflict baseline | 93.90680 [93.06089, 94.69272] | 0.054489 | 77,514.898148 |
| v02 joint baseline | 89.73313 [88.55185, 90.90405] | 0.569436 | 1,194,237.805556 |
| Local search | 98.94252 [98.64193, 99.19996] | 0.000559 | Not recorded |
| HiGHS incumbent | 100.00000 [100, 100] | 0.022782 | Not recorded |

The paired guided-minus-free difference is +10.522304 pp [7.658964, 13.409226], but guided-minus-rule is −4.049700 pp [−5.224595, −2.863129], guided-minus-minimum-interface is −3.937569 pp [−5.087139, −2.748252], and guided-minus-local-search is −9.045098 pp [−10.226907, −7.883852]. Guided-minus-enumeration is +0.164291 pp [−0.643421, +0.906602]. These saved unbounded transfer data support a guided/free difference but not a general guided advantage over other comparators.

Guided transfer quality is 91.70784% at n=64, 90.54697% at 128, and 87.43746% at 256; its median wall costs are 0.095874, 0.577544, and 2.914147 seconds respectively. Its mean work at n=256 is 2,933,718.236111. Regime means are balanced 90.05633%, ground-scarce 88.61963%, and satellite-scarce 91.01630%. Per-size and per-regime CIs for every method are in the JSON.

The independently budgeted offline evidence query covers 72 transfer pairs and certifies 43 relations: 10 reversals and 33 preservations; 58 attempts have unresolved bounds. The combined base quotient has 172 classes, 86 arcs, and zero self-loop requirements and is acyclic on these observed specifications. There are 86 strict side requirements. Guided score consistency is 66/86 (76.7442%), versus free 50/86 (58.1395%), rule-only 60/86 (69.7674%), and enumeration 64/86 (74.4186%). All 86 saved boundaries are reached by these four programs. Guided chooses either designated pair member in 8/86 cases and all eight choices are consistent; free chooses a member in 45/86 and 28 are consistent. These pair statistics do not overturn the schedule-quality comparison.

## Descriptive diagnosis of g05 and its frozen controls

This analysis explains saved behavior; it is not a proposal-selection exercise. No program, AST, data, evidence label, or freeze is changed after observing transfer outcomes. Final primary plots will use cooperative003, not bounded002 or the old unbounded test. The expanded alias census has not certified natural necessity: its 200 queries are unresolved, so it cannot replace the diagnostic necessity witness with a certified natural one.

Let w be root weight, C total neighbor weight, H heaviest neighbor weight, d degree, E the number of induced neighbor edges, and M the sum of minimum endpoint weights over those edges. The frozen controls use distinct surrogate objectives:

| Program | Local / continuation surrogate | What follows from the formula |
|---|---|---|
| g05 | w − C + min(C, M/(1 + E/max(1,d))) | Scores never exceed w. Edge contributions can overlap; scalar damping does not identify a feasible alternative set or certify a marginal completion value. There is no H loss floor. |
| g01 / free | w − max(H, C − M) | Estimated loss is at least H. Edge overlap can still distort the loss. These two saved programs are identical after renaming the custom feature. |
| g03 | Density bonus times a weight/exposure ratio | Normalizes E by possible neighborhood edges; it does not identify which heavy alternatives can coexist. |
| g12 | w / max(0.000001, w, greedy independent neighbor weight) | Uses a feasible local alternative value, with order-dependent looseness. Local feasibility supplies no global action-ranking guarantee. |
| g18 | w + midpoint of cover and greedy values on the graph retained after the action | Uses retained-continuation structure. The midpoint itself is not a sound preference certificate; root-dependent recomputation can be expensive. |

On all 216 saved transfer contexts, g01/free have identical ordered schedules and feature work. Their minor wall-time differences are measurement variation from separate executions. The no-consistency, no-master, low-penalty, and high-penalty controls all freeze g05 itself, with 216/216 identical ordered schedules and work. Their zero behavior differences cannot establish the causal value of the omitted procedure; the finite selection simply chose the same program in these runs.

| Control | g05 minus control quality (pp), paired 95% CI | Median paired g05/control wall ratio, 95% CI | Median paired g05/control work ratio, 95% CI |
|---|---|---|---|
| g01 / free | +10.522304 [7.658964, 13.409226] | 1.053623 [1.048317, 1.058586] for free | 1.023364 [1.021107, 1.026358] |
| g03 minimum interface | −3.937569 [−5.087139, −2.748252] | 3.076243 [2.945887, 3.267552] | 1.754730 [1.742114, 1.761147] |
| g12 natural validation | +0.034194 [−1.505010, 1.619500] | 6.495702 [5.814912, 8.351485] | 3.575253 [3.214377, 3.869837] |
| g18 no cost | −8.339639 [−9.622889, −7.123969] | 1.252558 [1.115747, 1.491463] | 0.515470 [0.440722, 0.640546] |
| Rule only | −4.049700 [−5.224595, −2.863129] | 8.092056 [6.811789, 9.710963] | 10.084703 [8.087620, 12.240945] |
| Enumeration | +0.164291 [−0.643421, +0.906602] | 1.008111 [1.006943, 1.010782] | 1.001825 [1.001284, 1.002484] |

Thus g03 achieves higher old-transfer quality at lower measured cost. g12 has nearly the same aggregate quality as g05 with much less measured cost; the interval does not establish quality equivalence. g18 has higher quality but greater charged work, despite lower median paired wall cost in this dense transfer sample. These are different measured quantities, and none justifies retuning the primary freeze on old test outcomes.

g12's selection denominator explains part of the validation contrast. Its non-probe validation mean is 99.301669%, versus g05 98.999179%; the paired g05−g12 difference is −0.302490 pp [−0.708569, +0.099082]. On temporal validation it is −0.326555 pp [−0.624752, −0.029862]. But g12 scores 98.636364% on the probe schedules where g05 scores 100%, leading to mixed means of 99.087054% and 99.322024%. The mixed paired difference +0.234970 pp [−0.159539, +0.644086] is not a general natural-instance preference. g12 also has higher non-probe validation work (105,480.547619 versus 75,873.190476), so changing the quality denominator alone does not isolate the effect of cost. The controls differ in feature, scoring formula, and selection population.

### An exact failure in the original training bank

For `c3_train_64_0001_anchored_weighted_clique_cover_0`, both boundaries are the initial state. On the left, g05 chooses contact 35170; the saved oracle certifies regret exactly 192 using two expanded nodes. Free, rule-only, enumeration, g03, g12, and g18 choose 28126 and have exact regret zero. The corresponding right-side result is the same. This one block contributes 384 of the total 388 weight units in g05's certified regret lower sum (98.9691%). The negative non-probe mean is therefore dominated by a concrete training case rather than broad positive-regret incidence.

| Contact | Weight | Degree / induced edges | Neighbor weight C | Edge-min sum M | g05 estimated loss | g05 score | g18 retained midpoint score |
|---|---:|---:|---:|---:|---:|---:|---:|
| 35170, g05 actual choice | 887 | 21 / 172 | 18,114 | 151,113 | 1,671.652850 | −784.652850 | 2,339 |
| 28126, other controls' choice | 730 | 17 / 136 | 5,888 | 34,642 | 2,038.888889 | −1,308.888889 | 2,531 |
| 34982, evidence-pair member | 1,079 | 21 / 172 | 18,373 | 150,067 | 2,044.466321 | −965.466321 | 2,531 |

The 17-neighbor set of contact 28126 has 136 = 17·16/2 edges, so it is a clique. Its exact independent-set value is therefore the heaviest neighbor weight, 559. g05's scalar-damped loss estimate is 2,038.888889, much larger than that local attainable alternative. This relative calibration makes its score lower than 35170's. The stored global completion audit separately certifies the 192 loss. In this case, g18's retained-cover and retained-greedy values agree: 1,801 after choosing 28126 and 1,452 after choosing 35170; adding the chosen weights gives the exact 2,531 versus 2,339 contrast. This is an inspectable explanation of one training failure, not a causal proof for every dense-transfer loss.

All derived feature values and scores, source identity, original actual choices, and exact stored regret endpoints are retained under `program_diagnosis.audited_train_case` in the JSON. No new oracle solve or schedule outcome was generated for this inspection.

### Why charged work and wall cost change with the graph regime

The compiler lowers g05/g01/enumeration's edge-min statistics and g03's edge count into deletion-maintained aggregates. Initialization checks every neighbor pair for every root, so its membership workload is the sum over roots of d(d−1)/2. g05 and g01 share this large cost; g05's second edge-count feature is relatively cheap once those pairs are visited. The old transfer paired work ratio of only 1.023364 against g01/free reflects this sharing.

In the saved n=128 development graphs (training and validation together), average degree is 1.9795/3.2061/2.8027 in the balanced/ground-scarce/satellite-scarce regimes, with mean initial neighbor-pair checks 271.94/729.31/546.94. In transfer the corresponding averages are 30.0547/43.1452/41.4941 and 58,928.96/121,111.96/113,543.46. These source-backed structural counts support the relevance of initialization cost on dense graphs. They do not by themselves attribute a quality change to density.

g12 and g18 do not request the induced-edge aggregate initialization; their custom greedy/cover nodes use the generic snapshot evaluator. Their charged operations and exact-arithmetic overhead differ from the edge aggregates. The number of actual constructive decisions also changes: at n=128, g18 selects a mean 56.3333 contacts on the 30 non-probe validation contexts but 10.9306 on the 72 transfer contexts. On the 24 temporal validation contexts at n=128, its mean work is 26,498,254.166667 and median saved wall time 9.706371 seconds; on transfer n=128 its mean work is 1,062,976.958333 and median wall time 0.361532 seconds. These populations and execution conditions differ, so the values explain why a validation cost ranking need not transfer; they are not a hardware-matched speedup claim. The cooperative003 measurement will report actual CPU cost and completion alongside quality.

### Consequences for the scientific claim

The supported outcome is a costed, typed program-discovery procedure with finite-catalogue repair and exact compiled trace semantics, accompanied by a candid negative transfer result for the selected g05. Seed pair consistency does not guarantee that a deployment rollout reaches or chooses the pair, that its actual action has low regret, or that validation-selected cost-quality utility transfers. The collapsed ablations cannot establish that synthesis gates or the master improved final schedules in this saved bank. Keep these distinctions explicit; preserve the frozen controls and the planned cooperative003 evaluation. Any future redesigned scorer needs a separate training-only design and a newly declared evaluation, rather than revision against these old test outcomes.

## Main-paper figure choices and captions

`paper/figures/evidence_discovery_v03.pdf` is the provisional first full-width quantitative figure: three falsifiable panels in 7 × 2.65 in (504 × 190.8 pt), with embedded Arial regular/bold at 9 pt. The left panel uses observed counts, so it has no inferential error bars. The center separates probe-origin contradiction from non-probe evidence **within the original rollout bank**. It will be revised if the expanded non-probe census certifies aliases or obstruction. The right preserves the negative enumeration comparison. Label: `fig:evidence-discovery`.

Proposed caption: “(a) Certificates on 42 non-probe training pairs. (b) In the original rollout bank, 64 self-loop requirements originate from probes and vanish after repair. (c) Fixed-bank prefix selections on mixed validation contexts; enumeration exceeds guided at the final budget. One candidate bank per arm.”

`paper/figures/runtime_v03.pdf` is the recommended column figure, 3.33 × 2.45 in (239.76 × 176.4 pt), with embedded Arial at 9 pt. Label: `fig:runtime`.

Proposed caption: “Median paired interpreter/compiled time for one fixed structural rule; error bars are 95% cluster bootstrap intervals over 150 contexts with three runs per backend. Traces match throughout. The 1,024-contact point contains only three C3 source blocks.”

Reserve the second full-width quantitative composite for the completed holdout and dense/long-contact transfer archives. It should separate temporal and C3 quality from probes and pair quality with compiled work, using the frozen primary programs and ablations. Do not insert a placeholder curve or reconstructed outcome. These two composites plus the column runtime figure preserve the requested total figure-height budget; omit the large development stress plot from the main text.

The declared execution amendment in `docs/EXECUTION_BUDGET_AMENDMENT_V03.md` uses the cooperative003 holdout and transfer runs for the final primary inference comparisons. A cooperative guard checks every 256 charged-meter writes, targeting five process-CPU seconds per frozen constructive program. Primitive or cleanup work can overshoot; measured CPU times must accompany the target, which is not a hard real-time deadline. Timeout rows have no returned schedule and no substituted fallback. The final summary must retain the full assigned denominator: report completion rate and either zero-normalized all-context utility or conditional completed-schedule quality with explicit coverage. Earlier failed harness runs and the unbounded pilot remain execution diagnostics. HiGHS and local search keep their different ten- and two-second budgets and must not be described as budget matched.

Both exports were reopened as PNGs and visually checked after layout repair. Legends, axes, titles, and numbers are visible without overlapping labels or clipping. PDFs are single-page vectors at their intended paper dimensions; font resources identify embedded ArialMT and Arial-BoldMT. PNGs at 300 dpi are supplied for inspection, not manuscript rasterization.

## Remaining boundaries

- The 380-context development archive is complete: 95 training and 95 validation pairs, both sides; all MILP statuses 0 with recorded zero gap, and all saved schedules feasible. Its quality results are development screening rather than held-out evaluation.
- The archived C3 graphs lose the original adapter verifier context on serialization. Recorded feasibility here is graph-edge feasibility; it is not a repeated verification against original physical source constraints.
- Quotient acyclicity, seed score consistency, observed trace agreement, schedule quality, and actual-next-action regret are distinct outcomes. A score-consistent pair does not imply the scheduler reaches or chooses either pair member.
- Primary cooperative003 holdout/transfer archives are complete and analyzed below. The completed unbounded transfer and original-bank relevance audit remain separately labeled supplementary/offline. Development numbers retain their validation/development label when used in the paper.
- Within-configuration action aliasing and cross-configuration quotient cycles are different mechanisms. The expanded census must identify full base-vector equality within each side and audit the unexposed `satellite_trans_time` source field before assigning a natural alias or cross-side cycle interpretation. No census outcome is assumed in the present figures.

<!-- FINAL_COOPERATIVE_003 -->

## Completed cooperative003 evaluation

The two immutable archives contain all 840 held-out contexts and all 216 dense-long transfer contexts. Constructive programs use the full declared interface (`score_slice=False`) with a cooperative five-process-CPU-second target. HiGHS uses ten seconds and local search two seconds; these are distinct budgets. Failure has reward zero in the all-assigned mean. Completed-case quality and completion are separate outcomes. Reference ratios use the archived floating MILP upper, not a formal optimality proof.

The stratified 2,000-replicate bootstrap samples source seeds across all three temporal regimes and both graph sides, C3 source blocks, and diagnostic pairs. Conditional-quality bootstrap retains failed clusters in its assignment frame. The two populations are never pooled.

### Held-out (840 contexts; includes diagnostic probes)

| Frozen method | Completed / assigned | All-assigned ratio, % (95% CI) | Completed-case ratio, % | Median CPU, s | Median wall, s |
|---|---:|---:|---:|---:|---:|
| guided | 704/840 | 82.968844 [77.576630, 88.042481] | 98.996916 | 0.355944 | 0.355950 |
| free | 773/840 | 90.464368 [87.534525, 93.195110] | 98.305393 | 0.311503 | 0.311510 |
| rule | 796/840 | 93.841372 [91.691371, 95.804698] | 99.028584 | 0.295591 | 0.295593 |
| enumerated | 762/840 | 90.026315 [86.677946, 92.886848] | 99.241607 | 0.309744 | 0.309752 |
| guided_one_feature | 776/840 | 90.726170 [87.698869, 93.374420] | 98.208741 | 0.311855 | 0.311861 |
| guided_minimum_interface | 813/840 | 95.572557 [94.339871, 96.676307] | 98.746553 | 0.269284 | 0.269288 |
| guided_natural_validation | 706/840 | 83.289863 [77.971568, 88.377386] | 99.098421 | 0.358452 | 0.358462 |
| guided_no_cost | 344/840 | 40.901406 [33.528089, 48.977383] | 99.875527 | 5.000055 | 5.000141 |
| multi_start_1to2_search | 840/840 | 99.832614 [99.795573, 99.866012] | 99.832614 | unavailable | 0.000356 |

Guided−rule paired all-assigned difference: -10.872528 percentage points (95% CI [-14.518103, -7.509400]).

### Dense-long transfer (216 contexts)

| Frozen method | Completed / assigned | All-assigned ratio, % (95% CI) | Completed-case ratio, % | Median CPU, s | Median wall, s |
|---|---:|---:|---:|---:|---:|
| guided | 203/216 | 84.955581 [81.792602, 88.018125] | 90.396086 | 0.855492 | 0.855504 |
| free | 203/216 | 75.106020 [70.365984, 79.732223] | 79.915765 | 0.824210 | 0.824222 |
| rule | 216/216 | 93.947120 [93.154393, 94.684913] | 93.947120 | 0.069280 | 0.069281 |
| enumerated | 201/216 | 83.907529 [79.971307, 87.529048] | 90.169285 | 0.849664 | 0.849685 |
| guided_one_feature | 202/216 | 74.808677 [69.884133, 79.628240] | 79.993437 | 0.815325 | 0.815364 |
| guided_minimum_interface | 216/216 | 93.834989 [92.935759, 94.747953] | 93.834989 | 0.310694 | 0.310699 |
| guided_natural_validation | 216/216 | 89.863226 [88.262575, 91.398586] | 89.863226 | 0.083231 | 0.083232 |
| guided_no_cost | 165/216 | 75.269643 [63.329596, 86.087999] | 98.534806 | 0.678362 | 0.678375 |
| multi_start_1to2_search | 216/216 | 98.942518 [98.641928, 99.199958] | 98.942518 | unavailable | 0.000574 |

Guided−rule paired all-assigned difference: -8.991539 percentage points (95% CI [-12.034034, -6.143584]).

### Figure choice and limits

`outcomes_cooperative_v03.pdf` is a 7 × 2.85 inch, three-panel gallery figure with non-probe held-out quality, completion, and all-assigned median CPU alongside dense-long transfer. It keeps the negative result visible. The 95% intervals in quality/completion are source-cluster intervals; median CPU points are descriptive. The standalone runtime plot remains a fixed-rule implementation comparison and is not evidence of every frozen program's speed.

Suggested caption (42 words): **Full-interface v03 evaluation under a cooperative five-CPU-second target. Failure receives zero reward in panel (a); panel (b) shows completion. Quality and completion intervals resample source clusters. Panel (c) reports all-assigned median CPU, including unsuccessful runs. Diagnostic probes are omitted here.**

The saved g05, g01/g03/g12/g18 diagnoses remain descriptive. Identical ablations cannot establish a mechanism benefit. Successful TRAIN examples do not attribute aggregate held-out failure to one mechanism. Fresh v04 data are a separate evaluation after a TRAIN-only freeze.
