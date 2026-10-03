"""Independent exhaustive cross-checks of the v03 hitting-set B&B master.

The reference enumerates original repair subsets and uses Kahn elimination,
without calling the implementation's quotient diagnosis or master search.
Tests are implementation checks; the formal review supplies the proof audit.
"""
from collections import defaultdict
from fractions import Fraction
import itertools
import random
import unittest

from cipheur.refinement import minimum_cost_vector_refinement


def independent_dag(occurrences, requirements, values, selected):
    keys = {oid: (tuple((name, Fraction(value)) for name, value in sorted(base.items())),
                  tuple((name, Fraction(values[name][oid])) for name in sorted(selected)))
            for oid, base in occurrences.items()}
    adjacency, indegree = defaultdict(set), {}
    for req in requirements:
        source, destination = keys[req["preferred"]], keys[req["other"]]
        indegree.setdefault(source, 0)
        indegree.setdefault(destination, 0)
        if destination not in adjacency[source]:
            adjacency[source].add(destination)
            indegree[destination] += 1
    ready = [vertex for vertex, degree in indegree.items() if degree == 0]
    removed = 0
    while ready:
        vertex = ready.pop()
        removed += 1
        for destination in adjacency[vertex]:
            indegree[destination] -= 1
            if indegree[destination] == 0:
                ready.append(destination)
    return removed == len(indegree)


def subsets(names, limit=None):
    for size in range(len(names) + 1):
        if limit is None or size <= limit:
            yield from itertools.combinations(sorted(names), size)


def exact_key(selected, costs):
    return sum((Fraction(costs[name]) for name in selected), Fraction(0)), len(selected), tuple(sorted(selected))


def exhaustive_optimum(occurrences, requirements, values, costs, limit=None):
    feasible = [exact_key(selected, costs) for selected in subsets(values, limit)
                if independent_dag(occurrences, requirements, values, selected)]
    return min(feasible) if feasible else None


def set_cover_table(source_sets):
    elements = sorted(set().union(*map(set, source_sets.values())))
    occurrences, requirements = {}, []
    for index, element in enumerate(elements):
        p, n = f"p{element}", f"n{element}"
        occurrences[p] = occurrences[n] = {"base_class": index}
        requirements.append({"preferred": p, "other": n})
    values = {name: {oid: int(oid[0] == "p" and int(oid[1:]) in covered) for oid in occurrences}
              for name, covered in source_sets.items()}
    return occurrences, requirements, values


