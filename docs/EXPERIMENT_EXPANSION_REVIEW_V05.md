# Evidence-based expansion of the V05 experiments

This review reads existing immutable V04/V05 analysis records. It changes no programme, selector, experiment input, metric, analysis script or paper source. The new frozen-winner public/C3 transfer study was still in progress when this review was written; its outcomes are not used here. The late-layout security delta is complete, and further release scanning is paused until another final-ready signal.

The useful addition is an explanation of where the mechanisms work and where they fail. The original baseline table, matched-pilot table and complete-public-graph counterexample table should remain. More audit counts or delivery logs would not strengthen the scientific argument.

## Highest-value new main-text evidence: stratified pure cancellation

The following table is independently recomputed from the exact endpoint strings in `experiments/analysis/v04/summary.json`, `pure_cancellation.rows`. Both arms retain the **same unmatched component bounds**; only uncertainty from exactly identical common residual components is removed.

| TRAIN population | Comparisons | Strictly narrower | Median width before | Median width after | Strict before → after |
|---|---:|---:|---:|---:|---:|
| Standard | 216 | 197 | 100.5 | 23 | 0 → 0 |
| Dense/long | 108 | 0 | 43.875 | 43.875 | 17 → 17 |
| C3 | 72 | 2 | 17,060 | 17,060 | 16 → 16 |

**Suggested caption.** Pure component cancellation on TRAIN, fixing all unmatched bounds. Widths are in each context's original reward units; different weight scales preclude interpreting cross-population widths as a difficulty ranking. Narrowing need not certify a sign. No test-based programme change is made.

Exact checks performed for this review:

- All 396 `(pair_id, side, state_id, a, b)` keys are unique.
- For every row, the cancelled interval is nested within the uncancelled interval; saved width values equal the exact `Fraction` endpoint differences.
- Strict indicators match exact positive/negative sign tests in both arms.
- The three strata sum to 396 comparisons, 199 narrower intervals and 33 strict certificates in each arm, matching the frozen summary. The remaining outcomes are 61 exact ties and 302 unresolved comparisons.
- Exact stratum medians are `201/2 → 23`, `351/8 → 351/8`, and `17060 → 17060`; the pooled median is separately `86.75 → 36`.

This is a substantive boundary condition: 197 of the 199 improvements occur in standard TRAIN contexts, yet none becomes strict there. Dense/long cancellation removes some exactly known components but does not narrow an interval; C3 has only two narrowing cases. The theory guarantees removal of common uncertainty, not enough information about the unmatched residual to decide an action. The separate whole-residual/component strategy contrast, 10 → 33 strict, changes the bounding strategy and must not be attributed to isolated cancellation.

## Public quality: separate ranking loss from missing completion

The main table's metric remains failure-zero, equal-context reward relative to the strongest saved verified feasible witness. A 100% ratio is not an optimum certificate. Native seed means belong to the same graph context. They are not extra independent instances, and primary/native/classical total computational budgets are unmatched.

| Public population | Primary all-assigned reward % | Primary completed/assigned | Primary successful-subset reward % | Degree all-assigned reward % | Published leader, all-assigned reward % |
|---|---:|---:|---:|---:|---|
| DIMACS unit | 80.5284 | 17/18 | 85.2653 | 85.0409 | CHILS-ILS: 100.0000, 54/54 runs |
| DIMACS hash | 87.0737 | 17/18 | 92.1957 | 84.9152 | M2WIS: 100.0000, 54/54 runs |
| SATLIB unit | 32.9304 | 10/30 | 98.7912 | 98.8029 | CHILS: 99.9677, 90/90 runs |
| SATLIB hash | 31.0455 | 10/30 | 93.1364 | 92.1389 | CHILS: 99.9952, 90/90 runs |

Successful-subset columns above are **diagnostic**, not replacement primary metrics. They are recomputed exactly from the frozen `context_statistics` rows for the one-run constructive policy. In both SATLIB weight modes all ten successful primary runs are `uf20-91`; all ten `uf50-218` and ten `uf75-325` runs fail. Therefore the apparently competitive conditional reward covers only the easiest source family. It cannot support a quality comparison with Degree's 30/30 population. The public DIMACS unit primary also trails Degree among completed cases, so completion alone does not explain every transfer loss.

Preserve native failures as well: M2WIS DIMACS-unit completion is 48/54, WeightedBR DIMACS-unit/hash completion is 48/54 and 52/54. Their all-assigned values already include failure zeros. Higher successful-case reward cannot erase deployment failure. CHILS-ILS is an executed setting of the CHILS implementation, not an additional separately published algorithm. Free/rule-only controls remain project controls; they must not be labelled EoH/ReEvo reproductions.

