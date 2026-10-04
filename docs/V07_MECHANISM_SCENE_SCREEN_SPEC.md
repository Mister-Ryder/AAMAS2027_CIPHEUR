# V07 mechanism scene screen: outcome-free specification

Status: planning only. This document authorizes no graph benchmark, optimizer, conditional oracle, candidate assessment, model call or TEST-label read. It changes no V06 algorithm, input, feature interface or result. The immediate objective is to establish whether the intended C3 scene supports recurrent decision structures before making a transfer claim or changing the method.

## 1. Scene and claim to test

The core hypothesis is: a frozen structural rule encounters related resource-competition patterns in later opportunity windows, and recomputing features on the graph rebuilt under the current constraints exposes relevant changes. The hypothesis does not say that a rule memorizes the switching-gap coordinate, that the same generator guarantees recurring decisions, or that recurring patterns guarantee better complete schedules.

Use the C3 scene proposal prepared separately in `V07_SCENE_DATASET_SELECTION.md` and `configs/v07/C3_scene_screening_001.json`: original duration rewards and complete contact intervals; retrospective day/window partitions; common, explicitly declared ground-transition configurations; inherited satellite predicates kept fixed. Those files own the numerical settings and window inventory. The proposed start-window frame has an empty boundary and retains contacts whose ends cross the window boundary. It is an independent static opportunity subproblem, not a segment of a feasible full-day schedule. Previously exposed C3 cannot be called a new unseen corpus.

Retain every prescribed window and configuration, including zero edge changes, zero aliases, uncovered classes and insufficient certificate scope. A screen reports applicability and coverage; it must not select favorable seeds/windows, adjust weight classes or remove inconvenient instances. A later modification of the frame requires an explicit new protocol rather than a silent screening filter.

## 2. Exact decision boundary

For graph `G_theta=(V,E_theta,w)` and boundary `B=(F,X)`:

- `F` is the already committed independent set, feasible under the current configuration.
- `X` is the permanently excluded set, disjoint from `F`.
- `R_theta(B)=V \ (F union X union N_theta(F))` is the available action set.
- A committed inclusion decision chooses `a` in `R_theta(B)`, retains `F union {a}`, and removes its conflicts. Its conditional completion value is `V_theta(a|B)=w(F)+w(a)+alpha_w(G_theta[R_theta(B)\N_theta[a]])`.

A paired comparison `(theta0,theta1,B,a,b)` requires identical contact opportunities/rewards, exactly the declared configuration intervention, one identical `F,X`, feasibility of `F` on both sides, and `a,b` available on both sides. The two actions need not be mutually compatible: each is considered as a separate inclusion. Report their adjacency explicitly. Never use different boundary commitments and call the change a pure configuration effect.

Three boundary scopes remain separate:

1. **Initial static scene:** `F=X=empty`. This is the only reached boundary supplied automatically by an input-only window screen.
2. **Reached construction decision:** a later, separately frozen reference rollout supplies `F,X` and the available set. The screen itself performs no rollout. Static initial-state evidence cannot be relabeled as reached-policy evidence.
3. **Repair decision:** the outside incumbent is fixed, destroyed/restricted vertices and permanent exclusions determine the actual local feasible graph. Any inclusion certificate must use that exact local boundary. A B&B pivot is a search-order decision that can explore both branches; inclusion-value ordering does not prove an earlier incumbent or lower search cost.

For a given full-residual boundary, scores of all available actions must be computed on that residual snapshot. For a patch-scoring interface, they must be computed on the actual patch snapshot. A full-graph motif census is not automatically a census of the interface exercised at runtime. Actual path control and budget binding remain a later TRAIN-only diagnostic, not a dataset screening result.

## 3. Fixed label-free structural census

Fix classes before labels. Use exact adjacency/resource incidence, without reward quantization or artificial inserted motifs. The following census is descriptive and not an information-obstruction proof.

### 3.1 Per-window intervention exposure

For each paired configuration retain `|V|`, `|E0|`, `|E1|`, added/removed edges, edge Jaccard distance (zero when both empty), and fractions of contacts whose neighbor sets change. Report weight/duration distributions, edge-type counts, component sizes and zero-change counts with all-window denominators.

Record an edge-reason bitmask from the actual builder: same-station rule, inherited same-satellite rule and any genuine task rule. Multiple reasons may hold. Increasing only a station gap can create a station-related edge even when a satellite edge already exists; distinguish changed reason masks from changed untyped edges. Do not assert single-capacity interval semantics for the legacy satellite predicate.

### 3.2 Rooted topology census

On each declared available set, record the following exact root descriptors:

