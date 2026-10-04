"""Fixed-catalogue additive-cost TRAIN experiment, registered before evaluation.

`prepare` reads static R1 ASTs and certified endpoint metadata only. `execute`
measures standalone expression work and calls the unchanged exact refinement
routine; it is a separately authorized server phase. There is no LLM, policy
selection, repair scheduler, TEST input or conditional-oracle invocation here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.graph_features import FeatureRuleProgram, _FeatureState, graph_operation_library
from cipheur.model import Graph
from cipheur.programs import FEATURES
from cipheur.refinement import minimum_cost_vector_refinement

VERSION = "v06_fixed_catalogue_additive_cost_001"
R1_RESULTS_SHA = "9520ab3b3f85d2ca6e04ca91fc805a4d1f720152e4be9fe87e873abb7580fa24"
EVIDENCE_SHA = "762fc25046eeb13f49044b96c5d74b7136dedcc363e1fec81809bcc83aa62913"
FROZEN = {
    "cipheur/graph_features.py": "b6f807e9a1a13e8443532247e24fc802815053d375f69ed2c2718a222282a03d",
    "cipheur/refinement.py": "90a7e6c6981a73d13b715dc0b2b773cd2052724c2e044af617b7795eb074bd99",
    "cipheur/representation.py": "5f844dd5ab6d5f79e92a0a7ea6ba0af6073d2e7d3f39a69a091b3fcf875d9dc0",
    "cipheur/model.py": "d5968cffb1676a2f4bd73d5ba2715618142059b0c81ec8263f76a79100a8a1d8",
    "cipheur/programs.py": "cca9739aff75dba79d3ad4b5742f1db10e88ffb398f21dbda09fc23bd20b0f59",
}
WORKER_FRAME = None
WORKER_SETUP = None


def digest(path):
    value = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False) + "\n").encode("utf-8"))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc():
    return datetime.now(timezone.utc).isoformat()


def source_inventory():
    for name, expected in FROZEN.items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen production source changed: " + name)
    return {**FROZEN, "cipheur/__init__.py": digest(ROOT / "cipheur/__init__.py"),
            "scripts/run_catalogue_refinement_v06.py": digest(__file__)}


def json_rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def collect_catalogue(path):
    """Metadata-only AST union: eligibility, scores, quality and cost are ignored."""
    expressions, positions, statuses = {}, [], Counter()
    for row in json_rows(path):
        identity = row["id"]
        if identity in positions:
            raise ValueError("Duplicate R1 raw position")
        positions.append(identity)
        statuses[row["status"]] += 1
        if row["status"] != "static_valid":
            continue
        program = FeatureRuleProgram.from_dict(row["program"])
        for old_name, compiled in program._expressions:
            expression = compiled.to_dict()
            expression_hash = sha256(canonical(expression)).hexdigest()
            entry = expressions.setdefault(expression_hash, {
                "name": "f_" + expression_hash, "expression_sha256": expression_hash,
                "expression": expression, "original_metadata_sources": []})
            if entry["expression"] != expression:
                raise ValueError("Canonical hash collision")
            entry["original_metadata_sources"].append({"original_source_id": identity,
                                                       "original_feature_name": old_name})
    expected = {f"block_{b}_{a}:{s}" for b in range(5)
                for a in ("witness", "relations", "objective") for s in range(8)}
    if set(positions) != expected:
        raise ValueError("Catalogue must retain all120 original R1 LLM positions")
    catalogue = [expressions[h] for h in sorted(expressions)]
    return catalogue, {"all_original_positions": len(positions), "status_counts": dict(statuses),
                       "canonical_expression_count": len(catalogue),
                       "original_positions": sorted(positions)}


def endpoint_frame(evidence):
    records = evidence["records"]
    if len(records) != 120 or any(r["split"] != "train" for r in records):
        raise ValueError("Only the original120 TRAIN snapshots are permitted")
    labels = {r["id"]: r for r in evidence["labels"]}
    if set(labels) != {r["id"] for r in records}:
        raise ValueError("TRAIN label bindings differ")
    graphs, active_sets, endpoints, requirements, bindings = {}, {}, {}, [], {}
    for record in sorted(records, key=lambda r: r["id"]):
        sid = record["id"]
        graph = Graph.from_dict(record["graph"])
        if graph.digest() != record["graph_digest"]:
            raise ValueError("TRAIN graph digest differs")
        active = graph.available(record["fixed"], record["excluded"])
        graphs[sid], active_sets[sid] = graph, active
        strict = [q for q in labels[sid]["rows"] if q["difference"]["status"] == "strict"]
        endpoints[sid] = sorted({q[key] for q in strict for key in ("a", "b")})
        for v in endpoints[sid]:
            oid = sid + "|" + v
            if oid in bindings or v not in active:
                raise ValueError("Ambiguous or unavailable certified occurrence")
            bindings[oid] = {"state": sid, "node": v, "graph_digest": graph.digest(),
                             "fixed": sorted(record["fixed"]), "excluded": sorted(record["excluded"])}
        for index, q in enumerate(strict):
            a, b, p = q["a"], q["b"], q["difference"]["preferred"]
            if p not in (a, b) or a == b or b not in graph.adj[a]:
                raise ValueError("Strict requirement is not an adjacent legal choice")
            n = b if p == a else a
            lo, hi = Fraction(q["difference"]["lower_exact"]), Fraction(q["difference"]["upper_exact"])
            if p == b:
                lo, hi = -hi, -lo
            if not 0 < lo <= hi:
                raise ValueError("Saved strict interval does not certify the orientation")
            requirements.append({"preferred": sid + "|" + p, "other": sid + "|" + n,
                                 "state": sid, "query_index": index,
                                 "lower_exact": str(lo), "upper_exact": str(hi)})
    if len(requirements) != 594:
        raise ValueError("Full original594 strict TRAIN frame changed")
    return {"graphs": graphs, "active": active_sets, "endpoints": endpoints,
            "requirements": requirements, "bindings": bindings}


def prepare(study, results, evidence_path):
    study, results, evidence_path = Path(study), Path(results), Path(evidence_path)
    if study.exists():
        raise ValueError("Never overwrite a registration or scientific record")
    sources = source_inventory()
    if digest(results) != R1_RESULTS_SHA or digest(evidence_path) != EVIDENCE_SHA:
        raise ValueError("The independently audited R1 source bytes differ")
    catalogue, inventory = collect_catalogue(results)
    frame = endpoint_frame(read(evidence_path))  # Boundaries/IDs only: no feature evaluation.
    if len(catalogue) != 53:
        raise ValueError("Metadata-counted53-expression catalogue differs")
    plans = [{"id": "prefix_4", "names": [f["name"] for f in catalogue[:4]]},
             {"id": "prefix_8", "names": [f["name"] for f in catalogue[:8]]},
             {"id": "prefix_16", "names": [f["name"] for f in catalogue[:16]]},
             {"id": "full_53", "names": [f["name"] for f in catalogue]}]
    for plan in plans:
        n = len(plan["names"])
        plan["catalogue_size"] = n
        plan["subsets_at_K6"] = sum(math.comb(n, k) for k in range(min(6, n) + 1))
        plan["independent_exhaustive_crosscheck"] = n <= 16
    study.mkdir(parents=True)
    write(study / "catalogue.json", {"version": VERSION, "selection": "SHA256 of canonical typed AST bytes ascending; all static-valid R1 positions, including ineligible candidates",
                                    "canonicalization": "compiled_expression.to_dict then JSON sorted keys UTF8 compact separators; names and rationales excluded; no algebraic simplification",
                                    "catalogue": catalogue, "inventory": inventory})
    shutil.copyfile(evidence_path, study / "training_evidence.json")
    write(study / "occurrence_bindings.json", {"unique_occurrences": len(frame["bindings"]),
          "bindings": frame["bindings"], "requirements": frame["requirements"]})
    protocol = {
        "version": VERSION, "registered_before_any_new_feature_value_cost_or_master": True,
        "utc": utc(), "selection_split": "train", "test_accessed": False,
        "R1_adaptive_catalogue": True, "blind_or_independent_authoring_claimed": False,
        "excluded_from_R2_author_packets_and_selector": True,
        "R1_results_sha256": R1_RESULTS_SHA, "original_evidence_sha256": EVIDENCE_SHA,
        "source_sha256": sources, "typed_library_operations": len(graph_operation_library()),
        "catalogue_sha256": digest(study / "catalogue.json"),
        "training_evidence_sha256": digest(study / "training_evidence.json"),
        "occurrence_bindings_sha256": digest(study / "occurrence_bindings.json"),
        "catalogue_size": 53, "all_static_valid_raw_positions": 112,
        "catalogue_plans": plans, "max_selected": 6,
        "max_rounds": 128, "max_master_subsets": 250000,
        "feature_limits": {"max_work": 100000000, "cpu_seconds": 60},
        "independent_master_max_states_total_per_catalogue": 250000,
        "independent_exhaustive_max_subsets": 14893,
        "all_train_states": 120, "strict_requirements": 594,
        "unique_certified_occurrences": len(frame["bindings"]), "base_features": list(FEATURES),
        "standalone_cost": "max(1,sum fresh _FeatureState charged feature_work over every unique (state,node) certified endpoint occurrence); per-expression, no cross-root/expression cache sharing",
        "cost_scope": "Positive additive standalone expression-evaluation operation proxy; excludes graph construction/static parse and shared base9 overhead. CPU/wall/setup are reported separately. Not deployment shared-DAG cost or runtime optimality.",
        "expression_failure": "Retain partial values and all assigned feature rows. Every planned catalogue containing an incomplete/nonfinite feature is unresolved; never silently remove it or substitute an expression.",
        "refinement": "Frozen minimum_cost_vector_refinement; exact budgeted master; full594-requirement quotient rebuild after every solution; fixedK6",
        "independent_checks": "Exact numeric fullQ via separate Kahn checker; concrete strict arcs/equality vectors/cut feature membership; memoized cut-mask dynamic programming cost crosscheck; exhaustive subsets for n<=16",
        "proof_scope": "Resolved full quotient plus exact masters establishes catalogue/K additive minimum only. Budget stops retain optimal=False and unresolved status. No scalar-DSL fit, new source, globally optimal feature or runtime claim.",
        "workers_default": 8, "no_oracle_policy_or_LLM_calls": True,
        "all_assignment_rows_retained": True,
    }
    write(study / "protocol.json", protocol)
    write(study / "freeze_receipt.json", {"version": VERSION, "before_feature_evaluation_and_master": True,
          "protocol_sha256": digest(study / "protocol.json"),
          "input_sha256": {name: digest(study / name) for name in ("catalogue.json", "training_evidence.json", "occurrence_bindings.json")}})
    capsule = study / "source_capsule.zip"
    member_sources = {name: ROOT / name for name in sources}
    member_sources.update({"study/" + name: study / name for name in
                           ("protocol.json", "freeze_receipt.json", "catalogue.json", "training_evidence.json", "occurrence_bindings.json")})
    with zipfile.ZipFile(capsule, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member, path in sorted(member_sources.items()):
            info = zipfile.ZipInfo(member, date_time=(2026, 10, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    write(study / "source_capsule_receipt.json", {"source_capsule_sha256": digest(capsule),
          "protocol_sha256": digest(study / "protocol.json"),
          "member_sha256": {name: digest(path) for name, path in member_sources.items()},
          "safe_relative_file_members_only": True, "no_feature_or_master_execution": True})
    return {"prepared": str(study), "catalogue_size": 53, "unique_occurrences": len(frame["bindings"]),
            "protocol_sha256": digest(study / "protocol.json"), "source_capsule_sha256": digest(capsule),
            "feature_values_or_master_run": False}


class FeatureLimit(ValueError):
    pass


class FeatureMeter(dict):
    def __init__(self, max_work, cpu_seconds):
        super().__init__()
        self.max_work, self.deadline = max_work, time.process_time() + cpu_seconds

    def check(self):
        if self.get("feature_work", 0) > self.max_work:
            raise FeatureLimit("standalone_feature_work_cap")
        if time.process_time() >= self.deadline:
            raise FeatureLimit("standalone_feature_CPU_cap")

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key == "feature_work":
            self.check()


def init_feature_worker(evidence_path):
    global WORKER_FRAME, WORKER_SETUP
    cpu, wall = time.process_time(), time.perf_counter()
    WORKER_FRAME = endpoint_frame(read(evidence_path))
    WORKER_SETUP = {"CPU_seconds": time.process_time() - cpu,
                    "wall_seconds": time.perf_counter() - wall}


def evaluate_feature(task):
    entry, limits = task
    cpu, wall = time.process_time(), time.perf_counter()
    meter, values = FeatureMeter(**limits), {}
    name = "base9" if entry is None else entry["name"]
    result = {"id": name, "completed": False, "values": values,
              "worker_shared_input_setup": WORKER_SETUP, "no_fallback": True}
    try:
        program = FeatureRuleProgram("standalone", [] if entry is None else
                                     [{"name": entry["name"], "expression": entry["expression"]}], "weight")
        expression = None if entry is None else program._expressions[0][1]
        for sid in sorted(WORKER_FRAME["graphs"]):
            graph, active = WORKER_FRAME["graphs"][sid], WORKER_FRAME["active"][sid]
            for node in WORKER_FRAME["endpoints"][sid]:
                meter.check()
                state = _FeatureState(graph, active, meter)  # Fresh standalone state per occurrence.
                value = state.feature_values(program, node) if entry is None else state.evaluate(expression, node)
                if entry is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                    raise ValueError("nonfinite_standalone_value")
                values[sid + "|" + node] = value
        meter.check()
        result.update(completed=True, status="completed", measured_standalone_work=meter.get("feature_work", 0),
                      positive_additive_cost=max(1, meter.get("feature_work", 0)))
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        result.update(status="feature_evaluation_failed", error_type=type(error).__name__, error=str(error),
                      measured_standalone_work=meter.get("feature_work", 0), positive_additive_cost=None)
    result.update(meter=dict(meter), evaluated_occurrences=len(values),
                  CPU_seconds=time.process_time() - cpu, wall_seconds=time.perf_counter() - wall)
    return result


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Independent quotient requires exact finite numeric values")
    return Fraction(value)


class IndependentQuotient:
    """Full numeric quotient, independently rebuilt by Kahn topological deletion."""
    def __init__(self, occurrences, requirements, values):
        self.ids = sorted(occurrences)
        index = {oid: i for i, oid in enumerate(self.ids)}
        base_ids = {}
        self.base = []
        for oid in self.ids:
            signature = tuple((key, number(value)) for key, value in sorted(occurrences[oid].items()))
            self.base.append(base_ids.setdefault(signature, len(base_ids)))
        self.values = {name: [number(column[oid]) for oid in self.ids] for name, column in values.items()}
        self.edges = [(index[r["preferred"]], index[r["other"]]) for r in requirements]

    def check(self, selected, detailed=True):
        names = tuple(sorted(selected))
        groups, ids = {}, []
        for i, base in enumerate(self.base):
            key = (base,) + tuple(self.values[name][i] for name in names)
            ids.append(groups.setdefault(key, len(groups)))
        adj = [set() for _ in groups]
        indegree = [0 for _ in groups]
        self_loops = 0
        for a, b in self.edges:
            u, v = ids[a], ids[b]
            if u == v:
                self_loops += 1
                if not detailed:
                    return False
            if v not in adj[u]:
                adj[u].add(v)
                indegree[v] += 1
        pending = deque(i for i, degree in enumerate(indegree) if degree == 0)
        removed = 0
        while pending:
            u = pending.popleft(); removed += 1
            for v in adj[u]:
                indegree[v] -= 1
                if indegree[v] == 0:
                    pending.append(v)
        acyclic = removed == len(groups)
        return {"acyclic": acyclic, "quotient_nodes": len(groups),
                "quotient_edges": sum(map(len, adj)), "self_loop_requirements": self_loops} if detailed else acyclic


class ProofLimit(ValueError):
    pass


def independent_cut_master(cuts, costs, max_selected, remaining_states):
    """Memoized DP on uncovered witness-bitmask and remaining feature count."""
    cuts = [set(c) for c in cuts]
    names = sorted(costs)
    cover = {name: sum(1 << i for i, cut in enumerate(cuts) if name in cut) for name in names}
    calls = 0

    @lru_cache(None)
    def solve(mask, slots):
        nonlocal calls
        if calls >= remaining_states:
            raise ProofLimit("independent_cut_DP_state_cap")
        calls += 1
        if not mask:
            return (0, ())
        if slots == 0:
            return None
        witness = min((i for i in range(len(cuts)) if mask & (1 << i)),
                      key=lambda i: (len(cuts[i]), i))
        best = None
        for name in sorted(cuts[witness]):
            tail = solve(mask & ~cover[name], slots - 1)
            if tail is None:
                continue
            if name in tail[1]:
                raise AssertionError("A feature cannot cover an uncovered cut twice")
            selected = tuple(sorted((name,) + tail[1]))
            candidate = (costs[name] + tail[0], selected)
            if best is None or (candidate[0], len(selected), selected) < (best[0], len(best[1]), best[1]):
                best = candidate
        return best
    try:
        best = solve((1 << len(cuts)) - 1, max_selected)
        return {"complete": True, "states": calls, "feasible": best is not None,
                "cost_exact": str(best[0]) if best else None,
                "selected_names": list(best[1]) if best else None}
    except ProofLimit as error:
        return {"complete": False, "states": calls, "feasible": None,
                "cost_exact": None, "selected_names": None, "reason": str(error)}


def exhaustive_refinement(checker, costs, max_selected, max_subsets):
    names, evaluated, quotient_checks, best = sorted(costs), 0, 0, None
    for size in range(min(max_selected, len(names)) + 1):
        for selected in itertools.combinations(names, size):
            if evaluated >= max_subsets:
                return {"complete": False, "subsets_enumerated": evaluated,
                        "quotient_checks": quotient_checks, "reason": "independent_exhaustive_subset_cap"}
            evaluated += 1
            cost = sum(costs[name] for name in selected)
            key = (cost, len(selected), selected)
            if best is not None and key >= best:
                continue  # Positive exact costs prove this subset cannot improve the objective.
            quotient_checks += 1
            if checker.check(selected, detailed=False):
                best = key
    return {"complete": True, "subsets_enumerated": evaluated, "quotient_checks": quotient_checks,
            "feasible": best is not None, "cost_exact": str(best[0]) if best else None,
            "selected_names": list(best[2]) if best else None,
            "scope": "every subset of fixed catalogue of size<=K enumerated; cost-dominated quotient tests skipped soundly"}


def equal_vectors(left, right):
    return set(left) == set(right) and all(number(left[k]) == number(right[k]) for k in left)


def audit_refinement(result, occurrences, requirements, values, costs, protocol, exhaustive):
    checker = IndependentQuotient(occurrences, requirements, values)
    checks, covers = [], []
    for witness in result["witnesses"]:
        arcs, joins = witness["requirements"], witness["equality_joins"]
        if len(arcs) != len(joins) or not arcs:
            raise ValueError("Production witness has no concrete closed alternating walk")
        selected = witness["separated_after_selected"]
        for i, arc in enumerate(arcs):
            original = requirements[arc["requirement_index"]]
            if any(arc[k] != original[k] for k in ("preferred", "other")):
                raise ValueError("Witness arc is not a retained original strict requirement")
            join = joins[i]
            if join["negative"] != arc["other"] or join["positive"] != arcs[(i + 1) % len(arcs)]["preferred"]:
                raise ValueError("Witness equality join does not close the concrete walk")
            vectors = []
            for endpoint in (join["negative"], join["positive"]):
                vector = {**occurrences[endpoint], **{name: values[name][endpoint] for name in selected}}
                vectors.append(vector)
            if (not equal_vectors(*vectors) or not equal_vectors(vectors[0], join["negative_vector"])
                    or not equal_vectors(vectors[1], join["positive_vector"])):
                raise ValueError("Saved exact equality does not hold in full current interface")
        cover = sorted(name for name in costs if any(number(values[name][j["negative"]]) !=
                                                     number(values[name][j["positive"]]) for j in joins))
        if cover != witness["separating_features"]:
            raise ValueError("Witness cut membership differs from exact join separation")
        covers.append(cover)
        checks.append({"witness": witness["id"], "strict_arcs": len(arcs), "joins": len(joins),
                       "exact_equality_and_cover_verified": True, "separating_features": cover})
    master_checks, states_used = [], 0
    for round_index, row in enumerate(result["rounds"]):
        if row["cuts"] != covers[:round_index + 1]:
            raise ValueError("Master omitted or altered a concrete necessary cut")
        q = checker.check(row["selected_names"])
        if (q["acyclic"] == row["quotient"]["contradictory"] or
                any(q[k] != row["quotient"][k] for k in ("quotient_nodes", "quotient_edges", "self_loop_requirements"))):
            raise ValueError("Round did not recheck the same full quotient")
        if len(row["selected_names"]) > protocol["max_selected"]:
            raise ValueError("A master exceeded declaredK")
        exact_cost = sum(costs[name] for name in row["selected_names"])
        if exact_cost != Fraction(row["cost_exact"]):
            raise ValueError("Master additive cost differs")
        proof = independent_cut_master(row["cuts"], costs, protocol["max_selected"],
                                       max(0, protocol["independent_master_max_states_total_per_catalogue"] - states_used))
        states_used += proof["states"]
        if proof["complete"] and (not proof["feasible"] or Fraction(proof["cost_exact"]) != exact_cost):
            raise ValueError("Independent exact cut master disagrees with production cost")
        master_checks.append({"round": round_index, "full_quotient_verified": q, "independent_DP": proof})
    final = checker.check(result["selected_names"])
    if (final["acyclic"] == result["diagnosis"]["contradictory"] or
            any(final[k] != result["diagnosis"][k] for k in ("quotient_nodes", "quotient_edges", "self_loop_requirements"))):
        raise ValueError("Final production quotient differs from independent full rebuild")
    if sum(costs[name] for name in result["selected_names"]) != Fraction(result["cost_exact"]):
        raise ValueError("Final additive cost differs")
    enumeration = exhaustive_refinement(checker, costs, protocol["max_selected"],
                                        protocol["independent_exhaustive_max_subsets"]) if exhaustive else None
    if enumeration and enumeration["complete"] and result["optimal"]:
        if not enumeration["feasible"] or Fraction(enumeration["cost_exact"]) != Fraction(result["cost_exact"]):
            raise ValueError("Independent exhaustive catalogue optimum disagrees")
    final_master_proved = (not result["rounds"] and final["acyclic"]) or bool(
        master_checks and master_checks[-1]["independent_DP"]["complete"])
    verified = (result["optimal"] and result["repaired"] and final["acyclic"] and
                (bool(enumeration and enumeration["complete"] and enumeration["feasible"]) or final_master_proved))
    return {"cut_checks": checks, "round_checks": master_checks, "final_full_quotient": final,
            "independent_DP_states_total": states_used, "exhaustive": enumeration,
            "independently_verified_additive_minimum": bool(verified),
            "unresolved_production_is_never_relabelled_optimal": True}


def solve_catalogue(task):
    plan, occurrences, requirements, values, costs, protocol = task
    cpu, wall = time.process_time(), time.perf_counter()
    row = {"id": plan["id"], "catalogue_size": plan["catalogue_size"], "max_selected": protocol["max_selected"],
           "completed": False, "minimum_cost_claimed": False}
    try:
        result = minimum_cost_vector_refinement(occurrences, requirements, values, costs,
                   max_rounds=protocol["max_rounds"], max_master_subsets=protocol["max_master_subsets"],
                   max_selected=protocol["max_selected"])
        production_cpu, production_wall = time.process_time() - cpu, time.perf_counter() - wall
        audit = audit_refinement(result, occurrences, requirements, values, costs, protocol,
                                 plan["independent_exhaustive_crosscheck"])
        row.update(completed=True, status="resolved_additive_minimum" if result["optimal"] else "unresolved",
                   production=result, audit=audit, minimum_cost_claimed=bool(result["optimal"]),
                   production_CPU_seconds=production_cpu, production_wall_seconds=production_wall)
    except Exception as error:
        row.update(status="refinement_or_independent_audit_failure", error_type=type(error).__name__, error=str(error))
        if "result" in locals():
            row["production"] = result
    row.update(CPU_seconds=time.process_time() - cpu, wall_seconds=time.perf_counter() - wall)
    return row


def verify_study(study):
    protocol, freeze = read(study / "protocol.json"), read(study / "freeze_receipt.json")
    if (protocol["version"] != VERSION or protocol["test_accessed"] or protocol["selection_split"] != "train"
            or freeze["protocol_sha256"] != digest(study / "protocol.json")
            or not freeze["before_feature_evaluation_and_master"]):
        raise ValueError("Missing or changed pre-evaluation registration")
    for name, expected in protocol["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen capsule source changed: " + name)
    for name, expected in freeze["input_sha256"].items():
        if digest(study / name) != expected:
            raise ValueError("Frozen capsule input changed: " + name)
    return protocol


def execute(study, output, workers):
    study, output = Path(study), Path(output)
    if output.exists():
        raise ValueError("Never overwrite or resume a scientific assignment inventory")
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError("This protocol permits one to eight graph-feature workers")
    protocol = verify_study(study)
    catalogue = read(study / "catalogue.json")["catalogue"]
    if len(catalogue) != protocol["catalogue_size"]:
        raise ValueError("Frozen catalogue size differs")
    frame = endpoint_frame(read(study / "training_evidence.json"))
    output.mkdir(parents=True)
    write(output / "execution.json", {"utc": utc(), "workers": workers, "python": platform.python_version(),
          "platform": platform.platform(), "protocol_sha256": digest(study / "protocol.json"),
          "source_sha256": protocol["source_sha256"], "TEST_accessed": False,
          "R2_authoring_or_selector_consumption": False})
    feature_rows = {}
    tasks = [(None, protocol["feature_limits"])] + [(entry, protocol["feature_limits"]) for entry in catalogue]
    with (output / "feature_rows.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=workers, initializer=init_feature_worker,
                                 initargs=(str(study / "training_evidence.json"),)) as pool:
            futures = {pool.submit(evaluate_feature, task): "base9" if task[0] is None else task[0]["name"] for task in tasks}
            for future in as_completed(futures):
                identity = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    row = {"id": identity, "completed": False, "status": "feature_worker_failure",
                           "error_type": type(error).__name__, "error": str(error), "values": {}}
                feature_rows[identity] = row
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); stream.flush()
                write(output / "progress.json", {"phase": "standalone_features", "assigned": len(tasks),
                      "returned": len(feature_rows), "completed": sum(r["completed"] for r in feature_rows.values())})
    base = feature_rows["base9"]
    results, pending = [], []
    for plan in protocol["catalogue_plans"]:
        bad = [name for name in ["base9"] + plan["names"] if not feature_rows[name]["completed"]]
        if bad:
            results.append({"id": plan["id"], "catalogue_size": plan["catalogue_size"], "completed": False,
                            "status": "unresolved_incomplete_feature_values", "failed_assignments": bad,
                            "minimum_cost_claimed": False})
            continue
        values = {name: feature_rows[name]["values"] for name in plan["names"]}
        costs = {name: feature_rows[name]["positive_additive_cost"] for name in plan["names"]}
        pending.append((plan, base["values"], frame["requirements"], values, costs, protocol))
    with (output / "results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in results:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        if pending:
            with ProcessPoolExecutor(max_workers=min(workers, len(pending))) as pool:
                futures = {pool.submit(solve_catalogue, task): task[0] for task in pending}
                for future in as_completed(futures):
                    plan = futures[future]
                    try:
                        row = future.result()
                    except Exception as error:
                        row = {"id": plan["id"], "catalogue_size": plan["catalogue_size"], "completed": False,
                               "status": "catalogue_worker_failure", "error_type": type(error).__name__,
                               "error": str(error), "minimum_cost_claimed": False}
                    results.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); stream.flush()
                    write(output / "progress.json", {"phase": "catalogue_master", "assigned": 4,
                          "returned": len(results), "completed_execution": sum(r["completed"] for r in results),
                          "resolved_additive_minimum": sum(r.get("minimum_cost_claimed", False) for r in results)})
    write(output / "complete.json", {"all_assignments_returned": len(feature_rows) == len(tasks) and len(results) == 4,
          "all_assignment_completion_is_not_solver_success": True,
          "feature_assignments": len(tasks), "feature_completed": sum(r["completed"] for r in feature_rows.values()),
          "catalogue_assignments": 4, "catalogue_execution_completed": sum(r["completed"] for r in results),
          "catalogue_status_counts": dict(Counter(r["status"] for r in results)),
          "protocol_sha256": digest(study / "protocol.json"), "feature_rows_sha256": digest(output / "feature_rows.jsonl"),
          "results_sha256": digest(output / "results.jsonl"), "execution_sha256": digest(output / "execution.json"),
          "TEST_accessed": False, "R2_authoring_or_selector_consumption": False})
    return {"output": str(output), "feature_rows": len(feature_rows), "catalogue_rows": len(results),
            "complete_sha256": digest(output / "complete.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--study", required=True)
    prep.add_argument("--results", default="experiments/discovery/v06_synthesis_server_001/llm/candidate_results.jsonl")
    prep.add_argument("--evidence", default="experiments/discovery/v06_authoring_001/training_evidence.json")
    run = sub.add_parser("execute")
    run.add_argument("--study", required=True); run.add_argument("--out", required=True)
    run.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    result = prepare(args.study, args.results, args.evidence) if args.action == "prepare" else execute(args.study, args.out, args.workers)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
