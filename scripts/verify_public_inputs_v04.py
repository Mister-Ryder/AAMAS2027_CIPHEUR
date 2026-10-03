"""Audit prespecified public graph INPUTS and saved native smoke fixtures only.

No generated-program public/fresh test outputs are read or evaluated.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
import io
from pathlib import Path, PurePosixPath
import re
import tarfile
import verify_v03_evidence as audit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments/runs/v04/public_data_v04_002.tar.gz"


def binary(raw):
    line, rest = raw.split(b"\n", 1)
    length = int(line)
    header, bits = rest[:length].decode("ascii"), rest[length:]
    declarations = re.findall(r"^p\s+(?:edge|col)\s+(\d+)\s+(\d+)\s*$", header, re.M)
    assert len(declarations) == 1
    n, m = map(int, declarations[0])
    edges, offset = set(), 0
    for high in range(n):
        count = high//8 + 1
        assert len(bits[offset:offset+count]) == count
        for low in range(high):
            if (bits[offset+low//8] >> (7-low%8)) & 1: edges.add((low,high))
        offset += count
    assert offset == len(bits) and len(edges) == m
    return n, edges


def cnf(raw):
    declarations, words, ended = [], [], False
    for line in raw.decode("ascii").splitlines():
        line = line.strip()
        if not line or line.startswith("c"): continue
        if line == "%": ended = True; continue
        if ended:
            assert line == "0"
            continue
        if line.startswith("p"):
            fields = line.split(); assert fields[:2] == ["p","cnf"] and len(fields) == 4
            declarations.append(tuple(map(int,fields[2:])))
        else: words.extend(map(int,line.split()))
    assert len(declarations) == 1
    variables, count = declarations[0]
    clauses, pending = [], []
    for word in words:
        if word == 0: clauses.append(pending); pending = []
        else:
            assert 1 <= abs(word) <= variables
            pending.append(word)
    assert not pending and len(clauses) == count
    occurrences = [(c,p,l) for c, clause in enumerate(clauses) for p,l in enumerate(clause)]
    # Pairwise definition is independent of the parser's literal-index joins.
    edges = {(i,j) for i,a in enumerate(occurrences) for j,b in enumerate(occurrences[i+1:],i+1) if a[0] == b[0] or a[2] == -b[2]}
    return len(occurrences), edges, variables, count, occurrences


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,default=DATA)
    parser.add_argument("--output",type=Path,default=ROOT/"experiments/analysis/v04/public_input_audit.json")
    parser.add_argument("--native-preflight",type=Path,default=ROOT/"experiments/analysis/v04/native_preflight_v04.json")
    parser.add_argument("--native-smoke",type=Path,help="Optional original auxiliary three-vertex smoke receipt; not bundled in the public input archive")
    args=parser.parse_args(argv)
    meta,hashes,raw_members={},{},{}
    wanted={"protocol.json","complete.json","data.json","source_receipts.json"}
    for name,handle,full in audit.stream(args.archive):
        if name in wanted:
            if name in meta:raise ValueError("Duplicate public input proof member: "+name)
            payload=handle.read();meta[name]=json.loads(payload);hashes[name]=sha256(payload).hexdigest()
        elif PurePosixPath(full).parent.name=="raw":
            if name in raw_members:raise ValueError("Duplicate public raw-source member: "+name)
            raw_members[name]=handle.read()
    if not wanted<=meta.keys():raise ValueError("Public input archive lacks required proof members: "+", ".join(sorted(wanted-meta.keys())))
    protocol,complete=meta["protocol.json"],meta["complete.json"]
    records,receipts=meta["data.json"]["public"],meta["source_receipts.json"]
    bysource = {r["id"]:r for r in receipts}
    config = protocol["config"]
    audit.require(len(records) == len({r["id"] for r in records}) == complete["retained_graphs"] == protocol["declared_graphs"] == 96, "public_96_complete_unique", "data", "population mismatch")
    audit.require(hashes["data.json"] == complete["data_sha256"], "public_data_sha256", "complete", "hash mismatch")
    audit.require(protocol["outcome_selection"] is False and config["programs_frozen_on_satellite_training_only"] is True and config["public_test_may_not_choose_programs_or_thresholds"] is True, "public_frozen_transfer_scope", "protocol", "selection access scope")
    expected = {}
    for name in config["dimacs"]:
        raw = raw_members[name+".clq.b"]
        n, source_edges = binary(raw)
        edges = {(u,v) for u in range(n) for v in range(u+1,n) if (u,v) not in source_edges}
        receipt = bysource[name]
        audit.require(sha256(raw).hexdigest() == receipt["sha256"] and receipt["original_vertices"] == n and receipt["original_edges"] == len(source_edges) and receipt["conflict_edges"] == len(edges), "public_dimacs_raw_receipt", name, "source counts/hash mismatch")
        expected[name] = n, edges
    for collection, limit in config["satlib"].items():
        raw = raw_members[collection+".tar.gz"]
        raw_hash = sha256(raw).hexdigest()
        members = {}
        with tarfile.open(fileobj=io.BytesIO(raw),mode="r|gz") as archive:
            for member in archive:
                p = PurePosixPath(member.name)
                audit.require(not p.is_absolute() and ".." not in p.parts and not member.issym() and not member.islnk(), "public_satlib_archive_safe", collection, member.name)
                if member.isfile() and member.name.endswith(".cnf"): members[member.name] = archive.extractfile(member).read()
        selected = sorted(members)[:limit]
        audit.require(len(selected) == limit, "public_satlib_fixed_lex_count", collection, "insufficient fixed members")
        for member in selected:
            name = collection+":"+Path(member).stem
            n, edges, variables, clauses, occurrences = cnf(members[member])
            receipt = bysource[name]
            audit.require(receipt["member"] == member and receipt["archive_sha256"] == raw_hash and receipt["sha256"] == sha256(members[member]).hexdigest(), "public_satlib_raw_receipt", name, "source hash/member mismatch")
            audit.require(receipt["variables"] == variables and receipt["clauses"] == receipt["unit_weight_upper"] == clauses and receipt["literal_occurrences"] == [list(v) for v in occurrences], "public_satlib_occurrence_reduction", name, "CNF metadata mismatch")
            expected[name] = n, edges
    for r in records:
        name, mode = r["cluster"], r["source"]["weight_mode"]
        n, edges = expected[name]
        g = audit.GraphView(r["graph"])
        converted = {tuple(sorted((str(a),str(b)))) for a,b in edges}
        audit.require(len(g.contacts) == n and g.edges == converted and set(g.contacts) == {str(i) for i in range(n)}, "public_exact_graph_conversion", r["id"], "vertices/conflicts differ from raw source")
        audit.require(g.raw["provenance"]["physical_scheduling_claim"] is False and mode in config["weight_modes"], "public_graph_semantic_scope", r["id"], "scope or mode mismatch")
        for i in range(n):
            value = 1 if mode == "unit" else 1+int(sha256(f"20261003:{name}:{i}".encode()).hexdigest(),16)%20
            audit.require(g.weights[str(i)] == value, "public_weight_extension_exact", r["id"]+":"+str(i), "weight mismatch")
        audit.require(sum(g.weights.values()) <= 2**31-1 and all(w.denominator == 1 for w in g.weights.values()), "native_weight_scaling_preflight", r["id"], "weights outside native integer scope")
    from verify_fresh_inputs_v04 import native
    native_report=native(args.native_preflight)
    smoke = json.loads(args.native_smoke.read_text(encoding="utf-8")) if args.native_smoke is not None else []
    smoke_summary = []
    for r in smoke:
        values = list(map(int,r["solution_text"].split()))
        indices = [i for i,flag in enumerate(values) if flag == 1] if r["output_format"] == "partition_flags" else [i-1 for i in values]
        audit.require(indices == [0,1] and r["selected"] == ["0","1"] and r["value"] == 30 and r["completed"] is True and r["feasible"] is True and r["exact_optimum_claimed"] is False, "native_smoke_format_original_objective", r["method"], "incorrect membership/objective")
        audit.require(r["input_sha256"] == "462b99a2b8bf0d3a958b524be65b67c65ddbf790e3124956b892b436b633734d", "native_smoke_same_metis_input", r["method"], "different input")
        smoke_summary.append({k:r[k] for k in ("method","output_format","executable_sha256","value","declared_seconds","hard_wall_seconds","seconds")})
    report = {"scope":"Public input construction and released native tiny-fixture preflight; original auxiliary three-vertex smoke only when explicitly supplied; no fresh/generated-program test results read", "graphs":len(records), "raw_sources":len(expected), "families":dict(Counter(r["family"] for r in records)), "data_sha256":complete["data_sha256"], "protocol_sha256":hashes["protocol.json"], "public_parser_sha256":audit.file_digest(ROOT/"cipheur/public_benchmarks.py"), "native_adapter_sha256":audit.file_digest(ROOT/"cipheur/advanced_baselines.py"), "native_smoke":smoke_summary, "checks":dict(audit.CHECKS), "issues":list(audit.ISSUES.values()), "limitations":["Raw payload hashes are compared with preserved receipts; only previously inspected official samples were independently downloaded, not all48 sources.","Released native preflight checks exact input/output mapping and objective recomputation, pinned source/build/binary and clean-worktree receipts; the auxiliary original smoke is independently checked only when explicitly supplied.","Hash weights are a declared extension, not original weighted public benchmarks.","Short fixed budgets and CHILS p4/c1/s0.1 are modified runtime parameters, not the papers' recommended/default operating regime."]}
    report["native_preflight"]=native_report
    report["native_smoke_scope"]="original auxiliary receipt independently audited" if args.native_smoke is not None else "auxiliary receipt not supplied; default independently audits the released 32-case/128-attempt native preflight"
    report["archive_sha256"]=audit.file_digest(args.archive)
    report["native_smoke_receipt_sha256"]=audit.file_digest(args.native_smoke) if args.native_smoke is not None else None
    output = args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output),"graphs":len(records),"raw_sources":len(expected),"checks":sum(audit.CHECKS.values()),"issues":report["issues"]}))
    return int(any(i["severity"] == "error" for i in report["issues"]))


if __name__ == "__main__": raise SystemExit(main())
