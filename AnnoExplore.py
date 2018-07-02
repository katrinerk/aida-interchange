# Read human-readable info on LDC AIDA annotation
# and integrate it with a GAIA graph.

import sys
import os
import rdflib
import csv
from first import first
import pickle
from AidaGraph import AidaGraph, AidaNode

###############################################
# class for integrating LDC annotation with
# GAIA interchange format versions of the annotation.
# In particular we link graph nodes to mentions
# and we read human-readable mention descriptions and hypothesis descriptions
# and add them to the graph or make them available
class LDCAnno:
    def __init__(self, ldcdir, mygraph):
        self.ldcdir = ldcdir
        self.mygraph = mygraph

        self.read_ldc_hypotheses()
        self.detect_mention_graphnodes()
        self.read_ldc_descriptions()
        
    # given a directory with LDC annotation for a particular scenario,
    # find the hypothesis file and read it into a 
    # read LDC hypothesis file, return a dictionary
    # that maps from node labels to (hypothesis label to relevance rating)
    def read_ldc_hypotheses(self):
        ldc_filenames = os.listdir(self.ldcdir)
        ldc_hypothesis_filename = first(iter(ldc_filenames), key = lambda x:x.endswith("hypotheses.tab"), default= None)
    
        # mapping from mention to hypothesis to relevance setting
        self.mention_hypothesis = { }
        
        if ldc_hypothesis_filename is None:
            return 

        with open(os.path.join(self.ldcdir, ldc_hypothesis_filename)) as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            next(reader) # get rid of the header line
            for treenode, hypothesislabel, mention, relevance in reader:
                if relevance != 'n/a':
                    if mention not in self.mention_hypothesis:
                        self.mention_hypothesis[ mention ] = { }
                    self.mention_hypothesis[ mention ][hypothesislabel] = relevance


    # given a graph, note all nodes that have mentions associated with them,
    # and make a mapping from mentions to node labels
    def detect_mention_graphnodes(self):
        self.mention_graphnodes = { }
    
        for node in self.mygraph.nodes():
            for mention in self.mygraph.mentions_associated_with(node.name):
                if mention not in self.mention_graphnodes: self.mention_graphnodes[mention] = set()
                self.mention_graphnodes[mention].add(node.name)

    

    # given a directory with LDC annotation for a particular scenario,
    # read the entity, event, and relation descriptions, and add them to a given AidaGraph.
    def read_ldc_descriptions(self):
        ldc_filenames = os.listdir(self.ldcdir)

        for ere in ["ent", "evt", "rel"]:
            filename = first(iter(ldc_filenames), key = lambda x:x.endswith(ere + "_mentions.tab"), default = None)

            if filename is None:
                print("could not find", ere, "file")
                continue


            with open(os.path.join(self.ldcdir, filename)) as csvfile:
                reader = csv.reader(csvfile, delimiter = '\t')
                next(reader) # header line again

                # iterate over rows in description file
                for row in reader:
                    mention_id = row[1]
                    type_id = row[2]
                    description = row[7]

                    # find all graph nodes that go with this mention
                    for nodelabel in self.mention_graphnodes.get(mention_id, []):
                        # and store the description with those graph nodes
                        node = self.mygraph.node_labeled(nodelabel)
                        if node is not None:
                            node.add_description(description)
    
###############################################
# read in all GAIA-format annotation from a whole scenario,
# and remember which information was in which file
def read_ldc_gaia_annotation(scenariodir):
    indircontents = os.listdir(scenariodir)

    mygraph = AidaGraph()
    
    for filename in indircontents:
        if filename.endswith(".ttl") and not(filename.endswith(".all.ttl")):
            print("adding", filename)
            filepath = os.path.join(scenariodir, filename)
            g = rdflib.Graph()
            result = g.parse(filepath, format = "ttl")

            # add to the AidaGraph
            mygraph.add_graph(g)

    return mygraph

