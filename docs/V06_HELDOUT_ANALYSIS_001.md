# Read-only analysis contract for R2/EoH heldout mechanism results

This document describes the prepared analysis, not heldout findings. Preparation
has read frozen source/protocol schemas and constructed fixtures only. It has
not opened live batch outcomes, run a programme, queried an oracle, or selected
a new method. The analysis requires final canonical archives and their actual
zero-error independent result audits.

## Required inputs and failure guard

`scripts/analyze_heldout_mechanism_v06.py` accepts both canonical R2 and EoH
server archives plus their reports from `scripts/verify_heldout_results_v06.py`.
Before reading results or registered input payloads it checks the report kind,
positive integer check count, integer zero errors, empty error records, exact
archive SHA-256, current independent-auditor source SHA-256, complete identity
coverage and requested state-assignment counts. It then checks the terminal
complete marker, no selection/oracle/fallback flags, and actual results bytes.
A partial batch, stale audit, changed archive, worker-return frame omission or
wrong schema fails. No directory of live results is accepted.

The frozen identity composition is checked as **16 R2 outputs plus 11 controls**:
four genuine proposed witness joint winners, twelve nonguarded W/R/O quality
outputs, two TRAIN quality-selected fixed controls, common Degree, and all eight
original enumerated structural controls. The EoH addon contributes four
nonguarded published-quality pipeline outputs with their original seed/author
origins. It must reuse the identical R2 records, certificates and five mappings.

All 31 identities, original 72 states and six variants remain assigned:
**13,392 kernel positions**. The analyser preserves null identities, worker and
interface failures, and every original query. Duplicate executable AST groups
are reported explicitly. A repeated seed-origin EoH output remains a real
pipeline identity; it is not treated as a distinct learned programme or an
independent model draw.

## Relational and representation measurements

The primary measurements are actual strict scalar fit and actual base-alias
strict fit using the audited scorer predictions. All ties, unknown intervals,
score ties, tiny positive differences that fail the prescribed fit margin, and
missing interface scores remain separate. Full-member denominators and
conditional measured denominators are stored; missing predictions never become
zero accuracy. Demand-interface and declared-interface quotient contradictions,
self-loops and witness kinds are retained per original identity/variant.

Paired intervention queries are matched by pair identity and original query
position, retaining both constraint sides. Joint correctness on strict reversal
or strict preservation requires **both** observed endpoint predictions to pass.
Exact tie on both sides, strict-to-tie, tie-to-strict and incomplete intervals
are separately counted. A missing side remains an unknown joint measurement.
Action and source-cluster alignment or duplicate endpoints cannot be ignored.

The analyzer stores two distinct sound-interval-weighted diagnostics. Let the
certificate interval `[L,U]` enclose `V(a)-V(b)`. The positive preferred gap
lower bound is `L` for preferred action `a`, and `-U` for preferred action `b`.

1. **Certified-gap-weighted specification violation:** this positive lower
   bound contributes when the prescribed strict-fit test fails. It includes
   positive scores whose separation is below the fit margin. It is a weighted
   specification statistic, not an assertion that an action was actually
   selected incorrectly.
2. **Hypothetical pairwise rank choice minimum loss:** the larger score wins a
   two-action comparison, with the actual lexicographic ID tie rule. The lower
   bound contributes only when that hypothetical ranking selects the certified
   inferior action. Score ties and tiny positive margin failures are explicit.
   With no score observation, the loss is null.

Both concern conditional full-residual completion values under explicit
boundary commitments. The deployed repair uses patch-local greedy ordering and
branch priority; this hypothetical two-action choice is not a recorded kernel
decision. Neither quantity is online scheduling regret, pivot efficiency,
realized objective loss, or a new exact oracle call.

## Scheduling coverage, objective and cost

Every kernel position retains status, missing/error reason, verified feasible
incumbent, initialization reward, exact reward, feature/repair work, search
nodes, original kernel CPU/wall measurements, graph materialization and task
times. A completed normal budget stop remains a normal execution. A programme
error may retain an audited feasible incumbent; its objective and costs appear
only under **retained-incumbent diagnostics**. Normal-only performance is
separate, with explicit coverage and conditional/full-member statistics.

Raw objectives are reported per family. Common Degree comparisons require both
policy and Degree to be normal on the same state and variant; raw gain, named
Degree percentage gain, work ratio and measured CPU/wall ratios are stored.
Zero or absent denominators remain null. No method is divided by the best saved
feasible value and displayed as saturated near-100-percent quality. Raw
objectives from unrelated families are not pooled.

CPU/wall/work come from the already audited execution receipts. They are not
remeasured, not authoring/model costs, and not proof that nominal internal
budgets are equal end-to-end deadlines.

## Relabels, authoring blocks and uncertainty

