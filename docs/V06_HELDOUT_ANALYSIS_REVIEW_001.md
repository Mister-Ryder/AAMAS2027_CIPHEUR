# V06 held-out mechanism analysis: independent source/toy review

Review date: 2026-10-04. This review covers the prepared analyzer, its constructed tests, the two registered analysis configurations, and the static interface of its independent auditor. **No real held-out archive, result, certificate payload, or ongoing performance output was opened.** No programme, scheduler, feature evaluator, experimental oracle, authoring request, or selection process was executed. Only artificial statistical fixtures were evaluated. This document is the sole new project file written by the reviewer; the analyzer, tests, frozen metadata, and paper remain untouched.

## Decision and reviewed versions

The diagnostic definitions, normal-versus-error separation, fixed identity frame, and clustered aggregation pass source and constructed-test review. Ten existing toy tests pass. **Before presenting the output as bound to the complete frozen analysis/audit source, add two provenance guards:** exact hashes of the two analysis configurations and the independent auditor's helper-source closure. These omissions do not establish an error in any actual scientific result, which this review did not inspect.

| Source | SHA-256 at review |
|---|---|
| `scripts/analyze_heldout_mechanism_v06.py` | `49cb52d6bf034c559ddd3a1babd4b958929bb6307a64b57344622b5218ff77e7` |
| `tests/test_analyze_heldout_mechanism_v06.py` | `9395cfebcf1b2255f49af01a5f522fe7e2d863034a086062fb6b0b3fcd7348a6` |
| `scripts/verify_heldout_results_v06.py` | `2e6625390671b515dada316da82be0f05af73ff1e3402a50e836fd0c34f39bd9` |
| `configs/analysis_v06_001.json` | `52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1` |
| `configs/analysis_refinement_v06_002.json` | `f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769` |

## Provenance guards to add

### Registered configurations

At analyzer lines 538–540, `main()` reads both configurations and checks their two pre-evaluation Boolean flags. It records the current file hashes in output metadata but does not compare them to the registered hashes. Consequently the flags alone cannot demonstrate that the bytes are the original registered specifications. For example, a replacement object containing only the requisite `registered_before...: true` field satisfies this gate while omitting the original scope.

Require the exact two hashes listed above before loading any held-out payload. Hash checks also bind their versions, inheritance, selector scope, and attribution text. Preserve the configurations; no scientific runtime change is needed.

### Independent auditor closure

`validate_audit()` binds zero errors, an empty error list, positive integer check count, archive SHA, current auditor main-file SHA, full frame, and no selection/reexecution calls. However, it ignores `independent_helper_sha256`, which the auditor already emits for:

- `scripts/verify_matched_llm_v05.py`;
- `scripts/verify_public_alias_v05.py`;
- `scripts/verify_synthesis_train_v06.py`.

An in-memory artificial report with otherwise valid R2 fields and `independent_helper_sha256={"incorrect_helper.py": "stale"}` was accepted by `validate_audit()`. Thus the current validator is not a complete exact-source gate for the independent mathematics implemented through those helpers. Bind the exact expected helper set and hashes, ideally pinned to reviewed source bytes, before accepting the report. This does not require rerunning scientific programmes or modifying frozen study inputs.

Other input bindings are well structured: final audit/archive checks precede payload reading; the terminal marker precedes result reading; raw results SHA and identity/variant counts are checked; the full frozen evidence, mapping, source, root release, and selection provenance are transitively checked by the independent auditor. The analyzer preserves audit-file, terminal, protocol, source, archive, and root-release bindings in its output. Those are useful provenance receipts, not signatures authenticating an arbitrary hand-written audit report.

## Certified-gap diagnostics are distinct from achieved scheduling quality

For a strict interval `[L,U]` representing `Q(a)-Q(b)`, the minimum certified preferred gap is `L` when `a` is preferred and `-U` when `b` is preferred. The analyzer correctly requires a positive gap and does not invent one for unknown or tie labels.

It computes two different quantities:

1. **Gap-weighted specification violation:** gap if the frozen strict-margin ranking check fails, otherwise zero.
2. **Hypothetical pairwise rank-choice minimum loss:** gap if a two-action score comparison, using vertex-ID ties, chooses the certified worse action, otherwise zero.

They are not interchangeable. The existing tiny-margin toy ranks the preferred action above its rival but fails the required margin; its specification violation is positive while hypothetical wrong-choice loss is zero. An exact score tie may also have positive specification violation but zero hypothetical loss when ID order happens to choose the preferred action.

