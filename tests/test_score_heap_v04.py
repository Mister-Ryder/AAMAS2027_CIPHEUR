import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from cipheur.compiled import schedule_compiled
from cipheur.graph_features import FeatureRuleProgram
from cipheur.holdout_study import BudgetMeter, ProgramBudgetExceeded
from cipheur.score_heap_v04 import schedule_heap, score_locality
from tests.test_compiled_v03 import graph, op


class WorkCap(RuntimeError):
    pass


class CappedMeter(dict):
    def __init__(self, limit):
        super().__init__()
        self.limit = limit

    def __setitem__(self, key, value):
        if key == "feature_work" and value > self.limit:
            raise WorkCap("test work budget exceeded")
        super().__setitem__(key, value)


class ScoreHeapTests(unittest.TestCase):
    def parity(self, g, program, fixed=(), excluded=()):
        full = schedule_compiled(g, program, fixed, excluded, score_slice=True)
        heap = schedule_heap(g, program, fixed, excluded)
        for key in ("selected", "value", "trace", "feasible"):
            self.assertEqual(heap[key], full[key], (g.name, program.name, key))
        self.assertEqual(heap["compilation"], full["compilation"])
        self.assertEqual(heap["feature_work"], sum(heap[key] for key in (
            "initialization_work", "update_work", "query_work", "priority_work")))
        return full, heap

    def test_all_93_training_programs_on_300_random_boundaries(self):
        source = Path(__file__).parent / "fixtures/score_heap_training_bank_v04.json"
        bank = [FeatureRuleProgram.from_dict(row["program"]) for row in json.loads(source.read_text())]
        self.assertEqual(len(bank), 93)
        rng = random.Random(2026100304)
        for case in range(300):
            n = rng.randrange(0, 21)
            density = [0, .05, .2, .5, 1][case % 5]
            weights = [rng.choice([0, .1, .2, .25, 1, 1000, 1e-12, rng.random()*20]) for _ in range(n)]
            if case % 11 == 0:
                weights = [0]*n
            edges = [(i,j) for i in range(n) for j in range(i+1,n) if rng.random() < density]
            g = graph(weights, edges, "random_"+str(case))
            fixed = []
            if case % 3:
                for node in rng.sample(sorted(g.nodes), len(g.nodes)):
                    if len(fixed) < 3 and rng.random() < .2 and g.feasible(fixed+[node]):
                        fixed.append(node)
            excluded = [v for v in sorted(g.nodes) if v not in fixed and rng.random() < .15]
            for program in bank:
                self.parity(g, program, fixed, excluded)

    def test_distance_two_frontier_is_refreshed(self):
        g = graph([10,1,1.5,1], [(0,1),(1,2),(2,3)])
        _, heap = self.parity(g, FeatureRuleProgram("distance_two", [], "weight-degree"))
        self.assertEqual([r["selected"] for r in heap["trace"]], ["0","2"])
        self.assertEqual(heap["score_heap"]["refresh_score_evaluations"], 1)

    def test_local_aggregates_packing_overlapping_edges_and_ties(self):
        neighbors = op("neighbors",op("root"))
        edges = op("induced_edges",neighbors)
        features = [{"name":"E","expression":op("count",edges)},
                    {"name":"M","expression":op("edge_min_weight_sum",edges)},
                    {"name":"P","expression":op("edge_weight_product_sum",edges)},
                    {"name":"L","expression":op("greedy_independent_weight",neighbors)},
                    {"name":"U","expression":op("clique_cover_weight",neighbors)},
                    {"name":"self","expression":op("sum_weights",op("singleton",op("root")))}]
        g = graph([2,8,3,3,7,1,1], [(0,1),(0,2),(1,2),(1,3),(2,3),(3,4),(4,5),(5,6)])
        for rule in ("weight+degree", "weight-degree", "max_conflict_weight-weight",
                     "weight-conflict_weight", "weight-E+M/20+P/100", "weight-L+U/2", "self"):
            _, heap = self.parity(g,FeatureRuleProgram("aggregates",features,rule))
            self.assertTrue(heap["score_heap"]["eligible_local"])
        tied = graph([1]*20, [(i,i+1) for i in range(19)])
        self.parity(tied,FeatureRuleProgram("ties",[],"degree"))

    def test_conservative_global_gate_ignores_no_untaken_branch(self):
        available = {"name":"global_count","expression":op("count",op("available"))}
        cancelling = {"name":"zero","expression":op("count",op("difference",op("available"),op("available")))}
        g = graph([1,2,3,4,5],[(0,1),(2,3)])
        programs = [FeatureRuleProgram("remaining",[],"remaining_count+weight"),
                    FeatureRuleProgram("compatible",[],"compatible_weight-weight"),
                    FeatureRuleProgram("untaken",[available],"weight if degree>=0 else global_count"),
                    FeatureRuleProgram("cancelled",[cancelling],"weight+zero")]
        for p in programs:
            _, heap = self.parity(g,p)
            self.assertFalse(heap["score_heap"]["eligible_local"])
            self.assertEqual(heap["score_heap"]["full_rescore_states"],len(heap["trace"]))
        unused = FeatureRuleProgram("unused",[available],"weight")
        self.assertTrue(score_locality(unused)["static_scores"])
        self.parity(g,unused)

    def test_all_current_local_numeric_and_set_primitives(self):
        root = op("root"); n = op("neighbors",root); s = op("singleton",root)
        expressions = [op("duration",root),op("weight",root),op("max_weight",n),
                       op("sum_weights",op("union",n,s)),op("count",op("intersection",n,s)),
                       op("sum_weights",op("difference",n,s)),
                       op("abs",op("div",op("sub",op("const"),op("const")),op("max",op("const"),op("const"))))]
        # Constants require the typed value form rather than generic args.
        expressions[-1] = {"op":"abs","args":[{"op":"div","args":[{"op":"sub","args":[{"op":"const","value":3},{"op":"const","value":5}]},{"op":"max","args":[{"op":"const","value":1},{"op":"const","value":2}]}]}]}
        g = graph([.1,.2,2,0,7],[(0,1),(1,2),(2,3),(3,4)])
        for i,e in enumerate(expressions):
            self.parity(g,FeatureRuleProgram("primitive"+str(i),[{"name":"f","expression":e}],"weight+f"))

    def test_budget_errors_propagate_in_both_modes_without_schedule(self):
        g = graph([1]*80,[(i,i+1) for i in range(79)])
        for rule in ("weight-degree", "remaining_count+weight"):
            p = FeatureRuleProgram("budget",[],rule)
            complete = schedule_heap(g,p)
            for limit in (0, complete["initialization_work"]+1, complete["feature_work"]-1):
                meter = CappedMeter(limit)
                with self.assertRaises(WorkCap): schedule_heap(g,p,meter=meter)
                self.assertNotIn("selected",meter)
                self.assertNotIn("trace",meter)
        with patch("cipheur.holdout_study.time.process_time",return_value=0):
            meter = BudgetMeter(1)
        with patch("cipheur.holdout_study.time.process_time",return_value=2):
            with self.assertRaises(ProgramBudgetExceeded):
                schedule_heap(g,FeatureRuleProgram("cpu_cap",[],"weight"),meter=meter)

    def test_large_sparse_fixture_saves_score_queries_and_charged_work(self):
        g = graph([1+i%13/4 for i in range(768)],[(i,i+1) for i in range(0,768,2)])
        full, heap = self.parity(g,FeatureRuleProgram("sparse",[],"weight/max(1,degree)"))
        self.assertEqual(heap["score_heap"]["score_evaluations"],768)
        self.assertEqual(heap["score_heap"]["refresh_score_evaluations"],0)
        self.assertGreater(full["query_work"],20*heap["query_work"])
        self.assertLess(heap["feature_work"],full["feature_work"]*.1)
        self.assertGreater(heap["feature_primitives"]["score_heap_compare"],0)


if __name__ == "__main__": unittest.main()
