# given a directory with LDC annotation about a single topic, in GAIA interface format,
# and given a directory with the matching original LDC annotation,
# identify all paths that link conflicting hypotheses
# and display them, most frequent last.
#
# usage:
# python3 ldchypotheses.py <interchangeformatdir> <ldcdir>

#######
# integrating LDC hypothesis annotation with the interface-format annotation

import sys
import os
import rdflib
import csv
from first import first
import pickle
from AidaGraph import AidaGraph, AidaNode
import AnnoExplore
import WebpplInterface

indir = "shortdir"

outf = open("test.wppl", "w")

mygraph = AnnoExplore.read_ldc_gaia_annotation(indir)

    
WebpplInterface.wppl_write_graph(mygraph, outf)

print("\n\n", file = outf)

unit_obj = WebpplInterface.WpplUnits(mygraph)
unit_obj.write_units(outf)

print("\n\n", file = outf)

unit_obj.write_unit_distances(outf)

outf.close()
