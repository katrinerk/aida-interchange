"""
    This is a program to process Statements of Information Need (SOINs; provided by DARPA in XML), extract the relevant
    query specifications, resolve and rank entrypoints, and produce JSON output structures for use downstream by the
    hypothesis creation program.

    The program receives SOIN XML input and outputs a single JSON file.

    TODO:
     - Figure out why we fail to match the example image query
     - Determine where background KB addresses live to better match KB-based entrypoint descriptions
     - Write a wrapper function to package found entrypoints properly in the JSON output structure
     - Introduce sysarg handling code for ease of use

    Author: Eric Holgate
            holgate@utexas.edu
"""
from aif import AidaGraph
from aif import JsonInterface

import xml.etree.ElementTree as ET
import json
import os
import argparse
import rdflib

from copy import deepcopy


class UnexpectedXMLTag(Exception):
    """
    This Exception will be raised if the processing script encounters unexpected information in the SOIN input.
    """
    pass


class SOIN:
    def __init__(self, in_path):
        self.frames, self.temporal_info, self.entrypoints = self._process_xml(in_path)
        self.json = {}

    def __str__(self):
        returnme = ""
        returnme += "========================================"
        returnme += "This run will test the parse of the input XML."
        returnme += "========================================\n\n"

        returnme += "Frames:\n"
        for frame in self.frames:
            returnme += "Frame: " + frame
            for edge in self.frames[frame]:
                returnme += "\tEdge: " + edge
                for rel in self.frames[frame][edge]:
                    returnme += "\t\t" + rel

        returnme += "========================================\n\n"

        returnme += "Temporal Information:\n"
        for subject in self.temporal_info:
            returnme += "Subject: " + subject
            for time in self.temporal_info[subject]:
                returnme += "\t" + time + ": "
                for unit in self.temporal_info[subject][time]:
                    returnme += "\t\t" + unit + ": " + self.temporal_info[subject][time][unit]

        returnme += "========================================\n\n"

        returnme += "EPs:\n"
        for ep_num, ep_dict in enumerate(self.entrypoints):
            returnme += "EP " + str(ep_num + 1) + " : "
            for k in ep_dict:
                returnme += "\t" + k + ": " + str(ep_dict[k])

        return returnme

    @staticmethod
    def _process_xml(in_path):
        """
        This function will process the XML input and retrieve:
            (1) The specified frames
            (2) Any temporal information
            (3) The entrypoint specifications


        :param in_path:
        :return:
            :frames: a dictionary mapping frame IDs to lists of query constraint triples
            :temporal_info: a dictionary mapping start_time and end_time to dictionaries mapping temporal units to
                            constraint specifications
            :eps: a list of entrypoint representations
        """

        # noinspection PyPep8Naming
        def del_XX(in_time):
            """
            This inner function simply checks for missing temporal information coded as "XX". If an instance of "XX" is
            found, it returns an empty String. Otherwise, it returns the unmodified input.

            :param in_time: the text contained in the temporal XML tag
            :return: the JSON compliant text
            """
            if (not in_time) or (in_time == "XX"):
                return ""
            else:
                return in_time.strip()

        tree = ET.parse(in_path)
        root = tree.getroot()

        frames = {}
        eps = []
        temporal_info = {}

        # Traverse the XML tree
        for div in root:
            # Handle frame definitions
            if div.tag == "frames":
                for frame in div:
                    frame_id = frame.attrib['id']
                    frame_rep = {}  # This will contain the JSON-compliant representation of this frame

                    for edges in frame:  # This is a wrapper node type and this loop should only ever execute once
                        for edge in edges:
                            edge_id = edge.attrib['id']
                            edge_dict = {"subject": None,
                                         "predicate": None,
                                         "object": None}

                            for relation in edge:

                                if relation.tag == "subject":
                                    edge_dict['subject'] = relation.text.strip()

                                elif relation.tag == "predicate":
                                    edge_dict['predicate'] = relation.text.strip()

                                elif relation.tag == "object":
                                    edge_dict['object'] = relation.text.strip()

                                else:
                                    raise UnexpectedXMLTag

                            # Hand this up
                            edge_rep = [edge_dict['subject'],
                                        edge_dict['predicate'],
                                        edge_dict['object']]
                            frame_rep[edge_id] = edge_rep

                        # Hand the frame representation up to be returned later
                        frames[frame_id] = frame_rep

            # Handle temporal information definitions
            elif div.tag == "temporal_info_list":
                for temp_info in div:
                    subject = ""
                    start = {}
                    end = {}

                    for time in temp_info:
                        if time.tag == "subject":
                            subject = time.text.strip()

                        elif time.tag == "start_time":
                            start_time_rep = {"year": None,
                                              "month": None,
                                              "day": None,
                                              "hour": None,
                                              "minute": None}

                            for info in time:
                                if info.tag == "year":
                                    start_time_rep["year"] = del_XX(info.text)

                                elif info.tag == "month":
                                    start_time_rep["month"] = del_XX(info.text)

                                elif info.tag == "day":
                                    start_time_rep["day"] = del_XX(info.text)

                                elif info.tag == "hour":
                                    start_time_rep["hour"] = del_XX(info.text)

                                elif info.tag == "minute":
                                    start_time_rep["minute"] = del_XX(info.text)

                                else:
                                    raise UnexpectedXMLTag

                            # Hand this up
                            start = start_time_rep

                        elif time.tag == "end_time":
                            time_rep = {"year": "",
                                        "month": "",
                                        "day": "",
                                        "hour": "",
                                        "minute": ""}

                            for info in time:
                                if info.tag == "year":
                                    time_rep["year"] = del_XX(info.text)

                                elif info.tag == "month":
                                    time_rep["month"] = del_XX(info.text)

                                elif info.tag == "day":
                                    time_rep["day"] = del_XX(info.text)

                                elif info.tag == "hour":
                                    time_rep["hour"] = del_XX(info.text)

                                elif info.tag == "minute":
                                    time_rep["minute"] = del_XX(info.text)

                                else:
                                    raise UnexpectedXMLTag

                            # Hand this up
                            end = time_rep

                        else:
                            raise UnexpectedXMLTag

                    temporal_info[subject] = {"start_time": start, "end_time": end}

            # Handle entrypoint definitions
            elif div.tag == "entrypoints":
                ep_rep_template = {
                    "node_name": None,
                    "ent_type": None,
                    "ent_subtype": None,
                    "ent_subsubtype": None,
                    "descriptor": None,
                }

                image_descriptor_rep_template = {
                    "type": "image",
                    "doceid": None,
                    "topleft": None,
                    "bottomright": None
                }

                text_descriptor_rep_template = {
                    "type": "text",
                    "doceid": None,
                    "start": None,
                    "end": None,
                }

                string_descriptor_rep_template = {
                    "type": "string",
                    "name_string": None,
                }

                kb_descriptor_rep_template = {
                    "type": "kb",
                    "kbid": None,
                }

                for ep in div:
                    ep_rep = deepcopy(ep_rep_template)

                    for elem in ep:
                        if elem.tag == "node":
                            ep_rep["node_name"] = elem.text.strip()

                        elif elem.tag == "typed_descriptor":

                            for descriptor in elem:
                                if descriptor.tag == "enttype":
                                    ep_rep["ent_type"] = descriptor.text.strip()

                                elif descriptor.tag == "entsubtype":
                                    ep_rep["ent_subtype"] = descriptor.text.strip()

                                elif descriptor.tag == "entsubsubtype":
                                    ep_rep["ent_subsubtype"] = descriptor.text.strip()

                                elif descriptor.tag == "image_descriptor":
                                    descriptor_rep = deepcopy(image_descriptor_rep_template)

                                    for info in descriptor:
                                        if info.tag == "doceid":
                                            descriptor_rep["doceid"] = info.text.strip()

                                        elif info.tag == "topleft":
                                            descriptor_rep["topleft"] = info.text.strip()

                                        elif info.tag == "bottomright":
                                            descriptor_rep["bottomright"] = info.text.strip()

                                        else:
                                            raise UnexpectedXMLTag

                                    # Hand this up
                                    ep_rep["descriptor"] = descriptor_rep

                                elif descriptor.tag == "text_descriptor":
                                    descriptor_rep = deepcopy(text_descriptor_rep_template)

                                    for info in descriptor:
                                        if info.tag == "doceid":
                                            descriptor_rep["doceid"] = info.text.strip()

                                        elif info.tag == "start":
                                            descriptor_rep["start"] = info.text.strip()

                                        elif info.tag == "end":
                                            descriptor_rep["end"] = info.text.strip()

                                        else:
                                            raise UnexpectedXMLTag

                                    # Hand this up
                                    ep_rep["descriptor"] = descriptor_rep

                                elif descriptor.tag == "string_descriptor":
                                    descriptor_rep = deepcopy(string_descriptor_rep_template)

                                    for name_string in descriptor:
                                        if name_string.tag == "name_string":
                                            descriptor_rep["name_string"] = name_string.text.strip()
                                        else:
                                            raise UnexpectedXMLTag

                                    # Hand this up
                                    ep_rep["descriptor"] = descriptor_rep

                                elif descriptor.tag == "kb_descriptor":
                                    descriptor_rep = deepcopy(kb_descriptor_rep_template)

                                    for id in descriptor:
                                        if id.tag == "kbid":
                                            descriptor_rep["kbid"] = id.text.strip()
                                        else:
                                            raise UnexpectedXMLTag

                                    # Hand this up
                                    ep_rep["descriptor"] = descriptor_rep

                                else:
                                    raise UnexpectedXMLTag

                        else:
                            raise UnexpectedXMLTag

                    eps.append(ep_rep)

            else:
                raise UnexpectedXMLTag

        # Return the constructed, JSON-compliant representations
        return frames, temporal_info, eps


