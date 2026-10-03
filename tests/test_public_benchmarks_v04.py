import unittest,random
from cipheur.public_benchmarks import parse_dimacs_binary,parse_cnf
class PublicParserTests(unittest.TestCase):
 def test_binary_roundtrip_and_edge_count_rejection(self):
  r=random.Random(3)
  for n in range(1,25):
   e={(j,i) for i in range(n) for j in range(i) if r.random()<.4};p=f'p edge {n} {len(e)}\n'.encode();b=bytearray()
   for i in range(n):
    row=bytearray((i+8)//8)
    for j in range(i):
     if (j,i) in e:row[j//8]|=1<<(7-j%8)
    b.extend(row)
   payload=str(len(p)).encode()+b'\n'+p+bytes(b);nn,ee,_=parse_dimacs_binary(payload);self.assertEqual((nn,ee),(n,frozenset(e)))
   with self.assertRaises(ValueError):parse_dimacs_binary(payload[:-1])
 def test_sat_reduction_preserves_satisfiable_upper_and_unsat_gap(self):
  from itertools import combinations
  for raw,opt in [(b'p cnf 2 2\n1 2 0\n-1 2 0\n',2),(b'p cnf 1 2\n1 0\n-1 0\n',1)]:
   n,e,m=parse_cnf(raw);best=max(len(c) for k in range(n+1) for c in combinations(range(n),k) if all(tuple(sorted(x)) not in e for x in combinations(c,2)));self.assertEqual(best,opt);self.assertGreaterEqual(m['unit_weight_upper'],best)
 def test_official_satlib_percent_end_marker_is_not_an_empty_clause(self):
  n,e,m=parse_cnf(b'p cnf 2 2\n1 2 0\n-1 2 0\n%\n0\n');self.assertEqual(n,4);self.assertEqual(m['clauses'],2)
 def test_invalid_literal_and_missing_clause_rejected(self):
  for raw in (b'p cnf 1 1\n2 0\n',b'p cnf 2 2\n1 0\n'):
   with self.assertRaises(ValueError):parse_cnf(raw)
if __name__=='__main__':unittest.main()
