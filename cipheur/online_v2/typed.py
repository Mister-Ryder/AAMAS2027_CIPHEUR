"""Safe typed graph recipes for current-instance, at-most64-node patches.

Graph aggregates use integer input weights and explicit ``weight_scale``;
diagnostics are Fractions. Float conversion happens only for ranking. Active
sets are never truncated. Feature evaluation is lazy and caches belong to one
active snapshot. This module has no model, oracle or optimizer dependency.
"""
from __future__ import annotations
import ast
import copy
from dataclasses import dataclass
from fractions import Fraction
import keyword
import math
import re
import time
from typing import Any

MAX_PATCH = 64
MAX_FEATURES = 6
MAX_EXPRESSION_NODES = 48
MAX_EXPRESSION_DEPTH = 8
# Numeric ranking rules compose several complete scoring blocks; their safe
# AST budget is separate from the graph-feature operation budget above.
MAX_RULE_NODES = 256
MAX_RULE_DEPTH = 16
BASE_NAMES = ('weight', 'duration', 'degree', 'conflict_weight', 'max_conflict_weight',
              'compatible_weight', 'station_gap', 'satellite_gap', 'remaining_count')
ALIASES = {'neighbor_weight_sum': 'conflict_weight', 'neighbor_max_weight': 'max_conflict_weight',
           'active_count': 'remaining_count'}
COEFFICIENT_NAMES = tuple('c' + str(i) for i in range(4))
FUNCTIONS = ('min', 'max', 'abs')
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

GRAPH_OPERATION_TYPES = {
    'root': ((), 'Node'), 'available': ((), 'NodeSet'), 'patch_init': ((), 'NodeSet'),
    'neighbors': (('Node',), 'NodeSet'), 'neighbors_of_set': (('NodeSet',), 'NodeSet'),
    'singleton': (('Node',), 'NodeSet'), 'union': (('NodeSet', 'NodeSet'), 'NodeSet'),
    'intersection': (('NodeSet', 'NodeSet'), 'NodeSet'), 'difference': (('NodeSet', 'NodeSet'), 'NodeSet'),
    'induced_edges': (('NodeSet',), 'EdgeSet'), 'incident_edges': (('NodeSet',), 'EdgeSet'),
    'count': (('NodeSet|EdgeSet',), 'Number'), 'sum_weights': (('NodeSet',), 'Number'),
    'max_weight': (('NodeSet',), 'Number'), 'clique_cover_weight': (('NodeSet',), 'Number'),
    'greedy_independent_weight': (('NodeSet',), 'Number'),
    'edge_min_weight_sum': (('EdgeSet',), 'Number'), 'edge_weight_product_sum': (('EdgeSet',), 'Number'),
    'weight': (('Node',), 'Number'), 'duration': (('Node',), 'Number'), 'const': ((), 'Number'),
    'add': (('Number', 'Number'), 'Number'), 'sub': (('Number', 'Number'), 'Number'),
    'mul': (('Number', 'Number'), 'Number'), 'div': (('Number', 'Number'), 'Number'),
    'min': (('Number', 'Number'), 'Number'), 'max': (('Number', 'Number'), 'Number'),
    'abs': (('Number',), 'Number'),
}


def graph_operation_library():
    descriptions = {
        'available': 'Current residual active node set.',
        'patch_init': 'Immutable initial patch P, including nodes already removed from residual active.',
        'count': 'Cardinality of the supplied set; count(patch_init) stays fixed.',
        'sum_weights': 'Sum original node weights for the supplied set; sum_weights(patch_init) stays fixed.',
        'max_weight': 'Maximum original node weight in the supplied set, including removed initial-P nodes.',
        'neighbors_of_set': 'Union of current residual neighbors of inputSet intersect active; removed input nodes are not traversed.',
        'induced_edges': 'Edges induced by inputSet intersect active; both endpoints must be residual active.',
        'incident_edges': 'Current residual edges incident to inputSet intersect active; both endpoints must be residual active.',
        'clique_cover_weight': 'Deterministic clique-cover weight on inputSet intersect active in the current residual graph.',
        'greedy_independent_weight': 'Deterministic greedy independent weight on inputSet intersect active in the current residual graph.',
    }
    return {op: {'arguments': list(args), 'result': kind,
                 **({'semantics': descriptions[op]} if op in descriptions else {})}
            for op, (args, kind) in GRAPH_OPERATION_TYPES.items()}


