# Fixed-AST heap execution analysis

Three repeated paired executions use the unchanged TRAIN-frozen primary and degree ASTs. Failures remain null; CPU/work ratios require both backends complete. Source-cluster bootstrap uses the per-context median ratio, not repeated timings as independent graph samples.

| Population/AST | Assigned contexts | Assessable pairs | Mean context-median CPU ratio (95% CI) | Work ratio |
|---|---:|---:|---:|---:|
| fresh/c3/primary | 24 | 72 | 4.6110 [4.0887, 5.1853] | 4.6367 |
| fresh/c3/degree | 24 | 72 | 3.7954 [3.4008, 4.2480] | 2.6263 |
| fresh/dense_long/primary | 216 | 648 | 1.1871 [1.1499, 1.2291] | 1.1882 |
| fresh/dense_long/degree | 216 | 648 | 0.8714 [0.8558, 0.8870] | 0.7822 |
| fresh/standard/primary | 216 | 648 | 15.4511 [12.9081, 18.1896] | 13.3416 |
| fresh/standard/degree | 216 | 648 | 10.3792 [8.7810, 12.1092] | 5.9803 |

fresh assigned/completed counts: `{"degree/full_scan/assigned": 1368, "degree/full_scan/completed": 1368, "degree/heap/assigned": 1368, "degree/heap/completed": 1368, "primary/full_scan/assigned": 1368, "primary/full_scan/completed": 1368, "primary/heap/assigned": 1368, "primary/heap/completed": 1368}`.

| sparse/ca-GrQc/primary | 2 | 0 | unassessable | unassessable |
| sparse/ca-GrQc/degree | 2 | 0 | unassessable | unassessable |
| sparse/ca-HepPh/primary | 2 | 0 | unassessable | unassessable |
| sparse/ca-HepPh/degree | 2 | 0 | unassessable | unassessable |
| sparse/ca-HepTh/primary | 2 | 0 | unassessable | unassessable |
| sparse/ca-HepTh/degree | 2 | 0 | unassessable | unassessable |
| sparse/facebook_combined/primary | 2 | 0 | unassessable | unassessable |
| sparse/facebook_combined/degree | 2 | 0 | unassessable | unassessable |

sparse assigned/completed counts: `{"degree/full_scan/assigned": 24, "degree/full_scan/completed": 0, "degree/heap/assigned": 24, "degree/heap/completed": 18, "primary/full_scan/assigned": 24, "primary/full_scan/completed": 0, "primary/heap/assigned": 24, "primary/heap/completed": 7}`.

The four SNAP sources supply eight fixed contexts; their two weight modes share topology. This is a post-diagnostic execution extension, not a change to the original confirmatory quality study. Missing full-run parity is unassessable, and a timing ratio is not a solution-quality comparison. CPU target overshoot remains observed. No model or conditional oracle participates online.
