"""Public DIMACS/SATLIB graph transfer, with immutable source receipts.

These are algorithmic MWIS tests, not physical satellite scenarios. Source
graphs are never chosen by solver success. Unit weights retain the benchmark;
hash weights are explicitly a weighted extension of the same public graph.
"""
from __future__ import annotations
import argparse,io,json,re,tarfile
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
from .model import Contact,Graph

DIMACS_ROOT='https://archive.dimacs.rutgers.edu/pub/challenge/graph/benchmarks/'
SATLIB_ROOT='https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/'

def parse_dimacs_binary(raw):
    header,body=raw.split(b'\n',1);length=int(header)
    preamble=body[:length].decode('ascii');payload=body[length:]
    matches=re.findall(r'^p\s+(?:edge|col)\s+(\d+)\s+(\d+)\s*$',preamble,re.M)
    if len(matches)!=1:raise ValueError('Exactly one graph declaration required')
    n,m=map(int,matches[0]);edges=set();cursor=0
    for i in range(n):
        width=(i+8)//8;row=payload[cursor:cursor+width];cursor+=width
        if len(row)!=width:raise ValueError('Truncated binary adjacency')
        for j in range(i):
            if row[j//8] & (1<<(7-j%8)):edges.add((j,i))
    if cursor!=len(payload) or len(edges)!=m:raise ValueError('DIMACS byte/edge count mismatch')
    return n,frozenset(edges),{'declared_vertices':n,'declared_edges':m,'preamble':preamble}

def parse_cnf(raw):
    text=raw.decode('ascii');declarations=[];tokens=[];ended=False
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('c'):continue
        if line=='%':ended=True;continue
        if ended:
            if line!='0':raise ValueError('Unexpected data after CNF percent terminator')
            continue
        if line.startswith('p'):
            fields=line.split()
            if len(fields)!=4 or fields[:2]!=['p','cnf']:raise ValueError('Invalid CNF declaration')
            declarations.append(tuple(map(int,fields[2:])))
        else:tokens.extend(map(int,line.split()))
    if len(declarations)!=1:raise ValueError('Exactly one CNF declaration required')
    variables,count=declarations[0];clauses=[];current=[]
    for literal in tokens:
        if literal==0:clauses.append(current);current=[]
        else:
            if abs(literal)>variables:raise ValueError('Literal outside variable range')
            current.append(literal)
    if current or len(clauses)!=count:raise ValueError('CNF clause count/terminator mismatch')
    vertices=[];edges=set();by_literal={}
    for c,clause in enumerate(clauses):
        ids=[]
        for position,literal in enumerate(clause):
            idx=len(vertices);vertices.append((c,position,literal));ids.append(idx)
            by_literal.setdefault(literal,[]).append(idx)
        edges.update((a,b) for i,a in enumerate(ids) for b in ids[i+1:])
    for literal,ids in by_literal.items():
        if literal<0:continue
        edges.update(tuple(sorted((a,b))) for a in ids for b in by_literal.get(-literal,[]))
    return len(vertices),frozenset(edges),{'variables':variables,'clauses':count,
        'literal_occurrences':vertices,'unit_weight_upper':count,
        'reduction':'one vertex per literal occurrence; same-clause and complementary-literal conflicts'}

def graph_record(name,family,n,edges,source,weight_mode):
    def weight(i):
        return 1 if weight_mode=='unit' else 1+int(sha256(f'20261003:{name}:{i}'.encode()).hexdigest(),16)%20
    contacts=tuple(Contact(str(i),weight(i),'public_graph',str(i),0,1) for i in range(n))
    identifier=name+'_'+weight_mode
    graph=Graph(identifier,contacts,frozenset((str(a),str(b)) for a,b in edges),
        {'model':'explicit_public_conflict_graph','station_gap':0,'satellite_gap':0},
        {'public_source':name,'weight_mode':weight_mode,'physical_scheduling_claim':False})
    return {'id':identifier,'family':family,'cluster':name,'graph':graph.to_dict(),
        'source':{**source,'weight_mode':weight_mode,
                  'weighted_extension':'SHA25620261003 vertex weights1..20' if weight_mode!='unit' else None}}

def prepare(config_path,output,cache=None):
    config=json.loads(Path(config_path).read_text());root=Path(output);root.mkdir(parents=True,exist_ok=False)
    rawroot=root/'raw';rawroot.mkdir();records=[];receipts=[];unavailable=[]
    def fetch(name,url):
        candidate=Path(cache)/name if cache else None
        return candidate.read_bytes() if candidate and candidate.is_file() else urlopen(url,timeout=30).read()
    for name in config['dimacs']:
        sub='volume/Clique/' if name.startswith('C') else 'clique/'
        url=DIMACS_ROOT+sub+name+'.clq.b'
        try:
            raw=fetch(name+'.clq.b',url);n,source_edges,meta=parse_dimacs_binary(raw)
            (rawroot/(name+'.clq.b')).write_bytes(raw)
            edges=frozenset((a,b) for a in range(n) for b in range(a+1,n) if (a,b) not in source_edges)
            source={'url':url,'sha256':sha256(raw).hexdigest(),'conversion':'exact complement of public clique graph',
                    'original_vertices':n,'original_edges':len(source_edges),'conflict_edges':len(edges)}
            receipts.append({'id':name,**source,'preamble':meta['preamble']})
            records.extend(graph_record(name,'DIMACS',n,edges,source,mode) for mode in config['weight_modes'])
        except Exception as error:unavailable.append({'id':name,'url':url,'error':str(error)})
        print(json.dumps({'prepared_graphs':len(records),'source':name}),flush=True)
    for collection,limit in config['satlib'].items():
        url=SATLIB_ROOT+collection+'.tar.gz'
        try:
            raw=fetch(collection+'.tar.gz',url);(rawroot/(collection+'.tar.gz')).write_bytes(raw)
            archive_hash=sha256(raw).hexdigest()
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
                members=sorted((m for m in archive.getmembers() if m.isfile() and m.name.endswith('.cnf')),key=lambda m:m.name)[:limit]
                if len(members)!=limit:raise ValueError('Too few prespecified SAT instances')
                for member in members:
                    content=archive.extractfile(member).read();n,edges,meta=parse_cnf(content)
                    name=collection+':'+Path(member.name).stem
                    source={'url':url,'archive_sha256':archive_hash,'member':member.name,'sha256':sha256(content).hexdigest(),**meta}
                    receipts.append({'id':name,**source})
                    records.extend(graph_record(name,'SATLIB',n,edges,source,mode) for mode in config['weight_modes'])
        except Exception as error:unavailable.append({'id':collection,'url':url,'error':str(error)})
        print(json.dumps({'prepared_graphs':len(records),'source':collection}),flush=True)
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate public instance identity')
    def write(name,value):(root/name).write_text(json.dumps(value,indent=2,allow_nan=False))
    write('data.json',{'public':records});write('source_receipts.json',receipts)
    write('protocol.json',{'config':config,'config_sha256':sha256(Path(config_path).read_bytes()).hexdigest(),
          'declared_graphs':(len(config['dimacs'])+sum(config['satlib'].values()))*len(config['weight_modes']),
          'retained_graphs':len(records),'unavailable':unavailable,'outcome_selection':False,
          'satlib_sampling':'lexicographically first filenames, fixed count before downloading',
          'scope':'zero-shot algorithmic graph transfer; no claim of satellite physics'})
    write('complete.json',{'complete':True,'retained_graphs':len(records),'unavailable_sources':len(unavailable),
          'data_sha256':sha256((root/'data.json').read_bytes()).hexdigest()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--cache')
    a=p.parse_args();prepare(a.config,a.output,a.cache)
