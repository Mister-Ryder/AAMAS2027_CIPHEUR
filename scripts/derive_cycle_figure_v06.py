"""Reconstruct the four-occurrence illustration from immutable R1 TRAIN data.

Independent feature/graph/recurrence helpers are used; no R2 output, production
scorer, conditional oracle, deployment kernel or TEST data is accessed.
"""
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_matched_llm_v05 import FeatureView, canonical, quotient
from scripts.verify_public_alias_v05 import exact_alpha, exact_vector

FRAME = ROOT / "experiments/discovery/v06_refinement_draft_003/training_evidence.json"
RESULTS = ROOT / "experiments/discovery/v06_synthesis_server_001/llm/candidate_results.jsonl"
OUT = ROOT / "experiments/analysis/v06/cycle_figure_evidence_v06_001.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Preserve the original illustration evidence")
    assert digest(FRAME) == "762fc25046eeb13f49044b96c5d74b7136dedcc363e1fec81809bcc83aa62913"
    assert digest(RESULTS) == "9520ab3b3f85d2ca6e04ca91fc805a4d1f720152e4be9fe87e873abb7580fa24"
    frame = json.loads(FRAME.read_bytes())
    record = next(r for r in frame["records"] if r["id"] == "v06_public32|MANN_a9_unit")
    label = next(r for r in frame["labels"] if r["id"] == record["id"])
    assert record["split"] == label["split"] == "train"
    wanted = {"block_2_relations:3", "block_3_objective:7"}
    rows = {}
    with RESULTS.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["id"] in wanted:
                rows[row["id"]] = row
    assert set(rows) == wanted
    seed = rows["block_2_relations:3"]["program"]
    exemplar = rows["block_3_objective:7"]["program"]
    expression = next(f["expression"] for f in exemplar["features"] if f["name"] == "exclude_lb")
    feature = {"name": "exclude_lb", "expression": expression}
    assert expression["op"] == "greedy_independent_weight"
    state = FeatureView(record["graph"], record["fixed"], record["excluded"])
    ids = ("34", "5", "7", "35")
    vectors = {v: state.features(seed, v) for v in ids}
    assert len(vectors["5"]) == 15
    assert exact_vector(vectors["5"]) == exact_vector(vectors["7"])
    assert exact_vector(vectors["34"]) == exact_vector(vectors["35"])
    requirements = [{"preferred": "34", "other": "5"}, {"preferred": "7", "other": "35"}]
    certs = []
    for req in requirements:
        p, n = req["preferred"], req["other"]
        cert = next(r for r in label["rows"] if {r["a"], r["b"]} == {p, n})
        assert cert["difference"]["status"] == "strict" and cert["difference"]["preferred"] == p
        certs.append(cert)
    values, recurrence_states = {}, 0
    for v in ids:
        rest = state.active - {v} - state.adj[v]
        alpha, states = exact_alpha(state.nodes, state.adj, rest)
        recurrence_states += states
        values[v] = str(Fraction(state.nodes[v]["weight"]) + alpha)
    assert values == {"34": "15", "5": "14", "7": "15", "35": "14"}
    distinction = {v: state.operation(expression, v) for v in ids}
    assert distinction == {"34": 13.0, "5": 13.0, "7": 12.0, "35": 13.0}
    before = quotient(vectors, requirements)
    after = quotient({v: {**vec, "illustrative_exclude_lb": distinction[v]} for v, vec in vectors.items()}, requirements)
    assert before["contradictory"] and before["self_loop_requirements"] == 0
    assert not after["contradictory"] and after["quotient_nodes"] == 3
    result = {"version": "R1_TRAIN_cycle_illustration_evidence_v06_001",
        "TRAIN_only": True, "R2_outputs_accessed": False, "TEST_accessed": False,
        "seed_candidate_id": "block_2_relations:3", "feature_exemplar_id": "block_3_objective:7",
        "frame_sha256": digest(FRAME), "R1_results_sha256": digest(RESULTS),
        "record_id": record["id"], "source_scope": record["scope"],
        "graph_digest": record["graph_digest"], "fixed": record["fixed"], "excluded": record["excluded"],
        "seed_program_sha256": canonical(seed), "exemplar_program_sha256": canonical(exemplar),
        "seed_feature_vectors": vectors, "requirements": requirements, "saved_certificates": certs,
        "independent_conditional_values_exact": values, "independent_recurrence_states": recurrence_states,
        "distinguishing_feature": feature, "distinguishing_values": distinction,
        "displayed_quotient_before": before, "displayed_quotient_after": after,
        "scope": "Only these two requirements; no perfect full-frame fit, prompting advantage or schedule-quality claim",
        "ID_tie_breaking_not_assumed_invariant": True, "script_sha256": digest(__file__),
        "independent_helper_sha256": {p: digest(ROOT / p) for p in
            ("scripts/verify_matched_llm_v05.py", "scripts/verify_public_alias_v05.py")}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes((json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())
    print(json.dumps({"evidence": str(OUT), "sha256": digest(OUT), "recurrence_states": recurrence_states,
        "two_class_cycle_verified": True, "three_class_displayed_DAG_verified": True}))


if __name__ == "__main__":
    main()
