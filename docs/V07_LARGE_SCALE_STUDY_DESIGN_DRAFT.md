# V07 large-scale scene and study design — draft, not an execution release

**Status: NOT YET PREREGISTERED; no frozen execution protocol exists and no new benchmark, certificate acquisition, model call or TEST execution has started.** The user has broadly authorized experiments; this draft adds no user-approval requirement. Root will consolidate the scene and diagnostic protocol before execution. It does not modify V06 sources, selections, results or analyses. No V06 TEST outcome or private credential was read to choose it.

The current evidence establishes a scoped information-repair mechanism. It does not establish that stronger feature representability necessarily improves complete scheduling quality. In particular, the identical V06 TRAIN qualities occur **before** distribution shift; they cannot primarily be explained by mismatched TEST data. Bigger or weighted TRAIN instances do not automatically repair that causal gap. V07 must first diagnose the internal TRAIN chain, and only then justify a costly independent large-scale evaluation.

## 1. Scene contract before a dataset

The target is repeated single-capacity satellite/ground-station competition with configuration changes in ground switching gap. A transferable decision relationship requires recurrent resource-competition structure, not simply more random vertices. Freeze the following scene contract before selecting seeds, obtaining certificates or seeing scheduler outcomes:

| Contract | Required interpretation and implementation |
|---|---|
| Task opportunities | Contacts are alternative/recurrent opportunities for mission task classes, competing through shared satellite and ground resources. New TEST opportunities have new IDs, placements and source seeds, while retaining the same specified task/resource grammar. |
| Recurring structure | Repeated overlapping windows and short/long occupancy patterns recur through a common resource/calendar model. Preserve naturally generated competing chains and neighborhoods; do not splice in a known strict-reversal toy, duplicate a favorable graph or filter instances by alias/quality outcomes. |
| Priorities and durations | Finite task-priority classes and duration/service classes must come from the intended scheduling background, or be clearly labeled explicit synthetic scenario assumptions. Quantization must precede graph generation and labels. It must not be tuned to force exact aliases. The current background duration and reward are measured in seconds; the existing quarter-valued V06 random weights/durations are an unsupported placeholder, not a fitted operational distribution or grounds for changing reward units. |
| Resources | Use the same resource families on TRAIN and TEST: balanced (8 satellites, 6 ground stations), ground-scarce (12, 3), satellite-scarce (3, 12). Resource assignments and opportunity-window grammar share one generator and version. |
| Only intervention | Within a source, freeze contacts, priority weights, durations, times, resource IDs and capacities. Rebuild conflicts for different `station_gap` values only; satellite gap remains zero and both capacities remain one. |
| Transfer scope | Primary transfer is new source seeds and new gap values **within the same frozen scenario grammar and sizes**. Recurrent structural roles transfer; exact contacts/instance outcomes do not. Natural mission prevalence and arbitrary-family transfer are outside scope without external evidence. |

**Unresolved scene decision:** the mission-to-priority/duration-class mapping and recurring opportunity/calendar rule need background calibration before the scene protocol is frozen. Do not silently replace this step with the existing independent-uniform random generator. Any quarter-weight prototype is an unsupported synthetic placeholder until reconciled with the background's seconds-based reward/duration contract. No particular class values are claimed here to be grounded observations.

A repeated scene can still lack exact full-base-nine aliases. Those vectors include weight, duration, degree, conflict-weight sum/max, compatible-weight sum, gap settings and remaining count. Merely discretizing weights does not guarantee equality of all these entries or contradictory preferences. Report motif recurrence, exact alias incidence and structural obstruction separately. An absent trigger is a valid result, not permission to alter seeds/classes or manufacture successful labels.

## 2. Smallest meaningful large-scale frame

Conditional on the approved scene contract, use this minimum rather than small TRAIN followed only by large TEST:

