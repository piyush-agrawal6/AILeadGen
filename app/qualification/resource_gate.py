"""Cheap, evidence-backed gates for newly started Maps scans only."""
import asyncio,json,re
from datetime import datetime,timezone,timedelta
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from app.acquisition.policy import valid_email
from app.database.prospects import now
from app.database.models import Contact
from app.database.repositories import BusinessRepository,ContactRepository
from app.enrichment.contacts import extract_contacts_from_html,is_valid_business_email
from app.enrichment.dns import check_email_dns
from app.enrichment.crawler import CrawlResult
from app.utils.http import SafeAsyncClient
from app.utils.urls import is_safe_url,extract_domain
from app.audit.quick import perform_quick_audit
from app.scoring.opportunities import analyze_opportunities

class QualificationAnomaly(RuntimeError):pass
IGNORED_PRELIMINARY={'ROBOTS_NOT_OBSERVED','SITEMAP_NOT_OBSERVED','HOURS_NOT_OBSERVED','NO_CITY_REFERENCE'}

def meaningful(opportunity,options,*,preliminary=False):
    selected=options.get('opportunities') or ['WEBSITE','SEO','SECURITY'];evidence=opportunity.get('evidence',{})
    groups=[[r for r in evidence.get(k,[]) if r.get('code') not in IGNORED_PRELIMINARY] for k in selected]
    areas=[sum(float(r.get('points',0)) for r in group) for group in groups];points=[float(r.get('points',0)) for group in groups for r in group]
    if not points:return False
    threshold=options.get('preliminary_opportunity_threshold') or 10
    if preliminary:return max(areas,default=0)>=threshold
    mode=options.get('qualification_mode','BALANCED');qualified=options.get('qualified_score_threshold') or 35
    if mode=='EXPLORATORY':return max(areas,default=0)>=threshold
    if mode=='STRICT':return max(points)>=40 or max(areas,default=0)>=qualified and sum(p>=10 for p in points)>=2
    return max(points)>=15 or max(areas,default=0)>=qualified

def lighthouse_useful(probe):
    if not probe or not probe.html_content:return False
    html=probe.html_content
    return len(html.encode())>=150_000 or len(re.findall(r'<script\b',html,re.I))>=12 or len(re.findall(r'<img\b',html,re.I))>=20

async def contact_pages(probe,maximum=2):
    """Only a bounded pair of observed official contact/about/team links."""
    base=probe.final_url or probe.requested_url;html=probe.html_content or '';found=[]
    for a in BeautifulSoup(html,'html.parser').find_all('a',href=True):
        url=urljoin(base,a['href'])
        if url not in found and extract_domain(url)==extract_domain(base) and re.search(r'/(?:contact|about|team)',urlsplit(url).path,re.I) and is_safe_url(url,check_dns=False):found.append(url)
    pages=[]
    for url in found[:maximum]:
        try:
            async with SafeAsyncClient(timeout=5,follow_redirects=True,max_bytes=500_000,redirect_limit=3) as client:
                response=await client.get(url)
                final=str(response.url)
                if response.status_code==200 and extract_domain(final)==extract_domain(base):pages.append((final,response.text))
        except Exception:continue
    return pages

