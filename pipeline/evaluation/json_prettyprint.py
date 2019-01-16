# Katrin Erk Jan 2019:
# for inclusion with other scripts.
# does prettyprinting of graph nodes from our json format


import sys
import json
import re

###################################

###
# retain only names that are probably English
def english_names(labellist):
    return [label for label in labellist if re.search(r"^[A-Za-z0-9\-,\.\'\"\(\)\? ]+$", label)]

###
# given a label, shorten it for easier reading
def shorten_label(label):
    return label.split("/")[-1]

###
# given an ERE label, return labels of all adjacent statements
# with the given predicate and where erelabel is an argument in the given ererole (subject, object)
def each_ere_adjacent_stmt(erelabel, predicate, ererole, json_obj):
    if erelabel not in json_obj["theGraph"]:
        return

    for stmtlabel in json_obj["theGraph"][erelabel].get("adjacent", []):
        if stmtlabel in json_obj["theGraph"] and \
          json_obj["theGraph"][stmtlabel][ererole] == erelabel and \
          json_obj["theGraph"][stmtlabel]["predicate"] == predicate:
            yield stmtlabel
            
    

###
# return a dictionary that characterizes the given ERE in terms of:
# - ere type (nodetype)
# - names ("name")
# - type statements associated ("typestmt")
# - affiliation in terms of APORA ("affiliation")
def ere_characterization(erelabel, json_obj):
    retv = { }

    if erelabel in json_obj["theGraph"]:
        retv["label"] = erelabel
        retv["nodetype"] = shorten_label(json_obj["theGraph"][erelabel]["type"])
        
        retv["typestmt"] = ", ".join(set(shorten_label(json_obj["theGraph"][stmtlabel]["object"]) \
                                        for stmtlabel in each_ere_adjacent_stmt(erelabel, "type", "subject", json_obj)))

        names = set()
        for stmtlabel in each_ere_adjacent_stmt(erelabel, "type", "subject", json_obj):
            names.update(english_names(json_obj["theGraph"][erelabel].get("name", [])))
                    
        retv["name"] = ", ".join(names)

        affiliations = set() 
        for affiliatestmtlabel in each_ere_adjacent_stmt(erelabel, "GeneralAffiliation.APORA_Affiliate", "object", json_obj):
            relationlabel = json_obj["theGraph"][affiliatestmtlabel]["subject"]
            for affiliationstmtlabel in each_ere_adjacent_stmt(relationlabel, "GeneralAffiliation.APORA_Affiliation", "subject", json_obj):
                affiliationlabel = json_obj["theGraph"][affiliationstmtlabel]["object"]
                affiliations.update(english_names(json_obj["theGraph"][affiliationlabel].get("name", [ ])))

        retv["affiliation"] = ", ".join(affiliations)
    
    return retv

####
def print_ere_characterization(erelabel, json_obj, fout, short=False):
    characterization = ere_characterization(erelabel, json_obj)
    if short:
        print("\t label :", characterization["label"], file = fout)
    else:
        for key in ["label", "nodetype", "name", "typestmt", "affiliation"]:
            if key in characterization and characterization[key] != "":
                print("\t", key, ":", characterization[key], file = fout)
####
# print characterization of a given statement in terms of:
# predicate, subject, object
# subject and object can be strings or ERE characterizations
def print_statement_info(stmtlabel, json_obj, fout):
    if stmtlabel not in json_obj["theGraph"]:
        return

    node = json_obj["theGraph"][stmtlabel]

    print("---", file = fout)
    print("Statement", stmtlabel, file = fout)
    for label in ["subject", "predicate", "object"]:
        if node[label] in json_obj["theGraph"]:
            print(label, ":", file = fout)
            print_ere_characterization(node[label], json_obj, fout, short = (node["predicate"] == "type"))
        else:
            print(label, ":", shorten_label(node[label]), file = fout)
    print("\n", file = fout)

####
# Given a set of statement labels, sort the labels for more human-friendly output:
# group all statements that refer to the same event
def sorted_statements_for_output(stmtset, json_obj):
    # map from event labels to statement that mention them
    event_stmt = { }
    for stmtlabel in stmtset:
        node = json_obj["theGraph"].get(stmtlabel, None)
        if node is None: continue
        for rel in ["subject", "object"]:
            if node[rel] in json_obj["theGraph"] and json_obj["theGraph"][node[rel]].get("type", None) == "Event":
                if node[rel] not in event_stmt:
                    event_stmt[ node[rel]] = set()
                event_stmt[ node[rel] ].add(stmtlabel)

    # put statements in output list in order of events that mention them
    stmts_done = set()
    retv = [ ]
    for stmts in event_stmt.values():
        for stmt in stmts:
            if stmt not in stmts_done:
                stmts_done.add(stmt)
                retv.append(stmt)
                
    # and statements that don't mention events
    for stmt in stmtset:
        if stmt not in stmts_done:
            stmts_done.add(stmt)
            retv.append(stmt)

    return retv
