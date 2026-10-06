# CIP-Heur — V06 checkpoint and V07 scene analysis

**LLM-Guided Synthesis of Constraint-Adaptive Heuristics for Satellite–Ground Scheduling**

Public repository: [Mister-Ryder/AAMAS2027_CIPHEUR](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR).

## Current research: online adaptation and expanded LLM responsibilities (2026-10-06)

The new [online v2 implementation and evidence](experiments/stk_online_llm_v2/README.md) replaces the fixed ranking-head research direction with current-instance heuristic evolution. Real LLM calls generate structural features, ranking rules, neighborhood policies, mutation templates and control configurations from complete TRAIN failure/cost feedback. Runtime states reset for each instance; current-instance evaluation and evidence computation are charged solver work.

Two cloud development rounds each completed all 144 assignments with feasible outputs and no execution errors; 43 implementation tests passed. The expanded second-round system lowered Witness mean complete reward from 735,924.746 to 733,079.886 seconds and increased feature cost. This is an inspectable research candidate, **not a verified improvement**. The 576-job held-out study remains pending. See [the complete paired comparison](experiments/stk_online_llm_v2/reports/development_round2/两轮比较.md), [LLM roles and boundaries](experiments/stk_online_llm_v2/reports/LLM参与扩展与方法边界.md), and [complete raw review archives](experiments/stk_online_llm_v2/review_archives/README.md).

The V06/V07 material below is retained as historical evidence; its frozen-program description is not the new online optimizer's definition.

The corresponding STK data-construction artifact is now included under [`datasets/CIPHEUR_STK_20261005`](datasets/CIPHEUR_STK_20261005/PUBLIC_RELEASE.md): 64 primary TRAIN/validation/TEST graph instances, 32 earlier diagnostic graphs, ten raw contact libraries, generation/build code, source receipts, hashes, and data reports. Large reproducible STK object files and failed intermediates are intentionally excluded from Git.

The framework uses sound offline conditional-completion evidence to diagnose whether a graph-feature interface can express required action rankings. Concrete quotient cycles and equality joins guide typed feature–rule refinement. A frozen priority program then operates within a common feasibility-enforcing classical repair kernel; deployment requires no LLM or full-residual certification oracle.

V06 delivers the runnable framework, frozen authoring studies, public-graph and scheduling evaluations, manuscript, and reproducible evidence. The paper artifact is [CIPHEUR_AAMAS2027_V06.pdf](paper/CIPHEUR_AAMAS2027_V06.pdf); the public release target is [v0.6.0](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR/releases/tag/v0.6.0). The [research report](docs/V06_FINAL_RESEARCH_REPORT.md) separates supported scientific findings from engineering history. Mature classical components and the common CHILS initialization are shared infrastructure; their gains are not attributed to LLM guidance.

V06 is an auditable research checkpoint, not a claim that the intended large-scale configuration-adaptation advantage has been established. V07 first analyzes original scene inputs, exact decision-information requirements and the deployment decision interface. See the [mathematical data-selection criteria](docs/V07_DATA_SELECTION_MATHEMATICAL_CRITERIA.md), [TRAIN contribution-chain diagnosis](docs/V07_TRAIN_CONTRIBUTION_CHAIN_DIAGNOSIS.md), and [actual public-benchmark assessment](docs/V07_PUBLIC_BENCHMARK_SCENARIO_AUDIT.md). The prepared integrity workflow targets Python 3.10 and 3.13; public Actions status applies only to a revision that has actually been pushed.

The LLM proposes typed feature expressions and compatible ranking rules conditioned on certified structural witnesses. Deterministic checks decide admissibility and selection. The quotient theory establishes when representation refinement is necessary; it does not establish that an LLM is necessary or superior to enumeration. See the [LLM design rationale](docs/V06_LLM_DESIGN_RATIONALE.md).

## Run a frozen V06 program

Python 3.10+ is sufficient for the core demonstration; it uses only the standard library. Run from the repository root:

```text
python scripts/demo_repair_v06.py
```

The default chooses the first preregistered genuine W-joint winner, not a winner selected on TEST. Its four-program bank is [examples/frozen_joint_bank_v06.json](examples/frozen_joint_bank_v06.json). The verified toy returns independent contacts `b,c,d` with exact reward 13. This demonstrates runnable deployment and feasibility, not benchmark effectiveness. Output is written to a new `output/demo_v06/result.json`; use `--out NEW_PATH` for another run. The script refuses to overwrite existing evidence.

## V06 evidence and scientific scope

