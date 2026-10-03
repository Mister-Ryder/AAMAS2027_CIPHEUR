import unittest
from unittest.mock import patch
from cipheur.holdout_study import BudgetMeter,ProgramBudgetExceeded,execute_with_budget
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact,Graph
class CooperativeBudgetTests(unittest.TestCase):
 def test_checkpoint_uses_process_cpu_and_does_not_swallow_timeout(self):
  with patch('cipheur.holdout_study.time.process_time',return_value=0):m=BudgetMeter(1)
  with patch('cipheur.holdout_study.time.process_time',return_value=2):
   for i in range(255):m['feature_work']=i
   with self.assertRaises(ProgramBudgetExceeded):m['feature_work']=256
 def test_budgeted_frozen_trace_matches_unbudgeted(self):
  g=Graph('budget',tuple(Contact(str(i),i+1,'s','g',i,i+1) for i in range(8)),frozenset({('0','1'),('2','3')}),{})
  p=FeatureRuleProgram('test',[],'weight/max(1,degree)')
  a=execute_with_budget(g,p,(),(),None);b=execute_with_budget(g,p,(),(),10)
  for key in ('selected','trace','value','feasible'):self.assertEqual(a[key],b[key])
 def test_zero_cpu_budget_eventually_interrupts_charged_execution(self):
  g=Graph('budget',tuple(Contact(str(i),i+1,'s','g',i,i+1) for i in range(40)),frozenset(),{})
  with self.assertRaises(ProgramBudgetExceeded):execute_with_budget(g,FeatureRuleProgram('test',[],'weight'),(),(),0)
if __name__=='__main__':unittest.main()
