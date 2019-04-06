# Katrin Erk March 2019
# Rule-based expansion of hypotheses

import sys
from collections import deque



from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from seeds.aidahypothesis import AidaHypothesis
from seeds.hypothesisfilter import AidaHypothesisFilter

        
        
#########################
#########################
# class that manages cluster expansion
class ClusterExpansion:
    # initialize with an AidaJson object and a list of AidaHypothesis objects
    def __init__(self, graph_obj, hypothesis_obj):
        self.graph_obj = graph_obj
        self.hypothesis_obj = hypothesis_obj

    # compile json object that lists all the hypotheses with their statements
    def to_json(self):
        return self.hypothesis_obj.to_json()

    # make a list of strings with the clusters in readable form
    def to_s(self):
        return self.hypothesis_obj.to_s()

    # for each ERE, add all typing statements.
    # This is done using add_stmt and not extend
    # because all type statements are currently thought to be compatible
    def type_completion(self):
        for hypothesis in self.hypothesis_obj.hypotheses:
            for ere_id in hypothesis.eres():
                for stmtlabel in self.graph_obj.each_ere_adjacent_stmt(ere_id, "type", "subject"):
                    hypothesis.add_stmt(stmtlabel)

 
