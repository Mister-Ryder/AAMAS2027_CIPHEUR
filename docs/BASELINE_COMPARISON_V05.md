# Executed v04 baseline comparison for the v05 presentation

No new experiments, programme selection, solver calls or model calls were performed. All point values below are independently recomputed from the two immutable short-budget archives with exact Fraction rewards and reconciled with the saved v04 summary and independent archive audits. The standalone exchange cost is independently recomputed and checked against the archived audit. Long-budget subsets, SNAP and later heap extensions do not enter these seven columns.

Competitive reward is the equal-context mean of reward divided by the strongest saved verified feasible witness. Native seeds 1/2/3 are averaged within a context, with failure reward zero; they are not independent graph samples. Coverage is completed/requested method runs. A 100% ratio is not a proof of optimality. Source-cluster intervals are retained from the independently audited v04 summary after checking their point estimates; this builder does not recompute the bootstrap.

The main table uses twelve methods. Full numerical controls below retain all twenty-three actually executed method IDs. Free/rule-only synthesis are project controls, not implementations of EoH or ReEvo. CHILS-ILS is the executed one-population ILS setting of the published CHILS implementation, not another independently published algorithm.

Elapsed time is a context median; published-method context times first average all three seed times. These are not summed seed costs. Classical exchange times include all five assigned classical initializers, including failed attempts, plus exchange search. Missing times remain unavailable. Constructive policies have a five-process-CPU-second cooperative target, native solvers a five-second native limit plus hard wall, HiGHS ten seconds, and exchange two seconds after initialization. Total computation is unmatched.

