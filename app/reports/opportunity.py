"""Deterministic consultancy copy derived exclusively from stored public evidence."""
import re
from app.reports.copy import FINDING_COPY,explanation

CONTENT_VERSION=2
ALIASES={'NO_HTTPS':'HTTP_ONLY','NO_HTTP_TO_HTTPS_REDIRECT':'HTTP_ONLY','HTTP_NOT_HTTPS':'HTTP_ONLY','MISSING_VIEWPORT':'NO_MOBILE_VIEWPORT','POOR_VERTICAL_CONVERSION_FLOW':'NO_PRIMARY_CTA','NO_CONTACT_FLOW':'NO_PRIMARY_CTA','BROKEN_INTERNAL_LINKS':'BROKEN_LINKS','MISSING_LOCAL_SCHEMA':'MISSING_SCHEMA','NO_VERTICAL_SCHEMA':'MISSING_SCHEMA'}
BUSINESS_COPY={
 'HTTP_ONLY':('Visitor trust','The public experience still uses HTTP','the page we reached was served over HTTP','Unencrypted browsing can create trust and data-protection concerns for visitors.','Consistent HTTPS across the public journey, with redirects and certificate checks.'),
 'NO_MOBILE_VIEWPORT':('Mobile usability','A clearer experience on smaller screens','a mobile viewport declaration was absent from the reviewed HTML','Potential customers may have to work harder to read content or reach the next step on a phone.','Responsive page templates with a verified mobile layout and clear next steps.'),
 'NO_PRIMARY_CTA':('Customer journey','Make the next enquiry easier','a prominent booking or enquiry action was not found in the sampled links','Interested visitors may not have an obvious route from browsing to contacting the business.','A visible primary action and a tested enquiry or booking journey.'),
 'MISSING_META_DESCRIPTION':('Search presentation','Give search visitors clearer context','the homepage had no meta description in the reviewed response','A useful description can help explain the page to search visitors; search engines may choose their own snippet.','Accurate page titles and descriptions that reflect the services and location.'),
 'MISSING_H1':('Content clarity','Make the page purpose easier to understand','a primary heading was not found on the reviewed page','Visitors and assistive tools may receive less guidance about the page and its services.','A clear heading hierarchy and focused service presentation.'),
 'MISSING_SCHEMA':('Search foundations','Describe the business more clearly','relevant structured business data was not observed','Search systems may have less explicit context about the business; this does not establish a ranking problem.','Accurate structured data appropriate to the business and its public services.'),
 'NO_CONTACT_PAGE':('Enquiry clarity','Make business contact details easier to find','a dedicated contact page was not observed in the sample','Potential customers may need extra effort to confirm how and where to get in touch.','An accessible contact page with accurate business details and a suitable enquiry method.'),
}
SERVICES={
 'WEBSITE':('Website modernisation + technical foundation upgrade','PlaneByte can rebuild the key pages around a mobile-first experience, clearer service information and a focused enquiry journey.'),
 'SEO':('Technical SEO + search presentation improvements','PlaneByte can improve page structure, search descriptions and relevant business information around the observed gaps.'),
 'SECURITY':('Technical trust + public configuration review','PlaneByte can review the observed transport and browser configuration with your hosting provider and implement an agreed improvement scope.'),
 'COMBINED':('Website modernisation + technical foundation upgrade','PlaneByte can connect a clearer mobile-first website and enquiry journey with stronger search foundations and technical trust.'),
}

def sentences(values):
 values=list(values)
 return values[0] if len(values)==1 else ', '.join(values[:-1])+' and '+values[-1] if values else ''

