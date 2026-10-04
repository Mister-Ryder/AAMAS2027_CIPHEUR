# Independent V06 method draft review

Owned draft: `paper/drafts/v06/method.tex`. This is a replacement section
fragment, not an addition to the current paper. No current `paper/main.tex`,
section, figure, frozen source/evidence or result file was edited. No V06
candidate assessment, raw author response or TEST outcome was read. The draft
contains no empirical superiority, model-population benefit or acceptance
claim. The research-paper-writing skill informed its proof and claim scope;
root's explicit section-only ownership overrides the skill's general Git and
pipeline suggestions.

## Length and source checks

The draft is about 1,325 visible prose words plus eight display equations
(headings counted, inline/display mathematics and citation/label commands
excluded by a deterministic regex count). It falls within the requested
1,250–1,450-word target. Braces are balanced and every cited key exists in
`paper/references_v03.bib`. Only four existing published MWIS references are
used in the single shared-kernel paragraph: `lamm2019weighted`,
`gellner2021struction`, `grossmann2024mmwis`, `grossmann2025chils`. Their
bibliographic records were read; no invented/arXiv reference was introduced.
They provide classical optimization context, not a claim that this Python
kernel reproduces those complete solvers or invented their ingredients.

The fragment has not been compiled as a substitute for root's multi-file
manuscript or visually inspected within the final layout. Root retains the
official class, fonts, geometry, figure placement and integration compile.

## Mathematical and implementation crosswalk

| Claim | Conditions preserved in the draft | Reviewed source |
|---|---|---|
| Component cancellation encloses the full-residual difference | Same graph and F/X boundary; common components match exact vertex sets; unmatched terms use bounds with the correct sign; no cross-configuration cancellation from IDs | `CancelledCompletionOracle` in `cipheur/relevance_synthesis_v04.py`, existing method |
| Regional clique envelope is sound | Sound induced-H upper plus disjoint verified cliques covering the remainder; cross-region conflicts relaxed, feasible lower witnesses checked | `cipheur/oracle.py`, `cipheur/repair_v06.py` |
| Scalar exists iff finite quotient is a DAG | Exact equality of represented finite values, all observed strict arcs including self-loops; unrestricted deterministic pointwise scalar, no bounded-grammar or unseen-state converse | `cipheur/refinement.py`, `cipheur/representation.py` |
| Full quotient repair attains a minimum | Fixed finite feature-value catalogue/evidence, positive additive standalone costs, declared K, globally solved master, complete quotient acyclic; finite subsets ensure exact separation terminates or reports infeasibility | `minimum_cost_vector_refinement` in `cipheur/refinement.py` |
| Additional features cannot repair via unused declarations | Base9 always retained; syntactically referenced additional coordinates only in the gate; declared diagnostics/finite checks remain separate | `interface_assessment` in `cipheur/synthesis_study_v06.py` |
| Numerical fit is independently measured | Original full F/X snapshots, strict scalar margin; score fit is not implied by the DAG and does not certify later restricted-patch preferences | `interface_assessment`, `selection_key` in `cipheur/synthesis_study_v06.py` |
| Bounded repair preserves the incumbent | Movable D excludes permanent F; Fout=I−D; D remains in legal restricted R'; independent local J has no edge to Fout; exact positive gain checked against original graph/F/X | `cipheur/repair_v06.py` |
| Programme's main role is local ordering | Common Degree initializer, targets, expansion and restriction; programme changes feasible local greedy order and pivot vertex; include-first traversal shared | `RepairConfig(policy_scope="branch")`, `repair_schedule`, `_solve` |
| TRAIN selection matches the new implementation | Common gate for all three prompt arms; strict fit first, exact equal-family retained reward/total weight second, charged feature+repair work third, original slot fourth; normal cap is eligible, errors/invalid/missing/duplicates cannot win, empty cell has no fallback | `assess_candidate`, `macro_quality`, `selection_key`, `select_cells` |

