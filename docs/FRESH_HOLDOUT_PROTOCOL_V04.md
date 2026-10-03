# Fresh v04 confirmation protocol

This is a new confirmation study after known v03 failures motivated a revised TRAIN method. It does not relabel development or old test evidence as a new test. Programme authoring and final thresholds are fixed before v04 TRAIN outcomes; numerical selection uses only the 66 declared TRAIN graph contexts. Fresh validation has no role in candidate selection. A fresh TRAIN freeze must precede any fresh test quality outcome.

## Freeze and receipts

Archive the exact 93-programme bank, final TRAIN config, selected programmes, primary-only guided ablation, information gate/master logs, and module/compiler/backend source hashes. The selected-programme receipt must contain `selection_split=train`, `test_accessed=false`, programme definitions and the bank/config hashes. The v04 backend is uniformly `score_slice=True`, including all old controls. Record the backend source hash: inference cost is not interchangeable with v03 full-interface cost.

Record the authoring scope honestly: one continuing assistant agent session with root feedback before v04 TRAIN results, served model `gpt-6.1-sol` from trusted root metadata, 12 final new proposals, zero external API calls, token usage unavailable. The single authoring session is not a replicated LLM generation experiment. Old free/rule/enumerated banks remain frozen controls. If the compiler changes after selection, remeasure selection cost on TRAIN and refreeze before generating fresh test outcomes; do not reuse a changed backend with an old cost-based freeze silently.

After the freeze, the new independent confirmation uses fresh input identities. No replacement instance may be chosen because a candidate or oracle performs poorly. Any source shortage is reported as a shortage. Prespecified changes require a new protocol receipt and must be distinguished from the original confirmation.

## Fresh temporal generators

`configs/relevance_v04_fresh_protocol.json` specifies both standard and dense-long profiles, each with balanced, ground-scarce and satellite-scarce resource regimes and sizes 64/128/256. Validation has three paired instances per cell; test has twelve. This is 54 validation pairs (108 graph contexts) and 216 test pairs (432 contexts), before any C3 source-derived addition. The namespace is 40,000,000 for standard and 140,000,000 for dense-long, separate from v03's 9,000,000 and 109,000,000 namespaces. Split offsets remain one million; size contributes 1,000 times the size and instance index is below 1,000. Seeds are checked for split overlap. Distributional generator parameters and interventions retain the declared profiles, with no oracle call or outcome filtering during generation.

The two intervention sides preserve all contact IDs, weights and windows. The standard profile horizon is 1.8 times n and durations are quarter-grid values from 0.5 through 12; dense-long horizon is 0.18 times n and durations through 48. Ground gaps are the prespecified split-specific values; satellite gap stays zero. Freshness means new generated contacts/seeds, not a new deployment population.

The same seed is deliberately reused across resource regimes, creating common-random-number pairing. Cluster analyses across regimes by that seed/profile/size identity, rather than treating every configuration side as an independent draw. Intervention sides also belong to one pair. Report regime and density strata as well as any aggregate; do not let a large synthetic stratum hide a dense or C3 failure.

## Fresh C3 source blocks

Fresh C3 evaluation requires the union of **all previously exposed v03 train, validation and test original contact IDs**, including discovery/development and all old holdout/transfer input containers. Read only their saved `data.json` input members; never their result files. `cipheur.study_data_v04.prior_id_manifest` checks source IDs against all actual contacts on both intervention sides and records the source-data SHA256 and each input member SHA256. The caller must enumerate every exposed input container. The builder cannot prove an unknown archive was not omitted, so inventory completeness is an explicit protocol obligation and must be independently reviewed.

The new builder excludes this union globally before source-day block construction and rejects an inconsistent source-data hash. Validation draws unused day-1 contacts; test draws unused day-2 contacts. It requests three time-ordered disjoint source blocks at each of 64/128/256/512 contacts. The split source days remain fixed and the intervention parameter cycle remains outcome independent. Unavailable blocks appear in the shortage receipt and receive no replacement with an already exposed block. New IDs are `v04_c3_...`, but original source IDs, not renamed record IDs, establish freshness. The two sides share one source block.

This is a new subset of the same C3 physical source, not independent satellites, seasons, data sources or external deployment generalization. Use a whole disjoint source block as the statistical unit; the two configurations and multiple diagnostics on that block do not create additional independent samples. The public original scheduling verifier must still recheck produced schedules through the existing source adapter. Graph feasibility and source feasibility should both be reported.

Builder command after a successful freeze (the input list below must be completed with every exposed v03 data container):

```text
python -m cipheur.study_data_v04 --config configs/relevance_v04_fresh_protocol.json --frozen runs/relevance_train_v04_001/frozen_programs.json --prior-input PATH_TO_DISCOVERY_DATA.json runs/development_scale_001/data.json PATH_TO_OLD_HOLDOUT_INPUT.tar.gz PATH_TO_OLD_TRANSFER_INPUT.tar.gz --stable-root PATH_TO_FROZEN_V51_SOURCE --out runs/fresh_data_v04_001
```

Paths are arguments to read local/server input sources already controlled by the root runner, not requests for this subagent to obtain credentials or contact a server. Omitting `--stable-root` builds only fresh temporal inputs and marks C3 as not generated. A temporal-only result must not be described as completed C3 confirmation. The simpler `relevance_synthesis_v04 --mode fresh-data` command generates temporal inputs only; the unified builder above additionally enforces the TRAIN freeze and C3 identity rules.

## Budget and failure accounting

Constructive programmes receive the same declared five process CPU-second cooperative cap under the sliced backend. Save measured feature work, CPU and wall time, completion status and schedule. Timeout returns no completed schedule and invokes no fallback. Report completion rate, quality among completed cases, and zero-normalized quality across all requested cases separately. Reporting only completed cases would favor a programme that times out on difficult cases.

Existing HiGHS reference uses ten seconds and local search uses two seconds; these are separate comparison budgets, not a claim of matched compute. Keep lower/upper/timeout statuses in reference logs. If a new public solver benchmark or SOTA comparator is added, freeze its version, actual runnable configuration, preprocessing, graph/complement convention, objective weighting, CPU allocation and time limit independently before its first outcome; do not claim that a named package was run if only literature was inspected. Public unweighted DIMACS and weighted scheduling subsets are distinct scopes.

## Prespecified analyses and interpretation

Primary confirmation is complete schedule reward/cost with all requested cases accounted for, plus strata and paired uncertainty. Secondary analysis checks actual reached boundaries under the frozen programmes, with finite-pool regret lower/upper, unknown counts, reachable/unsampled denominators and source/configuration auditing. Conditional preference/regret cannot establish a global scheduling guarantee. A base quotient may be acyclic on a natural bank and still admit poor heuristic behavior; that possibility is an explicit falsifiable limitation, not evidence to discard a stratum.

Retain the prior g03 minimum-interface result as an ablation, the v03 main g05 as a prior control, g12, g18, all free/rule/enumerated controls and the v04 primary-only selection ablation. Candidate generation and proposal counts differ and should not be portrayed as replicated LLM superiority. New public baseline/benchmark results may broaden external scope, but do not repair freshness or establish causal effects of a single score term by themselves.

If the fresh test is negative, report it and the archived freeze unchanged. A later redesign must be a separately declared study with another fresh test identity set. Development improvements, old transferred outcomes and fresh validation descriptions remain labelled accordingly.
