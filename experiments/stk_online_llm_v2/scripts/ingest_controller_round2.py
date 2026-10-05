"""Audit the two actual compact-plan controller calls without repairing output.

Original responses and all unexecuted plans remain immutable.  Whole calls,
not individual repaired recipes, are accepted.  No model or optimizer is run.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
OLD=PROJECT/'experiments/stk_full_llm_v1'
ARMS=('witness_operators','feedback_operators')
CONFIG_FIELDS={'credit_metric','evolve_every','parameter_mode','structural_mode','paired_race'}


def digest(path):
    path=Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read_json(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    def reject(value):raise ValueError('Nonfinite JSON number: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,parse_constant=reject)


def save_new(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    with path.open('x',encoding='utf-8') as stream:stream.write(text)


def require(value,message):
    if not value:raise ValueError(message)


def load_r1_helpers(root):
    source=Path(root)/'scripts/ingest_synthesis.py'
    spec=importlib.util.spec_from_file_location('v2_r1_ingest_helpers',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def explicit_served_versions(events):
    """Only resolved/served metadata, never requested labels or model text."""
    values=set()
    for line in Path(events).read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        event=json.loads(line)
        for metadata in (event,event.get('response'),event.get('session'),
                         event.get('thread'),event.get('turn')):
            if isinstance(metadata,dict):
                for key in ('resolved_model','served_model','served_model_version'):
                    if isinstance(metadata.get(key),str):values.add(metadata[key])
    return sorted(values) if values else 'unknown'


def audit_call(root,arm,event_audit,validate_schema,validate_recipe,validate_config):
    folder=Path(root)/'llm_calls'/f'{arm}.r2.b0'
    actual_plan_path=folder/'call_plan.compact.json'
    record=dict(arm=arm,call_id=folder.name,actual_plan=str(actual_plan_path),
        actual_plan_sha256=digest(actual_plan_path),status='pending',accepted=False,
        valid_recipe_count=0,recipes_requested=6,real_cli_invocation_observed=False,
        actual_served_model_version='unknown',model_metadata_observed='unknown',
        original_response_preserved=True,no_silent_repair=True,
        initial_and_final_plans_used=False)
    bank=config=None
    try:
        require(actual_plan_path.is_file(),'Missing actual compact plan')
        plan=read_json(actual_plan_path)
        require(plan['call_id']==folder.name,'Actual call_id differs')
        require(plan['response_schema_version']=='stk_online_controller_v2','Wrong actual response schema version')
        require(Path(plan['stdin_path']).name=='prompt.compact.txt','Actual plan must use compact prompt')
        require(digest(plan['stdin_path'])==plan['prompt_sha256'],'Actual compact prompt changed')
        schema_path=folder/'response_schema.json'
        require(digest(schema_path)==plan['schema_sha256'],'Recorded call schema changed')
        require(digest(Path(root)/'llm_controller_schema.json')==plan['schema_sha256'],'Root controller schema differs from actual call schema')
        marker=read_json(folder/'NOT_EXECUTED_INITIAL_PLANS.json')
        require(marker['status']=='NOT_EXECUTED' and marker['actual_plan_to_run']=='call_plan.compact.json',
                'Initial/final plans are not clearly marked unexecuted')
        for initial in marker['plans']:
            require(digest(folder/initial['path'])==initial['sha256'],'Unexecuted prior plan was changed')
        record.update(prompt_sha256=plan['prompt_sha256'],schema_sha256=plan['schema_sha256'],
            model_requested=plan['model_requested'],reasoning_effort_requested=plan['reasoning_effort_requested'],
            TRAIN_metrics_sha256=plan.get('TRAIN_metrics_sha256'),
            actual_round1_source_zip_sha256=plan.get('actual_round1_source_zip_sha256'),
            VAL_outcomes_used=plan['VAL_outcomes_used'],TEST_outcomes_used=plan['TEST_outcomes_used'])
        require(plan['VAL_outcomes_used'] is False and plan['TEST_outcomes_used'] is False,'Non-TRAIN generation input')
        receipt_path=Path(plan['receipt_path']);events=Path(plan['stdout_path']);response_path=Path(plan['response_path'])
        record.update(receipt_sha256=digest(receipt_path),events_sha256=digest(events),
                      response_sha256=digest(response_path))
        if not receipt_path.is_file():
            record['real_cli_invocation_observed']=events.is_file() and events.stat().st_size>0
            record['status']='pending_actual_call' if record['real_cli_invocation_observed'] else 'not_started'
            return record,None,None
        receipt=read_json(receipt_path)
        record.update(receipt=receipt,real_cli_invocation_observed=bool(receipt.get('pid')),
                      generation_wall_seconds=receipt.get('wall_seconds'))
        if events.is_file():
            audit=event_audit(events)
            record.update(event_audit=audit,usage=audit['usage_sum'],
                model_metadata_observed=audit['model_observed'],
                actual_served_model_version=explicit_served_versions(events),
                tool_call_count=audit['tool_call_count'])
            if audit['turns_completed']>0:record['real_cli_invocation_observed']=True
        else:audit=None
        require(receipt.get('call_id')==plan['call_id'],'Receipt call_id differs')
        require(receipt.get('prompt_sha256')==plan['prompt_sha256'],'Receipt belongs to an unexecuted/other prompt')
        require(receipt.get('argv')==plan['argv'],'Receipt argv differs from actual compact plan')
        require(receipt.get('exit_code')==0 and not receipt.get('timed_out'),
                'Actual CLI failed or timed out; entire call excluded')
        require(events.is_file() and audit is not None,'No actual event log')
        require(audit['turns_completed']>=1,'No completed actual model turn')
        require(audit['tool_call_count']==0,'Actual tool activity: entire call excluded')
        require(not audit['errors'],'Actual model turn failed/error event')
        require(response_path.is_file() and receipt.get('response_exists') is True,'No actual response')
        require(receipt.get('response_sha256')==digest(response_path),'Original response changed after execution')
        response=read_json(response_path)
        schema=read_json(schema_path);validate_schema(response,schema)
        require(set(response)=={'schema_version','controller_config','recipes','rationale'},'Unexpected response top-level keys')
        require(response['schema_version']=='stk_online_controller_v2','Wrong response version')
        require(set(response['controller_config'])==CONFIG_FIELDS,'Controller missing/extra fields; no default completion')
        config_checked=validate_config(response['controller_config'])
        require(config_checked==response['controller_config'],'Executable validator silently changed config')
        require(type(response['recipes']) is list and len(response['recipes'])==6,'Exactly six recipes required')
        names=set()
        for recipe in response['recipes']:
            validated=validate_recipe(recipe)
            require(validated==recipe,'Executable validator silently changed recipe')
            require(recipe['name'] not in names,'Duplicate recipe names')
            names.add(recipe['name'])
        bank=dict(schema_version='stk_online_llm_v2',recipes=response['recipes'])
        config=response['controller_config']
        record.update(status='accepted',accepted=True,valid_recipe_count=6,
            returned_recipe_count=6,controller_config=config,
            rationale_sha256=hashlib.sha256(response['rationale'].encode('utf-8')).hexdigest())
    except Exception as error:
        record.update(status='excluded',error=repr(error),accepted=False,valid_recipe_count=0)
    return record,bank,config


def ingest(args):
    root=args.root.resolve();audit_path=args.audit_file or root/'audit_round2.json'
    if audit_path.exists():raise FileExistsError('Refusing existing audit; use a new --audit-file revision')
    sys.path.insert(0,str(args.cipheur_root.resolve()))
    from cipheur.online_v2.typed import validate_recipe
    from cipheur.online_v2.controller import validate_controller_config
    helpers=load_r1_helpers(root)
    event_audit=helpers.load_event_audit(args.old_root)
    records,extractions=[],[]
    for arm in ARMS:
        row,bank,config=audit_call(root,arm,event_audit,helpers.validate_response_schema,
                                 validate_recipe,validate_controller_config)
        records.append(row)
        if bank is not None:extractions.append((arm,bank,config,row))
    bank_dir=args.bank_dir or root/'banks_round2';config_dir=args.config_dir or root/'configs_round2'
    if not args.audit_only:
        for arm,_,_,_ in extractions:
            for path in (bank_dir/(arm+'.json'),config_dir/(arm+'.json')):
                if path.exists():raise FileExistsError('Refusing existing extraction: '+str(path))
        for arm,bank,config,row in extractions:
            bank_path=bank_dir/(arm+'.json');config_path=config_dir/(arm+'.json')
            save_new(bank_path,bank);save_new(config_path,config)
            row.update(bank_path=str(bank_path),bank_sha256=digest(bank_path),
                       config_path=str(config_path),config_sha256=digest(config_path))
    usage={}
    for row in records:
        for name,value in row.get('usage',{}).items():usage[name]=usage.get(name,0)+value
    actual=sum(row['real_cli_invocation_observed'] for row in records)
    summary=dict(version='stk_online_controller_round2_actual_ingest_v1',calls=records,
        offline_LLM_calls_actual=actual,planned_calls=2,
        accepted_calls=sum(row['accepted'] for row in records),
        excluded_calls=sum(row['status']=='excluded' for row in records),
        pending_calls=sum(row['status'] in ('pending_actual_call','not_started','pending') for row in records),
        accepted_recipes=sum(row['valid_recipe_count'] for row in records),
        requested_recipe_slots_for_actual_calls=actual*6,usage_sum=usage,
        observed_tool_call_count=sum(row.get('tool_call_count',0) for row in records),
        actual_served_model_unknown_calls=sum(row['actual_served_model_version']=='unknown' for row in records if row['real_cli_invocation_observed']),
        ingest_model_calls=0,ingest_optimizer_calls=0,TEST_outcomes_read=False,VAL_outcomes_read=False,
        actual_plan_policy='Only call_plan.compact.json; initial/final plans were never executed.',
        audit_only=args.audit_only,script_sha256=digest(Path(__file__)),
        schema_sha256=digest(root/'llm_controller_schema.json'),
        event_audit_source_sha256=digest(args.old_root/'scripts/llm_cli_proposer.py'),
        schema_validator_source_sha256=digest(root/'scripts/ingest_synthesis.py'),
        controller_validator_source_sha256=digest(args.cipheur_root/'cipheur/online_v2/controller.py'),
        typed_validator_source_sha256=digest(args.cipheur_root/'cipheur/online_v2/typed.py'))
    save_new(audit_path,summary)
    print(json.dumps({key:summary[key] for key in ('offline_LLM_calls_actual','accepted_calls',
        'excluded_calls','pending_calls','accepted_recipes','usage_sum')},ensure_ascii=False))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--cipheur-root',type=Path,default=PROJECT)
    parser.add_argument('--old-root',type=Path,default=OLD)
    parser.add_argument('--audit-file',type=Path)
    parser.add_argument('--bank-dir',type=Path);parser.add_argument('--config-dir',type=Path)
    parser.add_argument('--audit-only',action='store_true')
    ingest(parser.parse_args())
