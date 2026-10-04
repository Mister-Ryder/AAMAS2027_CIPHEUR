# Matched cold-authoring pilot: frozen V05 results

This report follows the analysis contract frozen before any new TRAIN/TEST outcome was read. Four authoring blocks, three evidence arms, and twelve original slots per cell are a bounded descriptive pilot. It does not establish model-population superiority, public-graph transfer, or physical C3 generalization.

A receives explicit quotient equality-join witnesses plus certified labels; B receives the same certified labels; C receives objective feedback without labels. Grammar, example graphs, degree feedback, full-interface gate, TRAIN selector, and demanded runtime are common. All slots and unavailable selections remain assigned; no post-TEST selection or AST execution occurs in this analysis.

TEST quality is exact feasible reward over a common independently verified weighted clique upper, with failures zero. The denominator differs from the strongest-feasible-witness ratio used by the V04 main baseline table. Neither is a proven optimum. All sides and all registered regimes/sizes are retained. Completion of an archive means every assignment is recorded, not that every programme succeeds.

## Four-block TEST comparisons

| Population | Arm | Block 1 % | Block 2 % | Block 3 % | Block 4 % | Mean of four % | Completed/assigned |
|---|---|---:|---:|---:|---:|---:|---:|
| overall | A Witness | 79.3766 | 79.3859 | 79.3766 | 79.3766 | 79.3790 | 864/864 |
| overall | B Relations | 79.3766 | 79.3766 | 79.3287 | 79.3766 | 79.3647 | 864/864 |
| overall | C Objective | 78.4846 | 78.4846 | 79.3766 | 78.4846 | 78.7076 | 864/864 |
| standard | A Witness | 87.0447 | 87.0447 | 87.0447 | 87.0447 | 87.0447 | 432/432 |
| standard | B Relations | 87.0447 | 87.0447 | 87.0147 | 87.0447 | 87.0372 | 432/432 |
| standard | C Objective | 86.3494 | 86.3494 | 87.0447 | 86.3494 | 86.5232 | 432/432 |
| dense_long | A Witness | 71.7086 | 71.7272 | 71.7086 | 71.7086 | 71.7133 | 432/432 |
| dense_long | B Relations | 71.7086 | 71.7086 | 71.6426 | 71.7086 | 71.6921 | 432/432 |
| dense_long | C Objective | 70.6197 | 70.6197 | 71.7086 | 70.6197 | 70.8920 | 432/432 |

| Population | Contrast | Four block differences (pp) | Mean (pp) | Observed block range (pp) | Block signs +/0/− |
|---|---|---|---:|---|---|
| overall | A_minus_B | +0.0000, +0.0093, +0.0480, +0.0000 | +0.0143 | [0.0, 0.04796266362542692] | 2/2/0 |
| overall | B_minus_C | +0.8921, +0.8921, -0.0480, +0.8921 | +0.6571 | [-0.04796266362542692, 0.8920781607121385] | 3/0/1 |
| standard | A_minus_B | +0.0000, +0.0000, +0.0299, +0.0000 | +0.0075 | [0.0, 0.0299428746125538] | 1/3/0 |
| standard | B_minus_C | +0.6953, +0.6953, -0.0299, +0.6953 | +0.5140 | [-0.0299428746125538, 0.6952627140349203] | 3/0/1 |
| dense_long | A_minus_B | +0.0000, +0.0185, +0.0660, +0.0000 | +0.0211 | [0.0, 0.06598245263830002] | 2/2/0 |
| dense_long | B_minus_C | +1.0889, +1.0889, -0.0660, +1.0889 | +0.8002 | [-0.06598245263830002, 1.088893607389357] | 3/0/1 |

These ranges describe the four observed blocks. They are not confidence intervals. Paired graph comparisons do not create additional independent authoring replicates. No p-value, best-of-four result, or model-population effect is claimed.

The single common Degree reference has failure-zero quality overall: 78.573111%, standard: 86.350023%, dense_long: 70.796198%. It is not replicated as four independent authoring outputs.

In this fixed four-block pilot, explicit joins add 0.014309 percentage points over labels, with two zero block contrasts. Labels add 0.657068 points over objective feedback, with three positive block contrasts and one reversal. The observed additional join benefit is small; the label contrast concerns these particular selected programmes. Every evidence arm uses an LLM, so this design does not isolate an LLM-versus-non-LLM benefit. Token costs are unequal. These outcomes support no published-solver dominance or model-population claim.

## Original-slot TRAIN curves

