################################
# Tools for working with json format AIDA graphs


import json
import re

class AidaJson:
    def __init__(self, json_obj):
        self.json_obj = json_obj
        self.thegraph = json_obj["theGraph"]

    ###############################
    ###
    # given an ERE label, return labels of all adjacent statements
    # with the given predicate and where erelabel is an argument in the given ererole (subject, object)
    def each_ere_adjacent_stmt(self, erelabel, predicate, ererole):
        if erelabel not in self.thegraph:
            return

        for stmtlabel in self.thegraph[erelabel].get("adjacent", []):
            if stmtlabel in self.thegraph and \
              self.thegraph[stmtlabel][ererole] == erelabel and \
              self.thegraph[stmtlabel]["predicate"] == predicate:
                yield stmtlabel


    ###
    # return a dictionary that characterizes the given ERE in terms of:
    # - ere type (nodetype)
    # - names ("name")
    # - type statements associated ("typestmt")
    # - affiliation in terms of APORA ("affiliation")
    def ere_characterization(self, erelabel):
        retv = { }

        if erelabel in self.thegraph:
            retv["label"] = erelabel
            retv["nodetype"] = self._shorten_label(self.thegraph[erelabel]["type"])

            retv["typestmt"] = ", ".join(set(self._shorten_label(self.thegraph[stmtlabel]["object"]) \
                                            for stmtlabel in self.each_ere_adjacent_stmt(erelabel, "type", "subject")))

            names = set()
            for stmtlabel in self.each_ere_adjacent_stmt(erelabel, "type", "subject"):
                names.update(self._english_names(self.thegraph[erelabel].get("name", [])))

            retv["name"] = ", ".join(names)

            affiliations = set() 
            for affiliatestmtlabel in self.each_ere_adjacent_stmt(erelabel, "GeneralAffiliation.APORA_Affiliate", "object"):
                relationlabel = self.thegraph[affiliatestmtlabel]["subject"]
                for affiliationstmtlabel in self.each_ere_adjacent_stmt(relationlabel, "GeneralAffiliation.APORA_Affiliation", "subject"):
                    affiliationlabel = self.thegraph[affiliationstmtlabel]["object"]
                    affiliations.update(self._english_names(self.thegraph[affiliationlabel].get("name", [ ])))

            retv["affiliation"] = ", ".join(affiliations)

        return retv

    ####
    def print_ere_characterization(self, erelabel, fout, short=False):
        characterization = self.ere_characterization(erelabel)
        if short:
            print("\t label :", characterization["label"], file = fout)
        else:
            for key in ["label", "nodetype", "name", "typestmt", "affiliation"]:
                if key in characterization and characterization[key] != "":
                    print("\t", key, ":", characterization[key], file = fout)
                    
    ####
    # print characterization of a given statement in terms of:
    # predicate, subject, object
    # subject and object can be strings or ERE characterizations
    def print_statement_info(self, stmtlabel, fout):
        if stmtlabel not in self.thegraph:
            return

        node = self.thegraph[stmtlabel]

        print("---", file = fout)
        print("Statement", stmtlabel, file = fout)
        for label in ["subject", "predicate", "object"]:
            if node[label] in self.thegraph:
                print(label, ":", file = fout)
                self.print_ere_characterization(node[label], fout, short = (node["predicate"] == "type"))
            else:
                print(label, ":", self._shorten_label(node[label]), file = fout)
        print("\n", file = fout)

    ####
    # Given a set of statement labels, sort the labels for more human-friendly output:
    # group all statements that refer to the same event
    def sorted_statements_for_output(self, stmtset):
        # map from event labels to statement that mention them
        event_stmt = { }
        for stmtlabel in stmtset:
            node = self.thegraph.get(stmtlabel, None)
            if node is None: continue
            for rel in ["subject", "object"]:
                if node[rel] in self.thegraph and self.thegraph[node[rel]].get("type", None) == "Event":
                    if node[rel] not in event_stmt:
                        event_stmt[ node[rel]] = set()
                    event_stmt[ node[rel] ].add(stmtlabel)

        # put statements in output list in order of events that mention them
        stmts_done = set()
        retv = [ ]
        for stmts in event_stmt.values():
            for stmt in stmts:
                if stmt not in stmts_done:
                    stmts_done.add(stmt)
                    retv.append(stmt)

        # and statements that don't mention events
        for stmt in stmtset:
            if stmt not in stmts_done:
                stmts_done.add(stmt)
                retv.append(stmt)

        return retv


    ###############################

    ###
    # retain only names that are probably English
    def _english_names(self, labellist):
        return [label for label in labellist if re.search(r"^[A-Za-z0-9\-,\.\'\"\(\)\? ]+$", label)]

    ###
    # given a label, shorten it for easier reading
    def _shorten_label(self, label):
        return label.split("/")[-1]

