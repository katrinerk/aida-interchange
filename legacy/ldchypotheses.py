# given a directory with LDC annotation about a single topic, in GAIA interface format,
# and given a directory with the matching original LDC annotation,
# identify all paths that link conflicting hypotheses
# and display them, most frequent last.
#
# usage:
# python3 ldchypotheses.py <interchangeformatdir> <ldcdir>

#######
# integrating LDC hypothesis annotation with the interface-format annotation

import sys

from legacy import AnnoExplore, Conflicting

## ## # ldcdir = "/Users/kee252/Documents/Projects/AIDA/data/LDC_scenario1_seedling/ldc_seedling_anno_v3/data/T101"
## ## # indir = "/Users/kee252/Documents/Projects/AIDA/data/LDC_scenario1_seedling/interchangeformat_2018-06-15/T101"

if len(sys.argv) != 3:
    print("usage:")
    print("python3 ldchypotheses.py <interchangeformatdir> <ldcdir>")
    sys.exit(1)

# read in the LDC annotation
indir = sys.argv[1]

mygraph = AnnoExplore.read_ldc_gaia_annotation(indir)

print("number of nodes:", len(mygraph.node))
print("number of entity nodes:", len(list(mygraph.nodes(targettype='Entity'))))
print("number of event nodes:", len(list(mygraph.nodes(targettype='Event'))))
print("number of relation nodes:", len(list(mygraph.nodes(targettype='Relation'))))

# read in the LDC hypothesis info
ldcdir = sys.argv[2]

ldc_obj = AnnoExplore.LDCAnno(ldcdir, mygraph)
if len(ldc_obj.mention_hypothesis) == 0:
    print("could not find hypothesis file")
    sys.exit(1)

print("number of mentions with associated hypotheses:", len(ldc_obj.mention_hypothesis))
print("number of mentions with associated graph nodes:", len(ldc_obj.mention_graphnodes))

conflict_obj = Conflicting.ConflictingEvidence(mygraph, ldc_obj)

conflict_obj.get_all_conflicting_mention_pairs()
print('number of mentions with at least one conflict: ', len(conflict_obj.conflicting_mention_map))

conflict_obj.detect_conflicting_paths()
print("#entries:", len(conflict_obj.conflict_path))


# print conflict paths
conflict_obj.print_conflict_paths()

## # for each hypothesis, determine supporting and conflicting evidence
# conflict_obj.detect_pro_and_con_evidence()
# conflict_obj.print_procon_evidence()
