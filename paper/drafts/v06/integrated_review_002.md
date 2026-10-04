# V06 integrated review 002: compressed draft

Reviewed 2026-10-04: current paper/main.tex and all seven active paper/drafts/v06/*.tex fragments. Archived original author sections are preserved and were not modified. The supporting TRAIN calibration document was read; the five displayed diagnostic/TRAIN PNG panels were inspected, and the algorithm panel was checked against its previously inspected unchanged content and current caption. No EoH output, TEST label, experiment or evaluator was read/run. This review alone is written.

Root reports the current integrated draft as **seven body pages plus one reference page**. This is an initial layout observation, not independently verified final compliance. The actual withheld/performance results are still absent. Do not call the final eight-page result-bearing paper complete or approved.

## Overall result

Compression largely preserves the scientific structure and improves the paper. It keeps the separate certificate, representability, numerical-fit and scheduling questions; the complete cross-state quotient; the optional exact catalogue master/proof; the actual shared search behavior; and the necessary adverse findings. Moving detailed native TRAIN calibration and the prefix table out of the body is appropriate: the main prose retains their scientifically relevant negative/null outcomes.

The remaining changes are small but important formal clarifications. The abstract still has the old broad oracle wording. The intervention definition has lost its explicit two-configuration boundary-feasibility condition. The first theorem should state its dependence on the represented vector alone, and the cost subsection should explicitly freeze the base and feature-value table. No major new method exposition or engineering report is needed.

## What survived compression correctly

| Item | Assessment |
|---|---|
| Nonnegative rewards and static constraints | Preserved. Capacity-one satellite/station pairwise conflicts are distinguished from general operational satellite scheduling; public MWIS and exploratory C3 retain separate meanings. |
| Full conditional objective | Preserved. It includes the fixed reward and compatible global completion, rather than a rollout or patch-only objective. |
| Cancellation | Preserved. Components are identified by complete vertex sets within one graph; cross-configuration, size-only and partially overlapping matches are explicitly insufficient. |
| Sound bounds/abstention | Preserved. Feasible packings, clique upper bounds, bounded exact tightening, rational arithmetic and unknown abstention remain. Neither a stop nor a tie is promoted to preservation. |
| Global quotient semantics | Preserved. Self-loops, exact equality, cross-state joins and complete retained-inventory rechecks are all present. Splitting one cycle is not treated as sufficient. |
| Exact catalogue scope | Mostly preserved. Fixed finite catalogue, positive standalone costs, capacity K, exact/global masters, replacement trials and the lack of a practical-LLM/runtime optimality guarantee remain. Two short assumptions should be explicit below. |
| Native incumbent F/X validation | Correctly added. Independence, inclusion of permanent F and exclusion of X are checked before repair. Destroying only I minus F preserves F; the region excludes exterior conflicts/X; a checked positive exact gain protects feasibility. |
| R2 provenance | Preserved. Experiments describe the separately registered shared rejected seed, and the algorithm caption explicitly says one bounded warm-repair round. Proposal positions are not adaptive iterations. |
| Main table's unfavorable evidence | Preserved visibly. R is bold for raw/selected fit and selected work; all schedule qualities tie; the W slot with 312 fitted labels remains; the fifth block favoring R is reported. The text does not claim fully consistent scores. |
| Weight/equality limitation | Correctly added to Discussion. Unit rewards collapse several summaries; heterogeneous rewards can make vectors unique and the quotient trivially acyclic despite grammar difficulty. Weighted deployment does not measure natural obstruction incidence. |
| Classical negative comparison | Preserved. Warm-versus-full-target CHILS remains 2/222/64; improving the half-target seed in 4/288 does not establish guidance superiority. |

## P0/P1 changes still needed

### 1. Restore admissibility on both sides of an intervention (P0)

problem.tex defines an admissible boundary once, then says an aligned intervention preserves its identities. Preserving F/X does not preserve F's independence after a switching gap changes. Availability of a/b alone also does not repair an infeasible F. Add one sentence:

> The common boundary must be admissible under both configurations.

This is a formal assumption underlying conditional feasibility and the certificate interpretation, not a new experimental claim. Also restore s_v < e_v beside the contact interval. In the conditional-value display, “independent in G_theta” is marginally clearer than unqualified “independent,” although the surrounding context already determines the graph.

### 2. State the scalar's exact observation scope (P1)

Theorem 1 currently says “an unrestricted deterministic scalar.” Its paragraph heading says pointwise, and the previous strict requirement uses h(phi(x)); nevertheless the theorem statement itself should say **a scalar of the represented vector alone**. Otherwise a scalar that separately observes graph identity/history would evade the equality classes. A compact statement is:

> An unrestricted deterministic scalar h(phi(x)) satisfies all observed requirements if and only if Q_phi is acyclic.

Keep the finite/unrestricted, bounded-grammar and unseen-correctness caveats already immediately below it. They need not be repeated throughout related work.

### 3. Explicitly freeze the base and feature-value table in the cost master (P1)

The compressed master/proof is worth keeping as a core formal subproblem. Its text currently fixes the catalogue/cost/K, uses “the base,” and later mentions fixed evidence. Add **fixed base and frozen occurrence feature-value table** to its first sentence. State that each master is solved globally before accepting the terminating DAG. The existing proof and replacement-trial sentence then correctly establish the scoped additive minimum. Do not change this into a guarantee for coordinate-replacing R2 proposals, actual selected rules, shared-DAG savings or deployment runtime.

One short cost definition would improve interpretation: c_f is standalone operation work on the declared fixed occurrence inventory. It is not the family-averaged complete-policy work c(P) in the first table. The current scopes say this qualitatively; naming the aggregation prevents comparing 1,371,468 directly with 8,441 or 7,850.

### 4. Align the abstract with the body (P0 before a final submission)

main.tex's adopted abstract is unchanged. Its “without online LLM or oracle calls” is broader than the method: deployment still invokes bounded classical optimization and can use native CHILS initialization. Use the already correct body phrase **without online LLM or full-residual certification-oracle calls**.

“Selected jointly for specification consistency” should distinguish finite input representability from measured numerical preference fit; none of the actual R2 programs satisfies all 594 strict requirements. A minimal clarification is “selected for finite input representability, preference fit, complete-schedule quality, and feature-computation cost.” This is precision about the implemented contribution, not an innovation downgrade.

The abstract's held-out-study statement must be backed by the real audited evaluation before final submission. It is currently an aim/plan, not a completed empirical finding. Do not add an efficacy sentence until the actual outcomes support it; retain null/adverse outcomes when they do not.

### 5. Keep the two comparison scopes distinct (P1)

Introduction contribution 3 combines “published-solver comparisons” with “under common classical components.” W/R/O and typed EoH/controls share the framework kernel; the original native published solvers have their own algorithms. Prefer “controlled authoring under a common kernel and separate published-solver comparisons.” Do not imply that native Struction/M2WIS are executed through our shared repair module.

Define numerical m(P) briefly as the number of retained strict requirements with score difference greater than eta, eta nonnegative. A single inline definition suffices. Also disclose that the fixed authoring examples are a subset whereas the controller evaluates the complete retained TRAIN inventory; the compressed wording currently leaves a reader unsure whether every one of the 594 labels was in the prompt. Use the frozen protocol's actual counts, not a reconstructed or outcome-chosen subset.

## Figures and caption consistency

- **Motivation:** the 20/26 to 20/14 bars, X independent-to-clique intervention and stable Y edge match the constructed diagnostic graph. The caption correctly says same-configuration base equivalence, excludes fixed reward, and does not claim a TRAIN synthesis result. The satellite scene is illustrative, not an assertion that its two pictured stations literally encode all graph resources.
- **Actual TRAIN quotient:** the two original arcs, two equality joins, and three-class replacement DAG match the recorded displayed obstruction. “Feature values, not fitted scores,” coordinate replacement, cold-bank provenance and the need for complete rechecking survive. The LLM icon must remain read as the source of a recorded feature proposal, not a fresh successful R2 response. The current caption supplies that provenance adequately.
- **Algorithm:** the absent dashed catalogue clause has been deleted from both caption and Description. The visible evidence/synthesis/repair stages now match the text. The general return loop is explicitly distinguished from the single actual R2 warm round. This previous problem is resolved.
- **Yield:** the all-five average, retained fifth-bank dashed curves and fixed-slot x-axis match the caption. This is not a learning-iteration curve or a sample-efficiency demonstration.
- **Catalogue:** the curve has zero self-loops at trials 7 and 8 but the Full DAG marker only at 9. The nearby prose preserves both directed-cycle checks and avoids treating zero self-loops as success. The cost-share panel matches the four reported work shares and is explicitly standalone cost.

One remaining usability issue: g(S), T(v) and c(S) in the generated concept/cost-share graphics are not defined by the compressed prose. Define g as greedy-packing weight, T(v) as the active compatible continuation A minus {v} and its neighbors, and the plotted c(S) as the clique-cover upper-bound weight. Distinguish that c from complete-policy work c(P), or use a different notation if root later revises the graphic. This needs one compact caption/prose sentence, not another figure. The method already supplies the relevant typed operations.

The catalogue paragraph now has a standalone punctuation line after “none yields an acyclic repair.” Join it back into the sentence during ordinary editing; no result changed.

## Necessary result-bearing additions, after actual audited outcomes

The current seven-body-page layout reserves only roughly one body page before an eight-page target; the real findings may require more. Do not refill space with request counts, audit-check totals, archive identities or a second native TRAIN-calibration table. A compact three-table main structure is sufficient:

1. **Keep the current TRAIN authoring table.** It distinguishes the one supported interface-yield effect from W's fit/work disadvantage and identical scheduling quality. Add a concise, separately labeled EoH authoring/selection result only after its own freeze/audit; it is a typed adaptation with a real iterative feedback process, not an unrestricted reproduction. Include measured authoring resources rather than calling slots equal computation.
2. **Add one withheld-mechanism table.** Use the registered source/family strata and report strict-label coverage, endpoint rule fit and paired reversal/preservation fit with their actual denominators. Retain tie/unknown/null counts; exact ties must not be scored as strict-preservation successes. Include the prescribed-renaming fit/range or consistency measure. Distinguish W joint versus R/O quality-only full-pipeline comparisons from an authoring-only witness effect. Selection roles remain frozen; no TEST-best variant is selected for presentation as the deployed winner.
3. **Add one complete published-performance table.** Keep every assessed native solver name/citation plus frozen proposed/control/EoH roles, original raw objectives by family, valid/assigned coverage and measured wall/CPU cost. Compare comparable metadata-supported source subsets; do not rank raw means from different success subsets as if they were matched. Explicit numerical incompatibilities remain dashes/nulls, not zero quality; failed/rejected execution cost is separated from valid-output timing. Show the common-initializer gain and the full-budget CHILS reference, not only a half-budget warm seed.

One additional curve has high value only after real data arrive: **quality or paired improvement versus actual charged computation** across the three registered targets, separated by input family and initialization track. It can expose whether costly priorities lose useful search time and whether warm-start gains survive comparison to full-budget CHILS. Original raw objective magnitudes must not be pooled across WDP, Segmentation, contacts, Grids and C3. Actual wall cost and work proxies need their distinct labels; nominal target alone is not an end-to-end deadline.

The released TRAIN patch bridge is useful as a short mechanistic paragraph or a small panel/column in the mechanism table after its audit. Report core versus full-strict-enriched query coverage, patch-size/strict-overlap limitations, local ties/unknowns and separate full/local target directions. It measures include-preference agreement on immutable patches, **not pivot efficiency or schedule improvement**. Its TRAIN status must remain visible; it is not held-out confirmation and cannot feed back into authors/selection. A large separate bridge table is unnecessary if coverage is too narrow to support a broader mechanism inference.

C3 remains a separate exploratory track with inherited predicates and provenance; it cannot validate the main synthetic physical model. Full per-policy/per-target/family inventories can remain in the supporting artifacts, while the main table retains complete method coverage and meaningful paired effects. Use source/paired-configuration and authoring-block units for uncertainty; the planned assignment count is not a sample size of independent scientific replications.

## Verdict for the next integration step

The compressed draft is a sounder, leaner **method-and-TRAIN initial paper**. The imported-incumbent validation, one-round R2 scope, exact-equality limitation and adverse first-table evidence have survived. Restore the few formal clauses above, keep the short scoped master/proof, and fill only independently audited actual results. This review does not certify final page compliance, empirical adaptation, competitiveness or acceptance.
