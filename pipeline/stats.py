import sys
from collections import defaultdict
from os.path import dirname, realpath
from pathlib import Path

import rdflib
from tqdm import tqdm

src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from aif import AidaGraph


def get_stats(graph):
    return {
        '# Nodes': len(list(graph.nodes())),
        '# Entities': len(list(graph.nodes('Entity'))),
        '# Relations': len(list(graph.nodes('Relation'))),
        '# Events': len(list(graph.nodes('Event'))),
        '# Statements': len(list(graph.nodes('Statement'))),
        '# SameAsClusters': len(list(graph.nodes('SameAsCluster'))),
        '# ClusterMemberships': len(list(graph.nodes('ClusterMembership')))
    }


def file_stats(input_file):
    print('Reading AIF file from {}...'.format(input_file))
    g = rdflib.Graph()
    g.parse(input_path, format='ttl')
    print('Done.')

    print('Found {} triples.'.format(len(g)))
    print('Adding all triples to AidaGraph...')
    graph = AidaGraph()
    graph.add_graph(g)
    print('Done.')

    stats = get_stats(graph)

    print('Printing statistics...')
    for key, val in stats.items():
        print('{}: {}'.format(key, val))


def directory_stats(input_dir):
    print('Reading AIF files from {}...'.format(input_dir))
    file_list = [f for f in Path(input_dir).iterdir() if f.is_file()]
    print('Find {} files in the directory.'.format(len(file_list)))

    stats_list = defaultdict(list)

    for input_f in tqdm(file_list):
        g = rdflib.Graph()
        g.parse(str(input_f), format='ttl')
        graph = AidaGraph()
        graph.add_graph(g)

        stats = get_stats(graph)

        for key, val in stats.items():
            stats_list[key].append(val)

    print('Printing statistics...')
    for key, val in stats_list.items():
        print('{}: mean = {:.2f}, min = {}, max = {}'.format(
            key, sum(val) / len(val), min(val), max(val)))


if __name__ == '__main__':
    input_path = sys.argv[1]

    if Path(input_path).is_file():
        file_stats(input_path)
    else:
        directory_stats(input_path)
