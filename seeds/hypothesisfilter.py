# Katrin Erk April 2019
#
# Class for filtering hypotheses for logical consistency
# Rule-based filtering

import sys

class AidaHypothesisFilter:
    def __init__(self, thegraph):
        self.graph_obj = thegraph


    # ERE should have at most one affiliation statement
    def ere_one_affiliation_stmt(self, hypothesis, ere_id):
        
        return len(list(hypothesis.ere_each_affiliation(ere_id))) <= 1
            

 
    # All attackers in a conflict.attack event need to have one possible affiliation in common,
    # also all instruments,
    # and all attackers and instruments
    # (if there is no known affiliation that is also okay)
    def event_attack_attacker_instrument_compatible(self, hypothesis, ere_id):
        # Is this a Conflict.Attack event?
        if not self.graph_obj.is_event(ere_id): return True
        if "Conflict.Attack" not in self.graph_obj.possible_types(ere_id): return True
        attackers = list(hypothesis.eventrelation_each_argument_labeled(ere_id, "Conflict.Attack_Attacker"))
        instruments = list(hypothesis.eventrelation_each_argument_labeled(ere_id, "Conflict.Attack_Instrument"))

        attacker_affiliations_intersect = self._possible_affiliation_intersect(hypothesis, attackers)
        if attacker_affiliations_intersect is not None and len(attacker_affiliations_intersect) == 0:
            # print("HIER1 no intersection between attacker affiliations")
            return False

        instrument_affiliations_intersect = self._possible_affiliation_intersect(hypothesis, instruments)
        if instrument_affiliations_intersect is not None and len(instrument_affiliations_intersect) == 0:
            # print("HIER2 no intersection between instrument affiliations")
            return False
        
        if attacker_affiliations_intersect is not None and instrument_affiliations_intersect is not None and len(attacker_affiliations_intersect.intersection(instrument_affiliations_intersect)) == 0:
            return False

        return True

            
    ##########################################
    # main checking function
    # okay to add this statement to the hypothesis?
    def validate(self, hypothesis, stmt):

        tests = [
            self.ere_one_affiliation_stmt,
            self.event_attack_attacker_instrument_compatible
            ]

        for ere_id in hypothesis.eres_of_stmt(stmt):
            for test in tests:
                if not test(hypothesis, ere_id):
                    print("HIER hypothesis rejected esp", stmt)
                    print(hypothesis.to_s())
                    input("Press enter")
                    return False
                
        return True

    #######3
    # helper functions
    
    # intersection of possible affiliation IDs of EREs.
    # returns None if no known affiliations
    def _possible_affiliation_intersect(self, hypothesis, ere_ids):
        affiliations = None
        
        for ere_id in ere_ids:
            these_affiliations = set(hypothesis.ere_each_possible_affiliation(ere_id))
            if len(these_affiliations) > 0:
                if affiliations is None:
                    affiliations = these_affiliations
                else:
                    affiliations.intersection_update(these_affiliations)

        return affiliations
