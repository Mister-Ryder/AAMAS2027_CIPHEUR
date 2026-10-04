"""Mathematical objective-order tests for the separate lossless encoding."""
from fractions import Fraction
from itertools import combinations
from hashlib import sha256
from pathlib import Path
import unittest

from cipheur.advanced_baselines_gcd_v06 import metis_input
from cipheur.advanced_baselines_v06 import metis_input as preserved_input
from cipheur.model import Contact, Graph


class LosslessNativeEncodingTests(unittest.TestCase):
    def graph(self, weights):
        return Graph("exact", tuple(Contact(str(i), w, "S", str(i), 0, 1)
                     for i, w in enumerate(weights)), frozenset({("0", "1")}))

    def encoded(self, graph, fixed=(), excluded=()):
        text, nodes, scale, contract, divisor = metis_input(
            graph, "M2WIS", fixed, excluded)
        lines = text.splitlines()[1:]
        values = {v: int(line.split()[0]) for v, line in zip(nodes, lines)}
        return nodes, values, Fraction(divisor, scale)

    def test_every_feasible_objective_and_tie_is_preserved(self):
        graph = self.graph([Fraction(2, 3), Fraction(4, 3), 2, 0])
        nodes, values, reverse = self.encoded(graph)
        self.assertEqual(reverse, Fraction(2, 3))
        pairs = []
        for size in range(len(nodes) + 1):
            for selected in combinations(nodes, size):
                if graph.feasible(selected):
                    original = sum((Fraction(graph.nodes[v].weight)
                                    for v in selected), Fraction())
                    integer = sum(values[v] for v in selected)
                    self.assertEqual(original, reverse * integer)
                    pairs.append((original, integer))
        for a in pairs:
            for b in pairs:
                self.assertEqual((a[0] > b[0]) - (a[0] < b[0]),
                                 (a[1] > b[1]) - (a[1] < b[1]))

    def test_common_factor_resolves_range_without_clipping(self):
        graph = self.graph([2_000_000_000, 2_000_000_000])
        with self.assertRaises(ValueError):
            preserved_input(graph, "M2WIS")
        nodes, values, reverse = self.encoded(graph)
        self.assertEqual(values, {"0": 1, "1": 1})
        self.assertEqual(reverse, 2_000_000_000)

    def test_irreducible_overflow_remains_unsupported(self):
        graph = self.graph([2**63 - 1, 2**63 - 2])
        for method in ("CHILS", "M2WIS", "Struction", "WeightedBR"):
            with self.assertRaises(ValueError):
                metis_input(graph, method)

    def test_boundary_reward_is_constant_and_exclusions_are_retained(self):
        graph = self.graph([999, 17, Fraction(2, 3), Fraction(4, 3), 23])
        nodes, values, reverse = self.encoded(graph, fixed=("0",), excluded=("4",))
        self.assertEqual(nodes, ["2", "3"])
        for subset in ((), ("2",), ("3",), ("2", "3")):
            selected = ("0",) + subset
            self.assertTrue(graph.feasible(selected))
            reward = sum((Fraction(graph.nodes[v].weight)
                          for v in selected), Fraction())
            self.assertEqual(reward, 999 + reverse * sum(values[v] for v in subset))

    def test_zero_reward_and_original_wrapper_bytes(self):
        graph = self.graph([0, 0])
        nodes, values, reverse = self.encoded(graph)
        self.assertEqual(reverse, 1)
        self.assertEqual(values, {"0": 0, "1": 0})
        source = Path(__file__).resolve().parents[1] / "cipheur/advanced_baselines_v06.py"
        self.assertEqual(sha256(source.read_bytes()).hexdigest(),
                         "713364f084ef9c3538be275b2437e681e6a9d0457dbc028d621ba0bc71ee4477")


if __name__ == "__main__":
    unittest.main()