| Dimension | TRAIN | Independent TEST |
|---|---|---|
| Complete graph sizes | 512 and 1,024 contacts | The same 512 and 1,024 contacts |
| Resource families | The three families above | The identical families |
| Occupancy profiles | Two fixed background-defined short/long or standard/high-occupancy profiles | Identical profile definitions and class distributions |
| Source seeds per size × resource × profile | 2 | 4 new seeds |
| Independent source graphs | 24 | 48 |
| Station gaps | `[0, 1, 3]` | `[0.5, 2, 6]` |
| Full configuration states | 72 | 144 |
| Source namespace | New V07 TRAIN namespace | Separate new V07 TEST namespace |

Thus both distributions are weighted, duration-aware and genuinely large. TEST gap 6 includes declared extrapolation beyond TRAIN's largest gap; report interpolation and extrapolation separately. These are proposed gap values, subject to units/background confirmation before freeze. A 2,048-contact extension is an additional preregistered scale stratum, not a substitute for matched-size evidence or a post-outcome favorable extension.

Do not use V06 TEST graphs as new TRAIN, as motif exemplars selected by success, or as scene parameter pilots. Use one new outcome-free generator for both V07 splits, with split-specific seed namespaces and a common parameter object. Record contacts/graph/source hashes, realized densities and component sizes; retain every declared cell even if dense, trivial, unsupported or unfavorable. Statistical units are generated sources; gaps, query endpoints and repeated opportunities within a source are dependent.

## 3. TRAIN internal causal-link barrier

Before expensive TEST release, answer the following from TRAIN execution/evidence. These are diagnostics with preserved denominators, not a search for positive instances or a promise that larger data produce gains.

1. **Trigger and boundary:** Do recurring competition motifs actually yield strict certified preferences, exact base-nine aliases or demanded full-quotient cycles? Are requests attached to actual scheduler decision boundaries? Report invalid replay, no challenger, unknown interval and query-shortfall rates. If there are no certified strict aliases/obstructions, do not claim that the information-repair mechanism was activated. Preserve the complete study and explain the missing trigger.
2. **Representation versus scoring:** For every authored program, evaluate the full demanded feature quotient and actual scalar margins separately. An acyclic quotient means some order is representable on the retained inventory; it does not imply that the authored scalar fits it. Unused declared features cannot conceal a demanded-input obstruction. Retain all strict constraints, not only the prompt examples.
3. **Ranking versus action path:** Log the actual selected action, feasible residual, fixed/excluded sets and score inputs. Check whether changing the frozen ranking head changes the action/search path under the same initializer and budget. A score difference on an unvisited boundary is not guidance efficacy. Record ties, identical traces, unreachable certified boundaries and boundary escapes. Ground the budget in the real scheduling setting; do not deliberately disable the common classical solver or weaken its exact search solely to create a ranking advantage.
4. **Action path versus incumbent:** Record when changed paths change feasible incumbent reward, and when common initialization or completed classical search erases their difference. Report component/patch completion, exact-bound closures where legitimately available, budget stops, search-node/work/time usage and quality coverage. Vertex count alone is not a hardness measure.
5. **Claim barrier:** If TRAIN quality remains flat, V07 may support information diagnosis/representation/scalar repair, but cannot declare an additional quality contribution. Do not attribute this to TEST shift or release expensive TEST merely to hunt for a positive ordering. Root must decide whether to proceed with a clearly scoped information-transfer study, or close the performance claim and document the broken link.

Optional deterministic coefficient/scalar fitting belongs inside a joint feature-rule repair pipeline, not as a hidden authored-output replacement. It may be considered **after** locating a representability-to-scalar-fit failure. Freeze its hypothesis class, coefficient bounds, objective, work budget and stopping before running it; use only certified TRAIN inequalities. Apply the same fitting controller to appropriate fixed-feature and learned-feature controls. Preserve original LLM proposals and fitted deployments as distinct artifacts, charging the controller cost. A finite quotient DAG need not be realizable by a bounded linear/conditional DSL. No solver-generated scalar is counted as a genuine new LLM proposal.

## 4. Exact decision-boundary contract

### Primary: actual committed inclusion decisions

