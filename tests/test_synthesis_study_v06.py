import unittest
from fractions import Fraction
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph
from cipheur.synthesis_study_v06 import interface_assessment, macro_quality, select_cells, validate_response


class SynthesisContractTests(unittest.TestCase):
    def setUp(self):
        self.g=Graph("actual_alias",tuple(Contact(v,1,"S",v,0,1) for v in "abxyzw"),
            frozenset((a,b) for a,b in (('a','b'),('a','x'),('a','y'),('x','y'),('b','z'),('b','w'))))
        self.record={"id":"r","family":"f","split":"train","paired":False,"fixed":[],"excluded":[],
                     "graph":self.g.to_dict(),"graph_digest":self.g.digest()}
        self.labels=[{"id":"r","rows":[{"a":"a","b":"b","kind":"alias","base_alias_by_side":[True],
            "difference":{"status":"strict","preferred":"a"}}]}]
        self.feature={"name":"h","expression":{"op":"count","args":[{"op":"induced_edges","args":[
            {"op":"neighbors","args":[{"op":"root","args":[]}]}]}]}}

    def test_unused_feature_does_not_repair_deployed_interface(self):
        # a and b have the same base9, but forced completion has values3 and2.
        raw=FeatureRuleProgram("unused",[self.feature],"weight").to_dict()
        got=interface_assessment(raw,[self.record],self.labels)
        self.assertTrue(got['quotient']['contradictory'])
        self.assertFalse(got['declared_quotient']['contradictory'])
        self.assertEqual(got['strict_passed'],0)
        used=interface_assessment(FeatureRuleProgram("used",[self.feature],"h").to_dict(),[self.record],self.labels)
        self.assertFalse(used['quotient']['contradictory'])
        self.assertEqual(used['alias_strict_passed'],1)

    def test_slots_and_duplicates_are_never_replaced(self):
        p=FeatureRuleProgram("same",[],"weight").to_dict()
        rows=validate_response({"version":"matched_cold_bank_v06","block":0,"arm":"witness","candidates":[p,p]},0,"witness",8)
        self.assertEqual(len(rows),8)
        self.assertEqual(rows[1]['status'],'duplicate_deployment_AST_within_batch')
        self.assertEqual(rows[-1]['status'],'missing_slot')
        self.assertEqual(rows[-1]['slot'],7)

    def test_lex_selector_and_empty_prefix(self):
        def row(slot,fit,q,work,eligible=True):
            return {'id':str(slot),'block':0,'arm':'witness','slot':slot,'eligible':eligible,
                    'interface':{'strict_passed':fit},'kernel_summary':{'macro_quality_exact':q,'macro_work_exact':str(work)}}
        rows=[row(0,0,'1',1,False),row(1,4,'1/2',10),row(2,3,'1',1),row(3,4,'3/4',20),row(4,4,'3/4',15)]
        winners,empty,prefix=select_cells(rows,1)
        self.assertEqual(winners[0]['slot'],4)
        self.assertEqual(len(empty),2)
        self.assertIsNone(prefix[0]['winner_id'])
        self.assertEqual(prefix[1]['winner_id'],'1')

    def test_macro_quality_weights_families_not_cases(self):
        a={**self.record,'id':'a','family':'A'};b={**self.record,'id':'b','family':'A'}
        c={**self.record,'id':'c','family':'B'}
        def row(i,v):return {'id':i,'result':{'value_exact':str(v),'meter':{'feature_work':1,'repair_work':2}}}
        got=macro_quality([row('a',3),row('b',3),row('c',6)],[a,b,c])
        self.assertEqual(Fraction(got['macro_quality_exact']),Fraction(3,4))
        self.assertEqual(Fraction(got['macro_work_exact']),3)

    def test_test_snapshot_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'TEST'):
            interface_assessment(FeatureRuleProgram('x',[], 'weight').to_dict(),[{**self.record,'split':'test'}],self.labels)


if __name__=='__main__':unittest.main()
