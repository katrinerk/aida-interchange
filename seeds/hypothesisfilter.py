# Katrin Erk April 2019
#
# Class for filtering hypotheses for logical consistency
# Rule-based filtering

import sys

class AidaHypothesisFilter:
    def __init__(self, thegraph):
        self.graph_obj = thegraph


    ##############################################################
    # ERE tests
    # They return sets of problematic statements
    #######
    #
    ## # All attackers in a conflict.attack event need to have one possible affiliation in common,
    ## # also all instruments,
    ## # and all attackers and instruments
    ## # (if there is no known affiliation that is also okay).
    ## # Entities that are possible affiliates of any affiliation relation
    ## # are counted as their own affiliates.
    ## # For example, Ukraine counts as being affiliated with Ukraine.
    ## def event_attack_attacker_instrument_compatible(self, hypothesis, ere_id):
    ##     # BROKEN because I can't figure out which statements to flag as problematic
    ##     ##
    ##     # Is this a Conflict.Attack event?
    ##     # If not, no problem
    ##     if not self.graph_obj.is_event(ere_id): return [ ]
    ##     if all(not t.startswith("Conflict.Attack") for t in in self.graph_obj.possible_types(ere_id)):
    ##         return [ ]

    ##     # getting argument statements and argument EREs for attackers and instruments
    ##     attackers = list(hypothesis.eventrelation_each_argstmt_labeled_like(ere_id, "Conflict.Attack", "Attacker"))
    ##     instruments = list(hypothesis.eventrelation_each_argstmt_labeled_like(ere_id, "Conflict.Attack", "Instrument"))

    ##     # if there are multiple attackers but no joint affiliation: problem
    ##     # BM
    ##     attacker_affiliations_intersect = self._possible_affiliation_intersect(hypothesis, attackers)
    ##     if attacker_affiliations_intersect is not None and len(attacker_affiliations_intersect) == 0:
    ##         # print("HIER1 no intersection between attacker affiliations")
    ##         return False

    ##     instrument_affiliations_intersect = self._possible_affiliation_intersect(hypothesis, instruments)
    ##     if instrument_affiliations_intersect is not None and len(instrument_affiliations_intersect) == 0:
    ##         # print("HIER2 no intersection between instrument affiliations")
    ##         return False
        
    ##     if attacker_affiliations_intersect is not None and instrument_affiliations_intersect is not None and len(attacker_affiliations_intersect.intersection(instrument_affiliations_intersect)) == 0:
    ##         # print("no intersection betwen attacker and instrument affiliations", attacker_affiliations_intersect, instrument_affiliations_intersect)
    ##         return False

    ##     # no problem here
    ##     return [ ]

            
    ##########################################
    # main checking function
    # okay to add this statement to the hypothesis?
    def validate(self, hypothesis, stmt):

        ere_tests = [
            # self.event_attack_attacker_instrument_compatible
            ]

        for ere_id in hypothesis.eres_of_stmt(stmt):
            for test in ere_tests:
                if not test(hypothesis, ere_id):
                    ## print("HIER hypothesis rejected esp", stmt)
                    ## print(hypothesis.to_s())
                    ## input("Press enter")
                    return False
                
        return True

    #############################################
    # other main function:
    # post-hoc, remove statements from the hypothesi that shouldn't be there
    def filter(self, hypothesis):
        return True
        

    #######3
    # helper functions
    
    # intersection of possible affiliation IDs of EREs.
    # returns None if no known affiliations
    #
    # input: pairs (argument statement, filler ERE)
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
