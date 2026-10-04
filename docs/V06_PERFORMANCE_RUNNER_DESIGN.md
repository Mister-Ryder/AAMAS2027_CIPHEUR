# V06 performance runner: two shared initialization tracks

`scripts/run_performance_test_v06.py` is prepared for review and has not executed
TEST optimization. Its source and plan have not yet been frozen, pending the
root's final configuration/population review. It provides a source/input freeze,
exact TRAIN-selection bindings and a root-owned launch barrier.

The core inventory is 216 fresh synthetic TEST endpoints, 25 WDP TEST sources
and three exact-scalable UAI Segmentation TEST sources. An optional additional
track includes all ten source-SHA TEST Grids inputs whose exact integer LCM
weights fit the source-verified CHILS64 contract, while retaining their signed32
limitations for other methods. C3 interval and legacy tracks are kept separate;
the root's intended final population choice includes both. The source
inventory never filters on solver quality. Native methods are CHILS,
CHILS_ILS and M2WIS at three fixed seeds, and Struction/WeightedBR at seed 1.
Fifteen repair policies consist of twelve genuine TRAIN-selected programs,
Degree, and two quality-only fixed-bank controls selected separately on TRAIN.
The control's failed interface gate is never relabeled as joint eligibility.
An absent quality-only control remains an explicitly missing baseline slot.

Every graph and nominal target 0.1/1/5 has 42 predeclared receipts:

- Eleven published native method/seed requests at the full nominal target.
- Fifteen policies with common Degree initialization and bounded repair at the
  full nominal target.
- One common seed-1 CHILS initialization at half the nominal target.
- Fifteen policies supplied that exact common CHILS incumbent, Degree-feasibly
  extending it and running bounded repair at half the nominal target.

The strong initialization track uses the unchanged kernel. It does not compute
a separate cold Degree candidate or choose the best of two initializations.
Every returned warm incumbent must be feasible and have exact reward no smaller
than the common supplied CHILS solution. A failed initializer makes the warm
track unavailable without a hidden fallback. An ordinary time/search/patch cap
retains the anytime incumbent; a program error remains `completed=false` with
any retained incumbent recorded for diagnosis.

The shared CHILS initializer is executed once per graph/target. Each standalone
warm pipeline is charged its measured initial native wrapper wall/self CPU and
child CPU plus its own repair wall/CPU. The actual shared batch cost is recorded
separately and must not be confused with a sum of standalone pipeline costs.
Graph loading is also measured separately once per source. Native preprocessing,
startup, output validation and cooperative repair overshoot remain explicit.
Nominal time targets are not matched end-to-end hard deadlines, and native
C/C++ versus Python implementation costs must be discussed.

The performance repair caps are branch scope, patch size 24, destroy size 4,
one expansion, 128 nodes per patch, 512 patches, 65536 total search nodes and no
work cap. These do not change the original .5-second/200000-work TRAIN selector,
candidate ASTs or authoring evidence. All unsupported exact native inputs retain
null rewards and selections rather than zero quality.

`plan-only` freezes sources, populations and both tracks without candidate or
solver access. `bind-selections` requires exact hashes of twelve genuine TRAIN
winners across three arms/four matched blocks and a separate controls selection.
`prepare-inputs` only materializes frozen graph bytes on the server. `server-run`
requires a root-created authorization JSON bound to the protocol, capsule,
deployment, both selection files and input freeze. Eight workers execute with a
four-hour whole-batch guard and persistent journals. All partial receipts and
unreturned predetermined assignment keys are preserved without retries.

The base core has 30,744 receipts: 244 contexts × three targets × 42 requests.
The additional ten Grids inputs add 1260 receipts, and each 24-context C3 track
adds 3024. With all ten Grids and both C3 tracks, there are 302 contexts and
38052 assigned receipts, before any outcome-based action. Local verification
has only counted the symbolic 126 unique keys for one toy source; no research
graph was optimized locally or on the server by this runner.
