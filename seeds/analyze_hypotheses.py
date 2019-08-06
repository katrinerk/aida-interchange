import sys
import json

import os
import re
import statistics

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from seeds.aidahypothesis import AidaHypothesis, AidaHypothesisCollection

###############33
def neighbor_eres(ere, graph_obj):
    retv = set()
    
    for stmt in graph_obj.each_ere_adjacent_stmt_anyrel(ere):
        if graph_obj.stmt_subject(stmt) != ere and graph_obj.is_ere(graph_obj.stmt_subject(stmt)):
            retv.add(graph_obj.stmt_subject(stmt))
        if graph_obj.stmt_object(stmt) != ere and graph_obj.is_ere(graph_obj.stmt_object(stmt)):
            retv.add(graph_obj.stmt_object(stmt))

    return retv
            

hypothesis_filename = sys.argv[1]
graph_filename = sys.argv[2]

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))

    
with open(hypothesis_filename, 'r') as fin:
    json_hypotheses = json.load(fin)
    hypothesis_collection = AidaHypothesisCollection.from_json(json_hypotheses, graph_obj)

percentage_events_vs_relations = [ ]
percentage_single_arg_events = [ ]
percentage_single_arg_relations = [ ]
numstatements_entity = [ ]
numstatements_core_entity = [ ]
num_onestep_neighbors = [ ]
num_twostep_neighbors = [ ]

for hypothesis in hypothesis_collection.hypotheses:
    numevents = 0
    numrelations = 0
    num_singlearg_events = 0
    num_singlearg_relations = 0
    onestep_neighbors = set()
    twostep_neighbors = set()
    for ere in hypothesis.eres():
        # ###########event
        if graph_obj.is_event(ere):
            numevents += 1
            roles = [ thing for thing in hypothesis.eventrelation_each_argstmt(ere)]
            if len(roles) < 2:
                num_singlearg_events += 1
        # ##########relation
        elif graph_obj.is_relation(ere):
            numrelations += 1
            roles = [ thing for thing in hypothesis.eventrelation_each_argstmt(ere)]
            if len(roles) < 2:
                num_singlearg_relations += 1

        # ############entity
        elif graph_obj.is_entity(ere):
            roles = [ stmt for stmt in graph_obj.each_ere_adjacent_stmt_anyrel(ere) if stmt in hypothesis.stmts and (graph_obj.is_relationrole_stmt(stmt) or graph_obj.is_eventrole_stmt(stmt))]
            numstatements_entity.append(len(roles))

        # any ERE: one-step, two-step neighbor EREs
        this_neighbors = neighbor_eres(ere, graph_obj)
        onestep_neighbors.update(this_neighbors)
        for n in this_neighbors:
            twostep_neighbors.update(neighbor_eres(n, graph_obj))
        
    # core entity
    for ere in hypothesis.core_eres():
        if graph_obj.is_entity(ere):
            roles = [ stmt for stmt in graph_obj.each_ere_adjacent_stmt_anyrel(ere) if stmt in hypothesis.stmts and (graph_obj.is_relationrole_stmt(stmt) or graph_obj.is_eventrole_stmt(stmt))]
            numstatements_core_entity.append(len(roles))

            

    if numevents > 0 or numrelations > 0:
        percentage_events_vs_relations.append(numevents/(numevents + numrelations))
    if numevents > 0:
        percentage_single_arg_events.append(num_singlearg_events/numevents)
    if numrelations > 0:
        percentage_single_arg_relations.append(num_singlearg_relations/numrelations)

    num_onestep_neighbors.append(len(onestep_neighbors))
    num_twostep_neighbors.append(len(twostep_neighbors))

print("============ Hypothesis analysis ===========")
print("All counts are of statements included in the hypothesis.")
print("------ Event and relation analysis ---------")

print("Percentage events vs. relations", round(statistics.mean(percentage_events_vs_relations), 3), "sd", round(statistics.stdev(percentage_events_vs_relations), 3))
print("Of events, percentage one-arg", round(statistics.mean(percentage_single_arg_events), 3), "sd", round(statistics.stdev(percentage_single_arg_events), 3))
print("Of relations, percentage one-arg", round(statistics.mean(percentage_single_arg_relations), 3), "sd", round(statistics.stdev(percentage_single_arg_relations), 3))

print("------ Entity ---------")
print("# role statements per entity", round(statistics.mean(numstatements_entity), 3), "sd", round(statistics.stdev(numstatements_entity), 3))
print("# role statements per core entity", round(statistics.mean(numstatements_core_entity), 3), "sd", round(statistics.stdev(numstatements_core_entity), 3))

print("============ Seed analysis ===========")
print("Graph density analysis:")
print("Neighbor EREs are counted irrespective of whether they are in the hypothesis.")
print("# EREs one step from included entities", round(statistics.mean(num_onestep_neighbors), 3), "sd", round(statistics.stdev(num_onestep_neighbors), 3))
print("# EREs two steps from included entities", round(statistics.mean(num_twostep_neighbors), 3), "sd", round(statistics.stdev(num_twostep_neighbors), 3))

for i, hypothesis in enumerate(hypothesis_collection.hypotheses):
    print("Hyp", i, "#EREs one step/two steps from included entities", num_onestep_neighbors[i], num_twostep_neighbors[i])
    
