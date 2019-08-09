# make a list of all event and relation role labels used in a given
# collection of json graph files

import json
import os
import sys
from os.path import dirname, realpath

from rdflib.namespace import split_uri

src_path = dirname(dirname(realpath(__file__)))
sys.path.insert(0, src_path)

from aif import AidaJson


def process(json_filename, event_roles, rel_roles, event_types, rel_types):
    with open(json_filename, 'r') as fin:
        graph_obj = AidaJson(json.load(fin))

    for _, stmt_node in graph_obj.each_statement():
        if stmt_node['predicate'] == 'type':
            type_name = split_uri(stmt_node['object'])[1]
            if graph_obj.is_event(stmt_node['subject']):
                event_types.add(type_name)
            elif graph_obj.is_relation(stmt_node['subject']):
                rel_types.add(type_name)
        else:
            if graph_obj.is_event(stmt_node['subject']):
                event_roles.add(stmt_node['predicate'])
            elif graph_obj.is_relation(stmt_node['subject']):
                rel_roles.add(stmt_node['predicate'])

    return event_roles, rel_roles, event_types, rel_types


def main():
    graphs = sys.argv[1]
    output_json = sys.argv[2]

    event_roles = set()
    rel_roles = set()
    event_types = set()
    rel_types = set()

    if os.path.isfile(graphs):
        print(graphs)
        event_roles, rel_roles, event_types, rel_types = process(
            graphs, event_roles, rel_roles, event_types, rel_types)

    elif os.path.isdir(graphs):
        for basename in os.listdir(graphs):
            print(basename)
            graph_filename = os.path.join(graphs, basename)
            event_roles, rel_roles, event_types, rel_types = process(
                graph_filename, event_roles, rel_roles, event_types, rel_types)

    type_and_role_list = {
        'event_types': sorted(list(event_types)),
        'event_roles': sorted(list(event_roles)),
        'relation_types': sorted(list(rel_types)),
        'relation_roles': sorted(list(rel_roles))
    }

    with open(output_json, 'w') as fout:
        json.dump(type_and_role_list, fout, indent=2)

    print("================")
    print("Event roles")
    print("================")

    for role in sorted(event_roles):
        print(role)

    print("================")
    print("Relation roles")
    print("================")

    for role in sorted(rel_roles):
        print(role)

    print("================")
    print("Event types")
    print("================")

    for type in sorted(event_types):
        print(type)

    print("================")
    print("Relation types")
    print("================")

    for type in sorted(rel_types):
        print(type)


if __name__ == '__main__':
    main()
