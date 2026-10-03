# Independent review of the score-local heap kernel

Reviewed on 2026-10-03. This is a static correctness review of the separate
`cipheur/score_heap_v04.py` backend. No model, conditional oracle, native solver,
old run archive, or fresh evaluation output was executed or read for this review.
The review does not establish a scheduling-quality gain or a runtime speedup.

## Reviewed source

| Source | SHA-256 at review |
| --- | --- |
| `cipheur/score_heap_v04.py` | `e9af50647ee93ad8fb4944b5b41605a264bcd7648e9a7fdae5422148a08976b0` |
| `cipheur/compiled.py` | `f0f85d0104fbdcdca54fd5adf743e42946812132612cfe590d02315fb8631788` |
| `cipheur/graph_features.py` | `b6f807e9a1a13e8443532247e24fc802815053d375f69ed2c2718a222282a03d` |

Finding: no correctness defect was identified in this implementation. The local
eligibility criterion, deletion frontier, versioned priority entries, global
rescore mode, and failure propagation match the stated conservative design.
The claim is exact equivalence to `schedule_compiled(..., score_slice=True)` on
valid queried inputs under immutable graph data and constraints. Test execution
and performance verification belong to the implementation owner.

## Locality proof

Let A be the active set, v a surviving scored vertex, and N_A(v) its active
neighbors. Let D be the actual active vertices deleted by one kernel step.
Assume D does not intersect `{v} union N_A(v)`.

The current typed DSL has exactly one operation returning a `Node`: `root`.
Consequently every `neighbors` or `singleton` input refers to v. There is no
arbitrary vertex lookup, Node-returning iterator, or higher-order mapping over
neighbor vertices. For a surviving root, `singleton(root)` remains `{v}`;
`neighbors(root)` remains N_A(v) under the stated deletion condition.

Induction on the reviewed typed expression tree then gives the following:

1. `root`, its weight and duration, and numeric constants are unchanged.
2. The two allowed NodeSet sources without `available` are the root singleton
   and its active neighbors. Their values are unchanged. Union, intersection,
   and difference preserve equality of their inputs.
3. Induced edges are determined by that unchanged node set and immutable
   adjacency. Counts, sums, maxima, edge aggregates, clique-cover traversal,
   and deterministic greedy-independent traversal have unchanged arguments
   and immutable weights, so their results are unchanged.
4. Arithmetic and the validated ranking rule preserve those identical numeric
   inputs and therefore the identical floating-point score, including its
   branch decisions and score validation.

Static configuration inputs `station_gap` and `satellite_gap` are also unchanged.
The three demanded base neighbor aggregates are local by the same argument.
Thus any demanded custom expression using only the reviewed operations and no
`available` leaf is safe to cache outside the deletion frontier.

This proof covers neighborhood edge aggregates and generic graph traversals;
it is not restricted to degree and neighbor-weight sums. It also resolves the
root-singleton membership concern: membership only changes for a removed root,
whose priority entry is discarded rather than reused.

## Eligibility and fallback

The implementation uses `program.code.co_names` intersected with validated
feature names to determine every possibly demanded ranking input. This is
conservative across conditional and short-circuit branches. An untaken branch
does not justify local eligibility when its input is global.

Demanded `compatible_weight`, `remaining_count`, any custom expression with an
`available` leaf, or any unreviewed operation selects full residual rescoring.
This remains true for an expression in which global terms mathematically
cancel or are restricted by an intersection. Unused declared features do not
affect eligibility under the existing score-sliced semantics.

The explicit operation whitelist is essential. `depends_on_root` alone does
not prove locality. Adding an arbitrary-node or multihop Node-returning
operation requires a new review before extending the whitelist. Graph weights,
contact times, adjacency, constraints, and the program must remain unchanged
during execution.

## Frontier and heap proof

At a step selecting s, the implementation obtains the actual deletion set
`D = {s} union evaluator.neighbors[s]` before updating the evaluator. These
maintained neighbor sets contain active vertices. For a dynamic local rule it
forms

`F = (union of evaluator.neighbors[x] for x in D) minus D`.

This is exactly the surviving active neighbor frontier of all removed vertices.
It includes vertices two graph steps away from s through a blocked neighbor.
For every surviving v outside F, D is disjoint from its closed active
neighborhood, so the locality proof preserves v's cached score. The evaluator
first performs the full deletion batch; every v in F is then rescored against
the completed residual state. Deleting both endpoints of a neighborhood edge
does not cause score refresh against an intermediate state.

