# Independent frozen-action audit

The retrospective action archive passes330,923 checks with no errors.
All588 contexts are present:132 validation and456 test. This audit reads
saved graphs/results only; it changes no proposals, inputs, TRAIN selection,
compiled program, oracle source or native solver. Script:
[verify_frozen_action_results_v04.py](../scripts/verify_frozen_action_results_v04.py).
Structured report:
[frozen_action_audit.json](../experiments/analysis/v04/frozen_action_audit.json).
Actual reached-state rows:
[frozen_action_reached_states.json](../experiments/analysis/v04/frozen_action_reached_states.json).

## Population and immutable protocol

Six executed ASTs are byte-identical to the TRAIN-frozen programs: guided,
free, rule-only, enumeration, selected classical baseline and prior guided
control. Original input SHA is
`827d6182abc67e3d8da16de59a785059153eef8a73a55be670f9e2b90c943af1`;
TRAIN freeze SHA is
`2f4379e782413a2ba68222314ec674163f91a5ffcf75c7d74062388dc601987b`.
Config bytes exactly match the separately frozen source ZIP. Every executed
source module matches its manifest; the relevant TRAIN synthesis/oracle/model/
graph-feature/compiler modules exactly match the original relevance source ZIP.
No deployed oracle or new model call is introduced. Execution and completion
receipts prohibit program selection and record zero model calls.

The two-state plan is reconstructed from actual completed rollouts: the initial
state and highest-coverage recorded boundary within the first two commitments,
with deterministic state-ID tie-breaking. Every saved source, boundary, state
hash, planned/unsampled count and finite action pool matches this plan.
Query caps remain TRAIN's64 nodes per component,128 searchable vertices,
10,000 expanded nodes and128 component calls per state. Matched extra
whole-residual comparisons are disabled. Actual pooled costs total5,126
component calls and118,629 expanded nodes. This is offline evidence cost,
not deployed inference cost.

All588 context audits complete, but **not every rollout completes**:
3,526/3,528 assigned schedules finish. `free_v03` fails on both sides of
`v04_c3_validation_512_0001` under the cooperative CPU target, preserving null
selection, reward, trace and completed work. These failures do not create
actual-reached states for that program. Test rollouts are all complete and
all2,736 six-policy traces/selections/rewards agree with the original advanced
fresh-quality archive. Independent original-graph checks verify feasibility
and exact reward; original C3 reconstruction/physical-verifier checks are
documented by the existing fresh input and advanced outcome audits.

## Independent state and regret verification

Independent graph/scalar evaluation replays1,071,174 candidate scores and
every saved argmax, including deterministic lexical ties. Its optimized graph
decoder is cross-checked against the existing independent TRAIN decoder at
each saved chosen root. Boundaries reached by a program choose exactly its
saved next rollout action. This checks the evidence-generating finite pool,
without changing a ranking policy.

Across1,176 sampled states there are4,384 unordered conditional-value
comparisons:105 strict,2,008 exact ties and2,271 unresolved. Validation contributes
11/472/504 strict/tie/unknown comparisons; test contributes94/1,536/1,767.
All common residual components and complete unmatched partitions, rational
endpoint sums, forced action feasibility, feasible lower witnesses, outward
rounding, preference/status labels and cache/search-cap receipts reconcile.
There are7,147 small component rows and1,568 distinct components exhaustively
checked at at most12 vertices; all saved intervals contain their exact optima.
There are6,878 larger-component receipt rows. Of105 strict comparisons,
five use only components within the exhaustive range and100 involve a
larger unmatched component.

Large-component upper endpoints remain computational receipts tied to the
unchanged, hash-verified executed TRAIN oracle code. Branch-and-bound frontier
proofs were not archived, so this is **not a complete independent proof
artifact audit of all upper endpoints**. Lower witnesses and saved cancellation
arithmetic are independently checked. Strict counts refer to the executed
sound-oracle evidence protocol, with this verification boundary preserved.
They must not be called independently proved natural obstructions.

Regret is the maximum conditional-value difference over the fixed six-program
action pool, clipped below at zero. Exact endpoint arithmetic and unknown
counts reproduce independently. Only5,664 rows at a program's actual sampled
reached states enter its own summaries;1,392 counterfactual rows are excluded.
Means first average a program's reached states within a context, then contexts
within the declared population. Bounds are deterministic intervals, not95%
confidence intervals. A finite-pool upper bound does not bound all-action
regret, and the conditional means do not estimate all states of a rollout.

| Primary population | Contexts | Own sampled states | Positive / zero / unresolved | Mean weight-normalized interval |
| --- | ---: | ---: | ---: | ---: |
| Validation standard |54 |55 |0 /32 /23 |[0,1.993081] |
| Validation dense/long |54 |84 |5 /24 /55 |[0.011726,8.959740] |
| Validation C3 |24 |28 |0 /6 /22 |[0,26.945570] |
| Test standard |216 |230 |0 /118 /112 |[0,3.263598] |
| Test dense/long |216 |299 |18 /71 /210 |[0.018693,9.006211] |
| Test C3 |24 |26 |0 /2 /24 |[0,28.339512] |

The primary's555 own sampled test states therefore comprise18 positive
finite-pool regrets,191 zero-pool regrets and346 unresolved regrets. Every
positive primary test regret occurs in the dense/long population. This
supports neither universal optimal ranking nor a guidance superiority claim.
Among actual-reached test preference incidences, the primary chooses a
source-preferred endpoint18 times and an inferior endpoint25 times. These
are repeated relation incidences, not18/25 independent trials. Shared states,
pairs and seeds can recur; per-program reached plans also differ, preventing
unqualified comparisons of conditional means across programs.

The full report retains each program/population's completion, reached-state
coverage, unknown comparisons and conditional regret intervals. In particular,
the selected degree baseline's standard/dense/C3 upper means are3.508197,
8.125404 and26.777730. These different-state means cannot isolate the effect
of the feature rule. No causal/global-quality benefit is inferred, and no
selection is revised using these held-out observations.
