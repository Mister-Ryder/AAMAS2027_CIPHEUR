"""Independent finite checks of v04 certificates, scopes and selection."""
import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from fractions import Fraction

from cipheur.compiled import schedule_compiled
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph
from cipheur.oracle import local_bound
from cipheur.relevance_synthesis_v04 import (
    CancelledCompletionOracle, build_bank, components, fresh_temporal_data,
    fresh_temporal_pair, guided_candidates, load_train, select_candidates,
    train_context,
)
from cipheur.study_data_v04 import build_fresh_study, prior_id_manifest


def make_graph(weights, edges):
    return Graph("test", tuple(Contact(v, w, v, v, 0, 1)
                 for v, w in weights.items()), frozenset(edges))


def exhaustive_conditional(graph, action, fixed=(), excluded=()):
    """Independent enumeration, without oracle partitioning or its bounds."""
    active = sorted(graph.available(fixed, excluded))
    optimum = Fraction(0)
    for size in range(len(active) + 1):
        for subset in itertools.combinations(active, size):
            chosen = tuple(fixed) + subset
            if action in subset and graph.feasible(chosen):
                optimum = max(optimum, sum((Fraction(graph.nodes[v].weight)
                                            for v in chosen), Fraction(0)))
    return optimum


class CancellationCertificateTests(unittest.TestCase):
    def test_random_exhaustive_conditional_differences_and_witnesses(self):
        rng = random.Random(470291)
        for index in range(32):
            names = list("abcdefg")[:4 + index % 4]
            graph = make_graph({v: rng.choice((0., .1, .2, 1., 3., 7.)) for v in names},
                [edge for edge in itertools.combinations(names, 2) if rng.random() < .37])
            fixed = (names[0],) if index % 3 == 0 else ()
            excluded = (names[-1],) if index % 3 == 1 else ()
            active = sorted(graph.available(fixed, excluded))
            true_values = {v: exhaustive_conditional(graph, v, fixed, excluded) for v in active}
            for limit, calls in ((0, 20), (1, 2), (5, 20), (100, 20), (0, 0)):
                oracle = CancelledCompletionOracle(graph, fixed, excluded,
                    nodes_per_component=limit, max_nodes=limit * 3,
                    max_search_component=5, max_calls=calls)
                for a, b in itertools.combinations(active, 2):
                    row = oracle.difference(a, b)
                    exact = true_values[a] - true_values[b]
                    self.assertLessEqual(Fraction(row["lower_exact"]), exact)
                    self.assertGreaterEqual(Fraction(row["upper_exact"]), exact)
                    self.assertLessEqual(Fraction(row["lower"]), exact)
                    self.assertGreaterEqual(Fraction(row["upper"]), exact)
                    if row["preferred"] == a:
                        self.assertGreater(exact, Fraction(1e-8))
                    elif row["preferred"] == b:
                        self.assertLess(exact, -Fraction(1e-8))
                    for side_rows in row["unmatched"].values():
                        for component in side_rows:
                            witness = component["bound"]["selected"]
                            self.assertTrue(set(witness) <= set(component["vertices"]))
                            self.assertTrue(graph.feasible(witness))
                            self.assertEqual(sum((Fraction(graph.nodes[v].weight)
                                for v in witness), Fraction(0)), Fraction(component["bound"]["lower_exact"]))
                self.assertLessEqual(oracle.expanded_nodes, limit * 3)
                self.assertLessEqual(oracle.calls, calls)

    def test_conditioning_cancels_unknown_component_of_connected_original_graph(self):
        # x connects both actions to C5. Conditioning on either action deletes
        # x and the other action, leaving exactly the same unsolved C5.
        graph = make_graph({"a": 3, "b": 2, "x": 1, **{f"c{i}": 2 for i in range(5)}},
            [("a", "b"), ("a", "x"), ("b", "x"), ("x", "c0")]
            + [(f"c{i}", f"c{(i + 1) % 5}") for i in range(5)])
        self.assertEqual(len(components(graph, graph.nodes)), 1)
        oracle = CancelledCompletionOracle(graph, nodes_per_component=0, max_nodes=0, max_calls=0)
        row = oracle.difference("a", "b")
        self.assertEqual(row["lower_exact"], "1")
        self.assertEqual(row["upper_exact"], "1")
        self.assertEqual(row["preferred"], "a")
        self.assertEqual(row["cancelled_components"], [[f"c{i}" for i in range(5)]])
        self.assertEqual(oracle.calls, 0)
        la = local_bound(graph, {"a", "b"}, "a", max_nodes=0)
        lb = local_bound(graph, {"a", "b"}, "b", max_nodes=0)
        self.assertLessEqual(Fraction(la.lower_exact) - Fraction(lb.upper_exact), 0)
        self.assertGreaterEqual(Fraction(la.upper_exact) - Fraction(lb.lower_exact), 0)

    def test_pool_scope_does_not_claim_global_regret(self):
        graph = make_graph({"a": 4, "b": 3, "outside": 5},
                           list(itertools.combinations(("a", "b", "outside"), 2)))
        oracle = CancelledCompletionOracle(graph, nodes_per_component=100)
        row = oracle.pool_regret("a", ("a", "b"))
        self.assertEqual(row["upper_exact"], "0")
        self.assertEqual(exhaustive_conditional(graph, "outside") - exhaustive_conditional(graph, "a"), 1)
        self.assertIn("not an upper bound on all-action", row["scope"])
        for args in (("missing", "missing", 0), ("a", "b", -1), ("a", "b", float("nan"))):
            with self.assertRaises(ValueError):
                oracle.difference(*args)
        with self.assertRaises(ValueError):
            oracle.pool_regret("a", ("outside", "missing"))


