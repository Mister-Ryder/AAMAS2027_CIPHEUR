# V06 fixed-catalogue cost findings and independent proof review

The completed TRAIN-only study supplies an actual instance of the scoped finite-catalogue theorem: **the full 53-expression catalogue admits a four-feature acyclic interface with exact minimum additive cost 1,371,468**. An independent explicit lower-bound certificate attains the same value. All three SHA-ordered prefixes fail to separate a concrete directed cycle. Their original scientific status remains `unresolved`; completion of all four assignments does not mean all four repairs succeeded.

This review reads the immutable server archive and replays its feature semantics, without rerunning any master, exhaustive optimizer, conditional oracle or scheduling policy. It does not access R2 responses/assessments or TEST. The study's results remain excluded from R2 author packets and selection.

## Fixed scope and source bindings

Archive: `experiments/runs/v06/catalogue_cost_server_v06_001.tar.gz`, 1,092,436 bytes; SHA256 `dab90de26a486d11174ba10f06723c8c02ae277aa2907d643fe36909107ecc05`. All 29 regular files match the untouched extraction in `experiments/discovery/v06_catalogue_cost_server_001/remote/`. The 12-member capsule SHA is `2c19af4c639926e457b9bcdbf5c2eb5dd9b23c23055af748da5217003c7a64f6`; protocol SHA is `b0e9949454d0b4f6bc0516e5b9fdce27b660cc7e4417e766549e48b33c9851ca`. Capsule, runtime, input and completion-receipt hash bindings pass.

The catalogue is the canonical-AST union of features from all 112 statically valid positions among 120 R1 slots, including ineligible candidates; eight invalid-response positions remain recorded. Metadata SHA order defines prefixes of 4, 8, 16 and all 53 expressions, with no selected-program insertion. There are 30 distinct measured feature columns on this finite frame; canonical AST identity does not imply distinct information. This is an adaptive R1 catalogue on observed TRAIN evidence, not a blind catalogue or independent authoring comparison.

Every case uses the same original 120 unit-weight TRAIN snapshots (119 have 32 vertices and one has 28), all 594 strict requirements, and 864 unique certified endpoint occurrences, with the same fixed/excluded boundary per snapshot. All 53 feature tasks and the base-nine task completed. Costs are positive, exact integer sums of freshly initialized per-occurrence operation charges, excluding graph construction, parsing and shared base-nine overhead. They do not measure deployment DAG sharing or optimal runtime. The library has 25 frozen operations; K=6, 128 rounds and 250,000 master subsets were fixed before feature evaluation.

## All four scientific outcomes

| Catalogue | Scientific result / reason | Final features | Current subset cost | Rounds / witnesses | Master subsets | Full-Q nodes / edges / self-loop requirements | Saved exhaustive crosscheck |
|---|---|---:|---:|---:|---:|---:|---|
| SHA prefix 4 | unresolved: inseparable cycle | 2 | 1,379,402* | 4 / 5 | 17 | 610 / 446 / 0, cyclic | 0 feasible of 16 |
| SHA prefix 8 | unresolved: inseparable cycle | 2 | 1,321,237* | 7 / 8 | 58 | 500 / 422 / 0, cyclic | 0 feasible of 247 |
| SHA prefix 16 | unresolved: inseparable cycle | 2 | 1,274,105* | 7 / 8 | 152 | 500 / 422 / 0, cyclic | 0 feasible of 14,893 |
| Full 53 | resolved additive minimum | 4 | **1,371,468** | 9 / 9 | 879 | 650 / 461 / 0, acyclic | no full enumeration; exact cut DP plus independent lower-bound certificate |

\* Costs of current **cyclic** subsets are not successful repair costs or catalogue optima. A smaller partial cost is not an improvement over the resolved interface. None of the three negative cases stopped because of a feature/master/time budget. The production reason is `catalogue_cannot_separate_witness`.

All three prefixes retain the MANN_a9 source-induced snapshot's strict arcs 34→5 and 7→35, each with saved exact margin 1. Joins 5~7 and 35~34 remain exactly equal even after adding **every feature in the respective prefix**. This independently proves that no subset of that prefix can break the closed walk, even without K. The saved exhaustive results agree; their original `unresolved` status is retained rather than retrospectively relabeled as a successful repair.

## Why repeated full-quotient separation matters

The base-nine quotient has 35 nodes, 81 distinct arcs and 90 self-loop requirements. For the full catalogue, seven successive self-loop cuts precede two genuine directed-cycle cuts. After solving the seventh master, self-loops are zero, but the full quotient remains cyclic. Adding the sole separator of the next walk breaks 5~7, yet a different two-arc walk, 34→5 and 3→12, survives through joins 5~3 and 12~34. The final addition distinguishes 12 from 34. Only the ninth master solution passes a full 594-requirement rebuild. Thus a self-loop-only check or a stop after repairing the first directed witness would accept an inconsistent interface on these actual observations.

