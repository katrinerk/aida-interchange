import json
import sys
from os.path import dirname, realpath

src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from aif import AidaJson


def is_isolated_ere(aida_json, ere_label):
    for stmt_label in aida_json.each_ere_adjacent_stmt_anyrel(ere_label):
        if not aida_json.is_typestmt(stmt_label):
            return False
    return True


def is_duplicate_statements(aida_json, stmt_1, stmt_2):
    if aida_json.stmt_subject(stmt_1) != aida_json.stmt_subject(stmt_2):
        return False
    if aida_json.stmt_predicate(stmt_1) != aida_json.stmt_predicate(stmt_2):
        return False
    if aida_json.stmt_object(stmt_1) != aida_json.stmt_object(stmt_2):
        return False
    return True


def main():
    with open(sys.argv[1], 'r') as fin:
        aida_json = AidaJson(json.load(fin))

    print('\n==========\nERE statistics\n==========')

    ent_label_list = [node_label for node_label, _ in aida_json.each_entity()]
    rel_label_list = [node_label for node_label, _ in aida_json.each_relation()]
    evt_label_list = [node_label for node_label, _ in aida_json.each_event()]
    ere_label_list = [node_label for node_label, _ in aida_json.each_ere()]

    non_iso_ent_label_list = [node_label for node_label in ent_label_list if
                              not is_isolated_ere(aida_json, node_label)]
    non_iso_rel_label_list = [node_label for node_label in rel_label_list if
                              not is_isolated_ere(aida_json, node_label)]
    non_iso_evt_label_list = [node_label for node_label in evt_label_list if
                              not is_isolated_ere(aida_json, node_label)]
    non_iso_ere_label_list = [node_label for node_label in ere_label_list if
                              not is_isolated_ere(aida_json, node_label)]

    print('# (all / non-isolated) entity nodes: {} / {}'.format(
        len(ent_label_list), len(non_iso_ent_label_list)))
    print('# (all / non-isolated) relation nodes: {} / {}'.format(
        len(rel_label_list), len(non_iso_rel_label_list)))
    print('# (all / non-isolated) event nodes: {} / {}'.format(
        len(evt_label_list), len(non_iso_evt_label_list)))
    print('# (all / non-isolated) ERE nodes: {} / {}'.format(
        len(ere_label_list), len(non_iso_ere_label_list)))

    print('\n==========\nStatement statistics\n==========')

    stmt_label_list = \
        [node_label for node_label, _ in aida_json.each_statement()]

    unique_stmt_mapping = {}
    unique_to_duplicate_stmt_dict = {}
    duplicate_to_unique_stmt_dict = {}

    stmt_cat_dict = {}

    typing_stmt_cat_list = ['Entity-Type', 'Relation-Type', 'Event-Type',
                            'ERE-Type']
    non_iso_typing_stmt_cat_list = ['non-iso ' + stmt_cat for stmt_cat in
                                    typing_stmt_cat_list]
    non_iso_unique_typing_stmt_cat_list = \
        ['non-iso unique ' + stmt_cat for stmt_cat in typing_stmt_cat_list]
    general_stmt_type_list = ['Event-Entity', 'Relation-Entity',
                              'Relation-Event', 'General']
    unique_general_stmt_type_list = ['unique ' + stmt_cat for stmt_cat
                                     in general_stmt_type_list]

    stmt_cat_list = typing_stmt_cat_list + non_iso_typing_stmt_cat_list + \
        non_iso_unique_typing_stmt_cat_list + general_stmt_type_list + \
        unique_general_stmt_type_list
    stmt_cat_counter = {stmt_cat: 0 for stmt_cat in stmt_cat_list}

    for stmt_label in stmt_label_list:
        stmt_subj = aida_json.stmt_subject(stmt_label)
        stmt_pred = aida_json.stmt_predicate(stmt_label)
        stmt_obj = aida_json.stmt_object(stmt_label)

        subj_type = aida_json.thegraph[stmt_subj]['type']

        if stmt_pred == 'type':
            stmt_cat = '{}-{}'.format(subj_type, 'Type')
        else:
            obj_type = aida_json.thegraph[stmt_obj]['type']
            stmt_cat = '{}-{}'.format(subj_type, obj_type)

        stmt_cat_dict[stmt_label] = stmt_cat

        stmt_cat_counter[stmt_cat] += 1

        if stmt_cat.endswith('-Type'):
            stmt_cat_counter['ERE-Type'] += 1

            if not is_isolated_ere(aida_json, stmt_subj):
                stmt_cat_counter['non-iso ' + stmt_cat] += 1
                stmt_cat_counter['non-iso ERE-Type'] += 1

                if (stmt_subj, stmt_obj, stmt_pred) in unique_stmt_mapping:
                    is_unique = False
                    unique_stmt_label = \
                        unique_stmt_mapping[(stmt_subj, stmt_obj, stmt_pred)]
                    unique_to_duplicate_stmt_dict[unique_stmt_label].append(
                        stmt_label)
                    duplicate_to_unique_stmt_dict[stmt_label] = \
                        unique_stmt_label
                else:
                    is_unique = True
                    unique_stmt_mapping[(stmt_subj, stmt_obj, stmt_pred)] = \
                        stmt_label
                    unique_to_duplicate_stmt_dict[stmt_label] = []
                if is_unique:
                    stmt_cat_counter['non-iso unique ' + stmt_cat] += 1
                    stmt_cat_counter['non-iso unique ERE-Type'] += 1

        else:
            stmt_cat_counter['General'] += 1

            if (stmt_subj, stmt_obj, stmt_pred) in unique_stmt_mapping:
                is_unique = False
                unique_stmt_label = unique_stmt_mapping[
                    (stmt_subj, stmt_obj, stmt_pred)]
                unique_to_duplicate_stmt_dict[unique_stmt_label].append(
                    stmt_label)
                duplicate_to_unique_stmt_dict[stmt_label] = unique_stmt_label
            else:
                is_unique = True
                unique_stmt_mapping[(stmt_subj, stmt_obj, stmt_pred)] = \
                    stmt_label
                unique_to_duplicate_stmt_dict[stmt_label] = []
            if is_unique:
                stmt_cat_counter['unique ' + stmt_cat] += 1
                stmt_cat_counter['unique General'] += 1

    stmt_count = len(stmt_label_list)

    print('# all statement nodes:', stmt_count)
    print()
    for stmt_cat in typing_stmt_cat_list:
        print(
            '# (all / non-isolated / non-isolated unique) {} '
            'statement nodes: {} / {} / {}'.format(
                stmt_cat,
                stmt_cat_counter[stmt_cat],
                stmt_cat_counter['non-iso ' + stmt_cat],
                stmt_cat_counter['non-iso unique ' + stmt_cat],
            ))
    print()
    for stmt_cat in general_stmt_type_list:
        print('# (all / unique) {} statement nodes: {} / {}'.format(
            stmt_cat, stmt_cat_counter[stmt_cat],
            stmt_cat_counter['unique ' + stmt_cat]))

    print('\n==========\nERE connectedness statistics\n==========')

    ent_metric_keys = [
        'Entity-Type statements',
        'Event-Entity statements',
        'Relation-Entity statements',
        'General statements'
    ]

    ent_node_stats = {}

    for node_label in ent_label_list:
        node_stats = {metric_key: 0 for metric_key in ent_metric_keys}
        for stmt_label in aida_json.each_ere_adjacent_stmt_anyrel(node_label):
            stmt_cat = stmt_cat_dict[stmt_label]
            node_stats['{} statements'.format(stmt_cat)] += 1
            if not stmt_cat.endswith('-Type'):
                node_stats['General statements'] += 1
        ent_node_stats[node_label] = node_stats

    non_iso_ent_node_stats = {node_label: ent_node_stats[node_label] for
                              node_label in non_iso_ent_label_list}

    ent_count = len(ent_label_list)
    non_iso_ent_count = len(non_iso_ent_label_list)

    # print('Across all {} entity nodes:'.format(ent_count))
    # for metric_key in ent_metric_keys:
    #     metric_list = [node_stats[metric_key] for node_label, node_stats in
    #                    ent_node_stats.items()]
    #     assert len(metric_list) == ent_count
    #     metric_min = min(metric_list)
    #     metric_max = max(metric_list)
    #     metric_mean = sum(metric_list) / len(metric_list)
    #     print('# of {}: min = {}, max = {}, average = {:.2f}'.format(
    #         metric_key, metric_min, metric_max, metric_mean))

    # print()
    print('Across all {} non-isolated entity nodes:'.format(
        non_iso_ent_count))
    for metric_key in ent_metric_keys:
        metric_list = [node_stats[metric_key] for node_label, node_stats in
                       non_iso_ent_node_stats.items()]
        assert len(metric_list) == non_iso_ent_count
        metric_min = min(metric_list)
        metric_max = max(metric_list)
        metric_mean = sum(metric_list) / len(metric_list)
        print('# of {}: min = {}, max = {}, average = {:.2f}'.format(
            metric_key, metric_min, metric_max, metric_mean))

    rel_metric_keys = [
        'Relation-Type statements',
        'Relation-Entity statements',
        'Relation-Event statements',
        'General statements'
    ]

    rel_node_stats = {}

    for node_label in rel_label_list:
        node_stats = {metric_key: 0 for metric_key in rel_metric_keys}
        for stmt_label in aida_json.each_ere_adjacent_stmt_anyrel(node_label):
            stmt_cat = stmt_cat_dict[stmt_label]
            node_stats['{} statements'.format(stmt_cat)] += 1
            if not stmt_cat.endswith('-Type'):
                node_stats['General statements'] += 1
        rel_node_stats[node_label] = node_stats

    non_iso_rel_node_stats = {node_label: rel_node_stats[node_label] for
                              node_label in non_iso_rel_label_list}

    rel_count = len(rel_label_list)
    non_iso_rel_count = len(non_iso_rel_label_list)

    # print('Across all {} relation nodes:'.format(rel_count))
    # for metric_key in rel_metric_keys:
    #     metric_list = [node_stats[metric_key] for node_label, node_stats in
    #                    rel_node_stats.items()]
    #     assert len(metric_list) == rel_count
    #     metric_min = min(metric_list)
    #     metric_max = max(metric_list)
    #     metric_mean = sum(metric_list) / len(metric_list)
    #     print('# of {}: min = {}, max = {}, average = {:.2f}'.format(
    #         metric_key, metric_min, metric_max, metric_mean))

    print()
    print('Across all {} non-isolated relation nodes:'.format(
        non_iso_rel_count))
    for metric_key in rel_metric_keys:
        metric_list = [node_stats[metric_key] for node_label, node_stats in
                       non_iso_rel_node_stats.items()]
        assert len(metric_list) == non_iso_rel_count
        metric_min = min(metric_list)
        metric_max = max(metric_list)
        metric_mean = sum(metric_list) / len(metric_list)
        print('# of {}: min = {}, max = {}, average = {:.2f}'.format(
            metric_key, metric_min, metric_max, metric_mean))

    evt_metric_keys = [
        'Event-Type statements',
        'Event-Entity statements',
        'Relation-Event statements',
        'General statements'
    ]

    evt_node_stats = {}

    for node_label in evt_label_list:
        node_stats = {metric_key: 0 for metric_key in evt_metric_keys}
        for stmt_label in aida_json.each_ere_adjacent_stmt_anyrel(node_label):
            stmt_cat = stmt_cat_dict[stmt_label]
            node_stats['{} statements'.format(stmt_cat)] += 1
            if not stmt_cat.endswith('-Type'):
                node_stats['General statements'] += 1
        evt_node_stats[node_label] = node_stats

    non_iso_evt_node_stats = {node_label: evt_node_stats[node_label] for
                              node_label in non_iso_evt_label_list}

    evt_count = len(evt_label_list)
    non_iso_evt_count = len(non_iso_evt_label_list)

    # print('Across all {} event nodes:'.format(evt_count))
    # for metric_key in evt_metric_keys:
    #     metric_list = [node_stats[metric_key] for node_label, node_stats in
    #                    evt_node_stats.items()]
    #     assert len(metric_list) == evt_count
    #     metric_min = min(metric_list)
    #     metric_max = max(metric_list)
    #     metric_mean = sum(metric_list) / len(metric_list)
    #     print('# of {}: min = {}, max = {}, average = {:.2f}'.format(
    #         metric_key, metric_min, metric_max, metric_mean))

    print()
    print('Across all {} non-isolated event nodes:'.format(non_iso_evt_count))
    for metric_key in evt_metric_keys:
        metric_list = [node_stats[metric_key] for node_label, node_stats in
                       non_iso_evt_node_stats.items()]
        assert len(metric_list) == non_iso_evt_count
        metric_min = min(metric_list)
        metric_max = max(metric_list)
        metric_mean = sum(metric_list) / len(metric_list)
        print('# of {}: min = {}, max = {}, average = {:.2f}'.format(
            metric_key, metric_min, metric_max, metric_mean))

    # print('\n==========\nNeighbor statistics\n==========')

    ent_neighbor_map = {ent_label: {'event': [], 'relation': []} for ent_label
                        in non_iso_ent_label_list}
    rel_neighbor_map = {rel_label: {'entity': [], 'event': []} for rel_label in
                        non_iso_rel_label_list}
    evt_neighbor_map = {evt_label: {'entity': [], 'relation': []} for evt_label
                        in non_iso_evt_label_list}

    for stmt_label in stmt_label_list:
        stmt_subj = aida_json.stmt_subject(stmt_label)
        stmt_pred = aida_json.stmt_predicate(stmt_label)
        stmt_obj = aida_json.stmt_object(stmt_label)

        if stmt_pred == 'type':
            continue

        subj_type = aida_json.thegraph[stmt_subj]['type']
        obj_type = aida_json.thegraph[stmt_obj]['type']

        if subj_type == 'Event':
            assert obj_type == 'Entity'
            ent_neighbor_map[stmt_obj]['event'].append(stmt_subj)
            evt_neighbor_map[stmt_subj]['entity'].append(stmt_obj)
        else:
            assert subj_type == 'Relation'
            if obj_type == 'Entity':
                ent_neighbor_map[stmt_obj]['relation'].append(stmt_subj)
                rel_neighbor_map[stmt_subj]['entity'].append(stmt_obj)
            else:
                assert obj_type == 'Event'
                evt_neighbor_map[stmt_obj]['relation'].append(stmt_subj)
                rel_neighbor_map[stmt_subj]['event'].append(stmt_obj)

    '''
    print('Across all {} non-isolated entity nodes:'.format(non_iso_ent_count))
    for neighbor_type in ['event', 'relation']:
        neighbor_count_list = [len(neighbor_map[neighbor_type]) for neighbor_map
                               in ent_neighbor_map.values()]
        assert len(neighbor_count_list) == non_iso_ent_count
        neighbor_count_min = min(neighbor_count_list)
        neighbor_count_max = max(neighbor_count_list)
        neighbor_count_mean = sum(neighbor_count_list) / len(
            neighbor_count_list)
        print('# of {} neighbors: min = {}, max = {}, average = {:.2f}'.format(
            neighbor_type, neighbor_count_min, neighbor_count_max,
            neighbor_count_mean))

    ent_neighbor_map_neighbor_evt = {k: v for k, v in ent_neighbor_map.items()
                                     if len(v['event']) > 0}
    print('\nAcross all {} non-isolated entity nodes that are connected to at '
          'least 1 event:'.format(len(ent_neighbor_map_neighbor_evt)))
    for neighbor_type in ['event', 'relation']:
        neighbor_count_list = [len(neighbor_map[neighbor_type]) for neighbor_map
                               in ent_neighbor_map_neighbor_evt.values()]
        neighbor_count_min = min(neighbor_count_list)
        neighbor_count_max = max(neighbor_count_list)
        neighbor_count_mean = sum(neighbor_count_list) / len(
            neighbor_count_list)
        print('# of {} neighbors: min = {}, max = {}, average = {:.2f}'.format(
            neighbor_type, neighbor_count_min, neighbor_count_max,
            neighbor_count_mean))

    ent_neighbor_map_neighbor_rel = {k: v for k, v in ent_neighbor_map.items()
                                     if len(v['relation']) > 0}
    print('\nAcross all {} non-isolated entity nodes that are connected to at '
          'least 1 relation:'.format(len(ent_neighbor_map_neighbor_rel)))
    for neighbor_type in ['event', 'relation']:
        neighbor_count_list = [len(neighbor_map[neighbor_type]) for neighbor_map
                               in ent_neighbor_map_neighbor_rel.values()]
        neighbor_count_min = min(neighbor_count_list)
        neighbor_count_max = max(neighbor_count_list)
        neighbor_count_mean = sum(neighbor_count_list) / len(
            neighbor_count_list)
        print('# of {} neighbors: min = {}, max = {}, average = {:.2f}'.format(
            neighbor_type, neighbor_count_min, neighbor_count_max,
            neighbor_count_mean))

    print('\nAcross all {} non-isolated relation nodes:'.format(
        non_iso_rel_count))
    for neighbor_type in ['entity', 'event']:
        neighbor_count_list = [len(neighbor_map[neighbor_type]) for neighbor_map
                               in rel_neighbor_map.values()]
        assert len(neighbor_count_list) == non_iso_rel_count
        neighbor_count_min = min(neighbor_count_list)
        neighbor_count_max = max(neighbor_count_list)
        neighbor_count_mean = sum(neighbor_count_list) / len(
            neighbor_count_list)
        print('# of {} neighbors: min = {}, max = {}, average = {:.2f}'.format(
            neighbor_type, neighbor_count_min, neighbor_count_max,
            neighbor_count_mean))

    print('\nAcross all {} non-isolated event nodes:'.format(non_iso_evt_count))
    for neighbor_type in ['entity', 'relation']:
        neighbor_count_list = [len(neighbor_map[neighbor_type]) for neighbor_map
                               in evt_neighbor_map.values()]
        assert len(neighbor_count_list) == non_iso_evt_count
        neighbor_count_min = min(neighbor_count_list)
        neighbor_count_max = max(neighbor_count_list)
        neighbor_count_mean = sum(neighbor_count_list) / len(
            neighbor_count_list)
        print('# of {} neighbors: min = {}, max = {}, average = {:.2f}'.format(
            neighbor_type, neighbor_count_min, neighbor_count_max,
            neighbor_count_mean))
    '''

    print('\n==========\nDisjoint ERE pairs\n==========')

    disjoint_ere_pairs = {'Relation-Entity': [], 'Event-Entity': [],
                          'Relation-Event': []}

    for ent_label, neighbor_map in ent_neighbor_map.items():
        if len(neighbor_map['event']) == 0 and len(
                neighbor_map['relation']) == 1:
            neighbor_label = neighbor_map['relation'][0]
            neighbor_neighbor_map = rel_neighbor_map[neighbor_label]
            if len(neighbor_neighbor_map['entity']) == 1 and len(
                    neighbor_neighbor_map['event']) == 0:
                disjoint_ere_pairs['Relation-Entity'].append(
                    (neighbor_label, ent_label))

        elif len(neighbor_map['event']) == 1 and len(
                neighbor_map['relation']) == 0:
            neighbor_label = neighbor_map['event'][0]
            neighbor_neighbor_map = evt_neighbor_map[neighbor_label]
            if len(neighbor_neighbor_map['entity']) == 1 and len(
                    neighbor_neighbor_map['relation']) == 0:
                disjoint_ere_pairs['Event-Entity'].append(
                    (neighbor_label, ent_label))

    for rel_label, neighbor_map in rel_neighbor_map.items():
        if len(neighbor_map['entity']) == 1 and len(neighbor_map['event']) == 0:
            neighbor_label = neighbor_map['entity'][0]
            neighbor_neighbor_map = ent_neighbor_map[neighbor_label]
            if len(neighbor_neighbor_map['event']) == 0 and len(
                    neighbor_neighbor_map['relation']) == 1:
                assert (rel_label, neighbor_label) in disjoint_ere_pairs[
                    'Relation-Entity']

        elif len(neighbor_map['entity']) == 0 and len(
                neighbor_map['event']) == 1:
            neighbor_label = neighbor_map['event'][0]
            neighbor_neighbor_map = evt_neighbor_map[neighbor_label]
            if len(neighbor_neighbor_map['entity']) == 0 and len(
                    neighbor_neighbor_map['relation']) == 1:
                disjoint_ere_pairs['Relation-Event'].append(
                    (rel_label, neighbor_label))

    for evt_label, neighbor_map in evt_neighbor_map.items():
        if len(neighbor_map['entity']) == 1 and len(
                neighbor_map['relation']) == 0:
            neighbor_label = neighbor_map['entity'][0]
            neighbor_neighbor_map = ent_neighbor_map[neighbor_label]
            if len(neighbor_neighbor_map['event']) == 1 and len(
                    neighbor_neighbor_map['relation']) == 0:
                assert (evt_label, neighbor_label) in disjoint_ere_pairs[
                    'Event-Entity']

        elif len(neighbor_map['entity']) == 0 and len(
                neighbor_map['relation']) == 1:
            neighbor_label = neighbor_map['relation'][0]
            neighbor_neighbor_map = rel_neighbor_map[neighbor_label]
            if len(neighbor_neighbor_map['entity']) == 0 and len(
                    neighbor_neighbor_map['event']) == 1:
                assert (neighbor_label, evt_label) in disjoint_ere_pairs[
                    'Relation-Event']

    for ere_pair_key, ere_pair_list in disjoint_ere_pairs.items():
        print('# disjoint {} pairs:'.format(ere_pair_key), len(ere_pair_list))


if __name__ == '__main__':
    main()
