import sys
import json

import os
import re

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from seeds.aidahypothesis import AidaHypothesis, AidaHypothesisCollection

###############33

hypothesis_filename = sys.argv[1]
graph_filename = sys.argv[2]
outdir = sys.argv[3]

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))

    
with open(hypothesis_filename, 'r') as fin:
    json_hypotheses = json.load(fin)
    hypothesis_collection = AidaHypothesisCollection.from_json(json_hypotheses, graph_obj)

for index, hypothesis in enumerate(hypothesis_collection.hypotheses):
    outfilename = os.path.join(outdir, "hypothesis" + str(index) + ".txt")
    with open(outfilename, "w") as fout:
        print(hypothesis.to_s(), file = fout)
