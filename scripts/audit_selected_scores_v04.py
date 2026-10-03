"""TRAIN-only scalar-agreement audit and a source-backed mechanism figure.

Read the completed immutable TRAIN archive and prior TRAIN seed certificates.
No scheduling, conditional oracle, programme selection, or fresh/public outcome
reader is invoked. Every selected endpoint score is checked against both the
eager reference interpreter and the demanded compiled evaluator.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import tarfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cipheur.compiled import CompiledEvaluator
from cipheur.graph_features import FeatureRuleProgram, _FeatureState
from cipheur.model import Graph

BLUE, ORANGE, GRAY, INK, PURPLE = "#176B9B", "#D36B32", "#687782", "#243640", "#71559C"
MEMBERS = ("complete.json", "config.json", "execution.json", "candidate_bank.json",
           "training_contexts.jsonl", "information_repair.json", "assessments.json", "frozen_programs.json")
CHOICES = (("guided_v04", "Joint"), ("baseline", "Degree"), ("free_v03", "Free"),
           ("rule_v03", "Rule"), ("enumerated_v03", "Enum"), ("prior_guided_controls", "g03"))


def canonical_hash(value):
    # Same outer hash as _information_audit; Graph.digest uses its own format.
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_receipt(path):
    path = Path(path).resolve()
    try:
        name = path.relative_to(ROOT).as_posix()
    except ValueError:
        name = str(path)
    return {"path": name, "sha256": sha256(path.read_bytes()).hexdigest()}


def read_train_archive(path):
    objects, receipts = {}, {}
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            name = Path(member.name).name
            if not member.isfile() or name not in MEMBERS:
                continue
            if name in objects:
                raise ValueError("Ambiguous TRAIN archive member: " + name)
            raw = tar.extractfile(member).read()
            receipts[name] = {"member": member.name, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
            objects[name] = ([json.loads(line) for line in raw.splitlines() if line]
                             if name.endswith(".jsonl") else json.loads(raw))
    if set(objects) != set(MEMBERS):
        raise ValueError("Missing completed TRAIN members")
    frozen, execution = objects["frozen_programs.json"], objects["execution.json"]
    if not objects["complete.json"]["complete"] or frozen["test_accessed"] is not False:
        raise ValueError("Not a completed outcome-free TRAIN freeze")
    if frozen["selection_split"] != "train" or execution["test_outcomes_read"] is not False:
        raise ValueError("Non-TRAIN provenance")
    if execution["source"]["validation_and_test_outcomes_used"] is not False:
        raise ValueError("TRAIN selection used forbidden outcomes")
    for member, field in (("candidate_bank.json", "candidate_bank_sha256"), ("config.json", "config_sha256")):
        if receipts[member]["sha256"] != frozen[field]:
            raise ValueError("Immutable TRAIN freeze hash mismatch: " + member)
    runtime = {}
    for name in ("model.py", "graph_features.py", "compiled.py"):
        current = file_receipt(ROOT / "cipheur" / name)
        expected = execution["source_sha256"][name]
        if current["sha256"] != expected:
            raise ValueError("Runtime differs from immutable TRAIN source: " + name)
        runtime[name] = {**current, "matches_train_source": True}
    return objects, {"archive": file_receipt(path), "members": receipts, "runtime": runtime}


def reconstruct(objects, specifications):
    """Rebuild canonical endpoint bindings without regenerating a certificate."""
    endpoints, states, requirements = {}, {}, []
    actual_checked, actual_unknown = 0, 0
    epsilon = Fraction(objects["config.json"]["epsilon"])

    def append(graph, fixed, excluded, preferred, other, metadata):
        fixed, excluded = tuple(sorted(fixed)), tuple(sorted(excluded))
        active = graph.available(fixed, excluded)
        if preferred == other or not {preferred, other} <= active:
            raise ValueError("Requirement endpoints are not distinct feasible actions")
        digest = graph.digest()
        prefix = canonical_hash([digest, list(fixed), list(excluded)])
        if prefix not in states:
            states[prefix] = (graph, set(active), fixed, excluded)
        ids = []
        for node in (preferred, other):
            oid = prefix + ":" + node
            binding = {"prefix": prefix, "node": node, "graph_digest": digest,
                       "fixed": list(fixed), "excluded": list(excluded), "active_count": len(active)}
            if oid in endpoints and endpoints[oid] != binding:
                raise ValueError("Canonical occurrence collision")
            endpoints[oid] = binding
            ids.append(oid)
        requirements.append({"preferred": ids[0], "other": ids[1], "metadata": metadata})

    contexts = sorted(objects["training_contexts.jsonl"], key=lambda row: (row["pair_id"], row["side"]))
    for context in contexts:
        graph = Graph.from_dict(context["graph"])
        for state in context["states"]:
            expected_prefix = canonical_hash([graph.digest(), sorted(state["fixed"]), sorted(state["excluded"])])
            if state["id"] != expected_prefix:
                raise ValueError("Saved reached state is not its canonical boundary")
            for delta in state["differences"]:
                lower, upper = Fraction(delta["lower_exact"]), Fraction(delta["upper_exact"])
                if lower > upper:
                    raise ValueError("Invalid saved difference enclosure")
                preferred = delta["a"] if lower > epsilon else delta["b"] if upper < -epsilon else None
                if preferred != delta["preferred"]:
                    raise ValueError("Saved actual strict label fails its exact sign test")
                if preferred is None:
                    actual_unknown += 1
                    continue
                other = delta["b"] if preferred == delta["a"] else delta["a"]
                append(graph, state["fixed"], state["excluded"], preferred, other,
                       {"kind": "cancelled_actual_action", "pair_id": context["pair_id"], "side": context["side"]})
                actual_checked += 1

    # This is the complete original source TRAIN universe, not just 66 sampled contexts.
    training_digests = set(objects["execution.json"]["source"]["training_graph_digests"])
    prior_checked = 0
    for spec in specifications:
        for side in ("left", "right"):
            graph = Graph.from_dict(spec[side])
            if graph.digest() not in training_digests:
                raise ValueError("Prior certificate is not from the source TRAIN universe")
            preferred = spec[side + "_preferred"]
            other = spec["b"] if preferred == spec["a"] else spec["a"]
            positive = spec["bounds"][side + ("_a" if preferred == spec["a"] else "_b")]
            negative = spec["bounds"][side + ("_b" if preferred == spec["a"] else "_a")]
            if Fraction(positive["lower_exact"]) <= Fraction(negative["upper_exact"]) + Fraction(spec["epsilon"]):
                raise ValueError("Prior label lacks its saved exact strict inequality")
            append(graph, spec["fixed"], spec["excluded"], preferred, other,
                   {"kind": "prior_training_certificate", "id": spec.get("id"), "side": side})
            prior_checked += 1
    if requirements != objects["information_repair.json"]["requirements"]:
        raise ValueError("Reconstructed TRAIN requirements differ in values or order")
    if len(endpoints) != objects["information_repair.json"]["occurrences"]:
        raise ValueError("Occurrence denominator differs from frozen information audit")
    return endpoints, states, requirements, {"actual_strict_requirements": actual_checked,
        "prior_strict_requirements": prior_checked, "non_strict_actual_comparisons": actual_unknown,
        "original_train_digest_count": len(training_digests), "audited_contexts": len(contexts),
        "reconstructed_requirements_sha256": canonical_hash(requirements)}


def selected_entries(objects):
    assessments = objects["assessments.json"]
    by_id = {entry["id"]: entry for entry in assessments}
    bank = {entry["id"]: entry for entry in objects["candidate_bank.json"]}
    if len(by_id) != len(assessments) or set(by_id) != set(bank):
        raise ValueError("Candidate assessment identity mismatch")
    for candidate_id, entry in bank.items():
        if entry["program"] != by_id[candidate_id]["program"]:
            raise ValueError("Assessment programme changed")
        if canonical_hash(entry["program"]) != entry["program_sha256"]:
            raise ValueError("Candidate AST receipt mismatch")
    frozen = objects["frozen_programs.json"]
    result = []
    for arm, label in CHOICES:
        entry = by_id[frozen["selection"][arm]["selected_id"]]
        if entry["program"] != frozen["programs"][arm]:
            raise ValueError("Selected AST differs from original TRAIN freeze")
        result.append({**entry, "audit_label": label, "frozen_arm_selection": True})
    guards = [entry for entry in assessments if entry["program"]["name"] == "v04_retained_guard_64"]
    if len(guards) != 1:
        raise ValueError("Missing unique prespecified guard64 proposal")
    result.append({**guards[0], "audit_label": "Guard64", "frozen_arm_selection": False})
    return result


def classify(preferred, other):
    # No objective tolerance and no ID tie-break: these are strict numeric orders.
    return "agree" if preferred > other else "tie" if preferred == other else "violate"


def audit_scores(entries, endpoints, states, requirements):
    by_state = defaultdict(list)
    for oid, binding in endpoints.items():
        by_state[binding["prefix"]].append((oid, binding["node"]))
    output, checked = [], 0
    for entry in entries:
        started = perf_counter()
        program = FeatureRuleProgram.from_dict(entry["program"])
        scores, feature_values = {}, {}
        for prefix in sorted(by_state):
            graph, active, _, _ = states[prefix]
            reference = _FeatureState(graph, active, None)
            compiled = CompiledEvaluator(graph, program, active, score_slice=True)
            for oid, node in sorted(by_state[prefix]):
                values = reference.feature_values(program, node)
                eager, demanded = program._rank(values), compiled.score(node)
                if not math.isfinite(eager) or eager != demanded:
                    raise AssertionError(f"Interpreter/compiled score mismatch: {entry['id']} {oid}")
                scores[oid], feature_values[oid] = eager, values
                checked += 1
        counts = {"all": Counter(), "cancelled_actual_action": Counter(), "prior_training_certificate": Counter()}
        rows = []
        for index, requirement in enumerate(requirements):
            p, n = requirement["preferred"], requirement["other"]
            outcome = classify(scores[p], scores[n])
            counts["all"][outcome] += 1
            counts[requirement["metadata"]["kind"]][outcome] += 1
            rows.append({"requirement_index": index, "preferred": p, "other": n,
                         "metadata": requirement["metadata"], "score_preferred": scores[p],
                         "score_other": scores[n], "score_difference": scores[p] - scores[n], "outcome": outcome})
        summaries = {}
        for kind, count in counts.items():
            total = sum(count.values())
            summaries[kind] = {"requirements": total, **{key: count[key] for key in ("agree", "tie", "violate")},
                               "strict_agreement_fraction": count["agree"] / total if total else None}
        output.append({**entry, "declared_interface_acyclic": not entry["contradictory"],
                       "agreement": summaries, "endpoint_scores": scores, "endpoint_feature_values": feature_values,
                       "requirement_scores": rows, "audit_elapsed_seconds": perf_counter() - started,
                       "interpreter_compiled_exact_score_parity": True})
        print(json.dumps({"scored": entry["audit_label"], "agreement": summaries["all"],
                          "elapsed_seconds": output[-1]["audit_elapsed_seconds"]}), flush=True)
    return output, checked


def figure(data, prefix):
    """One bank scatter and paired selected-rule diagnostic columns; no CI fiction."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    for path in (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")):
        if path.exists():
            font_manager.fontManager.addfont(str(path))
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
        "axes.titlesize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
        "axes.edgecolor": GRAY, "axes.linewidth": .7, "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.facecolor": "white"})
    fig = plt.figure(figsize=(7, 2.1))
    bank_ax = fig.add_axes([.085, .34, .365, .49])
    agreement_ax = fig.add_axes([.575, .34, .155, .49])
    regret_ax = fig.add_axes([.80, .34, .17, .49], sharey=agreement_ax)
    fig.text(.085, .96, "(a) Fixed TRAIN bank: 93 programmes", ha="left", va="top", fontsize=9, fontweight="bold")
    fig.text(.51, .96, "(b) Fixed rule audits: 824 requirements", ha="left", va="top", fontsize=9, fontweight="bold")
    for ax in (bank_ax, agreement_ax, regret_ax):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#E2E7EA", linewidth=.55)
        ax.set_axisbelow(True)
        ax.tick_params(length=3, width=.7, pad=2)
    for row in data["bank_assessments"]:
        cyclic = row["contradictory"]
        color = PURPLE if row["arm"] == "guided_v04" else GRAY
        bank_ax.scatter(row["macro_relative_work"], 100 * row["macro_train_quality"],
                        s=22, marker="x" if cyclic else "o", color=ORANGE if cyclic else color,
                        edgecolors=None if cyclic else BLUE, linewidths=.65, alpha=.8, zorder=3)
    bank_ax.set_xscale("log")
    bank_ax.set_xlim(.5, 150)
    bank_ax.set_ylim(74, 101.5)
    bank_ax.set_xticks([1, 10, 100], labels=["1", "10", "100"])
    bank_ax.set_yticks([75, 85, 95, 100])
    bank_ax.set_xlabel("Relative work (log scale)", labelpad=3)
    bank_ax.set_ylabel("TRAIN quality (%)", labelpad=3)
    for label, text, location in (("Joint", "Frozen joint", (2.0, 91)), ("Guard64", "Guard64", (27, 88))):
        row = next(r for r in data["selected_audits"] if r["audit_label"] == label)
        xy = (row["macro_relative_work"], 100 * row["macro_train_quality"])
        bank_ax.scatter(*xy, s=65 if label == "Joint" else 42, marker="*" if label == "Joint" else "D",
                        facecolors=PURPLE if label == "Joint" else "white", edgecolors=PURPLE,
                        linewidths=.8, zorder=5)
        bank_ax.annotate(text, xy=xy, xytext=location, color=PURPLE, fontsize=9,
                         ha="left", arrowprops={"arrowstyle": "-", "color": PURPLE, "linewidth": .7})
    rows = data["selected_audits"]
    agreement_ax.set_ylim(-.6, len(rows) - .4)
    agreement_ax.invert_yaxis()
    agreement_ax.set_xlim(0, 105)
    agreement_ax.set_xticks([0, 50, 100])
    agreement_ax.set_yticks(range(len(rows)), labels=[r["audit_label"] for r in rows])
    agreement_ax.tick_params(axis="y", length=0, pad=6)
    regret_ax.tick_params(axis="y", left=False, labelleft=False)
    regret_ax.set_xlim(-.12, 4.7)
    regret_ax.set_xticks([0, 2, 4])
    agreement_ax.set_xlabel("Agreement (%)", labelpad=3)
    regret_ax.set_xlabel("Pool regret bounds", labelpad=3)
    for y, row in enumerate(rows):
        color = PURPLE if row["arm"] == "guided_v04" else GRAY
        cyclic = row["contradictory"]
        agreement_ax.scatter(100 * row["agreement"]["all"]["strict_agreement_fraction"], y, s=36,
                             marker="x" if cyclic else "o", color=ORANGE if cyclic else color,
                             edgecolors=None if cyclic else BLUE, linewidths=.9, zorder=4)
        lo, hi = row["macro_actual_regret_lower"], row["macro_actual_regret_upper"]
        if lo is None or hi is None:
            regret_ax.text(2.2, y, "missing", va="center", ha="center", color=GRAY)
            continue
        if not 0 <= lo <= hi:
            raise ValueError("Invalid saved reached finite-pool regret enclosure")
        regret_ax.hlines(y, lo, hi, colors=color, linewidth=1)
        regret_ax.plot([lo, hi], [y, y], linestyle="none", marker="|", markersize=6,
                       markeredgewidth=1, color=color)
    # Legends state semantics; comparison-arm cyclic interfaces are not silently rejected.
    handles = [Line2D([], [], marker="o", color="none", markerfacecolor=PURPLE, markeredgecolor=BLUE,
                      markersize=5, label="Guided"),
               Line2D([], [], marker="o", color="none", markerfacecolor=GRAY, markeredgecolor=BLUE,
                      markersize=5, label="Control / DAG"),
               Line2D([], [], marker="x", color=ORANGE, linestyle="none", markersize=5,
                      label="Cyclic interface")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.065, .015), ncol=3,
               frameon=False, columnspacing=.8, handletextpad=.35)
    fig.text(.97, .047, "Bounds are not CIs", ha="right", va="center", color=GRAY, fontsize=9)
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(prefix.with_suffix(".pdf"))
    fig.savefig(prefix.with_suffix(".png"), dpi=300)
    plt.close(fig)
    return {"pdf": file_receipt(prefix.with_suffix(".pdf")),
            "png": file_receipt(prefix.with_suffix(".png")),
            "width_inches": 7, "height_inches": 2.1, "font": "Arial", "font_points": 9,
            "matplotlib_version": matplotlib.__version__}


