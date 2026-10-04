# V06 R2: independent authoring audit prepared before completion

The independent auditor is `scripts/verify_refinement_authoring_v06.py`, SHA-256 `e1969e06145d8b893da8a227b99aa9a9774647ccba64722b44477297e0ea6bec`. Its intended full result is `experiments/analysis/v06/refinement_authoring_audit_v06_002.json`. **That full authoring audit has not yet been run.**

The frozen study is `experiments/discovery/v06_refinement_draft_003`. Protocol SHA-256 is `fd6214a89e15a59c6ec75e6348872c63b508a8b667076f03f0c8f933fcbd694f`; runtime binding SHA-256 is `829b79c7e6b34d652dd2334b565027e291dd5ec7f4cd0bc3c0b8151433104d78`.

The registration-only check passed **54 checks with zero errors**, recorded in `experiments/analysis/v06/refinement_registration_audit_v06_002.json`, SHA-256 `03364916bd8ce9b4aba72b0b2d6c571a8ea0800d79da0fcf215d7d579bb48ab7`. It opened only frozen protocol/runtime/source/packet inputs. No R2 session receipt, response, candidate content or tool history was opened or normalized. Thirteen additional synthetic in-memory access-disposition cases checked that the auditor permits a same-session packet read, rejects extra files/redirection/chained commands, and distinguishes failed pre-process ACL attempts from possible successful access. These tests used invented examples rather than authoring observations.

## Required completion gate

Full audit requires `authoring_completion.json` with the exact pinned protocol/runtime hashes, all fifteen fixed response identities, `all15_R2_requests_frozen_before_assessment=true`, identical requested settings, no assessment/retry and no TEST access. This validation occurs before any session receipt/event/response read. The audit must additionally wait for the controller's explicit all-fifteen completion notice. A registration-only result is not a substitute for this full audit.

The full audit independently reconstructs all 120 static positions without importing the R2 production loader or evaluating a feature/rule/graph. It retains missing, malformed, duplicate and transport-failed positions. The first four whole transport-complete blocks are selected from the five fixed blocks using receipt exit code, timeout and nonempty response bytes, independently of candidate syntax, fit, gate, quality or work.

## Evidence to inspect after freezing

- Every original response, last-message, prompt, packet, inline stdin wrapper, event stream, stderr and receipt is byte-bound. Original response bytes are never rewritten.
- Each session uses the fresh isolated namespace, one distinct thread/turn, registered CLI binary and requested configuration, without a controller model override or retry. The entire original packet remains available inline despite any duplicate file-read failure.
- Saved event usage and served-model fields must agree with receipts. Missing served-model metadata remains unknown; requested configuration does not establish actual served identity. Missing usage remains unknown. Cached tokens remain a subset of input, and usage does not count backend calls or establish monetary cost.
- Tool histories are inspected for actual file/browser/outcome access and shared writes. Unrecognized or potentially successful external access is a manual-review flag, not silently accepted. Failed pre-process/kernel ACL attempts that returned diagnostics only are recorded without being misclassified as successful data access; a forbidden-target attempt remains visible as a warning.
- Original finite wall-time/exit/timeout receipts are bound, not remeasured. This driver does not emit precise per-session UTC start/end timestamps; they must not be invented. Prompt/settings/slot matching does not imply equal tokens, latency or backend compute.

The first full audit output is preserved. If a tool type needs manual resolution, retain the original flags and append a separately bound reviewed report. No candidate may be repaired, replaced, retried, filtered by fit, or assessed before the all-fifteen freeze. R1's nine-of-twelve deployment failure remains unchanged.