def load_graph(in_dir):
    """
    This is a function to load a graph into memory.
    :param in_dir:
    :return:
    """
    turtles = []
    for file in os.listdir(in_dir):
        if file.endswith(".ttl"):
            turtles.append(os.path.join(in_dir, file))
        # Create an empty AidaGraph, then add the contents of each TTL to it.
    graph = AidaGraph()
    for file in turtles:
        subgraph = rdflib.Graph()
        subgraph.parse(file, format="ttl")
        graph.add_graph(subgraph)

    return graph


def check_type(node, ep):
    """
    A function which determines the extent to which a given AidaGraph node and Entrypoint definition contain matching
    type statements.

    :param node: an AidaGraph typing statement node.
    :param ep: a dictionary representing an entrypoint definition (maintained in SOIN)
    :return num_matched: an integer representation of the number of typing classifications matched
    """
    # t = node.get('object', shorten=True)
    # print(t)
    # input()

    types = next(iter(node.get("object", shorten=True))).strip().split('.')


    # Fix types to length 3 (in case subtype or subsubtype information was missing)
    for i in range(3 - len(types)):
        types.append("")

    num_matched = 0
    if types[0].lower().strip() == ep['ent_type'].lower().strip():
        num_matched += 1
        if types[1].lower().strip() == ep['ent_subtype'].lower().strip():
            num_matched += 1
            if types[2].lower().strip() == ep['ent_subsubtype'].lower().strip():
                num_matched += 1

    return num_matched


