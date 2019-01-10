# Pengchiang Cheng Fall 2018
# Preprocessing for AIDA eval
# part of scripts for coref compression

import json
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('input_aidagraph',
                    help='path to input aidagraph.json file')
parser.add_argument('input_aidaquery',
                    help='path to input aidaquery.json file')
parser.add_argument('output_aidagraph',
                    help='path to output aidagraph.json file')

args = parser.parse_args()

with open(args.input_aidagraph, 'r') as fin:
    aidagraph = json.load(fin)

with open(args.input_aidaquery, 'r') as fin:
    aidaquery = json.load(fin)

prototypes = set([])
for entrypoint in aidaquery['entrypoints']:
    prototypes.update(entrypoint['ere'])

print('Prototypes: {}'.format(prototypes))

coref_counter = len([
    node for node, content in aidagraph['theGraph'].items()
    if content['type'] == 'ClusterMembership'])

for cluster, member_list in aidaquery['coref'].items():
    cluster_name = 'facet-cluster-' + cluster
    print('Adding SameAsCluster node: {}'.format(cluster_name))
    # add new cluster node
    aidagraph['theGraph'][cluster_name] = {'type': 'SameAsCluster'}

    for member in member_list:
        assert member in aidagraph['theGraph']

        # add new clusterMembership node
        cluster_membership_name = 'facet-cluster-membership-' + member
        print('Adding ClusterMembership node: {}'.format(
            cluster_membership_name))
        aidagraph['theGraph'][cluster_membership_name] = {
            'type': 'ClusterMembership',
            'cluster': cluster_name,
            'clusterMember': member,
            'conf': 1.0,
            'index': coref_counter,
        }
        coref_counter += 1

        # add prototype information of cluster node
        if member in prototypes:
            aidagraph['theGraph'][cluster_name]['prototype'] = member

with open(args.output_aidagraph, 'w') as fout:
    json.dump(aidagraph, fout, indent=1)
