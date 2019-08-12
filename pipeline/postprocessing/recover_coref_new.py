import json
from argparse import ArgumentParser
from pathlib import Path


parser = ArgumentParser()
parser.add_argument('input_hypotheses_path',
                    help='path to the input json file for hypotheses')
parser.add_argument('input_log_path',
                    help='path to log file from coref compression')
parser.add_argument('output_hypotheses_path',
                    help='path to write the coref-recovered hypotheses')

args = parser.parse_args()

input_hypotheses_path = Path(args.input_hypotheses_path)
assert input_hypotheses_path.exists(), '{} does not exist!'.format(
    input_hypotheses_path)

print('Reading hypotheses from {}'.format(input_hypotheses_path))
with open(input_hypotheses_path, 'r') as fin:
    input_hypotheses_json = json.load(fin)

input_log_path = Path(args.input_log_path)
assert input_log_path.exists(), '{} does not exist!'.format(input_log_path)

print('Reading coref log from {}'.format(input_log_path))
with open(input_log_path, 'r') as fin:
    input_log_json = json.load(fin)

output_hypotheses_json = {}

# probs do not change
output_hypotheses_json['probs'] = input_hypotheses_json['probs']

output_hypotheses_json['support'] = []

for hypothesis in input_hypotheses_json["support"]:
    # Resolve the statements and weights before coref-compression
    new_stmt_weight_mapping = {}
    for old_stmt, stmt_weight in zip(hypothesis['statements'],
                                     hypothesis['statementWeights']):
        for new_stmt in input_log_json['new_stmt_to_old_stmts'][old_stmt]:
            if new_stmt not in new_stmt_weight_mapping:
                new_stmt_weight_mapping[new_stmt] = stmt_weight
            elif new_stmt_weight_mapping[new_stmt] < stmt_weight:
                new_stmt_weight_mapping[new_stmt] = stmt_weight

    new_hypothesis = {'statements': [], 'statementWeights': []}
    for new_stmt, stmt_weight in new_stmt_weight_mapping.items():
        new_hypothesis['statements'].append(new_stmt)
        new_hypothesis['statementWeights'].append(stmt_weight)

    new_hypothesis['failedQueries'] = hypothesis['failedQueries']

    new_query_stmts = set()
    for old_query_stmt in hypothesis['queryStatements']:
        new_query_stmts.update(
            input_log_json['new_stmt_to_old_stmts'][old_query_stmt])
    new_hypothesis['queryStatements'] = list(new_query_stmts)

    output_hypotheses_json['support'].append(new_hypothesis)

if 'graph' in input_hypotheses_json:
    output_hypotheses_json['graph'] = input_hypotheses_json['graph']
if 'queries' in input_hypotheses_json:
    output_hypotheses_json['queries'] = input_hypotheses_json['queries']

output_hypotheses_path = Path(args.output_hypotheses_path)
print('Writing coref-recovered hypotheses to {}'.format(output_hypotheses_path))
with open(output_hypotheses_path, 'w') as fout:
    json.dump(output_hypotheses_json, fout, indent=2)
