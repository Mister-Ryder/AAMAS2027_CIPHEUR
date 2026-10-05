"""Bounded current-instance evolution of declarative scheduling recipes.

There are at most four live genomes.  No historical fit/quality table is read.
The solver supplies *raw* feasible-proposal gain and charged CPU time; rejected
negative proposals must not be rewritten to zero before ``observe``.  Current
archive consistency can break an otherwise equal selection score, but cannot
replace quality/cost feedback.  All controller work belongs in the solver clock.

LLM provenance is deliberately external: typed templates are not evidence that
a model was called.  Mutations only compose these supplied feature templates.
"""
from __future__ import annotations

import ast
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Integral, Real
import random
from typing import Callable, Mapping


BASE_NAMES = ("weight", "duration", "degree", "conflict_weight",
              "max_conflict_weight", "compatible_weight", "station_gap",
              "satellite_gap", "remaining_count")
MAX_POPULATION = 4
COEFFICIENT_BOUND = 16.0
EVOLVE_EVERY = 8
EMA_DECAY = 0.8
DEFAULT_CONFIG = {
    "credit_metric": "relative_gain_per_cpu", "evolve_every": 8,
    "parameter_mode": "additive", "structural_mode": "legacy_mixed",
    "paired_race": False,
}


def validate_controller_config(config=None) -> dict:
    """Optional strict overrides; None exactly preserves the r1 policy."""
    if config is None:
        return deepcopy(DEFAULT_CONFIG)
    if not isinstance(config, Mapping) or set(config) - set(DEFAULT_CONFIG):
        raise ValueError("Unknown controller configuration fields")
    result = {**DEFAULT_CONFIG, **config}
    domains = {
        "credit_metric": {"absolute_signed_gain_per_cpu", "relative_gain_per_cpu"},
        "parameter_mode": {"additive", "bounded_relative"},
        "structural_mode": {"legacy_mixed", "atomic_template", "same_operator_rewrite"},
    }
    for field, values in domains.items():
        if not isinstance(result[field], str) or result[field] not in values:
            raise ValueError("Invalid " + field)
    if type(result["evolve_every"]) is not int or result["evolve_every"] not in (8, 32, 64):
        raise ValueError("evolve_every must be 8, 32 or 64 credit updates")
    if type(result["paired_race"]) is not bool:
        raise ValueError("paired_race must be a boolean")
    return result


