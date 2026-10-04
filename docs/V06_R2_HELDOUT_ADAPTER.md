# Separate R2 held-out mechanism adapter

Outcome-free prototype: `cipheur/heldout_refinement_v06.py`, with the new registration `configs/relabel_refinement_v06_002.json`. Its construction and tests read no R2 raw responses/candidate outcomes or genuine TEST labels. No real preparation or TEST execution has occurred. The earlier `heldout_mechanism_v06.py` and `relabel_v06_001.json` remain byte-identical; their twelve-genuine-winner barrier is unchanged.

## Roles and preserved evidence

R2 requires four genuine W joint winners, one per preselected whole transport block. Each retains the original information, finite-score and completed-feasible TRAIN gate. The twelve W/R/O quality-only comparator **positions** use the common objective selector; their recorded gate eligibility may be false. They are nonguarded comparators, never certified proposed-method winners. An absent bank remains null, with no scorer/search invocation, fallback, invented zero reward/fit/work/time, or deletion from assigned comparisons.

The inventory is four proposed programs + twelve quality positions + Degree + two frozen block-0 quality-only controls + all eight enumerated structural controls: **27 requested identities**, 19 main-comparison identities. Duplicate ASTs retain separate authoring/selection identities and separate measured executions; they are not independent source samples.

All **72 original withheld states**, every pair, planned query, tie/unknown and quota shortfall remain in the frame. Original plus five source-cluster-seeded bijections gives **162 identity/variant assignments and 11,664 requested state assignments**. Missing quality positions lower the separately reported scorable count, without reducing the requested frame. The original salt/order/bijection is retained, including the same mapping for paired contexts. Graph weights/edges, F/X, actions, certificate vertex fields and signed exact intervals are transported by isomorphism; numeric interval strings are never interpreted as IDs. There are no additional oracle calls.

The adapter reuses the unchanged old adapter's pure TEST interface and shared kernel. It preserves `split="test"`, checks all strict requirements on original full snapshots, and reports base alias, declared/full-demanded quotient obstruction and actual scalar margin fit separately. Unused declared features do not repair demanded aliases. The original 8-worker, 0.5 nominal-wall, 200,000-work kernel, every search cap and ordinary feasible budget-stop incumbent are retained, with actual time, work and errors.

R2 is incremental repair conditional on the common R1-selected warm seed and frontier. W-joint versus R/O-quality includes framework/selection differences; quality-only W/R/O uses a common objective selector. These comparisons do not identify an isolated witness cause or broad model-population advantage. Shared classical initialization/search is not an LLM-specific novelty. The original failed R1 release and observations remain separately retained.

## Root release contract

Preparation and execution are Linux-only and refuse an existing output directory. Preparation requires explicit byte SHA256 arguments for the R2 selection, original controls selection, TEST certificate `results.jsonl`, and root release. Before any certificate read, the adapter validates the release flags and selection binding. It never generates its own release or queries certificates.

The new root receipt must use these fields:

```json
{
  "version": "v06_R2_root_TEST_release_002",
  "issued_by": "root",
  "allow_TEST": true,
  "before_any_TEST_labels_or_performance": true,
  "all15_R2_requests_frozen_before_assessment": true,
  "all120_original_slots_assessed": true,
  "independent_R2_TRAIN_audit_zero_errors": true,
  "authoring_completion_verified": true,
  "proposed_witness_joint_count": 4,
  "R1_barrier_remains_failed": true,
  "matched_transport_complete_blocks": [0, 1, 2, 3],
  "original_runtime_sha256": "replace with the adapter's ORIGINAL_RUNTIME_SHA256 object",
  "R2_heldout_source_sha256": "replace with the adapter's source_hashes() object"
}
```

The block list above is illustrative: use the actual first four whole transport-complete blocks, without outcome filtering. Both source fields must be objects, not strings. The receipt also requires the following **scalar byte-hash fields**, calculated from the actual final immutable files:

