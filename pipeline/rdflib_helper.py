from collections import defaultdict

from rdflib.namespace import Namespace, RDF, XSD
from rdflib.term import BNode, Literal, URIRef
import logging


# namespaces for common prefixes
AIDA = Namespace('https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/InterchangeOntology#')
LDC = Namespace('https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/LdcAnnotations#')
LDC_ONT = Namespace('https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/LDCOntology#')


def count_nodes(node_set):
    node_count = 0
    bnode_count = 0
    for node_id in node_set:
        node_count += 1
        if not isinstance(node_id, URIRef):
            assert isinstance(node_id, BNode)
            bnode_count += 1
    return node_count, bnode_count


def catalogue_kb_nodes(kb_graph):
    node_type_set = set()
    for subj, obj in kb_graph.subject_objects(predicate=RDF.type):
        node_type_set.add(obj)

    node_type_set = {
        kb_graph.namespace_manager.compute_qname(node_type)[-1] for node_type in node_type_set}
    node_type_set.discard('Statement')

    kb_nodes_by_category = {}

    print('Counts for all node categories in the KB:\n==========')

    # Count statement nodes
    kb_stmt_set = set(kb_graph.subjects(predicate=RDF.type, object=RDF.Statement))
    kb_type_stmt_set = set(kb_graph.subjects(predicate=RDF.predicate, object=RDF.type))

    assert kb_type_stmt_set.issubset(kb_stmt_set)
    kb_edge_stmt_set = kb_stmt_set - kb_type_stmt_set

    kb_nodes_by_category['Statement'] = kb_stmt_set
    kb_nodes_by_category['EdgeStatement'] = kb_edge_stmt_set
    kb_nodes_by_category['TypeStatement'] = kb_type_stmt_set

    for category, node_set in kb_nodes_by_category.items():
        node_count, bnode_count = count_nodes(node_set)
        print('# {}:  {}  (# BNode:  {})'.format(category, node_count, bnode_count))
    print()

    # Count core nodes (EREs and Clusters)
    for node_type in ['Entity', 'Relation', 'Event', 'SameAsCluster', 'ClusterMembership']:
        node_set = set(kb_graph.subjects(predicate=RDF.type, object=AIDA.term(node_type)))
        node_count, bnode_count = count_nodes(node_set)
        print('# {}:  {}  (# BNode:  {})'.format(node_type, node_count, bnode_count))
        kb_nodes_by_category[node_type] = node_set
    print()

    # Count justification nodes
    for node_type in sorted(node_type_set):
        if 'Justification' not in node_type:
            continue
        node_set = set(kb_graph.subjects(predicate=RDF.type, object=AIDA.term(node_type)))
        node_count, bnode_count = count_nodes(node_set)
        print('# {}:  {}  (# BNode:  {})'.format(node_type, node_count, bnode_count))
        kb_nodes_by_category[node_type] = node_set
    print()

    # Count other nodes
    for node_type in sorted(node_type_set):
        if node_type in kb_nodes_by_category:
            continue
        node_set = set(kb_graph.subjects(predicate=RDF.type, object=AIDA.term(node_type)))
        node_count, bnode_count = count_nodes(node_set)
        print('# {}:  {}  (# BNode:  {})'.format(node_type, node_count, bnode_count))
        kb_nodes_by_category[node_type] = node_set
    print()

    print('Sanity check ...')
    cum_count = 0
    for category, node_set in kb_nodes_by_category.items():
        if category == 'Statement':
            continue
        for node_id in node_set:
            cum_count += len(list(kb_graph.predicate_objects(subject=node_id)))
    if cum_count == len(kb_graph):
        print(
            'Success: the sum of # triples for each node category == '
            '# triples in the whole graph: {}'.format(cum_count))
    else:
        print(
            'Warning: the sum of # triples for each node category != '
            '# triples in the whole graph: {}, {}'.format(cum_count, len(kb_graph)))

    return kb_nodes_by_category


def index_type_statement_nodes(kb_graph, kb_type_stmt_set):
    kb_type_stmt_key_mapping = defaultdict(set)

    for kb_stmt in kb_type_stmt_set:
        kb_stmt_subj = next(iter(kb_graph.objects(subject=kb_stmt, predicate=RDF.subject)))
        kb_stmt_pred = next(iter(kb_graph.objects(subject=kb_stmt, predicate=RDF.predicate)))
        kb_stmt_obj = next(iter(kb_graph.objects(subject=kb_stmt, predicate=RDF.object)))
        assert kb_stmt_pred == RDF.type
        # kb_type_stmt_key_mapping[(kb_stmt_subj, kb_stmt_obj)].add(kb_stmt)
        type_ont = kb_graph.namespace_manager.compute_qname(kb_stmt_obj)[-1]
        kb_type_stmt_key_mapping[kb_stmt_subj].add((kb_stmt, type_ont))

    return kb_type_stmt_key_mapping


