##
# exploring the neighborhood of nodes.
# introducing the "whois" predicate that is written
# to give the info about a node that is most informative to a human
#
# call with a single .ttl file as its argument

import rdflib
import sys
from AidaGraph import AidaGraph, AidaNode

testfilename = sys.argv[1]


# reading in a graph. important: set the format right, there seem to be lots of RDF formats
g = rdflib.Graph()
result = g.parse(testfilename, format = "ttl")

mygraph = AidaGraph()
mygraph.add_graph(g)


###
print("Neighbors of entities")
input("hit enter")


# explore neighborhood of entities
for node in mygraph.nodes(targettype = "Entity"):
    print("========")
    print("Entity", node.shortname())
    whois_obj = mygraph.whois(node.name)
    whois_obj.prettyprint()
    
###
print("Neighbors of events")
input("hit enter")

# explore neighborhood of entities
for node in mygraph.nodes(targettype = "Event"):
    print("========")
    print("Event", node.shortname())
    whois_obj = mygraph.whois(node.name)
    whois_obj.prettyprint()
