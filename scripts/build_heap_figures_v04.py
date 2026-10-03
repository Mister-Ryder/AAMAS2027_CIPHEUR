"""Paired fixed-AST execution analysis, with failures and conditioning explicit."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from build_result_figures_v03 import style, save, BLUE, PURPLE, GRAY, ORANGE
from build_result_figures_v04 import read_archive, identity, interval

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/analysis/v04"


def analyse(path, dataset):
    a = read_archive(path)
    rows = a['results.jsonl']
    done = a['complete.json']
    assert done['complete'] and len(rows) == done['contexts']
    assert a['execution.json']['selection_permitted'] is False
    assert a['_member_sha256']['config.json'] == a['execution.json']['config_sha256']
    assert sum(len(c['runs']) for c in rows) == 12*len(rows)
    by_group, coverage = defaultdict(list), Counter()
    sparse_cases = []
    for context in rows:
        group,cluster = identity(context['family'],context['cluster'])
        if dataset == 'sparse': group = context['cluster']
        for arm in ('primary','degree'):
            runs = [r for r in context['runs'] if r['arm'] == arm]
            assert len(runs) == 6
            pairs = [p for p in context['paired'] if p['arm'] == arm]
            assert len(pairs) == 3
            for backend in ('full_scan','heap'):
                assigned = [r for r in runs if r['backend'] == backend]
                assert sorted(r['repetition'] for r in assigned) == [0,1,2]
                for run in assigned:
                    coverage[arm+'/'+backend+'/assigned'] += 1
                    coverage[arm+'/'+backend+'/completed'] += int(run['completed'])
                    if not run['completed']:
                        assert all(run[k] is None for k in ('selected','value','value_exact','trace'))
                        assert run['fallback_used'] is False
            for pair in pairs:
                if pair['both_completed']:
                    assert pair['exact_trace_selection_value_parity'] is True
            valid = [p for p in pairs if p['both_completed']]
            entry = {'id':context['id'],'stratum':group,'cluster':str(cluster),'n':context['n'],
                     'arm':arm,'assessable_pairs':len(valid),'assigned_pairs':3,
                     'cpu_ratio':statistics.median(p['full_over_heap_cpu'] for p in valid) if valid else None,
                     'work_ratio':statistics.median(p['full_over_heap_work'] for p in valid) if valid else None,
                     'score_evaluations_saved':statistics.median(p['score_evaluations_saved'] for p in valid) if valid else None}
            by_group[group+'/'+arm].append(entry)
            if dataset == 'sparse':
                sparse_cases.append({**entry,'runs':[{k:r[k] for k in ('backend','repetition','completed','cpu_seconds','seconds','status')} for r in runs]})
    groups = {g:{'assigned_contexts':len(rs),'assessable_pairs':sum(r['assessable_pairs'] for r in rs),
                 'cpu_ratio_conditional':interval(rs,'cpu_ratio'), 'work_ratio_conditional':interval(rs,'work_ratio'),
                 'score_evaluations_saved_conditional':interval(rs,'score_evaluations_saved')} for g,rs in by_group.items()}
    return {'source':a['_source'],'execution':a['execution.json'],'complete':done,
            'coverage':dict(coverage),'groups':groups,'sparse_cases':sparse_cases,
            'scope':'identical frozen ASTs, 3 order-balanced pairs; conditional ratios require both executions complete; failures retain null schedules'}


def plot(summary):
    fig,axes = plt.subplots(1,2,figsize=(7,2.25))
    fig.subplots_adjust(left=.155,right=.99,bottom=.31,top=.70,wspace=.51)
    labels = [('standard','Standard'),('dense_long','Dense / long'),('c3','C3 contacts')]
    ax = axes[0]
    for offset,arm,color,label in [(-.10,'primary',PURPLE,'Frozen joint AST'),(.10,'degree',GRAY,'Degree AST')]:
        for i,(group,_) in enumerate(labels):
            ci = summary['fresh']['groups'][group+'/'+arm]['cpu_ratio_conditional']
            if ci is None:continue
            x,lo,hi = [ci[k] for k in ('estimate','lower','upper')]
            ax.errorbar(x,i+offset,xerr=[[max(0,x-lo)],[max(0,hi-x)]],color=color,
                        marker='o',ms=4.5,capsize=2,label=label if i==0 else None)
    ax.axvline(1,color=ORANGE,lw=1,ls='--')
    ax.set_yticks(range(3),[l for _,l in labels]);ax.invert_yaxis()
    ax.set_xlabel('Full scan / heap CPU ratio')
    ax.set_title('(a) Paired fresh execution',loc='left',fontweight='bold')
    ax.grid(axis='x',alpha=.15)
    ax = axes[1]
    cases = [c for c in summary['sparse']['sparse_cases'] if c['arm']=='primary']
    cases.sort(key=lambda c:(c['n'],c['id']))
    for backend,color,label,marker in [('full_scan',GRAY,'Scan','x'),('heap',BLUE,'Heap','o')]:
        for i,case in enumerate(cases):
            runs = [r for r in case['runs'] if r['backend']==backend]
            cpu = statistics.median(r['cpu_seconds'] for r in runs)
            complete = sum(r['completed'] for r in runs)
            ax.scatter(case['n'],cpu,color=color,marker=marker,s=21,
                       facecolors='none' if marker=='o' and complete<3 else color,
                       label=label if i==0 else None)
    ax.axhline(5,color=ORANGE,lw=1,ls='--',label='5 s target')
    ax.set_yscale('log');ax.set_xlabel('SNAP vertices');ax.set_ylabel('Median process CPU (s)')
    ax.set_ylim(1.9,6.3);ax.set_yticks([2,3,5],['2','3','5'])
    ax.text(.06,.31,'GrQc: 6/6 heap runs complete',transform=ax.transAxes,
            color=BLUE,fontsize=9,fontweight='bold')
    ax.text(.06,.20,'Other sources: 1/18 complete',transform=ax.transAxes,
            color=ORANGE,fontsize=9)
    ax.set_title('(b) All assigned large-graph runs',loc='left',fontweight='bold')
    ax.grid(alpha=.15);ax.minorticks_off()
    ax.legend(loc='upper left',bbox_to_anchor=(0,1.48),ncol=3,
              handlelength=1,columnspacing=.7,handletextpad=.3,frameon=False,fontsize=9)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper left',
               bbox_to_anchor=(.14,1),ncol=2,frameon=False,fontsize=9)
    fig.text(.5,.02,'Same AST; 3 paired repeats; hollow point = at least one failed repetition',ha='center',fontsize=9)
    save(fig,'heap_execution_v04')


def main():
    summary = {name:analyse(ROOT/f'experiments/runs/v04/heap_{name}_v04_001.tar.gz',name)
               for name in ('fresh','sparse')}
    OUT.mkdir(exist_ok=True)
    (OUT/'heap_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    lines = ['# Fixed-AST heap execution analysis','','Three repeated paired executions use the unchanged TRAIN-frozen primary and degree ASTs. Failures remain null; CPU/work ratios require both backends complete. Source-cluster bootstrap uses the per-context median ratio, not repeated timings as independent graph samples.','','| Population/AST | Assigned contexts | Assessable pairs | Mean context-median CPU ratio (95% CI) | Work ratio |','|---|---:|---:|---:|---:|']
    for name,s in summary.items():
        for group,g in s['groups'].items():
            c,w=g['cpu_ratio_conditional'],g['work_ratio_conditional']
            text=f"{c['estimate']:.4f} [{c['lower']:.4f}, {c['upper']:.4f}]" if c else 'unassessable'
            lines.append(f"| {name}/{group} | {g['assigned_contexts']} | {g['assessable_pairs']} | {text} | {w['estimate']:.4f} |" if w else f"| {name}/{group} | {g['assigned_contexts']} | {g['assessable_pairs']} | {text} | unassessable |")
        lines += ['',f"{name} assigned/completed counts: `{json.dumps(s['coverage'],sort_keys=True)}`.",'']
    lines += ['The four SNAP sources supply eight fixed contexts; their two weight modes share topology. This is a post-diagnostic execution extension, not a change to the original confirmatory quality study. Missing full-run parity is unassessable, and a timing ratio is not a solution-quality comparison. CPU target overshoot remains observed. No model or conditional oracle participates online.','']
    (ROOT/'docs/HEAP_RESULT_ANALYSIS_V04.md').write_text('\n'.join(lines),encoding='utf-8')
    style();plot(summary)
    print(json.dumps({n:s['coverage'] for n,s in summary.items()}))


if __name__ == '__main__':main()
