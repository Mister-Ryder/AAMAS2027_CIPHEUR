# Frozen-policy heap execution extension

Implemented and checked on 2026-10-03. This is a post-diagnostic execution
extension prompted by the execution bottleneck on public inputs. It leaves
the frozen primary program, degree comparator, `compiled.py`, and original
confirmatory runner unchanged. It makes no scheduling-quality selection.

## Backend and proof

`cipheur/score_heap_v04.py` reuses `CompiledEvaluator(score_slice=True)` and its
incremental feature state, compiler metadata, and work charges. The independent
review is [SCORE_HEAP_REVIEW_V04.md](SCORE_HEAP_REVIEW_V04.md).

The backend conservatively inspects all rule inputs that can be demanded,
including untaken branches. Immutable weights, durations, configuration values,
and current single-root typed expressions without an `available` leaf are
eligible for local caching. Degree and neighbor weight aggregates are local.
Every demanded global input, `available` leaf, or unreviewed operation selects
full residual rescoring before execution. Unused declarations follow the
existing demanded-feature semantics.

After deleting the closed neighborhood D of the selected vertex, the backend
refreshes surviving vertices in the union of active neighborhoods of every
vertex of D. This includes vertices two steps from the selection through a
blocked neighbor. Outside this frontier, the root and all demanded local sets
and values are unchanged. The priority key is exactly `(-score, node, version)`;
version checks discard stale entries and preserve the lexicographic tie rule.

Heap pushes, pops, actual comparisons, validation, cache operations and frontier
scans are charged alongside compiler work. Sorting, allocation, and other
Python overhead are included in measured CPU time, but the work proxy is not a
bit-complexity theorem. No general speedup or stale-heap memory bound is claimed.
Budget exceptions propagate without a partial or replacement schedule.

## Validation receipt

The clean invocation `python -m unittest tests.test_score_heap_v04
tests.test_heap_study_v04 -v` passed **13 tests in 41.075 seconds**. The timing is
the test-suite elapsed time, not a backend comparison.

* All 93 frozen TRAIN-bank ASTs were compared on 300 seeded random graphs with
  n=0..20, five density settings, zero/fractional/extreme finite weights, and
  valid fixed/excluded boundaries: **27,900** complete trace, selection, value,
  feasibility and compiler-metadata comparisons passed. The conservative gate
  classifies this bank as 66 dynamic local, 5 static, and 22 global programs.
* Targeted checks covered distance-two invalidation, increasing and decreasing
  scores, deleted maxima, induced-edge aggregates, deterministic local packing
  and covering, exact ties, singleton/set operations, unused global features,
  global features in untaken branches, and symbolically cancelling global terms.
* Deterministic work caps and cooperative CPU failure checks returned no partial
  selection, trace, or reward. Asymmetric backend failures remained failure
  records; their parity and paired ratio fields were null.
* A real two-worker smoke run used eight small synthetic contexts and generated
  96 complete rows, 48 exact paired comparisons, and zero mismatches. Source ZIP
  hashes, input/freeze/program hashes, result-byte hash, and no-selection receipts
  were checked. Duplicate identities, invalid boundaries, changed source bytes,
  changed ASTs, outcome-selection settings, and output overwriting were rejected.

On a 768-vertex graph of 384 disjoint edges with the unchanged degree rule,
the full scan made 147,840 score queries and the heap made 768. Query work was
1,774,080 versus 9,216; total charged work was 1,777,157 versus 25,321, including
13,028 priority-work units and 7,835 actual heap comparisons. Every trace entry
matched. This fixed diagnostic fixture does not establish public-graph timing.

## Prespecified runner

`cipheur/heap_study_v04.py` and `configs/heap_extension_v04.json` compare the same
frozen `guided_v04` primary and `baseline` degree ASTs using the demanded-feature
full scan and heap. Both selected programs pass the local gate. The primary rule
remains `weight/max(0.000001,weight,nc)`.

The saved populations are the separate SNAP sparse bank (8 contexts) and the
fresh scheduling test bank (456 contexts). Three repetitions use alternating
backend order and reversed program order; each arm is first exactly half the
time across either population. No warmup, reward selection, oracle, native
solver or candidate generation is performed. Each run has a cooperative
**5 process-CPU second target**, checked every 128 meter writes. Primitive and
cleanup overshoot is retained rather than interpreted as a hard deadline.
CPU and wall time include program parsing, evaluator/compiler/heap
initialization, scoring, updates and final graph verification. Worker count and
platform are saved; concurrent CPU contention remains part of the timing scope.

Every assigned run records completion and cost. Successful runs retain exact
trace, selected vertices, original-graph feasibility, floating reward and exact
Fraction reward. Failures retain elapsed CPU/wall time and an error receipt, with
null schedule, reward, trace and completed-work count. Ratios and trace parity
are computed only when both backends complete. Coverage must accompany such
conditional ratios. No retry or budget-triggered backend fallback is allowed.

The config pins both input byte hashes, TRAIN-freeze byte hash and executed AST
hashes. The runner archives source/config/freeze bytes before starting workers
and verifies all imported project-source hashes at each context. Root additionally
freezes the external deployment package before running the extension. SNAP has
96 assigned runs and 48 pairs; fresh has 5,472 assigned runs and 2,736 pairs.

```text
python -m cipheur.heap_study_v04 --data .research/public_sparse_v04_001/data.json --frozen .research/train_v04_frozen.json --config configs/heap_extension_v04.json --out .research/heap_sparse_v04_001 --workers N
python -m cipheur.heap_study_v04 --data .research/fresh_data_v04_002/data.json --frozen .research/train_v04_frozen.json --config configs/heap_extension_v04.json --out .research/heap_fresh_v04_001 --workers N
```

## Byte identities at validation

| File | SHA-256 |
| --- | --- |
| `score_heap_v04.py` | `e9af50647ee93ad8fb4944b5b41605a264bcd7648e9a7fdae5422148a08976b0` |
| `heap_study_v04.py` | `4ac48c2f9d161973b218456c92affa50d49c46595df588a42281bd74cfbe2983` |
| `heap_extension_v04.json` | `be8d2491d7ea0c6fff702d0d3a5f4782c344886ac8e74229444cd7473a715ab3` |
| `test_score_heap_v04.py` | `22cea0ce9736f4edf0686b07ac095c6d183411294bc98d4e1488e3fcf6a96690` |
| `test_heap_study_v04.py` | `c99e4b04b208655d8b0f464a7b3e512fa637405c437114f816ff5d046a784cd3` |
| 93-program fixture | `7189f3a2cf37853cea60937b5ceb26611ebc669bc659a1a4316f730bd428068f` |
| Frozen TRAIN receipt | `2f4379e782413a2ba68222314ec674163f91a5ffcf75c7d74062388dc601987b` |

Actual local input/freeze/program bytes matched every pinned config hash after
validation. No fresh or public scheduling-quality outcomes were inspected to
implement or validate this extension.
