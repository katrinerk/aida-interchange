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
from clusterextend import ClusterExpansion

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

# and expand on them
hypothesis_obj = ClusterExpansion(graph_obj, clusterseed_obj.finalize())
hypothesis_obj.type_completion()

# write hypotheses out in json format.

with open(outfilename, "w") as fout:
    json.dump(hypothesis_obj.to_json(), fout, indent = 1)


# write out hypotheses to stdout, to test readable output
## for hyp in hypothesis_obj.hypotheses()[:10]:
##     print("\n\nhypothesis\n")
##     print("log weight", hyp.lweight, "\n")
##     print(hyp.to_s())
##     print("\n\n")
##     input("press enter...")

def shortestname(label):
    if label in graph_obj.thegraph and "name" in graph_obj.thegraph[label]:
        names = graph_obj.english_names(graph_obj.thegraph[label]["name"])
        if len(names) > 0:
            return sorted(names, key = lambda s:len(s))[0]
    return None

# analysis of hypotheses
json_struct = hypothesis_obj.to_json()
print("Number of hypotheses:", len(json_struct["support"]))
print("Number of hypotheses without failed queries:", len([h for h in json_struct["support"] if len(h["failedQueries"]) == 0]))

for hyp in hypothesis_obj.hypotheses()[:10]:
    print("hypothesis log wt", hyp.lweight)
    for qvar, filler in sorted(hyp.qvar_filler.items()):
        name = shortestname(filler)
        if name is not None:
            print(qvar, ":", filler, name)
        else:
            print(qvar, ":", filler)
    print("\n")
    input("press enter...")


