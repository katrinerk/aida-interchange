"""
    This is a program to process Statements of Information Need (SOINs; provided by DARPA in XML), extract the relevant
    query specifications, resolve and rank entrypoints, and produce JSON output structures for use downstream by the
    hypothesis creation program.

    The program receives SOIN XML input and outputs a single JSON file.

    TODO:
     - Add video descriptor coverage
     - Replace variable identities
     - Handle cases where resolved EPs are not coreferential

    Author: Eric Holgate
            holgate@utexas.edu
"""
import sys
import json
import os
import argparse
import rdflib
import itertools

from copy import deepcopy
from os.path import dirname, realpath
src_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.insert(0, src_path)

from aif import AidaGraph
from pipeline.soin_processing import SOIN
from pipeline.soin_processing.TypedDescriptor import *
from pipeline.soin_processing.templates_and_constants import DEBUG, SCORE_WEIGHTS, DEBUG_SCORE_FLOOR


graph_path = '/Users/eholgate/Desktop/SOIN/Annotation_Generated_V4/Annotation_Generated_V4_Valid/R107'
graph_path = '/Users/eholgate/Downloads/GAIA_1-OPERA_3_Colorado_1/NIST/'


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


def get_cluster_mappings(graph):
    cluster_to_prototype = {}
    entities_to_clusters = {}

    for node in graph.nodes():
        if node.is_sameas_cluster():
            cluster_to_prototype[node.name] = next(iter(node.get('prototype')))
        elif node.is_cluster_membership():
            cluster_member = next(iter(node.get('clusterMember')))
            cluster = next(iter(node.get('cluster')))
            entities_to_clusters[cluster_member] = cluster

    return cluster_to_prototype, entities_to_clusters


def check_type(node, typed_descriptor):
    """
    A function which determines the extent to which a given AidaGraph node and Entrypoint definition contain matching
    type statements.

    :param node: AidaNode
    :param typed_descriptor: TypedDescriptor
    :return: int
    """
    types = next(iter(node.get('object', shorten=True))).strip().split('.')

    # Fix types to length 3 (in case subtype or subsubtype information was missing)
    for i in range(3 - len(types)):
        types.append("")

    types_dict = {
        'type': types[0],
        'subtype': types[1],
        'subsubtype': types[2],
    }

    return typed_descriptor.enttype.get_type_score(types_dict)


def get_subject_node(graph, typing_statement):
    """
    A function to return the subject node for a typing statement node.
    :param graph:
    :param typing_statement:
    :return: AidaNode or False
    """
    subject_node_id_set = typing_statement.get('subject')
    if not subject_node_id_set:
        return False

    subject_node = graph.get_node(next(iter(subject_node_id_set)))
    if not subject_node:
        return False

    return subject_node


def get_justification_node(graph, typing_statement):
    """
    A function to return the justification node for a typing statement node.
    :param graph:
    :param typing_statement:
    :return: AidaNode or False
    """
    justification_node_id_set = typing_statement.get('justifiedBy')
    if not justification_node_id_set:
        return False

    justification_node = graph.get_node(next(iter(justification_node_id_set)))
    if not justification_node:
        return False

    return justification_node


def get_kb_link_node(graph, typing_statement):
    """
    A function to return the KB linking node from a typing statement
    :param graph: AidaGraph
    :param typing_statement: AidaNode
    :return: AidaNode/False
    """
    subject_node = get_subject_node(graph, typing_statement)
    if not subject_node:
        return False
    link_id_set = subject_node.get('link')
    if not link_id_set:
        return False
    link_node = graph.get_node(next(iter(link_id_set)))
    if not link_node:
        return False

    return link_node


def get_bounding_box_node(graph, justification_node):
    """
    A function to return the bounding box node from a justification node.
    :param graph: AidaGraph
    :param justification_node: AidaNode
    :return: AidaNode
    """
    bounding_box_id_set = justification_node.get('boundingBox')
    if not bounding_box_id_set:
        return False
    print(bounding_box_id_set)
    bounding_box_node = graph.get_node(next(iter(bounding_box_id_set)))
    if not bounding_box_node:
        return False
    return bounding_box_node


