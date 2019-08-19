import json
import logging
import math
from argparse import ArgumentParser
from collections import defaultdict
from io import BytesIO
from operator import itemgetter
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import Namespace, RDF, XSD, NamespaceManager
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib.plugins.serializers.turtle import VERB
from rdflib.term import BNode, Literal, URIRef

from pipeline.json_graph_helper import build_cluster_member_mappings
from pipeline.rdflib_helper import AIDA, LDC, LDC_ONT
from pipeline.rdflib_helper import catalogue_kb_nodes, triples_for_subject
from pipeline.rdflib_helper import triples_for_edge_stmt, triples_for_type_stmt, triples_for_ere
from pipeline.rdflib_helper import triples_for_cluster, triples_for_cluster_membership
from pipeline.rdflib_helper import load_children_to_parent_mapping
from pipeline.rdflib_helper import match_cluster_membership_bnode, match_statement_bnode
from pipeline.rdflib_helper import match_subjects_intersection
from pipeline.rdflib_helper import index_statement_nodes, index_cluster_membership_nodes
from pipeline.rdflib_helper import index_type_statement_nodes, find_finest_grained_type_stmt_for_ere

UTEXAS = Namespace('http://www.utexas.edu/aida/')
OPERA = Namespace('http://www.lti.cs.cmu.edu/aida/opera/corpora/eval/')

expanding_preds_for_stmt = \
    [AIDA.justifiedBy, AIDA.confidence, AIDA.containedJustification, AIDA.boundingBox, AIDA.system]
excluding_preds_for_stmt = [AIDA.privateData]

expanding_preds_for_ere = \
    [AIDA.informativeJustification, AIDA.confidence, AIDA.boundingBox, AIDA.system]
excluding_preds_for_ere = [AIDA.privateData, AIDA.link, AIDA.justifiedBy, AIDA.ldcTime]

expanding_preds_for_cluster = \
    [AIDA.informativeJustification, AIDA.confidence, AIDA.boundingBox, AIDA.system]
excluding_preds_for_cluster = [AIDA.privateData, AIDA.link, AIDA.justifiedBy, AIDA.ldcTime]

expanding_preds_for_cm = [AIDA.confidence, AIDA.system]
excluding_preds_for_cm = []

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', level=logging.INFO)


# trying to match the AIF format
class AIFSerializer(TurtleSerializer):
    xsd_namespace_manager = NamespaceManager(Graph())
    xsd_namespace_manager.bind('xsd', XSD)

    # when writing BNode as subjects, write closing bracket
    # in a new line at the end
    def s_squared(self, subject):
        if (self._references[subject] > 0) or not isinstance(subject, BNode):
            return False
        self.write('\n' + self.indent() + '[')
        self.predicateList(subject)
        self.write('\n] .')
        return True

    # when printing Literals, directly call Literal.n3()
    def label(self, node, position):
        if node == RDF.nil:
            return '()'
        if position is VERB and node in self.keywords:
            return self.keywords[node]
        if isinstance(node, Literal):
            return node.n3(namespace_manager=self.xsd_namespace_manager)
        else:
            node = self.relativize(node)

            return self.getQName(node, position == VERB) or node.n3()


# return the text representation of the graph
def print_graph(g):
    serializer = AIFSerializer(g)
    stream = BytesIO()
    serializer.serialize(stream=stream)
    return stream.getvalue().decode()


def compute_cluster_handle_mapping(ere_set, graph_json, member_to_clusters):
    entity_cluster_set = set()
    for ere in ere_set:
        # Only include handles for clusters of Entities.
        if graph_json['theGraph'][ere]['type'] == 'Entity':
            for cluster in member_to_clusters[ere]:
                entity_cluster_set.add(cluster)

    cluster_handles = {}
    for cluster in entity_cluster_set:
        cluster_handles[cluster] = graph_json['theGraph'][cluster]['handle']

    return cluster_handles


def compute_cluster_importance_mapping(ere_importance, graph_json, member_to_clusters):
    cluster_importance = {}

    for ere, importance in ere_importance.items():
        # Only include importance values for clusters of Events or Relations.
        if graph_json['theGraph'][ere]['type'] in ['Event', 'Relation']:
            for cluster in member_to_clusters[ere]:
                if cluster not in cluster_importance or cluster_importance[cluster] < importance:
                    cluster_importance[cluster] = importance

    return cluster_importance


