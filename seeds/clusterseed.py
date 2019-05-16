# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# This only add the statements that the Statement of Information Need asks for,
# but constructs all possible cluster seeds that can be made using different statements
# that all fill the same SOIN

import sys
from collections import deque
import datetime


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
    def __init__(self, graph_obj, core_constraints, temporal_constraints, hypothesis, 
                     qvar_filler = None, unfilled = None, unfillable = None):
        # the following data is not changed, and is kept just for info
        self.graph_obj = graph_obj
        self.core_constraints = core_constraints
        # temporal constraints: mapping queryvariable -> {start_time: ..., end_time:...}
        self.temporal_constraints = temporal_constraints
        # the following data is changed.
        # flags: am I done?
        self.done = False
        
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

    # finalize:
    # report failed queries ot the underlying AidaHypothesis object
    def finalize(self):

        self.hypothesis.add_failed_queries( list(map( lambda ix: self.core_constraints[ix], self.unfillable)) )

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

                retv.append(OneClusterSeed(self.graph_obj, self.core_constraints, self.temporal_constraints, new_hypothesis, 
                       new_qvar_filler, new_unfilled, new_unfillable))
                

        if len(retv) == 0:
            # all the fillers were filtered away
            self.unfilled.remove(nfc["index"])
            self.unfillable.add(nfc["index"])
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
        # HIER
        if len(retv) == 0 and has_temporal_constraint:
           retv, has_temporal_constraint = self._extend_withvariable(nfc, 1)
        ## if len(retv) == 0 and has_temporal_cosntraint:
        ##     retv, has_temporal_constraint = self._extend_withvariable(nfc, 2)
        
        return retv

    # nfc is a structure with entries "predicate", "role", "erelabel", "variable"
    # find statements that match this constraint, and
    # return a pair (hyp, has_temporal_cosntraint) where
    # hyp is a list of triples; (extended hypothesis, query_variable, filler)
    # and has_temporal_constraint is true if there was at least one temporal constraint that didn't get matched
    def _extend_withvariable(self, nfc, leeway = 0):

        print("HIER leeway", leeway)
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

            # determine the entity that fills the role that has the variable
            filler = self.graph_obj.thegraph[stmtlabel][otherrole]

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

        # make seed clusters
        self.hypotheses = self._make_seeds()


    # export hypotheses to AidaHypothesisCollection
    def finalize(self):
        hypotheses_for_export = [ h.finalize() for h in self.hypotheses ]
        return AidaHypothesisCollection( hypotheses_for_export)
        
    # create initial cluster seeds.
    # this is called from __init__
    def _make_seeds(self):
        hypotheses_todo = deque()
        hypotheses_done = [ ]

        # initialize deque with one core hypothesis per facet
        for facet_index, facet in enumerate(self.soin_obj["facets"]):

            # start a new hypothesis
            core_hyp = OneClusterSeed(self.graph_obj, facet["queryConstraints"], self._pythonize_datetime(facet.get("temporal", {})), AidaHypothesis(self.graph_obj))
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
