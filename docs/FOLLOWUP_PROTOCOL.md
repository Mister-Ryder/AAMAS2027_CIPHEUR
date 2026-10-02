# Fresh-instance frozen-program follow-up

The follow-up applies every method in an earlier `frozen_programs.json` to fresh
test instances. The original file is copied byte for byte. No program is edited,
no candidate is added, and no training or validation selection is repeated.

```powershell
python -m cipheur.followup --pilot experiments/runs/pilot_v0.2.0 --output experiments/runs/followup_v0.2.0
```

The output directory must be new. The default suite expands the three families
to 24 diagnostic, 32 random temporal, and 16 C3 windows per split. Only the test
records with indices at or beyond the old requested test counts are retained:
diagnostic indices 12–23, random indices 16–31, and C3 indices 8–15 for the
original pilot. The generated training and validation records are saved for
data provenance and are never used for program selection.

New instances are compared with **all three prior splits**. Reused record IDs,
synthetic seeds, physical-instance fingerprints, scheduling-graph fingerprints,
and C3 opportunity IDs are rejected. Repeated diagnostic topology is intentional;
the claim is fresh instantiated mechanism probes, not unseen-topology learning.

Increasing C3 window counts changes their time partition: 8 windows cover
10,800 seconds each, whereas 16 windows cover 5,400 seconds each. The new windows
retain the declared deterministic resource grouping and node-cap rule. Any
opportunity already present in any old split is then excluded by original ID.
The exclusion count and surviving contact count are recorded. When exclusion
changes a graph, its induced edges preserve the pairwise frozen V51 conflict
predicates, and the original verifier checks retained selections in the larger
pre-exclusion window context. A window containing no unseen opportunity is
reported explicitly and provides no scheduling context. There is no filtering
for preference reversal, graph change, certificate success, or schedule quality.

This study uses fresh instances under the **same held-out test resource
configurations** as the original pilot. It does not provide a new constraint
distribution, an independent LLM trial, or full-C3 performance evidence.
Diagnostic, random temporal, and source-derived C3 results remain separate.

Before evaluating new objective values or certificates, the follow-up saves the
unchanged frozen file, configuration, raw generated suite, retained test data,
cross-run identity audit, source snapshot, and freeze receipt with SHA-256
hashes. Offline completion certification and reference bounds run after that
freeze. The reference search permits at least 100,000 expanded nodes and records
lower/upper bounds and exactness for each context. Reported quality is schedule
value divided by the sound reference upper bound; it equals the optimal-value
ratio only when that reference is exact.

Each C3 schedule is additionally checked with the original V51 verifier while
the runtime context remains available. Outputs include raw per-method/context
JSON and CSV metrics, reference bounds, certificates and unresolved acquisition
attempts, original-verifier results, family and relation summaries, and hashes
of all saved artifacts. Identical frozen programs may occur under several method
labels; their objective results do not count as independent method discoveries.
