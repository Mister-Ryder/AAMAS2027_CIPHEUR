"""Outcome-free, explicitly exploratory C3 contact-derived input preparation."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import argparse
import csv
import io
import json
import os
from pathlib import Path
import platform
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.model import Contact, Graph, temporal_graph

STEM = "c3_interval_inputs_v06_001"
STAGE = ROOT / "experiments/discovery" / STEM
CAPSULE = ROOT / "experiments/source_snapshots/v06" / (STEM + "_source.zip")
OUT = ROOT / "output" / STEM
FRESH = "experiments/runs/v04/advanced_fresh_v04_001.tar.gz"
FRESH_SHA = "4bbddde5655edf06b6959ada796166ff44b909e8bec9f8d5383e1796cdab7828"
CSV_SHA = "ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e"
CSV_PATH = "inputs/C3_source_v06.csv"
CODE = ("cipheur/__init__.py", "cipheur/model.py", "scripts/prepare_c3_interval_inputs_v06.py")


def digest(raw):
    return sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode())


def original_pairs():
    assert digest((ROOT / FRESH).read_bytes()) == FRESH_SHA
    with tarfile.open(ROOT / FRESH, "r:gz") as tar:
        data = json.load(tar.extractfile("advanced_fresh_v04_001/data.json"))
    pairs = sorted((r for r in data["test"] if r["family"] == "c3"), key=lambda r:r["id"])
    assert len(pairs) == 12 and Counter(len(r["left"]["contacts"]) for r in pairs) == {64:3,128:3,256:3,512:3}
    return pairs


def package(csv_path):
    if STAGE.exists() or CAPSULE.exists():
        raise ValueError("Do not overwrite the first C3 transformation protocol")
    raw_csv = Path(csv_path).read_bytes()
    assert digest(raw_csv) == CSV_SHA
    pairs = original_pairs()
    identities = [{"id": r["id"], "source_ids": [c["id"] for c in r["left"]["contacts"]],
        "n": len(r["left"]["contacts"]), "source_metadata": r["source"],
        "legacy_constraints_left": r["left"]["constraints"],
        "legacy_constraints_right": r["right"]["constraints"]} for r in pairs]
    protocol = {"version": STEM, "before_any_new_graph_or_optimization": True,
        "source_archive": FRESH, "source_archive_sha256": FRESH_SHA,
        "source_csv_sha256": CSV_SHA, "source_csv_capsule_path": CSV_PATH,
        "source_encoding": "strict GB18030; quoted resource labels stripped exactly",
        "sources": identities, "original_pairs": 12, "original_contexts": 24,
        "new_interval_pairs": 12, "new_interval_contexts": 24,
        "ground_gap_seconds_left": 0.5, "ground_gap_seconds_right": 6,
        "satellite_gap_seconds": 0, "tasks": "Preserve the original empty task field",
        "contact_values": "Original integer link start/end in seconds and reward=end-start; match every inherited contact to its exact original CSV row before construction",
        "new_model": "Single-capacity station/satellite resource interval conflicts; task conflicts only if a nonempty original task exists",
        "old_model": "Original frozen V51 crossing/overlap conflict predicates remain a separate exploratory track, not silently replaced",
        "exposure": "These12source subproblems and24legacy contexts were exposed in V04/V05. Newviews are transformations of previously observed sources, not independent held-out natural data.",
        "source_selection": "All original12C3 TEST blocks retained, including zero-edge-change pairs; no performance/alias/density selection",
        "optional_execution": "Input preparation only; root may predeclare the interval and/or legacy tracks before TEST performance launch. Keep all selected tracks separate from fresh synthetic and natural public populations.",
        "optimization_calls": 0, "oracle_calls": 0, "candidate_reads": 0,
        "source_sha256": {n:digest((ROOT/n).read_bytes()) for n in CODE}}
    write(STAGE / "protocol.json", protocol)
    write(STAGE / "freeze_receipt.json", {"before_any_new_graph_or_optimization": True,
        "protocol_sha256": digest((STAGE/"protocol.json").read_bytes()),
        "source_csv_sha256": CSV_SHA, "source_archive_sha256": FRESH_SHA,
        "source_sha256": protocol["source_sha256"]})
    names = [*CODE, "experiments/discovery/"+STEM+"/protocol.json",
             "experiments/discovery/"+STEM+"/freeze_receipt.json"]
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):
            z.writestr(name, (ROOT/name).read_bytes())
        z.writestr(CSV_PATH, raw_csv)
    receipt = {"before_any_new_graph_or_optimization": True,
        "source_zip_sha256": digest(CAPSULE.read_bytes()),
        "source_files_sha256": {n:digest((ROOT/n).read_bytes()) for n in names},
        "source_csv_sha256": CSV_SHA}
    write(STAGE/"capsule_receipt.json", receipt)
    print(json.dumps(receipt), flush=True)


def generate():
    if platform.system() != "Linux":
        raise ValueError("C3 input preparation is reserved for the authorized server")
    if OUT.exists():
        raise ValueError("Preserve first generated input archive")
    protocol = json.loads((STAGE/"protocol.json").read_bytes())
    freeze = json.loads((STAGE/"freeze_receipt.json").read_bytes())
    receipt = json.loads((STAGE/"capsule_receipt.json").read_bytes())
    assert digest(CAPSULE.read_bytes()) == receipt["source_zip_sha256"]
    assert digest((STAGE/"protocol.json").read_bytes()) == freeze["protocol_sha256"]
    for n, expected in protocol["source_sha256"].items():
        assert digest((ROOT/n).read_bytes()) == expected
    raw_csv = (ROOT/CSV_PATH).read_bytes()
    assert digest(raw_csv) == CSV_SHA
    rows = list(csv.reader(io.StringIO(raw_csv.decode("gb18030"))))
    assert len(rows) == 69924
    clean = lambda s:s.strip().strip("'").strip('"')
    source_rows = rows[1:]
    OUT.mkdir(parents=True)
    host = {"before_any_new_graph_or_optimization": True, "timestamp_unix": time.time(),
        "pid": os.getpid(), "python": sys.version, "platform": platform.platform(),
        "source_zip_sha256": receipt["source_zip_sha256"]}
    write(OUT/"host_receipt.json", host)
    contexts, new_pairs, identity = [], [], []
    checked = 0
    original_id_sets = []
    for pair in original_pairs():
        assert pair["left"]["contacts"] == pair["right"]["contacts"]
        contacts = []
        for inherited in pair["left"]["contacts"]:
            source = source_rows[int(inherited["id"])]
            start, end = int(clean(source[2])), int(clean(source[3]))
            assert inherited["start"] == start and inherited["end"] == end
            assert inherited["station"] == clean(source[0]) and inherited["satellite"] == clean(source[1])
            assert Fraction(inherited["weight"]) == end-start and end > start
            assert inherited["task"] == ""
            contacts.append(Contact(inherited["id"], end-start, clean(source[1]),clean(source[0]),start,end,""))
            checked += 1
        original_id_sets.append(set(c.id for c in contacts))
        stem = pair["id"].replace("v04_c3_test_", "v06_c3_interval_exploratory_")
        left = temporal_graph(stem+":left", contacts, station_gap=0.5, satellite_gap=0)
        right = temporal_graph(stem+":right", contacts, station_gap=6, satellite_gap=0)
        assert left.contacts == right.contacts and left.edges <= right.edges
        provenance = {"source_data_sha256": CSV_SHA, "legacy_pair_id": pair["id"],
            "original_ids": [int(c.id) for c in contacts],
            "scope": "Previously exposed C3 source contacts, transformed single-capacity interval model; exploratory"}
        left.provenance = dict(provenance)
        right.provenance = dict(provenance)
        new_pairs.append({"id": stem, "left": left.to_dict(), "right": right.to_dict(),
            "split": "exploratory", "source": provenance,
            "added_edges": len(right.edges-left.edges), "removed_edges": 0})
        for side, graph in (("left",left),("right",right)):
            contexts.append({"id":stem+":"+side,"pair_id":stem,"side":side,"split":"exploratory",
                "population":"C3_interval_exploratory","graph":graph.to_dict(),"graph_sha256":graph.digest(),
                "n":len(contacts),"m":len(graph.edges),"source_weight_scale":1,"source":provenance})
        for side in ("left","right"):
            graph = Graph.from_dict(pair[side])
            contexts.append({"id":pair["id"]+":"+side,"pair_id":pair["id"],"side":side,"split":"exploratory",
                "population":"C3_legacy_exploratory","graph":pair[side],"graph_sha256":graph.digest(),
                "n":len(contacts),"m":len(graph.edges),"source_weight_scale":1,"source":pair["source"]})
        identity.append({"source_pair_id":pair["id"],"n":len(contacts),
            "interval_left_graph_sha256":left.digest(),"interval_right_graph_sha256":right.digest(),
            "interval_left_edges":len(left.edges),"interval_right_edges":len(right.edges),
            "interval_added_edges":len(right.edges-left.edges),"legacy_left_edges":len(pair["left"]["edges"]),
            "legacy_right_edges":len(pair["right"]["edges"]),"all_original_contact_fields_verified":True})
    assert sum(map(len,original_id_sets)) == len(set.union(*original_id_sets)) == 2880
    assert len(contexts) == 48 and len(new_pairs) == 12 and checked == 2880
    write(OUT/"data.json",{"contexts":sorted(contexts,key=lambda r:r["id"]),"interval_pairs":new_pairs})
    write(OUT/"identity.json",{"records":identity,"checked_source_contacts":checked,
        "source_blocks_disjoint":True,"models_not_pooled":True,"optimization_calls":0})
    for name in ("protocol.json","freeze_receipt.json","capsule_receipt.json"):
        (OUT/name).write_bytes((STAGE/name).read_bytes())
    write(OUT/"complete.json",{"prepared_contexts":48,"original_contexts":24,"interval_contexts":24,
        "original_source_pairs":12,"checked_source_contacts":2880,"optimization_calls":0,"oracle_calls":0,
        "candidate_reads":0,"data_sha256":digest((OUT/"data.json").read_bytes()),
        "identity_sha256":digest((OUT/"identity.json").read_bytes()),
        "source_zip_sha256":receipt["source_zip_sha256"],"protocol_sha256":freeze["protocol_sha256"]})
    archive=ROOT/"experiments/runs/v06"/(STEM+".tar.gz")
    archive.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,"x:gz") as tar:
        tar.add(OUT,arcname=STEM)
    write(STAGE/"archive_receipt.json",{"archive_sha256":digest(archive.read_bytes()),
        "archive_bytes":archive.stat().st_size,"optimization_calls":0})
    print(json.dumps(json.loads((STAGE/"archive_receipt.json").read_bytes())),flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("package","generate"))
    p.add_argument("--csv",default="E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/data/C3.csv")
    a=p.parse_args()
    package(a.csv) if a.mode=="package" else generate()
