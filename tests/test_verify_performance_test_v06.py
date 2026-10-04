"""Fabricated mathematical/receipt counterexamples; no experimental rollout."""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import unittest
from scripts.verify_performance_test_v06 import Audit,GraphAudit,cohort,expected_keys,safe_member,key,policy_phase_receipts,canonical
from tests.test_verify_heldout_results_v06 import graph,incumbent

def toy():
    record,result,_,config=incumbent();cfg={**config['repair_config'],'max_patches':1,'policy_scope':'branch'}
    result.update(config=cfg,random_seed=1);protocol={'repair_config':cfg}
    return GraphAudit(record['graph'],Audit()),result,{'method_id':'Degree','program':None,'available':True},protocol

def patch():
    return {'destroy':['1'],'target':'0','local_selected':['1'],'incumbent_patch_exact':'2','lower_exact':'2',
        'upper_exact':'2','root_upper_exact':'2','root_clique_cover':[['0','1']],'restricted_exact':True,
        'patch':['0','1'],'full_region_size':2,'restricted':False,'priority_order':[],'common_degree_order':[],
        'greedy_passes':[],'gain_exact':'0','committed':False,'search_nodes':0,'stage':'returned'}

def native_receipt():
    g=toy()[0];r={'track':'native','method':'CHILS','seed':1,'nominal_wall_target_seconds':1}
    protocol={'executables':{'CHILS':{'path':'/bin/constructed_solver','sha256':'toy_binary'}}}
    result={'method':'CHILS','seed':1,'declared_seconds':1,'hard_wall_seconds':30,'threads':1,'exact_optimum_claimed':False,
        'wrapper_wall_seconds':.3,'wrapper_self_cpu_seconds':.02,'seconds':.25,'child_cpu_seconds':.1,
        'input_sha256':g.metis_sha,'integer_scale':1,'executable_sha256':'toy_binary','solver_invoked':True,
        'command':['/bin/constructed_solver','-g','/tmp/cipheur_v06_solver_toy/input.graph','-o','/tmp/cipheur_v06_solver_toy/solution.txt',
            '-p','4','-c','1','-s','0.1','-t','1','-r','1'],'nominal_target_exceeded':False,
        'completed':True,'feasible':True,'selected':['1'],'value_exact':'2','returncode':0,'status':'checked_feasible_incumbent',
        'solution_text':'2\n','output_format':'one_based_ids'}
    return g,r,result,protocol

