"""Launch the frozen supplemental waiting queue once; never the primary queue."""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

from run_feature_diagnostic_queue import verify_freeze

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--train-data-root", type=Path)
    parser.add_argument("--test-data-root", type=Path)
    parser.add_argument("--cipheur-root", type=Path)
    parser.add_argument("--primary-receipt", type=Path)
    args = parser.parse_args()
    if os.name != "posix":
        raise SystemExit("Upload then launch on the cloud POSIX host; no local Windows experiment")
    root = args.root.resolve()
    verify_freeze(root)
    start_path = root / "feature_diagnostic_queue_start.json"
    if start_path.exists() or (root / "feature_diagnostic_queue_receipt.json").exists():
        raise SystemExit("Existing supplemental queue record; do not duplicate or silently retry")
    argv = [sys.executable, str(root / "scripts/run_feature_diagnostic_queue.py"), "--root", str(root)]
    for name in ("train_data_root", "test_data_root", "cipheur_root", "primary_receipt"):
        value = getattr(args, name)
        if value is not None:
            argv += ["--" + name.replace("_", "-"), str(value.resolve())]
    with start_path.open("x", encoding="utf-8") as record:
        with (root / "feature_diagnostic_queue.stdout.txt").open("w") as out, (root / "feature_diagnostic_queue.stderr.txt").open("w") as err:
            process = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True, cwd=root)
        data = {"pid": process.pid, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "argv": argv, "scope": "supplemental mechanism diagnostic; primary results unchanged",
            "starts_optimization_only_after": "formal_queue_receipt.status=all_formal_stages_complete",
            "poll_seconds": 60, "stages": ["feature_diagnostic_train", "feature_diagnostic_test"],
            "expected_jobs": [256, 512], "diagnostic_version": "8_v2_5LLM_3grammar",
            "solver_cores_total": 8, "cpus": list(range(24, 32)),
            "automatic_retry": False, "main_queue_overlap_permitted": False}
        json.dump(data, record, indent=2)
    print(json.dumps(data))


if __name__ == "__main__":
    main()
