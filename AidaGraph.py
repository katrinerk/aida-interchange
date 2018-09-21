"""builds on RDFGraph, has higher-level access"""

import queue
import json

from RDFGraph import RDFGraph, RDFNode


omit_labels = ("system", "confidence", "privateData", "justifiedBy")


class AidaNode(RDFNode):
    """a node: a ttl node, extended by domain-specific stuff"""
    def __init__(self, nodename):
        RDFNode.__init__(self, nodename)
        self.description = None

    def add_description(self, description):
        self.description = description

    def prettyprint(self, omit=omit_labels):
        super().prettyprint(omit=omit)
        if self.description is not None:
            print("\t", "descr :", self.description)

    def has_type(self, targettype, shorten=True):
        """if the node has type of targettype"""
        return targettype in self.get("type", shorten=shorten)

    def is_entity(self):
        """if the node is an Entity"""
        return self.has_type("Entity", shorten=True)

    def is_relation(self):
        """if the node is a Relation"""
        return self.has_type("Relation", shorten=True)

    def is_event(self):
        """if the node is an Event"""
        return self.has_type("Event", shorten=True)

    def is_ere(self):
        """if the node is an Entity / Relation / Event"""
        return self.is_entity() or self.is_relation() or self.is_event()

    def is_statement(self):
        """if the node is a Statement"""
        return self.has_type("Statement", shorten=True)

    def is_sameas_cluster(self):
        """if the node is a SameAsCluster"""
        return self.has_type("SameAsCluster", shorten=True)

    def is_cluster_membership(self):
        """if the node is a ClusterMembership statement"""
        return self.has_type("ClusterMembership", shorten=True)


    def has_predicate(self, pred, shorten=False):
        """if the node has a predicate relation to a node with label pred"""
        return pred in self.get("predicate", shorten=shorten)

    def has_subject(self, subj, shorten=False):
        """if the node has a subject relation to a node with label subj"""
        return subj in self.get("subject", shorten=shorten)

    def has_object(self, obj, shorten=False):
        """if the node has an object relation to a node with label obj"""
        return obj in self.get("object", shorten=shorten)

    def is_type_statement(self, nodelabel=None):
        """if the node is a Statement specifying the type of nodelabel"""
        if self.is_statement() and self.has_predicate("type", shorten=True):
            if nodelabel is None or self.has_subject(nodelabel, shorten=False):
                return True
        return False

    def is_kbentry_statement(self, nodelabel=None):
        """if the node is a Statement specifying the type of nodelabel"""
        if self.is_statement() and self.has_predicate("hasKBEntry", shorten=True):
            if nodelabel is None or self.has_subject(nodelabel, shorten=False):
                return True
        return False


################################
# info classes: returned by AidaGraph,
# include node info as well as pre-parsed domain-specific info

# a typing statement
class AidaTypeInfo:
    def __init__(self, typenode):
        # type label
        self.typenode = typenode
        self.typelabels = self.typenode.get("object", shorten=True)


# a KB entry
class AidaKBEntryInfo:
    def __init__(self, kbentrynode):
        self.kbentrynode = kbentrynode
        self.kbentry = self.kbentrynode.get("object", shorten=True)


# a node's neighbor, with the edge label between them and the direction of the edge
class AidaNeighborInfo:
    def __init__(self, thisnodelabel, neighbornodelabel, role, direction):
        self.thisnodelabel = thisnodelabel
        self.neighbornodelabel = neighbornodelabel
        self.role = role
        assert direction in ["<", ">"]
        self.direction = direction

    def inverse_direction(self):
        if self.direction == "<":
            return ">"
        else:
            return "<"

    def __str__(self):
        return self.direction + RDFNode.shortlabel(self.role) + \
               self.direction + " " + RDFNode.shortlabel(self.neighbornodelabel)


