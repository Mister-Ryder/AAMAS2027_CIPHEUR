# Method redesign v0.3: implementable research contract

This document develops the exact title and abstract in `paper/ABSTRACT_TARGET.md`. The method remains offline, certified, representation-sensitive synthesis of a frozen graph-ranking program. The user-specified limit is **eight pages of main text, excluding references**. The method fragment is `paper/sections/method.tex`; it does not edit the title, abstract, or parent manuscript. Experimental outcomes must come from saved executions, never from the guarantees or hypotheses below.

## 1. What the existing evidence requires us to fix

The v0.2 prototype diagnoses exact feature aliases and offers a typed feature–rule interface, but its fixed bank makes contradiction-guided generation indistinguishable from free joint selection. Its simple rules can evade the specified root pair by selecting peripheral contacts. The fresh-instance follow-up also shows that representation consistency and complete-schedule quality are different quantities. These findings require stronger **search**, **state relevance**, and **deployment cost** mechanisms, rather than renaming the existing gate.

The redesign therefore adds four tightly connected components:

1. Evidence acquisition at actual rollout residual states with a current next-action anchor.
2. Minimum-cost feature repair over a finite proposal catalogue, using witnessed equality joins and repeated full-quotient separation.
3. Globally sound clique-cover envelopes for budgeted conditional completion certificates.
4. Shared compiled graph expressions and incremental residual aggregates, whose actual work enters joint program selection.

These are algorithms and finite-evidence guarantees, not claims of a newly discovered general abstraction-refinement theorem or of measured superiority.

## 2. Decision-relevant acquisition contract

A graph state is determined by fixed contacts `F`, explicit exclusions `X`, and the current configuration. Obtain `F` from an actual incumbent or archive rollout. Replay precisely that boundary in the paired intervention graph; reject the query if the fixed contacts cease to be feasible. Preserve contacts, rewards, time windows, model semantics, and exactly one changed admissible resource parameter.

Use the true next kernel action `a` on at least one side as the anchor, rather than choosing arbitrary node pairs. Select a challenger `b` among common feasible actions adjacent to `a` in both graphs, preferably the highest-ranked such challenger. Ranking uncertainty, changed structural exposure, or disagreement among retained programs only prioritizes queries; none provides a label. Include some uniformly sampled eligible challenges as the acquisition control. Preservation queries must remain eligible even when a legal parameter change leaves the edges unchanged.

Each saved request needs `anchor_side`, `rollout_program`, `step`, `fixed`, `excluded`, actual next action, action rank positions on both sides, configuration change, and the graph/residual fingerprints. Each saved attempt includes failure reason, four interval computations, expanded nodes, elapsed time, and total budget consumed.

For every candidate, additionally measure:

- **Boundary reachability:** whether its unrestricted rollout reaches the saved fixed/excluded state. Equality of state means semantic contact sets, not coincidental trajectory index.
- **Next-action escape:** after starting the same kernel at the saved boundary, whether its next action is outside `{a,b}`.
- **Chosen-action consistency:** whether it next chooses the certified preferred member when it chooses one of the pair.
- **Conditional regret:** at visited rollout states, compare the chosen action with a sound bound on the best available completion, reporting a regret interval when the reference is incomplete.

Escape is not automatically a failure: another action can be a better or compatible first move. It is nevertheless mandatory to report because pairwise score consistency alone may never affect scheduling. Do not introduce an unproved rule that a locally preferred member must beat every third action. Evaluate complete schedules separately, and report pair relevance by real trajectory visitation and escape rates, not only on constructed probes.

## 3. Sound certificate contract

For a fixed feasible boundary and forced action `d`, let `A` be the globally available residual contacts after committing `d`. Split `A` into interior `H` and outside `O`. Compute a budgeted upper bound `U_H` on the induced interior MWIS value. Partition `O` into disjoint verified cliques `C_j`. A safe full conditional upper bound is

`U(d | F,X) = w(F+d) + U_H + sum_j max_{v in C_j} w(v)`.

