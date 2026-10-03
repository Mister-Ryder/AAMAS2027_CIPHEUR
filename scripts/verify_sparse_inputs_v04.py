"""Independent SNAP raw edge-list to declared simple-graph input audit."""
import argparse
from collections import Counter
from hashlib import sha256
import gzip
import json
from pathlib import Path
import re
import verify_v03_evidence as audit

ROOT=Path(__file__).resolve().parents[1]


def run(path=None, output=None):
    path=Path(path) if path is not None else ROOT/"experiments/runs/v04/public_sparse_v04_001.tar.gz"
    data=receipts=config=complete=None;raw={};hashes={}
    for name,handle,_ in audit.stream(path):
        if name in {"data.json","source_receipts.json","config.json","protocol.json","protocol_before_fetch.json","complete.json"}:
            payload=handle.read();hashes[name]=sha256(payload).hexdigest()
            if name=="data.json":data=json.loads(payload)
            elif name=="source_receipts.json":receipts=json.loads(payload)
            elif name=="config.json":config=json.loads(payload)
            elif name=="complete.json":complete=json.loads(payload)
        elif name.endswith(".txt.gz"):raw[name]=handle.read()
    audit.require(len(data["public"])==8 and len(raw)==len(receipts)==4,"sparse_eight_inputs_four_sources","SNAP","count mismatch")
    audit.require(hashes["data.json"]==complete["data_sha256"],"sparse_saved_input_bytes","SNAP","archive/completion bytes differ")
    summaries=[]
    for receipt in receipts:
        name=receipt["name"];compressed=raw[name+".txt.gz"];text=gzip.decompress(compressed)
        audit.require(sha256(compressed).hexdigest()==receipt["compressed_sha256"] and sha256(text).hexdigest()==receipt["decompressed_sha256"],"sparse_compressed_decompressed_bytes",name,"raw hashes differ")
        vertices=set();ordered=set();simple=set();loops=set();rows=duplicates=0;comments=[];header=None
        for line in text.decode("ascii").splitlines():
            if line.startswith("#"):
                comments.append(line);match=re.search(r"Nodes:\s*(\d+)\s+Edges:\s*(\d+)",line)
                if match:header=tuple(map(int,match.groups()))
                continue
            if not line.strip():continue
            fields=line.split();audit.require(len(fields)==2,"sparse_two_column_original_edges",name,"malformed edge row")
            a,b=map(int,fields);vertices.update((a,b));rows+=1;duplicates+=(a,b) in ordered;ordered.add((a,b))
            if a==b:loops.add(a)
            else:simple.add(tuple(sorted((str(a),str(b)))))
        audit.require(sorted(vertices)==receipt["original_vertex_ids"] and sorted(loops)==receipt["self_loop_vertex_ids"] and len(vertices)==receipt["retained_vertices"] and len(simple)==receipt["retained_edges"] and rows==receipt["raw_edge_rows"] and len(ordered)==receipt["unique_ordered_arcs"] and duplicates==receipt["duplicate_ordered_rows"],"sparse_exact_projection_population",name,"vertex/edge/loop counts differ")
        audit.require(receipt["conversion"]=="undirected simple projection; retain all observed vertices; deduplicate unordered edges and discard self-loop arcs" and receipt["self_loop_policy"]=="drop_loop_arcs" and receipt["original_looped_MWIS_preservation_claimed"] is False and receipt["removed_vertex_count"]==receipt["invented_isolated_vertices"]==0,"sparse_declared_nonpreserving_loop_projection",name,"projection/loop scope differs")
        if header:audit.require(header==(receipt["header_declared_nodes"],receipt["header_declared_edges"]) and header[0]==len(vertices) and header[1]==rows,"sparse_raw_header_population",name,"header count differs")
        records=[r for r in data["public"] if r["source"]["name"]==name]
        audit.require(len(records)==2 and {r["source"]["weight_mode"] for r in records}=={"unit","hash_weighted"},"sparse_two_weight_modes",name,"weight-mode allocation differs")
        for r in records:
            g=audit.GraphView(r["graph"])
            audit.require(set(g.contacts)=={str(v) for v in vertices} and g.edges==simple and not r["fixed"] and not r["excluded"],"sparse_original_vertices_and_simple_edges",r["id"],"graph/boundary differs from declared projection")
            source={k:v for k,v in r["source"].items() if k not in {"weight_mode","weighted_extension","weight_formula","physical_scheduling_claim"}}
            audit.require(source==receipt and r["source"]["physical_scheduling_claim"] is False,"sparse_embedded_source_receipt",r["id"],"source provenance differs")
            for v,c in g.contacts.items():
                weight=1 if r["source"]["weight_mode"]=="unit" else 1+int(sha256(("20261003:"+name+":"+v).encode()).hexdigest(),16)%20
                audit.require(c["weight"]==weight and c["satellite"]=="public_graph" and c["station"]==v and c["start"]==0 and c["end"]==1 and c["task"]=="","sparse_exact_declared_weights_and_embedding",r["id"]+"/"+v,"weight/graph embedding differs")
        summaries.append({"source":name,"vertices":len(vertices),"raw_rows":rows,"simple_edges":len(simple),"dropped_self_links":len(loops),"compressed_sha256":sha256(compressed).hexdigest(),"decompressed_sha256":sha256(text).hexdigest(),"origin_url_receipt":receipt["url"]})
    result={"archive_sha256":audit.file_digest(path),"input_sha256":hashes["data.json"],"contexts":8,"sources":summaries,"checks":dict(audit.CHECKS),"issues":list(audit.ISSUES.values()),"scope":"Raw compressed/decompressed bytes, simple projection, original IDs, weight modes and every graph edge independently checked. All69 self-links are intentionally dropped while retaining vertices; this is not original looped-graph MWIS equivalence. Origin download authenticity beyond archived HTTPS receipts is not independently established. No performance or selection computation occurs."}
    output=Path(output) if output is not None else ROOT/"experiments/analysis/v04/sparse_input_audit.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,default=ROOT/"experiments/runs/v04/public_sparse_v04_001.tar.gz")
    parser.add_argument("--output",type=Path,default=ROOT/"experiments/analysis/v04/sparse_input_audit.json")
    args=parser.parse_args()
    r=run(args.archive,args.output);print(json.dumps({"checks":sum(audit.CHECKS.values()),"issues":r["issues"],"sources":r["sources"]}));raise SystemExit(int(any(i["severity"]=="error" for i in r["issues"])))
