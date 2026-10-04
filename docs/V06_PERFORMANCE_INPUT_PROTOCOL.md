# Fresh V06 synthetic performance input plan

`scripts/prepare_performance_v06.py` prepares inputs only. It does not import
the repair kernel, scorer, conditional oracle or native solver adapters. No
V06 performance outcome was read or executed by this agent. Existing TRAIN
inputs and the V05 capsules/results remain unchanged.

The fixed frame is 512, 1,024 and 2,048 contacts, three resource regimes, two
horizon/duration profiles and six independent source pairs per cell: 108 pairs
and 216 paired constraint endpoints. There are 129,024 unique synthetic source
contacts; the two endpoints within each pair intentionally share all contacts.
The input's statistical unit is the generated source pair, not the endpoint.
This is a specified-generator performance population, not a physical-source
or satellite mission sample and not evidence of a model-level advantage.

| Parameter | Standard | Dense/long |
|---|---:|---:|
| Horizon / contact count | 1.8 | 0.18 |
| Duration, in generator time units | uniform quarters 0.5–12 | uniform quarters 0.5–48 |
| Start time | uniform quarter slot in the horizon | same rule |
| Reward | uniform quarters 0.25–20 | same rule |
| Station switching gap, paired left → right | 0.5 → 6 | same intervention |
| Satellite switching gap | 0 | 0 |

Resources are fixed to (satellites, ground stations): balanced (8,6), ground
scarce (12,3), satellite scarce (3,12). Each resource has capacity one. Satellite
and ground assignments are independent uniform draws. These choices preserve
the existing temporal generators' parameters at larger scales; no density
pilot or optimizer outcome selected them. Actual edge counts/densities are
reported for every generated endpoint and never cause filtering or re-drawing.
Dense/long names the generator profile; it is not a promise about every
realized graph's relative edge count. Since horizon scales with n, this
protocol does not silently increase expected local contention with size.

The new seed namespace is `V06_FRESH_PERFORMANCE_TEST_20261003_001`. Full SHA256
of namespace plus profile/regime/size/index supplies each independent RNG
seed. Unlike the earlier same-seed resource pairing, no different resource
cell reuses a seed or synthetic contact identity. Contact IDs use the new
`v06perf_001_` prefix and deterministic cell ordinal/index. No old contact
records or physical source IDs are imported. New draws can coincidentally
have equal attribute values; the claim is new source identities and draws,
not a guarantee of unique numerical attributes.

First freeze the metadata, complete cell inventory and generator/model source
hashes without generating a graph:

```text
python scripts/prepare_performance_v06.py --out NEW_INPUT_DIR --plan-only
```

After copying those same source bytes, generate the fixed inventory:

```text
python scripts/prepare_performance_v06.py --out NEW_INPUT_DIR --generate --workers 4
```

Optionally add `--selection TRAIN_SELECTION.json` to bind a receipt containing
twelve genuine selected programmes, `selection_split=train` and
`test_accessed=false`. Input generation itself can precede assessment because
its parameters are independent of all candidate outcomes; a solver TEST run
must still wait for the programme/configuration TRAIN freeze. The builder has
no TRAIN branch. Any new TRAIN design needs a separate explicit protocol.

`protocol.json` and `freeze_receipt.json` precede generation. `data.json`
provides 108 `test` pair records and 216 explicit `contexts` for runner
compatibility. `input_identity.json` pins original contact IDs and endpoint
graph digests, sizes, edge counts and densities. `input_progress.json` reports
generation progress; `input_completion.json` confirms the whole input frame
and hashes. No optimization completion is implied. Changed plan/source bytes,
duplicate identities, missing endpoints, replacing an existing input file and
alternative-seed recovery are rejected. A generation exception preserves a
failure receipt and partial progress; a new attempt requires its own preserved
input directory/protocol rather than overwriting observations.

Three targeted tests check exact prespecified counts/seeds/parameters, tiny
deterministic contact identity and independently reconstructed temporal
conflicts, and metadata freeze/round-trip/tamper rejection without graph
generation. Only twelve-contact fixtures were generated locally; no 216-state
performance data, candidate evaluation or solver outcome was produced here.