Fresh primary reward is 99.4580/96.1072/97.5610% on standard/dense/C3, versus Degree 98.4743/94.4624/97.0380%. This is useful selected-program evidence. Free is slightly higher on standard/dense; its paired contrasts there cross zero. The C3 primary-minus-Free contrast is +0.1746 pp [0.0365, 0.3464], while primary-minus-Degree crosses zero. Published implementations and classical exchange attain higher fresh rewards. Some reduction-based native methods are also substantially faster on these inputs, so a general speed or quality advantage is unestablished.

## Feature evaluation and same-program execution cost

The following possible compact cost panel adds information not apparent from quality alone. The two columns execute **the identical frozen primary AST** and have identical traces/rewards on all 456 fresh contexts. These CPU entries are population medians, not paired speedup estimates. Work entries are population means of the declared feature-work proxy, not FLOPs or machine-independent bit complexity.

| Fresh population | Mean work, full interface → demanded | Median process CPU s, full interface → demanded | Mean-work reduction | Reduction in CPU medians |
|---|---:|---:|---:|---:|
| Standard | 413,374.01 → 261,040.38 | 0.392373 → 0.209108 | 36.85% | 46.71% |
| Dense/long | 871,747.03 → 824,211.13 | 0.282344 → 0.234991 | 5.45% | 16.77% |
| C3 | 1,311,257.96 → 1,161,521.33 | 0.674085 → 0.474095 | 11.42% | 29.67% |

The demanded evaluator skips unused numeric feature primitives while retaining charged static aggregate maintenance. Smaller savings on dense inputs therefore limit the benefit of slicing; they are not a reward improvement. A separate same-AST heap experiment gives paired context-median scan/heap CPU ratios 15.4511×/1.1871×/4.6110× for standard/dense/C3. Degree on dense graphs instead has ratio 0.8714×. The measured work proxy also worsens there (scan/heap 0.7822×), so priority/frontier overhead is retained rather than hidden. These two experiments must not be multiplied into an invented universal combined speedup.

The TRAIN Guard64 diagnostic makes the selection trade-off explicit: strict scalar agreement rises from 631/824 to 701/824, but relative work rises from 6.657 to 51.266 (7.70× primary work), while TRAIN reward falls from 99.033% to 98.871%. Both interfaces are acyclic. Neither greater agreement nor an acyclic representation implies greater schedule utility. The reached finite-pool regret enclosures overlap and have different coverage; they are not confidence intervals or a strict ranking.

SNAP supports a completion result, not a paired speedup. At five seconds, primary/Degree heaps complete 7/24 and 18/24 runs; at a separate thirty-second target they complete 12/24 and 24/24. Full scans complete 0/24 per AST at either target. No full-scan/heap timing pair is assessable. The fixed-source thirty-second extension does not replace failures in the original confirmation.

## Matched authoring benefit versus recorded model cost

All four-block comparisons retain all 144 original proposal slots and the same TRAIN selector. The fixed 216-context TEST population has 2,808/2,808 completed assignments. Its quality denominator is a verified common clique upper, **different from the V04 baseline-table feasible-witness denominator**.

| Arm | Full gate eligible/slots | Four-block TEST mean % | Total reported input (cached subset) | Total output tokens | Mean observed session wall s |
|---|---:|---:|---:|---:|---:|
| A: labels + join witnesses | 48/48 | 79.3790 | 482,830 (340,224) | 41,311 | 455.33 |
| B: labels | 48/48 | 79.3647 | 1,041,126 (847,360) | 25,143 | 334.82 |
| C: objective feedback | 40/48 | 78.7076 | 620,134 (479,360) | 22,075 | 281.16 |

Relations add +0.657068 pp overall, +0.513961 standard and +0.800175 dense, with block differences `[+0.892078,+0.892078,−0.047963,+0.892078]` overall. Explicit joins add +0.014309 overall, +0.007486 standard and +0.021131 dense; overall blocks are `[0,+0.009272,+0.047963,0]`. These are four-block descriptions, not CIs or model-population estimates. Two witness-versus-label block selections have identical deployment AST hashes and exactly tied outcomes.

Cached input is a subset of input; reasoning output is a subset of output. Neither should be added twice. Witness sessions use less reported input than relations sessions, but more output and longer observed completion time. Therefore saying simply that witnesses are “more expensive” is unsupported without a declared unified cost metric. Session wall includes service/concurrency effects, not measured inference CPU. All twelve sessions request the same configuration, but actual served-model metadata is unavailable. Equal settings/session/slot counts do not imply equal token or compute budgets. No monetary conversion or marginal cost-effectiveness claim is warranted.

