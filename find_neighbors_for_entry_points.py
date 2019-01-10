# Pengxiang Cheng Fall 2018
# pre- and postprocessing for the AIDA eval
# determine k-hop neighborhood of a set of entry points

import json
from argparse import ArgumentParser
from copy import deepcopy


# Find all zero_hop neighbors of a set of starting_nodes (default to be EREs).
# Return a closure for all ERE nodes, a closure for all SameAsCluster nodes,
# and a set of (ERE, SameAsCluster) pairs, representing corresponding
# ClusterMembership nodes (since they can be BNodes, thus cannot be
# identified by randomly generated node names).
def find_coref_closure(starting_nodes, neighbors_mapping, start_from_ere=True):
    # closure for all ERE nodes
    ere_closure = set([])
    # closure for all SameAsCluster nodes
    cluster_closure = set([])
    # set of (ERE, SameAsCluster) pairs
    cluster_memberships = set([])

    # set of nodes in current iteration
    current_neighbors = starting_nodes
    # set of neighbors of nodes in current iteration, for the next iteration
    new_neighbors = set([])

    # boolean value indicating whether this iteration contains ERE nodes or
    # SameAsCluster nodes
    ere_node_this_iteration = start_from_ere

    while current_neighbors:
        # update ere_closure with nodes in current iteration if
        # it contains ERE nodes
        if ere_node_this_iteration:
            ere_closure.update(current_neighbors)
        # otherwise update cluster_closure with nodes in current iteration
        else:
            cluster_closure.update(current_neighbors)

        # look for neighbors for each node in the current iteration
        for current_node in current_neighbors:
            # if this is an ERE node
            if ere_node_this_iteration:
                neighbors = neighbors_mapping['zero-hop-ere'].get(
                    current_node, [])
                # add all pairs of (current_node, neighbor) to the set of
                # ClusterMembership nodes
                cluster_memberships.update(
                    [(current_node, n) for n in neighbors])
            # otherwise, this is a SameAsCluster node
            else:
                neighbors = neighbors_mapping['zero-hop-cluster'].get(
                    current_node, [])
                # add all pairs of (neighbor, current_node) to the set of
                # ClusterMembership nodes
                cluster_memberships.update(
                    [(n, current_node) for n in neighbors])

            # add all neighbors of the current node to the set of new_neighbors
            new_neighbors.update(set(neighbors))

        # remove nodes already in the closure, as we don't want to
        # process the same node more than once.
        new_neighbors -= ere_closure
        new_neighbors -= cluster_closure

        # set current_neighbors = new_neighbors, then reset new_neighbors
        current_neighbors = deepcopy(new_neighbors)
        new_neighbors = set([])

        # flip the boolean value, as the iterations would go like
        # ERE --> SameAsCluster --> ERE --> SameAsCluster --> ...
        ere_node_this_iteration = not ere_node_this_iteration

    return ere_closure, cluster_closure, cluster_memberships


# Find all typing statements for a closure of ERE nodes.
# Each typing statement is represented by a pair of (ERE/subject, Type/object)
# (again, we must use a pair to identify the typing statement as it can
# possibly be a BNode).
def find_typing_statements(ere_closure, neighbors_mapping):
    typing_statements = set([])
    for ere in ere_closure:
        ere_types = neighbors_mapping['one-hop'].get(ere, [])
        # there should be one and only one typing statement for each ERE node
        # in the closure, if not, we print a warning message.
        if not ere_types:
            print('Warning! Could not find typing statement '
                  'for node {}'.format(ere))
            continue
        if len(ere_types) > 1:
            print('Warning! Found multiple typing statements '
                  'for node {}'.format(ere))
        for ere_type in ere_types:
            typing_statements.add((ere, ere_type))

    return typing_statements


# Find all half-hop neighbors for a closure of ERE nodes.
# Return a set of (subj, obj) pairs representing corresponding statements
# connecting the nodes and neighbors, as well as, a closure for all ERE
# nodes, a closure for all SameAsCluster nodes, and a set of
# (ERE, SameAsCluster) pairs for corresponding ClusterMembership nodes,
# similar to the output of find_coref_closure.
def find_half_hop_neighbors(ere_closure, neighbors_mapping):
    neighbors = set([])
    statements = set([])

    for ere in ere_closure:
        for obj in neighbors_mapping['half-hop-subj'].get(ere, []):
            statements.add((ere, obj))
            neighbors.add(obj)
        for subj in neighbors_mapping['half-hop-obj'].get(ere, []):
            statements.add((subj, ere))
            neighbors.add(subj)

    ere_closure_neighbors, cluster_closure_neighbors, \
        cluster_membership_neighbors = find_coref_closure(
            neighbors, neighbors_mapping, start_from_ere=True)

    return statements, ere_closure_neighbors, cluster_closure_neighbors, \
        cluster_membership_neighbors