def check_descriptor(graph, node, ep):
    # Pull the justification information
    justification_node_id_set = node.get('justifiedBy')
    # If there is no justification information for this statement, return False
    if not justification_node_id_set:
        return False

    justification_node_id = next(iter(justification_node_id_set))
    justification_node = graph.get_node(justification_node_id)
    if not justification_node:
        return False

    # Handle TEXT type descriptors
    if ep["descriptor"]['type'] == "text":
        # Check the justification type; if it doesn't match, return False
        justification_type = next(iter(justification_node.get("type", shorten=True)))
        if justification_type != "TextJustification":
            return False

        justification_source = next(iter(justification_node.get("source"))).value.strip()
        # Check the source document ID
        if justification_source == ep['descriptor']['doceid']:
            justification_start_offset = str(next(iter(justification_node.get("startOffset"))).value).strip()
            justification_end_offset = str(next(iter(justification_node.get("endOffsetInclusive"))).value).strip()

            # Check the character offsets
            if justification_start_offset == ep['descriptor']['start']:
                if justification_end_offset == ep['descriptor']['end']:
                    return True
        return False

    # Handle IMAGE type descriptors
    # TODO: Is it possible that the original R103 example can't be found bc the justification is a compound one?
    elif ep['descriptor']['type'] == 'image':
        # Check the justification type; if it doesn't match, return False
        justification_type = next(iter(justification_node.get("type", shorten=True)))
        if justification_type != "ImageJustification":
            return False

        # Check the source information
        justification_source = next(iter(justification_node.get("source"))).value.strip()
        if justification_source == ep['descriptor']['doceid']:
            bounding_box_id = next(iter(justification_node.get('boundingBox')))
            bounding_box_node = graph.get_node(bounding_box_id)
            bb_upper_left_x = str(next(iter(bounding_box_node.get('boundingBoxUpperLeftX'))).value).strip()
            bb_upper_left_y = str(next(iter(bounding_box_node.get('boundingBoxUpperLeftY'))).value).strip()
            bb_lower_right_x = str(next(iter(bounding_box_node.get('boundingBoxLowerRightX'))).value).strip()
            bb_lower_right_y = str(next(iter(bounding_box_node.get('boundingBoxLowerRightY'))).value).strip()

            ep_upper_left_x, ep_upper_left_y = ep['descriptor']['topleft'].strip().split(',')
            ep_lower_right_x, ep_lower_right_y = ep['descriptor']['bottomright'].split(',')

            if bb_upper_left_x == ep_upper_left_x and bb_upper_left_y == bb_upper_left_y:
                if bb_lower_right_x == ep_lower_right_x and bb_lower_right_y == ep_lower_right_y:
                    return True

    # Handle STRING descriptor types
    elif ep['descriptor']['type'] == 'string':
        subj_id = node.get('subject')
        if not subj_id:
            return False

        subj_node = graph.get_node(next(iter(subj_id)))
        if not subj_node:
            return False
        name_set = subj_node.get('hasName')
        if not name_set:
            return False
        namestring = next(iter(name_set))

        if namestring.strip() == ep['descriptor']['name_string']:
            return True
        return False

    # Handle KB descriptor type
    elif ep['descriptor']['type'] == 'kb':
        subj_id = node.get('subject')
        if not subj_id:
            return False

        subj_node = graph.get_node(next(iter(subj_id)))
        if not subj_node:
            return False

        link_id = subj_node.get('link')
        if not link_id:
            return False

        link_node = graph.get_node(next(iter(link_id)))
        if not link_node:
            return False

        link_target_set = link_node.get('linkTarget')
        if not link_target_set:
            return False

        link_target = next(iter(link_target_set)).value

        if link_target.strip() == ep['descriptor']['kbid']:
            return True

    return False


