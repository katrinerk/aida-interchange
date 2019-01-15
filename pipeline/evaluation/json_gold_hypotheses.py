# Katrin Erk Jan 2019:
# Given json with gold hypothesis annotation
# (which EREs support/partially support/contradict a given hypothesis),
# write out all hypotheses in human readable form.
#
# usage:
# python3 json_gold_hypotheses.py <inputfile.json> <outputdirectory>
#
# Output is written to output directory, one file per hypothesis


import sys
import json
import re

import json_prettyprint

###################################

####
def each_statement_mentioning_hypothesis(hypothesis, hyprelation, json_obj):
    for label, node in json_obj["theGraph"].items():
        if node["type"] == "Statement" and hypothesis in node.get(hyprelation, []):
            yield label
        
#######################
###
# Input is a json file that encodes the contents of an AIF file
jsonfilename = sys.argv[1]
# output is a directory into which all the hypotheses will be written
outdir = sys.argv[2]

# read input
with open(jsonfilename, 'r') as fin:
    json_obj = json.load(fin)

###
# make a list of all hypotheses
hypotheses = set()
for label, node in json_obj["theGraph"].items():
    for hyptype in ["hypotheses_supported", "hypotheses_partially_supported", "hypotheses_contradicted"]:
        if hyptype in node:
            hypotheses.update(node[hyptype])

###
# Write output for each hypothesis
for hypothesis in hypotheses:
    filename = outdir + "/" + hypothesis + "txt"
    with open(filename, "w") as fout:
        print("=======================================", file = fout)
        print("==== Hypothesis", hypothesis, "============", file = fout)
        print("=======================================", file = fout)

        # determine supporting, partially supporting, contradicting statements for this hypothesis
        hyp_supporting = set(each_statement_mentioning_hypothesis(hypothesis, "hypotheses_supported", json_obj))
        hyp_partially_supporting = set(each_statement_mentioning_hypothesis(hypothesis, "hypotheses_partially_supported", json_obj))
        hyp_contradicting = set(each_statement_mentioning_hypothesis(hypothesis, "hypotheses_contradicted", json_obj))

        # handle statements that appear in multiple sets
        # if stmts are both supporting and partially supporting, keep only the stronger category
        hyp_partially_supporting.difference_update(hyp_contradicting)
        # keep separate statements that appear in both contradicting and (partially) supporting
        hyp_multi = (hyp_supporting.union(hyp_partially_supporting)).intersection(hyp_contradicting)
        hyp_supporting.difference_update(hyp_multi)
        hyp_partially_supporting.difference_update(hyp_multi)
        hyp_contradicting.difference_update(hyp_multi)
        

        for hyptype, hypset in [["Supporting statements", hyp_supporting], \
                                      ["Partially supporting statements", hyp_partially_supporting], \
                                      ["Contradicting statements", hyp_contradicting], \
                                    ["Statements listed as both supporting and contradicting", hyp_multi]]:

            print("---------------------------------------", file = fout)
            print("----", hyptype, "------------", file = fout)
            print("---------------------------------------", file = fout)

            for label in hypset:
                json_prettyprint.print_statement_info(label, json_obj, fout)


