"""Frozen enumerated controls under the original V06 TRAIN assessor.

The four repeats measure host/budget variation of eight fixed ASTs; they are
not independent authoring draws. A quality-only baseline is recorded even if
its representation fails the joint synthesis gate. That baseline is never
described as an eligible proposed-program winner.
"""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
import json
from pathlib import Path
import platform

from .graph_features import FeatureRuleProgram
from .synthesis_extension_v06 import load_extended_bank
from .synthesis_study_v06 import ROOT, assess_candidate, canonical, digest, selection_key, write


def prepare(parent, supplement, controls, out):
    """Register the assessment without reading experimental responses."""
    parent, supplement, controls, out = map(Path, (parent, supplement, controls, out))
    if out.exists():
        raise ValueError("Preserve the first control-assessment registration")
    protocol = json.loads((parent / "protocol.json").read_bytes())
    bank = json.loads((controls / "control_banks.json").read_bytes())
    receipt = json.loads((controls / "freeze_receipt.json").read_bytes())
    if digest(controls / "control_banks.json") != receipt["control_banks_sha256"]:
        raise ValueError("Frozen control bank changed")
    if digest(Path(__file__).parent / "synthesis_study_v06.py") != protocol["source_sha256"]["assessment"]:
        raise ValueError("Original assessor changed")
    entries = []
    for block in range(4):
        for group, programs in bank["banks"].items():
            if len(programs) != 8:
                raise ValueError("Retain all eight original control slots")
            for slot, raw in enumerate(programs):
                program = FeatureRuleProgram.from_dict(raw).to_dict()
                ast_hash = canonical({k: program[k] for k in ("features", "rule")})
                if ast_hash != receipt["bank_deployment_AST_sha256"][group][slot]:
                    raise ValueError("Control deployment AST binding changed")
                entries.append({"id": f"control_{block}_{group}:{slot}", "block": block,
                    "arm": group, "slot": slot, "program": program,
                    "program_sha256": canonical(program), "deployment_AST_sha256": ast_hash,
                    "status": "static_valid"})
    out.mkdir(parents=True)
    write(out / "protocol.json", {"version": "v06_controls_TRAIN_assessment_001",
        "registered_before_any_raw_LLM_candidate_assessment": True,
        "parent_protocol_sha256": digest(parent / "protocol.json"),
        "supplement_protocol_sha256": digest(supplement / "protocol.json"),
        "control_bank_sha256": digest(controls / "control_banks.json"),
        "control_freeze_sha256": digest(controls / "freeze_receipt.json"),
        "source_sha256": {name: digest(Path(__file__).parent / name) for name in
            ("control_assessment_v06.py", "synthesis_extension_v06.py", "synthesis_study_v06.py",
             "repair_v06.py", "graph_features.py", "compiled.py")},
        "entries": entries, "entries_sha256": canonical(entries),
        "original_slots": 64, "unique_original_ASTs": 16, "repeated_blocks": 4,
        "independent_authoring_draws": False,
        "kernel_config": protocol["kernel_config"], "interface_limits": protocol["interface_limits"],
        "joint_selector": "Unchanged full demanded-interface acyclicity gate, then max strict fit, max exact family quality, min exact family work, original slot",
        "quality_only_baseline_selector": "Among all completed feasible TRAIN assessments (including interface-gate failures): max exact family quality, min exact family work, original slot. No gate failure is relabeled as eligible.",
        "performance_deployment": "For each bank use the quality-only winner of repeat block0; the four repetitions do not multiply the performance sample size. Keep every other outcome in the mechanism report.",
        "empty_bank": "Keep null; no extra AST, repair, oracle or fallback",
        "selection_split": "train", "test_accessed": False,
        "authoring_barrier": "All15 original/supplemental requests must be frozen before execution"})
    write(out / "freeze_receipt.json", {"before_assessment": True,
        "protocol_sha256": digest(out / "protocol.json")})