- degree and induced-neighborhood edge count;
- triangle count at the root and open centered-wedge count, respectively `m(N(v))` and `choose(degree(v),2)-m(N(v))`;
- neighbors supported by station-only, satellite-only and multiple conflict reasons;
- resource incidence: number of distinct stations/satellites among neighbors, counts sharing the root station/satellite;
- same-station/same-satellite centered two-neighbor triples, split into linked versus unlinked neighbor pairs and exact conflict-reason classes;
- connected-component membership/size for the residual graph, separately from root-neighborhood classes.

The third-order centered classes are a finite predefined catalogue: two spokes each have a fixed edge-reason mask, and the neighbor-neighbor edge is absent or has its own mask. Neighbor roles are unordered. Counts include all valid triples; absent classes remain explicit zeros. These are domain structural classes, not discretized numeric feature vectors. They can recur despite different weights, degrees and contact IDs. Counts may be accumulated efficiently by resource/adjacency indexing, but an approximate sampled implementation must declare its sampling units and retain its denominator.

For weighted diagnostics additionally report exact sums/maxima already in the base interface, weighted neighbor-edge minimum sums and the observed source reward-duration relationship. Their values remain exact; they do not redefine a motif class through tuned bins. Topological recurrence alone omits the weights that determine MWIS preferences.

### 3.3 Cross-window recurrence and coverage

Fit no classes on held-out outcomes. Let `C_train` be the set of predefined classes actually present in the complete TRAIN census. For validation/later windows report:

- class coverage: number of observed held-out classes also in `C_train` / number observed;
- occurrence coverage: count of held-out motif occurrences belonging to `C_train` / all held-out motif occurrences;
- root exposure coverage: roots participating in at least one observed TRAIN class / all roots;
- full descriptor reuse: roots whose exact declared rooted descriptor was observed on TRAIN / all roots;
- family/window-balanced summaries in addition to pooled occurrence summaries, so large dense windows do not silently dominate.

Each denominator is different and must be labeled. Empty populations yield unavailable values, not 100% coverage. A root belonging to one very common motif does not imply coverage of its entire decision neighborhood. Report recurrence by day, window scale, model, configuration and resource class; no best-family selection. Optional distribution distances may compare fixed class histograms, but require no learned threshold and are not guarantees of preference transfer.

## 4. Complete base-nine exact-alias census

The existing `cipheur.programs.FEATURES` interface is exactly:

`weight, duration, degree, conflict_weight, max_conflict_weight, compatible_weight, station_gap, satellite_gap, remaining_count`.

The primary exact-alias key uses **all nine** fields on the stated available set. Preserve raw rational/integer source semantics and declared feature arithmetic; do not round floats, bucket weights, remove durations or zero configuration fields to manufacture collisions. In this C3 source reward equals duration, so those two fields are redundant, but redundancy does not imply equality of complete vectors. `compatible_weight` is also algebraically related to total available weight, root weight and neighbor-weight sum; report this rather than treating all nine as independent dimensions.

For each boundary and the cross-boundary inventory report:

- distinct vectors / action occurrences;
- fraction of actions in non-singleton exact classes;
- number of unordered aliased action pairs;
- class size distribution and largest class;
- aliased pairs whose fixed structural descriptors differ;
- same-boundary, cross-window and cross-configuration counts separately.

A pair can differ structurally without differing in optimal preference. No score, value label or quotient arc exists at this screening stage. Accordingly, call these **potential indistinguishability sites**, not certified contradictions or guaranteed representation repairs.

Different gap coordinates prevent cross-configuration full-base-nine equality when a gap changes. Aliases can still exist within one configuration or across windows with the same configuration. If a new deployed grammar intentionally excludes gap coordinates, separately declare a **new graph-only interface** and census its seven-field projection; do not substitute that projection for the original nine-field theorem/gate. Static AST dependency checks can later show that a proposed rule does not read gap fields, resource/contact IDs, absolute source time, day or split. Feature recomputation on current adjacency still carries the consequences of configuration changes without reading their scalar setting.

## 5. What the exact quotient does and does not establish

The theorem concerns exact equivalence of complete represented occurrence vectors and certified directed strict demands. An equality census without demands is not its quotient graph. Many exact classes are harmless: weighted, boundary-preserving graph automorphisms give equal conditional completion values, so symmetric indistinguishable actions alone do not create a strict contradiction.

