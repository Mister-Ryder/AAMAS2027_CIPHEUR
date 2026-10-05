"""Kernel integration fixtures, not LLM outputs or performance evidence."""
from copy import deepcopy
from fractions import Fraction
import json
import unittest
import numpy as np
from cipheur.online_v2.solver import IntGraph,Incumbent,solve,feasible,choose_patch
import random
import time
from unittest.mock import patch
from cipheur.online_v2.controller import OnlineController

def fixture_recipe():
    return dict(name='synthetic_exchange_fixture',features=[],rule='weight/(1+degree)',
        coefficients=[1.,0.,0.,0.],rationale='Handwritten integration fixture; no LLM provenance.',
        patch_policy=dict(anchor='uniform',destroy_count=1,patch_cap=16,expand_hops=1,reconstruction='exchange'),
        evaluation_plan=dict(feature_scope='patch',max_feature_cpu_fraction=.3,lazy=True),
        adaptation_template=dict(mutation_scales=[.2]*4,stagnation_trials=8,action='mutate'))

def graph():
    return IntGraph({0:{1,2},1:{0},2:{0}}, {0:9000000,1:5000000,2:5000000},['a','b','c'],
        dict(weight_scale=1000000,duration={0:Fraction(9),1:Fraction(5),2:Fraction(5)},
            station_gap={0:100,1:100,2:100},satellite_gap=150,
            station={0:'g',1:'g',2:'g'},satellite={0:'s',1:'s',2:'s'}),{},np.array([0,0]),np.array([1,2]))

class KernelTests(unittest.TestCase):
    def test_incremental_exchange_value_and_blocker_counts(self):
        g=graph();state=Incumbent(g,[0]);self.assertEqual(state.blockers,[0,1,1])
        state.commit({0},{1,2});self.assertEqual(state.value,10000000)
        self.assertEqual(state.blockers,[2,0,0]);self.assertTrue(feasible(g,state.selected))
        self.assertFalse(state.commit({1,2},{0}));self.assertEqual(state.value,10000000)

    def test_full_current_solve_updates_and_commits_without_oracle(self):
        g=graph();r=solve(g,[fixture_recipe()],.15,2,instance_id='unit-instance')
        self.assertEqual(r['seed_value_ticks'],9000000)
        self.assertEqual(r['value_ticks'],10000000)
        self.assertTrue(r['feasible']);self.assertGreater(r['controller']['update_count'],8)
        self.assertGreater(r['controller']['mutation_count'],0)
        self.assertEqual(r['online_llm_calls'],0);self.assertEqual(r['external_oracle_calls'],0)
        self.assertTrue(all(a['value_ticks']<=b['value_ticks'] for a,b in zip(r['best_so_far'],r['best_so_far'][1:])))
        json.dumps(r)

    def test_patch_outside_is_exactly_compatible(self):
        g=graph();state=Incumbent(g,[1,2]);recipe=fixture_recipe()
        for anchor in ('uniform','blocked_gain','rejection_frontier','resource_boundary'):
            recipe['patch_policy']['anchor']=anchor
            destroy,patch,_=choose_patch(state,recipe,random.Random(3),[])
            outside=state.selected-destroy
            self.assertTrue(destroy<=patch)
            self.assertFalse(patch&outside)
            self.assertTrue(all(not(g.adjacency[v]&outside) for v in patch))

    def test_parent_race_charges_both_and_commits_only_winner(self):
        class RaceController(OnlineController):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs)
                self.child=self.mutate(self.population[0],random.Random(4))
            def select(self,*args,**kwargs):
                return self.child
        calls=[]
        def fake_reconstruct(g,p,recipe,coeff,rng,deadline):
            calls.append((set(p),rng.getstate(),deadline))
            start=time.process_time()
            while time.process_time()-start<.001:pass
            chosen={1,2} if len(calls)==2 else {0}
            value=sum(g.weights[v] for v in chosen)
            return chosen,dict(status='complete',rank_value_ticks=value,exchange_added_ticks=0,
                rank_commits=len(chosen),rank_trace=[],feature_stats={'feature_cpu':.0001,'feature_reads':{}},
                reconstruction_cpu_seconds=time.process_time()-start)
        with patch('cipheur.online_v2.solver.OnlineController',RaceController),patch(
                'cipheur.online_v2.solver.reconstruct',side_effect=fake_reconstruct),patch(
                'cipheur.online_v2.solver.shared_exchange',return_value=0):
            result=solve(graph(),[fixture_recipe()],.03,2,
                controller_config={'paired_race':True,'evolve_every':64})
        raced=[r for r in result['trials'] if r['paired_race']]
        self.assertEqual(len(raced),1)
        row=raced[0];race=row['paired_race']
        self.assertEqual(calls[0][0],calls[1][0]);self.assertEqual(calls[0][1],calls[1][1])
        self.assertEqual(result['value_ticks'],10000000)
        self.assertTrue(row['accepted']);self.assertFalse(row['child_accepted'])
        self.assertEqual(row['committed_genome_id'],race['parent_id'])
        self.assertEqual(row['raw_gain_ticks'],0);self.assertEqual(row['accepted_gain_ticks'],1000000)
        self.assertGreater(row['cpu_seconds'],race['parent_cpu_seconds'])
        self.assertGreaterEqual(race['parent_cpu_seconds'],.001)
        self.assertEqual(result['value_ticks']-result['seed_value_ticks'],
            result['stats']['operator_gain_ticks']+result['stats'].get('shared_exchange_gain_ticks',0))
        self.assertEqual(result['stats']['rank_commits'],sum(r['rank_commits']+
            (r['paired_race'] or {}).get('parent_rank_commits',0) for r in result['trials']))

    def test_evidence_uses_current_features_and_separate_representation_namespaces(self):
        recipes=[]
        for name,op in [('current_count','count'),('current_weight','sum_weights')]:
            r=fixture_recipe();r['name']=name
            r['features']=[{'name':name,'expression':{'op':op,'args':[{'op':'available','args':[]}]}}]
            r['rule']='weight/(1+degree)+c0*'+name
            recipes.append(r)
        result=solve(graph(),recipes,.2,2,mode='fixed')
        gates=[c['archive_gate'] for c in result['certificates'] if 'archive_gate' in c]
        self.assertGreater(len(gates),0)
        expected={g['representation_hash']:g['recipe']['features'][0]['name']
            for g in result['controller']['population']}
        for gate in gates:
            self.assertEqual(len(gate['coordinate_names']),10)
            self.assertEqual(gate['coordinate_names'][-1],expected[gate['representation_hash']])

if __name__=='__main__':unittest.main()
