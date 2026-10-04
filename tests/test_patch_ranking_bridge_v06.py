"""Tiny independent graphs only; never read real TRAIN or R2/TEST outcomes."""
from copy import deepcopy
from fractions import Fraction
import io
import itertools
import json
from pathlib import Path
import random
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph
from scripts import patch_ranking_bridge_v06 as bridge


def graph(weights, edges=()):
    return Graph("tiny", tuple(Contact(v, w, "S" + v, "G" + v, 0, 1)
                              for v, w in weights.items()), frozenset(edges))


def config(states=1):
    # Duplicate production limits, never import a real dataset or label file.
    return {"version": "tiny_bridge_test", "split": "train", "no_authoring_or_selection_feedback": True,
        "expected_states": states, "pairs_per_patch": 4, "max_patch_vertices": 24,
        "recurrence_states_per_query": 100000, "max_score_feature_work": 200000,
        "certificate_epsilon_exact": "0", "score_margin_exact": "0", "salt": "tiny-fixture",
        "required_roles": {"witness_joint": 4, "witness_quality": 4, "relations_quality": 4,
            "objective_quality": 4, "fixed_structural": 1, "fixed_base": 1, "degree": 1},
        "optional_eoh_identities": 4}


def fixture(g, incumbent, destroy, region, fixed=(), excluded=()):
    context = {"id": "tiny:0", "split": "train", "family": "tiny", "cluster": "tiny",
        "pair_id": "tiny", "side": "graph", "graph": g.to_dict(), "graph_sha256": g.digest(),
        "fixed": list(fixed), "excluded": list(excluded)}
    outside = set(incumbent) - set(destroy)
    trace = {"destroy": list(destroy), "patch": list(region),
        "full_region_size": len(g.available(outside, excluded)), "stage": "returned",
        "committed": False, "gain_exact": "0", "priority_order": []}
    row = {"id": context["id"], "split": "train", "method": "shared_kernel_degree",
        "graph_sha256": g.digest(), "fixed": list(fixed), "excluded": list(excluded),
        "result": {"priority": "degree", "config": {"policy_scope": "branch"},
                   "initial_selected": list(incumbent), "patch_trace": [trace]}}
    return context, row


def forced_optimum(g, region, action):
    ids = sorted(region)
    candidates = []
    for mask in range(1 << len(ids)):
        chosen = [v for i, v in enumerate(ids) if mask & (1 << i)]
        if action in chosen and g.feasible(chosen):
            candidates.append(sum((Fraction(g.nodes[v].weight) for v in chosen), Fraction()))
    return max(candidates)


def bank():
    p = FeatureRuleProgram("same_weight_program", [], "weight").to_dict()
    entries = [{"id": role + ":" + str(i), "role": role,
                "priority": "degree" if role == "degree" else "program",
                "program": None if role in ("degree", "fixed_base") else p}
               for role, count in config()["required_roles"].items() for i in range(count)]
    return {"selection_split": "train", "test_used_for_selection": False, "entries": entries}


class SamplingTests(unittest.TestCase):
    def test_first_constructed_patch_ignores_outcomes(self):
        g = graph({"a": 8, "b": 7, "c": 2, "z": 100}, [("a", "b")])
        c, r = fixture(g, ["a", "z"], ["a"], ["a", "b", "c"], ["z"])
        first = bridge.select_patch(c, r, config())
        altered = deepcopy(r)
        altered["result"]["patch_trace"][0].update(gain_exact="999", committed=True,
                                                    root_pruned=True, lower_exact="1000")
        altered["result"]["patch_trace"].append({"patch": ["c"], "gain_exact": "2000"})
        second = bridge.select_patch(c, altered, config())
        self.assertEqual(first["patch_index"], 0)
        self.assertEqual(first["outside_fixed"], ["z"])
        self.assertEqual(first["queries"], second["queries"])
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertNotEqual(first["feedback_row_sha256"], second["feedback_row_sha256"])

    def test_boundary_and_split_fail_closed(self):
        g = graph({"a": 2, "b": 1, "z": 1}, [("a", "b"), ("z", "b")])
        c, r = fixture(g, ["a", "z"], ["a"], ["a"], ["z"])
        self.assertEqual(bridge.select_patch(c, r, config())["patch"], ["a"])
        bad = deepcopy(r); bad["result"]["patch_trace"][0]["patch"].append("b")
        with self.assertRaises(ValueError): bridge.select_patch(c, bad, config())
        c["split"] = "test"
        with self.assertRaises(ValueError): bridge.select_patch(c, r, config())

    def test_no_patch_is_retained_and_no_score_is_called(self):
        g = graph({"a": 1})
        c, r = fixture(g, ["a"], [], [])
        r["result"]["patch_trace"] = []
        with patch.object(bridge, "local_difference", side_effect=AssertionError("No oracle during inventory")), \
             patch.object(bridge, "score_patch", side_effect=AssertionError("No scorer during inventory")):
            inventory = bridge.build_inventory([c], [r], config())
        self.assertEqual(inventory[0]["patch_status"], "no_constructed_nonempty_patch")
        self.assertEqual(inventory[0]["quota"]["pair_shortfall"], 4)

    def test_sha_core_and_full_strict_union_are_distinct_and_deduplicated(self):
        g = graph({str(i): 1 for i in range(6)}, [("0", "1"), ("2", "3")])
        core, quota = bridge.pair_plan(g, set(g.nodes), "x", config())
        self.assertEqual(len(core), 4)
        self.assertTrue(core[0]["competing"] and core[1]["competing"])
        reverse = Graph(g.name, tuple(reversed(g.contacts)), g.edges)
        self.assertEqual(core, bridge.pair_plan(reverse, set(g.nodes), "x", config())[0])
        existing = core[0]
        extra = next(p for p in itertools.combinations(sorted(g.nodes), 2)
                     if set(p) not in [{q["a"], q["b"]} for q in core])
        state = {"id": "x", "graph": g.to_dict(), "queries": core, "quota": quota}
        refs = [{"a": existing["b"], "b": existing["a"], "original_row_index": 0},
                {"a": extra[0], "b": extra[1], "original_row_index": 1}]
        bridge.enrich_queries(state, refs, config())
        self.assertEqual(len(state["queries"]), 5)
        self.assertEqual(sum(q["in_core_sha"] for q in state["queries"]), 4)
        self.assertEqual(sum(q["in_full_strict_bridge"] for q in state["queries"]), 2)
        self.assertEqual(state["queries"][0]["full_reference_rows"], [0])


