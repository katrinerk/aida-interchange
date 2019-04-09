# Katrin Erk April 2019:
# Evaluate cluster seeds.
# Use the packages in directory seeds/ to generate initial clusters,
# then evaluate their precision and recall against gold hypotheses
# matching each statement of information need
#
# usage:
#  python3 eval_clusterseeds.py <graph_dir> <query_dir>


import sys
import os
import json


from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from seeds import ClusterSeeds, ClusterExpansion, AidaHypothesis
from one_aida_graph_scorer import AidaGraphScorer


###################################


graph_dir = sys.argv[1]
soin_dir = sys.argv[2]

###
# load statements of information, sort by graph file
graph_soin = { }
for entry in os.listdir(soin_dir):
    soin_filename = os.path.join(soin_dir, entry)
    if os.path.isfile(soin_filename) and soin_filename.endswith(".json"):
        # this is one of the files to process.
        print("Reading", entry)
        with open(soin_filename, 'r') as fin:
            soin_obj = json.load(fin)

        # get the matching graph object
        if "graph" not in soin_obj:
            print("Error in", soin_filename, "No graph file given")
            continue

        if soin_obj["graph"] not in graph_soin:
            graph_soin[ soin_obj["graph"] ] = [ ]

        graph_soin[ soin_obj["graph"] ].append((entry, soin_obj))


        
#####
# for each graph filename: evaluate the clusters created for each soin
# that goes with this graph
all_prec = [ ]
all_rec = [ ]
all_lenient_prec = [ ]
all_lenient_rec = [ ]
all_perc_conflicting = [ ]

print("Writing log file log_eval_clusterseed.log")
logf = open("log_eval_clusterseed.log", "w")

for graph_name in graph_soin.keys():

    graph_filename = os.path.join(graph_dir, graph_name)
    if not os.path.isfile(graph_filename):
        print("Error, could not find graph file", graph_filename)
        continue

    with open(graph_filename, 'r') as fin:
        graph_obj = AidaJson(json.load(fin))

    score_obj = AidaGraphScorer(graph_obj)

    # now iterate over statements of information need
    for soin_name, soin_obj in graph_soin[ graph_name]:
        
        # make cluster seeds
        clusterseed_obj = ClusterSeeds(graph_obj, soin_obj)
        hypothesis_obj = ClusterExpansion(graph_obj, clusterseed_obj.finalize())
        hypothesis_obj.type_completion()        

        # obtain the cluster seeds as a json object
        hypo_json = hypothesis_obj.to_json()

        ## # print out hypothesis info, don't evaluate
        ## print(graph_name)
        ## print(", ".join(soin_obj["queries"]))
        ## print(hypo_json)
        ## input("hit enter")
        ## continue
        
        
        # and evaluate
        modelhypo_goldhypo, goldhypo_covered, scores, model_stmt_rating = score_obj.score(hypo_json, hset = soin_obj["queries"])

        # print out evaluation results
        print("===== ", ", ".join(soin_obj["queries"]), "===")
        print("Macro-average Strict Prec:", round(sum(scores["strict_prec"].values()) / len(scores["strict_prec"].values()), 3),
                  "Rec:", round(sum(scores["strict_rec"].values()) / len(scores["strict_rec"].values()), 3))
        print("Macro-average Lenient Prec:", round(sum(scores["lenient_prec"].values()) / len(scores["lenient_prec"].values()), 3), "Rec:", round(sum(scores["lenient_rec"].values()) / len(scores["lenient_rec"].values()), 3))
        print("Coverage in percentage of gold hypotheses:", round(len(goldhypo_covered) / score_obj.num_gold_hypotheses(hset = soin_obj["queries"]), 3))
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
        ##         # print SOIN name, model hypothesis number, gold hypothesis name
        ##         print(soin_name, modelhypo_index, modelhypo_goldhypo.get(modelhypo_index, "--"), file = logf)
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
    
