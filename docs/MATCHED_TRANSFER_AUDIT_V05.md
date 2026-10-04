# Independent audit of exploratory frozen-program transfer

The new transfer archive passes **141,652 independent checks with zero errors**. All **1,560 assigned runs** remain present: **1,007 complete**, **553 `_CPUCap` failures**, no worker exceptions and no no-progress hard-wall interruption. These are the twelve original TRAIN-selected V05 programs and one fixed Degree reference on 120 previously observed V04 contexts. This extension is exploratory transfer, not a new confirmatory held-out population.

This document is an audit report, not manuscript text. The independent outputs are `scripts/verify_matched_transfer_v05.py` and `experiments/analysis/v05/matched_transfer_audit_v05_001.json`. The experiment protocol, source capsule, data, programs, archive and publisher analysis were not modified by this auditor.

## Provenance and denominator checks

- The protocol and source capsule are byte-identical to the hashes communicated when the experiment launched. The freeze timestamp precedes execution. Every capsule member, registered source file and original matched semantic file matches its original receipt.
- The copied winner file matches the original TRAIN archive **byte for byte**. All four authoring blocks and all three arms are retained, including repeated deployment ASTs; no candidate is replaced, deduplicated or reselected.
- Every context matches its original V04 graph, source metadata, ID, explicit fixed/excluded boundary and reference witnesses. The 96 public contexts comprise 48 source graphs with two weight views; the 24 C3 contexts comprise 12 paired source subproblems. They do not constitute 120 independent new graph sources.
- The actual stable-source `C3.csv` SHA-256 agrees with all 24 C3 source/provenance records. Contact-origin IDs agree across those records. This auditor does not implement a new physical edge reconstruction; the exact prior input graphs are checked, and all saved complete schedules are checked for graph feasibility. The execution archive separately retains the original source reconstruction and scheduling-predicate checks.
- All **21,571 nonempty clique parts** and **56,878 clique-internal edges** are checked independently. Exact rational sums reproduce every original formal upper bound `U`; every saved lower witness is feasible under its boundary and reproduces the original `L`. Neither denominator is replaced using new results. `U` is a sound bound, not a proven optimum; `L` is a prior feasible schedule value and can be exceeded.

## Independent result reconstruction

Every completed schedule is checked for unique selected vertices, preserved fixed/excluded commitments, pairwise graph feasibility, complete deletion trace, remaining counts, finite saved scores and exact rational reward. Failed assignments retain null schedule/reward fields and receive zero in both quality aggregates. Completion counts, failure types, all per-context qualities, all four block means and equal-block arm means agree exactly with the separate publisher analysis. CPU/wall summaries include known failed-run timings rather than censoring those runs.

A bounded first-score check was fixed by input properties before reading result rows: at most two contexts per population, with at most 300 vertices and 15,000 edges, ordered by graph digest then ID. Independent demanded-feature interpretation verifies **130/130 first-action argmaxes**, with **zero skips** under a two-process-CPU-second verifier ceiling per assignment. Later-step scores are not reexecuted. These checks replay recorded evidence; they do not run a replacement scheduling program or change any outcome.

| Previously observed population | Contexts | Witness %U (complete/assigned) | Relations %U (complete/assigned) | Objective %U (complete/assigned) | Degree %U (complete/assigned) |
|---|---:|---:|---:|---:|---:|
| DIMACS unit | 18 | 40.154603 (63/72) | 40.106332 (64/72) | 39.845915 (63/72) | 43.939551 (17/18) |
| DIMACS hash-weighted | 18 | 41.279976 (65/72) | 40.820657 (64/72) | 42.230076 (67/72) | 41.719623 (17/18) |
| SATLIB unit | 30 | 24.645333 (40/120) | 24.645333 (40/120) | 24.645333 (40/120) | 49.493753 (20/30) |
| SATLIB hash-weighted | 30 | 22.595133 (40/120) | 22.609494 (40/120) | 23.415749 (40/120) | 44.439601 (20/30) |
| C3 paired subproblems | 24 | 65.598787 (91/96) | 68.626423 (96/96) | 68.990910 (96/96) | 68.232581 (24/24) |

