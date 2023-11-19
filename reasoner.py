from py4j.java_gateway import JavaGateway
import sys
import itertools
import copy


def load_onto(ontologyName):
    parser = gateway.getOWLParser()
    formatter = gateway.getSimpleDLFormatter()
    print("Loading the ontology...")

    # load an ontology from a file
    ontology = parser.parseFile(ontologyName)

    print("Loaded the ontology!")

    print("Converting to binary conjunctions")
    gateway.convertToBinaryConjunctions(ontology)

    return ontology


def subsumers(ontologyName='pizza.owl', className='"Margherita"'):
    # IMPORTANT
    # remember to have "" in the class name (NEED TO append FORMAT CHECK)

    print(f'Finding the subsumers of class {className} in ontology {ontologyName}')

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
    roles = dict()

    conceptsByElement['d0'] = []
    rolesByElement['d0'] = []
    initialConcept = elFactory.getConceptName(className)

    # i don't like this but atm <concept> in <set> does not work
    conceptsByElement['d0'].append(initialConcept)
    dcounter = 1

    changed = True

    while changed:
        print('---')
        changed = False

        # apply all the rules
        possibleNewElements = dict()  # this if new elements are appended
        for d in conceptsByElement.keys():
            updatedConcepts = conceptsByElement[d].copy()
            # Top-rule
            if elFactory.getTop() not in conceptsByElement[d]:
                print(f'top-rule: appending Top to {d}')
                updatedConcepts.append(elFactory.getTop())
                changed = True

            # GCI-rule
            for gci in GCIaxioms:
                if (gci.lhs() in conceptsByElement[d] and
                        gci.rhs() not in conceptsByElement[d]):
                    print(f'GCI-rule: appending {formatter.format(gci.rhs())} to {d}')
                    updatedConcepts.append(gci.rhs())
                    changed = True

            # n-rule 1
            for c in conceptsByElement[d]:

                if c.getClass().getSimpleName() == "ConceptConjunction":
                    if c.getConjuncts()[0] not in conceptsByElement[d]:
                        print(f'CONJ-rule1: appending {formatter.format(c.getConjuncts()[0])} to {d}')
                        updatedConcepts.append(c.getConjuncts()[0])
                        changed = True
                    if c.getConjuncts()[1] not in conceptsByElement[d]:
                        print(f'CONJ-rule1: appending {formatter.format(c.getConjuncts()[1])} to {d}')
                        updatedConcepts.append(c.getConjuncts()[1])
                        changed = True

            conceptsByElement[d] = updatedConcepts
            updatedConcepts = conceptsByElement[d].copy()
            # n-rule 2
            for c1, c2 in itertools.permutations(conceptsByElement[d], 2):

                conj = elFactory.getConjunction(c1, c2)
                if conj in allConcepts and conj not in conceptsByElement[d]:
                    print(f'CONJ-rule2: appending {formatter.format(conj)}')
                    updatedConcepts.append(conj)
                    changed = True

            conceptsByElement[d] = updatedConcepts
            updatedConcepts = conceptsByElement[d].copy()

            #E-rule 1
            #optimization-wise, not ideal, but each rule might be changing hte concepts
            for c in conceptsByElement[d]:
                if c.getClass().getSimpleName() == "ExistentialRoleRestriction":

                    role = c.role()
                    filler = c.filler()

                    introduced = False

                    if d not in rolesByElement.keys():
                        rolesByElement[d] = []
                    # look if already-present elements are suitable candidates
                    for r_succ_candidate in conceptsByElement.keys():
                        if filler in conceptsByElement[r_succ_candidate] and not introduced:
                            # there is an element e with initial concept C --- need to verify if this works as intended
                            if (role, r_succ_candidate) not in rolesByElement[d]:
                                rolesByElement[d].append((role, r_succ_candidate))
                                changed = True
                                print(
                                    f'E-rule1 introducing a {formatter.format(role)}-successor from {d} to {r_succ_candidate}')
                            introduced = True

                    if not introduced:
                        r_successor = f'd{dcounter}'
                        # append a new r successor to d, assign the concept as initial concept
                        possibleNewElements[r_successor] = [filler]
                        dcounter += 1
                        changed = True
                        rolesByElement[d].append((role, r_successor))
                        print(
                            f'E-rule1 introducing a {formatter.format(role)}-successor from {d} to NEW element d{dcounter - 1}')

            conceptsByElement[d] = updatedConcepts
            updatedConcepts = conceptsByElement[d].copy()

            #E-rule 2
            if d in rolesByElement.keys():
                for role, r_succ_candidate in rolesByElement[d]:
                    if r_succ_candidate in conceptsByElement.keys():
                        for r_succ_concept in conceptsByElement[r_succ_candidate]:
                            newConcept = elFactory.getExistentialRoleRestriction(role, r_succ_concept)
                            if newConcept not in conceptsByElement[d] and newConcept in allConcepts:
                                updatedConcepts.append(newConcept)
                                changed = True
                        conceptsByElement[d] = updatedConcepts
                    else:
                        for r_succ_concept in possibleNewElements[r_succ_candidate]:
                            newConcept = elFactory.getExistentialRoleRestriction(role, r_succ_concept)
                            if newConcept not in conceptsByElement[d] and newConcept in allConcepts:
                                updatedConcepts.append(newConcept)
                                changed = True
                        conceptsByElement[d] = updatedConcepts

        for elem in possibleNewElements.keys():
            # probably updates need to happen before
            conceptsByElement[elem] = possibleNewElements[elem]

    print('end')


gateway = JavaGateway()
#subsumers(sys.argv[1],sys.argv[2])
#subsumers('vuramen.ttl', 'NoukouChickenRamen')
subsumers()
# if role not in roles.keys():
#     # this is a 'new' role
#     roles[role] = []
#
# introduced = False
#
# # look if already-present elements are suitable candidates
# for r_succ_candidate in conceptsByElement.keys():
#     if filler in conceptsByElement[r_succ_candidate] and not introduced:
#         # there is an element e with initial concept C --- need to verify if this works as intended
#         if ((d, r_succ_candidate) not in roles[role]):
#             roles[role].append((d, r_succ_candidate))
#             changed = True
#             print(f'E-rule1 introducing a {formatter.format(role)}-successor from {d} to {r_succ_candidate}')
#         introduced = True

# if not introduced:
#     r_successor = f'd{dcounter}'
#     # append a new r successor to d, assign the concept as initial concept
#     possibleNewElements[r_successor] = {filler}
#     dcounter += 1
#     changed = True
#     roles[role].append((d, r_successor))
#     print(f'E-rule1 introducing a {formatter.format(role)}-successor from {d} to NEW element d{dcounter-1}')

# for concept in allConcepts:
#     print(concept)
#     conceptInterp[concept.conceptNames()] = {'concept':concept, 'elements':[]}
#
# inputConcept = elFactory.getConceptName(className)
# print(inputConcept.conceptNames())
# if  inputConcept.conceptNames() not in conceptInterp.keys():
#     print('something is wrong')
#     return
# else:
#     conceptInterp[inputConcept.conceptNames()]['concept'] = inputConcept
#     conceptInterp[inputConcept.conceptNames()]['element'].append(f'd{dcounter}')
#     dcounter +=1
