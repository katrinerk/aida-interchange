import itertools
import json
import sys
from argparse import ArgumentParser
from collections import defaultdict, Counter
from os.path import dirname, realpath
from pathlib import Path

src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

from aif import AidaJson


def make_stmt_keys(stmt_entry, member_to_prototypes):
    subj = stmt_entry["subject"]
    if subj in member_to_prototypes:
        new_subj_set = member_to_prototypes[subj]
    else:
        print('Warning: statement subject {} not found in '
              'any ClusterMembership node'.format(subj))
        new_subj_set = {subj}

    pred = stmt_entry["predicate"]

    obj = stmt_entry["object"]
    if pred != 'type':
        if obj in member_to_prototypes:
            new_obj_set = member_to_prototypes[obj]
        else:
            print('Warning: statement object {} not found in '
                  'any ClusterMembership node'.format(obj))
            new_obj_set = {obj}
    else:
        new_obj_set = {obj}

    return [(new_subj, pred, new_obj) for new_subj, new_obj
            in itertools.product(new_subj_set, new_obj_set)]


def build_mappings(input_graph_json):
    # Build mappings between clusters and members, and mappings between
    # clusters and prototypes
    cluster_to_members = defaultdict(set)
    member_to_clusters = defaultdict(set)
    cluster_membership_key_mapping = {}

    cluster_to_prototype = {}
    prototype_to_clusters = defaultdict(set)

    for node_label, node in input_graph_json['theGraph'].items():
        if node['type'] == 'ClusterMembership':
            cluster = node.get('cluster', None)
            member = node.get('clusterMember', None)
            assert cluster is not None and member is not None

            cluster_to_members[cluster].add(member)
            member_to_clusters[member].add(cluster)

            assert (cluster, member) not in cluster_membership_key_mapping
            cluster_membership_key_mapping[(cluster, member)] = node_label

        elif node['type'] == 'SameAsCluster':
            assert node_label not in cluster_to_prototype

            prototype = node.get('prototype', None)
            assert prototype is not None

            cluster_to_prototype[node_label] = prototype
            prototype_to_clusters[prototype].add(node_label)

    num_clusters = len(cluster_to_members)
    num_members = len(member_to_clusters)
    num_prototypes = len(prototype_to_clusters)
    assert len(cluster_to_prototype) == num_clusters

    print('\nConstructed mapping from {} clusters to {} members'.format(
        num_clusters, num_members))

    clusters_per_member_counter = Counter(
        [len(v) for v in member_to_clusters.values()])
    for key in sorted(clusters_per_member_counter.keys()):
        if key > 1:
            print(
                '\tFor {} out of {} members, each belong to {} clusters'.format(
                    clusters_per_member_counter[key], num_members, key))

    print('\nConstructed mapping from {} clusters to {} prototypes'.format(
        num_clusters, num_prototypes))

    clusters_per_prototype_counter = Counter(
        [len(v) for v in prototype_to_clusters.values()])
    for key in sorted(clusters_per_prototype_counter.keys()):
        if key > 1:
            print(
                '\tFor {} out of {} prototypes, each is the prototype of {} '
                'clusters'.format(
                    clusters_per_prototype_counter[key], num_prototypes, key))

    # Build mappings between members and prototypes, using the above
    # constructed mappings
    member_to_prototypes = defaultdict(set)
    prototype_to_members = defaultdict(set)

    for member, clusters in member_to_clusters.items():
        assert member not in member_to_prototypes
        for cluster in clusters:
            prototype = cluster_to_prototype[cluster]
            member_to_prototypes[member].add(prototype)
            prototype_to_members[prototype].add(member)

    assert len(member_to_prototypes) == num_members
    assert len(prototype_to_members) == num_prototypes

    print('\nConstructed mapping from {} members to {} prototypes'.format(
        num_members, num_prototypes))

    prototypes_per_member_counter = Counter(
        [len(v) for v in member_to_prototypes.values()])
    for key in sorted(prototypes_per_member_counter.keys()):
        if key > 1:
            print(
                '\tFor {} out of {} members, each is mapped to {} '
                'prototypes'.format(
                    prototypes_per_member_counter[key], num_members, key))

    # Add ERE nodes that are not connected to any ClusterMembership node to
    # the mappings between members and prototypes. This shouldn't happen,
    # unless the TA2 output we get don't conform to the NIST-restricted
    # formatting requirements.
    ere_nodes_not_in_clusters = set()
    for node_label, node in input_graph_json['theGraph'].items():
        if node['type'] in ['Entity', 'Relation', 'Event']:
            if node_label not in member_to_prototypes:
                ere_nodes_not_in_clusters.add(node_label)
    if len(ere_nodes_not_in_clusters) > 0:
        print('\nWarning: Found {} ERE nodes that are not connected to any '
              'ClusterMembership node'.format(len(ere_nodes_not_in_clusters)))
        print('Adding them to the mappings between members and prototypes')
        for node_label in ere_nodes_not_in_clusters:
            member_to_prototypes[node_label].add(node_label)
            prototype_to_members[node_label].add(node_label)
        print(
            '\nAfter correction, constructed mapping from {} members to '
            '{} prototypes'.format(
                len(member_to_prototypes), len(prototype_to_members)))

    # Build mappings from old statement labels to new statement labels
    stmt_count = 0

    stmt_key_to_new_stmt = {}
    new_stmt_to_stmt_key = {}
    old_stmt_to_new_stmts = defaultdict(set)
    new_stmt_to_old_stmts = defaultdict(set)

    for node_label, node in input_graph_json['theGraph'].items():
        if node['type'] == 'Statement':
            stmt_keys = make_stmt_keys(
                stmt_entry=node, member_to_prototypes=member_to_prototypes)
            for stmt_key in stmt_keys:
                if stmt_key not in stmt_key_to_new_stmt:
                    new_stmt_label = 'Statement-{}'.format(stmt_count)
                    stmt_count += 1
                    stmt_key_to_new_stmt[stmt_key] = new_stmt_label
                    new_stmt_to_stmt_key[new_stmt_label] = stmt_key
                else:
                    new_stmt_label = stmt_key_to_new_stmt[stmt_key]

                old_stmt_to_new_stmts[node_label].add(new_stmt_label)
                new_stmt_to_old_stmts[new_stmt_label].add(node_label)

    num_old_stmts = len(old_stmt_to_new_stmts)
    num_new_stmts = len(new_stmt_to_old_stmts)

    assert len(stmt_key_to_new_stmt) == num_new_stmts
    assert len(new_stmt_to_stmt_key) == num_new_stmts

    print(
        '\nConstructed mapping from {} old statements to {} new '
        'statements'.format(
            num_old_stmts, num_new_stmts))

    new_stmts_per_old_stmt_counter = Counter(
        [len(v) for v in old_stmt_to_new_stmts.values()])
    for key in sorted(new_stmts_per_old_stmt_counter.keys()):
        if key > 1:
            print(
                '\tFor {} out of {} old statements, each is mapped to {} new '
                'statements'.format(
                    new_stmts_per_old_stmt_counter[key], num_old_stmts, key))

    mappings = {
        'cluster_to_members': cluster_to_members,
        'member_to_clusters': member_to_clusters,
        'cluster_membership_key_mapping': cluster_membership_key_mapping,
        'cluster_to_prototype': cluster_to_prototype,
        'prototype_to_clusters': prototype_to_clusters,
        'member_to_prototypes': member_to_prototypes,
        'prototype_to_members': prototype_to_members,
        'stmt_key_to_new_stmt': stmt_key_to_new_stmt,
        'new_stmt_to_stmt_key': new_stmt_to_stmt_key,
        'old_stmt_to_new_stmts': old_stmt_to_new_stmts,
        'new_stmt_to_old_stmts': new_stmt_to_old_stmts
    }

    return mappings


