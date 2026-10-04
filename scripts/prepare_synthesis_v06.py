"""Freeze outcome-independent examples and matched TRAIN authoring packets.

The packet subset is chosen from input metadata with the registered hash rule,
not from certificate signs, kernel performance or previously authored banks.
Strict labels and equality joins are the only differences between the arms.
"""
from __future__ import annotations
import argparse
import ast
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.graph_features import FeatureRuleProgram, graph_operation_library
from cipheur.model import Graph
from cipheur.programs import FEATURES
from cipheur.refinement import diagnose_occurrences

ARMS = ("witness", "relations", "objective")
SALT = "v06_author_packet_metadata_only_001"
CONFIG = ROOT / "configs/repair_train_v06_001.json"
PLAN = ROOT / "experiments/discovery/v06_evidence_001"
TRAIN = ROOT / "experiments/runs/v06/v06_evidence_train_001.tar.gz"
BASE = FeatureRuleProgram("base_v06", [], "weight")


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n").encode())


def read_member(archive, suffix, lines=False):
    with tarfile.open(archive) as tar:
        members = [m for m in tar if m.name.endswith("/"+suffix)]
        if len(members) != 1:
            raise ValueError("Expected exactly one archive member: " + suffix)
        raw = tar.extractfile(members[0]).read()
    return [json.loads(line) for line in raw.splitlines() if line] if lines else json.loads(raw)


def order(identity):
    return sha256((SALT+"|"+identity).encode()).digest()


def select_packet_records(records):
    train = [r for r in records if r["split"] == "train"]
    selected = []
    for family in ("DIMACS", "SATLIB"):
        rows = sorted((r for r in train if r["family"] == family), key=lambda r: order(r["cluster"]))
        selected.extend(rows[:3])
    for family in sorted({r["family"] for r in train if r["paired"]}):
        rows = [r for r in train if r["family"] == family]
        first = min({r["cluster"] for r in rows}, key=order)
        selected.extend(sorted((r for r in rows if r["cluster"] == first), key=lambda r:r["side"]))
    if len(selected) != 18 or len({r["id"] for r in selected}) != 18:
        raise ValueError("Registered 18-state packet frame changed")
    return selected


def masked_graph(graph, number):
    mapping = {old: f"n{i:03d}" for i, old in enumerate(sorted(graph.nodes))}
    # No physical/resource metadata is available to the typed graph DSL.
    return {"name": f"case_{number:02d}",
            "nodes": [{"id": mapping[v], "weight": graph.nodes[v].weight,
                       "duration": graph.nodes[v].end-graph.nodes[v].start} for v in sorted(graph.nodes)],
            "edges": [[mapping[a], mapping[b]] for a,b in sorted(graph.edges)],
            "constraints": graph.constraints}, mapping


