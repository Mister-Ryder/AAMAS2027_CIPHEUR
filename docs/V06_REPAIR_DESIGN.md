# V06 shared bounded repair: implementation and pre-evaluation contract

This is a new algorithmic development, not a reinterpretation of the V05
construction-only algorithm. V05 outcomes and negative published comparisons
remain unchanged. The code below was implemented and checked using small
synthetic unit fixtures; no V06 scheduling TEST or public optimization outcome
was read to choose its settings. Implementation defaults are provisional, not
TRAIN-selected hyperparameters. Publication/release preparation remains paused
while the new research objective is unresolved.

## Framework role and classical component

The unchanged research core is the diagnosis and finite-catalogue refinement
of a declared feature interface through certified quotient obstructions. V06
adds a shared deployment repair component. A typed, frozen programme orders
feasible greedy additions and the pivot vertices of a bounded local search;
it does not determine feasibility, supply an upper bound, or call an LLM or
conditional-value oracle online. The component can replace more than one
incumbent vertex with multiple alternatives, whereas the existing explicit
`swap_search` comparator considers singleton replacements and pairs sharing at
most one blocker. The exact K2,3 unit fixture demonstrates a legal 12-to-15
two-to-three replacement that this existing comparator cannot make. This is a
capability regression test, not evidence of superiority on a scheduling or
published benchmark population.

Clique bounds, independent-set greedy construction, branch-and-bound and
local exchanges are classical ingredients. Existing published references
`lamm2019weighted`, `gellner2021struction`, `grossmann2024mmwis`, and
`grossmann2025chils` provide relevant mature MWIS comparison context; this
module does not reproduce their full algorithms or claim their components as
new inventions. Its framework question is whether a certified/refined typed
programme improves the allocation/order of the same repair work. Published
solvers require a separate complete comparison; their unsuccessful runs and
the V05 negative results cannot be dropped to make that question look stronger.

## Callable API and operational semantics

Owned implementation: `cipheur/repair_v06.py`. Example:

```python
from cipheur.repair_v06 import RepairConfig, repair_schedule

cfg = RepairConfig(
    max_patch_vertices=24, max_destroy=4, max_patches=64,
    expansion_steps=1, node_budget_per_patch=2000,
    max_search_nodes=50000, max_work=None,
    upper_pruning=True, policy_scope="branch",
)
row = repair_schedule(
    graph, raw_or_typed_feature_rule_program,
    fixed=(), excluded=(), initial=None,
    priority="program", seconds=5.0, clock="wall",
    config=cfg, random_seed=1,
)
```

`program` may be an unchanged `FeatureRuleProgram` or its source dictionary.
Dictionary parsing, evaluator initialization and all subsequent execution are
inside the actual CPU/wall timing and the cooperative deadline. Input graph
materialization outside the function must be reported separately by a runner.
`priority` is `program`, `degree` or `random`. Rule-only, no-witness and guided
controls use the same `program` path and differ only in frozen AST. There is no
graph-size fallback to another programme or solver.

`seconds=None` disables the time cap for deterministic node/work unit checks;
`clock="cpu"` uses process CPU and `clock="wall"` uses a monotonic wall clock.
Published native timers use wall targets, so wall mode supports an honest same
nominal-target comparison. Different language/runtime/startup costs still
prevent a claim of identical total computation. Actual end-to-end CPU and wall
must accompany every nominal-budget curve. Caps are cooperative: a bulk
primitive and final witness validation can overshoot, and this overshoot is
included in measured time and charged work, not silently censored.

The common initializer is exact weight/remaining-degree greedy construction,
with lexicographic ties and a lazy heap whose incident-degree updates reproduce
a full scan's decisions. It is independent of the programme for every arm.
A supplied feasible seed is completed by this same initializer. The default
seed is the permanent fixed set; no hidden best-of-bank initializer is used.
A cap during initialization retains the feasible prefix. Consequently V06
uses anytime-incumbent semantics, not V04/V05's full-construction failure-zero
semantics. A normal cap returns `completed=True`, `feasible=True`, and the
best retained incumbent. An invalid programme or unexpected repair error is
explicitly `completed=False`, with its retained incumbent available for audit
and `fallback_used=False`. Runners must report these categories separately,
predeclare error handling, and retain every assigned row.

Useful output fields include `selected`, `value_exact`, `starting_value_exact`,
`initial_value_exact`, `initial_selected`, `initialization_complete`, `status`,
`budget_exhausted`, `global_budget_exhausted`,
`patch_node_budget_exhaustions`, `improvements`, `patch_trace`, `meter`,
`cpu_seconds`, and `wall_seconds`. Exact values are `Fraction(float_weight)`
strings, preserving the input weights' exact binary values. The float `value`
is presentation only. A started patch interrupted even before its enclosure
has a trace row with `upper_exact=None`, the stop stage/reason, no exact claim,
and its unchanged feasible local incumbent. Attempted counts include these rows.
`no_improvement_in_attempted_patches` means no improvement was found under the
reported caps; it does not prove an exchange neighborhood was exhausted.

