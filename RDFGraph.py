#########
# RDF graph:
# takes as input an rdflib Graph
# generated from an AIDA interchange format file
# (the AIDA interchange format is based on the GAIA proposal)
#
# Transforms the graph into the following format:
# one node for each subject of the rdflib Graph
# an entry for each predicate/object pair associated with this subject
# in the rdflib graph
#
######
# Here is how rdflib reads an AIDA interchange format file:
########
## original:
## <http://darpa.mil/annotations/ldc/assertions/388>
##         a               rdf:Statement ;
##         rdf:object      ldcOnt:GeopoliticalEntity ;
##         rdf:predicate   rdf:type ;
##         rdf:subject     ldc:E781145.00381 ;
##         aif:confidence  [ a                    aif:Confidence ;
##                           aif:confidenceValue  "1.0"^^<http://www.w3.org/2001/XMLSchema#double> ;
##                           aif:system           ldc:LDCModelGenerator
##                         ] ;
##         aif:system      ldc:LDCModelGenerator .


## ldc:E781145.00381  a  aif:Entity ;
##         aif:system  ldc:LDCModelGenerator .

######3
## turned into:
## subj http://darpa.mil/annotations/ldc/assertions/388 
## pred http://www.isi.edu/aida/interchangeOntology#confidence 
## obj ub1bL12C25 

## subj ub1bL12C25 
## pred http://www.isi.edu/aida/interchangeOntology#system 
## obj http://darpa.mil/annotations/ldc/LDCModelGenerator 

## subj ub1bL12C25 
## pred http://www.w3.org/1999/02/22-rdf-syntax-ns#type 
## obj http://www.isi.edu/aida/interchangeOntology#Confidence 

## subj http://darpa.mil/annotations/ldc/E781145.00381 
## pred http://www.isi.edu/aida/interchangeOntology#system 
## obj http://darpa.mil/annotations/ldc/LDCModelGenerator 

## subj ub1bL12C25 
## pred http://www.isi.edu/aida/interchangeOntology#confidenceValue 
## obj 1.0 

## subj http://darpa.mil/annotations/ldc/assertions/388 
## pred http://www.w3.org/1999/02/22-rdf-syntax-ns#subject 
## obj http://darpa.mil/annotations/ldc/E781145.00381 

## subj http://darpa.mil/annotations/ldc/assertions/388 
## pred http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate 
## obj http://www.w3.org/1999/02/22-rdf-syntax-ns#type 

## subj http://darpa.mil/annotations/ldc/E781145.00381 
## pred http://www.w3.org/1999/02/22-rdf-syntax-ns#type 
## obj http://www.isi.edu/aida/interchangeOntology#Entity 
###### and so on.

# so subj and obj are nodes, and pred is an edge label on the edge from subj to obj

import os
import rdflib
import urllib

####
# RDFNode: as we are using a ttl-like notation,
# a RDFNode keeps all triples that share a subject,
# with the subject as the "node name".
# It keeps a dictionary "entry" with all preds as keys and the objects as values.
class RDFNode:

    # initialization: remember the subj, and start an empty dict of pred/obj pairs
    def __init__(self, nodename):
        self.name = nodename
        self.outedge = { }
        self.inedge = { }
        self.source = set()

    def add_source(self, source):
        self.source.add(source)

    # adding a pred/obj pair
    def add(self, pred, obj):
        if pred not in self.outedge: self.outedge[pred] = set()
        self.outedge[pred].add(obj)

    def add_inedge(self, pred, subj):
        if pred not in self.inedge: self.inedge[pred] = set()
        self.inedge[pred].add(subj)

    # shorten any label by removing the URI path and keeping only the last bit
    def shortlabel(self, label):
        urlpieces = urllib.parse.urlsplit(label)
        if urlpieces.fragment == "":
            return os.path.basename(urlpieces.path)
        else:
            return urlpieces.fragment

    # shorten the node name
    def shortname(self):
        return self.shortlabel(self.name)

    # prettyprint: write the node name, and all pred/object pairs, all in short form
    def prettyprint(self, omit = None):
        if len(self.source) > 0:
            print(self.shortname(), "from", ", ".join(self.source))
        else:
            print(self.shortname())
        for pred, obj in self.outedge.items():
            if omit is None or self.shortlabel(pred) not in omit:
                print("\t", self.shortlabel(pred), ":", " ".join(self.shortlabel(o) for o in obj))

    # get: given a pred, return the obj's that go with it
    def get(self, targetpred, shorten = False):
        if targetpred in self.outedge:
            return self._maybe_shorten(self.outedge[targetpred], shorten)
        else:
            for pred in self.outedge.keys():
                if self.shortlabel(pred) == targetpred:
                    return self._maybe_shorten(self.outedge[pred], shorten)
        return set([ ])

    def _maybe_shorten(self, labellist, shorten = False):
        if shorten:
            return set([ self.shortlabel(l) for l in labellist ])
        else: return set(labellist)

##################
class RDFGraph:
    # initialization builds an empty graph
    def __init__(self, nodeclass = RDFNode):
        self.node = { }
        self.nodeclass = nodeclass

    # adding another RDF file to the graph of this object
    def add_graph(self, rdflibgraph, source = None):
        # record the set of nodes that are described in rdflibgraph
        new_nodes = set()
        # for each new node, record all its outgoing edges
        for subj, pred, obj in rdflibgraph:
            if subj not in self.node:
                self.node[subj] = self.nodeclass(subj)
                new_nodes.add(subj)

            self.node[subj].add(pred, obj)
            if source is not None: self.node[subj].add_source(source)

            # record the same edge as incoming edge for the obj
            if obj in self.node:
                self.node[obj].add_inedge(pred, subj)

        # record edges from existing nodes to new nodes
        # as inedges on the new nodes
        for subj in self.node:
            if subj not in new_nodes:
                for pred, obj in self.node[subj].outedge.items():
                    if obj in new_nodes:
                        self.node[obj].add_inedge(pred, subj)


    # printing out the graph in readable form
    def prettyprint(self):
        for entry in self.node:
            print("==============")
            self.node[entry].prettyprint()
                

 
