# V07 C6/W6 TRAIN input scene screen

The single input-only execution completed **48/48 graphs in 24/24 prescribed windows, with zero failed windows**. It made no optimizer, conditional-oracle or LLM call. Day 1 and day 2 contacts were not materialized as graph inputs; their start-day counts were read as source metadata only. No labels, candidate programs or scheduling outcomes were read.

The natural weighted scenes have exact full-base-nine aliases, but they are uncommon: 556 size-two classes across the 48 configuration graphs, involving 1,112 of 282,066 action occurrences (approximately 0.394%). This is an input collision census, not evidence of contradictory preferences. All 48 initial graphs are connected. Every prescribed ground-transition intervention changes graph structure. These observations support a meaningful real-data configuration scene while leaving the availability and usefulness of sound decision labels unresolved.

## Fixed frame and source ownership

Both C6 and W6 cover **three days**, not six. Their timestamps are relative integral seconds, with observed minimum link start 0 and maximum link end 259,200. The source names indicate nested opportunity families/density, not the number of days. The source containment/exposure audit is owned separately by root; these two sources are not assumed independent.

| Source | Full rows | TRAIN day-0 rows | Day-0 grounds / satellites | Cross-window-end contacts retained |
|---|---:|---:|---:|---:|
| C6 | 140,406 | 47,156 | 40 / 168 | 6,590 |
| W6 | 279,521 | 93,877 | 80 / 168 | 12,903 |

TRAIN ownership is `0 <= link_start < 86400`, divided into all twelve half-open 7,200-second start windows per source. No contact end is clipped. These are independent static opportunity frames with empty fixed/excluded boundaries; combining their schedules into a feasible full-day calendar is not claimed. Contacts crossing a window or split boundary keep their original intervals and remain owned by their start window.

Each window is built twice, with ground transition 340/680 and satellite change/transition 150/300. Resource identity normalization is explicitly whitespace/BOM trimming followed by removal of terminal single/double quote characters; this includes unpaired quote artifacts in W data. It differs from the old loader's paired-quote-only cleanup. Exact integer times and duration weights are preserved. The original frozen V51 `Arc`, `ConflictParameters` and `build_conflict_graph` are reused; in particular, the inherited crossing-overlap satellite predicate is not replaced with an ideal interval-capacity model. Source priority fields do not replace the duration objective.

Raw CSV bytes and resource/contact fields stay at their local source paths. Published-style outputs contain aggregates, graph digests, normalized TRAIN row-identity hashes and source/source-code receipts. No raw CSV is copied into the screening namespace or source capsule.

## Actual TRAIN census

The following sums retain dependence between configurations of the same window. Component and median-degree ranges are over the twelve windows for that row. A full-base-nine class uses reward, duration, degree, neighbor-weight sum/maximum, compatible-weight sum, ground gap, satellite-change gap and residual count, with exact integer arithmetic and no bucketing or rounding.

| Source / ground gap | Window n range | Window m range | Density range | Median degree range | Full-base9 alias classes / action occurrences | Descriptor-split classes |
|---|---:|---:|---:|---:|---:|---:|
| C6 / 340 | 3,563–4,252 | 67,999–92,843 | 0.01002–0.01072 | 39–45 | 126 / 252 | 0 |
| C6 / 680 | 3,563–4,252 | 79,513–109,128 | 0.01167–0.01253 | 45–53 | 112 / 224 | 1 |
| W6 / 340 | 7,642–8,760 | 147,133–175,924 | 0.00459–0.00506 | 39–41 | 164 / 328 | 2 |
| W6 / 680 | 7,642–8,760 | 174,690–209,577 | 0.00546–0.00599 | 47–49 | 154 / 308 | 0 |

Every alias class has size two, so the class counts above also equal unordered aliased-pair counts. The additional descriptor contains degree, ground-only/satellite-only/both-reason neighbor counts and the number of distinct neighbor resources. It is a coarse domain descriptor, not a complete rooted-isomorphism test and not a claim that those fields are available to the existing typed scoring library. Only three exact classes split under that particular descriptor. Classes whose descriptor agrees may still differ in uncounted neighborhood topology; classes whose descriptor differs need not differ in completion value.

The coarser `(weight,duration,degree)` projection has respectively 8,062 / 7,760 / 17,186 / 16,565 non-singleton classes across the four rows, involving 19,656 / 18,456 / 42,989 / 40,170 action occurrences. This shows that repeated degree/weight states are common while adding the complete neighbor-weight information greatly reduces collisions. These projection counts are not substituted for the full-base-nine theorem or gate.

All graphs have exactly one connected component, whose size is the window n. This does not establish the connected components of each forced-action conditional residual; no such queries were made. It flags a possible cost boundary for full-residual certificate acquisition, rather than proving that every comparison is intractable.

## Configuration response

