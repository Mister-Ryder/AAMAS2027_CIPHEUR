# Independent formal review of v03 repair and certificate claims

Review date: 2026-10-03. This audit reviews the branch-and-bound master introduced after the initial v03 implementation. It combines a proof audit, source inspection, an independent mathematical review, and exhaustive reference checks. Passing tests are evidence about implementation behavior, not substitutes for the proofs below. No server experiments, external models, or credentials were used in this review.

## Verdict and exact scope

The exact cycle-join separation argument is sound. The current branch-and-bound hitting-set master preserves the conditions needed to certify an additive optimum after a full quotient DAG check. The weighted clique envelope and finite scalar representability proposition are also sound under the explicitly stated assumptions.

The principal issue found was an optimization-domain mismatch: the implementation limits added features to the remaining DSL slots, while the initial Proposition 2 omitted that limit. The reviewed manuscript revision now includes `sum z_f <= K` and scopes the minimum to the declared feature limit. The same revision makes trial selections replaceable, exempts fixed constant feature limits from the generic NP-hard claim, and acknowledges deterministic sorting overhead. Those were substantive formal clarifications, not cosmetic terminology changes.

No high-severity search correctness defect was found. `refinement.py` was left unchanged. One remaining wording recommendation is to state explicitly that the classical `H_m` weighted greedy cover guarantee assumes **no cardinality constraint**; ordinary weighted greedy does not inherit that guarantee for the capped repair master.

## Claim-by-claim proof audit

### Proposition 1: finite pointwise scalar representability

Assume a finite set of occurrences and requirements, exact feature equality, and an unrestricted pointwise scalar function of precisely those features. Every scorer-observable input must be represented; neither hidden identifiers nor evidence labels may supply a second scoring channel.

If the quotient contains a cycle, its required strict score decreases compose into `h(x) > h(x)`, which is impossible. A self-loop is the length-one case. Conversely, for a finite DAG assign each quotient vertex the length of its longest outgoing path. Every arc `u -> v` satisfies `length(u) >= 1 + length(v)`, hence the assignment satisfies every strict requirement. Scaling by a number strictly greater than the desired positive score margin establishes that margin. Extend this function arbitrarily outside the finite observed vectors.

This proves the stated equivalence. It does **not** prove bounded-DSL expressibility, satisfaction by an actually proposed rule, generalization, or greedy schedule optimality. The manuscript preserves these distinctions.

### Necessary concrete equality-join cuts

A lifted witness contains concrete requirement arcs `p_i -> n_i` and joins `n_i ~ p_(i+1)`, with cyclic indices. For a proposed feature subset `S`, suppose no selected feature separates any join. Since the base features remain fixed, every join stays equal under `(base, S)`. The concrete arcs then induce a closed directed walk in the refined quotient. Every finite closed directed walk contains a directed cycle, including possible self-loops. Consequently, an acyclic repair must select at least one feature in the witness's separating-feature set.

This necessity statement is stronger than relying on quotient representatives: the stored negative and positive endpoints refer to the actual occurrences of neighboring requirement arcs. `diagnose_occurrences` checks equality of each such pair and preserves self-loops and all requirements. It extracts one witness at a time, but rebuilds the entire quotient before every separation decision.

Breaking a join is necessary for breaking that concrete walk; it need not be sufficient to repair the whole quotient. The repeated full quotient check supplies the missing sufficiency test.

### Proposition 2: additive optimum after exact separation

The required conditions are:

1. Fixed evidence, fixed base features, and a fixed finite proposal catalogue with fixed evaluated feature values.
2. Fixed finite positive additive feature costs. These are a surrogate objective; shared compiled deployment cost is a different, generally nonadditive objective.
3. A declared master-feasible domain, including the cardinality limit `K` when one is imposed.
4. Every master solution is globally optimal over that domain and all retained necessary witness cuts.
5. Each trial uses the current selected subset appended to the **fixed base**, replacing previous trial choices. Intermediate selected features are not irrevocably accumulated.
6. Termination is declared successful only after checking the **entire** refined quotient is acyclic.

