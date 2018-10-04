import json
import sys
from collections import defaultdict
from pathlib import Path

fin_dir = Path(sys.argv[1])
fout_path = sys.argv[2]

print('Initialize neighbors mapping...')
neighbors_mapping_all = {
    'zero-hop': defaultdict(set),
    'half-hop': defaultdict(set),
    'one-hop': defaultdict(set)
}

print('Reading all split neighbor information from directory {}...'.format(fin_dir))
for fin_path in sorted(fin_dir.glob('*.json')):
    print('Loading neighbor information from {}...'.format(fin_path))
    with open(fin_path, 'r') as fin:
        neighbors_mapping = json.load(fin)
        for distance, neighbors in neighbors_mapping.items():
            for key, val in neighbors.items():
                neighbors_mapping_all[distance][key].update(set(val))

# convert sets to lists for json dump
for distance, neighbors in neighbors_mapping_all.items():
    for key in neighbors:
        neighbors[key] = list(neighbors[key])

print('Writing json output to {}...'.format(fout_path))
with open(fout_path, 'w') as fout:
    json.dump(neighbors_mapping_all, fout, indent=2)
