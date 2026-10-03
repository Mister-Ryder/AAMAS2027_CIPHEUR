# v04 source-backed quantitative analysis

This analysis uses immutable archived observations. Fresh and public outcomes remain separate; public DIMACS/SATLIB and unit/hash-weighted graphs are not pooled. The four native comparators retain seeds 1, 2, 3 as a per-context mean with failure reward zero. Seeds are not treated as independent graph samples.

## Isolated TRAIN common-component cancellation

396 saved action comparisons use identical zero-search bounds on the unmatched components. Cancelling the common components makes all 396 intervals nested and 199 strictly narrower. Median width is 86.75 without cancellation and 36 after cancellation. Strict certificates stay 33→33, with zero gains or losses; 61 exact ties and 302 unresolved comparisons remain. The separate whole-residual-versus-component strategy comparison has 10→33 strict relations and does not isolate cancellation.

Mean paired width reduction: 90.704545, 95% source-cluster CI [27.172412, 183.542929]. Action comparisons sharing a TRAIN source are kept together. The figure CDF is the observed finite-bank distribution, not a confidence band.

`cancellation_uncertainty_v04.pdf` is 7 × 2.6 inches with Arial 9 pt. Suggested caption: **Matched TRAIN cancellation audit. Each comparison keeps the same unmatched zero-search bounds. Cancelling common components narrows 199 of 396 intervals and preserves interval nesting, but the number of strict certificates remains 33. The separate whole-residual strategy comparison is not plotted.**

## Outcome population inventory

| Population | Assigned contexts |
|---|---:|
| fresh: standard_balanced | 72 |
| fresh: standard_ground_scarce | 72 |
| fresh: standard_satellite_scarce | 72 |
| fresh: dense_long_balanced | 72 |
| fresh: dense_long_ground_scarce | 72 |
| fresh: dense_long_satellite_scarce | 72 |
| fresh: c3 | 24 |
| public: DIMACS/unit | 18 |
| public: DIMACS/hash_weighted | 18 |
| public: SATLIB/unit | 30 |
| public: SATLIB/hash_weighted | 30 |

## Completed comparisons

### fresh: short

