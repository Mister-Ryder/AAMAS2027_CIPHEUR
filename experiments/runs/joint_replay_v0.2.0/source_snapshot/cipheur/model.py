from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from typing import Iterable


@dataclass(frozen=True)
class Contact:
    id: str
    weight: float
    satellite: str
    station: str
    start: float
    end: float
    task: str = ""


@dataclass
class Graph:
    name: str
    contacts: tuple[Contact, ...]
    edges: frozenset[tuple[str, str]]
    constraints: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        self.nodes = {c.id: c for c in self.contacts}
        if len(self.nodes) != len(self.contacts):
            raise ValueError("Duplicate contact ids")
        for c in self.contacts:
            if not all(math.isfinite(v) for v in (c.weight, c.start, c.end)) or c.weight < 0 or c.end <= c.start:
                raise ValueError("Contacts require finite nonnegative weights and positive duration")
        try:
            if not math.isfinite(math.fsum(c.weight for c in self.contacts)):
                raise ValueError("Total graph weight must be representable")
        except OverflowError as error:
            raise ValueError("Total graph weight must be representable") from error
        canonical = set()
        for a, b in self.edges:
            if a == b or a not in self.nodes or b not in self.nodes:
                raise ValueError("Invalid graph edge")
            canonical.add(tuple(sorted((a, b))))
        self.edges = frozenset(canonical)
        self.adj = {k: set() for k in self.nodes}
        for a, b in self.edges:
            self.adj[a].add(b)
            self.adj[b].add(a)

    def feasible(self, selected: Iterable[str]) -> bool:
        ids = tuple(selected)
        chosen = set(ids)
        return len(ids) == len(chosen) and chosen <= self.nodes.keys() and all(
            not self.adj[v].intersection(chosen) for v in chosen
        )

    def value(self, selected: Iterable[str]) -> float:
        return math.fsum(self.nodes[v].weight for v in selected)

    def available(self, fixed=(), excluded=()) -> set[str]:
        fixed = tuple(fixed)
        excluded = set(excluded)
        if not set(excluded) <= self.nodes.keys():
            raise ValueError("Unknown excluded node")
        if not self.feasible(fixed) or set(fixed).intersection(excluded):
            raise ValueError("Invalid fixed boundary")
        blocked = set(fixed) | set(excluded)
        for v in fixed:
            blocked.update(self.adj[v])
        return set(self.nodes) - blocked

    def to_dict(self) -> dict:
        return {"name": self.name, "contacts": [asdict(c) for c in self.contacts],
                "edges": [list(e) for e in sorted(self.edges)],
                "constraints": self.constraints, "provenance": self.provenance}

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], tuple(Contact(**c) for c in d["contacts"]),
                   frozenset(tuple(e) for e in d["edges"]), d.get("constraints", {}),
                   d.get("provenance", {}))

    def digest(self) -> str:
        d = self.to_dict()
        d.pop("name")
        d.pop("provenance")
        return sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def temporal_graph(name: str, contacts, station_gap=0.0, satellite_gap=0.0) -> Graph:
    """Single-capacity synthetic model; intentionally separate from V51 rules."""
    if not all(math.isfinite(g) and g >= 0 for g in (station_gap, satellite_gap)):
        raise ValueError("Switching gaps must be nonnegative")
    contacts = tuple(contacts)
    edges = set()
    for i, a in enumerate(contacts):
        for b in contacts[i + 1:]:
            first, second = sorted((a, b), key=lambda c: (c.start, c.id))
            if (a.station == b.station and second.start < first.end + station_gap) or (
                a.satellite == b.satellite and second.start < first.end + satellite_gap
            ) or (a.task and a.task == b.task):
                edges.add(tuple(sorted((a.id, b.id))))
    return Graph(name, contacts, frozenset(edges),
                 {"station_gap": station_gap, "satellite_gap": satellite_gap,
                  "model": "synthetic_single_capacity_temporal"})


def reversal_fixture(scale=1.0, suffix="") -> tuple[Graph, Graph]:
    contacts = (
        Contact("a" + suffix, 8 * scale, "s1", "g1", 0, 2),
        Contact("b" + suffix, 5 * scale, "s2", "g1", 0, 1),
        Contact("c" + suffix, 6 * scale, "s3", "g1", 2, 3),
        Contact("d" + suffix, 2 * scale, "s4", "g2", 0, 1),
    )
    return (temporal_graph("gap0" + suffix, contacts, station_gap=0),
            temporal_graph("gap1" + suffix, contacts, station_gap=1))


def aligned_intervention(left: Graph, right: Graph, fixed=(), excluded=()) -> dict:
    if left.contacts != right.contacts:
        raise ValueError("Interventions must preserve contacts, weights, ids and time windows")
    if left.constraints.get("model") != right.constraints.get("model"):
        raise ValueError("Interventions must preserve the constraint model")
    changes = {k: [left.constraints.get(k), right.constraints.get(k)]
               for k in left.constraints.keys() | right.constraints.keys()
               if left.constraints.get(k) != right.constraints.get(k)}
    if len(changes) != 1:
        raise ValueError("Exactly one constraint parameter must change")
    if not left.feasible(fixed) or not right.feasible(fixed):
        raise ValueError("Boundary commitments must remain feasible on both sides")
    left.available(fixed, excluded)
    right.available(fixed, excluded)
    return {"parameter_changes": changes,
            "removed_edges": sorted(left.edges - right.edges),
            "added_edges": sorted(right.edges - left.edges)}
