"""Frozen V06 TEST mechanism/relabel evaluation; no authoring or oracle calls.

Research preparation/execution are Linux-only and require explicit byte-bound
TRAIN winners, control selection and previously frozen TEST certificates.
Pure helpers are available for tiny, outcome-free contract tests.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import time

from .compiled import CompiledEvaluator
from .graph_features import FeatureRuleProgram
from .model import Contact, Graph
from .programs import FEATURES
from .refinement import diagnose_occurrences
from .representation import vector_key
from .repair_v06 import RepairConfig, repair_schedule
from .synthesis_study_v06 import ARMS, InterfaceMeter, canonical, digest, macro_quality, write


SOURCE_NAMES = ("heldout_mechanism_v06.py", "synthesis_study_v06.py", "repair_v06.py",
                "compiled.py", "graph_features.py", "model.py", "programs.py",
                "refinement.py", "representation.py", "__init__.py")
REPAIR_CONFIG = dict(max_patch_vertices=24, max_destroy=4, max_patches=32,
                     expansion_steps=1, node_budget_per_patch=128,
                     max_search_nodes=4096, max_work=200000,
                     upper_pruning=True, policy_scope="branch")
DEFAULT_INTERFACE_LIMITS = dict(max_work=100000000, cpu_seconds=60)


def source_hashes():
    return {name: digest(Path(__file__).parent / name) for name in SOURCE_NAMES}


LOADED_SOURCE_HASHES = source_hashes()


def _linux_only():
    if platform.system() != "Linux":
        raise ValueError("V06 held-out research preparation/execution is Linux-only")


def _bound_read(path, expected):
    path = Path(path)
    if not isinstance(expected, str) or len(expected) != 64 or digest(path) != expected:
        raise ValueError("Required SHA256 binding changed: " + str(path))
    return json.loads(path.read_bytes())


def validate_selected(selection):
    """A transport-complete block is not inferred from favourable outcomes."""
    blocks = selection.get("matched_transport_complete_blocks", [])
    programs = selection.get("programs", [])
    if (selection.get("selection_split") != "train" or selection.get("test_accessed") is not False
        or selection.get("all_cells_have_genuine_winner") is not True
        or selection.get("all120_original_slots_assessed") is not True
        or selection.get("no_fallback") is not True
        or len(blocks) != 4 or len(set(blocks)) != 4
        or any(type(b) is not int or not 0 <= b <= 4 for b in blocks)
        or blocks != sorted(blocks) or len(programs) != 12):
        raise ValueError("Exactly 12 genuine frozen TRAIN winners from four whole transport blocks are required")
    cells = {(b, a) for b in blocks for a in ARMS}
    if {(p["block"], p["arm"]) for p in programs} != cells:
        raise ValueError("Frozen winners do not cover every whole-block arm exactly once")
    if len({p["id"] for p in programs}) != 12:
        raise ValueError("Duplicate selected identity")
    entries = []
    for p in programs:
        if (type(p["slot"]) is not int or not 0 <= p["slot"] < 8
            or p["id"] != f"block_{p['block']}_{p['arm']}:{p['slot']}"
            or canonical(p["program"]) != p["program_sha256"]):
            raise ValueError("Selected program/slot binding changed")
        raw = FeatureRuleProgram.from_dict(p["program"]).to_dict()
        entries.append({**p, "program": raw, "role": "TRAIN_selected",
                        "priority": "program", "main_comparison": True})
    return entries


def control_entries(selection, bank):
    if (selection.get("selection_split") != "train" or selection.get("test_accessed") is not False
        or selection.get("all64_original_slots_assessed") is not True
        or selection.get("no_fallback") is not True):
        raise ValueError("Complete, frozen TRAIN-only controls selection is required")
    entries = []
    for group in ("enumerated_structural", "fixed_base9"):
        found = [r for r in selection["selections"] if r["block"] == 0 and r["bank"] == group]
        if len(found) != 1 or found[0].get("quality_only_baseline") is None:
            raise ValueError("Missing genuine block0 quality-only control: " + group)
        p = found[0]["quality_only_baseline"]
        slot = p["slot"]
        if (type(slot) is not int or not 0 <= slot < 8 or len(bank["banks"][group]) != 8
            or p["program"] != bank["banks"][group][slot]
            or canonical(p["program"]) != p["program_sha256"]):
            raise ValueError("Quality-only control changed from its frozen catalogue")
        entries.append({**p, "role": "TRAIN_quality_only_control", "priority": "program",
                        "main_comparison": True, "joint_gate_not_required": True})
    degree = FeatureRuleProgram.from_dict(bank["degree_fixed_reference"]).to_dict()
    entries.append({"id": "fixed_degree", "arm": "degree", "block": None, "slot": None,
                    "program": degree, "program_sha256": canonical(degree),
                    "role": "classical_Degree", "priority": "degree", "main_comparison": True})
    structural = bank["banks"]["enumerated_structural"]
    if len(structural) != 8:
        raise ValueError("Retain all eight original enumerated structural controls")
    for slot, raw in enumerate(structural):
        p = FeatureRuleProgram.from_dict(raw).to_dict()
        entries.append({"id": f"robust_enumerated_structural:{slot}", "arm": "enumerated_structural",
                        "block": None, "slot": slot, "program": p, "program_sha256": canonical(p),
                        "role": "complete_relabel_control_bank", "priority": "program",
                        "main_comparison": False})
    return entries


def validate_test_labels(records, labels):
    """Check every planned query's binding and signed status, never replace it."""
    if len({r["id"] for r in records}) != len(records) or len({r["id"] for r in labels}) != len(labels):
        raise ValueError("Duplicate TEST state or certificate")
    lmap = {r["id"]: r for r in labels}
    if set(lmap) != {r["id"] for r in records}:
        raise ValueError("TEST certificate coverage must equal the entire input frame")
    for record in records:
        graph = Graph.from_dict(record["graph"])
        label = lmap[record["id"]]
        if (record["split"] != "test" or label["split"] != "test"
            or graph.digest() != record["graph_digest"] or label["graph_digest"] != record["graph_digest"]
            or label["quota"] != record["quota"] or label["family"] != record["family"]
            or label["cluster"] != record["cluster"] or len(label["rows"]) != len(record["queries"])):
            raise ValueError("Changed TEST state/certificate binding")
        available = graph.available(record["fixed"], record["excluded"])
        if sum(q["planned"] for q in record["quota"].values()) != len(record["queries"]):
            raise ValueError("Planned quota does not account for every TEST query")
        for plan, row in zip(record["queries"], label["rows"]):
            if any(plan[k] != row[k] for k in ("a", "b", "kind", "base_alias_by_side")):
                raise ValueError("TEST query order, actions or alias binding changed")
            a, b, d = row["a"], row["b"], row["difference"]
            if a not in available or b not in available or b not in graph.adj[a] or (d["a"], d["b"]) != (a, b):
                raise ValueError("Conditional TEST actions are not bound feasible competitors")
            lo, hi = Fraction(d["lower_exact"]), Fraction(d["upper_exact"])
            if lo > hi:
                raise ValueError("Invalid signed TEST interval")
            if d["status"] == "strict":
                expected = a if lo > Fraction(1e-8) else b if hi < -Fraction(1e-8) else None
                if expected is None or d["preferred"] != expected:
                    raise ValueError("Strict TEST preference disagrees with its signed interval")
            elif d["status"] == "exact_tie":
                if lo != 0 or hi != 0 or not d["exact"] or d["preferred"] is not None:
                    raise ValueError("Invalid exact conditional tie")
            elif d["status"] == "unknown":
                if d["preferred"] is not None:
                    raise ValueError("An unknown TEST interval cannot supply a strict label")
            else:
                raise ValueError("Unknown certificate status")


