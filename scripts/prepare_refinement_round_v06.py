"""Prepare TRAIN-adaptive V06 R2 packets without authoring or assessing them.

R1 observations select one common seed and its counterexamples. A draft is
deliberately not executable: protocol/freeze/transport files are written only
by explicit finalization with a separately approved pre-generation role plan.
No optimizer, conditional certifier, candidate evaluator or model is called.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.graph_features import FeatureRuleProgram, graph_operation_library
from cipheur.model import Graph
from cipheur.programs import FEATURES

VERSION = "matched_refinement_round_v06_002"
ARMS = ("witness", "relations", "objective")
BLOCKS, SLOTS = 5, 8
SALT = "v06_r2_counterexample_metadata_sha_002"
LABEL_CAP, STATE_CAP, PACKET_BYTE_CAP = 32, 16, 180000
SOURCES = {
    "synthesis_study_v06.py": "f640af65645426cdf172d1cbc7326bae221acf43ece81225ef8bf06cf2c8b0bb",
    "repair_v06.py": "c4cbdb9878c041321f4cfcc0637a7a3113add38732ca04d05c8687d9a8e7e8f3",
    "graph_features.py": "b6f807e9a1a13e8443532247e24fc802815053d375f69ed2c2718a222282a03d",
    "compiled.py": "f0f85d0104fbdcdca54fd5adf743e42946812132612cfe590d02315fb8631788",
    "model.py": "d5968cffb1676a2f4bd73d5ba2715618142059b0c81ec8263f76a79100a8a1d8",
    "programs.py": "cca9739aff75dba79d3ad4b5742f1db10e88ffb398f21dbda09fc23bd20b0f59",
    "refinement.py": "90a7e6c6981a73d13b715dc0b2b773cd2052724c2e044af617b7795eb074bd99",
    "representation.py": "5f844dd5ab6d5f79e92a0a7ea6ba0af6073d2e7d3f39a69a091b3fcf875d9dc0",
}
JOINT_SELECTOR = [
    "static_valid_and_finite_full_TRAIN_interface_and_feasible_kernel",
    "demanded_full_TRAIN_quotient_acyclic",
    "maximize_actual_strict_fit_margin_1e-8",
    "maximize_macro_family_reward_over_total_weight",
    "minimize_macro_family_feature_plus_repair_work",
    "earlier_original_slot",
]
QUALITY_SELECTOR = [
    "static_valid_and_completed_feasible_kernel",
    "maximize_macro_family_reward_over_total_weight",
    "minimize_macro_family_feature_plus_repair_work",
    "earlier_original_slot",
]
PLAN_VERSION = "v06_R2_pre_generation_selection_roles_002"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def encoded(value, compact=False):
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       **options) + "\n").encode("utf-8")


def canonical(value):
    return sha256(encoded(value, compact=True)).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metadata_order(value):
    return sha256(SALT.encode() + b"|" + encoded(value, compact=True)).digest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def check_sources():
    for name, expected in SOURCES.items():
        if digest(ROOT / "cipheur" / name) != expected:
            raise ValueError("Frozen R1 source differs: " + name)
    return dict(SOURCES)


def validate_plan(plan):
    """Accept the independently reviewed R2 role schema, never the R1 barrier."""
    if (plan.get("version") != PLAN_VERSION
            or plan.get("registered_before_any_R2_authoring_or_candidate_assessment") is not True
            or plan.get("authoring", {}).get("fixed_whole_blocks") != BLOCKS
            or plan["authoring"].get("arms") != list(ARMS)
            or plan["authoring"].get("original_slots_per_block_arm") != SLOTS
            or plan["authoring"].get("all_original_slots") != 120
            or plan.get("uniform_joint_selector", {}).get("ordering") != [
                "max strict TRAIN scalar fit", "max exact equal-family reward/total-weight",
                "min exact equal-family feature-plus-repair work", "original slot"]
            or plan.get("uniform_quality_only_selector", {}).get("ordering") != [
                "max exact equal-family reward/total-weight",
                "min exact equal-family feature-plus-repair work", "original slot"]
            or plan.get("deployment", {}).get("proposed_method_count") != 4
            or SOURCES["synthesis_study_v06.py"] not in plan["uniform_joint_selector"].get("assessor", "")
            or not plan.get("independent_pre_generation_review")):
        raise ValueError("The approved five-block R2 joint/quality role plan is required")
    return plan


def exact_number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("A saved feature vector must contain finite numbers")
    return Fraction(value)


def validate_evidence(evidence):
    records = evidence["records"]
    if len(records) != 120 or any(r["split"] != "train" for r in records):
        raise ValueError("R2 consumes the unchanged 120 TRAIN states only")
    rmap = {r["id"]: r for r in records}
    if len(rmap) != len(records):
        raise ValueError("Duplicate TRAIN state identifier")
    graphs = {}
    for r in records:
        graph = Graph.from_dict(r["graph"])
        if graph.digest() != r["graph_digest"]:
            raise ValueError("TRAIN graph digest differs")
        graph.available(r["fixed"], r["excluded"])
        graphs[r["id"]] = graph
    labels = {r["id"]: r for r in evidence["labels"]}
    feedback = {r["id"]: r for r in evidence["kernel_feedback"]}
    if set(labels) != set(rmap) or set(feedback) != set(rmap):
        raise ValueError("TRAIN labels/feedback must cover every original state")
    strict, by_state = {}, {}
    for sid in sorted(rmap):
        rows = [q for q in labels[sid]["rows"] if q["difference"]["status"] == "strict"]
        by_state[sid] = []
        active = graphs[sid].available(rmap[sid]["fixed"], rmap[sid]["excluded"])
        for index, q in enumerate(rows):
            a, b, p = q["a"], q["b"], q["difference"]["preferred"]
            if a == b or p not in (a, b) or not {a, b} <= active or b not in graphs[sid].adj[a]:
                raise ValueError("Strict query is not a feasible adjacent choice")
            n = b if p == a else a
            lower, upper = Fraction(q["difference"]["lower_exact"]), Fraction(q["difference"]["upper_exact"])
            # Stored differences are a minus b, independent of preferred action.
            if p == b:
                lower, upper = -upper, -lower
            if not 0 < lower <= upper:
                raise ValueError("Saved strict interval does not prove its preferred sign")
            key = (sid, p, n)
            if key in strict:
                raise ValueError("Duplicate strict requirement")
            relation = {"state": sid, "preferred": p, "other": n,
                        "query_index": index, "kind": q["kind"],
                        "lower_exact": str(lower), "upper_exact": str(upper)}
            strict[key] = relation
            by_state[sid].append(key)
    if len(strict) != 594:
        raise ValueError("The original 594 strict TRAIN requirements changed")
    return rmap, graphs, strict, by_state, feedback


def kernel_summary(rows, rmap, graphs, config):
    if len(rows) != len(rmap) or {r["id"] for r in rows} != set(rmap):
        raise ValueError("A completed seed must retain all 120 kernel observations")
    qualities, works = defaultdict(list), defaultdict(list)
    for row in rows:
        sid, result = row["id"], row["result"]
        record, graph = rmap[sid], graphs[sid]
        if (not result["completed"] or not result["feasible"] or result.get("fallback_used", False)
                or result.get("error")
                or result["config"] != config["repair_config"]
                or result["declared_seconds"] != config["seconds"]
                or result["deadline_clock"] != config["clock"]):
            raise ValueError("Saved seed kernel did not complete under the fixed contract")
        selected = result["selected"]
        if (not graph.feasible(selected) or not set(record["fixed"]) <= set(selected)
                or set(record["excluded"]) & set(selected)):
            raise ValueError("Saved selected set violates its explicit boundary")
        reward = sum((Fraction(graph.nodes[v].weight) for v in selected), Fraction())
        if reward != Fraction(result["value_exact"]):
            raise ValueError("Saved reward differs from independently summed feasible set")
        total = sum((Fraction(c.weight) for c in graph.contacts), Fraction())
        meter = result["meter"]
        work = meter["feature_work"] + meter["repair_work"]
        if type(work) is not int or work < 0:
            raise ValueError("Saved work must be a nonnegative integer")
        qualities[record["family"]].append(reward / total if total else Fraction(1))
        works[record["family"]].append(work)
    q = {f: sum(v, Fraction()) / len(v) for f, v in qualities.items()}
    w = {f: Fraction(sum(v), len(v)) for f, v in works.items()}
    return {"macro_quality_exact": str(sum(q.values(), Fraction()) / len(q)),
            "macro_work_exact": str(sum(w.values(), Fraction()) / len(w)),
            "family_reward_over_total_weight": {f: str(v) for f, v in q.items()},
            "family_work": {f: str(v) for f, v in w.items()}}


def seed_key(row):
    return (-row["interface"]["strict_passed"],
            -Fraction(row["kernel_summary"]["macro_quality_exact"]),
            Fraction(row["kernel_summary"]["macro_work_exact"]), row["id"])


def choose_seed(path, rmap, graphs, strict, config):
    """Stream the immutable bank; retain no more than one large result row."""
    best, inventory, seen = None, [], set()
    for line in Path(path).open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        if row["id"] != f"block_{row['block']}_{row['arm']}:{row['slot']}":
            raise ValueError("R1 source identity differs from its original raw position")
        if row["id"] in seen:
            raise ValueError("Duplicate original R1 slot")
        seen.add(row["id"])
        item = {k: row[k] for k in ("id", "block", "arm", "slot", "status", "assessment_status", "eligible")}
        item["seed_pool"] = False
        if (row["status"] == "static_valid" and row["assessment_status"] == "assessed"
                and not row["eligible"] and row["interface"]["quotient"]["contradictory"]):
            program = FeatureRuleProgram.from_dict(row["program"]).to_dict()
            if program != row["program"]:
                raise ValueError("Saved static program is not its canonical accepted form")
            interface = row["interface"]
            checks = interface["strict_checks"]
            keys = set()
            passed = 0
            for c in checks:
                key = (c["state"], c["preferred"], c["b"] if c["preferred"] == c["a"] else c["a"])
                if key not in strict or key in keys:
                    raise ValueError("Saved scalar fit is not the full original strict frame")
                keys.add(key)
                ps, ns = c["score_preferred"], c["score_other"]
                exact_number(ps); exact_number(ns)
                if c["passed"] != (ps > ns + 1e-8) or c["score_tie"] != (ps == ns):
                    raise ValueError("Saved scalar agreement differs from its score pair")
                passed += int(c["passed"])
            if keys != set(strict) or interface["strict_total"] != 594 or passed != interface["strict_passed"]:
                raise ValueError("Saved strict-fit count differs")
            demanded = sorted(set(FeatureRuleProgram.from_dict(program).code.co_names)
                              & {f["name"] for f in program["features"]})
            if demanded != sorted(interface["demanded_features"]):
                raise ValueError("Saved demanded interface differs from unchanged rule AST")
            summary = kernel_summary(row["kernel_rows"], rmap, graphs, config)
            if summary != row["kernel_summary"]:
                raise ValueError("Saved exact family macro quality/work differs")
            item.update(seed_pool=True, strict_passed=passed,
                        macro_quality_exact=summary["macro_quality_exact"],
                        macro_work_exact=summary["macro_work_exact"])
            if best is None or seed_key(row) < seed_key(best):
                best = row
        inventory.append(item)
    expected = {f"block_{b}_{a}:{s}" for b in range(5) for a in ARMS for s in range(8)}
    if seen != expected:
        raise ValueError("Seed selection must retain all five R1 blocks and 120 slots")
    if best is None:
        raise ValueError("No completed finite contradictory seed exists; do not invent one")
    return best, sorted(inventory, key=lambda r: r["id"])


def concrete_cycles(seed, rmap, graphs, strict, by_state):
    occurrences = {}
    for sid, graph in graphs.items():
        for v in graph.nodes:
            oid = sid + "|" + v
            if oid in occurrences:
                raise ValueError("Ambiguous saved occurrence identifier")
            occurrences[oid] = (sid, v)
    vectors = set(FEATURES) | set(seed["interface"]["demanded_features"])
    result, mandatory = [], []
    for witness in seed["interface"]["quotient"]["structural_witnesses"]:
        reqs, joins = witness["requirements"], witness["equality_joins"]
        if witness["kind"] not in ("directed_cycle", "self_loop") or not reqs or len(reqs) != len(joins):
            raise ValueError("Structural witness does not have concrete cyclic joins")
        resolved = []
        for req in reqs:
            ps, p = occurrences[req["preferred"]]
            ns, n = occurrences[req["other"]]
            key = (ps, p, n)
            if ps != ns or req["state"] != ps or key not in strict:
                raise ValueError("Witness arc is not a saved strict requirement")
            if by_state[ps][req["query_index"]] != key:
                raise ValueError("Witness strict-query index does not identify its endpoints")
            resolved.append(key)
            if key not in mandatory:
                mandatory.append(key)
        for i, join in enumerate(joins):
            if join["negative"] != reqs[i]["other"] or join["positive"] != reqs[(i + 1) % len(reqs)]["preferred"]:
                raise ValueError("Equality join does not close the concrete directed cycle")
            negative, positive = join["negative_vector"], join["positive_vector"]
            if set(negative) != vectors or set(positive) != vectors:
                raise ValueError("Join omits part of the full demanded interface")
            if any(exact_number(negative[k]) != exact_number(positive[k]) for k in vectors):
                raise ValueError("Claimed equality join differs exactly")
        result.append({"kind": witness["kind"], "requirements": resolved, "joins": joins})
    if not result:
        raise ValueError("The chosen seed lacks an inspectable concrete cycle")
    return result, mandatory, occurrences


def choose_feedback(seed, records, strict, mandatory):
    """Mandatory witnesses precede SHA-ordered misranked strict requirements."""
    rmap = {r["id"]: r for r in records}
    companions = defaultdict(set)
    for r in records:
        if r["paired"]:
            companions[r.get("pair", r["cluster"])].add(r["id"])

    def state_closure(keys):
        states = {k[0] for k in keys}
        for sid in list(states):
            record = rmap[sid]
            if record["paired"]:
                states.update(companions[record.get("pair", record["cluster"])])
        return states

    selected = list(dict.fromkeys(mandatory))
    if len(selected) > LABEL_CAP or len(state_closure(selected)) > STATE_CAP:
        raise ValueError("Mandatory complete cycle evidence exceeds registered packet caps")
    failed = [(c["state"], c["preferred"], c["b"] if c["preferred"] == c["a"] else c["a"])
              for c in seed["interface"]["strict_checks"] if not c["passed"]]
    candidates = sorted(set(failed) - set(selected),
                        key=lambda k: (metadata_order({"state": k[0], "preferred": k[1], "other": k[2],
                                                      "kind": strict[k]["kind"]}), k))
    decisions = []
    for key in candidates:
        add = len(selected) < LABEL_CAP and len(state_closure(selected + [key])) <= STATE_CAP
        decisions.append({"key": list(key), "included": add,
                          "metadata_sha256": metadata_order({"state": key[0], "preferred": key[1], "other": key[2],
                                                             "kind": strict[key]["kind"]}).hex()})
        if add:
            selected.append(key)
    # Author-facing relation order does not mark witness membership in R.
    selected.sort(key=lambda k: (metadata_order({"state": k[0], "preferred": k[1], "other": k[2],
                                               "kind": strict[k]["kind"]}), k))
    states = sorted(state_closure(selected), key=lambda sid: (metadata_order({"state": sid}), sid))
    return selected, states, decisions


def projected_feedback(result):
    return {"initial_value_exact": result["initial_value_exact"],
            "value_exact": result["value_exact"], "selected": result["selected"],
            "improvements": result["improvements"], "patches_attempted": result["patches_attempted"],
            "search_nodes": result["meter"]["search_nodes"],
            "feature_work": result["meter"]["feature_work"],
            "repair_work": result["meter"]["repair_work"],
            "cpu_seconds": result["cpu_seconds"], "wall_seconds": result["wall_seconds"]}


def masked_cases(states, rmap, graphs, feedback, seed):
    mapping = {sid: f"case_{i:03d}" for i, sid in enumerate(states)}
    groups = sorted({rmap[sid].get("pair", rmap[sid]["cluster"]) for sid in states},
                    key=lambda group: (metadata_order({"group": group}), group))
    gmap = {group: f"group_{i:03d}" for i, group in enumerate(groups)}
    seed_rows = {r["id"]: r["result"] for r in seed["kernel_rows"]}
    cases = []
    for sid in states:
        record, graph = rmap[sid], graphs[sid]
        domain = "synthetic_temporal" if record["paired"] else "source_induced_conflict"
        context = {"domain": domain, "weights": "unit",
                   "group": gmap[record.get("pair", record["cluster"])],
                   "paired_side": record.get("side")}
        if record["paired"]:
            family = record["family"].removeprefix("temporal_unit_")
            regime, horizon = family.rsplit("_", 1)
            context.update(resource_regime=regime, horizon_profile=horizon)
        cases.append({"case": mapping[sid], "context": context,
                      "graph": {"name": mapping[sid],
                                "nodes": [{"id": v, "weight": graph.nodes[v].weight,
                                           "duration": graph.nodes[v].end - graph.nodes[v].start}
                                          for v in sorted(graph.nodes)],
                                "edges": [list(edge) for edge in sorted(graph.edges)],
                                "constraints": {"station_gap": graph.constraints.get("station_gap", graph.constraints.get("ground_trans_time", 0)),
                                                "satellite_gap": graph.constraints.get("satellite_gap", graph.constraints.get("satellite_change_time", 0))}},
                      "fixed": list(record["fixed"]), "excluded": list(record["excluded"]),
                      "degree_repair_feedback": projected_feedback(feedback[sid]["result"]),
                      "shared_seed_repair_feedback": projected_feedback(seed_rows[sid])})
    return cases, mapping


def build_packets(seed, cases, mapping, strict, selected, cycles, occurrences, config):
    shared_program = {"name": "shared_seed_v06r2", "features": seed["program"]["features"],
                      "rule": seed["program"]["rule"], "rationale": ""}
    if canonical({k: shared_program[k] for k in ("features", "rule")}) != canonical({k: seed["program"][k] for k in ("features", "rule")}):
        raise ValueError("Masking changed the common deployment AST")
    common = {
        "version": "masked_refinement_packet_v06_002",
        "task": "Develop a new batch of typed structural features and numeric ranking rules, starting from the shared seed code and shown TRAIN graph/quality/work observations.",
        "shared_seed_program": shared_program,
        "shared_seed_macro_feedback": {k: seed["kernel_summary"][k] for k in ("macro_quality_exact", "macro_work_exact")},
        "base_features": list(FEATURES), "typed_operations": graph_operation_library(),
        "limits": {"additional_features": 6, "expression_nodes_per_feature": 48,
                   "expression_depth_per_feature": 8, "rule_characters": 2000,
                   "rule_AST_nodes": 256, "program_slots": SLOTS},
        "rule_language": "Python numeric expression with +,-,*,/,min,max,abs, comparisons, if/else, and/or/not. No exponentiation, subscripts, attributes, imports, ID/benchmark/seed lookup or model calls.",
        "operation_notes": {
            "current_snapshot": "root is the scored action; available is the current active set; neighbors(root) is restricted to that set. Node IDs in the examples are unchanged because the polynomial library uses deterministic ID tie breaks, but the rule cannot read IDs.",
            "packing_features": "clique_cover_weight returns a deterministic weight-ordered clique partition sum; greedy_independent_weight returns a deterministic weight-ordered feasible packing. Both are polynomial numeric features, not conditional optimal-value calls.",
            "division": "An exactly zero denominator is rejected. Guard typed and numeric-rule division with max(epsilon,abs(denominator)).",
            "residual": "difference(difference(available,neighbors(root)),singleton(root)) is the retained set after choosing root.",
            "base": "The full input fields of base9 are shown: weight,duration,degree,conflict_weight,max_conflict_weight,compatible_weight,remaining_count,station_gap,satellite_gap. Edges define explicit conflicts; no hidden physical fields are scored."},
        "deployment_kernel": {k: config[k] for k in ("seconds", "clock", "repair_config", "quality_normalization", "all_arms_share", "cap_scope")},
        "common_observation_scope": "These graphs and the seed are chosen adaptively from the completed previous TRAIN round, not an independent new sample. Quality is feasible repair reward/total graph weight; work is charged feature plus repair operations. Program priorities affect the local greedy feasible proposal and pivot vertex, with shared include-first traversal, bounds, patch targets and all caps.",
        "authoring_constraints": "Return exactly8 diverse hypotheses once without executing evaluations. Read only packet.json; do not inspect old banks, other files, internet or TEST. Keep the six-feature grammar unchanged; feature expressions cannot reference other custom features. Missing, invalid and duplicate original slots receive no replacement.",
        "examples": cases,
        "response_wire_scope": "matched_cold_bank_v06 is the legacy JSON wire tag, not a claim that this adaptive experiment is an independent cold round.",
        "output_schema": {"version": "matched_cold_bank_v06",
                          "block": "integer0..4", "arm": "witness/relations/objective",
                          "candidates": [{"name": "unique_short_name", "features": [{"name": "new_identifier", "expression": {"op": "OP", "args": []}}],
                                          "rule": "numeric expression", "rationale": "brief reason"}]},
    }
    relations = [{"label_id": f"r{i:03d}", "case": mapping[k[0]], "preferred": k[1], "other": k[2],
                  "lower_exact": strict[k]["lower_exact"], "upper_exact": strict[k]["upper_exact"],
                  "scope": "preferred-minus-other full-residual conditional completion difference at the explicit shown F/X boundary; not a restricted-patch pivot guarantee"}
                 for i, k in enumerate(selected)]
    label_ids = {key: relations[i]["label_id"] for i, key in enumerate(selected)}
    explicit = []
    for cycle in cycles:
        reqs = [{"label_id": label_ids[k], "preferred": mapping[k[0]] + "|" + k[1],
                 "other": mapping[k[0]] + "|" + k[2]} for k in cycle["requirements"]]
        joins = []
        for join in cycle["joins"]:
            ns, n = occurrences[join["negative"]]; ps, p = occurrences[join["positive"]]
            joins.append({"negative": mapping[ns] + "|" + n, "positive": mapping[ps] + "|" + p,
                          "negative_vector": join["negative_vector"], "positive_vector": join["positive_vector"]})
        explicit.append({"kind": cycle["kind"], "requirements": reqs, "equality_joins": joins,
                         "interface": {"base9": list(FEATURES), "demanded_additional_features": seed["interface"]["demanded_features"]},
                         "comparison": "exact integer and binary-float numeric equality; no tolerance"})
    packets = {}
    for block in range(BLOCKS):
        for arm in ARMS:
            packet = {**common, "block": block, "arm": arm}
            if arm == "objective":
                packet["authoring_objective"] = "Improve equal-family feasible repair reward/total graph weight, then reduce equal-family charged feature+repair work. Use the common seed and graph feedback to propose new code."
            else:
                packet["certified_relations"] = relations
                packet["shared_seed_scalar_fit_feedback"] = {
                    "strict_passed": seed["interface"]["strict_passed"], "strict_total": 594,
                    "shown_relations": [{"label_id": label_ids[(c["state"], c["preferred"], c["b"] if c["preferred"] == c["a"] else c["a"])],
                                         "score_preferred": c["score_preferred"], "score_other": c["score_other"], "passed": c["passed"]}
                                        for c in seed["interface"]["strict_checks"]
                                        if (c["state"], c["preferred"], c["b"] if c["preferred"] == c["a"] else c["a"]) in label_ids]}
                packet["authoring_objective"] = "Retain finite execution and feasible shared-kernel output; require the full TRAIN quotient of base9 plus rule-demanded additional features to be acyclic on all594 strict requirements. Then maximize actual strict scalar inequalities with score_preferred > score_other +1e-8, then equal-family reward/total graph weight, then minimize charged feature+repair work, then original slot. Unused additional features cannot repair the demanded interface. A DAG allows some real-valued scorer, not necessarily this bounded scalar rule. Offline interface caps remain100million feature units and60CPU seconds. No hard gate is weakened."
                packet["label_scope"] = "Saved certificates concern the displayed full residual snapshots with identical explicit F/X; repair quality is assessed separately. All120 original TRAIN states remain in assessment, including states not printed here."
            if arm == "witness":
                packet["explicit_equality_joins"] = explicit
                packet["representation_instruction"] = "The displayed strict arcs and exact equality joins close a directed cycle under the current demanded interface. Changing only the scalar rule cannot realize all these inequalities. Propose a new typed structural distinction actually demanded by the rule; splitting a single join does not by itself prove that the full TRAIN quotient is acyclic. The controller rechecks the entire unchanged TRAIN quotient."
            packets[f"block_{block}_{arm}"] = packet
    return packets, common, label_ids


def audit_packets(packets, rmap, mapping):
    forbidden_objective = ("certified_relations", "explicit_equality_joins", "scalar_fit", "strict_passed",
                           "quotient", "acyclic", "ineligible", "equality_joins")
    common_fields = ("shared_seed_program", "shared_seed_macro_feedback", "examples", "typed_operations", "limits", "deployment_kernel")
    first = next(iter(packets.values()))
    sizes = {}
    for stem, packet in packets.items():
        raw = encoded(packet, compact=True)
        sizes[stem] = len(raw)
        if len(raw) > PACKET_BYTE_CAP:
            raise ValueError("Packet exceeds registered byte cap")
        text = raw.decode("utf-8")
        if any(sid in text for sid in rmap) or any(r["cluster"] in text for r in rmap.values()):
            raise ValueError("An original source/state identifier leaked into authoring")
        if any(packet[k] != first[k] for k in common_fields):
            raise ValueError("Arms received different common seed/graph/feedback content")
        if packet["arm"] == "objective" and any(word in text.lower() for word in forbidden_objective):
            raise ValueError("Objective arm received gate, label or fit disclosure")
        if packet["arm"] == "relations" and "explicit_equality_joins" in packet:
            raise ValueError("Relations arm received witness-only joins")
        for case in packet["examples"]:
            sid = next(s for s, name in mapping.items() if name == case["case"])
            original = Graph.from_dict(rmap[sid]["graph"])
            if {n["id"] for n in case["graph"]["nodes"]} != set(original.nodes):
                raise ValueError("Masking changed node IDs and tie semantics")
            if {tuple(edge) for edge in case["graph"]["edges"]} != set(original.edges):
                raise ValueError("Masking changed the exact conflict graph")
    return {"checks_passed": True, "packet_bytes": sizes, "max_packet_bytes": max(sizes.values()),
            "objective_gate_label_fit_disclosure": False, "common_fields_identical": list(common_fields),
            "original_state_source_metadata_masked": True, "original_node_IDs_preserved": True}


def prepare(output, r1_directory, evidence_path, config_path, selection_plan):
    output, r1_directory = Path(output), Path(r1_directory)
    if output.exists():
        raise ValueError("Never overwrite a draft, packet inventory or old round")
    check_sources()
    selection_plan = Path(selection_plan)
    plan = validate_plan(read(selection_plan))
    evidence_path, config_path = Path(evidence_path), Path(config_path)
    selection = read(r1_directory / "selection.json")
    execution = read(r1_directory / "execution.json")
    parent = read(r1_directory / "parent_protocol.json")
    results = r1_directory / "candidate_results.jsonl"
    if (selection["test_accessed"] or execution["test_accessed"]
            or selection["selection_split"] != "train" or execution["selection_split"] != "train"
            or digest(results) != selection["candidate_results_sha256"]
            or digest(r1_directory / "parent_protocol.json") != selection["parent_protocol_sha256"]
            or digest(r1_directory / "supplement_protocol.json") != selection["supplement_protocol_sha256"]
            or digest(r1_directory / "execution.json") != selection["execution_sha256"]):
        raise ValueError("R1 results are not bound to their immutable TRAIN receipts")
    if any(execution["source_sha256"].get(name) != expected for name, expected in SOURCES.items()):
        raise ValueError("R1 assessment used another source version")
    if digest(evidence_path) != parent["training_evidence_sha256"] or digest(config_path) != parent["kernel_config_sha256"]:
        raise ValueError("R1 evidence/config bytes changed")
    evidence, config = read(evidence_path), read(config_path)
    if config != parent["kernel_config"] or parent["selector"] != JOINT_SELECTOR:
        raise ValueError("R2 must preserve the R1 shared contract and joint gate")
    rmap, graphs, strict, by_state, feedback = validate_evidence(evidence)
    for row in feedback.values():
        result = row["result"]
        if (not result["completed"] or not result["feasible"] or result["config"] != config["repair_config"]
                or result["declared_seconds"] != config["seconds"] or result["deadline_clock"] != config["clock"]):
            raise ValueError("Common Degree feedback did not use the fixed shared kernel")
    seed, inventory = choose_seed(results, rmap, graphs, strict, config)
    cycles, mandatory, occurrences = concrete_cycles(seed, rmap, graphs, strict, by_state)
    selected, states, decisions = choose_feedback(seed, evidence["records"], strict, mandatory)
    cases, mapping = masked_cases(states, rmap, graphs, feedback, seed)
    packets, common, label_ids = build_packets(seed, cases, mapping, strict, selected, cycles, occurrences, config)
    audit = audit_packets(packets, rmap, mapping)
    output.mkdir(parents=True)
    files = {}
    for stem, packet in packets.items():
        path = output / "packets" / (stem + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded(packet, compact=True))
        prompt = (f"Read only packet.json. This is TRAIN-adaptive refinement round2, block {packet['block']}, arm {packet['arm']}. "
                  "Author exactly8 candidates in one fresh isolated session from the frozen grammar, shared seed and supplied observations; do not execute evaluations or read other files. "
                  "Return one JSON object with exactly version,block,arm,candidates, using version matched_cold_bank_v06 as the legacy response wire format only. "
                  "Each candidate has exactly name,features,rule,rationale. No fences or prose. Missing, malformed or duplicate raw positions get no replacement. "
                  "No other session is visible. All15 sessions and all120 original positions are frozen before any round2 assessment.\n")
        (path.with_suffix(".prompt.md")).write_bytes(prompt.encode("utf-8"))
        for suffix in (".json", ".prompt.md"):
            name = "packets/" + stem + suffix
            files[name] = digest(output / name)
    shutil.copyfile(evidence_path, output / "training_evidence.json")
    shutil.copyfile(selection_plan, output / "selection_plan.json")
    selection_receipt = {
        "version": "v06_r2_common_seed_selection_002", "selection_split": "train", "test_accessed": False,
        "all_R1_original_positions_retained": 120, "seed_source_id": seed["id"],
        "seed_pool": "completed static-valid finite unchanged-assessor interface; full120 feasible completed kernels; demanded quotient contradictory",
        "selector": ["maximize_actual_strict_fit", "maximize_exact_macro_family_quality", "minimize_exact_macro_family_work", "lexicographic_source_id"],
        "seed_strict_passed": seed["interface"]["strict_passed"], "seed_strict_total": 594,
        "seed_kernel_summary": seed["kernel_summary"], "seed_program": seed["program"],
        "deployment_AST_sha256": seed["deployment_AST_sha256"], "raw_original_slot_inventory": inventory,
        "finite_status_scope": "unchanged f640 completed finite interface; every saved strict score and witness vector independently finite-checked; no new candidate execution",
        "cycle_witnesses": seed["interface"]["quotient"]["structural_witnesses"],
        "mandatory_cycle_requirements": [list(k) for k in mandatory],
        "selected_requirements": [{**strict[k], "label_id": label_ids[k]} for k in selected],
        "feedback_cap_decisions": decisions, "masked_state_bindings": mapping,
        "all_common_states": states, "paired_companions_included": True,
        "authoring_access_forbidden": True,
    }
    write(output / "seed_selection.json", selection_receipt)
    write(output / "packet_audit.json", audit)
    protocol = {
        "version": VERSION, "status": "DRAFT_NOT_AUTHORIZED_FOR_AUTHORING",
        "refinement_round": 2, "TRAIN_driven_adaptation": True, "independent_repetition_claimed": False,
        "registered_before_round2_authoring": False, "selection_plan_status": "approved_pre_generation_pending_transport_freeze",
        "selection_plan": plan, "selection_plan_sha256": digest(selection_plan),
        "blocks": BLOCKS, "arms": list(ARMS), "slots_per_block_arm": SLOTS, "requested_slots": BLOCKS * len(ARMS) * SLOTS,
        "preplanned_extra_whole_block": True, "all120_original_slots_assessed": True,
        "cohort": "first four by-index blocks with all three transport-complete authoring cells; conditional cohort, not missing-at-random",
        "no_adaptive_supplement": True, "no_retry_or_replacement": True,
        "transport_requested": {"workers": 2, "timeout_seconds": 1800, "reasoning_effort": "ultra", "fresh_namespace_required": True,
                                "same_requested_model_and_settings": True, "served_model_identity_not_inferred_from_configuration": True},
        "selection_split": "train", "test_accessed": False,
        "seed_selection_sha256": digest(output / "seed_selection.json"),
        "packet_selection_salt": SALT, "packet_cases": len(cases), "packet_strict_relations": len(selected),
        "packet_cycle_witnesses": len(cycles), "packet_concrete_equality_joins": sum(len(c["joins"]) for c in cycles),
        "packet_limits": {"labels": LABEL_CAP, "states_including_paired_companions": STATE_CAP, "bytes": PACKET_BYTE_CAP},
        "packet_common_sha256": canonical(common), "packet_sha256": files,
        "training_evidence_sha256": digest(output / "training_evidence.json"),
        "R1_candidate_results_sha256": digest(results), "R1_selection_sha256": digest(r1_directory / "selection.json"),
        "R1_execution_sha256": digest(r1_directory / "execution.json"),
        "R1_parent_protocol_sha256": digest(r1_directory / "parent_protocol.json"),
        "R1_supplement_protocol_sha256": digest(r1_directory / "supplement_protocol.json"),
        "kernel_config_sha256": digest(config_path), "kernel_config": config,
        "joint_selector_unchanged": JOINT_SELECTOR,
        "gate": "base9 plus rule-demanded additional features; full exact-numeric unchanged TRAIN quotient acyclic",
        "all_train_strict_requirements": 594, "interface_limits": parent["interface_limits"],
        "original_R1_failed_gates_retained": True, "response_wire_format": "matched_cold_bank_v06",
        "response_wire_format_does_not_mean_independent_cold_experiment": True,
        "source_sha256": {"builder": digest(__file__), "assessment": SOURCES["synthesis_study_v06.py"],
                          "kernel": SOURCES["repair_v06.py"], "typed_library": SOURCES["graph_features.py"],
                          "compiled_runtime": SOURCES["compiled.py"]},
        "all_unchanged_assessment_sources": dict(SOURCES),
        "causal_or_model_population_advantage_claimed": False,
    }
    write(output / "draft_protocol.json", protocol)
    controlled = ["training_evidence.json", "selection_plan.json", "seed_selection.json", "packet_audit.json", "draft_protocol.json"]
    files.update({name: digest(output / name) for name in controlled})
    write(output / "preparation_receipt.json", {"version": "v06_r2_draft_preparation_002", "utc": utc(),
          "final_protocol_exists": False, "authoring_authorized": False,
          "source_sha256": digest(__file__), "immutable_prepared_files_sha256": files})
    return {"draft": str(output), "seed": seed["id"], "cases": len(cases), "labels": len(selected),
            "cycle_arcs": len(mandatory), "packets": len(packets), "raw_slots": BLOCKS * len(ARMS) * SLOTS,
            "max_packet_bytes": audit["max_packet_bytes"], "preparation_sha256": digest(output / "preparation_receipt.json"),
            "authoring_authorized": False}


def finalize(study, selection_plan, transport_source):
    """Explicit second phase, usable only with an approved pre-authoring plan."""
    study, selection_plan, transport_source = Path(study), Path(selection_plan), Path(transport_source)
    if any((study / name).exists() for name in ("protocol.json", "freeze_receipt.json", "transport_amendment.json", "authoring_completion.json", "responses", "receipts")):
        raise ValueError("Finalization is one-time and must precede all R2 authoring")
    check_sources()
    receipt = read(study / "preparation_receipt.json")
    if receipt["source_sha256"] != digest(__file__):
        raise ValueError("Draft builder source changed")
    for name, expected in receipt["immutable_prepared_files_sha256"].items():
        if digest(study / name) != expected:
            raise ValueError("Prepared draft byte changed: " + name)
    plan = validate_plan(read(selection_plan))
    if digest(selection_plan) != digest(study / "selection_plan.json"):
        raise ValueError("The approved selection plan changed after draft preparation")
    if not transport_source.is_file() or transport_source.name == "author_matched_cli_v06.py":
        raise ValueError("R2 requires a fresh transport source and isolated namespace")
    protocol = read(study / "draft_protocol.json")
    protocol.update(status="FROZEN_BEFORE_ROUND2_AUTHORING", registered_before_round2_authoring=True,
                    selection_plan_status="approved_pre_generation", selection_plan=plan,
                    selection_plan_sha256=digest(selection_plan), selector=JOINT_SELECTOR,
                    quality_only_selector=QUALITY_SELECTOR)
    protocol["source_sha256"]["authoring_transport"] = digest(transport_source)
    write(study / "protocol.json", protocol)
    protocol_hash = digest(study / "protocol.json")
    write(study / "freeze_receipt.json", {"version": "v06_refinement_freeze_002", "utc": utc(),
          "before_round2_authoring": True, "R1_assessment_already_completed": True,
          "protocol_sha256": protocol_hash, "selection_plan_sha256": digest(study / "selection_plan.json"),
          "preparation_receipt_sha256": digest(study / "preparation_receipt.json"),
          "packet_sha256": protocol["packet_sha256"], "training_evidence_sha256": protocol["training_evidence_sha256"]})
    write(study / "transport_amendment.json", {"version": "v06_refinement_native_transport_002",
          "original_protocol_sha256": protocol_hash, "decided_before_any_round2_authoring_or_assessment": True,
          "R1_assessment_already_completed": True, "native_cli_ephemeral_isolated_read_only": True,
          "new_namespace_required": True, "source_sha256": digest(transport_source),
          "workers": 2, "timeout_seconds": 1800, "no_retry": True,
          "served_model_identity_unknown_until_event_receipt": True,
          "cells": [{"response_file": f"block_{b}_{a}.json", "packet_sha256": digest(study / "packets" / f"block_{b}_{a}.json")}
                    for b in range(BLOCKS) for a in ARMS]})
    return {"frozen": str(study), "protocol_sha256": protocol_hash, "raw_slots": 120,
            "before_round2_authoring": True, "R1_assessment_already_completed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    draft = sub.add_parser("prepare")
    draft.add_argument("--out", required=True)
    draft.add_argument("--r1-results", default="experiments/discovery/v06_synthesis_server_001/llm")
    draft.add_argument("--evidence", default="experiments/discovery/v06_authoring_001/training_evidence.json")
    draft.add_argument("--config", default="configs/repair_train_v06_001.json")
    draft.add_argument("--selection-plan", default="configs/refinement_selection_v06_002.json")
    final = sub.add_parser("finalize")
    final.add_argument("--study", required=True)
    final.add_argument("--selection-plan", required=True)
    final.add_argument("--transport-source", required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(args.out, args.r1_results, args.evidence, args.config, args.selection_plan)
    else:
        result = finalize(args.study, args.selection_plan, args.transport_source)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
