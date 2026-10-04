"""Metadata-only cold authoring receipt audit; no candidate assessment."""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import statistics


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def audit(study,output):
    study=Path(study);completion=json.loads((study/"authoring_completion.json").read_text(encoding="utf-8"))
    if completion["all_authoring_completed_before_assessment"] is not True:raise ValueError("Missing all-cell authoring freeze")
    checks=Counter();errors=[];sessions=[]
    def require(condition,kind,cell):
        checks[kind]+=1
        if not condition:errors.append({"kind":kind,"cell":cell})
    for cell,name in sorted(completion["receipt_paths"].items()):
        path=study/name;receipt=json.loads(path.read_text(encoding="utf-8"));responses=study/"responses"/(cell+".json");events=study/"receipts"/(cell+".events.jsonl")
        raw_final=study/"receipts"/(cell+".last_message.txt");stderr=study/"receipts"/(cell+".stderr.txt");wrapper=study/"receipts"/(cell+".input.txt")
        prompt=study/"packets"/(cell+".prompt.md");packet=study/"packets"/(cell+".json")
        require(receipt["cell"]==cell and receipt["no_retry"] is True and receipt["no_candidate_assessment"] is True,"no_retry_assessment_transport",cell)
        require(digest(responses)==receipt["response_sha256"]==completion["response_sha256"][cell+".json"] and responses.read_bytes()==raw_final.read_bytes(),"unmodified_last_message_response_bytes",cell)
        for file,key in ((events,"raw_event_sha256"),(stderr,"raw_stderr_sha256"),(wrapper,"wrapper_prompt_sha256"),(prompt,"frozen_prompt_sha256"),(packet,"packet_sha256")):
            require(digest(file)==receipt[key],"raw_receipt_bytes",cell)
        text=wrapper.read_text(encoding="utf-8")
        require(prompt.read_text(encoding="utf-8") in text and packet.read_text(encoding="utf-8") in text,"inline_frozen_prompt_and_packet",cell)
        completed_items=[];usage=[];observed=[];eventtypes=Counter()
        for line in events.read_text(encoding="utf-8",errors="replace").splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            eventtypes[event.get("type")]+=1
            if event.get("usage") is not None:usage.append({"event_type":event.get("type"),"usage":event["usage"]})
            if event.get("model") is not None:observed.append(event["model"])
            if event.get("type")=="item.completed":completed_items.append(event.get("item",{}))
        require((usage or None)==receipt["usage_events"] and (observed or None)==receipt["observed_model"],"actual_event_metadata_reconstruction",cell)
        commands=[];collab=[]
        for item in completed_items:
            if item.get("type")=="command_execution":
                command=item.get("command","")
                permitted=("packet.json" in command and "Get-Content" in command and ".." not in command and "python" not in command.lower())
                require(permitted and item.get("status")=="failed" and item.get("exit_code")==-1 and "Failed to create unified exec process" in item.get("aggregated_output",""),"only_recorded_packet_read_attempt_failed_precreation",cell)
                commands.append({"command_sha256":sha256(command.encode()).hexdigest(),"requested_packet_read":permitted,"status":item.get("status"),"exit_code":item.get("exit_code"),"failed_before_process_creation":True})
            elif item.get("type")=="collab_tool_call":
                require(item.get("tool")=="wait" and item.get("receiver_thread_ids")==[] and item.get("agents_states")=={} and item.get("prompt") is None,"empty_wait_no_additional_authoring",cell)
                collab.append({"tool":item.get("tool"),"receiver_count":len(item.get("receiver_thread_ids",[])),"status":item.get("status")})
            else:require(item.get("type") in ("error","agent_message"),"no_other_recorded_tool_type",cell)
        counts={k:sum(e["usage"].get(k,0) for e in usage) for k in ("input_tokens","cached_input_tokens","output_tokens","reasoning_output_tokens")}
        sessions.append({"cell":cell,"arm":receipt["arm"],"block":receipt["block"],"receipt_sha256":digest(path),"raw_event_sha256":digest(events),
                         "requested_configuration":receipt["requested_configuration"],"observed_model":receipt["observed_model"],"wall_seconds":receipt["wall_seconds"],
                         "usage_totals":counts,"exit_code":receipt["exit_code"],"timed_out":receipt["timed_out"],"recorded_command_attempts":commands,"recorded_collaboration_calls":collab,"event_types":dict(eventtypes)})
    require(len(sessions)==12 and len(completion["response_sha256"])==12,"all_twelve_authoring_receipts","completion")
    require(len({json.dumps(r["requested_configuration"],sort_keys=True) for r in sessions})==1,"same_requested_configuration","completion")
    summary={}
    for arm in ("witness","relations","objective"):
        rows=[r for r in sessions if r["arm"]==arm]
        summary[arm]={"sessions":len(rows),"slots":48,"total_reported_usage":{k:sum(r["usage_totals"][k] for r in rows) for k in rows[0]["usage_totals"]},
                      "mean_session_wall_seconds":statistics.fmean(r["wall_seconds"] for r in rows),"median_session_wall_seconds":statistics.median(r["wall_seconds"] for r in rows)}
    report={"version":"matched_authoring_cost_receipt_audit_v05_001","authoring_completion_sha256":digest(study/"authoring_completion.json"),"checks":dict(checks),"errors":errors,
            "all_requested_settings_identical":True,"observed_model_available_any_session":any(r["observed_model"] for r in sessions),"sessions":sessions,"summary":summary,
            "scope":["Metadata/hash inspection only: no candidate JSON parsing, TRAIN/TEST outcomes or scorer assessment.","CLI reported usage is not a count of backend API calls; cached input is retained without monetary-cost inference.","Requested settings and session/slot counts match; token/latency/actual served-model matching is not established.","Retained events contain three packet-read attempts failing before process creation and three empty-target waits; no successful or outside-data tool action is recorded.","Startup error messages and raw stderr contents are not printed or copied into the report. Every raw log hash is retained."]}
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"checks":sum(checks.values()),"errors":len(errors),"summary":summary}),flush=True)
    if errors:raise SystemExit(1)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--study",required=True);parser.add_argument("--out",required=True)
    args=parser.parse_args();audit(args.study,args.out)