def train(parent, supplement, controls, registration, out, workers=8):
    if platform.system() != "Linux":
        raise ValueError("Control research assessment is server-only")
    parent, supplement, controls, registration, out = map(Path,
        (parent, supplement, controls, registration, out))
    if out.exists():
        raise ValueError("Never overwrite control outcomes")
    proto = json.loads((registration / "protocol.json").read_bytes())
    freeze = json.loads((registration / "freeze_receipt.json").read_bytes())
    if digest(registration / "protocol.json") != freeze["protocol_sha256"]:
        raise ValueError("Control registration changed")
    for name, expected in proto["source_sha256"].items():
        if digest(Path(__file__).parent / name) != expected:
            raise ValueError("Frozen assessment runtime changed: " + name)
    if (digest(parent / "protocol.json") != proto["parent_protocol_sha256"]
        or digest(supplement / "protocol.json") != proto["supplement_protocol_sha256"]
        or digest(controls / "control_banks.json") != proto["control_bank_sha256"]
        or digest(controls / "freeze_receipt.json") != proto["control_freeze_sha256"]
        or canonical(proto["entries"]) != proto["entries_sha256"]):
        raise ValueError("Control assessment input binding changed")
    original, _, transport, matched = load_extended_bank(parent, supplement)
    evidence = json.loads((parent / "training_evidence.json").read_bytes())
    if len(evidence["records"]) != 120 or any(r["split"] != "train" for r in evidence["records"]):
        raise ValueError("Changed TRAIN frame")
    out.mkdir(parents=True)
    write(out / "execution.json", {"registration_sha256": digest(registration / "protocol.json"),
        "all15_authoring_sessions_frozen_before_assessment": True, "workers": workers,
        "source_sha256": proto["source_sha256"], "transport_cells": transport,
        "matched_transport_complete_blocks": matched, "test_accessed": False})
    rows = []
    with (out / "candidate_results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(assess_candidate, (entry, evidence, original)): entry
                       for entry in proto["entries"]}
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception as error:
                    row = {**futures[future], "eligible": False, "kernel_rows": [],
                        "assessment_status": "assessment_worker_error",
                        "error_type": type(error).__name__, "error": str(error)}
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                print(json.dumps({"assessed_control": row["id"], "eligible": row["eligible"],
                    "status": row["assessment_status"]}), flush=True)
    selected = []
    for block in range(4):
        for group in ("enumerated_structural", "fixed_base9"):
            cell = [r for r in rows if r["block"] == block and r["arm"] == group]
            joint = [r for r in cell if r["eligible"]]
            quality = [r for r in cell if r.get("kernel_summary") and len(r["kernel_rows"]) == 120
                and all(x["result"]["completed"] and x["result"]["feasible"] for x in r["kernel_rows"])]
            qkey = lambda r: (-Fraction(r["kernel_summary"]["macro_quality_exact"]),
                Fraction(r["kernel_summary"]["macro_work_exact"]), r["slot"])
            winner = min(joint, key=selection_key) if joint else None
            baseline = min(quality, key=qkey) if quality else None
            fields = ("id", "block", "arm", "slot", "program", "program_sha256", "eligible")
            selected.append({"block": block, "bank": group,
                "joint_eligible_winner": {k: winner[k] for k in fields} if winner else None,
                "quality_only_baseline": {k: baseline[k] for k in fields} if baseline else None,
                "joint_eligible_slots": len(joint), "quality_completed_slots": len(quality),
                "used_for_performance": block == 0})
    write(out / "selection.json", {"version": "v06_fixed_controls_TRAIN_selection_001",
        "selection_split": "train", "test_accessed": False, "all64_original_slots_assessed": len(rows) == 64,
        "unique_ASTs": 16, "independent_authoring_draws": False, "selections": selected,
        "registration_sha256": digest(registration / "protocol.json"),
        "candidate_results_sha256": digest(out / "candidate_results.jsonl"), "no_fallback": True})
    write(out / "complete.json", {"complete": True, "returned_slots": len(rows),
        "eligible": sum(r["eligible"] for r in rows),
        "assessment_status": dict(Counter(r["assessment_status"] for r in rows)),
        "selection_sha256": digest(out / "selection.json"), "TEST_queries": 0})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "train"))
    parser.add_argument("--parent", required=True); parser.add_argument("--supplement", required=True)
    parser.add_argument("--controls", required=True); parser.add_argument("--out", required=True)
    parser.add_argument("--registration"); parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.parent, args.supplement, args.controls, args.out)
    else:
        train(args.parent, args.supplement, args.controls, args.registration, args.out, args.workers)
