# Experiments review v0.3

Owned deliverables: `paper/sections/experiments.tex` and this review. The draft follows the accepted abstract in `paper/ABSTRACT_TARGET.md` and the certified representation–rule contract in `paper/sections/method.tex`. It applies the research-paper-writing skill's claim-to-experiment discipline. No main file, source code, result artifact, or Git state is edited by this author.

## Section contract

Updated root instruction for final integration: approximately 850 words plus figures, following float congestion in a nine-body-page build. This supersedes the earlier 1,000–1,150-word target. The current section is approximately 818 visible words including active tables and figure captions; final held-out conclusions and their caption still need integration. Each study answers a scientific claim:

| Study | Claim and evidence | Necessary qualification |
| --- | --- | --- |
| Incidence | Certified ordering requirements expose missing observable distinctions. | Designed aliases do not estimate prevalence in temporal/C3 schedules. |
| Bounds and acquisition | Clique envelopes and rollout-anchored queries make certification useful. | Uniform control is also rollout anchored; challenger sampling and query ordering differ. |
| Finite repair | Small distinguishing interfaces can remove the observed obstruction. | Exact minimum is finite-catalogue, fixed-evidence, additive standalone work only. |
| Full separation | A full rebuilt quotient is necessary after a witness cover. | The four-cycle is a controlled regression fixture, not a workload incidence result. |
| Independent proposal banks | Guided/free/rule procedures differ when proposals are authored separately. | Main guided/free/enumerated selection now uses the same acyclicity/consistency gate and whole-program utility. One batch per arm still supplies no model-level synthesis replication; rule-only retains valid formulas regardless of consistency. |
| Frozen schedules | Repairs can be judged by complete feasible scheduling quality under shifts. | Test numbers must be fresh, post-freeze, held-out outcomes; development means cannot substitute. |
| Compiled cost | Sharing and residual updates reduce actual work under suitable structure. | Include initialization and dense-graph intersections; a matched trace is not a universal compiler proof. |

## Facts verified directly

