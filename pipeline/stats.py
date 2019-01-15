import argparse
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
    num_statements = len(list(graph.nodes('Statement')))

    if num_statements > 0:
        perc_type_statements= (len(list(g for g in graph.nodes('Statement') if g.has_predicate("type", shorten = True))) / num_statements) * 100
    else:
        perc_type_statements = 0

    num_entities = len(list(graph.nodes('Entity')))

    if num_entities > 0:
        # a singleton entity is one that only has type statements
        # and no other statements or relations attached
        singleton_entities = [ ]
        for node in graph.nodes('Entity'):
            
            singleton = True
            
            for pred, subjlabels in node.inedge.items():
                if not singleton:
                    break
                for subjlabel in subjlabels:
                    subjnode = graph.get_node(subjlabel)
                    if subjnode and (subjnode.is_relation() or (subjnode.is_statement() and not subjnode.is_type_statement())):
                        singleton = False
                        break
            if singleton:
                singleton_entities.append(node)

        perc_singleton_entities = len(singleton_entities) / num_entities * 100
    else:
        perc_singleton_entities = 0

    num_events = len(list(graph.nodes('Event')))

    if num_events > 0:
        # a singleton entity is one that only has type statements
        # and no other statements or relations attached
        singleton_events = []
        for node in graph.nodes('Event'):

            singleton = True

            for pred, subjlabels in node.inedge.items():
                if not singleton:
                    break
                for subjlabel in subjlabels:
                    subjnode = graph.get_node(subjlabel)
                    if subjnode and (subjnode.is_relation() or (subjnode.is_statement() and not subjnode.is_type_statement())):
                        singleton = False
                        break
            if singleton:
                singleton_events.append(node)

        perc_singleton_events = len(singleton_events) / num_events * 100
    else:
        perc_singleton_events = 0

    return {
        '# Nodes': len(list(graph.nodes())),
        '# Entities': num_entities,
        '% Singleton Entities': perc_singleton_entities,
        '# Relations': len(list(graph.nodes('Relation'))),
        '# Events': num_events,
        '% Singleton Events': perc_singleton_events,
        '# Statements': num_statements,
        '% Type Statements': perc_type_statements,
        '# SameAsClusters': len(list(graph.nodes('SameAsCluster'))),
        '# ClusterMemberships': len(list(graph.nodes('ClusterMembership')))
    }


def file_stats(input_file):
    print('Reading AIF file from {}...'.format(input_file))
    g = rdflib.Graph()
    g.parse(input_file, format='ttl')
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


def directory_stats(input_dir, suffix=None, filename_list=None):
    print('Reading AIF files from {}...'.format(input_dir))
    if suffix:
        file_list = [f for f in Path(input_dir).glob('*.{}'.format(suffix))
                     if f.is_file()]
    else:
        file_list = [f for f in Path(input_dir).iterdir() if f.is_file()]
    print('Found {} articles'.format(len(file_list)))

    if filename_list is not None:
        print('Constraining by a filename list of {} entries'.format(
            len(filename_list)))
        file_list = [f for f in file_list if f.stem in filename_list]
        print('Get {} articles after filtering'.format(len(file_list)))

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
        print('{}: mean = {:.2f}, min = {:.2f}, max = {:.2f}'.format(
            key, sum(val) / len(val), min(val), max(val)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_path', help='path to the input file/directory')
    parser.add_argument('--suffix', '-s',
                        help='file suffix to match files in the input '
                             'directory, default to empty (run over all files)')
    parser.add_argument('--filename_list', '-l',
                        help='a text file containing the filenames that we '
                             'want to include in the statistics')

    args = parser.parse_args()

    if Path(args.input_path).is_file():
        file_stats(args.input_path)
    else:
        if args.filename_list is not None:
            with open(args.filename_list, 'r') as fin:
                filename_list = [line.strip() for line in fin]
        else:
            filename_list = None
        directory_stats(args.input_path, args.suffix, filename_list)
