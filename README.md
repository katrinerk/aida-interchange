# aida-interchange
scripts for accessing the AIDA interchange format

# 2 packages with classes:
* RDFGraph, RDFnode provide basic access to RDF data in a way that groups all subj/pred/obj triples by subj
* AidaGraph, AidaNode provide access to RDF data that has AIDA data in the GAIA interface format. It has methods that pretty-print nodes and explore their environment, traverse the graph, determine type and KB-entry knowledge for entities and events, and iterate over all entities and events in the graph.

# Demo scripts:

# rdftest : read in a .ttl file, write out as subj/pred/obj triples, 
# write out with prettyprint() from our internal graph format
python3 rdftest.py [infile.ttl] 

# aidagraphtest: showcases a number of methods of the AidaGraph method
python3 aidagraphtest.py [infile.ttl]

# neighborexplore: showcases the whois() prettyprint function
python3 neighborexplore.py [infile.ttl]

# ldchypotheses: The LDC annotation has descriptions of entity/event mentions, and says which entity/event mentions fully support, partially support, or contradict particular hypotheses that they have been annotating for. This script integrates that information with the AidaGraph, and prints out all paths in the graph where the start nodes supports a particular hypothesis and the end node contradicts it (or vice versa). This is quite rudimentary and could be improved
python3 ldchypotheses.py [indir] [ldcdir]
where indir is a directory with .ttl data in interchange format, for example on T101, and ldcdir is the corresponding [ldcdata]/data/Tsomething directory
