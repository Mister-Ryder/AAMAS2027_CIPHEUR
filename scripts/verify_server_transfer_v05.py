"""Independent, read-only audit of V05 server replay and cross-host identity.

No project execution/semantic modules, LLM, oracle, or policy rollout is used.
The older independent verifier supplies graph views and typed-expression
interpretation. Every saved trace is replayed as vertex deletion and checked
with exact reward arithmetic. Small predetermined first states receive bounded
first-argmax verification, never repair or replacement of an observed result.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_matched_llm_v05 import boundary, check_schedule, FeatureView, first_action
from scripts.verify_public_alias_v05 import read_members, graph_digest, view

ROOT = Path(__file__).resolve().parents[1]
STEM = "matched_transfer_server_v05_001"
STUDY = ROOT / "experiments/discovery" / STEM
CAPSULE = ROOT / "experiments/source_snapshots/v05" / (STEM + "_source.zip")
ARMS = ("witness", "relations", "objective")
COUNTS = {"DIMACS_unit": 18, "DIMACS_hash_weighted": 18,
          "SATLIB_unit": 30, "SATLIB_hash_weighted": 30, "C3": 24}
PINNED_PROTOCOL = "492ea9d3c94228c1a86c00a8f7b9b1e8f9f2489f16ec04d833a99abd64e2debc"
PINNED_CAPSULE = "b04c965d4bce9b942f4544e2570db28122eacc73b9a5f473854d784c4e1ab9b4"
FIRST_POLICY = {"eligible_max_vertices": 300, "eligible_max_edges": 15000,
                "contexts_per_population": 2, "order": "graph_sha256, then context ID",
                "verification_process_cpu_seconds_per_assignment": 2,
                "scope": "Only a first-state argmax; no later scores or policy rollouts."}


def digest(raw):
    return sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


class VerificationLimit(RuntimeError):
    pass


class BoundedFeatureView(FeatureView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deadline = time.process_time() + FIRST_POLICY["verification_process_cpu_seconds_per_assignment"]

    def operation(self, *args, **kwargs):
        if time.process_time() > self.deadline:
            raise VerificationLimit("Independent first-score CPU ceiling")
        return super().operation(*args, **kwargs)

    def features(self, *args, **kwargs):
        if time.process_time() > self.deadline:
            raise VerificationLimit("Independent first-score CPU ceiling")
        return super().features(*args, **kwargs)


def expected_context(row, graph, source, population):
    keys = ("id", "pair_id", "side", "split", "family", "cluster", "n", "m",
            "graph_sha256", "fixed", "excluded")
    refkeys = ("formal_upper_exact", "formal_upper_method", "clique_partition",
               "best_verified_lower_exact", "lower_witness", "lower_witness_method")
    return {**{k: row[k] for k in keys}, "graph": graph, "source": source,
            "population": population, "reference": {k: row["reference"][k] for k in refkeys}}


def audit_cross_host(raw, protocol, require):
    """Recompute paired identity and compare receipts without importing runners."""
    old_stem = "matched_transfer_exploratory_v05_001"
    old_study = ROOT / "experiments/discovery" / old_stem
    old_archive = ROOT / "experiments/runs/v05" / (old_stem + ".tar.gz")
    server_archive = ROOT / "experiments/runs/v05" / (STEM + ".tar.gz")
    old_capsule = ROOT / "experiments/source_snapshots/v05" / (old_stem + "_source.zip")
    comparison = ROOT / "experiments/analysis/v05/matched_transfer_cross_host_v05_001.json"
    local = read_members(old_archive, ("protocol.json", "data.json", "frozen_programs.json",
                                       "results.jsonl", "complete.json"))
    require(protocol["replay_of"] == old_stem and protocol["same_complete_assignment_inventory"]
            and digest(old_archive.read_bytes()) == protocol["original_local_archive_sha256"]
            == "4b4888820ac71797aa5f1e05980f0216fd94acac2f9e17f65340001fdc8536a2",
            "original_local_archive_and_replay_contract", "local")
    require(digest(old_capsule.read_bytes()) == protocol["original_local_source_zip_sha256"]
            and digest(local["protocol.json"]) == protocol["original_local_protocol_sha256"]
            and local["protocol.json"] == (old_study / "protocol.json").read_bytes(),
            "original_local_protocol_and_capsule_binding", "local")
    for name in ("data.json", "frozen_programs.json"):
        require(raw[name] == local[name] == (old_study / name).read_bytes(),
                "cross_host_exact_input_and_AST_bytes", name)
    require(raw["budget_scope_clarification.json"] == (old_study / "budget_scope_clarification.json").read_bytes(),
            "copied_append_only_local_budget_scope_not_rewritten", "clarification")
    with zipfile.ZipFile(old_capsule) as old, zipfile.ZipFile(CAPSULE) as new:
        old_members, new_members = set(old.namelist()), set(new.namelist())
        semantic_files = sorted(n for n in old_members if n.startswith("cipheur/") and n.endswith(".py"))
        for name in semantic_files + ["scripts/matched_transfer_exploratory_v05.py"]:
            require(name in new_members and old.read(name) == new.read(name),
                    "cross_host_original_runner_and_semantic_module_identity", name)
        runner = "scripts/matched_transfer_exploratory_v05.py"
        require(digest(new.read(runner)) == protocol["original_local_runner_sha256"],
                "wrapper_original_runner_pin", runner)
        wrapper_ast = ast.parse(new.read("scripts/matched_transfer_server_v05.py"))
        config = next(n for n in wrapper_ast.body if isinstance(n, ast.FunctionDef) and n.name == "configure")
        assigned = [n for n in config.body if isinstance(n, ast.Assign)]
        targets = [a.attr for n in assigned for t in n.targets for a in t.elts]
        require(len(config.body) == 2 and targets == ["STEM", "STUDY", "CAPSULE", "CAPSULE_RECEIPT", "CONFIG"],
                "wrapper_configuration_changes_storage_globals_only", "configure")
        run = next(n for n in wrapper_ast.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        calls = [n for n in ast.walk(run) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                 and n.func.value.id == "original" and n.func.attr == "run"]
        require(len(calls) == 1 and [a.id for a in calls[0].args] == ["output", "stable_root"]
                and not calls[0].keywords,
                "wrapper_dispatches_original_run_unmodified_arguments", "run")

    execution = json.loads(raw["execution.json"])
    complete = json.loads(raw["complete.json"])
    host = execution["server_host_receipt"]
    prior = ROOT / "experiments/runs/v05/matched_eval_v05_001.tar.gz"
    require(execution["workers"] == host["workers"] == protocol["workers"] == 8
            and execution["platform"] == host["platform"] and execution["python"] == host["python"]
            and host["python"].startswith("3.11.17") and host["platform"].startswith("Linux-")
            and host["python_executable"].endswith("/py311/bin/python"),
            "recorded_server_runtime_and_workers", "host")
    quota, period = map(int, host["cgroup"]["/sys/fs/cgroup/cpu.max"].split())
    require(quota / period == 16 and host["cpu_count"] == 192 and host["affinity_count"] == 192,
            "recorded_server_quota_and_affinity", "host")
    require(host["existing_server_matched_2808_archive_sha256"]
            == protocol["prior_matched_2808_archive_sha256"] == digest(prior.read_bytes())
            == "acb6eb5eef6bbe0b3f8b3a0e908d558318e1f0768c34261dfa98fe35f8dac680",
            "prior_matched_2808_existing_server_local_archive_identity", "host")
    require(host["C3_csv_sha256"] == "ec95f50c11d800f051e218aa1e414df873ddd12e1f71ce911da3ba28adff647e"
            and execution["original_local_archive_sha256"] == protocol["original_local_archive_sha256"]
            and execution["cross_host_replay_of"] == old_stem,
            "server_C3_source_and_original_archive_metadata", "host")
    package_raw = read_members(server_archive, ("packaging_receipt.json",))["packaging_receipt.json"]
    package = json.loads(package_raw)
    require(package["execution_and_validation_finished_before_packaging"]
            and package["source_capsule_and_runner_unchanged"] and package["assignments_reexecuted"] == 0
            and package["results_sha256_before_after"] == digest(raw["results.jsonl"])
            and package["validation_sha256_before_after"] == digest(raw["validation.json"])
            and package["complete_sha256"] == digest(raw["complete.json"]),
            "post_execution_packaging_only_and_output_hashes", "packaging")
    require(json.loads(raw["validation.json"])["errors"] == 0 and complete["hard_wall_safety_triggered"] is False,
            "executed_validation_and_no_safety_interrupt", "complete")

    def assignments(content):
        result = {}
        for line in content.splitlines():
            context = json.loads(line)
            for row in context["rows"]:
                key = (context["id"], row["method"])
                require(key not in result, "cross_host_unique_assignment", str(key))
                result[key] = row
        return result

    left, right = assignments(local["results.jsonl"]), assignments(raw["results.jsonl"])
    require(left.keys() == right.keys() and len(left) == len(right) == 1560,
            "all_1560_cross_host_pair_keys", "comparison")
    counts, per_method, differences = Counter(), defaultdict(Counter), []
    for key in sorted(left):
        a, b = left[key], right[key]
        category = ("both_complete" if a["completed"] and b["completed"] else
                    "local_only_complete" if a["completed"] else
                    "server_only_complete" if b["completed"] else "neither_complete")
        counts[category] += 1
        per_method[key[1]][category] += 1
        if a["completed"] and b["completed"]:
            equality = {"exact_reward": a["value_exact"] == b["value_exact"],
                        "selected_set": a["selected"] == b["selected"],
                        "decision_trace": a["trace"] == b["trace"],
                        "trace_choices_counts": [(t["selected"], t["remaining_count"]) for t in a["trace"]]
                            == [(t["selected"], t["remaining_count"]) for t in b["trace"]]}
            for field, equal in equality.items():
                counts[field + ("_equal" if equal else "_different")] += 1
                require(equal, "jointly_completed_" + field + "_identity", str(key))
            if not all(equality.values()):
                differences.append({"context": key[0], "method": key[1],
                    "kind": "both_complete_semantic_or_score_difference", "equal": equality,
                    "local_value_exact": a["value_exact"], "server_value_exact": b["value_exact"]})
        elif a["completed"] != b["completed"] or a["status"] != b["status"]:
            differences.append({"context": key[0], "method": key[1],
                "kind": "completion_or_failure_difference", "local_status": a["status"],
                "server_status": b["status"], "local_cpu_seconds": a["cpu_seconds"],
                "server_cpu_seconds": b["cpu_seconds"]})
    observed = load(comparison)
    require(observed["assignment_pairs"] == 1560 and observed["counts"] == dict(counts)
            and observed["per_method_completion"] == {k: dict(v) for k, v in per_method.items()}
            and observed["all_differences"] == differences,
            "independent_cross_host_aggregate_and_every_difference", "comparison")
    require(observed["local_archive_sha256"] == digest(old_archive.read_bytes())
            and observed["server_archive_sha256"] == digest(server_archive.read_bytes())
            and observed["data_sha256"] == digest(raw["data.json"])
            and observed["frozen_programs_sha256"] == digest(raw["frozen_programs.json"]),
            "publisher_cross_host_archive_input_binding", "comparison")
    return {"counts": dict(counts), "per_method_completion": {k: dict(v) for k, v in per_method.items()},
            "all_differences": differences, "local_archive_sha256": digest(old_archive.read_bytes()),
            "comparison_sha256": digest(comparison.read_bytes()),
            "packaging_receipt_sha256": digest(package_raw), "server_host_receipt": host,
            "source_scope": "Identical prior-observed graphs and TRAIN winners; not independent fresh evidence.",
            "runtime_scope": "Recorded host-specific CPU/wall, not independently remeasured or causally attributed."}


def audit(archive, analysis, output, provenance_only=False):
    checks, errors = Counter(), []
    def require(condition, kind, where):
        checks[kind] += 1
        if not condition:
            errors.append({"kind": kind, "where": where})

    start = time.perf_counter()
    protocol = load(STUDY / "protocol.json")
    freeze = load(STUDY / "freeze_receipt.json")
    frozen = load(STUDY / "frozen_programs.json")
    contexts = load(STUDY / "data.json")["contexts"]
    require(digest((STUDY / "protocol.json").read_bytes()) == PINNED_PROTOCOL,
            "original_protocol_pin", "protocol")
    require(digest(CAPSULE.read_bytes()) == PINNED_CAPSULE, "original_source_capsule_pin", "capsule")
    require(freeze["before_any_extension_execution"] and protocol["before_any_extension_execution"]
            and protocol["no_authoring_no_test_selection"] and protocol["all_assigned_banks_retained"],
            "fixed_exploratory_contract", "protocol")
    require(protocol["contexts"] == 120 and protocol["assignments"] == 1560
            and protocol["methods_per_context"] == 13 and protocol["population_counts"] == COUNTS,
            "registered_population_and_budget", "protocol")
    require(protocol["program_cpu_seconds"] == 5 and protocol["workers"] == 8
            and protocol["hard_wall_safety_no_context_progress_seconds"] == 1800,
            "fixed_execution_budget", "protocol")
    for name in ("protocol", "data", "frozen_programs"):
        value = digest((STUDY / (name + ".json")).read_bytes())
        require(value == freeze[name + "_sha256"], "registered_input_bytes", name)
        if name != "protocol":
            require(value == protocol[name + "_sha256"], "protocol_input_bytes", name)
    receipt_path = CAPSULE.with_name(STEM + "_source_receipt.json")
    receipt = load(receipt_path)
    require(receipt["source_zip_sha256"] == PINNED_CAPSULE and receipt["before_any_extension_execution"],
            "source_receipt_pin", "receipt")
    with zipfile.ZipFile(CAPSULE) as z:
        require(set(z.namelist()) == set(receipt["file_sha256"]), "complete_capsule_inventory", "zip")
        for name, value in receipt["file_sha256"].items():
            require(digest(z.read(name)) == value == digest((ROOT / name).read_bytes()),
                    "unchanged_source_and_capsule_bytes", name)
        for name, value in freeze["source_sha256"].items():
            require(digest(z.read(name)) == value, "preexecution_source_freeze", name)
        for name, value in frozen["source_sha256"].items():
            require(digest(z.read("cipheur/" + name)) == value,
                    "unchanged_original_matched_semantics", name)
        execute_ast = next(n for n in ast.parse(z.read("cipheur/matched_synthesis_v05.py"))
                           .body if isinstance(n, ast.FunctionDef) and n.name == "execute")
        call = execute_ast.body[1].body[0].value
        parser = call.args[1]
        meter = next(k.value for k in call.keywords if k.arg == "meter")
        require(isinstance(parser, ast.Call) and isinstance(parser.func, ast.Attribute)
                and isinstance(parser.func.value, ast.Name) and parser.func.value.id == "FeatureRuleProgram"
                and parser.func.attr == "from_dict" and isinstance(meter, ast.Call)
                and isinstance(meter.func, ast.Name) and meter.func.id == "_Meter",
                "independent_source_parse_before_meter_argument_order", "execute")
        timers = execute_ast.body[0].value
        require(isinstance(timers, ast.Tuple) and [n.func.attr for n in timers.elts]
                == ["perf_counter", "process_time"],
                "independent_source_actual_timers_before_AST_parse", "execute")
        meter_ast = next(n for n in ast.parse(z.read("cipheur/relevance_synthesis_v04.py"))
                         .body if isinstance(n, ast.ClassDef) and n.name == "_Meter")
        init = next(n for n in meter_ast.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        deadline = init.body[1].value
        writer = next(n for n in meter_ast.body if isinstance(n, ast.FunctionDef) and n.name == "__setitem__")
        guard = writer.body[1].test
        require(isinstance(deadline, ast.BinOp) and isinstance(deadline.op, ast.Add)
                and deadline.left.func.attr == "process_time" and deadline.right.id == "seconds"
                and isinstance(guard, ast.BoolOp) and isinstance(guard.op, ast.And)
                and guard.values[0].left.right.value == 128,
                "independent_source_cooperative_CPU_deadline_every_128_writes", "meter")

    source_names = {"public": "advanced_public_v04_001", "fresh": "advanced_fresh_v04_001",
                    "train": "matched_train_v05_001"}
    original, original_raw = {}, {}
    for label, stem in source_names.items():
        version = "v05" if label == "train" else "v04"
        path = ROOT / "experiments/runs" / version / (stem + ".tar.gz")
        require(digest(path.read_bytes()) == protocol["source_archive_sha256"][label],
                "original_source_archive_identity", label)
        names = ("frozen_programs.json",) if label == "train" else ("data.json", "results.jsonl")
        raw = read_members(path, names)
        original_raw[label] = raw
        original[label] = {name: ([json.loads(l) for l in value.splitlines() if l]
                                 if name.endswith(".jsonl") else json.loads(value))
                           for name, value in raw.items()}
    require((STUDY / "frozen_programs.json").read_bytes() == original_raw["train"]["frozen_programs.json"],
            "exact_original_train_winner_bytes", "frozen")
    expected_programs = {f"block_{b}_{a}" for b in range(4) for a in ARMS}
    require(set(frozen["programs"]) == set(frozen["selection"]) == expected_programs
            and set(protocol["programs"]) == expected_programs,
            "all_twelve_winner_banks_no_deduplication", "frozen")
    require(frozen["selection_split"] == "train" and frozen["test_accessed"] is False,
            "original_train_only_selection", "frozen")
    programs = {**frozen["programs"], "Degree": protocol["reference_program"]}
    expected = []
    for label in ("public", "fresh"):
        oldrows = {r["id"]: r for r in original[label]["results.jsonl"]}
        olddata = original[label]["data.json"]
        if label == "public":
            for item in olddata["public"]:
                pop = item["family"] + "_" + item["source"]["weight_mode"]
                expected.append(expected_context(oldrows[item["id"] + ":graph"], item["graph"], item["source"], pop))
        else:
            for item in olddata["test"]:
                if item["family"] == "c3":
                    for side in ("left", "right"):
                        expected.append(expected_context(oldrows[item["id"] + ":" + side],
                                                         item[side], item["source"], "C3"))
    expected.sort(key=lambda c: c["id"])
    require(contexts == expected, "all_original_graph_source_boundary_U_L_identity", "data")
    require(len(contexts) == len({c["id"] for c in contexts}) == 120
            and dict(Counter(c["population"] for c in contexts)) == COUNTS,
            "all_120_preserved_source_contexts", "data")
    source_csv = Path("E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/data/C3.csv")
    source_csv_sha256 = digest(source_csv.read_bytes())
    for c in contexts:
        if c["population"] == "C3":
            require(c["source"]["source_data_sha256"] == c["graph"]["provenance"]["source_data_sha256"]
                    == source_csv_sha256
                    and c["source"]["original_ids"] == c["graph"]["provenance"]["original_ids"],
                    "original_C3_source_csv_bytes_and_contact_ids", c["id"])

    for c in contexts:
        where = c["id"]
        nodes, edges, adj = view(c["graph"])
        require(graph_digest(c["graph"]) == c["graph_sha256"] and len(nodes) == c["n"] and len(edges) == c["m"],
                "independent_graph_identity", where)
        require(all(math.isfinite(v["weight"]) and v["weight"] > 0 for v in nodes.values()),
                "positive_finite_graph_weights", where)
        active = boundary(nodes, adj, c["fixed"], c["excluded"])
        cover = c["reference"]["clique_partition"]
        members = [v for part in cover for v in part]
        require(len(members) == len(set(members)) and set(members) == active,
                "independent_upper_partition_domain", where)
        for part in cover:
            require(bool(part), "nonempty_upper_clique", where)
            for i, a in enumerate(part):
                for b in part[i+1:]:
                    require(b in adj[a], "independent_upper_clique_edges", where + ":" + a + ":" + b)
        upper = sum((Fraction(nodes[v]["weight"]) for v in c["fixed"]), Fraction())
        upper += sum((max(Fraction(nodes[v]["weight"]) for v in part) for part in cover), Fraction())
        require(upper == Fraction(c["reference"]["formal_upper_exact"]) and upper > 0,
                "exact_original_upper_denominator", where)
        lower = c["reference"]["lower_witness"]
        require(len(lower) == len(set(lower)) and set(lower) <= nodes.keys()
                and not any(adj[v] & set(lower) for v in lower)
                and set(c["fixed"]) <= set(lower) and not set(c["excluded"]) & set(lower),
                "independent_prior_lower_witness_feasibility", where)
        value = sum((Fraction(nodes[v]["weight"]) for v in lower), Fraction())
        require(value == Fraction(c["reference"]["best_verified_lower_exact"]) and 0 < value <= upper,
                "exact_original_lower_denominator", where)

    subset = []
    for population in sorted(COUNTS):
        eligible = [c for c in contexts if c["population"] == population
                    and c["n"] <= FIRST_POLICY["eligible_max_vertices"]
                    and c["m"] <= FIRST_POLICY["eligible_max_edges"]]
        subset.extend(sorted(eligible, key=lambda c: (c["graph_sha256"], c["id"]))[:FIRST_POLICY["contexts_per_population"]])
    first_ids = {c["id"] for c in subset}
    provisional = {"checks": dict(checks), "errors": errors, "first_argmax_policy": FIRST_POLICY,
                   "first_argmax_context_ids": sorted(first_ids), "contexts": COUNTS}
    if provenance_only:
        print(json.dumps(provisional, indent=2), flush=True)
        if errors:
            raise SystemExit(1)
        return

    archive = Path(archive)
    require(digest(archive.read_bytes()) == "3bf2197f96206411354930a4c2c042ea393bc9f63808f1a08d0c4a78cb8b2c31",
            "downloaded_server_archive_pin", "archive")
    raw = read_members(archive, ("protocol.json", "data.json", "frozen_programs.json", "freeze_receipt.json",
                                 "execution.json", "results.jsonl", "validation.json", "complete.json",
                                 "budget_scope_clarification.json"))
    obj = {name: ([json.loads(l) for l in value.splitlines() if l] if name.endswith(".jsonl") else json.loads(value))
           for name, value in raw.items()}
    for name in ("protocol.json", "data.json", "frozen_programs.json", "freeze_receipt.json", "budget_scope_clarification.json"):
        require(raw[name] == (STUDY / name).read_bytes(), "unchanged_archived_inputs_and_clarification", name)
    execution, complete = obj["execution.json"], obj["complete.json"]
    require(execution["protocol_sha256"] == complete["protocol_sha256"] == PINNED_PROTOCOL
            and execution["source_zip_sha256"] == complete["source_zip_sha256"] == PINNED_CAPSULE,
            "executed_frozen_protocol_source_binding", "execution")
    require(datetime.fromisoformat(freeze["created_utc"].replace("Z", "+00:00"))
            <= datetime.fromisoformat(execution["started_utc"].replace("Z", "+00:00")),
            "registration_precedes_execution_timestamp", "execution")
    clarification = obj["budget_scope_clarification.json"]
    require(clarification["original_protocol_sha256"] == protocol["original_local_protocol_sha256"]
            and clarification["source_zip_sha256"] == protocol["original_local_source_zip_sha256"]
            and clarification["code_execution_backend_budget_unchanged"]
            and clarification["clarification_before_analysis"]
            and clarification["new_result_rewards_accessed_for_this_clarification"] is False,
            "append_only_honest_meter_scope_clarification", "clarification")
    require(complete["complete"] and complete["contexts"] == 120 and complete["assignments"] == 1560
            and complete["results_sha256"] == digest(raw["results.jsonl"])
            and complete["validation_sha256"] == digest(raw["validation.json"])
            and complete["frozen_programs_sha256"] == protocol["frozen_programs_sha256"],
            "complete_raw_archive_binding", "complete")
    results = obj["results.jsonl"]
    require(len(results) == len({r["id"] for r in results}) == 120
            and {r["id"] for r in results} == {c["id"] for c in contexts},
            "complete_context_result_coverage", "results")
    result_by_id = {r["id"]: r for r in results}
    qualities, lowers, completed_by_method, failures = {}, {}, Counter(), Counter()
    first_checked, first_skipped = [], []
    for c in contexts:
        result = result_by_id[c["id"]]
        require(result["graph_sha256"] == c["graph_sha256"] and result["population"] == c["population"]
                and result["n"] == c["n"] and result["m"] == c["m"],
                "result_original_graph_identity", c["id"])
        require(len(result["rows"]) == 13 and {r["method"] for r in result["rows"]} == set(programs),
                "all_13_assigned_methods_retained", c["id"])
        methods = sorted(programs)
        shift = int(c["graph_sha256"][:8], 16) % len(methods)
        if "method_order" in result:
            require(result["method_order"] == methods[shift:] + methods[:shift]
                    and [r["method"] for r in result["rows"]] == result["method_order"],
                    "registered_outcome_free_execution_order", c["id"])
        for row in result["rows"]:
            name, where = row["method"], c["id"] + ":" + row["method"]
            check_schedule(row, c, require, where)
            if row["completed"]:
                require(row["status"] == "completed", "completed_status_consistency", where)
                value = Fraction(row["value_exact"])
                require(value <= Fraction(c["reference"]["formal_upper_exact"]),
                        "completed_reward_below_prior_upper", where)
                q, l = (100 * float(value / Fraction(c["reference"][field])) for field in
                        ("formal_upper_exact", "best_verified_lower_exact"))
                completed_by_method[name] += 1
                if c["id"] in first_ids and row["trace"]:
                    try:
                        choice, score = first_action(programs[name], BoundedFeatureView(c["graph"], c["fixed"], c["excluded"]))
                        require(row["trace"][0]["selected"] == choice and row["trace"][0]["score"] == score,
                                "independent_bounded_first_argmax", where)
                        first_checked.append(where)
                    except VerificationLimit as exc:
                        first_skipped.append({"assignment": where, "reason": str(exc)})
                    except (TypeError, ValueError, ArithmeticError, RecursionError) as exc:
                        require(False, "independent_first_score_interpreter_error", where + ":" + type(exc).__name__)
            else:
                require(row["status"] != "completed", "failure_status_consistency", where)
                q = l = 0.0
                failures[row["status"]] += 1
                if c["id"] in first_ids:
                    first_skipped.append({"assignment": where, "reason": "Executed assignment incomplete; retained zero quality."})
            for field in ("cpu_seconds", "wall_seconds"):
                require(row[field] is None or isinstance(row[field], (int, float))
                        and math.isfinite(row[field]) and row[field] >= 0,
                        "executed_nonnegative_or_unknown_timing", where + ":" + field)
            qualities[c["id"], name], lowers[c["id"], name] = q, l
    require(sum(completed_by_method.values()) == complete["completed_assignments"]
            and dict(failures) == complete["failure_status_counts"]
            and len(qualities) == len(lowers) == 1560,
            "all_assignment_failures_and_completion_accounted", "complete")

    analysis = Path(analysis)
    published = load(analysis)
    require(published["exploratory"] and published["protocol_sha256"] == PINNED_PROTOCOL
            and published["source_zip_sha256"] == PINNED_CAPSULE
            and published["archive_sha256"] == digest(archive.read_bytes()),
            "publisher_analysis_archive_binding", "analysis")
    summaries = {}
    for population in COUNTS:
        cases = [c for c in contexts if c["population"] == population]
        published_pop = published["populations"][population]
        require(published_pop["contexts"] == len(cases) and published_pop["context_ids"] == [c["id"] for c in cases],
                "analysis_original_context_inventory", population)
        summary = {"contexts": len(cases), "arms": {}, "degree": {}}
        for name in sorted(programs):
            q = [qualities[c["id"], name] for c in cases]
            l = [lowers[c["id"], name] for c in cases]
            rows = [next(r for r in result_by_id[c["id"]]["rows"] if r["method"] == name) for c in cases]
            m = published_pop["methods"][name]
            require(m["quality_to_upper_percent"] == q and m["quality_to_prior_feasible_percent"] == l
                    and m["mean_quality_to_formal_upper_percent"] == statistics.mean(q)
                    and m["mean_quality_to_prior_best_feasible_percent"] == statistics.mean(l)
                    and m["assigned"] == len(cases) and m["completed"] == sum(r["completed"] for r in rows),
                    "independent_failure_zero_per_method_quality", population + ":" + name)
            require(m["failure_status_counts"] == dict(Counter(r["status"] for r in rows if not r["completed"])),
                    "per_method_uncensored_failure_counts", population + ":" + name)
            known_cpu = [r["cpu_seconds"] for r in rows if r["cpu_seconds"] is not None]
            known_wall = [r["wall_seconds"] for r in rows if r["wall_seconds"] is not None]
            require(m["known_timing_assignments"] == len(known_cpu)
                    and m["mean_cpu_seconds_all_known_assignments"] == (statistics.mean(known_cpu) if known_cpu else None)
                    and m["mean_wall_seconds_all_known_assignments"] == (statistics.mean(known_wall) if known_wall else None),
                    "all_known_timing_receipts_not_only_successes", population + ":" + name)
            if name == "Degree":
                summary["degree"] = {"mean_percent_U": statistics.mean(q), "mean_percent_L": statistics.mean(l),
                                      "assigned": len(cases), "completed": sum(r["completed"] for r in rows)}
                require(published_pop["degree"] == m, "common_degree_reference_not_replicated_blocks", population)
        for arm in ARMS:
            block_upper = [statistics.mean(qualities[c["id"], f"block_{b}_{arm}"] for c in cases) for b in range(4)]
            block_lower = [statistics.mean(lowers[c["id"], f"block_{b}_{arm}"] for c in cases) for b in range(4)]
            assigned = 4 * len(cases)
            completed = sum(next(r["completed"] for r in result_by_id[c["id"]]["rows"]
                                 if r["method"] == f"block_{b}_{arm}") for c in cases for b in range(4))
            a = published_pop["arms"][arm]
            require(a["block_quality_to_formal_upper_percent"] == block_upper
                    and a["block_quality_to_prior_best_feasible_percent"] == block_lower
                    and a["equal_block_mean_quality_to_formal_upper_percent"] == statistics.mean(block_upper)
                    and a["equal_block_mean_quality_to_prior_best_feasible_percent"] == statistics.mean(block_lower)
                    and a["assigned"] == assigned and a["completed"] == completed,
                    "independent_all_four_equal_block_arm_means", population + ":" + arm)
            summary["arms"][arm] = {"block_percent_U": block_upper, "mean_percent_U": statistics.mean(block_upper),
                                    "block_percent_L": block_lower, "mean_percent_L": statistics.mean(block_lower),
                                    "assigned": assigned, "completed": completed}
        summary["contrasts_pp"] = {f"{a}_minus_{b}_pp": summary["arms"][a]["mean_percent_U"] - summary["arms"][b]["mean_percent_U"]
                                    for a, b in (("witness", "relations"), ("witness", "objective"), ("relations", "objective"))}
        require(summary["contrasts_pp"] == published_pop["contrasts"], "independent_descriptive_arm_contrasts", population)
        summaries[population] = summary

    report = {"version": "matched_transfer_server_independent_audit_v05_001", "archive": str(archive),
              "archive_sha256": digest(archive.read_bytes()), "protocol_sha256": PINNED_PROTOCOL,
              "source_zip_sha256": PINNED_CAPSULE, "data_sha256": protocol["data_sha256"],
              "frozen_programs_sha256": protocol["frozen_programs_sha256"],
              "original_source_archive_sha256": protocol["source_archive_sha256"],
              "original_C3_csv_sha256": source_csv_sha256,
              "budget_scope_clarification_sha256": digest(raw["budget_scope_clarification.json"]),
              "publisher_analysis_sha256": digest(analysis.read_bytes()),
              "audit_script_sha256": digest(Path(__file__).read_bytes()),
              "independent_helper_sha256": {name: digest((ROOT / "scripts" / name).read_bytes())
                    for name in ("verify_matched_llm_v05.py", "verify_public_alias_v05.py")},
              "checks": dict(checks), "errors": errors, "elapsed_wall_seconds": time.perf_counter() - start,
              "contexts": COUNTS, "assignments": len(qualities), "completed_assignments": sum(completed_by_method.values()),
              "failure_status_counts": dict(failures), "first_argmax_policy": FIRST_POLICY,
              "first_argmax_context_ids": sorted(first_ids), "first_argmax_checked": first_checked,
              "first_argmax_skipped": first_skipped, "independent_summaries": summaries,
              "cross_host": audit_cross_host(raw, protocol, require),
              "scope": ["Exploratory transfer on repeated, prior-observed V04 graphs; not new confirmatory held-out instances.",
                        "All twelve original TRAIN-selected ASTs retained, including identical deployment ASTs. No new authoring or test selection.",
                        "Every complete saved trace independently checked for boundary, feasibility, complete deletion and exact reward; later scores not rerun.",
                        "Every original U clique partition and L feasible witness checked independently; U is not an exact optimum and L may be exceeded.",
                        "Four generation blocks are descriptive paired units; duplicate weight views and C3 pair sides are not independent sources.",
                        "CPU/wall costs are recorded executed measurements, not independently remeasured; cooperative deadline starts after AST parsing.",
                        "No new source-C3 physical reconstruction was implemented by this independent auditor; original graphs/metadata are byte-identical and graph feasibility is replayed."]}
    report["checks"] = dict(checks)
    report["elapsed_wall_seconds"] = time.perf_counter() - start
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": sum(checks.values()), "errors": len(errors), "cross_host": report["cross_host"]["counts"],
                      "first_argmax_checked": len(first_checked), "first_argmax_skipped": len(first_skipped),
                      "completed_assignments": sum(completed_by_method.values()), "summaries": summaries}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", default=str(ROOT / "experiments/runs/v05" / (STEM + ".tar.gz")))
    p.add_argument("--analysis", default=str(ROOT / "experiments/analysis/v05" / (STEM + ".json")))
    p.add_argument("--out", default=str(ROOT / "experiments/analysis/v05/matched_transfer_server_audit_v05_001.json"))
    p.add_argument("--provenance-only", action="store_true")
    args = p.parse_args()
    audit(args.archive, args.analysis, args.out, args.provenance_only)
