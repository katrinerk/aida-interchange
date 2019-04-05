# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# from a Json variant of a statement of information need
#
# usage:
# python3 make_clusterseeds.py <input kb in json format> <statement of information need in json format> <outfilename>
import sys
import json



from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson

from clusterseed import ClusterSeeds

###########
# read data

graph_filename = sys.argv[1]
soin_filename = sys.argv[2]
outfilename = sys.argv[3]

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))

with open(soin_filename, 'r') as fin:
    soin_obj = json.load(fin)

###########
# create cluster seeds

clusterseed_obj = ClusterSeeds(graph_obj, soin_obj)

# write hypotheses out in json format.

with open(outfilename, "w") as fout:
    json.dump(clusterseed_obj.to_json(), fout, indent = 1)


# write out hypotheses to stdout, to test readable output
for hyp in clusterseed_obj.to_s():
    print("\n\nhypothesis\n")
    print(hyp)
    print("\n\n")
    input("press enter...")