- `configs/study_v03_remote.json` and `cipheur/study_data.py` prescribe 95 training pairs, 95 validation pairs, and 420 test pairs, each with two graph contexts. The allocation is temporal 60/60/360, C3 15/15/40, diagnostic 20/20/20.
- Temporal sizes: 32, 64, 128, 256, 512. Resource regimes use satellite/ground populations (8,6), (12,3), and (3,12). Ground-gap intervention pairs by split: (0,2), (0.25,3.5), and (0.5,6); satellite gap is zero.
- C3 sizes: 64, 128, 256, 512, 1,024. Original source contains 69,923 opportunities. Protocol coverage reports 822 excluded earlier-study opportunities, 27,776 distinct current opportunities, no empty blocks, and no prior opportunity reuse. Training/validation/test correspond to days 0/1/2. Successive time-ordered subproblems have disjoint original IDs.
- Source defaults for ground transition, satellite change, satellite transition: 340, 150, 300 seconds. Target values by train/validation/test: 450/600/750, 180/210/270, 360/420/540.
- Development archive `experiments/runs/v03/development_scale_001.tar.gz`: 380/380 graph tasks complete, 469.2502 seconds; eight workers; Linux 5.15, Python 3.11.17; `test_accessed=false`, `interpretation=development_screening`. Seven methods per context yield 2,660 schedules. CPU identity is not yet verified.
- Mechanism archive `experiments/runs/v03/mechanisms_001.tar.gz`: 186 evidence tasks, 51 anchored clique-envelope specifications, 150 non-diagnostic runtime contexts, three runs per backend/context.
- Baseline stress archive `experiments/runs/v03/scalability_001.tar.gz`: complete 56/56 contexts in 1,370.1378 seconds. Context counts: n=1,024: 8 balanced, 8 ground-scarce, 8 satellite-scarce; n=2,048: the same 24 temporal contexts plus 4 C3; n=4,096: 4 C3 only. This is the separate baseline scale study, not frozen guided-program held-out evaluation. Largest-size results cannot establish all-regime generalization.
- Root-verified evidence counts on 62 pairs (20 diagnostic, 42 temporal/C3): ranked/clique 172 attempts, 51 specifications (26 reversal/25 preservation), 52,355 expanded nodes; uniform/clique 170 attempts, 58 specifications (14/44), 52,377 nodes; ranked/weight-sum 176 attempts, 36 specifications (24/12), 84,138 nodes. The ranked/clique bank contains 32 diagnostic specifications (24/8) and 19 temporal/source specifications (2/17). Multiple boundary certificates from a pair must be clustered, not treated as independent samples.
- Root-verified runtime medians (interpreter/compiled), by contacts: 32: 1.102 timing / 3.190 work (24 contexts); 64: 1.205 / 5.794 (30); 128: 1.359 / 10.593 (30); 256: 1.722 / 20.324 (30); 512: 2.441 / 39.932 (30); 1,024: 4.446 / 50.993 (six C3 contexts only). All action traces agree across both backends and three repetitions.
- Runtime comparison fixes `structural_runtime` with the `NEIGHBOR_EDGE_MIN` feature and `weight-0.6*conflict_weight+redundancy/max(1,degree)` rule. It is not a general speedup measured over every final selected proposal. The paper names this fixed structural-rule scope.
- Final figure-analysis report `docs/RESULT_ANALYSIS_V03.md` confirms 2,000 percentile bootstrap replicates, seed 20261003, 95% coverage, temporal common-seed clustering across regimes, C3 source-block clustering, and stratified temporal/C3/probe resampling. Runtime takes backend median across three repetitions, then median of paired context ratios. It is not a ratio of pooled means; the single assistant batch per arm supplies no synthesis-variation interval.
- Mechanism budgets from `mechanism_study.py`: 40 conditional calls, 8,000 search nodes, two rollout steps, four query attempts, two saved relations, 500 nodes per call, region maximum 128, seed 41. `residual_evidence.py` default strict objective tolerance is 1e-8.
- Mechanism repair: four candidates; base quotient 80 classes and 50 arcs, contradictory. Exact subset master examines 16 subsets, selects `neigh_edges`, standalone additive work 6,181, one round. Rebuilt quotient 100 classes/50 arcs, no self-loop requirements, acyclic; `optimal=true`.
- Independent author audit using current `diagnose_representation` on the archived 51 specifications: the full bank has 64 strict self-loop requirements, all diagnostic. The combined 19 temporal/C3 specifications give 60 classes, 30 arcs, no self-loop, and an acyclic quotient. Per-family certificates: C3 4 preservation; balanced temporal 4 preservation; ground-scarce temporal 2 reversal/3 preservation; satellite-scarce temporal 6 preservation. These are multiple saved comparisons, not independent workload counts. The manuscript must state that impossibility is shown on constructed aliases, not observed on the sampled natural/source workload.
- Full-quotient regression figure describes a coarse two-cycle; a cost-1 feature breaks its original concrete witness but leaves a refined four-cycle; a second exact master selects the cost-2 repair. This figure is independently implementation-audited in `docs/FIGURE_DESIGN_V03.md`.
- `scale_study.py` compares five pointwise ranking programs; local search starts from their best schedule with a two-second budget; HiGHS gets ten seconds. It checks returned schedules but marks floating MILP outputs `exact=false`, `scope=floating_milp_reference`.
- Important v0.3 verification limit: `scale_study.task` reconstructs serialized graphs with `Graph.from_dict`, which does not restore the C3 `_v51_context`. `Graph.feasible` checks conflict edges. Consequently the draft does not claim that every v0.3 C3 schedule passed the original source verifier; a saved postcheck is needed for that claim.
- Original `discovery_study.py` assesses independent guided/free/rule banks plus deterministic enumeration, 24 candidates per bank; prefixes 8/16/24, fixed saved order; selection lambda .002, tau .75, validation maximum 128. The original guided minimum-interface restriction is superseded for the primary frozen program by `joint_selection.py` and `frozen_joint_001.json`; it remains as the `guided_minimum_interface` ablation.
- Final joint protocol in `docs/FROZEN_EVALUATION_PROTOCOL_V03.md`: primary test 420 pairs/840 contexts; separately declared dense/long-contact transfer 108 pairs/216 contexts at n=64/128/256 and all three resource regimes. Dense horizon 0.18n vs primary 1.8n; maximum duration 48 vs primary 12; new seed range; no transfer outcome enters selection. Whole acyclic, consistency-eligible feature–rule pairs maximize validation quality minus .002 normalized compiled work. Low/high penalties (.0005/.008), one-feature, and natural-validation-only controls are frozen without regenerating proposals.
- Verified `experiments/discovery/v03/model_provenance_receipt.json`: internal Codex assistant model `gpt-6.1-sol`, reasoning effort `ultra`, inherited by cold proposer agents; one request and 24 candidates per assistant arm; zero external API calls; token counts unavailable. This verified orchestration receipt resolves the original generation notes' unavailable model identifier. The paper uses one concise provenance sentence.
- Verified `frozen_joint_001.json` joint prefix curves: guided/free/rule selected programs unchanged at 8/16/24. Guided `g05_diminishing_pair_discount`: consistency 35/36 (97.2222%), validation quality .99322024. Free `free_04_pair_discounted_deletion`: 34/36 (94.4444%), .99035743. Rule `rule_only_conflict_mass_efficiency`: 4/36 (11.1111%), .99416780. Enumerated `enum_edge_min_2` at 16/24: 35/36 (97.2222%), .99438999, highest final validation quality. Enumeration at 8 selects `enum_edge_count_2`, consistency 100%, quality .99348018. These are training consistency and validation quality, never held-out schedule means.
- Earlier independent score audit with `ranking_report` and `evidence_relevance` started a program at every saved boundary, including counterfactual boundaries that its own rollout did not reach. On anchored51, the raw guided aggregates were 98/102 score-consistent, 88/102 reachable, 98/102 boundary-start escapes, and four consistent pair choices. The four choices are all unreachable. The raw escape total must never be presented as executed-action frequency. The final relevance audit below supersedes that interpretation.

