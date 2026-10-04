# Compact scientific panels (V05)

Presentation-only panels reuse existing, unchanged analysis arrays. No experiment, resampling, selection or numerical analysis was rerun.

| Panel | Native inches | Native font | PDF SHA-256 |
|---|---:|---:|---|
| `effect_gain_compact_v05` | 3.35 × 1.70 | Arial ≥9pt | `06e135de875c2454ed2b6b532b29c37d750ebce3d0755400def51b3830005a98` |
| `effect_trajectory_compact_v05` | 3.35 × 1.70 | Arial ≥9pt | `923da2453696c6deab2d8eab269013f6f5b1906e998f68b0054461c2601131c3` |
| `llm_yield_compact_v05` | 3.35 × 1.70 | Arial ≥9pt | `40b60d3444a7fbc2c4a794b398c5e8d26b60e819f3d3dcc5dc6bf26fa5594e21` |
| `llm_utility_compact_v05` | 3.35 × 1.85 | Arial ≥9pt | `176f289259be00d86cd12bd1c5cbd6f26abf26bfd4c68aba8c890fea1d3c0622` |
| `heap_scaling_compact_v05` | 3.35 × 1.70 | Arial ≥9pt | `fafb8a5ca175a6623e775daaf3b4b34364c911474c1618584a75fb8f9622d0e9` |

## Input identity and plotting verification

The saved TRAIN prefix curves agree exactly with the corresponding TRAIN curves in the final TRAIN/TEST report. All line x/y arrays and confidence-band polygon vertices were compared directly with the original JSON fields. The twelve four-block yield traces, twelve four-block utility traces, every arm mean, all original null utility prefixes and all 36 missing-prefix counts are retained. No intervals were recalculated.

Checks: `{"block_curves": 24, "confidence_band_vertices": 9, "line_x_arrays": 43, "line_y_arrays": 43, "missing_prefix_cells": 36}`. Every visible text artist is at least 9pt at the native width; all text extents stay inside the canvas. PDF dimensions and visual rendering receive a separate independent check.

| Unchanged input | SHA-256 |
|---|---|
| `experiments/analysis/v05/effect_curves.json` | `68e541ddec1d58f9cfb65c7d49de5ed7539a1b5c3aee773c4fd67127d3df64b9` |
| `experiments/analysis/v05/matched_train_analysis_v05.json` | `c831cfaa290f03dc5e0a5228be6821bc4b4141c3aca85d3835335d88c77acf76` |
| `experiments/analysis/v05/matched_results_v05.json` | `5723d3a456dde62d690706c3d3821c66c07aaa60f1a3e1c2a6844f1ad891b9de` |

## Placement and scientific interpretation

An independent panel-level reviewer repeated 131 exact checks after the coincident-marker adjustment: all 43 x/y pairs, nine confidence bands and 36 count-strip cells match the unchanged inputs; the 24 individual bank curves are included in those line checks. Independent PDF inspection confirms 9pt upright text and glyph boxes within every panel. The purple open circles and smaller blue squares expose the identical A/B yield coordinates without jitter. Final manuscript placement and page-level review remain the root editor's responsibility.

The final manuscript places independent vector panels in paired half-textwidth minipages, including the heap and transfer coverage panels in Figure 6. Shrinking below native width would reduce nominal text below 9pt. LaTeX supplies panel labels and captions; the panels contain no report-style prose footers.

The final placement uses the same .495-textwidth for all six result panels, with 9.3167pt printed chart text. The earlier single-column heap placement measured 8.9647pt and has been superseded. The table above describes native fonts. The sixth panel's source arrays, grouping checks and provenance are documented separately in `TRANSFER_PRESENTATION_V05.md`.

Effect panels concern the same 216 dense/long contexts; gain is primary minus rule-only, and prefix curves are primary minus Degree/rule-only/Free. The intervals remain paired source-cluster intervals. Prefix progress is eliminated-vertex fraction, not elapsed time or LLM learning. The full-population companion stays unchanged and available separately.

Pilot curves use original slots 1–12, retain four individual banks per arm and show arm-mean utility only when every bank has an eligible prefix. Null prefixes are gaps, never zero or fallback utility. The A/B/C missing-bank strip retains counts of four, three and one in objective-only early slots. Eligibility is declared-interface acyclicity, not full scalar ranking fit, and these TRAIN curves do not select prefixes with TEST outcomes.

The heap plot contains all three populations for the same frozen primary AST. Its ratios are means of per-context median full-scan/heap CPU ratios with the original confidence intervals. Execution parity and speedup do not establish LLM benefit, whole-schedule improvement or a valid sparse speedup for failed full scans.

Short legends: Bal. = balanced, Ground = ground scarce, Sat. = satellite scarce; Dense = dense/long; A Witness, B Relations, C Objective use the manuscript’s registered arm definitions.
