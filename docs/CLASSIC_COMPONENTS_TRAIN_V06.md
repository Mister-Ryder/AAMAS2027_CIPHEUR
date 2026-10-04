# Classical-component TRAIN calibration V06

This separate calibration tests classical initialization and the unchanged common repair kernel. It does not evaluate any LLM-generated program. Its outcomes are excluded from R2 author packets and candidate selection. The original 1,008-request public calibration, original 120-state evidence/common feedback and candidate assessments remain unchanged. No TEST optimization is authorized by this registration.

## Frozen design

Registration: `experiments/discovery/classic_components_train_v06_001/registration.json`; configuration: `configs/classic_components_train_v06_001.json`.

The source capsule is `experiments/source_snapshots/v06/classic_components_train_v06_001_source.zip`, SHA256 `67526e9f78afe90008945c8747d3be0003cb22d64014d94b29c636c6f634ed11`. The configuration SHA256 is `15cf938268afbd5cfcba666b90a9969914de314ca616da74f46b14f964ef1492`. All source/input/configuration bytes were locked before this calibration produced outcomes.

All 25 WDP TRAIN source graphs and all seven exact-LCM CHILS64-compatible UAI TRAIN source graphs are included. The UAI sources are Segmentation 12/13/16, Grids 25/28/29 and ProteinFolding 11. The last four had not been optimized in the original calibration. This is metadata-based numerical-support inclusion, not selection by solution quality.

The nominal wall targets are 0.1, 1 and 5 seconds. Each source/target has ten retained requests:

- CHILS at the full target, seeds 1/2/3.
- CHILS at half the target, seeds 1/2/3.
- The corresponding same-seed CHILS half-target incumbent, supplied to Degree-priority repair for the remaining half target.
- Degree initialization and repair at the full target, seed 1.

There are 32 sources × 3 targets × 10 requests = 960 assignments. CHILS half-phase results are shared only with their corresponding warm pipeline. Their measured native wrapper self CPU, child CPU and wall cost are charged once to that standalone warm pipeline, in addition to repair cost. Actual shared graph loading/preparation and shared context costs are retained separately.

Repair parameters are unchanged: branch policy scope, 24 patch vertices, four destroyed vertices, one expansion step, 128 nodes per patch, 512 patches, 65,536 total search nodes, no work cap, upper pruning enabled. The kernel SHA256 is `c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3`.

Warm repair validates and retains the supplied CHILS incumbent, then Degree-feasibly extends it and attempts bounded repair. It does not compute a separate cold Degree candidate or choose between two initializers. Every returned warm reward must be at least its native initial reward. A missing or failed native initializer yields an explicit unavailable warm request; it never triggers a hidden fallback.

Original UAI Fraction weights are multiplied by their exact source LCM before integer encoding. WDP original integer weights are preserved and the clique graph is exactly complemented for MWIS. The largest included scaled total is 17,049,568,327,944, below both the signed64 limit and the exact-integer binary64 range. There is no float rounding, GCD reduction, graph reduction or modification to original objectives. Reported rewards divide by the original source LCM.

Native targets refer to the solver's internal wall clock; repair uses its cooperative wall timer. Native encoding/startup/output validation and repair overshoot remain in measured costs. The native process safety guard is 30 seconds; the batch guard is 3,600 seconds, with partial journals and every missing assignment retained. These are nominal target comparisons, not equal end-to-end hard deadlines or equal C++/Python computational budgets. Seeds are nested within each source and are not independent graph samples.

## Execution

Server-only execution uses eight workers in an isolated directory, reserving half the server's 16-CPU quota. Before launch, a read-only inventory found no other active research processes and approximately 8.8 GB used under the 60 GiB memory quota. The detached launcher PID is 54000; worker PID is 54057. The graph protocol SHA256 is `41a0108ea122efc65fa3bf10c690bf5d25fb7ef5f192d75361ec29e582a2d734`.

Four mock-only orchestration tests passed before registration. They verify all request keys and phase reuse/cost sums, refusal of TEST contexts, unavailable-initializer handling without fallback, and rejection of a decreasing warm reward. They perform no actual optimization.

The batch is complete: 960/960 assignments returned, all with independently checked feasible incumbents. No native, runner or safety-guard failures occurred and no retries were made. The policy batch took 220.018 seconds; shared verification/preparation took 136.173 seconds; the recorded preparation-plus-execution interval was 356.383 seconds. Archiving and transport are outside that execution interval.

The immutable archive is `experiments/runs/v06/classic_components_train_v06_001.tar.gz`, 52,792,894 bytes, SHA256 `d5f49828494d55ffd0f725e493ad9dee61f335ef8e49feeada091635c66abd2c`. Results SHA256: `d44fa7cd2a7552ba38297ca2460f1ca30f713501dc7b7236c42e34efe50f6aae`.

`scripts/check_classic_components_train_v06.py` checks raw source mappings, every exact original-objective reward and feasible selected set, all 960 assignment keys, all native seed/command/saved-output bindings, all paired initializer identities and standalone phase-cost sums. It completed **160,890,742 checks with zero errors**. This is a separate audit implementation by the execution agent, not a separate-person audit. It imports no project runtime and calls no solver, kernel or oracle. The machine-readable audit is `experiments/analysis/v06/classic_components_train_check_v06_001.json`.

The 576 native receipts are checked feasible incumbents. Warm repair stops are 150 time-budget, 26 patch-limit and 112 no-improvement stops. Cold repair stops are 58 time-budget, 10 patch-limit and 28 no-improvement stops. These are normal anytime stops retaining actual feasible incumbents, not missing outcomes. Some short-target cold runs legitimately return the empty feasible prefix with zero reward; these are distinct from unsupported inputs or failed runs.

## Descriptive component findings

Across all 288 paired source/seed/target requests, warm repair improves its matching half-target CHILS incumbent in **4 cases**, ties in **284**, and decreases in **0**. Against the same-seed full-target CHILS result, warm repair is better in **2**, equal in **222**, and worse in **64**. These counts do not establish a reliable quality advantage over full-target CHILS. The experiment contains no LLM program, so it cannot establish an LLM benefit.

| Source family | Paired source/seed/targets | Warm vs half CHILS: better/equal/worse | Warm vs full CHILS: better/equal/worse |
|---|---:|---:|---:|
| Grids | 27 | 1 / 26 / 0 | 1 / 9 / 17 |
| ProteinFolding | 9 | 0 / 9 / 0 | 0 / 6 / 3 |
| Segmentation | 27 | 0 / 27 / 0 | 0 / 27 / 0 |
| WDP 1xx | 45 | 2 / 43 / 0 | 0 / 35 / 10 |
| WDP 2xx | 36 | 0 / 36 / 0 | 0 / 28 / 8 |
| WDP 4xx | 36 | 0 / 36 / 0 | 0 / 35 / 1 |
| WDP 5xx | 54 | 0 / 54 / 0 | 0 / 45 / 9 |
| WDP 6xx | 54 | 1 / 53 / 0 | 1 / 37 / 16 |

The JSON preserves exact per-source rewards and actual phase timing summaries at every target. Raw quality is not pooled across different objective families, no optimum is asserted, and these nested seed counts carry no population significance claim. All results remain excluded from R2 author packets and selection, and no TEST optimization was performed.
