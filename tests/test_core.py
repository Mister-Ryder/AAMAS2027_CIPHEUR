import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from cipheur.model import Contact, Graph, reversal_fixture, aligned_intervention, temporal_graph
from cipheur.oracle import Budget, local_bound, solve, certify_pair
from cipheur.programs import Program, features, schedule, requirement_report
from cipheur.pipeline import load_config, run


def brute(graph, fixed=(), excluded=()):
    ids = sorted(graph.available(fixed, excluded))
    best = graph.value(fixed)
    for n in range(len(ids) + 1):
        for subset in itertools.combinations(ids, n):
            selected = tuple(fixed) + subset
            if graph.feasible(selected):
                best = max(best, graph.value(selected))
    return best


class BoundTests(unittest.TestCase):
    def test_large_scale_rounding_cannot_shrink_upper_bound(self):
        contacts = tuple(Contact(str(i), w, str(i), str(i), 0, 1) for i, w in enumerate((1e16, 1.0, 1.0)))
        graph = Graph("large_scale", contacts, frozenset())
        result = solve(graph)
        self.assertEqual(set(result.selected), {"0", "1", "2"})
        self.assertEqual(result.upper, 10000000000000002)
        self.assertTrue(result.exact)

    def test_frontier_and_local_bounds_against_exhaustive_completion(self):
        rng = random.Random(45)
        for trial in range(18):
            contacts = tuple(Contact(str(i), rng.randint(1, 8), f"s{i}", f"g{i}", 0, 1) for i in range(7))
            edges = frozenset((str(i), str(j)) for i in range(7) for j in range(i + 1, 7) if rng.random() < .35)
            graph = Graph(str(trial), contacts, edges)
            fixed = ("0",)
            excluded = ("6",)
            optimum = brute(graph, fixed, excluded)
            for limit in (0, 1, 3, 10000):
                result = solve(graph, fixed=fixed, excluded=excluded, max_nodes=limit)
                self.assertTrue(graph.feasible(result.selected))
                self.assertAlmostEqual(graph.value(result.selected), result.lower)
                self.assertLessEqual(result.lower, optimum)
                self.assertGreaterEqual(result.upper, optimum)
                if result.exact:
                    self.assertEqual(result.lower, optimum)
            for action in sorted(graph.available(fixed, excluded))[:2]:
                optimum = brute(graph, fixed + (action,), excluded)
                for region in ({action}, {action, "2", "3"}, set(graph.nodes)):
                    result = local_bound(graph, region, action, fixed, excluded, 3)
                    self.assertTrue(graph.feasible(result.selected))
                    self.assertLessEqual(result.lower, optimum)
                    self.assertGreaterEqual(result.upper, optimum)

    def test_four_completion_certificate_and_program_requirements(self):
        left, right = reversal_fixture()
        witness, log = certify_pair(left, right, "a", "b", Budget(), fixed=("d",))
        self.assertIsNotNone(witness)
        self.assertEqual(witness["left_preferred"], "a")
        self.assertEqual(witness["right_preferred"], "b")
        self.assertEqual(witness["certificate_scope"], "full_residual_graph_with_fixed_boundary")
        for key, graph in (("left_a", left), ("left_b", left), ("right_a", right), ("right_b", right)):
            selected = witness["bounds"][key]["selected"]
            self.assertTrue(graph.feasible(selected))
            self.assertIn(key[-1], selected)
            self.assertIn("d", selected)
        self.assertFalse(requirement_report(Program("static", "weight"), [witness])["all_passed"])
        self.assertTrue(requirement_report(Program("cost", "weight - 1.2 * conflict_weight"), [witness])["all_passed"])

    def test_local_certificate_never_ignores_external_opportunity(self):
        left, right = reversal_fixture()
        # A mutually conflicting exterior pair creates uncertainty in the sum bound.
        exterior = (Contact("x", 100, "sx", "gx", 0, 1), Contact("y", 100, "sy", "gy", 0, 1))
        for graph in (left, right):
            graph.contacts += exterior
            graph.edges |= {("x", "y")}
            graph.__post_init__()
        witness, details = certify_pair(left, right, "a", "b", Budget(), max_region=2)
        self.assertIsNone(witness)
        self.assertEqual(details["reason"], "unresolved_bounds")

    def test_oracle_exhaustion_is_not_certificate(self):
        with self.assertRaises(RuntimeError):
            certify_pair(*reversal_fixture(), "a", "b", Budget(max_calls=2))
        left, _ = reversal_fixture()
        bounded = solve(left, max_nodes=0)
        self.assertFalse(bounded.exact)
        self.assertGreaterEqual(bounded.upper, brute(left))

    def test_disagreement_checks_direction_not_merely_switching(self):
        from cipheur.acquisition import acquire
        opposite = Program("opposite", "weight if station_gap > 0 else -weight")
        witnesses, _ = acquire([reversal_fixture()], opposite, Budget())
        self.assertTrue(witnesses[0]["current_program_failed"])

    def test_alignment_rejects_changed_actions_and_multiple_constraints(self):
        left, right = reversal_fixture()
        right.contacts = right.contacts[:-1]
        with self.assertRaises(ValueError):
            aligned_intervention(left, right)
        left, right = reversal_fixture()
        right.constraints["satellite_gap"] = 1
        with self.assertRaises(ValueError):
            aligned_intervention(left, right)


