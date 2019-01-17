# Katrin Erk Jan 2019:
# Given a set of generated hypotheses,
# evaluate each one:
#   find the gold hypothesis with greatest overlap, then evaluate
#   the model-generated hypothesis for precision and recall,
#   and show elements that are contradicting or superfluous
#
# usage:
# python3 eval_hypotheses.py <generated hypotheses.json> <thegraph.json> <outdir> [--prefix <relevant hypothesis prefix>]
#
# Output is written to stdout.


import sys
import json
import argparse


from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

from  aif import AidaJson

###################################

parser = argparse.ArgumentParser()
parser.add_argument('hypo_json', help='path to the json file containing system-generated hypotheses')
parser.add_argument('thegraph_json', 
                    help='path to a json file containing the AIDA graph, including gold hypotheses')
parser.add_argument('outdir', help='path to dictionary in which to write detailed human-readable eval')
parser.add_argument('--prefix', '-p',
                    help='string prefix of gold hypothesis names to consider'
                         'default to empty (use all hypotheses)')

args = parser.parse_args()

###
# read the graph and the model-generated hypotheses
with open(args.thegraph_json, 'r') as fin:
    json_obj = AidaJson(json.load(fin))

with open(args.hypo_json, 'r') as fin:
    hypo_obj = json.load(fin)

###
# for each gold hypothesis, determine supporting, partially supporting, contradicting statements
goldhypothesis = { }
for stmtlabel, node in json_obj.each_statement():
    for hyptype in ["hypotheses_supported", "hypotheses_partially_supported", "hypotheses_contradicted"]:
        for hyplabel in node.get(hyptype, [ ]):
            # do we have a hypothesis name prefix?
            # if so, we only keep hypotheses that start with this prefix
            if args.prefix is not None and not(hyplabel.startswith(args.prefix)):
                continue
            
            if hyplabel not in goldhypothesis:
                goldhypothesis[hyplabel] = { }
            if hyptype not in goldhypothesis[hyplabel]:
                goldhypothesis[hyplabel][hyptype] = set()
            goldhypothesis[hyplabel][hyptype].add(stmtlabel)

# clean up the sets: statements that are supporting are not also partially supporting,
# and statements that are (partially) supporting are not contradicting
for hypothesis, entry in goldhypothesis.items():
    entry.get("hypotheses_partially_supported", set()).difference_update(entry.get("hypotheses_supported", set()))
    entry.get("hypotheses_contradicted", set()).difference_update(entry.get("hypotheses_supported", set()))
    entry.get("hypotheses_contradicted", set()).difference_update(entry.get("hypotheses_partially_supported", set()))


###
# for each model hypothesis, find the closest matching gold hypothesis
modelhypo_goldhypo = { }

for modelhypo_index, modelhypo in enumerate(hypo_obj["support"]):
    max_overlap = 0
    max_partial_overlap = 0
    max_goldhypo = None
    
    for goldhypo in goldhypothesis.keys():
        overlap = len(goldhypothesis[goldhypo].get("hypotheses_supported", set()).intersection(modelhypo["statements"]))
        partial_overlap = len(goldhypothesis[goldhypo].get("hypotheses_partially_supported", set()).intersection(modelhypo["statements"]))
        # print("modelhypo", modelhypo_index, "gold", goldhypo, overlap, partial_overlap, \
        #        goldhypothesis[goldhypo]["hypotheses_supported"].intersection(modelhypo["statements"]))

        if overlap > max_overlap or (overlap == max_overlap and partial_overlap > max_partial_overlap):
            max_overlap = overlap
            max_partial_overlap = partial_overlap
            max_goldhypo = goldhypo

    modelhypo_goldhypo[modelhypo_index] = max_goldhypo
    # print("model hypothesis", modelhypo_index, ":", max_goldhypo, "with overlap", max_overlap, "/", max_partial_overlap)

    
