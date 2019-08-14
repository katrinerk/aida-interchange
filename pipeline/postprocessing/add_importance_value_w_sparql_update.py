import json
import math
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


def compute_importance_mapping(graph_json, hypothesis, member_to_clusters):
    stmt_importance = {}
    node_importance = {}

    for stmt_label, stmt_weight in zip(hypothesis['statements'], hypothesis['statementWeights']):
        if stmt_weight <= 0.0:
            stmt_weight = math.exp(stmt_weight / 100.0)
        else:
            stmt_weight = 0.0001

        stmt_entry = graph_json['theGraph'][stmt_label]

        stmt_subj = stmt_entry.get('subject', None)
        stmt_pred = stmt_entry.get('predicate', None)
        stmt_obj = stmt_entry.get('object', None)

        assert stmt_subj is not None
        assert stmt_pred is not None
        assert stmt_obj is not None

        if stmt_pred != 'type':
            stmt_importance[(stmt_subj, stmt_pred, stmt_obj)] = stmt_weight

        if graph_json['theGraph'][stmt_subj]['type'] in ['Event', 'Relation']:
            # if stmt_subj not in node_importance:
            #     node_importance[stmt_subj] = stmt_weight
            # elif node_importance[stmt_subj] < stmt_weight:
            #     node_importance[stmt_subj] = stmt_weight

            for cluster in member_to_clusters[stmt_subj]:
                if cluster not in node_importance:
                    node_importance[cluster] = stmt_weight
                elif node_importance[cluster] < stmt_weight:
                    node_importance[cluster] = stmt_weight

    return stmt_importance, node_importance


def main():
    parser = ArgumentParser()
    parser.add_argument('graph_json_path', help='path to the graph json file')
    parser.add_argument('hypotheses_json_path', help='path to the hypotheses json file')
    parser.add_argument('frame_id', help='Frame ID of the hypotheses')
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

    frame_id = args.frame_id

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print('Creating output directory {}'.format(output_dir))
        output_dir.mkdir(parents=True)

    top_count = 0

    for result_idx, prob in sorted(
            enumerate(hypotheses_json['probs']), key=itemgetter(1), reverse=True):
        if prob <= 0.0:
            hyp_weight = math.exp(prob / 2.0)
        else:
            hyp_weight = 0.0001

        hypothesis = hypotheses_json['support'][result_idx]

        top_count += 1

        hypothesis_id = '{}_hypothesis_{:0>3d}'.format(frame_id, top_count)

        hypothesis_name = 'utexas:{}'.format(hypothesis_id)

        update_query_count = 0

        update_str = update_prefix + 'INSERT DATA\n{\n'
        update_str += '  {} rdf:type aida:Hypothesis .\n'.format(hypothesis_name)
        update_str += '  {} aida:importance {:.4f} .\n'.format(hypothesis_name, hyp_weight)

        stmt_importance, node_importance = compute_importance_mapping(
            graph_json, hypothesis, member_to_clusters)

        for node_id, importance_value in node_importance.items():
            update_str += '  <{}> aida:importance {:.4f} .\n'.format(node_id, importance_value)

        update_str += '}'

        output_path = output_dir / 'hypothesis-{:0>3d}-update-{:0>4d}.rq'.format(
            top_count, update_query_count)

        with open(output_path, 'w') as fout:
            fout.write(update_str)

        update_query_count += 1

        for (stmt_subj, stmt_pred, stmt_obj), importance_value in stmt_importance.items():
            update_str = update_prefix
            update_str += \
                'INSERT {{ ?x aida:importance {:.4f} . }}\n' \
                'WHERE\n{{\n' \
                '?x a rdf:Statement .\n' \
                '?x rdf:subject <{}> .\n' \
                '?x rdf:predicate ldcOnt:{} .\n' \
                '?x rdf:object <{}> .\n}}\n'.format(
                    importance_value, stmt_subj, stmt_pred, stmt_obj)

            output_path = output_dir / 'hypothesis-{:0>3d}-update-{:0>4d}.rq'.format(
                top_count, update_query_count)

            with open(output_path, 'w') as fout:
                fout.write(update_str)

            update_query_count += 1

        if top_count >= args.top:
            break


if __name__ == '__main__':
    main()
