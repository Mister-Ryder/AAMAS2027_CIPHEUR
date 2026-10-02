import unittest
from cipheur.graph_features import FeatureRuleProgram, NEIGHBOR_EDGE_MIN
from cipheur.model import Contact, temporal_graph
from cipheur.oracle import Budget, certify_pair
from cipheur.representation import diagnose_representation, ranking_report, vector_key


def alias_pair():
    contacts = [Contact("a", 8, "SA", "G0", 0, 10), Contact("b", 8, "SB", "G0", 0, 10)]
    for i, start in enumerate((2, 4, 6)):
        contacts.append(Contact(f"x{i}", 6, "SA", "GX", start, start + 1))
    for i, start in enumerate((2, 2.5, 6)):
        contacts.append(Contact(f"y{i}", 6, "SB", f"GY{i}", start, start + 1))
    return (temporal_graph("left", contacts, station_gap=0),
            temporal_graph("right", contacts, station_gap=4))


class RepresentationTests(unittest.TestCase):
    def test_exact_alias_proves_impossibility_and_expansion_resolves_it(self):
        left, right = alias_pair()
        spec, _ = certify_pair(left, right, "a", "b", Budget(), include_preservation=True)
        self.assertEqual(spec["relation"], "reversal")
        base = FeatureRuleProgram("base", [], "weight")
        diagnosis = diagnose_representation(base, [spec])
        self.assertTrue(diagnosis["contradictory"])
        self.assertTrue(diagnose_representation(base, [spec], max_witnesses=0)["contradictory"])
        self.assertEqual(diagnosis["self_loop_requirements"], 2)
        extended = FeatureRuleProgram("extended", [{"name": "redundancy", "expression": NEIGHBOR_EDGE_MIN}],
                                      "weight - conflict_weight + redundancy")
        self.assertFalse(diagnose_representation(extended, [spec])["contradictory"])
        self.assertTrue(ranking_report(extended, [spec])["all_passed"])

    def test_preservation_is_certified_even_when_edges_do_not_change(self):
        left, right = alias_pair()
        right = temporal_graph("right", left.contacts, station_gap=0.1)
        # Even a parameter intervention with unchanged edges certifies strict
        # preservation, because both conditional objective inequalities are sound.
        spec, _ = certify_pair(left, right, "a", "b", Budget(), include_preservation=True)
        self.assertEqual(spec["relation"], "preservation")
        self.assertEqual(spec["left_preferred"], spec["right_preferred"])

    def test_ties_are_unknown(self):
        contacts = (Contact("a", 8, "SA", "G", 0, 10), Contact("b", 8, "SB", "G", 0, 10))
        left = temporal_graph("left", contacts, station_gap=0)
        right = temporal_graph("right", contacts, station_gap=1)
        spec, detail = certify_pair(left, right, "a", "b", Budget(), include_preservation=True)
        self.assertIsNone(spec)
        self.assertEqual(detail["reason"], "unresolved_bounds")

    def test_vector_equality_does_not_use_rounding(self):
        self.assertNotEqual(vector_key({"x": 1.0}), vector_key({"x": 1.0 + 1e-15}))
        self.assertEqual(vector_key({"x": -0.0}), vector_key({"x": 0.0}))
        self.assertNotEqual(vector_key({"x": 2**53}), vector_key({"x": 2**53+1}))


if __name__ == "__main__":
    unittest.main()
