# given a directory with LDC annotation about a single topic, in GAIA interface format,
# and given a directory with the matching original LDC annotation,
# identify all paths that link conflicting hypotheses
# and display them, most frequent last.
#
# usage:
# python3 ldchypotheses.py <interchangeformatdir> <ldcdir>

#######
# integrating LDC hypothesis annotation with the interface-format annotation

import sys
import os
import rdflib
import csv
from first import first
import pickle
from AidaGraph import AidaGraph, AidaNode

#########
# given two relevance labels for the same hypothesis,
# what kinds of labels are contradicting?
def conflicting_evidence(hyprel1, hyprel2):
    for hyp, rel in hyprel1.items():
        if hyp in hyprel2 and conflicting_relevance(rel, hyprel2[hyp]): return True
    return False

def conflicting_relevance(relevance1, relevance2):
    if relevance1 == "contradicts" and relevance2 in ["fully-relevant", "partially-relevant"]: return True
    elif relevance2 == "contradicts" and relevance1 in ["fully-relevant", "partially-relevant"]: return True
    return False


#########
# given a path through the graph,
# map it to a path label under which it can be filed,
# such that we can detect multiple paths that have "the same shape".
# currently, this is very simplistic and does not recognize
# paths that have the same edge labels but go in the opposite direction
# in an undirected graph.
def canonical_pathlabel(path, mygraph):
    pathlabel = ""
    for nobj in path:
        node = mygraph.node_labeled(nobj.neighbornodelabel)
        if node is not None:
            pathlabel += nobj.direction + " " + node.shortlabel(nobj.role) + " " + str(node.get("type", shorten = True)) + " " + str(node.get("predicate", shorten = True)) + " | "
    return pathlabel

#########
# given a directory with LDC annotation for a particular scenario,
# find the hypothesis file and read it into a 
# read LDC hypothesis file, return a dictionary
# that maps from node labels to (hypothesis label to relevance rating)
def read_ldc_hypotheses(ldcdir):
    ldc_filenames = os.listdir(ldcdir)
    ldc_hypothesis_filename = first(iter(ldc_filenames), key = lambda x:x.endswith("hypotheses.tab"), default= None)
    
    if ldc_hypothesis_filename is None:
        return None

    # mapping from mention to hypothesis to relevance setting
    mention_hypothesis = { }

    with open(os.path.join(ldcdir, ldc_hypothesis_filename)) as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        next(reader) # get rid of the header line
        for treenode, hypothesislabel, mention, relevance in reader:
            if relevance != 'n/a':
                if mention not in mention_hypothesis:
                    mention_hypothesis[ mention ] = { }
                mention_hypothesis[ mention ][hypothesislabel] = relevance

    return mention_hypothesis

#########
# given a directory with LDC annotation for a particular scenario,
# read the entity, event, and relation descriptions, and add them to a given AidaGraph.
def read_ldc_descriptions(ldcdir, mygraph, mention_graphnodes):
    ldc_filenames = os.listdir(ldcdir)

    for ere in ["ent", "evt", "rel"]:
        filename = first(iter(ldc_filenames), key = lambda x:x.endswith(ere + "_mentions.tab"), default = None)

        if filename is None:
            print("could not find", ere, "file")


        with open(os.path.join(ldcdir, filename)) as csvfile:
            reader = csv.reader(csvfile, delimiter = '\t')
            next(reader) # header line again
            for row in reader:
                mention_id = row[1]
                type_id = row[2]
                description = row[7]

                # find all graph nodes that go with this mention
                for nodelabel in mention_graphnodes.get(mention_id, []):
                    # and store the description with those graph nodes
                    node = mygraph.node_labeled(nodelabel)
                    if node is not None:
                        node.add_description(description)



#########
# given a directory with GAIA interface format representations of LDC annotation
# for a particular scenario,
# read in all the individual files (but not the .all.ttl) and store them in a joint AidaGraph.
# return the AidaGraph object
def read_ldc_gaia_annotation(indir):
    indircontents = os.listdir(indir)

    mygraph = AidaGraph()

    for filename in indircontents:
        if filename.endswith(".ttl") and not(filename.endswith(".all.ttl")):
            print("adding", filename)
            filepath = os.path.join(indir, filename)
            g = rdflib.Graph()
            result = g.parse(filepath, format = "ttl")
            filenameroot, filenamext = os.path.splitext(filename)
            mygraph.add_graph(g, source = filenameroot)

    return mygraph

