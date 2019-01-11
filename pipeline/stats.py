import rdflib
import sys
from aif import AidaGraph

input_path = sys.argv[1]

print('Reading ttl file from {}...'.format(input_path))
g = rdflib.Graph()
g.parse(input_path, format='ttl')
print('Done.')

print('Found {} triples.'.format(len(g)))

print('Adding all triples to AidaGraph...')
mygraph = AidaGraph()
mygraph.add_graph(g)
print('Done.')

print('Printing statistics...')
print('Found {} nodes.'.format(len(list(mygraph.nodes()))))
print('Found {} Entity nodes.'.format(len(list(mygraph.nodes('Entity')))))
print('Found {} Relation nodes.'.format(len(list(mygraph.nodes('Relation')))))
print('Found {} Event nodes.'.format(len(list(mygraph.nodes('Event')))))
print('Found {} Statement nodes.'.format(len(list(mygraph.nodes('Statement')))))
print('Found {} SameAsCluster nodes.'.format(len(list(mygraph.nodes('SameAsCluster')))))
print('Found {} ClusterMembership nodes.'.format(len(list(mygraph.nodes('ClusterMembership')))))

