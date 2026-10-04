"""Input-only, standard-library C-series profiling; never imports a solver.

Reports aggregates and whole-inventory digests, never resource labels or rows.
The normalization is explicit: trim whitespace and boundary quotes; parse
integer times and encode the first six fields as compact JSON for hashing.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics


DEFAULT_SOURCE = Path(r"E:/01-Joycecyq/2026-AAMAS/data")
DEFAULT_OLD = Path(r"E:/01-Joycecyq/2026-ESWA/DAI2026_SNSD_V51_STABLE/SNSD_V51_FINAL/data/C3.csv")
DEFAULT_OUT = Path("experiments/analysis/v07/input_profiles_c_series_001.json")
INTEGER = re.compile(r"[+-]?\d+\Z")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean(value):
    return value.strip().strip("'\"").strip()


def integer(value):
    if not INTEGER.fullmatch(value):
        raise ValueError("not an integer-time field")
    return int(value)


def row_hash(fields):
    return hashlib.sha256(json.dumps(fields, ensure_ascii=True,
                                     separators=(",", ":")).encode("ascii")).hexdigest()


def inventory_hash(hashes):
    # Fixed-length ASCII hashes plus newlines are an unambiguous inventory.
    h = hashlib.sha256()
    for value in hashes:
        h.update(value.encode("ascii") + b"\n")
    return h.hexdigest()


def summary(values):
    if not values:
        return {"count": 0, "min": None, "median": None, "p95": None,
                "max": None, "distinct": 0}
    ordered = sorted(values)
    return {"count": len(values), "min": ordered[0],
            "median": statistics.median(ordered),
            "p95": ordered[int(.95 * (len(ordered) - 1))],
            "max": ordered[-1], "distinct": len(set(ordered))}


def quote_shape(raw):
    raw = raw.strip()
    left = raw[:1] if raw[:1] in ("'", '"') else "none"
    right = raw[-1:] if raw[-1:] in ("'", '"') else "none"
    return f"left:{left}|right:{right}"


def profile(path):
    counts = Counter()
    column_counts = Counter()
    missing = [0] * 6
    numeric_invalid = [0] * 4
    headers = None
    metadata = [Counter() for _ in range(6)]
    first6_hashes, first4_hashes, whole_row_hashes = [], [], []
    resources = [defaultdict(set), defaultdict(set)]
    quote_shapes = [Counter(), Counter()]
    pairs, records, durations, lead_margins, tail_margins = set(), [], [], [], []
    metadata_date_joint = Counter()
    with path.open("r", encoding="gb18030", errors="strict", newline="") as f:
        reader = csv.reader(f, strict=True)
        headers = next(reader)
        for row in reader:
            counts["rows"] += 1
            column_counts[len(row)] += 1
            normalized = [clean(value) for value in row]
            if len(row) != 12:
                counts["wrong_column_count"] += 1
            for i in range(6):
                if len(row) <= i or not normalized[i]:
                    missing[i] += 1
            for i in range(6):
                metadata[i][normalized[i + 6] if len(row) > i + 6 else ""] += 1
            if len(row) < 6:
                continue
            times, valid = [], True
            for i in range(4):
                try:
                    times.append(integer(normalized[i + 2]))
                except ValueError:
                    numeric_invalid[i] += 1
                    valid = False
            if not valid or not normalized[0] or not normalized[1]:
                continue
            for i in range(2):
                resources[i][normalized[i]].add(row[i].strip())
                quote_shapes[i][quote_shape(row[i])] += 1
            pairs.add((normalized[0], normalized[1]))
            canonical6 = normalized[:2] + times
            first6_hashes.append(row_hash(canonical6))
            first4_hashes.append(row_hash(canonical6[:4]))
            whole_row_hashes.append(row_hash(canonical6 + normalized[6:]))
            st, et, ts, te = times
            dur = et - st
            durations.append(dur)
            lead_margins.append(st - ts)
            tail_margins.append(te - et)
            counts["negative_duration"] += dur < 0
            counts["zero_duration"] += dur == 0
            counts["tracking_contains_link"] += ts <= st <= et <= te
            counts["tracking_nonmonotone"] += te < ts
            records.append((st, et, normalized[0], normalized[1]))
            # Date values are metadata, not extra days inferred from row count.
            metadata_date_joint[(st // 86400, normalized[8] if len(normalized) > 8 else "")] += 1

    min_start = min((r[0] for r in records), default=None)
    max_end = max((r[1] for r in records), default=None)
    min_track = min((st - margin for (st, _, _, _), margin in zip(records, lead_margins)), default=None)
    max_track = max((et + margin for (_, et, _, _), margin in zip(records, tail_margins)), default=None)
    origin = min_start // 86400 * 86400 if min_start is not None else 0
    final_day = max(((r[0] - origin) // 86400 for r in records), default=-1)
    days, windows = [], []
    for day in range(final_day + 1):
        ds, de = origin + day * 86400, origin + (day + 1) * 86400
        own = [r for r in records if ds <= r[0] < de]
        days.append({"day_index": day, "start": ds, "end": de,
                     "contacts_by_start": len(own),
                     "ground_count": len({r[2] for r in own}),
                     "satellite_count": len({r[3] for r in own}),
                     "end_crossing_count": sum(r[1] > de for r in own),
                     "incoming_link_overlap_count": sum(r[0] < ds < r[1] for r in records)})
        for block in range(12):
            ws, we = ds + block * 7200, ds + (block + 1) * 7200
            selected = [r for r in own if ws <= r[0] < we]
            windows.append({"day_index": day, "block_index": block,
                            "start": ws, "end": we, "contacts_by_start": len(selected),
                            "ground_count": len({r[2] for r in selected}),
                            "satellite_count": len({r[3] for r in selected}),
                            "end_crossing_count": sum(r[1] > we for r in selected),
                            "incoming_link_overlap_count": sum(r[0] < ws < r[1] for r in records)})

    extra = []
    for i, values in enumerate(metadata):
        nonempty = {k: v for k, v in values.items() if k}
        # Metadata controls only: never emit resource-label columns 0/1.
        extra.append({"column_index": i + 6, "header": headers[i + 6] if len(headers) > i + 6 else None,
                      "empty_count": values.get("", 0), "nonempty_count": sum(nonempty.values()),
                      "nonempty_distinct": len(nonempty), "star_sentinel_count": values.get("*", 0),
                      "value_counts_if_small": dict(sorted(nonempty.items())) if len(nonempty) <= 32 else None,
                      "numeric_nonempty_count": sum(n for v, n in nonempty.items() if INTEGER.fullmatch(v)),
                      "numeric_summary_distinct_values": summary([int(v) for v in nonempty if INTEGER.fullmatch(v)])})

    result = {
        "file": path.name, "path": str(path), "sha256": digest(path), "bytes": path.stat().st_size,
        "encoding": "gb18030_strict", "header": headers,
        "row_count": counts["rows"], "valid_required_rows": len(first6_hashes),
        "column_count_distribution": dict(sorted(column_counts.items())),
        "required_missing_counts": missing, "integer_time_invalid_counts": numeric_invalid,
        "wrong_column_count": counts["wrong_column_count"],
        "ground_count": len(resources[0]), "satellite_count": len(resources[1]),
        "ground_satellite_pair_count": len(pairs),
        "resource_normalization": [
            {"column_index": i, "raw_label_count": len({v for variants in resources[i].values() for v in variants}),
             "normalized_label_count": len(resources[i]),
             "normalized_labels_with_multiple_raw_variants": sum(len(v) > 1 for v in resources[i].values()),
             "boundary_quote_shape_counts": dict(sorted(quote_shapes[i].items()))} for i in range(2)],
        "time": {"basis": "integer_seconds", "origin": origin, "min_link_start": min_start,
                 "max_link_end": max_end, "link_span_seconds": None if min_start is None else max_end - min_start,
                 "link_span_days": None if min_start is None else (max_end - min_start) / 86400,
                 "min_tracking_start": min_track, "max_tracking_end": max_track},
        "duration_seconds": summary(durations),
        "objective_interpretation": "inherited_loader_weight_equals_link_duration_not_an_independent_CSV_weight_column",
        "negative_duration_count": counts["negative_duration"], "zero_duration_count": counts["zero_duration"],
        "tracking_contains_link_count": counts["tracking_contains_link"],
        "tracking_nonmonotone_count": counts["tracking_nonmonotone"],
        "tracking_lead_seconds": summary(lead_margins), "tracking_tail_seconds": summary(tail_margins),
        "keys": {
            "first6_unique_count": len(set(first6_hashes)),
            "first6_duplicate_excess": len(first6_hashes) - len(set(first6_hashes)),
            "first4_unique_count": len(set(first4_hashes)),
            "first4_duplicate_excess": len(first4_hashes) - len(set(first4_hashes)),
            "normalized_full_row_duplicate_excess": len(whole_row_hashes) - len(set(whole_row_hashes)),
            "ordered_first6_inventory_sha256": inventory_hash(first6_hashes),
            "sorted_first6_multiset_sha256": inventory_hash(sorted(first6_hashes))},
        "metadata": extra,
        "execution_date_vs_start_day": [{"start_day_absolute": d, "metadata_execution_date": value, "rows": n}
                                              for (d, value), n in sorted(metadata_date_joint.items())],
        "natural_days": days, "two_hour_windows": windows,
        "two_hour_count_summary": summary([r["contacts_by_start"] for r in windows]),
        "two_hour_end_crossing_summary": summary([r["end_crossing_count"] for r in windows]),
    }
    return result, first6_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--old-c3", type=Path, default=DEFAULT_OLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output exists; choose a new path to preserve previous profiling evidence")
    results, ordered = [], []
    for index in range(1, 7):
        item, hashes = profile(args.source_dir / f"C{index}.csv")
        results.append(item); ordered.append(hashes)
    nested = []
    for i in range(6):
        for j in range(i + 1, 6):
            earlier, later = Counter(ordered[i]), Counter(ordered[j])
            shared = sum(min(n, later.get(h, 0)) for h, n in earlier.items())
            nested.append({"earlier": results[i]["file"], "later": results[j]["file"],
                           "earlier_rows": len(ordered[i]), "later_rows": len(ordered[j]),
                           "shared_normalized_first6_occurrences": shared,
                           "earlier_only_occurrences": len(ordered[i]) - shared,
                           "later_only_occurrences": len(ordered[j]) - shared,
                           "earlier_multiset_contained": all(later[h] >= n for h, n in earlier.items()),
                           "ordered_prefix_equal": ordered[j][:len(ordered[i])] == ordered[i]})
    old = {"path": str(args.old_c3), "exists": args.old_c3.is_file(), "sha256": None,
           "byte_sha256_equal_new_C3": None}
    if old["exists"]:
        old["sha256"] = digest(args.old_c3)
        old["byte_sha256_equal_new_C3"] = old["sha256"] == results[2]["sha256"]
        old_profile, old_hashes = profile(args.old_c3)
        old["normalized_first6_order_equal_new_C3"] = old_hashes == ordered[2]
        old["row_count"] = old_profile["row_count"]
    report = {
        "version": "v07_C_series_input_profiles_001", "profile_scope": "input_only_no_optimizer_or_oracle",
        "script_sha256": digest(Path(__file__)), "resource_labels_or_contact_rows_published": False,
        "normalization": "whitespace_strip_then_all_boundary_single_double_quote_strip_then_whitespace_strip; integral_times_canonical_int; compact_ASCII_JSON_first6_SHA256",
        "hash_scope": "First6 includes resource identity plus link/track integer times; only aggregate hashes published",
        "p95_definition": "sorted_value_at_floor_0p95_times_n_minus_1",
        "window_scope": "half_open_start_assignment; full_end_retained; incoming_link_overlap_not_implicitly_committed",
        "profiles": results, "nested_first6_multiset_comparisons": nested, "old_C3_comparison": old,
        "schema_interpretation": {
            "cancellation_flag_present": False, "execution_count_present": False,
            "column_6": "whether_feeder_link_not_cancellation", "column_7": "maximum_elevation",
            "column_8": "task_execution_date_not_execution_count", "column_9": "orbit_revolution",
            "column_10": "ascending_descending_orbit_flag", "column_11": "priority",
            "metadata_filtering_performed": False},
        "conclusion": {
            "all_15_earlier_multisets_contained": all(x["earlier_multiset_contained"] for x in nested),
            "all_15_ordered_prefixes_equal": all(x["ordered_prefix_equal"] for x in nested),
            "C_file_number_is_not_day_count": True,
            "C1_TRAIN_C6_TEST_source_contact_overlap": nested[4]["shared_normalized_first6_occurrences"],
            "recommended_source": "C6_canonical_full_input_for_explicit_chronological_or_source_split_not_file_index_split",
            "future_independence_or_structure_recurrence_proven": False}
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "sha256": digest(args.out),
                      "rows": [r["row_count"] for r in results],
                      "all_nested": report["conclusion"]["all_15_earlier_multisets_contained"],
                      "old_C3_equal": old["byte_sha256_equal_new_C3"]}))


if __name__ == "__main__":
    main()