| Study | Completed evidence | Interpretation |
| --- | --- | --- |
| R1 cold synthesis | All 120 original slots retained; 112 valid programs assessed. Nine of twelve requested joint cells had an eligible winner. | Its original release barrier failed and its TEST study was stopped. It is not relabeled as a successful framework deployment. |
| R2 shared-seed refinement | Fifteen real author requests, 120 valid programs and 14,400 cloud TRAIN assignments. Independent authoring and mathematical audits pass. Four genuine W-joint programs are frozen. | Witness/relations/objective gate yields are 28/40, 24/40 and 0/40 across all five blocks. Matched four-block yields are 26/32, 19/32 and 0/32. The retained fifth block favors relations. |
| R2 ranking and scheduling | All 120 programs have identical TRAIN macro quality, 2693/4480 of total input reward. No program fits every strict requirement. | Witness guidance does not improve mean strict-rule fit or selected work over relations in this study. Gate yield, rule fit and reward are separate outcomes. |
| Fixed-catalogue representation repair | All 53 observed expressions; four additions resolve the complete quotient at independently certified minimum additive standalone cost 1,371,468. Prefixes 4/8/16 remain cyclic. | The minimum is scoped to that finite catalogue and evidence. It is not a runtime optimum or a fully fitted ranking rule. |
| Published classical solvers | Actual cloud TRAIN calibration for CHILS, its ILS variant, M2WIS, Struction and WeightedBR, with original weights and explicit compatibility limits. | Raw quality, coverage and actual wall costs are reported separately. Mature shared components have not established a guidance benefit. |
| Authentic EoH-DSL comparison | All 32 genuine sequential author calls and four seed fitness evaluations completed; independent audits pass. Four frozen quality pipelines retain the shared seed under the original tie rule. | All TRAIN qualities tie. This is a typed adaptation, not an unrestricted native reproduction; it supplies no newly authored quality improvement in this run. |
| Frozen heldout mechanism study | 31 requested identities, 72 states and five paired identifier renamings; all 13,392 kernel positions are normal and feasible. W-joint original strict fit is 91.94%. | W-joint is +3.37 pp above W-quality, but −1.82 pp below R-quality. Every matched Degree reward difference is zero. Three of twenty W-joint renamed quotients become contradictory. |
| TRAIN patch bridge | 120 original Degree first-patch restrictions, 159 distinct conditional queries and 2,760 complete scoring positions. The core sample has 14 strict and 141 exact-tie labels. | Degree fits all 15 local strict union labels. W-joint fits 58/60 repeated labels. Full-residual and local-patch preferences can reverse or become ties; no local-priority superiority is established. |
| Larger frozen performance study | All 52,548 declared assignments on 302 contexts and three targets are covered by the final independent audit: 71,184,835 checks, zero errors. The prepared statistical analysis is complete. | At T5, every defined non-C3 same-source warm W-joint versus Degree/EoH contrast is exact zero. Grids W-joint complete-group quality is undefined; 525 native encoding limitations and 82 policy errors remain recorded. No general quality superiority is established. |

Evidence and scientific limits: [R2 scientific review](docs/V06_R2_TRAIN_SCIENTIFIC_REVIEW.md), [catalogue findings](docs/V06_CATALOGUE_COST_FINDINGS.md), [EoH outcomes](docs/V06_PUBLISHED_EOH_FROZEN_RESULTS.md), [heldout outcomes](docs/V06_HELDOUT_RESULTS_001.md), [patch bridge](docs/V06_PATCH_BRIDGE_RESULTS.md), and [complete performance tables](experiments/analysis/v06/performance_tables_v06_002/PERFORMANCE_RESULTS_V06.md). Cloud provenance, authoring receipts, compatibility corrections and operational failures remain in separate Markdown reports, outside the manuscript.

## Evidence replay

Compressed cloud archives in `experiments/runs/v06/` are canonical raw evidence. The large performance archive is a release asset, and the heldout compact is supplied in lossless parts. Their retrieval and analysis commands are in [V06 replay instructions](docs/REPLAY_V06.md). Large assessment caches can be reconstructed without evaluating programs:

```text
python scripts/restore_assessment_caches_v06.py R1 R2 catalogue
```

The final performance audit is [performance_TEST_audit_v06_003.json](experiments/analysis/v06/performance_TEST_audit_v06_003.json), SHA-256 `db7209ad60c4d2f1cff07ec50b2bf26fd5d473153c56d809ff416f6781de22d6`. Replay instructions distinguish saved-result analysis from optional mathematical re-auditing; neither changes frozen selection. Use new output paths to preserve original reports.

Optional analysis dependencies are available through `python -m pip install -e ".[research]"`. Native published solvers require their separately pinned official binaries. Their host-specific executable paths, encoding limitations, exact input transformations and time accounting are documented in the protocols; equal nominal targets are not equal end-to-end hard deadlines.

## Paper and figures

The manuscript uses the official AAMAS class, with eight body pages and one reference page in the final PDF. [LaTeX source](paper/main.tex) integrates independently authored V06 sections from `paper/drafts/v06/`. The paper presents the method, mathematical scope, published-method comparisons and measured findings; full evidence inventories and engineering records are supplied in Markdown.

The compact engineering figures include the actual cycle-replacement illustration, an editable [draw.io algorithm figure](paper/figures/algorithms_v06c.drawio), and source-verified vector panels for proposal yield, complete-quotient refinement and feature work. Labels, caption scope and uniform figure styles distinguish illustrated mechanisms from measured outcomes.

## Historical versions

[The exact previous README](docs/archives/README_V05_BEFORE_V06.md) preserves V03–V05 context and replay commands. Exact V05 manuscript bytes remain in `paper/archives/v05_before_v06/`. Prior failed requests and negative outcomes retain their original protocols, raw archives and reports. The local V05 transfer and its separate cloud replay are exploratory historical studies; neither is a new V06 confirmation.
