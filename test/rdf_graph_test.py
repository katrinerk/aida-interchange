##
# a simple test script illustrating what can be done with a RDFGraph object

import sys

import rdflib

from aif import RDFGraph

# this needs to be a .ttl file.
# run this on any .ttl file in the interchange fomrat
infilename = sys.argv[1]

# reading in a graph. important: set the format right, there seem to be lots
# of RDF formats
g = rdflib.Graph()
result = g.parse(infilename, format="ttl")

# length of the graph: 11.
print("graph has %s statements" % len(g))

# what are those 11?
for subj, pred, obj in g:
    print("subj", subj, "\npred", pred, "\nobj", obj, "\n")

input("press enter")
print("\n\n")

# read this into our own format, an AidaGraph
mygraph = RDFGraph()
mygraph.add_graph(g)
mygraph.prettyprint()