Every independent set takes at most one contact from each clique. Relaxing edges between the interior and outside enlarges the feasible set; it therefore preserves upper-bound validity. A singleton partition is always valid and recovers the previous outside-weight bound. A deterministic greedy clique partition is sufficient; no maximum-clique optimality claim is necessary. Verify coverage, disjointness, and all intra-clique adjacencies. The same clique-cover bound may replace the weight-sum envelope at every branch-and-bound frontier node.

Each lower bound must be the exact value of a checked full-graph feasible schedule containing the boundary and forced action. Complete an interior incumbent outside using a deterministic feasible greedy routine. Store four independent feasibility witnesses. Use exact arithmetic for the saved binary weights, or rigorous outward rounding throughout. Retain the maximum valid lower and minimum valid upper bound across repeated computations of the same conditional space; a new heuristic clique cover need not itself monotonically tighten the old bound.

Certify `a` over `b` only when `L(a) > U(b)+epsilon`. Opposite strict directions on the two sides certify reversal; the same strict direction on both sides certifies preservation. Exact ties, overlapping intervals, region limits, and exhausted budgets remain unknown. Report why a query is unknown: equal conditional optima, unresolved bounds, invalid alignment, or exhausted computation are different events.

## 4. Minimum distinguishing representation: precise finite problem

Let `Z` be the finite decision occurrences in accumulated certified strict requirements. A requirement arc has concrete endpoints `p_i -> n_i`, where `p_i` must score higher. Exact equality of all observable semantic features defines the current quotient `Q_phi`. Self-loops are retained. The quotient is acyclic exactly when an unrestricted pointwise scalar score exists on the observed feature vectors; a DAG says nothing about expressibility in the bounded rule DSL or generalization.

A contradiction witness is a sequence of concrete requirement arcs `p_i -> n_i` together with the specific equality joins `n_i ~ p_(i+1)`, cyclically. The joins are essential: merely listing quotient classes or one representative per class is insufficient. The sequence is a closed alternating walk on occurrences. A new feature breaks this particular witness only if it distinguishes at least one of these joins.

For a finite typed proposal catalogue `F`, set `d(W,f)=1` if feature `f` breaks witness `W`. Let `c_f>0` be a conservative, additive standalone feature-work estimate on development states. Solve

`min sum_f c_f z_f` subject to `sum_f d(W,f) z_f >= 1` for every collected witness, with `z_f in {0,1}`.

The practical routine is constraint generation:

1. Extract concrete witnesses from the current quotient.
2. Ask the LLM for several typed features addressing their missing joins; type-check and evaluate the catalogue.
3. Solve the accumulated cover problem using an exact master solver or cost-per-new-witness greedy selection.
4. Append the selected features to the representation and rebuild the **entire** quotient over all saved requirements.
5. If it remains cyclic, extract a new concrete witness and repeat. If the current catalogue cannot cover that witness, request additional features or return `unrepaired` when budget expires.

Hitting all original coarse simple cycles is insufficient. Refinement can expose a cycle whose coarse projection revisits an old class. Full quotient rechecking supplies the missing separation step. Never state that a one-pass cover repairs every observed contradiction unless the rebuilt quotient is acyclic.

The generic finite-catalogue optimization is NP-hard: reduce weighted set cover by assigning every universe element its own base feature class and one strict self-loop pair. A candidate feature separates that pair exactly when its source set contains the element. Unique base classes prevent inter-element aliases. Thus a feature subset repairs all pairs exactly when the source subsets cover the universe. This proves hardness of the generic finite observation problem, not a separate realizability theorem for the particular graph DSL.

For a fixed witness family `W` and additive costs, greedy weighted set cover gives the usual `H_|W|` approximation to covering **that family**. It does not give a logarithmic guarantee for all current or future cycles, the complete synthesis loop, DSL rule search, or shared-DAG deployment cost. If each master solve is globally optimal and full-quotient separation terminates with a DAG, the result is an exact minimum for that finite catalogue, fixed evidence, and additive surrogate objective: every cut is necessary, and the returned solution is feasible for the original repair problem. Budgeted/greedy outputs must be described as feasible repairs or partial repairs, not proved global minima.

After feature evaluation, canonicalization of `N` occurrence vectors of length `k` takes expected `O(Nk)` hashing work in a unit-cost arithmetic model. Quotient construction and DFS take `O(N+M)` time for `M` requirements; exact-number bit costs and graph-feature evaluation are additional. Master selection remains combinatorial.

