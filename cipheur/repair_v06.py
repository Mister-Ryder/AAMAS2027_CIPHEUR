"""Shared bounded independent-set repair, with typed-program search priorities.

Local clique bounds, greedy incumbents and branch-and-bound are classical
components. The programme chooses where/what to explore; it never supplies a
feasibility certificate or an upper bound. No conditional-value oracle,
synthesis service or external executable is imported or called.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import heapq
import math
import random
import time

from .compiled import CompiledEvaluator
from .graph_features import FeatureRuleProgram
from .model import Graph


@dataclass(frozen=True)
class RepairConfig:
    # Defaults are implementation limits, not settings selected on TEST.
    max_patch_vertices: int = 24
    max_destroy: int = 4
    max_patches: int = 64
    expansion_steps: int = 1
    node_budget_per_patch: int = 2000
    max_search_nodes: int = 50000
    max_work: int | None = None
    upper_pruning: bool = True
    policy_scope: str = "branch"

    def __post_init__(self):
        for name in ("max_patch_vertices", "max_destroy", "max_patches",
                     "expansion_steps", "node_budget_per_patch", "max_search_nodes"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(name + " must be a nonnegative integer")
        if self.max_destroy > self.max_patch_vertices:
            raise ValueError("A patch must have space for every destroyed incumbent vertex")
        if self.max_work is not None and (type(self.max_work) is not int or self.max_work < 0):
            raise ValueError("max_work must be a nonnegative integer or None")
        if type(self.upper_pruning) is not bool:
            raise ValueError("upper_pruning must be boolean")
        if self.policy_scope not in ("branch", "target_and_branch"):
            raise ValueError("policy_scope must be branch or target_and_branch")


class _Stopped(Exception):
    pass


class _Meter(dict):
    """Cooperative end-to-end deadline and charged-operation budget.

    The dict interface also receives the unchanged compiled feature runtime's
    charges. Bulk primitives can overshoot; measured time includes the final
    validation. Work is an operation proxy, not FLOPs or machine-independent
    complexity. No stage obtains a separate uncharged execution allowance.
    """
    def __init__(self, seconds, clock, max_work, max_search_nodes):
        super().__init__(feature_work=0, repair_work=0, search_nodes=0,
                         feature_primitives={}, repair_primitives={})
        if seconds is not None and (type(seconds) not in (int, float)
                                   or not math.isfinite(seconds) or seconds < 0):
            raise ValueError("seconds must be finite and nonnegative or None")
        if clock not in ("cpu", "wall"):
            raise ValueError("clock must be cpu or wall")
        self.cpu_start, self.wall_start = time.process_time(), time.perf_counter()
        self.clock = time.process_time if clock == "cpu" else time.perf_counter
        self.deadline = None if seconds is None else self.clock() + seconds
        self.max_work, self.max_search_nodes = max_work, max_search_nodes
        self.reason, self.sealed, self.writes = None, False, 0

    def check(self):
        if self.sealed:
            return
        if self.max_work is not None and self.get("feature_work", 0) + self["repair_work"] > self.max_work:
            self.reason = "work_budget"
        elif self.deadline is not None and self.clock() >= self.deadline:
            self.reason = "time_budget"
        if self.reason:
            raise _Stopped(self.reason)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.writes += 1
        if not self.sealed and (key == "feature_work" or self.writes % 32 == 0):
            self.check()

    def tick(self, primitive, amount=1):
        self["repair_work"] += amount
        parts = self["repair_primitives"]
        parts[primitive] = parts.get(primitive, 0) + amount
        self.check()

    def node(self):
        if self["search_nodes"] >= self.max_search_nodes:
            self.reason = "total_node_budget"
            raise _Stopped(self.reason)
        self["search_nodes"] += 1
        self.tick("search_node")


def _value(graph, nodes):
    return sum((Fraction(graph.nodes[v].weight) for v in nodes), Fraction())


def _boundary(graph, initial, fixed, excluded):
    fixed, excluded = tuple(fixed), tuple(excluded)
    legal = graph.available(fixed, excluded)
    initial = tuple(fixed) if initial is None else tuple(initial)
    if (not graph.feasible(initial) or not set(fixed) <= set(initial)
            or set(initial) & set(excluded)):
        raise ValueError("Initial incumbent violates graph/fixed/excluded feasibility")
    return set(initial), set(fixed), set(excluded), legal


def _priorities(graph, nodes, program, priority, rng, meter):
    nodes = set(nodes)
    if priority == "program":
        evaluator = CompiledEvaluator(graph, program, nodes, meter, score_slice=True)
        values = {}
        for v in sorted(nodes):
            meter.tick("priority_score")
            values[v] = evaluator.score(v)
        return values
    if priority == "degree":
        values = {}
        for v in sorted(nodes):
            meter.tick("degree_priority", len(graph.adj[v]) + 2)
            values[v] = Fraction(graph.nodes[v].weight) / max(1, len(graph.adj[v] & nodes))
        return values
    if priority == "random":
        values = {}
        for v in sorted(nodes):
            meter.tick("random_priority")
            values[v] = rng.random()
        return values
    raise ValueError("priority must be program, degree or random")


def _initialize(graph, incumbent, legal, weights, meter, trace):
    """Common exact weight/degree greedy initializer, charged for every arm.

    A caller-supplied seed is completed using the same initializer. It is not a
    hidden best-of-bank seed. A time cap retains the feasible prefix already
    constructed, because this new algorithm is explicitly anytime.
    """
    active = set(legal) - incumbent
    for v in incumbent:
        meter.tick("initializer_boundary", len(graph.adj[v]))
        active.difference_update(graph.adj[v])
    # Exact lazy heap, with the same decisions as a full weight/degree scan.
    # It is common to every arm; no programme-specific seed is credited as a
    # target/branch-priority benefit. Updating only incident degrees avoids a
    # quadratic full-residual scan on large sparse graphs.
    degrees, versions, heap = {}, {}, []
    for v in sorted(active):
        meter.tick("initializer_degree", len(graph.adj[v]) + 1)
        degrees[v], versions[v] = len(graph.adj[v] & active), 0
        heapq.heappush(heap, (-weights[v] / max(1, degrees[v]), v, 0))
        meter.tick("initializer_heap_push")
    while heap:
        meter.tick("initializer_heap_pop")
        negative, v, version = heapq.heappop(heap)
        if v not in active or versions[v] != version:
            continue
        incumbent.add(v)  # keep the feasible prefix before the next cap check
        trace.append({"selected": v, "score_exact": str(-negative), "available": len(active)})
        deleted = ({v} | graph.adj[v]) & active
        meter.tick("initializer_delete", len(graph.adj[v]) + 1)
        active.difference_update(deleted)
        affected = set()
        for u in sorted(deleted):
            for neighbor in sorted(graph.adj[u]):
                meter.tick("initializer_incident_update")
                if neighbor in active:
                    degrees[neighbor] -= 1
                    affected.add(neighbor)
        for u in sorted(affected):
            versions[u] += 1
            heapq.heappush(heap, (-weights[u] / max(1, degrees[u]), u, versions[u]))
            meter.tick("initializer_heap_push")


def _patch_region(graph, incumbent, destroy, excluded, meter):
    outside = incumbent - destroy
    # This is exactly V \ (outside U N(outside) U excluded), including old D.
    blocked = set(outside) | excluded
    for v in sorted(outside):
        meter.tick("patch_boundary_scan", len(graph.adj[v]))
        blocked.update(graph.adj[v])
    meter.tick("patch_universe_scan", len(graph.nodes))
    region = set(graph.nodes) - blocked
    if not destroy <= region:
        raise AssertionError("Destroyed incumbent is missing from legal repair region")
    return outside, region


def _uncomputed_result(graph, destroy):
    return {"local_selected": sorted(destroy), "lower_exact": str(_value(graph, destroy)),
            "upper_exact": None, "root_upper_exact": None,
            "upper_method": "not_computed", "root_clique_cover": [],
            "search_nodes": 0, "bound_cuts": 0, "root_pruned": False, "restricted_exact": False,
            "priority_order": [], "common_degree_order": [], "greedy_passes": [],
            "pivot_count": 0, "degree_pivot_disagreements": 0,
            "termination": "not_started", "patch_node_budget_exhausted": False,
            "budget_exhausted": False}


def _solve(graph, region, destroy, weights, priority_factory, meter, node_budget, upper_pruning):
    """Exact arithmetic and bitmask local B&B; partial search keeps its witness."""
    nodes = sorted(region)
    index = {v: i for i, v in enumerate(nodes)}
    adjacency, values = [], []
    for v in nodes:
        meter.tick("local_adjacency", len(nodes))
        adjacency.append(sum(1 << index[u] for u in nodes if u in graph.adj[v]))
        values.append(weights[v])
    full = (1 << len(nodes)) - 1
    initial_mask = sum(1 << index[v] for v in destroy)
    best_mask, best = initial_mask, sum((weights[v] for v in destroy), Fraction())
    root_upper, root_cover, expanded, cuts = None, [], 0, 0
    frontier, cache = None, {}
    reason, root_pruned, search_finished = "node_budget", False, False
    priority_order, common_degree_order, greedy_passes = [], [], []
    pivots, pivot_disagreements = 0, 0

    def members(mask):
        while mask:
            bit = mask & -mask
            yield bit.bit_length() - 1
            mask ^= bit

    def envelope(mask, keep_cover=False):
        if mask in cache and not keep_cover:
            meter.tick("bound_cache_hit")
            return cache[mask], []
        ids = list(members(mask))
        meter.tick("bound_order", len(ids))
        order = sorted(ids, key=lambda i: (-(adjacency[i] & mask).bit_count(), -values[i], nodes[i]))
        remaining, upper, cover = mask, Fraction(), []
        for i in order:
            meter.tick("bound_membership")
            if not remaining & (1 << i):
                continue
            clique = [i]
            remaining ^= 1 << i
            common = adjacency[i]
            for j in order:
                meter.tick("bound_clique_test")
                if remaining & (1 << j) and common & (1 << j):
                    clique.append(j)
                    remaining ^= 1 << j
                    common &= adjacency[j]
            upper += max(values[j] for j in clique)
            cover.append([nodes[j] for j in clique])
        cache[mask] = upper
        return upper, cover

    try:
        root_upper, root_cover = envelope(full, True)
        if root_upper < best:
            raise AssertionError("Invalid local upper enclosure")
        if upper_pruning and root_upper <= best:
            root_pruned, reason, frontier = True, "root_bound", []
        else:
            scores = priority_factory(set(nodes))
            order = sorted(range(len(nodes)), key=lambda i: (-scores[nodes[i]], nodes[i]))
            common_order = sorted(range(len(nodes)), key=lambda i: (
                -values[i] / max(1, (adjacency[i] & full).bit_count()), nodes[i]))
            priority_order = [nodes[i] for i in order]
            common_degree_order = [nodes[i] for i in common_order]
            # Same two cheap feasible lower-bound constructions for every arm.
            for label, greedy_order in (("priority", order), ("common_degree", common_order)):
                available, chosen, val = full, 0, Fraction()
                greedy_record = {"order": label, "value_exact": "0", "complete": False}
                greedy_passes.append(greedy_record)
                for i in greedy_order:
                    meter.tick("local_greedy")
                    if available & (1 << i):
                        chosen |= 1 << i
                        val += values[i]
                        available &= ~((1 << i) | adjacency[i])
                        # Publish a feasible prefix before the next budget check.
                        if val > best:
                            best_mask, best = chosen, val
                        greedy_record["value_exact"] = str(val)
                greedy_record["complete"] = True
            frontier = [(full, 0, Fraction())]
            while frontier and expanded < node_budget:
                meter.node()
                mask, chosen, val = frontier.pop()
                expanded += 1
                if val > best:
                    best_mask, best = chosen, val
                if not mask:
                    continue
                if upper_pruning and val + envelope(mask)[0] <= best:
                    cuts += 1
                    continue
                i = next(i for i in order if mask & (1 << i))
                pivots += 1
                pivot_disagreements += i != next(j for j in common_order if mask & (1 << j))
                rest = mask & ~(1 << i)
                frontier.append((rest, chosen, val))
                frontier.append((rest & ~adjacency[i], chosen | (1 << i), val + values[i]))
            search_finished = not frontier
            reason = "restricted_optimum" if search_finished else "node_budget"
    except _Stopped as stop:
        reason = str(stop)
    chosen = {nodes[i] for i in members(best_mask)}
    # Proof validation is unavoidable after a cap; charge it without discarding
    # an already found witness. Actual CPU/wall time includes this overshoot.
    prior_sealed = meter.sealed
    meter.sealed = True
    meter.tick("local_validation", len(chosen) + sum(len(graph.adj[v]) for v in chosen))
    meter.sealed = prior_sealed
    if not graph.feasible(chosen) or _value(graph, chosen) != best:
        raise AssertionError("Local incumbent proof failed")
    # A stopped node may already have been popped before its children/upper
    # were processed. An empty Python stack then is NOT an exhaustion proof.
    exact = root_upper is not None and (root_upper == best or root_pruned or search_finished)
    patch_cap = reason == "node_budget" and not exact
    upper_method = "not_computed" if root_upper is None else (
        "exhaustive_restricted_search" if exact and best < root_upper
        else "exact_verified_clique_partition")
    return {"local_selected": sorted(chosen), "lower_exact": str(best),
            "upper_exact": str(best if exact else root_upper) if root_upper is not None else None,
            "root_upper_exact": str(root_upper) if root_upper is not None else None,
            "upper_method": upper_method,
            "root_clique_cover": root_cover,
            "search_nodes": expanded, "bound_cuts": cuts, "root_pruned": root_pruned,
            "priority_order": priority_order, "common_degree_order": common_degree_order,
            "greedy_passes": greedy_passes, "pivot_count": pivots,
            "degree_pivot_disagreements": pivot_disagreements,
            "restricted_exact": exact, "termination": reason,
            "patch_node_budget_exhausted": patch_cap,
            "budget_exhausted": meter.reason is not None or patch_cap}


def repair_patch(graph, initial, destroy, *, fixed=(), excluded=(), region=None,
                 priorities=None, node_budget=10000, upper_pruning=True,
                 max_patch_vertices=None, seconds=None, clock="cpu", max_work=None):
    """An independently checkable single-patch primitive, without a model call.

    Optional region is an explicit restriction of the full free region. D must
    survive any restriction/truncation. Exactness is local to the returned
    patch, never an unrestricted/global optimum claim.
    """
    if type(node_budget) is not int or node_budget < 0 or type(upper_pruning) is not bool:
        raise ValueError("Invalid local node/pruning budget")
    if max_patch_vertices is not None and (type(max_patch_vertices) is not int or max_patch_vertices < 0):
        raise ValueError("Invalid patch size cap")
    if max_work is not None and (type(max_work) is not int or max_work < 0):
        raise ValueError("Invalid patch work cap")
    meter = _Meter(seconds, clock, max_work, node_budget)
    incumbent, fixed, excluded, _ = _boundary(graph, initial, fixed, excluded)
    destroy = set(destroy)
    if not destroy <= incumbent or destroy & fixed:
        raise ValueError("Destroyed nodes must be movable incumbent nodes")
    # Validate the explicit restriction even with a zero budget. This bounded
    # input validation is inside the actual timer; optimization can then abstain.
    outside = incumbent - destroy
    blocked = outside | excluded
    for v in outside:
        blocked |= graph.adj[v]
    full_region = set(graph.nodes) - blocked
    selected_region = full_region if region is None else set(region)
    if not destroy <= selected_region <= full_region:
        raise ValueError("A restricted patch must be legal and retain every destroyed node")
    if priorities is not None:
        if any(v not in priorities or not math.isfinite(float(priorities[v])) for v in selected_region):
            raise ValueError("Every patch node needs a finite priority")
    if max_patch_vertices is not None:
        if len(destroy) > max_patch_vertices:
            raise ValueError("Patch truncation cannot delete destroyed incumbent nodes")
    result = _uncomputed_result(graph, destroy)
    try:
        meter.tick("input_validation", len(graph.nodes) + len(graph.edges) + len(incumbent))
        meter.tick("patch_boundary_scan", sum(len(graph.adj[v]) for v in outside))
        meter.tick("patch_universe_scan", len(graph.nodes))
        weights, scores = {}, {}
        for v in sorted(selected_region):
            meter.tick("exact_weight_conversion")
            weights[v] = Fraction(graph.nodes[v].weight)
            meter.tick("degree_priority", len(graph.adj[v]) + 1)
            scores[v] = (priorities[v] if priorities is not None else
                         weights[v] / max(1, len(graph.adj[v] & selected_region)))
        if max_patch_vertices is not None:
            extras = sorted(selected_region - destroy, key=lambda v: (-scores[v], v))
            meter.tick("patch_restriction_order", len(extras))
            selected_region = destroy | set(extras[:max_patch_vertices - len(destroy)])
        result = _solve(graph, selected_region, destroy, weights, lambda _: scores,
                        meter, node_budget, upper_pruning)
    except _Stopped as stop:
        result["termination"], result["budget_exhausted"] = str(stop), True
    local = set(result["local_selected"])
    updated = outside | local
    meter.sealed = True
    meter.tick("final_validation", len(updated) + sum(len(graph.adj[v]) for v in updated))
    if (not graph.feasible(updated) or not fixed <= updated or updated & excluded
            or _value(graph, updated) < _value(graph, incumbent)):
        raise AssertionError("Global patch monotonicity/feasibility invariant failed")
    return {**result, "selected": sorted(updated), "value_exact": str(_value(graph, updated)),
            "feasible": True, "destroy": sorted(destroy), "patch": sorted(selected_region),
            "full_region_size": len(full_region), "restricted": selected_region != full_region,
            "gain_exact": str(_value(graph, updated) - _value(graph, incumbent)),
            "scope": "restricted_induced_patch_with_outside_incumbent_fixed",
            "cpu_seconds": time.process_time() - meter.cpu_start,
            "wall_seconds": time.perf_counter() - meter.wall_start, "meter": dict(meter)}


def repair_schedule(graph, program=None, *, fixed=(), excluded=(), initial=None,
                    priority="program", seconds=5.0, clock="cpu", config=None, random_seed=1):
    """Uniform anytime kernel for program/Degree/random priorities.

    Default branch scope uses common Degree target/expansion/restriction and
    the chosen priority only inside capped patches. Optional target_and_branch
    scope also changes target/region ordering. Time starts before parsing,
    initializing or scoring. Budget
    exhaustion is normal anytime termination; programme errors are explicitly
    failed rows with the retained feasible incumbent for diagnosis, no fallback.
    """
    config = RepairConfig() if config is None else config
    if not isinstance(config, RepairConfig):
        raise TypeError("config must be RepairConfig")
    if priority not in ("program", "degree", "random"):
        raise ValueError("Unknown repair priority")
    if type(random_seed) is not int:
        raise ValueError("random_seed must be integer")
    meter = _Meter(seconds, clock, config.max_work, config.max_search_nodes)
    incumbent, fixed, excluded, legal = _boundary(graph, initial, fixed, excluded)
    starting_value = _value(graph, incumbent)
    seed_value, seed_selected = starting_value, sorted(incumbent)
    init_trace, patches = [], []
    initialized, improvements, attempted = False, 0, 0
    pending_patch = None
    status, error = "patch_limit", None
    rng = random.Random(random_seed)
    scores = None
    try:
        meter.tick("input_validation", len(graph.nodes) + len(graph.edges) + len(incumbent))
        if isinstance(program, dict):
            program = FeatureRuleProgram.from_dict(program)
        if priority == "program" and not isinstance(program, FeatureRuleProgram):
            raise ValueError("Program priority requires a typed FeatureRuleProgram")
        meter.check()
        weights = {}
        for v in sorted(graph.nodes):
            meter.tick("exact_weight_conversion")
            weights[v] = Fraction(graph.nodes[v].weight)
        _initialize(graph, incumbent, legal, weights, meter, init_trace)
        initialized, seed_value, seed_selected = True, _value(graph, incumbent), sorted(incumbent)
        while attempted < config.max_patches:
            meter.check()
            # The global target snapshot is the original F/X residual and does
            # not change as the incumbent changes. Reuse these exact scores;
            # each local patch is still scored on its own induced snapshot.
            if scores is None:
                target_priority = priority if config.policy_scope == "target_and_branch" else "degree"
                scores = _priorities(graph, legal, program, target_priority, rng, meter)
            outside_nodes = sorted(legal - incumbent, key=lambda v: (-scores[v], v))
            blockers = {}
            for v in outside_nodes:
                meter.tick("incumbent_blocker_scan", len(graph.adj[v]))
                blockers[v] = graph.adj[v] & incumbent
            seen, committed = set(), False
            for target in outside_nodes:
                if attempted >= config.max_patches:
                    break
                base = blockers[target]
                if not base or base & fixed or len(base) > config.max_destroy:
                    continue
                proposals = [set(base)]
                growing = set(base)
                for _ in range(config.expansion_steps):
                    # Expand through a competing candidate adjacent to D. The
                    # same rule/cap is shared by all arms; only rank differs.
                    extension = None
                    for v in outside_nodes:
                        meter.tick("region_expansion_scan")
                        extra = blockers[v] - growing
                        if (extra and blockers[v] & growing and not blockers[v] & fixed
                                and len(growing | extra) <= config.max_destroy):
                            extension = extra
                            break
                    if extension is None:
                        break
                    growing |= extension
                    proposals.append(set(growing))
                for destroy in proposals:
                    key = tuple(sorted(destroy))
                    if key in seen or attempted >= config.max_patches:
                        continue
                    seen.add(key)
                    attempted += 1
                    before = _value(graph, destroy)
                    record = {**_uncomputed_result(graph, destroy), "target": target,
                              "destroy": sorted(destroy), "patch": None, "full_region_size": None,
                              "restricted": None, "incumbent_patch_exact": str(before),
                              "gain_exact": "0", "committed": False, "stage": "region_construction"}
                    patches.append(record)
                    pending_patch = record
                    outside_fixed, region = _patch_region(graph, incumbent, destroy, excluded, meter)
                    full_region_size = len(region)
                    retained = set(destroy)
                    if len(retained) < config.max_patch_vertices:
                        retained.add(target)
                    extra = sorted(region - retained, key=lambda v: (-scores[v], v))
                    meter.tick("patch_restriction_order", len(extra))
                    region = retained | set(extra[:config.max_patch_vertices - len(retained)])
                    record.update(patch=sorted(region), full_region_size=full_region_size,
                                  restricted=len(region) != full_region_size, stage="local_search")
                    factory = lambda r: _priorities(graph, r, program, priority, rng, meter)
                    result = _solve(graph, region, destroy, weights, factory, meter,
                                    config.node_budget_per_patch, config.upper_pruning)
                    replacement = set(result["local_selected"])
                    gain = Fraction(result["lower_exact"]) - before
                    record.update(result)
                    record.update(gain_exact=str(gain), stage="returned")
                    if gain > 0:
                        updated = outside_fixed | replacement
                        # A valid improving witness found just before a cap is
                        # retained. Final validation may softly overshoot; its
                        # work/time is still charged, without dropping the gain.
                        prior_sealed = meter.sealed
                        meter.sealed = True
                        meter.tick("commit_validation", len(updated) + sum(len(graph.adj[v]) for v in updated))
                        meter.sealed = prior_sealed
                        if (not graph.feasible(updated) or not fixed <= updated or updated & excluded
                                or _value(graph, updated) <= _value(graph, incumbent)):
                            raise AssertionError("Repair attempted a nonimproving or infeasible commit")
                        incumbent = updated
                        improvements += 1
                        committed = True
                        record["committed"] = True
                    pending_patch = None
                    if meter.reason:
                        raise _Stopped(meter.reason)
                    if committed:
                        break
                if committed:
                    break
            if not committed:
                status = ("patch_limit" if attempted >= config.max_patches else
                          "no_improvement_in_attempted_patches")
                break
    except _Stopped as stop:
        status = str(stop)
        if pending_patch is not None:
            pending_patch.update(termination=str(stop), budget_exhausted=True)
    except Exception as failure:
        status = "programme_or_repair_error"
        error = {"type": type(failure).__name__, "message": str(failure)}
        if pending_patch is not None:
            pending_patch.update(termination="programme_or_repair_error", error=error)
    if not initialized:
        seed_value, seed_selected = _value(graph, incumbent), sorted(incumbent)
    # Audit the retained incumbent even if the cooperative deadline has passed.
    # Its unavoidable cost/overshoot remains in the returned execution timings.
    meter.sealed = True
    meter.tick("final_validation", len(incumbent) + sum(len(graph.adj[v]) for v in incumbent))
    if not graph.feasible(incumbent) or not fixed <= incumbent or incumbent & excluded:
        raise AssertionError("Retained anytime incumbent violates the original boundary")
    value = _value(graph, incumbent)
    if value < starting_value:
        raise AssertionError("Repair lost its starting incumbent")
    return {"selected": sorted(incumbent), "value": graph.value(incumbent), "value_exact": str(value),
            "feasible": True, "completed": error is None, "incumbent_available": True,
            "status": status, "error": error, "fallback_used": False,
            "budget_exhausted": meter.reason is not None or any(p["budget_exhausted"] for p in patches),
            "global_budget_exhausted": meter.reason is not None,
            "patch_node_budget_exhaustions": sum(p["patch_node_budget_exhausted"] for p in patches),
            "initialization_complete": initialized,
            "starting_value_exact": str(starting_value), "initial_value_exact": str(seed_value),
            "initial_selected": seed_selected, "initializer_trace": init_trace,
            "improvements": improvements, "patches_attempted": attempted, "patch_trace": patches,
            "priority": priority, "random_seed": random_seed, "config": asdict(config),
            "priority_role": "local_greedy_and_pivot_vertex; shared_include_first_traversal",
            "global_priority_snapshot": "original_fixed_excluded_residual",
            "declared_seconds": seconds, "deadline_clock": clock,
            "cpu_seconds": time.process_time() - meter.cpu_start,
            "wall_seconds": time.perf_counter() - meter.wall_start, "meter": dict(meter),
            "exact_optimum_claimed": False,
            "scope": "anytime_feasible_independent_set; exactness only for explicit restricted patches",
            "online_model_calls": 0, "conditional_oracle_calls": 0}
