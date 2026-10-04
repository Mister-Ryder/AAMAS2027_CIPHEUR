"""Independent V06 TRAIN source/query/certificate verification, with no TEST solve.

Only older independent graph/exact-recurrence helpers are imported. Original
oracle and scheduling modules are never imported or called. Frozen TEST input
inventory is reconstructed, but no conditional optimum or programme is
evaluated on any TEST state. Verification is not evidence collection/tuning.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_public_alias_v05 import (
    read_members, view, graph_digest, base9, exact_vector, components,
    exact_alpha, VerificationLimit,
)

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments/discovery/v06_evidence_001"
SERVER = ROOT / "experiments/discovery/v06_evidence_server_001"
ARCHIVE = ROOT / "experiments/runs/v06/v06_evidence_train_001.tar.gz"
CAPSULE = ROOT / "experiments/source_snapshots/v06/v06_evidence_train_001_source.zip"
PINS = {
    "archive": "3f6986a6b803761c503876d4b3d1419c7f1fe3adab3acc5929dcb4c6db2c7a48",
    "source": "74c1854536206fe098cbad86cd3a5c400dda279ecbff49c76cf3d80b2e075380",
    "data": "968f96b7712ca3ecc8a7b43f567c6b6403742f26f0e76e9d5f2c680973827784",
    "protocol": "32e008c2d348df53813696f8bfc413829704a9e76c07e4d03ac036387cb11854",
    "freeze": "00e67514c70d76547991fa3c9908b85c954d48e35a4dab605dcf0876234a87c5",
    "budget": "16834240d6136cf54cf208e3f03b24f7d0505f72b9cc898df8bf1ac31f4b19d2",
}


def digest(raw):
    return sha256(raw).hexdigest()


def obj(raw):
    return json.loads(raw)


def ordering(salt, text):
    return sha256((salt + "|" + text).encode()).digest()


def frozen_queries(graphs, identity, salt):
    """Independent all-nine exact alias and common-edge query ordering."""
    views = [view(g) for g in graphs]
    common = set.intersection(*(set(edges) for _, edges, _ in views))
    vectors = [{v: base9(g, nodes, adj, v) for v in nodes}
               for g, (nodes, _, adj) in zip(graphs, views)]
    groups = {"alias": [], "control": []}
    for a, b in sorted(common, key=lambda e: ordering(salt, identity + "|" + "|".join(e))):
        aliases = [exact_vector(v[a]) == exact_vector(v[b]) for v in vectors]
        kind = "alias" if any(aliases) else "control"
        groups[kind].append({"a": a, "b": b, "kind": kind, "base_alias_by_side": aliases})
    queries = [q for kind in ("alias", "control") for q in groups[kind][:8]]
    quotas = {k: {"eligible": len(v), "planned": min(8, len(v)),
                  "shortfall": max(0, 8-len(v))} for k, v in groups.items()}
    return queries, quotas


def rebuild_inventory(records, protocol, require):
    """Source reconstruction/feature checks only; no TRAIN or TEST oracle here."""
    salt = protocol["salt"]
    public_path = ROOT / protocol["public_input"]
    require(digest(public_path.read_bytes()) == protocol["public_input_sha256"],
            "original_public_input_bytes", "public")
    public_raw = read_members(public_path, ("data.json",))["data.json"]
    require(digest(public_raw) == protocol["public_input_member_sha256"],
            "original_public_member_bytes", "public")
    originals = [r for r in obj(public_raw)["public"] if r["source"]["weight_mode"] == "unit"]
    require(len(originals) == len({r["cluster"] for r in originals}) == 48,
            "original_48_source_clusters", "public")
    expected, splitmap = {}, {}
    for family in ("DIMACS", "SATLIB"):
        population = sorted((r for r in originals if r["family"] == family),
                            key=lambda r: ordering(salt, "source-split|" + r["cluster"]))
        for index, original in enumerate(population):
            split = "train" if index < len(population)//2 else "test"
            splitmap[original["cluster"]] = split
            source = original["graph"]
            subset = set(sorted((c["id"] for c in source["contacts"]),
                                key=lambda v: ordering(salt, original["id"] + "|" + v))[:32])
            graph = {"name": source["name"] + "_induced32",
                     "contacts": [c for c in source["contacts"] if c["id"] in subset],
                     "edges": [e for e in source["edges"] if set(e) <= subset],
                     "constraints": source["constraints"],
                     "provenance": {"origin": "source_derived_hash_ordered_induced_graph",
                        "source_graph_digest": graph_digest(source), "source_id": original["id"],
                        "subset_salt": salt, "subset_size": 32,
                        "selected_original_vertices": sorted(subset)}}
            queries, quota = frozen_queries([graph], "public|" + original["id"], salt)
            ident = "v06_public32|" + original["id"]
            expected[ident] = {"id": ident, "split": split, "family": family,
                "cluster": original["cluster"], "paired": False, "graph": graph,
                "graph_digest": graph_digest(graph), "fixed": [], "excluded": [],
                "queries": queries, "quota": quota,
                "source": {"id": original["id"], "graph_digest": graph_digest(source),
                           "metadata": original["source"], "subset_salt": salt},
                "scope": "new induced state in previously exposed public corpus"}
    require(splitmap == protocol["public_source_split"], "independent_source_family_split", "public")
    for split, count in (("train", 8), ("test", 4)):
        for regime, resources in (("balanced", (8, 6)), ("ground_scarce", (12, 3)),
                                  ("satellite_scarce", (3, 12))):
            for profile, horizon in (("short", 11), ("long", 24)):
                for index in range(count):
                    name = f"v06_unit_{split}_{regime}_{profile}_{index:03d}"
                    seed = int.from_bytes(ordering(salt, name)[:8], "big")
                    rng = random.Random(seed)
                    contacts = []
                    for i in range(32):
                        start = rng.randrange(horizon * 4) / 4
                        contacts.append({"id": f"v{i:03d}", "weight": 1,
                            "satellite": f"S{rng.randrange(resources[0])}",
                            "station": f"G{rng.randrange(resources[1])}",
                            "start": start, "end": start + 1, "task": ""})
                    gaps = (0, 1) if split == "train" else (.25, 2)
                    graphs = []
                    for side, gap in zip(("left", "right"), gaps):
                        edges = []
                        for i, a in enumerate(contacts):
                            for b in contacts[i+1:]:
                                first, second = sorted((a, b), key=lambda c: (c["start"], c["id"]))
                                if (a["station"] == b["station"] and second["start"] < first["end"] + gap
                                        or a["satellite"] == b["satellite"] and second["start"] < first["end"]):
                                    edges.append(sorted((a["id"], b["id"])))
                        graphs.append({"name": name + "_" + side, "contacts": contacts,
                            "edges": sorted(edges), "constraints": {"station_gap": gap,
                                "satellite_gap": 0, "model": "synthetic_single_capacity_temporal"},
                            "provenance": {}})
                    queries, quota = frozen_queries(graphs, name, salt)
                    for side, graph in zip(("left", "right"), graphs):
                        ident = name + ":" + side
                        expected[ident] = {"id": ident, "pair": name, "side": side,
                            "split": split, "family": "temporal_unit_" + regime + "_" + profile,
                            "cluster": name, "paired": True, "graph": graph,
                            "graph_digest": graph_digest(graph), "fixed": [], "excluded": [],
                            "queries": queries, "quota": quota,
                            "source": {"seed": seed, "station_gaps": list(gaps),
                                       "outcome_filtering": False, "unit_duration_reward": True},
                            "scope": "synthetic single-capacity physical pairwise model; not C3"}
    require(set(expected) == {r["id"] for r in records} and len(records) == len(expected) == 192,
            "all_192_source_derived_input_ids", "inputs")
    for r in records:
        require(r == expected[r["id"]], "independent_source_graph_base9_query_quota_reconstruction", r["id"])
    train = [r for r in records if r["split"] == "train"]
    test = [r for r in records if r["split"] == "test"]
    require(len(train) == 120 and len(test) == 72 and len({r["graph_digest"] for r in records}) == 192
            and not {r["graph_digest"] for r in train} & {r["graph_digest"] for r in test},
            "registered_split_counts_and_graph_digest_nonoverlap", "inputs")
    require(not {r["cluster"] for r in train} & {r["cluster"] for r in test},
            "source_cluster_nonoverlap", "inputs")
    return train, test


def audit(output, max_states=1000000):
    started = time.perf_counter()
    checks, errors = Counter(), []
    def require(ok, kind, where):
        checks[kind] += 1
        if not ok:
            errors.append({"kind": kind, "where": where})

    require(digest(ARCHIVE.read_bytes()) == PINS["archive"], "raw_archive_pin", "archive")
    require(digest(CAPSULE.read_bytes()) == PINS["source"], "source_capsule_pin", "capsule")
    names = ("data.json", "protocol.json", "freeze_receipt.json", "BUDGET_SCOPE.json",
             "results.jsonl", "complete.json", "execution.json", "execution_plan.json",
             "capsule_receipt.json", "execution_budget_receipt.json", "execution_host_receipt.json",
             "query_launch_receipt.json")
    raw = read_members(ARCHIVE, names)
    freeze, protocol, data = (obj(raw[n]) for n in ("freeze_receipt.json", "protocol.json", "data.json"))
    for name, pin in (("data.json", "data"), ("protocol.json", "protocol"),
                      ("freeze_receipt.json", "freeze"), ("BUDGET_SCOPE.json", "budget")):
        require(digest(raw[name]) == PINS[pin] and raw[name] == (STUDY / name).read_bytes(),
                "frozen_input_bytes", name)
    require(freeze["data_sha256"] == PINS["data"] and freeze["protocol_sha256"] == PINS["protocol"]
            and freeze["before_any_oracle_query"] and protocol["before_any_oracle_query"]
            and protocol["data_generation_outcome_queries"] == 0
            and protocol["prior_public_corpus_exposed"] and protocol["physical_source_claim"] is False,
            "honest_prequery_provenance", "freeze")
    require(data["protocol"] == protocol, "embedded_protocol_identity", "data")
    receipt = obj(raw["capsule_receipt.json"])
    require(receipt["registered_before_any_query"] and receipt["query_split"] == "train"
            and receipt["source_zip_sha256"] == PINS["source"]
            and receipt["budget_scope_sha256"] == PINS["budget"],
            "capsule_prequery_split_binding", "capsule")
    with zipfile.ZipFile(CAPSULE) as z:
        require(set(z.namelist()) == set(receipt["files_sha256"]), "capsule_full_member_inventory", "capsule")
        for name, expected in receipt["files_sha256"].items():
            require(digest(z.read(name)) == expected == digest((ROOT / name).read_bytes()),
                    "frozen_source_current_and_capsule_identity", name)
        for name, expected in freeze["source_sha256"].items():
            require(digest(z.read("cipheur/" + name)) == expected, "original_semantic_source_pin", name)
        source_ast = ast.parse(z.read("cipheur/evidence_study_v06.py"))
        run = next(n for n in source_ast.body if isinstance(n, ast.FunctionDef) and n.name == "run_state")
        constructor = [n for n in ast.walk(run) if isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Name) and n.func.id == "CancelledCompletionOracle"]
        require(len(constructor) == 1 and any(k.arg is None and isinstance(k.value, ast.Name)
                and k.value.id == "ORACLE" for k in constructor[0].keywords),
                "new_oracle_constructor_per_state_source_scope", "run_state")
        original = ast.parse(z.read("cipheur/relevance_synthesis_v04.py"))
        cls = next(n for n in original.body if isinstance(n, ast.ClassDef) and n.name == "CancelledCompletionOracle")
        diff = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "difference")
        epsilon = diff.args.defaults[-1].value
        require(epsilon == 1e-8, "executed_epsilon_from_frozen_source", "difference")
    budget = obj(raw["BUDGET_SCOPE.json"])
    require(budget["original_freeze_sha256"] == PINS["freeze"] and budget["before_any_oracle_query"]
            and budget["new_oracle_instance_per_state"] and budget["global_call_cap"] is None
            and budget["max_calls"] == 1024 and budget["max_expanded_nodes"] == 2000000
            and budget["per_unmatched_component_expanded_limit"] == 50000
            and budget["per_component_vertex_search_cutoff"] == 32
            and budget["cancelled_identical_components_do_not_consume_solver_calls"],
            "append_only_per_state_budget_scope", "budget")
    require(protocol["oracle"] == {"nodes_per_component": 50000, "max_search_component": 32,
                                    "max_nodes": 2000000, "max_calls": 1024},
            "registered_oracle_limits", "protocol")
    plan, execution, complete = (obj(raw[n]) for n in ("execution_plan.json", "execution.json", "complete.json"))
    append, host, launch = (obj(raw[n]) for n in
                           ("execution_budget_receipt.json", "execution_host_receipt.json", "query_launch_receipt.json"))
    require(plan["split"] == execution["split"] == complete["split"] == append["split"] == "train"
            and plan["test_queries_permitted"] is False and host["test_queries_permitted"] is False
            and append["test_queries_run"] == 0 and execution["programme_freeze_sha256"] is None,
            "TRAIN_only_no_TEST_query_or_programme_evaluation", "execution")
    require(plan["original_source_sha256"] == execution["source_sha256"] == freeze["source_sha256"]
            and plan["prior_plan_freeze_sha256"] == PINS["freeze"]
            and receipt["execution_plan_sha256"] == digest(raw["execution_plan.json"]),
            "executed_source_original_freeze_binding", "execution")
    require(append["append_only"] and append["budget_scope_sha256"] == PINS["budget"]
            and append["source_zip_sha256"] == PINS["source"] and append["exit_code"] == 0
            and append["whole_run_guard_triggered"] is False and append["query_retries"] == 0
            and append["original_execution_sha256"] == digest(raw["execution.json"])
            and append["original_complete_sha256"] == digest(raw["complete.json"])
            and append["execution_host_receipt_sha256"] == digest(raw["execution_host_receipt.json"]),
            "append_only_original_results_and_no_retry_binding", "execution")
    require(launch["execution_host_receipt_sha256"] == digest(raw["execution_host_receipt.json"])
            and launch["split"] == "train" and launch["timestamp_unix"] >= host["timestamp_unix"]
            and host["before_any_oracle_query"] and host["source_zip_sha256"] == PINS["source"]
            and host["budget_scope_sha256"] == PINS["budget"]
            and host["execution_plan_sha256"] == digest(raw["execution_plan.json"])
            and launch["workers"] == host["workers"] == plan["workers"] == execution["workers"] == 8,
            "prequery_host_launch_and_workers_binding", "host")

    train, test = rebuild_inventory(data["records"], protocol, require)
    results = [obj(line) for line in raw["results.jsonl"].splitlines() if line]
    require(len(results) == len({r["id"] for r in results}) == 120
            and {r["id"] for r in results} == {r["id"] for r in train},
            "all_TRAIN_states_and_TEST_absence", "results")
    by_id = {r["id"]: r for r in results}
    exact_cache, exact_states, unverified = {}, 0, []
    counts, summaries, paired = Counter(), defaultdict(Counter), defaultdict(dict)
    strict_details = []
    def optimum(identity, nodes, adj, part):
        nonlocal exact_states
        key = identity, tuple(sorted(part))
        if key not in exact_cache:
            try:
                value, spent = exact_alpha(nodes, adj, key[1], max_states)
                exact_cache[key] = value
                exact_states += spent
            except VerificationLimit:
                exact_cache[key] = None
                unverified.append({"state": identity, "component": list(key[1])})
        return exact_cache[key]

    for index, record in enumerate(sorted(train, key=lambda r: r["id"])):
        ident, result = record["id"], by_id[record["id"]]
        graph = record["graph"]
        nodes, edges, adj = view(graph)
        require(len(nodes) <= 32 and all(c["weight"] == 1 for c in nodes.values())
                and record["fixed"] == record["excluded"] == [], "small_unit_empty_boundary", ident)
        require(result["graph_digest"] == record["graph_digest"] == graph_digest(graph)
                and result["split"] == "train" and result["family"] == record["family"]
                and result["cluster"] == record["cluster"] and result["quota"] == record["quota"],
                "result_original_state_quota_identity", ident)
        require(len(result["rows"]) == len(record["queries"]), "all_prescheduled_queries_retained", ident)
        meter = result["oracle_budget"]
        require(0 <= meter["calls"] <= 1024 and 0 <= meter["expanded_nodes"] <= 2000000
                and meter["max_nodes"] == 2000000 and meter["max_calls"] == 1024,
                "executed_state_budget_receipt", ident)
        for field in ("elapsed_seconds", "solve_elapsed_seconds"):
            require(math.isfinite(meter[field]) and meter[field] >= 0,
                    "recorded_nonnegative_oracle_time", ident + ":" + field)
        unique_bounds = {}
        for qindex, (query, row) in enumerate(zip(record["queries"], result["rows"])):
            where = ident + ":" + str(qindex)
            a, b, difference = query["a"], query["b"], row["difference"]
            require(all(row[k] == query[k] for k in query) and (a, b) in edges
                    and a != b and difference["a"] == a and difference["b"] == b,
                    "frozen_competing_feasible_query_payload", where)
            alias = exact_vector(base9(graph, nodes, adj, a)) == exact_vector(base9(graph, nodes, adj, b))
            side_index = 0 if not record["paired"] or record["side"] == "left" else 1
            require(alias == query["base_alias_by_side"][side_index]
                    and query["kind"] == ("alias" if any(query["base_alias_by_side"]) else "control"),
                    "independent_per_side_alias_semantics", where)
            pa, pb = components(adj, nodes.keys() - adj[a] - {a}), components(adj, nodes.keys() - adj[b] - {b})
            require(set(map(tuple, difference["cancelled_components"])) == pa & pb,
                    "exact_common_component_cancellation", where)
            partitions, side_bounds = {"a": pa-pb, "b": pb-pa}, {}
            for side in ("a", "b"):
                exported = difference["unmatched"][side]
                require(len(exported) == len(partitions[side])
                        and set(tuple(p["vertices"]) for p in exported) == partitions[side],
                        "complete_unmatched_component_partition", where + side)
                for component in exported:
                    part, bound = tuple(component["vertices"]), component["bound"]
                    lo, hi = Fraction(bound["lower_exact"]), Fraction(bound["upper_exact"])
                    chosen = bound["selected"]
                    require(len(chosen) == len(set(chosen)) and set(chosen) <= set(part)
                            and not any(adj[v] & set(chosen) for v in chosen),
                            "component_lower_witness_feasibility", where)
                    require(sum((Fraction(nodes[v]["weight"]) for v in chosen), Fraction()) == lo
                            and 0 <= lo <= hi <= len(part) and bound["exact"] == (lo == hi),
                            "component_exact_reward_interval_flag", where)
                    value = optimum(ident, nodes, adj, part)
                    require(value is not None and lo <= value <= hi,
                            "independent_component_optimum_enclosed", where)
                    require(0 <= bound["expanded"] <= 50000, "per_component_expansion_ceiling", where)
                    if part in unique_bounds:
                        require(bound == unique_bounds[part], "within_state_bound_cache_identity", where)
                    unique_bounds[part] = bound
                    side_bounds[side, part] = lo, hi
            forced = Fraction(nodes[a]["weight"]) - Fraction(nodes[b]["weight"])
            lower = forced + sum((side_bounds["a", p][0] for p in partitions["a"]), Fraction())
            lower -= sum((side_bounds["b", p][1] for p in partitions["b"]), Fraction())
            upper = forced + sum((side_bounds["a", p][1] for p in partitions["a"]), Fraction())
            upper -= sum((side_bounds["b", p][0] for p in partitions["b"]), Fraction())
            require(lower == Fraction(difference["lower_exact"]) and upper == Fraction(difference["upper_exact"])
                    and difference["forced_weight_difference_exact"] == str(forced),
                    "exact_cancelled_signed_interval_arithmetic", where)
            require(Fraction(difference["lower"]) <= lower <= upper <= Fraction(difference["upper"])
                    and difference["exact"] == (lower == upper),
                    "outward_float_enclosure_and_exact_flag", where)
            full_a = [optimum(ident, nodes, adj, p) for p in pa]
            full_b = [optimum(ident, nodes, adj, p) for p in pb]
            if all(v is not None for v in full_a + full_b):
                truth = forced + sum(full_a, Fraction()) - sum(full_b, Fraction())
                require(lower <= truth <= upper, "independent_full_conditional_value_difference", where)
            else:
                truth = None
                require(False, "independent_full_conditional_unverified", where)
            preferred = a if lower > Fraction(epsilon) else b if upper < -Fraction(epsilon) else None
            status = "strict" if preferred is not None else "exact_tie" if lower == upper == 0 else "unknown"
            require(difference["preferred"] == preferred and difference["status"] == status,
                    "independent_strict_tie_unknown_sign", where)
            if preferred:
                require(truth is not None and (truth > 0 if preferred == a else truth < 0),
                        "strict_label_independent_truth_sign", where)
                strict_details.append({"id": ident, "a": a, "b": b, "kind": query["kind"],
                    "preferred": preferred, "delta_exact": str(truth), "per_side_alias": alias,
                    "family": record["family"], "cluster": record["cluster"]})
            if status == "exact_tie":
                require(truth == 0, "exact_tie_independent_truth", where)
            counts[status] += 1
            summaries[record["family"]][status] += 1
            summaries[record["family"]][query["kind"] + "_queries"] += 1
            summaries[record["family"]]["actual_side_alias_queries"] += alias
            summaries[record["family"]]["strict_actual_side_alias"] += alias and status == "strict"
            counts["actual_side_alias_queries"] += alias
            counts["strict_actual_side_alias"] += alias and status == "strict"
            if record["paired"]:
                paired[record["pair"]][record["side"], a, b] = {
                    "status": status, "preferred": preferred, "delta_exact": str(truth), "alias": alias}
        calls = sum(v["reason"] != "call_budget_trivial_interval" for v in unique_bounds.values())
        require(meter["cache_components"] == len(unique_bounds) and meter["calls"] == calls
                and meter["expanded_nodes"] == sum(v["expanded"] for v in unique_bounds.values()),
                "unique_component_call_and_expansion_accounting", ident)
        if index % 40 == 39:
            print(json.dumps({"checked_TRAIN_states": index+1, "errors_so_far": len(errors)}), flush=True)

    relations, pair_details = Counter(), []
    for pair, values in sorted(paired.items()):
        keys = sorted({(a, b) for side, a, b in values})
        for a, b in keys:
            left, right = values["left", a, b], values["right", a, b]
            if left["status"] == right["status"] == "strict":
                kind = "strict_preservation" if left["preferred"] == right["preferred"] else "strict_reversal"
            elif left["status"] == right["status"] == "exact_tie":
                kind = "tie_on_both_sides"
            elif "unknown" in (left["status"], right["status"]):
                kind = "unknown_endpoint"
            else:
                kind = "tie_to_strict" if left["status"] == "exact_tie" else "strict_to_tie"
            relations[kind] += 1
            pair_details.append({"pair": pair, "a": a, "b": b, "classification": kind,
                                 "left": left, "right": right})
    status_counts = {k: counts[k] for k in ("strict", "exact_tie", "unknown") if counts[k]}
    shortfall = sum(q["shortfall"] for r in train for q in r["quota"].values())
    require(complete["execution_complete"] and complete["states"] == 120
            and complete["query_status"] == status_counts and complete["query_shortfalls"] == shortfall
            and complete["results_sha256"] == digest(raw["results.jsonl"])
            and complete["unknowns_retained"] and complete["programme_freeze_sha256"] is None,
            "independent_complete_counts_and_result_binding", "complete")
    require(sum(len(r["queries"]) for r in train) == plan["train_queries"] == 1503
            and plan["train_states"] == 120 and sum(status_counts.values()) == 1503
            and plan["train_query_kind"] == dict(Counter(q["kind"] for r in train for q in r["queries"])),
            "all_1503_frozen_query_slots", "complete")
    require(not unverified, "all_component_verifications_complete", "independent")
    report = {"version": "v06_TRAIN_evidence_independent_audit_001", "archive_sha256": PINS["archive"],
        "source_zip_sha256": PINS["source"], "data_sha256": PINS["data"], "protocol_sha256": PINS["protocol"],
        "freeze_receipt_sha256": PINS["freeze"], "budget_scope_sha256": PINS["budget"],
        "execution_host_receipt_sha256": digest(raw["execution_host_receipt.json"]),
        "execution_budget_receipt_sha256": digest(raw["execution_budget_receipt.json"]),
        "audit_script_sha256": digest(Path(__file__).read_bytes()),
        "independent_helper_sha256": digest((ROOT / "scripts/verify_public_alias_v05.py").read_bytes()),
        "checks": dict(checks), "errors": errors, "status_counts": status_counts,
        "TRAIN_states": 120, "TRAIN_queries": 1503, "TEST_conditional_queries_or_programme_evaluations": 0,
        "unavailable_quota_slots": shortfall, "per_side_alias_counts": dict(counts),
        "family_summary": {k: dict(v) for k, v in summaries.items()},
        "paired_query_classifications": dict(relations), "paired_details": pair_details,
        "strict_details": strict_details, "independent_exact_components": len(exact_cache),
        "independent_exact_recurrence_states": exact_states, "unverified_components": unverified,
        "independent_per_component_state_ceiling": max_states,
        "elapsed_wall_seconds": time.perf_counter()-started,
        "scope": ["TRAIN-only certificate verification; no TEST conditional optimization, programme evaluation or authoring.",
                  "Exact source/query reconstruction for frozen TRAIN/TEST input inventory, without TEST outcomes.",
                  "All TRAIN full conditional values and exported component intervals independently checked by memoized exact recurrence.",
                  "Aliased query pool means alias on either paired side; per-side aliases and strict obstructions remain distinct.",
                  "Public new states are source-disjoint within an exposed corpus; synthetic contacts are controlled, not natural C3.",
                  "Recorded oracle/host time is not independently remeasured or attributed to model benefit."]}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"checks": sum(checks.values()), "errors": len(errors), "status": status_counts,
        "strict_side_alias": counts["strict_actual_side_alias"], "paired": dict(relations),
        "exact_components": len(exact_cache), "exact_states": exact_states}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "experiments/analysis/v06/evidence_train_audit_v06_001.json"))
    parser.add_argument("--max-independent-states", type=int, default=1000000)
    args = parser.parse_args()
    audit(args.out, args.max_independent_states)
