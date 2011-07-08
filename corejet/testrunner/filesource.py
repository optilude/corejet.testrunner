from corejet.core.model import RequirementsCatalogue

# python 2.5 compatibility
from __future__ import with_statement 

def fileSource(path):
    """Read a file containing a CoreJet XML document
    """
    
    catalogue = RequirementsCatalogue()
    with open(path) as stream:
        catalogue.populate(stream)
    return catalogue
