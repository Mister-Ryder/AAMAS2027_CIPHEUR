# V06 pinned weighted-public input acquisition

This is an input/provenance report, not an experimental quality table. No
optimization, candidate evaluation, or TEST conditional-certificate query was
performed during acquisition. All declared raw cases and incompatibilities
are retained. The new authoring TRAIN corpus remains the previously frozen
public-induced/synthetic evidence input; these additional public sources do
not silently replace or enlarge that authoring input.

## UAI/MMAP: all 81 raw source instances

The [author benchmark repository](https://github.com/jamestrimble/max-weight-clique-instances)
accompanies the published [CP 2017 benchmark study](https://eprints.gla.ac.uk/143720/).
The [pinned UAI README](https://raw.githubusercontent.com/jamestrimble/max-weight-clique-instances/a0fd6b631136255807a98727b496a09a65b3301d/UAI/README.md)
identifies WCSP constraint-composite graphs derived from UAI Competition 2014
PR/MMAP instances, with CP 2017 and CPAIOR 2017 encoding provenance. The native
supplied graph is an MWIS conflict graph. No complement was applied.

Pinned commit: `a0fd6b631136255807a98727b496a09a65b3301d`. Before raw acquisition,
all 81 MMAP paths, Git blob SHA1 identifiers, byte sizes and a fixed source
split were saved in `experiments/discovery/uai_mmap_v06_001/protocol.json`,
SHA256 `cd4b45f3115118cac883294f532f4d229ad6b3f1c00d36aaead7d43545caa5c6`.
The immutable source capsule SHA256 is
`477ba535f1c3e224516f26c4165febe4d80dff7c14df612149583e4a8a5cbb21`.
The stdlib-only fetch/parser SHA256 is
`bff4c4fe601c364115514dba334acfbd23ea7f87ba0c5220b4d851c472b9d330`.

All 81 downloads completed with exact pinned Git blob/byte identity and valid
DIMACS parsing. Their 11,266,187 raw bytes were preserved without rewriting.
Acquisition and metadata parsing took 139.103 seconds on the cloud host,
in a persistent detached process (PID 49756). Raw archive:
`experiments/runs/v06/uai_mmap_inputs_v06_001.tar.gz`, SHA256
`4c9d8decb20d771f581dbbbee825408a42baa36eab353fb80f3991af47bb0940`.
Full input/encoding inventory:
`experiments/analysis/v06/uai_mmap_inventory_v06_001.json`, SHA256
`d1ba42377fb00e25e8ad5e91815406172f150f6481b7c9203c60b30eb113bd7f`.

| Source family | Total | Reserved TRAIN | Reserved TEST | Vertex range |
|---|---:|---:|---:|---:|
| Grids | 13 | 3 | 10 | 1,552–25,341 |
| Promedas | 61 | 33 | 28 | 1,954–9,282 |
| ProteinFolding | 1 | 1 | 0 | 1,552 |
| Segmentation | 6 | 3 | 3 | 832–882 |
| All | 81 | 40 | 41 | 832–25,341 |

Each original source-instance basename is one cluster. A fixed salted SHA256
order allocates the first 40 source clusters to TRAIN and the remaining 41 to
TEST; all future derived views and seeds must remain in their source cluster.
The split was not chosen by graph density, weight validity, encoding support
or quality. It is source-instance disjoint, not family disjoint; families and
related instances should remain visible in any later dependence analysis.
Reserved TRAIN membership does not imply these cases were actually used for
this round's authoring or selector.

### Exact-weight and native-solver boundary

All 81 files contain nonintegral weights. Raw weight strings were parsed as
exact `Fraction` values, without conversion through binary floating point.
There are no negative weights, zero weights, repeated edges or parse errors.
Unique edge counts range from 1,214 to 31,581. The smallest raw weight is
`739989/1000000000`; the largest is `1900000000000000000000`.

The predeclared native compatibility check takes the exact rational denominator
LCM and tests nonnegative integer weights with total at most `2^31−1`. Only
six cases satisfy that conservative implementation contract. Exact reduction
by the common integer GCD does not enlarge that signed32 supported set: 75 cases
remain unsupported under this original common contract. Those cases have not
been discarded or rounded and cannot be presented as successful comparisons
under a signed32 contract. After the separate CHILS64 source review, an
input-only check of the same immutable metadata finds 20 exact signed64-LCM
compatible inputs: the original six Segmentation cases, all 13 Grids cases and
ProteinFolding_11. Thus 14 additional cases are CHILS-specific encoding
possibilities, not successful optimization results. The original 81-source
inventory and six-case common-native boundary remain unchanged.

The supported cases are Segmentation 12, 13 and 16 in the reserved TRAIN split,
and Segmentation 14, 18 and 19 in TEST. All use exact denominator scale 100,000;
scaled total weights are approximately 2.88–3.23e8. If they are evaluated later,
construct graph weights directly as exact integers `Fraction(raw)*100000`,
record that scale, and convert reported objective values back by dividing by
100,000. Uniform positive scaling preserves the original MWIS problem. Do not
first parse raw decimals as floats and assume `Fraction(float)` reproduces the
decimal objective; it does not. Do not pass the other 75 raw fractional/huge
weights to a float graph interface and claim the original exact objective.

The six supported cases alone are a small family-specific set. They cannot
stand in for an all-81 natural weighted result, and their support status says
nothing about algorithmic performance. A separate weighted-public family is
being acquired under another pre-outcome input protocol to broaden the future
native comparison without changing this archived boundary report.

## WDP

The subsequent WDP acquisition is separately registered in
`experiments/discovery/wdp_inputs_v06_001/`. It includes all 50 `.grf` source
graphs plus the README, with a fixed 25/25 original-source SHA split and no
performance filtering. Source graphs are maximum-weight clique instances;
future MWIS evaluation must use the exact simple undirected complement while
preserving weights and vertices. No solver has been run on these inputs.
All 50 raw graphs and the README completed download and pinned Git blob/byte
verification. All graph files parsed as valid; there are no zero/negative
weights, duplicate edges or noninteger graph weights. Their 45,017,977 bytes
were preserved unchanged. Acquisition/metadata parsing took 234.714 seconds on
the cloud host in PID 50249, without any solver call. Archive:
`experiments/runs/v06/wdp_inputs_v06_001.tar.gz`, SHA256
`b47996fd674af7d4a1c2543c628b0d51f204d6c66f8bbd74687d3148a9f67c06`.
Full inventory: `experiments/analysis/v06/wdp_inventory_v06_001.json`, SHA256
`d7899055c070ea5fe9a066acb7d70b540fa6aadef162dfdbf0b080ae07d6521b`.
Pre-download protocol SHA256:
`3a469823d789bddd483b77288dc719e55476069ff0affb30c4be10e17542d76f`.
Source capsule SHA256:
`292b79689d488200d5931558f9d7edbc03a64958ef6e7c6f0e46c5b928c94c30`.

The [pinned WDP source README](https://raw.githubusercontent.com/jamestrimble/max-weight-clique-instances/a0fd6b631136255807a98727b496a09a65b3301d/WDP/README.md)
traces the graphs to Lau and Goh's published ICTAI 2002 winner-determination
instances. The repository contains ten instances from each of five families,
with permuted vertex IDs. The authors converted the original three-decimal
bids precisely to integer weights by multiplying by 1,000 using `BigDecimal`;
they explicitly identify small errors from float conversion in some earlier
reports. That provenance should be cited rather than pretending this project's
inventory introduced the weights.

Graph sizes range from 500 to 1,500 vertices. Source clique graphs have
17,142–155,734 edges; their exact MWIS complements have 103,044–1,045,022 edges.
Raw integer vertex weights range from 270,252 to 46,777,047. The largest total
vertex weight is 32,171,491,080. Every case exceeds the original conservative
signed-32-bit total-weight encoding contract, and common-GCD reduction does
not make any case satisfy it. This is a supported-input boundary, not a
measured solver failure or a low-quality baseline result.

A read-only source inspection found that the installed CHILS uses signed
`long long` for graph weights, graph parsing, solution cost, neighbor-weight
sums and local gains. WDP totals are within that width. A separately registered
V06 CHILS encoder can preserve these integer weights under a declared
signed-64-bit total contract, while leaving the old 32-bit helper unchanged.
The installed M2WIS and WeightedBR use unsigned-32-bit `NodeWeight` and weight
accumulators; the CHILS relaxation must not be applied universally to them.
No claim about a safe extended Struction path is made without checking its
actual source dependency chain. The source/compile-flag inventory is
`experiments/discovery/v06_native_width_001/inventory.json`, SHA256
`23af079a2ef8b37e922d8cf09288f18fb74f8a2716a379887db8cc0875cbe3661`.

For later evaluation, keep these scopes explicit: new synthetic quarter-weight
graphs fit the conservative old contract and permit the full existing native
suite; WDP exact weights can support a separately registered CHILS64
comparison, with other encoding limitations reported. Unsupported encoding
must not be converted to zero-quality scores to manufacture an algorithm or
LLM advantage. This acquisition phase establishes no such advantage.