def index_statement_nodes(kb_graph, kb_stmt_set):
    kb_stmt_key_mapping = defaultdict(set)

    for kb_stmt in kb_stmt_set:
        kb_stmt_subj = next(iter(kb_graph.objects(subject=kb_stmt, predicate=RDF.subject)))
        kb_stmt_pred = next(iter(kb_graph.objects(subject=kb_stmt, predicate=RDF.predicate)))
        kb_stmt_obj = next(iter(kb_graph.objects(subject=kb_stmt, predicate=RDF.object)))
        kb_stmt_key_mapping[(kb_stmt_subj, kb_stmt_pred, kb_stmt_obj)].add(kb_stmt)

    return kb_stmt_key_mapping


def index_cluster_membership_nodes(kb_graph, kb_cm_set):
    kb_cm_key_mapping = defaultdict(set)

    for kb_cm in kb_cm_set:
        kb_cm_cluster = next(iter(kb_graph.objects(subject=kb_cm, predicate=AIDA.cluster)))
        kb_cm_member = next(iter(kb_graph.objects(subject=kb_cm, predicate=AIDA.clusterMember)))
        kb_cm_key_mapping[(kb_cm_cluster, kb_cm_member)].add(kb_cm)

    return kb_cm_key_mapping


def match_subjects_intersection(kb_graph, po_pair_list, verbose=False):
    po_pair = po_pair_list[0]
    match_set = set(kb_graph.subjects(predicate=po_pair[0], object=po_pair[1]))

    for po_pair in po_pair_list[1:]:
        match_set = match_set & set(kb_graph.subjects(predicate=po_pair[0], object=po_pair[1]))

    warning_msg = ' & '.join([str(po_pair[0]) for po_pair in po_pair_list])

    if len(match_set) == 0:
        if verbose:
            print('Warning: cannot find a match for {}!'.format(warning_msg))
        return None

    if verbose and len(match_set) > 1:
        print('Warning: find more than 1 match for {}!'.format(warning_msg))

    return match_set.pop()


def match_statement_bnode(kb_graph, stmt_entry, kb_nodes_by_category=None, verbose=False):
    assert stmt_entry['type'] == 'Statement'
    stmt_subj = stmt_entry.get('subject', None)
    stmt_pred = stmt_entry.get('predicate', None)
    stmt_obj = stmt_entry.get('object', None)
    assert stmt_subj is not None and stmt_pred is not None and stmt_obj is not None

    kb_stmt_id = match_subjects_intersection(
        kb_graph,
        [(RDF.subject, URIRef(stmt_subj)), (RDF.object, URIRef(stmt_obj))],
        verbose=verbose)

    # stmt_subj_match_set = set(kb_graph.subjects(predicate=RDF.subject, object=URIRef(stmt_subj)))
    # stmt_obj_match_set = set(kb_graph.subjects(predicate=RDF.object, object=URIRef(stmt_obj)))
    # common_match_set = stmt_subj_match_set & stmt_obj_match_set
    #
    # if len(common_match_set) == 0:
    #     print('Warning: cannot find a match for the pair of subject & object!')
    #     return None
    #
    # if len(common_match_set) > 1:
    #     print('Warning: find more than 1 match for the pair of subject & object!')
    # kb_stmt_id = common_match_set.pop()

    if kb_stmt_id is not None and kb_nodes_by_category is not None:
        if stmt_pred == 'type':
            assert kb_stmt_id in kb_nodes_by_category['TypeStatement']
        else:
            assert kb_stmt_id in kb_nodes_by_category['EdgeStatement']

    return kb_stmt_id


def match_cluster_membership_bnode(kb_graph, cm_entry, kb_nodes_by_category=None, verbose=False):
    assert cm_entry['type'] == 'ClusterMembership'
    cm_cluster = cm_entry['cluster']
    cm_member = cm_entry['clusterMember']

    kb_cm_id = match_subjects_intersection(
        kb_graph,
        [(AIDA.cluster, URIRef(cm_cluster)), (AIDA.clusterMember, URIRef(cm_member))],
        verbose=verbose)

    # cm_cluster_match_set = set(kb_graph.subjects(predicate=AIDA.cluster, object=URIRef(cm_cluster)))
    # cm_member_match_set = set(kb_graph.subjects(
    #     predicate=AIDA.clusterMember, object=URIRef(cm_member)))
    # common_match_set = cm_cluster_match_set & cm_member_match_set
    #
    # if len(common_match_set) == 0:
    #     print('Warning: cannot find a match for the pair of cluster & clusterMember!')
    #     return None
    #
    # if len(common_match_set) > 1:
    #     print('Warning: find more than 1 match for the pair of cluster & clusterMember!')
    # kb_cm_id = common_match_set.pop()

    if kb_cm_id is not None and kb_nodes_by_category is not None:
        assert kb_cm_id in kb_nodes_by_category['ClusterMembership']

    return kb_cm_id


