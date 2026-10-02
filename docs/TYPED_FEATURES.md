# Typed graph features and frozen ranking programs

`cipheur.graph_features` supplies the representation side of the joint
feature--rule interface. Its runtime uses the current conflict graph and active
candidate set. It does not import or invoke an optimization oracle, certificate
generator, candidate provider, or LLM.

## Public interface

```python
from cipheur.graph_features import FeatureRuleProgram, schedule_feature_program

program = FeatureRuleProgram.from_dict({
    "name": "neighbor_structure",
    "features": [{
        "name": "n_edge_min",
        "expression": {
            "op": "edge_min_weight_sum", "args": [{
                "op": "induced_edges", "args": [{
                    "op": "neighbors", "args": [{"op": "root", "args": []}]
                }]
            }]
        }
    }],
    "rule": "weight - conflict_weight + n_edge_min",
    "rationale": "Expose conflicts among the contacts blocked by the root action."
})
values = program.evaluate_features(graph, node, active)
score = program.score(graph, node, active, meter={})
result = schedule_feature_program(graph, program, fixed=(), excluded=())
```

The example is an interface demonstration, not a claim that this ranking rule
is optimal or effective. `program.to_dict()` returns the complete serializable
feature--rule pair. The nine base-feature names match the original `Program`
interface: `weight`, `duration`, `degree`, `conflict_weight`,
`max_conflict_weight`, `compatible_weight`, `station_gap`, `satellite_gap`, and
`remaining_count`. Base sums use `math.fsum` over a deterministic order.

`evaluate_features(graph, node, active, meter=None)` returns the complete
observable numeric interface for a root action. This is the interface that an
offline representation-conflict detector should compare. `score` evaluates the
safe rule on that interface. A scored root must be in the active set, and all
active IDs must be present in the graph.

## Typed operation library

An expression is a nested JSON object `{"op": operation, "args": [...]}`.
Zero-argument operations may omit `args`; serialization inserts an empty list.
Numeric constants use exactly `{"op": "const", "value": number}`.

| Operations | Argument types | Result type | Meaning |
| --- | --- | --- | --- |
| `root` | none | `Node` | Current scored action |
| `available` | none | `NodeSet` | Current active candidates |
| `neighbors` | `Node` | `NodeSet` | Active conflicting neighbors |
| `singleton` | `Node` | `NodeSet` | Singleton if its node is active; otherwise empty |
| `union`, `intersection`, `difference` | `NodeSet`, `NodeSet` | `NodeSet` | Set algebra |
| `induced_edges` | `NodeSet` | `EdgeSet` | Conflicts induced by that node set |
| `count` | `NodeSet` or `EdgeSet` | `Number` | Collection cardinality |
| `sum_weights`, `max_weight` | `NodeSet` | `Number` | Sum or maximum of contact weights |
| `edge_min_weight_sum` | `EdgeSet` | `Number` | Sum of smaller endpoint weights |
| `edge_weight_product_sum` | `EdgeSet` | `Number` | Sum of endpoint-weight products |
| `weight`, `duration` | `Node` | `Number` | Contact attributes |
| `const` | none | `Number` | Bounded finite numeric literal |
| `add`, `sub`, `mul`, `div`, `min`, `max` | `Number`, `Number` | `Number` | Binary numeric operation |
| `abs` | `Number` | `Number` | Absolute value |

Empty sums and empty maxima return zero. Division by zero and any nonfinite
result reject the candidate's evaluation. `graph_operation_library()` returns
the above signatures for a synthesis prompt.

For the active neighborhood $N_A(v)=N_G(v)\cap A$, the two key structural
features are

$$
n\_edge\_min(v,A)=\sum_{\{u,z\}\in E_G[N_A(v)]}\min(w_u,w_z),\qquad
n\_edge\_count(v,A)=|E_G[N_A(v)]|.
$$

Their canonical ASTs are exported as `NEIGHBOR_EDGE_MIN` and
`NEIGHBOR_EDGE_COUNT`. They expose relations among the root's neighbors that
the original degree and neighbor-weight sums do not express. They are graph
statistics; neither is an oracle for the best completion value.

