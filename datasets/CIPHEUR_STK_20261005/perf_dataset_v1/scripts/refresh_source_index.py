"""Register the fixed VAL/TEST physical sources without changing old indexes.

Only physical provenance and completion status are recorded. This command does
not create labels, run a scoring program, choose configurations, or access
schedule-performance results.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PERF_ROOT = Path(__file__).resolve().parents[1]
ROOT = PERF_ROOT.parent
SCENES = ("CP-AU-r006", "CP-AP-r006", "CP-AU-r008", "CP-AP-r008", "CP-AU-r009", "CP-AP-r009")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parameter_path = ROOT / "source_plan" / "CIPHEUR_parameters.json"
    parameters = json.loads(parameter_path.read_text(encoding="utf-8-sig"))
    scenes = {s["scene_id"]: s for s in parameters["scene_definitions"]}
    entries = []
    for name in SCENES:
        scene = scenes[name]
        folder = ROOT / "raw" / name
        entry = {"scene_id": name, "source_group": scene["source_group"],
                 "split": scene["split"], "geometry_id": scene["geometry_id"],
                 "replicate_id": scene["replicate_id"], "epoch_utc": scene["epoch_utc"],
                 "horizon_stop_utc": scene["horizon_stop_utc"],
                 "raw_relative_path": str(folder.relative_to(ROOT)).replace("\\", "/"),
                 "physical_status": "planned", "graphs_status": "planned",
                 "test_labels_or_scores_generated_by_this_workflow": False}
        manifest_path = folder / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry.update(physical_status=manifest["status"], manifest_sha256=sha(manifest_path))
            for field in ("pairs_completed", "pairs_total", "contact_count", "boundary_records",
                          "raw_interval_count", "crossing_horizon_count", "elapsed_seconds", "started_at",
                          "finished_at", "formal_dataset", "eop_sha256", "generator_sha256",
                          "eop_loaded_covers_padded_propagation", "eop_actual_table_matches_source",
                          "owned_stk_instance_closed", "contacts_sha256"):
                if field in manifest:
                    entry[field] = manifest[field]
        graph_manifest_path = PERF_ROOT / "graphs" / name / "manifest.json"
        if graph_manifest_path.exists():
            graph_manifest = json.loads(graph_manifest_path.read_text(encoding="utf-8"))
            if graph_manifest["raw_manifest_sha256"] != entry.get("manifest_sha256"):
                raise RuntimeError(f"Graph/raw provenance differs: {name}")
            entry.update(graphs_status=graph_manifest["status"],
                         graphs_relative_path=str(graph_manifest_path.parent.relative_to(ROOT)).replace("\\", "/"),
                         graph_manifest_sha256=sha(graph_manifest_path),
                         unique_graph_configurations_complete=graph_manifest["complete_configurations"])
        entries.append(entry)
    index = {
        "schema_version": "cipheur-perf-dataset-v1-physical-source-index",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "parameters_relative_path": "source_plan/CIPHEUR_parameters.json",
        "parameters_sha256": sha(parameter_path), "generator_relative_path": "scripts/stk_generate.py",
        "generator_sha256": sha(ROOT / "scripts" / "stk_generate.py"),
        "frozen_eop_relative_path": "source_dependencies/EOP-v1.1.txt",
        "frozen_eop_sha256": sha(ROOT / "source_dependencies" / "EOP-v1.1.txt"),
        "new_independent_source_group_count": 3,
        "source_group_policy": "AU/AP companion geometries and all constraint configurations from one replicate stay in the same split; six libraries are three source groups.",
        "test_access_policy": "Physical generation, provenance and input quality checks only before root freezes every scoring program. No TEST evidence labels, tuning or performance-score exposure by this workflow.",
        "existing_training_source_ids": ["CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001"],
        "original_indexes_modified": False, "sources": entries,
    }
    path = PERF_ROOT / "source_index.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(json.dumps({"index": str(path), "physical_statuses": {e["scene_id"]: e["physical_status"] for e in entries}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
