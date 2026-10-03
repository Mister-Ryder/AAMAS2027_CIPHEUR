# Problem Setting review, v0.3

The standalone section fragment is `paper/sections/problem.tex`. Its role is to give the reader a mathematically complete scheduling problem before the synthesis machinery appears. It contains approximately 468 prose words, counting the satellite footnote and treating each inline mathematical expression as one item; the compact figure caption adds 26 words. Displayed equations are excluded from this count.

## Definition and scope decisions

- A contact fixes the satellite, ground station, link interval, and nonnegative reward. Choosing it selects the entire given opportunity; interval endpoints are not decision variables.
- Source-derived rewards are original link durations. Synthetic rewards can be independent of duration. The paper does not reinterpret either as delivered bytes or priority-weighted traffic.
- The graph has one edge for every pair rejected by the declared resource predicates. MWIS is an exact reformulation only within this pairwise model. The section does not extend graph feasibility to arbitrary cumulative storage, energy, queue, or higher-order constraints.
- Resource configurations are static throughout each scheduling run. An aligned pair changes exactly one admissible parameter while holding contacts, resource identities, intervals, weights, and boundary semantics fixed.
- The fixed selected set is independent, the excluded set is explicit, and both sets contain valid contact identifiers. The same boundary must be feasible on both sides, although the residual available sets may differ.
- The conditional optimum includes the fixed reward and the entire compatible completion. Both compared actions are residual and adjacent on both sides. Individual feasibility is retained when the parameter changes.
- The frozen feature--rule program ranks the current residual contacts. The fixed kernel commits a maximum-score vertex and removes its closed neighborhood. Its output is feasible under the chosen graph predicates, and exhaustion makes the selection complete. This is a feasibility statement, not an optimality claim.

## Exact source-derived satellite semantics

The main text distinguishes model-specific graph construction from the algorithm's general pairwise assumption. The unusual source-derived satellite interval cases are stated in a compact footnote:

1. Contacts sharing a satellite conflict if their starts coincide.
2. With ordered starts, a later interval contained in the earlier one conflicts.
3. A crossing overlap `s_u < s_v < e_u < e_v` conflicts exactly when the overlap `e_u - s_v` is strictly less than satellite change time.
4. Nonoverlapping shared-satellite contacts conflict when their gap is strictly less than satellite transition time.

Consequently, sufficiently long crossing overlaps can be admissible under the frozen source model. The section preserves that meaning and does not replace it with the synthetic single-capacity overlap rule. All strict threshold comparisons match the original builder; equality at a threshold does not create a timing conflict through that case.

The supporting code is:

- `cipheur/model.py:11` and `:22`: contacts, weighted graph, and independent-set feasibility.
- `cipheur/model.py:62`: fixed/excluded boundary validation and residual availability.
- `cipheur/model.py:92`: the separate synthetic single-capacity temporal model.
- `cipheur/model.py:121`: aligned single-parameter interventions.
- `cipheur/v51_adapter.py`: original legacy modules remain authoritative for conflict predicates; original resource names, link intervals, and rewards are retained.
- `cipheur/study_data.py:73–83`: larger source-derived instances retain original opportunities and call the same frozen graph builder while changing one parameter.
- `E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/src/snsd_core/graph.py:196–221`: ground and satellite timing cases.
- The corresponding `data.py:40–45`: source reward equals link duration.

The accepted abstract and the published-only `paper/references_v03.bib` were read. No literature claim was needed in this definition section, so it adds no citation or unverified bibliographic entry. Related-work positioning remains with the introduction and related-work owners.

## Integration with the method section

The coordinator should input this fragment immediately before the method section. It owns `sec:problem`, `eq:mwis`, `eq:residual`, and `eq:conditional-value`.

At drafting time, `paper/sections/method.tex` still defines the graph, MWIS, boundary, kernel, intervention, and conditional optimum. Remove those repeated definitions when integrating. The acquisition subsection can begin with the incumbent rollout and shared-boundary replay procedure, referring to this section. The certificate subsection can begin with the oracle intervals around Equation~`eq:conditional-value` and proceed to full-residual lower/upper bounds. Keep its action relevance, invalid replay handling, query priority, strict certificate conditions, and proof arguments.

The figure builder is independently creating `paper/figures/problem_setting.drawio.pdf` and editable Draw.io XML. The figure environment uses label `fig:problem` and this caption:

> From contact opportunities to a complete feasible schedule: resource predicates create conflict edges; vertex weights encode contact rewards; an independent set selects mutually compatible contact intervals.

The schematic should show satellite/station-labeled intervals, the corresponding weighted conflict graph, and the selected compatible intervals. It is a problem mapping, not an experimental result or a synthesis architecture.

## Local review and validation

The section has three matched equation environments, one matched figure environment, balanced inline math delimiters and braces, and no citation commands. The figure reference has a matching label inside the fragment. A full manuscript compilation and visual check remain integration tasks because this is an input fragment and the diagram is being built separately. The MWIS and conditional-value labels must be unique after method deduplication.

No root manuscript, code, experiment, bibliography, Git state, or other section was modified by this writer.
