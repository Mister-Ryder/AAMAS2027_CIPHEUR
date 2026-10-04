# V07 public benchmark scenario audit

## Decision

The existing WDP and UAI/MMAP inputs are valid **public weighted graph
optimization benchmarks**, but they do not contain the fields needed for
the paper's satellite-resource reconfiguration experiment. They should
remain **secondary comparisons with classical/native MWIS methods** and,
where explicitly scoped, abstract representation diagnostics. They cannot
serve as the main evidence that a frozen programme adapts to changed
satellite–ground switching constraints.

For the next scene study, the main input role should move to **C6/W6 contact
windows under explicitly declared resource configurations**, subject to
the mechanism-applicability screening and deployment-boundary requirements.
That change is justified by source semantics, not the existing test scores.
It does not guarantee an information-conflict trigger or performance gain.
Existing registered public inputs, programmes and results remain unchanged.

This assessment reads pinned acquisition inventories, source README
metadata, bounded raw-file headers and the conversion functions. It does
not run an optimizer, conditional oracle, experiment or full-matrix parser,
read TEST scores, or reproduce raw graphs in this report. SatNet candidate
assessment is owned separately and is not duplicated here.

## Original source semantics and fields

| Existing population | What the supplied input represents | Available fields | Missing for satellite adaptation |
|---|---|---|---|
| WDP, 50 `.grf` files | Bid-compatibility graphs for combinatorial-auction winner determination; supplied as maximum-weight clique instances | Vertex IDs, bid-derived weights, undirected edges | Contacts, stations/satellites, time windows, switching parameters, future contact periods; original bid bundles are not in these graph files |
| UAI/MMAP, 81 `.mwvc` files | UAI2014 MAP/WCSP constraint-composite graphs, supplied for minimum-weight vertex cover / equivalent MWIS | Vertex IDs, rational weights, undirected edges | Contact/resource/time/gap metadata, original graphical-model factor tables and a scheduling reconfiguration process |
| `UAI_Grids_CHILS64` | An exact-encoding support track for selected **UAI Grids** inputs | The same UAI graph fields | It is not an independent physical dataset or the CHILS paper's application corpus |

