# V06 R2: completed independent authoring provenance review

The full independent author audit passes **479 checks with zero errors**. All fifteen fixed author requests completed, and all 120 original candidate positions are independently static-valid. This is a syntax/provenance result, not an eligibility, representation-fit or schedule-quality result. No candidate score, assessment outcome, gate, selection or TEST query was inspected or executed in this review.

Audit: `experiments/analysis/v06/refinement_authoring_audit_v06_002.json`, SHA-256 **`2c3327ae92e0deccabb054636bcabfd9e31ed317679837fc26b31243128b7f7c`**.

Auditor: `scripts/verify_refinement_authoring_v06.py`, unchanged SHA-256 `e1969e06145d8b893da8a227b99aa9a9774647ccba64722b44477297e0ea6bec`.

All-fifteen completion: SHA-256 `2b410d9293d4eeeb0bf39e40989025effae0012975f79ddfb89aec2e4a7f8582`, completed UTC `2026-10-03T19:24:05.539695+00:00`. It is bound to the frozen protocol `fd6214a89e15a59c6ec75e6348872c63b508a8b667076f03f0c8f933fcbd694f` and runtime `829b79c7e6b34d652dd2334b565027e291dd5ec7f4cd0bc3c0b8151433104d78`. Full audit ran only after that freeze and the controller's explicit completion notice.

## Sessions, accesses and original positions

All fifteen requests exited with code zero without a timeout. Their thread IDs are distinct. The first four whole transport-complete blocks are **[0,1,2,3]**, selected solely by the preregistered transport rule. Block 4 remains a retained, assessed fixed block outside the four-block matched cohort. No missing, malformed, duplicate or transport-failed raw position was found; no position was repaired or replaced.

Every response exactly matches its original last-message bytes. Packet, prompt, full inline stdin wrapper, receipt, stderr and raw events agree with their hashes. Each isolated workspace contains only its own unchanged packet. All original packet information was delivered inline in stdin.

Each of the fifteen author sessions attempted only a `Get-Content` read of its own supplied packet. All such attempts failed **before process creation** because of the recorded sandbox ACL failure. They returned no file content. The permitted input was nevertheless available inline. No successful external file, browser, outcome, other-session access or shared write appears in the recorded tools. There are no unknown tool types, unresolved manual-access flags or forbidden-target warnings. This is a statement about the available recorded author events, not an unverifiable universal backend assertion.

## Requested settings and actual reported authoring cost

All sessions requested the same `gpt-6.1-sol`, `openai` provider and `ultra` reasoning setting using the same registered CLI binary. There was no controller model override, adaptive supplement or controller retry. **The actual served model remains unknown for all fifteen requests**, since their raw events provide no model identifier. Requested settings must not be presented as proof of the served model.

Each session provides an original usage receipt. The matched four-block totals and mean original elapsed times are:

| Matched arm | Original slots | Reported input | Cached input (subset) | Reported output | Mean session wall seconds |
|---|---:|---:|---:|---:|---:|
| Witness | 32 | 215,828 | 160,896 | 65,452 | 638.386 |
| Relations | 32 | 256,987 | 186,880 | 64,714 | 700.232 |
| Objective | 32 | 273,967 | 200,704 | 42,768 | 421.561 |

The all-five-block totals remain in the audit. Do not add cached tokens to input totals, or infer backend-call count, monetary expense or equal compute from these receipts. The fixed slots/settings match; prompt lengths, actual tokens, latency and backend compute do not. The driver does not emit precise per-session UTC start/end fields, and this review does not invent them or remeasure latency.

## Remaining scientific gates

Authoring provenance is clear to proceed to the separately frozen R2 TRAIN assessment. Every original position must still be assessed under the unchanged `f640` interface and shared-kernel semantics. Joint eligibility, actual strict fit, quality and work remain separate outcomes. The uniform joint selector and uniform quality-only comparator selector retain their distinct roles.

Only four genuine witness-arm joint winners, one per preregistered matched block, can satisfy the proposed-method deployment barrier. Nonguarded quality-only W/R/O comparator policies do not repair missing framework winners. R1's original nine-of-twelve failed barrier, its identical assessed TRAIN quality and its genuine MANN information obstruction remain unchanged. R2 is targeted warm TRAIN repair conditional on that R1-selected seed, not cold independent authoring or a model-wide causal study.
