# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# This only add the statements that the Statement of Information Need asks for,
# but constructs all possible cluster seeds that can be made using different statements
# that all fill the same SOIN

import sys
from collections import deque
import datetime
import math


from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from seeds.aidahypothesis import AidaHypothesis, AidaHypothesisCollection
from seeds.hypothesisfilter import AidaHypothesisFilter
from seeds.datecheck import AidaIncompleteDate, temporal_constraint_match


#########
# class that holds a single cluster seed.
# just a data structure, doesn't do much.
class OneClusterSeed:
    def __init__(self, graph_obj, core_constraints, temporal_constraints, hypothesis, lweight = 0.0,
                     qvar_filler = None, unfilled = None, unfillable = None):
        # the following data is not changed, and is kept just for info
        self.graph_obj = graph_obj
        self.core_constraints = core_constraints
        # temporal constraints: mapping queryvariable -> {start_time: ..., end_time:...}
        self.temporal_constraints = temporal_constraints
        # the following data is changed.
        # flags: am I done?
        self.done = False

        # what is my current log weight?
        self.lweight = lweight
        
        # hypothesis is an AidaHypothesis object
        self.hypothesis = hypothesis

        # hypothesis filter
        self.filter = AidaHypothesisFilter(self.graph_obj)

        # mapping from query variable to filler: string to string, value strings are IDs in graph_obj
        if qvar_filler is None: self.qvar_filler = { }
        else: self.qvar_filler = qvar_filler

        # unfilled, unfillable are indices on self.core_constraints
        if unfilled is None: self.unfilled = set(range(len(core_constraints)))
        else: self.unfilled = unfilled

        if unfillable is None: self.unfillable = set()
        else: self.unfillable = unfillable

        # some weights
        self.FAILED_QUERY_WT = -0.5
        self.FAILED_TEMPORAL = -0.5

    # finalize:
    # report failed queries ot the underlying AidaHypothesis object
    def finalize(self):

        self.hypothesis.add_failed_queries( list(map( lambda ix: self.core_constraints[ix], self.unfillable)) )
        self.hypothesis.update_lweight(self.lweight)
        self.hypothesis.add_qvar_filler(self.qvar_filler)

        return self.hypothesis
            
    # extend hypothesis by one statement filling the next fillable core constraint.
    # returns a list of OneClusterSeed objects
    def extend(self):
        nfc = self._next_fillable_constraint()

        if nfc is None:
            # no next fillable constraint.
            # declare done, and return only this object
            self.done = True
            # no change to qvar_filler
            self.unfillable.update(self.unfilled)
            self.unfilled = set()
            return [ self ]

        # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
        # find statements that match this constraint, and
        # return a list of extended hypotheses to match this.
        # these hypotheses have not been run through the filter yet
        # format: list of tuples (new hypothesis, new_stmt, variable, filler)
        new_hypotheses = self._extend(nfc)

        if len(new_hypotheses) == 0:
            # something has gone wrong
            self.unfilled.remove(nfc["index"])
            self.unfillable.add(nfc["index"])
            # update the weight
            self.lweight += self.FAILED_QUERY_WT
            return [self ]

        # determine the constraint that we are matching
        # and remove it from the list of unfilled constraints
        constraint = self.core_constraints[ nfc["index"] ]

        retv = [ ]
        for new_hypothesis, stmtlabel, variable, filler in new_hypotheses:
            if self.filter.validate(new_hypothesis, stmtlabel):
                # yes: make a new OneClusterSeed object with this extended hypothesis
                new_qvar_filler = self.qvar_filler.copy()
                if variable is not None and filler is not None and self.graph_obj.is_ere(filler):
                    new_qvar_filler[ variable] = filler

                # changes to unfilled, not to unfillable
                new_unfilled = self.unfilled.difference([nfc["index"]])
                new_unfillable = self.unfillable.copy()

                retv.append(OneClusterSeed(self.graph_obj, self.core_constraints, self.temporal_constraints, new_hypothesis, self.lweight, 
                       new_qvar_filler, new_unfilled, new_unfillable))
                

        if len(retv) == 0:
            # all the fillers were filtered away
            self.unfilled.remove(nfc["index"])
            self.unfillable.add(nfc["index"])
            # update the weight
            self.lweight += self.FAILED_QUERY_WT
            return  [ self ]
        else:
            return retv
        
    # return true if there is at least one unfilled core constraint remaining
    def core_constraints_remaining(self):
        return len(self.unfilled) > 0
    
    # next fillable constraint from the core constraints list,
    # or None if none fillable
    def _next_fillable_constraint(self):
        for constraint_index in self.unfilled:
            
            subj, pred, obj = self.core_constraints[constraint_index]

            # if we can fill this constraint, then either subj is known and
            # obj is unknown/constraint, or obj is known and subj is unknown/constraint
            for known, unknown, knownrole, unknownrole in [(subj, obj, "subject", "object"), (obj, subj, "object", "subject")]:
                if known in self.graph_obj.thegraph:
                    knownere = known
                elif known in self.qvar_filler:
                    knownere = self.qvar_filler[known]
                else:
                    knownere = None


                if knownere is not None:
                    # we do seem to have a fillable constraint
                    # what are the statements that could fill it?
                    stmt_candidates = list(self.graph_obj.each_ere_adjacent_stmt(knownere, pred, knownrole))
                        
                    # check if unknown is a constant in the graph,
                    # in which case it is not really unknown
                    if self._is_string_constant(unknown):
                        # which of the statement candidates have the right filler?
                        stmt_candidates = [s for s in stmt_candidates if self.graph_obj.thegraph[s][unknownrole] == unknown]
                        return {
                            "index" : constraint_index,
                            "stmt" : stmt_candidates,
                            "role" : knownrole,
                            "has_variable" : False
                            }
                        
                    else:
                        # nope, we have a variable we can fill
                        return {
                            "index" : constraint_index,
                            "stmt" : stmt_candidates,
                            "variable" : unknown,
                            "role" : knownrole,
                            "has_variable" : True
                            }

        return None

    # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
    # find statements that match this constraint, and
    # return a list of triples; (extended hypothesis, query_variable, filler)
    def _extend(self, nfc):

        if len(nfc["stmt"]) == 0:
            # did not find any matches to this constraint
            return [ ]

        if not nfc["has_variable"]:
            # this next fillable constraint states a constant string value about a known ERE.
            # we do have more than zero matching statements. add just the first one, they are identical
            stmtlabel = nfc["stmt"][0]
            if stmtlabel not in self.graph_obj.thegraph:
                print("Error in ClusterSeed: unexpectedly did not find statement", stmtlabel)
                return [ ]
                
            else:
                # can this statement be added to the hypothesis without contradiction?
                # extended hypothesis
                return [ (self.hypothesis.extend(stmtlabel, core = True), stmtlabel, None, None)]

        # we know that we have a variable now.
        # it is in nfc["variable"]
        # determine the role that the variable is filling, if there is a variable
        # make a new hypothesis for each statement that could fill the current constraint.
        # if we don't find anything, re-run with more leeway on temporal constraints
        retv, has_temporal_constraint = self._extend_withvariable(nfc, 0)
        if len(retv) == 0 and has_temporal_constraint:
            # relax temporal matching by one day
            # update weight to reflect relaxing of temporal constraint
            self.lweight += self.FAILED_TEMPORAL
            retv, has_temporal_constraint = self._extend_withvariable(nfc, 1)
            
        if len(retv) == 0 and has_temporal_constraint:
            # relax temporal matching: everything goes
            self.lweight += self.FAILED_TEMPORAL
            retv, has_temporal_constraint = self._extend_withvariable(nfc, 2)
        
        return retv

    # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
    # find statements that match this constraint, and
    # return a pair (hyp, has_temporal_cosntraint) where
    # hyp is a list of triples; (extended hypothesis, query_variable, filler)
    # and has_temporal_constraint is true if there was at least one temporal constraint that didn't get matched
    def _extend_withvariable(self, nfc, leeway = 0):

        # print("HIER leeway", leeway)
        retv = [ ]
        has_temporal_constraint = False
        
        otherrole = self._nfc_otherrole(nfc)
        if otherrole is None:
            # some error
            return (retv, has_temporal_constraint)

        
        for stmtlabel in nfc["stmt"]:
            if stmtlabel not in self.graph_obj.thegraph:
                print("Error in ClusterSeed: unexpectedly did not find statement", stmtlabel)
                continue

            # determine the entity or value that fills the role that has the variable
            filler = self.graph_obj.thegraph[stmtlabel][otherrole]

            # is this an entity? if so, we need to check for temporal constraints.
            if filler in self.graph_obj.thegraph:
                # is there a problem with a temporal constraint?
                if not temporal_constraint_match(self.graph_obj.thegraph[filler], self.temporal_constraints.get(nfc["variable"], None), leeway):
                    # yup, this filler runs afoul of some temporal constraint.
                    # do not use it
                    print("temp mismatch")
                    has_temporal_constraint = True
                    continue

            # can this statement be added to the hypothesis without contradiction?
            # extended hypothesis
            new_hypothesis = self.hypothesis.extend(stmtlabel, core = True)
            retv.append( (new_hypothesis, stmtlabel, nfc["variable"], filler) )

        return (retv, has_temporal_constraint)
    
    # given a next_fillable_constraint dictionary,
    # if it has a role of "subject" return 'object' and vice versa
    def _nfc_otherrole(self, nfc):
        if nfc["role"] == "subject":
            return "object"
        elif nfc["role"] == "object":
            return "subject"
        else:
            print("ClusterSeed error: unknown role", nfc["role"])
            return None

    # is the given string a variable, or should it be viewed as a string constant?
    # use the list of all string constants in the given graph
    def _is_string_constant(self, strval):
        return strval in self.graph_obj.string_constants_of_graph

      
