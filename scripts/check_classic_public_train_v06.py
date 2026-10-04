"""Read-only independent raw-source audit; imports no project solver/runtime."""
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
STEM = "classic_public_train_v06_001"


def digest(raw):
    return sha256(raw).hexdigest()


def parse(raw):
    weights, edges = {}, set()
    for line in raw.decode().splitlines():
        tokens = line.split()
        if tokens and tokens[0] == "n":
            weights[int(tokens[1])] = Fraction(tokens[2])
        elif tokens and tokens[0] == "e":
            edges.add(tuple(sorted((int(tokens[1]), int(tokens[2])))))
    return weights, edges


def check():
    archive = ROOT / "experiments/runs/v06" / (STEM + ".tar.gz")
    assert digest(archive.read_bytes()) == "86152347d4f8da14083c90fac8494909e0dde2feafcc09b4bd72ffbbd682039f"
    with tarfile.open(archive, "r:gz") as tar:
        protocol_raw = tar.extractfile(STEM + "/protocol.json").read()
        protocol = json.loads(protocol_raw)
        results_raw = tar.extractfile(STEM + "/results.jsonl").read()
        rows = [json.loads(line) for line in results_raw.splitlines()]
        completion = json.load(tar.extractfile(STEM + "/completion.json"))
        host = json.load(tar.extractfile(STEM + "/host_receipt.json"))
        freeze = json.load(tar.extractfile(STEM + "/freeze_receipt.json"))
        launch = json.load(tar.extractfile(STEM + "/launch_receipt.json"))
    assert digest(protocol_raw) == freeze["protocol_sha256"] == completion["protocol_sha256"] == launch["protocol_sha256"]
    assert digest(results_raw) == completion["results_sha256"]
    assert protocol["split"] == "train" and len(protocol["contexts"]) == 28
    assert completion["test_executions"] == completion["oracle_calls"] == completion["model_calls"] == 0
    assert completion["returned"] == completion["assigned"] == len(rows) == 1008
    assert protocol["repair_config"]["max_work"] is None
    expected = {(c["id"], t, m["method"], m["seed"]) for c in protocol["contexts"]
                for t in (0.1, 1, 5) for m in protocol["methods"]}
    keys = [(r["id"], r["nominal_wall_target_seconds"], r["method"], r["seed"]) for r in rows]
    assert len(keys) == len(set(keys)) and set(keys) == expected
    by_id = defaultdict(list)
    for row in rows:
        by_id[row["id"]].append(row)
    sources = {}
    for family, binding in protocol["inputs"].items():
        path = ROOT / binding["archive"]
        assert digest(path.read_bytes()) == binding["archive_sha256"]
        records = [c for c in protocol["contexts"] if c["input_family"] == family]
        with tarfile.open(path, "r:gz") as tar:
            for c in records:
                raw = tar.extractfile(binding["member_root"] + "/" + c["path"]).read()
                assert digest(raw) == c["raw_sha256"]
                sources[c["id"]] = parse(raw)
    contexts_by_file = {STEM + "/" + c["graph_file"]: c for c in protocol["contexts"]}
    checks, statuses, times = 10, Counter(), defaultdict(list)
    result_values = defaultdict(list)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if member.name not in contexts_by_file:
                continue
            c = contexts_by_file[member.name]
            graph_raw = tar.extractfile(member).read()
            assert digest(graph_raw) == c["graph_file_sha256"] == freeze["graph_files_sha256"][c["graph_file"]]
            graph = json.loads(graph_raw)
            identity = {k: v for k, v in graph.items() if k not in ("name", "provenance")}
            assert digest(json.dumps(identity, sort_keys=True).encode()) == c["graph_sha256"]
            source_weights, source_edges = sources[c["id"]]
            ids = {f"v{i:05d}": i for i in source_weights}
            assert {v["id"] for v in graph["contacts"]} == set(ids)
            for contact in graph["contacts"]:
                assert Fraction(contact["weight"]) == source_weights[ids[contact["id"]]] * c["source_weight_scale"]
                checks += 1
            edges = {tuple(sorted((ids[a], ids[b]))) for a, b in graph["edges"]}
            assert len(edges) == len(graph["edges"]) == c["m_conflict"]
            if c["input_family"] == "WDP":
                assert len(edges) + len(source_edges) == c["n"]*(c["n"]-1)//2
                assert not edges.intersection(source_edges)
            else:
                assert edges == source_edges
            assert all(1 <= a < b <= c["n"] for a, b in edges)
            checks += len(edges) + 6
            adjacency = {v: [] for v in range(1, c["n"] + 1)}
            for a, b in edges:
                adjacency[a].append(b)
                adjacency[b].append(a)
            metis = f"{c['n']} {len(edges)} 10\n" + "\n".join(
                str(int(source_weights[v] * c["source_weight_scale"])) + " " +
                " ".join(map(str, sorted(adjacency[v]))) for v in range(1, c["n"] + 1)) + "\n"
            metis_sha = digest(metis.encode())
            total = sum(source_weights.values(), Fraction()) * c["source_weight_scale"]
            for row in by_id[c["id"]]:
                assert row["split"] == "train" and row["runner_error"] is None
                assert row["graph_sha256"] == c["graph_sha256"] and row["source_sha256"] == c["raw_sha256"]
                assert row["source_weight_scale"] == c["source_weight_scale"]
                result = row["result"]
                statuses[result["status"]] += 1
                assert row["wrapper_wall_seconds"] >= 0 and row["wrapper_self_cpu_seconds"] >= 0
                times[(c["input_family"], row["method"], row["nominal_wall_target_seconds"])].append(row["wrapper_wall_seconds"])
                if result["status"] == "encoding_not_supported":
                    assert c["input_family"] == "WDP" and row["method"] in ("M2WIS", "Struction", "WeightedBR")
                    assert total > 2**31 - 1
                    assert result["value"] is result["selected"] is result["feasible"] is row["value_exact_original_objective"] is None
                    assert result["solver_invoked"] is False and result["completed"] is False
                    checks += 9
                    continue
                assert result["completed"] is True and result["feasible"] is True
                selected = result["selected"]
                assert len(selected) == len(set(selected)) and set(selected) <= ids.keys()
                selected_ids = [ids[v] for v in selected]
                for pair in combinations(selected_ids, 2):
                    pair = tuple(sorted(pair))
                    assert (pair in source_edges) if c["input_family"] == "WDP" else (pair not in source_edges)
                    checks += 1
                original = sum((source_weights[v] for v in selected_ids), Fraction())
                assert Fraction(result["value_exact"]) == original * c["source_weight_scale"]
                assert Fraction(row["value_exact_original_objective"]) == original
                if row["method"] != "Degree":
                    assert result["input_sha256"] == metis_sha and result["integer_scale"] == 1
                    name = "CHILS" if row["method"] == "CHILS_ILS" else row["method"]
                    assert result["executable_sha256"] == protocol["executables"][name]["sha256"]
                    assert result["declared_seconds"] == row["nominal_wall_target_seconds"]
                    assert result["hard_wall_seconds"] == 30 and result["child_cpu_seconds"] >= 0
                else:
                    assert result["meter"].get("feature_work", 0) == 0
                result_values[(c["input_family"], row["method"], row["nominal_wall_target_seconds"])].append(str(original))
                checks += 14
    assert statuses == Counter(completion["status_counts"])
    assert statuses["encoding_not_supported"] == 375
    assert sum(v for k, v in statuses.items() if k != "encoding_not_supported") == 633
    import statistics
    groups = [{"input_family": key[0], "method": key[1], "target": key[2],
               "requests": len(values), "null_rewards": len(values)-len(result_values[key]),
               "median_wrapper_wall_seconds": statistics.median(values),
               "mean_original_objective_exact": (str(sum(map(Fraction, result_values[key]), Fraction()) / len(result_values[key]))
                                                 if result_values[key] else None)} for key, values in sorted(times.items())]
    report = {"errors": 0, "independent_implementation_checks": checks,
        "auditor_scope": "Separate audit implementation by execution agent; not a separate-person audit; no project runtime imported and no solver or oracle called",
        "archive_sha256": digest(archive.read_bytes()), "source_zip_sha256": protocol["source_zip_sha256"],
        "protocol_sha256": digest(protocol_raw), "results_sha256": digest(results_raw),
        "audit_source_sha256": digest(Path(__file__).read_bytes()), "all_1008_assignment_keys_verified": True,
        "all_28_exact_source_graph_mappings_verified": True, "all_633_incumbents_source_feasible_and_exact": True,
        "all_375_input_limits_are_null": True, "status_counts": dict(statuses),
        "groups": groups, "cloud_host": host, "test_solver_calls": 0,
        "quality_scope": "Raw original objective by source family; no optimum normalization or cross-family quality pooling",
        "timing_scope": "Nominal native internal wall versus cooperative Degree timer; end-to-end wrapper and shared loading reported, not claimed hard-budget equivalent"}
    path = ROOT / "experiments/analysis/v06/classic_public_train_check_v06_001.json"
    path.write_bytes((json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode())
    print(json.dumps({"errors": 0, "checks": checks, "assigned": 1008, "feasible": 633, "input_limits": 375}))


if __name__ == "__main__":
    check()
