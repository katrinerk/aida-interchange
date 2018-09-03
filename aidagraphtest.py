##
# a script illustrating different things that can be done with an AIDA graph object.
# call with a single .ttl file as its argument

import rdflib
import sys
from AidaGraph import AidaGraph
from RDFGraph import RDFNode
from itertools import combinations

mygraph = AidaGraph()

for testfilename in sys.argv[1:]:
    # reading in a graph.
    # important: set the format right, there seem to be lots of RDF formats
    g = rdflib.Graph()
    result = g.parse(testfilename, format="ttl")

    mygraph.add_graph(g)

# write out the short names of all ere or statement nodes with their node types
input("\n*** Printing hort names and node types of all ERE / Statement nodes, "
      "hit enter\n")
for node in mygraph.nodes():
    if node.is_ere() or node.is_statement():
        print(node.shortname(), ",".join(node.get("type", shorten=True)))

# write out all nodes
# input("\n*** Printing all nodes (with full info), hit enter\n")
# for node in mygraph.nodes():
#     print("\n--")
#     node.prettyprint(omit = [ ])

# find all type statements for each node
input("\n*** Printing type statements, hit enter\n")
for node in mygraph.nodes():
    node_printed = False
    for type_info in mygraph.types_of(node.name):
        if not node_printed:
            print("node", node.shortname())
            node_printed = True
        print("\t type",
              ",".join(type_info.typelabels),
              "at confidence",
              ",".join(str(c) for c in mygraph.confidence_of(
                  type_info.typenode.name)))

# mentions for statements
input("\n*** Listing mentions associated with statements, hit enter\n")
for node in mygraph.nodes(targettype="Statement"):
    node_printed = False
    for mention in mygraph.mentions_associated_with(node.name):
        if not node_printed:
            print("--")
            node.prettyprint()
            node_printed = True
        print("Mention", mention)

# provenances for statements
input("\n*** Listing provenances associated with statements, hit enter\n")
for node in mygraph.nodes(targettype="Statement"):
    node_printed = False
    for provenance in mygraph.provenances_associated_with(node.name):
        if not node_printed:
            print("--")
            node.prettyprint()
            node_printed = True
        print("Provenance", provenance)

# hypotheses supported by statements
input("\n*** Listing hypotheses supported by statements, hit enter\n")
for node in mygraph.nodes(targettype="Statement"):
    node_printed = False
    for hypothesis in mygraph.hypotheses_supported(node.name):
        if not node_printed:
            print("--")
            node.prettyprint()
            node_printed = True
        print("Supports", hypothesis)

# hypotheses partially supported by statements
input("\n*** Listing hypotheses partially supported by statements, hit enter\n")
for node in mygraph.nodes(targettype="Statement"):
    node_printed = False
    for hypothesis in mygraph.hypotheses_partially_supported(node.name):
        if not node_printed:
            print("--")
            node.prettyprint()
            node_printed = True
        print("Partially supports", hypothesis)

# hypotheses contradicted by statements
input("\n*** Listing hypotheses contradicted by statements, hit enter\n")
for node in mygraph.nodes(targettype="Statement"):
    node_printed = False
    for hypothesis in mygraph.hypotheses_contradicted(node.name):
        if not node_printed:
            print("--")
            node.prettyprint()
            node_printed = True
        print("Contradicts", hypothesis)

# hypotheses conflicting between statements
input("\n*** Listing hypotheses conflicting between statements, hit enter\n")
for node_1, node_2 in combinations(mygraph.nodes(targettype="Statement"), r=2):
    node_printed = False
    for hypothesis in mygraph.conflicting_hypotheses(node_1.name, node_2.name):
        if not node_printed:
            print("--")
            node_1.prettyprint()
            node_2.prettyprint()
            node_printed = True
        print("Conflicted by", hypothesis)

# find all nodes that are neighbors of a particular entity
input("\n*** Printing neighbors of each entity, hit enter\n")
for node in mygraph.nodes(targettype="Entity"):
    print("----")
    node.prettyprint()

    # print neighbors
    for neighbor_info in mygraph.neighbors_of(node.name):
        if RDFNode.shortlabel(neighbor_info.role) in ["type", "system", "hasName"]:
            continue
        print("neighbor", neighbor_info.direction,
              RDFNode.shortlabel(neighbor_info.role))
        neighbor_node = mygraph.get_node(neighbor_info.neighbornodelabel)
        if neighbor_node:
            neighbor_node.prettyprint()

# find all nodes that are neighbors of a particular relation
input("\n*** Printing neighbors of each relation, hit enter\n")
for node in mygraph.nodes(targettype="Relation"):
    print("----")
    node.prettyprint()

    # print neighbors
    for neighbor_info in mygraph.neighbors_of(node.name):
        if RDFNode.shortlabel(neighbor_info.role) in ["type", "system"]:
            continue
        print("neighbor", neighbor_info.direction,
              RDFNode.shortlabel(neighbor_info.role))
        neighbor_node = mygraph.get_node(neighbor_info.neighbornodelabel)
        if neighbor_node:
            neighbor_node.prettyprint()

# find all nodes that are neighbors of a particular event
input("\n*** Printing neighbors of each event, hit enter\n")
for node in mygraph.nodes(targettype="Event"):
    print("----")
    node.prettyprint()

    # print neighbors 
    for neighbor_info in mygraph.neighbors_of(node.name):
        if RDFNode.shortlabel(neighbor_info.role) in ["type", "system"]:
            continue
        print("neighbor", neighbor_info.direction,
              RDFNode.shortlabel(neighbor_info.role))
        neighbor_node = mygraph.get_node(neighbor_info.neighbornodelabel)
        if neighbor_node:
            neighbor_node.prettyprint()

# grab a random entity, traverse the graph from there
input("\nTraversing the graph from a random node, hit enter\n")

entity_node = list(mygraph.nodes(targettype="Entity"))[0]
print("Entity is", entity_node.shortname())

for nodelabel, path in mygraph.traverse(entity_node.name):
    # print the label of the  start node
    pathlabel = entity_node.shortname() + " | "
    for n_info in path:
        node = mygraph.get_node(n_info.neighbornodelabel)
        if node is not None:
            # print role and direction, and the label of the neighbor node
            pathlabel += str(n_info)
            # print type of the neighbor node
            type_str = ",".join(node.get("type", shorten=True))
            if type_str:
                pathlabel += " " + type_str
            # print predicate of the neighbor node
            predicate_str = ",".join(node.get("predicate", shorten=True))
            if predicate_str:
                pathlabel += " " + predicate_str
            # print separator
            pathlabel += " | "
    print(pathlabel)
