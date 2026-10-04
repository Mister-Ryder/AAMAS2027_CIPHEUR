# V06 R2: independently verified TRAIN outcomes and their limits

The R2 source/result/selector audit passes **2,184,019 checks with zero errors**, covering all 120 original candidates, **14,400 actual TRAIN assignments** and **163,187 saved patch traces**. Four genuine witness-arm joint winners satisfy the separately registered R2 deployment barrier. This readiness result does not establish held-out effectiveness or model superiority. R1's original nine-of-twelve failed barrier remains unchanged.

Audit: `experiments/analysis/v06/refinement_train_audit_v06_002.json`, SHA-256 `a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34`.

Original R2 archive SHA-256: `9ad65026b830a44365fab90655ae3620fcddb6c263e063bde334ae6301c5a185`; source capsule SHA-256: `67239f759c17cf347e663b6495e6dc47a550ffd56fcd86d7e069c20afe3140fc`. All 11 archived members and all 152 capsule members are byte-bound. The independently reconstructed selection SHA-256 is `bce7361133bc2ae2fc0eba0d22206c64a78d5e5ad22c7f163bc8a3c8de14ce73`.

Descriptive review: `experiments/analysis/v06/refinement_train_scientific_review_v06_002.json`, SHA-256 `83425e3c940fad37e46403c76f77f08826d3941162bdb14a2b8b6d25a310dc60`, produced by `scripts/summarize_refinement_audit_v06.py` from the zero-error audit and previously verified saved metadata. No program, oracle or graph evaluator was executed to create this review.

## Raw-slot coverage and information gate

All candidates are static-valid, have finite audited interfaces and complete feasible execution on all 120 TRAIN states. There are no kernel programme errors or global budget stops. The full demanded quotient uses all base features plus syntactically demanded additions; the independently audited declared quotient has the same failure counts here. Passing this gate does not mean that the current formula fits all ranking requirements.

| Population | Arm | Static / finite / complete feasible | Joint eligible | Yield | Contradictory quotient | Self-loop present | Cycle without self-loop |
|---|---|---:|---:|---:|---:|---:|---:|
| All five fixed blocks | W | 40 / 40 / 40 | 28 | 70.0% | 12 | 11 | 1 |
| All five fixed blocks | R | 40 / 40 / 40 | 24 | 60.0% | 16 | 10 | 6 |
| All five fixed blocks | O | 40 / 40 / 40 | 0 | 0.0% | 40 | 28 | 12 |
| Preregistered matched blocks 0–3 | W | 32 / 32 / 32 | 26 | 81.25% | 6 | 5 | 1 |
| Preregistered matched blocks 0–3 | R | 32 / 32 / 32 | 19 | 59.375% | 13 | 10 | 3 |
| Preregistered matched blocks 0–3 | O | 32 / 32 / 32 | 0 | 0.0% | 32 | 22 | 10 |

“Self-loop present” counts candidates with at least one directly aliased strict requirement; it does not exclude additional longer cycles. “Cycle without self-loop” counts contradictory interfaces that have no directly aliased strict requirement. It is not a count of every cycle in the graph.

The matched W−R eligibility difference is **+21.875 percentage points**. Across the four matched authoring blocks the eligible counts W/R are **7/4, 8/4, 3/3, 8/8**, out of eight original positions per cell. Two blocks favor W and two tie. The retained fifth block reverses this contrast (**2/5**), reducing the all-five-block difference to **+10 points**. The matched cohort was chosen by the first-four whole transport-complete rule before outcome inspection; the fifth block must remain visible rather than being hidden.

This supports a narrow descriptive result: explicit witness feedback increases observed information-gate yield in this conditional warm-repair study. It does not establish broad causal efficacy across models, tasks or arbitrary seeds. Four authoring blocks, an adaptively chosen R1 seed/frontier, and unmatched actual authoring compute limit that interpretation.

## Rule fit is a distinct outcome and does not uniformly improve

No R2 candidate attains all 594 strict requirements; **full actual scalar consistency is zero in every arm**. All candidate schedules have the same exact TRAIN macro quality **2693/4480**, approximately **60.1116% of total input graph weight**. This denominator is neither optimum nor a best-feasible reference. There is no TRAIN scheduling-quality advantage for W, R, O or the joint selector.

