# Pengxiang Cheng Fall 2018:
# preprocessing for AIDA eval
# determine zero-hop, half-hop, one-hop adjacencies
# BUGGY: does hops based on statements, not entities

import rdflib
import sys


namespace_aida= rdflib.Namespace("https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/InterchangeOntology#")
namespace_ldc = rdflib.Namespace("https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/LdcAnnotations#")

infilename = sys.argv[1]
g = rdflib.Graph()
g.parse(infilename, format="ttl")

# adjacent, zero-hop:
# mapping node numbers to sets of node numbers
adj0 = { }
# adjacent, half-hop
adj05 = { }
# adjacent, one-hop
adj1 = { }

def record_adj(node1, node2, adj):
    if node1 not in adj:
        adj[node1] = set()
    if node2 not in adj:
        adj[ node2] = set()

    adj[node1].add(node2)
    adj[node2].add(node1)
    

# determine zero-hop adjacencies: cluster nodes to prototypes
for clusternode in g.subjects(rdflib.RDF.type, namespace_aida.SameAsCluster):
    for protonode in g.objects(subject = clusternode, predicate = namespace_aida.prototype):
        record_adj(clusternode, protonode, adj0)

for corefnode in g.subjects(rdflib.RDF.type, namespace_aida.ClusterMembership):
    for clusternode in g.objects(subject = corefnode, predicate = namespace_aida.cluster):
        for membernode in g.objects(subject = corefnode, predicate = namespace_aida.clusterMember):
            record_adj(clusternode, membernode, adj0)

# determine half-hop adjacencies
for statementnode in g.subjects(rdflib.RDF.type, rdflib.RDF.Statement):
    # if both the subject and object of this statement live in the LDC namespace, this is a half-hop
    for subjnode in g.objects(subject = statementnode, predicate = rdflib.RDF.subject):
        snamespace, label = rdflib.namespace.split_uri(subjnode)
        if snamespace == namespace_ldc:
            for objnode in g.objects(subject = statementnode, predicate = rdflib.RDF.object):
                onamespace, label = rdflib.namespace.split_uri(objnode)
                if onamespace == namespace_ldc:
                    record_adj(subjnode, objnode, adj05)


# determine one-hop adjacencies
