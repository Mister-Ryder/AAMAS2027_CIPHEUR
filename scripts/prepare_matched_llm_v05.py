"""Freeze matched cold-authoring packets from TRAIN-only evidence.

This builder reads the immutable v04 TRAIN archive and saved TRAIN labels,
never prior held-out quality. Packet selection uses strata and graph identity,
not candidate rewards. All arms share the same masked graphs and degree-rule
feedback. Only certified labels and explicit equality-join guidance differ.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.compiled import schedule_compiled
from cipheur.graph_features import FeatureRuleProgram, graph_operation_library
from cipheur.model import Graph
from cipheur.programs import FEATURES
from scripts.audit_selected_scores_v04 import read_train_archive, reconstruct

ARMS = ("witness", "relations", "objective")
TRAIN_SHA = "e4fd36a6233040b31c77ccffc58827b4a06480953561f783c15f146436399922"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def mask_graph(graph, number):
    nodes = {old: "n" + str(i).zfill(3) for i, old in enumerate(sorted(graph.nodes))}
    sats = {s: "S" + str(i) for i, s in enumerate(sorted({c.satellite for c in graph.contacts}))}
    stations = {s: "G" + str(i) for i, s in enumerate(sorted({c.station for c in graph.contacts}))}
    tasks = {s: "T" + str(i) for i, s in enumerate(sorted({c.task for c in graph.contacts if c.task}))}
    value = graph.to_dict()
    value["name"], value["provenance"] = f"case_{number:02d}", {}
    for c in value["contacts"]:
        c["id"], c["satellite"], c["station"] = nodes[c["id"]], sats[c["satellite"]], stations[c["station"]]
        c["task"] = tasks[c["task"]] if c["task"] else ""
    value["edges"] = [sorted([nodes[a], nodes[b]]) for a, b in sorted(graph.edges)]
    return value, nodes


def prepare(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Preserve frozen packets: choose a new directory")
    archive = ROOT / "experiments/runs/v04/relevance_train_v04_001.tar.gz"
    if sha256(archive.read_bytes()).hexdigest() != TRAIN_SHA:
        raise ValueError("TRAIN archive differs from preregistered bytes")
    objects, provenance = read_train_archive(archive)
    specs_path = ROOT / "experiments/discovery/v03/seed_specifications.json"
    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    endpoints, states, requirements, reconstruction = reconstruct(objects, specs)
    if len(requirements) != 824 or len(objects["training_contexts.jsonl"]) != 66:
        raise ValueError("Unexpected TRAIN evidence frame")
    output.mkdir(parents=True)
    contexts = sorted(objects["training_contexts.jsonl"], key=lambda c: (c["family"], c["size"], Graph.from_dict(c["graph"]).digest()))
    groups = defaultdict(list)
    for c in contexts:
        groups[c["family"]].append(c)
    selected = [rows[0] for _, rows in sorted(groups.items())]
    selected += [rows[1] for _, rows in sorted(groups.items()) if len(rows) > 1][:12-len(selected)]
    # Add both intervention graphs of the first saved explicit cycle witness.
    witness_ids = {j[k] for w in objects["information_repair.json"]["base_quotient"]["structural_witnesses"]
                   for j in w["equality_joins"] for k in ("negative", "positive")}
    witness_digests = {endpoints[oid]["graph_digest"] for oid in witness_ids}
    prior = [s for s in specs if any(Graph.from_dict(s[side]).digest() in witness_digests for side in ("left", "right"))]
    graphs = {Graph.from_dict(c["graph"]).digest(): (Graph.from_dict(c["graph"]), c["family"], c["fixed"] if "fixed" in c else []) for c in selected}
    for s in prior:
        for side in ("left", "right"):
            g = Graph.from_dict(s[side])
            graphs[g.digest()] = (g, "constructed_diagnostic", s["fixed"])
    case_map, masks, examples = {}, {}, []
    degree = FeatureRuleProgram("degree_reference", [], "weight/max(1,degree)", "Shared fixed classical reference.")
    for number, (gd, (g, family, fixed)) in enumerate(sorted(graphs.items())):
        masked, mapping = mask_graph(g, number)
        case_map[gd], masks[gd] = masked["name"], mapping
        # Feedback at the empty boundary is identical across arms, without an
        # LLM-program AST, a selected-bank result, or conditional-optimum label.
        r = schedule_compiled(g, degree, score_slice=True)
        examples.append({"case": masked["name"], "stratum": family, "graph": masked,
                         "degree_reference": {"rule": degree.rule, "reward": r["value"], "feature_work": r["feature_work"],
                                              "selection": [mapping[v] for v in r["selected"]]}})
    labels = []
    per_case = defaultdict(int)
    for index, r in enumerate(requirements):
        p, n = endpoints[r["preferred"]], endpoints[r["other"]]
        gd = p["graph_digest"]
        if gd not in graphs or p["graph_digest"] != n["graph_digest"]:
            continue
        quota = 4 if graphs[gd][1] == "constructed_diagnostic" else 2
        if per_case[gd] >= quota:
            continue
        mapping = masks[gd]
        labels.append({"label_id": f"r{index:04d}", "case": case_map[gd],
                       "fixed": [mapping[v] for v in p["fixed"]], "excluded": [mapping[v] for v in p["excluded"]],
                       "preferred": mapping[p["node"]], "other": mapping[n["node"]],
                       "status": "saved_strict_sound_oracle_requirement",
                       "source_kind": r["metadata"]["kind"]})
        per_case[gd] += 1
    joins = []
    for w in objects["information_repair.json"]["base_quotient"]["structural_witnesses"]:
        for j in w["equality_joins"]:
            p, n = endpoints[j["positive"]], endpoints[j["negative"]]
            gp, gn = p["graph_digest"], n["graph_digest"]
            joins.append({"kind": w["kind"], "positive_case": case_map[gp], "positive": masks[gp][p["node"]],
                          "negative_case": case_map[gn], "negative": masks[gn][n["node"]],
                          "positive_base9": j["positive_vector"], "negative_base9": j["negative_vector"],
                          "interpretation": "Exactly equal declared base vectors join a strict directed cycle. Recover missing graph distinctions with typed features; separating this witness alone does not ensure the full quotient is acyclic."})
    common = {"task": "Synthesize deterministic ranking programs for weighted independent-set contact selection.",
              "base_features": list(FEATURES), "typed_operations": graph_operation_library(),
              "limits": {"additional_features": 6, "expression_nodes": 48, "expression_depth": 8, "rule_characters": 2000,
                         "rule_AST_nodes": 256, "program_slots": 12},
              "rule_language": "One Python numeric expression; +,-,*,/,min,max,abs,comparisons,conditional expression,and/or/not. No power, indexing, imports, identifiers outside base/custom features, IDs, oracle or model calls.",
              "operation_notes": {"neighbors": "Current active neighbors of its node argument; root is the candidate being ranked.",
                                  "available": "Current feasible residual nodes.", "clique_cover_weight": "Deterministic greedy clique partition upper construction on the supplied induced set; ordinary rounded score input.",
                                  "greedy_independent_weight": "Deterministic weight-ordered feasible packing on the supplied induced set; ordinary rounded score input.",
                                  "div": "Typed feature division uses a signed near-zero guard; use explicit max guards in the Python ranking rule."},
              "selection": "All arms receive the same full declared-interface acyclicity gate on 824 saved TRAIN relations, then equal-family TRAIN schedule reward minus 0.002*(relative feature work-1). Highest utility wins; exact tie uses earlier slot. Failure reward is zero and relative work 100. No held-out selection.",
              "examples": examples,
              "output_schema": {"version": "matched_cold_bank_v05", "block": "integer 0..3", "arm": "witness/relations/objective", "candidates": [{"name": "short_unique_name", "features": [{"name": "new_identifier", "expression": {"op": "OP", "args": []}}], "rule": "numeric expression", "rationale": "brief reason"}]}}
    packet_hashes = {}
    for block in range(4):
        for arm in ARMS:
            packet = {"version": "masked_author_packet_v05_001", "block": block, "arm": arm, **common}
            if arm != "objective": packet["certified_relations"] = labels
            if arm == "witness": packet["explicit_cycle_joins"] = joins
            stem = f"block_{block}_{arm}"
            path = output / "packets" / (stem + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(packet, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
            packet_hashes[path.relative_to(output).as_posix()] = sha256(path.read_bytes()).hexdigest()
            prompt = ("You are a cold program-authoring session. Read only this packet and its prompt; do not read existing programs, outcome files, manuscript, other banks, or any test data. "
                      "Use the supplied grammar to author exactly 12 candidate slots in one batch. Do not evaluate schedules or run the oracle. Do not copy another arm. "
                      "Write the exact JSON response once; invalid, missing and exact-duplicate deployment AST slots will remain failed attempts without replacements. "
                      "No outcome-informed follow-up or selection is allowed. Your own technical reasoning is allowed. Preserve all candidates, including uncertain hypotheses.\n\n"
                      f"Packet: `{path.resolve().as_posix()}`\nResponse: `{(output / 'responses' / (stem + '.json')).resolve().as_posix()}`\n"
                      f"Use version matched_cold_bank_v05, block {block}, arm {arm}. Each candidate must have exactly name,features,rule,rationale. Output JSON only in that response file.\n")
            prompt_path = output / "packets" / (stem + ".prompt.md")
            prompt_path.write_text(prompt, encoding="utf-8")
            packet_hashes[prompt_path.relative_to(output).as_posix()] = sha256(prompt_path.read_bytes()).hexdigest()
    # A complete endpoint binding table is a runner-only artifact. Cold authors
    # are explicitly forbidden from reading it or the protocol source inputs.
    state_rows = {sid: {"graph": g.to_dict(), "fixed": list(f), "excluded": list(x)} for sid, (g, active, f, x) in states.items()}
    context_rows = [{"pair_id": c["pair_id"], "side": c["side"], "family": c["family"], "graph": c["graph"],
                     "fixed": next(s["fixed"] for s in c["states"] if any(t["step"] == 0 for t in s["sources"])),
                     "excluded": c["states"][0]["excluded"],
                     "fixed_reward_reference": max(r["value"] for r in c["rows"] if r["completed"]),
                     "fixed_degree_work": next(r["feature_work"] for r in c["rows"] if r["candidate_id"] == "baseline:1")} for c in contexts]
    evidence = {"version": "matched_train_evidence_v05", "contexts": context_rows, "states": state_rows,
                "endpoints": endpoints, "requirements": requirements, "scope": "TRAIN only; authoring access forbidden", "reconstruction": reconstruction}
    write(output / "training_evidence.json", evidence)
    protocol = {"version": "matched_synthesis_v05_001", "stage": "bounded_four_block_pilot", "registered_before_new_authoring": True,
                "served_model": "gpt-6.1-sol", "settings": "Inherited root model/reasoning settings; cold fork_turns=none", "blocks": 4,
                "arms": list(ARMS), "slots_per_block_arm": 12, "requested_slots": 144, "authoring_sessions": 12,
                "independent_API_seeds": None, "token_usage": None, "token_compute_matching_claimed": False,
                "same_grammar_same_examples_same_feedback_same_selector": True,
                "contrasts": {"witness_minus_relations": "incremental explicit equality-join guidance", "relations_minus_objective": "incremental saved certified decision labels"},
                "selection_split": "train", "old_test_selection": False,
                "train_archive": {"path": archive.relative_to(ROOT).as_posix(), "sha256": TRAIN_SHA},
                "training_evidence_sha256": sha256((output / "training_evidence.json").read_bytes()).hexdigest(),
                "packet_sha256": packet_hashes, "packet_common_sha256": digest(common), "packet_natural_snapshot_count": len(selected),
                "packet_distinct_graph_count": len(examples), "packet_relation_count": len(labels), "packet_explicit_join_count": len(joins),
                "selection": {"information_gate_every_arm": True, "utility": "equal-family mean reward/frozen V04 TRAIN feasible reference - 0.002*(equal-family mean work/frozen Degree work - 1)",
                              "cost_penalty": 0.002, "failure_reward": 0, "failure_relative_work": 100, "tie": "exact utility then earlier slot",
                              "reached_regret_selection": False, "reward_reference_not_optimum": True},
                "cpu_seconds": 5.0, "backend": "compiled_demanded", "invalid_missing_duplicate_no_replacement": True,
                "test": {"namespace": 180000000, "dense_namespace_offset": 100000000, "profiles": ["standard", "dense_long"],
                         "regimes": ["balanced", "ground_scarce", "satellite_scarce"], "sizes": [64, 128, 256], "pairs_per_cell": 6,
                         "pairs": 108, "contexts": 216,
                         "generation_after_selection_freeze": True, "no_C3_in_extension": True, "no_public_reselection": True},
                "inference": "Four authoring blocks are a bounded descriptive pilot; no strong model-population superiority inference. Source/seed clusters and both intervention sides remain paired.",
                "diagnostic_scope": "Prior constructed probe contradictions are not naturally discovered obstructions. Natural-only information gate status is reported separately.",
                "provenance": {"train": provenance, "builder_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "seed_specifications_sha256": sha256(specs_path.read_bytes()).hexdigest()}}
    write(output / "protocol.json", protocol)
    (output / "responses").mkdir()
    write(output / "freeze_receipt.json", {"protocol_sha256": sha256((output / "protocol.json").read_bytes()).hexdigest(), "packet_sha256": packet_hashes,
                                         "training_evidence_sha256": protocol["training_evidence_sha256"], "before_authoring": True})
    print(json.dumps({"created": str(output), "slots": 144, "packets": 12, "snapshot_graphs": len(examples), "relations": len(labels)}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    prepare(p.parse_args().out)
