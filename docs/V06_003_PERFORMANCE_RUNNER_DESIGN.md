# V06_003 additive performance adapter

This adapter was implemented without reading candidate files or observed R2/EoH outcomes. Root subsequently registered its source and protocol before EoH outcomes and before any TEST optimization. No deployment has been bound, and TEST launch remains subject to the root release.

The canonical completed registration is `experiments/discovery/performance_r2_eoh_test_v06_003_registered_001`: protocol SHA `59395b0b7f4c8460da8e58bcdccaa292b189a627716e1e050c52b7a659ba4cfa`, freeze SHA `bd3f842113f776d2cb3909fcd8ce1b454d41da689bf96050d7c10541e1255882`, source ZIP SHA `b08d95b17d571a19a062109726e0bb7f4f80322addcd099b73b8f3568c494f09`, capsule receipt SHA `bc445d536ba61d9a4f03c8c5f9b0bea5fe29b536e9e3736773992327722b6f25`. Source SHA `785d8d262082b62b301e1b6681dc0d98b347b8ab17ba948144b761d52b0cefc9` is unchanged.

The originally documented relative `--study` registration command failed at `Path.relative_to(ROOT)` after writing a partial protocol/freeze/source ZIP, before any solver or candidate binding. Root preserved that original partial directory, `experiments/discovery/performance_r2_eoh_test_v06_003`, and completed a separate registration with an absolute study path. This report corrects command examples only; no source, frozen protocol or partial artifact was changed.

The new entry point is `scripts/run_performance_r2_eoh_test_v06.py`, with `configs/performance_r2_eoh_v06_003.json`. It imports only the original R2 pure identity-validation function. Original R2 runner SHA `21824f6b3f7ccaa348d53bd67bbe50e1073cec5d021fad5462ad7bf1379ab5fe` and original R1 runner SHA `af66f797aa00d18c3ba9d3ab88866acb988d5980127ed548bb15d7e07a2f31b3` remain unchanged. Original R1/R2 protocols and their barriers are not edited.

## Roles and assignment matrix

All original nineteen roles remain separate: four genuine R2 W joint winners, twelve requested nonguarded R2 W/R/O quality positions, two original fixed-bank block0 quality controls, and shared Degree. Four additive `published_EoH_DSL_quality:run_0..3` positions are nonguarded published quality baselines. They do not satisfy, replace or pool with the four-W joint barrier.

EoH origin is explicit in deployment and every emitted policy row: `shared_R1_warm_seed`, `genuine_EoH_author_slot`, or `missing`. A retained seed winner is not relabeled as newly authored code. A missing run remains a requested null identity in both tracks/all budgets. Duplicate ASTs retain their separate requested identities without creating independent graph samples.

The fixed full scope is 302 sources: 216 fresh synthetic TEST, 25 WDP TEST, 3 common-supported UAI Segmentation TEST, 10 exact-LCM CHILS64-only UAI Grids TEST, and two separately labeled previously exposed C3 tracks of24 contexts each. No quality pooling crosses these populations or the two C3 model semantics.

At each source and nominal wall target `.1/1/5`, the matrix is11 full native requests +1 shared CHILS-half initializer +23 cold policy requests +23 warm policy requests =58. Across three targets this is174/source and52,548 total, adding7,248 EoH policy requests to the unchanged R2 matrix. Native seeds/methods, signed32 unsupported-input nulls, weight transforms, repair caps, eight workers, native30s guard and whole-batch4h guard are preserved.

Warm pipelines reuse one CHILS(seed1,T/2) initializer per source/target. Each policy is still charged the same measured standalone native preparation/startup/self+child CPU/wall plus its own repair cost. Actual shared execution cost is separately reported. Failed/unsupported initializers make the associated warm requests unavailable with null quality; they do not silently use Degree. Every normal warm incumbent must retain reward at least its supplied feasible native seed. These are nominal wall-target comparisons, not equal end-to-end deadlines or language-independent CPU fairness.

## Binding and release

The base R2 selection and independent audit must first pass its unchanged pure four-W barrier. The additive final EoH selection must retain all32 original positions and exactly four run identities. Two independent EoH audit receipts must each contain `errors:0`, the exact `selection_sha256`, `TEST_accessed:false`, and distinct `audit_phase:"authoring"` / `audit_phase:"train"`. All original audit bytes are copied, never synthesized or rewritten by the runner. If the independent audit uses another documented schema, a reviewed source adapter is required before any performance source freeze.

The root-owned TEST authorization must bind the existing protocol/source/deployment/R2 selection/control/input/audit fields, `all_source_hashes` (including the R2 analysis config and this additive config/source), and the three added fields:

```
published_selection_sha256
published_author_audit_sha256
published_TRAIN_audit_sha256
```

