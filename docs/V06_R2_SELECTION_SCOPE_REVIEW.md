# Independent pre-generation review of V06 R2 selection roles

**Decision: the registered distinction between a guarded proposed method and nonguarded quality comparators is methodologically defensible.** This approval concerns the study design, not future results, candidate correctness, complete scalar consistency or held-out effectiveness. It does not reopen the failed R1 deployment decision.

Reviewed configuration: `configs/refinement_selection_v06_002.json`, version `v06_R2_pre_generation_selection_roles_002`, SHA-256 **`2fda6a9ef59f8483deb838c0edca2b515118c2d7409f44ee3bc655217d7c71d9`**. This review precedes R2 authoring and candidate assessment. The configuration records the following commitments:

- Five fixed whole authoring blocks × three arms × eight original slots: **120 raw positions**. There are no adaptive supplements, retries, replacements or requested-model changes.
- Select the first four whole transport-complete blocks in index order, independently of candidate syntax, fit, gate, quality or cost. Assess and report all five blocks and all original positions. This is a transport-conditional cohort; transport failure is not assumed missing at random. Fewer than four whole complete blocks cannot support the declared four-block deployment.
- Use one common finite, fully completed-feasible R1 candidate with a contradictory demanded quotient, ordered by maximum strict fit, maximum exact family quality, minimum exact family work and stable original source ID. This seed and the example frontier are selected using R1 TRAIN information. The resulting estimand is **incremental warm-start repair conditional on that seed**, not cold authoring efficacy or an independent replication of R1.
- Preserve the unchanged original assessor `cipheur.synthesis_study_v06.assess_candidate`, frozen SHA-256 `f640af65645426cdf172d1cbc7326bae221acf43ece81225ef8bf06cf2c8b0bb`, library, shared kernel and budgets.

## Uniform gate remains the primary information comparison

Every arm receives the same joint gate: static-valid finite program, acyclic full base-plus-demanded-addition quotient, and completed-feasible error-free shared-kernel execution on all 120 TRAIN states. Ordinary anytime budget stops are retained under the original semantics. The joint selection order is maximum strict fit, maximum exact equal-family reward/total graph weight, minimum exact equal-family feature-plus-repair work, then original slot.

W/R/O must all use this identical gate and selector for raw-slot eligibility, fit and prefix-yield reports. Ineligible candidates and empty cells remain observable failures of this gate. Acyclicity means that the finite observed representation does not force a ranking contradiction; it does not mean that the actual scalar formula fits every requirement, that the bounded DSL can express every compatible order, or that a selected program generalizes. Report exact scalar fit separately.

Failed/invalid slots remain in the eligibility denominator. They have no actual measured scalar predictions: record their fit as absent, with failure counts, rather than silently treating them as observed zero-accuracy programs. If an unconditional credited-fit metric assigns them zero credit, declare that convention and distinguish it from valid-program scalar accuracy. Do not select transport cohorts using either of these outcomes.

## Separate quality selection is a legitimate comparator

The quality-only selector requires a static-valid finite program and exactly 120 completed-feasible error-free TRAIN rows. It orders by exact family quality, exact family work and original slot. It does **not** use labels, strict fit or quotient eligibility in the ordering, and is applied identically to W/R/O. A program whose information gate failed may enter this nonguarded quality-comparator bank, with that failure still visible. An empty bank remains null; no fallback program or extra candidate may be supplied.

Proposed-method deployment requires **four genuine W joint winners**, one per preselected matched block. This does not require every objective-only or relations-only authoring sample to solve the proposed framework's information constraint. Up to twelve separately selected quality-only programs—four per arm—can be deployed as nonguarded comparators, including quality-only W. These are not certified framework winners. Identical ASTs remain separate assigned authoring identities; they do not become additional independent source samples.

The two frozen deterministic block-0 quality-only control policies, Degree and the predeclared published native methods remain additional comparators. Those methods must not inherit an originality or LLM attribution from being used inside the common initialization/search kernel.

## Permitted interpretation of arm contrasts

All arms must receive the same warm seed, common graph snapshots and quality/work feedback. W and R must receive identical certified ranking labels; explicit exact equality joins/cycle witnesses are the controlled W-specific information. O lacks ranking and gate-fit feedback during authoring, but still enters the common later assessment. It is an objective-only **authoring condition**, not a label-free complete pipeline.

