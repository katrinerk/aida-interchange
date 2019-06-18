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
# python3 coref.py <aidagraph.json> 
# <aidagraph_output.json> <coref_log.json>
#
# writes new aidagraph_output.json

import sys
import json
import random
from argparse import ArgumentParser

from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
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
parser.add_argument('output_aidagraph',
                    help='path to output aidagraph.json file')
parser.add_argument('output_coref_log',
                    help='path to output coref_log.json file')

args = parser.parse_args()

with open(args.input_aidagraph, 'r') as fin:
    json_in = json.load(fin)


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

# each new ERE (cluster of old EREs): make new index,
# assume that all cluster members have the same type.
# form union of content from cluster members
for newname, oldnames in json_log["ereName"].items():
    # write new ERE entry
    json_out["theGraph"][newname] = {
        "index" : erecounter
        }
    # type info
    types = set(json_in["theGraph"][n]["type"] for n in oldnames)
    if len(types) > 1:
        types.remove("Entity")
    if len(types) > 1:
        print("error: multiple types", oldnames, types, file = sys.stderr)
        
    json_out["theGraph"][newname]["type"] = types.pop()
    
    # add additional info from old members of this ERE.
    # all the additional entries have list values.
    additional_info = { }
    for oldname in oldnames:
        for entry, content in json_in["theGraph"][oldname].items():
            if entry == "type" or entry == "index" or entry == "adjacent":
                continue
            if entry not in additional_info:
                additional_info[ entry ] = set()
            additional_info[entry].update(content)

    for entry, content in additional_info.items():
        json_out["theGraph"][newname][entry] = list(content)
        
    erecounter += 1

# Now that EREs have been compressed into ERE coref groups,
# multiple old statements may collapse into a single new statement.
# We can collapse two statements if they have the same predicate,
# their subjects belong to the same ERE group, and
# their objects belong to the same ERE group
    
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

    # source
    sources = set()
    for oldname in oldnames:
        if "source" in json_in["theGraph"][oldname]:
            sources.update(json_in["theGraph"][oldname]["source"])
    if len(sources)> 0:
        json_out["theGraph"][newname]["source"] = list(sources)

    # hypotheses
    for label in ["hypotheses_supported", "hypotheses_partially_supported", "hypotheses_contradicted"]:
        hypotheses = set()
        for oldname in oldnames:
            if label in json_in["theGraph"][oldname]:
                hypotheses.update(json_in["theGraph"][oldname][label])
        if len(hypotheses) > 0:
            json_out["theGraph"][newname][label] = list(hypotheses)
        
            
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

if 'statementProximity' in json_in:
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


################
# write output

with open(args.output_coref_log, "w") as fout:
    json.dump(json_log, fout, indent = 1)

with open(args.output_aidagraph, "w") as fout:
    json.dump(json_out, fout, indent = 1)