class DevelopmentProtocolTests(unittest.TestCase):
    def test_bank_provenance_and_full_sliced_trace_parity(self):
        root = Path(__file__).resolve().parents[1]
        bank = build_bank(root / "experiments/discovery/v03")
        self.assertEqual(len(bank), 93)
        proposals = guided_candidates()
        saved = json.loads((root / "configs/relevance_v04_guided_bank.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["candidates"], proposals)
        self.assertEqual(len(proposals), 12)
        for seed in (129, 203):
            rng = random.Random(seed)
            names = [str(i) for i in range(9)]
            graph = make_graph({v: rng.randrange(1, 24) / 4 for v in names},
                [edge for edge in itertools.combinations(names, 2) if rng.random() < .32])
            for source in proposals:
                program = FeatureRuleProgram.from_dict(source)
                full = schedule_compiled(graph, program, score_slice=False)
                sliced = schedule_compiled(graph, program, score_slice=True)
                self.assertEqual(full["selected"], sliced["selected"])
                self.assertEqual(full["value"], sliced["value"])
                self.assertEqual(full["trace"], sliced["trace"])
        # Both branches are taken in one complete rollout. These are synthetic
        # semantic fixtures, not data used to choose either threshold.
        for source, size in zip(proposals[-2:], (67, 131)):
            graph = make_graph({f"n{i:03d}": 1 + i % 7 for i in range(size)}, ())
            program = FeatureRuleProgram.from_dict(source)
            full = schedule_compiled(graph, program, score_slice=False)
            sliced = schedule_compiled(graph, program, score_slice=True)
            self.assertEqual(full["trace"], sliced["trace"])
            self.assertEqual(full["selected"], sliced["selected"])

    def test_train_context_actual_replay_and_difference_soundness(self):
        graph = make_graph({"a": 4, "b": 3, "c": 2, "d": 1}, (("a", "b"), ("a", "c")))
        bank = [{"id": "fixture:0", "arm": "fixture", "index": 0,
            "program": FeatureRuleProgram("weight", [], "weight").to_dict()},
            {"id": "fixture:1", "arm": "fixture", "index": 1,
            "program": FeatureRuleProgram("small_degree", [], "-degree").to_dict()}]
        config = {"program_cpu_seconds": 5, "max_rollout_steps": 2,
            "max_states_per_context": 3, "epsilon": 1e-8, "max_matched_full_comparisons": 3,
            "cancellation": {"nodes_per_component": 100, "max_search_component": 20,
                             "max_nodes": 500, "max_calls": 100}}
        pair = {"id": "fixture", "family": "fixture", "left": graph.to_dict(), "fixed": [], "excluded": []}
        context = train_context((pair, "left", bank, config))
        for state in context["states"]:
            self.assertTrue(graph.feasible(state["fixed"]))
            for source in state["sources"]:
                rollout = next(row for row in context["rows"] if row["candidate_id"] == source["candidate_id"])
                replay = [item["selected"] for item in rollout["trace"][:source["step"]]]
                self.assertEqual(sorted(replay), state["fixed"])
            for delta in state["differences"]:
                exact = exhaustive_conditional(graph, delta["a"], state["fixed"]) - exhaustive_conditional(graph, delta["b"], state["fixed"])
                self.assertEqual(Fraction(delta["lower_exact"]), exact)
                self.assertEqual(Fraction(delta["upper_exact"]), exact)
            for cid, regret in state["regret"].items():
                self.assertEqual(regret["actual_reached_in_recorded_rollout"],
                                 any(s["candidate_id"] == cid for s in state["sources"]))

    def test_fresh_seeds_and_load_train_reject_test_containers(self):
        config = {"profiles": ["standard", "dense_long"], "regimes": ["balanced", "ground_scarce"],
                  "sizes": [8, 16], "per_cell": {"validation": 2, "test": 2}, "seed_namespace": 40000000}
        data = fresh_temporal_data(config)
        seeds = {split: {p["source"]["seed"] for p in records} for split, records in data.items()}
        self.assertFalse(seeds["validation"] & seeds["test"])
        for split, records in data.items():
            for pair in records:
                self.assertEqual(pair["left"]["contacts"], pair["right"]["contacts"])
                self.assertFalse(pair["source"]["outcome_filtering"])
                old_seed = 9000000 + (1 if split == "validation" else 2) * 1000000 + pair["source"]["size"] * 1000
                if pair["source"]["profile"] == "dense_long":
                    old_seed += 100000000
                self.assertNotEqual(pair["source"]["seed"], old_seed)
        train = fresh_temporal_pair("train", 8, 0, "balanced")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.json"
            path.write_text(json.dumps({"train": [train], "validation": "must not be iterated"}), encoding="utf-8")
            selected, receipt = load_train(path, min_contacts=1, max_contacts=16)
            self.assertEqual(selected, [train])
            self.assertFalse(receipt["validation_and_test_outcomes_used"])
            path.write_text(json.dumps({"train": [train], "test": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_train(path, min_contacts=1, max_contacts=16)

    def test_unknown_is_secondary_and_counterfactual_regret_is_excluded(self):
        graph = make_graph({"a": 10}, ())
        bank = [{"id": "baseline:1", "arm": "baseline", "index": 1, "program": {}},
                {"id": "guided_v04:0", "arm": "guided_v04", "index": 0, "program": {"name": "first"}},
                {"id": "guided_v04:1", "arm": "guided_v04", "index": 1, "program": {"name": "second"}}]
        context = {"family": "fixture", "graph": graph.to_dict(),
            "rows": [{"candidate_id": entry["id"], "value": 10, "completed": True,
                      "feature_work": 10, "cpu_seconds": .1} for entry in bank],
            "states": [{"regret": {
                "guided_v04:0": {"actual_reached_in_recorded_rollout": True, "lower": 1, "upper": 3, "unknown_comparisons": 2},
                "guided_v04:1": {"actual_reached_in_recorded_rollout": True, "lower": 0, "upper": 2, "unknown_comparisons": 10},
            }}, {"regret": {"guided_v04:1": {"actual_reached_in_recorded_rollout": False,
                                              "lower": 999, "upper": 999, "unknown_comparisons": 999}}}]}
        information = {"candidate_quotients": {entry["id"]: {"contradictory": False} for entry in bank}}
        config = {"timeout_relative_work": 100, "cost_penalty": .002,
                  "primary_tie_band": .002, "joint_information_gate": True}
        assessments, programs, selection = select_candidates([context], bank, information, config)
        second = next(row for row in assessments if row["id"] == "guided_v04:1")
        self.assertEqual(second["unknown_comparisons"], 10)
        self.assertEqual(second["reached_audited_states"], 1)
        self.assertEqual(second["macro_actual_regret_upper"], .2)
        self.assertEqual(programs["guided_v04"]["name"], "second")
        self.assertTrue(selection["guided_v04"]["unknown_is_not_a_hard_gate"])

    def test_prior_c3_manifest_covers_all_splits_and_checks_actual_contacts(self):
        old = make_graph({"123": 1, "124": 2}, (("123", "124"),))
        new = make_graph({"125": 1}, ())
        def pair(graph):
            return {"family": "c3", "left": graph.to_dict(), "right": graph.to_dict(),
                    "source": {"original_ids": [int(v) for v in graph.nodes], "source_data_sha256": "a" * 64}}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.json"
            data = {"train": [pair(old)], "validation": [], "test": [pair(new)]}
            path.write_text(json.dumps(data), encoding="utf-8")
            manifest = prior_id_manifest([path])
            self.assertEqual(manifest["original_ids"], [123, 124, 125])
            self.assertFalse(manifest["outcomes_read"])
            data["test"][0]["source"]["original_ids"] = [999]
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                prior_id_manifest([path])

    def test_fresh_builder_requires_freeze_and_rejects_source_overlap(self):
        config = {"profiles": ["standard"], "regimes": ["balanced"], "sizes": [8],
            "per_cell": {"validation": 1, "test": 1}, "seed_namespace": 40000000,
            "c3_target_sizes": [1], "c3_pairs_per_size": 1, "independent_unit": "source block"}
        frozen = {"test_accessed": False, "selection_split": "train", "programs": {"g": {"name": "frozen"}}}
        generated = build_fresh_study(config, frozen)
        self.assertEqual(generated["protocol"]["counts"], {"validation": 1, "test": 1})
        self.assertIn("instance_fingerprint", generated["test"][0]["source"])
        # _record internally returns Graph objects. The public builder must
        # serialize them before either CLI export or downstream Graph.from_dict.
        portable = json.loads(json.dumps(generated, allow_nan=False))
        for split in ("validation", "test"):
            original = fresh_temporal_pair(split, 8, 0, "balanced", namespace=40000000)
            for side in ("left", "right"):
                self.assertIsInstance(portable[split][0][side], dict)
                self.assertEqual(Graph.from_dict(portable[split][0][side]).digest(),
                                 Graph.from_dict(original[side]).digest())
        with self.assertRaises(ValueError):
            build_fresh_study(config, {**frozen, "test_accessed": True})
        graph = make_graph({"123": 1}, ())
        record = {"id": "c3_test", "family": "c3", "source": {"original_ids": [123]},
                  "left": graph.to_dict(), "right": graph.to_dict()}
        fake = {"train": [], "validation": [], "test": [record],
                "protocol": {"c3": {"data_sha256": "a" * 64}}}
        manifest = {"original_ids": [123], "source_data_sha256": ["a" * 64]}
        with patch("cipheur.study_data_v04.build_study", return_value=fake):
            with self.assertRaises(AssertionError):
                build_fresh_study(config, frozen, manifest, "irrelevant-mocked-source")


if __name__ == "__main__":
    unittest.main()
