# Katrin Erk Oct 7 2018
# read aida results json object, along
# with log object from from coref.py, to
# produce an aidaresults.json that looks as
# if aidabaseline.wppl had run without coref transformation
#
# usage:
# python3 postcoref.py <aidaresult.json> <coref_log.json> <aidaresult_output.json>
#
# writes new aidaresult_output.json.

import json
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('input_aidaresult',
                    help='path to input aidaresult.json file')
parser.add_argument('coref_log',
                    help='path to coref_log.json file from coref.py')
parser.add_argument('output_aidaresult',
                    help='path to output aidaresult.json file')

args = parser.parse_args()

with open(args.input_aidaresult, 'r') as fin:
    json_in = json.load(fin)

with open(args.coref_log, 'r') as fin:
    json_log = json.load(fin)

# this is going to be the new aidaresult.json
json_out = { }
    
# probs does not change
json_out["probs"] = json_in["probs"]

json_out["support"] = [ ]

for cluster in json_in["support"]:
    newcluster = { }
    newcluster["failedQueries"] = cluster["failedQueries"]
    newstatements = [ ]

    # map each statement from cluster to a list of statements
    # from the original statement list
    for stmt in cluster["statements"]:
        newstatements = newstatements + json_log["stmtName"][stmt]

    # append all the coref statements
    newstatements.extend(json_log["coref"])

    # and done with this cluster
    newcluster["statements"] = newstatements
    json_out["support"].append(newcluster)


################
# write output

with open(args.output_aidaresult, "w") as fout:
    json.dump(json_out, fout, indent = 1)
