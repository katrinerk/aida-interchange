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

    def __repr__(self):
        hrule = "========================================"
        print("This run will test the parse of the input XML.")
        print(hrule + "\n\n")

        print("Frames:\n")
        for frame in self.frames:
            print("Frame: " + frame)
            for edge in self.frames[frame]:
                print("\tEdge: " + edge)
                for rel in self.frames[frame][edge]:
                    print("\t\t" + rel)

        print(hrule + "\n\n")

        print("Temporal Information:\n")
        for subject in self.temporal_info:
            print("Subject: " + subject)
            for time in self.temporal_info[subject]:
                print("\t" + time + ": ")
                for unit in self.temporal_info[subject][time]:
                    print("\t\t" + unit + ": " + self.temporal_info[subject][time][unit])

        print(hrule + "\n\n")

        print("EPs:\n")
        for ep_num, ep_dict in enumerate(self.entrypoints):
            print("EP " + str(ep_num + 1) + " : ")
            for k in ep_dict:
                print("\t" + k + ": " + str(ep_dict[k]))

        return ""

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

    :param in_dir: The directory containing the TTL files.
    :return: A JSON graph object
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

    return interface_object

def check_type(node, ep):
    """
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



def find_entrypoint(graph_interface, ep):
    """
    This function identifies the node address in the graph for the specified entrypoint description.

    :param graph_interface:
    :param ep:
    :return:
    """
    matches = []

    # Iterate through all statement nodes:
    for statement in graph_interface.json_obj["statements"]:
        # Check to see if this is a Type statement that matches the entrypoint criteria
        if check_type(graph_interface.json_obj["theGraph"][statement], ep):
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
                print("Entering.")
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
                    input()

            # TODO: This can be pulled out to make this code more efficient. Currenlty it's iterating through all
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

            elif ep["descriptor"]["type"]["kb"]:
                # TODO: Where do the background KB addresses live in the JSON / AIF
                pass

    return matches


def main():
    parser = argparse.ArgumentParser(description="Convert an XML-based Statement of Information Need definition to "
                                                 "the JSON-compliant UT Austin internal representation, "
                                                 "then identify and rank entrypoint nodes to be passed downstream.")
    parser.add_argument("soin_in", action="store", help="The path to the input XML")
    args = parser.parse_args()

    soin = SOIN(args.soin_in)
    print(soin)

    graph_interface = load_graph("/Users/eholgate/Desktop/SOIN/Annotation_Generated_V4"
                                       "/Annotation_Generated_V4_Valid/R103/.")

    for ep in soin.entrypoints:
        if ep["descriptor"]["type"] == "string":
            test_ep = ep
            break

    matches = find_entrypoint(graph_interface, test_ep)
    print(matches)
    print(len(matches))
    # # Return a list of possible matches
    # matches = []
    # for statement in graph_interface.json_obj['statements']:
    #     if check_type(graph_interface.json_obj['theGraph'][statement], test_ep):
    #         matches.append(statement)
    #
    # print(matches)





if __name__ == "__main__":
    main()












def find_entrypoint(ep_specs):
    """
    This function will search the input graph for nodes that match a given entrypoint specification.

    :param ep_specs:
    :return:
    """
    return None


def write_output():
    """Write the output """
    return None
