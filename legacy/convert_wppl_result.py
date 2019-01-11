# Pengxiang Cheng Fall 2018
# Pre- and postprocessing for AIDA eval

import json
from argparse import ArgumentParser
from io import BytesIO
from operator import itemgetter
from os import makedirs
from os.path import join, exists

from rdflib import Graph
from rdflib.namespace import Namespace, RDF
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib.plugins.serializers.turtle import VERB
from rdflib.term import BNode, Literal, URIRef

# namespaces for common prefixes
LDC = Namespace(
    'https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/LdcAnnotations#')
AIDA = Namespace(
    'https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/InterchangeOntology#')


# trying to match the AIF format
class AIFSerializer(TurtleSerializer):

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
            return node.n3()
        else:
            node = self.relativize(node)

            return self.getQName(node, position == VERB) or node.n3()


# return the text representation of the graph
def print_graph(g):
    serializer = AIFSerializer(g)
    stream = BytesIO()
    serializer.serialize(stream=stream)
    return stream.getvalue().decode()


# extract triples from kb_graph with query_subj as the subject,
# recursively expand BNode objects.
def triples_for_subject(kb_graph, query_subj):
    triples = []

    for s, p, o in kb_graph.triples((query_subj, None, None)):
        triples.append((s, p, o))
        if isinstance(o, BNode):
            triples.extend(triples_for_subject(kb_graph, o))
    return triples


# extract triples for a Statement node, optionally including triples defining
# the subject / object of the statement if they are ERE nodes
def triples_for_statement(kb_graph, stmt_id, include_subj_obj_def=False):
    assert stmt_id.startswith('assertion-')
    triples = triples_for_subject(kb_graph, LDC.term(stmt_id))
    ke_id_list = [LDC.term(stmt_id)]

    if include_subj_obj_def:
        # for all subjects of the statement
        for o in kb_graph.objects(
                subject=LDC.term(stmt_id), predicate=RDF.subject):
            # if the subject is an LDC node
            if isinstance(o, URIRef) and kb_graph.compute_qname(o)[0] == 'ldc':
                triples.extend(triples_for_subject(kb_graph, o))
                ke_id_list.append(o)
        # for all objects of the statement
        for o in kb_graph.objects(
                subject=LDC.term(stmt_id), predicate=RDF.object):
            # if the object is an LDC node
            if isinstance(o, URIRef) and kb_graph.compute_qname(o)[0] == 'ldc':
                triples.extend(triples_for_subject(kb_graph, o))
                ke_id_list.append(o)

    return triples, ke_id_list


# extract triples for a ClusterMembership node, optionally including triples
# defining the cluster / clusterMember.
def triples_for_coref(kb_graph, aida_graph, coref_id,
                      include_cluster_def=False, include_member_def=False):
    coref_node = aida_graph['theGraph'][coref_id]
    assert coref_node['type'] == 'ClusterMembership'
    cluster_id = coref_node['cluster']
    member_id = coref_node['clusterMember']

    cluster_id_subj_list = set(kb_graph.subjects(
        predicate=AIDA.cluster, object=LDC.term(cluster_id)))

    member_id_subj_list = set(kb_graph.subjects(
        predicate=AIDA.clusterMember, object=LDC.term(member_id)))

    common_subj_list = cluster_id_subj_list & member_id_subj_list
    assert len(common_subj_list) == 1
    cluster_membership_id = common_subj_list.pop()

    triples = triples_for_subject(kb_graph, cluster_membership_id)
    ke_id_list = [cluster_membership_id]

    if include_cluster_def:
        triples.extend(triples_for_subject(kb_graph, LDC.term(cluster_id)))
        ke_id_list.append(LDC.term(cluster_id))
    if include_member_def:
        triples.extend(triples_for_subject(kb_graph, LDC.term(member_id)))
        ke_id_list.append(LDC.term(member_id))

    return triples, ke_id_list


