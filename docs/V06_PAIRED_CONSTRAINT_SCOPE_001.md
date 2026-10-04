# Existing paired constraint-intervention results (V06)

## Conclusion and scope

- All 13 strict-reversal and 83 strict-preservation requirements come from synthetic paired-contact states, not the unpaired public graphs. They are competing-action requirements, not independent scheduling instances: reversal spans seven source contact pairs and preservation eighteen.
- All 24 TEST contact pairs have identical contact arrays within each pair. The only within-pair intervention is station gap 0.25 to 2; satellite gap remains zero, resource counts remain fixed, and rewards/durations remain one. All 24 edge sets change.
- TRAIN uses station gap 0 to 1, while held-out uses 0.25 to 2. New hashed seeds draw separate contacts. Thus configuration values are withheld, but the generator family, six resource/profile families, unit reward/duration, and 32-node size remain shared. This is distribution-related generalization across one constraint axis, not demonstrated transfer across all constraint types.
- Balanced uses 8 satellites/6 stations, ground scarce 12/3, satellite scarce 3/12. Short/long horizons are 11/24. These are across-family regimes, not extra within-pair intervention axes.
- Test has 24 public unpaired states plus 48 synthetic paired states. Public source-cluster withholding occurs inside an exposed corpus. Public graphs contribute single-state strict-fit results, but none of these paired reversal/preservation rows.
- Pairwise certified correctness describes rankings under the saved full-residual empty fixed/excluded boundary. It is not actual kernel reward, repair-pivot correctness, policy regret, or evidence of universal scheduling-quality superiority.

## All frozen cohort counts, original mapping

| Cohort | Frozen identities | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---:|---|---|
| W joint | 4 | 82.69 (43/52) | 95.48 (317/332) |
| W quality | 4 | 82.69 (43/52) | 89.76 (298/332) |
| R quality | 4 | 86.54 (45/52) | 97.89 (325/332) |
| O quality | 4 | 69.23 (36/52) | 92.17 (306/332) |
| EoH-DSL | 4 | 84.62 (44/52) | 100.00 (332/332) |
| Degree | 1 | 46.15 (6/13) | 85.54 (71/83) |
| Control enumerated_structural | 1 | 38.46 (5/13) | 84.34 (70/83) |
| Control fixed_base9 | 1 | 0.00 (0/13) | 0.00 (0/83) |
| All fixed structural bank | 8 | 63.46 (66/104) | 92.77 (616/664) |

Joint W exceeds Degree on these ranking diagnostics, but the aggregate is below quality-only R and EoH for both categories. The main table therefore highlights only the actual column maxima, never an assumed W advantage. W joint versus quality-only R/O also compares different TRAIN selectors, so it cannot isolate generation alone. All cohorts retain whole assigned strict-category positions; no prediction failures or favorable pairs are filtered.

## All six family decompositions

### temporal_unit_balanced_long

| Cohort | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---|---|
| W joint | -- | 98.33 (59/60) |
| W quality | -- | 93.33 (56/60) |
| R quality | -- | 100.00 (60/60) |
| O quality | -- | 91.67 (55/60) |
| EoH-DSL | -- | 100.00 (60/60) |
| Degree | -- | 86.67 (13/15) |
| Control enumerated_structural | -- | 80.00 (12/15) |
| Control fixed_base9 | -- | 0.00 (0/15) |
| All fixed structural bank | -- | 91.67 (110/120) |

All saved requirement categories for one frozen identity: `{"exact_tie_both": 17, "strict_preservation": 15, "strict_to_tie": 15, "tie_to_strict": 7}`.

### temporal_unit_balanced_short

| Cohort | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---|---|
| W joint | 100.00 (16/16) | 95.83 (23/24) |
| W quality | 100.00 (16/16) | 87.50 (21/24) |
| R quality | 100.00 (16/16) | 100.00 (24/24) |
| O quality | 75.00 (12/16) | 91.67 (22/24) |
| EoH-DSL | 100.00 (16/16) | 100.00 (24/24) |
| Degree | 50.00 (2/4) | 100.00 (6/6) |
| Control enumerated_structural | 50.00 (2/4) | 100.00 (6/6) |
| Control fixed_base9 | 0.00 (0/4) | 0.00 (0/6) |
| All fixed structural bank | 87.50 (28/32) | 100.00 (48/48) |

All saved requirement categories for one frozen identity: `{"exact_tie_both": 28, "strict_preservation": 6, "strict_reversal": 4, "strict_to_tie": 11, "tie_to_strict": 15}`.

### temporal_unit_ground_scarce_long

| Cohort | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---|---|
| W joint | 100.00 (8/8) | 96.15 (50/52) |
| W quality | 100.00 (8/8) | 90.38 (47/52) |
| R quality | 100.00 (8/8) | 100.00 (52/52) |
| O quality | 100.00 (8/8) | 100.00 (52/52) |
| EoH-DSL | 100.00 (8/8) | 100.00 (52/52) |
| Degree | 100.00 (2/2) | 100.00 (13/13) |
| Control enumerated_structural | 100.00 (2/2) | 100.00 (13/13) |
| Control fixed_base9 | 0.00 (0/2) | 0.00 (0/13) |
| All fixed structural bank | 100.00 (16/16) | 100.00 (104/104) |

