# generate webppl format output in a json file called aidagraph.json
# that describes an AIDA graph, the units for clustering, and baseline values
#  for cluster distances.
#
# usage:
# python3 generate_wppl.py <interchangeformatdir> 

import logging
import sys

import rdflib

from aif import AidaGraph, JsonInterface

logging.basicConfig(
    level=logging.DEBUG, format='%(asctime)s - %(message)s')

kb_filename = sys.argv[1]
output_filename = sys.argv[2]

logging.info('Reading kb from {}...'.format(kb_filename))
g = rdflib.Graph()
result = g.parse(kb_filename, format="ttl")
logging.info('Done.')

logging.info('Building AidaGraph with {} triples...'.format(len(g)))
mygraph = AidaGraph()
mygraph.add_graph(g)
logging.info('Done.')

logging.info('Building input aidagraph.json for webppl...')
wppl_obj = JsonInterface(mygraph, simplification_level=0)
logging.info('Done.')

logging.info('Writing output to {}...'.format(output_filename))
outf = open(output_filename, 'w')
wppl_obj.write(outf)
outf.close()
logging.info('Done.')
