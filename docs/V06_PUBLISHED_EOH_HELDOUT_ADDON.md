# Separate EoH held-out addon

This is a new outcome-free registration, not a revision of R2 or an EoH result. Its construction read only frozen source, static metadata/configurations and hashes; it did not read evolving EoH calls/fitness, final selected programs, original withheld graph contents or certificates. The static registration is `experiments/discovery/v06_published_eoh_heldout_addon_001`. The only new execution module is `cipheur/heldout_published_eoh_v06.py`; it does not import the EoH discovery implementation, request a model, select a program or call a certificate oracle.

The requested frame is **four frozen EoH quality pipeline positions × all72 original states × original plus five existing bijections =1,728 state assignments**, grouped into24 identity/variant jobs. The original27 R2 roles, policies and control identities are unchanged. Use their already assigned original/five-relabel control measurements; do not execute extra controls for this addon. Same source-cluster salt `V06_RELABEL_ROBUSTNESS_20261004_001`, paired-context mapping, certificate transport, 0.5nominal-wall repair, all node/work/patch caps and actual-time accounting apply. Only the corresponding typed certificate vertex fields are transported; exact interval strings remain numbers.

The four output identities are `published_EoH_DSL_quality:run_0` through `run_3`. Their final bank is `experiments/discovery/v06_published_eoh_001/selection.json`, version `v06_published_EoH_DSL_TRAIN_quality_selection_001`. All32 original author positions, failures and four seed-fitness observations must be frozen and independently audited first. A pipeline may legitimately retain its initial shared R1 warm seed under the registered published objective-population rule: report `winner_origin=shared_R1_warm_seed`, not successful newly authored improvement. Genuine authored origin must name an original same-run slot. Missing output remains null for all432 assigned state positions; do not fabricate zero fit/reward/work/time, use a Degree fallback, drop it or replace it with a different quality comparator. Equal ASTs retain separate pipeline identities and measured executions.

## Two-stage root release

First, issue the **main R2 root release only after complete EoH final-bank/author/TRAIN audit freeze**, before the first original72 TEST certificate query. In addition to the existing R2 fields, bind:

```json
{
  "published_EoH_all32_and4_seed_fitness_frozen_before_TEST": true,
  "published_EoH_addon_registration_sha256": "STATIC_ADDON_FREEZE_RECEIPT_BYTE_SHA256",
  "published_EoH_selection_sha256": "FINAL_FOUR_POSITION_BANK_BYTE_SHA256",
  "published_EoH_authoring_audit_sha256": "INDEPENDENT_AUTHOR_AUDIT_BYTE_SHA256",
  "published_EoH_TRAIN_audit_sha256": "INDEPENDENT_TRAIN_AUDIT_BYTE_SHA256",
  "published_EoH_addon_source_sha256": "REPLACE_WITH_MODULE_SOURCE_HASHES_OBJECT"
}
```

The source field must be an object, not a string. EoH selection must bind its original protocol and root authoring release SHA `6f3a7059c92bebbf2905cdf51a9eda681a73d8990f3f254fc567c3b461ad9c35`. Both independent EoH audits require positive `checks` (integer or a dictionary of integer counts), `errors=0` or `[]`, `audit_phase=authoring`/`train`, exact `selection_sha256`, `protocol_sha256`, `root_authoring_release_sha256`, `all32_positions_frozen=true` and `TEST_accessed=false`. Independent audits verify the real four seed observations and all32 original positions; the addon cannot manufacture these audits.

Second, after certificate generation and original R2 preparation, root may issue **`v06_published_EoH_root_TEST_addon_release_001`**, before the addon reads any prepared TEST labels or executes any policy. This later receipt binds the actual parent registration/certificates indirectly through the prepared R2 freeze; it has no circular future-output hash. Required flags:

```json
{
  "version": "v06_published_EoH_root_TEST_addon_release_001",
  "issued_by": "root",
  "allow_TEST": true,
  "before_any_addon_TEST_label_read_or_programme_evaluation": true,
  "EoH_bank_and_audits_frozen_before_original_TEST_queries": true,
  "all32_author_positions_and4_seed_fitness_frozen": true,
  "independent_EoH_author_and_TRAIN_audits_zero_errors": true,
  "requested_published_identities": 4,
  "original_R2_27_identities_roles_hashes_unchanged": true
}
```

