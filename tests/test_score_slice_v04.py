import random,unittest
from cipheur.compiled import schedule_compiled
from cipheur.graph_features import FeatureRuleProgram,schedule_feature_program
from tests.test_compiled_v03 import graph,op
class ScoreSliceTests(unittest.TestCase):
 def test_defined_programs_keep_every_action_score_after_slicing(self):
  rng=random.Random(20261003)
  root=op('root');neighbors=op('neighbors',root);edges=op('induced_edges',neighbors)
  fs=[{'name':'E','expression':op('count',edges)},{'name':'L','expression':op('greedy_independent_weight',neighbors)},{'name':'U','expression':op('clique_cover_weight',neighbors)}]
  rules=['weight','weight/max(1,degree)','weight-conflict_weight','max_conflict_weight','compatible_weight','remaining_count+station_gap-satellite_gap','weight/max(weight,L)','weight/max(weight,U)','weight-E/max(1,degree)','weight/(1+abs(U-L))','duration','weight if remaining_count>12 else weight+L','weight+U if degree>2 else max(weight,L)']
  for j in range(30):
   n=rng.randrange(2,26);g=graph([rng.random()*10+.01 for _ in range(n)],[(i,k) for i in range(n) for k in range(i+1,n) if rng.random()<.35])
   for rule in rules:
    p=FeatureRuleProgram('slice',fs,rule);a=schedule_feature_program(g,p);b=schedule_compiled(g,p,score_slice=True)
    for key in ('selected','trace','value','feasible'):self.assertEqual(a[key],b[key],(j,rule))
    self.assertEqual(b['feature_work'],sum(b[key] for key in ('initialization_work','update_work','query_work')))
 def test_untaken_branch_does_not_evaluate_its_primitive(self):
  root=op('root');g=graph([1,2,3,4,5,6],[(0,1),(0,2),(1,2),(2,3),(4,5)])
  p=FeatureRuleProgram('branch',[{'name':'cover','expression':op('clique_cover_weight',op('available'))}],'weight if remaining_count>=0 else cover')
  b=schedule_compiled(g,p,score_slice=True);a=schedule_compiled(g,FeatureRuleProgram('simple',[],'weight'),score_slice=True)
  self.assertEqual(a['trace'],b['trace'])
  self.assertNotIn('aggregation',b['feature_primitives'])
 def test_unused_expensive_feature_is_not_executed(self):
  root=op('root');g=graph([1,2,3,4,5,6],[(0,1),(0,2),(1,2),(2,3),(4,5)])
  p=FeatureRuleProgram('weight',[{'name':'unused','expression':op('clique_cover_weight',op('available'))}],'weight')
  a=schedule_compiled(g,p);b=schedule_compiled(g,p,score_slice=True)
  self.assertEqual(a['trace'],b['trace']);self.assertLess(b['feature_work'],a['feature_work'])
  self.assertEqual(b['compilation']['scorer_inputs'],['weight']);self.assertEqual(b['compilation']['lowered_aggregates'],[])
if __name__=='__main__':unittest.main()
