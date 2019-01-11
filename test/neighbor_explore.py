##
# exploring the neighborhood of nodes.
# introducing the "whois" predicate that is written
# to give the info about a node that is most informative to a human
#
# call with a single .ttl file as its argument

import sys

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

import rdflib

from aif import AidaGraph

testfilename = sys.argv[1]

# reading in a graph. important: set the format right, there seem to be lots of RDF formats
g = rdflib.Graph()
result = g.parse(testfilename, format="ttl")

mygraph = AidaGraph()
mygraph.add_graph(g)

# explore neighborhood of entities
input("\nNeighbors of entities, hit enter\n")

for node in mygraph.nodes(targettype="Entity"):
    print("========")
    print("Entity", node.shortname())
    whois_info = mygraph.whois(node.name)
    whois_info.prettyprint()

# explore neighborhood of relations
input("\nNeighbors of relations, hit enter\n")

for node in mygraph.nodes(targettype="Relation"):
    print("========")
    print("Relation", node.shortname())
    whois_info = mygraph.whois(node.name)
    whois_info.prettyprint()

# explore neighborhood of events
input("\nNeighbors of events, hit enter\n")

for node in mygraph.nodes(targettype="Event"):
    print("========")
    print("Event", node.shortname())
    whois_info = mygraph.whois(node.name)
    whois_info.prettyprint()
