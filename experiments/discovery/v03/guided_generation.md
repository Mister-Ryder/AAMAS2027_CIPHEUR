# Guided proposal generation provenance

- Arm: guided.
- Backend: Codex internal assistant agent.
- Exact model identifier: not exposed.
- Automated model-provider API calls: 0.
- Generation protocol: one assistant-agent turn, 24-candidate budget, one completed batch.
- Provenance first recorded: 2026-10-03 02:47:47 UTC.
- Completed and checked: 2026-10-03 02:52:44 UTC.
- Proposal artifact: `guided_batch.json`.

The JSON is the actual assistant-authored proposal response from this turn. The 24 feature sets, rules, names, and rationales were synthesized explicitly by the assistant. A small deterministic serialization helper expanded the authored typed-operation trees into JSON; it did not generate candidates through replay, retrieval, a coefficient grid, a graph oracle, or a model API. Each rationale is retained in the raw response JSON.

## Inputs and separation

The proposal request files were `training_context.json` and `guided_witnesses.json`. Implementation reads were limited to `cipheur/graph_features.py` for the typed expression and safe ranking schema and `cipheur/model.py` for graph loading and feasible runtime checks. No other-arm proposal files, validation data, test data, test results, or paper conclusions were read. No source code or Git state was changed.

The guided input reports 32 self-loop requirements in the quotient on base feature vectors. The concrete witnesses show equal base vectors with independent neighbor triples, an edge plus an isolated neighbor, and a clique, including interventions whose certified preferred action reverses and interventions whose preferred action is preserved. The proposal response therefore uses current graph structure rather than candidate identifiers, source identifiers, split labels, instance lookup, or an intervention-specific threshold.

## Structural hypotheses

The batch deliberately spans different graph summaries and decision formulas:

- Cheap neighborhood edge counts, edge-minimum weight, and edge-product weight, with caps, diminishing returns, density normalization, and duration/setup normalization.
- Compatible residual edge corrections and retained-subgraph density.
- Weighted conflicts eliminated from the entire active graph.
- Neighborhood clique-cover and greedy-independent estimates, with net gain, relative pressure, midpoint, uncertainty penalty, and adaptive bracket policies.
- Retained clique-cover and greedy-independent continuation estimates, with optimistic, feasible, midpoint, downside-sensitive, exchange-ratio, and size-adjusted policies.
- Cross-boundary edge weights linking excluded neighbors to compatible retained contacts.

The primitives `clique_cover_weight` and `greedy_independent_weight` are the allowed fixed polynomial graph operations. They do not invoke conditional certificates or an online model. Traversal cost is a tradeoff: simple edge statistics offer lower work, whereas continuation and bracket features may justify more work only if later evaluation supports that choice. These are candidate hypotheses, with no claimed generation or generalization benefit.

## Validation performed

All 24 candidates successfully constructed through `FeatureRuleProgram.from_dict`. There are 24 unique names. The maximum number of additional features is 3; the maximum feature expression has 9 AST nodes and depth 6, within the limits of 6 features, 48 nodes, and depth 8.

All candidates were executed by the unchanged scheduling kernel on both sides of all 32 supplied training pairs, for 1,536 runtime/feasibility checks. Every schedule was feasible, and no score or feature evaluation failed. This check inspected execution validity only; no validation/test performance, arm comparison, or candidate-selection result was produced or used to revise the batch.