def check_descriptor(graph, typing_statement, typed_descriptor):
    if typed_descriptor.descriptor.descriptor_type == "Text":
        justification_node = get_justification_node(graph, typing_statement)
        if not justification_node:
            return False
        jtype_set = justification_node.get('type', shorten=True)
        if not jtype_set:
            return False
        jtype = next(iter(jtype_set))
        if jtype != "TextJustification":
            return False

        return typed_descriptor.descriptor.evaluate_node(justification_node)

    elif typed_descriptor.descriptor.descriptor_type == "String":
        subject_node = get_subject_node(graph, typing_statement)
        if not subject_node:
            return False
        return typed_descriptor.descriptor.evaluate_node(subject_node)

    elif typed_descriptor.descriptor.descriptor_type == "Image":
        justification_node = get_justification_node(graph, typing_statement)
        if not justification_node:
            return False
        jtype_set = justification_node.get('type', shorten=True)
        if not jtype_set:
            return False
        jtype = next(iter(jtype_set))
        if jtype != "ImageJustification":
            return False

        bounding_box_node = get_bounding_box_node(graph, justification_node)
        if not bounding_box_node:
            return False
        if not (justification_node and bounding_box_node):
            return False

        return typed_descriptor.descriptor.evaluate_node(justification_node, bounding_box_node)

    elif typed_descriptor.descriptor.descriptor_type == "Video":
        justification_node = get_justification_node(graph, typing_statement)
        if not justification_node:
            return False

        jtype_set = justification_node.get('type', shorten=True)
        if not jtype_set:
            return False

        jtype = next(iter(jtype_set))
        if jtype != "KeyFrameVideoJustification":
            return False

        bounding_box_node = get_bounding_box_node(graph, justification_node)
        if not bounding_box_node:
            return False

        return typed_descriptor.descriptor.evaluate_node(justification_node, bounding_box_node)

    elif typed_descriptor.descriptor.descriptor_type == "KB":
        link_node = get_kb_link_node(graph, typing_statement)
        if not link_node:
            return False
        return typed_descriptor.descriptor.evaluate_node(link_node)

    return False


def find_entrypoint(graph, entrypoint, cluster_to_prototype, entity_to_cluster, ep_cap):
    """
    A function to resolve an entrypoint to the set of entity nodes that satisfy it.
    This function iterates through every node in the graph. If that node is a typing statement, it computes a
    typed score (how many matches between enttypes) and descriptor score (how many complete TypedDescriptor matches)
    across all TypedDescriptors. These scores are mapped typed_score -> descriptor_score -> {Nodes}.

    The function returns the set of nodes mapped to the highest scores (i.e.,
     highest typed_score -> highest descriptor_score).
    :param graph: AidaGraph
    :param entrypoint: Entrypoint
    :param cluster_to_prototype: dict
    :param entity_to_cluster: dict
    :param ep_cap: int
    :return: {Nodes}
    """
    results = {}
    for node in graph.nodes():

        if node.is_type_statement():
            typed_score = 0
            name_score = 0
            descriptor_score = 0

            has_type = 0
            has_name = 0
            has_descriptor = 0

            num_enttypes = 0
            num_descriptors = 0

            # TODO: Why is this wrapped in a useless tuple??
            for filler in entrypoint.typed_descriptor_list:
                for typed_descriptor in filler:
                    if typed_descriptor.enttype:
                        has_type = 1
                        num_enttypes += 1
                        typed_score += check_type(node, typed_descriptor)
                    if typed_descriptor.descriptor:
                        if typed_descriptor.descriptor.descriptor_type == 'String':
                            has_name = 1
                            name_score += check_descriptor(graph, node, typed_descriptor)
                        else:
                            has_descriptor = 1
                            num_descriptors += 1
                            descriptor_score += check_descriptor(graph, node, typed_descriptor)

            # Compute the total score, pull the prototype, and add the prototype node to the results dict
            # Compute the denominator for the score based on what information was present
            raw_score = (typed_score/100) + (name_score/100) + (descriptor_score/100)
            score_numerator = 0
            score_denominator = 0

            if has_type:
                score_numerator += ((typed_score/num_enttypes)/100) * SCORE_WEIGHTS['type']
                score_denominator += SCORE_WEIGHTS['type']
            if has_name:
                score_numerator += (name_score/100) * SCORE_WEIGHTS['name']
                score_denominator += SCORE_WEIGHTS['name']
            if has_descriptor:
                score_numerator += ((descriptor_score/num_descriptors)/100) * SCORE_WEIGHTS['descriptor']
                score_denominator += SCORE_WEIGHTS['descriptor']

            if DEBUG:
                print("Raw Score: " + str(raw_score))
                print("Score Numerator: " + str(score_numerator))
                print("Score Denominator: " + str(score_denominator))

            total_score = (score_numerator/score_denominator) * 100

            if DEBUG:
                print("Normalized Score: " + str(total_score))
                print()
                print("##############################################")
                print()
                if (total_score >= DEBUG_SCORE_FLOOR):
                    input()

            subject_address = next(iter(node.get('subject')))
            try:
                prototype = cluster_to_prototype[entity_to_cluster[subject_address]]
            except KeyError:
                continue

            if total_score in results:
                results[total_score].add((total_score, prototype))
            else:
                results[total_score] = {(total_score, prototype)}

    set_of_nodes = set()
    return_count = 0
    scores_sorted = sorted(results.keys(), reverse=True)
    for score in scores_sorted:
        for node in results[score]:
            if return_count >= ep_cap:
                break
            elif node not in set_of_nodes:
                return_count += 1
                set_of_nodes.add(node)

    ordered_list = sorted(list(set_of_nodes), key=lambda x: x[0], reverse=True)
    ep_list = []
    ep_weight_list = []
    for elem in ordered_list:
        ep_list.append(elem[1])
        ep_weight_list.append(elem[0])
    return ep_list, ep_weight_list


