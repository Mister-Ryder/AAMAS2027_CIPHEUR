"""R2 warm-seed TRAIN assessment with separately frozen deployment roles.

R1's failed twelve-winner barrier is immutable. R2 retains the same candidate
assessor and information gate, while objective-selected comparators are named
separately from genuine witness-guided proposed-program winners.
"""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
import json
from pathlib import Path
import platform

from .synthesis_study_v06 import ARMS, assess_candidate, canonical, digest, select_cells, selection_key, validate_response, write


def load_bank(study):
    study = Path(study)
    proto = json.loads((study / "protocol.json").read_bytes())
    freeze = json.loads((study / "freeze_receipt.json").read_bytes())
    complete = json.loads((study / "authoring_completion.json").read_bytes())
    runtime = json.loads((study / "transport_runtime_binding.json").read_bytes())
    if (proto["version"] != "matched_refinement_round_v06_002" or proto["blocks"] != 5
        or proto["slots_per_block_arm"] != 8 or proto["arms"] != list(ARMS)
        or digest(study / "protocol.json") != freeze["protocol_sha256"]
        or not freeze["before_round2_authoring"]
        or complete["version"] != "R2_matched_cli_authoring_completion_v06"
        or complete["protocol_sha256"] != digest(study / "protocol.json")
        or not complete["all15_R2_requests_frozen_before_assessment"]
        or not complete["same_requested_model_and_settings_all_cells"]
        or complete["transport_runtime_binding_sha256"] != digest(study / "transport_runtime_binding.json")):
        raise ValueError("All15 R2 authoring sessions must be immutably frozen")
    for name, expected in proto["packet_sha256"].items():
        if digest(study / name) != expected:
            raise ValueError("Frozen R2 packet changed: " + name)
    if digest(study / "training_evidence.json") != proto["training_evidence_sha256"]:
        raise ValueError("Frozen R2 TRAIN evidence changed")
    names = {f"block_{b}_{a}.json" for b in range(5) for a in ARMS}
    if set(complete["response_sha256"]) != names:
        raise ValueError("R2 completion does not cover all fifteen requests")
    bank, transport = [], []
    # Compute transport inclusion without inspecting candidate contents.
    for block in range(5):
        for arm in ARMS:
            stem = f"block_{block}_{arm}"
            path = study / "responses" / (stem + ".json")
            receipt = json.loads((study / "receipts" / (stem + ".receipt.json")).read_bytes())
            if (digest(path) != complete["response_sha256"][stem + ".json"]
                or digest(path) != receipt["response_sha256"]
                or receipt["requested_configuration"] != runtime["requested_configuration"]
                or receipt["packet_sha256"] != digest(study / "packets" / (stem + ".json"))):
                raise ValueError("R2 transport/source binding changed")
            transport.append({"block": block, "arm": arm,
                "complete_transport": receipt["exit_code"] == 0 and not receipt["timed_out"] and path.stat().st_size > 0,
                "receipt_sha256": digest(study / "receipts" / (stem + ".receipt.json"))})
    matched = [b for b in range(5) if all(x["complete_transport"] for x in transport if x["block"] == b)][:4]
    for block in range(5):
        for arm in ARMS:
            path = study / "responses" / f"block_{block}_{arm}.json"
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                payload = None
            bank.extend(validate_response(payload, block, arm, 8))
    return proto, bank, transport, matched


def quality_key(row):
    return (-Fraction(row["kernel_summary"]["macro_quality_exact"]),
            Fraction(row["kernel_summary"]["macro_work_exact"]), row["slot"])


def quality_covered(row):
    return (row.get("assessment_status") == "assessed" and row.get("kernel_summary") is not None
        and len(row.get("kernel_rows", [])) == 120
        and all(r["result"]["completed"] and r["result"]["feasible"] for r in row["kernel_rows"]))


