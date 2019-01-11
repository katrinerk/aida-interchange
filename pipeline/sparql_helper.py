# Pengxiang Cheng Fall 2018
# pre- and postprocessing for the AIDA eval

from os.path import exists, join
from os import makedirs
import subprocess


# split node_query_item_list evenly into num_node_queries partitions,
# then generate a query string for each partition.
def produce_node_queries(
        node_query_item_list, num_node_queries, node_query_prefix='DESCRIBE '):
    node_query_item_list = list(set(node_query_item_list))

    node_query_list = []

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

    return node_query_list


# split stmt_query_item_list into several partitions, with at most
# num_stmts_per_query statements per partition, then generate a query string
# for each partition.
def produce_stmt_queries(
        stmt_query_item_list, stmt_query_prefix, num_stmts_per_query=3000):
    stmt_query_list = []

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

        stmt_query += '\n}'
        stmt_query_list.append(stmt_query)

    return stmt_query_list


# execute a list of node queries and a list of statement queries in parallel
# on a bunch of TDB database copies. The number of node queries should be
# equal to the number of DB copies.
# set dry_run = True to only write the query files without executing them.
def execute_sparql_queries(node_query_list, stmt_query_list, db_path_list,
                           output_dir, filename_prefix, num_header_lines=7,
                           dry_run=False):
    assert len(node_query_list) == len(db_path_list)

    if not exists(output_dir):
        makedirs(output_dir)

    query_cmd_list = []

    print('Writing queries to files ...')
    for node_query_idx, node_query in enumerate(node_query_list):
        node_query_path = join(output_dir, '{}-node-query-{}.rq'.format(
            filename_prefix, node_query_idx))
        with open(node_query_path, 'w') as fout:
            fout.write(node_query + '\n')

        node_query_result_path = join(
            output_dir, '{}-node-query-{}-result.ttl'.format(
                filename_prefix, node_query_idx))
        query_cmd_list.append(
            'echo "query {0}"; tdbquery --loc {1} --query {0} > {2}; '.format(
                node_query_path, db_path_list[node_query_idx],
                node_query_result_path))

    num_db = len(db_path_list)
    num_stmt_query = len(stmt_query_list)

    for stmt_query_idx, stmt_query in enumerate(stmt_query_list):
        stmt_query_path = join(output_dir, '{}-stmt-query-{}.rq'.format(
            filename_prefix, stmt_query_idx))
        with open(stmt_query_path, 'w') as fout:
            fout.write(stmt_query + '\n')

        stmt_query_result_path = join(
            output_dir, '{}-stmt-query-{}-result.ttl'.format(
                filename_prefix, stmt_query_idx))

        db_idx = int(stmt_query_idx / num_stmt_query * num_db)
        query_cmd_list[db_idx] += \
            'echo "query {0}"; tdbquery --loc {1} --query {0} > {2}; '.format(
                stmt_query_path, db_path_list[db_idx], stmt_query_result_path)

    if not dry_run:
        print('Executing queries ...')
        process_list = [
            subprocess.Popen(cmd, shell=True) for cmd in query_cmd_list]

        for process in process_list:
            process.wait()

    merge_cmd = \
        'cp {0}/{1}-node-query-0-result.ttl ' \
        '{0}/{1}-result.ttl; '.format(output_dir, filename_prefix)
    for node_query_idx in range(1, len(node_query_list)):
        merge_cmd += \
            'tail -n +{3} {0}/{1}-node-query-{2}-result.ttl ' \
            '>> {0}/{1}-result.ttl; '.format(
                output_dir, filename_prefix, node_query_idx, num_header_lines+1)
    for stmt_query_idx in range(len(stmt_query_list)):
        merge_cmd += \
            'tail -n +{3} {0}/{1}-stmt-query-{2}-result.ttl ' \
            '>> {0}/{1}-result.ttl; '.format(
                output_dir, filename_prefix, stmt_query_idx, num_header_lines+1)

    if not dry_run:
        print('Merging query outputs to {}/{}-result.ttl ...'.format(
            output_dir, filename_prefix))
        # print(merge_cmd)
        subprocess.call(merge_cmd, shell=True)

    clean_cmd = \
        'rm {0}/{1}-node-query-*; rm {0}/{1}-stmt-query-*'.format(
            output_dir, filename_prefix)

    if not dry_run:
        print('Cleaning up intermediate outputs in {} ...'.format(output_dir))
        # print(clean_cmd)
        subprocess.call(clean_cmd, shell=True)