def find_entrypoint(graph, ep):
    """
    This function resolves an Entrypoint definition to an AidaGraph node.

    :param graph: an AidaGraph object
    :param ep: a dictionary representing the Entrypoint definition (maintained in SOIN)
    :return:
    """
    results = {
        0: {True: [], False: []},
        1: {True: [], False: []},
        2: {True: [], False: []},
        3: {True: [], False: []},
    }
    # Iterate through the nodes in the graph, looking for typing statements.
    for node in graph.nodes():
        if node.is_type_statement():
            types_matched = check_type(node, ep)
            descriptor_matched = check_descriptor(graph, node, ep)

            # Get the Entity node this statement describes
            ent_node = graph.get_node(next(iter(node.get('subject'))))
            results[types_matched][descriptor_matched].append(ent_node.name.split('#')[-1])

    # TODO: There's probably something smarter to do here - let's talk about it?
    if results[3][True]:
        return results[3][True].pop()
    elif results[2][True]:
        return results[2][True].pop()
    elif results[1][True]:
        return results[1][True].pop()
    elif results[0][True]:
        return results[0][True].pop()

    if results[3][False]:
        return results[3][False].pop()
    elif results[2][False]:
        return results[2][False].pop()
    elif results[1][False]:
        return results[1][False].pop()
    elif results[0][False]:
        return results[0][False].pop()