## Reached-state relevance audit

Source: `experiments/runs/v03/relevance_001.tar.gz` and the corresponding section of `docs/RESULT_ANALYSIS_V03.md`. Eight frozen programs are audited against 51 acquired specifications (102 side requirements) with a 1,000-node conditional solver budget. Regret compares optimal residual completion at the reached saved boundary with completion forced to include the program's actual next choice. Its sound endpoints are derived from exact-rational lower/upper envelopes and clamped at zero. The resulting mean interval is a formal bound, not a 95% confidence interval. Missing unreached states are not assigned zero regret.

| Program | Reached / 102 | Actual escapes | Consistent pair choices | Mean formal regret bound, reached states | Positive / zero / unresolved |
| --- | --- | --- | --- | --- | --- |
| Guided g05 | 88 | 88/88 | 0/0 | [4.409091, 5.161932] | 4/83/1 |
| Free | 88 | 64/88 | 24/24 | [0.045455, 0.798295] | 2/85/1 |
| Rule-only | 88 | 88/88 | 0/0 | [0.045455, 0.798295] | 2/85/1 |
| Enumeration | 88 | 88/88 | 0/0 | [0.045455, 0.798295] | 2/85/1 |
| Minimum interface g03 | 88 | 87/88 | 1/1 | [0, 0.752841] | 0/87/1 |
| No-cost g18 | 86 | 80/86 | 6/6 | [0, 0.706395] | 0/85/1 |
| Natural-validation g12 | 86 | 84/86 | 2/2 | [0.825581, 1.595930] | 10/75/1 |
| Weight anchor | 102 | 0/102 | 60/102 | [6.409314, 7.058824] | 64/37/1 |

For the four main arms, 88 reached states comprise 64 probe and 24 temporal/C3 requirements. All 64 guided probe actions escape the pair but have exact zero conditional regret. Hence an escape by itself is not a bad action. On the 24 non-probe reached states, guided has mean formal regret bound [16.166667,18.927083], with 4 positive, 19 zero, and 1 unresolved; free/rule/enumeration each have [0.166667,2.927083], with 2 positive, 21 zero, and 1 unresolved. Twenty-three of the 24 have exact reference and chosen values. The manuscript reports this non-probe scope and the actual 88/88 escapes, never the counterfactual 98/102 total. Endpoint cluster confidence intervals are distinct supplementary statistics in the analysis JSON.