## 5. Efficient deployment contract

Compile typed feature ASTs into a shared DAG by structural hashing. Repeated set expressions such as `neighbors(root)` and root-independent expressions such as `sum_weights(available)` are shared. Scope cached values to the graph and residual snapshot. Lower recognized aggregate patterns to maintained quantities; arbitrary composed features retain a valid snapshot interpreter.

For active neighborhood `N_R(v)`, maintain residual degree `D_R(v)`, conflict-weight sum `W_R(v)`, and the structural statistic

`T_R(v) = sum_{(u,z) in E[N_R(v)]} min(w_u,w_z)`.

After deleting active contact `x`, update surviving neighbor `v` by `D(v)-=1`, `W(v)-=w_x`, and

`T(v) -= sum_{y in N_R(v) intersection N_R(x)} min(w_x,w_y)`.

Process multiple deletions sequentially, removing `x` from the active set after its incident update. An edge whose endpoints are both deleted is subtracted only when its first endpoint is removed. Maintaining triangle sums costs graph intersection work, not constant time. Charge initialization, cache construction, all deletions, set/intersection scans, unsupported expression evaluation, and score evaluation. The graph may be dense and initialization may dominate. Measure elapsed feature, scoring, and total deployment time as well as the deterministic operation counter.

Preserve deterministic finite numerical outputs. Algebraically equivalent incremental arithmetic can differ in floating-point rounding and change strict ranking. Use exact accumulation, compensated/reproducible sums with a declared numerical contract, or fall back to snapshot evaluation when equivalence cannot be certified. Check the compiled evaluator against the reference interpreter on deletion traces, including overlapping batch deletions and edge cases. Do not claim exact behavioral equivalence solely from matching a few aggregate values.

## 6. Joint selection and independent LLM evidence

The LLM proposes typed features and an associated bounded scoring rule. The repair solver selects sufficient distinguishing features from those proposals; the LLM must then revise the rule against the selected interface. All accumulated reversal and preservation inequalities are replayed. Use the full compiled cost, not a sum of duplicated AST costs, in the final selection objective `validation_quality - lambda * normalized_feature_work`, subject to declared consistency and validity gates. Record residual violations if the gate allows less than 100% consistency. If no candidate passes, return no eligible program rather than claiming successful refinement.

Make witness-guided joint generation, free joint generation, and fixed-representation rule generation **independent batches** with the same call/candidate budgets, model interface, selection set, and training graph/evidence access. The guided condition receives concrete contradiction joins and their repair target; the free condition receives the same source evidence without that guidance; the rule-only condition can change formulas but not features. A shared bank can evaluate selection gates but cannot identify a generation advantage.

Direct assistant proposals are permissible actual assistant synthesis if each batch has an independent saved request and raw response. Label the backend and model provenance precisely. Count assistant-mediated calls separately from automated API calls and replay. Retain rejected proposals, typed validation failures, oracle failures, tokens when available, and wall-clock discovery cost. Never describe an assistant-made file or replay as an external API model run.

Freeze one accepted feature–rule program per run before any held-out objective or certificate is queried. Test held-out contact instances, held-out constraint configurations, and their joint shift. Deployment reads only current graph structure and permitted resource fields; it does not consult a model, conditional oracle, evidence table, or selection split.

## 7. Manuscript claims and necessary measurements

The method can claim exact obstruction diagnosis, sound full-residual certificates, finite-catalogue cost-aware repair, and a feasible frozen kernel. It cannot infer global optimality, universal adaptation, a generation advantage, or scalable certification from those properties.

The experiments need: natural-state contradiction incidence; anchored vs arbitrary-state evidence relevance; reversal/preservation/unknown yield by family; certification rate and bound widths vs graph size/density; observed cycles removed per proposal and feature work; escape and reachability; compiled vs reference work and wall time; independent matched-budget synthesis success and quality; preservation/cost/certification ablations; and complete-schedule comparisons with strong heuristics and solver references. Designed exact-alias probes remain mechanism tests, not workload prevalence estimates. Separate schedule quality from strict-score consistency, and separate discovery cost from online deployment latency.
