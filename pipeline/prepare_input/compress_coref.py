# Katrin Erk Oct 7 2018
# pre- and postprocessing for AIDA eval
#
# resolve all coreferences in an aidagraph.json data
# structure, and write a reduced aidagraph.json data structure
# without coreferring EREs or statements,
# along with a second .json file that details which original EREs/
# statements correspond to which reduced ones
#
# usage:
# python3 coref.py <aidagraph.json> <aidaquery.json>
# <aidagraph_output.json> <aidaquery_output.json> <coref_log.json>
#
# writes new aidagraph_output.json, aidaquery_output.json.

import sys
import json
import random
from argparse import ArgumentParser

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import EREUnify

##############
# flip a coin with the given bias. returns True or False
def flip(prob):
    rvalue = random.random()
    if rvalue <= prob:
        return True
    else:
        return False

# given a statement entry from theGraph,
# return a (subject, predicate, object) triple
# where ERE subjects and objects are mapped to their unifiers
def make_stmt_key(stmt_entry, unifier):
    subj = stmt_entry["subject"]
    if subj in unifier:
        subj = unifier[subj]


    pred = stmt_entry["predicate"]
    
    obj = stmt_entry["object"]
    if obj in unifier:
        obj = unifier[obj]

    return (subj, pred, obj)

# given a statement label and the old json object,
# make the statement key and look up the new statement label in the
# oldstmt_newstmt dictionary
def get_newstmt_label(oldstmt, ereunif, the_graph, oldstmt_newstmt):
    if oldstmt not in the_graph:
        return None
    content = the_graph[oldstmt]
    stmt_key = make_stmt_key(content, ereunif)
    return oldstmt_newstmt[ stmt_key] 
    
##############

parser = ArgumentParser()
parser.add_argument('input_aidagraph',
                    help='path to input aidagraph.json file')
parser.add_argument('input_aidaquery',
                    help='path to input aidaquery.json file')
parser.add_argument('output_aidagraph',
                    help='path to output aidagraph.json file')
parser.add_argument('output_aidaquery',
                    help='path to output aidaquery.json file')
parser.add_argument('output_coref_log',
                    help='path to output coref_log.json file')

args = parser.parse_args()

with open(args.input_aidagraph, 'r') as fin:
    json_in = json.load(fin)

with open(args.input_aidaquery, 'r') as fin:
    json_query_in = json.load(fin)


# this is going to be the new aidagraph.json
json_out = { }
# and this is going to be a log of all the changes that were made
json_log = { }

##
# determine coref
# we still do probabilistic coref, but we only do it once

erecoref_obj = EREUnify()

# first, make sure all EREs get a unifier
for label, content in json_in["theGraph"].items():
    if content["type"] in ["Entity", "Event", "Relation"]:
        # yep, we need to write this out
        erecoref_obj.add(label)

# then determine coreference
json_log["coref"] = [ ]

for label, content in json_in["theGraph"].items():
    if content["type"] == "ClusterMembership":
        if flip(content["conf"]):
            # yes, consider this
            json_log["coref"].append(label)
            erecoref_obj.unify_ere_coref(content["clusterMember"], content["cluster"])

            
# mapping: oldname -> new name
ereunif = erecoref_obj.all_new_names()

# invert the mapping to get new name -> list of old names
json_log["ereName"]= { }

for oldname, newname in ereunif.items():
    # log the connection between old and new ERE name
    if newname not in json_log["ereName"]:
        json_log["ereName"][newname] = [ ]
        
    json_log["ereName"][newname].append(oldname)

# write the new theGraph: start with EREs
json_out["theGraph"] = { }
erecounter = 0

for newname, oldnames in json_log["ereName"].items():
    # write new ERE entry,
    # leaving out "adjacent" for now
    json_out["theGraph"][newname] = {
        "type" : json_in["theGraph"][oldnames[0]]["type"], 
        "adjacent" : [ ],
        "index" : erecounter
        }
    erecounter += 1


    
# keep a dictionary mapping (subject, predicate, object) triples to new statement names
oldstmt_newstmt = { }
stmtcounter = 0
# mapping from new statement names to lists of old statement names
json_log["stmtName"] = { }

