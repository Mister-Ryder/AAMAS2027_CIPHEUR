# R2 held-out preparation: original audit versus scalar receipt

The main TEST release and every scientific runtime source remain immutable.
After the original 72 TEST certificates were computed and independently
verified, root checked the remaining preparation metadata before executing any
R2 held-out programme. This exposed a byte-identity mismatch, not a failed
scientific audit: the pre-generation transport binds the original independent
packet report, while the reviewed count-schema adapter creates a separately
hashed scalar-count receipt required by the frozen consumer. The original
preparation function compared the transport's original-report hash directly
with the scalar-copy hash. Those two valid files cannot have equal hashes.

`scripts/prepare_heldout_r2_audit_compat_v06.py` is a separate metadata-only
preparation entry point. It verifies both files against the original main
release, checks that the scalar receipt preserves all findings and counts,
and compares the transport with the original report it actually bound.
Its extracted preparation function has only that one comparison change and
the source-snapshot location adjustment required by its separate file.
It continues to write the original registration schema and uses the unchanged
original execution module. It changes no programme, selector, feature, query,
certificate, scientific gate, work/time budget, source split or comparison.
No scientific experiment is rerun as part of this compatibility operation.

The separate syntax/provenance comparator
`scripts/verify_heldout_audit_compat_v06.py` verifies that the rest of the
preparation function's AST is identical. Its report is
`experiments/analysis/v06/heldout_packet_audit_identity_compatibility_review_v06_001.json`:
18 checks and zero errors. Six fabricated mutation tests reject changes to
winner gates, certificate binding, worker limits and audit checks. The first
test invocation contained an invalid fabricated Python mutation; that test
was corrected before execution was authorized. No genuine experiment ran in
that failing test. The original independent scientific audits remain unchanged.

This comparator was executed by root. The previously assigned reviewer
agents are unavailable because of an account usage limit; this mechanical
comparison is explicitly not described as a newly completed subagent audit.

The compatibility receipt is separately dated after certificate verification
and before R2 programme evaluation:
`experiments/discovery/v06_test_release_002/heldout_packet_audit_compatibility_release_001.json`.
It does not claim that a new global TEST freeze occurred before already-read
certificates. The original main release still supplies the earlier freeze.
The independent certificate verifier retained all 962 original queries,
including 453 strict preferences and 509 exact ties, with 18,247 checks and
zero errors. No extra certificate queries or LLM author calls were added.

Complete performance evaluation runs separately on the server. Held-out
programme execution will follow that batch to avoid overlapping solver
workloads in the timing comparison. Metadata preparation executes no solver.

The separate R2 registration was prepared successfully on the cloud, retaining
27 non-null identities and all 11,664 state assignments. Its complete prepared
archive was downloaded and checked before root issued the second-stage EoH
addon release. Two manually transcribed wrapped-terminal digest literals were
incorrect and were rejected before that release was written. Archive identity
was corrected to the actual verified bytes; the parent freeze identity is now
derived directly from the pinned complete archive rather than transcribed a
second time. No registration, experiment, certificate or selection was rerun.
The EoH addon was then prepared successfully with all four identities and 1,728
assigned states. Preparation performed zero programme evaluations.