class CertificateTests(unittest.TestCase):
    def test_memo_and_stopped_intervals_enclose_independent_enumeration(self):
        rng = random.Random(571)
        for _ in range(18):
            g = graph({str(i): rng.randrange(0, 13) / 4 for i in range(6)},
                      [p for p in itertools.combinations([str(i) for i in range(6)], 2) if rng.random() < .4])
            region = set(g.nodes) - {"5"}
            for a, b in itertools.combinations(sorted(region), 2):
                truth = forced_optimum(g, region, a) - forced_optimum(g, region, b)
                exact = bridge.local_difference(g, region, a, b, 100000)
                self.assertEqual(Fraction(exact["lower_exact"]), truth)
                self.assertEqual(Fraction(exact["upper_exact"]), truth)
                for cap in (0, 2):
                    bounded = bridge.local_difference(g, region, a, b, cap)
                    self.assertLessEqual(Fraction(bounded["lower_exact"]), truth)
                    self.assertGreaterEqual(Fraction(bounded["upper_exact"]), truth)
                    self.assertLessEqual(bounded["recurrence_states"], cap)
                    if bounded["preferred"] is not None:
                        self.assertEqual(bounded["preferred"], a if truth > 0 else b)

    def test_component_hard_stop_retains_unknown_and_witness(self):
        g = graph({"x": 6, "y": 9, "z": 6}, [("x", "y"), ("y", "z")])
        b = bridge.component_bound(g, set(g.nodes), 0)
        self.assertEqual(b["recurrence_states"], 0)
        self.assertFalse(b["exact"])
        self.assertLess(Fraction(b["lower_exact"]), Fraction(b["upper_exact"]))
        self.assertTrue(g.feasible(b["selected"]))

    def test_full_and_local_directions_can_disagree(self):
        g = graph({"a": 8, "b": 7, "x": 10, "y": 3},
                  [("a", "b"), ("a", "x"), ("b", "y")])
        full = bridge.local_difference(g, set(g.nodes), "a", "b")
        local = bridge.local_difference(g, {"a", "b", "y"}, "a", "b")
        self.assertEqual(full["preferred"], "b")
        self.assertEqual(local["preferred"], "a")
        self.assertEqual(local["scope"], bridge.LOCAL_SCOPE)

    def test_identical_components_cancel_even_with_zero_budget(self):
        g = graph({"a": 4, "b": 3, "x": 7, "y": 6}, [("a", "b"), ("x", "y")])
        d = bridge.local_difference(g, set(g.nodes), "a", "b", 0)
        self.assertEqual(d["lower_exact"], "1")
        self.assertEqual(d["upper_exact"], "1")
        self.assertEqual(d["cancelled_components"], [["x", "y"]])
        self.assertEqual(d["recurrence_states"], 0)


