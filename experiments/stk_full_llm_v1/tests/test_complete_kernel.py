"""One meaningful complete-graph fixture: heads must change actual commits."""
from pathlib import Path
import subprocess
import sys
import tempfile
import json
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
sys.path.insert(0,str(PROJECT));sys.path.insert(0,str(ROOT/"scripts"))
from full_schedule_execution import run_full_schedule,committing_greedy,default_program
from cipheur.model import Contact,Graph
from cipheur.repair_v06 import _Meter

class CompleteKernelFixture(unittest.TestCase):
    def test_head_changes_full_schedule_and_cli(self):
        graph=Graph("three_action_fixture",tuple(Contact(v,w,"s"+v,"g"+v,0,w) for v,w in (("a",10),("b",6),("c",6))),
            frozenset({("a","b"),("a","c")}),
            {"station_gap_by_antenna":{"ga":340,"gb":340,"gc":340},"satellite_gap":150},
            {"weight_ticks":{"a":10000000,"b":6000000,"c":6000000}})
        # Shared static degree seed takes a (10). Dynamic Degree commits b/c
        # (12), while Weight commits a (10). No common LS or repair can conceal
        # this causal head difference in the fixture.
        degree=run_full_schedule(graph,"degree",.5,2,swap_rounds=0,max_repairs=0)
        weight=run_full_schedule(graph,"weight",.5,2,swap_rounds=0,max_repairs=0)
        self.assertEqual(degree["selected"],["b","c"]);self.assertEqual(weight["selected"],["a"])
        self.assertTrue(degree["head_ever_committed"] and weight["head_ever_committed"])
        self.assertEqual(degree["phases"]["construction"]["raw_delta_from_seed_ticks"],2000000)
        self.assertTrue(degree["feasible"] and weight["feasible"])
        self.assertEqual(degree["stats"]["conditional_oracle_calls"],0)
        # Exercise actual NPZ/meta/bank/CLI/result path on the same graph.
        with tempfile.TemporaryDirectory(prefix="full_schedule_fixture_") as temp:
            folder=Path(temp);npz=folder/"fixture.npz";meta=folder/"fixture.json";bank=folder/"bank.json";output=folder/"result.json"
            np.savez(npz,contact_id=np.array(["a","b","c"]),weight_ticks=np.array([10000000,6000000,6000000]),
                satellite_id=np.array(["sa","sb","sc"]),antenna_id=np.array(["ga","gb","gc"]),
                start_ticks=np.zeros(3,dtype=np.int64),end_ticks=np.array([10000000,6000000,6000000]),
                edge_u=np.array([0,0]),edge_v=np.array([1,2]),ground_gap_by_node_ticks=np.full(3,340000000),
                satellite_gap_ticks=np.array(150000000),source_id=np.array("fixture"))
            meta.write_text(json.dumps({"source_id":"fixture","config_id":"fixture","split":"train",
                "station_gap_by_antenna_seconds":{"ga":340,"gb":340,"gc":340}}))
            bank.write_text(json.dumps({"programs":[{"id":"fixture_degree","arm":"relations_rule_only",
                "program":default_program("degree").to_dict(),"provenance":{"live_llm":False,"fixture_only":True}}]}))
            child=subprocess.run([sys.executable,str(ROOT/"scripts"/"full_schedule_benchmark.py"),"--graph",str(npz),
                "--metadata",str(meta),"--source","fixture","--config","fixture","--split","train","--method","program",
                "--program-bank",str(bank),"--program-id","fixture_degree","--seconds",".5","--swap-rounds","0",
                "--max-repairs","0","--output",str(output)],capture_output=True,text=True)
            self.assertEqual(child.returncode,0,child.stderr)
            row=json.loads(output.read_text());self.assertEqual(row["value_ticks"],12000000)
            self.assertEqual(row["selected"],["b","c"]);self.assertTrue(row["head_ever_committed"])
            self.assertEqual(row["split"],"train");self.assertEqual(row["stats"]["online_llm_calls"],0)
            self.assertEqual(row["program_arm"],"relations_rule_only")

if __name__=="__main__":unittest.main()