Let `R_K` be all cardinality-feasible feature subsets whose full quotient is a DAG, and let `M_t` be the subsets satisfying the retained cuts. Necessity of each cut gives `R_K subseteq M_t`. Thus the master optimum is no greater than the true minimum repair cost. At successful termination its globally optimal master subset also belongs to `R_K`, so its cost is no less than the true minimum. The two inequalities give equality.

Without budgets, finite separation also terminates: a newly extracted witness has equal joins under the current subset, so that subset hits none of its separating features and is excluded by the new cut. No previously excluded subset can recur. There are at most `2^|F|` subsets, or fewer within a cardinality limit. The process reaches a DAG or establishes infeasibility. This is a finite termination argument, not a polynomial-time bound.

If a witness has no separating catalogue feature, all catalogue subsets preserve its closed walk; no repair exists in that fixed catalogue. If a cardinality-constrained master is infeasible, no repair exists **within that limit**. Neither event proves impossibility for a larger language or a newly expanded catalogue.

If the catalogue is expanded between solves, all retained witness coefficients must be reevaluated for the new feature columns before claiming optimality over the final catalogue. The implemented vector solver accepts a fixed table per invocation; it does not itself perform dynamic expansion. Similarly, modifying costs or feature semantics requires a new consistently evaluated optimization problem.

### Weighted clique envelope and rounding

Fix a feasible boundary and forced action. Partition the remaining available vertices into interior `H` and outside cliques `C_j`. For any feasible completion, its contribution inside `H` is bounded by a sound induced-MWIS upper bound `U_H`. Its intersection with each verified clique has at most one vertex, so its outside contribution is at most `sum_j max_{v in C_j} w_v`. Adding the exact weight of the fixed and forced contacts yields the full conditional upper bound. Relaxing cross-region edges cannot invalidate an upper bound.

The assumptions matter: outside cliques must cover the entire outside set, be disjoint, and contain every required pairwise edge; the committed contacts must be feasible; the interior bound must be sound; weights are nonnegative. With negative weights one would need an explicit zero option in each clique maximum. The stated graph model has nonnegative weights.

The source verifies clique validity and coverage, computes objective sums with exact `Fraction` arithmetic for the saved numerical weights, and exports endpoints outward. `local_bound` already receives the fixed-action base inside its interior solve and therefore adds only the outside envelope; it does not double-count the base term in the manuscript formula. Every lower endpoint is supported by a full-graph feasible selected set. Intersecting repeated intervals by maximum valid lower and minimum valid upper remains sound even when individual greedy covers are not monotone.

The node and call budgets do not bound all clique construction or arithmetic work. Elapsed cost must remain separately measured, as it is in the source. Soundness of an interval does not establish scalable certification.

### Generic explicit-table NP-hardness

For each set-cover universe element `e`, create two occurrences `p_e, n_e` with the same base feature value, unique to `e`, and the strict requirement `p_e -> n_e`. For each source subset `S`, create a feature with `f_S(p_e) = 1` exactly when `e in S`, and `f_S(n_e) = 0`. Copy the source subset's positive cost.

A selected feature family separates element `e` exactly when it covers `e`. If an element is uncovered, its self-loop survives. If every element is covered, each pair splits and contributes a single forward arc; distinct base classes prohibit cross-element aliases, so the quotient is acyclic. Feasible repairs and covers therefore have identical additive costs. The construction has a polynomial-size explicit feature table.

This proves hardness for the unrestricted table problem, or for a limit `K` supplied as part of the input (take `K = |F|`). It does not prove hardness for the particular graph DSL. A fixed constant `K`, such as six remaining slots, permits polynomial enumeration of `O(|F|^K)` candidate subsets in catalogue size; this can still be computationally expensive.

The classical `H_m` greedy statement concerns covering a **fixed witness family without a cardinality cap**. It supplies no guarantee for future separating witnesses, full quotient repair, joint synthesis, compiled deployment work, or a fixed-slot master.

