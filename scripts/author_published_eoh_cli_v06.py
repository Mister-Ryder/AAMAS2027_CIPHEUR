"""One genuine native-CLI EoH author request; requires prior root release.

The driver never evaluates candidates or opens certificates. Root manually
transfers the immutable request/raw-response capsule for Linux TRAIN fitness,
then imports its bound, quality-only feedback before preparing another call.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.published_eoh_v06 import load_study, make_request, read
from cipheur.synthesis_study_v06 import digest, write
from scripts.author_matched_cli_v06 import CLI, safe_configuration

INSTRUCTION = {
    "i1": "Describe a new heuristic thought in one sentence and implement it as the typed program; the shared warm seed supplies the starting context.",
    "e1": "Explore a heuristic with a form as different as possible from the selected parent thoughts/programs.",
    "e2": "Identify the parents' common backbone, then explore a different heuristic motivated by that backbone and describe its thought.",
    "m1": "Modify the selected parent thought/program to seek better complete-schedule performance.",
    "m2": "Identify and change numerical parameters of the parent score/feature expressions while retaining the algorithmic structure.",
    "m3": "Analyze the parent's redundant components and simplify its typed feature/rule implementation for efficiency and generalization.",
}


def execute(study, request, root_release_sha256):
    study, request = Path(study), Path(request)
    load_study(study, root_release_sha256)
    req = read(request)
    if req["slot"] is None:
        raise ValueError("A warm-seed evaluation is not an LLM author request")
    with tempfile.TemporaryDirectory() as temp:
        expected = make_request(study, req["run"], req["slot"], Path(temp) / "request.json", root_release_sha256)
    if expected != req:
        raise ValueError("Published request differs from its frozen operator/population recipe")
    transport = read(study / "transport_binding.json")
    configured = transport["requested_configuration"]
    if safe_configuration() != configured or digest(CLI) != transport["cli_executable_sha256"]:
        raise ValueError("Requested native CLI/settings differ from published freeze")
    out = study / "calls" / req["id"]
    work = ROOT / ".research/v06_published_eoh_cli_workspaces" / study.name / req["id"]
    if out.exists() or work.exists():
        raise ValueError("Never retry or replace a published author slot")
    out.mkdir(parents=True); work.mkdir(parents=True)
    shutil.copyfile(request, out / "request.json")
    write(work / "packet.json", req["packet"])
    prompt = ("This is a registered EoH-DSL discovery request in a fresh isolated session. "
        "Read only the packet supplied below or packet.json. Inspect no other directory/session, "
        "run no evaluation, consult no internet and write no files. The controller saves your "
        "exact final response. Return exactly one FeatureRuleProgram JSON object, not a list, "
        "without Markdown fences. The unchanged typed grammar allows six added features, "
        "48 nodes and depth8 per feature expression, with the unchanged scalar-rule grammar. "
        "Missing, malformed and duplicate attempts are retained without another request.\n\n"
        + INSTRUCTION[req["operator"]] + "\n\nFROZEN PACKET\n"
        + json.dumps(req["packet"], ensure_ascii=False))
    (out / "input.txt").write_bytes(prompt.encode("utf-8"))
    last, events, stderr = (out / n for n in ("last_message.txt", "events.jsonl", "stderr.txt"))
    command = [str(CLI), "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--json",
        "--cd", str(work), "--output-last-message", str(last), "-"]
    started = time.perf_counter(); timed_out = False; exit_code = None; spawn_error = None
    with events.open("xb") as stdout, stderr.open("xb") as err:
        try:
            child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=err,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                child.communicate(prompt.encode("utf-8"), timeout=1800)
            except subprocess.TimeoutExpired:
                child.kill(); child.communicate(); timed_out = True
            exit_code = child.returncode
        except OSError as error:
            spawn_error = str(error)
    if not last.exists():
        last.write_bytes(b"")
    shutil.copyfile(last, out / "response.json")
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
    receipt = {"id": req["id"], "run": req["run"], "slot": req["slot"], "operator": req["operator"],
        "request_sha256": digest(request), "response_sha256": digest(out / "response.json"),
        "wrapper_sha256": digest(out / "input.txt"), "raw_event_sha256": digest(events),
        "raw_stderr_sha256": digest(stderr), "cli_executable_sha256": digest(CLI),
        "requested_configuration": configured, "observed_model": models or None, "usage_events": usage or None,
        "root_release_sha256": root_release_sha256, "wall_seconds": time.perf_counter() - started,
        "exit_code": exit_code, "timed_out": timed_out, "spawn_error": spawn_error,
        "no_retry": True, "no_candidate_assessment": True, "TEST_accessed": False}
    write(out / "receipt.json", receipt)
    if safe_configuration() != configured:
        raise ValueError("Requested settings changed during published call; retained receipt, no retry")
    return {"original_attempt": req["id"], "out": str(out), "exit_code": exit_code, "timed_out": timed_out}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("study", "request", "root-release-sha256"):
        p.add_argument("--" + n, required=True)
    print(json.dumps(execute(**vars(p.parse_args())), ensure_ascii=False))


if __name__ == "__main__":
    main()
