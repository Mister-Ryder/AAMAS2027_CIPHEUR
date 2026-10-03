"""Check release bytes and completed assignments, not solver success.

Default verification uses the standard library and never extracts archives.
Release creation and optional actual-PDF checks additionally require pypdf.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest/RELEASE_V04_SHA256.json"
FIGURES = (
    "motivation.drawio", "method_overview.drawio", "problem_setting-wide.drawio",
    "component_cancellation.drawio", "repair_cycle.drawio", "train_mechanisms_v04",
    "quality_cost_combined_v04", "heap_execution_v04",
)
STUDIES = {
    "advanced_fresh_v04_001": (456, 20),
    "advanced_public_v04_001": (96, 21),
    "advanced_sparse_v04_002": (8,),
    "frozen_action_v04_001": (588,),
    "heap_fresh_v04_001": (456,),
    "heap_sparse_v04_001": (8,),
    "heap_sparse_v04_30s_001": (8,),
    "relevance_train_v04_001": (66,),
}


def digest_stream(stream):
    h = sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def digest(path):
    with path.open("rb") as stream:
        return digest_stream(stream)


def safe_name(name):
    p = PurePosixPath(name)
    assert name and not p.is_absolute() and ".." not in p.parts
    assert "\\" not in name and ":" not in name
    return p


def released_paths():
    raw = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT,
    )
    paths = sorted({x.decode("utf-8") for x in raw.split(b"\0") if x})
    return [n for n in paths if n != MANIFEST.relative_to(ROOT).as_posix()]


def archive_inventory(paths):
    records = {}
    for name in paths:
        p = ROOT / safe_name(name)
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                assert len(names) == len(set(names)), f"Duplicate ZIP member: {name}"
                for n in names:
                    safe_name(n)
                assert z.testzip() is None, f"ZIP CRC failed: {name}"
                records[name] = {"members": len(names), "type": "zip"}
        elif p.name.endswith(".tar.gz"):
            with tarfile.open(p, "r:gz") as t:
                entries = t.getmembers()
                names = [m.name for m in entries]
                assert len(names) == len(set(names)), f"Duplicate tar member: {name}"
                for m in entries:
                    safe_name(m.name)
                    assert m.isfile() or m.isdir(), f"Nonregular archive member: {name}"
                records[name] = {"members": len(entries), "type": "tar.gz"}
    return records


def completion_checks():
    records = {}
    for stem, expected in STUDIES.items():
        with tarfile.open(ROOT / "experiments/runs/v04" / (stem + ".tar.gz"), "r:gz") as t:
            receipt = json.load(t.extractfile(stem + "/complete.json"))
            if stem.startswith("advanced_"):
                assert receipt["execution_complete"] and receipt["selection_permitted"] is False
                assert len(receipt["phases"]) == len(expected)
                for i, (phase, count) in enumerate(zip(receipt["phases"], expected)):
                    assert phase["execution_complete"]
                    assert phase["processed_contexts"] == phase["requested_contexts"] == count
                    member = stem + ("/results.jsonl" if i == 0 else "/long_results.jsonl")
                    assert digest_stream(t.extractfile(member)) == phase["results_sha256"]
            elif stem.startswith("relevance_train_"):
                assert receipt["complete"] and receipt["training_contexts"] == expected[0]
                assert receipt["candidates"] == 93
            else:
                assert receipt.get("complete", receipt.get("execution_complete")) is True
                assert receipt["contexts"] == expected[0] and receipt["selection_permitted"] is False
                assert digest_stream(t.extractfile(stem + "/results.jsonl")) == receipt["results_sha256"]
            records[stem] = {"assigned_contexts_by_phase": list(expected), "receipt": receipt}
    return records


def check_paper_layout():
    from pypdf import PdfReader
    reader = PdfReader(ROOT / "paper/main.pdf")
    assert len(reader.pages) == 9, "Expected eight body pages and one reference page"
    texts = [p.extract_text() or "" for p in reader.pages]
    heading = r"^\s*References\s*$"
    assert not any(re.search(heading, text, re.M | re.I) for text in texts[:8])
    assert re.search(heading, texts[8], re.M | re.I)
    assert re.search(r"^\s*7\s+Conclusion\s*$", texts[7], re.M | re.I)
    assert not any(re.search(r"^\s*7\s+Conclusion\s*$", text, re.M | re.I) for text in texts[8:])
    printed = {int(n) for n in re.findall(r"^\[(\d+)\]", texts[8], re.M)}
    assert printed == set(range(1, 25)), "Expected 24 complete reference entries"
    body = "\n".join(texts[:8])
    assert re.findall(r"Figure\s+(\d+)\s*:", body) == [str(i) for i in range(1, 9)]
    assert sorted(re.findall(r"Table\s+(\d+)\s*:", body)) == ["1", "2"]
    assert all(tuple(float(x) for x in p.mediabox) == tuple(float(x) for x in reader.pages[0].mediabox)
               for p in reader.pages)
    return {"body_pages": 8, "reference_pages": 1, "total_pages": 9,
            "main_figures": 8, "main_tables": 2, "printed_reference_entries": 24,
            "layout_check": "pypdf text/page allocation plus root render-and-inspect of all nine pages"}


def verify(write=False, paper_layout=False):
    source = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    assert "\\documentclass[sigconf,anonymous,balance=false]{aamas}" in source
    bib = (ROOT / "paper/references_v03.bib").read_text(encoding="utf-8")
    assert not re.search(r"arxiv|eprint|preprint", bib, re.I)
    required = ["paper/main.pdf", "paper/aamas.cls", "paper/ACM-Reference-Format.bst",
                "examples/frozen_program_v04.json", "manifest/CURRENT_SOURCE_SHA256.json"]
    required += [f"paper/figures/{n}.{ext}" for n in FIGURES for ext in ("pdf", "png")]
    required += [f"paper/figures/{n}" for n in FIGURES[:5]]
    if write:
        assert paper_layout, "Release creation requires the actual PDF page check"
        paths = released_paths()
        assert set(required).issubset(paths)
        payload = {"release": "0.4.0", "date": "2026-10-03", "paper": check_paper_layout(),
                   "scope": "Byte identities and assignment completion; not a replacement for scientific audits",
                   "files": {n: digest(ROOT / safe_name(n)) for n in paths},
                   "archives": archive_inventory(paths), "studies": completion_checks()}
        MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert payload["release"] == "0.4.0" and set(required).issubset(payload["files"])
        for n, expected in payload["files"].items():
            assert re.fullmatch(r"[0-9a-f]{64}", expected)
            assert digest(ROOT / safe_name(n)) == expected, f"Changed release file: {n}"
        assert archive_inventory(payload["files"]) == payload["archives"]
        assert completion_checks() == payload["studies"]
        if paper_layout:
            assert check_paper_layout() == payload["paper"]
    print(f"Verified release 0.4.0: {len(payload['files'])} file hashes, "
          f"{len(payload['archives'])} archive inventories, {len(STUDIES)} completed assignment studies; "
          "solver failures retained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create the reviewed release manifest")
    parser.add_argument("--paper-layout", action="store_true", help="Verify the actual PDF using pypdf")
    args = parser.parse_args()
    verify(args.write, args.paper_layout)
