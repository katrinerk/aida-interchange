# Finding conflicting statements in LDC AIDA annotation
#

import sys
import os
import rdflib
import csv
from first import first
import pickle
from AidaGraph import AidaGraph, AidaNode
from AnnoExplore import LDCAnno

######################################3
class ConflictingEvidence:
    def __init__(self, mygraph, ldcanno_obj):
        self.mygraph = mygraph
        self.ldcanno_obj = ldcanno_obj

        self.conflict_path = { }
        self.procon_evidence = { }


    #################
    # given an AidaGraph and a dictionary mapping
    # node names to hypothesis labels to relevance labels,
    # find all paths that link conflicting nodes.
    # returns a mapping from conflict path labels to actual paths that
    # bear that label
    def detect_conflicting_paths(self):
        # record pairs of endnodes we have done before, so we don't report the same path in 2 directions
        # node1label -> node2label set
        ends_done = { }

        # invert mention_graphnodes for easy lookup of mentions for a graph node
        graphnode_mentions = { }
        for m, gs in self.ldcanno_obj.mention_graphnodes.items():
            for g in gs:
                if g not in graphnode_mentions: graphnode_mentions[g] = set()
                graphnode_mentions[g].add(m)
    
        # record conflict paths:
        # pathlabel -> path
        self.conflict_path = { }

        for mention, graphnodes in self.ldcanno_obj.mention_graphnodes.items():
            # we have a mention, and the graph nodes associated with it.
            # if the mention is associated with hypotheses, traverse the graph from all its
            # associated nodes
            if mention in self.ldcanno_obj.mention_hypothesis:

                for startnodelabel in graphnodes:
                    startnode = self.mygraph.node_labeled(startnodelabel)
                    if startnode is None:
                        # this should not happen given how mention_graphnodes was created
                        continue

                    # traverse, and find contradicting nodes
                    for othernodelabel, path in self.mygraph.traverse(startnodelabel, omitroles = ["system", "confidence", "privateData", "justifiedBy"]):
                        # if it's the same as the start node, don't pursue this.
                        if othernodelabel == startnodelabel:
                            continue
                        # look up the other node in the LDC hypothesis table: does it have a conflicting view
                        # on some hypothesis?
                        othermentions = graphnode_mentions.get( othernodelabel, set())
                        if any(self._conflicting_evidence(self.ldcanno_obj.mention_hypothesis[mention], self.ldcanno_obj.mention_hypothesis.get(othermention, set()))
                                   for othermention in othermentions):
                            # this other node has conflicting evidence with startnode
                            pathlabel = self._canonical_pathlabel(path)

                            if (startnodelabel in ends_done and (pathlabel, othernodelabel) in ends_done[startnodelabel]) or \
                              (othernodelabel in ends_done and (pathlabel, startnodelabel) in ends_done[othernodelabel]):
                                # we have seen this path before, in one direction or the other
                                continue

                            # new path, record it
                            if pathlabel not in self.conflict_path: self.conflict_path[pathlabel] = [ ]
                            self.conflict_path[pathlabel].append((startnodelabel, path))

        return self.conflict_path

    # for each hypothesis, detect all graph nodes that are labeled as pro/con this hypothesis
    def detect_pro_and_con_evidence(self):
        # get the set of all hypotheses
        hypotheses = set()
        for hr in self.ldcanno_obj.mention_hypothesis.values():
            hypotheses.update(hr.keys())

        # hypothesis -> (pro mentions, con mentions)
        self.procon_evidence = { }

        for hypothesis in hypotheses:
            promentions = [ m for m, hr in self.ldcanno_obj.mention_hypothesis.items() if hypothesis in hr and hr[hypothesis] in ["fully-relevant", "partially-relevant"]]
            conmentions = [ m for m, hr in self.ldcanno_obj.mention_hypothesis.items() if hypothesis in hr and hr[hypothesis] == "contradicts"]

            pro = set()
            for m in promentions:
                pro.update(self.ldcanno_obj.mention_graphnodes.get(m, []))
            con = set()
            for m in conmentions:
                con.update(self.ldcanno_obj.mention_graphnodes.get(m, []))

            self.procon_evidence[ hypothesis ] = (pro, con)

        return self.procon_evidence

    
    #########
    # given a mapping from pathlabels to paths,
    # where each path links two conflicting nodes,
    # print out the information, sorted by frequency of path label,
    # most frequent path last.
    # for each pathlabel, print one sample path
    def print_conflict_paths(self):
        print("Entries by frequency:")

        for pathlabel in sorted(self.conflict_path.keys(), key = lambda p:len(self.conflict_path[p]), reverse = True):
            print("========================")
            print(pathlabel)
            print("Freq:", len(self.conflict_path[pathlabel]))
            print("Example:")
            startnodelabel, path = self.conflict_path[pathlabel][0]
            startnode = self.mygraph.node_labeled(startnodelabel)
            self.mygraph.whois(startnodelabel, follow = 3).prettyprint()
            for index, step in enumerate(path):
                node = self.mygraph.node_labeled(step.neighbornodelabel)
                print("--")
                print(step.direction, node.shortlabel(step.role))
                if index == len(path) - 1:
                    self.mygraph.whois(step.neighbornodelabel, follow = 3).prettyprint(indent = 0)
                else:
                    self.mygraph.whois(step.neighbornodelabel, follow = 0).prettyprint(indent = 1)

            input("hit enter")
              

    #####
    # print pro and con evidence for each hypothesis
    def print_procon_evidence(self):
        for hypothesis in self.procon_evidence.keys():
            print("====================")
            print("Evidence PRO hypothesis", hypothesis)
            print("====================")

            for pro in self.procon_evidence[hypothesis][0]:
                obj = self.mygraph.whois(pro)
                if obj is not None:
                    obj.prettyprint()
                    print("-----")

            input("please hit enter")

            print("====================")
            print("Evidence CON hypothesis", hypothesis)
            print("====================")

            for con in self.procon_evidence[hypothesis][1]:
                obj = self.mygraph.whois(con)
                if obj is not None:
                    obj.prettyprint()
                    print("-----")

    

    #########
    # helper functions
    #########
    
    # given two relevance labels for the same hypothesis,
    # what kinds of labels are contradicting?
    def _conflicting_evidence(self, hyprel1, hyprel2):
        for hyp, rel in hyprel1.items():
            if hyp in hyprel2 and self._conflicting_relevance(rel, hyprel2[hyp]): return True
            return False

    def _conflicting_relevance(self, relevance1, relevance2):
        if relevance1 == "contradicts" and relevance2 in ["fully-relevant", "partially-relevant"]: return True
        elif relevance2 == "contradicts" and relevance1 in ["fully-relevant", "partially-relevant"]: return True
        return False

    # given a path through the graph,
    # map it to a path label under which it can be filed,
    # such that we can detect multiple paths that have "the same shape".
    # currently, this is very simplistic and does not recognize
    # paths that have the same edge labels but go in the opposite direction
    # in an undirected graph.
    def _canonical_pathlabel(self, path):
        pathlabel = ""
        
        for nobj in path:
            node = self.mygraph.node_labeled(nobj.neighbornodelabel)
            if node is not None:
                pathlabel += nobj.direction + " " + node.shortlabel(nobj.role) + " " + str(node.get("type", shorten = True)) + " " + str(node.get("predicate", shorten = True)) + " | "
        return pathlabel




