"""Orchestration/cost/failure contracts with mocked solvers, no research runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("performance_runner",ROOT/"scripts/run_performance_test_v06.py")
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
from cipheur.model import Contact,Graph


class PerformanceRunnerContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="v06_orchestration_mock_")
        self.out=Path(self.temp.name)
        graph=Graph("mock",(Contact("v1",1,"s1","g1",0,1),Contact("v2",2,"s2","g2",0,1)),
                    frozenset({("v1","v2")}))
        runner.write(self.out/"toy.json",graph.to_dict())
        self.context={"id":"mock","population":"mock","split":"test","n":2,"m":1,
            "graph_file":"toy.json","graph_file_sha256":runner.digest(self.out/"toy.json"),
            "graph_sha256":graph.digest(),"source_weight_scale":1}
        self.protocol={"wall_targets":[.1,1,5],"native_requests":[r for r in runner.METHODS if r["method"]!="Degree"],
            "repair_config":runner.REPAIR,"executables":{n:{"path":"never_invoked"} for n in
                ("CHILS","M2WIS","Struction","WeightedBR")}}
        self.deployment={"programs":[{"method_id":"p"+str(i),"program":{},"program_sha256":"mock",
             "kind":"mock","available":True} for i in range(14)]+[
             {"method_id":"Degree","program":None,"kind":"mock","available":True}]}
        self.native_calls=[];self.repair_calls=[]

    def tearDown(self):self.temp.cleanup()

    def native(self,graph,executable,name,**kwargs):
        self.native_calls.append(kwargs)
        return {"method":name,"seed":kwargs["seed"],"completed":True,"feasible":True,
                "selected":["v2"],"value_exact":"2","seconds":.3,"child_cpu_seconds":.2,"status":"mock"}

    def repair(self,graph,**kwargs):
        self.repair_calls.append(kwargs)
        self.assertEqual(kwargs["clock"],"wall")
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","status":"mock"}

    def execute(self,native=None,repair=None):
        with patch.object(runner,"run_solver",native or self.native),patch.object(runner,"repair_schedule",repair or self.repair):
            runner.run_context(self.context,self.protocol,self.deployment,self.out)
        return [json.loads(l) for p in (self.out/"context_results").glob("*.jsonl") for l in p.read_text().splitlines()]

    def test_shared_initialization_keys_and_standalone_cost(self):
        rows=self.execute()
        self.assertEqual(len(rows),126)
        self.assertEqual(len({runner.key(r) for r in rows}),126)
        self.assertEqual(len(self.native_calls),36)
        self.assertEqual(len(self.repair_calls),90)
        warm=[r for r in rows if r["track"]=="warm_CHILS"]
        self.assertEqual(len(warm),45)
        self.assertTrue(all(r["standalone_pipeline_cpu_seconds"]>=.2 for r in warm))
        self.assertTrue(all(r["standalone_pipeline_wall_seconds"]>=.3 for r in warm))
        self.assertTrue(all(r["successful_assignment"] for r in rows))
        self.assertEqual(sum(r["initial"] is not None for r in self.repair_calls),45)

    def test_native_initial_failure_never_falls_back(self):
        def native(graph,executable,name,**kw):
            if kw["seconds"] in (.05,.5,2.5):
                return {"completed":False,"feasible":None,"selected":None,"value":None,
                        "seconds":.3,"status":"mock_native_failure"}
            return self.native(graph,executable,name,**kw)
        rows=self.execute(native=native)
        warm=[r for r in rows if r["track"]=="warm_CHILS"]
        self.assertEqual(len(warm),45)
        self.assertEqual(len(self.repair_calls),45)
        self.assertTrue(all(r["result"] is None and not r["successful_assignment"] for r in warm))
        self.assertTrue(all(r["runner_error"]["type"]=="NativeInitializerUnavailable" for r in warm))

    def test_missing_quality_control_is_kept_not_replaced(self):
        self.deployment["programs"][0]["available"]=False
        rows=self.execute()
        missing=[r for r in rows if r["method"]=="p0"]
        self.assertEqual(len(rows),126)
        self.assertEqual(len(missing),6)
        self.assertEqual(len(self.repair_calls),84)
        self.assertTrue(all(r["result"] is None for r in missing))

    def test_declining_mock_result_is_failed_diagnostic(self):
        def repair(graph,**kwargs):
            result=self.repair(graph,**kwargs)
            if kwargs["initial"] is not None:result["value_exact"]="0"
            return result
        rows=self.execute(repair=repair)
        warm=[r for r in rows if r["track"]=="warm_CHILS"]
        self.assertTrue(all(r["runner_error"]["type"]=="AssertionError" for r in warm))
        self.assertTrue(all(not r["successful_assignment"] and r["quality_reward_exact_original_objective"] is None for r in warm))
        self.assertTrue(all(r["diagnostic_retained_reward_exact_original_objective"]=="0" for r in warm))


if __name__=="__main__":unittest.main()
