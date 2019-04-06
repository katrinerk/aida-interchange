# Katrin Erk April 2019
#
# Class for filtering hypotheses for logical consistency
# Rule-based filtering

import sys

class AidaHypothesisFilter:
    def __init__(self, thegraph):
        self.thegraph = thegraph

    # okay to add this statement to the hypothesis?
    def validate(self, hypothesis, stmt):
        return True