The necessity/repair figure now labels panel (b) "Original rollout bank." Its zero non-probe obstruction conclusion is scoped to that original acquired evidence, not every later offline audit or all possible temporal/C3 workloads.

## Assistant proposal provenance and operational logs

The paper needs only one concise provenance sentence. The internal model identifier is now verified as `gpt-6.1-sol` with ultra reasoning. It must not present this as an external API run, claim API calls, infer unavailable token counts, or equate proposal counts with matched compute.

Verified current source files:

- `experiments/discovery/v03/guided_generation.md`: one independent Codex internal assistant turn, 24 proposals, zero automated provider API calls. Training inputs only: shared context and concrete guided witnesses. Candidate expressions/rules are assistant authored; helper only serializes trees. All 24 type-check; 24 unique names; at most three extra features, nine AST nodes, depth six. After authorship, 1,536 runtime/feasibility checks ran on the supplied 32 training pairs; all feasible, no score failure. No validation/test comparison influenced revisions.
- `experiments/discovery/v03/free_generation.md`: one independent assistant turn, 24 proposals, zero automated API calls. Shared context and 18 certified specifications; no guided witnesses or other-arm files read. No schedule evaluation or metric search ran. Construction checks passed; at most two extra features, nine AST nodes, depth six. Saved context hash `5ed27fcc1b5e5b7bb32b9163fd36e2fce2a3805c1db9daa976ee8b1db71bf1b0`; response hash `b642fb86bb3cb53616c41e38f5fb18791b2887274728dd6470e0fe786783b79d`.
- `experiments/discovery/v03/rule_generation.md` (verified after the first draft): one independent Codex internal assistant turn, 24 rule-only proposals, zero external API calls, unavailable model identifier/tokens. Reads only shared training context and `graph_features.py`; 32 training pairs/18 certified specifications; no guided witnesses, other arm files, paper/method, validation/test, scores, or schedules inspected. All proposals frozen before construction; each has an empty feature list. All 24 construct in one post-freeze pass; names and rules unique; 256-node scorer AST limit. No schedule executed, quality-based replacement, or formula revision after validation.

These execution checks differ across arms. They check validity rather than matched search. Deterministic enumeration uses no assistant request; it is a candidate-budget comparator, not a request- or token-matched LLM arm. A single batch per arm gives no model-level replication or across-run synthesis variance.

## Result integration requirements

LaTeX result slots are comments only; they do not display placeholders in the PDF. Root analysis will provide the verified final summaries and plots. No v0.2 mean or v0.3 development mean is described as primary held-out evidence.

1. Incidence: attempted queries and reasons by family and size; reversal/preservation/unknown; certificate yields; actual exact self-loop and cycle incidence outside constructed diagnostics.
2. Bound comparison: paired yield/width/work/time for ranked clique, uniform clique, ranked weight-sum. Unknown ties, interval overlap, exhausted budget, and alignment failures need separate counts.
3. Relevance: saved-boundary reachability, escapes, chosen-member consistency, and any separately computed conditional-regret intervals. Pair consistency alone cannot explain schedule gains.
4. Proposal study: all 8/16/24 prefix curves; candidate validity/rejection counts; final programs; exact guided repair scope; eligibility; separate reversal/preservation violations; within-bank gate controls. No eligible candidate must be shown explicitly.
5. Held-out schedules: freeze receipt/hash before test access; test completion; pairwise quality with per-regime and C3 breakdown; primary denominator coverage/gap/status; paired bootstrap confidence intervals keeping the two sides together. Temporal seeds are shared across regimes at a given split/size/index, so an aggregate temporal interval should preferably resample these seed blocks across all regimes. Per-regime pair bootstrap is appropriate. If using independent pair bootstrap across regimes, explicitly disclose the assumption. Record worst losses, ties, feasibility, and source-verifier results. Synthetic and C3 results must remain separate from diagnostics.
6. Stress: exact completed contexts, size/density coverage, source block overlap audit, quality/reference coverage and runtime. A stress development run is not the main held-out test.
7. Runtime: paired timing/work ratios across 150 contexts, repeated timing aggregation method, size/density strata, initialization/update/query shares, CPU/process concurrency limitations. Deployment must include every executed graph operation; discovery cost remains separate.