All five prescribed renamings remain visible. Full five-rename mean/worst
statistics are null when any required measurement is absent; observed-only
statistics retain their measured-rename count. Worst fit/reward means the
minimum; worst work/time means the maximum. The analyzer additionally collapses
five variants inside each original query/state before computing source
bootstrap intervals, so permutations do not inflate the source sample count.

Intervals use **2,000 family-stratified source/pair-cluster bootstrap replicates,
seed 261004**, retaining paired constraint sides, all programme identities and
mapping dependence. Empty resampled denominators remain missing replicates and
are counted. They are source uncertainty conditional on these frozen programmes,
not model-population intervals.

Four block-level common-selector W-minus-R and R-minus-O contrasts are displayed.
Joint W versus W/R/O quality-only contrasts are separately identified as
framework-plus-selector comparisons. Block IDs and null outcomes remain
explicit; a full four-block mean requires all four measurements. Common-source
intervals keep the same four frozen programme outputs together. This conditional
warm-seed study is not independent cold replication, and shared Degree/classical
repair improvements cannot be attributed to LLM guidance.

## Output schema and command

The main JSON has version `v06_R2_EoH_heldout_mechanism_analysis_001`, provenance
metadata, all identities, per-variant/family summaries, five-rename summaries,
source intervals, block contrasts, duplicate-AST dependence and EoH origin counts.
Each input binding includes canonical archive SHA, independent report SHA,
auditor source SHA/checks/errors, terminal/results/protocol/root-release hashes
and scientific source hashes. Both preregistered analysis-config hashes and
the analyzer source hash are bound.

The associated `_compact.json` has version
`v06_R2_EoH_heldout_analysis_compact_001` and the same metadata/frame, plus all
`query_rows`, `pair_rows`, `kernel_rows` and `assignment_rows`. The main report
binds its exact compact byte SHA-256. Full frozen traces stay in canonical
archives; the compact contains analysed, audit-backed numeric records rather
than a second experimental execution.

```powershell
python scripts/analyze_heldout_mechanism_v06.py `
  --r2-archive experiments/runs/v06/<canonical-R2-heldout>.tar.gz `
  --r2-audit experiments/analysis/v06/<final-zero-error-R2-audit>.json `
  --eoh-archive experiments/runs/v06/<canonical-EoH-heldout>.tar.gz `
  --eoh-audit experiments/analysis/v06/<final-zero-error-EoH-audit>.json `
  --out experiments/analysis/v06/heldout_mechanism_analysis_v06_001.json
```

Outputs are exclusive and cannot overwrite an earlier interpretation. Ten
constructed tests pass, including the full 31-identity/13,392-position frame,
failure/byte/source audit guards, rejection before reading partial results,
cluster-preserved sides, missing denominators, signed losses, margin/tie
distinction, paired joint fit, five-rename direction and diagnostic error
incumbents. Production bootstrap is fixed at 2,000; the constructed frame test
uses two resamples solely to check data plumbing. No actual heldout analysis
has been issued during this preparation.

## Provenance hardening after source/toy review

The initial ten-test preparation result above remains historical. The review
identified that an unchanged pre-TEST Boolean did not bind the exact frozen
analysis configuration and that the analyzer checked the auditor's own source
without checking its reported independent-helper closure. The updated analyzer
checks both configuration byte hashes before audit/archive payload reads:

| Frozen analysis configuration | SHA-256 |
|---|---|
| `configs/analysis_v06_001.json` | `52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1` |
| `configs/analysis_refinement_v06_002.json` | `f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769` |

The required audit report's `independent_helper_sha256` must match the complete
current three-helper closure: `verify_matched_llm_v05.py`,
`verify_public_alias_v05.py` and `verify_synthesis_train_v06.py`. Missing, stale
or extra helper bindings fail. These exact bindings are retained in the output
input metadata. No helper or frozen configuration was changed by this update.

Unscaled completion-gap diagnostics retain their existing numeric outputs.
Every mechanism summary now records its contributing families and labels
mixed-family gap sums/means as diagnostics only. Primary paper loss conclusions
must use the existing per-family summaries. Family-stratified bootstrapping does
not make different raw objective units interchangeable; neither signed-gap
statistic is upgraded to actual kernel regret or repair efficiency.

Three added constructed tests reject changes to either config even when its
registration Booleans are unchanged, reject incomplete/stale/currently altered
helper closures, and check mixed versus single-family loss scope. All **13
analyzer tests passed**; the combined analyzer/bridge suite passed **28 tests**.
This was a constructed-fixture check, not an actual heldout analysis. Updated
analyzer SHA-256:
`5acedcb11f0a407e377b98a24162ae9f1864a0e275faa5a28f59ccb323fb54d2`.
Updated analyzer-test SHA-256:
`dccdf09d88f6a24ec10687109064ffc1ce938f153a77d7094c09fa013d3c8eb3`.
Earlier review of the previous analyzer bytes does not certify this revised
version. No real result payloads or incomplete batch outcomes were read, and no
programme, scheduler, oracle or experimental runtime was executed.
