# Free-joint actual assistant proposal provenance

- Arm: `free_joint`.
- Backend: Codex internal assistant agent. The exact model identifier was not exposed by local orchestration.
- Delivery: one independent assistant generation turn produced all 24 candidates in `free_batch.json`. These are actual newly authored assistant proposals, not an automated model API response, a replay, or a claim that an API was invoked.
- Automated model API calls: 0. Local shell/Python work serialized the assistant-authored expressions and performed construction checks.
- Candidate budget: 24, delivered exactly once as a frozen batch. No candidates were discarded or replaced after outcome evaluation.
- UTC creation time: 2026-10-03T02:52:13.279717+00:00.

## Inputs inspected

1. `experiments/discovery/v03/training_context.json`: operation signatures, base features, 32 full training graph pairs, and 18 supplied certified relational specifications. The large raw context was inspected together with programmatic summaries of its own training graphs and supplied specifications. Training specification preferences and bounds were allowed inputs for this arm.
2. `cipheur/graph_features.py`: the allowed typed-expression and `FeatureRuleProgram.from_dict` construction interface, including deterministic operation semantics and safe scorer syntax.
3. The parent's direct free-joint generation instructions. No guided representation target, contradiction witness, or feature repair request was provided to this arm.

Training-context SHA-256: `5ed27fcc1b5e5b7bb32b9163fd36e2fce2a3805c1db9daa976ee8b1db71bf1b0`.

No guided witness file, other arm proposal or provenance file, paper, method document, theoretical claim, validation data, test data, or test result was opened. No candidate schedule evaluation or metric-based search was run. Shared training metadata present inside the permitted context was not incorporated into any executable feature or rule.

## Generation approach

The portfolio was authored jointly over representation and scorer. It spans local feasible and upper-estimate opportunity costs, weighted edge and density surrogates, absolute and ratio decisions, piecewise regret, whole compatible-schedule estimates, include-versus-exclude margins with several bound orientations, temporal efficiency, two-sided cohesion, and closed replacement bundles. All candidate rationales are preserved in the raw JSON. Candidates are hypotheses for downstream selection, not a claim of validated optimality or measured requirement satisfaction.

Each feature uses only the supplied deterministic typed graph operations. Each scorer uses only the nine base features, that candidate's extra numeric features, bounded constants, and safe arithmetic/max/min/abs. No contact identifier, station identity, satellite identity, instance name, side label, hash, table lookup, oracle result, or online LLM is referenced by an executable proposal. Graph set operations are evaluated on the current active set by the shared runtime.

Cost was considered during generation: local one-feature proposals provide cheaper alternatives to broader continuation estimates; larger graph-work candidates are included only to test meaningful scheduling approximations. Several candidates reuse identical typed subexpressions for the runtime's immutable-active-set memoization. This is a portfolio of structural strategies, not a coefficient grid.

## Construction checks

All 24 raw candidate dictionaries were accepted by `FeatureRuleProgram.from_dict` before delivery. Candidate names are unique. The maximum additional feature count is 2 of the allowed 6. The maximum typed feature expression size is 9 nodes of the allowed 48, and its maximum depth is 6 of the allowed 8. Scorer construction checks passed. Divisors in all ranking rules are positive by an added one or a `max(1, ...)` guard on the supplied nonnegative contact data; feature expressions introduce no division operations.

Construction validation reads only the authored batch and runtime interface. It does not run scheduling, inspect validation or test schedules, rank candidates by performance, or alter any candidate.

Delivered batch SHA-256: `b642fb86bb3cb53616c41e38f5fb18791b2887274728dd6470e0fe786783b79d`.
