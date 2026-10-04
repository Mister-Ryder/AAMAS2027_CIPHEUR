"""Snapshot one immutable published-EoH request/call for the trusted server transfer."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.published_eoh_v06 import digest, load_study, read, write


def package(study, request, out, root_release_sha256):
    study, request, out = Path(study).resolve(), Path(request).resolve(), Path(out).resolve()
    proto = load_study(study, root_release_sha256)
    value = read(request)
    receipt_path = out.with_suffix(".receipt.json")
    if out.exists() or receipt_path.exists():
        raise ValueError("Never overwrite a transaction snapshot or transfer receipt")
    if (value["protocol_sha256"] != digest(study / "protocol.json")
        or value["root_release_sha256"] != root_release_sha256
        or value["training_states_sha256"] != proto["training_states_sha256"]):
        raise ValueError("Transaction source/input/release binding changed")
    files = [study / "root_authoring_release.json", request]
    if value["slot"] is not None:
        calls = study / "calls" / value["id"]
        call = read(calls / "receipt.json")
        if (call["request_sha256"] != digest(request)
            or digest(calls / "request.json") != digest(request)
            or call["root_release_sha256"] != root_release_sha256
            or call["response_sha256"] != digest(calls / "response.json")
            or call["wrapper_sha256"] != digest(calls / "input.txt")
            or call["raw_event_sha256"] != digest(calls / "events.jsonl")
            or call["raw_stderr_sha256"] != digest(calls / "stderr.txt")
            or call["no_retry"] is not True or call["no_candidate_assessment"] is not True
            or call["TEST_accessed"] is not False):
            raise ValueError("Original author transaction changed before transfer")
        files.extend(sorted(p for p in calls.iterdir() if p.is_file()))
    file_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in files}
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "x", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            z.write(path, str(path.relative_to(ROOT)).replace("\\", "/"))
    receipt = {"version": "v06_published_EoH_immutable_transaction_transfer_001",
        "id": value["id"], "run": value["run"], "slot": value["slot"],
        "capsule_sha256": digest(out), "files_sha256": file_hashes,
        "protocol_sha256": digest(study / "protocol.json"),
        "root_release_sha256": root_release_sha256,
        "source_sha256": proto["source_sha256"], "packaging_source_sha256": digest(__file__),
        "candidate_content_not_parsed_for_transfer": True, "TEST_accessed": False}
    write(receipt_path, receipt)
    return {"id": value["id"], "capsule": str(out), "capsule_sha256": digest(out),
            "receipt_sha256": digest(receipt_path), "files": len(file_hashes)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("study", "request", "out", "root-release-sha256"):
        parser.add_argument("--" + name, required=True)
    print(json.dumps(package(**vars(parser.parse_args())), ensure_ascii=False))
