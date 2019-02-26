# Katrin Erk Jan 2019:
# Given json with gold hypothesis annotation
# (which EREs support/partially support/contradict a given hypothesis),
# write out all hypotheses in human readable form.
# Doing hypothesis cleanup: what is supporting cannot be contradicting
#
# usage:
# python3 json_gold_hypotheses.py <inputfile.json> <outputdirectory>
#
# Output is written to output directory, one text file and one graph file per hypothesis


import sys
import json
import re


from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

from  aif import AidaJson

###################################

####
# Given a hypothesis, yield all statements that stand in the given relation
# (hypotheses_supported, hypotheses_partially_supported, hypotheses_contradicted)
# to this hypothesis
def each_statement_mentioning_hypothesis(hypothesis, hyprelation, json_obj):
    for label, node in json_obj.thegraph.items():
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
    json_obj = AidaJson(json.load(fin))

    
###
# make a list of all hypotheses
# hypotheses is a set of hypothesis labels
hypotheses = set()
for label, node in json_obj.thegraph.items():
    for hyptype in ["hypotheses_supported", "hypotheses_partially_supported", "hypotheses_contradicted"]:
        if hyptype in node:
            hypotheses.update(node[hyptype])

###
# Write output for each hypothesis
for hypothesis in hypotheses:
    filename = outdir + "/" + hypothesis + "txt"
    jsonfilename = outdir + "/" + hypothesis + ".json"
    graphfilename = outdir + "/" + hypothesis + ".viz"

    json_obj.graphviz(outfilename = graphfilename, showview = False, unary_stmt=True)
    
    # determine supporting, partially supporting, contradicting statements for this hypothesis
    hyp_supporting = set(each_statement_mentioning_hypothesis(hypothesis, "hypotheses_supported", json_obj))
    hyp_partially_supporting = set(each_statement_mentioning_hypothesis(hypothesis, "hypotheses_partially_supported", json_obj))
    hyp_contradicting = set(each_statement_mentioning_hypothesis(hypothesis, "hypotheses_contradicted", json_obj))

    # handle statements that appear in multiple sets
    # if stmts are both supporting and partially supporting, keep only the stronger category
    hyp_partially_supporting.difference_update(hyp_supporting)
    # keep separate statements that appear in both contradicting and (partially) supporting
    hyp_multi = (hyp_supporting.union(hyp_partially_supporting)).intersection(hyp_contradicting)
    hyp_supporting.difference_update(hyp_multi)
    hyp_partially_supporting.difference_update(hyp_multi)
    hyp_contradicting.difference_update(hyp_multi)

    # write json output
    with open(jsonfilename, "w") as fout:
        json.dump({
            "supporting" : list(hyp_supporting),
            "partially_supporting" : list(hyp_partially_supporting),
            "contradicting" : list(hyp_contradicting),
            "both_supporting_and_contradicting" : list(hyp_multi)
            }, fout, indent = 1)
        

    # write text output
    with open(filename, "w") as fout:
        print("=======================================", file = fout)
        print("==== Hypothesis", hypothesis, "============", file = fout)
        print("=======================================", file = fout)

        for hyptype, hypset in [["Supporting statements", hyp_supporting], \
                                      ["Partially supporting statements", hyp_partially_supporting], \
                                      ["Contradicting statements", hyp_contradicting], \
                                    ["Statements listed as both supporting and contradicting", hyp_multi]]:

            print("---------------------------------------", file = fout)
            print("----", hyptype, "------------", file = fout)
            print("---------------------------------------", file = fout)

            for label in json_obj.sorted_statements_for_output(hypset):
                json_obj.print_statement_info(label, fout)


