"""Independent input-only C3 interval sweep; no project imports or scheduling."""
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import csv
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
STEM="c3_interval_inputs_v06_001"


def sweep(contacts,gap,field):
    groups=defaultdict(list)
    for c in contacts:groups[c[field]].append(c)
    edges=set()
    for group in groups.values():
        active=[]
        for c in sorted(group,key=lambda r:(r["start"],r["id"])):
            active=[a for a in active if Fraction(a["end"])+Fraction(gap)>Fraction(c["start"])]
            for a in active:edges.add(tuple(sorted((a["id"],c["id"]))))
            active.append(c)
    return edges


def main():
    path=ROOT/"experiments/runs/v06"/(STEM+".tar.gz")
    receipt=json.loads((ROOT/"experiments/discovery"/STEM/"archive_receipt.json").read_bytes())
    assert sha256(path.read_bytes()).hexdigest()==receipt["archive_sha256"]
    with tarfile.open(path) as t:
        data_raw=t.extractfile(STEM+"/data.json").read()
        data=json.loads(data_raw)
        complete=json.load(t.extractfile(STEM+"/complete.json"))
        protocol=json.load(t.extractfile(STEM+"/protocol.json"))
    assert sha256(data_raw).hexdigest()==complete["data_sha256"]
    assert complete["optimization_calls"]==complete["oracle_calls"]==complete["candidate_reads"]==0
    raw_csv=Path("E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/data/C3.csv").read_bytes()
    assert sha256(raw_csv).hexdigest()==protocol["source_csv_sha256"]
    rows=list(csv.reader(io.StringIO(raw_csv.decode("gb18030"))))[1:]
    with tarfile.open(ROOT/protocol["source_archive"]) as t:
        old=json.load(t.extractfile("advanced_fresh_v04_001/data.json"))
    old_contexts={r["id"]+":"+side:r[side] for r in old["test"] if r["family"]=="c3" for side in ("left","right")}
    clean=lambda s:s.strip().strip("'").strip('"')
    checks=8
    pair_graphs=defaultdict(dict)
    for c in data["contexts"]:
        graph=c["graph"]
        d={k:v for k,v in graph.items() if k not in ("name","provenance")}
        assert sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()==c["graph_sha256"]
        for contact in graph["contacts"]:
            row=rows[int(contact["id"])]
            assert contact["station"]==clean(row[0]) and contact["satellite"]==clean(row[1])
            assert Fraction(contact["start"])==Fraction(clean(row[2]))
            assert Fraction(contact["end"])==Fraction(clean(row[3]))
            assert Fraction(contact["weight"])==Fraction(clean(row[3]))-Fraction(clean(row[2]))>0
            checks+=5
        if c["population"]=="C3_legacy_exploratory":
            assert graph==old_contexts[c["id"]]
            checks+=1
        else:
            assert c["population"]=="C3_interval_exploratory"
            gap=Fraction(1,2) if c["side"]=="left" else Fraction(6)
            independent=sweep(graph["contacts"],gap,"station")|sweep(graph["contacts"],0,"satellite")
            assert independent=={tuple(e) for e in graph["edges"]}
            checks+=len(independent)+2
            pair_graphs[c["pair_id"]][c["side"]]=graph
    allids=[];pairs=[]
    for identity,graphs in sorted(pair_graphs.items()):
        assert graphs["left"]["contacts"]==graphs["right"]["contacts"]
        left={tuple(e) for e in graphs["left"]["edges"]};right={tuple(e) for e in graphs["right"]["edges"]}
        assert left<=right
        allids.extend(c["id"] for c in graphs["left"]["contacts"])
        pairs.append({"id":identity,"n":len(graphs["left"]["contacts"]),"left_edges":len(left),
                      "right_edges":len(right),"added_edges":len(right-left)})
        checks+=3
    assert len(allids)==len(set(allids))==2880 and len(pairs)==12 and len(data["contexts"])==48
    report={"errors":0,"checks":checks,"audit_source_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),
        "archive_sha256":receipt["archive_sha256"],"data_sha256":complete["data_sha256"],
        "source_csv_sha256":protocol["source_csv_sha256"],"all_source_contact_fields_checked":True,
        "all_24_interval_graphs_independently_sweep_checked":True,"all_24_legacy_graphs_unchanged":True,
        "source_contacts":2880,"source_pairs":12,"pairs":pairs,"optimization_calls":0,"candidate_reads":0,
        "exposure_scope":"Previously exposed C3 source blocks, model-transformed exploratory population, not independent new natural TEST data",
        "audit_scope":"Independent implementation by execution agent; no project runtime/solver imported"}
    target=ROOT/"experiments/analysis/v06/c3_interval_inputs_check_v06_001.json"
    target.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
    print(json.dumps({"errors":0,"checks":checks,"pairs":pairs}))


if __name__=="__main__":main()