| Population | Method | Completed / requested runs | Failure-zero competitive ratio, % (95% CI) | Mean formal-upper ratio, % | Median wall, s |
|---|---|---:|---:|---:|---:|
| standard | CHILS | 648/648 | 100.00000 [100.00000, 100.00000] | 87.47430 | 5.003782 |
| standard | CHILS_ILS | 648/648 | 100.00000 [100.00000, 100.00000] | 87.47430 | 5.004603 |
| standard | HiGHS_MILP | 216/216 | 100.00000 [100.00000, 100.00000] | 87.47430 | 0.009813 |
| standard | M2WIS | 648/648 | 100.00000 [100.00000, 100.00000] | 87.47430 | 0.042387 |
| standard | Struction | 648/648 | 100.00000 [100.00000, 100.00000] | 87.47430 | 0.008832 |
| standard | WeightedBR | 648/648 | 100.00000 [100.00000, 100.00000] | 87.47430 | 0.006648 |
| standard | baseline | 216/216 | 98.47428 [98.32575, 98.62556] | 86.15507 | 0.143936 |
| standard | baseline_degree | 216/216 | 98.47428 [98.32575, 98.62556] | 86.15507 | 0.114375 |
| standard | baseline_structural_ratio | 216/216 | 98.28410 [98.10799, 98.46157] | 85.99787 | 0.136547 |
| standard | baseline_v02_joint | 216/216 | 99.32563 [99.22417, 99.42648] | 86.88908 | 0.195550 |
| standard | baseline_weight | 216/216 | 96.38637 [96.02169, 96.77006] | 84.32877 | 0.057673 |
| standard | baseline_weighted_conflict | 216/216 | 99.12977 [98.99772, 99.26667] | 86.72070 | 0.127942 |
| standard | enumerated_v03 | 216/216 | 98.89556 [98.77748, 99.01937] | 86.52162 | 0.265817 |
| standard | fixed_classical_1to2_search | 216/216 | 99.83572 [99.79737, 99.87290] | 87.33291 | 0.000550 |
| standard | free_v03 | 216/216 | 99.53301 [99.45073, 99.60851] | 87.07210 | 0.396518 |
| standard | guarded_continuation_64 | 216/216 | 99.59253 [99.48982, 99.69535] | 87.12051 | 1.785852 |
| standard | guided_primary_only_ablation | 216/216 | 99.45802 [99.36125, 99.55040] | 87.00581 | 0.209599 |
| standard | guided_v04 | 216/216 | 99.45802 [99.36125, 99.55040] | 87.00581 | 0.209128 |
| standard | guided_v04_full_interface | 216/216 | 99.45802 [99.36125, 99.55040] | 87.00581 | 0.392426 |
| standard | legacy_continuation_g18 | 72/216 | 33.27779 [16.65252, 49.89890] | 29.02804 | 5.002669 |
| standard | legacy_guided_g05 | 216/216 | 99.24677 [99.14817, 99.35087] | 86.82387 | 0.248653 |
| standard | prior_guided_controls | 216/216 | 98.80106 [98.66699, 98.93331] | 86.43087 | 0.166748 |
| standard | rule_v03 | 216/216 | 98.92188 [98.80167, 99.04547] | 86.54476 | 0.127307 |
| dense_long | CHILS | 648/648 | 100.00000 [100.00000, 100.00000] | 73.72384 | 5.008175 |
| dense_long | CHILS_ILS | 648/648 | 100.00000 [100.00000, 100.00000] | 73.72384 | 5.011589 |
| dense_long | HiGHS_MILP | 216/216 | 100.00000 [100.00000, 100.00000] | 73.72384 | 0.022771 |
| dense_long | M2WIS | 648/648 | 100.00000 [100.00000, 100.00000] | 73.72384 | 0.206735 |
| dense_long | Struction | 648/648 | 100.00000 [100.00000, 100.00000] | 73.72384 | 0.015177 |
| dense_long | WeightedBR | 648/648 | 99.99471 [99.98413, 100.00000] | 73.72084 | 0.038720 |
| dense_long | baseline | 216/216 | 94.46236 [93.81389, 95.09789] | 69.68314 | 0.053103 |
| dense_long | baseline_degree | 216/216 | 94.46236 [93.81389, 95.09789] | 69.68314 | 0.023630 |
| dense_long | baseline_structural_ratio | 216/216 | 90.73481 [89.61206, 91.84812] | 66.81565 | 0.265158 |
| dense_long | baseline_v02_joint | 203/216 | 84.14258 [80.31720, 87.18483] | 62.25060 | 0.850602 |
| dense_long | baseline_weight | 216/216 | 78.47344 [74.14885, 82.48307] | 58.61009 | 0.012178 |
| dense_long | baseline_weighted_conflict | 216/216 | 94.18216 [93.40302, 94.97582] | 69.46648 | 0.040205 |
| dense_long | enumerated_v03 | 216/216 | 94.49786 [93.86477, 95.12307] | 69.72467 | 0.088026 |
| dense_long | fixed_classical_1to2_search | 216/216 | 98.72847 [98.39210, 99.03378] | 72.81295 | 0.000655 |
| dense_long | free_v03 | 216/216 | 96.27278 [95.66091, 96.79222] | 70.95370 | 0.292046 |
| dense_long | guarded_continuation_64 | 216/216 | 96.87455 [96.12366, 97.60881] | 71.55050 | 0.327799 |
| dense_long | guided_primary_only_ablation | 216/216 | 96.10716 [95.57555, 96.61710] | 70.86295 | 0.237036 |
| dense_long | guided_v04 | 216/216 | 96.10716 [95.57555, 96.61710] | 70.86295 | 0.235190 |
| dense_long | guided_v04_full_interface | 216/216 | 96.10716 [95.57555, 96.61710] | 70.86295 | 0.282705 |
| dense_long | legacy_continuation_g18 | 167/216 | 76.19909 [64.85034, 86.79474] | 58.36226 | 0.617222 |
| dense_long | legacy_guided_g05 | 203/216 | 84.95213 [81.04355, 88.09997] | 62.90372 | 0.860951 |
| dense_long | prior_guided_controls | 216/216 | 93.57375 [92.42949, 94.64460] | 69.00213 | 0.292421 |
| dense_long | rule_v03 | 216/216 | 94.51802 [93.88855, 95.13767] | 69.73116 | 0.039639 |
| c3 | CHILS | 72/72 | 100.00000 [100.00000, 100.00000] | 70.19353 | 5.004848 |
| c3 | CHILS_ILS | 72/72 | 100.00000 [100.00000, 100.00000] | 70.19353 | 5.007378 |
| c3 | HiGHS_MILP | 24/24 | 100.00000 [100.00000, 100.00000] | 70.19353 | 0.020812 |
| c3 | M2WIS | 72/72 | 100.00000 [100.00000, 100.00000] | 70.19353 | 0.102233 |
| c3 | Struction | 72/72 | 100.00000 [100.00000, 100.00000] | 70.19353 | 0.012402 |
| c3 | WeightedBR | 72/72 | 99.90677 [99.77510, 100.00000] | 70.13714 | 0.118178 |
| c3 | baseline | 24/24 | 97.03800 [95.82335, 98.15465] | 68.23258 | 0.134982 |
| c3 | baseline_degree | 24/24 | 97.03800 [95.82335, 98.15465] | 68.23258 | 0.118851 |
| c3 | baseline_structural_ratio | 24/24 | 96.47020 [95.18574, 97.72938] | 67.90964 | 0.171213 |
| c3 | baseline_v02_joint | 24/24 | 96.67690 [95.70014, 97.62197] | 67.97813 | 0.263510 |
| c3 | baseline_weight | 24/24 | 92.92615 [88.35128, 96.83299] | 65.27556 | 0.068864 |
| c3 | baseline_weighted_conflict | 24/24 | 97.48549 [96.24475, 98.48496] | 68.55529 | 0.133089 |
| c3 | enumerated_v03 | 24/24 | 96.74532 [95.13012, 98.10844] | 68.05110 | 0.327102 |
| c3 | fixed_classical_1to2_search | 24/24 | 99.56730 [99.18282, 99.86242] | 69.91422 | 0.000834 |
| c3 | free_v03 | 24/24 | 97.38647 [96.24059, 98.39987] | 68.51369 | 0.770775 |
| c3 | guarded_continuation_64 | 24/24 | 96.63168 [95.06748, 97.99241] | 68.00476 | 1.046858 |
| c3 | guided_primary_only_ablation | 24/24 | 97.56104 [96.56513, 98.47769] | 68.62642 | 0.472863 |
| c3 | guided_v04 | 24/24 | 97.56104 [96.56513, 98.47769] | 68.62642 | 0.474098 |
| c3 | guided_v04_full_interface | 24/24 | 97.56104 [96.56513, 98.47769] | 68.62642 | 0.674089 |
| c3 | legacy_continuation_g18 | 6/24 | 24.62775 [0.00000, 49.62775] | 21.14384 | 5.000327 |
| c3 | legacy_guided_g05 | 24/24 | 96.11119 [94.37968, 97.61079] | 67.67155 | 0.302213 |
| c3 | prior_guided_controls | 24/24 | 97.16003 [95.46953, 98.54664] | 68.40411 | 0.225769 |
| c3 | rule_v03 | 24/24 | 96.74303 [95.12791, 98.10856] | 68.04967 | 0.127516 |
### fresh: long_prespecified_subset

