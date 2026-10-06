"""Independent CIPHEUR P0 STK 11 generator; never attach to an existing STK.

Raw STK doubles are preserved as 17-digit round-trip decimal strings.  The
frozen numerical scheduling instance uses half-even microsecond endpoints,
with reward computed only as their difference. No window is sliced, shifted,
shortened, duplicated into antennas, filtered by length or given a new reward.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
import time
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / "source_plan" / "CIPHEUR_parameters.json"
EOP_SOURCE = ROOT / "source_dependencies" / "EOP-v1.1.txt"
EOP_PORTABLE_NAME = "CIPHEUR_EOP_20261004.txt"
HELP_ROOT = Path(r"C:\Program Files\AGI\STK 11\Help\Subsystems\connectCmds\Content")
EARTH_ROOT = Path(r"C:\Program Files\AGI\STK 11\STKData\CentralBodies\Earth")
TYPELIB = "{D6A1725B-89FF-43A4-995B-7F055549F4EB}"
OBJECTS_MODULE = None
MICRO = Decimal("0.000001")
FIELDS = ["source_group", "geometry_id", "replicate_id", "epoch_utc",
          "contact_id", "pass_id", "satellite_id", "site_id", "antenna_id",
          "start_utc", "end_utc", "start_seconds", "end_seconds", "duration_seconds",
          "start_tick", "end_tick", "duration_tick", "crosses_horizon", "scope",
          "access_settings_hash"]
RAW_FIELDS = FIELDS[:11] + ["start_seconds", "end_seconds", "duration_seconds",
    "provider_duration_seconds", "crosses_horizon", "scope", "access_settings_hash",
    "start_serialization_error_seconds", "end_serialization_error_seconds"]
P0_ORDER = ["CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001"]


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def iso_parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def utcg(value):
    return value.strftime("%d %b %Y %H:%M:%S.") + f"{value.microsecond:06d}"


def utc_tick(epoch, tick):
    return (epoch + timedelta(microseconds=tick)).isoformat(timespec="microseconds").replace("+00:00", "Z")


def ticks(value):
    return int((Decimal(value).quantize(MICRO, rounding=ROUND_HALF_EVEN) / MICRO))


def fixed_tick(value):
    return f"{Decimal(value) * MICRO:.6f}"


def cast(obj, interface):
    global OBJECTS_MODULE
    import win32com.client.gencache as cache
    if OBJECTS_MODULE is None:
        OBJECTS_MODULE = cache.EnsureModule(TYPELIB, 0, 1, 0, bForDemand=False)
    name = "_" + interface
    iid = OBJECTS_MODULE.NamesToIIDMap.get(name)
    if iid is None:
        raise RuntimeError(f"Installed STK 11 typelib has no {name}")
    cls = getattr(cache.GetModuleForCLSID(iid), name)
    return cls(getattr(obj, "_oleobj_", obj))


def command(root, command_text, log):
    result = root.ExecuteCommand(command_text)
    rows = [str(result.Item(i)) for i in range(result.Count)]
    log.append({"command": command_text, "result": rows})
    return rows


def constraints_snapshot(obj):
    coll = obj.AccessConstraints
    return [{"type": int(coll.Item(i).ConstraintType),
             "name": str(coll.Item(i).ConstraintName)} for i in range(coll.Count)]


def constraints_only(obj, allowed):
    coll = obj.AccessConstraints
    for row in constraints_snapshot(obj):
        if row["type"] not in allowed:
            coll.RemoveConstraint(row["type"])
    if not coll.IsConstraintActive(26):
        coll.AddConstraint(26)  # eCstrLineOfSight: retain Earth obstruction.


def initial_snapshot(satellite):
    prop = cast(satellite.Propagator, "IAgVePropagatorJ2Perturbation")
    state = cast(prop.InitialState.Representation.ConvertTo(1), "IAgOrbitStateClassical")
    state.SizeShapeType = 4  # eSizeShapeSemimajorAxis
    state.LocationType = 2  # eLocationMeanAnomaly
    state.Orientation.AscNodeType = 1  # eAscNodeRAAN
    shape = cast(state.SizeShape, "IAgClassicalSizeShapeSemimajorAxis")
    loc = cast(state.Location, "IAgClassicalLocationMeanAnomaly")
    node = cast(state.Orientation.AscNode, "IAgOrientationAscNodeRAAN")
    return {"propagator_type": int(satellite.PropagatorType),
        "propagator_name": "J2Perturbation", "step_seconds": float(prop.Step),
        "propagation_start": str(prop.StartTime), "propagation_stop": str(prop.StopTime),
        "orbit_epoch": str(prop.InitialState.Epoch),
        "propagation_frame_enum": int(prop.InitialState.PropagationFrame),
        "coordinate_system_enum": int(state.CoordinateSystemType),
        "coordinate_system_requested": "J2000", "state_epoch": str(state.Epoch),
        "semi_major_axis_km": float(shape.SemiMajorAxis),
        "eccentricity": float(shape.Eccentricity),
        "inclination_deg": float(state.Orientation.Inclination),
        "argument_of_perigee_deg": float(state.Orientation.ArgOfPerigee),
        "raan_deg": float(node.Value), "mean_anomaly_deg": float(loc.Value),
        "active_constraints": constraints_snapshot(satellite)}


def access_settings(access, maxstep):
    adv = cast(access.Advanced, "IAgStkAccessAdvanced")
    adv.UsePreciseEventTimes = True
    adv.UseFixedTimeStep = False
    adv.MaxTimeStep = maxstep
    adv.TimeConvergence = 0.001
    adv.EnableLightTimeDelay = False
    actual = {k: getattr(adv, k) for k in ["UsePreciseEventTimes", "UseFixedTimeStep",
        "MaxTimeStep", "MinTimeStep", "TimeConvergence", "EnableLightTimeDelay",
        "AbsoluteTolerance", "RelativeTolerance", "AberrationType"]}
    if not actual["UsePreciseEventTimes"] or actual["UseFixedTimeStep"] or actual["EnableLightTimeDelay"]:
        raise RuntimeError(f"Access settings not applied: {actual}")
    if actual["MaxTimeStep"] != maxstep or actual["TimeConvergence"] != 0.001:
        raise RuntimeError(f"Access numeric settings mismatch: {actual}")
    return actual


def extract_provider(access):
    provider = access.DataProviders.GetDataPrvIntervalFromPath("Access Data")
    result = provider.Exec("-3600", "262800")
    data = {}
    for i in range(result.DataSets.Count):
        ds = result.DataSets.Item(i)
        data[str(ds.ElementName)] = [format(v, ".17g") if isinstance(v, (float, int)) else str(v)
                                    for v in ds.GetValues()]
    return data


def get_intervals(data):
    starts = data.get("Start Time", [])
    stops = data.get("Stop Time", [])
    duration = data.get("Duration", [""] * len(starts))
    if not (len(starts) == len(stops) == len(duration)):
        raise RuntimeError("Access Data arrays have unequal lengths")
    rows = []
    prev = -math.inf
    for a, b, d in zip(starts, stops, duration):
        af, bf = float(a), float(b)
        if not (math.isfinite(af) and math.isfinite(bf) and -3600 <= af < bf <= 262800):
            raise RuntimeError(f"Invalid raw interval {a}, {b}")
        if af < prev:
            raise RuntimeError("Overlapping or duplicate intervals within one actual object pair")
        prev = bf
        rows.append((a, b, d))
    return rows


def eop_verify(root, definition, ascii_eop):
    """Prove this scenario loaded the frozen new EOP, including actual values."""
    scene = root.CurrentScenario
    earth = cast(scene.EarthData, "IAgScEarthData")
    actual_file = str(earth.EOPFilename)
    start, stop = str(earth.EOPStartTime), str(earth.EOPStopTime)
    lo = float(root.ConversionUtility.ConvertDate("UTCG", "EpSec", start))
    hi = float(root.ConversionUtility.ConvertDate("UTCG", "EpSec", stop))
    if lo > -3600 or hi < 262800:
        raise RuntimeError(f"Loaded EOP does not cover propagation: {start}..{stop}")
    epoch = iso_parse(definition["epoch_utc"])
    expected = None
    for line in EOP_SOURCE.read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[:3] == [str(epoch.year), f"{epoch.month:02d}", f"{epoch.day:02d}"]:
            expected = {"pole_wander_x_arcsec": float(parts[4]), "pole_wander_y_arcsec": float(parts[5]),
                        "ut1_minus_utc_seconds": float(parts[6]), "source_line": line}
            break
        if len(parts) >= 7 and all(x.isdigit() for x in parts[:3]) and tuple(map(int, parts[:3])) == (epoch.year, epoch.month, epoch.day):
            expected = {"pole_wander_x_arcsec": float(parts[4]), "pole_wander_y_arcsec": float(parts[5]),
                        "ut1_minus_utc_seconds": float(parts[6]), "source_line": line}
            break
    if expected is None:
        raise RuntimeError("Planning-start date missing from frozen EOP source")
    provider = scene.DataProviders.GetDataPrvTimeVarFromPath("EOP Table Data")
    result = provider.ExecSingle(utcg(epoch))
    actual = {str(result.DataSets.Item(i).ElementName): list(result.DataSets.Item(i).GetValues())
              for i in range(result.DataSets.Count)}
    required = {"Pole Wander X": expected["pole_wander_x_arcsec"] / 3600,
                "Pole Wander Y": expected["pole_wander_y_arcsec"] / 3600,
                "UT1-UTC": expected["ut1_minus_utc_seconds"]}
    differences = {}
    for name, wanted in required.items():
        if not actual.get(name):
            raise RuntimeError(f"Actual loaded EOP table missing {name}")
        differences[name] = float(actual[name][0]) - wanted
        if abs(differences[name]) > 1e-10:
            raise RuntimeError(f"Loaded EOP mismatch {name}: {actual[name][0]} vs {wanted}")
    if not any(abs(v) > 0 for v in required.values()):
        raise RuntimeError("Planning-start EOP unexpectedly all zero")
    return {"source_file": str(EOP_SOURCE), "source_sha256": sha(EOP_SOURCE),
        "loaded_filename": actual_file, "ascii_staged_eop_file": str(ascii_eop),
        "loaded_eop_start_utcg": start, "loaded_eop_stop_utcg": stop,
        "covers_entire_padded_propagation": True, "planning_start_source_values": expected,
        "actual_stk_eop_table_at_planning_start": actual, "difference_actual_minus_expected": differences,
        "table_matches_source": True, "future_values_are_forecasts": True,
        "publisher_download_receipt": json.loads((ROOT / "source_dependencies" / "download_receipt.json").read_text(encoding="utf-8"))}


def build(root, parameters, definition, out, log, ascii_eop):
    epoch = iso_parse(definition["epoch_utc"])
    stop = iso_parse(definition["horizon_stop_utc"])
    if (stop - epoch).total_seconds() != 259200:
        raise ValueError("P0 planning horizon must be exactly 72h")
    root.NewScenario(definition["scene_id"].replace("-", "_"))
    for key, value in [("DateFormat", "UTCG"), ("DistanceUnit", "km"), ("AngleUnit", "deg"), ("TimeUnit", "sec")]:
        root.UnitPreferences.SetCurrentUnit(key, value)
    command(root, "Units_Set * Connect Distance km", log)
    command(root, "Units_Set * Connect Time sec", log)
    scene = root.CurrentScenario
    scene.SetTimePeriod(utcg(epoch - timedelta(hours=1)), utcg(stop + timedelta(hours=1)))
    scene.Epoch = utcg(epoch)
    # Scenario-local override; never alter installation/global settings or any
    # other task's instance. Load before any orbit is propagated.
    command(root, f'EarthData * EOPFile "{ascii_eop}"', log)
    eop = eop_verify(root, definition, ascii_eop)
    write_json(out / "eop_loaded_receipt.json", eop)
    command(root, "AccessConfig / UseLightTimeDelay Off", log)
    command(root, "AccessConfig / MaxSamplingStepSize 30", log)
    command(root, "AccessConfig / TimeConvergence 0.001", log)
    satellites = []
    for i, spec in enumerate(definition["satellites"], 1):
        name = spec["satellite_id"].replace("-", "_")
        command(root, f"New / */Satellite {name}", log)
        values = " ".join(format(float(spec[k]), ".17g") for k in ["semi_major_axis_km",
            "eccentricity", "inclination_deg", "argument_of_perigee_deg", "raan_deg", "mean_anomaly_deg"])
        command(root, f'SetState */Satellite/{name} Classical J2Perturbation '
            f'"{utcg(epoch - timedelta(hours=1))}" "{utcg(stop + timedelta(hours=1))}" '
            f'30 J2000 "{utcg(epoch)}" {values}', log)
        sat = cast(root.GetObjectFromPath(f"Satellite/{name}"), "IAgSatellite")
        constraints_only(sat, {26})
        snapshot = initial_snapshot(sat)
        for key in ["semi_major_axis_km", "eccentricity", "inclination_deg", "argument_of_perigee_deg", "raan_deg", "mean_anomaly_deg"]:
            difference = snapshot[key] - float(spec[key])
            if key.endswith("deg"):
                difference = (difference + 180) % 360 - 180
            if abs(difference) > 1e-7:
                raise RuntimeError(f"Actual orbit mismatch {name} {key}: {snapshot[key]} vs {spec[key]}")
        satellites.append({"satellite_id": spec["satellite_id"], "object_path": f"Satellite/{name}",
                           "requested": spec, "actual": snapshot})
        if i % 12 == 0:
            print(f"{definition['scene_id']}: propagated {i}/84 satellites", flush=True)
    stations = []
    for spec in parameters["stations"]:
        name = spec["site_id"]
        command(root, f"New / */Facility {name}", log)
        fac = cast(root.GetObjectFromPath(f"Facility/{name}"), "IAgFacility")
        fac.UseTerrain = False
        fac.AltRef = 2  # eWGS84, ellipsoid altitude.
        fac.Position.AssignGeodetic(spec["latitude_deg"], spec["longitude_deg_east"], 0)
        constraints_only(fac, {14, 26})
        coll = fac.AccessConstraints
        c = coll.GetActiveConstraint(14) if coll.IsConstraintActive(14) else coll.AddConstraint(14)
        c = cast(c, "IAgAccessCnstrMinMax")
        c.EnableMin = True
        c.Min = 15
        c.EnableMax = False
        lat, lon, alt = fac.Position.QueryPlanetodeticArray()
        stations.append({**spec, "object_path": f"Facility/{name}", "actual": {
            "latitude_deg": float(lat), "longitude_deg_east": float(lon), "altitude_km": float(alt),
            "alt_reference_enum": int(fac.AltRef), "use_terrain": bool(fac.UseTerrain),
            "minimum_elevation_deg": float(c.Min), "active_constraints": constraints_snapshot(fac)}})
    write_json(out / "actual_geometry.json", {"satellites": satellites, "stations": stations,
        "scenario": {"name": str(scene.InstanceName), "epoch_utcg": str(scene.Epoch),
                     "start_utcg": str(scene.StartTime), "stop_utcg": str(scene.StopTime)}})
    root.UnitPreferences.SetCurrentUnit("DateFormat", "EpSec")
    if float(scene.StartTime) != -3600 or float(scene.StopTime) != 262800:
        raise RuntimeError("Scenario padding/epoch alignment failed")
    return epoch, satellites, stations, eop


def dependency_receipt(out):
    target = out / "environment_dependencies"
    target.mkdir()
    originals = [EARTH_ROOT / "Earth.cb", EARTH_ROOT / "EarthAttitude2000.rot",
                 EARTH_ROOT / "EGM2008.grv"]
    rows = []
    for src in originals:
        if src.is_file():
            dest = target / src.name
            shutil.copy2(src, dest)
            rows.append({"original_path": str(src), "saved_path": str(dest.relative_to(out)),
                         "size_bytes": src.stat().st_size, "sha256": sha(dest)})
        else:
            rows.append({"original_path": str(src), "status": "not_found"})
    help_rows = []
    for file in ["cmd_Access.htm", "cmd_AccessConfig.htm", "cmd_SetStateClassical.htm", "cmd_PositionFacilityPlaceTargetAreaTarget.htm"]:
        src = HELP_ROOT / file
        help_rows.append({"official_local_help": str(src), "sha256": sha(src)})
    write_json(out / "environment_receipt.json", {"dependencies": rows, "official_local_help": help_rows,
        "earth_shape_note": "Earth.cb defines WGS84 ellipsoid, while its gravity model is EGM2008; these are different settings.",
        "scope": "Ideal geometric access, no terrain mask, no RF/weather/illumination/request constraints."})


def generate(parameters, definition, retry_failed=False):
    out = ROOT / "raw" / definition["scene_id"]
    if out.exists():
        if not retry_failed:
            raise FileExistsError(f"Output exists; never silently overwrite: {out}")
        old = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        if old.get("status") != "failed":
            raise RuntimeError("Only failed attempts may be archived for retry")
        dest = out.parent / "failed_attempts" / (out.name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        assert out.resolve().parent == (ROOT / "raw").resolve()
        assert dest.resolve().is_relative_to((ROOT / "raw").resolve())
        dest.parent.mkdir(exist_ok=True)
        out.rename(dest)
    out.mkdir(parents=True)
    manifest = {"status": "running", "started_at": now(), "scene_id": definition["scene_id"],
        "source_group": definition["source_group"], "geometry_id": definition["geometry_id"],
        "replicate_id": definition["replicate_id"], "split": definition["split"],
        "parameters_file": str(PARAMETERS), "parameters_sha256": sha(PARAMETERS),
        "generator_sha256": sha(Path(__file__)), "planning_epoch_utc": definition["epoch_utc"],
        "planning_horizon_seconds": 259200, "simulation_range_seconds": [-3600, 262800],
        "pairs_completed": 0, "pairs_total": 1008, "contact_count": 0}
    write_json(out / "manifest.json", manifest)
    write_json(out / "recipe.json", {"common_settings": parameters["common_settings"],
                                     "scene_definition": definition, "stations": parameters["stations"]})
    commands = []
    app = root = None
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    t0 = time.perf_counter()
    try:
        app = win32com.client.DispatchEx("STK11.Application")
        app.Visible = False
        app.UserControl = False
        root = app.Personality2
        manifest["stk_version"] = command(root, "GetSTKVersion / Details", commands)
        if not any("v11." in x for x in manifest["stk_version"]):
            raise RuntimeError("STK 11 required")
        receipt = json.loads((ROOT / "source_dependencies" / "download_receipt.json").read_text(encoding="utf-8"))
        if sha(EOP_SOURCE) != receipt["sha256"] or not receipt["publisher_sha256_verified"]:
            raise RuntimeError("Frozen EOP file differs from verified publisher input")
        staging = Path(tempfile.mkdtemp(prefix=definition["scene_id"].replace("-", "_") + "_", suffix="_CIPHEUR_STK"))
        if not str(staging).isascii():
            raise RuntimeError("STK native serializer requires an ASCII staging path")
        ascii_eop = staging / EOP_PORTABLE_NAME
        shutil.copy2(EOP_SOURCE, ascii_eop)
        manifest["owned_ascii_scene_staging_directory"] = str(staging)
        epoch, satellites, stations, eop = build(root, parameters, definition, out, commands, ascii_eop)
        manifest.update(formal_dataset=True, eop_sha256=sha(EOP_SOURCE),
            eop_loaded_covers_padded_propagation=True, eop_actual_table_matches_source=True,
            eop_receipt_file="eop_loaded_receipt.json")
        dependency_receipt(out)
        # STK 11 native serializer fails with this machine's Chinese directory
        # components. Use a fresh owned ASCII staging folder, then copy every
        # dependency into the requested data root (no simulation data is lost).
        scene_dir = out / "scene"
        scene_dir.mkdir()
        staged_scene_file = staging / (definition["scene_id"].replace("-", "_") + ".sc")
        scene_file = scene_dir / staged_scene_file.name
        root.SaveScenarioAs(str(staged_scene_file))
        for p in staging.iterdir():
            if p.is_file():
                shutil.copy2(p, scene_dir / p.name)
            elif p.is_dir():
                shutil.copytree(p, scene_dir / p.name)
        complete = []
        boundary = []
        raw_rows = []
        pair_counts = []
        settings_seen = {}
        max_error = Decimal(0)
        spot_samples = []
        selected_pairs = {(0, 0), (27, 5), (55, 6), (83, 11)}
        with (out / "provider_reports.jsonl").open("w", encoding="utf-8") as reports:
            for sj, sat in enumerate(satellites):
                for gj, station in enumerate(stations):
                    if (out / "STOP_REQUEST").exists():
                        raise RuntimeError("Cooperative stop requested; owned instance closes through finally")
                    aobj = root.GetObjectFromPath(sat["object_path"])
                    bobj = root.GetObjectFromPath(station["object_path"])
                    access = aobj.GetAccessToObject(bobj)
                    actual = access_settings(access, 30)
                    h = hash_json(actual)
                    settings_seen[h] = actual
                    access.ComputeAccess()
                    data = extract_provider(access)
                    reports.write(json.dumps({"satellite_id": sat["satellite_id"],
                        "site_id": station["site_id"], "settings_hash": h, "data": data}) + "\n")
                    intervals = get_intervals(data)
                    count = 0
                    for p, (a, b, provider_d) in enumerate(intervals, 1):
                        sa, sb = ticks(a), ticks(b)
                        if sb <= sa:
                            raise RuntimeError("Microsecond serialization collapsed a positive contact; do not drop silently")
                        inside = Decimal(a) >= 0 and Decimal(b) <= 259200
                        cross = (Decimal(a) < 0 < Decimal(b)) or (Decimal(a) < 259200 < Decimal(b))
                        scope = "complete_horizon" if inside else ("crosses_horizon" if cross else "outside_horizon_padding")
                        pass_id = f"{definition['scene_id']}:{sat['satellite_id']}:{station['site_id']}:p{p:04d}"
                        row = {"source_group": definition["source_group"], "geometry_id": definition["geometry_id"],
                            "replicate_id": definition["replicate_id"], "epoch_utc": definition["epoch_utc"],
                            "contact_id": pass_id, "pass_id": pass_id, "satellite_id": sat["satellite_id"],
                            "site_id": station["site_id"], "antenna_id": station["antenna_id"],
                            "start_utc": utc_tick(epoch, sa), "end_utc": utc_tick(epoch, sb),
                            "start_seconds": fixed_tick(sa), "end_seconds": fixed_tick(sb),
                            "duration_seconds": fixed_tick(sb - sa), "start_tick": sa, "end_tick": sb,
                            "duration_tick": sb - sa, "crosses_horizon": cross,
                            "scope": scope, "access_settings_hash": h}
                        (complete if inside else boundary).append(row)
                        ea, eb = Decimal(row["start_seconds"]) - Decimal(a), Decimal(row["end_seconds"]) - Decimal(b)
                        max_error = max(max_error, abs(ea), abs(eb))
                        raw_rows.append({**row, "start_seconds": a, "end_seconds": b,
                            "duration_seconds": str(Decimal(b) - Decimal(a)), "provider_duration_seconds": provider_d,
                            "start_serialization_error_seconds": str(ea), "end_serialization_error_seconds": str(eb)})
                        count += int(inside)
                    pair_counts.append({"satellite_id": sat["satellite_id"], "site_id": station["site_id"],
                                        "raw_intervals": len(intervals), "complete_horizon_intervals": count})
                    if (sj, gj) in selected_pairs:
                        access.ClearAccess()
                        actual15 = access_settings(access, 15)
                        access.ComputeAccess()
                        data15 = extract_provider(access)
                        intervals15 = get_intervals(data15)
                        differences = []
                        if len(intervals15) == len(intervals):
                            differences = [{"interval_index": k + 1, "start_difference_seconds": float(a15) - float(a),
                                            "end_difference_seconds": float(b15) - float(b)}
                                for k, ((a, b, _), (a15, b15, _)) in enumerate(zip(intervals, intervals15))]
                        spot_samples.append({"satellite_id": sat["satellite_id"], "site_id": station["site_id"],
                            "settings_30": actual, "settings_15": actual15, "raw_30": data, "raw_15": data15,
                            "same_interval_count": len(intervals) == len(intervals15), "differences": differences})
                        access.ClearAccess()
                        access_settings(access, 30)
                        access.ComputeAccess()
                    manifest.update(pairs_completed=len(pair_counts), contact_count=len(complete),
                                    updated_at=now(), elapsed_seconds=time.perf_counter() - t0)
                    if len(pair_counts) == 1 or len(pair_counts) % 48 == 0 or len(pair_counts) == 1008:
                        reports.flush()
                        write_json(out / "manifest.json", manifest)
                        print(f"{definition['scene_id']}: access {len(pair_counts)}/1008, complete={len(complete)}", flush=True)
        complete.sort(key=lambda r: (r["start_tick"], r["contact_id"]))
        boundary.sort(key=lambda r: (r["start_tick"], r["contact_id"]))
        for name, rows, fields in [("contacts.csv", complete, FIELDS), ("contacts_boundary.csv", boundary, FIELDS),
                                   ("access_raw.csv", raw_rows, RAW_FIELDS)]:
            with (out / name).open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        write_json(out / "pair_counts.json", pair_counts)
        write_json(out / "access_actual_settings.json", settings_seen)
        write_json(out / "sampling_spot_check.json", {"selection_rule": "Fixed indices (0,0),(27,5),(55,6),(83,11), chosen before results",
            "samples": spot_samples, "max_endpoint_difference_seconds": max((abs(d[k]) for s in spot_samples for d in s["differences"]
                for k in ["start_difference_seconds", "end_difference_seconds"]), default=None)})
        if not all(s["same_interval_count"] for s in spot_samples):
            raise RuntimeError("30/15s fixed-pair access count mismatch; retain outputs but do not mark success")
        write_json(out / "precision_receipt.json", {"raw_format": "STK Access Data double -> .17g round-trip strings; provider arrays preserved in JSONL",
            "frozen_endpoints": "Decimal nearest microsecond, ROUND_HALF_EVEN, exactly six decimal places",
            "reward": "end_tick - start_tick, neither provider-duration roundoff nor reassignment",
            "tick_seconds": "0.000001", "maximum_absolute_endpoint_serialization_error_seconds": str(max_error),
            "physical_time_convergence_seconds": "0.001", "accuracy_warning": "Microsecond serialization is numerical semantics, not orbital accuracy",
            "overflow_check": {"maximum_capacity_one_reward_tick_upper_bound": 12 * 259200 * 1000000,
                               "signed_int64_safe": 12 * 259200 * 1000000 < 2 ** 63}})
        root.SaveScenarioAs(str(staged_scene_file))
        for p in staging.iterdir():
            if p.is_file():
                shutil.copy2(p, scene_dir / p.name)
            elif p.is_dir():
                shutil.copytree(p, scene_dir / p.name, dirs_exist_ok=True)
        # Preserve the original native save and make only its EOP reference
        # portable. The bytes and SHA of the referenced EOP remain unchanged.
        shutil.copy2(staged_scene_file, out / "native_save_original.sc")
        scene_text = scene_file.read_text(encoding="ascii")
        if str(ascii_eop) not in scene_text:
            raise RuntimeError("Native saved scenario has an unexpected EOP file reference")
        scene_file.write_text(scene_text.replace(str(ascii_eop), EOP_PORTABLE_NAME), encoding="ascii")
        unresolved = []
        for p in scene_dir.rglob("*"):
            if p.is_file() and str(staging).encode("ascii") in p.read_bytes():
                unresolved.append(str(p.relative_to(scene_dir)))
        if unresolved:
            raise RuntimeError(f"Portable scene retains temporary directory references: {unresolved}")
        write_json(out / "scene_portability_receipt.json", {
            "all_native_scene_files_and_subdirectories_copied": True,
            "only_native_change": "EOP absolute staged filename -> relative unique portable filename",
            "eop_portable_filename": EOP_PORTABLE_NAME, "eop_sha256": sha(scene_dir / EOP_PORTABLE_NAME),
            "unresolved_temporary_path_references": unresolved,
            "original_native_save": "native_save_original.sc", "final_scene": str(scene_file)})
        if definition["scene_id"] == "CP-AU-r000":
            validation_stage = Path(tempfile.mkdtemp(prefix="CP_AU_r000_reload_", suffix="_CIPHEUR_STK"))
            for p in scene_dir.iterdir():
                if p.is_file():
                    shutil.copy2(p, validation_stage / p.name)
                elif p.is_dir():
                    shutil.copytree(p, validation_stage / p.name)
            root.CloseScenario()
            root.LoadScenario(str(validation_stage / scene_file.name))
            root.UnitPreferences.SetCurrentUnit("DateFormat", "UTCG")
            reload_eop = eop_verify(root, definition, validation_stage / EOP_PORTABLE_NAME)
            loaded = root.CurrentScenario
            reload_counts = {}
            for i in range(loaded.Children.Count):
                typ = str(loaded.Children.Item(i).ClassName)
                reload_counts[typ] = reload_counts.get(typ, 0) + 1
            if reload_counts != {"Satellite": 84, "Facility": 12}:
                raise RuntimeError(f"Reloaded scene object counts mismatch: {reload_counts}")
            write_json(out / "pilot_portable_reload.json", {"status": "success", "same_owned_instance": True,
                "new_ascii_staging_directory": str(validation_stage), "object_counts": reload_counts,
                "eop_loaded_after_relative_reference": reload_eop,
                "verification": "Saved data scene and all dependencies reloaded from a new ASCII directory; no access recomputation."})
        write_json(out / "connect_commands.json", commands)
        files = [{"path": str(p.relative_to(out)), "size_bytes": p.stat().st_size, "sha256": sha(p)}
                 for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"]
        manifest.update(status="success", finished_at=now(), elapsed_seconds=time.perf_counter() - t0,
            contact_count=len(complete), boundary_records=len(boundary), raw_interval_count=len(raw_rows),
            crossing_horizon_count=sum(r["crosses_horizon"] for r in boundary), files=files,
            contacts_sha256=sha(out / "contacts.csv"), scene_file=str(scene_file),
            no_minimum_duration_filter=True, full_visibility_intervals=True, no_legacy_input_used=True)
    except Exception as exc:
        manifest.update(status="failed", failed_at=now(), error_type=type(exc).__name__,
                        error=str(exc), traceback=traceback.format_exc(), elapsed_seconds=time.perf_counter() - t0)
        write_json(out / "connect_commands.json", commands)
        raise
    finally:
        if app is not None:
            try:
                app.Quit()
                manifest["owned_stk_instance_closed"] = True
            except Exception as exc:
                manifest["owned_stk_instance_closed"] = False
                manifest["close_error"] = str(exc)
        if manifest.get("status") == "success" and "staging" in locals():
            # Only this explicitly created, ASCII temp directory may be removed.
            if staging.resolve().parent == Path(tempfile.gettempdir()).resolve() and staging.name.endswith("_CIPHEUR_STK"):
                shutil.rmtree(staging)
                manifest["owned_ascii_scene_staging_removed_after_complete_copy"] = True
            if "validation_stage" in locals() and validation_stage.resolve().parent == Path(tempfile.gettempdir()).resolve() and validation_stage.name.endswith("_CIPHEUR_STK"):
                shutil.rmtree(validation_stage)
        write_json(out / "manifest.json", manifest)
        root = app = None
        pythoncom.CoUninitialize()
    print(json.dumps({"scene_id": definition["scene_id"], "status": manifest["status"],
                      "contacts": manifest["contact_count"], "elapsed_seconds": manifest["elapsed_seconds"]}), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", action="append", help="Scene ID from parameter JSON; default P0 order")
    parser.add_argument("--retry-failed", action="store_true", help="Archive failed attempt, then retry; never overwrite success")
    args = parser.parse_args()
    p = json.loads(PARAMETERS.read_text(encoding="utf-8-sig"))
    definitions = {s["scene_id"]: s for s in p["scene_definitions"]}
    for name in args.scene or P0_ORDER:
        generate(p, definitions[name], retry_failed=args.retry_failed)


if __name__ == "__main__":
    main()