On large heterogeneous weighted graphs, reward/duration/neighbor-sum/max fields may make virtually all occurrence vectors unique. Consistent strict demands within a boundary then have no cross-occurrence equality joins to force a representation obstruction. The acyclicity gate may be vacuous; passing it neither proves sufficient transferable information nor shows an LLM repaired information. Even with aliases, all certified demands may remain compatible. Rule-grammar failure on an acyclic quotient is a bounded expressivity/fitting issue, not a proved information deficit. Unknown certificates remain unknown.

Approximate motif matching and exact quotient equality answer different questions. A tolerance/binning-based quotient would require a new relation, robustness assumptions and a separate guarantee; it cannot inherit the exact theorem. Do not add such a relation merely because natural aliases are scarce.

If labels are acquired later, retain all requested comparisons. Compute the full quotient on the declared occurrence inventory, preserve self-loops/cycles and uncovered witnesses, and separate the practical candidate-interface gate from exact finite-catalogue minimum-cost repair. Per-window equality incidence does not predict cycle prevalence.

## 6. Label-free candidate framing and certificate feasibility

Freeze comparison slots before conditional values. A simple plan takes all exact-alias pairs when tractable, together with a fixed hash-ordered sample of non-alias competing pairs. Cap each stratum using a public hash seed and complete before/after inventories; retain requested, available, capped and unavailable counts. Do not select comparisons because a synthesized head ranks them differently or because an oracle finds a reversal. If all pairs are too many, an exhaustive count plus hash sample is preferable to silently presenting selected witnesses as prevalence.

For paired configurations, require the same action IDs and common availability. Candidate framing reports neighborhood changes, descriptor changes and complete feature-vector changes for both actions. A comparison with no change is retained as an invariance-control slot, not deleted. Labels of reversal, preservation, tie or unknown require the later sound conditional bounds.

Cancellation tractability can be screened without solving: form the two conditional residuals, match components by exact vertex sets **within each configuration**, and count unmatched components/vertices and their sizes. This is only a geometric workload estimate. A large unmatched component predicts missing exact closure under a cap, not a preference, and must not be excluded after labels. Nonidentical components cannot cancel merely because they are isomorphic or have similar histograms.

## 7. Invariance and identity-tie diagnostics

Retain future metamorphic checks as a separately registered diagnostic: contact-ID bijection, station/satellite-name bijection and common time translation with durations/gaps unchanged. Graph edges and exact feasibility/objective should transform accordingly. A rule using only label-invariant structural primitives should have correspondingly invariant scores; equal-score action ties may still follow the implementation's deterministic ID order. That tie path can change later boundaries and complete schedules without a representation change.

Do not assume every existing typed primitive is label-invariant. The fixed greedy-independent-set and greedy clique-cover summaries can break weight ties by IDs, so their returned numerical summaries can change under relabeling. Distinguish graph-construction invariance, primitive-score invariance, scalar-score invariance and kernel tie-path invariance. ID sensitivity is not automatically evidence of LLM failure or a structural contradiction. Original and relabeled occurrences stay clustered, not independent sources.

## 8. Minimal implementation handoff

Root can authorize a new `cipheur/scene_screen_v07.py` after the scene contract is frozen. Suggested input schema: source/contact hashes, split/window/model/configuration, full graph and edge-reason masks, and an explicit boundary inventory. Suggested output: `window_census`, `motif_census`, `base9_alias_census`, `paired_change_census`, `candidate_slots`, `unmatched_component_workload` and a source/parameter receipt. No imports of oracle, solver, repair, synthesis or model-provider modules are needed. Graph construction and exact set/feature counting are allowed only under that later input-screen release; this document has not run them.

Acceptance means correct provenance, complete prescribed coverage, defined exact arithmetic and no outcome-conditioned exclusions. It does **not** require a minimum number of aliases, reversals or anticipated gains. Root should first see the unfiltered census, then state the supported research scope. Large weighted data can support a recurring-structure study while providing little or no exact-quotient trigger; that is a legitimate mechanism boundary rather than a reason to redesign source rewards.

## Read-only basis

Inspected existing definitions: `cipheur/model.py` (`available`, `temporal_graph`), `cipheur/programs.py` (`FEATURES`, feature semantics), `cipheur/graph_features.py` (typed primitives and ID-tied summaries), `paper/sections/method.tex` (exact quotient/cancellation scope), `scripts/prepare_c3_interval_inputs_v06.py` (legacy-versus-interval separation), `V07_RECURRING_STRUCTURE_SCENARIO_CONTRACT.md` and `V07_LARGE_SCALE_STUDY_DESIGN_DRAFT.md`. C3's new numerical window proposal is owned by the separate data agent and requires its own provenance. No actual graph screen, label inventory, candidate program or optimizer outcome was loaded for this specification.
