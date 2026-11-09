"""Bounded company crawling and progressive intake; never imports an audit engine."""
import asyncio,csv,json,re
from pathlib import Path
from datetime import datetime,timezone
from bs4 import BeautifulSoup
from app.database.models import Contact
from app.database.repositories import BusinessRepository,ContactRepository
from app.database.prospects import ProspectRepository,now
from app.platform.context import organization
from app.acquisition.policy import policy,valid_email,published_email
from app.enrichment.contacts import is_valid_business_email
from app.enrichment.dns import check_email_dns
from app.storage import publish_artifact


def evidence(crawl,company_name=None):
    """Public excerpts are data, not instructions or claims of verified revenue."""
    from app.prospecting.company_facts import extract
    attributes=extract(crawl.all_htmls,company_name)
    pages=[]
    for url,html in list(crawl.all_htmls.items())[:3]:
        soup=BeautifulSoup(html,'html.parser')
        title=soup.title.get_text(' ',strip=True)[:200] if soup.title else ''
        meta=soup.find('meta',attrs={'name':'description'})
        for node in soup(['script','style','noscript','iframe','svg']):node.decompose()
        text=' '.join(soup.get_text(' ',strip=True).split())[:4000]
        pages.append({'url':url,'title':title,'description':str(meta.get('content',''))[:1000] if meta else '', 'excerpt':text})
    return {'status':'COMPLETE' if pages else 'FAILED','pages':pages,'retrieved_at':now(),'kind':'PUBLIC_COMPANY_INFORMATION','summary':next((page['description'] for page in pages if page['description']),pages[0]['excerpt'][:500] if pages else ''),'summary_type':'SOURCE_EXCERPT','ownership_verified':False,'attributes':attributes}


def resolve_profile(c,configuration):
    snapshot=configuration.get('icp_snapshot')
    if snapshot:
        from app.icp.models import Profile
        if str(snapshot.get('organization_id'))!=organization():
            from fastapi import HTTPException
            raise HTTPException(404,'Targeting snapshot not found in this workspace.')
        return Profile.model_validate(snapshot).model_dump(mode='json')
    key=configuration.get('icp_id')
    if not key:
        row=c.execute('SELECT default_icp_id FROM organization_setup WHERE organization_id=?',(organization(),)).fetchone();key=row[0] if row else None
    if not key:return {}
    from app.icp.service import get
    return get(c,str(key))


def match_icp(c,b,facts,configuration,*,profile=None):
    profile=resolve_profile(c,configuration) if profile is None else profile
    from app.icp.matching import evaluate
    return evaluate(profile,b,facts)


async def public_contact(b,tags,crawl):
    """Reuse published source evidence; never synthesize a mailbox pattern."""
    email=valid_email(b.public_email)
    if not email or not is_valid_business_email(email):return False
    proof=tags.setdefault('field_sources',{}).get('email',{})
    if proof.get('verification') not in ('PUBLICLY_PUBLISHED','OBSERVED_PUBLIC_PAGE'):
        source=next((item[1] for item in crawl.contacts.emails if valid_email(item[0])==email),None) if crawl else None
        if not source and b.source_osm and b.external_osm_id:source='https://www.openstreetmap.org/'+b.external_osm_id
        if not source and b.source_overture and b.external_overture_id:source='overture://places/'+b.external_overture_id
        if not source:return False
        proof={'url':source,'verification':'PUBLICLY_PUBLISHED','value':email,'discovered_at':now()}
    if not proof.get('dns_validated'):
        try:_,valid=await asyncio.wait_for(asyncio.to_thread(check_email_dns,email),timeout=5)
        except (TimeoutError,ValueError):return False
        if not valid:return False
        proof['dns_validated']=True
    tags['field_sources']['email']=proof
    return True


