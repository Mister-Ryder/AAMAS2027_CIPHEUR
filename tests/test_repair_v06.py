"""Independent exhaustive checks of the shared anytime repair kernel.

Enumeration uses the original edge list, not the repair solver/bound routines.
No scheduling TEST or public outcome is used to choose implementation settings.
"""
from dataclasses import replace
from fractions import Fraction
import itertools
import json
import random
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph
from cipheur.repair_v06 import RepairConfig, repair_patch, repair_schedule
from cipheur.strong_baselines import swap_search
from scripts import run_repair_feedback_v06 as feedback


def graph_of(weights, edges=()):
    return Graph("test", tuple(Contact(str(v), w, "s" + str(v), "g" + str(v), 0, 1)
                               for v, w in enumerate(weights)),
                 frozenset((str(a), str(b)) for a, b in edges))


def independent(graph, chosen):
    chosen = set(chosen)
    return chosen <= set(graph.nodes) and all(not {a, b} <= chosen for a, b in graph.edges)


def value(graph, chosen):
    return sum((Fraction(graph.nodes[v].weight) for v in chosen), Fraction())


def enumerate_optimum(graph, region):
    ids = sorted(region)
    return max(value(graph, (ids[i] for i in range(len(ids)) if mask & (1 << i)))
               for mask in range(1 << len(ids))
               if independent(graph, (ids[i] for i in range(len(ids)) if mask & (1 << i))))


def free_region(graph, incumbent, destroy, excluded=()):
    outside = set(incumbent) - set(destroy)
    blocked = outside | set(excluded)
    for a, b in graph.edges:
        if a in outside:
            blocked.add(b)
        if b in outside:
            blocked.add(a)
    return set(graph.nodes) - blocked


def scan_initializer(graph, initial=(), fixed=(), excluded=()):
    chosen = set(initial) | set(fixed)
    active = free_region(graph, chosen, (), excluded)
    trace = []
    while active:
        degrees = {v: sum(v in edge and bool((set(edge) - {v}) & active) for edge in graph.edges)
                   for v in active}
        ratios = {v: Fraction(graph.nodes[v].weight) / max(1, degrees[v]) for v in active}
        v = min(active, key=lambda x: (-ratios[x], x))
        trace.append(v)
        chosen.add(v)
        active = free_region(graph, chosen, (), excluded)
    return chosen, trace


def weight_program():
    return FeatureRuleProgram("weight", [], "weight")


def cover_program():
    return FeatureRuleProgram("cover", [{"name": "nc", "expression": {
        "op": "clique_cover_weight", "args": [{"op": "neighbors", "args": [
            {"op": "root", "args": []}]}]}}], "weight / max(0.000001, weight, nc)")


