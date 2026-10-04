# Frozen V003 performance analysis interface

This is an outcome-free statistical implementation prepared while the performance batch runs. It reads **only final compact rows bound to a zero-error independent performance audit**. It does not open the run archive, raw results, graphs, ASTs, author responses, or live progress. It imports no scheduling runtime and calls no optimizer or model.

## Input barrier

`scripts/analyze_performance_test_v06.py` requires:

- `--audit`: independent report with integer `errors: 0`, original `archive_sha256`, exact `audited_rows_sha256`, and `registered_constants` containing `wall_targets: [0.1, 1, 5]`, `total_contexts: 302`, `total_assignments: 52548`, `policy_slots: 23`.
- `--rows`: the hash-bound final compact JSONL, including **every assigned row**, even unsupported, missing, failed, and unreturned requests.
- `--out`: a new directory; an existing analysis is never overwritten.

The audit also supplies 23 frozen policy metadata entries in `policies`. Each uses the same fields as compact rows: `method`, `analysis_cohort`, `program_kind`, `program_role`, `authoring_block`, `authoring_arm`, `program_sha256`, `published_winner_origin`. Roles have fixed counts: `joint_W`, `quality_W`, `quality_R`, `quality_O`, and `published_EoH_DSL_quality` each have four identities; `control_structural`, `control_base9`, and `Degree` each have one. A duplicate AST remains a distinct requested identity. Seed-origin EoH winners retain their origin; quality-only identities cannot become genuine joint winners.

Every row includes `id, population, family, n, regime, profile, pair_id, side, source_cluster, target, track, method, seed, analysis_cohort, program_kind, program_role, authoring_block, authoring_arm, program_sha256, published_winner_origin, success, returned, status, error, reward_exact, total_exact`. Exact values are integer/rational strings; unsuccessful quality is null, including diagnostic retained incumbents.

Optional measurements are numeric or null: `standalone_wall_seconds`, `standalone_cpu_seconds`, `native_wall_seconds`, `native_cpu_seconds`, `policy_wall_seconds`, `policy_cpu_seconds`, `shared_graph_load_wall_seconds`, `shared_graph_load_cpu_seconds`, `work`, `search_nodes`. Times are audited measurements, not estimates from nominal budgets. Warm standalone costs already charge the entire shared initializer plus the individual repair; the analyzer does not amortize them over policies. Shared graph-loading cost remains explicit and a separate standalone-plus-loading estimate is also produced.

The full matrix is checked again: 302 contexts, all three targets, 23 identities in both policy tracks, five native methods with their prescribed 11 total seed assignments, and the common half-target initializer. Six original `fresh_*` family names remain unchanged and together cover 216 endpoints; WDP25, Segmentation3, Grids10, C3 interval24, and C3 legacy24 remain separate. The independent audit certifies feasibility, objective reconstruction, phase costs, and source provenance; this analysis does not replace that audit.

## Estimands and missingness

Native seeds are averaged **inside each source/context first**. Frozen role members are similarly averaged inside each context. The primary quality value exists only when every requested member succeeds. A separately marked available-member conditional mean and its exact denominator are retained. No failed seed/program is filled with zero, dropped from coverage, replaced, or selected by its TEST quality.

CHILS full-target **native seed1** is the fixed reference, including for its own stochastic source mean. It is never replaced by the best seed or TEST method. Paired percentage gains are null when either quality is unavailable or reference reward is zero. Negative gains remain. Other prespecified contrasts include same-track Degree, joint W against quality-only R/O and EoH, quality-only W–R and R–O, and warm–cold shared-initializer differences. Four matched R2 block contrasts are separately retained. These comparisons distinguish framework-plus-selector differences, conditional generation contrasts, and classical-component gains.

Source/pair-cluster bootstrap uses **2,000 replicates, seed261004**. Fresh constraint sides are resampled together by original pair; public and C3 observations use original source clusters. Within-source seeds and all frozen identities move together. All assigned clusters, including wholly missing clusters, enter the resampling frame. Undefined bootstrap draws are counted explicitly, with intervals conditional on defined observations. Exact point estimates are retained as rational strings. Source intervals do not establish an LLM/model-population effect; the four conditional authoring blocks are descriptive.

Raw objectives never pool across families. C3 previously exposed exploratory models never pool with unseen core inputs or with each other. Dimensionless paired contrasts may aggregate within a named population, while raw differences stay family-specific. Every identity and all three targets remain in budget curves, even when an entire point is null. Connected budget points are not an invented anytime trajectory or learning convergence curve. Nominal solver targets are not matched end-to-end deadlines or language-independent compute; actual CPU, wall, preparation, phase costs, overshoot, and measurement coverage remain visible.

NumPy, when available, only vectorizes multiplicities of the same Python-Random cluster draws; a standard-library fallback uses identical draws. Its version is recorded. Toy verification compares the two paths. Neither path reads scientific results during preparation.

## Outputs and invocation

```text
python scripts/analyze_performance_test_v06.py --audit FINAL_AUDIT.json --rows FINAL_audited_rows.jsonl --out NEW_ANALYSIS_DIRECTORY
```

The output contains four context JSONLs (cohort and identity estimates, cohort and identity paired contrasts), plus `analysis.json` with exact denominators, coverage/status counts, source intervals, phase costs, every three-point budget curve, and archive/audit/compact/source/config hashes. No best-program ranking, selection, significance test, or manuscript claim is generated.

The frozen analysis scopes are pinned to `analysis_v06_001.json` SHA256 `52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1` and `analysis_refinement_v06_002.json` SHA256 `f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769`.

Validation: 15 small artificial-data tests cover exact role averaging and duplicate AST identities, failed seeds/nulls, fixed reference, paired bootstrap boundaries, missing clusters, deterministic acceleration/fallback, matched-block heterogeneity, complete costs, all-null budget points, separated populations, changing status counts, audit/hash barriers, invalid timings, and missing assignments. No research dataset was read or evaluated.
