"""Open a portable data scene through an owned ASCII STK 11 staging folder.

Run --interactive only when a human wants to edit the scene. Changes are
saved as a new scene revision in data; original simulation data is preserved.
Without --interactive, this is a read-only hidden load check and closes itself.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from stk_generate import ROOT, EOP_PORTABLE_NAME, cast, sha, write_json


def staged_copy(source, stage):
    shutil.copytree(source, stage, dirs_exist_ok=True)
    scenes = list(stage.glob("*.sc"))
    if len(scenes) != 1:
        raise ValueError("Scene directory must have exactly one native .sc")
    sc = scenes[0]
    eop = stage / EOP_PORTABLE_NAME
    if not eop.is_file():
        raise FileNotFoundError("Portable scene's frozen EOP dependency is absent")
    text = sc.read_text(encoding="ascii")
    text, count = re.subn(r"(?m)^(\s*EOPFilename\s+).*$", lambda m: m.group(1) + str(eop), text)
    if count != 1:
        raise RuntimeError("Native scenario must have one EOPFilename entry")
    sc.write_text(text, encoding="ascii")
    return sc, eop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_id", help="For example CP-AU-r000")
    parser.add_argument("--interactive", action="store_true", help="Open an editable owned visible STK window")
    args = parser.parse_args()
    original = ROOT / "raw" / args.scene_id
    assert original.resolve().is_relative_to((ROOT / "raw").resolve())
    manifest = json.loads((original / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "success" or not manifest.get("formal_dataset"):
        raise RuntimeError("Open helper only accepts a successful formal dataset scene")
    stage = Path(tempfile.mkdtemp(prefix="CIPHEUR_scene_open_", suffix="_CIPHEUR_STK"))
    if not str(stage).isascii():
        raise RuntimeError("STK11 requires an ASCII staging directory on this machine")
    sc, eop = staged_copy(original / "scene", stage)
    if sha(eop) != manifest["eop_sha256"]:
        raise RuntimeError("Scene EOP dependency differs from simulation manifest")
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.DispatchEx("STK11.Application")
        app.Visible = args.interactive
        app.UserControl = False
        root = app.Personality2
        root.LoadScenario(str(sc))
        earth = cast(root.CurrentScenario.EarthData, "IAgScEarthData")
        print(json.dumps({"loaded": str(sc), "frozen_eop_sha256": sha(eop),
            "owned_stk_process_id": int(app.ProcessID),
            "actual_loaded_eop": str(earth.EOPFilename), "eop_start": str(earth.EOPStartTime),
            "eop_stop": str(earth.EOPStopTime), "object_count": int(root.CurrentScenario.Children.Count)}, ensure_ascii=False), flush=True)
        if args.interactive:
            answer = input("Edit the scene in the owned STK window. Enter SAVE to save a new revision, or press Enter to close without saving: ")
            if answer == "SAVE":
                root.SaveScenarioAs(str(sc))
                revision = original / "scene_revisions" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                shutil.copytree(stage, revision)
                saved_sc = revision / sc.name
                saved_text = saved_sc.read_text(encoding="ascii").replace(str(eop), EOP_PORTABLE_NAME)
                saved_sc.write_text(saved_text, encoding="ascii")
                write_json(revision / "revision_receipt.json", {"source_dataset_manifest": str(original / "manifest.json"),
                    "purpose": "Human-editable scene revision; does not change frozen contacts or graph results",
                    "created_at": datetime.now(timezone.utc).isoformat(), "eop_sha256": sha(eop)})
                print(str(revision), flush=True)
    finally:
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()
        if stage.resolve().parent == Path(tempfile.gettempdir()).resolve() and stage.name.endswith("_CIPHEUR_STK"):
            shutil.rmtree(stage)


if __name__ == "__main__":
    main()
