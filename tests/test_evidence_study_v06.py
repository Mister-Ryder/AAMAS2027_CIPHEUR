"""Check query eligibility and honest quotas independently of oracle outcomes."""
import unittest
from cipheur.evidence_study_v06 import queries, BASE
from cipheur.model import Graph, Contact, temporal_graph
from cipheur.representation import vector_key


def graph(n, edges):
    return Graph("test", tuple(Contact(str(i), 1, "s"+str(i), "g"+str(i), 0, 1)
                               for i in range(n)), frozenset(edges))


class QueryPlanTests(unittest.TestCase):
    def test_control_and_alias_groups_keep_eligible_common_edges(self):
        left = graph(5, {("0", "1"), ("1", "2"), ("2", "0"), ("2", "3")})
        right = graph(5, set(left.edges) | {("3", "4")})
        planned, quota = queries([left, right], "fixed-plan")
        self.assertEqual(queries([left, right], "fixed-plan"), (planned, quota))
        self.assertEqual({tuple((q['a'], q['b'])) for q in planned}, set(left.edges))
        self.assertEqual(len(planned), len({(q['a'], q['b']) for q in planned}))
        for q in planned:
            actual = [vector_key(BASE.evaluate_features(g,q['a'],set(g.nodes))) ==
                      vector_key(BASE.evaluate_features(g,q['b'],set(g.nodes)))
                      for g in (left,right)]
            self.assertEqual(q['base_alias_by_side'], actual)
            self.assertEqual(q['kind'], 'alias' if any(actual) else 'control')
        self.assertEqual(sum(q['shortfall'] for q in quota.values()), 12)

    def test_no_competing_actions_are_retained_as_shortfalls(self):
        planned, quota = queries([graph(3,set())], "empty")
        self.assertEqual(planned, [])
        self.assertEqual(quota['alias'], {'eligible':0,'planned':0,'shortfall':8})
        self.assertEqual(quota['control'], {'eligible':0,'planned':0,'shortfall':8})

    def test_unit_contacts_preserve_static_physical_intervention(self):
        contacts = tuple(Contact(str(i),1,f'S{i%3}',f'G{i%2}',i/4,i/4+1)
                         for i in range(8))
        left, right = (temporal_graph('left',contacts,0,0),
                       temporal_graph('right',contacts,1,0))
        self.assertEqual(left.contacts,right.contacts)
        self.assertLessEqual(left.edges,right.edges)
        planned, quota = queries([left,right], 'physical')
        self.assertTrue(all(q['b'] in left.adj[q['a']] and
                            q['b'] in right.adj[q['a']] for q in planned))
        self.assertEqual(sum(v['planned'] for v in quota.values()),len(planned))


if __name__ == '__main__': unittest.main()
