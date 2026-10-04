# V06 final performance curves and interpretation

These figures use only the final audit-backed aggregate analysis. No solver, program, bootstrap, source selection, or denominator was rerun.

## Scientific conclusions

- At five seconds, warm joint-W has an exact zero paired increment over same-track Degree and EoH-DSL in every defined non-C3 family. All six fresh scheduling family means match the fixed CHILS seed-1 reference.
- WDP 5xx joint-W zero gain is defined on 2/4 source groups. Its same-source paired difference against Degree and EoH is zero. Their full-coverage means of about -0.36% are not directly comparable to that partial cohort as a claimed joint-program advantage.
- Joint-W Grids complete-source coverage is 8/10, 1/10, and 0/10 at nominal targets 0.1, 1, and 5. At five seconds 30/40 individual joint assignments succeed, but no source has all four members successful. Missing cohort quality is not zero quality.
- Cold joint-W dense-long ground-scarce quality is -53.4153%, -3.2844%, and -1.2004% against CHILS seed1. Its five-second paired difference against same-track Degree is -0.4511%, 95% source interval [-0.6111%, -0.2828%].
- Five-second mean standalone CPU at standard balanced is 4.2462 s for warm joint-W versus 3.8820 s for warm EoH at equal quality. Dense-long ground scarce is 5.0344 versus 4.8817 s. No speed or general quality superiority follows from these comparisons.
- Across the full returned matrix, 82 programme/repair errors and 525 unsupported native encoding requests remain failures or null quality. A zero-error independent verification is not a claim that all research assignments succeeded.

## Fixed sources and outputs

- analysis_path: `E:\01-Joycecyq\2026-AAMAS\第二篇\experiments\analysis\v06\performance_TEST_analysis_v06_003\analysis.json`
- analysis_sha256: `839324710784ba71ee40c25ea199b527ff346fb7ec1209f97756ed2d9513aaf9`
- audit_path: `E:\01-Joycecyq\2026-AAMAS\第二篇\experiments\analysis\v06\performance_TEST_audit_v06_003.json`
- audit_sha256: `db7209ad60c4d2f1cff07ec50b2bf26fd5d473153c56d809ff416f6781de22d6`
- archive_sha256: `196848904ee99f4ec4bcc311edbddeab60893d39599dc6cc18e4adffad87c5e1`
- audited_rows_sha256: `24b6f0302a95d144d3d7b0c17226abda2030370dd8ba73fd8e8bae2394b1b948`
- analysis_source_sha256: `b01f05e1706d7a8ea10d2629f3c924170855b693f6c621bb80d46a370a5b88d2`
- audit_source_sha256: `59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a`
- Figure builder SHA256: `4f17c7c1ca8057a7f2061ece38689bd9c3520c65240267c6d2fbf4674fa43297`
- Final figure receipt SHA256: `74db4251e376a5dd98d44fc01135a5dbae84c1ec2212f3eb49e689620aa13db7`
- Output directory: `experiments/analysis/v06/performance_figures_v06_003_render_002`
- 15 separate gain PDF/PNG panels, four fixed-main CPU/gain PDF/PNG panels, and one shared legend PDF/PNG are preserved. The four main gain PDFs and legend were copied into `paper/figures`.
- The first presentation attempt stopped on an automatic locator text-bounds guard before the last panel. Its 14 partial gain panels remain under `performance_figures_v06_003`. The successful rendering only prunes outer automatic tick labels; it does not alter any plotted x/y statistic, interval, cohort, source, or scientific execution.

## Interpretation and geometry

- Main curve families were fixed before outcomes: standard balanced, dense-long ground scarce, WDP 4xx, and UAI Grids. All other families and both exploratory C3 tracks remain available below and as separate figures.
- Native panels are 3.35 by 2.15 inches, with Arial at least 9 pt and a separate 7 by 0.52 inch shared legend. Main panels use the same y range, including zero and every negative mean/interval. Four main PNGs were visually inspected after rendering; titles, axes, coverage footers, and missing line gaps are visible.
- The curve x coordinate is the nominal solver wall target, not elapsed optimization time. The CPU panels show actual measured standalone CPU means ordered by nominal target, not an anytime trajectory or learning curve.
- Warm standalone cost charges the full reused common CHILS initializer to each policy. CPU means can include measured failed policy attempts and have different denominators from complete-cohort quality. Graph loading is separately labeled in the original analysis; the CPU panels do not silently add or remove it.
- Sources/pairs, not author runs, are bootstrap units. The 95% intervals reuse the original 2,000-replicate seed-261004 statistics conditional on frozen programmes; they do not establish a population-level LLM effect.
- Public corpus exposure and fixed source-cluster withholding remain explicit. The four EoH outputs retain the same common seed AST; they are not four newly independent programme identities.

## Complete fixed-family curve values

Each gain cell is stored mean % [95% CI], with defined complete-cohort/reference source-context pairs over all assigned contexts. The CPU table reuses stored conditional mean seconds and its defined-context count. No raw objective is pooled across families.

### fresh_standard_balanced / standard_balanced

