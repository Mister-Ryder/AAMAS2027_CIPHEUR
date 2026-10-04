"""Execute exactly one separately registered complete three-arm block."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.author_matched_cli_v06 import execute_cell,safe_configuration,digest,write

def main():
    parent=ROOT/"experiments/discovery/v06_authoring_001"
    study=ROOT/"experiments/discovery/v06_authoring_supplement_001"
    protocol=json.loads((study/"protocol.json").read_text(encoding="utf-8"))
    freeze=json.loads((study/"freeze_receipt.json").read_text(encoding="utf-8"))
    completion=json.loads((parent/"authoring_completion.json").read_text(encoding="utf-8"))
    if (not completion["all_authoring_completed_before_assessment"]
        or digest(study/"protocol.json")!=freeze["protocol_sha256"]
        or digest(parent/"protocol.json")!=protocol["parent_protocol_sha256"]):
        raise ValueError("Incomplete parent or changed supplemental freeze")
    for name,expected in protocol["packet_sha256"].items():
        if digest(study/name)!=expected:raise ValueError("Frozen supplemental packet changed")
    if (study/"authoring_completion.json").exists():raise ValueError("No supplemental rerun")
    for name in ("responses","receipts"):
        (study/name).mkdir(exist_ok=True)
        if list((study/name).iterdir()):raise ValueError("No prior response or receipt may be replaced")
    configured=safe_configuration()
    if configured!=protocol["parent_requested_configuration"]:raise ValueError("Requested model/settings changed")
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(execute_cell,4,arm,study,configured) for arm in ("witness","relations","objective")]
        for f in as_completed(fs):rows.append(f.result())
    if safe_configuration()!=configured:raise ValueError("Requested configuration changed")
    write(study/"authoring_completion.json",{"version":"v06_supplement_authoring_completion_001",
        "supplement_protocol_sha256":digest(study/"protocol.json"),
        "parent_completion_sha256":digest(parent/"authoring_completion.json"),
        "completed_utc":datetime.now(timezone.utc).isoformat(),"all_authoring_completed_before_assessment":True,
        "same_requested_model_and_settings_all_cells":True,
        "response_sha256":{r["cell"]+".json":r["response_sha256"] for r in rows},
        "receipt_paths":{r["cell"]:"receipts/"+r["cell"]+".receipt.json" for r in rows},
        "failed_transport_cells":[r["cell"] for r in rows if r["exit_code"] or r["timed_out"]],
        "no_assessment_or_retry":True})
    print(json.dumps({"all_supplemental_cells_frozen":True}),flush=True)

if __name__=="__main__":main()
