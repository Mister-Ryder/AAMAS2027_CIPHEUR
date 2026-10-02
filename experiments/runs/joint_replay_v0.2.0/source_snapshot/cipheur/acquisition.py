from __future__ import annotations
from itertools import combinations
from .model import aligned_intervention
from .programs import features


def acquire(pairs, program, budget, max_attempts=8, max_witnesses=4,
            strategy="disagreement", fixed=(), excluded=(), max_region=64,
            nodes_per_call=10000, known_keys=()):
    """Rank legal interventions by failure to switch, then certify using the oracle.

    Cheap ranking is a proxy, not an assertion of ground-truth disagreement.
    Every attempted query, including rejected queries, is recorded and charged.
    """
    from .oracle import certify_pair
    candidates = []
    for pair_index, (left, right) in enumerate(pairs):
        aligned_intervention(left, right, fixed, excluded)
        common = left.available(fixed, excluded) & right.available(fixed, excluded)
        for a, b in combinations(sorted(common), 2):
            if (left.name, right.name, a, b) in known_keys:
                continue
            if b not in left.adj[a] or b not in right.adj[a]:
                continue
            if not ((left.adj[a] ^ right.adj[a]) | (left.adj[b] ^ right.adj[b])):
                continue
            gaps = []
            for graph in (left, right):
                available = graph.available(fixed, excluded)
                gaps.append(program.score(features(graph, a, available)) -
                            program.score(features(graph, b, available)))
            missed_switch = gaps[0] * gaps[1] >= 0
            exposure = len((left.adj[a] ^ right.adj[a]) | (left.adj[b] ^ right.adj[b]))
            priority = (int(missed_switch), exposure, -min(abs(g) for g in gaps))
            candidates.append((priority, pair_index, a, b, gaps))
    if strategy == "disagreement":
        candidates.sort(key=lambda c: (c[0], -c[1], c[2], c[3]), reverse=True)
    elif strategy == "uniform":
        # Deterministic permutation, reproducible matched-budget control.
        import random
        random.Random(0).shuffle(candidates)
    else:
        raise ValueError("Unknown acquisition strategy")
    witnesses, attempts = [], []
    for priority, index, a, b, gaps in candidates[:max_attempts]:
        before = budget.to_dict()
        try:
            witness, details = certify_pair(*pairs[index], a, b, budget, fixed, excluded,
                                           max_region=max_region, nodes_per_call=nodes_per_call)
        except RuntimeError as error:
            attempts.append({"pair": index, "a": a, "b": b, "reason": str(error),
                             "before": before, "after": budget.to_dict()})
            break
        attempts.append({"pair": index, "a": a, "b": b, "score_gaps": gaps,
                         "ranking_proxy": list(priority), "details": details,
                         "before": before, "after": budget.to_dict()})
        if witness:
            witness["current_program_failed"] = not all(
                (gap if witness[side + "_preferred"] == a else -gap) > 1e-8
                for side, gap in zip(("left", "right"), gaps)
            )
            witnesses.append(witness)
            if len(witnesses) >= max_witnesses:
                break
    return witnesses, attempts