Panel (a) plots cumulative eligible yield against original proposal slot; thin lines are individual banks and thick lines are four-block means. Panel (b) plots each bank's best eligible TRAIN J and a mean only when all four banks have an eligible prefix. Its count strip retains no-eligible prefixes explicitly. Invalid, missing and duplicate slots are never replaced or sorted away. These are finite-bank TRAIN sample-efficiency curves, not online learning, CPU anytime trajectories, or TEST-based prefix selection.

Eligibility is the saved full declared-interface DAG gate, not perfect scalar score agreement. Scalar agreement and actual-only gate diagnoses remain separate saved diagnostics. All 48 slots per arm have acyclic actual-only quotients; the 48/48, 48/48, 40/48 full-gate contrast therefore arises from requirements that include prior diagnostic probes. TRAIN J is reconciled to original complete-schedule reward/common frozen feasible reference and relative feature work, with failure reward 0 and failure work 100; its value may exceed 1. No new completion hard gate is introduced.

## Authoring provenance and cost

All twelve native cold CLI cells requested gpt-6.1-sol with ultra reasoning. Actual served-model identifiers were absent from the retained events. The original protocol's model label is not upgraded into observed provider metadata. Token events are retained exactly, including input, cached-input, output and reasoning-output counts; slots/settings/session counts are matched, token and latency costs are not. Cached input is a subset of input and is not added again as extra input.

| Cell | Input tokens | Cached input | Output tokens | Reasoning output | Observed model |
|---|---:|---:|---:|---:|---|
| block_0_objective | 94175 | 59904 | 6178 | 3573 | unavailable |
| block_0_relations | 145051 | 109056 | 5985 | 2761 | unavailable |
| block_0_witness | 96132 | 60928 | 8768 | 5694 | unavailable |
| block_1_objective | 143127 | 108544 | 4310 | 1479 | unavailable |
| block_1_relations | 194189 | 156544 | 4844 | 2246 | unavailable |
| block_1_witness | 146439 | 109696 | 10145 | 5140 | unavailable |
| block_2_objective | 191233 | 154752 | 5696 | 3011 | unavailable |
| block_2_relations | 350836 | 272896 | 6043 | 1803 | unavailable |
| block_2_witness | 144146 | 108672 | 13248 | 8530 | unavailable |
| block_3_objective | 191599 | 156160 | 5891 | 3446 | unavailable |
| block_3_relations | 351050 | 308864 | 8271 | 2859 | unavailable |
| block_3_witness | 96113 | 60928 | 9150 | 4871 | unavailable |

## Independent audit and immutable sources

Verified assignments: TRAIN 66×144; TEST 2808 assigned, 2808 completed. Independent checks: {'train_feasibility_replay': 466588, 'train_means': 432, 'test_feasibility_replay': 222856, 'common_clique_upper': 222790}. The analysis replays stored selected vertices and residual counts, verifies exact reward and clique partitions, and recomputes means/contrasts. It never evaluates a scorer, changes a programme, regenerates a candidate, or reruns a solver. Saved feature-gate diagnostics are reconciled but not recomputed from ASTs.

Analysis plan SHA256: `00ba0ab40374082f65cbbfe552be03c96f0201bd48ef119d64e38d74bc09a03d`; analysis script SHA256: `ff5d2555e44a2c452ee25ef1183544ca78b171c56fa3b578ae8b90498c887d9d`.

- train: `experiments/runs/v05/matched_train_v05_001.tar.gz` — SHA256 `eca11e5803ab68ba7456eca496c53a331b533fcf925eb4e108b019b1d6825d49`
- original_protocol: `experiments/discovery/v05/protocol.json` — SHA256 `4b7422b6e65c9ab670f47c4de3dd922d544d8344fc6559c4c0c79bebb82c4d02`
- training_evidence: `experiments/discovery/v05/training_evidence.json` — SHA256 `3bf0854b8ed5c4317faf68d8c614a7f9e6e405d1c3927575881478a9590def69`
- authoring_completion: `experiments/discovery/v05/authoring_completion.json` — SHA256 `5d09e7862753e87b975e9d2b68a846a4cd639379b4cdb5baa893dcb272fc88b2`
- fresh: `experiments/runs/v05/matched_fresh_v05_001.tar.gz` — SHA256 `2c2dca62ed8b769f3e7929f6beee9ef16b91f0617eba04ec5885b0ce3fb6610a`
- evaluation: `experiments/runs/v05/matched_eval_v05_001.tar.gz` — SHA256 `acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680`

All archive/member hashes, exact paired values, complete slot statuses, selected-AST identities, work/runtime data, registered subgroups and authoring usage are retained in the source-backed JSON. No external result or model API was accessed.
