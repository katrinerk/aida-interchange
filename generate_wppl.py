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
import MyScratchInterface

indir = sys.argv[1]


entrypoints = [{
    "ere" : ["E779987.00064", "V779987.00022"],
    # MH-17 is-a Vehicle, kbEntry MH-17, the event is an attack, target-of Conflict-Attack, target-of Conflict-Attack
    "statements" : [ "assertion-915",  "relation-718", "assertion-918", "ub6bL329C1", "ub6bL272C1" ],
    "corefacetLabels" : ["?crash_target", "?crash_event"],
    "corefacetFillers" : ["E779987.00064","V779987.00022"],
    "coreconstraints" : [
        ["?crash_event", "Conflict_attack_attacker", "?crash_attacker"],
        ["?crash_event", "Conflict_attack_instrument", "?crash_instrument"],
        ["?crash_event", "Conflict_attack_place", "?crash_place"]
    ],
}]
    
mygraph = AnnoExplore.read_ldc_gaia_annotation(indir)
wppl_obj = MyScratchInterface.WpplInterface(mygraph, entrypoints)

outf = open("aidagraph.json", "w")
wppl_obj.write(outf)
outf.close()