These are full-residual, boundary-conditional, two-action diagnostics. They do not show the action selected by the actual restricted repair search; they do not measure pivot efficiency, complete-schedule reward, online regret, or loss relative to an unconstrained global optimum. Multiple query losses can concern overlapping decisions and must not be summed or averaged and described as achieved schedule loss. The analyzer's output names and limit statements correctly describe this restriction.

Actual kernel rewards come from separate audited incumbent receipts. They retain the original graph boundary and exact weight objective. Error incumbents remain diagnostic only; normal `completed=True, error=None` returns populate normal-performance statistics. Ordinary time/work/node-budget termination remains a normal anytime return with its actual feasible reward. The `normal_budget_stop` count reflects the kernel's broader `budget_exhausted` flag, not exclusively exhaustion of the global wall deadline.

### Raw diagnostic gaps should be shown by family

The analyzer produces both global mechanism summaries and family-specific mechanism summaries. Global gap summaries pool raw conditional completion-value units, even though kernel raw objectives are separated by family. This is an interpretation risk if graph families have different reward scales. An additional artificial fixture with gaps `[1,100]` had pooled violation mean 50.5; rescaling the second family's unit to give gap 10,000 changed that mean to 5,000.5 while every ranking pass/fail stayed the same.

Use the existing family-specific gap outputs in the manuscript. If a global gap number is retained in an auxiliary report, label it as a pooled, scale-dependent diagnostic and state the common-unit assumption. It must not be presented as normalized algorithm quality, cross-family scheduling regret, or an LLM-specific gain.

## Identity frame, missingness, and fixed comparisons

The frame is **31 frozen identities × 6 variants × 72 original states = 13,392 kernel positions**:

- R2: 27 identities, comprising four proposed joint W winners, twelve nonguarded W/R/O quality comparators, two TRAIN quality-only controls, Degree, and eight fixed control-bank identities;
- EoH: four separately frozen quality-pipeline identities, with their explicit winner origins;
- each uses the original graph-ID assignment and all five prescribed relabelings.

The analyzer retains role, arm, block, source identity, programme/AST hashes, joint-gate status, missing status, and EoH winner origin. Duplicate ASTs remain separate dependent identities; the four EoH origins cannot be treated as four independent newly authored winners when the frozen metadata says they came from the shared seed. The ten-test artificial full frame retains all 31 identities and 13,392 positions and exposes duplicate AST groups rather than dropping them.

Missing identities, interface failures, worker/validation failures, and programme-error incumbents are explicit. Unobserved fit/reward is null, not zero; `summarize()` reports assigned, measured, and missing members. A full-members mean exists only when all assigned members are measured, while conditional means and their denominators remain secondary. Paired reversal correctness requires both measured endpoints; tie transitions and unknown intervals remain separate categories.

Degree comparisons use the same state and same relabel variant with both policies normally completed. There is no best TEST comparator selection. Work, CPU, and wall ratios require positive/nonzero denominators; zero-reference reward produces an undefined percentage gain, not an invented ratio. Raw kernel objectives and raw role reward contrasts stay family-specific.

The fixed four-block contrasts distinguish common-selector W/R/O quality comparisons from joint-versus-quality comparisons, the latter also changing selection. All remain conditional on the common R1 seed and frozen cohort. The code does not rank candidates on TEST and redeploy the winner. The upstream independent audit remains essential because internal compaction uses dictionaries and relies on its uniqueness/full-frame checks.

## Source bootstrap and two different renaming estimands

The registered bootstrap uses 2,000 replicates and seed 261004. It samples source/pair clusters inside family strata, retaining both constraint endpoints and all within-cluster targets. Missing-only source clusters remain in the resampling frame; conditional denominators and valid replicate counts are explicit. These intervals concern source uncertainty conditional on the frozen programmes and four descriptive authoring blocks. They are not uncertainty over models, prompts, authoring attempts, or independent relabel draws.

Five relabelings collapse inside each query/state before the source bootstrap. Missing any of the five makes the corresponding all-five statistic null. Cost worst cases use maxima, while fit/reward worst cases use minima. Original IDs remain separately displayed.

Two legitimate but different robustness quantities are emitted:

- `five_rename_robustness`: take the worst **whole-dataset mean** among the five shared mappings;
- `five_rename_source_bootstrap`: first take the worst mapping **for each query/state**, then average/resample those collapsed rows.

An artificial two-query case made mapping 0 fail only query 0 and mapping 1 fail only query 1, with the other mappings passing both. The worst shared mapping's fit was 0.5; the mean per-query worst fit was 0.0. Both calculations are correct. In general `mean(min over mappings)` can be below `min over mappings(mean)`. Figures and captions must specify which question they answer and must not label both merely “worst renaming.” For cost maxima, the corresponding inequality reverses.

