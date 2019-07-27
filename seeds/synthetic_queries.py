# Katrin Erk July 2019
# Given a json graph file,
# make n synthetic queries, as follows:
# Select an entity node that has at least k events 
# to which it is connected by the same role.
# Or: Select an event node that has at least k different entities to which it is connected by the same role
#
# usage:
# python3 synthetic_queries.py <graphfilename> <outdir>
#
# graphfilename is a json graph
# outdir is a directory in which query json files will be written, one per generated query
# set numqueries_entities, numqueries_events to change how many queries will be generated

import sys
import json
from collections import deque
import math
import os
import re
import random

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson

#########################
numqueries_entities = 10
numqueries_events = 10
numsteps_for_connectedness = 2

#########################
# read graph file 
graph_filename = sys.argv[1]
outdir = sys.argv[2]

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))

# iterate through all entities or through all events, find all adjacent event roles, collect EREs on the other side.
# keep the entity/the event only if it has at least one role with two different fillers
# because then it is query-able.
def find_eres_with_multiple_eventroles_of_same_kind(ere_iterator, other_ere_function):
    retv = { }
    
    for ere, dummy in ere_iterator():
        for stmt in graph_obj.each_ere_adjacent_stmt_anyrel(ere):
            if graph_obj.is_eventrole_stmt(stmt):
                # this is an event role: record it
                if ere not in retv:
                   retv[ ere] = { }
                # determine role label and event ID
                rolelabel = graph_obj.stmt_predicate(stmt)
                other_ere = other_ere_function(stmt)

                # record
                if rolelabel not in retv[ ere]: retv[ere][rolelabel ] = set()
                retv[ ere][rolelabel].add(other_ere)
                
        # only keep this ere if it has two entries somewhere in the dict
        if ere in retv:
            if not(any(len(other_eres) > 1 for rolelabel, other_eres in retv[ere].items())):
                del retv[ ere ]

    return retv

# to determine entities that are adjacent to multiple different events of the same type
# by the same role, 
# generate mapping entity -> event role -> set of event IDs that this goes to
entity_evrole = find_eres_with_multiple_eventroles_of_same_kind(graph_obj.each_entity, graph_obj.stmt_subject)
# determine events that have multiple possible fillers for the same argument
# mapping event -> event role -> set of entity IDs that fill the role
event_rolefillers = find_eres_with_multiple_eventroles_of_same_kind(graph_obj.each_event, graph_obj.stmt_object)

# for events, only keep the ones that also have roles with only one filler
delete_events = [ ]
for event in event_rolefillers.keys():
    if not(any(len(fillers) == 1 for rolelabel, fillers in event_rolefillers[event].items())):
        delete_events.append(event)
for e in delete_events:
    del event_rolefillers[e]

# keep the top 3 * numqueries_entities entities, and the top 3*numqueries_events events
entity_weight = { }
for e in entity_evrole.keys():
    entity_weight[e] = sum(len(entity_evrole[e][f]) for f in entity_evrole[e].keys() if len(entity_evrole[e].get(f, set())) > 1)

event_weight = { }
for e in event_rolefillers.keys():
    event_weight[e] = sum(len(event_rolefillers[e][f]) for f in event_rolefillers[e].keys() if len(event_rolefillers[e].get(f, set())) > 1)
    
topn_entities = sorted(entity_weight.keys(), key = lambda e:entity_weight[e], reverse = True)[:3 * numqueries_entities]
topn_events = sorted(event_weight.keys(), key = lambda e:event_weight[e], reverse = True)[:3 * numqueries_events]

## print("HIER top n entities")
## for e in topn_entities:
##     print(e, entity_weight[e])
## print("HIER top n events")
## for e in topn_events:
##     print(e, event_weight[e])

## sys.exit(0)

########
# weight each ERE by how many entities there are in its M-step neighborhood for
# M= numsteps_for_connectedness
# helper function: one-step ERE neighbors
def onestep_neighbors(ere):
    retv = set()
    
    for stmt in graph_obj.each_ere_adjacent_stmt_anyrel(ere):
        if graph_obj.stmt_subject(stmt) == ere and graph_obj.is_ere(graph_obj.stmt_object(stmt)):
            retv.add(graph_obj.stmt_object(stmt))
        elif graph_obj.stmt_object(stmt) == ere and graph_obj.is_ere(graph_obj.stmt_subject(stmt)):
            retv.add(graph_obj.stmt_subject(stmt))

    return retv