#########################
#########################
# class that manages all cluster seeds
class ClusterSeeds:
    # initialize with an AidaJson object and a statement of information need,
    # which is just a json object
    def __init__(self, graph_obj, soin_obj):
        self.graph_obj = graph_obj
        self.soin_obj = soin_obj

        # parameters for ranking
        self.rank_first_k = 100
        self.bonus_for_novelty = -5
        self.consider_next_k_in_reranking = 10000

        # make seed clusters
        self.hypotheses = self._make_seeds()
        
    # export hypotheses to AidaHypothesisCollection
    def finalize(self):

        # ranking is a list of the hypotheses in self.hypotheses,
        # best first
        ranking = self._rank_seeds()

        # turn ranking into log weights:
        # meaningless numbers. just assign 1/2, 1/3, 1/4, ...
        for rank, hyp in enumerate(ranking):
            hyp.lweight = math.log(1.0 / (rank + 1))
        
        hypotheses_for_export = [ h.finalize() for h in ranking ] #sorted(self.hypotheses, key = lambda h:h.hypothesis.lweight, reverse = True)]
        return AidaHypothesisCollection( hypotheses_for_export)
        
    # create initial cluster seeds.
    # this is called from __init__
    def _make_seeds(self):
        hypotheses_todo = deque()
        hypotheses_done = [ ]

        # initialize deque with one core hypothesis per facet
        for facet_index, facet in enumerate(self.soin_obj["facets"]):

            # start a new hypothesis
            core_hyp = OneClusterSeed(self.graph_obj, facet["queryConstraints"], self._pythonize_datetime(facet.get("temporal", {})), \
                                          AidaHypothesis(self.graph_obj), lweight = 0.0)
            hypotheses_todo.append(core_hyp)

        # extend all hypotheses in the deque until they are done
        while len(hypotheses_todo) > 0:
            core_hyp = hypotheses_todo.popleft()
            if core_hyp.done:
                # nothing more to be done for this hypothesis
                hypotheses_done.append(core_hyp)
                continue

            new_hypotheses = core_hyp.extend()
            hypotheses_todo.extend(new_hypotheses)

        # at this point, all hypotheses are as big as they can be.
        return hypotheses_done


    # given the "temporal" piece of a statement of information need,
    # turn the date and time info in the dictionary
    # into Python datetime objects
    def _pythonize_datetime(self, json_temporal):
        retv = { }
        for qvar, tconstraint in json_temporal.items():
            retv[qvar] = { }
            
            if "start_time" in tconstraint:
                entry = tconstraint["start_time"]
                retv[qvar]["start_time"] = AidaIncompleteDate(entry.get("year", None), entry.get("month", None), entry.get("day", None))
            if "end_time" in tconstraint:
                entry = tconstraint["end_time"]
                retv[qvar]["end_time"] = AidaIncompleteDate(entry.get("year", None), entry.get("month", None), entry.get("day", None))
                                                        
        return retv

    #########################
    # compute a weight for all cluster seeds in self.hypotheses
    def _rank_seeds(self):
        # group seeds by their current weight,
        # which depends on whether they missed any query constraints
        hypothesis_groups = self._group_seed_byweight(self.hypotheses)
        
        # initial ranking by connectedness, using the hypothesis groups
        ranking= self._rank_seed_connectedness(hypothesis_groups)

        # re-rank by diversity. we only care about the self.rank_first_k highest ranked items
        ranking = self._rank_seed_novelty(ranking)

        # ranking is a list of hypotheses from self.hypotheses, ranked
        # best first
        return ranking

    # group hypotheses by their lweight,
    # which indicates whether they failed to meet any query constraints
    def _group_seed_byweight(self, hypotheses):
        grouping = { }
        for hyp in hypotheses:
            if hyp.lweight is None:
                # this should not happen, but just to make sure
                hyp.lweight = 0.0
                
            if hyp.lweight not in grouping:
                grouping[hyp.lweight] = [ ]

            grouping[hyp.lweight].append(hyp)

        return grouping
    
    # weighting based on connectedness of a cluster seed:
    # sum of degrees of EREs in the cluster.
    # this rewards both within-cluster and around-cluster connectedness
    # this does seed connectedness ratings for multiple groups of hypotheses,
    # where the grouping is a mapping from weight to group
    def _rank_seed_connectedness(self, grouped_hypotheses):
        ranking = [ ]
        # sort groups by weight, highest weight first
        for lweight, group in sorted(grouped_hypotheses.items(), reverse = True):
            ranking += self._rank_seed_connectedness_forgroup(group)

        return ranking

    #  do the actual work in connectedness ranking
    def _rank_seed_connectedness_forgroup(self, hypotheses):
        weights = [ ]

        for hypothesis in hypotheses:
            outdeg = 0
            # for each ERE of this hypothesis
            for erelabel in hypothesis.hypothesis.eres():
                # find statements IDs of statements adjacent to the EREs of this hypothesis
                for stmtlabel in self.graph_obj.each_ere_adjacent_stmt_anyrel(erelabel):
                    outdeg += 1
            weights.append( outdeg)

        return [ h for h, w in sorted(zip(hypotheses, weights), key = lambda hw:hw[1], reverse = True)]

    # given a list of pairs (ranking, OneClusterSeed object),
    # produce a new such list where objects are ranked more highly
    # if they differ most from all the top k items
    def _rank_seed_novelty(self, hypotheses):
        ranked = [ hypotheses[0] ]
        torank = hypotheses[1:]

        qvar_characterization = self._update_qvar_characterization_for_seednovelty({ }, hypotheses[0])

        print("HIER rank0", hypotheses[0].qvar_filler)
        ix = 0
        
        while len(torank) > max(0, len(hypotheses) - self.rank_first_k):
            # select the item to rank next
            # print("HIER qvar ch.", qvar_characterization)
            nextitem_index = self._rank_seed_novelty_one(torank, qvar_characterization)
            if nextitem_index is None:
                # we didn't find any more items to rank
                break
            
            # append the next best item to the ranked items
            nextitem = torank.pop(nextitem_index)
            ranked.append(nextitem)
            if ix < 11:
                print("HIEr nextitem", nextitem.qvar_filler)
                ix += 1
            qvar_characterization = self._update_qvar_characterization_for_seednovelty(qvar_characterization, nextitem)

        # at this point we have ranked the self.rank_first_k items
        # just attach the rest of the items at the end
        ranked += torank

        return ranked

    def _rank_seed_novelty_one(self, torank, qvar_characterization):
        # for each item in torank, determine difference from items in ranked
        # in terms of qvar_filler

        best_index = None
        best_value = None
        
        for index, hyp in enumerate(torank):
            if index >= self.consider_next_k_in_reranking:
                # we have run out of the next k to consider,
                # don't go further down the list
                break

            this_value = 0
            for qvar, filler in hyp.qvar_filler.items():
                if qvar in qvar_characterization.keys():
                    if filler in qvar_characterization[ qvar ]:
                        # there are higher-ranked hypotheses that have the same filler
                        # for this qvar. take a penalty for that
                        this_value += qvar_characterization[qvar][filler]
                    else:
                        # novel qvar filler! Take a bonus
                        this_value += self.bonus_for_novelty
                else:
                    # this hypothesis, for some reason, has a query variable
                    # that we haven't seen before.
                    # this shouldn't happen.
                    # oh well, take a bonus for novelty then
                    this_value += self.bonus_for_novelty

            # print("HIER1", this_value, hyp.qvar_filler)
            # input("hit enter...")

            # at this point we have the value for the current hypothesis.
            # if it is the minimum achievable value, stop here and go with this hypothesis
            if this_value <= self.bonus_for_novelty * len(qvar_characterization):
                best_index = index
                best_value = this_value
                break

            # check if the current value is better than the previous best.
            # if so, record this index as the best one
            if best_value is None or this_value < best_value:
                best_index = index
                best_value = this_value


        return best_index

        
    # ranking by seed novelty uses a characterization of the query variable fillers for the
    # already ranked items.
    # this function takes an existing query variable characterization and updates it
    # with the query variable fillers of the given hypothesis, which is a OneClusterSeed.
    # format of qvar_characterization:
    # qvar -> filler -> count
    #
    # That is, we penalize a hypothesis that has the same qvar filler that we have seen before
    # with a value equivalent to the number of previous hypotheses that had the same filler.
    def _update_qvar_characterization_for_seednovelty(self, qvar_characterization, hypothesis):
        for qvar, filler in hypothesis.qvar_filler.items():
            if qvar not in qvar_characterization:
                qvar_characterization[ qvar ] = { }

            qvar_characterization[ qvar ][ filler ] = qvar_characterization[qvar].get(filler, 0) + 1

        return qvar_characterization
