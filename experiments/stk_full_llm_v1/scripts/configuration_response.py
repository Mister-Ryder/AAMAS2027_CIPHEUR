"""Describe frozen-schedule responses to predeclared configuration changes.

No repair, programme scoring, optimiser, model or conditional oracle. TEST
selections are opened only after explicit formal-result release. The graph is
used solely to count conflicts in already saved selections and edge changes.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import itertools
from pathlib import Path
from fractions import Fraction
import numpy as np
from analyze_comparison import (ALIASES, CONFIGS, LABELS, BASELINES, canonical, group, sha, dump, csv_dump,
                                hierarchical_mean, exact_fields, fmt, table, style, save_figure,
                                variant_label, colour, batch)

TRANSITIONS = ([('A', alias) for alias in ('M', 'J', 'stress', 'W', 'E', 'MW', 'ME')]
               + [('W', 'J'), ('E', 'J'), ('W', 'E'), ('E', 'W'), ('MW', 'ME'), ('ME', 'MW')])
REGISTRATION = {
    "version": "configuration_response_v1_pre_outcomes", "registered_before_TEST_outcomes": True,
    "fixed_directed_changes": TRANSITIONS,
    "pairing": "Same physical source, method/programme, declared CPU budget and seed; only configuration changes.",
    "invariants": "Identical node indices/contact IDs and exact integer weights across all8 configurations of a source; graph and metadata SHA must match saved result identities.",
    "metrics": ["new/deleted graph conflict edges", "old selected schedule conflicts in new graph", "unique old-selected conflict-endpoint count and summed reward ticks", "old/new schedule Jaccard", "saved final complete reward delta ticks", "removed/added selected contact count and reward ticks"],
    "conflicted_reward_interpretation": "Sum of unique selected vertices touching at least one new-graph violation. Not minimum loss, not a lower bound on required repair loss, not an optimized removal set.",
    "quality_interpretation": "New and old final qualities are paid saved result values under different constraints. Their difference is not a same-instance algorithm ranking or superiority claim.",
    "statistical_unit": "r008/r009 physical source groups; seeds/config transitions/AU/AP geometries are repeated observations, not independent samples.",
    "aggregation": "Equal seeds within transition/source, equal AU/AP geometries within source group, equal2groups. Each transition separate; if aggregated, transition weights equal.",
    "controls": "All frozen programmes and baselines, both LLM batches. No data-based transition selection.",
    "figure": "Compact2x2: graph added/deleted edges; stale selected conflict count; new/old Jaccard; changed selected reward. Main axes include all fixed directed transitions, programmes retain same colour and batch markers. Exact per-source table accompanies graphic.",
    "not_executed": ["repair", "optimizer", "LLM", "oracle", "parameter tuning", "programme scoring", "TEST selection"],
}


def load_projection(paths, protocol):
    records = {}; evidence = []
    for path in paths:
        obj = json.loads(Path(path).read_text(encoding="utf-8")); evidence.append({"path": str(Path(path).resolve()), "sha256": sha(path)})
        if obj.get("metrics_rewritten") is not False or obj.get("no_graphs_opened") is not True:
            raise ValueError("Use selection-only frozen formal projection")
        for r in obj["records"]:
            if r["split"] != "test": continue
            if r["source"] not in protocol["test_sources"] or r["protocol_sha256"] != obj["protocol_sha256"]:
                raise ValueError("Unfrozen TEST selection")
            if r["method"] == "program" and (r["program_id"] not in protocol["final_program_ids"] or r["program_bank_sha256"] != protocol["frozen_program_bank_sha256"]):
                raise ValueError("Unselected TEST programme")
            if r['seed'] not in protocol['seeds'] or float(r['declared_cpu_seconds']) not in protocol['budgets_seconds']:
                raise ValueError('Unregistered TEST seed/budget')
            variant = r["program_id"] if r["method"] == "program" else r["method"]
            cfg = canonical(r.get("graph_config_id") or r["config"])
            key = (r["source"], variant, float(r["declared_cpu_seconds"]), r["seed"], cfg)
            if key in records: raise ValueError("Duplicate saved TEST selection")
            selection_sha = hashlib.sha256(json.dumps(r["selected"]).encode()).hexdigest()
            if selection_sha != r["selected_set_sha256"]: raise ValueError("Projection selection hash mismatch")
            r = dict(r, variant=variant, config=cfg); records[key] = r
    return records, evidence


def load_source(graph_root, source, selections):
    graphs = {}; origin = None; receipts = []
    for cfg in CONFIGS:
        path = graph_root / source / (cfg + ".npz"); meta_path = path.with_suffix(".json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")); graph_sha = sha(path); meta_sha = sha(meta_path)
        if meta["source_id"] != source or meta["config_id"] != cfg or meta["split"] != "test" or meta["npz_sha256"] != graph_sha:
            raise ValueError("TEST graph metadata/source/SHA differs")
        with np.load(path, allow_pickle=False) as z:
            graph = {k: z[k].copy() for k in ('contact_id', 'weight_ticks', 'edge_u', 'edge_v')}
        n = len(graph['weight_ticks']); u, v = graph['edge_u'], graph['edge_v']
        if np.any(u >= v) or np.any(u < 0) or np.any(v >= n): raise ValueError("Invalid frozen edge indices")
        graph['keys'] = u.astype(np.int64) * n + v.astype(np.int64)
        if len(graph['keys']) > 1 and np.any(np.diff(graph['keys']) <= 0): raise ValueError("Unsorted/duplicate frozen graph edges")
        if origin is None: origin = (graph['contact_id'], graph['weight_ticks'])
        elif not all(np.array_equal(a, b) for a, b in zip(origin, (graph['contact_id'], graph['weight_ticks']))):
            raise ValueError("Node identities/weights changed across configurations")
        for result in selections:
            if result['config'] == cfg and (result['input_graph_sha256'] != graph_sha or result['metadata_sha256'] != meta_sha):
                raise ValueError("Saved selection and graph/meta SHA differ")
        graph.update(n=n, sha256=graph_sha, metadata_sha256=meta_sha); graphs[cfg] = graph
        receipts.append({"source": source, "config": cfg, "npz_sha256": graph_sha, "metadata_sha256": meta_sha})
    return graphs, receipts


def selection_mask(record, graph):
    selected = record['selected']
    if selected != sorted(set(selected)) or any(not isinstance(i, int) or i < 0 or i >= graph['n'] for i in selected):
        raise ValueError("Invalid saved final selected indices")
    mask = np.zeros(graph['n'], dtype=bool); mask[selected] = True
    if np.any(mask[graph['edge_u']] & mask[graph['edge_v']]): raise ValueError("Final selected schedule violates its original frozen graph")
    # Checking saved sum/feasibility is not an algorithm call or fresh policy score.
    if sum(int(graph['weight_ticks'][i]) for i in selected) != record['value_ticks'] or record['feasible'] is not True:
        raise ValueError("Saved complete quality/feasibility differs from saved selection")
    return mask


def describe(old, new, old_graph, new_graph, old_mask, new_mask, edge_changes):
    stale = old_mask[new_graph['edge_u']] & old_mask[new_graph['edge_v']]
    conflicted_nodes = np.unique(np.concatenate((new_graph['edge_u'][stale], new_graph['edge_v'][stale])))
    intersection = int(np.count_nonzero(old_mask & new_mask)); union = int(np.count_nonzero(old_mask | new_mask))
    removed = np.flatnonzero(old_mask & ~new_mask); added = np.flatnonzero(new_mask & ~old_mask)
    sg, geometry = group(old['source']); w = old_graph['weight_ticks']
    delta = int(new['value_ticks']) - int(old['value_ticks'])
    row = {'source': old['source'], 'source_group': sg, 'geometry': geometry, 'variant': old['variant'], 'method': old['method'],
           'program_id': old['program_id'], 'arm': old.get('program_arm') or old['method'], 'seed': old['seed'],
           'budget': float(old['declared_cpu_seconds']), 'declared_cpu_seconds': float(old['declared_cpu_seconds']),
           'old_config': old['config'], 'new_config': new['config'], 'config': old['config'] + '->' + new['config'],
           'graph_added_edges': edge_changes[0], 'graph_deleted_edges': edge_changes[1],
           'stale_schedule_conflict_edges': int(np.count_nonzero(stale)), 'stale_schedule_conflicted_nodes': len(conflicted_nodes),
           'stale_conflicted_reward_ticks': sum(int(w[i]) for i in conflicted_nodes),
           'old_selected_count': int(np.count_nonzero(old_mask)), 'new_selected_count': int(np.count_nonzero(new_mask)),
           'selected_intersection': intersection, 'selected_union': union, 'jaccard_exact': str(Fraction(intersection, union) if union else Fraction(1)),
           'jaccard': intersection / union if union else 1., 'removed_contacts': len(removed), 'added_contacts': len(added),
           'removed_reward_ticks': sum(int(w[i]) for i in removed), 'added_reward_ticks': sum(int(w[i]) for i in added),
           'saved_quality_delta_ticks': delta, 'saved_quality_delta_seconds_exact': str(Fraction(delta, 1_000_000)),
           'old_result_sha256': old['result_sha256'], 'new_result_sha256': new['result_sha256'],
           'old_graph_sha256': old_graph['sha256'], 'new_graph_sha256': new_graph['sha256'],
           'conflicted_reward_is_minimum_loss': False}
    return row


def summaries(rows):
    buckets = defaultdict(list)
    for r in rows: buckets[(r['variant'], r['budget'], r['old_config'], r['new_config'])].append(r)
    output = []
    metrics = ['graph_added_edges', 'graph_deleted_edges', 'stale_schedule_conflict_edges', 'stale_schedule_conflicted_nodes',
               'stale_conflicted_reward_ticks', 'removed_contacts', 'added_contacts', 'removed_reward_ticks', 'added_reward_ticks', 'saved_quality_delta_ticks']
    for (variant, budget, old, new), vals in sorted(buckets.items()):
        item = {'variant': variant, 'arm': vals[0]['arm'], 'budget': budget, 'old_config': old, 'new_config': new, 'runs': len(vals)}
        for metric in metrics:
            value, groups, _ = hierarchical_mean(vals, lambda r: Fraction(int(r[metric])))
            item.update(exact_fields('mean_' + metric, value)); item[metric + '_groups_exact'] = {sg: str(v) for sg, v in groups.items()}
        value, groups, _ = hierarchical_mean(vals, lambda r: Fraction(r['jaccard_exact']))
        item.update(exact_fields('mean_jaccard', value)); item['jaccard_groups_exact'] = {sg: str(v) for sg, v in groups.items()}
        item['independent_physical_groups'] = len(groups); output.append(item)
    return output


def make_plot(output, summary, bank, protocol):
    if not summary: return {'status': 'unavailable', 'reason': 'no fixed transition pairs'}
    plt = style(); fig, axs = plt.subplots(2, 2, figsize=(7.1, 4.3), constrained_layout=True)
    # One common declared budget per panel is fixed, not chosen for effect.
    budget = 10.; selected = protocol['final_program_ids']; labels = [a + '→' + b for a, b in TRANSITIONS]
    lookup = {(s['variant'], s['budget'], s['old_config'], s['new_config']): s for s in summary}
    # Graph changes independent of method; retain actual first available source-group aggregates.
    for i, (old, new) in enumerate(TRANSITIONS):
        graphrow = next((s for s in summary if s['budget'] == budget and s['old_config'] == ALIASES[old] and s['new_config'] == ALIASES[new]), None)
        if graphrow:
            axs[0, 0].bar(i - .17, graphrow['mean_graph_added_edges'], width=.32, color='#0072B2')
            axs[0, 0].bar(i + .17, -graphrow['mean_graph_deleted_edges'], width=.32, color='#D55E00')
    axs[0, 0].set_ylabel('Added (+) / deleted (−) conflict edges')
    for pid in selected:
        vals = [lookup.get((pid, budget, ALIASES[a], ALIASES[b])) for a, b in TRANSITIONS]
        kw = {'color': colour(pid, bank), 'marker': 'o', 'markersize': 3, 'markerfacecolor': 'none' if batch(bank[pid]) == 1 else colour(pid, bank), 'linestyle': 'None', 'label': variant_label(pid, bank)}
        xs = [i for i, s in enumerate(vals) if s]
        axs[0, 1].plot(xs, [vals[i]['mean_stale_schedule_conflict_edges'] for i in xs], **kw)
        axs[1, 0].plot(xs, [vals[i]['mean_jaccard'] for i in xs], **kw)
        axs[1, 1].plot(xs, [(vals[i]['mean_removed_reward_ticks'] + vals[i]['mean_added_reward_ticks']) / 1_000_000 for i in xs], **kw)
    axs[0, 1].set_ylabel('Old schedule conflicts in new graph')
    axs[1, 0].set_ylabel('Final schedule Jaccard'); axs[1, 0].set_ylim(-.02, 1.02)
    axs[1, 1].set_ylabel('Removed + added selected reward (s)')
    for ax in axs.flat:
        ax.set_xticks(range(len(TRANSITIONS)), labels, rotation=60, ha='right', fontsize=5.8); ax.grid(axis='y')
    axs[0, 1].legend(ncol=2, loc='best')
    paths = save_figure(fig, list(axs.flat), output, 'fig05_configuration_change', plt)
    return {'status': 'rendered', 'paths': paths, 'budget': budget, 'caption': 'Fixed directed configuration changes,10s declared budget. Graph edges change with resource policy; old selections can become invalid and frozen-programme final selections differ. Two physical groups averaged equally. Conflict-endpoint reward is not minimum repair loss; cross-configuration final quality is not same-instance algorithm superiority.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True); ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--released-formal-results', action='store_true'); ap.add_argument('--selections', type=Path, action='append', default=[])
    ap.add_argument('--graph-root', type=Path); ap.add_argument('--protocol', type=Path); ap.add_argument('--program-bank', type=Path)
    ap.add_argument('--allow-partial', action='store_true'); ap.add_argument('--no-plots', action='store_true')
    a = ap.parse_args()
    if a.prepare:
        if a.selections or a.graph_root or a.protocol or a.program_bank: raise ValueError('Registration cannot read inputs/results')
        dump(a.output / 'configuration_response.registration.json', REGISTRATION); print('Fixed transition registration saved; no TEST selections opened.'); return
    if not a.released_formal_results or not a.selections or not a.graph_root or not a.protocol or not a.program_bank:
        ap.error('Released formal selections, frozen protocol/bank and graph root required')
    protocol = json.loads(a.protocol.read_text(encoding='utf-8')); bank = {v['id']: v for v in json.loads(a.program_bank.read_text(encoding='utf-8'))['programs']}
    if protocol.get('frozen') is not True or sha(a.program_bank) != protocol['frozen_program_bank_sha256']: raise ValueError('Frozen programme contract differs')
    saved = a.output / 'configuration_response.registration.json'
    if saved.is_file() and json.loads(saved.read_text(encoding='utf-8')) != json.loads(json.dumps(REGISTRATION)): raise ValueError('Registered transitions changed')
    records, evidence = load_projection(a.selections, protocol)
    if any(r['protocol_sha256'] != sha(a.protocol) for r in records.values()): raise ValueError('Saved selection uses another protocol')
    rows, graph_receipts, missing = [], [], []
    for source in protocol['test_sources']:
        source_records = [r for r in records.values() if r['source'] == source]
        graphs, receipts = load_source(a.graph_root, source, source_records); graph_receipts.extend(receipts)
        masks = {k: selection_mask(r, graphs[r['config']]) for k, r in records.items() if r['source'] == source}
        prefixes = [(source, variant, float(budget), seed) for variant, budget, seed in
                    itertools.product(BASELINES + protocol['final_program_ids'], protocol['budgets_seconds'], protocol['seeds'])]
        edge_changes = {(ALIASES[x], ALIASES[y]):
                        (len(np.setdiff1d(graphs[ALIASES[y]]['keys'], graphs[ALIASES[x]]['keys'], assume_unique=True)),
                         len(np.setdiff1d(graphs[ALIASES[x]]['keys'], graphs[ALIASES[y]]['keys'], assume_unique=True)))
                        for x, y in TRANSITIONS}
        for prefix in prefixes:
            for oldalias, newalias in TRANSITIONS:
                oldkey, newkey = prefix + (ALIASES[oldalias],), prefix + (ALIASES[newalias],)
                if oldkey not in records or newkey not in records: missing.append({'pair': list(prefix), 'change': [oldalias, newalias]}); continue
                old, new = records[oldkey], records[newkey]
                rows.append(describe(old, new, graphs[old['config']], graphs[new['config']], masks[oldkey], masks[newkey], edge_changes[(old['config'], new['config'])]))
    if missing and not a.allow_partial: raise ValueError('Missing predeclared config pairs; --allow-partial needed for incomplete progress only')
    summary = summaries(rows); a.output.mkdir(parents=True, exist_ok=True)
    csv_dump(a.output / 'configuration_response_runs.csv', rows); csv_dump(a.output / 'configuration_response_summary.csv', summary)
    receipt = make_plot(a.output, summary, bank, protocol) if not a.no_plots else {'status': 'not_requested'}
    dump(a.output / 'configuration_response.audit.json', {'version': REGISTRATION['version'], 'fixed_registration': REGISTRATION,
          'inputs': evidence, 'graph_receipts': graph_receipts, 'missing_pairs': missing, 'partial': bool(missing), 'figure': receipt,
          'optimizer_calls': 0, 'model_calls': 0, 'oracle_calls': 0, 'repair_calls': 0, 'programme_score_calls': 0,
          'script_sha256': sha(Path(__file__)), 'protocol_sha256': sha(a.protocol)})
    lines = ['# 配置变化与完整调度响应', '', '所有变化边在读取TEST结果前固定。仅描述冻结结果与输入图的结构变化，不重新优化或择优。统计单位为r008/r009，两组等权；配置、种子和AU/AP不是额外独立样本。', '',
             '**旧选择的冲突节点收益是所有涉冲突节点的收益总和，既不是最小修复损失，也不是必要损失下界。**新旧最终质量差发生在不同约束图中，不能当成同实例算法排名。', '',
             table(['程序/方法', '预算s', '旧→新W/E', '图新增边', '图删除边', '旧调度冲突边', 'Jaccard', '涉冲突收益s', '最终质量差s'],
                   [[s['variant'], int(s['budget']), LABELS[s['old_config']] + '→' + LABELS[s['new_config']], fmt(s['mean_graph_added_edges']), fmt(s['mean_graph_deleted_edges']), fmt(s['mean_stale_schedule_conflict_edges']), fmt(s['mean_jaccard']), fmt(s['mean_stale_conflicted_reward_ticks'] / 1_000_000), fmt(s['mean_saved_quality_delta_ticks'] / 1_000_000)] for s in summary]), '',
             '配对原始精确值：`configuration_response_runs.csv`；每组精确聚合：`configuration_response_summary.csv`；图/身份/SHA与缺失记录：`configuration_response.audit.json`。', '',
             '图状态：' + receipt['status'] + '。' + receipt.get('caption', ''), '']
    (a.output / '配置变化分析.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'pairs': len(rows), 'missing': len(missing), 'response_summary': len(summary)}, ensure_ascii=False))

if __name__ == '__main__': main()
