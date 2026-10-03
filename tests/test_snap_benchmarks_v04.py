from hashlib import sha256
import itertools
import unittest

from cipheur.model import Graph
from cipheur.snap_benchmarks_v04 import graph_record, parse_snap


class SparseSourceTests(unittest.TestCase):
    def test_exact_simple_projection_multiplicity_and_explicit_loop_semantics(self):
        raw = b"# Nodes: 4 Edges: 7\n1 2\n2 1\n1 2\n2 3\n3 3\n3 4\n4 1\n"
        nodes, edges, receipt = parse_snap(raw, source_directed=True)
        self.assertEqual(nodes, (1, 2, 3, 4))
        self.assertEqual(edges, frozenset(((1, 2), (1, 4), (2, 3), (3, 4))))
        self.assertEqual(receipt["raw_edge_rows"], 7)
        self.assertEqual(receipt["duplicate_ordered_rows"], 1)
        self.assertEqual(receipt["self_loop_vertex_ids"], [3])
        self.assertEqual(receipt["canonical_self_loop_arcs_removed"], 1)
        self.assertEqual(receipt["removed_vertex_count"], 0)
        self.assertFalse(receipt["original_looped_MWIS_preservation_claimed"])
        self.assertTrue(receipt["conversion_edge_sets_verified"])
        # Enumerate semantics independently: original self-links forbid their
        # vertex, whereas the explicitly projected simple problem retains it.
        original_arcs = ((1, 2), (2, 1), (1, 2), (2, 3), (3, 3), (3, 4), (4, 1))
        feasible = {frozenset(s) for k in range(5) for s in itertools.combinations((1, 2, 3, 4), k)
                    if all(not (a in s and b in s) for a, b in original_arcs)}
        converted = {frozenset(s) for k in range(5) for s in itertools.combinations(nodes, k)
                     if all(not (a in s and b in s) for a, b in edges)}
        projected_from_rows = {frozenset(s) for k in range(5) for s in itertools.combinations(nodes, k)
                    if all(not (a in s and b in s) for a, b in original_arcs if a != b)}
        self.assertEqual(projected_from_rows, converted)
        self.assertNotEqual(feasible, converted)
        self.assertIn(frozenset((3,)), converted)

    def test_header_mismatch_never_invents_isolates_and_malformed_rows_rejected(self):
        nodes, edges, receipt = parse_snap(b"# Nodes: 99 Edges: 1\n10 20\n")
        self.assertEqual(nodes, (10, 20))
        self.assertFalse(receipt["header_node_count_matches_observed"])
        self.assertEqual(receipt["invented_isolated_vertices"], 0)
        for raw in (b"1 2 3\n", b"1.0 2\n", b"# Nodes: 2 Edges: 1\n# Nodes: 3 Edges: 1\n1 2\n"):
            with self.assertRaises(ValueError):
                parse_snap(raw)
        with self.assertRaises(ValueError):
            parse_snap(b"1 1\n", self_loop_policy="reject")

    def test_original_integer_ids_hash_weights_and_graph_roundtrip(self):
        nodes, edges, receipt = parse_snap(b"10 100\n100 999\n")
        unit = graph_record("fixture", nodes, edges, receipt, "unit")
        weighted = graph_record("fixture", nodes, edges, receipt, "hash_weighted")
        g1, g2 = Graph.from_dict(unit["graph"]), Graph.from_dict(weighted["graph"])
        self.assertEqual(g1.edges, g2.edges)
        self.assertEqual(set(g2.nodes), {"10", "100", "999"})
        self.assertEqual(g2.digest(), Graph.from_dict(g2.to_dict()).digest())
        for vertex in nodes:
            expected = 1 + int(sha256(f"20261003:fixture:{vertex}".encode()).hexdigest(), 16) % 20
            self.assertEqual(g2.nodes[str(vertex)].weight, expected)
            self.assertEqual(g1.nodes[str(vertex)].weight, 1)
        self.assertFalse(weighted["source"]["physical_scheduling_claim"])
        self.assertEqual(unit["cluster"], weighted["cluster"])


if __name__ == "__main__":
    unittest.main()
