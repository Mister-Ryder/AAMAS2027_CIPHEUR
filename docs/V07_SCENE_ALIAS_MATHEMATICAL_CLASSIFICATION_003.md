# V07 natural TRAIN aliases: exact symmetry classification

All **556 prescribed exact-full-base-nine aliased pairs** from the 48 C6/W6 TRAIN graphs were classified, with **zero failed windows**. Four pairs are equal-weight adjacent true twins, zero are nonadjacent open twins, and **552 are non-twins**. The four true twins have explicit transposition-automorphism proofs of equal conditional inclusion optima at the declared empty boundary. The other 552 pairs have no such proof; they are not thereby strict conflicts or successful information-repair examples.

This is an input-only mathematical pass. No optimizer, conditional oracle, LLM, candidate quality assessment or held-out graph/label was used. The previous `contact_scene_screen_v07_002` source, protocol, census and receipts remain unchanged. Full adjacency was not cached by that census, so this new registered pass rebuilt the same 48 TRAIN graphs once and checked each graph digest and aliased-pair count against the original frozen census.

## Exact proof and limits

For actions `a,b` in an undirected graph with equal weights, if

`N(a) \ {b} = N(b) \ {a}`,

the permutation swapping `a` and `b` and fixing every other vertex preserves all graph edges and weights. It maps every independent set containing `a` to an equal-weight independent set containing `b`, and conversely. At the **same empty fixed/excluded boundary**, both actions are available and their conditional completion values are exactly equal. Therefore their forced-inclusion value difference is zero even when the MWIS value itself is unknown.

Adjacency distinguishes true twins from open twins. Adjacent twins cannot both be selected, while open twins can; the swap proof of equal separate forced-inclusion values holds in either case. The output records the equal-weight condition, equality of both outside-neighbor sets, adjacency, graph digest, action row hashes and explicit boundary. It records `forced_inclusion_value_difference_exact="0"` only with this proof schema. This is a mathematical symmetry proof, not an oracle result or an invented exact optimum.

The proof concerns the unmarked weighted MWIS graph, whose edges enforce feasibility. It does not require resource labels or edge-reason masks to be preserved. In these four actual twin pairs the edge-reason masks also happen to be preserved. A different boundary can break a swap symmetry when commitments or exclusions distinguish the actions; this pass asserts only the declared empty boundary. A non-twin pair may still be symmetric under a more complex automorphism or have equal conditional optima without any automorphism.

## Complete census

| Source / ground gap | Assigned aliased pairs | Adjacent true twins | Open twins | Non-twins | Weighted unmarked WL1 separates | Weighted unmarked WL2 separates |
|---|---:|---:|---:|---:|---:|---:|
| C6 / 340 | 126 | 0 | 0 | 126 | 125 | 126 |
| C6 / 680 | 112 | 2 | 0 | 110 | 108 | 108 |
| W6 / 340 | 164 | 0 | 0 | 164 | 164 | 164 |
| W6 / 680 | 154 | 2 | 0 | 152 | 152 | 152 |
| All configuration occurrences | **556** | **4** | **0** | **552** | **549** | **550** |

There are 531 distinct `(source,window,action-pair)` identities in the union of the two gap configurations. Of these, 25 are full-base-nine aliases at both configurations, 265 only at 340, and 241 only at 680. These are not independent instances: repeated configurations share source contacts and source-window identity. All 24 windows and all 48 graphs remain represented, including any zero-alias graph; none was filtered by the mathematical outcome.

For these 531 pairs the simple twin status is non-twin at both configurations for 527, and non-twin at 340 to adjacent true twin at 680 for four. A pair not aliased in the other configuration is retained explicitly with `base9_alias=false`. Changing configuration can alter whether a pair is structurally interchangeable; no preference reversal follows from these status changes.

## Fixed richer structural discrimination

The pass uses two predetermined exact color-refinement rounds, with initial colors `(original weight,original duration)`. The new color is the tuple of the old root color and the exact multiset of neighbor colors. One variant ignores edge reasons; the other includes the inherited ground/satellite/both reason mask. Tuple interning uses exact tuple equality, not rounded numeric values or cryptographic hash equivalence. It runs exactly two rounds for all graphs, not until a desired distinction appears.

The marked and unmarked variants happen to separate the same numbers here: 549 pairs after one round and 550 after two. All four twin pairs remain indistinguishable. Two non-twin pairs also remain indistinguishable after the two rounds. A changed color establishes a richer observable structural/weight distinction between those roots. Equal colors do not prove rooted isomorphism, and differing colors do not prove different conditional values. These refinements are diagnostic structure encodings; they are not additions to the frozen typed operation library or a deployable ranking rule.

In particular, this result should not be stated as “550 information conflicts” or “552 profitable refinements.” The original complete base-nine vectors coincide, but preferences have not been certified. For a strict same-boundary preference at an aliased pair, the exact quotient would have a self-loop under that interface; the input-only pass has not acquired the strict demand needed for that conclusion.

## Execution and retained evidence

New classifier: `scripts/classify_scene_aliases_v07.py`.

Namespace: `experiments/discovery/scene_alias_classification_v07_003/`.

- `protocol.json` fixes all 48 graphs, all 556 alias assignments, boundary, proof and WL definitions before graph reconstruction.
- `source_capsule.zip` binds the classifier and the unchanged prior census/source/input receipts. Raw CSVs are not copied.
- `freeze_receipt.json` and `execution_receipt.json` bind preparation and execution.
- `window_classifications.jsonl` preserves every window's result.
- `classification_summary.json` contains all graph pair rows and 531 cross-configuration records, including action/source-window identity hashes and other-side non-alias status.
- `completion_receipt.json` records 48 completed graphs, 556 classified pair occurrences and zero failures.

The eight-worker execution took 9.0634 seconds from the new execution-receipt creation through result aggregation. This is graph/input classification time, not a scheduling timing result.

| Artifact | SHA-256 |
|---|---|
| Classifier source | `56a0d567c167ec2a3610487ad76407942dfaeb2cb92d2b983a05a37b125c0148` |
| New protocol | `9474c7f8b34c07092dd9c135cf20063dbc76fbb9a230a756a048f38ff1398194` |
| New freeze receipt | `9fa1d7caaf8b5d9052abc823a36477bb2e684ed8f1787144f50f2909ee22f0c3` |
| New source capsule | `20a6ff92b25c9d0521762883c5959f2fd37ea8d1032ee75647b362fec17ee14e` |
| Classification summary | `4b71e538fbdaa1a8c4fb8e32035403c30bba4f7f14a7c0e635e846114c4104d7` |
| Completion receipt | `9d8d4fd60d0c212123c3ed485e3aabfebfe11a85442d822065e92df4b9b35391` |

## Mathematical dataset decision available now

Natural exact aliases in these duration-weighted TRAIN scenes are mostly not explained by the simplest equal-weight transposition symmetry, and a richer fixed structural encoding usually separates them. That establishes a nontrivial input-identifiability question. It still does not establish strict decision information conflicts, their configuration-dependent persistence/reversal, recurrence on later windows or complete-schedule benefits.

Root may next predeclare sound bounded TRAIN conditional queries for the entire remaining inventory or a fixed hash-sampled inventory with explicit assigned denominators. The graph components are large, so closure may be unavailable; unknown labels must remain unknown. Do not query only WL-separated or favorable-looking pairs, or treat complex-automorphism/tie possibilities as disproved. No such query or optimization is authorized or executed by this pass.
