# R2 performance runner: separate roles and two shared initialization tracks

`scripts/run_performance_r2_test_v06.py` is a new runner. It has not executed TEST optimization, read an R2 response/candidate/outcome file, bound actual deployed identities or created a performance source capsule. The original `scripts/run_performance_test_v06.py` remains byte-identical at SHA256 `af66f797aa00d18c3ba9d3ab88866acb988d5980127ed548bb15d7e07a2f31b3`, including its original twelve-genuine-winner barrier. R1's failed barrier is not amended by this separate R2 plan.

Only static R2 deployment code and the pre-generation role configuration were inspected. Future `bind-selections` may run only after independently audited R2 TRAIN selection reports `ready_for_TEST=true`. It requires four joint-eligible witness winners, one from each preselected transport-complete block; twelve requested W/R/O quality-only comparator cells; and the separately frozen original two block0 fixed-bank controls. A quality-only winner may fail the joint gate and retains that fact. A missing quality-only cell stays an unavailable assigned identity with null reward; it is never replaced or relabeled as a proposed winner. Identical ASTs remain distinct assigned authoring identities. Joint and quality-only roles are never pooled.

The independent TRAIN audit is supplied using `--selection-audit` and `--selection-audit-sha256`, with fields `errors=0`, the exact `selection_sha256`, `ready_for_TEST=true`, and `proposed_witness_joint_count=4`. Its full original bytes and hash are retained. The final root release must independently bind that audit, the frozen selections, deployment, source capsule, protocol and input freeze before any server TEST launch. Its `all_source_hashes` must also match every frozen runtime/configuration dependency, including `configs/analysis_refinement_v06_002.json`. That analysis configuration is hash-bound without reading candidate or outcome files. No binding is currently performed. This adapter requirement can be aligned to the independently produced audit's documented schema before a performance source freeze, without reading candidates or weakening the gate.

## Predetermined populations and assignment counts

The primary core comprises 216 new synthetic TEST endpoints, 25 WDP TEST source graphs and three exact-scalable UAI Segmentation TEST sources: 244 contexts. All ten additional signed64-compatible UAI Grids TEST sources are an optional separately labeled numerical-support track. Both original C3 legacy and contact-derived interval tracks comprise 24 contexts each; these use previously exposed background source contacts and are exploratory. C3 tracks are kept separate from each other and from the independent core. Population inclusion uses frozen metadata, not solver quality.

Each source and nominal target 0.1/1/5 seconds has 50 assigned receipts:

- Eleven full-target published native method/seed requests: CHILS/CHILS_ILS/M2WIS at seeds1/2/3, Struction/WeightedBR at seed1.
- One common seed1 CHILS half-target initializer.
- Nineteen repair identities at the full target with common Degree initialization.
- The same nineteen identities supplied the exact common CHILS incumbent, with Degree-feasible extension and bounded repair at half the target.

The nineteen identities are four genuine witness-joint proposed winners, twelve requested nonguarded W/R/O quality comparators, Degree, and two original quality-only fixed controls. Thus the base core has 36,600 requests; ten Grids add 1,500, and each 24-context C3 track adds 3,600. All optional tracks give 302 contexts and **45,300 requests**. Missing comparator positions do not shrink the assigned denominator.

The unchanged performance kernel uses branch scope, 24 patch vertices, four destroyed vertices, one expansion step, 128 nodes per patch, 512 patches, 65,536 search nodes, no work cap and upper pruning. This does not alter the original 120-state R2 TRAIN assessor or .5-second selector. Neither this runner nor its deployment may use new calibration or TEST outcomes to choose candidate programs, blocks, budgets, populations or presentation subsets.

## Objective, coverage and cost semantics

Each input freeze records exact original total source weight. Primary receipts preserve exact original feasible reward; any reward/total-weight fraction is a loose input-derived upper-bound fraction and is never labeled an optimality percentage. A secondary relative comparison is predeclared against full-target CHILS seed1 on the same source/target. Zero, failed or unsupported reference rewards make that ratio null, with their assignment and failure coverage retained. There is no best-TEST reference choice or denominator replacement.

Results must remain separated by synthetic resource/profile families, WDP's five source families, UAI Segmentation, UAI Grids CHILS64, C3 interval and C3 legacy. Native signed32 input limits in WDP/Grids are retained as null, not zero quality. Ordinary anytime repair caps retain actual feasible incumbents, including a legitimate empty prefix with zero reward. Program errors retain any incumbent only as a diagnostic with failed primary quality. Report coverage before conditional quality summaries. Blocks, seeds and duplicate ASTs are nested within shared source graphs, not independent graph samples.

Warm repair retains the supplied feasible CHILS incumbent and must not reduce its exact original reward. It does not compute a second cold Degree candidate or choose the better of two initializers. Native initialization failure makes the associated advanced rows unavailable without fallback. A single initializer is actually executed per source/target; every standalone warm policy is charged the same measured native wrapper self CPU plus child CPU, and full wrapper wall, in addition to its own repair cost. Shared graph preparation/loading and actual batch costs are recorded separately. Equal nominal targets are not equal end-to-end hard deadlines or language-independent computational fairness; native preprocessing/startup/checking and repair overshoot remain explicit.

Execution is server-only with eight workers, persistent per-context journals, a four-hour batch guard and a 30-second native process guard. Every missing predetermined assignment after a guard remains explicitly null without a retry. The runner archives all partial journals, selections, independent audit and release receipts.

## Verification before any actual deployment

Ten mock-only contracts passed. They check the four-versus-twelve role separation and duplicate preservation, missing-quality identity retention, rejection of failed/missing joint winners, independent-audit binding, unchanged original runner bytes, all 150 unique per-source keys and role counts, exactly one shared initializer per target, standalone native/repair cost sums, no warm fallback after native failure, failed diagnostic treatment of a decreasing warm result, and refusal of an unexpected TRAIN source. Solvers and kernels are mocked throughout; the manually defined two-node fixture is not a research experiment. No R2 candidate or result file was read for these checks.