Assigned contexts: 36; assigned source/pair clusters: 18. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| CHILS-ILS (3) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| M2WIS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Struction | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| WeightedBR | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Joint W / Degree | -1.2699 [-1.3905, -1.1378]; 36/36 | -0.8706 [-1.0366, -0.6952]; 36/36 | -0.7317 [-0.8972, -0.5522]; 36/36 |
| Joint W / CHILS | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| EoH-DSL / CHILS | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1125; 36/36 | 1.0129; 36/36 | 5.0134; 36/36 |
| CHILS-ILS (3) | 0.1205; 36/36 | 1.0230; 36/36 | 5.0223; 36/36 |
| M2WIS (3 seeds) | 0.1861; 36/36 | 0.1862; 36/36 | 0.1881; 36/36 |
| Struction | 0.0290; 36/36 | 0.0289; 36/36 | 0.0297; 36/36 |
| WeightedBR | 0.0227; 36/36 | 0.0230; 36/36 | 0.0230; 36/36 |
| Joint W / Degree | 0.1028; 36/36 | 1.0028; 36/36 | 1.9208; 36/36 |
| Joint W / CHILS | 0.1174; 36/36 | 1.0182; 36/36 | 4.2462; 36/36 |
| EoH-DSL / CHILS | 0.1174; 36/36 | 1.0177; 36/36 | 3.8820; 36/36 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 108/108 | 108/108 | 108/108 |
| CHILS-ILS (3) | 108/108 | 108/108 | 108/108 |
| M2WIS (3 seeds) | 108/108 | 108/108 | 108/108 |
| Struction | 36/36 | 36/36 | 36/36 |
| WeightedBR | 36/36 | 36/36 | 36/36 |
| Joint W / Degree | 144/144 | 144/144 | 144/144 |
| Joint W / CHILS | 144/144 | 144/144 | 144/144 |
| EoH-DSL / CHILS | 144/144 | 144/144 | 144/144 |

### fresh_standard_ground_scarce / standard_ground_scarce

Assigned contexts: 36; assigned source/pair clusters: 18. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| CHILS-ILS (3) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| M2WIS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Struction | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| WeightedBR | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Joint W / Degree | -1.7389 [-1.9273, -1.5402]; 36/36 | -1.2208 [-1.4229, -0.9982]; 36/36 | -1.0158 [-1.2173, -0.7943]; 36/36 |
| Joint W / CHILS | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| EoH-DSL / CHILS | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1127; 36/36 | 1.0133; 36/36 | 5.0136; 36/36 |
| CHILS-ILS (3) | 0.1210; 36/36 | 1.0225; 36/36 | 5.0238; 36/36 |
| M2WIS (3 seeds) | 0.2282; 36/36 | 0.2292; 36/36 | 0.2294; 36/36 |
| Struction | 0.0303; 36/36 | 0.0293; 36/36 | 0.0304; 36/36 |
| WeightedBR | 0.0230; 36/36 | 0.0229; 36/36 | 0.0243; 36/36 |
| Joint W / Degree | 0.1033; 36/36 | 1.0021; 36/36 | 1.9803; 36/36 |
| Joint W / CHILS | 0.1179; 36/36 | 1.0183; 36/36 | 4.4560; 36/36 |
| EoH-DSL / CHILS | 0.1179; 36/36 | 1.0183; 36/36 | 4.0299; 36/36 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 108/108 | 108/108 | 108/108 |
| CHILS-ILS (3) | 108/108 | 108/108 | 108/108 |
| M2WIS (3 seeds) | 108/108 | 108/108 | 108/108 |
| Struction | 36/36 | 36/36 | 36/36 |
| WeightedBR | 36/36 | 36/36 | 36/36 |
| Joint W / Degree | 144/144 | 144/144 | 144/144 |
| Joint W / CHILS | 144/144 | 144/144 | 144/144 |
| EoH-DSL / CHILS | 144/144 | 144/144 | 144/144 |

### fresh_standard_satellite_scarce / standard_satellite_scarce

