##
# a script illustrating different things that can be done with an AIDA graph object.
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

# write out the short names of all nodes with their node types
print("short names and node types of all nodes")
input("hit enter")
for node in mygraph.nodes():
    print(node.shortname(), ",".join(node.get("type", shorten = True)))
input("hit enter")
    
# find all confidence levels
print("Printing confidence levels")
input("hit enter")
for node in mygraph.nodes(targettype = "Confidence"):
    print(",".join(str(c) for c in node.confidencelevels()))
input("hit enter")


# find all type statements for each node
print("Printing type statements")
input("hit enter")
for node in mygraph.nodes():
    node_printed = False
    for typeobj in mygraph.types_of(node.name):
        if not node_printed:
            print("node", node.shortname())
            node_printed = True
        print("\t type", ",".join(typeobj.typelabels), "at confidence", ",".join(str(c) for c in typeobj.confidenceValues))
input("hit enter")

# write out all nodes
print("Printing all nodes (with full info)")
input("hit enter")
for node in mygraph.nodes():
    node.prettyprint(omit = [ ])
    print("\n")
input("hit enter")

# mentions for nodes
print("Listing mentions")
input("hit enter")
for node in mygraph.nodes():
    node_printed = False
    for mention in mygraph.mentions_associated_with(node.name):
        if not node_printed:
            print("--")
            node.prettyprint()
            node_printed = True
        print("Mention", mention)


# find all nodes that are neighbors of a particular entity
print("printing neighbors of each entity")
input("hit enter")
for node in mygraph.nodes(targettype = "Entity"):
    node.prettyprint()

    # print neighbors 
    for neighbor_obj in mygraph.neighbors_of(node.name):
        if node.shortlabel(neighbor_obj.role) in ["type", "system"]:
            continue
        print("neighbor", neighbor_obj.direction, node.shortlabel(neighbor_obj.role))
        neighbor_node = mygraph.node_labeled(neighbor_obj.neighbornodelabel)
        if neighbor_node:
            neighbor_node.prettyprint()
    print("----")
input("hit enter")

# find all nodes that are neighbors of a particular event
print("printing neighbors of each event")
input("hit enter")
for node in mygraph.nodes(targettype = "Event"):
    node.prettyprint()

    # print neighbors 
    for neighbor_obj in mygraph.neighbors_of(node.name):
        if node.shortlabel(neighbor_obj.role) in ["type", "system"]:
            continue
        print("neighbor", neighbor_obj.direction, node.shortlabel(neighbor_obj.role))
        neighbor_node = mygraph.node_labeled(neighbor_obj.neighbornodelabel)
        if neighbor_node:
            neighbor_node.prettyprint()
    print("----")
input("hit enter")


# grab a random entity, traverse the graph from there
print("traversing the graph from a random node")
input("hit enter")
entity_node = list(mygraph.nodes(targettype = "Entity"))[0]
print("Entity is", entity_node.shortname())

for nodelabel, path in mygraph.traverse(entity_node.name, omitroles = ["system", "justifiedBy", "confidence", "privateData"]):
    pathlabel = ""
    for nobj in path:
        node = mygraph.node_labeled(nobj.neighbornodelabel)
        if node is not None:
            pathlabel += nobj.direction + " " + entity_node.shortlabel(nobj.role) + " " + ",".join(node.get("type", shorten = True)) + " " + ",".join(node.get("predicate", shorten = True)) + " | "
    print(pathlabel)
