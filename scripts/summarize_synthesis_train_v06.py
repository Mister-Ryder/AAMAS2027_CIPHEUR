"""Immutable byte extraction and descriptive accounting of completed TRAIN."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
STEM="synthesis_train_server_v06_001"
ARCHIVE=ROOT/"experiments/runs/v06"/(STEM+".tar.gz")
DEST=ROOT/"experiments/discovery/v06_synthesis_server_001"


def digest(raw):return sha256(raw).hexdigest()


def extract():
    expected=json.loads((ROOT/"experiments/discovery"/STEM/"archive_receipt.json").read_bytes())
    assert digest(ARCHIVE.read_bytes())==expected["archive_sha256"]
    existing=DEST.exists()
    if not existing:DEST.mkdir(parents=True)
    hashes={}
    with tarfile.open(ARCHIVE) as t:
        for member in t:
            parts=Path(member.name).parts
            assert parts[0]==STEM and ".." not in parts and not Path(member.name).is_absolute()
            target=DEST.joinpath(*parts[1:])
            assert target.resolve().is_relative_to(DEST.resolve())
            if member.isdir():target.mkdir(parents=True,exist_ok=True);continue
            assert member.isfile()
            raw=t.extractfile(member).read()
            if target.exists():assert target.read_bytes()==raw
            else:
                assert not existing,"An existing immutable extraction must be complete"
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open("xb") as stream:stream.write(raw)
            hashes[target.relative_to(DEST).as_posix()]=digest(raw)
    receipt={"archive_sha256":expected["archive_sha256"],"original_bytes_preserved":True,
             "files_sha256":hashes,"extract_script_sha256":digest(Path(__file__).read_bytes())}
    path=DEST/"EXTRACTION_RECEIPT.json"
    if path.exists():assert json.loads(path.read_bytes())==receipt
    else:path.write_bytes((json.dumps(receipt,indent=2)+"\n").encode())
    return expected["archive_sha256"]


def compact(row):
    interface=row.get("interface",{})
    kernel=row.get("kernel_summary",{})
    return {"id":row["id"],"block":row["block"],"arm":row["arm"],"slot":row["slot"],
        "static_status":row["status"],"assessment_status":row["assessment_status"],"eligible":row["eligible"],
        "strict_total":interface.get("strict_total"),"strict_passed":interface.get("strict_passed"),
        "alias_total":interface.get("alias_strict_total"),"alias_passed":interface.get("alias_strict_passed"),
        "demanded_feature_count":len(interface.get("demanded_features",[])),
        "quotient_contradictory":interface.get("quotient",{}).get("contradictory"),
        "self_loop_requirements":interface.get("quotient",{}).get("self_loop_requirements"),
        "witness_kinds":dict(Counter(w["kind"] for w in interface.get("quotient",{}).get("structural_witnesses",[]))),
        "interface_feature_work":interface.get("interface_feature_work"),
        "interface_cpu_seconds":interface.get("interface_cpu_seconds"),
        "macro_quality_exact":kernel.get("macro_quality_exact"),"macro_work_exact":kernel.get("macro_work_exact"),
        "kernel_rows_returned":len(row.get("kernel_rows",[])),
        "kernel_failed_rows":sum(not r["result"]["completed"] or not r["result"]["feasible"] for r in row.get("kernel_rows",[])),
        "error_type":row.get("error_type"),"error":row.get("error")}


def group(rows):
    assessed=[r for r in rows if r["strict_total"] is not None]
    def total(key):return sum(r[key] for r in assessed)
    def interval(key):
        values=[r[key] for r in assessed if r[key] is not None]
        return [min(values),max(values)] if values else None
    return {"raw_slots":len(rows),"static_valid":sum(r["static_status"]=="static_valid" for r in rows),
        "eligible":sum(r["eligible"] for r in rows),"assessment_status":dict(Counter(r["assessment_status"] for r in rows)),
        "interface_assessed_slots":len(assessed),"contradictory_interfaces":sum(bool(r["quotient_contradictory"]) for r in assessed),
        "strict_passed_sum":total("strict_passed"),"strict_total_sum":total("strict_total"),
        "alias_passed_sum":total("alias_passed"),"alias_total_sum":total("alias_total"),
        "strict_passed_range":interval("strict_passed"),"alias_passed_range":interval("alias_passed"),
        "interface_work_range":interval("interface_feature_work"),"interface_cpu_range":interval("interface_cpu_seconds"),
        "explicit_interface_or_feature_budget_failures":sum("budget" in (r.get("error") or "").lower() for r in rows),
        "kernel_failed_rows":sum(r["kernel_failed_rows"] for r in rows)}


def main():
    archive_sha=extract()
    raw=[json.loads(line) for line in (DEST/"llm/candidate_results.jsonl").read_bytes().splitlines()]
    rows=[compact(r) for r in raw]
    controls=[compact(json.loads(line)) for line in (DEST/"controls/candidate_results.jsonl").read_bytes().splitlines()]
    selection=json.loads((DEST/"llm/selection.json").read_bytes())
    control_selection=json.loads((DEST/"controls/selection.json").read_bytes())
    cells=[]
    for block in range(5):
        for arm in ("witness","relations","objective"):
            rs=sorted((r for r in rows if r["block"]==block and r["arm"]==arm),key=lambda r:r["slot"])
            assert len(rs)==8
            cells.append({"block":block,"arm":arm,"matched_transport_block":block in selection["matched_transport_complete_blocks"],
                          **group(rs),"slots":rs})
    byid={r["id"]:r for r in rows}
    winners=[byid[p["id"]] for p in selection["programs"]]
    block0=[]
    for bank in ("enumerated_structural","fixed_base9"):
        rs=[r for r in controls if r["block"]==0 and r["arm"]==bank]
        select=next(r for r in control_selection["selections"] if r["block"]==0 and r["bank"]==bank)
        block0.append({"bank":bank,**group(rs),"joint_eligible_slots":select["joint_eligible_slots"],
            "quality_completed_slots":select["quality_completed_slots"],
            "joint_winner_id":select["joint_eligible_winner"]["id"] if select["joint_eligible_winner"] else None,
            "quality_only_winner_id":select["quality_only_baseline"]["id"] if select["quality_only_baseline"] else None,
            "quality_only_winner":next((r for r in rs if select["quality_only_baseline"] and r["id"]==select["quality_only_baseline"]["id"]),None)})
    report={"archive_sha256":archive_sha,"source_zip_sha256":json.loads((DEST/"registration.json").read_bytes())["source_zip_sha256"],
        "summary_script_sha256":digest(Path(__file__).read_bytes()),"raw_slots":120,"controls_slots":64,
        "all15_cells":cells,"all_raw_arms":{a:group([r for r in rows if r["arm"]==a]) for a in ("witness","relations","objective")},
        "matched_transport_arms":{a:group([r for r in rows if r["arm"]==a and r["block"] in selection["matched_transport_complete_blocks"]]) for a in ("witness","relations","objective")},
        "matched_blocks":selection["matched_transport_complete_blocks"],"genuine_winners":len(winners),"winners":winners,
        "empty_matched_cells":selection["empty_matched_cells"],"all_unconditional_empty_cells":selection["all_unconditional_empty_cells"],
        "ready_for_TEST":selection["all_cells_have_genuine_winner"],"control_block0":block0,
        "source_results_sha256":{"llm":digest((DEST/"llm/candidate_results.jsonl").read_bytes()),
                                 "controls":digest((DEST/"controls/candidate_results.jsonl").read_bytes())},
        "scope":"Descriptive accounting only; no reassessment/selection/repair/TEST calls. Full static/semantic independent audit remains separate."}
    path=ROOT/"experiments/analysis/v06/synthesis_train_summary_v06_001.json"
    path.write_bytes((json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode())
    lines=["# V06 completed server TRAIN diagnostic", "",
        "All120 original LLM positions and64 control repeats were retained. This is descriptive accounting, not a new assessor, selector or independent semantic audit. The four matched authoring blocks are1/2/3/4; the original block0 transport failure stays in the unconditional accounting. No ASTs, gates, scalar scores or TRAIN quality are edited.","",
        "| Block | Arm | Eligible /8 | Strict fit range /594 | Alias fit range /90 | Status |",
        "|---:|---|---:|---|---|---|"]
    for c in cells:lines.append(f"|{c['block']}|{c['arm']}|{c['eligible']}/8|{c['strict_passed_range']}|{c['alias_passed_range']}|{c['assessment_status']}|")
    lines.extend(["","The exact three empty matched cells are relations block1, objective block2 and witness block4. Nine genuine winners do not meet the registered twelve-winner performance barrier. TEST remains unexecuted, and missing programs cannot be substituted or repaired silently.","",
        "| Winner | Strict /594 | Alias /90 | Exact TRAIN Q | Exact work |",
        "|---|---:|---:|---|---|"])
    for r in winners:lines.append(f"|{r['id']}|{r['strict_passed']}|{r['alias_passed']}|{r['macro_quality_exact']}|{r['macro_work_exact']}|")
    lines.extend(["","Controls repeat the same16 ASTs four times; these are not independent authoring draws. Only block0 quality-only winners are declared for performance, without relabeling a failed joint gate.","",
        "| Control bank | Joint eligible /8 | Completed quality /8 | Joint winner | Quality-only winner |",
        "|---|---:|---:|---|---|"])
    for c in block0:lines.append(f"|{c['bank']}|{c['joint_eligible_slots']}|{c['quality_completed_slots']}|{c['joint_winner_id']}|{c['quality_only_winner_id']}|")
    lines.extend(["","Complete per-slot work/CPU/strict/alias/gate/kernel status, exact winner values and arm accounting are in `experiments/analysis/v06/synthesis_train_summary_v06_001.json`. Extracted original bytes and file hashes are in `experiments/discovery/v06_synthesis_server_001/EXTRACTION_RECEIPT.json`. Both phase logs and source/host/archive receipts remain in the immutable archive.","",
        "Raw archive SHA256: `"+archive_sha+"`.","No scheduling/oracle/model calls were performed by this summary or extraction."])
    (ROOT/"docs/V06_SYNTHESIS_TRAIN_DIAGNOSTIC.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"cells":[{k:c[k] for k in ("block","arm","eligible","strict_passed_range","alias_passed_range","assessment_status")} for c in cells],
        "genuine_winners":len(winners),"empty_matched_cells":selection["empty_matched_cells"],
        "control_block0":[{k:c[k] for k in ("bank","joint_eligible_slots","quality_completed_slots","quality_only_winner_id")} for c in block0]}))


if __name__=="__main__":main()
