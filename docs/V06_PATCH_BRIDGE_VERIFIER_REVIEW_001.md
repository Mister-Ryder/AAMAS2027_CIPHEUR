# V06 patch-bridge verifier: independent source and toy review

Review date: 2026-10-04. Scope: the verifier, its constructed tests, the original bridge runner, and frozen registration/program metadata. No bridge result archive, live performance output, new certificate, or deployed-program experiment was read or executed. Only independent functions on artificial graphs and the existing eleven constructed tests were executed. No runner, verifier, test, registration, program, or paper file was modified by this review.

## Decision

The mathematical and assignment-frame design is sound within the stated, restricted diagnostic scope. The eleven existing toy tests pass. **One receipt-validation gap needs correction before relying on a zero-error final audit:** an executed score position can claim a work-cap failure while omitting its work and time receipts, and `check_score()` currently accepts that position. This is an audit-code issue; it does not establish that any actual execution row is wrong.

There is also an applicability restriction: `check_saved_patch()` requires a complete common-Degree initializer and populated first-patch bounds. It should not be described as supporting arbitrary interrupted original traces. The frozen registration declares 120 constructed patches; checking the corresponding actual receipts remains the separate, future full-archive audit.

## Reviewed versions

| File | SHA-256 at this review |
|---|---|
| `scripts/verify_patch_bridge_v06.py` | `72633872b96f6c1be43249822e2665670525b7af7b898a90da4af7cf5df809cd` |
| `tests/test_verify_patch_bridge_v06.py` | `e34e47d80c709cdcaac82facdce8866abcd9c4d0cafd3423c6709eef12c05e79` |
| `scripts/patch_ranking_bridge_v06.py` | `b0d4a599fa165eb2a74b55d85ec375ef538c9fa174bd4ce8783ea5233b870523` |
| Bridge config | `ba158d95c38511e533e182952e26db29fcc5a29de107476b71f3977e57a6fcc4` |
| Bridge protocol | `967f7a60d1a7f158280b27e08f8db783391c7fa13298a7f8c90148fc83cec07a` |
| Bridge registration freeze | `52fba1417af9be535e2a22ff030f99c33ff715349974a7150a79cc0bab3aa347` |
| Frozen 23-identity program inventory | `f19b64047748a673a2fcd3335abbf9dc922b404ed6d45a18a3d26a90725d9602` |

The verifier separately pins the root release (`975846ae…d8311`), execution capsule (`824f6f7a…37e77`), original Degree archive (`e67be3ca…f717fc`), and two independent helper modules. Its registration checks bind every capsule member to both receipt and current source bytes, compare source dictionaries, and require TRAIN-only selection and a complete root release before accepting outputs. These are checks implemented in the reviewed code; this review did not execute the full registration/archive audit.

## Required correction: an unsubstantiated cap can pass

At verifier lines 362–442, `check_score()` validates the feature meter and CPU/wall only inside `if "feature_meter" in saved:` (line 409). When a constructed, nonmissing position has status `score_work_cap`, it requires null scores/fits and string error fields, but does not first require that a meter exists.

A constructed two-node edge with weights 2 and 1, direct Degree priority, and a 200,000-work cap has independently computable scores `{a: 2, b: 1}` and direct work 6. Supplying this row:

```python
{
    "state_id": "toy", "program_id": "degree", "role": "degree",
    "patch_status": "constructed", "selection_performed": False,
    "status": "score_work_cap", "scores": None,
    "local_fit": None, "full_target_fit": None,
    "error_type": "_FeatureLimit", "error": "claimed cap without meter",
    "partial_scores_not_predictions": {}
}
```

produced `checks.errors == []` in the independent toy call. No feature-work crossing or executed timing supported the claimed failure. The production runner always writes a meter and CPU/wall for scored/capped/error positions, so omission is not an allowed alternative encoding. An otherwise valid prediction could be removed from the observed denominator by this false classification.

Recommended audit-only repair: require a dictionary meter and finite CPU/wall for every actually executed constructed, nonmissing position; then apply the existing status-specific checks. A cap must retain a charged crossing above the frozen work limit. Do not require all complete-program meter subfields for an error occurring during evaluator initialization, because the production partial meter may legitimately be incomplete. Add a toy regression rejecting the row above and a scored row missing its receipts. No frozen algorithm or scientific result needs modification.

