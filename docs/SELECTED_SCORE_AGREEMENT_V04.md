# Frozen TRAIN scalar agreement and synthesis mechanisms

This is a post-freeze TRAIN diagnostic. It changes no proposal, programme, eligibility rule, or selection; no fresh, public or held-out quality outcomes are read. Scalar agreement is a diagnostic, while the implemented guided/free/enumerated information gate tests acyclicity of the entire declared feature interface.

## Evidence and reconstruction

The immutable archive contains 66 contexts and 93 assessments. All 824 saved requirements reconstruct exactly, in saved order: 788 actual-action requirements and 36 prior TRAIN certificates. There are 668 unique endpoint occurrences. Occurrence identity is compact-JSON SHA256([Graph.digest(), sorted(F), sorted(X)]) + ':' + vertex ID. Context JSONL completion order is sorted by (pair_id, side) before replaying state/difference order. Prior seed order, left then right, follows. Prior membership is checked against all recorded source TRAIN digests, not only the sampled context graphs. Every endpoint is feasible at its bound F/X, and each retained relation passes its saved exact Fraction sign inequality. No oracle or schedule is rerun.

Numeric outcomes use the unchanged validated rule and native finite scores: preferred > other is strict agreement, equality is a tie, and preferred < other is violation. Objective epsilon and vertex-ID tie-breaking do not redefine scalar agreement. Eager reference and demanded compiled endpoint scores agree exactly for every queried occurrence. Rates count saved requirement rows, including repeated/shared-state evidence; they are not independent test observations or estimates of agreement on all feasible actions. An actual-action requirement may be counterfactual for another audited programme; only the saved reached regret statistic is restricted to that programme's own recorded rollout.

## Seven fixed programme audits

Six are the original frozen arm selections. Guard64 is a fixed prespecified proposal, audited as a diagnostic rather than newly selected. The primary-only guided ablation is the identical primary AST and is not counted twice.

| Programme | DAG | All agree/tie/violate (824) | Actual agree/tie/violate (788) | Prior agree/tie/violate (36) | TRAIN quality | Relative work | Reached pool-regret bounds | Reached states | Unknown comparisons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Joint | acyclic | 631/0/193 | 596/0/192 | 35/0/1 | 99.033% | 6.657 | [0.000425, 4.238066] | 84 | 335 |
| Degree | cyclic | 465/33/326 | 462/1/325 | 3/32/1 | 97.997% | 1.000 | [0.003570, 3.819279] | 103 | 415 |
| Free | acyclic | 590/4/230 | 555/4/229 | 35/0/1 | 98.640% | 10.278 | [0.004887, 4.244339] | 83 | 274 |
| Rule | cyclic | 492/33/299 | 489/1/298 | 3/32/1 | 98.528% | 1.270 | [0.001991, 3.819388] | 117 | 446 |
| Enum | acyclic | 486/0/338 | 483/0/305 | 3/0/33 | 98.528% | 5.213 | [0.001991, 3.819388] | 120 | 453 |
| g03 | acyclic | 550/0/274 | 516/0/272 | 34/0/2 | 96.445% | 5.523 | [0.020610, 4.038588] | 99 | 348 |
| Guard64 | acyclic | 701/2/121 | 665/2/121 | 36/0/0 | 98.871% | 51.266 | [0.000000, 4.049197] | 77 | 322 |

## What these diagnostics establish

The frozen joint rule agrees with 35/36 prior requirements (97.22%) but 596/788 actual-action requirements (75.63%). This is a descriptive difference within the saved TRAIN evidence, not a statistical generalization claim: the smaller prior bank and the actual-state bank have different constructions, and requirement rows share graphs and occurrences. Guard64 has 701/824 strict agreements versus 631/824 for the joint rule, but uses 7.70 times its measured work and has lower saved TRAIN quality (98.871% versus 99.033%). Both declared interfaces are acyclic. This demonstrates why representation feasibility, a particular scalar rule's orders, and measured scheduling utility are distinct diagnostics; it does not identify the cause of their differences or authorize a new selection. The seven reached finite-pool regret intervals overlap, so they do not support a strict regret ranking among these rules.

The observed gap between an acyclic interface and imperfect scalar agreement directly distinguishes existence of an unrestricted finite fitting score from the frozen bounded rule's actual orders. It does not establish that replacing that rule would improve fresh scheduling. Quality is the equal-family mean reward divided by the best completed bank reward per context, a feasible empirical comparator. Work is relative to the degree baseline; incomplete runs retain zero quality and the declared penalty. The original measured quality/work/regret assessments are reused without recomputation or outcome filtering. Regret endpoints are averaged certified finite-pool enclosures with full-context mean-weight normalization and programme-specific reached coverage; they are not confidence intervals, point estimates, all-action regret, or whole-schedule loss bounds.

## Main-ready figure

`paper/figures/train_mechanisms_v04.pdf` is a 7×2.1-inch vector figure with Arial 9-point text; its PNG is an inspection preview. Panel (a) preserves all 93 measured TRAIN quality/work points, including incompletion penalties, and marks declared-interface acyclicity independently of proposal arm. Panel (b) aligns each fixed rule's strict agreement with its saved reached finite-pool regret enclosure. No midpoint is plotted as an estimate. All 93 assessment records, all endpoint scores/features and all 824 classification rows per audited programme are preserved in the JSON.

**Caption proposal.** TRAIN evidence separates representation, scalar ranking and schedule-aware selection. (a) All 93 frozen-bank proposals: quality relative to the best completed bank schedule versus relative measured work (log scale). Blue rims denote acyclic declared interfaces; orange crosses denote cyclic interfaces retained in separate comparator arms. (b) Six original arm selections and the fixed Guard64 diagnostic: strict score agreement on 824 saved requirements (788 actual-action and 36 prior), alongside programme-specific reached finite-pool regret enclosures. The enclosures are not CIs; coverage differs. All quantities are TRAIN diagnostics, without a fresh-quality claim.

## Provenance and limits

The TRAIN and seed input hashes, immutable member hashes and current matching runtime hashes are in the JSON. The reconstruction and interpreter/compiled parity checks guard this audit; they do not replace the quotient theorem or demonstrate generalization. The bank and selected-programme files remain unchanged.

Elapsed audit time: 2.47 seconds. Exact endpoint parity checks: 4676.

```text
.venv/Scripts/python.exe scripts/audit_selected_scores_v04.py
```
