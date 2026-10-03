"""Outcome-independent, larger static scheduling study with disjoint day splits."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import random, json
from hashlib import sha256
from .model import Contact, Graph, temporal_graph
from .experiment_data import _record, diagnostic_pair

SPLITS = ('train','validation','test')

def temporal_pair(split, size, index, regime='balanced', profile='standard'):
    if profile not in ('standard','dense_long'):
        raise ValueError('Unknown predeclared temporal profile')
    seed = 9000000 + SPLITS.index(split)*1000000 + size*1000 + index + (100000000 if profile=='dense_long' else 0)
    rng = random.Random(seed)
    resources = {'balanced':(8,6), 'ground_scarce':(12,3), 'satellite_scarce':(3,12)}[regime]
    satellites, grounds = resources
    horizon = size * (1.8 if profile=='standard' else .18)
    shift = SPLITS.index(split)*10000000 + index*10000
    contacts = []
    for k in range(size):
        start = rng.randrange(int(horizon*4))/4
        duration = rng.randrange(2,49 if profile=='standard' else 193)/4
        contacts.append(Contact(f'v{rng.getrandbits(64):016x}', rng.randrange(1,81)/4,
                       f'S{rng.randrange(satellites)}',f'G{rng.randrange(grounds)}',
                       shift+start, shift+start+duration))
    before, after = ((0.,2.),(.25,3.5),(.5,6.))[SPLITS.index(split)]
    prefix='temporal' if profile=='standard' else 'dense_long'
    name = f'{prefix}_{split}_{regime}_{size}_{index:04d}'
    left = temporal_graph(name+'_left',contacts,station_gap=before,satellite_gap=0)
    right = temporal_graph(name+'_right',contacts,station_gap=after,satellite_gap=0)
    return _record(name,prefix+'_'+regime,left,right,{'split':split,'seed':seed,
        'origin':'v03_temporal_generator','size':size,'regime':regime,
        'horizon':horizon,'population_claim':'specified_generator_only'})

def build_study(config):
    result = {s:[] for s in SPLITS}
    per_split = config.get('per_size',{'train':8,'validation':8,'test':24})
    for split in SPLITS:
        for regime in config.get('regimes',['balanced','ground_scarce','satellite_scarce']):
            for size in config.get('sizes',[32,64,128,256]):
                for index in range(per_split[split]):
                    result[split].append(temporal_pair(split,size,index,regime,config.get('temporal_profile','standard')))
        # Keep designed probes separate from natural/source-derived quality.
        for index in range(60,60+config.get('diagnostic_per_split',20)):
            pair = diagnostic_pair(split,index)
            pair['id'] = 'v03_'+pair['id']
            result[split].append(pair)
    coverage = {'empty_blocks':[],'reused_prior_contacts':0}
    if config.get('stable_root'):
        from .v51_adapter import _load_legacy, _file_sha256, _PARAMETERS
        legacy, sources = _load_legacy(Path(config['stable_root']))
        csv = Path(config['stable_root'])/'SNSD_V51_FINAL'/'data'/'C3.csv'
        dataset = legacy['data'].load_arcs(str(csv))
        excluded = set(config.get('exclude_original_ids',()))
        used = set()
        coverage.update(data_sha256=_file_sha256(csv),total_opportunities=len(dataset.arcs),
                        excluded_prior_opportunities=len(excluded),source_files=sources)
        for day,split in enumerate(SPLITS):
            all_arcs = sorted((a for a in dataset.arcs if a.link_st//86400==day
                       and a.id not in excluded and a.link_et>a.link_st),key=lambda a:(a.link_st,a.id))
            cursor = 0
            for size in config.get('c3_sizes',[64,128,256,512]):
                for index in range(config.get('c3_per_size',{'train':3,'validation':3,'test':8})[split]):
                    selected = all_arcs[cursor:cursor+size]
                    cursor += size
                    if len(selected)!=size:
                        coverage['empty_blocks'].append({'split':split,'size':size,'index':index,
                                                        'retained':len(selected)})
                        continue
                    original_ids = [a.id for a in selected]
                    assert not used.intersection(original_ids)
                    used.update(original_ids)
                    local = tuple(replace(a,id=i) for i,a in enumerate(selected))
                    contacts = tuple(Contact(str(a.id),float(a.weight),a.satellite_name,
                                    a.ground_name,a.link_st,a.link_et) for a in selected)
                    parameter = ('ground_trans_time','satellite_change_time','satellite_trans_time')[index%3]
                    target = {'ground_trans_time':(450,600,750),
                              'satellite_change_time':(180,210,270),
                              'satellite_trans_time':(360,420,540)}[parameter][day]
                    name = f'c3_{split}_{size}_{index:04d}'
                    graphs = []
                    for label,value in (('left',_PARAMETERS[parameter]),('right',target)):
                        params = {**_PARAMETERS,parameter:value}
                        original = legacy['graph'].build_conflict_graph(local,legacy['graph'].ConflictParameters(**params))
                        edges = frozenset(tuple(sorted((str(original_ids[int(u)]),str(original_ids[int(v)]))))
                                          for u,v in original.edges)
                        graph = Graph(name+'_'+label,contacts,edges,{'model':'v51_legacy',**params},
                            {'source_data_sha256':coverage['data_sha256'],'original_ids':original_ids,
                             'scope':'time_ordered_disjoint_source_subproblem'})
                        graph._v51_context = (original,legacy['verifier'],{str(a.id):i for i,a in enumerate(selected)})
                        graphs.append(graph)
                    result[split].append(_record(name,'c3',*graphs,{'split':split,'seed':None,
                        'origin':'frozen_c3','original_ids':original_ids,'parameter':parameter,
                        'before':_PARAMETERS[parameter],'after':target,'size':size,
                        'source_data_sha256':coverage['data_sha256'],
                        'population_claim':'time_ordered_subproblems_only'}))
        coverage['unique_original_opportunities'] = len(used)
    identities = {}
    for split in SPLITS:
        for record in result[split]:
            fp = record['source']['instance_fingerprint']
            if fp in identities: raise ValueError('Duplicate contact instance')
            identities[fp] = split
    result['protocol'] = {'version':'large_static_study_v03','outcome_filtering':False,
        'split_counts':{s:len(result[s]) for s in SPLITS},'c3':coverage,
        'split_rule':'synthetic_disjoint_seed_ranges_and_C3_day_0_1_2',
        'interventions':'one_constraint_at_a_time_identical_contacts',
        'oracle_calls_during_generation':0}
    return result
