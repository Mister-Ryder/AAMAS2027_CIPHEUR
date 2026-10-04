# V06 TRAIN evidence: cloud execution receipt

The new preordered TRAIN evidence plan was executed on the authorized cloud
server, independently of the earlier V05 transfer replay. No TEST oracle query
was executed, no query was selected using an outcome, and no original source,
query plan, or original execution receipt was edited. This report records
certificate coverage; it does not report an LLM or scheduling improvement.

## Frozen plan and execution

- Original plan: `experiments/discovery/v06_evidence_001/`.
- Original protocol SHA256:
  `32e008c2d348df53813696f8bfc413829704a9e76c07e4d03ac036387cb11854`.
- Original data SHA256:
  `968f96b7712ca3ecc8a7b43f567c6b6403742f26f0e76e9d5f2c680973827784`.
- Append-only pre-query budget clarification SHA256:
  `16834240d6136cf54cf208e3f03b24f7d0505f72b9cc898df8bf1ac31f4b19d2`.
- New source capsule:
  `experiments/source_snapshots/v06/v06_evidence_train_001_source.zip`, SHA256
  `74c1854536206fe098cbad86cd3a5c400dda279ecbff49c76cf3d80b2e075380`.
- The capsule contains the ten original frozen semantic modules, package init,
  the four original plan files, and a new orchestration wrapper. It excludes
  concurrently developed repair/authoring code. Every original semantic hash
  was checked before execution.
- New registered execution plan:
  `experiments/discovery/v06_evidence_server_001/execution_plan.json`, SHA256
  `11c801b9ed5ccd370b26347aca8a2f69e1f52036d0bad9f3e58c6b978c1844d5`.
- Cloud directory: `/root/autodl-tmp/aamas2027_v06_evidence_train_001`.
- Launcher PID 48818, query process PID 48821. Detached processes wrote
  persistent logs. Python 3.11.17 was reused without dependency installation.
- CPU quota was 16 cores, visible CPU count 192, container memory cap 60 GiB.
  Eight workers reserved half the CPU quota. The pre-query process inventory
  did not show another active research computation; no other process was
  stopped or changed.
- Each graph/state had a fresh oracle with at most 1,024 solver calls and
  2,000,000 expanded nodes. Each unmatched component had at most 32 vertices
  and 50,000 expanded nodes. Exact cancellation and the within-state component
  cache retain their original semantics. A 3,600-second whole-job wall guard
  was only a stalled-job safeguard, with partial outcomes retained and no
  query retry. It did not trigger.

## Coverage and certificates

All 120 TRAIN states returned all 1,503 preordered queries. There were 594
strict conditional-value certificates and 909 exact ties, with no unknown
labels. The 417 quota shortfalls remain in the receipt: these are absent
eligible alias/control queries, not discarded outcomes.

The preselection category `alias` means an alias on either side of a paired
intervention. It must not be interpreted as an alias on both sides. Using the
stored boolean for the actual side yields:

| Actual-side base representation | Strict | Exact tie | Total |
|---|---:|---:|---:|
| Alias | 90 | 570 | 660 |
| Distinguishable | 504 | 339 | 843 |

The 630 paired common-action query pairs contain 12 strict reversals, 123
strict preference preservations, 201 pairs with a strict preference on one
side and an exact tie on the other, and 294 ties on both sides. These counts
describe TRAIN evidence, not performance gains or a final TEST result.

Across the states, the oracle used 1,496 calls and 15,200 expanded nodes. The
largest single-state counts were 33 calls and 2,199 nodes, within the declared
caps. Summed worker CPU time was 1.314 seconds and wrapper wall time was 0.416
seconds. The fast execution is consistent with small states, exact component
cancellation, and low search-node counts; it is not an extrapolated runtime
for large scheduling instances.

Public TRAIN and TEST raw sources are disjoint within this new plan, but the
underlying public corpus was exposed in prior V04/V05 studies. The induced
32-vertex states are new exploratory states, not a new independent corpus.
The synthetic temporal states follow the declared unit-duration/unit-reward
pairwise contact model and are not real C3 observations.

## Archived binding and accounting

- Raw archive: `experiments/runs/v06/v06_evidence_train_001.tar.gz`, SHA256
  `3f6986a6b803761c503876d4b3d1419c7f1fe3adab3acc5929dcb4c6db2c7a48`.
- Results SHA256:
  `45bb07139da8321ccca54f841fb040119f0c1bbf6b2eec8739277b564561b755`.
- Execution host receipt SHA256:
  `41189725161bc357dbb51d43c9338dd3d26d6e236f5cd9061e0b80da9946bc3f`.
- The archive includes original `execution.json` and `complete.json` unchanged,
  plus the original budget clarification and append-only source/host/budget
  bindings in `execution_budget_receipt.json`. Query retries and TEST queries
  are both zero. No credential is included.
- Read-only accounting script: `scripts/analyze_evidence_server_v06.py`.
- Accounting output:
  `experiments/analysis/v06/evidence_server_train_001.json`.

The accounting checks exact TRAIN state identity and coverage, query order and
quota identity, all receipt hashes, signed interval label consistency, and
oracle budget counts. It does not independently re-solve the certificate
problems. A separate scientific audit should check those proofs before final
paper claims. The stored TEST inputs remain unqueried until a TRAIN-selected
program freeze authorizes the predeclared TEST query phase.
