"""Outcome-free exact numeric encoding inventory; no optimizer/runtime imports."""
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import argparse,json,math
from pathlib import Path
import platform,time

def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
def reject_constant(value):raise ValueError('Nonfinite JSON literal: '+value)
def fraction(value):
    if type(value) is int or isinstance(value,Decimal):return Fraction(value)
    if isinstance(value,str):return Fraction(value)
    raise ValueError('Unsupported exact weight type: '+type(value).__name__)
def compatible(weights,bits):
    return bool(weights) and all(w>=0 for w in weights) and 0<sum(weights)<=2**(bits-1)-1 and max(weights)<=2**(bits-1)-1

def inspect(inputs,out):
    inputs,out=Path(inputs).resolve(),Path(out).resolve()
    assert not out.exists()
    freeze=json.loads((inputs/'input_freeze.json').read_bytes())
    assert digest(inputs/'context_inventory.json')==freeze['context_inventory_sha256']
    inventory=json.loads((inputs/'context_inventory.json').read_bytes())
    contexts=[c for c in inventory['contexts'] if c['population'] in ('WDP','UAI_Segmentation','UAI_Grids_CHILS64')]
    assert Counter(c['population'] for c in contexts)=={'WDP':25,'UAI_Segmentation':3,'UAI_Grids_CHILS64':10}
    rows=[];started=time.perf_counter();cpu=time.process_time()
    for c in sorted(contexts,key=lambda c:c['id']):
        path=(inputs/c['graph_file']).resolve();assert path.is_relative_to(inputs)
        assert digest(path)==c['graph_file_sha256']==freeze['graph_files_sha256'][c['graph_file']]
        row={'id':c['id'],'population':c['population'],'source_cluster':c['source_cluster'],
             'graph_sha256':c['graph_sha256'],'graph_file':c['graph_file'],
             'graph_file_sha256':c['graph_file_sha256'],'source_weight_scale':c['source_weight_scale']}
        try:
            graph=json.loads(path.read_bytes(),parse_float=Decimal,parse_constant=reject_constant)
            weights=[fraction(r['weight']) for r in graph['contacts']]
            assert len(weights)==c['n']
            lcm=1
            for w in weights:lcm=math.lcm(lcm,w.denominator)
            integer=[int(w*lcm) for w in weights]
            assert all(Fraction(i,lcm)==w for i,w in zip(integer,weights))
            common=0
            for w in integer:common=math.gcd(common,abs(w))
            reduced=[w//common for w in integer] if common else None
            if reduced is not None:assert all(Fraction(i*common,lcm)==w for i,w in zip(reduced,weights))
            before={str(bits):compatible(integer,bits) for bits in (32,64)}
            after={str(bits):compatible(reduced,bits) if reduced is not None else False for bits in (32,64)}
            total=sum(weights,Fraction());scale=Fraction(c['source_weight_scale'])
            row.update(status='valid_exact_numeric_inventory',vertices=len(weights),LCM=lcm,integer_weight_GCD=common,
                negative_weights=sum(w<0 for w in weights),zero_weights=sum(w==0 for w in weights),
                integer_sum_before_GCD=sum(integer),integer_max_before_GCD=max(integer) if integer else None,
                integer_sum_after_GCD=sum(reduced) if reduced is not None else None,
                integer_max_after_GCD=max(reduced) if reduced else None,
                signed_numeric_compatible_before=before,signed_numeric_compatible_after=after,
                graph_weight_total_exact=str(total),source_objective_total_exact=str(total/scale),
                native_encoded_to_graph_weight_multiplier_exact=str(Fraction(common,lcm)) if common else None,
                native_encoded_to_source_objective_multiplier_exact=str(Fraction(common,lcm)/scale) if common else None,
                exact_weight_reconstruction_verified=reduced is not None,
                numeric_inventory_scope='Nonnegative weights, max and total only; does not claim solver execution or identical heuristic trajectories')
        except Exception as e:
            row.update(status='metadata_encoding_error',error_type=type(e).__name__,error=str(e))
        rows.append(row)
    summary={}
    for population in ('WDP','UAI_Segmentation','UAI_Grids_CHILS64'):
        values=[r for r in rows if r['population']==population]
        summary[population]={'assigned':len(values),'valid_numeric_rows':sum(r['status']=='valid_exact_numeric_inventory' for r in values),
            'signed32_before':sum(r.get('signed_numeric_compatible_before',{}).get('32',False) for r in values),
            'signed32_after':sum(r.get('signed_numeric_compatible_after',{}).get('32',False) for r in values),
            'signed64_before':sum(r.get('signed_numeric_compatible_before',{}).get('64',False) for r in values),
            'signed64_after':sum(r.get('signed_numeric_compatible_after',{}).get('64',False) for r in values)}
    report={'version':'v06_public_exact_LCM_GCD_numeric_inventory_001','rows':rows,'summary':summary,
        'source_script_sha256':digest(__file__),'input_freeze_sha256':digest(inputs/'input_freeze.json'),
        'context_inventory_sha256':digest(inputs/'context_inventory.json'),'graph_inputs_or_V003_modified':False,
        'optimization_calls':0,'candidate_or_label_files_read':False,'TEST_numeric_inputs_read':True,'TEST_optimized':False,
        'actual_cpu_seconds':time.process_time()-cpu,'actual_wall_seconds':time.perf_counter()-started,
        'platform':platform.platform(),'python':platform.python_version(),
        'scope':'Metadata-only lossless numeric encoding check. Uniform GCD division preserves objective order; heuristic algorithms may remain internally scale-sensitive. Old frozen unsupported requests remain unchanged.'}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'summary':summary,'output_sha256':digest(out),'optimization_calls':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();inspect(args.inputs,args.out)
