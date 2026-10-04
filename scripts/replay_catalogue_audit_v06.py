"""Replay the original independent reviewer with only its output redirected.

The preserved reviewer bytes and their mathematical checks remain unchanged.
The original signed audit is never overwritten. No optimizer is run.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scripts/audit_catalogue_cost_v06_001_original.py"
EXPECTED="1176b283a70f6824f7e9e06c22a0f6b41453c884a5782b08c40482c06d3f7c6f"


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",default=".research/replayed_catalogue_cost_audit_v06.json")
    args=parser.parse_args(); output=(ROOT/args.out).resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists():
        raise ValueError("Use a new output inside the project; preserve prior audit bytes")
    data=SOURCE.read_bytes()
    if sha256(data).hexdigest()!=EXPECTED:
        raise ValueError("Original independent reviewer source changed")
    source=data.decode("utf-8")
    old="OUT = ROOT / 'experiments/analysis/v06/catalogue_cost_audit_v06_001.json'"
    if source.count(old)!=1:
        raise ValueError("Original reviewer output assignment changed")
    # Only this I/O destination changes; the original __file__ binds source SHA.
    source=source.replace(old,"OUT = Path("+repr(str(output))+")",1)
    exec(compile(source,str(SOURCE),"exec"),{"__file__":str(SOURCE),"__name__":"__main__"})
