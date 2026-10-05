"""Complete-queue, paired full-schedule analysis; no optimizer is imported.

development requires144 jobs; comparison requires all576.  Registration,
metrics, job identities and recorded source hashes are checked once.  Repeated
AU/AP/config/seed observations are averaged inside the two physical r groups.
No p-values, interpolation, programme selection or implicit failure deletion.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
METHODS = ("llm_witness", "llm_feedback", "grammar_online", "witness_fixed", "witness_base9",
           "degree", "chils_ils", "chils", "cp_sat")
MECHANISMS = METHODS[:5]
RESPONSES = (("A", "W"), ("A", "E"), ("A", "J"), ("W", "J"), ("E", "J"),
             ("A", "M"), ("M", "J"), ("J", "stress"),
             ("W", "ME"), ("E", "MW"), ("ME", "J"), ("MW", "J"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def physical_group(source):
    found = re.search(r"(r\d{3})$", source)
    require(found is not None, "Unknown physical source group")
    return found.group(1)


def mean(values):
    values = list(values)
    return sum(values, Fraction()) / len(values) if values else None


def hierarchy(rows, function):
    """Seed -> config -> AU/AP/source -> r group -> two groups, equal weights."""
    cells = defaultdict(list)
    for row in rows:
        value = function(row)
        if value is None:
            return None  # Missing measurements are not fabricated zero.
        cells[(row["source"], row["config"])].append(Fraction(value))
    sources = defaultdict(list)
    for (source, _), values in cells.items():
        sources[source].append(mean(values))
    groups = defaultdict(list)
    for source, values in sources.items():
        groups[physical_group(source)].append(mean(values))
    return mean(mean(values) for values in groups.values())


def number(value):
    return None if value is None else float(value)


def case_key(row):
    return row["source"], row["config"], row["budget_cpu_seconds"], row["seed"]


def load_complete(stage, input_root, registration_path):
    expected = 144 if stage in ("development", "development_round2") else 576
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    metrics_path, summary_path = input_root / "metrics.json", input_root / "execution_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    require(registration.get("stage") == stage and registration.get("status") == "ready"
            and registration.get("job_count") == expected, "Wrong/unready frozen registration")
    require(summary.get("all_attempted") and summary.get("all_job_count") == expected
            and summary.get("complete_job_count") == expected and summary.get("failed_job_count") == 0
            and summary.get("method_error_or_non_ok_count") == 0,
            "Queue incomplete or method errors: no quality summary generated")
    require(metrics.get("all_job_count") == expected and len(metrics["records"]) == expected
            and not metrics.get("failed_jobs") and metrics.get("method_error_or_non_ok_count") == 0,
            "Incomplete/error metrics: no quality summary generated")
    require(summary.get("metrics_sha256") == sha(metrics_path), "Metrics/summary SHA differs")
    jobs_path = registration_path.parent / registration["jobs_filename"]
    require(sha(jobs_path) == registration["jobs_sha256"] == summary["jobs_sha256"], "Frozen job SHA differs")
    jobs = {job["job_id"]: job for job in
            (json.loads(line) for line in jobs_path.read_text(encoding="utf-8").splitlines() if line.strip())}
    records = metrics["records"]
    require(len(jobs) == expected and len({r["job_id"] for r in records}) == expected
            and {r["job_id"] for r in records} == set(jobs), "Job identities missing/duplicated")
    require(set(registration["methods"]) == set(METHODS), "Method denominator differs")
    graph_map = {(g["source"], g["config"]): g for g in registration["graphs"]}
    identities = defaultdict(set)
    for graph in registration["graphs"]:
        identities[graph["source"]].add((graph["node_mapping_sha256"], graph["weight_ticks_sha256"]))
    require(all(len(values) == 1 for values in identities.values()), "Cross-configuration nodes/rewards differ")
    for row in records:
        job = jobs[row["job_id"]]
        require(row.get("feasible") is True and row.get("execution_status") == "ok", "Non-feasible/non-ok output")
        for key in ("source", "config", "method", "seed", "split", "input_graph_sha256", "metadata_sha256", "bank_sha256"):
            require(row.get(key) == job.get(key), "Output/registration differs: " + key)
        if "controller_config_sha256" in job:
            require(row.get("controller_config_sha256") == job["controller_config_sha256"],"Controller config SHA differs")
        require(row.get("budget_cpu_seconds") == job["seconds"], "Budget differs")
        require(type(row.get("value_ticks")) is int and row["value_ticks"] >= 0, "Noninteger full objective")
        require(type(row.get("cpu_seconds")) in (int, float) and math.isfinite(row["cpu_seconds"]) and row["cpu_seconds"] >= 0,
                "Invalid actual CPU")
        code = job["code_hashes"]
        require(row.get("script_sha256") == code["scripts/benchmark.py"], "Benchmark source differs")
        require(bool(row.get("module_sha256")), "Missing executable-module hash receipt")
        for module, actual in row["module_sha256"].items():
            path = "code/cipheur/online_v2/" + module + ".py"
            require(path in code and code[path] == actual, "Executable module SHA differs: " + module)
        graph = graph_map[(row["source"], row["config"])]
        row["config_alias"] = graph["config_alias"]
        row["physical_group"] = physical_group(row["source"])
    expected_groups = {"r000", "r001"} if stage in ("development", "development_round2") else {"r008", "r009"}
    require({r["physical_group"] for r in records} == expected_groups, "Physical source groups differ")
    require({r["method"] for r in records} == set(METHODS), "Actual method set differs")
    return records, registration, summary, graph_map


def paired_statistics(rows, baseline):
    lookup = {case_key(row): row for row in baseline}
    def difference(row):
        other = lookup[case_key(row)]
        require(row["input_graph_sha256"] == other["input_graph_sha256"], "Unpaired input graph")
        return row["value_ticks"] - other["value_ticks"]
    delta = hierarchy(rows, difference)
    relative = hierarchy(rows, lambda r: Fraction(difference(r) * 100, lookup[case_key(r)]["value_ticks"])
                         if lookup[case_key(r)]["value_ticks"] else None)
    return number(delta / 1_000_000), number(relative)


def table_rows(records):
    output = []
    for budget in sorted({r["budget_cpu_seconds"] for r in records}):
        degree = [r for r in records if r["method"] == "degree" and r["budget_cpu_seconds"] == budget]
        chils = [r for r in records if r["method"] == "chils_ils" and r["budget_cpu_seconds"] == budget]
        for method in METHODS:
            rows = [r for r in records if r["method"] == method and r["budget_cpu_seconds"] == budget]
            d, dpct = paired_statistics(rows, degree)
            c, cpct = paired_statistics(rows, chils)
            exact = hierarchy(rows, lambda r: r["value_ticks"])
            output.append({"method": method, "budget_cpu_seconds": budget, "runs": len(rows),
                           "independent_source_groups": len({r["physical_group"] for r in rows}),
                           "mean_value_ticks_exact": str(exact), "mean_reward_seconds": number(exact / 1_000_000),
                           "paired_delta_degree_seconds": d, "paired_relative_degree_percent": dpct,
                           "paired_delta_chils_p1_seconds": c, "paired_relative_chils_p1_percent": cpct,
                           "mean_actual_cpu_seconds": number(hierarchy(rows, lambda r: r["cpu_seconds"])),
                           "mean_feature_cpu_seconds": number(hierarchy(rows, lambda r: r.get("feature_cpu_seconds"))),
                           "mean_trial_count": number(hierarchy(rows, lambda r: r.get("trial_summary", {}).get("count"))),
                           "mean_soft_cpu_overshoot_seconds": number(hierarchy(rows, lambda r: r.get("soft_cpu_overshoot_seconds"))),
                           "negative_raw_proposals": sum(r.get("trial_summary", {}).get("negative_raw", 0) for r in rows)})
    return output


def response_rows(records, graph_map):
    lookup = {(r["method"], r["source"], r["config_alias"], r["budget_cpu_seconds"], r["seed"]): r for r in records}
    output = []
    aliases = {r["config_alias"] for r in records}
    for before, after in RESPONSES:
        if not {before, after} <= aliases:
            continue
        for budget in sorted({r["budget_cpu_seconds"] for r in records}):
            for method in METHODS:
                rows = [r for r in records if r["method"] == method and r["config_alias"] == before and r["budget_cpu_seconds"] == budget]
                def change(row, who):
                    key = (who, row["source"], after, budget, row["seed"])
                    old = lookup[(who, row["source"], before, budget, row["seed"])]
                    return lookup[key]["value_ticks"] - old["value_ticks"]
                absolute = hierarchy(rows, lambda r: change(r, method))
                versus_degree = hierarchy(rows, lambda r: change(r, method) - change(r, "degree"))
                versus_chils = hierarchy(rows, lambda r: change(r, method) - change(r, "chils_ils"))
                output.append({"method": method, "budget_cpu_seconds": budget, "from_config": before, "to_config": after,
                               "mean_reward_response_seconds": number(absolute / 1_000_000),
                               "paired_response_difference_degree_seconds": number(versus_degree / 1_000_000),
                               "paired_response_difference_chils_p1_seconds": number(versus_chils / 1_000_000),
                               "same_nodes_and_rewards_registered": True,
                               "scope": "Paired cold reoptimization; not a mid-solve change event"})
    return output


def mechanism_rows(records):
    output = []
    for budget in sorted({r["budget_cpu_seconds"] for r in records}):
        for method in MECHANISMS:
            rows = [r for r in records if r["method"] == method and r["budget_cpu_seconds"] == budget]
            average = lambda f: number(hierarchy(rows, f))
            reads = lambda r: sum(r["actual_added_feature_reads"].values()) if "actual_added_feature_reads" in r else None
            output.append({"method": method, "budget_cpu_seconds": budget,
                           "mean_mutations": average(lambda r: r.get("controller", {}).get("mutation_count")),
                           "mean_attempts": average(lambda r: r.get("trial_summary", {}).get("count")),
                           "mean_accepted": average(lambda r: r.get("trial_summary", {}).get("accepted")),
                           "mean_rank_commits": average(lambda r: r.get("trial_summary", {}).get("rank_commits")),
                           "mean_actual_added_feature_reads": average(reads),
                           "mean_negative_raw": average(lambda r: r.get("trial_summary", {}).get("negative_raw")),
                           "mean_operator_gain_seconds": average(lambda r: Fraction(r["stats"]["operator_gain_ticks"], 1_000_000) if "operator_gain_ticks" in r.get("stats", {}) else Fraction()),
                           "mean_rank_stage_gain_seconds": average(lambda r: Fraction(r["stats"]["rank_stage_gain_ticks"], 1_000_000) if "rank_stage_gain_ticks" in r.get("stats", {}) else Fraction()),
                           "mean_patch_common_exchange_gain_seconds": average(lambda r: Fraction(r["stats"]["local_exchange_added_ticks"], 1_000_000) if "local_exchange_added_ticks" in r.get("stats", {}) else Fraction()),
                           "mean_shared_global_exchange_gain_seconds": average(lambda r: Fraction(r["stats"]["shared_exchange_gain_ticks"], 1_000_000) if "shared_exchange_gain_ticks" in r.get("stats", {}) else Fraction()),
                           "cycle_notifications": sum(r.get("controller", {}).get("cycle_notifications", 0) for r in rows),
                           "witness_mutations": sum(r.get("controller", {}).get("witness_mutations", 0) for r in rows),
                           "feature_reads_missing_jobs": sum("actual_added_feature_reads" not in r for r in rows)})
    return output


def csv_save(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value, signed=False):
    return "NA" if value is None else format(value, "+.3f" if signed else ".3f")


def report_text(stage, primary, mechanisms):
    lines = ["# 当前实例内自适应：完整调度结果", "",
             ("开发结果；不得当作独立持出验证。" if stage in ("development", "development_round2") else "正式比较的576任务全部完成后生成。"),
             "所有方法输出完整可行调度，方法错误为0。统计单元为两个r物理来源组；先在组内等权汇总seed、配置和AU/AP，再等权汇总两组。AU/AP、配置和seed不扩大独立n，不作显著性检验。收益单位秒，目标仍使用精确整数微秒。", "",
             "| 方法 | 预算s | 完整收益s | ΔDegree s / % | ΔCHILS p1 s / % | 实际CPU s | 特征CPU s | 提案数 |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in primary:
        lines.append(f"| {row['method']} | {row['budget_cpu_seconds']} | {fmt(row['mean_reward_seconds'])} | "
                     f"{fmt(row['paired_delta_degree_seconds'],True)} / {fmt(row['paired_relative_degree_percent'],True)} | "
                     f"{fmt(row['paired_delta_chils_p1_seconds'],True)} / {fmt(row['paired_relative_chils_p1_percent'],True)} | "
                     f"{fmt(row['mean_actual_cpu_seconds'])} | {fmt(row['mean_feature_cpu_seconds'])} | {fmt(row['mean_trial_count'])} |")
    lines.extend(["", "Δ为同来源、配置、预算和seed的配对差；百分比为组内等权的配对相对差。负结果全部保留。特征CPU仅覆盖重构，证书诊断和控制器成本仍计入总CPU；超预算记录见primary_table.csv。", "",
                  "| 方法 | 预算s | 变异 | 提案/接受 | 排名commit | 实际新增特征读取 | 负提案 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in mechanisms:
        lines.append(f"| {row['method']} | {row['budget_cpu_seconds']} | {fmt(row['mean_mutations'])} | "
                     f"{fmt(row['mean_attempts'])} / {fmt(row['mean_accepted'])} | {fmt(row['mean_rank_commits'])} | "
                     f"{fmt(row['mean_actual_added_feature_reads'])} | {fmt(row['mean_negative_raw'])} |")
    cycles = sum(row["cycle_notifications"] for row in mechanisms)
    lines.extend(["", ("运行记录中的循环触发为0：不能声称部署期间已验证信息冲突引导表示修复。" if cycles == 0 else
                       f"运行记录有{cycles}次循环通知；通知、表示变化和最终质量仍需分别判断。"),
                  "特征读取、变异和排名commit表明参与，不能代替完整收益。算子接受收益包含选点、排名及共用局部exchange；共享搜索收益不能全部归因于LLM。相关代数分解保留在mechanism_table.csv，不能冒充因果消融。", "",
                  "by_config.csv和by_source_group.csv保留所有分层结果。constraint_response.csv报告同节点/奖励下的配置收益变化及相对Degree/CHILS的响应差；约束变严导致的绝对下降不等于算法失败。这是冷启动重新优化，未实现中途热切换。", "",
                  "anytime_points.json仅保存原始incumbent事件；原生方法只有端点时明确标记，未插值。当前定制STK、两个来源组及单seed结果不证明广泛泛化、最优性或录用。", ""])
    return "\n".join(lines)


def main(stage, input_root, registration_path, output_root, enriched=None):
    input_root, registration_path, output_root = map(lambda p: Path(p).resolve(), (input_root, registration_path, output_root))
    records, registration, summary, graph_map = load_complete(stage, input_root, registration_path)
    enrichment_path = Path(enriched) if enriched else input_root / "enriched_metrics.json"
    enrichment_used = False
    if enrichment_path.is_file():
        detail = json.loads(enrichment_path.read_text(encoding="utf-8"))
        require(detail.get("complete") and detail.get("metrics_sha256") == sha(input_root / "metrics.json"), "Incomplete/unbound enrichment")
        by_id = {row["job_id"]: row for row in detail["records"]}
        require(set(by_id) == {row["job_id"] for row in records}, "Enrichment job set differs")
        for row in records:
            values = by_id[row["job_id"]]
            for field in ("actual_added_feature_reads", "feature_operation_counts", "feature_cpu_seconds"):
                row[field] = values[field]
            row["mechanism_enrichment"] = values
        enrichment_used = True
    primary, mechanisms = table_rows(records), mechanism_rows(records)
    config_rows, source_rows = [], []
    for alias in sorted({r["config_alias"] for r in records}):
        config_rows.extend({"config_alias": alias, **r} for r in table_rows([r for r in records if r["config_alias"] == alias]))
    for group in sorted({r["physical_group"] for r in records}):
        source_rows.extend({"physical_group": group, **r} for r in table_rows([r for r in records if r["physical_group"] == group]))
    responses = response_rows(records, graph_map)
    curves = [{"job_id": r["job_id"], "source": r["source"], "method": r["method"], "config_alias": r["config_alias"],
               "budget_cpu_seconds": r["budget_cpu_seconds"], "seed": r["seed"],
               "native_internal_trace_unavailable": r["method"] in ("chils", "chils_ils", "cp_sat"),
               "points": r.get("best_so_far", []), "interpolation": False} for r in records]
    profile = {"stage": stage, "jobs": len(records), "independent_source_groups": 2,
               "all_feasible": True, "method_errors": 0, "metrics_sha256": sha(input_root / "metrics.json"),
               "execution_summary_sha256": sha(input_root / "execution_summary.json"),
               "registration_sha256": sha(registration_path), "jobs_sha256": registration["jobs_sha256"],
               "source_sha256": sha(__file__), "source_scope_hash_checks_passed": True,
               "same_source_nodes_and_rewards_passed": True, "enrichment_used": enrichment_used,
               "primary_table": primary, "mechanism_table": mechanisms,
               "all_negative_results_retained": True, "p_values_computed": False,
               "optimizer_calls": 0, "model_calls": 0}
    output_root.mkdir(parents=True, exist_ok=True)
    for name, rows in (("primary_table", primary), ("mechanism_table", mechanisms),
                       ("by_config", config_rows), ("by_source_group", source_rows), ("constraint_response", responses)):
        csv_save(output_root / (name + ".csv"), rows)
    (output_root / "analysis_profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_root / "anytime_points.json").write_text(json.dumps(curves, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_root / "完整调度比较.md").write_text(report_text(stage, primary, mechanisms), encoding="utf-8")
    print(json.dumps({"stage": stage, "jobs": len(records), "report": str(output_root / "完整调度比较.md")}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("development", "development_round2", "comparison"), required=True)
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--enriched", type=Path)
    args = parser.parse_args()
    main(args.stage, args.input_root or ROOT / "cloud" / args.stage,
         args.registration or ROOT / "registrations" / args.stage / "registration.json",
         args.output_root or ROOT / "reports" / args.stage, args.enriched)
