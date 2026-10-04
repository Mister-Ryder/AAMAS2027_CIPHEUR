# Editable algorithm flow: V05

This figure presents the procedure and its decision branches. It is a presentation revision of the unchanged V04 method, not a new programme, proposal round, selection rule, experiment, or result.

## Deliverables and placement

- `paper/figures/algorithms_v05.drawio`: native, uncompressed editable draw.io XML.
- `paper/figures/algorithms_v05.pdf`: native Desktop vector rendering with normalized placement, one page, **504.00 × 201.60 pt (7.00 × 2.80 in)**.
- `paper/figures/algorithms_v05.png`: native Desktop export, 2106 × 841 pixels, with the same embedded editable XML.

The native source uses Arial at 12.6/13 logical units. PDF text-state verification gives a minimum placed size of **9.0499 pt** and a maximum of 9.3372 pt at the intrinsic seven-inch width. Place the PDF at seven inches to retain this minimum; reducing its width also reduces the labels. The final PNG and an independent 144 dpi Poppler rendering of the final PDF were visually inspected. The text is selectable, the decisions are diamonds, and both repair and residual-update loops are explicit.

The mandatory draw.io skill was applied. Native draw.io Desktop performed the rendering; the existing `scripts/build_schematics_v03.py` helpers repaired export metadata. PDF decoded page content and extracted text were asserted identical before and after metadata normalization. Desktop's supported `--crop` flag removes blank print tiles. Its cropped vector page was then uniformly scaled by 504/504.95999 to the requested seven-inch width, and less than 0.1 pt of blank outer top border was trimmed to the 2.8-inch height. This retains the native vector rendering and exact label characters; it does not redraw the diagram or distort its aspect ratio. Label-character parity was asserted after serialization, and the final PDF was independently rendered to verify the blank-border trim. The PNG retained its original compressed pixel stream. Embedded XML in both final exports was checked byte-for-byte against the `.drawio` source. The explicit request for editable source and both exports takes precedence over the skill's default cleanup of standalone sources. All V04 schematics are preserved.

| Artifact | SHA256 |
|---|---|
| `algorithms_v05.drawio` | `6fb6305e71cb4d40bd415133585b5b68bd7404fb05e319e4275931232298afa1` |
| `algorithms_v05.pdf` | `7be287b0e0e0a059b3ae58bfd89d7e7689110dc6daf7bfe8ef649d3ad60d1f62` |
| `algorithms_v05.png` | `8cba65d4bb1c4feaa4c9dc2417fbdcfe835b7af96943124efb365c4d42efba1a` |

The final presentation follows the request for short action/decision labels: phase headings were shortened, and the unrestricted finite-scorer existence qualification is carried by this audit/caption rather than a paragraph inside the repaired-interface node. There are no paragraph blocks in the diagram.

## Scientific reading

**Evidence.** The paired graphs replay the same feasible fixed and excluded sets, F/X, for the tested actions. Each conditional action comparison uses sound completion enclosures. “Same-G cancel” refers to identical residual components shared by the two actions **inside one graph**; it never subtracts components across different graph configurations. Only a strictly signed enclosure enters the ordering requirements. Unknown or non-strict comparisons, including certified ties, abstain from producing a strict label. The exact quotient merges equality classes of the complete declared feature vector and retains the strict requirements. Its witness consists of concrete occurrence endpoints for equality joins and strict arcs.

**Implemented bank.** The solid middle lane is the joint feature/rule method. An offline assistant session authors typed feature and score AST proposals; invalid candidates are rejected, and a cyclic full declared-interface quotient makes a joint-bank candidate ineligible. The historical rule-only and classical comparator arms are not silently forced through this joint-bank gate. The V04 authoring receipt records one continuing `gpt-6.1-sol` assistant session, with feedback before programme freeze, rather than external LLM API calls. No numerical outcome or model effect is depicted here.

