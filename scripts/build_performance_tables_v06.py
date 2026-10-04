"""Render frozen published-method comparisons from an audited analysis only.

No method, target or family is selected by its observed performance. All three
targets and every registered family are rendered in the supporting Markdown;
the compact manuscript table uses the fixed five-second target. Values are
paired gains over CHILS seed1, never percentages of an alleged optimum.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from hashlib import sha256
import json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
METHODS=(
    ('native','native:CHILS','CHILS','grossmann2025chils'),
    ('native','native:CHILS_ILS','ILS','grossmann2025chils'),
    ('native','native:M2WIS',r'M$^2$WIS','grossmann2024mmwis'),
    ('native','native:Struction','Str.','gellner2021struction'),
    ('native','native:WeightedBR','WBR','lamm2019weighted'),
    ('warm_CHILS','Degree','Degree',''),
    ('warm_CHILS','published_EoH_DSL_quality','EoH','liu2024eoh'),
    ('warm_CHILS','joint_W','Joint W',''),
)

def digest(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def gain_key(row):
    return row['population'],row['family'],row['target'],row['track'],row['first']

def mean(metric):
    value=metric.get('mean')
    if value is not None and (isinstance(value,bool) or not math.isfinite(value)):
        raise ValueError('Invalid audited summary value')
    return value

def cell(metric,highlight=False):
    value=mean(metric)
    text='---' if value is None else ('0.00' if round(value,2)==0 else f'{value:+.2f}')
    if highlight:text=r'\textbf{'+text+'}'
    if metric['defined_contexts']!=metric['assigned_contexts']:
        text+=f"$^{{{metric['defined_contexts']}/{metric['assigned_contexts']}}}$"
    return text

def family_label(pop,fam):
    if pop.startswith('fresh_'):
        text=pop.removeprefix('fresh_')
        profile='Dense' if text.startswith('dense_long_') else 'Standard'
        regime=('ground' if text.endswith('ground_scarce') else
                'satellite' if text.endswith('satellite_scarce') else 'balanced')
        return profile+'/'+regime
    return str(fam).replace('WDP_','WDP ').replace('_',r'\_')

def build(analysis_path,expected_sha,out):
    analysis_path=Path(analysis_path);out=Path(out)
    if digest(analysis_path)!=expected_sha:raise ValueError('Root-approved analysis bytes changed')
    data=json.loads(analysis_path.read_bytes())
    if data.get('version')!='v06_audited_performance_analysis_001' or data.get('assignments')!=52548 or data.get('no_TEST_selection') is not True:
        raise ValueError('A complete audited frozen analysis is required')
    if data.get('bootstrap_replicates')!=2000 or data.get('bootstrap_seed')!=261004:
        raise ValueError('Use the frozen source-cluster statistics')
    rows={gain_key(r):r for r in data['contrast_summaries']
        if r['scope']=='population_family' and r['contrast']=='versus_fixed_full_CHILS_seed1'}
    families=sorted({(r['population'],r['family']) for r in rows.values()},key=lambda x:(x[0],str(x[1])))
    primary=[p for p in families if not p[0].startswith('C3_')]
    # Cost and coverage have different measured-member conditioning from reward.
    costs={(r['population'],r['family'],r['target'],r['track'],r['estimate']):r
        for r in data['role_summaries'] if r['scope']=='population_family'}
    provenance={'version':'v06_performance_table_render_001','analysis_sha256':expected_sha,
        'analysis_archive_sha256':data['archive_sha256'],'analysis_audit_sha256':data['independent_audit_sha256'],
        'renderer_sha256':digest(__file__),'main_nominal_target':5,'all_targets':[.1,1,5],
        'main_scope':'Every non-C3 frozen family; all exploratory C3 families remain in supporting report',
        'highlight_scope':'Observed greatest full-coverage point estimate in the family; partially covered means are marked and excluded from bolding. No significance or optimality claim',
        'methods':[{'track':t,'estimate':e,'label':n,'citation':c} for t,e,n,c in METHODS],
        'cells':[]}
    def record(pop,fam,target,track,estimate):
        key=pop,fam,target,track,estimate
        if key not in rows or key not in costs:raise ValueError('A frozen method/family/target is missing')
        contrast,summary=rows[key],costs[key]
        metric=contrast['metrics']['percent_gain_exact']
        return {'population':pop,'family':fam,'target':target,'track':track,'estimate':estimate,
            'gain':metric,'coverage':summary['coverage'],'assigned_contexts':summary['assigned_contexts'],
            'complete_contexts':summary['complete_contexts'],
            'measured_standalone_cpu':summary['metrics']['standalone_cpu_seconds'],
            'measured_standalone_wall':summary['metrics']['standalone_wall_seconds'],
            'measurement_member_counts':summary['measurement_member_counts']}
    tex=[r'\begin{table*}[t]',r'\centering',r'\small',r'\setlength{\tabcolsep}{3pt}',
        r'\caption{Published solvers and the common-component framework: paired gain (\%) over full-target CHILS seed1 at nominal $T=5$. Seeds and frozen pipeline identities are averaged within context. Superscripts give defined/assigned contexts for incomplete coverage; dashes are undefined. Bold marks the greatest fully covered point estimate, without a significance claim. Partially covered means cannot establish superiority. Str.: Struction; WBR: WeightedBR. Nominal targets differ from total measured cost.}',
        r'\label{tab:v06-published}',r'\begin{tabular}{l'+('r'*len(METHODS))+'}',r'\toprule',
        'Family & '+' & '.join(n+(r'~\cite{'+c+'}' if c else '') for _,_,n,c in METHODS)+r'\\',r'\midrule']
    for pop,fam in primary:
        entries=[record(pop,fam,5,t,e) for t,e,_,_ in METHODS]
        values=[mean(r['gain']) for r in entries]
        complete=[r['gain']['defined_contexts']==r['gain']['assigned_contexts'] for r in entries]
        best=max((v for v,full in zip(values,complete) if v is not None and full),default=None)
        label=family_label(pop,fam)
        tex.append(label+' & '+' & '.join(cell(r['gain'],v is not None and full and v==best) for r,v,full in zip(entries,values,complete))+r'\\')
        provenance['cells'].extend(entries)
    tex.extend([r'\bottomrule',r'\end{tabular}',r'\end{table*}',''])
    md=['# Complete audited performance comparison','',
        'This is an experimental supporting report. Every frozen target, family and pipeline is retained in the analysis. The manuscript table is fixed at the declared five-second target and includes every non-C3 family. All exploratory C3 results stay separate below.','',
        'Gains are paired percentages relative to full-target native CHILS seed1, not optimum-normalized scores. Cost means are conditional on known measured receipts and may use a different denominator from complete-member quality. Coverage and measurement counts remain explicit. Seed/program means occur inside each context; no best-TEST identity is selected.','']
    all_estimates=sorted({(r['track'],r['first']) for r in rows.values()})
    for pop,fam in families:
        md.extend([f'## {pop} / {fam}',''])
        for target in (.1,1,5):
            md.extend([f'Nominal target: {target} seconds.','',
                '| Track / estimate | Paired gain (%) [source CI95] | Defined / assigned contexts | Success / requested members | CPU seconds (known contexts) | Wall seconds (known contexts) |',
                '|---|---:|---:|---:|---:|---:|'])
            for track,estimate in all_estimates:
                entry=record(pop,fam,target,track,estimate);m=entry['gain'];value=mean(m);ci=m['ci95'];coverage=entry['coverage']
                val='null' if value is None else f'{value:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]'
                def time(field):
                    met=entry[field];v=mean(met)
                    return 'null' if v is None else f"{v:.6f} ({met['defined_contexts']}/{met['assigned_contexts']})"
                md.append(f"| {track} / {estimate} | {val} | {m['defined_contexts']}/{m['assigned_contexts']} | {coverage['successful_members']}/{coverage['requested_members']} | {time('measured_standalone_cpu')} | {time('measured_standalone_wall')} |")
            md.append('')
    if out.exists():raise ValueError('Preserve previous generated tables; use a new directory')
    out.mkdir(parents=True)
    for name,text in (('published_methods_v06.tex','\n'.join(tex)),('PERFORMANCE_RESULTS_V06.md','\n'.join(md))):
        with (out/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text+'\n')
    provenance['generated_sha256']={n:digest(out/n) for n in ('published_methods_v06.tex','PERFORMANCE_RESULTS_V06.md')}
    with (out/'table_provenance.json').open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(provenance,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'out':str(out),'families':len(families),'main_families':len(primary)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('analysis','analysis-sha256','out'):p.add_argument('--'+name,required=True)
    args=p.parse_args();build(args.analysis,args.analysis_sha256,args.out)
