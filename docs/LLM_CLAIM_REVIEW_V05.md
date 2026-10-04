# V05 independent review of the LLM contribution

Review date: 2026-10-03, Asia/Shanghai. Scope: actual authoring receipts, immutable V04 TRAIN diagnostics, fresh outcomes and frozen-action audits. This is a scientific claim review, not an acceptance prediction. No V04 programme or outcome was changed. New V05 authoring responses were not read or assessed while writing this review.

## Main finding

The user's concern is justified. The current results establish that an assistant authored executable structural heuristics, and that one selected programme improves several classical degree-rule comparisons. They do **not** establish that certified guidance makes LLM synthesis superior to ordinary LLM authoring, that the LLM discovered a naturally necessary missing representation, or that the resulting heuristic outperforms strong published MWIS systems. Better figures can explain the mechanism; they cannot supply that missing comparison.

The most defensible contribution is a **checkable interface between certified decision evidence and offline programme synthesis**, with a separate empirical assessment of the selected programmes. The diagnosis/finite-catalogue theorem, scalar rule fit, complete-schedule quality and implementation speed are four different claims. The manuscript must keep their evidence separate.

## Actual LLM participation

V03 has one cold assistant-authored batch per guided/free/rule-only arm, with 24 slots each. The receipt identifies Codex assistant model `gpt-6.1-sol`, root-verified inherited settings, and unavailable token counts. Candidate counts were matched, while authoring compute and later construction checks were not matched. See [AI assistance disclosure](AI_ASSISTANCE_V03.md) and `experiments/discovery/v03/model_provenance_receipt.json`.

V04 has **one continuing assistant authoring session**, 12 new proposals, root design feedback and revisions before V04 TRAIN outcomes. The controls reuse older 24-slot banks. The requests explicitly identify neighborhood packing/cover summaries, retained continuations, limited compute regimes and programme interfaces. Therefore the evidence supports composition of a supplied typed library, not an independently replicated discovery of new primitives. The final primary is:

```text
nc = clique_cover_weight(neighbors(root))
score = weight / max(0.000001, weight, nc)
```

This is an actual executed AST. It is not a model answer consulted at each scheduling step, a fine-tuned LLM or an online model planner. The deployed kernel has no LLM or conditional-oracle dependency. The V04 receipt reports zero external API calls for its assistant-turn authoring transport; that description must not be silently carried over to the new CLI authoring transport. V05 must report its actual CLI sessions/metadata separately.

## Claim-by-claim evidence

| Possible claim | Evidence | Defensible wording |
|---|---|---|
| The LLM participates in the method | Actual saved proposal ASTs and authoring receipts; selected AST executes in the kernel | “An offline assistant composes typed features and ranking rules from supplied evidence.” |
| Structural input expansion can resolve an information obstruction | Exact quotient theorem; constructed probe self-loops and full refined quotient checks | “Certified contradictions provide checkable structural synthesis targets on the diagnostic evidence.” |
| The method discovers indispensable missing structure in natural scheduling data | The actual-only 788-requirement base quotient is already acyclic; all 32 self-loops come from prior diagnostic probes; 200 broader natural alias queries remain unknown | **Not established.** Label the illustrations as constructed diagnostics and retain the natural-evidence gap. |
| The selected rule fits the certified specification | Primary strict agreement 631/824, with 193 violations; actual-only agreement 596/788 | **Not established as full fit.** An acyclic declared interface means a finite unrestricted score can fit, not that this bounded rule does. |
| LLM guidance improves schedule quality | V04 new guided bank versus historical, unequal control banks; no replicated generation study | Report the selected-programme differences below; do not attribute them causally to LLM guidance. |
| The reached-regret selector improves the primary | Primary-only and full guided selections are byte-identical | **No observed primary selection effect.** Retain this zero-effect ablation. |
| Cancellation improves evidence efficiency | 199/396 intervals narrow; median width 86.75→36 using identical unmatched bounds; strict certificates stay 33→33 | “Cancellation removes common uncertainty.” It did not increase strict yield in this isolated control. |
| Frozen heuristic avoids online model latency | Deployment has no LLM/oracle calls | Operational property, shared by classical executable solvers; not by itself a quality advantage. |
| Faster inference demonstrates better LLM synthesis | Demand/heap transformations preserve fixed AST traces on assessable pairs | Compiler/backend advantage, separately validated; not a causal authoring advantage. |
| Superior to published state of the art | CHILS/ILS/M2WIS/Struction/HiGHS reach strongest observed fresh rewards; Python method has poor public coverage | **Unsupported.** Display those real comparisons and failures prominently. |

## Selected-programme comparisons that can be shown

The following are percentage-point differences in the saved competitive reward ratio. Its denominator is the strongest archived verified feasible witness, not an optimum. Intervals are the original source/seed-cluster paired 95% bootstrap intervals; they are descriptive comparisons within this study, without a model-level causal interpretation or a new multiplicity claim.

| Population | Guided minus Degree | Guided minus Free | Guided minus Rule-only | Guided minus classical 1-to-2 search |
|---|---:|---:|---:|---:|
| Standard, 216 contexts / 36 seed clusters | +0.9837 [0.7850, 1.1711] | −0.0750 [−0.1826, 0.0351] | +0.5361 [0.3775, 0.6900] | −0.3777 [−0.4645, −0.2929] |
| Dense/long, 216 contexts / 36 seed clusters | +1.6448 [0.9286, 2.3577] | −0.1656 [−0.5659, 0.1964] | +1.5891 [0.8760, 2.3016] | −2.6213 [−3.2647, −2.0543] |
| C3, 24 contexts / 12 source blocks | +0.5230 [−0.7521, 1.9832] | +0.1746 [0.0365, 0.3464] | +0.8180 [−0.4095, 2.2131] | −2.0063 [−2.8626, −1.2101] |

