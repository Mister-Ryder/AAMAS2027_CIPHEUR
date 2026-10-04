"""Analyze only final, independently audited compact V006 TEST assignments.

No optimizer/runtime imports, AST access, TEST selection, or raw archive access.
Exact within-context seed/member means precede source-cluster aggregation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import statistics

try:
    import numpy as np
except ImportError:  # Replay remains possible using only the standard library.
    np = None

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (0.1, 1.0, 5.0)
BOOTSTRAPS = 2000
BOOTSTRAP_SEED = 261004
CONFIG_HASHES = {
    "configs/analysis_v06_001.json": "52331002bdb20535cbeaa3fee727135a36d53a6b3577e76d5a18a4cf54a1ecd1",
    "configs/analysis_refinement_v06_002.json": "f05c32a67f412105c57b91aaedab131f140db1d35423f210d209e990caa79769",
}
POLICY_COHORT_COUNTS = {"joint_W": 4, "quality_W": 4, "quality_R": 4,
                        "quality_O": 4, "published_EoH_DSL_quality": 4,
                        "control_structural": 1, "control_base9": 1, "Degree": 1}
NATIVE_SEEDS = {"CHILS": (1, 2, 3), "CHILS_ILS": (1, 2, 3),
                "M2WIS": (1, 2, 3), "Struction": (1,), "WeightedBR": (1,)}
POPULATION_COUNTS = {"fresh_temporal": 216, "WDP": 25, "UAI_Segmentation": 3,
                     "UAI_Grids_CHILS64": 10, "C3_interval_exploratory": 24,
                     "C3_legacy_exploratory": 24}
TIME_FIELDS = ("standalone_wall_seconds", "standalone_cpu_seconds",
               "native_wall_seconds", "native_cpu_seconds", "policy_wall_seconds",
               "policy_cpu_seconds", "shared_graph_load_wall_seconds",
               "shared_graph_load_cpu_seconds", "work", "search_nodes")
META_FIELDS = ("population", "family", "n", "regime", "profile", "pair_id", "side", "source_cluster")
AUDIT_VERSION = "v06_independent_performance_TEST_audit_001"
AUDITOR_SOURCE_SHA256 = "59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a"
AUDIT_HELPER_SHA256 = {
    "scripts/verify_public_alias_v05.py": "6b349b659bad3acfd3a9e1abbf9046a984f8f66df05068841c1ba8c076aa959a",
    "scripts/verify_matched_llm_v05.py": "52b331fea2214642ac50ffe3996c95a6fb9893320e50df84e1371f8fedae087b",
    "scripts/verify_synthesis_train_v06.py": "941264da65d8aac3ccb9242de75ebff4c7f8cc29eb602e071be11d4e25dc8322",
}
REQUIRED_AUDIT_CHECKS = {
    "complete_preregistered_frame": 1,
    "actual_root_authorized_launch": 1,
    "original_complete_prepared_context_frame": 1,
    "original_execution_no_retry": 1,
    "host_launch_execution_complete_source_and_guard_binding": 1,
    "original_lossless_graph_bytes": 302,
    "complete_frame_including_missing_and_failed": 1,
}
COST_SCOPE = (
    "Cost means are conditional on known measured members and contexts, including measured failed attempts; "
    "they do not share the all-members-success condition of complete quality means. "
    "Unavailable warm initializer costs remain in the common_initializer track; a null warm cost is not zero "
    "and is not an all-request attempted-pipeline cost. Each known warm standalone cost charges the full "
    "initializer plus its own repair; shared execution and graph loading are separately labeled."
)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def exact(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Exact objective must be an integer or rational string")
    return Fraction(value)


def number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("Measured time/work must be numeric or null")
    if not math.isfinite(value) or value < 0:
        raise ValueError("Measured time/work must be finite and nonnegative")
    return float(value)


def target(value):
    value = float(value)
    if value not in TARGETS:
        raise ValueError("Unexpected nominal target")
    return value


def cohort(row):
    """Role-derived frozen metadata, never an outcome-dependent grouping."""
    if row["track"] == "native":
        if row["method"] not in NATIVE_SEEDS:
            raise ValueError("Unknown published native method")
        return "native:" + row["method"]
    if row["track"] == "common_initializer":
        if row["method"] != "CHILS_half" or row["seed"] != 1:
            raise ValueError("Unexpected common initializer identity")
        return "common_initializer:CHILS_half"
    if row["track"] not in ("cold_Degree", "warm_CHILS"):
        raise ValueError("Unknown track")
    name = row.get("analysis_cohort")
    if name not in POLICY_COHORT_COUNTS:
        raise ValueError("Policy needs audited frozen analysis_cohort metadata")
    return name


def cluster(row):
    if row["population"].startswith("fresh_"):
        if not row.get("pair_id"):
            raise ValueError("Fresh temporal endpoints need their frozen pair ID")
        return "pair:" + str(row["pair_id"])
    if not row.get("source_cluster"):
        raise ValueError("Public/C3 inputs need their original source cluster")
    return "source:" + str(row["source_cluster"])


def validate_rows(rows, strict=True):
    seen, contexts, identities = set(), {}, {}
    for r in rows:
        required = {"id", "population", "family", "n", "target", "track", "method", "seed",
                    "success", "returned", "status", "error", "reward_exact", "total_exact"}
        if not required <= r.keys():
            raise ValueError("Compact audited row is missing required fields")
        if type(r["success"]) is not bool or type(r["returned"]) is not bool:
            raise ValueError("Success and returned flags must be booleans")
        if type(r["seed"]) is not int or not isinstance(r["status"], str):
            raise ValueError("Seed and status must retain their audited types")
        if r["success"] and r["error"] is not None:
            raise ValueError("Successful quality cannot carry an execution error")
        r["target"] = target(r["target"])
        k = (r["id"], r["target"], r["track"], r["method"], r["seed"])
        if k in seen:
            raise ValueError("Duplicate requested assignment")
        seen.add(k)
        name = cohort(r)
        cluster(r)
        reward, total = exact(r["reward_exact"]), exact(r["total_exact"])
        if r["success"] != (reward is not None) or (r["success"] and not r["returned"]):
            raise ValueError("Unsuccessful/unreturned rewards must remain null")
        if reward is not None and (reward < 0 or total is None or not 0 <= reward <= total):
            raise ValueError("Successful objective violates exact input-total boundary")
        for field in TIME_FIELDS:
            number(r.get(field))
        meta = tuple(r.get(field) for field in META_FIELDS)
        if r["id"] in contexts and contexts[r["id"]] != meta:
            raise ValueError("Context identity changes across assignments")
        contexts[r["id"]] = meta
        if r["track"] in ("cold_Degree", "warm_CHILS"):
            descriptor = (name, r.get("program_kind"), r.get("program_role"),
                          r.get("authoring_block"), r.get("authoring_arm"),
                          r.get("program_sha256"), r.get("published_winner_origin"))
            if r["method"] in identities and identities[r["method"]] != descriptor:
                raise ValueError("A frozen policy identity changes role/AST/origin")
            identities[r["method"]] = descriptor
            if r["seed"] != 1:
                raise ValueError("Policy deployment must use seed1")
        elif r["track"] == "native" and r["seed"] not in NATIVE_SEEDS[r["method"]]:
            raise ValueError("Unknown native stochastic seed")
    if strict:
        if len(rows) != 52548 or len(contexts) != 302 or len(identities) != 23:
            raise ValueError("Incomplete predeclared 302-context/52548-assignment matrix")
        if Counter(d[0] for d in identities.values()) != POLICY_COHORT_COUNTS:
            raise ValueError("Frozen policy roles are missing or pooled")
        populations = Counter("fresh_temporal" if meta[0].startswith("fresh_") else meta[0]
                              for meta in contexts.values())
        if populations != POPULATION_COUNTS:
            raise ValueError("Population coverage differs from the frozen V003 matrix")
        for context_id in contexts:
            for t in TARGETS:
                expected = {(context_id, t, "native", method, seed)
                            for method, seeds in NATIVE_SEEDS.items() for seed in seeds}
                expected.add((context_id, t, "common_initializer", "CHILS_half", 1))
                expected |= {(context_id, t, track, method, 1)
                             for track in ("cold_Degree", "warm_CHILS") for method in identities}
                if not expected <= seen:
                    raise ValueError("An assigned method/seed/track is missing")
    return identities


def verify_audit_provenance(audit, observed_report_sha256, expected_report_sha256):
    """Bind the root-authorized report bytes and the reviewed mathematical verifier closure."""
    if (not isinstance(expected_report_sha256, str) or len(expected_report_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_report_sha256)):
        raise ValueError("A root-authorized independent audit SHA256 is required")
    if observed_report_sha256 != expected_report_sha256:
        raise ValueError("Independent audit bytes differ from the root-authorized SHA256")
    if audit.get("errors") != 0 or type(audit.get("errors")) is not int:
        raise ValueError("Independent performance audit has not passed")
    if audit.get("version") != AUDIT_VERSION:
        raise ValueError("Unsupported or stale independent performance audit version")
    if type(audit.get("error_details")) is not list or audit["error_details"]:
        raise ValueError("Independent audit must retain an empty error_details list")
    checks, by_kind = audit.get("checks"), audit.get("checks_by_kind")
    if (type(checks) is not int or checks <= 0 or not isinstance(by_kind, dict) or not by_kind
            or any(type(v) is not int or v <= 0 for v in by_kind.values())
            or sum(by_kind.values()) != checks):
        raise ValueError("Independent audit check counts are absent or inconsistent")
    if any(by_kind.get(k) != count for k, count in REQUIRED_AUDIT_CHECKS.items()):
        raise ValueError("Independent audit lacks complete original frame/source checks")
    complete = by_kind.get("terminal_complete_original_batch", 0)
    interrupted = by_kind.get("incomplete_batch_guard_or_error_explicit", 0)
    if complete + interrupted != 1 or complete not in (0, 1) or interrupted not in (0, 1):
        raise ValueError("Independent audit lacks exactly one final batch disposition")
    if complete and (by_kind.get("complete_batch_exact_deployment_protocol_and_successful_exit") != 1
                     or by_kind.get("terminal_status_count_reconstruction") != 1):
        raise ValueError("Complete audit lacks successful-exit and terminal-count proofs")
    if (audit.get("audit_source_sha256") != AUDITOR_SOURCE_SHA256
            or digest(ROOT / "scripts/verify_performance_test_v06.py") != AUDITOR_SOURCE_SHA256):
        raise ValueError("Independent audit source differs from the reviewed verifier")
    if audit.get("independent_helper_sha256") != AUDIT_HELPER_SHA256:
        raise ValueError("Independent audit helper closure differs from the reviewed sources")
    if any(digest(ROOT / name) != expected for name, expected in AUDIT_HELPER_SHA256.items()):
        raise ValueError("Local independent audit helper closure has changed")


def load_audited_rows(audit_path, rows_path, expected_audit_sha256):
    """The production entry barrier binds final compact bytes to a zero-error audit."""
    audit = json.loads(Path(audit_path).read_bytes())
    verify_audit_provenance(audit, digest(audit_path), expected_audit_sha256)
    if audit.get("audited_rows_sha256") != digest(rows_path):
        raise ValueError("Compact rows are not bound to the independent audit")
    archive = audit.get("archive_sha256")
    if not isinstance(archive, str) or len(archive) != 64 or any(c not in "0123456789abcdef" for c in archive):
        raise ValueError("Independent audit must bind the original run archive")
    constants = audit.get("registered_constants", {})
    if constants.get("wall_targets") != [0.1, 1, 5] or constants.get("total_contexts") != 302:
        raise ValueError("Audit is not for the complete frozen V003 matrix")
    if constants.get("total_assignments") != 52548 or constants.get("policy_slots") != 23:
        raise ValueError("Audit has a different assignment/role denominator")
    rows = []
    with Path(rows_path).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    validate_rows(rows, strict=True)
    policy_metadata = audit.get("policies")
    if not isinstance(policy_metadata, list) or len(policy_metadata) != 23:
        raise ValueError("Independent audit must bind the frozen23 policy metadata")
    policy_by_method = {p["method"]: p for p in policy_metadata}
    if len(policy_by_method) != 23 or Counter(p["analysis_cohort"] for p in policy_metadata) != POLICY_COHORT_COUNTS:
        raise ValueError("Independent policy metadata has missing or pooled roles")
    fields = ("analysis_cohort", "program_kind", "program_role", "authoring_block",
              "authoring_arm", "program_sha256", "published_winner_origin")
    for r in rows:
        if r["track"] in ("cold_Degree", "warm_CHILS"):
            if r["method"] not in policy_by_method or any(r.get(k) != policy_by_method[r["method"]].get(k) for k in fields):
                raise ValueError("Compact policy metadata differs from the audited frozen identity")
    return audit, rows


def mean_exact(values):
    values = [v for v in values if v is not None]
    return str(sum(values, Fraction()) / len(values)) if values else None


def context_estimates(rows, by_identity=False):
    """Average requested seeds/role members inside each context before any source mean."""
    groups = defaultdict(list)
    for r in rows:
        name = r["method"] if by_identity else cohort(r)
        groups[(r["id"], r["target"], r["track"], name)].append(r)
    out = []
    for (context_id, t, track, name), members in sorted(groups.items()):
        first = members[0]
        values = [exact(r["reward_exact"]) for r in members]
        available = [v for v in values if v is not None]
        complete = len(available) == len(members)
        totals = {exact(r["total_exact"]) for r in members}
        if len(totals) != 1:
            raise ValueError("Input total changes across the same context")
        record = {"id": context_id, "target": t, "track": track, "estimate": name,
                  **{field: first.get(field) for field in META_FIELDS}, "cluster": cluster(first),
                  "requested_members": len(members),
                  "returned_members": sum(r["returned"] for r in members),
                  "successful_members": len(available), "complete_requested_group": complete,
                  "cost_scope": COST_SCOPE,
                  "complete_mean_reward_exact": mean_exact(values) if complete else None,
                  "available_mean_reward_exact": mean_exact(values),
                  "total_exact": first["total_exact"],
                  "status_counts": dict(sorted(Counter(r["status"] for r in members).items())),
                  "error_counts": dict(sorted(Counter(json.dumps(r["error"], sort_keys=True) for r in members if r["error"] is not None).items())),
                  "member_identities": sorted({r["method"] for r in members}),
                  "analysis_cohort": cohort(first), "program_kind": first.get("program_kind"),
                  "program_role": first.get("program_role"), "authoring_arm": first.get("authoring_arm"),
                  "authoring_blocks": sorted({r["authoring_block"] for r in members if r.get("authoring_block") is not None}),
                  "published_origin_counts": dict(sorted(Counter(r.get("published_winner_origin") for r in members if r.get("published_winner_origin") is not None).items()))}
        for field in TIME_FIELDS:
            measured = [number(r.get(field)) for r in members]
            known = [v for v in measured if v is not None]
            record[field] = statistics.mean(known) if known else None
            record[field + "_defined_members"] = len(known)
        for clock in ("wall", "cpu"):
            pipeline = record["standalone_" + clock + "_seconds"]
            shared = record["shared_graph_load_" + clock + "_seconds"]
            record["standalone_plus_graph_load_" + clock + "_seconds"] = pipeline + shared if pipeline is not None and shared is not None else None
        known_wall = [number(r.get("standalone_wall_seconds")) for r in members if r.get("standalone_wall_seconds") is not None]
        record["known_wall_members"] = len(known_wall)
        record["over_nominal_wall_members"] = sum(v > t for v in known_wall)
        record["over_nominal_wall_fraction"] = record["over_nominal_wall_members"] / len(known_wall) if known_wall else None
        out.append(record)
    return out


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    p = (len(values) - 1) * q
    a, b = math.floor(p), math.ceil(p)
    return values[a] + (values[b] - values[a]) * (p - a)


class ClusterBootstrap:
    """Identical cluster draws for all methods/metrics on the same assigned units."""
    def __init__(self, replicates=BOOTSTRAPS, seed=BOOTSTRAP_SEED):
        self.replicates, self.seed, self.samples = replicates, seed, {}

    def interval(self, units, field, is_exact=False):
        groups = defaultdict(list)
        for r in units:
            value = r.get(field)
            if value is not None:
                value = float(exact(value)) if is_exact else float(value)
            groups[r["cluster"]].append(value)
        keys = tuple(sorted(groups))
        values = [v for group in groups.values() for v in group if v is not None]
        if not keys:
            raise ValueError("Bootstrap needs assigned source clusters")
        sums = [sum(v for v in groups[k] if v is not None) for k in keys]
        counts = [sum(v is not None for v in groups[k]) for k in keys]
        draws = []
        if values and len(keys) == 1:
            draws = [sums[0] / counts[0]] * self.replicates
        elif values:
            if keys not in self.samples:
                rng = random.Random(self.seed)
                samples = []
                for _ in range(self.replicates):
                    multiplicity = Counter(rng.randrange(len(keys)) for _ in keys)
                    samples.append(tuple(multiplicity[i] for i in range(len(keys))))
                self.samples[keys] = np.asarray(samples, dtype=np.int64) if np is not None else samples
            samples = self.samples[keys]
            if np is not None:
                # Same Python-Random draws; vectorization does not introduce a second RNG.
                numerators = np.einsum('ij,j->i', samples, np.asarray(sums, dtype=np.float64), optimize=False)
                denominators = np.einsum('ij,j->i', samples, np.asarray(counts, dtype=np.int64), optimize=False)
                valid = denominators > 0
                draws = (numerators[valid] / denominators[valid]).tolist()
            else:
                for sample in samples:
                    denominator = sum(count * multiplicity for count, multiplicity in zip(counts, sample))
                    if denominator:
                        draws.append(sum(value * multiplicity for value, multiplicity in zip(sums, sample)) / denominator)
        return {"assigned_contexts": len(units), "defined_contexts": len(values),
                "assigned_clusters": len(keys), "defined_clusters": sum(c > 0 for c in counts),
                "mean": statistics.mean(values) if values else None,
                "mean_exact": mean_exact([exact(r.get(field)) for r in units]) if is_exact else None,
                "ci95": [percentile(draws, 0.025), percentile(draws, 0.975)] if draws else [None, None],
                "requested_bootstrap_replicates": self.replicates,
                "defined_bootstrap_replicates": len(draws),
                "interval_scope": "Conditional on defined contexts; missing values remain null. Source intervals are not model-population effects."}


def strata(record, include_population=False):
    p, f = record["population"], record["family"]
    groups = [("population_family", p, f, None, None, None),
              ("population_family_n", p, f, record["n"], None, None)]
    if record.get("regime") is not None or record.get("profile") is not None:
        groups += [("population_family_regime_profile", p, f, None, record.get("regime"), record.get("profile")),
                   ("population_family_n_regime_profile", p, f, record["n"], record.get("regime"), record.get("profile"))]
    if include_population:
        groups += [("population", p, None, None, None, None),
                   ("population_n", p, None, record["n"], None, None)]
    return set(groups)


def summaries(estimates, bootstrap):
    groups = defaultdict(list)
    for r in estimates:
        for s in strata(r):
            groups[(*s, r["track"], r["estimate"], r["target"])].append(r)
    out = []
    for k, units in sorted(groups.items(), key=lambda kv: repr(kv[0])):
        scope, population, family, n, regime, profile, track, name, t = k
        metrics = {field: bootstrap.interval(units, field, is_exact=True)
                   for field in ("complete_mean_reward_exact", "available_mean_reward_exact")}
        for field in ("standalone_wall_seconds", "standalone_cpu_seconds",
                      "standalone_plus_graph_load_wall_seconds", "standalone_plus_graph_load_cpu_seconds",
                      "native_wall_seconds", "native_cpu_seconds", "policy_wall_seconds", "policy_cpu_seconds",
                      "shared_graph_load_wall_seconds", "shared_graph_load_cpu_seconds", "work", "search_nodes",
                      "over_nominal_wall_fraction"):
            metrics[field] = bootstrap.interval(units, field)
        coverage = {field: sum(r[field] for r in units) for field in ("requested_members", "returned_members", "successful_members")}
        out.append({"scope": scope, "population": population, "family": family, "n": n,
                    "regime": regime, "profile": profile, "track": track, "estimate": name,
                    "target": t, "coverage": coverage,
                    "measurement_member_counts": {field: sum(r[field + "_defined_members"] for r in units) for field in TIME_FIELDS},
                    "nominal_wall_overshoot": {field: sum(r[field] for r in units) for field in ("known_wall_members", "over_nominal_wall_members")},
                    "status_counts": dict(sorted(sum((Counter(r["status_counts"]) for r in units), Counter()).items())),
                    "complete_contexts": sum(r["complete_requested_group"] for r in units),
                    "assigned_contexts": len(units), "metrics": metrics, "cost_scope": COST_SCOPE})
    return out


def paired_percent(a, b):
    a, b = exact(a), exact(b)
    return str((a - b) * 100 / b) if a is not None and b is not None and b > 0 else None


def contrasts(estimates, identity_estimates, bootstrap, by_identity=False):
    indexed = {(r["id"], r["target"], r["track"], r["estimate"]): r for r in estimates}
    block_index = {}
    if by_identity:
        for r in estimates:
            blocks = r["authoring_blocks"]
            if len(blocks) == 1 and r["analysis_cohort"] in ("joint_W", "quality_W", "quality_R", "quality_O"):
                k = (r["id"], r["target"], r["track"], blocks[0], r["analysis_cohort"])
                if k in block_index:
                    raise ValueError("Frozen authoring block has multiple identities in one role")
                block_index[k] = r
    native_reference = {}
    # Fixed reference is explicitly the one original CHILS seed1 assignment, not its seed mean.
    for r in identity_estimates:
        if r["track"] == "native" and r["estimate"] == "CHILS_seed1":
            native_reference[(r["id"], r["target"])] = r
    records = []
    def add(a, b, name):
        av = a["complete_mean_reward_exact"]
        bv = b["complete_mean_reward_exact"] if b is not None else None
        records.append({**{k: a.get(k) for k in ("id", "target", "population", "family", "n", "regime", "profile", "cluster")},
                        "track": a["track"], "contrast": name, "first": a["estimate"],
                        "reference": b["estimate"] if b else None,
                        "reference_track": b["track"] if b else None,
                        "analysis_cohort": a["analysis_cohort"],
                        "cost_scope": COST_SCOPE,
                        "authoring_block": a["authoring_blocks"][0] if by_identity and len(a["authoring_blocks"]) == 1 else None,
                        "absolute_reward_difference_exact": str(exact(av) - exact(bv)) if av is not None and bv is not None else None,
                        "percent_gain_exact": paired_percent(av, bv),
                        "wall_difference_seconds": a["standalone_wall_seconds"] - b["standalone_wall_seconds"] if b and a["standalone_wall_seconds"] is not None and b["standalone_wall_seconds"] is not None else None,
                        "cpu_difference_seconds": a["standalone_cpu_seconds"] - b["standalone_cpu_seconds"] if b and a["standalone_cpu_seconds"] is not None and b["standalone_cpu_seconds"] is not None else None})
    for a in estimates:
        if a["track"] != "common_initializer":
            add(a, native_reference.get((a["id"], a["target"])), "versus_fixed_full_CHILS_seed1")
        if a["track"] in ("cold_Degree", "warm_CHILS"):
            add(a, indexed.get((a["id"], a["target"], a["track"], "Degree")), "versus_same_track_Degree")
            comparisons = {"joint_W": ("quality_R", "quality_O", "published_EoH_DSL_quality"),
                           "quality_W": ("quality_R",), "quality_R": ("quality_O",)}
            if by_identity:
                for ref in comparisons.get(a["analysis_cohort"], ()):
                    if ref == "published_EoH_DSL_quality" or len(a["authoring_blocks"]) != 1:
                        continue
                    b = block_index.get((a["id"], a["target"], a["track"], a["authoring_blocks"][0], ref))
                    add(a, b, "within_frozen_block:" + a["analysis_cohort"] + "_minus_" + ref)
            else:
                for ref in comparisons.get(a["estimate"], ()):
                    add(a, indexed.get((a["id"], a["target"], a["track"], ref)), a["estimate"] + "_minus_" + ref)
            if a["track"] == "warm_CHILS":
                add(a, indexed.get((a["id"], a["target"], "cold_Degree", a["estimate"])), "shared_initializer_warm_minus_cold")
    grouped = defaultdict(list)
    for r in records:
        for s in strata(r, include_population=True):
            grouped[(*s, r["track"], r["contrast"], r["first"], r["target"])].append(r)
    summaries_out = []
    for k, units in sorted(grouped.items(), key=lambda kv: repr(kv[0])):
        scope, population, family, n, regime, profile, track, name, first, t = k
        # Raw objectives remain family-specific; only dimensionless gains cross families.
        fields = ("percent_gain_exact", "wall_difference_seconds", "cpu_difference_seconds")
        if family is not None:
            fields += ("absolute_reward_difference_exact",)
        summaries_out.append({"scope": scope, "population": population, "family": family, "n": n,
                              "regime": regime, "profile": profile, "track": track, "contrast": name,
                              "first": first, "target": t,
                              "analysis_cohort": units[0]["analysis_cohort"],
                              "cost_scope": COST_SCOPE,
                              "authoring_block": units[0]["authoring_block"],
                              "metrics": {field: bootstrap.interval(units, field, field.endswith("_exact")) for field in fields}})
    return records, summaries_out


def fixed_reference_estimates(rows):
    reference = [r for r in rows if r["track"] == "native" and r["method"] == "CHILS" and r["seed"] == 1]
    records = context_estimates(reference, by_identity=True)
    for r in records:
        r["estimate"] = "CHILS_seed1"
    return records


def curves(summary_rows):
    groups = defaultdict(list)
    metadata = ("scope", "population", "family", "n", "regime", "profile", "track", "estimate", "contrast", "first", "analysis_cohort", "authoring_block")
    for r in summary_rows:
        group = tuple((k, json.dumps(r[k], sort_keys=True)) for k in metadata if k in r)
        groups[group].append(r)
    output = []
    for group, points in sorted(groups.items(), key=lambda kv: repr(kv[0])):
        points.sort(key=lambda r: r["target"])
        if [p["target"] for p in points] != list(TARGETS):
            raise ValueError("A curve omitted a predeclared target, including null points")
        output.append({**{k: json.loads(v) for k, v in group}, "points": points,
                       "x_scope": "All nominal targets retained; measured standalone CPU/wall are separate point metrics. No interpolated anytime trace."})
    return output


def analyze_rows(rows, strict=True, replicates=BOOTSTRAPS, seed=BOOTSTRAP_SEED):
    validate_rows(rows, strict=strict)
    bootstrap = ClusterBootstrap(replicates, seed)
    role = context_estimates(rows)
    identity = context_estimates(rows, by_identity=True)
    summary = summaries(role, bootstrap)
    identity_summary = summaries(identity, bootstrap)
    paired, paired_summary = contrasts(role, fixed_reference_estimates(rows), bootstrap)
    identity_paired, identity_paired_summary = contrasts(identity, fixed_reference_estimates(rows), bootstrap, by_identity=True)
    return {"context_estimates": role, "identity_context_estimates": identity,
            "role_summaries": summary, "identity_summaries": identity_summary,
            "contrast_contexts": paired, "contrast_summaries": paired_summary,
            "identity_contrast_contexts": identity_paired, "identity_contrast_summaries": identity_paired_summary,
            "role_budget_curves": curves(summary), "identity_budget_curves": curves(identity_summary),
            "contrast_budget_curves": curves(paired_summary),
            "identity_contrast_budget_curves": curves(identity_paired_summary),
            "bootstrap_replicates": replicates, "bootstrap_seed": seed,
            "cost_scope": COST_SCOPE,
            "no_TEST_selection": True, "raw_objectives_never_pooled_across_families": True,
            "no_p_values_or_model_population_claims": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--audit-sha256", required=True,
                        help="Root-authorized SHA256 of the final independent audit report")
    parser.add_argument("--rows", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise ValueError("Preserve original analysis; use a new output directory")
    config_hashes = {name: digest(ROOT / name) for name in CONFIG_HASHES}
    if config_hashes != CONFIG_HASHES:
        raise ValueError("Predeclared analysis scope changed; retain the frozen configuration")
    audit, rows = load_audited_rows(args.audit, args.rows, args.audit_sha256)
    analysis = analyze_rows(rows)
    out.mkdir(parents=True)
    for name in ("context_estimates", "identity_context_estimates", "contrast_contexts", "identity_contrast_contexts"):
        with (out / (name + ".jsonl")).open("x", encoding="utf-8", newline="\n") as stream:
            for row in analysis.pop(name):
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n")
    analysis.update(version="v06_audited_performance_analysis_001", archive_sha256=audit["archive_sha256"],
                    independent_audit_sha256=digest(args.audit), audited_rows_sha256=digest(args.rows),
                    independent_audit_authorization_sha256=args.audit_sha256,
                    registered_constants=audit["registered_constants"], analysis_config_sha256=config_hashes,
                    analysis_source_sha256=digest(__file__), assignments=len(rows))
    analysis["numpy_version"] = np.__version__ if np is not None else None
    with (out / "analysis.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(analysis, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"out": str(out), "analysis_sha256": digest(out / "analysis.json"), "assignments": len(rows)}))


if __name__ == "__main__":
    main()
