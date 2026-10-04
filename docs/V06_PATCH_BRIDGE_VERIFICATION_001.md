# Independent verification of the frozen TRAIN patch bridge

This document specifies the independent auditor, not an experiment result. No
bridge result archive was read, no real programme was scored, no local-value
query was executed, and no TEST input or feedback was accessed in preparation.
Only the frozen TRAIN registration, source/program metadata and constructed
toy fixtures were checked.

## Frozen scope and provenance

The actual producer is `scripts/patch_ranking_bridge_v06.py`. The registration
is `experiments/discovery/v06_patch_bridge_001`; the programme inventory is
`experiments/discovery/v06_patch_bridge_programs_frozen_001/program_inventory.json`.
All 120 original common-Degree TRAIN contexts and all 23 frozen deployment
identities remain, giving **2,760 scoring positions**. Duplicate executable
ASTs remain distinct deployment identities. Null programmes and failed scores
remain assigned positions with null predictions.

The query bank is the union of 155 core hash-selected pairs and seven pairs
carrying surviving original strict full-TRAIN requirements. The overlap leaves
**159 distinct queries**. The 325 core pair quota shortfalls are retained.
The additional full-strict stratum is conditioned on prior certification and
patch membership; it is not an estimate of natural incidence.

Pinned inputs checked by the new verifier:

| Artifact | SHA-256 |
|---|---|
| Bridge freeze | `52fba1417af9be535e2a22ff030f99c33ff715349974a7150a79cc0bab3aa347` |
| 23-programme inventory | `f19b64047748a673a2fcd3335abbf9dc922b404ed6d45a18a3d26a90725d9602` |
| Root bridge release | `975846ae34e90d2d8efb7bdbacb6c189693ddf14544b1c5baac0c506275d8311` |
| Execution source capsule | `824f6f7ae3d4f9e88f79149794aa74842f03970278f132e8d71f7d4e70d37e77` |
| Original Degree feedback archive | `e67be3ca5c91d6d5d413c4226de6ae047f0b63673d3b951d1cfd95de62f717fc` |

Every member of the execution source capsule is checked against the external
capsule receipt and current frozen bytes. Canonical server output registration,
programme inventory and root release must match the original bytes exactly.
The caller must supply the returned canonical archive's SHA-256; the audit
also binds all fourteen required output-member hashes and its own source.
Archives are read in place without extraction; ambiguous named members fail.

## Mathematical checks

The auditor is `scripts/verify_patch_bridge_v06.py`. It imports only existing
independent audit helpers, whose byte hashes are pinned. It does not import
`cipheur`, the production feature compiler, repair kernel, oracle, or bridge
runner. A runtime check rejects an accidental production-module import.

For each original Degree trace, it independently reconstructs every common
initializer argmax and the first nonempty constructed patch, including a
root-pruned patch. A later patch cannot replace that first patch based on gain,
labels or programme scores. The auditor recomputes the legal outside boundary,
destroy set preservation, target inclusion, fixed Degree restriction order,
original graph digest and all snapshot/trace identities.

For each patch it verifies the original root clique partition, exact weighted
clique upper bound, feasible lower witness and saved interval. An independent
memoized include/exclude recurrence computes the restricted optimum with a
one-million-state verification ceiling. A ceiling failure produces a failed
verification, never an asserted exact certificate or repaired experimental
label. This is proof checking of frozen TRAIN evidence, not another assay.

For each query it reconstructs the two conditional residual partitions and
identical-component cancellation. It independently computes each unmatched
component optimum, checks every lower witness and upper enclosure, reconstructs
the fallback clique upper when the producer exhausted its recurrence budget,
and checks the aggregate difference interval, sign, epsilon, tie/unknown flag
and shared per-query search-count receipt. The auditor records the independently
verified difference but preserves the original unknown label even when its own
larger proof budget obtains a tighter answer.

Original full-residual requirements are verified separately at their original
permanent boundary. The full and local directions may disagree: neither is
silently substituted for the other. Saved full/local overlap summaries must
retain disagreement and unknown cases.

## Scores, missingness, and measured costs

Every real scoring position receives a `position_audit_rows` entry. A separate
typed-expression evaluator honors rule short-circuiting and reconstructs the
complete immutable patch score vector, exact binary-float values, ID tie break,
priority order and diagnostic greedy proposal. Degree scores use exact rational
arithmetic. Strict fit is recomputed using the frozen exact score margin for
both local and full targets, with all stratum flags and denominators preserved.

Programme feature-work is an **executed operation-count proxy**. This auditor
checks nonnegative primitive counts, their total, initialization/query/update
receipt arithmetic, zero deletion work, cap adherence and explicit cap failure.
Degree's direct work count is recomputed exactly from original adjacency sizes.
It does not independently remeasure every programme primitive, CPU or elapsed
time; finite original measurements are bound and retained verbatim. The audit
must not be described as a fresh speed measurement or a proof of feature-cost
dominance. Partial cap scores are checked as partial records and never treated
as full predictions or zero-accuracy completed scores.