## Main contrast and separate extension

`policy_scope="branch"` is the primary default. The original fixed/excluded
residual receives common Degree target scores, cached once because that
snapshot is unchanged. Target order, blocker selection, overlapping-blocker
expansion and patch restriction use these same scores in all arms. Typed
programme evaluation is confined to capped local snapshots, avoiding an
uncapped whole-graph programme evaluation that could consume the entire
budget before any repair. A pivot selects the vertex on which to branch;
include-first/exclude-second traversal is common. The programme also orders
one local feasible greedy pass. A second exact weight/degree greedy pass is
common to all arms. Thus the primary contrast tests **local greedy and pivot
priority**, not programme-dependent choice of the region or include/exclude
orientation. Each patch records both orders, greedy-pass values/completion,
pivot count and disagreements with its common exact Degree pivot order.

`policy_scope="target_and_branch"` is an explicitly separate extension that
also changes whole-residual target scores and region restriction. Its global
feature cost is fully charged. It must not be pooled into the primary contrast
or presented as a clean local-ordering ablation. The `expansion_steps=0` family
uses only the initial target's blockers. Positive steps expand destruction
through overlapping blocker sets up to the shared cap. These two finite
neighborhood designs should be compared on TRAIN before their settings are
frozen; no fresh/public outcome may choose them.

The same conditional state has the same region-selection rule and tie order
across primary arms. Later trajectories may diverge because different local
searches find different improving incumbents, or spend their common deadline
differently. It would be incorrect to claim all arms visit identical regions
through an entire run. Random priorities have a recorded deterministic seed;
time-free node/work-capped runs reproduce their decisions.

## Feasibility, enclosures and exactness scope

Let I be the current independent incumbent satisfying permanent F and X.
Choose movable D subset I with D disjoint from F. Set Fout = I minus D and

`R = V minus (Fout union N(Fout) union X)`.

I's independence and disjointness from X imply D subset R. Any independent
J subset R is disjoint from Fout and has no edge into Fout; hence
`Fout union J` is globally independent, contains F, and excludes X. The old D
is a feasible local witness, so initializing local best to D prevents any
loss. An exact strictly positive gain is committed only after checking the
replacement against the original graph and F/X boundary. No floating epsilon
is used for gain acceptance. Interrupted searches return their best known
feasible witness, and final proof validation cannot discard an improvement
already found immediately before a cap.

When R is too large, the shared restriction retains all D, the target when
space permits, and highest-ranked remaining candidates up to the cap. It
returns R' with D subset R' subset R. A bound and an exhaustion proof concern
**R' with Fout fixed**, not R, a larger exchange neighborhood, or the global
MWIS. `full_region_size`, `patch` and `restricted` make the scope inspectable;
`exact_optimum_claimed=False` is unconditional for the schedule result.

A greedy clique partition C of the induced patch gives
`U(R') = sum_C max_{v in C} w(v)`.
Every independent set takes at most one vertex from each clique. Disjoint
coverage and clique membership therefore prove this exact rational upper
enclosure. A completed root bound U <= w(D) proves that this restricted patch
cannot strictly improve D, permitting a sound skip. Dynamic clique partitions
also bound each search node's remaining mask; `chosen_value + U(mask) <= best`
permits optimization pruning. Programme scores do not enter either proof.
`root_upper_exact` preserves the clique partition's sum even when a completed
local search tightens `upper_exact` to the smaller optimum. In that case
`upper_method="exhaustive_restricted_search"` identifies the proof; the larger
root cover is not falsely presented as an optimal clique enclosure. The root
enclosure stays sound after partial search. Exactness is declared
only if the verified feasible witness equals that root bound, root pruning
closes the patch, or the full local search frontier was normally exhausted.
An exception after popping a node is **not** a frontier-exhaustion proof.

`upper_pruning=False` disables both root skipping and every dynamic
clique-envelope optimization cut; it still computes the same root enclosure
for reporting and runs the same feasible greedy passes. It is not a switch
to a weaker weight-sum pruning algorithm. ON/OFF share the conditional patch,
starting D, scores, traversal and all budget limits. Equal wall/node budgets
can produce different progress because pruning changes cost. Restricted
exactness and root-pruned counts must not be described as a global certificate.

## Cost, evaluation and honest research status

The meter charges input validation, exact weight conversion, initializer
heap/degrees/deletion updates, targets/blocker scans, expansion/restriction,
local adjacency, compiled feature operations, greedy passes, clique bounds,
search nodes, and local/commit/final validation. Feature charges use the
existing demand-driven compiler with `score_slice=True`. Work is a declared
operation proxy, not FLOPs; actual CPU/wall is the separate empirical cost.
Final checks are charged but cannot be interrupted after they would discard
a known valid witness. No stage receives a fresh independent time allowance.

