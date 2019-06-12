# Katrin Erk Summer 2019:
# make human-readable output from a json output file
#
# usage:
#
# python3 make_humanreadable_output.py <hypotheses.json> <graphfile.json> <outdir>
import json
import sys
import os

from optparse import OptionParser

from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)


from aif import AidaJson
from seeds import AidaHypothesis

##########3

usage = "usage: %prog [options] hypotheses_json inputkb_json outdir"
parser = OptionParser(usage)
# maximum number of seeds to store
parser.add_option("-w", "--minweight", action = "store", dest = "minweight", type = "float", default = None, help = "only list hypotheses down to this min weight")
# maximum number of seeds to store
parser.add_option("-n", "--maxnum", action = "store", dest = "maxnum", type = "float", default = None, help = "only list top n hypotheses")


(options, args) = parser.parse_args()

if len(args) != 3:
     parser.print_help()
     sys.exit(1)

hypothesis_filename = args[0]
graph_filename = args[1]
out_dir = args[2]

with open(hypothesis_filename, 'r') as fin:
    hypo_obj = json.load(fin)

with open(graph_filename, 'r') as fin:
    graph_obj = AidaJson(json.load(fin))

for index, hypo in enumerate(hypo_obj["support"]):
    hypo_prob = hypo_obj["probs"][index]

    # are we done? if we are only printing a maximum number of hypotheses or down to a minimum weight,
    # stop when we have reached that
    if options.maxnum is not None and index > options.maxnum:
        break
    if options.minweight is not None and hypo_prob < options.minweight:
        break

    aidahypo_obj = AidaHypothesis(graph_obj, stmts = hypo["statements"], stmt_weights = dict((hypo["statements"][i], hypo["statementWeights"][i]) for i in range(len(hypo["statements"]))))
    
    out_filename = os.path.join(out_dir, "hypothesis" + str(index) + ".txt")
    with open(out_filename, "w") as fout:
        print(aidahypo_obj.to_s(), file = fout)


