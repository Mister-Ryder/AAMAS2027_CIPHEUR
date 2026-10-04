from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cipheur.experiment_data import diagnostic_pair
from cipheur.graph_features import FeatureRuleProgram, NEIGHBOR_EDGE_COUNT
from cipheur.matched_synthesis_v05 import ARMS, execute, file_hash, information_gate, load_bank, nested_inputs, select, validate_response, write
from cipheur.model import Contact, Graph


class MatchedSynthesisV05Tests(unittest.TestCase):
    def program(self, name="p"):
        return FeatureRuleProgram(name, [], "weight", "test").to_dict()

    def payload(self, candidates, arm="witness", block=0):
        return {"version": "matched_cold_bank_v05", "block": block, "arm": arm, "candidates": candidates}

    def test_missing_invalid_duplicate_slots_remain_assigned(self):
        candidates=[self.program(), self.program("renamed"), {"rule":"weight"}]
        entries=validate_response(self.payload(candidates),0,"witness")
        self.assertEqual(len(entries),12)
        self.assertEqual([r["status"] for r in entries[:4]],
                         ["static_valid","duplicate_deployment_AST_within_batch","invalid_candidate","missing_slot"])
        self.assertEqual(sum(r["program"] is not None for r in entries),1)

    def test_extra_candidates_and_wrong_arm_not_silently_salvaged(self):
        for value in [self.payload([self.program(str(i)) for i in range(13)]), self.payload([self.program()],"objective")]:
            entries=validate_response(value,0,"witness")
            self.assertTrue(all(r["status"]=="invalid_response_schema" for r in entries))

    def test_gate_distinguishes_information_from_scalar_fit(self):
        pair=diagnostic_pair("train",0,"reversal")
        states,endpoints,requirements={},{},[]
        for side,preferred,other in [("left",pair["b"],pair["a"]),("right",pair["a"],pair["b"])]:
            states[side]={"graph":pair[side].to_dict(),"fixed":list(pair["fixed"]),"excluded":list(pair["excluded"])}
            for node in (pair["a"],pair["b"]):
                endpoints[side+":"+node]={"prefix":side,"node":node}
            requirements.append({"preferred":side+":"+preferred,"other":side+":"+other,"metadata":{"kind":"cancelled_actual_action"}})
        evidence={"states":states,"endpoints":endpoints,"requirements":requirements}
        plain={"id":"plain","program":self.program()}
        feature=FeatureRuleProgram("split",[{"name":"ec","expression":NEIGHBOR_EDGE_COUNT}],"weight","Unused distinguishing field tests full-interface gate.").to_dict()
        a=information_gate((plain,evidence));b=information_gate(({"id":"split","program":feature},evidence))
        self.assertFalse(a["passed"])
        self.assertTrue(b["passed"])
        self.assertEqual(b["scalar_agreement"],{"tie":2})

    def test_timeout_preserves_null_schedule_no_fallback(self):
        g=Graph("timeout",tuple(Contact(str(i),1,str(i),str(i),0,1) for i in range(64)),frozenset())
        r=execute(g,self.program(),seconds=0)
        self.assertFalse(r["completed"])
        self.assertIsNone(r["selected"])
        self.assertIsNone(r["trace"])
        self.assertIsNone(r["value"])

    def test_completion_exact_original_reward(self):
        g=Graph("fraction",(Contact("a",.25,"a","a",0,1),Contact("b",.5,"b","b",0,1)),frozenset())
        r=execute(g,self.program(),seconds=5)
        self.assertTrue(r["completed"])
        self.assertEqual(r["value_exact"],"3/4")
        self.assertTrue(g.feasible(r["selected"]))

    def test_selection_uniform_gate_failure_penalty_and_exact_tie(self):
        bank=[]
        for arm in ARMS:
            bank+=validate_response(self.payload([self.program("first"),FeatureRuleProgram("second",[],"weight/2","other rule").to_dict()],arm),0,arm,slots=2)
        contexts=[]
        for family in ["large","large","small"]:
            contexts.append({"family":family,"fixed_reward_reference":10,"fixed_degree_work":1,
                             "rows":[{"candidate_id":e["id"],"completed":True,"value":8,"feature_work":1} for e in bank]})
        gates=[{"candidate_id":e["id"],"passed":True} for e in bank]
        assessments,programs,choices=select(bank,contexts,gates)
        self.assertEqual(len(programs),3)
        self.assertTrue(all(c["selected_id"].endswith(":0") for c in choices.values()))
        self.assertTrue(all(abs(a["utility"]-.8)<1e-12 for a in assessments))
        for gate in gates:
            if "relations" in gate["candidate_id"]:gate["passed"]=False
        _,programs,choices=select(bank,contexts,gates)
        self.assertNotIn("block_0_relations",programs)
        self.assertIsNone(choices["block_0_relations"]["selected_id"])
        self.assertFalse(choices["block_0_relations"]["fallback_used"])

    def test_all_authoring_freeze_is_required_and_response_changes_reject(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);protocol={"blocks":4,"slots_per_block_arm":12,"requested_slots":144}
            write(p/"protocol.json",protocol)
            with self.assertRaises(ValueError):load_bank(p,protocol)
            write(p/"transport_amendment.json",{"original_protocol_sha256":file_hash(p/"protocol.json"),"decided_before_any_v05_candidate_assessment":True})
            hashes={}
            for block in range(4):
                for arm in ARMS:
                    name=f"block_{block}_{arm}.json";write(p/"responses"/name,self.payload([],arm,block));hashes[name]=file_hash(p/"responses"/name)
            write(p/"authoring_completion.json",{"version":"matched_cli_authoring_completion_v05","transport_amendment_sha256":file_hash(p/"transport_amendment.json"),
                                                "all_authoring_completed_before_assessment":True,"same_requested_model_and_settings_all_cells":True,"response_sha256":hashes})
            bank,receipts=load_bank(p,protocol)
            self.assertEqual(len(bank),144)
            self.assertTrue(all(e["status"]=="missing_slot" for e in bank))
            (p/"responses/block_0_witness.json").write_text("{}",encoding="utf-8")
            with self.assertRaises(ValueError):load_bank(p,protocol)

    def test_input_inventory_reads_seed_and_graph_identity(self):
        g=Graph("identity",(Contact("a",1,"s","g",0,1),),frozenset())
        seeds,graphs,fp=set(),set(),set()
        nested_inputs({"test":[{"source":{"seed":180000001},"left":g.to_dict()}]},seeds,graphs,fp)
        self.assertEqual(seeds,{180000001})
        self.assertEqual(graphs,{g.digest()})
        self.assertEqual(len(fp),1)


if __name__=="__main__":unittest.main()