#########
# given a graph, note all nodes that have mentions associated with them,
# and make a mapping from mentions to node labels
def detect_mention_graphnodes(mygraph):
    mention_graphnodes = { }
    
    for node in mygraph.nodes():
        for mention in mygraph.mentions_associated_with(node.name):
            if mention not in mention_graphnodes: mention_graphnodes[mention] = set()
            mention_graphnodes[mention].add(node.name)

    return mention_graphnodes

#########
# given an AidaGraph and a dictionary mapping
# node names to hypothesis labels to relevance labels,
# find all paths that link conflicting nodes.
# returns a mapping from conflict path labels to actual paths that
# bear that label
def detect_conflicting_paths(mygraph, mention_hypothesis, mention_graphnodes):
    # record pairs of endnodes we have done before, so we don't report the same path in 2 directions
    # node1label -> node2label set
    ends_done = { }

    # invert mention_graphnodes for easy lookup of mentions for a graph node
    graphnode_mentions = { }
    for m, gs in mention_graphnodes.items():
        for g in gs:
            if g not in graphnode_mentions: graphnode_mentions[g] = set()
            graphnode_mentions[g].add(m)
    
    # record conflict paths:
    # pathlabel -> path
    conflict_path = { }

    for mention, graphnodes in mention_graphnodes.items():
        # we have a mention, and the graph nodes associated with it.
        # if the mention is associated with hypotheses, traverse the graph from all its
        # associated nodes
        if mention in mention_hypothesis:

            for startnodelabel in graphnodes:
                startnode = mygraph.node_labeled(startnodelabel)
                if startnode is None:
                    # this should not happen given how mention_graphnodes was created
                    continue

                # traverse, and find contradicting nodes
                for othernodelabel, path in mygraph.traverse(startnodelabel, omitroles = ["system", "confidence", "privateData", "justifiedBy"]):
                    # if it's the same as the start node, don't pursue this.
                    if othernodelabel == startnodelabel:
                        continue
                    # look up the other node in the LDC hypothesis table: does it have a conflicting view
                    # on some hypothesis?
                    othermentions = graphnode_mentions.get( othernodelabel, set())
                    if any(conflicting_evidence(mention_hypothesis[mention], mention_hypothesis.get(othermention, set())) for othermention in othermentions):
                        # this other node has conflicting evidence with startnode
                        pathlabel = canonical_pathlabel(path, mygraph)

                        if (startnodelabel in ends_done and (pathlabel, othernodelabel) in ends_done[startnodelabel]) or (othernodelabel in ends_done and (pathlabel, startnodelabel) in ends_done[othernodelabel]):
                            # we have seen this path before, in one direction or the other
                            continue

                        # new path, record it
                        if pathlabel not in conflict_path: conflict_path[pathlabel] = [ ]
                        conflict_path[pathlabel].append((startnodelabel, path))

    return conflict_path

#########
# given a mapping from pathlabels to paths,
# where each path links two conflicting nodes,
# print out the information, sorted by frequency of path label,
# most frequent path last.
# for each pathlabel, print one sample path
def print_conflict_paths(conflict_path, mygraph):
    print("Entries by frequency:")
    
    for pathlabel in sorted(conflict_path.keys(), key = lambda p:len(conflict_path[p]), reverse = True):
        print("========================")
        print(pathlabel)
        print("Freq:", len(conflict_path[pathlabel]))
        print("Example:")
        startnodelabel, path = conflict_path[pathlabel][0]
        startnode = mygraph.node_labeled(startnodelabel)
        mygraph.whois(startnodelabel, follow = 3).prettyprint()
        for index, step in enumerate(path):
            node = mygraph.node_labeled(step.neighbornodelabel)
            print("--")
            print(step.direction, node.shortlabel(step.role))
            if index == len(path) - 1:
                mygraph.whois(step.neighbornodelabel, follow = 3).prettyprint(indent = 0)
            else:
                mygraph.whois(step.neighbornodelabel, follow = 0).prettyprint(indent = 1)
            
        input("hit enter")
              