The Free point estimate is slightly higher on standard and dense/long. The C3 Guided-minus-Free interval is positive, whereas the C3 Guided-minus-Degree interval crosses zero. These are different contrasts and must not be conflated. The C3 result is a new subset of one physical source, not independent satellites/seasons or a model-generation replication.

The selected programme has 18 positive, 191 zero and 346 unresolved finite-pool regrets on its 555 actually reached sampled test states. All 18 positive regrets occur in dense/long instances. A finite-pool interval does not measure all-action regret, entire-rollout loss or global optimality. Different programmes visit different states, preventing causal comparisons of their unconditional summary means. Large unmatched-component bounds are tied to the hash-verified executed sound oracle, with the archived independent-proof boundary described in [the action audit](FROZEN_ACTION_AUDIT_V04.md).

## What the revised visuals should answer

Three dense scientific illustrations can replace the former five: (1) one concrete physical intervention, its two conflict graphs, feasible action competitors and certified value reversal; (2) the actual offline evidence→LLM→typed AST→full-quotient/action/cost checks→freeze workflow, with a distinct deployment boundary; (3) a real programme decision case combining its feature calculation, scalar ordering, selected schedule and measured loss/quality. An LLM icon alone is not evidence of benefit. Numbers in a generated mechanism illustration must come from the checked example and retain a “constructed” label when appropriate; generated artwork must not invent experimental observations.

For results, a cited published-baseline table should carry quality, completion and cost, and the important method names should appear with their published references. A prompt-sample-efficiency curve is useful only if its proposal ordering and TRAIN-only prefix selection are clear. Runtime scaling or constraint-sensitivity curves address different questions and should not be presented as model-synthesis gains.

## New evidence study: matched cold authoring

The new frozen V05 protocol is a separate bounded pilot, not a retrospective repair of V04. It uses 4 paired authoring blocks × 3 arms × 12 slots, identical typed library/examples/feedback/selector, and 216 fresh temporal test contexts after a new TRAIN freeze. Arm A receives certified relations plus explicit equality-join witnesses; B receives the same certified relations and graphs without joins; C receives objective feedback without oracle labels. The full 824-label interface gate is the same across arms.

A−B isolates the incremental explicit witness guidance; B−C isolates the supplied certified labels. Invalid, missing and exact duplicate deployment AST slots remain failed search attempts. No outcome-based replacement, arm-specific repair, selection threshold tuning or old-TEST selection is permitted. The original protocol/packets are preserved; a pre-outcome transport amendment substitutes the same fresh ephemeral CLI transport for **all 12** cells after the collaboration capacity limit. The lone collaboration response is retained as an excluded unassessed transport pilot.

Four authoring blocks support descriptive replicated observations, not a strong claim about the population of LLM generations: an exact paired randomization/sign test with four pairs has coarse resolution. Test case bootstraps must not turn four authoring blocks into hundreds of independent model samples. Sessions may share one configured model service; token/latency matching is unavailable unless the actual receipts show it. Formal inference should preserve both authoring blocks and common source/seed clusters and disclose the small number of blocks.

This pilot can produce an honest positive or negative prompt-guidance comparison. If it is negative, retain it, keep the mechanism claim narrow, and redesign in another preregistered study with another fresh test set. No requirement to improve numerical results authorizes test-driven programme selection.

## Introduction and method rewrite recommendations

Suggested opening contribution sentence:

> We connect certified conditional scheduling preferences to offline programme synthesis through an exact test of representation sufficiency, so that the synthesis process can request a missing structural distinction before revising its scalar rule.

Suggested explicit LLM role paragraph:

> The LLM is an offline proposal generator. A prompt contains typed graph operations, observed scheduling feedback and, in the guided condition, certified preference relations with concrete feature-equality joins. It returns a structural feature interface and a deterministic ranking expression. Independent checks validate the interface, execute complete schedules and account for feature cost. The selected programme is frozen; online scheduling evaluates that programme inside a fixed feasibility kernel.

Suggested evidence boundary paragraph:

> Diagnostic instances demonstrate that additional structure can remove a certified representation obstruction. Natural scheduling comparisons assess the frozen programmes' quality and cost, but the observed natural strict bank does not itself establish an unavoidable base-representation contradiction. An acyclic expanded interface does not ensure that its selected bounded rule satisfies every label or improves all complete schedules.

In the methods, separate four boxes/paragraphs: certificate production; quotient/witness diagnosis; LLM proposal and uniform validation; schedule-quality/cost selection and freeze. Put authoring transport, unavailable usage and excluded-pilot incidents in Markdown engineering reports. In the experiments, retain essential replication/count asymmetries and gate/failure semantics so the scientific comparison remains reviewable.

## Inspectable sources

- [V04 authoring receipt](V04_PROPOSAL_AUTHORING.json).
- [TRAIN scalar agreement](SELECTED_SCORE_AGREEMENT_V04.md), `experiments/analysis/v04/selected_score_agreement.json`.
- [Independent evidence audit](EVIDENCE_AUDIT_V04.md), `experiments/analysis/v04/training_audit.json`.
- [Fresh/public analysis](RESULT_ANALYSIS_V04.md), `experiments/analysis/v04/summary.json`.
- [Frozen reached-action audit](FROZEN_ACTION_AUDIT_V04.md).
- [V05 matched protocol](MATCHED_LLM_PROTOCOL_V05.md), `experiments/discovery/v05/protocol.json`, original packet hashes and transport amendment.
