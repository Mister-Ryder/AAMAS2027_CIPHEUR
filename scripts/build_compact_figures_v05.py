"""Presentation-only independent panels from unchanged V05 analysis arrays.

No archive execution, estimation, selection, resampling or numerical analysis.
Native panel width is 3.35 inches; use at least this printed width for 9pt text.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'paper/figures'
REPORT = ROOT/'docs/COMPACT_FIGURES_V05.md'
BLUE, PURPLE, ORANGE, GRAY, INK = '#176B9B', '#71559C', '#D36B32', '#687782', '#243640'
ARMS = ('witness', 'relations', 'objective')
ARM_STYLE = {'witness':(PURPLE,'o','-','A Witness'),
             'relations':(BLUE,'s','--','B Relations'),
             'objective':(GRAY,'^',':','C Objective')}
CONTROL_STYLE = (('baseline','Degree',GRAY,'^','-.'),
                 ('rule_v03','Rule only',BLUE,'s','-'),
                 ('free_v03','Free',ORANGE,'o','--'))
REGIME_STYLE = (('balanced','Bal.',PURPLE,'o','-'),
                ('ground_scarce','Ground',BLUE,'s','--'),
                ('satellite_scarce','Sat.',ORANGE,'^','-.'))
POPULATION_STYLE = (('standard','Standard',BLUE,'o','-'),
                    ('dense_long','Dense',PURPLE,'s','--'),
                    ('c3','C3',ORANGE,'^','-.'))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def style():
    font_manager.findfont('Arial', fallback_to_default=False)
    plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.labelsize':9,
        'axes.titlesize':9,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,
        'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,
        'axes.edgecolor':GRAY,'axes.labelcolor':INK,'text.color':INK,
        'xtick.color':INK,'ytick.color':INK,'figure.facecolor':'white','savefig.facecolor':'white'})


def read_inputs():
    paths = [ROOT/'experiments/analysis/v05'/name for name in
             ('effect_curves.json','matched_train_analysis_v05.json','matched_results_v05.json')]
    documents = [json.loads(p.read_text(encoding='utf-8')) for p in paths]
    effect, train, final = documents
    assert train['stage'] == 'TRAIN_only' and train['test_results_read'] is False
    assert train['train']['curves'] == final['train']['curves'], 'TRAIN prefix arrays changed after TEST'
    assert effect['selection_permitted'] is False
    return effect, train['train']['curves'], {p.relative_to(ROOT).as_posix():digest(p) for p in paths}


def panel(height=1.70):
    fig = plt.figure(figsize=(3.35,height))
    ax = fig.add_axes([.18,.255,.805,.555])
    ax.tick_params(pad=2,length=3)
    ax.xaxis.labelpad = 3
    ax.yaxis.labelpad = 3
    ax.grid(axis='y',alpha=.15,lw=.5)
    return fig, ax


def checked_line(ax,x,y,checks,**kwargs):
    line, = ax.plot(x,y,**kwargs)
    np.testing.assert_array_equal(np.asarray(line.get_xdata()),np.asarray(x))
    np.testing.assert_array_equal(np.asarray(line.get_ydata()),np.asarray(y))
    checks['line_x_arrays'] += 1
    checks['line_y_arrays'] += 1
    return line


def checked_band(ax,x,lo,hi,color,checks):
    x,lo,hi = [np.asarray(value,dtype=float) for value in (x,lo,hi)]
    band = ax.fill_between(x,lo,hi,color=color,alpha=.10,linewidth=0)
    expected = np.vstack(((x[0],hi[0]),np.column_stack((x,lo)),
                          (x[-1],hi[-1]),np.column_stack((x,hi))[::-1],(x[0],hi[0])))
    assert len(band.get_paths()) == 1
    np.testing.assert_array_equal(band.get_paths()[0].vertices,expected)
    checks['confidence_band_vertices'] += 1
    return band


def legend(fig,handles):
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.56,1.005),
        ncol=3,frameon=False,handlelength=1.25,handletextpad=.3,
        columnspacing=.65,borderaxespad=.1)


def build_panels(effect,curves):
    """Return live figures so an independent reviewer can inspect artists."""
    style()
    checks = {'line_x_arrays':0,'line_y_arrays':0,'confidence_band_vertices':0,
              'missing_prefix_cells':0,'block_curves':0}
    output = {}
    fig,ax = panel(); handles=[]
    for regime,label,color,marker,ls in REGIME_STYLE:
        rows = effect['quality']['rule_only_gain_by_regime']['dense_long'][regime]
        x = [r['n'] for r in rows]
        y,lo,hi = [[r[k] for r in rows] for k in ('estimate','lower','upper')]
        handles.append(checked_line(ax,x,y,checks,color=color,marker=marker,ls=ls,lw=1.25,ms=3.5,label=label))
        checked_band(ax,x,lo,hi,color,checks)
    ax.axhline(0,color=INK,lw=.7)
    ax.set_xscale('log',base=2)
    ax.set(xlabel='Contacts n',ylabel='Final gain (pp)')
    ax.set_xticks([64,128,256],['64','128','256']);legend(fig,handles)
    output['effect_gain_compact_v05'] = fig

    fig,ax = panel(); handles=[]
    for control,label,color,marker,ls in CONTROL_STYLE:
        curve = effect['quality']['pointwise_curves']['dense_long'][control]
        x,y,lo,hi = [np.asarray(curve[k]) for k in ('grid','estimate','lower','upper')]
        handles.append(checked_line(ax,x,y,checks,color=color,ls=ls,lw=1.25,label=label,
                                     zorder=5 if control=='baseline' else 4))
        checked_band(ax,x,lo,hi,color,checks)
        checked_line(ax,x[-1:],y[-1:],checks,color=color,marker=marker,ls='none',ms=3.5)
        if control=='baseline':
            checked_line(ax,x[20:100:20],y[20:100:20],checks,color=color,marker=marker,ls='none',ms=3,zorder=6)
    ax.axhline(0,color=INK,lw=.7)
    ax.set(xlim=(-.01,1.01),xlabel='Eliminated fraction',ylabel='Prefix gain (pp)')
    ax.set_xticks([0,.25,.5,.75,1],['0','.25','.50','.75','1']);legend(fig,handles)
    output['effect_trajectory_compact_v05'] = fig

    x = np.arange(1,13)
    fig,ax = panel(); handles=[]
    for arm in ARMS:
        color,marker,ls,label = ARM_STYLE[arm]
        c = curves[arm]
        assert len(c['blocks']) == 4
        for block in c['blocks']:
            checked_line(ax,x,block['eligible_yield'],checks,color=color,alpha=.23,lw=.75)
            checks['block_curves'] += 1
        # Coincident A/B values remain unshifted. An open circle around the
        # smaller square exposes both identities rather than hiding A's trace.
        handles.append(checked_line(ax,x,c['mean_eligible_yield'],checks,color=color,
            marker=marker,ms=4.7 if arm=='witness' else 2.5,
            markerfacecolor='white' if arm=='witness' else color,
            markeredgewidth=.9,lw=1.45 if arm=='witness' else 1.15,ls=ls,label=label))
    ax.set(xlim=(.7,12.3),ylim=(-.25,12.35),xlabel='Original slot',ylabel='Eligible count')
    ax.set_xticks(x);ax.set_yticks([0,3,6,9,12]);legend(fig,handles)
    output['llm_yield_compact_v05'] = fig

    fig = plt.figure(figsize=(3.35,1.85))
    ax = fig.add_axes([.18,.57,.805,.255])
    strip = fig.add_axes([.18,.23,.805,.22],sharex=ax)
    ax.grid(axis='y',alpha=.15,lw=.5);ax.tick_params(pad=2,length=3,labelbottom=False)
    handles=[]
    for arm in ARMS:
        color,marker,ls,label = ARM_STYLE[arm];c=curves[arm]
        for block in c['blocks']:
            values=np.asarray([np.nan if value is None else value for value in block['best_eligible_train_J']])
            assert np.array_equal(np.isnan(values),[value is None for value in block['best_eligible_train_J']])
            checked_line(ax,x,values,checks,color=color,alpha=.30,lw=.75)
            checks['block_curves'] += 1
        values=np.asarray([np.nan if value is None else value for value in c['mean_best_eligible_train_J']])
        assert np.array_equal(np.isnan(values),[value is None for value in c['mean_best_eligible_train_J']])
        handles.append(checked_line(ax,x,values,checks,color=color,marker=marker,ms=3,lw=1.2,ls=ls,label=label))
    ax.set(xlim=(.7,12.3),ylabel='TRAIN J');ax.yaxis.labelpad=3
    ax.set_yticks([.95,.965,.98],['.950','.965','.980'])
    strip.set(ylim=(-.5,2.5),xlabel='Original slot')
    strip.set_xticks(x);strip.set_yticks([0,1,2],['C','B','A'])
    strip.tick_params(length=0,pad=2);strip.xaxis.labelpad=3
    strip.spines['left'].set_visible(False);strip.spines['bottom'].set_visible(False)
    for index,arm in enumerate(ARMS):
        for slot,count in enumerate(curves[arm]['no_eligible_banks'],1):
            text=strip.text(slot,2-index,str(count),ha='center',va='center',fontsize=9,
                            color=ORANGE if count else '#AAB4BB')
            assert text.get_text()==str(count) and text.get_position()==(slot,2-index)
            checks['missing_prefix_cells'] += 1
    fig.text(.18,.48,'No eligible bank (of 4)',fontsize=9,color=GRAY)
    legend(fig,handles)
    output['llm_utility_compact_v05'] = fig

    fig,ax = panel();handles=[]
    for population,label,color,marker,ls in POPULATION_STYLE:
        rows=effect['heap']['curves'][population]
        x=[r['n'] for r in rows]
        y,lo,hi=[[r[k] for r in rows] for k in ('estimate','lower','upper')]
        handles.append(checked_line(ax,x,y,checks,color=color,marker=marker,ls=ls,lw=1.25,ms=3.5,label=label))
        checked_band(ax,x,lo,hi,color,checks)
    ax.axhline(1,color=INK,lw=.7)
    ax.set_xscale('log',base=2);ax.set_yscale('log')
    ax.set(xlabel='Contacts n',ylabel='Scan / heap CPU')
    ax.set_xticks([64,128,256,512],['64','128','256','512'])
    ax.set_yticks([1,2,4,8,16,32],['1','2','4','8','16','32']);legend(fig,handles)
    output['heap_scaling_compact_v05'] = fig
    for figure in output.values():
        for axes in figure.axes:
            axes.minorticks_off()
    return output,checks


def validate_text(fig):
    fig.canvas.draw(); renderer=fig.canvas.get_renderer(); box=fig.bbox
    # Axis keeps cached tick artists outside the view interval, but its draw
    # routine does not render them. Check the actual displayed labels only.
    outside_ticks=set()
    for axes in fig.axes:
        for axis in (axes.xaxis,axes.yaxis):
            low,high=sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                if not low <= tick.get_loc() <= high:
                    outside_ticks.update((id(tick.label1),id(tick.label2)))
    failures=[]
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text() or id(text) in outside_ticks: continue
        assert text.get_fontsize() >= 9
        extent=text.get_window_extent(renderer)
        if extent.x0 < box.x0-.5 or extent.y0 < box.y0-.5 or extent.x1 > box.x1+.5 or extent.y1 > box.y1+.5:
            failures.append(text.get_text())
    assert not failures,'Clipped figure text: '+repr(failures)


def main():
    effect,curves,sources=read_inputs();figures,checks=build_panels(effect,curves)
    lines=['# Compact scientific panels (V05)','',
        'Presentation-only panels reuse existing, unchanged analysis arrays. No experiment, resampling, selection or numerical analysis was rerun.','',
        '| Panel | Native inches | Native font | PDF SHA-256 |','|---|---:|---:|---|']
    for name,fig in figures.items():
        validate_text(fig)
        fig.savefig(OUT/(name+'.pdf'))
        fig.savefig(OUT/(name+'.png'),dpi=300)
        width,height=fig.get_size_inches()
        lines.append(f'| `{name}` | {width:.2f} × {height:.2f} | Arial ≥9pt | `{digest(OUT/(name+".pdf"))}` |')
        plt.close(fig)
    assert checks['block_curves']==24 and checks['missing_prefix_cells']==36
    assert checks['confidence_band_vertices']==9
    lines+=['','## Input identity and plotting verification','',
        'The saved TRAIN prefix curves agree exactly with the corresponding TRAIN curves in the final TRAIN/TEST report. All line x/y arrays and confidence-band polygon vertices were compared directly with the original JSON fields. The twelve four-block yield traces, twelve four-block utility traces, every arm mean, all original null utility prefixes and all 36 missing-prefix counts are retained. No intervals were recalculated.','',
        'Checks: `'+json.dumps(checks,sort_keys=True)+'`. Every visible text artist is at least 9pt at the native width; all text extents stay inside the canvas. PDF dimensions and visual rendering receive a separate independent check.','',
        '| Unchanged input | SHA-256 |','|---|---|']
    for name,expected in sources.items():
        assert digest(ROOT/name)==expected
        lines.append(f'| `{name}` | `{expected}` |')
    lines+=['','## Placement and scientific interpretation','',
        'Place each vector panel at a width of at least 3.35 inches. Two panels can occupy two roughly half-textwidth minipages; the heap panel fits a single column. Shrinking below native width would reduce nominal text below 9pt. LaTeX supplies panel labels and captions; the panels contain no report-style prose footers.','',
        'Effect panels concern the same 216 dense/long contexts; gain is primary minus rule-only, and prefix curves are primary minus Degree/rule-only/Free. The intervals remain paired source-cluster intervals. Prefix progress is eliminated-vertex fraction, not elapsed time or LLM learning. The full-population companion stays unchanged and available separately.','',
        'Pilot curves use original slots 1–12, retain four individual banks per arm and show arm-mean utility only when every bank has an eligible prefix. Null prefixes are gaps, never zero or fallback utility. The A/B/C missing-bank strip retains counts of four, three and one in objective-only early slots. Eligibility is declared-interface acyclicity, not full scalar ranking fit, and these TRAIN curves do not select prefixes with TEST outcomes.','',
        'The heap plot contains all three populations for the same frozen primary AST. Its ratios are means of per-context median full-scan/heap CPU ratios with the original confidence intervals. Execution parity and speedup do not establish LLM benefit, whole-schedule improvement or a valid sparse speedup for failed full scans.','',
        'Short legends: Bal. = balanced, Ground = ground scarce, Sat. = satellite scarce; Dense = dense/long; A Witness, B Relations, C Objective use the manuscript’s registered arm definitions.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({'panels':list(figures),'geometry_inches':{n:[3.35,1.85 if n=='llm_utility_compact_v05' else 1.70] for n in figures},'checks':checks}))


if __name__=='__main__': main()