def _hash(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _choice(rng, values):
    if not values:
        raise ValueError("Cannot choose from an empty collection")
    index = rng.randrange(len(values)) if hasattr(rng, "randrange") else int(rng.integers(len(values)))
    return values[index]


def _normal(rng, scale: float) -> float:
    return rng.gauss(0.0, scale) if hasattr(rng, "gauss") else float(rng.normal(0.0, scale))


def _validate(recipe: dict) -> dict:
    from .typed import validate_recipe
    candidate = deepcopy(recipe)
    validate_recipe(candidate)
    return candidate


def _ast_size(expression: dict) -> tuple[int, int]:
    children = [_ast_size(child) for child in expression.get("args", [])]
    return (1 + sum(size for size, _ in children),
            1 + max((depth for _, depth in children), default=0))


def _ops(expression: dict) -> set[str]:
    answer = {expression["op"]}
    for child in expression.get("args", []):
        answer.update(_ops(child))
    return answer


def _replace_feature(rule: str, name: str) -> str:
    class Remove(ast.NodeTransformer):
        def visit_Name(self, node):
            return ast.copy_location(ast.Constant(0.0), node) if node.id == name else node
    return ast.unparse(ast.fix_missing_locations(Remove().visit(ast.parse(rule, mode="eval"))))


def _bind_semantic_rule(rule, coefficients, feature_mapping):
    """Bind a whole supplied rule block, never an invented structural term."""
    class Bind(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in {f"c{i}" for i in range(4)}:
                return ast.copy_location(ast.Constant(float(coefficients[int(node.id[1])])), node)
            if node.id in feature_mapping:
                return ast.copy_location(ast.Name(feature_mapping[node.id], ctx=ast.Load()), node)
            return node
    return ast.unparse(ast.fix_missing_locations(Bind().visit(ast.parse(rule, mode="eval"))))


def _tree_distance(left, right):
    distance = int(left["op"] != right["op"])
    if left["op"] == right["op"] == "const":
        return int(left["value"] != right["value"])
    a, b = left.get("args", []), right.get("args", [])
    distance += sum(_tree_distance(x, y) for x, y in zip(a, b))
    distance += sum(_ast_size(x)[0] for x in a[len(b):])
    distance += sum(_ast_size(x)[0] for x in b[len(a):])
    return distance


@dataclass(frozen=True)
class Genome:
    id: str
    recipe: dict
    origin_name: str
    parent_id: str | None
    generation: int
    mutation_kind: str
    program_hash: str
    representation_hash: str
    coefficient_centers: tuple[float, ...] = ()

    @property
    def coefficients(self):
        return self.recipe["coefficients"]

    @property
    def features(self):
        return self.recipe["features"]

    @property
    def rule(self):
        return self.recipe["rule"]

    @property
    def patch_policy(self):
        return self.recipe["patch_policy"]

    def to_dict(self) -> dict:
        return {"id": self.id, "recipe": deepcopy(self.recipe),
                "origin_name": self.origin_name, "parent_id": self.parent_id,
                "generation": self.generation, "mutation_kind": self.mutation_kind,
                "program_hash": self.program_hash,
                "representation_hash": self.representation_hash,
                "coefficient_centers": list(self.coefficient_centers)}


@dataclass
class _Credit:
    selections: int = 0
    observations: int = 0
    positive: int = 0
    negative: int = 0
    gain_ticks: int = 0
    cpu_seconds: float = 0.0
    ema_reward: float = 0.0
    ema_cpu: float = 0.0
    fit_sum: float = 0.0
    fit_observations: int = 0

    @property
    def rate(self) -> float:
        return self.ema_reward / max(self.ema_cpu, 1e-6) if self.observations else 0.0

    @property
    def certificate_fit(self) -> float | None:
        return self.fit_sum / self.fit_observations if self.fit_observations else None

    def to_dict(self):
        return {**vars(self), "fitness_rate": self.rate,
                "certificate_fit": self.certificate_fit}


class OnlineController:
    """Select/observe/mutate interface; call ``reset`` at each cold instance.

    ``recipes`` may be the strict bank object or its list.  A returned Genome is
    read-only by contract; use ``to_dict`` when an independent copy is required.
    ``progress`` is audit context, never a historical selection prior.
    Modes: online; fixed (same initial portfolio, round-robin); coefficients_only.
    A synchronous log_callback receives full genesis/mutation records, so the
    complete replay log can be streamed without retaining an unbounded pool.
    """

    def __init__(self, recipes, instance_id: str = "instance", *, mode="online",
                 seed: int = 2, log_callback: Callable[[dict], None] | None = None,
                 config: Mapping | None = None):
        if isinstance(recipes, Mapping):
            if set(recipes) != {"schema_version", "recipes"} or recipes["schema_version"] != "stk_online_llm_v2":
                raise ValueError("Expected the strict stk_online_llm_v2 recipe bank")
            recipes = recipes["recipes"]
        if not isinstance(recipes, list) or not 1 <= len(recipes) <= 32:
            raise ValueError("Supply one to 32 unscored recipes")
        if mode not in {"online", "fixed", "coefficients_only"}:
            raise ValueError("Unknown controller mode")
        self._library = tuple(_validate(recipe) for recipe in recipes)
        if len({recipe["name"] for recipe in self._library}) != len(self._library):
            raise ValueError("Seed recipe names must be unique")
        self.mode, self.seed, self.log_callback = mode, int(seed), log_callback
        self.config = validate_controller_config(config)
        self.config_source = "legacy_defaults" if config is None else "caller_provided"
        self.events = deque(maxlen=256)  # Audit buffer, not optimizer population.
        self.reset(instance_id)

    @property
    def population(self) -> tuple[Genome, ...]:
        return tuple(self._genomes.values())

    @property
    def statistics(self) -> dict:
        return {identifier: credit.to_dict() for identifier, credit in self._credits.items()}

    def _emit(self, event: str, **fields):
        record = {"event": event, "instance_id": self.instance_id,
                  "selected_count": self.selected_count,
                  "update_count": self.update_count, **fields}
        self.events.append(record)
        if self.log_callback is not None:
            self.log_callback(deepcopy(record))

    def reset(self, instance_id: str | None = None):
        if instance_id is not None:
            if not isinstance(instance_id, str) or not instance_id:
                raise ValueError("instance_id must be a nonempty string")
            self.instance_id = instance_id
        self.events.clear()
        self._genomes: dict[str, Genome] = {}
        self._credits: dict[str, _Credit] = {}
        self._serial = 0
        self._library_cursor = min(MAX_POPULATION, len(self._library))
        self.selected_count = self.update_count = self.mutation_count = 0
        self.cycle_notifications = self.witness_mutations = 0
        self.stagnation_count = self._last_evolution = 0
        self._pending_witness: dict | None = None
        self._rng = random.Random(self.seed)
        for recipe in self._library[:MAX_POPULATION]:
            self._install(deepcopy(recipe), origin_name=recipe["name"], mutation_kind="seed")
        self._emit("reset", mode=self.mode, seed=self.seed,
                   population_size=len(self._genomes), historical_prior_used=False,
                   config=deepcopy(self.config), config_source=self.config_source,
                   config_sha256=_hash(self.config))

    def _install(self, recipe, *, origin_name, parent=None, mutation_kind, centers=None):
        candidate = _validate(recipe)
        self._serial += 1
        identifier = f"{_hash(self.instance_id)[:10]}.g{self._serial:06d}"
        semantic = {key: value for key, value in candidate.items() if key not in {"name", "rationale"}}
        if centers is None:
            centers = parent.coefficient_centers if parent is not None else candidate["coefficients"]
        genome = Genome(identifier, candidate, origin_name,
                        parent.id if parent else None, (parent.generation + 1) if parent else 0,
                        mutation_kind, _hash(semantic),
                        _hash({"features": candidate["features"],
                               "feature_scope": candidate["evaluation_plan"]["feature_scope"]}),
                        tuple(float(value) for value in centers))
        removed = None
        if len(self._genomes) >= MAX_POPULATION:
            # Keep the parent when possible.  Credit belongs only to live genomes.
            possible = [g for g in self.population if parent is None or g.id != parent.id]
            removed = min(possible or list(self.population),
                          key=lambda g: (self._credits[g.id].rate,
                                         self._credits[g.id].observations, g.id))
            del self._genomes[removed.id]
            del self._credits[removed.id]
        self._genomes[genome.id], self._credits[genome.id] = genome, _Credit()
        self._emit("genome_created", genome=genome.to_dict(),
                   retired_id=removed.id if removed else None,
                   actual_program_changed=parent is None or genome.program_hash != parent.program_hash,
                   actual_representation_changed=parent is not None and genome.representation_hash != parent.representation_hash)
        return genome

    def _index(self, genome: Genome) -> float:
        credit = self._credits[genome.id]
        if not credit.observations:
            return math.inf
        exploration = 0.25 * math.sqrt(math.log(self.update_count + 2) / credit.observations)
        if self.config["credit_metric"] == "absolute_signed_gain_per_cpu":
            # Exploration has tick units too; it is not an unscaled0.25 ticks.
            scale = max((abs(c.ema_reward) for c in self._credits.values() if c.observations), default=1.)
            exploration *= max(scale, 1.)
        return (credit.ema_reward + exploration) / max(credit.ema_cpu, 1e-6)

    def _best_parent(self) -> Genome:
        return max(self.population,
                   key=lambda genome: (self._credits[genome.id].rate,
                                       self._credits[genome.id].observations,
                                       genome.id))

    def _maybe_evolve(self, rng):
        if self.mode == "fixed" or not self.update_count:
            return
        if self._pending_witness is not None and self.mode == "online":
            pending, self._pending_witness = self._pending_witness, None
            parent = self._best_parent()
            child = self._witness_mutant(parent, rng)
            if child is None:
                self._emit("witness_mutation_unavailable", **pending,
                           reason="No supplied template with set-neighbor/incident-edge structure")
            else:
                self.witness_mutations += 1
                self._emit("witness_mutation", id=child.id, **pending,
                           witness_distinguished=False, ranking_repaired=False)
            self._last_evolution = self.update_count
            return
        parent = self._best_parent()
        threshold = parent.recipe["adaptation_template"]["stagnation_trials"]
        if self.update_count - self._last_evolution < self.config["evolve_every"]:
            return
        action = parent.recipe["adaptation_template"]["action"] if self.stagnation_count >= threshold else "mutate"
        if action == "switch_recipe" and self.mode == "online" and self._library_cursor < len(self._library):
            recipe = deepcopy(self._library[self._library_cursor])
            self._library_cursor += 1
            child = self._install(recipe, origin_name=recipe["name"], parent=parent,
                                  mutation_kind="lazy_recipe_switch", centers=recipe["coefficients"])
            self.mutation_count += 1
        else:
            if action == "diversify":
                parent = _choice(rng, list(self.population))
            child = self.mutate(parent, rng)
        self._last_evolution = self.update_count
        self._emit("adaptation", action=action, id=child.id,
                   stagnation_count=self.stagnation_count)

    def select(self, rng=None, progress=None) -> Genome:
        rng = self._rng if rng is None else rng
        self._maybe_evolve(rng)
        if self.mode == "fixed":
            # Same seed coverage as online, with no feedback-driven allocation.
            candidates = [self.population[self.selected_count % len(self.population)]]
        else:
            unobserved = [g for g in self.population if not self._credits[g.id].observations]
            if unobserved:
                candidates = unobserved
            else:
                indices = {g.id: self._index(g) for g in self.population}
                best = max(indices.values())
                candidates = [g for g in self.population if abs(indices[g.id] - best) <= 1e-9]
        fit_tiebreak = False
        if len(candidates) > 1 and all(self._credits[g.id].certificate_fit is not None for g in candidates):
            best_fit = max(self._credits[g.id].certificate_fit for g in candidates)
            narrowed = [g for g in candidates if self._credits[g.id].certificate_fit == best_fit]
            fit_tiebreak = len(narrowed) < len(candidates)
            candidates = narrowed
        genome = _choice(rng, candidates)
        self._credits[genome.id].selections += 1
        self.selected_count += 1
        self._emit("selected", id=genome.id, program_hash=genome.program_hash,
                   representation_hash=genome.representation_hash,
                   current_archive_fit_tiebreak=fit_tiebreak,
                   progress=deepcopy(progress))
        return genome

    def observe(self, identifier: str, gain_ticks: int, removed_ticks: int,
                cpu_seconds: float, cert_fit: float | None = None) -> dict:
        if identifier not in self._credits:
            raise KeyError("Observe only a live genome returned by this instance")
        if (isinstance(gain_ticks, bool) or not isinstance(gain_ticks, Integral)
                or isinstance(removed_ticks, bool) or not isinstance(removed_ticks, Integral)
                or removed_ticks < 0):
            raise ValueError("Gain and removed weight require exact integer ticks")
        if isinstance(cpu_seconds, bool) or not isinstance(cpu_seconds, Real) or not math.isfinite(cpu_seconds) or cpu_seconds < 0:
            raise ValueError("Charged CPU seconds must be finite and nonnegative")
        if cert_fit is not None and (isinstance(cert_fit, bool) or not isinstance(cert_fit, Real)
                                     or not math.isfinite(cert_fit) or not 0 <= cert_fit <= 1):
            raise ValueError("cert_fit is None or current-instance archive fit in [0,1]")
        credit = self._credits[identifier]
        absolute = self.config["credit_metric"] == "absolute_signed_gain_per_cpu"
        reward = (float(gain_ticks) if absolute
                  else max(-1.0, min(1.0, int(gain_ticks) / max(int(removed_ticks), 1))))
        cost = max(float(cpu_seconds), 1e-6)
        if not credit.observations:
            credit.ema_reward, credit.ema_cpu = reward, cost
        else:
            credit.ema_reward = EMA_DECAY * credit.ema_reward + (1 - EMA_DECAY) * reward
            credit.ema_cpu = EMA_DECAY * credit.ema_cpu + (1 - EMA_DECAY) * cost
        credit.observations += 1
        credit.positive += int(gain_ticks > 0)
        credit.negative += int(gain_ticks < 0)
        credit.gain_ticks += int(gain_ticks)
        credit.cpu_seconds += float(cpu_seconds)
        if cert_fit is not None:
            credit.fit_sum += float(cert_fit)
            credit.fit_observations += 1
        self.update_count += 1
        self.stagnation_count = 0 if gain_ticks > 0 else self.stagnation_count + 1
        result = {"id": identifier, "gain_ticks": int(gain_ticks),
                  "removed_ticks": int(removed_ticks), "cpu_seconds": float(cpu_seconds),
                  "reward": reward, "fitness_rate": credit.rate,
                  "credit_metric": self.config["credit_metric"],
                  "reward_units": "signed_ticks" if absolute else "clipped_relative_gain",
                  "cert_fit": None if cert_fit is None else float(cert_fit),
                  "cert_fit_source": "current_instance_archive" if cert_fit is not None else None,
                  "program_hash": self._genomes[identifier].program_hash}
        self._emit("updated", **result)
        return result

    def _parameter_mutation(self, recipe: dict, rng, centers=None):
        scales = recipe["adaptation_template"]["mutation_scales"]
        if self.config["parameter_mode"] == "bounded_relative":
            centers = recipe["coefficients"] if centers is None else centers
            result = []
            for center, scale in zip(centers, scales):
                if center == 0:
                    result.append(0.0)
                    continue
                # Center and sign come from the semantic seed/block.  Mutation
                # cannot enable a zero coefficient or reverse a seed's sign.
                delta = _normal(rng, abs(center) * min(float(scale), .5))
                lower, upper = sorted((.5 * center, 1.5 * center))
                result.append(max(-COEFFICIENT_BOUND, min(COEFFICIENT_BOUND,
                                   max(lower, min(upper, center + delta)))))
            recipe["coefficients"] = result
            return
        recipe["coefficients"] = [max(-COEFFICIENT_BOUND, min(COEFFICIENT_BOUND,
                                            value + _normal(rng, scale)))
                                  for value, scale in zip(recipe["coefficients"], scales)]

    def _feature_templates(self, *, broader=False):
        templates = []
        for recipe in self._library:
            for feature in recipe["features"]:
                if not broader or {"neighbors_of_set", "incident_edges"} & _ops(feature["expression"]):
                    templates.append(feature)
        return templates

    def _attach_feature(self, recipe: dict, feature: dict, rng):
        feature = deepcopy(feature)
        used = set(BASE_NAMES) | {f"c{i}" for i in range(4)} | {f["name"] for f in recipe["features"]}
        name = feature["name"]
        suffix = 0
        while name in used:
            suffix += 1
            name = f"online_f{self._serial}_{suffix}"
        feature["name"] = name
        if len(recipe["features"]) >= 6:
            dropped = recipe["features"].pop(_choice(rng, list(range(len(recipe["features"])))))
            recipe["rule"] = _replace_feature(recipe["rule"], dropped["name"])
        recipe["features"].append(feature)
        available = ([i for i, value in enumerate(recipe["coefficients"]) if value != 0]
                     if self.config["parameter_mode"] == "bounded_relative" else list(range(4)))
        if not available:
            raise ValueError("Bounded-relative mutation cannot activate a zero seed coefficient")
        coefficient = _choice(rng, available)
        if self.config["parameter_mode"] == "additive" and abs(recipe["coefficients"][coefficient]) < 1e-12:
            recipe["coefficients"][coefficient] = 1.0
        recipe["rule"] = f"({recipe['rule']}) + c{coefficient} * {name}"

    def _structural_mutation(self, recipe: dict, rng, kind: str):
        templates = self._feature_templates()
        if kind == "feature_mask" and recipe["features"]:
            feature = recipe["features"].pop(_choice(rng, list(range(len(recipe["features"])))))
            recipe["rule"] = _replace_feature(recipe["rule"], feature["name"])
        elif kind == "feature_fusion" and templates:
            left, right = _choice(rng, templates), _choice(rng, templates)
            expression = {"op": "add", "args": [deepcopy(left["expression"]), deepcopy(right["expression"])]}
            size, depth = _ast_size(expression)
            if size > 48 or depth > 8:
                expression = deepcopy(left["expression"])
            self._attach_feature(recipe, {"name": "online_fusion", "expression": expression}, rng)
        elif kind == "feature_import" and templates:
            self._attach_feature(recipe, _choice(rng, templates), rng)
        else:
            # Recombine the safe rule itself, not merely its coefficients.
            variable = _choice(rng, list(BASE_NAMES) + [f["name"] for f in recipe["features"]])
            available = ([i for i, value in enumerate(recipe["coefficients"]) if value != 0]
                         if self.config["parameter_mode"] == "bounded_relative" else list(range(4)))
            if not available:
                raise ValueError("Bounded-relative mutation cannot activate a zero seed coefficient")
            coefficient = _choice(rng, available)
            if self.config["parameter_mode"] == "additive" and abs(recipe["coefficients"][coefficient]) < 1e-12:
                recipe["coefficients"][coefficient] = 1.0
            recipe["rule"] = f"({recipe['rule']}) + c{coefficient} * {variable}"

    def _policy_mutation(self, recipe: dict, rng):
        policy = recipe["patch_policy"]
        field = _choice(rng, ["anchor", "destroy_count", "patch_cap", "expand_hops", "reconstruction"])
        values = {"anchor": ["uniform", "blocked_gain", "rejection_frontier", "resource_boundary"],
                  "destroy_count": list(range(1, 13)), "patch_cap": [16, 24, 32, 48, 64],
                  "expand_hops": [1, 2], "reconstruction": ["greedy", "rcl", "exchange"]}[field]
        policy[field] = _choice(rng, [value for value in values if value != policy[field]])

    def _atomic_template_recipe(self, parent: Genome, rng, *, broader=False):
        """Mix two intact supplied semantic score blocks, with <=3 features.

        Seed coefficients are bound inside each block. Only the two outer
        mixture coefficients can evolve; declared input fields are not dropped
        to make an oversized pair fit. Invalid/oversized pairs are unavailable.
        """
        left = next(recipe for recipe in self._library if recipe["name"] == parent.origin_name)
        signature = lambda recipe: _hash({key: recipe[key] for key in ("features", "rule", "coefficients")})
        donors = [recipe for recipe in self._library if signature(recipe) != signature(left)
                  and (not broader or any({"neighbors_of_set", "incident_edges"} & _ops(f["expression"])
                                          for f in recipe["features"]))]
        # Bounded randomized traversal, not a quality/fit search.
        candidates = []
        while donors:
            donor = _choice(rng, donors)
            donors.remove(donor)
            candidates.append(donor)
        for donor in candidates[:8]:
            recipe, features, expressions, used = deepcopy(parent.recipe), [], {}, set(BASE_NAMES) | {
                "neighbor_weight_sum", "neighbor_max_weight", "active_count", "min", "max", "abs",
                "c0", "c1", "c2", "c3"}
            mappings = []
            for block in (left, donor):
                mapping = {}
                for feature in block["features"]:
                    key = _hash(feature["expression"])
                    if key not in expressions:
                        name = feature["name"]
                        if name in used:
                            name = f"block_f{len(features)}"
                            while name in used:
                                name += "_x"
                        used.add(name)
                        features.append({"name": name, "expression": deepcopy(feature["expression"])})
                        expressions[key] = name
                    mapping[feature["name"]] = expressions[key]
                mappings.append(mapping)
            if len(features) > 3:
                continue
            first = _bind_semantic_rule(left["rule"], left["coefficients"], mappings[0])
            second = _bind_semantic_rule(donor["rule"], donor["coefficients"], mappings[1])
            recipe["features"] = features
            recipe["rule"] = f"c0 * ({first}) + c1 * ({second})"
            centers = [.5, .5, 0., 0.]
            recipe["coefficients"] = centers.copy()
            try:
                _validate(recipe)
            except (ValueError, TypeError, SyntaxError):
                continue
            return recipe, centers, {"source_names": [left["name"], donor["name"]],
                                     "source_semantic_hashes": [signature(left), signature(donor)],
                                     "whole_score_blocks_preserved": True}
        return None

    def _same_operator_recipe(self, parent: Genome, rng, *, broader=False):
        """Replace one Number tree by a close, same-outer-op supplied tree."""
        if not parent.features or len(parent.features) > 3:
            return None
        options = []
        for index, feature in enumerate(parent.features):
            original = feature["expression"]
            for template in self._feature_templates(broader=broader):
                proposed = template["expression"]
                if proposed["op"] != original["op"] or _hash(proposed) == _hash(original):
                    continue
                distance = _tree_distance(original, proposed)
                limit = max(2, math.ceil(.35 * max(_ast_size(original)[0], _ast_size(proposed)[0])))
                if distance <= limit:
                    options.append((index, template, distance))
        if not options:
            return None
        index, template, distance = _choice(rng, options)
        recipe = deepcopy(parent.recipe)
        recipe["features"][index]["expression"] = deepcopy(template["expression"])
        return recipe, list(parent.coefficient_centers), {
            "feature_name": recipe["features"][index]["name"], "source_feature_name": template["name"],
            "outer_operator": template["expression"]["op"], "tree_distance": distance,
            "supplied_expression_hash": _hash(template["expression"])}

    def _configured_structure(self, parent, rng, *, broader=False):
        if self.config["structural_mode"] == "atomic_template":
            return self._atomic_template_recipe(parent, rng, broader=broader)
        if self.config["structural_mode"] == "same_operator_rewrite":
            return self._same_operator_recipe(parent, rng, broader=broader)
        return None

    def mutate(self, parent: Genome | str, rng=None) -> Genome:
        if self.mode == "fixed":
            raise RuntimeError("Fixed-controller ablation cannot mutate")
        rng = self._rng if rng is None else rng
        parent = self._genomes[parent] if isinstance(parent, str) else parent
        if parent.id not in self._genomes:
            raise KeyError("Mutation parent must belong to the current live population")
        if self.mode == "online" and self.config["structural_mode"] != "legacy_mixed":
            proposal = self._configured_structure(parent, rng)
            if proposal is not None:
                recipe, centers, details = proposal
                self._parameter_mutation(recipe, rng, centers)
                self._policy_mutation(recipe, rng)
                child = self._install(recipe, origin_name=parent.origin_name, parent=parent,
                                      mutation_kind=self.config["structural_mode"], centers=centers)
                self.mutation_count += 1
                self._emit("semantic_structure_mutation", id=child.id, **details)
                return child
            self._emit("structural_mutation_unavailable", parent_id=parent.id,
                       structural_mode=self.config["structural_mode"],
                       reason="No valid <=3-feature supplied block pair or close same-operator tree")
            # Preserve a usable online path without inventing a new structural
            # formula. This fallback is explicitly not representation repair.
            recipe = deepcopy(parent.recipe)
            self._parameter_mutation(recipe, rng, parent.coefficient_centers)
            self._policy_mutation(recipe, rng)
            child = self._install(recipe, origin_name=parent.origin_name, parent=parent,
                                  mutation_kind="parameter_policy_only_structure_unavailable")
            self.mutation_count += 1
            return child
        for _ in range(8):
            recipe = deepcopy(parent.recipe)
            self._parameter_mutation(recipe, rng, parent.coefficient_centers)
            if self.mode == "coefficients_only":
                kind = "coefficients_only"
            else:
                kind = _choice(rng, ["feature_mask", "feature_import", "feature_fusion", "rule_splice"])
                try:
                    self._structural_mutation(recipe, rng, kind)
                except ValueError:
                    continue
                self._policy_mutation(recipe, rng)
            try:
                _validate(recipe)
            except (ValueError, TypeError, SyntaxError):
                continue
            child = self._install(recipe, origin_name=parent.origin_name, parent=parent, mutation_kind=kind)
            self.mutation_count += 1
            return child
        # A bounded valid rule substitution, using the parent's own variables.
        recipe = deepcopy(parent.recipe)
        if self.config["parameter_mode"] == "bounded_relative":
            self._parameter_mutation(recipe, rng, parent.coefficient_centers)
            if self.mode == "online":
                self._policy_mutation(recipe, rng)
            child = self._install(recipe, origin_name=parent.origin_name, parent=parent,
                                  mutation_kind="parameter_policy_only_structure_unavailable")
            self.mutation_count += 1
            return child
        if self.mode == "online":
            variable = parent.features[0]["name"] if parent.features else "degree"
            recipe["rule"] = f"weight / max(1, abs({variable}) + abs(c0))"
            recipe["coefficients"][0] = 1.0 if recipe["coefficients"][0] != 1.0 else 2.0
            kind = "bounded_rule_recombination"
        else:
            recipe["coefficients"][0] = -recipe["coefficients"][0] or 1.0
            kind = "bounded_coefficient_mutation"
        child = self._install(recipe, origin_name=parent.origin_name, parent=parent, mutation_kind=kind)
        self.mutation_count += 1
        return child

    def notify_cycle(self, witness_id: str, proof: Mapping):
        """Notify a *verified current-instance* archive cycle, not a fit failure.

        The independent exact-quotient archive supplies has_cycle=True.  No claim
        of repaired information/ranking is made until separately measured.
        """
        if not isinstance(witness_id, str) or not witness_id:
            raise ValueError("A nonempty actual cycle witness ID is required")
        if not isinstance(proof, Mapping) or proof.get("has_cycle") is not True:
            raise ValueError("Only an actual complete-quotient cycle may trigger this path")
        if proof.get("instance_id", self.instance_id) != self.instance_id:
            raise ValueError("Cross-instance cycle notifications are not allowed")
        self.cycle_notifications += 1
        self._pending_witness = {"witness_id": witness_id, "proof_hash": _hash(dict(proof))}
        self._emit("cycle_notified", **self._pending_witness)

    def _witness_mutant(self, parent: Genome, rng) -> Genome | None:
        if self.config["structural_mode"] != "legacy_mixed":
            proposal = self._configured_structure(parent, rng, broader=True)
            if proposal is None:
                return None
            recipe, centers, details = proposal
            self._parameter_mutation(recipe, rng, centers)
            child = self._install(recipe, origin_name=parent.origin_name, parent=parent,
                                  mutation_kind="current_cycle_" + self.config["structural_mode"], centers=centers)
            self.mutation_count += 1
            self._emit("semantic_structure_mutation", id=child.id, **details)
            return child
        templates = self._feature_templates(broader=True)
        if not templates:
            return None
        for template in templates:
            recipe = deepcopy(parent.recipe)
            self._parameter_mutation(recipe, rng, parent.coefficient_centers)
            try:
                self._attach_feature(recipe, template, rng)
            except ValueError:
                continue
            try:
                _validate(recipe)
            except (ValueError, TypeError, SyntaxError):
                continue
            child = self._install(recipe, origin_name=parent.origin_name, parent=parent,
                                  mutation_kind="current_cycle_feature_import")
            self.mutation_count += 1
            return child
        return None

    def snapshot(self) -> dict:
        return {"instance_id": self.instance_id, "mode": self.mode,
                "config": deepcopy(self.config), "config_source": self.config_source,
                "config_sha256": _hash(self.config),
                "selected_count": self.selected_count, "update_count": self.update_count,
                "mutation_count": self.mutation_count,
                "cycle_notifications": self.cycle_notifications,
                "witness_mutations": self.witness_mutations,
                "stagnation_count": self.stagnation_count,
                "population": [genome.to_dict() for genome in self.population],
                "statistics": self.statistics, "historical_prior_used": False}
