# Katrin Erk Oct 7 2018
# resolve all coreferences in an aidagraph.json data
# structure, and write a reduced aidagraph.json data structure
# without coreferring EREs or statements,
# along with a second .json file that details which original EREs/
# statements correspond to which reduced ones
#
# usage:
# python3 coref.py <aidagraph.json> <aidaquery.json>
#
# writes new aidagraph.json, aidaquery.json.
# the previous aida graph and query will be copied to
# original_aidagraph.json and original_aidaquery.json

import json
import random
import sys

class EREUnify:
    def __init__(self):
        self.unifier = { }

    def add(self, ere):
        if ere not in self.unifier:
            self.unifier[ere] = ere
            
    def unify_ere_coref(self, ere, coref):
        ereu = self.get_unifier(ere)
        if ereu != coref:
            # unification needed
            self.unifier[ ere] = coref
            # if any other variable points to 'othervar', make it point to 'unifier'
            for var in self.unifier.keys():
                if self.unifier[var] == ere:
                    self.unifier[var] = coref


    def get_unifier(self, ell):
        return self.unifier.get(ell, ell)

    def all_new_names(self):
        retv = { }
        oldname_newname = { }
        namecount = 0

        for ere, ereu in self.unifier.items():
            if ereu not in oldname_newname:
                oldname_newname[ereu] = "ERE" + str(namecount)
                namecount += 1

                
            retv[ere] = oldname_newname[ereu]

        return retv

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

infilename1 = sys.argv[1]
infilename2 = sys.argv[2]
    
f = open(infilename1)
json_in = json.load(f)
f.close()

f = open(infilename2)
json_query_in = json.load(f)
f.close()


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
outf = open("original_aidagraph.json", "w")
json.dump(json_in, outf, indent = 1)
outf.close()

outf = open("original_aidaquery.json", "w")
json.dump(json_query_in, outf, indent = 1)
outf.close()

    
outf = open("aidacoreflog.json", "w")
json.dump(json_log, outf, indent = 1)
outf.close()

outf = open("aidagraph.json", "w")
json.dump(json_out, outf, indent = 1)
outf.close()

outf = open("aidaquery.json", "w")
json.dump(json_query_out, outf, indent = 1)
outf.close()
