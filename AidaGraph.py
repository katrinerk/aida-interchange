###
# builds on RDFGraph, has higher-level access

import queue
import sys
import json

from RDFGraph import RDFGraph, RDFNode

import pprint

################################
# a node: a ttl node, extended by domain-specific stuff
class AidaNode(RDFNode):
    def __init__(self, nodename):
        RDFNode.__init__(self, nodename)
        self.description = None

    def add_description(self, description):
        self.description = description

    def prettyprint(self, omit = ["system", "confidence", "privateData", "justifiedBy"]):
        RDFNode.prettyprint(self, omit = omit)
        if self.description is not None:
            print("\t", "descr :", self.description)

    


################################
# info classes: returned by AidaGraph,
# include node info as well as pre-parsed domain-specific info

# a typing statement
class AidaTypeInfo:
    def __init__(self, typenode):
        # type label
        self.typenode = typenode
        self.typelabels = self.typenode.get("object", shorten = True)


# a KB entry
class AidaKBEntryInfo:
    def __init__(self, kbentrynode):
        self.kbentrynode = kbentrynode
        self.kbentry = self.kbentrynode.get("object", shorten= True)
        
# a node's neighbor, with the edge label between them and the direction of the edge
class AidaNeighborInfo:
    def __init__(self, thisnodelabel, neighbornodelabel, role, direction):
        self.thisnodelabel = thisnodelabel
        self.neighbornodelabel= neighbornodelabel
        self.role = role
        if direction not in ["<", ">"]: raise Error
        self.direction = direction

    def inverse_direction(self):
        if self.direction == "<": return ">"
        else: return "<"

# characterization of an entity or event in terms of its types,
# arguments, and events
class AidaWhoisInfo:
    def __init__(self):
        self.node = None
        self.type_info = { }
        self.kb_info = set()
        self.inedge_info = [ ]
        self.outedge_info = [ ]

    def add_node(self, node):
        self.node = node

    # for each type of this ere, keep only the maximum observed confidence level,
    # but do be prepared to keep multiple types
    def add_type(self, typeobj, conflevels):
        for typelabel in typeobj.typelabels:
            self.type_info[typelabel] = max(max(conflevels), self.type_info.get(typelabel, 0))

    def add_kbentry(self, kbobj):
        self.kb_info = self.kb_info.union(kbobj.kbentry)

    def add_inedge(self, pred, node, whois_obj):
        self.inedge_info.append( (pred, node, whois_obj))

    def add_outedge(self, pred, node, whois_obj):
        self.outedge_info.append( (pred, node, whois_obj))

    def prettyprint(self, indent = 0, omit = [ ]):
        # node type and predicate
        if self.node is not None:
            print("\t" * indent, "Node", self.node.shortname())
            
            if "Statement" in self.node.get("type", shorten=True):
                print("\t" * indent, "pred:", ",".join(self.node.get("predicate", shorten=True)))
            else:
                print("\t" * indent, "isa:", ",".join(self.node.get("type", shorten=True)))
            if self.node.description is not None:
                print("\t" * indent, "Descr :", self.node.description)
                
        # type info
        if len(self.type_info) > 0:
            print("\t"*indent, "types:", ", ".join(t + "(conf=" + str(c) + ")" for t, c in self.type_info.items()))
        # KB entries
        if len(self.kb_info) > 0:
            print("\t"*indent, "KB entries:", ", ".join(self.kb_info))
        # incoming edges
        if len(self.inedge_info) > 0:
            for pred, node, whois_obj in self.inedge_info:
                if node.name not in omit:
                    print("\t"*indent, "<" + node.shortlabel(pred) + "<", node.shortname())
                    whois_obj.prettyprint(indent = indent + 1, omit = omit + [self.node.name])
        # outgoing edges
        if len(self.outedge_info) > 0:
            for pred, node, whois_obj in self.outedge_info:
                if node.name not in omit:
                    print("\t"*indent, ">" + node.shortlabel(pred) + ">", node.shortname())
                    whois_obj.prettyprint(indent = indent + 1, omit= omit + [self.node.name])
        
        
        
