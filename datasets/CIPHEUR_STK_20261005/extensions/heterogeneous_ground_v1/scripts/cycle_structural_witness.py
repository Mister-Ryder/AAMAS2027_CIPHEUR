"""Two fixed graph statistics on the authoritative first cycle, no search."""
from pathlib import Path
from collections import Counter, deque
import importlib.util
import json
import numpy as np

script=Path(__file__).resolve();ext=script.parents[1]
spec=importlib.util.spec_from_file_location("readonly_hetero_profile",script.with_name("hetero_formal_report.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source="CP-AU-r000";query_id=source+":q008:d16"
formal=ext/"analysis"/"quad_evidence"
query=next(q for q in m.read(formal/source/"query_manifest.json")["queries"] if q["id"]==query_id)
patch=set(query["patch_indices"]);rows=[];edges={};phis={}
for config in ("E","J"):
    path=ext/"graphs"/source/(m.tag(config)+".npz")
    with np.load(path,allow_pickle=False) as stored:z={k:stored[k].copy() for k in stored.files}
    adj=m.patch_adjacency(z,patch)
    if config=="E":e_adj=adj
    edges[config]={tuple(sorted((a,b))) for a in patch for b in adj[a]}
    phis[config]={}
    for action in ("a","b"):
        root=query[action];neighbors=adj[root]
        t=sum(len(adj[u]) for u in neighbors)
        q=sum(len(adj[u]&neighbors) for u in neighbors)//2
        phis[config][action]=list(m.phi(z,root,patch,adj))
        rows.append({"config":config,"action":action,"contact_id":query[action+"_contact_id"],
            "degree":len(neighbors),"T_sum_neighbor_degrees":t,"Q_neighbor_induced_edges":q})
assert phis["E"]==phis["J"]
changed=edges["J"]-edges["E"]
endpoints={v for edge in changed for v in edge}
locations=[]
for action in ("a","b"):
    root=query[action];distance={root:0};parent={};queue=deque([root])
    while queue:
        node=queue.popleft()
        for neighbor in sorted(e_adj[node]):
            if neighbor not in distance:
                distance[neighbor]=distance[node]+1;parent[neighbor]=node;queue.append(neighbor)
    reachable=endpoints&distance.keys()
    nearest=min(reachable,key=lambda node:(distance[node],node)) if reachable else None
    route=[];here=nearest
    while here is not None:
        route.append(here)
        if here==root:break
        here=parent[here]
    route.reverse()
    locations.append({"action":action,"minimum_endpoint_distance":distance[nearest] if nearest is not None else None,
        "nearest_endpoint_index":nearest,"shortest_path_indices":route,
        "shortest_path_contact_ids":[str(z["contact_id"][v]) for v in route],
        "reachable_changed_endpoints":len(reachable),"unreachable_changed_endpoints":len(endpoints-reachable),
        "endpoint_distance_histogram":dict(sorted(Counter(distance[v] for v in reachable).items())),
        "root_component_nodes_in_E_P":len(distance)})
result={"scope":"one preregistered deterministic cycle case; two pre-fixed input statistics only; no fittedranking, certificate or model calls",
    "source":source,"query_id":query_id,"patch_count":len(patch),"rows":rows,
    "full_base9_root_vectors_equal_E_J":True,
    "T_definition":"sum(degree_P(u) foru inN_P(v))",
    "T_existing_typed_library_expressible":True,
    "T_note":"no direct neighbour-degree reducer, but exact edge-count identityT=|E(P)|-|E(P minusN)|+|E(N)| uses existing typedoperators; no candidate fitting performed",
    "Q_definition":"count(induced_edges(neighbors(root))) within sameP",
    "Q_existing_typed_library_expressible":True,
    "Q_expression":{"op":"count","args":[{"op":"induced_edges","args":[{"op":"neighbors","args":[{"op":"root","args":[]}]}]}]},
    "library_source":"cipheur/graph_features.py::NEIGHBOR_EDGE_COUNT and GRAPH_OPERATION_TYPES",
    "library_sha256":m.digest(ext.parents[4]/"第二篇"/"cipheur"/"graph_features.py"),
    "new_patch_edges_E_to_J":len(edges["J"]-edges["E"]),
    "new_patch_edge_indices":sorted(edges["J"]-edges["E"]),
    "structural_location":{"graph":"E configuration graph induced by same recordedP, before addingJ edges",
        "definition":"min unweighted shortest-path distance fromroot to eitherendpoint ofanyE-to-J newedge; ties use ascendingoriginalnodeindex",
        "changed_endpoint_count":len(endpoints),"roots":locations,
        "scope":"location witness only, no repairedfeature or rankingclaim"},
    "script_sha256":m.digest(script),"manifest_sha256":m.digest(formal/source/"query_manifest.json")}
m.dump(ext/"analysis"/"formal_report"/"cycle_structural_witness.json",result)
print(json.dumps(result,ensure_ascii=False))
