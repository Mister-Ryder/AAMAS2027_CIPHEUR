# V06 TRAIN-only restricted-patch ranking bridge

This separate diagnostic study tests whether frozen priorities agree with
forced-inclusion preferences in the actual restricted patches constructed by
the common Degree kernel. It connects the learned ranking interface to the
local problem used at deployment. It does **not** certify pivot efficiency,
search-node savings, complete-schedule quality, global optima, or generalization.
The study contributes no authoring, selector or tuning feedback.

## Two freezes and permitted phases

The implementation is `scripts/patch_ranking_bridge_v06.py`; declared settings
are `configs/patch_ranking_bridge_v06_001.json`. Its `prepare` phase reads only
the original common-Degree TRAIN archive and already-frozen original TRAIN
evidence. It constructs the metadata/query inventory without calling a
conditional oracle, scoring a candidate, reading R2 responses or reading TEST.
Every source graph, source context, feedback row, complete original trace,
chosen trace entry, boundary and snapshot is bound by a digest. The complete
original evidence bytes are preserved separately.

The original archive is
`experiments/runs/v06/repair_degree_feedback_v06_001.tar.gz`, SHA-256
`e67be3ca5c91d6d5d413c4226de6ae047f0b63673d3b951d1cfd95de62f717fc`.
It contains the 120 original TRAIN states; no new scheduling run recreates
or substitutes its trace. Archive member/freeze checks are required before
sampling. All 120 assigned identities remain, including explicit missing
result/patch rows should these occur.

Actual new labels and program scores require a later, explicit root-issued
release whose externally supplied hash binds the bridge freeze receipt,
complete program inventory and runtime source hashes. `prepare` does not
create such a release. The root reviews and freezes the capsule before cloud
execution, after the selected programs are released. Existing plan or outcome
directories are never overwritten. The run rejects altered source/config/input
bytes, non-TRAIN rows, incomplete identity roles and a mismatched release.

## Outcome-independent patch selection

For each state, take the **first nonempty constructed patch in original trace
order**, including a root-pruned patch or one whose local search stopped.
Selection uses materialized patch metadata; it does not use gain, bound
tightness, returned quality, labels, rule fit or candidate outcomes. An earlier
entry without a materialized patch cannot have committed an update; that
inconsistent trace is rejected rather than skipped. Consequently the first
selected patch's incumbent is the saved `initial_selected` incumbent.

Recover its destroy set D, outside incumbent F_out = I minus D, original
permanent fixed set F and excluded set X, and saved restricted region Rprime.
Require D to be movable and independent, F to remain in F_out, and
D subset Rprime subset V minus (F_out union N(F_out) union X). Verify the saved
full-free-region size and the original 24-vertex patch limit. The scorer receives
the original full graph and exactly Rprime as its immutable active snapshot,
matching the kernel's `CompiledEvaluator(..., score_slice=True)` call.

Some original patches can be certified at the root before priorities are
queried by the production kernel. Their `original_priority_order_present`
indicator is retained and counted; they are not removed. Agreement on such a
patch is a ranking diagnostic, not an operational benefit from a score the
original search did not need.

## Two fixed query strata

First, choose four core pairs from all distinct patch actions, taking adjacent
pairs before nonadjacent pairs and fixed SHA order within each group. Fill
with nonadjacent pairs only on adjacent shortfall. Record every pair's competing
indicator and all pair/edge shortfalls. Both actions are individually feasible
against the same outside incumbent; a nonadjacent pair is explicitly not an
exclusive-choice conflict.

Second, add **every already-certified original strict TRAIN requirement whose
two actions both remain in Rprime**. Deduplicate the union by unordered pair,
retaining `in_core_sha`, `in_full_strict_bridge`, original row indices and both
sampling ranks. The original inventory contains at most sixteen pairs/state,
so the union has at most twenty pairs/patch. Extra pairs have a separate fixed
SHA order. They depend on pre-existing full certification and patch metadata,
and are **not an estimate of natural conflict or reversal incidence**. Neither
stratum uses a program outcome or a new local label to select pairs.

## Offline local certificates

For d in Rprime, the target is w(F_out) + w(d) + MWIS of the graph induced by
Rprime minus d and its neighbors. The outside reward is constant across the
compared actions and cancels. Within the restricted induced graph, identical
connected components cancel exactly; other components are bounded independently.

