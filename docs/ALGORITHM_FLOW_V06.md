# V06 algorithm flow: semantics and native export audit

Created 2026-10-04 for the V06 draft. This is a procedure diagram, with no optimisation outcomes or performance claims. The V05 diagrams and manuscript sources were not edited.

## Deliverables

- `paper/figures/algorithms_v06.drawio`: editable native XML.
- `paper/figures/algorithms_v06.pdf`: one-page native vector export, 7 inches wide.
- `paper/figures/algorithms_v06.png`: native preview with the same editable XML embedded.

The authoring utility is the ignored `.research/build_algorithms_v06.py`; it reuses the installed Desktop CLI and metadata normalisers from `scripts/build_schematics_v03.py`. Only the new V06 assets are exported. Neither an image-generation model nor a generic raster renderer produced the PDF.

## Procedure encoded

1. **Offline evidence.** The paired graphs replay the same fixed/excluded boundary, with feasibility checked on each side. Common residual components cancel only within an individual graph. Sound difference enclosures produce strict labels when their sign is certified; ties and unknowns abstain. The exact quotient uses all retained strict labels. A cycle exposes concrete strict arcs and equality joins, rather than an unspecified contradiction. Acyclic evidence also reaches the offline authoring stage.
2. **Offline synthesis.** A finite offline LLM feature/rule batch undergoes static typed validation and the full quotient DAG check for its demanded interface: the base coordinates plus syntactically referenced additional feature coordinates. Rejected slots remain in the accounting and receive no replacement or hidden fallback. Passing the representation gate does not establish scalar agreement. Selection separately prioritises numerical TRAIN strict-label fit, exact family-macro schedule reward ratio `q`, charged work, and original slot. `q` here uses feasible schedule reward divided by the graph's total available reward, not the old V05 common-upper quality measure. The selected program is frozen before evaluation.
3. **Online repair.** All arms start from the common Degree incumbent and construct patches using the same outer policy. For a destroyed incumbent subset `D`, retain `Fout = I \ D`; the legal repair set is `R = V \ (Fout ∪ N(Fout) ∪ X)`. The capped region `R′` must contain `D`. The frozen local priority orders the greedy warm start and vertex pivot. The bounded search uses shared classical clique bounds and include-first traversal; the LLM does not generate these components. The online diamond's `Δ` means the exact local reward gain `w(J) − w(D)`, distinct from the offline conditional-completion difference. Only strictly positive, globally feasible replacements commit. A per-patch node cap may retain a feasible improvement before the next patch. Global time/work/search/patch caps or exhausted attempted passes return the incumbent. Conditional full-residual labels do not prove local patch pivot preferences.

The small dashed circuit is **separate optional exact catalogue repair**, not the practical bank's regeneration loop. Each exact additive-cost master solution is checked against the **full** quotient; a surviving cycle adds a concrete equality-join cut. Its minimum-cost claim requires the fixed finite catalogue, declared feature limit and exact master/separation conditions stated in the method. An unresolved or budget-limited master is not a proof of optimal repair. There is no connection from this optional circuit into the frozen practical bank.

No online LLM or full-residual certification-oracle calls are depicted or required. The diagram's return paths denote a feasible anytime incumbent, not a guarantee of globally optimal scheduling or exhaustive neighbourhood search.

## Geometry and export checks

- Native canvas: **700 × 295** logical units; three main lanes, with the optional circuit inset within the synthesis lane.
- Arial labels: minimum **14.5** logical units; headers 16. All label sizes were checked from native XML.
- PDF: **504.0 × 215.217755 pt**, one page. At `0.9\textwidth` for a seven-inch text width this is approximately **6.3 × 2.690 inches**.
- Actual PDF text matrices, not just the nominal canvas ratio, yield a minimum effective font of **10.350830 pt**, or **9.315747 pt** at that placement. Therefore a width below `0.9\textwidth` should not be used without checking the minimum placed font again.
- PNG: **2118 × 904 pixels**; loaded and visually inspected after final export. Decision text, retained-slot rejection, the optional join-cut cycle and the incumbent-return paths are legible. The online positive-gain and no-improvement paths both return to the shared patch loop.
- PDF resources contain fonts and vector graphics, with **no image XObjects**. The Desktop-rendered PDF was uniformly scaled without a raster conversion; extracted text was asserted equal before and after scaling.
- PDF Subject and PNG `mxGraphModel` metadata decode to **exactly the same native XML** as the `.drawio` file. Source XML parses, IDs are unique, and all edges have native `mxGeometry`. Metadata repair preserves page content/text and PNG pixel chunks.

| Asset | SHA-256 |
|---|---|
| `algorithms_v06.drawio` | `4747ed8c93216dd3d952b9acbbee37e2f8291d7a7f5d4d1f8703a6bb7b05299e` |
| `algorithms_v06.pdf` | `343211dff7fde6cc7f55d57798d7220a4d08ec2e8892133b4ba3262ce4f17fda` |
| `algorithms_v06.png` | `031ca4b2401c9eaab023e9b8b31f14ad0ca6c5556d10daf7fe1302f93de53ffe` |

Draw.io guidance read from the installed plugin's `drawio/drawio/1.1.0/skills/drawio/SKILL.md` and the official [native XML reference](https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/xml-reference.md). Explicit coordinates follow the requested compact publication geometry and the existing repository's native vector workflow. The requested native `.drawio` is retained for editing.

## Suggested caption

V06 procedure. Offline, within-graph component cancellation supports sound strict labels and exact quotient diagnosis; unknowns and ties abstain. Typed proposals pass a demanded-interface DAG gate before numerical TRAIN fit, schedule quality and charged work select a frozen program. The dashed full-quotient catalogue circuit is a separate optional exact routine. Online, common Degree initialization and shared restricted patches preserve feasibility. Frozen priorities rank local greedy proposals and search pivots; classical bounds and include-first traversal are shared. Strictly improving feasible replacements commit, while budget or patch exhaustion returns the incumbent.
