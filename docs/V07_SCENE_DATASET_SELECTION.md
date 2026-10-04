# V07 C3 scene dataset selection: an input-only plan

## Selected candidate setting

Use **all chronological two-hour C3 start-window blocks**, with the original
V51 conflict predicates, actual resource assignments and objective
`weight = link_end - link_start`. Day 0 supplies TRAIN, day 1 validation and
day 2 retrospective heldout opportunities. The three ground-transition
values **340, 510 and 680 seconds** are fixed before graph construction or
outcomes; satellite-change/transition values stay **150/300 seconds**.
Every window is evaluated at all three settings. This tests new temporal
opportunities within a shared configuration domain, not unseen-gap values.

This is **candidate A**, the authenticity control and an unconfirmed core
mechanism candidate. Candidate B below keeps visibility availability but
declares a different fixed-packet task. Neither candidate has an executed
or frozen optimization protocol. A proposed alternative configuration
split uses TRAIN/validation **340/680** and heldout **425/595** seconds, to
test within-range interpolation. It is not yet adopted or tested. Choose
between the common-domain and interpolation designs before decision labels
or optimization outcomes, rather than choosing the better result.

This is a **candidate setting for mechanism screening**, not a claim that
C3 already triggers the core information-conflict mechanism. The plan is
[C3_scene_screening_001.json](../configs/v07/C3_scene_screening_001.json).
No graph, optimization problem or conditional certificate was solved to
choose these windows or gaps. Only original CSV aggregate counts were read.

The original corpus was previously used in development and experiments.
Chronological separation remains useful, but it is retrospective and
cannot be advertised as a previously unseen corpus or prospective
deployment evaluation. It contains only three days. A successful day-2
result would not establish robustness across seasons or later missions.

## Why this setting, rather than larger unrelated synthetic graphs

C3 contains **69,923 real windows**, **40 stations**, **84 satellites** and
all **3,360 resource pairs**. Each resource pair occurs 12–25 times over the
three days, with median 21. Duration equals reward: minimum 101 seconds,
median 1,124, maximum 1,244. This makes repeated competing resource use a
plausible source of recurring local packing structures. It does not yet
establish that the structural distinctions controlling a decision repeat.

Whole time blocks preserve real opportunity density, duration–reward
coupling, resource assignments and their time dependence. They avoid
selecting a small resource subset or planting a repeated motif to produce
an alias. Two-hour blocks are the primary scene because their measured
scale is naturally around two thousand contacts. Four/eight-hour blocks
are declared nested scale checks, not alternative populations to choose
after outcomes or independent repetitions.

| Window width | Day 0 minimum / median / maximum | Day 1 minimum / median / maximum | Day 2 minimum / median / maximum |
|---|---:|---:|---:|
| 2 hours | 975 / 2,090.5 / 2,686 | 999 / 2,057.5 / 2,732 | 1,012 / 2,020.5 / 2,751 |
| 4 hours | 2,104 / 3,991.5 / 5,206 | 2,112 / 3,946 / 5,308 | 2,101 / 3,964 / 5,365 |
| 8 hours | 5,493 / 8,885 / 9,008 | 5,461 / 8,738 / 9,085 | 5,395 / 8,606 / 9,252 |

The exact two-hour counts in chronological order are:

| Split | Twelve counts |
|---|---|
| Day 0, TRAIN | 1,614; 2,188; 2,520; 2,686; 2,543; 2,161; 2,080; 2,101; 1,863; 1,526; 1,129; 975 |
| Day 1, validation | 1,550; 2,227; 2,576; 2,732; 2,521; 2,102; 2,045; 2,070; 1,825; 1,524; 1,113; 999 |
| Day 2, retrospective heldout | 1,614; 2,273; 2,614; 2,751; 2,497; 2,068; 2,005; 2,036; 1,769; 1,525; 1,089; 1,012 |

