"""Optional, bounded public enrichment; unidentified website ownership stays review-only."""
import hashlib,json
from app.database.connection import db_session
from app.acquisition.config import require
from app.acquisition.firecrawl import FirecrawlLeadSource,SourceUnavailable
from app.acquisition.pipeline import inherit_existing
from app.normalization.businesses import normalize_business
from app.utils.text import normalize_business_name
from app.utils.urls import extract_domain
from app.acquisition import service

async def missing_website(jid,b,tags,processing,budget,db_path=None):
    with db_session(db_path) as c:
        record=service.job(c,jid)
        inherit_existing(c,b,tags,organization=record['organization_id'])
        try:require('firecrawl',c);enabled=True
        except Exception:enabled=False
    normalize_business(b)
    if b.website or not processing.find_missing_contacts or not enabled:return b,tags
    from app.acquisition.worker import provider_request
    source=FirecrawlLeadSource();term=' '.join(str(x) for x in (b.name,b.city,b.country,'official website') if x);fingerprint=hashlib.sha256(term.encode()).hexdigest();matches={}
    try:
        result=await provider_request(jid,'missing-site-search:'+fingerprint,'search',budget,lambda:source.search(term,limit=3,country_code=b.country_code),db_path)
        for item in result['items'][:3]:
            url=item.get('url') or ''
            if not url:continue
            key='missing-site:'+hashlib.sha256(url.encode()).hexdigest()
            async def extract():
                page=await source.scrape(url);candidate,reason=source.candidate(url,page);return {'candidate':candidate,'reason':reason}
            checked=await provider_request(jid,key,'scrape',budget,extract,db_path);record=checked['candidate']
            if not record or normalize_business_name(record['company_name'])!=b.normalized_name:continue
            text=record.get('evidence_text','');location=bool(b.city and b.city.casefold() in text);phone=bool(b.normalized_phone and ''.join(x for x in b.normalized_phone if x.isdigit()) in ''.join(x for x in record.get('phone','') if x.isdigit()))
            if not(location or phone):continue
            matches[extract_domain(record['website'])]=record
        if len(matches)==1:
            candidate=next(iter(matches.values()));b.website=candidate['website'];tags.setdefault('field_sources',{})['website']=candidate['field_sources']['website']
            for field,destination in [('email','public_email'),('phone','phone')]:
                if not getattr(b,destination) and candidate.get(field):setattr(b,destination,candidate[field]);tags['field_sources'][field]=candidate['field_sources'][field]
            normalize_business(b)
        else:tags['needs_review']='WEBSITE_OWNERSHIP_REVIEW_REQUIRED'
    except SourceUnavailable:
        tags['needs_review']='WEBSITE_OWNERSHIP_REVIEW_REQUIRED'
        with db_session(db_path) as c:service.issue(c,jid,tags.get('row_number'),'Missing website could not be confidently resolved within the Firecrawl budget.',{'company':b.name})
    return b,tags

async def optional_contacts(jid,data,source,budget,db_path=None):
    """One opt-in contact/about page per request; total page cap is durable."""
    from app.acquisition.worker import provider_request
    from app.enrichment.contacts import extract_contacts_from_html
    from app.utils.urls import is_safe_url
    url=data.get('contact_page')
    if not url or not is_safe_url(url,check_dns=False) or extract_domain(url)!=extract_domain(data['website']):return data
    key='contact-crawl:'+hashlib.sha256(url.encode()).hexdigest()
    async def collect():
        pages=await source.bounded_crawl(url,1);found={}
        for page in pages[:1]:
            final=(page.get('metadata') or {}).get('sourceURL') or url
            html=page.get('html') or ''
            if not is_safe_url(final,check_dns=False) or extract_domain(final)!=extract_domain(data['website']) or not isinstance(html,str) or len(html)>3_000_000:continue
            contacts=extract_contacts_from_html(html,final)
            if contacts.emails:found['email']={'value':contacts.emails[0][0],'url':contacts.emails[0][1]}
            if contacts.phones:found['phone']={'value':contacts.phones[0][0],'url':contacts.phones[0][1]}
        return found
    try:
        found=await provider_request(jid,key,'crawl',budget,collect,db_path)
        for field,evidence in found.items():
            if not data.get(field):data[field]=evidence['value'];data['field_sources'][field]={'source':'FIRECRAWL','url':evidence['url'],'verification':'PUBLICLY_PUBLISHED'}
    except SourceUnavailable:
        with db_session(db_path) as c:service.issue(c,jid,None,'Optional contact-page discovery did not complete within its resource limits.',{'url':url})
    return data

async def contact_page_email(jid,data,source,budget,db_path=None):
    """One official contact-page scrape before deep analysis, within page budget."""
    from app.acquisition.worker import provider_request
    from app.enrichment.contacts import extract_contacts_from_html
    from app.acquisition.policy import published_email
    from app.utils.urls import is_safe_url
    if published_email(data,data.get('field_sources',{})):return data
    url=data.get('contact_page')
    if not url or not is_safe_url(url,check_dns=False) or extract_domain(url)!=extract_domain(data['website']):return data
    key='contact-page:'+hashlib.sha256(url.encode()).hexdigest()
    with db_session(db_path) as c:
        if c.execute("SELECT 1 FROM acquisition_requests WHERE job_id=? AND request_key=? AND status='FAILED'",(jid,key)).fetchone():return data
    async def collect():
        page=await source.scrape(url);final=(page.get('metadata') or {}).get('sourceURL') or url;html=page.get('html') or ''
        if not is_safe_url(final,check_dns=False) or extract_domain(final)!=extract_domain(data['website']) or not isinstance(html,str) or len(html)>3_000_000:return {'credits':page.get('_credits_used')}
        contacts=extract_contacts_from_html(html,final)
        return ({'email':contacts.emails[0][0],'url':contacts.emails[0][1]} if contacts.emails else {})|{'credits':page.get('_credits_used')}
    found=await provider_request(jid,key,'scrape',budget,collect,db_path)
    if found.get('email'):
        data['email']=found['email'];data['field_sources']['email']={'source':'FIRECRAWL','url':found['url'],'verification':'PUBLICLY_PUBLISHED'}
    return data
