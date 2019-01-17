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


##################
# read json file
json_filename = sys.argv[1]

if len(sys.argv) > 2:
    graph_filename = sys.argv[2]
else:
    graph_filename = None


with open(json_filename, 'r') as fin:
    json_obj = AidaJson(json.load(fin))


json_obj.graphviz(showview = True, outfilename = graph_filename)
