# Pengxiang Cheng Fall 2018
# pre- and postprocessing for the AIDA eval

import json
from argparse import ArgumentParser
from operator import itemgetter
from pathlib import Path
from sparql_helper import *


def queries_for_aida_result(
        aida_graph, result, soin_id, num_node_queries=5,
        num_stmts_per_query=3000):
    node_query_prefix = 'DESCRIBE '
    stmt_query_prefix = \
        'PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' \
        'PREFIX aida:  <https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/' \
        'InterchangeOntology#>\n' \
        'PREFIX domainOntology: <https://tac.nist.gov/tracks/SM-KBP/2018/' \
        'ontologies/SeedlingOntology#>\n\n' \
        'DESCRIBE ?x\n' \
        'WHERE {\n'

    node_query_item_list = []
    stmt_query_item_list = []

    for stmt in result['statements']:
        stmt_entry = aida_graph['theGraph'][stmt]

        if stmt_entry['type'] == 'Statement':
            subject_id = stmt_entry['subject']
            predicate_id = stmt_entry['predicate']
            object_id = stmt_entry['object']

            # add subject to node_str_list for node query
            node_query_item_list.append('<{}>'.format(subject_id))

            if predicate_id == 'type':
                stmt_query_item_list.append(
                    '{{\n?x rdf:subject <{}> .\n?x rdf:predicate rdf:type .\n'
                    '?x rdf:object <{}> .\n}}'.format(subject_id, object_id))

            else:
                # add object to node_str_list for node query if
                # it's not a typing statement
                node_query_item_list.append('<{}>'.format(object_id))

                stmt_query_item_list.append(
                    '{{\n?x rdf:subject <{}> .\n?x rdf:predicate '
                    'domainOntology:{} .\n?x rdf:object <{}> .\n}}'.format(
                        subject_id, predicate_id, object_id))

        elif stmt_entry['type'] == 'ClusterMembership':
            # do not handle facet-cluster-membership entries for now
            # if stmt.startswith('facet-cluster'):
            #     continue

            cluster_id = stmt_entry['cluster']
            if cluster_id.startswith('facet-cluster'):
                cluster_id = \
                    'http://www.utexas.edu/aida/entrypoint-coref/{}/{}'.format(
                        soin_id, cluster_id)
            member_id = stmt_entry['clusterMember']

            node_query_item_list.append('<{}>'.format(cluster_id))
            node_query_item_list.append('<{}>'.format(member_id))

            stmt_query_item_list.append(
                '{{\n?x aida:cluster <{}> .\n'
                '?x aida:clusterMember <{}> \n}}'.format(cluster_id, member_id))

        else:
            print('Unrecognized statement:\n{}'.format(stmt_entry))

    node_query_item_list = list(set(node_query_item_list))
    stmt_query_item_list = list(set(stmt_query_item_list))

    node_query_list = produce_node_queries(
        node_query_item_list, num_node_queries=num_node_queries,
        node_query_prefix=node_query_prefix)

    stmt_query_list = produce_stmt_queries(
        stmt_query_item_list, stmt_query_prefix=stmt_query_prefix,
        num_stmts_per_query=num_stmts_per_query)

    return node_query_list, stmt_query_list


def main():
    parser = ArgumentParser()
    parser.add_argument('aida_graph_path', help='path to aidagraph.json')
    parser.add_argument('aida_result_path', help='path to aidaresult.json')
    parser.add_argument('db_path_prefix', help='prefix of tdb database path')
    parser.add_argument('soin_id', help='id of the SOIN')
    parser.add_argument('output_dir', help='path to output directory')
    parser.add_argument('--top', default=3, type=int,
                        help='number of top hypothesis to output')
    parser.add_argument('--dry_run', action='store_true',
                        help='if specified, only write the SPARQL queries to '
                             'files,'
                             'without actually executing the queries')

    args = parser.parse_args()

    print('Reading AIDA graph from {}'.format(args.aida_graph_path))
    with open(args.aida_graph_path, 'r') as fin:
        aida_graph = json.load(fin)

    print('Reading AIDA result from {}'.format(args.aida_result_path))
    with open(args.aida_result_path, 'r') as fin:
        aida_result = json.load(fin)

    if not exists(args.output_dir):
        print('Creating output directory {}'.format(args.output_dir))
        makedirs(args.output_dir)

    print('Found {} hypothesese with probability {}'.format(
        len(aida_result['probs']), aida_result['probs']))

    db_path_prefix = Path(args.db_path_prefix)
    db_path_list = [str(path) for path in sorted(db_path_prefix.glob('copy*'))]
    print('Using the following tdb databases to query: {}'.format(db_path_list))

    num_node_queries = len(db_path_list)

    top_count = 0
    for result_idx, prob in sorted(
            enumerate(aida_result['probs']), key=itemgetter(1), reverse=True):
        result = aida_result['support'][result_idx]
        node_query_list, stmt_query_list = \
            queries_for_aida_result(aida_graph, result, soin_id=args.soin_id,
                                    num_node_queries=num_node_queries)

        top_count += 1

        print('Writing queries for top #{} hypothesis with prob {}'.format(
            top_count, prob))

        execute_sparql_queries(
            node_query_list, stmt_query_list, db_path_list, args.output_dir,
            filename_prefix='hypothesis-{}'.format(top_count),
            num_header_lines=7, dry_run=args.dry_run)

        if top_count >= args.top:
            break


if __name__ == '__main__':
    main()
