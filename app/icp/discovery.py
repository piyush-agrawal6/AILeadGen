"""Honest translation from approved ICP criteria to existing discovery inputs."""
from app.icp.service import get
from app.config.locations import country
from app.prospecting.criteria import SearchCriteria

VERTICALS = {
    'hospitality': ('hotel', 'hotels', 'hospitality', 'accommodation'),
    'real_estate': ('real estate', 'property'),
    'restaurant': ('restaurants', 'restaurant'),
    'dentists': ('dentists', 'dentistry', 'dental clinics'),
    'home_services': ('home services',),
    'auto_repair': ('auto repair',),
    'legal': ('legal', 'law firms'),
    'veterinary': ('veterinary', 'veterinarians'),
}


def preview(c, key):
    from fastapi import HTTPException
    profile = get(c, key)
    if profile['status'] != 'ACTIVE':
        raise HTTPException(409, 'Activate this targeting profile before using it for discovery.')
    company = profile['criteria']['company']; countries = []; warnings = []
    for value in company['countries']:
        try: countries.append(country(value).name)
        except ValueError: warnings.append('Country requires review: ' + value)
    verticals = []
    for term in company['industries']:
        normalized = term.casefold().replace('_', ' ')
        match = next((key for key, aliases in VERTICALS.items() if normalized in aliases or normalized == key.replace('_', ' ')), None)
        if match: verticals.append(match)
        else: warnings.append('Use Search with AI or review source coverage for industry: ' + term)
    criteria = SearchCriteria(categories=company['business_categories'][:20], regions=company['regions'][:20],
                              employee_min=company['employee_min'], employee_max=company['employee_max']).model_dump()
    post = []
    for group, values in profile['criteria'].items():
        if group == 'weights': continue
        for field, value in values.items():
            if value in (None, [], '') or field == 'revenue_currency': continue
            if group == 'company' and field in ('countries', 'cities', 'industries'): continue
            post.append({'field': group + '.' + field, 'value': value, 'mode': 'POST_DISCOVERY_EVIDENCE'})
    return {'profile': profile, 'filters': {'countries': list(dict.fromkeys(countries)), 'cities': company['cities'],
            'verticals': list(dict.fromkeys(verticals)), 'search_criteria': criteria},
            'warnings': warnings, 'post_discovery': post,
            'requires_city_review': bool(company['cities']), 'discovery_started': False}
