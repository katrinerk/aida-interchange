# Katrin Erk April 2019
#
# Class for filtering hypotheses for logical consistency
# Rule-based filtering

import sys
from collections import deque

from os.path import dirname, realpath
src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from seeds.aidahypothesis import AidaHypothesis

class AidaHypothesisFilter:
    def __init__(self, thegraph):
        self.graph_obj = thegraph


    ##############################################################
    # Tests
    # They take in a hypothesis and the statement (which is part of the hypothesis) to test.
    # They return False if there is a problem, and True otherwise
    # Assumed invariant: the hypothesis is error-free except for possibly this statement.
    # (This can be achieved by filtering as each new statement is added)
    
    #######
    #
    ## # All attackers in a conflict.attack event need to have one possible affiliation in common,
    ## # also all instruments,
    ## # and all attackers and instruments
    ## # (if there is no known affiliation that is also okay).
    ## # Entities that are possible affiliates of any affiliation relation
    ## # are counted as their own affiliates.
    ## # For example, Ukraine counts as being affiliated with Ukraine.
    def event_attack_attacker_instrument_compatible(self, hypothesis, test_stmt):

        # is stmt an event role of a conflict.attack event, specifically an attacker or instrument?
        if not self.graph_obj.is_eventrole_stmt(test_stmt):
            return True
        if not self.graph_obj.stmt_predicate(test_stmt).startswith("Conflict.Attack"):
            return True
        if not self.graph_obj.stmt_predicate(test_stmt).endswith("Instrument") or self.graph_obj.stmt_predicate(test_stmt).endswith("Attacker"):
            return True

        # this is an event role of a conflict.attack.
        # its subject is the event ERE.
        event_ere = self.graph_obj.stmt_subject(test_stmt)
        
        # getting argument EREs for attackers and instruments
        attackers = list(hypothesis.eventrelation_each_argument_labeled_like(event_ere, "Conflict.Attack", "Attacker"))
        instruments = list(hypothesis.eventrelation_each_argument_labeled_like(event_ere, "Conflict.Attack", "Instrument"))

        # if there are multiple attackers but no joint affiliation: problem
        attacker_affiliations_intersect = self._possible_affiliation_intersect(hypothesis, attackers)
        if attacker_affiliations_intersect is not None and len(attacker_affiliations_intersect) == 0:
            # print("HIER1 no intersection between attacker affiliations")
            return False

        instrument_affiliations_intersect = self._possible_affiliation_intersect(hypothesis, instruments)
        if instrument_affiliations_intersect is not None and len(instrument_affiliations_intersect) == 0:
            # print("HIER2 no intersection between instrument affiliations")
            return False
        
        if attacker_affiliations_intersect is not None and instrument_affiliations_intersect is not None and len(attacker_affiliations_intersect.intersection(instrument_affiliations_intersect)) == 0:
            # print("no intersection betwen attacker and instrument affiliations", attacker_affiliations_intersect, instrument_affiliations_intersect)
            return False

        # no problem here
        return True

    #######
    #
    # Don't have multiple types on an event or relation
    def single_type_per_eventrel(self, hypothesis, test_stmt):
        # potential problem only if this is a type statement
        if not self.graph_obj.is_typestmt(test_stmt):
            return True

        ere = self.graph_obj.stmt_subject(test_stmt)

        # no problem if we have an entity
        if self.graph_obj.is_entity(ere):
            return True

        # okay, we have an event or relation.
        # check whether this ere has another type
        if len(stmt for stmt in self.graph_obj.each_ere_adjacent_stmt(ere, "type", "subject")) > 1:
            return False

        return True
        
    #######
    #
    # Don't have multiple affiliations of the exact same subtype for the same ERE
    # NOT FINISHED
    
    ##########################################
    # main checking function
    # check one single statement, which is part of the hypothesis.
    # assumption: this statement is the only potentially broken statement in the hypothesis
    def validate(self, hypothesis, stmt):

        tests = [
            self.event_attack_attacker_instrument_compatible,
            self.single_type_per_eventrel
            ]

        for test_okay in tests:
            if not test_okay(hypothesis, stmt):
                ## print("HIER hypothesis rejected esp", stmt)
                ## print(hypothesis.to_s())
                ## input("Press enter")
                return False
                
        return True

    #############################################
    # other main function:
    # post-hoc, remove statements from the hypothesis that shouldn't be there.
    # do this by starting a new hypothesis and re-inserting statements there by statement weight,
    # using the validate function
    def filtered(self, hypothesis):

        # new hypothesis: "incremental" because we add in things one at a time.
        # start with the core statements
        incr_hypothesis = AidaHypothesis(self.graph_obj, stmts = hypothesis.core_stmts.copy(),
                                             core_stmts = hypothesis.core_stmts.copy(),
                                             stmt_weights = dict((stmt, wt) for stmt, wt in hypothesis.stmt_weights.items() if stmt in hypothesis.core_stmts),
                                             lweight = hypothesis.lweight)
        incr_hypothesis.add_failed_queries(hypothesis.failed_queries)
        incr_hypothesis.add_qvar_filler(hypothesis.qvar_filler)
        incr_hypothesis_eres = set(incr_hypothesis.eres())

        # all other statements are candidates, sorted by their weights in the hypothesis, highest first
        candidates = [ stmt for stmt in hypothesis.stmts if stmt not in hypothesis.core_stmts]
        candidates.sort(key = lambda stmt:hypothesis.stmt_weights[stmt], reverse = True)
        candidates = deque(candidates)

        # candidates are set aside if they currently don't connect to any ERE in the incremental hypothesis
        candidates_set_aside = deque()

        def insert_candidate(stmt):
            incr_hypothesis.add_stmt(stmt, weight = hypothesis.stmt_weights[stmt])
            for nodelabel in [ self.graph_obj.stmt_subject(stmt), self.graph_obj.stmt_object(stmt) ]:
                if self.graph_obj.is_ere(nodelabel):
                    incr_hypothesis_eres.add(nodelabel)

        def check_candidates_set_aside():
            for stmt in candidates_set_aside:
                if self.graph_obj.stmt_subject(stmt) in incr_hypothesis_eres or self.graph_obj.stmt_object(stmt) in incr_hypothesis_eres:
                    # yes, check now whether this candidate should be inserted
                    candidates_set_aside.remove( stmt)
                    if self.validate(incr_hypothesis, stmt):
                        insert_candidate(stmt)
            

        while len(candidates) > 0:
            # any set-aside candidates that turn out to be connected to the hypothesis after all?
            check_candidates_set_aside()

            # now test the next non-set-aside candidate
            stmt = candidates.popleft()
            if self.validate(incr_hypothesis, stmt):
                insert_candidate(stmt)

        # no candidates left in the candidate set, but maybe something from the set-aside candidate list
        # has become connected to the core by the last candidate to be added
        check_candidates_set_aside()
        
        return incr_hypothesis
        

    #######3
    # helper functions
    
    # intersection of possible affiliation IDs of EREs.
    # returns None if no known affiliations
    #
    # input: list of filler EREs
    def _possible_affiliation_intersect(self, hypothesis, ere_ids):
        affiliations = None
        
        for ere_id in ere_ids:
            these_affiliations = set(hypothesis.ere_each_possible_affiliation(ere_id))
            if hypothesis.ere_possibly_isaffiliation(ere_id):
                these_affiliations.add(ere_id)
            if len(these_affiliations) > 0:
                if affiliations is None:
                    affiliations = these_affiliations
                else:
                    affiliations.intersection_update(these_affiliations)

        return affiliations