All saved requirement categories for one frozen identity: `{"exact_tie_both": 18, "strict_preservation": 13, "strict_reversal": 2, "strict_to_tie": 18, "tie_to_strict": 6}`.

### temporal_unit_ground_scarce_short

| Cohort | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---|---|
| W joint | 67.86 (19/28) | 93.75 (30/32) |
| W quality | 67.86 (19/28) | 81.25 (26/32) |
| R quality | 75.00 (21/28) | 93.75 (30/32) |
| O quality | 57.14 (16/28) | 78.12 (25/32) |
| EoH-DSL | 71.43 (20/28) | 100.00 (32/32) |
| Degree | 28.57 (2/7) | 62.50 (5/8) |
| Control enumerated_structural | 14.29 (1/7) | 62.50 (5/8) |
| Control fixed_base9 | 0.00 (0/7) | 0.00 (0/8) |
| All fixed structural bank | 39.29 (22/56) | 81.25 (52/64) |

All saved requirement categories for one frozen identity: `{"exact_tie_both": 22, "strict_preservation": 8, "strict_reversal": 7, "strict_to_tie": 20, "tie_to_strict": 7}`.

### temporal_unit_satellite_scarce_long

| Cohort | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---|---|
| W joint | -- | 100.00 (84/84) |
| W quality | -- | 100.00 (84/84) |
| R quality | -- | 100.00 (84/84) |
| O quality | -- | 97.62 (82/84) |
| EoH-DSL | -- | 100.00 (84/84) |
| Degree | -- | 90.48 (19/21) |
| Control enumerated_structural | -- | 95.24 (20/21) |
| Control fixed_base9 | -- | 0.00 (0/21) |
| All fixed structural bank | -- | 98.81 (166/168) |

All saved requirement categories for one frozen identity: `{"exact_tie_both": 22, "strict_preservation": 21, "tie_to_strict": 9}`.

### temporal_unit_satellite_scarce_short

| Cohort | Reversal correct/assigned; % | Preservation correct/assigned; % |
|---|---|---|
| W joint | -- | 88.75 (71/80) |
| W quality | -- | 80.00 (64/80) |
| R quality | -- | 93.75 (75/80) |
| O quality | -- | 87.50 (70/80) |
| EoH-DSL | -- | 100.00 (80/80) |
| Degree | -- | 75.00 (15/20) |
| Control enumerated_structural | -- | 70.00 (14/20) |
| Control fixed_base9 | -- | 0.00 (0/20) |
| All fixed structural bank | -- | 85.00 (136/160) |

All saved requirement categories for one frozen identity: `{"exact_tie_both": 23, "strict_preservation": 20, "strict_to_tie": 6, "tie_to_strict": 15}`.

## Exact fields and source bindings

- Analysis: `experiments/analysis/v06/heldout_mechanism_analysis_v06_001.json`; SHA256 `a2296b5189abc8adb9bc6e70ef04b0639d4f580929a0e4b64f332c15bef950d5`.
- Saved compact rows: `experiments/analysis/v06/heldout_mechanism_analysis_v06_001_compact.json`; recorded SHA256 `dd8687daeb7176b30f44cb92a1a1804402d39dcb9346e1c3db39303ed19a9653`.
- Summary metric path: `summaries[i].variants.original.mechanism.pair_categories.strict_reversal.joint_correctness` and the corresponding `strict_preservation` path. Family summaries: `summaries[i].variants.original.mechanism_by_family[family].pair_categories[category].joint_correctness`.
- Raw saved schema: `pair_rows[]` fields `program_id`, `variant`, `pair`, `query_index`, `cluster`, `family`, `category`, `pair_passed`, `left_passed`, `right_passed`, `left_preferred`, `right_preferred`. Use original mapping and every row of each fixed category; group identities by frozen role/arm metadata, never best TEST fit.
- Conditional schedule-quality fields are separately in `kernel_rows[]`: `normal_completed`, `normal_performance_reward_exact`, and `normal_paired_degree_percentage_gain`; these are not substituted for the pair correctness fields.
- Input state provenance: `experiments/discovery/v06_evidence_001/data.json`, `records[]` explicit split, pair/side, source.station_gaps, graph.constraints, complete graph.contacts; preparation source `cipheur/evidence_study_v06.py`.
- Query replay recipe without any solver: filter the saved `pair_rows` on `variant == original`, join `program_id` to the saved identities, retain all matching category rows, count `pair_passed is True` and `pair_passed is not None`, and show correct/assigned plus measured/assigned. No new bootstrap or oracle is needed.
- Unique assigned query categories per original identity: {"exact_tie_both": 130, "strict_preservation": 83, "strict_reversal": 13, "strict_to_tie": 70, "tie_to_strict": 59}. Tie-to-strict/strict-to-tie/exact-tie cases remain distinct rather than being relabeled reversals or discarded as errors.
- The six cohorts in the compact TeX table contain 21 of the 23 original deployment identities. The MD additionally preserves both fixed controls and all eight relabel-bank identities, totaling the original 31-identity analysis frame. Five renamings remain in saved results; this table is explicitly original-mapping only.
- Generated table: `paper/generated/paired_constraint_adaptation_v06.tex`, label `tab:v06-paired-adaptation`. No main-paper source, runtime, data, certificates, or analysis output was modified.
