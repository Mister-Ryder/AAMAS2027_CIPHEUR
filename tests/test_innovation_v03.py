"""Exhaustive soundness, actual-state provenance and full-separation regressions."""
import itertools
from dataclasses import asdict, replace
from fractions import Fraction
import unittest

from cipheur.graph_features import FeatureRuleProgram, NEIGHBOR_EDGE_MIN
from cipheur.model import Contact, Graph, reversal_fixture, temporal_graph
from cipheur.oracle import (Budget, solve, local_bound, certify_pair, greedy_clique_cover,
                            clique_cover_upper, exact_value, _intersect_bounds)
from cipheur.refinement import (diagnose_occurrences, minimum_cost_vector_refinement,
                                minimum_cost_refinement)
from cipheur.residual_evidence import (acquire_rollout_evidence, rollout_states,
                                      residual_fingerprint, evidence_relevance)


def exhaustive_value(graph, fixed=(), excluded=()):
    ids = sorted(graph.available(fixed, excluded))
    return max(exact_value(graph, tuple(fixed) + subset)
               for size in range(len(ids) + 1) for subset in itertools.combinations(ids, size)
               if graph.feasible(tuple(fixed) + subset))


def vector_cycle():
    # A -> B -> A in the coarse graph. cheap refines it into a surviving
    # A0 -> B0 -> A1 -> B1 -> A0 cycle, whose coarse walk revisits classes.
    occurrences = {name: {"class": 0 if name[0] == "a" else 1}
                   for name in ("a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4")}
    requirements = [{"preferred": p, "other": n} for p, n in
                    (("a1", "b1"), ("b2", "a2"), ("a3", "b3"), ("b4", "a4"))]
    cheap = {name: int(name in {"a2", "a3", "b3", "b4"}) for name in occurrences}
    repair = {name: i for i, name in enumerate(occurrences)}
    return occurrences, requirements, {"cheap": cheap, "repair": repair}, {"cheap": 1, "repair": 2}


