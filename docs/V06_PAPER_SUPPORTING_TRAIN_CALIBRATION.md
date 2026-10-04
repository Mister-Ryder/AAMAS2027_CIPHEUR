# Supporting TRAIN calibration for the V06 paper

The independently authored experimental fragment originally contained this
calibration table. Root moved the detailed table out of the eight-page body to
reserve space for the frozen proposed-policy/public-solver TEST comparison.
No outcome, method, unsupported request or unfavorable contrast is discarded.
The original section bytes remain in
`paper/drafts/v06/archives/initial_author_sections_001/experiments.tex`.
Its original SHA256 is
`0280c8f9f54b2729e359e76ff16bfc751acd8183b60b08bcbdd51a829551ab8a`.

These are completed native TRAIN calibration results at a common one-second
nominal internal target. They are not proposed-program performance results.
Raw reward means use valid outputs only, with coverage shown before interpreting
quality. Stochastic native methods use three fixed seeds per source;
deterministic methods and Degree use one. Wall values are median wrapper seconds.

| Method | WDP raw reward | Valid/assigned | Wall | UAI Segmentation raw reward | Valid/assigned | Wall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CHILS | **84,224,796.39** | 75/75 | 1.509 | **1,670.450** | 9/9 | 1.014 |
| CHILS ILS | 84,221,656.72 | 75/75 | 1.516 | **1,670.450** | 9/9 | 1.019 |
| M²WIS | — | 0/75 | 0.003 rejection | **1,670.450** | 9/9 | 0.075 |
| Struction | — | 0/25 | 0.004 rejection | **1,670.450** | 3/3 | 0.024 |
| WeightedBR | — | 0/25 | 0.003 rejection | **1,670.450** | 3/3 | **0.021** |
| Shared Degree repair | 48,279,098.24 | 25/25 | **1.000** | 1,663.217 | 3/3 | 0.347 |

WDP nulls arise from the pinned signed-32-bit encoding compatibility check,
not zero quality or algorithmic inability. Rejection latency is not solver
efficiency. All original objectives and exact scale/complement mappings remain
unchanged. Rewards must not be pooled across these families.

Across all three nominal targets (0.1/1/5 seconds), 633 of 1,008 native calibration
assignments return checked feasible incumbents and 375 are explicit numerical
incompatibilities. WDP CHILS median wrapper walls are 0.598/1.509/5.521 seconds.
Startup, conversion and validation prevent treating nominal targets as matched
hard end-to-end deadlines.

The separate common-component calibration has 960 feasible assignments over
32 sources. Warm Degree improves its matched half-target CHILS initializer in
4/288 cases, with 284 ties and no decrease. Against full-target CHILS it
wins/ties/loses in **2/222/64**. The main body retains this unfavorable comparison:
shared mature search does not establish a witness-guidance benefit. These
calibration outcomes were not supplied to R2 authoring or used in its selector.

The source bindings, exact calculation checks and published citations are in
`paper/drafts/v06/experiments_review.md`; the component protocol/results are in
[CLASSIC_COMPONENTS_TRAIN_V06.md](CLASSIC_COMPONENTS_TRAIN_V06.md).

The redundant catalogue-prefix table was also moved from the body. Its full
fixed scope remains 4/8/16/53 expressions: the first three prefixes are unresolved
cycles (4/7/7 master rechecks), and the full catalogue is acyclic after nine
rechecks with four additions at exact minimum additive standalone cost 1,371,468.
Unresolved subset costs are not valid repair optima. All four outcomes remain
in the main prose and [catalogue findings](V06_CATALOGUE_COST_FINDINGS.md).
