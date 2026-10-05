import copy
from fractions import Fraction
import time
import unittest

from cipheur.online_v2.typed import (PatchEvaluator, compile_rule, validate_recipe,
                                     validate_feature_expression, graph_operation_library)

def op(name, *args): return {'op': name, 'args': list(args)}

def recipe(features=None, rule='c0 * weight / (degree + 1)'):
    return {'name': 'typed_fixture', 'features': [] if features is None else features, 'rule': rule,
            'patch_policy': {'anchor': 'uniform', 'destroy_count': 2, 'patch_cap': 16, 'expand_hops': 2, 'reconstruction': 'greedy'},
            'evaluation_plan': {'feature_scope': 'patch', 'max_feature_cpu_fraction': .1, 'lazy': True},
            'adaptation_template': {'mutation_scales': [.1, .1, .1, .1], 'stagnation_trials': 8, 'action': 'mutate'},
            'coefficients': [1, 0, 0, 0], 'rationale': 'Unit-test graph, not an experiment result.'}

def fixture(program, active=None, patch_init=None, metadata=None, deadline=None):
    # root0 has neighbors1,2; induced-neighbor edge1-2, plus1-3/2-4/3-4 outside one hop.
    adj = {0: {1, 2}, 1: {0, 2, 3}, 2: {0, 1, 4}, 3: {1, 4}, 4: {2, 3}, 5: set()}
    weights = {0: 8_000_000, 1: 5_000_000, 2: 7_000_000, 3: 2_000_000, 4: 11_000_000, 5: 3_000_000}
    return PatchEvaluator(adj, weights, program, program['coefficients'], set(adj) if active is None else active,
                          {0, 3, 5} if patch_init is None else patch_init,
                          {'weight_scale': 1_000_000} if metadata is None else metadata, deadline)

