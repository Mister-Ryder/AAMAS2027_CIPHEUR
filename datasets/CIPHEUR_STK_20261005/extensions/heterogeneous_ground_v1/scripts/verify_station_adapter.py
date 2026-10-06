"""One fixed 16-node input-adapter fixture; no evidence solver or labels."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys

path=Path(__file__).with_name("heterogeneous_evidence.py")
spec=importlib.util.spec_from_file_location("hetero_adapter_fixture",path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=m.core.SOURCES[0]
arrays,graphs,ids=m.source_graphs(source)
original_path=m.OLDPROBE/source/"query_manifest.json"
original=json.loads(original_path.read_text(encoding="utf-8"))
query=original["queries"][0]
assert query["anchor_slot"]==0 and query["patch_cap"]==16
patch={ids[i] for i in query["patch_indices"]}
all9=m.core.FeatureRuleProgram("adapter_all9",[]," + ".join(m.core.FEATURES))
gap_arithmetic=m.core.FeatureRuleProgram("adapter_gap_type",[],"station_gap / satellite_gap + weight")
frozen=m.core.FeatureRuleProgram.from_dict(json.loads((m.core.PROJECT/"examples"/"frozen_joint_bank_v06.json").read_text(encoding="utf-8"))["programs"][0]["program"])
checks=[]
for config in m.CONFIGS:
    graph=graphs[config]
    evaluator=m.StationLocalEvaluator(graph,all9,patch,score_slice=False)
    for node in sorted(patch):
        actual=tuple(str(Fraction(evaluator.feature_values(node)[name])) for name in m.core.FEATURES)
        assert actual==m.local_phi(graph,node,patch)
        assert Fraction(actual[m.core.FEATURES.index("station_gap")])==graph.constraints["station_gap_by_antenna"][graph.nodes[node].station]
    checks.append({"config":config,"complete_base9_matches_recorded_phi":True,"nodes":len(patch)})
for config,gap in (("A",340),("J",1200)):
    old,oldids=m.core.build_graph(arrays[config],source,gap)
    assert oldids==ids and old.edges==graphs[config].edges
    for node in sorted(patch):assert m.core.phi(old,node,patch)==m.local_phi(graphs[config],node,patch)
    for program in (all9,gap_arithmetic,frozen):
        reference=m.CompiledEvaluator(old,program,patch,score_slice=True)
        adapted=m.StationLocalEvaluator(graphs[config],program,patch,score_slice=True)
        for node in sorted(patch):assert reference.score(node)==adapted.score(node)
    checks.append({"config":config,"uniform_old_base9_and_frozen_scores_exactly_equal":True})
root=ids[query["a"]]
for rule,expected in (("weight",0),("station_gap",1)):
    program=m.core.FeatureRuleProgram("adapter_cost_fixture",[],rule)
    meter={};evaluator=m.StationLocalEvaluator(graphs["W"],program,patch,meter,score_slice=True)
    evaluator.score(root)
    primitives=meter["feature_primitives"]
    assert primitives.get("station_local_root_field_read",0)==expected
    assert primitives.get("station_local_mapping_read",0)==expected
    checks.append({"rule":rule,"station_local_extra_reads":2*expected,"lazy_cost_scope_correct":True})
receipt={"scope":"one fixed original first-anchor 16-node patch; no solver/labels/model calls",
    "source":source,"query_id":query["id"],"patch_nodes":len(patch),
    "original_manifest_sha256":m.core.digest(original_path),
    "numeric_namespace":m.NAMESPACE,"all_passed":True,"checks":checks,
    "production_script_sha256":m.core.digest(path),"fixture_script_sha256":m.core.digest(Path(__file__)),
    "graph_npz_sha256":{c:m.core.digest(m.EXT/"graphs"/source/(m.tag(c)+".npz")) for c in m.CONFIGS}}
m.core.dump(m.EXT/"analysis"/"adapter_fixture.json",receipt)
print(json.dumps(receipt,ensure_ascii=False))