def cluster_mappings(records, index, salt):
    if type(index) is not int or not 0 <= index < 5:
        raise ValueError("Exactly five registered permutation indices, 0..4, are supported")
    nodes = defaultdict(set)
    for record in records:
        nodes[record["cluster"]].update(c["id"] for c in record["graph"]["contacts"])
    return {cluster: {old: f"r{i:03d}" for i, old in enumerate(sorted(ids,
             key=lambda old: (sha256(f"{salt}|{cluster}|{index}|{old}".encode()).digest(), old)))}
            for cluster, ids in nodes.items()}


def _relabel_difference(raw, mapping):
    d = deepcopy(raw)
    for key in ("a", "b", "preferred"):
        if d.get(key) is not None:
            d[key] = mapping[d[key]]
    d["cancelled_components"] = [sorted(mapping[v] for v in c) for c in d.get("cancelled_components", [])]
    for rows in d.get("unmatched", {}).values():
        for row in rows:
            row["vertices"] = sorted(mapping[v] for v in row["vertices"])
            row["bound"]["selected"] = sorted(mapping[v] for v in row["bound"].get("selected", []))
    # Numeric strings, including an exact interval equal to an old node ID,
    # are deliberately untouched. Only typed vertex positions are remapped.
    return d


def relabel_inventory(records, labels, index, salt):
    mappings = cluster_mappings(records, index, salt)
    new_records, new_labels = [], []
    for record in records:
        mapping = mappings[record["cluster"]]
        original = Graph.from_dict(record["graph"])
        graph = Graph(original.name + f"_relabel_{index}",
                      tuple(Contact(**{**c, "id": mapping[c["id"]]}) for c in record["graph"]["contacts"]),
                      frozenset((mapping[a], mapping[b]) for a, b in original.edges),
                      deepcopy(original.constraints), deepcopy(original.provenance))
        r = deepcopy(record)
        r.update(graph=graph.to_dict(), graph_digest=graph.digest(),
                 fixed=[mapping[v] for v in record["fixed"]],
                 excluded=[mapping[v] for v in record["excluded"]],
                 original_graph_digest=record["graph_digest"], relabel_index=index)
        for query in r["queries"]:
            query["a"], query["b"] = mapping[query["a"]], mapping[query["b"]]
        # Contact order, reward/resource/time fields and every original edge are
        # preserved under the bijection. Constraints and boundary remain static.
        if len(mapping) != len(set(mapping.values())) or any(
            graph.nodes[mapping[v]].weight != original.nodes[v].weight or
            {mapping[u] for u in original.adj[v]} != graph.adj[mapping[v]] for v in original.nodes):
            raise AssertionError("Relabeling is not an exact weighted graph isomorphism")
        new_records.append(r)
    rmap = {r["id"]: r for r in new_records}
    for label in labels:
        l = deepcopy(label); mapping = mappings[label["cluster"]]
        l["original_graph_digest"] = label["graph_digest"]
        l["graph_digest"] = rmap[label["id"]]["graph_digest"]
        for row in l["rows"]:
            row["a"], row["b"] = mapping[row["a"]], mapping[row["b"]]
            row["difference"] = _relabel_difference(row["difference"], mapping)
        new_labels.append(l)
    validate_test_labels(new_records, new_labels)
    return new_records, new_labels, mappings