Additional receipt limits should remain explicit: partial-score keys are checked as a subset, rather than as the exact completed prefix of the sorted scoring loop; when independent full scoring raises, partial-score values are not independently reconstructed. These partial values must remain nonpredictions and must not support partial accuracy claims.

## Assignment frame, selection, and source scope

The intended frame is exactly 120 original TRAIN states × 23 frozen identities = 2,760 score assignments, not 2,760 independent programs or graph samples. The code checks exact state order, all state–identity pairs, raw stream hashes, 2,760 cumulative-prefix rows, and all 23 summary rows. Null/error positions remain in the assigned frame. Duplicate executable ASTs retain their original identities.

Roles are reconstructed from the actual entries: four genuine W joint winners; four W, four R, and four O quality-only identities; one structural control; one fixed-base control; one Degree control; and four published EoH-DSL quality identities. Genuine W identities cannot be absent or replaced by Degree. The stale/historical inventory `role_counts` field is not used to silently drop the added EoH identities. The frozen EoH metadata identifies all four selected programs as the shared warm seed; these cannot be described as four newly authored winning ASTs.

The bridge audit verifies deployment against the root-frozen inventory, not by repeating R2/EoH selection from original authoring archives. The upstream selection audits and root release supply that provenance. This division is appropriate provided publication/release checks continue to bind those upstream audits. No bridge fit should be sent back to authors or used to reselect any identity.

## Snapshot and interruption scope

The first nonempty constructed patch is selected from the original common-Degree trace, including root-pruned or capped local search. Neither gain, bound tightness, nor program fit selects a later patch. The verifier reconstructs every Degree initializer argmax, retained incumbent, outside fixed set, eligible residual, destroy-preserving restriction, graph/snapshot hashes, and patch-local feasibility.

For a constructed patch with populated bounds, it independently checks a disjoint clique-cover upper bound, feasible local lower witness, and `L ≤ exact MWIS ≤ U ≤ root U`; an exactness claim additionally requires equality. This is stronger than trusting the saved search status.

A second artificial test used two nonadjacent vertices, a correct first Degree selection, a feasible partial initializer, `initialization_complete=False`, and no constructed patch. It returned no patch but recorded `original_degree_complete_feasible_initializer`. The runner's `select_patch()` would retain such a no-patch state after validating the feasible saved prefix; the verifier insists on completion before reaching its no-patch branch. Similarly, a materialized first patch without a populated root cover/upper bound cannot pass the direct bound indexing. These are conservative failures, not false certificates. Either document the complete-initializer/populated-bound precondition for this frozen study or handle valid interrupted no-patch rows explicitly. Do not repair missing original outcomes with new optimization.

## Local certificates and full-versus-local distinctions

The frozen query union has 159 assignments: 155 deterministic core pairs plus seven surviving original full-strict pairs, with three overlaps and four added pairs. The 325 shortfalls are relative to the requested four core pairs per 120 states: `480 − 155 = 325`. The code reconstructs adjacency-first SHA ordering, the complete union, flags, and shortfalls. A shortfall is not a zero-valued label.

For a local patch `R`, the forced-inclusion difference is

`w(a) − w(b) + Σ alpha(C_a) − Σ alpha(C_b)`.

Identical connected components cancel exactly. Every unmatched component is checked with an independent exact recurrence and a feasible lower witness. For saved component intervals `[L_a,U_a]` and `[L_b,U_b]`, the reconstructed difference interval is

`[w(a)−w(b)+ΣL_a−ΣU_b, w(a)−w(b)+ΣU_a−ΣL_b]`.

A strict direction requires the entire interval beyond the fixed epsilon; `[0,0]` is an exact tie; everything else remains unknown. Stronger independent verification never upgrades a saved unknown. The fixed 100,000-state shared query budget and capped clique enclosure are checked as receipts; recurrence state counts are not independently remeasured. The independent verifier's own one-million-state ceiling must fail closed if exceeded.

Original full-strict requirements use the original permanent boundary and full residual, while local labels fix the saved outside incumbent and restrict completion to the patch. These objective differences can disagree: the existing four-node toy gives full difference −6 and restricted difference +4. The code preserves disagreements and unknowns, and computes separate local and full fits. The full-strict stratum is certification-conditioned; neither it nor adjacency-first core sampling estimates unbiased natural decision incidence.

## Scores, fits, prefixes, and null denominators

