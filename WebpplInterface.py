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
# * compute units for clustering,
# * compute pairwise distances between units
class WpplInterface:
    def __init__(self, mygraph):
        self.mygraph = mygraph
        
        self.json_obj = { }

        # re-encode the graph
        self.json_obj["theGraph"] = self._transform_graph()
        # compute units
        self.units = [ ]
        self.json_obj["units"] = self._compute_units()
        # and pairwise unit distances. we consider maximal distances of 5.
        self.dist = { }
        self.maxdist = 5
        
        self.json_obj["unitDistances"] = self._compute_distances()

    def write(self, io):
        json.dump(self.json_obj, io, indent = 1)

    ###########3
    # functions that are actually doing the work
    
    def _transform_graph(self):
        retv = { }
        
        # we write out statements, events, entities
        for node in self.mygraph.nodes():
            # entities, events: they only have a type
            if "Entity" in node.get("type", shorten = True):
                retv[ node.shortname() ] = { "type" : "Entity" }
            elif "Event" in node.get("type", shorten = True):
                retv[ node.shortname() ] = { "type" : "Event" }
            # statements have a single subj, pred, obj, a maximal confidence level, and possibly mentions
            elif "Statement" in node.get("type", shorten = True):
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

    # compute the units for clustering, return as a list of sets of node names
    # units are groups of statements that share the same mention.
    # for entities and events that only have a single type of KB entry,
    # the type and KB entry statements go into all units that mention the entity/event
    # and do not go into a separate unit.
    def _compute_units(self):
        
        ee_statements, nonunit_statements = self._types_and_kbentries()
        
        mention_stmt = { }
        
        for node in self.mygraph.nodes("Statement"):
            # skip this statement?
            if node.name in nonunit_statements:
                continue
            
            # Whenever there is more than one mention associated with a statement,
            # these are two different mentions justifying a statement.
            # so just list the statement as belonging to both.
            for mention in self.mygraph.mentions_associated_with(node.name):
                if mention not in mention_stmt:
                    mention_stmt[mention] = [ ]
                if node.name not in mention_stmt[mention]:
                    mention_stmt[mention].append(node.name)

        # in units, retain full names of unit members
        # add in typing and kb entry statements as appropriate
        self.units = [ ]
        for unit in mention_stmt.values():
            ## print("Statements")
            ## for stmtlabel in unit: self.mygraph.node_labeled(stmtlabel).prettyprint()
            # determine entities and events mentioned in the unit
            ee = set()
            for stmtlabel in unit:
                n = self.mygraph.node_labeled(stmtlabel)
                for label in n.get("subject"):
                    if label in self.mygraph.node: ee.add(label)
                for label in n.get("object"):
                    if label in self.mygraph.node: ee.add(label)

            new_unit = set(unit)
            for e in ee:
                if e in ee_statements:
                    new_unit.update(ee_statements[e])

            ## print("\n\nadding")
            ## for stmtlabel in new_unit: self.mygraph.node_labeled(stmtlabel).prettyprint()
            ## input()
                    
            self.units.append( list(new_unit))
        
        # in the json object, use short names
        somenode = first(self.mygraph.node.values())
        return list(map(lambda unit: [ somenode.shortlabel(e) for e in unit ], self.units))
        

    # for entities and events: if they have a single type and/or a single KB entry,
    # record all statements that state this type/ KB entry
    def _types_and_kbentries(self):
        # mapping from entity or event name to typing or KB entry statement name
        ee_statements = { }
        # set of statements that should not get their own unit
        nonunit_statements = set()

        for node in self.mygraph.nodes():
            # only consider entity and event nodes
            if "Entity" in node.get("type", shorten = True) or "Event" in node.get("type", shorten = True):

                # type info
                typeobjs = list(self.mygraph.types_of(node.name))
                typelabels = set( o.typelabels.pop() for o in typeobjs)
                # single type label?
                if len(typelabels) == 1:
                    # record typing statements in ee_statements
                    if node.name not in ee_statements: ee_statements[node.name] = set()
                    ee_statements[node.name].update(o.typenode.name for o in typeobjs)
                    # .. and in nonunit_statements
                    nonunit_statements.update(o.typenode.name for o in typeobjs)

                # kb entry info
                kbobjs = list(self.mygraph.kbentries_of(node.name))
                kbentries = set( o.kbentry.pop() for o in kbobjs)
                if len(kbentries) == 1:
                    # record typing statements in ee_statements
                    if node.name not in ee_statements: ee_statements[node.name] = set()
                    ee_statements[node.name].update(o.kbentrynode.name for o in kbobjs)
                    # .. and in nonunit_statements
                    nonunit_statements.update(o.kbentrynode.name for o in kbobjs)
                
        return (ee_statements, nonunit_statements)
                
       
    # compute the distances between units.
    # return as a list of lists,
    # where the first list contains the distances of unit 0 to all other units,
    # the second list contains the distances of unit 1 to all units of index 2 or higher.
    # and so on.
    def _compute_distances(self):
        # get pairwise node distances
        self._compute_node_distances()

        # compute unit distances
        retv = [ ]
        
        for i in range(len(self.json_obj["units"]) - 1):
            retv.append( [ self._unit_distance(i, j) for j in range(i+1, len(self.units)) ] )

        return retv
 

    # compute pairwise distances between graph nodes.
    # only start at statements, and go maximally self.maxdist nodes outward from each statement
    # don't use Floyd-Warshall, it's too slow with this many nodes
    def _compute_node_distances(self):
        # target data structure:
        # (nodename1, nodename2) -> distance
        # where nodename1 is alphabetically before nodename2
        self.dist = { }

        # we only do statement nodes.
        labels = [ k for k, n in self.mygraph.node.items() if "Statement" in n.get("type", shorten = True)]
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
                    if obj == subj: continue
                    self.dist[ self._nodepair(subj, obj)] = min( self.getdist(subj, obj), dist)
                    newfringe.update(self._valid_neighbors(obj, visitlabels))
                fringe = newfringe
                dist += 1
                

    # distance between two units: minimum node distance between them
    def _unit_distance(self, i1, i2):
        return min(self.getdist( label1, label2) for label1 in self.units[i1] for label2 in self.units[i2])
        
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

