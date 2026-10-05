"""Thirty-two deterministic, matched-language graph-grammar candidates.

Universal MWIS score/feature templates, frozen without inspecting any data or
label. Includes cheap base rules, local induced subgraphs and broader residual
completion primitives. Actual computation cost is charged by the same runner.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

from train_context import PROJECT, digest, encoded, freeze_json, library, require
from llm_cli_proposer import program_policy


def op(name, *args):
    return dict(op=name, args=list(args))


def make_bank():
    root, available = op("root"), op("available")
    neighbors = op("neighbors", root)
    residual = op("difference", op("difference", available, neighbors), op("singleton", root))
    definitions = dict(
        neighbor_edges=op("count", op("induced_edges", neighbors)),
        neighbor_edge_min=op("edge_min_weight_sum", op("induced_edges", neighbors)),
        neighbor_edge_product=op("edge_weight_product_sum", op("induced_edges", neighbors)),
        neighbor_pack=op("greedy_independent_weight", neighbors),
        neighbor_cover=op("clique_cover_weight", neighbors),
        residual_edges=op("count", op("induced_edges", residual)),
        residual_edge_min=op("edge_min_weight_sum", op("induced_edges", residual)),
        residual_edge_product=op("edge_weight_product_sum", op("induced_edges", residual)),
        residual_pack=op("greedy_independent_weight", residual),
        residual_cover=op("clique_cover_weight", residual),
        available_edges=op("count", op("induced_edges", available)),
    )
    # Each template is meaningful independently of the dataset's IDs or gap values.
    base_rules = [
        "weight/(1+degree)",
        "weight/(1+conflict_weight)",
        "weight/(1+max_conflict_weight)",
        "weight/(1+degree*degree)",
        "weight/(1+conflict_weight/(1+degree))",
        "weight/(1+0.25*degree)",
        "weight/(1+4*degree)",
        "weight*(1+weight/(1+max_conflict_weight))/(1+degree)",
    ]
    local_rules = [
        "weight*(1+neighbor_edges/(1+degree))/(1+degree)",
        "weight*(1+neighbor_edge_min/(1+conflict_weight))/(1+degree)",
        "weight/(1+conflict_weight/(1+neighbor_edges))",
        "weight/(1+neighbor_pack)",
        "weight/(1+neighbor_cover)",
        "weight*(1+neighbor_edges)/(1+degree*degree)",
        "weight/max(1,1+conflict_weight-neighbor_edge_min/(1+degree))",
        "weight*(1+neighbor_edge_product/(1+conflict_weight*conflict_weight))/(1+degree)",
    ]
    residual_rules = [
        "weight+residual_pack",
        "weight+residual_cover",
        "weight+0.75*residual_pack+0.25*residual_cover",
        "weight+0.25*residual_pack+0.75*residual_cover",
        "weight/(1+degree)-0.25*residual_edge_min/(1+compatible_weight)",
        "weight/(1+degree)-residual_edge_min/(1+compatible_weight)",
        "weight/(1+degree)-residual_edges/(1+remaining_count)",
        "weight/(1+degree)-residual_edge_product/(1+compatible_weight*compatible_weight)",
    ]
    mixed_rules = [
        "weight+residual_pack-0.25*(residual_cover-residual_pack)",
        "weight+residual_pack-(residual_cover-residual_pack)",
        "(weight+residual_pack)/(1+0.05*degree)",
        "weight+residual_pack-0.25*neighbor_pack",
        "weight+residual_pack-0.25*neighbor_cover",
        "weight/(1+degree/(1+available_edges/(1+remaining_count)))",
        "weight*(1+neighbor_edges/(1+degree))/(1+neighbor_pack)",
        "weight+0.5*residual_pack+0.5*residual_cover-0.25*neighbor_pack",
    ]
    candidates = []
    for family, rules in (("base", base_rules), ("local", local_rules), ("residual", residual_rules), ("mixed", mixed_rules)):
        for position, raw_rule in enumerate(rules):
            # Expensive broader-set expressions may be used in repair domains;
            # there is no hidden narrowing of available() in full construction.
            rule = f"({raw_rule}) if remaining_count<=128 else weight/(1+degree)" if family in ("residual", "mixed") else raw_rule
            used = [name for name in definitions if name in raw_rule]
            program = dict(name=f"grammar_{family}_{position}",
                           features=[dict(name=name, expression=deepcopy(definitions[name])) for name in used],
                           rule=rule,
                           rationale="Universal deterministic MWIS grammar template; exact same public typed operations and scorer. "
                                     + ("Broader residual computation is explicitly size-guarded, not secretly localized." if family in ("residual", "mixed")
                                        else "Local or base cost and normalization alternative; no label-specific tuning."))
            program = program_policy(program, False)
            identifier = f"nonllm_grammar.{family}.s{position}"
            candidates.append(dict(id=identifier, arm="nonllm_grammar", family=family, slot=len(candidates), program=program,
                program_content_sha256=hashlib.sha256(encoded(dict(features=program["features"], rule=program["rule"])).encode()).hexdigest(),
                provenance=dict(generator="deterministic stratified typed-grammar enumeration", generator_sha256=digest(Path(__file__)),
                    labels_read=False, TRAIN_results_read=False, VAL_read=False, TEST_read=False, model_calls=0,
                    structural_witness_read=False, total_candidate_budget=32,
                    family_budget="8base+8local+8residual+8mixed", language="unchanged FeatureRuleProgram/graph_operation_library",
                    size_guard="128 active vertices for broader residual templates; all scopes/costs use real currentavailable()",
                    selection="Candidate selection is performed later under the same TRAIN/VAL protocol; no solver run by generator")))
    require(len(candidates) == 32 and len({p["program_content_sha256"] for p in candidates}) == 32,
            "Exactly32 distinct grammar candidate slots are required")
    return dict(version="stk_full_llm_v1_nonllm_grammar_bank", selection_split="TRAIN", TEST_used_for_selection=False,
                generation_read_any_dataset=False, candidate_count=32, language=library(), programs=candidates,
                framing="Deterministic universal grammar candidate search control, not random noise and not a claimed learned feature repair")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "banks" / "nonllm_grammar32.json")
    args = parser.parse_args()
    bank = make_bank()
    freeze_json(args.output, bank)
    print(encoded(dict(bank=str(args.output), candidates=32, model_calls=0, dataset_read=False)))


if __name__ == "__main__":
    main()
