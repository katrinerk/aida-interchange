import json
from argparse import ArgumentParser
from io import BytesIO

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

UTEXAS_PREFIX = 'http://www.utexas.edu/aida/'


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


def get_subgraph_for_hard_coref(aidaquery, soin_id):
    cluster_prefix = UTEXAS_PREFIX + 'entrypoint-coref/{}/'.format(soin_id)
    print('Using prefix {} for cluster node names'.format(cluster_prefix))

    system_node = URIRef(UTEXAS_PREFIX + 'system')

    prototypes = set([])
    for entrypoint in aidaquery['entrypoints']:
        prototypes.update(entrypoint['ere'])

    print('Prototypes: {}'.format(prototypes))

    all_triples = []

    for cluster, member_list in aidaquery['coref'].items():
        cluster_node = URIRef(cluster_prefix + 'facet-cluster-' + cluster)
        print('Adding SameAsCluster node {}'.format(cluster_node))
        all_triples.append((cluster_node, RDF.type, AIDA.SameAsCluster))
        all_triples.append((cluster_node, AIDA.system, system_node))

        for member in member_list:
            # add new clusterMembership node
            cluster_membership_node = BNode()

            print('Adding ClusterMembership node {} for member {}'.format(
                cluster_membership_node, member))

            all_triples.append((
                cluster_membership_node, RDF.type, AIDA.ClusterMembership))
            all_triples.append((
                cluster_membership_node, AIDA.cluster, cluster_node))
            all_triples.append((
                cluster_membership_node, AIDA.clusterMember, URIRef(member)))
            all_triples.append((
                cluster_membership_node, AIDA.system, system_node))

            confidence_node = BNode()
            all_triples.append((
                cluster_membership_node, AIDA.confidence, confidence_node))
            all_triples.append((
                confidence_node, RDF.type, AIDA.Confidence))
            all_triples.append((
                confidence_node, AIDA.confidenceValue, Literal(1.0)))
            all_triples.append((
                confidence_node, AIDA.system, system_node))

            if member in prototypes:
                all_triples.append((
                    cluster_node, AIDA.prototype, URIRef(member)))

    subgraph = Graph()

    subgraph.bind('aida', AIDA)

    # add triples for the subgraph
    for triple in all_triples:
        subgraph.add(triple)

    return subgraph


def main():
    parser = ArgumentParser()
    parser.add_argument('soin_id', help='id of the SOIN')
    parser.add_argument('aidaquery_path', help='path to aidaquery.json')
    parser.add_argument('output_path', help='path to output ttl file')

    args = parser.parse_args()

    print('Reading aidaquery.json from {}'.format(args.aidaquery_path))
    with open(args.aidaquery_path, 'r') as fin:
        aidaquery = json.load(fin)

    subgraph = get_subgraph_for_hard_coref(
        aidaquery=aidaquery, soin_id=args.soin_id)

    print('Writing subgraph of hard coref to {}'.format(args.output_path))
    with open(args.output_path, 'w') as fout:
        fout.write(print_graph(subgraph))


if __name__ == '__main__':
    main()
