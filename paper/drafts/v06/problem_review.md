# V06 Problem Setting review

Independent fragment: `problem.tex`; main manuscript, code, frozen inputs and
results are unchanged. Read the current problem section, V06 method draft,
repair design, evaluation protocol draft and performance-input protocol only;
no new raw model responses or TEST outcomes were read.
The fragment has approximately 495 prose words when each inline math expression
is counted as one token. Three equation environments and inline math delimiters
pass static balance checks.

- Keeps three compact equations and the existing labels `eq:mwis`,
  `eq:residual`, `eq:conditional-value`. Symbols align with the method's
  `G_theta`, `B=(F,X)`, `R_theta(B)`, `V_theta(d|B)` and frozen `(phi_P,h_P)`.
- Defines positive intervals, nonnegative rewards/gaps, static configurations,
  single-capacity pairwise conflicts and aligned interventions with identical
  contacts and individually feasible competing actions on both sides.
- Replaces irreversible greedy commitments with the shared classical anytime
  repair kernel. Permanent `F/X` differs from the movable incumbent and
  temporary exterior. Capped execution retains a feasible incumbent; neither
  maximality nor global optimality is promised.
- Explicitly allows bounded local classical search at deployment while
  excluding online LLM and full-residual certification-oracle calls. Global
  conditional labels do not establish local-patch priority correctness.
- C3 special predicates remain historical background. Public graphs carry
  only an MWIS interpretation. No solver dominance, LLM advantage, natural
  physical incidence, or new performance claim is made.

Root should check any final figure caption and old execution descriptions
against these updated semantics when merging. This is a section fragment;
compilation and full-manuscript layout verification belong to the integration
pass.
