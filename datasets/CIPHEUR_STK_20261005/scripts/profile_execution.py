"""Plot recorded interface diagnostics; never execute an optimization solver."""
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

parser = argparse.ArgumentParser()
parser.add_argument('--data-root', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
root = args.data_root.resolve()
stage = root/'analysis/patch_interface_probe'
sources = ['CP-AU-r000', 'CP-AP-r000', 'CP-AU-r001', 'CP-AP-r001']
rows, receipts = [], []
for source in sources:
    manifest_path = stage/source/'query_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    sizes = {q['id']: len(q['patch_indices']) for q in manifest['queries']}
    for path in sorted((stage/source/'bb_traces').glob('*.json')):
        content = path.read_bytes()
        receipts.append({'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(content).hexdigest()})
        for row in json.loads(content):
            rows.append({**row, 'patch_size': sizes[row['query_id']], 'source': source})
heads = ['degree', 'existing_frozen', 'certified_reference']
sizes = [16, 64, 128]
summary = {'scope': 'TRAIN bounded interface diagnostics, not new LLM synthesis or full-schedule method evaluation',
           'states_are_correlated': True, 'source_groups': 2, 'per_size': [], 'sources': receipts}
deltas = {}
for size in sizes:
    selected = [r for r in rows if r['patch_size'] == size]
    paired = {}
    for row in selected:
        paired.setdefault((row['query_id'], row['side']), {})[row['head']] = row
    differences = [float(Fraction(v['existing_frozen']['lower_exact']) - Fraction(v['degree']['lower_exact'])) for v in paired.values()]
    deltas[size] = np.asarray(differences)
    summary['per_size'].append({'patch_size': size, 'states': len(paired),
        'different_values_states': sum(len({r['lower_exact'] for r in v.values()}) > 1 for v in paired.values()),
        'frozen_minus_degree_mean_seconds': float(np.mean(differences)),
        'frozen_win_loss_tie': [sum(d > 0 for d in differences), sum(d < 0 for d in differences), sum(d == 0 for d in differences)],
        'per_head': {head: {'rows': sum(r['head'] == head for r in selected),
            'restricted_exact_rows': sum(r['head'] == head and r['restricted_exact'] for r in selected),
            'wall_seconds': sum(r['total_wall_seconds'] for r in selected if r['head'] == head)} for head in heads}})
out = root/'analysis/figures'; out.mkdir(exist_ok=True)
(root/'analysis/execution_profile.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
    'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42})
fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.2), constrained_layout=True)
colors = ['#285d80', '#b85e23', '#7a6a9a']
labels = ['Degree', 'Existing frozen control', 'Certified diagnostic reference']
for head, color, label, marker in zip(heads, colors, labels, ['o', 's', '^']):
    y = [entry['per_head'][head]['restricted_exact_rows']/entry['per_head'][head]['rows'] for entry in summary['per_size']]
    axes[0].plot(sizes, y, color=color, marker=marker, label=label, linewidth=1.5)
axes[0].set_xscale('log', base=2); axes[0].set_xticks(sizes, labels=[str(s) for s in sizes])
axes[0].set_ylim(-.04, 1.04); axes[0].yaxis.set_major_formatter(PercentFormatter(1))
axes[0].set_xlabel('Actual number of patch activities')
axes[0].set_ylabel('Restricted-optimum rate')
axes[0].set_title('(a) Fixed 2,000-node allowance', loc='left', fontsize=11)
axes[0].legend(loc='upper right', fontsize=8, frameon=False)
for size, color, style in [(64, '#285d80', '--'), (128, '#b85e23', '-')]:
    values = np.sort(deltas[size])
    axes[1].step(values, np.arange(1, len(values)+1)/len(values), where='post',
                 color=color, linestyle=style, linewidth=1.8, label=f'{size} activities (n={len(values)})')
axes[1].axvline(0, color='#777777', linewidth=.8, linestyle=':')
axes[1].set_ylim(0, 1.03); axes[1].yaxis.set_major_formatter(PercentFormatter(1))
axes[1].set_xlabel('Existing frozen − Degree patch reward (s)')
axes[1].set_ylabel('Empirical cumulative fraction')
axes[1].set_title('(b) All paired outcomes, including losses', loc='left', fontsize=11)
axes[1].legend(loc='lower right', fontsize=8, frameon=False)
for axis in axes:
    axis.grid(axis='y', alpha=.18)
fig.savefig(out/'p0_execution_diagnostics.pdf')
fig.savefig(out/'p0_execution_diagnostics.png', dpi=220)
print(json.dumps({'sources': len(sources), 'rows': len(rows), 'per_size': [{k:v for k,v in e.items() if k != 'per_head'} for e in summary['per_size']]}))
