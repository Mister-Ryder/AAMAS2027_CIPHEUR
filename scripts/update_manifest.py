"""Normalize maintained text and refresh the current-source manifest.

Frozen runs, baselines, original template assets and their receipts are never
rewritten. This manifest is deliberately not a frozen experiment receipt.
"""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("cipheur", "configs", "docs", "examples", "paper", "scripts", "tests", ".github", "autoresearch")
EXCLUDED = {"aamas.cls", "ACM-Reference-Format.bst"}
TEXT = {".py", ".json", ".md", ".tex", ".bib", ".toml", ".yml", ".ps1", ".tsv", ".drawio"}


def main():
    paths = [ROOT / n for n in (".gitattributes", ".gitignore", "pyproject.toml", "README.md", "run_smoke.ps1")]
    for group in GROUPS:
        paths.extend(p for p in (ROOT / group).rglob("*") if p.is_file() and p.suffix in TEXT
                     and p.name not in EXCLUDED and "__pycache__" not in p.parts)
    manifest = {}
    for path in sorted(paths):
        raw = path.read_bytes()
        normalized = raw.replace(b"\r\n", b"\n")
        if normalized != raw:
            path.write_bytes(normalized)
        manifest[path.relative_to(ROOT).as_posix()] = sha256(normalized).hexdigest()
    target = ROOT / "manifest" / "CURRENT_SOURCE_SHA256.json"
    target.write_bytes((json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"Recorded {len(manifest)} maintained files; immutable experiment bytes unchanged")


if __name__ == "__main__":
    main()