# build a subgraph from a list of statements for one AIDA result
def get_subgraph_for_result(
        kb_graph, aida_graph, prob, statements, include_subj_obj_def=False,
        include_cluster_def=False, include_member_def=False):
    all_triples = []
    all_ke_id_list = []

    for stmt in statements:
        # extract triples for Statement nodes
        if stmt.startswith('assertion-'):
            triples, ke_id_list = triples_for_statement(
                kb_graph=kb_graph, stmt_id=stmt,
                include_subj_obj_def=include_subj_obj_def)
            all_triples.extend(triples)
            all_ke_id_list.extend(ke_id_list)

        # extract triples for ClusterMembership nodes
        else:
            triples, ke_id_list = triples_for_coref(
                kb_graph=kb_graph, aida_graph=aida_graph, coref_id=stmt,
                include_cluster_def=include_cluster_def,
                include_member_def=include_member_def)
            all_triples.extend(triples)
            all_ke_id_list.extend(ke_id_list)

    subgraph = Graph()

    # bind all prefixes of kb_graph
    for prefix, namespace in kb_graph.namespaces():
        subgraph.bind(prefix, namespace)

    # remove unused prefix bindings
    subgraph.store._IOMemory__prefix = {
        key: val for key, val in subgraph.store._IOMemory__prefix.items()
        if val not in ['xml', 'xsd']}
    subgraph.store._IOMemory__namespace = {
        key: val for key, val in subgraph.store._IOMemory__namespace.items()
        if key not in ['xml', 'xsd']}

    # create a BNode for the hypothesis
    hypothesis_id = BNode()

    # add triple for type aida:hypothesis
    subgraph.add((hypothesis_id, RDF.type, AIDA.hypothesis))

    # add triples for the probability of the hypothesis
    confidence_id = BNode()
    subgraph.add((hypothesis_id, AIDA.confidence, confidence_id))
    subgraph.add((confidence_id, RDF.type, AIDA.Confidence))
    subgraph.add((confidence_id, AIDA.confidenceValue, Literal(prob)))

    # add triples for all aida:hypothesisContent edges
    for ke_id in all_ke_id_list:
        subgraph.add((hypothesis_id, AIDA.hypothesisContent, ke_id))

    # add triples for the subgraph
    for triple in all_triples:
        subgraph.add(triple)

    return subgraph


def main():
    parser = ArgumentParser()
    parser.add_argument('aida_graph_path', help='path to aidagraph.json')
    parser.add_argument('aida_result_path', help='path to aidaresult.json')
    parser.add_argument('kb_path', help='path to T10x.kb.ttl')
    parser.add_argument('output_dir', help='path to output directory')
    parser.add_argument('--top', default=3, type=int,
                        help='number of top hypothesis to output')

    args = parser.parse_args()

    print('Reading AIDA graph from {}'.format(args.aida_graph_path))
    with open(args.aida_graph_path, 'r') as fin:
        aida_graph = json.load(fin)

    print('Reading AIDA result from {}'.format(args.aida_result_path))
    with open(args.aida_result_path, 'r') as fin:
        aida_result = json.load(fin)

    print('Reading kb from {}'.format(args.kb_path))
    kb_graph = Graph()
    kb_graph.parse(args.kb_path, format='ttl')

    if not exists(args.output_dir):
        print('Creating output directory {}'.format(args.output_dir))
        makedirs(args.output_dir)

    print('Found {} hypothesese with probability {}'.format(
        len(aida_result['probs']), aida_result['probs']))

    top_count = 0
    for result_idx, prob in sorted(
            enumerate(aida_result['probs']), key=itemgetter(1), reverse=True):
        result = aida_result['support'][result_idx]
        subgraph = get_subgraph_for_result(
            kb_graph=kb_graph, aida_graph=aida_graph, prob=prob,
            statements=result['statements'], include_subj_obj_def=True,
            include_cluster_def=True, include_member_def=True)

        top_count += 1

        output_path = join(
            args.output_dir, 'hypothesis-{}.ttl'.format(top_count))
        print('Writing to top #{} hypothesis with prob {} to {}'.format(
            top_count, prob, output_path))
        with open(output_path, 'w') as fout:
            fout.write(print_graph(subgraph))

        if top_count >= args.top:
            break


if __name__ == '__main__':
    main()