HiGHS MILP cites Huangfu and Hall (2018), *Parallelizing the dual revised simplex method*, Mathematical Programming Computation 10(1):119–142, DOI 10.1007/s12532-017-0130-5, using `huangfu2018highs`. This is the [official HiGHS academic acknowledgment recommendation](https://highs.dev/#background), independently checked on 2026-10-03 and linked to the [publisher record](https://link.springer.com/article/10.1007/s12532-017-0130-5). It acknowledges the executed software; the article concerns dual revised simplex and is not represented as a separate MILP-specific algorithm publication.

## Standard

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 100.00000 [100.00000, 100.00000] | 648/648 | 5.003782 |
| M2WIS | 100.00000 [100.00000, 100.00000] | 648/648 | 0.042387 |
| Struction | 100.00000 [100.00000, 100.00000] | 648/648 | 0.008832 |
| WeightedBR | 100.00000 [100.00000, 100.00000] | 648/648 | 0.006648 |
| CHILS_ILS | 100.00000 [100.00000, 100.00000] | 648/648 | 5.004603 |
| baseline | 98.47428 [98.32575, 98.62556] | 216/216 | 0.143936 |
| enumerated_v03 | 98.89556 [98.77748, 99.01937] | 216/216 | 0.265817 |
| free_v03 | 99.53301 [99.45073, 99.60851] | 216/216 | 0.396518 |
| guarded_continuation_64 | 99.59253 [99.48982, 99.69535] | 216/216 | 1.785852 |
| guided_primary_only_ablation | 99.45802 [99.36125, 99.55040] | 216/216 | 0.209599 |
| guided_v04 | 99.45802 [99.36125, 99.55040] | 216/216 | 0.209128 |
| legacy_continuation_g18 | 33.27779 [16.65252, 49.89890] | 72/216 | 5.002669 |
| legacy_guided_g05 | 99.24677 [99.14817, 99.35087] | 216/216 | 0.248653 |
| prior_guided_controls | 98.80106 [98.66699, 98.93331] | 216/216 | 0.166748 |
| rule_v03 | 98.92188 [98.80167, 99.04547] | 216/216 | 0.127307 |
| guided_v04_full_interface | 99.45802 [99.36125, 99.55040] | 216/216 | 0.392426 |
| baseline_weight | 96.38637 [96.02169, 96.77006] | 216/216 | 0.057673 |
| baseline_degree | 98.47428 [98.32575, 98.62556] | 216/216 | 0.114375 |
| baseline_weighted_conflict | 99.12977 [98.99772, 99.26667] | 216/216 | 0.127942 |
| baseline_v02_joint | 99.32563 [99.22417, 99.42648] | 216/216 | 0.195550 |
| baseline_structural_ratio | 98.28410 [98.10799, 98.46157] | 216/216 | 0.136547 |
| fixed_classical_1to2_search | 99.83572 [99.79737, 99.87290] | 216/216 | 0.637643 |
| HiGHS_MILP | 100.00000 [100.00000, 100.00000] | 216/216 | 0.009813 |

## Dense/long

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 100.00000 [100.00000, 100.00000] | 648/648 | 5.008175 |
| M2WIS | 100.00000 [100.00000, 100.00000] | 648/648 | 0.206735 |
| Struction | 100.00000 [100.00000, 100.00000] | 648/648 | 0.015177 |
| WeightedBR | 99.99471 [99.98413, 100.00000] | 648/648 | 0.038720 |
| CHILS_ILS | 100.00000 [100.00000, 100.00000] | 648/648 | 5.011589 |
| baseline | 94.46236 [93.81389, 95.09789] | 216/216 | 0.053103 |
| enumerated_v03 | 94.49786 [93.86477, 95.12307] | 216/216 | 0.088026 |
| free_v03 | 96.27278 [95.66091, 96.79222] | 216/216 | 0.292046 |
| guarded_continuation_64 | 96.87455 [96.12366, 97.60881] | 216/216 | 0.327799 |
| guided_primary_only_ablation | 96.10716 [95.57555, 96.61710] | 216/216 | 0.237036 |
| guided_v04 | 96.10716 [95.57555, 96.61710] | 216/216 | 0.235190 |
| legacy_continuation_g18 | 76.19909 [64.85034, 86.79474] | 167/216 | 0.617222 |
| legacy_guided_g05 | 84.95213 [81.04355, 88.09997] | 203/216 | 0.860951 |
| prior_guided_controls | 93.57375 [92.42949, 94.64460] | 216/216 | 0.292421 |
| rule_v03 | 94.51802 [93.88855, 95.13767] | 216/216 | 0.039639 |
| guided_v04_full_interface | 96.10716 [95.57555, 96.61710] | 216/216 | 0.282705 |
| baseline_weight | 78.47344 [74.14885, 82.48307] | 216/216 | 0.012178 |
| baseline_degree | 94.46236 [93.81389, 95.09789] | 216/216 | 0.023630 |
| baseline_weighted_conflict | 94.18216 [93.40302, 94.97582] | 216/216 | 0.040205 |
| baseline_v02_joint | 84.14258 [80.31720, 87.18483] | 203/216 | 0.850602 |
| baseline_structural_ratio | 90.73481 [89.61206, 91.84812] | 216/216 | 0.265158 |
| fixed_classical_1to2_search | 98.72847 [98.39210, 99.03378] | 216/216 | 1.198516 |
| HiGHS_MILP | 100.00000 [100.00000, 100.00000] | 216/216 | 0.022771 |

## C3

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 100.00000 [100.00000, 100.00000] | 72/72 | 5.004848 |
| M2WIS | 100.00000 [100.00000, 100.00000] | 72/72 | 0.102233 |
| Struction | 100.00000 [100.00000, 100.00000] | 72/72 | 0.012402 |
| WeightedBR | 99.90677 [99.77510, 100.00000] | 72/72 | 0.118178 |
| CHILS_ILS | 100.00000 [100.00000, 100.00000] | 72/72 | 5.007378 |
| baseline | 97.03800 [95.82335, 98.15465] | 24/24 | 0.134982 |
| enumerated_v03 | 96.74532 [95.13012, 98.10844] | 24/24 | 0.327102 |
| free_v03 | 97.38647 [96.24059, 98.39987] | 24/24 | 0.770775 |
| guarded_continuation_64 | 96.63168 [95.06748, 97.99241] | 24/24 | 1.046858 |
| guided_primary_only_ablation | 97.56104 [96.56513, 98.47769] | 24/24 | 0.472863 |
| guided_v04 | 97.56104 [96.56513, 98.47769] | 24/24 | 0.474098 |
| legacy_continuation_g18 | 24.62775 [0.00000, 49.62775] | 6/24 | 5.000327 |
| legacy_guided_g05 | 96.11119 [94.37968, 97.61079] | 24/24 | 0.302213 |
| prior_guided_controls | 97.16003 [95.46953, 98.54664] | 24/24 | 0.225769 |
| rule_v03 | 96.74303 [95.12791, 98.10856] | 24/24 | 0.127516 |
| guided_v04_full_interface | 97.56104 [96.56513, 98.47769] | 24/24 | 0.674089 |
| baseline_weight | 92.92615 [88.35128, 96.83299] | 24/24 | 0.068864 |
| baseline_degree | 97.03800 [95.82335, 98.15465] | 24/24 | 0.118851 |
| baseline_weighted_conflict | 97.48549 [96.24475, 98.48496] | 24/24 | 0.133089 |
| baseline_v02_joint | 96.67690 [95.70014, 97.62197] | 24/24 | 0.263510 |
| baseline_structural_ratio | 96.47020 [95.18574, 97.72938] | 24/24 | 0.171213 |
| fixed_classical_1to2_search | 99.56730 [99.18282, 99.86242] | 24/24 | 0.761382 |
| HiGHS_MILP | 100.00000 [100.00000, 100.00000] | 24/24 | 0.020812 |

## DIMACS unit

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 99.62963 [98.88889, 100.00000] | 54/54 | 5.010557 |
| M2WIS | 88.88889 [72.22222, 100.00000] | 48/54 | 5.141543 |
| Struction | 98.93708 [97.97822, 99.74897] | 54/54 | 4.236122 |
| WeightedBR | 78.44366 [63.31749, 91.82871] | 48/54 | 5.017528 |
| CHILS_ILS | 100.00000 [100.00000, 100.00000] | 54/54 | 5.016804 |
| baseline | 85.04087 [72.21839, 94.74608] | 17/18 | 0.071229 |
| enumerated_v03 | 85.79667 [73.60007, 94.30766] | 17/18 | 0.162719 |
| free_v03 | 82.20281 [69.90807, 91.17666] | 17/18 | 0.950326 |
| guarded_continuation_64 | 74.66349 [56.94388, 89.63643] | 15/18 | 0.886868 |
| guided_primary_only_ablation | 80.52837 [68.19607, 90.02609] | 17/18 | 0.835585 |
| guided_v04 | 80.52837 [68.19607, 90.02609] | 17/18 | 0.832673 |
| legacy_continuation_g18 | 62.09890 [40.59096, 82.12649] | 12/18 | 2.573808 |
| legacy_guided_g05 | 62.90093 [43.18146, 80.87703] | 13/18 | 1.446371 |
| prior_guided_controls | 73.75228 [55.85013, 88.79331] | 15/18 | 0.688308 |
| rule_v03 | 85.04087 [72.21839, 94.74608] | 17/18 | 0.080019 |
| guided_v04_full_interface | 80.52837 [68.19607, 90.02609] | 17/18 | 0.906631 |
| baseline_weight | 72.74964 [63.55241, 81.69337] | 18/18 | 0.028019 |
| baseline_degree | 85.04087 [72.21839, 94.74608] | 17/18 | 0.045501 |
| baseline_weighted_conflict | 85.04087 [72.21839, 94.74608] | 17/18 | 0.081846 |
| baseline_v02_joint | 64.51117 [44.46905, 82.85698] | 13/18 | 1.326568 |
| baseline_structural_ratio | 73.77043 [56.15915, 88.64664] | 15/18 | 0.651023 |
| fixed_classical_1to2_search | 92.95333 [87.65877, 96.90717] | 18/18 | 2.471634 |
| HiGHS_MILP | 82.58568 [66.87208, 94.30949] | 18/18 | 10.016783 |

## DIMACS hash

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 99.93595 [99.80785, 100.00000] | 54/54 | 5.011826 |
| M2WIS | 100.00000 [100.00000, 100.00000] | 54/54 | 5.198047 |
| Struction | 99.44274 [98.60636, 99.98328] | 54/54 | 3.445145 |
| WeightedBR | 88.83620 [79.72636, 95.66768] | 52/54 | 5.019797 |
| CHILS_ILS | 99.80785 [99.42355, 100.00000] | 54/54 | 5.017936 |
| baseline | 84.91519 [73.40146, 92.37248] | 17/18 | 0.071378 |
| enumerated_v03 | 85.46372 [74.03861, 92.83312] | 17/18 | 0.156653 |
| free_v03 | 84.09845 [72.68023, 91.58308] | 17/18 | 0.916941 |
| guarded_continuation_64 | 78.76255 [61.70290, 94.03623] | 15/18 | 0.895114 |
| guided_primary_only_ablation | 87.07372 [75.58511, 94.44861] | 17/18 | 0.801564 |
| guided_v04 | 87.07372 [75.58511, 94.44861] | 17/18 | 0.805619 |
| legacy_continuation_g18 | 63.03181 [41.36161, 83.93109] | 12/18 | 2.528628 |
| legacy_guided_g05 | 65.93865 [45.37305, 83.27414] | 13/18 | 1.436290 |
| prior_guided_controls | 76.26246 [58.82811, 90.96959] | 15/18 | 0.691785 |
| rule_v03 | 85.60556 [74.19608, 92.90761] | 17/18 | 0.079236 |
| guided_v04_full_interface | 87.07372 [75.58511, 94.44861] | 17/18 | 0.888295 |
| baseline_weight | 83.07229 [77.12298, 87.91965] | 18/18 | 0.028734 |
| baseline_degree | 84.91519 [73.40146, 92.37248] | 17/18 | 0.042519 |
| baseline_weighted_conflict | 89.62746 [78.18664, 96.56223] | 17/18 | 0.081896 |
| baseline_v02_joint | 64.79319 [44.50832, 82.29498] | 13/18 | 1.312816 |
| baseline_structural_ratio | 74.77008 [57.49182, 88.81500] | 15/18 | 0.653383 |
| fixed_classical_1to2_search | 95.80689 [93.47507, 97.85260] | 18/18 | 2.507049 |
| HiGHS_MILP | 94.22462 [84.85256, 99.51642] | 18/18 | 8.856733 |

## SATLIB unit

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 99.96768 [99.92690, 99.99658] | 90/90 | 5.008652 |
| M2WIS | 99.71184 [99.62280, 99.80390] | 90/90 | 5.208442 |
| Struction | 96.91568 [96.32565, 97.50444] | 90/90 | 5.022273 |
| WeightedBR | 99.63578 [99.53156, 99.73358] | 90/90 | 5.019868 |
| CHILS_ILS | 99.90800 [99.85188, 99.95231] | 90/90 | 5.015830 |
| baseline | 98.80288 [98.53428, 99.06230] | 30/30 | 1.970985 |
| enumerated_v03 | 32.85714 [16.44689, 49.37729] | 10/30 | 5.000398 |
| free_v03 | 32.71062 [16.33700, 49.08425] | 10/30 | 5.000429 |
| guarded_continuation_64 | 65.93625 [46.27496, 82.41027] | 20/30 | 4.638734 |
| guided_primary_only_ablation | 32.93040 [16.48352, 49.41484] | 10/30 | 5.000360 |
| guided_v04 | 32.93040 [16.48352, 49.41484] | 10/30 | 5.000333 |
| legacy_continuation_g18 | 0.00000 [0.00000, 0.00000] | 0/30 | 5.000477 |
| legacy_guided_g05 | 66.01875 [46.29375, 82.51188] | 20/30 | 4.108391 |
| prior_guided_controls | 66.03404 [46.30919, 82.53571] | 20/30 | 3.358718 |
| rule_v03 | 98.80288 [98.53428, 99.06230] | 30/30 | 1.969726 |
| guided_v04_full_interface | 32.93040 [16.48352, 49.41484] | 10/30 | 5.000319 |
| baseline_weight | 92.40709 [91.60116, 93.17343] | 30/30 | 0.948016 |
| baseline_degree | 98.80288 [98.53428, 99.06230] | 30/30 | 1.950435 |
| baseline_weighted_conflict | 98.80288 [98.53428, 99.06230] | 30/30 | 2.054324 |
| baseline_v02_joint | 66.01875 [46.29375, 82.51188] | 20/30 | 3.426774 |
| baseline_structural_ratio | 66.01875 [46.29375, 82.51188] | 20/30 | 2.651746 |
| fixed_classical_1to2_search | 98.94151 [98.72242, 99.15352] | 30/30 | 11.010308 |
| HiGHS_MILP | 98.04900 [97.10053, 98.83261] | 30/30 | 10.011441 |

## SATLIB hash

| Method ID | Failure-zero reward % (95% source-cluster interval) | Completed/requested runs | Standalone median elapsed s |
|---|---:|---:|---:|
| CHILS | 99.99515 [99.98752, 99.99974] | 90/90 | 5.008684 |
| M2WIS | 99.99199 [99.98401, 99.99843] | 90/90 | 5.171279 |
| Struction | 98.04554 [97.40609, 98.64948] | 90/90 | 5.022015 |
| WeightedBR | 99.72639 [99.59064, 99.83529] | 90/90 | 5.021198 |
| CHILS_ILS | 99.93173 [99.86047, 99.97731] | 90/90 | 5.015993 |
| baseline | 92.13885 [91.45394, 92.73903] | 30/30 | 1.904293 |
| enumerated_v03 | 31.18142 [15.61943, 46.98880] | 10/30 | 5.000423 |
| free_v03 | 29.66983 [14.80449, 44.62421] | 10/30 | 5.000389 |
| guarded_continuation_64 | 35.08629 [19.04086, 53.75859] | 11/30 | 5.000548 |
| guided_primary_only_ablation | 31.04546 [15.48281, 46.66560] | 10/30 | 5.000316 |
| guided_v04 | 31.04546 [15.48281, 46.66560] | 10/30 | 5.000370 |
| legacy_continuation_g18 | 0.00000 [0.00000, 0.00000] | 0/30 | 5.000476 |
| legacy_guided_g05 | 57.44046 [40.53754, 71.77755] | 20/30 | 3.997127 |
| prior_guided_controls | 63.90461 [44.94606, 79.89376] | 20/30 | 3.072843 |
| rule_v03 | 93.90293 [93.09802, 94.55990] | 30/30 | 1.886385 |
| guided_v04_full_interface | 31.04546 [15.48281, 46.66560] | 10/30 | 5.000354 |
| baseline_weight | 92.86060 [92.00661, 93.76382] | 30/30 | 0.901532 |
| baseline_degree | 92.13885 [91.45394, 92.73903] | 30/30 | 1.870433 |
| baseline_weighted_conflict | 94.81901 [94.39228, 95.26795] | 30/30 | 1.938599 |
| baseline_v02_joint | 60.11180 [42.43157, 75.11396] | 20/30 | 3.320664 |
| baseline_structural_ratio | 59.33732 [41.77706, 74.17674] | 20/30 | 2.560513 |
| fixed_classical_1to2_search | 98.29244 [97.71214, 98.79814] | 30/30 | 10.594816 |
| HiGHS_MILP | 99.95852 [99.90961, 99.99072] | 30/30 | 1.877830 |

## What the LLM comparison supports

The frozen structural primary improves Degree by 0.984 and 1.645 percentage points on standard and dense/long scheduling, with positive paired source-cluster intervals. It improves the rule-only control by 0.536 and 1.589 points there. Free synthesis has higher standard/dense point means by 0.075/0.166 points; both primary-minus-Free intervals cross zero. C3 primary-minus-Free is +0.175 points [0.036, 0.346], whereas primary-minus-Degree and primary-minus-rule intervals cross zero. This is mixed selected-program evidence, not a general model-level advantage.

Published implementations and the classical exchange control exceed the primary on fresh reward. Public failures further limit transfer. Unequal proposal counts (12 guided versus 24 historical controls), one continuing guided authoring session, unavailable token costs, changed evidence and unmatched computation prevent causal attribution to LLM guidance. The actual-regret tie-break selected the same AST as the primary-only ablation. Representation refinement, structural scoring and pure execution optimizations have their own evidence; they do not establish LLM superiority.

Missing evidence: matched-budget repeated authoring sessions; a controlled guidance-versus-no-guidance experiment with identical proposal/checking compute; canonical executed EoH/ReEvo comparisons; and actual native anytime trajectories. Frozen rollout prefixes are construction progress, not CPU-time progress or an LLM learning curve.

## Immutable sources

- summary: `experiments/analysis/v04/summary.json` — SHA256 `8116ed245ab2fe612818d19a50493d75ad47e080d69d3ef57de0597d47abe090`
- fresh: `experiments/runs/v04/advanced_fresh_v04_001.tar.gz` — SHA256 `4bbddde5655edf06b6959ada796166ff44b909e8bec9f8d5383e1796cdab7828`
- public: `experiments/runs/v04/advanced_public_v04_001.tar.gz` — SHA256 `b37999eb75b52a12da80ae071984791e37bff54a8351c836fc4ac7a800e29050`
- fresh_audit: `experiments/analysis/v04/advanced_fresh_audit.json` — SHA256 `19bb6f6b751cff3aa9f13fe341febe6fdbf87e4a29c41726f3561219526e417a`
- public_audit: `experiments/analysis/v04/advanced_public_audit.json` — SHA256 `3a322f0181c7377ba021b5f07c3346e53dfacbff37bb2696da6d0c8fba9e3c19`

The JSON includes exact ratios, context-level denominators, all elapsed values, member/source/executable receipts and the saved interval definitions. Main-table decimal rounding does not change the underlying values.
