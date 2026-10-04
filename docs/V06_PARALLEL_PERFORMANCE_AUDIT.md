# V06 performance audit: bounded process orchestration

`scripts/verify_performance_parallel_v06.py` changes verification execution
only. The original mathematics remains in the unchanged
`scripts/verify_performance_test_v06.py`, SHA-256
`59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a`.
The wrapper pins that file in the parent and each spawned worker. Its own
SHA-256 is `6e5ccfd1782ddce0548268a4e670be20841e28639e7b3f08586e95fcba464b71`.
No experiment, candidate, frozen source, original auditor, helper, test or
analyzer was modified. Preparation compiled the wrapper and checked `--help`
only; it did not open real results or perform any real or constructed audit.

## Scope preserved

The parent retains the original canonical archive hash, frozen protocol/source/
deployment/release checks, safe archive-member checks, graph-byte and result
hashes, original execution/host/guard receipts and complete requested frame.
It stages graph and context-journal bytes during the original first archive
pass. Workers reread only these staged files and compare journal hashes with
the first archive pass. The existing `journal_second_pass_same_bytes` category
now denotes this bound staged reread, rather than decompressing the same archive
a second time. Output bytes remain tied to the canonical archive hash.

Each top-level process worker owns one new original `GraphAudit`, preserving
all native command/encoding/output checks, exact rewards and feasibility,
common Degree initialization, every retained patch restriction and clique
proof, restricted-optimum checks, priority/greedy traces, charged work, all
phase-time/cost receipts and original compact fields. Within-context caches
retain their original lifetime. Workers return all checks, errors, totals,
status counts, seen keys, journal-row hashes and compact rows. Exceptions fail
the audit; there is no hidden worker retry or fabricated success.

The original membership/uniqueness check is moved to the parent, where it is
performed once per returned assignment against the global frame and seen set.
This preserves cross-context duplicate detection without adding a duplicate
check to each worker row. All remaining per-context mathematical and receipt
checks are copied from the byte-pinned original source. The parent then retains
the original aggregate-generated worker-null and guard-unreturned handling,
full 52,548-row/302-context/23-policy frame, final aggregate hash/status counts,
complete/partial execution semantics and final report.

## Resource and ordering contract

`ProcessPoolExecutor(max_workers=6)` has at most six context futures in flight.
Frozen protocol/deployment/hash lookup metadata is initialized once per worker;
graphs, decoded journals and mathematical caches remain per context. Only the
small compact rows and counters return to the parent. The parent consumes
futures in original archive-journal order, then writes original explicit-null
order, so parallel completion order cannot reorder compact output. Temporary
staging uses a new directory namespace and does not overwrite the serial
auditor's staging or partial rows.

Staging requires disk space for graphs plus the exact context journals; this is
not a lossless-storage reduction. Verification wall/CPU consumption is not
experimental runtime or algorithm cost, and parallelization is not claimed as
an algorithmic speedup.

The report keeps the original expected version
`v06_independent_performance_TEST_audit_001` and records
`audit_source_sha256` as the imported original mathematical auditor. Additional
`orchestrator_source_sha256` and `verification_orchestration` fields identify
the new process orchestration, six-worker bound, deterministic order and zero
experimental reexecution/retry. Three original helper hashes and downstream
analyzer source pins remain unchanged. A source review of the original auditor
does not by itself review the new orchestration; root owns the necessary
integration inspection and actual launch.

## Command and partial-run preservation

Root first preserves the interrupted serial compact prefix separately. The
new output paths must not already exist; neither reports nor compact rows are
overwritten. Root then executes the required complete audit once:

```powershell
python scripts/verify_performance_parallel_v06.py `
  --archive experiments/runs/v06/<canonical-V003-result-archive>.tar.gz `
  --archive-sha256 <actual-canonical-archive-SHA256> `
  --out experiments/analysis/v06/<final-performance-audit>.json `
  --rows-out experiments/analysis/v06/<final-performance-audited-rows>.jsonl
```

No scientific result, success count or final audit is asserted by this
preparation note. The same final zero-error report and full compact frame are
required before statistical analysis.
