"""Independent small-graph checks of exact alias census and certificate scope."""
from fractions import Fraction
import itertools
import math
import random
import unittest
from unittest.mock import patch

from cipheur.alias_census import (base_vectors, census_pairs, certify_candidates,
                                 development_pairs, query_plan, summarize_certificates)
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph
from cipheur.programs import FEATURES


def pair_fixture(*, omitted=False, unequal=False, identity="fixture"):
    # Pure synthetic unit fixture, never part of the natural study. a and b
    # block independent/partly compatible triples; only x's internal edges change.
    weights = {"a": 8, "b": 5 if unequal else 8,
               **{v: 6 for v in ("x1", "x2", "x3", "y1", "y2", "y3")}}
    contacts = tuple(Contact(v, w, v, v, 0, 2 if v in ("a", "b") else 1)
                     for v, w in weights.items())
    edges = {("a", "b"), ("y1", "y2")}
    edges.update(("a", v) for v in ("x1", "x2", "x3"))
    edges.update(("b", v) for v in ("y1", "y2", "y3"))
    parameter = "satellite_trans_time" if omitted else "station_gap"
    left = Graph(identity + "left", contacts, frozenset(edges), {"model": "unit", parameter: 0})
    right = Graph(identity + "right", contacts,
                  frozenset(edges | set(itertools.combinations(("x1", "x2", "x3"), 2))),
                  {"model": "unit", parameter: 1})
    return {"id": identity, "family": "unit", "source": {"split": "train"},
            "left": left.to_dict(), "right": right.to_dict(), "fixed": [], "excluded": [],
            "census_split": "train"}


def exact_completion(graph, forced, fixed=()):
    committed = tuple(fixed) + (forced,)
    available = sorted(graph.available(committed))
    return max(sum((Fraction(graph.nodes[v].weight) for v in committed + subset), Fraction(0))
               for size in range(len(available) + 1)
               for subset in itertools.combinations(available, size)
               if graph.feasible(committed + subset))