def resolve_all_entrypoints(graph, entrypoints, cluster_to_prototype, entity_to_cluster, ep_cap):
    ep_dict = {}
    ep_weight_dict = {}
    for entrypoint in entrypoints:
        # results[entrypoint.variable[0]]
        ep_list, ep_weight_list = find_entrypoint(graph,
                                                  entrypoint,
                                                  cluster_to_prototype,
                                                  entity_to_cluster,
                                                  ep_cap)
        ep_dict[entrypoint.variable[0]] = ep_list
        ep_weight_dict[entrypoint.variable[0]] = ep_weight_list

    return ep_dict, ep_weight_dict


def main():
    parser = argparse.ArgumentParser(description="Convert an XML-based Statement of Information Need definition to "
                                                 "the JSON-compliant UT Austin internal representation, "
                                                 "then identify and rank entrypoint nodes to be passed downstream.")
    parser.add_argument("soin_in", action="store", help="The path to the input XML")
    parser.add_argument("graph_in", action="store", help="The path to the input TTLs")
    parser.add_argument("out_path", action="store", help="The output path.")
    parser.add_argument('-ep',
                        '--ep-cap',
                        action='store',
                        type=int,
                        default=50,
                        help='The maximum number of EPs *per entrypoint description*')
    args = parser.parse_args()

    if args.soin_in[-1] != '/':
        args.soin_in[-1] += '/'

    if args.out_path[-1] != '/':
        args.out_path[-1] += '/'

    if not(os.path.exists(args.out_path)):
        os.mkdir(args.out_path)

    print("Loading Graph...")
    graph = load_graph(args.graph_in)
    print("\tDone.\n")

    print("Getting Cluster Mappings...")
    cluster_to_prototype, entity_to_cluster = get_cluster_mappings(graph)
    print("\tDone.\n")

    soins = []
    for f in os.listdir(args.soin_in):
        if f.endswith('.xml'):
            soins.append(f)
    s_count = 0
    for s in soins:
        s_count += 1
        print("Processing SOIN " + str(s_count) + " of " + str(len(soins)))
        print("\tParsing SOIN XML...")
        soin = SOIN.process_xml(args.soin_in + s)
        print("\t\tDone.\n")

        print("\tResolving all entrypoints...")
        ep_dict, ep_weights_dict = resolve_all_entrypoints(graph, soin.entrypoints, cluster_to_prototype, entity_to_cluster, args.ep_cap)
        print("\t\tDone.\n")

        write_me = {
            'graph': '',
            'entrypoints': ep_dict,
            'entrypointWeights': ep_weights_dict,
            'queries': [],
            'facets': [],
        }

        print("\tSerializing data structures...")
        temporal_info = soin.temporal_info_to_dict()
        for frame in soin.frames:
            frame_rep = frame.frame_to_dict(temporal_info)
            write_me['facets'].append(frame_rep)
        print("\t\tDone.\n")

        print("\tWriting output...")
        with open(args.out_path + s.strip('.xml') + '_query.json', 'w') as out:
            json.dump(write_me, out, indent=1)
        print("\t\tDone.\n")


if __name__ == "__main__":
    main()

