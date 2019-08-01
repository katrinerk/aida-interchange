# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# from a Json variant of a statement of information need
#
# usage:
# python3 make_clusterseeds.py [options] <statement of information need in json format> <input kb in json format> <outfilename/outdir>
#
# parameters:
#
# -l, --log: write log. Logs are written to the same directory as the query. Do this for qualitative analysis of the diversity of query responses,
#    but do not use this during evaluation, as it slows down the script.
#
# -n, --maxseeds <arg>: computes *all* seeds, but writes out only the top n. Do use this during evaluation if we get lots of cluster seeds!
#   We will only get evaluated on a limited number of top hypotheses anyway.
#
# -d, --dirs: set this if we have a directory of SoIN files and a directory of graph files.
#   We will probably not need this during evaluatoin as there won't be that many SoIN files
#
# -f, --discard_failed_queries: discards hypotheses that have any failed query constraints. Try not to use this one during evaluation at first,
#   so that we don't discard hypotheses we might still need.
#   If we have too many hypotheses and the script runs too slowly, then use this.
#
# -c, --early_cutoff <arg>: discards hypotheses early, based only on the scores of entry points in Eric's script, keeping
#   only the n best. Try not to use this one during evaluation at first,
#   so that we don't discard hypotheses we might still need.
#   If we have too many hypotheses and the script runs too slowly, then use this.
#
# -r, --rank_cutoff <arg>: discards hypotheses early if there are at least <arg> other hypotheses
#   that coincide with this one in 3 query variable fillers
#   We do need this in the evaluation! Otherwise combinatory explosion happens.
#   I've standard-set this to 100.

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
def work(soin_filename, graph_filename = None, graph_dir = None, out_filename = None, maxnumseeds = None, log = False,
             discard_failedqueries = False, earlycutoff = False, qs_cutoff = None):

    with open(soin_filename, 'r') as fin:
        soin_obj = json.load(fin)

    if graph_filename is None:
        graph_filename = os.path.join(graph_dir, soin_obj.get("graph", None))

        
    if graph_filename is None:
        print("could not determine graph file for SoIN", soin_filename)
        return

    try:
        with open(graph_filename, 'r') as fin:
            graph_obj = AidaJson(json.load(fin))
    except FileNotFoundError:
        print("could not find graph file", graph_filename, "-- skipping")
        return

    if out_filename is None:
        out_filename = soin_filename + ".out.json"

    
    ###########
    # create cluster seeds

    clusterseed_obj = ClusterSeeds(graph_obj, soin_obj, discard_failedqueries = discard_failedqueries, earlycutoff = earlycutoff, qs_cutoff = qs_cutoff)

    # and expand on them
    print("Expansion of seeds")
    hypothesis_obj = ClusterExpansion(graph_obj, clusterseed_obj.finalize())
    hypothesis_obj.type_completion()
    hypothesis_obj.affiliation_completion()

    print("Writing seeds")

    # write hypotheses out in json format.

    with open(out_filename, "w") as fout:
        json_seeds = hypothesis_obj.to_json()
    
        if maxnumseeds is not None:
            # possibly prune seeds
            json_seeds["probs"] = json_seeds["probs"][:options.maxnumseeds]
            json_seeds["support"] = json_seeds["support"][:options.maxnumseeds]

        # add graph filename and queries
        json_seeds["graph"] = os.path.basename(graph_filename)
        json_seeds["queries"] = soin_obj["queries"]
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
# discard hypotheses with failed queries?
parser.add_option("-f", "--discard_failed_queries", action = "store_true", dest = "discard_failedqueries", default = False, help = "discard hypotheses that have failed queries")
# early cutoff: discard queries below the best k based only on entry point scores
parser.add_option("-c", "--early_cutoff", action = "store", dest = "earlycutoff", type = "int", default = None, help = "discard hypotheses below the best n based only on entry point scores")
# write logs?
parser.add_option("-l", "--log", action = "store_true", dest = "log", default = False, help = "write log files to query directory")
# rank-based cutoff
parser.add_option("-r", "--rank_cutoff", action = "store", dest = "qs_cutoff", type = "int", default = 100, help = "discard hypotheses early if there are n others that have the same fillers for 3 of their query variables")


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
            work(soin_filename, graph_dir = graph_name, out_filename= out_filename, maxnumseeds = options.maxnumseeds, log = options.log,
                     discard_failedqueries = options.discard_failedqueries, earlycutoff = options.earlycutoff, qs_cutoff = options.qs_cutoff)
else:
    # work on a single query
    print("SoIN", soin_name)
    work(soin_name, graph_filename = graph_name, out_filename = out_name, maxnumseeds = options.maxnumseeds, log = options.log,
             discard_failedqueries = options.discard_failedqueries, earlycutoff = options.earlycutoff, qs_cutoff = options.qs_cutoff)
