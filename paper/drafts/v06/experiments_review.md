# Independent V06 experiments fragment: numeric bindings and limits

Authored 2026-10-04. Only completed, previously verified TRAIN results are used. No scheduling policy, conditional oracle, author or selector was executed to produce this section. No evolving EoH response or TEST outcome was read. The manuscript fragment is not yet integrated or compiled; root owns main-paper integration.

## Manuscript scope and layout

The draft has three tables: information-gate yield/rule fit/selected work; all four catalogue outcomes; and every native baseline actually assessed, at the common one-second nominal target. The native table is a TRAIN calibration, not a proposed-program comparison. The three completed source plots retain native 3.35-inch, 9-point design: one yield panel in a column and cost/work panels paired across both columns. Root can relocate floats while retaining legibility. Draft-only input markers keep EoH, withheld mechanism, performance and patch-bridge results unfilled.

The prose is approximately 1,100 words excluding table bodies; the whole section remains below the requested 1,500-word narrative target. No audit counts, artifact hashes or host/file paths appear in the paper prose. The current V05 main source and original sections were not edited.

## Exact source bindings

| Verified source | Relative artifact | SHA-256 |
|---|---|---|
| R2 scientific summary | `experiments/analysis/v06/refinement_train_scientific_review_v06_002.json` | `83425e3c940fad37e46403c76f77f08826d3941162bdb14a2b8b6d25a310dc60` |
| R2 independent TRAIN audit | `experiments/analysis/v06/refinement_train_audit_v06_002.json` | `a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34` |
| TRAIN evidence audit | `experiments/analysis/v06/evidence_train_audit_v06_001.json` | `b3969c764a6f594ebdb8c656200519b09777270c2ba3833e56ee8d93286dc314` |
| Finite catalogue audit | `experiments/analysis/v06/catalogue_cost_audit_v06_001.json` | `b485a74414364e551abebc250dd6922498865a0a41ed93a8523ab4a559f5e0d2` |
| Native public TRAIN audit | `experiments/analysis/v06/classic_public_train_check_v06_001.json` | `4ba6b13b8c9e0646fc5338df5680112ee0cebb4cbf11d34aab0e781bf1fef748` |
| Common component TRAIN audit | `experiments/analysis/v06/classic_components_train_check_v06_001.json` | `587450abdb4c26376f998dbc9f75fff2c70258773d838863712f37746307e1cc` |
| R2 authoring provenance | `experiments/analysis/v06/refinement_authoring_audit_v06_002.json` | `2c3327ae92e0deccabb054636bcabfd9e31ed317679837fc26b31243128b7f7c` |
| R1 summary | `experiments/analysis/v06/synthesis_train_summary_v06_001.json` | `97087fff13b42fa8f19b7bd3e619d481898b6cb604d07823d0cb7fef13b95d88` |

R2 original archive: `9ad65026b830a44365fab90655ae3620fcddb6c263e063bde334ae6301c5a185`; source capsule: `67239f759c17cf347e663b6495e6dc47a550ffd56fcd86d7e069c20afe3140fc`; independently reconstructed selection: `bce7361133bc2ae2fc0eba0d22206c64a78d5e5ad22c7f163bc8a3c8de14ce73`. The completed assessment used eight workers and 55.99 seconds of recorded batch wall time, with 2,184,019 independent checks and zero errors; these operational details remain here rather than becoming performance claims in the manuscript.

## Table 1 exact inputs

| Arm | Eligible all five / matched four | Matched raw fitted-label mean | Selected fitted-label mean | Selected macro-work mean |
|---|---|---|---|---|
| witness | 28/40; 26/32 | 17533/32/594 | 574 | 21609669/2560 |
| relations | 24/40; 19/32 | 9197/16/594 | 2319/4 | 4019069/512 |
| objective | 0/40; 0/32 | 8847/16/594 | None | None |

