# Independent v03 evidence audit

Auditor: [verify_v03_evidence.py](../scripts/verify_v03_evidence.py). Structured output: [evidence_audit.json](../experiments/analysis/v03/evidence_audit.json). The auditor reads only saved v03 results, v03 source snapshots, and declared v03 freeze inputs. It never extracts archives, executes archived source, reruns scheduling studies, or reads a fresh v04 test.

Run python scripts/verify_v03_evidence.py. The final audit includes both completed cooperative003 archives: 4,682,362 invariant checks and 347 distinct small conditional brute-force problems, with no errors. Independent population summaries and seed-block intervals are reproduced by [summarize_v03_audit.py](../scripts/summarize_v03_audit.py) and saved in [final_population_audit.json](../experiments/analysis/v03/final_population_audit.json).

## Verified populations and harness status

Count actual JSONL rows, not the last periodically written progress checkpoint.

| Archive | Actual unique context rows / assigned contexts | Completion interpretation |
| --- | ---: | --- |
| development_scale_001 | 380/380 | Complete train/validation screen; seven methods, 2,660 schedules; no held-out performance claim |
| scalability_001 | 56/56 | Complete baseline stress; 48 temporal and 8 C3 contexts; proposed frozen programs absent |
| holdout_unbounded_partial_001 | 182/840 | Partial harness diagnostic; balanced temporal contexts only; last checkpoint 180 |
| holdout_bounded_partial_002 | 207/840 | Failed partial harness; balanced temporal contexts only; last checkpoint 200 |
| transfer_001 | 216/216 | Complete supplementary unbounded dense/long-contact transfer |
| transfer_bounded_002 | 216/216 | Complete signal-guard transfer; 11 no-cost-program timeouts retained |
| holdout_cooperative_003 | 840/840 | Final primary population; all regimes, C3 source blocks, and probes present |
| transfer_cooperative_003 | 216/216 | Final dense/long-contact transfer under cooperative execution limits |

The incomplete primary archives do not represent all resource regimes, source blocks, or probes. Their missing contexts are unexecuted harness coverage, not successful schedules or measured per-program timeouts. The structured audit leaves the all-prespecified-context mean undefined for partial archives, while retaining completed-only and recorded-context descriptive means. The completed cooperative archives now provide the final v03 primary populations.

Mechanisms contain 186 acquisition tasks: three conditions on 62 training pairs. Independent counts reproduce all 51 saved anchored/clique specifications, 150 runtime contexts, and 900 backend/repetition records (two backends × three repeats × 150 contexts). All backend traces agree. Trace order is compared across backends, while saved schedules are compared as sets because they are serialized in sorted-ID order.

The proposal archive contains 24 candidates in each of four banks plus one cost-reference assessment. All candidate schedule rows point to validation data. The archived guided winner uses the old minimum-interface gate; primary frozen_joint_001 selects whole feature–rule pairs. These are different declared procedures, not interchangeable results.

## Independent checks

The auditor recomputes graph hashes from canonical edges, contacts, and constraints; verifies unique pair and id-side keys; checks aligned contacts, C3 identity separation, and disjoint split seeds; and verifies every returned schedule against conflict edges, fixed/excluded commitments, and its exact rational reward sum. Floating saved rewards agree with those sums to numerical tolerance. MILP records retain exact=false and floating_milp_reference scope. Their incumbent feasibility and numerical endpoint ordering are checked without treating upper values as formal optimum certificates.

For every saved decision certificate, both actions must be available and adjacent in both configurations, exactly one constraint must change, the preferred forced-action lower endpoint must strictly exceed the competing upper endpoint plus epsilon, and the relation label must agree with preferred IDs. Lower witnesses must be feasible, contain the forced action/commitments, exclude prohibited contacts, and equal the rational lower endpoint exactly. Endpoint ordering, outward floating rounding, exact flags, clique membership/edges/disjointness, and raw local-cover outside coverage are checked. Unresolved acquired attempts receive the same saved-bound checks.

For graphs with at most 12 contacts, exhaustive enumeration independently obtains conditional MWIS optima, checking interval containment, exact-value claims, and next-action regret. The completed audit checks 347 distinct small conditional problems. Large upper bounds are not replayed through every branch-and-bound frontier; their witnesses, partitions, rational ordering, and archived implementation provenance are checked. Do not describe this as an independent proof of every large optimum.

All complete results-file digests match receipts. Every held-out execution references joint freeze SHA-256 4928a392d6068d5767c96bb4e27f2e5db4028c349b112105812e963415b965ea. Saved generated programs equal the freeze, and candidate/evidence/data/assessment input hashes match preserved bytes. Prefix winners are independently recomputed using the frozen gate, shared cost-reference normalization, and lambda=.002. Repeated budget variants retain identical data bytes. Execution/amendment/freeze declarations forbid test-driven selection; these declarations and hashes support provenance but cannot prove all human information access.