async def process(c,businesses,campaign_id,options,crawler,check_cancel,emit):
    org=organization();mode=policy(options.get('source_type','OVERTURE'));target=max(1,int(options.get('target',50)))
    profile=resolve_profile(c,options)
    from app.platform.workspace import business_workspace
    for business in businesses:business_workspace(c,business,organization=org,campaign_id=campaign_id)
    # Reuse company excerpts only for the same canonical company, website and
    # verified workspace. Assessment caches are deliberately not consulted.
    for b in businesses:
        identity=c.execute('SELECT prospect_id FROM businesses WHERE id=?',(b.id,)).fetchone()
        prospect_id=identity[0] if identity else None
        if not prospect_id or not b.website:continue
        tags=json.loads(b.source_tags or '{}')
        if tags.get('company_intelligence',{}).get('status')=='COMPLETE':continue
        prior=c.execute("SELECT b.source_tags_json,b.public_email FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.prospect_id=? AND b.website=? AND b.id<>? AND r.organization_id=? ORDER BY b.id DESC LIMIT 5",(prospect_id,b.website,b.id,org)).fetchall()
        for row in prior:
            saved=json.loads(row['source_tags_json'] or '{}');facts=saved.get('company_intelligence',{})
            if facts.get('status')!='COMPLETE':continue
            try:fresh=0<=(datetime.now(timezone.utc)-datetime.fromisoformat(facts['retrieved_at'])).total_seconds()<7*86400
            except (ValueError,KeyError,TypeError):fresh=False
            if not fresh:continue
            tags['company_intelligence']=facts
            proof=saved.get('field_sources',{}).get('email',{})
            if not b.public_email and row['public_email'] and proof.get('verification')=='PUBLICLY_PUBLISHED':
                b.public_email=row['public_email'];tags.setdefault('field_sources',{})['email']=proof
            b.source_tags=json.dumps(tags);break
    counts={'qualified':0,'company_pages':0,'company_information':0,'manual_contact':0,'no_email':0,'needs_review':0,'icp_mismatch':0,'reused':0}
    limit=300 if options.get('max_candidates') is None else int(options['max_candidates'])
    queue=list(businesses[:min(1000,max(0,limit))]);semaphore=asyncio.Semaphore(2)
    from app.prospecting.criteria import evaluate
    def search_evaluation(b,facts):
        existing=c.execute('SELECT 1 FROM prospect_observations old JOIN businesses original ON original.id=old.business_id WHERE old.prospect_id=(SELECT prospect_id FROM businesses WHERE id=?) AND original.run_id<>? LIMIT 1',(b.id,b.run_id)).fetchone()
        return evaluate(b,facts,options.get('search_criteria'),existing=bool(existing))

    async def crawl_one(b):
        async with semaphore:
            check_cancel()
            tags=json.loads(b.source_tags or '{}')
            if not mode.trusted_import and search_evaluation(b,tags.get('company_intelligence',{}))['status']=='EXCLUDED':return None
            if not b.website:return None
            # Firecrawl is contactable discovery. Never crawl unusable raw results.
            tags=json.loads(b.source_tags or '{}')
            if mode.email_before_analysis and not mode.business_fit_gate and not published_email(b,tags.get('field_sources',{})):return None
            try:return await asyncio.wait_for(crawler.crawl(b.website),timeout=25)
            except Exception:return None
    for offset in range(0,len(queue),2):
        if counts['qualified']>=target:break
        group=queue[offset:offset+min(2,target-counts['qualified'])]
        tasks=[];results=[]
        for b in group:
            tags=json.loads(b.source_tags or '{}');prior=tags.get('company_intelligence',{})
            fresh=False
            if prior.get('retrieved_at') and prior.get('status')=='COMPLETE':
                try:fresh=0<=(datetime.now(timezone.utc)-datetime.fromisoformat(prior['retrieved_at'])).total_seconds()<7*86400
                except (ValueError,TypeError):pass
            if fresh:tasks.append(None);results.append(None);counts['reused']+=1;counts['company_information']+=1
            else:tasks.append(asyncio.create_task(crawl_one(b)));results.append(None)
        try:
            for index,task in enumerate(tasks):
                if task:results[index]=await task
        finally:
            for task in tasks:
                if task and not task.done():task.cancel()
            await asyncio.gather(*(task for task in tasks if task),return_exceptions=True)
        for b,crawl in zip(group,results):
            check_cancel();tags=json.loads(b.source_tags or '{}');facts=tags.get('company_intelligence',{})
            if crawl:
                facts=evidence(crawl,b.name);counts['company_pages']+=crawl.pages_crawled;counts['company_information']+=bool(crawl.pages_crawled)
                tags['company_intelligence']=facts
                b.website_status='REACHABLE' if crawl.pages_crawled else 'UNREACHABLE'
                if not b.public_email and (not mode.trusted_import or options.get('find_missing_contacts')):
                    for raw,url,*_ in crawl.contacts.emails:
                        email=valid_email(raw)
                        if not email or not is_valid_business_email(email):continue
                        try:_,valid=await asyncio.wait_for(asyncio.to_thread(check_email_dns,email),timeout=5)
                        except TimeoutError:continue
                        if not valid:continue
                        b.public_email=email;tags.setdefault('field_sources',{})['email']={'value':email,'url':url,'verification':'PUBLICLY_PUBLISHED','discovered_at':now(),'dns_validated':True};break
                for raw,url,*_ in crawl.contacts.emails[:20]:
                    email=valid_email(raw)
                    if email and is_valid_business_email(email) and not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='email' AND contact_value=?",(b.id,email)).fetchone():ContactRepository(c).insert(Contact(business_id=b.id,contact_type='email',contact_value=email,source_url=url,source_type='WEBSITE',is_valid=bool(email==b.public_email and tags.get('field_sources',{}).get('email',{}).get('dns_validated')),is_public_business_contact=True))
                for phone,url,confidence in crawl.contacts.phones[:10]:
                    if not b.phone:b.phone=phone;b.normalized_phone=phone;tags.setdefault('field_sources',{})['phone']={'value':phone,'url':url,'verification':'OBSERVED_PUBLIC_PAGE','discovered_at':now()}
                    if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='phone' AND contact_value=?",(b.id,phone)).fetchone():ContactRepository(c).insert(Contact(business_id=b.id,contact_type='phone',contact_value=phone,source_url=url,source_type='WEBSITE',confidence=confidence))
                for url in crawl.contacts.contact_forms[:5]:
                    if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='contact_form' AND contact_value=?",(b.id,url)).fetchone():ContactRepository(c).insert(Contact(business_id=b.id,contact_type='contact_form',contact_value=url,source_url=url,source_type='WEBSITE'))
                for platform,url in crawl.social_links.items():
                    if platform in ('instagram','facebook','linkedin','x_url') and not getattr(b,platform):setattr(b,platform,url)
            elif not facts:tags['company_intelligence']={'status':'NOT_AVAILABLE' if not b.website else 'FAILED','pages':[],'retrieved_at':now()}
            fit=match_icp(c,b,tags['company_intelligence'],options,profile=profile);tags['icp_match']=fit
            # Company qualification is separate from contact availability. A
            # fitting Maps company may be retained for manual contact. Only the
            # explicit Firecrawl contactable source requires a usable email.
            usable=bool(valid_email(b.public_email)) if mode.trusted_import else await public_contact(b,tags,crawl) if valid_email(b.public_email) else False
            tags['contact_availability']={'status':('OWNER_PROVIDED' if mode.trusted_import else 'PUBLIC_EMAIL_VALIDATED') if usable else 'NO_USABLE_PUBLIC_EMAIL','usable_email':usable}
            if not usable:counts['no_email']+=1
            if usable and not mode.trusted_import:
                proof=tags['field_sources']['email']
                if not c.execute("SELECT 1 FROM contacts WHERE business_id=? AND contact_type='email' AND contact_value=? AND is_valid=1 AND is_public_business_contact=1",(b.id,b.public_email)).fetchone():
                    ContactRepository(c).insert(Contact(business_id=b.id,contact_type='email',contact_value=b.public_email,source_url=proof.get('url'),source_type=options.get('source_type','OVERTURE'),is_valid=True,is_public_business_contact=True))
            search_fit=search_evaluation(b,tags.get('company_intelligence',{}));tags['search_evaluation']=search_fit
            reason=None
            if not mode.trusted_import:
                if search_fit['status']=='EXCLUDED':reason='SEARCH_CRITERIA_EXCLUDED'
                elif mode.business_fit_gate and b.vertical_validation_status=='INVALID':reason='BUSINESS_FIT_MISMATCH'
                elif fit['status']=='MISMATCH':reason='ICP_MISMATCH';counts['icp_mismatch']+=1
                elif fit['status']=='NEEDS_REVIEW':reason='ICP_REQUIRES_REVIEW'
                elif mode.email_before_analysis and not valid_email(b.public_email):reason='NO_EMAIL'
                elif not mode.business_fit_gate and not published_email(b,tags.get('field_sources',{})):reason='EMAIL_EVIDENCE_REQUIRED'
                elif mode.email_before_analysis and not usable:reason='NO_USABLE_PUBLIC_EMAIL'
            if tags.get('qualification'):tags.setdefault('historical_qualification',tags['qualification'])
            tags['qualification']={'policy':mode.mode.value,'primary_reason':reason or ('QUALIFIED_IMPORTED' if mode.trusted_import else 'QUALIFIED'),'analysis_status':'EXCLUDED_FROM_LEAD_ENGINE','qualified_at':now()}
            b.source_tags=json.dumps(tags);b.processing_status='NORMALIZED' if reason else 'QUALIFIED';b.rejection_reason=reason;b.is_rejected=False
            BusinessRepository(c).update(b)
            if not reason:
                try:ProspectRepository(c).observe(b,campaign_id,options.get('created_by'),organization=org)
                except ValueError:b.processing_status='REJECTED';b.is_rejected=True;b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED';BusinessRepository(c).update(b);counts['needs_review']+=1;c.commit();continue
                counts['qualified']+=1;counts['manual_contact']+=not usable
            if campaign_id:
                from app.workflows.history import capture_business
                capture_business(c,campaign_id,b.id)
            c.commit()
            emit(stage='COMPANY',event_type='COMPANY_SAVED',message='Company information and source qualification saved.',completed=counts['qualified'],total=target,metadata={'business_id':b.id,'qualified':not bool(reason)})
    return counts


