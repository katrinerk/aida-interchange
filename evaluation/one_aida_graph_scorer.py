# Katrin Erk April 2019
# for a given AIDA graph in json format,
# determine all gold hypotheses,
# allow comparison with model hypotheses


class AidaGraphScorer:
    # input: AIDA graph in json format
    def __init__(self, graph_obj):
        self.graph_obj = graph_obj

        self.goldhypothesis = self._record_gold_hypotheses()


    ###
    def num_gold_hypotheses(self, hprefix = None, hset = None):
        if hprefix is not None:
            return len(list(h for h in self.goldhypothesis.keys() if h.startswith(hprefix)))
        elif hset is not None:
            # print("HIER2", self.goldhypothesis.keys(), hset)
            return len(set(self.goldhypothesis.keys()).intersection(hset))
        else:
            return len(list(self.goldhypothesis.keys()))

    ###
    # compute and return scores
    def score(self, modelhypo_obj, hprefix = None, hset = None):
        modelhypo_goldhypo, goldhypo_covered = self._match(modelhypo_obj, hprefix = hprefix, hset = hset)
        
        ###
        # For each model hypothesis, keep strict and lenient precision and recall
        # as well as percentage of statements that were conflicting with the gold hypothesis
        # Keys are model hypothesis indices.
        strict_prec = { }
        strict_rec = { }
        lenient_prec = { }
        lenient_rec = { }
        conflicting_perc = { }
        # for each model hypothesis, also keep records of which (core)
        # statements are correct or incorrect
        model_stmt_rating = { }

        for modelhypo_index, modelhypo in enumerate(modelhypo_obj["support"]):

            if modelhypo_index not in modelhypo_goldhypo or modelhypo_goldhypo[modelhypo_index] is None:
                # probably a completely empty hypothesis.
                # record it as having a recall of zero.
                strict_prec[ modelhypo_index ] = 0
                strict_rec[modelhypo_index ] = 0
                lenient_prec[modelhypo_index] = 0
                lenient_rec[modelhypo_index] = 0
                conflicting_perc[ modelhypo_index ] = 0

            else:
                
                goldhypo = modelhypo_goldhypo[ modelhypo_index]

                # determine the statements supported or partially supported by the best matching gold hypothesis
                goldhypo_supported = self.goldhypothesis[goldhypo].get("stmt_supporting", set())
                lenient_goldhypo_supported = goldhypo_supported.union(self.goldhypothesis[goldhypo].get("stmt_partially_supporting", set()))

                # strict precision and recall
                truepos = len(goldhypo_supported.intersection(modelhypo["statements"]))
                strict_prec[ modelhypo_index] = truepos / len(modelhypo["statements"])
                if len(goldhypo_supported) > 0:
                    strict_rec[modelhypo_index] = truepos / len(goldhypo_supported)
                else:
                    strict_rec[modelhypo_index] = 1

                # lenient precision and recall
                truepos = len(lenient_goldhypo_supported.intersection(modelhypo["statements"]))
                lenient_prec[modelhypo_index] = truepos / len(modelhypo["statements"])
                if len(lenient_goldhypo_supported) > 0:
                    lenient_rec[modelhypo_index] = truepos / len(lenient_goldhypo_supported)
                else:
                    lenient_rec[modelhypo_index] = 1

                # conflicting statements
                conflicting = set(modelhypo["statements"]).intersection(self.goldhypothesis[goldhypo].get("stmt_contradicting", set()))
                if len(modelhypo["statements"]) > 0:
                    conflicting_perc[modelhypo_index] = len(conflicting) / len(modelhypo["statements"])
                else:
                    conflicting_perc[modelhypo_index] = 0

                model_stmt_rating[ modelhypo_index] = { "core_correct" : [],
                                                        "core_incorrect" : [],
                                                        "other_correct" : [],
                                                        "other_incorrect" : [],
                                                        "missing" : [],
                                                        "conflicting" : list(conflicting)
                                                       }

                # core (query) statements
                for stmtlabel in modelhypo["queryStatements"]:
                    # is this statement correct or not?
                    if stmtlabel in goldhypo_supported:
                        model_stmt_rating[ modelhypo_index]["core_correct"].append(stmtlabel)
                    else:
                        model_stmt_rating[ modelhypo_index]["core_incorrect"].append(stmtlabel)

                # extra statements
                for stmtlabel in set(modelhypo["statements"]).difference(modelhypo["queryStatements"]):
                    # is this statement correct or not?
                    if stmtlabel in goldhypo_supported:
                        model_stmt_rating[ modelhypo_index]["other_correct"].append(stmtlabel)
                    else:
                        model_stmt_rating[ modelhypo_index]["other_incorrect"].append(stmtlabel)

                # missing statements
                for stmtlabel in goldhypo_supported.difference(modelhypo["statements"]):
                    model_stmt_rating[modelhypo_index]["missing"].append(stmtlabel)

        return (modelhypo_goldhypo, goldhypo_covered,
                    {"strict_prec" : strict_prec,
                     "strict_rec" : strict_rec,
                     "lenient_prec" : lenient_prec,
                     "lenient_rec" : lenient_rec,
                     "perc_conflicting" : conflicting_perc }, model_stmt_rating)
        
            
    # store info on all gold hypotheses in the AIDA graph object
    def _record_gold_hypotheses(self):
        ###
        # for each gold hypothesis, determine supporting, partially supporting, contradicting statements
        goldhypothesis = { }
        for stmtlabel, node in self.graph_obj.each_statement():
            for hyptype, stmttype in [["hypotheses_supported", "stmt_supporting"],
                                          ["hypotheses_partially_supported", "stmt_partially_supporting"],
                                          ["hypotheses_contradicted", "stmt_contradicting"]]:
                for hyplabel in node.get(hyptype, [ ]):

                    if hyplabel not in goldhypothesis:
                        goldhypothesis[hyplabel] = { }
                    if stmttype not in goldhypothesis[hyplabel]:
                        goldhypothesis[hyplabel][stmttype] = set()
                    goldhypothesis[hyplabel][stmttype].add(stmtlabel)

        # clean up the sets: statements that are supporting are not also partially supporting,
        # and statements that are (partially) supporting are not contradicting
        for hypothesis, entry in goldhypothesis.items():
            entry.get("stmt_partially_supporting", set()).difference_update(entry.get("stmt_supporting", set()))
            entry.get("stmt_contradicting", set()).difference_update(entry.get("stmt_supporting", set()))
            entry.get("stmt_contradicting", set()).difference_update(entry.get("stmt_partially_supporting", set()))

        return goldhypothesis

    # given a set of model hypotheses, match them to the closest gold hypotheses
    def _match(self, modelhypo_obj, hprefix = None, hset = None):

        ###
        # for each model hypothesis, find the closest matching gold hypothesis.
        # Also make a note of all equally matching gold hypotheses so we can compute coverage
        # returns:
        # - mapping from model hypothesis index to gold hypothesis ID (best match)
        # - list of covered gold hypotheses
        modelhypo_goldhypo = { }
        goldhypo_covered = set()

        for modelhypo_index, modelhypo in enumerate(modelhypo_obj["support"]):
            max_overlap = 0
            max_partial_overlap = 0
            max_goldhypo = [ ]

            for goldhypo in self.goldhypothesis.keys():
                # are we only considering hypotheses with a particular prefix?
                if hprefix is not None and not goldhypo.startswith(hprefix):
                    continue
                if hset is not None and goldhypo not in hset:
                    continue
                
                overlap = len(self.goldhypothesis[goldhypo].get("stmt_supporting", set()).intersection(modelhypo["statements"]))
                partial_overlap = len(self.goldhypothesis[goldhypo].get("stmt_partially_supporting", set()).intersection(modelhypo["statements"]))
                # print("modelhypo", modelhypo_index, "gold", goldhypo, overlap, partial_overlap, \
                #        goldhypothesis[goldhypo]["stmt_supporting"].intersection(modelhypo["statements"]))

                if overlap == max_overlap and partial_overlap == max_partial_overlap:
                    # add this to the set of current best gold hypotheses
                    max_goldhypo.append(goldhypo)

                elif overlap > max_overlap or (overlap == max_overlap and partial_overlap > max_partial_overlap):
                    max_overlap = overlap
                    max_partial_overlap = partial_overlap
                    # discard all previous best hypotheses, as this one has trumped them
                    max_goldhypo = [ goldhypo ]

            goldhypo_covered.update(max_goldhypo)
            if len(max_goldhypo) > 0:
                modelhypo_goldhypo[modelhypo_index] = max_goldhypo[0]
            # print("model hypothesis", modelhypo_index, ":", max_goldhypo, "with overlap", max_overlap, "/", max_partial_overlap)

        return (modelhypo_goldhypo, goldhypo_covered)
    

 