def heldout_interface_assessment(raw, records, labels, limits=None):
    """Same finite-evaluation semantics as TRAIN, with an explicit TEST guard.

    No record is relabeled as TRAIN and no selection/gate decision is made.
    Feature/rank work is charged at strict endpoints exactly as in the original
    interface assessor. Ties/unknowns remain planned rows with no invented fit.
    """
    validate_test_labels(records, labels)
    start = time.process_time(); wall = time.perf_counter()
    meter = InterfaceMeter(**(limits or DEFAULT_INTERFACE_LIMITS))
    program = FeatureRuleProgram.from_dict(raw); meter.check()
    demanded = set(program.code.co_names) & {f["name"] for f in program.features}
    lmap = {r["id"]: r for r in labels}
    occurrences, declared, requirements, checks, all_checks = {}, {}, [], [], []
    for record in sorted(records, key=lambda r: r["id"]):
        meter.check()
        graph = Graph.from_dict(record["graph"])
        active = graph.available(record["fixed"], record["excluded"])
        rows = lmap[record["id"]]["rows"]
        strict = [q for q in rows if q["difference"]["status"] == "strict"]
        evaluator = CompiledEvaluator(graph, program, active, meter, score_slice=False)
        cache = {}
        for node in sorted({q[k] for q in strict for k in ("a", "b")}):
            values = evaluator.feature_values(node)
            cache[node] = (values, program._rank(values, meter))
            oid = record["id"] + "|" + node
            occurrences[oid] = {k: v for k, v in values.items() if k in FEATURES or k in demanded}
            declared[oid] = values
        strict_index = 0
        for query_index, q in enumerate(rows):
            d = q["difference"]
            row = {"state": record["id"], "split": "test", "cluster": record["cluster"],
                   "family": record["family"], "pair": record.get("pair"), "side": record.get("side"),
                   "query_index": query_index, "a": q["a"], "b": q["b"], "query_kind": q["kind"],
                   "certificate_status": d["status"], "preferred": d["preferred"],
                   "lower_exact": d["lower_exact"], "upper_exact": d["upper_exact"],
                   "passed": None, "score_a": None, "score_b": None}
            if d["status"] == "strict":
                p, n = d["preferred"], q["b"] if d["preferred"] == q["a"] else q["a"]
                requirements.append({"preferred": record["id"] + "|" + p, "other": record["id"] + "|" + n,
                                     "state": record["id"], "query_index": strict_index})
                strict_index += 1
                ps, ns = cache[p][1], cache[n][1]
                side = 0 if not record["paired"] or record["side"] == "left" else 1
                base_alias = vector_key({k: cache[p][0][k] for k in FEATURES}) == vector_key(
                    {k: cache[n][0][k] for k in FEATURES})
                if base_alias != q["base_alias_by_side"][side]:
                    raise ValueError("Strict endpoint base alias changed under evaluation")
                passed = ps > ns + 1e-8
                row.update(score_a=cache[q["a"]][1], score_b=cache[q["b"]][1], passed=passed,
                           score_preferred=ps, score_other=ns, score_tie=ps == ns,
                           actual_base_alias=base_alias,
                           demanded_feature_alias=vector_key(occurrences[record["id"] + "|" + p]) ==
                               vector_key(occurrences[record["id"] + "|" + n]))
                checks.append(row)
                meter.check()
            all_checks.append(row)
    diagnosis = diagnose_occurrences(occurrences, requirements); meter.check()
    declared_diagnosis = diagnose_occurrences(declared, requirements); meter.check()
    return {"split": "test", "selection_performed": False, "demanded_features": sorted(demanded),
            "strict_total": len(checks), "strict_passed": sum(q["passed"] for q in checks),
            "alias_strict_total": sum(q["actual_base_alias"] for q in checks),
            "alias_strict_passed": sum(q["passed"] and q["actual_base_alias"] for q in checks),
            "quotient": diagnosis, "declared_quotient": declared_diagnosis,
            "strict_checks": checks, "query_checks": all_checks,
            "certificate_status": dict(Counter(q["certificate_status"] for q in all_checks)),
            "planned_queries": len(all_checks),
            "quota_shortfalls": sum(q["shortfall"] for r in records for q in r["quota"].values()),
            "interface_feature_work": meter["feature_work"],
            "interface_cpu_seconds": time.process_time() - start,
            "interface_wall_seconds": time.perf_counter() - wall,
            "full_observed_consistency": not diagnosis["contradictory"] and all(q["passed"] for q in checks)}