# extract triples from kb_graph with query_subj as the subject
def triples_for_subject(kb_graph, query_subj, expanding_preds=None, excluding_preds=None):
    if expanding_preds is None:
        expanding_preds = []
    if excluding_preds is None:
        excluding_preds = []

    triples = set()

    for s, p, o in kb_graph.triples((query_subj, None, None)):
        if p in excluding_preds:
            continue
        triples.add((s, p, o))
        if p in expanding_preds:
            triples.update(triples_for_subject(
                kb_graph, o, expanding_preds=expanding_preds, excluding_preds=excluding_preds))

    return triples


# extract triples from kb_graph with query_subj as the subject
def triples_for_edge_stmt(kb_graph, stmt_id, children_to_parent):
    triples = set()

    for s, p, o in kb_graph.triples((stmt_id, None, None)):
        if p == AIDA.privateData:
            continue

        # Hot fix to ensure that the aida:justifiedBy field in an edge statement must
        # be pointed to an aida:CompoundJustification node
        if p == AIDA.justifiedBy:
            obj_type = list(kb_graph.objects(subject=o, predicate=RDF.type))[0]
            if obj_type != AIDA.CompoundJustification:
                assert obj_type in [AIDA.TextJustification, AIDA.ImageJustification,
                                    AIDA.KeyFrameVideoJustification]

                comp_just_node = BNode()
                triples.add((s, p, comp_just_node))
                triples.add((comp_just_node, RDF.type, AIDA.CompoundJustification))
                triples.add((comp_just_node, AIDA.containedJustification, o))

                comp_just_conf_node = BNode()
                triples.add((comp_just_node, AIDA.confidence, comp_just_conf_node))

                just_conf_node_list = list(kb_graph.objects(subject=o, predicate=AIDA.confidence))
                if len(just_conf_node_list) > 0:
                    just_conf_node = just_conf_node_list[0]
                    for pred, obj in kb_graph.predicate_objects(subject=just_conf_node):
                        triples.add((comp_just_conf_node, pred, obj))

                triples.update(triples_for_justification(kb_graph, o, children_to_parent))
            else:
                triples.add((s, p, o))
                triples.update(triples_for_compound_just(kb_graph, o, children_to_parent))
        else:
            triples.add((s, p, o))

            if p == AIDA.confidence:
                triples.update(triples_for_conf(kb_graph, o))

            if p == AIDA.system:
                triples.update(triples_for_subject(kb_graph, o))

    return triples


def triples_for_type_stmt(kb_graph, stmt_id, children_to_parent):
    triples = set()

    for s, p, o in kb_graph.triples((stmt_id, None, None)):
        if p == AIDA.privateData:
            continue

        triples.add((s, p, o))

        if p == AIDA.justifiedBy:
            triples.update(triples_for_justification(kb_graph, o, children_to_parent))

        if p == AIDA.confidence:
            triples.update(triples_for_conf(kb_graph, o))

        if p == AIDA.system:
            triples.update(triples_for_subject(kb_graph, o))

    return triples


def triples_for_ere(kb_graph, ere_id, children_to_parent, type_stmt_id_list):
    triples = set()

    # Hot fix to ensure that each ERE has up to one informative justification per source document
    seen_source_document = set()

    info_just_count = 0
    max_info_just_add_to_type_stmt = 3

    for info_just in kb_graph.objects(subject=ere_id, predicate=AIDA.informativeJustification):
        info_just_triples = triples_for_justification(kb_graph, info_just, children_to_parent)

        source_document = None
        for _, info_just_p, info_just_o in info_just_triples:
            if info_just_p == AIDA.sourceDocument:
                source_document = str(info_just_o)
                break

        if source_document is not None:
            if source_document in seen_source_document:
                logging.warning(
                    'Duplicate source document {} in informative justifications for {}'.format(
                        source_document, ere_id))
                continue
            seen_source_document.add(source_document)

        triples.add((ere_id, AIDA.informativeJustification, info_just))
        triples.update(info_just_triples)

        # Hot fix to ensure that all informative justifications for each ERE are also in the
        # aida:justifiedBy field of all its typing statements.
        # Note: only add up to 3 informative justifications to the typing statement to prevent
        # combinatorial explosion when executing AIDA graph query.
        # if info_just_count < max_info_just_add_to_type_stmt:
        #     for type_stmt_id in type_stmt_id_list:
        #         triples.add((type_stmt_id, AIDA.justifiedBy, info_just))

        info_just_count += 1

    for s, p, o in kb_graph.triples((ere_id, None, None)):
        if p in [AIDA.justifiedBy, AIDA.privateData, AIDA.link, AIDA.ldcTime]:
            continue

        if p == AIDA.informativeJustification:
            continue

        triples.add((s, p, o))

        # if p == AIDA.informativeJustification:
        #     triples.update(triples_for_justification(kb_graph, o, children_to_parent))

        if p == AIDA.confidence:
            triples.update(triples_for_conf(kb_graph, o))

        if p == AIDA.system:
            triples.update(triples_for_subject(kb_graph, o))

    return triples


