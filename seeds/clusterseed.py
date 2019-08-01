# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# This only add the statements that the Statement of Information Need asks for,
# but constructs all possible cluster seeds that can be made using different statements
# that all fill the same SOIN


import sys
from collections import deque
import datetime
import math
import itertools
import functools
import operator
import numpy


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
    def __init__(self, graph_obj, core_constraints, temporal_constraints, hypothesis, qvar_filler, lweight = 0.0,
                    unfilled = None, unfillable = None, entrypoints = None):
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
        self.qvar_filler = qvar_filler
        # entry points (will not be used in ranking this hypothesis later)
        self.entrypoints = entrypoints

        # unfilled, unfillable are indices on self.core_constraints
        if unfilled is None: self.unfilled = set(range(len(core_constraints)))
        else: self.unfilled = unfilled

        if unfillable is None: self.unfillable = set()
        else: self.unfillable = unfillable

        # some weights for things that might go wrong during query creation
        self.FAILED_QUERY_WT = -0.5
        self.FAILED_TEMPORAL = -0.5
        self.FAILED_ONTOLOGY = -0.5
        self.DUPLICATE_FILLER = -10


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

        elif nfc["failed"]:
            # this particular constraint was not fillable, and will never be fillable.
            self.unfilled.remove(nfc["index"])
            self.unfillable.add(nfc["index"])
            # update the weight
            # print("adding failed query weight", self.lweight, self.lweight + self.FAILED_QUERY_WT)
            self.lweight += self.FAILED_QUERY_WT
            return [self ]
            
        else:
            # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
            # find statements that match this constraint, and
            # return a list of extended hypotheses to match this.
            # these hypotheses have not been run through the filter yet
            # format: list of tuples (new hypothesis, new_stmt, variable, filler)
            new_hypotheses = self._extend(nfc)

            if len(new_hypotheses) == 0:
                # print("HIER no new hypotheses")
                # something has gone wrong
                self.unfilled.remove(nfc["index"])
                self.unfillable.add(nfc["index"])
                # update the weight
                # print("adding failed query weight", self.lweight, self.lweight + self.FAILED_QUERY_WT)
                self.lweight += self.FAILED_QUERY_WT
                return [self ]

            # determine the constraint that we are matching
            # and remove it from the list of unfilled constraints
            constraint = self.core_constraints[ nfc["index"] ]

            retv = [ ]
            for new_hypothesis, stmtlabel, variable, filler in new_hypotheses:
                add_weight = 0
                
                if self.filter.validate(new_hypothesis, stmtlabel):
                    # yes: make a new OneClusterSeed object with this extended hypothesis
                    new_qvar_filler = self.qvar_filler.copy()
                    if variable is not None and filler is not None and self.graph_obj.is_ere(filler):
                        new_qvar_filler[ variable] = filler
                        if filler in self.qvar_filler.values():
                            # some other variable has been mapped to the same ERE
                            add_weight += self.DUPLICATE_FILLER
                            # print("duplicate filler", new_qvar_filler)
                            

                    # changes to unfilled, not to unfillable
                    new_unfilled = self.unfilled.difference([nfc["index"]])
                    new_unfillable = self.unfillable.copy()

                    if nfc["relaxed"]:
                        # print("adding failed ontology weight", self.lweight, self.lweight + self.FAILED_ONTOLOGY)
                        add_weight += self.FAILED_ONTOLOGY

                    retv.append(OneClusterSeed(self.graph_obj, self.core_constraints, self.temporal_constraints, new_hypothesis, new_qvar_filler,
                                                lweight = self.lweight + add_weight, unfilled = new_unfilled, unfillable = new_unfillable,
                                                entrypoints = self.entrypoints))
                

            if len(retv) == 0:
                # all the fillers were filtered away
                self.unfilled.remove(nfc["index"])
                self.unfillable.add(nfc["index"])
                # update the weight
                # print("all candidate statements filtered away, adding failed query weight", self.lweight, self.lweight + self.FAILED_QUERY_WT)
                self.lweight += self.FAILED_QUERY_WT
                return  [ self ]
            else:
                return retv
        
    # return true if there is at least one unfilled core constraint remaining
    def core_constraints_remaining(self):
        return len(self.unfilled) > 0

    # return true if there are no unfillable constraints
    def no_failed_core_constraints(self):
        return len(self.unfillable) == 0

    def has_statements(self):
        return len(self.hypothesis.stmts) > 0
    
    # next fillable constraint from the core constraints list,
    # or None if none fillable
    def _next_fillable_constraint(self):
        # iterate over unfilled query constraints to see if we can find one that can be filled
        for constraint_index in self.unfilled:
            
            subj, pred, obj = self.core_constraints[constraint_index]

            # if either subj or obj is known (is an ERE or has an entry in qvar_filler,
            # then we should be able to fill this constraint now, or it is unfillable
            subj_filler = self._known_coreconstraintentry(subj)
            obj_filler = self._known_coreconstraintentry(obj)

            if subj_filler is not None and obj_filler is not None:
                # new edge between two known variables
                return self._fill_constraint_knowneres(constraint_index, subj_filler, pred, obj_filler)
            
            elif subj_filler is not None:
                return self._fill_constraint(constraint_index, subj_filler, "subject", pred, obj, "object")

            elif obj_filler is not None:
                return self._fill_constraint(constraint_index, obj_filler, "object", pred, subj, "subject")
                
            else:
                # this constraint cannot be filled at this point,
                # wait and see if it can be filled some other time
                continue

        # reaching this point, and not having returned anything:
        # this means we do not have any fillable constraints left
        return None

            



    # given a subject or object from a core constraint, is this an ERE ID from the graph
    # or a variable for which we already know the filler?
    # if so, return the filler ERE ID. otherwise none
    def _known_coreconstraintentry(self, entry):
        if entry in self.graph_obj.thegraph: return entry
        elif entry in self.qvar_filler: return self.qvar_filler[entry]
        else: return None

    # see if this label can be generalized by cutting out the lowest level of specificity.
    # returns: generalized label, plus role (or None)
    def _generalize_label(self, label):
        pieces = label.split("_")
        if len(pieces) == 1:
            labelclass = label
            labelrole = ""
        elif len(pieces) == 2:
            labelclass = pieces[0]
            labelrole = pieces[1]
        else:
            print("unexpected number of underscores in label, could not split", label)
            return (None, None)
    
        pieces = labelclass.split(".")
        if len(pieces) <= 2:
            # no more general class possible
            return (None, None)
        
        # we can try a more lenient match
        labelclass = ".".join(pieces[:-1])
        return (labelclass, labelrole)

    # returns list of statement candidates bordering ERE
    # that have ERE in role 'role' (subject, object) and have predicate 'pred'.
    # also returns whether the statements had to be relaxed.
    # If no statements could be found, returnsNone
    def _statement_candidates(self, ere, pred, role):
        candidates = list(self.graph_obj.each_ere_adjacent_stmt(ere, pred, role))

        if len(candidates) > 0:
            # success, we found some
            return { "candidates" : candidates,
                     "relaxed" : False }

        # no success. see if more lenient match will work
        lenient_pred, lenient_role = self._generalize_label(pred)

        # print("no match for", pred, "checking", lenient_pred, lenient_role)
        
        if lenient_pred is None:
            # no generalization possible
            return None
        else:
            # try the more general class
            candidates = []
            for stmt in self.graph_obj.each_ere_adjacent_stmt_anyrel(ere):
                if self.graph_obj.stmt_predicate(stmt).startswith(lenient_pred) and self.graph_obj.stmt_predicate(stmt).endswith(lenient_role):
                    candidates.append(stmt)

            if len(candidates) > 0:
                # success, we found some
                # print("success")
                return { "candidates" : candidates,
                            "relaxed" : True }
            else:
                return None
                
    # try to fill this constraint from the graph, either strictly or leniently.
    # one side of this constraint is a known ERE, the other side can be anything
    def _fill_constraint(self, constraint_index, knownere, knownrole, pred, unknown, unknownrole):
        # find statements that could fill the role
        candidates = self._statement_candidates(knownere, pred, knownrole)

        if candidates is None:
            # no candidates found at all, constraint is unfillable
            return { "index" : constraint_index,
                    "failed" : True
                         }
        
        # check if unknown is a constant in the graph,
        # in which case it is not really unknown
        if self._is_string_constant(unknown):
            # which of the statement candidates have the right filler?
            candidates = [s for s in candidates if self.graph_obj.thegraph[s][unknownrole] == unknown]
            if len(candidates) == 0:
                return { "index" : constraint_index,
                    "failed" : True
                         }
            else:
                return {
                    "index" : constraint_index,
                    "stmt" : candidates["candidates"],
                    "role" : knownrole,
                    "has_variable" : False,
                    "relaxed" : candidates["relaxed"],
                    "failed" : False
                    }
                        
        else:
            # nope, we have a variable we can fill
            # any fillers?
            return {
                "index" : constraint_index,
                "stmt" : candidates["candidates"],
                "variable" : unknown,
                "role" : knownrole,
                "has_variable" : True,
                "relaxed" : candidates["relaxed"],
                "failed" : False
                }
        
    # try to fill this constraint from the graph, either strictly or leniently.
    # both sides of this constraint are known EREs
    def _fill_constraint_knowneres(self, constraint_index, ere1, pred, ere2):
        # find statements that could fill the role
        possible_candidates = self._statement_candidates(ere1, pred, "subject")

        if possible_candidates is None:
            # no candidates found at all, constraint is unfillable
            return { "index" : constraint_index,
                    "failed" : True
                         }

        # we did find candidates.
        # check whether any of the candidates has ere2 as its object
        candidates = [c for c in possible_candidates["candidates"] if self.graph_obj.stmt_object == ere2]
        if len(candidates) == 0:
            # constraint is unfillable
            return { "index" : constraint_index,
                    "failed" : True
                         }

        else:
            return { "index" : constraint_index,
                         "failed" : False,
                         "stmt" : candidates,
                         "has_variable" : False,
                         "relaxed" : candidates["relaxed"]
                         }
            
        

    # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
    # find statements that match this constraint, and
    # return a list of triples; (extended hypothesis, query_variable, filler)
    def _extend(self, nfc):

        if len(nfc["stmt"]) == 0:
            # did not find any matches to this constraint
            return [ ]

        if not nfc["has_variable"]:
            # this next fillable constraint states a constant string value about a known ERE,
            # or it states a new connection between known EREs.
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
            # print("adding failed temporal weight", self.lweight, self.lweight + self.FAILED_TEMPORAL)
            self.lweight += self.FAILED_TEMPORAL
            retv, has_temporal_constraint = self._extend_withvariable(nfc, 1)
            
        if len(retv) == 0 and has_temporal_constraint:
            # relax temporal matching: everything goes
            # print("adding failed temporal weight", self.lweight, self.lweight + self.FAILED_TEMPORAL)
            self.lweight += self.FAILED_TEMPORAL
            retv, has_temporal_constraint = self._extend_withvariable(nfc, 2)
        
        return retv

    # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
    # find statements that match this constraint, and
    # return a pair (hyp, has_temporal_cosntraint) where
    # hyp is a list of triples; (extended hypothesis, query_variable, filler)
    # and has_temporal_constraint is true if there was at least one temporal constraint that didn't get matched
    def _extend_withvariable(self, nfc, leeway = 0):

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
                    # print("temp mismatch")
                    has_temporal_constraint = True
                    continue

                # we also check wether including this statement will violate another constraint.
                # if so, we do  not include it
                if self._second_constraint_violated(nfc["variable"], filler, nfc["index"]):
                    # print("second constraint violated, skipping", stmtlabel[-5:], self.graph_obj.stmt_predicate(stmtlabel))
                    continue

            # can this statement be added to the hypothesis without contradiction?
            # extended hypothesis
            new_hypothesis = self.hypothesis.extend(stmtlabel, core = True)
            retv.append( (new_hypothesis, stmtlabel, nfc["variable"], filler) )

        return (retv, has_temporal_constraint)

    # second constraint violated: given a variable and its filler,
    # see if filling this qvar with this filler will make any constraint that is yet unfilled unfillable
    def _second_constraint_violated(self, variable, filler, exceptindex):
        for constraint_index in self.unfilled:
            if constraint_index == exceptindex:
                # this was the constraint we were just going to fill, don't re-check it
                continue
            
            subj, pred, obj = self.core_constraints[constraint_index]
            if subj == variable and obj in self.qvar_filler:
                # found a constraint involving this variable and another variable that has already been filled
                candidates = self._statement_candidates(filler, pred, "subject")
                if candidates is None:
                    ## print("trying to add", filler[-5:], "for", variable, "originally doing", self.core_constraints[exceptindex], exceptindex, constraint_index)
                    ## print("could not fill", subj, pred, obj, "where obj is ", self.qvar_filler[obj][-5:])
                    ## input()
                    return True
                else:
                    candidates = [c for c in candidates["candidates"] if self.graph_obj.stmt_object == self.qvar_filler[obj]]
                    if len(candidates) == 0:
                        ## print("trying to add", filler[-5:], "for", variable, "originally doing", self.core_constraints[exceptindex], exceptindex, constraint_index)
                        ## print("could not fill", subj, pred, obj, "where obj is ", self.qvar_filler[obj][-5:])
                        ## input()
                        return True
                    
            elif obj == variable and subj in self.qvar_filler:                
                # found a constraint involving this variable and another variable that has already been filled
                candidates = self._statement_candidates(filler, pred, "object")
                if candidates is None:
                    ## print("trying to add", filler[-5:], "for", variable, "originally doing", self.core_constraints[exceptindex], exceptindex, constraint_index)
                    ## print("could not fill", subj, pred, obj, "where subj is ", self.qvar_filler[subj][-5:])
                    ## input()
                    return True
                else:
                    candidates = [c for c in candidates["candidates"] if self.graph_obj.stmt_subject == self.qvar_filler[subj]]
                    if len(candidates) == 0:
                        ## print("trying to add", filler[-5:], "for", variable, "originally doing", self.core_constraints[exceptindex], exceptindex, constraint_index)
                        ## print("could not fill", subj, pred, obj, "where subj is ", self.qvar_filler[subj][-5:])
                        ## input()
                        return True

        return False
                
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
    def __init__(self, graph_obj, soin_obj, discard_failedqueries = False, earlycutoff = None):
        self.graph_obj = graph_obj
        self.soin_obj = soin_obj

        self.discard_failedqueries = discard_failedqueries
        self.earlycutoff = earlycutoff
        
        # parameters for ranking
        self.rank_first_k = 100
        self.bonus_for_novelty = -5
        self.consider_next_k_in_reranking = 10000
        self.num_bins = 5

        # make seed clusters
        self.hypotheses = self._make_seeds()

    # export hypotheses to AidaHypothesisCollection
    def finalize(self):

        # ranking is a list of the hypotheses in self.hypotheses,
        # best first
        print("Making the ranking")
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
        # keep queue of hypotheses-in-making, list of finished hypotheses
        hypotheses_todo = deque()
        hypotheses_done = [ ]

        # HIER
        QS_COUNT_CUTOFF = 3
        QS_CUTOFF = 100
        qvar_signatures = { }
        def make_one_signature(keys, qfdict):
            return "_".join(k + "|" + qfdict[k][-5:] for k in sorted(keys))
            
        def make_qvar_signature(h):
            if len(h.qvar_filler) - len(h.entrypoints) < QS_COUNT_CUTOFF:
                return None
            # return "_".join(k + "|" + v for k, v in sorted(h.qvar_filler.items()))
            # return "_".join(k + "|" + v[-5:] for k, v in sorted(h.qvar_filler.items()))
            qs_entry = make_one_signature(h.entrypoints, h.qvar_filler)
            return [qs_entry + "_" + make_one_signature(keys, h.qvar_filler) for keys in itertools.combinations(sorted(k for k in h.qvar_filler.keys() if k not in h.entrypoints), 2)]

        # have we found any hypothesis without failed queries yet?
        # if so, we can eliminate all hypotheses with failed queries
        previously_found_hypothesis_without_failed_queries = False

        if self.earlycutoff is not None:
            facet_cutoff = self.earlycutoff / len(self.soin_obj["facets"])

        ################
        print("Initializing cluster seeds")
        # initialize deque with one core hypothesis per facet
        for facet in self.soin_obj["facets"]:

            index = 0
            for qvar_filler, entrypoint_weight in self._each_entry_point_combination(self.soin_obj["entrypoints"], self.soin_obj["entrypointWeights"], facet):
                ## print("entry points")
                ## for q, f in qvar_filler.items():
                ##     print(q, f[-5:])
                ## print("====")
                index += 1

                if self.earlycutoff is not None and index >= facet_cutoff:
                    # print("early cutoff on cluster seeds: breaking off at", index)
                    break

                # start a new hypothesis
                core_hyp = OneClusterSeed(self.graph_obj, facet["queryConstraints"], self._pythonize_datetime(facet.get("temporal", {})), \
                                              AidaHypothesis(self.graph_obj), qvar_filler, lweight = entrypoint_weight,
                                              entrypoints = list(qvar_filler.keys()))
                hypotheses_todo.append(core_hyp)

        ################
        print("Extending cluster seeds")
        testindex = 0
        # extend all hypotheses in the deque until they are done
        while len(hypotheses_todo) > 0:
            testindex += 1
            if testindex % 500 == 0:
                print("hypotheses to do", len(hypotheses_todo), "hypotheses done", len(hypotheses_done))
                #input()
            # if len(hypotheses_done) > 5000:
            #       break
            
            core_hyp = hypotheses_todo.popleft()
            qs = make_qvar_signature(core_hyp)
            if qs is not None:
                if any(qvar_signatures.get(q1, 0) >= QS_CUTOFF for q1 in qs):
                    # do not process this hypothesis further
                    # print("skipping hypothesis", qs)
                    continue
                else:
                    for q1 in qs:
                        # print("HIER", q1, qvar_signatures.get(q1, 0))
                        qvar_signatures[ q1] = qvar_signatures.get(q1, 0) + 1

            if self.discard_failedqueries:
                # we are discarding hypotheses with failed queries
                if previously_found_hypothesis_without_failed_queries and not(core_hyp.no_failed_core_constraints()):
                    # don't do anything with this one, discard
                    # It has failed queries, and we have found at least one hypothesis without failed queries
                    # print("discarding hypothesis with failed queries")
                    continue
                
            if core_hyp.done:
                # hypothesis finished.
                # any statements in this one?
                if not core_hyp.has_statements():
                    # if not, don't record it
                    # print("empty hypothesis")
                    continue

                if self.discard_failedqueries and core_hyp.no_failed_core_constraints():
                    # yes, no failed queries!
                    # is this the first one we find? then remove all previous "done" hypotheses,
                    # as they had failed queries
                    if not previously_found_hypothesis_without_failed_queries:
                        # print("found a hypothesis without failed queries, discarding", len(hypotheses_done))
                        hypotheses_done = [ ]

                if core_hyp.no_failed_core_constraints():
                    previously_found_hypothesis_without_failed_queries = True


                # mark this hypothesis as done
                hypotheses_done.append(core_hyp)
                ## for q, v in core_hyp.qvar_filler.items():
                ##     print("qvar", q, v[-5:])
                ## print([s[-5:] for s in core_hyp.hypothesis.stmts])
                ## print("----")
                        
                continue

            new_hypotheses = core_hyp.extend()
            # put extensions of this hypothesis to the beginning of the queue, such that
            # we explore one hypothesis to the end before we start the next.
            # this way we can see early if we have hypotheses without failed queries
            hypotheses_todo.extendleft(new_hypotheses)
            # hypotheses_todo.extend(new_hypotheses)

        if not previously_found_hypothesis_without_failed_queries:
            print("Warning: All hypotheses had at least one failed query.")
        
        # at this point, all hypotheses are as big as they can be.
        return hypotheses_done

    #################################
    # Return any combination of entry point fillers for all the entry points
    #
    # returns pairs (qvar_filler, weight)
    # where qvar_filler is a dictionary mapping query variables to fillers, and
    # weight is the confidence of the fillers
    def _each_entry_point_combination(self, entrypoints, entrypoint_weights, facet):
        # variables occurring in this facet: query constraints have the form [subj, pred, obj] where subj, obj are variables.
        # collect those
        facet_variables = set(c[0] for c in facet["queryConstraints"]).union(c[2] for c in facet["queryConstraints"])
        # variables we are filling: all entry points that appear in the query constraints of this facet
        entrypoint_variables = sorted(e for e in entrypoints.keys() if e in facet_variables)

        # itertools.product does Cartesian product of n sets
        # here we do a product of entry point filler indices, so we can access each filler as well as its weight
        filler_index_tuples = [ ]
        weights = [ ]

        for filler_indices in itertools.product(*(range(len(entrypoints[v])) for v in entrypoint_variables)):

            # qvar-> filler mapping: pair each entry point variable with the i-th filler, where i
            # is the filler index for that entry point variable
            qvar_fillers = dict((v, entrypoints[v][i]) for v, i in zip(entrypoint_variables, filler_indices))

            # reject if any two variables are mapped to the same ERE
            if any (qvar_fillers[v1] == qvar_fillers[v2] for v1 in entrypoint_variables for v2 in entrypoint_variables if v1 != v2):
                continue
            
            filler_index_tuples.append( qvar_fillers)
            # weight:
            # filler weights are in the range of [0, 100]
            # multiply weights/100 of the fillers,
            # then take the log to be in log-probability space
            weights.append( math.log(functools.reduce(operator.mul, (entrypoint_weights[v][i]/100.0 for v, i in zip(entrypoint_variables, filler_indices)))))

        for qvar_filler, weight in sorted(zip(filler_index_tuples, weights), key = lambda pair:pair[1], reverse = True):
            yield (qvar_filler, weight)
        
    ##################################
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
        ## qf_signatures = set()
        ## for h in self.hypotheses:
        ##     s = "___".join([ key + "_" + filler[-6:] for key, filler in sorted(h.qvar_filler.items())])
        ##     if s in qf_signatures:
        ##         print("duplicate signature")
        ##     qf_signatures.add(s)
                

        ## input()
        
        # group seeds by their current weight,
        # which depends on the goodness of their entry points
        # and on whether they missed any query constraints
        # this is a list of lists of hypotheses
        hypothesis_groups = self._group_seed_byweight(self.hypotheses)
        # print("HIER group sizes", [len(g) for g in hypothesis_groups])
        #print("HIER first group weights", [h.lweight for h in hypothesis_groups[0]])
        #print("HIER last group weights", [h.lweight for h in hypothesis_groups[-1]])
        ## for g in hypothesis_groups:
        ##     print("group weights", [h.lweight for h in g])
        ##     print("duplicate weights?", [any(h.qvar_filler[v1] == h.qvar_filler[v2] for h in g for v1 in h.qvar_filler.keys() for v2 in h.qvar_filler.keys() if v1 != v2) for h in g])
        
        # initial ranking by connectedness, using the hypothesis groups
        ranking= self._rank_seed_connectedness(hypothesis_groups)

        # re-rank by diversity. we only care about the self.rank_first_k highest ranked items
        ranking = self._rank_seed_novelty(ranking)

        # ranking is a list of hypotheses from self.hypotheses, ranked
        # best first
        return ranking

    # group hypotheses by their lweight,
    # which indicates how good their entrypoints were,
    # and whether they failed to meet any query constraints
    def _group_seed_byweight(self, hypotheses):
        # sort hypotheses by weight, highest first
        # but first make sure each hypothesis has a weight
        for hyp in hypotheses:
            if hyp.lweight is None:
                # this should not happen, but just to make sure
                hyp.lweight = 0.0
                
        hypotheses_sorted = sorted(hypotheses, key = lambda h: h.lweight, reverse = True)
        hypothesis_weights = [h.lweight for h in hypotheses_sorted]

        # make self.num_bins bins of weights
        bin_sizes, dummy = numpy.histogram(hypothesis_weights, self.num_bins)

        # print("HIER1", hypotheses_sorted, bin_sizes)
        bins = [ ]
        
        lower_index = 0
        for binsize in bin_sizes:
            bins.append(hypotheses_sorted[ lower_index : lower_index + binsize] )
            lower_index += binsize
            

        ## for ix, b in enumerate(bins):
        ##     print("HIER bin", ix, [h.lweight for h in b])
            
        return bins
        ## # make list of hypothesis weights
        ## grouping = { }
        ## for hyp in hypotheses:
        ##     if hyp.lweight is None:
        ##         # this should not happen, but just to make sure
        ##         hyp.lweight = 0.0
                
        ##     if hyp.lweight not in grouping:
        ##         grouping[hyp.lweight] = [ ]

        ##     grouping[hyp.lweight].append(hyp)

        ## return grouping
    
    # weighting based on connectedness of a cluster seed:
    # sum of degrees of EREs in the cluster.
    # this rewards both within-cluster and around-cluster connectedness
    # this does seed connectedness ratings for multiple groups of hypotheses,
    # where the grouping is a mapping from weight to group
    def _rank_seed_connectedness(self, grouped_hypotheses):
        ranking = [ ]
        for group in grouped_hypotheses:
            ranking += self._rank_seed_connectedness_forgroup(group)

        # print("HIER ranking", [h.lweight for h in ranking])
        return ranking
    
        ## ranking = [ ]
        ## # sort groups by weight, highest weight first
        ## for lweight, group in sorted(grouped_hypotheses.items(), reverse = True):
        ##     ranking += self._rank_seed_connectedness_forgroup(group)

        ## return ranking

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
        if len(hypotheses) == 0:
            return hypotheses
        
        ranked = [ hypotheses[0] ]
        torank = hypotheses[1:]

        qvar_characterization = self._update_qvar_characterization_for_seednovelty({ }, hypotheses[0])

        # print("HIER rank0", hypotheses[0].qvar_filler)
        
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
                if qvar in hyp.entrypoints:
                    # do not count entry point variables when checking for novelty
                    # print("skipping variable in ranking", qvar)
                    continue
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
