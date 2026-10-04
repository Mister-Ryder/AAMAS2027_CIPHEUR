# Lossless native-encoding hypothesis check

Root considered a possible improvement to the numerical interface of the public
solver comparison before any V06 TEST optimizer execution: exact rational weights
can be integerized by their denominator LCM, then divided by the common positive
GCD. This preserves every independent set's objective order and exact ties.
The reverse factor GCD/LCM recovers original reward. It cannot be replaced by
rounding, clipping or weight-rank substitution.

The hypothesis that this would recover signed-32-bit compatibility was rejected
by input evidence. The already frozen public inventory records GCD one for the
25 WDP and ten Grids sources, and their reduced sums still exceed the conservative
signed-32-bit contract. The three Segmentation sources are already compatible.
The runner's independent check of all 38 actual frozen graph byte streams confirms
compatible counts before/after of WDP 0/0, Segmentation 3/3, and Grids 0/0;
all 38 remain signed-64-bit compatible. The eight-second numerical check uses no
solver, certificate query, programme selection or LLM feedback.

Consequently there is no extra native experiment or altered compatibility rule.
The original V003 52,548 assignments, unsupported-input records, exact weights,
kernel, baseline wrapper and source freezes remain unchanged. A numerical range
limitation is not a zero reward or proof that the published algorithm cannot
solve the problem. Final performance tables must state that scope explicitly.

The separate unused prototype `cipheur/advanced_baselines_gcd_v06.py` and its five
mathematical tests retain the proposed interface for inspectable review. Tests
enumerate all feasible subsets/ties on a rational fixture, check boundary reward
and exclusions, confirm that common factors can resolve an artificial range
failure, retain irreducible overflow, handle zero weights, and pin the original
wrapper bytes. This prototype is not imported by the frozen performance study
or the manuscript's proposed method. Native heuristics may be scale-sensitive
despite mathematical objective equivalence, which would require a separately
registered experiment if a future dataset had a useful common factor.

The byte-verified server receipt is `experiments/analysis/v06/public_weight_gcd_metadata_v06_001.json` (SHA-256 `cd942ccd9ba4e65d60e6395a9ff9760833abd7fb97ab92483bf7cf63ff347aaf`). Its numerical check script has SHA-256 `9d24defa318594bd23d2ed5a9c4a5f58ea582947ac4abe96ae070af05df8a876`. All 38 actual frozen public graphs have integer LCM 1 and common factor 1; the compatibility gain is zero. No scheduling-effectiveness conclusion is inferred from input checking. The detailed per-source encoding report is `docs/PUBLIC_WEIGHT_GCD_ENCODING_V06.md`.