class OnlineTypedTests(unittest.TestCase):
    def test_two_hop_and_incident_are_distinct_actual_graph_features(self):
        ns = op('neighbors', op('root'))
        twohop = op('difference', op('neighbors_of_set', ns), op('union', ns, op('singleton', op('root'))))
        p = recipe([{'name': 'twohop_weight', 'expression': op('sum_weights', twohop)},
                    {'name': 'induced_count', 'expression': op('count', op('induced_edges', ns))},
                    {'name': 'incident_count', 'expression': op('count', op('incident_edges', ns))},
                    {'name': 'incident_min', 'expression': op('edge_min_weight_sum', op('incident_edges', ns))}],
                   'twohop_weight + incident_count - induced_count')
        e = fixture(p); values = e.feature_values(0)
        self.assertEqual(values['twohop_weight'], Fraction(13))
        self.assertEqual(values['induced_count'], 1)
        self.assertEqual(values['incident_count'], 5)
        self.assertEqual(values['incident_min'], Fraction(26))
        self.assertEqual(e.score(0), 17.)
        self.assertTrue(all(isinstance(v, Fraction) for v in values.values()))

    def test_lazy_unused_bad_feature_is_never_computed(self):
        unused = op('div', op('count', op('incident_edges', op('available'))), {'op': 'const', 'value': 0})
        p = recipe([{'name': 'unused', 'expression': unused}], 'weight')
        e = fixture(p)
        self.assertEqual(e.score(0), 8.)
        self.assertNotIn('incident_edges', e.stats['op_counts'])
        self.assertEqual(e.stats['evaluations'], 1)
        self.assertEqual(e.stats['feature_reads'], {'unused': 0})
        with self.assertRaises(ValueError): e.feature_values(0)

    def test_score_feature_reads_are_separate_from_diagnostic_and_cache(self):
        p = recipe([{'name': 'structure', 'expression': op('count', op('incident_edges', op('neighbors', op('root'))))},
                    {'name': 'unused', 'expression': op('count', op('available'))}], 'structure + structure')
        e = fixture(p)
        self.assertEqual(e.score(0), 10.)
        # Same Name is resolved once in each numeric evaluation, even if the
        # expression uses it twice; cached feature values still count as reads.
        self.assertEqual(e.stats['feature_reads'], {'structure': 1, 'unused': 0})
        e.feature_values(0)
        self.assertEqual(e.stats['feature_reads'], {'structure': 1, 'unused': 0})
        self.assertEqual(e.stats['diagnostic_feature_reads'], {'structure': 1, 'unused': 1})
        self.assertEqual(e.score(0), 10.)
        self.assertEqual(e.stats['feature_reads'], {'structure': 2, 'unused': 0})

    def test_lazy_conditional_does_not_evaluate_unreached_branch(self):
        p = recipe([{'name': 'bad', 'expression': op('div', {'op': 'const', 'value': 1}, {'op': 'const', 'value': 0})}],
                   'weight if degree > 0 else bad')
        self.assertEqual(fixture(p).score(0), 8.)

    def test_remove_invalidates_cache_and_edges_require_both_active_endpoints(self):
        p = recipe([{'name': 'incident_count', 'expression': op('count', op('incident_edges', op('neighbors', op('root'))))},
                    {'name': 'init_weight', 'expression': op('sum_weights', op('patch_init'))}], 'incident_count + init_weight')
        e = fixture(p); self.assertEqual(e.score(0), 18.)  # 5edges + init8+2+3
        e.remove({2, 3}); values = e.feature_values(0)
        self.assertEqual(values['incident_count'], 1); self.assertEqual(values['init_weight'], 13)
        self.assertEqual(values['degree'], 1); self.assertEqual(values['active_count'], 4)
        self.assertEqual(values['compatible_weight'], 14)  # nodes4,5; closed neighborhood excludesroot
        self.assertEqual(e.score(0), 14.)
        with self.assertRaises(ValueError): e.score(2)

    def test_initial_P_is_immutable_but_structural_ops_use_only_residual(self):
        # P={0,1,3}; removed1 previously connected to active2, so traversing
        # removed1 would incorrectly include2 after also removingroot0's2.
        initial = op('patch_init')
        p = recipe([
            {'name': 'init_count', 'expression': op('count', initial)},
            {'name': 'init_sum', 'expression': op('sum_weights', initial)},
            {'name': 'used_sum', 'expression': op('sub', op('sum_weights', initial), op('sum_weights', op('intersection', initial, op('available'))))},
            {'name': 'init_neighbor_sum', 'expression': op('sum_weights', op('neighbors_of_set', initial))},
            {'name': 'init_induced', 'expression': op('count', op('induced_edges', initial))},
            {'name': 'init_incident', 'expression': op('count', op('incident_edges', initial))},
        ], 'used_sum')
        e = fixture(p, patch_init={0, 1, 3})
        before = e.feature_values(0)
        self.assertEqual(before['init_count'], 3); self.assertEqual(before['init_sum'], 15)
        self.assertEqual(before['used_sum'], 0); self.assertEqual(before['init_induced'], 2)
        e.remove({1, 2})
        after = e.feature_values(0)
        self.assertEqual(e.patch_init, frozenset({0, 1, 3}))
        self.assertEqual(after['init_count'], 3); self.assertEqual(after['init_sum'], 15)
        self.assertEqual(after['used_sum'], 5)
        # Remaining P roots0,3: only3-4 exists; removed1 contributes no links.
        self.assertEqual(after['init_neighbor_sum'], 11)
        self.assertEqual(after['init_induced'], 0); self.assertEqual(after['init_incident'], 1)
        self.assertEqual(e.score(0), 5.)

    def test_cover_and_greedy_intersect_initial_P_with_current_active(self):
        p = recipe([{'name': 'cover', 'expression': op('clique_cover_weight', op('patch_init'))},
                    {'name': 'greedy', 'expression': op('greedy_independent_weight', op('patch_init'))},
                    {'name': 'initial_max', 'expression': op('max_weight', op('patch_init'))}], 'cover + greedy')
        e = fixture(p, patch_init={0, 3, 4})
        before = e.feature_values(0)
        self.assertEqual(before['cover'], 19); self.assertEqual(before['greedy'], 19)
        e.remove({4}); after = e.feature_values(0)
        self.assertEqual(after['cover'], 10); self.assertEqual(after['greedy'], 10)
        self.assertEqual(after['initial_max'], 11)
        self.assertIn('intersect active', graph_operation_library()['clique_cover_weight']['semantics'])

    def test_explicit_scale_and_duration_metadata_are_exact(self):
        p = recipe([{'name': 'products', 'expression': op('edge_weight_product_sum', op('induced_edges', op('neighbors', op('root'))))}], 'products')
        e = fixture(p, metadata={'weight_scale': 1_000_000, 'duration': {0: Fraction(8000001, 1000000)},
                                 'station_gap': {0: 340}, 'satellite_gap': 150})
        values = e.feature_values(0)
        self.assertEqual(values['products'], Fraction(35)); self.assertEqual(values['duration'], Fraction(8000001, 1000000))
        self.assertEqual(values['weight'], 8); self.assertEqual(values['station_gap'], 340)
        self.assertEqual(values['satellite_gap'], 150)
        self.assertEqual(values['conflict_weight'], values['neighbor_weight_sum'])
        self.assertEqual(fixture(recipe(rule='weight'), metadata={}).score(0), 8_000_000.)

    def test_illegal_rules_and_feature_types_are_rejected(self):
        for rule in ["__import__('os')", 'weight.real', 'weight[0]', '[weight][0]', 'weight ** 2',
                     '(lambda: 1)()', 'sum(x for x in [])', 'unknown + 1', 'True', 'weight > 0', 'min(weight)', 'abs(weight,degree)', 'max(weight=1)', 'c4']:
            with self.subTest(rule=rule), self.assertRaises(ValueError): compile_rule(rule, [])
        for expr in [op('neighbors_of_set', op('root')), op('incident_edges', op('root')), op('sum_weights', op('incident_edges', op('available'))),
                     op('count', op('root')), op('unknown'), {'op': 'const', 'value': True}, {'op': 'root', 'python': 'bad'}]:
            with self.subTest(expr=expr), self.assertRaises(ValueError): validate_feature_expression(expr)
        expr = {'op': 'const', 'value': 1}
        for _ in range(8): expr = op('abs', expr)
        with self.assertRaises(ValueError): validate_feature_expression(expr)

    def test_complete_numeric_scoring_blocks_can_be_composed(self):
        # Six full coefficient-bound score blocks are more than48 semantic
        # expressions, but valid under the independent numeric-rule budget.
        block = '(c0 * weight / (degree + 1) + c1 * conflict_weight / (weight + 1) + c2 * max_conflict_weight / (weight + 1) + c3 * station_gap / (satellite_gap + 1))'
        p = recipe(rule=' + '.join([block] * 6))
        validate_recipe(p)
        e = fixture(p, metadata={'weight_scale': 1_000_000, 'station_gap': 340, 'satellite_gap': 150})
        self.assertAlmostEqual(e.score(0), 16.)

    def test_numeric_limits_do_not_relax_safe_AST_or_feature_limits(self):
        def balanced_rules(leaves):
            if len(leaves) == 1: return leaves[0]
            middle = len(leaves) // 2
            return '(' + balanced_rules(leaves[:middle]) + '+' + balanced_rules(leaves[middle:]) + ')'
        #128 leaves +127 binary operators +1 abs call =256 semantic nodes.
        exactly256 = 'abs(' + balanced_rules(['weight'] * 128) + ')'
        compile_rule(exactly256, [])
        with self.assertRaisesRegex(ValueError, 'exceeds256'):
            compile_rule('abs(' + exactly256 + ')', [])
        exactly_depth16 = 'weight'
        for _ in range(15): exactly_depth16 = 'abs(' + exactly_depth16 + ')'
        compile_rule(exactly_depth16, [])
        with self.assertRaisesRegex(ValueError, 'depth16'):
            compile_rule('abs(' + exactly_depth16 + ')', [])
        for rule in ('round(weight)', 'eval(weight)', 'weight.real', 'weight ** 2'):
            with self.subTest(rule=rule), self.assertRaises(ValueError): compile_rule(rule, [])
        with self.assertRaises(ValueError): compile_rule('weight' + ' ' * 2000, [])
        def balanced_features(leaves):
            if len(leaves) == 1: return leaves[0]
            middle = len(leaves) // 2
            return op('add', balanced_features(leaves[:middle]), balanced_features(leaves[middle:]))
        #24 leaves +23 add operations +1 abs =48; another abs must fail.
        feature48 = op('abs', balanced_features([{'op': 'const', 'value': 1} for _ in range(24)]))
        validate_feature_expression(feature48)
        with self.assertRaisesRegex(ValueError, 'exceeds48'):
            validate_feature_expression(op('abs', feature48))

    def test_recipe_strict_keys_bounds_and_reserved_names(self):
        good = recipe(); saved = validate_recipe(good); saved['name'] = 'other'; self.assertEqual(good['name'], 'typed_fixture')
        bads = [dict(good, extra='rejected'), dict(good, coefficients=[0, 0, 0, 17]),
                dict(good, features=[{'name': 'weight', 'expression': {'op': 'const', 'value': 1}}])]
        bad = copy.deepcopy(good); bad['patch_policy']['patch_cap'] = 65; bads.append(bad)
        bad = copy.deepcopy(good); bad['evaluation_plan']['lazy'] = False; bads.append(bad)
        bad = copy.deepcopy(good); bad['adaptation_template']['mutation_scales'] = [0, -1, 0, 0]; bads.append(bad)
        for value in bads:
            with self.assertRaises(ValueError): validate_recipe(value)
        self.assertIn('incident_edges', graph_operation_library())

    def test_oversized_patch_is_rejected_and_deadline_is_cpu_based(self):
        p = recipe()
        with self.assertRaises(ValueError): PatchEvaluator({n: set() for n in range(65)}, {n: 1 for n in range(65)}, p, [1,0,0,0], set(range(65)), set())
        with self.assertRaises(TimeoutError): fixture(p, deadline=time.process_time() - 1)
        e = fixture(p); e.deadline = lambda: True
        with self.assertRaises(TimeoutError): e.score(0)
        e.deadline = None; e.score(0)
        self.assertGreaterEqual(e.stats['feature_cpu'], 0)
        self.assertGreater(e.stats['ops'], 0); self.assertEqual(e.stats['scorecalls'], 1)

if __name__ == '__main__': unittest.main()
