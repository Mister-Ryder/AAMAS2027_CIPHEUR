"""Produce source-backed P0 input statistics and scientific diagnostic plots."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def profile(root: Path) -> list[dict]:
    rows, distributions, receipts = [], {}, []
    for path in sorted((root / 'graphs').glob('*/summary.json')):
        summary = json.loads(path.read_text(encoding='utf-8'))
        source = summary['source_id']
        base = next(g for g in summary['graphs'] if g['ground_gap_seconds'] == 340)
        graph_path = path.parent / 'g0340.npz'
        with np.load(graph_path, allow_pickle=False) as graph:
            durations = graph['weight_ticks'].astype(float) / 1_000_000
        distributions[source] = np.sort(durations)
        q = np.quantile(durations, [0, .25, .5, .75, 1])
        for graph in sorted(summary['graphs'], key=lambda x: x['ground_gap_seconds']):
            stats = graph['stats']
            rows.append(dict(source_id=source, source_group=graph['source_group'],
                split=graph['split'], ground_gap_seconds=graph['ground_gap_seconds'],
                contacts=stats['n'], edges=stats['m'], mean_degree=stats['average_degree_2m_over_n'],
                edge_growth_from_g340=stats['m'] / base['stats']['m'] - 1,
                duration_min_s=q[0], duration_q25_s=q[1], duration_median_s=q[2],
                duration_q75_s=q[3], duration_max_s=q[4],
                duration_reward_identical_across_configs=summary['same_vertex_and_weight_hash_for_every_config'],
                component_count=stats['component_count']))
        receipts.append(dict(source_id=source, graph_summary=str(path.relative_to(root)),
            graph_summary_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            duration_source=str(graph_path.relative_to(root)), duration_npz_sha256=base['npz_sha256']))
    if not rows:
        raise RuntimeError('No completed graph summaries; no diagnostic measurements available')
    out = root / 'analysis'
    out.mkdir(exist_ok=True)
    with (out / 'dataset_profile.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    (out / 'dataset_profile.json').write_text(json.dumps(dict(
        scope='completed P0 TRAIN input libraries only; not method-performance results',
        independent_source_groups=len({r['source_group'] for r in rows}),
        libraries=len(distributions), graphs=len(rows), rows=rows,
        source_receipts=receipts), ensure_ascii=False, indent=2), encoding='utf-8')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9,
        'axes.spines.top':False, 'axes.spines.right':False, 'axes.linewidth':.7,
        'pdf.fonttype':42, 'ps.fonttype':42, 'savefig.facecolor':'white'})
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9), constrained_layout=True)
    colors = {'AU':'#255B87', 'AP':'#B85F26'}
    for source, values in distributions.items():
        geometry = 'AU' if '-AU-' in source else 'AP'
        replica = source.rsplit('-', 1)[-1]
        style = '-' if replica == 'r000' else '--'
        label = f'{geometry} {replica}'
        axes[0].step(values, np.arange(1, len(values)+1)/len(values),
                     where='post', lw=1.3, color=colors[geometry], ls=style, label=label)
        subset = [r for r in rows if r['source_id']==source]
        axes[1].plot([r['ground_gap_seconds'] for r in subset],
                     [r['edge_growth_from_g340'] for r in subset],
                     lw=1.3, color=colors[geometry], ls=style,
                     marker='o' if replica=='r000' else 's', markersize=3.5, label=label)
    axes[0].set(xlabel='Full-contact duration (s)', ylabel='Empirical cumulative fraction',
                title='(a) Unmodified visibility intervals', ylim=(0, 1))
    axes[1].set(xlabel='Ground switching gap (s)', ylabel='Edge growth relative to g340',
                title='(b) Same contacts, stricter constraints', xticks=[340,680,1200,1800])
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    for ax in axes:
        ax.grid(axis='y', color='#D5D5D5', lw=.5, alpha=.65)
        ax.set_axisbelow(True)
    axes[0].legend(fontsize=8, frameon=False, loc='lower right')
    figures=out/'figures'; figures.mkdir(exist_ok=True)
    fig.savefig(figures/'p0_input_diagnostics.pdf', bbox_inches='tight')
    fig.savefig(figures/'p0_input_diagnostics.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    return rows


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    result=profile(args.root)
    print(json.dumps({'graphs':len(result), 'sources':len({r['source_id'] for r in result})}))
