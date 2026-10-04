# V06 dataset and scenario alignment

## Narrow conclusion

The evidence and performance frames are related but are not the same learning
problem at different seeds. TRAIN uses small unit-weight evidence states;
the 72-state mechanism TEST retains that scale and introduces unseen **station
switching-gap values**. The 216 fresh performance endpoints simultaneously
introduce larger graphs, heterogeneous rewards/durations, different temporal
profiles and further unseen station gaps. Their performance cannot isolate
the effect of a single configuration shift.

The three nominal resource-count regimes are **shared across TRAIN and both
TEST frames**, not withheld regimes. Within every contact pair, only station
gap changes; satellite gap stays zero and both resources remain single-capacity.
This supports a specific frozen-policy transfer design, not generalization to
arbitrary resource constraints, parallel capacities or the full V51 model.

This note reads frozen generator/protocol fields and the small evidence-input
metadata. It performs no optimization, conditional query, independent audit
replay or large performance-analysis load. No frozen file is changed.

## Actual frames and source composition

| Frame | Abstract public states | Synthetic contact pairs / endpoints | Contact graph size | Contact reward / duration |
|---|---:|---:|---:|---|
| TRAIN evidence/assessment | 24: 9 DIMACS, 15 SATLIB | 48 / 96 | 32 per contact endpoint | Both exactly 1 |
| Withheld mechanism states | 24: 9 DIMACS, 15 SATLIB | 24 / 48 | 32 per contact endpoint | Both exactly 1 |
| Fresh performance | None in this 216-endpoint subset | 108 / 216 | 512, 1024, 2048 | Reward 0.25–20; variable duration |

Thus **120 TRAIN states are not 120 satellite-contact instances**, and **72
heldout states are not 72 satellite-contact instances**. The public portion
uses source-derived induced graphs under the fixed salt
`v06_261003_new_source_state_queries_001`. TRAIN has 23 induced public graphs
of size 32 and one of size 28; all 24 public TEST states have size 32.
These public graph objects use the common graph API but are abstract packing
benchmarks, not physical contact data.

The 48 public source clusters are split separately inside DIMACS and SATLIB
by fixed SHA ordering: 9/9 and 15/15. Their new induced TRAIN/TEST states are
source-disjoint, while the original public corpus was already exposed. The
frozen protocol explicitly records `prior_public_corpus_exposed=true` and
`physical_source_claim=false`.

## Resource and temporal configuration distribution

Resource pairs below mean **(satellites, ground stations)** and describe
nominal label sets from which assignments are drawn uniformly. A small
sample need not occupy every nominal resource label.

| Regime | Resource counts | TRAIN short / long endpoints | Mechanism TEST short / long endpoints | Performance standard / dense-long endpoints |
|---|---:|---:|---:|---:|
| balanced | (8,6) | 16 / 16 | 8 / 8 | 36 / 36 |
| ground_scarce | (12,3) | 16 / 16 | 8 / 8 | 36 / 36 |
| satellite_scarce | (3,12) | 16 / 16 | 8 / 8 | 36 / 36 |

Each evidence regime/profile has eight TRAIN source pairs and four TEST
source pairs. Short and long evidence profiles sample starts on a 0.25 grid
over horizons **11 and 24**, respectively; duration stays 1. Performance
has six independent pairs per regime/profile/size cell, giving 18 cells
and 108 pairs. Each performance family has 12 endpoints at each of the
three sizes, hence 36 endpoints.

| Configuration axis | Contact TRAIN | Mechanism contact TEST | Fresh performance |
|---|---|---|---|
| Station gap, left / right | 0 / 1 | 0.25 / 2 | 0.5 / 6 |
| Satellite gap | 0 | 0 | 0 |
| Resource capacity model | One per satellite and station | Same | Same |
| Nominal resource regimes | All three above | Same three | Same three |
| Graph size | 32 | 32 | 512 / 1024 / 2048 |
| Temporal horizon | 11 / 24 | 11 / 24 | Standard: 1.8n; dense-long: 0.18n |
| Duration | 1 | 1 | Standard: 0.5–12; dense-long: 0.5–48 |
| Reward | 1 | 1 | Uniform quarter values 0.25–20 |

The station-gap value sets have no overlap. Mechanism TEST includes a
gap within the TRAIN range (0.25) and one beyond it (2); performance includes
0.5 and 6. This is numerical gap transfer within the same single-capacity
model and seen resource regimes. Standard and dense-long performance jointly
change horizon and duration distribution; they are not pure density
interventions. Changing the nominal regime changes both resource counts and
resamples opportunities, so it is not a one-axis same-source resource-count
intervention either. No satellite-gap, multi-capacity, storage/energy or
multi-antenna axis is tested by these synthetic pairs.

## Pairing, instances and seeds

Within a source pair, the contact opportunities are generated once and
preserved across left/right endpoints: identical IDs, weights, resources,
start and end times. Only station switching gap changes. The right graph
therefore adds conflicts monotonically; it does not remove/reweight contacts.
Evidence queries use edges common to both endpoints and retain individually
feasible competing actions at the fixed empty boundary. Quota shortfalls,
exact ties and unresolved labels are not resampled away.