def compress_eres(input_graph_json, mappings, output_graph_json):
    if 'theGraph' not in output_graph_json:
        output_graph_json['theGraph'] = {}

    if 'ere' not in output_graph_json:
        output_graph_json['ere'] = []
    else:
        assert len(output_graph_json['ere']) == 0

    print('\nBuilding ERE / SameAsCluster / ClusterMembership entries '
          'for the compressed graph')

    num_new_eres = 0

    for prototype, members in mappings['prototype_to_members'].items():
        old_entry = input_graph_json['theGraph'][prototype]

        # Use the same ERE index from the original graph
        new_entry = {'index': old_entry['index']}

        member_entry_list = [input_graph_json['theGraph'][member] for member in
                             members]

        # Resolve the type of the compressed ERE node
        type_set = set(
            member_entry['type'] for member_entry in member_entry_list)
        # if len(type_set) > 1:
        #     type_set.remove('Entity')
        if len(type_set) > 1:
            print('Error: multiple types {} from the following EREs {}'.format(
                type_set, members))
        new_entry['type'] = type_set.pop()

        # Resolve the adjacent statements of the compressed ERE node
        adjacency_set = set()
        for member_entry in member_entry_list:
            for old_stmt in member_entry['adjacent']:
                adjacency_set.update(
                    mappings['old_stmt_to_new_stmts'][old_stmt])
        new_entry['adjacent'] = list(adjacency_set)

        # Resolve the names of the compressed ERE node
        name_set = set()
        for member_entry in member_entry_list:
            if 'name' in member_entry:
                name_set.update(member_entry['name'])
        for cluster in mappings['prototype_to_clusters'][prototype]:
            cluster_handle = input_graph_json['theGraph'][cluster].get('handle',
                                                                       None)
            if cluster_handle is not None and cluster_handle != '[unknown]':
                name_set.add(cluster_handle)
        if len(name_set) > 0:
            new_entry['name'] = list(name_set)

        # Resolve the LDC time list of the compressed ERE node
        ldc_time_list = []
        for member_entry in member_entry_list:
            if 'ldcTime' in member_entry:
                ldc_time_list.extend(member_entry['ldcTime'])
        if len(ldc_time_list) > 0:
            new_entry['ldcTime'] = ldc_time_list

        output_graph_json['theGraph'][prototype] = new_entry
        output_graph_json['ere'].append(prototype)

        # Add SameAsCluster nodes and ClusterMembership nodes
        for cluster in mappings['prototype_to_clusters'][prototype]:
            same_as_cluster_entry = input_graph_json['theGraph'][cluster]
            output_graph_json['theGraph'][cluster] = same_as_cluster_entry

            cluster_membership_key = \
                mappings['cluster_membership_key_mapping'][(cluster, prototype)]
            cluster_membership_entry = input_graph_json['theGraph'][
                cluster_membership_key]
            output_graph_json['theGraph'][
                cluster_membership_key] = cluster_membership_entry

        num_new_eres += 1

    print('\tDone')

    return num_new_eres


