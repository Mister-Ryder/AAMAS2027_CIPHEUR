# CIPHEUR STK 20261005 public research bundle

This directory is the reviewable data-construction bundle used by the online-v2 study. It contains the final graph instances, the contact tables needed to rebuild them, STK generation and graph-building code, source parameters, validation receipts, and the principal data reports. Algorithm code and complete scheduling results are stored under [`experiments/stk_online_llm_v2`](../../experiments/stk_online_llm_v2/README.md).

## Released benchmark instances

| Part | Physical libraries | Configurations per library | NPZ graph instances | Role |
| --- | ---: | ---: | ---: | --- |
| `extensions/heterogeneous_ground_v1/graphs` | 4 (`AU/AP × r000/r001`) | A/W/E/J | 16 | TRAIN development |
| `perf_dataset_v1/graphs/*r006` | 2 (`AU/AP × r006`) | A/M/J/stress/W/E/MW/ME | 16 | validation, not used to select online-v2 |
| `perf_dataset_v1/graphs/*r008,*r009` | 4 (`AU/AP × r008/r009`) | A/M/J/stress/W/E/MW/ME | 32 | held-out TEST, not executed by online-v2 |

The primary benchmark therefore contains **64 graph instances** from ten physical STK libraries. Each library has 84 satellites, 12 ground stations, and a 72-hour planning horizon. Configurations belonging to the same physical library preserve contacts, node identities, and duration rewards; resource-conflict edges change with the declared station gaps.

The release also preserves two earlier diagnostic families:

- `graphs/`: 16 uniform-gap P0 graphs (`340/680/1200/1800` seconds);
- `extensions/joint_resource_v1/graphs/`: 16 joint-resource diagnostic graphs used to determine that the tested satellite-gap axis did not provide an effective independent change.

These diagnostic families are provenance for dataset design and are not extra independent TRAIN/TEST observations.

## Configuration semantics

`A=(340,340)`, `M=(680,680)`, `J=(1200,1200)`, and `stress=(1800,1800)` use uniform west/east ground-station gaps. `W=(1200,340)`, `E=(340,1200)`, `MW=(680,1200)`, and `ME=(1200,680)` impose heterogeneous simultaneous constraints. Satellite turnaround is fixed at 150 seconds in the final benchmark.

Every optimization reward is the original contact duration in exact integer microsecond ticks. The microsecond representation freezes numerical inputs; it is not a claim that the underlying physical simulation is accurate to one microsecond.

## Reproducibility contents

- `raw_contacts/`: final contact and boundary tables plus per-library geometry, generation recipe, environment, precision, EOP, and sampling receipts. Large editable STK object files are omitted.
- `scripts/`: STK automation, graph construction, profiling, evidence generation, and source-index code.
- `source_plan/` and `source_dependencies/`: frozen scenario parameters and Earth-orientation source receipts.
- `analysis/`: input contracts, profiles, graph screens, boundary sensitivity, quotient summaries, and data-construction reports.
- `extensions/*/analysis` and `perf_dataset_v1/analysis`: stage-specific data reports and figures.
- `RELEASE_MANIFEST.json`: byte size and SHA-256 of every released file other than the manifest itself.

Run the read-only integrity check from the repository root:

```text
python datasets/CIPHEUR_STK_20261005/scripts/verify_public_release.py
```

The graph format and mathematical edge semantics are documented in [`analysis/图数据格式与数学语义.md`](analysis/图数据格式与数学语义.md). The complete data-construction history is retained in [`README_数据说明.md`](README_数据说明.md); later extension conclusions do not overwrite the original negative P0 result.

Some frozen receipts and source metadata retain the original Windows or cloud paths as provenance. Those fields document where a run occurred; they are not portable runtime dependencies. Public replay should resolve files relative to this release root as described by the current scripts and manifest.

## Deliberately excluded material

The local working directory also contains about 1.27 GB of editable STK satellite-object files, stale-EOP diagnostics, failed attempts, Python caches, and duplicate cloud working copies. They are reproducible or operational intermediates and are not required to run the released graph experiments. They were excluded to keep the Git repository usable. Original contacts, final graphs, generation code, source parameters, hashes, and scientific reports are included.

No online-v2 validation or TEST scheduling quality was read to construct this release. The two completed online-v2 development rounds used only the 16 TRAIN graphs; their full results, including negative outcomes, are preserved in the experiment directory.
