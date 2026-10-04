"""Read-only source/objective/phase audit; no project runtime or solver imports."""
from collections import Counter,defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import statistics
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STEM="classic_components_train_v06_001"


def digest(raw):return sha256(raw).hexdigest()


def parse(raw):
    weights,edges={},set()
    for line in raw.decode().splitlines():
        fields=line.split()
        if fields and fields[0]=="n":weights[int(fields[1])]=Fraction(fields[2])
        elif fields and fields[0]=="e":edges.add(tuple(sorted((int(fields[1]),int(fields[2])))))
    return weights,edges


def key(r):return r["id"],r["nominal_wall_target_seconds"],r["track"],r["seed"]


def check():
    archive=ROOT/"experiments/runs/v06"/(STEM+".tar.gz")
    capsule=ROOT/"experiments/source_snapshots/v06"/(STEM+"_source.zip")
    registration=ROOT/"experiments/discovery"/STEM
    receipt=json.loads((registration/"archive_receipt.json").read_bytes())
    assert digest(archive.read_bytes())==receipt["archive_sha256"] and archive.stat().st_size==receipt["archive_bytes"]
    assert receipt["execution_complete"] is True
    with tarfile.open(archive) as tar:
        def read(name):return tar.extractfile(STEM+"/"+name).read()
        protocol_raw=read("protocol.json");protocol=json.loads(protocol_raw)
        results_raw=read("results.jsonl");rows=[json.loads(l) for l in results_raw.splitlines()]
        completion=json.loads(read("completion.json"));freeze=json.loads(read("freeze_receipt.json"))
        host=json.loads(read("host_receipt.json"));launch=json.loads(read("launch_receipt.json"))
        execution=json.loads(read("server_execution_receipt.json"));capsule_receipt=json.loads(read("capsule_receipt.json"))
        config_raw=read("registered_config.json");config=json.loads(config_raw)
    assert digest(protocol_raw)==freeze["protocol_sha256"]==completion["protocol_sha256"]==launch["protocol_sha256"]
    assert digest(results_raw)==completion["results_sha256"]
    assert digest(capsule.read_bytes())==protocol["source_zip_sha256"]==completion["source_zip_sha256"]==capsule_receipt["source_zip_sha256"]==execution["source_zip_sha256"]
    assert digest(config_raw)==capsule_receipt["config_sha256"]==host["config_sha256"]
    with zipfile.ZipFile(capsule) as zip:
        assert set(zip.namelist())==set(capsule_receipt["files_sha256"])
        for name,want in capsule_receipt["files_sha256"].items():assert digest(zip.read(name))==want
        for name,want in config["source_sha256"].items():assert digest(zip.read(name))==want
    assert execution["exit_code"]==0 and not execution["whole_batch_guard_triggered"] and execution["retries"]==0
    assert protocol["split"]=="train" and protocol["targets"]==[.1,1,5] and protocol["native_seeds"]==[1,2,3]
    assert not protocol["TEST_execution_permitted"] and protocol["prepared_before_any_solver"]
    assert completion["TEST_solver_calls"]==completion["LLM_candidate_reads"]==completion["oracle_calls"]==completion["model_calls"]==0
    assert protocol["repair_config"]["max_work"] is None and len(protocol["contexts"])==32
    assert Counter(c["input_family"] for c in protocol["contexts"])=={"WDP":25,"UAI":7}
    expected={(c["id"],t,track,seed) for c in protocol["contexts"] for t in (.1,1,5)
        for track in ("CHILSfull","CHILShalf","Degreewarm","Degreecold") for seed in ((1,) if track=="Degreecold" else (1,2,3))}
    keyed={key(r):r for r in rows}
    assert len(rows)==len(keyed)==completion["assigned"]==completion["returned"]==960 and set(keyed)==expected
    source={};checks=20
    for family,binding in protocol["input_bindings"].items():
        rawpath=ROOT/binding["archive"];assert digest(rawpath.read_bytes())==binding["archive_sha256"]
        with tarfile.open(rawpath) as tar:
            for c in protocol["contexts"]:
                if c["input_family"]!=family:continue
                raw=tar.extractfile(binding["member_root"]+"/"+c["path"]).read()
                assert digest(raw)==c["raw_sha256"] and c["split"]=="train"
                source[c["id"]]=parse(raw)
    byid=defaultdict(list)
    for r in rows:byid[r["id"]].append(r)
    statuses=Counter();successful=0;groups=defaultdict(list);pairs=[]
    with tarfile.open(archive) as tar:
        for c in protocol["contexts"]:
            raw=tar.extractfile(STEM+"/"+c["graph_file"]).read();graph=json.loads(raw)
            assert digest(raw)==c["graph_file_sha256"]==freeze["graph_files_sha256"][c["graph_file"]]
            identity={k:v for k,v in graph.items() if k not in ("name","provenance")}
            assert digest(json.dumps(identity,sort_keys=True).encode())==c["graph_sha256"]
            weights,source_edges=source[c["id"]];ids={f"v{i:05d}":i for i in weights}
            assert set(ids)=={v["id"] for v in graph["contacts"]}
            scale=c["source_weight_scale"];assert scale>0
            for contact in graph["contacts"]:
                assert Fraction(contact["weight"])==weights[ids[contact["id"]]]*scale
                assert (weights[ids[contact["id"]]]*scale).denominator==1
                checks+=2
            total=sum(weights.values(),Fraction())*scale;assert 0<=total<=2**63-1
            edges={tuple(sorted((ids[a],ids[b]))) for a,b in graph["edges"]}
            assert len(edges)==len(graph["edges"])==c["m_conflict"]
            if c["input_family"]=="WDP":
                assert not edges.intersection(source_edges) and len(edges)+len(source_edges)==c["n"]*(c["n"]-1)//2
            else:assert edges==source_edges
            assert all(1<=a<b<=c["n"] for a,b in edges)
            checks+=len(edges)+5
            adj={v:[] for v in weights}
            for a,b in edges:adj[a].append(b);adj[b].append(a)
            metis=f"{c['n']} {len(edges)} 10\n"+"\n".join(str(int(weights[v]*scale))+" "+" ".join(map(str,sorted(adj[v]))) for v in range(1,c["n"]+1))+"\n"
            metis_sha=digest(metis.encode())
            for row in byid[c["id"]]:
                assert row["source_sha256"]==c["raw_sha256"] and row["graph_sha256"]==c["graph_sha256"] and row["split"]=="train"
                result=row.get("result");status=result["status"] if result else row["runner_error"]["type"]
                statuses[row["track"]+":"+status]+=1
                ok=row["runner_error"] is None and result is not None and result.get("completed") is True and result.get("feasible") is True
                assert row["successful_assignment"]==ok and row["assignment_returned"]
                successful+=ok;reward=None
                if result and result.get("selected") is not None:
                    selected=result["selected"];assert len(selected)==len(set(selected)) and set(selected)<=ids.keys()
                    chosen=[ids[v] for v in selected]
                    for p in combinations(chosen,2):
                        p=tuple(sorted(p));assert (p in source_edges) if c["input_family"]=="WDP" else (p not in source_edges)
                        checks+=1
                    reward=sum((weights[v] for v in chosen),Fraction())
                    assert Fraction(result["value_exact"])==reward*scale
                assert row["quality_reward_exact_original_objective"]==(str(reward) if ok else None)
                if row["track"] in ("CHILSfull","CHILShalf") and ok:
                    assert result["input_sha256"]==metis_sha and result["integer_scale"]==1
                    assert result["executable_sha256"]==protocol["CHILS_executable"]["sha256"] and result["hard_wall_seconds"]==30
                    target=row["nominal_wall_target_seconds"]*(.5 if row["track"]=="CHILShalf" else 1)
                    assert result["declared_seconds"]==target and result["child_cpu_seconds"]>=0
                    assert result["method"]=="CHILS" and result["seed"]==row["seed"] and result["threads"]==1
                    assert result["returncode"]==0 and result["solver_invoked"] and result["output_format"]=="one_based_ids"
                    output=[int(v) for v in result["solution_text"].split()]
                    assert len(output)==len(set(output)) and sorted(output)==sorted(ids[v] for v in result["selected"])
                    command=result["command"]
                    assert len(command)==15 and command[0]==protocol["CHILS_executable"]["path"]
                    assert command[1]=="-g" and command[3]=="-o" and command[5:]==["-p","4","-c","1","-s","0.1","-t",str(target),"-r",str(row["seed"])]
                    checks+=8
                    wall=result["wrapper_wall_seconds"];cpu=result["wrapper_self_cpu_seconds"]+result["child_cpu_seconds"]
                elif row["track"]=="Degreewarm" and result is not None:
                    half=keyed[(row["id"],row["nominal_wall_target_seconds"],"CHILShalf",row["seed"])]
                    initial=half["result"];assert half["successful_assignment"]
                    assert row["native_initial_selected"]==initial["selected"] and row["native_initial_value_exact"]==initial["value_exact"]
                    assert Fraction(result["value_exact"])>=Fraction(initial["value_exact"])
                    assert row["native_initial_wrapper_wall_seconds"]==initial["wrapper_wall_seconds"]
                    assert row["native_initial_wrapper_self_cpu_seconds"]==initial["wrapper_self_cpu_seconds"]
                    assert row["native_initial_child_cpu_seconds"]==initial["child_cpu_seconds"]
                    assert row["standalone_pipeline_wall_seconds"]==initial["wrapper_wall_seconds"]+row["repair_wrapper_wall_seconds"]
                    assert row["standalone_pipeline_cpu_seconds"]==initial["wrapper_self_cpu_seconds"]+initial["child_cpu_seconds"]+row["repair_wrapper_cpu_seconds"]
                    assert row["repair_phase_nominal_seconds"]==row["native_phase_nominal_seconds"]==row["nominal_wall_target_seconds"]*.5
                    wall=row["standalone_pipeline_wall_seconds"];cpu=row["standalone_pipeline_cpu_seconds"]
                elif row["track"]=="Degreecold" and result is not None:
                    wall=row["repair_wrapper_wall_seconds"];cpu=row["repair_wrapper_cpu_seconds"]
                else:
                    assert not ok and row["quality_reward_exact_original_objective"] is None
                    if row["track"]=="Degreewarm":assert row["runner_error"]["type"]=="NativeInitializerUnavailable" and result is None
                    wall=cpu=None
                if wall is not None:assert wall>=0 and cpu>=0
                groups[(c["input_family"],c["family"],row["track"],row["nominal_wall_target_seconds"])].append({"id":c["id"],"seed":row["seed"],"successful":ok,"reward":str(reward) if ok else None,"wall":wall,"cpu":cpu})
                checks+=25
            for target in (.1,1,5):
                for seed in (1,2,3):
                    warm=keyed[(c["id"],target,"Degreewarm",seed)];half=keyed[(c["id"],target,"CHILShalf",seed)];full=keyed[(c["id"],target,"CHILSfull",seed)]
                    h=Fraction(half["quality_reward_exact_original_objective"]) if half["successful_assignment"] else None
                    w=Fraction(warm["quality_reward_exact_original_objective"]) if warm["successful_assignment"] else None
                    f=Fraction(full["quality_reward_exact_original_objective"]) if full["successful_assignment"] else None
                    pairs.append({"id":c["id"],"input_family":c["input_family"],"family":c["family"],"target":target,"seed":seed,
                        "half":str(h) if h is not None else None,"warm":str(w) if w is not None else None,"full":str(f) if f is not None else None,
                        "warm_minus_half":str(w-h) if w is not None and h is not None else None,
                        "warm_minus_full":str(w-f) if w is not None and f is not None else None})
    assert successful==completion["successful"] and statuses==Counter(completion["status_counts"])
    summaries=[]
    for k,g in sorted(groups.items()):
        good=[r for r in g if r["successful"]];times=[r for r in g if r["wall"] is not None]
        summaries.append({"input_family":k[0],"family":k[1],"track":k[2],"target":k[3],"assigned":len(g),"successful":len(good),
            "mean_original_objective_exact":str(sum((Fraction(r["reward"]) for r in good),Fraction())/len(good)) if good else None,
            "median_actual_standalone_wall_seconds":statistics.median(r["wall"] for r in times) if times else None,
            "median_actual_standalone_cpu_seconds":statistics.median(r["cpu"] for r in times) if times else None})
    contrasts=[]
    for family in sorted({r["family"] for r in pairs}):
        for target in (.1,1,5):
            relevant=[r for r in pairs if r["family"]==family and r["target"]==target]
            d={"family":family,"target":target,"assigned_paired_seeds":len(relevant)}
            for comparator in ("half","full"):
                vals=[Fraction(r["warm_minus_"+comparator]) for r in relevant if r["warm_minus_"+comparator] is not None]
                d["warm_vs_"+comparator]={"assessable":len(vals),"better":sum(v>0 for v in vals),"equal":sum(v==0 for v in vals),"worse":sum(v<0 for v in vals)}
            contrasts.append(d)
    report={"errors":0,"checks":checks,"audit_scope":"Independent implementation by execution agent, not separate-person audit; no project runtime/native/kernel/oracle calls",
        "archive_sha256":digest(archive.read_bytes()),"source_zip_sha256":digest(capsule.read_bytes()),"protocol_sha256":digest(protocol_raw),"results_sha256":digest(results_raw),
        "audit_source_sha256":digest(Path(__file__).read_bytes()),"assigned":960,"successful":successful,"null_or_failed":960-successful,
        "all_source_mappings_and_exact_objectives_checked":True,"all_assignment_keys_and_phase_costs_checked":True,
        "status_counts":dict(statuses),"groups":summaries,"pairwise_contrasts":contrasts,"paired_raw_rewards":pairs,
        "host":host,"execution":execution,"no_TEST_no_candidate_reads":True,"not_for_R2_author_packets_or_selection":True,
        "quality_scope":"Exact original objective per family/source; seeds nested within source, no cross-family quality pooling, optimum normalization or inference",
        "timing_scope":"Nominal native internal wall and cooperative repair wall; measured standalone native+repair wrapper phase sums, plus shared graph preparation separately; not hard-deadline equal compute"}
    path=ROOT/"experiments/analysis/v06/classic_components_train_check_v06_001.json"
    path.write_bytes((json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode())
    print(json.dumps({"errors":0,"checks":checks,"assigned":960,"successful":successful,"status_counts":dict(statuses)}))


if __name__=="__main__":check()