def exports(c,run,qualified,output_dir):
    """General prospect exports have no scores, findings or mandatory PDF."""
    from openpyxl import Workbook
    fields=['company','website','email','phone','city','country','industry','qualification','icp_match']
    rows=[]
    for b in qualified:
        tags=json.loads(b.source_tags or '{}');rows.append([b.name,b.website or '',b.public_email or '',b.phone or '',b.city or '',b.country or '',b.vertical,b.processing_status,tags.get('icp_match',{}).get('status','NOT_CONFIGURED')])
    root=Path(output_dir);root.mkdir(parents=True,exist_ok=True);csv_path=root/f'prospects_{run.id}.csv';xlsx_path=root/f'prospects_{run.id}.xlsx'
    # Escape spreadsheet formulas in both export formats, including untrusted names.
    safe=lambda value:"'"+str(value) if str(value).lstrip().startswith(('=','+','-','@','\t','\r')) else str(value)
    with csv_path.open('w',newline='',encoding='utf-8-sig') as file:
        writer=csv.writer(file);writer.writerow(fields);writer.writerows([[safe(value) for value in row] for row in rows])
    book=Workbook();sheet=book.active;sheet.title='Companies';sheet.append(fields)
    for row in rows:sheet.append([safe(value) for value in row])
    sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions;book.save(xlsx_path)
    campaign=c.execute('SELECT campaign_id FROM pipeline_runs WHERE id=? AND organization_id=?',(run.id,organization())).fetchone()[0] or 'legacy'
    for kind,path in [('csv',csv_path),('xlsx',xlsx_path)]:publish_artifact(c,f'campaigns/{campaign}/runs/{run.id}/leads.{kind}',path,run_id=run.id,kind=kind)
    return str(xlsx_path),len(rows)
