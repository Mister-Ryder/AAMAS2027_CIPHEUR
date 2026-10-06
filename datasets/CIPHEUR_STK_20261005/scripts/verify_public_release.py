"""Read-only integrity and dataset-denominator checks for the public bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["version"] == "cipheur_stk_public_release_v1", "Manifest version differs")
    actual = [path for path in ROOT.rglob("*") if path.is_file()
              and path != manifest_path and "__pycache__" not in path.parts]
    lookup = {row["path"]: row for row in manifest["entries"]}
    require(len(lookup) == manifest["files"] == len(actual), "Released file denominator differs")
    for path in actual:
        relative = path.relative_to(ROOT).as_posix()
        require(relative in lookup, "Unmanifested release file: " + relative)
        row = lookup[relative]
        require(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                "Byte/hash mismatch: " + relative)
    require(sum(path.stat().st_size for path in actual) == manifest["bytes"], "Release byte total differs")

    train = list((ROOT / "extensions/heterogeneous_ground_v1/graphs").rglob("*.npz"))
    heldout = list((ROOT / "perf_dataset_v1/graphs").rglob("*.npz"))
    validation = [path for path in heldout if path.parent.name.endswith("-r006")]
    test = [path for path in heldout
            if path.parent.name.endswith("-r008") or path.parent.name.endswith("-r009")]
    require((len(train), len(validation), len(test)) == (16, 16, 32),
            "Primary TRAIN/validation/TEST graph denominator differs")
    require(len(list((ROOT / "graphs").rglob("*.npz"))) == 16, "P0 graph count differs")
    require(len(list((ROOT / "extensions/joint_resource_v1/graphs").rglob("*.npz"))) == 16,
            "Joint-resource diagnostic graph count differs")
    require(len([path for path in (ROOT / "raw_contacts").iterdir() if path.is_dir()]) == 10,
            "Physical raw-contact library count differs")
    print(json.dumps({"status": "verified", "files": len(actual),
                      "primary_graphs": 64, "train": 16, "validation": 16,
                      "test": 32, "diagnostic_graphs": 32}, ensure_ascii=False))


if __name__ == "__main__":
    main()
