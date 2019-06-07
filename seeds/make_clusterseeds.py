# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# from a Json variant of a statement of information need
#
# usage:
# python3 make_clusterseeds.py [options] <statement of information need in json format> <input kb in json format> <outfilename/outdir> 
import sys
import json

from optparse import OptionParser

import os
from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson

from clusterseed import ClusterSeeds
from clusterextend import ClusterExpansion

########################################
# helper function for logging
def shortestname(label, graph_obj):
    if label in graph_obj.thegraph and "name" in graph_obj.thegraph[label]:
        names = graph_obj.english_names(graph_obj.thegraph[label]["name"])
        if len(names) > 0:
            return sorted(names, key = lambda s:len(s))[0]
    return None


##
# function that actually does the work
def work(soin_filename, graph_filename = None, graph_dir = None, out_filename = None, maxnumseeds = None, log = False):

    with open(soin_filename, 'r') as fin:
        soin_obj = json.load(fin)

    if graph_filename is None:
        graph_filename = os.path.join(graph_dir, soin_obj.get("graph", None))

        
    if graph_filename is None:
        print("could not determine graph file for SoIN", soin_filename)
        return

    with open(graph_filename, 'r') as fin:
        graph_obj = AidaJson(json.load(fin))

    if out_filename is None:
        out_filename = soin_filename + ".out.json"

    
    ###########
    # create cluster seeds

    clusterseed_obj = ClusterSeeds(graph_obj, soin_obj)

    # and expand on them
    hypothesis_obj = ClusterExpansion(graph_obj, clusterseed_obj.finalize())
    hypothesis_obj.type_completion()

    # write hypotheses out in json format.

    with open(out_filename, "w") as fout:
        json_seeds = hypothesis_obj.to_json()
    
        if maxnumseeds is not None:
            # possibly prune seeds
            json_seeds["probs"] = json_seeds["probs"][:options.maxnumseeds]
            json_seeds["support"] = json_seeds["support"][:options.maxnumseeds]

        # add graph filename
        json_seeds["graph_filename"] = os.path.abspath(graph_filename)
        json.dump(json_seeds, fout, indent = 1)


    if log:
        logfilename = soin_filename + ".log"

        with open(logfilename, "w") as lout:
            
            json_struct = hypothesis_obj.to_json()
            print("Number of hypotheses:", len(json_struct["support"]), file = lout)
            print("Number of hypotheses without failed queries:", len([h for h in json_struct["support"] if len(h["failedQueries"]) == 0]), file = lout)

            for hyp in hypothesis_obj.hypotheses()[:10]:
                print("hypothesis log wt", hyp.lweight, file = lout)
                for qvar, filler in sorted(hyp.qvar_filler.items()):
                    name = shortestname(filler, graph_obj)
                    if name is not None:
                        print(qvar, ":", filler, name, file = lout)
                    else:
                        print(qvar, ":", filler, file = lout)
                        
                # print("\n\n", hyp.to_s(), file = lout)

                print("\n", file = lout)
                 
########################################
########################################


###########
# read data

usage = "usage: %prog [options] soin_json inputkb_json outname"
parser = OptionParser(usage)
# maximum number of seeds to store
parser.add_option("-n", "--maxseeds", action = "store", dest = "maxnumseeds", type = "int", default = None, help = "only list up to n cluster seeds")
# directories instead of files
parser.add_option("-d", "--dirs", action = "store_true", dest = "isdir", default = False, help = "soin, graph, output are directories rather than files")

(options, args) = parser.parse_args()

if len(args) != 3:
     parser.print_help()
     sys.exit(1)

soin_name = args[0]
graph_name = args[1]
out_name = args[2]

if options.isdir:
    # work on all SoINs in given directory
    for entry in os.listdir(soin_name):
        soin_filename = os.path.join(soin_name, entry)
        if os.path.isfile(soin_filename) and soin_filename.endswith(".json"):
            # this is one of the files to process.
            print("SoIN", entry)
            out_filename = os.path.join(out_name, "seeds_" + entry)
            work(soin_filename, graph_dir = graph_name, out_filename= out_filename, maxnumseeds = options.maxnumseeds, log = True)
else:
    # work on a single query
    print("SoIN", soin_name)
    work(soin_name, graph_filename = graph_name, out_filename = out_name, maxnumseeds = options.maxnumseeds, log = True)