def paired_checks(interface):
    grouped = defaultdict(dict)
    for q in interface["query_checks"]:
        if q["pair"] is not None:
            grouped[(q["pair"], q["query_index"])][q["side"]] = q
    rows = []
    for (pair, index), sides in sorted(grouped.items()):
        if set(sides) != {"left", "right"}:
            raise ValueError("Missing paired TEST endpoint")
        l, r = sides["left"], sides["right"]
        if (l["a"], l["b"]) != (r["a"], r["b"]):
            raise ValueError("Paired relabeling changed competing-action alignment")
        ls, rs = l["certificate_status"], r["certificate_status"]
        if ls == rs == "strict":
            category = "strict_preservation" if l["preferred"] == r["preferred"] else "strict_reversal"
            passed = l["passed"] and r["passed"]
        elif ls == rs == "exact_tie":
            category, passed = "exact_tie_both", None
        elif "unknown" in (ls, rs):
            category, passed = "incomplete_interval", None
        else:
            category, passed = ("strict_to_tie" if ls == "strict" else "tie_to_strict"), None
        rows.append({"pair": pair, "cluster": l["cluster"], "query_index": index,
                     "a": l["a"], "b": l["b"], "category": category, "pair_passed": passed,
                     "left_passed": l["passed"], "right_passed": r["passed"],
                     "left_preferred": l["preferred"], "right_preferred": r["preferred"]})
    return rows


