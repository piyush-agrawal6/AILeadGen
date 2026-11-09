"""Contact intake only: no analyzer, scoring, browser or report dependency."""
import asyncio,json
from urllib.parse import urljoin,urlsplit
from app.mail.contacted import normalize,lookup
from app.database.prospects import now,ProspectRepository
from app.database.repositories import BusinessRepository,ContactRepository
from app.database.models import Contact

def defaults():
    from app.prospecting.policy import configuration
    return configuration({'qualification_mode':'CONTACTABLE_ONLY','email_strategy':'WORKSPACE'})

def enabled(configuration):
    return (configuration or {}).get('qualification_mode')=='CONTACTABLE_ONLY'

def accept(c,b,campaign_id,source,proof):
    from app.platform.workspace import business_workspace
    organization=business_workspace(c,b,campaign_id=campaign_id)
    email=normalize(b.public_email);reason=None
    if not b.name or not b.name.strip():reason='INVALID_BUSINESS_IDENTITY'
    elif not email:reason='NO_EMAIL'
    elif proof.get('verification') not in ('PUBLICLY_PUBLISHED','OBSERVED_PUBLIC_PAGE','OWNER_PROVIDED'):reason='EMAIL_EVIDENCE_REQUIRED'
    elif lookup(c,email):reason='ALREADY_CONTACTED'
    elif c.execute("SELECT 1 FROM email_address_suppressions WHERE LOWER(address)=? AND status IN ('INVALID','TEMPORARILY_UNUSABLE')",(email,)).fetchone():reason='SUPPRESSED'
    elif c.execute("SELECT 1 FROM businesses b JOIN pipeline_runs p ON p.id=b.run_id WHERE p.campaign_id=? AND LOWER(b.public_email)=? AND b.processing_status='QUALIFIED' AND b.id<>?",(campaign_id,email,b.id or -1)).fetchone():reason='DUPLICATE_EMAIL'
    if reason:
        b.processing_status='NORMALIZED';b.rejection_reason=reason;BusinessRepository(c).update(b);return reason
    b.public_email=email
    pid=ProspectRepository(c).observe(b,campaign_id,organization=organization)
    from app.sales.service import suppressed
    if suppressed(c,pid):b.processing_status='NORMALIZED';b.rejection_reason='SUPPRESSED';BusinessRepository(c).update(b);return 'SUPPRESSED'
    b.processing_status='QUALIFIED';b.is_rejected=False;b.rejection_reason=None;BusinessRepository(c).update(b)
    if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='email' AND LOWER(contact_value)=?",(b.id,email)).fetchone():
        ContactRepository(c).insert(Contact(business_id=b.id,contact_type='email',contact_value=email,source_type='OWNER_IMPORT' if proof.get('verification')=='OWNER_PROVIDED' else 'EARLY_EMAIL' if source=='OVERTURE' else source,source_url=proof.get('url') or 'import://owner',is_valid=True,is_public_business_contact=proof.get('verification')!='OWNER_PROVIDED',confidence=1.0))
    tags=json.loads(b.source_tags or '{}');tags.setdefault('field_sources',{})['email']={**proof,'value':email,'discovered_at':proof.get('discovered_at') or now()};tags['qualification']={'mode':'CONTACTABLE_ONLY','primary_reason':'QUALIFIED','analysis_status':'DISABLED'};b.source_tags=json.dumps(tags);BusinessRepository(c).update(b);return 'QUALIFIED'

async def maps(c,businesses,campaign_id,options,check_cancel):
    """Homepage plus at most two public contact pages; stop at the remaining target."""
    from bs4 import BeautifulSoup
    from app.utils.http import SafeAsyncClient
    from app.utils.urls import extract_domain,is_safe_url
    from app.enrichment.contacts import extract_contacts_from_html,is_valid_business_email
    from app.enrichment.dns import check_email_dns
    counts={'email_found':0,'email_valid':0,'qualified':0,'already_contacted':0,'suppressed':0,'no_email':0,'contact_pages':0,'analyzed':0};seen=set()
    for b in businesses:
        check_cancel()
        if counts['qualified']>=options.get('target',50):break
        if b.processing_status=='QUALIFIED':counts['qualified']+=1;continue
        values=[];pages=[b.website] if b.website and is_safe_url(b.website,check_dns=False) else []
        # Published source contacts do not require a website or rediscovery.
        if b.public_email and b.source_osm and b.external_osm_id:
            values.append((b.public_email,'https://www.openstreetmap.org/'+b.external_osm_id))
        elif b.public_email and b.source_overture and b.external_overture_id:
            from urllib.parse import quote
            values.append((b.public_email,'overture://places/'+quote(b.external_overture_id,safe='')))
        # Existing public email evidence is reused without rediscovery.
        observed=c.execute('SELECT prospect_id FROM businesses WHERE id=?',(b.id,)).fetchone();pid=observed[0] if observed else None
        if pid:
            values.extend((r['contact_value'],r['source_url']) for r in c.execute("SELECT x.contact_value,x.source_url FROM contacts x JOIN businesses z ON z.id=x.business_id WHERE z.prospect_id=? AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1",(pid,)).fetchall())
        for index in range(3):
            if values or index>=len(pages):break
            check_cancel();url=pages[index]
            try:
                async with SafeAsyncClient(timeout=5,follow_redirects=True,max_bytes=500_000,redirect_limit=3) as client:r=await client.get(url)
                final=str(r.url)
                if r.status_code!=200 or extract_domain(final)!=extract_domain(b.website):continue
                counts['contact_pages']+=1;values.extend(extract_contacts_from_html(r.text,final).emails)
                if index==0 and not values:
                    for a in BeautifulSoup(r.text,'html.parser').find_all('a',href=True):
                        u=urljoin(final,a['href'])
                        if extract_domain(u)==extract_domain(final) and any(t in urlsplit(u).path.lower() for t in ('contact','about','team')) and u not in pages and is_safe_url(u,check_dns=False):pages.append(u)
            except Exception:continue
        if values:counts['email_found']+=1
        chosen=None;old=False
        for raw,url in values:
            email=normalize(raw)
            if not email or not is_valid_business_email(email):continue
            if lookup(c,email):old=True;continue
            if email in seen:continue
            _,valid=await asyncio.to_thread(check_email_dns,email)
            if valid:chosen=(email,url);break
        if not chosen:
            reason='ALREADY_CONTACTED' if old else 'NO_EMAIL';b.processing_status='NORMALIZED';b.rejection_reason=reason;BusinessRepository(c).update(b);counts['already_contacted' if old else 'no_email']+=1;c.commit();continue
        b.public_email=chosen[0];counts['email_valid']+=1;reason=accept(c,b,campaign_id,'OVERTURE',{'url':chosen[1],'verification':'PUBLICLY_PUBLISHED','dns_validated':True,'discovered_at':now()})
        if reason=='QUALIFIED':counts['qualified']+=1;seen.add(b.public_email)
        elif reason=='SUPPRESSED':counts['suppressed']+=1
        c.commit()
    return counts