class ReleaseAndScoreTests(unittest.TestCase):
    def test_same_snapshot_scores_separate_full_and_local_targets(self):
        g = graph({"a": 8, "b": 7, "x": 10, "y": 3}, [("a", "b"), ("a", "x"), ("b", "y")])
        c, r = fixture(g, ["b", "x"], ["b", "x"], ["a", "b", "y", "x"])
        state = bridge.select_patch(c, r, config())
        state["patch"] = ["a", "b", "y"]
        local = bridge.local_difference(g, set(state["patch"]), "a", "b")
        refs = [{"a": "a", "b": "b", "preferred": "b", "scope": bridge.FULL_SCOPE}]
        entry = {"id": "p", "role": "witness_joint", "priority": "program",
                 "program": FeatureRuleProgram("w", [], "weight").to_dict()}
        out = bridge.score_patch(state, entry, config(), refs, [local])
        self.assertEqual(out["local_fit"]["passed"], 1)
        self.assertEqual(out["full_target_fit"]["passed"], 0)
        self.assertEqual(out["scores"]["a"], "8")
        self.assertNotIn("x", out["scores"])

    def test_nulls_duplicates_and_work_caps_are_explicit(self):
        entries = bridge.validate_program_inventory(bank(), config())
        self.assertEqual(len(entries), 19)
        self.assertIsNone(next(e for e in entries if e["role"] == "fixed_base")["program"])
        bad = bank(); bad["entries"] = bad["entries"][1:]
        with self.assertRaises(ValueError): bridge.validate_program_inventory(bad, config())
        g = graph({"a": 2, "b": 1}, [("a", "b")])
        c, r = fixture(g, ["a"], ["a"], ["a", "b"])
        state = bridge.select_patch(c, r, config())
        small = config(); small["max_score_feature_work"] = 0
        out = bridge.score_patch(state, entries[0], small, [], [])
        self.assertEqual(out["status"], "score_work_cap")
        self.assertIsNone(out["scores"])
        self.assertIsNone(out["local_fit"])

    def test_metadata_prepare_and_released_tiny_run(self):
        g = graph({"a": 2, "b": 1, "c": 1}, [("a", "b")])
        c, r = fixture(g, ["a", "c"], ["a"], ["a", "b"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); archive = root / "feedback.tar.gz"
            raw = {"training_contexts.json": json.dumps({"contexts": [c]}).encode(),
                   "results.jsonl": (json.dumps(r) + "\n").encode()}
            raw["protocol.json"] = json.dumps({"split": "train", "priority": "degree"}).encode()
            raw["freeze_receipt.json"] = json.dumps({"before_any_feedback_execution": True,
                "training_contexts_sha256": bridge.sha256(raw["training_contexts.json"]).hexdigest(),
                "protocol_sha256": bridge.sha256(raw["protocol.json"]).hexdigest()}).encode()
            with tarfile.open(archive, "w:gz") as t:
                for name, value in raw.items():
                    info = tarfile.TarInfo("tiny/" + name); info.size = len(value)
                    t.addfile(info, io.BytesIO(value))
            cfg = config(); cfg["feedback_archive_sha256"] = bridge.digest(archive)
            cfgfile = root / "config.json"; bridge.write(cfgfile, cfg)
            evidence = root / "training.json"
            bridge.write(evidence, {"records": [{"id": c["id"], "split": "train", "graph": g.to_dict(), "fixed": [], "excluded": []}],
                "labels": [{"id": c["id"], "split": "train", "graph_digest": g.digest(), "rows": [{"a": "a", "b": "b", "difference": {
                    "status": "strict", "preferred": "a", "lower_exact": "1", "upper_exact": "1"}}]}]})
            registration = root / "registration"
            with patch.object(bridge, "local_difference", side_effect=AssertionError("No new certificate in prepare")), \
                 patch.object(bridge, "score_patch", side_effect=AssertionError("No score in prepare")):
                prepared = bridge.prepare(archive, cfgfile, evidence, registration)
            self.assertEqual(prepared["new_certificates"], 0)
            self.assertEqual(prepared["program_scores"], 0)
            programs = root / "programs.json"; bridge.write(programs, bank())
            release = root / "release.json"; bridge.write(release, {})
            with self.assertRaises(ValueError):
                bridge.run(registration, programs, release, bridge.digest(release), root / "unauthorized")
            self.assertFalse((root / "unauthorized").exists())
            bridge.write(release, {"bridge_execution_authorized": True, "program_release_complete": True,
                "before_any_bridge_certificate_or_program_score": True, "selection_split": "train",
                "no_bridge_authoring_or_selection_feedback": True,
                "bridge_freeze_sha256": bridge.digest(registration / "freeze_receipt.json"),
                "program_inventory_sha256": bridge.digest(programs), "runtime_source_sha256": bridge.sources()})
            result = bridge.run(registration, programs, release, bridge.digest(release), root / "tiny_run")
            self.assertEqual(result["states"], 1)
            self.assertEqual(result["strict_full_local_agreement"], 1)
            summary = bridge.read(root / "tiny_run" / "summary.json")
            self.assertEqual(len(summary), 19)
            self.assertTrue(any(x["missing_program"] for x in summary))
            prefixes = bridge.read(root / "tiny_run" / "prefixes.json")
            self.assertEqual(len(prefixes), 19)
            with self.assertRaises(ValueError):
                bridge.run(registration, programs, release, bridge.digest(release), root / "tiny_run")


if __name__ == "__main__":
    unittest.main()
