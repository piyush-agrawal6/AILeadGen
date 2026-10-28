import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from app.database.repositories import BusinessRepository,WebsiteProfileRepository,LighthouseRepository,FindingRepository,ContactRepository

ROOT=Path(__file__).resolve().parents[2]


def clean(value,limit=1200):
    text=str(value or '').strip()
    return text[:limit] if text.casefold() not in ('nan','none','null') else ''


def public_url(value):
    text=clean(value,600)
    try:
        parsed=urlsplit(text)
        return text if parsed.scheme in ('http','https') and parsed.hostname and '.' in parsed.hostname and not parsed.username and not parsed.password else ''
    except ValueError:return ''


def brand_config():
    source=json.loads((ROOT/'config/report_brand.json').read_text(encoding='utf-8'))
    return {'name':'PlaneByte','website':public_url(os.environ.get('PLANEBYTE_WEBSITE',source.get('website'))),
            'contact_email':clean(os.environ.get('PLANEBYTE_CONTACT_EMAIL',source.get('contact_email')),150),
            'phone':clean(os.environ.get('PLANEBYTE_PHONE',source.get('phone')),60),
            'show_pricing':os.environ.get('REPORT_SHOW_PRICING','false').casefold()=='true',
            'pricing':source.get('pricing',{}),'score_targets':source.get('score_targets',{'WEBSITE':90,'SEO':100,'SECURITY':100})}


def client_snapshot(conn,business_id,created_at):
    business=BusinessRepository(conn).get_by_id(business_id)
    if not business:raise ValueError('Business does not exist')
    profile=WebsiteProfileRepository(conn).get_by_business_id(business_id)
    lighthouse=LighthouseRepository(conn).get_by_business_id(business_id)
    raw=conn.execute('SELECT * FROM opportunity_scores WHERE business_id=?',(business_id,)).fetchone()
    evidence=json.loads(raw['evidence_json']) if raw else {}
    findings=FindingRepository(conn).list_by_business_id(business_id)
    contacts=ContactRepository(conn).list_by_business_id(business_id)
    website=public_url(business.website)
    mode='NO_WEBSITE' if not website else 'REACHABLE' if profile and profile.reachable else 'UNREACHABLE' if (profile is not None or business.website_status=='UNREACHABLE') else 'UNASSESSED'
    # Explicit allowlist: workflow, notes, assignment, raw IDs, provenance IDs,
    # exception strings and internal recommendations never enter this snapshot.
    result={'business':{'name':clean(business.name,180),'vertical':clean(business.vertical,80).replace('_',' ').title(),'city':clean(business.city,100),'country':clean(business.country,100),'website':website,'phone':clean(business.normalized_phone or business.phone,80),'email':clean(business.public_email,150)},
            'mode':mode,'created_at':created_at,'brand':brand_config(),'scores':{kind:raw[column] if raw else None for kind,column in [('WEBSITE','website_opportunity_score'),('SEO','seo_opportunity_score'),('SECURITY','security_opportunity_score')]},
            'primary':raw['primary_opportunity'] if raw else None,'evidence':{},'findings':[],
            'website':{},'lighthouse':{}}
    if mode!='REACHABLE':
        result['scores']['SEO']=None;result['scores']['SECURITY']=None
    for kind in ('WEBSITE','SEO','SECURITY'):
        result['evidence'][kind]=[{'code':clean(item.get('code'),100),'detail':clean(item.get('detail'),900),'points':max(0,min(100,int(item.get('points',0))))} for item in evidence.get(kind,[])[:30]]
    result['findings']=[{'code':clean(item.finding_code,100),'category':clean(item.category,50),'title':clean(item.title,160),'description':clean(item.description,900),'evidence':clean(item.evidence,900)} for item in findings[:80]]
    for contact in contacts:
        if not contact.is_public_business_contact or not contact.is_valid:continue
        field='email' if contact.contact_type=='email' else 'phone' if contact.contact_type=='phone' else None
        if field and not result['business'][field]:result['business'][field]=clean(contact.contact_value,150)
    if profile:
        result['website']={key:getattr(profile,key,None) for key in ['reachable','https_enabled','has_viewport','has_contact_page','has_booking','has_phone_on_site','has_email_on_site','page_count_crawled','has_robots_txt','has_sitemap','has_schema','has_h1','h1_count','http_status']}
        for key in ['html_title','meta_description','canonical_url']:result['website'][key]=clean(getattr(profile,key,None),400)
        result['website']['technologies']=[clean(value,80) for value in profile.detected_technologies[:8]]
        result['website']['schema_types']=[clean(value,80) for value in profile.schema_types[:8]]
    if lighthouse:
        result['lighthouse']={key:getattr(lighthouse,key,None) for key in ['performance_score','seo_score','accessibility_score','best_practices_score','lcp_ms','cls','tbt_ms']}
    from app.reports.metrics import client_metrics
    result['client_metrics']=client_metrics(result)
    result['offer'] = {
        'enabled':os.environ.get('REPORT_OFFER_ENABLED','true').lower()=='true',
        'title':clean(os.environ.get('REPORT_OFFER_TITLE','Website Redesign Launch Package'),120),
        'subtitle':clean(os.environ.get('REPORT_OFFER_SUBTITLE','Included at no additional charge with an eligible PlaneByte website project'),250),
        'seo':os.environ.get('REPORT_OFFER_INCLUDE_SEO_FOUNDATION','true').lower()=='true',
        'security':os.environ.get('REPORT_OFFER_INCLUDE_SECURITY_HARDENING','true').lower()=='true',
        'support':os.environ.get('REPORT_OFFER_INCLUDE_POST_LAUNCH_AUDIT','true').lower()=='true',
        'show_prices':os.environ.get('REPORT_SHOW_VALUE_STACK_PRICES','false').lower()=='true',
        'prices':json.loads((ROOT/'config/report_brand.json').read_text(encoding='utf-8')).get('value_stack_prices',{})}
    result['social_profiles']=[];result['capture']=None;result['business_scale']=None
    from app.database.phase36_schema import phase36_ready
    if phase36_ready(conn):
        scale=conn.execute('SELECT business_scale FROM business_intelligence WHERE business_id=?',(business_id,)).fetchone()
        result['business_scale']=scale[0] if scale else None
        capture=conn.execute('SELECT object_key,page_url,captured_at,status,reason FROM website_captures WHERE business_id=?',(business_id,)).fetchone()
        result['capture']=dict(capture) if capture else None
        pid=conn.execute('SELECT prospect_id FROM businesses WHERE id=?',(business_id,)).fetchone()[0]
        result['social_profiles']=[dict(r) for r in conn.execute('SELECT platform,profile_url,activity_status,last_activity_at,activity_reason FROM social_profiles WHERE prospect_id=? ORDER BY platform',(pid,)).fetchall()]
    return result
