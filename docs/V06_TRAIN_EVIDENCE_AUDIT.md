# Independent V06 TRAIN evidence audit

Date: 2026-10-03. **28,087 checks, zero errors.** This verification independently reconstructs frozen inputs/queries and certifies saved TRAIN outcomes. It does not collect a new experimental query, author/evaluate a policy or solve any TEST conditional problem.

The frozen inventory contains 192 states: 120 TRAIN and 72 TEST. Public-source TRAIN/TEST clusters are disjoint within a previously exposed corpus: nine DIMACS plus 15 SATLIB per side. The controlled synthetic track has 48 TRAIN pairs and 24 TEST pairs, across three resource regimes and two horizons. TRAIN station gap changes zero→one; held-out input configuration is 0.25→two. Every source-induced subset, generated contact, original conflict edge, source split, salted query ordering, base-nine vector, per-side alias flag and unavailable quota count was independently reconstructed from raw source inputs. TEST reconstruction checks inputs only; **TEST conditional queries and program evaluations remain zero**.

Auditor: `scripts/verify_evidence_v06.py`, SHA256 `ae42647e665c1e09562f937a29bffc4489e0e3fa49aad62d7a31fe9c8d1f97b3`. It imports only older independent graph/exact-recurrence helpers. No original oracle, experiment runner or scheduling module is imported or called.

Receipt: `experiments/analysis/v06/evidence_train_audit_v06_001.json`, SHA256 `b3969c764a6f594ebdb8c656200519b09777270c2ba3833e56ee8d93286dc314`.

## Evidence coverage and alias semantics

| TRAIN measure | Count |
|---|---:|
| Scheduled queries | 1,503 |
| Certified strict conditional preferences | 594 |
| Exact conditional-value ties | 909 |
| Queried interval unknowns | 0 |
| Unavailable quota slots | 417 |
| Queries drawn from the alias pool | 847 |
| Queries drawn from the nonalias-control pool | 656 |
| Queries actually aliased on the evaluated side | 660 |
| Strict preferences with an actual equal-base-vector conflict | 90 |

A paired query belongs to the alias pool when its two competing actions have equal base vectors on **either** intervention side. It need not be an alias on both sides. Therefore neither all 847 alias-pool slots nor all 594 strict labels are information conflicts. The 90 genuine strict equal-vector cases are **29 DIMACS, seven SATLIB and 54 controlled synthetic endpoint cases**. They prove a pointwise rule using only those nine values cannot obey those particular inequalities. They do not establish a benefit from LLM authoring, removal of all full-quotient cycles, numerical fit of an expanded rule or improved complete schedules.

| Family | Strict | Exact ties | Strict actual-side aliases |
|---|---:|---:|---:|
| DIMACS | 68 | 53 | 29 |
| SATLIB | 55 | 67 | 7 |
| Balanced / long horizon | 55 | 87 | 8 |
| Balanced / short horizon | 91 | 139 | 9 |
| Ground-scarce / long horizon | 56 | 126 | 2 |
| Ground-scarce / short horizon | 103 | 151 | 12 |
| Satellite-scarce / long horizon | 80 | 116 | 7 |
| Satellite-scarce / short horizon | 86 | 170 | 16 |

These are query/endpoint counts, not independent-source counts. Public source-derived states reuse an exposed corpus; synthetic instances are deliberately controlled unit-reward/unit-duration contact realizations. They are not empirical natural C3 incidences. The old 200 physical unknowns remain unknown and are not replaced by these easier synthetic cases.

## Paired intervention outcomes

The synthetic track contributes 630 competing-action pairs, evaluated at both endpoints, yielding 1,260 endpoint rows. The public track contributes 243 rows, for a total of 1,503.

| Independent paired classification | Count |
|---|---:|
| Strict preference preserved | 123 |
| Strict preference reversed | 12 |
| Exact conditional tie on both sides | 294 |
| Strict→tie | 116 |
| Tie→strict | 85 |

Only the 135 strict-on-both-side cases instantiate strict preservation/reversal requirements without an indifferent endpoint. An exact conditional-value tie does not require equal heuristic scores. A frozen scorer's directional fit must later be assessed separately under the registered margin. No program fit or synthesis advantage was inferred during this audit.

## Independent conditional proof replay

Every TRAIN graph has at most 32 vertices, unit weights and empty F/X. The auditor independently solves **3,236 distinct conditioned connected components**, using **251,760 memoized include/exclude recurrence states** with a declared one-million-state ceiling per component. No component hit that ceiling, and no verification result remains unresolved. Common residual components are included in the independent full conditional values as well as checked for exact cancellation.

For each exported unmatched component, the selected lower witness is feasible and has the exact recorded reward; the independently computed optimum lies inside its saved LB/UB interval. The auditor reconstructs the complete conditioned component partition and all cancellation matches, verifies signed rational interval arithmetic and outward floating enclosures, checks the frozen default epsilon of 1e−8, and verifies strict/tie signs against independently computed full conditional values. It also reconstructs each state's unique component cache and exactly accounts for recorded call/expanded-node totals. The original oracle was never used as the checker.

Budgets reset per graph/state: at most 1,024 component solver calls and two-million expanded nodes across its scheduled queries, with 50,000 nodes per unmatched component and a 32-vertex search cutoff. Identical cancelled components consume no component solve. A state with zero component calls can legitimately have an exact tie proof by cancellation alone. The recorded approximately 0.416-second whole-run wall duration is an executed host receipt, not an independently remeasured cost or LLM efficiency claim.

## Byte bindings and held-out protection

| Artifact | SHA256 |
|---|---|
| TRAIN raw archive | `3f6986a6b803761c503876d4b3d1419c7f1fe3adab3acc5929dcb4c6db2c7a48` |
| Pre-query source capsule | `74c1854536206fe098cbad86cd3a5c400dda279ecbff49c76cf3d80b2e075380` |
| Frozen full input inventory | `968f96b7712ca3ecc8a7b43f567c6b6403742f26f0e76e9d5f2c680973827784` |
| Original evidence protocol | `32e008c2d348df53813696f8bfc413829704a9e76c07e4d03ac036387cb11854` |
| Original pre-query freeze | `00e67514c70d76547991fa3c9908b85c954d48e35a4dab605dcf0876234a87c5` |
| Append-only budget scope | `16834240d6136cf54cf208e3f03b24f7d0505f72b9cc898df8bf1ac31f4b19d2` |

The capsule inventory and every original semantic source are byte bound; append-only host/budget receipts bind original execution/completion bytes, state budgets and source hashes. Launch receipts precede TRAIN queries, execution has no program freeze, all 120 result IDs are TRAIN, and no retry or whole-run guard occurred. The original receipts and source were not modified by verification.

The evidence is now suitable for the registered TRAIN synthesis/selection study. It still needs frozen candidates, actual scalar-rule checks, held-out certificates after winner freeze, shared-kernel execution and non-LLM comparisons before any claimed framework or LLM advantage is supported.