def find_neighbors_for_entry_point(
        starting_eres, neighbors_mapping, verbose=False):
    all_neighbors = {
        'eres': set([]),
        'clusters': set([]),
        'cluster_memberships': set([]),
        'general_statements': set([]),
        'typing_statements': set([])
    }

    # search for all zero-hop neighbors
    ere_closure_zero, cluster_closure_zero, cluster_memberships_zero = \
        find_coref_closure(
            starting_eres, neighbors_mapping, start_from_ere=True)

    if verbose:
        print('\nEREs zero-hop from the entry point: \n{}'.format(
            '\n'.join(ere_closure_zero)))
        print('\nClusters zero-hop from the entry point: \n{}'.format(
            '\n'.join(cluster_closure_zero)))
        print('\nClusterMemberships zero-hop from the entry point: \n{}'.format(
            '\n'.join(map(str, cluster_memberships_zero))))

    all_neighbors['eres'].update(ere_closure_zero)
    all_neighbors['clusters'].update(cluster_closure_zero)
    all_neighbors['cluster_memberships'].update(cluster_memberships_zero)

    # search for typing statements of zero-hop EREs
    # (considered as one-hops neighbors)
    typing_statements = find_typing_statements(
        ere_closure_zero, neighbors_mapping)

    if verbose:
        print('\nTyping statements of zero-hop ERE closure: \n{}'.format(
            '\n'.join(map(str, typing_statements))))

    all_neighbors['typing_statements'].update(typing_statements)

    # search for half-hop neighbors, as well as corresponding statements
    statements_half, ere_closure_half, cluster_closure_half, \
        cluster_membership_half = find_half_hop_neighbors(
            ere_closure_zero, neighbors_mapping)

    if verbose:
        print('\nStatements connecting zero-hop and half-hop EREs: \n{}'.format(
            '\n'.join(map(str, statements_half))))

        print('\nEREs half-hop from the entry point: \n{}'.format(
            '\n'.join(ere_closure_half)))
        print('\nClusters half-hop from the entry point: \n{}'.format(
            '\n'.join(cluster_closure_half)))
        print('\nClusterMemberships half-hop from the entry point: \n{}'.format(
            '\n'.join(map(str, cluster_membership_half))))

    all_neighbors['general_statements'].update(statements_half)

    all_neighbors['eres'].update(ere_closure_half)
    all_neighbors['clusters'].update(cluster_closure_half)
    all_neighbors['cluster_memberships'].update(cluster_membership_half)

    # search for one-hop neighbors, as well as corresponding statements
    statements_one, ere_closure_one, cluster_closure_one, \
        cluster_membership_one = find_half_hop_neighbors(
            ere_closure_half, neighbors_mapping)

    if verbose:
        print('\nStatements connecting half-hop and one-hop EREs: \n{}'.format(
            '\n'.join(map(str, statements_one))))

        print('\nEREs one-hop from the entry point: \n{}'.format(
            '\n'.join(ere_closure_one)))
        print('\nClusters one-hop from the entry point: \n{}'.format(
            '\n'.join(cluster_closure_one)))
        print('\nClusterMemberships one-hop from the entry point: \n{}'.format(
            '\n'.join(map(str, cluster_membership_one))))

    all_neighbors['general_statements'].update(statements_one)

    all_neighbors['eres'].update(ere_closure_one)
    all_neighbors['clusters'].update(cluster_closure_one)
    all_neighbors['cluster_memberships'].update(cluster_membership_one)

    return all_neighbors


def main():
    parser = ArgumentParser()
    parser.add_argument('query_path',
                        help='path to aidaquery.json')
    parser.add_argument('neighbors_mapping_path',
                        help='path to neighbors_mapping.json file')
    parser.add_argument('output_path', help='path to write output')
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()

    with open(args.query_path, 'r') as fin:
        aida_query = json.load(fin)

    # entry_points = set(args.entry_points.split(','))

    starting_eres = set([])
    for cluster, mentions in aida_query['coref'].items():
        starting_eres.update(mentions)
    # for entry_point in aida_query['entrypoints']:
    #     starting_eres.update(entry_point['ere'])
    print('Looking for neighbors of entry points: {}'.format(starting_eres))

    neighbors_mapping_path = args.neighbors_mapping_path
    print('Loading neighbor information from {}...'.format(
        neighbors_mapping_path))
    with open(neighbors_mapping_path, 'r') as fin:
        neighbors_mapping = json.load(fin)

    all_neighbors = find_neighbors_for_entry_point(
        starting_eres, neighbors_mapping, verbose=args.verbose)

    # convert sets to lists for json dump
    for key in all_neighbors:
        all_neighbors[key] = list(all_neighbors[key])

    with open(args.output_path, 'w') as fout:
        json.dump(all_neighbors, fout, indent=2)


if __name__ == '__main__':
    main()
