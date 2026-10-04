"""Only fabricated tiny graphs; no frozen V06 TEST data or outcomes are read."""
from copy import deepcopy
from fractions import Fraction
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from cipheur.graph_features import FeatureRuleProgram
from cipheur.heldout_mechanism_v06 import (
    ARMS, DEFAULT_INTERFACE_LIMITS, REPAIR_CONFIG, cluster_mappings, control_entries,
    evaluate_entry, heldout_interface_assessment, paired_checks, relabel_inventory,
    prepare, run, source_hashes, validate_selected, validate_test_labels,
)
from cipheur.model import Contact, Graph
from cipheur.synthesis_study_v06 import canonical, digest, write


def program(rule="ne"):
    return FeatureRuleProgram("tiny", [{"name": "ne", "expression": {
        "op": "count", "args": [{"op": "induced_edges", "args": [
            {"op": "neighbors", "args": [{"op": "root", "args": []}]}]}]}}],
        rule, "Fabricated unit-test program").to_dict()


def tiny_pair(numeric=False):
    ids = tuple(str(i) for i in range(8)) if numeric else tuple("abcdefpx")
    a, b, c, d, e, f, fixed, excluded = ids
    contacts = tuple(Contact(v, 1, "s" + v, "g" + v, 0, 1) for v in ids)
    shared = {(a, b), (a, c), (a, d), (b, e), (b, f)}
    graphs = [Graph("tiny_left", contacts, frozenset(shared | {(c, d)}), {"station_gap": 0}),
              Graph("tiny_right", contacts, frozenset(shared | {(e, f)}), {"station_gap": 1})]
    records, labels = [], []
    for side, graph, pref, delta in zip(("left", "right"), graphs, (a, b), ("1", "-1")):
        query = {"a": a, "b": b, "kind": "alias", "base_alias_by_side": [True, True]}
        quota = {"alias": {"eligible": 1, "planned": 1, "shortfall": 7},
                 "control": {"eligible": 0, "planned": 0, "shortfall": 8}}
        record = {"id": "fixture:" + side, "split": "test", "family": "tiny", "cluster": "fixture",
                  "paired": True, "pair": "fixture", "side": side, "graph": graph.to_dict(),
                  "graph_digest": graph.digest(), "fixed": [fixed], "excluded": [excluded],
                  "queries": [deepcopy(query)], "quota": deepcopy(quota)}
        # These values are immediately evident from the six-vertex graph:
        # forcing a leaves e/f; forcing b leaves c/d. No oracle is executed.
        unmatched = {}
        for role, vertices, chosen in (("a", [e, f], [e, f] if side == "left" else [e]),
                                       ("b", [c, d], [c] if side == "left" else [c, d])):
            val = str(len(chosen))
            unmatched[role] = [{"vertices": vertices, "bound": {"lower_exact": val,
                "upper_exact": val, "selected": chosen, "exact": True, "expanded": 0}}]
        difference = {"a": a, "b": b, "preferred": pref, "status": "strict", "exact": True,
                      "lower_exact": delta, "upper_exact": delta, "lower": float(delta), "upper": float(delta),
                      "forced_weight_difference_exact": "0", "cancelled_components": [], "unmatched": unmatched}
        records.append(record)
        labels.append({"id": record["id"], "split": "test", "family": "tiny", "cluster": "fixture",
                       "graph_digest": graph.digest(), "quota": deepcopy(quota),
                       "rows": [{**query, "difference": difference}]})
    return records, labels


