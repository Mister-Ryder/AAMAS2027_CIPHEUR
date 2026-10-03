# v04 advanced comparison runner

`cipheur/advanced_study_v04.py` evaluates immutable saved graph inputs and a TRAIN freeze. It does not generate candidates or instances, select winners, repair failed schedules, patch upstream binaries or execute test feedback. Root controls the source inventory, official binary build receipts, freeze validation and server run. This subagent tested only synthetic semantic fixtures; it has not executed fresh/public evaluation inputs or contacted a server.

## Inputs and fixed short protocol

The input is either public benchmark `data.json` with a `public` record list and a `graph` field, or fresh scheduling `data.json` with `test`/`validation` pair lists and `left`/`right` graphs. Public contexts receive IDs `record_id:graph`; scheduling contexts receive `pair_id:left` and `pair_id:right`. Original fixed commitments and excluded contacts are retained for every method. Each graph is checked with `Graph.available(F,X)` before dispatch. No graph is regenerated or filtered by solver performance.

The freeze must have nonempty `programs`, `selection_split=train` and `test_accessed=false`. All frozen programme ASTs are validated before execution. Optional programme-ID and context-ID subsets must be explicit, distinct, existing IDs in the config; their plan is written before outcomes. Scheduling defaults to test only; validation requires an explicit split declaration. Empty requested runs are rejected.

Prespecified extra controls use an `additional_programmes` list. Each entry has `id`, `program` (the complete raw `FeatureRuleProgram` dictionary), and `source_receipt` with `path` and exact file `sha256`, plus optional role/build metadata. The runner validates the hash and checks that the source JSON contains the identical normalized programme definition. Identities must differ from every original TRAIN freeze member and comparison method. Source bytes are copied into `additional_source_N.json`; `additional_programme_receipts.json` records the original source/hash, programme hash and `member_of_original_TRAIN_freeze=false`. An immutable legacy g05 or a previously authored guarded proposal can therefore be an explicitly named fixed control without altering the principal TRAIN freeze. Original freeze bytes are copied unchanged. All extra controls must be declared before fresh outputs; this is not a mechanism for post-test selection.

Each graph context runs the four configured official published binaries through the existing `advanced_baselines.run_solver` adapter: CHILS, M2WIS, Struction and WeightedBR. Each uses seeds 1,2,3 and a declared solver time limit of five seconds. Adapter flags and single-thread settings are preserved; the runner additionally sets OMP/OpenBLAS/MKL/NumExpr worker environments to one thread. The config declares native executable paths; receipts record file SHA256, existence and optional supplied build/source metadata. Missing paths, incompatible inputs and nonzero exits become failed run rows, never substitute algorithms.

With optional `chils_ils_short=true`, the five-second phase additionally runs `CHILS_ILS` with seeds 1/2/3 from the **same CHILS executable**, using the official ILS configuration supplied by the adapter (`-p1 -c1`). This is a second prespecified configuration of one published solver, not a fifth independent published system. The four required executable mappings stay unchanged. The option does not add ILS automatically to the optional 30-second phase; that phase's four method names remain separately declared. ILS failures, CPU/wall use and mean-three summaries have the same accounting as other native rows.

Each selected frozen programme and all five existing fixed classical comparator programmes run through `schedule_compiled(..., score_slice=True)` with a five-process-CPU-second cooperative meter. The five fixed comparators are weight, degree, weighted conflict, the earlier v02 joint formula and structural ratio; they are not described as five separate published SOTA systems. Local improving 1-to-1/1-to-2 search receives two seconds and starts only from the best completed fixed classical comparator. It cannot use a generated programme or advanced solver as initialization. If no such comparator completed, local search is an explicit failure.

