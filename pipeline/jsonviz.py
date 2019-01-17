# Katrin Erk January 2019
# given a json AIDA file, visualize the graph
#
# usage:
# python3 jsonviz.ph <AIDAgraph.json> [<output file prefix>]


import sys
import json
import subprocess
import os
import graphviz


from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson

####
def nodeshortlabel(label):
    return label.split("/")[-1].split("#")[-1]

##################
# read json file
json_filename = sys.argv[1]

if len(sys.argv) > 2:
    graph_filename = sys.argv[2]
else:
    graph_filename = None


with open(json_filename, 'r') as fin:
    json_obj = AidaJson(json.load(fin))

###
# visualize
dot = graphviz.Digraph(comment = "AIDA graph", engine = "circo")

# color scheme
colorscheme = {
    "Entity" : "beige",
    "Event" : "lightblue",
    "Relation": "lightgrey"
    }

# make all the ERE nodes
for nodelabel, node in json_obj.each_ere():

    characterization = json_obj.ere_characterization(nodelabel)
    erecolor = colorscheme[ node["type"]]

    nodecontent = ""
    if "typestmt" in characterization and characterization["typestmt"] != "":
        nodecontent += "type:" + characterization["typestmt"] + "\n"

    if "name" in characterization and characterization["name"] != "":
        nodecontent += characterization["name"]
        
    ## characterization = node["type"][:2]
    ## if node["type"] == "Statement":
    ##     characterization += "\npred:" + node["predicate"]
    ## if "name" in node:
    ##     characterization += "\nname: " + node["name"]
    ## if "subject" in node and node["subject"] not in json_obj["theGraph"]:
    ##     characterization +="\nsubj:" + nodeshortlabel(node["subject"])
    ## if "object" in node and node["object"] not in json_obj["theGraph"]:
    ##     characterization +="\nobj:" + nodeshortlabel(node["object"])

    dot.node(nodeshortlabel(nodelabel),  nodecontent, color=erecolor, style = "filled")


# make statements into connections
for nodelabel, node in json_obj.each_statement():
    # statements that connects two EREs
    if json_obj.is_ere(node["subject"]) and json_obj.is_ere(node["object"]):
        dot.edge(nodeshortlabel(node["subject"]), nodeshortlabel(node["object"]), label = node["predicate"])

    else:
        if node["predicate"] != "type":
            print("Omitting statement:", nodelabel, node["predicate"])
        

if graph_filename:
    dot.render(graph_filename, view=True)
else:
    dot.render(view=True)


