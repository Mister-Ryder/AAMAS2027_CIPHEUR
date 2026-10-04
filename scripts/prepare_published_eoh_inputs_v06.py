"""Prepare the distinct, outcome-free published EoH TRAIN capsule; never execute it."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Graph
from cipheur.published_eoh_v06 import (ORIGINAL_RUNTIME_SHA256, canonical, digest,
    grammar_contract, prepare, read, reject_labels, source_hashes, validate_records, write)
from scripts.author_matched_cli_v06 import CLI, safe_configuration

SOURCE_STUDY = ROOT / "experiments/discovery/v06_refinement_draft_003"
EXPECTED_EVIDENCE = "762fc25046eeb13f49044b96c5d74b7136dedcc363e1fec81809bcc83aa62913"
EXPECTED_SEED_RECEIPT = "7067d4237f2e5df54216727fba33059724ad71cb28c226c1af011e9fea43065b"
EXPECTED_R1_SEED = "a278615e138562aef69ca7e09512db01e725779e7b3186829682038518b1913b"
EXPECTED_SEED = "83dc9ce30a4d7ff8c529c36d33b3aa4d47276480a88da3ca4bc6a48b391c156c"
EXPECTED_KERNEL = "3587db7ba52fe9f21f0171600fee120e5598b551ed06bbe674e7d0cb38e3cb4b"
FIELDS = ("id", "split", "family", "cluster", "graph", "graph_digest", "fixed", "excluded")
SALT = "v06_author_packet_metadata_only_001"
SERVER = "/root/autodl-tmp/aamas2027_v06_published_eoh_001"
PYTHON = "/root/autodl-tmp/aamas2027_v03/py311/bin/python"


def metadata_examples(records):
    """Reuse the original registered metadata rule without reading query/label values."""
    order = lambda identity: sha256((SALT + "|" + identity).encode()).digest()
    chosen = []
    for family in ("DIMACS", "SATLIB"):
        chosen.extend(sorted((r for r in records if r["family"] == family),
                             key=lambda r: order(r["cluster"]))[:3])
    for family in sorted({r["family"] for r in records if r["paired"]}):
        rows = [r for r in records if r["family"] == family]
        cluster = min({r["cluster"] for r in rows}, key=order)
        chosen.extend(sorted((r for r in rows if r["cluster"] == cluster), key=lambda r: r["side"]))
    if len(chosen) != 18 or len({r["id"] for r in chosen}) != 18:
        raise ValueError("Original metadata-selected18-state frame changed")
    return chosen


def build(inputs, study):
    inputs, study = Path(inputs).resolve(), Path(study).resolve()
    if inputs.exists() or study.exists():
        raise ValueError("Never overwrite a preparation namespace or receipt")
    evidence_path = SOURCE_STUDY / "training_evidence.json"
    seed_path = SOURCE_STUDY / "seed_selection.json"
    kernel_path = ROOT / "configs/repair_train_v06_001.json"
    expected = {evidence_path: EXPECTED_EVIDENCE, seed_path: EXPECTED_SEED_RECEIPT,
                kernel_path: EXPECTED_KERNEL}
    for path, wanted in expected.items():
        if digest(path) != wanted:
            raise ValueError("Original prepared input changed: " + str(path))
    prototype_path = ROOT / "manifest/PUBLISHED_EOH_PROTOTYPE_SOURCE_FREEZE.json"
    prototype = read(prototype_path)
    for path, wanted in {**prototype["owned_artifact_sha256"],
                         **prototype["bound_runtime_source_sha256"]}.items():
        if digest(ROOT / path) != wanted:
            raise ValueError("Independent prototype source freeze changed: " + path)
    for path, wanted in ORIGINAL_RUNTIME_SHA256.items():
        if digest(ROOT / "cipheur" / path) != wanted:
            raise ValueError("Original eight-file scientific runtime changed")
    r2_binding_path = SOURCE_STUDY / "transport_runtime_binding.json"
    r2_binding = read(r2_binding_path)
    r2_protocol = read(SOURCE_STUDY / "draft_protocol.json")
    if (r2_protocol["training_evidence_sha256"] != EXPECTED_EVIDENCE
        or r2_protocol["seed_selection_sha256"] != EXPECTED_SEED_RECEIPT
        or r2_protocol["kernel_config_sha256"] != EXPECTED_KERNEL
        or r2_binding["draft_protocol_sha256"] != digest(SOURCE_STUDY / "draft_protocol.json")
        or r2_binding["preparation_receipt_sha256"] != digest(SOURCE_STUDY / "preparation_receipt.json")
        or r2_binding["transport_helper_sha256"] != digest(ROOT / "scripts/author_matched_cli_v06.py")
        or r2_binding["requested_configuration"] != safe_configuration()
        or r2_binding["cli_executable_sha256"] != digest(CLI)):
        raise ValueError("Current R2 TRAIN/seed/requested-native-transport binding changed")
    old_seed = read(seed_path)
    r1_seed = FeatureRuleProgram.from_dict(old_seed["seed_program"]).to_dict()
    packet_path = SOURCE_STUDY / "packets/block_0_objective.json"
    seed = FeatureRuleProgram.from_dict(read(packet_path)["shared_seed_program"]).to_dict()
    if (canonical(r1_seed) != EXPECTED_R1_SEED or r1_seed != old_seed["seed_program"]
        or canonical(seed) != EXPECTED_SEED or seed != read(packet_path)["shared_seed_program"]
        or old_seed["selection_split"] != "train" or old_seed["test_accessed"] is not False
        or digest(packet_path) != r2_protocol["packet_sha256"]["packets/block_0_objective.json"]
        or seed["features"] != r1_seed["features"] or seed["rule"] != r1_seed["rule"]):
        raise ValueError("Warm seed differs from the original R2 author packet")
    for name, expected_sha in r2_protocol["packet_sha256"].items():
        if name.endswith(".json"):
            path = SOURCE_STUDY / name
            if digest(path) != expected_sha or read(path)["shared_seed_program"] != seed:
                raise ValueError("All15 original R2 author packets must have the same warm seed")
    original = read(evidence_path)["records"]
    pure = [{key: record[key] for key in FIELDS} for record in original]
    validate_records(pure)
    for record in pure:
        graph = Graph.from_dict(record["graph"])
        if (not set(record["fixed"]) <= graph.nodes.keys()
            or not set(record["excluded"]) <= graph.nodes.keys()
            or set(record["fixed"]) & set(record["excluded"])
            or not graph.feasible(record["fixed"])):
            raise ValueError("Original fixed/excluded boundary changed")
    selected = metadata_examples(original)
    r1_protocol_path = ROOT / "experiments/discovery/v06_authoring_001/protocol.json"
    r1_protocol = read(r1_protocol_path)
    r1_packet_path = ROOT / "experiments/discovery/v06_authoring_001/packets/block_0_objective.json"
    original_builder = ROOT / "scripts/prepare_synthesis_v06.py"
    if (digest(original_builder) != r1_protocol["source_sha256"]["builder"]
        or digest(r1_packet_path) != r1_protocol["packet_sha256"]["packets/block_0_objective.json"]):
        raise ValueError("Original metadata-only example registration changed")
    old_examples = read(r1_packet_path)["examples"]
    for number, (record, example) in enumerate(zip(selected, old_examples, strict=True)):
        graph = Graph.from_dict(record["graph"])
        mapping = {node: f"n{i:03d}" for i, node in enumerate(sorted(graph.nodes))}
        masked = {"name": f"case_{number:02d}",
            "nodes": [{"id": mapping[v], "weight": graph.nodes[v].weight,
                       "duration": graph.nodes[v].end - graph.nodes[v].start} for v in sorted(graph.nodes)],
            "edges": [[mapping[a], mapping[b]] for a, b in sorted(graph.edges)],
            "constraints": graph.constraints}
        if masked != example["graph"] or record["family"] != example["stratum"]:
            raise ValueError("Metadata-only18 examples differ from the original registration")
    lookup = {r["id"]: r for r in pure}
    context = {"task": "Synthesize a typed structural-feature and numeric-ranking heuristic for maximum-weight independent-set repair, starting from the shared warm seed. Use permitted polynomial operations on the current active graph; fixed vertices remain selected and excluded vertices unavailable. Maximize equal-family complete-schedule reward divided by total graph weight under the unchanged 0.5-second wall/200000-work repair budget. Program priority influences only the feasible greedy proposal and pivot. Do not use ID or benchmark lookup, external state, imports, model or oracle calls. Name/rationale describe the thought; features/rule execute.",
        "typed_grammar": grammar_contract(), "TRAIN_examples": [lookup[r["id"]] for r in selected]}
    reject_labels(context)
    execution = {"version": "v06_published_EoH_fixed_wave_execution_amendment_001",
        "approved_by": "root", "approved_before_any_published_call_or_fitness": True,
        "waves": [[0, 1], [2, 3]], "max_concurrent_local_author_calls": 2,
        "fitness_transactions_serialized": True, "workers_per_fitness_transaction": 8,
        "maximum_total_fitness_workers": 8, "seed_fitness_order_within_wave": "run ascending",
        "candidate_fitness_order_within_wave": "slot ascending, then run ascending",
        "next_slot_requires_previous_hash_bound_feedback_ingested": True,
        "new_wave_requires_previous_wave_positions_disposed": True,
        "adaptation_scope": "Execution occupancy only; all32fixed original positions/operators/RNG streams and quality-only population semantics unchanged",
        "supersedes": "Prototype documentation's serial fixed run order, disclosed before any actual authoring/fitness",
        "server_project_root": SERVER, "server_python": PYTHON}
    inputs.mkdir(parents=True)
    provenance = {"source_TRAIN_evidence_sha256": EXPECTED_EVIDENCE,
        "source_R1_seed_selection_sha256": EXPECTED_SEED_RECEIPT,
        "source_R2_preparation_receipt_sha256": digest(SOURCE_STUDY / "preparation_receipt.json"),
        "source_R2_draft_protocol_sha256": digest(SOURCE_STUDY / "draft_protocol.json"),
        "source_R2_transport_binding_sha256": digest(r2_binding_path),
        "source_R2_seed_packet_sha256": digest(packet_path),
        "original_R1_seed_program_sha256": EXPECTED_R1_SEED,
        "author_visible_R2_seed_program_sha256": EXPECTED_SEED,
        "R1_to_R2_seed_difference": "Only name/rationale metadata: R2 uses shared_seed_v06r2 with blank rationale; executable features/rule identical",
        "prototype_source_freeze_sha256": digest(prototype_path),
        "input_preparation_source_sha256": digest(__file__),
        "original_metadata_example_builder_sha256": digest(original_builder),
        "original_metadata_example_packet_sha256": digest(r1_packet_path),
        "original_kernel_configuration_sha256": EXPECTED_KERNEL}
    write(inputs / "train_inputs.json", {"version": "v06_published_EoH_pure_TRAIN_problem_inputs_001",
        "records": pure, "source_binding": provenance})
    write(inputs / "seed.json", {"program": seed, "program_sha256": EXPECTED_SEED,
        "source_candidate_id": old_seed["seed_source_id"], "TRAIN_label_selected_history": True,
        "R1_seed_selection_sha256": EXPECTED_SEED_RECEIPT,
        "original_R1_seed_program_sha256": EXPECTED_R1_SEED,
        "exact_author_visible_R2_seed_preserved": True})
    write(inputs / "common_context.json", context)
    write(inputs / "execution_plan.json", execution)
    write(inputs / "transport_binding.json", {"version": "v06_published_EoH_native_transport_binding_001",
        "requested_configuration": r2_binding["requested_configuration"],
        "cli_executable_sha256": r2_binding["cli_executable_sha256"],
        "authoring_transport_sha256": digest(ROOT / "scripts/author_published_eoh_cli_v06.py"),
        "transport_helper_sha256": r2_binding["transport_helper_sha256"],
        "source_binding": provenance, "execution_plan": execution,
        "execution_plan_sha256": digest(inputs / "execution_plan.json"),
        "served_model_not_inferred_from_requested_settings": True})
    shutil.copyfile(kernel_path, inputs / "kernel_config.json")
    shutil.copyfile(ROOT / "configs/published_eoh_v06_001.json", inputs / "config.json")
    write(inputs / "input_validation.json", {"version": "v06_published_EoH_input_validation_001",
        "source_binding": provenance, "allowed_record_fields": list(FIELDS),
        "states": 120, "family_counts": dict(sorted(Counter(r["family"] for r in pure).items())),
        "original_projection_byte_values_preserved": True, "graph_digest_and_F_X_checked": True,
        "metadata_example_salt": SALT, "example_states": [r["id"] for r in selected],
        "metadata_rule_matches_original_registered_builder": True,
        "information_values_not_used_for_examples_or_authors": True,
        "R2_response_or_candidate_outcomes_accessed": False, "TEST_accessed": False,
        "native_authoring_calls": 0, "seed_fitness_evaluations": 0})
    write(inputs / "freeze_receipt.json", {"version": "v06_published_EoH_preparation_inputs_freeze_001",
        "artifact_sha256": {p.name: digest(p) for p in sorted(inputs.iterdir()) if p.is_file()}})
    prepare(inputs / "config.json", inputs / "seed.json", inputs / "common_context.json",
            inputs / "train_inputs.json", inputs / "kernel_config.json", inputs / "transport_binding.json", study)
    registration = {"version": "v06_published_EoH_actual_preparation_registration_001",
        "prepared_utc": datetime.now(timezone.utc).isoformat(), "status": "PREPARED_AWAITING_ROOT_AUTHORING_RELEASE",
        "inputs_relative_path": str(inputs.relative_to(ROOT)).replace("\\", "/"),
        "study_relative_path": str(study.relative_to(ROOT)).replace("\\", "/"),
        "source_binding": provenance, "input_freeze_sha256": digest(inputs / "freeze_receipt.json"),
        "protocol_sha256": digest(study / "protocol.json"),
        "study_freeze_receipt_sha256": digest(study / "freeze_receipt.json"),
        "execution_plan_sha256": digest(inputs / "execution_plan.json"),
        "shared_R1_warm_seed_sha256": EXPECTED_SEED,
        "R1_seed_selection_sha256": EXPECTED_SEED_RECEIPT,
        "requested_positions": 32, "maximum_schedule_assignments_including_four_seed_fitness": 4320,
        "maximum_summed_nominal_kernel_seconds": 2160,
        "nominal_time_is_not_actual_wall_ETA": True,
        "source_closure_files": sorted(source_hashes()),
        "authoring_calls": 0, "fitness_evaluations": 0, "TEST_accessed": False,
        "root_authoring_release_created": False, "prototype_freeze_preserved": True,
        "R2_samples_roles_selectors_and_receipts_preserved": True,
        "root_release_must_also_bind_this_registration_and_execution_plan": True}
    write(study / "preparation_registration.json", registration)
    archive = study.parent / (study.name + "_preparation_capsule.zip")
    if archive.exists():
        raise ValueError("Never overwrite a source/input capsule")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(source_hashes()):
            z.write(ROOT / rel, rel)
        z.write(__file__, "scripts/prepare_published_eoh_inputs_v06.py")
        for directory in (inputs, study):
            for path in sorted(directory.rglob("*")):
                if path.is_file(): z.write(path, str(path.relative_to(ROOT)).replace("\\", "/"))
    summary = {"prepared_study": str(study), "protocol_sha256": registration["protocol_sha256"],
        "freeze_receipt_sha256": registration["study_freeze_receipt_sha256"],
        "preparation_registration_sha256": digest(study / "preparation_registration.json"),
        "execution_plan_sha256": registration["execution_plan_sha256"],
        "capsule": str(archive), "capsule_sha256": digest(archive),
        "authoring_calls": 0, "fitness_evaluations": 0, "TEST_accessed": False}
    print(json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True); parser.add_argument("--study", required=True)
    arguments = parser.parse_args()
    build(arguments.inputs, arguments.study)
