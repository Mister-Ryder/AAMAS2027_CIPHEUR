"""Six predefined non-LLM grammar heuristics in the same declarative language.

These are manually designed controls, not random search and not selected using
TRAIN fit, schedule quality or the structural challenge.  No model is called.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT))
from cipheur.online_v2.typed import validate_recipe
from ingest_synthesis import validate_response_schema


def op(name, *args):
    return {"op": name, "args": list(args)}


def make_controls():
    root = op("root")
    neighbors = op("neighbors", root)
    closed = op("union", neighbors, op("singleton", root))
    twohop = op("difference", op("neighbors_of_set", neighbors), closed)
    definitions = [
        ("grammar.neighbor_edges", "neighbor_edges", op("count", op("induced_edges", neighbors)),
         "weight / (1 + degree) + c0 * neighbor_edges / (1 + degree)",
         "uniform", 3, 16, 1, "greedy"),
        ("grammar.neighbor_mean", "neighbor_mean", op("div", op("sum_weights", neighbors),
             op("max", {"op": "const", "value": 1}, op("count", neighbors))),
         "weight / (1 + degree) - c0 * neighbor_mean / (1 + degree)",
         "blocked_gain", 4, 24, 1, "rcl"),
        ("grammar.neighbor_edge_weight", "neighbor_edge_weight", op("edge_min_weight_sum", op("induced_edges", neighbors)),
         "weight / (1 + degree) + c0 * neighbor_edge_weight / (1 + conflict_weight)",
         "resource_boundary", 6, 32, 1, "exchange"),
        ("grammar.compatible_max", "compatible_max", op("max_weight", op("difference", op("available"), closed)),
         "weight / (1 + degree) + c0 * compatible_max / (1 + conflict_weight)",
         "rejection_frontier", 8, 48, 2, "greedy"),
        ("grammar.twohop_count", "twohop_count", op("count", twohop),
         "weight / (1 + degree) - c0 * twohop_count / (1 + remaining_count)",
         "blocked_gain", 10, 64, 2, "rcl"),
        ("grammar.twohop_incident", "twohop_incident", op("count", op("incident_edges", twohop)),
         "weight / (1 + degree) - c0 * twohop_incident / (1 + remaining_count)",
         "resource_boundary", 12, 64, 2, "exchange"),
    ]
    recipes = []
    for index, (name, feature_name, expression, rule, anchor, destroy, cap, hops, reconstruction) in enumerate(definitions):
        recipe = {"name": name, "features": [{"name": feature_name, "expression": deepcopy(expression)}],
                  "rule": rule,
                  "patch_policy": {"anchor": anchor, "destroy_count": destroy,
                                   "patch_cap": cap, "expand_hops": hops,
                                   "reconstruction": reconstruction},
                  "evaluation_plan": {"feature_scope": "patch", "max_feature_cpu_fraction": .15, "lazy": True},
                  "adaptation_template": {"mutation_scales": [.15, .15, .15, .15],
                                          "stagnation_trials": 16,
                                          "action": ("mutate", "diversify", "switch_recipe")[index % 3]},
                  "coefficients": [1., .5, .25, -.25],
                  "rationale": "Manually predefined non-LLM grammar heuristic. Bounded patch-only structure; no cover/oracle/full-graph scoring. This is not random-search or historically selected evidence of superiority."}
        validate_recipe(recipe)
        recipes.append(recipe)
    return {"schema_version": "stk_online_llm_v2", "recipes": recipes}


def main(output_root=ROOT):
    output_root = Path(output_root).resolve()
    bank = make_controls()
    schema = json.loads((output_root / "schema.json").read_text(encoding="utf-8"))
    validate_response_schema(bank, schema)
    folder = output_root / "banks"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / "grammar_operators.json"
    destination.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance = {"version": "stk_online_llm_v2_predefined_grammar_controls",
                  "generator": "manually predefined six grammar heuristics",
                  "random_search": False, "actual_LLM_calls": 0,
                  "historical_fit_used_for_selection": False,
                  "historical_schedule_quality_used_for_selection": False,
                  "structural_challenge_used_for_selection": False,
                  "recipes": len(bank["recipes"]), "bank_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                  "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "scope": "All feature computation on exact bounded patches; same schema and executable validator as model recipes",
                  "cost_note": "No full-graph cover/greedy feature; actual bounded feature computation still incurs charged CPU"}
    (folder / "grammar_controls_provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bank": str(destination), "recipes": 6, "actual_LLM_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    main(args.output_root)
