# V06 shared Degree repair: cloud TRAIN feedback

All 120 explicitly TRAIN graph snapshots from the frozen evidence input were
executed once on the authorized cloud server. TEST inputs were not
materialized or scored by the feedback runner. The resulting feedback is
available for the next matched authoring protocol; it is not a comparison
between synthesized priorities and does not establish an LLM advantage.

## Pre-outcome configuration and frozen implementation

The controller fixed `configs/repair_train_v06_001.json` before any V06 repair
outcome. Every assignment used the shared Degree initializer and local Degree
priority with branch scope, nominal 0.5 wall seconds, one expansion step,
at most 24 patch vertices, four destroyed incumbent vertices, 32 patches,
128 search nodes per patch, 4,096 total search nodes, 200,000 charged operations,
upper pruning enabled, and random seed one. No configuration or programme was
selected from these outcomes.

The source capsule contains only the seven actual static runtime dependencies
and the server wrapper, original full input bytes, root configuration and
new outcome-free execution plan. The original input contains both splits;
only the 120 `split=train` records are normalized into the execution targets.
The other 72 records are skipped before graph materialization. The original
runner checks source bytes captured before runtime import as well as the
prepared input/context/configuration/protocol freeze before execution.

- Kernel SHA256:
  `c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3`.
- Original feedback runner SHA256:
  `b1df66408db5f7ccfcea72f67b12b62e27baaf894567f38e86af2f4306c4aa82`.
- Root configuration SHA256:
  `3587db7ba52fe9f21f0171600fee120e5598b551ed06bbe674e7d0cb38e3cb4b`.
- Source capsule:
  `experiments/source_snapshots/v06/repair_degree_feedback_v06_001_source.zip`,
  SHA256 `c1908c18248d0be293588d30ed4bb56bdb647238547e3579dbf01f3f240196f3`.
- Server execution-plan SHA256:
  `b52e0ab7513ab14b89dea99e0d281a4320dc279cd327a88e0697d42c6a437a59`.
- Feedback protocol SHA256 (created outcome-free by server `--prepare-only`):
  `5d10011c743ff878d63331046747723bc2c7062af730a2d5518d2a9ccd93b412`.

## Actual cloud execution

Remote directory `/root/autodl-tmp/aamas2027_v06_repair_feedback_001`, launcher
PID 49524, eight workers under the 16-core cgroup quota and 60-GiB memory cap.
Python 3.11.17 and existing dependencies were reused. Detached persistent
logs preserve the prepare and execution output. A 3,600-second whole-run wall
guard was only a failure safeguard; it did not trigger. No job was interrupted,
no assignment was retried, and no conditional-value oracle or LLM was called
by the repair feedback.

All 120 assignments returned a feasible incumbent, with complete common
initialization. Runner and kernel errors were zero. The saved statuses are
119 `no_improvement_in_attempted_patches` and one `patch_limit`. Time/work/local
node exhaustion counts reported by the kernel are zero; the explicit patch
limit remains a separate stopping status and must not be hidden by describing
every execution as unrestricted search.

Three public induced-32 states improved the shared initial incumbent:

| TRAIN state | Initial reward | Final reward |
|---|---:|---:|
| `v06_public32|hamming6-2_unit` | 16 | 17 |
| `v06_public32|MANN_a9_unit` | 14 | 15 |
| `v06_public32|p_hat300-1_unit` | 3 | 4 |

The other 117 states did not change their initial incumbent. No improvement
within attempted restricted patches is not a proof of global optimality.
These small TRAIN states also cannot establish scalability or a contribution
from typed priority: no alternative priority has yet been evaluated in this
feedback run.

The original policy-batch wall time was 0.0882 seconds. The external wrapper
measured 0.4796 seconds for preparation and execution together, including two
interpreter/import launches, input/source checking, pool startup and receipt
writing. Those are distinct timing scopes. Shared batch startup is recorded
separately and is not falsely charged to each kernel's nominal 0.5-second
target. Each row retains actual kernel CPU/wall and task CPU/wall, with graph
materialization recorded separately. Nominal cooperative timing and reported
charged operations are not claims of equal compute across languages or hosts.

## Downloaded raw evidence

- Archive: `experiments/runs/v06/repair_degree_feedback_v06_001.tar.gz`, SHA256
  `e67be3ca5c91d6d5d413c4226de6ae047f0b63673d3b951d1cfd95de62f717fc`.
- Results SHA256:
  `080a662a735aae9e911a0e6910515738af4f83a0983825283de6568949384b5b`.
- Host receipt SHA256:
  `7e07fcf622345bc4c59f9751f198e8decf7912693b091ab286bf0c76299565ad`.
- Each row has `id` and `result`, where `result` is the complete JSON repair
  response with exact reward strings, retained selected set, initialization
  trace, patch trace, cap/status fields and meters. Any returned runner error
  would have remained an explicit `result=null` row.
- Original `protocol.json`, `freeze_receipt.json`, `completion.json`, contexts
  and results are unchanged. Host/source/root-config bindings and full-startup
  timing were appended as separate files.

This is TRAIN authoring feedback, not a withheld TEST evaluation. The final
authoring protocol and selected-program freeze must precede any future TEST
optimization or TEST conditional-certificate query.
