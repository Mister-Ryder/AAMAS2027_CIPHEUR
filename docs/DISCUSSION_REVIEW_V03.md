# Independent discussion and conclusion review — v03

Authoring scope: `paper/sections/discussion.tex`, `paper/sections/conclusion.tex`, and this review. No main-file, code, experiment, or Git edits.

The central claim is certified representation repair, not unrestricted global optimality or a generic LLM quality advantage. The prose distinguishes guarantees about saved evidence from observations about executed schedules and generalization. No experiment value, held-out gain, or acceptance claim was invented.

## Evidence and claim boundaries

| Manuscript statement | Inspectable basis | Boundary retained |
| --- | --- | --- |
| Designed aliases establish an information obstruction, while current temporal/C3 saved requirements are acyclic under the base interface. | `paper/sections/experiments.tex`, section “When Does Representation Repair Become Necessary?”; `paper/sections/introduction.tex` explains the alias construction. | Diagnostic probes do not establish prevalence on natural scheduling workloads; changing certified preferences alone does not imply representation insufficiency. |
| Quotient acyclicity characterizes finite unrestricted pointwise scalar scoring. | `paper/sections/method.tex`, Proposition 1; `.research/initial_diagnosis.json` explicitly saves `acyclic_does_not_prove_dsl_expressibility`. | No claim of realizability in the restricted scorer language, unseen consistency, or greedy global optimality. |
| The minimum repair depends on the finite catalogue, fixed evidence, and additive surrogate. | Method Proposition 2; `.research/repair.json` selects `neigh_edges` at additive work 6,181, marks globally optimal master/full quotient check, and saves final DAG. The archived four-feature mechanism run is `experiments/runs/v03/mechanisms_001.tar.gz`. | Shared AST execution cost is nonadditive; a minimal representation is not necessarily the best whole feature–rule pair. |
| Boundary preferences need trajectory relevance and complete-schedule evaluation. | Method certificate and selection subsections; problem conditional-value definition; experiments relevance subsection. | A program may avoid a saved boundary or select a third action. Neither action is automatically a scheduling failure. |
| One batch per synthesis condition cannot identify a general model-level witness-guidance benefit. | `experiments/discovery/v03/{guided,free,rule}_generation.md` and corresponding raw proposal JSON. | Guided uses 1,536 execution/feasibility smoke checks; free and rule use construction checks. Matched proposal/request counts are not matched compute. No token budget, repeated independent generation trials, or model-family comparison is established. |
| Compiler efficiency depends on graph structure and unsupported features. | Method incremental update/cost contract; experiments runtime subsection. | All initialization, update, cache, intersection, and fallback costs count; dense operations are not constant-time. |
| Frozen deployment retains feasible scheduling without online model/oracle access. | Problem kernel invariants and method deployment contract. | Feasibility is relative to evaluated pairwise resource predicates; schedule quality and the quality–cost tradeoff remain empirical. |

## Editorial separation

Discussion and conclusion contain no server address, account/API configuration, development status, delivery instructions, software test tally, draft page-count information, or project-management narrative. Operational provenance belongs in experiment/AI-use supplementary Markdown, with only the scientifically relevant generation limitations retained in the paper. No citations were added because the arguments follow the paper's definitions, proofs, and explicitly recorded protocol.

These sections are deliberately concise for the eight-page main text. Final manuscript integration should preserve the three distinctions: information obstruction versus preference change; finite additive repair optimum versus compiled deployment cost; conditional order versus executed complete-schedule performance.
