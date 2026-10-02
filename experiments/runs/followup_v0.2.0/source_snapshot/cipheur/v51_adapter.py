"""Read-only adapter for the frozen SNSD-v5.1 satellite conflict model.

The legacy modules remain the authority for conflict predicates.  This module
imports their source into a private namespace without creating bytecode files
inside the frozen project.  Prefix subsets are for integration smoke checks.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Iterable

from .model import Contact, Graph


_PARAMETERS = {
    "ground_trans_time": 340,
    "satellite_change_time": 150,
    "satellite_trans_time": 300,
}
_SOURCE_NAMES = ("data.py", "graph.py", "verifier.py")
_FALLBACK_HINT = "Use the standalone synthetic smoke command if V51 data or NumPy are unavailable."


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_legacy(stable_root: Path) -> tuple[dict[str, ModuleType], dict]:
    """Import original sources without sys.path edits or source-tree writes."""
    source_root = stable_root / "SNSD_V51_FINAL" / "src" / "snsd_core"
    paths = {name: source_root / name for name in _SOURCE_NAMES}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing frozen V51 sources: " + ", ".join(missing) + ". " + _FALLBACK_HINT)
    sources = {name: path.read_bytes() for name, path in paths.items()}
    receipts = {
        name: {"path": str(paths[name]), "sha256": sha256(raw).hexdigest()}
        for name, raw in sources.items()
    }
    fingerprint = sha256(json.dumps(receipts, sort_keys=True).encode("utf-8")).hexdigest()[:20]
    package_name = "_cipheur_frozen_v51_" + fingerprint
    names = {name[:-3]: package_name + "." + name[:-3] for name in _SOURCE_NAMES}
    if all(name in sys.modules for name in names.values()):
        return {key: sys.modules[name] for key, name in names.items()}, receipts

    package = ModuleType(package_name)
    package.__path__ = [str(source_root)]
    package.__package__ = package_name
    sys.modules[package_name] = package
    loaded = []
    try:
        for filename, raw in sources.items():
            name = names[filename[:-3]]
            spec = importlib.util.spec_from_file_location(name, paths[filename])
            if spec is None:
                raise ImportError("Cannot load frozen V51 source " + str(paths[filename]))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            loaded.append(name)
            # compile(bytes) honors Python source encoding declarations and does
            # not write .pyc files.  Relative imports resolve in our private package.
            exec(compile(raw, str(paths[filename]), "exec"), module.__dict__)
            setattr(package, filename[:-3], module)
    except Exception as exc:
        for name in loaded:
            sys.modules.pop(name, None)
        sys.modules.pop(package_name, None)
        if isinstance(exc, ModuleNotFoundError) and exc.name == "numpy":
            raise RuntimeError("The optional V51 adapter requires NumPy. " + _FALLBACK_HINT) from exc
        raise
    return {key: sys.modules[name] for key, name in names.items()}, receipts


def _nonnegative_int(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(label + " must be a nonnegative integer")
    return value


def load_v51_pair(
    stable_root: Path,
    csv_path: Path | None = None,
    limit: int = 64,
    parameter: str = "ground_trans_time",
    before: int = 340,
    after: int = 500,
) -> tuple[Graph, Graph]:
    """Build aligned legacy graphs for one parameter intervention.

    Both sides use the first ``limit`` CSV opportunities in their original
    order.  No claim about full-C3 performance or reversal existence follows
    from this subset.  No original source or data file is copied or modified.
    """
    stable_root = Path(stable_root).expanduser().resolve()
    csv_path = (Path(csv_path).expanduser().resolve() if csv_path is not None else
                stable_root / "SNSD_V51_FINAL" / "data" / "C3.csv")
    if parameter not in _PARAMETERS:
        raise ValueError("parameter must be one of: " + ", ".join(_PARAMETERS))
    _nonnegative_int(limit, "limit")
    if limit == 0:
        raise ValueError("limit must be positive")
    _nonnegative_int(before, "before")
    _nonnegative_int(after, "after")
    if before == after:
        raise ValueError("before and after must differ for a constraint intervention")
    if not csv_path.is_file():
        raise FileNotFoundError("Missing V51 CSV: " + str(csv_path) + ". " + _FALLBACK_HINT)
    legacy, sources = _load_legacy(stable_root)
    dataset = legacy["data"].load_arcs(str(csv_path))
    arcs = tuple(dataset.arcs[:limit])
    if not arcs:
        raise ValueError("The V51 CSV contains no opportunities")
    if any(arc.id != i for i, arc in enumerate(arcs)):
        raise ValueError("The frozen loader did not return dense prefix IDs")
    # IDs come from the original loader, not a fresh resource enumeration.
    contacts = tuple(
        Contact(str(arc.id), float(arc.weight), arc.satellite_name,
                arc.ground_name, arc.link_st, arc.link_et)
        for arc in arcs
    )
    original_ids = [str(arc.id) for arc in arcs]
    metadata = {
        str(arc.id): {
            "original_id": arc.id, "ground_id": arc.ground,
            "satellite_id": arc.satellite, "trace_start": arc.trace_st,
            "trace_end": arc.trace_et, "priority": arc.priority,
        } for arc in arcs
    }
    common = {
        "adapter": "cipheur.v51_adapter",
        "source_project": str(stable_root),
        "source_files": sources,
        "source_data": {
            "path": str(csv_path), "sha256": _file_sha256(csv_path),
            "encoding": dataset.encoding, "header": list(dataset.header),
            "total_opportunities": len(dataset.arcs),
        },
        "scope": "prefix_subset_smoke_only",
        "limit_requested": limit, "num_contacts": len(arcs),
        "local_to_original_ids": original_ids,
        "arc_metadata": metadata,
        "intervention": {"parameter": parameter, "before": before, "after": after},
    }
    pair = []
    for value in (before, after):
        params = dict(_PARAMETERS)
        params[parameter] = value
        original_graph = legacy["graph"].build_conflict_graph(
            arcs, legacy["graph"].ConflictParameters(**params))
        edges = frozenset(tuple(sorted((str(int(u)), str(int(v)))))
                          for u, v in original_graph.edges)
        provenance = {**common, "legacy_graph_hash": original_graph.graph_hash}
        adapted = Graph("v51_prefix_%d_%s_%d" % (len(arcs), parameter, value),
                        contacts, edges, {"model": "v51_legacy", **params}, provenance)
        # Runtime-only verifier state is excluded from serializable provenance.
        adapted._v51_context = (original_graph, legacy["verifier"],
                                {str(arc.id): i for i, arc in enumerate(arcs)})
        pair.append(adapted)
    added = pair[1].edges - pair[0].edges
    removed = pair[0].edges - pair[1].edges
    for adapted in pair:
        adapted.provenance["intervention_edge_changes"] = {
            "added": len(added), "removed": len(removed),
            "graph_changed": bool(added or removed),
        }
    return pair[0], pair[1]


def verify_v51_selection(graph: Graph, selected: Iterable[str]) -> dict:
    """Check an adapted selection using the original read-only verifier.

    Use a Graph returned by ``load_v51_pair``; runtime verifier state is not
    retained by Graph serialization.  Contact IDs and mapped local integer IDs
    are returned together so the old check can be audited.
    """
    context = getattr(graph, "_v51_context", None)
    if context is None:
        raise ValueError("Original verifier state is unavailable; reload with load_v51_pair")
    original_graph, verifier, mapping = context
    selected = tuple(selected)
    invalid = [contact_id for contact_id in selected if contact_id not in mapping]
    # Preserve unknowns as out-of-range IDs and preserve duplicates for the
    # original checker rather than silently filtering or repairing the set.
    mapped = tuple(mapping.get(contact_id, original_graph.num_nodes + i)
                   for i, contact_id in enumerate(selected))
    check = verifier.verify_selected_ids(original_graph, mapped)
    return {
        "feasible": check.feasible,
        "selected_contact_ids": list(selected), "mapped_local_ids": list(mapped),
        "invalid_contact_ids": invalid,
        "conflicting_local_edges": [list(edge) for edge in check.conflicting_edges],
        "invalid_local_ids": list(check.invalid_ids),
        "duplicate_local_ids": list(check.duplicate_ids),
    }
