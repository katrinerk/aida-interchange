import sys
import json

import os
from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson

#####3
graph_filename = sys.argv[1]

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))


# nodes that are in use
usednodes = set()
for stmtlabel, dummy in graph_obj.each_statement():
    label = graph_obj.stmt_subject(stmtlabel)
    if label in graph_obj.thegraph:
        usednodes.add(label)
    label = graph_obj.stmt_object(stmtlabel)
    if label in graph_obj.thegraph:
        usednodes.add(label)

# map cluster -> members that are in use
cluster_usedmembers = { }

for label in graph_obj.thegraph.keys():
    if graph_obj.thegraph[label].get("type", None) == "ClusterMembership":
        cluster = graph_obj.thegraph[label].get("cluster", None)
        member = graph_obj.thegraph[label].get("clusterMember", None)
        if cluster is not None and member in usednodes:
            if cluster not in cluster_usedmembers: cluster_usedmembers[ cluster ] = set()
            cluster_usedmembers[ cluster ].add(member)


for cluster, used in cluster_usedmembers.items():
    if len(used) > 1:
        print("not compressed", cluster, list(used))

