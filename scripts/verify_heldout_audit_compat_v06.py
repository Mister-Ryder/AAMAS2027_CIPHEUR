"""Independent syntax/provenance comparison; no TEST labels or scientific runs."""
from __future__ import annotations
import argparse, ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'cipheur/heldout_refinement_v06.py'
NEW=ROOT/'scripts/prepare_heldout_r2_audit_compat_v06.py'
def digest(path): return sha256(Path(path).read_bytes()).hexdigest()

def compare_function_syntax(old_text,new_text):
    old=next(n for n in ast.parse(old_text).body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
    new=next(n for n in ast.parse(new_text).body if isinstance(n,ast.FunctionDef) and n.name=='_prepare_compat')
    changes={'name':0,'packet_identity':0,'source_snapshot_path':0}
    class Normalise(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            if node.name=='_prepare_compat': node.name='prepare'; changes['name']+=1
            return self.generic_visit(node)
        def visit_Name(self,node):
            if node.id=='EXPECTED_ORIGINAL_PACKET_AUDIT_SHA256':
                changes['packet_identity']+=1
                return ast.Subscript(value=ast.Name(id='bindings',ctx=ast.Load()),slice=ast.Constant(value='packet_audit_sha256'),ctx=ast.Load())
            return node
        def visit_Attribute(self,node):
            if isinstance(node.value,ast.Name) and node.value.id=='frozen' and node.attr=='__file__':
                changes['source_snapshot_path']+=1
                return ast.Name(id='__file__',ctx=ast.Load())
            return self.generic_visit(node)
    normalized=Normalise().visit(new)
    if changes!={'name':1,'packet_identity':1,'source_snapshot_path':1}: raise ValueError('Unexpected preparer syntax changes')
    if ast.dump(old,include_attributes=False)!=ast.dump(normalized,include_attributes=False): raise ValueError('Other preparation/selection/certificate logic changed')
    return changes

def verify(out):
    out=Path(out)
    if out.exists(): raise ValueError('Preserve mechanical reviews')
    changes=compare_function_syntax(OLD.read_text(encoding='utf-8'),NEW.read_text(encoding='utf-8'))
    errors=[];checks=2
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not ok: errors.append(label)
    check(digest(OLD)=='1e8bd6a2577eabe8e33a73edc1303358f09cdbfc1c5c53604eaf91db3380ef1a','unchanged_old_preparer')
    release=ROOT/'experiments/discovery/v06_test_release_002/root_TEST_release.json'
    check(digest(release)=='8e69f14051ce731332b11aaefa2f60c2ace38780e4f20dfb9429974555ca83d1','unchanged_main_root')
    main=json.loads(release.read_bytes())
    packet=ROOT/'experiments/analysis/v06/refinement_packet_audit_v06_002.json'
    scalar=ROOT/'experiments/analysis/v06/refinement_packet_audit_v06_002_scalar_receipt_001.json'
    original=json.loads(packet.read_bytes()); copied=json.loads(scalar.read_bytes())
    check(digest(packet)==main['original_independent_audit_sha256'][packet.name]=='7cabb43f86f1346dfd7b0156c096fc05bfd70c6f24850ee663394137f803837c','original_packet_binding')
    check(digest(scalar)==main['packet_audit_sha256']=='b0ecae2f92522b42ff6b884cd8b1a0896984c3012904c041c0b5c3575ad14951','scalar_packet_binding')
    check(copied['schema_adapter']['original_report_sha256']==digest(packet),'copy_original_provenance')
    check(copied['checks']==sum(original['checks'].values())==original['total_checks'] and copied['checks']>0,'lossless_positive_count')
    check(copied['errors']==0 and original['errors']==[] and original['error_count']==0,'original_zero_errors')
    check(copied['original_check_categories']==original['checks'] and copied['original_error_records']==original['errors'],'original_categories_retained')
    for key,value in original.items():
        if key not in ('checks','errors'): check(copied.get(key)==value,'finding:'+key)
    runtime=json.loads((ROOT/'experiments/discovery/v06_refinement_draft_003/transport_runtime_binding.json').read_bytes())
    check(runtime['independent_packet_audit_sha256']==digest(packet),'pre_generation_transport_bound_original_report')
    check(digest(packet)!=digest(scalar),'two_different_valid_byte_identities')
    report={'version':'v06_R2_packet_audit_preparation_mechanical_review_001','checked_utc':datetime.now(timezone.utc).isoformat(),
        'checks':checks,'errors':len(errors),'error_records':errors,'syntax_normalization':changes,
        'original_preparer_sha256':digest(OLD),'compatibility_preparer_sha256':digest(NEW),'reviewer_sha256':digest(__file__),
        'main_root_release_sha256':digest(release),'original_packet_audit_sha256':digest(packet),'scalar_packet_receipt_sha256':digest(scalar),
        'science_runtime_unchanged':True,'original_prepare_function_other_syntax_identical':True,
        'TEST_labels_or_scores_read':False,'new_scientific_checks':0,'programme_runs':0,
        'scope':'Root-executed independent mechanical comparison, not a new subagent scientific audit; separate preparer resolves original-report versus scalar-copy byte provenance only.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8',newline='\n') as stream: stream.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'checks':checks,'errors':errors,'review_sha256':digest(out)}))
    if errors: raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    verify(parser.parse_args().out)