Optional `full_interface_programme_ids`, for example `["guided_v04"]`, runs each identical immutable AST again as `guided_v04_full_interface` with `score_slice=false` and the same five-CPU-second cooperative cap. This is a cost/semantics ablation, not an additional synthesis candidate or a change to the principal scorer. Its row stores `same_AST_as` and its backend. `full_interface_parity` compares selected sets, exact values and full decision traces only when both runs complete; a timeout makes parity unassessable rather than true or false. Feature work and CPU/wall use remain independently measured. Full-interface ablation IDs must be an explicit distinct subset of the declared frozen/extra programmes and cannot collide with other method names.

HiGHS receives ten seconds, one thread and the existing weighted independent-set MILP formulation. These budgets have different meanings and are **not a claim of equal total computation**. Record child CPU and wall time from the official adapter, parent adapter overhead, constructive CPU/wall time, local CPU/wall time and numerical-reference time separately. The constructive meter checks every 128 writes; it can overshoot a hard five-second deadline and observed time remains in the row. Preprocessing, import, input encoding, solution verification and reference construction are not silently absorbed into an equal-runtime claim.

## Native failures and exact weight conversion

The official adapter encodes the same conditioned residual with exact integer scaling of the supplied float weights. Integer overflow/unsupported range is an explicit `input_encoding_failure`; the runner does not round, clip or change weights to obtain a solver result. The five-second solver argument is a soft solver budget. A separate hard subprocess wall limit defaults to 30 seconds. Root observed upstream M2WIS failure on one fully reduced edgeless three-vertex residual during native preflight; that observation is a preflight failure, not a reason to patch upstream code or replace that task. Internal exact subroutines can also overshoot a soft five-second limit and hit the hard wall. Such runs remain failures.

Every failed native row retains the complete adapter result, including command, exit status, stdout/stderr and raw solution fields available from the adapter. A successful native set is rechecked against the **original graph, F and X**, and its exact Fraction weight is recomputed. Invalid returned selections are stored as failed rows with the returned adapter object. Constructive exceptions retain any returned result object; interrupted programmes return no schedule. No fallback is credited to any method.

## Reference bounds and primary stochastic summary

The runner independently constructs a deterministic clique partition of the active residual. It verifies complete coverage, disjointness and every required clique edge, then computes

`U = w(F) + sum_C max_{v in C} w(v)`

in exact Fraction arithmetic. `reference.formal_upper_exact`, the outward float, the concrete clique partition and verification status are stored. Every completed method has a graph-feasible set and exact weight, supplying a sound lower witness. If every method fails, the fixed boundary is labelled an **a-priori feasible reference witness**; it is never inserted as a completed solver/programme schedule.

HiGHS dual values, status, gap and warnings are retained under separate numerical fields. A missing HiGHS incumbent stays missing; the runner does not replace it with F. Solver status zero, a numerical gap of zero or equality to a floating dual does not establish a formal optimum. `independent_exact_proof=true` is permitted only when an exact feasible weight equals the independently verified exact clique upper. Its proof kind and witness are retained. Numerical upper values below a verified lower are flagged independently. This proof concerns the provided conflict graph; source-physical feasibility has a separate verifier receipt.

The primary stochastic statistic for each published solver is the **arithmetic mean of the three prespecified seeded rewards**, counting a failed run as zero for all-case accounting. Completed-only reward mean, completed runs, failed runs and completion rate are separately stored. No best-of-three quality enters the declared primary statistic. Normalized quality divides verified exact reward by the sound clique upper; this can be a weak denominator and is not normalization by a known optimum. If the upper is zero, a completed zero-reward schedule has quality one and failure has quality zero. If no formal upper is available, normalized quality is unknown rather than fabricated. Deterministic comparator/programme summaries are single-run values with the same explicit failure accounting.

Cross-context analysis should respect public source graph clusters (unit and hash-weight extensions share one source), paired scheduling configurations and reused temporal seeds across resource regimes. Row count is not an independent-sample count. Dense, C3, DIMACS and SATLIB scopes should remain identifiable. The runner creates per-context evidence; it does not itself certify a general performance ranking or a paper-level SOTA conclusion.