| Release field | File bound |
|---|---|
| `selection_sha256`, `controls_selection_sha256` | R2 selection; original fixed-control selection |
| `R2_protocol_sha256`, `selection_plan_sha256`, `R2_freeze_sha256` | R2 study protocol, unchanged pre-generation role plan, pre-authoring freeze |
| `authoring_completion_sha256`, `transport_runtime_binding_sha256` | All-fifteen authoring completion; pre-generation transport/runtime binding |
| `R2_TRAIN_execution_sha256`, `R2_TRAIN_complete_sha256`, `R2_candidate_results_sha256` | Complete 120-position TRAIN execution, completion and candidate-results byte hashes |
| `R2_TRAIN_audit_sha256`, `R2_authoring_audit_sha256`, `packet_audit_sha256` | Independent TRAIN, all-fifteen authoring and prepared-packet audits |
| `training_evidence_sha256` | Original TRAIN evidence bound by the R2 protocol |
| `original_evidence_freeze_sha256`, `original_data_sha256`, `original_query_protocol_sha256` | Original `v06_evidence_001` freeze, data and query protocol |
| `controls_protocol_sha256`, `controls_freeze_sha256` | Original fixed-control assessment registration and freeze |
| `control_bank_sha256`, `control_bank_freeze_sha256` | Original fixed banks and their freeze |
| `kernel_config_sha256`, `relabel_config_sha256` | Unchanged kernel configuration; the new R2 relabel configuration |

Audit files require a positive integer `checks` and `errors=0` or `errors=[]`; retain their complete original contents. The adapter hashes the TRAIN candidate-results file but does **not** parse raw candidates, responses or assessment rows. It reads only the already frozen deployment selection and metadata/audit summaries. Original runtime hashes are pinned in code and cross-checked with the R2 protocol; the new adapter/helper-source map must be bound in the root receipt before withheld access.

Only after all fifteen authoring sessions and the independent zero-error 120-position TRAIN audit confirm four genuine W winners may root create this release. Generate original TEST certificates with **`programme_freeze_sha256` equal to the root release receipt's byte hash**, not the selection hash. The receipt already binds the exact R2 selection. The adapter rejects a certificate bound to the older twelve-winner selection or to the R2 selection alone.

## Entry points and outputs

Use `python -B -m cipheur.heldout_refinement_v06 prepare --help` for the required path/hash arguments. `--r2-study` contains protocol, selection plan, pre-authoring freeze, authoring completion, runtime binding and TRAIN evidence; `--train-assessment` contains execution, completion and candidate-results files. Supply the three independent audits, original evidence plan/control registration, frozen banks and new relabel configuration. This is a future authorized operation; preparation itself executes no program and no oracle.

After that separately frozen registration, execution is:

```text
python -B -m cipheur.heldout_refinement_v06 run --registration <NEW_R2_REGISTRATION> --out <NEW_R2_RESULTS> --root-release-sha256 <ROOT_RELEASE_BYTE_SHA256>
```

Registration saves all selected roles, audit/completion receipts, the unchanged TEST inputs/certificates, five mapping inventories, runtime source snapshots and every artifact hash. Results retain per-query scalar/alias/quotient checks, paired reversal/preservation categories, every state incumbent/reward/work/time/error, null assignments and all five relabel measurements. Missing predictions remain absent. Completion counts, normal-cap stops, errors, missing comparisons and source-cluster dependence are stated separately; assignment completion is not an effectiveness claim.

Validation: `python -B -m unittest tests.test_heldout_refinement_v06 -v`. Eleven fabricated tiny-graph/metadata tests cover the four-W barrier, nonguarded gate-failed comparators, null positions, duplicate identities, release checks before certificate access, release-bound certificates, five paired ID bijections including numeric IDs/F/X/actions, unused-feature aliases, tiny shared-kernel incumbents, overwrite/tamper rejection and unchanged old files. No genuine TEST frame or outcome is read by these tests.