| Population | Method | Completed / requested runs | Failure-zero competitive ratio, % (95% CI) | Mean formal-upper ratio, % | Median wall, s |
|---|---|---:|---:|---:|---:|
| standard | CHILS | 18/18 | 100.00000 [100.00000, 100.00000] | 88.09757 | 30.006396 |
| standard | HiGHS_MILP | 6/6 | 100.00000 [100.00000, 100.00000] | 88.09757 | 0.373881 |
| standard | M2WIS | 18/18 | 100.00000 [100.00000, 100.00000] | 88.09757 | 0.061015 |
| standard | Struction | 18/18 | 100.00000 [100.00000, 100.00000] | 88.09757 | 0.009460 |
| standard | WeightedBR | 18/18 | 100.00000 [100.00000, 100.00000] | 88.09757 | 0.007277 |
| standard | baseline | 6/6 | 98.48024 [98.48024, 98.48024] | 86.77341 | 0.461791 |
| standard | baseline_degree | 6/6 | 98.48024 [98.48024, 98.48024] | 86.77341 | 0.453599 |
| standard | baseline_structural_ratio | 6/6 | 99.16020 [99.16020, 99.16020] | 87.37225 | 0.526836 |
| standard | baseline_v02_joint | 6/6 | 99.13912 [99.13912, 99.13912] | 87.33656 | 0.757444 |
| standard | baseline_weight | 6/6 | 94.60115 [94.60115, 94.60115] | 83.33905 | 0.219048 |
| standard | baseline_weighted_conflict | 6/6 | 98.60868 [98.60868, 98.60868] | 86.88725 | 0.488048 |
| standard | enumerated_v03 | 6/6 | 98.89668 [98.89668, 98.89668] | 87.14267 | 1.062177 |
| standard | fixed_classical_1to2_search | 6/6 | 99.94735 [99.94735, 99.94735] | 88.05161 | 0.001732 |
| standard | free_v03 | 6/6 | 99.46777 [99.46777, 99.46777] | 87.62910 | 1.576842 |
| standard | guarded_continuation_64 | 6/6 | 99.09802 [99.09802, 99.09802] | 87.30644 | 2.574131 |
| standard | guided_primary_only_ablation | 6/6 | 99.36347 [99.36347, 99.36347] | 87.54330 | 0.851807 |
| standard | guided_v04 | 6/6 | 99.36347 [99.36347, 99.36347] | 87.54330 | 0.853105 |
| standard | guided_v04_full_interface | 6/6 | 99.36347 [99.36347, 99.36347] | 87.54330 | 1.585131 |
| standard | legacy_continuation_g18 | 0/6 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.004290 |
| standard | legacy_guided_g05 | 6/6 | 98.82961 [98.82961, 98.82961] | 87.07800 | 0.962278 |
| standard | prior_guided_controls | 6/6 | 98.45607 [98.45607, 98.45607] | 86.74982 | 0.655759 |
| standard | rule_v03 | 6/6 | 98.89668 [98.89668, 98.89668] | 87.14267 | 0.486095 |
| dense_long | CHILS | 18/18 | 100.00000 [100.00000, 100.00000] | 65.33821 | 30.017023 |
| dense_long | HiGHS_MILP | 6/6 | 100.00000 [100.00000, 100.00000] | 65.33821 | 0.343287 |
| dense_long | M2WIS | 18/18 | 100.00000 [100.00000, 100.00000] | 65.33821 | 0.361708 |
| dense_long | Struction | 18/18 | 100.00000 [100.00000, 100.00000] | 65.33821 | 0.035324 |
| dense_long | WeightedBR | 18/18 | 100.00000 [100.00000, 100.00000] | 65.33821 | 0.115077 |
| dense_long | baseline | 6/6 | 93.03461 [93.03461, 93.03461] | 60.78671 | 0.116341 |
| dense_long | baseline_degree | 6/6 | 93.03461 [93.03461, 93.03461] | 60.78671 | 0.096950 |
| dense_long | baseline_structural_ratio | 6/6 | 91.71960 [91.71960, 91.71960] | 59.93222 | 1.407317 |
| dense_long | baseline_v02_joint | 5/6 | 76.52670 [76.52670, 76.52670] | 49.17402 | 4.456704 |
| dense_long | baseline_weight | 6/6 | 75.68405 [75.68405, 75.68405] | 49.30763 | 0.035945 |
| dense_long | baseline_weighted_conflict | 6/6 | 94.33930 [94.33930, 94.33930] | 61.61333 | 0.151940 |
| dense_long | enumerated_v03 | 6/6 | 92.65613 [92.65613, 92.65613] | 60.53418 | 0.424915 |
| dense_long | fixed_classical_1to2_search | 6/6 | 98.31831 [98.31831, 98.31831] | 64.18192 | 0.002679 |
| dense_long | free_v03 | 6/6 | 95.26519 [95.26519, 95.26519] | 62.16781 | 2.182752 |
| dense_long | guarded_continuation_64 | 6/6 | 94.65998 [94.65998, 94.65998] | 61.82842 | 1.601943 |
| dense_long | guided_primary_only_ablation | 6/6 | 95.39178 [95.39178, 95.39178] | 62.28573 | 1.851749 |
| dense_long | guided_v04 | 6/6 | 95.39178 [95.39178, 95.39178] | 62.28573 | 1.879780 |
| dense_long | guided_v04_full_interface | 6/6 | 95.39178 [95.39178, 95.39178] | 62.28573 | 2.011353 |
| dense_long | legacy_continuation_g18 | 1/6 | 15.77896 [15.77896, 15.77896] | 11.18980 | 5.002920 |
| dense_long | legacy_guided_g05 | 5/6 | 75.46058 [75.46058, 75.46058] | 48.56297 | 4.427371 |
| dense_long | prior_guided_controls | 6/6 | 93.79064 [93.79064, 93.79064] | 61.22073 | 1.504449 |
| dense_long | rule_v03 | 6/6 | 92.65613 [92.65613, 92.65613] | 60.53418 | 0.148422 |
| c3 | CHILS | 24/24 | 100.00000 [100.00000, 100.00000] | 70.03957 | 30.004586 |
| c3 | HiGHS_MILP | 8/8 | 100.00000 [100.00000, 100.00000] | 70.03957 | 0.020729 |
| c3 | M2WIS | 24/24 | 100.00000 [100.00000, 100.00000] | 70.03957 | 0.139938 |
| c3 | Struction | 24/24 | 100.00000 [100.00000, 100.00000] | 70.03957 | 0.018298 |
| c3 | WeightedBR | 24/24 | 99.93174 [99.79522, 100.00000] | 69.99966 | 0.153055 |
| c3 | baseline | 8/8 | 97.77672 [96.08924, 98.98097] | 68.61245 | 0.145616 |
| c3 | baseline_degree | 8/8 | 97.77672 [96.08924, 98.98097] | 68.61245 | 0.119066 |
| c3 | baseline_structural_ratio | 8/8 | 96.50617 [93.96401, 99.04832] | 67.84788 | 0.179479 |
| c3 | baseline_v02_joint | 8/8 | 97.50354 [96.05671, 98.95037] | 68.44653 | 0.272525 |
| c3 | baseline_weight | 8/8 | 96.24217 [92.32087, 99.12140] | 67.62342 | 0.067192 |
| c3 | baseline_weighted_conflict | 8/8 | 98.00580 [97.06897, 99.12482] | 68.75679 | 0.134019 |
| c3 | enumerated_v03 | 8/8 | 97.95997 [96.63901, 98.98097] | 68.71960 | 0.325315 |
| c3 | fixed_classical_1to2_search | 8/8 | 99.78191 [99.34574, 100.00000] | 69.91238 | 0.000808 |
| c3 | free_v03 | 8/8 | 97.10874 [95.53920, 99.10298] | 68.18606 | 0.766405 |
| c3 | guarded_continuation_64 | 8/8 | 98.02807 [96.42740, 99.62198] | 68.82627 | 0.957020 |
| c3 | guided_primary_only_ablation | 8/8 | 97.36733 [95.82801, 99.20896] | 68.35421 | 0.472346 |
| c3 | guided_v04 | 8/8 | 97.36733 [95.82801, 99.20896] | 68.35421 | 0.474530 |
| c3 | guided_v04_full_interface | 8/8 | 97.36733 [95.82801, 99.20896] | 68.35421 | 0.671840 |
| c3 | legacy_continuation_g18 | 2/8 | 25.00000 [0.00000, 75.00000] | 21.89596 | 5.000364 |
| c3 | legacy_guided_g05 | 8/8 | 97.09590 [94.54119, 99.13478] | 68.27224 | 0.305633 |
| c3 | prior_guided_controls | 8/8 | 97.78440 [96.24742, 99.29702] | 68.65701 | 0.223347 |
| c3 | rule_v03 | 8/8 | 97.95997 [96.63901, 98.98097] | 68.71960 | 0.127218 |
### public: short

