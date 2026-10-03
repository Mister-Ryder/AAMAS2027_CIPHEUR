# v04 method extension: actual actions and component-cancelled evidence

This document records a new development method before any v04 TRAIN outcome was read by its author. It does not report a test result or promise an improvement. The v03 held-out failures were already known qualitatively when this design began; this is an explicitly motivated new study, not a claim of blinded v03 selection.

## Concrete change

The representation repair master remains the finite-catalogue exact minimum-cost cycle-separation method. Its objective is informational consistency on sound strict requirements, not whole-schedule optimality. The new engine addresses a separate gap: a programme can satisfy those requirements while selecting poor actions elsewhere. It therefore measures complete TRAIN schedules and acquires bounded evidence at boundaries actually reached by the candidate bank. Candidates keep the existing `FeatureRuleProgram` AST and typed features; deployment executes the same source semantics through `schedule_compiled(..., score_slice=True)`.

The extension has three mechanisms: cancel mathematically identical unsolved continuation components before bounding a preference difference; acquire comparisons among actual argmax actions at recorded rollout boundaries; and select programmes by declared schedule quality/cost, using actual-action regret only within a prespecified utility band. The smallest separating interface remains an ablation, not a restriction of the principal guided bank.

## Exact component cancellation

Let a valid boundary be fixed commitments F and excluded contacts X, with residual feasible actions R. For an action d in R, write R_d = R minus ({d} union N_R(d)). The conflict graph is additive across its connected components, so its full conditional optimum is

`V(d) = w(F) + w(d) + sum_{C in components(R_d)} alpha_w(G[C])`.

For actions a,b, the engine identifies components with exactly the same vertex set in both R_a and R_b **in the same original graph**. Such a component has identical weights and induced edges, hence exactly the same possibly unknown optimum on the two sides. Its term cancels. With A and B the unmatched component collections,

`V(a)-V(b) = w(a)-w(b) + sum_{C in A} alpha_w(G[C]) - sum_{C in B} alpha_w(G[C])`.

If `[L_C,U_C]` encloses each unmatched component optimum, sound difference bounds are

`L_ab = w(a)-w(b) + sum_A L_C - sum_B U_C`,

`U_ab = w(a)-w(b) + sum_A U_C - sum_B L_C`.

This argument does not require solving cancelled components, nor that the original graph was disconnected. Conditioning can disconnect a previously connected graph. It requires the same feasible F,X and the same graph for the two forced actions; cancellation across intervention graphs is not performed. It also requires additive independent-set utility. Cross-component constraints absent from the graph would invalidate the decomposition and must be handled in the graph/model verifier.

All certificate arithmetic uses exact `Fraction` values of the supplied finite float weights. Each lower bound has a feasible independent-set witness; upper bounds use the existing sound weighted clique-cover branch-and-bound oracle. Floats exported in logs round outward. A strict requirement is emitted only when L_ab exceeds epsilon or U_ab is below minus epsilon. Budget exhaustion preserves an interval and an explicit unknown; it never invents preservation. Identical component vertex sets key the cache. Large unmatched components receive a zero-search sound envelope. The call-limit fallback is explicitly `[0,sum_C w]`, a sound trivial interval, and is not logged as a completed solver call.

The new enclosure is not claimed to dominate every implementation-specific old full enclosure: clique-cover heuristics may produce different covers when the graph is split. The engine stores a matched zero-search comparison against the old full-residual enclosure for the first three deterministically ordered action pairs at each audited boundary. These rows isolate cancellation from additional search and use identical actions and F,X.

## Actual rollout provenance and regret scope

Each completed programme runs a full constructive schedule. Its initial boundary and at most two subsequent boundaries are recorded with programme ID, rollout step, graph digest and fixed-set identity. The shared query plan always includes the initial boundary, then prioritises the boundary reached by the most bank programmes, with a deterministic hash tie-break; the maximum is two audited states per context. All unselected boundary counts remain in the output.

At each audited state the engine replays the same F,X and evaluates the actual argmax of every programme through the sliced compiler. It builds a finite pool of their distinct selected actions, then compares every unordered pool pair in deterministic ID order under a shared state budget. A programme's regret interval bounds `max_{u in pool} V(u)-V(chosen)`. Its **upper endpoint bounds only that finite-pool regret**, not regret against every feasible contact or global schedule loss. Lower endpoints can still establish a loss relative to a particular alternative. Unresolved comparisons remain counted.

