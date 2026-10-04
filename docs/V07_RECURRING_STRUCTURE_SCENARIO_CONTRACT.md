# V07 recurring structure and deployment scenario contract

## Conclusion and scope

The background data support a recurring **resource-pair opportunity setting**,
but do not yet establish recurring decision-relevant graph states. The current
synthetic experiments share a weighted graph-packing abstraction with C3;
they are not an empirically calibrated C3 simulator. Practical reuse of a
TRAIN-derived structural rule therefore requires three separate premises:
future recurrence of the relevant structures, agreement between certificate
and deployment boundaries, and a ranking head that actually affects the
budgeted decision path. None follows merely from successful synthesis on a
small constructed graph.

This note uses source/schema inspection and local aggregate statistics from
the original C3 CSV. It runs no solver, conditional oracle, new experiment or
TEST-outcome selection. The existing TRAIN patch-bridge report is used only
to explain the already documented boundary mismatch. Facts below are
distinguished from proposed V07 hypotheses; this is not a new method or an
experimental protocol approval.

## Verified background facts

The inspected original input is
`E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/data/C3.csv`.
The loader's stable first six columns specify ground station, satellite,
link start/end and tracking start/end. Resource IDs are assigned from the
observed labels. A stored priority column is available, but the implemented
optimization weight is `link_et - link_st`, not that priority.

| Aggregate over the original CSV | Observed value |
|---|---:|
| Contact rows / columns per row | 69,923 / 12 |
| Ground stations / satellites | 40 / 84 |
| Distinct ground–satellite resource pairs | 3,360 = 40 × 84 |
| Contacts per resource pair, minimum / median / maximum | 12 / 21 / 25 |
| Link duration and objective weight, minimum / median / p95 / maximum | 101 / 1,124 / 1,239 / 1,244 seconds |
| Distinct durations / zero-duration contacts / duration-one contacts | 1,142 / 0 / 0 |
| Observed time span | 259,200 seconds, three days |
| Contacts in the three relative 86,400-second bins | 23,386 / 23,284 / 23,253 |
| Contacts per ground station, minimum / median / maximum | 1,726 / 1,745 / 1,800 |
| Contacts per satellite, minimum / median / maximum | 697 / 880 / 926 |
| Duplicate exact first-six-field tuples | 0 |
| Tracking margins around every link | 20 seconds before and 20 after |

These are descriptive whole-file aggregates, not optimization measurements.
The p95 is the sorted observation at index `floor(.95*(N-1))`. All link
windows lie inside their tracking windows. Times and durations are integral
in this source. Consequently, the background is not accurately described
as having arbitrary continuous, all-distinct scalar weights: durations do
repeat. That fact alone does not establish equality or recurrence of full
rooted feature vectors.

The inspected original data directory contains this C3 input, rather than a
separate later-period corpus. The three days can motivate a chronological
study; they do not verify recurrence across later weeks, hardware changes or
future operational deployments. No resource names or contact-level records
are published by this note.

The canonical V51 conflict builder has defaults
`ground_trans_time=340`, `satellite_change_time=150` and
`satellite_trans_time=300`, all nonnegative integer time parameters. On a
shared ground station, the later contact conflicts when it starts before
the earlier contact ends plus the ground transition time. The inherited
satellite predicate is more specific: identical starts and contained
overlap conflict; crossing overlap uses the satellite-change threshold;
non-overlap uses the satellite-transition threshold. Large crossing
overlaps can be allowed by that legacy predicate. Thus this model cannot
silently be replaced by the usual single-capacity interval-overlap rule.
The graph builder uses link times, while tracking times and priority remain
stored metadata. Inspection does not supply storage, energy, multi-antenna
or hardware-capacity parameters.

The second-paper V51 adapter preserves the original weights and conflict
predicates. Existing source-derived C3 studies use limited contact blocks
and explicit parameter interventions, not a proof about the complete
69,923-contact schedule. The old time-ordered builder divides contacts into
day-indexed TRAIN/validation/TEST subproblems and rotates one of the three
transition parameters. These day/block splits are evidence provenance,
not demonstrations that a structure learned on one day recurs on the next.

## Where the synthetic setting agrees and differs

Both settings encode contacts as vertices, incompatibilities as edges and
feasible selections as independent sets. This is a valid common
optimization interface. The distributions and physical predicates are
substantially different:

