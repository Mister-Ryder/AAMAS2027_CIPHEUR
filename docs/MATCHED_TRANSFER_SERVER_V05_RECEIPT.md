# V05 frozen-program transfer: separate cloud replay

The 120-context exploratory transfer experiment was replayed on the authorized
cloud server with the same 12 TRAIN-frozen programmes, Degree control, graph
identities, original verified U/L references, compiled score-slice evaluator,
deterministic seed, and five-CPU-second cooperative scheduling cap. This is a
cross-host replay of previously exposed graphs, not a new independent test
population. No programme was reselected and no local outcome was overwritten.

The actual cap begins after AST parsing, as documented in the pre-existing
append-only budget clarification. Returned CPU/wall timing starts before
parsing and includes validation and cooperative overshoot. Old native results
have a different host/budget/backend scope and are not mixed into this replay
as equal-cost comparisons.

## Freeze and execution

- Protocol: `configs/matched_transfer_server_v05.json` and
  `experiments/discovery/matched_transfer_server_v05_001/protocol.json`.
- Protocol SHA256:
  `492ea9d3c94228c1a86c00a8f7b9b1e8f9f2489f16ec04d833a99abd64e2debc`.
- Source capsule SHA256:
  `b04c965d4bce9b942f4544e2570db28122eacc73b9a5f473854d784c4e1ab9b4`.
- Frozen winner file SHA256:
  `37757102547f7e8b774900ac78a5c714bccb795d5471afed546f393f915e0eaa`.
- Graph data SHA256:
  `7a572d043ff0d3a05a630b5b0ecf522c90a50cef74b8e7c66fdbc6e2784e6793`.
- Cloud directory: `/root/autodl-tmp/aamas2027_v05_transfer_server_001`.
- PID 47914, detached persistent log, Python 3.11.17 reused. Eight workers
  used half the 16-core CPU quota. No other research process was interrupted.
- All 1,560 assignments returned: 1,054 completed and 506 retained `_CPUCap`
  failures. No declared hard-wall safeguard triggered. Whole-job wall time
  was 484.669 seconds.

## Cross-host results

All 1,007 assignments completed on both hosts have identical exact reward,
selected set, and full decision trace, including scores and remaining-action
counts. Another 47 assignments completed on the cloud server but hit the cap
locally. There were 506 failures on both hosts and no local-only completion.
The paired completion differences are retained individually in
`matched_transfer_cross_host_v05_001.json`.

These differences matter scientifically: the five local C3 Witness failures
and the local Degree SATLIB 975-vertex failure do not recur on the cloud host.
The earlier local completion-rate figure therefore describes the local host
only. Large SATLIB synthesized-program failures persist, while cloud Degree
completes all SATLIB contexts; this replay does not establish a Witness-arm
or LLM advantage. The separate server analysis retains each arm's four block
means, failure-zero quality, original U/L denominators, and every timing.

The server also retained the original 2,808-assignment V05 matched evaluation
archive at `/root/autodl-tmp/aamas2027_v05_matched_001/`, with SHA256
`acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680`.
That hash matches the original local immutable copy. It had already been run
on this cloud deployment; author generation and TRAIN evaluation were not
repeated for the transfer replay.

## Downloaded evidence

- New raw archive:
  `experiments/runs/v05/matched_transfer_server_v05_001.tar.gz`, SHA256
  `3bf2197f96206411354930a4c2c042ea393bc9f63808f1a08d0c4a78cb8b2c31`.
- Results SHA256:
  `dc70c96ed0ab1829673c9ed1f07af77958ae2ce9efb05e3e5f3cfe735893de09`.
- Validation SHA256:
  `f342d105a8da28349e65d696c182c6daf549bd864156e29c7e27857891a0d36c`.
- Analysis:
  `experiments/analysis/v05/matched_transfer_server_v05_001.json` and `.md`.
- Cross-host paired comparison:
  `experiments/analysis/v05/matched_transfer_cross_host_v05_001.json` and `.md`.

After every assignment and the original `complete.json` had been written,
archiving initially failed because the empty archive-parent directory was
absent from the source ZIP. Only that directory was created; existing result
and validation hashes were checked against the complete receipt, then the
existing outputs were archived. No assignment was rerun. An append-only
`packaging_receipt.json` in the archive documents the packaging recovery.
Independent scientific auditing of this new cloud archive is separate from
the already completed audit of the local archive. The server-specific audit
subsequently completed 156,291 checks with zero errors, including the exact
cross-host joins, source bindings, original bounds and full saved traces:
`docs/MATCHED_TRANSFER_SERVER_AUDIT_V05.md`, with JSON receipt
`experiments/analysis/v05/matched_transfer_server_audit_v05_001.json`, SHA256
`5052a311eb5b4003571784e70e9aaf72ff023619aef47e4a11b2e8a81b7f5350`.