All displayed quality means retain incomplete assignments as zero. Each LLM arm is an equal mean over its four frozen authoring blocks; Degree is one fixed reference, not four independent generation blocks. The two weight views and paired C3 sides must not be used to inflate source independence.

## Budget clarification

The original protocol sentence placed program parsing inside the cooperative deadline. The unchanged source actually evaluates `FeatureRuleProgram.from_dict` before constructing `_Meter(5)`. The append-only `budget_scope_clarification.json` corrects that description without changing code, assignments, parsing, budgets or selection. It was added during execution before analysis; it is not represented as part of the original pre-execution source capsule.

Independent source-AST inspection confirms the order: actual CPU/wall timers start before AST parsing, while the cooperative process-CPU deadline starts when `_Meter` is constructed and is checked every 128 meter writes. Recorded timings retain parsing, evaluator initialization, scheduling and returned validation work, including overshoot. A five-second cooperative target is therefore not a strict five-second upper bound on the returned assignment CPU time. Graph materialization and source checks are separate. No old-server native-baseline timing is pooled with the new same-host measurements.

## Scientific implications for the paper

The transfer results do **not** establish a general witness-guidance advantage. Degree wins the unit DIMACS and both SATLIB failure-zero populations. All three LLM arms complete only one third of SATLIB assignments under this target, whereas Degree completes two thirds; runtime portability materially affects the aggregate result. The weighted DIMACS witness result includes an extra completion of an unchanged deployment AST near the cooperative deadline, so that completion difference cannot itself establish a structural-authoring gain.

On C3, the Objective arm exceeds Degree by **0.758329758574 percentage points of U**, while averaging **98.121832% of the prior fixed L**. Relations completes all 96 C3 assignments; five failures from Witness block 1 reduce that arm's mean. Thus a small advantage over Degree on this restricted C3 transfer track is compatible with failing to improve the stronger prior feasible reference. Coverage and fixed-L comparisons should remain visible beside the U-normalized quality.

An appropriate concise paper statement is: “Exploratory transfer executes all twelve TRAIN-frozen programs on the previously observed public/C3 graphs without reselection. Completion is a limiting factor: each arm completes 40/120 assignments per SATLIB weight view versus Degree's 20/30. On C3 the Objective arm reaches 68.991% of the prior upper bound versus Degree's 68.233%, but 98.122% of the prior feasible reference. These results do not establish general witness superiority and expose computational portability beyond the TRAIN feature-work penalty.” Retain the fixed-denominator and repeated-data scope when integrating this draft sentence.

No significance or general model superiority is inferred from four authoring blocks. Slot/configuration matching does not establish token/latency matching. The new experiment concerns deployment of already-authored programs, not new LLM learning curves or a new native-solver comparison. Its timing results do not measure LLM authoring speed or pure model inference CPU.

## Frozen bindings

| Evidence | SHA-256 |
|---|---|
| Result archive | `4b4888820ac71797aa5f1e05980f0216fd94acac2f9e17f65340001fdc8536a2` |
| Protocol | `8f785558ace072936baf2e29b2c3585c1cf3fd8528036ad2398695f9cb061288` |
| Source capsule | `81cee9ea27374ba055cc15a6af11d810c7aad68982a1830fbae045d202031b62` |
| Input data | `7a572d043ff0d3a05a630b5b0ecf522c90a50cef74b8e7c66fdbc6e2784e6793` |
| Original TRAIN winners | `37757102547f7e8b774900ac78a5c714bccb795d5471afed546f393f915e0eaa` |
| Budget clarification | `678ad9d2d282298488c575cc5933247c6c8acad4227724079e0cbab07a9c8c2d` |
| Publisher analysis | `f2713f139f539ded9f1c3496f6cdeb2adc3ecbf59d99d30660c12fcc3abecd04` |
| Original C3 CSV | `ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e` |

The JSON additionally binds the independent audit script and both independent helper scripts. Zero-error status applies only to these bound artifacts and the stated verification scope.
