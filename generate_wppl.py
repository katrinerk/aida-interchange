# generate webppl format output in a json file called aidagraph.json
# that describes an AIDA graph, the units for clustering, and baseline values for cluster distances.
#
# usage:
# python3 generate_wppl.py <interchangeformatdir> 


import sys
import os
import rdflib
import csv
from first import first
import pickle
from AidaGraph import AidaGraph, AidaNode
import AnnoExplore
import WebpplInterface

kb_filename = sys.argv[1]


entrypoints = [{
    "ere" : ["E780874.00294", "V780874.00065"],
    # MH-17 is-a Vehicle, kbEntry MH-17, the event is an attack, target-of Conflict-Attack (repeated).
    "statements" : [ "assertion-3434",  "assertion-3455", "assertion-3459", "assertion-3463", "assertion-3466"],
    "corefacetLabels" : ["?crash_target", "?crash_event"],
    "corefacetFillers" : ["E780874.00294","V780874.00065"],
    "coreconstraints" : [
        ["?crash_event", "Conflict_attack_attacker", "?crash_attacker"],
        ["?crash_event", "Conflict_attack_instrument", "?crash_instrument"],
        ["?crash_event", "Conflict_attack_place", "?crash_place"]
    ],
}]

g = rdflib.Graph()
result = g.parse(kb_filename, format="ttl")

mygraph = AidaGraph()
mygraph.add_graph(g)

wppl_obj = WebpplInterface.WpplInterface(mygraph, entrypoints)

outf = open("aidagraph.json", "w")
wppl_obj.write(outf)
outf.close()