The four-block source contrast keeps fixed block rows together inside the source resampling frame; it does not bootstrap block rows as additional source samples or independent model draws. Its complete four-block mean becomes null if a required complete block contrast is missing.

## Cost and remaining interpretation limits

The analyzer preserves kernel versus task CPU/wall, graph-materialization time, feature/repair work, search nodes, and actual assignment/interface costs separately. It performs no new timing measurement. The audited operation counter is a proxy, not equivalent CPU across a Python policy and a native baseline. Interface costs, kernel costs, and authoring costs represent different phases and must not be merged or substituted without an explicit scope.

Normal-only cost statistics are accompanied by failure coverage; retained-error diagnostic receipts do not make an errored policy a successful deployment. Conversely, an anytime budget stop is not a failed programme. A source interval for a favourable paired reward ratio cannot establish an LLM-specific effect when the comparison includes selector or shared classical components.

## Executed verification and final boundary

`python -B -m unittest tests.test_analyze_heldout_mechanism_v06 -v`: **10 constructed tests passed** in approximately 1.6 seconds. They cover terminal gating before incomplete result reads, stale/failed audit rejection, null denominators, paired cluster resampling, signed gaps and margin failures, tie choices, reversal completeness, relabel missingness/worst directions, error-incumbent versus normal-cap treatment, and the complete 31-identity frame.

Additional in-memory fixtures confirmed the missing helper-closure check, the two distinct renaming estimands, and the scale dependence of pooled raw gap diagnostics. No real held-out effect, coverage value, cost, rank fit, or schedule-quality number was inspected. Final acceptance requires the additional frozen-source guards and a complete independent zero-error audit of each canonical result archive; this review alone is not that result audit.

## Final follow-up: provenance and diagnostic-scope fixes reviewed

The initial text and counterexamples above remain historical. The initial review document SHA was `0c3f1b796c306a18b5671369611d5be152384dc3da40fdbc9e810c0ffb018915`. The two provenance omissions apply to analyzer SHA `49cb52d6…8ff77e7`; they are **resolved in the final reviewed analyzer** `5acedcb11f0a407e377b98a24162ae9f1864a0e275faa5a28f59ccb323fb54d2`. Updated tests have SHA `dccdf09d88f6a24ec10687109064ffc1ce938f153a77d7094c09fa013d3c8eb3`.

`validate_analysis_configs()` now requires the exact two registered hashes before any archive/audit payload reading. It is called from both the main entry point and `load_batch()`, so direct batch loading cannot bypass the guard. The unchanged registered Boolean checks remain additional consistency checks.

`validate_audit()` now requires the complete current three-helper digest dictionary, including its exact names and no extras. Missing, stale, extra, or changed helper bytes invalidate the audit gate. The independently observed helper closure at this follow-up was:

| Helper | SHA-256 |
|---|---|
| `scripts/verify_matched_llm_v05.py` | `52b331fea2214642ac50ffe3996c95a6fb9893320e50df84e1371f8fedae087b` |
| `scripts/verify_public_alias_v05.py` | `6b349b659bad3acfd3a9e1abbf9046a984f8f66df05068841c1ba8c076aa959a` |
| `scripts/verify_synthesis_train_v06.py` | `941264da65d8aac3ccb9242de75ebff4c7f8cc29eb602e071be11d4e25dc8322` |

The original artificial report containing `{"incorrect_helper.py": "stale"}` is now rejected. Exact configuration bytes pass; the updated tests also reject changed bytes with unchanged preregistration flags before any archive reader is called.

Each query summary now explicitly identifies its family set, `mixed_family_diagnostic_only`, and `primary_paper_loss_eligible`. Mixed-family raw gap quantities remain auxiliary diagnostics; only a single-family summary is flagged for primary loss presentation. Output units and limits repeat this qualification. The source no longer leaves the scale-dependent mixed diagnostic eligible for unqualified paper loss conclusions.

Independent execution of the updated constructed suite: **13 tests passed**, approximately 1.66 seconds. This includes the original mathematical/null/frame tests plus exact configuration pins, the complete helper gate, and mixed-family diagnostic qualification. No actual held-out outcomes, scientific programmes, or new oracle calls were read/executed. No code, test, configuration, frozen runtime, or result was changed by this reviewer.

Final verdict: **SOURCE/TOY PASS** for the final analyzer version above. The distinct global-versus-per-query worst-renaming estimands and the separation between certified pairwise diagnostics and achieved kernel quality remain required interpretation limits. A complete, independently audited canonical-results input is still mandatory; this follow-up is readiness review, not a real-results audit or an efficacy claim.
