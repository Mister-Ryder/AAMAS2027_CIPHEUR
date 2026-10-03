"""Independent TRAIN-only archive audit; no fresh validation/test file access.

Checks saved witnesses and exact cancellation arithmetic without running the
study or importing its scheduler, compiler, oracle, or selection implementation.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import statistics
import time
import zipfile

import verify_v03_evidence as audit

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments/runs/v04/relevance_train_v04_001.tar.gz"
SOURCE = ROOT / "experiments/source_snapshots/v04/relevance_v04_source.zip"
COUNTS = Counter()
SMALL = {}
WIDTHS = []
COLLECTED = defaultdict(list)


def expression(g, active, root, e):
    """Standalone evaluation of the 13 graph operations present in this bank."""
    op = e["op"]
    a = [expression(g, active, root, x) for x in e.get("args", [])]
    if op == "root": return root
    if op == "available": return set(active)
    if op == "neighbors": return g.adj[a[0]] & active
    if op == "singleton": return {a[0]} & active
    if op == "union": return a[0] | a[1]
    if op == "difference": return a[0] - a[1]
    if op == "induced_edges": return {(u, v) for u, v in g.edges if u in a[0] and v in a[0]}
    if op == "count": return len(a[0])
    if op == "max_weight": return max((g.contacts[v]["weight"] for v in a[0]), default=0.0)
    if op in ("edge_min_weight_sum", "edge_weight_product_sum"):
        return math.fsum(min(g.contacts[u]["weight"], g.contacts[v]["weight"]) if op == "edge_min_weight_sum" else g.contacts[u]["weight"] * g.contacts[v]["weight"] for u, v in sorted(a[0]))
    if op in ("clique_cover_weight", "greedy_independent_weight"):
        order = sorted(a[0], key=lambda v: (-g.weights[v], v))
        remaining, terms = set(a[0]), []
        for v in order:
            if v not in remaining: continue
            if op == "greedy_independent_weight":
                terms.append(g.contacts[v]["weight"])
                remaining.difference_update(g.adj[v] | {v})
            else:
                group = [v]
                remaining.remove(v)
                for u in order:
                    if u in remaining and all(u in g.adj[q] for q in group):
                        group.append(u)
                        remaining.remove(u)
                terms.append(max(g.contacts[q]["weight"] for q in group))
        return math.fsum(terms)
    raise ValueError("Unaudited graph operation: " + op)


def diagnose(vectors, requirements):
    nodes, edges, loops = set(vectors.values()), set(), 0
    for r in requirements:
        a, b = vectors[r["preferred"]], vectors[r["other"]]
        edges.add((a, b)); loops += a == b
    adj, indegree = defaultdict(set), {v: 0 for v in nodes}
    for a, b in edges:
        adj[a].add(b); indegree[b] += 1
    pending, visited = [v for v in nodes if indegree[v] == 0], 0
    while pending:
        v = pending.pop(); visited += 1
        for u in adj[v]:
            indegree[u] -= 1
            if indegree[u] == 0: pending.append(u)
    return {"contradictory": visited != len(nodes), "quotient_nodes": len(nodes), "quotient_edges": len(edges), "self_loop_requirements": loops}


def information_replay(contexts, bank, information, seeds, known):
    endpoints, requirements = {}, []
    def append(g, fixed, excluded, preferred, other, metadata):
        prefix = canonical([g.digest, sorted(fixed), sorted(excluded)])
        for v in (preferred, other):
            endpoints[prefix + ":" + v] = g, fixed, excluded, v
        requirements.append({"preferred": prefix + ":" + preferred, "other": prefix + ":" + other, "metadata": metadata})
    for c in sorted(contexts, key=lambda c: (c["pair_id"], c["side"])):
        g = audit.GraphView(c["graph"])
        for state in c["states"]:
            for d in state["differences"]:
                if d["preferred"] is not None:
                    other = d["b"] if d["preferred"] == d["a"] else d["a"]
                    append(g, state["fixed"], state["excluded"], d["preferred"], other, {"kind":"cancelled_actual_action", "pair_id":c["pair_id"], "side":c["side"]})
    for spec in seeds:
        audit.certificate(spec, "v04_prior_seed/" + spec["id"])
        for side in ("left", "right"):
            g = audit.GraphView(spec[side])
            audit.require(g.digest in known, "training_prior_evidence_source_split", spec["id"], "seed graph outside original train")
            preferred = spec[side + "_preferred"]
            other = spec["b"] if preferred == spec["a"] else spec["a"]
            append(g, spec["fixed"], spec["excluded"], preferred, other, {"kind":"prior_training_certificate", "id":spec["id"], "side":side})
    audit.require(requirements == information["requirements"] and len(endpoints) == information["occurrences"], "training_information_population_replay", "information", "requirements/endpoints mismatch")
    base = {oid: audit.base_vector(g, v, f, x) for oid, (g, f, x, v) in endpoints.items()}
    diagnosis = diagnose(base, requirements)
    for k, v in diagnosis.items():
        audit.require(information["base_quotient"][k] == v, "training_base_quotient_replay", k, "diagnosis mismatch")
    for entry in bank:
        features = entry["program"]["features"]
        vectors = {}
        for oid, (g, f, x, v) in endpoints.items():
            values = dict(base[oid])
            values.update({feature["name"]: expression(g, g.available(f, x), v, feature["expression"]) for feature in features})
            vectors[oid] = tuple(sorted(values.items()))
        actual = diagnose(vectors, requirements)
        for k, v in actual.items():
            audit.require(information["candidate_quotients"][entry["id"]][k] == v, "training_candidate_full_quotient_replay", entry["id"] + "/" + k, "diagnosis mismatch")
    actual = [r for r in requirements if r["metadata"]["kind"] == "cancelled_actual_action"]
    actual_ids = {r[k] for r in actual for k in ("preferred","other")}
    actual_diagnosis = diagnose({k:v for k,v in base.items() if k in actual_ids},actual)
    loop_kinds = Counter(r["metadata"]["kind"] for r in requirements if base[r["preferred"]] == base[r["other"]])
    return {"requirements":len(requirements), "endpoints":len(endpoints), "base":diagnosis, "actual_action_requirements":len(actual), "actual_action_base_quotient":actual_diagnosis,"self_loop_requirement_kinds":dict(loop_kinds), "all_93_candidate_quotients_recomputed":True}


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def partition(g, active):
    remaining, parts = set(active), []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        part, queue = {seed}, [seed]
        while queue:
            neighbors = g.adj[queue.pop()] & remaining
            remaining.difference_update(neighbors)
            part.update(neighbors)
            queue.extend(neighbors)
        parts.append(tuple(sorted(part)))
    return set(parts)


def optimum(g, vertices):
    key = g.digest, tuple(vertices)
    if key not in SMALL:
        nodes = tuple(vertices)
        adjacency = [sum(1 << j for j, v in enumerate(nodes) if v in g.adj[u]) for u in nodes]
        @lru_cache(None)
        def search(mask):
            if not mask:
                return Fraction(0)
            bit = mask & -mask
            i = bit.bit_length() - 1
            without = mask ^ bit
            return max(search(without), g.weights[nodes[i]] + search(without & ~adjacency[i]))
        SMALL[key] = search((1 << len(nodes)) - 1)
    return SMALL[key]


def component(g, row, where):
    vertices, b = tuple(row["vertices"]), row["bound"]
    lo, hi = Fraction(b["lower_exact"]), Fraction(b["upper_exact"])
    audit.require(len(vertices) == len(set(vertices)) and set(vertices) <= g.contacts.keys(), "component_vertices", where, "invalid vertices")
    audit.require(g.feasible(b["selected"]) and set(b["selected"]) <= set(vertices), "component_lower_witness", where, "infeasible/foreign witness")
    audit.require(g.value(b["selected"]) == lo, "component_exact_witness_value", where, "lower differs from witness")
    audit.require(lo <= hi <= sum((g.weights[v] for v in vertices), Fraction(0)), "component_interval_order", where, "invalid upper/order")
    audit.require(b["exact"] == (lo == hi), "component_exact_flag", where, "flag mismatch")
    if len(vertices) <= 12:
        exact = optimum(g, vertices)
        audit.require(lo <= exact <= hi, "component_small_bruteforce_interval", where, "optimum outside saved interval")
        COUNTS["small_component_rows"] += 1
    else:
        COUNTS["large_component_computational_receipts"] += 1
    return lo, hi


def zero_component(g, vertices):
    """Cheap rational witnesses: weight-greedy lower and disjoint clique upper."""
    started = time.perf_counter()
    selected, remaining, cliques, operations = [], set(vertices), [], 0
    for v in sorted(vertices, key=lambda v: (-g.weights[v], v)):
        operations += len(selected)
        if not g.adj[v].intersection(selected): selected.append(v)
    order = sorted(vertices, key=lambda v: (-len(g.adj[v] & remaining), -g.weights[v], v))
    for seed in order:
        operations += 1
        if seed not in remaining: continue
        group = [seed]; remaining.remove(seed)
        for v in order:
            operations += 1
            if v not in remaining: continue
            operations += len(group)
            if all(v in g.adj[q] for q in group):
                group.append(v); remaining.remove(v)
        cliques.append(sorted(group))
    lo = g.value(selected)
    hi = sum((max(g.weights[v] for v in c) for c in cliques), Fraction(0))
    return {"vertices": list(vertices), "bound": {"lower_exact": str(lo), "upper_exact": str(hi), "selected": sorted(selected), "exact": lo == hi, "expanded": 0, "reason": "independent_zero_search_common_control"}, "clique_cover":cliques, "receipt":{"new_zero_search_calls":1, "expanded_nodes":0, "membership_check_units":operations, "wall_seconds":time.perf_counter()-started}}


def pure_cancellation(contexts, epsilon, output=None):
    rows, witnesses = [], []
    for c in contexts:
        g = audit.GraphView(c["graph"])
        for state in c["states"]:
            cache, origins = {}, {}
            for matched in state["matched_full_residual"]:
                for side in ("a", "b"):
                    for part in matched["cancelled_zero_node"]["unmatched"][side]:
                        key = tuple(part["vertices"])
                        if key in cache:
                            audit.require(cache[key]["bound"] == part["bound"], "pure_cancel_cached_same_zero_bounds", state["id"], "same component has different zero-search intervals")
                        cache[key], origins[key] = part, "saved_unmatched_zero_search"
            for matched in state["matched_full_residual"]:
                d = matched["cancelled_zero_node"]
                clo, chi = Fraction(d["lower_exact"]), Fraction(d["upper_exact"])
                common_width, removed_vertices, reused, new_calls = Fraction(0), 0, 0, 0
                for part in d["cancelled_components"]:
                    key = tuple(part)
                    if key not in cache:
                        cache[key] = zero_component(g, key)
                        origins[key] = "new_independent_zero_search_common"
                        new_calls += 1
                        witness = {"pair_id":c["pair_id"], "side":c["side"], "state_id":state["id"], **cache[key]}
                        witnesses.append(witness)
                        audit.require({v for clique in witness["clique_cover"] for v in clique} == set(key) and sum(map(len,witness["clique_cover"])) == len(key), "pure_cancel_common_clique_partition", state["id"], "cover invalid")
                        audit.require(all(all(v in g.adj[u] for i,u in enumerate(clique) for v in clique[i+1:]) for clique in witness["clique_cover"]), "pure_cancel_common_clique_edges", state["id"], "non-clique")
                    else:
                        reused += 1
                    lo, hi = component(g, cache[key], state["id"] + "/pure-common")
                    common_width += hi-lo; removed_vertices += len(key)
                ulo, uhi = clo-common_width, chi+common_width
                audit.require(ulo <= clo <= chi <= uhi and chi-clo <= uhi-ulo, "pure_cancellation_interval_containment", state["id"], "cancelled interval not contained")
                strict = lambda lo, hi: lo > epsilon or hi < -epsilon
                rows.append({"pair_id":c["pair_id"], "side":c["side"], "family":c["family"], "state_id":state["id"], "a":d["a"], "b":d["b"], "cancelled_lower_exact":str(clo), "cancelled_upper_exact":str(chi), "uncancelled_same_bounds_lower_exact":str(ulo), "uncancelled_same_bounds_upper_exact":str(uhi), "common_uncertainty_exact":str(common_width), "cancelled_strict":strict(clo,chi), "uncancelled_strict":strict(ulo,uhi), "removed_components":len(d["cancelled_components"]), "removed_vertices":removed_vertices, "reused_component_bounds":reused, "new_zero_search_calls":new_calls, "unmatched_bounds_reoptimized":False})
    summary = {"comparisons":len(rows), "distinct_comparisons":len({(r["state_id"],r["a"],r["b"]) for r in rows}), "uncancelled_strict":sum(r["uncancelled_strict"] for r in rows), "cancelled_strict":sum(r["cancelled_strict"] for r in rows), "strict_gains":sum(r["cancelled_strict"] and not r["uncancelled_strict"] for r in rows), "strict_losses":sum(r["uncancelled_strict"] and not r["cancelled_strict"] for r in rows), "cancelled_unresolved":sum(not r["cancelled_strict"] and r["cancelled_lower_exact"] != r["cancelled_upper_exact"] for r in rows), "width_reductions":sum(Fraction(r["common_uncertainty_exact"]) > 0 for r in rows), "removed_component_occurrences":sum(r["removed_components"] for r in rows), "removed_vertex_occurrences":sum(r["removed_vertices"] for r in rows), "new_zero_search_common_calls":len(witnesses), "new_search_expanded_nodes":0, "reused_component_bound_occurrences":sum(r["reused_component_bounds"] for r in rows), "common_membership_check_units":sum(w["receipt"]["membership_check_units"] for w in witnesses), "common_wall_seconds":sum(w["receipt"]["wall_seconds"] for w in witnesses), "median_cancelled_width":statistics.median(float(Fraction(r["cancelled_upper_exact"])-Fraction(r["cancelled_lower_exact"])) for r in rows), "median_uncancelled_width":statistics.median(float(Fraction(r["uncancelled_same_bounds_upper_exact"])-Fraction(r["uncancelled_same_bounds_lower_exact"])) for r in rows), "scope":"Same saved unmatched zero-search component intervals in both arms; only common-component uncertainty is removed. Additional common zero-search witnesses are offline audit costs, not deployment costs."}
    output = Path(output) if output is not None else ROOT / "experiments/analysis/v04/pure_cancellation_training.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"summary":summary,"comparisons":rows,"new_common_component_witnesses":witnesses},indent=2)+"\n")
    return summary


def delta(g, state, row, where, epsilon):
    a, b = row["a"], row["b"]
    active = g.available(state["fixed"], state["excluded"])
    audit.require(a in active and b in active and a != b, "difference_actions_feasible", where, "invalid actions")
    pa = partition(g, active - g.adj[a] - {a})
    pb = partition(g, active - g.adj[b] - {b})
    saved_common = {tuple(v) for v in row["cancelled_components"]}
    audit.require(saved_common == pa & pb, "cancelled_identical_components", where, "incorrect cancelled vertex sets")
    lower = upper = g.weights[a] - g.weights[b]
    for side, expected in (("a", pa - pb), ("b", pb - pa)):
        rows = row["unmatched"][side]
        audit.require({tuple(r["vertices"]) for r in rows} == expected and len(rows) == len(expected), "unmatched_complete_partition", where, "missing/duplicate/unmatched component")
        for r in rows:
            lo, hi = component(g, r, where)
            lower += lo if side == "a" else -hi
            upper += hi if side == "a" else -lo
    lo, hi = Fraction(row["lower_exact"]), Fraction(row["upper_exact"])
    audit.require((lo, hi) == (lower, upper), "cancelled_difference_exact_arithmetic", where, "difference endpoint mismatch")
    audit.require(Fraction(row["lower"]) <= lo and Fraction(row["upper"]) >= hi, "difference_outward_float", where, "rounded inward")
    preferred = a if lo > epsilon else b if hi < -epsilon else None
    audit.require(row["preferred"] == preferred and row["status"] == ("strict" if preferred else "exact_tie" if lo == hi == 0 else "unknown"), "difference_strict_label", where, "unsupported label")
    audit.require(row["exact"] == (lo == hi), "difference_exact_flag", where, "flag mismatch")
    COUNTS["differences"] += 1
    COUNTS["strict_differences"] += preferred is not None
    COUNTS["with_cancelled_components"] += bool(saved_common)
    return lo, hi


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=PATH)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/analysis/v04/training_audit.json")
    parser.add_argument("--pure-output", type=Path, help="Cancellation report; defaults beside --output")
    parser.add_argument("--local-cache", type=Path, help="Optional directory containing train_v04_{frozen,assessments,complete}.json")
    args = parser.parse_args(argv)
    path, source_path, output = args.archive.resolve(), args.source.resolve(), args.output.resolve()
    meta, hashes = audit.json_members(path, {"candidate_bank.json", "data.json", "config.json", "generation_receipt.json", "execution.json", "information_repair.json", "assessments.json", "frozen_programs.json", "complete.json"})
    bank, config, frozen = meta["candidate_bank.json"], meta["config.json"], meta["frozen_programs.json"]
    execution, information = meta["execution.json"], meta["information_repair.json"]
    byid = {e["id"]: e for e in bank}
    audit.require(len(bank) == len(byid) == 93, "training_bank_93_unique", "bank", str(len(bank)))
    for e in bank:
        audit.require(canonical(e["program"]) == e["program_sha256"], "candidate_program_hash", e["id"], "hash mismatch")
    audit.require(frozen["candidate_bank_sha256"] == hashes["candidate_bank.json"], "freeze_bank_bytes", "freeze", "hash mismatch")
    audit.require(frozen["config_sha256"] == hashes["config.json"], "freeze_saved_config_bytes", "freeze", "hash mismatch")
    audit.require(frozen["test_accessed"] is False and frozen["no_validation_or_test_outcome_selection"] is True and frozen["selection_split"] == config["selection_split"] == "train", "training_only_freeze", "freeze", "invalid selection provenance")
    audit.require(execution["test_outcomes_read"] is False and execution["source"]["validation_and_test_outcomes_used"] is False, "training_only_execution", "execution", "test access declaration")
    with zipfile.ZipFile(source_path) as z:
        names = set(z.namelist())
        for name, digest in execution["source_sha256"].items():
            member = "cipheur/" + name
            audit.require(member in names and sha256(z.read(member)).hexdigest() == digest, "training_source_manifest", member, "source mismatch")
        input_config = z.read("configs/relevance_v04_train.json")
        seeds = json.loads(z.read("experiments/discovery/v03/seed_specifications.json"))
        audit.require(sha256(input_config).hexdigest() == execution["config_sha256"] and json.loads(input_config) == config, "training_input_config_source", "config", "input bytes or semantics mismatch")
    pairs = {p["id"]: p for p in meta["data.json"]["train"]}
    audit.require(len(pairs) == 33, "training_data_33_pairs", "data", str(len(pairs)))
    contexts, seen = [], set()
    for member, handle, _ in audit.stream(path):
        if member != "training_contexts.jsonl":
            continue
        for line in handle:
            c = json.loads(line)
            key = c["pair_id"], c["side"]
            audit.require(key not in seen and key[0] in pairs and key[1] in ("left", "right"), "training_context_unique", str(key), "duplicate/unknown")
            seen.add(key)
            pair, g = pairs[key[0]], audit.GraphView(c["graph"])
            audit.require(g.digest == audit.GraphView(pair[key[1]]).digest, "training_context_graph_hash", str(key), "graph mismatch")
            audit.require(pair.get("split", "train") == "train" and "train" in pair["id"], "training_context_split", str(key), "non-train context")
            rows = {r["candidate_id"]: r for r in c["rows"]}
            audit.require(len(rows) == len(c["rows"]) == 93 and set(rows) == set(byid), "training_context_complete_bank", str(key), "missing/duplicate candidate")
            for cid, r in rows.items():
                where = str(key) + "/" + cid
                if r["completed"]:
                    audit.check_selection(g, r["selected"], r["value"], pair.get("fixed", []), pair.get("excluded", []), where)
                    trace = r["trace"]
                    chosen = list(pair.get("fixed", []))
                    for step in trace:
                        active = g.available(chosen, pair.get("excluded", []))
                        audit.require(step["selected"] in active and step["remaining_count"] == len(active), "training_trace_boundary", where, "invalid rollout")
                        chosen.append(step["selected"])
                    audit.require(set(chosen) == set(r["selected"]), "training_trace_saved_selection", where, "trace differs")
                    COUNTS["completed_schedules"] += 1
                else:
                    audit.require(all(r[k] is None for k in ("value", "feature_work", "selected", "trace")), "training_failure_no_fallback", where, "failed row has partial output")
                    COUNTS["failed_schedules"] += 1
            for state in c["states"]:
                where = str(key) + "/state/" + state["id"]
                audit.require(canonical([g.digest, tuple(sorted(state["fixed"])), tuple(pair.get("excluded", []))]) == state["id"], "training_state_identity", where, "hash mismatch")
                sources = {r["candidate_id"] for r in state["sources"]}
                for source in state["sources"]:
                    r, step = rows[source["candidate_id"]], source["step"]
                    reached = list(pair.get("fixed", [])) + [x["selected"] for x in r["trace"][:step]]
                    audit.require(r["completed"] and set(reached) == set(state["fixed"]), "training_state_actual_reached", where, "counterfactual source marked reached")
                choices = state["choices"]
                active = g.available(state["fixed"], state["excluded"])
                audit.require(all(a in active for a in choices.values()), "training_choice_feasibility", where, "infeasible choice")
                actions = state["actions"]
                audit.require(actions == sorted(set(choices.values())), "training_action_pool", where, "pool mismatch")
                audit.require({(d["a"], d["b"]) for d in state["differences"]} == set(itertools.combinations(actions, 2)), "training_all_action_comparisons", where, "missing comparison")
                endpoints = {}
                for d in state["differences"]:
                    endpoints[d["a"], d["b"]] = delta(g, state, d, where, Fraction(config["epsilon"]))
                for cid, regret in state["regret"].items():
                    chosen, lo, hi, unknown = choices[cid], Fraction(0), Fraction(0), 0
                    for d in state["differences"]:
                        if chosen not in (d["a"], d["b"]):
                            continue
                        l, u = endpoints[d["a"], d["b"]]
                        if chosen == d["a"]:
                            l, u = -u, -l
                        lo, hi = max(lo, l), max(hi, u)
                        unknown += d["status"] == "unknown"
                    audit.require((Fraction(regret["lower_exact"]), Fraction(regret["upper_exact"])) == (lo, hi) and regret["unknown_comparisons"] == unknown, "training_pool_regret_arithmetic", where + cid, "regret mismatch")
                    audit.require(regret["actual_reached_in_recorded_rollout"] == (cid in sources), "training_regret_reached_flag", where + cid, "counterfactual included")
                for matched in state["matched_full_residual"]:
                    zero = matched["cancelled_zero_node"]
                    clo, chi = delta(g, state, zero, where + "/zero", Fraction(config["epsilon"]))
                    flo, fhi = Fraction(matched["full_lower_exact"]), Fraction(matched["full_upper_exact"])
                    WIDTHS.append({"family": c["family"], "full_width": float(fhi-flo), "cancelled_zero_width": float(chi-clo), "full_strict": flo > Fraction(config["epsilon"]) or fhi < -Fraction(config["epsilon"]), "cancelled_zero_strict": zero["preferred"] is not None, "has_common": bool(zero["cancelled_components"])})
            best = max((r["value"] for r in rows.values() if r["completed"]), default=0)
            reference_work = max(1, rows["baseline:1"]["feature_work"] or 1)
            normalization = max(1, statistics.fmean(x["weight"] for x in c["graph"]["contacts"]))
            for cid, r in rows.items():
                regrets = [s["regret"][cid] for s in c["states"] if cid in s["regret"] and s["regret"][cid]["actual_reached_in_recorded_rollout"]]
                COLLECTED[cid].append({"family": c["family"], "quality": r["value"]/best if r["completed"] and best else 0, "relative_work": r["feature_work"]/reference_work if r["completed"] else config["timeout_relative_work"], "regret_lower": statistics.fmean(x["lower"]/normalization for x in regrets) if regrets else None, "regret_upper": statistics.fmean(x["upper"]/normalization for x in regrets) if regrets else None, "completed": r["completed"], "unknown": sum(x["unknown_comparisons"] for x in regrets), "reached": len(regrets)})
            contexts.append(c)
    audit.require(seen == {(p, s) for p in pairs for s in ("left", "right")} and len(contexts) == meta["complete.json"]["training_contexts"] == 66, "training_66_complete_contexts", "contexts", "population incomplete")
    information_summary = information_replay(contexts, bank, information, seeds, set(execution["source"]["training_graph_digests"]))
    pure_summary = pure_cancellation(contexts, Fraction(config["epsilon"]), args.pure_output or output.with_name("pure_cancellation_training.json"))
    def macro(rows, field):
        families = defaultdict(list)
        for r in rows:
            if r[field] is not None:
                families[r["family"]].append(r[field])
        return statistics.fmean(statistics.fmean(v) for v in families.values()) if families else None
    recomputed = []
    saved = {r["id"]: r for r in meta["assessments.json"]}
    for entry in bank:
        rows = COLLECTED[entry["id"]]
        quality, cost = macro(rows, "quality"), macro(rows, "relative_work")
        r = {**entry, "macro_train_quality": quality, "macro_relative_work": cost, "primary_utility": quality-config["cost_penalty"]*(cost-1), "macro_actual_regret_lower": macro(rows, "regret_lower"), "macro_actual_regret_upper": macro(rows, "regret_upper"), "completed": sum(x["completed"] for x in rows), "contexts": len(rows), "unknown_comparisons": sum(x["unknown"] for x in rows), "reached_audited_states": sum(x["reached"] for x in rows), "contradictory": information["candidate_quotients"][entry["id"]]["contradictory"]}
        for key, value in r.items():
            audit.require(audit.near(saved[entry["id"]][key], value) if isinstance(value, float) else saved[entry["id"]][key] == value, "training_assessment_reproduction", entry["id"] + "/" + key, "metric mismatch")
        recomputed.append(r)
    selection = {}
    for arm in sorted({e["arm"] for e in bank}):
        pool = [r for r in recomputed if r["arm"] == arm]
        if arm in ("guided_v04", "free_v03", "enumerated_v03") and config["joint_information_gate"]:
            pool = [r for r in pool if not r["contradictory"]]
        primary = max(pool, key=lambda r: (r["primary_utility"], -r["index"]))
        band = [r for r in pool if r["primary_utility"] >= primary["primary_utility"]-config["primary_tie_band"]]
        chosen = min(band, key=lambda r: (r["macro_actual_regret_upper"] if r["macro_actual_regret_upper"] is not None else float("inf"), r["macro_actual_regret_lower"] if r["macro_actual_regret_lower"] is not None else float("inf"), r["unknown_comparisons"], -r["primary_utility"], r["index"]))
        selection[arm] = {"eligible": len(pool), "within_primary_band": len(band), "selected_id": chosen["id"], "primary_only_id": primary["id"], "unknown_is_not_a_hard_gate": True}
        audit.require(selection[arm] == frozen["selection"][arm] and chosen["program"] == frozen["programs"][arm], "training_selection_reproduction", arm, "selected program mismatch")
    audit.require(frozen["programs"]["guided_primary_only_ablation"] == frozen["programs"]["guided_v04"], "guided_main_equals_primary_ablation", "freeze", "unexpected ablation bytes")
    if args.local_cache is not None:
        for name in ("frozen_programs.json", "assessments.json", "complete.json"):
            local = args.local_cache / {"frozen_programs.json":"train_v04_frozen.json", "assessments.json":"train_v04_assessments.json", "complete.json":"train_v04_complete.json"}[name]
            audit.require(json.loads(local.read_text(encoding="utf-8")) == meta[name], "training_local_archive_semantics", name, "local copy mismatch")
    report = {"scope": "TRAIN archive and frozen source only; no fresh validation/test access, no study rerun", "archive_sha256": audit.file_digest(path), "source_zip_sha256": audit.file_digest(source_path), "source_manifest_verified": True, "local_cache_compared": args.local_cache is not None, "member_sha256": hashes, "context_count": len(contexts), "bank_count": len(bank), "families": dict(Counter(c["family"] for c in contexts)), "information_replay":information_summary, "selection": selection, "main_guided": next({k:v for k,v in r.items() if k != "program"} for r in recomputed if r["id"] == selection["guided_v04"]["selected_id"]), "counts": dict(COUNTS), "small_distinct_components": len(SMALL), "matched_cancellation": {"comparisons": len(WIDTHS), "with_common_components": sum(x["has_common"] for x in WIDTHS), "full_zero_search_strict": sum(x["full_strict"] for x in WIDTHS), "cancelled_zero_search_strict": sum(x["cancelled_zero_strict"] for x in WIDTHS), "narrower": sum(x["cancelled_zero_width"] < x["full_width"] for x in WIDTHS), "equal": sum(x["cancelled_zero_width"] == x["full_width"] for x in WIDTHS), "wider": sum(x["cancelled_zero_width"] > x["full_width"] for x in WIDTHS), "median_full_width": statistics.median(x["full_width"] for x in WIDTHS), "median_cancelled_zero_width": statistics.median(x["cancelled_zero_width"] for x in WIDTHS)}, "checks": dict(audit.CHECKS), "issues": list(audit.ISSUES.values()), "limitations": ["Large component upper endpoints are computational receipts tied to hash-verified executed oracle source; no saved B&B frontier certificate.", "Matched full-residual endpoints have no component witnesses; the cancelled counterpart arithmetic and component witnesses are checked.", "TRAIN-only access declarations are provenance evidence, not a proof of every human information access."]}
    report["pure_cancellation"] = pure_summary
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"output": str(output), "contexts": len(contexts), "bank": len(bank), "selected": selection, "checks": sum(audit.CHECKS.values()), "issues": report["issues"], "matched": report["matched_cancellation"]}))
    return int(any(i["severity"] == "error" for i in report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