A programme contributes to the selection regret statistic only when this boundary occurs in its recorded rollout. Evaluations at another programme's boundary are marked counterfactual and retained for auditing, but excluded from its selection regret. No claim is made that two sampled boundaries capture a complete long-horizon decision process. The source logs preserve replayable boundaries, compared actions, cancellation partitions, component intervals, node/call budgets, unknown counts and sampled/unsampled denominators.

## Fixed proposal bank and deployment features

The bank contains 93 programmes: 12 new guided proposals, all 24 prior free proposals, all 24 prior rule-only proposals, all 24 enumerated proposals, five baselines, and four prior guided controls g03/g05/g12/g18. The 12 proposals were authored in one continuing assistant agent session with root feedback and revisions **before any v04 TRAIN result**. Trusted root turn metadata identifies the served model as `gpt-6.1-sol`; there were zero external API calls. Token use is unavailable, not zero. This is an authoring session count, not an LLM-server call count or replicated generation study. Prompts and follow-up design requests are preserved in this task history; the JSON receipt records the final scope. Generation compute and candidate counts are not matched to the prior 24-proposal arms.

The six typed feature expressions used by the guided catalogue are: independent greedy weight and clique-cover weight of the root's current conflicting neighbors; current-neighbor edge count and pair minimum-weight sum; and greedy weight and clique-cover weight of the continuation left after forcing the root. Greedy packing is a feasible value and clique cover is an upper-bound construction mathematically, but deployed typed features are ordinary rounded scalar summaries. They are **heuristic scorer inputs**, not exported exact preference certificates. The independent exact offline oracle is responsible for certified labels.

The proposal forms are: feasible-neighbor ratio (g12); cover ratio; midpoint ratio; normalized width discount; feasible-neighbor loss; cover loss; width-normalized midpoint ratio; a feasible-packing/pair hybrid; feasible-packing/density hybrid; density-adjusted gap ratio; and two retained-continuation proposals guarded by remaining_count <=64 or <=128. The guards switch solely on the state-wide remaining count, so all actions in a state use one score branch and scale. Their thresholds were fixed from the declared 32/64/128 development compute regimes, not optimized using prior test rewards. Above the guard each uses the earlier density/pressure form; below it uses `weight + (residual_cover+residual_greedy)/2`. Neither a midpoint nor a neighbor ratio guarantees a correct global ranking.

Root's demand-driven compiler evaluates only features referenced by the taken scoring branch; maintenance of the static feature-dependency superset remains charged. All 93 programmes use that backend uniformly. A default full interface remains available for exact source/trace parity checks; it preserves v03 snapshots when score_slice is false.

## Declared TRAIN objective and information repair

The development configuration contains 24 deterministic non-probe TRAIN intervention pairs selected from the completed development archive (32/64/128 contacts; quota two per family/size/changed-parameter stratum) plus nine outcome-independent fresh dense-long TRAIN pairs (three resource regimes times three sizes). This gives 33 pairs, 66 graph contexts and four workers. Validation and test records/results are not used for programme selection. The engine rejects test/transfer/outcome containers as its training input. Prior diagnostic training certificates may supply the inherited information gate; they are separately labelled and checked against the supplied TRAIN graph digest inventory and their strict exact bound inequalities.

For each context, quality is reward divided by the best observed completed schedule in this bank. This is a **feasible empirical comparison value**, not a formal optimum or solver upper bound. Failure quality is zero. Feature work is divided by the degree baseline's work; timeout relative work is the declared value 100. Primary utility is equal-family mean quality minus 0.002 times (equal-family mean relative work minus one). This charges bank programmes uniformly under the sliced backend, while retaining measured CPU time as a separate field.

Within each arm, the engine first finds the best primary utility. Programmes within 0.002 of it are ordered by finite-pool actual-reached regret upper, then lower, unknown count, primary utility and programme index. This is a **declared near-tie band**, not strict lexicographic maximization of primary utility. Unknown regret is not a hard eligibility threshold. Missing regret coverage is recorded and ordered last, not treated as zero. The primary-only guided winner is saved as an ablation.

