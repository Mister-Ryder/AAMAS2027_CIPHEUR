"""Role-boundary checks: a failed information gate cannot become the method."""
import unittest
from cipheur.refinement_study_v06 import deployment_selection


def candidate(block, arm, slot, joint, quality="1/2", work="20", fit=10):
    return {"id": f"block_{block}_{arm}:{slot}", "block": block, "arm": arm,
        "slot": slot, "program": {"name": "same_AST"}, "program_sha256": "a" * 64,
        "eligible": joint, "assessment_status": "assessed", "interface": {"strict_passed": fit},
        "kernel_summary": {"macro_quality_exact": quality, "macro_work_exact": work},
        "kernel_rows": [{"result": {"completed": True, "feasible": True}} for _ in range(120)]}


class RefinedDeploymentRoles(unittest.TestCase):
    def test_failed_baseline_gate_does_not_block_or_impersonate_genuine_method(self):
        rows = [candidate(b, a, 0, a == "witness") for b in range(4)
                for a in ("witness", "relations", "objective")]
        # A much better reward and fit cannot launder an inadequate W interface.
        rows.append(candidate(0, "witness", 1, False, quality="3/4", work="1", fit=100))
        out = deployment_selection(rows, [0, 1, 2, 3])
        self.assertTrue(out["ready_for_TEST"])
        joint = [p for p in out["programs"] if p["role"] == "proposed_witness_joint"]
        self.assertEqual(len(joint), 4)
        self.assertTrue(all(p["eligible"] and p["slot"] == 0 for p in joint))
        nonguarded = next(p for p in out["programs"] if p["id"] == "quality|block_0_witness:1")
        self.assertFalse(nonguarded["eligible"])
        self.assertFalse(nonguarded["joint_gate_required"])
        self.assertEqual(out["quality_comparator_requested_count"], 12)

    def test_missing_genuine_witness_cannot_be_filled_by_any_quality_program(self):
        rows = [candidate(b, a, 0, b != 2 and a == "witness") for b in range(4)
                for a in ("witness", "relations", "objective")]
        out = deployment_selection(rows, [0, 1, 2, 3])
        self.assertFalse(out["ready_for_TEST"])
        self.assertEqual(out["proposed_witness_joint_count"], 3)
        self.assertTrue(out["R1_barrier_remains_failed"])

    def test_missing_comparator_stays_null_and_duplicates_keep_their_identities(self):
        rows = [candidate(b, "witness", 0, True) for b in range(4)]
        out = deployment_selection(rows, [0, 1, 2, 3])
        self.assertTrue(out["ready_for_TEST"])
        self.assertEqual(len(out["quality_comparator_missing_cells"]), 8)
        missing = [p for p in out["programs"] if p.get("missing_baseline")]
        self.assertEqual(len(missing), 8)
        self.assertTrue(all(p["program"] is None and p["source_candidate_id"] is None for p in missing))
        retained = [p for p in out["programs"] if p["program"] is not None]
        self.assertEqual(len(retained), 8)  # Four joint + four quality identities; same AST is not deduplicated.
        self.assertEqual(len({p["id"] for p in out["programs"]}), 16)


if __name__ == "__main__":
    unittest.main()
