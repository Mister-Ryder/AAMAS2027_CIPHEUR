# Frozen-program transfer: exploratory analysis and limits

All twelve TRAIN-frozen winners and the fixed Degree program were executed on all 120 pre-existing contexts (96 public and 24 C3), giving 1,560 assignments. The original registered V05 TRAIN/TEST study and its results were not changed. The extension was fixed before new executions, but the input populations had already been observed in V04, so it is exploratory and is not independent confirmatory replication.

## Complete inventory and failure handling

1,007 assignments completed; 553 failed through the unchanged cooperative CPU cap. There were no worker exceptions, fallback methods, candidate replacements or hard-wall safety stops. Whole-inventory completion is Witness 299/480, Relations 304/480, Objective 306/480, and Degree 98/120. Of the 553 failures, 500 occur on SATLIB, 48 on DIMACS and five on C3. These are coverage totals, without pooling the five quality populations. Both successful and failed assignments contribute to the assigned denominators. A failed assignment contributes zero quality; it does not contribute a partial schedule. The publisher runner performed 105,253 exact reward/feasibility/deletion-trace checks with zero errors. All 24 C3 graphs were reconstructed from the original V51 source; all 307 completed C3 schedules passed its physical conflict verifier. A separate read-only audit (scripts/verify_matched_transfer_v05.py; docs/MATCHED_TRANSFER_AUDIT_V05.md; experiments/analysis/v05/matched_transfer_audit_v05_001.json) passed 141,652 checks with zero errors, including all assignment identities/coverage, exact per-context qualities and four-block arm means, and 130 initial first-argmax checks with zero skips. This first-argmax audit does not claim recomputation of every later residual score. The C3.csv SHA also matches all 24 source/provenance records.

## Quality and the four authoring blocks

Primary quality is 100 W/U, where U is the old, independently verified weighted clique-partition upper bound. Secondary quality is 100 W/L, where L is the old best verified feasible reward; this may exceed 100 and is not an optimum ratio. Both denominators and their witnesses were frozen before execution and never updated using these new outputs. Four block means receive equal weight within each arm. They are descriptive authoring repetitions, not four independent graph populations or a significance test.

| Population | Arm | Block 0 %U | Block 1 %U | Block 2 %U | Block 3 %U | Equal-block mean %U | Completed/assigned |
|---|---|---:|---:|---:|---:|---:|---:|
| DIMACS_hash_weighted | witness | 40.8271 | 40.8271 | 40.8271 | 42.6385 | 41.2800 | 65/72 |
| DIMACS_hash_weighted | relations | 40.8271 | 40.8271 | 40.8012 | 40.8271 | 40.8207 | 64/72 |
| DIMACS_hash_weighted | objective | 42.4381 | 42.4381 | 41.6060 | 42.4381 | 42.2301 | 67/72 |
| DIMACS_unit | witness | 40.1063 | 40.2994 | 40.1063 | 40.1063 | 40.1546 | 63/72 |
| DIMACS_unit | relations | 40.1063 | 40.1063 | 40.1063 | 40.1063 | 40.1063 | 64/72 |
| DIMACS_unit | objective | 39.0647 | 40.1063 | 40.1063 | 40.1063 | 39.8459 | 63/72 |
| SATLIB_hash_weighted | witness | 22.5951 | 22.5951 | 22.5951 | 22.5951 | 22.5951 | 40/120 |
| SATLIB_hash_weighted | relations | 22.5951 | 22.5951 | 22.6526 | 22.5951 | 22.6095 | 40/120 |
| SATLIB_hash_weighted | objective | 23.6893 | 23.6893 | 22.5951 | 23.6893 | 23.4157 | 40/120 |
| SATLIB_unit | witness | 24.6453 | 24.6453 | 24.6453 | 24.6453 | 24.6453 | 40/120 |
| SATLIB_unit | relations | 24.6453 | 24.6453 | 24.6453 | 24.6453 | 24.6453 | 40/120 |
| SATLIB_unit | objective | 24.6453 | 24.6453 | 24.6453 | 24.6453 | 24.6453 | 40/120 |
| C3 | witness | 68.6264 | 56.5159 | 68.6264 | 68.6264 | 65.5988 | 91/96 |
| C3 | relations | 68.6264 | 68.6264 | 68.6264 | 68.6264 | 68.6264 | 96/96 |
| C3 | objective | 69.1124 | 69.1124 | 68.6264 | 69.1124 | 68.9909 | 96/96 |