def findings(data):
 rows={}
 for kind,items in data.get('evidence',{}).items():
  if data.get('mode')!='REACHABLE' and kind!='WEBSITE':continue
  for item in items:
   code=ALIASES.get(item.get('code'),item.get('code'))
   if code not in FINDING_COPY or not str(item.get('detail','')).strip():continue
   explained=explanation(kind,{**item,'code':code})
   category,title,observation,impact,improvement=BUSINESS_COPY.get(code,(('Customer experience' if kind=='WEBSITE' else 'Search foundations' if kind=='SEO' else 'Technical trust'),explained['title'],explained['evidence'].rstrip('.'),explained['impact'],explained['recommendation']))
   row={'code':code,'kind':kind,'title':title,'category':category,'observation':observation,'evidence':explained['evidence'],'impact':impact,'improvement':improvement,'points':item.get('points',0),'priority':'HIGH IMPACT' if item.get('points',0)>=15 else 'MEDIUM IMPACT' if item.get('points',0)>=5 else 'FOUNDATIONAL'}
   if code not in rows or row['points']>rows[code]['points']:rows[code]=row
 primary=data.get('primary')
 # One physical observation has one explanation even when multiple score families use it.
 return sorted(rows.values(),key=lambda r:(-(r['points']+(6 if r['kind']==primary else 0)),r['code']))

def pitch_support(data,selected):
 supported=[]
 for kind in selected:
  scoped={**data,'evidence':{kind:data.get('evidence',{}).get(kind,[])}}
  meaningful=[r for r in findings(scoped) if r['points']>0]
  policy=data.get('pitch_policy',data.get('brand',{}).get('pitch_policy',{})).get(kind,{})
  codes={r['code'] for r in meaningful}
  if policy.get('enabled',True) and len(meaningful)>=policy.get('minimum_findings',2) and (data.get('scores',{}).get(kind) or 0)>=policy.get('minimum_score',40) and set(policy.get('required_evidence',[]))<=codes:supported.append(kind)
 return supported

def plan(data,variant=None,allowed_kinds=None):
 allowed_kinds=allowed_kinds if allowed_kinds is not None else data.get('outreach_pitch_types')
 if allowed_kinds is not None:
  data={**data,'evidence':{k:v for k,v in data.get('evidence',{}).items() if k in allowed_kinds}}
 all_findings=findings(data);primary=data.get('primary') or 'WEBSITE'
 if variant in ('website','seo','security'):
  primary=variant.upper()
  all_findings=sorted(all_findings,key=lambda r:(r['kind']!=primary,-r['points']))
 kinds={r['kind'] for r in all_findings if r['points']>=10}
 if allowed_kinds is not None:chosen='combined' if len(allowed_kinds)>1 else (allowed_kinds[0].lower() if allowed_kinds else primary.lower())
 else:chosen='combined' if variant=='combined' or (variant is None and len(kinds)>=2 and (data.get('scores',{}).get('WEBSITE') or 0)>=40) else primary.lower()
 if chosen not in ('website','seo','security','combined'):chosen='website'
 key=chosen.upper();service_title,solution=SERVICES[key]
 if chosen=='combined' and allowed_kinds is not None and 'WEBSITE' not in allowed_kinds:service_title='Search foundations + technical trust';solution='PlaneByte can connect technical SEO improvements and agreed public configuration work within one implementation scope.'
 approved=data.get('brand',{}).get('services',{})
 relevant=[k for k in ('WEBSITE','SEO','SECURITY') if k in kinds]
 if primary in relevant:relevant.remove(primary);relevant.insert(0,primary)
 services=[{'kind':k,**approved[k]} for k in relevant if k in approved][:3]
 top=all_findings[:3];offer=data.get('offer') or {}
 eligible=bool((allowed_kinds is None or 'WEBSITE' in allowed_kinds) and offer.get('enabled') and chosen in ('website','combined') and (data.get('scores',{}).get('WEBSITE') or 0)>=40)
 included=[]
 for flag,title,description in [('seo','SEO launch foundations','Core page titles, descriptions and crawlability checks for the agreed pages.'),('security','Basic external security configuration review','Public HTTPS and browser configuration checks, with hosting dependencies documented.'),('support','Post-launch technical validation','Recheck the agreed pages, enquiry paths and technical setup after launch.')]:
  if eligible and offer.get(flag):included.append({'title':title,'description':description})
 value=('For an eligible website project, '+sentences(i['title'].lower().replace('seo','SEO') for i in included)+' can be included in the agreed scope, rather than separate add-ons.') if included else ''
 return {'content_version':CONTENT_VERSION,'pitch_types':list(allowed_kinds) if allowed_kinds is not None else sorted(kinds),'variant':chosen,'findings':all_findings[:5],'top':top,'service_title':service_title,'solution':solution,'services':services,'included':included,'offer_eligible':eligible,'value':value,'credibility':data.get('brand',{}).get('report_copy',{}).get('why_planebyte',[]),'cta':data.get('brand',{}).get('report_copy',{}).get('cta') or "If this is already on your roadmap, reply here and I can send over a suggested priority order and rough implementation scope.",'title':'Website & Digital Growth Review' if chosen in ('website','combined') else 'Digital Growth Opportunity Review'}