Sound strict TRAIN differences plus separately retained sound prior TRAIN certificates produce an occurrence quotient. The base interface is the current nine-field `FeatureRuleProgram` base, not a legacy feature-sum definition. The six-expression catalogue is passed to the existing master, which rechecks the full quotient after each proposed interface. Each bank programme's whole-feature quotient is audited. Guided/free/enumerated synthesis arms receive the declared consistency gate; rule-only and baseline controls remain comparators with different eligibility scope. This asymmetry must be stated when reporting comparisons. Acyclic consistency guarantees a fitting arbitrary score on the finite quotient, not realizability by every AST or good unseen schedules.

Repair costs are additive standalone typed-feature work on the observed endpoints, a declared proxy rather than measured joint DAG runtime. Shared evaluation and branch laziness can change deployment cost, so the principal objective uses the actual compiled programme meter. The master is limited to six selected features, 32 separation rounds and 100,000 visited master subsets. A completed exact master followed by a full-quotient acyclicity check establishes the finite-catalogue additive optimum; exhaustion retains `optimal=false` and its reason and supplies no optimality claim.

A separate quotient adds `satellite_trans_time` presence/value for configuration auditing. That field is not an explicit field in the deployed nine-base interface. An alias that disappears upon this audit cannot be advertised as unavoidable structural information loss under a complete configuration input.

## Bounded implementation and commands

The constructive inference cap is five process CPU seconds with cooperative meter checks every 128 meter writes. It is not a hard operating-system termination deadline; overshoot and observed CPU time are reported. A timed-out programme returns no schedule and receives no fallback. The oracle budget per audited state is 10,000 expanded nodes and 128 calls; each unmatched component gets at most 64 nodes and components larger than 128 vertices receive zero search. State acquisition has at most two boundaries and at most two actual rollout steps. These are prespecified resource limits, not outcome filters.

Run the development engine from the repository root:

```text
python -m cipheur.relevance_synthesis_v04 --mode train --data runs/development_scale_001/data.json --discovery experiments/discovery/v03 --config configs/relevance_v04_train.json --out runs/relevance_train_v04_001 --workers 4
```

The engine writes the input graphs, exact bank, generation/source/config receipts, flushed per-context evidence, information repair, assessments, selected programmes, and a nonempty TRAIN freeze with `test_accessed=false` before fresh test evaluation. A failure leaves partial outputs and must not be presented as a completed freeze.

## Negative natural-alias inspection and verification

The immutable alias_census_001 run left all 200 queried aliases unresolved at its declared 2,000-node budget. Its nine typed-distinguished candidate rows are three independent C3 action pairs repeated at initial and two actual boundaries. Inspecting only those input partitions finds **no identical component to cancel** in any row. The TRAIN 256-contact case has unmatched component sizes 245/245, 242/242 and 239/239; the validation 256 case has 247/247, 245/245 and 243/243; the validation 1024 case has 1001/1001, 988/988 and 975/975. Validation inspection was input-only incidence diagnosis, not a selection label or validation oracle query. These cases remain unknown; cancellation alone does not rescue them.

The focused tests independently enumerate conditional MWIS on 32 small random graphs with binary-float weights and budgets including zero and call exhaustion; check exact/outward difference enclosure and feasible lower witnesses; exhibit cancellation of an unknown C5 despite an originally connected graph; distinguish pool regret from all-action regret; replay actual fixed boundaries; check counterfactual exclusion and unknown semantics; verify all 12 full/sliced traces; and check fresh split/source-ID safeguards. These checks support implementation correctness but do not substitute for the cancellation proof, an empirical gain or a fresh frozen hold-out study.

The extension's current limitations are finite candidate grammar/catalogue, conditional and sampled regret, model-complete conflict graphs, limited oracle strength on large connected residuals, known prior-study motivation, one assistant authoring session, non-matched generation budgets, and heuristic deployment score forms. Novelty claims should name the combination of sound cancellation, actual-action acquisition and schedule-aware finite synthesis, without claiming a new general MWIS bound, a globally optimal heuristic or established superiority to public MWIS systems.
