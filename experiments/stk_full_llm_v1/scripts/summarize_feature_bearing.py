"""Read existing paid TRAIN/VAL outcomes; describe feature-bearing shortlists.

No candidate is selected here. Main freeze is not opened or changed. No TEST,
model, optimizer, graph-feature evaluation, or new labels are used.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path
import sys

from train_context import PROJECT, digest, freeze_json, require
from joint_select import load_banks

sys.path.insert(0, str(PROJECT))
from cipheur.graph_features import FeatureRuleProgram

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, default=ROOT / "analysis/feature_bearing_shortlist")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output_root.resolve()
    train_path, val_path = root / "selection/train_shortlist.json", root / "selection/val_selection.json"
    bank_path, metrics_path = root / "banks/real_cli_12calls.audit2.json", root / "cloud/validation/metrics.json"
    train, val = read(train_path), read(val_path)
    require(val["TRAIN_shortlist_sha256"] == digest(train_path), "VAL refers to a different TRAIN shortlist")
    items, bank_hashes = load_banks([bank_path])
    paid = read(metrics_path)
    require(not paid["failed_jobs"] and paid["all_job_count"] == 560, "Expected all560 paid VALIDATION records")
    by_id = {}
    for row in paid["records"]:
        require(row["split"] == "val", "Non-VAL artifact supplied")
        by_id.setdefault(row.get("program_id"), []).append(row)
    train_rows = {row["program_id"]: row for row in train["candidates"]}
    rows, pools = [], {}
    for group_name in ("witness_joint.b0", "witness_joint.b1", "relations_joint.b0", "relations_joint.b1"):
        group, ranks = train["groups"][group_name], val["groups"][group_name]["ordered_ids"]
        require(set(group["selected_ids"]) == set(ranks), "Need all4 shortlisted candidates with complete VALIDATION coverage")
        feature_bearing = []
        for identifier in ranks:
            item = items[identifier]
            program = FeatureRuleProgram.from_dict(item["program"])
            declared = [name for name, _ in program._expressions]
            referenced = sorted(set(program.code.co_names) & set(declared))
            info, training, runs = val["candidates"][identifier], train_rows[identifier], by_id.get(identifier, [])
            require(info["eligible"] and info["denominator"] == 16 and len(runs) == 16, "Candidate lacks paid full16 VAL coverage")
            row = {"pool": group_name, "program_id": identifier, "VAL_rank_fixed_quality_then_tiebreak": ranks.index(identifier) + 1,
                "main_final_in_this_pool": identifier == val["groups"][group_name]["selected_id"],
                "declared_features": declared, "rule_referenced_features_co_names": referenced,
                "feature_bearing_and_rule_referenced": bool(declared and referenced),
                "VAL_Q_exact": info["VALIDATION_Q"]["exact"], "VAL_Q": info["VALIDATION_Q"]["float"],
                "TRAIN_Q_exact": training["metrics"]["Q"]["exact"], "TRAIN_Q": training["metrics"]["Q"]["float"],
                "TRAIN_G_exact": training["metrics"]["G"]["exact"], "TRAIN_G": training["metrics"]["G"]["float"],
                "TRAIN_passed": training["strict_passed"], "TRAIN_total": 743,
                "TRAIN_C_mean_feature_work_exact": training["metrics"]["C"]["exact"],
                "TRAIN_C_mean_feature_work": training["metrics"]["C"]["float"],
                "VAL_C_mean_feature_work_exact": str(sum((Fraction(run["meter"]["feature_work"]) for run in runs), Fraction()) / 16),
                "VAL_paid_feasible_records": len(runs), "VAL_mean_cpu_seconds": sum(run["cpu_seconds"] for run in runs) / 16,
                "VAL_mean_wall_seconds": sum(run["wall_seconds"] for run in runs) / 16,
                "VAL_head_committed_records": sum(bool(run["head_ever_committed"]) for run in runs),
                "VAL_programme_error_count": sum(run["programme_error_count"] for run in runs),
                "VAL_deadline_soft_overshoot_count": sum(bool(run["deadline_soft_overshoot"]) for run in runs),
                "program": item["program"], "program_content_sha256": item["program_content_sha256"]}
            rows.append(row)
            if row["feature_bearing_and_rule_referenced"]:
                feature_bearing.append(identifier)
        pools[group_name] = {"main_final_id": val["groups"][group_name]["selected_id"],
                            "feature_bearing_rule_referenced_ids": feature_bearing,
                            "all_shortlist_ids": ranks, "new_diagnostic_id_selected": None}
    result = {"version": "paid_feature_bearing_shortlist_completeness_v1", "pools": pools, "records": rows,
        "inputs_sha256": dict(bank_hashes, **{str(path): digest(path) for path in (train_path, val_path, metrics_path)}),
        "representation_warning": "co_names is a static referenced-name set; a conditional branch can skip its feature on an actual root. Presence/reference does not prove information-gate repair, ranking fit gain, or schedule gain.",
        "scope": "existing28 shortlist/560 paid VAL records; table reports the16 candidates in four joint pools only",
        "main_selection_changed": False, "diagnostic_candidate_selected": False, "TEST_read": False,
        "new_model_calls": 0, "new_optimizer_calls": 0, "new_graph_feature_evaluations": 0}
    freeze_json(out / "summary.json", result)
    fields = [key for key in rows[0] if key != "program"]
    csv_path = out / "summary.csv"
    require(not csv_path.exists(), "Preserve existing diagnostic")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: json.dumps(row[key], ensure_ascii=False) if isinstance(row[key], list) else row[key] for key in fields} for row in rows])
    print(json.dumps({"summary": str(out / "summary.json"), "pools": pools,
                      "feature_bearing_rows": [{key: row[key] for key in ("pool", "program_id", "VAL_rank_fixed_quality_then_tiebreak", "VAL_Q", "TRAIN_passed", "TRAIN_C_mean_feature_work", "VAL_C_mean_feature_work_exact")} for row in rows if row["feature_bearing_and_rule_referenced"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
