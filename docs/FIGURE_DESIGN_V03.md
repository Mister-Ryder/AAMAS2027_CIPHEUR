# Scientific figure design for v03

All schematic figures are native draw.io diagrams, exported by the installed draw.io Desktop CLI to vector PDFs and high-resolution PNG inspection previews. Each PDF and PNG contains the editable diagram XML. `scripts/build_schematics_v03.py` is the reproducible builder. It first audits the substantive examples against the current implementation, then creates native `.drawio` sources, exports them, checks their dimensions and embedded XML, and removes the intermediate native files. Use `--keep-source` if a separate `.drawio` file is wanted.

## Asset and placement contract

| Figure label | Publication asset | Preview | Intended placement |
| --- | --- | --- | --- |
| `fig:motivation` | `paper/figures/motivation.drawio.pdf` | `motivation.drawio.png` | Introduction, full text width |
| `fig:problem` | `paper/figures/problem_setting.drawio.pdf` | `problem_setting.drawio.png` | Problem formulation, single column |
| `fig:method` | `paper/figures/method_overview.drawio.pdf` | `method_overview.drawio.png` | Method overview, full text width |
| `fig:cancellation` | `paper/figures/component_cancellation.drawio.pdf` | `component_cancellation.drawio.png` | Full-residual certification, single column |
| `fig:repair` | `paper/figures/repair_cycle.drawio.pdf` | `repair_cycle.drawio.png` | Worked witness-to-program synthesis, full text width |
| `fig:compiler` | `paper/figures/compiled_updates.drawio.pdf` | `compiled_updates.drawio.png` | Compiled residual evaluation, single column |

The full-width figures use a 680-unit canvas, exported by this Desktop build as approximately 490 PDF points. The column figures use a 330-unit canvas, approximately 238 PDF points. Labels use Arial at 12.5–13 draw.io units, at least 9 points at the intended AAMAS placement (`\textwidth=504pt`, `\columnwidth=240pt`). Use `width=\textwidth` for motivation, method and repair, and `width=\columnwidth` for problem, cancellation and compiler. Do not shrink a full-width figure to a column. Only key mechanisms use thick colored strokes. Proposed mechanisms are blue `#176B9B`, contradictions or incorrect updates are orange `#D36B32`, and ordinary graph structure is gray `#687782`. White backgrounds and restrained pale fills keep the figures printable.

The revised placed image-height budgets are 3.6 inches for motivation, 3.2 inches for method, and 3.0 inches for worked synthesis, excluding captions. Their native canvases are respectively 680×348, 680×310, and 680×292. Purple `#71559C` with a restrained lilac fill identifies the offline LLM session and its actual authored proposals; blue denotes proposed/verified computation, orange certificates of missing distinctions or failed action audits, and gray ordinary graph structure. The original overview and four-cycle recheck remain available as `method_overview-simple.drawio.pdf` and `repair_cycle-simple.drawio.pdf`. Wider optional versions of the two column figures are `problem_setting-wide.drawio.pdf` and `compiled_updates-wide.drawio.pdf`, with matching `.drawio.png` previews; these are intended for the Markdown review or full-width reuse.

## Caption proposals and scientific commitments

### Motivation (`fig:motivation`)

**Proposed caption.** A ground-gap intervention exposes a missing structural distinction. The same contact opportunities and rewards are held fixed while the ground transition gap changes from 0 to 4; satellite gap remains 0. Roots `a,b` each have reward 8 and three reward-6 peripheral neighbors. The X triple shares one station and changes from an independent set to a clique, whereas the Y triple uses distinct stations and retains one satellite-overlap edge. At the common boundary, the conditional completion increments for committing `a,b` change from `(20,26)` to `(20,14)`, reversing the preferred root from `b` to `a`. All nine base inputs of `a,b`, including the resource-gap scalars, agree within each configuration, so each strict ordering becomes a quotient self-loop. The induced-neighborhood edge count distinguishes the roots as `(0,1)` before and `(3,1)` after the intervention.

The figure reproduces the training reversal in `cipheur/experiment_data.py:diagnostic_pair`, at unit reward scale and without its time translation. The independent committed contact `z` is omitted from the graph and subtracted from the displayed conditional values. Equality is **within each configuration**: the complete vectors are not equal across the intervention because ground-gap inputs change. The displayed conditional preference does not imply that a greedy schedule must select either root or that the refined score is globally optimal.

### Scheduling model (`fig:problem`)

