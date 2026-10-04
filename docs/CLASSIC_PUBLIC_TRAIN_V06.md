# V06 classical public TRAIN calibration

This is a server-only classical calibration experiment. It is excluded from
the LLM authoring packets, subsequent authoring supplements and the original
frozen 120-state TRAIN selector. No TEST scheduling, conditional oracle or LLM
call is authorized by this experiment.

## Registration and exact inputs

`configs/classic_public_train_v06_001.json` was frozen before any calibration
outcomes, SHA256
`e60f38761da24cac6be8858e08227ab3640be4cab05a1334dea4c2a74978895d`.
The source capsule is
`experiments/source_snapshots/v06/classic_public_train_v06_001_source.zip`,
SHA256 `fdd2a7baed510e54c95c99698758dfa6495f17c6a15aaa092e64dfbad18a8a31`.
The new runner is `scripts/run_classic_public_train_v06.py`, frozen SHA256
`e2048a61c073fad2e692d179511c30b92fc30f4bc196cf43f3c681d329376230`.
The unchanged shared repair kernel has SHA256
`c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3`.

All 25 WDP TRAIN sources from the pre-acquisition source-SHA split are used.
Their supplied maximum-weight-clique graph is complemented exactly, retaining
every vertex and original integer weight. This preserves the supplied raw
weighted objective; no rescaling or graph reduction is applied. Dummy contact
attributes only carry the public graph through the existing graph API and do
not assert a physical satellite interpretation.

All three exact-scalable UAI/MMAP TRAIN sources are used:
`Segmentation_12`, `Segmentation_13`, `Segmentation_16`. Their raw native MWIS
edges are retained. Each weight is parsed directly as `Fraction(raw_string)`
and multiplied by exactly 100000 before conversion to an integer. The returned
exact reward is divided by 100000 to recover the raw input objective. The other
75 of 81 UAI inputs fail the original common signed32 exact-encoding contract;
they remain inventoried and are neither rounded nor counted as zero-quality
algorithm failures. This calibration deliberately retains the original three
compatible TRAIN sources. A later input-only CHILS64 inventory check finds 14
additional exact-scalable sources (13 Grids and ProteinFolding_11), yielding
20 CHILS64-compatible inputs overall. Those additional inputs were not optimized
by this frozen calibration. Compatibility is solver-specific. UAI TEST inputs
remain unexecuted.

Before starting any optimization, the server independently verifies the raw
archive hashes, input graph/weight inventories, exact orientation, source bytes
and native executable identities. It then writes prepared TRAIN graph identities
and a separate execution freeze receipt. No source or input is repaired after a
solver outcome.

## Method and budget matrix

There are 28 sources × three nominal wall targets × 12 method/seed requests:
1008 assigned requests in total. Targets are 0.1, 1 and 5 seconds. CHILS,
CHILS_ILS and M2WIS each use seeds 1, 2 and 3. Struction, WeightedBR and the
shared-kernel Degree policy use seed 1. All native children are restricted to
one requested thread. All unsupported, failed and capped requests are retained.

CHILS and CHILS_ILS use a separately reviewed signed64 integer contract. In the
pinned compiled source, graph weights, neighboring-weight sums, gains and
incumbent costs use signed `long long`; all positive WDP totals fit that range.
The review includes the actual compile flags and source hashes in
`experiments/discovery/v06_native_width_001/inventory.json`. M2WIS, Struction
and WeightedBR retain the conservative signed32 total-weight contract. Thus
375 WDP requests are predetermined exact-encoding limitations. Such a row has
null reward, selection and feasibility and `solver_invoked=false`; it cannot be
used to claim an algorithmic quality advantage.

The Degree policy uses the same repair kernel with branch scope, 24 patch
vertices, destroy size 4, one expansion step, 128 nodes per patch, 512 patches,
65536 total search nodes, no work cap and enabled upper pruning. This is a new
performance configuration, registered before its outcomes. The original
authoring feedback configuration remains 0.5 wall seconds, 32 patches, 4096
search nodes and a 200000 work cap.

Native time targets are internal nominal wall targets. A separate 30-second
outer child guard is retained for every target. The native wrapper includes
exact METIS preparation, process startup, I/O and result validation. The Degree
cooperative wall timer includes validation, initialization, repair and final
checking; bulk operations may overshoot. Actual native child CPU, wrapper CPU
and wall time are recorded. Equal nominal targets are not matched end-to-end
hard deadlines, and C/C++ native versus Python implementation costs remain an
explicit comparison limitation.

Graph loading, input hashing, graph reconstruction and identity checking occur
once per source and have a separate shared receipt. They are not silently added
36 times to a per-policy time. Interpreter imports, preparation and worker-pool
startup are measured at batch level. Eight workers reserve half of the server's
16-CPU quota; the memory quota is 60 GiB. A whole-batch 3600-second guard only
protects against a genuine hang. Persistent per-source journals retain partial
results if a worker fails; missing predetermined requests become explicit
worker-error rows without a retry or replacement run.

## Completed cloud execution and verification

Cloud directory:
`/root/autodl-tmp/aamas2027_v06_classic_public_train_001`.
Detached launcher PID: 51333; optimization child PID: 51391. Execution completed
all 1008 requests in 232.762 seconds of policy-batch wall time. There are 549
checked feasible native outputs and 84 feasible Degree anytime outputs. The
375 predetermined encoding limitations remain null. There are no native-output,
runner or hard-guard failures. Degree termination records are 50 time budgets,
six patch limits and 28 searches without improvement in their attempted patches.
These are anytime stopping reasons, not proof of optimality.

The immutable downloaded archive is
`experiments/runs/v06/classic_public_train_v06_001.tar.gz`, SHA256
`86152347d4f8da14083c90fac8494909e0dde2feafcc09b4bd72ffbbd682039f`,
44,519,820 bytes. Server execution protocol SHA256 is
`415cd558c4b0fdf60ac4e2969559ad69888733362ff6a3adf6cfc3ef04f24dcc`.
The original launcher/worker logs, configuration, prepared graphs, per-source
loading/journals, source/executable bindings and completion are inside it.

`scripts/check_classic_public_train_v06.py` performs a separate, read-only audit
implementation without importing the project graph/runtime/solvers. It checks
the full 28 exact raw-source graph mappings, all 1008 predetermined request
identities, all 633 incumbent rewards and feasibility against original source
edges, exact native METIS identities and all 375 null encoding limitations.
It passed 19,959,970 checks with zero errors. Its receipt is
`experiments/analysis/v06/classic_public_train_check_v06_001.json`. This is an
independent implementation by the execution agent; it is not a separate-person
audit. No solver, oracle or additional scheduling run was used in verification.

One observed timing limitation is material: on WDP, median CHILS wrapper wall
times at nominal targets 0.1/1/5 are 0.598/1.509/5.521 seconds, whereas Degree
times are 0.100/1.000/2.204 seconds. Dense graph encoding/startup/checking can be
substantial relative to a small native internal target. These data support a
nominal-target and actual-cost comparison, not matched hard-wall claims. Raw
per-source rewards, seeds and timings remain available; means are not pooled
across WDP and UAI, and unsupported requests are not converted to zeros.

The research run has not been executed locally. Local verification was limited
to a three-node synthetic mapping/configuration contract without a scheduler or
solver call. No best-program selection, TEST tuning, optimality claim or LLM
benefit follows from this calibration protocol.