#################################3
class AidaGraph(RDFGraph):

    def __init__(self, nodeclass = AidaNode):
        RDFGraph.__init__(self, nodeclass = nodeclass)
    
    # access method for a single node by its label
    def node_labeled(self, nodelabel):
        return self.node.get(nodelabel, None)
    
    # iterator over the nodes.
    # optionally with a restriction on the type of the nodes returned
    def nodes(self, targettype = None):
        for node in self.node.values():
            if targettype is None or targettype in node.get("type")  or targettype in node.get("type", shorten = True):
                yield node

    # confidence level associated with a node. node given by its name
    def confidence_of(self, nodename):
        if nodename not in self.node:
            return None
        confnodelabels = self.node[nodename].get("confidence")
        
        confidenceValues = set()
        for clabel in confnodelabels:
            if clabel in self.node:
                confidenceValues.update( float(c) for c in self.node[clabel].get("confidenceValue"))

        return confidenceValues

    # iterator over types for a particular entity/event/relation
    # yields AidaTypeInfo objects that
    # give access ot the whole typing node
    def types_of(self, obj):
        if obj in self.node:
            for pred, subjs in self.node[obj].inedge.items():
                for subj in subjs:
                    if subj in self.node:
                        subjnode = self.node[subj]
                        if "type" in subjnode.get("predicate", shorten = True) and obj in subjnode.get("subject"):
                            yield AidaTypeInfo(subjnode)

    # knowledge base entries of a node
    def kbentries_of(self, obj):
        if obj in self.node:
            for pred, subjs in self.node[obj].inedge.items():
                for subj in subjs:
                    if subj in self.node:
                        subjnode = self.node[subj]
                        if "hasKBEntry" in subjnode.get("predicate", shorten = True) and obj in subjnode.get("subject"):
                            yield AidaKBEntryInfo(subjnode)

    # mentions associated with this particular node
    def mentions_associated_with(self, subj):
        if subj in self.node:
            justifications = self.node[subj].get("justifiedBy")
            for jlabel in justifications:
                if jlabel in self.node:
                    privatelabels = self.node[jlabel].get("privateData")
                    for plabel in privatelabels:
                        if plabel in self.node:
                            mentionstrings = self.node[plabel].get("jsonContent")
                            for mentionstring in mentionstrings:
                                jobj = json.loads(mentionstring)
                                if "mention" in jobj:
                                    yield jobj["mention"]

    # source for a node
    def sources_associated_with(self, subj):
        if subj in self.node:
            private_data = self.node[subj].get("privateData")
            for plabel in private_data:
                if plabel in self.node:
                    strings = self.node[plabel].get("jsonContent")
                    for s in strings:
                        jobj = json.loads(s)
                        if "provenance" in jobj:
                            for p in jobj["provenance"]:
                                yield p
                        
                            
            
                
    ## # iterator over neighbors of a node
    # that mention the label of the entity, or whose label is mentioned
    # in the entry of the entity
    # yields AidaNeighborInfo objects
    def neighbors_of(self, subj):
        if subj not in self.node:
            return
        
        for pred, objs in self.node[subj].outedge.items():
            for obj in objs:
                yield AidaNeighborInfo(subj, obj, pred, ">")
        for pred, othersubjs in self.node[subj].inedge.items():
            for othersubj in othersubjs:
                yield AidaNeighborInfo(subj, othersubj, pred, "<")


    # output a characterization of a node:
    # what is its type,
    # what events is it involved in (for an entity),
    # what arguments does it have (for an event)
    def whois(self, nodelabel, follow = 2):
        if nodelabel not in self.node:
            return None
        
        whois_obj = AidaWhoisInfo()

        node = self.node[nodelabel]
        whois_obj.add_node(node)
        # we do have an entry for this node.
        # determine its types
        for type_obj in self.types_of(nodelabel):
            conflevel = self.confidence_of(type_obj.typenode.name)
            if conflevel is not None:
                whois_obj.add_type(type_obj, conflevel)

        # determine KB entries
        for kb_obj in self.kbentries_of(nodelabel):
            whois_obj.add_kbentry(kb_obj)

        if follow > 0:
            # we were asked to also explore this node's neighbors
            # explore incoming edges
            for pred, subjs in self.node[nodelabel].inedge.items():
                for subj in subjs:
                    if subj in self.node:
                        subjnode = self.node[subj]
                        if len(subjnode.get("predicate", shorten = True).intersection(["type", "hasKBEntry"])) > 0:
                            # don't re-record typing nodes
                            continue
                        elif "Statement" in subjnode.get("type", shorten=True):
                            whois_neighbor_obj = self.whois(subj, follow = follow - 1)
                            whois_obj.add_inedge(pred, subjnode, whois_neighbor_obj)

            # explore outgoing edges
            for pred, objs in self.node[nodelabel].outedge.items():
                for obj in objs:
                    if obj in self.node:
                        objnode = self.node[obj]
                        if len(objnode.get("type", shorten = True).intersection(["Statement", "Entity"])) > 0:
                            whois_neighbor_obj = self.whois(obj, follow = follow - 1)
                            whois_obj.add_outedge(pred, objnode, whois_neighbor_obj)

                    

        return whois_obj
            

    # traverse: explore the whole reachable graph starting from
    # startnodelabel,
    # yields pairs (nodelabel, path)
    # where path is a list of AidaNeighborInfo objects, starting from startnodelabel
    def traverse(self, startnodelabel, omitroles = ["system", "justifiedBy", "confidence", "privateData"]):
        nodelabels_to_visit = queue.Queue()
        nodelabels_to_visit.put((startnodelabel, []))
        edges_visited = set()
        if startnodelabel not in self.node:
            return
        
        startnode = self.node[startnodelabel]

        if omitroles is None:
            omitroles = set()

        while not(nodelabels_to_visit.empty()):
            current_label, current_path = nodelabels_to_visit.get()

            yield (current_label, current_path)

            for neighbor_obj in self.neighbors_of(current_label):
                if neighbor_obj.role in omitroles or startnode.shortlabel(neighbor_obj.role) in omitroles:
                    continue
                visited = [
                    (current_label, neighbor_obj.role, neighbor_obj.direction, neighbor_obj.neighbornodelabel),
                    (neighbor_obj.neighbornodelabel, neighbor_obj.role, neighbor_obj.inverse_direction(), current_label) ]

                if any(v in edges_visited for v in visited):
                    pass
                else:
                    nodelabels_to_visit.put( (neighbor_obj.neighbornodelabel, current_path + [neighbor_obj]) )
                    for v in visited: edges_visited.add(v)