Let A be the actual available set, N(v) its active neighbors, and T(v)=A\(N(v)∪{v}). The selected features are:

| SHA-order index (zero based) | Expression | Standalone work | Share of optimum |
|---:|---|---:|---:|
| 4 | greedy-independent weight of N(v)∪{v} | 29,964 | 2.18% |
| 16 | greedy-independent weight of A\{v} | 147,167 | 10.73% |
| 27 | number of edges induced by T(v) | 394,682 | 28.78% |
| 29 | clique-cover weight of T(v) | 799,655 | 58.31% |

The continuation clique primitive dominates the additive proxy. Root deletion and neighborhood completion provide complementary distinctions; neither a neighborhood edge statistic alone nor removal of all self-loops establishes realizability. Greedy/clique primitives retain their frozen weight/vertex-ID tie order, so these feature values are not claimed to be invariant under arbitrary vertex relabeling.

## Independent minimum-cost certificate

For necessary cuts C_j, assign nonnegative weights y_4=394,682, y_6=799,655, y_7=147,167 and y_8=29,964 (all other weights zero; witness indices are zero based). Every one of the 53 features satisfies sum_{j:f∈C_j} y_j ≤ c_f. The audit records each exact inequality and slack. Any acyclic repair must hit every necessary cut, so its additive cost is at least sum_j y_j = **1,371,468**. The verified four-feature DAG attains this bound. This proves the fixed-catalogue minimum independently of the production B&B and the server's DP, without rerunning optimization. The bound also holds without K for this particular catalogue; it does not establish minimum cardinality, uniqueness, a scalar-grammar solution or unseen-data behavior.

The server additionally saved complete independent cut-mask DP results for all 27 master rounds, totaling 10/22/22/39 DP states for the four cases. The reviewed recurrence chooses an uncovered cut, removes all cuts hit by a chosen feature, decrements K and minimizes exact positive cost; a feature cannot recur after its covered cuts disappear. The exhaustive checker covers all subsets of cardinality ≤K and skips only cost-dominated quotient tests after a feasible incumbent. For the three infeasible prefixes, all 16/247/14,893 subsets had quotient tests. This reviewer verifies the saved result inventories and feasible DP subsets/costs, but does **not** rerun either optimizer; their full memo/enumeration traces were not saved. The direct inseparable-walk proofs and exact dual certificate close the scientific claims without relying on those summary receipts alone.

## Audit coverage, cost and limits

`experiments/analysis/v06/catalogue_cost_audit_v06_001.json` records **569,686 checks with zero discrepancies**: all 45,792 additional-feature values and 7,776 base values are checked against frozen replay and an independently written uncached interpreter; all 54 work totals and primitive breakdowns match; all concrete strict arcs, cyclic equality joins, cut memberships, accumulated cuts, K constraints, exact costs, every master-round full quotient and final quotients match. Saved strict-enclosure orientation and graph/boundary bindings are checked; the already independently audited original MWIS certificates are not re-solved here. The read-only audit ran for approximately 5.50 seconds locally. Check counts describe this scoped verification, not proof of a secret-free repository or universally correct software.

Production refinement CPU seconds were 0.068/0.122/0.135/0.228 for prefixes 4/8/16/full53. CPU including server independent checking was 0.135/0.886/**54.627**/0.327 seconds. The prefix-16 exhaustive verification dominates elapsed cost; it must not be attributed to the production separator. Feature tasks consumed 11.962 summed CPU seconds, with shared worker input setup reported separately. The entire eight-worker server process took 57.892 wall seconds and 72.722 child user+system CPU seconds. These are observed costs, not speedup or shared-DAG runtime optimality evidence.

The supported contribution is a concrete, repeated full-quotient repair with an independently certified finite-catalogue additive optimum, together with three informative catalogue insufficiencies. The frame is alias-enriched synthetic/source-induced unit data, including MANN_a9; it does not establish a certified obstruction in natural physical scheduling incidence, superiority of the LLM author, schedule-quality improvement, or perfect fit by a bounded scalar rule. No conclusion here changes an R2 proposal or selector.

## Compact manuscript-ready interpretation (optional)

On 594 strict TRAIN requirements, the 53-expression R1 catalogue yielded a four-feature acyclic interface with exact additive cost 1,371,468. Nine full-quotient checks were required: eliminating every self-loop still left a two-arc cycle, and repairing that cycle exposed another. A separate nonnegative weighting of four necessary cuts proves the same lower bound, establishing the finite-catalogue cost minimum without relying on solver termination alone. SHA prefixes of 4, 8 and 16 expressions preserved an unbreakable concrete cycle; exhaustive checks found no feasible subset. These results support scoped representational repair and the need to recheck the entire quotient. They do not establish scalar-rule expressibility, runtime optimality or generalization to natural physical incidence.
