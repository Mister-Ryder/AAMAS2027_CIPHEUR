import copy
from contextlib import redirect_stdout
from hashlib import sha256
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from cipheur import heap_study_v04 as study
from tests.test_compiled_v03 import graph


class HeapStudyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).parents[1]/"configs/heap_extension_v04.json").read_bytes())
        bank = json.loads((Path(__file__).parent/"fixtures/score_heap_training_bank_v04.json").read_bytes())
        by_name = {r["program"]["name"]:r["program"] for r in bank}
        self.programs = {"primary":by_name["v04_upper_ratio"],"degree":by_name["degree"]}

    def context(self, g, fixed=(), excluded=()):
        return {"id":"fixture:graph","pair_id":"fixture","side":"graph","split":"public",
                "family":"test_fixture","cluster":"fixture","graph":g.to_dict(),
                "fixed":list(fixed),"excluded":list(excluded)}

    def test_empty_and_overlapping_boundary_preserve_exact_pairs(self):
        fixtures = [(graph([],[]),[],[]),
                    (graph([0,.1,.2,9,8],[(0,1),(1,2),(2,3),(3,4)]),["0"],["2"])]
        for g,f,x in fixtures:
            result = study.process_context((self.context(g,f,x),0,self.programs,self.config,{}))
            self.assertEqual(len(result["runs"]),12)
            self.assertEqual(len(result["paired"]),6)
            self.assertTrue(all(p["both_completed"] and p["exact_trace_selection_value_parity"] for p in result["paired"]))
            self.assertTrue(all(r["completed"] and not r["fallback_used"] for r in result["runs"]))
            for row in result["runs"]:
                self.assertTrue(set(f) <= set(row["selected"]))
                self.assertFalse(set(x)&set(row["selected"]))
                self.assertEqual(row["program_sha256"],study.digest(self.programs[row["arm"]]))

    def test_cpu_failure_has_no_partial_schedule_or_fallback(self):
        g = graph([1]*100,[(i,i+1) for i in range(99)])
        for backend in self.config["backends"]:
            clock = itertools.chain([0,0],itertools.repeat(2))
            with patch("cipheur.heap_study_v04.time.process_time",side_effect=clock):
                row = study.execute_backend(g,self.programs["degree"],backend,[],[],1)
            self.assertFalse(row["completed"])
            self.assertEqual(row["status"],"CPU_budget_exceeded")
            for key in ("selected","trace","value","value_exact","feature_work","score_evaluations"):
                self.assertIsNone(row[key])
            self.assertFalse(row["fallback_used"])

    def test_asymmetric_failure_retained_without_parity_or_ratio(self):
        original = study.execute_backend
        def execute(g,p,b,f,x,s):
            if b == "full_scan": return original(g,p,b,f,x,s)
            with patch("cipheur.heap_study_v04.schedule_heap",side_effect=study.CPUExceeded("fixture target")):
                return original(g,p,b,f,x,s)
        with patch("cipheur.heap_study_v04.execute_backend",side_effect=execute):
            result = study.process_context((self.context(graph([1,2],[(0,1)])),0,self.programs,self.config,{}))
        self.assertEqual(sum(r["completed"] for r in result["runs"]),6)
        for pair in result["paired"]:
            self.assertFalse(pair["both_completed"])
            self.assertIsNone(pair["exact_trace_selection_value_parity"])
            self.assertIsNone(pair["full_over_heap_cpu"])
            self.assertIsNone(pair["full_over_heap_work"])
            self.assertEqual(pair["failed_backends"],["heap"])

    def test_order_balance_in_both_declared_populations(self):
        for contexts in (8,456):
            for arm in range(2):
                first = [study.backend_order(c,r,arm)[0] for c in range(contexts) for r in range(3)]
                self.assertEqual(first.count("heap"),first.count("full_scan"))
            for rep in range(3):
                self.assertEqual(sum((c+rep)%2 == 0 for c in range(contexts)),contexts//2)

    def test_budget_protocols_are_explicit_and_do_not_replace_original(self):
        self.assertEqual(study.validate_config(self.config)["program_cpu_seconds"], 5)
        longer = {**self.config, "version":"fixed_ast_heap_execution_extension_v04_30s",
                  "program_cpu_seconds":30}
        self.assertEqual(study.validate_config(longer)["program_cpu_seconds"], 30)
        for cfg in ({**self.config,"program_cpu_seconds":30},
                    {**longer,"program_cpu_seconds":5},
                    {**longer,"program_cpu_seconds":60}):
            with self.assertRaises(ValueError): study.validate_config(cfg)

    def test_identity_boundary_source_and_selection_guards(self):
        c = self.context(graph([1,2],[(0,1)]))
        record = {"id":"fixture","family":"test_fixture","graph":c["graph"]}
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            study.normalise_contexts({"public":[record,record]})
        with self.assertRaises(ValueError):
            study.normalise_contexts({"public":[{**record,"fixed":["0","1"]}]})
        with self.assertRaisesRegex(ValueError,"source changed"):
            study.process_context((c,0,self.programs,self.config,{"score_heap_v04.py":"0"*64}))
        for key,value in (("selection_permitted",True),("repetitions",1),("score_slice",False)):
            altered = {**self.config,key:value}
            with self.assertRaises(ValueError): study.validate_config(altered)
        _, contexts = study.normalise_contexts({"test":[{"id":"pair","family":"test_fixture",
            "left":c["graph"],"right":c["graph"],"source":{"seed":7}}],"validation":[]})
        self.assertEqual([r["id"] for r in contexts],["pair:left","pair:right"])
        self.assertEqual([r["cluster"] for r in contexts],["7","7"])

    def test_real_process_pool_smoke_and_byte_receipts(self):
        # Synthetic fixtures validate the harness; no fresh/SNAP experiment is run.
        public = []
        for i in range(8):
            g = graph([],[]) if i == 0 else graph([0,.1,2,1],[(0,1),(1,2)])
            public.append({"id":"smoke"+str(i),"family":"test_fixture","graph":g.to_dict(),
                           "fixed":["0"] if i == 1 else [],"excluded":["2"] if i == 1 else []})
        frozen = {"test_accessed":False,"selection_split":"train","candidate_bank_sha256":"0"*64,
                  "programs":{"guided_v04":self.programs["primary"],"baseline":self.programs["degree"]}}
        data = json.dumps({"public":public}).encode()
        freeze = json.dumps(frozen).encode()
        config = copy.deepcopy(self.config)
        config["input_sha256"]["public"] = sha256(data).hexdigest()
        config["train_freeze_sha256"] = sha256(freeze).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/"data.json").write_bytes(data); (root/"freeze.json").write_bytes(freeze)
            (root/"config.json").write_text(json.dumps(config),encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                result = study.run(root/"data.json",root/"freeze.json",root/"config.json",root/"out",workers=2)
            self.assertEqual(result,{"contexts":8,"runs":96,"parity_failures":0})
            complete = json.loads((root/"out/complete.json").read_bytes())
            receipt = json.loads((root/"out/execution.json").read_bytes())
            raw_results = (root/"out/results.jsonl").read_bytes()
            self.assertEqual(complete["results_sha256"],sha256(raw_results).hexdigest())
            self.assertTrue(complete["all_completed_pairs_match"])
            self.assertEqual(len(raw_results.splitlines()),8)
            self.assertEqual(complete["method_counts"],{a+"/"+b+"/completed":24 for a in self.programs for b in config["backends"]})
            self.assertEqual(receipt["input_sha256"],sha256(data).hexdigest())
            self.assertEqual(receipt["train_freeze_sha256"],sha256(freeze).hexdigest())
            self.assertEqual(receipt["program_sha256"],config["program_sha256"])
            self.assertFalse(receipt["selection_permitted"])
            self.assertFalse(receipt["original_confirmatory_runner_modified"])
            with zipfile.ZipFile(root/"out/source_snapshot.zip") as archive:
                self.assertEqual(archive.read("frozen_programs.json"),freeze)
                for name,expected in receipt["source_sha256"].items():
                    self.assertEqual(sha256(archive.read("cipheur/"+name)).hexdigest(),expected)
            with self.assertRaises(FileExistsError):
                study.run(root/"data.json",root/"freeze.json",root/"config.json",root/"out")
            altered = copy.deepcopy(config); altered["program_sha256"]["primary"] = "0"*64
            (root/"config.json").write_text(json.dumps(altered),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Executed AST"):
                study.run(root/"data.json",root/"freeze.json",root/"config.json",root/"bad")
            self.assertFalse((root/"bad").exists())


if __name__ == "__main__": unittest.main()
