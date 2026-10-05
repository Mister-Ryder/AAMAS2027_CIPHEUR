"""Prepare, root-run and ingest bounded native-CLI proposals.

Root runs the recorded argv with stdin_path, captures stdout as events.jsonl,
stderr as stderr.txt, and writes execution_receipt.json with exit_code. The
ingest gate rejects tool activity and uses the real FeatureRuleProgram parser.
The implementation subagent does not run run-planned; root owns actual calls.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from train_context import CONDITIONS, FEATURES, SOURCES, PROJECT, encoded, digest, freeze_json, require


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[1]
MODEL = "gpt-6.1-sol"
EFFORT = "ultra"


def op_schema(op, argument_type=None, arity=0):
    return {"type": "object", "properties": {
        "op": {"type": "string", "enum": [op]},
        "args": {"type": "array", "items": argument_type or {"type": "null"},
                 "minItems": arity, "maxItems": arity}},
        "required": ["op", "args"], "additionalProperties": False}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def response_schema(condition, round_number, batch):
    """The recursive schema mirrors every current public typed graph operation."""
    defs = {"Node": op_schema("root")}
    defs["NodeSet"] = {"anyOf": [op_schema("available"),
        op_schema("neighbors", ref("Node"), 1), op_schema("singleton", ref("Node"), 1),
        *[op_schema(op, ref("NodeSet"), 2) for op in ("union", "intersection", "difference")]]}
    defs["EdgeSet"] = op_schema("induced_edges", ref("NodeSet"), 1)
    constant = {"type": "object", "properties": {
        "op": {"type": "string", "enum": ["const"]},
        "value": {"type": "number", "minimum": -1e9, "maximum": 1e9}},
        "required": ["op", "value"], "additionalProperties": False}
    defs["Number"] = {"anyOf": [constant,
        op_schema("count", {"anyOf": [ref("NodeSet"), ref("EdgeSet")]}, 1),
        *[op_schema(op, ref("NodeSet"), 1) for op in
          ("sum_weights", "max_weight", "clique_cover_weight", "greedy_independent_weight")],
        *[op_schema(op, ref("EdgeSet"), 1) for op in ("edge_min_weight_sum", "edge_weight_product_sum")],
        *[op_schema(op, ref("Node"), 1) for op in ("weight", "duration")],
        *[op_schema(op, ref("Number"), 2) for op in ("add", "sub", "mul", "div", "min", "max")],
        op_schema("abs", ref("Number"), 1)]}
    defs["Feature"] = {"type": "object", "properties": {
        "name": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$", "maxLength": 80},
        "expression": ref("Number")}, "required": ["name", "expression"], "additionalProperties": False}
    defs["Program"] = {"type": "object", "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 200},
        "features": {"type": "array", "items": ref("Feature"), "maxItems": 0 if condition == "relations_rule_only" else 6},
        "rule": {"type": "string", "minLength": 1, "maxLength": 2000},
        "rationale": {"type": "string", "maxLength": 20000}},
        "required": ["name", "features", "rule", "rationale"], "additionalProperties": False}
    return {"type": "object", "$defs": defs, "properties": {
        "condition": {"type": "string", "enum": [condition]},
        "round": {"type": "integer", "enum": [round_number]},
        "batch": {"type": "integer", "enum": [batch]},
        "programs": {"type": "array", "items": ref("Program"), "minItems": 8, "maxItems": 8}},
        "required": ["condition", "round", "batch", "programs"], "additionalProperties": False}


def representative_view(context):
    """32 TRAIN requirements: real reverse-edge cycles, then source/stage/size strata.

    The full 743 requirements remain frozen for scoring. Sampling is only a
    prompt-size choice and does not depend on any candidate or held-out result.
    """
    common = deepcopy(context["common"])
    rows = common["strict_relations"]
    vectors = {identifier: vector for identifier, vector in common["vectors"]}
    directed = defaultdict(list)
    for row in rows:
        directed[(row[5], row[6])].append(row)
    cycle_pairs = {tuple(sorted((u, v))) for u, v in directed if (v, u) in directed}
    primary_query = context["witness_only"]["query_id"]
    ordered_cycles = sorted(cycle_pairs, key=lambda uv: (
        not any(r[3] == primary_query for r in directed[uv] + directed[(uv[1], uv[0])]), uv))
    chosen, selected = [], set()

    def add(row):
        if row[0] not in selected and len(chosen) < 32:
            chosen.append(row)
            selected.add(row[0])

    cycle_examples = []
    for u, v in ordered_cycles[:3]:
        pair = []
        for edge in ((u, v), (v, u)):
            row = min(directed[edge], key=lambda r: (r[3] != primary_query, r[1] != "heterogeneous", r[2:5], r[0]))
            add(row)
            pair.append(row[0])
        cycle_examples.append(pair)
    # Two residual-size endpoints in each of the twelve stage/source cells.
    for stage in ("p0", "expanded", "heterogeneous"):
        for source in SOURCES:
            candidates = sorted([r for r in rows if r[1] == stage and r[2] == source],
                                key=lambda r: (Fraction(vectors[r[5]][8]), r[3], r[4], r[0]))
            if candidates:
                add(candidates[0])
                add(candidates[-1])
    # Fill remaining slots with unseen directed vector edges, then any remaining row.
    shown_edges = {(r[5], r[6]) for r in chosen}
    for row in rows:
        if (row[5], row[6]) not in shown_edges:
            add(row)
            shown_edges.add((row[5], row[6]))
        if len(chosen) == 32:
            break
    for row in rows:
        add(row)
    used = {r[index] for r in chosen for index in (5, 6)}
    common["vectors"] = [[identifier, vector] for identifier, vector in common["vectors"] if identifier in used]
    common["strict_relations"] = chosen
    common["prompt_sampling"] = dict(total_strict_requirements=len(rows), shown_requirements=len(chosen),
        selection="up to three existing two-cycles; two residual-size endpoints per stage/source cell; unseen directed vector edges to32",
        full_union_used_for_actual_training_evaluation=True)
    # Only the Witness condition will be told the directed-cycle interpretation.
    return common, dict(selected_relation_ids=[r[0] for r in chosen],
                        discovered_two_cycle_classes=len(cycle_pairs), selected_two_cycles=cycle_examples)


def make_prompt(context, condition, round_number, batch, feedback=None):
    common, sampling = representative_view(context)
    rule_only = condition == "relations_rule_only"
    if rule_only:
        # Rule-only has the same base9 table but no structural synthesis interface.
        common["library"]["operations"] = {}
        common["library"]["max_features"] = 0
    task = f"""You are the offline heuristic-program synthesis component of a controlled experiment.
