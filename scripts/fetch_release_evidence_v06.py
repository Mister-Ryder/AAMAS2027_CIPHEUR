"""Restore exact large cloud evidence from the public V06 release.

This is file transport only: no experiment, model, optimizer or oracle runs.
Existing differing files are preserved. Downloads are checked before renaming.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'manifest/RELEASE_V06_ASSETS.json'
PREFIX = 'https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR/releases/download/v0.6.0/'

def digest(path):
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def destination(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe evidence path')
    result = (ROOT / Path(*p.parts)).resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise ValueError('Evidence leaves repository')
    return result

def fetch(only):
    manifest = json.loads(MANIFEST.read_bytes())
    if manifest['version'] != 'v06_public_release_assets_001':
        raise ValueError('Unknown release asset contract')
    known = {r['name']: r for r in manifest['assets']}
    if only and not set(only).issubset(known):
        raise ValueError('Unknown requested asset')
    for name in (only or sorted(known)):
        row = known[name]
        if row['url'] != PREFIX + name or '/' in name or '\\' in name:
            raise ValueError('Unexpected public release URL')
        target = destination(row['canonical_path'])
        if target.exists():
            if target.stat().st_size != row['bytes'] or digest(target) != row['sha256']:
                raise ValueError('Existing evidence differs: ' + row['canonical_path'])
            print(json.dumps({'asset': name, 'status': 'already_identical'}), flush=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.download')
        h = sha256(); count = 0
        # Exclusive creation also preserves an interrupted download for inspection.
        with temporary.open('xb') as stream:
            with urlopen(Request(row['url'], headers={'User-Agent': 'CIPHEUR-evidence/0.6.0'}), timeout=60) as response:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    stream.write(block); h.update(block); count += len(block)
        if count != row['bytes'] or h.hexdigest() != row['sha256']:
            raise ValueError('Downloaded evidence identity differs: ' + name)
        if target.exists():
            raise ValueError('Destination appeared during transport')
        temporary.rename(target)
        print(json.dumps({'asset': name, 'status': 'restored', 'bytes': count}), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', nargs='*', help='Omit to restore every large canonical asset')
    fetch(parser.parse_args().assets)