def test_me():
    soin = SOIN("/Users/eholgate/Desktop/SOIN/StatementOfInformationNeed_Example_M18/R103.xml")
    graph = load_graph("/Users/eholgate/Desktop/SOIN/Annotation_Generated_V4/Annotation_Generated_V4_Valid/R103/.")
    # graph = load_graph("/Users/eholgate/Desktop/SOIN/colorado_TTL/.")

    for ep in soin.entrypoints:
        if ep["descriptor"]["type"] == "text":
            test_ep = ep
            break
    # print(test_ep)
    # input()
    result = find_entrypoint(graph, test_ep)
    print(result)


def main():
    parser = argparse.ArgumentParser(description="Convert an XML-based Statement of Information Need definition to "
                                                 "the JSON-compliant UT Austin internal representation, "
                                                 "then identify and rank entrypoint nodes to be passed downstream.")
    parser.add_argument("soin_in", action="store", help="The path to the input XML")
    parser.add_argument("graph_in", action="store", help="The path to the input TTLs")
    parser.add_argument("out_path", action="store", help="The output path.")
    args = parser.parse_args()

    print("Parsing SOIN XML...")
    soin = SOIN(args.soin_in)
    # soin = SOIN("/Users/eholgate/Desktop/SOIN/StatementOfInformationNeed_Example_M18/R103.xml")
    print("\tDone.\n")

    print("Loading Graph...")
    graph = load_graph(args.graph_in)
    print("\tDone.\n")

    facet_template = {
        "ERE": [],
        "temporal": soin.temporal_info,
        "statements": [],
        "queryConstraints": {},
         }

    writeme = {
        "graph": parser.graph_in,
        "queries": [],
        "facets": [],
    }

    print("Resolving Entrypoints...")
    for ep in soin.entrypoints:
        ep_node = find_entrypoint(graph, ep)
        facet_template['ERE'].append(ep_node)
    print("\tDone.\n")

    print("Formatting output...")
    for frame, constraints in soin.frames.items():
        facet = deepcopy(facet_template)
        facet['queryConstraints'] = constraints
        writeme['facets'].append(facet)
    print("\tDone.\n")

    print("Writing output...")
    with open(args.out_path, 'w') as out:
        json.dump(writeme, out, indent=1)
    print("\tDone.\n")
    # # Return a list of possible matches
    # matches = []
    # for statement in graph_interface.json_obj['statements']:
    #     if check_type(graph_interface.json_obj['theGraph'][statement], test_ep):
    #         matches.append(statement)
    #
    # print(matches)





if __name__ == "__main__":
    main()


##############################
#    DEPRECATED FUNCTIONS    #
##############################
def _deprecated_load_graph(in_dir):
    """
    DEPRECATED: This has been replaced with load_graph(), which does not utilize JsonInterface
    This is a function to load a graph into memory.

    :param in_dir: The directory containing the TTL files.
    :return graph: an AidaGraph object
    :return graph_interface: a JsonInterface object
    """
    turtles = []
    for file in os.listdir(in_dir):
        if file.endswith(".ttl"):
            turtles.append(os.path.join(in_dir, file))

    # Create an empty AidaGraph, then add the contents of each TTL to it.
    graph = AidaGraph()
    for file in turtles:
        subgraph = rdflib.Graph()
        subgraph.parse(file, format="ttl")
        graph.add_graph(subgraph)

    # Convert the AidaGraph to a JSON Representation
    interface_object = JsonInterface(graph, simplification_level=0)

    return graph, interface_object

