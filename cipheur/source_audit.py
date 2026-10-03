"""Reconstruct the frozen source graph before checking saved C3 selections."""
from functools import lru_cache
from pathlib import Path
from dataclasses import replace
from .v51_adapter import _load_legacy

@lru_cache(maxsize=2)
def source(stable_root):
    legacy, receipts = _load_legacy(Path(stable_root))
    data = legacy['data'].load_arcs(str(Path(stable_root)/'SNSD_V51_FINAL'/'data'/'C3.csv'))
    return legacy, {a.id:a for a in data.arcs}, receipts

def check_source_graph(graph, selections, stable_root):
    if graph.constraints.get('model')!='v51_legacy':
        return {'applicable':False}
    legacy, arcs, receipts=source(str(stable_root))
    ids=graph.provenance['original_ids']; mapping={str(v):i for i,v in enumerate(ids)}
    local=tuple(replace(arcs[v],id=i) for i,v in enumerate(ids))
    params={k:v for k,v in graph.constraints.items() if k!='model'}
    original=legacy['graph'].build_conflict_graph(local,legacy['graph'].ConflictParameters(**params))
    reconstructed=frozenset(tuple(sorted((str(ids[int(a)]),str(ids[int(b)])))) for a,b in original.edges)
    if reconstructed!=graph.edges:raise AssertionError('Saved graph differs from source predicates')
    checks={}
    for name,selected in selections.items():
        mapped=[mapping[v] for v in selected]
        check=legacy['verifier'].verify_selected_ids(original,mapped)
        if not check.feasible:raise AssertionError('Original source verifier rejected '+name)
        checks[name]={'feasible':check.feasible,'conflicts':len(check.conflicting_edges),
                      'duplicates':len(check.duplicate_ids),'invalid':len(check.invalid_ids)}
    return {'applicable':True,'reconstructed_edges_identical':True,'checks':checks,
            'source_sha256':{k:v['sha256'] for k,v in receipts.items()}}