## Bounded evaluation amendment

Source: `docs/EXECUTION_BUDGET_AMENDMENT_V03.md`, read before final result integration. Candidate banks, selected programs, training evidence, and test contacts remain unchanged. No test quality outcome is used to select or revise programs. The original unbounded no-cost control `g18` exposed a missing inference limit: after fourteen minutes across eight workers, only 160/840 primary contexts had completed. Original records remain preserved as an execution-cost diagnostic.

The final primary run is `holdout_bounded_002`; bounded transfer will be `transfer_bounded_002`. Both use the same byte-frozen `frozen_joint_001` programs. Each constructive program receives five process-CPU seconds; timeout yields `value=None` and no returned schedule. There is no repair, fallback program, or partial schedule substitution. Report completed-schedule quality, timeout/completion rate, and CPU/wall cost jointly. The independent local-search comparator has its own two-second budget and HiGHS its ten-second budget; no inference-compute matching claim is made. Offline evidence audits of generated arms and baselines are separate from deployment and do not repeatedly rerun the expensive no-cost control.

The paper states the budget and completion interpretation concisely; timestamps, abandoned execution history, and delivery details stay here or in the dedicated amendment.

Latest diagnosed execution update: bounded002 primary failed with 207/840 unique saved rows (last progress checkpoint 200) because local-search initialization compared completed floating baseline rewards with `None` timeout values in `max`, causing a `TypeError`. The earlier signal-stall interpretation was unproven. The archived amendment retains the older explanation; `docs/EXECUTION_BUDGET_AMENDMENT_V03.md` now explicitly corrects it. Transfer002 completed 216/216. The final unbounded001 archive contains 182/840 unique rows (checkpoint 180; 160 was the earlier fourteen-minute progress snapshot). Both partial primary archives contain balanced temporal contexts only. Cooperative003 evaluates the same 840/216 contexts and frozen programs, initializes local search from completed classical baselines only, and retains no-coverage if none completed. Its five-process-CPU-second target may overshoot inside a primitive; it must not be described as a hard wall-time or primitive-preemption limit. Final execution wording waits for the completed receipt. No partial primary mean is promoted into the paper. The original bank's reached-state negative relevance and zero non-probe obstruction remain valid. The separately archived alias census has 200 unresolved queries and no certified natural alias; unresolved results do not prove absence of aliases.

## Wording to reject

- “All specifications satisfied” with tau .75 unless the measured selected program achieves 100%.
- “Exact approximation ratio” or “formal certificate” for HiGHS floating upper references.
- “Guided generation wins” as a general model-level claim from only one assistant batch per arm. The principal guided/free joint arms now share selection gates; rule-only has a separate consistency scope.
- “Optimal representation” beyond the specific finite catalogue, fixed evidence, and additive work surrogate.
- “Natural prevalence” from purpose-built exact-alias probes.
- “Constant-time updates” or “runtime speedup” inferred only from an operation counter.
- “Full C3 scheduling” for time-ordered source subproblems.
- “Compute matched” from 24 proposals and one generation request when tokens are unavailable and smoke-check counts differ.

## Remaining editorial work

Replace comment slots with grounded result prose and approved figure/table inputs; reduce protocol detail where needed to keep final length. Retain the concise provenance sentence and put delivery timestamps/hashes in this document. Then check LaTeX references, table fit, figure captions, word count, and the compiled final manuscript. Parent owns compilation and main-file integration.

First-draft static verification: balanced LaTeX braces and environments and unique section/table labels. Final compression supersedes the original ~1,587-word draft and the later ~1,034-word version. The current estimate is 818 visible words including both active quantitative figures' captions and tables. Active assets are `evidence_discovery_v03.pdf` (full width, label `fig:evidence-discovery`) and `runtime_v03.pdf` (column width, label `fig:runtime`); no duplicate is added to the parent main file by this author. Remaining final-budget, held-out/source-audit, and outcome-figure slots are comments only. This static check does not confirm compiled page layout.

