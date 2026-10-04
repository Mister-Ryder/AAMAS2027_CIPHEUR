"""Apply publication emphasis without changing any reported decimal or cell.

Run after the original table generators. Tints identify study conditions;
bold values denote the largest displayed competitive rewards, including ties.
The input observations and all failed-run denominators remain unchanged.
The paper retains every quality/coverage row; the full timing panel remains
in docs/BASELINE_COMPARISON_V05.md, with representative costs in the text.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def plain(source):
    source = re.sub(r'\\rowcolor\{blue!7\}\s*', '', source)
    source = re.sub(r'\\textbf\{([+-]?\d+(?:\.\d+)?)\}', r'\1', source)
    return source


def numeric_cells(source):
    """All decimal/numerator text, excluding captions and style color names."""
    table = source.split(r'\begin{tabular}', 1)[1]
    table = table.split(r'\end{tabular}', 1)[0]
    table = plain(table)
    return re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?', table)


def baseline():
    path = ROOT / 'paper/generated/baseline_table_v05.tex'
    original = path.read_text(encoding='utf-8')
    source = plain(original)
    caption = ('Executed baselines on seven separate populations. Cells: failure-zero '
               'competitive reward \\%, with completed-run \\% in parentheses. Native '
               'quality averages three seeds within each context; budgets are distinct. '
               'Blue identifies the study policy; bold marks the largest displayed '
               'quality per column, including ties, without significance claims.')
    source = re.sub(r'\\caption\{[^\n]*\}', lambda _: r'\caption{'+caption+'}', source, count=1)
    observations = json.loads((ROOT / 'experiments/analysis/v05/baseline_table_v05.json').read_text(encoding='utf-8'))
    methods = observations['main_method_ids']
    groups = observations['population_order']
    best = [max(round(observations['populations'][g]['methods'][m]['competitive_reward_pct'], 2) for m in methods) for g in groups]
    lines = source.splitlines()
    quality = False
    checked = 0
    for i, line in enumerate(lines):
        if 'Competitive reward (run coverage)' in line:
            quality = True
        if 'Median all-assigned elapsed time' in line:
            quality = False
        if ' & ' not in line or line.startswith('Method '):
            continue
        cells = line.split(' & ')
        if len(cells) != 8:
            continue
        if quality:
            values = [re.match(r'(\d+\.\d+) \(', c) for c in cells[1:]]
            assert all(values), 'Unexpected quality-cell syntax'
            for j, match in enumerate(values):
                value = match.group(1)
                if float(value) == best[j]:
                    cells[j+1] = cells[j+1].replace(value, r'\textbf{'+value+'}', 1)
                checked += 1
        styled = ' & '.join(cells)
        if r'\textbf{Guided primary}' in cells[0]:
            styled = r'\rowcolor{blue!7} '+styled
        lines[i] = styled
    styled = '\n'.join(lines)+'\n'
    assert checked == 84
    assert numeric_cells(styled) == numeric_cells(original)
    # Remove only the complete timing panel, never a selected quality row.
    # The independently reconstructed MD report retains all elapsed costs.
    marker = '\\midrule\n\\multicolumn{8}{l}{\\textit{Median all-assigned elapsed time (seconds)}}'
    if marker in styled:
        prefix, timing = styled.split(marker, 1)
        assert timing.count(' & ') == 12 * 7
        styled = prefix + '\\bottomrule' + timing.split('\\bottomrule', 1)[1]
    assert styled.count(' & ') == 13 * 7
    path.write_text(styled, encoding='utf-8')
    return checked


def pilot():
    path = ROOT / 'paper/generated/matched_llm_table_v05.tex'
    original = path.read_text(encoding='utf-8')
    source = plain(original)
    caption = ('Four-block matched pilot on 216 fresh graphs. Cells: failure-zero '
               'mean $100W/U$, with verified clique upper $U$. All original slots '
               'are retained. Contrasts are percentage points. Blue highlights '
               'Witness and the relations--objective contrast; four descriptive '
               'blocks establish no significance.')
    source = re.sub(r'\\caption\{[^\n]*\}', lambda _: r'\caption{'+caption+'}', source, count=1)
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('A Witness &'):
            lines[i] = r'\rowcolor{blue!7} '+line
        elif line.startswith('B$-$C &'):
            lines[i] = r'\rowcolor{blue!7} '+line.replace('mean +0.66 pp', r'mean \textbf{+0.66} pp')
    styled = '\n'.join(lines)+'\n'
    assert numeric_cells(styled) == numeric_cells(original)
    path.write_text(styled, encoding='utf-8')


def main():
    count = baseline()
    pilot()
    print(json.dumps({'quality_cells_checked': count, 'reported_numbers_unchanged': True,
                      'styles': 'study tint; largest displayed quality in bold; descriptive pilot contrast'}))


if __name__ == '__main__':
    main()
