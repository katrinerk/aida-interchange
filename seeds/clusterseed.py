# Katrin Erk March 2019
# Rule-based creation of initial hypotheses
# This only add the statements that the Statement of Information Need asks for,
# but constructs all possible cluster seeds that can be made using different statements
# that all fill the same SOIN

import sys
from collections import deque



from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from  aif import AidaJson
from seeds.aidahypothesis import AidaHypothesis, AidaHypothesisCollection
from seeds.hypothesisfilter import AidaHypothesisFilter

#########
# class that holds a single cluster seed.
# just a data structure, doesn't do much.
class OneClusterSeed:
    def __init__(self, graph_obj, core_constraints, hypothesis, 
                     qvar_filler = None, unfilled = None, unfillable = None):
        # the following data is not changed, and is kept just for info
        self.graph_obj = graph_obj
        self.core_constraints = core_constraints
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

        # print("HIER qvar filler", self.qvar_filler)
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
        # find statements that match this constraint
        retv = [ ]

        # determine the constraint that we are matching
        # and remove it from the list of unfilled constraints
        constraint = self.core_constraints[ nfc["index"] ]

        if len(nfc["stmt"]) == 0:
            # did not find any fillers after all
            # no change to qvar_filler
            self.unfilled.remove(nfc["index"])
            self.unfillable.add(nfc["index"])
            return [self ]

        for stmtlabel in nfc["stmt"]:
            if stmtlabel not in self.graph_obj.thegraph:
                print("Error in ClusterSeed: unexpectedly did not find statement", stmtlabel)
                continue

            # can this statement be added to the hypothesis without contradiction?
            # extended hypothesis
            new_hypothesis = self.hypothesis.extend(stmtlabel, core = True)
            
            if self.filter.validate(new_hypothesis, stmtlabel):
                # yes: make a new OneClusterSeed object with this extended hypothesis

                # possible change to qvar_filler
                new_qvar_filler = self.qvar_filler.copy()
                otherrole = self._nfc_otherrole(nfc)
                if otherrole is not None:
                    filler = self.graph_obj.thegraph[stmtlabel][otherrole]
                    if self.graph_obj.is_ere(filler):
                        new_qvar_filler[ nfc["variable"]] = filler

                # changes to unfilled, not to unfillable
                new_unfilled = self.unfilled.difference([nfc["index"]])
                new_unfillable = self.unfillable.copy()
                
                retv.append(OneClusterSeed(self.graph_obj, self.core_constraints, new_hypothesis, 
                   new_qvar_filler, new_unfilled, new_unfillable))
                

        if len(retv) == 0:
            # none of the possible fillers for this constraint worked -- or there were none.
            # put the current constraint in the list of unfillable constraints
            self.info["unfillable_core_constraints"].append(constraint)
            retv = [ self ]

        return retv
        
    # next fillable constraint from the core constraints list,
    # or None if none fillable
    def _next_fillable_constraint(self):
        for constraint_index in self.unfilled:
            
            subj, pred, obj = self.core_constraints[constraint_index]
            
            if subj in self.graph_obj.thegraph:
                return {
                    "index" : constraint_index,
                    "stmt" : list(self.graph_obj.each_ere_adjacent_stmt(subj, pred, "subject")),
                    "variable" : obj,
                    "role" : "subject"
                    }
                    
            elif subj in self.qvar_filler:
                return {
                    "index" : constraint_index,
                    "stmt" : list(self.graph_obj.each_ere_adjacent_stmt(self.qvar_filler[subj], pred, "subject")),
                    "variable": obj,
                    "role" : "subject"
                    }
        
            elif obj in self.graph_obj.thegraph:
                return {
                    "index" : constraint_index,
                    "stmt" : list(self.graph_obj.each_ere_adjacent_stmt(obj, pred, "object")),
                    "variable": subj,
                    "role" : "object"
                    }

            elif obj in self.qvar_filler:
                return {
                    "index" : constraint_index,
                    "stmt" : list(self.graph_obj.each_ere_adjacent_stmt(self.qvar_filler[obj], pred, "object")),
                    "variable": subj,
                    "role" : "object"
                    }

        return None

    def _nfc_otherrole(self, nfc):
        if nfc["role"] == "subject":
            return "object"
        elif nfc["role"] == "object":
            return "subject"
        else:
            print("ClusterSeed error: unknown role", nfc["role"])
            return None
        
    def core_constraints_remaining(self):
        return len(self.unfilled) > 0

        
        
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
            core_hyp = OneClusterSeed(self.graph_obj, facet["queryConstraints"], AidaHypothesis(self.graph_obj))
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
 
