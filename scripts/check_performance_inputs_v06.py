"""Independently verify generated V06 input identities and physical conflicts.

No project graph/generator/scheduler/oracle module is imported. An interval
sweep within each declared resource independently checks every conflict edge.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "experiments/runs/v06/performance_inputs_v06_001.tar.gz"
OUT = ROOT / "experiments/analysis/v06/performance_inputs_check_v06_001.json"


def digest(raw):
    return sha256(raw).hexdigest()


def physics_edges(contacts, ground_gap, satellite_gap):
    edges = set()
    for resource, gap in (("station", ground_gap), ("satellite", satellite_gap)):
        groups = defaultdict(list)
        for contact in contacts:
            groups[contact[resource]].append(contact)
        for rows in groups.values():
            active = []
            for contact in sorted(rows, key=lambda c: (c["start"], c["id"])):
                active = [old for old in active if old["end"] + gap > contact["start"]]
                for old in active:
                    edges.add(tuple(sorted((old["id"], contact["id"]))))
                active.append(contact)
    return edges


def main():
    with tarfile.open(ARCHIVE) as tar:
        prefix = "performance_inputs_v06_001/"
        blobs = {m.name[len(prefix):]: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    complete = json.loads(blobs["input_completion.json"])
    assert complete["input_generation_complete"]
    assert complete["optimization_calls"] == complete["candidate_evaluations"] == 0
    assert complete["data_sha256"] == digest(blobs["data.json"])
    assert complete["input_identity_sha256"] == digest(blobs["input_identity.json"])
    assert complete["protocol_sha256"] == digest(blobs["protocol.json"])
    data, identity = json.loads(blobs["data.json"]), json.loads(blobs["input_identity.json"])
    assert len(data["test"]) == 108 and len(data["contexts"]) == 216
    contact_ids, pair_ids = set(), set()
    checks, counts = Counter(), Counter()
    endpoint_lookup = {r["id"]: r for r in data["contexts"]}
    assert len(endpoint_lookup) == 216
    graph_ids = set()
    for pair in data["test"]:
        assert pair["split"] == "test" and pair["id"] not in pair_ids
        pair_ids.add(pair["id"])
        left, right = pair["left"], pair["right"]
        assert left["contacts"] == right["contacts"]
        ids = {c["id"] for c in left["contacts"]}
        assert len(ids) == pair["source"]["size"] and not (ids & contact_ids)
        contact_ids.update(ids)
        assert {tuple(e) for e in left["edges"]} <= {tuple(e) for e in right["edges"]}
        checks["paired_contact_identity_and_monotone_intervention"] += 1
        for side, graph, gap in (("left", left, 0.5), ("right", right, 6.0)):
            row = endpoint_lookup[pair["id"] + ":" + side]
            assert row["graph"] == graph and row["split"] == "test"
            assert row["cluster"] == pair["id"] and row["side"] == side
            graph_copy = {k: v for k, v in graph.items() if k not in ("name", "provenance")}
            graph_hash = digest(json.dumps(graph_copy, sort_keys=True).encode())
            assert graph_hash == row["graph_sha256"] and graph_hash not in graph_ids
            graph_ids.add(graph_hash)
            stored = {tuple(e) for e in graph["edges"]}
            assert len(stored) == len(graph["edges"]) == row["m"]
            expected = physics_edges(graph["contacts"], gap, 0.0)
            assert stored == expected, pair["id"] + ":" + side
            assert row["n"] == len(graph["contacts"])
            assert row["density"] == 2*len(stored)/(row["n"]*(row["n"]-1))
            for c in graph["contacts"]:
                assert c["weight"] > 0 and c["end"] > c["start"]
                assert c["weight"] * 4 == int(c["weight"] * 4)
                assert c["start"] * 4 == int(c["start"] * 4)
                assert c["end"] * 4 == int(c["end"] * 4)
            checks["every_original_contact_fields"] += len(graph["contacts"])
            checks["independent_exact_physical_edge_set"] += 1
            checks["graph_identity_metadata"] += 1
            counts[row["family"]] += 1
    assert len(contact_ids) == identity["unique_contact_ids"] == complete["unique_contact_ids"] == 129024
    assert len(graph_ids) == 216 and dict(counts) == identity["family_counts"]
    for row in identity["endpoint_identities"]:
        assert all(endpoint_lookup[row["id"]][k] == value for k, value in row.items())
    report = {"source_archive_sha256": digest(ARCHIVE.read_bytes()),
              "input_data_sha256": complete["data_sha256"],
              "input_identity_sha256": complete["input_identity_sha256"],
              "protocol_sha256": complete["protocol_sha256"],
              "check_script_sha256": digest(Path(__file__).read_bytes()),
              "pairs": 108, "endpoints": 216, "unique_contact_ids": len(contact_ids),
              "checks": dict(checks), "family_counts": dict(counts), "errors": 0,
              "optimization_calls": 0,
              "verification_scope": "independent interval sweep exact edge equality, graph hashes, full pair/endpoint/contact coverage; no optimization outcome or solver evaluated"}
    if OUT.exists():
        raise ValueError("Preserve first input validation receipt")
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
