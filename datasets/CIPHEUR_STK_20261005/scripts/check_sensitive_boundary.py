"""Check only the declared scene/gap near-boundary resource pair.

The original full library/graphs remain frozen. Two actual satellite-site
pairs are recomputed at max step 15s and time convergence 0.0001s, then matched
by the original contact midpoint; all raw refinement output is retained.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from stk_generate import ROOT, cast, sha, now, write_json, access_settings, extract_provider, get_intervals, ticks
from open_saved_scene import staged_copy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", default="CP-AP-r000")
    parser.add_argument("--gap", type=int, default=680)
    args = parser.parse_args()
    raw = ROOT / "raw" / args.scene
    source_manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    if source_manifest.get("status") != "success":
        raise RuntimeError("Source opportunity library must already be successful")
    graph_file = ROOT / "graphs" / args.scene / f"g{args.gap:04d}.json"
    g = json.loads(graph_file.read_text(encoding="utf-8"))
    diagnostic = g["stats"]["near_boundary_diagnostics"]["ground"]
    if diagnostic["near_boundary_pair_count"] != 1:
        raise RuntimeError("This check is scoped to exactly the one requested near-boundary pair")
    example = diagnostic["examples"][0]
    ids = [example["earlier_contact"], example["later_contact"]]
    with (raw / "contacts.csv").open(encoding="utf-8", newline="") as f:
        rows = {r["contact_id"]: r for r in csv.DictReader(f) if r["contact_id"] in ids}
    if set(rows) != set(ids):
        raise RuntimeError("Requested graph contact IDs absent from frozen opportunity table")
    out = ROOT / "analysis" / "boundary_sensitivity" / f"{args.scene}_g{args.gap:04d}"
    out.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "running", "started_at": now(), "scene_id": args.scene, "ground_gap_seconds": args.gap,
        "source_manifest_sha256": sha(raw / "manifest.json"),
        "frozen_contacts_sha256": sha(raw / "contacts.csv"), "source_graph_metadata_sha256": sha(graph_file),
        "eop_sha256": source_manifest["eop_sha256"], "scope": "Two actual object pairs only; no library or graph edits",
        "selected_boundary_example": example, "generator_sha256": sha(Path(__file__))}
    write_json(out / "manifest.json", receipt)
    stage = Path(tempfile.mkdtemp(prefix=args.scene.replace("-", "_") + "_boundary_", suffix="_CIPHEUR_STK"))
    sc, eop = staged_copy(raw / "scene", stage)
    if sha(eop) != source_manifest["eop_sha256"]:
        raise RuntimeError("Scene EOP differs from simulation source")
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.DispatchEx("STK11.Application")
        app.Visible = False
        app.UserControl = False
        receipt["owned_stk_process_id"] = int(app.ProcessID)
        root = app.Personality2
        root.LoadScenario(str(sc))
        root.UnitPreferences.SetCurrentUnit("DateFormat", "EpSec")
        root.UnitPreferences.SetCurrentUnit("TimeUnit", "sec")
        root.UnitPreferences.SetCurrentUnit("AngleUnit", "deg")
        refined = {}
        reports = []
        for ident in ids:
            row = rows[ident]
            satellite = root.GetObjectFromPath("Satellite/" + row["satellite_id"].replace("-", "_"))
            station = root.GetObjectFromPath("Facility/" + row["site_id"])
            access = satellite.GetAccessToObject(station)
            access.ClearAccess()
            access_settings(access, 15)
            adv = cast(access.Advanced, "IAgStkAccessAdvanced")
            adv.TimeConvergence = 0.0001
            actual = {k: getattr(adv, k) for k in ["MaxTimeStep", "TimeConvergence", "UsePreciseEventTimes", "UseFixedTimeStep", "EnableLightTimeDelay"]}
            if actual["MaxTimeStep"] != 15 or actual["TimeConvergence"] != 0.0001:
                raise RuntimeError("Refinement settings did not apply")
            access.ComputeAccess()
            data = extract_provider(access)
            intervals = get_intervals(data)
            midpoint = (Decimal(row["start_seconds"]) + Decimal(row["end_seconds"])) / 2
            matched = [(a, b, d) for a, b, d in intervals if Decimal(a) < midpoint < Decimal(b)]
            if len(matched) != 1:
                raise RuntimeError("Original contact midpoint does not identify one refined full interval")
            a, b, d = matched[0]
            refined[ident] = {"original_frozen": row, "raw_refined_start_seconds": a,
                "raw_refined_end_seconds": b, "refined_start_tick": ticks(a), "refined_end_tick": ticks(b),
                "start_difference_from_frozen_seconds": str(Decimal(a) - Decimal(row["start_seconds"])),
                "end_difference_from_frozen_seconds": str(Decimal(b) - Decimal(row["end_seconds"])),
                "actual_settings": actual}
            reports.append({"contact_id": ident, "actual_settings": actual, "data": data})
        gap = Decimal(args.gap)
        earlier, later = ids
        original_margin = Decimal(rows[later]["start_seconds"]) - Decimal(rows[earlier]["end_seconds"]) - gap
        refined_margin = Decimal(refined[later]["raw_refined_start_seconds"]) - Decimal(refined[earlier]["raw_refined_end_seconds"]) - gap
        refined_tick_margin = refined[later]["refined_start_tick"] - refined[earlier]["refined_end_tick"] - args.gap * 1000000
        result = {"contacts": refined, "original_frozen_margin_seconds": str(original_margin),
            "refined_raw_margin_seconds": str(refined_margin), "refined_tick_margin": refined_tick_margin,
            "original_ground_conflict": original_margin < 0, "refined_raw_ground_conflict": refined_margin < 0,
            "refined_tick_ground_conflict": refined_tick_margin < 0,
            "edge_classification_stable": (original_margin < 0) == (refined_margin < 0) == (refined_tick_margin < 0),
            "precision_note": "The tighter run is a numerical sensitivity check, not a rigorous physical timing error bound; original data/graph remain frozen."}
        write_json(out / "result.json", result)
        write_json(out / "refined_provider_reports.json", reports)
        if sha(raw / "contacts.csv") != receipt["frozen_contacts_sha256"] or sha(graph_file) != receipt["source_graph_metadata_sha256"]:
            raise RuntimeError("Frozen input changed during the sensitivity check")
        receipt.update(status="success", finished_at=now(), edge_classification_stable=result["edge_classification_stable"],
            files=[{"path": p.name, "sha256": sha(p), "size_bytes": p.stat().st_size}
                   for p in sorted(out.iterdir()) if p.is_file() and p.name != "manifest.json"])
        print(json.dumps({"status": "success", "original_margin_seconds": str(original_margin),
            "refined_margin_seconds": str(refined_margin), "edge_classification_stable": result["edge_classification_stable"]}), flush=True)
    except BaseException as exc:
        receipt.update(status="failed", error=str(exc), failed_at=now())
        raise
    finally:
        if app is not None:
            app.Quit()
            receipt["owned_stk_instance_closed"] = True
        pythoncom.CoUninitialize()
        if stage.resolve().parent == Path(tempfile.gettempdir()).resolve() and stage.name.endswith("_CIPHEUR_STK"):
            shutil.rmtree(stage)
        write_json(out / "manifest.json", receipt)


if __name__ == "__main__":
    main()
