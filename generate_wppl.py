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
    "queryConstraints" : [
        ["V780874.00065", "Conflict.Attack_Attacker", "?crash_attacker"],
        ["V780874.00065", "Conflict.Attack_Instrument", "?crash_instrument"],
        ["V780874.00065", "Conflict.Attack_Place", "?crash_place"]
    ],
}]

g = rdflib.Graph()
result = g.parse(kb_filename, format="ttl")

mygraph = AidaGraph()
mygraph.add_graph(g)

wppl_obj = WebpplInterface.WpplInterface(mygraph, entrypoints, simplification_level = 0)

outf = open("aidagraph.json", "w")
wppl_obj.write(outf)
outf.close()