###
# Analyze each model-generated hypothesis
strict_preclist = [ ]
strict_reclist = [ ]
lenient_preclist = [ ]
lenient_reclist = [ ]

for modelhypo_index, modelhypo in enumerate(hypo_obj["support"]):
    
    modelhypo_prob = hypo_obj["probs"][modelhypo_index]
    goldhypo = modelhypo_goldhypo[ modelhypo_index ]
    goldhypo_supported = goldhypothesis[goldhypo].get("hypotheses_supported", set())
    lenient_goldhypo_supported = goldhypo_supported.union(goldhypothesis[goldhypo].get("hypotheses_partially_supported", set()))


    # strict precision and recall
    truepos = len(goldhypo_supported.intersection(modelhypo["statements"]))
    strict_prec = truepos / len(modelhypo["statements"])
    strict_rec = truepos / len(goldhypo_supported)
    strict_preclist.append(strict_prec)
    strict_reclist.append(strict_rec)

    # lenient precision and recall
    truepos = len(lenient_goldhypo_supported.intersection(modelhypo["statements"]))
    lenient_prec = truepos / len(modelhypo["statements"])
    lenient_rec = truepos / len(lenient_goldhypo_supported)
    lenient_preclist.append(strict_prec)
    lenient_reclist.append(strict_rec)

    # short output to stdout
    print("Model hypothesis", modelhypo_index, "p=", round(modelhypo_prob, 2), ", matched to gold", goldhypo, file = sys.stderr)
    print("Strict Prec:", round(strict_prec, 3), "Rec:", round(strict_rec, 3), file = sys.stderr)
    print("Lenient Prec:", round(lenient_prec, 3), "Rec:", round(lenient_rec, 3), "\n", file = sys.stderr)

    # longer output to file
    outfilebase = args.outdir + "/hypo" + str(modelhypo_index)
    with open(outfilebase + ".txt", "w") as fout:
        print("====================================", file = fout)
        print("Model hypothesis", modelhypo_index, "p=", round(modelhypo_prob, 2), ", matched to gold", goldhypo, file = fout)
        print("------------------------------------", file = fout)
        print("Strict Prec:", round(strict_prec, 3), "Rec:", round(strict_rec, 3), file = fout)
        print("Lenient Prec:", round(lenient_prec, 3), "Rec:", round(lenient_rec, 3), file = fout)
        print("\n", file = fout)

        print("------------------------------------", file = fout)        
        print("Model hypothesis details:\n", file = fout)

        for stmtlabel in json_obj.sorted_statements_for_output(modelhypo["statements"]):
            json_obj.print_statement_info(stmtlabel, fout)
        print("\n", file = fout)

        print("------------------------------------", file = fout)
        print("Superfluous statements wrt.strict gold hypothesis membership:\n", file = fout)

        for stmtlabel in json_obj.sorted_statements_for_output(set(modelhypo["statements"]).difference(goldhypo_supported)):
            json_obj.print_statement_info(stmtlabel, fout)
        print("\n", file = fout)            

        print("------------------------------------\n", file = fout)
        print("Missing statements from gold hypothesis (strict membership):\n", file = fout)

        for stmtlabel in json_obj.sorted_statements_for_output(goldhypo_supported.difference(modelhypo["statements"])):
            json_obj.print_statement_info(stmtlabel, fout)
        print("\n", file = fout)

    # graphical output of the hypothesis
    json_obj.graphviz(outfilename = outfilebase + ".viz", showview = False, stmt = modelhypo["statements"], unary_stmt=True)


        
print("===========", file = sys.stderr)
print("Macro-average Strict  Prec:", round(sum(strict_preclist) / len(strict_preclist), 3), "Rec:", round(sum(strict_reclist) / len(strict_reclist), 3))
print("Macro-average Lenient Prec:", round(sum(lenient_preclist) / len(lenient_preclist), 3), "Rec:", round(sum(lenient_reclist) / len(lenient_reclist), 3))

