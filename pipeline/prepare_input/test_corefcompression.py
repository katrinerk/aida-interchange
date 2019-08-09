import json
import sys
from collections import defaultdict
from os.path import dirname, realpath

src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

from aif import AidaJson

graph_filename = sys.argv[1]

print('Loading json graph from {}'.format(graph_filename))
with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))
print('\tDone\n')

# nodes that are in use
used_nodes = set()
for stmt_label, _ in graph_obj.each_statement():
    subj_label = graph_obj.stmt_subject(stmt_label)
    if subj_label in graph_obj.thegraph:
        used_nodes.add(subj_label)
    obj_label = graph_obj.stmt_object(stmt_label)
    if obj_label in graph_obj.thegraph:
        used_nodes.add(obj_label)

# map cluster -> members that are in use
cluster_all_members = defaultdict(set)
cluster_used_members = defaultdict(set)

for label in graph_obj.thegraph.keys():
    if graph_obj.thegraph[label].get("type", None) == "ClusterMembership":
        cluster = graph_obj.thegraph[label].get("cluster", None)
        member = graph_obj.thegraph[label].get("clusterMember", None)
        if cluster is not None and member is not None:
            cluster_all_members[cluster].add(member)
            if member in used_nodes:
                cluster_used_members[cluster].add(member)

clusters_w_more_than_one_members = [
    cluster for cluster, all_members in cluster_all_members.items()
    if len(all_members) > 1]
clusters_w_more_than_one_used_members = [
    cluster for cluster, used_members in cluster_used_members.items()
    if len(used_members) > 1]

print('# all clusters:', len(cluster_all_members))
print('# clusters with more than one members:',
      len(clusters_w_more_than_one_members))
print('# clusters with more than one used members:',
      len(clusters_w_more_than_one_used_members))

if len(clusters_w_more_than_one_used_members) > 1:
    print('The graph is not coref-compressed')
elif len(clusters_w_more_than_one_members) > 1:
    print('The graph is weakly coref-compressed')
else:
    print('The graph is strongly coref-compressed')
