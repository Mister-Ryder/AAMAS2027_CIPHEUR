"""Restore ignored byte-identical V06 caches from public, pinned raw archives.

Existing identical files are verified; changed files are never overwritten.
No evaluation, model call, oracle or candidate selection is performed.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "R1": ("synthesis_train_server_v06_001", "c6b3b754aa0af36c769a4865e5f935085136f025d88665f079835dfc445f89d9",
        "synthesis_train_server_v06_001", "experiments/discovery/v06_synthesis_server_001"),
    "R2": ("refinement_train_server_v06_002", "9ad65026b830a44365fab90655ae3620fcddb6c263e063bde334ae6301c5a185",
        "refinement_train_server_v06_002", "experiments/discovery/v06_refinement_server_002"),
    "catalogue": ("catalogue_cost_server_v06_001", "dab90de26a486d11174ba10f06723c8c02ae277aa2907d643fe36909107ecc05",
        "aamas2027_v06_catalogue_cost_001", "experiments/discovery/v06_catalogue_cost_server_001/remote"),
}


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        while data := stream.read(1024*1024):
            h.update(data)
    return h.hexdigest()


def restore(name):
    stem, expected, prefix, relative = CASES[name]
    archive = ROOT / "experiments/runs/v06" / (stem + ".tar.gz")
    if digest(archive) != expected:
        raise ValueError("Original server archive changed: " + name)
    destination = (ROOT / relative).resolve()
    if not destination.is_relative_to(ROOT.resolve()):
        raise ValueError("Cache destination must remain within the project")
    members, seen = [], set()
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                or not path.parts or path.parts[0] != prefix
                or not (member.isfile() or member.isdir())):
                raise ValueError("Unsafe archive member: " + member.name)
            if member.isdir():
                continue
            key = "/".join(path.parts[1:])
            if not key or key.casefold() in seen:
                raise ValueError("Duplicate/empty case-folded archive path")
            seen.add(key.casefold()); target = (destination / key).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive destination escaped the cache")
            stream = source.extractfile(member); content = stream.read()
            value = sha256(content).hexdigest()
            if target.exists() and (not target.is_file() or digest(target) != value):
                raise ValueError("Changed existing cache is preserved: " + str(target))
            members.append((key, content, value))
    written = 0
    for key, content, value in members:
        target = destination / key
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(content)
            written += 1
        if digest(target) != value:
            raise ValueError("Restored bytes differ: " + key)
    return {"case": name, "archive_sha256": expected, "cache": relative,
        "file_count": len(members), "new_files": written,
        "byte_identical": True, "evaluation_or_selection": False}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases",nargs="+",choices=list(CASES))
    print(json.dumps([restore(name) for name in parser.parse_args().cases]))
