"""Independent matched-auditor semantics on finite, directly checkable data."""
import unittest

from scripts.verify_matched_llm_v05 import FeatureView,normalized_program,quotient,slots,rank,check_schedule,independent_reference,first_action


def graph():
    return {"name":"independent_verifier_fixture","contacts":[{"id":v,"weight":w,"start":0,"end":1} for v,w in (("a",1),("b",1),("x",2),("y",3))],
            "edges":[["a","b"],["a","x"],["a","y"],["x","y"]],"constraints":{"station_gap":0,"satellite_gap":0}}


def program():
    return {"name":"own_fixture","features":[{"name":"nc","expression":{"op":"clique_cover_weight","args":[{"op":"neighbors","args":[{"op":"root"}]}]}}],
            "rule":"weight/max(0.000001,weight,nc)","rationale":"Independent fixture"}


class MatchedVerifierTests(unittest.TestCase):
    def test_typed_feature_and_rank(self):
        p=normalized_program(program());v=FeatureView(graph())
        self.assertEqual(v.features(p,"a")["nc"],4)
        self.assertEqual(v.features(p,"b")["nc"],1)
        self.assertEqual(rank(p,v.features(p,"a")),.25)
        self.assertEqual(rank(p,v.features(p,"b")),1)
        self.assertEqual(p["features"][0]["expression"]["args"][0]["args"][0],{"op":"root","args":[]})

    def test_boundary_feature_active_semantics(self):
        p=normalized_program(program());v=FeatureView(graph(),fixed=["b"])
        self.assertEqual(v.active,frozenset({"x","y"}))
        self.assertEqual(v.features(p,"x")["nc"],3)
        self.assertEqual(v.features(p,"x")["degree"],1)

    def test_duplicate_and_missing_slots_are_retained(self):
        payload={"version":"matched_cold_bank_v05","block":0,"arm":"witness","candidates":[program(),{**program(),"name":"renamed","rationale":"other prose"}]}
        result=slots(payload,0,"witness")
        self.assertEqual(result[0]["status"],"static_valid")
        self.assertEqual(result[1]["status"],"duplicate_deployment_AST_within_batch")
        self.assertEqual(sum(r["status"]=="missing_slot" for r in result),10)

    def test_exact_binary_vector_dag_and_self_loop(self):
        requirements=[{"preferred":"p","other":"q"}]
        self.assertFalse(quotient({"p":{"w":2**53+1},"q":{"w":2**53}},requirements)["contradictory"])
        self.assertTrue(quotient({"p":{"w":1},"q":{"w":1.0}},requirements)["contradictory"])

    def test_completed_schedule_and_failure_receipts(self):
        errors=[]
        def require(condition,kind,where):
            if not condition:errors.append((kind,where))
        row={"completed":True,"selected":["b","y"],"value":4,"value_exact":"4","feature_work":20,
             "trace":[{"selected":"b","remaining_count":4,"score":1},{"selected":"y","remaining_count":2,"score":1}]}
        check_schedule(row,{"graph":graph(),"fixed":[],"excluded":[]},require,"fixture")
        self.assertEqual(errors,[])
        row["value_exact"]="5";check_schedule(row,{"graph":graph(),"fixed":[],"excluded":[]},require,"fixture")
        self.assertTrue(any(k=="independent_complete_schedule_reward" for k,w in errors))

    def test_independent_upper_and_first_action(self):
        p=normalized_program(program());state=FeatureView(graph())
        self.assertEqual(independent_reference(graph()),(4,4))
        self.assertEqual(first_action(p,state),("b",1))


if __name__=="__main__":unittest.main()
