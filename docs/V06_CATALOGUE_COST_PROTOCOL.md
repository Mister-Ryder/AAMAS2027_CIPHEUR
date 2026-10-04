# V06 fixed-catalogue additive-cost experiment

Registered 2026-10-04 UTC+08:00, before any new TRAIN feature values, feature
costs or refinement/master outcomes were computed. Root reviewed the frozen
protocol/source inventory and authorized an independent server execution.
The server execution is delegated to the effect agent because persistent tool
sessions are agent-scoped. **No actual study feature measurement/master was
executed locally, and no server action was performed by this agent.** No R2
response, assessment or TEST output was read.

## Scientific scope

The experiment substantiates the scoped finite-catalogue theorem on the original
594 strict TRAIN requirements. It asks whether repeated full-quotient
separation attains a minimum **positive additive standalone operation cost**
within a fixed typed-expression catalogue and at most six additions. It does
not optimize deployment runtime, shared computation, an unrestricted feature
space, a bounded scalar rule, schedule quality or unseen data.

The catalogue is the union of canonical typed expressions from **all 112
statically valid positions among all 120 R1 raw positions**, including ineligible
candidates. Eight invalid response positions remain in the metadata inventory.
Feature names and rationales are excluded from expression identity; compiled
expression dictionaries are encoded as compact UTF-8 JSON with sorted keys.
No algebraic simplification or semantic deduplication is performed. The 53
distinct expressions are ordered by SHA-256. Eligibility, fit, quality and
cost are not used to choose a catalogue prefix. No known winner or seed feature
set is forcibly inserted.

This is an **R1-adaptive catalogue on previously observed TRAIN evidence**, not
a blind algorithm comparison or independent LLM authoring study. Its outputs
are excluded from R2 author packets, gates and selectors. The frozen library
contains 25 operations; no library or production source was changed.

| Registered catalogue | Size | Subsets with size ≤6 | Independent exhaustive check |
|---|---:|---:|---|
| SHA prefix 4 | 4 | 16 | Yes |
| SHA prefix 8 | 8 | 247 | Yes |
| SHA prefix 16 | 16 | 14,893 | Yes |
| Full union | 53 | 26,144,848 | No; bounded independent cut-master DP |

All versions use base9 and the same full 594-requirement frame from the 120
original TRAIN snapshots, with explicit F/X. Repeated endpoints in a state are
deduplicated; endpoints in different states remain distinct. This yields **864
unique certified `(state,node)` occurrences**. Feature values/costs are measured
at every such occurrence, including states beyond a displayed witness. The
measurement is not over every vertex or over uncertified queries. Original
labels and their exact sign orientation are replay-validated; no conditional
oracle is called.

## Cost, budgets and failures

For each expression independently, each occurrence receives a fresh frozen
`_FeatureState`; there is no cache shared across roots or expressions. The
declared cost is `max(1, sum(feature_work))`, a positive integer operation proxy.
Static parsing, graph construction and shared base9 overhead are excluded from
that additive objective and reported separately through actual CPU/wall/setup
fields. These standalone costs do not equal shared-DAG deployment work.

Before measurements, per-expression caps were fixed at 100,000,000 charged
feature units and 60 CPU seconds. All 53 expressions plus base9 are assigned.
An incomplete/nonfinite expression retains its partial values and failure row;
every planned catalogue containing it is unresolved. It is never silently
removed or substituted. Worker input construction is shared setup, and process
startup/import/batch overhead belongs to the external execution receipt.

The unchanged `minimum_cost_vector_refinement` uses **K=6**, at most **128
separation rounds**, and **250,000 cumulative master subsets** per catalogue.
It rechecks the complete quotient after each master solution. Budget stops
remain `optimal=False`, even if independent enumeration later finds a repair.
No unknown result is relabelled as an attained minimum. Inseparable-witness and
cardinality-infeasibility reasons remain explicit in the production result.

Independent verification uses a separate exact-numeric Kahn quotient checker,
checks each concrete strict arc, cyclic equality join and separating-feature
cut, and recounts selected additive costs. A memoized dynamic program over
uncovered witness-bitmasks and remaining feature count crosschecks master costs,
with 250,000 states shared across all rounds of one catalogue. Prefixes of at
most 16 additionally enumerate every subset of size ≤6, soundly skipping
quotient evaluation when exact cost/tie order already makes a subset dominated.
The final independent-minimum flag requires a production-resolved DAG and a
completed independent cost proof. Production optimality, independent proof
coverage, and assignment completion are separate fields.

## Runnable frozen package

Runner: `scripts/run_catalogue_refinement_v06.py`.
Study: `experiments/discovery/v06_catalogue_cost_001`.
The source ZIP has 12 safe relative file members with individually verified
hashes: six dependency sources, the runner and five registered study files.
It contains no authentication configuration. Size: **456,187 bytes**.

Preparation, already completed without evaluation:

```powershell
.venv/Scripts/python.exe scripts/run_catalogue_refinement_v06.py prepare --study experiments/discovery/v06_catalogue_cost_001
.venv/Scripts/python.exe -m unittest tests.test_catalogue_refinement_v06 -v
```

Preparation requires a new directory. The six tiny tests passed in 0.028
seconds: metadata-only union/deduplication, 30 randomized weighted/cardinality
DP-versus-exhaustive crosschecks, exact integer/binary-float equality, multiple
surviving cycles/full-quotient repair, budget-unknown retention and positive
standalone costs/failure recording on a two-node toy graph. They are unit
checks; no actual TRAIN feature values or masters were executed.

Authorized server phase, after safe extraction into the unique directory
`/root/autodl-tmp/aamas2027_v06_catalogue_cost_001`:

```bash
/root/autodl-tmp/aamas2027_v03/py311/bin/python scripts/run_catalogue_refinement_v06.py execute --study study --out results --workers 8
```

The runner checks every registered source/input byte before work and refuses an
existing output directory. It writes all 54 feature assignment rows,
four catalogue result rows, progress, execution and completion receipts. A
completion receipt describes returned assignments, **not universal solver
success**. Detached launch/host cgroup/CPU/wall accounting and a 7,200-second
outer guard can be recorded separately; partial outputs remain if the guard
fires. No TEST or online policy/LLM call is made. Archives stay below 100 MB.

| Frozen artifact | SHA-256 |
|---|---|
| Runner | `84a84ee8fa4e501510f4ab8e3b7df647b7f095567d4457d07c1e37e4878af131` |
| Protocol | `b0e9949454d0b4f6bc0516e5b9fdce27b660cc7e4417e766549e48b33c9851ca` |
| Source ZIP | `2c19af4c639926e457b9bcdbf5c2eb5dd9b23c23055af748da5217003c7a64f6` |

Results/analysis remain pending. Planned reporting retains all four catalogues:
feature completion, remaining full-quotient cycles/self-loops, selected feature
count, exact standalone cost, rounds/cuts, evaluated master subsets, quotient
evaluations, independent proof coverage and measured CPU/wall. A favourable
cost outcome would support only the declared finite-catalogue additive claim;
negative or unresolved prefixes are equally retained.
