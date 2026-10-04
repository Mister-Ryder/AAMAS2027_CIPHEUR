"""Read-only coverage/accounting for archived V06 TRAIN certificates."""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "experiments/runs/v06/v06_evidence_train_001.tar.gz"
PREFIX = "v06_evidence_train_001/"
OUT = ROOT / "experiments/analysis/v06/evidence_server_train_001.json"


def digest(raw):
    return sha256(raw).hexdigest()


def main():
    with tarfile.open(ARCHIVE) as tar:
        files = {m.name[len(PREFIX):]: tar.extractfile(m).read()
                 for m in tar.getmembers() if m.isfile() and m.name.startswith(PREFIX)}
    get = lambda name: json.loads(files[name])
    complete, original, capsule, budget = (get(n) for n in
        ("complete.json", "freeze_receipt.json", "capsule_receipt.json", "execution_budget_receipt.json"))
    assert complete["execution_complete"] and complete["split"] == "train"
    assert digest(files["results.jsonl"]) == complete["results_sha256"]
    assert digest(files["data.json"]) == original["data_sha256"]
    assert digest(files["protocol.json"]) == original["protocol_sha256"]
    assert digest(files["BUDGET_SCOPE.json"]) == budget["budget_scope_sha256"]
    assert digest(files["execution.json"]) == budget["original_execution_sha256"]
    assert digest(files["complete.json"]) == budget["original_complete_sha256"]
    assert digest(files["execution_host_receipt.json"]) == budget["execution_host_receipt_sha256"]
    assert budget["test_queries_run"] == 0 and budget["query_retries"] == 0
    assert capsule["source_zip_sha256"] == budget["source_zip_sha256"]
    inputs = {r["id"]: r for r in get("data.json")["records"] if r["split"] == "train"}
    results = [json.loads(line) for line in files["results.jsonl"].splitlines()]
    assert len(results) == len(inputs) == 120
    assert len({r["id"] for r in results}) == len(results)
    assert {r["id"] for r in results} == set(inputs)
    total, by_family, by_actual_alias = Counter(), defaultdict(Counter), defaultdict(Counter)
    pairs = defaultdict(dict)
    calls, nodes, times = [], [], []
    for result in results:
        plan = inputs[result["id"]]
        assert result["graph_digest"] == plan["graph_digest"] and result["split"] == "train"
        assert result["quota"] == plan["quota"]
        assert len(result["rows"]) == len(plan["queries"])
        meter = result["oracle_budget"]
        assert meter["max_calls"] == 1024 and meter["max_nodes"] == 2000000
        assert meter["calls"] <= 1024 and meter["expanded_nodes"] <= 2000000
        calls.append(meter["calls"]); nodes.append(meter["expanded_nodes"]); times.append(result["cpu_seconds"])
        for row, query in zip(result["rows"], plan["queries"]):
            assert {k: row[k] for k in query} == query
            difference = row["difference"]
            assert difference["a"] == query["a"] and difference["b"] == query["b"]
            lower, upper = Fraction(difference["lower_exact"]), Fraction(difference["upper_exact"])
            assert lower <= upper
            status = difference["status"]
            if status == "strict":
                assert lower > 0 or upper < 0
                assert difference["preferred"] == (row["a"] if lower > 0 else row["b"])
            elif status == "exact_tie":
                assert lower == upper == 0 and difference["preferred"] is None
            side = 0 if len(query["base_alias_by_side"]) == 1 or plan.get("side") == "left" else 1
            actual_alias = query["base_alias_by_side"][side]
            total[status] += 1
            by_family[result["family"]][status] += 1
            by_actual_alias[str(actual_alias).lower()][status] += 1
            if plan["paired"]:
                pairs[(plan["pair"], row["a"], row["b"])][plan["side"]] = {
                    "status": status, "preferred": difference["preferred"], "alias": actual_alias}
    paired = Counter()
    for rows in pairs.values():
        assert set(rows) == {"left", "right"}
        a, b = rows["left"], rows["right"]
        if a["status"] == b["status"] == "strict":
            paired["strict_reversal" if a["preferred"] != b["preferred"] else "strict_preservation"] += 1
        elif a["status"] == b["status"] == "exact_tie":
            paired["tie_both_sides"] += 1
        elif {a["status"], b["status"]} <= {"strict", "exact_tie"}:
            paired["strict_one_side_tie_other"] += 1
        else:
            paired["unknown_or_unclassified"] += 1
    assert dict(total) == complete["query_status"]
    assert sum(total.values()) == 1503
    report = {"archive_sha256": digest(ARCHIVE.read_bytes()),
              "source_zip_sha256": capsule["source_zip_sha256"],
              "original_protocol_sha256": original["protocol_sha256"],
              "budget_scope_sha256": budget["budget_scope_sha256"],
              "results_sha256": complete["results_sha256"],
              "host_receipt_sha256": budget["execution_host_receipt_sha256"],
              "analysis_script_sha256": digest(Path(__file__).read_bytes()),
              "states": len(results), "queries": sum(total.values()),
              "query_status": dict(total), "by_family": dict(by_family),
              "by_actual_side_base_alias": dict(by_actual_alias),
              "paired_query_pairs": len(pairs), "paired_labels": dict(paired),
              "query_shortfalls": complete["query_shortfalls"],
              "oracle_calls_total": sum(calls), "oracle_calls_max_state": max(calls),
              "expanded_nodes_total": sum(nodes), "expanded_nodes_max_state": max(nodes),
              "cpu_seconds_state_sum": sum(times), "wall_seconds": budget["total_wall_seconds"],
              "test_queries": 0, "query_retries": 0, "guard_triggered": budget["whole_run_guard_triggered"],
              "label_scope": "TRAIN conditional-value certificates, not scheduling improvements or LLM benefits",
              "alias_scope": "preselected kind is any-side alias; counts above use actual per-side boolean",
              "public_scope": "new induced32 source-disjoint TRAIN/TEST states within previously exposed corpus"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        raise ValueError("Keep the first accounting receipt")
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