class ExactCensusTests(unittest.TestCase):
    def test_current_typed_fsum_interface_and_all_nine_fields(self):
        graph = Graph("rounding", tuple(Contact(v, w, v, v, 0, 1)
                      for v, w in (("a", 2), ("b", 1e16), ("c", 1), ("d", 1))),
                      frozenset(("a", v) for v in ("b", "c", "d")),
                      {"ground_trans_time": 3, "satellite_change_time": 7,
                       "satellite_trans_time": 9})
        with patch("cipheur.programs.features", side_effect=AssertionError("legacy sums must not be used")):
            vector = base_vectors(graph, set(graph.nodes))["a"]
        self.assertEqual(set(vector), set(FEATURES))
        self.assertEqual(vector["conflict_weight"], math.fsum((1e16, 1, 1)))
        self.assertNotEqual(vector["conflict_weight"], sum((1e16, 1, 1)))
        self.assertEqual(vector["station_gap"], 3)
        self.assertEqual(vector["satellite_gap"], 7)
        self.assertNotIn("satellite_trans_time", vector)

    def test_development_only_exclusion_and_duplicate_guards(self):
        normal = pair_fixture()
        probe = {**pair_fixture(identity="probe"), "family": "diagnostic"}
        source_probe = {**pair_fixture(identity="source_probe"), "source": {"split": "train", "origin": "designed_temporal_probe"}}
        data = {"train": [probe, normal, source_probe], "validation": []}
        pairs, excluded = development_pairs(data)
        self.assertEqual([p["id"] for p in pairs], ["fixture"])
        self.assertEqual(len(excluded), 2)
        with self.assertRaises(ValueError):
            development_pairs({**data, "test": []})
        with self.assertRaises(ValueError):
            development_pairs({"train": [normal, normal], "validation": []})
        with self.assertRaises(ValueError):
            census_pairs([probe])

    def test_denominators_against_all_pairs_reference_on_random_graphs(self):
        rng = random.Random(20031)
        program = FeatureRuleProgram("independent_reference", [], "weight")
        for trial in range(30):
            names = list("abcdef")
            contacts = tuple(Contact(v, rng.choice((1, 2, 3)), v, v, 0, rng.choice((1, 2))) for v in names)
            potential = list(itertools.combinations(names, 2))
            le = {e for e in potential if rng.random() < .45}
            re = le | {e for e in potential if rng.random() < .2}
            left = Graph("left", contacts, frozenset(le), {"model": "unit", "station_gap": 0})
            right = Graph("right", contacts, frozenset(re), {"model": "unit", "station_gap": 1})
            pair = {"id": str(trial), "family": "unit", "source": {"split": "train"},
                    "census_split": "train", "left": left.to_dict(), "right": right.to_dict()}
            census, candidates = census_pairs([pair], max_steps=0)
            common = [e for e in potential if e in le and e in re]
            vectors = {side: {v: program.evaluate_features(g, v, set(names)) for v in names}
                       for side, g in (("left", left), ("right", right))}
            side_counts = {side: sum(vectors[side][a] == vectors[side][b] for a, b in common)
                           for side in vectors}
            union = sum(any(vectors[side][a] == vectors[side][b] for side in vectors) for a, b in common)
            self.assertEqual(census["totals"].get("common_conflicting_pairs", 0), len(common))
            self.assertEqual(census["totals"].get("within_side_exact_alias_pairs", 0), union)
            for side in vectors:
                self.assertEqual(census["totals"].get("within_side_exact_alias_pairs_" + side, 0), side_counts[side])
            self.assertEqual(len(candidates), union)  # visible station_gap excludes every cross join.
            self.assertEqual(census["totals"]["unique_boundaries"], 1)

    def test_actual_rollout_provenance_invalid_replay_and_common_actions(self):
        contacts = tuple(Contact(v, w, v, v, 0, 1) for v, w in (("a", 20), ("b", 10), ("c", 1), ("d", 1)))
        left = Graph("left", contacts, frozenset({("c", "d")}), {"model": "unit", "station_gap": 0})
        right = Graph("right", contacts, frozenset({("a", "b"), ("c", "d")}), {"model": "unit", "station_gap": 1})
        pair = {"id": "replay", "family": "unit", "source": {"split": "train"}, "census_split": "train",
                "left": left.to_dict(), "right": right.to_dict()}
        census, candidates = census_pairs([pair], max_steps=2)
        self.assertEqual(census["totals"]["invalid_boundary_replays"], 1)
        bad = next(row for row in census["boundaries"] if not row["valid_replay"])
        self.assertEqual(bad["fixed"], ["a", "b"])
        # Independently reconstruct each recorded origin by the actual rule and
        # contact-ID tie break, then check both-side action eligibility.
        for row in census["boundaries"]:
            for origin in row["rollout_origins"]:
                graph = left if origin["side"] == "left" else right
                selected = []
                for _ in range(origin["step"]):
                    active = graph.available(selected)
                    action = min(active, key=lambda v: (-graph.nodes[v].weight / max(1, len(graph.adj[v] & active)), v))
                    selected.append(action)
                self.assertEqual(sorted(selected), row["fixed"])
        for candidate in candidates:
            for graph in (left, right):
                available = graph.available(candidate["fixed"], candidate["excluded"])
                self.assertIn(candidate["a"], available)
                self.assertIn(candidate["b"], available)
                self.assertIn(candidate["b"], graph.adj[candidate["a"]])

    def test_deterministic_priority_and_query_ids_without_oracle(self):
        data = {"train": [pair_fixture(identity="z"), pair_fixture(identity="a")], "validation": []}
        pairs, _ = development_pairs(data)
        census, candidates = census_pairs(pairs, max_steps=0)
        selected, plan = query_plan(candidates, 1)
        with patch("cipheur.alias_census.certify_pair", side_effect=AssertionError("plan must precede queries")):
            again, again_plan = query_plan(list(reversed(candidates)), 1)
        self.assertEqual(plan, again_plan)
        self.assertEqual(selected, again)
        self.assertEqual(selected[0]["query_priority"], 0)
        self.assertFalse(plan["oracle_outcomes_used"])
        self.assertEqual(plan["eligible_count"], census["totals"]["query_eligible_candidates"])


