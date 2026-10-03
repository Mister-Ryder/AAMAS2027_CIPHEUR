"""Fresh INPUT audit and native tiny-fixture audit; no fresh outcome access."""
import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from math import lcm
import itertools
import json
from pathlib import Path
import sys
import zipfile
import verify_v03_evidence as audit

ROOT = Path(__file__).resolve().parents[1]
FRESH = ROOT / "experiments/runs/v04/fresh_data_v04_002.tar.gz"
SOURCE = ROOT / "experiments/source_snapshots/v04/relevance_v04_source.zip"
GENERATOR_SOURCE = ROOT / "experiments/source_snapshots/v04/advanced_v04_003_source.zip"
TRAIN = ROOT / "experiments/runs/v04/relevance_train_v04_001.tar.gz"


def native(path=None):
    path = Path(path) if path is not None else ROOT/"experiments/analysis/v04/native_preflight_v04.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    results, failures = defaultdict(Counter), []
    for i,c in enumerate(d["test_cases"]):
        g = audit.GraphView(c["graph"])
        exact = g.optimum(c["fixed"], c["excluded"])
        audit.require(exact is not None and audit.near(c["exhaustive_optimum"], exact), "native_fixture_exhaustive_optimum", str(i), "saved optimum mismatch")
        active = sorted(g.available(c["fixed"],c["excluded"]))
        index = {v:i+1 for i,v in enumerate(active)}
        scale = 1
        for v in active: scale = lcm(scale,g.weights[v].denominator)
        edges = sum(len(g.adj[v]&set(active)) for v in active)//2
        text = "\n".join([f"{len(active)} {edges} 10"]+[str(int(g.weights[v]*scale))+" "+" ".join(str(index[u]) for u in sorted(g.adj[v]&set(active),key=lambda u:index[u])) for v in active])+"\n"
        for r in c["runs"]:
            method = r["method"]
            audit.require(r["integer_scale"] == scale and r["input_sha256"] == sha256(text.encode()).hexdigest(), "native_fixture_exact_metis_scaling", f"{i}/{method}", "input differs")
            audit.require(r["executable_sha256"] == d["binary_sha256"][method] and r["threads"] == 1 and r["exact_optimum_claimed"] is False, "native_fixture_pinned_binary", f"{i}/{method}", "identity/scope mismatch")
            results[method]["assigned"] += 1
            if not r["completed"]:
                audit.require(all(r[k] is None for k in ("selected","value","feasible")), "native_fixture_failure_null", f"{i}/{method}", "fallback/partial schedule")
                failures.append({"case":i,"method":method,"status":r["status"]})
                results[method]["failed"] += 1
                continue
            audit.check_selection(g,r["selected"],r["value"],c["fixed"],c["excluded"],f"{i}/{method}")
            audit.require(Fraction(r["value"]) <= exact and r["feasible"] is True, "native_fixture_returned_below_optimum", f"{i}/{method}", "infeasible or exceeds optimum")
            if not active:
                audit.require(set(r["selected"]) == set(c["fixed"]), "native_fixture_empty_residual_shortcut", f"{i}/{method}", "shortcut differs from fixed")
                results[method]["completed"] += 1
                results[method]["empty_residual_wrapper_shortcut"] += 1
                results[method]["tiny_optimum_attained"] += Fraction(r["value"]) == exact
                continue
            values = list(map(int,r["solution_text"].split()))
            if r["output_format"] == "partition_flags":
                audit.require(len(values) == len(active) and set(values) <= {0,1}, "native_fixture_flags_valid", f"{i}/{method}", "malformed flags")
                selected = list(c["fixed"])+[v for v,flag in zip(active,values) if flag]
            else:
                audit.require(len(values) == len(set(values)) and all(1 <= v <= len(active) for v in values), "native_fixture_ids_valid", f"{i}/{method}", "malformed IDs")
                selected = list(c["fixed"])+[active[v-1] for v in values]
            audit.require(set(selected) == set(r["selected"]), "native_fixture_output_original_mapping", f"{i}/{method}", "output mapping mismatch")
            results[method]["completed"] += 1
            results[method]["tiny_optimum_attained"] += Fraction(r["value"]) == exact
    audit.require(len(d["test_cases"]) == d["cases"] == 32 and sum(x["assigned"] for x in results.values()) == d["native_runs"] == 128 and failures == d["native_failures"], "native_fixture_population_complete", "native", "population/failure mismatch")
    expected = {"KaMIS":"2e4b3861b8063f05e8520434b97ce59e21ca49e7", "CHILS":"515952724cd3dcc6c4365a340ecf0f1da782119a"}
    for name,commit in expected.items():
        r = d["sources"][name]
        audit.require(r["returncode"] == 0 and r["stdout"].strip() == commit, "native_pinned_commit_receipt", name, "commit mismatch")
    audit.require(d["sources"]["KaMIS_submodules"]["returncode"] == 0 and " b6bedee5fdef49108ad8400389497192b6b23f64 " in d["sources"]["KaMIS_submodules"]["stdout"], "native_submodule_initialized_receipt", "KaHIP", "missing/modified submodule")
    worktrees = d.get("upstream_worktree_verification",{})
    if worktrees:
        clean_nodes = []
        for name,r in worktrees.items():
            clean_nodes.append((name,r))
            clean_nodes.extend((name+"/"+sub,s) for sub,s in r.get("submodules",{}).items())
        for name,r in clean_nodes:
            audit.require(r["diff"]["returncode"] == 0 and r["diff"]["stdout"] == "" and r["tracked_status"]["returncode"] == 0 and r["tracked_status"]["stdout"] == "", "native_clean_tracked_worktree_receipt", name, "upstream tracked source changed")
        audit.require(len(clean_nodes) == 3 and d.get("all_tracked_source_bytes_match_pinned_commits") is True, "native_clean_all_sources_receipt", "native", "missing checkout/submodule clean receipt")
    else:
        audit.issue("native_upstream_clean_status_not_recorded", "native", "HEAD/submodule commit identifies a base, but clean diff/status receipts are required to establish unmodified source", "warning")
    shortcuts = sum(x["empty_residual_wrapper_shortcut"] for x in results.values())
    return {"receipt_sha256":audit.file_digest(path),"cases":32,"assigned_adapter_attempts":128,"actual_executable_invocations":128-shortcuts,"empty_residual_wrapper_shortcuts":shortcuts,"methods":{k:dict(v) for k,v in results.items()},"failures":failures,"commits":expected,"clean_tracked_worktrees_verified":bool(worktrees),"binary_sha256":d["binary_sha256"],"build_file_sha256":{k:sha256(v.encode()).hexdigest() for k,v in d["build_files"].items()},"compiler":d["compiler"]["stdout"].splitlines()[0],"scope":"Source/build/clean tracked worktree receipts checked as saved provenance; native binaries are not present locally for independent byte rehash."}