def compress_statements(input_graph_json, mappings, output_graph_json):
    print('\nBuilding statement entries for the compressed graph')

    if 'theGraph' not in output_graph_json:
        output_graph_json['theGraph'] = {}

    if 'statements' not in output_graph_json:
        output_graph_json['statements'] = []
    else:
        assert len(output_graph_json['statements']) == 0

    num_new_stmts = 0

    for new_stmt, stmt_key in mappings['new_stmt_to_stmt_key'].items():
        stmt_idx = int(new_stmt.split('-')[1])
        subj, pred, obj = stmt_key
        new_entry = {
            'type': 'Statement',
            'index': stmt_idx,
            'subject': subj,
            'predicate': pred,
            'object': obj
        }

        old_stmt_entry_list = [
            input_graph_json['theGraph'][old_stmt]
            for old_stmt in mappings['new_stmt_to_old_stmts'][new_stmt]]

        # Resolve the extra information (source and hypotheses) of the new
        # statement
        for label in ['source', 'hypotheses_supported',
                      'hypotheses_partially_supported',
                      'hypotheses_contradicted']:
            label_value_set = set()
            for old_stmt_entry in old_stmt_entry_list:
                if label in old_stmt_entry:
                    label_value_set.update(old_stmt_entry[label])
            if len(label_value_set) > 0:
                new_entry[label] = list(label_value_set)

        output_graph_json['theGraph'][new_stmt] = new_entry
        output_graph_json['statements'].append(new_stmt)
        num_new_stmts += 1

    print('\tDone')

    return num_new_stmts


def main():
    parser = ArgumentParser()
    parser.add_argument('input_graph_path',
                        help='path to the input graph json file')
    parser.add_argument('output_graph_path',
                        help='path to write the coref-compressed graph')
    parser.add_argument('output_log_path', help='path to write the log file')

    args = parser.parse_args()

    input_graph_path = Path(args.input_graph_path)
    assert input_graph_path.exists(), '{} does not exist!'.format(
        input_graph_path)

    print('Reading json graph from {}'.format(input_graph_path))
    with open(input_graph_path, 'r') as fin:
        input_graph_json = json.load(fin)
    print('\tDone')

    aida_json = AidaJson(input_graph_json)

    num_old_eres = len(list(aida_json.each_ere()))
    assert num_old_eres == len(input_graph_json['ere'])
    num_old_stmts = len(list(aida_json.each_statement()))
    print('\nFound {} EREs and {} statements in the original graph'.format(
        num_old_eres, num_old_stmts))

    mappings = build_mappings(input_graph_json)

    output_graph_json = {'theGraph': {}, 'ere': [], 'statements': []}

    num_new_eres = compress_eres(input_graph_json, mappings, output_graph_json)
    num_new_stmts = compress_statements(input_graph_json, mappings,
                                        output_graph_json)

    print(
        '\nFinished coref-compressed graph with {} EREs and {} '
        'statements'.format(
            num_new_eres, num_new_stmts))

    output_graph_path = Path(args.output_graph_path)
    print('\nWriting compressed json graph to {}'.format(output_graph_path))
    with open(output_graph_path, 'w') as fout:
        json.dump(output_graph_json, fout, indent=2)

    log_json = {}
    for mapping_key, mapping in mappings.items():
        if 'key' in mapping_key:
            continue
        if mapping_key.endswith('s'):
            log_json[mapping_key] = {k: list(v) for k, v in mapping.items()}
        else:
            log_json[mapping_key] = mapping

    output_log_path = Path(args.output_log_path)
    print('\nWriting compression log to {}'.format(output_log_path))
    with open(output_log_path, 'w') as fout:
        json.dump(log_json, fout, indent=2)


if __name__ == '__main__':
    main()