class CertificateScopeTests(unittest.TestCase):
    def candidate(self, pair):
        _, candidates = census_pairs([pair], max_steps=0)
        return next(row for row in candidates if (row["a"], row["b"]) == ("a", "b"))

    def check_bounds(self, pair, row):
        for side in ("left", "right"):
            graph = Graph.from_dict(pair[side])
            for action in ("a", "b"):
                bound = row["details"]["bounds"].get(side + "_" + action)
                if bound is None:
                    continue
                optimum = exact_completion(graph, action)
                self.assertLessEqual(Fraction(bound["lower_exact"]), optimum)
                self.assertGreaterEqual(Fraction(bound["upper_exact"]), optimum)
                self.assertTrue(graph.feasible(bound["selected"]))
                self.assertIn(action, bound["selected"])

    def test_nine_input_alias_certifies_real_self_loops(self):
        pair = pair_fixture()
        candidate = self.candidate(pair)
        self.assertEqual(set(candidate["within_equal_sides"]), {"left", "right"})
        self.assertIn("within_side_typed_structure_distinction", candidate["kinds"])
        row = certify_candidates([pair], [candidate], query_nodes=2000)[0]
        self.check_bounds(pair, row)
        self.assertEqual(row["pair_relation"], "reversal")
        summary = summarize_certificates([pair], [row])
        self.assertEqual(summary["certified_side_requirements"], 2)
        self.assertEqual(summary["base_quotient"]["self_loop_requirements"], 2)
        self.assertTrue(summary["configuration_audited_quotient"]["contradictory"])

    def test_one_side_certified_other_unknown_is_not_preservation(self):
        pair = pair_fixture()
        row = certify_candidates([pair], [self.candidate(pair)], query_nodes=2000, max_calls=2)[0]
        self.check_bounds(pair, row)
        self.assertEqual(row["pair_relation"], "unknown")
        self.assertEqual(row["side_preferences"], {"left": "b", "right": None})
        self.assertIsNone(row["certificate"])
        summary = summarize_certificates([pair], [row])
        self.assertEqual(summary["totals"]["unknown"], 1)
        self.assertEqual(summary["certified_side_requirements"], 1)
        self.assertEqual(summary["totals"]["unknown_side_requirements"], 1)

    def test_cross_cycle_due_to_unexposed_configuration_is_not_structural_necessity(self):
        pair = pair_fixture(omitted=True, unequal=True)
        candidate = self.candidate(pair)
        self.assertFalse(candidate["within_equal_sides"])
        self.assertEqual(candidate["unexposed_changed_parameters"], ["satellite_trans_time"])
        self.assertIn("cross_direct_vector_match", candidate["kinds"])
        row = certify_candidates([pair], [candidate], query_nodes=2000)[0]
        self.check_bounds(pair, row)
        self.assertEqual(row["pair_relation"], "reversal")
        summary = summarize_certificates([pair], [row])
        self.assertTrue(summary["base_quotient"]["contradictory"])
        self.assertEqual(summary["base_quotient"]["self_loop_requirements"], 0)
        self.assertFalse(summary["configuration_audited_quotient"]["contradictory"])
        self.assertTrue(summary["configuration_omission_can_explain_all_observed_cycles"])

    def test_cross_only_identical_residual_problems_remain_counted_but_not_queried(self):
        pair = pair_fixture(omitted=True, unequal=True)
        pair["right"]["edges"] = pair["left"]["edges"]
        candidate = self.candidate(pair)
        self.assertTrue(candidate["residual_problems_identical"])
        self.assertFalse(candidate["query_eligible"])
        selected, plan = query_plan([candidate], 200)
        self.assertEqual(selected, [])
        self.assertEqual(plan["eligible_count"], 0)
        summary = summarize_certificates([pair], [])
        self.assertEqual(summary["certified_side_requirements"], 0)
        self.assertFalse(summary["base_quotient"]["contradictory"])

    def test_multiple_workers_preserve_query_ids_and_sound_relations(self):
        pairs = [pair_fixture(identity="one"), pair_fixture(identity="two")]
        _, candidates = census_pairs(pairs, max_steps=0)
        selected = [row for row in candidates if (row["a"], row["b"]) == ("a", "b")]
        serial = certify_candidates(pairs, selected, workers=1)
        parallel = certify_candidates(pairs, selected, workers=2)
        semantic = lambda rows: [(r["candidate"]["id"], r["pair_relation"], r["side_preferences"],
                                  r["budget"]["expanded_nodes"]) for r in rows]
        self.assertEqual(semantic(serial), semantic(parallel))


if __name__ == "__main__":
    unittest.main()
