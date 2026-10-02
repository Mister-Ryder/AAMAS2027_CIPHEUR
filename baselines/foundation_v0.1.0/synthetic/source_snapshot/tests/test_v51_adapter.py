"""Integrity tests for the optional frozen V51 adapter, not effectiveness tests."""
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import unittest

from cipheur.model import Graph, aligned_intervention
from cipheur.v51_adapter import load_v51_pair, verify_v51_selection, _load_legacy


DEFAULT_ROOT = (Path(__file__).resolve().parents[3] / "2026-ESWA" /
                "DAI2026_SNSD_V51_STABLE")
STABLE_ROOT = Path(os.environ.get("CIPHEUR_V51_STABLE_ROOT", str(DEFAULT_ROOT)))


def legacy_available():
    try:
        import numpy  # noqa: F401 -- adapter's optional dependency
    except ImportError:
        return False
    return (STABLE_ROOT / "SNSD_V51_FINAL" / "src" / "snsd_core" / "data.py").is_file()


@unittest.skipUnless(legacy_available(), "Optional frozen V51 project/NumPy unavailable")
class V51AdapterTests(unittest.TestCase):
    def test_aligned_prefixes_match_original_graph_and_hashes(self):
        legacy, _ = _load_legacy(STABLE_ROOT.resolve())
        csv_path = STABLE_ROOT / "SNSD_V51_FINAL" / "data" / "C3.csv"
        dataset = legacy["data"].load_arcs(str(csv_path))
        for limit in (32, 64):
            with self.subTest(limit=limit):
                left, right = load_v51_pair(STABLE_ROOT, limit=limit)
                self.assertEqual(left.contacts, right.contacts)
                self.assertEqual([c.id for c in left.contacts], [str(i) for i in range(limit)])
                self.assertEqual(aligned_intervention(left, right)["parameter_changes"],
                                 {"ground_trans_time": [340, 500]})
                for graph, gap in ((left, 340), (right, 500)):
                    original = legacy["graph"].build_conflict_graph(
                        dataset.arcs[:limit], legacy["graph"].ConflictParameters(ground_trans_time=gap))
                    self.assertEqual(graph.edges, frozenset(tuple(sorted((str(int(a)), str(int(b)))))
                                                           for a, b in original.edges))
                    self.assertEqual(graph.provenance["legacy_graph_hash"], original.graph_hash)
                    self.assertEqual(graph.provenance["scope"], "prefix_subset_smoke_only")
                    self.assertEqual(graph.provenance["source_data"]["sha256"],
                                     sha256(csv_path.read_bytes()).hexdigest())
                    for receipt in graph.provenance["source_files"].values():
                        self.assertEqual(receipt["sha256"], sha256(Path(receipt["path"]).read_bytes()).hexdigest())
                    self.assertEqual(Graph.from_dict(graph.to_dict()).digest(), graph.digest())
                    for contact, arc in zip(graph.contacts, dataset.arcs):
                        self.assertEqual((contact.weight, contact.start, contact.end),
                                         (arc.weight, arc.link_st, arc.link_et))
                        self.assertEqual((contact.satellite, contact.station),
                                         (arc.satellite_name, arc.ground_name))

    def test_original_partial_overlap_and_target_parameter(self):
        # First two contacts partially overlap by 200: the unusual legacy
        # satellite rule allows them at change_time=150, but forbids at 250.
        text = ("ground,satellite,link_st,link_et,trace_st,trace_et\n"
                "g1,s1,0,400,0,400\n"
                "g2,s1,200,600,200,600\n"
                "g3,s2,0,100,0,100\n"
                "g3,s3,450,550,450,550\n")
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "contracts.csv"
            csv_path.write_text(text, encoding="utf-8")
            before, after = load_v51_pair(STABLE_ROOT, csv_path, limit=4,
                                          parameter="satellite_change_time", before=150, after=250)
            self.assertNotIn(("0", "1"), before.edges)
            self.assertIn(("0", "1"), after.edges)
            self.assertEqual(before.contacts, after.contacts)
            self.assertEqual(after.provenance["intervention_edge_changes"],
                             {"added": 1, "removed": 0, "graph_changed": True})
            self.assertTrue(verify_v51_selection(before, ("0", "1"))["feasible"])
            self.assertFalse(verify_v51_selection(after, ("0", "1"))["feasible"])
            self.assertEqual(verify_v51_selection(after, ("0", "1"))["mapped_local_ids"], [0, 1])
            left, right = load_v51_pair(STABLE_ROOT, csv_path, limit=4,
                                        parameter="ground_trans_time", before=340, after=500)
            self.assertNotIn(("2", "3"), left.edges)
            self.assertIn(("2", "3"), right.edges)

    def test_checker_preserves_invalid_and_duplicate_ids(self):
        left, _ = load_v51_pair(STABLE_ROOT, limit=32)
        self.assertTrue(verify_v51_selection(left, ("0",))["feasible"])
        duplicate = verify_v51_selection(left, ("0", "0"))
        self.assertFalse(duplicate["feasible"])
        self.assertEqual(duplicate["mapped_local_ids"], [0, 0])
        self.assertEqual(duplicate["duplicate_local_ids"], [0])
        invalid = verify_v51_selection(left, ("unknown",))
        self.assertFalse(invalid["feasible"])
        self.assertEqual(invalid["invalid_contact_ids"], ["unknown"])


class V51ArgumentTests(unittest.TestCase):
    def test_rejects_invalid_interventions_before_loading(self):
        for overrides in ({"limit": 0}, {"limit": -1}, {"limit": True},
                          {"parameter": "station_gap"}, {"before": -1},
                          {"before": 340, "after": 340}, {"after": 500.5}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                load_v51_pair(Path("missing"), **overrides)

    def test_missing_data_mentions_standalone_smoke(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "standalone synthetic smoke"):
                load_v51_pair(Path(directory))


if __name__ == "__main__":
    unittest.main()
