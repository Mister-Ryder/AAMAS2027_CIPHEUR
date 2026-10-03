"""Independent complete-v03 population summaries with retained null failures."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import verify_v03_evidence as audit

ROOT = Path(__file__).resolve().parents[1]
METHODS = ["guided", "free", "rule", "enumerated", "guided_minimum_interface", "guided_no_cost", "multi_start_1to2_search", "HiGHS_MILP"]


def summary(name):
    path = ROOT / "experiments/runs/v03" / (name + ".tar.gz")
    rows = []
    for member, handle, _ in audit.stream(path):
        if member != "results.jsonl": continue
        for line in handle:
            r = json.loads(line)
            by = {m["method"]: m for m in r["methods"]}
            best = max(m["value"] for m in by.values() if m.get("completed", m["value"] is not None))
            vector = []
            for method in METHODS:
                m = by[method]
                done = m.get("completed", m["value"] is not None)
                vector.extend([m["value"]/r["reference"]["upper"] if done else 0, int(done), m["value"]/best if done else 0])
            stratum = "temporal" if r["family"].startswith("temporal_") else "dense_long" if r["family"].startswith("dense_long_") else r["family"]
            rows.append({"family":r["family"], "n":r["n"], "cluster":str(r["cluster"]), "stratum":stratum, "values":np.asarray(vector)})
    def population(selected):
        blocks = defaultdict(lambda:defaultdict(list))
        for r in selected: blocks[r["stratum"]][r["cluster"]].append(r["values"])
        observed = sum((r["values"] for r in selected), np.zeros(len(METHODS)*3))
        rng = np.random.default_rng(20261003)
        samples = np.zeros((2000,len(METHODS)*3))
        for stratum, clusters in sorted(blocks.items()):
            values = np.asarray([np.sum(clusters[k],axis=0) for k in sorted(clusters)])
            indices = rng.integers(0,len(values),size=(2000,len(values)))
            samples += values[indices].sum(axis=1)
        result = {"contexts":len(selected), "clusters":{s:len(c) for s,c in blocks.items()}, "methods":{}, "paired_zero_quality_differences_pp":{}}
        for i, method in enumerate(METHODS):
            q, done, primal = observed[i*3:i*3+3]
            qs, ds, ps = samples[:,i*3],samples[:,i*3+1],samples[:,i*3+2]
            result["methods"][method] = {"completed":int(done), "failed":len(selected)-int(done), "coverage":done/len(selected), "quality_completed_only":q/done if done else None, "quality_all_assigned_zero":q/len(selected), "quality_all_assigned_zero_ci95":np.quantile(qs/len(selected),[.025,.975]).tolist(), "coverage_ci95":np.quantile(ds/len(selected),[.025,.975]).tolist(), "quality_completed_only_ci95":np.quantile(np.divide(qs,ds,out=np.full_like(qs,np.nan),where=ds>0),[.025,.975]).tolist(), "primal_best_observed_ratio_all_assigned_zero":primal/len(selected)}
        for other in ("free", "rule", "enumerated", "guided_minimum_interface", "multi_start_1to2_search"):
            j = METHODS.index(other)*3
            result["paired_zero_quality_differences_pp"]["guided_minus_"+other] = {"mean":100*(observed[0]-observed[j])/len(selected), "ci95":(100*np.quantile((samples[:,0]-samples[:,j])/len(selected),[.025,.975])).tolist()}
        return result
    return {"archive":name,"archive_sha256":audit.file_digest(path), "whole_population":population(rows), "families":{f:population([r for r in rows if r["family"]==f]) for f in sorted({r["family"] for r in rows})}, "sizes":{str(n):population([r for r in rows if r["n"]==n]) for n in sorted({r["n"] for r in rows})}}


if __name__ == "__main__":
    results = [summary(n) for n in ("holdout_cooperative_003","transfer_cooperative_003")]
    report = {"scope":"Complete v03 cooperative003 archives only; no fresh v04 data", "confidence":"2000 percentile seed-block bootstrap replicates, seed20261003; pair configurations and shared temporal regime seeds retained; temporal/C3/probe strata held fixed", "null_policy":"Failed schedules contribute zero only to explicitly all-assigned performance; completed-only quality is reported alongside coverage", "reference_scope":"Floating MILP upper reference, not a formal optimum certificate; primal best-observed includes all19 completed methods and is descriptive", "results":results}
    output = ROOT / "experiments/analysis/v03/final_population_audit.json"
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"output":str(output),"results":[{"archive":r["archive"],"families":list(r["families"]),"guided_minus_rule":r["whole_population"]["paired_zero_quality_differences_pp"]["guided_minus_rule"]} for r in results]}))