# characterization of an entity or event in terms of its types,
# arguments, and events
class AidaWhoisInfo:
    def __init__(self, node):
        self.node = node
        self.type_conf_info = {}
        self.kbentry_info = set()
        self.inedge_info = []
        self.outedge_info = []

    # for each type of this ere, keep only the maximum observed confidence level,
    # but do be prepared to keep multiple types
    def add_type(self, type_info, conflevels):
        for typelabel in type_info.typelabels:
            self.type_conf_info[typelabel] = max(
                max(conflevels), self.type_conf_info.get(typelabel, 0))

    def add_kbentry(self, kbentry_info):
        self.kbentry_info = self.kbentry_info.union(kbentry_info.kbentry)

    def add_inedge(self, pred, node, whois_info):
        self.inedge_info.append((pred, node, whois_info))

    def add_outedge(self, pred, node, whois_info):
        self.outedge_info.append((pred, node, whois_info))

    def prettyprint(self, indent=0, omit=[]):
        # node type and predicate
        if self.node is not None:
            print("\t" * indent, "Node", self.node.shortname())

            if self.node.is_statement():
                print("\t" * indent, "pred:",
                      ",".join(self.node.get("predicate", shorten=True)))
            else:
                print("\t" * indent, "isa:",
                      ",".join(self.node.get("type", shorten=True)))
            if self.node.description is not None:
                print("\t" * indent, "Descr :", self.node.description)

        # type info
        if len(self.type_conf_info) > 0:
            print("\t"*indent, "types:",
                  ", ".join(t + "(conf=" + str(c) + ")" for t, c
                            in self.type_conf_info.items()))

        # KB entries
        if len(self.kbentry_info) > 0:
            print("\t"*indent, "KB entries:", ", ".join(self.kbentry_info))

        # incoming edges
        if len(self.inedge_info) > 0:
            for pred, node, whois_info in self.inedge_info:
                if node.name not in omit:
                    print("\t"*indent,
                          "<" + RDFNode.shortlabel(pred) + "<",
                          node.shortname())
                    whois_info.prettyprint(indent=indent + 1, omit=omit + [self.node.name])

        # outgoing edges
        if len(self.outedge_info) > 0:
            for pred, node, whois_obj in self.outedge_info:
                if node.name not in omit:
                    print("\t"*indent,
                          ">" + RDFNode.shortlabel(pred) + ">",
                          node.shortname())
                    whois_obj.prettyprint(indent=indent + 1, omit=omit + [self.node.name])


