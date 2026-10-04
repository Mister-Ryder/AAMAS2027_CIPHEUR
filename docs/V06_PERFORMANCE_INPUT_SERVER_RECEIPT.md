# V06 fresh performance inputs: cloud generation receipt

All prescribed 108 source pairs / 216 TEST endpoints were generated on the
authorized cloud server. This stage computed input graphs only: no solver,
synthesized candidate, conditional-value oracle, or reference solution was
evaluated. The twelve genuine TRAIN winners are not yet bound (`selection`
is explicitly null); future TEST optimization must wait for their separate
selection freeze.

## Outcome-free design and source freeze

The generator fixed three sizes (512, 1,024, 2,048), three resource regimes,
two temporal profiles, and six independently seeded source pairs per cell.
There are 18 cells, 108 pairs, and 216 endpoints. Every prescribed cell is
retained; no realized density, optimization quality, or post-test property
was used to drop/reseed a cell. Left/right endpoints intentionally share all
contacts and differ only in station switching gap 0.5 versus 6.0. Satellite
gap is zero. Contacts are single-capacity synthetic pairwise contacts, not
physical C3 observations.

Resource counts `(satellites, grounds)` are balanced `(8,6)`, ground scarce
`(12,3)`, and satellite scarce `(3,12)`. Starts, durations and rewards are
quarter-valued. Standard horizon is `1.8*n`, with durations 0.5–12; dense-long
horizon is `0.18*n`, with durations 0.5–48. Rewards are uniformly selected
quarters 0.25–20. Exact integer encoding therefore uses at most scale four
and safely fits the old conservative native weight range at these sizes.

- Original generator: `scripts/prepare_performance_v06.py`, SHA256
  `893115422a9e7dbae61105cec7ffa27d257e8a482cab380af9909c11a4364ee8`.
- Unchanged physical-model source: `cipheur/model.py`, SHA256
  `d5968cffb1676a2f4bd73d5ba2715618142059b0c81ec8263f76a79100a8a1d8`.
- Source capsule:
  `experiments/source_snapshots/v06/performance_inputs_v06_001_source.zip`,
  SHA256 `4fe4e952965ed4e92e3de32e93b92c5e13c5966bd817917ead4248d8d852a067`.
- Server `--plan-only` froze the full cell/configuration/source protocol before
  generating any graph. Original protocol SHA256:
  `d1184a1eb47c451847d34cb5ebc8e5a83dda4ef56382c820112750e9a9ec9b92`.
- Metadata/freeze/host receipts are in
  `experiments/discovery/performance_inputs_server_v06_001/` and in the archive.

## Cloud generation and data coverage

Remote directory `/root/autodl-tmp/aamas2027_v06_performance_inputs_001`, PID
50123, four workers, reused Python 3.11.17, persistent detached logs. The
original generation/serialization/checking wall time was 50.843 seconds.
There were no generation errors, alternative seeds, or redraws. The original
source/plan/completion bytes were preserved; host/source/startup bindings were
appended separately.

All 129,024 source contact IDs are unique across pairs; the two endpoints of
a pair intentionally repeat those same IDs. Each of the six regime/profile
families contains 36 endpoints (three sizes × six pairs × two sides). All 216
graph hashes are unique. Across endpoint sizes and sides, realized density
ranges from about 0.00088 to 0.20173. These are reported properties, not input
filters. Paired endpoints are dependent; the experimental statistical unit is
the source pair, not two independent contact sets.

## Downloaded evidence and independent implementation check

- Raw input archive:
  `experiments/runs/v06/performance_inputs_v06_001.tar.gz` (44,851,806 bytes),
  SHA256 `1f853ec90153ecd65418119352c13d9e17242e6dddd407ed8eaa45f7bf3aa20b`.
- Full `data.json` SHA256:
  `23caf12cca124aa1ed97f7848454b8a6ac2bb283462c4719510bd6fc30357548`.
- Endpoint identity metadata:
  `experiments/analysis/v06/performance_input_identity_v06_001.json`, SHA256
  `40057a9b68e09f261c04979f4ebe1989123851a0ee06ff6636fdfc650a1ac001`.

The separately written `scripts/check_performance_inputs_v06.py` imports no
project generator, graph model, scheduler or oracle. It uses an independent
interval sweep within each station and satellite resource and checks exact
equality to every original graph's edge set, not only selected solution
feasibility. It also checks graph hashes, input/metadata hashes, all 108 paired
contact equalities and monotone edge interventions, all endpoint identities,
global contact namespaces and all 258,048 endpoint contact-field records.
There were zero assertion failures or optimization calls. The result is
`experiments/analysis/v06/performance_inputs_check_v06_001.json`; checker SHA256
is `d61af5a5d9563c74ca21f46513ce5ddbd305dcce7a34027681ee933139bcf1b3`.
This is an independent implementation check, performed by the execution
agent; a separate peer audit can additionally assess the derivation and code.

Input generation and correctness checks provide no quality, SOTA, or LLM
benefit evidence. Those require the forthcoming separately frozen shared
kernel/native comparison and retained outcomes under declared cost scopes.
