import json
import sys

aidagraph_path = sys.argv[1]
aidaquery_path = sys.argv[2]

with open(aidagraph_path, 'r') as fin:
    aidagraph = json.load(fin)

with open(aidaquery_path, 'r') as fin:
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

new_aidagraph_path = sys.argv[3]

with open(new_aidagraph_path, 'w') as fout:
    json.dump(aidagraph, fout, indent=1)