class PatchSoundnessTests(unittest.TestCase):
    def assert_sound(self, graph, initial, destroy, result, fixed=(), excluded=()):
        self.assertTrue(independent(graph, result["selected"]))
        self.assertTrue(set(fixed) <= set(result["selected"]))
        self.assertFalse(set(excluded) & set(result["selected"]))
        self.assertEqual(Fraction(result["value_exact"]), value(graph, result["selected"]))
        self.assertGreaterEqual(value(graph, result["selected"]), value(graph, initial))
        region = set(result["patch"])
        self.assertTrue(set(destroy) <= region <= free_region(graph, initial, destroy, excluded))
        optimum = enumerate_optimum(graph, region)
        self.assertLessEqual(Fraction(result["lower_exact"]), optimum)
        if result["upper_exact"] is not None:
            self.assertGreaterEqual(Fraction(result["upper_exact"]), optimum)
            cover = result["root_clique_cover"]
            self.assertEqual(sorted(v for clique in cover for v in clique), sorted(region))
            for clique in cover:
                self.assertEqual(len(clique), len(set(clique)))
                self.assertTrue(all(tuple(sorted((a, b))) in graph.edges
                                    for a, b in itertools.combinations(clique, 2)))
            root_upper = sum((max(Fraction(graph.nodes[v].weight) for v in clique)
                              for clique in cover), Fraction())
            self.assertEqual(Fraction(result["root_upper_exact"]), root_upper)
            self.assertGreaterEqual(root_upper, optimum)
        if result["restricted_exact"]:
            self.assertEqual(Fraction(result["lower_exact"]), optimum)
            self.assertEqual(Fraction(result["upper_exact"]), optimum)
        json.dumps(result, allow_nan=False)

    def test_all_four_vertex_graphs_exact_and_truncated_against_enumeration(self):
        possible = list(itertools.combinations(range(4), 2))
        for weights in ((0.1, 0.2, 0.3, 0.4), (1e16, 1, 1, 0), (2, 7, 3, 5)):
            for mask in range(1 << len(possible)):
                graph = graph_of(weights, (e for i, e in enumerate(possible) if mask & (1 << i)))
                initial = {"0"}
                for limit in (0, 1, 3, 1000):
                    for pruning in (False, True):
                        result = repair_patch(graph, initial, initial, node_budget=limit,
                                              upper_pruning=pruning)
                        self.assert_sound(graph, initial, initial, result)
                        if limit == 1000:
                            self.assertTrue(result["restricted_exact"])

    def test_random_boundaries_and_restricted_regions(self):
        rng = random.Random(60203)
        for case in range(40):
            n = rng.randrange(3, 9)
            graph = graph_of([rng.choice((0, 0.1, 0.3, 2, 9)) for _ in range(n)],
                             [e for e in itertools.combinations(range(n), 2) if rng.random() < 0.4])
            initial = set()
            for v in rng.sample(sorted(graph.nodes), n):
                if independent(graph, initial | {v}):
                    initial.add(v)
            fixed = set(rng.sample(sorted(initial), rng.randrange(len(initial) + 1)))
            destroy = set(rng.sample(sorted(initial - fixed), rng.randrange(len(initial - fixed) + 1)))
            excluded = {v for v in set(graph.nodes) - initial if rng.random() < 0.3}
            region = free_region(graph, initial, destroy, excluded)
            region = destroy | {v for v in region - destroy if rng.random() < 0.7}
            for pruning in (False, True):
                for limit in (0, 2, 10000):
                    result = repair_patch(graph, initial, destroy, fixed=fixed, excluded=excluded,
                                          region=region, node_budget=limit, upper_pruning=pruning)
                    self.assert_sound(graph, initial, destroy, result, fixed, excluded)
                    if limit == 10000:
                        self.assertTrue(result["restricted_exact"])

    def test_two_to_three_move_not_available_to_existing_one_to_two_baseline(self):
        graph = graph_of((6, 6, 5, 5, 5), itertools.product((0, 1), (2, 3, 4)))
        old = swap_search(graph, ("0", "1"), seconds=1)
        self.assertEqual(old["value"], 12)
        result = repair_patch(graph, ("0", "1"), ("0", "1"))
        self.assertEqual(result["selected"], ["2", "3", "4"])
        self.assertEqual(result["gain_exact"], "3")
        self.assertTrue(result["restricted_exact"])
        self.assert_sound(graph, ("0", "1"), ("0", "1"), result)

    def test_restriction_and_fixed_scope_cannot_claim_global_optimum(self):
        graph = graph_of((5, 6, 100, 20), ((0, 1), (0, 2)))
        result = repair_patch(graph, ("0", "3"), ("0",), fixed=("3",),
                              region=("0", "1"))
        self.assertEqual(result["value_exact"], "26")
        self.assertTrue(result["restricted"])
        self.assertTrue(result["restricted_exact"])
        self.assertLess(Fraction(result["value_exact"]), enumerate_optimum(graph, graph.nodes))
        self.assert_sound(graph, ("0", "3"), ("0",), result, ("3",))
        with self.assertRaises(ValueError):
            repair_patch(graph, ("0", "3"), ("3",), fixed=("3",))
        with self.assertRaises(ValueError):
            repair_patch(graph, ("0", "3"), ("0",), region=("1",))
        with self.assertRaises(ValueError):
            repair_patch(graph, ("0", "3"), ("0",), max_patch_vertices=0)
        capped = repair_patch(graph, ("0", "3"), ("0",), max_patch_vertices=1)
        self.assertEqual(capped["patch"], ["0"])
        self.assertEqual(capped["gain_exact"], "0")

    def test_root_pruning_reduces_search_without_changing_exact_optimum(self):
        graph = graph_of((9, 7, 4, 3, 2), itertools.combinations(range(5), 2))
        on = repair_patch(graph, ("0",), ("0",), upper_pruning=True)
        off = repair_patch(graph, ("0",), ("0",), upper_pruning=False)
        self.assertTrue(on["root_pruned"])
        self.assertFalse(off["root_pruned"])
        self.assertEqual(off["bound_cuts"], 0)
        self.assertGreater(off["search_nodes"], on["search_nodes"])
        self.assertEqual(on["value_exact"], off["value_exact"])
        self.assertTrue(off["restricted_exact"])

    def test_every_work_stop_is_sound_and_does_not_false_prove_popped_node(self):
        graph = graph_of((6, 6, 5, 5, 5), itertools.product((0, 1), (2, 3, 4)))
        final = repair_patch(graph, ("0", "1"), ("0", "1"), upper_pruning=False)
        stops_with_upper = 0
        for work in range(final["meter"]["repair_work"] + 1):
            result = repair_patch(graph, ("0", "1"), ("0", "1"),
                                  upper_pruning=False, max_work=work)
            self.assert_sound(graph, ("0", "1"), ("0", "1"), result)
            if result["budget_exhausted"] and result["upper_exact"] is not None:
                stops_with_upper += 1
        self.assertGreater(stops_with_upper, 10)
        for clock in ("cpu", "wall"):
            zero = repair_patch(graph, ("0", "1"), ("0", "1"), seconds=0, clock=clock)
            self.assertEqual(zero["selected"], ["0", "1"])
            self.assertEqual(zero["termination"], "time_budget")
            self.assertFalse(zero["restricted_exact"])

    def test_interrupted_root_cannot_prove_suboptimal_greedy_witness_exact(self):
        graph = graph_of((7, 8, 1, 1, 3, 8, 4),
                         ((0, 1), (0, 6), (1, 5), (2, 4), (3, 4), (3, 5), (4, 5)))
        ranks = {v: graph.nodes[v].weight for v in graph.nodes}
        root = repair_patch(graph, ("0",), ("0",), priorities=ranks, node_budget=0,
                            upper_pruning=False)
        self.assertEqual(root["lower_exact"], "15")
        self.assertEqual(enumerate_optimum(graph, graph.nodes), 16)
        self.assertFalse(root["restricted_exact"])
        final = repair_patch(graph, ("0",), ("0",), priorities=ranks)
        self.assertEqual(final["lower_exact"], "16")
        self.assertEqual(final["root_upper_exact"], "21")
        self.assertEqual(final["upper_exact"], "16")
        self.assertEqual(final["upper_method"], "exhaustive_restricted_search")
        saw_interrupted_suboptimal = False
        for work in range(final["meter"]["repair_work"] + 1):
            result = repair_patch(graph, ("0",), ("0",), priorities=ranks, max_work=work)
            self.assert_sound(graph, ("0",), ("0",), result)
            if result["termination"] == "work_budget" and result["lower_exact"] == "15":
                saw_interrupted_suboptimal = True
                self.assertFalse(result["restricted_exact"])
        self.assertTrue(saw_interrupted_suboptimal)


