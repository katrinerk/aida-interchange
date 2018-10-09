import json
import sys
from os import makedirs
from os.path import exists, join

all_neighbors_path = sys.argv[1]
output_dir = sys.argv[2]

if not exists(output_dir):
    makedirs(output_dir)

with open(all_neighbors_path, 'r') as fin:
    all_neighbors = json.load(fin)

# write query for all ERE and SameAsCluster nodes
node_str_list = []
for node in all_neighbors['eres'] + all_neighbors['clusters']:
    node_str_list.append('<{}>'.format(node))

print('Found {} nodes to query'.format(len(node_str_list)))

num_nodes = len(node_str_list)
split_num = int(num_nodes / 3)

node_str_list_list = [
    node_str_list[:split_num],
    node_str_list[split_num: split_num * 2],
    node_str_list[split_num * 2:]
]

for i in range(3):
    node_query_str = 'DESCRIBE ' + ' '.join(node_str_list_list[i]) + '\n'

    with open(join(output_dir, 'node_query_{}.rq'.format(i)), 'w') as fout:
        fout.write(node_query_str)

# write query for all general and typing Statements, and ClusterMemberships
stmt_str_list = []
for subj, obj in all_neighbors['typing_statements'] + \
                 all_neighbors['general_statements']:
    stmt_str_list.append(
        '{{\n?x rdf:subject <{}> .\n?x rdf:object <{}> .\n}}'.format(
            subj, obj))

for member, cluster in all_neighbors['cluster_memberships']:
    stmt_str_list.append(
        '{{\n?x aida:cluster <{}> .\n?x aida:clusterMember <{}> .\n}}'.format(
            cluster, member))

num_stmt_per_query = 3000

stmt_query_prefix = \
    'PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' \
    'PREFIX aida:  <https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/' \
    'InterchangeOntology#>\n\n' \
    'DESCRIBE ?x\n' \
    'WHERE {'

stmt_query_str = stmt_query_prefix

stmt_count = 0
stmt_query_count = 0
for stmt_str in stmt_str_list:
    stmt_count += 1
    stmt_query_str += '\n' + stmt_str
    if stmt_count < num_stmt_per_query:
        stmt_query_str += '\nUNION'
    else:
        stmt_query_str += '\n}\n'
        output_path = join(
            output_dir, 'stmt_query_{}.rq'.format(stmt_query_count))
        with open(output_path, 'w') as fout:
            fout.write(stmt_query_str)

        stmt_count = 0
        stmt_query_count += 1
        stmt_query_str = stmt_query_prefix