Use the existing `CompiledEvaluator` semantics: at current feasible `F`, explicit `X` and `A = graph.available(F, X)`, score active actions, select score-descending/ID-tie-breaking argmax, commit that action, then delete it and its neighbors. The frozen rule must directly determine this action path. Full-residual evidence is

`V(a | F, X) - V(b | F, X)`

with forced inclusion and all remaining feasible completion opportunities. Source intervention sides replay the **same** `F/X`; an infeasible counterfactual replay remains an explicit failed request. It is not repaired by changing `F`, intersecting two trajectories or shrinking the global residual to a favorable neighborhood.

This is a diagnostic path using the current compiled library, not a proposal to remove classical search and then claim superiority. Actual deployment semantics and scheduling budgets must determine whether commitment is the relevant decision. If the application uses complete exact patch search, retain it and report its ranking-insensitive quality honestly. If commitment is relevant, a new V07 anytime wrapper can meter that loop, retain the last feasible prefix on a real application cap, and preserve exact scoring/deletion/tie semantics. `schedule_compiled` currently runs to completion and provides no outer deadline/prefix return on interruption. Freeze any wrapper before authoring outcomes, with the same wrapper for learned, fixed-feature and Degree controls.

### Secondary: common-backbone repair

Keep the existing `repair_v06` as a separately scoped shared component. Its default branch scope initializes and targets with Degree, while programs affect bounded patch branch priorities; complete branch-and-bound may return the same optimum irrespective of ranking. Global forced-inclusion fit is therefore **not** a certificate of patch ranking or branch-expansion efficiency.

For a future genuinely aligned patch label, freeze the exact patch and outside commitments: `F = incumbent outside patch`, `X = every unavailable outside opportunity`, and active actions from the actual legal patch residual. Bounds then describe that outside-fixed conditional completion problem, not unrestricted global scheduling. If the policy merely chooses branch order and both include/exclude children remain searched, forced-inclusion preferences still do not certify compute efficiency. Such labels require an explicit action contract; do not relabel global certificates as patch certificates. The minimum V07 should report the primary commitment mechanism and secondary repair outcomes separately rather than silently changing the frozen repair kernel to obtain favorable effects.

## 5. Bounded evidence; no all-graph exact pre-solving

Reuse `CancelledCompletionOracle` on the exact graph/F/X. For actions a/b, it cancels identical induced conditioned components by exact vertex-set identity, then sums sound lower/upper envelopes only on unmatched components. This encloses the **full** conditional difference. Common unknown optima cancel without solving them; unmatched large components remain bounded, not assumed exact.

Proposed initial TRAIN request budget: **576 paired attempts** = 24 sources × two fixed gap contrasts `(0,1)` and `(1,3)` × two prescribed anchor boundaries × six requested competing action pairs. This is an attempted-evidence budget, not a promise of 576 strict relations or reversals. Use boundary steps 0 and 8 from a fixed pre-evidence reference rollout, anchored on a specified side, with legal counterfactual replay. Short trajectories, invalid replay, missing competitors and absent aliases remain original positions/shortfalls. If root opts for adaptive TRAIN acquisition later, it needs a separately frozen controller and common arm-visibility contract; no such adaptation is implicit here.

Query construction may use scores, resource roles and exact feature equality **before** labels. A fixed per-boundary six-position mix can reserve three exact-base-nine-alias competitors and three ranked competing neighbors; retain unavailable positions rather than substituting favorable certified requests. Sort/sample deterministically from the frozen query namespace. Freeze the original request table before its first certificate call.

Draft per endpoint/boundary oracle limits: `nodes_per_component=256`, `max_search_component=64`, `max_nodes=16384`, `max_calls=128`, with component caching within that exact graph/F/X and a separate 30-second task guard. Larger unmatched components get zero-node feasible-lower/verified-clique-upper envelopes; call exhaustion keeps sound trivial bounds. A wall guard must preserve completed records and mark unfinished queries unknown/error explicitly. These are suggested caps requiring root preregistration, not empirically calibrated settings.

