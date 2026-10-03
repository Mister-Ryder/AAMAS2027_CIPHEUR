import unittest
from cipheur.advanced_baselines import metis_input,parse_solution,solver_command
from tests.test_compiled_v03 import graph
class PublishedSolverAdapterTests(unittest.TestCase):
 def test_exact_integer_scaling_and_boundaries(self):
  g=graph([.25,1.5,2.75,3.0],[(0,1),(1,2)]);text,active,scale=metis_input(g,['0'],['3']);self.assertEqual(scale,4);self.assertEqual(active,['2']);self.assertEqual(text,'1 0 10\n11 \n')
 def test_formats_are_explicit_and_invalid_outputs_rejected(self):
  self.assertEqual(parse_solution('1 1 0',['a','b','c'],'partition_flags'),['a','b'])
  self.assertEqual(parse_solution('1 2',['a','b','c'],'one_based_ids'),['a','b'])
  for value,fmt in [('1 2','partition_flags'),('0','one_based_ids'),('1 1','one_based_ids')]:
   with self.assertRaises(ValueError):parse_solution(value,['a','b','c'],fmt)
 def test_single_thread_concurrent_chils_is_explicit(self):
  command,fmt=solver_command('CHILS','CHILS','g','s',5,2);self.assertEqual(fmt,'one_based_ids');self.assertIn('-c',command);self.assertEqual(command[command.index('-c')+1],'1')
  ils,_=solver_command('CHILS','CHILS_ILS','g','s',5,2);self.assertEqual(ils[ils.index('-p')+1],'1');self.assertEqual(command[command.index('-p')+1],'4')
if __name__=='__main__':unittest.main()
