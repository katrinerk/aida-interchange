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
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from one_aida_graph_scorer import AidaGraphScorer

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
score_obj = AidaGraphScorer(json_obj)
    
###
# Analyze each model-generated hypothesis

modelhypo_goldhypo, goldhypo_covered, scores, model_stmt_rating = score_obj.score(hypo_obj, hprefix = args.prefix)

for modelhypo_index, modelhypo in enumerate(hypo_obj["support"]):

    # predicted probability and gold mapping for model hypo
    modelhypo_prob = hypo_obj["probs"][modelhypo_index]
    goldhypo = modelhypo_goldhypo[ modelhypo_index]

    if goldhypo is None:
        print("Model hypothesis", modelhypo_index, "had no matching gold hypothesis.", file = sys.stderr)
        continue
    
    # short output to stdout
    print("Model hypothesis", modelhypo_index, "p=", round(modelhypo_prob, 2), ", matched to gold", goldhypo, file = sys.stderr)
    print("Strict Prec:", round(scores["strict_prec"][modelhypo_index], 3), "Rec:", round(scores["strict_rec"][modelhypo_index], 3), file = sys.stderr)
    print("Lenient Prec:", round(scores["lenient_prec"][modelhypo_index], 3), "Rec:", round(scores["lenient_rec"][modelhypo_index], 3), "\n", file = sys.stderr)

    # longer output to file
    outfilebase = args.outdir + "/hypo" + str(modelhypo_index)
    with open(outfilebase + ".txt", "w") as fout:
        print("====================================", file = fout)
        print("Model hypothesis", modelhypo_index, "p=", round(modelhypo_prob, 2), ", matched to gold", goldhypo, file = fout)
        print("------------------------------------", file = fout)
        print("Strict Prec:", round(scores["strict_prec"][modelhypo_index], 3), "Rec:", round(scores["strict_rec"][modelhypo_index], 3), file = fout)
        print("Lenient Prec:", round(scores["lenient_prec"][modelhypo_index], 3), "Rec:", round(scores["lenient_rec"][modelhypo_index], 3), file = fout)
        print("\n", file = fout)

        print("------------------------------------", file = fout)        
        print("Model hypothesis core statements:\n", file = fout)

        for stmtlabel in json_obj.sorted_statements_for_output(model_stmt_rating[modelhypo_index]["core_correct"]):
            json_obj.print_statement_info(stmtlabel, fout, additional = "(correct)")
        for stmtlabel in json_obj.sorted_statements_for_output(model_stmt_rating[modelhypo_index]["core_incorrect"]):
            json_obj.print_statement_info(stmtlabel, fout, additional = "(incorrect)")
            
        print("\n", file = fout)

        print("------------------------------------", file = fout)
        print("Model hypothesis other statements:\n", file = fout)

        for stmtlabel in json_obj.sorted_statements_for_output(model_stmt_rating[modelhypo_index]["other_correct"]):
            json_obj.print_statement_info(stmtlabel, fout, additional = "(correct)")
        for stmtlabel in json_obj.sorted_statements_for_output(model_stmt_rating[modelhypo_index]["other_incorrect"]):
            json_obj.print_statement_info(stmtlabel, fout, additional = "(incorrect)")

        print("\n", file = fout)            


        print("------------------------------------\n", file = fout)
        print("Missing statements from gold hypothesis (strict membership):\n", file = fout)

        for stmtlabel in json_obj.sorted_statements_for_output(model_stmt_rating[modelhypo_index]["missing"]):
            json_obj.print_statement_info(stmtlabel, fout)
        print("\n", file = fout)

    # graphical output of the hypothesis
    json_obj.graphviz(outfilename = outfilebase + ".viz", showview = False, stmt = modelhypo["statements"], unary_stmt=True)


        
print("===========", file = sys.stderr)
print("Macro-average Strict  Prec:", round(sum(scores["strict_prec"].values()) / len(scores["strict_prec"].values()), 3), "Rec:", round(sum(scores["strict_rec"].values()) / len(scores["strict_rec"].values()), 3))
print("Macro-average Lenient Prec:", round(sum(scores["lenient_prec"].values()) / len(scores["lenient_prec"].values()), 3), "Rec:", round(sum(scores["lenient_rec"].values()) / len(scores["lenient_rec"].values()), 3))
print("Coverage in percentage of gold hypotheses:", round(len(goldhypo_covered) / score_obj.num_gold_hypotheses(hprefix = args.prefix), 3))
print("Gold hypotheses covered:", ", ".join(list(goldhypo_covered)))