Each active vertex initially has a priority entry with key
`(-score, node, version)`. A refresh increments that vertex's version and pushes
its new exact score. A popped entry is usable only if its node remains active
and its version equals the current stored version. Removed vertices lose their
version entry; stale entries are discarded. Therefore every active vertex has
one current usable score entry, and every usable score equals its current
score-sliced evaluator score. Heap minimum chooses maximum score with the same
lexicographic node tie break as the existing kernel. The version affects only
stale-entry detection for one node and cannot alter ordering between distinct
nodes. The emitted score and active-set count match that step's state.

For a static score, no surviving vertex needs refresh. For a global rule, the
heap is cleared and all active scores are recomputed at each state. This mode
is selected before execution; it is not a response to timeout or failure.

## Numeric and failure scope

The backend reuses the score-sliced `CompiledEvaluator` for all feature and
ranking arithmetic. Heap negation and subsequent trace negation preserve the
queried finite score, including signed zero. Exact score ties retain the string
node order of the existing kernel.

The implementation does not catch budget exceptions or return a partial result
after an evaluator or heap-meter failure. No alternate backend or fabricated
schedule is returned after failure. A comparison-meter exception can interrupt
a heap operation; propagation is the appropriate outcome because that internal
state is not returned as a complete schedule.

Equivalence to the eager `schedule_feature_program` requires all eagerly
evaluated declared features to be valid as well. An unused or untaken custom
feature can divide by zero or overflow in the eager reference while the sliced
backend never queries it. Equality of all error behavior between eager and
sliced evaluation is therefore not claimed.

## Adversarial verification recommendations

Each successful differential case should compare the entire trace, returned
selection, objective value, and feasibility with the score-sliced full-rescore
kernel, rather than only the selected objective value.

| Case | Required observation |
| --- | --- |
| Four-node path a-b-c-d, weights `(10, 1, 1.5, 1)`, rule `weight-degree` | Selecting a deletes a and b; c must refresh from -0.5 to 0.5 and then beat d at 0. Updating only a's neighbors would incorrectly select d. |
| Rules with scores that increase and scores that decrease after deletion | Current-version checks and immediate frontier refresh handle both directions without assuming monotone scores. |
| Deleting the maximum-weight neighbor of a surviving root | The evaluator's lazy maximum heap removes the obsolete maximum and its score heap receives the refreshed value. |
| Removing both endpoints of an edge in a surviving root's neighborhood | Maintained edge count/min/product aggregates reflect one completed deletion batch and match the reference without double subtraction. |
| Exact score ties after refresh, zero weights, fractional weights, and string IDs such as `"10"` and `"2"` | Tie ordering and exact returned action scores match the reference. |
| Custom expressions using singleton(root), unions with neighbors, set differences, and induced edges | Local eligibility is accepted and surviving singleton membership remains valid. |
| Disconnected components with demanded remaining_count or compatible_weight | Remote deletion still selects full rescore and all remaining candidate scores match. |
| Demanded available in an untaken branch or a cancelling/intersected expression | Conservative full-rescore mode is selected even if branch-sensitive or symbolic analysis could prove a narrower dependency. |
| Unused declared global feature | It does not force global mode under score-sliced semantics. |
| Fixed and excluded boundaries, an empty residual, and invalid boundaries | Initial active set and validation match the existing kernel. |
| Controlled budget exception during initialization, refresh, push, comparison, pop, and frontier work | The original exception propagates and no successful or partial schedule is returned. |
| Exhaustive small graphs and seeded randomized graphs/rules | Every action and score agrees for local, static, and global modes. |

The implementation owner reported that the four-node path already passes exact
trace parity. That is a reported check, not an independently executed result in
this review. Further tests should record their own inputs and outcomes.

## Work and claim boundaries

Heap pushes, pops, comparisons, cache writes/deletes, stale validation, frontier
scans, and full-rescore clearing are charged in addition to compiler work.
`_Entry` preserves tuple comparison and charges actual heap comparisons. These
counts are an implementation work proxy, not a machine-independent bit-cost or
wall-time theorem. Sorting, set allocation, and other Python overhead remain
part of measured runtime even where individual instructions are not itemized.

Local invalidation need not improve time for every program or graph. Generic
neighborhood traversals can remain expensive, dense frontiers can refresh most
survivors, and stale heap entries can accumulate. No tight stale-heap memory
bound or general speedup is claimed. Timing or scheduling-quality conclusions
require their own frozen, complete evaluation receipts.
