# Outcome-free C3 interval input preparation

The authorized server prepared two separate exploratory tracks from the
original 12 C3 source blocks: the unchanged 24 V51 legacy conflict contexts,
and 24 new single-capacity resource-interval contexts. This prepares inputs
only; no schedule, candidate ranking, native solver, conditional oracle or LLM
was executed.

Every one of the 2880 original contacts was matched to its exact C3.csv row.
Original resource labels, link start/end times in seconds and duration rewards
were checked. Each new view uses integer reward `end-start`, ground transition
gap 0.5 seconds on the left and 6 seconds on the right, and satellite gap zero.
The same contacts appear on both sides. The interval graph joins two contacts
that share a station or satellite when their reserved intervals conflict under
these gaps. All source blocks and zero-change pairs are retained.

This transformation changes the constraint model; it does not claim to preserve
the original V51 crossing/overlap semantics. Both tracks remain separately
labeled. The original blocks and legacy contexts were exposed in V04/V05, so
neither track is a new independent natural held-out population. The raw C3
dataset has 69923 source rows; these experiments use the inherited 12 disjoint
subproblems, not the full raw scheduling problem.

The source/input protocol was frozen before construction:
`experiments/discovery/c3_interval_inputs_v06_001/protocol.json`, SHA256
`c198e3db04124ce8445caa2759e6a545d015a854ee0a56abdcfa0c203d010950`.
The input/source capsule is
`experiments/source_snapshots/v06/c3_interval_inputs_v06_001_source.zip`,
SHA256 `118c76f9b572e60f44e230d968d014562eb63166d74b40dc3c6d294e615d70bc`.
Its CSV source bytes have SHA256
`ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e`.
Construction ran in
`/root/autodl-tmp/aamas2027_v06_c3_interval_inputs_001`, PID 52561, and the
immutable downloaded input archive is
`experiments/runs/v06/c3_interval_inputs_v06_001.tar.gz`, SHA256
`af7c0295a8db99e3eacb8d5d6e1a0183a87808312ca04bb280f01e10b69323a9`,
1,321,474 bytes. All 48 context identities and original metadata are preserved.

`scripts/check_c3_interval_inputs_v06.py` independently checks original CSV
fields, graph hashes and contact disjointness without project imports. It uses
a resource-wise interval sweep, whereas the constructor uses a pairwise
predicate. All 24 new graph edge sets match exactly, all 24 old graph objects
are unchanged, and the source blocks are disjoint. The receipt
`experiments/analysis/v06/c3_interval_inputs_check_v06_001.json` passed 147379
checks with zero errors. This is an independent implementation by the execution
agent, not a separate-person audit.

Six interval pairs have no added edge. The remaining six add 1, 2, 1, 2, 7 and
4 edges. These are input metadata, not evidence of preference reversal or
algorithmic gain. Graphs are not omitted or rescaled to force a stronger shift.
Optional performance inclusion must be declared before TEST launch, and all
such results must remain separate from fresh synthetic instances and the
natural weighted public benchmark populations.
