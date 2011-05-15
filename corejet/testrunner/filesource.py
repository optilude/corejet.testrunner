from corejet.core.model import RequirementsCatalogue

def fileSource(path):
    """Read a file containing a CoreJet XML document
    """
    
    catalogue = RequirementsCatalogue()
    with open(path) as stream:
        catalogue.populate(stream)
    return catalogue