The auditor recomputes all 2,760 prefix counters, all 23 per-identity summaries,
family/stratum coverage and null denominators. Its JSON preserves `patch_audit_rows`,
`label_audit_rows`, and **all 2,760 `position_audit_rows`**, including actual
fit rows, original measured cost receipts, source-row digest and local errors.
Summary consumers should use these rows rather than discard failed/null slots.

## Preparation verification and later command

Eleven constructed tests passed: clique witness corruption, exact component
cancellation, unknown preservation, full/local reversal, lazy rule evaluation,
strict margins/ties, null-score retention, direct Degree cost corruption, query
union/shortfalls, ambiguous archive rejection and production-import exclusion.
The frozen registration additionally passed 52 metadata checks with zero errors;
this is **not** an outcome audit and does not authorize an efficacy claim.

After the canonical server archive is complete and its transport hash is known:

```powershell
python scripts/verify_patch_bridge_v06.py `
  --archive experiments/runs/v06/<canonical-server-patch-bridge>.tar.gz `
  --archive-sha256 <transport-verified-64-character-SHA256> `
  --out experiments/analysis/v06/patch_bridge_audit_v06_001.json
```

The output is exclusive: an existing receipt cannot be overwritten. Successful
final verification requires positive `checks`, `errors=0`, 120 states, 159
queries and all 2,760 positions. No final report has been issued during this
preparation. Ranking agreement remains a restricted forced-inclusion diagnostic;
it does not establish branch-pivot efficiency, full-residual optimality,
held-out adaptation or complete-schedule improvement.

## Test isolation correction

The initial eleven constructed checks above passed in their isolated run.
Root subsequently identified that the production-import assertion consulted
the parent test process's entire `sys.modules`, so unrelated test discovery
could contaminate that assertion. The same check now imports the verifier in
a fresh subprocess and checks only that import's module closure. It performs
no production calculation. The verifier source and frozen experiment sources
remain unchanged; this corrects test isolation rather than scientific evidence.

## Mandatory receipt correction after independent review

The independent source/toy review in
`docs/V06_PATCH_BRIDGE_VERIFIER_REVIEW_001.md` applies to verifier SHA-256
`72633872b96f6c1be43249822e2665670525b7af7b898a90da4af7cf5df809cd`.
That review and its findings remain unchanged. Its constructed counterexample
showed that an executed `score_work_cap` record could omit both its meter and
timing fields because the old checks ran only when those fields were present.
The corrected verifier SHA-256 is
`75baf23c35195a7934eafe43f6e455ca8e8eb20a7aa5585601261d1c2b01a07d`;
the updated test source SHA-256 is
`08cf704223d12423b0232fbdcde9f7a557b659aa020bf8a9b7f338dcbaef511c`.
The earlier review does not certify this new version; a separate re-review is
required.

Every actually executed, nonmissing scored, cap or programme-error position now
requires a nonnegative integer feature-work count, a dictionary of nonnegative
integer primitive counts, and both finite nonnegative CPU and wall-time
measurements. Booleans are not accepted as integer counts. These checks run
before scoring, cap and error early returns. A programme that fails during
construction may legitimately lack completed phase counters; its core partial
meter and both outer timing receipts remain mandatory. Missing identities and
unconstructed patches must retain null measurements and cannot fabricate zero
costs.

Degree cap receipts additionally require the independently reconstructed first
work-cap crossing and exact preceding score prefix. A cap that its complete
Degree work could never reach is rejected even if an invented over-cap meter is
supplied. Four added constructed tests cover omitted/null execution receipts,
the original cap omission and fabricated crossing, a genuine partial programme
error, and fabricated costs for a missing identity. All **15 constructed tests
passed** after the correction, including the subprocess import-isolation test.
The historical eleven-test result and 52 metadata checks above remain distinct
preparation records.

This verifier currently requires a complete original common-Degree initializer
and a populated first-patch root cover/bounds receipt. General interrupted or
unconstructed original traces are conservatively rejected; a later audit must
confirm that all 120 frozen constructed-patch inputs satisfy this scope. Partial
programme scores are checked against independently reconstructed values when
available, but this is not a general completed-prefix proof for arbitrary
programme errors. They remain nonpredictions. Programme primitive counts and
measured times are retained and arithmetically checked, not independently
remeasured.

The producer's outer timing starts after graph deserialization and meter
creation. It includes programme parsing, evaluator construction, scoring,
ordering, greedy diagnostics and fit checks; it excludes graph loading,
certificate construction, authoring and the original repair run. These are
offline diagnostic timings, not pure feature latency or deployed end-to-end
repair cost. No actual bridge outcomes were read or rerun for this correction;
the frozen runner, experiment evidence and independent review were not changed.
