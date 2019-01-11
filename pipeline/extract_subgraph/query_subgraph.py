# Pengxiang Cheng Fall 2018
# pre- and postprocessing for the AIDA eval

import json
from argparse import ArgumentParser
from pathlib import Path

from pipeline.sparql_helper import *

parser = ArgumentParser()
parser.add_argument('all_neighbors_path', help='path to all_neighbors.json')
parser.add_argument('db_path_prefix', help='prefix of tdb database path')
parser.add_argument('output_dir', help='path to output directory')
parser.add_argument('--dry_run', action='store_true',
                    help='if specified, only write the SPARQL queries to files,'
                         'without actually executing the queries')

args = parser.parse_args()

output_dir = args.output_dir

if not exists(output_dir):
    makedirs(output_dir)

with open(args.all_neighbors_path, 'r') as fin:
    all_neighbors = json.load(fin)

db_path_prefix = Path(args.db_path_prefix)
db_path_list = [str(path) for path in sorted(db_path_prefix.glob('copy*'))]
print('Using the following tdb databases to query: {}'.format(db_path_list))

# queries for all ERE and SameAsCluster nodes
node_query_element_list = []
for node in all_neighbors['eres'] + all_neighbors['clusters']:
    node_query_element_list.append('<{}>'.format(node))

print('Found {} nodes to query'.format(len(node_query_element_list)))

node_query_prefix = 'DESCRIBE '
num_node_queries = len(db_path_list)

node_query_list = produce_node_queries(
    node_query_element_list, num_node_queries=num_node_queries,
    node_query_prefix=node_query_prefix)

# queries for all general and typing Statements, and ClusterMemberships
stmt_query_element_list = []
for subj, obj in all_neighbors['typing_statements'] + \
                 all_neighbors['general_statements']:
    stmt_query_element_list.append(
        '{{\n?x rdf:subject <{}> .\n?x rdf:object <{}> .\n}}'.format(
            subj, obj))

for member, cluster in all_neighbors['cluster_memberships']:
    stmt_query_element_list.append(
        '{{\n?x aida:cluster <{}> .\n?x aida:clusterMember <{}> .\n}}'.format(
            cluster, member))

print('Found {} statements to query'.format(len(stmt_query_element_list)))

num_stmts_per_query = 3000

stmt_query_prefix = \
    'PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' \
    'PREFIX aida:  <https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/' \
    'InterchangeOntology#>\n\n' \
    'DESCRIBE ?x\n' \
    'WHERE {'

stmt_query_list = produce_stmt_queries(
    stmt_query_element_list, stmt_query_prefix=stmt_query_prefix,
    num_stmts_per_query=num_stmts_per_query)

execute_sparql_queries(
    node_query_list, stmt_query_list, db_path_list, output_dir,
    filename_prefix='subgraph', num_header_lines=7, dry_run=args.dry_run)