| Population | Mean strict labels fitted W | R | O | W−R |
|---|---:|---:|---:|---:|
| All five fixed blocks, 40 positions per arm | 553.550 / 594 | 575.750 / 594 | 548.950 / 594 | −22.200 labels |
| Matched four blocks, 32 positions per arm | 547.90625 / 594 | 574.81250 / 594 | 552.93750 / 594 | −26.90625 labels |

The valid witness-arm slot with only 312 fitted labels remains in these raw-slot means. Removing it after observing its result would bias the comparison. An information-rich representation can still have a poorly fitted numeric rule; information compatibility and actual scalar accuracy must not be conflated.

## Uniform joint winners and nonguarded quality winners

Uniform joint selection yields a W and R winner in every fixed block, but **all five O joint cells are empty**. The declared deployment takes only four genuine W joint winners from matched blocks 0–3. R joint winners remain available for diagnostics; the separate quality-comparison roles do not inherit their selection semantics.

| Matched block | W joint strict fit | W alias fit | R joint strict fit | R alias fit |
|---|---:|---:|---:|---:|
| 0 | 548 / 594 | 81 / 90 | 582 / 594 | 86 / 90 |
| 1 | 585 / 594 | 86 / 90 | 584 / 594 | 86 / 90 |
| 2 | 584 / 594 | 86 / 90 | 576 / 594 | 82 / 90 |
| 3 | 579 / 594 | 85 / 90 | 577 / 594 | 81 / 90 |
| Four-block mean | 574.00 / 594 | 84.50 / 90 | 579.75 / 594 | 83.75 / 90 |

Selected W−R strict-fit block contrasts are **−34, +1, +8, +2 labels**, averaging **−5.75**. Selected actual base-alias fit averages **+0.75 labels** for W. The best W scalar reaches 585/594, one more than the shared seed's 584/594, but this is not a general advantage in scalar fit or complete certification consistency.

The quality-only selector has a nonnull winner in all fifteen fixed cells, and all twelve matched W/R/O comparator identities are retained. It orders only exact schedule quality, work and original slot. Their joint eligibility happens to be **3/4 W, 2/4 R and 0/4 O**. These are nonguarded quality comparators even when a particular program also passes the joint gate; their role must not be relabeled after observing that outcome.

| Matched selector role / arm | Actual joint eligibility | Mean strict fit | Mean alias fit | Mean exact macro work |
|---|---:|---:|---:|---|
| Uniform joint / W | 4/4 | 574.00 / 594 | 84.50 / 90 | 21609669/2560 |
| Uniform joint / R | 4/4 | 579.75 / 594 | 83.75 / 90 | 4019069/512 |
| Uniform joint / O | 0/4, absent | absent | absent | absent |
| Quality-only / W | 3/4 | 555.25 / 594 | 81.00 / 90 | 448711/64 |
| Quality-only / R | 2/4 | 577.25 / 594 | 83.00 / 90 | 31639547/4608 |
| Quality-only / O | 0/4 | 526.50 / 594 | 45.25 / 90 | 17573449/3840 |

All present programs have the same TRAIN macro quality. Work values are charged feature-plus-repair operation proxies; the mean work of the selected W joint programs is higher than R's. Actual authoring token/elapsed costs are separately reported in `docs/V06_R2_AUTHORING_PROVENANCE_REVIEW.md` and are not matched. Shared Degree initialization, two local greedy lower bounds, clique bounds and capped BnB remain common classical components, not LLM-specific gains.

## Claims permitted before held-out results

The current evidence supports the sound diagnosis of input-information conflicts, a genuine public TRAIN cycle beyond direct pair aliasing, targeted warm-start feature/rule synthesis under an unchanged library, and improved matched information-gate yield for explicit witnesses. It also exposes negative/null outcomes: imperfect scalar fit, worse mean W strict fit, equal TRAIN scheduling quality, a fifth-block gate-yield reversal, and additional feature/search cost.

Do not write that witness guidance improves every ranking metric, produces fully specification-consistent programs, dominates R in quality/cost, proves held-out adaptation, beats advanced solvers, or guarantees acceptance. The four-W readiness condition permits a separately frozen held-out evaluation; it does not establish its result. The quality-only W/R/O contrast uses a common selector, whereas W-joint versus R/O-quality measures the full framework including selection. Neither comparison can turn common mature solver components into an original LLM contribution.
