"""Create the deterministic byte-hash manifest for this public data bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "RELEASE_MANIFEST.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == OUTPUT or "__pycache__" in path.parts:
            continue
        rows.append({"path": path.relative_to(ROOT).as_posix(),
                     "bytes": path.stat().st_size, "sha256": digest(path)})
    value = {
        "version": "cipheur_stk_public_release_v1",
        "dataset": "CIPHEUR_STK_20261005",
        "files": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "manifest_excludes_itself": True,
        "entries": rows,
    }
    OUTPUT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value[key] for key in ("files", "bytes")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