All actual-only quotients are acyclic; the 48/48 versus 40/48 gate-yield difference is caused by included prior diagnostic requirements. None of the selected bounded scalar programs fits all 824 requirements. Every arm uses an LLM, so the pilot compares evidence delivery to an authoring system, not LLM versus non-LLM synthesis. The original regret tie-break selects the same AST as the primary-only ablation; it cannot receive credit for an observed quality gain. The prefix curves describe finite-bank TRAIN sample efficiency, not online improvement or TEST reselection.

## Public alias failures localize two distinct limitations

The fixed-program public diagnostic independently verifies all 67 strict comparisons. Thirteen complete unit-weight DIMACS graphs yield 2 strict, 28 exact ties and 74 unknown queries; 48 source-derived induced graphs yield 65 strict and 155 exact ties, with 164 absent eligible query slots. These are lexicographic, quota-limited samples and shared source graphs, not incidence estimates. They must not be pooled into a natural physical-obstruction rate.

For `brock200_2`, equal nine-input vectors and equal neighbour covers (23/23) conceal forced values 10/9. For `san200_0.7_1`, the new feature distinguishes covers 18/17, but the frozen rule prefers the action with smaller cover even though forced values are 30/25 in the opposite order. Thus one case lacks distinguishing information in the selected interface; the other is a scalar-ranking failure despite added distinguishing information. In the induced sample the primary splits 21/65 strict aliases, orders 13 correctly and 8 incorrectly, and ties 44. This demonstrates why a feature envelope is not a certificate of its induced action order. It does not prove that these sampled edges cause the primary's aggregate schedule losses: they need not be the actions chosen on its own rollout. All 200 physical-source alias queries remain unknown, so public algorithmic counterexamples cannot become a claim of certified natural scheduling incidence.

## Main-text discussion proposal (select paragraphs, not the entire report)

The following compact prose is 516 words under a simple English word/number count. For the root's current 450–550-word **total** expansion allowance, prioritize its first two paragraphs (199 words), then select cost or pilot sentences that are not already in the paper; reserve space for the separately frozen transfer evidence and related work. Do not duplicate the existing full counterexample/pilot tables.

> Cancellation improves precision unevenly. With identical unmatched-component bounds, 197 of 216 standard TRAIN comparisons narrow, reducing median width from 100.5 to 23 reward units, but none acquires a strict sign. Dense/long comparisons retain 17 strict certificates without any narrowing; C3 has two narrower intervals and unchanged strict yield of 16. The pooled 199 narrower intervals therefore do not represent additional certified preferences. Common-component uncertainty can be removed exactly while uncertainty about the unmatched continuation remains decisive. The separate 10-to-33 strict-yield comparison changes the bounding strategy and does not isolate cancellation. Widths use original rewards, so their scales should not rank families by difficulty.
>
> Public transfer reveals both ranking and computation limits. On DIMACS unit weights, the primary trails Degree even among completed cases. On SATLIB, it completes only ten of thirty cases per weight mode: all successful cases belong to uf20-91, while uf50-218 and uf75-325 time out. Successful-subset reward is 98.79%/93.14%, but the prespecified failure-zero means are 32.93%/31.05%. Reporting conditional quality alone would hide a source-family selection effect. Degree completes all thirty cases; published implementations generally achieve higher all-assigned reward. These observations preclude overall solver dominance and explain why evaluation must retain completion coverage alongside quality.
>
> The public certificates also distinguish missing information from an unsuitable ranking map. In brock200_2, equal base vectors and equal neighbour covers hide forced rewards 10 versus 9. In san200_0.7_1, covers 18 versus 17 distinguish the actions, but the primary's normalization reverses the certified 30-versus-25 preference. Among 65 induced strict aliases, the feature splits 21; the scalar rule orders thirteen correctly and eight incorrectly. Thus repairing an interface obstruction and choosing a useful scalar rule are separate tasks. These sampled competing edges need not be selected on the primary's rollout and do not identify the cause of aggregate loss. Physical-source queries remain uncertified.
>
> The matched pilot isolates evidence content more closely than the original authoring bank, but remains small. Labels improve the four-block mean over objective feedback by 0.657 points, with three positive blocks and one reversal; explicit joins add only 0.014 points over labels. Reported output totals are 41,311/25,143/22,075 tokens for witness/label/objective arms, with mean session completion times 455/335/281 seconds. Witnesses use fewer reported input tokens than labels, so these heterogeneous costs do not define a single cost-effectiveness ordering. Equal settings and slots are not equal compute. Every arm uses an LLM, and no model-population or LLM-versus-non-LLM effect follows.
>
> Execution improvements have a cleaner intervention: the AST and rewards are fixed. Demanded evaluation reduces mean feature work by 36.85% on standard contexts but only 5.45% on dense/long contexts. A separate heap experiment yields scan/heap CPU ratios 15.45, 1.19 and 4.61 across standard/dense/C3; Degree instead slows on dense inputs. Larger sparse inputs show improved completion, but no completed full-scan pairs permit a speedup estimate. Finally, Guard64 fits more TRAIN scalar orders yet uses 7.70 times primary work and has lower TRAIN reward. Acyclic representation, scalar agreement, scheduling quality and execution cost require separate measurements rather than a single claim of LLM improvement.

