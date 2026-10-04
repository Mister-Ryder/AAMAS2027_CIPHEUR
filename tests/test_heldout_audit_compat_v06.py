"""Fabricated syntax mutation checks; no genuine TEST evidence access."""
import ast, unittest
from pathlib import Path
from scripts.verify_heldout_audit_compat_v06 import compare_function_syntax

ROOT=Path(__file__).resolve().parents[1]
class AuditIdentityCompatibility(unittest.TestCase):
    def setUp(self):
        self.old=(ROOT/'cipheur/heldout_refinement_v06.py').read_text(encoding='utf-8')
        self.new=(ROOT/'scripts/prepare_heldout_r2_audit_compat_v06.py').read_text(encoding='utf-8')
    def test_only_declared_metadata_changes(self):
        self.assertEqual(compare_function_syntax(self.old,self.new),{'name':1,'packet_identity':1,'source_snapshot_path':1})
    def test_winner_gate_mutation_rejected(self):
        with self.assertRaises(ValueError): compare_function_syntax(self.old,self.new.replace('len(entries) != 27','len(entries) != 26'))
    def test_certificate_root_binding_mutation_rejected(self):
        with self.assertRaises(ValueError): compare_function_syntax(self.old,self.new.replace('cert_complete["programme_freeze_sha256"] != root_release_sha256','False'))
    def test_worker_budget_mutation_rejected(self):
        with self.assertRaises(ValueError): compare_function_syntax(self.old,self.new.replace('workers != 8','workers != 4'))
    def test_undeclared_audit_bypass_rejected(self):
        with self.assertRaises(ValueError): compare_function_syntax(self.old,self.new.replace('_audit_passed(_read(path), name)','pass'))
    def test_missing_identity_comparison_rejected(self):
        with self.assertRaises(ValueError): compare_function_syntax(self.old,self.new.replace('runtime.get("independent_packet_audit_sha256") != EXPECTED_ORIGINAL_PACKET_AUDIT_SHA256','False'))

if __name__=='__main__':unittest.main()
