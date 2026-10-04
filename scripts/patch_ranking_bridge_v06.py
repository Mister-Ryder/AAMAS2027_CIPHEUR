"""Freeze common-Degree TRAIN patches, then run a separately released ranking assay.

Preparation never scores a program or computes a conditional value. Execution
requires a root-issued release binding the plan, program inventory and runtime.
All labels concern forced inclusion in the saved RESTRICTED patch; they do not
certify branch-pivot efficiency, full residual optima or deployment improvement.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE_NAMES = ("scripts/patch_ranking_bridge_v06.py", "cipheur/__init__.py",
                "cipheur/model.py", "cipheur/programs.py",
                "cipheur/graph_features.py", "cipheur/compiled.py")
STARTUP_SOURCES = {name: sha256((ROOT / name).read_bytes()).hexdigest()
                   for name in SOURCE_NAMES}
from cipheur.model import Graph

LOCAL_SCOPE = "restricted_patch_forced_include_with_saved_outside_incumbent_fixed"
FULL_SCOPE = "original_full_residual_requirement_at_original_permanent_boundary"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                   allow_nan=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sources():
    current = {name: digest(ROOT / name) for name in SOURCE_NAMES}
    if current != STARTUP_SOURCES:
        raise ValueError("Runtime changed after startup")
    return current


def validate_config(config):
    for key in ("expected_states", "pairs_per_patch", "max_patch_vertices",
                "recurrence_states_per_query", "max_score_feature_work"):
        if type(config.get(key)) is not int or config[key] < 0:
            raise ValueError("Nonnegative integer required: " + key)
    if config["pairs_per_patch"] != 4 or config["recurrence_states_per_query"] > 100000:
        raise ValueError("Four fixed pairs and at most 100000 recurrence states are required")
    for key in ("certificate_epsilon_exact", "score_margin_exact"):
        if Fraction(config[key]) < 0:
            raise ValueError("Margins must be nonnegative")
    if not isinstance(config.get("salt"), str) or not config["salt"]:
        raise ValueError("A fixed sampling salt is required")
    if config.get("split") != "train" or config.get("no_authoring_or_selection_feedback") is not True:
        raise ValueError("Bridge is TRAIN-only and cannot feed authoring or selection")
    return config


def pair_plan(graph, region, identity, config):
    """Metadata only: adjacent pairs first, fixed hash order within each group."""
    candidates = list(itertools.combinations(sorted(region), 2))
    def key(pair):
        text = config["salt"] + "|" + identity + "|" + pair[0] + "|" + pair[1]
        return (pair[1] not in graph.adj[pair[0]], sha256(text.encode()).digest(), pair)
    ordered = sorted(candidates, key=key)
    rows = [{"a": a, "b": b, "sample_rank": i,
             "competing": b in graph.adj[a]} for i, (a, b)
            in enumerate(ordered[:config["pairs_per_patch"]])]
    adjacent = sum(b in graph.adj[a] for a, b in candidates)
    return rows, {"eligible_pairs": len(candidates), "eligible_adjacent_pairs": adjacent,
                  "planned_pairs": len(rows), "planned_adjacent_pairs": sum(r["competing"] for r in rows),
                  "pair_shortfall": max(0, config["pairs_per_patch"] - len(rows)),
                  "adjacent_quota_shortfall": max(0, config["pairs_per_patch"] - adjacent)}


def select_patch(context, row, config):
    """First constructed patch, never chosen by objective, bound or score."""
    if context.get("split") != "train" or row.get("split") != "train":
        raise ValueError("Non-TRAIN context/trace refused")
    graph = Graph.from_dict(context["graph"])
    if graph.digest() != context["graph_sha256"] or graph.digest() != row["graph_sha256"]:
        raise ValueError("Context/trace graph binding mismatch")
    fixed, excluded = set(context["fixed"]), set(context["excluded"])
    graph.available(context["fixed"], context["excluded"])
    if (context["id"] != row["id"] or row.get("method") != "shared_kernel_degree"
            or set(row["fixed"]) != fixed or set(row["excluded"]) != excluded):
        raise ValueError("Original common-Degree boundary or identity changed")
    common = {k: context.get(k) for k in ("id", "family", "cluster", "pair_id", "side")}
    common.update(split="train", graph=context["graph"], graph_sha256=graph.digest(),
                  permanent_fixed=sorted(fixed), excluded=sorted(excluded),
                  context_sha256=canonical(context), feedback_row_sha256=canonical(row))
    result = row.get("result")
    if result is None:
        return {**common, "patch_status": "no_result", "queries": [],
                "quota": {"eligible_pairs": 0, "planned_pairs": 0,
                          "pair_shortfall": config["pairs_per_patch"]}}
    if result.get("priority") != "degree" or result.get("config", {}).get("policy_scope") != "branch":
        raise ValueError("Only saved common-Degree branch-scope traces are permitted")
    incumbent = set(result["initial_selected"])
    if not graph.feasible(incumbent) or not fixed <= incumbent or incumbent & excluded:
        raise ValueError("Saved initial incumbent violates permanent boundary")
    trace = result["patch_trace"]
    for i, patch in enumerate(trace):
        # Successful construction means a nonempty materialized region, even
        # if local search later stopped, pruned at root or returned an error.
        if patch.get("patch"):
            destroy, region = set(patch["destroy"]), set(patch["patch"])
            outside = incumbent - destroy
            full_region = graph.available(outside, excluded)
            if (not destroy or not destroy <= incumbent or destroy & fixed
                    or not destroy <= region <= full_region
                    or len(region) > config["max_patch_vertices"]
                    or patch.get("full_region_size") != len(full_region)
                    or patch.get("stage") not in ("local_search", "returned")):
                raise ValueError("First constructed patch has invalid saved boundary/region")
            queries, quota = pair_plan(graph, region, context["id"], config)
            return {**common, "patch_status": "constructed", "patch_index": i,
                "patch_id": context["id"] + "|patch:" + str(i),
                "incumbent_before": sorted(incumbent), "outside_fixed": sorted(outside),
                "destroy": sorted(destroy), "patch": sorted(region),
                "full_free_region": sorted(full_region), "restricted": region != full_region,
                "original_trace_sha256": canonical(trace), "selected_trace_sha256": canonical(patch),
                "original_trace_stage": patch["stage"],
                "original_priority_order_present": bool(patch.get("priority_order")),
                "snapshot_sha256": canonical({"graph_sha256": graph.digest(),
                    "outside_fixed": sorted(outside), "excluded": sorted(excluded),
                    "destroy": sorted(destroy), "patch": sorted(region)}),
                "queries": queries, "quota": quota}
        # Reconstruction is independent of choosing a gain. A malformed trace
        # must not be skipped in favor of a later more attractive patch.
        if patch.get("committed"):
            raise ValueError("A trace cannot commit before recording a constructed patch")
    return {**common, "patch_status": "no_constructed_nonempty_patch", "queries": [],
            "quota": {"eligible_pairs": 0, "planned_pairs": 0,
                      "pair_shortfall": config["pairs_per_patch"]}}


def build_inventory(contexts, feedback, config):
    validate_config(config)
    ids = [r["id"] for r in contexts]
    if (len(ids) != config["expected_states"] or len(set(ids)) != len(ids)
            or len(feedback) != len(ids) or len({r["id"] for r in feedback}) != len(ids)
            or set(ids) != {r["id"] for r in feedback}):
        raise ValueError("Every original TRAIN identity must occur exactly once")
    lookup = {r["id"]: r for r in feedback}
    return [select_patch(c, lookup[c["id"]], config) for c in sorted(contexts, key=lambda c: c["id"])]


def archive_data(path):
    selected, bindings = {}, {}
    with tarfile.open(path) as archive:
        for suffix in ("training_contexts.json", "results.jsonl", "protocol.json", "freeze_receipt.json"):
            members = [m for m in archive.getmembers() if m.isfile() and m.name.endswith("/" + suffix)]
            if len(members) != 1:
                raise ValueError("Expected unique feedback member: " + suffix)
            raw = archive.extractfile(members[0]).read()
            bindings[suffix] = {"member": members[0].name, "sha256": sha256(raw).hexdigest()}
            selected[suffix] = ([json.loads(line) for line in raw.splitlines() if line]
                                if suffix.endswith(".jsonl") else json.loads(raw))
    protocol, receipt = selected["protocol.json"], selected["freeze_receipt.json"]
    if (protocol.get("split") != "train" or protocol.get("priority") != "degree"
            or receipt.get("before_any_feedback_execution") is not True
            or receipt.get("protocol_sha256") != bindings["protocol.json"]["sha256"]
            or receipt.get("training_contexts_sha256") != bindings["training_contexts.json"]["sha256"]):
        raise ValueError("Original feedback archive freeze is inconsistent")
    return selected["training_contexts.json"]["contexts"], selected["results.jsonl"], bindings


def prepare(archive, config_path, full_training_evidence, out):
    out, config = Path(out), validate_config(read(config_path))
    if out.exists():
        raise ValueError("Preserve existing bridge registration")
    if digest(archive) != config["feedback_archive_sha256"]:
        raise ValueError("Common-Degree archive differs from the prescribed original")
    contexts, rows, bindings = archive_data(archive)
    inventory = build_inventory(contexts, rows, config)
    # The core SHA plan is already fixed. This second stratum uses only the
    # pre-existing strict inventory, never new local values or program scores.
    evidence = read(full_training_evidence)
    references = full_reference_index(evidence, inventory)
    for state in inventory:
        enrich_queries(state, references[state["id"]], config)
    out.mkdir(parents=True)
    write(out / "config.json", config)
    write(out / "inventory.json", {"split": "train", "records": inventory})
    # Preserve existing evidence. The added stratum is explicitly conditioned
    # on its original strict certification; the four core pairs are not.
    (out / "original_training_evidence.json").write_bytes(Path(full_training_evidence).read_bytes())
    protocol = {"version": config["version"], "split": "train",
        "before_any_bridge_certificate_or_program_score": True,
        "bridge_program_inventory_accessed": False, "selection_performed": False,
        "archive_sha256": digest(archive), "archive_members": bindings,
        "original_training_evidence_sha256": digest(full_training_evidence),
        "states": len(inventory), "patch_status_counts": dict(Counter(r["patch_status"] for r in inventory)),
        "planned_queries": sum(len(r["queries"]) for r in inventory),
        "core_SHA_queries": sum(q["in_core_sha"] for r in inventory for q in r["queries"]),
        "original_full_strict_pair_queries": sum(q["in_full_strict_bridge"] for r in inventory for q in r["queries"]),
        "added_query_scope": "All pre-existing strict full-TRAIN pairs surviving in Rprime; certification-conditioned, not natural incidence",
        "query_shortfalls": sum(r["quota"]["pair_shortfall"] for r in inventory),
        "local_label_scope": LOCAL_SCOPE, "original_label_scope": FULL_SCOPE,
        "runtime_source_sha256": sources()}
    write(out / "protocol.json", protocol)
    receipt = {"version": config["version"], "split": "train",
        "before_any_bridge_certificate_or_program_score": True,
        "files": {name: digest(out / name) for name in
                  ("config.json", "inventory.json", "protocol.json", "original_training_evidence.json")},
        "runtime_source_sha256": sources()}
    write(out / "freeze_receipt.json", receipt)
    return {"prepared": str(out), "states": len(inventory),
            "patch_status_counts": protocol["patch_status_counts"], "queries": protocol["planned_queries"],
            "new_certificates": 0, "program_scores": 0}


def components(graph, vertices):
    remaining, parts = set(vertices), []
    while remaining:
        first = min(remaining); remaining.remove(first)
        found, pending = {first}, [first]
        while pending:
            neighbors = graph.adj[pending.pop()] & remaining
            remaining -= neighbors; found |= neighbors; pending.extend(sorted(neighbors))
        parts.append(tuple(sorted(found)))
    return tuple(sorted(parts))


class _RecurrenceLimit(Exception):
    pass


def component_bound(graph, part, state_limit):
    """Independent memo recurrence; a stop retains only verified sound bounds."""
    if type(state_limit) is not int or not 0 <= state_limit <= 100000:
        raise ValueError("Recurrence limit must be an integer in [0, 100000]")
    nodes = tuple(sorted(part)); weights = [Fraction(graph.nodes[v].weight) for v in nodes]
    adjacency = [sum(1 << j for j, u in enumerate(nodes) if u in graph.adj[v]) for v in nodes]
    full, memo, states = (1 << len(nodes)) - 1, {0: (Fraction(), 0)}, 0
    def alpha(mask):
        nonlocal states
        if mask in memo:
            return memo[mask]
        if states >= state_limit:
            raise _RecurrenceLimit()
        states += 1
        indices = [i for i in range(len(nodes)) if mask & (1 << i)]
        i = min(indices, key=lambda j: (-(adjacency[j] & mask).bit_count(), nodes[j]))
        rest = mask & ~(1 << i)
        without = alpha(rest)
        residual_value, residual_selection = alpha(rest & ~adjacency[i])
        with_i = (weights[i] + residual_value, residual_selection | (1 << i))
        result = with_i if with_i[0] > without[0] else without
        memo[mask] = result
        return result
    try:
        lower, chosen = alpha(full)
        upper, reason = lower, "exact_memo_recurrence"
    except _RecurrenceLimit:
        # These two witnesses are independently checked below. Partial memo
        # search is not falsely reported as exhaustive after a hard stop.
        active, chosen, lower = full, 0, Fraction()
        order = sorted(range(len(nodes)), key=lambda i: (-weights[i], nodes[i]))
        for i in order:
            if active & (1 << i):
                chosen |= 1 << i; lower += weights[i]
                active &= ~((1 << i) | adjacency[i])
        remaining, cover = set(nodes), []
        for v in sorted(nodes, key=lambda v: (-len(graph.adj[v] & set(nodes)), v)):
            if v not in remaining:
                continue
            clique = [v]; remaining.remove(v)
            for u in sorted(remaining):
                if all(u in graph.adj[x] for x in clique):
                    clique.append(u); remaining.remove(u)
            cover.append(clique)
        flattened = [v for clique in cover for v in clique]
        if len(flattened) != len(set(flattened)) or set(flattened) != set(nodes):
            raise AssertionError("Fallback clique partition is invalid")
        if any(b not in graph.adj[a] for clique in cover
               for a, b in itertools.combinations(clique, 2)):
            raise AssertionError("Fallback clique witness is invalid")
        upper = sum((max(Fraction(graph.nodes[v].weight) for v in clique) for clique in cover), Fraction())
        reason = "recurrence_limit_sound_clique_enclosure"
    selected = [v for i, v in enumerate(nodes) if chosen & (1 << i)]
    if not graph.feasible(selected) or lower != sum((Fraction(graph.nodes[v].weight) for v in selected), Fraction()) or lower > upper:
        raise AssertionError("Component enclosure failed independent witness checks")
    return {"lower_exact": str(lower), "upper_exact": str(upper), "selected": selected,
            "exact": lower == upper, "recurrence_states": states, "state_limit": state_limit,
            "reason": reason}


def local_difference(graph, region, a, b, state_limit=100000, epsilon=Fraction()):
    if type(state_limit) is not int or not 0 <= state_limit <= 100000:
        raise ValueError("Per-query recurrence limit must be an integer in [0, 100000]")
    region = set(region)
    if a == b or not {a, b} <= region or not region <= graph.nodes.keys():
        raise ValueError("Both distinct actions must occur in the frozen patch")
    if Fraction(epsilon) < 0:
        raise ValueError("Certificate margin must be nonnegative")
    pa = set(components(graph, region - {a} - graph.adj[a]))
    pb = set(components(graph, region - {b} - graph.adj[b]))
    cache, states_used = {}, 0
    def bound(part):
        nonlocal states_used
        if part not in cache:
            cache[part] = component_bound(graph, part, max(0, state_limit - states_used))
            states_used += cache[part]["recurrence_states"]
        return cache[part]
    unmatched = {side: [{"vertices": list(p), "bound": bound(p)} for p in sorted(parts)]
                 for side, parts in (("a", pa - pb), ("b", pb - pa))}
    forced = Fraction(graph.nodes[a].weight) - Fraction(graph.nodes[b].weight)
    lower = forced + sum((Fraction(r["bound"]["lower_exact"]) for r in unmatched["a"]), Fraction())
    lower -= sum((Fraction(r["bound"]["upper_exact"]) for r in unmatched["b"]), Fraction())
    upper = forced + sum((Fraction(r["bound"]["upper_exact"]) for r in unmatched["a"]), Fraction())
    upper -= sum((Fraction(r["bound"]["lower_exact"]) for r in unmatched["b"]), Fraction())
    preferred = a if lower > Fraction(epsilon) else b if upper < -Fraction(epsilon) else None
    return {"a": a, "b": b, "lower_exact": str(lower), "upper_exact": str(upper),
            "preferred": preferred, "status": "strict" if preferred else "exact_tie" if lower == upper == 0 else "unknown",
            "exact": lower == upper, "cancelled_components": [list(p) for p in sorted(pa & pb)],
            "unmatched": unmatched, "recurrence_states": sum(x["recurrence_states"] for x in cache.values()),
            "epsilon_exact": str(Fraction(epsilon)), "query_state_limit": state_limit, "scope": LOCAL_SCOPE,
            "outside_incumbent_weight_cancels": True}


def full_reference_index(data, inventory):
    """Existing TRAIN labels only; never query new full-graph certificates."""
    records, labels = data["records"], data["labels"]
    if any(r.get("split") != "train" for r in records + labels):
        raise ValueError("Original reference input must contain TRAIN rows only")
    originals = {r["id"]: r for r in records}
    saved = {r["id"]: r for r in labels}
    if len(originals) != len(records) or len(saved) != len(labels):
        raise ValueError("Duplicate original reference identities")
    result = {}
    for state in inventory:
        original, label = originals[state["id"]], saved[state["id"]]
        if (Graph.from_dict(original["graph"]).digest() != state["graph_sha256"]
                or label["graph_digest"] != state["graph_sha256"]
                or set(original["fixed"]) != set(state["permanent_fixed"])
                or set(original["excluded"]) != set(state["excluded"])):
            raise ValueError("Original full labels differ from saved source/boundary")
        region, refs = set(state.get("patch", [])), []
        for i, row in enumerate(label["rows"]):
            difference = row["difference"]
            if difference["status"] == "strict" and {row["a"], row["b"]} <= region:
                preferred = difference["preferred"]
                if preferred not in (row["a"], row["b"]):
                    raise ValueError("Original strict label has invalid preferred action")
                refs.append({"a": row["a"], "b": row["b"], "preferred": preferred,
                    "original_row_index": i, "lower_exact": difference["lower_exact"],
                    "upper_exact": difference["upper_exact"], "scope": FULL_SCOPE})
        result[state["id"]] = refs
    return result


def enrich_queries(state, references, config):
    """Union core SHA pairs with ALL original strict surviving pairs."""
    core = state["queries"]
    merged = {tuple(sorted((q["a"], q["b"]))): {**q, "in_core_sha": True,
              "in_full_strict_bridge": False, "full_reference_rows": []} for q in core}
    graph = Graph.from_dict(state["graph"])
    for ref in references:
        key = tuple(sorted((ref["a"], ref["b"])))
        if key not in merged:
            merged[key] = {"a": key[0], "b": key[1], "sample_rank": None,
                "competing": key[1] in graph.adj[key[0]], "in_core_sha": False,
                "in_full_strict_bridge": True, "full_reference_rows": []}
        merged[key]["in_full_strict_bridge"] = True
        merged[key]["full_reference_rows"].append(ref["original_row_index"])
    extras = sorted((q for q in merged.values() if not q["in_core_sha"]),
        key=lambda q: sha256((config["salt"] + "|full|" + state["id"] + "|" + q["a"] + "|" + q["b"]).encode()).digest())
    state["queries"] = [merged[tuple(sorted((q["a"], q["b"])))] for q in core] + extras
    for i, q in enumerate(state["queries"]):
        q["query_rank"] = i
    state["quota"].update(core_planned_pairs=len(core),
        full_strict_surviving_requirements=len(references),
        full_strict_surviving_unique_pairs=sum(q["in_full_strict_bridge"] for q in state["queries"]),
        union_planned_pairs=len(state["queries"]), added_original_full_pairs=len(extras))
    if len(state["queries"]) > 20:
        raise ValueError("Original <=16 plus core four pair bank exceeded twenty")


class _FeatureLimit(Exception):
    pass


class FeatureMeter(dict):
    def __init__(self, limit):
        super().__init__(feature_work=0, feature_primitives={}); self.limit = limit
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key == "feature_work" and value > self.limit:
            raise _FeatureLimit("Feature-work cap reached; partial scores are not full predictions")


def validate_program_inventory(bank, config):
    if bank.get("selection_split") != "train" or bank.get("test_used_for_selection") is not False:
        raise ValueError("Programs must have been selected/frozen on TRAIN without TEST tuning")
    entries = bank["entries"]
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Deployment identities must be unique; duplicate ASTs remain separate")
    counts = Counter(e["role"] for e in entries)
    expected = dict(config["required_roles"])
    if counts.get("eoh_quality", 0):
        expected["eoh_quality"] = config["optional_eoh_identities"]
    if dict(counts) != expected:
        raise ValueError("Retain every declared role/identity, including explicit nulls")
    for e in entries:
        if not isinstance(e["id"], str) or not e["id"] or e.get("priority") not in ("degree", "program"):
            raise ValueError("Invalid explicit identity or priority")
        if (e["role"] == "degree") != (e["priority"] == "degree"):
            raise ValueError("Only the Degree control uses Degree priority")
        if e["priority"] == "degree" and e.get("program") is not None:
            raise ValueError("Degree has no program AST")
        if e["role"] == "witness_joint" and e.get("program") is None:
            raise ValueError("Four genuine W joint programs are required; no missing replacement")
    return entries


def score_patch(state, entry, config, references, local_labels):
    """Exactly the immutable snapshot used by the kernel, with no label input."""
    common = {"state_id": state["id"], "program_id": entry["id"], "role": entry["role"],
              "patch_status": state["patch_status"], "selection_performed": False}
    if state["patch_status"] != "constructed":
        return {**common, "status": "no_patch", "scores": None, "local_fit": None, "full_target_fit": None}
    if entry["priority"] == "program" and entry.get("program") is None:
        return {**common, "status": "missing_program", "scores": None, "local_fit": None, "full_target_fit": None}
    graph, region = Graph.from_dict(state["graph"]), set(state["patch"])
    scores, meter = {}, FeatureMeter(config["max_score_feature_work"])
    cpu, wall = time.process_time(), time.perf_counter()
    try:
        if entry["priority"] == "degree":
            for v in sorted(region):
                meter["feature_work"] += len(graph.adj[v]) + 2
                scores[v] = Fraction(graph.nodes[v].weight) / max(1, len(graph.adj[v] & region))
        else:
            from cipheur.compiled import CompiledEvaluator
            from cipheur.graph_features import FeatureRuleProgram
            programme = FeatureRuleProgram.from_dict(entry["program"])
            evaluator = CompiledEvaluator(graph, programme, region, meter, score_slice=True)
            for v in sorted(region):
                score = evaluator.score(v)
                if not math.isfinite(score):
                    raise ValueError("Nonfinite patch score")
                scores[v] = Fraction(score)
        order = sorted(region, key=lambda v: (-scores[v], v))
        active, greedy = set(region), []
        for v in order:
            if v in active:
                greedy.append(v); active -= {v} | graph.adj[v]
        if not graph.feasible(greedy) or not graph.feasible(set(greedy) | set(state["outside_fixed"])):
            raise AssertionError("Immutable-priority greedy proposal is infeasible")
        margin = Fraction(config["score_margin_exact"])
        def fit(targets):
            rows = []
            for r in targets:
                preferred = r["preferred"]
                if preferred is None:
                    continue
                other = r["b"] if preferred == r["a"] else r["a"]
                difference = scores[preferred] - scores[other]
                rows.append({"a": r["a"], "b": r["b"], "preferred": preferred,
                    "score_difference_exact": str(difference), "passed": difference > margin,
                    "score_tie": difference == 0, "target_scope": r["scope"],
                    "in_core_sha": r.get("in_core_sha", False),
                    "in_full_strict_bridge": r.get("in_full_strict_bridge", False)})
            return {"strict_targets": len(rows), "passed": sum(r["passed"] for r in rows),
                "core_SHA_strict_targets": sum(r["in_core_sha"] for r in rows),
                "core_SHA_passed": sum(r["in_core_sha"] and r["passed"] for r in rows),
                "full_strict_pair_local_targets": sum(r["in_full_strict_bridge"] for r in rows),
                "full_strict_pair_local_passed": sum(r["in_full_strict_bridge"] and r["passed"] for r in rows),
                "rows": rows}
        return {**common, "status": "scored", "snapshot_sha256": state["snapshot_sha256"],
            "scores": {v: str(scores[v]) for v in sorted(scores)}, "priority_order": order,
            "local_fit": fit(local_labels), "full_target_fit": fit(references),
            "greedy_proposal": greedy, "greedy_patch_weight_exact": str(sum((Fraction(graph.nodes[v].weight) for v in greedy), Fraction())),
            "greedy_scope": "diagnostic priority-only proposal; not the kernel's retained best incumbent",
            "branch_scope": "fixed priority ordering only; no branch search or pivot-efficiency evaluation",
            "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.perf_counter() - wall,
            "feature_meter": dict(meter), "score_margin_exact": str(margin)}
    except Exception as error:
        return {**common, "status": "score_work_cap" if isinstance(error, _FeatureLimit) else "score_error",
            "scores": None, "local_fit": None, "full_target_fit": None,
            "partial_scores_not_predictions": {v: str(x) for v, x in scores.items()},
            "error_type": type(error).__name__, "error": str(error),
            "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.perf_counter() - wall,
            "feature_meter": dict(meter)}


def verify_release(registration, programmes, release, release_sha256):
    registration = Path(registration)
    receipt, protocol, config = (read(registration / n) for n in
                                ("freeze_receipt.json", "protocol.json", "config.json"))
    if (receipt.get("split") != "train" or receipt.get("before_any_bridge_certificate_or_program_score") is not True
            or protocol.get("before_any_bridge_certificate_or_program_score") is not True):
        raise ValueError("Bridge inventory must precede its labels and scores")
    for name, expected in receipt["files"].items():
        if digest(registration / name) != expected:
            raise ValueError("Bridge registration changed: " + name)
    if receipt["runtime_source_sha256"] != sources() or protocol["runtime_source_sha256"] != sources():
        raise ValueError("Bridge runtime differs from frozen source capsule")
    if digest(release) != release_sha256:
        raise ValueError("Root release identity mismatch")
    approval = read(release)
    required = {"bridge_execution_authorized": True, "program_release_complete": True,
        "before_any_bridge_certificate_or_program_score": True, "selection_split": "train",
        "no_bridge_authoring_or_selection_feedback": True,
        "bridge_freeze_sha256": digest(registration / "freeze_receipt.json"),
        "program_inventory_sha256": digest(programmes), "runtime_source_sha256": sources()}
    if any(approval.get(k) != v for k, v in required.items()):
        raise ValueError("A matching explicit root bridge release is required")
    inventory_file = read(registration / "inventory.json")
    if inventory_file.get("split") != "train" or any(r.get("split") != "train" for r in inventory_file["records"]):
        raise ValueError("Non-TRAIN patch inventory refused")
    entries = validate_program_inventory(read(programmes), validate_config(config))
    return config, inventory_file["records"], entries


def run(registration, programmes, release, release_sha256, out):
    config, inventory, entries = verify_release(registration, programmes, release, release_sha256)
    references = full_reference_index(read(Path(registration) / "original_training_evidence.json"), inventory)
    out = Path(out)
    if out.exists():
        raise ValueError("Never overwrite bridge outcomes")
    out.mkdir(parents=True)
    for name in ("inventory.json", "config.json", "protocol.json", "freeze_receipt.json", "original_training_evidence.json"):
        (out / name).write_bytes((Path(registration) / name).read_bytes())
    (out / "program_inventory.json").write_bytes(Path(programmes).read_bytes())
    (out / "root_release.json").write_bytes(Path(release).read_bytes())
    hashes = {e["id"]: canonical({k: e["program"][k] for k in ("features", "rule")})
              if e.get("program") is not None else None for e in entries}
    write(out / "execution.json", {"split": "train", "runtime_source_sha256": sources(),
        "root_release_sha256": release_sha256, "deployment_ast_sha256": hashes,
        "duplicate_ast_identities_retained": True, "selection_performed": False,
        "online_model_calls": 0, "new_full_residual_oracle_calls": 0})
    label_rows, score_rows, prefixes = [], [], []
    cumulative = {e["id"]: Counter() for e in entries}
    with (out / "labels.jsonl").open("x", encoding="utf-8", newline="\n") as label_stream, (out / "scores.jsonl").open("x", encoding="utf-8", newline="\n") as score_stream:
        for state_index, state in enumerate(inventory):
            local, agreements = [], []
            if state["patch_status"] == "constructed":
                graph = Graph.from_dict(state["graph"])
                for query in state["queries"]:
                    value = local_difference(graph, state["patch"], query["a"], query["b"],
                        config["recurrence_states_per_query"], Fraction(config["certificate_epsilon_exact"]))
                    local.append({**query, **value})
                for ref in references[state["id"]]:
                    overlap = next((r for r in local if {r["a"], r["b"]} == {ref["a"], ref["b"]}), None)
                    if overlap is not None:
                        agreements.append({"a": ref["a"], "b": ref["b"], "full_preferred": ref["preferred"],
                            "local_preferred": overlap["preferred"], "local_status": overlap["status"],
                            "direction_agrees": overlap["preferred"] == ref["preferred"] if overlap["status"] == "strict" else None,
                            "full_scope": FULL_SCOPE, "local_scope": LOCAL_SCOPE})
            label_row = {"id": state["id"], "split": "train", "family": state["family"],
                "patch_status": state["patch_status"], "snapshot_sha256": state.get("snapshot_sha256"),
                "quota": state["quota"], "rows": local, "available_original_full_requirements": references[state["id"]],
                "full_vs_local_overlap": agreements, "oracle_used_by_program": False}
            label_rows.append(label_row)
            label_stream.write(json.dumps(label_row, ensure_ascii=False, allow_nan=False) + "\n"); label_stream.flush()
            for entry in entries:
                scored = score_patch(state, entry, config, references[state["id"]], local)
                score_rows.append(scored)
                score_stream.write(json.dumps(scored, ensure_ascii=False, allow_nan=False) + "\n"); score_stream.flush()
                counter = cumulative[entry["id"]]
                counter["assigned_states"] += 1
                counter["sampled_queries"] += len(local)
                counter["local_strict_labels"] += sum(r["status"] == "strict" for r in local)
                counter["core_SHA_queries"] += sum(r["in_core_sha"] for r in local)
                counter["core_SHA_strict_labels"] += sum(r["in_core_sha"] and r["status"] == "strict" for r in local)
                counter["full_strict_pair_queries"] += sum(r["in_full_strict_bridge"] for r in local)
                counter["score_complete_states"] += scored["status"] == "scored"
                if scored["local_fit"] is not None:
                    counter["observed_local_strict_predictions"] += scored["local_fit"]["strict_targets"]
                    counter["local_strict_passed"] += scored["local_fit"]["passed"]
                    counter["observed_core_SHA_strict_predictions"] += scored["local_fit"]["core_SHA_strict_targets"]
                    counter["core_SHA_strict_passed"] += scored["local_fit"]["core_SHA_passed"]
                    counter["observed_full_pair_local_strict_predictions"] += scored["local_fit"]["full_strict_pair_local_targets"]
                    counter["full_pair_local_strict_passed"] += scored["local_fit"]["full_strict_pair_local_passed"]
                    counter["observed_full_target_predictions"] += scored["full_target_fit"]["strict_targets"]
                    counter["full_target_passed"] += scored["full_target_fit"]["passed"]
                prefixes.append({"program_id": entry["id"], "state_prefix": state_index + 1,
                                 "last_state_id": state["id"], **dict(counter)})
    coverage = {"states": len(inventory), "patch_status_counts": dict(Counter(r["patch_status"] for r in inventory)),
        "families": dict(Counter(r["family"] for r in inventory)),
        "original_priority_order_present_states": sum(r.get("original_priority_order_present", False) for r in inventory),
        "planned_queries": sum(len(r["queries"]) for r in inventory),
        "planned_adjacent_queries": sum(q["competing"] for r in inventory for q in r["queries"]),
        "core_SHA_queries": sum(q["in_core_sha"] for r in inventory for q in r["queries"]),
        "core_SHA_local_label_status_counts": dict(Counter(r["status"] for s in label_rows for r in s["rows"] if r["in_core_sha"])),
        "original_full_strict_pair_queries": sum(q["in_full_strict_bridge"] for r in inventory for q in r["queries"]),
        "original_full_strict_pair_local_status_counts": dict(Counter(r["status"] for s in label_rows for r in s["rows"] if r["in_full_strict_bridge"])),
        "per_family": {family: {
            "states": sum(r["family"] == family for r in inventory),
            "constructed_patches": sum(r["family"] == family and r["patch_status"] == "constructed" for r in inventory),
            "core_SHA_queries": sum(q["in_core_sha"] for r in inventory if r["family"] == family for q in r["queries"]),
            "union_queries": sum(len(r["queries"]) for r in inventory if r["family"] == family),
            "local_status": dict(Counter(q["status"] for r in label_rows if r["family"] == family for q in r["rows"]))}
            for family in sorted({r["family"] for r in inventory})},
        "pair_quota_shortfalls": sum(r["quota"]["pair_shortfall"] for r in inventory),
        "local_label_status_counts": dict(Counter(r["status"] for s in label_rows for r in s["rows"])),
        "original_full_requirements_available": sum(len(s["available_original_full_requirements"]) for s in label_rows),
        "full_local_overlap": sum(len(s["full_vs_local_overlap"]) for s in label_rows),
        "strict_full_local_agreement": sum(r["direction_agrees"] is True for s in label_rows for r in s["full_vs_local_overlap"]),
        "strict_full_local_disagreement": sum(r["direction_agrees"] is False for s in label_rows for r in s["full_vs_local_overlap"]),
        "scope": "Local inclusion agreement only; no pivot-efficiency or complete-schedule effectiveness claim"}
    write(out / "coverage.json", coverage)
    write(out / "prefixes.json", prefixes)
    write(out / "summary.json", [{"id": e["id"], "role": e["role"], "deployment_ast_sha256": hashes[e["id"]],
        "missing_program": e["priority"] == "program" and e.get("program") is None,
        "status_counts": dict(Counter(r["status"] for r in score_rows if r["program_id"] == e["id"])),
        **dict(cumulative[e["id"]]), "missing_predictions_are_not_zero_accuracy": True} for e in entries])
    write(out / "complete.json", {"split": "train", "execution_complete": True,
        "assigned_states": len(inventory), "assigned_program_state_identities": len(inventory) * len(entries),
        "labels_sha256": digest(out / "labels.jsonl"), "scores_sha256": digest(out / "scores.jsonl"),
        "selection_performed": False, "online_model_calls": 0, "new_full_residual_oracle_calls": 0,
        "no_authoring_or_selection_feedback": True, "root_release_sha256": release_sha256,
        "runtime_source_sha256": sources()})
    return {"complete": str(out), **coverage}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    for name in ("archive", "config", "full-training-evidence", "out"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("run")
    for name in ("registration", "programmes", "release", "release-sha256", "out"):
        p.add_argument("--" + name, required=True)
    args = vars(parser.parse_args(argv)); mode = args.pop("mode")
    if mode == "prepare":
        args["config_path"] = args.pop("config")
    print(json.dumps(prepare(**args) if mode == "prepare" else run(**args), ensure_ascii=False))


if __name__ == "__main__":
    main()
