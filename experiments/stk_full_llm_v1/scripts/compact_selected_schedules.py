"""Lossless selection-only projection of released frozen formal result files.

Never rewrite metrics or solve/score any graph. Run on the existing formal
stage directory; retain failed-job receipts independently of valid selections.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

FIELDS = ("method", "program_id", "program_arm", "source", "config", "graph_config_id", "split", "seed",
          "declared_cpu_seconds", "selected", "selected_count", "selected_set_sha256", "value_ticks", "value_exact",
          "feasible", "nodes", "edges", "cpu_seconds", "wall_seconds", "head_ever_committed", "input_graph_sha256",
          "metadata_sha256", "program_bank_sha256", "protocol_sha256", "execution_module_sha256", "graph_manifest_sha256")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--released-formal-results", action="store_true")
    a = ap.parse_args()
    if not a.released_formal_results: ap.error("Root must release frozen formal outputs before projection")
    protocol = json.loads(a.protocol.read_text(encoding="utf-8"))
    if protocol.get("frozen") is not True: raise ValueError("Frozen protocol required")
    protocol_sha = sha(a.protocol); records = []
    jobs_path = a.stage_root / "jobs.jsonl"
    jobs = [json.loads(line) for line in jobs_path.read_text(encoding="utf-8").splitlines() if line.strip()] if jobs_path.is_file() else []
    job_map = {j.get("job_id"): j for j in jobs}
    for path in sorted((a.stage_root / "results").glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("split") == "test":
            if result.get("protocol_sha256") != protocol_sha or result.get("source") not in protocol["test_sources"]:
                raise ValueError("TEST result protocol/source differs from freeze")
            if result.get("method") == "program" and (result.get("program_id") not in protocol["final_program_ids"] or result.get("program_bank_sha256") != protocol["frozen_program_bank_sha256"]):
                raise ValueError("TEST programme differs from frozen final set")
        selected = result.get("selected")
        if not isinstance(selected, list) or any(not isinstance(v, int) or isinstance(v, bool) for v in selected):
            raise ValueError("Selection must be saved exact integer node indices")
        if selected != sorted(set(selected)) or result.get("selected_count") != len(selected):
            raise ValueError("Saved selection is not unique/sorted or count differs")
        selected_sha = hashlib.sha256(json.dumps(selected).encode()).hexdigest()
        if selected_sha != result.get("selected_set_sha256"): raise ValueError("Saved selection hash differs")
        record = {k: result.get(k) for k in FIELDS}
        record.update(job_id=path.stem, result_sha256=sha(path), result_relative_path=path.relative_to(a.stage_root).as_posix(),
                      execution_status=job_map.get(path.stem, {}).get("status", "unknown"))
        records.append(record)
    if not records: raise ValueError("No released formal result files")
    out = {"version": "frozen_formal_selected_projection_v1", "records": records, "result_count": len(records),
           "failed_jobs": [j for j in jobs if j.get("status") != "complete"], "jobs_sha256": sha(jobs_path) if jobs_path.is_file() else None,
           "stage_root_provenance": str(a.stage_root), "protocol_sha256": protocol_sha, "no_graphs_opened": True,
           "optimizer_calls": 0, "model_calls": 0, "metrics_rewritten": False,
           "scope": "Saved final selected indices and identities only; quality is unchanged paid result field, not a new score."}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"results": len(records), "failed_jobs": len(out["failed_jobs"]), "sha256": sha(a.output)}))

if __name__ == "__main__": main()
