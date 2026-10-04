from fractions import Fraction
import unittest
from cipheur.advanced_baselines import metis_input as original_input
from cipheur.advanced_baselines_v06 import metis_input,run_solver
from cipheur.model import Contact,Graph

class ExactNativeEncodingTests(unittest.TestCase):
    def graph(self,weights):
        return Graph('weights',tuple(Contact(str(i),w,'S',str(i),0,1) for i,w in enumerate(weights)),frozenset({('0','1')}))
    def test_small_exact_input_matches_original(self):
        g=self.graph([Fraction(1,4),Fraction(3,4)])
        old=original_input(g)
        new=metis_input(g,'CHILS')
        self.assertEqual(old,new[:3])
        self.assertEqual(new[2],4)
    def test_large_total_is_solver_specific_not_global_relaxation(self):
        g=self.graph([2000000000,2000000000])
        text,nodes,scale,contract=metis_input(g,'CHILS')
        self.assertIn('2000000000 2',text)
        self.assertEqual(scale,1)
        self.assertIn('signed64',contract)
        with self.assertRaises(ValueError):original_input(g)
        for name in ('M2WIS','Struction','WeightedBR'):
            row=run_solver(g,'not_accessed',name)
            self.assertEqual(row['status'],'encoding_not_supported')
            self.assertIsNone(row['value'])
            self.assertFalse(row['solver_invoked'])
    def test_signed64_overflow_still_rejected(self):
        g=self.graph([2**62,2**62])
        with self.assertRaisesRegex(ValueError,'signed64'):metis_input(g,'CHILS')

if __name__=='__main__':unittest.main()
