"""R2 roles/barriers/shared-cost orchestration contracts; mocked optimization."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("r2_performance_runner",ROOT/"scripts/run_performance_r2_test_v06.py")
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from cipheur.model import Contact,Graph


def fixtures():
    program={"name":"manual_mock","features":[],"rule":"weight","rationale":"Mock contract only"}
    selected={"version":"v06_R2_joint_and_quality_roles_TRAIN_selection_002","selection_split":"train","test_accessed":False,
        "all120_original_slots_assessed":True,"ready_for_TEST":True,"proposed_witness_joint_count":4,
        "quality_comparator_requested_count":12,"selection_plan_sha256":"mock_config","no_fallback":True,
        "R1_barrier_remains_failed":True,"matched_transport_complete_blocks":[0,1,2,3],"programs":[],"quality_comparator_missing_cells":[]}
    for block in range(4):
        selected["programs"].append({"id":f"joint|b{block}w","source_candidate_id":f"b{block}w","block":block,"arm":"witness","slot":0,
            "program":program,"program_sha256":runner.canonical(program),"eligible":True,"role":"proposed_witness_joint","joint_gate_required":True})
        for arm in ("witness","relations","objective"):
            selected["programs"].append({"id":f"quality|b{block}{arm}","source_candidate_id":f"b{block}{arm}","block":block,"arm":arm,"slot":0,
                "program":program,"program_sha256":runner.canonical(program),"eligible":False,"role":"nonguarded_quality_comparator",
                "joint_gate_required":False,"missing_baseline":False})
    controls={"selection_split":"train","test_accessed":False,"all64_original_slots_assessed":True,"selections":[
        {"block":0,"bank":bank,"used_for_performance":True,"quality_only_baseline":{"program":program,"program_sha256":runner.canonical(program),"eligible":False}}
        for bank in ("enumerated_structural","fixed_base9")]}
    audit={"errors":0,"selection_sha256":"mock_selection","ready_for_TEST":True,"proposed_witness_joint_count":4}
    return selected,controls,audit


class R2BindingContract(unittest.TestCase):
    def bind(self,s,c,a):return runner.deployment_from_selection(s,c,a,"mock_selection","mock_config")

    def test_roles_duplicates_and_nonjoint_quality_remain_separate(self):
        programs,blocks=self.bind(*fixtures())
        self.assertEqual(blocks,[0,1,2,3]);self.assertEqual(len(programs),19)
        self.assertEqual(Counter(p["kind"] for p in programs),{"genuine_R2_witness_joint":4,"nonguarded_R2_quality_comparator":12,"quality_only_fixed_control":2,"shared_classical_priority":1})
        self.assertEqual(len({p["program_sha256"] for p in programs if p["program"] is not None}),1)
        self.assertTrue(all(p["joint_eligible"] is False for p in programs if p["kind"]=="nonguarded_R2_quality_comparator"))

    def test_missing_quality_keeps_requested_identity(self):
        s,c,a=fixtures();r=next(r for r in s["programs"] if r["role"]=="nonguarded_quality_comparator" and r["block"]==1 and r["arm"]=="relations")
        r.update(id="quality|block_1_relations:missing",source_candidate_id=None,slot=None,program=None,program_sha256=None,missing_baseline=True)
        s["quality_comparator_missing_cells"]=[{"block":1,"arm":"relations"}]
        programs,_=self.bind(s,c,a);self.assertEqual(len(programs),19)
        self.assertEqual(sum(not p["available"] for p in programs),1)

    def test_missing_or_ineligible_joint_never_replaced_by_quality(self):
        s,c,a=fixtures();s["programs"][0]["eligible"]=False
        with self.assertRaises(AssertionError):self.bind(s,c,a)

    def test_audit_not_ready_or_wrong_selection_is_rejected(self):
        for field,value in (("errors",1),("ready_for_TEST",False),("selection_sha256","other"),("proposed_witness_joint_count",3)):
            s,c,a=fixtures();a[field]=value
            with self.assertRaises(AssertionError):self.bind(s,c,a)

    def test_original_runner_bytes_preserved(self):
        self.assertEqual(runner.digest(ROOT/runner.PRESERVED_R1_RUNNER),runner.PRESERVED_R1_SHA)


class R2OrchestrationContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="v06_r2_orchestration_mock_");self.out=Path(self.temp.name)
        graph=Graph("mock",(Contact("v1",1,"s1","g1",0,1),Contact("v2",2,"s2","g2",0,1)),frozenset({("v1","v2")}))
        runner.write(self.out/"toy.json",graph.to_dict())
        self.context={"id":"mock","population":"mock","split":"test","n":2,"m":1,"graph_file":"toy.json",
            "graph_file_sha256":runner.digest(self.out/"toy.json"),"graph_sha256":graph.digest(),"source_weight_scale":1,"total_source_weight_exact":"3"}
        self.protocol={"wall_targets":[.1,1,5],"native_requests":[r for r in runner.METHODS if r["method"]!="Degree"],
            "repair_config":runner.REPAIR,"executables":{name:{"path":"never_invoked"} for name in ("CHILS","M2WIS","Struction","WeightedBR")}}
        self.deployment={"programs":runner.deployment_from_selection(*fixtures(),"mock_selection","mock_config")[0]}
        self.native_calls=[];self.repair_calls=[]

    def tearDown(self):self.temp.cleanup()

    def native(self,graph,exe,name,**kw):
        self.native_calls.append({"name":name,**kw})
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","seconds":.3,"child_cpu_seconds":.2,"status":"mock"}

    def repair(self,graph,**kw):
        self.repair_calls.append(kw);self.assertEqual(kw["clock"],"wall")
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","status":"mock"}

    def execute(self,native=None,repair=None):
        with patch.object(runner,"run_solver",native or self.native),patch.object(runner,"repair_schedule",repair or self.repair):
            runner.run_context(self.context,self.protocol,self.deployment,self.out)
        return [json.loads(l) for path in (self.out/"context_results").glob("*.jsonl") for l in path.read_text().splitlines()]

    def test_150_exact_keys_and_common_initializer_cost_reuse(self):
        rows=self.execute();self.assertEqual(len(rows),150);self.assertEqual(len({runner.key(r) for r in rows}),150)
        self.assertEqual({runner.key(r) for r in rows},{runner.key(r) for r in runner.expected_rows(self.context,self.protocol,self.deployment)})
        self.assertEqual(len(self.native_calls),36);self.assertEqual(len(self.repair_calls),114)
        self.assertTrue(all(r["successful_assignment"] and r["input_total_weight_fraction_exact"]=="2/3" for r in rows))
        warm=[r for r in rows if r["track"]=="warm_CHILS"];self.assertEqual(len(warm),57)
        for r in warm:
            initial=next(x["result"] for x in rows if x["track"]=="common_initializer" and x["nominal_wall_target_seconds"]==r["nominal_wall_target_seconds"])
            self.assertEqual(r["shared_initializer_receipt_sha256"],runner.canonical(initial))
            self.assertEqual(r["standalone_pipeline_wall_seconds"],initial["wrapper_wall_seconds"]+r["policy_wrapper_wall_seconds"])
            self.assertEqual(r["standalone_pipeline_cpu_seconds"],initial["wrapper_self_cpu_seconds"]+.2+r["policy_wrapper_cpu_seconds"])
        self.assertEqual(Counter(r["program_kind"] for r in warm),{"genuine_R2_witness_joint":12,"nonguarded_R2_quality_comparator":36,"quality_only_fixed_control":6,"shared_classical_priority":3})
        self.assertTrue(all(r["initial"]==["v2"] for r in self.repair_calls if r["initial"] is not None))

    def test_null_quality_never_zero_filled_or_replaced(self):
        p=next(p for p in self.deployment["programs"] if p["kind"]=="nonguarded_R2_quality_comparator")
        p.update(available=False,program=None,program_sha256=None)
        rows=self.execute();missing=[r for r in rows if r["method"]==p["method_id"]]
        self.assertEqual(len(rows),150);self.assertEqual(len(missing),6);self.assertEqual(len(self.repair_calls),108)
        self.assertTrue(all(r["result"] is None and not r["successful_assignment"] and r["quality_reward_exact_original_objective"] is None and r["program_role"]=="nonguarded_quality_comparator" for r in missing))

    def test_native_initial_failure_cannot_invoke_warm_fallback(self):
        def native(graph,exe,name,**kw):
            if kw["seconds"] in (.05,.5,2.5):return {"completed":False,"feasible":None,"selected":None,"status":"mock_failure"}
            return self.native(graph,exe,name,**kw)
        rows=self.execute(native=native);warm=[r for r in rows if r["track"]=="warm_CHILS"]
        self.assertEqual(len(warm),57);self.assertEqual(len(self.repair_calls),57)
        self.assertTrue(all(r["result"] is None and r["runner_error"]["type"]=="NativeInitializerUnavailable" for r in warm))

    def test_decreasing_warm_retained_only_as_failure_diagnostic(self):
        def repair(graph,**kw):
            result=self.repair(graph,**kw)
            if kw["initial"] is not None:result["value_exact"]="0"
            return result
        rows=self.execute(repair=repair);warm=[r for r in rows if r["track"]=="warm_CHILS"]
        self.assertTrue(all(not r["successful_assignment"] and r["quality_reward_exact_original_objective"] is None and r["diagnostic_retained_reward_exact_original_objective"]=="0" for r in warm))

    def test_unexpected_train_context_refused_before_solver(self):
        self.context["split"]="train"
        with self.assertRaises(AssertionError):self.execute()
        self.assertEqual(self.native_calls,[]);self.assertEqual(self.repair_calls,[])


if __name__=="__main__":unittest.main()
