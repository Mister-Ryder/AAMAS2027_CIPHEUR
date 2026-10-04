"""Independent-verifier checks against complete small graph enumeration."""
from fractions import Fraction
import random
import unittest

from scripts.verify_public_alias_v05 import exact_alpha,unit_upper_decision,VerificationLimit


def fixture(n,seed,unit=False):
    randomizer=random.Random(seed)
    nodes={str(v):{"weight":1 if unit else randomizer.randrange(1,10)/2} for v in range(n)}
    adj={v:set() for v in nodes};vertices=tuple(nodes)
    for i,v in enumerate(vertices):
        for u in vertices[i+1:]:
            if randomizer.random()<.43:adj[v].add(u);adj[u].add(v)
    return nodes,adj,vertices


def brute(nodes,adj,vertices):
    values=[]
    for mask in range(1<<len(vertices)):
        chosen=[v for i,v in enumerate(vertices) if mask&(1<<i)]
        if not any(u in adj[v] for i,v in enumerate(chosen) for u in chosen[i+1:]):
            values.append(sum((Fraction(nodes[v]["weight"]) for v in chosen),Fraction(0)))
    return max(values)


class IndependentVerifierTests(unittest.TestCase):
    def test_weighted_recurrence_matches_full_enumeration(self):
        for seed in range(20):
            n=seed%10+1;nodes,adj,vertices=fixture(n,seed)
            result,states=exact_alpha(nodes,adj,vertices)
            self.assertEqual(result,brute(nodes,adj,vertices));self.assertGreater(states,0)

    def test_unit_colouring_proves_exact_upper_and_rejects_false_upper(self):
        for seed in range(20):
            n=seed%11+1;nodes,adj,vertices=fixture(n,seed,unit=True)
            optimum=brute(nodes,adj,vertices)
            self.assertTrue(unit_upper_decision(nodes,adj,vertices,optimum)[0])
            self.assertFalse(unit_upper_decision(nodes,adj,vertices,optimum-1)[0])

    def test_verification_limit_is_explicit(self):
        nodes,adj,vertices=fixture(6,1,unit=True)
        with self.assertRaises(VerificationLimit):exact_alpha(nodes,adj,vertices,max_states=0)
        with self.assertRaises(VerificationLimit):unit_upper_decision(nodes,adj,vertices,1,max_states=0)


if __name__=="__main__":unittest.main()