**Proposed caption.** From contact intervals to a feasible independent set. Five opportunities use distinct satellites and the indicated ground stations under a ground transition gap of 1. Ground resource conflicts produce the path `a–b–c–d`, with `e` isolated on another station. The selected independent set `{a,d,e}` has reward 10 and maps back to a feasible timetable; in particular, `a` and `d` respect the transition gap. This mapping applies to the modeled pairwise hard constraints.

This is a deliberately small constructed illustration, not an experiment or a source-derived C3 instance. The builder reconstructs the intervals through the implemented `temporal_graph` predicate and verifies all three conflict edges, selected-set feasibility, and reward. The graph and final timetable use matching labels, so resource compatibility can be checked directly.

### Method (`fig:method`)

**Short paper caption (46 words).** Offline synthesis exposes the LLM's evidence packet, prompt constraints and joint feature–rule proposals. Deterministic checks repair the full quotient and audit reached actions, quality and compiled cost. Feedback informs later offline batches; the selected score-sliced program is frozen before online greedy commitment and residual updates.

The revised method figure makes LLM participation central. It contains the actual diagnostic neighborhood motifs, an equality join `b→a≡φb`, a source-backed summary of prompt constraints, the primary frozen v04 `root→neighbors→clique_cover_weight` AST, the minimum-cost master/full-quotient feedback loop, and the TRAIN selection ledger with a declared-interface DAG gate, quality–work utility and reached-action regret. The DAG gate establishes finite representability; numerical agreement of the bounded score with certified preferences is a separate diagnostic, not a selection term or perfect-agreement gate. The displayed feature is exactly `nc = clique_cover_weight(neighbors(root))`; its score `weight/max(0.000001,weight,nc)` is displayed verbatim. These match `guided_v04` in `.research/train_v04_frozen.json`; the clique envelope is a neighborhood feature and its normalized score does not certify global action order. The older g03 edge-count AST remains in the separate worked-synthesis figure. The left motifs include all four neighbors: the opposite reward 8 root and three reward 6 peripheral vertices. The tiny motifs are the constructed diagnostic configuration at gap0; they are not a certified natural alias. Actual rollout boundaries and chosen actions with challengers enter the later audit. Identical vertex-set connected components cancel before bounding the full conditional-value difference; unknown outcomes remain unknown.

The purple agent symbol is a generic assistant-session icon. The overview now labels the actual offline `gpt-6.1-sol` assistant session explicitly. The v04 bank comprises 12 final proposals authored in one continuing assistant-agent session, with root feedback before TRAIN outcomes, as recorded in `docs/V04_PROPOSAL_AUTHORING.json`; external provider API calls are zero and token counts remain unknown. The original g03/g18 proposals shown elsewhere are saved in `experiments/discovery/v03/guided_batch.json`; their witness-conditioned creation and one-batch scope are recorded in `guided_generation.md`. Exact model provenance (`gpt-6.1-sol`, ultra) is supported by the root-verified `model_provenance_receipt.json`. Prompt-card sentences summarize the supplied evidence and allowed schema; they are **not** presented as verbatim decrypted prompt text. The feedback arrow means a later offline design batch, including the new TRAIN-only redesign, not an automatically repeated or measured provider-API call. Each evaluated bank is frozen before its outcome-driven selection. The selected deployment program is frozen after TRAIN selection and before fresh evaluation. The figure does not imply matched generation compute, several independent batches, or any online LLM call.

The finite action-pool regret upper bound is **not** an all-action regret upper bound. Repair establishes observed representability, not global score optimality. The master objective uses additive standalone feature cost; joint selection measures the compiled program.

Score slicing in the updated deployment mechanism means that only named inputs referenced by the score enter its static dependency graph; numeric input evaluation is lazy along the executed score branch. Shared subexpressions and residual updates preserve reference scores. Initialization and maintenance for the static demanded superset still count toward cost. This mechanism must not be used to relabel old measurements: v03 cooperative003 and all 001 archived timings used the earlier full-interface compiler/default `score_slice=False`; v04 training calls explicitly use `score_slice=True`. The figure is a mechanism illustration, not an empirical advantage claim or a claim about old timing scope.

### Common-component cancellation (`fig:cancellation`)

**Short paper caption.** Identical residual components cancel from the global conditional-value difference. In this constructed zero-search example, separate intervals [33,43] and [28,38] overlap, yet shared five-cycle K cancels exactly, leaving Δ=5 and a strict preference for a. The oracle never bounds K.