The totals are respectively 23,386, 23,284 and 23,253. Primary opportunity
groups number 12 per split, 36 overall. Three configurations give 36 planned
graphs per split, **108 graphs overall**, retaining the dependence among
the three configurations of one opportunity group. Four-hour windows
combine adjacent two-hour groups; eight-hour windows combine adjacent
four-hour groups. All scales reuse the same original contacts.

## What is preserved and what is intervened on

The original link/tracking times, stable source-contact identity and station
and satellite assignments are retained. Priority remains source metadata,
not a replacement objective. No reward/time normalization, clipping,
resource sampling, density filter or outcome-selected gap is permitted.
The original tracking interval encloses every link with 20 seconds on each
side; the canonical conflict predicate still uses link times.

The primary model is explicitly **V51 legacy**. Shared-ground transition
uses 340/510/680; satellite conflicts retain the inherited contained,
crossing-overlap and non-overlap cases at 150/300. These are the repository
model and its parameter extensions, not independently measured hardware
limits. The factors 1/1.5/2 are deterministic sensitivity settings, with
no optimization evidence supporting one over another. A physical ideal
single-capacity interval model would be a separate declared population;
it must not silently replace V51 or reuse certificates from it.

Within a window, the complete contact set is identical across gap settings;
only ground-transition conflicts may change. Satellite constraints and
weights do not change. The resource-count domain is the observed C3
domain, rather than the small synthetic (8,6)/(12,3)/(3,12) nominal sets.

## Candidate B: fixed service jobs within observed availability

A closer match to structural opportunity-cost decisions may be a **fixed
payload/slot communication service**. Treat original C3 links as visibility
availability, not mandatory occupations that earn their full duration.
Create explicitly declared jobs with a satellite, release/deadline, equal
payload value and fixed service length. Generate feasible service intervals
inside the original visibility intervals by a deterministic rule. Distinct
station/time candidates serving one job form a complete mutual-exclusion
clique, including alternatives whose intervals do not overlap. Across
jobs, a single satellite and a single station cannot occupy overlapping
service intervals; a declared station transition gap adds resource edges.

For illustration only, an operational protocol could request one equal
packet per satellite per hour, with a 60-second service and an hourly
deadline. A candidate in one visibility window starts at the maximum of
the job release and visibility start, and is retained only if its full
service ends within both the window and deadline. This gives a finite
deterministic candidate rule without optimizing start times. The exact
service length, job cadence, candidate-generation rule and treatment of
window-crossing jobs must be registered before screening; this illustration
is not an adopted workload or evidence that 60 seconds is appropriate.
Unservable jobs remain in coverage denominators, rather than being
resampled. Candidate/job IDs and random seeds cannot be chosen from labels.

B assigns a job to a chronological block by its release time. It must use
every original visibility interval intersecting that job's permitted
horizon, including an interval whose start precedes the block. Such
boundary visibility may be shared between adjacent frames and must be
reported; job-split separation would not imply raw-contact-source
disjointness. The counts above apply to A's start-window contacts, not
B's ungenerated service candidates. B candidate counts remain unknown.

The original C3 schema contains **no job identity, packet demand, release,
deadline, payload or service protocol**. Those fields are synthetic workload
assumptions. B therefore must be described as **availability-derived with
a declared workload**, not original C3 scheduling with weights replaced by
one. Equal values/durations derive from the proposed service protocol;
they are not a claim about the original duration-weighted objective. The
protocol may lead to repeated base values, but exact full-vector aliases,
sound conflicts, recurring labels and runtime effects still need to be
measured. Equal service values alone guarantee none of them.

B uses an explicit ideal single-capacity interval model, with its satellite
gap/capacity convention separately stated. It does not reuse the original
V51 contained/crossing satellite predicate or its 150/300 parameters by
name. Station gaps grounded in the repository's 340-second default are
controlled assumptions, not independently measured switching times for
the new packet protocol. A and B are separate populations, objectives and
certificate scopes. B can be a prospective core-mechanism candidate while
A remains the real-duration background control; neither may silently
inherit the other's labels or performance claims.