######
# for each given hypothesis, detect all graph nodes that are labeled as pro/con this hypothesis
def determine_pro_and_con_evidence(mygraph, mention_hypothesis, mention_graphnodes):
    # get the set of all hypotheses
    hypotheses = set()
    for hr in mention_hypothesis.values():
        hypotheses.update(hr.keys())

    # hypothesis -> (pro mentions, con mentions)
    procon_evidence = { }

    for hypothesis in hypotheses:
        promentions = [ m for m, hr in mention_hypothesis.items() if hypothesis in hr and hr[hypothesis] in ["fully-relevant", "partially-relevant"]]
        conmentions = [ m for m, hr in mention_hypothesis.items() if hypothesis in hr and hr[hypothesis] == "contradicts"]

        pro = set()
        for m in promentions:
            pro.update(mention_graphnodes.get(m, []))
        con = set()
        for m in conmentions:
            con.update(mention_graphnodes.get(m, []))

        procon_evidence[ hypothesis ] = (pro, con)
        
    return procon_evidence


#####
# print pro and con evidence for each hypothesis
def print_procon_evidence(pro_and_con_evidence, mygraph):
    for hypothesis in pro_and_con_evidence.keys():
        print("====================")
        print("Evidence PRO hypothesis", hypothesis)
        print("====================")
        
        for pro in pro_and_con_evidence[hypothesis][0]:
            obj = mygraph.whois(pro)
            if obj is not None:
                obj.prettyprint()
                print("-----")

        input("please hit enter")

        print("====================")
        print("Evidence CON hypothesis", hypothesis)
        print("====================")
        
        for con in pro_and_con_evidence[hypothesis][1]:
            obj = mygraph.whois(con)
            if obj is not None:
                obj.prettyprint()
                print("-----")

###################


## ## # ldcdir = "/Users/kee252/Documents/Projects/AIDA/data/LDC_scenario1_seedling/ldc_seedling_anno_v3/data/T101"
## ## # indir = "/Users/kee252/Documents/Projects/AIDA/data/LDC_scenario1_seedling/interchangeformat_2018-06-15/T101"

# read in the LDC annotation
indir = sys.argv[1]

mygraph = read_ldc_gaia_annotation(indir)

print("number of nodes:", len(mygraph.node))

# read in the LDC hypothesis info
ldcdir = sys.argv[2]

mention_hypothesis = read_ldc_hypotheses(ldcdir)
if mention_hypothesis is None:
    print("could not find hypothesis file")
    sys.exit(1)

# find out which mentions go with which graph nodes
# because descriptions and hypotheses apply to mentions, not graph nodes
# which stand for types
mention_graphnodes = detect_mention_graphnodes(mygraph)

# read entity, event, and relation descriptions
# and add them into the graph at the matching mentions
read_ldc_descriptions(ldcdir, mygraph, mention_graphnodes)

# for each node that has hypothesis relevance, find paths to other nodes that offer contradicting evidence
conflict_path = detect_conflicting_paths(mygraph, mention_hypothesis, mention_graphnodes)
print("#entries:", len(conflict_path))

## print("writing conflict paths to conflict_paths.pkl")
## outf = open("conflict_paths.pkl", "wb")
## pickle.dump(conflict_path, outf)
## outf.close()

## # print conflict paths
print_conflict_paths(conflict_path, mygraph)

## # for each hypothesis, determine supporting and conflicting evidence
## pro_and_con_evidence = determine_pro_and_con_evidence(mygraph, mention_hypothesis, mention_graphnodes)

## print("writing pro and con evidence to procon_evidence.pkl")
## outf = open("procon_evidence.pkl", "wb")
## pickle.dump(pro_and_con_evidence, outf)
## outf.close()

## # print pro and con evidence for each hypothesis
## print_procon_evidence(pro_and_con_evidence, mygraph)