def evaluate_entry(task):
    entry, records, labels, protocol, variant = task
    if source_hashes() != protocol["source_sha256"] or LOADED_SOURCE_HASHES != protocol["source_sha256"]:
        raise ValueError("Frozen held-out runtime changed after load")
    cpu, wall = time.process_time(), time.perf_counter()
    result = {"id": entry["id"], "identity": entry, "variant": variant, "split": "test",
              "selection_performed": False, "extra_oracle_calls": 0, "kernel_rows": []}
    try:
        result["interface"] = heldout_interface_assessment(entry["program"], records, labels,
                                                            protocol["interface_limits"])
        result["paired_checks"] = paired_checks(result["interface"])
    except Exception as error:
        result.update(interface_error_type=type(error).__name__, interface_error=str(error))
    cfg = protocol["kernel_config"]
    for record in sorted(records, key=lambda r: r["id"]):
        start_cpu, start_wall = time.process_time(), time.perf_counter()
        row = {"id": record["id"], "family": record["family"], "cluster": record["cluster"], "split": "test"}
        try:
            graph = Graph.from_dict(record["graph"])
            row["graph_materialization_cpu_seconds"] = time.process_time() - start_cpu
            row["graph_materialization_wall_seconds"] = time.perf_counter() - start_wall
            observed = repair_schedule(graph, entry["program"], fixed=record["fixed"], excluded=record["excluded"],
                priority=entry["priority"], seconds=cfg["seconds"], clock=cfg["clock"],
                config=RepairConfig(**cfg["repair_config"]))
            selected = observed["selected"]
            value = sum((Fraction(graph.nodes[v].weight) for v in selected), Fraction())
            if (not graph.feasible(selected) or not set(record["fixed"]) <= set(selected)
                or set(record["excluded"]) & set(selected) or Fraction(observed["value_exact"]) != value):
                raise ValueError("Held-out incumbent fails independent original-graph reward/feasibility check")
            row["result"] = observed
        except Exception as error:
            row.update(error_type=type(error).__name__, error=str(error))
        row["task_cpu_seconds"] = time.process_time() - start_cpu
        row["task_wall_seconds"] = time.perf_counter() - start_wall
        result["kernel_rows"].append(row)
    rows = result["kernel_rows"]
    complete = [r for r in rows if r.get("result", {}).get("completed")]
    retained = [r for r in rows if r.get("result", {}).get("feasible")]
    result["kernel_coverage"] = {"assigned_states": len(records), "returned_states": len(rows),
        "normal_completed": len(complete), "verified_incumbents": len(retained),
        "errors": len(rows) - len(complete),
        "normal_budget_stops": sum(r["result"].get("budget_exhausted", False) for r in complete),
        "status": dict(Counter(r.get("result", {}).get("status", "worker_or_validation_error") for r in rows))}
    result["kernel_summary"] = macro_quality(rows, records) if len(retained) == len(records) else None
    result["actual_cpu_seconds"] = time.process_time() - cpu
    result["actual_wall_seconds"] = time.perf_counter() - wall
    return result