class SharedScheduleTests(unittest.TestCase):
    def test_common_heap_initializer_equals_independent_exact_full_scan(self):
        rng = random.Random(307)
        for _ in range(40):
            n = rng.randrange(1, 16)
            graph = graph_of([rng.choice((0, 0.1, 1, 7, 11)) for _ in range(n)],
                             [e for e in itertools.combinations(range(n), 2) if rng.random() < 0.3])
            expected, trace = scan_initializer(graph)
            for priority in ("degree", "program", "random"):
                result = repair_schedule(graph, weight_program(), priority=priority, seconds=None,
                                         config=RepairConfig(max_patches=0))
                self.assertEqual(result["selected"], sorted(expected))
                self.assertEqual([r["selected"] for r in result["initializer_trace"]], trace)
                self.assertTrue(result["initialization_complete"])
                self.assertEqual(result["initial_value_exact"], result["value_exact"])
                self.assertEqual(result["conditional_oracle_calls"], 0)

    def test_common_branch_scope_has_identical_first_patch_and_local_feature_charges(self):
        graph = graph_of((6, 6, 5, 5, 5), itertools.product((0, 1), (2, 3, 4)))
        config = RepairConfig(max_destroy=2, max_patch_vertices=5, max_patches=1,
                              expansion_steps=0, upper_pruning=False)
        results = [repair_schedule(graph, cover_program(), initial=("0", "1"), priority=p,
                                   seconds=None, config=config) for p in ("program", "degree", "random")]
        for result in results:
            self.assertTrue(result["feasible"])
            self.assertTrue(result["completed"])
            self.assertEqual(result["value_exact"], "15")
            self.assertEqual(result["patch_trace"][0]["target"], "2")
            self.assertEqual(result["patch_trace"][0]["patch"], list("01234"))
            self.assertEqual(result["config"]["policy_scope"], "branch")
            self.assertEqual(result["online_model_calls"], 0)
            json.dumps(result, allow_nan=False)
        self.assertGreater(results[0]["meter"]["feature_work"], 0)
        self.assertEqual(results[1]["meter"]["feature_work"], 0)
        # The cover programme happens to agree with Degree on this fixture;
        # another valid rule must still be able to change local pivot order.
        weight = repair_schedule(graph, weight_program(), initial=("0", "1"), seconds=None,
                                 config=config)
        self.assertNotEqual(weight["patch_trace"][0]["priority_order"],
                            results[1]["patch_trace"][0]["priority_order"])
        self.assertGreater(weight["patch_trace"][0]["degree_pivot_disagreements"], 0)
        calls = []
        from cipheur import repair_v06
        original = repair_v06._priorities
        def record(*args, **kwargs):
            calls.append((set(args[1]), args[3]))
            return original(*args, **kwargs)
        with patch("cipheur.repair_v06._priorities", side_effect=record):
            repair_schedule(graph, cover_program(), initial=("0", "1"), seconds=None, config=config)
        self.assertEqual(calls[0][1], "degree")
        self.assertTrue(all(len(nodes) <= config.max_patch_vertices for nodes, mode in calls
                            if mode == "program"))

    def test_target_extension_is_explicit_and_random_node_capped_runs_reproduce(self):
        graph = graph_of((6, 6, 5, 5, 5), itertools.product((0, 1), (2, 3, 4)))
        config = RepairConfig(max_destroy=2, max_patch_vertices=5, node_budget_per_patch=1,
                              max_search_nodes=2, upper_pruning=False, policy_scope="target_and_branch")
        first = repair_schedule(graph, initial=("0", "1"), priority="random", seconds=None,
                                config=config, random_seed=37)
        second = repair_schedule(graph, initial=("0", "1"), priority="random", seconds=None,
                                 config=config, random_seed=37)
        for key in ("selected", "value_exact", "patch_trace", "meter", "status"):
            self.assertEqual(first[key], second[key])
        self.assertEqual(first["config"]["policy_scope"], "target_and_branch")
        self.assertTrue(first["budget_exhausted"])

    def test_work_caps_retain_feasible_initialization_and_last_improvement(self):
        graph = graph_of((6, 6, 5, 5, 5), itertools.product((0, 1), (2, 3, 4)))
        config = RepairConfig(max_destroy=2, max_patch_vertices=5, max_patches=1,
                              expansion_steps=0, upper_pruning=False)
        final = repair_schedule(graph, weight_program(), initial=("0", "1"), seconds=None, config=config)
        improved_stops = 0
        for work in range(final["meter"]["repair_work"] + final["meter"]["feature_work"] + 1):
            result = repair_schedule(graph, weight_program(), initial=("0", "1"), seconds=None,
                                     config=replace(config, max_work=work))
            self.assertTrue(independent(graph, result["selected"]))
            self.assertGreaterEqual(Fraction(result["value_exact"]), 12)
            self.assertEqual(result["improvements"], sum(r["committed"] for r in result["patch_trace"]))
            self.assertEqual(result["patches_attempted"], len(result["patch_trace"]))
            if result["budget_exhausted"] and Fraction(result["value_exact"]) > 12:
                improved_stops += 1
        self.assertGreater(improved_stops, 0)
        for clock in ("cpu", "wall"):
            stopped = repair_schedule(graph, weight_program(), initial=("0", "1"), seconds=0, clock=clock)
            self.assertEqual(stopped["value_exact"], "12")
            self.assertFalse(stopped["initialization_complete"])
            self.assertTrue(stopped["completed"])
            self.assertEqual(stopped["status"], "time_budget")
        prefix_graph = graph_of((2, 3, 4, 5, 6))
        prefixes = [repair_schedule(prefix_graph, priority="degree", seconds=None,
                                   config=RepairConfig(max_work=w, max_patches=0)) for w in range(100)]
        self.assertTrue(any(0 < len(r["selected"]) < 5 for r in prefixes))
        self.assertTrue(all(r["initial_selected"] == r["selected"] for r in prefixes))

    def test_errors_are_explicit_without_fallback_and_boundaries_remain_global(self):
        graph = graph_of((6, 6, 5, 5, 5, 100), itertools.product((0, 1), (2, 3, 4)))
        failure = repair_schedule(graph, {"invalid": True}, initial=("0", "1"), seconds=None)
        self.assertFalse(failure["completed"])
        self.assertEqual(failure["status"], "programme_or_repair_error")
        self.assertEqual(failure["selected"], ["0", "1"])
        self.assertFalse(failure["fallback_used"])
        result = repair_schedule(graph, weight_program(), fixed=("0",), excluded=("5",), seconds=None)
        self.assertIn("0", result["selected"])
        self.assertNotIn("5", result["selected"])
        self.assertTrue(independent(graph, result["selected"]))
        self.assertTrue(all("0" not in r["destroy"] for r in result["patch_trace"]))
        with self.assertRaises(ValueError):
            RepairConfig(policy_scope="all")
        with self.assertRaises(ValueError):
            RepairConfig(max_destroy=3, max_patch_vertices=2)
        with self.assertRaises(ValueError):
            repair_schedule(graph, initial=("0", "2"), priority="degree")


