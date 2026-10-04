# Public-weight GCD encoding check

The metadata-only check of all 38 prepared public TEST graph files found no removable common weight factor. Every graph has LCM 1 and integer-weight GCD 1. Lossless GCD division therefore leaves the frozen native32 compatibility boundary unchanged; no additional optimizer experiment is justified by this hypothesis.

| Prepared population | Graphs checked | signed32 before / after | signed64 before / after |
|---|---:|---:|---:|
| WDP | 25 | 0 / 0 | 25 / 25 |
| UAI Segmentation | 3 | 3 / 3 | 3 / 3 |
| UAI Grids, CHILS64 track | 10 | 0 / 0 | 10 / 10 |

The check reads exact Fraction weights from the actual graph-file bytes, computes the denominator LCM, integer-weight GCD, and maximum and total integer weights before and after division. It checks exact reconstruction of the graph and source objective and records each graph-file SHA256. The bound is conservative: support requires nonnegative integer weights and both maximum and total within the declared signed integer range. This checks the existing adapter's declared input contract; it does not establish every internal arithmetic limit of a native solver.

Uniform positive scaling preserves objective order. A heuristic's internal stopping or search behavior can still depend on scale; this check makes no runtime or quality equivalence claim. The unsupported requests in frozen V003 remain requested and explicitly unsupported. No original input, protocol, source capsule, adapter, program, or result was changed.

This activity accessed TEST numerical input metadata only. It made **zero optimizer calls**, read no candidate or label files, and performed no TEST optimization. Its server CPU and wall time and all 38 per-graph records are preserved in the JSON receipt.

Evidence:

- `experiments/analysis/v06/public_weight_gcd_metadata_v06_001.json`, SHA256 `cd942ccd9ba4e65d60e6395a9ff9760833abd7fb97ab92483bf7cf63ff347aaf`.
- `scripts/check_public_weight_gcd_v06.py`, SHA256 `9d24defa318594bd23d2ed5a9c4a5f58ea582947ac4abe96ae070af05df8a876`.
- Prepared input freeze SHA256 `42f7e9606499e379063c81d66d96beaa9cefb77be57be66c6076784ff33e4689` and context inventory SHA256 `f4d204d75ee2eb9e05b40405ae25bd47a0b4c3714df27a28a0b4930b857cc917`.

The local transport check independently verified the downloaded report's hash, script hash, all graph-file hashes against the prepared inventory, integer sum/max relations, and equality with the original-source total. The initially suggested removable WDP factor was a numerical hypothesis, not an empirical finding; these exact checks reject it.
