"""Audit and describe the registered four-block pilot; never execute a policy.

Archive bytes are read in place, without extraction. The TEST denominator is
the same independently verified clique upper for every assigned programme on
a graph. Proposal-prefix diagnostics use TRAIN only and original output slots.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/analysis/v05/matched_analysis_plan_v05.json"
PLAN_SHA = "00ba0ab40374082f65cbbfe552be03c96f0201bd48ef119d64e38d74bc09a03d"
ARMS = ("witness", "relations", "objective")
LABELS = {"witness": "A Witness", "relations": "B Relations", "objective": "C Objective"}
COLORS = {"witness": "#71559C", "relations": "#176B9B", "objective": "#687782"}
CONTRASTS = (("A_minus_B", "witness", "relations"), ("B_minus_C", "relations", "objective"))


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    return sha256(value).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def fraction(value):
    # Match the scientific model: floats are the exact stored binary weights.
    require(type(value) in (int, float, str), "Non-numeric exact weight")
    if isinstance(value, float):
        require(math.isfinite(value), "Non-finite numeric observation")
    return Fraction(value)


def mean(values):
    values = list(values)
    require(values, "Empty assigned mean")
    return sum(values, Fraction(0)) / len(values)


def estimate(value):
    return {"exact": str(value), "value": float(value), "pct": 100 * float(value)}


def close(a, b, label):
    require(math.isfinite(float(a)) and math.isfinite(float(b)), label + ": non-finite")
    require(math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-11), label + ": mismatch")


def relative(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


class Archive:
    def __init__(self, path, expected=None):
        self.path = Path(path)
        self.sha = digest(self.path.read_bytes())
        require(expected is None or expected.lower() == self.sha, "Archive hash mismatch: " + str(path))
        self.tar = tarfile.open(self.path, "r:gz")
        self.members, self.receipts = {}, {}
        for member in self.tar.getmembers():
            name = member.name
            p = PurePosixPath(name)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in name
                    and not (p.parts and ":" in p.parts[0]), "Unsafe archive member: " + name)
            require(not member.issym() and not member.islnk(), "Archive links are prohibited")
            require(member.isfile() or member.isdir(), "Special archive member is prohibited")
            require(name not in self.members, "Duplicate archive member: " + name)
            self.members[name] = member

    def raw(self, basename):
        matches = [m for name, m in self.members.items() if m.isfile() and PurePosixPath(name).name == basename]
        require(len(matches) == 1, "Missing or ambiguous member: " + basename)
        member = matches[0]
        require(member.size <= 512 * 1024 * 1024, "Analysis member exceeds declared memory cap")
        raw = self.tar.extractfile(member).read()
        require(len(raw) == member.size, "Truncated archive member")
        self.receipts[basename] = {"member": member.name, "sha256": digest(raw), "bytes": len(raw)}
        return raw

    def json(self, basename):
        return json.loads(self.raw(basename))

    def jsonl(self, basename):
        return [json.loads(line) for line in self.raw(basename).splitlines() if line.strip()]

    def provenance(self):
        return {"path": relative(self.path), "sha256": self.sha, "members_read": self.receipts,
                "safe_inventory_members": len(self.members), "extracted": False}


def graph_parts(graph):
    weights = {c["id"]: fraction(c["weight"]) for c in graph["contacts"]}
    require(len(weights) == len(graph["contacts"]), "Duplicate graph contacts")
    require(all(w >= 0 for w in weights.values()), "Negative graph weight")
    edges, adj = set(), {v: set() for v in weights}
    for pair in graph["edges"]:
        require(len(pair) == 2, "Malformed edge")
        a, b = pair
        require(a in weights and b in weights and a != b, "Invalid graph edge")
        edge = tuple(sorted((a, b)))
        edges.add(edge)
        adj[a].add(b); adj[b].add(a)
    require(len(edges) == len(graph["edges"]), "Duplicate source edges")
    return weights, adj, edges


def graph_digest(graph):
    # Graph.to_dict preserves contact order and supplies canonical edge order.
    value = {"contacts": graph["contacts"], "edges": sorted([list(sorted(e)) for e in graph["edges"]]),
             "constraints": graph.get("constraints", {})}
    return digest(json.dumps(value, sort_keys=True).encode())


def clique_upper(weights, adj):
    remaining = set(weights)
    order = sorted(remaining, key=lambda v: (-len(adj[v]), -weights[v], v))
    cliques = []
    for seed in order:
        if seed not in remaining:
            continue
        clique = [seed]; remaining.remove(seed)
        for node in order:
            if node in remaining and all(node in adj[v] for v in clique):
                clique.append(node); remaining.remove(node)
        cliques.append(sorted(clique))
    seen = set()
    for clique in cliques:
        require(clique and not seen.intersection(clique), "Invalid clique partition")
        require(all(b in adj[a] for i, a in enumerate(clique) for b in clique[i + 1:]), "Not a clique")
        seen.update(clique)
    require(seen == set(weights), "Clique partition does not cover the graph")
    return sum((max(weights[v] for v in clique) for clique in cliques), Fraction(0)), cliques


def row_reward(row, weights, adj, fixed=(), excluded=()):
    require(type(row["completed"]) is bool, "Completion must be an explicit boolean")
    if not row["completed"]:
        require(all(row.get(k) is None for k in ("selected", "trace", "value", "value_exact", "feature_work")),
                "Failed assignment must retain null result fields")
        return Fraction(0), 1
    require(row["status"] == "completed", "Success row has a failure status")
    chosen = row["selected"]
    require(len(chosen) == len(set(chosen)) and set(chosen) <= weights.keys(), "Invalid selected IDs")
    require(set(fixed) <= set(chosen) and not set(chosen).intersection(excluded), "Boundary restriction violated")
    require(all(not adj[v].intersection(chosen) for v in chosen), "Claimed completed schedule is infeasible")
    total = sum((weights[v] for v in chosen), Fraction(0))
    require(total == Fraction(row["value_exact"]), "Exact reward differs from selected contacts")
    close(row["value"], total, "Float reward")
    active = set(weights) - set(fixed) - set(excluded)
    for v in fixed:
        require(v in weights, "Unknown fixed vertex")
        active -= adj[v]
    replay = list(fixed)
    for step in row["trace"]:
        v = step["selected"]
        require(v in active and step["remaining_count"] == len(active), "Invalid actual rollout boundary")
        require(math.isfinite(float(step["score"])), "Non-finite rollout score")
        replay.append(v)
        active -= {v} | adj[v]
    require(not active and sorted(replay) == sorted(chosen), "Completed trace does not finish this schedule")
    require(type(row["feature_work"]) is int and row["feature_work"] >= 0, "Invalid completed work count")
    return total, len(row["trace"]) + len(chosen) + 3


def prefix_curves(assessments):
    result = {}
    for arm in ARMS:
        block_curves = []
        for block in range(4):
            rows = sorted((r for r in assessments if r["arm"] == arm and r["block"] == block), key=lambda r:r["slot"])
            require([r["slot"] for r in rows] == list(range(12)), "Authoritative slots changed")
            count, best, yields, utilities = 0, None, [], []
            for row in rows:
                if row["gate_passed"]:
                    require(row["status"] == "static_valid", "Nonstatic slot passed gate")
                    count += 1
                    best = row["utility"] if best is None else max(best, row["utility"])
                yields.append(count); utilities.append(best)
            block_curves.append({"block":block,"eligible_yield":yields,"best_eligible_train_J":utilities,
                                 "slot_status":[r["status"] for r in rows]})
        result[arm] = {"blocks":block_curves,
            "mean_eligible_yield":[statistics.fmean(b["eligible_yield"][i] for b in block_curves) for i in range(12)],
            "no_eligible_banks":[sum(b["best_eligible_train_J"][i] is None for b in block_curves) for i in range(12)],
            "mean_best_eligible_train_J":[None if any(b["best_eligible_train_J"][i] is None for b in block_curves)
                else statistics.fmean(b["best_eligible_train_J"][i] for b in block_curves) for i in range(12)]}
    return result


def train_audit(archive, evidence, protocol, completion, checks, plan):
    bank = archive.json("candidate_bank.json")
    gates = archive.jsonl("information_gates.jsonl")
    contexts = archive.jsonl("training_results.jsonl")
    assessments = archive.json("assessments.json")
    frozen = archive.json("frozen_programs.json")
    execution, done = archive.json("execution.json"), archive.json("complete.json")
    require(archive.raw("protocol.json") == json.dumps(protocol,indent=2,ensure_ascii=False,allow_nan=False).encode()+b"\n",
            "TRAIN protocol copy differs")
    require(done["complete"] is True and len(bank) == len(assessments) == len(gates) == 144, "Incomplete assigned TRAIN inventory")
    require(done["contexts"] == len(contexts) == len(evidence["contexts"]) == 66, "Incomplete TRAIN frame")
    require(done["attempts"] == 66 * 144, "TRAIN assignment count changed")
    require(done["frozen_sha256"] == archive.receipts["frozen_programs.json"]["sha256"], "TRAIN freeze hash differs")
    require(frozen["selection_split"] == "train" and frozen["test_accessed"] is False
            and frozen["no_replacement_no_fallback"] is True and frozen["all_assigned_banks"] == 12, "Invalid selection freeze")
    require(frozen["candidate_bank_sha256"] == archive.receipts["candidate_bank.json"]["sha256"], "Bank hash differs")
    for field in ("protocol_sha256","authoring_completion_sha256","training_evidence_sha256","source_sha256",
                  "transport_amendment_sha256","prior_input_inventory_sha256"):
        require(frozen[field] == execution[field], "TRAIN source binding changed: " + field)
    for field, expected in (("authoring_completion_sha256",plan["authoring_completion_sha256"]),
                            ("protocol_sha256",plan["source_protocol_sha256"]),
                            ("transport_amendment_sha256",plan["transport_amendment_sha256"]),
                            ("training_evidence_sha256",protocol["training_evidence_sha256"])):
        require(execution[field] == expected,"Original source binding changed: " + field)
    expected_ids = {f"block_{b}_{a}:{s}" for b in range(4) for a in ARMS for s in range(12)}
    bank_by = {r["id"]:r for r in bank}; gate_by = {r["candidate_id"]:r for r in gates}
    assess_by = {r["id"]:r for r in assessments}
    require(set(bank_by) == set(gate_by) == set(assess_by) == expected_ids, "Missing/duplicate candidate IDs")
    for name, expected in completion["response_sha256"].items():
        require(digest(archive.raw(name)) == expected == frozen["response_sha256"][name], "Raw response changed")
    evidence_by = {(r["pair_id"],r["side"]):r for r in evidence["contexts"]}
    require(len(evidence_by) == 66, "Duplicate TRAIN input contexts")
    seen, candidate_values = set(), defaultdict(list)
    for context in contexts:
        key = (context["pair_id"],context["side"])
        require(key in evidence_by and key not in seen, "Unexpected/duplicate TRAIN result")
        seen.add(key); original = evidence_by[key]
        require(context["graph_digest"] == graph_digest(original["graph"]), "TRAIN graph changed")
        require(context["family"] == original["family"] and context["fixed_reward_reference"] == original["fixed_reward_reference"]
                and context["fixed_degree_work"] == original["fixed_degree_work"], "TRAIN common references changed")
        rows = {r["candidate_id"]:r for r in context["rows"]}
        require(len(context["rows"]) == len(rows) == 144 and set(rows) == expected_ids, "Missing TRAIN assignments")
        weights, adj, _ = graph_parts(original["graph"])
        for cid, row in rows.items():
            _, n = row_reward(row,weights,adj,original["fixed"],original["excluded"]); checks["train_feasibility_replay"] += n
            q = fraction(row["value"])/fraction(context["fixed_reward_reference"]) if row["completed"] and context["fixed_reward_reference"] else Fraction(0)
            work = Fraction(row["feature_work"],max(1,context["fixed_degree_work"])) if row["completed"] else Fraction(100)
            candidate_values[cid].append((context["family"],q,work,row["completed"]))
    require(seen == set(evidence_by), "TRAIN contexts are incomplete")
    for cid in sorted(expected_ids):
        entry, assessment, gate = bank_by[cid], assess_by[cid], gate_by[cid]
        require(all(entry.get(k) == assessment.get(k) for k in ("arm","block","slot","status","program")), "Assessment slot mutation")
        require(type(gate["passed"]) is bool and assessment["gate_passed"] == gate["passed"], "Eligibility differs")
        require(not gate["passed"] or gate["status"] == "completed", "Unavailable gate passed eligibility")
        if entry["status"] == "static_valid":
            require(entry["program_sha256"] == canonical(entry["program"]), "Static AST hash changed")
            require(entry["deployment_AST_sha256"] == canonical({k:entry["program"][k] for k in ("features","rule")}), "Deployment AST changed")
        else:
            require(entry["program"] is None and not gate["passed"], "Failed output slot was salvaged")
        if gate["status"] == "completed":
            require(gate["passed"] == (not gate["full_quotient"]["contradictory"]), "DAG gate status changed")
            require(sum(gate["scalar_agreement"].values()) == len(evidence["requirements"]), "Incomplete scalar diagnostic")
        grouped = defaultdict(list)
        for family,q,work,completed in candidate_values[cid]: grouped[family].append((q,work))
        quality = mean(mean(r[0] for r in rs) for rs in grouped.values())
        work = mean(mean(r[1] for r in rs) for rs in grouped.values())
        utility = quality - fraction(protocol["selection"]["cost_penalty"])*(work-1)
        for field, val in (("quality",quality),("relative_work",work),("utility",utility)):
            close(assessment[field],val,"TRAIN " + cid + " " + field)
            checks["train_means"] += 1
        require(assessment["assigned_contexts"] == 66 and assessment["completed_contexts"] == sum(r[3] for r in candidate_values[cid]),
                "TRAIN completion totals differ")
    selected = {}
    for block in range(4):
        for arm in ARMS:
            name = f"block_{block}_{arm}"; choice = frozen["selection"][name]
            pool = [r for r in assessments if r["block"]==block and r["arm"]==arm and r["gate_passed"]]
            require(choice["eligible_slots"] == len(pool), "Selected-bank eligible count differs")
            if pool:
                # Audit the frozen TRAIN choice; this never creates or replaces an AST.
                best = max(pool,key=lambda r:(r["utility"],-r["slot"]))
                require(choice["selected_id"] == best["id"] and frozen["programs"][name] == best["program"], "TRAIN choice changed")
                close(choice["utility"],best["utility"],"Selected TRAIN utility")
                selected[name] = {"selected_id":best["id"],"program_sha256":canonical(best["program"]),
                                  "deployment_AST_sha256":best["deployment_AST_sha256"],"slot":best["slot"]}
            else:
                require(choice["selected_id"] is None and name not in frozen["programs"] and choice["fallback_used"] is False,
                        "A no-eligible cell was replaced")
                selected[name] = {"selected_id":None,"programme_available":False}
    require(frozen["no_eligible_banks"] == sum(r["selected_id"] is None for r in selected.values()), "No-eligible count differs")
    diagnostics={arm:{"full_gate_passed":sum(gate_by[r["id"]]["passed"] for r in bank if r["arm"]==arm),
                      "actual_only_acyclic":sum(gate_by[r["id"]].get("status")=="completed" and
                          not gate_by[r["id"]]["actual_only_quotient"]["contradictory"] for r in bank if r["arm"]==arm),
                      "assigned":48} for arm in ARMS}
    return {"frozen":frozen,"execution":execution,"assessments":assessments,"gates":gates,"selected":selected,"gate_diagnostics":diagnostics,
            "curves":prefix_curves(assessments),"contexts":len(contexts)}


def summarize_test(records, assignments, train):
    groups = {"overall":records}
    groups.update({p:[r for r in records if r["profile"]==p] for p in ("standard","dense_long")})
    groups.update({f"size_{s}":[r for r in records if r["size"]==s] for s in (64,128,256)})
    groups.update({p:[r for r in records if r["regime"]==p] for p in ("balanced","ground_scarce","satellite_scarce")})
    summaries = {}
    for group, contexts in groups.items():
        arm_rows = {}
        for arm in ARMS:
            blocks = []
            for b in range(4):
                name = f"block_{b}_{arm}"; rows = [c["rows"][name] for c in contexts]
                blocks.append({"block":b,"quality":estimate(mean(Fraction(r["ratio_exact"]) for r in rows)),
                    "completed":sum(r["completed"] for r in rows),"assigned":len(rows),
                    "mean_cpu_seconds":statistics.fmean(r["cpu_seconds"] for r in rows),
                    "median_cpu_seconds":statistics.median(r["cpu_seconds"] for r in rows),
                    "mean_wall_seconds":statistics.fmean(r["wall_seconds"] for r in rows),
                    "median_wall_seconds":statistics.median(r["wall_seconds"] for r in rows),
                    "mean_completed_work":statistics.fmean(r["feature_work"] for r in rows if r["completed"])
                        if any(r["completed"] for r in rows) else None})
            arm_rows[arm] = {"blocks":blocks,"four_block_mean":estimate(mean(Fraction(b["quality"]["exact"]) for b in blocks)),
                             "completed":sum(b["completed"] for b in blocks),"assigned":4*len(contexts)}
        contrasts = {}
        for label,a,b in CONTRASTS:
            block_estimates=[]
            for block in range(4):
                deltas = [Fraction(c["rows"][f"block_{block}_{a}"]["ratio_exact"])-Fraction(c["rows"][f"block_{block}_{b}"]["ratio_exact"])
                          for c in contexts]
                value=mean(deltas)
                block_estimates.append({"block":block,"difference":estimate(value),"paired_contexts":len(deltas),
                    "positive_contexts":sum(v>0 for v in deltas),"zero_contexts":sum(v==0 for v in deltas),
                    "negative_contexts":sum(v<0 for v in deltas),"paired_values_exact":[str(v) for v in deltas]})
            vals = [Fraction(b["difference"]["exact"]) for b in block_estimates]
            contrasts[label]={"blocks":block_estimates,"four_block_mean":estimate(mean(vals)),
                "observed_block_range_pp":[100*float(min(vals)),100*float(max(vals))],
                "block_signs":{"positive":sum(v>0 for v in vals),"zero":sum(v==0 for v in vals),"negative":sum(v<0 for v in vals)},
                "authoring_blocks":4,"paired_assignments":4*len(contexts),"confidence_interval":None}
        degree_rows = [c["rows"]["degree"] for c in contexts]
        summaries[group]={"contexts":len(contexts),"source_pairs":len({c["pair_id"] for c in contexts}),
            "distinct_source_seeds":len({c["source_seed"] for c in contexts}),"arms":arm_rows,"contrasts":contrasts,
            "degree":{"quality":estimate(mean(Fraction(r["ratio_exact"]) for r in degree_rows)),
                      "completed":sum(r["completed"] for r in degree_rows),"assigned":len(contexts)}}
    return summaries


def test_audit(fresh, evaluation, train, protocol, checks):
    data = fresh.json("data.json"); fresh_done = fresh.json("complete.json")
    copied = evaluation.raw("data.json")
    require(digest(copied) == fresh.receipts["data.json"]["sha256"], "Fresh/evaluation input bytes differ")
    frozen = evaluation.json("frozen_programs.json")
    require(frozen == train["frozen"], "TEST uses another frozen bank")
    execution, done = evaluation.json("execution.json"), evaluation.json("complete.json")
    contexts = evaluation.jsonl("results.jsonl")
    require(done["complete"] is True and fresh_done["complete"] is True, "Archives are not complete assignments")
    require(execution["new_program_selection"] is False and execution["external_model_calls"] == execution["online_oracle_calls"] == 0,
            "Unexpected online adaptation")
    require(execution["source_sha256"] == train["execution"]["source_sha256"], "TRAIN/TEST execution source differs")
    require(execution["data_sha256"] == fresh.receipts["data.json"]["sha256"] == fresh_done["data_sha256"], "Fresh data hash differs")
    require(execution["freeze_sha256"] == evaluation.receipts["frozen_programs.json"]["sha256"] == data["protocol"]["selection_frozen_sha256"],
            "Fresh generation does not bind this freeze")
    require(execution["protocol_sha256"] == data["protocol"]["protocol_sha256"] == train["frozen"]["protocol_sha256"], "Protocol changed")
    require(done["results_sha256"] == evaluation.receipts["results.jsonl"]["sha256"], "Outcome member hash differs")
    require(len(contexts) == done["contexts"] == fresh_done["contexts"] == 216 and len(data["test"])==108, "Assigned fresh population differs")
    require(done["assigned_runs"] == 216*13, "TEST assignment denominator differs")
    require(data["protocol"]["no_C3"] is True and data["protocol"]["outcome_filtering"] is False, "Fresh population scope changed")
    inputs, seen = {}, set()
    for pair in data["test"]:
        require(pair["left"]["contacts"] == pair["right"]["contacts"], "Intervention changed original contacts/weights")
        source=pair["source"]
        require(source["profile"] in protocol["test"]["profiles"] and source["regime"] in protocol["test"]["regimes"]
                and source["size"] in protocol["test"]["sizes"] and source["namespace"] == protocol["test"]["namespace"]
                and source["split"] == "test" and source["outcome_filtering"] is False, "Unregistered TEST input")
        for side in ("left","right"):
            key=(pair["id"],side)
            require(key not in inputs,"Duplicate fresh input context")
            inputs[key]=(pair,side)
    methods = {f"block_{b}_{a}" for b in range(4) for a in ARMS} | {"degree"}
    records=[]; completed_total=0; population=Counter()
    for context in sorted(contexts,key=lambda c:(c["pair_id"],c["side"])):
        key=(context["pair_id"],context["side"])
        require(key in inputs and key not in seen,"Unexpected/duplicate TEST result")
        seen.add(key); pair,side=inputs[key]; graph=pair[side]
        require(context["graph_digest"]==graph_digest(graph) and context["source"]==pair["source"]
                and context["family"]==pair["family"] and context["size"]==len(graph["contacts"]), "TEST task provenance differs")
        weights,adj,_=graph_parts(graph); upper,cover=clique_upper(weights,adj)
        require(upper>0 and upper==Fraction(context["reference"]["upper_exact"]),"Common clique upper differs")
        require(0<=Fraction(context["reference"]["lower_exact"])<=upper,"Invalid reference enclosure")
        rows={r["method"]:r for r in context["rows"]}
        require(len(context["rows"])==len(rows)==13 and set(rows)==methods,"Missing/duplicate TEST assignments")
        audited={}
        for name,row in rows.items():
            reward,n=row_reward(row,weights,adj,pair["fixed"],pair["excluded"]);checks["test_feasibility_replay"]+=n
            require(reward<=upper,"Feasible reward exceeds verified common upper")
            for field in ("cpu_seconds","wall_seconds"):
                require(isinstance(row[field],(int,float)) and math.isfinite(row[field]) and row[field]>=0,"Invalid recorded cost")
            if name!="degree" and train["selected"][name]["selected_id"] is None:
                require(not row["completed"] and row["status"]=="no_eligible_training_slot","Missing bank used a fallback")
            completed_total+=row["completed"]
            audited[name]={"completed":row["completed"],"status":row["status"],"reward_exact":str(reward),
                "ratio_exact":str(reward/upper),"feature_work":row["feature_work"],"cpu_seconds":row["cpu_seconds"],"wall_seconds":row["wall_seconds"]}
        source=pair["source"];population[source["profile"],source["regime"],source["size"]]+=1
        records.append({"pair_id":pair["id"],"side":side,"source_seed":source["seed"],"profile":source["profile"],
            "regime":source["regime"],"size":len(weights),"graph_digest":context["graph_digest"],
            "common_upper_exact":str(upper),"verified_clique_partition":cover,"rows":audited})
        checks["common_clique_upper"]+=len(weights)+sum(len(c)*(len(c)-1)//2 for c in cover)+1
    require(seen==set(inputs) and completed_total==done["completed_runs"],"Incomplete TEST assignment reconciliation")
    require(len(population)==18 and all(n==12 for n in population.values()),"TEST stratum counts differ")
    return {"records":records,"summaries":summarize_test(records,methods,train),"completed":completed_total,"assigned":216*13,
            "population_counts":[{"profile":p,"regime":r,"size":s,"contexts":n} for (p,r,s),n in sorted(population.items())]}


def plot(curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family":"Arial","font.size":9,"axes.titlesize":9,"axes.labelsize":9,
        "xtick.labelsize":9,"ytick.labelsize":9,"legend.fontsize":9,"pdf.fonttype":42,"ps.fonttype":42,
        "axes.spines.top":False,"axes.spines.right":False,"axes.edgecolor":"#687782","text.color":"#243640",
        "axes.labelcolor":"#243640","xtick.color":"#243640","ytick.color":"#243640"})
    fig=plt.figure(figsize=(7,2.8))
    a=fig.add_axes([.08,.20,.39,.64]);b=fig.add_axes([.60,.39,.38,.45]);m=fig.add_axes([.60,.20,.38,.12],sharex=b)
    x=np.arange(1,13);styles={"witness":("o","-"),"relations":("s","--"),"objective":("^",":")}
    handles=[]
    for arm in ARMS:
        color=COLORS[arm];mark,style=styles[arm];c=curves[arm]
        for block in c["blocks"]:
            a.plot(x,block["eligible_yield"],color=color,alpha=.23,lw=.75)
            b.plot(x,[np.nan if v is None else v for v in block["best_eligible_train_J"]],color=color,alpha=.30,lw=.75)
        h,=a.plot(x,c["mean_eligible_yield"],color=color,marker=mark,ms=3,lw=1.25,ls=style,label=LABELS[arm]);handles.append(h)
        b.plot(x,[np.nan if v is None else v for v in c["mean_best_eligible_train_J"]],color=color,marker=mark,ms=3,lw=1.25,ls=style)
    a.set(title="(a) Eligible proposals",xlabel="Original proposal slot",ylabel="Cumulative count",xlim=(.7,12.3),ylim=(-.25,12.35))
    a.set_xticks(range(1,13));a.set_yticks([0,3,6,9,12]);a.grid(axis="y",color="#DEE4E8",lw=.5)
    b.set(title="(b) Best eligible TRAIN J",ylabel="Utility",xlim=(.7,12.3));b.grid(axis="y",color="#DEE4E8",lw=.5)
    b.tick_params(axis="x",labelbottom=False)
    if not any(v is not None for arm in ARMS for block in curves[arm]["blocks"] for v in block["best_eligible_train_J"]):
        b.text(.5,.5,"No eligible prefixes",transform=b.transAxes,ha="center",va="center",color="#687782")
    m.set(ylim=(-.5,2.5),xlabel="Original proposal slot");m.set_xticks(range(1,13));m.set_yticks([0,1,2],labels=["C","B","A"])
    m.tick_params(length=0);m.spines["left"].set_visible(False);m.spines["bottom"].set_visible(False)
    for index,arm in enumerate(ARMS):
        y=2-index
        for slot,count in enumerate(curves[arm]["no_eligible_banks"],1):
            m.text(slot,y,str(count),ha="center",va="center",fontsize=9,color="#D36B32" if count else "#AAB4BB")
    fig.text(.60,.345,"Banks without an eligible prefix (of 4)",fontsize=9,ha="left",color="#687782")
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.52,1.01),ncol=3,frameon=False,handlelength=2,
               columnspacing=1.2,borderaxespad=.15)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path);fig.savefig(path.with_suffix(".png"),dpi=300);plt.close(fig)


def table(payload):
    summary=payload["test"]["summaries"]["overall"];train=payload["train"]
    row_end = " " + chr(92) * 2
    lines=["% Generated from frozen original-slot TRAIN and common-graph TEST observations.","\\begin{table*}[t]","\\centering",
        "\\caption{Four-block matched evidence pilot. Cells report failure-zero mean $100W/U$ on the same 216 fresh graphs; $U$ is a verified clique upper, not an optimum. All twelve output slots per cell are retained. Paired contrasts are percentage points; four blocks are descriptive authoring replicates.}",
        "\\label{tab:matched-llm}","\\setlength{\\tabcolsep}{6pt}","\\begin{tabular}{lrrrrcc}","\\toprule",
        "Arm & Block 1 & Block 2 & Block 3 & Block 4 & Eligible/48 & Complete/864"+row_end,"\\midrule"]
    for arm in ARMS:
        values=summary["arms"][arm]
        eligible=sum(r["gate_passed"] for r in train["assessments"] if r["arm"]==arm)
        lines.append(LABELS[arm]+" & "+" & ".join(f"{b['quality']['pct']:.2f}" for b in values["blocks"])
                     +f" & {eligible}/48 & {values['completed']}/864"+row_end)
    degree=summary["degree"]
    lines.append(f"Degree & \\multicolumn{{4}}{{c}}{{{degree['quality']['pct']:.2f} (one common reference)}} & -- & {degree['completed']}/216"+row_end)
    lines.append("\\midrule")
    for key,_,_ in CONTRASTS:
        c=summary["contrasts"][key];label="A$-$B" if key=="A_minus_B" else "B$-$C"
        lines.append(label+" & "+" & ".join(f"{v['difference']['pct']:+.2f}" for v in c["blocks"])
            +f" & \\multicolumn{{2}}{{c}}{{mean {c['four_block_mean']['pct']:+.2f} pp}}"+row_end)
    return "\n".join(lines+["\\bottomrule","\\end{tabular}","\\end{table*}",""])


def markdown(payload):
    lines=["# Matched cold-authoring pilot: frozen V05 results","",
        "This report follows the analysis contract frozen before any new TRAIN/TEST outcome was read. Four authoring blocks, three evidence arms, and twelve original slots per cell are a bounded descriptive pilot. It does not establish model-population superiority, public-graph transfer, or physical C3 generalization.","",
        "A receives explicit quotient equality-join witnesses plus certified labels; B receives the same certified labels; C receives objective feedback without labels. Grammar, example graphs, degree feedback, full-interface gate, TRAIN selector, and demanded runtime are common. All slots and unavailable selections remain assigned; no post-TEST selection or AST execution occurs in this analysis.","",
        "TEST quality is exact feasible reward over a common independently verified weighted clique upper, with failures zero. The denominator differs from the strongest-feasible-witness ratio used by the V04 main baseline table. Neither is a proven optimum. All sides and all registered regimes/sizes are retained. Completion of an archive means every assignment is recorded, not that every programme succeeds.","",
        "## Four-block TEST comparisons","",
        "| Population | Arm | Block 1 % | Block 2 % | Block 3 % | Block 4 % | Mean of four % | Completed/assigned |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for group in ("overall","standard","dense_long"):
        summary=payload["test"]["summaries"][group]
        for arm in ARMS:
            row=summary["arms"][arm]
            lines.append(f"| {group} | {LABELS[arm]} | "+" | ".join(f"{b['quality']['pct']:.4f}" for b in row["blocks"])
                +f" | {row['four_block_mean']['pct']:.4f} | {row['completed']}/{row['assigned']} |")
    lines.extend(["","| Population | Contrast | Four block differences (pp) | Mean (pp) | Observed block range (pp) | Block signs +/0/− |",
                  "|---|---|---|---:|---|---|"])
    for group in ("overall","standard","dense_long"):
        for key,c in payload["test"]["summaries"][group]["contrasts"].items():
            signs=c["block_signs"]
            lines.append(f"| {group} | {key} | "+", ".join(f"{b['difference']['pct']:+.4f}" for b in c["blocks"])
                +f" | {c['four_block_mean']['pct']:+.4f} | {c['observed_block_range_pp']} | {signs['positive']}/{signs['zero']}/{signs['negative']} |")
    overall=payload["test"]["summaries"]["overall"]
    lines.extend(["","These ranges describe the four observed blocks. They are not confidence intervals. Paired graph comparisons do not create additional independent authoring replicates. No p-value, best-of-four result, or model-population effect is claimed.","",
        "The single common Degree reference has failure-zero quality "+", ".join(
            f"{p}: {payload['test']['summaries'][p]['degree']['quality']['pct']:.6f}%" for p in ("overall","standard","dense_long"))+". It is not replicated as four independent authoring outputs.","",
        f"In this fixed four-block pilot, explicit joins add {overall['contrasts']['A_minus_B']['four_block_mean']['pct']:.6f} percentage points over labels, with two zero block contrasts. Labels add {overall['contrasts']['B_minus_C']['four_block_mean']['pct']:.6f} points over objective feedback, with three positive block contrasts and one reversal. The observed additional join benefit is small; the label contrast concerns these particular selected programmes. Every evidence arm uses an LLM, so this design does not isolate an LLM-versus-non-LLM benefit. Token costs are unequal. These outcomes support no published-solver dominance or model-population claim.","",
        "## Original-slot TRAIN curves","",
        "Panel (a) plots cumulative eligible yield against original proposal slot; thin lines are individual banks and thick lines are four-block means. Panel (b) plots each bank's best eligible TRAIN J and a mean only when all four banks have an eligible prefix. Its count strip retains no-eligible prefixes explicitly. Invalid, missing and duplicate slots are never replaced or sorted away. These are finite-bank TRAIN sample-efficiency curves, not online learning, CPU anytime trajectories, or TEST-based prefix selection.","",
        "Eligibility is the saved full declared-interface DAG gate, not perfect scalar score agreement. Scalar agreement and actual-only gate diagnoses remain separate saved diagnostics. All 48 slots per arm have acyclic actual-only quotients; the 48/48, 48/48, 40/48 full-gate contrast therefore arises from requirements that include prior diagnostic probes. TRAIN J is reconciled to original complete-schedule reward/common frozen feasible reference and relative feature work, with failure reward 0 and failure work 100; its value may exceed 1. No new completion hard gate is introduced.","",
        "## Authoring provenance and cost","",
        "All twelve native cold CLI cells requested gpt-6.1-sol with ultra reasoning. Actual served-model identifiers were absent from the retained events. The original protocol's model label is not upgraded into observed provider metadata. Token events are retained exactly, including input, cached-input, output and reasoning-output counts; slots/settings/session counts are matched, token and latency costs are not. Cached input is a subset of input and is not added again as extra input.","",
        "| Cell | Input tokens | Cached input | Output tokens | Reasoning output | Observed model |","|---|---:|---:|---:|---:|---|"])
    for cell,row in sorted(payload["authoring_usage"].items()):
        totals=Counter()
        for event in row.get("usage_events") or []: totals.update(event["usage"])
        lines.append(f"| {cell} | {totals.get('input_tokens','unavailable')} | {totals.get('cached_input_tokens','unavailable')} | {totals.get('output_tokens','unavailable')} | {totals.get('reasoning_output_tokens','unavailable')} | {row.get('observed_model') or 'unavailable'} |")
    lines.extend(["","## Independent audit and immutable sources","",
        f"Verified assignments: TRAIN {payload['train']['contexts']}×144; TEST {payload['test']['assigned']} assigned, {payload['test']['completed']} completed. Independent checks: {payload['checks']}. The analysis replays stored selected vertices and residual counts, verifies exact reward and clique partitions, and recomputes means/contrasts. It never evaluates a scorer, changes a programme, regenerates a candidate, or reruns a solver. Saved feature-gate diagnostics are reconciled but not recomputed from ASTs.","",
        f"Analysis plan SHA256: `{payload['analysis_plan_sha256']}`; analysis script SHA256: `{payload['analysis_script_sha256']}`.",""])
    for name,row in payload["sources"].items(): lines.append(f"- {name}: `{row['path']}` — SHA256 `{row['sha256']}`")
    lines.extend(["","All archive/member hashes, exact paired values, complete slot statuses, selected-AST identities, work/runtime data, registered subgroups and authoring usage are retained in the source-backed JSON. No external result or model API was accessed.",""])
    return "\n".join(lines)


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")


def train_markdown(payload):
    lines=["# Matched cold-authoring pilot: TRAIN analysis, TEST pending", "",
        "The immutable analysis contract was frozen before any new TRAIN/TEST outcome was read. This stage reads only the completed TRAIN archive and authoring/input receipts. No fresh TEST archive has been read, no scorer has been executed, and no programme has been changed or selected again.", "",
        "Four blocks compare A (explicit quotient equality-join witnesses plus certified labels), B (the same certified labels), and C (objective feedback without labels). The 144 original slots remain assigned. Eligibility is the full declared-interface DAG gate, not perfect numerical score agreement. TRAIN utility follows the original family-macro quality and relative-work objective, including its failure rules.", "",
        "| Arm | Eligible / 48 | Block 1 final best J | Block 2 | Block 3 | Block 4 |",
        "|---|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        curves=payload["train"]["curves"][arm]
        lines.append("| "+LABELS[arm]+" | "+str(sum(b["eligible_yield"][-1] for b in curves["blocks"]))+"/48 | "+
            " | ".join("unavailable" if b["best_eligible_train_J"][-1] is None else f"{b['best_eligible_train_J'][-1]:.6f}" for b in curves["blocks"])+" |")
    lines.extend(["", "All 48 slots per arm have acyclic actual-only quotients. The full-gate yield difference arises from requirements that include prior diagnostic probes, rather than obstruction on the saved actual-only requirements. No programme satisfies all 824 numerical score requirements; DAG eligibility is distinct from bounded-rule fit.", "",
        "Panel (a) plots cumulative eligible yield over original slots 1–12. Panel (b) plots best eligible TRAIN J per bank; the arm mean appears only when every block has an eligible prefix. The count strip retains missing eligible prefixes. These are finite-bank TRAIN sample-efficiency diagnostics, not online learning, TEST performance curves, or CPU anytime trajectories. Thin lines are individual banks and thick lines are four-block means.", "",
        "All twelve native cold CLI cells requested gpt-6.1-sol with ultra reasoning; served-model identifiers were absent from retained events. Settings/session/slot counts were matched, token and latency costs were not. Four authoring blocks support descriptive comparisons, not model-population inference. No TEST outcome or model advantage is reported at this stage.", "",
        f"Independent checks: {payload['checks']}. TRAIN has {payload['train']['contexts']} contexts × 144 assigned original slots. Archive completion denotes recorded assignments, not universal solver success.", "",
        f"Analysis contract SHA256: `{payload['analysis_plan_sha256']}`. Analysis script SHA256: `{payload['analysis_script_sha256']}`.", ""])
    for name,row in payload["sources"].items(): lines.append(f"- {name}: `{row['path']}` — SHA256 `{row['sha256']}`")
    lines.extend(["", "The JSON preserves individual prefix curves, all original slot statuses, selected immutable AST identities, exact feasibility checks, saved gate diagnostics and source/member hashes. The final TEST table will be generated only after its fresh-input and completed-evaluation archives are available.", ""])
    return "\n".join(lines)


def self_test():
    weights={"a":Fraction(5),"b":Fraction(4),"c":Fraction(3)};adj={"a":{"b"},"b":{"a"},"c":set()}
    upper,cover=clique_upper(weights,adj);require(upper==8 and sorted(v for c in cover for v in c)==["a","b","c"],"Tiny clique check")
    row={"completed":True,"status":"completed","selected":["a","c"],"value":8,"value_exact":"8","feature_work":3,
         "trace":[{"selected":"a","remaining_count":3,"score":1},{"selected":"c","remaining_count":1,"score":1}]}
    require(row_reward(row,weights,adj)[0]==8,"Tiny feasible replay")
    bad={**row,"selected":["a","b"]}
    try:row_reward(bad,weights,adj)
    except ValueError:pass
    else:raise AssertionError("Infeasible row accepted")
    failed={"completed":False,**{k:None for k in ("selected","trace","value","value_exact","feature_work")}}
    require(row_reward(failed,weights,adj)[0]==0,"Failure-zero rule")
    rows=[{"arm":a,"block":b,"slot":s,"status":"static_valid" if s>=2 else "missing_slot",
           "gate_passed":s>=2,"utility":s/10} for a in ARMS for b in range(4) for s in range(12)]
    c=prefix_curves(rows)["witness"]
    require(c["no_eligible_banks"][:3]==[4,4,0] and c["mean_best_eligible_train_J"][:3]==[None,None,.2]
            and c["mean_eligible_yield"][-1]==10,"Original-slot null prefix")
    require(mean([Fraction(0),Fraction(1)])==Fraction(1,2),"Assigned mean includes failure")
    print("PASS: tiny exact clique, feasible trace, infeasible rejection, failure-zero, original-slot null prefix, assigned denominator")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true");p.add_argument("--check-contract",action="store_true")
    p.add_argument("--train-only",action="store_true",help="Audit TRAIN and export prefix curves without opening fresh/TEST archives")
    p.add_argument("--train",default=str(ROOT/"experiments/runs/v05/matched_train_v05_001.tar.gz"))
    p.add_argument("--fresh",default=str(ROOT/"experiments/runs/v05/matched_fresh_v05_001.tar.gz"))
    p.add_argument("--evaluation",default=str(ROOT/"experiments/runs/v05/matched_eval_v05_001.tar.gz"))
    for name in ("train","fresh","evaluation"):p.add_argument("--"+name+"-sha256")
    p.add_argument("--training-evidence",default=str(ROOT/"experiments/discovery/v05/training_evidence.json"))
    p.add_argument("--authoring-completion",default=str(ROOT/"experiments/discovery/v05/authoring_completion.json"))
    p.add_argument("--original-protocol",default=str(ROOT/"experiments/discovery/v05/protocol.json"))
    p.add_argument("--out")
    p.add_argument("--figure",default=str(ROOT/"paper/figures/llm_pilot_v05.pdf"))
    p.add_argument("--table",default=str(ROOT/"paper/generated/matched_llm_table_v05.tex"))
    p.add_argument("--markdown",default=str(ROOT/"docs/MATCHED_LLM_RESULTS_V05.md"))
    a=p.parse_args()
    if a.self_test:self_test();return
    require(digest(PLAN.read_bytes())==PLAN_SHA,"Frozen analysis contract changed")
    plan=json.loads(PLAN.read_bytes())
    if a.check_contract:
        print(json.dumps({"plan_sha256":PLAN_SHA,"version":plan["version"],"outcomes_read":False}));return
    # No result archive is opened before the exact frozen analysis plan is checked.
    evidence_raw=Path(a.training_evidence).read_bytes();completion_raw=Path(a.authoring_completion).read_bytes()
    original_protocol_raw=Path(a.original_protocol).read_bytes()
    require(digest(completion_raw)==plan["authoring_completion_sha256"],"Authoring completion changed")
    require(digest(original_protocol_raw)==plan["source_protocol_sha256"],"Original protocol changed")
    evidence,completion=json.loads(evidence_raw),json.loads(completion_raw)
    train=Archive(a.train,a.train_sha256)
    protocol_raw=train.raw("protocol.json");protocol=json.loads(protocol_raw)
    # The runner writes an indented JSON copy; bind original bytes and verify
    # semantic equality rather than pretending the serialized copy is identical.
    require(protocol==json.loads(original_protocol_raw) and digest(evidence_raw)==protocol["training_evidence_sha256"],"Original protocol/evidence changed")
    checks=Counter();t=train_audit(train,evidence,protocol,completion,checks,plan)
    payload={"version":"matched_analysis_v05_001","analysis_plan_sha256":PLAN_SHA,"analysis_script_sha256":digest(Path(__file__).read_bytes()),
        "stage":"TRAIN_only" if a.train_only else "TRAIN_and_TEST", "test_results_read":False,
        "sources":{"train":train.provenance(),
                   "original_protocol":{"path":relative(a.original_protocol),"sha256":digest(original_protocol_raw)},
                   "training_evidence":{"path":relative(a.training_evidence),"sha256":digest(evidence_raw)},
                   "authoring_completion":{"path":relative(a.authoring_completion),"sha256":digest(completion_raw)}},
        "checks":dict(checks),"train":t,"authoring_usage":completion["actual_model_and_usage"],
        "scope":"Four-block descriptive evidence pilot; not authoring-population inference; no TEST prefix selection or policy evaluation"}
    if a.train_only:
        output=a.out or str(ROOT/"experiments/analysis/v05/matched_train_analysis_v05.json")
        write(output,payload);write(a.markdown,train_markdown(payload));plot(t["curves"],a.figure)
        print(json.dumps({"complete":True,"stage":"TRAIN_only","test_results_read":False,"checks":dict(checks),"output":output},ensure_ascii=False));return
    fresh=Archive(a.fresh,a.fresh_sha256);evaluation=Archive(a.evaluation,a.evaluation_sha256)
    e=test_audit(fresh,evaluation,t,protocol,checks)
    payload.update({"test":e,"checks":dict(checks),"test_results_read":True})
    payload["sources"].update({"fresh":fresh.provenance(),"evaluation":evaluation.provenance()})
    output=a.out or str(ROOT/"experiments/analysis/v05/matched_results_v05.json")
    write(output,payload);write(a.table,table(payload));write(a.markdown,markdown(payload));plot(t["curves"],a.figure)
    print(json.dumps({"complete":True,"assigned_test":e["assigned"],"completed_test":e["completed"],"checks":dict(checks),"output":output},ensure_ascii=False))


if __name__=="__main__":main()
