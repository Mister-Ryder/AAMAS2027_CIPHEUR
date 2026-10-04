# V06b algorithm flow: common-incumbent initialization

Date: 2026-10-04. This is a pre-TEST presentation extension, not a new TRAIN-selected program, changed repair kernel or empirical result. No raw author response, candidate assessment or solver outcome was read. The original V06 native figure and both exports remain byte-identical.

## New assets and exact change

- `paper/figures/algorithms_v06b.drawio`
- `paper/figures/algorithms_v06b.pdf`
- `paper/figures/algorithms_v06b.png`

The only changed graph cell is **51**, the online entry: `Common / Degree I` becomes `Common / incumbent I`. Native diagram name/ID become `algorithms_v06b`. All other cells, labels, geometry, connectors, colors and font sizes match V06 exactly. There is no added box. The original explanation of evidence, demanded-interface gate, separate scalar fit, optional exact catalogue loop and shared local search remains in `docs/ALGORITHM_FLOW_V06.md`.

## Initialization scope

The frozen TRAIN and withheld-mechanism track retains its original common Degree initializer and unchanged selection. In the separately registered strong-initialization performance track, all frozen priority arms receive the **same verified CHILS seed-1 independent-set incumbent** on each task. CHILS uses a nominal target of `0.5T`, followed by the frozen repair kernel with nominal `0.5T`. CHILS is a published solver component (`grossmann2025chils`), not an LLM-generated initializer.

The existing `repair_schedule(..., initial=I)` interface validates the supplied independent set and completes it through the same Degree-compatible initializer before local repair. That completion, patch construction, local frozen-priority greedy proposal and vertex pivot, shared include-first traversal, classical bounds and feasibility checks retain their existing semantics. All program arms start from the same supplied incumbent; subsequent trajectories may diverge after different feasible improvements.

If native initialization fails, times out without a valid independent set, or cannot support the original input, the strong track is **unsupported** for that task. It does not substitute a Degree seed or another native solver. Unsupported assignments and their actual costs remain in the record.

Actual setup, native initialization, Degree-compatible completion and repair CPU/wall must be included in pipeline accounting. The two nominal fractions are timer targets; native setup/guard behavior and cooperative repair checks can overshoot them. This is not a claim of a hard matched end-to-end deadline or equal compute with a standalone published solver. No online LLM or full-residual certification-oracle call is introduced.

## Suggested caption

V06 procedure. Offline evidence and full-quotient diagnosis guide typed feature--rule synthesis; representation adequacy, numerical TRAIN fit, reward and charged work remain separate. The dashed catalogue circuit is an optional exact routine. Online, a common feasible incumbent enters the shared restricted-patch kernel; frozen priorities order local greedy proposals and pivots, while bounds and include-first traversal are classical. The mechanism track uses Degree initialization. The separately registered strong performance track shares a CHILS incumbent across arms before the same Degree-compatible completion and repair. Native initialization failure is unsupported, without fallback; actual pipeline costs accompany nominal time targets.

## Optional method integration sentence

> The same repair kernel also accepts a common independent-set incumbent supplied by a published solver for the strong-initialization performance comparison.

This sentence is a suggested draft integration only. `paper/drafts/v06/method.tex`, current manuscript sections, programs and production source were not edited for this figure task.

## Native export and verification

The ignored `.research/build_algorithms_v06b.py` reuses the established V06 authoring utility in memory with the two explicit substitutions above. Installed draw.io Desktop exports the native XML to embedded-source PDF/PNG; the existing metadata repair preserves page text/content and PNG pixel chunks. The PDF is uniformly scaled, with text parity asserted before and after scaling.

- Canvas **700 × 295** logical units; minimum Arial font **14.5** logical units.
- One-page native-vector PDF **504.0 × 215.217755 pt**; no image XObjects.
- Actual minimum effective PDF font **10.350830 pt**, yielding **9.315747 pt** at `0.9\textwidth` for seven-inch text width. Printed size then approximately **6.3 × 2.690 inches**.
- PNG **2118 × 904 pixels**, loaded and visually inspected. The changed incumbent label fits its original box; the remaining decisions, loops and return paths remain legible.
- PDF Subject and PNG `mxGraphModel` decode to the exact new `.drawio` XML. XML parses, IDs are unique and edge geometries exist.
- Independent native-cell comparison permits exactly the entry label change; all other cell attributes and geometry match. All three original V06 hashes were recomputed and match the original audit.

| V06b asset | SHA-256 |
|---|---|
| `algorithms_v06b.drawio` | `2204e2f7d6a6f870a5addb4fed316c3a65899b78261ded51c1e6e72d0e270a9e` |
| `algorithms_v06b.pdf` | `bfd961a623988d349574be202e96d59053432342a9b89c8e98d5bfc81d5ed543` |
| `algorithms_v06b.png` | `d31fe176d7fe0a5b443d25d7efa41402408db6321dfc5240e62eb20cede6f52c` |

| Preserved V06 asset | SHA-256, unchanged |
|---|---|
| `algorithms_v06.drawio` | `4747ed8c93216dd3d952b9acbbee37e2f8291d7a7f5d4d1f8703a6bb7b05299e` |
| `algorithms_v06.pdf` | `343211dff7fde6cc7f55d57798d7220a4d08ec2e8892133b4ba3262ce4f17fda` |
| `algorithms_v06.png` | `031ca4b2401c9eaab023e9b8b31f14ad0ca6c5556d10daf7fe1302f93de53ffe` |