The runner implements an independent exact memoized include/exclude recurrence.
A query has a hard total limit of **100,000 newly expanded recurrence states**
across its unmatched components. Each component receives only the remaining
allowance. A stop retains a verified feasible greedy packing and a verified
disjoint clique-cover upper bound, with exact rational weights. Tight fallback
enclosures can still prove exactness; an exhausted search is never described
as exhaustive merely because its stack/memo is partial. All strict labels,
exact ties and unresolved intervals remain. A strict label uses the declared
positive objective margin 1/100000000. There is no online oracle and no new
full-residual label query.

Original full requirements are kept at their **original permanent F/X** scope,
not relabeled as local certificates. Compare their direction with the local
direction for the full-strict query stratum. Report strict agree/disagree counts,
local ties and unknowns separately. A local tie is neither strict direction
agreement nor failure. Full and local directions may legitimately disagree.

## Frozen identities and scoring

The root supplies a JSON program inventory containing `selection_split: train`,
`test_used_for_selection: false`, and `entries`. Each entry has unique `id`,
explicit `role`, `priority` (`program` or `degree`), and a frozen typed `program`
AST or an explicit null. Required roles comprise four `witness_joint`, four each
of `witness_quality`, `relations_quality`, `objective_quality`, one
`fixed_structural`, one `fixed_base` and one `degree`: nineteen identities.
If the future EoH comparison is added, include all four `eoh_quality` identities,
including nulls. Four genuine non-null W joint programs are required; quality
or classical programs cannot replace a missing proposed program. Duplicate
executable programs remain separately assigned identities and are not counted
as independent discoveries.

Each priority is evaluated once on every vertex of the same immutable patch,
in sorted identifier order, with a 200,000 feature-work cap. Preserve errors,
partial-score diagnostics and missing programs. Partial scores are not complete
predictions. Degree uses exact weight divided by max(1, patch degree). Separately
measure strict fit against (a) locally certified targets, stratified into core
and full-strict pair cohorts, and (b) surviving original full targets evaluated
using these patch scores. Score ties fail a strict score-margin requirement;
unknown/tied objective targets provide no strict scoring constraint. Score
margin is 1/1000000000.

A priority-only greedy proposal is recorded as an auxiliary feasible witness.
It is not the kernel's retained best incumbent, which also includes D, a common
Degree proposal and bounded search. No branch search is executed in this
assay. Forced-inclusion labels do not prove that choosing the preferred action
as a branch pivot leads to fewer nodes under shared include-first traversal.
That efficiency question requires a separate matched search replay.

## Outputs and execution interface

Preparation saves `inventory.json`, `config.json`, original TRAIN evidence,
`protocol.json` and `freeze_receipt.json`. Execution saves raw `labels.jsonl`,
raw per-identity/per-state `scores.jsonl`, per-family coverage, cumulative
prefix counts, per-identity summary, executable-field hashes and completion
bindings. Missing predictions are absent accuracy observations rather than
fabricated zero-accuracy programs; their coverage shortfall remains explicit.
No result selects a winner or changes the ongoing R2 study.

```text
python scripts/patch_ranking_bridge_v06.py prepare --archive ORIGINAL_DEGREE_TRAIN_ARCHIVE --config configs/patch_ranking_bridge_v06_001.json --full-training-evidence ORIGINAL_TRAIN_EVIDENCE --out NEW_REGISTRATION
python scripts/patch_ranking_bridge_v06.py run --registration FROZEN_REGISTRATION --programmes FROZEN_PROGRAM_INVENTORY --release ROOT_BRIDGE_RELEASE --release-sha256 EXPECTED_ROOT_RELEASE_HASH --out NEW_OUTCOMES
```

The root release must declare `bridge_execution_authorized`,
`program_release_complete`, `before_any_bridge_certificate_or_program_score`,
`no_bridge_authoring_or_selection_feedback` all true; `selection_split` train;
and exact `bridge_freeze_sha256`, `program_inventory_sha256` and
`runtime_source_sha256` bindings. These fields authorize only this diagnostic
run; they do not claim the registered method succeeded.

Eleven tiny-graph tests independently enumerate conditional optima, check
hard-cap soundness and exact component cancellation, exhibit legitimate
full/local preference disagreement, confirm gain-independent patch selection,
test query-union deduplication and explicit nulls, and verify that preparation
does not invoke scorers/certifiers. The end-to-end released test uses temporary
toy artifacts only. Real TRAIN labels and program scores remain unexecuted
until the root's later release.