def report_issues(data,p=None):
 p=p or plan(data);issues=[]
 if len(p['findings'])<2:issues.append('At least two meaningful, distinct findings are required.')
 if not p['services']:issues.append('No approved PlaneByte service matches the evidence.')
 if not p['solution'] or not p['cta']:issues.append('A clear value proposition and reply CTA are required.')
 if len({r['code'] for r in p['findings']})!=len(p['findings']):issues.append('Repeated findings require review.')
 def strings(value):
  if isinstance(value,str):yield value
  elif isinstance(value,dict):
   for v in value.values():yield from strings(v)
  elif isinstance(value,list):
   for v in value:yield from strings(v)
 if any(re.search(r'{{|}}|\[INSERT|\[COMPANY',v) for v in strings(data)):issues.append('Unresolved content placeholders require review.')
 return issues

def vertical_context(business):
 vertical=business.get('vertical','').lower().replace('_',' ')
 if any(x in vertical for x in ('hospital','hotel')):return {'journey':'guest','action':'booking or enquiry','mobile':'mobile guest experience','impact_action':'the booking or enquiry journey'}
 if 'dent' in vertical:return {'journey':'patient','action':'appointment enquiry','mobile':'mobile contact experience','impact_action':'the appointment enquiry journey'}
 if 'real estate' in vertical:return {'journey':'buyer or tenant','action':'property enquiry','mobile':'mobile property browsing experience','impact_action':'the property enquiry journey'}
 if 'home service' in vertical:return {'journey':'customer','action':'quote or service enquiry','mobile':'mobile contact experience','impact_action':'the call or enquiry journey'}
 if 'legal' in vertical:return {'journey':'client','action':'consultation enquiry','mobile':'mobile contact experience','impact_action':'the consultation enquiry journey'}
 return {'journey':'customer','action':'enquiry','mobile':'mobile experience','impact_action':'the enquiry journey'}


def email_observation(item,business):
    """A business-language translation, never a new measured finding."""
    context=vertical_context(business);code=item['code']
    copy={
      'HTTP_ONLY':'the reviewed site did not use an encrypted connection',
      'NO_MOBILE_VIEWPORT':'the mobile setup may be less consistent on smaller screens',
      'NO_PRIMARY_CTA':f"a clear {context['action']} step was not apparent in the reviewed pages",
      'MISSING_META_DESCRIPTION':'the homepage has limited guidance for how the business is described in search results',
      'MISSING_TITLE':'the reviewed page lacked a clear title for visitors and search systems',
      'MISSING_H1':'the main purpose of the page could be clearer to visitors',
      'MULTIPLE_H1':'the page hierarchy could make key information easier to follow',
      'MISSING_SCHEMA':'the reviewed pages could describe the business more explicitly to search systems',
      'NO_CONTACT_PAGE':'a dedicated contact page was not apparent in the reviewed pages',
      'NO_PHONE_CTA':'the reviewed pages did not offer a direct tap-to-call action',
      'NO_CITY_REFERENCE':'the service location was not clear in the sampled page text',
      'POOR_PERFORMANCE':'the recorded loading check suggests a slower experience for visitors',
      'VERY_POOR_PERFORMANCE':'the recorded loading check suggests significant friction before visitors reach key content',
      'BROKEN_LINKS':'some links in the reviewed journey led to page errors',
      'NO_CSP':'a browser protection policy for permitted page content was not observed',
      'NO_FRAME_PROTECTION':'a browser policy controlling where the pages can be embedded was not observed',
      'NO_HSTS':'a browser policy for preferring secure connections on return visits was not observed',
      'NO_NOSNIFF':'a browser protection setting for interpreting downloaded content was not observed',
      'NO_REFERRER_POLICY':'a browser policy for sharing referral information was not observed',
      'NO_PERMISSIONS_POLICY':'a browser policy for optional device capabilities was not observed',
      'INSECURE_FORM_ACTION':'an enquiry form pointed to an unencrypted destination; no form was submitted',
      'CERTIFICATE_VERIFICATION_FAILED':'the recorded connection check could not confirm a trusted website certificate',
      'ROBOTS_NOT_OBSERVED':'the review could not confirm the intended guidance for search crawlers',
      'SITEMAP_NOT_OBSERVED':'a page-discovery file for search systems was not observed',
      'MISSING_CANONICAL':'the preferred page version was not explicitly identified in the reviewed response',
    }
    return copy.get(code,item['impact'][0].lower()+item['impact'][1:].rstrip('.'))