| Population | Method | Completed / requested runs | Failure-zero competitive ratio, % (95% CI) | Mean formal-upper ratio, % | Median wall, s |
|---|---|---:|---:|---:|---:|
| DIMACS/unit | CHILS | 54/54 | 99.62963 [98.88889, 100.00000] | 53.35479 | 5.010557 |
| DIMACS/unit | CHILS_ILS | 54/54 | 100.00000 [100.00000, 100.00000] | 53.47556 | 5.016804 |
| DIMACS/unit | HiGHS_MILP | 18/18 | 82.58568 [66.87208, 94.30949] | 47.35115 | 10.016783 |
| DIMACS/unit | M2WIS | 48/54 | 88.88889 [72.22222, 100.00000] | 49.00933 | 5.141543 |
| DIMACS/unit | Struction | 54/54 | 98.93708 [97.97822, 99.74897] | 53.08210 | 4.236122 |
| DIMACS/unit | WeightedBR | 48/54 | 78.44366 [63.31749, 91.82871] | 45.27659 | 5.017528 |
| DIMACS/unit | baseline | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.071229 |
| DIMACS/unit | baseline_degree | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.045501 |
| DIMACS/unit | baseline_structural_ratio | 15/18 | 73.77043 [56.15915, 88.64664] | 40.33051 | 0.651023 |
| DIMACS/unit | baseline_v02_joint | 13/18 | 64.51117 [44.46905, 82.85698] | 36.50455 | 1.326568 |
| DIMACS/unit | baseline_weight | 18/18 | 72.74964 [63.55241, 81.69337] | 42.09919 | 0.028019 |
| DIMACS/unit | baseline_weighted_conflict | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.081846 |
| DIMACS/unit | enumerated_v03 | 17/18 | 85.79667 [73.60007, 94.30766] | 44.23028 | 0.162719 |
| DIMACS/unit | fixed_classical_1to2_search | 18/18 | 92.95333 [87.65877, 96.90717] | 50.37068 | 0.000697 |
| DIMACS/unit | free_v03 | 17/18 | 82.20281 [69.90807, 91.17666] | 42.71721 | 0.950326 |
| DIMACS/unit | guarded_continuation_64 | 15/18 | 74.66349 [56.94388, 89.63643] | 40.61075 | 0.886868 |
| DIMACS/unit | guided_primary_only_ablation | 17/18 | 80.52837 [68.19607, 90.02609] | 42.21071 | 0.835585 |
| DIMACS/unit | guided_v04 | 17/18 | 80.52837 [68.19607, 90.02609] | 42.21071 | 0.832673 |
| DIMACS/unit | guided_v04_full_interface | 17/18 | 80.52837 [68.19607, 90.02609] | 42.21071 | 0.906631 |
| DIMACS/unit | legacy_continuation_g18 | 12/18 | 62.09890 [40.59096, 82.12649] | 31.72140 | 2.573808 |
| DIMACS/unit | legacy_guided_g05 | 13/18 | 62.90093 [43.18146, 80.87703] | 35.96338 | 1.446371 |
| DIMACS/unit | prior_guided_controls | 15/18 | 73.75228 [55.85013, 88.79331] | 40.33760 | 0.688308 |
| DIMACS/unit | rule_v03 | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.080019 |
| DIMACS/hash_weighted | CHILS | 54/54 | 99.93595 [99.80785, 100.00000] | 50.50821 | 5.011826 |
| DIMACS/hash_weighted | CHILS_ILS | 54/54 | 99.80785 [99.42355, 100.00000] | 50.39027 | 5.017936 |
| DIMACS/hash_weighted | HiGHS_MILP | 18/18 | 94.22462 [84.85256, 99.51642] | 49.14687 | 8.856733 |
| DIMACS/hash_weighted | M2WIS | 54/54 | 100.00000 [100.00000, 100.00000] | 50.56718 | 5.198047 |
| DIMACS/hash_weighted | Struction | 54/54 | 99.44274 [98.60636, 99.98328] | 50.35613 | 3.445145 |
| DIMACS/hash_weighted | WeightedBR | 52/54 | 88.83620 [79.72636, 95.66768] | 46.98887 | 5.019797 |
| DIMACS/hash_weighted | baseline | 17/18 | 84.91519 [73.40146, 92.37248] | 41.71962 | 0.071378 |
| DIMACS/hash_weighted | baseline_degree | 17/18 | 84.91519 [73.40146, 92.37248] | 41.71962 | 0.042519 |
| DIMACS/hash_weighted | baseline_structural_ratio | 15/18 | 74.77008 [57.49182, 88.81500] | 38.72367 | 0.653383 |
| DIMACS/hash_weighted | baseline_v02_joint | 13/18 | 64.79319 [44.50832, 82.29498] | 35.21275 | 1.312816 |
| DIMACS/hash_weighted | baseline_weight | 18/18 | 83.07229 [77.12298, 87.91965] | 42.77872 | 0.028734 |
| DIMACS/hash_weighted | baseline_weighted_conflict | 17/18 | 89.62746 [78.18664, 96.56223] | 43.77574 | 0.081896 |
| DIMACS/hash_weighted | enumerated_v03 | 17/18 | 85.46372 [74.03861, 92.83312] | 42.02264 | 0.156653 |
| DIMACS/hash_weighted | fixed_classical_1to2_search | 18/18 | 95.80689 [93.47507, 97.85260] | 49.01821 | 0.000836 |
| DIMACS/hash_weighted | free_v03 | 17/18 | 84.09845 [72.68023, 91.58308] | 41.40946 | 0.916941 |
| DIMACS/hash_weighted | guarded_continuation_64 | 15/18 | 78.76255 [61.70290, 94.03623] | 40.73196 | 0.895114 |
| DIMACS/hash_weighted | guided_primary_only_ablation | 17/18 | 87.07372 [75.58511, 94.44861] | 42.63849 | 0.801564 |
| DIMACS/hash_weighted | guided_v04 | 17/18 | 87.07372 [75.58511, 94.44861] | 42.63849 | 0.805619 |
| DIMACS/hash_weighted | guided_v04_full_interface | 17/18 | 87.07372 [75.58511, 94.44861] | 42.63849 | 0.888295 |
| DIMACS/hash_weighted | legacy_continuation_g18 | 12/18 | 63.03181 [41.36161, 83.93109] | 30.77646 | 2.528628 |
| DIMACS/hash_weighted | legacy_guided_g05 | 13/18 | 65.93865 [45.37305, 83.27414] | 35.54619 | 1.436290 |
| DIMACS/hash_weighted | prior_guided_controls | 15/18 | 76.26246 [58.82811, 90.96959] | 39.69167 | 0.691785 |
| DIMACS/hash_weighted | rule_v03 | 17/18 | 85.60556 [74.19608, 92.90761] | 42.06359 | 0.079236 |
| SATLIB/unit | CHILS | 90/90 | 99.96768 [99.92690, 99.99658] | 74.52839 | 5.008652 |
| SATLIB/unit | CHILS_ILS | 90/90 | 99.90800 [99.85188, 99.95231] | 74.48438 | 5.015830 |
| SATLIB/unit | HiGHS_MILP | 30/30 | 98.04900 [97.10053, 98.83261] | 73.11474 | 10.011441 |
| SATLIB/unit | M2WIS | 90/90 | 99.71184 [99.62280, 99.80390] | 74.33853 | 5.208442 |
| SATLIB/unit | Struction | 90/90 | 96.91568 [96.32565, 97.50444] | 72.25677 | 5.022273 |
| SATLIB/unit | WeightedBR | 90/90 | 99.63578 [99.53156, 99.73358] | 74.28036 | 5.019868 |
| SATLIB/unit | baseline | 30/30 | 98.80288 [98.53428, 99.06230] | 73.65815 | 1.970985 |
| SATLIB/unit | baseline_degree | 30/30 | 98.80288 [98.53428, 99.06230] | 73.65815 | 1.950435 |
| SATLIB/unit | baseline_structural_ratio | 20/30 | 66.01875 [46.29375, 82.51188] | 49.56729 | 2.651746 |
| SATLIB/unit | baseline_v02_joint | 20/30 | 66.01875 [46.29375, 82.51188] | 49.56729 | 3.426774 |
| SATLIB/unit | baseline_weight | 30/30 | 92.40709 [91.60116, 93.17343] | 68.90002 | 0.948016 |
| SATLIB/unit | baseline_weighted_conflict | 30/30 | 98.80288 [98.53428, 99.06230] | 73.65815 | 2.054324 |
| SATLIB/unit | enumerated_v03 | 10/30 | 32.85714 [16.44689, 49.37729] | 24.58034 | 5.000398 |
| SATLIB/unit | fixed_classical_1to2_search | 30/30 | 98.94151 [98.72242, 99.15352] | 73.76283 | 0.001971 |
| SATLIB/unit | free_v03 | 10/30 | 32.71062 [16.33700, 49.08425] | 24.48838 | 5.000429 |
| SATLIB/unit | guarded_continuation_64 | 20/30 | 65.93625 [46.27496, 82.41027] | 49.50641 | 4.638734 |
| SATLIB/unit | guided_primary_only_ablation | 10/30 | 32.93040 [16.48352, 49.41484] | 24.64533 | 5.000360 |
| SATLIB/unit | guided_v04 | 10/30 | 32.93040 [16.48352, 49.41484] | 24.64533 | 5.000333 |
| SATLIB/unit | guided_v04_full_interface | 10/30 | 32.93040 [16.48352, 49.41484] | 24.64533 | 5.000319 |
| SATLIB/unit | legacy_continuation_g18 | 0/30 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000477 |
| SATLIB/unit | legacy_guided_g05 | 20/30 | 66.01875 [46.29375, 82.51188] | 49.56729 | 4.108391 |
| SATLIB/unit | prior_guided_controls | 20/30 | 66.03404 [46.30919, 82.53571] | 49.57916 | 3.358718 |
| SATLIB/unit | rule_v03 | 30/30 | 98.80288 [98.53428, 99.06230] | 73.65815 | 1.969726 |
| SATLIB/hash_weighted | CHILS | 90/90 | 99.99515 [99.98752, 99.99974] | 71.84047 | 5.008684 |
| SATLIB/hash_weighted | CHILS_ILS | 90/90 | 99.93173 [99.86047, 99.97731] | 71.79615 | 5.015993 |
| SATLIB/hash_weighted | HiGHS_MILP | 30/30 | 99.95852 [99.90961, 99.99072] | 71.81484 | 1.877830 |
| SATLIB/hash_weighted | M2WIS | 90/90 | 99.99199 [99.98401, 99.99843] | 71.83824 | 5.171279 |
| SATLIB/hash_weighted | Struction | 90/90 | 98.04554 [97.40609, 98.64948] | 70.45487 | 5.022015 |
| SATLIB/hash_weighted | WeightedBR | 90/90 | 99.72639 [99.59064, 99.83529] | 71.65055 | 5.021198 |
| SATLIB/hash_weighted | baseline | 30/30 | 92.13885 [91.45394, 92.73903] | 66.19612 | 1.904293 |
| SATLIB/hash_weighted | baseline_degree | 30/30 | 92.13885 [91.45394, 92.73903] | 66.19612 | 1.870433 |
| SATLIB/hash_weighted | baseline_structural_ratio | 20/30 | 59.33732 [41.77706, 74.17674] | 42.95803 | 2.560513 |
| SATLIB/hash_weighted | baseline_v02_joint | 20/30 | 60.11180 [42.43157, 75.11396] | 43.52380 | 3.320664 |
| SATLIB/hash_weighted | baseline_weight | 30/30 | 92.86060 [92.00661, 93.76382] | 66.70709 | 0.901532 |
| SATLIB/hash_weighted | baseline_weighted_conflict | 30/30 | 94.81901 [94.39228, 95.26795] | 68.12846 | 1.938599 |
| SATLIB/hash_weighted | enumerated_v03 | 10/30 | 31.18142 [15.61943, 46.98880] | 22.69267 | 5.000423 |
| SATLIB/hash_weighted | fixed_classical_1to2_search | 30/30 | 98.29244 [97.71214, 98.79814] | 70.62731 | 0.028748 |
| SATLIB/hash_weighted | free_v03 | 10/30 | 29.66983 [14.80449, 44.62421] | 21.59710 | 5.000389 |
| SATLIB/hash_weighted | guarded_continuation_64 | 11/30 | 35.08629 [19.04086, 53.75859] | 25.57320 | 5.000548 |
| SATLIB/hash_weighted | guided_primary_only_ablation | 10/30 | 31.04546 [15.48281, 46.66560] | 22.59513 | 5.000316 |
| SATLIB/hash_weighted | guided_v04 | 10/30 | 31.04546 [15.48281, 46.66560] | 22.59513 | 5.000370 |
| SATLIB/hash_weighted | guided_v04_full_interface | 10/30 | 31.04546 [15.48281, 46.66560] | 22.59513 | 5.000354 |
| SATLIB/hash_weighted | legacy_continuation_g18 | 0/30 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000476 |
| SATLIB/hash_weighted | legacy_guided_g05 | 20/30 | 57.44046 [40.53754, 71.77755] | 41.59198 | 3.997127 |
| SATLIB/hash_weighted | prior_guided_controls | 20/30 | 63.90461 [44.94606, 79.89376] | 46.27297 | 3.072843 |
| SATLIB/hash_weighted | rule_v03 | 30/30 | 93.90293 [93.09802, 94.55990] | 67.46810 | 1.886385 |
### public: long_prespecified_subset