Use ONLY the TRAIN evidence printed below. This is a pure JSON completion: do not call ANY tool,
inspect a file, browse, execute code, ask a question, or access the workspace. The complete permitted
input is this stdin text. Return only one JSON object conforming to the provided output schema.

Generate exactly EIGHT diverse, deterministic programs for condition {condition}, round {round_number},
independent batch {batch}. Every program must have exactly name, features, rule, rationale. Do not
return id or score_expression inside a program. Feature expression trees must use the actual library
and preserve typed argument arity: root/available have args=[], const has only op/value, all others
have op/args. Number-returning features: at most6,48 expression nodes,depth8. Rule: <=2000 chars,
<=256 AST nodes; only declared numeric feature variables and min/max/abs, arithmetic, comparisons,
boolean operators and numeric conditional expressions. No Python attributes, loops, imports, power,
indexing, custom op, feature references inside expression trees, strings in rules, oracle or LLM calls.

{ 'CORE RULE-ONLY CONTROL: every features array MUST be []. Use only the nine base variables. You may refine scoring rules but must not add any representation.' if rule_only else 'JOINT SYNTHESIS: invent a small number of informative Number features from the SAME typed graph-operation library, together with their scoring rules. Do not merely rename an unchanged base feature. Some programs may deliberately use zero added features as cost-aware candidates.' }

Higher score is preferred. Infer reusable structure-to-decision relationships rather than memorizing
source labels, contact IDs, geometry, epoch, config tags or the fixed340/1200/150 setting. Numeric
normalization coefficients are allowed; a gap-value lookup, explicit gap-literal branch or exact
weight/duration equality memorization is forbidden. Guard every denominator with a generic positive
offset or max. Counts and weights have different scales; ranking must remain finite for empty/small
neighborhoods and changing active sets. Dynamic active-set evaluation and feature computation are
charged within the same total CPU budget. A score_slice evaluates only named features used in rule.

