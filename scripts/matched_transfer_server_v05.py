"""Frozen cross-host replay; reuse the exact local runner, with new storage only.

Only paths/study identity and execution receipt metadata are adapted. Programs,
graphs, U/L, scorer, feasibility kernel, method rotation and CPU cap are unchanged.
Credentials and transport helper are excluded from every public capsule.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import matched_transfer_exploratory_v05 as original

STEM = "matched_transfer_server_v05_001"
OLD_STEM = "matched_transfer_exploratory_v05_001"
STUDY = ROOT / "experiments/discovery" / STEM
CAPSULE = ROOT / "experiments/source_snapshots/v05" / (STEM + "_source.zip")
RECEIPT = CAPSULE.with_name(STEM + "_source_receipt.json")
CONFIG = ROOT / "configs/matched_transfer_server_v05.json"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def prepare():
    old_protocol, frozen, cases = original.check_freeze()
    old_archive = ROOT / "experiments/runs/v05" / (OLD_STEM + ".tar.gz")
    config = original.load(CONFIG)
    assert len(cases) == 120 and config["workers"] == 8 and config["program_cpu_seconds"] == 5
    if STUDY.exists() or CAPSULE.exists():
        raise ValueError("Preserve the locked server replay; no replacement")
    STUDY.mkdir(parents=True)
    for name in ("data.json", "frozen_programs.json", "budget_scope_clarification.json"):
        shutil.copyfile(original.STUDY / name, STUDY / name)
    protocol = {**old_protocol, "version": STEM, "before_any_extension_execution": True,
        "design": "Cross-host replay of the same completed local exploratory transfer; not new independent evidence",
        "workers": 8, "program_cpu_seconds": 5, "hard_wall_safety_no_context_progress_seconds": 1800,
        "same_complete_assignment_inventory": True, "replay_of": OLD_STEM,
        "original_local_protocol_sha256": digest(original.STUDY / "protocol.json"),
        "original_local_source_zip_sha256": digest(original.CAPSULE),
        "original_local_archive_sha256": digest(old_archive),
        "original_local_runner_sha256": digest(ROOT / "scripts/matched_transfer_exploratory_v05.py"),
        "config_sha256": digest(CONFIG), "data_sha256": digest(STUDY / "data.json"),
        "frozen_programs_sha256": digest(STUDY / "frozen_programs.json"),
        "pre_execution_reference_checks": sum(original.verify_reference(c) for c in cases),
        "execution_adaptation": "Reuse the exact original run and analyze callables; override only new storage paths/study name and append read-only host metadata to execution.json. No scoring, scheduling, failure handling, assignment ordering or denominator changes.",
        "budget_scope": "The same execute backend starts actual CPU/wall timers before AST parsing, then constructs the 5-process-CPU-second cooperative meter after parse. Compiled evaluator initialization, queries, updates and scheduling are capped; actual cost includes parsing, verification and overshoot. Graph/source materialization remains separately recorded.",
        "server_allocation": "Preflight visible192 CPUs, cgroup quota16 CPU equivalents; use8 workers to leave half the CPU quota available, without interrupting another task.",
        "server_expected_host_key_sha256": "52ff51e92c8303ac6500b5f9a365df24295acaef2451d911e1dcc1a116705210",
        "runtime": "/root/autodl-tmp/aamas2027_v03/py311/bin/python (existing Python3.11.17, no environment installation)",
        "physical_source": "/root/autodl-tmp/aamas2027_v03/baselines/SNSD_V51_FINAL/data/C3.csv",
        "prior_matched_2808_origin": "Already executed on this same server: /root/autodl-tmp/aamas2027_v05_matched_001/matched_eval_v05_001.tar.gz; SHA exactly matches the audited local copy. No new authors or TRAIN selection are run.",
        "prior_matched_2808_archive_sha256": "acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680",
        "cross_host_comparison": "Retain both archives. Compare all1560 method/context pairs for completion status and, only where both complete, exact reward, selected sets and full saved decision traces/scores. Report all differences; no replacement or host-based selection."}
    original.write(STUDY / "protocol.json", protocol)
    files = sorted((ROOT / "cipheur").glob("*.py")) + [ROOT / "scripts/matched_transfer_exploratory_v05.py", Path(__file__), CONFIG]
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in files}
    original.write(STUDY / "freeze_receipt.json", {"version": STEM, "before_any_extension_execution": True,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol_sha256": digest(STUDY / "protocol.json"), "data_sha256": digest(STUDY / "data.json"),
        "frozen_programs_sha256": digest(STUDY / "frozen_programs.json"), "source_sha256": sources})
    files += sorted(STUDY.glob("*.json"))
    CAPSULE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CAPSULE, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    original.write(RECEIPT, {"version": STEM, "before_any_extension_execution": True,
        "source_zip_sha256": digest(CAPSULE), "file_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in files}})
    print(json.dumps({"protocol_sha256": digest(STUDY / "protocol.json"), "source_zip_sha256": digest(CAPSULE), "assignments": 1560, "workers": 8}), flush=True)


def configure():
    original.STEM, original.STUDY = STEM, STUDY
    original.CAPSULE, original.CAPSULE_RECEIPT, original.CONFIG = CAPSULE, RECEIPT, CONFIG


def host_receipt():
    cgroup = {}
    for path in ("/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/cpuset.cpus.effective"):
        p = Path(path)
        cgroup[path] = p.read_text().strip() if p.is_file() else None
    mem = {}
    p = Path("/proc/meminfo")
    if p.is_file():
        for line in p.read_text().splitlines():
            k, v = line.split(":", 1)
            if k in ("MemTotal", "MemAvailable"):
                mem[k] = v.strip()
    existing = Path("/root/autodl-tmp/aamas2027_v05_matched_001/matched_eval_v05_001.tar.gz")
    return {"platform": platform.platform(), "python": sys.version, "python_executable": sys.executable,
        "cpu_count": os.cpu_count(), "affinity_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "cgroup": cgroup, "memory": mem, "workers": 8, "existing_server_matched_2808_archive_sha256": digest(existing) if existing.is_file() else None,
        "persistent_detached_log": True, "no_other_task_interrupted": True}


def run(output, stable_root):
    configure()
    protocol, _, _ = original.check_freeze()
    host = host_receipt()
    assert host["existing_server_matched_2808_archive_sha256"] == protocol["prior_matched_2808_archive_sha256"]
    csv = Path(stable_root) / "SNSD_V51_FINAL/data/C3.csv"
    host["C3_csv_sha256"] = digest(csv)
    assert host["C3_csv_sha256"] == "ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e"
    write = original.write
    def with_host_receipt(path, value):
        if Path(path).name == "execution.json":
            value = {**value, "server_host_receipt": host, "cross_host_replay_of": OLD_STEM,
                     "original_local_archive_sha256": protocol["original_local_archive_sha256"]}
        return write(path, value)
    original.write = with_host_receipt
    original.run(output, stable_root)


def rows(path, stem):
    with tarfile.open(path, "r:gz") as tar:
        records = [json.loads(x) for x in tar.extractfile(stem + "/results.jsonl") if x.strip()]
        data_hash = sha256(tar.extractfile(stem + "/data.json").read()).hexdigest()
        frozen_hash = sha256(tar.extractfile(stem + "/frozen_programs.json").read()).hexdigest()
    return {(r["id"], m["method"]): m for r in records for m in r["rows"]}, data_hash, frozen_hash


def compare():
    configure()
    original.analyze()
    old = ROOT / "experiments/runs/v05" / (OLD_STEM + ".tar.gz")
    new = ROOT / "experiments/runs/v05" / (STEM + ".tar.gz")
    local, local_data, local_frozen = rows(old, OLD_STEM)
    server, server_data, server_frozen = rows(new, STEM)
    assert local.keys() == server.keys() and len(local) == 1560
    assert local_data == server_data and local_frozen == server_frozen
    status, differences, per_method = Counter(), [], defaultdict(Counter)
    for key in sorted(local):
        a, b = local[key], server[key]
        category = "both_complete" if a["completed"] and b["completed"] else "local_only_complete" if a["completed"] else "server_only_complete" if b["completed"] else "neither_complete"
        status[category] += 1
        per_method[key[1]][category] += 1
        if a["completed"] and b["completed"]:
            equal = {"exact_reward": a["value_exact"] == b["value_exact"], "selected_set": a["selected"] == b["selected"],
                "decision_trace": a["trace"] == b["trace"], "trace_choices_counts": [(t["selected"],t["remaining_count"]) for t in a["trace"]] == [(t["selected"],t["remaining_count"]) for t in b["trace"]]}
            for field, value in equal.items():
                status[field + ("_equal" if value else "_different")] += 1
            if not all(equal.values()):
                differences.append({"context": key[0], "method": key[1], "kind": "both_complete_semantic_or_score_difference", "equal": equal, "local_value_exact": a["value_exact"], "server_value_exact": b["value_exact"]})
        elif a["completed"] != b["completed"] or a["status"] != b["status"]:
            differences.append({"context": key[0], "method": key[1], "kind": "completion_or_failure_difference", "local_status": a["status"], "server_status": b["status"],
                "local_cpu_seconds": a["cpu_seconds"], "server_cpu_seconds": b["cpu_seconds"]})
    target = ROOT / "experiments/analysis/v05/matched_transfer_cross_host_v05_001.json"
    original.write(target, {"version": "matched_transfer_cross_host_v05_001", "local_archive_sha256": digest(old), "server_archive_sha256": digest(new),
        "data_sha256": local_data, "frozen_programs_sha256": local_frozen, "assignment_pairs": 1560,
        "counts": dict(status), "per_method_completion": {k:dict(v) for k,v in per_method.items()}, "all_differences": differences,
        "interpretation": "Cross-host computational replay on identical already-observed inputs; no new independent scheduling population or authoring. Both outcomes retained, no replacement or selection. Process CPU is host-specific; the shared nominal deadline does not make different processors/interpreters equivalent."})
    md = ["# Server replay and cross-host receipt V05", "", "The same twelve frozen TRAIN winners and compiled Degree were replayed on the same 120 contexts, giving1,560 assignments. No authoring, TRAIN selection, oracle queries, reference updates or local-result overwrites occurred. The separately stored server archive is the server evidence; the old local archive is retained.", "",
        "The prior matched216-context/2,808-assignment evaluation was already run on this same server. Its server archive SHA `acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680` exactly matches the old audited local copy. It does not require a new authoring or TRAIN run.", "", "## Matched execution counts", "", "| Category | Count |", "|---|---:|"]
    md += [f"| {k} | {v} |" for k,v in status.items()]
    md += ["", "The cross-host JSON retains every changed completion/failure status and every semantic/score difference among jointly completed runs. CPU cap outcomes can differ with host throughput and interpreter version. This is execution robustness, not a new algorithm or LLM causal effect. No old native C++ timings are pooled with these new Python assignments.", "",
        "Local archive SHA: `" + digest(old) + "`", "Server archive SHA: `" + digest(new) + "`", "Data SHA: `" + local_data + "`", "Frozen winners SHA: `" + local_frozen + "`", ""]
    target.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"comparison": str(target), "counts": dict(status), "difference_records": len(differences)}), flush=True)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("prepare", "run", "compare"))
    p.add_argument("--output", default=str(ROOT / "runs" / STEM))
    p.add_argument("--stable-root", default="/root/autodl-tmp/aamas2027_v03/baselines")
    a = p.parse_args()
    if a.command == "prepare": prepare()
    elif a.command == "run": run(a.output, a.stable_root)
    else: compare()