## Mechanism claims and negative evidence

| Condition | Attempts | Reversal / preservation | Non-probe specifications | Expanded nodes |
| --- | ---: | ---: | ---: | ---: |
| Ranked / clique | 172 | 26/25 | 19 | 52,355 |
| Uniform / clique | 170 | 14/44 | 20 | 52,377 |
| Ranked / weight sum | 176 | 24/12 | 4 | 84,138 |

Clique improves yield versus weight sums with fewer nodes. Ranked acquisition does **not** dominate uniform: uniform saves more total and non-probe specifications. Extra ranked reversals are probe effects. Uniform also remains rollout anchored and changes query ordering; it is not an unanchored-query control.

Independent reconstruction gives 80 original classes, 50 arcs, and 64 strict self-loop requirements. The 19 temporal/C3 specifications give 60 classes, 30 arcs, no self-loop, and an acyclic quotient. All original-bank self-loops come from probes. With neighborhood-edge count, the rebuilt quotient has 100 classes, 50 arcs, and no cycle. All 16 catalogue subsets independently reproduce the unique minimum {neigh_edges}, cost 6,181 under **saved additive standalone-work weights**. This does not remeasure operation costs, optimize shared compiled cost, establish bounded-DSL realizability, or establish natural-workload necessity.

The expanded census enumerates 120,369 candidates and follows a frozen 200-query plan. All queries are unknown; no natural alias or strict requirement is certified. Query count, plan membership, unique IDs, no-test/no-program-change declarations, and bound witnesses are checked. Unknown is never recoded as preservation or absence; the census does not prove no natural obstruction.

## Reached-state relevance

The original relevance bank has 51 specifications / 102 side requirements per program. Guided g05 reaches 88 and escapes the designated pair at all 88. Its four pair-member choices in the saved raw aggregate occur at unreached counterfactual boundaries; actual pair-member choices are zero. Free reaches 88, escapes 64, and makes 24 consistent actual pair-member choices. Escape alone is not failure: all 64 reached guided probe escapes have exact zero regret.

On 24 reached non-probe requirements, guided mean conditional regret is formally bounded by [16.166667,18.927083] reward units; free/rule/enumeration each have [0.166667,2.927083]. These mean endpoint bounds are **not confidence intervals**. Unreached states are not zero regret. The archive omits individual reference and forced-completion witnesses; small probe regrets are exhaustively verified, while larger components cannot be independently reconstructed without rerunning an oracle. This is a recorded reproducibility warning.

## Transfer quality and timeout interpretation

Both transfer001 and transfer002 contain all 216 contexts. Guided/free/rule/enumeration complete in both, retaining identical reward/reference means: 89.897420%, 79.375116%, 93.947120%, and 89.733129%. Local search attains 98.942518%. Guided beats free here but loses to rule-only, minimum-interface (93.834989%), and local search; guided versus enumeration is small. A general guided advantage is unsupported.

No-cost g18 completes all 216 unbounded transfer contexts at 98.237059%. In bounded002 it completes 205/216; eleven timeout rows have null value, selected, and feasible, with completed=false. Completed-only quality is 98.299584%; explicitly zero-normalized over all 216 assignments it is 93.293587%. Null failures are excluded from completed-only means and retained in the all-context denominator. No partial schedule or fallback reward is substituted.

## Discrepancies and provenance limits

1. **Checkpoint lag:** Exact primary counts are 182 and 207, versus checkpoints 180 and 200. Progress is written every ten rows; these are valid lags, not duplication. Final reporting must use actual rows.
2. **Superseded failure explanation:** Bounded002's archived amendment attributes a signal-guard stall. The recovered cause is a TypeError when baseline initialization compares floats with timeout nulls. The archive is preserved; EXECUTION_BUDGET_AMENDMENT_V03.md records the correction and cooperative003 behavior.
3. **Development source gap recovered exactly:** The initially closest zip matched 17/19 files. Git commit 7df976f9a134f871d25efc8ce4f24845c3b1a93a contains exact manifest-matching graph_features.py (SHA-256 8f322a82fab72457a7dfe064f1da394164f40bd8daec517b90181a96de755296) and oracle.py (f8d93dbcc6c19a473c18c00bc90d20cf5ad3e91b863b0ccbbf06aebc4d091cce). All 19 development source files are now preserved in experiments/source_snapshots/v03/development_001_source.zip, SHA-256 972ed5d198e60474836849f0e80d11e8f2eaa4375a8e8cac6d89b0f7c511dc63. Its recovery_receipt.json records the Git origins of those two files and preserved-zip origins of the other seventeen. This is a reconstructed execution-manifest snapshot, not the original zip packaging; no current-tree source or nonmatching file was substituted.
4. **Older C3 physical receipts absent:** Development/stress have 60+8 C3 rows without source receipts; old runtime has 30 C3 contexts without them. Their schedules are independently graph-feasible, which is weaker than original physical verification. Available partial primary archives contain no C3. Final cooperative003 passes all80 graph/source-edge reconstruction receipts and all1,314 completed C3 selection receipts, with zero conflicts, duplicates, or invalid contacts; failures do not claim a source-verified selection.
5. **Large regret witness omission:** Offline relevance omits component completion witnesses, as above.

