"""Bounded packet-contract tests; no model, optimizer or research outcomes run."""
import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cipheur.model import Contact, Graph
from cipheur.programs import FEATURES
from scripts import prepare_refinement_round_v06 as r2


def vector(value=1):
    return {name: value for name in FEATURES}


class RefinementPacketContractTests(unittest.TestCase):
    def test_seed_order_exact_quality_then_work_then_source_identity(self):
        def row(identity, fit=584, quality="2693/4480", work="5"):
            return {"id": identity, "interface": {"strict_passed": fit},
                    "kernel_summary": {"macro_quality_exact": quality, "macro_work_exact": work}}
        # The rational difference is below float resolution: ordering must retain it.
        better = row("z", quality=str(Fraction(2693, 4480) + Fraction(1, 10**30)))
        base = row("a")
        self.assertEqual(min([base, better], key=r2.seed_key), better)
        self.assertEqual(min([row("a", work="6"), row("z")], key=r2.seed_key)["id"], "z")
        self.assertEqual(min([row("z"), row("a")], key=r2.seed_key)["id"], "a")
        self.assertEqual(min([better, row("x", fit=585, quality="0")], key=r2.seed_key)["id"], "x")

    def cycle_fixture(self):
        # Abstract certified arcs are supplied to this binding check; the routine
        # does not purport to prove their conditional values from this tiny graph.
        graph = Graph("source", tuple(Contact(v, 1, "s", v, 0, 1) for v in "abcd"),
                      frozenset({("a", "b"), ("c", "d")}))
        keys = [("state", "a", "b"), ("state", "c", "d")]
        reqs = [{"state": "state", "preferred": "state|a", "other": "state|b", "query_index": 0},
                {"state": "state", "preferred": "state|c", "other": "state|d", "query_index": 1}]
        joins = [{"negative": "state|b", "positive": "state|c", "negative_vector": vector(), "positive_vector": vector()},
                 {"negative": "state|d", "positive": "state|a", "negative_vector": vector(2), "positive_vector": vector(2)}]
        seed = {"interface": {"demanded_features": [], "quotient": {
            "structural_witnesses": [{"kind": "directed_cycle", "requirements": reqs, "equality_joins": joins}]}}}
        return graph, keys, seed

    def test_every_concrete_cycle_arc_and_join_endpoint_is_retained(self):
        graph, keys, seed = self.cycle_fixture()
        cycles, mandatory, _ = r2.concrete_cycles(seed, {}, {"state": graph}, dict.fromkeys(keys), {"state": keys})
        self.assertEqual(mandatory, keys)
        self.assertEqual(len(cycles[0]["joins"]), 2)
        bad = copy.deepcopy(seed)
        bad["interface"]["quotient"]["structural_witnesses"][0]["equality_joins"][0]["positive"] = "state|a"
        with self.assertRaisesRegex(ValueError, "close"):
            r2.concrete_cycles(bad, {}, {"state": graph}, dict.fromkeys(keys), {"state": keys})

    def test_near_equal_float_vectors_do_not_create_an_equality_join(self):
        graph, keys, seed = self.cycle_fixture()
        seed["interface"]["quotient"]["structural_witnesses"][0]["equality_joins"][0]["positive_vector"]["weight"] = 1.0000000000000002
        with self.assertRaisesRegex(ValueError, "differs exactly"):
            r2.concrete_cycles(seed, {}, {"state": graph}, dict.fromkeys(keys), {"state": keys})

    def test_strict_filtered_query_index_cannot_bind_another_arc(self):
        graph, keys, seed = self.cycle_fixture()
        seed["interface"]["quotient"]["structural_witnesses"][0]["requirements"][0]["query_index"] = 1
        with self.assertRaisesRegex(ValueError, "strict-query index"):
            r2.concrete_cycles(seed, {}, {"state": graph}, dict.fromkeys(keys), {"state": keys})

    def test_feedback_closure_caps_and_order_do_not_depend_on_input_order(self):
        records = [{"id": "public", "paired": False, "cluster": "source"},
                   {"id": "left", "paired": True, "pair": "p", "cluster": "p"},
                   {"id": "right", "paired": True, "pair": "p", "cluster": "p"}]
        mandatory = [("public", "a", "b")]
        failed = [{"state": "right", "a": "x", "b": "y", "preferred": "y", "passed": False}]
        seed = {"interface": {"strict_checks": failed}}
        strict = {mandatory[0]: {"kind": "alias"}, ("right", "y", "x"): {"kind": "ordinary"}}
        got = r2.choose_feedback(seed, records, strict, mandatory)
        other = r2.choose_feedback(seed, list(reversed(records)), strict, mandatory)
        self.assertEqual(got, other)
        self.assertEqual(set(got[1]), {"public", "left", "right"})
        with patch.object(r2, "STATE_CAP", 2):
            capped = r2.choose_feedback(seed, records, strict, mandatory)
            self.assertEqual(capped[0], mandatory)
            self.assertEqual(capped[1], ["public"])
        with patch.object(r2, "LABEL_CAP", 0):
            with self.assertRaisesRegex(ValueError, "Mandatory"):
                r2.choose_feedback(seed, records, strict, mandatory)

    def test_finalization_rejects_modified_draft_before_authorizing_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            study = Path(temp)
            r2.write(study / "draft_protocol.json", {"status": "draft"})
            r2.write(study / "preparation_receipt.json", {"source_sha256": r2.digest(r2.__file__),
                      "immutable_prepared_files_sha256": {"draft_protocol.json": r2.digest(study / "draft_protocol.json")}})
            r2.write(study / "draft_protocol.json", {"status": "changed"})
            with patch.object(r2, "check_sources", return_value={}):
                with self.assertRaisesRegex(ValueError, "draft byte changed"):
                    r2.finalize(study, study / "plan.json", study / "transport.py")
            self.assertFalse((study / "protocol.json").exists())
            self.assertFalse((study / "freeze_receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