def prepare(plan, selection, selection_sha256, controls_selection, controls_selection_sha256,
            certificates, test_certificate_sha256, authoring_protocol, controls_registration,
            control_bank, control_freeze, relabel_config, kernel_config, out, workers=8):
    _linux_only()
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer")
    out, plan, certificates = Path(out), Path(plan), Path(certificates)
    if out.exists():
        raise ValueError("Never overwrite held-out registration")
    if source_hashes() != LOADED_SOURCE_HASHES:
        raise ValueError("Loaded held-out source bytes changed")
    selected = _bound_read(selection, selection_sha256)
    entries = validate_selected(selected)
    controls = _bound_read(controls_selection, controls_selection_sha256)
    author = json.loads(Path(authoring_protocol).read_bytes())
    control_protocol = json.loads((Path(controls_registration) / "protocol.json").read_bytes())
    control_receipt = json.loads((Path(controls_registration) / "freeze_receipt.json").read_bytes())
    bank = json.loads(Path(control_bank).read_bytes())
    bank_freeze = json.loads(Path(control_freeze).read_bytes())
    if (selected["parent_protocol_sha256"] != digest(authoring_protocol)
        or controls["registration_sha256"] != digest(Path(controls_registration) / "protocol.json")
        or control_receipt["protocol_sha256"] != controls["registration_sha256"]
        or control_protocol["control_bank_sha256"] != digest(control_bank)
        or bank_freeze["control_banks_sha256"] != digest(control_bank)):
        raise ValueError("TRAIN/control protocol binding changed")
    for key, name in (("assessment", "synthesis_study_v06.py"), ("kernel", "repair_v06.py"),
                      ("typed_library", "graph_features.py"), ("compiled_runtime", "compiled.py")):
        if digest(Path(__file__).parent / name) != author["source_sha256"][key]:
            raise ValueError("Frozen original assessment/kernel source changed: " + name)
    entries += control_entries(controls, bank)
    if len(entries) != 23 or len({e["id"] for e in entries}) != 23:
        raise ValueError("All 23 requested comparator identities must remain explicit")
    data = json.loads((plan / "data.json").read_bytes())
    data_freeze = json.loads((plan / "freeze_receipt.json").read_bytes())
    if (data_freeze["data_sha256"] != digest(plan / "data.json")
        or data_freeze["protocol_sha256"] != digest(plan / "protocol.json")
        or data_freeze["before_any_oracle_query"] is not True):
        raise ValueError("Original frozen query/input frame changed")
    records = [r for r in data["records"] if r["split"] == "test"]
    if len(records) != 72:
        raise ValueError("Retain all 72 frozen TEST states")
    label_path = certificates / "results.jsonl"
    if digest(label_path) != test_certificate_sha256:
        raise ValueError("Required TEST certificate SHA256 changed")
    complete = json.loads((certificates / "complete.json").read_bytes())
    execution = json.loads((certificates / "execution.json").read_bytes())
    if (complete.get("execution_complete") is not True or complete.get("split") != "test"
        or execution.get("split") != "test" or complete.get("states") != 72
        or complete["results_sha256"] != test_certificate_sha256
        or complete["programme_freeze_sha256"] != selection_sha256
        or execution["programme_freeze_sha256"] != selection_sha256
        or digest(certificates / "data.json") != digest(plan / "data.json")
        or digest(certificates / "protocol.json") != digest(plan / "protocol.json")
        or execution["source_sha256"] != data_freeze["source_sha256"]):
        raise ValueError("TEST certificates lack the genuine TRAIN winner freeze/input binding")
    labels = [json.loads(line) for line in label_path.read_text(encoding="utf-8").splitlines() if line]
    validate_test_labels(records, labels)
    relabel = json.loads(Path(relabel_config).read_bytes())
    kernel = json.loads(Path(kernel_config).read_bytes())
    if (relabel.get("registered_before_any_TEST_programme_evaluation") is not True
        or relabel.get("permutations_per_source") != 5
        or relabel.get("version") != "v06_pre_TEST_relabel_robustness_001"
        or not isinstance(relabel.get("salt"), str) or not relabel["salt"]
        or kernel["seconds"] != .5 or kernel["clock"] != "wall"
        or kernel["repair_config"] != REPAIR_CONFIG or kernel != author["kernel_config"]
        or kernel != control_protocol["kernel_config"]
        or author["interface_limits"] != DEFAULT_INTERFACE_LIMITS
        or control_protocol["interface_limits"] != DEFAULT_INTERFACE_LIMITS):
        raise ValueError("Registered relabel/shared .5-second/200k-work evaluation semantics changed")
    out.mkdir(parents=True)
    for name, path in (("selection.json", selection), ("controls_selection.json", controls_selection),
                       ("authoring_protocol.json", authoring_protocol), ("kernel_config.json", kernel_config),
                       ("relabel_config.json", relabel_config), ("control_bank.json", control_bank),
                       ("control_freeze.json", control_freeze)):
        shutil.copyfile(path, out / name)
    write(out / "test_inputs.json", {"records": records})
    write(out / "test_certificates.json", {"labels": labels})
    inventory = []
    for index in range(5):
        remapped, _, mappings = relabel_inventory(records, labels, index, relabel["salt"])
        inventory.append({"variant": f"relabel_{index}", "index": index, "mappings": mappings,
                          "graph_digests": {r["id"]: r["graph_digest"] for r in remapped}})
    write(out / "relabel_inventory.json", inventory)
    sources = source_hashes()
    for name in sources:
        target = out / "source_snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).parent / name, target)
    protocol = {"version": "v06_heldout_mechanism_relabel_001", "split": "test",
        "selection_sha256": selection_sha256, "controls_selection_sha256": controls_selection_sha256,
        "test_certificate_sha256": test_certificate_sha256,
        "original_data_sha256": digest(plan / "data.json"), "source_sha256": sources,
        "entries": entries, "kernel_config": kernel, "interface_limits": author["interface_limits"],
        "variants": ["original"] + [f"relabel_{i}" for i in range(5)], "workers": workers,
        "all_original_states": 72, "relabel_state_count": 360,
        "matched_transport_complete_blocks": selected["matched_transport_complete_blocks"],
        "selection_performed": False, "extra_oracle_calls": 0,
        "identical_AST_execution_reused": False,
        "main_comparators": 15, "complete_robustness_bank_comparators": 23,
        "normal_caps_retain_incumbents": True,
        "base_interface_and_actual_scalar_fit_reported_separately": True}
    write(out / "protocol.json", protocol)
    write(out / "freeze_receipt.json", {"before_any_TEST_programme_evaluation": True,
        "artifact_sha256": {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()},
        "source_sha256": sources})
    return {"prepared": str(out), "assigned_identities": 23, "variants": 6, "TEST_programme_evaluations": 0}


