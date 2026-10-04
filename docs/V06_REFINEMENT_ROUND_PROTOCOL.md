# V06 R2: TRAIN-adaptive representational repair preparation

Status: **inspectable draft, not an authoring or assessment completion**. No R2
model session, optimizer, conditional certifier, candidate assessment or TEST
execution was invoked by the packet builder. R1 sources and observations remain
unchanged. The approved selection-role plan is
`configs/refinement_selection_v06_002.json` (SHA-256
`2fda6a9ef59f8483deb838c0edca2b515118c2d7409f44ee3bc655217d7c71d9`).

The current reviewed draft is
`experiments/discovery/v06_refinement_draft_003`. The earlier `_002` draft is
preserved; it is not the final source-bound draft. This round has its own
protocol version, `matched_refinement_round_v06_002`. The legacy response tag
`matched_cold_bank_v06` is only a JSON wire format and does not describe an
independent cold replication of R1.

## Common seed and feedback frontier

The builder streamed all 120 R1 original positions and retained their statuses.
Ninety-seven completed, finite, static-valid candidates had contradictory
demanded quotients and completed feasible kernels on all 120 TRAIN states. The
common seed is selected from that pool by descending actual strict fit,
descending **exact rational** equal-family quality, ascending exact equal-family
charged work, then lexicographic original source identity. Quality and work
were independently recounted from the saved feasible selected sets and meters;
no policy was executed. Completed finite interface status comes from the
unchanged f640 assessor; all saved strict score pairs and witness vectors were
also checked for finiteness. This is receipt replay, not an independent proof of
every feature evaluation.

The selected R1 seed is `block_2_relations:3`: 584/594 strict scalar agreements,
equal-family quality `2693/4480`, and equal-family work `34510619/5760`. Its six
additional features are all demanded by its scalar rule. The saved full demanded
quotient has a genuine two-arc cycle on the TRAIN induced `MANN_a9_unit` graph:

- strict arcs `34 > 5` and `7 > 35`;
- exact equality joins `5 ~ 7` and `35 ~ 34` under base9 plus all six demanded
  additional features.

Both arcs are bound to their concrete state/endpoints and strict-filtered query
indices. Each join must connect the preceding negative endpoint to the next
positive endpoint and have exactly equal finite numeric vectors; binary-float
values are compared exactly, with no tolerance. The saved strict conditional
intervals are oriented as preferred-minus-other, including sign reversal when
the preferred endpoint was originally `b`.

Every concrete witness requirement is mandatory. Remaining misranked strict
requirements are ordered by a fixed SHA over state/action/query-kind metadata,
with at most 32 distinct labels and 16 states, counting any paired companion.
The present frontier has 11 labels and six states: five labelled states plus
the paired companion of the selected temporal endpoint. Mandatory evidence
alone exceeding the caps aborts preparation. Remaining cases exceeding a cap
are explicitly recorded as omitted. Every displayed interval is `[1,1]`;
these labels concern the original full residual snapshot and explicit F/X,
not a restricted repair patch or a pivot-optimality guarantee.

## Matched information and unchanged limits

All arms receive exactly the same seed AST, six full graph views, boundaries,
generic background descriptors, Degree feedback, seed quality/work feedback,
base9 and existing 25-operation typed library. Original node IDs, weights,
durations, conflict edges and scored constraint fields are retained. Source,
state, pair and cluster metadata are replaced coherently by opaque case/group
IDs. Seed name and rationale are replaced without changing its deployment AST.
The original bindings are controller-only.

Relations receives the same 11 certified strict labels and scalar misranking
feedback as Witness, without explicit equality joins. Witness additionally
receives the concrete full cycle, endpoint vectors and diagnosis. Objective
receives graph/quality/work observations and code, with no labels, gate,
strict-fit counts, diagnosis or equality-join disclosure. The prepared packet
audit checks this separation and equality of common fields.

The grammar remains six additional features, 48 expression nodes and depth
eight per feature, 256 rule AST nodes and 2,000 rule characters. Assessment
retains the f640 source, full 594-label demanded quotient, 100-million feature
unit/60-CPU-second offline interface caps, and identical 0.5-wall-second shared
branch-scope repair contract. No new primitive, fallback, candidate patch or
gate weakening is introduced.

Five whole blocks, three arms and eight original slots produce 15 sessions and
120 raw positions, fixed before generation. All positions are assessed. The
descriptive matched cohort is the first four whole transport-complete blocks
by index, irrespective of syntax, gates, fit, quality or work. This conditional
cohort is not assumed missing at random; there is no adaptive supplement,
retry, replacement or requested-model change.

The approved controller plan separately records identical joint-gated and
quality-only selectors for all three arms. Null winners remain null. Four
genuine Witness joint winners are required for framework deployment; quality
comparators are explicitly nonguarded, with their actual gate statuses retained.
Framework-versus-quality comparisons include selector differences. Common
quality-selector arm contrasts concern this adaptively selected seed and four
descriptive authoring blocks; they do not establish a population or causal LLM
advantage. R1 failed barriers and observations remain recorded.

## Reproducible preparation and explicit finalization

From the repository root:

```powershell
.venv/Scripts/python.exe scripts/prepare_refinement_round_v06.py prepare --out experiments/discovery/v06_refinement_draft_003
.venv/Scripts/python.exe -m unittest tests.test_refinement_round_v06 -v
```

The prepared directory must be new. For an independent replay, choose another
unused output path; do not overwrite `_003`. The six bounded unit tests check
exact rational ordering, concrete cycle closure, near-equality rejection,
strict-query identity, deterministic capped paired-state selection and refusal
to authorize a changed draft. They passed in 0.041 seconds. No full research
test suite or policy evaluation was rerun. Fifteen packet JSON files are at most
34,067 bytes each.

Preparation deliberately writes `draft_protocol.json` and
`preparation_receipt.json`, but **does not** write `protocol.json`,
`freeze_receipt.json`, `transport_amendment.json`, responses or authoring
receipts. Explicit finalization requires the exact already-bound approved plan
and a fresh R2 transport source, with all prepared files and unchanged assessor
dependencies verified first:

```powershell
.venv/Scripts/python.exe scripts/prepare_refinement_round_v06.py finalize --study experiments/discovery/v06_refinement_draft_003 --selection-plan configs/refinement_selection_v06_002.json --transport-source scripts/author_refinement_cli_v06.py
```

The last command is a contract example, **not an execution claim**. Root owns
the fresh transport/loader and its isolated R2 namespace, final review and model
launch. Final transport receipts state that R1 assessment already occurred,
and bind decisions before R2 authoring/assessment; they do not falsely claim
that no V06 assessment had occurred.

Current preparation SHA-256:
`a90a17bd2cd632fae963de090a34eca82cdb03ef04af705e1c2deff0c976ecbb`.
Builder source SHA-256:
`cc335cb572eaf8d694e39f0caa104a133b4f17df1c2749dbfcd48063b7944056`.
Draft protocol SHA-256:
`c221899818df0a72f088b022bc502a818a26c6037217036b2794e9814efc6907`.