Across pairs, TRAIN and mechanism TEST names include their split and feed
different SHA-derived seeds to the generator. The stored evidence metadata
contains 48 distinct TRAIN contact-source seeds and 24 distinct TEST seeds,
with zero seed, state-ID or graph-digest intersection. Evidence contact vertex
strings `v000`–`v031` are reused across independently generated cases; that
string reuse is not reuse of the same opportunity tuples. Generic identifier
ordering also does not establish permutation invariance, which is measured
separately by the five heldout mappings.

Performance uses the separate namespace
`V06_FRESH_PERFORMANCE_TEST_20261003_001`, full-SHA seeds and IDs
`v06perf_001_<ordinal>_c<index>`. Its 108 source seeds have no intersection
with the evidence contact seeds. Cells are independent across regime, profile,
size and index; left/right intentionally share their source. Absolute time
offset `ordinal*100000` distinguishes cells without changing within-cell
conflicts. No historical source contacts are imported into this synthetic
216-endpoint subset. The existing input checker records all 108 paired
opportunity identities and exact interval-model edge sets; it is not rerun here.

## What frozen graph adaptation means

The program is a function of the **current** graph, active patch and root
action. The grammar permits station/satellite gap base coordinates, but the
four actual proposed W-joint rules in
`examples/frozen_joint_bank_v06.json` reference neither `station_gap` nor
`satellite_gap`. Their typed feature operations do not read configuration
knobs directly. This specific bank therefore responds through current graph
structure and other referenced values, rather than direct scoring on the
numeric gap coordinate. It would be incorrect to extend that statement to
all 31 comparators or claim that the grammar forbids such coordinates.

Neighborhoods, root-deleted sets, compatible continuations, induced edges,
packings and clique covers are recomputed under the current graph. Changing
the station gap can therefore change structural features and priorities
without changing the program or requesting another LLM call. The tested
problems remain paired static scheduling instances, not a streaming
resource-change simulation.

This functional dependence explains how a frozen program can respond to
configuration changes. It does not guarantee correct rankings under all
new configurations. The 72-state preference-transfer measurements evaluate
that question on the specified frame; representation adequacy, actual scalar
fit and realized schedule reward remain distinct outcomes.

The small unit-weight design permits bounded exact conditional certification
and intentionally enriches informative equal-feature comparisons. It is a
mechanism test, not evidence that such collisions are common in natural
weighted satellite data. The larger weighted frame additionally changes
optimization difficulty. Its broad failure/null/quality outcomes cannot be
ascribed solely to unseen switching gaps; graph size, duration, reward and
density must remain visible in interpretation. Existing data support **new
instances plus numerical-gap transfer**, not an isolated causal estimate of
configuration generalization or guaranteed adaptation.

The complete 302-context performance frame further contains 38 original
weighted public source graphs and 48 previously exposed C3 exploratory
contexts. They must remain separate from fresh synthetic claims. The public
calibration/source boundary is documented in
[TRAIN/TEST and oracle boundary](V06_TRAIN_TEST_AND_ORACLE_BOUNDARY.md).

## Traceable fields and receipts

| Evidence | Fields used | Path / SHA-256 |
|---|---|---|
| Actual 192-state inventory | `records.{split,family,paired,pair,source.seed,graph.contacts,graph.constraints,graph_digest}` | `experiments/discovery/v06_evidence_001/data.json` — `968f96b7712ca3ecc8a7b43f567c6b6403742f26f0e76e9d5f2c680973827784` |
| Evidence source/config split | `public_source_split`, `counts`, exposure/model-scope flags | `experiments/discovery/v06_evidence_001/protocol.json` — `32e008c2d348df53813696f8bfc413829704a9e76c07e4d03ac036387cb11854` |
| Evidence generation | `prepare`: resource/horizon loops, TRAIN8/TEST4, gap pairs and split-derived seeds | `cipheur/evidence_study_v06.py` — `968bf3e7c1aee39b42de9066dc605507eb2a108de29b7ed29ea9460684dab567` |
| Performance declared cells | `sizes`, `resources`, `profiles`, `cells`, `generator`, `contact_scope` | `experiments/discovery/performance_inputs_server_v06_001/generation_protocol.json` — `d1184a1eb47c451847d34cb5ebc8e5a83dda4ef56382c820112750e9a9ec9b92` |
| Performance generation | `planned_cells`, `build_pair`, untouched contacts and station-gap endpoints | `scripts/prepare_performance_v06.py` — `893115422a9e7dbae61105cec7ffa27d257e8a482cab380af9909c11a4364ee8` |
| Actual fresh-input receipt | 108 pairs, 216 endpoints, six families, original contact-field/edge checks | `experiments/analysis/v06/performance_inputs_check_v06_001.json`; binds data SHA `23caf12cca124aa1ed97f7848454b8a6ac2bb283462c4719510bd6fc30357548` |

The canonical fresh-input archive is
`experiments/runs/v06/performance_inputs_v06_001.tar.gz`, SHA-256
`1f853ec90153ecd65418119352c13d9e17242e6dddd407ed8eaa45f7bf3aa20b`.
These are existing frozen evidence bindings, not newly generated outcomes or
a replacement for the completed independent audits.