class HeldoutInterfaceTests(unittest.TestCase):
    def test_unused_feature_does_not_repair_demanded_alias(self):
        records, labels = tiny_pair()
        unused = heldout_interface_assessment(program("weight"), records, labels)
        self.assertTrue(unused["quotient"]["contradictory"])
        self.assertFalse(unused["declared_quotient"]["contradictory"])
        self.assertEqual(unused["demanded_features"], [])
        self.assertEqual((unused["strict_passed"], unused["strict_total"]), (0, 2))
        used = heldout_interface_assessment(program("ne"), records, labels)
        self.assertFalse(used["quotient"]["contradictory"])
        self.assertEqual(used["demanded_features"], ["ne"])
        self.assertEqual((used["strict_passed"], used["strict_total"]), (2, 2))
        self.assertEqual(used["alias_strict_total"], 2)
        self.assertEqual(paired_checks(used)[0]["category"], "strict_reversal")
        self.assertTrue(paired_checks(used)[0]["pair_passed"])
        self.assertFalse(used["selection_performed"])
        self.assertTrue(all(r["split"] == "test" for r in records))

    def test_five_bijections_preserve_paired_inputs_boundaries_and_intervals(self):
        records, labels = tiny_pair(numeric=True)
        original = deepcopy((records, labels))
        seen = set()
        for index in range(5):
            remapped, mapped_labels, mappings = relabel_inventory(records, labels, index, "tiny_fixture_salt")
            mapping = mappings["fixture"]
            seen.add(tuple(sorted(mapping.items())))
            self.assertEqual(set(mapping), set("01234567"))
            self.assertEqual(len(set(mapping.values())), 8)
            self.assertEqual(remapped[0]["graph"]["contacts"], remapped[1]["graph"]["contacts"])
            self.assertEqual(remapped[0]["fixed"], [mapping["6"]])
            self.assertEqual(remapped[1]["excluded"], [mapping["7"]])
            self.assertEqual(mapped_labels[0]["rows"][0]["difference"]["lower_exact"], "1")
            self.assertEqual(mapped_labels[1]["rows"][0]["difference"]["upper_exact"], "-1")
            self.assertEqual(mapped_labels[0]["rows"][0]["difference"]["preferred"], mapping["0"])
            left = Graph.from_dict(remapped[0]["graph"])
            self.assertTrue(left.feasible([mapping[v] for v in ("0", "4", "5", "6")]))
            score = heldout_interface_assessment(program(), remapped, mapped_labels)
            self.assertEqual(score["strict_passed"], 2)
            self.assertTrue(paired_checks(score)[0]["pair_passed"])
        self.assertEqual(len(seen), 5)
        self.assertEqual((records, labels), original)
        self.assertEqual(cluster_mappings(records, 2, "tiny_fixture_salt"),
                         cluster_mappings(records, 2, "tiny_fixture_salt"))

    def test_ties_unknowns_and_shortfalls_remain_outside_strict_fit(self):
        records, labels = tiny_pair()
        records, labels = records[:1], labels[:1]
        records[0].update(paired=False); records[0].pop("pair"); records[0].pop("side")
        baseline = heldout_interface_assessment(program(), records, labels)
        tie = deepcopy(records[0]["queries"][0]); tie.update(a="c", b="d", base_alias_by_side=[True])
        unknown = deepcopy(records[0]["queries"][0])
        records[0]["queries"].extend((tie, unknown))
        labels[0]["rows"].extend(({
            **tie, "difference": {"a": "c", "b": "d", "preferred": None, "status": "exact_tie",
                "exact": True, "lower_exact": "0", "upper_exact": "0"}}, {
            **unknown, "difference": {"a": "a", "b": "b", "preferred": None, "status": "unknown",
                "exact": False, "lower_exact": "-1", "upper_exact": "1"}}))
        for data in (records[0], labels[0]):
            data["quota"]["alias"].update(planned=3, shortfall=5)
        result = heldout_interface_assessment(program(), records, labels)
        self.assertEqual(result["certificate_status"], {"strict": 1, "exact_tie": 1, "unknown": 1})
        self.assertEqual(result["strict_total"], 1)
        self.assertEqual(result["quota_shortfalls"], 13)
        self.assertIsNone(result["query_checks"][1]["passed"])
        self.assertIsNone(result["query_checks"][2]["passed"])
        self.assertEqual(result["interface_feature_work"], baseline["interface_feature_work"])

    def test_split_and_certificate_binding_fail_instead_of_train_relabel(self):
        records, labels = tiny_pair()
        records[0]["split"] = "train"
        with self.assertRaisesRegex(ValueError, "TEST"):
            heldout_interface_assessment(program(), records, labels)
        records, labels = tiny_pair()
        labels[0]["rows"][0]["difference"]["preferred"] = "b"
        with self.assertRaisesRegex(ValueError, "signed interval"):
            validate_test_labels(records, labels)
        records, labels = tiny_pair()
        labels[0]["rows"] = []
        with self.assertRaisesRegex(ValueError, "binding"):
            validate_test_labels(records, labels)

    def test_tiny_kernel_keeps_both_assigned_states_and_correct_reward(self):
        records, labels = tiny_pair()
        entry = {"id": "unit_only", "program": program(), "priority": "program"}
        protocol = {"source_sha256": source_hashes(), "interface_limits": DEFAULT_INTERFACE_LIMITS,
                    "kernel_config": {"seconds": .5, "clock": "wall", "repair_config": REPAIR_CONFIG}}
        result = evaluate_entry((entry, records, labels, protocol, "original"))
        self.assertEqual(result["extra_oracle_calls"], 0)
        self.assertEqual(result["kernel_coverage"]["verified_incumbents"], 2)
        for row in result["kernel_rows"]:
            self.assertTrue(row["result"]["completed"])
            self.assertTrue(row["result"]["feasible"])
            self.assertEqual(Fraction(row["result"]["value_exact"]), 4)
            self.assertGreaterEqual(row["result"]["meter"]["repair_work"], 0)


