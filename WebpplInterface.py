################################
# Simple interface between an AidaGraph and Webppl:
# write out the graph as a big JavaScript data structure
# write out units for clustering:
# currently these are Statements that pertain to the same event mention


import sys
import os
import rdflib
import csv
from first import first
import pickle
from AidaGraph import AidaGraph, AidaNode
import AnnoExplore

#####
# given an AidaGraph, write out all of its entities, events, and statements
# into a webppl structure
def wppl_write_graph(mygraph, pipe):
    # start of data structure
    print('var theGraph = {', file = pipe)
    
    # entities
    for node in mygraph.nodes():
        # entities, events: they only have a type
        if "Entity" in node.get("type", shorten = True):
            print("\t\"" + str(node.name) + "\" : { type : \"Entity\" },", file = pipe)
        elif "Event" in node.get("type", shorten = True):
            print("\t\"" + str(node.name) + "\" : { type : \"Event\" },", file = pipe)

        # statements have a single subj, pred, obj, a maximal confidence level, and possibly mentions
        elif "Statement" in node.get("type", shorten = True):
            print("\t\"" + str(node.name) + "\" : {", file = pipe)
            print("\ttype : \"Statement\", ", file = pipe)

            # subj, pred, obj
            for label in ["subject", "predicate", "object"]:
                content = node.get(label, shorten = True)
                if len(content) > 0:
                    print("\t" + label + " :", "\"" + str(content.pop()) + "\",", file = pipe)

            # confidence
            conflevels = mygraph.confidence_of(node.name)
            if len(conflevels) > 0:
                print("\tconf :", max(conflevels), ",", file = pipe)

            # mentions
            mentions = list(mygraph.mentions_associated_with(node.name))
            if len(mentions) > 0:
                print("\tmentionID : [", ",".join("\"" + str(m) + "\"" for m in mentions), "],", file = pipe)

            # done
            print("\t},", file = pipe)

    # all done
    print("}", file = pipe)

                    
            

