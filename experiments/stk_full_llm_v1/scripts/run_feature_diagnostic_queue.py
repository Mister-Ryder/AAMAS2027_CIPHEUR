"""Supplemental frozen8-head v2 queue; wait for primary completion, run once.

Uses the existing stage dispatcher and unchanged kernel. TRAIN256 and TEST512
are serial stages on CPUs24..31. All failed records remain; no automatic retry.
This file must be uploaded before launch; local development does not run it.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OLD_TRAIN = Path("/root/autodl-tmp/cipheur_stk_p0_20261005_001/data")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def paths(root):
    return {"bank": root / "banks/frozen_feature_diagnostic8_v2.json",
            "ids": root / "selection/feature_diagnostic8_v2_ids.json",
            "protocol": root / "protocol.feature_diagnostic8_v2.frozen.json"}


def verify_freeze(root):
    files = paths(root)
    protocol, bank, ids = read(files["protocol"]), read(files["bank"]), read(files["ids"])
    if protocol.get("frozen") is not True or protocol.get("no_TEST_selection") is not True:
        raise ValueError("Supplemental diagnostic must be frozen without TEST selection")
    if sha(files["bank"]) != protocol["frozen_program_bank_sha256"]:
        raise ValueError("Supplemental bank changed after freeze")
    names = [item["id"] for item in bank["programs"]]
    if len(names) != 8 or len(set(names)) != 8 or set(names) != set(ids["program_ids"]) or set(names) != set(protocol["final_program_ids"]):
        raise ValueError("Expected all8 frozen diagnostic heads, including all3 grammar controls")
    if protocol.get("version") != "supplemental_feature_mechanism_diagnostic8_v2":
        raise ValueError("The unexecuted5 design is superseded; only v2 may run")
    if protocol["budgets_seconds"] != [2, 10] or protocol["seeds"] != [2]:
        raise ValueError("Supplemental diagnostic budgets/seeds changed")
    if sha(root / "protocol.frozen.json") != protocol["main_freeze_hashes"]["protocol.frozen.json"]:
        raise ValueError("Primary protocol changed; diagnostic cannot follow an altered study")
    for filename, expected in protocol["execution_script_hashes"].items():
        if sha(root / "scripts" / filename) != expected:
            raise ValueError("Frozen kernel/runtime changed: " + filename)
    return files, protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--train-data-root", type=Path, default=OLD_TRAIN)
    parser.add_argument("--test-data-root", type=Path)
    parser.add_argument("--cipheur-root", type=Path)
    parser.add_argument("--primary-receipt", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if os.name != "posix":
        raise SystemExit("This is the cloud POSIX queue; do not launch local Windows runs")
    files, protocol = verify_freeze(root)
    test_data = (args.test_data_root or root / "data").resolve()
    code_root = (args.cipheur_root or root / "code").resolve()
    primary_path = (args.primary_receipt or root / "formal_queue_receipt.json").resolve()
    receipt_path = root / "feature_diagnostic_queue_receipt.json"
    if receipt_path.exists():
        raise SystemExit("Supplemental queue already recorded; do not duplicate or silently retry")
    state = {"version": "feature_diagnostic_queue_v2", "started_utc": now(), "queue_pid": os.getpid(),
        "status": "waiting_for_primary", "primary_receipt": str(primary_path),
        "primary_required_status": "all_formal_stages_complete", "primary_poll_seconds": 60,
        "main_freeze_hashes": protocol["main_freeze_hashes"], "diagnostic_frozen_at_utc": protocol["frozen_at_utc"],
        "diagnostic_bank_sha256": sha(files["bank"]), "diagnostic_protocol_sha256": sha(files["protocol"]),
        "diagnostic_ids_sha256": sha(files["ids"]), "cpus": list(range(24, 32)), "solver_cores_total": 8,
        "main_queue_overlap_permitted": False, "automatic_retry": False, "stages": []}
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)

    def save():
        temporary = receipt_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(temporary, receipt_path)

    try:
        while True:
            primary = None
            if primary_path.is_file():
                try:
                    primary = read(primary_path)
                except json.JSONDecodeError:
                    # Primary writes its own receipt in place. Wait on a partial
                    # write rather than treating it as completion or failure.
                    pass
            if primary is not None:
                if primary.get("status") == "all_formal_stages_complete":
                    if primary["protocol_sha256"] != protocol["main_freeze_hashes"]["protocol.frozen.json"] or primary["bank_sha256"] != protocol["main_freeze_hashes"]["banks/frozen_final8.json"]:
                        raise ValueError("Primary completion receipt belongs to another freeze")
                    state.update(primary_complete_observed_utc=now(), primary_completed_receipt_sha256=sha(primary_path),
                                 primary_ended_utc=primary.get("ended_utc"), status="pre_registering_diagnostic_stages")
                    save()
                    break
                if primary.get("status") in ("registration_failed", "execution_incomplete", "failed", "cancelled"):
                    state.update(status="primary_incomplete_no_diagnostic_run", primary_terminal_status=primary["status"], ended_utc=now())
                    save()
                    raise SystemExit(2)
            time.sleep(60)
        # Recheck immutable input freeze after the potentially long wait.
        verify_freeze(root)
        runner = root / "scripts/stage_schedule_runner.py"
        for stage, folder_name, data, expected in (("final_train", "feature_diagnostic_train", args.train_data_root.resolve(), 256),
                                                  ("test", "feature_diagnostic_test", test_data, 512)):
            folder = root / folder_name
            folder.mkdir(exist_ok=True)
            common = [sys.executable, str(runner), "--stage", stage, "--manifest", str(folder / "registration/manifest.json"),
                      "--data-root", str(data), "--cipheur-root", str(code_root)]
            register = common + ["--register", "--program-bank", str(files["bank"]), "--program-ids-json", str(files["ids"]),
                "--protocol", str(files["protocol"]), "--budgets", "2", "10", "--seeds", "2",
                "--cpus", *[str(cpu) for cpu in range(24, 32)], "--shuffle-seed", "20261009" if stage == "test" else "20261008"]
            if stage == "final_train":
                register += ["--graph-root", str(data / "extensions/heterogeneous_ground_v1/graphs")]
            entry = {"stage": stage, "scope": "supplemental_feature_diagnostic", "path": str(folder),
                "expected_jobs": expected, "registration_argv": register,
                "execution_argv": common + ["--execute", "--output-root", str(folder / "results")]}
            state["stages"].append(entry)
            save()
            with (folder / "registration.stdout.txt").open("w") as out, (folder / "registration.stderr.txt").open("w") as err:
                entry["registration_exitcode"] = subprocess.run(register, stdout=out, stderr=err).returncode
            save()
            if entry["registration_exitcode"]:
                state.update(status="diagnostic_registration_failed", ended_utc=now())
                save()
                raise SystemExit(entry["registration_exitcode"])
            manifest = read(folder / "registration/manifest.json")
            if manifest["job_count"] != expected or manifest["workers"] != 8 or manifest["seeds"] != [2]:
                raise ValueError("Registered supplemental grid disagrees with frozen256/512 design")
            entry["registration_manifest_sha256"] = sha(folder / "registration/manifest.json")
            save()
        state["status"] = "executing_serial_diagnostic_stages"
        save()
        for entry in state["stages"]:
            folder = Path(entry["path"])
            entry["started_utc"] = now()
            save()
            with (folder / "execution.stdout.txt").open("w") as out, (folder / "execution.stderr.txt").open("w") as err:
                entry["execution_exitcode"] = subprocess.run(entry["execution_argv"], stdout=out, stderr=err).returncode
            entry["ended_utc"] = now()
            save()
            if entry["execution_exitcode"]:
                state.update(status="diagnostic_execution_incomplete", ended_utc=now())
                save()
                raise SystemExit(entry["execution_exitcode"])
            compact = [sys.executable, str(root / "scripts/compact_results.py"), "--stage-root", str(folder / "results"),
                       "--output", str(folder / "metrics.json"), "--include-curves"]
            entry["projection_argv"] = compact
            with (folder / "projection.stdout.txt").open("w") as out, (folder / "projection.stderr.txt").open("w") as err:
                entry["projection_exitcode"] = subprocess.run(compact, stdout=out, stderr=err).returncode
            save()
            if entry["projection_exitcode"]:
                state.update(status="diagnostic_projection_failed", ended_utc=now())
                save()
                raise SystemExit(entry["projection_exitcode"])
            metrics = read(folder / "metrics.json")
            entry.update(metrics_sha256=sha(folder / "metrics.json"), result_records=metrics["result_count"],
                         all_job_count=metrics["all_job_count"], failed_jobs=len(metrics["failed_jobs"]))
            save()
        state.update(status="all_feature_diagnostic_stages_complete", ended_utc=now())
        save()
        print(json.dumps(state))
    except Exception as error:
        state.update(status="diagnostic_queue_error", error=repr(error), ended_utc=now())
        save()
        raise


if __name__ == "__main__":
    main()
