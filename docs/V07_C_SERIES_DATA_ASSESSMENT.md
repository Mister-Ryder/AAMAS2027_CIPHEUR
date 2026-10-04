# V07 complete C-series input assessment

## Main findings

**C6 contains 140,406 contacts over three days, not six days.** C1–C6
all span the same relative link-time range, 0–259,200 seconds. Their
normalized contact inventories are strictly nested: **C1 ⊂ C2 ⊂ C3 ⊂ C4
⊂ C5 ⊂ C6**. Every earlier contact occurs in every later file, although
the CSV row order is not an ordered prefix. A C1-TRAIN/C6-TEST experiment
would reuse all 23,598 C1 contacts and cannot establish independent
instance generalization.

Use **C6 as one canonical complete source**, then define explicit
chronological windows or another justified source split inside that input.
Do not infer TRAIN/TEST roles or duration from the file suffix. Three-day
chronological separation remains retrospective: new C3 is byte-identical
to the previously used background C3, and C6 contains that whole exposed
subset. Additional satellite contacts in C6 do not make the whole corpus
unseen or provide an independent future period.

These are input findings only. No graph, optimizer, conditional certificate,
programme assessment or TEST-outcome selection was executed. The report
publishes no resource identifiers or contact-level records. W-series inputs
are outside this assigned assessment.

## Reproducible profile and normalization

The independent standard-library script is
[profile_c_series_v07.py](../scripts/profile_c_series_v07.py). Its complete
aggregate output is
[input_profiles_c_series_001.json](../experiments/analysis/v07/input_profiles_c_series_001.json).
It reads each file as **strict GB18030**, without replacement characters,
using a strict CSV parser. Required values are whitespace-trimmed and
stripped of boundary single/double quotes; integral time fields are
canonical integers. The normalized first six fields are encoded as compact
ASCII JSON and hashed with SHA-256. Multiset containment is checked for all
15 earlier/later file pairs; ordered-prefix equality is checked separately.
Only aggregate inventory hashes are published.

All C resource cells have balanced single quotes. Each normalized resource
label has just one raw representation, with no normalization collisions.
Thus the explicit quote cleaning changes representation, not observed
resource cardinality in these inputs. This does not assert the same result
for W-series files or an arbitrary future CSV.

The script refuses to overwrite an existing output. To repeat the input
profile without replacing this evidence:

```powershell
python scripts/profile_c_series_v07.py --out experiments/analysis/v07/input_profiles_c_series_replay.json
```

## Schema, validity and objective interpretation

Every file has the same 12-column header and every data row has 12 fields:

| Position, zero-based | Actual header | Meaning relevant to preprocessing |
|---:|---|---|
| 0–1 | 地面站标识 / 卫星标识 | Resource identity; never printed in this report |
| 2–3 | 开始建链时间 / 结束建链时间 | Link start/end, integer seconds |
| 4–5 | 开始跟踪时间 / 结束跟踪时间 | Tracking start/end, integer seconds |
| 6 | 是否馈电 | Feeder-link indicator; **not a cancellation flag** |
| 7 | 最大仰角 | Maximum elevation; unavailable as `*` |
| 8 | 任务执行日期 | Execution-date metadata; **not an execution count** |
| 9 | 圈次 | Orbit revolution metadata; unavailable as `*` |
| 10 | 升降轨标识 | Ascending/descending metadata; unavailable as `*` |
| 11 | 优先级 | Priority; empty in every row |

Across all six files there are zero missing required first-six values,
zero invalid integer time fields, zero negative or zero link durations,
and zero malformed column-count rows. Every tracking interval contains
its link and extends exactly **20 seconds before and 20 after** it.
Tracking time therefore spans −20 to 259,220 seconds even though link
time spans 0 to 259,200.

The inherited scheduling loader defines **weight = link duration**. This
is an implemented objective interpretation, not a separate weight column
or an empirical priority measurement. Empty priority cannot supply
heterogeneous task value; a new priority model would be an explicitly
different workload. `*` is a nonnumeric sentinel, not zero elevation,
zero orbit or a usable orbit-direction category. No metadata-based
filtering was performed.

## Complete-file size and contact-key quality

| File | Contacts | Stations | Satellites | Resource pairs | Duration minimum / median / p95 / maximum, seconds |
|---|---:|---:|---:|---:|---|
| C1 | 23,598 | 40 | 28 | 1,120 | 101 / 1,123 / 1,239 / 1,244 |
| C2 | 46,818 | 40 | 56 | 2,240 | 101 / 1,123 / 1,239 / 1,244 |
| C3 | 69,923 | 40 | 84 | 3,360 | 101 / 1,124 / 1,239 / 1,244 |
| C4 | 93,153 | 40 | 112 | 4,480 | 101 / 1,124 / 1,239 / 1,244 |
| C5 | 116,755 | 40 | 140 | 5,600 | 101 / 1,123 / 1,239 / 1,244 |
| C6 | 140,406 | 40 | 168 | 6,720 | 101 / 1,123 / 1,239 / 1,244 |

Every observed station–satellite combination occurs in its file. All six
have zero duplicate excess for normalized first-six keys, normalized
first-four keys (resource identities plus link start/end), and complete
normalized rows. Contact identity can therefore be bound to the original
first-six key; CSV row positions should not be treated as cross-file
independent contacts. This empirical uniqueness of contact records is
different from equality or uniqueness of an algorithm's feature vectors.

All 15 normalized earlier/later multiset comparisons have zero earlier-only
occurrences. All 15 ordered-prefix comparisons are false. The C6-only
contact count relative to C3 is **70,483**; the remaining 69,923 contacts
are exactly the original C3 inventory.