| Axis | Original C3/V51 | Existing V06 synthetic contacts |
|---|---|---|
| Resources | 84 satellites, 40 stations | Nominal (satellites, stations): (8,6), (12,3), (3,12) |
| Evidence state | Real duration-weighted contacts | n=32, duration=1, reward=1 |
| Large performance state | Real contact windows | n=512/1,024/2,048; sampled times and assignments |
| Reward–duration relation | Reward equals duration | Large-graph reward .25–20 sampled independently of duration |
| Large-graph duration | 101–1,244 seconds | Standard .5–12; dense-long .5–48, on the declared synthetic scale |
| Ground-gap values | Default 340; source-derived interventions use larger values | TRAIN 0/1; mechanism heldout .25/2; performance .5/6 |
| Satellite conflicts | Three inherited V51 cases above | Single-capacity interval model, satellite gap zero |
| Opportunity generation | Observed resource assignments and windows | Uniform resource assignments, independent sampled cells |

There is no declared empirical fitting of these synthetic distributions to
C3 and no time-unit conversion that aligns their gaps, durations and
horizons. A future normalized simulator would need to co-scale all relevant
time quantities and preserve the duration–reward coupling; normalization
cannot be asserted retroactively. The separate C3 interval track preserves
original contacts and weights but changes conflict semantics, using station
gaps .5/6. It remains explicitly exploratory and distinct from legacy V51.

The existing small contact mechanism frames contain 96 TRAIN endpoints and
48 heldout endpoints, with identical opportunities within each two-gap
pair. New seeds establish new generated states, not an empirical future
C3 distribution. Their unit-weight design makes exact certification and
equal-feature comparisons tractable. It does not demonstrate how often
those comparisons arise in real duration-weighted scheduling. The larger
synthetic frame jointly changes size, duration, reward, horizon and gap;
it cannot isolate a single operational configuration-transfer effect.

## Three prerequisites for a practical V07 claim

### 1. Relevant structures must recur in future states

**Verified:** every resource pair appears repeatedly in C3. **Not verified:**
the same rooted conflict/continuation structure, represented distinctions,
boundary commitments and resulting preferred actions recur. Resource-pair
repetition is compatible with entirely different competing windows and
neighbors each time.

**Proposed hypothesis:** future chronological windows contain a measurable
fraction of decision states from structural families defined using TRAIN
only. Reuse should concern observable packing structure and its parameter
range, rather than literal vertex IDs, absolute timestamps or copied graph
instances. Before a practical transfer claim, the study must report future
coverage of these families and separately retain uncovered states. Any
canonicalization, normalization or family definition must be fixed before
future outcomes, preserve relevant physical distinctions, and identify the
source-period split. A synthetic template planted to guarantee recurrence
is a controlled mechanism experiment, not natural recurrence evidence.

The exact quotient theorem needs equality of **complete represented
vectors across the demand inventory**, not just equal durations or degrees.
If every represented vector is unique, its equality quotient contains no
joins; a consistent ordering can be assigned pointwise, and the
representation-obstruction gate may be vacuous. An acyclic gate can also
occur without uniqueness. Failure of a bounded score grammar in either
case is a rule-fit limitation, not a proved information deficit. An exact
collision census on actual TRAIN states has not been performed in this
note. Artificial unit weights cannot stand in for that census. Approximate
binning changes the mathematical equivalence relation and must not be
introduced merely to manufacture cycles; approximate recurrence would
require its own statistical scope and error criterion.

### 2. Certificate boundaries must match deployed decisions

**Verified:** the deployed repair kernel keeps the outside incumbent fixed,
retains destroyed incumbent vertices in the restricted patch, respects
permanent commitments/exclusions, and commits only a globally feasible
strict improvement. A full-residual forced-inclusion comparison is not
automatically a patch-local comparison. The existing TRAIN bridge retains
seven formerly full-strict pairs: three retain their strict direction,
one reverses and three become exact local ties. These are already measured
TRAIN diagnostics, not newly queried labels.

**Proposed requirement:** a training label intended for patch-local greedy
inclusion must use the same restricted candidate graph and fixed outside
boundary as deployment. If the programme is used for B&B pivot priority,
the claim must be narrower: a pivot ultimately explores both include and
exclude branches. A higher conditional inclusion optimum does not prove
that pivoting on that action first reduces search work or finds an
incumbent earlier. Such a path benefit requires measurement under the same
cap. Dataset objective, resource predicates and action feasibility must
also agree; an interval-model certificate cannot label a different V51
legacy decision by assumption.

