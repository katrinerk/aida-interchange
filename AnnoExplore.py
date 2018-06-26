# Read human-readable info on LDC AIDA annotation
# and integrate it with a GAIA graph.
# also, read a whole directory full of LDC annotation in GAIA format
# and record which information came from which file

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
class OneScenarioAnno:
    def __init__(self, scenariodir):
        self.scenariodir = scenariodir

        self.read_ldc_gaia_annotation()

        # given a directory with GAIA interface format representations of LDC annotation
    # for a particular scenario,
    # read in all the individual files (but not the .all.ttl) and store them in a joint AidaGraph.
    # return the AidaGraph object
    def read_ldc_gaia_annotation(self):
        indircontents = os.listdir(self.scenariodir)

        self.mygraph = AidaGraph()
        # mapping from source (filename root) to lists of entities, events, statements that occur in 
        self.source = { }

        for filename in indircontents:
            if filename.endswith(".ttl") and not(filename.endswith(".all.ttl")):
                print("adding", filename)
                filepath = os.path.join(self.scenariodir, filename)
                g = rdflib.Graph()
                result = g.parse(filepath, format = "ttl")
                filenameroot, filenamext = os.path.splitext(filename)

                # add to the AidaGraph
                self.mygraph.add_graph(g)
                # list what was in that source
                self.source[ filenameroot] = self.describe_source(g)

    def describe_source(self, rdflibgraph):
        # these are the labels of node described in this subgraph
        nodelabels = set([ subj for subj, pred, obj in rdflibgraph])

        # find events, entities, other things in this source
        events = [ ]
        entities = [ ]
        statements = [ ]

        for nl in nodelabels:
            node = self.mygraph.node_labeled(nl)
            if "Event" in node.get("type", shorten = True):
                events.append(nl)
            elif "Entity" in node.get("type", shorten = True):
                entities.append(nl)
            elif "Statement" in node.get("type", shorten = True):
                statements.append(nl)
            else:
                # do not record stuff that is not an entity,an event, or a statement for now
                pass

        return { "entities" : entities, "events" : events, "statements" : statements }
        