###########
# Given an AidaGraph, compute and manage units for clustering
class WpplUnits:
    def __init__(self, mygraph):
        self.mygraph = mygraph

        # units: each unit is a list of statement node names
        self.units = self._compute_units()
        
        # node distances
        self.dist = { }
        self.maxdist = 5

    ####
    # write units in webppl format
    def write_units(self, pipe):
        print("var units = [", file = pipe)
        
        for unit in self.units:
            print("\t[", ",".join("\"" + str(n) + "\"" for n in unit), "],", file = pipe)

        print("]", file = pipe)

    ####
    # write unit distances in webppl format:
    # list of lists, where the first list contains the distances of unit 0 to all other units,
    # the second list contains the distances of unit 1 to all units of index 2 or higher.
    # and so on.
    def write_unit_distances(self, pipe):
        # get pairwise node distances
        self.compute_node_distances()

        # write out unit distances
        print("var dpDistances = [", file = pipe)

        for i in range(len(self.units) - 1):
            print("\t[", file = pipe)
            print("\t", ", ".join( str(self._unit_distance(i, j)) for j in range(i+1, len(self.units))), file = pipe)
            print("\t],", file = pipe)

        print("]", file = pipe)
            

    ######3
    # compute the units for clustering, return as a list of sets of node names
    # currently, units are groups of statements that share the same mention
    def _compute_units(self):
        mention_stmt = { }
        
        for node in self.mygraph.nodes("Statement"):
            # Whenever there is more than one mention associated with a statement,
            # these are two different mentions justifying a statement.
            # so just list the statement as belonging to both.
            for mention in self.mygraph.mentions_associated_with(node.name):
                if mention not in mention_stmt: mention_stmt[mention] = set()
                mention_stmt[mention].add(node.name)

        return list(mention_stmt.values())
        


    ########3
    # distance between two units: minimum node distance between them
    def _unit_distance(self, i1, i2):
        return min(self.getdist( label1, label2) for label1 in self.units[i1] for label2 in self.units[i2])
        
    # distance: compute pairwise distances between graph nodes.
    # only start at statements, and go maximally self.maxdist nodes outward from each statement
    # don't use Floyd-Warshall, it's too slow with this many nodes
    def compute_node_distances(self):
        # target data structure:
        # (nodename1, nodename2) -> distance
        # where nodename1 is alphabetically before nodename2
        self.dist = { }

        # we only do statement nodes.
        labels = [ k for k, n in self.mygraph.node.items() if "Statement" in n.get("type", shorten = True)]
        print("Statement nodes:", len(labels))
        # we step through neighbors that are event or entities too
        visitlabels = set([ k for k, n in self.mygraph.node.items() if len(n.get("type", shorten=True).intersection({"Statement", "Event", "Entity"})) > 0])

        # do maxdist steps outwards from each statement node
        for subj in labels:
            # next round of nodes to visit: neighbors of subj
            fringe = self._valid_neighbors(subj, visitlabels)

            dist = 1
            while dist < self.maxdist:
                newfringe = set()
                for obj in fringe:
                    self.dist[ self._nodepair(subj, obj)] = min( self.getdist(subj, obj), dist)
                    newfringe.update(self._valid_neighbors(obj, visitlabels))
                fringe = newfringe
                dist += 1

    # helper functions for node_distances
    def getdist(self, l1, l2):
        if l1 == l2:
            return 0
        elif l1 < l2 and (l1, l2) in self.dist:
            return self.dist[ (l1, l2) ]
        elif l2 < l1 and (l2, l1) in self.dist:
            return self.dist[ (l2, l1) ]
        else: return 10 * self.maxdist

    def _nodepair(self, l1, l2):
        return tuple(sorted([l1, l2]))

    def _valid_neighbors(self, nodelabel, visitlabels):
        retv = set()
        for nset in self.mygraph.node[nodelabel].outedge.values(): retv.update(nset)
        for nset in self.mygraph.node[nodelabel].inedge.values(): retv.update(nset)
        return retv.intersection(visitlabels)
    
    

    ## # distance: compute pairwise distances between graph nodes.
    ## # Floyd-Warshall algorithm
    ## def compute_node_distances(self):
    ##     # target data structure:
    ##     # (nodename1, nodename2) -> distance
    ##     # where nodename1 is alphabetically before nodename2
    ##     self.dist = { }

    ##     # we only do event, entity, and statement nodes.
    ##     labels = [ k for k, n in self.node.items() if len(n.get("type", shorten = True).intersection(["Statement", "Event", "Entity"])) > 0 ]
        
    ##     # initialize by neighbor distances of 1.
    ##     # (initialization of self-distance to zero is automatic with getdist
    ##     for subj in labels:
    ##         for objs in self.node[subj].outedge.values():
    ##             for obj in objs:
    ##                 if obj in labels:
    ##                     self.dist[ self._nodepair(subj, obj)]= 1

    ##     # main loop
    ##     for i in range(len(labels)):
    ##         for j in range(len(labels)):
    ##             for k in range(len(labels)):
    ##                 if self.getdist(labels[i], labels[j]) > self.getdist(labels[i], labels[k]) + self.getdist(labels[k], labels[j]):
    ##                     self.dist[ self._nodepair( labels[i], labels[j]) ] = self.getdist(labels[i], labels[k]) + self.getdist(labels[k], labels[j])

    ## # helper functions for node_distances
    ## def getdist(self, l1, l2):
    ##     if l1 == l2:
    ##         return 0
    ##     elif l1 < l2 and (l1, l2) in self.dist:
    ##         return self.dist[ (l1, l2) ]
    ##     elif l2 < l1 and (l2, l1) in self.dist:
    ##         return self.dist[ (l2, l1) ]
    ##     else: return float("inf")

    ## def _nodepair(self, l1, l2):
    ##     return tuple(sorted([l1, l2]))
    
    
