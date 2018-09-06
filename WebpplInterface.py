################################
# Simple interface between an AidaGraph and Webppl:
# write out the graph as a big JavaScript data structure
# write out units for clustering:
# currently these are Statements that pertain to the same event mention


import sys
import os
import rdflib
import csv
import json
from first import first
from AidaGraph import AidaGraph, AidaNode
import AnnoExplore


###########
# Given an AidaGraph, transform it into input for WebPPL analysis:
# * re-encode the graph,
# * compute pairwise distances between statements
class WpplInterface:
    def __init__(self, mygraph, entrypoints):
        self.mygraph = mygraph
        
        self.json_obj = { }

        # re-encode the graph
        self.json_obj["theGraph"] = self._transform_graph()
        # and pairwise statement distances. we consider maximal distances of 5.
        self.dist = { }
        self.maxdist = 5

        # turn distance into proximity
        self.json_obj["statementProximity"] = self._compute_proximity()

        # complete the entry point information given 
        self.json_obj["entrypoints"] = self._characterize_entrypoints(entrypoints)
        
    def write(self, io):
        json.dump(self.json_obj, io, indent = 1)

    ###################################
    # functions that are actually doing the work

    def _transform_graph(self):
        retv = { }
        
        # we write out statements, events, entities, relations
        for node in self.mygraph.nodes():
            # entities, events: they  have a type. They also have a list of adjacent statement indices to be added later
            if node.is_entity():
                retv[ node.shortname() ] = { "type" : "Entity",
                                             "adjacent" : self._adjacent_statements(node)}
            elif node.is_event():
                retv[ node.shortname() ] = { "type" : "Event",
                                             "adjacent" : self._adjacent_statements(node)}
            elif node.is_relation():
                retv[ node.shortname() ] = { "type" : "Relation",
                                             "adjacent" : self._adjacent_statements(node)}
            # statements have a single subj, pred, obj, a maximal confidence level, and possibly mentions
            elif node.is_statement():
                # type
                retv[ node.shortname() ] = { "type" : "Statement"}

                # predicate, subject, object
                for label in ["predicate", "subject", "object"]:
                    content = node.get(label, shorten = True)
                    if len(content) > 0:
                        retv[node.shortname()][label] = str(content.pop())
                

                # confidence
                conflevels = self.mygraph.confidence_of(node.name)
                if len(conflevels) > 0:
                    retv[ node.shortname()]["conf"] = max(conflevels)

        return retv

    # for an entity, relation, or event, determine all statements that mention it
    def _adjacent_statements(self, node):
        retv = [ ]

        # check all the neighbor nodes for whether they are statements
        for rel, neighbornodelabels in node.inedge.items():
            for neighbornodelabel in neighbornodelabels:

                neighbornode = self._getnode(neighbornodelabel)
                if neighbornode is not None:
                    if neighbornode.is_statement():
                        retv.append(neighbornode.shortname())
                        
        return retv
    

    # compute the proximity between statements.
    # return as a dictionary mapping entry indices to dictionaries other_entry_index:proximity
    # proximities are normalized to sum to 1.
    def _compute_proximity(self):
        # get pairwise node distances
        # in the shape of a dictionary
        # self.dist: node label -> node label -> distance
        self._compute_node_distances()

        # compute unit proximity
        retv = { }
        
        for stmt1 in self.dist.keys():
            # sum of proximities for reachable nodes
            sumprox = sum(self.maxdist - dist for dist in self.dist[stmt1].values())

            # proximity normalized by summed proximities
            if sumprox > 0:
                retv[stmt1] = { }
                for stmt2 in self.dist[stmt1].keys():
                    retv[stmt1][stmt2] = (self.maxdist - self.dist[stmt1][stmt2]) / sumprox

        return retv
 

    # compute pairwise distances between graph nodes.
    # only start at statements, and go maximally self.maxdist nodes outward from each statement
    # don't use Floyd-Warshall, it's too slow with this many nodes
    def _compute_node_distances(self):
        # target data structure:
        # nodename1 -> nodename2 -> distance
        self.dist = { }

        # we only do statement nodes.
        self.statements = [ k for k, n in self.mygraph.node_dict.items() if n.is_statement()]
        # we step through neighbors that are EREs or statements
        visitlabels = set([ k for k, n in self.mygraph.node_dict.items() if n.is_statement() or n.is_ere()])

        # do maxdist steps outwards from each statement node
        for subj in self.statements:
            subjnode = self._getnode(subj)
            if subjnode is None: continue

            subjlabel = subjnode.shortname()
            
            # next round of nodes to visit: neighbors of subj
            fringe = self._valid_neighbors(subjnode, visitlabels)

            dist = 1
            while dist < self.maxdist:
                newfringe = set()
                for obj in fringe:
                    if obj == subj: continue
                    objnode = self._getnode(obj)
                    if objnode is None: continue

                    objlabel = objnode.shortname()
                    
                    if objnode.is_statement():
                        # keep track of distance only if this is a statement node
                        if subjlabel not in self.dist: self.dist[subjlabel] = { }
                        self.dist[subjlabel][objlabel] = min(self.dist[subjlabel].get(objlabel, self.maxdist + 1), dist)
                    
                    newfringe.update(self._valid_neighbors(objnode, visitlabels))
                fringe = newfringe
                dist += 1

                

    # # helper functions for node_distances. called by get_node_distances and _unit_distance
    # def getdist(self, l1, l2):
    #     if l1 == l2:
    #         return 0
    #     elif l1 < l2 and (l1, l2) in self.dist:
    #         return self.dist[ (l1, l2) ]
    #     elif l2 < l1 and (l2, l1) in self.dist:
    #         return self.dist[ (l2, l1) ]
    #     else: return self.unreachabledist

    # # sorted pair of label 1, label 2
    # def _nodepair(self, l1, l2):
    #     return tuple(sorted([l1, l2]))

    # return all node labels that have an incoming or outgoing edge to/from the node with label nodelabel
    def _valid_neighbors(self, node, visitlabels):
        retv = set()
        for nset in node.outedge.values(): retv.update(nset)
        for nset in node.inedge.values(): retv.update(nset)
        return retv.intersection(visitlabels)


    # prepare entry point descriptions to be in the right format for wppl.
    # an entry point is a dictionary with the following entries:
    # - ere: a list of labels of entities, relations, and events
    # - statements: a list of labels of statements
    # - corefacetLabels, corefacetFillers: two lists that together map labels of core facets to their fillers in ERE
    # (don't ask; it's because there is no way to create updated dictionaries in webppl where the key is stored in a variable)
    # - coreconstraints: a list of triples [ corefacetID, AIDAedgelabel, corefacetID] where
    #   statements corresponding to these triples need to be added to the cluster
    # - candidates: a list of statement labels such that these are exactly the statements that have one of the
    #   "ere" entries as one of their arguments. these are candidates for addition to the cluster.
    #
    # at this point we assume that the entry point has been completely filled in except for the "candidates".
    # This function modifies the entry points in place, adding candidates
    # and replacing each statement in "statements" by its ID
    def _characterize_entrypoints(self, entrypoints):
        for entrypoint in entrypoints:

            # fill in candidates            
            candidateset = set()

            # for each ERE in the entry point:
            # its adjacent statements go in the set of candidates
            for nodelabel in entrypoint["ere"]:
                if nodelabel in self.json_obj["theGraph"] and \
                  self.json_obj["theGraph"][nodelabel]["type"] in ["Entity", "Event", "Relation"]:
                    candidateset.update(self.json_obj["theGraph"][nodelabel]["adjacent"])

            # statements that are already part of the entry point don't go into candidates
            candidateset.difference_update(entrypoint["statements"])
            
            entrypoint["candidates"] = list(candidateset)
            
        return entrypoints

    def _getnode(self, nodelabel):
        if nodelabel in self.mygraph.node_dict:
            return self.mygraph.node_dict[nodelabel]
        else: return None
         
