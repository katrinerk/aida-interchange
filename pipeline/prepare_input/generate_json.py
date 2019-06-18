# generates a json file called aidagraph.json
# that describes an AIDA graph, the units for clustering, and baseline values
#  for cluster distances.
#
# usage:
# python3 generate_json.py <kbfilename> <jsonfilename> <jsonjustfilename>
#
# where
# kbfilename is the name of an AIF file in .ttl format, or of a directory in which all files are .ttl files.
#     In the latter case, all the files in the directory are combined into a single json file
# jsonfilename is the name of the output file, in json format
# jsonjustfilename is the name of a file in json format listing justifications for all nodes

import logging
import sys
import os

from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

import rdflib

from aif import AidaGraph, JsonInterface


#########################
def work(kb_filename, mygraph):
    logging.info('Reading kb from {}...'.format(kb_filename))
    g = rdflib.Graph()
    result = g.parse(kb_filename, format="ttl")
    logging.info('Done.')

    logging.info('Building AidaGraph with {} triples...'.format(len(g)))
    
    mygraph.add_graph(g)
    logging.info('Done.')


##########################

logging.basicConfig(
    level=logging.DEBUG, format='%(asctime)s - %(message)s')

kb_name = sys.argv[1]
output_filename = sys.argv[2]
output_just_filename = sys.argv[3]

mygraph = AidaGraph()


if os.path.isdir(kb_name):
    for kb_basename in os.listdir(kb_name):
        if kb_basename.endswith(".ttl") or kb_basename.endswith("turtle"):
            kb_filename = os.path.join(kb_name, kb_basename)
            work(kb_filename, mygraph)
else:
    work(kb_name, mygraph)
        

logging.info('Building json representation of the AIF graph...')
json_obj = JsonInterface(mygraph, simplification_level=0)
logging.info('Done.')

logging.info('Writing output to {}...'.format(output_filename))
logging.info('and justifications to {}...'.format(output_just_filename))
outf = open(output_filename, 'w')
json_obj.write(outf)
outf.close()
outf = open(output_just_filename, 'w')
json_obj.write_just(outf)
outf.close()
logging.info('Done.')