| Comparison | Defensible interpretation |
|---|---|
| W versus R raw-slot gate/fit/prefix yield, same joint evaluation | Incremental effect of explicit witness feedback conditional on the shared R1-selected seed and selected frontier; retain all failures. |
| Quality-only W versus quality-only R/O | Arm-generation contrast under the same objective selector, conditional on the warm seed; four authoring blocks are descriptive. |
| W joint-selected versus R/O quality-only | Difference between complete framework pipelines, including different selection roles; not an isolated causal witness or model effect. |
| Proposed pipeline versus shared-kernel Degree/fixed controls | Added frozen priority/representation contribution on the same kernel and budget; shared classical gains do not become LLM gains. |
| Proposed pipeline versus published native methods | End-to-end solver comparison under declared input compatibility and timing scope; unrelated to causal model attribution. |

Prompt/settings/slot matching does not establish equal authoring compute. Preserve actual input, cached-input, output and elapsed receipts, unknown served-model metadata, and failures. No broad causal, model-superiority or SOTA conclusion follows from four blocks alone.

## Freeze and release requirements

Before withheld labels or any performance TEST, freeze all raw responses, every original-slot TRAIN assessment, both selector outputs, candidate hashes and the release receipt. The R2 source/input/query and performance namespace must be separately registered. Native component TRAIN results must remain excluded from R2 author packets and selection. No performance outcome may choose the cohort, seed, library, gate, budgets, source populations, deployment winner, or additional repair round.

R1's original result archive remains SHA-256 `c6b3b754aa0af36c769a4865e5f935085136f025d88665f079835dfc445f89d9`. Its independent audit is `experiments/analysis/v06/synthesis_train_audit_v06_001.json`, SHA-256 `d0dfeb7d780dda90e70cd16f77c8348ff9e8293a34eafa716bef6e4cd0b5226e`, with 3,203,865 checks and zero errors. It confirms **nine of twelve genuine winners and `ready_for_TEST=false`**, identical TRAIN quality across every assessed R1 candidate, and a real public TRAIN two-arc feature-quotient obstruction. R2 cannot replace these facts, and a successful R2 result cannot retrospectively count R1 as successful.

## Independent prepared-packet review

The final inspectable prepared draft is `experiments/discovery/v06_refinement_draft_003`. Earlier draft `002` was preserved; it is not the audited final input. New auditor `scripts/verify_refinement_packets_v06.py` reads only saved JSON and hashes, without importing a production author, feature evaluator, conditional oracle, assessor or repair kernel. Its result, `experiments/analysis/v06/refinement_packet_audit_v06_002.json`, SHA-256 **`7cabb43f86f1346dfd7b0156c096fc05bfd70c6f24850ee663394137f803837c`**, records **386 checks and zero errors**.

It independently reconstructs the common best-ineligible seed ordering and the fixed SHA frontier. All eleven signed labels come from the unchanged certified TRAIN frame. Mandatory cycle requirements are retained, including the already-correct second arc, and the six states include the companion side of the selected synthetic pair. Every original node ID, weight, duration, conflict edge, F/X commitment and saved Degree/seed feedback is preserved. Source/state/cluster names are masked. The two complete feature-vector joins agree with the prior independent exact MANN proof.

All fifteen packets contain the same seed code, graph examples, common feedback and grammar. W and R have identical relations, seed scalar-fit feedback and gate instructions; only W receives explicit concrete equality joins and the representation diagnosis. O contains no ranking, scalar-fit or gate disclosure. Within each arm, the five packets differ only in block metadata. Packet length differs across arms, so this audit does not establish equal compute.

The draft remains distinct from final registration. Final protocol, runtime/helper/source and transport hashes must be frozen before generation, and raw event-access review is still required after all fifteen new authoring sessions complete. The same receipt cannot stand in for future candidate or TEST audits.

Read-only review of `cipheur/refinement_study_v06.py` and `scripts/author_refinement_cli_v06.py` finds that the declared uniform joint/quality selectors and four-W deployment barrier are implemented separately. Transport inclusion is computed before response parsing, with all 120 raw positions retained. The fresh namespace, full inline packet, same requested settings and no controller retry preserve the planned transport design. Original assessor/helper hashes must also be guarded by the final source capsule/server wrapper; requested settings and future event metadata do not prove the served model identity.