| Source | Changed windows / assigned | Added edges, all windows | Roots with changed neighborhoods / distinct TRAIN contacts | Changed graph-only seven-field vectors |
|---|---:|---:|---:|---:|
| C6 | 12 / 12 | 170,974 | 47,074 / 47,156 | 47,074 |
| W6 | 12 / 12 | 343,969 | 93,763 / 93,877 | 93,763 |

No edge was removed and no existing edge changed only its reason mask. Full nine-field vectors change for every action because the explicit ground-gap field itself changes. The graph-only seven-field diagnostic removes the two gap coordinates solely when measuring the response of other graph-derived inputs; it is not a silently redefined primary representation or deployed grammar. It demonstrates graph response, not learned adaptation accuracy.

The fixed pattern census counts unordered pairs of root spokes with edge-reason masks 1 (ground), 2 (satellite) or 3 (both). It includes the six predefined mask-pair classes and root-presence counts. It deliberately does not classify the edge between the two neighbors, so these are coarse centered-spoke classes, not induced-wedge or triangle counts. Their prevalence cannot be interpreted as repeated decision preferences. Later-window recurrence coverage is not yet evaluated because validation/heldout graphs were not built.

## Execution timeline and preserved packaging failure

1. Metadata profiles confirmed exact source hashes and origin 0. Root revised the initial six-day assumption to day-0 TRAIN, day-1 validation and day-2 retrospective heldout before graph construction.
2. `contact_scene_screen_v07_001` prepared source/input hashes without graphs. Its first execution stopped before worker creation because JSON converted integer metadata dictionary keys to strings and the reload equality check compared unlike key types. No graph, schedule, oracle or model call occurred. This namespace and its frozen bytes remain preserved.
3. The new script makes metadata day keys explicitly strings. No source contact, conflict rule, feature key, window or graph assignment changed. A new namespace `contact_scene_screen_v07_002` was prepared and frozen before execution.
4. Eight input workers constructed the two prescribed graphs per window once. The 24 tasks finished with zero failure. Recorded batch wall time after execution-receipt creation is 6.4825 seconds; summed task CPU is 41.8594 seconds and task wall is 42.9637 seconds. Task times include legacy import/build/census within workers, while initial source parsing and preparation are outside that batch interval. These are input-preparation costs, not algorithm performance timings.

## Replay and evidence

Script: `scripts/screen_contact_scene_v07.py`. Run the existing namespace only for inspection, not as an overwrite/resume. A new replay namespace must first run `prepare` with the same two source names, CSV paths, raw SHA pins, day0/origin0/eight-worker contract, then `run`. The source capsule contains code only; a replay operator needs access to the pinned local CSV files and the pinned original V51 project source.

Canonical outputs under `experiments/discovery/contact_scene_screen_v07_002/`:

- `protocol.json`: exact frame and no-filter/call constraints.
- `train_identity_inventory.json`: all 24 ordered window identities and TRAIN row hashes; 10,726,599 bytes.
- `freeze_receipt.json` and `source_snapshot.zip`: pre-graph code/input bindings.
- `execution_receipt.json`, `window_results.jsonl`, `screen_summary.json` and `completion_receipt.json`: all assigned graphs, terminal status and results. Summary is 1,183,096 bytes.

| Artifact | SHA-256 |
|---|---|
| C6 original CSV | `2e6b398fe2a6cee1497ab3eccf45d0108bdb30b4f2fa6c12f276e2028c9446cb` |
| W6 original CSV | `c0fe378c68400d985c05617d89e41b320df03e6565b91ac7ad6821a6659e01ca` |
| New screening script | `9a2782bf5ef002d7c50a1ff6587affac23ea6b1d1cbb0d89fd4730afc4fb9365` |
| Completed protocol | `bd490e0045d73720db1beefcc57adaa710cd90db1bd0c1206276f00caff0a39c` |
| Completed freeze receipt | `d28a592a5236ef2fa021706547ab298277f90849c776754fb7bf1811aca8efdd` |
| Code-only source snapshot | `82676c71f7afc1313a716421485694dd1a593ccd0fca3ec931c8c3f4c401edf2` |
| Completed screen summary | `f01d60e86231cef5f726e22353400e7ad39159c85ecf86859d1f637d220dd6dc` |
| Completion receipt | `f8d0224d1307ec50e491eaf27ca2624b9e0d3355cb4f4a37622a251d7383d997` |

## Supported next decision

This scene is not vacuous at the input-alias level, and actual constraint intervention changes nearly all contact neighborhoods. It is also much larger, connected and more heterogeneous than the old tiny unit-weight certificate setting. These are reasons to define a bounded, honest TRAIN evidence-acquisition plan, not a claim that the LLM will improve schedule quality. Freeze any comparison inventory and boundary scope before labels, preserve all aliases/non-alias controls and unknowns, and do not choose only the three descriptor-split classes. Missing certificate closure, absent strict contradictions and unchanged complete reward are valid outcomes. Validation/heldout construction and any optimization remain outside this completed task.