| Population | Method | Completed / requested runs | Failure-zero competitive ratio, % (95% CI) | Mean formal-upper ratio, % | Median wall, s |
|---|---|---:|---:|---:|---:|
| DIMACS/unit | CHILS | 54/54 | 100.00000 [100.00000, 100.00000] | 53.47556 | 30.009663 |
| DIMACS/unit | HiGHS_MILP | 18/18 | 82.58568 [66.87208, 94.30949] | 47.35115 | 10.020307 |
| DIMACS/unit | M2WIS | 54/54 | 100.00000 [100.00000, 100.00000] | 53.47556 | 20.804755 |
| DIMACS/unit | Struction | 54/54 | 99.65528 [99.14222, 100.00000] | 53.34395 | 4.681153 |
| DIMACS/unit | WeightedBR | 54/54 | 94.16905 [86.79428, 99.57111] | 51.13448 | 30.016218 |
| DIMACS/unit | baseline | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.075964 |
| DIMACS/unit | baseline_degree | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.044993 |
| DIMACS/unit | baseline_structural_ratio | 15/18 | 73.77043 [56.15915, 88.64664] | 40.33051 | 0.648569 |
| DIMACS/unit | baseline_v02_joint | 13/18 | 64.51117 [44.46905, 82.85698] | 36.50455 | 1.324297 |
| DIMACS/unit | baseline_weight | 18/18 | 72.74964 [63.55241, 81.69337] | 42.09919 | 0.027709 |
| DIMACS/unit | baseline_weighted_conflict | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.081496 |
| DIMACS/unit | enumerated_v03 | 17/18 | 85.79667 [73.60007, 94.30766] | 44.23028 | 0.160987 |
| DIMACS/unit | fixed_classical_1to2_search | 18/18 | 92.95333 [87.65877, 96.90717] | 50.37068 | 0.000619 |
| DIMACS/unit | free_v03 | 17/18 | 82.20281 [69.90807, 91.17666] | 42.71721 | 0.934131 |
| DIMACS/unit | guarded_continuation_64 | 15/18 | 74.66349 [56.94388, 89.63643] | 40.61075 | 0.879190 |
| DIMACS/unit | guided_primary_only_ablation | 17/18 | 80.52837 [68.19607, 90.02609] | 42.21071 | 0.823790 |
| DIMACS/unit | guided_v04 | 17/18 | 80.52837 [68.19607, 90.02609] | 42.21071 | 0.828677 |
| DIMACS/unit | guided_v04_full_interface | 17/18 | 80.52837 [68.19607, 90.02609] | 42.21071 | 0.903350 |
| DIMACS/unit | legacy_continuation_g18 | 12/18 | 62.09890 [40.59096, 82.12649] | 31.72140 | 2.544076 |
| DIMACS/unit | legacy_guided_g05 | 13/18 | 62.90093 [43.18146, 80.87703] | 35.96338 | 1.436484 |
| DIMACS/unit | prior_guided_controls | 15/18 | 73.75228 [55.85013, 88.79331] | 40.33760 | 0.688264 |
| DIMACS/unit | rule_v03 | 17/18 | 85.04087 [72.21839, 94.74608] | 43.93955 | 0.079332 |
| SATLIB/unit | CHILS | 9/9 | 100.00000 [100.00000, 100.00000] | 76.66649 | 30.008642 |
| SATLIB/unit | HiGHS_MILP | 3/3 | 98.51564 [96.92308, 100.00000] | 75.56450 | 10.011356 |
| SATLIB/unit | M2WIS | 9/9 | 99.74453 [99.54128, 100.00000] | 76.47355 | 30.212661 |
| SATLIB/unit | Struction | 9/9 | 98.53305 [97.12821, 100.00000] | 75.57492 | 30.022012 |
| SATLIB/unit | WeightedBR | 9/9 | 99.67678 [99.23547, 100.00000] | 76.41966 | 30.020998 |
| SATLIB/unit | baseline | 3/3 | 98.46718 [97.24771, 100.00000] | 75.50884 | 1.959879 |
| SATLIB/unit | baseline_degree | 3/3 | 98.46718 [97.24771, 100.00000] | 75.50884 | 1.931453 |
| SATLIB/unit | baseline_structural_ratio | 2/3 | 66.05505 [0.00000, 100.00000] | 51.90370 | 2.630923 |
| SATLIB/unit | baseline_v02_joint | 2/3 | 66.05505 [0.00000, 100.00000] | 51.90370 | 3.476352 |
| SATLIB/unit | baseline_weight | 3/3 | 91.20469 [88.92308, 93.40659] | 69.97566 | 0.906157 |
| SATLIB/unit | baseline_weighted_conflict | 3/3 | 98.46718 [97.24771, 100.00000] | 75.50884 | 2.026470 |
| SATLIB/unit | enumerated_v03 | 1/3 | 31.86813 [0.00000, 95.60440] | 25.43860 | 5.000447 |
| SATLIB/unit | fixed_classical_1to2_search | 3/3 | 98.77299 [98.15385, 100.00000] | 75.74525 | 0.001963 |
| SATLIB/unit | free_v03 | 1/3 | 32.96703 [0.00000, 98.90110] | 26.31579 | 5.000236 |
| SATLIB/unit | guarded_continuation_64 | 2/3 | 66.05505 [0.00000, 100.00000] | 51.90370 | 4.662062 |
| SATLIB/unit | guided_primary_only_ablation | 1/3 | 32.60073 [0.00000, 97.80220] | 26.02339 | 5.000291 |
| SATLIB/unit | guided_v04 | 1/3 | 32.60073 [0.00000, 97.80220] | 26.02339 | 5.000292 |
| SATLIB/unit | guided_v04_full_interface | 1/3 | 32.60073 [0.00000, 97.80220] | 26.02339 | 5.000212 |
| SATLIB/unit | legacy_continuation_g18 | 0/3 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000273 |
| SATLIB/unit | legacy_guided_g05 | 2/3 | 66.05505 [0.00000, 100.00000] | 51.90370 | 4.097709 |
| SATLIB/unit | prior_guided_controls | 2/3 | 66.05505 [0.00000, 100.00000] | 51.90370 | 3.330251 |
| SATLIB/unit | rule_v03 | 3/3 | 98.46718 [97.24771, 100.00000] | 75.50884 | 1.957437 |
### sparse: short