The same three added bindings are independently checked in both server-launch and worker-launch paths. No TEST execution can be authorized by the adapter itself.

For replay on a fresh checkout, `ABS_PROJECT_ROOT` must be the absolute project directory. The completed local registration already exists and must not be replanned. The registration template describes its root-executed step; later binding and Linux launch also use an absolute study path:

```text
python scripts/run_performance_r2_eoh_test_v06.py plan-only --study <ABS_PROJECT_ROOT>/experiments/discovery/performance_r2_eoh_test_v06_003_registered_001 --include-c3 both --include-uai64

python scripts/run_performance_r2_eoh_test_v06.py bind-selections --study <ABS_PROJECT_ROOT>/experiments/discovery/performance_r2_eoh_test_v06_003_registered_001 --selection <R2_SELECTION_JSON> --selection-sha256 <R2_SELECTION_SHA> --controls <ORIGINAL_CONTROL_SELECTION_JSON> --controls-sha256 <CONTROL_SHA> --selection-audit <R2_INDEPENDENT_TRAIN_AUDIT_JSON> --selection-audit-sha256 <R2_AUDIT_SHA> --published-selection <EOH_FINAL_SELECTION_JSON> --published-selection-sha256 <EOH_SELECTION_SHA> --published-author-audit <EOH_INDEPENDENT_AUTHOR_AUDIT_JSON> --published-author-audit-sha256 <EOH_AUTHOR_AUDIT_SHA> --published-train-audit <EOH_INDEPENDENT_TRAIN_AUDIT_JSON> --published-train-audit-sha256 <EOH_TRAIN_AUDIT_SHA>

python scripts/run_performance_r2_eoh_test_v06.py prepare-inputs --study <ABS_PROJECT_ROOT>/experiments/discovery/performance_r2_eoh_test_v06_003_registered_001 --out <ABS_PROJECT_ROOT>/output/performance_r2_eoh_test_v06_003

python scripts/run_performance_r2_eoh_test_v06.py server-run --study <ABS_PROJECT_ROOT>/experiments/discovery/performance_r2_eoh_test_v06_003_registered_001 --out <ABS_PROJECT_ROOT>/output/performance_r2_eoh_test_v06_003 --authorization <ROOT_TEST_RELEASE_JSON>
```

The last two are Linux-only. The root executed the canonical absolute registration step. Identity binding and TEST execution have not been run at the time of this update; separately authorized input preparation is recorded below.

Root later separately authorized input-only server preparation. It finished in the isolated `/root/autodl-tmp/aamas2027_v06_performance_r2_eoh_test_003` workspace:302 materialized graph files, zero optimization calls, no deployment/candidate files uploaded, and exit0 without guard. One graph-preparation process was paused during an EoH fitness transaction and resumed, with both process-group events preserved. Actual preparation wall169.775s includes that pause; child user CPU163.986s and system CPU are retained in the original receipt.

Exact receipts/inventory/freeze are downloaded under the canonical registration's `server_input_preparation` directory. Input freeze SHA `42f7e9606499e379063c81d66d96beaa9cefb77be57be66c6076784ff33e4689`; inventory SHA `f4d204d75ee2eb9e05b40405ae25bd47a0b4c3714df27a28a0b4930b857cc917`. Server verification checked all302 actual graph-file byte hashes, while the local transport check verified those frozen mappings, unique IDs, the complete population counts and52,548 future assignments. The graph archive is60,932,371B, SHA `a16f618b5e3290a2dfa52ba1b592fb488d9e1a12935222efa379d130a7a5d425`, now downloaded as `experiments/runs/v06/performance_v003_input_preparation_server_001.tar.gz` through a separate read-only connection that left the fitness controller available. A local streaming check again verified every302 actual archived graph-file byte hash plus exact original inventory/freeze byte equality, without reconstructing graphs or invoking a solver. Its original receipt is `server_input_preparation/local_archive_download_verification.json`. These are input-preparation records, not experimental quality results or TEST method execution.

## Verification

Five small mock-only tests pass in `tests/test_performance_r2_eoh_runner_v06.py`. They verify23 role identities and explicit seed origins; missing published nulls; rejection of incorrect audit phases/hashes or a failed proposed joint gate;174 unique requests with36 native and138 repair mock calls; exact common-initializer reuse and standalone warm-cost charging; and preservation of both original runner hashes. Only a two-node manually authored fixture is materialized. The tests never invoke a real solver, inspect research outcomes, or create a frozen performance study.

Quality definitions are unchanged: exact original feasible reward; input-total-weight fraction as a loose source-derived upper-bound fraction, never optimum percentage; secondary ratio against the fixed full-target CHILS seed1 when available. Unsupported requests and failed rows remain null with coverage reported before quality. No best-TEST denominator, post-outcome cohort change or selection is introduced.
