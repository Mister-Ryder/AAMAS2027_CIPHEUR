"""Data-integrity and mechanism checks; generation never uses outcome labels."""
from dataclasses import replace
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur.experiment_data import SPLITS, audit_suite, diagnostic_pair, make_suite
from cipheur.model import Graph, aligned_intervention
from cipheur.programs import features
from cipheur.v51_adapter import _load_legacy, verify_v51_selection


def conditional_brute(record, side, action):
    graph = record[side]
    fixed = record["fixed"] + (action,)
    available = sorted(graph.available(fixed, record["excluded"]))
    best = graph.value(fixed)
    for size in range(len(available) + 1):
        for subset in itertools.combinations(available, size):
            selected = fixed + subset
            if graph.feasible(selected):
                best = max(best, graph.value(selected))
    return best


class SyntheticDataTests(unittest.TestCase):
    def test_true_temporal_reversal_aliases_all_nine_base_features(self):
        for split in SPLITS:
            record = diagnostic_pair(split, 0, "reversal")
            roles = record["source"]["semantic_roles"]
            scale = record["source"]["weight_scale"]
            z_value = record["left"].value(record["fixed"])
            self.assertEqual(record["a"], roles["a"])
            self.assertEqual(record["b"], roles["b"])
            self.assertEqual(record["left"].contacts, record["right"].contacts)
            self.assertEqual(len(record["left"].nodes), 9)
            self.assertEqual(aligned_intervention(record["left"], record["right"], record["fixed"])
                             ["parameter_changes"], {"station_gap": {
                                 "train": [0.0, 4.0], "validation": [0.2, 4.4], "test": [0.6, 5.0]}[split]})
            for side in ("left", "right"):
                graph = record[side]
                active = graph.available(record["fixed"], record["excluded"])
                self.assertEqual(features(graph, record["a"], active), features(graph, record["b"], active))
                self.assertEqual(len(features(graph, record["a"], active)), 9)
                self.assertFalse(graph.adj[roles["z"]])
                self.assertTrue(graph.feasible(record["fixed"] + (record["a"],)))
                self.assertTrue(graph.feasible(record["fixed"] + (record["b"],)))
            x_ids = [roles[f"x{i}"] for i in range(1, 4)]
            y_ids = [roles[f"y{i}"] for i in range(1, 4)]
            self.assertTrue(record["left"].feasible(x_ids))
            self.assertEqual(sum(tuple(sorted(pair)) in record["right"].edges
                                 for pair in itertools.combinations(x_ids, 2)), 3)
            for side in ("left", "right"):
                self.assertEqual(sum(tuple(sorted(pair)) in record[side].edges
                                     for pair in itertools.combinations(y_ids, 2)), 1)
            for side, action, expected in (("left", record["a"], 20), ("left", record["b"], 26),
                                           ("right", record["a"], 20), ("right", record["b"], 14)):
                self.assertEqual(conditional_brute(record, side, action), z_value + expected * scale)

    def test_preservation_and_tie_are_retained_with_real_external_edge_change(self):
        for split in SPLITS:
            for subtype in ("preservation", "tie"):
                record = diagnostic_pair(split, 4, subtype)
                roles = record["source"]["semantic_roles"]
                edge = tuple(sorted((roles["outside1"], roles["outside2"])))
                self.assertEqual(record["right"].edges - record["left"].edges, {edge})
                for side in ("left", "right"):
                    active = record[side].available(record["fixed"], record["excluded"])
                    self.assertEqual(features(record[side], record["a"], active),
                                     features(record[side], record["b"], active))
                    a_value = conditional_brute(record, side, record["a"])
                    b_value = conditional_brute(record, side, record["b"])
                    if subtype == "tie":
                        self.assertEqual(a_value, b_value)
                    else:
                        self.assertGreater(b_value, a_value)

    def test_deterministic_suite_has_disjoint_seeds_instances_targets_and_sizes(self):
        config = {"counts": {"diagnostic": 10, "random_temporal": 4, "c3": 0}}
        with patch("cipheur.oracle.solve", side_effect=AssertionError("Oracle called during generation")):
            suite = make_suite(config)
        repeated = make_suite(config)
        fingerprints = []
        seeds = []
        for split, sizes in (("train", (16, 24)), ("validation", (18, 26)), ("test", (20, 28))):
            self.assertEqual(len(suite[split]), 14)
            self.assertEqual([r["source"]["instance_fingerprint"] for r in suite[split]],
                             [r["source"]["instance_fingerprint"] for r in repeated[split]])
            random_records = [r for r in suite[split] if r["family"] == "random_temporal"]
            self.assertEqual([len(r["left"].nodes) for r in random_records], list(sizes) * 2)
            self.assertEqual({r["source"]["subtype"] for r in suite[split] if r["family"] == "diagnostic"},
                             {"reversal", "preservation", "tie"})
            for record in suite[split]:
                fingerprints.append(record["source"]["instance_fingerprint"])
                seeds.append(record["source"]["seed"])
                for graph in (record["left"], record["right"]):
                    self.assertTrue(graph.feasible(record["fixed"]))
                    if record["a"] is not None:
                        self.assertTrue(graph.feasible(record["fixed"] + (record["a"],)))
                        self.assertTrue(graph.feasible(record["fixed"] + (record["b"],)))
                json.dumps({**record, "left": record["left"].to_dict(), "right": record["right"].to_dict()})
        self.assertEqual(len(fingerprints), len(set(fingerprints)))
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertTrue(suite["audit"]["passed"])
        self.assertTrue(suite["audit"]["target_configurations_disjoint"])
        self.assertEqual(suite["protocol"]["oracle_calls_during_generation"], 0)

    def test_no_common_conflict_edge_does_not_remove_random_record(self):
        # One contact cannot have a competing action.  Patching graph creation
        # to return an empty edge set exercises retention without outcome tests.
        import cipheur.experiment_data as data_module
        original = data_module.temporal_graph
        def no_edges(*args, **kwargs):
            graph = original(*args, **kwargs)
            return Graph(graph.name, graph.contacts, frozenset(), graph.constraints)
        with patch("cipheur.experiment_data.temporal_graph", side_effect=no_edges):
            suite = make_suite({"counts": {"diagnostic": 0, "random_temporal": 2, "c3": 0}})
        for split in SPLITS:
            self.assertEqual(len(suite[split]), 2)
            self.assertTrue(all(record["a"] is None and record["b"] is None for record in suite[split]))

    def test_unavailable_c3_is_explicit_and_has_no_synthetic_substitution(self):
        with tempfile.TemporaryDirectory() as directory:
            suite = make_suite({"stable_root": directory,
                                "counts": {"diagnostic": 0, "random_temporal": 0, "c3": 1}})
        self.assertEqual(suite["coverage"]["c3"]["status"], "unavailable")
        self.assertFalse(suite["coverage"]["c3"]["synthetic_substitution"])
        self.assertTrue(suite["coverage"]["c3"]["reason"])
        self.assertTrue(all(not suite[split] for split in SPLITS))

    def test_partial_split_counts_and_invalid_ranges(self):
        suite = make_suite({"counts": {"diagnostic": {"train": 2}, "random_temporal": 0, "c3": 0}})
        self.assertEqual([len(suite[split]) for split in SPLITS], [2, 0, 0])
        for counts in ({"diagnostic": 1001}, {"random_temporal": -1}, {"diagnostic": True}):
            with self.assertRaises(ValueError):
                make_suite({"counts": {"c3": 0, **counts}})

    def test_audit_rejects_record_and_instance_leakage(self):
        suite = make_suite({"counts": {"diagnostic": 1, "random_temporal": 0, "c3": 0}})
        leaked = dict(suite["train"][0])
        leaked["id"] = "different_id"
        leaked["source"] = {**leaked["source"], "split": "test"}
        suite["test"].append(leaked)
        with self.assertRaisesRegex(ValueError, "physical instance"):
            audit_suite(suite)