def _deprecated_check_type_json_interface(node, ep):
    """
    DEPRECATED: This function has been replaced by check_type() which operates on AidaNode input instead of
                JsonInterface input.
    This is a function to check if the typing statement of a node matches the type constraints of a query.

    :param node:
    :param typing:
    :return:
    """
    # Check to see if this node is a Type statement
    if node["predicate"] == "type":
        obj_str = node["object"].split("#")[-1]
        node_types = obj_str.split(".")

        # Check the current node types against the provided constraints
        if node_types[0].lower() == ep["ent_type"].lower():
            if (len(node_types) >= 2) and node_types[1].lower() == ep["ent_subtype"].lower():
                if (len(node_types) >= 3) and node_types[2].lower() == ep["ent_subsubtype"].lower():
                    return True

        return False

def _deprecated_find_entrypoint(graph, graph_interface, ep):
    """
    DEPRECATED: this function has been replaced by find_entrypoint() which does not utilize JsonInterface input.
    This function identifies the node address in the graph for the specified entrypoint description.

    :param graph:
    :param graph_interface:
    :param ep:
    :return:
    """
    matches = []

    # Iterate through all statement nodes:
    for statement in graph_interface.json_obj["statements"]:
        print("huh")
        # Check to see if this is a Type statement that matches the entrypoint criteria
        if check_type(graph_interface.json_obj["theGraph"][statement], ep):
            print("Checking type")
            # Check Justification information based on Descriptor type

            # Handle text descriptors
            if ep["descriptor"]["type"] == "text":
                # Check to make sure there is justification information for this node
                if statement not in graph_interface.json_just_obj:
                    continue

                # Pull the justification information
                just_node = graph_interface.json_just_obj[statement][0]
                # Check the source document ID
                if "source" not in just_node:
                    continue
                if just_node["source"][0].value == ep["descriptor"]["doceid"]:
                    # Check the offset values
                    if just_node["startOffset"][0].value == int(ep["descriptor"]["start"]) and \
                            just_node["endOffsetInclusive"][0].value == int(ep["descriptor"]["end"]):
                        matches.append(statement)

            # TODO: There is a bug here preventing us from finding the image-based entrypoint in the sample SOIN.
            #  I don't *think* the issue is in this code. I still need to check to see if I can find the node in the
            #  raw AIF.
            #  It may also be the case that they've defined an entrypoint that simply does not have a representation
            #  in the LDC graph...
            #  In the meantime, consider this condition unimplemented.
            elif ep["descriptor"]["type"] == "image":
                # Check to make sure there is justification information for this node
                if statement not in graph_interface.json_just_obj:
                    continue

                # Pull the justification information
                just_node = graph_interface.json_just_obj[statement][0]
                # Check the source document ID
                if "source" not in just_node:
                    continue
                if just_node["source"][0].value == ep["descriptor"]["doceid"]:
                    # Check the bounding box
                    print(just_node)
                    # input()

            # TODO: This can be pulled out to make this code more efficient. Currently it's iterating through all
            #  ERE's many times
            elif ep["descriptor"]["type"] == "string":
                for entity in graph_interface.json_obj["ere"]:
                    node = graph_interface.json_obj["theGraph"][entity]
                    if node["type"] == "Entity":
                        if "name" not in node:
                            continue
                        for name in node["name"]:
                            if name == ep["descriptor"]["name_string"]:
                                if statement in node['adjacent']:
                                    matches.append(statement)
                                    break

            # Handle KB descriptors; this requires searching the AidaGraph representation, as this information is not
            # maintained in the JSON representation.
            elif ep["descriptor"]["type"] == "kb":
                print("ENTERING!!!")
                # First, check typing equivalence
                print(graph_interface.json_obj["theGraph"][statement].keys())
                # node_address = graph_interface.json_obj["theGraph"][statement]["name"]
                for n in graph.nodes():
                    if n.name.strip() == statement:
                        pass
    return matches