No B workload has been generated here. Its final input-only proposal should
be selected for a defensible service setting, then evaluated with the same
whole chronological windows. If it yields no applicable trigger, retain
that result. Trying service lengths, seeds or label boundaries until a
positive cycle appears would not validate a practical setting.

## Time-window boundary semantics

Let `s = day*86400 + block*7200`. A contact belongs to the two-hour group
when **s ≤ link_start < s+7200**. Keep its original end even when it lies
beyond that boundary. Actual two-hour groups contain between zero and 410
such end-crossing contacts. Cropping them would change both reward and
conflict semantics; they must remain intact.

These are standalone static start-window opportunity problems with initial
permanent F/X empty. Contacts starting outside the block are absent, not
implicitly committed. Independently selected sets from adjacent windows
cannot simply be joined into a feasible full-day schedule. A rolling
deployment that carries earlier accepted contacts would need explicit
outside commitments and a separate input/label boundary definition before
training. This plan does not fabricate that boundary.

## Screening and acceptance contract

First inspect **day-0 TRAIN inputs only**, without optimizers or conditional
queries. Retain all twelve windows and all three gaps. Record resource-pair
recurrence; connected-component and neighborhood structure; TRAIN-defined
rooted-signature recurrence; complete base-nine exact equality; graph edge
changes across gap settings; and graph/feature construction costs. An
exact full base-vector alias cannot be created by dropping weight or gap,
rounding continuous values or selecting only repeated cases. Different gap
coordinates themselves prevent full-vector equality across those settings,
even when a structural pattern recurs. Declared referenced interfaces must
match eventual deployment; they cannot be chosen from future outcomes.

Recurring resource pairs and similar-sized graphs are insufficient. A
useful structural family must be defined on observable rooted conflict and
continuation structure using TRAIN alone, survive identifier changes, and
have reported future-window coverage. Approximate similarity and exact
feature alias are separate diagnostics. Neither yields a certified
contradiction before sound decision labels exist.

If day 0 has no exact alias or no recurring structural trigger, retain that
zero and do **not** promote C3 to a demonstrated information-obstruction
benchmark. Do not replace quiet windows with denser windows or choose
another gap after observing a failure. The nested scales remain labelled
scale checks; selecting a new primary scale would require a separate
prospective protocol, not retrospective rebranding.

Input topology alone cannot establish runtime relevance. A later separately
frozen TRAIN path probe must show that the shared kernel actually reaches
and uses ranking decisions: pre-score bound pruning and fully solved
patches are separate from budget-limited decisions. A local certificate
must use the deployed patch and fixed outside boundary. A forced-inclusion
preference does not prove that a B&B pivot ordering is faster. Only after
this interface is fixed may future-state structure coverage and, under a
separate frozen study, future decision/performance outcomes be measured.
All missing, untriggered, tied and uncovered cases stay visible.

The detailed label-free mechanism diagnostics are independently planned in
[mechanism-scene screening specification](V07_MECHANISM_SCENE_SCREEN_SPEC.md).
The three practical prerequisites and background/synthetic mismatch remain
in [recurring-structure scenario contract](V07_RECURRING_STRUCTURE_SCENARIO_CONTRACT.md).

## Source bindings and publication boundary

Original input:
`E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/data/C3.csv`,
SHA-256 `ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e`.
Its minimum link start is 0 and maximum link end is 259,200 seconds. The
canonical original graph source is
`SNSD_V51_FINAL/src/snsd_core/graph.py`, SHA-256
`030d6d0e26776c5817083ee95edb9c536da92ec30eb9afb727ce783e8232c5c4`.
The existing second-paper adapter is `cipheur/v51_adapter.py`, SHA-256
`68699aa08e21a6dea1108ba64878916efaf56e05f076e93aa6cda9b7c6dad28d`.

Only this aggregate plan/config is intended for repository publication.
Raw C3 data, contact/resource names and derived raw-contact inventories
are not uploaded. The local source reference in the config enables
reproduction by authorized users; it does not distribute the input.
