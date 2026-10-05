"""Build validation input, then freeze exact selected programs before TEST."""
import argparse,datetime,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def write(p,v):
    p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():raise ValueError('Preserve existing frozen artifact: '+str(p))
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def candidates():
    programs=read(ROOT/'banks/real_cli_12calls.audit2.json')['programs']+read(ROOT/'banks/nonllm_grammar32.json')['programs']
    if len({p['id'] for p in programs})!=len(programs):raise ValueError('Duplicate original IDs')
    return programs
def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['validation','final']);ap.add_argument('--selection',type=pathlib.Path,required=True);a=ap.parse_args()
    selection=read(a.selection);programs=candidates();byid={p['id']:p for p in programs}
    if a.stage=='validation':
        ids=sorted({p for group in selection['groups'].values() for p in group['selected_ids']})
        if any(p not in byid for p in ids):raise ValueError('Invalid shortlist ID')
        write(ROOT/'selection/validation_program_ids.json',{'program_ids':ids,'TRAIN_shortlist_sha256':sha(a.selection),'TEST_read':False})
        write(ROOT/'banks/validation_candidates128.json',{'version':'same_128_original_candidates_validation_v1','selection_split':'TRAIN','TEST_used_for_selection':False,'programs':programs})
        print(json.dumps({'shortlisted':len(ids),'bank_size':len(programs)}));return
    if selection.get('split') not in ['VALIDATION','val','validation']:raise ValueError('Require independent VALIDATION selection')
    ids=sorted({group['selected_id'] for group in selection['groups'].values()})
    if len(ids)!=7:raise ValueError('Expected 6 independent LLM programs plus one grammar program')
    old=read(ROOT.parents[1]/'examples/frozen_joint_bank_v06.json')['programs'][0]
    old=dict(old);old['arm']='old_frozen';old['provenance']={'source':'existing frozen v06 first preregistered head','selected_by_TEST':False,'new_synthesis_calls':0}
    final=[byid[p] for p in ids]+[old];ids=[p['id'] for p in final]
    bankpath=ROOT/'banks/frozen_final8.json'
    write(bankpath,{'version':'frozen_full_stk_final8_v1','selection_split':'VALIDATION','TEST_used_for_selection':False,
        'selected_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selection_sha256':sha(a.selection),
        'original_bank_sha256':sha(ROOT/'banks/real_cli_12calls.audit2.json'),'programs':final})
    write(ROOT/'selection/final_program_ids.json',{'program_ids':ids,'frozen_program_bank_sha256':sha(bankpath)})
    protocol=read(ROOT/'protocol.pre_generation.json');execution=read(ROOT/'freeze_execution.json')
    protocol.update(frozen=True,frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='Final programs and protocol frozen after VALIDATION and before any TEST scoring',
        test_sources=['CP-AU-r008','CP-AP-r008','CP-AU-r009','CP-AP-r009'],
        final_program_ids=ids,frozen_program_bank_sha256=sha(bankpath),
        budgets_seconds=[2,10],seeds=[2,3,5],patch_cap=128,swap_rounds=2,swap_fraction=.1,max_repairs=10000,
        destroy_cycle=[16,32],execution_script_hashes=execution['script_sha256'],
        native_CHILS_executable_sha256=execution['native_CHILS_executable_sha256'],
        validation_selection_sha256=sha(a.selection),selection_rule_sha256=sha(ROOT/'selection_rule.pre_results.json'),
        requested_model='gpt-6.1-sol',served_model_versions_observed='unknown; actual metadata not emitted',
        real_offline_LLM_call_count=12,no_TEST_used_in_generation_fit_or_selection=True,
        test_parameter_status='680/1800 uniform and 680/1200,1200/680 mixtures absent from TRAIN evidence and complete schedule selection',
        evaluation_mode='paired static configurations of identical contacts; not an unimplemented mid-run parameter event')
    write(ROOT/'protocol.frozen.json',protocol)
    print(json.dumps({'program_count':len(final),'frozen_program_bank_sha256':sha(bankpath),'protocol_sha256':sha(ROOT/'protocol.frozen.json')}))
if __name__=='__main__':main()