class HeldoutFreezeTests(unittest.TestCase):
    def test_genuine_whole_transport_blocks_required(self):
        p = program()
        programs = [{"id": f"block_{b}_{a}:0", "block": b, "arm": a, "slot": 0,
                     "program": p, "program_sha256": canonical(p)} for b in (1, 2, 3, 4) for a in ARMS]
        selection = {"selection_split": "train", "test_accessed": False,
            "all_cells_have_genuine_winner": True, "all120_original_slots_assessed": True, "no_fallback": True,
            "matched_transport_complete_blocks": [1, 2, 3, 4], "programs": programs}
        self.assertEqual(len(validate_selected(selection)), 12)
        for key, value in (("all_cells_have_genuine_winner", False), ("test_accessed", True),
                           ("matched_transport_complete_blocks", [1, 2, 3]), ("no_fallback", False)):
            invalid = {**selection, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_selected(invalid)

    def test_every_requested_control_identity_retained_including_duplicate_ast(self):
        p = program()
        bank = {"banks": {"enumerated_structural": [p] * 8, "fixed_base9": [p] * 8},
                "degree_fixed_reference": FeatureRuleProgram("degree", [], "weight/max(1,degree)").to_dict()}
        selection = {"selection_split": "train", "test_accessed": False,
            "all64_original_slots_assessed": True, "no_fallback": True,
            "selections": [{"block": 0, "bank": group, "quality_only_baseline": {
                "id": group + "_winner", "slot": 2, "program": p, "program_sha256": canonical(p),
                "eligible": False}} for group in ("enumerated_structural", "fixed_base9")]}
        entries = control_entries(selection, bank)
        self.assertEqual(len(entries), 11)
        self.assertEqual(len({e["id"] for e in entries}), 11)
        self.assertEqual(sum(e["main_comparison"] for e in entries), 3)
        self.assertTrue(entries[0]["joint_gate_not_required"])

    def test_research_run_is_linux_only_and_never_overwrites(self):
        with patch("cipheur.heldout_mechanism_v06.platform.system", return_value="Windows"):
            with self.assertRaisesRegex(ValueError, "Linux-only"):
                run("missing", "missing")
        with tempfile.TemporaryDirectory() as directory:
            with patch("cipheur.heldout_mechanism_v06.platform.system", return_value="Linux"):
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    run("missing", Path(directory))

    def test_fabricated_prepare_freezes_every_assignment_and_refuses_tampering(self):
        # Exactly 72 fabricated eight-vertex states exercise the preparation
        # frame count. No scorer, repair, oracle or real TEST file is executed.
        import cipheur.heldout_mechanism_v06 as runner
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            plan, certificates, controls_registration = (base / n for n in ("plan", "certs", "controls"))
            records, labels = [], []
            for i in range(36):
                rs, ls = tiny_pair()
                for r, l in zip(rs, ls):
                    r["id"] = l["id"] = f"tiny_only_{i}:{r['side']}"
                    r["cluster"] = l["cluster"] = r["pair"] = f"tiny_only_{i}"
                records.extend(rs); labels.extend(ls)
            write(plan / "data.json", {"records": records})
            write(plan / "protocol.json", {"only_fabricated_unit_fixtures": True})
            write(plan / "freeze_receipt.json", {"data_sha256": digest(plan / "data.json"),
                "protocol_sha256": digest(plan / "protocol.json"), "before_any_oracle_query": True,
                "source_sha256": {"fabricated_source": "unit_only"}})
            kernel = {"seconds": .5, "clock": "wall", "repair_config": REPAIR_CONFIG}
            author = {"kernel_config": kernel, "interface_limits": DEFAULT_INTERFACE_LIMITS,
                "source_sha256": {k: digest(Path(runner.__file__).parent / n) for k, n in (
                    ("assessment", "synthesis_study_v06.py"), ("kernel", "repair_v06.py"),
                    ("typed_library", "graph_features.py"), ("compiled_runtime", "compiled.py"))}}
            write(base / "author.json", author); write(base / "kernel.json", kernel)
            raw = program()
            selection = {"selection_split": "train", "test_accessed": False,
                "all_cells_have_genuine_winner": True, "all120_original_slots_assessed": True,
                "no_fallback": True, "matched_transport_complete_blocks": [1, 2, 3, 4],
                "parent_protocol_sha256": digest(base / "author.json"),
                "programs": [{"id": f"block_{b}_{a}:0", "block": b, "arm": a, "slot": 0,
                              "program": raw, "program_sha256": canonical(raw)}
                             for b in (1, 2, 3, 4) for a in ARMS]}
            write(base / "selection.json", selection)
            bank = {"banks": {"enumerated_structural": [raw] * 8, "fixed_base9": [raw] * 8},
                    "degree_fixed_reference": FeatureRuleProgram("degree", [], "weight/max(1,degree)").to_dict()}
            write(base / "bank.json", bank)
            write(base / "bank_freeze.json", {"control_banks_sha256": digest(base / "bank.json")})
            write(controls_registration / "protocol.json", {"control_bank_sha256": digest(base / "bank.json"),
                "kernel_config": kernel, "interface_limits": DEFAULT_INTERFACE_LIMITS})
            write(controls_registration / "freeze_receipt.json", {
                "protocol_sha256": digest(controls_registration / "protocol.json")})
            write(base / "controls_selection.json", {"selection_split": "train", "test_accessed": False,
                "all64_original_slots_assessed": True, "no_fallback": True,
                "registration_sha256": digest(controls_registration / "protocol.json"),
                "selections": [{"block": 0, "bank": group, "quality_only_baseline": {
                    "id": group + "_tiny", "slot": 0, "program": raw, "program_sha256": canonical(raw)}}
                    for group in ("enumerated_structural", "fixed_base9")]})
            certificates.mkdir()
            (certificates / "results.jsonl").write_text("".join(
                __import__("json").dumps(l) + "\n" for l in labels), encoding="utf-8")
            for name in ("data.json", "protocol.json"):
                (certificates / name).write_bytes((plan / name).read_bytes())
            selected_hash = digest(base / "selection.json")
            label_hash = digest(certificates / "results.jsonl")
            write(certificates / "execution.json", {"split": "test", "programme_freeze_sha256": selected_hash,
                                                   "source_sha256": {"fabricated_source": "unit_only"}})
            write(certificates / "complete.json", {"execution_complete": True, "split": "test", "states": 72,
                "results_sha256": label_hash, "programme_freeze_sha256": selected_hash})
            write(base / "relabel.json", {"registered_before_any_TEST_programme_evaluation": True,
                "permutations_per_source": 5, "version": "v06_pre_TEST_relabel_robustness_001", "salt": "tiny"})
            kwargs = dict(plan=plan, selection=base / "selection.json", selection_sha256=selected_hash,
                controls_selection=base / "controls_selection.json",
                controls_selection_sha256=digest(base / "controls_selection.json"), certificates=certificates,
                test_certificate_sha256=label_hash, authoring_protocol=base / "author.json",
                controls_registration=controls_registration, control_bank=base / "bank.json",
                control_freeze=base / "bank_freeze.json", relabel_config=base / "relabel.json",
                kernel_config=base / "kernel.json", out=base / "registration", workers=1)
            with patch.object(runner.platform, "system", return_value="Linux"), \
                 patch.object(runner, "repair_schedule", side_effect=AssertionError("Preparation must not score")):
                response = prepare(**kwargs)
                self.assertEqual(response["TEST_programme_evaluations"], 0)
                self.assertEqual(response["assigned_identities"], 23)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    prepare(**kwargs)
                (base / "registration/test_inputs.json").write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "changed"):
                    run(base / "registration", base / "must_not_execute")
            self.assertFalse((base / "must_not_execute").exists())


if __name__ == "__main__":
    unittest.main()