## What the results support

This extension does not support a general transfer advantage for witness-guided authoring. Its mean falls below Degree in all five populations. Objective-only winners exceed Degree by 0.5105 percentage points of U on hash-weighted DIMACS and 0.7583 points on C3, but lose on both SATLIB variants and unit DIMACS. These descriptive improvements are relative to this fixed constructive reference, not newly demonstrated superiority to the published native algorithms. The old native solver study remains distinct.

On C3, objective-only achieves 98.1218% of the old best verified feasible reward (Degree 97.0380%); it does not improve the mean prior feasible envelope. Relations and objective complete all 96 C3 arm assignments. Witness completes 91/96: its block-1 extra neighbor_pack score term times out on five C3 contexts, reducing that block to 56.5159%U versus 68.6264%U for the other witness blocks. This is direct evidence that feature/rule cost learned on TRAIN can become unfavorable under transfer. It supports reporting computation cost and complete-schedule coverage, not claiming the complexity itself is advantageous.

On both SATLIB variants each arm completes only 40/120 assignments, whereas Degree completes 20/30. The large failure-zero quality gap is therefore partly a budget/coverage failure. Comparing only completed cases would remove the central observed limitation and is not the reported primary measure.

Several independently assigned frozen winners have identical deployed ASTs. They remain separate real executions. Close-to-deadline differences among identical ASTs can reflect process-clock/runtime variation; they cannot be attributed to the authoring evidence. Unit-weight score transformations also often preserve action ordering. Neither repeated authorship labels nor similar curves establish an LLM benefit.

## Timing scope

The same unchanged execute backend was used for every arm and Degree on this local host, with 16 parallel workers and deterministic assignment order. Total returned assignment CPU was 4,186.625 seconds; the whole run plus source/trace validation took 367.665 elapsed seconds. Maximum recorded assignment CPU was 5.03125 seconds. Late cooperative overshoot is retained. Concurrent-host elapsed measurements should not be pooled with the previous server/native timings or interpreted as uncontended deployment latency.

The append-only budget_scope_clarification.json corrects the protocol wording without changing any code, data or budget: returned CPU/wall timers start before AST parsing, but the meter is constructed after FeatureRuleProgram.from_dict. The five-second cooperative deadline covers compiled evaluator initialization, queries, updates and scheduling after parsing; actual returned cost also includes parsing, feasibility and exact-reward validation. Graph materialization (0.84375 CPU seconds total, maximum 0.0625 per context) and source reconstruction/validation are separately recorded.

## Source dependence and replay

The public inventory contains 18 DIMACS and 30 SATLIB source graphs, each in unit and deterministic hash-weight variants. Those variants are not independent populations. C3 contains 12 pre-existing source subproblems with two constraint contexts each; paired contexts and source blocks are not independent satellite datasets. No new TEST selection, online LLM call, oracle-derived feature or proof of native solver optimality was added.

Protocol: experiments/discovery/matched_transfer_exploratory_v05_001/protocol.json
Source capsule: experiments/source_snapshots/v05/matched_transfer_exploratory_v05_001_source.zip
Raw archive: experiments/runs/v05/matched_transfer_exploratory_v05_001.tar.gz
Analysis: experiments/analysis/v05/matched_transfer_exploratory_v05_001.json

Protocol SHA256: `8f785558ace072936baf2e29b2c3585c1cf3fd8528036ad2398695f9cb061288`
Archive SHA256: `4b4888820ac71797aa5f1e05980f0216fd94acac2f9e17f65340001fdc8536a2`
Source ZIP SHA256: `81cee9ea27374ba055cc15a6af11d810c7aad68982a1830fbae045d202031b62`
