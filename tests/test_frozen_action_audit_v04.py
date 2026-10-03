import unittest
from fractions import Fraction

from cipheur.frozen_action_audit_v04 import task
from cipheur.model import Contact, Graph


class FrozenActionAuditTests(unittest.TestCase):
    def fixture(self):
        graph = Graph('star',tuple(Contact(str(i),w,'s',str(i),0,1)
                     for i,w in enumerate((3,2,2))),frozenset({('0','1'),('0','2')}))
        pair={'id':'paired','family':'diagnostic','left':graph.to_dict(),'fixed':[],'excluded':[]}
        bank=[{'id':'weight','program':{'name':'weight','features':[],'rule':'weight','rationale':'fixed fixture'}},
              {'id':'degree','program':{'name':'degree','features':[],'rule':'weight/max(1,degree)','rationale':'fixed fixture'}}]
        config={'program_cpu_seconds':5,'max_rollout_steps':2,'max_states_per_context':2,
                'max_matched_full_comparisons':0,'epsilon':1e-8,
                'cancellation':{'nodes_per_component':64,'max_search_component':128,'max_nodes':10000,'max_calls':128}}
        return pair,bank,config

    def test_actual_choices_have_sound_finite_pool_regret(self):
        pair,bank,config=self.fixture()
        row=task((pair,'left',bank,config,{}))
        self.assertTrue(row['execution_complete'])
        self.assertFalse(row['selection_permitted'])
        initial=next(s for s in row['states'] if not s['fixed'])
        self.assertEqual(initial['choices'],{'weight':'0','degree':'1'})
        for name,expected in (('weight',1),('degree',0)):
            r=initial['regret'][name]
            self.assertTrue(r['actual_reached_in_recorded_rollout'])
            self.assertEqual(Fraction(r['lower_exact']),expected)
            self.assertEqual(Fraction(r['upper_exact']),expected)
        self.assertEqual([r['value'] for r in row['rows']],[3,4])

    def test_invalid_boundary_is_explicit_failure_without_replacement_evidence(self):
        pair,bank,config=self.fixture();pair['fixed']=['0','1']
        row=task((pair,'left',bank,config,{}))
        self.assertFalse(row['execution_complete'])
        self.assertEqual(row['states'],[])
        self.assertEqual(row['rows'],[])
        self.assertIn('error',row)


if __name__=='__main__':unittest.main()