## Table emphasis and placement

1. Keep the seven-population executed-baseline table prominent. Bold exact quality leaders within each population, including exact ties; use the primary row's colour/name to locate the study policy, not to imply it is best. The verified leaders are: fresh standard CHILS/M2WIS/Struction/WeightedBR/CHILS-ILS/HiGHS; dense/C3 all those except WeightedBR; DIMACS unit CHILS-ILS; DIMACS hash M2WIS; both SATLIB modes CHILS. A displayed 100% still does not certify an optimum. Caption the seed/run denominators and failure-zero convention clearly.
2. Add the three-row pure-cancellation table near certification analysis. Its useful conclusion is heterogeneous precision with zero new strict signs, not a second aggregate success claim. This table can replace repeated pooled-width prose.
3. If space permits a small cost table, choose either the three-row same-AST demanded/full CPU-work panel or a three-arm authoring-cost panel. Do not add process/audit-check totals to the PDF. The existing pilot table should retain four block means rather than replace them with a pooled winner.
4. Keep source-derived public aliases separate from physical C3. The two-row complete-public counterexample table already communicates both information and mapping failures efficiently.
5. New winner transfer is a post-outcome exploratory extension of twelve already frozen programmes on the **already observed** public96/C324 populations. Once its immutable archive is complete and audited, report all four blocks/all arms and coverage. Do not combine its public/C3 observations with the original 216-context pilot population or use them to reselect programmes. Its primary denominator is the old verified clique upper and its secondary denominator the old feasible witness, so neither should silently replace the original pilot or baseline denominator. Duplicate winner ASTs remain assigned. Cost comparisons belong to the same-host extension; the older native-server timings cannot be treated as paired costs. A positive result would support bounded external transfer; a negative result must remain visible. The outcome-free protocol is `experiments/discovery/matched_transfer_exploratory_v05_001/protocol.json`, SHA256 `8f785558ace072936baf2e29b2c3585c1cf3fd8528036ad2398695f9cb061288`, with `freeze_receipt.json` and a separate source capsule under `experiments/source_snapshots/v05/`. These scope facts were supplied by the extension's owner while the study was running; no extension outcome was read here.

## Inspected source identities

These are current byte identities of the existing numerical source records used in this review. The underlying raw-archive hashes and audit scopes are retained inside the records and the original source reports; archives were not re-extracted for this review.

| Source | SHA256 |
|---|---|
| `experiments/analysis/v05/baseline_table_v05.json` | `0becb6d1b51474796c82c963d93d4ce43b7cafd01d3ba56d3e76fb305fce7b9c` |
| `experiments/analysis/v04/summary.json` | `8116ed245ab2fe612818d19a50493d75ad47e080d69d3ef57de0597d47abe090` |
| `experiments/analysis/v04/pure_cancellation_training.json` | `14e328cf6b3c8689013b74275956a29642eab57670d970629469afec256a65ef` |
| `experiments/analysis/v04/training_audit.json` | `bcb5ff31c6b33d4827c95a4d1f8dbeaf4fe3f0adfd782c33c375e5298db9041a` |
| `experiments/analysis/v04/heap_summary.json` | `429a9d7ecf1f44fc9962499e475259679dbe70ee8747bed6cdd598fd1b249a43` |
| `experiments/analysis/v04/sparse_heap_30s_audit.json` | `c8028f030221cade8fa8150ed86c15036d965a3cecc437efffc3419fbe0cd688` |
| `experiments/analysis/v05/matched_results_v05.json` | `5723d3a456dde62d690706c3d3821c66c07aaa60f1a3e1c2a6844f1ad891b9de` |
| `experiments/analysis/v05/matched_authoring_costs_v05_001.json` | `132b055a2ec492d6a5c42fccf93aca0f302c1934d3b9b56bd2bbb294faa4fbd5` |
| `experiments/analysis/v05/public_alias_audit_v05_001.json` | `0b258da79253abadfbb4b0db63e7ce4e428747262213ce7f392953b165f3f095` |

Supporting interpretation records read: `docs/BASELINE_COMPARISON_V05.md`, `docs/MATCHED_LLM_RESULTS_V05.md`, `docs/SELECTED_SCORE_AGREEMENT_V04.md`, `docs/HEAP_RESULT_ANALYSIS_V04.md`, and the current experiment section. No newly unfinished transfer result is read, and no further release-ready claim is made.
