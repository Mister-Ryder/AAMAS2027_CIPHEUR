# Static constraint-adaptation data protocol

`cipheur.experiment_data.make_suite(config)` creates paired **static** scheduling
problems. Each pair holds opportunities, identifiers, resources, time intervals,
and weights fixed, then changes only one resource-gap parameter. There is no
online arrival process or online LLM/oracle call in this data protocol.

The function returns `train`, `validation`, and `test` lists, plus `protocol`,
`coverage`, and `audit`. Every pair record contains `id`, `family`, `left` and
`right` (`Graph` objects), `fixed`, `excluded`, `a`, `b`, and `source`. Convert the
two graphs with `graph.to_dict()` when saving JSON. An absent common conflict
edge produces `a = b = None`; that scheduling pair remains in the dataset.

```python
from cipheur.experiment_data import make_suite

suite = make_suite({
    "counts": {"diagnostic": 20, "random_temporal": 20, "c3": 12},
    "stable_root": "E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE",
    "c3_max_contacts": 28,
})
```

A family count can instead be `{"train": 8, "validation": 4, "test": 4}`;
missing split keys in such an explicit mapping mean zero. Defaults are 20
diagnostic, 20 random temporal, and 12 C3 window pairs per split. Counts of zero
disable a family. Synthetic counts are limited to 1,000 per split to preserve
the declared seed ranges.

## Generation precedes evidence and outcome labels

Generation invokes neither optimisation bounds nor ranking programs. There is
no filtering for graph changes, reversals, certification success, or achieved
schedule quality. Candidate actions are the lexicographically first conflict
edge common to both graphs after boundary exclusions; this is a structural,
deterministic choice. Diagnostic pairs designate their constructed root edge.
Unresolved and tied evidence must subsequently be reported rather than dropped
from coverage. Learning and candidate selection use training and validation;
the test set is reserved for a frozen program.

## Three distinct families

| Family | Purpose and physical semantics | Train / validation / test targets |
| --- | --- | --- |
| `diagnostic` | Designed probes under the synthetic single-capacity temporal model; mechanism checks only | Reversal ground gaps 4 / 4.4 / 5; preservation/tie gaps 0.5 / 0.65 / 0.8 |
| `random_temporal` | Opportunities drawn from the documented synthetic generator | Ground gaps 2 / 3 / 5 |
| `c3` | Original C3 opportunities using frozen V51 conflict predicates | Ground transition times 500 / 600 / 700 seconds |

These families must not be pooled into a claim about natural C3 performance.
Synthetic durations and weights are independent; C3 weights remain original
link durations. The synthetic conflict predicate is deliberately distinct from
the inherited V51 satellite partial-overlap rule.

### Diagnostic representation conflicts

The primary probe has two weight-8 roots `a,b`, a common station, distinct
satellites, and interval `[0,10]`. Three weight-6 X opportunities share `a`'s
satellite and one exterior station, at `[2,3]`, `[4,5]`, and `[6,7]`. Three
weight-6 Y opportunities share `b`'s satellite but use three distinct stations,
at `[2,3]`, `[2.5,3.5]`, and `[6,7]`. A ground-gap increase changes the X triple
from independent to a clique while the Y triple keeps one satellite-overlap
edge. Each root conflicts with its own triple and the other root.

All nine base features of `a,b` are exactly identical within each decision
context, yet their optimal conditional completion values at unit scale, excluding
the independent committed boundary value, are:

| Static problem | Commit to `a` | Commit to `b` | Preferred root |
| --- | ---: | ---: | --- |
| Before the ground-gap intervention | 20 | 26 | `b` |
| After the ground-gap intervention | 20 | 14 | `a` |

The values follow directly from the construction; no optimisation result is
used by generation. Training gap pairs are `(0,4)`, validation `(0.2,4.4)`, and
test `(0.6,5)`. Every record gets opaque shuffled IDs, a time translation, and a
random dyadic weight scale shared by both static problems. An independent
contact `z` is fixed selected and remains feasible in every completion.

Every group of five probes includes three reversal, one preservation, and one
tie instance. Preservation probes change a separate exterior resource edge
under smaller ground gaps while preserving `b`'s advantage. Tie probes keep
both root completion values equal. They are retained to test abstention and
coverage reporting. These probes establish behavior on deliberately constructed
information limitations; they do not estimate a natural reversal frequency.

### Random temporal opportunities

Training alternates 16/24 contacts, validation 18/26, and test 20/28. One contact
is an independent committed boundary opportunity. Other starts lie on a
0.25-unit grid in `[0,80]`; durations range from 0.5 to 12 and weights from 0.25
to 12. Satellite and station counts increase across splits and are recorded in
each source receipt. Within each pair, only the station gap changes:
`(0,2)`, `(0.3,3)`, or `(0.6,5)`. Satellite gap remains zero. Pair generation
does not require a common conflict edge or a changed graph.

### Source-derived C3 windows

The adapter reads the original CSV and source modules without copying or
altering them. The observed dataset contains 69,923 opportunities over three
days. Contacts whose start times belong to `[0,86400)`, `[86400,172800)`, and
`[172800,259200)` are assigned to training, validation, and test respectively.
Each day is divided into disjoint equal start-time windows. Window membership
uses link start, so a contact extending past a window endpoint still belongs
to exactly one window.

Before constructing any graph, each window chooses a deterministic cyclic
group of five original station IDs and sixteen original satellite IDs, then
retains the earliest 28 eligible opportunities by `(link_start, original_id)`.
`c3_stations_per_group`, `c3_satellites_per_group`, and `c3_max_contacts` may
reduce or vary this scope, with the node cap limited to 28. Nonpositive-duration
opportunities are ineligible because `Graph` requires positive intervals.
Original IDs, names, weights, link and trace intervals, and resource IDs are
preserved. The legacy builder needs dense IDs; only a temporary local ID is
assigned, and its edge endpoints are mapped back to original C3 IDs. The
original verifier remains attached to the in-memory graphs.

The reference configuration is shared at ground transition 340 seconds;
intervention targets 500/600/700 are held out across splits. Satellite change
and transition times stay 150 and 300 seconds. Empty windows are recorded in
coverage. Windows without graph changes or candidate edges remain present.
The coverage receipt reports eligible and retained opportunities, node caps,
actual graph changes, candidate availability, file hashes, and empty windows.
These are local subproblems, **not full-C3 schedules or a full-C3 benchmark**.
If the frozen project, CSV, or NumPy is unavailable, C3 lists are empty and
coverage gives the reason; synthetic substitution is never performed.

## Leakage checks and replay

Random temporal seed ranges start at 1,000/2,000/3,000, while diagnostic ranges
start at 100,000/200,000/300,000. The audit rejects duplicate seeds, record IDs,
contact-instance fingerprints, graph fingerprints, and C3 original opportunities.
It also rejects shared intervention target configurations across splits. The
shared C3 reference configuration is disclosed explicitly. Probe topology is
deliberately repeated with changed contacts and held-out gaps, and is reported
as a mechanism test rather than evidence of unseen-topology generalization.

The source receipt stores contact-instance and graph fingerprints, boundary
commitments, intervention edge additions/removals, generator parameters, seeds,
source provenance, and actual coverage. Tests verify the legal temporal probe,
exact base-feature aliasing, conditional values, preservation/ties, seed and
instance separation, and equality with the original legacy conflict predicates.