The component identity proof does not allow cancellation of partially
overlapping residuals, equal total weights, or common vertex names across
different configuration graphs. Unsearched common components can cancel
without knowing their optima; unsearched unmatched components remain bounded
and may leave the sign unknown.

The first theorem is both necessary and sufficient for arbitrary scores on
the finite observed classes. It proves neither rule-grammar expressibility
nor fit by an authored scalar. Its longest-path construction is not deployed
as a lookup-based scorer. The exact equality joins are concrete occurrences,
which may cross configurations/boundaries; separate per-state DAG checks would
be insufficient. The omitted-configuration-field audit remains necessary
before attributing an information obstruction specifically to structure.

The second theorem concerns the optional finite-catalogue subroutine. Its
master constraints are necessary for every final DAG, not sufficient until
the full quotient is rebuilt. Refined cycles can project to repeated coarse
classes. A truncated master, unresolved witness or variable programme bank
does not attain the theorem. The weighted-set-cover reduction is explicitly
about arbitrary finite feature-value tables with variable K; it does not
assert hardness for every typed library or for constant K. Standalone additive
cost cannot stand in for measured shared-DAG deployment work.

The repair paragraph gives the feasibility argument and deliberately leaves
heap encoding, search masks, exact root-versus-exhaustive proof metadata,
cooperative checks, cap numbers and multiprocessing in
`docs/V06_REPAIR_DESIGN.md`. Local search is a deployed classical solver
component; “no online oracle” means no full-residual certification/model call,
not a prohibition against bounded optimization inside the kernel. Local
exactness/root pruning concerns R' with Fout fixed, never a global MWIS or
minimum-runtime claim.

The full TRAIN specification has 594 strict requirements. The controller
checks all of them. Relations/witness packets expose their prescribed example
subset; the complete hidden controller record is not given to any author,
and the objective-only packet receives no certified relations/joins. C still
faces exactly the same certificate gate and selector; C is an authoring-input
ablation, not uncertified selection. The draft avoids claiming matched tokens,
latency, served model identity or an LLM population effect.

## Required integration changes outside this agent's ownership

1. Current `paper/sections/problem.tex` ends with a pure argmax construction
   loop and claims complete selection. That paragraph must distinguish the
   common initial construction from the new anytime incumbent/repair loop.
   V06 programme scores do not pick a global greedy argmax throughout the run.
2. Existing V05 online algorithm diagrams show constructive argmax/deletion
   alone. Update their online semantics to common initializer → selected
   blocker patch → bounded local greedy/pivot search → checked positive commit
   or retain incumbent. Keep full-residual offline certificates separate from
   restricted-patch deployment. Do not hard-code an unselected V06 AST.
3. Abstract/introduction should say demanded additional-feature gate plus
   actual scalar fit for V06, rather than implying that every declared extra
   feature contributes to gate repair or that DAG membership proves the actual
   scalar obeys certificates. The new lexicographic selector is not the old
   V04/V05 J=q−lambda*c selector.
4. Experiments must preserve a fair shared kernel/config/clock across prompt
   arms and classical priority controls, distinguish classical component
   strength from framework contribution, retain negative published comparisons,
   and defer all V06 quality/model advantage claims until verified results.
5. Online cost/failure reporting must use V06 anytime semantics. A time/node/
   work cap retaining I is not an old failed full-construction row. Unexpected
   programme/worker errors remain explicit and cannot silently obtain a
   replacement winner. Equal nominal wall targets do not establish identical
   total computation across Python/native implementations.
6. The draft reuses method/equation labels for replacement compatibility. Do
   not include it alongside the old method fragment: duplicate labels and two
   inconsistent methods would result. A full compile and visual layout check
   remain root's integration work.

No natural physical-source obstruction, universal patch preference,
schedule-quality guarantee or solver dominance is asserted by this draft.
