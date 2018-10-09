# Katrin Erk Oct 7 2018
# read aida results json object, along
# with log object from from coref.py, to
# produce an aidaresults.json that looks as
# if aidabaseline.wppl had run without coref transformation
#
# usage:
# python3 postcoref.py <aidaresult.json> <aidacoreflog.json>
#
# writes new aidaresult.json.
# the previous aida results file will be in original_aidaresult.json

import json
import random
import sys

infilename1 = sys.argv[1]
infilename2 = sys.argv[2]
    
f = open(infilename1)
json_in = json.load(f)
f.close()

f = open(infilename2)
json_log = json.load(f)
f.close()


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
outf = open("original_aidaresult.json", "w")
json.dump(json_in, outf, indent = 1)
outf.close()

outf = open("aidaresult.json", "w")
json.dump(json_out, outf, indent = 1)
outf.close()

    
