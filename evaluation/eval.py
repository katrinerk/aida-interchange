# Katrin Erk Jan 2019:
# Given a set of generated hypotheses,
# evaluate each one:
#   find the gold hypothesis with greatest overlap, then evaluate
#   the model-generated hypothesis for precision and recall,
#   and show elements that are contradicting or superfluous
#
# usage:
# python3 eval_hypotheses.py <directory with  hypotheses> <directory with graphs> <outdir> 
#
# Output is written to stdout.


import sys
import json
import argparse
import os


from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from one_aida_graph_scorer import AidaGraphScorer

###################################

parser = argparse.ArgumentParser()
parser.add_argument('hypo_dir', help='directory with json files containing system-generated hypotheses')
parser.add_argument('graph_dir', 
                    help='directory with json files containings AIDA graphs, including gold hypotheses')
parser.add_argument('out_dir', help='path to directory in which to write detailed human-readable eval')

args = parser.parse_args()


#####3
# load  all hypothesis files, sort by graph file
graph_hypo = { }

for entry in os.listdir(args.hypo_dir):
    hypo_filename = os.path.join(args.hypo_dir, entry)
    if os.path.isfile(hypo_filename) and hypo_filename.endswith(".json"):
        
        # this is one of the files to process.
        print("Reading hypotheses in", entry)
        
        with open(hypo_filename, 'r') as fin:
            hypo_obj = json.load(fin)

        # get the matching graph object
        if "graph" not in hypo_obj:
            print("Error in", hypo_filename, "No graph file given")
            continue

        if hypo_obj["graph"] not in graph_hypo:
            graph_hypo[ hypo_obj["graph"] ] = [ ]

        graph_hypo[ hypo_obj["graph"] ].append((entry, hypo_obj))

        
#####
# for each graph filename: evaluate the clusters created for each hypothesis
# that goes with this graph
all_prec = [ ]
all_rec = [ ]
all_lenient_prec = [ ]
all_lenient_rec = [ ]
all_perc_conflicting = [ ]

print("Writing log file log_eval.log")
logf = open("log_eval.log", "w")

for graph_name in graph_hypo.keys():

    graph_filename = os.path.join(args.graph_dir, graph_name)
    if not os.path.isfile(graph_filename):
        print("Error, could not find graph file", graph_filename)
        continue

    with open(graph_filename, 'r') as fin:
        graph_obj = AidaJson(json.load(fin))

    score_obj = AidaGraphScorer(graph_obj)

    # now iterate over hypotheses
    for hypo_name, hypo_json in graph_hypo[ graph_name]:
        
        # evaluate
        modelhypo_goldhypo, goldhypo_covered, scores, model_stmt_rating = score_obj.score(hypo_json, hset = hypo_json["queries"])

        # print out evaluation results
        print("===== ", ", ".join(hypo_json["queries"]), "===")
        print("#hypotheses:", len(hypo_json["support"]))
        print("Macro-average Strict Prec:", round(sum(scores["strict_prec"].values()) / len(scores["strict_prec"].values()), 3),
                  "Rec:", round(sum(scores["strict_rec"].values()) / len(scores["strict_rec"].values()), 3))
        print("Macro-average Lenient Prec:", round(sum(scores["lenient_prec"].values()) / len(scores["lenient_prec"].values()), 3), "Rec:", round(sum(scores["lenient_rec"].values()) / len(scores["lenient_rec"].values()), 3))
        print("Coverage in percentage of gold hypotheses:", round(len(goldhypo_covered) / score_obj.num_gold_hypotheses(hset = hypo_json["queries"]), 3))
        # print("Gold hypotheses covered:", ", ".join(sorted(list(goldhypo_covered))))
        print("Macro-average percentage contradicting statements:", round(sum(scores["perc_conflicting"].values()) / len(scores["perc_conflicting"].values()), 3))
        print("\n")

        all_prec += list(scores["strict_prec"].values())
        all_rec += list(scores["strict_rec"].values())
        all_lenient_prec += list(scores["lenient_prec"].values())
        all_lenient_rec += list(scores["lenient_rec"].values())
        all_perc_conflicting += list(scores["perc_conflicting"].values())

        # log file: conflicting statements included in hypotheses
        ## for modelhypo_index, ratings in model_stmt_rating.items():
        ##     if len(ratings["conflicting"]) > 0:
        ##         print("=============", file = logf)
        ##         # print HYPO name, model hypothesis number, gold hypothesis name
        ##         print(hypo_name, modelhypo_index, modelhypo_goldhypo.get(modelhypo_index, "--"), file = logf)
        ##         # print correct part of model hypothesis
        ##         print("------- correct part of model hypothesis: ------", file = logf)
        ##         correct_obj = AidaHypothesis(graph_obj, ratings["core_correct"] + ratings["other_correct"])
        ##         print(correct_obj.to_s(), file = logf)
        ##         # print conflicting part of model hypothesis
        ##         conflicting_obj = AidaHypothesis(graph_obj, list(ratings["conflicting"]))
        ##         print("------- conflicting: ----", file = logf)
        ##         print(conflicting_obj.to_s(), "\n\n", file = logf)
                
                          
logf.close()

print("==================")
print("Overall:")
print("==================")
print("Macro-average Strict Prec:", round(sum(all_prec) / len(all_prec), 3), "Rec:", round(sum(all_rec) / len(all_rec), 3))
print("Macro-average Lenient Prec:", round(sum(all_lenient_prec) / len(all_lenient_prec), 3),
          "Rec:", round(sum(all_lenient_rec) / len(all_lenient_rec), 3))
print("Macro-average percentrage contradicting statements:", round(sum(all_perc_conflicting)/len(all_perc_conflicting), 3))
    