def prior_payload(path):
    if path.name.endswith(".tar.gz"):
        matches = []
        for name, handle, full in audit.stream(path):
            if name == "data.json": matches.append((full,handle.read()))
        assert len(matches) == 1
        member, raw = matches[0]
    else: member, raw = None,path.read_bytes()
    return json.loads(raw),member,sha256(raw).hexdigest()


def fresh(archive=FRESH, source=SOURCE, freeze_archive=TRAIN, stable_root=None, config_path=None, prior_root=ROOT, generator_source=GENERATOR_SOURCE):
    archive, source, freeze_archive = map(Path, (archive, source, freeze_archive))
    meta, hashes = audit.json_members(archive, {"data.json", "protocol.json", "prior_original_id_manifest.json", "prior_input_inventory.json"})
    required = {"data.json", "protocol.json", "prior_original_id_manifest.json", "prior_input_inventory.json"}
    if not required <= meta.keys():
        raise ValueError("Fresh input archive lacks required proof members: " + ", ".join(sorted(required-meta.keys())))
    data, protocol = meta["data.json"], meta["protocol.json"]
    frozen_meta, frozen_hashes = audit.json_members(freeze_archive, {"frozen_programs.json"})
    frozen = frozen_meta["frozen_programs.json"]
    manifest, inventory = meta["prior_original_id_manifest.json"], meta["prior_input_inventory.json"]
    config_path = Path(config_path) if config_path is not None else ROOT/"configs/relevance_v04_fresh_protocol.json"
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    with zipfile.ZipFile(source) as z:
        audit.require(z.read("configs/relevance_v04_fresh_protocol.json") == config_bytes, "fresh_protocol_prefrozen_train_source_bytes", "config", "fresh prespecification changed from TRAIN source")
        train_source_hashes={p:sha256(z.read(p)).hexdigest() for p in ("cipheur/relevance_synthesis_v04.py","cipheur/experiment_data.py","cipheur/study_data.py","cipheur/v51_adapter.py")}
    with zipfile.ZipFile(generator_source) as z:
        generator_hashes = {p:sha256(z.read(p)).hexdigest() for p in ("cipheur/study_data_v04.py","cipheur/relevance_synthesis_v04.py","cipheur/experiment_data.py","cipheur/study_data.py","cipheur/v51_adapter.py")}
    audit.require(all(generator_hashes[p]==digest for p,digest in train_source_hashes.items()),"fresh_shared_generator_train_source_bytes","source","shared original generator modules differ between released snapshots")
    audit.require(protocol == data["protocol"] and protocol["frozen_receipt_sha256"] == frozen_hashes["frozen_programs.json"] and protocol["candidate_bank_sha256"] == frozen["candidate_bank_sha256"], "fresh_input_freeze_bytes", "protocol", "freeze/data receipt mismatch")
    audit.require(protocol["outcome_filtering"] is False and protocol["oracle_calls_during_generation"] == 0 and protocol["freeze_test_accessed"] is False and frozen["selection_split"] == "train", "fresh_input_no_outcome_construction", "protocol", "generation access declaration")
    prior_ids, prior_seeds, prior_graphs, prior_instances = set(),set(),set(),set()
    audit.require(len(inventory["paths"]) == len(manifest["sources"]) == 12, "fresh_prior_inventory_12", "inventory", "count mismatch")
    for supplied, receipt in zip(inventory["paths"],manifest["sources"]):
        # Keep the immutable receipt spelling; relocate Windows separators only
        # for filesystem access so the same inventory also works on Linux.
        path = Path(prior_root)/supplied.replace("\\", "/")
        previous, member, digest = prior_payload(path)
        audit.require(receipt["path"] == supplied and member == receipt["member"] and digest == receipt["input_sha256"], "fresh_prior_input_bytes", supplied, "payload receipt mismatch")
        for split in ("train","validation","test"):
            if split not in previous: continue
            records = previous[split]
            for p in records:
                if p.get("source",{}).get("seed") is not None: prior_seeds.add(p["source"]["seed"])
                for side in ("left","right"): prior_graphs.add(audit.GraphView(p[side]).digest)
                prior_instances.add(sha256(json.dumps(sorted(p["left"]["contacts"],key=lambda c:c["id"]),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest())
                if p.get("family") == "c3":
                    ids = {int(v) for v in p.get("source",{}).get("original_ids",p["left"]["provenance"]["original_ids"])}
                    for side in ("left","right"):
                        audit.require(ids == {int(c["id"]) for c in p[side]["contacts"]}, "fresh_prior_actual_contact_identity", supplied+p["id"], "manifest/contact mismatch")
                    prior_ids.update(ids)
    audit.require(sorted(prior_ids) == manifest["original_ids"] and len(prior_ids) == manifest["unique_original_ids"] == protocol["c3"]["excluded_prior_opportunities"] == 40886, "fresh_global_prior_id_union", "manifest", "union mismatch")
    audit.require(sha256(json.dumps(sorted(prior_ids)).encode()).hexdigest() == protocol["c3"]["excluded_original_ids_sha256"] and sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest() == protocol["c3"]["prior_manifest_sha256"], "fresh_prior_manifest_hashes", "manifest", "hash mismatch")
    sys.path.insert(0,str(ROOT))
    from cipheur.v51_adapter import _load_legacy
    if stable_root is None:
        raise ValueError("C3 input verification requires --stable-root with the hash-pinned original V51 source and C3.csv; physical checks cannot be skipped")
    stable = Path(stable_root).expanduser().resolve()
    for name,r in protocol["c3"]["source_files"].items():
        if not audit.require(audit.file_digest(stable/"SNSD_V51_FINAL/src/snsd_core"/name) == r["sha256"], "fresh_original_source_file_hash", name, "source changed"):
            raise ValueError("Relocated original C3 source hash differs: "+name)
    csv = stable/"SNSD_V51_FINAL/data/C3.csv"
    if not audit.require(audit.file_digest(csv) == protocol["c3"]["data_sha256"] and manifest["source_data_sha256"] == [protocol["c3"]["data_sha256"]], "fresh_original_data_hash", "C3", "CSV changed"):
        raise ValueError("Relocated original C3.csv hash differs")
    legacy,_ = _load_legacy(stable)
    arcs = {a.id:a for a in legacy["data"].load_arcs(str(csv)).arcs}
    seen, c3_ids, seeds, families, source_checks = set(),set(),defaultdict(set),{},0
    for split in ("validation","test"):
        families[split] = dict(Counter(p["family"] for p in data[split]))
        expected_families = {profile+"_"+regime:len(config["sizes"])*config["per_cell"][split] for profile in config["profiles"] for regime in config["regimes"]}
        expected_families["c3"] = len(config["c3_target_sizes"])*config["c3_pairs_per_size"]
        audit.require(families[split] == expected_families, "fresh_family_cells_prespecified", split, "family allocation differs from frozen protocol")
        audit.require(len(data[split]) == protocol["counts"][split], "fresh_declared_pair_counts", split, "count mismatch")
        for p in data[split]:
            where = split+"/"+p["id"]
            audit.require(p["id"] not in seen and p["source"]["split"] == split, "fresh_pair_unique_split", where, "duplicate/misassigned")
            seen.add(p["id"])
            audit.require(p["left"]["contacts"] == p["right"]["contacts"], "fresh_pair_contact_alignment", where, "contacts differ")
            fingerprint = sha256(json.dumps(sorted(p["left"]["contacts"],key=lambda c:c["id"]),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
            audit.require(fingerprint == p["source"]["instance_fingerprint"] and fingerprint not in prior_instances, "fresh_instance_identity", where, "contact hash mismatch or prior contact-instance reuse")
            if p["source"].get("seed") is not None:
                seed = p["source"]["seed"]; seeds[split].add(seed)
                audit.require(seed not in prior_seeds and p["source"]["outcome_filtering"] is False, "fresh_temporal_seed_not_prior", where, "seed reuse/filtering")
            gl, gr = audit.GraphView(p["left"]),audit.GraphView(p["right"])
            audit.require(gl.digest == p["source"]["left_graph_fingerprint"] and gr.digest == p["source"]["right_graph_fingerprint"] and gl.digest not in prior_graphs and gr.digest not in prior_graphs, "fresh_graph_hash_nonreuse", where, "graph hash reuse/mismatch")
            change = {k:[gl.raw["constraints"].get(k),gr.raw["constraints"].get(k)] for k in gl.raw["constraints"].keys()|gr.raw["constraints"].keys() if gl.raw["constraints"].get(k)!=gr.raw["constraints"].get(k)}
            intervention = p["source"]["intervention"]
            audit.require(len(change) == 1 and change == intervention["parameter_changes"] and [list(e) for e in sorted(gl.edges-gr.edges)] == intervention["removed_edges"] and [list(e) for e in sorted(gr.edges-gl.edges)] == intervention["added_edges"], "fresh_single_parameter_intervention", where, "intervention mismatch")
            if p["family"] == "c3":
                ids = [int(v) for v in p["source"]["original_ids"]]
                audit.require(len(ids) == len(set(ids)) and not set(ids)&(prior_ids|c3_ids), "fresh_c3_global_source_nonreuse", where, "duplicate/prior/fresh ID reuse")
                c3_ids.update(ids)
                for g in (gl,gr):
                    for v,c in g.contacts.items():
                        a = arcs[int(v)]
                        audit.require((c["weight"],c["satellite"],c["station"],c["start"],c["end"]) == (a.weight,a.satellite_name,a.ground_name,a.link_st,a.link_et), "fresh_c3_original_contact_fields", where+v, "source contact altered")
                    local = tuple(replace(arcs[v],id=i) for i,v in enumerate(ids))
                    original = legacy["graph"].build_conflict_graph(local,legacy["graph"].ConflictParameters(**{k:v for k,v in g.raw["constraints"].items() if k!="model"}))
                    edges = {tuple(sorted((str(ids[int(a)]),str(ids[int(b)])))) for a,b in original.edges}
                    audit.require(edges == g.edges, "fresh_c3_original_predicate_reconstruction", where, "source edges differ")
                    source_checks += 1
            else:
                for g in (gl,gr):
                    edges = set()
                    contacts = list(g.contacts.values())
                    for a,b in itertools.combinations(contacts,2):
                        first,second = sorted((a,b),key=lambda c:(c["start"],c["id"]))
                        if (a["station"]==b["station"] and second["start"]<first["end"]+g.raw["constraints"]["station_gap"]) or (a["satellite"]==b["satellite"] and second["start"]<first["end"]+g.raw["constraints"]["satellite_gap"]) or (a["task"] and a["task"]==b["task"]): edges.add(tuple(sorted((a["id"],b["id"]))))
                    audit.require(edges == g.edges, "fresh_temporal_predicate_reconstruction", where, "temporal edges differ")
    audit.require(not seeds["validation"]&seeds["test"], "fresh_validation_test_seed_disjoint", "splits", "seed overlap")
    audit.require(len(c3_ids) == protocol["c3"]["unique_original_opportunities"] == 5760, "fresh_c3_unique_5760", "C3", "source count mismatch")
    return {"input_data_sha256":hashes["data.json"],"protocol_sha256":hashes["protocol.json"],"prespecified_config_sha256":sha256(config_bytes).hexdigest(),"frozen_receipt_sha256":frozen_hashes["frozen_programs.json"],"prior_containers":12,"excluded_prior_original_ids":40886,"unique_new_c3_ids":len(c3_ids),"original_c3_graph_reconstructions":source_checks,"pairs":{s:len(data[s]) for s in ("validation","test")},"contexts":{s:2*len(data[s]) for s in ("validation","test")},"families":families,"generator_source_sha256":generator_hashes,"generator_source_archive_sha256":audit.file_digest(generator_source),"train_source_archive_sha256":audit.file_digest(source),"generator_source_scope":"module bytes from the released advanced snapshot; four shared modules equal the TRAIN snapshot; the fresh builder was added after freeze; source predicates are independently rebuilt; the original fresh wrapper source is not bundled or independently rehashed", "wrapper_source_available":False,"input_archive_sha256":audit.file_digest(archive),"train_freeze_archive_sha256":audit.file_digest(freeze_archive),"stable_root":str(stable),"prior_inventory_scope":"All12 explicitly supplied prior input containers checked, including all assigned primary IDs in partial archives; completeness beyond supplied inventory is caller provenance."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,default=FRESH)
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--generator-source",type=Path,default=GENERATOR_SOURCE,help="Released snapshot containing the post-freeze fresh builder module")
    parser.add_argument("--freeze-archive",type=Path,default=TRAIN)
    parser.add_argument("--stable-root",type=Path,required=True,help="Same hash-pinned original V51 source and C3.csv; required physical proof input")
    parser.add_argument("--config",type=Path,default=ROOT/"configs/relevance_v04_fresh_protocol.json")
    parser.add_argument("--prior-root",type=Path,default=ROOT,help="Root containing the immutable twelve-file prior inventory")
    parser.add_argument("--native-preflight",type=Path,default=ROOT/"experiments/analysis/v04/native_preflight_v04.json")
    parser.add_argument("--output",type=Path,default=ROOT/"experiments/analysis/v04/fresh_input_audit.json")
    args=parser.parse_args(argv)
    inputs = fresh(args.archive,args.source,args.freeze_archive,args.stable_root,args.config,args.prior_root,args.generator_source)
    native_report = native(args.native_preflight)
    report = {"scope":"Fresh INPUT data only, TRAIN freeze and prior data.json members only, plus saved native tiny fixtures; no fresh outcome files read", "fresh":inputs,"native":native_report,"checks":dict(audit.CHECKS),"issues":list(audit.ISSUES.values())}
    output = args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output),"fresh":inputs,"native_methods":native_report["methods"],"checks":sum(audit.CHECKS.values()),"issues":report["issues"]}))
    return int(any(i["severity"]=="error" for i in report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