Add scalar byte-hash fields `addon_registration_sha256` (static freeze), `R2_registration_freeze_sha256`, `EoH_selection_sha256`, `EoH_authoring_audit_sha256`, `EoH_TRAIN_audit_sha256`, `EoH_protocol_sha256`, `EoH_author_release_sha256`, `original_data_sha256`, `original_query_protocol_sha256`, `R2_root_release_sha256`, `R2_selection_sha256`, and an object `addon_source_sha256` equal to the module's complete source-hash dictionary. Preparation checks this release before prepared TEST input/label reads, then checks the original main receipt contains the same EoH freeze bindings. It copies parent records, signed labels and five mapping inventories byte-for-byte; the parent directory is never written.

## Commands and source closure

Static registration already exists. Its creation command was:

```text
python -B -m cipheur.heldout_published_eoh_v06 register --config configs/heldout_published_eoh_v06_001.json --eoh-study experiments/discovery/v06_published_eoh_001 --evidence-plan experiments/discovery/v06_evidence_001 --r2-relabel-config configs/relabel_refinement_v06_002.json --out experiments/discovery/v06_published_eoh_heldout_addon_001
```

Future server-only preparation, after both releases and independent EoH audits:

```text
python -B -m cipheur.heldout_published_eoh_v06 prepare --registration <STATIC_ADDON_DIRECTORY> --registration-sha256 <STATIC_FREEZE_SHA> --r2-registration <PREPARED_ORIGINAL_R2_DIRECTORY> --r2-freeze-sha256 <R2_FREEZE_SHA> --selection <FINAL_EOH_SELECTION_JSON> --selection-sha256 <EOH_SELECTION_SHA> --authoring-audit <INDEPENDENT_AUTHOR_AUDIT> --train-audit <INDEPENDENT_TRAIN_AUDIT> --root-release <ADDON_ROOT_RECEIPT> --root-release-sha256 <ADDON_ROOT_SHA> --out <NEW_PREPARED_ADDON_DIRECTORY>
python -B -m cipheur.heldout_published_eoh_v06 run --registration <NEW_PREPARED_ADDON_DIRECTORY> --registration-sha256 <ITS_FREEZE_BYTE_SHA> --out <NEW_ADDON_RESULT_DIRECTORY> --root-release-sha256 <ADDON_ROOT_SHA>
```

Source closure is exactly the unchanged original helper closure, unchanged R2 adapter/selector, plus the new addon module (13package files); all are copied/hash-bound in the static registration. Build a server capsule with these files at `cipheur/<name>`, the static registration and final bank/audits/releases, plus the prepared R2 registration. Do not import or package evolving EoH authoring workspaces as runtime dependencies. All research preparation/execution is Linux-only, standard-library runtime; overwriting registration or output paths is rejected. Missing slots do not invoke diagnostics or search. Normal feasible cap-stop incumbents remain results; errors stay explicit.

## Reporting limits and validation

Report all four origins, all requested/scorable/missing assignments, complete-feasible/error/cap coverage, exact macro reward divided by total graph weight, actual primitive work and time. Total graph weight is neither an optimum nor a best-method denominator. Retain every strict/tie/unknown query and shortfall. Full declared/demanded quotient obstruction and actual strict/base-alias scalar margin fit are **postfreeze diagnostics**, never an EoH population/fitness criterion. Report original and allfive relabel fit/quality measurements, mean and worst with absent measurements retained. Source clusters, paired endpoints and relabels determine dependence; four pipeline outputs are not independent test instances.

The discovery baseline is the registered **bounded, seeded EoH-DSL prototype**, with original32 genuine author attempts and quality-only published population management. It is not a faithful unrestricted native EoH reproduction. R1 label-selected warm-seed history remains disclosed even though subsequent EoH fitness feedback is label-free. W-joint versus EoH compares complete pipelines with different evidence, selection and authoring budgets; it cannot isolate model superiority or a pure witness cause. Shared classical initialization/repair receives no LLM-specific novelty credit. No success, advantage or held-out result is claimed by this registration.

Twelve fabricated tests pass: duplicate/seed/authored/null identity handling, unchanged32 slots, no gate requirement, positive independent audit bindings, root flags/source/selection integrity, main-before-original-TEST proof, rejected release before TEST reads, byte-preserved original72-state parent/mapping inventory, overwrite refusal, no inference for null slots and actual tiny shared-kernel execution. Tests read only fabricated metadata/tiny graphs and frozen static configurations; they do not read genuine withheld graphs/certificates or EoH outcomes. Command: `python -B -m unittest tests.test_heldout_published_eoh_v06 -v`.