### 3. The ranking head must genuinely control the budgeted path

**Verified:** with the current default `policy_scope='branch'`, target and
patch-restriction order use the common Degree policy. The frozen programme
orders one local greedy construction and the subsequent patch B&B pivots;
the common Degree greedy construction, include-first branching, bounds and
feasibility checks remain shared. Priorities are computed for the patch
snapshot, with the next remaining vertex chosen from that order. This is a
specific path-control interface, not control over every scheduling choice.

**Proposed operating condition:** patches sufficiently difficult under a
justified fixed budget must leave room for priority to affect a feasible
incumbent or search cost. If all patches are completed exactly, their
optimum is independent of ordering; the only possible benefit may be work
or time. If bounds prune before scores are used, there is no exercised
ranking decision. TRAIN path measurements should therefore distinguish
unscored/pruned patches, changed greedy prefixes/pivots, search completion,
time/work and realized gain. Do not weaken a common kernel after seeing
TEST results to create an apparent learned advantage. This condition is
especially relevant to the previous tiny patches: the existing TRAIN
bridge has 106 two-vertex patches among 120 and a tight root upper bound
in 117, so abundant scoring labels alone are not evidence of useful
budgeted control.

## Defensible current claim and unresolved assumptions

The frozen typed programme recomputes structural features on the current
graph. The four actual W-joint rules do not reference station/satellite gap
coordinates, although the base grammar permits them. This establishes how
these four programmes respond structurally to changed graphs; it does not
establish future-state recurrence, correct transferred rankings or a
schedule advantage. The statement must not be generalized to every
comparator or to a grammar that forbids configuration coordinates.

The present defensible interpretation is a certified representation and
proposal mechanism studied on controlled graph states, with separate
background contact benchmarks. Practical recurring-scene use remains a
hypothesis until all three prerequisites above are supported together.
The certificate proves a scoped information obstruction; the LLM proposes
typed distinctions and compatible rules; deterministic validation retains
authority. Neither a constructed witness nor the LLM itself supplies the
missing empirical bridge from TRAIN structure to future decisions.

## Traceable evidence

Hashes identify the bytes inspected, without exposing raw contact records.

| Artifact | SHA-256 |
|---|---|
| Original C3 CSV, path above | `ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e` |
| Original `SNSD_V51_FINAL/src/snsd_core/data.py` | `e18ebe861c8c578bc82e7386977cacf71904239a4332c03680314ec8d9b480ef` |
| Original `SNSD_V51_FINAL/src/snsd_core/graph.py` | `030d6d0e26776c5817083ee95edb9c536da92ec30eb9afb727ce783e8232c5c4` |
| `cipheur/v51_adapter.py` | `68699aa08e21a6dea1108ba64878916efaf56e05f076e93aa6cda9b7c6dad28d` |
| `cipheur/study_data.py` | `0a37342622ab2330447a86b3ffb0fe1c45696072652b15a25826423ae3688fb3` |
| `cipheur/graph_features.py` | `b6f807e9a1a13e8443532247e24fc802815053d375f69ed2c2718a222282a03d` |
| `cipheur/repair_v06.py` | `c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3` |
| Frozen evidence `experiments/discovery/v06_evidence_001/data.json` | `968f96b7712ca3ecc8a7b43f567c6b6403742f26f0e76e9d5f2c680973827784` |
| Performance input generation protocol | `d1184a1eb47c451847d34cb5ebc8e5a83dda4ef56382c820112750e9a9ec9b92` |

The performance protocol is
`experiments/discovery/performance_inputs_server_v06_001/generation_protocol.json`.
Existing supporting documents are
[V06 scenario alignment](V06_DATASET_SCENARIO_ALIGNMENT.md),
[TRAIN patch-bridge scope and results](V06_PATCH_BRIDGE_RESULTS.md),
[C3 interval input scope](V06_C3_INTERVAL_INPUT_SERVER_RECEIPT.md), and
[TRAIN/TEST and oracle boundary](V06_TRAIN_TEST_AND_ORACLE_BOUNDARY.md).
They retain the distinction between generated new states, exposed source
benchmarks and genuinely future physical data.
