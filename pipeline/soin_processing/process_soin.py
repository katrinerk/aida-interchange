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
from aif import AidaGraph
from pipeline.soin_processing import SOIN
from pipeline.soin_processing.TypedDescriptor import *

import json
import os
import argparse
import rdflib
import itertools

from copy import deepcopy

graph_path = '/Users/eholgate/Desktop/SOIN/Annotation_Generated_V4/Annotation_Generated_V4_Valid/R103'

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
    bounding_box_node = graph.get(next(iter(bounding_box_id_set)))
    if not bounding_box_node:
        return False
    return bounding_box_node


def check_descriptor(graph, typing_statement, typed_descriptor):
    if typed_descriptor.descriptor.descriptor_type == "Text":
        justification_node = get_justification_node(graph, typing_statement)
        if not justification_node:
            return False
        return typed_descriptor.descriptor.evaluate_node(justification_node)

    elif typed_descriptor.descriptor.descriptor_type == "String":
        subject_node = get_subject_node(graph, typing_statement)
        if not subject_node:
            return False
        return typed_descriptor.descriptor.evaluate_node(subject_node)

    elif typed_descriptor.descriptor.descriptor_type == "Image":
        justification_node = get_justification_node(graph, typing_statement)
        bounding_box_node = get_bounding_box_node(graph, justification_node)
        if not (justification_node and bounding_box_node):
            return False
        return typed_descriptor.descriptor.evaluate_node(justification_node, bounding_box_node)

    elif isinstance(typed_descriptor, VideoDescriptor):
        pass

    elif typed_descriptor.descriptor.descriptor_type == "KB":
        link_node = get_kb_link_node(graph, typing_statement)
        if not link_node:
            return False
        return typed_descriptor.descriptor.evaluate_node(link_node)

    return False


def find_entrypoint(graph, entrypoint):
    """
    A function to resolve an entrypoint to the set of entity nodes that satisfy it.
    This function iterates through every node in the graph. If that node is a typing statement, it computes a
    typed score (how many matches between enttypes) and descriptor score (how many complete TypedDescriptor matches)
    across all TypedDescriptors. These scores are mapped typed_score -> descriptor_score -> {Nodes}.

    The function returns the set of nodes mapped to the highest scores (i.e.,
     highest typed_score -> highest descriptor_score).
    :param graph: AidaGraph
    :param entrypoint: Entrypoint
    :return: {Nodes}
    """
    score_mapping = {}
    for node in graph.nodes():
        if node.is_type_statement():
            typed_score = 0
            descriptor_score = 0

            # TODO: Why is this wrapped in a useless tuple??
            for filler in entrypoint.typed_descriptor_list:
                for typed_descriptor in filler:
                    typed_score += check_type(node, typed_descriptor)
                    descriptor_result = check_descriptor(graph, node, typed_descriptor)

                    if check_descriptor(graph, node, typed_descriptor):
                        descriptor_score += 1

            if typed_score in score_mapping:
                if descriptor_score in score_mapping[typed_score]:
                    score_mapping[typed_score][descriptor_score].add(node)
                else:
                    score_mapping[typed_score][descriptor_score] = {node}
            else:
                score_mapping[typed_score] = {descriptor_score: {node}}

    typed_keys_sorted = sorted(score_mapping.keys(), reverse=True)
    descriptor_keys_sorted = sorted(score_mapping[typed_keys_sorted[0]].keys(), reverse=True)

    return score_mapping[typed_keys_sorted[0]][descriptor_keys_sorted[0]]


def resolve_all_entrypoints(graph, entrypoints, cluster_to_prototype, entity_to_cluster):
    results = {}
    for entrypoint in entrypoints:
        node_set = find_entrypoint(graph, entrypoint)

        #  TODO: Why is this also wrapped in a tuple?
        if entrypoint.variable[0] in results:

            results[entrypoint.variable[0]].union(node_set)
        else:
            results[entrypoint.variable[0]] = node_set

    coref_results = {}
    for variable in results:
        node_set = set()
        for node in results[variable]:
            subject = next(iter(node.get('subject')))
            node_set.add(cluster_to_prototype[entity_to_cluster[subject]])
        coref_results[variable] = node_set

    return coref_results


def main():
    parser = argparse.ArgumentParser(description="Convert an XML-based Statement of Information Need definition to "
                                                 "the JSON-compliant UT Austin internal representation, "
                                                 "then identify and rank entrypoint nodes to be passed downstream.")
    parser.add_argument("soin_in", action="store", help="The path to the input XML")
    parser.add_argument("graph_in", action="store", help="The path to the input TTLs")
    parser.add_argument("out_path", action="store", help="The output path.")
    args = parser.parse_args()

    print("Parsing SOIN XML...")
    soin = SOIN.process_xml(args.soin_in)
    print("\tDone.\n")

    print("Loading Graph...")
    graph = load_graph(args.graph_in)
    print("\tDone.\n")

    print("Getting Cluster Mappings...")
    cluster_to_prototype, entity_to_cluster = get_cluster_mappings(graph)
    print("\tDone.\n")

    print("Resolving all entrypoints...")
    result = resolve_all_entrypoints(graph, soin.entrypoints, cluster_to_prototype, entity_to_cluster)
    all_names = sorted(result)
    all_combinations = itertools.product(*(result[Name] for Name in all_names))
    all_combinations_dicts = []
    for combo in all_combinations:
        rep = {}
        for i in range(len(all_names)):
            rep[all_names[i]] = combo[i]
        all_combinations_dicts.append(rep)
    print("\tDone.\n")

    write_me = {
        'graph': '',
        'queries': [],
        'facets': [],
    }

    print("Serializing data structures...")
    for frame in soin.frames:
        print(len(all_combinations_dicts))
        for combo in all_combinations_dicts:
            temporal_info = soin.temporal_info_to_dict()
            frame_rep = frame.frame_to_dict(combo, soin.temporal_info_to_dict())
            write_me['facets'].append(frame_rep)
    print("\tDone.\n")

    print("Writing output...")
    with open(args.out_path, 'w') as out:
        json.dump(write_me, out, indent=1)
    print("\tDone.\n")


if __name__ == "__main__":
    main()

