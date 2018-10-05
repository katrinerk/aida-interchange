import json
import sys
from collections import defaultdict

import rdflib
from rdflib.namespace import Namespace, split_uri

fin_path = sys.argv[1]
fout_path = sys.argv[2]

LDC = Namespace(
    'https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/LdcAnnotations#')
AIDA = Namespace(
    'https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/InterchangeOntology#')
LDC_ONT = Namespace(
    'https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/SeedlingOntology#')
RDF = Namespace(
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#')

print('Initialize neighbors mapping...')
neighbors_mapping = {
    # neighbors of EREs in ClusterMembership nodes
    'zero-hop-ere': defaultdict(set),
    # neighbors of Clusters in ClusterMembership nodes
    'zero-hop-cluster': defaultdict(set),
    # neighbors of subjects in general statements
    'half-hop-subj': defaultdict(set),
    # neighbors of objects in general statements
    'half-hop-obj': defaultdict(set),
    # one-hop neighbors of EREs in typing statements
    'one-hop': defaultdict(set)
}

print('Reading triples from {}...'.format(fin_path))
g = rdflib.Graph()
g.parse(fin_path, format='ttl')
print('Done.')

print('Processing ClusterMembership nodes...')
# cluster and member in a ClusterMembership node have zero-hop distance
for coref in g.subjects(predicate=RDF.type, object=AIDA.ClusterMembership):
    for cluster in g.objects(subject=coref, predicate=AIDA.cluster):
        for member in g.objects(subject=coref, predicate=AIDA.clusterMember):
            neighbors_mapping['zero-hop-ere'][member].add(cluster)
            neighbors_mapping['zero-hop-cluster'][cluster].add(member)
print('Done.')

print('Processing Statement nodes...')
for statement in g.subjects(predicate=RDF.type, object=RDF.Statement):
    for pred in g.objects(subject=statement, predicate=RDF.predicate):
        pred_namespace, pred_name = split_uri(pred)
        # if the predicate lives in the RDF namespace
        # (and it must be a typing statement), this is a one-hop
        if pred_namespace == RDF:
            assert pred_name == 'type'
            distance = 'one-hop'
        # if the predicate lives in the LDC_ONT namespace, this is a half-hop
        else:
            assert pred_namespace == LDC_ONT
            distance = 'half-hop'

        for subj in g.objects(subject=statement, predicate=RDF.subject):
            for obj in g.objects(subject=statement, predicate=RDF.object):
                if distance == 'half-hop':
                    neighbors_mapping['half-hop-subj'][subj].add(obj)
                    neighbors_mapping['half-hop-obj'][obj].add(subj)
                else:
                    neighbors_mapping['one-hop'][subj].add(obj)
print('Done.')

# convert sets to lists for json dump
for distance, neighbors in neighbors_mapping.items():
    for key in neighbors:
        neighbors[key] = list(neighbors[key])

print('Writing json output to {}...'.format(fout_path))
with open(fout_path, 'w') as fout:
    json.dump(neighbors_mapping, fout, indent=2)
