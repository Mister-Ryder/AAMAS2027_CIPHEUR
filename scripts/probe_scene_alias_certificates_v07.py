"""Prepared-only by default; bounded Linux TRAIN conditional diagnostics.

Preserve 1,062 source/configuration positions. Only the 46 action pairs that
compete on both configurations are eligible (92 positions). No learner/TEST.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
import multiprocessing as mp
from pathlib import Path
import platform
import signal
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import screen_contact_scene_v07 as scene

SOURCES = ("scripts/probe_scene_alias_certificates_v07.py", "scripts/screen_contact_scene_v07.py",
           "cipheur/__init__.py", "cipheur/model.py", "cipheur/programs.py",
           "cipheur/graph_features.py", "cipheur/compiled.py", "cipheur/oracle.py",
           "cipheur/representation.py", "cipheur/refinement.py",
           "cipheur/relevance_synthesis_v04.py", "cipheur/v51_adapter.py")
OPERATION = "bounded_train_scene_alias_certificates"


class ComponentWallExceeded(TimeoutError):
    pass


class ComparisonWallExceeded(TimeoutError):
    pass


def primitive_status(interval):
    lower, upper = Fraction(interval["lower_exact"]), Fraction(interval["upper_exact"])
    if lower > upper:
        raise ValueError("Unsound reversed interval")
    return ("strict_a" if lower > 0 else "strict_b" if upper < 0
            else "exact_tie" if lower == upper == 0 else "unknown")


def make_bounded_oracle(graph):
    # Importing this module defines classes only; no schedule/oracle is called here.
    from cipheur.relevance_synthesis_v04 import CancelledCompletionOracle
    from cipheur.oracle import exact_value

    class BoundedOracle(CancelledCompletionOracle):
        def __init__(self):
            super().__init__(graph, (), (), nodes_per_component=2000,
                             max_search_component=10000, max_nodes=2000, max_calls=64)
            self.compare_deadline = self.component_deadline = None
            self.completed_expansions = self.component_timeouts = self.cache_hits = 0

        def alarm(self, _signum, _frame):
            now = time.monotonic()
            if self.compare_deadline is not None and now >= self.compare_deadline:
                raise ComparisonWallExceeded("comparison_wall_guard_5s")
            raise ComponentWallExceeded("component_wall_guard_1s")

        def arm(self):
            deadlines = [x for x in (self.compare_deadline, self.component_deadline) if x is not None]
            signal.setitimer(signal.ITIMER_REAL, max(0.000001, min(deadlines) - time.monotonic())
                            if deadlines else 0)

        def begin(self):
            # Valid completed/trivial cache entries persist; fresh per-comparison
            # call/node allowances do not reinterpret previous timeout debits.
            self.calls = self.expanded_nodes = 0
            self.completed_expansions = self.component_timeouts = self.cache_hits = 0
            self.component_deadline = None
            self.compare_deadline = time.monotonic() + 5.0
            self.old_handler = signal.signal(signal.SIGALRM, self.alarm)
            self.arm()

        def finish(self):
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self.old_handler)
            self.compare_deadline = self.component_deadline = None

        def bound(self, part):
            part = tuple(part)
            if part in self.cache:
                self.cache_hits += 1
                return self.cache[part]
            before_nodes, before_calls = self.expanded_nodes, self.calls
            allowance = min(self.nodes_per_component, self.max_nodes - before_nodes)
            if len(part) > self.max_search_component or before_calls >= self.max_calls:
                allowance = 0
            self.component_deadline = time.monotonic() + 1.0
            self.arm()
            try:
                answer = super().bound(part)
                self.completed_expansions += self.expanded_nodes - before_nodes
                return answer
            except ComponentWallExceeded:
                self.component_timeouts += 1
                # An interrupted solver does not expose its partial node count.
                # Debit its entire allowance to guarantee <=2,000 actual search
                # expansions over all component calls of this comparison.
                self.expanded_nodes = min(self.max_nodes, max(self.expanded_nodes, before_nodes + allowance))
                self.calls = max(self.calls, before_calls + 1)
                if part not in self.cache:
                    upper = exact_value(self.graph, part)
                    self.cache[part] = {"lower_exact": "0", "upper_exact": str(upper),
                        "selected": [], "exact": upper == 0, "expanded": None,
                        "reason": "component_timeout_sound_trivial_interval",
                        "node_allowance_debited": allowance,
                        "partial_search_nodes_observed": False}
                return self.cache[part]
            except ComparisonWallExceeded:
                self.expanded_nodes = min(self.max_nodes, max(self.expanded_nodes, before_nodes + allowance))
                self.calls = max(self.calls, before_calls + 1)
                raise
            finally:
                self.component_deadline = None
                self.arm()

    return BoundedOracle()


def trivial_difference(graph, a, b):
    """Singleton feasible lower and full conditional-residual sum upper."""
    wa, wb = Fraction(graph.nodes[a].weight), Fraction(graph.nodes[b].weight)
    active = graph.available((), ())
    if a == b or a not in active or b not in active:
        raise ValueError("Actions must be distinct and individually feasible")
    upper_a = wa + sum((Fraction(graph.nodes[v].weight)
                       for v in active - graph.adj[a] - {a}), Fraction(0))
    upper_b = wb + sum((Fraction(graph.nodes[v].weight)
                       for v in active - graph.adj[b] - {b}), Fraction(0))
    return {"lower_exact": str(wa - upper_b), "upper_exact": str(upper_a - wb),
            "conditional_a": {"lower_exact": str(wa), "upper_exact": str(upper_a)},
            "conditional_b": {"lower_exact": str(wb), "upper_exact": str(upper_b)},
            "method": "feasible_forced_singleton_and_nonnegative_conditional_residual_weight_sum"}


def compact_difference(result, oracle, emitted, component_stream):
    def reference(part):
        part = tuple(part)
        key = scene.digest(scene.canonical(part))
        if key not in emitted:
            record = {"component_id": key, "vertices": list(part), "vertex_count": len(part),
                      "bound": oracle.cache.get(part),
                      "identity": "exact sorted vertex set in this graph; never cross-configuration cancellation"}
            component_stream.write(json.dumps(record, allow_nan=False) + "\n")
            emitted.add(key)
        return key
    answer = {key: value for key, value in result.items() if key not in ("cancelled_components", "unmatched")}
    answer["cancelled_components"] = [reference(part) for part in result.get("cancelled_components", [])]
    answer["unmatched"] = {side: [reference(row["vertices"]) for row in result.get("unmatched", {}).get(side, [])]
                            for side in ("a", "b")}
    component_stream.flush()
    return answer


def process_window(task, out, stable_root):
    from cipheur.v51_adapter import _load_legacy
    from cipheur.model import Contact, Graph
    legacy, _ = _load_legacy(Path(stable_root))
    rows = [row["row_sha256"] for row in task["contacts"]]
    if len(set(rows)) != len(rows):
        raise ValueError("Ambiguous duplicated canonical contact identities")
    arcs = tuple(legacy["data"].Arc(id=i, priority=0.0,
        **{key: value for key, value in row.items() if key not in ("original_row_id", "row_sha256")})
        for i, row in enumerate(task["contacts"]))
    for gap in (340, 680):
        context = f"{task['source']}_window{task['window']:02d}_g{gap}"
        begin = time.perf_counter()
        native_graph = legacy["graph"].build_conflict_graph(arcs, legacy["graph"].ConflictParameters(gap, 150, 300))
        if native_graph.graph_hash != task["graph_hashes"][gap]:
            raise ValueError("Graph differs from the original frozen TRAIN input")
        contacts = tuple(Contact(rows[i], arc.link_time, arc.satellite_name, arc.ground_name,
                                 arc.link_st, arc.link_et) for i, arc in enumerate(arcs))
        graph = Graph(context, contacts,
                      frozenset(tuple(sorted((rows[int(a)], rows[int(b)]))) for a, b in native_graph.edges),
                      {"model": "v51_legacy", "ground_trans_time": gap,
                       "satellite_change_time": 150, "satellite_trans_time": 300})
        oracle = make_bounded_oracle(graph)
        scene.write_json(out / (context + ".graph_receipt.json"), {
            "context": context, "legacy_graph_sha256": native_graph.graph_hash,
            "oracle_graph_sha256": graph.digest(), "n": len(contacts), "m": len(graph.edges),
            "setup_wall_seconds": time.perf_counter() - begin,
            "setup_excluded_from_comparison_guard": True})
        emitted = set()
        with (out / (context + ".components.jsonl")).open("x", encoding="utf-8", newline="\n") as cs:
            with (out / (context + ".rows.jsonl")).open("x", encoding="utf-8", newline="\n") as stream:
                for position in task["positions"][gap]:
                    row = dict(position)
                    if not position["eligible_competing_both_configs"]:
                        row.update(status="not_queried_noncompeting_scene", label=None,
                                   interval=None, oracle_difference_called=False)
                    else:
                        a, b = position["a_row_sha256"], position["b_row_sha256"]
                        if a not in graph.available((), ()) or b not in graph.available((), ()) or b not in graph.adj[a]:
                            raise ValueError("Frozen scene eligibility does not hold in rebuilt graph")
                        fallback = trivial_difference(graph, a, b)
                        started_wall, started_cpu = time.perf_counter(), time.process_time()
                        if position["input_classification"]["kind"] != "non_twins":
                            proof = position["input_classification"].get("conditional_tie_proof")
                            if (not proof or proof["boundary"] != {"fixed": [], "excluded": []} or
                                proof["graph_sha256"] != native_graph.graph_hash or
                                graph.nodes[a].weight != graph.nodes[b].weight or
                                graph.adj[a] - {b} != graph.adj[b] - {a}):
                                raise ValueError("Transposition tie proof fails its frozen scope")
                            row.update(status="reused_exact_transposition_tie", label="exact_tie",
                                interval={"lower_exact": "0", "upper_exact": "0"},
                                proof=proof, oracle_difference_called=False)
                        else:
                            oracle.begin()
                            try:
                                result = oracle.difference(a, b, epsilon=0)
                                oracle.finish()
                                interval = {key: result[key] for key in ("lower_exact", "upper_exact")}
                                row.update(status="completed_sound_interval", label=primitive_status(interval),
                                    interval=interval, result=compact_difference(result, oracle, emitted, cs),
                                    oracle_difference_called=True)
                            except ComparisonWallExceeded:
                                oracle.finish()
                                row.update(status="comparison_wall_guard_unknown", label="unknown",
                                    interval=fallback, oracle_difference_called=True,
                                    incomplete_bound_discarded=True)
                            except Exception as error:
                                oracle.finish()
                                row.update(status="oracle_error_unknown", label="unknown", interval=fallback,
                                    oracle_difference_called=True,
                                    error=type(error).__name__ + ": " + str(error),
                                    incomplete_bound_discarded=True)
                            row["budget_receipt"] = {
                                "component_call_debit": oracle.calls, "node_budget_debit": oracle.expanded_nodes,
                                "observed_completed_expansions": oracle.completed_expansions,
                                "component_timeouts": oracle.component_timeouts, "cache_hits": oracle.cache_hits,
                                "max_nodes_per_comparison": 2000, "max_component_calls_per_comparison": 64,
                                "timeout_node_debit_is_not_observed_expansion_count": True}
                        row.update(actual_wall_seconds=time.perf_counter() - started_wall,
                                   actual_cpu_seconds=time.process_time() - started_cpu)
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
                    stream.flush()
        scene.write_json(out / (context + ".completion.json"), {
            "positions": len(task["positions"][gap]), "context": context,
            "rows_sha256": scene.digest((out / (context + ".rows.jsonl")).read_bytes())})


def worker(queue, out, stable_root):
    while True:
        task = queue.get()
        if task is None:
            return
        try:
            process_window(task, Path(out), stable_root)
        except Exception as error:
            scene.write_json(Path(out) / f"{task['source']}_window{task['window']:02d}.failure.json",
                             {"error": type(error).__name__ + ": " + str(error),
                              "source": task["source"], "window": task["window"]})


def prepare(args):
    out, screen, classification = map(lambda value: Path(value).resolve(), (args.out, args.screen, args.classification))
    if out.exists():
        raise ValueError("Preserve the initial certificate namespace")
    old_freeze = json.loads((screen / "freeze_receipt.json").read_bytes())
    screen_complete = json.loads((screen / "completion_receipt.json").read_bytes())
    cc = json.loads((classification / "completion_receipt.json").read_bytes())
    classified_raw = (classification / "classification_summary.json").read_bytes()
    if (screen_complete["completed_graphs"] != 48 or screen_complete["failed_windows"] != 0 or
        cc["completed_graphs"] != 48 or cc["classified_alias_pairs"] != 556 or cc["failed_windows"] != 0 or
        scene.digest(classified_raw) != cc["summary_sha256"]):
        raise ValueError("Require the complete pinned input/symmetry census")
    if scene.source_closure(old_freeze["stable_root"]) != old_freeze["source_sha256"]:
        raise ValueError("Prior frozen input source changed")
    classified = json.loads(classified_raw)
    positions = []
    for pair in classified["cross_configuration"]:
        eligible = pair["gap340"]["adjacent"] and pair["gap680"]["adjacent"]
        pair_id = scene.digest(scene.canonical([pair["source"], pair["window"], pair["a_row_sha256"], pair["b_row_sha256"]]))
        for gap in (340, 680):
            positions.append({"id": pair_id + f":g{gap}", "pair_id": pair_id,
                "source": pair["source"], "window": pair["window"], "split": "TRAIN", "day": 0,
                "ground_gap": gap, "a_row_sha256": pair["a_row_sha256"], "b_row_sha256": pair["b_row_sha256"],
                "eligible_competing_both_configs": bool(eligible),
                "input_classification": pair[f"gap{gap}"],
                "boundary": {"fixed": [], "excluded": []}})
    positions.sort(key=lambda row: (row["source"], row["window"], row["ground_gap"], row["pair_id"]))
    if len(positions) != 1062 or sum(row["eligible_competing_both_configs"] for row in positions) != 92:
        raise ValueError("The exact preregistered 531/46 pair frame is required")
    bound_artifacts = {"screen_protocol": scene.digest((screen / "protocol.json").read_bytes()),
                       "screen_summary": scene.digest((screen / "screen_summary.json").read_bytes()),
                       "screen_freeze": scene.digest((screen / "freeze_receipt.json").read_bytes()),
                       "classification_summary": scene.digest(classified_raw)}
    old_protocol = json.loads((screen / "protocol.json").read_bytes())
    hashes = {name: scene.digest((ROOT / name).read_bytes()) for name in SOURCES}
    legacy_root = Path(old_freeze["stable_root"]) / "SNSD_V51_FINAL/src/snsd_core"
    hashes.update({"legacy_project/SNSD_V51_FINAL/src/snsd_core/" + name:
                   scene.digest((legacy_root / name).read_bytes()) for name in scene.LEGACY_SOURCES})
    protocol = {"operation": OPERATION, "status": "prepared_not_released", "before_any_conditional_query": True,
        "sources": old_protocol["sources"], "input_bindings": bound_artifacts,
        "assigned_unique_pairs": 531, "assigned_positions": 1062, "eligible_competing_pairs": 46,
        "eligible_positions": 92, "noncompeting_pairs": 485, "noncompeting_positions": 970,
        "original_alias_occurrences": 556, "adjacent_alias_occurrences": 47,
        "adjacent_nontwin_alias_occurrences": 43, "adjacent_twin_alias_occurrences": 4,
        "eligibility": "adjacent on BOTH predeclared configurations; prelabel scene predicate, not oracle/quality selection",
        "superseded_unexecuted_draft": "all1062 queried; replaced before any freeze or oracle call",
        "graph_count": 48, "train_days": [0], "boundary": {"fixed": [], "excluded": []},
        "ground_gaps": [340, 680], "satellite_change_time": 150, "satellite_trans_time": 300,
        "nodes_per_component": 2000, "max_nodes_per_comparison": 2000,
        "max_search_component": 10000, "max_component_calls_per_comparison": 64,
        "component_wall_seconds": 1, "comparison_wall_seconds": 5,
        "whole_batch_wall_seconds": 600, "recommended_external_guard_seconds": 900, "workers": 8,
        "node_timeout_debit": "entire allocated allowance charged when interrupted prefix node count is unavailable",
        "comparison_guard_excludes": "input reads, graph construction, verified trivial fallback preparation; includes partitions, component construction and original bound calls",
        "whole_guard_includes": "input materialization, graph setup, comparisons and worker output; final ledger aggregation separately timed",
        "comparison_timeout": "unknown with independently prepared singleton lower/conditional residual sum upper; discard incomplete difference",
        "cache": "same graph only, exact vertex-set components; only completed verified or explicitly sound trivial entries; no retry/refinement after timeout",
        "query_order": "fixed source/window/config/pair_id order; asynchronous windows, deterministic within graph",
        "scope": "initial full-residual conditional MWIS; no actual greedy-path or repair-boundary claim",
        "test_allowed": False, "learner_allowed": False, "model_calls": 0,
        "source_sha256": hashes}
    out.mkdir(parents=True)
    scene.write_json(out / "protocol.json", protocol)
    scene.write_json(out / "query_inventory.json", {"positions": positions})
    (out / "screen_summary.json").write_bytes((screen / "screen_summary.json").read_bytes())
    with zipfile.ZipFile(out / "source_capsule.zip", "x", compression=zipfile.ZIP_DEFLATED) as capsule:
        for name in SOURCES:
            capsule.writestr(name, (ROOT / name).read_bytes())
        for name in scene.LEGACY_SOURCES:
            capsule.writestr("legacy_project/SNSD_V51_FINAL/src/snsd_core/" + name, (legacy_root / name).read_bytes())
        for name in ("protocol.json", "query_inventory.json", "screen_summary.json"):
            capsule.writestr("study/" + name, (out / name).read_bytes())
    scene.write_json(out / "freeze_receipt.json", {
        "before_any_conditional_query": True, "created_unix": time.time(),
        "protocol_sha256": scene.digest((out / "protocol.json").read_bytes()),
        "query_inventory_sha256": scene.digest((out / "query_inventory.json").read_bytes()),
        "source_capsule_sha256": scene.digest((out / "source_capsule.zip").read_bytes()),
        "screen_summary_sha256": scene.digest((out / "screen_summary.json").read_bytes())})
    print(json.dumps({"prepared": str(out), "assigned_positions": 1062,
                      "eligible_positions": 92, "oracle_calls": 0}), flush=True)


def run(args):
    if platform.system() != "Linux":
        raise ValueError("Conditional diagnostics are server-only and require POSIX timers")
    study, out = Path(args.study).resolve(), Path(args.out).resolve()
    if out.exists():
        raise ValueError("Use a new immutable result directory; no resume or retries")
    freeze = json.loads((study / "freeze_receipt.json").read_bytes())
    release_raw = Path(args.root_release).read_bytes()
    release = json.loads(release_raw)
    for name, field in (("protocol.json", "protocol_sha256"), ("query_inventory.json", "query_inventory_sha256"),
                        ("screen_summary.json", "screen_summary_sha256")):
        if scene.digest((study / name).read_bytes()) != freeze[field] or release.get(field) != freeze[field]:
            raise ValueError("Frozen study/release binding mismatch: " + name)
    if (release.get("operation") != OPERATION or release.get("before_any_conditional_query") is not True or
        release.get("test_allowed") is not False or release.get("source_capsule_sha256") != freeze["source_capsule_sha256"]):
        raise ValueError("A matching root release is mandatory")
    if scene.digest(Path(args.source_capsule).read_bytes()) != freeze["source_capsule_sha256"]:
        raise ValueError("Actual uploaded source capsule differs from the frozen bytes")
    protocol = json.loads((study / "protocol.json").read_bytes())
    stable_root = Path(args.legacy_root).resolve()
    for name, expected in protocol["source_sha256"].items():
        path = (stable_root / name.split("legacy_project/", 1)[1] if name.startswith("legacy_project/") else ROOT / name)
        if scene.digest(path.read_bytes()) != expected:
            raise ValueError("Pinned source differs: " + name)
    positions = json.loads((study / "query_inventory.json").read_bytes())["positions"]
    expected = {row["id"]: row for row in positions}
    out.mkdir(parents=True)
    begin = time.monotonic()
    scene.write_json(out / "execution_receipt.json", {"start_unix": time.time(), "root_release_sha256": scene.digest(release_raw),
        "protocol_sha256": freeze["protocol_sha256"], "workers": 8, "python": sys.version,
        "whole_batch_wall_seconds": 600, "assigned_positions": 1062, "eligible_positions": 92})
    per_context = defaultdict(list)
    for row in positions:
        per_context[(row["source"], row["window"], row["ground_gap"])].append(row)
    old = json.loads((study / "screen_summary.json").read_bytes())
    graph_hashes = {(r["source"], r["window"], r["ground_trans_time"]): r["legacy_graph_sha256"] for r in old["records"]}
    tasks = []
    for source in protocol["sources"]:
        source = {**source, "path": str(Path(args.data_root).resolve() / (source["name"] + ".csv"))}
        windows, _, _ = scene.read_train(source, 0, {0})
        for window, contacts in sorted(windows.items()):
            tasks.append({"source": source["name"], "window": window, "contacts": contacts,
                          "positions": {gap: per_context[(source["name"], window, gap)] for gap in (340, 680)},
                          "graph_hashes": {gap: graph_hashes[(source["name"], window, gap)] for gap in (340, 680)}})
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    for task in tasks:
        queue.put(task)
    for _ in range(8):
        queue.put(None)
    processes = [ctx.Process(target=worker, args=(queue, str(out), str(stable_root))) for _ in range(8)]
    for process in processes:
        process.start()
    terminated = []
    while any(process.is_alive() for process in processes):
        if time.monotonic() - begin >= 600:
            for process in processes:
                if process.is_alive():
                    terminated.append(process.pid)
                    process.terminate()
            break
        for process in processes:
            process.join(timeout=.1)
    for process in processes:
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=2)
    queue.cancel_join_thread()
    queue.close()
    rows, partial_lines = {}, []
    for path in sorted(out.glob("*.rows.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                partial_lines.append({"file": path.name, "line": number})
                continue
            if row["id"] not in expected or row["id"] in rows:
                raise ValueError("Unexpected/duplicated assignment ID in durable results")
            rows[row["id"]] = row
    for identity, position in expected.items():
        if identity not in rows:
            competing = position["eligible_competing_both_configs"]
            rows[identity] = {**position, "status": "batch_or_worker_failure_unknown" if competing else "not_queried_noncompeting_scene",
                              "label": "unknown" if competing else None, "interval": None,
                              "oracle_difference_called": None, "missing_worker_row": True}
    pair_rows = []
    by_pair = defaultdict(dict)
    for row in rows.values():
        by_pair[row["pair_id"]][row["ground_gap"]] = row
    for identity, both in sorted(by_pair.items()):
        a, b = both[340], both[680]
        left, right = a.get("label"), b.get("label")
        category = ("not_queried_noncompeting_scene" if not a["eligible_competing_both_configs"] else
                    "strict_reversal" if {left, right} == {"strict_a", "strict_b"} else
                    "strict_preservation" if left == right and left in ("strict_a", "strict_b") else
                    "exact_tie_both" if left == right == "exact_tie" else
                    "strict_to_exact_tie" if left in ("strict_a", "strict_b") and right == "exact_tie" else
                    "exact_tie_to_strict" if left == "exact_tie" and right in ("strict_a", "strict_b") else "unknown")
        pair_rows.append({"pair_id": identity, "source": a["source"], "window": a["window"],
                          "eligible": a["eligible_competing_both_configs"], "category": category,
                          "g340_id": a["id"], "g680_id": b["id"]})
    with (out / "complete_position_ledger.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for identity in sorted(rows):
            stream.write(json.dumps(rows[identity], allow_nan=False) + "\n")
    scene.write_json(out / "summary.json", {"assigned_positions": 1062, "retained_positions": len(rows),
        "eligible_positions": 92, "status_counts": dict(Counter(row["status"] for row in rows.values())),
        "eligible_label_counts": dict(Counter(row["label"] for row in rows.values() if row["eligible_competing_both_configs"])),
        "pair_categories": dict(Counter(row["category"] for row in pair_rows)), "pairs": pair_rows,
        "whole_guard_terminated_owned_pids": terminated, "partial_json_lines": partial_lines,
        "elapsed_wall_seconds": time.monotonic() - begin, "test_graphs": 0, "model_calls": 0})
    scene.write_json(out / "completion_receipt.json", {"terminal": True, "assigned_positions": 1062,
        "retained_positions": len(rows), "summary_sha256": scene.digest((out / "summary.json").read_bytes()),
        "ledger_sha256": scene.digest((out / "complete_position_ledger.jsonl").read_bytes()),
        "protocol_sha256": freeze["protocol_sha256"], "root_release_sha256": scene.digest(release_raw)})
    print(json.dumps({"terminal": True, "retained_positions": len(rows), "eligible_positions": 92}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--screen")
    parser.add_argument("--classification")
    parser.add_argument("--study")
    parser.add_argument("--root-release")
    parser.add_argument("--data-root")
    parser.add_argument("--legacy-root")
    parser.add_argument("--source-capsule")
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else run)(args)


if __name__ == "__main__":
    main()
