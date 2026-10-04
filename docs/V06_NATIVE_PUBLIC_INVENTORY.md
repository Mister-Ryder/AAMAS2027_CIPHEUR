# V06 native-solver and weighted-public inventory (no new optimization runs)

This read-only inventory supports a later registered V06 server experiment. It
does not select programmes, query a TEST oracle, run a solver, or select a
benchmark based on observed quality. V06 TRAIN selection and the evaluation
protocol must be frozen before any new TEST optimization.

## Reusable server solvers

The existing server installation and executable hashes match
`configs/advanced_public_v04_remote.json`:

| Method | Existing executable | SHA256 |
|---|---|---|
| CHILS | `/root/autodl-tmp/aamas2027_v03/baselines/CHILS/CHILS` | `19610c03f334c6267f94543ad3053d792cba56e9ae211fceb6c36f21750c88a0` |
| M2WIS | `/root/autodl-tmp/aamas2027_v03/baselines/KaMIS_v32/mmwis/build/mmwis` | `2238c64a6552fa4e21bd8c340e09475c187f26a49b43f41c4cda152b04316967` |
| Struction | `/root/autodl-tmp/aamas2027_v03/baselines/KaMIS_v32/mmwis/build/extern/struction/branch_reduce_convergence` | `84ccdd9bfd1fac5ae3e5c83037a72898207c408a11251971b4bf3617a2d5b46f` |
| WeightedBR | `/root/autodl-tmp/aamas2027_v03/baselines/KaMIS_v32/build/wmis/branch_reduce` | `8be531bea571585e0f582a13f9494ea68f24375c1c140309ab35c7a9afc0b73c` |

The reusable callable is `cipheur.advanced_baselines.run_solver`, taking graph,
executable, method name, `seconds`, seed, and a separate hard-wall safeguard.
The four CLIs accept floating-point time targets. CHILS uses `-t`; the KaMIS
executables use `--time_limit`. M2WIS also receives the same evolutionary and
ILS time target. The wrapper records end-to-end wall time, child CPU time,
return status, executable/input hashes, and schedule feasibility. It sets
OpenMP and numerical-library thread counts to one. No extra native build is
needed.

The original `advanced_study_v04.validate_config` enforces the original
five-second protocol, so it must not be repurposed or edited for a new
multi-budget protocol. A new V06 runner should call the stable native wrapper
directly. Targets such as 0.01/0.05/0.1/1/5 seconds can be registered uniformly
as wall limits. Native clocks are wall based (`omp_get_wtime` in CHILS and
`gettimeofday` in the KaHIP timer used by KaMIS). Startup/input preparation and
initial feature work must be explicitly accounted for. Equal wall targets
compare the actual deployments; they do not establish equal CPU work or erase
the C++ native versus Python implementation difference.

The exact integer METIS encoding currently requires a positive integral scale
whose total encoded weight fits the conservative signed-32-bit limit. A new
public-input inventory should record weight type, denominator, positivity,
total scale and every encoding failure before freezing the final population.
It must not silently round real weights or discard a case after seeing its
solver result. Missing outputs and timeouts remain explicit failures.

## New weighted-public source metadata

The author repository accompanying the published CP 2017 paper provides
weighted benchmark families. Its README explicitly states that the UAI family
is maximum-weight independent set, whereas the other benchmark graphs are
maximum-weight clique. Thus UAI edges should be used directly as conflict
edges; other families require a declared complement transformation for MWIS.
Sources: [author repository](https://github.com/jamestrimble/max-weight-clique-instances),
[published paper record](https://eprints.gla.ac.uk/143720/),
[official CP 2017 accepted papers](https://cp2017.a4cp.org/accepted_papers.html).

The [pinned UAI source README](https://raw.githubusercontent.com/jamestrimble/max-weight-clique-instances/a0fd6b631136255807a98727b496a09a65b3301d/UAI/README.md)
further identifies these as constraint composite graphs of WCSP conversions
from the UAI Competition 2014 PR/MMAP instances, with published CP 2017 and
CPAIOR 2017 provenance. Its instruction to compute maximum weighted clique
on the complement is consistent with directly computing MWIS on the supplied
graph. No complement should be applied to the UAI edges in this project's
conflict-graph interface.

Only GitHub commit/tree metadata was retrieved. No benchmark graph bytes were
downloaded and no benchmark outcome was computed. The pinned commit is
`a0fd6b631136255807a98727b496a09a65b3301d`. The non-truncated tree has 774 files
and 2,006,361,586 total blob bytes. Full cloning is unnecessary.

| Top-level family | Files (including metadata/helpers) | Total blob bytes |
|---|---:|---:|
| DIMACS | 161 | 543,472,212 |
| REF | 130 | 124,832,978 |
| UAI | 161 | 192,631,291 |
| WDP | 51 | 45,017,977 |
| Error-correcting codes | 33 | 93,672,930 |
| Graph colouring | 1 | 87 |
| Kidney exchange | 235 | 1,006,732,830 |

UAI includes 81 MMAP `.mwvc` graph files (11,266,187 bytes), 79 PR `.mwvc`
graph files (181,363,499 bytes), and one README. The MMAP set is a manageable
candidate for a genuinely weighted, previously unused input family: filenames
include `Grids`, `Promedas`, and other inference instances. The native MWIS
orientation comes from the author README, not the `.mwvc` suffix. Vertex and
edge counts, integer/real weight validity, and native encoding compatibility
are not inferable from the repository tree; those remain to be inventoried
from pinned raw bytes under an outcome-free source-selection protocol. There
has been no benchmark selection using a hidden difficulty or performance
measurement.

Earlier V04/V05 public studies used DIMACS and SATLIB with unit or constructed
hash weights. They did not use these UAI files. This distinguishes a new
natural weighted source from reweighting those old public graphs. It does not
automatically make an arbitrarily chosen subset representative or prove a
method's advantage.

The downloaded metadata file is
`experiments/discovery/v06_public_metadata_001/inventory.json`, SHA256
`7ce0455066e5b542f0865913602472b6dc3c9b355cf1b66fe95fd844a1ebc522`.
The cloud metadata directory is
`/root/autodl-tmp/aamas2027_v06_public_metadata_001`. GitHub tree `sha` values
inside the file are Git blob SHA1 identifiers, not raw-content SHA256 values.
Raw files must be hashed separately if they are later admitted to a registered
benchmark population.
