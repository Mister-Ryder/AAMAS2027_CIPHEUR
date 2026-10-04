"""Outcome-free performance input contracts; only tiny graphs generated here."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur.model import Graph
from scripts import prepare_performance_v06 as builder


class PerformanceInputTests(unittest.TestCase):
    def test_exact_prespecified_frame_unique_seeds_and_parameters(self):
        protocol = builder.make_protocol()
        self.assertEqual(protocol["pairs"], 108)
        self.assertEqual(protocol["endpoints"], 216)
        self.assertEqual(protocol["sizes"], [512, 1024, 2048])
        self.assertEqual(len({c["seed"] for c in protocol["cells"]}), 108)
        self.assertEqual(len({c["id"] for c in protocol["cells"]}), 108)
        self.assertTrue(all(c["split"] == "test" for c in protocol["cells"]))
        self.assertEqual(protocol["profiles"]["standard"]["horizon_per_contact"], 1.8)
        self.assertEqual(protocol["profiles"]["dense_long"]["horizon_per_contact"], 0.18)
        self.assertEqual(protocol["generator"]["station_gap_left"], 0.5)
        self.assertEqual(protocol["generator"]["station_gap_right"], 6.0)
        self.assertEqual(protocol["optimization_calls"], 0)
        self.assertFalse(protocol["outcome_filtering"])
        json.dumps(protocol, allow_nan=False)

    def test_tiny_pair_contact_identity_intervention_and_independent_edge_replay(self):
        cell = {**builder.planned_cells()[0], "size": 12}
        first = builder.build_pair(cell)
        self.assertEqual(first, builder.build_pair(cell))
        pair, contexts = first
        left, right = Graph.from_dict(pair["left"]), Graph.from_dict(pair["right"])
        self.assertEqual(left.contacts, right.contacts)
        self.assertTrue(left.edges <= right.edges)
        self.assertEqual([r["graph_sha256"] for r in contexts], [left.digest(), right.digest()])
        for graph, gap in ((left, 0.5), (right, 6.0)):
            independent_edges = set()
            for i, a in enumerate(graph.contacts):
                for b in graph.contacts[i + 1:]:
                    first_contact, second = sorted((a, b), key=lambda c: (c.start, c.id))
                    if ((a.station == b.station and second.start < first_contact.end + gap)
                            or (a.satellite == b.satellite and second.start < first_contact.end)):
                        independent_edges.add(tuple(sorted((a.id, b.id))))
            self.assertEqual(graph.edges, frozenset(independent_edges))
            self.assertTrue(all(0.25 <= c.weight <= 20 and 0.5 <= c.end - c.start <= 12
                                for c in graph.contacts))
        another, _ = builder.build_pair({**cell, "ordinal": 1, "id": "second", "seed": cell["seed"] + 1})
        self.assertFalse({c["id"] for c in pair["left"]["contacts"]} &
                         {c["id"] for c in another["left"]["contacts"]})

    def test_plan_freeze_roundtrip_without_generating_or_evaluating_graphs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new_inputs"
            with patch.object(builder, "temporal_graph", side_effect=AssertionError("no graph generation")):
                protocol = builder.prepare(output)
                self.assertEqual(protocol, builder.verify_plan(output))
            self.assertFalse((output / "data.json").exists())
            with self.assertRaises(FileExistsError):
                builder.prepare(output)
            (output / "input_execution.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                builder.generate(output)
            path = output / "protocol.json"
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["profiles"]["dense_long"]["horizon_per_contact"] = 0.1
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                builder.verify_plan(output)


if __name__ == "__main__":
    unittest.main()