## Branch-and-bound source audit

The checked master search starts at the empty feature set and branches on an uncovered witness cut. Every extension that covers all cuts must contain at least one feature from this cut, so the branches exhaust feasible continuations. A feature set already covering all cuts can be accepted without exploring its supersets, because every additional feature has strictly positive cost.

The visited-set cache is local to one master solve. Deduplicating an already visited subset cannot remove a distinct feasible continuation because all subsequent decisions depend only on that subset and the fixed current cuts. The cache resets when a new cut is added, which is essential.

Cost pruning uses `current_cost > incumbent_cost`, with exact fractions. Every extension costs at least as much because costs are positive. The strict comparison preserves equal-cost alternatives needed for the secondary minimum-cardinality and lexical tie breaks. Cardinality pruning discards only sets or extensions violating the declared limit.

The counter `master_subsets_evaluated` counts newly visited states, including pruned states, cumulatively across separation rounds. It is no longer an enumeration of every catalogue subset. Before visiting a new state, the code checks the remaining budget; duplicate queued states are skipped without consuming another visit. If a search is truncated, `optimal` remains false even when a subsequently checked full quotient makes the returned subset a feasible repair. Exact-budget completion is allowed when every needed state has been processed. An initially acyclic base correctly has zero-cost optimum without consuming master budget.

The code's `objective_scope` string does not name the cardinality restriction, although the separate `max_selected` field records it. A useful metadata improvement is an explicit optimality-domain field or a scope string that includes the declared feature limit. This is a reporting clarification; the reviewed master itself optimizes the correct constrained problem.

## Independent exhaustive tests and evidence

Added [test_refinement_master_v03.py](E:/01-Joycecyq/2026-AAMAS/第二篇/tests/test_refinement_master_v03.py). The reference does not call the implementation's cycle detector or master. It enumerates all candidate subsets and uses independent Kahn elimination on exact quotient keys.

The seven tests passed in 1.080 seconds in the local run. They include:

- 180 seeded random finite occurrence tables, each checked without a cap and with a random cap; aliases, repeated requirement arcs, self-loops, impossible strict systems, and integer, binary-float, and rational costs are included.
- 100 random weighted set-cover table reductions with guaranteed cover feasibility.
- Exhaustive checking of **every completed intermediate master**, not only the final selected repair.
- Repeated subset paths and equal-cost solutions whose tie break depends on cardinality and lexical order.
- 175 additional budgeted randomized invocations, checking repaired status against the independent full DAG test and refusing unwarranted optimality claims.
- A constrained-optimum counterexample: seven unit-cost specialist features repair seven pairs at cost 7; with at most six selected features a universal cost-10 feature is the minimum. Both results can be legitimately optimal only within their respective domains.
- Zero budgets, cumulative visit budgets across rounds, feasible-but-unproved outputs after truncation, and exact-budget completion.

These tests corroborate source behavior over small finite cases. The mathematical argument above is the basis for the general correctness claim.

## Reviewed source snapshot and follow-up recommendations

The snapshot hashes at the end of review were:

| File | SHA-256 |
|---|---|
| `cipheur/refinement.py` | `90a7e6c6981a73d13b715dc0b2b773cd2052724c2e044af617b7795eb074bd99` |
| `paper/sections/method.tex` | `dc6170aacc7dee8810738f39ea36315d3268dd7760a85d4deb59fd6f7481cbdc` |
| `tests/test_refinement_master_v03.py` | `68a60ad61b3c3e35bc9ded81ec7eeb077a4123f29757f5c2c3a1c1a35983eef2` |

Resolved in the reviewed manuscript: cardinality scope, replaceable trial features, fixed-cap hardness qualification, and sorting overhead. Recommended before final freeze: explicitly exclude cardinality constraints from the weighted-greedy guarantee; keep catalogue expansion's new-column cut evaluation explicit if that path is ever implemented; name the declared feature limit in optimality metadata. No broader theorem, generative advantage, held-out adaptation, or empirical scalability claim follows from this review.