For C3 source graphs, `check_source_graph` reconstructs the source predicates and checks all completed sets if `stable_root` is supplied. Missing source roots or source-audit errors are explicit. A completed graph experiment with an unverified source audit does not establish source-physical feasibility.

## Optional fixed long-budget subset

The optional `long_budget` declaration requires exactly 30 official solver seconds, a nonempty explicit context-ID subset of the short plan, and a hard wall of at least 30 seconds (default 60). It must be written before short results. This phase is stored in `long_results.jsonl` and `long_results_progress.json`, separately from short results. It repeats the same frozen programmes and fixed/reference comparators with their original 5/2/10 budgets; only the official binary time argument changes to 30 seconds. The subset is never chosen from poor/good short outcomes. Do not pool short and long runs or advertise the long phase as equal-budget comparison.

## Commands and example config

```text
python -m cipheur.advanced_study_v04 --data SAVED_data.json --frozen TRAIN_frozen_programs.json --config advanced_config.json --output FRESH_RUN_DIRECTORY --workers 4
```

The native paths below are placeholders. Root supplies the actual official build paths and may include an expected SHA256 and source/build receipt metadata per binary.

```json
{
  "executables": {
    "CHILS": {"path": "/native/official/CHILS"},
    "M2WIS": {"path": "/native/official/mmwis"},
    "Struction": {"path": "/native/official/struction"},
    "WeightedBR": {"path": "/native/official/weighted_branch_reduce"}
  },
  "seeds": [1, 2, 3],
  "official_seconds": 5,
  "hard_wall_seconds": 30,
  "program_cpu_seconds": 5,
  "score_slice": true,
  "chils_ils_short": true,
  "full_interface_programme_ids": ["guided_v04"],
  "milp_seconds": 10,
  "local_search_seconds": 2,
  "splits": ["test"],
  "stable_root": "/path/to/frozen/v51/source",
  "long_budget": {
    "seconds": 30,
    "hard_wall_seconds": 60,
    "context_ids": ["PREDECLARED_PAIR_ID:left", "PREDECLARED_PAIR_ID:right"]
  }
}
```

Omit `splits` or use `["public"]` for public inputs. Omit `stable_root` for non-C3 inputs. Omit `long_budget` when no independently prespecified representative subset is available. Optional `program_ids` and `context_ids` lists are filters on declared identities only. Binary SHA mismatch rejects dispatch; missing binary files remain explicit failures so unavailable systems are visible.

## Outputs, completion semantics and local verification

The run copies immutable original data/freeze/config bytes, normalizes the executable config, saves selected programme definitions and the complete planned context identities/F/X/digests, and records input/freeze/config/module/binary hashes. Per-context graph workers append and flush `results.jsonl`; `progress.json` includes processed contexts and failed method-run counts. Unexpected worker failures generate one explicit failed row for **every requested method/seed**, rather than deleting the context.

`complete.json.execution_complete` means every requested context was processed. `all_requested_methods_completed` is a separate field. Phase receipts retain failed-method counts and output hashes. Completion does not mean solver success, formal optimality, source feasibility or a scientific claim. A run with failures can be a completely recorded experiment; analyses must retain its failure denominators.

Local tests cover saved public/pair schemas, original boundaries and deterministic filters, real exact-scaling rejection, invalid selections, failed native stdout/exit preservation, mean-of-three versus best-of-three, absent numerical incumbents, independent clique bounds versus exhaustive MWIS, extra-source hash/definition checks, conditional full/sliced trace parity, optional three-seed ILS accounting and a multiprocess fixture preserving original freeze bytes and all 15 unavailable native requests. The local bundled Python lacks SciPy, so its tiny full runner fixture correctly recorded a MILP dependency failure; numerical-result verification was tested independently without claiming a local HiGHS solve. Actual official native preflight and fresh/public server execution remain root-controlled, separate evidence.
