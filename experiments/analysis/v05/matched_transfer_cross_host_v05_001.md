# Server replay and cross-host receipt V05

The same twelve frozen TRAIN winners and compiled Degree were replayed on the same 120 contexts, giving1,560 assignments. No authoring, TRAIN selection, oracle queries, reference updates or local-result overwrites occurred. The separately stored server archive is the server evidence; the old local archive is retained.

The prior matched216-context/2,808-assignment evaluation was already run on this same server. Its server archive SHA `acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680` exactly matches the old audited local copy. It does not require a new authoring or TRAIN run.

## Matched execution counts

| Category | Count |
|---|---:|
| both_complete | 1007 |
| exact_reward_equal | 1007 |
| selected_set_equal | 1007 |
| decision_trace_equal | 1007 |
| trace_choices_counts_equal | 1007 |
| neither_complete | 506 |
| server_only_complete | 47 |

The cross-host JSON retains every changed completion/failure status and every semantic/score difference among jointly completed runs. CPU cap outcomes can differ with host throughput and interpreter version. This is execution robustness, not a new algorithm or LLM causal effect. No old native C++ timings are pooled with these new Python assignments.

Local archive SHA: `4b4888820ac71797aa5f1e05980f0216fd94acac2f9e17f65340001fdc8536a2`
Server archive SHA: `3bf2197f96206411354930a4c2c042ea393bc9f63808f1a08d0c4a78cb8b2c31`
Data SHA: `7a572d043ff0d3a05a630b5b0ecf522c90a50cef74b8e7c66fdbc6e2784e6793`
Frozen winners SHA: `37757102547f7e8b774900ac78a5c714bccb795d5471afed546f393f915e0eaa`