# build a subgraph from a list of statements for one AIDA result
def build_subgraph_for_hypothesis(kb_graph, kb_nodes_by_category, kb_stmt_key_mapping,
                                  kb_cm_key_mapping, kb_type_stmt_key_mapping,
                                  graph_json, graph_mappings, hypothesis_id, prob,
                                  statements, statement_weights, children_to_parent,
                                  patch_info_just_to_type_just=False,
                                  patch_type_just_to_info_just=False):
    member_to_clusters = graph_mappings['member_to_clusters']
    cluster_to_prototype = graph_mappings['cluster_to_prototype']
    cluster_membership_key_mapping = graph_mappings['cluster_membership_key_mapping']

    # Set of all KB edge statement nodes
    kb_edge_stmt_set = set()
    # Mapping from ERE to all its KB type statement nodes
    kb_type_stmt_set = set()
    # kb_type_stmt_dict = defaultdict(set)

    # Mapping from KB edge statement nodes to importance values
    kb_stmt_importance = {}

    # Set of all ERE node labels
    ere_set = set()
    # Mapping from ERE node labels to importance values
    ere_importance = {}

    logging.info('Processing all statements')
    for stmt, stmt_weight in zip(statements, statement_weights):
        # Rescale the stmt_weight to get the importance value
        if stmt_weight <= 0.0:
            stmt_weight = math.exp(stmt_weight / 100.0)
        else:
            stmt_weight = 0.0001

        stmt_entry = graph_json['theGraph'][stmt]
        assert stmt_entry['type'] == 'Statement'

        stmt_subj = stmt_entry.get('subject', None)
        stmt_pred = stmt_entry.get('predicate', None)
        stmt_obj = stmt_entry.get('object', None)
        assert stmt_subj is not None and stmt_pred is not None and stmt_obj is not None

        # Find the statement node in the KB
        kb_stmt_id = URIRef(stmt)
        if kb_stmt_id not in kb_nodes_by_category['Statement']:
            kb_stmt_pred = RDF.type if stmt_pred == 'type' else LDC_ONT.term(stmt_pred)
            kb_stmt_id = next(iter(
                kb_stmt_key_mapping[(URIRef(stmt_subj), kb_stmt_pred, URIRef(stmt_obj))]))
            # kb_stmt_id = match_statement_bnode(
            #     kb_graph, stmt_entry, kb_nodes_by_category, verbose=verbose)

        # Add the subject of any statement to ere_set
        ere_set.add(stmt_subj)

        # Update the importance value of the subject of any statement based on stmt_weight
        if stmt_subj not in ere_importance or ere_importance[stmt_subj] < stmt_weight:
            ere_importance[stmt_subj] = stmt_weight

        if stmt_pred == 'type':
            if kb_stmt_id is not None:
                # Add kb_stmt_id to the set of KB type statement nodes
                kb_type_stmt_set.add(kb_stmt_id)
                # kb_type_stmt_dict[stmt_subj].add(kb_stmt_id)

        else:
            if kb_stmt_id is not None:
                # Add kb_stmt_id to the set of KB edge statement nodes
                kb_edge_stmt_set.add(kb_stmt_id)
                # Update the importance value of the edge statement
                kb_stmt_importance[kb_stmt_id] = stmt_weight

            # Add the object of edge statements to ere_set
            ere_set.add(stmt_obj)

            # Update the importance value of the object of edge statements based on stmt_weight
            if stmt_obj not in ere_importance or ere_importance[stmt_obj] < stmt_weight:
                ere_importance[stmt_obj] = stmt_weight

    # Set of all SameAsCluster node labels
    same_as_cluster_set = set()
    # Set of all KB ClusterMembership nodes
    kb_cluster_membership_set = set()

    # Set of all ERE node labels that are prototypes
    proto_ere_set = set()

    logging.info('Processing all EREs and clusters')
    for ere in ere_set:
        for cluster in member_to_clusters[ere]:
            # Add all corresponding cluster label of each ERE node to same_as_cluster_set
            same_as_cluster_set.add(cluster)

            # Find the ClusterMembership node in the KB
            kb_cluster_membership_set.update(kb_cm_key_mapping[URIRef(cluster), URIRef(ere)])
            # kb_cm_id = None
            # for cm_label in cluster_membership_key_mapping[(cluster, ere)]:
            #     if URIRef(cm_label) in kb_nodes_by_category['ClusterMembership']:
            #         kb_cm_id = URIRef(cm_label)
            #         break
            # if kb_cm_id is None:
            #     cm_label = next(iter(cluster_membership_key_mapping[(cluster, ere)]))
            #     cm_entry = graph_json['theGraph'][cm_label]
            #     kb_cm_id = match_cluster_membership_bnode(
            #         kb_graph, cm_entry, kb_nodes_by_category, verbose=verbose)
            #
            # if kb_cm_id is not None:
            #     # Add kb_cm_id to the set of KB ClusterMembership nodes
            #     kb_cluster_membership_set.add(kb_cm_id)

            # Add the prototype of each SameAsCluster node to ere_set
            proto_ere = cluster_to_prototype[cluster]
            proto_ere_set.add(proto_ere)

            # Find the type statement node for the prototype
            proto_type_stmt_id_list = kb_type_stmt_key_mapping[URIRef(proto_ere)]
            highest_granularity_level = max(
                [len(type_ont.split('.')) for _, type_ont in proto_type_stmt_id_list])
            for type_stmt_id, type_ont in proto_type_stmt_id_list:
                if len(type_ont.split('.')) == highest_granularity_level:
                    kb_type_stmt_set.add(type_stmt_id)
                    # kb_type_stmt_dict[proto_ere].add(type_stmt_id)
            # kb_type_stmt_set.update(kb_type_stmt_key_mapping[URIRef(proto_ere)])

            # kb_stmt_id_for_proto_ere_type = match_subjects_intersection(
            #     kb_graph,
            #     [(RDF.subject, URIRef(proto_ere)), (RDF.predicate, RDF.type)],
            #     verbose=verbose)
            #
            # if kb_stmt_id_for_proto_ere_type is not None:
            #     # Add kb_stmt_id for the prototype type to the set of KB edge statement nodes
            #     kb_type_stmt_set.add(kb_stmt_id_for_proto_ere_type)

            # Find the ClusterMembership node for the prototype in the KB
            kb_cluster_membership_set.update(kb_cm_key_mapping[URIRef(cluster), URIRef(proto_ere)])
            # kb_proto_cm_id = None
            # for cm_label in cluster_membership_key_mapping[(cluster, proto_ere)]:
            #     if URIRef(cm_label) in kb_nodes_by_category['ClusterMembership']:
            #         kb_proto_cm_id = URIRef(cm_label)
            #         break
            # if kb_proto_cm_id is None:
            #     cm_label = next(iter(cluster_membership_key_mapping[(cluster, proto_ere)]))
            #     cm_entry = graph_json['theGraph'][cm_label]
            #     kb_proto_cm_id = match_cluster_membership_bnode(
            #         kb_graph, cm_entry, kb_nodes_by_category, verbose=verbose)
            #
            # if kb_proto_cm_id is not None:
            #     # Add kb_proto_cm_id to the set of KB ClusterMembership nodes
            #     kb_cluster_membership_set.add(kb_proto_cm_id)

    # Add all prototype ERE labels to ere_set
    ere_set |= proto_ere_set

    # kb_type_stmt_dict_by_cluster = defaultdict(set)
    # for ere, kb_type_stmts in kb_type_stmt_dict.items():
    #     for cluster in member_to_clusters[ere]:
    #         kb_type_stmt_dict_by_cluster[cluster].update(kb_type_stmts)
    #
    # for cluster, kb_type_stmts in kb_type_stmt_dict_by_cluster.items():
    #     type_ont_set = set()
    #     for kb_type_stmt in kb_type_stmts:
    #         type_ont = kb_graph.namespace_manager.compute_qname(
    #             list(kb_graph.objects(subject=kb_type_stmt, predicate=RDF.object))[0])[-1]
    #         type_ont_set.add(type_ont)
    #     if len(type_ont_set) > 1:
    #         print('Warning: {} has more than 1 type: {}'.format(cluster, type_ont_set))
    #
    # kb_type_stmt_set = set([kb_type_stmt for ere, kb_type_stmts in kb_type_stmt_dict.items()
    #                         for kb_type_stmt in kb_type_stmts])

    # All triples to be added to the subgraph
    logging.info('Extracting all content triples')
    all_triples = set()

    # logging.info('Extracting triples for all Statements')
    # Add triples for all Statements
    # for kb_stmt_id in kb_type_stmt_set | kb_edge_stmt_set:
    #     all_triples.update(triples_for_subject(
    #         kb_graph=kb_graph,
    #         query_subj=kb_stmt_id,
    #         expanding_preds=expanding_preds_for_stmt,
    #         excluding_preds=excluding_preds_for_stmt
    #     ))
    for kb_stmt_id in kb_edge_stmt_set:
        all_triples.update(triples_for_edge_stmt(kb_graph, kb_stmt_id, children_to_parent))

    for kb_stmt_id in kb_type_stmt_set:
        all_triples.update(triples_for_type_stmt(kb_graph, kb_stmt_id, children_to_parent))

    # logging.info('Extracting triples for all EREs')
    # Add triples for all EREs
    for ere in ere_set:
        kb_ere_id = URIRef(ere)
        type_stmt_id_list = find_finest_grained_type_stmt_for_ere(
            kb_ere_id, kb_type_stmt_key_mapping, kb_type_stmt_set)
        all_triples.update(triples_for_ere(
            kb_graph, kb_ere_id, children_to_parent, type_stmt_id_list))
        # all_triples.update(triples_for_subject(
        #     kb_graph=kb_graph,
        #     query_subj=kb_ere_id,
        #     expanding_preds=expanding_preds_for_ere,
        #     excluding_preds=excluding_preds_for_ere
        # ))

    # logging.info('Extracting triples for all SameAsClusters')
    # Add triples for all SameAsClusters
    for cluster in same_as_cluster_set:
        kb_cluster_id = URIRef(cluster)
        all_triples.update(triples_for_cluster(kb_graph, kb_cluster_id, children_to_parent))
        # all_triples.update(triples_for_subject(
        #     kb_graph=kb_graph,
        #     query_subj=kb_cluster_id,
        #     expanding_preds=expanding_preds_for_cluster,
        #     excluding_preds=excluding_preds_for_cluster
        # ))

    # logging.info('Extracting triples for all ClusterMemberships')
    # Add triples for all ClusterMemberships
    for kb_cm_id in kb_cluster_membership_set:
        all_triples.update(triples_for_cluster_membership(kb_graph, kb_cm_id))
        # all_triples.update(triples_for_subject(
        #     kb_graph=kb_graph,
        #     query_subj=kb_cm_id,
        #     expanding_preds=expanding_preds_for_cm,
        #     excluding_preds=excluding_preds_for_cm
        # ))

    logging.info('Constructing a subgraph')
    # Start building the subgraph
    subgraph = Graph()

    # Bind all prefixes of kb_graph to the subgraph
    for prefix, namespace in kb_graph.namespaces():
        if str(namespace) not in [AIDA, LDC, LDC_ONT]:
            subgraph.bind(prefix, namespace)
    # Bind the AIDA, LDC, LDC_ONT, and UTEXAS namespaces to the subgraph
    subgraph.bind('aida', AIDA, override=True)
    subgraph.bind('ldc', LDC, override=True)
    subgraph.bind('ldcOnt', LDC_ONT, override=True)
    subgraph.bind('utexas', UTEXAS)

    # Hot fix to reduce the OPERA/OPERA file size
    subgraph.bind('opera', OPERA)

    # logging.info('Adding hypothesis related triples to the subgraph')
    # Add triple for the aida:Hypothesis node and its type
    kb_hypothesis_id = UTEXAS.term(hypothesis_id)
    subgraph.add((kb_hypothesis_id, RDF.type, AIDA.Hypothesis))

    # Add triple for the hypothesis importance value
    if prob <= 0.0:
        hyp_weight = math.exp(prob / 2.0)
    else:
        hyp_weight = 0.0001
    subgraph.add((kb_hypothesis_id, AIDA.importance, Literal(hyp_weight, datatype=XSD.double)))

    # Add triple for the aida:Subgraph node and its type
    kb_subgraph_id = UTEXAS.term(hypothesis_id + '_subgraph')
    subgraph.add((kb_hypothesis_id, AIDA.hypothesisContent, kb_subgraph_id))
    subgraph.add((kb_subgraph_id, RDF.type, AIDA.Subgraph))

    # Add all SameAsClusters as contents of the aida:Subgraph node
    for cluster in same_as_cluster_set:
        kb_cluster_id = URIRef(cluster)
        subgraph.add((kb_subgraph_id, AIDA.subgraphContains, kb_cluster_id))

    # logging.info('Adding all content triples to the subgraph')
    # Add all triples
    for triple in all_triples:
        subgraph.add(triple)

    # Add importance values for all edge statements:
    for kb_stmt_id, importance in kb_stmt_importance.items():
        subgraph.add((kb_stmt_id, AIDA.importance, Literal(importance, datatype=XSD.double)))

    # Compute importance values for Event/Relation clusters
    cluster_importance = compute_cluster_importance_mapping(
        ere_importance, graph_json, member_to_clusters=member_to_clusters)
    for cluster, importance in cluster_importance.items():
        kb_cluster_id = URIRef(cluster)
        subgraph.add((kb_cluster_id, AIDA.importance, Literal(importance, datatype=XSD.double)))

    # Compute handles for Entity clusters
    cluster_handles = compute_cluster_handle_mapping(
        ere_set, graph_json, member_to_clusters=member_to_clusters)

    for cluster, handle in cluster_handles.items():
        kb_cluster_id = URIRef(cluster)
        if len(list(subgraph.objects(subject=kb_cluster_id, predicate=AIDA.handle))) == 0:
            subgraph.add((kb_cluster_id, AIDA.handle, Literal(handle, datatype=XSD.string)))

    # Hot fix to ensure that at least 1 of the informative justifications for each ERE is
    # also in the aida:justifiedBy field of all its typing statements.
    for type_stmt_id in subgraph.subjects(predicate=RDF.predicate, object=RDF.type):
        type_just_list = list(
            subgraph.objects(subject=type_stmt_id, predicate=AIDA.justifiedBy))

        stmt_subj_id = list(subgraph.objects(subject=type_stmt_id, predicate=RDF.subject))[0]
        info_just_list = list(subgraph.objects(
            subject=stmt_subj_id, predicate=AIDA.informativeJustification))

        if patch_info_just_to_type_just:
            # for info_just in info_just_list:
            #     if info_just not in type_just_list:
            #         subgraph.add((type_stmt_id, AIDA.justifiedBy, info_just))

            if not any(info_just in type_just_list for info_just in info_just_list):
                subgraph.add((type_stmt_id, AIDA.justifiedBy, info_just_list[0]))
                # print('Add justification {} to typing statement {}'.format(
                #     info_just_list[0], type_stmt_id))

        if patch_type_just_to_info_just:
            seen_source_document = set()
            # Record all source documents already in the informative justifications
            for info_just in info_just_list:
                info_just_source_document = None
                for info_just_o in subgraph.objects(
                        subject=info_just, predicate=AIDA.sourceDocument):
                    info_just_source_document = str(info_just_o)
                    break
                seen_source_document.add(info_just_source_document)

            # Add an unseen justification of the typing statement as an inf_just of the ERE
            for type_just in type_just_list:
                if type_just in info_just_list:
                    continue

                type_just_source_document = None
                for type_just_o in subgraph.objects(
                        subject=type_just, predicate=AIDA.sourceDocument):
                    type_just_source_document = str(type_just_o)
                    break

                if type_just_source_document is not None:
                    if type_just_source_document in seen_source_document:
                        continue
                    seen_source_document.add(type_just_source_document)

                subgraph.add((stmt_subj_id, AIDA.informativeJustification, type_just))

    return subgraph


