# Replaying V06 evidence

The V06 paper artifact is `paper/CIPHEUR_AAMAS2027_V06.pdf`, with public release
target `v0.6.0`. The supported conclusions and limitations are summarized in
`docs/V06_FINAL_RESEARCH_REPORT.md`. Reading saved results does not require
authoring or rerunning any optimizer. Keep new replay outputs separate from
the canonical reports.

The public compressed server archives are the canonical raw evidence. Large
assessment caches are omitted from Git and reconstructed without evaluation:

```powershell
python scripts/restore_assessment_caches_v06.py R1 R2 catalogue
```

The unchanged 1.49 GB V003 performance archive is supplied as a public GitHub
V06 Release asset rather than an ordinary Git blob. Its canonical path, exact
size, SHA-256 and download URL are in `manifest/RELEASE_V06_ASSETS.json`:

```text
python scripts/fetch_release_evidence_v06.py
```

This restores bytes only. Existing differing files and interrupted downloads
are preserved; it neither reruns experiments nor changes any frozen programme.
All smaller final cloud archives remain directly in `experiments/runs/v06/`.

The full heldout compact exceeds Git's single-blob limit and is retained in
lossless 48 MiB parts. To reconstruct its original exact JSON bytes:

```text
python scripts/package_evidence_v06.py restore --manifest experiments/analysis/v06/heldout_compact_parts_v06_001/manifest.json
```

The containing analysis binds the canonical compact SHA-256. Packaging and
reassembly do not alter data, labels, programme identities or measured costs.

This verifies pinned archive hashes, safe regular-file paths and every extracted
file. Existing identical files are accepted; changed files are preserved and
reported as errors. It neither reruns experiments nor changes candidate selection.
The R1 failed release barrier and R2's separate deployment roles remain recorded.

## Final performance evidence and analysis

The final independent report is
`experiments/analysis/v06/performance_TEST_audit_v06_003.json`, SHA-256
`db7209ad60c4d2f1cff07ec50b2bf26fd5d473153c56d809ff416f6781de22d6`.
It records **71,184,835 checks and zero errors**, covering the complete frozen
52,548-assignment, 302-context frame. Its bound compact rows are
`experiments/analysis/v06/performance_TEST_audited_rows_v06_003.jsonl`.
The report retains the original mathematics source hash and separately names
the process orchestration source; parallelizing verification did not reduce
its scope or change experimental timing receipts.

After restoring the final compact rows, run the prepared statistical analyzer
with a new output directory:

```text
python scripts/analyze_performance_test_v06.py --audit experiments/analysis/v06/performance_TEST_audit_v06_003.json --rows experiments/analysis/v06/performance_TEST_audited_rows_v06_003.jsonl --out output/replay_v06/performance_analysis
```

The analyzer accepts only the final zero-error report and its exact hash-bound
rows. It checks the complete assignment frame, preserves failed and unsupported
positions as null quality, and uses the fixed CHILS full-target seed-1 reference.
It retains all 23 policy identities, three targets and both initialization
tracks. Duplicate ASTs are not removed or interpreted as independent model draws.
The prepared source/pair-cluster bootstrap uses 2,000 draws and seed 261004;
within-source seeds, constraint endpoints and frozen identities move together.
Actual wall/CPU measurements and their coverage remain distinct from nominal
solver targets. Warm standalone measurements charge the common initializer
to each policy rather than amortizing it across the bank.

Outputs comprise `analysis.json` and four context-level JSONLs containing
cohort/identity estimates and paired contrasts. Results remain separated by
population and family; previously exposed C3 models are exploratory. The
command performs statistical analysis of saved receipts, with no solver,
certificate-oracle, TEST-query or model call. See
`docs/V06_PERFORMANCE_ANALYSIS_001.md` for the complete interface and estimands.

The completed canonical analysis is
`experiments/analysis/v06/performance_TEST_analysis_v06_003/analysis.json`,
SHA-256 `839324710784ba71ee40c25ea199b527ff346fb7ec1209f97756ed2d9513aaf9`,
897,176,638 bytes. It and two large identity-level JSONLs exceed Git's
single-blob limit and are retained in lossless parts. Restore the exact
original bytes before opening these optional full outputs:

```text
python scripts/package_evidence_v06.py restore --manifest experiments/analysis/v06/performance_analysis_parts_v06_003/manifest.json
python scripts/package_evidence_v06.py restore --manifest experiments/analysis/v06/performance_identity_estimates_parts_v06_003/manifest.json
python scripts/package_evidence_v06.py restore --manifest experiments/analysis/v06/performance_identity_contrasts_parts_v06_003/manifest.json
```

The small complete supporting report is
`experiments/analysis/v06/performance_tables_v06_002/PERFORMANCE_RESULTS_V06.md`.
It contains all fifteen family/population groups at all three targets, with
quality, source intervals, coverage and measured CPU/wall denominators. Reading
it is sufficient for the reported findings and avoids loading the large JSON.
An apparent table difference with different complete-group coverage is not a
paired quality advantage: at T5, all defined non-C3 warm W-joint comparisons
against same-source Degree/EoH are exact zero. Undefined Grids means and
native encoding limitations remain explicit.

## Other completed evidence

The final heldout analysis is
`experiments/analysis/v06/heldout_mechanism_analysis_v06_001.json`, SHA-256
`a2296b5189abc8adb9bc6e70ef04b0639d4f580929a0e4b64f332c15bef950d5`.
Its restored compact SHA-256 is
`dd8687daeb7176b30f44cb92a1a1804402d39dcb9346e1c3db39303ed19a9653`.
The full scientific tables and all identity/renaming positions are documented
in `docs/V06_HELDOUT_RESULTS_001.md`.

The TRAIN patch-bridge report is
`experiments/analysis/v06/TRAIN_patch_bridge_audit_v06_001.json`, SHA-256
`4f7fd51d216fc9235f3b7f2704de4a17881ee19f891e3d5ea2100f80b7ac07b1`.
It verifies 2,760 scored positions and 159 distinct local conditional queries;
local boundaries are not interchangeable with original full-residual labels.
See `docs/V06_PATCH_BRIDGE_RESULTS.md`. Authentic EoH outcomes and the common
seed origin of all four selected pipelines are retained in
`docs/V06_PUBLISHED_EOH_FROZEN_RESULTS.md`.

## Optional independent re-auditing

The following commands replay existing evidence mathematically. They are
optional and are more expensive than reading the final reports or running the
demonstration. They do not create new experimental observations.

The independent R2 reviewers accept a separate output file:

```powershell
python scripts/verify_refinement_authoring_v06.py --out output/replay_v06/R2_authoring.json
python scripts/verify_refinement_train_v06.py --archive-sha 9ad65026b830a44365fab90655ae3620fcddb6c263e063bde334ae6301c5a185 --out output/replay_v06/R2_TRAIN.json
```

Use new output paths. The TRAIN reviewer requires the restored assessment caches
and preserved R1 independent reviewer modules; it replays saved traces and
mathematics rather than running the production search or certificate oracle.
Authoring verification reads the original frozen packets, responses and native
call receipts. These are retrospective audits, not new authoring requests.

The exact original independent catalogue reviewer is preserved in
`scripts/audit_catalogue_cost_v06_001_original.py`, hash
`1176b283a70f6824f7e9e06c22a0f6b41453c884a5782b08c40482c06d3f7c6f`.
Use the output-redirection wrapper to preserve the frozen audit:

```powershell
python scripts/replay_catalogue_audit_v06.py --out .research/catalogue_review_replayed.json
```

It repeats feature semantics, quotient/witness checks and the explicit
minimum-cost lower-bound certificate, with no master optimization, scheduling
policy, conditional oracle, LLM request or TEST access. Timing and audit timestamp
naturally differ. The cost claim is limited to positive additive standalone
charges over the fixed 53-expression TRAIN catalogue; it is not a runtime or
learned-scalar optimality claim. Scientific panel generation reads the already
verified immutable audit:

```powershell
python scripts/build_catalogue_figures_v06.py
```

Native solver provenance, cloud execution records, authoring receipts and detailed
experiment limitations belong in the separate Markdown reports. The manuscript
contains the method, relevant experimental evidence and scientific interpretation.
