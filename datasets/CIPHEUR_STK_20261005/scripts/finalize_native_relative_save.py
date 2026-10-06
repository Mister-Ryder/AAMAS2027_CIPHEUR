"""Finish the first pilot after STK already serialized a relative EOP name.

This repairs only the original generator's overly strict path guard. It never
regenerates, changes or truncates contacts, nor recomputes any Access queries.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from stk_generate import ROOT, PARAMETERS, EOP_SOURCE, EOP_PORTABLE_NAME, eop_verify, now, sha, write_json
from open_saved_scene import staged_copy


def main():
    out = ROOT / "raw" / "CP-AU-r000"
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if m.get("status") != "failed" or m.get("error") != "Native saved scenario has an unexpected EOP file reference":
        raise RuntimeError("Finalizer is limited to the identified native-relative-EOP guard failure")
    if m.get("pairs_completed") != 1008 or not m.get("formal_dataset"):
        raise RuntimeError("Physical generation must already be complete and formal")
    if m.get("eop_sha256") != sha(EOP_SOURCE):
        raise RuntimeError("Frozen EOP SHA mismatch")
    if not all((out / f).is_file() for f in ["contacts.csv", "contacts_boundary.csv", "access_raw.csv",
        "provider_reports.jsonl", "sampling_spot_check.json", "precision_receipt.json", "actual_geometry.json"]):
        raise RuntimeError("Complete generation artifacts are required")
    spots = json.loads((out / "sampling_spot_check.json").read_text(encoding="utf-8"))
    if not all(s["same_interval_count"] for s in spots["samples"]):
        raise RuntimeError("Fixed 15s spot checks did not pass")
    shutil.copy2(out / "manifest.json", out / "postprocess_failure_manifest.json")
    scene_dir = out / "scene"
    scene_file = scene_dir / "CP_AU_r000.sc"
    text = scene_file.read_text(encoding="ascii")
    if "EOPFilename     " + EOP_PORTABLE_NAME not in text:
        raise RuntimeError("Native save is not the expected already-relative EOP form")
    if sha(scene_dir / EOP_PORTABLE_NAME) != sha(EOP_SOURCE):
        raise RuntimeError("Portable EOP differs from actual simulation input")
    oldstage = Path(m["owned_ascii_scene_staging_directory"])
    if any(str(oldstage).encode("ascii") in p.read_bytes() for p in scene_dir.rglob("*") if p.is_file()):
        raise RuntimeError("Final scene contains a temporary-path dependency")
    write_json(out / "scene_portability_receipt.json", {"all_native_scene_files_and_subdirectories_copied": True,
        "native_serializer_already_used_relative_eop_reference": True,
        "only_native_change": "None; the native serializer already made its EOP path relative",
        "eop_portable_filename": EOP_PORTABLE_NAME, "eop_sha256": sha(scene_dir / EOP_PORTABLE_NAME),
        "unresolved_temporary_path_references": [], "original_native_save": "native_save_original.sc",
        "final_scene": str(scene_file)})
    p = json.loads(PARAMETERS.read_text(encoding="utf-8"))
    definition = next(s for s in p["scene_definitions"] if s["scene_id"] == "CP-AU-r000")
    stage = Path(tempfile.mkdtemp(prefix="CP_AU_r000_reload_", suffix="_CIPHEUR_STK"))
    staged_sc, eop = staged_copy(scene_dir, stage)
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.DispatchEx("STK11.Application")
        app.Visible = False
        app.UserControl = False
        pid = int(app.ProcessID)
        root = app.Personality2
        root.LoadScenario(str(staged_sc))
        root.UnitPreferences.SetCurrentUnit("DateFormat", "UTCG")
        root.UnitPreferences.SetCurrentUnit("AngleUnit", "deg")
        root.UnitPreferences.SetCurrentUnit("TimeUnit", "sec")
        eop_after = eop_verify(root, definition, eop)
        loaded = root.CurrentScenario
        counts = {}
        for i in range(loaded.Children.Count):
            typ = str(loaded.Children.Item(i).ClassName)
            counts[typ] = counts.get(typ, 0) + 1
        if counts != {"Satellite": 84, "Facility": 12}:
            raise RuntimeError("Reloaded portable scene has wrong object counts")
        write_json(out / "pilot_portable_reload.json", {"status": "success", "owned_stk_process_id": pid,
            "new_ascii_staging_directory": str(stage), "object_counts": counts,
            "eop_loaded_after_helper_explicit_staged_reference": eop_after,
            "verification": "Complete saved scene/dependencies reloaded once; helper maps frozen local EOP to the new ASCII staging path; no Access recomputation."})
    finally:
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()
        if stage.resolve().parent == Path(tempfile.gettempdir()).resolve() and stage.name.endswith("_CIPHEUR_STK"):
            shutil.rmtree(stage)
    write_json(out / "native_relative_save_finalization.json", {"finished_at": now(),
        "scope": "Guard repair and the planned single portable reload only; all contacts preserved unchanged",
        "original_failure_manifest": "postprocess_failure_manifest.json", "finalizer_sha256": sha(Path(__file__))})
    files = [{"path": str(f.relative_to(out)), "size_bytes": f.stat().st_size, "sha256": sha(f)}
        for f in sorted(out.rglob("*")) if f.is_file() and f.name != "manifest.json"]
    m.update(status="success", finished_at=now(), contacts_sha256=sha(out / "contacts.csv"),
        scene_file=str(scene_file), files=files, full_visibility_intervals=True,
        no_minimum_duration_filter=True, no_legacy_input_used=True,
        postprocess_guard_repaired=True, planned_portable_reload_completed=True)
    # Counts are derived from the saved full tables, without another simulation.
    import csv
    with (out / "contacts_boundary.csv").open(encoding="utf-8", newline="") as f:
        boundaries = list(csv.DictReader(f))
    m["boundary_records"] = len(boundaries)
    m["crossing_horizon_count"] = sum(r["crosses_horizon"] == "True" for r in boundaries)
    with (out / "access_raw.csv").open(encoding="utf-8", newline="") as f:
        m["raw_interval_count"] = sum(1 for _ in csv.DictReader(f))
    if oldstage.resolve().parent == Path(tempfile.gettempdir()).resolve() and oldstage.name.endswith("_CIPHEUR_STK"):
        shutil.rmtree(oldstage)
        m["owned_ascii_scene_staging_removed_after_complete_copy"] = True
    write_json(out / "manifest.json", m)
    print(json.dumps({"scene_id": m["scene_id"], "status": m["status"], "contact_count": m["contact_count"]}), flush=True)


if __name__ == "__main__":
    main()