## Safety limits

Additional features must have unique Python-style identifiers and may not
overwrite the nine base names or `min`, `max`, `abs`. Python keywords and names
starting with `__` are forbidden. Each program admits at most six additional
features. Each expression has at most 48 operation nodes and depth eight, and
must have a numeric root. Unknown operations, incorrect argument types, extra
JSON fields, and nonnumeric constants are rejected before execution.

The ranking rule has at most 2,000 characters and 256 Python AST nodes. It
supports numeric `+`, `-`, `*`, `/`, comparisons, Boolean combinations,
conditional expressions, and bounded `min`, `max`, `abs` calls. Its names are
restricted to the exact declared feature interface and those three functions.
Attributes, subscripts, comprehensions, imports, exponentiation, loops, and
arbitrary function calls are forbidden. Evaluation has no Python builtins.
Scores must be finite and have magnitude at most $10^{15}$.

`FEATURE_RULE_SCHEMA` describes the transport shape. Its expression field is
an object; the local typed validator is authoritative for operation types,
complexity limits, and executable safety. A transport's JSON validation alone
does not establish those properties.

## Computation cost and caching

Every scheduling decision constructs one immutable active-set snapshot. That
state memoizes structurally equal operation subtrees. Subtrees dependent on
`root` have the root ID in their cache key; root-independent expressions such
as `available` may be shared across scored actions in the same state. Every
active-set change creates a fresh state. Public standalone `score` and
`evaluate_features` calls each create their own state. No cache can retain a
stale neighborhood from a previous active set.

The returned `feature_work` is a deterministic **instrumented primitive-work
proxy**, not a CPU-instruction count or elapsed time. It sums these declared
units across feature evaluation after cache reuse:

| Primitive | Units |
| --- | --- |
| Executed graph-library operation | One per uncached subtree |
| Active-neighbor membership | One per inspected full-graph neighbor |
| Singleton membership | One |
| Set algebra scan | Sum of both operand cardinalities |
| Induced-edge membership | $k(k-1)/2$ for a set of $k$ nodes |
| Cardinality query | One |
| Weight read | One per read endpoint/contact weight |
| Sum/max aggregation | One per accumulated or compared item |
| Numeric arithmetic | One per unary/binary operation, contact-duration subtraction, or edge term |
| Contact field read | Two for a duration |
| Constraint lookup | Four for the two base gap features and their fallback lookups |

`feature_primitives` reports the breakdown, whose sum equals `feature_work`.
Cache lookup, object allocation, ID sorting, Python interpreter overhead, and
kernel bookkeeping are not extra primitive-work units. Their runtime effects
are captured by time measurements where they occur. This declared proxy must
not be presented as an exact count of all machine operations.

`feature_seconds` measures real feature evaluation with `perf_counter`,
including subtree lookup, traversal, sorting, and numeric construction.
`scoring_seconds` separately measures real safe-rule evaluation. Timings are
nonnegative measurements and vary across runs; only the primitive-work proxy
is intended to be deterministic. Empty active schedules return zero for both
times and work. Initial boundary validation and the feasibility kernel are
outside these two stage timers.

`schedule_feature_program` returns `selected`, `value`, `feasible`, and
`trace` along with these four cost fields. It selects the maximum score with
lexicographic ID tie-breaking, then removes the selected contact and its
conflicting neighbors. Fixed contacts and exclusions are validated by the
original `Graph.available` method. Consequently representation expansion
changes candidate rankings while preserving the same feasibility-enforcing
kernel.

## Verification

`python -m unittest tests.test_graph_features -v` covers exact structural
feature values, base-interface compatibility, state-change cache isolation,
shared-subtree work, typed errors, expression bounds, code-injection rejection,
nonfinite/runtime rejection, fixed boundaries, exclusions, and empty states.
Execution is additionally checked with oracle/certificate/LLM-provider calls
patched to fail if invoked. This verifies implementation behavior and does
not establish held-out scheduling effectiveness.
