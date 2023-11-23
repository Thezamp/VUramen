import reasoner
from reasoner import *
from py4j.java_gateway import JavaGateway
import time
import pandas as pd

gateway = JavaGateway()
formatter = gateway.getSimpleDLFormatter()
parser = gateway.getOWLParser()

elk = gateway.getELKReasoner()
hermit = gateway.getHermiTReasoner() # might the upper case T!

ontologies = ['vuramen.ttl',
              'pizza.owl',
              'ontologies/Project-1/amino-acid.amino-acid-ontology.2.owl.xml'
    ,'ontologies/Project-1/foodon.foodon.1.owl.xml'
              ]

temp_df = []
for ontoName in ontologies:
    print(f'ontology: {ontoName}')
    #get the ontology
    ontology = parser.parseFile(ontoName)

    elk.setOntology(ontology)
    hermit.setOntology(ontology)

    #find some classes
    allConcepts = ontology.getConceptNames()
    for i in [0,4,9]:

        concept = allConcepts.toArray()[i]
        print(f'\tconcept: {concept.toString()}')
        t_alg,found_alg = subsumers(ontoName,concept.toString())

        t0 = time.time()
        elk_subsumers = elk.getSubsumers(concept).toArray()
        elk_time = time.time()-t0

        t1= time.time()
        hermit_subsumers = hermit.getSubsumers(concept).toArray()
        hermit_time =time.time()-t1

        temp_df.append({'onto':ontoName,
                        'concept':concept.toString(),
                        'alg_time': t_alg,
                        'alg_found' : len(found_alg),
                        'alg_subsumers': [x.toString() for x in found_alg],
                        'elk_time': elk_time,
                        'elk_found': len(elk_subsumers),
                        'elk_subsumers': [x.toString() for x in elk_subsumers],
                        'hermit_time':hermit_time,
                        'hermit_fount': len(hermit_subsumers),
                        'hermit_subsumers': [x.toString() for x in hermit_subsumers]})

df = pd.DataFrame(temp_df)
df.to_csv('tests.csv')