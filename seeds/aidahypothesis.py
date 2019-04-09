# Katrin Erk April 2019
# Simple class for keeping an AIDA hypothesis.
# As a data structure, a hypothesis is simply a list of statements.
# We additionally track core statements so they can be visualized separately if needed.
# The class also provides access functions to determine EREs that are mentioned in the hypothesis,
# as well as their types, arguments, etc.
# All this is computed dynamically and not kept in the data structure. 

import sys


########3
# one AIDA hypothesis
class AidaHypothesis:
    def __init__(self, graph_obj, stmts = None, core_stmts = None):
        self.graph_obj = graph_obj
        if stmts is None:
            self.stmts = set()
        else:
            self.stmts = stmts

        if core_stmts is None:
            self.core_stmts = set()
        else:
            self.core_stmts = core_stmts

        # failed queries are added from outside, as they are needed in the json object
        self.failed_queries = [ ]

    #####
    # extending a hypothesis: adding a statement outright,
    # or making a new hypothesis and adding the statement there
    def add_stmt(self, stmtlabel, core = False):
        if stmtlabel in self.stmts:
            return
        
        if core:
            self.core_stmts.add(stmtlabel)

        self.stmts.add(stmtlabel)

    def extend(self, stmtlabel, core = False):
        if stmtlabel in self.stmts:
            return self
        
        new_hypothesis = self.copy()
        new_hypothesis.add_stmt(stmtlabel, core = core)
        return new_hypothesis

    def copy(self):
        return AidaHypothesis(self.graph_obj, self.stmts.copy(), self.core_stmts.copy())


    ########
    # json output as a hypothesis
    # make a json object describing this hypothesis
    def to_json(self):
        return {
            "statements" : list(self.stmts),
            "failedQueries": self.failed_queries,
            "queryStatements" : list(self.core_stmts)
            }

    def add_failed_queries(self, failed_queries):
        self.failed_queries = failed_queries
    
    ########
    # readable output: return EREs in this hypothesis, and the statements associated with them
    # string for single ERE
    def ere_to_s(self, ere_id, prefix = "", withargs = True):
        if self.graph_obj.is_event(ere_id) or self.graph_obj.is_relation(ere_id):
            return self._eventrel_to_s(ere_id, withargs = withargs)
        elif self.graph_obj.is_entity(ere_id):
            return self._entity_to_s(ere_id)
        else:
            return ""

    def _entity_to_s(self, ere_id, prefix = ""):
        retv = ""
        # print info on this argument
        retv += prefix + self.nodetype(ere_id) + " " + ere_id + "\n"

        # add type information if present
        for typelabel in self.ere_each_type(ere_id):
            retv += prefix + "ISA: " + typelabel + "\n"

        # print string labels, if any
        names = self.entity_names(ere_id)
        if len(names) > 0:
            retv += prefix + "names: " + ", ".join(names) + "\n"

        return retv
        
    def _eventrel_to_s(self, ere_id, prefix = "", withargs = True):
        retv = ""
        if not (self.graph_obj.is_event(ere_id) or self.graph_obj.is_relation(ere_id)):
            return retv

        retv += prefix + self.nodetype(ere_id) + " " + ere_id + "\n"

        # add type information if present
        for typelabel in self.ere_each_type(ere_id):
            retv += prefix + "ISA: " + typelabel + "\n"

        # add argument information:
        if withargs:
            # first sort by argument label
            arg_values = { }
            for arglabel, value in self.eventrelation_each_argument(ere_id):
                if arglabel not in arg_values: arg_values[arglabel] = set()
                arg_values[ arglabel ].add(value)

            # then add to string
            for arglabel, values in arg_values.items():
                retv += "\n" + prefix + "  " + arglabel + "\n"
                additionalprefix = "    "
                for arg_id in values:
                    retv += prefix + self._entity_to_s(arg_id, prefix + additionalprefix)

        return retv

    # String for whole hypothesis
    def to_s(self):
        retv = ""

        retv += ", ".join(self.stmts) + "\n\n"

        # make output for each event or relation in the hypothesis
        for ere_id in self.eres():
            if self.graph_obj.is_event(ere_id) or self.graph_obj.is_relation(ere_id):
                retv += self.ere_to_s(ere_id) + "\n"
                        
        return retv

    # String for a statement
    def statement_to_s(self, stmtlabel):
        if stmtlabel not in self.stmts:
            return ""

        retv = ""
        stmt = self.graph_obj.thegraph[stmtlabel]
        retv += "Statement " + stmtlabel + "\n"
        
        retv += "Subject:\n " 
        if self.graph_obj.is_node(stmt["subject"]):
            retv += self.ere_to_s(stmt["subject"], withargs = False, prefix = "    ") + "\n"
        else:
            retv += stmt["subject"] + "\n"

        retv += "Predicate: " + stmt["predicate"] + "\n"

        retv += "Object:\n " 
        if self.graph_obj.is_node(stmt["object"]):
            retv += self.ere_to_s(stmt["object"], withargs = False, prefix = "    ") + "\n"
        else:
            retv += stmt["object"] + "\n"
        

    #############
    # access functions

    # list of EREs adjacent to the statements in this hypothesis
    def eres(self):
        return list(set(nodelabel for stmtlabel in self.stmts for nodelabel in self.graph_obj.statement_args(stmtlabel) \
                        if self.graph_obj.is_ere(nodelabel)))

    def eres_of_stmt(self, stmtlabel):
        if stmtlabel not in self.stmts:
            return [ ]
        else:
            return list(set(nodelabel for nodelabel in self.graph_obj.statement_args(stmtlabel) \
                        if self.graph_obj.is_ere(nodelabel)))


    # iterate over arguments of an event or relation in this hypothesis
    # yield pairs of (argument label, ERE ID)
    def eventrelation_each_argument(self, eventrel_id):
        if not (self.graph_obj.is_event(eventrel_id) or self.graph_obj.is_relation(eventrel_id)):
            return

        for stmtlabel in self.graph_obj.each_ere_adjacent_stmt_anyrel(eventrel_id):
            if stmtlabel in self.stmts:
                stmt = self.graph_obj.thegraph[stmtlabel]
                if stmt["subject"] == eventrel_id and self.graph_obj.is_ere(stmt["object"]):
                    yield (stmt["predicate"], stmt["object"])

    def eventrelation_each_argument_labeled(self, eventrel_id, rolelabel):
        for thisrolelabel, filler in self.eventrelation_each_argument(eventrel_id):
            if thisrolelabel == rolelabel:
                yield filler
            

    # types of an ERE node in this hypothesis
    def ere_each_type(self, ere_id):
        if not self.graph_obj.is_ere(ere_id):
            return
        for stmtlabel in self.graph_obj.each_ere_adjacent_stmt(ere_id, "type", "subject"):
            if stmtlabel in self.stmts:
                yield self.graph_obj.shorten_label(self.graph_obj.thegraph[stmtlabel]["object"])
            
        
    
    # node type: Entity, Event, Relation, Statement
    def nodetype(self, nodelabel):
        if self.graph_obj.is_node(nodelabel):
            return self.graph_obj.thegraph[nodelabel]["type"]
        else:
            return None

    # names of an entity
    def entity_names(self, ere_id):
        return self.graph_obj.english_names(self.graph_obj.ere_names(ere_id))


    # possible affiliations of an ERE:
    # yield ERE that is the affiliation
    def ere_each_possible_affiliation(self, ere_id):
        # go through possible affiliation statements where this ERE is the object
        for stmtlabel in self.graph_obj.each_ere_adjacent_stmt(ere_id, "GeneralAffiliation.APORA_Affiliate", "object"):
            rel_id = self.graph_obj.thegraph[stmtlabel]["subject"]
            for otherstmtlabel in self.graph_obj.each_ere_adjacent_stmt(rel_id, "GeneralAffiliation.APORA_Affiliation", "subject"):
                affiliation_id = self.graph_obj.thegraph[otherstmtlabel]["object"]
                yield affiliation_id

    # actual affiliations of an ERE in this hypothesis
    def ere_each_affiliation(self, ere_id):
        # go through possible affiliation statements where this ERE is the object
        for stmtlabel in self.graph_obj.each_ere_adjacent_stmt(ere_id, "GeneralAffiliation.APORA_Affiliate", "object"):
            if stmtlabel not in self.stmts:
                continue
            
            rel_id = self.graph_obj.thegraph[stmtlabel]["subject"]
            for otherstmtlabel in self.graph_obj.each_ere_adjacent_stmt(rel_id, "GeneralAffiliation.APORA_Affiliation", "subject"):
                if otherstmtlabel not in self.stmts:
                    continue
                
                affiliation_id = self.graph_obj.thegraph[otherstmtlabel]["object"]
                yield affiliation_id
                
############3
# collection of hypotheses, after initial cluster seed generation has been done
class AidaHypothesisCollection:
    def __init__(self, hypotheses):
        self.hypotheses = hypotheses

    # compile json object that lists all the hypotheses with their statements
    def to_json(self):
       
        # make a json in the right format.
        # entries: "probs", "support". "probs": add dummy uniform probabilities
        json_out = { "probs": [ 1.0 / len(self.hypotheses) ] * len(self.hypotheses),
                     "support" : [ ]
                   }
        for hyp in self.hypotheses:
            json_out["support"].append(hyp.to_json())

        return json_out

    # make a list of strings with the new cluster seeds in readable form
    def to_s(self):
        return [ hyp.to_s() for hyp in self.hypotheses ]
        
