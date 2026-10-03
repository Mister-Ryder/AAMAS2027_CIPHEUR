# Independent v04 training and public-input audit

The initial audit covers the completed TRAIN archive, preserved source, prespecified public/fresh INPUTS, and native fixtures before fresh outcomes. The later completed-fresh subsection is a separately authorized outcome audit. Neither phase changes selections or reruns scheduling studies. Audit scripts: [verify_v04_training.py](../scripts/verify_v04_training.py), [verify_public_inputs_v04.py](../scripts/verify_public_inputs_v04.py), and [verify_advanced_results_v04.py](../scripts/verify_advanced_results_v04.py). Structured TRAIN/input outputs: [training_audit.json](../experiments/analysis/v04/training_audit.json), [pure_cancellation_training.json](../experiments/analysis/v04/pure_cancellation_training.json), and [public_input_audit.json](../experiments/analysis/v04/public_input_audit.json).

## TRAIN population and immutable freeze

The archived TRAIN population contains33 pairs/66 unique id-side contexts:12 C3,12 each of three standard temporal regimes, and6 each of three dense/long temporal regimes. Every context contains all93 unique candidate rows:12 new guided proposals,24 free,24 rule,24 enumeration,5 classical rules, and4 prior guided controls. Of6,138 schedule attempts,5,996 complete and142 retain null value, work, selection, and trace. Failures receive the declared selection penalty; no partial schedule or fallback is substituted.

All30 executed Python hashes, including compiled.py, exactly match the preserved relevance_v04_source.zip. Input-config bytes match the execution receipt, saved-config bytes match the freeze receipt, and both parse identically; their different hashes reflect serialization, not different parameters. Candidate-bank bytes and each of93 canonical program hashes match. Saved TRAIN freeze/assessment/completion local copies equal archived semantics. The source is copied byte-identically to experiments/source_snapshots/v04/relevance_v04_source.zip, SHA-2568b023844fb18dbb18947a838687a1dccc98045bc3a671c5816e769c59e93738f.

The independent audit checks schedule feasibility/reward, every trace boundary and remaining count, graph identity, recorded source states versus actual trace prefixes, all finite action-pool comparisons, exact rational cancellation arithmetic, outward floats, strict labels, and regret endpoints. Small components of at most12 contacts additionally receive independent exhaustive optimization;1,002 distinct component subproblems are checked. Large component upper endpoints remain computational receipts tied to executed source because the archive does not save every branch-and-bound frontier certificate. Feasible lower witnesses are directly verified.

Information replay reconstructs all824 requirements and668 endpoint occurrences. The base quotient has622 classes,812 arcs,32 strict self-loops and is contradictory. The788 new actual-action requirements alone have594 classes,788 arcs, no self-loop and an acyclic base quotient. A standalone implementation of the13 graph operations appearing in the banks recomputes all93 candidate full quotient diagnoses; every eligibility gate matches. All32 base self-loops originate from retained prior probe evidence rather than establishing newly discovered natural obstruction.

Every candidate assessment is recomputed using equal-family training quality, shared degree-rule work normalization, timeout-relative-work100, cost penalty.002, actual-reached finite-pool regret only, and a.002 primary tie band. All selections reproduce. Main guided_v04:1 is v04_upper_ratio, program SHA-25690079f0c7342f290c5858ff49b711f9b4cef96d028b260b8d1a2fdea13d463b6. It completes66/66, has macro training quality.990334104, relative work6.656695017, and primary utility.979020714. Its regret upper is4.238066428 after mean-contact-weight normalization; this upper bounds finite-pool regret only, not regret against all feasible actions. Unknown comparisons are335 across84 reached audited states.

Guided main and guided primary-only ablation are byte-identical. The secondary criterion therefore has no demonstrated selection effect for this arm. It changes selected IDs for enumeration, rule, and prior guided controls within their respective declared bands. No global guidance or secondary-criterion improvement follows from construction alone. Saved test_accessed=false, test_outcomes_read=false, and no-validation/test-selection declarations support provenance but cannot prove every human information access. Method design is explicitly informed by prior qualitative v03 failures; it is not claimed blinded to them.

## Cancellation mechanism: strategy contrast and pure control

