"""Exact input-structure analysis; reads frozen contacts, never runs STK or labels.

Default output consists only of two new analysis files in this extension.
Use --stdout-only to reproduce the JSON without writing any files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[1]
ROOT = EXTENSION.parents[1]
MICROSECONDS = 1_000_000
SOURCES = ("CP-AU-r000", "CP-AP-r000", "CP-AU-r001", "CP-AP-r001")
SATELLITE_BASELINE = 150
GROUND_POLICIES = (340, 1200)
SATELLITE_THRESHOLDS = (600, 900, 1200, 1800, 2400, 3600, 5400, 6000, 7200)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seconds(ticks):
    sign = "-" if ticks < 0 else ""
    value = abs(ticks)
    return f"{sign}{value // MICROSECONDS}.{value % MICROSECONDS:06d}"


def quantiles(values):
    ordered = sorted(values)
    if not ordered:
        return {}
    # The exact observed order statistic; no interpolation or time rounding.
    return {str(p): seconds(ordered[int((len(ordered) - 1) * p)])
            for p in (0, .25, .5, .75, .9, .99, 1)}


def pair_record(earlier, later, gap):
    return {
        "satellite_id": earlier["satellite_id"],
        "earlier_contact_id": earlier["contact_id"],
        "later_contact_id": later["contact_id"],
        "earlier_site_id": earlier["site_id"],
        "later_site_id": later["site_id"],
        "earlier_end_tick": earlier["e"],
        "later_start_tick": later["s"],
        "gap_tick": gap,
        "gap_seconds": seconds(gap),
    }


def minimum_record(previous, candidate):
    key = lambda r: (r["gap_tick"], r["earlier_contact_id"], r["later_contact_id"])
    return candidate if previous is None or key(candidate) < key(previous) else previous


def analyze_source(source):
    raw = ROOT / "raw" / source
    input_files = {name: {"relative_path": str((raw / name).relative_to(ROOT)).replace("\\", "/"),
                          "sha256": sha256(raw / name)}
                   for name in ("contacts.csv", "manifest.json", "actual_geometry.json")}
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "success" or manifest.get("formal_dataset") is not True:
        raise RuntimeError(f"{source}: not a successful formal physical opportunity library")
    with (raw / "contacts.csv").open(encoding="utf-8", newline="") as stream:
        contacts = list(csv.DictReader(stream))
    by_satellite, by_site = defaultdict(list), defaultdict(list)
    for row in contacts:
        row["s"], row["e"] = int(row["start_tick"]), int(row["end_tick"])
        if row["scope"] != "complete_horizon" or row["e"] - row["s"] != int(row["duration_tick"]):
            raise RuntimeError(f"{source}: invalid frozen full-window endpoint/duration contract")
        by_satellite[row["satellite_id"]].append(row)
        by_site[row["site_id"]].append(row)

    episodes, inter_episode_gaps, internal_nonoverlap_gaps = [], [], []
    internal_max_pair = None
    independent = {g: {"minimum_pair": None, "candidate_pair_count": 0,
                        "new_edge_counts_by_satellite_seconds": {str(t): 0 for t in SATELLITE_THRESHOLDS}}
                   for g in GROUND_POLICIES}
    cross_site_minimum, same_site_minimum = None, None
    internal_sat150_compatible = 0
    for satellite, rows in by_satellite.items():
        rows.sort(key=lambda r: (r["s"], r["contact_id"]))
        satellite_episodes, current, current_end = [], [], None
        for row in rows:
            # Half-open intervals overlap only when start < current union end.
            if current and row["s"] >= current_end:
                satellite_episodes.append(current)
                current = []
            current.append(row)
            current_end = max(current_end, row["e"]) if len(current) > 1 else row["e"]
        if current:
            satellite_episodes.append(current)
        for a, b in zip(satellite_episodes, satellite_episodes[1:]):
            inter_episode_gaps.append(min(r["s"] for r in b) - max(r["e"] for r in a))
        for episode in satellite_episodes:
            start, end = min(r["s"] for r in episode), max(r["e"] for r in episode)
            episodes.append({
                "satellite_id": satellite, "start_tick": start, "end_tick": end,
                "span_tick": end - start, "span_seconds": seconds(end - start),
                "contact_count": len(episode), "site_count": len({r["site_id"] for r in episode}),
                "actual_overlap_clique": max(r["s"] for r in episode) < min(r["e"] for r in episode),
                "contact_ids": [r["contact_id"] for r in episode],
            })
            for i, earlier in enumerate(episode):
                for later in episode[i + 1:]:
                    gap = later["s"] - earlier["e"]
                    if gap >= 0:
                        internal_nonoverlap_gaps.append(gap)
                        item = pair_record(earlier, later, gap)
                        if internal_max_pair is None or gap > internal_max_pair["gap_tick"]:
                            internal_max_pair = item
                    internal_sat150_compatible += int(gap >= SATELLITE_BASELINE * MICROSECONDS)
        # Exhaust all chronological unordered pairs sharing this satellite.
        for i, earlier in enumerate(rows):
            for later in rows[i + 1:]:
                gap = later["s"] - earlier["e"]
                if gap < SATELLITE_BASELINE * MICROSECONDS:
                    continue  # Already an edge at sat150, including all overlaps.
                item = pair_record(earlier, later, gap)
                if earlier["site_id"] != later["site_id"]:
                    cross_site_minimum = minimum_record(cross_site_minimum, item)
                else:
                    same_site_minimum = minimum_record(same_site_minimum, item)
                for ground_gap, result in independent.items():
                    if earlier["site_id"] == later["site_id"] and gap < ground_gap * MICROSECONDS:
                        continue  # Already a ground-resource edge.
                    result["candidate_pair_count"] += 1
                    result["minimum_pair"] = minimum_record(result["minimum_pair"], item)
                    for threshold in SATELLITE_THRESHOLDS:
                        if gap < threshold * MICROSECONDS:
                            result["new_edge_counts_by_satellite_seconds"][str(threshold)] += 1
    for result in independent.values():
        smallest = result["minimum_pair"]["gap_tick"]
        result["strict_first_new_threshold_tick"] = smallest + 1
        result["strict_first_new_threshold_seconds"] = seconds(smallest + 1)

    # Preserve the previously explored latitude grouping as a rejected candidate.
    # It is NOT the grouping used by the final heterogeneous_ground_v1 experiment.
    per_site = {}
    for site, rows in sorted(by_site.items()):
        rows.sort(key=lambda r: (r["s"], r["contact_id"]))
        additional = 0
        for i, earlier in enumerate(rows):
            for later in rows[i + 1:]:
                gap = later["s"] - earlier["e"]
                if gap >= 1200 * MICROSECONDS:
                    break
                if gap >= 340 * MICROSECONDS:
                    additional += 1
        per_site[site] = {"vertices": len(rows), "new_ground_union_edges_340_to_1200": additional}
    unadopted = {}
    for name, site_ids in {"latitude28": [f"GS{i:02d}" for i in range(1, 7)],
                           "latitude32": [f"GS{i:02d}" for i in range(7, 13)]}.items():
        unadopted[name] = {"site_ids": site_ids,
                           "vertices": sum(per_site[s]["vertices"] for s in site_ids),
                           "new_ground_union_edges_340_to_1200": sum(per_site[s]["new_ground_union_edges_340_to_1200"] for s in site_ids)}
    multi_site = [e for e in episodes if e["site_count"] > 1]
    return {
        "source_id": source, "source_group": contacts[0]["source_group"],
        "epoch_utc": contacts[0]["epoch_utc"], "input_files": input_files,
        "eop_sha256": manifest["eop_sha256"], "contact_count": len(contacts),
        "satellite_count": len(by_satellite), "site_count": len(by_site),
        "episode_count": len(episodes), "multi_site_episode_count": len(multi_site),
        "actual_overlap_nonclique_episode_count": sum(not e["actual_overlap_clique"] for e in episodes),
        "same_episode_nonoverlapping_pair_count": len(internal_nonoverlap_gaps),
        "same_episode_pairs_compatible_at_sat150": internal_sat150_compatible,
        "same_episode_nonoverlap_gap_quantiles_seconds": quantiles(internal_nonoverlap_gaps),
        "max_same_episode_nonoverlap_pair": internal_max_pair,
        "multi_site_episode_span_quantiles_seconds": quantiles([e["span_tick"] for e in multi_site]),
        "max_multi_site_episode": max(multi_site, key=lambda e: e["span_tick"]),
        "inter_episode_gap_quantiles_seconds": quantiles(inter_episode_gaps),
        "minimum_cross_site_gap_above_sat150": cross_site_minimum,
        "minimum_same_site_gap_above_sat150": same_site_minimum,
        "independent_satellite_edge_threshold_by_ground_gap": {str(g): r for g, r in independent.items()},
        "unadopted_latitude_group_candidate_appendix": {"adopted": False, "groups": unadopted, "per_site": per_site},
    }


def markdown(report):
    lines = ["# 卫星资源轴失效的精确输入结构证据", "",
             "本报告只分析已冻结的四库完整可见窗口，不运行 STK、不计算决策标签、不修改原始库或图。"
             "四库只来自 r000/r001 两个 source group，不能当作四个独立来源。", "",
             "对共享卫星的窗口按 `(start_tick, contact_id)` 排序，穷举所有窗口对。令间隔为"
             " `later.start_tick - earlier.end_tick`；排除 sat150 已有边，以及 ground340/1200 已有边。"
             "独立新卫星边要求 `tau_sat_tick > gap_tick`，因此冻结微秒实例中的第一个新阈值是最小间隔加 1 微秒。", "",
             "| 原始库 | 最小独立间隔（秒） | 最大跨站弧段（秒） | 同弧段非重叠最大间隔（秒） |",
             "|---|---:|---:|---:|"]
    for r in report["sources"]:
        lines.append(f"| {r['source_id']} | {r['minimum_cross_site_gap_above_sat150']['gap_seconds']} | "
                     f"{r['max_multi_site_episode']['span_seconds']} | {r['max_same_episode_nonoverlap_pair']['gap_seconds']} |")
    lines += ["", "弧段严格定义为同一卫星的半开窗口最大时间重叠连通组；它不是额外识别或验证的轨道圈次。"
              "同弧段的窗口并非全部实际时间重叠，但其非重叠间隔均小于150秒，故全部在 sat150 已经互斥。"
              "弧段间最小间隔约5392秒，中位数约5610秒；两端跨界窗口不在此完整窗口分析范围中。", "",
              "sat600 至 sat3600 不产生独立新边。sat5400 仅新增163/164/167/167条，sat6000 新增"
              "62633/62690/62575/62554条（AU0/AP0/AU1/AP1）。数值本身不能证明约90分钟是合理的资源周转时间。"
              "没有明确的热恢复、电量恢复或业务独占依据，不应把这样的时间解释为普通切换周转。", "",
              "最终试验采用 heterogeneous_ground_v1 已固定的经度分组：west={88,94,100}°，"
              "east={106,112,118}°，分别包含两个纬度行；保持 sat150。此报告不替代该最终试验的图/证据结果。", "",
              "## 未采纳候选附录", "",
              "此前检查的纬度分组 GS01–06 / GS07–12 **未采纳**。其 ground340→1200 新边数仅用于保留分析过程：", "",
              "| 原始库 | 纬度28°候选新增边 | 纬度32°候选新增边 |", "|---|---:|---:|"]
    for r in report["sources"]:
        groups = r["unadopted_latitude_group_candidate_appendix"]["groups"]
        lines.append(f"| {r['source_id']} | {groups['latitude28']['new_ground_union_edges_340_to_1200']} | "
                     f"{groups['latitude32']['new_ground_union_edges_340_to_1200']} |")
    lines += ["", "输入 SHA-256、端点、最小阈值配对、分位数和计算规则保存在同目录 `satellite_axis_thresholds.json`。"
              "微秒整数用于冻结优化实例，不表示 STK 物理精度达到微秒，也不构成物理误差上界。", "",
              "复现（只读原始库、仅打印结果）：", "", "```powershell",
              "$env:PYTHONIOENCODING = 'utf-8'",
              f"& 'C:/Users/JIA/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' '{str(Path(__file__).resolve()).replace(chr(92), '/')} ' --stdout-only".replace(".py '", ".py'"),
              "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()
    report = {
        "schema_version": "cipheur-input-satellite-axis-thresholds-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_scope": "Frozen full opportunity windows only; no new STK, graphs, labels or schedule experiments.",
        "script_relative_path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "script_sha256": sha256(Path(__file__)),
        "time_contract": {"tick_unit": "microsecond", "all_pair_arithmetic": "signed exact integers",
                          "threshold_comparison": "strict gap_tick < turnaround_tick",
                          "report_seconds": "exact six fractional digits; no coarse rounding"},
        "calculation_rules": {
            "baseline_satellite_seconds": SATELLITE_BASELINE, "ground_policies_seconds": GROUND_POLICIES,
            "pair_order": "(start_tick, contact_id), earlier index < later index",
            "visibility_episode": "Maximal overlap-connected component of half-open windows for one satellite; no independently validated orbit/pass identification.",
            "independent_new_edge": "shared satellite AND gap>=150s AND (different site OR gap>=ground policy); new edge only if gap<new satellite policy",
            "quantile": "Sorted observed order statistic at floor((n-1)*p), without interpolation",
        },
        "scientific_status": "The satellite150-to600 axis is inactive; threshold counts are input structural facts, not evidence-label or scheduling quality results.",
        "final_heterogeneous_grouping": {"extension": "heterogeneous_ground_v1", "adopted": True,
            "west_longitudes_degrees": [88, 94, 100], "west_sites": ["GS01", "GS02", "GS03", "GS07", "GS08", "GS09"],
            "east_longitudes_degrees": [106, 112, 118], "east_sites": ["GS04", "GS05", "GS06", "GS10", "GS11", "GS12"],
            "latitude_group_candidate_adopted": False},
        "sources": [analyze_source(source) for source in SOURCES],
        "interpretation": "A roughly90-minute wait is required before independent satellite edges appear. Without a separately grounded thermal/energy/exclusive-service constraint, this is not justified as ordinary handover turnaround. Timing sensitivity evidence is not a rigorous physical error bound.",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(rendered)
        return
    output = EXTENSION / "analysis"
    json_path, md_path = output / "satellite_axis_thresholds.json", output / "satellite_axis_thresholds.md"
    if json_path.exists() or md_path.exists():
        raise RuntimeError("Analysis outputs already exist; use --stdout-only for read-only reproduction")
    output.mkdir(parents=True, exist_ok=True)
    json_path.write_text(rendered, encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": "success", "sources": len(report["sources"]),
                      "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
