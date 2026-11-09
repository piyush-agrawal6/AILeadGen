"""Evidence-weighted matching; missing observations never become invented facts."""
import re
from datetime import datetime,timezone


def normal(value):return re.sub(r'[^\w]+',' ',str(value).casefold()).strip()


def evaluate(profile,business,facts,contact=None):
    if not profile:return {'status':'NOT_CONFIGURED','criteria':[],'score':None,'coverage':None}
    if profile['status']!='ACTIVE':return {'status':'NEEDS_REVIEW','profile_id':str(profile['id']),'criteria':[],'score':None,'coverage':None}
    checks=[];criteria=profile['criteria'];weights=criteria.get('weights',{});pages=facts.get('pages',[])
    actuals={'countries':business.country,'cities':business.city,'regions':business.state,'industries':business.vertical}
    person_fields={'job_titles':'role','job_functions':'job_function','seniority':'seniority','departments':'department'}
    text_fields={'industries','sub_industries','business_categories','technologies','business_models','maturity','languages','website_characteristics'}
    for group in ('company','contact','intent'):
        for field,expected in criteria[group].items():
            if expected in (None,[], '') or field=='revenue_currency':continue
            key=group+'.'+field;actual=None;status='UNKNOWN';source=None;explanation='No reliable observation is stored for this criterion.'
            if group=='company' and field in actuals and actuals[field]:
                actual=actuals[field];status='MATCH' if any(normal(value)==normal(actual) for value in expected) else 'MISMATCH'
                if field=='countries':
                    from app.config.locations import country
                    try:status='MATCH' if any(country(value).alpha_2==country(actual).alpha_2 for value in expected) else 'MISMATCH'
                    except ValueError:pass
                source='COMPANY_RECORD';explanation='Compared with the recorded company attribute; review its original discovery evidence.'
            elif group=='company' and field in ('employee_min','employee_max') and isinstance(facts.get('attributes',{}).get('employee_count',{}).get('value'),int):
                fact=facts['attributes']['employee_count'];actual=fact['value'];status='MATCH' if (actual>=expected if field=='employee_min' else actual<=expected) else 'MISMATCH';source=fact.get('source_url');explanation='Compared with the explicitly stated employee count in public structured data; this is not an estimate.'
            elif group=='contact' and contact and field in person_fields and contact.get(person_fields[field]):
                actual=contact[person_fields[field]];status='MATCH' if any(normal(value) in normal(actual) for value in expected) else 'MISMATCH';source=contact.get('source_url');explanation='Compared with the recorded professional contact attribute; employment is not independently verified.'
            if isinstance(expected,list) and (group=='company' and field in text_fields or group=='intent'):
                matches=[(value,page) for value in expected for page in pages if normal(value) and normal(value) in normal(page.get('excerpt',''))]
                if matches:
                    value,page=matches[0];status='EXCLUDED' if group=='intent' and field=='exclusions' else 'MATCH';actual=value;source=page.get('url');explanation='The requested phrase occurs in the cited public excerpt. This is a text observation, not proof of purchase intent or a verified business metric.'
            checks.append({'field':key,'status':status,'actual':actual,'expected':expected,'source':source,'explanation':explanation,'weight':weights.get(key,1)})
    known=[item for item in checks if item['status']!='UNKNOWN'];total=sum(item['weight'] for item in checks);known_weight=sum(item['weight'] for item in known)
    excluded=any(item['status']=='EXCLUDED' for item in checks)
    status='MISMATCH' if excluded or any(item['status']=='MISMATCH' for item in checks) else 'PARTIAL' if any(item['status']=='UNKNOWN' for item in checks) else 'MATCH'
    stamp=facts.get('retrieved_at');age=None
    try:age=max(0,int((datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds()/86400))
    except (ValueError,TypeError):pass
    return {'status':status,'profile_id':str(profile['id']),'revision':profile['revision'],'criteria':checks,'score':round(100*sum(item['weight'] for item in known if item['status']=='MATCH')/known_weight) if known_weight else None,'coverage':round(100*known_weight/total) if total else None,'evidence_age_days':age,'contact_relevance': 'NOT_EVALUATED' if contact is None else 'EVIDENCE_BASED','contact_availability_separate':True,'send_eligibility_evaluated':False}