## v04 manuscript replacement and claim map

The preceding v03 draft/operation descriptions are historical. The current
experiment section is replaced by a compact v04 confirmation account:749
words under `texcount -brief -sum`, including two tables, public/SNAP coverage
and retrospective reached-state evidence. The expanded884-word version is
preserved in `docs/archives/experiments_expanded_v04.tex`.
It contains no status/placeholder prose. The obsolete v03 evidence/runtime
floats are removed; root owns final figures/layout, using
`fig:quality-cost-fresh`, `fig:quality-cost-public` and `fig:heap-execution`.
The full manuscript is a multi-file project; parent owns its compiler checks.

| Current scientific claim | Supporting audit | Boundary retained in manuscript |
| --- | --- | --- |
| 93 programmes on66 TRAIN contexts,12 new guided proposals | `training_audit.json` | One session;24-proposal controls are unequal and not compute/model-matched |
| Selected active-neighbor clique-envelope ratio | Frozen TRAIN bytes and all advanced/heap programme hashes | Main and primary-only selection identical; no demonstrated secondary selection benefit |
| Necessity evidence and catalogue repair | `evidence_audit.json`, quotient replay in TRAIN audit | Original64 strict self-loops are probe-derived;19 non-probe specs acyclic;200 broader aliases unknown |
| Pure cancellation narrows199/396 nested intervals | `pure_cancellation_training.json` | Same unmatched bounds, median86.75→36; strict33→33;10→33 strategy contrast is not isolated cancellation |
| Fresh456 population and exact source nonreuse | `fresh_input_audit.json`, `advanced_fresh_audit.json` | Shared seed/regime/pair clusters; one C3 physical source; no prior-instance reuse in supplied inventory |
| Fresh competitive means/CIs and completion | Independent streaming advanced audit | Strongest saved feasible witness is descriptive, not optimum; native solvers remain stronger; failed continuation211/456 retained |
| Exact formal clique upper versus numerical HiGHS | Independent clique edge/partition/Fraction arithmetic | Only2 fresh contexts have independently verified lower=clique upper; numerical status0 is not a formal certificate |
| Original C3 source feasibility |24 rebuilt test graphs,1,008 original-verifier checks | Every completed schedule passes encoded source predicates, without broader physical-model claim |
| Heap exact execution equivalence and costs | `heap_extension_audit.json` plus independent proof | All2,736 fresh pairs match; degree dense overhead retained; no sparse pair assessable; unchanged frozen policy |
| Public96 and separate SNAP8 | Public-input parser audit and pinned input hashes | Unit/hash weights share topology; hash weights are declared extensions; separate populations |
| Public short primary54/96 and subset18/21 | `advanced_public_audit.json`,355,759 checks | Native-only30-second budget change; constructive target unchanged;42/3 null failures retained |
| SNAP original primary0/8 versus native24/24 seed completions | `advanced_sparse_audit.json`,65,199 checks | Separate extension; WeightedBR21/24; no primary quality or sparse interface parity credit |
| Primary555 sampled reached test-state finite-pool regrets | `frozen_action_audit.json`,330,923 checks |18 positive/191 zero/346 unresolved; counterfactuals excluded; large upper endpoints retain computational-receipt scope |

The separate30-second sparse execution extension is documented in
`sparse_heap_30s_audit.json` and `EVIDENCE_AUDIT_V04.md`. It retains zero
assessable fullscan/heap pairs and changes no original confirmation result.
No additional main-paper float or timing claim is added. Native citations use
the parent's active `references_v03.bib` keys.

All earlier v03 negative results remain preserved in `EVIDENCE_AUDIT_V03.md`
and `final_population_audit.json`, including failure-zero primary/transfer
guided-minus-rule differences−10.8725/−8.9915 percentage points. Partial001/002
harnesses remain partial and do not replace complete003 evidence. The later
v04 bank is explicitly informed by prior qualitative failures, with new TRAIN
selection and independently audited fresh inputs before confirmation. It is not
presented as blinded to earlier observations.
