"""Render descriptive objectives and measured CPU from saved audited context means.

The four displayed families and the five-second target already belong to the
declared main display. No objective is pooled across families; no statistical
selection, optimizer, oracle, or new experimental evaluation is performed.
"""
from pathlib import Path
from fractions import Fraction
from hashlib import sha256
import argparse,json,statistics

ROOT=Path(__file__).resolve().parents[1]
FAMILIES=(('fresh_standard_balanced','standard_balanced',36,'Standard/balanced'),
          ('fresh_dense_long_ground_scarce','dense_long_ground_scarce',36,'Dense/ground'),
          ('WDP','WDP_4xx',6,'WDP 4xx'),
          ('UAI_Grids_CHILS64','Grids',10,'Grids'))
METHODS=(('native','native:CHILS','CHILS','grossmann2025chils'),
         ('native','native:CHILS_ILS','ILS','grossmann2025chils'),
         ('native','native:M2WIS',r'M$^2$WIS','grossmann2024mmwis'),
         ('native','native:Struction','Struction','gellner2021struction'),
         ('native','native:WeightedBR','WeightedBR','lamm2019weighted'),
         ('warm_CHILS','Degree','Degree / CHILS',''),
         ('warm_CHILS','published_EoH_DSL_quality','EoH / CHILS','liu2024eoh'),
         ('warm_CHILS','joint_W','Joint W / CHILS',''))

def digest(path):
 h=sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def build(source,expected,out):
 source=Path(source);out=Path(out)
 if digest(source)!=expected:raise ValueError('Saved audited context bytes changed')
 if out.exists():raise ValueError('Preserve the prior presentation')
 wanted={(p,f) for p,f,_,_ in FAMILIES};rows=[]
 with source.open(encoding='utf-8') as stream:
  for line in stream:
   r=json.loads(line)
   if r['target']==5 and (r['population'],r['family']) in wanted:rows.append(r)
 cells={}
 for p,f,n,label in FAMILIES:
  for track,method,_,_ in METHODS:
   selected=[r for r in rows if (r['population'],r['family'],r['track'],r['estimate'])==(p,f,track,method)]
   if len(selected)!=n or len({r['id'] for r in selected})!=n:raise ValueError('Incomplete fixed context frame')
   reward=[Fraction(r['complete_mean_reward_exact']) for r in selected if r['complete_mean_reward_exact'] is not None]
   cpu=[r['standalone_cpu_seconds'] for r in selected if r['standalone_cpu_seconds'] is not None]
   cells[p,f,track,method]={'assigned':n,'complete_quality':len(reward),'known_cost':len(cpu),
    'mean_reward_exact':str(sum(reward,Fraction())/len(reward)) if reward else None,
    'mean_cpu':statistics.mean(cpu) if cpu else None,
    'requested_members':sum(r['requested_members'] for r in selected),
    'successful_members':sum(r['successful_members'] for r in selected)}
 best={}
 for p,f,n,_ in FAMILIES:
  eligible=[cells[p,f,t,m]['mean_cpu'] for t,m,_,_ in METHODS
            if cells[p,f,t,m]['complete_quality']==n and cells[p,f,t,m]['known_cost']==n]
  best[p,f]=min(eligible) if eligible else None
 tex=[r'\begin{table*}[!t]',r'\centering',r'\small',r'\setlength{\tabcolsep}{3pt}',
  r'\caption{Published solvers and frozen deployment at nominal $T=5$: within-family mean objective and measured standalone CPU seconds. WDP objectives are displayed in millions. Superscripts mark defined/assigned contexts; a partial reward mean cannot establish superiority over a fully covered method. Unsupported native executions have no displayed cost; other costs include failed attempts, charged initialization and repair, with graph loading separate. Bold marks lowest observed mean CPU among fully covered methods. All 13 families and targets remain in the report.}',
  r'\label{tab:v06-published}',r'\begin{tabular}{lrrrrrrrr}',r'\toprule',
  'Method & '+' & '.join(r'\multicolumn{2}{c}{'+label+'}' for _,_,_,label in FAMILIES)+r'\\',
  r' & $w(I)$ & CPU & $w(I)$ & CPU & $w(I)/10^6$ & CPU & $w(I)$ & CPU\\',r'\midrule']
 for track,method,label,cite in METHODS:
  values=[]
  for p,f,n,_ in FAMILIES:
   c=cells[p,f,track,method];q=c['mean_reward_exact'];cpu=c['mean_cpu']
   score='---' if q is None else (f'{float(Fraction(q))/1_000_000:.4f}' if p=='WDP' else f'{float(Fraction(q)):,.1f}')
   if c['complete_quality']!=n:score+=f"$^{{{c['complete_quality']}/{n}}}$"
   cost='---' if cpu is None or (track=='native' and c['complete_quality']==0) else f'{cpu:.2f}'
   if cpu is not None and c['complete_quality']==n and c['known_cost']==n and cpu==best[p,f]:cost=r'\textbf{'+cost+'}'
   if c['known_cost']!=n:cost+=f"$^{{{c['known_cost']}/{n}}}$"
   values.extend((score,cost))
  tex.append(label+(r'~\cite{'+cite+'}' if cite else '')+' & '+' & '.join(values)+r'\\')
 tex.extend((r'\bottomrule',r'\end{tabular}',r'\end{table*}',''))
 out.mkdir(parents=True)
 (out/'reward_cost_methods_v06.tex').write_text('\n'.join(tex),encoding='utf-8')
 records=[{'population':p,'family':f,'track':t,'method':m,**r} for (p,f,t,m),r in cells.items()]
 (out/'provenance.json').write_text(json.dumps({'version':'v06_descriptive_reward_cost_display_001',
  'context_estimates_sha256':expected,'renderer_sha256':digest(__file__),
  'nominal_target':5,'no_new_evaluation':True,'no_TEST_selection':True,
  'scope':'All four predeclared main families, every fixed displayed method; objectives stay family-specific.',
  'cells':records},indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'out':str(out),'families':4,'methods':8}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--contexts',required=True)
 p.add_argument('--contexts-sha256',required=True);p.add_argument('--out',required=True)
 a=p.parse_args();build(a.contexts,a.contexts_sha256,a.out)
