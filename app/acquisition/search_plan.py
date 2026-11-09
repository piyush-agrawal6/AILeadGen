"""Deterministic bounded contact-oriented expansion; no AI copy requests."""
ALIASES={'dentists':['dentist','dental clinic','family dentist','cosmetic dentist','dental practice','orthodontist'],'hospitality':['hotel','boutique hotel','guest house','motel','bed and breakfast'],'legal':['law firm','solicitor','attorney','legal practice'],'real_estate':['estate agent','real estate agency','property management'],'home_services':['plumber','electrician','home repair','roofing contractor'],'restaurant':['restaurant','bistro','cafe'],'auto_repair':['auto repair','car mechanic','car repair'],'veterinary':['veterinarian','veterinary clinic','animal hospital']}
def queries(intent,maximum):
    plan=list(intent.queries);place=' '.join(intent.cities or intent.countries)
    for suffix in ('official website contact email','contact us email','about contact'):
        for vertical in intent.verticals:
            for phrase in ALIASES.get(vertical,[vertical.replace('_',' ')]):
                q=f'{phrase} {place} {suffix}'
                if q.casefold() not in {x.casefold() for x in plan}:plan.append(q)
    return plan[:maximum]

def family(query):
    lowered=query.casefold()
    return next((term for terms in ALIASES.values() for term in sorted(terms,key=len,reverse=True) if lowered.startswith(term)),lowered.split(' ',1)[0])
