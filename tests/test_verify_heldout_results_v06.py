"""Independent verifier tests on fabricated inputs only."""
from copy import deepcopy
from fractions import Fraction
import unittest
from scripts.verify_heldout_results_v06 import Audit,transport,pairing,robustness,VARIANTS

def graph():
    return {'name':'toy','contacts':[{'id':'0','weight':1,'satellite':'s0','station':'g0','start':0,'end':1},
        {'id':'1','weight':2,'satellite':'s1','station':'g1','start':0,'end':1}],
        'edges':[['0','1']],'constraints':{},'provenance':{}}
def frame():
    records=[{'id':'left','cluster':'pair','pair':'pair','paired':True,'side':'left','split':'test','family':'toy',
        'graph':graph(),'graph_digest':'original','fixed':[],'excluded':[],'queries':[{'a':'0','b':'1'}]}]
    difference={'a':'0','b':'1','preferred':'1','lower_exact':'1','upper_exact':'1',
        'cancelled_components':[['0']],
        'unmatched':{'left':[{'vertices':['1'],'bound':{'selected':['1'],'lower_exact':'1','upper_exact':'1'}}]}}
    labels=[{'id':'left','cluster':'pair','graph_digest':'original','rows':[{'a':'0','b':'1','difference':difference}]}]
    return records,labels
def incumbent():
    cfg={'seconds':.5,'clock':'wall','repair_config':{'max_destroy':4,'max_patch_vertices':24,'max_patches':1,'node_budget_per_patch':128,'max_search_nodes':65536}}
    result={'config':cfg['repair_config'],'declared_seconds':.5,'deadline_clock':'wall','priority':'degree',
        'feasible':True,'incumbent_available':True,'fallback_used':False,'online_model_calls':0,'conditional_oracle_calls':0,
        'exact_optimum_claimed':False,'selected':['1'],'value_exact':'2','completed':True,'error':None,
        'initializer_trace':[{'selected':'1','available':2,'score_exact':'2'}],'initial_selected':['1'],
        'initial_value_exact':'2','initialization_complete':True,'starting_value_exact':'0','patch_trace':[],
        'improvements':0,'patches_attempted':0,'meter':{'search_nodes':0,'feature_work':0,'repair_work':0,
            'feature_primitives':{},'repair_primitives':{}},'global_budget_exhausted':False,'wall_seconds':.002,'cpu_seconds':.001}
    record={'id':'left','graph':graph(),'graph_digest':'original','fixed':[],'excluded':[]}
    return record,result,{'priority':'degree','program':None},cfg

class HeldoutVerification(unittest.TestCase):
    def test_numeric_interval_not_relabelled(self):
        records,labels=frame();rs,ls,m=transport(records,labels,0)
        self.assertEqual(ls[0]['rows'][0]['difference']['lower_exact'],'1')
        self.assertEqual(ls[0]['rows'][0]['difference']['preferred'],m['pair']['1'])
        self.assertEqual(ls[0]['rows'][0]['difference']['unmatched']['left'][0]['vertices'],[m['pair']['1']])
        self.assertEqual(labels,frame()[1])
    def test_shared_pair_mapping_and_weighted_edges(self):
        rs,labels=frame();right=deepcopy(rs[0]);right.update(id='right',side='right');rs.append(right)
        tr,_,m=transport(rs,labels,4)
        self.assertEqual(tr[0]['graph']['contacts'],tr[1]['graph']['contacts'])
        self.assertEqual(tr[0]['graph']['edges'],tr[1]['graph']['edges'])
        self.assertEqual(set(m['pair'].values()),{'r000','r001'})
    def test_valid_degree_incumbent_without_production_run(self):
        a=Audit();a.kernel(*incumbent(),'toy');self.assertEqual(a.errors,[])
    def test_incorrect_exact_reward_rejected(self):
        r,res,e,c=incumbent();res['value_exact']='3';a=Audit();a.kernel(r,res,e,c,'toy')
        self.assertIn('retained_original_graph_exact_objective_boundary',{x['kind'] for x in a.errors})
    def test_initializer_forgery_rejected(self):
        r,res,e,c=incumbent();res['initializer_trace'][0]['score_exact']='1';a=Audit();a.kernel(r,res,e,c,'toy')
        self.assertIn('every_common_degree_initializer_prefix',{x['kind'] for x in a.errors})
    def test_strict_reversal_and_joint_fit(self):
        q={'pair':'p','query_index':0,'side':'left','cluster':'p','a':'0','b':'1','certificate_status':'strict','preferred':'0','passed':True}
        right={**q,'side':'right','preferred':'1','passed':False};row=pairing([q,right])[0]
        self.assertEqual(row['category'],'strict_reversal');self.assertFalse(row['pair_passed'])
    def test_exact_ties_not_called_failed_predictions(self):
        q={'pair':'p','query_index':0,'side':'left','cluster':'p','a':'0','b':'1','certificate_status':'exact_tie','preferred':None,'passed':None}
        row=pairing([q,{**q,'side':'right'}])[0]
        self.assertEqual(row['category'],'exact_tie_both');self.assertIsNone(row['pair_passed'])
    def test_missing_pair_endpoint_rejected(self):
        with self.assertRaises(ValueError):pairing([{'pair':'p','query_index':0,'side':'left'}])
    def test_duplicate_pair_endpoint_rejected(self):
        q={'pair':'p','query_index':0,'side':'left'}
        with self.assertRaises(ValueError):pairing([q,q])
    def test_misaligned_actions_not_reversal(self):
        q={'pair':'p','query_index':0,'side':'left','cluster':'p','a':'0','b':'1','certificate_status':'strict','preferred':'0','passed':True}
        with self.assertRaises(ValueError):pairing([q,{**q,'side':'right','a':'2','b':'3','preferred':'3'}])
    def test_contradictory_quotient_requires_witness(self):
        a=Audit();a.witnesses({'structural_witnesses':[],'contradictory':True},{},[],'empty')
        self.assertIn('explicit_obstruction_witness_presence',{x['kind'] for x in a.errors})
    def test_total_patch_cap_rejects_valid_extra_patch(self):
        # The reviewer supplied this counterexample: individually valid
        # zero-gain patches must still obey the common total attempt limit.
        from tests.test_verify_performance_test_v06 import patch
        record,result,entry,cfg=incumbent();result.update(patch_trace=[patch(),patch()],patches_attempted=2)
        a=Audit();a.kernel(record,result,entry,cfg,'overcap')
        self.assertIn('every_patch_replay_final_identity',{x['kind'] for x in a.errors})
    def test_robustness_mean_worst_and_missing_propagation(self):
        entry={'id':'toy','missing_baseline':False};rows=[{'id':'toy','variant':v,'role_scope':{},'interface':{'strict_passed':i,'strict_total':9}}
            for i,v in enumerate(VARIANTS)]
        s=robustness('R2',[entry],rows)[0];self.assertEqual(s['mean_relabel_strict_passed'],3);self.assertEqual(s['worst_relabel_strict_passed'],1)
        rows[-1]['interface']=None;s=robustness('R2',[entry],rows)[0]
        self.assertIsNone(s['mean_relabel_strict_passed']);self.assertFalse(s['all5_fit_measurements_available'])

if __name__=='__main__':unittest.main()
