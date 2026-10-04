# V06 TRAIN patch bridge: audited results and scope

The actual canonical result audit passes **52,930 checks with zero errors**,
covering 120 frozen original-Degree first-patch snapshots, 159 distinct local
conditional queries and all 2,760 scoring positions. This is a TRAIN diagnostic
with frozen programmes, not heldout programme selection or another scheduling
experiment. No original runtime, evidence, programme or release was changed.

| Artifact | SHA-256 |
|---|---|
| Canonical server archive | `d47d75bba844ae30d81f399c9423d167b8eb4f5932d875fd2d2735ce25b473f4` |
| Independent audit `experiments/analysis/v06/TRAIN_patch_bridge_audit_v06_001.json` | `4f7fd51d216fc9235f3b7f2704de4a17881ee19f891e3d5ea2100f80b7ac07b1` |
| Current auditor `scripts/verify_patch_bridge_v06.py` | `fc313c55ebb127881078d600042d2ee40eb365baa30657975e1e166786c1f4c1` |
| Frozen execution capsule | `824f6f7ae3d4f9e88f79149794aa74842f03970278f132e8d71f7d4e70d37e77` |
| Frozen 23-programme inventory | `f19b64047748a673a2fcd3335abbf9dc922b404ed6d45a18a3d26a90725d9602` |
| Frozen bridge root release | `975846ae34e90d2d8efb7bdbacb6c189693ddf14544b1c5baac0c506275d8311` |

## Parser compatibility history

The single initially requested audit attempt stopped before mathematical outcome
reads because global basename lookup found both the actual output
`v06_TRAIN_patch_bridge_results_server_001/config.json` and the separate
`registration/config.json` copy. No failed audit receipt was produced and no
scientific check passed at that point. Root authorized the necessary read-only
namespace correction: the auditor now reads the exact producer output prefix,
rejects duplicate output files within that prefix, and independently checks
that both registration copies of config/protocol equal the output and frozen
local bytes. General helper archive ambiguity rejection remains.

The corrected required audit then ran once and passed. No extra probes, tests,
experimental runs or outcome-based source changes were made in this task. The
historical source/toy review and receipt-guard correction remain separately
documented; this actual receipt binds the new auditor source above.

## Assigned scope and local labels

All 120 original first constructed patches are retained. Their sizes are:
106 of size two, seven of size three, two of size four, one of size five, two
of size six, one of size seven and one of size thirteen. Only four original
traces have a saved priority order; an offline scored order is not fabricated
as a recorded original repair decision. All saved restricted-optimum claims
match the independent exact recurrence. The saved local lower witness equals
the restricted optimum in every patch; the root clique upper attains it in
117 patches. This does not assert that the pre-repair destroyed incumbent
already attained that optimum.

| Query stratum | Assigned distinct queries | Local strict | Exact local tie | Unknown |
|---|---:|---:|---:|---:|
| Core SHA-selected | 155 | 14 | 141 | 0 |
| Surviving original full-strict pairs | 7 | 4 | 3 | 0 |
| Union, after overlap | 159 | 15 | 144 | 0 |

The strata overlap and must not be summed. The seven added/surviving pairs are
conditioned on prior full-residual strict certification and patch membership;
their incidence is not comparable with the core sampling incidence. The 325
pair-quota shortfalls remain, as do six sampled pairs that are not adjacent.
Every pair is evaluated with its frozen original endpoints; individually
feasible actions and outside boundary commitments are independently checked.

## Actual fit, complete coverage and negative results

Each frozen identity scores all 120 states. All 2,760 positions have status
`scored`: zero missing identities, no feature-work cap failures and no programme
errors. Nulls and missing-score semantics remain in the schema, but there are
no actual failure/null scoring positions in this completed batch. A tie is a
measured local-label result, not a missing strict prediction.

| Role | Identities | Core strict fit | All local strict fit | Full-strict stratum local fit | Original full-target fit |
|---|---:|---:|---:|---:|---:|
| W joint | 4 | 55/56 | 58/60 | 15/16 | 20/28 |
| W quality | 4 | 55/56 | 58/60 | 15/16 | 17/28 |
| R quality | 4 | 56/56 | 60/60 | 16/16 | 24/28 |
| O quality | 4 | 56/56 | 60/60 | 16/16 | 19/28 |
| Fixed structural | 1 | 14/14 | 14/15 | 3/4 | 4/7 |
| Fixed base | 1 | 0/14 | 0/15 | 0/4 | 0/7 |
| Degree | 1 | 14/14 | 15/15 | 4/4 | 6/7 |
| EoH-DSL quality | 4 | 56/56 | 60/60 | 16/16 | 24/28 |

