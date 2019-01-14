# Katrin Erk January 2019
# given a json AIDA file, visualize the graph


import sys
import json
import subprocess
import os
import graphviz


from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

####
def nodeshortlabel(label):
    return label.split("/")[-1]


# read json file
json_filename = sys.argv[1]


with open(json_filename, 'r') as fin:
    json_obj = json.load(fin)

# visualize
dot = graphviz.Digraph(comment = "AIDA graph", engine = "circo")

# make all the nodes
for nodelabel, node in json_obj["theGraph"].items():
    
    characterization = node["type"][:2]
    if node["type"] == "Statement":
        characterization += "\npred:" + node["predicate"]
    if "name" in node:
        characterization += "\nname: " + node["name"]
    if "subject" in node and node["subject"] not in json_obj["theGraph"]:
        characterization +="\nsubj:" + nodeshortlabel(node["subject"])
    if "object" in node and node["object"] not in json_obj["theGraph"]:
        characterization +="\nobj:" + nodeshortlabel(node["object"])

    dot.node(nodeshortlabel(nodelabel),  characterization)


# make all the connections
for nodelabel, node in json_obj["theGraph"].items():
    if node["type"] == "Statement" and node["subject"] in json_obj["theGraph"]:
        dot.edge(nodeshortlabel(nodelabel), nodeshortlabel(node["subject"]), label = "subject")
        
    if node["type"] == "Statement" and node["object"] in json_obj["theGraph"]:
        dot.edge(nodeshortlabel(nodelabel), nodeshortlabel(node["object"]), label = "object")

dot.render(view=True)

