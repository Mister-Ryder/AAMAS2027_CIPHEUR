"""Fresh, immutable native-CLI authoring for the registered R2 warm repair.

The original R1 transport and every original request remain unchanged. Five
whole matched blocks are requested exactly once; cohort selection later uses
only transport success. No candidate evaluation or TEST access occurs here.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.author_matched_cli_v06 import CLI, safe_configuration, digest, write


def execute_cell(block, arm, study, configured):
    stem = f"block_{block}_{arm}"
    work = ROOT / ".research/v06_refinement_cli_workspaces" / study.name / stem
    if work.exists():
        raise ValueError("Never retry or replace an R2 authoring request: " + stem)
    work.mkdir(parents=True)
    packet = study / "packets" / (stem + ".json")
    prompt = study / "packets" / (stem + ".prompt.md")
    receipts = study / "receipts"
    shutil.copyfile(packet, work / "packet.json")
    wrapper = ("Registered R2 transport: this is a fresh isolated authoring session for a warm-start "
        "TRAIN repair study. The frozen packet is fully provided below and also at packet.json. "
        "Read no other files, inspect no previous outputs, run no evaluation, consult no internet, "
        "and access no other directory or session. Return the exact requested JSON as your final "
        "assistant message without Markdown fences or prose. The controller saves it; do not "
        "write output files. All missing, invalid and duplicate positions remain failures.\n\n"
        "FROZEN PROMPT\n" + prompt.read_text(encoding="utf-8") + "\nFROZEN PACKET\n"
        + packet.read_text(encoding="utf-8"))
    input_file = receipts / (stem + ".input.txt")
    input_file.write_bytes(wrapper.encode())
    last = receipts / (stem + ".last_message.txt")
    events = receipts / (stem + ".events.jsonl")
    stderr = receipts / (stem + ".stderr.txt")
    command = [str(CLI), "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
        "--json", "--cd", str(work), "--output-last-message", str(last), "-"]
    if safe_configuration() != configured:
        raise ValueError("Requested model/settings changed before R2 authoring")
    started = time.time()
    print(json.dumps({"started": stem, "utc": datetime.now(timezone.utc).isoformat()}), flush=True)
    with events.open("xb") as out, stderr.open("xb") as err:
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            child.communicate(wrapper.encode(), timeout=1800); timed_out = False
        except subprocess.TimeoutExpired:
            child.kill(); child.communicate(); timed_out = True
    if not last.exists():
        last.write_bytes(b"")
    response = study / "responses" / (stem + ".json")
    if response.exists():
        raise ValueError("Never overwrite an R2 raw response")
    shutil.copyfile(last, response)
    usage, models = [], []
    for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("usage") is not None:
            usage.append({"event_type": event.get("type"), "usage": event["usage"]})
        if event.get("model") is not None:
            models.append(event["model"])
    receipt = {"cell": stem, "block": block, "arm": arm, "exit_code": child.returncode,
        "timed_out": timed_out, "wall_seconds": time.time() - started,
        "requested_configuration": configured, "observed_model": models or None,
        "usage_events": usage or None, "packet_sha256": digest(packet),
        "frozen_prompt_sha256": digest(prompt), "wrapper_prompt_sha256": digest(input_file),
        "response_sha256": digest(response), "cli_executable_sha256": digest(CLI),
        "raw_event_sha256": digest(events), "raw_stderr_sha256": digest(stderr),
        "command_flags": ["exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
            "--json", "--cd", "ISOLATED_R2_PACKET_DIRECTORY", "--output-last-message", "CONTROLLER_RECEIPT", "-"],
        "no_retry": True, "no_candidate_assessment": True, "study_kind": "warm_start_targeted_TRAIN_refinement"}
    write(receipts / (stem + ".receipt.json"), receipt)
    print(json.dumps({"completed": stem, "exit_code": child.returncode,
        "wall_seconds": receipt["wall_seconds"], "response_bytes": response.stat().st_size}), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True); parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.workers != 2:
        raise ValueError("Registered transport has exactly two concurrent requests")
    study = ROOT / args.study
    proto = json.loads((study / "protocol.json").read_bytes())
    freeze = json.loads((study / "freeze_receipt.json").read_bytes())
    if (proto["version"] != "matched_refinement_round_v06_002" or proto["blocks"] != 5
        or proto["slots_per_block_arm"] != 8 or proto["arms"] != ["witness", "relations", "objective"]
        or digest(study / "protocol.json") != freeze["protocol_sha256"]
        or not freeze["before_round2_authoring"]):
        raise ValueError("Changed R2 scientific/transport freeze")
    if digest(__file__) != proto["source_sha256"]["authoring_transport"]:
        raise ValueError("Frozen R2 transport source changed")
    for name, expected in proto["packet_sha256"].items():
        if digest(study / name) != expected:
            raise ValueError("Frozen R2 packet changed: " + name)
    runtime = json.loads((study / "transport_runtime_binding.json").read_bytes())
    configured = safe_configuration()
    if (configured != runtime["requested_configuration"]
        or digest(__file__) != runtime["authoring_transport_sha256"]
        or digest(CLI) != runtime["cli_executable_sha256"]
        or digest(ROOT / "scripts/author_matched_cli_v06.py") != runtime["transport_helper_sha256"]
        or digest(study / "preparation_receipt.json") != runtime["preparation_receipt_sha256"]):
        raise ValueError("R2 requested model/settings differ from freeze")
    if (study / "authoring_completion.json").exists():
        raise ValueError("R2 all-request freeze already exists")
    for name in ("receipts", "responses"):
        (study / name).mkdir(exist_ok=True)
        if list((study / name).iterdir()):
            raise ValueError("Refuse to replace earlier R2 transport observations")
    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execute_cell, block, arm, study, configured)
            for block in range(5) for arm in proto["arms"]]
        for future in as_completed(futures):
            rows.append(future.result())
    if safe_configuration() != configured:
        raise ValueError("Requested settings changed during R2")
    write(study / "authoring_completion.json", {"version": "R2_matched_cli_authoring_completion_v06",
        "protocol_sha256": digest(study / "protocol.json"),
        "transport_runtime_binding_sha256": digest(study / "transport_runtime_binding.json"),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "all15_R2_requests_frozen_before_assessment": True, "same_requested_model_and_settings_all_cells": True,
        "response_sha256": {r["cell"] + ".json": r["response_sha256"] for r in rows},
        "receipt_paths": {r["cell"]: "receipts/" + r["cell"] + ".receipt.json" for r in rows},
        "failed_transport_cells": [r["cell"] for r in rows if r["exit_code"] or r["timed_out"]],
        "no_assessment_or_retry": True, "no_TEST_access": True})
    print(json.dumps({"all15_R2_requests_frozen": True}), flush=True)


if __name__ == "__main__":
    main()
