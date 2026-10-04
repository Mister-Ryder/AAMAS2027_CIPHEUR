"""Freeze deterministic V06 comparator banks without any candidate evaluation.

Eight fixed structural templates enumerate four feature-catalogue sizes and
two fixed coefficient blends. Eight base-nine rules remain a separate fixed
interface control. They are not randomized draws, experimental LLM authoring,
equal-compute comparators or data-blind inventions. The controller has already
audited TRAIN evidence, but no template is assessed or selected in this script.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Static grammar/schema verification only: no graph, reward, feature, fit or
# kernel function is called. This is an independent safe-expression validator.
from scripts.verify_matched_llm_v05 import normalized_program, canonical

STUDY = ROOT / "experiments/discovery/v06_controls_001"


def node(op, *args):
    return {"op": op, "args": list(args)}


def catalogue():
    neighbors = node("neighbors", node("root"))
    residual = node("difference", node("difference", node("available"), neighbors),
                    node("singleton", node("root")))
    return [
        {"name": "ng", "expression": node("greedy_independent_weight", neighbors)},
        {"name": "nu", "expression": node("clique_cover_weight", neighbors)},
        {"name": "rg", "expression": node("greedy_independent_weight", residual)},
        {"name": "ru", "expression": node("clique_cover_weight", residual)},
        {"name": "ne", "expression": node("count", node("induced_edges", neighbors))},
        {"name": "re", "expression": node("count", node("induced_edges", residual))},
    ]


def banks():
    features, structural = catalogue(), []
    # These coefficient/prefix choices are a fixed grammar enumeration. No
    # label, certificate, candidate score or old proposal is read here.
    for count in (2, 3, 4, 6):
        for blend, complement in ((0.25, 0.75), (0.75, 0.25)):
            rule = f"weight - {blend}*ng - {complement}*nu"
            if count == 3:
                rule += " + rg"
            if count >= 4:
                rule += f" + {blend}*rg + {complement}*ru"
            if count == 6:
                rule += (" + 0.125*ne/max(1,degree*(degree-1))"
                         " - 0.125*re/max(1,(remaining_count-degree-1)*(remaining_count-degree-2))")
            structural.append({"name": f"enum_struct_{count}_{str(blend).replace('.', '_')}",
                "features": features[:count], "rule": rule,
                "rationale": "Fixed catalogue-prefix/coefficient template, not empirical fitting or an experimental LLM authoring draw."})
    base_rules = [
        "weight", "weight/max(1,degree)", "weight/max(1,conflict_weight)",
        "weight-conflict_weight", "weight*(1+degree)", "weight+compatible_weight",
        "weight/max(1,duration)",
        "weight*(1+max_conflict_weight)/max(1,degree+station_gap+satellite_gap)",
    ]
    fixed = [{"name": f"fixed_base9_{i:02d}", "features": [], "rule": rule,
              "rationale": "Frozen classical/base-nine expression; a fixed-information-interface control, not a new authoring draw."}
             for i, rule in enumerate(base_rules)]
    for bank in (structural, fixed):
        normalized = [normalized_program(p) for p in bank]
        assert len(normalized) == 8
        assert len({canonical({k: p[k] for k in ("features", "rule")}) for p in normalized}) == 8
        bank[:] = normalized
    return {"enumerated_structural": structural, "fixed_base9": fixed}


def prepare():
    if STUDY.exists():
        raise ValueError("Preserve the original control freeze; no overwrite or replacement")
    groups = banks()
    payload = {"version": "v06_fixed_enumerated_controls_001",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_before_raw_LLM_candidate_assessment": True,
        "TRAIN_or_TEST_candidate_evaluations": 0, "raw_LLM_responses_read": 0,
        "experimental_LLM_authoring_calls": 0,
        "designed_after_TRAIN_evidence_audit": True,
        "generation": "Deterministic catalogue-prefix sizes2/3/4/6 × fixed blend0.25/0.75; no outcome-driven template selection.",
        "banks": groups,
        "degree_fixed_reference": {"name": "fixed_degree_reference", "features": [],
            "rule": "weight/max(1,degree)", "rationale": "Separate known classical Degree priority."},
        "assessment_contract": {"candidate_assessor": "cipheur.synthesis_study_v06.assess_candidate",
            "same_frozen_TRAIN_evidence_and_interface_gate": True,
            "same_frozen_shared_kernel_config_and_caps": True,
            "same_lexicographic_fit_quality_work_selector": True,
            "slots_per_bank": 8, "report_all_original_slots": True,
            "repeated_blocks": 4, "independent_authoring_draws": False,
            "repeat_scope": "The exact eight ASTs may be assessed four times for host/budget variability. Repeated blocks do not create32 independent proposals.",
            "empty_eligible_bank": "Retain empty result; no oracle, fallback, validation repair or extra template.",
            "degree_scope": "Degree is a separate fixed kernel reference, including when its base interface cannot pass the information gate."},
        "limits": {"additional_features": 6, "expression_nodes": 48, "expression_depth": 8},
        "attribution_limits": [
            "Enumerated assessed-slot-matched control, not random generation or matched model/token compute.",
            "Templates were written by the research controller after evidence auditing, without feature/fit/kernel assessment; this is not a claim of blind human/non-AI provenance.",
            "Base-nine unit-weight rules can coincide in ranking; static AST diversity is not semantic diversity or independent data.",
            "Structural catalogue prefixes vary capacity/cost; the six-feature entries share the same maximum capacity allowed to LLM proposals.",
            "Better than fixed-base rules alone establishes representation need, not unique LLM benefit."]}
    STUDY.mkdir(parents=True)
    raw = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode()
    path = STUDY / "control_banks.json"
    path.write_bytes(raw)
    receipt = {"version": "v06_control_bank_freeze_001", "before_candidate_assessment": True,
        "control_banks_sha256": sha256(raw).hexdigest(),
        "generator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "static_validator_sha256": sha256((ROOT / "scripts/verify_matched_llm_v05.py").read_bytes()).hexdigest(),
        "bank_deployment_AST_sha256": {k: [canonical({field: p[field] for field in ("features", "rule")})
                                          for p in bank] for k, bank in groups.items()},
        "kernel_caps_must_be_bound_by_controller_execution_protocol": True}
    (STUDY / "freeze_receipt.json").write_bytes((json.dumps(receipt, indent=2)+"\n").encode())
    print(json.dumps({"control_bank": str(path), "sha256": receipt["control_banks_sha256"],
                      "banks": {k: len(v) for k, v in groups.items()}, "candidate_evaluations": 0}), flush=True)


if __name__ == "__main__":
    prepare()