The labels are English, and the native canvas is 330×292, placing at about 2.94 inches at 240-point column width. This compact technical figure can replace the taller 4.30-inch compiler illustration in the main paper; the original compiler asset remains available for the figure gallery or supplement.

The constructed original graph has root actions `a,b` with rewards 8,6 and edge `{a,b}`; `A` has reward 5 and conflicts only with `b`; `B` has reward 2 and conflicts only with `a`; the five vertices `k0,...,k4` form a disjoint cycle with reward 10 each. Thus `R_a={A}∪K` and `R_b={B}∪K`, with the same exact vertex set K. The existing zero-node full-residual oracle gives `V(a)∈[33,43]` and `V(b)∈[28,38]`: feasible packing 20 and clique-cover 30 for K. The cancellation oracle solves only the two isolated unmatched components, obtains `Δ=8−6+5−2=5` exactly, expands zero search nodes, and never puts K into its component-bound cache. K is **not** approximated away; its identical unknown optimal value cancels algebraically from the global comparison. The tiny graph is a verified illustration, not a measured study outcome or an oracle input available to the deployed scorer.

### Worked witness-to-program synthesis (`fig:repair`)

**Short paper caption (46 words).** A constructed diagnostic self-loop exposes missing neighborhood structure. The actual assistant-authored g03 density and g18 continuation programs use distinct typed ASTs and ranking hypotheses. g03 separates both probe preferences; the separate TRAIN action audit illustrates why witness separation must still be followed by full-quotient, action and cost checks.

The left graph is the exact gap4 diagnostic configuration also audited in the motivation figure: roots have reward 8, peripheral vertices reward 6, X becomes a clique and Y retains one edge. The full conditional increments 20 versus 14 and complete within-side base-vector equality produce a self-loop. The committed isolated contact is subtracted as `w(F)`. The actual g03 proposal uses `count(induced_edges(neighbors(root)))`, normalized density `ρ=2E/max(1,d(d−1))`, and the saved rule `h=w(1+ρ)/(1+C/max(ε,w))`, where C is conflict weight, d residual degree, and ε=10⁻⁶. Unit-scale scores are `(1.882,2.196)` before and `(2.824,2.196)` after, showing the observed b-to-a probe ordering. These are exact-program evaluations rounded to three decimals, not a quality-advantage claim.

The actual g18 proposal shares `R_v=R\\({v}∪N(v))` across clique-cover and greedy-independent primitives, with score `w(v)+(L_v+U_v)/2`. Its lower and upper summaries are valid values for the retained graph, but their midpoint does not certify global action order. These ASTs and rules were authored in the original one-batch guided proposal response; the illustration does not claim that g18 was created by post-hoc inspection of the displayed later audit.

The bottom audit is explicitly a **separate** initial C3 TRAIN context: `c3_train_64_0001_anchored_weighted_clique_cover_0`, with fixed/excluded sets empty. The saved 1000-node conditional oracle completes exactly in two expanded nodes. g05 actually chooses 35170 and has regret 192 on each side; g03/g12/g18 choose 28126 and have regret 0. This is a concrete training counterexample to converting witness consistency into an action guarantee. It does not establish a cause of all dense/long-contact held-out failures. Exact results and source mapping are in `experiments/analysis/v03/summary.json` under `program_diagnosis.audited_train_case` and the relevance summary.

### Original full quotient recheck (gallery: `repair_cycle-simple.drawio.pdf`)

**Proposed caption.** Covering an original quotient cycle is insufficient. The actual four-requirement regression fixture starts with coarse classes A and B and a two-cycle. A cost-1 feature breaks an equality join in the concrete two-arc witness, but the full refined quotient contains the four-cycle `A0→B0→A1→B1→A0`, whose projection revisits the coarse classes. Full separation adds that witness and the next master replaces the cheap feature with a cost-2 feature that gives every occurrence a distinct value. All four requirement arcs then form a DAG. Minimum-cost claims require both an exact master and a final full-quotient DAG.

This is `tests/test_innovation_v03.py:vector_cycle` and `FullQuotientRefinementTests.test_concrete_joins_and_surviving_four_cycle_force_another_master`. Its requirements are `a1→b1`, `b2→a2`, `a3→b3`, `b4→a4`. The cheap feature takes value 1 on `{a2,a3,b3,b4}` and 0 elsewhere. The cost-2 feature gives all eight occurrences distinct values. The reported result is **replacement**, not cumulative selection of both features: selected catalogue entry `repair`, cost 2, two master rounds. The occurrence values in the middle panel show all four surviving equality joins.