def prepare(output, feedback_archive):
    output, feedback_archive = Path(output), Path(feedback_archive)
    if output.exists():
        raise ValueError("Preserve original authoring inventory; never overwrite")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    receipt = json.loads((PLAN/"freeze_receipt.json").read_text(encoding="utf-8"))
    if file_hash(PLAN/"data.json") != receipt["data_sha256"]:
        raise ValueError("Frozen graph inputs changed")
    records = json.loads((PLAN/"data.json").read_text(encoding="utf-8"))["records"]
    selected = select_packet_records(records)  # No outcomes used by selection.
    labels = {r["id"]:r for r in read_member(TRAIN,"results.jsonl",True)}
    feedback = {r["id"]:r for r in read_member(feedback_archive,"results.jsonl",True)}
    if set(labels) != set(feedback) or len(labels) != 120:
        raise ValueError("Feedback and certificates must cover all 120 TRAIN states")
    if sum(q["difference"]["status"]=="strict" for r in labels.values() for q in r["rows"])!=594:
        raise ValueError("Certified strict TRAIN frame changed")
    for row in feedback.values():
        r=row["result"]
        if r["config"]!=config["repair_config"] or r["declared_seconds"]!=config["seconds"] or r["deadline_clock"]!=config["clock"]:
            raise ValueError("Common feedback used another shared-kernel contract")
    audit_path=ROOT/"experiments/analysis/v06/evidence_train_audit_v06_001.json"
    audit=json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["archive_sha256"]!=file_hash(TRAIN) or audit["unverified_components"]:
        raise ValueError("Independent certificate audit is incomplete or bound to other bytes")
    examples, relations, joins = [], [], []
    occurrences, requirements = {}, []
    for number, record in enumerate(selected):
        g = Graph.from_dict(record["graph"])
        masked, mapping = masked_graph(g, number)
        result = feedback[record["id"]]["result"]
        if not result["feasible"] or not result["completed"]:
            raise ValueError("Common reference failed on a packet case")
        case = masked["name"]
        examples.append({"case":case,"stratum":record["family"],"graph":masked,
            "paired_case": record.get("side"),
            "degree_repair_feedback": {
                "initial_value_exact":result["initial_value_exact"],"value_exact":result["value_exact"],
                "selected":[mapping[v] for v in result["selected"]],
                "improvements":result["improvements"],"patches_attempted":result["patches_attempted"],
                "search_nodes":result["meter"]["search_nodes"],
                "feature_work":result["meter"]["feature_work"],"repair_work":result["meter"]["repair_work"]}})
        active = set(g.nodes)
        for q in labels[record["id"]]["rows"]:
            if q["difference"]["status"] != "strict":
                continue
            a,b = q["a"],q["b"]
            p = q["difference"]["preferred"]
            n = b if p == a else a
            lid = "r"+str(len(relations)).zfill(4)
            pv,nv = BASE.evaluate_features(g,p,active),BASE.evaluate_features(g,n,active)
            po,no = case+"|"+mapping[p],case+"|"+mapping[n]
            occurrences[po],occurrences[no] = pv,nv
            requirements.append({"preferred":po,"other":no,"label_id":lid})
            relations.append({"label_id":lid,"case":case,"preferred":mapping[p],"other":mapping[n],
                              "lower_exact":q["difference"]["lower_exact"],
                              "upper_exact":q["difference"]["upper_exact"],
                              "scope":"strict conditional completion value at the shown empty F/X boundary"})
            if pv == nv:
                joins.append({"kind":"self_loop","label_id":lid,"case":case,
                    "negative":mapping[n],"positive":mapping[p],"equal_base9":pv,
                    "neighbor_sets": {mapping[v]:[mapping[u] for u in sorted(g.adj[v])] for v in (p,n)},
                    "neighbor_induced_edges": {mapping[v]:[[mapping[a],mapping[b]] for a,b in sorted(g.edges)
                        if a in g.adj[v] and b in g.adj[v]] for v in (p,n)}})
    diagnosis = diagnose_occurrences(occurrences,requirements)
    common = {
        "task":"Jointly synthesize structural features and ranking expressions for constraint-adaptive MWIS repair.",
        "base_features":list(FEATURES),"typed_operations":graph_operation_library(),
        "limits":{"additional_features":6,"expression_nodes":48,"expression_depth":8,
                  "rule_characters":2000,"rule_AST_nodes":256,"program_slots":8},
        "rule_language":"Python numeric expression with +,-,*,/,min,max,abs, comparisons, if/else, and/or/not. No exponentiation, subscripts, attributes, imports, ID/benchmark/seed lookup or oracle/model calls.",
        "operation_notes":{
            "neighbors":"Neighbors in the current active set; root is the scored action; available is the current active set.",
            "clique_cover_weight":"Polynomial deterministic weight-ordered clique partition sum on the given set. It is a numeric feature; no conditional-optimum call.",
            "greedy_independent_weight":"Polynomial deterministic weight-ordered feasible independent packing on the given set. It is a numeric feature; no conditional-optimum call.",
            "div":"Typed division rejects an exactly zero denominator; use an explicit max(epsilon,abs(denominator)) guard for typed and rule divisions.",
            "base":"Base9 includes weight,duration,degree,conflict_weight,max_conflict_weight,compatible_weight,remaining_count,station_gap,satellite_gap. Duration/reward are one in these examples; station_gap differs between paired cases.",
            "residual":"The set difference(difference(available,neighbors(root)),singleton(root)) describes remaining actions after forcing the candidate. Structural summaries of this and the neighbor set may be informative but must remain polynomial typed operations."},
        "deployment_kernel":config,
        "selection":"All 8 raw slots are retained. Every arm has the same hard full-TRAIN demanded-interface quotient-DAG gate on 594 strict certificates. Additional features absent from the rule do not count for this gate. Then maximize the number of inequalities actually obeyed with score_preferred > score_other + 1e-8; then maximize equal-family mean feasible reward/total graph weight under the identical bounded repair; then minimize equal-family charged feature+repair work; then original slot index. All 120 TRAIN states are used; no TEST labels/quality. A DAG is representation feasibility, not scalar rule fit. Full offline interface assessment has a common cap of100million feature-operation units and60CPUseconds per candidate; reaching a cap retains an ineligible original slot.",
        "evidence_scope":"Example graphs selected solely from frozen TRAIN metadata. Certificates apply to the shown full graph at F=X=empty; they are not certificates about a later restricted patch. Quality and feature computation cost are assessed independently in the shared kernel.",
        "authoring_constraints":"Return exactly8 diverse hypotheses once, without executing any evaluations. Reason from these graphs and permitted polynomial operations; do not consult files other than packet.json, old candidates, internet or TEST. Names/rationales are not deployment semantics. Features must be computed from the current active graph; IDs are only for reading the examples.",
        "examples":examples,
        "output_schema":{"version":"matched_cold_bank_v06","block":"integer0..3","arm":"witness/relations/objective",
                         "candidates":[{"name":"unique_short_name","features":[{"name":"new_identifier","expression":{"op":"OP","args":[]}}],"rule":"numeric expression","rationale":"brief reason"}]}}
    packet_hashes={}
    output.mkdir(parents=True)
    for block in range(4):
        for arm in ARMS:
            packet={"version":"masked_author_packet_v06_001","block":block,"arm":arm,**common}
            if arm != "objective":
                packet["certified_relations"]=relations
            if arm == "witness":
                packet["explicit_equality_joins"]=joins
                packet["full_example_base_diagnosis"]=diagnosis
                packet["witness_instruction"]="Equal vectors with a strict label make rule-only adjustment impossible. Compose missing structural distinctions from the typed operations, then a score using them. Separate the full quotient and fit the actual inequalities; splitting one join alone is not enough. Prefer low cost; declared but unused features cannot repair the deployed interface."
            stem=f"block_{block}_{arm}"
            path=output/"packets"/(stem+".json")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((json.dumps(packet,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode())
            prompt=(f"Read only packet.json. This is cold authoring cell block {block}, arm {arm}. "
                    "Author exactly8 candidates from the frozen grammar and supplied examples, in one batch, with no evaluations or further file access. "
                    "Return one JSON object with exactly version,block,arm,candidates; version matched_cold_bank_v06. "
                    "Each candidate has exactly name,features,rule,rationale. No fences or prose. Missing, invalid and duplicate slots receive no replacement. "
                    "The typed expression limits are per additional feature, and feature expressions cannot reference other custom features. "
                    "Retain uncertain but reasoned hypotheses; the controller will evaluate all original slots only after all twelve authoring sessions are frozen.\n")
            (output/"packets"/(stem+".prompt.md")).write_bytes(prompt.encode())
            for suffix in (".json",".prompt.md"):
                relative="packets/"+stem+suffix
                packet_hashes[relative]=file_hash(output/relative)
    # Only the controller sees all TRAIN labels and original input bindings.
    write(output/"training_evidence.json",{"records":[r for r in records if r["split"]=="train"],
        "labels":list(labels.values()),"kernel_feedback":list(feedback.values()),
        "authoring_access_forbidden":True})
    protocol={"version":"matched_synthesis_v06_001","registered_before_new_authoring":True,
        "blocks":4,"arms":list(ARMS),"slots_per_block_arm":8,"requested_slots":96,
        "same_requested_settings_all_sessions":True,"compute_matching_claimed":False,
        "selection_split":"train","test_accessed":False,
        "packet_selection_salt":SALT,"packet_selected_input_ids":[r["id"] for r in selected],
        "packet_cases":len(examples),"packet_strict_relations":len(relations),"packet_explicit_alias_joins":len(joins),
        "packet_common_sha256":canonical(common),"packet_sha256":packet_hashes,
        "train_evidence_archive_sha256":file_hash(TRAIN),"train_feedback_archive_sha256":file_hash(feedback_archive),
        "independent_train_evidence_audit_sha256":file_hash(audit_path),
        "training_evidence_sha256":file_hash(output/"training_evidence.json"),
        "kernel_config_sha256":file_hash(CONFIG),"kernel_config":config,
        "gate":"Demanded additional features plus always-declared base9; full exact numeric TRAIN quotient acyclic",
        "selector":["static_valid_and_finite_full_TRAIN_interface_and_feasible_kernel", "demanded_full_TRAIN_quotient_acyclic", "maximize_actual_strict_fit_margin_1e-8", "maximize_macro_family_reward_over_total_weight", "minimize_macro_family_feature_plus_repair_work", "earlier_original_slot"],
        "failure":"Keep all raw positions; an empty eligible cell produces no winner and no fallback; TEST requires twelve genuine selected programs.",
        "additional_feature_scope":"The gate ignores unused additional features; their declared diagnostic is retained separately.",
        "contrast":{"primary":"witness minus relations","secondary":"relations minus objective"},
        "all_train_strict_requirements":594,"example_graph_selection_outcome_filtering":False,
        "interface_limits":{"max_work":100000000,"cpu_seconds":60},
        "source_sha256":{"builder":file_hash(__file__),"assessment":file_hash(ROOT/"cipheur/synthesis_study_v06.py"),"authoring_transport":file_hash(ROOT/"scripts/author_matched_cli_v06.py"),"kernel":file_hash(ROOT/"cipheur/repair_v06.py"),
                         "typed_library":file_hash(ROOT/"cipheur/graph_features.py"),"compiled_runtime":file_hash(ROOT/"cipheur/compiled.py")}}
    write(output/"protocol.json",protocol)
    write(output/"freeze_receipt.json",{"before_authoring":True,"protocol_sha256":file_hash(output/"protocol.json"),
         "packet_sha256":packet_hashes,"training_evidence_sha256":protocol["training_evidence_sha256"]})
    write(output/"transport_amendment.json",{"version":"v06_native_cli_transport_001",
         "original_protocol_sha256":file_hash(output/"protocol.json"),"decided_before_any_v06_candidate_assessment":True,
         "native_cli_ephemeral_isolated_read_only":True,"cells":[{"response_file":f"block_{b}_{a}.json",
             "packet_sha256":file_hash(output/"packets"/f"block_{b}_{a}.json")} for b in range(4) for a in ARMS],
         "no_retry":True,"served_model_identity_unknown_until_event_receipt":True})
    print(json.dumps({"prepared":str(output),"cases":len(examples),"strict_relations":len(relations),"explicit_joins":len(joins),"protocol_sha256":file_hash(output/"protocol.json")}))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True);p.add_argument("--feedback-archive",required=True)
    args=p.parse_args();prepare(args.out,args.feedback_archive)