class TrainFeedbackContractTests(unittest.TestCase):
    def test_mixed_inventory_selects_only_train_and_refuses_nontrain_execution(self):
        graph = graph_of((2, 3), ((0, 1),))
        data = {"records": [{"id": "train1", "split": "train", "graph": graph.to_dict()},
                            {"id": "test1", "split": "test", "graph": "do_not_materialize"}]}
        contexts = feedback.train_contexts(data)
        self.assertEqual([c["id"] for c in contexts], ["train1"])
        with self.assertRaises(ValueError):
            feedback.train_contexts(data, split="test")
        with self.assertRaises(ValueError):
            feedback.train_contexts({"contexts": [{"id": "unmarked", "graph": graph.to_dict()}]})
        with self.assertRaises(ValueError):
            feedback.train_contexts({"train": [{"id": "bad", "split": "test", "graph": graph.to_dict()}]})

    def test_prepare_verify_binds_exact_config_input_and_source_without_execution(self):
        graph = graph_of((2, 3), ((0, 1),))
        data = {"train": [{"id": "pair", "left": graph.to_dict(), "right": graph.to_dict()}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "data.json", root / "feedback"
            source.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(feedback, "repair_schedule", side_effect=AssertionError("must not execute")):
                protocol = feedback.prepare(source, output, workers=2)
                checked, contexts = feedback.verify_prepared(source, output, workers=2)
            self.assertEqual(protocol, checked)
            self.assertEqual(len(contexts), 2)
            self.assertEqual(protocol["repair_config"]["node_budget_per_patch"], 128)
            self.assertEqual(protocol["repair_config"]["max_work"], 200000)
            self.assertEqual(protocol["deadline_clock"], "wall")
            self.assertEqual(protocol["declared_seconds"], 0.5)
            self.assertFalse((output / "results.jsonl").exists())
            with self.assertRaises(ValueError):
                feedback.verify_prepared(source, output, workers=3)
            source.write_text(json.dumps(data) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                feedback.verify_prepared(source, output, workers=2)

    def test_worker_uses_fixed_degree_contract_and_reports_kernel_separately(self):
        graph = graph_of((2, 3), ((0, 1),))
        context = {"id": "tiny", "pair_id": "tiny", "side": "graph", "split": "train",
                   "family": "unit", "cluster": "tiny", "graph_sha256": graph.digest(),
                   "graph": graph.to_dict(), "fixed": [], "excluded": []}
        sentinel = {"completed": True, "feasible": True, "initialization_complete": False,
                    "budget_exhausted": True, "status": "time_budget", "value_exact": "0"}
        with patch.object(feedback, "repair_schedule", return_value=sentinel) as execute:
            row = feedback.execute_context(context)
        self.assertIs(row["result"], sentinel)
        self.assertTrue(row["assignment_returned"])
        self.assertEqual(execute.call_args.kwargs["priority"], "degree")
        self.assertEqual(execute.call_args.kwargs["clock"], "wall")
        self.assertEqual(execute.call_args.kwargs["seconds"], 0.5)
        self.assertEqual(execute.call_args.kwargs["config"], feedback.CONFIG)
        self.assertIn("graph_materialization_wall_seconds", row)
        with patch.object(feedback, "repair_schedule", side_effect=RuntimeError("unit failure")):
            error = feedback.execute_context(context)
        self.assertIsNone(error["result"])
        self.assertEqual(error["runner_error"]["type"], "RuntimeError")
        self.assertTrue(error["assignment_returned"])
        forbidden = feedback.execute_context({**context, "split": "test"})
        self.assertIsNone(forbidden["result"])
        self.assertEqual(forbidden["runner_error"]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
