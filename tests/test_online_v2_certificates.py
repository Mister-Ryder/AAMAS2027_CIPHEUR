"""Exhaustive small-patch optima validate certificates, not solver performance."""
from fractions import Fraction
import itertools
import math
import random
import time
import unittest
from unittest.mock import patch

from cipheur.online_v2.certificates import EvidenceArchive, local_certificates


def exact_conditional(adjacency, weights, active, root):
    nodes = sorted(active)
    best = None
    for mask in range(1 << len(nodes)):
        selected = {v for i, v in enumerate(nodes) if mask & (1 << i)}
        if root not in selected:
            continue
        if any(adjacency[v] & (selected - {v}) for v in selected):
            continue
        value = sum(weights[v] for v in selected)
        best = value if best is None else max(best, value)
    return best


def pair(lower, upper):
    return {"a": 0, "b": 1, "delta_lower_ticks": lower,
            "delta_upper_ticks": upper}


class LocalCertificateTests(unittest.TestCase):
    def check_graph(self, adjacency, weights, active, deadline=None):
        result = local_certificates(adjacency, weights, active, sorted(active),
                                    deadline=deadline)
        true = {}
        for row in result["roots"]:
            root, selected = row["root"], set(row["lower_solution"])
            optimum = exact_conditional(adjacency, weights, active, root)
            true[root] = optimum
            self.assertLessEqual(row["lower_ticks"], optimum)
            self.assertLessEqual(optimum, row["upper_ticks"])
            self.assertIn(root, selected)
            self.assertTrue(selected <= active)
            self.assertFalse(any(adjacency[v] & (selected - {v}) for v in selected))
            self.assertEqual(row["lower_ticks"], sum(weights[v] for v in selected))
            residual = active - adjacency[root] - {root}
            cover = row["upper_cliques"]
            flattened = [v for clique in cover for v in clique]
            self.assertEqual(set(flattened), residual)
            self.assertEqual(len(flattened), len(residual))
            for clique in cover:
                self.assertTrue(all(b in adjacency[a] for a, b in
                                    itertools.combinations(clique, 2)))
            self.assertEqual(row["upper_ticks"], weights[root] + sum(
                max(weights[v] for v in clique) for clique in cover))
        for row in result["pairs"]:
            delta = true[row["a"]] - true[row["b"]]
            self.assertLessEqual(row["delta_lower_ticks"], delta)
            self.assertLessEqual(delta, row["delta_upper_ticks"])
            if row["preference"] == "a":
                self.assertGreater(delta, 0)
            if row["preference"] == "b":
                self.assertLess(delta, 0)
        self.assertEqual(result["full_oracle_calls"], 0)

    def test_all_graphs_up_to_four_vertices_and_exhaustive_conditional_optima(self):
        for n in range(1, 5):
            edges = list(itertools.combinations(range(n), 2))
            for mask in range(1 << len(edges)):
                adjacency = {v: set() for v in range(n)}
                for i, (a, b) in enumerate(edges):
                    if mask & (1 << i):
                        adjacency[a].add(b)
                        adjacency[b].add(a)
                for weights in ({v: 1 for v in range(n)},
                                {v: (v * 7 + mask) % 19 for v in range(n)}):
                    self.check_graph(adjacency, weights, set(range(n)))

    def test_exhaustive_optima_on_seeded_graphs_up_to_ten_vertices(self):
        rng = random.Random(9327)
        for n in range(5, 11):
            for density in (0.05, 0.25, 0.5, 0.8, 1.0):
                adjacency = {v: set() for v in range(n)}
                for a, b in itertools.combinations(range(n), 2):
                    if rng.random() < density:
                        adjacency[a].add(b)
                        adjacency[b].add(a)
                weights = {v: rng.randrange(1000000000000) for v in range(n)}
                self.check_graph(adjacency, weights, set(range(n)))

    def test_expired_cpu_budget_keeps_sound_singleton_cover_and_feasible_lower(self):
        adjacency = {0: {1}, 1: {0, 2}, 2: {1, 3}, 3: {2}}
        self.check_graph(adjacency, {0: 9, 1: 4, 2: 15, 3: 7}, set(adjacency),
                         deadline=time.process_time() - 1)

    def test_invalid_patch_or_noninteger_objective_rejected(self):
        with self.assertRaises(ValueError):
            local_certificates({v: set() for v in range(65)},
                               {v: 1 for v in range(65)}, set(range(65)), [0])
        with self.assertRaises(ValueError):
            local_certificates({0: {1}, 1: set()}, {0: 1, 1: 2}, {0, 1}, [0])
        with self.assertRaises(TypeError):
            local_certificates({0: set()}, {0: 1.0}, {0}, [0])

    def test_interruptions_inside_greedy_and_clique_construction_remain_sound(self):
        adjacency = {0: {1, 3}, 1: {0, 2, 4}, 2: {1, 3, 5},
                     3: {0, 2, 4}, 4: {1, 3, 5}, 5: {2, 4}}
        weights = {v: 3 + v * 11 for v in adjacency}
        for stop_after in range(1, 41):
            calls = [0]
            def expired(_deadline):
                calls[0] += 1
                return calls[0] >= stop_after
            with patch("cipheur.online_v2.certificates._expired", expired):
                self.check_graph(adjacency, weights, set(adjacency), deadline=1.0)