| Population | Method | Completed / requested runs | Failure-zero competitive ratio, % (95% CI) | Mean formal-upper ratio, % | Median wall, s |
|---|---|---:|---:|---:|---:|
| SNAP/unit | CHILS | 12/12 | 100.00000 [100.00000, 100.00000] | 86.66702 | 5.142228 |
| SNAP/unit | CHILS_ILS | 12/12 | 99.99037 [99.97610, 100.00000] | 86.65955 | 5.140935 |
| SNAP/unit | HiGHS_MILP | 4/4 | 91.06119 [73.18356, 100.00000] | 79.99321 | 0.688588 |
| SNAP/unit | M2WIS | 12/12 | 99.95220 [99.85660, 100.00000] | 86.63133 | 1.167943 |
| SNAP/unit | Struction | 12/12 | 98.51020 [95.53059, 100.00000] | 85.55472 | 0.163294 |
| SNAP/unit | WeightedBR | 12/12 | 96.65392 [89.96176, 100.00000] | 84.16880 | 0.178020 |
| SNAP/unit | baseline | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.001043 |
| SNAP/unit | baseline_degree | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000531 |
| SNAP/unit | baseline_structural_ratio | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000539 |
| SNAP/unit | baseline_v02_joint | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000561 |
| SNAP/unit | baseline_weight | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000527 |
| SNAP/unit | baseline_weighted_conflict | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000672 |
| SNAP/unit | enumerated_v03 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000770 |
| SNAP/unit | fixed_classical_1to2_search | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 0.000000 |
| SNAP/unit | free_v03 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000637 |
| SNAP/unit | guarded_continuation_64 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000826 |
| SNAP/unit | guided_primary_only_ablation | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000515 |
| SNAP/unit | guided_v04 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000546 |
| SNAP/unit | guided_v04_full_interface | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000555 |
| SNAP/unit | legacy_continuation_g18 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000525 |
| SNAP/unit | legacy_guided_g05 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000740 |
| SNAP/unit | prior_guided_controls | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000807 |
| SNAP/unit | rule_v03 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000629 |
| SNAP/hash_weighted | CHILS | 12/12 | 100.00000 [100.00000, 100.00000] | 81.72291 | 5.098297 |
| SNAP/hash_weighted | CHILS_ILS | 12/12 | 100.00000 [100.00000, 100.00000] | 81.72291 | 5.096110 |
| SNAP/hash_weighted | HiGHS_MILP | 4/4 | 92.14773 [76.44318, 100.00000] | 76.53890 | 0.828488 |
| SNAP/hash_weighted | M2WIS | 12/12 | 99.98018 [99.94053, 100.00000] | 81.70982 | 1.169387 |
| SNAP/hash_weighted | Struction | 12/12 | 98.82312 [96.46935, 100.00000] | 80.94594 | 0.165446 |
| SNAP/hash_weighted | WeightedBR | 9/12 | 75.00000 [25.00000, 100.00000] | 65.21810 | 0.177945 |
| SNAP/hash_weighted | baseline | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000783 |
| SNAP/hash_weighted | baseline_degree | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000588 |
| SNAP/hash_weighted | baseline_structural_ratio | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000599 |
| SNAP/hash_weighted | baseline_v02_joint | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000682 |
| SNAP/hash_weighted | baseline_weight | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000478 |
| SNAP/hash_weighted | baseline_weighted_conflict | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000734 |
| SNAP/hash_weighted | enumerated_v03 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000699 |
| SNAP/hash_weighted | fixed_classical_1to2_search | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 0.000000 |
| SNAP/hash_weighted | free_v03 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000686 |
| SNAP/hash_weighted | guarded_continuation_64 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000786 |
| SNAP/hash_weighted | guided_primary_only_ablation | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000548 |
| SNAP/hash_weighted | guided_v04 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000716 |
| SNAP/hash_weighted | guided_v04_full_interface | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000680 |
| SNAP/hash_weighted | legacy_continuation_g18 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000545 |
| SNAP/hash_weighted | legacy_guided_g05 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000650 |
| SNAP/hash_weighted | prior_guided_controls | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000685 |
| SNAP/hash_weighted | rule_v03 | 0/4 | 0.00000 [0.00000, 0.00000] | 0.00000 | 5.000762 |

Competitive normalization is descriptive reward relative to the strongest archived independently verified feasible witness in the same context. It is not a claim of optimality. Exact clique-upper ratios and reference coverage are also retained. A missing reference remains unavailable, and a failed solver remains assigned with reward zero; neither silently disappears. Wall time includes all assigned runs. Native official budgets, cooperative constructive CPU targets, MILP and local-search budgets differ. Long-budget results remain a separate prespecified subset. Full-interface parity is assessed only when both executions complete, with the unassessable count retained.
