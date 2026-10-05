"""Freeze self-contained TRAIN-only inputs for three matched LLM conditions.

No optimizer or LLM is called. Only the four r000/r001 TRAIN libraries and
their existing formal P0 / expanded-patch / heterogeneous evidence are read.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


SCRIPT = Path(__file__).resolve()
PROJECT = SCRIPT.parents[3]
DEFAULT_DATA = PROJECT.parent / "data" / "两篇论文数据定制化构建" / "CIPHEUR_STK_20261005"
SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
CONDITIONS = ("witness_joint", "relations_joint", "relations_rule_only")
FEATURES = ("weight", "duration", "degree", "conflict_weight", "max_conflict_weight",
            "compatible_weight", "station_gap", "satellite_gap", "remaining_count")
TAGS = dict(A="gW0340_gE0340_s0150", W="gW1200_gE0340_s0150",
            E="gW0340_gE1200_s0150", J="gW1200_gE1200_s0150")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def freeze_json(path, value):
    """Idempotent only for byte-identical data; never replace a frozen context."""
    path = Path(path)
    data = (encoded(value) + "\n").encode("utf-8")
    if path.exists():
        require(path.read_bytes() == data, "Refusing to replace frozen input: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def library(project=PROJECT):
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from cipheur.graph_features import graph_operation_library, MAX_FEATURES, MAX_EXPRESSION_NODES, MAX_EXPRESSION_DEPTH
    return dict(operations=graph_operation_library(), max_features=MAX_FEATURES,
                max_expression_nodes=MAX_EXPRESSION_NODES, max_expression_depth=MAX_EXPRESSION_DEPTH,
                rule_max_characters=2000, rule_max_ast_nodes=256, base9=list(FEATURES),
                program_schema_keys=["name", "features", "rule", "rationale"],
                feature_schema_keys=["name", "expression"],
                constant="Only const has value; every other operation has an args array",
                feature_dependency="Feature expression trees cannot refer to other feature names",
                root="Only root() produces Node; available() is the current residual active NodeSet",
                numeric="Counts/gaps are integer seconds/counts; contact weight/duration are exact Fraction seconds; aggregates use execution math.fsum",
                station_gap="Actual root contact antenna gap, not a global mean/minimum",
                rule_operators="+ - * /; unary +/-; conditional if/else; comparisons; and/or/not; calls min/max/abs only",
                unavailable_inputs="No identifiers, epoch, source, configuration tag, edge-mask accessor, or offline label/oracle operation",
                costs="Generic set/induced-edge/greedy/cover primitives incur their real full graph or repair active-set computation cost",
                selection="Larger score wins; deterministic contact-id tie breaking is kernel-owned and not accessible to the rule")


def build_context(data_root, output_root, project=PROJECT):
    data_root, output_root = Path(data_root).resolve(), Path(output_root).resolve()
    inventory = {}

    def remember(path):
        path = Path(path)
        require(path.is_file(), "Required formal TRAIN file missing: " + str(path))
        inventory[str(path)] = dict(sha256=digest(path), bytes=path.stat().st_size)
        return path

    def read(path):
        return json.loads(remember(path).read_text(encoding="utf-8"))

    hetero = data_root / "extensions" / "heterogeneous_ground_v1"
    stages = dict(p0=data_root / "analysis" / "p0",
                  expanded=data_root / "analysis" / "patch_interface_probe",
                  heterogeneous=hetero / "analysis" / "quad_evidence")
    vectors, vector_ids, requirements, raw_requirements, original_manifests = [], {}, [], [], {}
    certificates, summaries, stage_counts = {}, {}, Counter()

    def vector_id(values):
        require(len(values) == 9, "Evidence must preserve all nine execution coordinates")
        normalized = tuple(str(Fraction(value)) for value in values)
        if normalized not in vector_ids:
            identifier = "v" + str(len(vectors))
            vector_ids[normalized] = identifier
            vectors.append([identifier, list(normalized)])
        return vector_ids[normalized]

    for stage, folder in stages.items():
        registration = read(folder / "registration.json")
        summaries[stage] = read(folder / "acceptance.json")
        for source in SOURCES:
            manifest = read(folder / source / "query_manifest.json")
            require(manifest["source"] == source and manifest["prepared_before_labels"],
                    "Input must be the named TRAIN source and pre-label manifest")
            original_manifests[stage + "/" + source] = manifest
            query_map = {query["id"]: query for query in manifest["queries"]}
            entries = read(folder / source / "strict_requirements.json")
            for entry in entries:
                require(entry["source"] == source and entry["query_id"] in query_map,
                        "Requirement source or registered query mismatch")
                sign = entry["delta_interval"]
                require(sign["preference"] in ("a", "b"), "Unknown/tie may not become a strict ranking requirement")
                cert_path = folder / entry["certificate_file"]
                if str(cert_path) not in certificates:
                    certificate = read(cert_path)
                    require(digest(cert_path) == entry["certificate_sha256"], "Certificate hash mismatch")
                    certificates[str(cert_path)] = certificate
                pref, other = vector_id(entry["preferred_phi"]), vector_id(entry["other_phi"])
                requirements.append(["r" + str(len(requirements)), stage, source,
                    entry["query_id"], entry["side"], pref, other,
                    sign["preference"], [sign["lower_ticks"], sign["upper_ticks"]]])
                raw_requirements.append(dict(stage=stage, **entry))
                stage_counts[stage] += 1

    # Only Witness-joint receives the frozen cycle, boundary, graph and path evidence.
    quotient = read(stages["heterogeneous"] / "complete_demanded_quotient.json")
    require(quotient["directed_cycle_observed"], "A genuine TRAIN cycle is required for the witness condition")
    cycle = quotient["cycle_trace"]
    require(cycle and all(edge["requirement"]["source"] in SOURCES for edge in cycle), "Cycle is outside TRAIN")
    source, query_id = cycle[0]["requirement"]["source"], cycle[0]["requirement"]["query_id"]
    require(all(edge["requirement"]["query_id"] == query_id for edge in cycle), "Unexpected multi-query primary cycle")
    manifest = original_manifests["heterogeneous/" + source]
    query = next(q for q in manifest["queries"] if q["id"] == query_id)
    structural = read(hetero / "analysis" / "formal_report" / "cycle_structural_witness.json")
    require(structural["source"] == source and structural["query_id"] == query_id, "Structure and cycle differ")
    patch = query["patch_indices"]
    local = {int(global_index): index for index, global_index in enumerate(patch)}
    graphs = {}
    for side, tag in TAGS.items():
        path = remember(hetero / "graphs" / source / (tag + ".npz"))
        require(digest(path) == manifest["graph_npz_sha256"][side], "Witness graph hash differs from manifest")
        with np.load(path, allow_pickle=False) as payload:
            weights = payload["weight_ticks"]
            edges = [[local[int(u)], local[int(v)]] for u, v in zip(payload["edge_u"], payload["edge_v"])
                     if int(u) in local and int(v) in local]
            graph = dict(local_node_indices=list(range(len(patch))), edges=edges,
                weight_seconds=[str(Fraction(int(weights[i]), 1_000_000)) for i in patch],
                root_station_gap_seconds=[int(payload["ground_gap_by_node_ticks"][i]) // 1_000_000 for i in patch],
                a=local[query["a"]], b=local[query["b"]])
            graphs[side] = graph
    cert_path = stages["heterogeneous"] / cycle[0]["requirement"]["certificate_file"]
    original_certificate = certificates[str(cert_path)]
    bound_spaces = {}
    for space, bound in original_certificate["bounds"].items():
        bound_spaces[space] = dict(lower_ticks=bound["lower_ticks"], upper_ticks=bound["upper_ticks"],
            exact=bound["exact"], feasible_lower_selected_local=[local[i] for i in bound["selected_indices"]],
            root_upper_ticks=bound.get("root_upper_ticks"),
            root_clique_partition_local=[[local[i] for i in clique] for clique in bound.get("root_clique_partition_indices", [])])
    location = structural["structural_location"]
    witness = dict(source=source, query_id=query_id,
        exact_cycle=[dict(preferred_vector=vector_id(edge["requirement"]["preferred_phi"]),
                          other_vector=vector_id(edge["requirement"]["other_phi"]),
                          side=edge["requirement"]["side"], delta_interval=edge["requirement"]["delta_interval"]) for edge in cycle],
        boundary=dict(active_P_count=len(patch), fixed_F_count=len(query["fixed_indices"]),
                      excluded_X_count=query["excluded_count"], boundary_hash=cycle[0]["requirement"]["boundary_hash"],
                      commitment="Same frozen feasible F, variable P, excluded X in every configuration"),
        same_local_graphs=graphs, conditional_bounds=bound_spaces,
        signs=original_certificate["signs"], interaction=original_certificate["interaction"],
        changed_E_to_J_edges_local=[[local[u], local[v]] for u, v in structural["new_patch_edge_indices"]],
        nearest_changed_edge_paths=[dict(action=row["action"], minimum_distance=row["minimum_endpoint_distance"],
             path_local=[local[i] for i in row["shortest_path_indices"]],
             reachable_changed_endpoints=row["reachable_changed_endpoints"],
             distance_histogram=row["endpoint_distance_histogram"]) for row in location["roots"]],
        unchanged_local_statistics=structural["rows"],
        limitation="The complete base9 keys, neighbor induced-edge Q and neighbor-degree T are unchanged across E/J; these local statistics do not repair this cycle. Structure lies beyond each root's immediate neighborhood. No successful new feature has been hand-written.",
        bound_scope="Restricted P conditional completions under fixed outside F/X, not a global 72h optimum")

    for filename in ("graph_features.py", "programs.py", "compiled.py", "model.py", "representation.py"):
        remember(project / "cipheur" / filename)
    lib = library(project)
    common = dict(version="stk_full_llm_train_context_v1", split="TRAIN", sources=list(SOURCES),
        source_groups=["r000", "r001"], independent_source_groups=2,
        problem="Maximum-weight independent set of complete satellite-ground contacts in current conflict graph; duration rewards; kernel enforces feasibility.",
        deployment="Frozen candidate score used inside a fixed feasibility kernel on fresh complete instances; no online LLM, labels or conditional oracle.",
        supervision_scope="Offline restricted conditional inclusion preferences can guide ranking but cannot alone guarantee final complete-schedule quality or the best B&B pivot.",
        library=lib, full_base9_columns=list(FEATURES),
        exact_numeric_table="Rational strings preserve Fraction weights and exact binary aggregate outputs; equal vector IDs mean exact full-nine coordinate equality.",
        vectors=vectors,
        strict_relation_columns=["relation_id", "stage", "source", "query_id", "side", "preferred_vector", "other_vector", "delta_preference", "delta_lower_upper_microticks"],
        strict_relations=requirements, strict_relation_counts_by_stage=dict(stage_counts),
        unknown_policy="Unknown intervals are absent from strict relations, not ties or preservation. Repeated/nested queries are not independent examples.",
        heterogeneous_coverage=dict(planned_quadqueries=summaries["heterogeneous"]["planned_quadqueries"],
                                    strict_requirements=summaries["heterogeneous"]["new_strict_requirements"],
                                    interaction=summaries["heterogeneous"]["interaction"]),
        synthesis_objective="Jointly improve genuine held-out complete-schedule quality, specification consistency and feature-computation cost; TRAIN feedback is descriptive. Do not optimize only tiny exact patches or hide computation cost.",
        grammar_policy="Use actual typed operations and bounded rule AST. No source/contact/config identifiers; no hard-coded gap-value lookup or equality memorization of contact duration/weight. Generic small coefficients and safe positive denominator offsets are allowed.")
    context = dict(common=common, witness_only=witness)
    freeze_json(output_root / "context" / "train_context.json", context)
    freeze_json(output_root / "context" / "train_evidence_snapshot.json",
                dict(raw_strict_requirements=raw_requirements, original_primary_query=query,
                     original_primary_certificate=original_certificate, original_structural_receipt=structural,
                     original_cycle_trace=cycle))
    profile = dict(version="stk_full_llm_train_input_profile_v1", split="TRAIN", source_ids=list(SOURCES),
        VAL_read=False, TEST_read=False, solver_calls=0, model_calls=0,
        conditions=list(CONDITIONS), calls_per_condition_per_round=2, candidates_per_call=8,
        planned_initial_candidates_per_condition=16, optional_feedback_rounds=1,
        maximum_candidates_per_condition=32, maximum_real_model_calls=12,
        relation_counts=dict(stage_counts), vector_count=len(vectors), input_inventory=inventory,
        condition_difference="Only witness_joint receives explicit G2 cycle and graph/path/bound structural witness; relations_joint has same numeric strict relations and library; relations_rule_only has same relations but features must be empty.",
        context_sha256=digest(output_root / "context" / "train_context.json"),
        evidence_snapshot_sha256=digest(output_root / "context" / "train_evidence_snapshot.json"),
        scripts=dict(train_context_sha256=digest(SCRIPT)))
    freeze_json(output_root / "context" / "train_context_profile.json", profile)
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-root", type=Path, default=SCRIPT.parents[1])
    args = parser.parse_args()
    profile = build_context(args.data_root, args.output_root)
    print(encoded({k: profile[k] for k in ("split", "relation_counts", "vector_count", "maximum_real_model_calls")}))


if __name__ == "__main__":
    main()