class EvidenceArchiveTests(unittest.TestCase):
    def test_exact_cycle_has_bounds_and_scope_not_dynamic_policy_claim(self):
        archive = EvidenceArchive()
        features = {0: (Fraction(1, 10), 3.0), 1: (Fraction(2, 10), 4.0)}
        self.assertFalse(archive.add("E", features, [pair(2, 8)])["has_cycle"])
        result = archive.add("J", features, [pair(-8, -2)])
        self.assertTrue(result["has_cycle"])
        self.assertEqual(result["cyclic_scc_count"], 1)
        self.assertTrue(result["only_archive_consistency"])
        self.assertFalse(result["arbitrary_dynamic_policy_impossibility_claim"])
        witness = result["structural_witness"]
        self.assertEqual(len(witness["cycle_path"]), 3)
        self.assertEqual({x["context_id"] for e in witness["edges"]
                          for x in e["occurrences"]}, {"E", "J"})

    def test_nextafter_or_decimal_lookalike_does_not_create_exact_cycle(self):
        archive = EvidenceArchive()
        archive.add("one", {0: (0.1,), 1: (2.0,)}, [pair(1, 2)])
        result = archive.add("two", {0: (math.nextafter(0.1, math.inf),),
                                     1: (2.0,)}, [pair(-2, -1)])
        self.assertFalse(result["has_cycle"])
        other = EvidenceArchive()
        other.add("one", {0: (Fraction(1, 10),), 1: (2,)}, [pair(1, 2)])
        self.assertFalse(other.add("two", {0: (0.1,), 1: (2,)},
                                  [pair(-2, -1)])["has_cycle"])

    def test_unknown_tie_eviction_and_self_loop(self):
        archive = EvidenceArchive(max_contexts=1)
        features = {0: (1,), 1: (2,)}
        archive.add("one", features, [pair(1, 2)])
        result = archive.add("two", features, [pair(-2, -1), pair(-1, 1), pair(0, 0)])
        self.assertFalse(result["has_cycle"])
        self.assertEqual(result["evicted_contexts"], ["one"])
        self.assertEqual(result["unknown_row_count"], 1)
        self.assertEqual(result["tie_row_count"], 1)
        self.assertTrue(EvidenceArchive().add("self", {0: (1,), 1: (1,)},
                                            [pair(1, 2)])["has_cycle"])

    def test_new_representation_requires_rebuilding_all_contexts(self):
        archive = EvidenceArchive()
        archive.add("one", {0: (1,), 1: (2,)}, [pair(1, 2)])
        with self.assertRaises(ValueError):
            archive.add("two", {0: (1, 5), 1: (2, 6)}, [pair(-2, -1)])
        self.assertEqual(archive.summary()["retained_context_ids"], ["one"])


if __name__ == "__main__":
    unittest.main()