Paper rounding: two decimals for fitted-label means and nearest integer for operation-work means. The zero-valued gate is real; an absent O joint scalar/cost remains a dash. W/R joint costs are 21609669/2560 and 4019069/512, i.e. 8441.276953125 and 7849.744140625. All candidate macro qualities equal 2693/4480, i.e. 0.6011160714285714 of total input reward; no optimum denominator is used.

All-five raw means W/R/O: 11071/20, 2303/4, 10979/20. Matched raw means: 17533/32, 9197/16, 8847/16.

The matched W/R yield block counts are 7/4, 8/4, 3/3, 8/8; the fifth is 2/5. All-five advantage is +10 percentage points; matched advantage is +21.875 points. Two blocks favor W and two tie. Selected W strict fit is lower overall, while selected alias fit is 169/2 versus 335/4 out of 90. No candidate attains all 594 strict labels. Four W joint policies are genuine guarded selections; quality-only comparators retain nonguarded roles even when their AST happens to pass the gate.

## Table 2 and catalogue figure inputs

| Catalogue | Original status | Final subset acyclic | Trials after base Q | Last-subset cost, not necessarily repair cost |
|---|---|---:|---|
| 4 | unresolved | False | 4 | 1379402 |
| 8 | unresolved | False | 7 | 1321237 |
| 16 | unresolved | False | 7 | 1274105 |
| 53 | resolved_additive_minimum | True | 9 | 1371468 |

Only the full-53 cost is printed as a minimum. The base quotient is separate from nine master rechecks (ten quotient evaluations including the base). Seven self-loop cuts then two genuine directed-cycle cuts lead to the final DAG; checking self-loops alone or stopping after the first directed obstruction is insufficient.

The certified optimum uses standalone costs 29964 + 147167 + 394682 + 799655 = 1371468. Their shares are 2.18%, 10.73%, 28.78%, 58.31%. The independent nonnegative cut-weight lower bound attains the same sum. This proves the fixed-catalogue additive optimum, not runtime optimality, minimum cardinality, unique features, bounded-scalar expressibility or unseen generalization. The adaptive R1 catalogue is not blind; this study stayed out of R2 authoring and selection.

## Native calibration: all budgets retained outside the compact table

| Family | Method | Nominal target | Feasible / assigned | Mean original objective (exact) | Median wrapper wall seconds |
|---|---|---:|---|---|---:|
| UAI | CHILS | 0.1 | 9/9 | 501134959/300000 | 0.115118980 |
| UAI | CHILS | 1 | 9/9 | 501134959/300000 | 1.014024109 |
| UAI | CHILS | 5 | 9/9 | 501134959/300000 | 5.011502296 |
| UAI | CHILS_ILS | 0.1 | 9/9 | 501134959/300000 | 0.120829929 |
| UAI | CHILS_ILS | 1 | 9/9 | 501134959/300000 | 1.019453555 |
| UAI | CHILS_ILS | 5 | 9/9 | 501134959/300000 | 5.016565025 |
| UAI | Degree | 0.1 | 3/3 | 498965107/300000 | 0.100942422 |
| UAI | Degree | 1 | 3/3 | 498965107/300000 | 0.346521351 |
| UAI | Degree | 5 | 3/3 | 498965107/300000 | 0.343758736 |
| UAI | M2WIS | 0.1 | 9/9 | 501134959/300000 | 0.077396780 |
| UAI | M2WIS | 1 | 9/9 | 501134959/300000 | 0.074949849 |
| UAI | M2WIS | 5 | 9/9 | 501134959/300000 | 0.074348111 |
| UAI | Struction | 0.1 | 3/3 | 501134959/300000 | 0.021094825 |
| UAI | Struction | 1 | 3/3 | 501134959/300000 | 0.024305128 |
| UAI | Struction | 5 | 3/3 | 501134959/300000 | 0.023983844 |
| UAI | WeightedBR | 0.1 | 3/3 | 501134959/300000 | 0.022149689 |
| UAI | WeightedBR | 1 | 3/3 | 501134959/300000 | 0.021079585 |
| UAI | WeightedBR | 5 | 3/3 | 501134959/300000 | 0.017626084 |
| WDP | CHILS | 0.1 | 75/75 | 6169704374/75 | 0.597978290 |
| WDP | CHILS | 1 | 75/75 | 6316859729/75 | 1.509491999 |
| WDP | CHILS | 5 | 75/75 | 6391142902/75 | 5.521360133 |
| WDP | CHILS_ILS | 0.1 | 75/75 | 6169704374/75 | 0.602619100 |
| WDP | CHILS_ILS | 1 | 75/75 | 2105541418/25 | 1.516011614 |
| WDP | CHILS_ILS | 5 | 75/75 | 6424217417/75 | 5.512965225 |
| WDP | Degree | 0.1 | 25/25 | 316916431/25 | 0.100344587 |
| WDP | Degree | 1 | 25/25 | 1206977456/25 | 1.000416040 |
| WDP | Degree | 5 | 25/25 | 1897643478/25 | 2.203702260 |
| WDP | M2WIS | 0.1 | 0/75 | None | 0.002865296 |
| WDP | M2WIS | 1 | 0/75 | None | 0.002837427 |
| WDP | M2WIS | 5 | 0/75 | None | 0.002853148 |
| WDP | Struction | 0.1 | 0/25 | None | 0.004070353 |
| WDP | Struction | 1 | 0/25 | None | 0.004050788 |
| WDP | Struction | 5 | 0/25 | None | 0.002722256 |
| WDP | WeightedBR | 0.1 | 0/25 | None | 0.002728395 |
| WDP | WeightedBR | 1 | 0/25 | None | 0.002705928 |
| WDP | WeightedBR | 5 | 0/25 | None | 0.002746947 |

