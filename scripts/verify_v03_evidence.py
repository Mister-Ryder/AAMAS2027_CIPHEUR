"""Independent, read-only audit of v03 archives; never extract or rerun studies.

Only the fixed experiments/runs/v03 directory is read. JSONL is consumed line
by line through streaming tar readers. Saved graph witnesses are checked by
standalone graph arithmetic, not the current scheduling/compiler code. Small
graphs (<=12 contacts) additionally receive exhaustive conditional MWIS checks.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, OrderedDict
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import itertools
import json
import math
import statistics
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments/runs/v03"
ISSUES = {}
CHECKS = Counter()
BRUTE_CACHE = {}
GRAPH_CACHE = OrderedDict()


def issue(code, where, detail, severity="error"):
    key = (severity, code)
    item = ISSUES.setdefault(key, {"severity": severity, "code": code,
                                 "count": 0, "examples": []})
    item["count"] += 1
    if len(item["examples"]) < 4:
        item["examples"].append({"where": where, "detail": detail})


def require(ok, code, where, detail):
    CHECKS[code] += 1
    if not ok:
        issue(code, where, detail)
    return bool(ok)


def near(a, b):
    return isinstance(a, (int, float)) and math.isfinite(a) and math.isclose(
        a, float(b), rel_tol=1e-10, abs_tol=1e-8)


def file_digest(path):
    h=sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


class GraphView:
    def __init__(self, raw):
        self.raw = raw
        self.contacts = {c["id"]: c for c in raw["contacts"]}
        self.weights = {k: Fraction(c["weight"]) for k, c in self.contacts.items()}
        self.edges = {tuple(sorted(e)) for e in raw["edges"]}
        self.adj = {k: set() for k in self.contacts}
        for a, b in self.edges:
            self.adj[a].add(b)
            self.adj[b].add(a)
        payload = {"contacts": raw["contacts"], "edges": [list(e) for e in sorted(self.edges)],
                   "constraints": raw.get("constraints", {})}
        self.digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def feasible(self, selected):
        chosen = set(selected)
        return (len(chosen) == len(selected) and chosen <= self.contacts.keys()
                and all(not self.adj[v].intersection(chosen) for v in chosen))

    def value(self, selected):
        return sum((self.weights[v] for v in selected), Fraction(0))

    def available(self, fixed=(), excluded=()):
        blocked = set(fixed) | set(excluded)
        for v in fixed:
            blocked.update(self.adj[v])
        return set(self.contacts) - blocked

    def optimum(self, fixed=(), excluded=()):
        if len(self.contacts) > 12:
            return None
        key = (self.digest, tuple(sorted(fixed)), tuple(sorted(excluded)))
        if key not in BRUTE_CACHE:
            active = sorted(self.available(fixed, excluded))
            best = self.value(fixed)
            for mask in range(1 << len(active)):
                selected = list(fixed) + [v for i, v in enumerate(active) if mask >> i & 1]
                if self.feasible(selected):
                    best = max(best, self.value(selected))
            BRUTE_CACHE[key] = best
        return BRUTE_CACHE[key]


def view(raw):
    key=id(raw)
    if key not in GRAPH_CACHE or GRAPH_CACHE[key].raw is not raw:
        GRAPH_CACHE[key]=GraphView(raw)
    GRAPH_CACHE.move_to_end(key)
    while len(GRAPH_CACHE)>48:
        GRAPH_CACHE.popitem(last=False)
    return GRAPH_CACHE[key]


def check_selection(g, selected, value, fixed, excluded, where):
    if not require(isinstance(selected, list), "selection_list", where, str(type(selected))):
        return
    valid = require(g.feasible(selected), "selection_feasible", where,
                    "duplicate, unknown contact, or conflicting edge")
    require(set(fixed) <= set(selected) and not set(excluded).intersection(selected),
            "selection_boundary", where, "fixed/excluded boundary not respected")
    if valid:
        require(near(value, g.value(selected)), "selection_objective", where,
                f"saved={value}; exact={g.value(selected)}")


def bounds(g, raw, action, fixed, excluded, where, region=None):
    if not raw:
        return
    try:
        lo, hi = Fraction(raw["lower_exact"]), Fraction(raw["upper_exact"])
    except (KeyError, ValueError, ZeroDivisionError) as e:
        issue("bound_exact_fields", where, str(e)); return
    require(lo <= hi, "bound_order", where, f"{lo}>{hi}")
    require(Fraction(raw["lower"]) <= lo and Fraction(raw["upper"]) >= hi,
            "bound_outward_rounding", where, "float endpoint rounded inward")
    require(raw.get("exact") == (lo == hi), "bound_exact_flag", where,
            "exact flag differs from rational endpoint equality")
    selected = raw.get("selected")
    check_selection(g, selected, raw["lower"], list(fixed)+[action], excluded, where)
    if isinstance(selected, list) and set(selected) <= g.contacts.keys():
        require(g.value(selected) == lo, "bound_witness_exact_value", where,
                f"witness={g.value(selected)}; lower={lo}")
    cover = raw.get("clique_cover", [])
    seen = set()
    for clique in cover:
        require(bool(clique) and len(clique) == len(set(clique))
                and not seen.intersection(clique) and set(clique) <= g.contacts.keys(),
                "clique_partition_valid", where, "empty, duplicate, overlapping, or unknown clique")
        if set(clique) <= g.contacts.keys():
            require(all(b in g.adj[a] for i, a in enumerate(clique) for b in clique[i+1:]),
                    "clique_edges", where, "saved clique contains a non-edge")
        seen.update(clique)
    if region is not None and raw.get("upper_method") == "weighted_clique_cover":
        outside = g.available(list(fixed)+[action], excluded) - set(region)
        require(seen == outside, "local_cover_outside_coverage", where,
                f"cover={len(seen)}; outside={len(outside)}")
    optimum = g.optimum(list(fixed)+[action], excluded)
    if optimum is not None:
        require(lo <= optimum <= hi, "small_graph_interval_contains_optimum", where,
                f"[{lo},{hi}] excludes brute-force optimum {optimum}")
        if raw.get("exact"):
            require(lo == optimum, "small_graph_exact_value", where, f"{lo}!={optimum}")


def check_bound_map(pair, mapping, fixed, excluded, where, region=None):
    for label, bound in mapping.items():
        if label not in ("left_a", "left_b", "right_a", "right_b"):
            continue
        side, which = label.split("_")
        bounds(view(pair[side]), bound, pair[which], fixed, excluded,
               where+"/"+label, region)


def check_history(pair, details, fixed, excluded, where):
    check_bound_map(pair, details.get("bounds", {}), fixed, excluded, where+"/accumulated")
    for i, h in enumerate(details.get("history", [])):
        check_bound_map(pair, h.get("raw_bounds", {}), fixed, excluded,
                        where+f"/history{i}/raw", h.get("region"))
        check_bound_map(pair, h.get("bounds", {}), fixed, excluded, where+f"/history{i}/intersection")


def certificate(spec, where):
    pair = spec
    fixed, excluded = spec.get("fixed", []), spec.get("excluded", [])
    views = {side: view(spec[side]) for side in ("left", "right")}
    require(spec["left"]["contacts"] == spec["right"]["contacts"],
            "certificate_identical_contacts", where, "contacts differ across intervention")
    changed = [k for k in set(spec["left"].get("constraints", {})) |
               set(spec["right"].get("constraints", {}))
               if spec["left"].get("constraints", {}).get(k) != spec["right"].get("constraints", {}).get(k)]
    require(len(changed) == 1, "certificate_single_intervention", where, str(changed))
    for side, g in views.items():
        active = g.available(fixed, excluded)
        require(g.feasible(fixed) and not set(fixed).intersection(excluded)
                and spec["a"] in active and spec["b"] in active
                and spec["b"] in g.adj[spec["a"]],
                "certificate_boundary_and_competition", where+"/"+side, "invalid boundary/actions")
        preferred = spec[side+"_preferred"]
        other = spec["b"] if preferred == spec["a"] else spec["a"]
        require(preferred in (spec["a"], spec["b"]), "certificate_preferred_action", where, preferred)
        pb = spec["bounds"][side+("_a" if preferred == spec["a"] else "_b")]
        ob = spec["bounds"][side+("_a" if other == spec["a"] else "_b")]
        require(Fraction(pb["lower_exact"]) > Fraction(ob["upper_exact"]) + Fraction(spec.get("epsilon", 1e-8)),
                "certificate_strict_separation", where+"/"+side, "preference not certified by rational endpoints")
    require(spec.get("relation") == ("preservation" if spec["left_preferred"] == spec["right_preferred"]
                                     else "reversal"), "certificate_relation", where, str(spec.get("relation")))
    check_history(pair, spec, fixed, excluded, where)


def stream(path):
    """Yield safe archive member handles; no extraction, links, or execution."""
    with tarfile.open(path, "r|gz") as tf:
        for member in tf:
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or member.issym() or member.islnk():
                issue("unsafe_archive_member", path.name, member.name)
                continue
            if member.isfile():
                yield p.name, tf.extractfile(member), member.name


def json_members(path, wanted):
    values, hashes = {}, {}
    for name, f, _ in stream(path):
        if name in wanted:
            raw = f.read()
            values[name] = json.loads(raw)
            hashes[name] = sha256(raw).hexdigest()
    return values, hashes


def snapshots():
    result = {}
    for path in sorted((ROOT/"experiments/source_snapshots/v03").glob("*.zip")):
        with zipfile.ZipFile(path) as z:
            result[path.name] = {PurePosixPath(n).name: sha256(z.read(n)).hexdigest()
                                 for n in z.namelist() if n.endswith(".py")}
    return result


SNAPSHOTS = {}


def execution_audit(meta, where, frozen_hash):
    execution = meta.get("execution.json", {})
    require(execution.get("selection_permitted", False) is False,
            "execution_no_test_selection", where, "selection permitted")
    require(execution.get("test_accessed", False) is False,
            "development_no_test_access", where, "development accessed test")
    if "frozen_sha256" in execution:
        require(execution["frozen_sha256"] == frozen_hash, "execution_frozen_hash", where,
                execution["frozen_sha256"])
    amendment = meta.get("execution_amendment.json", {})
    require(amendment.get("quality_outcomes_inspected_for_selection", False) is False,
            "amendment_no_test_selection", where, "quality used for selection")
    manifest = execution.get("source_sha256", {})
    scores = [(sum(snapshot.get(k) == v for k, v in manifest.items()), name)
              for name, snapshot in SNAPSHOTS.items()]
    if manifest and scores:
        matched, name = max(scores)
        missing = sorted(k for k, v in manifest.items() if SNAPSHOTS[name].get(k) != v)
        if missing:
            issue("source_snapshot_not_complete_match", where,
                  f"best={name}; matched={matched}/{len(manifest)}; unmatched={missing}", "warning")
        return {"best_snapshot": name, "matching_source_files": matched,
                "manifest_files": len(manifest), "unmatched_in_best_snapshot": missing,
                "current_tree_is_not_reproduction_reference": True}
    return {"manifest_files": len(manifest)}


def data_audit(data, where):
    pairs, contexts, seeds = {}, {}, defaultdict(set)
    original_ids = set()
    families = Counter()
    for split, records in data.items():
        for pair in records:
            pid = pair["id"]
            require(pid not in pairs, "data_unique_pair_id", where, pid)
            pairs[pid] = pair
            families[pair["family"]] += 1
            seed = pair.get("source", {}).get("seed")
            if seed is not None:
                seeds[split].add(seed)
            require(pair["left"]["contacts"] == pair["right"]["contacts"],
                    "data_aligned_contacts", where+"/"+pid, "contacts differ")
            for side in ("left", "right"):
                contexts[(pid, side)] = pair[side]
            if pair["family"] == "c3":
                ids = pair["left"]["provenance"]["original_ids"]
                require(len(ids) == len(set(ids)) and not original_ids.intersection(ids),
                        "data_disjoint_c3_ids", where+"/"+pid, "reused original IDs")
                original_ids.update(ids)
    for a, b in itertools.combinations(seeds, 2):
        require(not seeds[a].intersection(seeds[b]), "data_split_seed_disjointness", where, f"{a}/{b}")
    return pairs, contexts, {"pairs": len(pairs), "contexts": len(contexts),
                            "families_pairs": dict(families), "c3_unique_original_ids": len(original_ids)}


def schedules(path, frozen, frozen_hash, keep_data=False):
    wanted = {"config.json", "data_protocol.json", "execution.json", "complete.json",
              "progress.json", "execution_amendment.json", "programs.json", "data.json"}
    meta, member_hashes = json_members(path, wanted)
    data = meta.pop("data.json")
    pairs, contexts, allocation = data_audit(data, path.name)
    source = execution_audit(meta, path.name, frozen_hash)
    if "programs.json" in meta:
        for name, raw in frozen["programs"].items():
            require(meta["programs.json"].get(name) == raw, "immutable_program_bytes_semantics",
                    path.name+"/"+name, "saved program differs from pre-test freeze")
    seen, count, method_counts = set(), 0, {}
    family_counts, solver_status = Counter(), Counter()
    reference_map = {}
    c3_receipts, c3_solution_checks = 0, 0
    expected_methods=(set(meta["programs.json"])|{"multi_start_1to2_search","HiGHS_MILP"}) if "programs.json" in meta else None
    hasher = sha256()
    evidence_rows, saved_specs = 0, 0
    for name, f, _ in stream(path):
        if name == "results.jsonl":
            for line in f:
                hasher.update(line); row = json.loads(line); count += 1
                key = (row["id"], row["side"])
                where = path.name+"/"+row["id"]+"/"+row["side"]
                require(key not in seen, "results_unique_context", where, "duplicate id-side")
                seen.add(key); family_counts[row["family"]] += 1
                if not require(key in contexts, "result_in_allocation", where, "unknown context"):
                    continue
                pair, g = pairs[row["id"]], view(contexts[key])
                require(row["family"]==pair["family"] and row["split"]==pair["source"]["split"],
                        "result_family_split_matches_allocation",where,"family or split mismatch")
                require(row["graph_sha256"] == g.digest, "result_graph_hash", where,
                        f"saved={row['graph_sha256']}; reconstructed={g.digest}")
                require(row["n"] == len(g.contacts) and row["m"] == len(g.edges),
                        "result_graph_counts", where, "n/m mismatch")
                names = [r["method"] for r in row["methods"]]
                require(len(names) == len(set(names)), "result_unique_method", where, "duplicate method")
                if expected_methods is None:expected_methods=set(names)
                require(set(names)==expected_methods,"result_method_coverage",where,
                        "missing/extra declared method row")
                checks = row.get("source_verifier", {})
                if row["family"] == "c3":
                    if not checks:
                        issue("c3_source_receipt_absent",where,"older development/stress graph feasibility does not confirm original source verification","warning")
                    else:
                        require(checks.get("applicable") is True and checks.get("reconstructed_edges_identical") is True,
                                "c3_reconstruction_receipt", where, "missing source graph confirmation")
                    if checks.get("applicable") and checks.get("reconstructed_edges_identical"):
                        c3_receipts += 1
                for method in row["methods"]:
                    label = method["method"]; w = where+"/"+label
                    if label in meta.get("programs.json",{}):
                        require(method.get("program_name")==meta["programs.json"][label]["name"],
                                "executed_program_name_matches_freeze",w,"saved execution names another program")
                    stats = method_counts.setdefault(label, {"assigned": 0, "completed": 0,
                                    "failed": 0, "null_failure": 0, "quality_n": 0,
                                    "quality_sum": 0.0, "cpu_seconds": [], "failed_cpu_seconds": [], "statuses": Counter()})
                    stats["assigned"] += 1
                    for field in ("seconds","cpu_seconds"):
                        if method.get(field) is not None:
                            require(isinstance(method[field],(int,float)) and math.isfinite(method[field]) and method[field]>=0,
                                    "execution_time_nonnegative_finite",w+"/"+field,str(method[field]))
                    done = method.get("completed", method.get("value") is not None)
                    if not done:
                        stats["failed"] += 1
                        null = (method.get("value") is None and method.get("selected") is None
                                and method.get("feasible") is None)
                        stats["null_failure"] += int(null)
                        require(null, "timeout_has_no_schedule", w, "timeout retains value/schedule/feasibility")
                        stats["statuses"][method.get("status", "unspecified")] += 1
                        if method.get("cpu_seconds") is not None:
                            stats["failed_cpu_seconds"].append(method["cpu_seconds"])
                        continue
                    stats["completed"] += 1
                    check_selection(g, method.get("selected"), method.get("value"),
                                    pair.get("fixed", []), pair.get("excluded", []), w)
                    require(method.get("feasible") is True, "schedule_saved_feasible_flag", w, "feasible flag not true")
                    if method.get("cpu_seconds") is not None:
                        stats["cpu_seconds"].append(method["cpu_seconds"])
                    if row["family"] == "c3" and checks:
                        check = checks.get("checks", {}).get(label)
                        require(bool(check) and check.get("feasible") is True
                                and check.get("conflicts") == 0 and check.get("duplicates") == 0
                                and check.get("invalid") == 0,
                                "c3_completed_selection_receipt", w, "missing/nonzero source verification")
                        c3_solution_checks += int(bool(check) and check.get("feasible") is True)
                    upper = row["reference"].get("upper")
                    if isinstance(upper, (int, float)) and upper > 0:
                        stats["quality_n"] += 1
                        stats["quality_sum"] += method["value"]/upper
                        require(method["value"] <= upper+1e-7, "floating_reference_above_schedule", w,
                                f"{method['value']}>{upper}")
                ref = row["reference"]
                if "lower" in ref:
                    check_selection(g, ref["selected"], ref["lower"], pair.get("fixed", []),
                                    pair.get("excluded", []), where+"/reference")
                    require(ref.get("exact") is False and ref.get("scope") == "floating_milp_reference",
                            "floating_reference_scope", where, "solver wrongly marked exact")
                    require(ref["lower"] <= ref["upper"]+1e-7, "floating_reference_interval", where, "lower exceeds upper")
                    reference_map[key] = ref["upper"]
                    solver_status[str(ref.get("solver_status"))] += 1
        elif name == "test_evidence.jsonl":
            for line in f:
                row = json.loads(line); evidence_rows += 1
                for i, spec in enumerate(row.get("specifications", [])):
                    saved_specs += 1
                    certificate(spec, path.name+"/test_evidence/"+row["id"]+f"/{i}")
                pair = pairs[row["id"]]
                for i, attempt in enumerate(row.get("attempts", [])):
                    req = attempt.get("request", {})
                    check_history({**pair, "a": req.get("a", pair["a"]), "b": req.get("b", pair["b"])},
                                  attempt.get("details", {}), req.get("fixed", pair.get("fixed", [])),
                                  req.get("excluded", pair.get("excluded", [])),
                                  path.name+"/test_attempt/"+row["id"]+f"/{i}")
    complete = meta.get("complete.json", {})
    progress = meta.get("progress.json", {})
    checkpoint=progress.get("completed",count)
    require(0<=count-checkpoint<10,"progress_checkpoint_lag_within_writer_batch",path.name,
            f"progress={checkpoint}; rows={count}; writer batches 10")
    if complete:
        require(complete.get("completed", count) == count, "complete_actual_count", path.name, str(complete))
        require(count == len(contexts), "complete_full_allocation", path.name, f"{count}/{len(contexts)}")
        if "results_sha256" in complete:
            require(complete["results_sha256"] == hasher.hexdigest(), "complete_results_sha256", path.name,
                    "results digest differs")
        if "evidence_pairs" in complete:
            require(complete["evidence_pairs"] == evidence_rows, "complete_evidence_count", path.name,
                    f"{complete['evidence_pairs']}!={evidence_rows}")
    if count != len(contexts):
        issue("partial_harness_not_primary_complete", path.name,
              f"{count}/{len(contexts)}; missing={len(contexts)-count}; no completed marker={not bool(complete)}", "warning")
    if "002" in path.name and "holdout" in path.name:
        issue("obsolete_harness_failure_reason", path.name,
              "saved amendment attributes a signal-guard stall; final diagnosed cause is max over float/None baseline values", "warning")
    for stats in method_counts.values():
        require(stats["assigned"]==count,"method_recorded_context_coverage",path.name,
                f"method assigned={stats['assigned']}; result contexts={count}")
        cpu = stats.pop("cpu_seconds")
        failed_cpu=stats.pop("failed_cpu_seconds")
        stats["statuses"] = dict(stats["statuses"])
        stats["completed_quality_mean"] = stats["quality_sum"]/stats["quality_n"] if stats["quality_n"] else None
        # This explicit all-assigned denominator retains every timeout as zero.
        stats["recorded_context_zero_normalized_mean"] = stats["quality_sum"]/stats["assigned"] if stats["assigned"] else None
        stats["all_prespecified_context_zero_normalized_mean"] = stats["quality_sum"]/len(contexts) if count==len(contexts) else None
        stats["max_completed_cpu_seconds"] = max(cpu) if cpu else None
        stats["max_failed_cpu_seconds"] = max(failed_cpu) if failed_cpu else None
        stats["median_recorded_cpu_seconds"] = statistics.median(cpu+failed_cpu) if cpu or failed_cpu else None
        target=meta.get("config.json",{}).get("program_cpu_seconds")
        stats["completed_cpu_above_target"] = sum(v>target for v in cpu) if target else None
        del stats["quality_sum"]
    result = {"archive": path.name, "allocation": allocation, "actual_context_rows": count,
              "unique_contexts": len(seen), "families_context_rows": dict(family_counts),
              "quality_phase_complete": count == len(contexts),
              "progress_checkpoint_completed":checkpoint,"progress_checkpoint_lag":count-checkpoint,
              "complete_marker_present": bool(complete), "evidence_rows": evidence_rows,
              "saved_test_certificates": saved_specs, "solver_status_counts": dict(solver_status),
              "source_snapshot": source, "source_c3_graph_receipts": c3_receipts,
              "source_c3_completed_selection_receipts": c3_solution_checks,
              "member_sha256": member_hashes, "results_sha256": hasher.hexdigest(),
              "methods": method_counts}
    return result, (data, pairs, reference_map) if keep_data else None


def base_vector(g, node, fixed, excluded, extra=()):
    active = g.available(fixed, excluded); neigh = g.adj[node] & active
    c = g.contacts[node]; constraints = g.raw.get("constraints", {})
    values = {"weight": c["weight"], "duration": c["end"]-c["start"], "degree": len(neigh),
              "conflict_weight": float(g.value(neigh)),
              "max_conflict_weight": float(max((g.weights[v] for v in neigh), default=0)),
              "compatible_weight": float(g.value(active-neigh-{node})),
              "remaining_count": len(active),
              "station_gap": constraints.get("station_gap", constraints.get("ground_trans_time", 0)),
              "satellite_gap": constraints.get("satellite_gap", constraints.get("satellite_change_time", 0))}
    edges = [(a,b) for a,b in g.edges if a in neigh and b in neigh]
    if "neigh_edges" in extra: values["neigh_edges"] = len(edges)
    if "neigh_min" in extra: values["neigh_min"] = float(sum((min(g.weights[a],g.weights[b]) for a,b in edges),Fraction(0)))
    for name in ("neigh_cover", "neigh_greedy"):
        if name not in extra: continue
        remaining = set(neigh); total = Fraction(0)
        order = sorted(neigh,key=lambda v:(-g.weights[v],v))
        for v in order:
            if v not in remaining: continue
            if name == "neigh_greedy":
                total += g.weights[v];remaining.difference_update(g.adj[v]|{v})
            else:
                clique=[v];remaining.remove(v)
                for u in order:
                    if u in remaining and all(u in g.adj[q] for q in clique):
                        clique.append(u);remaining.remove(u)
                total += max(g.weights[q] for q in clique)
        values[name] = float(total)
    return tuple(sorted(values.items()))


def quotient(specs, extra=()):
    nodes, edges, loops = set(), set(), 0
    for spec in specs:
        for side in ("left", "right"):
            g = view(spec[side]); fixed=spec.get("fixed",[]);excluded=spec.get("excluded",[])
            va=base_vector(g,spec["a"],fixed,excluded,extra)
            vb=base_vector(g,spec["b"],fixed,excluded,extra)
            nodes.update((va,vb))
            arc=(va,vb) if spec[side+"_preferred"]==spec["a"] else (vb,va)
            edges.add(arc);loops += int(va==vb)
    adj=defaultdict(set);indeg={v:0 for v in nodes}
    for a,b in edges:adj[a].add(b);indeg[b]+=1
    queue=[v for v,n in indeg.items() if n==0];visited=0
    while queue:
        v=queue.pop();visited+=1
        for u in adj[v]:
            indeg[u]-=1
            if indeg[u]==0:queue.append(u)
    return {"classes":len(nodes),"arcs":len(edges),"self_loop_requirements":loops,"acyclic":visited==len(nodes)}


def mechanisms(path, dev_pairs):
    meta, hashes=json_members(path, {"execution.json","complete.json","train_specifications.json",
                                    "initial_diagnosis.json","repair.json","catalogue.json"})
    specs=meta["train_specifications.json"]
    for i,spec in enumerate(specs):certificate(spec,path.name+f"/spec{i}")
    conditions=defaultdict(lambda:Counter());runtime_seen=set();runtime_runs=0
    for name,f,_ in stream(path):
        if name=="evidence_results.jsonl":
            for line in f:
                row=json.loads(line);key=row["strategy"]+"/"+row["upper_method"];s=conditions[key]
                s["tasks"]+=1;s["attempts"]+=len(row["attempts"]);s["nodes"]+=row["budget"]["expanded_nodes"]
                for spec in row["specifications"]:
                    s["specifications"]+=1;s[spec["relation"]]+=1
                    if spec.get("family")!="diagnostic":s["non_probe_specifications"]+=1
                    certificate(spec,path.name+"/"+row["id"]+"/"+key+"/"+spec["id"])
                pair=dev_pairs[row["id"]]
                for i,a in enumerate(row["attempts"]):
                    req=a["request"]
                    s["reason_"+a.get("reason","unspecified")]+=1
                    if "a" in req and "b" in req:
                        check_history({**pair,"a":req["a"],"b":req["b"]},a.get("details",{}),
                                      req["fixed"],req["excluded"],path.name+"/"+row["id"]+f"/attempt{i}")
                    else:
                        require(not a.get("details",{}).get("bounds"),"no_candidate_no_bound_claim",
                                path.name+"/"+row["id"],a.get("reason","unspecified"))
        elif name=="runtime_results.jsonl":
            for line in f:
                row=json.loads(line);key=(row["id"],row["side"]);where=path.name+"/"+"/".join(key)
                require(key not in runtime_seen,"runtime_unique_context",where,"duplicate");runtime_seen.add(key)
                g=view(dev_pairs[row["id"]][row["side"]]);runs=row["runs"];runtime_runs+=len(runs)
                require(len(runs)==6 and {(r["backend"],r["repetition"]) for r in runs} ==
                        {(b,i) for b in ("reference","compiled") for i in range(3)},
                        "runtime_repetition_coverage",where,"missing/duplicate backend repetition")
                require(row.get("equivalent_traces") is True and all(r["trace"]==runs[0]["trace"] for r in runs),
                        "runtime_trace_equality",where,"traces differ")
                if row["family"]=="c3" and not row.get("source_verifier"):
                    issue("runtime_c3_source_receipt_absent",where,
                          "old runtime traces are independently graph-feasible but omit original source-verifier receipts","warning")
                for r in runs:
                    check_selection(g,r["selected"],r["value"],[],[],where+"/"+r["backend"])
                    actions=[t["selected"] for t in r["trace"]]
                    require(len(actions)==len(set(actions)) and set(actions)==set(r["selected"]),
                            "runtime_trace_selected",where,"trace/schedule membership mismatch")
    natural=[s for s in specs if s.get("family")!="diagnostic"]
    q0=quotient(specs);qn=quotient(natural);qr=quotient(specs,meta["repair.json"]["selected_names"])
    initial=meta["initial_diagnosis.json"]
    require(q0["classes"]==initial["quotient_nodes"] and q0["arcs"]==initial["quotient_edges"]
            and q0["self_loop_requirements"]==initial["self_loop_requirements"],
            "independent_original_quotient",path.name,str(q0))
    feature_names=[f["name"] for f in meta["catalogue.json"]];costs=meta["repair.json"]["feature_costs"]
    feasible=[]
    for mask in range(1<<len(feature_names)):
        subset=[v for i,v in enumerate(feature_names) if mask>>i&1]
        if quotient(specs,subset)["acyclic"]:feasible.append((sum(Fraction(costs[n]) for n in subset),subset))
    best=min(c for c,_ in feasible)
    require(best==Fraction(meta["repair.json"]["cost_exact"]) and qr["acyclic"],
            "independent_catalogue_minimum",path.name,f"minimum={best}; saved={meta['repair.json']['cost_exact']}")
    c=meta["complete.json"]
    require(sum(s["tasks"] for s in conditions.values())==c["evidence_tasks"]
            and len(specs)==c["specifications"] and len(runtime_seen)==c["runtime_contexts"],
            "mechanism_complete_counts",path.name,str(c))
    return {"archive":path.name,"conditions":{k:dict(v) for k,v in conditions.items()},
            "specifications":len(specs),"runtime_contexts":len(runtime_seen),"runtime_backend_runs":runtime_runs,
            "original_quotient":q0,"non_probe_quotient":qn,"repaired_quotient":qr,
            "independent_minimum_cost":str(best),"minimum_subsets":[s for c,s in feasible if c==best],
            "source_snapshot":execution_audit(meta,path.name,""),"member_sha256":hashes},specs


def discovery(path, dev_pairs, references, frozen):
    meta, hashes=json_members(path,{"candidate_banks.json","complete.json","frozen_programs.json"})
    counts=Counter();assessments={};data_splits=set();hasher=sha256()
    for name,f,_ in stream(path):
        if name!="candidate_assessments.jsonl":continue
        for line in f:
            hasher.update(line);r=json.loads(line);key=(r["arm"],r["index"])
            require(key not in assessments,"discovery_unique_candidate",path.name,str(key));counts[r["arm"]]+=1
            ratios=[]
            for row in r["rows"]:
                pair=dev_pairs[row["id"]];data_splits.add(pair["source"]["split"])
                check_selection(view(pair[row["side"]]),row["selected"],row["value"],
                                pair["fixed"],pair["excluded"],path.name+"/"+r["name"]+"/"+row["id"]+"/"+row["side"])
                ratio=row["value"]/references[(row["id"],row["side"])]
                require(near(row["ratio"],ratio),"discovery_saved_ratio",path.name+"/"+r["name"],str(row["ratio"]))
                ratios.append(ratio)
            require(near(r["quality"],math.fsum(ratios)/len(ratios)),"discovery_quality_mean",path.name+"/"+r["name"],str(r["quality"]))
            if r["arm"]!="baseline":
                require(r["program"]==meta["candidate_banks.json"][r["arm"]][r["index"]],
                        "discovery_candidate_matches_bank",path.name+"/"+r["name"],"program differs")
            assessments[key]={"name":r["name"],"program":r["program"],"quality":r["quality"],
                              "work":r["feature_work"],"consistency":r["consistency"],"contradictory":r["contradictory"],"index":r["index"]}
    require(dict(counts)=={"guided":24,"free":24,"rule":24,"enumerated":24,"baseline":1},"discovery_24_each",path.name,str(counts))
    require(data_splits=={"validation"},"discovery_validation_only",path.name,str(data_splits))
    require(meta["frozen_programs.json"].get("test_accessed") is False and frozen.get("test_accessed") is False,
            "freeze_no_test_access",path.name,"freeze claims test access")
    require(frozen["input_assessments_sha256"]==hasher.hexdigest(),"joint_assessments_sha256",path.name,"assessment bytes changed")
    # Recompute main joint prefix winners with the prespecified utility.
    cost_reference=assessments[("baseline",0)]["work"]
    for curve in frozen["joint_prefix_curves"]:
        arm,budget=curve["arm"],curve["budget"];pool=[v for (a,i),v in assessments.items() if a==arm and i<budget]
        eligible=[v for v in pool if arm=="rule" or (not v["contradictory"] and v["consistency"]>=0.75)]
        chosen=max(eligible,key=lambda v:(v["quality"]-0.002*(v["work"]/max(1,cost_reference)-1),v["quality"],-v["work"],-v["index"]))
        require(chosen["name"]==curve["name"],"joint_prefix_winner",path.name+"/"+arm+f"/{budget}",
                f"recomputed={chosen['name']}; saved={curve['name']}")
    return {"archive":path.name,"assessed_per_arm":dict(counts),"schedule_source_splits":sorted(data_splits),
            "assessment_sha256":hasher.hexdigest(),"archived_guided_scope":"minimum interface",
            "primary_joint_guided_scope":"whole-program utility, separate frozen_joint_001",
            "member_sha256":hashes}


def relevance(path, specs):
    specmap={s["id"]:s for s in specs};summary={}
    for name,f,_ in stream(path):
        if not name.endswith(".json") or name=="complete.json":continue
        data=json.load(f);seen=set();reached=escape=choices=consistent=0;lo=hi=Fraction(0);n=0
        large_regrets=0
        natural_lo=natural_hi=Fraction(0);natural_n=0
        for r in data["rows"]:
            key=(r["specification"],r["side"]);where=path.name+"/"+name+"/"+"/".join(key)
            require(key not in seen,"relevance_unique_side_requirement",where,"duplicate");seen.add(key)
            spec=specmap[key[0]];g=view(spec[r["side"]])
            reachable=r["boundary_reachable"];reached+=int(reachable)
            if not reachable:
                require(r.get("conditional_regret") is None,"unreachable_regret_not_zero",where,"unreached regret assigned")
                continue
            escape+=int(r["next_action_escape"]);chosen=r["next_action"]
            if chosen in (spec["a"],spec["b"]):
                choices+=1;consistent+=int(r["chosen_action_consistent"] is True)
            b=r.get("conditional_regret")
            if b is None:continue
            lb,ub=Fraction(b["lower_exact"]),Fraction(b["upper_exact"])
            require(0<=lb<=ub,"regret_formal_endpoint_order",where,str(b));lo+=lb;hi+=ub;n+=1
            if spec.get("family")!="diagnostic":natural_lo+=lb;natural_hi+=ub;natural_n+=1
            optimum=g.optimum(spec.get("fixed",[]),spec.get("excluded",[]))
            if optimum is not None:
                forced=g.optimum(spec.get("fixed",[])+[chosen],spec.get("excluded",[]))
                require(lb<=optimum-forced<=ub,"small_graph_regret_contains_true",where,
                        f"true={optimum-forced}; saved=[{lb},{ub}]")
            else:
                large_regrets+=1
        require(len(seen)==2*len(specs),"relevance_all_requirements",path.name+"/"+name,str(len(seen)))
        require(data["boundary_reachable"]==reached,"relevance_reachability_total",path.name+"/"+name,str(reached))
        summary[name[:-5]]={"requirements":len(seen),"reached":reached,"actual_escape":escape,
                           "actual_pair_choices":choices,"actual_consistent_pair_choices":consistent,
                           "reached_regret_mean_bounds":[float(lo/n),float(hi/n)] if n else None,
                           "non_probe_reached_regret_n":natural_n,
                           "non_probe_regret_mean_bounds":[float(natural_lo/natural_n),float(natural_hi/natural_n)] if natural_n else None,
                           "large_graph_regret_rows_without_component_witnesses":large_regrets,
                           "saved_counterfactual_escape_total":data["next_action_escape"]}
    issue("large_regret_component_witnesses_not_archived",path.name,
          "Relevance archive saves aggregate regret endpoints but no reference/forced-completion witness schedules; <=12-contact values are exhaustively verified, larger values cannot be independently reconstructed without rerunning the oracle.","warning")
    return {"archive":path.name,"programs":summary,"formal_bounds_are_not_confidence_intervals":True}


def aliases(path, dev_pairs):
    meta,hashes=json_members(path,{"execution.json","census.json","query_plan.json","summary.json","complete.json"})
    plan=set(meta["query_plan.json"]["selected_ids"]);candidate_ids=set();query_ids=set();relations=Counter()
    for name,f,_ in stream(path):
        if name=="candidates.jsonl":
            for line in f:
                c=json.loads(line);require(c["id"] not in candidate_ids,"alias_unique_candidate_id",path.name,c["id"]);candidate_ids.add(c["id"])
        if name=="oracle_results.jsonl":
            for line in f:
                r=json.loads(line);c=r["candidate"]
                require(c["id"] not in query_ids,"alias_unique_oracle_query",path.name,c["id"])
                query_ids.add(c["id"]);relations[r["pair_relation"]]+=1
                require(c["split"] in ("train","validation"),"alias_no_test_query",path.name,c["split"])
                require(r.get("unknown_is_not_preservation") is True,"alias_unknown_scope",path.name,c["id"])
                if r["pair_relation"]=="unknown":
                    require(r.get("certificate") is None,"alias_unknown_no_certificate",path.name,c["id"])
                if r.get("certificate"):certificate(r["certificate"],path.name+"/"+c["id"])
                pair={**dev_pairs[c["pair_id"]],"a":c["a"],"b":c["b"]}
                check_history(pair,r.get("details",{}),c["fixed"],c["excluded"],path.name+"/"+c["id"])
    require(query_ids==plan,"alias_frozen_query_plan",path.name,f"actual={len(query_ids)}; plan={len(plan)}")
    require(plan<=candidate_ids,"alias_plan_membership",path.name,"query missing from census")
    require(meta["complete.json"]["queries_completed"]==len(query_ids),"alias_complete_count",path.name,str(len(query_ids)))
    execution=meta["execution.json"]
    require(execution.get("test_or_transfer_outcomes_read") is False
            and execution.get("candidate_banks_or_frozen_programs_changed") is False,
            "alias_no_selection_feedback",path.name,"test outcomes or modified candidates")
    require(relations=={"unknown":200},"alias_all_unknown_200",path.name,str(relations))
    return {"archive":path.name,"enumerated_candidates":len(candidate_ids),"query_plan":len(plan),
            "query_relations":dict(relations),"certified_natural_aliases":0,
            "unknown_does_not_prove_absence":True,"summary_totals":meta["summary.json"]["totals"],
            "member_sha256":hashes}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"experiments/analysis/v03/evidence_audit.json")
    args=parser.parse_args()
    global SNAPSHOTS
    SNAPSHOTS=snapshots()
    frozen_path=ROOT/"experiments/discovery/v03/frozen_joint_001.json"
    frozen=json.loads(frozen_path.read_text());frozen_hash=sha256(frozen_path.read_bytes()).hexdigest()
    archives=sorted(RUNS.glob("*.tar.gz"));byname={p.name:p for p in archives}
    results=[]
    dev,kept=schedules(byname["development_scale_001.tar.gz"],frozen,frozen_hash,True)
    results.append(dev);dev_data,dev_pairs,dev_references=kept
    mechanism,specs=mechanisms(byname["mechanisms_001.tar.gz"],dev_pairs);results.append(mechanism)
    results.append(discovery(byname["discovery_001.tar.gz"],dev_pairs,dev_references,frozen))
    results.append(relevance(byname["relevance_001.tar.gz"],specs))
    results.append(aliases(byname["alias_census_001.tar.gz"],dev_pairs))
    consumed={r["archive"] for r in results}
    for path in archives:
        if path.name in consumed:continue
        result,_=schedules(path,frozen,frozen_hash);results.append(result)
    # Verify all declared pre-test input hashes against preserved bytes.
    known={"data.json":dev["member_sha256"]["data.json"],"results.jsonl":dev["results_sha256"]}
    for name,digest in frozen["input_sha256"].items():
        p=ROOT/name
        actual=sha256(p.read_bytes()).hexdigest() if p.is_file() else known.get(PurePosixPath(name).name)
        require(actual==digest,"freeze_input_sha256",name,f"saved={digest}; actual={actual}")
    for result in results:
        path=RUNS/result["archive"]
        result["archive_sha256"]=file_digest(path)
        result["archive_bytes"]=path.stat().st_size
    for family in ("holdout","transfer"):
        data_hashes={r.get("member_sha256",{}).get("data.json") for r in results
                     if r["archive"].startswith(family)}
        data_hashes.discard(None)
        require(len(data_hashes)<=1,"repeated_evaluation_immutable_data",family,
                "data bytes differ among execution-budget variants")
    output={"audit_version":"v03-independent-1","generated_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"v03 saved archives only; no extraction, code execution, expensive rerun, or fresh v04 test access",
            "frozen_joint_sha256":frozen_hash,"archives":results,
            "checks":dict(CHECKS),"small_graph_distinct_conditional_problems":len(BRUTE_CACHE),
            "issues":list(ISSUES.values()),
            "limits":["Floating MILP upper references are not independently certified exact optima.",
                      "Large-graph oracle upper endpoints have witness/partition/ordering checks, not a replay of every B&B frontier.",
                      "C3 physical checks are archived source-verifier receipts; this auditor independently checks graph witnesses but does not rebuild legacy physical models.",
                      "Large-graph relevance regret rows omit component completion witnesses; their endpoints are retained with a reproducibility warning, while all <=12-contact regrets are brute-force checked.",
                      "Saved no-test-selection declarations and immutable hashes are provenance evidence, not a proof of all human information access.",
                      "Only complete assigned context populations can support primary held-out means; partial harness snapshots remain diagnostics."]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    compact=[{"archive":r["archive"],"contexts":r.get("actual_context_rows"),
              "complete":r.get("quality_phase_complete")} for r in results]
    print(json.dumps({"output":str(args.output),"archives":compact,
                      "checks":sum(CHECKS.values()),"small_conditional_problems":len(BRUTE_CACHE),
                      "issues":[{"severity":i["severity"],"code":i["code"],"count":i["count"]} for i in ISSUES.values()]}))
    return int(any(i["severity"]=="error" for i in ISSUES.values()))


if __name__=="__main__":
    raise SystemExit(main())
