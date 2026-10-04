"""Outcome-free fresh V06 synthetic performance inputs; no TRAIN mutation.

Freeze the prescribed generator metadata/source before producing 108 pairs /
216 TEST endpoints. Neither phase runs a solver, programme or oracle. No cell
is dropped or replaced based on realized density or any optimization outcome.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.model import Contact, temporal_graph

NAMESPACE = "V06_FRESH_PERFORMANCE_TEST_20261003_001"
SIZES = (512, 1024, 2048)
RESOURCES = {"balanced": (8, 6), "ground_scarce": (12, 3), "satellite_scarce": (3, 12)}
PROFILES = {"standard": {"horizon_per_contact": 1.8, "duration_quarters": [2, 48]},
            "dense_long": {"horizon_per_contact": 0.18, "duration_quarters": [2, 192]}}
PAIRS_PER_CELL = 6
SOURCE_NAMES = ("scripts/prepare_performance_v06.py", "cipheur/model.py")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                    separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def planned_cells():
    cells = []
    for profile in PROFILES:
        for regime in RESOURCES:
            for size in SIZES:
                for index in range(PAIRS_PER_CELL):
                    identity = f"v06perf_test_{profile}_{regime}_{size}_{index:02d}"
                    seed_hash = sha256((NAMESPACE + "|" + identity).encode()).hexdigest()
                    cells.append({"id": identity, "ordinal": len(cells), "split": "test",
                        "profile": profile, "regime": regime, "size": size, "index": index,
                        "seed_sha256": seed_hash, "seed": int(seed_hash, 16)})
    return cells


def make_protocol():
    cells = planned_cells()
    return {"version": "v06_fresh_synthetic_performance_inputs_001", "split": "test",
        "seed_namespace": NAMESPACE, "sizes": list(SIZES),
        "resources": {name: list(values) for name, values in RESOURCES.items()},
        "profiles": PROFILES, "pairs_per_cell": PAIRS_PER_CELL, "pairs": len(cells),
        "endpoints": 2 * len(cells), "cells": cells, "cells_sha256": canonical_hash(cells),
        "source_sha256": {name: digest(ROOT / name) for name in SOURCE_NAMES},
        "generator": {"model": "synthetic_single_capacity_temporal", "time_step": 0.25,
            "start_quarter_rule": "uniform integer in [0,floor(4*horizon))",
            "duration_rule": "uniform inclusive quarter range specified by profile",
            "reward_quarters": [1, 80], "station_gap_left": 0.5, "station_gap_right": 6.0,
            "satellite_gap": 0.0, "station_capacity": 1, "satellite_capacity": 1,
            "resource_assignment": "independent uniform satellite and ground labels",
            "contact_ids": "v06perf_001_<cell ordinal 3 digits>_c<contact index 4 digits>",
            "rng": "random.Random(full SHA256 namespace+cell integer); each regime/profile/size/index independent",
            "density_selection": "Generator horizon/duration/resource parameters fixed without outcome pilot; realized edges are reported and never filter cells"},
        "before_any_performance_outcomes": True, "optimization_calls": 0, "oracle_calls": 0,
        "candidate_evaluations": 0, "outcome_filtering": False, "TRAIN_inputs_changed": False,
        "contact_scope": "Entirely new synthetic contact namespace; no source contacts imported. Left/right within one pair intentionally share every contact; different cells share none.",
        "population_scope": "Specified synthetic generator only; no physical-source representativeness or optimizer superiority claim",
        "statistical_unit": "Independent generated source pair; paired constraint endpoints are not independent observations",
        "training": "This builder has no TRAIN generation/evaluation branch; any optional future TRAIN design needs a separate protocol",
        "execution": "Input generation only. Programme/config selection must freeze on TRAIN before any solver TEST execution."}


def build_pair(cell):
    """Generate one declared cell, preserving contacts across its intervention."""
    if cell["split"] != "test" or cell["profile"] not in PROFILES or cell["regime"] not in RESOURCES:
        raise ValueError("Unknown declared performance input cell")
    size = cell["size"]
    if type(size) is not int or size <= 0:
        raise ValueError("Cell size must be a positive integer")
    rng = random.Random(cell["seed"])
    satellites, grounds = RESOURCES[cell["regime"]]
    profile = PROFILES[cell["profile"]]
    horizon = size * profile["horizon_per_contact"]
    low, high = profile["duration_quarters"]
    shift = cell["ordinal"] * 100000.0
    contacts = []
    for k in range(size):
        start = rng.randrange(max(1, int(horizon * 4))) / 4
        duration = rng.randrange(low, high + 1) / 4
        contacts.append(Contact(f"v06perf_001_{cell['ordinal']:03d}_c{k:04d}",
            rng.randrange(1, 81) / 4, f"S{rng.randrange(satellites)}", f"G{rng.randrange(grounds)}",
            shift + start, shift + start + duration))
    graphs = [temporal_graph(cell["id"] + "_" + side, contacts, gap, 0.0)
              for side, gap in (("left", 0.5), ("right", 6.0))]
    if graphs[0].contacts != graphs[1].contacts or not graphs[0].edges <= graphs[1].edges:
        raise AssertionError("Paired switching intervention changed contacts or removed conflicts")
    source = {"origin": "fresh_v06_synthetic_performance_generator", "split": "test",
        "seed_namespace": NAMESPACE, "seed": cell["seed"], "seed_sha256": cell["seed_sha256"],
        "size": size, "profile": cell["profile"], "regime": cell["regime"], "index": cell["index"],
        "ordinal": cell["ordinal"], "horizon": horizon, "duration_quarters": [low, high],
        "satellites": satellites, "ground_stations": grounds, "parameter": "station_gap",
        "outcome_filtering": False, "population_claim": "specified_generator_only",
        "instance_sha256": canonical_hash([asdict(c) for c in contacts])}
    pair = {"id": cell["id"], "split": "test", "family": cell["profile"] + "_" + cell["regime"],
        "cluster": cell["id"], "left": graphs[0].to_dict(), "right": graphs[1].to_dict(),
        "fixed": [], "excluded": [], "source": source}
    endpoints = []
    for side, graph in zip(("left", "right"), graphs):
        n, m = len(graph.nodes), len(graph.edges)
        endpoints.append({"id": cell["id"] + ":" + side, "pair_id": cell["id"], "side": side,
            "split": "test", "family": pair["family"], "cluster": cell["id"],
            "n": n, "m": m, "density": 2 * m / (n * (n - 1)) if n > 1 else 0.0,
            "mean_degree": 2 * m / n, "graph": graph.to_dict(), "graph_sha256": graph.digest(),
            "fixed": [], "excluded": [], "source": source})
    return pair, endpoints


def prepare(output):
    output = Path(output)
    protocol = make_protocol()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "protocol.json", protocol)
    write(output / "freeze_receipt.json", {"version": protocol["version"],
        "before_input_generation": True, "before_any_performance_outcomes": True,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol_sha256": digest(output / "protocol.json"),
        "source_sha256": protocol["source_sha256"]})
    return protocol


def verify_plan(output):
    output = Path(output)
    receipt = json.loads((output / "freeze_receipt.json").read_text(encoding="utf-8"))
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    if (receipt["before_input_generation"] is not True or
            digest(output / "protocol.json") != receipt["protocol_sha256"]):
        raise ValueError("Input generator metadata was not frozen or changed")
    if protocol != make_protocol() or receipt["source_sha256"] != protocol["source_sha256"]:
        raise ValueError("Prespecified generator configuration/runtime source changed")
    return protocol


def generate(output, workers=4, selection=None):
    output = Path(output)
    if type(workers) is not int or not 1 <= workers <= 64:
        raise ValueError("workers must be an integer between 1 and 64")
    protocol = verify_plan(output)
    if any((output / name).exists() for name in ("data.json", "input_completion.json",
            "input_execution.json", "input_progress.json", "input_generation_error.json")):
        raise ValueError("Preserve generated inputs; no replacing/re-drawing cells")
    selection_sha = None
    if selection is not None:
        frozen = json.loads(Path(selection).read_text(encoding="utf-8"))
        if (frozen.get("selection_split") != "train" or frozen.get("test_accessed") is not False
                or not frozen.get("all_cells_have_genuine_winner") or len(frozen.get("programs", [])) != 12):
            raise ValueError("Optional selection binding requires twelve genuine TRAIN-frozen programmes")
        selection_sha = digest(selection)
    started = time.perf_counter()
    write(output / "input_execution.json", {"protocol_sha256": digest(output / "protocol.json"),
        "workers": workers, "selection_sha256": selection_sha,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "before_graph_generation": True, "optimization_calls": 0})
    completed = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(build_pair, cell): cell for cell in protocol["cells"]}
        for future in as_completed(futures):
            cell = futures[future]
            # A generation error aborts and preserves the partial receipt: no
            # alternate seed, dropped cell or replacement population is allowed.
            try:
                completed[cell["ordinal"]] = future.result()
            except Exception as failure:
                write(output / "input_generation_error.json", {"failed_cell": cell["id"],
                    "type": type(failure).__name__, "message": str(failure),
                    "completed_pairs": len(completed), "alternate_seed_used": False})
                raise
            write(output / "input_progress.json", {"planned_pairs": len(protocol["cells"]),
                "generated_pairs": len(completed), "wall_seconds": time.perf_counter() - started})
    pairs, contexts, ids = [], [], set()
    for ordinal in range(len(protocol["cells"])):
        pair, endpoints = completed[ordinal]
        contact_ids = {c["id"] for c in pair["left"]["contacts"]}
        if len(contact_ids) != pair["source"]["size"] or contact_ids & ids:
            raise AssertionError("Contact namespace reused across source pairs")
        ids.update(contact_ids)
        pairs.append(pair)
        contexts.extend(endpoints)
    if len(pairs) != 108 or len(contexts) != 216 or len({c["id"] for c in contexts}) != 216:
        raise AssertionError("Prespecified performance frame incomplete")
    write(output / "data.json", {"test": pairs, "contexts": contexts,
        "protocol": {"version": protocol["version"], "protocol_sha256": digest(output / "protocol.json"),
                     "outcome_filtering": False, "selection_sha256": selection_sha}})
    write(output / "input_identity.json", {"unique_contact_ids": len(ids),
        "contact_ids_sha256": canonical_hash(sorted(ids)),
        "endpoint_identities": [{k: c[k] for k in ("id", "pair_id", "side", "graph_sha256", "n", "m", "density")}
                                for c in contexts],
        "family_counts": dict(Counter(c["family"] for c in contexts))})
    receipt = {"version": protocol["version"], "input_generation_complete": True,
        "pairs": len(pairs), "endpoints": len(contexts), "unique_contact_ids": len(ids),
        "data_sha256": digest(output / "data.json"), "input_identity_sha256": digest(output / "input_identity.json"),
        "protocol_sha256": digest(output / "protocol.json"), "selection_sha256": selection_sha,
        "source_sha256": protocol["source_sha256"], "workers": workers,
        "wall_seconds": time.perf_counter() - started, "optimization_calls": 0,
        "candidate_evaluations": 0, "test_outcomes_accessed": False, "TRAIN_inputs_changed": False}
    write(output / "input_completion.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--generate", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--selection")
    args = parser.parse_args(argv)
    receipt = prepare(args.out) if args.plan_only else generate(args.out, args.workers, args.selection)
    print(json.dumps(receipt, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
