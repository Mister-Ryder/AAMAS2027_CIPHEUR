# V05 evidence replay

Core scheduling uses Python 3.10+ and the standard library. Analysis figures need the existing optional research dependencies; PDF page checks additionally need pypdf. The recorded native CLI authoring launcher uses Python 3.11+ and a host-specific Codex executable. Replaying existing evidence does not need model authentication or a server.

Do not overwrite frozen receipts or result archives. Run from the repository root and send regenerated analyses to a separate directory:

```text
python scripts/verify_release_v05.py --paper-layout
python scripts/verify_matched_llm_v05.py --study experiments/discovery/v05 --train experiments/runs/v05/matched_train_v05_001.tar.gz --eval experiments/runs/v05/matched_eval_v05_001.tar.gz --source-zip experiments/source_snapshots/v05/matched_v05_001_source.zip --out output/v05_replay/independent.json
python scripts/analyze_matched_v05.py --train-sha256 eca11e5803ab68ba7456eca496c53a331b533fcf925eb4e108b019b1d6825d49 --fresh-sha256 2c2dca62ed8b769f3e7929f6beee9ef16b91f0617eba04ec5885b0ce3fb6610a --evaluation-sha256 acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680 --out output/v05_replay/results.json --figure output/v05_replay/curves.pdf --table output/v05_replay/table.tex --markdown output/v05_replay/results.md
```

The independent audit checks all gates, scalar TRAIN agreement, exact feasible trace rewards, TEST clique references and every completed first argmax. Later TEST scores are not reexecuted. The analysis checks stored traces/references and arithmetic; it performs no new rollout, candidate selection or oracle query. Neither check substitutes for the original budgeted execution measurements.

The separate public diagnostic protocol and audit command are in [PUBLIC_ALIAS_DIAGNOSTIC_V05.md](PUBLIC_ALIAS_DIAGNOSTIC_V05.md) and [PUBLIC_ALIAS_RESULTS_REVIEW_V05.md](PUBLIC_ALIAS_RESULTS_REVIEW_V05.md). Complete-graph and induced-subgraph tracks must remain separate. Preserved execution source capsules identify the actual code run; the current package release metadata is newer than the capsules' metadata. The ten matched semantic modules and public execution hashes are unchanged.

The V04 whole-release verifier must run at immutable commit `de0f70565eb56ceb6c2d2324481017a94782ec62`. Current V05 verification instead checks the retained V04 evidence/assets and every new archive, plus the final independent-audit hash chains.

## Retained candidate and local exploratory transfer

The current V05 paper is a retained candidate, not a completed release or final algorithm decision. The new user requirement starts V06 structural local-repair research; publication/security-release preparation is paused. Candidate PDF date/hash and current pending work are in `docs/DELIVERY_V05.md`. No V04 raw evidence is replaced.

The local extension keeps all twelve original TRAIN winners and Degree on the already observed public96/C324 inputs. Its archive records all 1,560 assignments, with 1,007 successful schedules and 553 CPU-cap failures. This is exploratory reuse of input populations, not a fresh independent holdout. Recheck the immutable archive without rerunning a policy or overwriting its report:

```text
python scripts/verify_matched_transfer_v05.py --archive experiments/runs/v05/matched_transfer_exploratory_v05_001.tar.gz --analysis experiments/analysis/v05/matched_transfer_exploratory_v05_001.json --out output/v05_replay/local_transfer_audit.json
```

This audits all assignment/trace/reward/reference identities and a bounded 130 initial argmax cases, not every later score. Current original archive SHA256 is `4b4888820ac71797aa5f1e05980f0216fd94acac2f9e17f65340001fdc8536a2`; source ZIP SHA256 is `81cee9ea27374ba055cc15a6af11d810c7aad68982a1830fbae045d202031b62`. The source capsule and frozen protocol remain byte-identical. Append-only `budget_scope_clarification.json` explains that the meter begins after AST parsing, while returned process CPU/wall includes parsing, initialization, scheduling and validation. Materialization/source reconstruction is recorded separately.

The user-requested server replay of these 1,560 assignments and additional platform checking of the original 2,808 TEST assignments are **pending**. Future server outputs must have separate receipts and archives; a local audit or completed-assignment receipt does not certify server execution. Report each host/budget/source independently, without pooling old native timings, excluding failures or selecting new winners. Do not rerun any `prepare`/`analyze` command into the frozen scientific directories. The final release manifest/CI will be refreshed by its owner only after the research and added verification are complete.
