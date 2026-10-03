# Outcome-free sparse public graph extension

This extension was specified separately from the original frozen DIMACS/SATLIB challenge protocol. It adds four official SNAP source graphs and two weight modes per graph, for eight requested algorithmic transfer contexts. Sources and conversion policy were fixed before this author accessed any current fresh scheduling/public quality results. No programme, threshold or solver was changed, and preparation made zero solver calls. This is a separate exploratory extension, not a claim that these graphs belonged to the original 96-context protocol.

## Sources and prepared graph sizes

The official pages establish the dataset identities and original reported sizes. Actual converted counts below were independently parsed from the saved compressed files; the difference in collaboration edge counts is exactly the explicit self-loop projection.

| Source | Observed vertices retained | Raw edge rows | Self-loop arcs removed | Simple undirected edges |
|---|---:|---:|---:|---:|
| [ca-GrQc](https://snap.stanford.edu/data/ca-GrQc.html) | 5,242 | 28,980 | 12 | 14,484 |
| [ca-HepTh](https://snap.stanford.edu/data/ca-HepTh.html) | 9,877 | 51,971 | 25 | 25,973 |
| [Facebook combined](https://snap.stanford.edu/data/ego-Facebook.html) | 4,039 | 88,234 | 0 | 88,234 |
| [ca-HepPh](https://snap.stanford.edu/data/ca-HepPh.html) | 12,008 | 237,010 | 32 | 118,489 |

All four observed vertex counts match the official declared counts and the raw headers where available. No isolated vertex identity was inferred from a contiguous ID range. A count mismatch would have made that source unavailable with its metadata preserved and no substitute graph. The official ca-GrQc, ca-HepTh and ca-HepPh edge totals include their self-links; their raw exports also contain reverse directions. Raw row counts therefore differ from canonical unordered edge counts and both remain in the receipts. The Facebook file has no node/edge header; its endpoint count is checked against the separately declared official page size.

## Explicit simple-network projection

The benchmark is the declared **simple undirected projection** of each source network. It keeps every observed integer vertex ID, replaces either directed ordering by its unordered pair, deduplicates repeated/reverse rows, and discards self-loop arcs while retaining their vertices. It does not complement the graph. These source networks are not interpreted as physical scheduling predicates. A coauthor self-link is not automatically a scheduling exclusion conflict.

Dropping self-loops changes independent-set eligibility compared with an original loop-conflict graph; **no preservation of that looped MWIS problem is claimed**. Every solver and programme sees exactly the same projected graph. Receipts retain the loop-bearing vertex IDs, raw loop rows, canonical loops removed, all original endpoint IDs, raw and unique ordered arc counts, reverse/duplicate counts, and pre/post projection edges and vertices. No vertex is deleted. A vertex observed only in a self-loop would become an explicitly observed isolate, not an invented identity.

The parser independently rebuilds the projected edge set from original rows and checks every endpoint. Graph construction uses canonical string forms of original integer IDs, then rechecks its edge set and total degree against the parsed set. `Graph.from_dict` identity roundtrips are tested. Self-loop rejection remains a supported parser mode for other contracts, but this fixed extension prespecifies explicit simple projection for all four sources.

## Weight modes and experimental scope

Unit weights preserve the declared simple-graph independent-set objective. The second mode is an explicitly labelled weighted extension, using the same SHA25620261003 rule as the earlier public input generator:

`w(v) = 1 + int(SHA256("20261003:" + dataset_name + ":" + original_integer_ID),16) % 20`.

Weights depend on the original ID, not its position after parsing or a solver output. Both modes share the same source vertices/edges and source cluster. There are four independent source graphs, not eight independent network samples. Dummy contacts provide the existing graph schema; they carry no satellite-physics claim. These graphs broaden algorithmic size and sparsity coverage beyond the earlier challenge inputs, rather than establish scheduling-domain generalization.

Root will declare a separate saved-input advanced-run config for all eight contexts, with the existing frozen programmes and official native solver protocol. No long-budget subset is needed for this extension. The planned server allocation is four graph workers within the 16-CPU quota. Native failure and soft-budget overshoot accounting remain the advanced runner's explicit protocol. Preparation has not run or inspected those comparisons.

## Immutable source receipts and files

Preparation command:

```text
python -m cipheur.snap_benchmarks_v04 --config configs/public_sparse_v04.json --output .research/public_sparse_v04_001 --archive .research/public_sparse_v04_001.tar.gz
```

The directory contains exact raw compressed files, `data.json` in the existing `public` schema, original config, a pre-fetch protocol timestamp/config hash, complete source/conversion receipts, a pinned source config, and completion/availability receipts. Each raw compressed file and decompressed payload has SHA256; gzip decompression checks integrity. Re-preparation from the pinned config rejects changed raw content. Existing output/archive paths are preserved rather than overwritten.

| Raw source | SHA256 of exact downloaded gzip bytes |
|---|---|
| ca-GrQc | `a254442cdf5d684712578b630c2e0d7543518ab154ef2341cabb607572ce7230` |
| ca-HepTh | `7235c7e11887f8a32dfd03a3aa0c77efdf89d41591a959c7d6e4ca11b1299bb5` |
| facebook_combined | `125e84db872eeba443d270c70315c256b0af43a502fcfe51f50621166ad035d7` |
| ca-HepPh | `8d679f64ea507834613f4c09e6f692cc8a2405d5a01bfe1ee3b24fbbea1d807f` |

Prepared `data.json` SHA256 is `7afb9d7451ae71ff99833b15cd6ce53f46b9736870483086fe4508c15153ff41`.
Preparation module SHA256 is `77a5de6b1502dfbb64545f0ad5df7b92ca2770fc65f02533670925158c62f502`.
The gzip archive is 3,999,668 bytes. These receipts identify input preparation, not successful optimization or scientific superiority.

Three tests passed: exact shadow/multiplicity accounting with explicit changed loop semantics checked by independent subset enumeration; malformed/count-mismatched inputs without invented isolates; and stable original-ID weight calculation plus graph/source edge identity roundtrip. No current quality outcome was consulted during source choice, conversion, weighting or verification.