Assigned contexts: 36; assigned source/pair clusters: 18. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| CHILS-ILS (3) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| M2WIS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Struction | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| WeightedBR | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Joint W / Degree | -1.2844 [-1.4582, -1.1130]; 36/36 | -0.8688 [-1.0535, -0.6689]; 36/36 | -0.6891 [-0.8549, -0.5113]; 36/36 |
| Joint W / CHILS | -0.0014 [-0.0035, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| EoH-DSL / CHILS | -0.0014 [-0.0035, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1128; 36/36 | 1.0135; 36/36 | 5.0143; 36/36 |
| CHILS-ILS (3) | 0.1198; 36/36 | 1.0232; 36/36 | 5.0245; 36/36 |
| M2WIS (3 seeds) | 0.1983; 36/36 | 0.1975; 36/36 | 0.1966; 36/36 |
| Struction | 0.0306; 36/36 | 0.0291; 36/36 | 0.0290; 36/36 |
| WeightedBR | 0.0242; 36/36 | 0.0232; 36/36 | 0.0230; 36/36 |
| Joint W / Degree | 0.1030; 36/36 | 1.0024; 36/36 | 2.0207; 36/36 |
| Joint W / CHILS | 0.1182; 36/36 | 1.0181; 36/36 | 4.3540; 36/36 |
| EoH-DSL / CHILS | 0.1181; 36/36 | 1.0181; 36/36 | 3.9522; 36/36 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 108/108 | 108/108 | 108/108 |
| CHILS-ILS (3) | 108/108 | 108/108 | 108/108 |
| M2WIS (3 seeds) | 108/108 | 108/108 | 108/108 |
| Struction | 36/36 | 36/36 | 36/36 |
| WeightedBR | 36/36 | 36/36 | 36/36 |
| Joint W / Degree | 144/144 | 144/144 | 144/144 |
| Joint W / CHILS | 144/144 | 144/144 | 144/144 |
| EoH-DSL / CHILS | 144/144 | 144/144 | 144/144 |

### fresh_dense_long_balanced / dense_long_balanced

Assigned contexts: 36; assigned source/pair clusters: 18. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | -0.0024 [-0.0072, 0.0000]; 36/36 | -0.0028 [-0.0084, 0.0000]; 36/36 | -0.0014 [-0.0042, 0.0000]; 36/36 |
| CHILS-ILS (3) | -0.0024 [-0.0072, 0.0000]; 36/36 | -0.0066 [-0.0174, 0.0000]; 36/36 | -0.0042 [-0.0127, 0.0000]; 36/36 |
| M2WIS (3 seeds) | 0.0010 [-0.0073, 0.0118]; 36/36 | -0.0032 [-0.0088, 0.0000]; 36/36 | -0.0032 [-0.0088, 0.0000]; 36/36 |
| Struction | -25.0235 [-27.1567, -22.3215]; 36/36 | -16.3182 [-20.3218, -11.9154]; 36/36 | -14.4920 [-18.8615, -9.7489]; 36/36 |
| WeightedBR | -3.3981 [-4.2179, -2.6579]; 36/36 | -0.5617 [-0.7310, -0.3948]; 36/36 | -0.1970 [-0.2895, -0.1094]; 36/36 |
| Joint W / Degree | -51.3807 [-64.2575, -37.7125]; 36/36 | -4.7083 [-5.4618, -3.8925]; 36/36 | -2.3550 [-2.9557, -1.6944]; 36/36 |
| Joint W / CHILS | -0.0130 [-0.0329, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| EoH-DSL / CHILS | -0.0130 [-0.0329, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1549; 36/36 | 1.0561; 36/36 | 5.0569; 36/36 |
| CHILS-ILS (3) | 0.1598; 36/36 | 1.0620; 36/36 | 5.0622; 36/36 |
| M2WIS (3 seeds) | 0.6527; 36/36 | 1.4859; 36/36 | 5.0436; 36/36 |
| Struction | 0.1821; 36/36 | 1.0211; 36/36 | 4.4683; 36/36 |
| WeightedBR | 0.1798; 36/36 | 1.0791; 36/36 | 5.0789; 36/36 |
| Joint W / Degree | 0.1012; 36/36 | 1.0015; 36/36 | 4.5282; 36/36 |
| Joint W / CHILS | 0.1656; 36/36 | 1.0720; 36/36 | 5.0161; 36/36 |
| EoH-DSL / CHILS | 0.1657; 36/36 | 1.0721; 36/36 | 4.8543; 36/36 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 108/108 | 108/108 | 108/108 |
| CHILS-ILS (3) | 108/108 | 108/108 | 108/108 |
| M2WIS (3 seeds) | 108/108 | 108/108 | 108/108 |
| Struction | 36/36 | 36/36 | 36/36 |
| WeightedBR | 36/36 | 36/36 | 36/36 |
| Joint W / Degree | 144/144 | 144/144 | 144/144 |
| Joint W / CHILS | 144/144 | 144/144 | 144/144 |
| EoH-DSL / CHILS | 144/144 | 144/144 | 144/144 |

### fresh_dense_long_ground_scarce / dense_long_ground_scarce

Assigned contexts: 36; assigned source/pair clusters: 18. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| CHILS-ILS (3) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| M2WIS (3 seeds) | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Struction | -7.3686 [-12.0966, -2.9504]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| WeightedBR | -11.7028 [-18.5343, -4.9359]; 36/36 | -0.2390 [-0.3386, -0.1430]; 36/36 | -0.0467 [-0.0945, -0.0097]; 36/36 |
| Joint W / Degree | -53.4153 [-67.5587, -38.1721]; 36/36 | -3.2844 [-4.1853, -2.4616]; 36/36 | -1.2004 [-1.7862, -0.6484]; 36/36 |
| Joint W / CHILS | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| EoH-DSL / CHILS | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1817; 36/36 | 1.0816; 36/36 | 5.0826; 36/36 |
| CHILS-ILS (3) | 0.1869; 36/36 | 1.0868; 36/36 | 5.0873; 36/36 |
| M2WIS (3 seeds) | 0.8976; 36/36 | 1.0112; 36/36 | 1.0120; 36/36 |
| Struction | 0.1710; 36/36 | 0.2083; 36/36 | 0.2072; 36/36 |
| WeightedBR | 0.1922; 36/36 | 0.8858; 36/36 | 3.5876; 36/36 |
| Joint W / Degree | 0.1008; 36/36 | 1.0017; 36/36 | 4.7388; 36/36 |
| Joint W / CHILS | 0.1908; 36/36 | 1.0866; 36/36 | 5.0344; 36/36 |
| EoH-DSL / CHILS | 0.1907; 36/36 | 1.0866; 36/36 | 4.8817; 36/36 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 108/108 | 108/108 | 108/108 |
| CHILS-ILS (3) | 108/108 | 108/108 | 108/108 |
| M2WIS (3 seeds) | 108/108 | 108/108 | 108/108 |
| Struction | 36/36 | 36/36 | 36/36 |
| WeightedBR | 36/36 | 36/36 | 36/36 |
| Joint W / Degree | 144/144 | 144/144 | 144/144 |
| Joint W / CHILS | 144/144 | 144/144 | 144/144 |
| EoH-DSL / CHILS | 144/144 | 144/144 | 144/144 |

### fresh_dense_long_satellite_scarce / dense_long_satellite_scarce

Assigned contexts: 36; assigned source/pair clusters: 18. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0013 [0.0000, 0.0039]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| CHILS-ILS (3) | 0.0013 [0.0000, 0.0039]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| M2WIS (3 seeds) | 0.0019 [0.0000, 0.0058]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| Struction | -19.4261 [-24.8183, -14.0457]; 36/36 | -5.7899 [-8.7576, -3.0141]; 36/36 | -4.8654 [-7.8098, -2.1588]; 36/36 |
| WeightedBR | -12.6371 [-20.2497, -5.2370]; 36/36 | -0.1808 [-0.2940, -0.0807]; 36/36 | -0.0716 [-0.1265, -0.0254]; 36/36 |
| Joint W / Degree | -55.1840 [-68.1094, -41.2277]; 36/36 | -3.4765 [-4.5826, -2.5473]; 36/36 | -1.3420 [-2.0805, -0.6740]; 36/36 |
| Joint W / CHILS | -0.0011 [-0.0033, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |
| EoH-DSL / CHILS | -0.0011 [-0.0033, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 | 0.0000 [0.0000, 0.0000]; 36/36 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1727; 36/36 | 1.0739; 36/36 | 5.0744; 36/36 |
| CHILS-ILS (3) | 0.1771; 36/36 | 1.0787; 36/36 | 5.0774; 36/36 |
| M2WIS (3 seeds) | 0.8201; 36/36 | 1.1768; 36/36 | 2.2470; 36/36 |
| Struction | 0.1776; 36/36 | 0.4938; 36/36 | 1.6519; 36/36 |
| WeightedBR | 0.1937; 36/36 | 0.9963; 36/36 | 4.3404; 36/36 |
| Joint W / Degree | 0.1009; 36/36 | 1.0016; 36/36 | 4.7405; 36/36 |
| Joint W / CHILS | 0.1828; 36/36 | 1.0853; 36/36 | 5.0530; 36/36 |
| EoH-DSL / CHILS | 0.1830; 36/36 | 1.0854; 36/36 | 4.8900; 36/36 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 108/108 | 108/108 | 108/108 |
| CHILS-ILS (3) | 108/108 | 108/108 | 108/108 |
| M2WIS (3 seeds) | 108/108 | 108/108 | 108/108 |
| Struction | 36/36 | 36/36 | 36/36 |
| WeightedBR | 36/36 | 36/36 | 36/36 |
| Joint W / Degree | 144/144 | 144/144 | 144/144 |
| Joint W / CHILS | 144/144 | 144/144 | 144/144 |
| EoH-DSL / CHILS | 144/144 | 144/144 | 144/144 |

### WDP / WDP_1xx

Assigned contexts: 5; assigned source/pair clusters: 5. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.2459 [-0.4418, 0.8447]; 5/5 | -0.2736 [-0.9190, 0.2303]; 5/5 | 0.1119 [-0.3507, 0.7858]; 5/5 |
| CHILS-ILS (3) | 0.2459 [-0.4418, 0.8447]; 5/5 | -0.2100 [-1.4239, 1.1361]; 5/5 | -0.8382 [-2.6526, 1.0145]; 5/5 |
| M2WIS (3 seeds) | null [null, null]; 0/5 | null [null, null]; 0/5 | null [null, null]; 0/5 |
| Struction | null [null, null]; 0/5 | null [null, null]; 0/5 | null [null, null]; 0/5 |
| WeightedBR | null [null, null]; 0/5 | null [null, null]; 0/5 | null [null, null]; 0/5 |
| Joint W / Degree | -75.6645 [-76.9969, -74.3321]; 5/5 | -14.5479 [-17.0536, -12.3434]; 5/5 | -12.6894 [-14.1712, -10.8838]; 5/5 |
| Joint W / CHILS | -0.1902 [-0.5706, 0.0000]; 5/5 | -0.0736 [-0.2208, 0.0000]; 5/5 | -0.2634 [-0.7078, 0.0000]; 5/5 |
| EoH-DSL / CHILS | -0.1902 [-0.5706, 0.0000]; 5/5 | -0.0736 [-0.2208, 0.0000]; 5/5 | -0.2634 [-0.7078, 0.0000]; 5/5 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.5296; 5/5 | 1.4241; 5/5 | 5.4198; 5/5 |
| CHILS-ILS (3) | 0.5316; 5/5 | 1.4250; 5/5 | 5.4232; 5/5 |
| M2WIS (3 seeds) | 0.0027; 5/5 | 0.0027; 5/5 | 0.0028; 5/5 |
| Struction | 0.0027; 5/5 | 0.0027; 5/5 | 0.0027; 5/5 |
| WeightedBR | 0.0027; 5/5 | 0.0027; 5/5 | 0.0027; 5/5 |
| Joint W / Degree | 0.1004; 5/5 | 1.0003; 5/5 | 4.9427; 5/5 |
| Joint W / CHILS | 0.5361; 5/5 | 1.4192; 5/5 | 4.3580; 5/5 |
| EoH-DSL / CHILS | 0.5361; 5/5 | 1.4178; 5/5 | 3.9938; 5/5 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 15/15 | 15/15 | 15/15 |
| CHILS-ILS (3) | 15/15 | 15/15 | 15/15 |
| M2WIS (3 seeds) | 0/15 | 0/15 | 0/15 |
| Struction | 0/5 | 0/5 | 0/5 |
| WeightedBR | 0/5 | 0/5 | 0/5 |
| Joint W / Degree | 20/20 | 20/20 | 20/20 |
| Joint W / CHILS | 20/20 | 20/20 | 20/20 |
| EoH-DSL / CHILS | 20/20 | 20/20 | 20/20 |

### WDP / WDP_2xx

Assigned contexts: 6; assigned source/pair clusters: 6. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | -1.7890 [-4.5355, 0.9715]; 6/6 | -1.2230 [-2.6469, -0.3140]; 6/6 | -0.0272 [-0.5484, 0.5641]; 6/6 |
| CHILS-ILS (3) | -1.7890 [-4.5355, 0.9715]; 6/6 | -1.3653 [-2.4812, -0.3920]; 6/6 | -0.2260 [-1.0593, 0.4170]; 6/6 |
| M2WIS (3 seeds) | null [null, null]; 0/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| Struction | null [null, null]; 0/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| WeightedBR | null [null, null]; 0/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| Joint W / Degree | -64.3202 [-66.2807, -62.4315]; 6/6 | -65.3471 [-66.7136, -63.9949]; 6/6 | null [null, null]; 0/6 |
| Joint W / CHILS | -2.4743 [-4.6434, -0.5589]; 6/6 | -0.7887 [-2.0153, 0.0000]; 5/6 | 0.0000 [0.0000, 0.0000]; 5/6 |
| EoH-DSL / CHILS | -2.4743 [-4.6434, -0.5589]; 6/6 | -0.9238 [-1.8500, -0.1462]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.5951; 6/6 | 1.5064; 6/6 | 5.4988; 6/6 |
| CHILS-ILS (3) | 0.5963; 6/6 | 1.5022; 6/6 | 5.5053; 6/6 |
| M2WIS (3 seeds) | 0.0028; 6/6 | 0.0028; 6/6 | 0.0028; 6/6 |
| Struction | 0.0027; 6/6 | 0.0027; 6/6 | 0.0027; 6/6 |
| WeightedBR | 0.0027; 6/6 | 0.0027; 6/6 | 0.0027; 6/6 |
| Joint W / Degree | 0.1004; 6/6 | 1.0004; 6/6 | 3.1193; 6/6 |
| Joint W / CHILS | 0.5950; 6/6 | 1.4767; 6/6 | 3.9536; 6/6 |
| EoH-DSL / CHILS | 0.5950; 6/6 | 1.4929; 6/6 | 3.7278; 6/6 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 18/18 | 18/18 | 18/18 |
| CHILS-ILS (3) | 18/18 | 18/18 | 18/18 |
| M2WIS (3 seeds) | 0/18 | 0/18 | 0/18 |
| Struction | 0/6 | 0/6 | 0/6 |
| WeightedBR | 0/6 | 0/6 | 0/6 |
| Joint W / Degree | 24/24 | 24/24 | 18/24 |
| Joint W / CHILS | 24/24 | 23/24 | 23/24 |
| EoH-DSL / CHILS | 24/24 | 24/24 | 24/24 |

### WDP / WDP_4xx

Assigned contexts: 6; assigned source/pair clusters: 6. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.1438 [-0.9280, 1.1538]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 |
| CHILS-ILS (3) | 0.1593 [-0.9214, 1.1708]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 |
| M2WIS (3 seeds) | null [null, null]; 0/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| Struction | null [null, null]; 0/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| WeightedBR | null [null, null]; 0/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| Joint W / Degree | -61.5221 [-62.6473, -60.2903]; 6/6 | null [null, null]; 0/6 | null [null, null]; 0/6 |
| Joint W / CHILS | -1.3736 [-4.1207, 0.0000]; 5/6 | 0.0000 [0.0000, 0.0000]; 5/6 | 0.0000 [0.0000, 0.0000]; 5/6 |
| EoH-DSL / CHILS | -2.3120 [-4.6468, 0.0000]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 | 0.0000 [0.0000, 0.0000]; 6/6 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.3200; 6/6 | 1.1897; 6/6 | 5.1709; 6/6 |
| CHILS-ILS (3) | 0.3047; 6/6 | 1.1965; 6/6 | 5.2279; 6/6 |
| M2WIS (3 seeds) | 0.0014; 6/6 | 0.0014; 6/6 | 0.0014; 6/6 |
| Struction | 0.0013; 6/6 | 0.0013; 6/6 | 0.0013; 6/6 |
| WeightedBR | 0.0013; 6/6 | 0.0013; 6/6 | 0.0013; 6/6 |
| Joint W / Degree | 0.1003; 6/6 | 0.8367; 6/6 | 1.4435; 6/6 |
| Joint W / CHILS | 0.3205; 6/6 | 1.1530; 6/6 | 3.2935; 6/6 |
| EoH-DSL / CHILS | 0.3212; 6/6 | 1.0939; 6/6 | 3.1198; 6/6 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 18/18 | 18/18 | 18/18 |
| CHILS-ILS (3) | 18/18 | 18/18 | 18/18 |
| M2WIS (3 seeds) | 0/18 | 0/18 | 0/18 |
| Struction | 0/6 | 0/6 | 0/6 |
| WeightedBR | 0/6 | 0/6 | 0/6 |
| Joint W / Degree | 24/24 | 18/24 | 18/24 |
| Joint W / CHILS | 23/24 | 23/24 | 23/24 |
| EoH-DSL / CHILS | 24/24 | 24/24 | 24/24 |

### WDP / WDP_5xx

Assigned contexts: 4; assigned source/pair clusters: 4. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | -1.1585 [-3.9093, 0.4339]; 4/4 | 0.8876 [-1.0135, 2.7887]; 4/4 | -1.0378 [-2.8331, 1.4944]; 4/4 |
| CHILS-ILS (3) | -1.1585 [-3.9093, 0.4339]; 4/4 | 1.6339 [-2.1097, 6.6275]; 4/4 | -1.5325 [-3.1661, 0.8614]; 4/4 |
| M2WIS (3 seeds) | null [null, null]; 0/4 | null [null, null]; 0/4 | null [null, null]; 0/4 |
| Struction | null [null, null]; 0/4 | null [null, null]; 0/4 | null [null, null]; 0/4 |
| WeightedBR | null [null, null]; 0/4 | null [null, null]; 0/4 | null [null, null]; 0/4 |
| Joint W / Degree | -100.0000 [-100.0000, -100.0000]; 4/4 | -46.9432 [-49.5330, -44.1759]; 4/4 | null [null, null]; 0/4 |
| Joint W / CHILS | -0.8190 [-2.4570, 0.0000]; 4/4 | null [null, null]; 0/4 | 0.0000 [0.0000, 0.0000]; 2/4 |
| EoH-DSL / CHILS | -0.8190 [-2.4570, 0.0000]; 4/4 | -1.2996 [-2.8814, 0.0000]; 4/4 | -0.3573 [-1.0718, 0.0000]; 4/4 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 1.4246; 4/4 | 2.3154; 4/4 | 6.3003; 4/4 |
| CHILS-ILS (3) | 1.4267; 4/4 | 2.3035; 4/4 | 6.3065; 4/4 |
| M2WIS (3 seeds) | 0.0042; 4/4 | 0.0042; 4/4 | 0.0154; 4/4 |
| Struction | 0.0041; 4/4 | 0.0041; 4/4 | 0.0041; 4/4 |
| WeightedBR | 0.0041; 4/4 | 0.0042; 4/4 | 0.0369; 4/4 |
| Joint W / Degree | 0.1004; 4/4 | 1.0006; 4/4 | 4.5074; 4/4 |
| Joint W / CHILS | 1.4224; 4/4 | 2.2447; 4/4 | 5.3209; 4/4 |
| EoH-DSL / CHILS | 1.4224; 4/4 | 2.3105; 4/4 | 5.1590; 4/4 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 12/12 | 12/12 | 12/12 |
| CHILS-ILS (3) | 12/12 | 12/12 | 12/12 |
| M2WIS (3 seeds) | 0/12 | 0/12 | 0/12 |
| Struction | 0/4 | 0/4 | 0/4 |
| WeightedBR | 0/4 | 0/4 | 0/4 |
| Joint W / Degree | 16/16 | 16/16 | 12/16 |
| Joint W / CHILS | 16/16 | 12/16 | 14/16 |
| EoH-DSL / CHILS | 16/16 | 16/16 | 16/16 |

### WDP / WDP_6xx

Assigned contexts: 4; assigned source/pair clusters: 4. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | -0.1336 [-1.3939, 1.0714]; 4/4 | -1.2714 [-1.6929, -0.8500]; 4/4 | 0.5245 [-0.1371, 1.2721]; 4/4 |
| CHILS-ILS (3) | -0.1336 [-1.3939, 1.0714]; 4/4 | -1.1903 [-2.2718, -0.4867]; 4/4 | 0.3749 [-1.5137, 2.5326]; 4/4 |
| M2WIS (3 seeds) | null [null, null]; 0/4 | null [null, null]; 0/4 | null [null, null]; 0/4 |
| Struction | null [null, null]; 0/4 | null [null, null]; 0/4 | null [null, null]; 0/4 |
| WeightedBR | null [null, null]; 0/4 | null [null, null]; 0/4 | null [null, null]; 0/4 |
| Joint W / Degree | -100.0000 [-100.0000, -100.0000]; 4/4 | -57.4080 [-58.9366, -56.3211]; 4/4 | null [null, null]; 0/4 |
| Joint W / CHILS | -0.8996 [-2.6988, 0.0000]; 4/4 | -2.7626 [-5.5251, 0.0000]; 2/4 | 0.0000 [0.0000, 0.0000]; 3/4 |
| EoH-DSL / CHILS | -0.8996 [-2.6988, 0.0000]; 4/4 | -2.8605 [-5.7210, 0.0000]; 4/4 | 0.0000 [0.0000, 0.0000]; 4/4 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 1.4025; 4/4 | 2.3009; 4/4 | 6.2948; 4/4 |
| CHILS-ILS (3) | 1.4035; 4/4 | 2.2938; 4/4 | 6.2981; 4/4 |
| M2WIS (3 seeds) | 0.0046; 4/4 | 0.0042; 4/4 | 0.0043; 4/4 |
| Struction | 0.0045; 4/4 | 0.0041; 4/4 | 0.0041; 4/4 |
| WeightedBR | 0.0045; 4/4 | 0.0041; 4/4 | 0.0041; 4/4 |
| Joint W / Degree | 0.1004; 4/4 | 1.0006; 4/4 | 4.5489; 4/4 |
| Joint W / CHILS | 1.4064; 4/4 | 2.2519; 4/4 | 5.0534; 4/4 |
| EoH-DSL / CHILS | 1.4064; 4/4 | 2.2857; 4/4 | 4.9073; 4/4 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 12/12 | 12/12 | 12/12 |
| CHILS-ILS (3) | 12/12 | 12/12 | 12/12 |
| M2WIS (3 seeds) | 0/12 | 0/12 | 0/12 |
| Struction | 0/4 | 0/4 | 0/4 |
| WeightedBR | 0/4 | 0/4 | 0/4 |
| Joint W / Degree | 16/16 | 16/16 | 12/16 |
| Joint W / CHILS | 16/16 | 14/16 | 15/16 |
| EoH-DSL / CHILS | 16/16 | 16/16 | 16/16 |

### UAI_Segmentation / Segmentation

Assigned contexts: 3; assigned source/pair clusters: 3. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |
| CHILS-ILS (3) | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |
| M2WIS (3 seeds) | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |
| Struction | -0.1795 [-0.5386, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |
| WeightedBR | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |
| Joint W / Degree | -6.2322 [-9.7358, -1.1594]; 3/3 | -6.2322 [-9.7358, -1.1594]; 3/3 | -6.2322 [-9.7358, -1.1594]; 3/3 |
| Joint W / CHILS | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |
| EoH-DSL / CHILS | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 | 0.0000 [0.0000, 0.0000]; 3/3 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1105; 3/3 | 1.0117; 3/3 | 5.0112; 3/3 |
| CHILS-ILS (3) | 0.1139; 3/3 | 1.0170; 3/3 | 5.0193; 3/3 |
| M2WIS (3 seeds) | 0.0958; 3/3 | 0.1000; 3/3 | 0.1005; 3/3 |
| Struction | 0.0896; 3/3 | 0.4810; 3/3 | 1.8170; 3/3 |
| WeightedBR | 0.0218; 3/3 | 0.0237; 3/3 | 0.0236; 3/3 |
| Joint W / Degree | 0.1009; 3/3 | 0.4078; 3/3 | 0.4073; 3/3 |
| Joint W / CHILS | 0.1166; 3/3 | 0.9979; 3/3 | 3.2593; 3/3 |
| EoH-DSL / CHILS | 0.1165; 3/3 | 0.9440; 3/3 | 3.0480; 3/3 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 9/9 | 9/9 | 9/9 |
| CHILS-ILS (3) | 9/9 | 9/9 | 9/9 |
| M2WIS (3 seeds) | 9/9 | 9/9 | 9/9 |
| Struction | 3/3 | 3/3 | 3/3 |
| WeightedBR | 3/3 | 3/3 | 3/3 |
| Joint W / Degree | 12/12 | 12/12 | 12/12 |
| Joint W / CHILS | 12/12 | 12/12 | 12/12 |
| EoH-DSL / CHILS | 12/12 | 12/12 | 12/12 |

### UAI_Grids_CHILS64 / Grids

Assigned contexts: 10; assigned source/pair clusters: 10. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0124 [-0.0198, 0.0431]; 10/10 | 0.0123 [-0.0080, 0.0312]; 10/10 | -0.0003 [-0.0180, 0.0166]; 10/10 |
| CHILS-ILS (3) | 0.0206 [-0.0170, 0.0589]; 10/10 | -0.0082 [-0.0534, 0.0281]; 10/10 | -0.0878 [-0.1143, -0.0621]; 10/10 |
| M2WIS (3 seeds) | null [null, null]; 0/10 | null [null, null]; 0/10 | null [null, null]; 0/10 |
| Struction | null [null, null]; 0/10 | null [null, null]; 0/10 | null [null, null]; 0/10 |
| WeightedBR | null [null, null]; 0/10 | null [null, null]; 0/10 | null [null, null]; 0/10 |
| Joint W / Degree | -75.6106 [-82.9858, -71.6430]; 8/10 | -10.7631 [-10.7631, -10.7631]; 1/10 | null [null, null]; 0/10 |
| Joint W / CHILS | -0.1537 [-0.3155, -0.0591]; 8/10 | -0.2186 [-0.2186, -0.2186]; 1/10 | null [null, null]; 0/10 |
| EoH-DSL / CHILS | -0.1274 [-0.2539, -0.0473]; 10/10 | -0.0711 [-0.1125, -0.0399]; 10/10 | -0.0171 [-0.0371, 0.0001]; 10/10 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1534; 10/10 | 1.0534; 10/10 | 5.0533; 10/10 |
| CHILS-ILS (3) | 0.1537; 10/10 | 1.0537; 10/10 | 5.0554; 10/10 |
| M2WIS (3 seeds) | 0.0219; 10/10 | 0.0223; 10/10 | 0.0227; 10/10 |
| Struction | 0.0213; 10/10 | 0.0225; 10/10 | 0.0210; 10/10 |
| WeightedBR | 0.0206; 10/10 | 0.0221; 10/10 | 0.0219; 10/10 |
| Joint W / Degree | 0.1037; 10/10 | 0.8603; 10/10 | 3.5228; 10/10 |
| Joint W / CHILS | 0.1647; 10/10 | 0.9741; 10/10 | 4.4484; 10/10 |
| EoH-DSL / CHILS | 0.1657; 10/10 | 1.0646; 10/10 | 4.9553; 10/10 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 30/30 | 30/30 | 30/30 |
| CHILS-ILS (3) | 30/30 | 30/30 | 30/30 |
| M2WIS (3 seeds) | 0/30 | 0/30 | 0/30 |
| Struction | 0/10 | 0/10 | 0/10 |
| WeightedBR | 0/10 | 0/10 | 0/10 |
| Joint W / Degree | 38/40 | 31/40 | 30/40 |
| Joint W / CHILS | 38/40 | 31/40 | 30/40 |
| EoH-DSL / CHILS | 40/40 | 40/40 | 40/40 |

### C3_interval_exploratory / all

Assigned contexts: 24; assigned source/pair clusters: 12. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0002 [0.0000, 0.0006]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| CHILS-ILS (3) | 0.0002 [0.0000, 0.0006]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| M2WIS (3 seeds) | 0.0003 [0.0000, 0.0010]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| Struction | -0.8379 [-1.8590, -0.1268]; 24/24 | -0.7739 [-1.7747, -0.0992]; 24/24 | -0.6264 [-1.5286, -0.0014]; 24/24 |
| WeightedBR | -0.4395 [-0.8503, -0.0965]; 24/24 | -0.0550 [-0.1385, -0.0005]; 24/24 | -0.0011 [-0.0029, 0.0000]; 24/24 |
| Joint W / Degree | -0.4957 [-0.8194, -0.2142]; 24/24 | -0.1234 [-0.3136, 0.0000]; 24/24 | -0.0159 [-0.0392, 0.0000]; 24/24 |
| Joint W / CHILS | 0.0000 [0.0000, 0.0000]; 24/24 | -0.0003 [-0.0010, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| EoH-DSL / CHILS | 0.0000 [0.0000, 0.0000]; 24/24 | -0.0003 [-0.0010, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1689; 24/24 | 1.0408; 24/24 | 5.0373; 24/24 |
| CHILS-ILS (3) | 0.1641; 24/24 | 1.0442; 24/24 | 5.0546; 24/24 |
| M2WIS (3 seeds) | 0.2839; 24/24 | 0.6600; 24/24 | 2.2153; 24/24 |
| Struction | 0.0652; 24/24 | 0.4402; 24/24 | 1.9953; 24/24 |
| WeightedBR | 0.0679; 24/24 | 0.4508; 24/24 | 2.1280; 24/24 |
| Joint W / Degree | 0.0931; 24/24 | 0.5227; 24/24 | 1.2371; 24/24 |
| Joint W / CHILS | 0.1790; 24/24 | 0.8089; 24/24 | 3.2451; 24/24 |
| EoH-DSL / CHILS | 0.1771; 24/24 | 0.7828; 24/24 | 3.0649; 24/24 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 72/72 | 72/72 | 72/72 |
| CHILS-ILS (3) | 72/72 | 72/72 | 72/72 |
| M2WIS (3 seeds) | 72/72 | 72/72 | 72/72 |
| Struction | 24/24 | 24/24 | 24/24 |
| WeightedBR | 24/24 | 24/24 | 24/24 |
| Joint W / Degree | 96/96 | 96/96 | 96/96 |
| Joint W / CHILS | 96/96 | 96/96 | 96/96 |
| EoH-DSL / CHILS | 96/96 | 96/96 | 96/96 |

### C3_legacy_exploratory / all

Assigned contexts: 24; assigned source/pair clusters: 12. C3 tracks are exploratory and not pooled with the 13 non-C3 families.

| Fixed series | T=0.1 gain % [CI]; pairs | T=1 gain % [CI]; pairs | T=5 gain % [CI]; pairs |
|---|---|---|---|
| CHILS (3 seeds) | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| CHILS-ILS (3) | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| M2WIS (3 seeds) | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| Struction | -0.0221 [-0.0598, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| WeightedBR | -0.3408 [-0.7605, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| Joint W / Degree | -2.3017 [-3.6046, -1.1955]; 24/24 | -0.9373 [-1.7788, -0.2707]; 24/24 | -0.5243 [-1.0825, -0.0394]; 24/24 |
| Joint W / CHILS | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |
| EoH-DSL / CHILS | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 | 0.0000 [0.0000, 0.0000]; 24/24 |

| Fixed series | CPU at 0.1; measured contexts | CPU at 1; measured contexts | CPU at 5; measured contexts |
|---|---|---|---|
| CHILS (3 seeds) | 0.1059; 24/24 | 1.0063; 24/24 | 5.0064; 24/24 |
| CHILS-ILS (3) | 0.1090; 24/24 | 1.0094; 24/24 | 5.0096; 24/24 |
| M2WIS (3 seeds) | 0.1292; 24/24 | 0.1827; 24/24 | 0.1820; 24/24 |
| Struction | 0.0371; 24/24 | 0.0888; 24/24 | 0.0887; 24/24 |
| WeightedBR | 0.0641; 24/24 | 0.4170; 24/24 | 1.9200; 24/24 |
| Joint W / Degree | 0.1027; 24/24 | 0.7240; 24/24 | 2.1238; 24/24 |
| Joint W / CHILS | 0.1098; 24/24 | 0.8596; 24/24 | 3.4936; 24/24 |
| EoH-DSL / CHILS | 0.1092; 24/24 | 0.8209; 24/24 | 3.1858; 24/24 |

| Fixed series | Member success at 0.1 | Member success at 1 | Member success at 5 |
|---|---|---|---|
| CHILS (3 seeds) | 72/72 | 72/72 | 72/72 |
| CHILS-ILS (3) | 72/72 | 72/72 | 72/72 |
| M2WIS (3 seeds) | 72/72 | 72/72 | 72/72 |
| Struction | 24/24 | 24/24 | 24/24 |
| WeightedBR | 24/24 | 24/24 | 24/24 |
| Joint W / Degree | 96/96 | 96/96 | 96/96 |
| Joint W / CHILS | 96/96 | 96/96 | 96/96 |
| EoH-DSL / CHILS | 96/96 | 96/96 | 96/96 |

