# Data structure for managing coreference:
# Basically a unification data structure
# that keeps, for each groups of coreferent EREs,
# a representative unifier


# data structure for managing coreference
# by having a single representative "unifier" for each
# coreference group.
class EREUnify:
    def __init__(self):
        self.unifier = { }

    # ere: a string label for an ERE (entity, relation, event)
    # add to the data structure.
    def add(self, ere):
        if ere not in self.unifier:
            self.unifier[ere] = ere

    # ere: a string label for an ERE
    # coref: representative unifier
    # make it so that the unifier of ere is coref.
    # any EREs that have 'ere' as their representative unifier
    # will be made to point to 'coref' instead.
    def unify_ere_coref(self, ere, coref):
        ereu = self.get_unifier(ere)
        if ereu != coref:
            # unification needed
            self.unifier[ ere] = coref
            # if any other variable points to 'ere', make it point to 'coref'
            for var in self.unifier.keys():
                if self.unifier[var] == ere:
                    self.unifier[var] = coref


    # ell: string label for an ERE
    # returns the representative unifier for ell.
    # if ell is not in the data structure, it is assumed to point to itself.
    def get_unifier(self, ell):
        return self.unifier.get(ell, ell)

    # make a new datastructure like self.unifier
    # that maps all EREs to new unifiers.
    # the new data structure is a dictionary.
    # its keys are the same EREs that are listed in self.unifier.
    # the representative unifiers that are the values are all new. 
    def all_new_names(self):
        retv = { }
        oldname_newname = { }
        namecount = 0

        for ere, ereu in self.unifier.items():
            if ereu not in oldname_newname:
                oldname_newname[ereu] = "ERE" + str(namecount)
                namecount += 1

                
            retv[ere] = oldname_newname[ereu]

        return retv

    # make an inverted version of self.unifier
    # in which each representative unifier
    # is mapped to the set of its cluster member names
    def get_clusters(self):
        retv = { }

        for ere, ereu in self.unifier.items():
            if ereu not in retv:
                retv[ ereu ] = set()
                
            retv[ereu].add(ere)

        return retv

    # return a set of all cluster prototypes/
    # representative unifiers
    def get_prototypes(self):
        return set(self.unifier.values())

    # return a list of all cluster members
    # recorded in self.unifier
    def get_members(self):
        return list(self.unifier.keys())
