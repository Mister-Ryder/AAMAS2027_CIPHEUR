"""Reserve, register and launch one background stage, with duplicate prevention."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

SCRIPT=Path(__file__).resolve()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def update(path,record):
    temporary=path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temporary,path)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",choices=("val","test","final_train"),required=True)
    p.add_argument("--run-root",type=Path,required=True)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--cipheur-root",type=Path,required=True)
    p.add_argument("--graph-root",type=Path)
    p.add_argument("--graph-manifest",type=Path)
    p.add_argument("--program-bank",type=Path,required=True)
    p.add_argument("--program-ids-json",type=Path,required=True)
    p.add_argument("--protocol",type=Path,required=True)
    p.add_argument("--execution-freeze",type=Path,default=SCRIPT.parent.parent/"freeze_execution.json")
    p.add_argument("--method",action="append",choices=("degree","weight","grasp","local2swap","cp_sat","chils_ils","chils"),default=[])
    p.add_argument("--native-executable",type=Path)
    p.add_argument("--budgets",type=float,nargs="+")
    p.add_argument("--seeds",type=int,nargs="+")
    p.add_argument("--shuffle-seed",type=int,default=20261005)
    args=p.parse_args()
    if not args.execution_freeze.is_file():raise ValueError("Explicit execution-freeze file is required")
    freeze=json.loads(args.execution_freeze.read_text(encoding="utf-8"))
    if freeze.get("frozen") is not True:raise ValueError("Execution kernel is not frozen")
    for name,expected in freeze["script_sha256"].items():
        if sha(SCRIPT.with_name(name))!=expected:raise ValueError("Frozen execution kernel mismatch: "+name)
    if args.native_executable and sha(args.native_executable)!=freeze["native_CHILS_executable_sha256"]:
        raise ValueError("Frozen CHILS native executable differs")
    ids_data=json.loads(args.program_ids_json.read_text(encoding="utf-8"))
    ids=ids_data if isinstance(ids_data,list) else ids_data["program_ids"]
    if not ids or len(set(ids))!=len(ids):raise ValueError("Give a nonempty, unique, explicitly selected programme ID list")
    budgets=args.budgets or ([2.] if args.stage=="val" else [2.,10.])
    seeds=args.seeds or ([2] if args.stage=="val" else [2,3,5])
    if not set(budgets)<=set(freeze["budgets_seconds"]) or not set(seeds)<=set(freeze["formal_seeds"]):raise ValueError("Budget/seed differs from execution freeze")
    root=args.run_root.resolve();root.mkdir(parents=True,exist_ok=True)
    receipt=root/"start_receipt.json"
    runner=SCRIPT.with_name("stage_schedule_runner.py")
    manifest=root/"registration"/"manifest.json"
    record={"status":"reserved_before_registration","reserved_utc":now(),"stage":args.stage,"hostname":socket.gethostname(),
            "launcher_pid":os.getpid(),"run_root":str(root),"launcher_sha256":sha(SCRIPT),"runner_sha256":sha(runner),
            "execution_freeze_sha256":sha(args.execution_freeze),"programme_bank_sha256":sha(args.program_bank),
            "programme_ids_sha256":sha(args.program_ids_json),"programme_ids":ids,"protocol_sha256":sha(args.protocol),
            "budgets_seconds":budgets,"seeds":seeds,"duplicate_policy":"Atomic start receipt; a used run root cannot be started again"}
    # Exclusive creation is the duplicate-start guard. A failed registration remains reviewable.
    with receipt.open("x",encoding="utf-8") as f:f.write(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    common=[sys.executable,str(runner),"--stage",args.stage,"--manifest",str(manifest),
            "--data-root",str(args.data_root),"--cipheur-root",str(args.cipheur_root)]
    register=common+["--register","--program-bank",str(args.program_bank),"--program-ids-json",str(args.program_ids_json),
                     "--protocol",str(args.protocol),"--budgets",*[str(v) for v in budgets],"--seeds",*[str(v) for v in seeds],
                     "--shuffle-seed",str(args.shuffle_seed)]
    if args.graph_root:register += ["--graph-root",str(args.graph_root)]
    if args.graph_manifest:register += ["--graph-manifest",str(args.graph_manifest)]
    for method in args.method:register += ["--method",method]
    if args.native_executable:register += ["--native-executable",str(args.native_executable)]
    record["registration_argv"]=register;update(receipt,record)
    with (root/"registration.stdout.txt").open("w",encoding="utf-8") as stdout,(root/"registration.stderr.txt").open("w",encoding="utf-8") as stderr:
        proc=subprocess.run(register,stdout=stdout,stderr=stderr,check=False)
    record["registration_exitcode"]=proc.returncode
    if proc.returncode:
        record.update(status="registration_failed_no_solver_started",finished_utc=now());update(receipt,record)
        raise SystemExit(proc.returncode)
    execute=common+["--execute","--output-root",str(root/"results")]
    if args.native_executable:execute += ["--native-executable",str(args.native_executable)]
    record.update(manifest_sha256=sha(manifest),execution_argv=execute)
    try:
        with (root/"execution.stdout.txt").open("a",encoding="utf-8") as stdout,(root/"execution.stderr.txt").open("a",encoding="utf-8") as stderr:
            kwargs={"start_new_session":True} if os.name!="nt" else {"creationflags":getattr(subprocess,"CREATE_NO_WINDOW",0)}
            child=subprocess.Popen(execute,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,close_fds=True,**kwargs)
        record.update(status="background_started_not_completion_claim",started_utc=now(),dispatcher_pid=child.pid)
    except Exception as exc:
        record.update(status="launch_failed",error=repr(exc));update(receipt,record);raise
    update(receipt,record)
    print(json.dumps({"stage":args.stage,"pid":record["dispatcher_pid"],"start_receipt":str(receipt),"manifest_sha256":record["manifest_sha256"]}),flush=True)

if __name__=="__main__":main()