## Metadata values and day assignment

The feeder indicator is `是` in every row of every file. Maximum elevation,
orbit revolution and ascending/descending columns are `*` throughout;
priority is empty throughout. Each of these columns has respectively one,
one, one, one and zero nonempty value kinds. Execution-date metadata has
three nonempty values, `1`, `2`, `3`, in every file. Nothing in this schema
establishes a cancellation state or an execution-count obligation.

Use link-start time for the declared natural-day partition, not the
execution-date column without specifying semantics:

| File | Starts in day 0 [0,86400) | Starts in day 1 [86400,172800) | Starts in day 2 [172800,259200) |
|---|---:|---:|---:|
| C1 | 7,961 | 7,827 | 7,810 |
| C2 | 15,682 | 15,581 | 15,555 |
| C3 | 23,386 | 23,284 | 23,253 |
| C4 | 31,165 | 31,013 | 30,975 |
| C5 | 39,152 | 38,839 | 38,764 |
| C6 | 47,156 | 46,664 | 46,586 |

For C6 the execution-date value counts are **46,600 / 46,668 / 47,138**,
so they are not the same as these start-day counts. The full cross-tab
shows 556 day-0 starts marked date `2` and 552 day-1 starts marked date
`3`; these counts match link-end crossings of those daily boundaries.
This is an observed correlation, not proof of a documented date policy.
Do not turn these values into additional days or infer repeated execution.

## C6 natural two-hour windows and boundary preservation

The canonical time origin is **0 seconds**. Each window assigns starts by
`window_start <= link_start < window_end`, preserves the complete original
end and duration, and counts incoming overlaps separately. All 36 natural
C6 windows have 40 ground stations and 120–137 observed satellites. The
contact count range is **3,563–4,252**, with median **3,903.5**. Thus the
earlier C3 two-hour expectation of roughly 2k contacts does not describe
the new C6 frame; C6 is naturally around 4k contacts per two hours.

| Day | Twelve start-window contact counts in chronological order |
|---|---|
| 0 | 4,252; 3,608; 3,563; 3,713; 3,896; 4,161; 4,222; 4,138; 3,941; 3,932; 3,846; 3,884 |
| 1 | 3,728; 3,600; 3,579; 3,740; 3,911; 4,172; 4,215; 4,146; 3,952; 3,921; 3,843; 3,857 |
| 2 | 3,720; 3,601; 3,596; 3,733; 3,950; 4,178; 4,222; 4,128; 3,919; 3,915; 3,848; 3,776 |

Between zero and 620 assigned contacts end beyond their two-hour window.
At the day-0/day-1 boundary 556 links overlap into the following day; at
the next daily boundary 552 do. Raw contact keys assigned by start are
disjoint across these partitions, but opportunity intervals and resources
remain temporally dependent. The complete profile includes every
window's end-crossing and incoming-overlap counts. These incoming counts
concern occupied link intervals, not additional transition-gap carry-over.

Cropping windows would change rewards and conflicts. Empty-F/X standalone
frames cannot be composed directly into a full-period schedule. A rolling
deployment would need actual outside commitments and transition carry-over
defined before generating decision labels. Whole-window chronological
input partitions alone neither supply those commitments nor guarantee
recurring decision structures.

## Recommended next boundary, without outcome-based selection

Adopt C6 as the canonical source and freeze an explicit day/window split.
For the currently authorized input screening, **day 0 alone** supplies
twelve two-hour TRAIN windows; later days must not be inspected as if they
were extra TRAIN graphs and then advertised as future unseen tests. Keep
all selected day-0 windows, real duration rewards, observed resource
assignments and the chosen model's original predicates. A later protocol
can reserve day 1 and day 2 for validation/retrospective heldout, but this
profile does not execute or release that study.

Profile validity is not acceptance of C6 as an information-obstruction
benchmark. Exact full-feature aliases, structural recurrence, sound
boundary-matched conflicts and actual priority-controlled search remain
separate screening/experimental questions. Their zero or missing outcomes
must be retained. Do not replace untriggered windows or call the larger
satellite cohort a guarantee that the core mechanism works.

The historical C3 scenario candidate documents remain scoped to that
smaller input. This assessment supersedes any inference that C6 means
six days or that C1–C6 provide independent temporal datasets; it does not
silently alter previous frozen evidence.

## Byte bindings

| Artifact | SHA-256 |
|---|---|
| Independent profiling script | `d44806e3781ed1fd733089b6b27cafc94f9c5c88717a738740a6e91dcf558fdc` |
| Full aggregate profile JSON | `38204d7b668213196dd3282ca1426cab7db1600c835419182d3a3f773397e562` |
| C1.csv | `aa54d2a7f33d43df3e73a74ecd5b4cdc0086c0f3b4b99a894b4e457bf45eaf5a` |
| C2.csv | `fdce63126a0d260a99e77b671adebd5ba498f08719399056d141ee0145c512a2` |
| New and old C3.csv, byte-identical | `ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e` |
| C4.csv | `0b40f2383a3cd7ba05315bbb39345dbc57f3ddb0039fa934552cee3cbdfc578d` |
| C5.csv | `aa6c705f50fcaec89638db1be20fd0f70f24989162501c6d82d8e8b37d66817b` |
| C6.csv | `2e6b398fe2a6cee1497ab3eccf45d0108bdb30b4f2fa6c12f276e2028c9446cb` |

Inputs are local under `E:/01-Joycecyq/2026-AAMAS/data`. This report does
not authorize their publication; only aggregate results and code are
intended for the research repository.