The public calibration has 1008 original requests, 549 native plus 84 Degree feasible outputs, and 375 predetermined encoding nulls. No null quality becomes zero. The paper displays all six methods at one second; 0.1/5-second rows remain above. The UAI public subset is specifically three Segmentation graphs, not a pooled Grids/ProteinFolding result. Native stochastic methods have three fixed seeds; deterministic methods and Degree have one. Bold marks observed reward and valid-output wall bests, with all equal Segmentation native rewards bold; input-rejection latency is excluded from valid-output timing bests.

Original WDP rewards exceed signed-32 encoding for the incompatible methods, and unsupported requests remain visible. Wrappers preserve exact original-objective source mappings; numerical compatibility is not assumed to preserve a learned rule. Median observed timing is descriptive, not a hard deadline or an optimum guarantee. Same-source seeds/targets are nested repeated observations, not independent source draws.

The separate component study has 960 feasible assignments and 32 sources. Warm versus matched half CHILS is 4 better / 284 equal / 0 worse; versus full CHILS it is 2 better / 222 equal / 64 worse. The raw 288-pair contrasts and per-family original rewards remain in the source JSON. No LLM runs participate, and calibration is excluded from R2 packets/selection.

## Pending inputs and interpretation

The frozen evaluation protocol has 302 contexts, three targets and 58 requests/context/target = 52,548 assignments, with 23 policy identities. It includes 216 fresh weighted contact endpoints, 25 WDP, three Segmentation, ten Grids and two separate 24-context C3 exploratory model blocks. The original 72 withheld mechanism states and five ID bijections remain distinct from that performance inventory. EoH authoring/fitness is underway; no candidate/output or selection finding is inferred here.

Do not promote these current findings to held-out adaptation, scheduling-quality superiority, W fit/cost dominance, matched authoring compute, natural satellite incidence, pivot-efficiency certification or SOTA. R1 failed its original nine-of-twelve barrier; R2 is conditional warm repair and does not retroactively replace that outcome. The main contribution currently supported is observed information repair, combined with the complete-quotient cost demonstration and clearly separated negative/null scalar and quality results.

Numeric validation checked every displayed scalar mean against the verified summary, every displayed native reward against the zero-error native audit, all four catalogue trial counts and the resolved exact cost, without running any experiment. The section has three tables and two floats containing three plot panels; figure paths and problem label resolve in the workspace. No typeset page claim is made before root compiles the integrated manuscript.
