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

indir = sys.argv[1]

mygraph = AnnoExplore.read_ldc_gaia_annotation(indir)
wppl_obj = WebpplInterface.WpplInterface(mygraph)

outf = open("aidagraph.json", "w")
wppl_obj.write(outf)
outf.close()
