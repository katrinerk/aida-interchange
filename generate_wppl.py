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
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')

kb_filename = sys.argv[1]
output_filename = sys.argv[2]


#entrypoints = [{
#    "ere" : ["E780874.00294", "V780874.00065"],
#    # MH-17 is-a Vehicle, kbEntry MH-17, the event is an attack, target-of Conflict-Attack (repeated).
#    "statements" : [ "assertion-3434",  "assertion-3455", "assertion-3459", "assertion-3463", "assertion-3466"],
#    "queryConstraints" : [
#        ["V780874.00065", "Conflict.Attack_Attacker", "?crash_attacker"],
#        ["V780874.00065", "Conflict.Attack_Instrument", "?crash_instrument"],
#        ["V780874.00065", "Conflict.Attack_Place", "?crash_place"]
#    ],
#}]

logging.info('Reading kb from {}...'.format(kb_filename))
g = rdflib.Graph()
result = g.parse(kb_filename, format="ttl")
logging.info('Done.')

logging.info('Building AidaGraph with {} triples...'.format(len(g)))
mygraph = AidaGraph()
mygraph.add_graph(g)
logging.info('Done.')

#wppl_obj = WebpplInterface.WpplInterface(mygraph, entrypoints, simplification_level = 0)
logging.info('Building input aidagraph.json for webppl...')
wppl_obj = WebpplInterface.WpplInterface(mygraph, simplification_level = 0)
logging.info('Done.')


logging.info('Writing output to {}...'.format(output_filename))
outf = open(output_filename, 'w')
wppl_obj.write(outf)
outf.close()
logging.info('Done.')