### Compilation (`fig:compiler`)

**Proposed caption.** Share typed subexpressions while preserving residual update semantics. Neighbor-edge count and minimum-weight edge sum share the same typed `root→neighbors→induced_edges` DAG. In the deletion example, two triangles share an edge and the tracked surviving root is vertex 2. With integer rewards `(2,3,5,7,11)`, its minimum-weight neighborhood-edge sum is initially `T(2)=5`. Sequentially deleting vertices 0 and 1 gives `5→3→0`; each subtraction uses the updated residual neighborhood. Computing both deletions from the original snapshot would subtract edge `{0,1}` twice and incorrectly produce `−2`. Caches remain valid only within a residual state, and all initialization, intersections, updates, cache work, and scoring contribute to measured work.

The topology is the overlapping batch-deletion fixture in `tests/test_compiled_v03.py`, with integer rewards chosen to expose the arithmetic clearly. The builder evaluates every displayed state through `CompiledEvaluator` and checks exact interface equality with the reference interpreter. Sharing a graph-operation DAG does not imply constant-time dense-graph updates. The compiler preserves the reference numeric interface; it does not claim a generic symbolic arithmetic transformation.

## Rebuild and validation

```powershell
.\.venv\Scripts\python.exe scripts\build_schematics_v03.py
```

The export command puts the input path **before** `--disable-gpu`; this installed Desktop CLI otherwise treats the unlisted Electron flag as an input filename. Windows export uses `Start-Process -WindowStyle Hidden -Wait`. Successful exports must pass native XML parsing, one-page PDF checks, nontrivial file size checks, editable `mxfile` XML checks in both formats, and preview dimension checks. Inspect the exported PNGs at full size and the PDFs at full text width after substantive changes.

This Desktop build writes malformed ancillary PNG metadata when `-e` is supplied: its `zTXt` stream uses raw deflate and an incorrect CRC, and its output lacks the final `IEND`. The builder preserves every original `IHDR`, color and compressed `IDAT` chunk, replaces only the malformed metadata with a standards-compliant `tEXt` chunk under draw.io's `mxGraphModel` key **before the first `IDAT`**, and adds `IEND`. The embedded native XML is URL-encoded as in draw.io's own export. The PDF's editable XML is recovered from its URL-encoded `/Subject` metadata. Pixel content is not altered by this normalization. The installed draw.io reader accepts this `tEXt` convention and stops searching for metadata at the first `IDAT`.

The builder's semantic checks cover the four conditional values, exact within-side base input equality, added X edges, unchanged satellite gap, neighborhood-edge counts, the two-round four-cycle repair, sequential update values, reference feature equality, timetable feasibility, and the zero-search cancellation example including overlapping original bounds and an unqueried common component. These are verification of the figure's factual content, not new experimental performance results.

### Frozen v04 overview audit (2026-10-03)

Only `method_overview()` in the editable builder and its two publication exports were revised. The displayed primary AST and literal score match `programs.guided_v04` in `.research/train_v04_frozen.json` (SHA256 `2f4379e782413a2ba68222314ec674163f91a5ffcf75c7d74062388dc601987b`), which records selection on TRAIN and `test_accessed=false`. The model label matches the v04 authoring receipt. The rich prompt/evidence, full-quotient separation, reached-action audit, freeze and online residual flow remain in place. No paper section, programme or evaluation output was changed or consulted for this update.

The final PNG was visually inspected at 2042×932 pixels: the complete literal score fits on one line, the clique-cover AST is readable, and all labels retain the minimum 12.5 draw.io-unit font (approximately 9.26 pt at full-width placement). The PDF remains a one-page 490.08×222.96 pt vector figure, with unchanged canvas and placement height. Both exports contain the same 65 editable cells. This Desktop exporter adds delimiter-escape backslashes inside the PDF's embedded XML for labels containing parentheses. For this overview only, `/Subject` was replaced with the URL-encoded native XML recovered from the PNG, restoring exact editable labels; the decoded PDF page content stream and extracted page text were verified unchanged. Future regeneration should repeat this metadata normalization before claiming identical editable labels in the two formats. An independent read-only audit confirmed the AST/rule match, TRAIN freeze scope and offline/online distinction; the normalized score remains a heuristic, without a global action-order guarantee.

### Earlier export QA record (superseded placement)