Strict labels require a positive separated interval (or negative separated interval for the opposite action); exact zero closure is a tie; overlapping intervals remain **unknown/abstain**. No greedy/native winner, best incumbent, approximate objective or confidence heuristic becomes a certified label. Never intersect bounds from different graphs, actions or F/X. Component cancellation is within one conditioned objective, not across changed-gap graphs merely sharing names. Record bound witnesses, unmatched/canceled component sizes, all calls/nodes/CPU/wall, timeout and trivial-bound reasons. The existing oracle caps calls/nodes but not envelope overhead, so the outer task guard and cost receipts are necessary for scale.

Evidence sufficiency is a preregistered TRAIN decision, not an outcome filter. Report strict/alias/cycle coverage by source family and size with all attempted denominators. If there is no mechanism trigger, no valid action-boundary coverage or negligible certified evidence, do not force information-repair authoring or create labels. Close that mechanism claim for this declared frame or proceed only under an explicitly narrower information study; keep all cells and failed attempts. No TEST opportunity is examined to fix TRAIN insufficiency.

## 6. Genuine offline synthesis and frozen deployment

A minimum authoring budget can use two fixed independent author blocks with eight original candidate positions each for W/R/O and an adapted EoH pipeline: 16 candidates per condition, 64 genuine single-candidate offline calls total. Four blocks would strengthen replication but must be chosen before calls. Do not claim model-population evidence from the minimum. Match typed feature/rule capacity and maximum candidate positions; measure actual tokens/call wall/controller work rather than asserting matched compute.

All arms share one predeclared safe typed start (for example a fixed Degree/prior rule, not a V06 TEST-selected winner). W receives certified TRAIN relations and concrete demanded-feature equality joins; R receives the same relation frontier without joins; O/EoH authors receive only TRAIN complete-schedule quality, work and errors. EoH retains its fixed exploration/mutation sequence, quality-only rounded-fitness population and earlier-member tie retention; an unchanged warm seed remains explicit, not a newly authored improvement. Unknowns are shown as unavailable evidence, not implied losses. Prompt examples are bounded, while controller checks use the full retained certified TRAIN inventory.

Fitness uses every declared large TRAIN state under the frozen action kernel and cost caps. Selection, fit/gate checks, failures and missing requested identities are retained; no invented author fallback, extra retries to obtain a winner or TEST-based scalar adjustment. Separate gate/scalar selections from quality-only pipeline selections; they answer different questions. Freeze source closure, scene/generator, TRAIN evidence/queries, all raw call metadata/proposals, deployable ASTs, selection/controller rules and runtime before any TEST certificate/performance call. Runtime workers receive programs and graphs only, never oracle objects, cached labels or synthesis services.

## 7. Comparators and fair cost scope

Include genuine published native CHILS, CHILS-ILS and Struction through the existing native wrappers, not heuristic-name stand-ins; retain prescribed stochastic seeds and exact numeric conversion. Include Degree, a fixed-base-feature scalar controller and the same typed EoH comparator. Unsupported encodings/failures stay null with assigned denominators. Additional native methods can be declared before release, not after seeing rankings.

Report three distinct tracks rather than pooling away action semantics:

1. **Committed construction:** learned/fixed/Degree rankings share the exact same compiled construction and feasibility checks. Primary mechanism evidence aligns here; include initialization, DAG compilation, feature/scoring/deletion work and actual complete-policy time. Native solvers supply whole-schedule comparison results at declared nominal targets, with actual wrapper overhead and deadline limitations exposed.
2. **Cold common repair:** the unchanged common Degree initializer plus bounded repair, with all program priorities using the same patch geometry and caps. This probes marginal search guidance, not global inclusion certification.
3. **Warm common repair:** one CHILS `T/2` initializer per graph/target is shared byte-identically across arms, then each policy gets `T/2` repair. Every standalone pipeline is charged the same measured initializer cost plus its own completion/feature/repair cost, even if the server computes the shared initializer once. Failed initialization makes all associated warm identities null, without a hidden Degree/best-of-bank fallback.