async def early_filter(c,businesses,probes,reuse,options,vertical):
    days=options.get('email_enrichment_reuse_days') or 7;reuse.windows['contacts']=days
    ids=[b.id for b in businesses];matched={}
    if ids:
        matched={r['id']:r['prospect_id'] for r in c.execute('SELECT id,prospect_id FROM businesses WHERE id IN ('+','.join('?' for _ in ids)+')',ids).fetchall()}
    pids={pid for pid in matched.values() if pid};known={};blocked=set()
    if pids:
        marks=','.join('?' for _ in pids);params=list(pids)
        for row in c.execute("SELECT b.prospect_id,x.contact_value,x.source_url,x.created_at FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id IN ("+marks+") AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1",params).fetchall():known.setdefault(row['prospect_id'],[]).append(dict(row))
        blocked={r[0] for r in c.execute("SELECT p.id FROM prospects p LEFT JOIN prospect_sales s ON s.prospect_id=p.id WHERE p.id IN ("+marks+") AND (p.lead_status IN ('DO_NOT_CONTACT','NOT_INTERESTED','REPLIED','MEETING','PROPOSAL','WON','LOST') OR s.suppressed_at IS NOT NULL)",params).fetchall()}
        blocked|={r[0] for r in c.execute("SELECT DISTINCT prospect_id FROM email_engagement_events WHERE prospect_id IN ("+marks+") AND event_type IN ('BOUNCED_HARD','UNSUBSCRIBED')",params).fetchall()}
    blocked_addresses={r[0].lower() for r in c.execute("SELECT address FROM email_address_suppressions WHERE status IN ('INVALID','TEMPORARILY_UNUSABLE')").fetchall()}
    counts={'email_searched':0,'email_found':0,'email_valid':0,'no_email':0,'invalid_email':0,'preliminary_opportunity':0,'contact_pages':0,'contacts_reused':0,'deep_audits_skipped':0};promising=[];sem=asyncio.Semaphore(4)
    async def one(b):
        async with sem:
            pid=matched.get(b.id);tags=json.loads(b.source_tags or '{}');q={'mode':options.get('qualification_mode','BALANCED'),'email_required':True,'checked_at':now()};tags['qualification']=q
            def reject(reason):
                q['primary_reason']=reason;b.rejection_reason=reason;b.processing_status='NORMALIZED';b.source_tags=json.dumps(tags);BusinessRepository(c).update(b)
            if pid in blocked:reject('SUPPRESSED');return
            probe=probes.get(b.id)
            if not probe or not probe.reachable:reject('NO_REACHABLE_WEBSITE');return
            from app.scoring.commercial import classify_scale_v2,footprint_counts
            scale,_,_=classify_scale_v2(b,*footprint_counts(c,b),pages={probe.final_url or b.website:probe.html_content or ''})
            if scale in ('ENTERPRISE','KNOWN_CHAIN') or scale not in options.get('business_scales',['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL']):reject('CHAIN_OR_ENTERPRISE' if scale in ('ENTERPRISE','KNOWN_CHAIN') else 'LOW_COMMERCIAL_FIT');return
            if b.vertical_validation_status!='VALID':reject('WRONG_VERTICAL');return
            cached=reuse.get(b,'contacts',probe);values=[];validations={};searched_at=now()
            if cached:
                values=[tuple(r) for r in cached.get('emails',[])];validations=cached.get('validations',{});searched_at=cached.get('searched_at') or searched_at;counts['contacts_reused']+=1
            cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
            for row in known.get(pid,[]):
                if row['source_url'] and str(row['created_at'] or '')>=cutoff:values.append((row['contact_value'],row['source_url'],1.0));validations[row['contact_value']]=True
            contacts=extract_contacts_from_html(probe.html_content or '',probe.final_url or b.website)
            values.extend(contacts.emails)
            if b.public_email and (b.source_overture or b.source_osm):
                source_url='https://www.openstreetmap.org/'+str(b.external_osm_id) if b.source_osm and b.external_osm_id else 'overture://'+str(b.external_overture_id or b.id)
                values.append((b.public_email,source_url,0.8))
            async def select(items):
                for email,url,confidence in items:
                    email=valid_email(email)
                    if not email or not is_valid_business_email(email) or email in blocked_addresses:continue
                    if email in validations:valid=validations[email]
                    else:
                        _,valid=await asyncio.to_thread(check_email_dns,email,2.0);validations[email]=valid
                    if valid:return email,url,confidence
                return None
            chosen=await select(values)
            if not chosen and not cached:
                counts['email_searched']+=1
                for url,html in await contact_pages(probe):
                    counts['contact_pages']+=1;values.extend(extract_contacts_from_html(html,url).emails);chosen=await select(values)
                    if chosen:break
            counts['email_found']+=int(bool(values))
            if not cached:reuse.put(b,'contacts',probe,{'emails':values,'validations':validations,'searched_at':searched_at})
            q['email_searched_at']=searched_at
            if not chosen:
                reason='INVALID_EMAIL' if values else 'NO_EMAIL';counts['invalid_email' if values else 'no_email']+=1;reject(reason);return
            email,url,confidence=chosen;b.public_email=email;counts['email_valid']+=1;q['email_valid']=True;q['email_source_url']=url
            if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='email' AND contact_value=? AND source_type='EARLY_EMAIL'",(b.id,email)).fetchone():ContactRepository(c).insert(Contact(business_id=b.id,contact_type='email',contact_value=email,source_url=url,source_type='EARLY_EMAIL',confidence=confidence))
            cr=CrawlResult(probe.final_url or b.website);cr.homepage_html=probe.html_content;cr.all_htmls={cr.start_url:probe.html_content or ''};cr.contacts=contacts
            profile,_=perform_quick_audit(b.id,cr,vertical,probe.https_enabled,probe.http_status or 200)
            opportunity=analyze_opportunities(b,profile,crawl=cr,probe=probe,selected=options.get('opportunities'))
            q['preliminary_opportunity_score']=max((opportunity.get(k.lower()+'_opportunity_score') or 0 for k in options.get('opportunities',['WEBSITE','SEO','SECURITY'])),default=0)
            q['preliminary_evidence']=opportunity.get('evidence',{})
            if not meaningful(opportunity,options,preliminary=True):reject('NO_MEANINGFUL_OPPORTUNITY');return
            counts['preliminary_opportunity']+=1;q['primary_reason']='PREQUALIFIED';b.source_tags=json.dumps(tags);BusinessRepository(c).update(b);promising.append(b)
    await asyncio.gather(*(one(b) for b in businesses));reuse.flush();c.commit()
    promising.sort(key=lambda b:json.loads(b.source_tags or '{}').get('qualification',{}).get('preliminary_opportunity_score',0),reverse=True)
    budget=options.get('deep_audit_budget',50)
    if len(businesses)>=100:budget=min(budget,20)
    selected=promising[:budget]
    for b in promising[budget:]:
        tags=json.loads(b.source_tags or '{}');tags['qualification']['primary_reason']='DEEP_AUDIT_BUDGET';b.rejection_reason='DEEP_AUDIT_BUDGET';b.source_tags=json.dumps(tags);BusinessRepository(c).update(b)
    counts['deep_audits_skipped']=len(businesses)-len(selected);c.commit()
    return selected,counts