class CliqueEnvelopeTests(unittest.TestCase):
    def test_all_four_vertex_graphs_and_binary_weights_against_exhaustive_mwis(self):
        edges = list(itertools.combinations("abcd", 2))
        for weights in ((0.1, 0.2, 0.3, 0.4), (1e16, 1, 1, 0), (2, 7, 3, 5)):
            contacts = tuple(Contact(v, w, v, v, 0, 1) for v, w in zip("abcd", weights))
            for edge_mask in range(1 << len(edges)):
                graph = Graph(str(edge_mask), contacts,
                              frozenset(e for i, e in enumerate(edges) if edge_mask & (1 << i)))
                optimum = exhaustive_value(graph)
                cover = greedy_clique_cover(graph, graph.nodes)
                self.assertGreaterEqual(clique_cover_upper(graph, graph.nodes, cover), optimum)
                for limit in (0, 1, 3, 100):
                    result = solve(graph, max_nodes=limit)
                    self.assertTrue(graph.feasible(result.selected))
                    self.assertEqual(Fraction(result.lower_exact), exact_value(graph, result.selected))
                    self.assertLessEqual(Fraction(result.lower_exact), optimum)
                    self.assertGreaterEqual(Fraction(result.upper_exact), optimum)
                    self.assertLessEqual(Fraction(result.lower), optimum)
                    self.assertGreaterEqual(Fraction(result.upper), optimum)
                    if result.exact:
                        self.assertEqual(Fraction(result.lower_exact), optimum)
                for action in graph.nodes:
                    conditional = exhaustive_value(graph, (action,))
                    for region in ({action}, {action, "a", "b"}, set(graph.nodes)):
                        result = local_bound(graph, region, action, max_nodes=1)
                        self.assertIn(action, result.selected)
                        self.assertLessEqual(Fraction(result.lower_exact), conditional)
                        self.assertGreaterEqual(Fraction(result.upper_exact), conditional)

    def test_partition_verification_and_strict_improvement_over_weight_sum(self):
        graph = Graph("clique", tuple(Contact(v, w, v, v, 0, 1) for v, w in zip("abc", (3, 7, 4))),
                      frozenset(itertools.combinations("abc", 2)))
        self.assertEqual(clique_cover_upper(graph, graph.nodes), 7)
        self.assertEqual(solve(graph, max_nodes=0).upper_exact, "7")
        self.assertEqual(solve(graph, max_nodes=0, upper_method="weight_sum").upper_exact, "14")
        for invalid in ((('a', 'b'),), (('a', 'b'), ('b', 'c')), (('a', 'a'), ('b', 'c'))):
            with self.assertRaises(ValueError):
                clique_cover_upper(graph, graph.nodes, invalid)
        graph = Graph("path", graph.contacts, frozenset((("a", "b"), ("b", "c"))))
        with self.assertRaises(ValueError):
            clique_cover_upper(graph, graph.nodes, (tuple("abc"),))

    def test_exterior_clique_can_close_full_graph_certificate(self):
        left, right = reversal_fixture()
        exterior = (Contact("x", 100, "sx", "gx", 0, 1), Contact("y", 100, "sy", "gy", 0, 1))
        pair = [Graph(g.name, g.contacts + exterior, g.edges | {("x", "y")}, g.constraints)
                for g in (left, right)]
        witness, _ = certify_pair(*pair, "a", "b", Budget(), max_region=2)
        self.assertIsNotNone(witness)
        summed, detail = certify_pair(*pair, "a", "b", Budget(), max_region=2, upper_method="weight_sum")
        self.assertIsNone(summed)
        self.assertEqual(detail["reason"], "unresolved_bounds")
        for key, bound in witness["bounds"].items():
            graph = pair[0] if key.startswith("left") else pair[1]
            self.assertTrue(graph.feasible(bound["selected"]))
            optimum = exhaustive_value(graph, (key[-1],))
            self.assertLessEqual(Fraction(bound["lower_exact"]), optimum)
            self.assertGreaterEqual(Fraction(bound["upper_exact"]), optimum)

    def test_repeated_intervals_use_max_lower_min_upper_and_keep_feasibility(self):
        graph, _ = reversal_fixture()
        old = asdict(solve(graph, max_nodes=0, upper_method="weight_sum"))
        new = asdict(solve(graph, max_nodes=100))
        new["upper_exact"], new["upper"] = "100", 100.0
        merged = _intersect_bounds(old, new)
        self.assertEqual(Fraction(merged["lower_exact"]), max(Fraction(old["lower_exact"]), Fraction(new["lower_exact"])))
        self.assertEqual(Fraction(merged["upper_exact"]), min(Fraction(old["upper_exact"]), Fraction(new["upper_exact"])))
        self.assertTrue(graph.feasible(merged["selected"]))
        self.assertEqual(Fraction(merged["lower_exact"]), exact_value(graph, merged["selected"]))

    def test_budget_unknown_preserves_partial_four_space_log(self):
        witness, detail = certify_pair(*reversal_fixture(), "a", "b", Budget(max_calls=2),
                                       raise_on_exhaustion=False)
        self.assertIsNone(witness)
        self.assertEqual(detail["reason"], "budget_exhausted")
        self.assertEqual(detail["after"]["calls"], 2)
        self.assertEqual(set(detail["history"][0]["raw_bounds"]), {"left_a", "left_b"})
        self.assertEqual(detail["history"][0]["uncomputed"], ["right_a", "right_b"])


