# Frozen performance and subsequent mechanism diagnostics

The original V003 performance batch was launched once on the provided cloud
server on 4 October 2026, under the original four-hour batch guard, eight
workers, all three nominal targets and both initialization tracks. Its
52,548 requested assignments and 302 input contexts remain unchanged.
`experiments/discovery/v06_test_release_002/performance_server_identity_staging_launch.json`
records the original launcher and exact post-TRAIN identity capsule. The
scientific source hashes and original input freeze were checked before launch.
No runtime source was modified to improve an observed result or reduce storage.

The operational `scripts/run_postperformance_assays_v06.py` waits until the
performance launcher and worker have terminated, including archive creation.
It then attempts each already released assay once, sequentially:

1. R2: 27 frozen identities × 72 original states × original/five renamings,
   totaling 11,664 state assignments.
2. EoH addon: four frozen pipeline identities on the same states/renamings,
   totaling 1,728 state assignments, using the original R2 control observations.
3. TRAIN restricted-patch bridge: all 23 frozen identities × all 120 original
   Degree-derived patches. All original 19 draft entries remain unchanged;
   all four EoH pipeline origins are retained in the new final inventory.

Waiting and sequencing prevent competing solver workloads during the primary
timing comparison. Each assay keeps its original scientific budgets, sources,
registrations, programmes and labels. The wrapper adds no further timeout or
retry and invokes no LLM or original full TEST certificate query. The bridge's
separately registered local TRAIN certificates are used only for postfreeze
diagnosis, not authoring, selection or online inference.

The wrapper records the dependency receipt, commands, starts, exits and full
logs. It archives complete raw result directories and prepared registrations,
including partial observations if a command fails. A failed command is not
silently replaced, retried, or converted to a zero reward. The original
performance guard's assigned but unreturned rows also remain explicit.

The final TRAIN bridge inventory and capsule are, respectively,
`experiments/discovery/v06_patch_bridge_programs_frozen_001/program_inventory.json`
and `experiments/source_snapshots/v06/v06_TRAIN_patch_bridge_execution_001.zip`.
The nineteen-entry draft remains preserved independently. Current launch and
queue records are execution provenance, not evidence of an algorithmic gain.
