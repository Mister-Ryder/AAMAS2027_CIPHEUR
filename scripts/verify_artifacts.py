"""Verify immutable run receipts and snapshots without private source data."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashed(path):
    return sha256(path.read_bytes()).hexdigest()


def verify():
    checked = 0
    for run in sorted((ROOT / "experiments" / "runs").iterdir()):
        receipt_path = run / "result_receipt.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for name, expected in receipt.items():
                assert hashed(run / name) == expected, f"Changed artifact: {run.name}/{name}"
                checked += 1
        freeze_path = run / "freeze_receipt.json"
        if freeze_path.exists():
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            snapshot = run / "source_snapshot" / "cipheur"
            if snapshot.exists():
                for name, expected in freeze["source_sha256"].items():
                    assert hashed(snapshot / name) == expected, f"Changed snapshot: {run.name}/{name}"
                    checked += 1
            evidence = freeze.get("evidence_and_selection_sha256", {})
            for name, expected in evidence.items():
                assert hashed(run / name) == expected, f"Changed freeze input: {run.name}/{name}"
                checked += 1
    pilot = ROOT / "experiments" / "runs" / "pilot_v0.2.0"
    audited = ROOT / "experiments" / "runs" / "pilot_v0.2.0_audited"
    followup = ROOT / "experiments" / "runs" / "followup_v0.2.0"
    assert hashed(pilot / "frozen_programs.json") == hashed(audited / "frozen_programs.json")
    assert hashed(pilot / "frozen_programs.json") == hashed(followup / "frozen_programs.json")
    for run in (audited, followup):
        rows = json.loads((run / "test_metrics.json").read_text(encoding="utf-8"))
        assert all(r["feasible"] and r["reference_exact"] for r in rows)
    print(f"Verified {checked} artifact/snapshot hashes, frozen-program identity and recorded feasibility/exactness")


if __name__ == "__main__":
    verify()