def triples_for_cluster(kb_graph, cluster_id, children_to_parent):
    triples = set()

    for s, p, o in kb_graph.triples((cluster_id, None, None)):
        if p in [AIDA.justifiedBy, AIDA.privateData, AIDA.link, AIDA.ldcTime]:
            continue

        triples.add((s, p, o))

        if p == AIDA.informativeJustification:
            triples.update(triples_for_justification(kb_graph, o, children_to_parent))

        if p == AIDA.confidence:
            triples.update(triples_for_conf(kb_graph, o))

        if p == AIDA.system:
            triples.update(triples_for_subject(kb_graph, o))

    return triples


def triples_for_cluster_membership(kb_graph, cm_id):
    triples = set()

    for s, p, o in kb_graph.triples((cm_id, None, None)):
        triples.add((s, p, o))

        if p == AIDA.confidence:
            triples.update(triples_for_conf(kb_graph, o))

        if p == AIDA.system:
            triples.update(triples_for_subject(kb_graph, o))

    return triples


def triples_for_compound_just(kb_graph, comp_just_id, children_to_parent):
    triples = set()

    for s, p, o in kb_graph.triples((comp_just_id, None, None)):
        if p == AIDA.privateData:
            continue

        triples.add((s, p, o))

        if p == AIDA.containedJustification:
            triples.update(triples_for_justification(kb_graph, o, children_to_parent))

        if p == AIDA.confidence:
            triples.update(triples_for_conf(kb_graph, o))

        if p == AIDA.system:
            triples.update(triples_for_subject(kb_graph, o))

    return triples


def triples_for_justification(kb_graph, just_id, children_to_parent):
    triples = set()

    for s, p, o in kb_graph.triples((just_id, None, None)):
        if p == AIDA.privateData:
            continue

        triples.add((s, p, o))

        if p in [AIDA.boundingBox, AIDA.confidence, AIDA.system]:
            triples.update(triples_for_subject(kb_graph, o, expanding_preds=[AIDA.system]))

    # Hot fix to add the missing aida:sourceDocument field when aida:source exists using
    # mapping from document element IDs to document IDs
    if not any(s == just_id and p == AIDA.sourceDocument for s, p, o in triples):
        source_id_list = [str(o) for s, p, o in triples if s == just_id and p == AIDA.source]
        if len(source_id_list) > 0:
            source_document_id = None
            for source_id in source_id_list:
                if source_id in children_to_parent:
                    source_document_id = children_to_parent[source_id][0]
                    break
            if source_document_id is not None:
                triples.add((just_id, AIDA.sourceDocument, Literal(source_document_id)))

    return triples

def triples_for_conf(kb_graph, conf_id):
    triples = set()

    for s, p, o in kb_graph.triples((conf_id, None, None)):
        if p == AIDA.confidenceValue:
            if float(o) < 0.0001:
                conf_value = Literal(0.0001, datatype=XSD.double)
            else:
                conf_value = o

            triples.add((s, p, conf_value))

        else:
            triples.add((s, p, o))

        if p == AIDA.system:
            triples.update(triples_for_subject(kb_graph, o))

    return triples


def load_children_to_parent_mapping(parent_children_filepath):
    print('\nLoading children-parent mapping from {}'.format(parent_children_filepath))
    with open(parent_children_filepath, 'r') as fin:
        lines = fin.readlines()

    children_to_parent = defaultdict(list)

    for line in lines[1:]:
        children, _, parent = line.strip().split('\t')
        if parent not in children_to_parent[children]:
            children_to_parent[children].append(parent)

    return children_to_parent


def find_finest_grained_type_stmt_for_ere(ere_id, kb_type_stmt_key_mapping, kb_type_stmt_set):
    all_type_stmt_id_list = kb_type_stmt_key_mapping[URIRef(ere_id)]

    highest_granularity_level = max(
        [len(type_ont.split('.')) for _, type_ont in all_type_stmt_id_list])

    type_stmt_id_list = []
    target_level = highest_granularity_level

    while len(type_stmt_id_list) == 0 and target_level >= 0:
        for type_stmt_id, type_ont in all_type_stmt_id_list:
            if len(type_ont.split('.')) == target_level and type_stmt_id in kb_type_stmt_set:
                type_stmt_id_list.append(type_stmt_id)
        target_level -= 1

    return type_stmt_id_list