All PDF variants have one page, all PNGs load normally, and native XML parses from every export. The motivation PNG was re-imported through draw.io Desktop and exported back to native XML: the recovered diagram contains the same **63 editable cells** as the PDF's native model. Final main PNGs were visually inspected after export. The redesigned overview exposes the assistant session and AST, its unknown-outcome line and feedback caption fit, and the worked synthesis's two rounded score rows and midpoint qualification are visible. The original four-cycle recheck remains intact in the gallery variant.

| Main figure | Native PDF size (pt) | Placed image height | Placement |
| --- | --- | --- | --- |
| Motivation | 490.08 × 251.04 | 3.59 in | 504 pt full width |
| Method | 490.08 × 222.96 | 3.18 in | 504 pt full width |
| Cancellation | 238.08 × 210.00 | 2.94 in | 240 pt column width |
| Worked synthesis | 490.08 × 210.00 | 3.00 in | 504 pt full width |
| Problem | 238.08 × 288.00 | 4.03 in | 240 pt column width |
| Compiler | 238.08 × 306.96 | 4.30 in | 240 pt column width |

These heights exclude the paper captions. Font sizes at placement are approximately 9.26–9.63 pt for full-width figures and 9.07–9.44 pt for column figures.

### Final eight-page manuscript QA, 3 October 2026

The final manuscript contains eight figures and two tables, using the stock official class typography and margins. All nine PDF pages were rendered and individually inspected, including the one reference page. The earlier placement table above records an intermediate layout; the final main allocation is as follows.

| Number | Scientific content | Final asset | Placement |
| --- | --- | --- | --- |
| 1 | Paired contacts, unchanged base alias, certified preference reversal | `motivation.drawio.pdf` (490.08 × 193.92 pt) | Full width, approximately 2.77 in high |
| 2 | Evidence packet → actual offline assistant → typed AST → audits → freeze → feasible deployment | `method_overview.drawio.pdf` (490.08 × 222.96 pt) | Full width, approximately 3.19 in high |
| 3 | Ground-station timeline → conflict graph → weighted independent selection | `problem_setting-wide.drawio.pdf` (490.08 × 180.00 pt) | Full width, approximately 2.57 in high |
| 4 | An identical unqueried component cancels; conditional bounds distinguish the actions | `component_cancellation.drawio.pdf` (238.08 × 210.00 pt) | One column |
| 5 | Concrete structural witness → saved g03/g18 assistant proposals → separate numerical/action checks | `repair_cycle.drawio.pdf` (490.08 × 210.00 pt) | Full width, approximately 3.00 in high |
| 6 | All 93 TRAIN programs; declared-interface DAG, scalar agreement and finite-pool regret separated | `train_mechanisms_v04.pdf` (7 × 2.1 in) | Full width |
| 7 | Complete-assignment quality/cost on fresh scheduling, DIMACS and SATLIB against published solvers | `quality_cost_combined_v04.pdf` (7 × 3.95 in) | Full width |
| 8 | Identical-AST fresh backend parity and paired CPU ratios; sparse failures and coverage | `heap_execution_v04.pdf` (7 × 2.25 in) | Full width |

Blue (`#176B9B`) denotes verified structure/evidence, purple (`#71559C`) the assistant/synthesis path, orange (`#D36B32`) intervention, obstruction or adverse outcome, and gray (`#687782`) comparators/context. Scientific plots use embedded Arial at 9 pt or larger; native schematic labels retain a minimum 12.5 draw.io units, approximately 9 pt after placement. Bold labels, directed arrows, shaded witness sets, exact numerical comparisons and selected-program markers carry the emphasis. The model icon represents the documented assistant session; it is not a decorative claim of repeated external-model experiments.

The constructed figures are mathematically checked examples, not observations from the natural scheduling population. Actual quantitative plots read the completed archives and retain assigned failures, source-cluster uncertainty, different budgets and negative results. No one-second or other runtime ratio is inferred from an unassessable pair. Figure 6 regret bars are bounds, not confidence intervals; Figure 7 uses different explicitly shown ordinate ranges between rows.

Five main schematic `.drawio` sources are published. Their PDF and PNG native XML labels are now exactly equal. The builder automatically normalizes the PDF `/Subject` metadata, and asserts that decoded page content and text are unchanged; it also repairs only the PNG ancillary metadata, preserving the compressed pixel streams. These steps make regeneration preserve editable labels without manually repeating a release-only fix. The rendered diagrams themselves were not altered by metadata normalization.
