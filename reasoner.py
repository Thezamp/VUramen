from py4j.java_gateway import JavaGateway
import sys
import itertools
import copy
import time

def load_onto(ontologyName):
    parser = gateway.getOWLParser()

    # load an ontology from a file
    ontology = parser.parseFile(ontologyName)
    gateway.convertToBinaryConjunctions(ontology)

    return ontology


def subsumers(ontologyName='pizza.owl', className='"Margherita"'):
    # IMPORTANT
    # remember to have "" in the class name (NEED TO append FORMAT CHECK)

    elFactory = gateway.getELFactory()
    ontology = load_onto(ontologyName)
    axioms = ontology.tbox().getAxioms()
    formatter = gateway.getSimpleDLFormatter()  # likely for debug

    # convert A = B axioms into A<=B, B<=A
    GCIaxioms = [x for x in axioms if x.getClass().getSimpleName() == "GeneralConceptInclusion"]
    equivalenceAxioms = [x for x in axioms if x.getClass().getSimpleName() == "EquivalenceAxiom"]

    for axiom in equivalenceAxioms:
        GCIaxioms.append(elFactory.getGCI(
            axiom.getConcepts()[0],
            axiom.getConcepts()[1]
        ))
        GCIaxioms.append(elFactory.getGCI(
            axiom.getConcepts()[1],
            axiom.getConcepts()[0]
        ))

    # the subsumers are among these this is the whole input
    allConcepts = ontology.getSubConcepts()

    # prepare for the algorithm:

    # dictionary for interpeting the concepts
    conceptsByElement = dict()
    rolesByElement = dict()

    conceptsByElement['d0'] = set()
    rolesByElement['d0'] = set()
    initialConcept = elFactory.getConceptName(className)

    conceptsByElement['d0'].add(initialConcept)
    dcounter = 1

    changed = True
    t = time.time()
    while changed:
        changed = False

        # apply all the rules
        extendedModel = conceptsByElement.copy()  # this if new elements are created. Cannot create new 'keys' while looping
        for d in conceptsByElement.keys():
            updatedConcepts = conceptsByElement[d].copy()
            # Top-rule
            if elFactory.getTop() not in conceptsByElement[d]:
                updatedConcepts.add(elFactory.getTop())
                changed = True

            # GCI-rule
            for gci in GCIaxioms:
                if (gci.lhs() in conceptsByElement[d] and
                        gci.rhs() not in conceptsByElement[d]):
                    updatedConcepts.add(gci.rhs())
                    changed = True

            # n-rule 1
            for c in conceptsByElement[d]:

                if c.getClass().getSimpleName() == "ConceptConjunction":
                    if c.getConjuncts()[0] not in conceptsByElement[d]:
                        updatedConcepts.add(c.getConjuncts()[0])
                        changed = True
                    if c.getConjuncts()[1] not in conceptsByElement[d]:
                        updatedConcepts.add(c.getConjuncts()[1])
                        changed = True

            #this ensures that new info from the rules application are immediately integrated
            # - but maybe slows down the process
            # - opt 1: maybe update only at the end, this will requires more loops but less assignments
            # - opt 2: loop on find a way to loop only on a 'snapshot' shallow copy of the updatedConcepts, while actually changing the
            # original -- probably doesnt work

            # n-rule 2
            for c1, c2 in itertools.permutations(conceptsByElement[d], 2):

                conj = elFactory.getConjunction(c1, c2)
                if conj in allConcepts and conj not in conceptsByElement[d]:
                    updatedConcepts.add(conj)
                    changed = True

            #E-rule 1
            for c in conceptsByElement[d]:
                if c.getClass().getSimpleName() == "ExistentialRoleRestriction":

                    role = c.role()
                    filler = c.filler()

                    introduced = False

                    '''this is if no roles have yet been assigned to d, initialize the set to avoid out of bound'''
                    if d not in rolesByElement.keys():
                        rolesByElement[d] = set()
                    '''look if already-present elements are suitable candidates'''
                    for r_succ_candidate in extendedModel.keys():
                        if not introduced and filler in extendedModel[r_succ_candidate]:
                            '''there is an element e with initial concept C
                            this could have been previously introduced in any of the d iteration, we thus need to
                            look into the extendedModel already, otherwise two new elements with coinciding starting 
                            concepts will be created'''
                            if (role, r_succ_candidate) not in rolesByElement[d]:
                                rolesByElement[d].add((role, r_succ_candidate))
                                changed = True
                            introduced = True

                    if not introduced:
                        r_successor = f'd{dcounter}'
                        '''append a new r successor to d, assign the concept as initial concept'''
                        extendedModel[r_successor] = {filler}
                        dcounter += 1
                        changed = True
                        rolesByElement[d].add((role, r_successor))

            #E-rule 2
            if d in rolesByElement.keys():
                for role, r_succ_candidate in rolesByElement[d]:
                    for r_succ_concept in extendedModel[r_succ_candidate]:
                        newConcept = elFactory.getExistentialRoleRestriction(role, r_succ_concept)
                        if newConcept not in conceptsByElement[d] and newConcept in allConcepts:
                            updatedConcepts.add(newConcept)
                            changed = True

            # disj rule

            # only rule

            extendedModel[d] = updatedConcepts


        conceptsByElement = extendedModel

    t1 = time.time()
    #print(f'elapsed: {t1 - t}')
    conceptNames = ontology.getConceptNames()
    out = []
    for concept in conceptsByElement['d0']:
        #print(formatter.format(concept))
        if (concept in conceptNames) or (concept == elFactory.getTop()):
            #to verify if we want to add also non 'named' concepts
            #print(formatter.format(concept))
            out.append(concept)
    return t1-t, out


gateway = JavaGateway()
#subsumers(sys.argv[1],sys.argv[2])
#subsumers('vuramen.ttl', 'VeganTagRamen')
#subsumers('ontologies/Project-1/eco.evidence-and-conclusion-ontology.49.owl.xml', 'ECO_0000003')
#subsumers()

