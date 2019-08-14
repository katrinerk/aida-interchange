import json
from argparse import ArgumentParser
from collections import defaultdict
from operator import itemgetter
from pathlib import Path

update_prefix = \
    'PREFIX ldcOnt: <https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/LDCOntology#>\n' \
    'PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' \
    'PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>\n' \
    'PREFIX aida:  <https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/InterchangeOntology#>\n' \
    'PREFIX ldc:   <https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/LdcAnnotations#>\n' \
    'PREFIX utexas: <http://www.utexas.edu/aida/>\n\n'


def build_member_cluster_mappings(graph_json):
    member_to_clusters = defaultdict(set)

    for node_label, node in graph_json['theGraph'].items():
        if node['type'] == 'ClusterMembership':
            cluster = node.get('cluster', None)
            member = node.get('clusterMember', None)
            assert cluster is not None and member is not None

            member_to_clusters[member].add(cluster)

    num_clusters = len(set([c for clusters in member_to_clusters.values() for c in clusters]))
    num_members = len(member_to_clusters)

    print('\nConstructed mapping from {} members to {} clusters'.format(
        num_members, num_clusters, ))

    return member_to_clusters


def compute_handle_mapping(graph_json, hypothesis, member_to_clusters):
    cluster_handles = {}

    for stmt_label in hypothesis['statements']:

        stmt_entry = graph_json['theGraph'][stmt_label]

        stmt_obj = stmt_entry.get('object', None)
        assert stmt_obj is not None

        if stmt_obj in graph_json['theGraph']:
            if graph_json['theGraph'][stmt_obj]['type'] == 'Entity':
                for cluster in member_to_clusters[stmt_obj]:
                    if cluster not in cluster_handles:
                        cluster_handles[cluster] = graph_json['theGraph'][cluster]['handle']

    return cluster_handles


def main():
    parser = ArgumentParser()
    parser.add_argument('graph_json_path', help='path to the graph json file')
    parser.add_argument('hypotheses_json_path', help='path to the hypotheses json file')
    parser.add_argument('output_dir', help='Directory to write queries')
    parser.add_argument('--top', default=14, type=int,
                        help='number of top hypothesis to output')

    args = parser.parse_args()

    graph_json_path = Path(args.graph_json_path)
    assert graph_json_path.exists(), '{} does not exist'.format(graph_json_path)
    print('Reading the graph from {}'.format(graph_json_path))
    with open(graph_json_path, 'r') as fin:
        graph_json = json.load(fin)

    member_to_clusters = build_member_cluster_mappings(graph_json)

    hypotheses_json_path = Path(args.hypotheses_json_path)
    assert hypotheses_json_path.exists(), '{} does not exist'.format(hypotheses_json_path)
    print('Reading the hypotheses from {}'.format(hypotheses_json_path))
    with open(hypotheses_json_path, 'r') as fin:
        hypotheses_json = json.load(fin)

    print('Found {} hypotheses with probabilities of {}'.format(
        len(hypotheses_json['probs']), hypotheses_json['probs']))

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print('Creating output directory {}'.format(output_dir))
        output_dir.mkdir(parents=True)

    top_count = 0

    for result_idx, prob in sorted(
            enumerate(hypotheses_json['probs']), key=itemgetter(1), reverse=True):
        hypothesis = hypotheses_json['support'][result_idx]

        top_count += 1

        update_str = update_prefix + 'INSERT DATA\n{\n'

        cluster_handles = compute_handle_mapping(graph_json, hypothesis, member_to_clusters)

        for cluster, handle in cluster_handles.items():
            handle = handle.lstrip('"')
            handle = handle.rstrip('"')
            update_str += '  <{}> aida:handle "{}" .\n'.format(cluster, handle)

        update_str += '}'

        output_path = output_dir / 'hypothesis-{:0>3d}-update.rq'.format(top_count)

        with open(output_path, 'w') as fout:
            fout.write(update_str)

        if top_count >= args.top:
            break


if __name__ == '__main__':
    main()
