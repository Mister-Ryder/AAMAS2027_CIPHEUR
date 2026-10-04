# V06 actual authoring efficiency: frozen receipt presentation

This is a presentation of already audited R2 gate counts and original bank author-call wall receipts. It invokes no new audit, optimizer, oracle, programme evaluation or model call; no raw response or TEST is read. All five banks per arm remain. The preregistered first four matched banks are descriptive conditional cohorts, not independent model-population samples or equal-compute treatments.

## Actual bank records

Each call proposes eight original positions. Wall is measured once for the complete bank call; no candidate completion time is interpolated. Exact decimal receipt values are retained below.

| Arm | Block | Matched4 | Eligible/original | Actual author-call wall seconds |
|---|---:|---|---:|---:|
| W | 0 | True | 7/8 | 658.8961420059204 |
| W | 1 | True | 8/8 | 814.0406451225281 |
| W | 2 | True | 3/8 | 513.499519109726 |
| W | 3 | True | 8/8 | 567.1091294288635 |
| W | 4 | False | 2/8 | 370.60423731803894 |
| R | 0 | True | 4/8 | 542.3900632858276 |
| R | 1 | True | 4/8 | 549.9651789665222 |
| R | 2 | True | 3/8 | 878.8849830627441 |
| R | 3 | True | 8/8 | 829.6886672973633 |
| R | 4 | False | 5/8 | 431.41123151779175 |
| O | 0 | True | 0/8 | 351.4090859889984 |
| O | 1 | True | 0/8 | 370.63443899154663 |
| O | 2 | True | 0/8 | 436.1669805049896 |
| O | 3 | True | 0/8 | 528.0328106880188 |
| O | 4 | False | 0/8 | 533.9711647033691 |

## Exact-denominator throughput

Throughput = 1000 × eligible proposals / sum of actual call-wall seconds in the specified cohort. It counts genuine gate-eligible original proposals, not learned quality gain or fitted scalars. Decimal displays are rounded only here; the sidecar retains exact rational denominators and rates.

| Scope | Arm | Eligible/original | Cumulative call-wall seconds | Mean bank wall seconds | Eligible per 1000 cumulative call-wall seconds |
|---|---|---:|---:|---:|---:|
| matched4 | W | 26/32 | 2553.545435667038 | 638.386358916759 | 10.181921824002 |
| matched4 | R | 19/32 | 2800.928892612457 | 700.232223153114 | 6.783463889467 |
| matched4 | O | 0/32 | 1686.243316173553 | 421.560829043388 | 0.000000000000 |
| all5 | W | 28/40 | 2924.149672985077 | 584.829934597015 | 9.575433247716 |
| all5 | R | 24/40 | 3232.340124130249 | 646.468024826050 | 7.424961197875 |
| all5 | O | 0/40 | 2220.214480876923 | 444.042896175384 | 0.000000000000 |

## Suggested caption and limits

Eligible original proposals versus measured author-call wall in all five warm-repair banks. Filled circles show blocks0–3, hollow diamonds retain block4, and crosses mark preregistered matched-four bank means. Every bank proposes eight positions. Session wall is not candidate latency or concurrent elapsed time; these conditional descriptive ratios do not establish equal compute, served-model identity, scalar consistency or scheduling-quality superiority.

Requested model is gpt-6.1-sol with ultra reasoning; served backend is recorded only as original receipt metadata and remains unknown when null. No response prose or programme AST enters this plot. R2 banks are batch proposal sessions, so throughput must not be equated to EoH's sequential refinement protocol.

## Presentation revision

The bottom marker-encoding legend was removed to avoid its collision with the horizontal-axis label. The arm legend, every bank point, fifth-bank diamonds and matched-four mean crosses are retained. Marker meanings remain in the caption. No numerical input or plot-coordinate formula changed.

Prior renderer archived at `experiments/source_snapshots/v06/refinement_authoring_efficiency_presentation_001.py`, SHA256 `3b45cd5d9c58f025b076fcd63d3ccaddb945beef1a50354fdb9c89764bdec5a8`. Previous _001 outputs/document remain intact.

## Provenance

Original gate audit SHA: `a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34`. Renderer and all15 receipt byte hashes, bank IDs, requested configuration and original observed-model values are retained in the presentation sidecar. No source/data/audit is modified.

Output directory: `experiments/analysis/v06/refinement_authoring_efficiency_v06_002`.

Sidecar SHA: `bee45541ea2b6f1630c2ece0a150bb8cc3eb15ae5b517f12160d798470bbbb23`.

| Figure | SHA256 |
|---|---|
| refinement_authoring_efficiency_v06.pdf | 67a39f49e3fa4472ac2506140679913a583c7a7a9fd8d7e5c765d7afa75b7237 |
| refinement_authoring_efficiency_v06.png | 154f61a5b4a87f001d4818ddcf5ac190b4bca8d878040e6c28e2dd886ef6e75b |