class RefinementMasterCrossChecks(unittest.TestCase):
    def assert_result_matches_original_problem(self, occurrences, requirements, values, costs, limit=None):
        optimum = exhaustive_optimum(occurrences, requirements, values, costs, limit)
        result = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_selected=limit)
        if optimum is None:
            self.assertFalse(result["repaired"])
            self.assertFalse(result["optimal"])
            self.assertIn(result["reason"], ("catalogue_cannot_separate_witness",
                                             "catalogue_infeasible_under_cardinality_limit"))
        else:
            self.assertTrue(result["repaired"])
            self.assertTrue(result["optimal"])
            self.assertEqual(Fraction(result["cost_exact"]), optimum[0])
            self.assertEqual(tuple(result["selected_names"]), optimum[2])
            self.assertTrue(independent_dag(occurrences, requirements, values, result["selected_names"]))
        # Check EVERY retained master optimum independently, not only the final
        # original repair. This exercises cut branching, tie breaks and pruning.
        for row in result["rounds"]:
            feasible = [exact_key(selected, costs) for selected in subsets(values, limit)
                        if all(set(selected).intersection(cut) for cut in row["cuts"])]
            master_optimum = min(feasible)
            self.assertTrue(row["master_globally_optimal"])
            self.assertTrue(row["full_quotient_rechecked"])
            self.assertEqual(Fraction(row["cost_exact"]), master_optimum[0])
            self.assertEqual(tuple(row["selected_names"]), master_optimum[2])
        return result

    def test_random_finite_tables_with_aliases_parallel_evidence_and_exact_costs(self):
        rng = random.Random(931720)
        for case in range(180):
            ids = [f"o{i}" for i in range(rng.randint(3, 9))]
            occurrences = {oid: {"base": rng.randrange(3)} for oid in ids}
            requirements = [{"preferred": rng.choice(ids), "other": rng.choice(ids)}
                            for _ in range(rng.randint(1, 14))]
            if case % 3 == 0:
                requirements.append(dict(requirements[0]))
            values = {f"f{i}": {oid: rng.randrange(4) for oid in ids}
                      for i in range(rng.randint(0, 7))}
            cost_pool = (1, 2, 5, 0.1, 0.2, Fraction(1, 3), Fraction(2, 7))
            costs = {name: rng.choice(cost_pool) for name in values}
            limits = (None, rng.randint(0, len(values)))
            for limit in limits:
                with self.subTest(case=case, max_selected=limit):
                    self.assert_result_matches_original_problem(occurrences, requirements, values, costs, limit)

    def test_random_weighted_set_cover_reduction_matches_original_objective(self):
        rng = random.Random(887123)
        for case in range(100):
            count, number = rng.randint(1, 7), rng.randint(1, 7)
            source_sets = {f"f{i}": {e for e in range(count) if rng.random() < 0.5} for i in range(number)}
            source_sets["universal"] = set(range(count))
            occurrences, requirements, values = set_cover_table(source_sets)
            costs = {name: rng.randint(1, 12) for name in values}
            with self.subTest(case=case):
                self.assert_result_matches_original_problem(occurrences, requirements, values, costs)

    def test_exact_tie_break_and_repeated_subset_paths(self):
        occurrences, requirements, values = set_cover_table({"a": {0}, "b": {0, 1}, "c": {1}})
        costs = {"a": 1, "b": 2, "c": 1}
        result = self.assert_result_matches_original_problem(occurrences, requirements, values, costs)
        self.assertEqual(result["selected_names"], ["b"])
        occurrences, requirements, values = set_cover_table({"a": {0, 1}, "b": {0, 2},
                                                            "c": {1, 2}, "d": {2}})
        result = self.assert_result_matches_original_problem(occurrences, requirements, values,
                                                             {name: 1 for name in values})
        self.assertEqual(result["selected_names"], ["a", "b"])

    def test_declared_cardinality_limit_changes_the_valid_optimality_scope(self):
        source_sets = {f"f{i}": {i} for i in range(7)}
        source_sets["universal"] = set(range(7))
        occurrences, requirements, values = set_cover_table(source_sets)
        costs = {name: 1 for name in values}
        costs["universal"] = 10
        unrestricted = self.assert_result_matches_original_problem(occurrences, requirements, values, costs)
        limited = self.assert_result_matches_original_problem(occurrences, requirements, values, costs, limit=6)
        self.assertEqual(unrestricted["cost_exact"], "7")
        self.assertEqual(limited["cost_exact"], "10")
        self.assertEqual(limited["selected_names"], ["universal"])
        self.assertEqual(limited["max_selected"], 6)

    def test_master_budget_can_return_feasible_without_claiming_optimal(self):
        occurrences, requirements, values = set_cover_table({"a": {0}, "b": {0}, "c": {0}})
        costs = {name: 1 for name in values}
        partial = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_master_subsets=2)
        self.assertEqual(partial["master_subsets_evaluated"], 2)
        self.assertEqual(partial["reason"], "master_budget_exhausted")
        self.assertTrue(partial["repaired"])
        self.assertFalse(partial["optimal"])
        self.assertTrue(independent_dag(occurrences, requirements, values, partial["selected_names"]))
        full = minimum_cost_vector_refinement(occurrences, requirements, values, costs)
        exact_budget = minimum_cost_vector_refinement(occurrences, requirements, values, costs,
                                                       max_master_subsets=full["master_subsets_evaluated"])
        self.assertTrue(exact_budget["optimal"])
        self.assertEqual(exact_budget["selected_names"], full["selected_names"])

    def test_budget_accounting_across_rounds_and_zero_budget(self):
        occurrences, requirements, values = set_cover_table({"a": {0}, "b": {1}})
        costs = {"a": 1, "b": 1}
        stopped = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_master_subsets=3)
        self.assertEqual(stopped["master_subsets_evaluated"], 3)
        self.assertEqual(stopped["reason"], "master_budget_exhausted")
        self.assertEqual(len(stopped["rounds"]), 1)
        self.assertFalse(stopped["repaired"])
        self.assertFalse(stopped["optimal"])
        zero = minimum_cost_vector_refinement(occurrences, requirements, values, costs, max_master_subsets=0)
        self.assertEqual(zero["master_subsets_evaluated"], 0)
        self.assertFalse(zero["optimal"])
        already_dag = minimum_cost_vector_refinement({"p": {"base": 1}, "n": {"base": 0}},
            [{"preferred": "p", "other": "n"}], {}, {}, max_rounds=0, max_master_subsets=0)
        self.assertTrue(already_dag["optimal"])
        self.assertEqual(already_dag["cost_exact"], "0")

    def test_budgeted_reports_never_mark_an_unrepaired_candidate_optimal(self):
        rng = random.Random(1379)
        for case in range(35):
            count = rng.randint(2, 6)
            source_sets = {f"f{i}": {e for e in range(count) if rng.random() < 0.45}
                           for i in range(rng.randint(2, 6))}
            source_sets["universal"] = set(range(count))
            occurrences, requirements, values = set_cover_table(source_sets)
            costs = {name: rng.choice((1, 2, 0.1)) for name in values}
            for budget in (0, 1, 2, 5, 12):
                result = minimum_cost_vector_refinement(occurrences, requirements, values, costs,
                                                         max_master_subsets=budget)
                self.assertLessEqual(result["master_subsets_evaluated"], budget)
                dag = independent_dag(occurrences, requirements, values, result["selected_names"])
                self.assertEqual(result["repaired"], dag)
                if result["optimal"]:
                    self.assertTrue(dag)
                    self.assertEqual(Fraction(result["cost_exact"]),
                                     exhaustive_optimum(occurrences, requirements, values, costs)[0])


if __name__ == "__main__":
    unittest.main()
