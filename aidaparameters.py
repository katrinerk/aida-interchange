# script that will set parameters in the aidagraph.json
# to be used in aidabaseline.wppl.
#
# It takes aidagraph.json as input, modifies it, and writes it out again.
#
# things that can be set here:
# * scale and rate for the gamma distribution used to set the cluster threshold
# * probability of cluster membership for an arbitrary candidate
# * number of particles to use
# * whether to print to screen all sampled cluster thresholds, proximity values, and
#   penalties incurred

from optparse import OptionParser
import json
import sys


usage = "usage: %prog [options] arg"
parser = OptionParser(usage)
parser.add_option("-s", "--shape", action = "store", dest = "shape", type = "float")
parser.add_option("-c", "--scale", action = "store", dest = "scale", type = "float")
parser.add_option("-p", "--prob", action = "store", dest = "baseprob", type = "float")
parser.add_option("-n", "--numsamples", action = "store", dest = "numsamples", type = "int")

(options, args) = parser.parse_args()

# reading the AIDA json file
f = open("aidagraph.json")
json_obj = json.load(f)
f.close()

if options.numsamples is not None:
    json_obj["numSamples"] = options.numsamples

if options.numsamples is not None:
    json_obj["memberProb"] = options.baseprob

    
if options.shape is not None:
    json_obj["parameters"]["shape"] = options.shape

if options.scale is not None:
    json_obj["parameters"]["scale"] = options.scale



# and writing it back out again
outf = open("aidagraph.json", "w")
json.dump(json_obj, outf, indent = 1)
outf.close