The saved396 matched TRAIN comparisons contrast a zero-search whole-residual envelope with a zero-search component strategy. Whole-residual strict labels number10 versus33 for components; widths are narrower327/equal38/wider31, with medians101.5 and36 reward units. This contrast includes decomposition/envelope ordering, so it cannot isolate cancellation or claim interval domination.

The pure control retains exactly the same saved unmatched-component zero-search bounds on all396 distinct comparisons. It adds identical common-component intervals to both conditioned completions before independently subtracting, then compares that interval with exact removal of common uncertainty. Common bounds are reused where saved; otherwise a deterministic zero-search weight-greedy feasible witness and degree/weight-ordered disjoint clique partition are computed once per state/component. All newly computed clique edges, partition coverage, rational bounds and lower witnesses pass; no oracle search or reoptimization of unmatched bounds occurs.

| Quantity | Uncancelled with identical component bounds | Exact cancellation |
| --- | ---: | ---: |
| Median interval width |86.75 |36.0 |
| Strict comparisons |33 |33 |
| Strict gains/losses from cancellation | — |0/0 |
| Strictly narrower intervals | — |199/396 |
| Remaining unresolved / exact ties | — |302/61 |

All396 cancelled intervals are contained in the corresponding uncancelled interval. The control removes2,981 common-component occurrences and11,706 vertex occurrences. It uses887 new offline zero-search common-component calls, zero expanded search nodes, and2,094 reused bound occurrences. Saved audit receipts report40,275 membership-check units and measured local wall time; these are audit costs and cannot be treated as deployment savings. Pure cancellation supports uncertainty reduction in this TRAIN sample, with no observed strict-yield gain. The complete TRAIN audit passes431,596 invariant checks with no errors.

## Public input and published baseline integration

All96 prespecified records are present:36 DIMACS records from18 originals and60 SATLIB records from30 lexicographically prespecified instances. Unit and hash-weighted versions share exactly the intended conflict graph. An independent decoder reconstructs binary lower triangles and clique complements; an independent pairwise reduction reconstructs same-clause and complementary-literal conflicts from CNF. Raw source/member hashes, archive membership, selected filename order, contact IDs, exact unit/SHA-derived weights1–20, and native conservative integer-weight range all match. Public-input audit passes49,242 checks with no errors.

The SATLIB parser's initial percent-terminator bug was found on official uf20-01.cnf and corrected before this completed96-record input collection. The independent parser also handles percent/end-zero syntax. Tiny literal-graph reductions were previously checked against exhaustive MAXSAT on empty-clause, tautology, and repeated-literal fixtures; binary fixtures checked a byte boundary and rejected truncation. The official DIMACS layout is documented by [bin2asc.c](https://archive.dimacs.rutgers.edu/pub/challenge/graph/translators/binformat/ANSI/bin2asc.c); datasets originate from [DIMACS](https://archive.dimacs.rutgers.edu/pub/challenge/graph/benchmarks/) and [SATLIB](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html).

Independent raw-output parsing of the four saved native smoke runs selects vertices0 and1 on a weighted three-vertex star, objective30, which is its exact tiny-graph optimum. The CHILS one-based-ID output and M2WIS/Struction/WeightedBR partition flags therefore have the correct orientation; wrapper objective comes from original graph weights. Native outputs remain checked feasible incumbents, with exact_optimum_claimed=false. Fractional-weight adapter fixtures separately checked exact integer scaling, fixed/excluded filtering, invalid output rejection, and empty residual behavior.