STABLE_ROOT = Path(__file__).resolve().parents[3] / "2026-ESWA" / "DAI2026_SNSD_V51_STABLE"
try:
    import numpy  # noqa: F401
    LEGACY_AVAILABLE = (STABLE_ROOT / "SNSD_V51_FINAL" / "data" / "C3.csv").is_file()
except ImportError:
    LEGACY_AVAILABLE = False


@unittest.skipUnless(LEGACY_AVAILABLE, "Optional frozen V51 project/NumPy unavailable")
class C3DataTests(unittest.TestCase):
    def test_source_derived_windows_preserve_legacy_predicates_and_original_fields(self):
        suite = make_suite({"stable_root": str(STABLE_ROOT),
                            "counts": {"diagnostic": 0, "random_temporal": 0, "c3": 3}})
        legacy, _ = _load_legacy(STABLE_ROOT.resolve())
        dataset = legacy["data"].load_arcs(str(STABLE_ROOT / "SNSD_V51_FINAL" / "data" / "C3.csv"))
        original_id_sets = []
        self.assertEqual(suite["coverage"]["c3"]["data"]["total_opportunities"], 69923)
        for day, split in enumerate(SPLITS):
            self.assertEqual(len(suite[split]), 3)
            split_ids = set()
            for record in suite[split]:
                ids = record["source"]["original_ids"]
                self.assertFalse(split_ids.intersection(ids))
                split_ids.update(ids)
                self.assertLessEqual(len(ids), 28)
                source_arcs = [dataset.arcs[original_id] for original_id in ids]
                local_arcs = tuple(replace(arc, id=i) for i, arc in enumerate(source_arcs))
                for contact, arc in zip(record["left"].contacts, source_arcs):
                    self.assertEqual((contact.id, contact.weight, contact.satellite, contact.station,
                                      contact.start, contact.end),
                                     (str(arc.id), arc.weight, arc.satellite_name, arc.ground_name,
                                      arc.link_st, arc.link_et))
                    self.assertLessEqual(day * 86400, contact.start)
                    self.assertLess(contact.start, (day + 1) * 86400)
                for side in ("left", "right"):
                    graph = record[side]
                    parameters = {key: value for key, value in graph.constraints.items() if key != "model"}
                    expected = legacy["graph"].build_conflict_graph(
                        local_arcs, legacy["graph"].ConflictParameters(**parameters))
                    expected_edges = frozenset(tuple(sorted((str(ids[int(a)]), str(ids[int(b)]))))
                                               for a, b in expected.edges)
                    self.assertEqual(graph.edges, expected_edges)
                    self.assertTrue(verify_v51_selection(graph, record["fixed"])["feasible"])
            original_id_sets.append(split_ids)
        for first, second in itertools.combinations(original_id_sets, 2):
            self.assertFalse(first & second)
        self.assertTrue(suite["audit"]["passed"])


if __name__ == "__main__":
    unittest.main()