The independent scorer imports only pinned audit helpers, uses a whitelist rule evaluator and lazy typed features, and compares the actual binary-floating-point score values through exact `Fraction` strings. Degree uses its separate exact weight/degree ratio. Sorting uses decreasing score and fixed vertex-ID ties. Greedy proposals are checked for independence inside the patch and after union with the outside fixed set.

Only strict labels enter ranking fit. A pass requires score difference strictly greater than the fixed score margin; a tie is retained separately. Local and original full target counts remain separate. The verifier recomputes cumulative assigned states, available labels, scored states, observed predictions, and passed predictions for every prefix. Missing programs, score errors, and caps retain null fits rather than zero accuracy. Conditional accuracy therefore requires its observed denominator and assignment/label coverage alongside it.

This is an immutable-priority diagnostic. It does not execute pivot search, reproduce a complete schedule, certify a useful branch ordering, or show that an LLM-derived program improves deployment reward. The production runner and verifier both label that distinction explicitly.

## Cost attribution

The meter is an operation proxy, not hardware-independent work or published-native equivalent compute. Exact direct Degree work is independently reconstructed; program primitive sums, initialization/query/update accounting, zero deletion-update work, and cap crossings are checked, but individual program primitive counts and runtime costs are not remeasured.

In `score_patch()` the timer starts after graph deserialization and meter creation. It includes program parsing, evaluator construction, scoring, ordering, greedy proposal construction, and fit calculations performed before timing fields are evaluated. It excludes prior local-certificate generation, graph deserialization, authoring, original repair search, and independent audit recurrence. Consequently it is offline patch-diagnostic execution time; it is neither pure feature time nor end-to-end deployed solver time. No reduction in this timer proves lower total synthesis cost, faster repair, or superiority to a C++ baseline.

## Executed toy verification and final boundary

`python -B -m unittest tests.test_verify_patch_bridge_v06 -v`: **11 tests passed**, covering clique partition corruption, cancellation, unknown preservation, full/local reversal, lazy unused features, score margins/ties, missing predictions, Degree work corruption, query union/shortfalls, duplicate archive members, and absence of production imports. Two additional in-memory toy calls confirmed the missing-meter cap acceptance and partial-initializer scope restriction described above.

This document is a source-review result, not a completed bridge-results audit. Acceptance of actual scientific outputs still requires the canonical server archive SHA, all frozen source/root bindings, a corrected zero-error independent audit, and the separate upstream authoring/selection provenance checks. No outcome or effect claim is made here.

## Follow-up: receipt guard corrected and independently rechecked

The preceding initial review and probes are preserved as history. Its original document SHA was `16c21c6f33e00c1fb36463249cc6ac4099e7105f086ec33c5aff714d9625507e`. The receipt-gap finding above applies to verifier SHA `72633872…f809cd`; it is **resolved in the subsequently reviewed verifier** `75baf23c35195a7934eafe43f6e455ca8e8eb20a7aa5585601261d1c2b01a07d`. Updated constructed tests have SHA `08cf704223d12423b0232fbdcde9f7a557b659aa020bf8a9b7f338dcbaef511c`.

The new `check_score_receipts()` runs before score/status interpretation. Every actually executed constructed, nonmissing position now requires a nonnegative meter and both finite nonnegative CPU/wall receipts. Nonexecuted missing positions cannot fabricate those receipts. Programme initialization/errors may retain legitimate partial meters without invented complete-phase counters. Complete scored positions retain the previous cost-sum checks. Degree cap rows additionally reconstruct the exact first crossing and exact completed sorted prefix.

Independent follow-up validation executed only artificial cases:

- All **15 updated toy tests passed** (approximately 0.14 seconds).
- The exact original missing-receipt counterexample now records three errors: absent executed meter, absent CPU, and absent wall. It can no longer silently remove a valid Degree prediction from the observed denominator.
- With the same two-node graph and cap 3, the actual work crossing 6 with completed prefix `{a: 2}` passes. Replacing that prefix with `{b: 1}` fails; claiming crossing work 4 also fails.

Verdict for this fix: **source/toy PASS**. The unchanged interruption/applicability limits, programme-cost proxy limitations, full/local scope restrictions, and need for the eventual independent canonical-results audit remain. This addendum does not claim an audit of real bridge outcomes, does not alter frozen execution source, and does not weaken the registered scientific protocol.