for label, content in json_in["theGraph"].items():
    if content["type"] == "Statement":
        stmt_key = make_stmt_key(content, ereunif)
        if stmt_key in oldstmt_newstmt:
            # we have already created this statement
            newstmt = oldstmt_newstmt[ stmt_key ]
        else:
            # we need to create this statement name
            newstmt = "Stmt" + str(stmtcounter)
            oldstmt_newstmt[ stmt_key ] = newstmt
            stmtcounter += 1

        if newstmt not in json_log["stmtName"]:
            json_log["stmtName"][newstmt] = [ ]
        json_log["stmtName"][newstmt].append(label)

# write new statements for theGraph
stmtcounter = 0
for newname, oldnames  in json_log["stmtName"].items():
    content = json_in["theGraph"][oldnames[0]]
    subj, pred, obj = make_stmt_key(content, ereunif)
    json_out["theGraph"][newname] = {
        "type": "Statement",
        "index": stmtcounter,
        "conf" : content["conf"],
        "subject" : subj,
        "predicate" : content["predicate"], 
        "object" : obj
        }
            
    stmtcounter += 1

# fill in adjacency in the ERE entries

for newname, oldnames in json_log["ereName"].items():
    adjacent = set()
    for oldname in oldnames:
        for oldstmt in json_in["theGraph"][oldname]["adjacent"]:
            newstmt = get_newstmt_label(oldstmt, ereunif, json_in["theGraph"], oldstmt_newstmt)
            if newstmt is None:
                print("error:", oldstmt, "missing in theGraph")
            else:
                adjacent.add(newstmt)
    
    json_out["theGraph"][newname]["adjacent"] = list(adjacent)
    
# write ere list
json_out["ere"] = sorted(json_log["ereName"].keys(), key = lambda e:json_out["theGraph"][e]["index"])

# write statement list
json_out["statements"] = sorted(json_log["stmtName"].keys(), key = lambda s:json_out["theGraph"][s]["index"])

# adapt statement proximity
proximities = { }
# new statement proximity: maximum of proximities of old statements
for stmt1, prox1 in json_in["statementProximity"].items():
    newstmt1 = get_newstmt_label(stmt1, ereunif, json_in["theGraph"], oldstmt_newstmt)
    if newstmt1 is None:
        continue
    if newstmt1 not in proximities:
        proximities[newstmt1] = { }
        
    for stmt2, value in prox1.items():
        newstmt2 = get_newstmt_label(stmt2, ereunif, json_in["theGraph"], oldstmt_newstmt)
        if newstmt2 is None:
            continue
        proximities[newstmt1][newstmt2] = max(value, proximities[newstmt1].get(newstmt2, 0))
    
json_out["statementProximity"] = proximities

###############
# update the query file

json_query_out  = { }
json_query_out["parameters"] = json_query_in["parameters"]
json_query_out["numSamples"]= json_query_in["numSamples"]
json_query_out["memberProb"] = json_query_in["memberProb"]
json_query_out["entrypoints"] = [ ]

for ep in json_query_in["entrypoints"]:
    newep = { }
    newere = set()
    for ere in ep["ere"]:
        newere.add(ereunif.get(ere, ere))

    newep["ere"] = list(newere)

    newstmt = set()
    for stmt in ep["statements"]:
        label = get_newstmt_label(stmt, ereunif, json_in["theGraph"], oldstmt_newstmt)
        if label is not None:
            newstmt.add(label)

    newep["statements"] = list(newstmt)

    newep["queryConstraints"] = [ ]

    for qc in ep["queryConstraints"]:
        subj = ereunif.get(qc[0], qc[0])
        pred = qc[1]
        obj = ereunif.get(qc[2], qc[2])

        newep["queryConstraints"].append([ subj, pred, obj])

    json_query_out["entrypoints"].append(newep)


################
# write output

with open(args.output_coref_log, "w") as fout:
    json.dump(json_log, fout, indent = 1)

with open(args.output_aidagraph, "w") as fout:
    json.dump(json_out, fout, indent = 1)

with open(args.output_aidaquery, "w") as fout:
    json.dump(json_query_out, fout, indent = 1)