The TRAIN box uses complete feasible-schedule quality, demanded feature work, and the actually reached finite-pool completion audit. It depicts **selection dependencies**, not a claim that a preliminary quotient filter saved all TRAIN evaluation: in the implementation, the fixed bank's TRAIN schedules and reached states are measured before the information audit and final eligibility/selection step. Unknown regret is retained and is not a hard exclusion gate. The finite-pool regret enclosure does not bound every action. Acyclicity asserts the existence of an unrestricted finite pointwise scorer, not perfect agreement of the selected bounded AST with all certified labels or globally optimal schedules.

The final bank is fixed before TRAIN outcomes. The practical cycle branch therefore ends at **exclude**, rather than inventing automatic LLM regeneration or a new bank after those outcomes. Initial certified quotient witnesses can inform the pre-freeze proposals. The freeze box records the selected feature interface, score AST and execution kernel; later audits do not alter them.

**Separate exact repair.** The dashed row is the independently implemented finite-catalogue subroutine and its theorem, not the principal bank-selection algorithm. An exact minimum additive-cost master, subject to the declared feature-count cap K, is separated by a **full quotient reconstruction after every master solution**. A surviving cycle yields a valid cut using concrete equality-join endpoints, and the master is re-solved. Feasible termination certifies the scoped minimum additive feature cost and a DAG on the saved finite evidence. The “unresolved: stop” status includes master-budget unknown or catalogue/cap infeasibility; neither is relabelled as a successful repair. This guarantee does not optimize nonadditive shared-DAG execution cost, the bounded score grammar, test quality, or all future residual states. The minimum repaired interface is a separate ablation in V04.

**Frozen online construction.** Current residual candidates are scored by the demanded typed evaluator, the maximum-score feasible vertex is committed, its closed conflict neighbourhood is deleted, and maintained graph/features are updated. The residual-empty diamond returns a feasible schedule; otherwise the loop continues. The initial F/X restrictions and selected programme are preserved as commits extend the chosen set and remove residual candidates. There are no online LLM or completion-oracle calls. Feasibility follows the conflict-graph invariant, not score optimality.

## Source correspondence

- Sound envelopes and pair certificates: `cipheur/oracle.py`, `solve`, `local_bound`, `certify_pair`.
- Actual-boundary acquisition and same-state replay: `cipheur/residual_evidence.py`, `rollout_states`, `acquire_rollout_evidence`.
- Shared-component cancellation: `cipheur/relevance_synthesis_v04.py`, `CancelledCompletionOracle`.
- Quotient diagnosis and concrete witness joins: `cipheur/refinement.py`, `diagnose_occurrences`; `cipheur/representation.py`, `diagnose_representation`.
- Exact catalogue master/full quotient separation: `cipheur/refinement.py`, `minimum_cost_vector_refinement`, `minimum_cost_refinement`.
- Typed syntax, evaluation and programme schema: `cipheur/graph_features.py`, `FeatureRuleProgram`.
- Fixed-bank TRAIN evidence, eligibility and near-tie selection: `cipheur/relevance_synthesis_v04.py`, `_information_audit`, `select_candidates`, `run_train`.
- Demanded numeric evaluation and residual updates: `cipheur/compiled.py`, `CompiledEvaluator`, `schedule_compiled`; the frozen score-local heap extension preserves the score/trace invariant described in the method.

## Suggested paper caption

**Algorithm flow.** Sound strict evidence exposes equality-join obstructions; typed offline proposals are gated by their full declared-interface quotient and selected using TRAIN schedule quality, feature cost, and reached finite-pool audits. The dashed subroutine performs scoped exact catalogue repair with repeated full-quotient separation. Frozen online construction uses only demanded typed scores and feasible residual updates; acyclic interfaces do not guarantee perfect bounded-rule fit.

No paper section, frozen programme, data archive, production implementation, or V04 figure was edited for this figure. The ignored authoring helper is `.research/build_algorithms_v05.py`; the native XML is the complete portable editable source.
