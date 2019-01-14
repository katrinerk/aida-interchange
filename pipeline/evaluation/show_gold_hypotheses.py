# Katrin Erk Jan 2019:
# Given AIF with gold hypothesis annotation
# (which EREs support/partially support/contradict a given hypothesis),
# write out all hypotheses in human readable form.


import sys
from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

import rdflib


from aif import AidaGraph, RDFNode, EREUnify

###################################

###
# Input is a .ttl file in AIF format.
# Encode it in an AidaGraph.
infilename = sys.argv[1]

g = rdflib.Graph()
result = g.parse(infilename, format="ttl")
mygraph = AidaGraph()
mygraph.add_graph(g)

###
# we need to record coreference between EREs
# to make the output hypotheses more readable

# map each cluster to its prototype
cluster_prototype = {}

for node in mygraph.nodes(targettype="SameAsCluster"):
    content = node.get("prototype", shorten=False)
    if len(content) > 0:
        # record this node only if it has a prototype as required
        cluster_prototype[node.name] = content.pop()

# record each cluster membership
erecoref_obj = EREUnify()

# record all EREs first
for node in mygraph.nodes():
    if node.is_ere():
        erecoref_obj.add(node.name)


for node in mygraph.nodes(targettype = "ClusterMembership"):
    content = node.get("cluster", shorten=False)
    if len(content) > 0:
        clusterlabel = content.pop()

        content = node.get("clusterMember", shorten=False)
        if len(content) > 0:
            clustermember = content.pop()

            erecoref_obj.unify_ere_coref(clustermember, clusterlabel)
        


## for ere, unifier in erecoref_obj.unifier.items():
##    print(ere, "->", unifier)

   
###
# For each ERE cluster, determine info to print out
erecluster = { }

for plabel in erecoref_obj.get_prototypes():
    erecluster[plabel] = {}
    erecluster[plabel]["nodetype"] = set()
    erecluster[plabel]["typestmt"] = set()
    erecluster[plabel]["name"] = set()
    erecluster[plabel]["affiliation"] = set()
    erecluster[plabel]["members"] = set()

# for all cluster members recorded in the coref object:
# record type, name, and affiliation for this cluster member
# with the prototype
for mlabel in erecoref_obj.get_members():
    plabel = erecoref_obj.get_unifier(mlabel)

    erecluster[plabel]["members"].add(mlabel)
    
    # node types
    mnode = mygraph.get_node(mlabel)
    if mnode is not None:
        erecluster[plabel]["nodetype"].update(mnode.get("type", shorten=True))

    # type statements
    for typeobj in mygraph.types_of(mlabel):
        erecluster[plabel]["typestmt"].update(typeobj.typelabels)

    # hasName entries for this node
    for mname in mygraph.names_of_ere(mlabel):
        erecluster[plabel]["name"].add(mname)


# Event clusters often have a prototype that is characterized as "entity".
# Not doing anything about it just now, just saying.

# Determine affiliation information
# Affiliation info has a complicated shape:
#
# Relation id1
# Statement id2: id1 type ldcOnt:GeneralAffiliation.APORA
# Statement id3: id2 ldcOnt:GeneralAffiliation.APORA_Affiliate id4
# Statement id5: id2 ldcOnt:GeneralAffiliation.APORA_Affiliation id6
# Entity id4
# Entity id6

# mapping from relation to affiliate
rel_affiliate = { }
# mapping from relation to affiliation
rel_affiliation = { }

for node in mygraph.nodes(targettype="Statement"):
    if node.has_predicate("GeneralAffiliation.APORA_Affiliate", shorten=True):
        rellabel = node.get("subject", shorten=False)
        affiliatelabel = node.get("object", shorten = False)
        if len(rellabel) == 1 and len(affiliatelabel) == 1:
            rel_affiliate[ rellabel.pop() ] = affiliatelabel.pop()
            
    elif node.has_predicate("GeneralAffiliation.APORA_Affiliation", shorten= True):
        rellabel = node.get("subject", shorten=False)
        affiliationlabel = node.get("object", shorten = False)
        if len(rellabel) == 1 and len(affiliationlabel) == 1:
            rel_affiliation[ rellabel.pop()] = affiliationlabel.pop()

# and enter cluster prototypes for affiliations into the cluster prototypes for affiliates
for rellabel, affiliatelabel in rel_affiliate.items():
    if rellabel in rel_affiliation:
        affiliationlabel = rel_affiliation[ rellabel]
        
        proto_affiliate = erecoref_obj.get_unifier(affiliatelabel)
        proto_affiliation = erecoref_obj.get_unifier(affiliationlabel)

        erecluster[ proto_affiliate]["affiliation"].add(affiliationlabel)

for plabel in erecluster.keys():
    print("prototype", plabel)
    print("members", erecluster[plabel]["members"])
    print("type", erecluster[plabel]["nodetype"])
    print("typestmt", erecluster[plabel]["typestmt"])
    print("name", erecluster[plabel]["name"])
    print("affiliation", erecluster[plabel]["affiliation"])
    print("\n")

        
        
## # get_clusters() returns a dictionary
## # mapping cluster prototype labels to node labels
## for prototype, members in erecoref_obj.get_clusters().items():
##     # map cluster member labels to cluster member nodes
##     membernodes = [ ]
##     for nname in members:
##         nnode = mygraph.get_node(nname)
##         if nnode is not None: membernodes.append(nnode)

##     # determine ERE type
##     clustertypes = set(n.get( for n in membernodes)

    
    
    


###
# What can be part of a hypothesis? Only statements, or other stuff too?
## types_of_hypothesisparts = set()

## for node in mygraph.nodes():
##     for hypothesis in mygraph.hypotheses_supported(node.name):
##         types_of_hypothesisparts.update(node.get("type", shorten=True))
##     for hypothesis in mygraph.hypotheses_partially_supported(node.name):
##         types_of_hypothesisparts.update(node.get("type", shorten=True))
##     for hypothesis in mygraph.hypotheses_contradicted(node.name):
##         types_of_hypothesisparts.update(node.get("type", shorten=True))
    
## print("types of nodes relevant to hypotheses:\n", types_of_hypothesisparts)
