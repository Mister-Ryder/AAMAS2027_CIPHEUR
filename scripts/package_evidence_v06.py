"""Losslessly package large canonical evidence into Git-compatible binary parts.

Packaging/reassembly operates on bytes only: no experiment is rerun. The manifest
records the unchanged canonical path, length and SHA-256. Reconstruction uses a
new sibling file, checks the full digest, then publishes that exact byte stream.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json,os
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
PART_BYTES=48*1024*1024

def digest(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def safe_path(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe artifact-relative path')
    result=(ROOT/Path(*p.parts)).resolve()
    if not result.is_relative_to(ROOT.resolve()):raise ValueError('Artifact leaves this repository')
    return result

def pack(source,out,part_bytes=PART_BYTES):
    source=Path(source).resolve();out=Path(out).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not out.is_relative_to(ROOT.resolve()):
        raise ValueError('Keep canonical source and binary parts inside this repository')
    if type(part_bytes) is not int or not 0<part_bytes<=1024*1024*1024:
        raise ValueError('Part size must be positive and at most one GiB')
    if not source.is_file() or out.exists():raise ValueError('Preserve existing bytes; require source and a new parts directory')
    out.mkdir(parents=True);parts=[];whole=sha256();length=0
    with source.open('rb') as stream:
        while block:=stream.read(min(1024*1024,part_bytes)):
            name=f'part_{len(parts):04d}.bin';dest=out/name
            part_hash=sha256();part_length=0
            with dest.open('xb') as target:
                while block:
                    target.write(block);whole.update(block);part_hash.update(block)
                    length+=len(block);part_length+=len(block)
                    if part_length==part_bytes:break
                    block=stream.read(min(1024*1024,part_bytes-part_length))
            parts.append({'path':dest.relative_to(ROOT).as_posix(),'bytes':part_length,'sha256':part_hash.hexdigest()})
    manifest={'version':'v06_lossless_evidence_parts_001','canonical_path':source.relative_to(ROOT).as_posix(),
        'bytes':length,'sha256':whole.hexdigest(),'part_bytes':part_bytes,'parts':parts,
        'experiment_reexecution':False,'content_transformations':False}
    with (out/'manifest.json').open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'manifest':(out/'manifest.json').relative_to(ROOT).as_posix(),'bytes':length,'parts':len(parts),'sha256':whole.hexdigest()}))

def restore(manifest_path):
    manifest_path=Path(manifest_path).resolve()
    if not manifest_path.is_relative_to(ROOT.resolve()):raise ValueError('Manifest leaves repository')
    m=json.loads(manifest_path.read_bytes())
    if m.get('version')!='v06_lossless_evidence_parts_001' or m.get('content_transformations') is not False:
        raise ValueError('Unknown or transformed evidence packaging')
    dest=safe_path(m['canonical_path']);parts=m['parts'];seen=set()
    if not parts or sum(p['bytes'] for p in parts)!=m['bytes']:raise ValueError('Incomplete part lengths')
    for p in parts:
        path=safe_path(p['path'])
        if path in seen or path==dest or not path.is_relative_to(manifest_path.parent):
            raise ValueError('Duplicate or misplaced evidence part')
        seen.add(path)
        if path.stat().st_size!=p['bytes'] or digest(path)!=p['sha256']:raise ValueError('Evidence part changed')
    if dest.exists():
        if dest.stat().st_size!=m['bytes'] or digest(dest)!=m['sha256']:raise ValueError('Preserve changed canonical artifact')
        print(json.dumps({'canonical_path':m['canonical_path'],'already_identical':True}));return
    dest.parent.mkdir(parents=True,exist_ok=True);temporary=dest.with_name(dest.name+'.reassembly_v06')
    whole=sha256();length=0
    with temporary.open('xb') as target:
        for p in parts:
            with safe_path(p['path']).open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):
                    whole.update(block);target.write(block);length+=len(block)
    if length!=m['bytes'] or whole.hexdigest()!=m['sha256']:
        raise ValueError('Reassembly mismatch; temporary bytes retained for inspection')
    if dest.exists():raise ValueError('Canonical destination appeared during reassembly')
    # Both resolved paths are checked repository-local regular files. No shell
    # deletion, recursive moves, or source modification is performed.
    os.rename(temporary,dest)
    print(json.dumps({'canonical_path':m['canonical_path'],'bytes':length,'sha256':whole.hexdigest(),'restored':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='action',required=True)
    make=subs.add_parser('pack');make.add_argument('--source',required=True);make.add_argument('--out',required=True)
    make.add_argument('--part-mib',type=int,default=48,help='48 for Git blobs; up to1024 for release assets')
    undo=subs.add_parser('restore');undo.add_argument('--manifest',required=True)
    args=p.parse_args()
    if args.action=='pack':pack(args.source,args.out,args.part_mib*1024*1024)
    else:restore(args.manifest)
