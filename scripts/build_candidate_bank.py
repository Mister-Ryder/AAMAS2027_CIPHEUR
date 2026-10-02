"""Materialize current-assistant proposals and a deterministic DSL control.

The proposal rationale was written after reading the saved training request.
This is not an automated model sampling experiment. No test outcomes enter it.
"""
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cipheur.experiments import digest, save
from cipheur.graph_features import NEIGHBOR_EDGE_MIN, NEIGHBOR_EDGE_COUNT


def build(request):
    candidates, origins = [], {}
    def add(name, rule, features=(), origin="enumerated", rationale="Deterministic declared-grid control"):
        candidates.append({"name": name, "features": list(features), "rule": rule, "rationale": rationale})
        origins[name] = origin
    add("weight", "weight")
    add("weight_degree", "weight / (1 + degree)")
    add("weighted_conflict", "weight / (1 + conflict_weight)")
    for coefficient in (0.05, 0.15, 0.3, 0.6, 1.0):
        add(f"base_linear_{coefficient}", f"weight - {coefficient} * conflict_weight")
        add(f"base_degree_{coefficient}", f"weight / (1 + {coefficient} * degree)")
        add(f"base_weighted_{coefficient}", f"weight / (1 + {coefficient} * conflict_weight)")
    minimum = [{"name": "neighbor_redundancy", "expression": NEIGHBOR_EDGE_MIN}]
    edges = [{"name": "neighbor_edges", "expression": NEIGHBOR_EDGE_COUNT}]
    for coefficient in (0.15, 0.3, 0.6, 1.0):
        for discount in (0.25, 0.5, 1.0):
            add(f"enum_discount_{coefficient}_{discount}",
                f"weight - {coefficient} * conflict_weight + {discount} * neighbor_redundancy / max(1, degree)", minimum)
    for degree_penalty in (0.25, 0.5, 1, 2):
        add(f"enum_edgecount_{degree_penalty}",
            f"weight / (1 + {degree_penalty} * degree) + 0.1 * neighbor_edges", edges)
    rationale = ("Training witnesses have identical base9 vectors but different induced edges among blocked neighbors. "
                 "Redundant conflicts suggest aggregate conflict_weight overstates mutually incompatible alternatives. "
                 "Compose neighbor-edge aggregates and normalize by degree to limit dense-clique double counting. "
                 "Sound certificates specify ordering; validation measures complete schedules and actual feature work.")
    proposed = [
        ("assistant_marginal", "weight - conflict_weight + neighbor_redundancy", minimum),
        ("assistant_clipped", "weight / (1 + max(0, conflict_weight - neighbor_redundancy))", minimum),
        ("assistant_normalized", "weight / (1 + max(0, conflict_weight - 2 * neighbor_redundancy / max(1, degree)))", minimum),
        ("assistant_density", "weight / (1 + degree) + 0.2 * neighbor_redundancy / (1 + degree * degree)", minimum),
        ("assistant_degree_repair", "weight / (1 + max(0, degree - 2 * neighbor_edges / max(1, degree)))", edges),
        ("assistant_weighted_repair", "weight / (1 + conflict_weight / max(1, weight) - min(degree / 2, neighbor_redundancy / (1 + conflict_weight)))", minimum),
    ]
    for coefficient in (0.05, 0.1, 0.2, 0.4):
        proposed.append((f"assistant_soft_{coefficient}",
            f"weight / (1 + {coefficient} * conflict_weight) + {coefficient} * neighbor_redundancy / (1 + degree)", minimum))
        proposed.append((f"assistant_marginal_{coefficient}",
            f"weight - {coefficient} * conflict_weight + {coefficient} * neighbor_redundancy / max(1, degree - 1)", minimum))
    for name, rule, features in proposed:
        add(name, rule, features, "current_assistant", rationale)
    return {"training_request_sha256": digest(request), "candidate_origins": origins,
            "provenance": {"proposal_mode": "current_assistant_authored",
                           "automated_llm_calls": 0, "test_outcomes_used": False,
                           "enumeration": "declared coefficient grid over same graph-operation library",
                           "limitation": "One assistant-authored bank; no independent LLM sampling repetitions. Shared-bank free joint is a strong control on the contradiction gate, not a separate free-form LLM search."},
            "candidates": candidates}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if Path(args.output).exists():
        raise ValueError("Candidate artifact already exists")
    bank = build(args.request)
    save(args.output, bank)
    print(f"Wrote {len(bank['candidates'])} candidates without test feedback")
