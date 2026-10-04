# V06 LLM design rationale and claim boundaries

This note supports the independently owned introduction revision. It reads
the current method, frozen typed-library definitions and previously audited
TRAIN reviews only. No actual heldout/performance outcomes, evolving results,
new oracle query or solver execution were accessed. Root owns method,
discussion, integration and the final audited-result replacement.

## Why use an LLM here?

A certified quotient cycle identifies a concrete information obstruction.
Its arcs and equality joins show that at least one currently equal pair of
occurrences must be distinguished. The witness does not construct the typed
expression that supplies that distinction or a bounded scalar rule that uses
it correctly. That remaining construction problem is the role assigned to the
LLM.

The frozen library supports typed graph sets, their compositions, scalar
reductions and arithmetic/conditional ranking expressions. It limits additional
features to six, each feature to 48 expression nodes and depth eight; the rule
also has a separate bounded syntax check. These limits constrain execution but
still leave combinatorial choices of expression trees, feature subsets and
compatible score expressions. No exact search-space cardinality, asymptotic
complexity result or measured enumeration speedup is asserted.

The LLM provides a conditionable prior over programme constructions, used as
a proposal operator. A prompt can convey the actual joins, example graphs and
a rejected programme together, enabling a joint feature-and-rule proposal.
The intended benefit is to concentrate a limited candidate budget on the
structural distinctions demanded by the evidence. This is a design rationale
and testable hypothesis, not a calibrated probability model or a theorem that
the LLM proposes better programmes.

Executable programme generation with evaluator feedback is established in
[FunSearch (Nature)](https://www.nature.com/articles/s41586-023-06924-6),
[EoH (ICML)](https://proceedings.mlr.press/v235/liu24bs.html) and
[ReEvo (NeurIPS)](https://proceedings.neurips.cc/paper_files/paper/2024/hash/4ced59d480e07d290b6f29fc8798f195-Abstract-Conference.html).
Their existing formal BibTeX entries are reused. These precedents motivate the
proposal mechanism; their reported successes are not evidence of an advantage
for our implementation. No new reference or arXiv entry was added.

## What determines whether a proposal is acceptable?

The LLM does not certify its own output. Deterministic checks establish typed
syntax and finite evaluation, rebuild the complete demanded quotient, measure
actual strict scalar fit and check feasible error-free TRAIN execution.
Selection orders eligible pairs by actual fit, schedule quality and charged
feature-plus-repair work. Acyclicity permits an unrestricted scalar on the
finite observed vectors; it does not establish that the proposed bounded rule
fits those vectors or transfers to new inputs. Mature shared repair and its
feasibility checks supply the deployment safeguards equally across arms.

Authoring and certification occur before freezing. Repeated deployment uses
the resulting programme without model or full-residual certification calls.
Offline expenditure can be shared across deployments, but no break-even
deployment count, net-cost saving or general inference-speed advantage has
been demonstrated. Candidate count and requested settings are matched; actual
tokens and authoring latency are not matched computation.

## Theory and the deterministic alternative

The finite representability theorem concerns feature information: a cycle
precludes any deterministic pointwise scalar of those represented values.
It proves the need to split an obstructing equality when satisfying those
strict requirements. It neither requires an LLM nor ranks proposal methods.

The existing 53-expression TRAIN catalogue makes deterministic interface
selection concrete. Its four-feature acyclic repair has independently
certified minimum standalone additive cost 1,371,468 on the fixed inventory.
The catalogue originates from prior R1 proposals, so this is deterministic
selection once expressions are available, not a blind non-LLM generator
comparison. It does not produce a fitted ranking rule, minimize general
shared-DAG runtime or prove transfer. The smaller unresolved catalogues remain
negative outcomes. Enumeration and manually supplied candidates are valid
alternatives under the same validators.

Source: `docs/V06_CATALOGUE_COST_FINDINGS.md`, recording the immutable catalogue
archive `dab90de26a486d11174ba10f06723c8c02ae277aa2907d643fe36909107ecc05`
and independent zero-error audit. No catalogue result was recomputed here.

## What the current evidence can say

The previously audited conditional warm-seed study reports 26/32 eligible W
positions versus 19/32 R positions in the four preregistered matched blocks.
This is an observed information-gate yield contrast from adding explicit
witness feedback within LLM synthesis. All original positions remain.
The four block counts are W/R 7/4, 8/4, 3/3 and 8/8; the fifth retained block
reverses the contrast at 2/5. All-five yield is 28/40 versus 24/40.

Relations-only proposals have stronger matched mean actual strict fit:
574.8125 versus W's 547.90625 fitted labels out of 594. Every candidate's TRAIN
macro schedule quality is exactly 2693/4480. No candidate fits all 594 strict
requirements, and selected W joint programmes have higher mean charged work
than R. The introduction preserves the stronger R fit and quality tie instead
of treating gate yield as general programme superiority.

Source: `docs/V06_R2_TRAIN_SCIENTIFIC_REVIEW.md`, bound to independent TRAIN
audit SHA `a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34`.
These existing findings do not establish LLM versus non-LLM advantage,
model-general benefit, fully consistent scalar rules, natural physical
information-conflict prevalence or heldout scheduling-quality superiority.
The original R1 failed deployment barrier remains a separate historical
outcome.

The measurable questions are therefore separate: whether witness conditioning
improves gate yield, whether the resulting rule fits certified preferences,
whether it helps a common repair kernel on audited heldout inputs, and what
feature, search and authoring costs it incurs. Comparisons to deterministic
controls and the separately registered published-synthesis pipeline answer
different questions from W-versus-R conditioning. Their actual heldout and
performance results remain placeholders until independently audited.

## Integration scope

Only `paper/drafts/v06/introduction.tex` and this new note were edited. The
introduction's three mechanism/design paragraphs now explain the missing
construction step, proposal choice, deterministic authority and deployment
cost separation. Its final result placeholder remains for the root to fill
with audited withheld-constraint, weighted-performance and published-synthesis
findings. The method supplies implementation detail; the discussion supplies
full theorem and empirical limits. No engineering logs, transport details or
new unsupported numbers were inserted into the manuscript.
