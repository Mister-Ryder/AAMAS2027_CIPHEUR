"""One-pass review-input reconstruction and fixed source/split graph checks.

Read-only source/graph check. No paid result, selection, scoring programme,
solver, STK, LLM or oracle is read/imported/called. Binary volumes are rebuilt
in an automatically removed temporary file, not a persistent extra archive.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
import numpy as np

NEW_SOURCES = ["CP-" + g + "-" + r for r in ("r006", "r008", "r009") for g in ("AU", "AP")]
CONFIGS = {"g0340": (340, 340), "g0680": (680, 680), "g1200": (1200, 1200), "g1800": (1800, 1800),
           "gW1200_gE0340_s0150": (1200, 340), "gW0340_gE1200_s0150": (340, 1200),
           "gW0680_gE1200_s0150": (680, 1200), "gW1200_gE0680_s0150": (1200, 680)}
REVIEW_SHA = "d755572f53bc917d410e9fce9f67812ebe40c6344206eb545bc9406d52b1ac45"
IDENTITY_ARRAYS = ('contact_id', 'pass_id', 'satellite_id', 'site_id', 'antenna_id', 'start_ticks', 'end_ticks')

def hash_bytes(value): return hashlib.sha256(value).hexdigest()

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def array_hash(*arrays):
    h = hashlib.sha256()
    for a in arrays:
        if a.dtype.kind in 'USO':
            for item in a.tolist():
                value = str(item).encode('utf-8'); h.update(len(value).to_bytes(8, 'little')); h.update(value)
        else: h.update(str(a.dtype).encode('ascii')); h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()

def require(condition, message):
    if not condition: raise ValueError(message)

def check_new_graph(payload, meta, source, cfg):
    with np.load(io.BytesIO(payload), allow_pickle=False) as z:
        fields = set(z.files)
        needed = set(IDENTITY_ARRAYS) | {'weight_ticks', 'edge_u', 'edge_v', 'edge_mask', 'indptr', 'indices', 'ground_gap_by_node_ticks', 'antenna_group_by_node', 'satellite_gap_ticks', 'ticks_per_second', 'source_id', 'source_group', 'config_id', 'split'}
        require(needed <= fields, 'Missing graph contract arrays')
        d = {k: z[k] for k in needed}
    split = 'validation' if source.endswith('r006') else 'test'
    require(meta['source_id'] == str(d['source_id']) == source and meta['config_id'] == str(d['config_id']) == cfg, 'Source/config identity differs')
    require(meta['split'] == str(d['split']) == split, 'Fixed source split differs')
    require(meta['source_group'] == str(d['source_group']) == 'CP-SOURCE-' + source[-4:], 'Source group differs')
    require(int(d['ticks_per_second']) == 1_000_000 and int(d['satellite_gap_ticks']) == 150_000_000, 'Microtick/satellite policy differs')
    n, m = len(d['weight_ticks']), len(d['edge_u']); u, v = d['edge_u'], d['edge_v']
    require(n == meta['stats']['n'] and m == meta['stats']['m'], 'Metadata dimensions differ')
    require(np.array_equal(d['weight_ticks'], d['end_ticks'] - d['start_ticks']) and np.all(d['weight_ticks'] > 0), 'Reward is not original complete-window endpoint difference')
    require(all(len(d[k]) == n for k in IDENTITY_ARRAYS), 'Node mapping length differs')
    require(array_hash(*(d[k] for k in IDENTITY_ARRAYS)) == meta['node_mapping_sha256'], 'Node mapping hash differs')
    require(array_hash(d['weight_ticks']) == meta['weight_ticks_sha256'], 'Weight hash differs')
    require(array_hash(u, v, d['edge_mask']) == meta['edge_arrays_sha256'], 'Edge hash differs')
    keys = u.astype(np.int64) * n + v.astype(np.int64)
    require(np.all(u >= 0) and np.all(u < v) and np.all(v < n) and (len(keys) < 2 or np.all(np.diff(keys) > 0)), 'Nonself/unique/sorted edges differ')
    ptr, indices = d['indptr'], d['indices']
    require(len(ptr) == n + 1 and int(ptr[0]) == 0 and int(ptr[-1]) == 2 * m and len(indices) == 2 * m and np.all(np.diff(ptr) >= 0), 'CSR dimensions differ')
    require(np.all(indices >= 0) and np.all(indices < n), 'CSR index out of range')
    csr_rows = np.repeat(np.arange(n, dtype=np.int64), np.diff(ptr))
    csr_edges = np.sort(csr_rows * n + indices)
    require(np.array_equal(csr_edges, np.sort(np.concatenate((u * n + v, v * n + u)))), 'CSR/undirected edge content differs')
    west, east = CONFIGS[cfg]
    expected_gap = np.where(d['antenna_group_by_node'] == 'west', west * 1_000_000, east * 1_000_000)
    require(set(d['antenna_group_by_node'].tolist()) == {'west', 'east'} and np.array_equal(d['ground_gap_by_node_ticks'], expected_gap), 'Actual per-antenna W/E policy differs')
    require(meta['west_gap_seconds'] == west and meta['east_gap_seconds'] == east and meta['satellite_gap_seconds'] == 150, 'Metadata policy differs')
    earlier_u = (d['start_ticks'][u] < d['start_ticks'][v]) | ((d['start_ticks'][u] == d['start_ticks'][v]) & (u < v))
    earlier, later = np.where(earlier_u, u, v), np.where(earlier_u, v, u)
    gap = d['start_ticks'][later] - d['end_ticks'][earlier]
    ground = (d['antenna_id'][u] == d['antenna_id'][v]) & (gap < d['ground_gap_by_node_ticks'][earlier])
    satellite = (d['satellite_id'][u] == d['satellite_id'][v]) & (gap < 150_000_000)
    require(np.all(ground | satellite), 'Stored conflict edge violates fixed resource predicate')
    reasons = ground.astype(np.uint8) + satellite.astype(np.uint8) * 2 + np.where(gap < 0, 4, 8).astype(np.uint8)
    require(np.array_equal(reasons, d['edge_mask']), 'Edge reason bits differ')
    identity = (meta['node_mapping_sha256'], meta['weight_ticks_sha256'], meta['raw_contacts_sha256'], meta['raw_manifest_sha256'])
    return {'source': source, 'config': cfg, 'split': split, 'nodes': n, 'edges': m, 'identity_contract': list(identity),
            'npz_sha256': hash_bytes(payload), 'CSR_matches_edges': True, 'stored_edges_match_resource_predicate': True,
            'edge_completeness_scope': 'Existing frozen builder receipt supplies edge completeness; this repeatable check validates stored edges/CSR and hashes without regenerating graphs.'}, identity

def run(args, receipt):
    review_manifest = args.review_root / 'manifest.json'; manifest = json.loads(review_manifest.read_text(encoding='utf-8'))
    index_path = args.perf_root / 'source_index.json'; index = json.loads(index_path.read_text(encoding='utf-8'))
    receipt['review_manifest_sha256'] = file_sha(review_manifest); receipt['source_index_sha256'] = file_sha(index_path)
    require(manifest['archive_sha256'] == args.expected_review_sha256, 'Published review archive SHA is not the expected frozen hash')
    sources = {s['scene_id']: s for s in index['sources']}; require(set(sources) == set(NEW_SOURCES), 'Exactly6new physical sources required')
    for source, s in sources.items():
        require(s['split'] == ('validation' if source.endswith('r006') else 'test') and s['source_group'] == 'CP-SOURCE-' + source[-4:], 'Index source/split contract differs')
        require(s['physical_status'] == s['graphs_status'] == 'success' and s['unique_graph_configurations_complete'] == 8 and s['formal_dataset'] is True, 'New source not complete formal data')
    receipt['source_splits'] = {s: sources[s]['split'] for s in sorted(sources)}; receipt['parts'] = []; graph_receipts = []
    combined_sha = hashlib.sha256(); total = 0
    with tempfile.TemporaryFile(mode='w+b') as rebuilt:
        for part in manifest['parts_in_order']:
            require(PurePosixPath(part['path']).name == part['path'], 'Unsafe volume path')
            h = hashlib.sha256(); part_bytes = 0
            with (args.review_root / part['path']).open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block); combined_sha.update(block); rebuilt.write(block); part_bytes += len(block)
            require(h.hexdigest() == part['sha256'] and part_bytes == part['bytes'], 'Volume bytes/hash differs')
            receipt['parts'].append({'path': part['path'], 'bytes': part_bytes, 'sha256': h.hexdigest()}); total += part_bytes
        require(total == manifest['archive_bytes'] and combined_sha.hexdigest() == manifest['archive_sha256'], 'Reconstructed archive bytes/hash differs')
        receipt['reconstructed_archive'] = {'bytes': total, 'sha256': combined_sha.hexdigest(), 'persistent_copy_created': False}
        rebuilt.seek(0)
        with zipfile.ZipFile(rebuilt) as archive:
            names = archive.namelist(); file_map = {v['path']: v for v in manifest['files']}
            provenance_names = {'graph_input_inventory.json', 'heldout/source_index.json'}
            require(len(names) == len(set(names)) and set(names) == set(file_map) | provenance_names, 'Review archive inventory differs')
            internal_inventory = json.loads(archive.read('graph_input_inventory.json'))
            require({v['path']: v for v in internal_inventory['files']} == file_map, 'Internal/public graph inventory differs')
            source_index_bytes = archive.read('heldout/source_index.json')
            require(hash_bytes(source_index_bytes) == receipt['source_index_sha256'], 'Public archived source index differs from local frozen index')
            receipt['archive_provenance_files'] = [{'path': name, 'sha256': hash_bytes(archive.read(name))} for name in sorted(provenance_names)]
            identities = defaultdict(set); counts = defaultdict(int)
            for name in sorted(names):
                pure = PurePosixPath(name); require(not pure.is_absolute() and '..' not in pure.parts, 'Unsafe archive member')
                if name in provenance_names: continue
                payload = archive.read(name); record = file_map[name]
                require(hash_bytes(payload) == record['sha256'] and len(payload) == record['bytes'], 'Archive member bytes/hash differs')
                if name.startswith('heldout/graphs/'):
                    source, file = pure.parts[2:]; cfg = Path(file).stem
                    require(source in sources and cfg in CONFIGS, 'Unregistered heldout source/config')
                    local = args.perf_root / 'graphs' / source / file
                    require(file_sha(local) == record['sha256'], 'Public reviewed input and local frozen graph differ')
                    if pure.suffix == '.npz':
                        meta_name = str(pure.with_suffix('.json')); meta = json.loads(archive.read(meta_name))
                        require(meta['npz_sha256'] == record['sha256'], 'Archived metadata and NPZ hash differ')
                        graphreceipt, identity = check_new_graph(payload, meta, source, cfg)
                        graphreceipt['metadata_sha256'] = file_map[meta_name]['sha256']; graph_receipts.append(graphreceipt)
                        identities[source].add(identity); counts[source] += 1
                elif name.startswith('train/graphs/'):
                    require(pure.parts[2][-4:] in ('r000', 'r001'), 'TRAIN physical source overlaps heldout split')
            require(len(graph_receipts) == 48 and all(counts[s] == 8 and len(identities[s]) == 1 for s in NEW_SOURCES), '48graph cross-config identity contract differs')
            receipt['review_file_count'] = len(names); receipt['review_train_graphs'] = sum(n.startswith('train/') and n.endswith('.npz') for n in names)
            require(receipt['review_train_graphs'] == 16, 'Review TRAIN16contract differs')
    receipt.update(status='success', new_graph_count=48, graph_checks=graph_receipts, fixed_node_weight_identity_all_sources=True,
                   optimizer_calls=0, programme_score_calls=0, model_calls=0, oracle_calls=0, result_files_read=0,
                   temporary_reconstruction_closed=True)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--review-root', type=Path, required=True); ap.add_argument('--perf-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True); ap.add_argument('--expected-review-sha256', default=REVIEW_SHA)
    args = ap.parse_args(); receipt = {'version': 'fixed_graph_input_reproduction_v1', 'status': 'running', 'script_sha256': file_sha(Path(__file__))}
    try: run(args, receipt)
    except Exception as error:
        receipt.update(status='failed', error=type(error).__name__ + ': ' + str(error)); raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('status', 'new_graph_count', 'review_file_count', 'fixed_node_weight_identity_all_sources')}, ensure_ascii=False))

if __name__ == '__main__': main()
