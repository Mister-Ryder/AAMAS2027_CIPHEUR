"""Register one complete matched replication block after a transport failure.

Original failed attempts, packets and protocol bytes are never overwritten.
This is a pre-assessment amendment, not outcome-directed proposal repair.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/"experiments/discovery/v06_authoring_001"
OUT=ROOT/"experiments/discovery/v06_authoring_supplement_001"
ARMS=("witness","relations","objective")

def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+"\n").encode())

def register():
    if OUT.exists():raise ValueError("Preserve the registered supplement")
    if (PARENT/"train_assessment.json").exists():raise ValueError("Assessment already started")
    if list((ROOT/"experiments/runs/v06").glob("synthesis_train*")):
        raise ValueError("Cannot make a pre-assessment amendment after TRAIN outcomes")
    parent_protocol=json.loads((PARENT/"protocol.json").read_text(encoding="utf-8"))
    failed=PARENT/"receipts/block_0_relations.receipt.json"
    receipt=json.loads(failed.read_text(encoding="utf-8"))
    if receipt["exit_code"]!=1 or (PARENT/"responses/block_0_relations.json").stat().st_size!=0:
        raise ValueError("The declared no-output transport failure is absent")
    error_events=[]
    events=PARENT/"receipts/block_0_relations.events.jsonl"
    for line in events.read_text(encoding="utf-8").splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get("type") in ("error","turn.failed"):error_events.append(event)
    if not any("Selected model is at capacity" in json.dumps(r) for r in error_events):
        raise ValueError("Unexpected reason for the supplemental transport block")
    OUT.mkdir(parents=True)
    packet_hashes={}
    for arm in ARMS:
        packet=json.loads((PARENT/"packets"/f"block_0_{arm}.json").read_text(encoding="utf-8"))
        packet["block"]=4
        packet["output_schema"]["block"]="integer4"
        path=OUT/"packets"/f"block_4_{arm}.json"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((json.dumps(packet,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode())
        prompt=(PARENT/"packets"/f"block_0_{arm}.prompt.md").read_text(encoding="utf-8").replace("block 0,", "block 4,")
        (OUT/"packets"/f"block_4_{arm}.prompt.md").write_bytes(prompt.encode())
        for suffix in (".json",".prompt.md"):
            relative=f"packets/block_4_{arm}"+suffix;packet_hashes[relative]=digest(OUT/relative)
    protocol={"version":"v06_transport_supplement_registration_001","created_utc":datetime.now(timezone.utc).isoformat(),
        "parent_protocol_sha256":digest(PARENT/"protocol.json"),"parent_protocol_unchanged":True,
        "parent_registered_cells":12,"parent_original_slots":96,
        "reason":"One parent cell returned provider-capacity error and zero candidate bytes; all original attempts are retained.",
        "failed_receipt_sha256":digest(failed),"failed_event_sha256":digest(events),"verified_error_events":error_events,
        "decided_before_any_candidate_assessment":True,"candidate_scores_read":0,"TEST_queries":0,
        "supplement_blocks":[4],"supplement_cells":3,"supplement_slots":24,"total_original_slots":120,
        "same_examples_graphs_labels_joins_library_selector_kernel":True,
        "packet_changes":"Only cell block ID and output-schema block metadata; original common scientific inputs unchanged.",
        "packet_sha256":packet_hashes,"parent_requested_configuration":receipt["requested_configuration"],
        "matched_analysis":"First four whole transport-complete blocks by original block index among0..4. A whole block is complete iff all three requests exit0, not timed out, and return nonempty raw bytes. JSON/DSL validity, feature repair, scalar fit and kernel outcomes never determine transport eligibility.",
        "failure_accounting":"Assess/report all120 original raw positions, including failed cells and incomplete blocks. Primary matched contrasts use four whole blocks; other blocks remain disclosed supplementary observations. Invalid DSL within a transport-complete block is retained and never replaced.",
        "TEST_freeze":"Exactly twelve genuine TRAIN-selected programs from the four whole matched blocks are required. A cell with no eligible candidate produces no winner and no fallback. Fewer than four transport-complete blocks stops this TEST study; no extra blocks, different models or retries in this registration.",
        "execution_order":"All parent sessions must finish/freeze before supplemental authoring begins; all15 sessions finish/freeze before any assessment.",
        "no_failed_cell_retry":True,"no_raw_response_overwrite":True,"no_outcome_based_reauthoring":True,
        "builder_sha256":digest(__file__)}
    write(OUT/"protocol.json",protocol)
    write(OUT/"freeze_receipt.json",{"protocol_sha256":digest(OUT/"protocol.json"),"packet_sha256":packet_hashes,"before_supplement_authoring":True})
    print(json.dumps({"registered":str(OUT),"protocol_sha256":digest(OUT/"protocol.json"),"total_slots":120}))

if __name__=="__main__":register()