The task is complete72-hour feasible schedule quality, also specification fit and actual feature cost.
Inclusion-value labels are offline restricted P/F/X evidence, not guaranteed good B&B pivot labels.
Do not assume fitting a patch certificate improves the final schedule. Expensive induced_edges on
all available vertices may be quadratic; greedy/cover on a root-conditioned global residual set may
also dominate the full solve. Provide genuine diversity in structural reach, cheap approximations,
normalization and rule form, balancing local-search/repair usefulness with full-graph cost. The same
frozen program is used without online certificate calls or re-synthesis when constraints change.

Your rationale must briefly explain the decision mechanism, structural reach and computation risk.
Do not claim an advantage has been measured. All performance feedback, if present, is TRAIN only.
"""
    body = dict(common_TRAIN_input=common)
    if condition == "witness_joint":
        body["certified_representation_conflict_and_structural_witness"] = context["witness_only"]
        task += "\nWITNESS GUIDANCE: an exact full-base9 directed cycle identifies information that a rule-only pointwise score cannot satisfy. Follow the saved structural evidence toward missing distinctions. The shown one-hop Q/T statistics are unchanged and do not repair this case. Broader root-conditioned residual features may distinguish it, but no hand-written repaired feature or outcome is supplied.\n"
    if feedback is not None:
        body["one_allowed_TRAIN_feedback_round"] = feedback
        task += "\nThis is the one permitted feedback round. Return eight new or substantively improved programs, preserving the same language and computation limits. Feedback belongs only to this condition, not other arms.\n"
    task += "\nSELF-CONTAINED INPUT JSON:\n" + encoded(body) + "\n"
    return task, sampling


def prepare(args):
    root = args.output_root.resolve()
    context_path = root / "context" / "train_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    profile = json.loads((root / "context" / "train_context_profile.json").read_text(encoding="utf-8"))
    require(digest(context_path) == profile["context_sha256"], "Frozen TRAIN context changed")
    require(args.round in (1, 2) and args.batch in (0, 1), "Only two rounds and two independent batches are permitted")
    feedback = None
    if args.round == 2:
        require(args.feedback is not None, "Round2 requires explicit TRAIN-only feedback")
        feedback = json.loads(args.feedback.read_text(encoding="utf-8"))
        require(feedback.get("split") == "TRAIN" and set(feedback.get("source_ids", [])) <= set(SOURCES)
                and feedback.get("source_ids"), "Feedback must explicitly name only the four TRAIN sources")
        require(feedback.get("arm") == args.condition, "Feedback may not disclose other conditions' outcomes")
    else:
        require(args.feedback is None, "Initial generation must not receive performance feedback")
    call_id = f"{args.condition}.r{args.round}.b{args.batch}"
    folder = root / "llm_calls" / call_id
    require(not folder.exists(), "A planned call cannot be overwritten or silently retried")
    prompt, sampling = make_prompt(context, args.condition, args.round, args.batch, feedback)
    folder.mkdir(parents=True)
    prompt_path, schema_path = folder / "prompt.txt", folder / "response_schema.json"
    prompt_path.write_text(prompt, encoding="utf-8")
    freeze_json(schema_path, response_schema(args.condition, args.round, args.batch))
    empty_cwd = Path(tempfile.mkdtemp(prefix="cipheur-llm-isolated-"))
    executable = args.cli_executable or shutil.which("codex")
    require(executable is not None, "Native Codex executable not found")
    argv = [str(executable), "exec", "--ignore-user-config", "--ignore-rules", "--model", MODEL,
        "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "--json", "--color", "never",
        "--cd", str(empty_cwd), "--output-schema", str(schema_path), "-o", str(folder / "response.json")]
    config = dict(model_reasoning_effort=EFFORT, web_search="disabled", project_doc_max_bytes=0,
                  developer_instructions="Pure JSON synthesis. Only stdin evidence is permitted. No tools, browsing, filesystem reads or writes, shell, plans or subagents. Return exactly the requested JSON.")
    disabled = ("shell_tool", "unified_exec", "shell_snapshot", "apps", "plugins", "browser_use",
                "browser_use_external", "computer_use", "in_app_browser", "multi_agent", "memories",
                "hooks", "code_mode_host", "view_image", "image_generation", "workspace_dependencies",
                "skill_search", "skill_mcp_dependency_install", "sleep_tool", "goals")
    for feature in disabled:
        config["features." + feature] = False
    config["features.skip_host_skill_discovery"] = True
    for key, value in config.items():
        argv.extend(["-c", key + "=" + json.dumps(value)])
    argv.append("-")
    plan = dict(call_id=call_id, condition=args.condition, round=args.round, batch=args.batch,
        candidates_requested=8, argv=argv, working_directory=str(empty_cwd), stdin_path=str(prompt_path),
        stdout_path=str(folder / "events.jsonl"), stderr_path=str(folder / "stderr.txt"),
        response_path=str(folder / "response.json"), receipt_path=str(folder / "execution_receipt.json"),
        model_requested=MODEL, reasoning_effort_requested=EFFORT,
        model_observed="unknown until actual metadata", prompt_sha256=digest(prompt_path),
        schema_sha256=digest(schema_path), context_sha256=profile["context_sha256"],
        feedback_sha256=digest(args.feedback) if args.feedback else None,
        prompt_bytes=len(prompt.encode("utf-8")), prompt_sampling=sampling,
        isolation="Fresh empty tempcwd; user config/rules ignored; available features disabled; read-only; any tool event rejected at ingest",
        actual_invocation_owner="root only; this script does not call the model")
    freeze_json(folder / "call_plan.json", plan)
    print(encoded(dict(call_plan=str(folder / "call_plan.json"), call_id=call_id, prompt_bytes=plan["prompt_bytes"])))


def event_audit(path):
    items, usage, models, errors, diagnostics = [], [], set(), [], []
    completed = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line)
        event_type = event.get("type", "")
        if event_type == "turn.completed":
            completed += 1
            usage.append(event.get("usage", {}))
        if event_type in ("error", "turn.failed"):
            errors.append(dict(line=line_number, event=event))
        item = event.get("item")
        if isinstance(item, dict):
            if item.get("type") == "error":
                # CLI configuration/startup diagnostics are status messages,
                # not tool actions. Keep them visible without calling them tools.
                diagnostics.append(dict(line=line_number, item=item))
            elif item.get("type") not in ("agent_message", "reasoning"):
                items.append(dict(line=line_number, type=item.get("type"), id=item.get("id")))
        # Never mine model names from model-authored message text or rationales.
        for metadata in (event, event.get("response"), event.get("session"), event.get("thread"), event.get("turn")):
            if isinstance(metadata, dict):
                for key in ("model", "model_name", "model_id", "resolved_model"):
                    if isinstance(metadata.get(key), str):
                        models.add(metadata[key])
    usage_sum = defaultdict(int)
    for item in usage:
        for key, value in item.items():
            if isinstance(value, int):
                usage_sum[key] += value
    return dict(turns_completed=completed, tool_events=items,
                tool_call_count=len({item["id"] or str(item["line"]) for item in items}), diagnostics=diagnostics,
                usage_records=usage, usage_sum=dict(usage_sum), errors=errors,
                model_observed=sorted(models) if models else "unknown",
                model_observed_policy="Only emitted CLI metadata; never infer from requested label")


def run_planned(args):
    """Root-only execution entry point; exactly one invocation per planned call."""
    root = args.output_root.resolve()
    folders = [args.call_directory.resolve()] if args.call_directory else [
        p for p in sorted((root / "llm_calls").iterdir())
        if p.name.endswith(f".r{args.round}.b0") or p.name.endswith(f".r{args.round}.b1")]
    require(folders and 1 <= args.workers <= 6, "Choose existing plans and1..6workers")
    plans = []
    for folder in folders:
        plan = json.loads((folder / "call_plan.json").read_text(encoding="utf-8"))
        require(not Path(plan["receipt_path"]).exists(), "Call already started; do not replay: " + plan["call_id"])
        require(digest(plan["stdin_path"]) == plan["prompt_sha256"], "Planned prompt changed")
        require(digest(folder / "response_schema.json") == plan["schema_sha256"], "Planned schema changed")
        require(not any(Path(plan["working_directory"]).iterdir()), "Model cwd must start empty")
        plans.append(plan)

    def invoke(plan):
        receipt_path = Path(plan["receipt_path"])
        receipt = dict(call_id=plan["call_id"], state="running", argv=plan["argv"],
                       prompt_sha256=plan["prompt_sha256"], started_unix=time.time(), invocation_owner="root")
        # Exclusive creation records budget consumption before issuing a real request.
        with receipt_path.open("x", encoding="utf-8") as handle:
            handle.write(encoded(receipt))
        started = time.perf_counter()
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            with Path(plan["stdout_path"]).open("wb") as stdout, Path(plan["stderr_path"]).open("wb") as stderr:
                process = subprocess.Popen(plan["argv"], stdin=subprocess.PIPE, stdout=stdout,
                                           stderr=stderr, cwd=plan["working_directory"], env=env)
                receipt["pid"] = process.pid
                receipt_path.write_text(encoded(receipt), encoding="utf-8")
                try:
                    process.communicate(Path(plan["stdin_path"]).read_bytes(), timeout=args.timeout_seconds)
                    receipt.update(exit_code=process.returncode, state="completed" if process.returncode == 0 else "failed")
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    receipt.update(exit_code=process.returncode, state="failed", timeout=True)
        except Exception as error:
            receipt.update(exit_code=None, state="failed", error=str(error))
        receipt.update(wall_seconds=time.perf_counter() - started, finished_unix=time.time())
        receipt_path.write_text(encoded(receipt) + "\n", encoding="utf-8")
        print(encoded({key: receipt[key] for key in ("call_id", "state", "exit_code", "wall_seconds")}), flush=True)
        return receipt

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(invoke, plans))
    if any(r["exit_code"] != 0 for r in results):
        raise SystemExit(1)


def program_policy(program, rule_only):
    if str(PROJECT) not in sys.path:
        sys.path.insert(0, str(PROJECT))
    from cipheur.graph_features import FeatureRuleProgram
    parsed = FeatureRuleProgram.from_dict(program)
    require(not rule_only or not parsed.features, "Rule-only cannot add features")
    # Generic coefficients are allowed. These checks prohibit value-lookup shortcuts.
    tree = ast.parse(parsed.rule, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            literals = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant)]
            require(not (names & {"station_gap", "satellite_gap"} and literals),
                    "Gap-literal comparison is a forbidden configuration lookup")
            if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
                require(not (names & {"weight", "duration"} and literals),
                        "Exact weight/duration equality lookup is forbidden")
    return parsed.to_dict()


def ingest(args):
    folder = args.call_directory.resolve()
    plan = json.loads((folder / "call_plan.json").read_text(encoding="utf-8"))
    require(digest(plan["stdin_path"]) == plan["prompt_sha256"], "Prompt changed after planning")
    require(digest(folder / "response_schema.json") == plan["schema_sha256"], "Schema changed after planning")
    receipt_path = folder / "execution_receipt.json"
    require(receipt_path.exists(), "Root execution receipt is required")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    audit = event_audit(folder / "events.jsonl")
    gate_errors = []
    if receipt.get("exit_code") != 0:
        gate_errors.append("nonzero or unavailable exit code")
    if audit["tool_call_count"]:
        gate_errors.append("tool events contaminate the pure stdin-only generation")
    if audit["turns_completed"] != 1 or audit["errors"]:
        gate_errors.append("expected one completed turn and no CLI error/failed turn")
    provenance = dict(call_id=plan["call_id"], prompt_sha256=plan["prompt_sha256"],
        context_sha256=plan["context_sha256"], response_sha256=digest(folder / "response.json") if (folder / "response.json").exists() else None,
        eventlog_sha256=digest(folder / "events.jsonl"), receipt_sha256=digest(receipt_path),
        model_requested=plan["model_requested"], model_observed=audit["model_observed"],
        reasoning_effort_requested=plan["reasoning_effort_requested"], usage=audit["usage_sum"],
        tool_call_count=audit["tool_call_count"], split="TRAIN", source_ids=list(SOURCES))
    valid, rejected = [], []
    if not gate_errors:
        try:
            response = json.loads((folder / "response.json").read_text(encoding="utf-8"))
            require(set(response) == {"condition", "round", "batch", "programs"}, "Unexpected response keys")
            require(all(response[key] == plan[key] for key in ("condition", "round", "batch")), "Response call identity differs")
            require(isinstance(response["programs"], list) and len(response["programs"]) == 8, "Exactly8 requested slots required")
            for slot, proposed in enumerate(response["programs"]):
                identifier = plan["call_id"] + ".s" + str(slot)
                try:
                    program = program_policy(proposed, plan["condition"] == "relations_rule_only")
                    fingerprint = hashlib.sha256(encoded(dict(features=program["features"], rule=program["rule"])).encode()).hexdigest()
                    valid.append(dict(id=identifier, arm=plan["condition"], round=plan["round"], batch=plan["batch"],
                                      slot=slot, program=program, program_content_sha256=fingerprint, provenance=provenance))
                except Exception as error:
                    rejected.append(dict(id=identifier, slot=slot, reason=str(error), original_proposed_program=proposed))
        except Exception as error:
            gate_errors.append("invalid response: " + str(error))
            valid = []
    report = dict(audit_version=2, call_id=plan["call_id"], candidates_requested=8, valid_candidates=len(valid),
                  gate_errors=gate_errors, rejected=rejected, event_audit=audit, provenance=provenance,
                  silent_replacement=False, all_failed_slots_consume_original_budget=True)
    freeze_json(folder / "ingest_report.v2.json", report)
    freeze_json(folder / "validated_bank.v2.json", dict(version="stk_full_llm_v1_call_bank_audit2", selection_split="TRAIN", programs=valid))
    print(encoded(dict(call_id=plan["call_id"], valid=len(valid), rejected=len(rejected), gate_errors=gate_errors)))


def merge(args):
    root = args.output_root.resolve()
    programs, calls = [], []
    for folder in sorted((root / "llm_calls").iterdir()):
        report_path = folder / "ingest_report.v2.json"
        bank_path = folder / "validated_bank.v2.json"
        if not report_path.exists():
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        calls.append(dict(call_id=report["call_id"], requested=8, valid=report["valid_candidates"],
                          gate_errors=report["gate_errors"], ingest_report_sha256=digest(report_path)))
        programs.extend(bank["programs"])
    require(len(calls) <= 12, "Maximum twelve actual planned calls")
    require(len({p["id"] for p in programs}) == len(programs), "Duplicate candidate ID")
    for condition in CONDITIONS:
        require(sum(call["call_id"].startswith(condition + ".") for call in calls) <= 4,
                "At most4 calls per condition")
    by_content = defaultdict(list)
    for program in programs:
        by_content[(program["arm"], program["program_content_sha256"])].append(program["id"])
    bank = dict(version="stk_full_llm_v1_real_cli_bank", selection_split="TRAIN", TEST_used_for_selection=False,
                model_requested=MODEL, reasoning_effort_requested=EFFORT, programs=programs, calls=calls,
                requested_slots=sum(c["requested"] for c in calls), valid_slots=len(programs),
                within_condition_duplicate_content=[ids for ids in by_content.values() if len(ids) > 1],
                duplicate_policy="Retain all paid slots and provenance; duplicates are not secretly replaced")
    # Each stage gets a new bank pathname, preserving all earlier artifacts.
    destination = args.bank_path or root / "banks" / ("real_cli_" + str(len(calls)) + "calls.audit2.json")
    freeze_json(destination, bank)
    print(encoded(dict(bank=str(destination), requested_slots=bank["requested_slots"], valid_slots=len(programs))))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output-root", type=Path, default=ROOT)
    prep.add_argument("--condition", choices=CONDITIONS, required=True)
    prep.add_argument("--round", type=int, default=1)
    prep.add_argument("--batch", type=int, choices=(0, 1), required=True)
    prep.add_argument("--feedback", type=Path)
    prep.add_argument("--cli-executable")
    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("--call-directory", type=Path, required=True)
    merge_parser = sub.add_parser("merge")
    merge_parser.add_argument("--output-root", type=Path, default=ROOT)
    merge_parser.add_argument("--bank-path", type=Path)
    run_parser = sub.add_parser("run-planned", help="Root-only real native CLI execution; no automatic retry")
    run_parser.add_argument("--output-root", type=Path, default=ROOT)
    run_parser.add_argument("--call-directory", type=Path)
    run_parser.add_argument("--round", type=int, choices=(1, 2), default=1)
    run_parser.add_argument("--workers", type=int, default=3)
    run_parser.add_argument("--timeout-seconds", type=float, default=1800)
    args = parser.parse_args()
    {"prepare": prepare, "ingest": ingest, "merge": merge, "run-planned": run_planned}[args.command](args)


if __name__ == "__main__":
    main()
