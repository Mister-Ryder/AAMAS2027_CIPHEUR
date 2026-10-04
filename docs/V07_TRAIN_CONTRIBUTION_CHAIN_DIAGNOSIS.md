# TRAIN contribution-chain diagnosis from existing R2 receipts

The schedule-quality plateau already occurs on TRAIN. A TEST distribution shift cannot be its principal explanation. The saved receipts instead show a common initializer and outer repair neighborhood, followed by local optimization that reaches the same objective regardless of program ordering.

This is a narrow read of the existing frozen source, original TRAIN candidate logs, and existing audit metadata. No oracle, optimizer, model, production scorer, mathematical verifier, or scientific replay was executed. No TEST performance analysis was loaded. Counts below are descriptive field aggregates from the original logs.

## Recorded facts

| Link or measurement | Existing observation |
|---|---:|
| Original candidate programs | 120 |
| TRAIN states per candidate | 120 |
| Saved kernel assignments | 14,400 |
| Completed kernels | 14,400 |
| Distinct final macro-quality values | One: `2693/4480` |
| Final value and selected set equal to common Degree initializer | 14,040 assignments |
| Positive committed improvements | 360 assignments/patches |
| States improved, identically in reward across all candidates | Three |
| States with different final reward across candidates | Zero of 120 |
| States with different final selected sets across candidates | One of 120; eight distinct sets, all equal reward |
| Global budget stops / patch-node budget exhaustions | 0 / 0 |
| Saved patches | 163,187 |
| Root-bound-pruned patches before local priority computation | 139,411 |
| Completed restricted searches | 23,776 |
| Patches reported `restricted_exact` | All 163,187 |
| Truncated patch regions | 240 |
| Kernels that actually called the program score | 8,400 (70 states × all 120 candidates) |
| Local program priority-score calls | 154,579; range 0–137 per kernel |
| Charged feature work | 51,020,993 |
| Patches with a program order different from Degree order | 16,564 |
| Actual local pivot disagreements against Degree order | 22,513 of 44,277 pivots |

The status counts are `no_improvement_in_attempted_patches: 14,280` and `patch_limit: 120`. Patch termination counts are `root_bound: 139,411` and `restricted_optimum: 23,776`; there are no saved node-budget terminations. Local exactness is confined to each explicit restricted patch. These facts do **not** prove a globally optimal schedule or absence of larger exchanges.

The common initial macro quality is `16123/26880` (0.5998139881); final quality is `2693/4480` (0.6011160714). The increase is `1/768`, common to every candidate. This calculation uses original recorded initial/final rewards and original per-state total weights with the same family macro definition. There are 119 TRAIN graphs of total unit weight 32 and one of total unit weight 28; assuming every denominator is 32 would be incorrect.

All three improvements are public induced states:

| State | Degree initial reward | Final reward for every candidate |
|---|---:|---:|
| `v06_public32|MANN_a9_unit` | 14 | 15 |
| `v06_public32|hamming6-2_unit` | 16 | 17 |
| `v06_public32|p_hat300-1_unit` | 3 | 4 |

The eight different final selected sets occur only on `p_hat300-1_unit`; they all have reward four. Thus the programs are neither all ignored nor all producing identical choices. They can alter a tied optimum and search work without altering the final scalar reward.

## Where the observable contribution chain stops

1. **Program generation → offline full-residual scores works.** The original interface assessments save `strict_checks`, strict/alias passed counts, demanded features, quotient status, and charged interface feature work. Those observations vary among programs. They do not by themselves establish schedule improvement.
2. **Offline ordering → runtime local ordering partly works.** The kernel receipts record actual priority-score calls, different `priority_order` lists, and pivot disagreements. The head is genuinely evaluated on 70 states for every candidate. On the other 50 states no patch gets beyond a sufficient root bound to request the head.
3. **Different ordering → different local objective does not work in this TRAIN regime.** Root bounds close 139,411 patches without using the head. Every remaining saved patch also reaches a restricted optimum. Consequently the branch order can change search effort or which equal-value witness is first, while an exact local optimum removes its objective effect.
4. **Local repair → global reward is shared.** The only improvements are the same three one-unit gains for every candidate. Source defaults use `policy_scope='branch'`: common Degree initialization and common Degree target/region construction; the program only affects local greedy/pivot order. The policy is not allowed to change the global initializer, destroy proposal, expansion, or restriction ranking in this track. A patch commits only a strictly positive gain; equal-value alternatives are not a separate diversification move.
5. **Schedule quality → candidate selection has no discrimination.** All 120 candidates have the same exact macro-quality value. In the joint selector, gate/strict-fit and cost therefore determine distinctions that reward cannot make. In the quality-only selector, the remaining work/slot tie-break determines distinctions. This is an observable flat objective channel, not proof that better representations lack value under every kernel.

