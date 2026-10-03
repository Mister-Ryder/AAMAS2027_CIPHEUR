import unittest
from itertools import combinations
from cipheur.model import Contact,Graph
from cipheur.graph_features import FeatureRuleProgram,schedule_feature_program
from cipheur.compiled import schedule_compiled

class NeighborhoodTools(unittest.TestCase):
    def test_checked_neighborhood_envelope_and_completion(self):
        contacts=tuple(Contact(str(i),float(i+1),'s'+str(i),'g'+str(i),0,1) for i in range(5))
        possible=list(combinations([str(i) for i in range(1,5)],2))
        expressions=[{'name':name,'expression':{'op':op,'args':[{'op':'neighbors','args':[{'op':'root','args':[]}]}]}}
            for name,op in [('upper','clique_cover_weight'),('lower','greedy_independent_weight')]]
        program=FeatureRuleProgram('interval',expressions,'weight/max(1,upper)')
        for mask in range(1<<len(possible)):
            edges={('0',str(i)) for i in range(1,5)}|{e for k,e in enumerate(possible) if mask&(1<<k)}
            graph=Graph('test',contacts,frozenset(edges))
            values=program.evaluate_features(graph,'0',set(graph.nodes))
            best=max(graph.value(selected) for bits in range(16)
                if graph.feasible(selected:=[str(i+1) for i in range(4) if bits&(1<<i)]))
            self.assertLessEqual(values['lower'],best)
            self.assertGreaterEqual(values['upper'],best)
            reference=schedule_feature_program(graph,program)
            compiled=schedule_compiled(graph,program)
            self.assertEqual(reference['trace'],compiled['trace'])

if __name__=='__main__':unittest.main()