class KernelTests(unittest.TestCase):
    def test_restricted_program_rejects_code_execution(self):
        for expression in ("__import__('os')", "weight.__class__", "[weight][0]", "2 ** 1000000", "sum(x for x in [])", "unknown"):
            with self.assertRaises((ValueError, SyntaxError)):
                Program("bad", expression)
        with self.assertRaises(ValueError):
            Program("bad", "weight / 0").score({"weight": 1})

    def test_all_programs_preserve_fixed_boundary_and_exclusions(self):
        for graph in reversal_fixture():
            for expression in ("weight", "-weight", "weight / (1 + degree)", "weight - conflict_weight", "weight if degree < 2 else -duration"):
                result = schedule(graph, Program("test", expression), fixed=("d",), excluded=("c",))
                self.assertTrue(graph.feasible(result["selected"]))
                self.assertIn("d", result["selected"])
                self.assertNotIn("c", result["selected"])

    def test_duplicate_and_unknown_boundary_rejected(self):
        graph, _ = reversal_fixture()
        self.assertFalse(graph.feasible(("a", "a")))
        self.assertNotIn("a", graph.available(excluded=(v for v in ("a",))))
        with self.assertRaises(ValueError):
            graph.available(excluded=("unknown",))
        with self.assertRaises(ValueError):
            temporal_graph("invalid_gap", graph.contacts, station_gap=float("nan"))


class PipelineTests(unittest.TestCase):
    def test_invalid_model_candidate_is_preserved_and_repaired_next_round(self):
        config = load_config(Path(__file__).resolve().parents[1] / "configs" / "smoke.json")
        bad = {"name": "invalid", "expression": "__import__('os')", "rationale": "invalid fixture"}
        good = {"name": "repair", "expression": "weight - 1.2 * conflict_weight", "rationale": "repair fixture"}
        with tempfile.TemporaryDirectory() as directory, patch("cipheur.pipeline.generate_candidate", side_effect=[
                (bad, {"live_llm": False}), (good, {"live_llm": False})]) as generate:
            target = Path(directory) / "run"
            result = run(config, target)
            self.assertEqual(result["candidate_rejections"], 1)
            self.assertTrue(result["requirements"]["all_passed"])
            self.assertTrue((target / "round_000" / "candidate_response.json").exists())
            request = generate.call_args_list[1].args[1]
            previous = json.loads(request["user"])["previous_attempts"]
            self.assertFalse(previous[0]["accepted"])
            self.assertTrue(previous[0]["error"])

    def test_end_to_end_receipt_and_offline_provenance(self):
        config = load_config(Path(__file__).resolve().parents[1] / "configs" / "smoke.json")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "run"
            result = run(config, target)
            self.assertEqual(result["witness_count"], 3)
            self.assertEqual(result["live_llm_calls"], 0)
            self.assertTrue(result["requirements"]["all_passed"])
            self.assertTrue(result["all_schedules_feasible"])
            self.assertFalse(result["effectiveness_validated"])
            receipt = json.loads((target / "receipt.json").read_text(encoding="utf-8"))
            self.assertIn("selected_program.json", receipt["artifact_sha256"])
            self.assertTrue((target / "source_snapshot" / "cipheur" / "oracle.py").is_file())
            with self.assertRaises(FileExistsError):
                run(config, target)


if __name__ == "__main__":
    unittest.main()