class ResidualAcquisitionTests(unittest.TestCase):
    def test_actual_rollout_anchor_and_identical_boundary_replay(self):
        pair = reversal_fixture()
        pair = tuple(Graph(g.name, tuple(replace(c, weight=20) if c.id == "d" else c for c in g.contacts),
                           g.edges, g.constraints) for g in pair)
        program = FeatureRuleProgram("incumbent", [], "weight")
        specs, attempts = acquire_rollout_evidence([pair], program, Budget(max_calls=1000), max_attempts=100)
        self.assertTrue(specs)
        spec = next(s for s in specs if s["acquisition"]["step"] == 1)
        request = spec["acquisition"]
        self.assertEqual(request["fixed"], ["d"])
        self.assertEqual(request["actual_next_action"], spec["a"])
        self.assertTrue(request["anchor_is_actual_argmax"])
        self.assertEqual(request["rank_positions"][request["anchor_side"]][spec["a"]], 1)
        anchor_graph = pair[0] if request["anchor_side"] == "left" else pair[1]
        trace = rollout_states(anchor_graph, program)
        self.assertEqual(trace[request["step"]]["fixed"], request["fixed"])
        self.assertEqual(trace[request["step"]]["actual_next_action"], spec["a"])
        for side, graph in zip(("left", "right"), pair):
            self.assertTrue(graph.feasible(spec["fixed"]))
            self.assertIn(spec["a"], graph.available(spec["fixed"], spec["excluded"]))
            self.assertIn(spec["b"], graph.adj[spec["a"]])
            self.assertEqual(request["residual_fingerprints"][side],
                             residual_fingerprint(graph, spec["fixed"], spec["excluded"]))
        relevance = evidence_relevance(program, [spec], regret_nodes=1000)
        self.assertEqual(relevance["boundary_reachable"], 2)
        self.assertEqual(relevance["next_action_escape"], 0)
        self.assertEqual(relevance["rows"][0]["conditional_regret"]["upper_exact"], "0")
        self.assertEqual(relevance["rows"][1]["conditional_regret"]["lower_exact"], "3")
        self.assertTrue(all("before" in row and "after" in row for row in attempts))

    def test_unreplayable_rollout_fixed_set_is_logged_and_never_certified(self):
        specs, attempts = acquire_rollout_evidence([reversal_fixture()], FeatureRuleProgram("p", [], "weight"),
                                                  Budget(max_calls=1000), anchor_sides=("left",))
        rejected = [a for a in attempts if a["reason"] == "invalid_boundary_replay"]
        self.assertTrue(rejected)
        self.assertEqual(set(rejected[0]["request"]["fixed"]), {"a", "c"})
        self.assertEqual(rejected[0]["before"], rejected[0]["after"])
        self.assertTrue(all(set(s["fixed"]) != {"a", "c"} for s in specs))

    def test_preservation_with_unchanged_edges_and_uniform_eligible_challengers(self):
        contacts = (Contact("a", 8, "sa", "g", 0, 2), Contact("b", 5, "sb", "g", 0, 1))
        pair = temporal_graph("l", contacts, station_gap=0), temporal_graph("r", contacts, station_gap=1)
        self.assertEqual(pair[0].edges, pair[1].edges)
        specs, attempts = acquire_rollout_evidence([pair], FeatureRuleProgram("p", [], "weight"), Budget(),
                                                   strategy="uniform", seed=7)
        self.assertTrue(specs)
        self.assertTrue(all(s["relation"] == "preservation" for s in specs))
        for spec in specs:
            self.assertIn(spec["b"], spec["acquisition"]["eligible_challengers"])
        self.assertTrue(all(a["request"]["strategy"] == "uniform" for a in attempts))

    def test_escape_and_semantic_reachability_are_separate_from_score_checks(self):
        specs, _ = acquire_rollout_evidence([reversal_fixture()], FeatureRuleProgram("p", [], "weight"), Budget())
        candidate = FeatureRuleProgram("escape", [], "weight - 2 * conflict_weight")
        report = evidence_relevance(candidate, specs[:1])
        self.assertEqual(report["boundary_reachable"], 2)
        self.assertEqual(report["next_action_escape"], 2)
        self.assertEqual(report["pair_choices"], 0)
        self.assertIsNone(report["pair_choice_consistency"])


