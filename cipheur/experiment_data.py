"""Static, outcome-independent train/validation/test scheduling data.

Generation does not consult an optimisation oracle, a ranking program, or
performance labels.  Diagnostic probes and source-derived C3 subsets remain
separate families; neither is presented as a sample of natural synthetic data.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Any

from .model import Contact, Graph, aligned_intervention, temporal_graph


SPLITS = ("train", "validation", "test")
DEFAULT_COUNTS = {"diagnostic": 20, "random_temporal": 20, "c3": 12}
_RANDOM_SEED_BASE = {"train": 1000, "validation": 2000, "test": 3000}
_DIAGNOSTIC_SEED_BASE = {"train": 100000, "validation": 200000, "test": 300000}
_REVERSAL_GAPS = {"train": (0.0, 4.0), "validation": (0.2, 4.4), "test": (0.6, 5.0)}
_PRESERVATION_GAPS = {"train": (0.0, 0.5), "validation": (0.05, 0.65), "test": (0.1, 0.8)}
_RANDOM_GAPS = {"train": (0.0, 2.0), "validation": (0.3, 3.0), "test": (0.6, 5.0)}
_RANDOM_SIZES = {"train": (16, 24), "validation": (18, 26), "test": (20, 28)}
_C3_TARGET_GAPS = {"train": 500, "validation": 600, "test": 700}


def _canonical_hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")).hexdigest()


def instance_fingerprint(contacts) -> str:
    """Contact-level identity, independent of graph name and constraint values."""
    return _canonical_hash([asdict(c) for c in sorted(contacts, key=lambda c: c.id)])


def _positive_int(value, label: str, *, allow_zero=False) -> int:
    lower = 0 if allow_zero else 1
    if type(value) is not int or value < lower:
        raise ValueError(f"{label} must be an integer >= {lower}")
    return value


def _count(config: dict, family: str, split: str) -> int:
    counts = config.get("counts", {})
    if not isinstance(counts, dict):
        raise ValueError("counts must map family names to integers or split mappings")
    value = counts.get(family, DEFAULT_COUNTS[family])
    if isinstance(value, dict):
        value = value.get(split, 0)
    count = _positive_int(value, f"counts.{family}.{split}", allow_zero=True)
    # The public seed ranges are fixed rather than silently extended into the
    # next split.  C3 uses deterministic time windows, not random seeds.
    if family != "c3" and count > 1000:
        raise ValueError("Synthetic counts must be <= 1000 to preserve disjoint seed ranges")
    if family == "c3" and count > 86400:
        raise ValueError("C3 counts must be <= 86400 to keep nonempty time windows")
    return count


def _opaque_ids(rng: random.Random, roles: list[str]) -> dict[str, str]:
    values = rng.sample(range(1 << 30), len(roles))
    return {role: f"n_{value:08x}" for role, value in zip(roles, values)}


def _choose_actions(left: Graph, right: Graph, fixed=(), excluded=()):
    active = left.available(fixed, excluded) & right.available(fixed, excluded)
    common = sorted(edge for edge in left.edges & right.edges if set(edge) <= active)
    return common[0] if common else (None, None)


def _record(record_id: str, family: str, left: Graph, right: Graph,
            source: dict, fixed=(), excluded=(), actions=None) -> dict:
    fixed, excluded = tuple(fixed), tuple(excluded)
    alignment = aligned_intervention(left, right, fixed, excluded)
    a, b = actions if actions is not None else _choose_actions(left, right, fixed, excluded)
    if a is not None or b is not None:
        if a is None or b is None or tuple(sorted((a, b))) not in left.edges & right.edges:
            raise ValueError("Candidate actions must be a common conflict edge")
        for graph in (left, right):
            if not {a, b} <= graph.available(fixed, excluded):
                raise ValueError("Candidate actions must remain individually boundary-feasible")
    receipt = {
        **source, "instance_fingerprint": instance_fingerprint(left.contacts),
        "left_graph_fingerprint": left.digest(), "right_graph_fingerprint": right.digest(),
        "intervention": alignment, "contact_count": len(left.contacts),
        "candidate_status": "common_conflict_edge" if a is not None else "no_common_conflict_edge",
        "outcome_filtering": False,
    }
    return {"id": record_id, "family": family, "left": left, "right": right,
            "fixed": fixed, "excluded": excluded, "a": a, "b": b, "source": receipt}


def diagnostic_pair(split: str, index: int, subtype: str | None = None) -> dict:
    """Build a temporal diagnostic probe with ID and time randomisation.

    The reversal has X independent -> clique and a fixed one-edge Y triple.
    At unit weight scale, without the independent fixed boundary, its four
    conditional optima are 20, 26, 20, 14.  This statement follows from the
    construction, and is never used to select or discard a generated record.
    """
    if split not in SPLITS:
        raise ValueError("Unknown split")
    _positive_int(index, "index", allow_zero=True)
    if index >= 1000:
        raise ValueError("Diagnostic index must be < 1000")
    subtype = subtype or ("reversal", "reversal", "reversal", "preservation", "tie")[index % 5]
    if subtype not in ("reversal", "preservation", "tie"):
        raise ValueError("Unknown diagnostic subtype")
    seed = _DIAGNOSTIC_SEED_BASE[split] + index
    rng = random.Random(seed)
    roles = ["a", "b", "x1", "x2", "x3", "y1", "y2", "y3", "z"]
    if subtype != "reversal":
        roles += ["outside1", "outside2"]
    ids = _opaque_ids(rng, roles)
    # Dyadic multipliers keep the deliberately identical base vectors exactly
    # equal under ordinary binary arithmetic, not just within a tolerance.
    scale = rng.choice((0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0))
    shift = rng.randint(0, 1000000) + SPLITS.index(split) * 2000000
    resource_tag = f"r_{rng.getrandbits(32):08x}"
    sat_a, sat_b = "SA_" + resource_tag, "SB_" + resource_tag
    g0, gx = "G0_" + resource_tag, "GX_" + resource_tag
    raw = [("a", 8, sat_a, g0, 0, 10), ("b", 8, sat_b, g0, 0, 10)]
    x_times = ((2, 3), (2.5, 3.5), (6, 7)) if subtype == "tie" else ((2, 3), (4, 5), (6, 7))
    for i, (start, end) in enumerate(x_times, 1):
        raw.append((f"x{i}", 6, sat_a, gx, start, end))
    for i, (start, end) in enumerate(((2, 3), (2.5, 3.5), (6, 7)), 1):
        raw.append((f"y{i}", 6, sat_b, f"GY{i}_" + resource_tag, start, end))
    raw.append(("z", 2, "SZ_" + resource_tag, "GZ_" + resource_tag, 30, 31))
    if subtype != "reversal":
        # Only this exterior resource changes when the small ground gap is
        # increased.  It cannot alter the difference of a/b completion values.
        raw += [("outside1", 2, "SO1_" + resource_tag, "GO_" + resource_tag, 20, 21),
                ("outside2", 2, "SO2_" + resource_tag, "GO_" + resource_tag, 21.3, 22.3)]
    contacts = [Contact(ids[role], weight * scale, satellite, station,
                        start + shift, end + shift)
                for role, weight, satellite, station, start, end in raw]
    rng.shuffle(contacts)
    before, after = (_REVERSAL_GAPS if subtype == "reversal" else _PRESERVATION_GAPS)[split]
    record_id = f"diagnostic_{split}_{index:04d}"
    left = temporal_graph(record_id + "_before", contacts, station_gap=before, satellite_gap=0)
    right = temporal_graph(record_id + "_after", contacts, station_gap=after, satellite_gap=0)
    source = {"split": split, "seed": seed, "origin": "designed_temporal_probe",
              "subtype": subtype, "population_claim": "mechanism_diagnostic_only",
              "weight_scale": scale, "time_translation": shift,
              "semantic_roles": ids, "construction": "equal_base_features_distinct_neighbor_structure",
              "expected_relation_by_construction": {
                  "reversal": ["b", "a"], "preservation": ["b", "b"], "tie": ["tie", "tie"]}[subtype]}
    return _record(record_id, "diagnostic", left, right, source, fixed=(ids["z"],),
                   actions=(ids["a"], ids["b"]))


def _random_pair(split: str, index: int) -> dict:
    seed = _RANDOM_SEED_BASE[split] + index
    rng = random.Random(seed)
    size = _RANDOM_SIZES[split][index % 2]
    satellite_count = 4 + SPLITS.index(split) + index % 2
    station_count = 3 + SPLITS.index(split)
    roles = [f"contact{i}" for i in range(size - 1)] + ["boundary"]
    ids = _opaque_ids(rng, roles)
    resource_tag = f"r_{rng.getrandbits(32):08x}"
    shift = SPLITS.index(split) * 2000000 + rng.randint(0, 1000000)
    contacts = []
    for role in roles[:-1]:
        start = rng.randint(0, 320) / 4
        duration = rng.randint(2, 48) / 4
        contacts.append(Contact(ids[role], rng.randint(1, 48) / 4,
                                f"S{rng.randrange(satellite_count)}_" + resource_tag,
                                f"G{rng.randrange(station_count)}_" + resource_tag,
                                shift + start, shift + start + duration))
    contacts.append(Contact(ids["boundary"], rng.randint(1, 12) / 4,
                            "SZ_" + resource_tag, "GZ_" + resource_tag, shift + 100, shift + 101))
    rng.shuffle(contacts)
    before, after = _RANDOM_GAPS[split]
    record_id = f"random_temporal_{split}_{index:04d}"
    left = temporal_graph(record_id + "_before", contacts, station_gap=before, satellite_gap=0)
    right = temporal_graph(record_id + "_after", contacts, station_gap=after, satellite_gap=0)
    source = {"split": split, "seed": seed, "origin": "random_temporal_contacts",
              "population_claim": "specified_synthetic_generator_only",
              "generator": {"requested_contact_count": size, "satellites": satellite_count,
                            "stations": station_count, "start_grid": 0.25,
                            "horizon": 80, "satellite_gap": 0.0},
              "time_translation": shift}
    return _record(record_id, "random_temporal", left, right, source, fixed=(ids["boundary"],))


def _default_stable_root() -> Path:
    return Path(__file__).resolve().parents[3] / "2026-ESWA" / "DAI2026_SNSD_V51_STABLE"


def _c3_records(config: dict, counts: dict[str, int]) -> tuple[dict, dict]:
    records = {split: [] for split in SPLITS}
    if not any(counts.values()):
        return records, {"status": "disabled_by_configuration", "requested": counts,
                         "generated": {split: 0 for split in SPLITS}}
    stable_root = Path(config.get("stable_root") or _default_stable_root()).expanduser().resolve()
    csv_path = Path(config.get("csv_path") or stable_root / "SNSD_V51_FINAL" / "data" / "C3.csv").expanduser().resolve()
    max_contacts = _positive_int(config.get("c3_max_contacts", 28), "c3_max_contacts")
    if max_contacts > 28:
        raise ValueError("c3_max_contacts must be <= 28 for this local-subproblem protocol")
    stations_per_group = _positive_int(config.get("c3_stations_per_group", 5), "c3_stations_per_group")
    satellites_per_group = _positive_int(config.get("c3_satellites_per_group", 16), "c3_satellites_per_group")
    try:
        from .v51_adapter import _load_legacy, _file_sha256, _PARAMETERS
        if not csv_path.is_file():
            raise FileNotFoundError("Missing frozen C3 data: " + str(csv_path))
        legacy, sources = _load_legacy(stable_root)
        dataset = legacy["data"].load_arcs(str(csv_path))
    except (FileNotFoundError, ModuleNotFoundError, RuntimeError) as error:
        return records, {"status": "unavailable", "reason": str(error),
                         "source_project": str(stable_root), "data_path": str(csv_path),
                         "requested": counts, "generated": {split: 0 for split in SPLITS},
                         "synthetic_substitution": False}
    data_receipt = {"path": str(csv_path), "sha256": _file_sha256(csv_path),
                    "encoding": dataset.encoding, "header": list(dataset.header),
                    "total_opportunities": len(dataset.arcs)}
    day_arcs = {day: [] for day in range(3)}
    for arc in dataset.arcs:
        day = arc.link_st // 86400
        if day in day_arcs:
            day_arcs[day].append(arc)
    coverage = {"status": "available", "requested": counts, "source_project": str(stable_root),
                "data": data_receipt, "source_files": sources, "scope": "resource_time_window_subproblems",
                "full_c3_performance_claim": False, "empty_windows": [], "splits": {}}
    used_original_ids: set[int] = set()
    for day, split in enumerate(SPLITS):
        count = counts[split]
        split_coverage = {"day_index": day, "day_interval": [day * 86400, (day + 1) * 86400],
                          "day_opportunities": len(day_arcs[day]), "generated": 0,
                          "eligible_before_cap": 0, "contacts_retained": 0,
                          "graph_changed_pairs": 0, "candidate_pairs": 0, "windows": []}
        coverage["splits"][split] = split_coverage
        for index in range(count):
            lo = day * 86400 + index * 86400 // count
            hi = day * 86400 + (index + 1) * 86400 // count
            grounds = {((index * stations_per_group + k) % len(dataset.ground_names))
                       for k in range(min(stations_per_group, len(dataset.ground_names)))}
            satellites = {((index * satellites_per_group + k) % len(dataset.satellite_names))
                          for k in range(min(satellites_per_group, len(dataset.satellite_names)))}
            eligible = [arc for arc in day_arcs[day]
                        if lo <= arc.link_st < hi and arc.ground in grounds and arc.satellite in satellites
                        and arc.link_et > arc.link_st]
            # A fixed selection rule, specified before any graph/oracle call.
            selected = sorted(eligible, key=lambda arc: (arc.link_st, arc.id))[:max_contacts]
            window_receipt = {"window_index": index, "start_interval": [lo, hi],
                              "ground_ids": sorted(grounds), "satellite_ids": sorted(satellites),
                              "eligible_before_cap": len(eligible), "retained": len(selected)}
            split_coverage["windows"].append(window_receipt)
            split_coverage["eligible_before_cap"] += len(eligible)
            if not selected:
                coverage["empty_windows"].append({"split": split, **window_receipt})
                continue
            selected = sorted(selected, key=lambda arc: arc.id)
            original_ids = [arc.id for arc in selected]
            if used_original_ids.intersection(original_ids):
                raise AssertionError("C3 original opportunity leaked across windows/splits")
            used_original_ids.update(original_ids)
            # Frozen build_conflict_graph requires dense IDs.  Only temporary
            # IDs are remapped; original resource IDs and every physical value
            # survive unchanged, and edge endpoints are mapped back afterwards.
            local_arcs = tuple(replace(arc, id=i) for i, arc in enumerate(selected))
            contacts = tuple(Contact(str(arc.id), float(arc.weight), arc.satellite_name,
                                     arc.ground_name, arc.link_st, arc.link_et) for arc in selected)
            record_id = f"c3_{split}_{index:04d}"
            pair = []
            for gap in (340, _C3_TARGET_GAPS[split]):
                parameters = {**_PARAMETERS, "ground_trans_time": gap}
                original = legacy["graph"].build_conflict_graph(
                    local_arcs, legacy["graph"].ConflictParameters(**parameters))
                edges = frozenset(tuple(sorted((str(original_ids[int(u)]), str(original_ids[int(v)]))))
                                  for u, v in original.edges)
                provenance = {"source_project": str(stable_root), "source_files": sources,
                              "source_data": data_receipt, "scope": "resource_time_window_subproblem",
                              "original_ids": original_ids, "temporary_local_legacy_graph_hash": original.graph_hash,
                              "window": window_receipt}
                graph = Graph(record_id + f"_gap{gap}", contacts, edges,
                              {"model": "v51_legacy", **parameters}, provenance)
                graph._v51_context = (original, legacy["verifier"],
                                      {str(arc.id): i for i, arc in enumerate(selected)})
                pair.append(graph)
            left, right = pair
            isolated = sorted(v for v in left.nodes if not left.adj[v] and not right.adj[v])
            fixed = (isolated[-1],) if isolated else ()
            source = {"split": split, "seed": None, "origin": "frozen_c3_opportunities",
                      "population_claim": "source_derived_local_subproblems_only",
                      "original_ids": original_ids, "source_data": data_receipt,
                      "source_files": sources, "window": window_receipt,
                      "cap_selection": "earliest_link_start_then_original_id",
                      "node_cap": max_contacts,
                      "arc_metadata": {str(arc.id): {"ground_id": arc.ground, "satellite_id": arc.satellite,
                                                    "trace_start": arc.trace_st, "trace_end": arc.trace_et,
                                                    "priority": arc.priority} for arc in selected}}
            record = _record(record_id, "c3", left, right, source, fixed=fixed)
            records[split].append(record)
            split_coverage["generated"] += 1
            split_coverage["contacts_retained"] += len(selected)
            split_coverage["graph_changed_pairs"] += left.edges != right.edges
            split_coverage["candidate_pairs"] += record["a"] is not None
    coverage["generated"] = {split: len(records[split]) for split in SPLITS}
    coverage["unique_original_opportunities_retained"] = len(used_original_ids)
    return records, coverage


def audit_suite(suite: dict) -> dict:
    """Fail on split leakage; return compact, inspectable split receipts."""
    instance_owner, graph_owner, seed_owner, original_owner = {}, {}, {}, {}
    target_configurations = {split: set() for split in SPLITS}
    results = {}
    record_ids = set()
    for split in SPLITS:
        families = {}
        for record in suite[split]:
            if record["id"] in record_ids:
                raise ValueError("Duplicate record ID")
            record_ids.add(record["id"])
            source = record["source"]
            if source["split"] != split:
                raise ValueError("Record has incorrect split provenance")
            families[record["family"]] = families.get(record["family"], 0) + 1
            fingerprint = source["instance_fingerprint"]
            if fingerprint in instance_owner:
                raise ValueError("Duplicate physical instance across generated records")
            instance_owner[fingerprint] = split
            seed = source.get("seed")
            if seed is not None:
                if seed in seed_owner:
                    raise ValueError("Duplicate synthetic seed")
                seed_owner[seed] = split
            for side in ("left", "right"):
                graph = record[side]
                graph_fingerprint = graph.digest()
                if graph_fingerprint in graph_owner:
                    raise ValueError("Duplicate scheduling graph across generated records")
                graph_owner[graph_fingerprint] = split
                graph.available(record["fixed"], record["excluded"])
            for original_id in source.get("original_ids", ()):
                if original_id in original_owner:
                    raise ValueError("Duplicate C3 original opportunity across windows/splits")
                original_owner[original_id] = split
            right_constraints = record["right"].constraints
            target_configurations[split].add(json.dumps(right_constraints, sort_keys=True))
        seeds = sorted(seed for seed, owner in seed_owner.items() if owner == split)
        results[split] = {"records": len(suite[split]), "families": families,
                          "seed_min": seeds[0] if seeds else None, "seed_max": seeds[-1] if seeds else None,
                          "target_configurations": [json.loads(value) for value in sorted(target_configurations[split])]}
    for i, split in enumerate(SPLITS):
        for other in SPLITS[i + 1:]:
            if target_configurations[split] & target_configurations[other]:
                raise ValueError("An intervention target configuration leaked across splits")
    return {"passed": True, "unique_instance_fingerprints": len(instance_owner),
            "unique_graph_fingerprints": len(graph_owner), "unique_synthetic_seeds": len(seed_owner),
            "unique_c3_opportunities": len(original_owner), "splits": results,
            "target_configurations_disjoint": True,
            "c3_shared_reference_configuration": {"ground_trans_time": 340, "satellite_change_time": 150,
                                                    "satellite_trans_time": 300}}


def make_suite(config: dict | None = None) -> dict:
    """Return Graph-valued static pair records and an explicit data protocol.

    ``counts`` maps diagnostic/random_temporal/c3 to a count per split or a
    ``{"train": ..., "validation": ..., "test": ...}`` mapping.  Missing split
    keys in an explicit mapping request zero records.  Unavailable C3 sources
    yield empty C3 lists with a reason; no synthetic replacement is generated.
    """
    config = dict(config or {})
    suite = {split: [] for split in SPLITS}
    counts = {family: {split: _count(config, family, split) for split in SPLITS}
              for family in DEFAULT_COUNTS}
    for split in SPLITS:
        suite[split].extend(diagnostic_pair(split, i) for i in range(counts["diagnostic"][split]))
        suite[split].extend(_random_pair(split, i) for i in range(counts["random_temporal"][split]))
    c3, coverage = _c3_records(config, counts["c3"])
    for split in SPLITS:
        suite[split].extend(c3[split])
    suite["protocol"] = {
        "version": "static_constraint_adaptation_data_v1", "outcome_filtering": False,
        "oracle_calls_during_generation": 0, "online_constraint_changes": False,
        "intervention_scope": "paired_static_problems_with_identical_contacts",
        "counts_requested": counts,
        "diagnostic_scope": "designed_mechanism_probes_not_natural_population_statistics",
        "synthetic_model": "synthetic_single_capacity_temporal",
        "c3_model": "frozen_v51_legacy_conflict_predicates",
        "c3_scope": "resource_time_window_subproblems_not_full_dataset_schedules",
        "seed_bases": {"diagnostic": _DIAGNOSTIC_SEED_BASE, "random_temporal": _RANDOM_SEED_BASE},
        "c3_split_rule": "link_start_day_0_train_day_1_validation_day_2_test",
        "configuration_split_rule": "disjoint_intervention_targets_shared_c3_reference_340_allowed",
    }
    suite["coverage"] = {"c3": coverage}
    suite["audit"] = audit_suite(suite)
    return suite
