import json
import sys
from pathlib import Path
from typing import Dict

from rdflib.namespace import split_uri


def process_file(input_path: Path, output_path: Path, ontology_mapping: Dict):
    assert input_path.is_file()

    print(f'Reading json graph from {input_path}')
    with open(str(input_path), 'r') as fin:
        graph_json = json.load(fin)

    for entry_label, entry in graph_json['theGraph'].items():
        if entry['type'] == 'Statement':
            subj = entry['subject']
            if entry['predicate'] == 'type':
                type_label = entry['object']
                type_namespace, type_name = split_uri(type_label)

                new_type_name = None
                if graph_json['theGraph'][subj]['type'] == 'Event':
                    if type_name in ontology_mapping['event_types']:
                        new_type_name = ontology_mapping['event_types'][type_name]
                    else:
                        print(f'{type_name} not found in event type mapping')
                elif graph_json['theGraph'][subj]['type'] == 'Relation':
                    if type_name in ontology_mapping['relation_types']:
                        new_type_name = ontology_mapping['relation_types'][type_name]
                    else:
                        print(f'{type_name} not found in relation type mapping')
                if new_type_name is not None:
                    new_type_label = type_namespace + new_type_name
                    graph_json['theGraph'][entry_label]['object'] = new_type_label
            else:
                role_name = entry['predicate']

                new_role_name = None
                if graph_json['theGraph'][subj]['type'] == 'Event':
                    if role_name in ontology_mapping['event_roles']:
                        new_role_name = ontology_mapping['event_roles'][role_name]
                    else:
                        print(f'{role_name} not found in event role mapping')
                elif graph_json['theGraph'][subj]['type'] == 'Relation':
                    if role_name in ontology_mapping['relation_roles']:
                        new_role_name = ontology_mapping['relation_roles'][role_name]
                    else:
                        print(f'{role_name} not found in relation role mapping')

                if new_role_name is not None:
                    graph_json['theGraph'][entry_label]['predicate'] = new_role_name

    print(f'Writing json graph with new ontology to {output_path}')
    with open(str(output_path), 'w') as fout:
        json.dump(graph_json, fout, indent=1)


def process_directory(input_path: Path, output_path: Path, ontology_mapping: Dict):
    assert input_path.is_dir()
    assert output_path.is_dir()

    input_file_list = []
    output_file_list = []
    for input_file_path in input_path.iterdir():
        if input_file_path.is_file():
            input_file_list.append(input_file_path)
            output_file_list.append(output_path / input_file_path.name)

    print(f'Found {len(input_file_list)} files in {input_path}')

    for input_file, output_file in zip(input_file_list, output_file_list):
        process_file(input_file, output_file, ontology_mapping)


if __name__ == '__main__':
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with open('old_to_new_ontology_mapping.json', 'r') as fin:
        ontology_mapping = json.load(fin)

    if input_path.is_file():
        process_file(input_path, output_path, ontology_mapping)
    else:
        process_directory(input_path, output_path, ontology_mapping)
