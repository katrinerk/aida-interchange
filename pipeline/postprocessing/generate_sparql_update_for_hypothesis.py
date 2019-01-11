# Pengxiang Cheng Fall 2018
# part of pre- and postprocessing for AIDA eval

from argparse import ArgumentParser
from os import makedirs
from os.path import exists, join

parser = ArgumentParser()
parser.add_argument('frame_id', help='Frame ID of the hypotheses')
parser.add_argument('output_dir', help='Directory to write queries')
parser.add_argument('--num_hypotheses', type=int, default=3,
                    help='Number of hypotheses, default is 3')

args = parser.parse_args()

frame_id = args.frame_id

output_dir = args.output_dir
if not exists(output_dir):
    makedirs(output_dir)

update_prefix = \
    'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' \
    'PREFIX aida: <https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/' \
    'InterchangeOntology#>\n' \
    'PREFIX utexas: <http://www.utexas.edu/aida/>\n\n'

for idx in range(1, args.num_hypotheses + 1):
    hypotheses_id = '{}_hypothesis_{}'.format(frame_id, idx)

    update_str_1 = update_prefix
    update_str_1 += \
        'INSERT DATA {{ utexas:{} rdf:type aida:Hypothesis . }}\n'.format(
            hypotheses_id)

    output_path_1 = join(output_dir, '{}_update_1.rq'.format(
        hypotheses_id))
    with open(output_path_1, 'w') as fout:
        fout.write(update_str_1)

    update_str_2 = update_prefix
    update_str_2 += \
        'INSERT {{ utexas:{} aida:hypothesisContent ?e }}\n' \
        'WHERE\n{{\n' \
        '{{ ?e rdf:type aida:Entity }}\nUNION\n' \
        '{{ ?e rdf:type aida:Relation }}\nUNION\n' \
        '{{ ?e rdf:type aida:Event }}\nUNION\n' \
        '{{ ?e rdf:type rdf:Statement }}\nUNION\n' \
        '{{ ?e rdf:type aida:SameAsCluster }}\nUNION\n' \
        '{{ ?e rdf:type aida:ClusterMembership }}\n}}\n'.format(hypotheses_id)

    output_path_2 = join(output_dir, '{}_update_2.rq'.format(
        hypotheses_id))
    with open(output_path_2, 'w') as fout:
        fout.write(update_str_2)
