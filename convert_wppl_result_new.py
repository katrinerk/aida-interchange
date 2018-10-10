import json
from argparse import ArgumentParser
from operator import itemgetter
from os import makedirs
from os.path import exists, join
import subprocess


db_path_list = [
    '/home/cc/aida/tdb_database_P103_Q004',
    '/home/cc/aida/tdb_database_P103_Q004_copy',
    '/home/cc/aida/tdb_database_P103_Q004_copy2',
    '/home/cc/aida/tdb_database_P103_Q004_copy3',
    '/home/cc/aida/tdb_database_P103_Q004_copy4'
]


def queries_for_aida_result(aida_graph, result, num_stmts_per_query=3000):
    node_query_prefix = 'DESCRIBE '
    stmt_query_prefix = \
        'PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' \
        'PREFIX aida:  <https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/' \
        'InterchangeOntology#>\n' \
        'PREFIX domainOntology: <https://tac.nist.gov/tracks/SM-KBP/2018/' \
        'ontologies/SeedlingOntology#>\n\n' \
        'DESCRIBE ?x\n' \
        'WHERE {\n'

    node_query_list = []
    stmt_query_list = []

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
                    '{{\n?x rdf:subj <{}> .\n?x rdf:predicate '
                    'domainOntology:{} .\n?x rdf:object <{}> .\n}}'.format(
                        subject_id, predicate_id, object_id))

        elif stmt_entry['type'] == 'ClusterMembership':
            # do not handle facet-cluster-membership entries for now
            if stmt.startswith('facet-cluster'):
                continue

            cluster_id = stmt_entry['cluster']
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

    num_node_queries = (len(db_path_list) - 1)

    num_nodes = len(node_query_item_list)
    split_num = int(num_nodes / num_node_queries)

    node_query_list.append(
        node_query_prefix + ' '.join(node_query_item_list[:split_num]))
    for node_query_idx in range(1, num_node_queries - 1):
        node_query_list.append(
            node_query_prefix +
            ' '.join(node_query_item_list[
                split_num * node_query_idx: split_num * (node_query_idx + 1)]))
    node_query_list.append(node_query_prefix + ' '.join(
        node_query_item_list[split_num * (num_node_queries - 1):]))

    # num_nodes = len(node_query_item_list)
    # num_nodes_finished = 0
    #
    # while num_nodes_finished < num_nodes:
    #     start_offset = num_nodes_finished
    #     end_offset = num_nodes_finished + num_nodes_per_query
    #     node_query = node_query_prefix
    #
    #     if end_offset <= num_nodes:
    #         node_query += ' '.join(
    #             node_query_item_list[start_offset: end_offset])
    #         num_nodes_finished = end_offset
    #     else:
    #         node_query += ' '.join(
    #             node_query_item_list[start_offset:])
    #         num_nodes_finished = num_nodes
    #
    #     node_query_list.append(node_query)

    num_stmts = len(stmt_query_item_list)
    num_stmts_finished = 0

    while num_stmts_finished < num_stmts:
        start_offset = num_stmts_finished
        end_offset = num_stmts_finished + num_stmts_per_query
        stmt_query = stmt_query_prefix

        if end_offset <= num_stmts:
            stmt_query += '\nUNION\n'.join(
                stmt_query_item_list[start_offset: end_offset])
            num_stmts_finished = end_offset
        else:
            stmt_query += '\nUNION\n'.join(
                stmt_query_item_list[start_offset:])
            num_stmts_finished = num_stmts

        stmt_query += '\n}\n'
        stmt_query_list.append(stmt_query)

    return node_query_list, stmt_query_list


def main():
    parser = ArgumentParser()
    parser.add_argument('aida_graph_path', help='path to aidagraph.json')
    parser.add_argument('aida_result_path', help='path to aidaresult.json')
    parser.add_argument('output_dir', help='path to output directory')
    parser.add_argument('--top', default=3, type=int,
                        help='number of top hypothesis to output')

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

    top_count = 0
    for result_idx, prob in sorted(
            enumerate(aida_result['probs']), key=itemgetter(1), reverse=True):
        result = aida_result['support'][result_idx]
        node_query_list, stmt_query_list = \
            queries_for_aida_result(aida_graph, result)

        top_count += 1

        print('Writing queries for top #{} hypothesis with prob {}'.format(
            top_count, prob))

        query_cmd_list = []

        for node_query_idx, node_query in enumerate(node_query_list):
            node_query_output_path = join(
                args.output_dir, 'hypothesis-{}-node-query-{}.rq'.format(
                    top_count, node_query_idx))
            with open(node_query_output_path, 'w') as fout:
                fout.write(node_query + '\n')

            node_query_result_path = join(
                args.output_dir, 'hypothesis-{}-node-query-{}-result.ttl'.format(
                    top_count, node_query_idx))
            query_cmd_list.append(
                'echo "query {}"; tdbquery --loc {} --query {} > {}'.format(
                    node_query_output_path, db_path_list[node_query_idx],
                    node_query_output_path, node_query_result_path))

        stmt_query_cmd = ''
        for stmt_query_idx, stmt_query in enumerate(stmt_query_list):
            stmt_query_output_path = join(
                args.output_dir, 'hypothesis-{}-stmt-query-{}.rq'.format(
                    top_count, stmt_query_idx))
            with open(stmt_query_output_path, 'w') as fout:
                fout.write(stmt_query + '\n')

            stmt_query_result_path = join(
                args.output_dir, 'hypothesis-{}-stmt-query-{}-result.ttl'.format(
                    top_count, stmt_query_idx))
            stmt_query_cmd += \
                'echo "query {}"; tdbquery --loc {} --query {} > {}; '.format(
                    stmt_query_output_path, db_path_list[-1],
                    stmt_query_output_path, stmt_query_result_path)

        query_cmd_list.append(stmt_query_cmd)

        process_list = [
            subprocess.Popen(cmd, shell=True) for cmd in query_cmd_list]

        for process in process_list:
            process.wait()

        merge_cmd = \
            'cp {0}/hypothesis-{1}-node-query-0-result.ttl ' \
            '{0}/hypothesis-{1}-result.ttl; '.format(args.output_dir, top_count)
        for node_query_idx in range(1, len(node_query_list)):
            merge_cmd += \
                'tail -n +8 {0}/hypothesis-{1}-node-query-{2}-result.ttl ' \
                '>> {0}/hypothesis-{1}-result.ttl; '.format(
                    args.output_dir, top_count, node_query_idx)
        for stmt_query_idx in range(len(stmt_query_list)):
            merge_cmd += \
                'tail -n +8 {0}/hypothesis-{1}-stmt-query-{2}-result.ttl ' \
                '>> {0}/hypothesis-{1}-result.ttl; '.format(
                    args.output_dir, top_count, stmt_query_idx)

        print('Merge query output to {}/hypothesis-{}-result.ttl'.format(
            args.output_dir, top_count))
        # print(merge_cmd)
        subprocess.call(merge_cmd, shell=True)

        clean_cmd = \
            'rm {0}/hypothesis-{1}-node-query-*; ' \
            'rm {0}/hypothesis-{1}-stmt-query-*'.format(
                args.output_dir, top_count)
        print('Clean up intermediate output in {}'.format(args.output_dir))
        # print(clean_cmd)
        subprocess.call(clean_cmd, shell=True)

        if top_count >= args.top:
            break


if __name__ == '__main__':
    main()