def company_signature(data,settings=None):
    name=(getattr(settings,'outreach_sender_name','') or '').strip()
    role=(getattr(settings,'outreach_sender_role','') or '').strip()
    lines=[name+' | PlaneByte' if name else 'PlaneByte']
    if name and role:lines.append(role)
    return '\n'.join(filter(None,[*lines,'Software Engineering · SEO · Security',data['brand'].get('website'),data['brand'].get('contact_email')]))


def why_planebyte(p):
    if p.get('credibility'):return tuple((p['credibility']+['','',''])[:3])
    if p['variant'] in ('website','combined') and ('WEBSITE' in p.get('pitch_types',[]) or not p.get('pitch_types')):
        kinds={s['kind'] for s in p['services']}
        areas=[]
        if 'WEBSITE' in kinds:areas.extend(['the website experience and development','deployment'])
        if 'SEO' in kinds:areas.append('technical SEO foundations')
        if 'SECURITY' in kinds:areas.append('agreed security configuration')
        return ('One team from strategy through launch.',
                'Instead of coordinating separate web, SEO and technical providers, PlaneByte can handle '+sentences(areas)+' within one implementation scope.',
                'You get one delivery plan, one technical team and one post-launch validation process.')
    return ('One team from priorities through validation.',
            'PlaneByte can connect the observed '+('search presentation and technical SEO' if p['variant']=='seo' else 'public technical trust and configuration')+' work with implementation and agreed hosting dependencies in one delivery scope.',
            'You get one delivery plan, one technical team and one validation process for the agreed changes.')


def email_values(data,p,settings=None):
 b=data['business'];name=b['name'];context=vertical_context(b);count=len(p['top'])
 opening=f"I reviewed the {name} website from a {context['journey']}-journey perspective and noticed "+({2:'two',3:'three'}.get(count,str(count)))+(' opportunities.' if count!=1 else ' opportunity.')
 observations=sentences(email_observation(r,b) for r in p['top'])
 observations=observations[0].upper()+observations[1:]+'.' if observations else ''
 impacts=[]
 for r in p['top']:
  label={'Visitor trust':'visitor trust','Mobile usability':context['mobile'],'Customer journey':context['impact_action'],'Search presentation':'search visibility foundations','Enquiry clarity':context['impact_action'],'Technical trust':'technical reliability'}.get(r['category'],r['category'].lower())
  if label not in impacts:impacts.append(label)
 impact='Together, these can affect '+sentences(impacts[:3])+'.' if impacts else ''
 subject=(str(min(3,count))+' website opportunities for '+name) if p['variant'] in ('website','combined') else ('Website review for '+name)
 if p['variant'] in ('website','combined') and ('WEBSITE' in p.get('pitch_types',[]) or not p.get('pitch_types')):
  solution='PlaneByte can address this through a mobile-first website and technical foundation upgrade, with a clearer '+context['action']+' journey, rather than simply changing the visual design.'
 else:solution=p['solution']
 included='For an eligible website project, we can also include '+sentences(i['title'].lower().replace('seo','SEO') for i in p['included'])+' within the agreed scope.' if p['included'] else ''
 return {'business_name':name,'opening':opening,'observations':observations,'business_impact':impact,'solution':solution,'included_value':included,'cta':p['cta'],'signature':company_signature(data,settings),'opportunity_subject':subject,'website':b.get('website'),'city':b.get('city'),'vertical':b.get('vertical'),'primary_opportunity':p['variant'],'top_finding':observations,'sender_name':getattr(settings,'outreach_sender_name','') or 'PlaneByte','sender_company':'PlaneByte'}