def _finite(value, name, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite numeric value')
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(name + ' is outside its declared bounds')
    return value


def _rational(value, name):
    if isinstance(value, Fraction): return value
    _finite(value, name)
    return Fraction(value) if type(value) is int else Fraction(str(value))


def _keys(value, expected, name):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(name + ' requires exactly ' + ', '.join(expected))


@dataclass(frozen=True)
class Expression:
    op: str
    args: tuple['Expression', ...]
    value: Fraction | None
    result_type: str
    depends_on_root: bool


def validate_feature_expression(expression):
    """Return an immutable, typechecked Number expression (48ops/depth8)."""
    nodes = 0
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_EXPRESSION_NODES or depth > MAX_EXPRESSION_DEPTH:
            raise ValueError('Feature expression exceeds48 operations or depth8')
        if not isinstance(item, dict) or not isinstance(item.get('op'), str):
            raise ValueError('Feature expressions must be operation objects')
        op = item['op']
        if op not in GRAPH_OPERATION_TYPES: raise ValueError('Unknown graph operation: ' + op)
        if op == 'const':
            _keys(item, ('op', 'value'), 'const')
            _finite(item['value'], 'const', -1e9, 1e9)
            return Expression(op, (), _rational(item['value'], 'const'), 'Number', False)
        if set(item) - {'op', 'args'}: raise ValueError('Undeclared feature-operation field')
        sources = item.get('args', [])
        if not isinstance(sources, list): raise ValueError('Feature args must be a list')
        wanted, result_type = GRAPH_OPERATION_TYPES[op]
        if len(sources) != len(wanted): raise ValueError(op + ' has incorrect arity')
        args = tuple(visit(source, depth + 1) for source in sources)
        if any(arg.result_type not in kind.split('|') for arg, kind in zip(args, wanted)):
            raise ValueError(op + ' has an incompatible argument type')
        return Expression(op, args, None, result_type, op == 'root' or any(a.depends_on_root for a in args))
    tree = visit(expression, 1)
    if tree.result_type != 'Number': raise ValueError('Feature must return Number')
    return tree


def compile_rule(rule, feature_names):
    """Compile only numeric arithmetic, bounded calls and numeric conditionals.

    The limit counts semantic expressions, excluding AST context/operator
    marker nodes:256 expressions, depth16. Feature expressions retain their
    independent48-operation/depth8 bound. No attributes, indexing, imports,
    comprehensions, assignment, exponentiation or executable function bodies.
    """
    if not isinstance(rule, str) or not rule.strip() or len(rule) > 2000:
        raise ValueError('Rule must be a nonempty bounded expression string')
    names = set(BASE_NAMES) | set(ALIASES) | set(COEFFICIENT_NAMES) | set(feature_names)
    if any(not isinstance(n, str) or not _IDENTIFIER.fullmatch(n) or n.startswith('__') or keyword.iskeyword(n) for n in names):
        raise ValueError('Invalid declared feature identifier')
    try: tree = ast.parse(rule, mode='eval')
    except (SyntaxError, RecursionError) as error: raise ValueError('Invalid rule syntax') from error
    visited = 0
    def infer(node, depth):
        nonlocal visited
        visited += 1
        if visited > MAX_RULE_NODES or depth > MAX_RULE_DEPTH:
            raise ValueError('Rule exceeds256 semantic expressions or depth16')
        if isinstance(node, ast.Constant):
            _finite(node.value, 'rule literal', -1e9, 1e9); return 'Number'
        if isinstance(node, ast.Name):
            if node.id not in names or node.id in FUNCTIONS: raise ValueError('Unknown numeric rule variable: ' + node.id)
            return 'Number'
        if isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            if infer(node.left, depth + 1) != 'Number' or infer(node.right, depth + 1) != 'Number': raise ValueError('Arithmetic needs Number')
            return 'Number'
        if isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub, ast.Not):
            kind = infer(node.operand, depth + 1)
            if type(node.op) is ast.Not:
                if kind != 'Bool': raise ValueError('not requires a comparison')
                return 'Bool'
            if kind != 'Number': raise ValueError('Unary arithmetic needs Number')
            return 'Number'
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords:
                raise ValueError('Only numeric min/max/abs calls allowed')
            expected = (1, 1) if node.func.id == 'abs' else (2, 8)
            if not expected[0] <= len(node.args) <= expected[1] or any(infer(a, depth + 1) != 'Number' for a in node.args):
                raise ValueError('Invalid numeric function arguments')
            return 'Number'
        if isinstance(node, ast.Compare):
            if any(type(op) not in (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq) for op in node.ops): raise ValueError('Invalid comparison operator')
            if infer(node.left, depth + 1) != 'Number' or any(infer(v, depth + 1) != 'Number' for v in node.comparators): raise ValueError('Comparison needs Number')
            return 'Bool'
        if isinstance(node, ast.BoolOp) and type(node.op) in (ast.And, ast.Or):
            if any(infer(v, depth + 1) != 'Bool' for v in node.values): raise ValueError('Boolean operator needs comparisons')
            return 'Bool'
        if isinstance(node, ast.IfExp):
            if infer(node.test, depth + 1) != 'Bool' or infer(node.body, depth + 1) != 'Number' or infer(node.orelse, depth + 1) != 'Number':
                raise ValueError('Conditional requires comparison and Number branches')
            return 'Number'
        raise ValueError('Disallowed rule syntax: ' + type(node).__name__)
    if infer(tree.body, 1) != 'Number': raise ValueError('Ranking rule must return Number')
    return compile(tree, '<online-v2-numeric-rule>', 'eval')


