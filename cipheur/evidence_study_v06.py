"""New graph/state evidence: freeze every query before any offline certificate.

Public source splits refer to new states within an already exposed corpus.
Synthetic contacts follow the declared physical pairwise model. No outcome is
consulted by preparation; TEST certificates require a subsequent program freeze.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import random
import tarfile
import time

from .graph_features import FeatureRuleProgram
from .model import Contact, Graph, temporal_graph
from .public_alias_v05 import induced_subset
from .representation import vector_key
from .relevance_synthesis_v04 import CancelledCompletionOracle

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = "experiments/runs/v04/public_data_v04_002.tar.gz"
PUBLIC_SHA = "e13f8d925fc59c900f772f0c7a9dace376cfd2c188f836b82bf20b49419970d3"
SALT = "v06_261003_new_source_state_queries_001"
BASE = FeatureRuleProgram("base_v06_evidence", [], "weight")
ORACLE = {"nodes_per_component": 50000, "max_search_component": 32,
          "max_nodes": 2000000, "max_calls": 1024}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n").encode("utf-8"))


def ordering(text):
    return sha256((SALT + "|" + text).encode()).digest()


def queries(graphs, identity):
    """Up to eight alias and eight nonalias common edges; labels unknown."""
    common = set.intersection(*(set(g.edges) for g in graphs))
    features = [{v: BASE.evaluate_features(g, v, set(g.nodes))
                 for v in sorted(g.nodes)} for g in graphs]
    groups = {"alias": [], "control": []}
    for a, b in sorted(common, key=lambda e: ordering(identity + "|" + "|".join(e))):
        alias = [vector_key(v[a]) == vector_key(v[b]) for v in features]
        kind = "alias" if any(alias) else "control"
        groups[kind].append({"a": a, "b": b, "kind": kind,
                             "base_alias_by_side": alias})
    chosen = [row for kind in ("alias", "control") for row in groups[kind][:8]]
    return chosen, {kind: {"eligible": len(rows), "planned": min(8, len(rows)),
                          "shortfall": max(0, 8-len(rows))}
                    for kind, rows in groups.items()}


def source_hashes():
    names = ("evidence_study_v06.py", "model.py", "graph_features.py",
             "programs.py", "representation.py", "public_alias_v05.py",
             "relevance_synthesis_v04.py", "oracle.py", "refinement.py",
             "compiled.py")
    return {name: digest(Path(__file__).parent/name) for name in names}


def prepare(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Preserve the registered V06 input/query plan")
    archive = ROOT/PUBLIC
    assert digest(archive) == PUBLIC_SHA
    with tarfile.open(archive) as tar:
        member = [m for m in tar.getmembers() if m.name.endswith("/data.json")]
        assert len(member) == 1
        raw = tar.extractfile(member[0]).read()
    original = [r for r in json.loads(raw)["public"]
                if r["source"]["weight_mode"] == "unit"]
    assert len(original) == len({r["cluster"] for r in original}) == 48
    records, public_split = [], {}
    for family in ("DIMACS", "SATLIB"):
        population = sorted((r for r in original if r["family"] == family),
                            key=lambda r: ordering("source-split|"+r["cluster"]))
        for i, r in enumerate(population):
            split = "train" if i < len(population)//2 else "test"
            public_split[r["cluster"]] = split
            g = induced_subset(Graph.from_dict(r["graph"]), r["id"], 32, SALT)
            plan, quota = queries([g], "public|"+r["id"])
            records.append({"id": "v06_public32|"+r["id"], "split": split,
                "family": family, "cluster": r["cluster"], "paired": False,
                "graph": g.to_dict(), "graph_digest": g.digest(),
                "fixed": [], "excluded": [], "queries": plan, "quota": quota,
                "source": {"id": r["id"], "graph_digest": Graph.from_dict(r["graph"]).digest(),
                           "metadata": r["source"], "subset_salt": SALT},
                "scope": "new induced state in previously exposed public corpus"})
    for split, count in (("train", 8), ("test", 4)):
        for regime, resources in (("balanced", (8, 6)), ("ground_scarce", (12, 3)),
                                  ("satellite_scarce", (3, 12))):
            for profile, horizon in (("short", 11), ("long", 24)):
                for index in range(count):
                    name = f"v06_unit_{split}_{regime}_{profile}_{index:03d}"
                    seed = int.from_bytes(ordering(name)[:8], "big")
                    rng = random.Random(seed)
                    contacts = []
                    for i in range(32):
                        start = rng.randrange(horizon*4)/4
                        contacts.append(Contact(f"v{i:03d}", 1, f"S{rng.randrange(resources[0])}",
                            f"G{rng.randrange(resources[1])}", start, start+1))
                    gaps = (0, 1) if split == "train" else (.25, 2)
                    gs = [temporal_graph(name+f"_{side}", contacts, gap, 0)
                          for side, gap in zip(("left", "right"), gaps)]
                    plan, quota = queries(gs, name)
                    for side, g in zip(("left", "right"), gs):
                        records.append({"id": name+":"+side, "pair": name, "side": side,
                            "split": split, "family": "temporal_unit_"+regime+"_"+profile,
                            "cluster": name, "paired": True, "graph": g.to_dict(),
                            "graph_digest": g.digest(), "fixed": [], "excluded": [],
                            "queries": plan, "quota": quota,
                            "source": {"seed": seed, "station_gaps": list(gaps),
                                       "outcome_filtering": False, "unit_duration_reward": True},
                            "scope": "synthetic single-capacity physical pairwise model; not C3"})
    assert len(records) == 192
    digests = [r["graph_digest"] for r in records]
    train = {r["graph_digest"] for r in records if r["split"] == "train"}
    test = {r["graph_digest"] for r in records if r["split"] == "test"}
    assert not train & test and len(digests) == len(set(digests))
    output.mkdir(parents=True)
    protocol = {"version": "v06_evidence_query_plan_001", "before_any_oracle_query": True,
        "salt": SALT, "query_order": "SHA order, alias8 then nonalias8 on common competing edges",
        "all_quota_shortfalls_retained": True, "oracle": ORACLE, "workers": 8,
        "test_query_requires_program_freeze": True, "public_input": PUBLIC,
        "public_input_sha256": PUBLIC_SHA, "public_input_member_sha256": sha256(raw).hexdigest(),
        "public_source_split": public_split, "prior_public_corpus_exposed": True,
        "counts": dict(Counter(r["split"] for r in records)),
        "data_generation_outcome_queries": 0, "physical_source_claim": False}
    write(output/"data.json", {"records": records, "protocol": protocol})
    write(output/"protocol.json", protocol)
    write(output/"freeze_receipt.json", {"data_sha256": digest(output/"data.json"),
        "protocol_sha256": digest(output/"protocol.json"), "source_sha256": source_hashes(),
        "before_any_oracle_query": True})
    print(json.dumps({"prepared": str(output), "counts": protocol["counts"],
                      "queries": sum(len(r["queries"]) for r in records)}), flush=True)


def run_state(record):
    started = time.process_time()
    g = Graph.from_dict(record["graph"])
    assert g.digest() == record["graph_digest"]
    oracle = CancelledCompletionOracle(g, record["fixed"], record["excluded"], **ORACLE)
    rows = [{**query, "difference": oracle.difference(query["a"], query["b"])}
            for query in record["queries"]]
    return {"id": record["id"], "split": record["split"], "family": record["family"],
            "cluster": record["cluster"], "graph_digest": g.digest(), "rows": rows,
            "oracle_budget": oracle.receipt(), "quota": record["quota"],
            "cpu_seconds": time.process_time()-started}


def run(plan, output, split, freeze=None):
    plan, output = Path(plan), Path(output)
    receipt = json.loads((plan/"freeze_receipt.json").read_text(encoding="utf-8"))
    assert receipt["before_any_oracle_query"] and receipt["source_sha256"] == source_hashes()
    assert receipt["data_sha256"] == digest(plan/"data.json")
    assert receipt["protocol_sha256"] == digest(plan/"protocol.json")
    frozen_hash = None
    if split == "test":
        if freeze is None:
            raise ValueError("Freeze selected programmes before TEST certificates")
        frozen = json.loads(Path(freeze).read_text(encoding="utf-8"))
        assert frozen["test_accessed"] is False and frozen["selection_split"] == "train"
        assert frozen["programs"]
        frozen_hash = digest(freeze)
    if output.exists():
        raise ValueError("Never overwrite registered query outcomes")
    records = [r for r in json.loads((plan/"data.json").read_text(encoding="utf-8"))["records"]
               if r["split"] == split]
    output.mkdir(parents=True)
    for name in ("data.json", "protocol.json", "freeze_receipt.json"):
        (output/name).write_bytes((plan/name).read_bytes())
    write(output/"execution.json", {"split": split, "programme_freeze_sha256": frozen_hash,
                                   "source_sha256": source_hashes(), "workers": 8})
    rows = []
    with (output/"results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(run_state, r) for r in records]
            for future in as_completed(futures):
                row = future.result()
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+"\n")
                stream.flush()
                rows.append(row)
    status = Counter(q["difference"]["status"] for r in rows for q in r["rows"])
    write(output/"complete.json", {"execution_complete": True, "split": split,
        "states": len(rows), "query_status": dict(status),
        "query_shortfalls": sum(v["shortfall"] for r in rows for v in r["quota"].values()),
        "results_sha256": digest(output/"results.jsonl"), "unknowns_retained": True,
        "programme_freeze_sha256": frozen_hash})
    print(json.dumps({"complete": str(output), "states": len(rows), "status": dict(status)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="mode", required=True)
    q = s.add_parser("prepare"); q.add_argument("--out", required=True)
    q = s.add_parser("run"); q.add_argument("--plan", required=True)
    q.add_argument("--out", required=True); q.add_argument("--split", choices=("train", "test"), required=True)
    q.add_argument("--frozen")
    a = p.parse_args()
    if a.mode == "prepare": prepare(a.out)
    else: run(a.plan, a.out, a.split, a.frozen)
