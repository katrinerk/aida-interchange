import sys

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

    #####
    # extending a hypothesis: adding a statement outright,
    # or making a new hypothesis and adding the statement there
    def add_stmt(self, stmtlabel, core = False):
        if core:
            self.core_stmts.add(stmtlabel)

        self.stmts.add(stmtlabel)

    def extend(self, stmtlabel, core = False):
        new_hypothesis = self.copy()
        new_hypothesis.add_stmt(stmtlabel, core = core)
        return new_hypothesis

    def copy(self):
        return AidaHypothesis(self.graph_obj, self.stmts.copy(), self.core_stmts.copy())

    ########
    # readable output: return EREs in this hypothesis, and the statements associated with them
    def to_s(self):
        retv = ""

        retv += ", ".join(self.stmts) + "\n\n"

        # make output for each event or relation in the hypothesis
        for ere_id in self.eres():
            if self.graph_obj.is_event(ere_id) or self.graph_obj.is_relation(ere_id):
                retv += self.nodetype(ere_id) + " " + ere_id + "\n"

                # add type information if present
                for typelabel in self.ere_each_type(ere_id):
                    retv += "ISA: " + typelabel + "\n"

                # add argument information:
                # first sort by argument label
                arg_values = { }
                for arglabel, value in self.eventrelation_each_argument(ere_id):
                    if arglabel not in arg_values: arg_values[arglabel] = set()
                    arg_values[ arglabel ].add(value)

                # then add to retv
                for arglabel, values in arg_values.items():
                    retv += "\n  " + arglabel + "\n"
                    prefix = "    "
                    for arg_id in values:
                        # print info on this argument
                        retv += prefix + self.nodetype(arg_id) + " " + arg_id + "\n"

                        # add type information if present
                        for typelabel in self.ere_each_type(arg_id):
                            retv += prefix + "ISA: " + typelabel + "\n"

                        # print string labels, if any
                        names = self.graph_obj.english_names(self.graph_obj.ere_names(arg_id))
                        if len(names) > 0:
                            retv += prefix + "names: " + ", ".join(names) + "\n"
        return retv

    #############
    # access functions

    # list of EREs adjacent to the statements in this hypothesis
    def eres(self):
        return list(set(nodelabel for stmtlabel in self.stmts for nodelabel in self.graph_obj.statement_args(stmtlabel) \
                        if self.graph_obj.is_ere(nodelabel)))


    # iterate over arguments of an event or relation in this hypothesis
    # yield pairs of (argument label, ERE ID
    def eventrelation_each_argument(self, eventrel_id):
        if not (self.graph_obj.is_event(eventrel_id) or self.graph_obj.is_relation(eventrel_id)):
            return

        for stmtlabel in self.graph_obj.each_ere_adjacent_stmt_anyrel(eventrel_id):
            if stmtlabel in self.stmts:
                stmt = self.graph_obj.thegraph[stmtlabel]
                if stmt["subject"] == eventrel_id and self.graph_obj.is_ere(stmt["object"]):
                    yield (stmt["predicate"], stmt["object"])
            

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