Example saved runtime evidence: candidate `block_0_witness:3`, state `v06_public32|C250.9_unit`, target `232`, destroy `{30,77}`, patch `{232,30,77,88}`. The program order is `[88,232,77,30]`, versus Degree `[30,88,232,77]`; the pivot differs. Restricted search nevertheless returns lower=upper=2, gain=0. This directly demonstrates differing executed ordering whose objective effect is closed by local exact search.

## Certification boundary and deployment boundary differ

The original TRAIN evidence certifies competing actions on their full residual snapshots with the recorded fixed/excluded commitments (the prepared states use empty commitments). `interface_assessment` constructs a compiled evaluator over that full active residual.

Actual repair first retains the common incumbent outside a destroyed set, forms a free local region, and scores only the induced active patch. Its outside incumbent is effectively committed while the free region is searched. `repair_schedule` supplies `_priorities(graph, region, program, ...)`; `_solve` invokes that priority factory only after the root bound fails to close the patch. Typed structural features can therefore receive a different active neighborhood from the offline full-residual certified comparison.

This is a source-level difference of decision boundary and action location. The receipts do not save a complete explicit join from every certified `(state,a,b)` comparison to every actual repair pivot/scoring call. They therefore cannot establish the proportion of violated full-residual specifications that are encountered as genuine runtime choices, nor whether enforcing each original certificate would improve a particular patch. No such alignment or benefit is assumed here.

## What remains unresolved

- Whether the same frozen representations would improve reward when local search is genuinely limited before reaching its patch optimum.
- Whether representation-driven target/destroy/region decisions, or non-improving diversification, would expose a useful action preference under a shared valid kernel.
- Whether local-boundary certificates rather than original full-residual requirements would better predict the actual execution choices.
- Whether any alternative would outperform a strong common initializer after all representation/search costs are charged.

These are hypotheses requiring a new registered TRAIN study; the present receipts do not answer them. A larger TRAIN set alone is not an established remedy. Merely enlarging the dataset while preserving an initializer/repair regime that closes the same objective channel can reproduce the plateau.

## Exact evidence locations

- Original archive: `experiments/runs/v06/refinement_train_server_v06_002.tar.gz`, SHA256 `9ad65026b830a44365fab90655ae3620fcddb6c263e063bde334ae6301c5a185`.
- Log member: `refinement_train_server_v06_002/llm/candidate_results.jsonl`, original saved bytes 197,638,849; recorded SHA256 `230daa4b100551bcf55030ea5c766192000071d2ef5091937a9fd1f3deac745b`.
- Existing audit: `experiments/analysis/v06/refinement_train_audit_v06_002.json`; its metadata and totals already bind 14,400 kernel assignments and 163,187 traces. No audit was rerun here.
- Existing descriptive review: `experiments/analysis/v06/refinement_train_scientific_review_v06_002.json`, with the original plateau statement and `2693/4480` arm means.
- Initial and final sets/values: `kernel_rows[].result.{initial_selected,initial_value_exact,selected,value_exact,improvements}`.
- Executed program cost: `kernel_rows[].result.meter.{feature_work,repair_primitives.priority_score}`.
- Search saturation and actual ordering: `patch_trace[].{root_pruned,restricted_exact,restricted,termination,priority_order,common_degree_order,pivot_count,degree_pivot_disagreements,gain_exact,committed}`.
- Shared scope and positive-only commit source: `cipheur/repair_v06.py` (`repair_schedule`, `_solve`, `_initialize`, `_priorities`). Assessment and macro-quality source: `cipheur/synthesis_study_v06.py` (`interface_assessment`, `assess_candidate`, `macro_quality`). Selection roles: `cipheur/refinement_study_v06.py` (`quality_key`, joint selection).
- Original source capsule: `experiments/source_snapshots/v06/refinement_train_server_v06_002_source.zip`, SHA256 `67239f759c17cf347e663b6495e6dc47a550ffd56fcd86d7e069c20afe3140fc`.