def _compile_features(features):
    if not isinstance(features, list) or len(features) > MAX_FEATURES: raise ValueError('At most6 declared features allowed')
    reserved = set(BASE_NAMES) | set(ALIASES) | set(COEFFICIENT_NAMES) | set(FUNCTIONS)
    compiled = {}
    for feature in features:
        _keys(feature, ('name', 'expression'), 'feature')
        name = feature['name']
        if not isinstance(name, str) or len(name) > 80 or not _IDENTIFIER.fullmatch(name) or name.startswith('__') or keyword.iskeyword(name) or name in reserved:
            raise ValueError('Invalid, duplicate or reserved feature name')
        reserved.add(name); compiled[name] = validate_feature_expression(feature['expression'])
    return compiled


def _program(program):
    if not isinstance(program.get('name'), str) or not program['name'].strip() or len(program['name']) > 200:
        raise ValueError('Program name must be a bounded nonempty string')
    if not isinstance(program.get('rationale'), str) or len(program['rationale']) > 20000:
        raise ValueError('Rationale must be a bounded string')
    features = _compile_features(program.get('features')); code = compile_rule(program.get('rule'), features)
    return features, code


def _coefficient_vector(values, name='coefficients', bounds=True):
    if not isinstance(values, list) or len(values) != 4: raise ValueError(name + ' requires4 numbers')
    for value in values: _finite(value, name, -16 if bounds else 0, 16 if bounds else None)
    return list(values)


def validate_recipe(recipe):
    """Strict public recipe schema; returns a defensive copy, never drops keys."""
    _keys(recipe, ('name', 'features', 'rule', 'patch_policy', 'evaluation_plan', 'adaptation_template', 'coefficients', 'rationale'), 'recipe')
    _program(recipe); _coefficient_vector(recipe['coefficients'])
    policy = recipe['patch_policy']
    _keys(policy, ('anchor', 'destroy_count', 'patch_cap', 'expand_hops', 'reconstruction'), 'patch_policy')
    if policy['anchor'] not in ('uniform', 'blocked_gain', 'rejection_frontier', 'resource_boundary'): raise ValueError('Unknown anchor')
    if policy['reconstruction'] not in ('greedy', 'rcl', 'exchange'): raise ValueError('Unknown reconstruction')
    for name, lo, hi in (('destroy_count', 1, 12), ('patch_cap', 16, 64), ('expand_hops', 1, 2)):
        if type(policy[name]) is not int or not lo <= policy[name] <= hi: raise ValueError('Invalid ' + name)
    plan = recipe['evaluation_plan']; _keys(plan, ('feature_scope', 'max_feature_cpu_fraction', 'lazy'), 'evaluation_plan')
    if plan['feature_scope'] != 'patch' or plan['lazy'] is not True: raise ValueError('Only lazy patch features are supported')
    _finite(plan['max_feature_cpu_fraction'], 'max_feature_cpu_fraction', .05, .3)
    template = recipe['adaptation_template']
    _keys(template, ('mutation_scales', 'stagnation_trials', 'action'), 'adaptation_template')
    _coefficient_vector(template['mutation_scales'], 'mutation_scales', bounds=False)
    if type(template['stagnation_trials']) is not int or not 8 <= template['stagnation_trials'] <= 128: raise ValueError('Invalid stagnation_trials')
    if template['action'] not in ('mutate', 'diversify', 'switch_recipe'): raise ValueError('Unknown adaptation action')
    return copy.deepcopy(recipe)