class FullQuotientRefinementTests(unittest.TestCase):
    def test_concrete_joins_and_surviving_four_cycle_force_another_master(self):
        occurrences, requirements, values, costs = vector_cycle()
        coarse = diagnose_occurrences(occurrences, requirements)
        self.assertEqual(len(coarse["structural_witnesses"][0]["requirements"]), 2)
        refined = diagnose_occurrences(occurrences, requirements, values, ("cheap",))
        self.assertTrue(refined["contradictory"])
        self.assertEqual(len(refined["structural_witnesses"][0]["requirements"]), 4)
        result = minimum_cost_vector_refinement(occurrences, requirements, values, costs)
        self.assertTrue(result["repaired"])
        self.assertTrue(result["optimal"])
        self.assertEqual(result["selected_names"], ["repair"])
        self.assertEqual(result["cost_exact"], "2")
        self.assertEqual(len(result["rounds"]), 2)
        self.assertTrue(all(r["full_quotient_rechecked"] for r in result["rounds"]))
        self.assertTrue(result["rounds"][0]["quotient"]["contradictory"])
        for witness in result["witnesses"]:
            arcs = witness["requirements"]
            for i, join in enumerate(witness["equality_joins"]):
                self.assertEqual(join["negative"], arcs[i]["other"])
                self.assertEqual(join["positive"], arcs[(i + 1) % len(arcs)]["preferred"])
                self.assertEqual(join["negative_vector"], join["positive_vector"])

    def test_exact_master_matches_exhaustive_original_repair_objective(self):
        occurrences, requirements, values, _ = vector_cycle()
        values["duplicate"] = dict(values["repair"])
        for costs in ({"cheap": 0.1, "repair": 0.2, "duplicate": 1},
                      {"cheap": 4, "repair": 8, "duplicate": 3}):
            candidates = []
            names = sorted(values)
            for n in range(len(names) + 1):
                for subset in itertools.combinations(names, n):
                    if not diagnose_occurrences(occurrences, requirements, values, subset)["contradictory"]:
                        candidates.append((sum((Fraction(costs[name]) for name in subset), Fraction(0)), len(subset), subset))
            optimum = min(candidates)
            result = minimum_cost_vector_refinement(occurrences, requirements, values, costs)
            self.assertEqual(Fraction(result["cost_exact"]), optimum[0])
            self.assertEqual(tuple(result["selected_names"]), optimum[2])

    def test_budget_or_unseparable_witness_never_claims_minimum_repair(self):
        occurrences, requirements, values, costs = vector_cycle()
        stopped = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_rounds=1)
        self.assertFalse(stopped["repaired"])
        self.assertFalse(stopped["optimal"])
        self.assertTrue(stopped["diagnosis"]["contradictory"])
        truncated = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_master_subsets=2)
        self.assertFalse(truncated["optimal"])
        impossible = minimum_cost_vector_refinement({"x": {"base": 0}}, [{"preferred": "x", "other": "x"}],
                                                     {"same": {"x": 1}}, {"same": 1})
        self.assertEqual(impossible["reason"], "catalogue_cannot_separate_witness")
        self.assertFalse(impossible["optimal"])

    def test_typed_catalogue_evaluation_records_concrete_graph_endpoints(self):
        from tests.test_representation import alias_pair
        spec, _ = certify_pair(*alias_pair(), "a", "b", Budget(), include_preservation=True)
        result = minimum_cost_refinement(FeatureRuleProgram("base", [], "weight"), [spec],
                                        [{"name": "redundancy", "expression": NEIGHBOR_EDGE_MIN}])
        self.assertTrue(result["repaired"])
        self.assertTrue(result["optimal"])
        self.assertEqual(result["selected_names"], ["redundancy"])
        self.assertGreater(result["measured_standalone_work"]["redundancy"], 0)
        join = result["witnesses"][0]["equality_joins"][0]
        self.assertEqual(join["negative_endpoint"]["occurrence"], join["negative"])
        self.assertIn(join["negative_endpoint"]["contact"], ("a", "b"))
        self.assertIn("graph_fingerprint", join["positive_endpoint"])
        self.assertFalse(result["rule_expressibility_proved"])


if __name__ == "__main__":
    unittest.main()