def deployment_selection(rows, matched):
    joint, empty, prefixes = select_cells(rows, 5)
    quality = []
    for block in range(5):
        for arm in ARMS:
            eligible = [r for r in rows if r["block"] == block and r["arm"] == arm and quality_covered(r)]
            winner = min(eligible, key=quality_key) if eligible else None
            quality.append({"block": block, "arm": arm, "winner": winner})
    required = [r for r in joint if r["block"] in matched and r["arm"] == "witness"]
    quality_matched = [r for r in quality if r["block"] in matched]
    fields = ("id", "block", "arm", "slot", "program", "program_sha256", "eligible")
    programs = [{**{k: r[k] for k in fields}, "id": "joint|" + r["id"],
        "source_candidate_id": r["id"], "role": "proposed_witness_joint", "joint_gate_required": True}
        for r in required]
    for cell in quality_matched:
        r = cell["winner"]
        programs.append({**({k: r[k] for k in fields} if r else {"block": cell["block"], "arm": cell["arm"], "slot": None,
            "program": None, "program_sha256": None, "eligible": False}),
            "id": "quality|" + (r["id"] if r else f"block_{cell['block']}_{cell['arm']}:missing"),
            "source_candidate_id": r["id"] if r else None,
            "role": "nonguarded_quality_comparator", "joint_gate_required": False,
            "missing_baseline": r is None})
    return {"matched_transport_complete_blocks": matched,
        "all_uniform_joint_winners": [{k: r[k] for k in fields} for r in joint],
        "all_uniform_empty_joint_cells": empty, "all_raw_joint_prefixes": prefixes,
        "all_uniform_quality_winners": [{"block": c["block"], "arm": c["arm"],
            "winner": {k: c["winner"][k] for k in fields} if c["winner"] else None} for c in quality],
        "proposed_witness_joint_count": len(required),
        "ready_for_TEST": len(matched) == 4 and len(required) == 4,
        "programs": programs, "quality_comparator_requested_count": len(quality_matched),
        "quality_comparator_missing_cells": [{"block": c["block"], "arm": c["arm"]} for c in quality_matched if c["winner"] is None],
        "no_fallback": True, "R1_barrier_remains_failed": True}


def train(study, out, workers=8):
    if platform.system() != "Linux":
        raise ValueError("R2 research assessment is server-only")
    study, out = Path(study), Path(out)
    if out.exists():
        raise ValueError("Never overwrite original R2 assessments")
    proto, bank, transport, matched = load_bank(study)
    for name, expected in proto["all_unchanged_assessment_sources"].items():
        if digest(Path(__file__).parent / name) != expected:
            raise ValueError("Original information/feasibility runtime changed: " + name)
    for key, name in (("assessment", "synthesis_study_v06.py"), ("kernel", "repair_v06.py"),
                      ("typed_library", "graph_features.py"), ("compiled_runtime", "compiled.py")):
        if digest(Path(__file__).parent / name) != proto["source_sha256"][key]:
            raise ValueError("Frozen assessment source changed: " + name)
    runtime = json.loads((study / "transport_runtime_binding.json").read_bytes())
    if digest(__file__) != runtime["R2_assessment_sha256"]:
        raise ValueError("Frozen R2 selector/assessment source changed")
    if digest(study / "selection_plan.json") != proto["selection_plan_sha256"]:
        raise ValueError("Frozen R2 deployment roles changed")
    evidence = json.loads((study / "training_evidence.json").read_bytes())
    if len(evidence["records"]) != 120 or any(r["split"] != "train" for r in evidence["records"]):
        raise ValueError("R2 uses the identical original120 TRAIN states only")
    if len(bank) != 120:
        raise ValueError("Keep all120 R2 original positions")
    out.mkdir(parents=True)
    write(out / "bank.json", bank)
    write(out / "execution.json", {"all15_R2_requests_frozen_before_assessment": True,
        "protocol_sha256": digest(study / "protocol.json"), "source_sha256": proto["source_sha256"],
        "bank_sha256": digest(out / "bank.json"), "matched_transport_complete_blocks": matched,
        "transport_cells": transport, "workers": workers, "TEST_accessed": False})
    rows = []
    with (out / "candidate_results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(assess_candidate, (entry, evidence, proto)): entry for entry in bank}
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception as error:
                    row = {**futures[future], "eligible": False, "kernel_rows": [],
                        "assessment_status": "assessment_worker_error", "error_type": type(error).__name__, "error": str(error)}
                rows.append(row); stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); stream.flush()
                print(json.dumps({"assessed_R2": row["id"], "eligible": row["eligible"],
                    "strict_fit": row.get("interface", {}).get("strict_passed")}), flush=True)
    selected = deployment_selection(rows, matched)
    write(out / "selection.json", {"version": "v06_R2_joint_and_quality_roles_TRAIN_selection_002",
        "selection_split": "train", "test_accessed": False, "all120_original_slots_assessed": len(rows) == 120,
        "selection_plan_sha256": proto["selection_plan_sha256"], **selected,
        "protocol_sha256": digest(study / "protocol.json"), "execution_sha256": digest(out / "execution.json"),
        "candidate_results_sha256": digest(out / "candidate_results.jsonl")})
    write(out / "complete.json", {"complete": True, "all120_assessed": len(rows) == 120,
        "eligible": sum(r["eligible"] for r in rows), "status": dict(Counter(r["assessment_status"] for r in rows)),
        "ready_for_TEST": selected["ready_for_TEST"], "proposed_witness_joint_count": selected["proposed_witness_joint_count"],
        "selection_sha256": digest(out / "selection.json"), "TEST_queries": 0})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True); parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(); train(args.study, args.out, args.workers)
