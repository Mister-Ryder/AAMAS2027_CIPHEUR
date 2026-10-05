"""Predeclared supplemental8 mechanism analysis, separate from the main study.

Preparation opens no results. Analysis requires explicit release and verifies
main and diagnostic bank/protocol hashes separately before exact graph pairing.
No graph, optimizer, synthesis model or conditional oracle is imported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path

from analyze_comparison import (COLOURS, ALIASES, KNOWN, canonical, normalise,
    read, sha, dump, csv_dump, group, exact_fields)
from train_context import DEFAULT_DATA, freeze_json

ROOT = Path(__file__).resolve().parents[1]
REFS = ("degree", "chils", "cp_sat")
TRAIN_CONFIGS = tuple(ALIASES[key] for key in ("A", "W", "E", "J"))
TEST_CONFIGS = tuple(ALIASES[key] for key in ("A", "M", "J", "stress", "W", "E", "MW", "ME"))
IDS = ("nonllm_grammar.local.s6", "nonllm_grammar.local.s7", "nonllm_grammar.residual.s1",
       "relations_joint.r1.b0.s7", "relations_joint.r1.b1.s7", "relations_joint.r2.b0.s6",
       "witness_joint.r1.b0.s6", "witness_joint.r1.b1.s5")
REGISTRATION = {
    "version": "feature_diagnostic8_analysis_v2_pre_results",
    "registered_before_diagnostic_results": True,
    "cohort": list(IDS), "cohort_rule": "all8 fixed TRAIN shortlist feature-bearing and co_names-referenced candidates; no VAL/TEST score filtering",
    "primary_study_unchanged": True, "scope": "supplemental mechanism diagnostic, not primary winner replacement",
    "diagnostic_grids": {"train": {"graphs": 16, "jobs": 256}, "test": {"graphs": 32, "jobs": 512}},
    "budgets": [2, 10], "seeds": [2], "baselines_reused_from_main": list(REFS),
    "hash_policy": "Validate each study against its own bank/protocol, then pair identical source/config/budget/seed2 with equal graph/metadata/execution-module SHA. Never rewrite reference SHA.",
    "quality": "Exact integer microticks; report paired delta seconds and graph-specific relative delta, exact Fraction until display",
    "aggregation": "Perbudget equal config mean within geometry; equal AU/AP within physical date group; equal r000/r001 for TRAIN, r008/r009 for TEST; expose both groups. No CI/pvalue or seed3 inference.",
    "missing": "All paid256/512 jobs accounted for including failures. Missing/nonfeasible quality is NA with full denominator; no failure deletion, zero-fill or candidate exclusion.",
    "cost_and_execution": ["actual totalCPU", "wall", "feature_work", "feature_seconds", "head commits/evaluations", "programme errors", "guard acceptance", "negative construction/repair raw proposals", "overshoot"],
    "information": "Use retained5 + appended3 TRAIN gate receipts; five ofeight acyclic, grammar residual719 highest fit. Gate consistency is potential information access, not score correctness or complete schedule improvement.",
    "figures": {"maximum_groups": 1, "panels": ["TRAINfit with gate symbol", "TRAIN/TEST10s paired delta vs Degree", "TEST10s feature cost versus delta vs CHILS"],
                "cohort": "all8, no favourable example selection", "all_zero_policy": "explicit no-visible-signal panel/table; no fabricated curve",
                "palette": COLOURS, "size_inches": [8.8, 4.0], "font_points": 8, "formats": ["PDF", "PNG300dpi"]},
    "online_LLM": 0, "new_solver_calls": 0, "new_model_calls": 0,
}


def mean(values):
    return sum(values, Fraction()) / len(values) if values else None


def case_key(row):
    return row["split"], row["source"], row["config"], int(row["declared_cpu_seconds"]), row["seed"]


def sources(split):
    reps = ("r000", "r001") if split == "train" else ("r008", "r009")
    return ["CP-" + geometry + "-" + rep for rep in reps for geometry in ("AU", "AP")]


def configs(split):
    return TRAIN_CONFIGS if split == "train" else TEST_CONFIGS


def expected_cases(split):
    return {(split, source, config, budget, 2) for source in sources(split) for config in configs(split) for budget in (2, 10)}


def study_files(protocol_path, bank_path):
    protocol = read(protocol_path)
    if protocol.get("frozen") is not True or protocol["frozen_program_bank_sha256"] != sha(bank_path):
        raise ValueError("Study bank does not match its own immutable protocol")
    bank = {item["id"]: item for item in read(bank_path)["programs"]}
    if set(bank) != set(protocol["final_program_ids"]):
        raise ValueError("Study bank cohort differs from its own freeze")
    return protocol, bank


def load_projection(path, protocol_path, bank_path, split, diagnostic):
    protocol, bank = study_files(protocol_path, bank_path)
    protocol_sha, bank_sha = sha(protocol_path), sha(bank_path)
    obj = read(path)
    if obj.get("version") != "full_schedule_metric_projection_v1":
        raise ValueError("Released input is not the paid metric projection")
    if diagnostic and obj["all_job_count"] != (256 if split == "train" else 512):
        raise ValueError("Diagnostic paid grid is not frozen256/512")
    records, keys = [], set()
    for raw in obj["records"]:
        if raw.get("protocol_sha256") != protocol_sha:
            raise ValueError("Raw result has another study's protocol SHA")
        if raw["method"] == "program" and raw.get("program_bank_sha256") != bank_sha:
            raise ValueError("Raw program result has another study's bank SHA")
        if raw.get("execution_module_sha256") != protocol["execution_script_hashes"]["full_schedule_execution.py"]:
            raise ValueError("Result kernel differs from frozen kernel")
        row = normalise(raw, path, bank, protocol, protocol_sha, bank_sha)
        if row["split"] != split or row["source"] not in sources(split) or row["config"] not in configs(split):
            raise ValueError("Unregistered input source/config/split")
        if int(row["declared_cpu_seconds"]) not in (2, 10):
            raise ValueError("Unregistered budget")
        if diagnostic and (row["program_id"] not in IDS or row["seed"] != 2 or row["method"] != "program"):
            raise ValueError("Extra diagnostic candidate, seed or comparator")
        key = case_key(row) + (row["variant"],)
        if key in keys:
            raise ValueError("Repeated paid output")
        keys.add(key)
        row["study"] = "supplemental8_v2" if diagnostic else "main_frozen8"
        row["metadata_sha256"] = raw.get("metadata_sha256")
        row["feature_work_integer"] = (raw.get("meter") or {}).get("feature_work")
        records.append(row)
    failed = obj["failed_jobs"]
    if diagnostic:
        observed = {row["job_id"] for row in records} | {row["job_id"] for row in failed}
        if len(observed) != obj["all_job_count"]:
            raise ValueError("Paid job coverage is incomplete, even after failures")
        expected = {key + (pid,) for key in expected_cases(split) for pid in IDS}
        failed_keys = set()
        for failure in failed:
            cfg = canonical(failure.get("config_alias") or failure["config"])
            budget = int(failure.get("seconds", failure.get("budget_seconds", 0)))
            failed_keys.add((split, failure["source"], cfg, budget, failure["seed"], failure["program_id"]))
        if keys | failed_keys != expected:
            raise ValueError("Paid diagnostic outcomes do not cover all frozen source/config/head cases")
    return records, failed, {"path": str(path.resolve()), "sha256": sha(path), "all_job_count": obj["all_job_count"],
                            "protocol_path": str(protocol_path.resolve()), "protocol_sha256": protocol_sha,
                            "bank_path": str(bank_path.resolve()), "bank_sha256": bank_sha}


def pairs(diag, references, split):
    lookup = {case_key(row) + (row["variant"],): row for row in diag}
    refs = {case_key(row) + (row["method"],): row for row in references if row["method"] in REFS and row["seed"] == 2}
    answer = []
    for case in sorted(expected_cases(split)):
        for pid in IDS:
            row = lookup.get(case + (pid,))
            for baseline in REFS:
                ref = refs.get(case + (baseline,))
                valid = bool(row and ref and row["complete_feasible"] and ref["complete_feasible"])
                if row and ref:
                    for field in ("input_graph_sha256", "metadata_sha256", "execution_module_sha256"):
                        if not row.get(field) or row[field] != ref.get(field):
                            raise ValueError("Cross-study pair input/runtime differs: " + field)
                result = {"split": split, "source": case[1], "source_group": group(case[1])[0], "geometry": group(case[1])[1],
                    "config": case[2], "declared_cpu_seconds": case[3], "seed": 2, "program_id": pid, "baseline": baseline,
                    "paired_feasible": valid, "status": "complete_pair" if valid else "missing_or_nonfeasible_NA",
                    "candidate_ticks": row["value_ticks"] if row else None, "reference_ticks": ref["value_ticks"] if ref else None,
                    "candidate_protocol_sha256": row.get("protocol_sha256") if row else None,
                    "reference_protocol_sha256": ref.get("protocol_sha256") if ref else None}
                delta = Fraction(row["value_ticks"] - ref["value_ticks"]) if valid else None
                relative = delta / ref["value_ticks"] if valid and ref["value_ticks"] > 0 else None
                result.update(exact_fields("delta_seconds", delta / 1_000_000 if delta is not None else None), exact_fields("relative_delta", relative))
                answer.append(result)
    return answer


def summarise(pair_rows):
    pools = defaultdict(list)
    for row in pair_rows:
        pools[row["split"], row["declared_cpu_seconds"], row["program_id"], row["baseline"]].append(row)
    result = []
    for (split, budget, pid, baseline), rows in sorted(pools.items()):
        groups = defaultdict(list)
        for row in rows:
            groups[row["source_group"]].append(row)
        group_values = {}
        for name, entries in sorted(groups.items()):
            expected = 2 * len(configs(split))
            complete = len(entries) == expected and all(row["paired_feasible"] for row in entries)
            group_values[name] = {"expected_pairs": expected, "feasible_pairs": sum(row["paired_feasible"] for row in entries),
                **exact_fields("delta_seconds", mean([Fraction(row["delta_seconds_exact"]) for row in entries]) if complete else None),
                **exact_fields("relative_delta", mean([Fraction(row["relative_delta_exact"]) for row in entries]) if complete else None)}
        complete = len(group_values) == 2 and all(value["delta_seconds_exact"] is not None for value in group_values.values())
        result.append({"split": split, "budget": budget, "program_id": pid, "baseline": baseline,
            "expected_pairs": len(expected_cases(split)) // 2, "feasible_pairs": sum(row["paired_feasible"] for row in rows),
            "physical_group_count": 2, "physical_groups": group_values,
            **exact_fields("mean_delta_seconds", mean([Fraction(value["delta_seconds_exact"]) for value in group_values.values()]) if complete else None),
            **exact_fields("mean_relative_delta", mean([Fraction(value["relative_delta_exact"]) for value in group_values.values()]) if complete else None)})
    return result


def costs(diag):
    lookup = {case_key(row) + (row["variant"],): row for row in diag}
    output = []
    for split in ("train", "test"):
        for budget in (2, 10):
            for pid in IDS:
                expected = [case for case in expected_cases(split) if case[3] == budget]
                rows = [lookup[case + (pid,)] for case in expected if case + (pid,) in lookup]
                value = {"split": split, "budget": budget, "program_id": pid, "expected_records": len(expected),
                    "recorded_artifacts": len(rows), "feasible_records": sum(row["complete_feasible"] for row in rows),
                    "head_committed_records": sum(bool(row["head_ever_committed"]) for row in rows),
                    "programme_error_count": sum(int(row["programme_error_count"] or 0) for row in rows),
                    "construction_guard_accepted": sum(row["construction_accepted_by_guard"] is True for row in rows),
                    "construction_guard_status_unknown": sum(row["construction_accepted_by_guard"] is None for row in rows),
                    "negative_construction_raw_proposals": sum(row["construction_raw_delta_ticks"] is not None and row["construction_raw_delta_ticks"] < 0 for row in rows),
                    "negative_repair_raw_proposals": sum((row["repair_summary"] or {}).get("negative_raw_gain_count", 0) for row in rows),
                    "repair_guard_accepted": sum((row["repair_summary"] or {}).get("accepted_count", 0) for row in rows),
                    "overshoot_records": sum(bool(row["over_declared_budget"]) for row in rows)}
                for field in ("cpu_seconds", "wall_seconds", "feature_seconds", "head_commits", "head_score_evaluations", "feature_work_integer"):
                    present = [row[field] for row in rows if row.get(field) is not None]
                    value[field + "_available_count"] = len(present)
                    value[field + "_mean"] = sum(present) / len(present) if present else None
                output.append(value)
    return output


def plots(out, summaries, cost_rows, gate, bank):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
    labels = ["N-local6", "N-local7", "N-residual", "R-b0/r1", "R-b1/r1", "R-b0/r2", "W-b0", "W-b1"]
    lookup = {(row["split"], row["budget"], row["program_id"], row["baseline"]): row for row in summaries}
    cost_map = {(row["split"], row["budget"], row["program_id"]): row for row in cost_rows}
    b_signal = any(lookup[split, 10, pid, "degree"]["mean_delta_seconds"] not in (0, None)
                   for pid in IDS for split in ("train", "test"))
    c_signal = any(lookup["test", 10, pid, "chils"]["mean_delta_seconds"] not in (0, None) for pid in IDS)
    fig, axes = plt.subplots(1, 3, figsize=(8.8, 4.0), gridspec_kw={"width_ratios": [1, 1.1, 1.1]})
    for i, pid in enumerate(IDS):
        colour = COLOURS[bank[pid]["arm"]]
        fit = 100 * Fraction(gate[pid]["strict_fit"]["exact"])
        repaired = gate[pid]["representation_consistent"]
        axes[0].scatter(float(fit), i, color=colour if repaired else "white", edgecolors=colour,
                        marker="D" if repaired else "o", s=30, linewidths=1.1)
        for split, offset, marker in (("train", -0.13, "^"), ("test", 0.13, "o")):
            row = lookup[split, 10, pid, "degree"]
            if b_signal and row["mean_delta_seconds"] is not None:
                values = [value["delta_seconds"] for value in row["physical_groups"].values()]
                axes[1].plot([min(values), max(values)], [i + offset, i + offset], color=colour, lw=1)
                axes[1].scatter(row["mean_delta_seconds"], i + offset, s=22, marker=marker, color=colour)
        delta = lookup["test", 10, pid, "chils"]["mean_delta_seconds"]
        cost = cost_map["test", 10, pid]["feature_work_integer_mean"]
        if c_signal and delta is not None and cost is not None:
            axes[2].scatter(cost, delta, color=colour, marker="D" if repaired else "o", s=25)
            axes[2].annotate(str(i + 1), (cost, delta), xytext=(3, 2), textcoords="offset points", fontsize=7)
    axes[0].set(yticks=range(8), yticklabels=[str(i + 1) + " " + label for i, label in enumerate(labels)],
                xlabel="TRAIN strict fit (%)", title="(a) Information gate and fit")
    axes[0].invert_yaxis()
    axes[0].text(.02, -.24, "Filled diamond: acyclic\nOpen circle: residual contradiction", transform=axes[0].transAxes, fontsize=7)
    axes[1].set(yticks=range(8), yticklabels=[], xlabel="Paired reward change (s)", title="(b) vs Degree, 10 CPU s")
    axes[1].invert_yaxis()
    axes[1].axvline(0, color="#666666", lw=.7, linestyle=":")
    axes[1].text(.02, -.24, "Triangle: TRAIN; circle: TEST\nRanges: two physical groups, not CI", transform=axes[1].transAxes, fontsize=7)
    if not b_signal:
        axes[1].text(.5, .5, "No nonzero paired effect\nSee exact table / NA coverage", ha="center", va="center", transform=axes[1].transAxes)
    axes[2].set(xlabel="Mean charged feature work", ylabel="TEST change vs CHILS (s)", title="(c) Measured cost and quality")
    axes[2].axhline(0, color="#666666", lw=.7, linestyle=":")
    if not c_signal:
        axes[2].text(.5, .5, "No nonzero paired effect\nCosts retained in CSV", ha="center", va="center", transform=axes[2].transAxes)
    allcost = [row["feature_work_integer_mean"] for row in cost_rows if row["split"] == "test" and row["budget"] == 10]
    if c_signal and all(value is not None and value > 0 for value in allcost):
        axes[2].set_xscale("log")
    for ax in axes:
        ax.grid(axis="x", color="#E5E5E5", linewidth=.4)
    fig.subplots_adjust(left=.13, right=.985, bottom=.24, top=.88, wspace=.35)
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "feature_mechanism_chain.pdf")
    fig.savefig(out / "feature_mechanism_chain.png", dpi=300)
    plt.close(fig)
    return {"figure": "feature_mechanism_chain", "palette": COLOURS, "cohort": list(IDS),
        "scope": "one8-head scientific multipanel; seed2 only; no fit-to-quality causal claim",
        "TEST_degree_effect_nonzero_count": sum(lookup["test", 10, pid, "degree"]["mean_delta_seconds"] not in (0, None) for pid in IDS),
        "no_synthetic_curve_or_interpolation": True}


def report(path, summaries, cost_rows, gate):
    lookup = {(row["split"], row["budget"], row["program_id"], row["baseline"]): row for row in summaries}
    rows = ["# 辅助特征机制诊断（8个预冻结程序）", "",
        "本报告属于独立补充诊断，不替换主实验最终程序。全部8个已有候选按 TRAIN 固定短名单和静态规则引用纳入，包含5个真实 LLM 候选和3个非 LLM grammar 对照；没有按 VAL/TEST 表现选出其中的优胜者。", "",
        "TRAIN 为16张完整图，TEST 为32张完整图；各使用2/10 CPU秒、固定seed2。TEST 的 r008/r009 两个物理来源组等权，AU/AP与配置属于组内重复测量。本诊断不能被描述成主实验的三seed结果，n=2不提供显著性检验或置信区间。", "",
        "TRAIN 信息门已经证明5/8扩展表示在全部743条既有严格要求上无环。非LLM residual-cover也完成修复，且719/743是本诊断最高拟合率；修复不是LLM或Witness独有。无环只证明这些已冻结关系具备一致表示，不保证评分全部正确，更不保证完整调度收益。部署没有在线LLM或条件oracle。", "",
        "主参考结果与辅助结果分别按各自的 bank/protocol SHA验证，之后仅比较 source/config/budget/seed2及图、元数据、执行内核 SHA一致的记录；没有改写参考协议SHA。", "",
        "## 全8头结果", "",
        "| 程序 | TRAIN信息门 | fit/743 | TRAIN 10s ΔDegree(s) | TEST 2s ΔDegree(s) | TEST 10s ΔDegree(s) | TEST 10s ΔCHILS(s) | TEST 10s ΔCP-SAT(s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    def fmt(value):
        return "NA" if value is None else f"{value:.3f}"
    for pid in IDS:
        values = [lookup[split, budget, pid, ref]["mean_delta_seconds"] for split, budget, ref in
            (("train", 10, "degree"), ("test", 2, "degree"), ("test", 10, "degree"), ("test", 10, "chils"), ("test", 10, "cp_sat"))]
        rows.append("| " + pid + " | " + ("修复" if gate[pid]["representation_consistent"] else "仍有矛盾") + " | " +
                    str(gate[pid]["strict_fit"]["passed"]) + " | " + " | ".join(fmt(value) for value in values) + " |")
    rows += ["", "所有相对差、两来源组分项及精确有理数保存在CSV。NA保留原完整分母，表示缺失或不可行配对，没有填零或删掉候选。", "",
        "## 实际成本与原始失利提案", "",
        "| 程序 | TEST10s 实际CPU均值 | 特征工作均值 | 有head commit的图/32 | 程序错误 | 负构造提案 | 负repair提案 | 超预算图/32 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in cost_rows:
        if row["split"] == "test" and row["budget"] == 10:
            rows.append("| " + row["program_id"] + " | " + fmt(row["cpu_seconds_mean"]) + " | " + fmt(row["feature_work_integer_mean"]) + " | " +
                str(row["head_committed_records"]) + "/32 | " + str(row["programme_error_count"]) + " | " + str(row["negative_construction_raw_proposals"]) + " | " +
                str(row["negative_repair_raw_proposals"]) + " | " + str(row["overshoot_records"]) + "/32 |")
    rows += ["", "CPU时限是软截止；完整可行回退和最终校验可能超时，实际耗时全部报告。Guard保留最终可行收益并记录被拒绝的负提案。负原始提案不能被省略，也不能被混同为最终收益为负。", "",
        "信息门、拟合率、完整收益和成本分别报告，图中的并列关系不是因果链证明。若收益变化为零或不利，保留该结果；补充诊断不会用于重新选择主程序。CHILS只提供可观察的seed/end事件时，不能据此宣称其内部搜索没有进展。", ""]
    path.write_text("\n".join(rows), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--released-formal-results", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_DATA / "perf_dataset_v1/analysis/feature_diagnostic_v2")
    parser.add_argument("--main-train", type=Path)
    parser.add_argument("--main-test", type=Path)
    parser.add_argument("--diagnostic-train", type=Path)
    parser.add_argument("--diagnostic-test", type=Path)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    output, root = args.output_root.resolve(), args.root.resolve()
    if args.prepare:
        if any((args.main_train, args.main_test, args.diagnostic_train, args.diagnostic_test)):
            raise ValueError("Preparation does not open any result input")
        freeze_json(output / "analysis_registration.json", REGISTRATION)
        print(json.dumps({"registration": str(output / "analysis_registration.json"), "sha256": sha(output / "analysis_registration.json"), "TEST_results_read": False}))
        return
    if not args.released_formal_results or not all((args.main_train, args.main_test, args.diagnostic_train, args.diagnostic_test)):
        parser.error("Require root release and all4 explicit paid result projections")
    if read(output / "analysis_registration.json") != REGISTRATION:
        raise ValueError("Pre-result analysis registration changed")
    if (output / "analysis_audit.json").exists():
        raise ValueError("Derived analysis already recorded; do not silently overwrite")
    main_proto, main_bank = root / "protocol.frozen.json", root / "banks/frozen_final8.json"
    diag_proto, diag_bank = root / "protocol.feature_diagnostic8_v2.frozen.json", root / "banks/frozen_feature_diagnostic8_v2.json"
    dp = read(diag_proto)
    if set(dp["final_program_ids"]) != set(IDS) or dp["seeds"] != [2] or dp["main_freeze_hashes"]["protocol.frozen.json"] != sha(main_proto):
        raise ValueError("Supplemental8 freeze not bound to supplied main freeze")
    refs, diag, failures, inputs = [], [], [], []
    for split, mpath, dpath in (("train", args.main_train, args.diagnostic_train), ("test", args.main_test, args.diagnostic_test)):
        mrows, mfailed, mi = load_projection(mpath, main_proto, main_bank, split, False)
        drows, dfailed, di = load_projection(dpath, diag_proto, diag_bank, split, True)
        refs.extend(mrows); diag.extend(drows); failures.extend({"study": "main", "split": split, "paid_failure": item} for item in mfailed)
        failures.extend({"study": "supplemental8_v2", "split": split, "paid_failure": item} for item in dfailed)
        inputs += [mi, di]
    gate_path = root / "analysis/feature_diagnostic_information_gate_v2/information_gate_summary.json"
    gate_obj = read(gate_path)
    if gate_obj["diagnostic_protocol_sha256"] != sha(diag_proto) or gate_obj["diagnostic_bank_sha256"] != sha(diag_bank):
        raise ValueError("Information gate is from another diagnostic freeze")
    gate = {item["program_id"]: item for item in gate_obj["programs"]}
    if set(gate) != set(IDS):
        raise ValueError("Information gate cohort incomplete")
    pair_rows = pairs(diag, refs, "train") + pairs(diag, refs, "test")
    summaries, cost_rows = summarise(pair_rows), costs(diag)
    output.mkdir(parents=True, exist_ok=True)
    csv_dump(output / "paid_diagnostic_records.csv", diag)
    csv_dump(output / "exact_paired_outcomes.csv", pair_rows)
    csv_dump(output / "paired_group_summary.csv", summaries)
    csv_dump(output / "actual_cost_and_proposals.csv", cost_rows)
    csv_dump(output / "TRAIN_information_gate.csv", list(gate.values()))
    dump(output / "paid_failures.json", failures)
    plot_bank = {item["id"]: item for item in read(diag_bank)["programs"]}
    receipt = plots(output / "figures", summaries, cost_rows, gate, plot_bank) if not args.no_plots else {"status": "not_requested"}
    dump(output / "figure_receipt.json", receipt)
    report(output / "报告.md", summaries, cost_rows, gate)
    dump(output / "analysis_audit.json", {"registration_sha256": sha(output / "analysis_registration.json"), "script_sha256": sha(Path(__file__)),
        "inputs": inputs, "information_gate_sha256": sha(gate_path), "all8_retained": True,
        "diagnostic_paid_jobs_expected": 768, "diagnostic_artifacts": len(diag), "paid_failures_retained": len(failures),
        "main_and_diagnostic_hash_validation_separate": True, "reference_SHA_rewritten": False,
        "TEST_selection_calls": 0, "new_solver_calls": 0, "new_LLM_calls": 0, "input_graphs_loaded": 0,
        "statistical_groups": ["r008", "r009"], "seed": 2, "not_main_three_seed_experiment": True})
    print(json.dumps({"report": str(output / "报告.md"), "diagnostic_artifacts": len(diag), "pairs_full_denominator": len(pair_rows), "cohort": list(IDS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