Candidate primary nominal targets may be `[1,5]` seconds, frozen on TRAIN before release. Native internal targets and cooperative Python targets are not identical end-to-end hard deadlines. Retain wrapper/self/child CPU separately, actual wall, startup/graph conversion, verified incumbent, caps/overshoot and parent versus worker CPU. Offline authoring/evidence/controller costs are separate from deployment timing. Report common-backbone improvements separately from learned-priority effects. Exact global optimum normalization is unavailable unless a sound global closure is actually obtained; use exact feasible reward and paired comparisons, not a fabricated optimum denominator.

## 8. Minimal implementable entries, in order

These files are **recommended new V07 entries**, not implemented or executed by this draft. Keep original V06 modules/receipts immutable and snapshot dependencies for a new namespace.

| New entry | Responsibility and reusable code |
|---|---|
| `configs/v07/scene_contract_001.json` | Root-approved classes/calendar, resources, capacities, scales, split namespaces/gaps, original query slots, all budgets, author/operator/selection rules and primary/secondary claim scope. Draft status alone cannot release execution. |
| `scripts/prepare_large_scale_v07.py --protocol ... --out ...` | Outcome-free one-generator scene construction for TRAIN/TEST, all cells and original contacts; reuse `Contact`, `temporal_graph` and graph serialization. It must not reuse V06 TEST populations or the V06 test-only builder's private assumptions. |
| `cipheur/commitment_v07.py` | Metered anytime `CompiledEvaluator` commitment loop with retained feasible prefix and exact frozen action trace; no oracle/native/LLM import. Same for every primary ranking control. |
| `scripts/prepare_train_decisions_v07.py --split TRAIN ...` | Freeze reference rollout query requests and exact F/X; count recurrence/aliases without labels; preserve unavailable query positions. Reuse reference score and graph boundary semantics, not detached top-score lists. |
| `scripts/run_train_certificates_v07.py --release ... --workers 8 ...` | Separate offline TRAIN cancellation oracle tasks with per-state budgets/guards, sound intervals and complete unknown/error receipts. Reuse `CancelledCompletionOracle`, not exact whole-graph pre-solving. |
| `scripts/diagnose_train_link_v07.py --TRAIN-only ...` | Preserve trigger→representation→scalar→visited action→incumbent/cost chain and explicit causal-link release decision. It does not choose new instances or alter the kernel. |
| New V07 author/controller entries | Root-managed genuine native author calls and pure quality-only EoH feedback, complete position/failure retention and program/source freeze. A scalar-fitting add-on requires its own preregistered control. |
| `scripts/run_large_scale_test_v07.py --root-test-release ...` | New independent seeds/gaps; frozen identities on all states; native baselines and all three tracks with complete costs/nulls. TEST certificates are a separate post-freeze offline process and never feed deployment or author selection. |

Existing server orchestration can stage a unique V07 source/input capsule, use the current Python environment and eight CPU workers, serialize costly native phases where needed, preserve exact byte transfers and terminal receipts, and record independent source namespaces. Root alone handles release signing, credentials, upload and execution. This draft reads no credential material and gives no server command that would start a benchmark.

## 9. Read-only implementation basis and immediate decision

The design was grounded in the current `model.py`, `programs.py` base-nine features, `compiled.py` evaluator/commitment loop, `oracle.py` sound clique envelopes, `relevance_synthesis_v04.py` component-cancellation oracle, `residual_evidence.py` actual-rollout/F/X replay, `repair_v06.py` common initialization/branch scope, native wrapper/performance orchestration, and the static outcome-free V06 generator definitions. It uses the already known flat TRAIN-quality finding as a motivation for diagnosis, not as a distribution-shift excuse. No new audit or experimental result is asserted.

**Next root decision:** freeze the scene contract and the TRAIN causal-link diagnostic protocol first. Resolve the background class/calendar assumptions and primary committed-action versus secondary search-priority scope. Then implement and run only the released large TRAIN evidence/fitness diagnostics. Large TEST is conditional on a truthful TRAIN scope decision and complete program freeze; a quality claim is unavailable if TRAIN remains flat. The 512/1,024 ×24-source/72-state TRAIN frame is a practical minimum, not evidence of efficacy or an approved benchmark.