class _LazyNumbers(dict):
    def __init__(self, evaluator, node):
        super().__init__(min=min, max=max, abs=abs); self.evaluator = evaluator; self.node = node
    def __missing__(self, name):
        if name in COEFFICIENT_NAMES: value = float(self.evaluator.coefficients[int(name[1])])
        else:
            value = float(self.evaluator._feature(name, self.node))
            if name in self.evaluator.expressions:
                self.evaluator.stats['feature_reads'][name] += 1
        self[name] = value; return value


class PatchEvaluator:
    """Mutable active view of a declared patch; ``remove`` invalidates all caches.

    Metadata: weight_scale (positive int, default1), duration map in Number
    units, station_gap map or scalar, satellite_gap scalar. A supplied map
    missing a referenced node raises rather than inventing a value. N[root]
    is closed in compatible_weight. patch_init is immutable initial P;
    count/sum_weights/max_weight retain its original nodes. Neighborhood,
    edge and cover/greedy operations first intersect their inputs with active.
    Deadline is absolute process_time CPU, or callable returning True when
    expired (a callable may also raise TimeoutError directly).
    """
    def __init__(self, adjacency: dict[int, set[int]], weights: dict[int, int], program: dict,
                 coefficients: list, active: set, patch_init: set, metadata: dict = None, deadline=None):
        started = time.process_time()
        self.stats = {'feature_cpu': 0., 'evaluations': 0, 'ops': 0, 'scorecalls': 0,
                      'op_counts': {}, 'cache_hits': 0, 'scoring_cpu': 0.,
                      'feature_reads': {}, 'diagnostic_feature_reads': {}}
        self.deadline = deadline; self._check_deadline()
        if not isinstance(adjacency, dict) or not isinstance(weights, dict): raise ValueError('Adjacency/weights must be dictionaries')
        if not isinstance(active, (set, frozenset)) or not isinstance(patch_init, (set, frozenset)): raise ValueError('Active/patch_init must be sets')
        if len(active) > MAX_PATCH: raise ValueError('Patch exceeds64 nodes; no truncation is permitted')
        if any(type(n) is not int for n in active | patch_init): raise ValueError('Patch nodes must be integer IDs')
        if not patch_init <= active: raise ValueError('patch_init must belong to initial active patch')
        if not active <= weights.keys() or not active <= adjacency.keys(): raise ValueError('Patch contains unknown nodes')
        self.active = set(active); self.patch_init = frozenset(patch_init); self._known_adjacency = adjacency
        self.weights = {}; self.adjacency = {}
        for node in sorted(active):
            self._check_deadline()
            value = weights[node]
            if type(value) is not int or abs(value) >= 2 ** 63: raise ValueError('Patch weights must be signed64-bit integers')
            if not isinstance(adjacency[node], (set, frozenset)) or any(type(n) is not int for n in adjacency[node]): raise ValueError('Neighbors must be integer node sets')
            if node in adjacency[node]: raise ValueError('Self edge in patch adjacency')
            self.weights[node] = value; self.adjacency[node] = frozenset(adjacency[node] & active)
        if any(a not in self.adjacency[b] for a in self.active for b in self.adjacency[a]): raise ValueError('Patch adjacency must be symmetric')
        self.metadata = {} if metadata is None else metadata
        if not isinstance(self.metadata, dict): raise ValueError('Metadata must be a dictionary')
        self.weight_scale = self.metadata.get('weight_scale', 1)
        if type(self.weight_scale) is not int or self.weight_scale <= 0: raise ValueError('weight_scale must be an explicit positive integer')
        if not isinstance(program, dict): raise ValueError('Program must be a dictionary')
        if set(program) == {'name', 'features', 'rule', 'rationale'}:
            self.program = copy.deepcopy(program)
        else: self.program = validate_recipe(program)
        self.expressions, self.code = _program(self.program)
        self.stats['feature_reads'] = {name: 0 for name in self.expressions}
        self.stats['diagnostic_feature_reads'] = {name: 0 for name in self.expressions}
        self.coefficients = _coefficient_vector(coefficients)
        self.referenced_names = frozenset(self.code.co_names) - set(FUNCTIONS)
        self._cache = {}; self._feature_cache = {}; self._snapshot = frozenset(self.active)
        self.stats['feature_cpu'] += time.process_time() - started

    def _check_deadline(self):
        if self.deadline is None: return
        expired = self.deadline() if callable(self.deadline) else time.process_time() >= self.deadline
        if expired: raise TimeoutError('Patch feature/ranking CPU deadline reached')

    def _charge(self, op, amount=1):
        self.stats['ops'] += amount
        self.stats['op_counts'][op] = self.stats['op_counts'].get(op, 0) + amount

    def _synchronise(self):
        if not self.active <= self.weights.keys() or len(self.active) > MAX_PATCH: raise ValueError('Active patch expanded outside its declared domain')
        snapshot = frozenset(self.active)
        if snapshot != self._snapshot:
            self._cache.clear(); self._feature_cache.clear(); self._snapshot = snapshot

    def remove(self, nodes):
        self._check_deadline()
        values = set(nodes)
        if any(type(n) is not int or n not in self._known_adjacency for n in values): raise ValueError('Removed node is unknown')
        self.active.difference_update(values)
        self._cache.clear(); self._feature_cache.clear(); self._snapshot = frozenset(self.active)

    def _metadata_number(self, field, node, default):
        if field not in self.metadata: return default
        value = self.metadata[field]
        if isinstance(value, dict):
            if node not in value: raise ValueError('Missing explicit ' + field + ' for node')
            value = value[node]
        return _rational(value, field)

    def _feature(self, name, node):
        self._check_deadline(); self._synchronise()
        if node not in self.active: raise ValueError('Scored root must belong to current active patch')
        name = ALIASES.get(name, name); key = (name, node)
        if key in self._feature_cache:
            self.stats['cache_hits'] += 1; return self._feature_cache[key]
        started = time.process_time()
        try:
            if name in self.expressions: value = self._eval(self.expressions[name], node)
            elif name == 'weight': self._charge('weight_read'); value = Fraction(self.weights[node], self.weight_scale)
            elif name == 'duration': self._charge('metadata_read'); value = self._metadata_number('duration', node, Fraction(self.weights[node], self.weight_scale))
            elif name == 'remaining_count': self._charge('active_count'); value = Fraction(len(self.active))
            elif name in ('station_gap', 'satellite_gap'):
                self._charge('metadata_read'); value = self._metadata_number(name, node, Fraction(0))
            elif name in ('degree', 'conflict_weight', 'max_conflict_weight', 'compatible_weight'):
                neighbors = self.adjacency[node] & self.active; self._charge('adjacency_scan', len(self.adjacency[node]))
                if name == 'degree': value = Fraction(len(neighbors))
                else:
                    nodes = self.active - neighbors - {node} if name == 'compatible_weight' else neighbors
                    self._charge('weight_read', len(nodes)); integers = [self.weights[n] for n in sorted(nodes)]
                    value = Fraction(max(integers, default=0) if name == 'max_conflict_weight' else sum(integers), self.weight_scale)
            else: raise ValueError('Unknown feature: ' + name)
            if not isinstance(value, Fraction): value = Fraction(value)
            self._feature_cache[key] = value; self.stats['evaluations'] += 1; return value
        finally: self.stats['feature_cpu'] += time.process_time() - started

    def _eval(self, expression, root):
        self._check_deadline()
        key = (expression, root if expression.depends_on_root else None)
        if key in self._cache: self.stats['cache_hits'] += 1; return self._cache[key]
        args = [self._eval(arg, root) for arg in expression.args]; op = expression.op
        self._charge(op)
        if op == 'root': value = root
        elif op == 'available': value = frozenset(self.active)
        elif op == 'patch_init': value = self.patch_init
        elif op == 'neighbors':
            self._charge('adjacency_scan', len(self.adjacency[args[0]])); value = self.adjacency[args[0]] & self.active
        elif op == 'neighbors_of_set':
            nodes = set()
            for n in sorted(args[0] & self.active):
                self._check_deadline(); self._charge('adjacency_scan', len(self.adjacency[n])); nodes.update(self.adjacency[n] & self.active)
            value = frozenset(nodes)
        elif op == 'singleton': value = frozenset({args[0]}) if args[0] in self.active else frozenset()
        elif op in ('union', 'intersection', 'difference'):
            self._charge('set_scan', len(args[0]) + len(args[1]))
            value = args[0] | args[1] if op == 'union' else args[0] & args[1] if op == 'intersection' else args[0] - args[1]
        elif op == 'induced_edges':
            nodes = sorted(args[0] & self.active); edges = set()
            for i, a in enumerate(nodes):
                self._check_deadline()
                for b in nodes[i + 1:]:
                    self._charge('edge_membership')
                    if b in self.adjacency[a]: edges.add((a, b))
            value = frozenset(edges)
        elif op == 'incident_edges':
            edges = set()
            for a in sorted(args[0] & self.active):
                self._check_deadline(); self._charge('adjacency_scan', len(self.adjacency[a]))
                for b in self.adjacency[a] & self.active: edges.add((min(a, b), max(a, b)))
            value = frozenset(edges)
        elif op == 'count': value = Fraction(len(args[0]))
        elif op in ('sum_weights', 'max_weight'):
            self._charge('weight_read', len(args[0])); values = [self.weights[n] for n in sorted(args[0])]
            value = Fraction(sum(values) if op == 'sum_weights' else max(values, default=0), self.weight_scale)
        elif op in ('edge_min_weight_sum', 'edge_weight_product_sum'):
            self._charge('weight_read', 2 * len(args[0])); self._charge('arithmetic', len(args[0]))
            integer = sum(min(self.weights[a], self.weights[b]) if op == 'edge_min_weight_sum' else self.weights[a] * self.weights[b] for a, b in sorted(args[0]))
            value = Fraction(integer, self.weight_scale if op == 'edge_min_weight_sum' else self.weight_scale ** 2)
        elif op in ('clique_cover_weight', 'greedy_independent_weight'):
            remaining = set(args[0] & self.active); order = sorted(remaining, key=lambda n: (-self.weights[n], n)); total = 0
            self._charge('weight_read', len(order))
            for a in order:
                self._check_deadline()
                if a not in remaining: continue
                remaining.remove(a)
                if op == 'greedy_independent_weight':
                    total += self.weights[a]; self._charge('adjacency_scan', len(self.adjacency[a])); remaining.difference_update(self.adjacency[a])
                else:
                    clique = [a]
                    for b in order:
                        self._check_deadline()
                        if b not in remaining: continue
                        self._charge('edge_membership', len(clique))
                        if all(b in self.adjacency[n] for n in clique): clique.append(b); remaining.remove(b)
                    total += max(self.weights[n] for n in clique)
            value = Fraction(total, self.weight_scale)
        elif op == 'weight': self._charge('weight_read'); value = Fraction(self.weights[args[0]], self.weight_scale)
        elif op == 'duration': self._charge('metadata_read'); value = self._metadata_number('duration', args[0], Fraction(self.weights[args[0]], self.weight_scale))
        elif op == 'const': value = expression.value
        elif op == 'add': value = args[0] + args[1]
        elif op == 'sub': value = args[0] - args[1]
        elif op == 'mul': value = args[0] * args[1]
        elif op == 'div':
            if args[1] == 0: raise ValueError('Feature division by zero')
            value = args[0] / args[1]
        elif op == 'min': value = min(args)
        elif op == 'max': value = max(args)
        elif op == 'abs': value = abs(args[0])
        else: raise AssertionError('Unreachable validated operation')
        self._cache[key] = value; return value

    def feature_values(self, node):
        """All declared representation coordinates as exact Fractions, no θ."""
        self._check_deadline(); self._synchronise()
        values = {}
        for name in BASE_NAMES + tuple(ALIASES) + tuple(self.expressions):
            values[name] = self._feature(name, node)
            if name in self.expressions: self.stats['diagnostic_feature_reads'][name] += 1
        return values

    def score(self, node):
        self._check_deadline(); self._synchronise()
        if node not in self.active: raise ValueError('Scored root must belong to current active patch')
        self.stats['scorecalls'] += 1; started = time.process_time(); before_feature_cpu = self.stats['feature_cpu']
        try:
            value = float(eval(self.code, {'__builtins__': {}}, _LazyNumbers(self, node)))
            if not math.isfinite(value): raise ValueError('Rule score must be finite')
            return value
        except (ZeroDivisionError, OverflowError, TypeError, KeyError) as error:
            raise ValueError('Invalid numeric score: ' + str(error)) from error
        finally:
            self.stats['scoring_cpu'] += max(0., time.process_time() - started - (self.stats['feature_cpu'] - before_feature_cpu))