## Paper claim map reviewed

| Claim | Evidence/decision |
| --- | --- |
| Quotient obstruction requires representation repair | Supported on probes and finite original evidence; original temporal/C3 quotient is acyclic |
| Clique improves acquisition | Supported versus weight sum; ranked superiority versus uniform unsupported |
| Full separation and finite additive minimum | Independent 16-subset reconstruction supports the minimum; four-cycle fixture remains controlled |
| Guided generation yields consistency | Saved guided bank is highly consistent; enumeration has higher validation quality; no model-level guidance advantage |
| Consistency explains actual action quality | Rejected by reached-state regret/escape evidence |
| Frozen program improves quality across configurations | Final primary/transfer003 retain guided quality/coverage losses versus rule, minimum interface, and local search |
| Compiler lowers cost | All 900 fixed-rule traces/schedules agree; measured speedup is limited to that rule and validation contexts |
| Every returned final-primary C3 selection passed original verification | Supported by final003 receipts; unsupported for older archives without receipts |
| Finite guarantees imply greedy optimality or universal quality gains | Unsupported; current introduction/experiments/discussion/conclusion separate these claims |

## Final v03 quality and coverage

Both final populations keep null timeout rows. Reward/reference percentages below separate completed-only quality from the explicitly all-assigned mean that assigns zero to a failed construction. All-assigned quality is an operational outcome, not an imputed completed schedule.

| Method | Primary complete /840 | Primary completed quality | Primary all-assigned quality | Transfer complete /216 | Transfer completed quality | Transfer all-assigned quality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Guided | 704 | 98.996916% | 82.968844% | 203 | 90.396086% | 84.955581% |
| Free | 773 | 98.305393% | 90.464368% | 203 | 79.915765% | 75.106020% |
| Rule | 796 | 99.028584% | 93.841372% | 216 | 93.947120% | 93.947120% |
| Enumeration | 762 | 99.241607% | 90.026315% | 201 | 90.169285% | 83.907529% |
| Minimum interface | 813 | 98.746553% | 95.572557% | 216 | 93.834989% | 93.834989% |
| No-cost g18 | 344 | 99.875527% | 40.901406% | 165 | 98.534806% | 75.269643% |
| Local search | 840 | 99.832614% | 99.832614% | 216 | 98.942518% | 98.942518% |

Guided minus rule all-assigned quality is −10.872528 percentage points on primary (95% seed-block bootstrap interval [−14.518103,−7.509400]) and −8.991539 on transfer ([−12.034034,−6.143584]). Bootstrap uses2,000 replicates, seed20261003, preserves both configuration sides and shared temporal seeds across regimes, and samples temporal/C3/probe strata separately. Conditional quality intervals preserve each program's own completion coverage; they are not a fair substitute for reporting failures. Full family/regime and contact-size results, primal/best-observed descriptive ratios, coverage intervals, and all comparisons are in the structured population audit.

Primary guided completed quality is96.528% on C3,99.497% balanced,98.848% ground scarce,99.278% satellite scarce, with coverage64/80,192/240,216/240,192/240 respectively. All40 probes complete at100% for guided/free/rule/enumeration. C3 evidence therefore cannot be pooled into a claim of family-general quality advantage. Transfer guided fails13 ground-scarce contexts; rule and minimum-interface complete all216.

Primary floating MILP references are status0 on838 contexts and status1 on2; all840 incumbents are feasible. Its mean incumbent/upper reference is99.997790%, while all216 transfer references have status0 and equal saved numerical endpoints. These are numerical primal references, not formal optimum certificates.

The cooperative source is preserved byte-identically at experiments/source_snapshots/v03/cooperative_v03_source.zip, SHA-2564226587e346a244b5fcb52d0c5f86ffcd7036f6392e002cc5953bc5f5031959c. All29 executed Python source hashes match. The five-CPU-second target is cooperative, with primitive/checkpoint overshoot: maximum failed primary guided CPU is5.184206 seconds. No completed constructive primary row exceeds5 seconds. Report the target and measured completion jointly; do not call this a hard wall-clock cap or comparator-matched compute.

The experiment section was not changed during this audit. Original-bank null incidence and negative relevance remain justified; final v03 evidence further rejects universal guided superiority. The later v04 method is motivated by these failures and requires a fresh population after its TRAIN-only freeze.