class AidaGraph(RDFGraph):

    def __init__(self, nodeclass=AidaNode):
        RDFGraph.__init__(self, nodeclass=nodeclass)

    # judge whether a node label exists in the graph
    def has_node(self, nodelabel):
        return nodelabel in self.node_dict

    # access method for a single node by its label
    def get_node(self, nodelabel):
        return self.node_dict.get(nodelabel, None)

    # iterator over the nodes.
    # optionally with a restriction on the type of the nodes returned
    def nodes(self, targettype=None):
        for node in self.node_dict.values():
            if targettype is None or node.has_type(targettype):
                yield node

    # given a node label, and a pred, return the list of object that go with it,
    # can be viewed as a composition of AidaGraph.node_labeled and RDFNode.get
    def get_node_objs(self, nodelabel, targetpred, shorten=False):
        node = self.get_node(nodelabel)
        if node:
            return node.get(targetpred=targetpred, shorten=shorten)
        else:
            return []

    # confidence level associated with a node. node given by its name
    def confidence_of(self, nodelabel):
        if not self.has_node(nodelabel):
            return None
        confidenceValues = set()

        for clabel in self.get_node_objs(nodelabel, "confidence"):
            for c in self.get_node_objs(clabel, "confidenceValue"):
                confidenceValues.add(float(c))

        return confidenceValues

    # iterator over types for a particular entity/event/relation
    # yields AidaTypeInfo objects that give access ot the whole typing node
    def types_of(self, nodelabel):
        if self.has_node(nodelabel):
            for pred, subjs in self.get_node(nodelabel).inedge.items():
                for subj in subjs:
                    subjnode = self.get_node(subj)
                    if subjnode and subjnode.is_type_statement(nodelabel):
                        yield AidaTypeInfo(subjnode)

    # iterator over knowledge base entries of a node
    def kbentries_of(self, nodelabel):
        if self.has_node(nodelabel):
            for pred, subjs in self.get_node(nodelabel).inedge.items():
                for subj in subjs:
                    subjnode = self.get_node(subj)
                    if subjnode and subjnode.is_kbentry_statement(nodelabel):
                        yield AidaKBEntryInfo(subjnode)

    # iterator over mentions associated with the statement node
    def mentions_associated_with(self, nodelabel):
        if not self.has_node(nodelabel) or \
                not self.get_node(nodelabel).is_statement():
            return

        for jlabel in self.get_node_objs(nodelabel, "justifiedBy"):
            for plabel in self.get_node_objs(jlabel, "privateData"):
                for jsonstring in self.get_node_objs(plabel, "jsonContent"):
                    jobj = json.loads(jsonstring)
                    if "mention" in jobj:
                        yield jobj["mention"]

    # iterator over provenances associate with the statement node
    def provenances_associated_with(self, nodelabel):
        if not self.has_node(nodelabel) or \
                not self.get_node(nodelabel).is_statement():
            return

        for plabel in self.get_node_objs(nodelabel, "privateData"):
            for jsonstring in self.get_node_objs(plabel, "jsonContent"):
                jobj = json.loads(jsonstring)
                if "provenance" in jobj:
                    for p in jobj["provenance"]:
                        yield p

    # iterator over source document ids associate with the statement node
    def sources_associated_with(self, nodelabel):
        if not self.has_node(nodelabel) or \
                not self.get_node(nodelabel).is_statement():
            return

        for jlabel in self.get_node_objs(nodelabel, "justifiedBy"):
            for source in self.get_node_objs(jlabel, "source"):
                yield source

    # iterator over hypotheses supported by the statement node
    def hypotheses_supported(self, nodelabel):
        if not self.has_node(nodelabel) or \
                not self.get_node(nodelabel).is_statement():
            return

        for plabel in self.get_node_objs(nodelabel, "privateData"):
            for jsonstring in self.get_node_objs(plabel, "jsonContent"):
                jobj = json.loads(jsonstring)
                if "hypothesis" in jobj:
                    for h in jobj["hypothesis"]:
                        yield h

    # iterator over hypotheses partially supported by the statement node
    def hypotheses_partially_supported(self, nodelabel):
        if not self.has_node(nodelabel) or \
                not self.get_node(nodelabel).is_statement():
            return

        for plabel in self.get_node_objs(nodelabel, "privateData"):
            for jsonstring in self.get_node_objs(plabel, "jsonContent"):
                jobj = json.loads(jsonstring)
                if "partial" in jobj:
                    for h in jobj["partial"]:
                        yield h

    # iterator over hypotheses contradicted by the statement node
    def hypotheses_contradicted(self, nodelabel):
        if not self.has_node(nodelabel) or \
                not self.get_node(nodelabel).is_statement():
            return

        for plabel in self.get_node_objs(nodelabel, "privateData"):
            for jsonstring in self.get_node_objs(plabel, "jsonContent"):
                jobj = json.loads(jsonstring)
                if "contradicts" in jobj:
                    for h in jobj["contradicts"]:
                        yield h

    # iterator over conflicting hypotheses between two statements
    def conflicting_hypotheses(self, nodelabel_1, nodelabel_2):
        if not self.has_node(nodelabel_1) or \
                not self.get_node(nodelabel_1).is_statement():
            return

        if not self.has_node(nodelabel_2) or \
                not self.get_node(nodelabel_2).is_statement():
            return

        # hypotheses fully / partially supported by nodelabel_1
        supporting_hyp_1 = set(self.hypotheses_supported(nodelabel_1))
        supporting_hyp_1.update(
            set(self.hypotheses_partially_supported(nodelabel_1)))
        # hypotheses contradicted by nodelabel_1
        contradicting_hyp_1 = set(self.hypotheses_contradicted(nodelabel_1))

        # hypotheses fully / partially supported by nodelabel_2
        supporting_hyp_2 = set(self.hypotheses_supported(nodelabel_2))
        supporting_hyp_2.update(
            set(self.hypotheses_partially_supported(nodelabel_2)))
        # hypotheses contradicted by nodelabel_2
        contradicting_hyp_2 = set(self.hypotheses_contradicted(nodelabel_2))

        for h in supporting_hyp_1.intersection(contradicting_hyp_2):
            yield h
        for h in supporting_hyp_2.intersection(contradicting_hyp_1):
            yield h

    # iterator over neighbors of a node
    # that mention the label of the entity, or whose label is mentioned
    # in the entry of the entity
    # yields AidaNeighborInfo objects
    def neighbors_of(self, nodelabel):
        if not self.has_node(nodelabel):
            return

        for pred, objs in self.get_node(nodelabel).outedge.items():
            for obj in objs:
                yield AidaNeighborInfo(nodelabel, obj, pred, ">")
        for pred, subjs in self.get_node(nodelabel).inedge.items():
            for subj in subjs:
                yield AidaNeighborInfo(nodelabel, subj, pred, "<")

    # output a characterization of a node:
    # what is its type,
    # what events is it involved in (for an entity),
    # what arguments does it have (for an event)
    def whois(self, nodelabel, follow=2):
        if not self.has_node(nodelabel):
            return None

        node = self.get_node(nodelabel)
        
        whois_info = AidaWhoisInfo(node)

        # we do have an entry for this node.
        # determine its types
        for type_info in self.types_of(nodelabel):
            conflevel = self.confidence_of(type_info.typenode.name)
            if conflevel is not None:
                whois_info.add_type(type_info, conflevel)

        # determine KB entries
        for kbentry_info in self.kbentries_of(nodelabel):
            whois_info.add_kbentry(kbentry_info)

        if follow > 0:
            # we were asked to also explore this node's neighbors
            # explore incoming edges
            for pred, subjs in node.inedge.items():
                for subj in subjs:
                    if self.has_node(subj):
                        subjnode = self.get_node(subj)
                        if subjnode.has_predicate("type", shorten=True) or \
                                subjnode.has_predicate("hasKBEntry"):
                            # don't re-record typing nodes
                            continue
                        elif subjnode.is_statement():
                            whois_neighbor_info = self.whois(subj, follow=follow - 1)
                            whois_info.add_inedge(pred, subjnode, whois_neighbor_info)

            # explore outgoing edges
            for pred, objs in node.outedge.items():
                for obj in objs:
                    if self.has_node(obj):
                        objnode = self.get_node(obj)
                        if objnode.is_statement() or objnode.is_ere():
                            whois_neighbor_info = self.whois(obj, follow=follow - 1)
                            whois_info.add_outedge(pred, objnode, whois_neighbor_info)

        return whois_info

    # traverse: explore the whole reachable graph starting from
    # startnodelabel,
    # yields pairs (nodelabel, path)
    # where path is a list of AidaNeighborInfo objects, starting from startnodelabel
    def traverse(self, startnodelabel, omitroles=omit_labels):
        nodelabels_to_visit = queue.Queue()
        nodelabels_to_visit.put((startnodelabel, []))
        edges_visited = set()
        if not self.has_node(startnodelabel):
            return

        if omitroles is None:
            omitroles = set()

        while not nodelabels_to_visit.empty():
            current_label, current_path = nodelabels_to_visit.get()

            yield (current_label, current_path)

            for neighbor_info in self.neighbors_of(current_label):
                if neighbor_info.role in omitroles or \
                        RDFNode.shortlabel(neighbor_info.role) in omitroles:
                    continue
                visited = [
                    (current_label, neighbor_info.role,
                     neighbor_info.direction, neighbor_info.neighbornodelabel),
                    (neighbor_info.neighbornodelabel, neighbor_info.role,
                     neighbor_info.inverse_direction(), current_label)
                ]

                if any(v in edges_visited for v in visited):
                    pass
                else:
                    nodelabels_to_visit.put(
                        (neighbor_info.neighbornodelabel, current_path + [neighbor_info]))
                    for v in visited:
                        edges_visited.add(v)
