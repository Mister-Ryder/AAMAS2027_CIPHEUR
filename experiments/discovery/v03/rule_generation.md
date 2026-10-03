# Rule-only proposal generation

This file records an actual proposal batch authored by the Codex internal assistant agent in one delegated agent turn. The executable proposals are in `rule_batch.json`. This was not an external model API run and was not a replay or a hand-coded replacement represented as an API response.

## Request and permitted inputs

The delegated request was to produce exactly 24 valid, diverse rule-only formulas with an empty `features` list for each candidate. Each scorer could use only `weight`, `duration`, `degree`, `conflict_weight`, `max_conflict_weight`, `compatible_weight`, `station_gap`, `satellite_gap`, and `remaining_count`. Safe arithmetic, `max`, `min`, `abs`, comparisons, Boolean conditions, and conditional expressions were allowed, subject to the 256-node ranking-rule AST limit. IDs, source hashes, lookups, oracles, an online LLM, and new features were prohibited. All 24 proposals had to be frozen before any runtime or training-quality check, and validation was limited to construction through `FeatureRuleProgram.from_dict`.

The input files accessed for proposal generation were:

- `experiments/discovery/v03/training_context.json`
- `cipheur/graph_features.py`

The training context contained 32 complete paired training graphs and 18 certified specifications. The agent inspected all contact weights, resource memberships, intervals, constraints, graph edges, fixed/excluded boundaries, and certified preference/bound information. To keep tool output readable after raw-file output was truncated, complete contact and edge information was also displayed using local integer indexes and time translations; all 18 specification graph bodies were confirmed to match graphs among those 32 pairs. The index projection was only a reading aid and is absent from executable formulas.

No guided witnesses, other-arm files, paper or method claim documents, validation data, or test results were accessed. No candidate schedules, scores, consistency measurements, or training-quality rankings were computed by this proposer.

## Frozen construction

All 24 candidate objects were written together before importing or calling the runtime construction interface. Every object contains exactly `name`, `features`, `rule`, and `rationale`; each `features` value is `[]`. Each rationale describes the proposed heuristic and its assumptions rather than claiming observed quality.

The batch spans direct reward; count, weight, and time efficiency; strongest-rival and aggregate exchange losses; preserved-reward continuation; concentrated-versus-tail loss; dominance, rival, isolation, residual-density, endgame, and setup-regime switches; load-weighted turnaround; clipped occupancy; bottleneck aggregation; and additive consensus. This is a set of distinct strategy families, not a coefficient grid. Numeric thresholds and coefficients are proposal choices without quality-based fitting.

No candidate can directly inspect edges between its neighbors or distinguish contacts with identical vectors of all nine permitted features. The batch does not conceal that information limitation through IDs or auxiliary calculations.

## Metadata and validation

- Backend: Codex internal assistant agent.
- Automated external model API calls: 0.
- Exact model identifier: not exposed.
- Candidate budget and frozen candidate count: 24.
- Token counts: not available; none are claimed.
- Quality-based candidate replacements: none.
- Construction validation: passed for all 24 frozen candidates in one post-freeze pass through `FeatureRuleProgram.from_dict`; the interface enforced safe syntax, permitted names, bounded constants, and the 256-node AST limit. The pass also checked the exact candidate count, unique names and rule strings, and empty feature lists. No score or schedule was executed, and no formula was replaced after validation.

The only files owned and written by this proposer are `rule_batch.json` and this generation record. Core implementation files and Git state were not modified.