These are programme-by-label counts on repeated common labels. Four EoH
outputs share the same seed-origin executable AST; they remain four genuine
pipeline output identities without becoming four distinct learned programmes.
The W joint per-programme core counts are 13/14, 14/14, 14/14 and 14/14; pooled
local counts are 13/15, 15/15, 15/15 and 15/15. No W-versus-Degree or
W-versus-quality-control local-priority advantage is supported here. The fixed
base rule's failure alone cannot establish an LLM benefit because Degree
already fits all local strict preferences.

## Full versus restricted boundary

Every local certificate forces an action within the restricted patch while
the saved outside incumbent remains fixed. Original full targets use their
original permanent boundary and full residual graph. Of the seven originally
strict full-residual comparisons, three remain local strict with the same
direction, one remains strict with the opposite direction and three become
exact local ties. Their labels are never substituted for one another.

The observed reversal and ties close a conceptual scope gap: a sound full
conditional certificate is not automatically a label for patch-local greedy
selection or B&B pivot choice. Score agreement here is a diagnostic. It is
neither a measurement of actual pivot benefit nor proof of realised schedule
gain, global regret, heldout adaptation or superiority over native MWIS solvers.

## Measured offline scoring cost

All executed positions retain mandatory meter and timing receipts. Feature
work is a charged operation-count proxy; means below aggregate all assigned
positions within each role. CPU/wall are the original server measurements.

| Role | Mean feature work | Mean CPU milliseconds | Mean wall milliseconds |
|---|---:|---:|---:|
| W joint | 18483/32 | 2.929 | 2.929 |
| W quality | 10927/24 | 2.154 | 2.154 |
| R quality | 60477/160 | 1.686 | 1.686 |
| O quality | 107903/480 | 1.222 | 1.222 |
| Fixed structural | 4681/40 | 0.357 | 0.358 |
| Fixed base | 1187/40 | 0.149 | 0.149 |
| Degree | 275/24 | 0.062 | 0.062 |
| EoH-DSL quality | 14399/40 | 1.719 | 1.719 |

These measurements start after graph deserialization and meter construction,
then include parsing/evaluator setup, scoring, ordering, diagnostic greedy
packing and fit evaluation. They exclude local/full certificate generation,
authoring and the original scheduling repair. They are not pure feature
latency, inference-only comparisons or total deployed scheduling cost.
The audit checks receipts and Degree work exactly; programme primitive costs
and clock measurements are not independently remeasured.

## Manuscript integration

The concise owned fragment is `paper/drafts/v06/patch_bridge_results.tex`.
It reports core/full-strict strata, overlap, exact ties, complete coverage and
the genuine negative local-priority comparison, followed by the full/local
scope mismatch. Root owns insertion into experiments and final page layout.
No audit counts, parser history, hashes or engineering timing detail is placed
in the manuscript fragment. Discussion/conclusion were subsequently updated
from the separately completed heldout analysis
`experiments/analysis/v06/heldout_mechanism_analysis_v06_001.json`, SHA
`a2296b5189abc8adb9bc6e70ef04b0639d4f580929a0e4b64f332c15bef950d5`.
Its compact rows are SHA
`dd8687daeb7176b30f44cb92a1a1804402d39dcb9346e1c3db39303ed19a9653`.

The current discussion reports W joint strict fit 1666/1812 = 91.94%,
joint W minus quality W +61/1812 = +3.37 percentage points and joint W minus
quality R -33/1812 = -1.82 points. The common quality-selector W minus R
contrast is -94/1812 = -5.19 points. Source-bootstrap intervals concern these
frozen identities and preserve paired source clusters; they do not establish
a model-population effect. All 13,392 actual heldout kernel positions are
normal, feasible and have zero exact matched-Degree reward difference.
All four EoH pipeline outputs retain the shared seed executable programme.
Observed relabel sensitivity remains explicit. No unsupported performance
comparison was added; root still owns weighted-performance findings and final
intro placeholder replacement.

The independent heldout-analysis owner additionally reports the already-frozen
compact assignment quotients: all four original W joint interfaces are DAGs;
three of the 20 renamed W joint interfaces become contradictory (blocks 0, 2
and 3 at `relabel_3`). The other 17 renamed interfaces remain DAGs. Discussion
retains both the original observed information compatibility and this failure
of numbering invariance. This is a read of completed compact rows, not a new
evaluation, proof or programme modification.