def markdown(data):
    lines = ["# Frozen TRAIN scalar agreement and synthesis mechanisms", "",
        "This is a post-freeze TRAIN diagnostic. It changes no proposal, programme, eligibility rule, or selection; "
        "no fresh, public or held-out quality outcomes are read. Scalar agreement is a diagnostic, while the implemented "
        "guided/free/enumerated information gate tests acyclicity of the entire declared feature interface.", "",
        "## Evidence and reconstruction", "",
        f"The immutable archive contains {data['summary']['training_contexts']} contexts and 93 assessments. "
        f"All {data['summary']['requirements']} saved requirements reconstruct exactly, in saved order: "
        f"{data['reconstruction']['actual_strict_requirements']} actual-action requirements and "
        f"{data['reconstruction']['prior_strict_requirements']} prior TRAIN certificates. "
        f"There are {data['summary']['occurrences']} unique endpoint occurrences. "
        "Occurrence identity is compact-JSON SHA256([Graph.digest(), sorted(F), sorted(X)]) + ':' + vertex ID. "
        "Context JSONL completion order is sorted by (pair_id, side) before replaying state/difference order. "
        "Prior seed order, left then right, follows. Prior membership is checked against all recorded source TRAIN digests, "
        "not only the sampled context graphs. Every endpoint is feasible at its bound F/X, and each retained relation passes "
        "its saved exact Fraction sign inequality. No oracle or schedule is rerun.", "",
        "Numeric outcomes use the unchanged validated rule and native finite scores: preferred > other is strict agreement, "
        "equality is a tie, and preferred < other is violation. Objective epsilon and vertex-ID tie-breaking do not redefine "
        "scalar agreement. Eager reference and demanded compiled endpoint scores agree exactly for every queried occurrence. "
        "Rates count saved requirement rows, including repeated/shared-state evidence; they are not independent test observations "
        "or estimates of agreement on all feasible actions. An actual-action requirement may be counterfactual for another audited "
        "programme; only the saved reached regret statistic is restricted to that programme's own recorded rollout.", "",
        "## Seven fixed programme audits", "",
        "Six are the original frozen arm selections. Guard64 is a fixed prespecified proposal, audited as a diagnostic rather "
        "than newly selected. The primary-only guided ablation is the identical primary AST and is not counted twice.", "",
        "| Programme | DAG | All agree/tie/violate (824) | Actual agree/tie/violate (788) | Prior agree/tie/violate (36) | TRAIN quality | Relative work | Reached pool-regret bounds | Reached states | Unknown comparisons |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in data["selected_audits"]:
        def triple(kind):
            a = row["agreement"][kind]
            return f"{a['agree']}/{a['tie']}/{a['violate']}"
        lines.append(f"| {row['audit_label']} | {'acyclic' if row['declared_interface_acyclic'] else 'cyclic'} | "
            f"{triple('all')} | {triple('cancelled_actual_action')} | {triple('prior_training_certificate')} | "
            f"{100*row['macro_train_quality']:.3f}% | {row['macro_relative_work']:.3f} | "
            f"[{row['macro_actual_regret_lower']:.6f}, {row['macro_actual_regret_upper']:.6f}] | "
            f"{row['reached_audited_states']} | {row['unknown_comparisons']} |")
    joint = next(row for row in data["selected_audits"] if row["audit_label"] == "Joint")
    guard = next(row for row in data["selected_audits"] if row["audit_label"] == "Guard64")
    prior = joint["agreement"]["prior_training_certificate"]
    actual = joint["agreement"]["cancelled_actual_action"]
    lines += ["", "## What these diagnostics establish", "",
        f"The frozen joint rule agrees with {prior['agree']}/{prior['requirements']} prior requirements "
        f"({100*prior['strict_agreement_fraction']:.2f}%) but {actual['agree']}/{actual['requirements']} "
        f"actual-action requirements ({100*actual['strict_agreement_fraction']:.2f}%). This is a descriptive difference "
        "within the saved TRAIN evidence, not a statistical generalization claim: the smaller prior bank and the actual-state "
        "bank have different constructions, and requirement rows share graphs and occurrences. "
        f"Guard64 has {guard['agreement']['all']['agree']}/824 strict agreements versus "
        f"{joint['agreement']['all']['agree']}/824 for the joint rule, but uses "
        f"{guard['macro_relative_work']/joint['macro_relative_work']:.2f} times its measured work and has lower saved "
        f"TRAIN quality ({100*guard['macro_train_quality']:.3f}% versus {100*joint['macro_train_quality']:.3f}%). "
        "Both declared interfaces are acyclic. This demonstrates why representation feasibility, a particular scalar rule's "
        "orders, and measured scheduling utility are distinct diagnostics; it does not identify the cause of their differences "
        "or authorize a new selection. The seven reached finite-pool regret intervals overlap, so they do not support a strict "
        "regret ranking among these rules.", "",
        "The observed gap between an acyclic interface and imperfect scalar agreement directly distinguishes "
        "existence of an unrestricted finite fitting score from the frozen bounded rule's actual orders. It does not establish "
        "that replacing that rule would improve fresh scheduling. Quality is the equal-family mean reward divided by the best "
        "completed bank reward per context, a feasible empirical comparator. Work is relative to the degree baseline; incomplete "
        "runs retain zero quality and the declared penalty. The original measured quality/work/regret assessments are reused "
        "without recomputation or outcome filtering. Regret endpoints are averaged certified finite-pool enclosures with "
        "full-context mean-weight normalization and programme-specific reached coverage; they are not confidence intervals, "
        "point estimates, all-action regret, or whole-schedule loss bounds.", "",
        "## Main-ready figure", "",
        "`paper/figures/train_mechanisms_v04.pdf` is a 7×2.1-inch vector figure with Arial 9-point text; its PNG is an inspection "
        "preview. Panel (a) preserves all 93 measured TRAIN quality/work points, including incompletion penalties, and marks "
        "declared-interface acyclicity independently of proposal arm. Panel (b) aligns each fixed rule's strict agreement with "
        "its saved reached finite-pool regret enclosure. No midpoint is plotted as an estimate. All 93 assessment records, all "
        "endpoint scores/features and all 824 classification rows per audited programme are preserved in the JSON.", "",
        "**Caption proposal.** TRAIN evidence separates representation, scalar ranking and schedule-aware selection. "
        "(a) All 93 frozen-bank proposals: quality relative to the best completed bank schedule versus relative measured work "
        "(log scale). Blue rims denote acyclic declared interfaces; orange crosses denote cyclic interfaces retained in separate "
        "comparator arms. (b) Six original arm selections and the fixed Guard64 diagnostic: strict score agreement on 824 "
        "saved requirements (788 actual-action and 36 prior), alongside programme-specific reached finite-pool regret enclosures. "
        "The enclosures are not CIs; "
        "coverage differs. All quantities are TRAIN diagnostics, without a fresh-quality claim.", "",
        "## Provenance and limits", "",
        "The TRAIN and seed input hashes, immutable member hashes and current matching runtime hashes are in the JSON. "
        "The reconstruction and interpreter/compiled parity checks guard this audit; they do not replace the quotient theorem "
        "or demonstrate generalization. The bank and selected-programme files remain unchanged.", "",
        f"Elapsed audit time: {data['summary']['audit_elapsed_seconds']:.2f} seconds. "
        f"Exact endpoint parity checks: {data['summary']['endpoint_score_parity_checks']}.", "",
        "```text", ".venv/Scripts/python.exe scripts/audit_selected_scores_v04.py", "```", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", default=str(ROOT / "experiments/runs/v04/relevance_train_v04_001.tar.gz"))
    parser.add_argument("--seeds", default=str(ROOT / "experiments/discovery/v03/seed_specifications.json"))
    parser.add_argument("--out-json", default=str(ROOT / "experiments/analysis/v04/selected_score_agreement.json"))
    parser.add_argument("--out-md", default=str(ROOT / "docs/SELECTED_SCORE_AGREEMENT_V04.md"))
    parser.add_argument("--figure-prefix", default=str(ROOT / "paper/figures/train_mechanisms_v04"))
    parser.add_argument("--no-figure", action="store_true")
    args = parser.parse_args(argv)
    started = perf_counter()
    objects, provenance = read_train_archive(args.archive)
    specs = json.loads(Path(args.seeds).read_text(encoding="utf-8"))
    endpoints, states, requirements, reconstruction = reconstruct(objects, specs)
    if len(requirements) != 824 or reconstruction["actual_strict_requirements"] != 788 or reconstruction["prior_strict_requirements"] != 36:
        raise ValueError("Unexpected frozen TRAIN requirement frame")
    entries = selected_entries(objects)
    scored, checked = audit_scores(entries, endpoints, states, requirements)
    result = {"version": "selected_scalar_agreement_v04_001", "scope": "post_freeze_TRAIN_diagnostic_only",
        "selection_changed": False, "new_oracle_calls": 0, "new_scheduling_runs": 0, "fresh_public_outcomes_read": False,
        "provenance": {**provenance, "seed_specifications": file_receipt(args.seeds), "audit_script": file_receipt(__file__)},
        "reconstruction": reconstruction, "occurrence_bindings": endpoints,
        "bank_assessments": objects["assessments.json"], "original_selection": objects["frozen_programs.json"]["selection"],
        "selected_audits": scored,
        "summary": {"training_contexts": len(objects["training_contexts.jsonl"]), "bank_candidates": len(objects["assessments.json"]),
                    "requirements": len(requirements), "occurrences": len(endpoints), "audited_programmes": len(scored),
                    "endpoint_score_parity_checks": checked, "audit_elapsed_seconds": perf_counter() - started,
                    "classification": "native strict > / == / <; no tolerance or ID tie-break",
                    "dag_gate_is_not_scalar_agreement": True, "bounds_are_not_confidence_intervals": True}}
    for path in (Path(args.out_json), Path(args.out_md)):
        path.parent.mkdir(parents=True, exist_ok=True)
    if not args.no_figure:
        result["figure_receipts"] = figure(result, args.figure_prefix)
    Path(args.out_json).write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    Path(args.out_md).write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"complete": True, "summary": result["summary"], "json": args.out_json,
                      "markdown": args.out_md, "figure": None if args.no_figure else args.figure_prefix}), flush=True)


if __name__ == "__main__":
    main()