The author-maintained repository identifies itself as accompanying
McCreesh, Prosser, Simpson and Trimble's *On Maximum Weight Clique
Algorithms, and How They Are Evaluated*, CP2017, pp.206–225. The formal
paper discusses application-derived benchmark families and the effect of
weight construction on heuristic comparisons; it is not a satellite-data
source. [Published CP2017 chapter](https://link.springer.com/chapter/10.1007/978-3-319-66158-2_14).

The pinned WDP README attributes the underlying winner-determination
instances to Lau and Goh's ICTAI2002 logistics-brokering work. It explains
that original three-decimal bids were multiplied by 1,000 using exact
decimal arithmetic and that vertices were permuted. Thus these weights
are bid-derived values, not link durations. Our archived README byte
identity is retained; no original bid table is reconstructed here.
[Pinned author WDP provenance](https://raw.githubusercontent.com/jamestrimble/max-weight-clique-instances/a0fd6b631136255807a98727b496a09a65b3301d/WDP/README.md).

The pinned UAI README explicitly describes conversion from UAI2014 MAP
problems to weighted CSPs and then constraint-composite graphs. It cites
Xu, Koenig and Kumar's formally published *A Constraint Composite
Graph-Based ILP Encoding of the Boolean Weighted CSP*, CP2017,
pp.630–638, DOI10.1007/978-3-319-66158-2_40. The original graph is intended
for MWVC; maximizing an independent set on its unchanged edges is
equivalent by `minimum cover weight = total vertex weight - maximum
independent-set weight`. The repository's general README also explicitly
distinguishes UAI as MWIS instances.
[Pinned author UAI provenance](https://raw.githubusercontent.com/jamestrimble/max-weight-clique-instances/a0fd6b631136255807a98727b496a09a65b3301d/UAI/README.md),
[Springer CP2017 contents verifying the formal paper](https://link.springer.com/book/10.1007/978-3-319-66158-2?page=3).

## Actual local source trace and bounded samples

Both acquisitions pin
`jamestrimble/max-weight-clique-instances` commit
`a0fd6b631136255807a98727b496a09a65b3301d` before optimization.
Their immutable raw archives are:

| Archive | SHA-256 |
|---|---|
| `experiments/runs/v06/wdp_inputs_v06_001.tar.gz` | `b47996fd674af7d4a1c2543c628b0d51f204d6c66f8bbd74687d3148a9f67c06` |
| `experiments/runs/v06/uai_mmap_inputs_v06_001.tar.gz` | `4c9d8decb20d771f581dbbbee825408a42baa36eab353fb80f3991af47bb0940` |

The WDP archive holds all 50 graphs and its provenance README; the UAI
archive holds all 81 declared MMAP graph files. Stored acquisition
inventories give WDP sizes 500–1,500 vertices across five families
(`1xx`, `2xx`, `4xx`, `5xx`, `6xx`), and UAI sizes 832–25,341 across
Grids, Promedas, ProteinFolding and Segmentation. These are input inventory
facts, not quality measurements.

Bounded samples inspected only the first twenty lines of:

- `wdp_inputs_v06_001/WDP/wdp-instances/in101.grf`: graph header has
  1,000 vertices and 155,734 edges; raw SHA-256
  `0df1193b19de9bba0c5b25e868144b0a5d3e99e3c0799f433155c4975314e48f`.
- `uai_mmap_v06_001/UAI/MMAP/Grids_18.mwvc`: graph header has
  6,412 vertices and 8,012 edges; raw SHA-256
  `79e15c67346a10d350d41724bca61e9a14fcd75e3c3e2e9209441205372e22f4`.

The declared text format is graph header `p edge/edges <n> <m>`, vertex
weight `n <integer ID> <numeric weight>`, and edge `e <ID> <ID>`.
The samples show graph headers and numeric vertex rows; the pinned parser
accepts comments plus these graph row kinds and rejects other data rows.
The stored successful acquisition parsing and author format specification
support the absence of separate physical contact fields. No adjacency
matrix, contact-level row or original weight list is copied into this note.

Acquisition uses `Fraction` on raw weight strings. WDP graphs retain
integer bid-derived weights. UAI retains exact rational weights, with
explicit exact scale/range compatibility where native solvers require
integers. Stored inventories report zero WDP files satisfying the
conservative signed32 total condition and six of 81 UAI files satisfying
it; incompatibility is not permission to round weights. The signed64
CHILS support track is an encoding limitation distinction, not a new
operational resource scenario.

## Our conversion is mathematical, not physical reconstruction

`scripts/run_classic_public_train_v06.py::raw_graph` parses exact weights
and authoritative source edges. For WDP, it creates the exact simple
undirected complement, preserving vertices and weights, so a maximum
clique becomes an MWIS on incompatibility edges. For UAI it keeps the
original conflict edges. The later performance input binding reuses this
orientation and its exact weight-scale rules.

To fit the common graph API, the converter assigns each public vertex a
constructed `public_sat_<vertex>` and `public_ground_<vertex>` carrier,
with start/end **0/1**. Its provenance explicitly sets
`contact_attributes_are_carrier_only=true`. These distinct carriers and
equal times neither generate nor explain the authoritative edges. They
cannot be used as observations of satellite/resource availability,
durations or switching costs. In particular, interpreting a fabricated
one-unit duration as a real contact workload would change the scientific
meaning of the input.

The older public DIMACS/SATLIB converter is similarly explicit: DIMACS
clique graphs are complemented; SATLIB CNFs are reduced to literal
occurrence conflicts. Unit or hash weights are labelled original
unweighted / constructed weighted views. Their common Contact fields
are carriers too. A seeded induced subgraph or hash-weight extension can
be a declared abstract diagnostic, but is not a natural time window or
operational constraint intervention.

## CHILS is a solver; its formal application corpus is different

The published SEA2025 CHILS paper studies a general weighted graph solver.
Its formal main application dataset contains **37 vehicle-routing
instances**, with route conflicts from shared drivers or loads and supplied
warm-start/clique information. Its reported main corpus is not our WDP or
UAI input collection. Our use of the released solver on public weighted
graphs is a solver comparison, not reproduction of that entire published
dataset or its experimental conditions.
[Formal SEA2025 CHILS paper, Dataset section](https://drops.dagstuhl.de/storage/00lipics/lipics-vol338-sea2025/html/LIPIcs.SEA.2025.22/LIPIcs.SEA.2025.22.html).

In current code, `UAI_Grids_CHILS64` is assigned to ten registered UAI
Grids source graphs meeting the exact signed64 condition but not the
common signed32 condition. The suffix indicates native encoding/solver
support. It must not be described as an additional CHILS source corpus or
as a satellite-ground dataset. This clarification is based on source
binding code, without opening any performance-result rows.

## What interventions these inputs can and cannot support

A source graph supports valid conditional MWIS values and representation
conflicts at explicit F/X boundaries. Therefore it remains useful for
abstract algorithm and information-interface questions. It does not
identify why an edge exists physically or how that edge should change
under a station-gap intervention.

For WDP, original goods/bundle/capacity data could support a separately
defined auction intervention, if those original fields were obtained and
validated. The supplied `.grf` lacks that mapping. For UAI, original
factor/variable/constraint data could support a separately specified
inference intervention, but the supplied converted graph is insufficient
to reconstruct it uniquely. Neither is a satellite intervention.

Consequently, arbitrary edge addition/deletion, vertex reweighting, or
attaching a gap coordinate to these graphs must not be presented as a
same-opportunity physical counterfactual. Such edits would be a new
synthetic graph perturbation study with its own scope. Increasing public
graph size does not repair this missing provenance.

## Revised role in the next research frame

1. **Main scene:** C6/W6 original contact-window opportunities under the
   exact chosen resource predicate and declared switching configurations.
   Keep real duration rewards and resources unless a separately labelled
   availability-derived workload is explicitly introduced. Whole-window
   provenance and exact decision boundaries must precede labels.
2. **Core applicability:** TRAIN-only structural/alias/path screening, then
   sound scoped evidence in a separately frozen study. Retain no-trigger
   windows. Physical data having the right fields is necessary but does
   not prove that the representation mechanism helps there.
3. **Secondary public comparison:** Preserve original public graph
   orientations/weights and all native support/failure coverage, with
   published baseline citations and shared declared budgets. This
   measures graph optimization performance; it cannot substitute for the
   main adaptation mechanism or establish a physical deployment claim.

The small companion metadata is
[public_benchmark_scenario_metadata_001.json](../experiments/analysis/v07/public_benchmark_scenario_metadata_001.json),
SHA-256 `8ae17b9c5c8b32769f8bd193e43e349f6a067addbcddb4dc5a8ae790baf6982e`.
It binds both raw archives, sample identities, pinned README Git blobs,
acquisition protocols and the conversion-source bytes. It records field
absence, transformation scope and recommended roles; it contains no
optimizer result or copied raw graph. No frozen study or paper file was
changed in this assessment.
