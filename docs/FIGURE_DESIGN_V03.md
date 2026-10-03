# Scientific figure design for v03

All five figures are native draw.io diagrams, exported by the installed draw.io Desktop CLI to vector PDFs and high-resolution PNG inspection previews. Each PDF and PNG contains the editable diagram XML. `scripts/build_schematics_v03.py` is the reproducible builder. It first audits the substantive examples against the current implementation, then creates native `.drawio` sources, exports them, checks their dimensions and embedded XML, and removes the intermediate native files. Use `--keep-source` if a separate `.drawio` file is wanted.

## Asset and placement contract

| Figure label | Publication asset | Preview | Intended placement |
| --- | --- | --- | --- |
| `fig:motivation` | `paper/figures/motivation.drawio.pdf` | `motivation.drawio.png` | Introduction, full text width |
| `fig:problem` | `paper/figures/problem_setting.drawio.pdf` | `problem_setting.drawio.png` | Problem formulation, single column |
| `fig:method` | `paper/figures/method_overview.drawio.pdf` | `method_overview.drawio.png` | Method overview, full text width |
| `fig:repair` | `paper/figures/repair_cycle.drawio.pdf` | `repair_cycle.drawio.png` | Minimum representation repair, full text width |
| `fig:compiler` | `paper/figures/compiled_updates.drawio.pdf` | `compiled_updates.drawio.png` | Compiled residual evaluation, single column |

The full-width figures use a 680-unit canvas, exported by this Desktop build as approximately 490 PDF points. The column figures use a 330-unit canvas, approximately 238 PDF points. Labels use Arial at 12.5–13 draw.io units, at least 9 points at the intended AAMAS placement (`\textwidth=504pt`, `\columnwidth=240pt`). Use `width=\textwidth` for motivation, method and repair, and `width=\columnwidth` for problem and compiler. Do not shrink a full-width figure to a column. Only key mechanisms use thick colored strokes. Proposed mechanisms are blue `#176B9B`, contradictions or incorrect updates are orange `#D36B32`, and ordinary graph structure is gray `#687782`. White backgrounds and restrained pale fills keep the figures printable.

The placed image-height budgets are 3.6 inches for motivation, 3.0 inches for method, and 2.7 inches for repair, excluding captions. Their compact native canvases are respectively 680×348, 680×290, and 680×260. Wider optional versions of the two column figures are `problem_setting-wide.drawio.pdf` and `compiled_updates-wide.drawio.pdf`, with matching `.drawio.png` previews; these are intended for the Markdown review or full-width reuse.

## Caption proposals and scientific commitments

### Motivation (`fig:motivation`)

**Proposed caption.** A ground-gap intervention exposes a missing structural distinction. The same contact opportunities and rewards are held fixed while the ground transition gap changes from 0 to 4; satellite gap remains 0. Roots `a,b` each have reward 8 and three reward-6 peripheral neighbors. The X triple shares one station and changes from an independent set to a clique, whereas the Y triple uses distinct stations and retains one satellite-overlap edge. At the common boundary, the conditional completion increments for committing `a,b` change from `(20,26)` to `(20,14)`, reversing the preferred root from `b` to `a`. All nine base inputs of `a,b`, including the resource-gap scalars, agree within each configuration, so each strict ordering becomes a quotient self-loop. The induced-neighborhood edge count distinguishes the roots as `(0,1)` before and `(3,1)` after the intervention.

The figure reproduces the training reversal in `cipheur/experiment_data.py:diagnostic_pair`, at unit reward scale and without its time translation. The independent committed contact `z` is omitted from the graph and subtracted from the displayed conditional values. Equality is **within each configuration**: the complete vectors are not equal across the intervention because ground-gap inputs change. The displayed conditional preference does not imply that a greedy schedule must select either root or that the refined score is globally optimal.

### Scheduling model (`fig:problem`)

**Proposed caption.** From contact intervals to a feasible independent set. Five opportunities use distinct satellites and the indicated ground stations under a ground transition gap of 1. Ground resource conflicts produce the path `a–b–c–d`, with `e` isolated on another station. The selected independent set `{a,d,e}` has reward 10 and maps back to a feasible timetable; in particular, `a` and `d` respect the transition gap. This mapping applies to the modeled pairwise hard constraints.

This is a deliberately small constructed illustration, not an experiment or a source-derived C3 instance. The builder reconstructs the intervals through the implemented `temporal_graph` predicate and verifies all three conflict edges, selected-set feasibility, and reward. The graph and final timetable use matching labels, so resource compatibility can be checked directly.

### Method (`fig:method`)

**Proposed caption.** Certified representation–rule refinement with a fixed deployment interface. Aligned static interventions yield full-residual bound comparisons and accumulated strict requirements, including positive preservation evidence. A cycle in the exact feature quotient exposes concrete ranking arcs and equality joins that no scalar score over the current inputs can satisfy. Typed LLM feature proposals enter a minimum-cost master; every selected refinement is checked on the full quotient, and surviving cycles add new constraints. Rule proposals are then replayed against the evidence and assessed using complete-schedule quality and measured compiled work. The eligible representation, rule, and kernel are frozen; online execution reads only the current graph and uses compiled features, scoring, commitment, and closed-neighborhood deletion.

The diagram deliberately exposes unknown certificate outcomes, unresolved repair outcomes, the full-quotient separation feedback, and the distinction between representability and bounded-rule expressibility. The master objective is additive standalone feature cost; the joint selection criterion measures the actual compiled program. The figure describes the implemented mechanism, not a claim that it empirically improves every tested family.

### Full quotient recheck (`fig:repair`)

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

The builder's semantic checks cover the four conditional values, exact within-side base input equality, added X edges, unchanged satellite gap, neighborhood-edge counts, the two-round four-cycle repair, sequential update values, reference feature equality, and timetable feasibility. These are verification of the figure's factual content, not new experimental performance results.

### Final QA record

All seven PDF variants have one page, all PNGs load normally, and native XML parses from every export. The motivation PNG was re-imported through draw.io Desktop and exported back to native XML: the recovered diagram contains the same **63 editable cells** as the PDF's native model. Every final compact PNG was visually inspected after the layout changes; the method bodies and feedback caption fit, the coarse repair arrows show their directions, and both repair-round statements fit on one line.

| Main figure | Native PDF size (pt) | Placed image height | Placement |
| --- | --- | --- | --- |
| Motivation | 490.08 × 251.04 | 3.59 in | 504 pt full width |
| Method | 490.08 × 209.04 | 2.99 in | 504 pt full width |
| Repair | 490.08 × 186.96 | 2.67 in | 504 pt full width |
| Problem | 238.08 × 288.00 | 4.03 in | 240 pt column width |
| Compiler | 238.08 × 306.96 | 4.30 in | 240 pt column width |

These heights exclude the paper captions. Font sizes at placement are approximately 9.26–9.63 pt for full-width figures and 9.07–9.44 pt for column figures.
