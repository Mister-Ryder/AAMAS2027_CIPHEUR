"""V003 additive roles/counts and shared-cost contracts; no research solver calls."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
runner=load("v003_mock_runner","scripts/run_performance_r2_eoh_test_v06.py")
oldtests=load("v002_mock_fixtures","tests/test_performance_r2_runner_v06.py")
from cipheur.model import Contact,Graph

def fixtures():
    selected,controls,audit=oldtests.fixtures()
    program={"name":"manual_mock","features":[],"rule":"weight","rationale":"Mock contract only"}
    published={"version":"v06_published_EoH_DSL_TRAIN_quality_selection_001","requested_positions":32,
        "all32_positions_frozen":True,"TEST_accessed":False,"future_performance_registration_required":True,
        "no_retry_or_fallback_authored_output":True,
        "original_positions":[{"run":r,"slot":s} for r in range(4) for s in range(8)],"programs":[]}
    for r in range(4):
        published["programs"].append({"id":f"published_EoH_DSL_quality:run_{r}","run":r,
            "role":"nonguarded_published_quality_baseline","joint_gate_required":False,"program":program,
            "program_sha256":runner.canonical(program),"source_id":f"run_{r}:warm_seed",
            "winner_origin":"shared_R1_warm_seed","TRAIN_label_selected_seed_history":True,
            "gate_fit_not_used_for_selection":True})
    aa={"errors":0,"selection_sha256":"mock_published","audit_phase":"authoring","TEST_accessed":False}
    ta={**aa,"audit_phase":"train"}
    return selected,controls,audit,published,aa,ta

def bind(f):
    s,c,a,p,aa,ta=f
    return runner.deployment_from_selection(s,c,a,"mock_selection","mock_config",p,aa,ta,"mock_published")

class AdditiveBinding(unittest.TestCase):
    def test_four_published_roles_seed_origin_and_duplicates_remain_explicit(self):
        programs,blocks=bind(fixtures())
        self.assertEqual(len(programs),23);self.assertEqual(blocks,[0,1,2,3])
        self.assertEqual(Counter(p["kind"] for p in programs),{"genuine_R2_witness_joint":4,
            "nonguarded_R2_quality_comparator":12,"quality_only_fixed_control":2,
            "shared_classical_priority":1,"nonguarded_published_EoH_DSL_quality":4})
        self.assertTrue(all(p["joint_eligible"] is None and p["winner_origin"]=="shared_R1_warm_seed"
                            for p in programs[-4:]))
        self.assertEqual(runner.digest(ROOT/runner.PRESERVED_R2_RUNNER),runner.PRESERVED_R2_SHA)
        self.assertEqual(runner.digest(ROOT/runner.PRESERVED_R1_RUNNER),runner.PRESERVED_R1_SHA)

    def test_null_published_position_does_not_block_or_replace_joint_role(self):
        f=fixtures();f[3]["programs"][1].update(winner_origin="missing",source_id=None,program=None,program_sha256=None)
        programs,_=bind(f)
        self.assertEqual(len(programs),23);self.assertFalse(programs[-3]["available"])
        f[0]["programs"][0]["eligible"]=False
        with self.assertRaises(AssertionError):bind(f)

    def test_audit_phase_sha_and_origin_are_mandatory(self):
        for idx,field,value in ((4,"errors",1),(4,"audit_phase","train"),(5,"selection_sha256","other"),(5,"TEST_accessed",True)):
            f=fixtures();f[idx][field]=value
            with self.assertRaises(AssertionError):bind(f)
        f=fixtures();f[3]["programs"][0]["winner_origin"]="genuine_EoH_author_slot"
        with self.assertRaises(AssertionError):bind(f)

class AdditiveOrchestration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="v003_mock_");self.out=Path(self.temp.name)
        graph=Graph("mock",(Contact("v1",1,"s1","g1",0,1),Contact("v2",2,"s2","g2",0,1)),frozenset({("v1","v2")}))
        runner.write(self.out/"toy.json",graph.to_dict())
        self.context={"id":"mock","population":"mock","split":"test","n":2,"m":1,"graph_file":"toy.json",
            "graph_file_sha256":runner.digest(self.out/"toy.json"),"graph_sha256":graph.digest(),"source_weight_scale":1,
            "total_source_weight_exact":"3"}
        self.protocol={"wall_targets":[.1,1,5],"native_requests":[m for m in runner.METHODS if m["method"]!="Degree"],
            "repair_config":runner.REPAIR,"executables":{name:{"path":"never_invoked"} for name in ("CHILS","M2WIS","Struction","WeightedBR")}}
        self.deployment={"programs":bind(fixtures())[0]};self.native_calls=[];self.repair_calls=[]

    def tearDown(self):self.temp.cleanup()
    def native(self,graph,exe,name,**kw):
        self.native_calls.append({"name":name,**kw})
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","child_cpu_seconds":.2,"status":"mock"}
    def repair(self,graph,**kw):
        self.repair_calls.append(kw)
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","status":"mock"}
    def execute(self):
        with patch.object(runner,"run_solver",self.native),patch.object(runner,"repair_schedule",self.repair):
            runner.run_context(self.context,self.protocol,self.deployment,self.out)
        return [json.loads(line) for p in (self.out/"context_results").glob("*.jsonl") for line in p.read_text().splitlines()]

    def test_174_assignment_keys_one_shared_initial_per_target_and_cost_charges(self):
        rows=self.execute()
        self.assertEqual(len(rows),174);self.assertEqual(len(self.native_calls),36);self.assertEqual(len(self.repair_calls),138)
        self.assertEqual({runner.key(r) for r in rows},{runner.key(r) for r in runner.expected_rows(self.context,self.protocol,self.deployment)})
        warm=[r for r in rows if r["track"]=="warm_CHILS"]
        self.assertEqual(len(warm),69)
        for row in warm:
            init=next(r["result"] for r in rows if r["track"]=="common_initializer" and r["nominal_wall_target_seconds"]==row["nominal_wall_target_seconds"])
            self.assertEqual(row["shared_initializer_receipt_sha256"],runner.canonical(init))
            self.assertEqual(row["standalone_pipeline_wall_seconds"],init["wrapper_wall_seconds"]+row["policy_wrapper_wall_seconds"])
        published=[r for r in rows if r.get("program_kind")=="nonguarded_published_EoH_DSL_quality"]
        self.assertEqual(len(published),24)
        self.assertTrue(all(r["published_winner_origin"]=="shared_R1_warm_seed" and r["program_role"]=="nonguarded_published_quality_baseline" for r in published))
        config=json.loads((ROOT/runner.ADAPTER_CONFIG).read_bytes())
        self.assertEqual(302*len(rows),config["total_requests"])
        self.assertEqual(302*3*2*4,config["additive_published_EoH_requests"])

    def test_null_published_positions_remain_six_null_requests_not_zero(self):
        self.deployment["programs"][-1].update(available=False,program=None,program_sha256=None,winner_origin="missing",source_candidate_id=None)
        rows=self.execute();null=[r for r in rows if r["method"]=="published_EoH_DSL_quality:run_3"]
        self.assertEqual(len(rows),174);self.assertEqual(len(null),6);self.assertEqual(len(self.repair_calls),132)
        self.assertTrue(all(r["quality_reward_exact_original_objective"] is None and r["result"] is None and r["program_role"]=="nonguarded_published_quality_baseline" for r in null))

if __name__=="__main__":unittest.main()
