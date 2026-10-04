"""Mock-only classical-component pipeline contracts, no research runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("classic_components",ROOT/"scripts/run_classic_components_train_v06.py")
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from cipheur.model import Contact,Graph


class ComponentContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="v06_component_mock_")
        self.out=Path(self.temp.name)
        graph=Graph("mock",(Contact("v1",1,"s1","g1",0,1),Contact("v2",2,"s2","g2",0,1)),frozenset({("v1","v2")}))
        runner.write(self.out/"toy.json",graph.to_dict())
        self.context={"id":"mock","input_family":"mock","family":"mock","source_cluster":"mock","split":"train",
            "path":"toy","raw_sha256":"mock","n":2,"m_conflict":1,"source_weight_scale":2,
            "graph_file":"toy.json","graph_file_sha256":runner.digest(self.out/"toy.json"),"graph_sha256":graph.digest()}
        self.config={"targets":[.1,1,5],"native_seeds":[1,2,3],"repair_config":runner.REPAIR,
            "CHILS_executable":{"path":"never_invoked"}}
        self.native_calls=[];self.repair_calls=[]

    def tearDown(self):self.temp.cleanup()

    def native(self,graph,path,name,**kw):
        self.native_calls.append(kw)
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","child_cpu_seconds":.2,"status":"mock"}

    def repair(self,graph,**kw):
        self.repair_calls.append(kw)
        self.assertEqual(kw["clock"],"wall")
        return {"completed":True,"feasible":True,"selected":["v2"],"value_exact":"2","status":"mock"}

    def execute(self,native=None,repair=None):
        with patch.object(runner,"OUT",self.out),patch.object(runner,"run_solver",native or self.native),patch.object(runner,"repair_schedule",repair or self.repair):
            runner.execute_context(self.context,self.config)
        return [json.loads(l) for p in (self.out/"context_results").glob("*.jsonl") for l in p.read_text().splitlines()]

    def test_exact_assignment_phase_reuse_and_cost(self):
        rows=self.execute();self.assertEqual(len(rows),30);self.assertEqual(len({runner.key(r) for r in rows}),30)
        self.assertEqual(len(self.native_calls),18);self.assertEqual(len(self.repair_calls),12)
        self.assertEqual({runner.key(r) for r in rows},{runner.key(r) for r in runner.expected(self.context)})
        self.assertTrue(all(r["successful_assignment"] and r["quality_reward_exact_original_objective"]=="1" for r in rows))
        for r in rows:
            if r["track"]=="Degreewarm":
                half=next(x for x in rows if x["track"]=="CHILShalf" and x["seed"]==r["seed"] and x["nominal_wall_target_seconds"]==r["nominal_wall_target_seconds"])
                self.assertEqual(r["native_initial_value_exact"],half["result"]["value_exact"])
                self.assertEqual(r["standalone_pipeline_wall_seconds"],half["result"]["wrapper_wall_seconds"]+r["repair_wrapper_wall_seconds"])
                self.assertEqual(r["standalone_pipeline_cpu_seconds"],half["result"]["wrapper_self_cpu_seconds"]+.2+r["repair_wrapper_cpu_seconds"])

    def test_missing_initializer_never_falls_back(self):
        def native(g,p,n,**kw):
            if kw["seconds"] in (.05,.5,2.5):return {"completed":False,"feasible":None,"value_exact":None,"status":"mock_failure"}
            return self.native(g,p,n,**kw)
        rows=self.execute(native=native);warm=[r for r in rows if r["track"]=="Degreewarm"]
        self.assertEqual(len(warm),9);self.assertEqual(len(self.repair_calls),3)
        self.assertTrue(all(r["result"] is None and r["runner_error"]["type"]=="NativeInitializerUnavailable" and not r["successful_assignment"] for r in warm))

    def test_decreasing_warm_reward_is_not_success(self):
        def repair(g,**kw):
            result=self.repair(g,**kw)
            if kw.get("initial") is not None:result["value_exact"]="0"
            return result
        rows=self.execute(repair=repair);warm=[r for r in rows if r["track"]=="Degreewarm"]
        self.assertTrue(all(r["runner_error"]["type"]=="AssertionError" and not r["successful_assignment"] and r["quality_reward_exact_original_objective"] is None for r in warm))

    def test_test_context_refused_before_solver(self):
        self.context["split"]="test"
        with self.assertRaises(AssertionError):self.execute()
        self.assertEqual(self.native_calls,[]);self.assertEqual(self.repair_calls,[])


if __name__=="__main__":unittest.main()
