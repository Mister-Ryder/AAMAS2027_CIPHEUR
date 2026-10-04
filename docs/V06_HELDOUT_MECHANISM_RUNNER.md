# V06 held-out mechanism and ID relabeling runner

New module: `cipheur/heldout_mechanism_v06.py`. This adds an outcome-free runner; implementation and tiny fabricated-graph tests do not execute or inspect real V06 TEST outcomes. Research `prepare` and `run` entry points refuse non-Linux hosts. No LLM or conditional-value oracle is imported/called by this runner's execution path.

Preparation requires explicit selection, controls-selection and original TEST `results.jsonl` SHA-256 values. It verifies all 120 original authoring positions were assessed, exactly twelve genuine TRAIN winners cover four whole transport-complete blocks, and no fallback/TEST selection occurred. It also requires the block0 quality-only winner from each fixed control bank, all eight enumerated structural controls, and the frozen fixed Degree reference. TEST certificates must have been generated under the same twelve-winner selection hash and original frozen 72-state query plan. Missing cells, controls, labels or planned-query bindings stop preparation; no new selection or replacement is performed.

```text
python -m cipheur.heldout_mechanism_v06 prepare --help
python -m cipheur.heldout_mechanism_v06 run --registration NEW_REGISTRATION --out NEW_OBSERVATIONS
```

The `prepare` arguments specify `--plan`, `--selection`, `--selection-sha256`, `--controls-selection`, `--controls-selection-sha256`, `--certificates`, `--test-certificate-sha256`, `--authoring-protocol`, `--controls-registration`, `--control-bank`, `--control-freeze`, `--relabel-config`, `--kernel-config`, `--out`, and optional `--workers`. Their full paths/bytes are bound in the new registration and source capsule. Preparation performs source/input/isomorphism checks only. It refuses an existing registration; execution writes a separate new directory and also refuses overwrite. Do not run research execution until the controller authorizes it.

All records remain `split='test'`. The original TRAIN checker is not called with altered splits. A pure TEST helper uses the same compiled feature evaluation, base-nine retention, syntactically demanded extra features, full combined quotient, declared-feature diagnostic and numerical margin as the original frozen assessor. Ties/unknowns remain query rows without artificial fit labels. Every planned quota shortfall is retained. Interface error is recorded independently of kernel observations; no TEST gate chooses a winner.

The baseline plus five bijective ID permutations follow `configs/relabel_v06_001.json`. A source cluster uses one SHA-ordered mapping on both paired configurations. Contact reward/resource/time/order, edges, fixed/excluded commitments, competitor/preferred IDs and component witnesses are mapped exactly; signed interval numbers are unchanged. Original certificates therefore transfer by graph isomorphism without extra oracle queries. Deterministic ID-based primitive/search ties may still change features or scheduling behavior; no invariance is presumed.

All 23 comparator identities are evaluated on all six variants: twelve selected programs, fixed Degree, two TRAIN quality-only controls, and eight original enumerated controls. The first fifteen form the primary mechanism comparison; the eight extra identities preserve the full relabel bank and its original baseline. Identical ASTs retain separate requested rows and independent executions rather than fabricated reused timing. The original .5-second nominal-wall/200,000-work configuration, bounds, initializer and branch scope are unchanged. Normal budget stops retain the verified incumbent; unexpected errors and actual CPU/wall/materialization time remain visible.

Per-identity output includes all strict/query checks, base/demanded aliases, complete quotients, reversal/preservation versus tie/incomplete classification, interface work, every state kernel result, exact reward, status and time. The summary records original, five-permutation, mean and worst strict-fit counts; incomplete measurements produce null summary values. Permutations and paired endpoints remain dependent observations within the original source cluster. No quality or synthesis claim follows from runner availability.

Tiny tests only:

```text
python -B -m unittest tests.test_heldout_mechanism_v06 -v
```
