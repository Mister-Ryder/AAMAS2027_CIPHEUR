"""Read-only, complete-denominator comparison of two TRAIN development rounds.

No solver, model, historical TEST outcome, or programme selection is imported.
The existing complete-queue gate checks each independently frozen runtime.
Enrichment is joined only to the exact metrics/raw-output receipts it describes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal
from fractions import Fraction
import json
import math
from pathlib import Path

from analyze_results import METHODS, ROOT, hierarchy, load_complete, require, sha


IDENTITY = ("job_id", "source", "config", "method", "seed", "budget_cpu_seconds")
EXPECTED_SOURCES = {"CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001"}


def pair_key(row):
    return (row["source"], row["config"], row["budget_cpu_seconds"], row["seed"], row["method"])


def load_round(stage, input_root, registration_path):
    records, registration, summary, _ = load_complete(stage, input_root, registration_path)
    enriched_path = input_root / "enriched_metrics.json"
    enriched = json.loads(enriched_path.read_text(encoding="utf-8"))
    require(enriched.get("complete") is True and not enriched.get("errors")
            and enriched.get("all_job_count") == 144 and len(enriched.get("records", [])) == 144,
            "Incomplete/error enrichment: no paired report generated")
    require(enriched.get("metrics_sha256") == summary["metrics_sha256"]
            and enriched.get("execution_summary_sha256") == sha(input_root / "execution_summary.json"),
            "Enrichment belongs to different metrics/summary")
    lookup = {row["job_id"]: row for row in enriched["records"]}
    require(len(lookup) == 144 and set(lookup) == {r["job_id"] for r in records},
            "Enrichment job identities missing/duplicated")
    merged = []
    for row in records:
        extra = lookup[row["job_id"]]
        require(all(row.get(k) == extra.get(k) for k in IDENTITY), "Enrichment identity differs")
        require(extra.get("raw_output_sha256") == row.get("output_sha256"),
                "Enrichment/raw-output SHA differs")
        require(extra.get("total_cpu_seconds") == row["cpu_seconds"], "Enrichment actual CPU differs")
        require(type(row.get("seed_value_ticks")) is int, "Missing integer common seed value")
        require(row["split"] == "train" and row["seed"] == 2 and row["budget_cpu_seconds"] == 10,
                "Development split/seed/budget differs")
        for key in ("feature_cpu_seconds", "trial_cpu_seconds", "scoring_cpu_seconds"):
            value = extra.get(key)
            require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                    "Missing/invalid enriched cost: " + key)
        for key in ("actual_added_feature_read_count", "program_hash_updates_created",
                    "representation_hash_updates_created"):
            require(type(extra.get(key)) is int and extra[key] >= 0, "Missing/invalid count: " + key)
        require(extra["actual_added_feature_read_count"] == sum(extra["actual_added_feature_reads"].values()),
                "Actual added-feature read total differs")
        merged.append({**row, **extra})
    require({r["source"] for r in merged} == EXPECTED_SOURCES, "TRAIN source denominator differs")
    require({r["config_alias"] for r in merged} == {"A", "W", "E", "J"}, "TRAIN configuration denominator differs")
    require(Counter(r["method"] for r in merged) == Counter({m: 16 for m in METHODS}),
            "Every method must cover all sixteen TRAIN graphs")
    require(len({pair_key(r) for r in merged}) == 144, "Duplicate paired observation")
    return merged, registration, summary


def gain_cpu(row):
    """Improvement over common feasible seed / actual charged CPU, in seconds/s."""
    return (Fraction(row["value_ticks"] - row["seed_value_ticks"], 1_000_000)
            / Fraction(row["cpu_seconds"])) if row["cpu_seconds"] > 0 else None


def mutations(row):
    # Native/CP controller counters are unobserved, not fabricated zero.
    return row.get("controller", {}).get("mutation_count")


def seconds_text(ticks):
    return format(Decimal(ticks) / Decimal(1_000_000), ".6f")


def make_pairs(first, second):
    left, right = {pair_key(r): r for r in first}, {pair_key(r): r for r in second}
    require(set(left) == set(right) and len(left) == 144, "Two rounds do not have the same 144 cases")
    output = []
    for key in sorted(left):
        a, b = left[key], right[key]
        require(all(a[k] == b[k] for k in ("input_graph_sha256", "metadata_sha256", "seed_value_ticks", "config_alias")),
                "Paired rounds differ in graph, metadata, common seed, or configuration")
        delta = b["value_ticks"] - a["value_ticks"]
        row = {"source": a["source"], "physical_group": a["physical_group"], "config": a["config"],
               "config_alias": a["config_alias"], "budget_cpu_seconds": a["budget_cpu_seconds"],
               "seed": a["seed"], "method": a["method"], "r1_job_id": a["job_id"], "r2_job_id": b["job_id"],
               "input_graph_sha256": a["input_graph_sha256"], "metadata_sha256": a["metadata_sha256"],
               "seed_value_ticks": a["seed_value_ticks"], "r1_value_ticks": a["value_ticks"],
               "r2_value_ticks": b["value_ticks"], "delta_value_ticks": delta,
               "r1_reward_seconds_exact": seconds_text(a["value_ticks"]),
               "r2_reward_seconds_exact": seconds_text(b["value_ticks"]),
               "delta_reward_seconds_exact": seconds_text(delta),
               "paired_result": "win" if delta > 0 else "loss" if delta < 0 else "tie"}
        values = {
            "gain_ticks": lambda r: r["value_ticks"] - r["seed_value_ticks"],
            "gain_seconds_per_actual_cpu_second": gain_cpu,
            "actual_cpu_seconds": lambda r: r["cpu_seconds"],
            "feature_cpu_seconds": lambda r: r["feature_cpu_seconds"],
            "scoring_cpu_seconds": lambda r: r["scoring_cpu_seconds"],
            "trial_cpu_seconds": lambda r: r["trial_cpu_seconds"],
            "trial_count": lambda r: r["trial_summary"]["count"],
            "mutation_count": mutations,
            "actual_added_feature_read_count": lambda r: r["actual_added_feature_read_count"],
            "negative_raw_proposal_count": lambda r: r["trial_summary"]["negative_raw"],
            "accepted_trial_count": lambda r: r["trial_summary"]["accepted"],
            "rank_commit_count": lambda r: r["trial_summary"]["rank_commits"],
            "program_hash_updates_created": lambda r: r["program_hash_updates_created"],
            "representation_hash_updates_created": lambda r: r["representation_hash_updates_created"],
            "soft_cpu_overshoot_seconds": lambda r: r.get("soft_cpu_overshoot_seconds"),
        }
        for name, getter in values.items():
            av, bv = getter(a), getter(b)
            for prefix, value in (("r1_", av), ("r2_", bv), ("delta_", None if av is None or bv is None else bv - av)):
                row[prefix + name] = float(value) if isinstance(value, Fraction) else value
        for prefix, original in (("r1_", a), ("r2_", b)):
            row[prefix + "trial_status_counts"] = json.dumps(original["trial_summary"]["status_counts"], sort_keys=True)
            row[prefix + "controller_config_sha256"] = original.get("controller_config_sha256")
            row[prefix + "bank_sha256"] = original.get("bank_sha256")
            row[prefix + "raw_output_sha256"] = original["raw_output_sha256"]
        output.append(row)
    return output


def average(rows, function):
    value = hierarchy(rows, function)
    return None if value is None else float(value)


def fmt(value, signed=False):
    return "NA" if value is None else format(value, "+.3f" if signed else ".3f")


def report(first, second, pairs, inputs):
    lines = ["# 两轮当前实例内在线优化：TRAIN开发配对比较", "",
             "两轮各144/144任务均通过既有注册、来源SHA、完整性、完整调度可行性与方法无错误门，全部九种方法保留；未按收益或优劣删行。每种方法比较相同16图、CPU预算10秒、seed=2。", "",
             "本报告仅使用两轮TRAIN开发投影与绑定的只读成本投影，不读取TEST，也不启动求解或LLM。四来源×四配置是重复观测，独立物理来源组仅r000/r001两个；先在各组内等权汇总AU/AP及A/W/E/J，再等权汇总两组。不提供显著性检验或独立样本扩张。", "",
             "| 方法 | R1完整收益s | R2完整收益s | R2−R1 s | 胜/平/负(16) | R1增益/CPU | R2增益/CPU | R1/R2实际CPU s |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for method in METHODS:
        a = [r for r in first if r["method"] == method]
        b = [r for r in second if r["method"] == method]
        p = [r for r in pairs if r["method"] == method]
        counts = Counter(r["paired_result"] for r in p)
        lines.append(f"| {method} | {fmt(average(a,lambda r: Fraction(r['value_ticks'],1_000_000)))} | "
                     f"{fmt(average(b,lambda r: Fraction(r['value_ticks'],1_000_000)))} | "
                     f"{fmt(average(p,lambda r: Fraction(r['delta_value_ticks'],1_000_000)),True)} | "
                     f"{counts['win']}/{counts['tie']}/{counts['loss']} | {fmt(average(a,gain_cpu))} | "
                     f"{fmt(average(b,gain_cpu))} | {fmt(average(a,lambda r:r['cpu_seconds']))}/{fmt(average(b,lambda r:r['cpu_seconds']))} |")
    lines += ["", "收益差使用原始整数微秒精确相减，CSV保留整数与六位小数秒。增益/CPU定义为(最终完整收益−共同可行初始收益)/实际总CPU，并非总收益/CPU。实际CPU包含加载、共同seed、控制器及局部证书；原生方法包含子进程CPU，软超时不删行。", "",
              "| 方法 | R1/R2特征CPU s | R1/R2提案数 | R1/R2变异数 | R1/R2实际新增特征读取 | R1/R2负原始提案数 |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    costs = (lambda r:r["feature_cpu_seconds"], lambda r:r["trial_summary"]["count"], mutations,
             lambda r:r["actual_added_feature_read_count"], lambda r:r["trial_summary"]["negative_raw"])
    for method in METHODS:
        a, b = [r for r in first if r["method"] == method], [r for r in second if r["method"] == method]
        lines.append("| " + method + " | " + " | ".join(fmt(average(a,f))+"/"+fmt(average(b,f)) for f in costs) + " |")
    lines += ["", "特征CPU计时覆盖重构阶段的特征计算，诊断特征与控制器成本仍计入实际总CPU；没有单独控制器CPU计时，不能用总CPU减特征CPU伪造精确控制成本。新增特征读取是实际库字段访问次数，不等于成功修复信息，也不等于LLM在线调用。原生CHILS/CP-SAT提案计数0表示未走本框架的patch提案接口，不能解释为没有搜索；其控制器变异未观测，记NA。所有失败/截止局部提案的状态计数与原始负提案保留在CSV。", "",
              "第二轮同时调整离线LLM配方/控制器策略，并包含表示语义隔离等工程修正。该配对差是整轮系统改变的开发结果，不能单独归因于LLM或其中一个修正。更多变异、特征读取或表示hash变化不能证明精确信息矛盾已修复；结构信息修复也不自动保证评分更正确或完整调度收益更高。本文不新增quotient/证书评估，不以这些计数冒充信息修复证明。", "",
              "当前比较是对固定配置分别冷启动重优化；不是运行中约束突变或warm-start实验。在线优化不调用LLM，LLM成本在离线生成记录中另行核算。TRAIN反馈后的第二轮结果仍属开发证据，不是独立持出有效性结论。", "",
              "绑定的输入文件：", ""]
    for label, path in inputs:
        lines.append(f"- {label}: `{path.resolve().as_posix()}`；SHA256 `{sha(path)}`。")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round1-root", type=Path, default=ROOT / "cloud/development")
    parser.add_argument("--round2-root", type=Path, default=ROOT / "cloud/development_round2")
    parser.add_argument("--round1-registration", type=Path, default=ROOT / "registrations/development/registration.json")
    parser.add_argument("--round2-registration", type=Path, default=ROOT / "registrations/development_round2/registration.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "reports/development_round2")
    args = parser.parse_args()
    # No output directory or completion artifact is created before both gates pass.
    first, _, _ = load_round("development", args.round1_root, args.round1_registration)
    second, _, _ = load_round("development_round2", args.round2_root, args.round2_registration)
    pairs = make_pairs(first, second)
    inputs = [("R1注册", args.round1_registration), ("R2注册", args.round2_registration)]
    for label, root in (("R1", args.round1_root), ("R2", args.round2_root)):
        inputs += [(label+" "+name, root/name) for name in ("metrics.json", "execution_summary.json", "enriched_metrics.json")]
    text = report(first, second, pairs, inputs)
    report_path, csv_path = args.output_root / "两轮比较.md", args.output_root / "paired_round_deltas.csv"
    require(not report_path.exists() and not csv_path.exists(), "Refusing to overwrite prior comparison artifacts")
    args.output_root.mkdir(parents=True, exist_ok=True)
    with csv_path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)
    with report_path.open("x", encoding="utf-8", newline="") as handle:
        handle.write(text)
    print(json.dumps({"status":"complete", "paired_cases":len(pairs), "methods":len(METHODS),
                      "report":str(report_path), "csv":str(csv_path), "optimizer_calls":0, "model_calls":0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