def main():
    parser = ArgumentParser()
    parser.add_argument('graph_json_path', help='path to the graph json file')
    parser.add_argument('hypotheses_json_dir', help='path to the hypotheses json directory')
    parser.add_argument('kb_path', help='path to the TA2 KB file (in AIF)')
    parser.add_argument('parent_children_path', help='path to the parent-children mapping file')
    parser.add_argument('output_dir', help='path to output directory')
    parser.add_argument('run_id', help='run ID')
    parser.add_argument('--top', default=14, type=int,
                        help='number of top hypothesis to output')

    args = parser.parse_args()

    graph_json_path = Path(args.graph_json_path)
    assert graph_json_path.exists(), '{} does not exist'.format(graph_json_path)
    print('Reading the graph from {}'.format(graph_json_path))
    with open(graph_json_path, 'r') as fin:
        graph_json = json.load(fin)

    graph_mappings = build_cluster_member_mappings(graph_json)

    hypotheses_json_dir = Path(args.hypotheses_json_dir)
    assert hypotheses_json_dir.is_dir(), '{} does not exist'.format(hypotheses_json_dir)

    print('Reading kb from {}'.format(args.kb_path))
    kb_graph = Graph()
    kb_graph.parse(args.kb_path, format='ttl')

    kb_nodes_by_category = catalogue_kb_nodes(kb_graph)

    kb_stmt_key_mapping = index_statement_nodes(
        kb_graph, kb_nodes_by_category['Statement'])
    kb_cm_key_mapping = index_cluster_membership_nodes(
        kb_graph, kb_nodes_by_category['ClusterMembership'])
    kb_type_stmt_key_mapping = index_type_statement_nodes(
        kb_graph, kb_nodes_by_category['TypeStatement'])

    parent_children_path = Path(args.parent_chidren_path)
    assert parent_children_path.exists(), '{} does not exist'.format(parent_children_path)
    children_to_parent = load_children_to_parent_mapping(parent_children_path)

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print('Creating output directory {}'.format(output_dir))
        output_dir.mkdir(parents=True)

    run_id = args.run_id

    for soin in ['E101', 'E102', 'E103']:
        hypotheses_json_path = hypotheses_json_dir / '{}.json'.format(soin)
        assert hypotheses_json_path.exists(), '{} does not exist'.format(hypotheses_json_path)
        print('Reading the hypotheses from {}'.format(hypotheses_json_path))
        with open(hypotheses_json_path, 'r') as fin:
            hypotheses_json = json.load(fin)

        print('Found {} hypotheses with probability {}'.format(
            len(hypotheses_json['probs']), hypotheses_json['probs']))

        soin_id = 'AIDA_M18_TA3_' + soin

        frame_id = soin_id + '_F1'

        top_count = 0
        for hypothesis_idx, prob in sorted(
                enumerate(hypotheses_json['probs']), key=itemgetter(1), reverse=True):
            hypothesis = hypotheses_json['support'][hypothesis_idx]

            top_count += 1

            hypothesis_id = '{}_hypothesis_{:0>3d}'.format(frame_id, top_count)

            subgraph = build_subgraph_for_hypothesis(
                kb_graph=kb_graph,
                kb_nodes_by_category=kb_nodes_by_category,
                kb_stmt_key_mapping=kb_stmt_key_mapping,
                kb_cm_key_mapping=kb_cm_key_mapping,
                kb_type_stmt_key_mapping=kb_type_stmt_key_mapping,
                graph_json=graph_json,
                graph_mappings=graph_mappings,
                hypothesis_id=hypothesis_id,
                prob=prob,
                statements=hypothesis['statements'],
                statement_weights=hypothesis['statementWeights'],
                children_to_parent=children_to_parent
            )

            output_path = output_dir / '{}.{}.{}.H{:0>3d}.ttl'.format(
                run_id, soin_id, frame_id, top_count)
            print('Writing hypothesis #{} with prob {} to {}'.format(top_count, prob, output_path))
            with open(output_path, 'w') as fout:
                fout.write(print_graph(subgraph))

            if top_count >= args.top:
                break


if __name__ == '__main__':
    main()
