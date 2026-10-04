"""Read-only CSV input census; no graph, optimizer, labels, or private identifiers."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics


DAY = 86400
WINDOW = 7200


def normalize(value: str) -> str:
    return value.strip().lstrip("\ufeff").strip("'\"").strip()


def legacy_clean(value: str) -> str:
    value = value.strip().lstrip("\ufeff")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


def digest_json(value) -> bytes:
    return sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).digest()


def summarize(values: list[int]) -> dict:
    if not values:
        return {"n": 0, "min": None, "max": None, "mean": None, "median": None, "unique": 0}
    return {"n": len(values), "min": min(values), "max": max(values),
            "mean": statistics.fmean(values), "median": statistics.median(values),
            "unique": len(set(values))}


def counter_json(counter: Counter) -> dict:
    return {str(k): v for k, v in sorted(counter.items(), key=lambda x: str(x[0]))}


def intervals_summary(intervals: list[tuple[int, int]], width: int) -> dict:
    """Half-open link intervals; boundary-touching end does not spill."""
    starts, ends, touches, contained = Counter(), Counter(), Counter(), Counter()
    spills, spill_end_boundary, invalid = 0, 0, 0
    for start, end in intervals:
        if end <= start:
            invalid += 1
            continue
        first, last = start // width, (end - 1) // width
        starts[first] += 1
        ends[last] += 1
        for index in range(first, last + 1):
            touches[index] += 1
        if first == last:
            contained[first] += 1
        else:
            spills += 1
        if end % width == 0:
            spill_end_boundary += 1
    all_indices = sorted(set(starts) | set(ends) | set(touches))
    return {"width_seconds": width, "origin_relative_seconds": 0,
            "membership": "[start,end); starts belong to floor(start/width), exact end boundary is not a spill",
            "spanning_boundary_rows": spills, "end_exact_boundary_rows": spill_end_boundary,
            "nonpositive_intervals": invalid,
            "bins": [{"index": i, "start": i * width, "end": (i + 1) * width,
                      "start_count": starts[i], "end_count": ends[i],
                      "intersecting_count": touches[i], "fully_contained_count": contained[i]}
                     for i in all_indices]}


def profile(path: Path):
    raw = path.read_bytes()
    raw_sha = sha256(raw).hexdigest()
    # Strict decoding: do not silently replace resource labels or times.
    text = raw.decode("gb18030", errors="strict")
    rows = csv.reader(text.splitlines())
    header = next(rows)
    dimensions, missing, placeholder = Counter(), Counter(), Counter()
    changed, unmatched, legacy_diff = Counter(), Counter(), Counter()
    metadata = [Counter() for _ in range(6)]
    grounds, satellites = set(), set()
    raw_grounds, raw_satellites = set(), set()
    ground_load, satellite_load = Counter(), Counter()
    first6, full, raw_full = set(), set(), set()
    sequence = []
    times = [[] for _ in range(4)]
    durations, track_duration, lead, tail = [], [], [], []
    link_intervals, track_intervals = [], []
    errors = Counter()
    n, normalization_changed_rows = 0, 0
    priority_parsed, priority_status = Counter(), Counter()
    for row in rows:
        if not row:
            errors["empty_csv_rows"] += 1
            continue
        n += 1
        dimensions[len(row)] += 1
        if len(row) != 12:
            errors["non_12_column_rows"] += 1
            continue
        clean = tuple(normalize(v) for v in row)
        normalization_changed_rows += any(a != b for a, b in zip(row, clean))
        for i, value in enumerate(row):
            changed[i] += value != clean[i]
            token = value.strip()
            unmatched[i] += bool(token) and ((token.startswith("'") != token.endswith("'")) or
                                             (token.startswith('"') != token.endswith('"')))
            legacy_diff[i] += legacy_clean(value) != clean[i]
            missing[i] += clean[i] == ""
            placeholder[i] += clean[i] == "*"
        raw_grounds.add(legacy_clean(row[0]))
        raw_satellites.add(legacy_clean(row[1]))
        grounds.add(clean[0]); satellites.add(clean[1])
        ground_load[clean[0]] += 1; satellite_load[clean[1]] += 1
        raw_full.add(digest_json(row)); full.add(digest_json(clean))
        for i in range(6):
            metadata[i][clean[6 + i]] += 1
        if not clean[11] or clean[11] == "*":
            priority_parsed[0.0] += 1
            priority_status["missing_or_placeholder_loader_defaults_to_0"] += 1
        else:
            try:
                priority = float(clean[11])
                if not math.isfinite(priority):
                    priority_status["nonfinite_priority"] += 1
                else:
                    priority_parsed[priority] += 1
                    priority_status["numeric"] += 1
            except ValueError:
                priority_parsed[0.0] += 1
                priority_status["nonnumeric_loader_defaults_to_0"] += 1
        try:
            t = tuple(int(clean[i]) for i in (2, 3, 4, 5))
        except ValueError:
            errors["noninteger_time_rows"] += 1
            continue
        canonical = (clean[0], clean[1], *t)
        key = digest_json(canonical)
        sequence.append(key); first6.add(key)
        for target, value in zip(times, t):
            target.append(value)
        start, end, trace_start, trace_end = t
        durations.append(end - start); track_duration.append(trace_end - trace_start)
        lead.append(start - trace_start); tail.append(trace_end - end)
        link_intervals.append((start, end)); track_intervals.append((trace_start, trace_end))
        errors["nonpositive_link_duration"] += end <= start
        errors["nonpositive_track_duration"] += trace_end <= trace_start
        errors["link_not_contained_in_track"] += trace_start > start or end > trace_end
    dataset_sha = sha256(b"".join(sorted(first6))).hexdigest()
    result = {
        "file": path.name, "source_sha256": raw_sha, "bytes": len(raw), "encoding": "gb18030",
        "header": header, "column_count": len(header), "row_count": n,
        "row_column_count_distribution": counter_json(dimensions),
        "resource_counts": {"ground": len(grounds), "satellite": len(satellites),
                            "legacy_clean_ground": len(raw_grounds), "legacy_clean_satellite": len(raw_satellites)},
        "resource_contact_count_distribution": {"ground": counter_json(Counter(ground_load.values())),
                                                "satellite": counter_json(Counter(satellite_load.values()))},
        "normalization": {"rule": "strip whitespace/BOM, strip leading/trailing single/double quote, strip whitespace",
                          "changed_rows": normalization_changed_rows,
                          "changed_cells_by_column": counter_json(changed),
                          "unbalanced_quote_cells_by_column": counter_json(unmatched),
                          "differs_from_legacy_paired_quote_cleaner_by_column": counter_json(legacy_diff),
                          "resource_identifiers_exported": False},
        "missing_cells_by_column": counter_json(missing), "star_placeholder_cells_by_column": counter_json(placeholder),
        "time_basis": {"type": "relative_integer_seconds", "calendar_epoch": None,
                       "day0_origin_seconds": 0, "link_start": summarize(times[0]), "link_end": summarize(times[1]),
                       "trace_start": summarize(times[2]), "trace_end": summarize(times[3]),
                       "interpretation": "day/window indices relative to zero; calendar date not established by these CSVs"},
        "duration_seconds": summarize(durations), "track_duration_seconds": summarize(track_duration),
        "tracking_margin_seconds": {"leading": summarize(lead), "trailing": summarize(tail),
                                    "leading_distribution": counter_json(Counter(lead)),
                                    "trailing_distribution": counter_json(Counter(tail))},
        "duration_value_frequency": counter_json(Counter(durations)),
        "metadata_distributions": {header[i + 6]: counter_json(metadata[i]) for i in range(6)},
        "priority_loader_semantics": {"parsed_distribution": counter_json(priority_parsed), "status": counter_json(priority_status),
                                      "optimization_weight": "link_end - link_start in seconds; priority is metadata, not inherited objective weight"},
        "metadata_quantity_or_cancellation": {"explicit_quantity_field": False, "explicit_cancellation_field": False,
                                             "note": "任务执行日期 is the supplied header; 是否馈电 is not a cancellation flag; do not reinterpret either"},
        "duplicates": {"raw_full_row_duplicate_count": n - len(raw_full),
                       "normalized_full_row_duplicate_count": n - len(full),
                       "normalized_first6_duplicate_count": len(sequence) - len(first6),
                       "normalized_unique_first6_rows": len(first6)},
        "normalized_first6_set_sha256": dataset_sha,
        "normalized_first6_order_sha256": sha256(b"".join(sequence)).hexdigest(),
        "natural_days_link": intervals_summary(link_intervals, DAY),
        "natural_days_tracking": intervals_summary(track_intervals, DAY),
        "two_hour_windows_link": intervals_summary(link_intervals, WINDOW),
        "two_hour_windows_tracking": intervals_summary(track_intervals, WINDOW),
        "errors": counter_json(errors),
    }
    return result, first6, sequence, grounds, satellites


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--legacy-loader", type=Path, default=Path(r"E:\01-Joycecyq\2026-ESWA\DAI2026_SNSD_V51_STABLE\SNSD_V51_FINAL\src\snsd_core\data.py"))
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Refusing to overwrite an existing input profile: " + str(args.out))
    files, sets, sequences, grounds, satellites = {}, {}, {}, {}, {}
    for index in range(1, 7):
        name = "W" + str(index)
        files[name], sets[name], sequences[name], grounds[name], satellites[name] = profile(args.data_dir / (name + ".csv"))
    pairs = []
    for i in range(1, 7):
        for j in range(i + 1, 7):
            a, b = "W" + str(i), "W" + str(j)
            common_prefix = 0
            for left, right in zip(sequences[a], sequences[b]):
                if left != right:
                    break
                common_prefix += 1
            pairs.append({"left": a, "right": b, "intersection_first6_unique_count": len(sets[a] & sets[b]),
                          "left_only_first6_unique_count": len(sets[a] - sets[b]),
                          "right_only_first6_unique_count": len(sets[b] - sets[a]),
                          "left_is_subset": sets[a] <= sets[b],
                          "left_is_ordered_file_prefix": sequences[a] == sequences[b][:len(sequences[a])],
                          "common_ordered_prefix_rows": common_prefix,
                          "ground_intersection_count": len(grounds[a] & grounds[b]),
                          "left_ground_subset": grounds[a] <= grounds[b],
                          "satellite_intersection_count": len(satellites[a] & satellites[b]),
                          "left_satellite_subset": satellites[a] <= satellites[b]})
    report = {"version": "v07_W_series_read_only_input_profile_001",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "complete input-only census; no graphs, optimization, oracle, or TEST results",
              "source_data_directory": str(args.data_dir.resolve()),
              "profiler_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
              "legacy_loader": {"path": str(args.legacy_loader), "sha256": sha256(args.legacy_loader.read_bytes()).hexdigest(),
                                "used_for": "source-read objective/priority semantics; not executed or changed"},
              "private_resource_identifiers_exported": False,
              "identity_comparison": "SHA256 of normalized [ground,satellite,int link_start,int link_end,int trace_start,int trace_end]; all sets and all ordered pairs compared",
              "files": files, "pairwise_relations": pairs,
              "interpretation": {"same_time_horizon": True,
                                 "all_adjacent_normalized_contact_sets_nested": all(p["left_is_subset"] for p in pairs if int(p["right"][1:]) == int(p["left"][1:]) + 1),
                                 "series_is_independent_train_test": False,
                                 "not_evidence_of": ["calendar days/epoch", "real observational provenance", "priority-weighted objective", "preference reversals", "algorithm benefit"]}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.out), "sha256": sha256(args.out.read_bytes()).hexdigest(),
                      "rows": {k: v["row_count"] for k, v in files.items()},
                      "nested": report["interpretation"]["all_adjacent_normalized_contact_sets_nested"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
