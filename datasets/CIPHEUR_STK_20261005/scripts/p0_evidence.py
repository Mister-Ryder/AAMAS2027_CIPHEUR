"""Registered P0 evidence and real repair-interface sensitivity diagnostics.

Labels are conditional optima of explicit restricted, outside-fixed patches,
never labels obtained by solving the complete 72-hour graph. No model is called.
The query manifest is saved before any conditional objective is computed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time

import numpy as np

_locations = argparse.ArgumentParser(add_help=False)
_locations.add_argument("--data-root", type=Path)
_locations.add_argument("--cipheur-root", type=Path)
_locations.add_argument("--output-root", type=Path)
_locations_args, _ = _locations.parse_known_args()
ROOT = (_locations_args.data_root or Path(__file__).resolve().parents[1]).resolve()
PROJECT = (_locations_args.cipheur_root or ROOT.parents[2] / "第二篇").resolve()
OUTPUT = (_locations_args.output_root or ROOT / "analysis" / "p0").resolve()
sys.path.insert(0, str(PROJECT))
from cipheur.model import Graph, Contact
from cipheur.programs import FEATURES, features
from cipheur.graph_features import FeatureRuleProgram
from cipheur.compiled import CompiledEvaluator
from cipheur.repair_v06 import RepairConfig, repair_schedule, repair_patch, _Meter, _solve, _priorities

SCALE = 1_000_000
SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
MAX_QUERIES = 50
PATCH_CAP = 64
MAX_DESTROY = 4
NODES = 2000
EPSILON_TICKS = 1
QUERY_SECONDS = 1.0


def digest(path):
    h = sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def hash_indices(indices):
    return sha256(np.asarray(sorted(indices), dtype="<u8").tobytes()).hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def build_graph(z, source, gap):
    ids = [str(x) for x in z["contact_id"]]
    contacts = tuple(Contact(ids[i], Fraction(int(z["weight_ticks"][i]), SCALE),
        str(z["satellite_id"][i]), str(z["antenna_id"][i]),
        Fraction(int(z["start_ticks"][i]), SCALE), Fraction(int(z["end_ticks"][i]), SCALE))
        for i in range(len(ids)))
    edges = frozenset((ids[int(a)], ids[int(b)]) for a, b in zip(z["edge_u"], z["edge_v"]))
    return Graph(source + f"-g{gap:04d}", contacts, edges,
                 {"station_gap": gap, "satellite_gap": 150,
                  "model": "full_contact_single_capacity_gap_v1"}), ids


def register():
    out = OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    frozen = PROJECT / "examples" / "frozen_joint_bank_v06.json"
    bank = json.loads(frozen.read_text(encoding="utf-8"))
    row = bank["programs"][0]
    registration = {
        "stage": "P0", "sources": list(SOURCES), "split": "TRAIN-development-only",
        "query_count_interpretation": "50 per geometry x replicate opportunity library; four libraries, 200 planned queries",
        "configuration_pair_seconds": [340, 1200], "satellite_gap_seconds": 150,
        "complete_contacts": True, "weight_contract": "(end_ticks-start_ticks)/1000000 seconds",
        "numeric_instance": "frozen original exported microsecond endpoints; no extra rounding",
        "epsilon_ticks": EPSILON_TICKS, "epsilon_seconds_exact": "1/1000000",
        "certificate_wall_seconds_per_query_four_spaces_combined": QUERY_SECONDS,
        "certificate_call_allocation": "remaining wall budget divided by uncomputed forced spaces; maximum 50000 B&B nodes per call",
        "query_rule": {
            "external_incumbent": "actual repair_v06 common dynamic exact weight/degree initializer at g1200, max_patches=0, unlimited initializer time",
            "targets": "non-incumbents sorted by actual original-residual weight/max(1,degree), contact-ID tie break",
            "destroy": "target incumbent blockers; actual one-step shared expansion through next Degree-ranked candidate, max_destroy=4",
            "patch": "same actual free-region calculation; retain destroy and target then global Degree-ranked extras, max64",
            "pair": "target a and highest local Degree-ranked b in destroyed incumbent also adjacent at g340; both feasible at same F and competing both sides",
            "fixed": "g1200 common external incumbent minus destroy; same fixed contact IDs in both configurations",
            "excluded": "V minus (F union restricted patch P); explicitly encoded as complement of recorded F/P over hashed source universe",
            "deduplication": "destroy-set deduplication; retain first50 eligible queries before computing any label",
            "failed_candidates": "save every screened reason count and representative IDs; no unavailable or unknown query is replaced after labels",
        },
        "scope": "restricted_induced_patch_with_external_incumbent_fixed; not72h full-graph conditional optimality",
        "g3": {"kernel": "unchanged actual cipheur.repair_v06._solve/_Meter/_priorities from repair_patch/repair_schedule",
               "patch_cap": PATCH_CAP, "node_budget_per_head": NODES,
               "heads": ["Degree", "existing_frozen_first_preregistered_v06_bank_entry", "certified_pair_reference_probe"],
               "frozen_bank_sha256": digest(frozen), "frozen_id": row["id"],
               "frozen_program": row["program"],
               "reference_rule": "only when a side has strict certificate: swap Degree scores of pair if wrongly ordered; otherwise unchanged",
               "reference_status": "offline development probe, not deployable method or algorithm result",
               "ordering_semantics": "forced inclusion optimality does not certify better B&B pivot ordering",
               "feature_cost": "same lazy head factory as actual repair_schedule: no head computation when root closes; feature/repair work and full local-search time recorded; same2000 search-node allowance",
               "time_budget": "none for P0 execution probe; node-limited, costs fully recorded; not equal wall-time performance comparison"},
        "quotient": "all certified strict side demands joined by complete9-field exact equality across all source/query boundaries; detect any self-loop and directed cycle",
        "quotient_numeric_namespace":"fraction_seconds_binary_fsum_base9_v1: root weight/duration are exact Fraction seconds; aggregate weight sums follow actual CompiledEvaluator binary float terms and once-rounded sum; no tolerance joins",
        "source_hashes": {p.name: digest(p) for p in [Path(__file__), PROJECT / "cipheur" / "repair_v06.py",
                PROJECT / "cipheur" / "compiled.py", PROJECT / "cipheur" / "programs.py"]},
        "registered_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_labels_read": False, "model_calls": 0,
    }
    path = out / "registration.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        # Never replace a previously registered rule with a changed one.
        for field in ("query_rule", "epsilon_ticks", "g3", "source_hashes"):
            if old[field] != registration[field]:
                raise ValueError("Registration differs: " + field)
        return old
    dump(path, registration)
    return registration


def prepare_queries(source, left, right, ids, z, output):
    index = {v: i for i, v in enumerate(ids)}
    t0 = time.perf_counter()
    init = repair_schedule(right, priority="degree", seconds=None,
                           config=RepairConfig(max_patches=0))
    incumbent = set(init["selected"])
    init_record = {k: init[k] for k in ("value_exact", "feasible", "cpu_seconds", "wall_seconds", "meter", "config")}
    init_record.update(selected_indices=sorted(index[v] for v in incumbent),
                       graph=right.name, purpose="feasible external boundary only, no conditional labels")
    dump(output / "external_incumbent.json", init_record)
    full = set(ids)
    scores = {v: right.nodes[v].weight / max(1, len(right.adj[v])) for v in ids}
    targets = sorted(full - incumbent, key=lambda v: (-scores[v], v))
    blockers = {v: right.adj[v] & incumbent for v in targets}
    seen, queries, reasons, unavailable = set(), [], Counter(), []
    for target in targets:
        base = blockers[target]
        if not base or len(base) > MAX_DESTROY:
            reason = "no_blockers" if not base else "destroy_above_fixed_cap"
            reasons[reason] += 1
            if len(unavailable) < 100:
                unavailable.append({"target": target, "reason": reason, "destroy_size": len(base)})
            continue
        proposals = [set(base)]
        for v in targets:
            extra = blockers[v] - base
            if extra and blockers[v] & base and len(base | extra) <= MAX_DESTROY:
                proposals.append(base | extra)
                break
        for destroy in proposals:
            key = tuple(sorted(destroy))
            if key in seen:
                reasons["duplicate_destroy"] += 1
                continue
            seen.add(key)
            fixed = incumbent - destroy
            blocked = set(fixed)
            for v in fixed:
                blocked.update(right.adj[v])
            region = full - blocked
            retained = destroy | {target}
            extras = sorted(region - retained, key=lambda v: (-scores[v], v))
            patch = retained | set(extras[:PATCH_CAP-len(retained)])
            eligible = destroy & left.adj[target] & right.adj[target]
            if not eligible:
                reasons["no_common_adjacent_destroyed_challenger"] += 1
                if len(unavailable) < 100:
                    unavailable.append({"target": target, "destroy": list(key),
                                        "reason": "no_common_adjacent_destroyed_challenger"})
                continue
            # Fixed, label-free selection within the explicitly declared patch.
            b = min(eligible, key=lambda v: (-right.nodes[v].weight / max(1, len(right.adj[v] & patch)), v))
            if any(left.adj[v] & fixed or right.adj[v] & fixed for v in patch):
                raise AssertionError("Same patch is not available on both sides")
            fixed_indices = sorted(index[v] for v in fixed)
            patch_indices = sorted(index[v] for v in patch)
            excluded_indices = sorted(set(range(len(ids))) - set(fixed_indices) - set(patch_indices))
            queries.append({"id": f"{source}:q{len(queries):03d}", "source": source,
                "slot": len(queries), "a": index[target], "b": index[b],
                "a_contact_id": target, "b_contact_id": b,
                "destroy_indices": sorted(index[v] for v in destroy), "fixed_indices": fixed_indices,
                "patch_indices": patch_indices, "full_free_region_size": len(region),
                "restricted": len(patch) != len(region),
                "excluded_encoding": "universe_indices minus fixed_indices minus patch_indices",
                "excluded_count": len(excluded_indices), "excluded_indices_sha256": hash_indices(excluded_indices),
                "fixed_indices_sha256": hash_indices(fixed_indices), "patch_indices_sha256": hash_indices(patch_indices),
                "same_fixed_excluded": True, "both_actions_feasible_competing_both_configurations": True})
            if len(queries) >= MAX_QUERIES:
                break
        if len(queries) >= MAX_QUERIES:
            break
    for slot in range(len(queries), MAX_QUERIES):
        queries.append({"id": f"{source}:q{slot:03d}", "source": source, "slot": slot,
                        "status": "unavailable", "reason": "eligible_registered_query_inventory_exhausted"})
    record = {"source": source, "graph_npz_sha256": {
        f"g{gap:04d}": digest(ROOT / "graphs" / source / f"g{gap:04d}.npz") for gap in (340, 1200)},
        "contact_id_sha256": sha256(json.dumps(ids).encode()).hexdigest(),
        "query_count": len(queries), "queries": queries,
        "screen_counts": dict(reasons), "unavailable_examples": unavailable,
        "prepared_before_labels": True, "preparation_wall_seconds": time.perf_counter()-t0,
        "external_incumbent_file": "external_incumbent.json",
        "head_rule_and_limits_file": "../registration.json"}
    dump(output / "query_manifest.json", record)
    return record


def patch_arrays(z, query):
    nodes = query["patch_indices"]
    loc = {v: j for j, v in enumerate(nodes)}
    masks, weights = [], [int(z["weight_ticks"][v]) for v in nodes]
    for v in nodes:
        neighbors = z["indices"][int(z["indptr"][v]):int(z["indptr"][v+1])]
        masks.append(sum(1 << loc[int(u)] for u in neighbors if int(u) in loc))
    return nodes, masks, weights, loc


def forced_bound(nodes, masks, weights, action_local, seconds):
    """Valid integer B&B bounds, preserving root upper if time is exhausted."""
    start = time.perf_counter()
    deadline = start + max(0, seconds)
    full = (1 << len(nodes)) - 1
    active = full & ~((1 << action_local) | masks[action_local])
    forced = weights[action_local]
    def members(mask):
        while mask:
            bit = mask & -mask
            yield bit.bit_length()-1
            mask ^= bit
    cache = {}
    def envelope(mask, keep=False):
        if mask in cache and not keep:
            return cache[mask], []
        order = sorted(members(mask), key=lambda j: (-(masks[j] & mask).bit_count(), -weights[j], nodes[j]))
        rest, total, cover = mask, 0, []
        for i in order:
            if not rest & (1 << i):
                continue
            clique = [i]
            rest &= ~(1 << i)
            common = masks[i]
            for j in order:
                if rest & (1 << j) and common & (1 << j):
                    clique.append(j)
                    rest &= ~(1 << j)
                    common &= masks[j]
            total += max(weights[j] for j in clique)
            if keep:
                cover.append([nodes[j] for j in clique])
        cache[mask] = total
        return total, cover
    order = sorted(members(active), key=lambda i: (-Fraction(weights[i], max(1,(masks[i]&active).bit_count())), nodes[i]))
    chosen, mask, best = 1 << action_local, active, forced
    for i in order:
        if mask & (1 << i):
            chosen |= 1 << i
            best += weights[i]
            mask &= ~((1 << i) | masks[i])
    root_extra, cover = envelope(active, True)
    root_upper = forced + root_extra
    frontier = [(active, 1 << action_local, forced)]
    expanded, best_mask, cuts = 0, chosen, 0
    while frontier and expanded < 50000 and time.perf_counter() < deadline:
        mask, selected, value = frontier.pop()
        expanded += 1
        if value > best:
            best, best_mask = value, selected
        if not mask:
            continue
        if value + envelope(mask)[0] <= best:
            cuts += 1
            continue
        i = min(members(mask), key=lambda j: (-(masks[j]&mask).bit_count(), -weights[j], nodes[j]))
        rest = mask & ~(1 << i)
        frontier.append((rest, selected, value))
        frontier.append((rest & ~masks[i], selected | (1 << i), value+weights[i]))
    # The remaining stack is a partition of the unexplored search space.
    upper = max([best] + [value + envelope(mask)[0] for mask, _, value in frontier])
    selected = [nodes[i] for i in members(best_mask)]
    if sum(weights[i] for i in members(best_mask)) != best or any(
            masks[i] & best_mask for i in members(best_mask)):
        raise AssertionError("Conditional lower witness invalid")
    if best > upper or upper > root_upper:
        raise AssertionError("Invalid conditional upper bound")
    return {"lower_ticks": best, "upper_ticks": upper, "exact": best == upper,
            "selected_indices": selected, "expanded_nodes": expanded, "bound_cuts": cuts,
            "root_upper_ticks": root_upper,
            "root_clique_partition_indices": cover,
            "frontier": [{"remaining_indices": [nodes[i] for i in members(mask)],
                "selected_indices": [nodes[i] for i in members(sel)], "value_ticks": val,
                "upper_ticks": val+envelope(mask)[0]} for mask, sel, val in frontier],
            "termination": "exact" if best==upper else "node_budget" if expanded>=50000 else "time_budget",
            "allocated_wall_seconds": seconds, "wall_seconds": time.perf_counter()-start}


def phi(graph, node, patch):
    # Match the actual compiled typed runtime's full base9 numeric semantics.
    # Its aggregate accumulator uses exactly represented float(weight) terms,
    # then rounds once, while root fields retain the Graph's numeric values.
    adjacent=graph.adj[node]&patch
    terms={v:Fraction(float(graph.nodes[v].weight)) for v in patch}
    neighbor_sum=sum((terms[v] for v in adjacent),Fraction())
    total=sum(terms.values(),Fraction())
    c=graph.nodes[node]
    values={"weight":c.weight,"duration":c.end-c.start,"degree":len(adjacent),
        "conflict_weight":float(neighbor_sum),
        "max_conflict_weight":max((graph.nodes[v].weight for v in adjacent),default=0),
        "compatible_weight":float(total-neighbor_sum-terms[node]),
        "station_gap":graph.constraints["station_gap"],"satellite_gap":graph.constraints["satellite_gap"],
        "remaining_count":len(patch)}
    # Fraction(float) preserves the actual aggregate's binary numeric value.
    return tuple(str(Fraction(values[name])) for name in FEATURES)


def sign_interval(a, b):
    lo = a["lower_ticks"]-b["upper_ticks"]
    hi = a["upper_ticks"]-b["lower_ticks"]
    status = "a" if lo > EPSILON_TICKS else "b" if hi < -EPSILON_TICKS else "tie" if lo == hi == 0 else "unknown"
    return {"lower_ticks": lo, "upper_ticks": hi, "preference": status,
            "epsilon_ticks": EPSILON_TICKS, "formula": "[La-Ub,Ua-Lb]"}


def certificate(z0, z1, query):
    start = time.perf_counter()
    bounds = {}
    for k, (z, action) in enumerate(((z0,query["a"]),(z0,query["b"]),(z1,query["a"]),(z1,query["b"]))):
        nodes, masks, weights, loc = patch_arrays(z, query)
        left = max(0, QUERY_SECONDS-(time.perf_counter()-start))
        bounds[("left_a","left_b","right_a","right_b")[k]] = forced_bound(
            nodes, masks, weights, loc[action], left/(4-k))
    signs = {side: sign_interval(bounds[side+"_a"], bounds[side+"_b"]) for side in ("left","right")}
    a, b = (signs[s]["preference"] for s in ("left","right"))
    relation = ("reversal" if a != b else "preservation") if a in ("a","b") and b in ("a","b") else (
        "tie" if a == b == "tie" else "tie_to_strict" if a == "tie" and b in ("a","b") else
        "strict_to_tie" if b == "tie" and a in ("a","b") else "unknown")
    return {"query_id": query["id"], "scope": "restricted outside-fixed patch, exact frozen microsecond instance",
            "common_fixed_reward_ticks":sum(int(z0["weight_ticks"][i]) for i in query["fixed_indices"]),
            "bound_value_scope":"variable patch contribution only; add common_fixed_reward_ticks to every forced bound for conditional full schedule value; common constant cancels from delta",
            "bounds": bounds, "signs": signs, "relation": relation,
            "wall_seconds": time.perf_counter()-start,
            "budget_includes_patch_arrays": True,
            "budget_soft_overshoot_note": "final bound/witness validation is recorded in wall time"}


def run_g3(graph, ids, query, cert, side, program):
    patch = {ids[i] for i in query["patch_indices"]}
    fixed = {ids[i] for i in query["fixed_indices"]}
    destroy = {ids[i] for i in query["destroy_indices"]}
    initial = fixed | destroy
    a, b = ids[query["a"]], ids[query["b"]]
    preferred = cert["signs"][side]["preference"]
    rows = []
    for head in ("degree","existing_frozen","certified_reference"):
        meter=_Meter(None,"cpu",None,NODES)
        weights={v:graph.nodes[v].weight for v in patch}
        meter.tick("exact_weight_conversion",len(patch))
        called,head_seconds,changed=False,0.,False
        def factory(region):
            nonlocal called,head_seconds,changed
            called=True
            start=time.perf_counter()
            scores=_priorities(graph,region,program,"program" if head=="existing_frozen" else "degree",None,meter)
            if head=="certified_reference" and preferred in ("a","b"):
                meter.tick("offline_reference_lookup")
                good,bad=(a,b) if preferred=="a" else (b,a)
                if scores[good]<=scores[bad]:
                    if scores[good]<scores[bad]:scores[good],scores[bad]=scores[bad],scores[good]
                    else:scores[good]+=Fraction(1,SCALE)
                    changed=True
            head_seconds=time.perf_counter()-start
            return scores
        result=_solve(graph,patch,destroy,weights,factory,meter,NODES,True)
        updated=fixed|set(result["local_selected"])
        meter.sealed=True
        meter.tick("final_validation",len(updated)+sum(len(graph.adj[v]) for v in updated))
        if not graph.feasible(updated) or not fixed<=updated or sum((graph.nodes[v].weight for v in updated),Fraction())<sum((graph.nodes[v].weight for v in initial),Fraction()):
            raise AssertionError("Actual solver returned invalid full-schedule patch")
        result.update(gain_exact=str(Fraction(result["lower_exact"])-sum((graph.nodes[v].weight for v in destroy),Fraction())),
            cpu_seconds=time.process_time()-meter.cpu_start,wall_seconds=time.perf_counter()-meter.wall_start,meter=dict(meter))
        row = {k:result[k] for k in ("lower_exact","upper_exact","restricted_exact","termination",
            "search_nodes","bound_cuts","priority_order","common_degree_order","greedy_passes",
            "pivot_count","degree_pivot_disagreements","root_pruned","gain_exact",
            "local_selected","cpu_seconds","wall_seconds","meter")}
        row.update(head=head, query_id=query["id"], side=side,
            head_called=called,head_preparation_wall_seconds=head_seconds,
            head_meter={"feature_work":meter.get("feature_work",0),"feature_primitives":meter.get("feature_primitives",{})},
            total_wall_seconds=result["wall_seconds"],
            total_operation_proxy=meter.get("feature_work",0)+meter.get("repair_work",0),
            preferred_probe_action=preferred, reference_degree_pair_changed=changed if head=="certified_reference" else None,
            committed=Fraction(result["gain_exact"])>0,
            selected_set_sha256=sha256(json.dumps(sorted(updated)).encode()).hexdigest(),
            full_schedule_value_exact=str(sum((graph.nodes[v].weight for v in updated),Fraction())),
            first_greedy_improvement=None)
        baseline = sum((graph.nodes[v].weight for v in destroy), Fraction())
        for i, p in enumerate(result["greedy_passes"]):
            if Fraction(p["value_exact"]) > baseline:
                row["first_greedy_improvement"] = {"pass_index":i,"pass_type":p["order"],
                    "value_exact":p["value_exact"],"complete":p["complete"]}
                break
        rows.append(row)
    return rows


def quotient(requirements):
    vertices, mapping, edges = {}, {}, defaultdict(list)
    for req in requirements:
        pair=[]
        for ph in (req["preferred_phi"],req["other_phi"]):
            key=tuple(ph)
            if key not in mapping:
                label="phi"+str(len(mapping))
                mapping[key]=label
                vertices[label]={"full9":list(key),"occurrences":[]}
            pair.append(mapping[key])
        u,v=pair
        for label, node in ((u,req["preferred_contact_id"]),(v,req["other_contact_id"])):
            vertices[label]["occurrences"].append({"query_id":req["query_id"],"source":req["source"],
                "side":req["side"],"contact_id":node,"boundary_hash":req["boundary_hash"]})
        edges[u].append((v,req))
    color, parent={},{}
    cycle=[]
    def visit(u):
        color[u]=1
        for v,req in edges[u]:
            if color.get(v,0)==0:
                parent[v]=(u,req)
                if visit(v): return True
            elif color.get(v)==1:
                trace=[{"from":u,"to":v,"requirement":req}]
                here=u
                while here!=v:
                    prev,p=parent[here]
                    trace.append({"from":prev,"to":here,"requirement":p})
                    here=prev
                cycle.extend(reversed(trace));return True
        color[u]=2
        return False
    for u in vertices:
        if color.get(u,0)==0 and visit(u):break
    return {"full_feature_names":list(FEATURES),"strict_requirements":len(requirements),
        "numeric_namespace":"fraction_seconds_binary_fsum_base9_v1",
        "vertices":vertices,"edges":[{"from":u,"to":v,"requirement":r} for u,lst in edges.items() for v,r in lst],
        "directed_cycle_observed":bool(cycle),"cycle_trace":cycle,
        "self_loop_count":sum(u==v for u,lst in edges.items() for v,_ in lst),
        "conclusion":"information_obstruction_certified" if cycle else "not_observed_on_preregistered_requirements"}


def process_source(source, registration, run_g3_flag=True, limit_execution=None):
    out=OUTPUT/source
    out.mkdir(parents=True,exist_ok=True)
    z0=load(ROOT/"graphs"/source/"g0340.npz")
    z1=load(ROOT/"graphs"/source/"g1200.npz")
    for name in ("contact_id","start_ticks","end_ticks","weight_ticks"):
        if not np.array_equal(z0[name],z1[name]):raise AssertionError("Contact identity mismatch: "+name)
    left,ids=build_graph(z0,source,340)
    right,ids1=build_graph(z1,source,1200)
    if ids!=ids1 or not left.edges<=right.edges:raise AssertionError("Nonmonotone intervention")
    manifest_path=out/"query_manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else prepare_queries(source,left,right,ids,z0,out)
    program=FeatureRuleProgram.from_dict(registration["g3"]["frozen_program"])
    certificates, requirements, traces=[],[],[]
    for query in manifest["queries"][:limit_execution]:
        if query.get("status")=="unavailable":
            certificates.append({"query_id":query["id"],"relation":"unavailable","reason":query["reason"]});continue
        cp=out/"certificates"/(query["id"].split(":")[-1]+".json")
        cert=json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else certificate(z0,z1,query)
        dump(cp,cert)
        certificates.append(cert)
        patch={ids[i] for i in query["patch_indices"]}
        for side,graph in (("left",left),("right",right)):
            pref=cert["signs"][side]["preference"]
            if pref in ("a","b"):
                good,bad=(query["a"],query["b"]) if pref=="a" else (query["b"],query["a"])
                requirements.append({"query_id":query["id"],"source":source,"side":side,
                    "boundary_hash":sha256((query["fixed_indices_sha256"]+query["excluded_indices_sha256"]+query["patch_indices_sha256"]).encode()).hexdigest(),
                    "certificate_file":str(cp.relative_to(OUTPUT)),"certificate_sha256":digest(cp),
                    "delta_interval":cert["signs"][side],"preferred_contact_id":ids[good],"other_contact_id":ids[bad],
                    "preferred_phi":list(phi(graph,ids[good],patch)),"other_phi":list(phi(graph,ids[bad],patch))})
            if run_g3_flag:
                tp=out/"traces"/(query["id"].split(":")[-1]+"_"+side+".json")
                rows=json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else run_g3(graph,ids,query,cert,side,program)
                dump(tp,rows);traces.extend(rows)
    dump(out/"strict_requirements.json",requirements)
    counts=Counter(c["relation"] for c in certificates)
    summary={"source":source,"queries":len(certificates),"relations":dict(counts),
        "strict_side_requirements":len(requirements),"query_manifest_sha256":digest(manifest_path),
        "certificate_total_wall_seconds":sum(c.get("wall_seconds",0) for c in certificates),
        "g3_rows":len(traces),"g3_restricted_exact":sum(r["restricted_exact"] for r in traces),
        "g3_distinct_value_states":sum(len({r["lower_exact"] for r in traces if r["query_id"]==q["id"] and r["side"]==s})>1
            for q in manifest["queries"] for s in ("left","right")),
        "scope":"TRAIN restricted actual patches only", "models_called":0}
    dump(out/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return requirements


def aggregate():
    out=OUTPUT
    req, summaries, all_rows=[],[],[]
    for source in SOURCES:
        p=out/source/"summary.json"
        if not p.exists():continue
        summaries.append(json.loads(p.read_text(encoding="utf-8")))
        req.extend(json.loads((out/source/"strict_requirements.json").read_text(encoding="utf-8")))
        for t in sorted((out/source/"traces").glob("*.json")):
            all_rows.extend(json.loads(t.read_text(encoding="utf-8")))
    q=quotient(req)
    dump(out/"complete_demanded_quotient.json",q)
    grouped=defaultdict(list)
    for row in all_rows:grouped[(row["query_id"],row["side"])].append(row)
    g3={"states":len(grouped),"rows":len(all_rows),"all_restricted_exact":bool(all_rows) and all(r["restricted_exact"] for r in all_rows),
        "different_final_patch_value_states":0,"different_priority_order_states":0,"different_search_nodes_states":0,
        "different_local_selected_states":0,"per_head":{}}
    for rows in grouped.values():
        g3["different_final_patch_value_states"]+=len({r["lower_exact"] for r in rows})>1
        g3["different_priority_order_states"]+=len({tuple(r["priority_order"]) for r in rows})>1
        g3["different_search_nodes_states"]+=len({r["search_nodes"] for r in rows})>1
        g3["different_local_selected_states"]+=len({tuple(r["local_selected"]) for r in rows})>1
    for head in ("degree","existing_frozen","certified_reference"):
        rows=[r for r in all_rows if r["head"]==head]
        g3["per_head"][head]={"rows":len(rows),"search_nodes":sum(r["search_nodes"] for r in rows),
            "total_wall_seconds":sum(r["total_wall_seconds"] for r in rows),
            "operation_proxy":sum(r["total_operation_proxy"] for r in rows),
            "feature_work":sum(r["head_meter"].get("feature_work",0) for r in rows),
            "committed_improvement_states":sum(r["committed"] for r in rows)}
    replicates={r:any(s["source"].endswith(r) and s["relations"].get("reversal",0)>0 for s in summaries) for r in ("r000","r001")}
    acceptance={"completed_sources":len(summaries),"planned_sources":4,"source_summaries":summaries,
        "G1_reversal_by_replicate":replicates,"G1": "observed_in_both_development_replicates" if all(replicates.values()) else "not_established_in_both_development_replicates",
        "G2":q["conclusion"],"G2_strict_requirements":q["strict_requirements"],"G2_quotient_vertices":len(q["vertices"]),
        "G3":g3,"P1": "eligible_for_small_P1_pending_joint_review" if len(summaries)==4 and sum(s["queries"] for s in summaries)==200 and all(replicates.values()) and q["directed_cycle_observed"] and
            (g3["different_final_patch_value_states"]>0 or g3["different_search_nodes_states"]>0) else "STOP_no_batch_LLM_or_P1",
        "limitations":["Patches retain full contacts but exclude domain outside recorded restricted P; no72h global optimum claim",
            "Forced inclusion certificate does not certify efficient B&B pivot order",
            "Equal node allowances are not equal total computation: all head and repair costs separately measured",
            "No cycle observed on this finite demand set does not prove absence of representation obstructions",
            "Source groups aggregate geometry and replicate; patch counts are not independent replication"]}
    dump(out/"acceptance.json",acceptance)
    print(json.dumps({k:v for k,v in acceptance.items() if k not in ("source_summaries","G3")},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(parents=[_locations])
    parser.add_argument("--source",choices=SOURCES)
    parser.add_argument("--register-only",action="store_true")
    parser.add_argument("--aggregate-only",action="store_true")
    parser.add_argument("--no-g3",action="store_true")
    parser.add_argument("--limit-execution",type=int,help="Pilot only: execute a prefix of the already registered50-query manifest; never claims completed P0")
    args=parser.parse_args()
    registration=register()
    if args.limit_execution is not None and (args.limit_execution<1 or args.limit_execution>50):
        raise ValueError("limit-execution must be1..50")
    dump(OUTPUT / ("execution_"+str(os.getpid())+".json"), {
        "hostname":socket.gethostname(),"platform":platform.platform(),"python":sys.version,
        "python_executable":sys.executable,"pid":os.getpid(),
        "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "argv":sys.argv,"data_root":str(ROOT),"cipheur_root":str(PROJECT),
        "script_sha256":digest(Path(__file__)),"registration_sha256":digest(OUTPUT/"registration.json")})
    if args.register_only:return
    if not args.aggregate_only:
        for source in ((args.source,) if args.source else SOURCES):
            process_source(source,registration,not args.no_g3,args.limit_execution)
    aggregate()


if __name__=="__main__":
    main()