class PerformanceAudit(unittest.TestCase):
    def test_complete_frozen_frame_size(self):
        p={'wall_targets':[.1,1,5],'native_requests':[{'method':str(i),'seed':1} for i in range(11)]}
        rows=list(expected_keys([{'id':'toy'}],p,[{'method_id':str(i)} for i in range(23)]))
        self.assertEqual(len(rows),174);self.assertEqual(len(set(rows)),174)
    def test_fractional_native_metis_without_rounding(self):
        source=graph();source['contacts'][0]['weight']=.25;source['contacts'][1]['weight']=.5;g=GraphAudit(source,Audit())
        self.assertEqual(g.integer_scale,4);self.assertEqual(g.metis_sha,sha256(b'2 1 10\n1 2\n2 1\n').hexdigest())
    def test_common_initializer_and_warm_seed(self):
        g,r,e,p=toy();g.kernel(r,e,p,.5,[],'cold');self.assertEqual(g.a.errors,[])
        warm=deepcopy(r);warm.update(initializer_trace=[],starting_value_exact='2');g.kernel(warm,e,p,.5,['1'],'warm')
        self.assertEqual(g.a.errors,[])
    def test_initializer_score_forgery(self):
        g,r,e,p=toy();r['initializer_trace'][0]['score_exact']='1';g.kernel(r,e,p,.5,[],'forged')
        self.assertIn('exact_common_degree_prefix',{x['kind'] for x in g.a.errors})
    def test_actual_exact_patch_proof(self):
        g,r,e,p=toy();r.update(patch_trace=[patch()],patches_attempted=1);g.kernel(r,e,p,.5,[],'patch')
        self.assertEqual(g.a.errors,[]);self.assertEqual(g.exact_cache[('0','1')][0],Fraction(2))
    def test_patch_count_cap_not_just_node_cap(self):
        g,r,e,p=toy();r.update(patch_trace=[patch(),patch()],patches_attempted=2);g.kernel(r,e,p,.5,[],'overcap')
        self.assertIn('complete_retained_incumbent_replay',{x['kind'] for x in g.a.errors})
    def test_nonclique_bound_forgery(self):
        source=graph();source['edges']=[];g=GraphAudit(source,Audit());r=toy()[1]
        r.update(initializer_trace=[{'selected':'1','available':2,'score_exact':'2'},{'selected':'0','available':1,'score_exact':'1'}],
            initial_selected=['0','1'],initial_value_exact='3',selected=['0','1'],value_exact='3')
        x=patch();x.update(destroy=['0','1'],target='0',incumbent_patch_exact='3',local_selected=['0','1'],lower_exact='3',upper_exact='3',root_upper_exact='2')
        r.update(patch_trace=[x],patches_attempted=1);g.kernel(r,{'method_id':'Degree','program':None,'available':True},toy()[3],.5,[],'badclique')
        self.assertIn('clique_partition_upper_proof',{e['kind'] for e in g.a.errors})
    def test_cohorts_preserve_role(self):
        self.assertEqual(cohort({'kind':'genuine_R2_witness_joint'}),'joint_W')
        self.assertEqual(cohort({'kind':'nonguarded_R2_quality_comparator','arm':'relations'}),'quality_R')
        self.assertEqual(cohort({'kind':'nonguarded_published_EoH_DSL_quality'}),'published_EoH_DSL_quality')
    def test_archive_traversal_rejected(self):
        import tarfile
        for name in ('../a','/a','x\\a'):
            with self.assertRaises(ValueError):safe_member(tarfile.TarInfo(name))
    def test_conflicting_target_rejected(self):
        with self.assertRaises(ValueError):key({'id':'x','target':5,'nominal_wall_target_seconds':1,'track':'native','method':'CHILS','seed':1})
    def test_missing_identity_cannot_fake_fallback(self):
        g,r,e,p=toy();e.update(available=False,method_id='missing');r['priority']='program';g.kernel(r,e,p,.5,[],'missing')
        self.assertIn('available_frozen_identity_no_fallback',{x['kind'] for x in g.a.errors})
    def test_valid_native_receipt_without_solver_execution(self):
        g,r,result,p=native_receipt();g.native(r,result,p,'native');self.assertEqual(g.a.errors,[])
    def test_native_wrong_file_paths_rejected(self):
        g,r,result,p=native_receipt();result['command'][2]='/wrong.graph';g.native(r,result,p,'wrongpath')
        self.assertIn('native_input_output_temporary_file_contract',{x['kind'] for x in g.a.errors})
    def test_negative_self_cpu_cannot_hide_in_positive_total(self):
        g,r,result,p=native_receipt();result.update(wrapper_self_cpu_seconds=-2,child_cpu_seconds=3);g.native(r,result,p,'negativeCPU')
        self.assertIn('individual_native_wrapper_time_receipts',{x['kind'] for x in g.a.errors})
    def test_executed_policy_cannot_omit_wall_or_cpu_receipt(self):
        for wall,cpu in ((None,.1),(.1,None),(.1,-.01)):
            a=Audit();r={'track':'cold_Degree','nominal_wall_target_seconds':1,'policy_nominal_seconds':1,
                'policy_wrapper_wall_seconds':wall,'policy_wrapper_cpu_seconds':cpu,'result':{},'runner_error':None}
            policy_phase_receipts(r,{'available':True},None,a,'toy')
            self.assertIn('executed_policy_phase_has_both_nonnegative_times',{x['kind'] for x in a.errors})
    def test_failed_initializer_row_retains_exact_receipt_without_policy_phase(self):
        initial={'completed':True,'feasible':True,'selected':['1']}
        row={'result':initial,'runner_error':{'type':'toy_error'},'successful_assignment':False}
        r={'track':'warm_CHILS','nominal_wall_target_seconds':1,'policy_nominal_seconds':.5,
            'result':None,'runner_error':{'type':'NativeInitializerUnavailable'},'native_initial_result':initial,
            'shared_initializer_receipt_sha256':canonical(initial),'advanced_track_available':False}
        a=Audit();policy_phase_receipts(r,{'available':True},row,a,'toy');self.assertEqual(a.errors,[])
        bad=deepcopy(r);bad['native_initial_result']=None;a=Audit()
        policy_phase_receipts(bad,{'available':True},row,a,'forged')
        self.assertIn('initializer_failure_no_fallback_and_exact_failed_receipt',{x['kind'] for x in a.errors})
    def test_successful_initializer_cannot_be_reported_unavailable(self):
        initial={'completed':True,'feasible':True,'selected':['1']};row={'result':initial,'runner_error':None,'successful_assignment':True}
        r={'track':'warm_CHILS','nominal_wall_target_seconds':1,'policy_nominal_seconds':.5,
            'result':None,'runner_error':{'type':'NativeInitializerUnavailable'},'native_initial_result':initial,
            'shared_initializer_receipt_sha256':canonical(initial),'advanced_track_available':False}
        a=Audit();policy_phase_receipts(r,{'available':True},row,a,'toy')
        self.assertIn('initializer_failure_no_fallback_and_exact_failed_receipt',{x['kind'] for x in a.errors})

if __name__=='__main__':unittest.main()
