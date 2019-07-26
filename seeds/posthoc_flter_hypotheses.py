import sys
import json

# Katrin Erk July 2019
# simple post-hoc filter for hypothesis files
#
# usage:
# python3 posthoc_filter_hypotheses.py <hypothesis_filename> <graph_filename> <outfilename>
#
# where hypothesis_filename is a hypothesis/cluster seed json,
# graph_filename is a graph json,
# and outfilename will be overwritten with an updated hypothesis/cluster seed json

import os
import re

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson

from seeds.aidahypothesis import AidaHypothesis, AidaHypothesisCollection
from seeds.hypothesisfilter import AidaHypothesisFilter

#########################
# read graph file and hypothesis file
hypothesis_filename = sys.argv[1]
graph_filename = sys.argv[2]
outfilename = sys.argv[3]

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))

with open(hypothesis_filename, 'r') as fin:
    json_hypotheses = json.load(fin)
    hypothesis_collection = AidaHypothesisCollection.from_json(json_hypotheses, graph_obj)

# make the filter
filter_obj = AidaHypothesisFilter(graph_obj)

new_hypothesis_collection = AidaHypothesisCollection( [])

for hypothesis in hypothesis_collection.hypotheses:
    new_hypothesis = filter_obj.filtered(hypothesis)
    new_hypothesis_collection.add(hypothesis)

with open(outfilename, "w") as fout:
    new_json_hypotheses = new_hypothesis_collection.to_json()
    
    # add graph filename and queries, if they were there before
    if "graph" in json_hypotheses:
        new_json_hypotheses["graph"] = json_hypotheses["graph"]
    if "queries" in json_hypotheses:
        new_json_hypotheses["queries"] = json_hypotheses["queries"]
        
    json.dump(new_json_hypotheses, fout, indent = 1)    

