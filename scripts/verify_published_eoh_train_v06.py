"""Independent EoH TRAIN trace/fitness audit after the entire final freeze.

Reuses only byte-pinned independent verifier mathematics. No production
assessor, repair kernel, scorer, oracle, population selector or TEST is run.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import verify_published_eoh_authoring_v06 as authors
from scripts import verify_refinement_train_v06 as r2_math
from scripts import verify_synthesis_train_v06 as math_reference
from scripts.verify_matched_llm_v05 import FeatureView, boundary, canonical, normalized_program
from scripts.verify_public_alias_v05 import view, graph_digest, exact_alpha

R2_MATH_SHA = "1e98e3eb84238a4999c026f5d081eec97fe147693383e8e1dd0470d505c3ef48"
R1_MATH_SHA = "941264da65d8aac3ccb9242de75ebff4c7f8cc29eb602e071be11d4e25dc8322"
ALIAS_SHA = "7028a303b4961e9e4a40646d05434d1f5cf4337be87fbd8ccad82b0669fbcbbb"
CLARIFICATION_SHA = "49ca3731c7a1a082c019feb8b8f4c53dc4e453a9a971dda3a458836d9f018457"
FAILED_ARCHIVE_SHA = "a857776f005c919b18615b40ce3a2b5fd18ab35474f92728d52b1c22e0dea3f2"
CAPSULE_SHA = "06373247ed2a7641283ceb3fe8655186fae623f0b417da1c955a90bfaf83da4a"
load, digest = authors.load, authors.digest
feasible, value = math_reference.feasible, math_reference.exact_value


def partial_trace_verifier(namespace):
    path = ROOT / "scripts/verify_refinement_train_v06.py"
    if digest(path) != R2_MATH_SHA:
        raise ValueError("Original independently verified R2 trace mathematics changed")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "audit")
    fn = next(n for n in outer.body if isinstance(n, ast.FunctionDef) and n.name == "partialverify")
    scope = {**vars(r2_math), **namespace}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), scope)
    return scope["partialverify"]


def transaction(study, stem, c):
    """Check original result archive/extraction, returning actual saved metadata."""
    root = study / "server_transactions"
    archive, receipt_path, extracted = root / (stem + ".tar.gz"), root / (stem + ".archive_receipt.json"), root / stem
    receipt, download = load(receipt_path), load(extracted / "download_verification.json")
    ahash = c.bind(archive)
    c.require(ahash == receipt["sha256"] == download["archive_sha256"] and receipt["transaction"] == stem
        and receipt["size"] == archive.stat().st_size and receipt["exit_code"] == 0
        and receipt["guard_triggered"] is False and download["byte_exact_result_download"] is True
        and download["TEST_accessed"] is False, "immutable_server_transaction_archive_download", stem)
    c.bind(receipt_path); c.bind(extracted / "download_verification.json")
    inventory = {r["path"]: r["sha256"] for r in download["members"]}
    saved = {}
    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        c.require({m.name for m in members} == set(inventory), "entire_download_member_inventory", stem)
        for m in members:
            raw = tar.extractfile(m).read()
            c.require(sha256(raw).hexdigest() == inventory[m.name], "all_immutable_archive_members_exact_bytes", m.name)
            leaf = m.name.split("/", 1)[1]
            saved[leaf] = raw
            if (extracted / leaf).is_file():
                c.require(c.bind(extracted / leaf) == inventory[m.name], "byte_preserved_extracted_member", m.name)
    for name in ("assessment.json", "execution.json", "feedback.json"):
        c.require(c.bind(extracted / "results" / name) == sha256(saved["results/" + name]).hexdigest(),
                  "three_exact_result_files", stem + "/" + name)
    transport = json.loads(saved[stem + ".transport_receipt.json"])
    c.require(transport["transaction"] == stem and transport["exit_code"] == 0 and not transport["guard_triggered"]
        and transport["TEST_accessed"] is False and transport["retry"] is False
        and transport["root_release_sha256"] == authors.RELEASE_SHA
        and sha256(saved["eoh_server_transaction_wrapper_v06.py"]).hexdigest() == transport["wrapper_sha256"]
        and sha256(saved[stem + ".log"]).hexdigest() == transport["log_sha256"], "original_transport_only_runtime_receipt", stem)
    c.require(saved["snapshot_path_compatibility_receipt.json"] == (root / "snapshot_path_compatibility_receipt.json").read_bytes(),
              "unchanged_exact_alias_mapping_in_each_result_archive", stem)
    for name, h in transport["result_file_sha256"].items():
        c.require(sha256(saved["results/" + name]).hexdigest() == h, "transport_all_result_hashes", stem + "/" + name)
    return load(extracted / "results/assessment.json"), load(extracted / "results/feedback.json"), load(extracted / "results/execution.json"), transport


def check_input_transaction(study, stem, request_path, c):
    capsule, receipt_path = study / "transactions" / (stem + ".zip"), study / "transactions" / (stem + ".receipt.json")
    receipt = load(receipt_path)
    c.require(c.bind(capsule) == receipt["capsule_sha256"] and receipt["id"] == stem
        and receipt["protocol_sha256"] == authors.PROTO_SHA and receipt["root_release_sha256"] == authors.RELEASE_SHA
        and receipt["TEST_accessed"] is False, "immutable_single_author_to_server_input_capsule", stem)
    c.bind(receipt_path)
    with zipfile.ZipFile(capsule) as z:
        c.require(set(z.namelist()) == set(receipt["files_sha256"]), "entire_single_input_capsule_inventory", stem)
        for name, h in receipt["files_sha256"].items():
            c.require(sha256(z.read(name)).hexdigest() == h == c.bind(ROOT / name), "single_input_capsule_exact_original_bytes", name)
    c.require(digest(request_path) in receipt["files_sha256"].values(), "capsule_binds_exact_request", stem)


def deployment_provenance(study, c):
    root = study / "server_transactions"
    alias_path = root / "snapshot_path_compatibility_receipt.json"
    note_path = root / "root_snapshot_path_provenance_clarification_001.json"
    alias, note = load(alias_path), load(note_path)
    c.require(c.bind(alias_path) == ALIAS_SHA and c.bind(note_path) == CLARIFICATION_SHA,
              "unchanged_alias_and_append_only_root_clarification_pinned")
    original, actual = alias["old_failure_archive_sha256"], digest(root / "run_0_seed.tar.gz")
    c.require(len(original) == 65 and len(actual) == 64 and actual == FAILED_ARCHIVE_SHA
        and note["unchanged_original_value"] == original and note["actual_failure_archive_sha256"] == actual
        and note["clarifies_receipt_sha256"] == ALIAS_SHA and note["issued_by"] == "root"
        and note["candidate_or_seed_fitness_evaluations_in_failed_attempt"] == 0
        and note["source_protocol_request_freeze_selector_unchanged"] is True
        and note["TEST_accessed"] is False, "65_character_original_typo_resolved_by_exact_64_byte_hash_only")
    failed_receipt = root / "run_0_seed.archive_receipt.json"
    failed = load(failed_receipt)
    c.require(c.bind(failed_receipt) == note["verified_transport_receipt_sha256"] and failed["sha256"] == actual
        and failed["exit_code"] == 1 and not failed["guard_triggered"], "original_failed_deployment_transport_retained")
    c.bind(root / "run_0_seed.tar.gz")
    c.require(c.bind(root / "run_0_seed.log") == note["failed_log_sha256"] and "load_study" in (root / "run_0_seed.log").read_text()
        and "FileNotFoundError" in (root / "run_0_seed.log").read_text(), "failure_before_quality_evaluation_log")
    with tarfile.open(root / "run_0_seed.tar.gz", "r:gz") as tar:
        members = [m.name for m in tar.getmembers() if m.isfile()]
        c.require(members == note["failure_archive_regular_file_inventory"]
            and not any("/results/" in n for n in members), "failed_attempt_zero_fitness_not_extra_seed_or_retry")
    freeze = load(study / "freeze_receipt.json")
    expected_alias = {k: h for k, h in freeze["artifact_sha256"].items() if "\\" in k}
    c.require(alias["alias_count"] == len(alias["aliases"]) == len(expected_alias) == 15
        and alias["before_any_quality_kernel_call"] is True and alias["TEST_accessed"] is False,
        "root_approved_pre_quality_exact15_path_aliases")
    for row in alias["aliases"]:
        c.require(row["frozen_key"] in expected_alias and row["sha256"] == expected_alias[row["frozen_key"]]
            and row["canonical_relative_path"] == row["frozen_key"].replace("\\", "/")
            and digest(study / row["canonical_relative_path"]) == row["sha256"], "alias_exact_unchanged_source_bytes", row["frozen_key"])


def audit(study, author_audit, out):
    began = time.perf_counter()
    selection = authors.final_gate(study)
    c = authors.Checks()
    p, config, context, records, seed, transport = authors.static(study, c)
    selected_sha = c.bind(study / "selection.json")
    author = load(author_audit)
    author_ok = (author.get("audit_phase") == "authoring" and author.get("errors") == 0 and author.get("checks", 0) > 0
        and author.get("selection_sha256") == selected_sha and author.get("all32_positions_frozen") is True
        and author.get("protocol_sha256") == authors.PROTO_SHA and author.get("root_authoring_release_sha256") == authors.RELEASE_SHA
        and author.get("TEST_accessed") is False)
    c.require(author_ok, "positive_independent_all32_authoring_receipt")
    if not author_ok:
        raise ValueError("Pass the independently reviewed all32 authoring audit before reading TRAIN assessments")
    c.bind(author_audit)
    c.require(c.bind(ROOT / "scripts/verify_refinement_train_v06.py") == R2_MATH_SHA
        and c.bind(ROOT / "scripts/verify_synthesis_train_v06.py") == R1_MATH_SHA, "independent_trace_math_sources_unchanged")
    prep_capsule = study.parent / "v06_published_eoh_001_preparation_capsule.zip"
    c.require(c.bind(prep_capsule) == CAPSULE_SHA, "original_pre_authoring_source_preparation_capsule")
    deployment_provenance(study, c)
    cfg = load(study / "kernel_config.json")
    c.require(cfg["seconds"] == 0.5 and cfg["clock"] == "wall" and cfg["workers"] == 8
        and cfg["repair_config"] == load(ROOT / "configs/repair_train_v06_001.json")["repair_config"],
        "original_R2_shared_kernel_caps_no_optimizer_change")
    state_views = {}
    for r in records:
        nodes, _, adj = view(r["graph"])
        state_views[r["id"]] = nodes, adj, boundary(nodes, adj, r["fixed"], r["excluded"])
    totals, exact_cache, priority_cache = Counter(), {}, {}
    namespace = {"require": c.require, "cfg": cfg, "state_views": state_views, "totals": totals,
        "exact_patch_cache": exact_cache, "priority_cache": priority_cache}
    complete = r2_math.complete_trace_verifier(namespace)
    partial = partial_trace_verifier(namespace)
    programs = {s["id"]: s["program"] for s in author["sessions"]}
    summaries, order = [], []
    for wave in ((0, 1), (2, 3)):
        tasks = [(r, None) for r in wave] + [(r, s) for s in range(8) for r in wave]
        for run, slot in tasks:
            if slot is not None and f"run_{run}_slot_{slot}" in author.get("unissued_positions", []):
                continue
            stem = f"run_{run}_seed" if slot is None else f"run_{run}_slot_{slot}"
            actual_stem = "run_0_seed_deployed" if run == 0 and slot is None else stem
            assessment, f, execution, host = transaction(study, actual_stem, c)
            imported = authors.feedback(study, run, slot, p, c)
            request_path = study / "requests" / (stem + ".json")
            request = load(request_path)
            c.require(f == imported and authors.label_free(f) and execution == load(study / "fitness" / f"run_{run}" /
                ("seed.receipt.json" if slot is None else f"slot_{slot}.receipt.json")), "exact_original_fitness_import_no_changed_feedback", stem)
            c.require(execution["request_sha256"] == digest(request_path) == host["request_sha256"]
                and execution["source_sha256"] == p["source_sha256"] and execution["protocol_sha256"] == authors.PROTO_SHA
                and execution["root_release_sha256"] == authors.RELEASE_SHA and execution["training_states_sha256"] == p["training_states_sha256"]
                and execution["split"] == "train" and execution["TEST_accessed"] is False and execution["certificate_access"] is False,
                "server_frozen_source_request_fullTRAIN_no_labels_or_TEST", stem)
            result_root = study / "server_transactions" / actual_stem / "results"
            c.require(execution["assessment_sha256"] == digest(result_root / "assessment.json")
                and execution["feedback_sha256"] == digest(result_root / "feedback.json")
                and assessment["request"] == request and assessment["certificate_access"] is False
                and assessment["selection_performed"] is False, "bound_raw_assessment_without_certificates_or_selection", stem)
            command = host["command"]
            c.require(command[1:5] == ["-B", "-m", "cipheur.published_eoh_v06", "evaluate"]
                and "--request" in command and command[command.index("--request") + 1].endswith("requests/" + stem + ".json")
                and command[command.index("--root-release-sha256") + 1] == authors.RELEASE_SHA,
                "only_original_server_evaluator_command", stem)
            if slot is not None:
                check_input_transaction(study, stem, request_path, c)
            start, finish = (datetime.fromisoformat(host[k].replace("Z", "+00:00")) for k in ("started_utc", "finished_utc"))
            c.require(start <= finish, "original_host_time_order", stem)
            if order:
                c.require(order[-1]["finished_utc"] <= start, "fixed_slot_run_serialized_fitness_no_overlap", stem)
            order.append({"id": stem, "started_utc": start, "finished_utc": finish})
            raw = seed["program"] if slot is None else programs.get(stem)
            c.require(assessment["program"] == raw, "independent_static_parser_exact_original_assessed_program", stem)
            rows = assessment["kernel_rows"]
            covered = False
            if raw is None:
                c.require(rows == [] and assessment["failure"] is not None and f["program_sha256"] is None,
                          "failed_author_slot_no_hidden_program_or_evaluation", stem)
            else:
                c.require(len(rows) == 120 and [r["id"] for r in rows] == sorted(state_views)
                    and len({r["id"] for r in rows}) == 120 and canonical(raw) == f["program_sha256"],
                    "all120_real_assignment_rows_without_drop_or_replacement", stem)
                rmap = {r["id"]: r for r in records}
                for row in rows:
                    r = rmap[row["id"]]
                    c.require(row["family"] == r["family"] and row["cluster"] == r["cluster"], "unchanged_source_family_cluster", stem + "/" + row["id"])
                    result = row.get("result")
                    if result is None:
                        c.require("error_type" in row and "error" in row, "explicit_original_worker_or_parse_failure_no_fallback", stem)
                        totals["row_errors"] += 1; continue
                    try:
                        verifier = partial if result["global_budget_exhausted"] or not result["completed"] else complete
                        verifier(r, result, raw, stem + "/" + row["id"])
                    except Exception as error:
                        c.require(False, "independent_saved_trace_replay_exception", stem + "/" + row["id"] + "/" + type(error).__name__ + ":" + str(error))
                covered = all(row.get("result", {}).get("completed") and row["result"]["feasible"] for row in rows)
            summary = None
            if covered:
                fq, fw = defaultdict(list), defaultdict(list)
                rmap = {r["id"]: r for r in records}
                for row in rows:
                    r, result = rmap[row["id"]], row["result"]
                    total = sum((Fraction(n["weight"]) for n in r["graph"]["contacts"]), Fraction())
                    fq[r["family"]].append(Fraction(result["value_exact"]) / total if total else Fraction(1))
                    fw[r["family"]].append(result["meter"]["feature_work"] + result["meter"]["repair_work"])
                qmean = {f: sum(v, Fraction()) / len(v) for f, v in fq.items()}
                wmean = {f: Fraction(sum(v), len(v)) for f, v in fw.items()}
                summary = {"macro_quality_exact": str(sum(qmean.values(), Fraction()) / len(qmean)),
                    "macro_work_exact": str(sum(wmean.values(), Fraction()) / len(wmean)),
                    "family_reward_over_total_weight": {f: str(q) for f, q in qmean.items()}, "family_work": {f: str(w) for f, w in wmean.items()}}
            c.require(assessment["kernel_summary"] == summary and f["quality_covered"] == covered
                and f["macro_quality_exact"] == (summary["macro_quality_exact"] if summary else None)
                and f["macro_work_exact"] == (summary["macro_work_exact"] if summary else None)
                and f["family_quality"] == (summary["family_reward_over_total_weight"] if summary else None)
                and f["family_work"] == (summary["family_work"] if summary else None),
                "independent_exact_equal_family_quality_and_work_feedback", stem)
            completed = sum(bool(row.get("result", {}).get("completed") and row["result"]["feasible"]) for row in rows)
            errors = sum(not bool(row.get("result", {}).get("completed") and row["result"]["feasible"]) for row in rows)
            c.require(f["assigned_states"] == 120 and f["completed_feasible_states"] == completed
                and f["error_count"] == errors and f["unexecuted_states"] == 120 - len(rows)
                and f["status"] == ("invalid_or_failed_original_attempt" if raw is None else "quality_covered" if covered else "kernel_error"),
                "real_failure_completed_and_unexecuted_counts_retained", stem)
            for key in ("actual_cpu_seconds", "actual_wall_seconds"):
                c.require(type(assessment[key]) in (int, float) and math.isfinite(assessment[key]) and assessment[key] >= 0,
                          "finite_original_parent_process_timing_not_total_CPU", stem + "/" + key)
            summaries.append({"id": stem, "run": run, "slot": slot, "quality_covered": covered,
                "program_sha256": f["program_sha256"], "macro_quality_exact": f["macro_quality_exact"],
                "macro_work_exact": f["macro_work_exact"], "completed_feasible_states": completed,
                "error_count": errors, "unexecuted_states": 120 - len(rows),
                "normal_budget_stops": sum(bool(row.get("result", {}).get("budget_exhausted")) for row in rows),
                "parent_process_cpu_seconds": assessment["actual_cpu_seconds"], "assessment_wall_seconds": assessment["actual_wall_seconds"]})
    c.require(sum(s["slot"] is None for s in summaries) == 4 and len(summaries) + len(author.get("unissued_positions", [])) == 36,
              "four_actual_seed_fitness_plus_all32_original_positions")
    # Check final selector against independently recomputed fitness, never source feedback alone.
    byid = {s["id"]: s for s in summaries}
    for output in selection["programs"]:
        source = output["source_id"]
        if source is not None:
            stem = source.replace(":warm_seed", "_seed")
            c.require(byid[stem]["quality_covered"] and byid[stem]["program_sha256"] == output["program_sha256"],
                      "final_pipeline_program_has_real_full_TRAIN_fitness", output["id"])
        run = output["run"]
        sf = byid[f"run_{run}_seed"]
        pop = authors.population([{"id": f"run_{run}:warm_seed", "program": seed["program"], "feedback": sf}])
        for slot in range(8):
            stem = f"run_{run}_slot_{slot}"
            if stem in byid and byid[stem]["quality_covered"]:
                pop = authors.population(pop + [{"id": stem, "program": programs[stem], "feedback": byid[stem]}])
        best = pop[0] if pop else None
        c.require(output["source_id"] == (best["id"] if best else None)
            and output["program"] == (best["program"] if best else None),
            "final_first_rounded_quality_selection_recomputed_from_independent_schedule_values", output["id"])
    report = {"version": "independent_published_EoH_frozen_TRAIN_audit_001", "audit_phase": "train",
        "checks": sum(c.counts.values()), "checks_by_kind": dict(c.counts), "errors": len(c.errors), "error_details": c.errors,
        "selection_sha256": selected_sha, "protocol_sha256": authors.PROTO_SHA, "root_authoring_release_sha256": authors.RELEASE_SHA,
        "all32_positions_frozen": True, "TEST_accessed": False, "totals": dict(totals), "fitness_inventory": summaries,
        "actual_seed_fitness_count": 4, "original_author_position_count": 32, "source_and_receipt_bindings": c.bindings,
        "audit_script_sha256": digest(__file__), "author_audit_script_sha256": digest(ROOT / "scripts/verify_published_eoh_authoring_v06.py"),
        "cpu_scope": "assessment.actual_cpu_seconds is the parent evaluator process only; worker CPU is not included, and no total_CPU claim is made",
        "original_deployment_hash_clarification": {"original_field_length": 65, "actual_archive_hash_length": 64,
            "failed_quality_evaluations": 0, "unchanged_alias_sha256": ALIAS_SHA, "append_only_clarification_sha256": CLARIFICATION_SHA},
        "elapsed_verifier_seconds": time.perf_counter() - began,
        "scope": "Replay of saved120 TRAIN schedules/priority/patch proof receipts; no production reexecution, oracle, TEST, selection changes or new author feedback"}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", default=str(authors.STUDY)); p.add_argument("--authoring-audit")
    p.add_argument("--out", required=True)
    a = p.parse_args(); study = Path(a.study); out = Path(a.out)
    if out.exists():
        raise ValueError("Preserve original audit outputs; use a new reviewed file for any resolution")
    report = audit(study, a.authoring_audit or study / "audit/authoring_audit.json", out)
    print(json.dumps({"checks": report["checks"], "errors": report["errors"], "report_sha256": digest(out)}))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