These are genuine implementation adapter checks, not new ablation aliases. The final native receipt supplies pinned commits, exact binary hashes, GNU9.4.0, CMake Release caches, the CHILS Makefile, and clean tracked-worktree diff/status receipts for KaMIS, CHILS and KaHIP. All three clean receipts pass. The upstreams are [CHILS](https://github.com/KarlsruheMIS/CHILS) and [KaMIS](https://github.com/KarlsruheMIS/KaMIS). Fixed short budgets and CHILS population4/thread1/alternation.1 differ from default/recommended runtime regimes; report published implementations under the declared experimental limits, without compute-matching claims. Public graphs test zero-shot algorithmic transfer; they do not establish satellite physics, and hash weights are explicitly benchmark extensions.

Raw hashes were checked against saved receipts for every source; only previously inspected official samples were independently downloaded. The audit does not authenticate all48 origin downloads independently. Public/generated-program performance is outside this input audit and remains unread here.

## Native fractional/boundary fixtures

The32 independently exhaustively checked fixtures have5–12 vertices with positive quarter-integer weights, fixed commitments and exclusions. All128 assigned adapter attempts reproduce exact METIS input hashes/scales and pinned executable hashes. Case27 has an empty residual: four wrapper shortcuts return only fixed commitments, so the receipt represents124 actual executable invocations and4 shortcuts, not128 native executions.

CHILS, Struction and WeightedBR each complete32/32 assigned fixtures (31 native invocations and1 shortcut), all at the independently obtained tiny optimum. M2WIS completes28/32 (27 native invocations and1 shortcut), also at the tiny optimum; cases0,12,24,30 terminate with returncode−11 and retain null reward, selection and feasibility. These crashes are preserved failures, not discarded cases. Exact original-weight objective, original-graph feasibility, boundary commitments, output orientation and every completed result's reward≤exhaustive optimum pass. The tiny-fixture optimum checks do not imply solver optimality on larger tests. Local binaries are not available to this auditor for byte rehash; source/build and executable identity are verified as archived receipts.

## Fresh input separation before evaluation

The fresh frozen protocol yields66 validation pairs/132 contexts and228 test pairs/456 contexts. Each split has standard and dense/long temporal profiles across three resource regimes at64,128,256 contacts, plus12 C3 pairs at64,128,256,512. Every pair's contact alignment, canonical contact fingerprint, both graph hashes, exactly one changed parameter and saved edge intervention are independently checked. Every temporal conflict graph is rebuilt from resource/time predicates. Fresh protocol config bytes exactly equal those preserved in the TRAIN source zip; the frozen-program receipt byte hash is2f4379e782413a2ba68222314ec674163f91a5ffcf75c7d74062388dc601987b.

All12 supplied prior data inputs are reread from their data.json payloads only. Input hashes match the prior manifests, including every assigned input contact in partial v03 archives. Their union contains40,886 unique original C3 IDs; all5,760 new IDs are disjoint from this union and each other across fresh validation/test. No new graph/contact fingerprint matches a prior instance, and synthetic seeds are disjoint from every supplied prior seed and across fresh splits. Shared seeds across regimes remain deliberate statistical clusters.

All48 fresh C3 graphs are independently rebuilt with the SHA-verified original data/graph predicates; each contact's weight, resource names and start/end agrees with its original arc. The C3 CSV hash matches both prior-source and fresh-source receipts. The audit checks the explicitly supplied inventory; completeness of all prior human exposure remains a provenance obligation. Generation records zero oracle calls and outcome_filtering=false. Fresh inputs and native fixtures are saved in [fresh_input_audit.json](../experiments/analysis/v04/fresh_input_audit.json); no fresh result file is read by this audit.

## Completed fresh v04 comparison

The separately authorized outcome audit reads `advanced_fresh_v04_001.tar.gz`
through streaming tar handles without extraction. It verifies **859,168**
invariants with no data errors. The exact executed manifest matches all34
Python modules in `advanced_v04_003_source.zip`; original-config bytes also
match the preserved pre-execution source package. TRAIN-freeze bytes remain
identical to the independent pre-test audit. Every frozen AST is unchanged;
three additional controls have exact source payload receipts and matching
canonical typed ASTs. Their programme hashes use spaced canonical JSON, whereas
the TRAIN bank uses compact canonical JSON; this is a serialization distinction,
not an AST mismatch.

Short-phase assignment is complete:456 unique id-side contexts and15,048
method rows, exactly33 per context. These comprise five published settings
(CHILS concurrent, CHILS ILS, M2WIS, Struction, WeightedBR), each with seeds1/2/3,
and18 deterministic programme/ablation/classical/local/numerical rows. The
prespecified30-second native subset contains20 contexts and600 rows, exactly30
per context; CHILS ILS is a short-phase setting only. Constructive CPU5, MILP10,
and local-search2 limits remain unchanged in the native long phase. Context and
method counts, phase result-byte hashes, boundaries, graph hashes, seed counts,
completion summaries, and every null failure are independently checked.

The primary and same-AST full-interface ablation complete all456 short and20
long contexts. Every complete action trace, selection and exact reward matches.
The primary-only selection ablation is also byte-identical to the main guided
selection and has identical completed traces; there is no observed secondary
selection effect for this arm. Trace state/count checks are independent of the
compiler; this audit does not rerun all candidate ranking evaluations.

All24 distinct test C3 graphs are reconstructed locally from the pinned original
physical source. Every one of **1,008** completed C3 selections across both
phases is independently submitted to that original verifier. Graph edges and
all archived feasible/conflict/duplicate/invalid receipts match; all completed
selections pass. Each completed native result also reproduces exact scaled
METIS input hash, original-contact output mapping, executable identity, solver
seed/time flags, and CHILS population4 or ILS population1 setting. These are
genuine native invocations, not locally renamed heuristic rules. Binary identity
is matched to archived preflight/execution hashes; the remote binaries are not
available locally for an additional rehash.

Every formal clique partition is independently checked for nonempty/disjoint
cliques, exact residual coverage, all clique edges and exact rational upper
weight including the fixed boundary. Every best-observed lower witness is
feasible and has the saved exact weight. All456 short and20 long HiGHS runs have
status0 numerical endpoints. Only **2/456** short contexts have a feasible lower
weight exactly equal to the independently verified clique upper; **0/20** long
contexts do. Status0 and100% best-observed reward therefore do not become broad
formal-optimality claims.

| Fresh population | Primary completed | Primary competitive reward | Degree reward | Struction reward | Primary / Struction median wall, s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard,216 contexts |216/216 |99.4580% [99.3612,99.5504] |98.4743% |100% |0.2091 /0.0088 |
| Dense/long,216 contexts |216/216 |96.1072% [95.5756,96.6171] |94.4624% |100% |0.2352 /0.0152 |
| C3,24 contexts |24/24 |97.5610% [96.5651,98.4777] |97.0380% |100% |0.4741 /0.0124 |

Competitive reward divides each context's mean seeded/single deterministic
reward by its strongest independently verified saved feasible witness. It is
descriptive and is not reward/optimum. Primary/formal-clique-upper means are
87.0058%,70.8630%,68.6264% in these populations, respectively. Failed seeds/runs
receive zero in all-assigned means and remain in coverage; native seeds are
averaged within a graph and are not independent graph observations. Independent
2,000-replicate seed/source-cluster bootstraps reproduce every saved fresh
metric and paired interval to1e-12. Both configurations and all temporal regimes
sharing a seed remain together.

The primary exceeds degree by0.9837 percentage points [0.7850,1.1711] on
standard and1.6448 [0.9286,2.3577] on dense/long. Its C3 difference is0.5230
[-0.7521,1.9832], so that comparison does not establish a source-population
improvement. Free guidance has slightly higher point quality in standard/dense,
with paired intervals crossing zero; C3 primary-minus-free is0.1746
[0.0365,0.3464]. These unequal-bank comparisons do not identify an LLM guidance
effect. CHILS, its ILS setting, M2WIS, Struction and HiGHS reach100% descriptive
competitive reward in all three populations. WeightedBR is100% on standard,
99.9947% on dense/long and99.9068% on C3. The native comparisons do not support
a SOTA-superiority claim. CHILS settings use about5 seconds per seed; several
other native algorithms terminate faster than the current Python primary.

The short phase retains211 failed `legacy_continuation_g18` runs,13
`legacy_guided_g05` failures and13 `baseline_v02_joint` failures. The long phase
retains17,1,1 respectively. Native, primary and other fresh comparators complete
their assigned calls. The bounded harness is complete even though some methods
fail; all old v03 negative results remain in the earlier audit.

Two interpretation cautions remain explicit. First, the long standard and dense
subsets each contain one shared seed block, producing degenerate bootstrap
endpoints; this is not evidence of population precision or broad30-second
generalization. Second, native wall points are medians of context mean-of-three
seed walls, not aggregate cost of three runs. The local-search row wall starts
after the five classical initializers. The audit checks its best-completed
initializer and nondecreasing reward, and separately adds every assigned
initializer wall, including failed initializers: combined medians are0.6376,
1.1985 and0.7614 seconds on standard/dense/C3. Search-only medians near0.0006
seconds must not be presented as total standalone scheduling cost.

Structured result: [advanced_fresh_audit.json](../experiments/analysis/v04/advanced_fresh_audit.json).

## Frozen-AST heap execution outcomes

The separate post-diagnostic archives `heap_fresh_v04_001.tar.gz` and
`heap_sparse_v04_001.tar.gz` pass **366,155** independent checks without errors.
Audit script: [verify_heap_results_v04.py](../scripts/verify_heap_results_v04.py).
Structured output: [heap_extension_audit.json](../experiments/analysis/v04/heap_extension_audit.json).
The exact archived seven-module source package is preserved as
`experiments/source_snapshots/v04/heap_execution_v04_source.zip`, SHA-256
`14b79fe7450d70eee621d0e01633e7cc9e2f9149cc73755577d62bbab62ab0cb`.
Its implementation bytes match the reviewed backend and runner; input, config,
TRAIN freeze and executed AST hashes reproduce the prespecified receipts.

Fresh assignment has456 contexts,5,472 complete rows and2,736 assessable pairs.
Every pair has identical full trace, selection, floating/exact reward and compiler
metadata. In addition, all2,736 rows per AST match their corresponding original
advanced-fresh confirmation trace and exact reward. This independently verifies
that the alternate backend preserves the confirmed policy rather than changing
its ranking. At every completed heap step, the audit recomputes the original
active deletion batch and surviving distance-two frontier, verifies refresh and
preserved-cache counts, and reconciles compiler/priority work with all recorded
primitive charges. Actual heap comparison/push/pop and cache-write counts match.

Three backend pairs per AST/context have the exact prespecified order and
balanced first-backend counts. CPU/work/query-saving ratios are recomputed only
for complete pairs; context medians precede source-cluster resampling. All
six fresh conditional mean/CI summaries match the separate figure analysis to
1e-12. Primary mean context-median CPU ratios are15.4511 [12.9081,18.1896] on
standard,1.1871 [1.1499,1.2291] on dense/long and4.6110 [4.0887,5.1853] on C3.
Degree dense/long is0.8714 [0.8558,0.8870], preserving the overhead case rather
than claiming uniform acceleration. Largest completed fresh primary full/heap
CPU observations are3.3578/1.9651 seconds.

SNAP assignment has8 contexts and96 rows. Each full-scan AST fails24/24 calls.
Heap primary completes7/24 and degree18/24; all remaining rows retain null
selection, trace, reward, exact reward and completed-work count. No partial or
fallback schedule is substituted. There are **zero assessable sparse pairs**.
The saved `all_completed_pairs_match=true` is therefore vacuous for this
population and does not confirm sparse trace parity or a paired speedup. Heap
successes improve observed completion only under this diagnostic CPU target;
they receive no credit in the original confirmatory quality comparison.

The target is cooperative5 process-CPU seconds, not a hard deadline. Largest
sparse full-scan failure CPU is5.0610 seconds; one completed primary heap run
records5.0154 seconds, consistent with the declared primitive/cleanup overshoot
scope. Coverage must accompany conditional timing ratios. In the plot a hollow
context point means at least one repetition failed; it can include successful
repetitions and must not be read as three failed runs. Four source graphs and
two topology-sharing weight modes are a narrow sparse diagnostic population.

## SNAP sparse input projection

The independently decoded sparse-input archive passes468,564 checks without
errors. Script: [verify_sparse_inputs_v04.py](../scripts/verify_sparse_inputs_v04.py).
Structured output: [sparse_input_audit.json](../experiments/analysis/v04/sparse_input_audit.json).
Compressed and decompressed raw hashes, every observed integer vertex ID,
every unique nonloop unordered edge, source-header/raw-row counts, two weight
modes, and exact SHA-derived weights reproduce all eight saved inputs.
The four declared simple graphs are:

| Source | Observed vertices | Simple edges | Dropped self-links |
| --- | ---: | ---: | ---: |
| ca-GrQc |5,242 |14,484 |12 |
| ca-HepTh |9,877 |25,973 |25 |
| facebook_combined |4,039 |88,234 |0 |
| ca-HepPh |12,008 |118,489 |32 |

The projection retains every observed vertex, deduplicates symmetric/repeated
arcs and drops69 self-links. All source receipts explicitly state that this
does not preserve eligibility in a raw looped-graph MWIS interpretation;
self-links are treated as source self-relations rather than vertex-exclusion
conflicts in the declared benchmark. No isolated vertex is invented and no
original vertex is removed. Unit and hash-weighted variants have identical
topology. These are explicit public graph inputs, not physical scheduling
graphs. Origin URLs/HTTPS acquisition are archived provenance; this auditor
does not independently authenticate all downloads with a second web fetch.

## SNAP advanced outcome audit

[advanced_sparse_audit.json](../experiments/analysis/v04/advanced_sparse_audit.json)
passes65,199 independent checks with no errors. All8 fixed contexts are present,
with33 assigned rows per context (264 total,125 completed). Every original
Python policy and its full-interface control fails8/8 under the cooperative
CPU target. All five classical initializers fail, so exchange search records
`no_completed_classical_initialization` without substituting a schedule.
CHILS, its ILS control, M2WIS and Struction each complete24/24 seed runs;
weighted branch-and-reduce completes21/24 and preserves three30-second hard-wall
timeouts as null. HiGHS returns eight verified feasible incumbents, six with
numerical status0 and two with status1; no clique-upper equality proves an
optimum. All eight primary interface comparisons are unassessable.

Original vertex identities, exact rewards, integer native input/output mapping,
seed settings, executable receipts, null failures, all-assigned observed costs,
clique covers, failure-zero seed averages and2,000-replicate bootstrap summaries
reproduce independently. Four source graphs per weight mode are the cluster
units. Unit/hash-weighted CHILS competitive ratios are100%/100%; M2WIS ratios
are99.9522%/99.9802%, Struction98.5102%/98.8231%, and weighted branch-and-reduce
96.6539%/75%, the latter weighted mean retaining the three failed seeds.
These are descriptive ratios to the strongest saved feasible witnesses.

All34 executed source modules and TRAIN-frozen ASTs match the original advanced
source ZIP. The separate extension-config bytes are **not** in that earlier
ZIP, which is retained as a provenance warning. Independent semantic comparison
allows only unchanged-source receipt-path repairs, removal of the public-only
long subset, and explicit extension/repair declarations. The first sparse
launch failed before output creation; it is a harness startup failure rather
than an assigned solver result. The second complete archive preserves every
assigned failure. Sparse failure exposes an execution bottleneck and supports
no original-primary quality or sparse trace-parity superiority claim.

## Public advanced outcome audit

[advanced_public_audit.json](../experiments/analysis/v04/advanced_public_audit.json)
independently checks96 short contexts with3,168 assigned rows and21
prespecified long-subset contexts with630 rows. Original graph identities,
frozen source/config/AST bytes, exact selections/rewards, formal clique
partitions, native integer input/output mapping, all-assigned observed costs,
null failures and seed-level averages pass355,759 checks without errors.
The primary completes54/96 short and18/21 subset contexts; same-AST
full-interface traces/rewards agree on54/18 assessable contexts, while42/3
failures remain explicitly unassessable. Two contexts in each phase have
verified feasible reward equal to the clique upper; HiGHS status0 counts
49/9 remain numerical rather than independent certificates.

| Short population | Primary complete | Failure-zero competitive reward,95% cluster CI |
| --- | ---: | ---: |
| DIMACS unit |17/18 |80.5284% [68.1961,90.0261] |
| DIMACS hash-weighted |17/18 |87.0737% [75.5851,94.4486] |
| SATLIB unit |10/30 |32.9304% [16.4835,49.4148] |
| SATLIB hash-weighted |10/30 |31.0455% [15.4828,46.6656] |

CHILS, its ILS setting and Struction each complete288/288 short seed runs.
M2WIS preserves six hard-wall timeouts (all three seeds on each of
`brock200_2_unit` and `hamming8-4_unit`); weighted branch-and-reduce preserves
eight hard-wall timeouts (the same six plus seeds2/3 of
`brock200_2_hash_weighted`). Each failed native row contributes zero rather
than a saved partial incumbent. CHILS/ILS quality is around99.6--100% across
these declared populations; other methods' precise values and intervals are
retained in the structured audit. Main-quality scope remains the strongest
saved feasible witness, not an optimum or a global quality guarantee.

All four native methods complete63/63 long-subset seed runs. The subset is
all18 DIMACS unit instances plus the lexicographically first unit instance
per three SATLIB collections. **Only native budgets increase to30 seconds;
constructive policies retain the five-process-CPU-second target.** Primary
completion18/21 therefore describes a different prespecified population and
cannot be presented as recovery caused by additional primary computation.
Three SATLIB source clusters provide narrow long-subset inference. Public
weight modes are analyzed separately while sharing topology/source identities;
all2,000-replicate intervals retain the declared cluster grain. Every saved
analysis endpoint, paired difference and cost/coverage interval reconciles
to1e-12 against the final three-population analysis file.

## Retrospective frozen action evidence

The separately planned588-context evidence extension passes330,923 independent
checks with no errors. See [FROZEN_ACTION_AUDIT_V04.md](FROZEN_ACTION_AUDIT_V04.md)
and [frozen_action_audit.json](../experiments/analysis/v04/frozen_action_audit.json).
Every state plan and1,071,174 independent scalar choice evaluations reconcile;
all2,736 test rollouts match original quality-study traces. Context audits all
complete, but two free-arm validation rollouts fail and remain null.
The primary's555 sampled reached test states contain18 positive finite-pool
regrets,191 zero and346 unresolved; counterfactual states are excluded.
Large-component frontier proofs remain absent, as explicitly scoped in the
report. No selection or policy is revised and no universal ranking claim follows.

## Separate30-second sparse heap extension

The source/config/input/freeze/result audit passes123,726 checks without errors.
Script: [verify_sparse_heap_30s_v04.py](../scripts/verify_sparse_heap_30s_v04.py).
Structured output:
[sparse_heap_30s_audit.json](../experiments/analysis/v04/sparse_heap_30s_audit.json).
The extension reuses exactly eight SNAP input/weight contexts and both TRAIN
ASTs, with three order-balanced repetitions at a cooperative30-process-CPU-
second target. Its explicit source ZIP SHA is
`d516c9819b847d6f7ae0e196234f436d8515e10f303cf634b3a0c07f9e413668`.

The six backend/core modules remain byte-identical to the reviewed5-second
extension. The runner source changes only its configuration admission guard:
it now accepts exactly the declared(version,CPU target) pairs for5/30-second
studies. This precise difference is independently checked and recorded; it is
not falsely called a byte-identical runner. The frozen new runner SHA is
`64e29c71376aa3f18a2ee5dc8d17b15a305aca304e7dafc7fbbada132786bfd5`,
versus original
`4ac48c2f9d161973b218456c92affa50d49c46595df588a42281bd74cfbe2983`.
Execution, scalar scoring, inference charging, ordering and null-failure logic
remain identical beyond the admitted target.

All96 assigned calls are retained. Primary heap completes12/24; degree heap
completes24/24. Both full scans still complete0/24, so there are **zero
assessable fullscan/heap pairs**. Saved all-completed-pairs-match is vacuously
true and must not be interpreted as sparse parity or a speedup. Independent
original-graph feasibility/exact rewards and charged heap-frontier/cache
counts pass on completed rows. All failed rows preserve null selection,
trace, reward and completed work with observed CPU/wall cost.

Twenty-five same-repetition successes overlap the5-second archive: seven
primary and18 degree. All have identical traces, selections and exact rewards.
Comparing every successful cross-repetition pair within the same input/AST
adds75 exact comparisons (21 primary,54 degree), also with no discrepancy.
These are repeated executions of the same inputs, **not new independent
quality instances**. They corroborate unchanged ranking on successes but do
not provide paired parity against any completed sparse full scan.

Maximum failed CPU is30.0151 seconds and maximum completed CPU is7.9899
seconds for degree/5.1365 for primary, within the declared cooperative
primitive/cleanup overshoot scope. Workers are eight here versus two in the
five-second sparse timing study, so no causal wall-cost comparison across
budgets is made. The extension changes neither TRAIN selection nor original
confirmatory failure-zero quality accounting. The compact manuscript retains
the5-second diagnostic, with this secondary result documented here.