TRAIN selection must assess complete retained feasible schedule reward and
actual cost, alongside pruning/search work and initialization coverage; all
negative and error/capped rows stay visible. Config, programmes, selected IDs,
seeds, budgets and clock mode must freeze before new TEST. The old full-residual
certified preference labels do not certify the programme's local-patch pivot
preferences: those are different boundaries. Report quotient/interface gate
and scalar label fit separately from empirical repair quality. Neither a
gate pass nor local exactness guarantees global quality, solver dominance,
or an LLM population-level advantage. This development has no such empirical
claim yet.

## Verification receipt

### Fixed TRAIN Degree feedback runner

`scripts/run_repair_feedback_v06.py` is a separate new runner; it does not
modify the old research modules or frozen source capsules. It fixes branch
scope, wall target 0.5 seconds, patch cap 24, destruction cap 4, patch count 32,
one overlapping-blocker expansion, 128 search nodes per patch, 4,096 total
search nodes, work cap 200,000 and upper pruning ON. These settings were
declared by root before feedback; 128 intentionally permits a capped patch
where ordering could matter. No empirical advantage is assumed from that
rationale. Subsequent authoring arms must share this configuration and clock.

Prepare and verify/run are separate commands:

```text
python scripts/run_repair_feedback_v06.py --data DATA.json --out NEW_FEEDBACK_DIR --workers 8 --prepare-only
python scripts/run_repair_feedback_v06.py --data DATA.json --out NEW_FEEDBACK_DIR --workers 8 --run
```

The existing V06 `records` inventory can contain 120 TRAIN and 72 TEST graph
snapshots: the runner selects only rows explicitly marked `train`, binds the
whole original input's byte hash and the selected ordered identities, and
never materializes or scores another split. TRAIN pair dictionaries or explicit
TRAIN contexts are also accepted. `--split` and workers must match the receipt;
non-TRAIN execution is rejected both at the parent and worker boundary.
Preparation validates selected graph identities/F/X without repair execution.
`training_contexts.json`, `protocol.json` and `freeze_receipt.json` pin exact
bytes and the actual static runtime dependencies; unrelated authoring modules
are not part of that inventory. Running refuses changed bytes, source or config
and refuses overwriting prior feedback. A source snapshot captured before the
runtime imports is checked again before prepare/run, refusing changes after
startup. Prepare creates a new output directory; run reuses it. The runner
does not tar/package results automatically: archiving is a separate deployment
step, whose parent directory must exist before creating the archive.

Workers save every assignment to `results.jsonl`; graph materialization is
timed separately from the kernel, and actual end-to-end task CPU/wall is also
retained. `progress.json` and `completion.json` distinguish returned assignments,
kernel errors, normal budget caps, feasible incumbents and initialization
completion. Neither assignment completion nor a feasible incumbent implies
an exact/global optimum. No reference oracle, LLM, programme selection or TEST
execution occurs. This agent ran only runner help and synthetic/mocked unit
checks locally; the 120-state feedback execution is delegated to the server
runner agent after a separate source/config freeze.

Run:

```text
python -m unittest tests.test_repair_v06 tests.test_compiled_v03 tests.test_cooperative_budget_v03 -v
```

The kernel suite has 12 meaningful tests plus three TRAIN runner contract tests.
Independently enumerated original-edge
subsets check every four-vertex graph (64 graphs), three weight sets including
decimal binary and large-weight near-tie cases, four node caps, both pruning
modes: 1,536 patch comparisons. Forty random 3–8-vertex graphs add 240
restricted/F/X comparisons. Exact outcomes equal enumerated patch optima;
partial lower/upper enclosures, clique partition coverage/edges, global
feasibility and monotonicity are checked. Every attainable work stop on two
fixed fixtures is also checked, including a 15-versus-16 case where both greedy
passes are suboptimal and an interrupted popped root must not be called exact.

Further checks cover a genuine two-to-three move, protected/excluded vertices,
D-preserving truncation, ON/OFF node reductions, exact heap/full-scan parity,
the common first patch across arms, local-only feature evaluation, pivot-order
effects, random-seed reproducibility, a useful last improvement retained after
a cap, zero CPU/wall caps, explicit invalid-programme failure, no fallback,
and JSON serialization. Runner tests reject forbidden splits, prevent other
split graphs being materialized, verify immutable input/source/config binding
without executing research, and distinguish mocked assignment/kernel outcomes.
The 11 unchanged compiler/cooperative-budget regression tests were also run:
26 tests passed together on the local Windows environment.
These tests are unit verification, not research runtime evidence. No full
repository/research suite was rerun.