# return ERE weight
def ere_weight_by_connectedness(ere):
    neighbors = set()
    new_starting_points = [ere]

    for i in range(numsteps_for_connectedness):

        thisstep_starting_points = new_starting_points
        new_starting_points = [ ]
        # invariant: all members of thisstep_starting_points are in neighbors (or are the original ere)
        # neighbors of new_starting_points have not been computed yet

        for startpoint in thisstep_starting_points:
            for endpoint in onestep_neighbors(startpoint):
                if endpoint not in neighbors:
                    neighbors.add(endpoint)
                    new_starting_points.append(endpoint)

        # now give this ERE a weight: connectedness, i.e. number of neighbors
        return len(neighbors)
            

# make entity queries:
# first, weight entities by their connectivity: number of EREs that can be reached in M steps
entity_reweight = dict((e, ere_weight_by_connectedness(e)) for e in topn_entities)
event_reweight = dict((e, ere_weight_by_connectedness(e)) for e in topn_events)

## print("HIER entity reweighting")
## for e in topn_entities:
##     print(e, entity_weight[e], entity_reweight[e])

## print("HIER event reweighting")
## for e in topn_events:
##     print(e, event_weight[e], event_reweight[e])
    
query_entities = sorted(entity_reweight.keys(), key = lambda e: entity_reweight[e], reverse = True)[:numqueries_entities]
query_events = sorted(event_reweight.keys(), key = lambda e: event_reweight[e], reverse = True)[:numqueries_events]

#######3
# write queries for entities
for query_entity in query_entities:
    query_json = { }
    query_json["graph"] = graph_filename

    facet_json = { "ere" : [ query_entity ], "statements" : [ ], "query_constraints" : [ ] }

    # add query constraints
    for eventindex, rolelabel in enumerate(entity_evrole[ query_entity ]):
        if len(entity_evrole[ query_entity ][rolelabel]) > 1:
            # entity is adjacent to event #index via rolelabel
            facet_json["query_constraints"].append( [ "?Event" + str(eventindex), rolelabel, query_entity])
            # other roles for that event
            event = random.choice(list(entity_evrole[ query_entity][rolelabel]))
            roles_done = set([rolelabel])
            for roleindex, stmt in enumerate(graph_obj.each_ere_adjacent_stmt_anyrel(event)):
                if graph_obj.is_eventrole_stmt(stmt) and graph_obj.stmt_predicate(stmt) not in roles_done:
                    facet_json["query_constraints"].append( [ "?Event" + str(eventindex), graph_obj.stmt_predicate(stmt), "?Role" + str(eventindex) + "_" + str(roleindex) ])
                    roles_done.add(graph_obj.stmt_predicate(stmt))
                                      
    
    query_json["facets"] = [ facet_json ]

    with open(os.path.join(outdir, "entity" + query_entity.split("/")[-1] + ".json"), "w") as fout:
        json.dump(query_json, fout, indent = 1)
        
#######3
# write queries for events
for query_event in query_events:
    query_json = { }
    query_json["graph"] = graph_filename

    facet_json = { "statements" : [ ], "query_constraints" : [ ] }

    # select a query entity that is an argument of this event, but not one with multiple choices
    query_rolelabel = random.choice(list(r for r in event_rolefillers[query_event] if len(event_rolefillers[query_event][r]) == 1))
    query_entity = list(event_rolefillers[query_event][query_rolelabel])[0]

    facet_json["ere"] = [query_entity]
    
    # add query constraints:
    # connection from entry point to event
    facet_json["query_constraints"].append( [ "?Event", query_rolelabel, query_entity])
    # ask about all other roles of this event
    for roleindex, rolelabel in enumerate(event_rolefillers[query_event].keys()):
        if rolelabel == query_rolelabel:
            continue
        
        facet_json["query_constraints"].append( [ "?Event", rolelabel, "?Role" + str(roleindex) ])
                                      
    
    query_json["facets"] = [ facet_json ]

    with open(os.path.join(outdir, "event_" + query_event.split("/")[-1] + ".json"), "w") as fout:
        json.dump(query_json, fout, indent = 1)
        