def run(registration, out):
    _linux_only()
    registration, out = Path(registration), Path(out)
    if out.exists():
        raise ValueError("Never overwrite held-out observations")
    freeze = json.loads((registration / "freeze_receipt.json").read_bytes())
    if freeze.get("before_any_TEST_programme_evaluation") is not True:
        raise ValueError("Missing pre-evaluation freeze")
    for name, expected in freeze["artifact_sha256"].items():
        if digest(registration / name) != expected:
            raise ValueError("Registered held-out input/source changed: " + name)
    protocol = json.loads((registration / "protocol.json").read_bytes())
    if source_hashes() != freeze["source_sha256"] or LOADED_SOURCE_HASHES != freeze["source_sha256"]:
        raise ValueError("Registered held-out runtime changed")
    records = json.loads((registration / "test_inputs.json").read_bytes())["records"]
    labels = json.loads((registration / "test_certificates.json").read_bytes())["labels"]
    validate_test_labels(records, labels)
    inventory = json.loads((registration / "relabel_inventory.json").read_bytes())
    relabel = json.loads((registration / "relabel_config.json").read_bytes())
    variants = [("original", records, labels)]
    for planned in inventory:
        rs, ls, mappings = relabel_inventory(records, labels, planned["index"], relabel["salt"])
        if mappings != planned["mappings"] or {r["id"]: r["graph_digest"] for r in rs} != planned["graph_digests"]:
            raise ValueError("Registered relabel bijections changed")
        variants.append((planned["variant"], rs, ls))
    tasks = [(e, rs, ls, protocol, variant) for variant, rs, ls in variants for e in protocol["entries"]]
    if len(tasks) != 138:
        raise ValueError("Every requested identity/variant must be assigned")
    out.mkdir(parents=True)
    write(out / "execution.json", {"registration_sha256": digest(registration / "protocol.json"),
        "selection_sha256": protocol["selection_sha256"],
        "controls_selection_sha256": protocol["controls_selection_sha256"],
        "test_certificate_sha256": protocol["test_certificate_sha256"],
        "source_sha256": protocol["source_sha256"], "split": "test", "workers": protocol["workers"],
        "assignments": 138, "state_kernel_assignments": 9936,
        "selection_performed": False, "extra_oracle_calls": 0})
    rows = []
    with (out / "results.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
            futures = {pool.submit(evaluate_entry, task): (task[0]["id"], task[-1]) for task in tasks}
            for future in as_completed(futures):
                identity, variant = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    row = {"id": identity, "variant": variant, "split": "test", "kernel_rows": [],
                           "worker_error_type": type(error).__name__, "worker_error": str(error)}
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); stream.flush()
                write(out / "progress.json", {"returned_assignments": len(rows), "assigned": len(tasks),
                                              "last_id": identity, "last_variant": variant})
    summary = []
    for entry in protocol["entries"]:
        observed = {r["variant"]: r for r in rows if r["id"] == entry["id"]}
        scores = [observed[f"relabel_{i}"].get("interface", {}).get("strict_passed") for i in range(5)]
        totals = [observed[f"relabel_{i}"].get("interface", {}).get("strict_total") for i in range(5)]
        complete_fit = all(s is not None for s in scores)
        summary.append({"id": entry["id"], "identity": entry,
            "original_strict_passed": observed["original"].get("interface", {}).get("strict_passed"),
            "original_strict_total": observed["original"].get("interface", {}).get("strict_total"),
            "all5_relabel_strict_passed": scores,
            "all5_relabel_strict_total": totals,
            "mean_relabel_strict_passed": sum(scores) / 5 if complete_fit else None,
            "worst_relabel_strict_passed": min(scores) if complete_fit else None,
            "all5_fit_measurements_available": complete_fit,
            "cluster_unit": "original source cluster; paired endpoints and five permutations are dependent"})
    write(out / "robustness_summary.json", summary)
    write(out / "complete.json", {"execution_complete": len(rows) == len(tasks), "split": "test",
        "returned_assignments": len(rows), "assigned": len(tasks),
        "worker_errors": sum("worker_error" in r for r in rows),
        "interface_errors": sum("interface_error" in r for r in rows),
        "kernel_errors": sum(r.get("kernel_coverage", {}).get("errors", 72) for r in rows),
        "results_sha256": digest(out / "results.jsonl"),
        "selection_performed": False, "extra_oracle_calls": 0,
        "all_quota_shortfalls_and_unknowns_retained": True})
    return {"complete": str(out), "returned_assignments": len(rows), "assigned": len(tasks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    for flag in ("plan", "selection", "selection-sha256", "controls-selection", "controls-selection-sha256",
                 "certificates", "test-certificate-sha256", "authoring-protocol", "controls-registration",
                 "control-bank", "control-freeze", "relabel-config", "kernel-config", "out"):
        p.add_argument("--" + flag, required=True)
    p.add_argument("--workers", type=int, default=8)
    p = sub.add_parser("run"); p.add_argument("--registration", required=True); p.add_argument("--out", required=True)
    args = vars(parser.parse_args()); mode = args.pop("mode")
    print(json.dumps(prepare(**args) if mode == "prepare" else run(**args), ensure_ascii=False))


if __name__ == "__main__":
    main()
